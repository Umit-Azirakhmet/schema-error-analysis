"""Shared deterministic revision analysis utilities."""
import numpy as np
import pandas as pd

FAMILIES = ['completion', 'syntax', 'envelope_contamination', 'schema_non_conformance', 'content_fidelity']
KEY = ['run_id', 'row_id']
CONDITION = ['dataset', 'model', 'method']


def load_metrics(path):
    """Nullable boolean dtypes must survive CSV round trips across chunk sizes."""
    columns = pd.read_csv(path, nrows=0).columns
    boolean_columns = [c for c in columns if c.endswith(('_flag', '_eligible')) or c in
        ['valid_parse', 'raw_valid_parse', 'is_complete', 'is_schema_assessable',
         'is_content_assessable', 'has_json_candidate', 'schema_valid', 'content_correct',
         'envelope_contamination_detected', 'strict_content_correct', 'contract_valid', 'contract_assessable']]
    return pd.read_csv(path, dtype={'row_id': str, **{c: 'boolean' for c in boolean_columns}}, low_memory=False)


def paired_effect(a, b, bootstrap=2000, seed=42):
    paired = pd.concat([a.rename('a'), b.rename('b')], axis=1).dropna()
    delta = (paired.b.astype(float) - paired.a.astype(float)).to_numpy()
    if not len(delta):
        return dict(n=0, difference=None, ci_low=None, ci_high=None)
    rng = np.random.default_rng(seed)
    means = np.array([rng.choice(delta, len(delta), replace=True).mean() for _ in range(bootstrap)])
    low, high = np.quantile(means, [.025, .975])
    return dict(n=len(delta), difference=delta.mean(), ci_low=low, ci_high=high)


def barplot(frame, index, column, value, path, ylabel):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    table = frame.pivot_table(index=index, columns=column, values=value, aggfunc='mean')
    if table.empty:
        return
    ax = table.plot.bar(figsize=(12, 6))
    ax.set_ylabel(ylabel)
    ax.figure.tight_layout()
    ax.figure.savefig(path, dpi=160)
    plt.close(ax.figure)
