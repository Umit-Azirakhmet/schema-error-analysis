"""Forest plot with input-cluster bootstrap intervals.

Run analysis.run_revision first. Historical published images remain unchanged.
"""
import argparse
import sys
from pathlib import Path
import pandas as pd

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports', type=Path, default=Path(__file__).resolve().parents[1] / 'reports/eacl_revision')
    parser.add_argument('--bootstrap', type=int, default=2000)
    args = parser.parse_args()
    output = args.reports
    source = output / 'correlations_bootstrap_ci.csv'
    if not source.exists():
        parser.error('Run python -m analysis.run_revision before generating revision figures')
    frame = pd.read_csv(source, dtype={'row_id': str})
    from analysis.association_analysis import plots
    plots(frame, output)


if __name__ == '__main__':
    main()
