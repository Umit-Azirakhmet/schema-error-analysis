"""Audit archived prompt examples and observed token limits without regeneration."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

import pandas as pd


def evidence_arrays(text):
    rows = []
    for match in re.finditer(r'"(table_cells|text_spans)"\s*:\s*', text):
        fragment = text[match.end():]
        try:
            value, _ = json.JSONDecoder().raw_decode(fragment)
            valid = isinstance(value, list) and all(isinstance(v, dict) for v in value)
            reason = 'array_of_objects' if valid else 'not_an_array_of_objects'
        except ValueError:
            valid, reason = False, 'invalid_json_example'
        rows.append(dict(field=match.group(1), valid=valid, reason=reason,
                         position=match.start(), excerpt=fragment[:160]))
    return rows


def analyze(records, metrics, output):
    history = []
    paths = ['pipeline/prompts/prompts.md', 'pipeline/prompts/prompting.md']
    commits = subprocess.check_output(['git', 'log', '--all', '--format=%H', '--', *paths], text=True).splitlines()
    for commit in dict.fromkeys(commits):
        date = subprocess.check_output(['git', 'show', '-s', '--format=%aI', commit], text=True).strip()
        for path in paths:
            result = subprocess.run(['git', 'show', f'{commit}:{path}'], text=True, encoding='utf-8', capture_output=True)
            if result.returncode:
                continue
            for example in evidence_arrays(result.stdout):
                history.append(dict(commit=commit, commit_date=date, source_file=path,
                    source_sha256=hashlib.sha256(result.stdout.encode()).hexdigest(), **example))
    pd.DataFrame(history).to_csv(output / 'historical_prompt_examples.csv', index=False)
    archived = []
    for row in records:
        if row['dataset'] != 'ARQA':
            continue
        examples = evidence_arrays(str(row.get('prompt') or ''))
        archived.append({k: row[k] for k in ['run_id', 'row_id', 'model', 'method']} | dict(
            prompt_available=bool(row.get('prompt')), example_n=len(examples),
            malformed_example_n=sum(not x['valid'] for x in examples)))
    pd.DataFrame(archived).to_csv(output / 'archived_arqa_prompt_audit.csv', index=False)
    budget = []
    for row in records:
        tokens = row.get('output_tokens')
        budget.append({k: row[k] for k in ['run_id', 'row_id', 'dataset', 'model', 'method']} | dict(
            output_tokens=tokens, token_limit=row['token_limit'],
            at_token_limit=None if tokens is None else tokens >= row['token_limit'],
            gold_characters=len(str(row.get('gold_json_raw') or '')),
            raw_characters=len(str(row.get('raw_response') or '')),
            nl_part_characters=len(str(row.get('nl_part') or '')),
            json_part_characters=len(str(row.get('json_part') or ''))))
    detail = pd.DataFrame(budget).merge(metrics[['run_id', 'row_id', 'valid_parse', 'is_complete',
        'completion_rule']], on=['run_id', 'row_id'], validate='one_to_one')
    detail.to_csv(output / 'token_budget_records.csv', index=False)
    summaries = []
    for condition, group in detail.groupby(['dataset', 'model', 'method']):
        at_cap = group.at_token_limit.eq(True)
        summaries.append(dict(zip(['dataset', 'model', 'method'], condition), n=len(group),
            token_count_available_n=group.output_tokens.notna().sum(), at_limit_n=int(at_cap.sum()),
            at_limit_rate=float(at_cap.mean()),
            parseable_at_limit_n=int((at_cap & group.valid_parse.eq(True)).sum()),
            incomplete_at_limit_n=int((at_cap & group.is_complete.eq(False)).sum()),
            unknown_at_limit_n=int((at_cap & group.is_complete.isna()).sum()),
            max_output_tokens=group.output_tokens.max(),
            gold_characters_median=group.gold_characters.median(),
            gold_characters_max=group.gold_characters.max(),
            nl_characters_median=group.nl_part_characters.median()))
    pd.DataFrame(summaries).to_csv(output / 'token_budget_summary.csv', index=False)
    result = dict(historical_examples=len(history), historical_invalid_examples=sum(not x['valid'] for x in history),
        archived_arqa_prompts=sum(x['prompt_available'] for x in archived),
        archived_arqa_missing_prompts=sum(not x['prompt_available'] for x in archived),
        archived_arqa_malformed_examples=sum(x['malformed_example_n'] for x in archived),
        limitations=['Committed prompt history is not proof of a per-run checkout.',
            'Missing prompts cannot establish whether malformed examples were shown.',
            'Character lengths are not token counts; gold fit cannot be inferred from characters.',
            'NL-to-format uses one shared generation budget for prose plus JSON.',
            'Token-limit hits alone do not establish semantic truncation.'])
    (output / 'protocol_audit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result
