#!/usr/bin/env python3
"""
Professional box‑and‑whisker plots – publication‑ready.

- Linear scale for ARQA, log scale for DeepJSONEval & SchemaToJSON.
- Clean white background, readable fonts, colourblind‑friendly palette.

Outputs:
  pipeline/outputs/visualizations/boxplots_pretty_final/*.png

Usage:
  python scripts/box_whisker_pretty_final.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
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
OUT_DIR = INPUT_CSV.parent / "visualizations" / "boxplots_pretty_final"
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

# ------------------------------------------------------------
# STYLE – clean and professional
# ------------------------------------------------------------
sns.set_style("whitegrid", {'grid.linestyle': '--', 'grid.alpha': 0.4})
sns.set_palette("Set2")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica']
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['figure.dpi'] = 150

def load_data():
    df = pd.read_csv(INPUT_CSV)
    existing_err = [c for c in ERROR_FAMILIES if c in df.columns]
    if existing_err:
        df['total_errors'] = df[existing_err].sum(axis=1)
    print(f"✅ Loaded {len(df)} rows")
    return df

def plot_box_whisker(df, dataset_name):
    df_ds = df[df['dataset'] == dataset_name].copy()
    if df_ds.empty:
        print(f"⚠️  No data for {dataset_name}")
        return

    # Prepare tidy data
    records = []
    for char in CHAR_FAMILIES:
        if char not in df_ds.columns or df_ds[char].nunique() <= 1:
            continue
        median = df_ds[char].median()
        for _, row in df_ds.iterrows():
            if row[char] >= median:
                group = f"{CHAR_LABELS[char]}\nHigh"
            else:
                group = f"{CHAR_LABELS[char]}\nLow"
            records.append({
                'group': group,
                'total_errors': row['total_errors']
            })
    if not records:
        print(f"⚠️  No valid splits for {dataset_name}")
        return

    tidy = pd.DataFrame(records)

    n_groups = len(tidy['group'].unique())
    if n_groups == 0:
        return

    # ---- Decide scale based on dataset ----
    if dataset_name in ["DeepJSONEval", "SchemaToJSON"]:
        use_log = True
        y_label = "Total Errors (log scale)"
    else:
        use_log = False
        y_label = "Total Errors"

    # ---- Figure size ----
    fig_width = min(12, n_groups * 0.6 + 2)
    fig_height = 6
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    # ---- Box plot ----
    # Colour palette: high = coral, low = teal
    palette = {'High': '#E67E22', 'Low': '#3498DB'}
    sns.boxplot(
        data=tidy,
        x='group',
        y='total_errors',
        palette=[palette['High'] if 'High' in g else palette['Low'] for g in tidy['group'].unique()],
        ax=ax,
        fliersize=2,
        linewidth=1.2,
        width=0.6
    )

    # ---- Jitter points ----
    sns.stripplot(
        data=tidy,
        x='group',
        y='total_errors',
        color='black',
        alpha=0.1,
        size=2,
        jitter=0.2,
        ax=ax
    )

    # ---- Axis scaling ----
    if use_log:
        ax.set_yscale('log')
        # Avoid log(0) issues – set a positive lower bound
        ax.set_ylim(bottom=0.5, top=np.percentile(tidy['total_errors'], 99.5) * 1.1)
    else:
        y_max = np.percentile(tidy['total_errors'], 99.5)
        ax.set_ylim(bottom=0, top=y_max * 1.1)

    # ---- Labels & formatting ----
    ax.set_xlabel('')
    ax.set_ylabel(y_label, fontsize=12, fontweight='bold')
    ax.set_title(dataset_name, fontsize=14, fontweight='bold', pad=15)
    plt.xticks(rotation=45, ha='right', fontsize=10)

    # ---- Legend ----
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=palette['High'], label='High (≥ median)'),
        Patch(facecolor=palette['Low'], label='Low (< median)')
    ]
    ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1, 1), frameon=False)

    # ---- Remove top and right spines ----
    sns.despine(ax=ax, top=True, right=True)

    # ---- Save ----
    plt.tight_layout()
    save_path = OUT_DIR / f'{dataset_name}_boxplot.png'
    plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"✅ Saved: {save_path}")
    plt.close()

    # ---- Print summary ----
    print(f"\n📊 {dataset_name} – Box Plot Summary")
    print("=" * 90)
    summary = tidy.groupby('group')['total_errors'].agg(['mean', 'median', 'std', 'count']).round(1)
    print(summary.to_string())

def main():
    print("=" * 80)
    print("📊 PROFESSIONAL BOX‑AND‑WHISKER PLOTS")
    print("=" * 80 + "\n")

    df = load_data()
    for dataset in sorted(df['dataset'].unique()):
        print(f"\n{'='*80}\n📊 Processing: {dataset}\n{'='*80}")
        plot_box_whisker(df, dataset)

    print(f"\n✅ All PNGs saved to: {OUT_DIR}")

if __name__ == "__main__":
    main()