"""Reproducible balanced blind sample, overlap assignment and separate challenge set."""
import pandas as pd
from analysis.common import CONDITION, FAMILIES


def sample(records, metrics, output, seed=42, per_cell=5):
    source = pd.DataFrame(records)
    sample_rows = []
    for condition, group in source.groupby(CONDITION):
        if len(group) < per_cell:
            raise ValueError(f'Insufficient annotation coverage: {condition}')
        picked = group.sample(n=per_cell, random_state=seed).copy()
        picked['population_n'] = len(group)
        picked['sample_n'] = per_cell
        picked['sampling_weight'] = len(group) / per_cell
        picked['double_annotate'] = [True, True] + [False] * (per_cell - 2)
        sample_rows.append(picked)
    balanced = pd.concat(sample_rows, ignore_index=True)
    balanced['sample_type'] = 'balanced'
    # Challenge examples are diagnostic only and have no population weight.
    keys = set(zip(balanced.run_id, balanced.row_id))
    challenge_keys = set()
    for family in FAMILIES:
        positive = metrics.loc[metrics[f'{family}_flag'].eq(True)]
        candidates = positive.loc[[key not in keys for key in zip(positive.run_id, positive.row_id)]]
        challenge_keys.update(zip(*[candidates.sample(n=min(10, len(candidates)), random_state=seed)[k]
                                    for k in ['run_id', 'row_id']]))
    challenge = source.loc[[key in challenge_keys for key in zip(source.run_id, source.row_id)]].copy()
    challenge['sample_type'] = 'challenge'
    challenge['sampling_weight'] = None
    challenge['double_annotate'] = True
    combined = pd.concat([balanced, challenge], ignore_index=True)
    # Shuffled opaque IDs conceal condition and automatic labels from annotators.
    combined = combined.sample(frac=1, random_state=seed).reset_index(drop=True)
    combined['annotation_id'] = [f'A{i:04}' for i in range(len(combined))]
    public = combined[['annotation_id', 'dataset', 'raw_response', 'gold_json_raw']].copy()
    public['schema'] = combined['schema'] if 'schema' in combined else None
    public['prompt'] = combined['prompt'] if 'prompt' in combined else None
    for family in FAMILIES:
        public[family] = ''
    public['notes'] = ''
    public.to_csv(output / 'annotation_sample.csv', index=False)
    combined[['annotation_id', 'run_id', 'row_id', *CONDITION, 'sample_type', 'sampling_weight',
              'population_n', 'sample_n', 'double_annotate']].to_csv(output / 'annotation_key.csv', index=False)
    # Blank template, never fabricated adjudicated labels.
    public[['annotation_id', *FAMILIES, 'notes']].to_csv(output / 'adjudicated_labels_template.csv', index=False)
