#!/usr/bin/env python3
"""
Professional box-and-whisker plots -- publication-ready, v2 (prettier).

Key visual upgrades over v1:
  - Low/High pairs are grouped tightly per family, with clear spacing
    between families (instead of one long undifferentiated row).
  - Alternating soft background bands behind each family pair, so the
    eye can parse "5 families" at a glance.
  - Okabe-Ito colorblind-safe palette, slightly desaturated for a
    calmer, more "editorial" look; median line drawn in a near-black
    for contrast against both colors.
  - Mean marker (small diamond) shown alongside the median line.
  - Sample size (n=...) printed under each box's x-tick label.
  - Legend moved to a clean horizontal strip above the plot (no more
    floating box competing with the title).
  - Subtitle line under the title for context.
  - Log-scale panels get a lighter/denser minor gridline treatment so
    the many decades of range stay readable.

Outputs:
  pipeline/outputs/visualizations/boxplots_pretty_final/*.png

Usage:
  python scripts/box_whisker_pretty_final_v2.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
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
    "SchemaFeatures_sum",
]

CHAR_LABELS = {
    "Complexity_sum": "Complexity",
    "ValueTypes_sum": "Value Types",
    "Structural_sum": "Structural",
    "TableFeatures_sum": "Table Features",
    "SchemaFeatures_sum": "Schema Features",
}

ERROR_FAMILIES = [
    "Completion_sum",
    "Syntax_sum",
    "Contamination_sum",
    "Schema_Error_sum",
    "Content_sum",
]

# Okabe-Ito colorblind-safe palette, softened slightly
COLOR_HIGH = "#E1812C"   # warm amber/orange
COLOR_LOW = "#3A7CA5"    # muted steel blue
COLOR_MEDIAN = "#2B2B2B" # near-black, reads on both fills
BAND_COLOR = "#F2F2F2"   # very light grey band behind each family pair

# ------------------------------------------------------------
# STYLE
# ------------------------------------------------------------
sns.set_style("white")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica']
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 15
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['figure.dpi'] = 150


def load_data():
    df = pd.read_csv(INPUT_CSV)
    existing_err = [c for c in ERROR_FAMILIES if c in df.columns]
    if existing_err:
        df['total_errors'] = df[existing_err].sum(axis=1)
    print(f"Loaded {len(df)} rows")
    return df


def plot_box_whisker(df, dataset_name):
    df_ds = df[df['dataset'] == dataset_name].copy()
    if df_ds.empty:
        print(f"No data for {dataset_name}")
        return

    # Build one (family, level) -> values dict, preserving family order
    family_data = {}
    for char in CHAR_FAMILIES:
        if char not in df_ds.columns or df_ds[char].nunique() <= 1:
            continue
        median = df_ds[char].median()
        low_vals = df_ds.loc[df_ds[char] < median, 'total_errors'].values
        high_vals = df_ds.loc[df_ds[char] >= median, 'total_errors'].values
        if len(low_vals) == 0 and len(high_vals) == 0:
            continue
        family_data[CHAR_LABELS[char]] = {'Low': low_vals, 'High': high_vals}

    if not family_data:
        print(f"No valid splits for {dataset_name}")
        return

    # ---- Decide scale based on dataset ----
    if dataset_name in ["DeepJSONEval", "SchemaToJSON"]:
        use_log = True
        y_label = "Total Errors (log scale)"
    else:
        use_log = False
        y_label = "Total Errors"

    # ---- Layout: 2 boxes per family, small gap within pair, bigger gap between families ----
    pair_gap = 0.62      # spacing between Low/High within a family
    family_gap = 1.0     # extra spacing between families

    positions = []
    tick_positions = []
    tick_labels = []
    box_data = []
    box_colors = []
    band_spans = []  # (start, end) in x for background shading

    cursor = 0.0
    for i, (fam_label, levels) in enumerate(family_data.items()):
        start = cursor
        low_pos = cursor
        high_pos = cursor + pair_gap
        positions.extend([low_pos, high_pos])
        box_data.extend([levels['Low'], levels['High']])
        box_colors.extend([COLOR_LOW, COLOR_HIGH])
        tick_positions.append((low_pos + high_pos) / 2)
        n_low, n_high = len(levels['Low']), len(levels['High'])
        tick_labels.append(f"{fam_label}\n(n={n_low} / n={n_high})")
        end = high_pos
        band_spans.append((start - pair_gap * 0.55, end + pair_gap * 0.55))
        cursor = high_pos + pair_gap + family_gap

    n_boxes = len(box_data)
    fig_width = min(14, max(7, len(family_data) * 2.0))
    fig_height = 6.2
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    # ---- Alternating soft background bands per family (visual grouping) ----
    for idx, (s, e) in enumerate(band_spans):
        if idx % 2 == 0:
            ax.axvspan(s, e, color=BAND_COLOR, zorder=0)

    # ---- Draw boxplots one at a time at custom positions ----
    bp = ax.boxplot(
        box_data,
        positions=positions,
        widths=0.5,
        patch_artist=True,
        showfliers=True,
        flierprops=dict(marker='o', markersize=2.5, markerfacecolor='#888888',
                         markeredgecolor='none', alpha=0.5),
        medianprops=dict(color=COLOR_MEDIAN, linewidth=1.8),
        whiskerprops=dict(color='#555555', linewidth=1.1),
        capprops=dict(color='#555555', linewidth=1.1),
        boxprops=dict(linewidth=1.1, edgecolor='#333333'),
        zorder=3,
    )
    for patch, color in zip(bp['boxes'], box_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.88)

    # ---- Mean markers ----
    means = [np.mean(vals) for vals in box_data]
    ax.scatter(positions, means, marker='D', s=26, facecolor='white',
               edgecolor=COLOR_MEDIAN, linewidth=1.1, zorder=4, label='_nolegend_')

    # ---- Axis scaling ----
    all_vals = np.concatenate(box_data)
    if use_log:
        ax.set_yscale('log')
        ax.set_ylim(bottom=0.5, top=np.percentile(all_vals, 99.5) * 1.4)
        ax.yaxis.set_minor_locator(mticker.LogLocator(base=10, subs=np.arange(2, 10) * 0.1))
        ax.grid(axis='y', which='major', linestyle='-', alpha=0.35, linewidth=0.8, zorder=1)
        ax.grid(axis='y', which='minor', linestyle=':', alpha=0.15, linewidth=0.6, zorder=1)
    else:
        y_max = np.percentile(all_vals, 99.5)
        ax.set_ylim(bottom=0, top=y_max * 1.1)
        ax.grid(axis='y', linestyle='--', alpha=0.35, linewidth=0.8, zorder=1)

    # ---- Labels & formatting ----
    ax.set_xlim(band_spans[0][0], band_spans[-1][1])
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=20, ha='right', fontsize=9.5)
    ax.set_xlabel('')
    ax.set_ylabel(y_label, fontsize=12, fontweight='bold')

    sns.despine(ax=ax, top=True, right=True)
    ax.tick_params(axis='x', length=0)

    # ---- Reserve a clean header band above the axes, then place title,
    #      subtitle, and legend at fixed figure-fraction positions so they
    #      never overlap regardless of figure size. ----
    fig.subplots_adjust(top=0.76, bottom=0.30, left=0.09, right=0.97)

    fig.text(0.09, 0.97, dataset_name, fontsize=16, fontweight='bold',
              ha='left', va='top')
    fig.text(0.09, 0.905, "Total errors split by characteristic level (median cut)",
              fontsize=10, color='#555555', ha='left', va='top')

    legend_elements = [
        Patch(facecolor=COLOR_LOW, edgecolor='#333333', linewidth=0.8, label='Low (< median)'),
        Patch(facecolor=COLOR_HIGH, edgecolor='#333333', linewidth=0.8, label='High (\u2265 median)'),
        Line2D([0], [0], marker='D', color='none', markerfacecolor='white',
               markeredgecolor=COLOR_MEDIAN, markersize=7, label='Mean'),
        Line2D([0], [0], color=COLOR_MEDIAN, linewidth=1.8, label='Median'),
    ]
    fig.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0.09, 0.855),
               ncol=4, frameon=False, fontsize=9.5, handletextpad=0.5, columnspacing=1.4)

    save_path = OUT_DIR / f'{dataset_name}_boxplot.png'
    plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"Saved: {save_path}")
    plt.close()

    print(f"\n{dataset_name} - Box Plot Summary")
    print("=" * 90)
    for fam_label, levels in family_data.items():
        for level_name, vals in levels.items():
            print(f"{fam_label:20s} {level_name:5s} mean={np.mean(vals):>10.1f}  "
                  f"median={np.median(vals):>10.1f}  std={np.std(vals):>10.1f}  n={len(vals)}")


def main():
    print("=" * 80)
    print("PROFESSIONAL BOX-AND-WHISKER PLOTS (v2, prettier)")
    print("=" * 80 + "\n")

    df = load_data()
    for dataset in sorted(df['dataset'].unique()):
        print(f"\n{'='*80}\nProcessing: {dataset}\n{'='*80}")
        plot_box_whisker(df, dataset)

    print(f"\nAll PNGs saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()
