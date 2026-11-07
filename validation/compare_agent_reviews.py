"""Prepare blinded conflicts and score an explicitly agent-generated reference.

No source annotations or original human-named artifacts are overwritten.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd

from analysis.common import FAMILIES, load_metrics
from validation.evaluate_annotations import validate_labels, agreement, evaluate


def load_reviews(directory):
    first = pd.read_csv(directory / 'reviewer_a.csv', keep_default_na=False)
    second = pd.concat([pd.read_csv(directory / name, keep_default_na=False)
                        for name in ['reviewer_b.csv', 'reviewer_c.csv']], ignore_index=True)
    validate_labels(first)
    validate_labels(second)
    if set(first.annotation_id) != set(second.annotation_id):
        raise ValueError('Both independent passes must cover the identical sample')
    return first.set_index('annotation_id'), second.set_index('annotation_id')


def prepare(reports):
    directory = reports / 'agent_review'
    source_hash = hashlib.sha256((reports / 'annotation_sample.csv').read_bytes()).hexdigest()
    for name in ['reviewer_a', 'reviewer_b', 'reviewer_c']:
        provenance = json.loads((directory / f'{name}_provenance.json').read_text(encoding='utf-8'))
        if provenance.get('source_sha256') != source_hash:
            raise ValueError(f'{name} reviewed a different source snapshot')
        review_hash = hashlib.sha256((directory / f'{name}.csv').read_bytes()).hexdigest()
        if provenance.get('review_csv_sha256') != review_hash:
            raise ValueError(f'{name} labels changed after provenance was written')
    first, second = load_reviews(directory)
    source = pd.read_csv(reports / 'annotation_sample.csv', keep_default_na=False).set_index('annotation_id')
    if set(source.index) != set(first.index):
        raise ValueError('Review coverage differs from frozen source sample')
    inputs = directory / 'inputs'
    inputs.mkdir(exist_ok=True)
    for name in ['annotation_sample.csv', 'annotation_key.csv', 'normalized_errors.csv']:
        target = inputs / name
        if target.exists() and target.read_bytes() != (reports / name).read_bytes():
            raise ValueError(f'Frozen audit input differs: {name}')
        if not target.exists():
            shutil.copyfile(reports / name, target)
    packets, conflicts = [], []
    for identity in source.index:
        disputed = [f for f in FAMILIES if first.at[identity, f] != second.at[identity, f]]
        if not disputed:
            continue
        packets.append(dict(annotation_id=identity, source=source.loc[identity].to_dict(),
            disputed_families=disputed,
            reviewer_a=first.loc[identity].to_dict(), reviewer_second=second.loc[identity].to_dict()))
        conflicts.extend(dict(annotation_id=identity, family=f, first=first.at[identity, f],
                              second=second.at[identity, f]) for f in disputed)
    with (directory / 'adjudication_packet.jsonl').open('w', encoding='utf-8') as handle:
        for packet in packets:
            handle.write(json.dumps(packet, ensure_ascii=False) + '\n')
    pd.DataFrame(conflicts, columns=['annotation_id', 'family', 'first', 'second']).to_csv(
        directory / 'disagreements.csv', index=False)
    return len(packets), len(conflicts)


def finalize(reports):
    directory = reports / 'agent_review'
    inputs = directory / 'inputs'
    first, second = load_reviews(directory)
    disputes = pd.read_csv(directory / 'disagreements.csv')
    resolved = pd.read_csv(directory / 'adjudicator.csv', keep_default_na=False)
    validate_labels(resolved)
    resolved = resolved.set_index('annotation_id')
    if set(resolved.index) != set(disputes.annotation_id):
        raise ValueError('Adjudicator must cover exactly the disputed responses')
    final = first.copy()
    log = []
    for row in disputes.itertuples():
        label = resolved.at[row.annotation_id, row.family]
        final.at[row.annotation_id, row.family] = label
        log.append(dict(annotation_id=row.annotation_id, family=row.family,
                        first=row.first, second=row.second, resolved=label,
                        rationale=resolved.at[row.annotation_id, 'notes']))
    for identity in final.index:
        final.at[identity, 'notes'] = ('Agent reference. First: ' + first.at[identity, 'notes'] +
            ' | Second: ' + second.at[identity, 'notes'] +
            (' | Adjudication: ' + resolved.at[identity, 'notes'] if identity in resolved.index else ''))
    final = final.reset_index()
    final.to_csv(directory / 'agent_reference_labels.csv', index=False)
    pd.DataFrame(log).to_csv(directory / 'adjudication_log.csv', index=False)
    key = pd.read_csv(inputs / 'annotation_key.csv', dtype={'row_id': str})
    metrics = evaluate(final, key, load_metrics(inputs / 'normalized_errors.csv'))
    metrics['reference_kind'] = 'agent_generated_not_human_ground_truth'
    metrics.to_csv(directory / 'detector_vs_agent_reference_metrics.csv', index=False)
    agreement_rows = []
    for sample_type, group in key.groupby('sample_type'):
        ids = set(group.annotation_id)
        result = agreement(first.loc[first.index.isin(ids)].reset_index(),
                           second.loc[second.index.isin(ids)].reset_index())
        for i, family in enumerate(result.family):
            a, b = first.loc[first.index.isin(ids), family], second.loc[second.index.isin(ids), family]
            b = b.reindex(a.index)
            assessed = a.ne('not-assessable') & b.ne('not-assessable')
            result.loc[i, 'both_assessable_n'] = int(assessed.sum())
            result.loc[i, 'both_unassessable_n'] = int((a.eq('not-assessable') & b.eq('not-assessable')).sum())
            result.loc[i, 'assessable_agreement'] = (a[assessed] == b[assessed]).mean() if assessed.any() else None
        result['sample_type'] = sample_type
        result['review_kind'] = 'inter_agent'
        agreement_rows.append(result)
    pd.concat(agreement_rows).to_csv(directory / 'inter_agent_agreement.csv', index=False)
    metadata = dict(status='complete_agent_audit_not_human_validation',
        distinct_responses=len(final), independent_judgments_per_response=2,
        first_pass_agents=['reviewer_a', 'reviewer_b', 'reviewer_c'],
        second_pass_partition={'reviewer_b': 'A0000-A0099', 'reviewer_c': 'A0100-A0229'},
        exact_model_diversity='not_established; reviewers report serving snapshot unavailable',
        disagreement_responses=disputes.annotation_id.nunique(), disagreement_labels=len(disputes),
        limitation='Process-independent agent judgments may share model biases; no human validation or human semantic ground truth.',
        source_sha256=hashlib.sha256((inputs / 'annotation_sample.csv').read_bytes()).hexdigest(),
        frozen_input_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs.glob('*.csv')},
        adjudication_csv_sha256=hashlib.sha256((directory / 'adjudicator.csv').read_bytes()).hexdigest(),
        coordinator_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        input_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('reviewer_*.csv')})
    (directory / 'audit_manifest.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'finalize'])
    parser.add_argument('--reports', type=Path, default=Path('reports/eacl_revision'))
    args = parser.parse_args()
    print(prepare(args.reports) if args.stage == 'prepare' else finalize(args.reports))


if __name__ == '__main__':
    main()
