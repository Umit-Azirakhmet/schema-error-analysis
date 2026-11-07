"""Offline EACL re-evaluation entry point. Never writes inside the archive."""
import argparse
import json
import platform
from pathlib import Path
import importlib.metadata
import hashlib
import pandas as pd
from scripts.Error_detector import GeneralErrorDetector
from .build_dataset import build
from . import association_analysis, family_prevalence, conditional_reliability, cleanup_ablation
from .audit_history import audit
from .source_evidence import EvidenceIndex
from .protocol_audit import analyze as protocol_audit
from validation.sample_annotations import sample


def run(args):
    output = args.output.resolve()
    archive = args.input.resolve()
    if output == archive or archive in output.parents:
        raise ValueError('Revision output must be outside the source archive')
    output.mkdir(parents=True, exist_ok=True)
    frozen_review = args.frozen_review.resolve()
    if output == frozen_review or frozen_review in output.parents or (output / 'agent_review').exists():
        raise ValueError('Choose a fresh version directory; never overwrite a frozen study')
    records = build(args.input, output)
    print(f'Reconciled {len(records)} generations', flush=True)
    metrics, schemas, evidence_rows, recovered_rows = [], [], [], []
    evidence_index = EvidenceIndex()
    for i, row in enumerate(records):
        detector = GeneralErrorDetector(token_limit=row['token_limit'])
        schema = detector._find_schema(row)
        schemas.append(schema)
        # Persist recovered schema in the blind sample without altering archive.
        row['schema'] = schema
        result = {k: row.get(k) for k in ['run_id', 'row_id', 'dataset', 'model', 'method', 'source_file', 'source_line']}
        result['schema_source'] = row.get('schema_source')
        result.update(detector.detect(row))
        result.update({f'legacy_{key}': value for key, value in row.items() if key == 'total_errors'})
        result.update({k: v for k, v in row.items() if k.startswith('legacy_')})
        result.update(row.get('characteristics') or {})
        result.update({f'archived_characteristic_{k}': v for k, v in (row.get('characteristics') or {}).items()})
        result.update(row['revision_characteristics'])
        if row['dataset'] == 'ARQA':
            evidence, recovered = evidence_index.assess(row)
            evidence_rows.append({k: row[k] for k in ['run_id', 'row_id', 'dataset', 'model', 'method']} | evidence)
            result.update(evidence)
            if recovered is not None:
                recovered_rows.append(dict(run_id=row['run_id'], row_id=row['row_id'], **recovered))
        metrics.append(result)
        if (i + 1) % 2000 == 0:
            print(f'Evaluated {i + 1} generations', flush=True)
    frame = pd.DataFrame(metrics)
    frame.to_csv(output / 'normalized_errors.csv', index=False)
    pd.DataFrame(evidence_rows).to_csv(output / 'arqa_source_grounding.csv', index=False)
    with (output / 'arqa_recovered_context.jsonl').open('w', encoding='utf-8') as handle:
        for row in recovered_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')
    protocol_audit(records, frame, output)
    print('Computing family prevalence and paired prompting effects', flush=True)
    family_prevalence.analyze(frame, output, args.bootstrap)
    conditional_reliability.analyze(frame, output)
    hypotheses = json.loads(args.hypotheses.read_text(encoding='utf-8'))
    print('Computing dataset-specific clustered Spearman intervals', flush=True)
    association_analysis.analyze(frame, output, hypotheses, args.bootstrap)
    print('Computing paired cleanup ablation', flush=True)
    cleanup_ablation.analyze(records, schemas, output, args.bootstrap)
    # Frozen labels/sampling remain tied to the original source snapshot.
    # Do not regenerate challenge samples while evaluating revised detectors.
    if args.new_annotation_sample:
        sample(records, frame, output)
    score_frozen_review(frame, frozen_review, output)
    audit(records, output)
    reconciliation = pd.read_csv(output / 'source_reconciliation.csv')
    for row in reconciliation.itertuples():
        source = Path(row.source_file)
        for path, digest in [(source, row.responses_sha256),
                             (source.with_name('manifest.json'), row.manifest_sha256),
                             (source.with_name('full_error_analysis.csv'), row.legacy_errors_sha256)]:
            if pd.notna(digest) and hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError(f'Archive changed during analysis: {path}')
    metadata = dict(detector_version='eacl-v2', bootstrap=args.bootstrap, seed=42,
        hypotheses=hypotheses, python=platform.python_version(),
        packages={p: importlib.metadata.version(p) for p in ['numpy', 'pandas', 'scipy', 'jsonschema', 'pyarrow']},
        source_rows=len(records), output_directory=str(output),
        status='recomputed_after_agent_audit_requires_manuscript_review',
        review_kind='independent_agent_audit_not_human_validation',
        content_metric='dataset_specific_gold_proxy; source_grounding_separate',
        retrospective_contract_version='retrospective-v1', frozen_review=str(frozen_review))
    root = Path(__file__).resolve().parents[1]
    code_paths = sorted([*root.glob('analysis/*.py'), *root.glob('scripts/*.py'), *root.glob('validation/*.py')])
    metadata['implementation_sha256'] = {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                                         for path in code_paths}
    (output / 'analysis_manifest.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(f'Finished. Provisional reports: {output}', flush=True)


def score_frozen_review(frame, review, output):
    from validation.evaluate_annotations import evaluate
    key = pd.read_csv(review / 'inputs/annotation_key.csv', dtype={'row_id': str})
    labels = pd.read_csv(review / 'agent_reference_labels.csv')
    old = pd.read_csv(review / 'detector_vs_agent_reference_metrics.csv')
    scores = evaluate(labels, key, frame)
    scores['reference_kind'] = 'agent_generated_not_human_ground_truth'
    scores.to_csv(output / 'detector_vs_frozen_agent_reference.csv', index=False)
    identity = ['sample_type', 'family', 'weighted']
    old.merge(scores, on=identity, suffixes=('_v1', '_v2'), validate='one_to_one').to_csv(
        output / 'detector_audit_comparison.csv', index=False)
    if 'contract_valid' in frame:
        summary = frame.groupby(['dataset', 'model', 'method']).agg(n=('row_id', 'size'),
            eligible_n=('contract_valid', 'count'), contract_valid_n=('contract_valid', 'sum'),
            eligible_conformance=('contract_valid', 'mean'))
        summary.to_csv(output / 'contract_prevalence.csv')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('pipeline/outputs'))
    parser.add_argument('--output', type=Path, default=Path('reports/eacl_revision/v2'))
    parser.add_argument('--frozen-review', type=Path, default=Path('reports/eacl_revision/agent_review'))
    parser.add_argument('--new-annotation-sample', action='store_true', help='Opt in only for a separate new study.')
    parser.add_argument('--bootstrap', type=int, default=2000)
    parser.add_argument('--hypotheses', type=Path, default=Path(__file__).with_name('revision_hypotheses.json'))
    args = parser.parse_args()
    if args.bootstrap < 100:
        parser.error('--bootstrap must be at least 100')
    run(args)


if __name__ == '__main__':
    main()
