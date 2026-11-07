"""Paired raw / outer-fence-only / complete-span ablation, without inner repair."""
import pandas as pd
from scripts.Error_detector import strip_code_fences, extract_json_candidate
from scripts.opportunity_metrics import evaluate
from .common import CONDITION, paired_effect


def conditions(raw):
    import re
    # Remove only a matched outer fence pair, never a lone opening fence.
    match = re.fullmatch(r'\s*```(?:json|python)?\s*\n?(.*?)\s*```\s*', raw, re.S | re.I)
    outer = strip_code_fences(raw) if match else raw
    candidate, _, _, complete = extract_json_candidate(raw)
    return {'raw': raw, 'outer_fence': outer, 'complete_span': candidate if complete else raw}


def analyze(records, schemas, output, bootstrap=2000):
    rows = []
    for row, schema in zip(records, schemas):
        for condition, text in conditions(str(row.get('raw_response') or '')).items():
            metrics = evaluate(text, row.get('gold_json_raw'), schema, row['dataset'])
            rows.append({k: row[k] for k in ['run_id', 'row_id', *CONDITION]} | dict(
                condition=condition, valid_parse=metrics['valid_parse'], schema_valid=metrics['schema_valid'],
                content_correct=metrics['content_correct'], contract_valid=metrics['contract_valid'],
                content_metric=metrics['content_metric']))
    frame = pd.DataFrame(rows)
    frame.to_csv(output / 'cleanup_ablation_results.csv', index=False)
    effects = []
    for condition_key, group in frame.groupby(CONDITION):
        for outcome in ['valid_parse', 'schema_valid', 'contract_valid', 'content_correct']:
            pivot = group.pivot(index=['run_id', 'row_id'], columns='condition', values=outcome)
            for cleaned in ['outer_fence', 'complete_span']:
                effects.append(dict(zip(CONDITION, condition_key), outcome=outcome, condition=cleaned,
                    **paired_effect(pivot.raw, pivot[cleaned], bootstrap)))
    pd.DataFrame(effects).to_csv(output / 'cleanup_ablation_deltas.csv', index=False)
