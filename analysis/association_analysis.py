"""Individual-feature Spearman estimates with input-cluster bootstrap intervals."""
import json
import numpy as np
import pandas as pd
from scipy.special import stdtr


def rankdata(values):
    """Average ranks for ties, as used by Spearman's coefficient."""
    return pd.Series(values).rank(method='average').to_numpy(float)


def rho(x, y):
    if len(x) < 3 or len(np.unique(x)) < 2 or len(np.unique(y)) < 2:
        return np.nan
    a, b = rankdata(x), rankdata(y)
    a = a - a.mean()
    b = b - b.mean()
    return np.dot(a, b) / np.sqrt(np.dot(a, a) * np.dot(b, b))


def clustered_ci(group, feature, outcome, bootstrap=2000, seed=42):
    """Resample input IDs, copying ALL their model/prompt observations together."""
    clean = group[['row_id', feature, outcome]].dropna()
    clean = clean.copy()
    clean[feature] = pd.to_numeric(clean[feature], errors='coerce')
    clean[outcome] = pd.to_numeric(clean[outcome], errors='coerce')
    clean = clean.replace([np.inf, -np.inf], np.nan).dropna()
    x, y = clean[feature].to_numpy(float), clean[outcome].to_numpy(float)
    clusters = [np.asarray(indices) for indices in clean.reset_index(drop=True).groupby('row_id').indices.values()]
    estimate = rho(x, y)
    result = dict(n=len(clean), eligible_n=len(clean), total_n=len(group), input_n=len(clusters),
                  rho=estimate, ci_low=np.nan, ci_high=np.nan, bootstrap_valid_n=0, p_value=np.nan)
    if not np.isfinite(estimate) or len(clusters) < 3:
        return result
    # Same asymptotic Student-t approximation used for Spearman inference.
    t = estimate * np.sqrt((len(x) - 2) / max(1e-15, 1 - estimate ** 2))
    result['p_value'] = 2 * stdtr(len(x) - 2, -abs(t))
    rng = np.random.default_rng(seed)
    estimates = []
    for _ in range(bootstrap):
        indices = np.concatenate([clusters[i] for i in rng.integers(0, len(clusters), len(clusters))])
        value = rho(x[indices], y[indices])
        if np.isfinite(value):
            estimates.append(value)
    result['bootstrap_valid_n'] = len(estimates)
    if len(estimates) >= .9 * bootstrap:
        result['ci_low'], result['ci_high'] = np.quantile(estimates, [.025, .975])
    return result


def bh_adjust(values):
    values = np.asarray(values, dtype=float)
    output = np.full(len(values), np.nan)
    valid = np.flatnonzero(np.isfinite(values))
    order = valid[np.argsort(values[valid])]
    if len(order):
        output[order] = np.minimum(1, np.minimum.accumulate(
            (values[order] * len(order) / np.arange(1, len(order) + 1))[::-1])[::-1])
    return output


def analyze(frame, output, hypotheses, bootstrap=2000):
    rows = []
    for dataset, group in frame.groupby('dataset'):
        strata = [('pooled', 'all', 'all', group)] + [
            ('within_condition', model, method, cell)
            for (model, method), cell in group.groupby(['model', 'method'])]
        for hypothesis in hypotheses:
            feature, outcome = hypothesis['feature'], hypothesis['outcome']
            if feature not in group or outcome not in group:
                raise ValueError(f'Unknown hypothesis columns: {feature}, {outcome}')
            for scope, model, method, cell in strata:
                rows.append(dict(dataset=dataset, feature=feature, outcome=outcome,
                    scope=scope, model=model, method=method, hypothesis_status=hypothesis.get('status', 'exploratory'),
                    **clustered_ci(cell, feature, outcome, bootstrap)))
    results = pd.DataFrame(rows)
    # P-values assume independent responses only within a condition. Pooled
    # response-level p-values are deliberately suppressed due to clustering.
    results.loc[results.scope.eq('pooled'), 'p_value'] = np.nan
    results['q_value_bh'] = bh_adjust(results.p_value)
    results.to_csv(output / 'correlations_by_dataset.csv', index=False)
    results.to_csv(output / 'correlations_bootstrap_ci.csv', index=False)
    plots(results, output)
    return results


def plots(results, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    pooled = results.loc[results.scope.eq('pooled')].copy()
    pooled['pair'] = pooled.feature + ' / ' + pooled.outcome
    for dataset, group in pooled.groupby('dataset'):
        table = group.pivot(index='feature', columns='outcome', values='rho')
        fig, ax = plt.subplots(figsize=(10, 5))
        im = ax.imshow(np.ma.masked_invalid(table.to_numpy(float)), vmin=-1, vmax=1, cmap='RdBu_r', aspect='auto')
        ax.set_xticks(range(len(table.columns)), table.columns, rotation=25, ha='right')
        ax.set_yticks(range(len(table.index)), table.index)
        ax.set_title(f'{dataset}: exploratory Spearman associations')
        fig.colorbar(im, ax=ax, label='Spearman rho')
        fig.tight_layout()
        fig.savefig(output / f'{dataset}_spearman_heatmap.png', dpi=160)
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(12, max(5, len(pooled) * .5)))
    for i, row in enumerate(pooled.itertuples()):
        if np.isfinite(row.rho):
            ax.plot(row.rho, i, 'o', color='black')
            ax.hlines(i, row.ci_low, row.ci_high, color='steelblue')
    ax.set_yticks(range(len(pooled)), pooled.dataset + ': ' + pooled.pair)
    ax.set_xlim(-1, 1)
    ax.axvline(0, color='gray', linestyle='--')
    ax.set_xlabel('Spearman rho with input-cluster percentile 95% CI')
    fig.tight_layout()
    fig.savefig(output / 'correlations_forest_plot.png', dpi=160)
    plt.close(fig)
