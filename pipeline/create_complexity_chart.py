import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Set professional style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica']

# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------
INPUT_CSV = Path("pipeline/outputs/family_sums.csv")
OUTPUT_DIR = Path(".")

# Characteristic families (as they appear in family_sums.csv)
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

# Error families (used to compute total_errors)
ERROR_FAMILIES = [
    "Completion_sum",
    "Syntax_sum",
    "Contamination_sum",
    "Schema_Error_sum",
    "Content_sum"
]

# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------
def load_data():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    # Compute total_errors if not already present
    if 'total_errors' not in df.columns:
        existing_err = [c for c in ERROR_FAMILIES if c in df.columns]
        if existing_err:
            df['total_errors'] = df[existing_err].sum(axis=1)
        else:
            raise ValueError("No error family columns found")
    print(f"✅ Loaded {len(df)} rows from {INPUT_CSV.name}")
    return df

# ------------------------------------------------------------
# CORRELATION WITH CI
# ------------------------------------------------------------
def correlation_with_ci(x, y):
    """Return (corr, lower_ci, upper_ci) using Fisher z-transformation."""
    n = len(x)
    if n < 3:
        return np.nan, np.nan, np.nan
    corr = x.corr(y)
    if pd.isna(corr):
        return np.nan, np.nan, np.nan
    # Fisher z
    z = 0.5 * np.log((1 + corr) / (1 - corr))
    se = 1 / np.sqrt(n - 3)
    z_low = z - 1.96 * se
    z_high = z + 1.96 * se
    ci_low = (np.exp(2 * z_low) - 1) / (np.exp(2 * z_low) + 1)
    ci_high = (np.exp(2 * z_high) - 1) / (np.exp(2 * z_high) + 1)
    return corr, ci_low, ci_high

# ------------------------------------------------------------
# FOREST PLOT
# ------------------------------------------------------------
def create_forest_plot(df, dataset_name, char_labels, output_dir="."):
    """Create a forest plot for a given dataset."""
    df_ds = df[df['dataset'] == dataset_name].copy()
    if df_ds.empty:
        print(f"No data for {dataset_name}")
        return

    results = []
    for char in CHAR_FAMILIES:
        if char not in df_ds.columns:
            continue
        if df_ds[char].nunique() <= 1:
            continue
        corr, ci_low, ci_high = correlation_with_ci(df_ds[char], df_ds['total_errors'])
        if not pd.isna(corr):
            results.append({
                'characteristic': char_labels.get(char, char),
                'correlation': corr,
                'ci_low': ci_low,
                'ci_high': ci_high,
                'n': len(df_ds)
            })

    if not results:
        print(f"No valid correlations for {dataset_name}")
        return

    results_df = pd.DataFrame(results)
    # Sort by absolute correlation
    results_df = results_df.sort_values('correlation', ascending=False)

    # ---- plot ----
    fig, ax = plt.subplots(figsize=(10, max(6, len(results_df) * 0.6)))

    # Colors based on direction
    colors = []
    for corr in results_df['correlation']:
        if corr > 0.1:
            colors.append('#E74C3C')   # red for positive
        elif corr < -0.1:
            colors.append('#3498DB')   # blue for negative
        else:
            colors.append('#95A5A6')   # gray

    y_pos = np.arange(len(results_df))

    # Confidence intervals
    for i, (corr, ci_low, ci_high) in enumerate(zip(
        results_df['correlation'], results_df['ci_low'], results_df['ci_high']
    )):
        ax.hlines(y=i, xmin=ci_low, xmax=ci_high, color='#2C3E50', linewidth=2.5, alpha=0.7)

    # Point estimates (diamonds)
    ax.scatter(
        results_df['correlation'],
        y_pos,
        s=300,
        c=colors,
        marker='D',
        edgecolors='#2C3E50',
        linewidth=1.5,
        zorder=3
    )

    # Correlation values with CI text
    for i, (corr, ci_low, ci_high) in enumerate(zip(
        results_df['correlation'], results_df['ci_low'], results_df['ci_high']
    )):
        if corr > 0:
            x_pos = corr + 0.06
            ha = 'left'
        elif corr < 0:
            x_pos = corr - 0.06
            ha = 'right'
        else:
            x_pos = 0.06
            ha = 'left'
        label = f'{corr:.2f}'
        ax.text(x_pos, i, label, va='center', ha=ha, fontsize=10, fontweight='bold')

    # Reference lines
    ax.axvline(x=0, color='#7F8C8D', linestyle='--', linewidth=1.5, alpha=0.5)
    ax.axvline(x=0.3, color='#BDC3C7', linestyle=':', linewidth=1, alpha=0.5)
    ax.axvline(x=-0.3, color='#BDC3C7', linestyle=':', linewidth=1, alpha=0.5)

    # Labels
    ax.set_yticks(y_pos)
    ax.set_yticklabels(results_df['characteristic'], fontsize=11)
    ax.set_xlabel('Correlation Coefficient', fontsize=13, fontweight='bold')
    ax.set_title(f'{dataset_name}: Characteristic Family Correlation with Total Errors', 
                 fontsize=15, fontweight='bold', pad=20)
    ax.set_xlim(-1.1, 1.1)

    ax.grid(axis='x', alpha=0.2, linestyle='--')
    ax.set_axisbelow(True)

    # Legend
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    legend_elements = [
        Patch(facecolor='#E74C3C', label='Positive Correlation (↑ Errors)'),
        Patch(facecolor='#3498DB', label='Negative Correlation (↓ Errors)'),
        Patch(facecolor='#95A5A6', label='No Correlation'),
        Line2D([0], [0], marker='D', color='w', markerfacecolor='#2C3E50', markersize=8, label='Correlation'),
        Line2D([0], [0], color='#2C3E50', linewidth=2.5, label='95% CI')
    ]
    ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1.02, 1), fontsize=10)

    plt.tight_layout()
    save_path = Path(output_dir) / f'{dataset_name}_forest_plot.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ Forest plot saved to: {save_path}")
    plt.close()

    # Print summary
    print(f"\n📊 {dataset_name} - Characteristic-Error Correlation Summary")
    print("=" * 80)
    print(f"{'Characteristic':<25} {'Correlation':<12} {'95% CI':<20} {'Effect':<15}")
    print("-" * 80)
    for _, row in results_df.iterrows():
        if row['correlation'] > 0.1:
            effect = "⬆️ Increases"
        elif row['correlation'] < -0.1:
            effect = "⬇️ Decreases"
        else:
            effect = "➖ No effect"
        print(f"{row['characteristic']:<25} {row['correlation']:<12.3f} [{row['ci_low']:.2f}, {row['ci_high']:.2f}] {effect}")

    return results_df

# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():
    print("=" * 80)
    print("📊 FOREST PLOT: Characteristic Families vs Total Errors")
    print("=" * 80 + "\n")

    df = load_data()
    datasets = df['dataset'].unique()
    print(f"Datasets: {list(datasets)}\n")

    for dataset in sorted(datasets):
        print(f"\n{'=' * 80}")
        print(f"📊 Processing: {dataset}")
        print("=" * 80)
        create_forest_plot(df, dataset, CHAR_LABELS, OUTPUT_DIR)

    print("\n" + "=" * 80)
    print("✅ COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    main()