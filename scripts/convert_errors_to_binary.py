#!/usr/bin/env python3
"""
Convert error count columns to binary (0/1) indicating error presence.

Forces conversion of ALL non‑identifier columns to numeric, then binary.

Usage:
  python scripts/convert_errors_to_binary.py --input "pipeline/outputs/full error analysis - combined_full_error_analysis.csv" --output "pipeline/outputs/full_error_analysis_binary.csv"
"""

import pandas as pd
from pathlib import Path
import argparse
import sys

# Columns to keep as identifiers (do not convert)
IDENTIFIER_COLS = ["row_id", "dataset", "model", "method", "run_id"]


def convert_to_binary(input_path, output_path):
    df = pd.read_csv(input_path)
    print(f"✅ Loaded {len(df)} rows from {input_path}")

    # Identify all columns except identifiers
    error_cols = [c for c in df.columns if c not in IDENTIFIER_COLS]
    print(f"🔍 Found {len(error_cols)} non‑identifier columns to convert.")

    # Convert each to numeric, then to binary (1 if > 0)
    for col in error_cols:
        # Force numeric, invalid -> NaN, then fill NaN with 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        # Convert to binary
        df[col] = (df[col] > 0).astype(int)

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"✅ Saved binary version to {output_path}")

    # Print summary
    print("\n📊 Sample of first 5 rows (binary errors):")
    print(df.head().to_string())


def main():
    parser = argparse.ArgumentParser(description="Convert error counts to binary (presence/absence).")
    parser.add_argument("--input", required=True, help="Path to input CSV file")
    parser.add_argument("--output", required=True, help="Path to output CSV file")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"❌ Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    convert_to_binary(Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()