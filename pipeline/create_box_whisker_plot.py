#!/usr/bin/env python3
"""
Export effect sizes as CSV only – no images, no rendering errors.

Outputs:
  - pipeline/outputs/visualizations/effect_sizes/effect_sizes.csv
  - pipeline/outputs/visualizations/effect_sizes/summary_by_dataset.csv

Usage:
  python scripts/export_effect_sizes.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------
INPUT_CSV = Path(
    r"C:\Users\Justin\SIP-git\schema-error-analysis\pipeline\outputs\family_sums.csv"
)
OUT_DIR = INPUT_CSV.parent / "visualizations" / "effect_sizes"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CHAR_FAMILIES = [
    "Complexity_sum",
    "ValueTypes_sum",
    "Structural_sum",
    "TableFeatures_sum",
    "SchemaFeatures_sum"
]

CHAR_LABELS = {
    "Complexity_sum": "Complexity",
    "ValueTypes_sum": "Value Types",
    "Structural_sum": "Structural",
    "TableFeatures_sum": "Table Features",
    "SchemaFeatures_sum": "Schema Features"
}

ERROR_FAMILIES = [
    "Completion_sum",
    "Syntax_sum",
    "Contamination_sum",
    "Schema_Error_sum",
    "Content_sum"
]

def load_data():
    df = pd.read_csv(INPUT_CSV)
    existing_err = [c for c in ERROR_FAMILIES if c in df.columns]
    if existing_err:
        df['total_errors'] = df[existing_err].sum(axis=1)
    return df

def bootstrap_diff(high, low, n_boot=1000):
    """Bootstrap 95% CI for difference in means."""
    diffs = []
    n_high, n_low = len(high), len(low)
    if n_high == 0 or n_low == 0:
        return np.nan, np.nan, np.nan
    for _ in range(n_boot):
        high_sample = np.random.choice(high, size=n_high, replace=True)
        low_sample = np.random.choice(low, size=n_low, replace=True)
        diffs.append(np.mean(high_sample) - np.mean(low_sample))
    return np.mean(diffs), np.percentile(diffs, [2.5, 97.5])

def export_effect_sizes(df):
    """Export effect sizes to CSV."""
    all_results = []

    for dataset in sorted(df['dataset'].unique()):
        df_ds = df[df['dataset'] == dataset].copy()
        print(f"\n📊 Processing: {dataset}")

        for char in CHAR_FAMILIES:
            if char not in df_ds.columns or df_ds[char].nunique() <= 1:
                continue

            median = df_ds[char].median()
            high = df_ds[df_ds[char] >= median]['total_errors'].values
            low = df_ds[df_ds[char] < median]['total_errors'].values

            if len(high) < 3 or len(low) < 3:
                continue

            mean_high = np.mean(high)
            mean_low = np.mean(low)
            diff, ci = bootstrap_diff(high, low)

            all_results.append({
                'dataset': dataset,
                'characteristic': CHAR_LABELS.get(char, char),
                'median_threshold': median,
                'n_high': len(high),
                'n_low': len(low),
                'mean_high': mean_high,
                'mean_low': mean_low,
                'effect_size': diff,
                'ci_low': ci[0],
                'ci_high': ci[1]
            })

    if not all_results:
        print("❌ No results found.")
        return

    df_results = pd.DataFrame(all_results)

    # Save full CSV
    csv_path = OUT_DIR / 'effect_sizes.csv'
    df_results.to_csv(csv_path, index=False)
    print(f"\n✅ Effect sizes saved to: {csv_path}")

    # Print summary table to console
    print("\n📊 SUMMARY TABLE")
    print("=" * 100)
    print(f"{'Dataset':<18} {'Characteristic':<18} {'Effect':<12} {'95% CI':<20} {'Direction':<10}")
    print("-" * 100)
    for _, row in df_results.iterrows():
        effect = row['effect_size']
        direction = "⬆️ Increases" if effect > 0 else "⬇️ Decreases" if effect < 0 else "➖ No effect"
        ci_text = f"[{row['ci_low']:.1f}, {row['ci_high']:.1f}]"
        print(f"{row['dataset']:<18} {row['characteristic']:<18} {effect:<12.1f} {ci_text:<20} {direction:<10}")

    return df_results

def main():
    print("=" * 80)
    print("📊 EFFECT SIZE EXPORTER (CSV only, no images)")
    print("=" * 80 + "\n")

    df = load_data()
    print(f"Loaded {len(df)} rows")

    export_effect_sizes(df)

    print(f"\n✅ Files saved to: {OUT_DIR}")
    print("   - effect_sizes.csv")
    print("\n💡 Use this CSV to create plots in Excel, Google Sheets, or any other tool.")

if __name__ == "__main__":
    main()