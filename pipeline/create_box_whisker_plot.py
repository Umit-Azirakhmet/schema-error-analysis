#!/usr/bin/env python3
"""
Robust box‑and‑whisker plots for characteristic families vs total errors.

Reads family_sums.csv, splits each characteristic family into High/Low groups,
removes outliers, and creates a merged box plot per dataset.

Saves PNGs to: pipeline/outputs/visualizations/boxplots_robust/
If plotting fails, prints summary stats to console.

Usage:
  python scripts/box_whisker_robust.py
"""

import pandas as pd
import matplotlib.pyplot as plt
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
OUT_DIR = INPUT_CSV.parent / "visualizations" / "boxplots_robust"
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
# PLOT STYLE
# ------------------------------------------------------------
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica']

# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------
def load_data():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    # Compute total errors
    existing_err = [c for c in ERROR_FAMILIES if c in df.columns]
    if existing_err:
        df['total_errors'] = df[existing_err].sum(axis=1)
    else:
        raise ValueError("No error family columns found")
    print(f"✅ Loaded {len(df)} rows from {INPUT_CSV.name}")
    return df

# ------------------------------------------------------------
# OUTLIER REMOVAL (IQR)
# ------------------------------------------------------------
def remove_outliers(data):
    if len(data) == 0:
        return data
    q1 = np.percentile(data, 25)
    q3 = np.percentile(data, 75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return data[(data >= lower) & (data <= upper)]

# ------------------------------------------------------------
# PLOT PER DATASET
# ------------------------------------------------------------
def plot_dataset(df, dataset_name):
    df_ds = df[df['dataset'] == dataset_name].copy()
    if df_ds.empty:
        print(f"⚠️  No data for {dataset_name}")
        return

    # Select characteristic families that have variance
    avail = []
    for char in CHAR_FAMILIES:
        if char in df_ds.columns and df_ds[char].nunique() > 1:
            avail.append(char)

    if not avail:
        print(f"⚠️  No varying characteristics for {dataset_name}")
        return

    # Build data: for each characteristic, high vs low
    all_data = []
    all_labels = []
    all_colors = []
    stats = []

    high_color = '#E74C3C'
    low_color  = '#3498DB'

    for char in avail:
        median = df_ds[char].median()
        high = df_ds[df_ds[char] >= median]['total_errors'].dropna().values
        low  = df_ds[df_ds[char] <  median]['total_errors'].dropna().values

        high_clean = remove_outliers(high)
        low_clean  = remove_outliers(low)

        if len(high_clean) > 3 and len(low_clean) > 3:
            all_data.append(high_clean)
            all_labels.append(f'{CHAR_LABELS[char]}\nHigh')
            all_colors.append(high_color)
            stats.append({
                'char': CHAR_LABELS[char],
                'group': 'High',
                'mean': np.mean(high_clean),
                'median': np.median(high_clean),
                'std': np.std(high_clean),
                'n': len(high_clean)
            })

            all_data.append(low_clean)
            all_labels.append(f'{CHAR_LABELS[char]}\nLow')
            all_colors.append(low_color)
            stats.append({
                'char': CHAR_LABELS[char],
                'group': 'Low',
                'mean': np.mean(low_clean),
                'median': np.median(low_clean),
                'std': np.std(low_clean),
                'n': len(low_clean)
            })

    if not all_data:
        print(f"⚠️  No valid splits for {dataset_name}")
        return

    # ------------------------------------------------------------
    # CREATE PLOT
    # ------------------------------------------------------------
    n_boxes = len(all_data)
    # Dynamically size figure, but cap at reasonable limits
    fig_width = min(12, n_boxes * 0.7 + 2)
    fig_height = min(8, 5 + (n_boxes // 2) * 0.2)
    # Ensure minimum size
    fig_width = max(8, fig_width)
    fig_height = max(5, fig_height)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    # Box plot
    bp = ax.boxplot(
        all_data,
        patch_artist=True,
        notch=False,
        widths=0.6,
        showfliers=False,
        boxprops={'linewidth': 1.2, 'edgecolor': '#2C3E50'},
        whiskerprops={'linewidth': 1.2, 'color': '#2C3E50'},
        capprops={'linewidth': 1.2, 'color': '#2C3E50'},
        medianprops={'linewidth': 2, 'color': '#2C3E50'}
    )

    # Color boxes
    for patch, color in zip(bp['boxes'], all_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)
        patch.set_edgecolor('#2C3E50')
        patch.set_linewidth(1.2)

    # Add jittered points (if not too many)
    for i, data in enumerate(all_data):
        if len(data) <= 50:
            x = np.random.normal(i + 1, 0.06, size=len(data))
            ax.scatter(x, data, alpha=0.15, s=8, color=all_colors[i], zorder=1)

    # Mean markers
    for i, data in enumerate(all_data):
        mean_val = np.mean(data)
        ax.scatter(i + 1, mean_val, color='#E74C3C', marker='D',
                   s=50, zorder=3, edgecolor='white', linewidth=1)

    # Axes
    ax.set_ylabel('Total Errors', fontsize=11, fontweight='bold')
    ax.set_title(f'{dataset_name}: Error Distribution by Characteristic Family\n(Outliers Removed)',
                 fontsize=13, fontweight='bold', pad=15)

    ax.set_xticks(range(1, n_boxes + 1))
    ax.set_xticklabels(all_labels, fontsize=7, fontweight='bold',
                       rotation=45, ha='right')

    # Y limits with padding
    all_vals = np.concatenate(all_data)
    y_min, y_max = np.min(all_vals), np.max(all_vals)
    y_range = y_max - y_min
    ax.set_ylim(y_min - 0.1 * y_range, y_max + 0.1 * y_range)

    ax.grid(axis='y', alpha=0.2, linestyle='--')
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Effect annotations (mean difference)
    for i in range(0, n_boxes, 2):
        if i + 1 < n_boxes:
            diff = stats[i]['mean'] - stats[i+1]['mean']
            effect = "⬆️" if diff > 0 else "⬇️" if diff < 0 else "➖"
            ax.text(i + 1.5, y_min - 0.08 * y_range, f'{effect} {abs(diff):.1f}',
                    ha='center', va='top', fontsize=7, color='#2C3E50',
                    transform=ax.get_xaxis_transform())

    # Legend
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    legend_elements = [
        Patch(facecolor='#E74C3C', alpha=0.5, edgecolor='#2C3E50', label='High (≥ median)'),
        Patch(facecolor='#3498DB', alpha=0.5, edgecolor='#2C3E50', label='Low (< median)'),
        Line2D([0], [0], marker='D', color='w', markerfacecolor='#E74C3C',
               markersize=8, label='Mean')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=8,
              framealpha=0.9, edgecolor='#BDC3C7', fancybox=True)

    plt.tight_layout()

    # ------------------------------------------------------------
    # SAVE
    # ------------------------------------------------------------
    save_path = OUT_DIR / f'{dataset_name}_boxplot.png'
    try:
        plt.savefig(save_path, dpi=100, bbox_inches='tight', facecolor='white')
        print(f"✅ Box plot saved to: {save_path}")
    except Exception as e:
        print(f"⚠️  Could not save image for {dataset_name}: {e}")
        print("   Printing summary stats instead.")
        # Print stats
        print_summary_stats(dataset_name, stats)
    finally:
        plt.close()

    # Always print stats to console (for quick reference)
    print_summary_stats(dataset_name, stats)


# ------------------------------------------------------------
# PRINT SUMMARY STATS (fallback)
# ------------------------------------------------------------
def print_summary_stats(dataset_name, stats):
    print(f"\n📊 {dataset_name} - Box Plot Summary")
    print("=" * 90)
    print(f"{'Characteristic':<25} {'Group':<8} {'Mean':<10} {'Median':<10} {'Std':<10} {'N':<8} {'Effect':<10}")
    print("-" * 90)
    for i, s in enumerate(stats):
        if i % 2 == 0 and i + 1 < len(stats):
            diff = stats[i]['mean'] - stats[i+1]['mean']
            effect = "⬆️" if diff > 0 else "⬇️" if diff < 0 else "➖"
        else:
            effect = ""
        print(f"{s['char']:<25} {s['group']:<8} {s['mean']:<10.1f} {s['median']:<10.1f} {s['std']:<10.1f} {s['n']:<8} {effect:<10}")

# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():
    print("=" * 80)
    print("📊 ROBUST BOX‑AND‑WHISKER PLOTS (Characteristic Families)")
    print("=" * 80 + "\n")

    df = load_data()
    datasets = df['dataset'].unique()
    print(f"Datasets: {list(datasets)}\n")

    for ds in sorted(datasets):
        print(f"\n{'=' * 80}")
        print(f"📊 Processing: {ds}")
        print("=" * 80)
        plot_dataset(df, ds)

    print("\n" + "=" * 80)
    print("✅ COMPLETE!")
    print(f"📁 Images (if generated) saved to: {OUT_DIR}")
    print("=" * 80)

if __name__ == "__main__":
    main()