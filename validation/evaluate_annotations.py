"""Score reference labels; the caller must disclose human or agent provenance."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from analysis.common import FAMILIES, load_metrics

LABELS = {'yes': True, 'no': False, 'not-assessable': None}


def validate_labels(labels):
    if labels.annotation_id.duplicated().any():
        raise ValueError('Duplicate annotation IDs')
    for family in FAMILIES:
        if not labels[family].isin(LABELS).all():
            raise ValueError(f'Incomplete/invalid labels for {family}')


def agreement(first, second):
    validate_labels(first)
    validate_labels(second)
    merged = first.merge(second, on='annotation_id', suffixes=('_a', '_b'), validate='one_to_one')
    rows = []
    for family in FAMILIES:
        a, b = merged[family + '_a'], merged[family + '_b']
        observed = (a == b).mean()
        chance = sum(a.eq(label).mean() * b.eq(label).mean() for label in LABELS)
        rows.append(dict(family=family, n=len(merged), agreement=observed,
                         cohen_kappa=(observed - chance) / (1 - chance) if chance < 1 else None))
    return pd.DataFrame(rows)


def evaluate(labels, key, automatic):
    validate_labels(labels)
    if set(labels.annotation_id) != set(key.annotation_id):
        raise ValueError('Adjudicated labels must cover the complete keyed sample')
    source_keys = set(zip(automatic.run_id, automatic.row_id))
    if not set(zip(key.run_id, key.row_id)).issubset(source_keys):
        raise ValueError('Automatic report is missing keyed sample generations')
    merged = labels.merge(key, on='annotation_id', validate='one_to_one').merge(
        automatic, on=['run_id', 'row_id'], validate='one_to_one')
    rows = []
    for sample_type, group in merged.groupby('sample_type'):
        for family in FAMILIES:
            truth = group[family].map(LABELS)
            prediction = group[family + '_flag']
            valid = truth.notna() & prediction.notna()
            for weighted in ([False, True] if sample_type == 'balanced' else [False]):
                weights = group.sampling_weight.astype(float) if weighted else pd.Series(1., index=group.index)
                yes, detected = truth.eq(True), prediction.eq(True)
                tp = weights[valid & yes & detected].sum()
                fp = weights[valid & ~yes & detected].sum()
                fn = weights[valid & yes & ~detected].sum()
                rows.append(dict(sample_type=sample_type, family=family, weighted=weighted,
                    n=len(group), eligible_n=valid.sum(), reference_unassessable_n=truth.isna().sum(),
                    automatic_unassessable_n=prediction.isna().sum(),
                    tp=tp, fp=fp, fn=fn, precision=tp/(tp+fp) if tp+fp else None,
                    recall=tp/(tp+fn) if tp+fn else None, f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None))
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--labels', type=Path, required=True)
    parser.add_argument('--reports', type=Path, default=Path('reports/eacl_revision'))
    parser.add_argument('--annotator-a', type=Path)
    parser.add_argument('--annotator-b', type=Path)
    args = parser.parse_args()
    key = pd.read_csv(args.reports / 'annotation_key.csv', dtype={'row_id': str})
    automatic = load_metrics(args.reports / 'normalized_errors.csv')
    result = evaluate(pd.read_csv(args.labels), key, automatic)
    result.to_csv(args.reports / 'detector_validation_metrics.csv', index=False)
    if args.annotator_a and args.annotator_b:
        agreement(pd.read_csv(args.annotator_a), pd.read_csv(args.annotator_b)).to_csv(
            args.reports / 'annotator_agreement.csv', index=False)


if __name__ == '__main__':
    main()
