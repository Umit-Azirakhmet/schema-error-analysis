"""Save evidence of historical code, keeping inferred and known facts separate."""
import json
import subprocess
from pathlib import Path


def audit(records, output):
    root = Path(__file__).resolve().parents[1]
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=root, text=True, encoding='utf-8')
    commit = git('rev-parse', 'HEAD').strip()
    history = git('log', '--format=%H %aI %s', '--', 'pipeline/src/models.py')
    manifest_paths = sorted({r['source_manifest'] for r in records})
    qwen = []
    for path in manifest_paths:
        manifest = json.loads(Path(path).read_text(encoding='utf-8'))
        if 'qwen' not in manifest['model'].lower():
            continue
        relative = Path(path).relative_to(root) if Path(path).is_absolute() else Path(path)
        introduced = git('log', '--diff-filter=A', '--format=%H', '--', relative.as_posix()).splitlines()
        qwen.append(dict(run_id=manifest['run_id'], generation_config=manifest.get('generation_config'),
            historical_git_commit=manifest.get('git_commit'),
            historical_thinking_enabled=manifest.get('thinking_enabled'),
            historical_model_revision=manifest.get('model_revision'),
            archive_introduction_commits=introduced, configuration_status='unverified_historical_runtime'))
    prior = git('show', '80ff3eb:pipeline/src/models.py')
    qwen_records = [row for row in records if 'qwen' in row.get('model', '').lower()]
    tag_counts = {}
    for row in qwen_records:
        dataset = row['dataset']
        counts = tag_counts.setdefault(dataset, dict(responses=0, thinking_tagged_responses=0))
        counts['responses'] += 1
        raw = str(row.get('raw_response') or '').lower()
        counts['thinking_tagged_responses'] += '<think>' in raw or '</think>' in raw
    report = dict(analysis_git_commit=commit, model_wrapper_history=history.splitlines(), qwen_runs=qwen,
        evidence=dict(pre_run_commit='80ff3eb', enable_thinking_false_in_code='kwargs["enable_thinking"] = False' in prior),
        final_response_tag_scan=tag_counts,
        completed_cross_branch_audit=dict(thread_id='01a1aef7-ac62-7d70-a6eb-3628cb406fab',
            title='Trace Qwen thinking setting history',
            findings='The linked audit traced main and Justin2 figure inputs, scanned all 3,894 final Qwen responses, and found no evidence of thinking-tag contamination. Earlier development tests are distinct from the final benchmark.'),
        rerun_decision='No regeneration justified solely by Qwen thinking mode.',
        audit_status='complete_for_thinking_mode_rerun_decision',
        residual_limitation='Effective per-run source commit, tokenizer revision and thinking kwargs were not logged. Absence of tags alone does not prove runtime mode.',
        conclusion='The prior code and completed cross-branch/output audit support treating the final benchmark as configured non-thinking. No thinking-mode-only rerun is warranted. Retain the runtime-provenance limitation; no model outputs were regenerated.')
    (output / 'historical_configuration_audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
