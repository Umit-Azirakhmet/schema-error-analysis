"""ARQA funnel using observable completion and strict gold-match proxy."""
import pandas as pd
from .common import CONDITION, barplot


def funnel(frame, conformance_column='schema_valid'):
    rows = []
    for condition, group in frame.loc[frame.dataset.eq('ARQA')].groupby(CONDITION):
        active = pd.Series(True, index=group.index)
        for stage, column in [('completed', 'is_complete'), ('parseable', 'valid_parse'),
                              (conformance_column, conformance_column), ('content_correct_proxy', 'content_correct')]:
            denominator = int(active.sum())
            assessed = active & group[column].notna()
            passed = active & group[column].eq(True)
            numerator = int(passed.sum())
            eligible = int(assessed.sum())
            rows.append(dict(zip(CONDITION, condition), stage=stage, numerator=numerator,
                denominator=denominator, eligible_n=eligible, unassessable_n=denominator - eligible,
                conditional_rate=numerator / eligible if eligible else None,
                transition_rate=numerator / denominator if denominator and eligible else None,
                all_generation_n=len(group), all_generation_rate=numerator / len(group) if eligible else None))
            active = passed
    return pd.DataFrame(rows)


def analyze(frame, output):
    result = funnel(frame)
    result.to_csv(output / 'conditional_reliability.csv', index=False)
    template = funnel(frame, 'contract_valid') if 'contract_valid' in frame else result
    template.to_csv(output / 'arqa_template_reliability.csv', index=False)
    diagnostics = []
    for condition, group in frame.loc[frame.dataset.eq('ARQA')].groupby(CONDITION):
        scopes = {'all_generations': pd.Series(True, index=group.index),
                  'completed': group.is_complete.eq(True),
                  'completed_parseable': group.is_complete.eq(True) & group.valid_parse.eq(True)}
        if 'contract_valid' in group:
            scopes['completed_parseable_template_valid'] = scopes['completed_parseable'] & group.contract_valid.eq(True)
        for scope, selected in scopes.items():
            for field in ['schema_non_conformance_flag', 'content_fidelity_flag',
                          'contract_non_conformance_flag', 'grounding_flag']:
                if field not in group:
                    continue
                values = group.loc[selected, field]
                n, eligible = len(values), int(values.notna().sum())
                errors = int(values.eq(True).sum())
                diagnostics.append(dict(zip(CONDITION, condition), scope=scope, outcome=field,
                    n=n, eligible_n=eligible, detected_n=errors, unassessable_n=n - eligible,
                    eligible_error_rate=errors / eligible if eligible else None,
                    detected_prevalence=errors / n if n else None))
    pd.DataFrame(diagnostics).to_csv(output / 'arqa_conditional_diagnostics.csv', index=False)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    contract_stage = 'contract_valid' if 'contract_valid' in frame else 'schema_valid'
    stages = ['completed', 'parseable', contract_stage, 'content_correct_proxy']
    table = template.pivot_table(index='stage', columns='model', values='all_generation_rate').reindex(stages)
    ax = table.plot.bar(figsize=(12, 6), rot=0)
    for i, stage in enumerate(stages):
        if table.loc[stage].isna().all():
            ax.text(i, .1, 'Unassessable', ha='center', color='dimgray', rotation=90)
    ax.set_xticklabels(['Observable completion', 'Parseable JSON', 'Retrospective template valid', 'Exact gold match proxy'])
    ax.set_ylabel('Fraction of all generations')
    ax.set_title('ARQA retrospective template funnel (methods averaged; formal schema unavailable)')
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=8)
    ax.figure.tight_layout()
    ax.figure.savefig(output / 'ARQA_reliability_funnel.png', dpi=160)
    plt.close(ax.figure)
    return result
