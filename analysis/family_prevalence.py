"""Eligible prevalence and within-input paired prompting contrasts."""
import itertools
import pandas as pd
from .common import CONDITION, FAMILIES, paired_effect, barplot


def analyze(frame, output, bootstrap=2000):
    rows, effects = [], []
    outcomes = [f'{f}_flag' for f in FAMILIES] + [c for c in frame if c.endswith('_rate')]
    if 'contract_non_conformance_flag' in frame:
        outcomes.append('contract_non_conformance_flag')
    for condition, group in frame.groupby(CONDITION):
        for family in FAMILIES:
            values = group[f'{family}_flag']
            detected = values.eq(True).sum()
            rows.append(dict(zip(CONDITION, condition), family=family, n=len(group),
                eligible_n=values.notna().sum(), detected_n=detected,
                detected_prevalence=detected / len(group),
                eligible_prevalence=values.mean() if values.notna().any() else None))
    prevalence = pd.DataFrame(rows)
    prevalence.to_csv(output / 'family_prevalence.csv', index=False)
    for (dataset, model), group in frame.groupby(['dataset', 'model']):
        for outcome in outcomes:
            pivot = group.pivot(index='row_id', columns='method', values=outcome)
            for before, after in itertools.combinations(sorted(pivot.columns), 2):
                result = paired_effect(pivot[before], pivot[after], bootstrap)
                effects.append(dict(dataset=dataset, model=model, outcome=outcome,
                    before=before, after=after, **result))
    pd.DataFrame(effects).to_csv(output / 'prompting_effects.csv', index=False)
    # Legacy count comparison is an explicitly separate appendix output.
    appendix = frame[CONDITION].copy()
    appendix['archived_total_errors'] = pd.to_numeric(frame.get('legacy_total_errors'), errors='coerce')
    appendix['recomputed_diagnostic_total'] = frame.total_errors
    appendix.groupby(CONDITION)[['archived_total_errors', 'recomputed_diagnostic_total']].agg(
        ['count', 'mean']).to_csv(output / 'appendix_legacy_totals.csv')
    for dataset, group in prevalence.groupby('dataset'):
        for family, cells in group.groupby('family'):
            barplot(cells, 'model', 'method', 'eligible_prevalence',
                    output / f'{dataset}_{family}_prevalence.png', 'Eligible detected prevalence')
    return prevalence
