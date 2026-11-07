"""Reconcile archived runs and write immutable-source, versioned analysis data."""
import argparse
import csv
import hashlib
import itertools
import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
from scripts.Error_detector import GeneralErrorDetector
from scripts.gold_json_analysis import analyze_gold_json_structure
from scripts.opportunity_metrics import strict_parse


@lru_cache(maxsize=4096)
def revision_characteristics(gold_raw):
    if not strict_parse(gold_raw)[0]:
        return {}
    return analyze_gold_json_structure(gold_raw)


def build(input_dir, output_dir, expected_conditions=36):
    output_dir.mkdir(parents=True, exist_ok=True)
    records, reconciliation, seen, input_gold = [], [], {}, {}
    for manifest_path in sorted(input_dir.rglob('manifest.json')):
        if any(part.lower() == 'sample' for part in manifest_path.relative_to(input_dir).parts):
            continue
        response_path = manifest_path.with_name('responses.jsonl')
        if not response_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        legacy_path = manifest_path.with_name('full_error_analysis.csv')
        legacy = {}
        if legacy_path.exists():
            with legacy_path.open(encoding='utf-8', newline='') as handle:
                for row in csv.DictReader(handle):
                    key = str(row['row_id'])
                    if key in legacy:
                        raise ValueError(f'Duplicate legacy row: {legacy_path}: {key}')
                    legacy[key] = row
        count = duplicates = accepted = 0
        with response_path.open(encoding='utf-8') as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                count += 1
                for field in ('run_id', 'dataset', 'model', 'method'):
                    if field in row and row[field] != manifest[field]:
                        raise ValueError(f'Manifest mismatch: {response_path}:{line_number}: {field}')
                    row[field] = manifest[field]
                if row.get('row_id') is None:
                    raise ValueError(f'Missing row ID: {response_path}:{line_number}')
                row['row_id'] = str(row['row_id'])
                key = row['run_id'], row['row_id']
                encoded = json.dumps(row, sort_keys=True)
                if key in seen:
                    if seen[key] != encoded:
                        raise ValueError(f'Conflicting generation key: {key}')
                    duplicates += 1
                    continue
                seen[key] = encoded
                explicit_schema = row.get('schema') is not None
                row['schema'] = GeneralErrorDetector()._find_schema(row)
                row['schema_source'] = ('record' if explicit_schema else 'archived_prompt') if row['schema'] is not None else None
                row['revision_characteristics'] = revision_characteristics(row.get('gold_json_raw'))
                instance = row['dataset'], row['row_id']
                if instance in input_gold and input_gold[instance] != row.get('gold_json_raw'):
                    raise ValueError(f'Gold differs across conditions: {instance}')
                input_gold[instance] = row.get('gold_json_raw')
                row.update(source_file=response_path.as_posix(), source_line=line_number,
                           source_manifest=manifest_path.as_posix(),
                           token_limit=manifest.get('generation_config', {}).get('max_new_tokens', 4096))
                row.update({f'legacy_{k}': v for k, v in legacy.get(row['row_id'], {}).items()
                            if k.endswith('_count') or k.endswith('_errors') or k.startswith(('arqa_', 'deepjson_', 'schematojson_'))})
                records.append(row)
                accepted += 1
        expected = manifest['total_rows']
        if count != expected:
            raise ValueError(f'Source reconciliation failed: {response_path}: {count} != {expected}')
        reconciliation.append(dict(run_id=manifest['run_id'], dataset=manifest['dataset'],
            model=manifest['model'], method=manifest['method'], source_rows=count,
            unique_rows=accepted, exact_duplicates=duplicates, manifest_total=expected,
            source_file=response_path.as_posix(),
            responses_sha256=hashlib.sha256(response_path.read_bytes()).hexdigest(),
            legacy_errors_sha256=hashlib.sha256(legacy_path.read_bytes()).hexdigest() if legacy_path.exists() else None,
            manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest()))
    if not records:
        raise ValueError('No complete runs found')
    rec = pd.DataFrame(reconciliation)
    conditions = ['dataset', 'model', 'method']
    if rec.duplicated(conditions).any():
        raise ValueError('Multiple runs per condition; select an explicit archive snapshot')
    coverage = set(map(tuple, rec[conditions].values))
    grid = set(itertools.product(*(sorted(rec[c].unique()) for c in conditions)))
    if len(coverage) != expected_conditions or coverage != grid:
        raise ValueError(f'Condition coverage: {len(coverage)}; missing {sorted(grid - coverage)}')
    row_sets = {}
    for row in records:
        condition = tuple(row[c] for c in conditions)
        row_sets.setdefault(condition, set()).add(row['row_id'])
    for dataset in rec.dataset.unique():
        sets = [ids for condition, ids in row_sets.items() if condition[0] == dataset]
        if any(ids != sets[0] for ids in sets):
            raise ValueError(f'Unmatched input coverage across conditions: {dataset}')
    rec.to_csv(output_dir / 'source_reconciliation.csv', index=False)
    # Serialize nested data explicitly so Arrow does not infer incompatible structs.
    frame = pd.DataFrame(records)
    for col in frame:
        if any(isinstance(v, (dict, list)) for v in frame[col]):
            frame[col] = frame[col].map(lambda v: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
    frame.to_parquet(output_dir / 'canonical_generations.parquet', index=False)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('pipeline/outputs'))
    parser.add_argument('--output', type=Path, default=Path('reports/eacl_revision'))
    args = parser.parse_args()
    print(f'Reconciled {len(build(args.input, args.output))} generations')


if __name__ == '__main__':
    main()
