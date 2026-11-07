"""Family prevalence and paired prompting effects replace raw-count headlines.

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
    source = output / 'normalized_errors.csv'
    if not source.exists():
        parser.error('Run python -m analysis.run_revision before generating revision figures')
    from analysis.common import load_metrics
    frame = load_metrics(source)
    from analysis.family_prevalence import analyze
    analyze(frame, output, args.bootstrap)


if __name__ == '__main__':
    main()
