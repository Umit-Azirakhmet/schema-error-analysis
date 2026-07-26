#!/usr/bin/env python3
"""
Generate two key visualizations:
  1) Average total errors heatmap (raw and normalized) across dataset, model, method.
  2) Characteristic-Error correlation heatmap (combined across all datasets).

Usage:
  python scripts/generate_two_plots.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path

# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------
INPUT_CSV = Path(
    r"C:\Users\Justin\SIP-git\schema-error-analysis\pipeline\outputs\family_sums.csv"
)
OUTPUT_DIR = INPUT_CSV.parent / "visualizations"

# Family definitions (must match column names in family_sums.csv)
CHAR_FAMILIES = ["Complexity_sum", "ValueTypes_sum", "Structural_sum", 
                 "TableFeatures_sum", "SchemaFeatures_sum"]
ERROR_FAMILIES = ["Completion_sum", "Syntax_sum", "Contamination_sum", 
                  "Schema_Error_sum", "Content_sum"]

CHAR_LABELS = {
    "Complexity_sum": "Complexity",
    "ValueTypes_sum": "Value Types",
    "Structural_sum": "Structural",
    "TableFeatures_sum": "Table Features",
    "SchemaFeatures_sum": "Schema Features"
}
ERROR_LABELS = {
    "Completion_sum": "Completion",
    "Syntax_sum": "Syntax",
    "Contamination_sum": "Contamination",
    "Schema_Error_sum": "Schema (Error)",
    "Content_sum": "Content"
}

# ------------------------------------------------------------
# SETUP
# ------------------------------------------------------------
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("Set2")

def load_data():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    print(f"✅ Loaded {len(df)} rows from {INPUT_CSV.name}")
    return df

# ------------------------------------------------------------
# PLOT 1: Average Error Heatmap (Raw + Normalized)
# ------------------------------------------------------------
def plot_avg_error_heatmap(df):
    """Create a side-by-side figure with raw and normalized average error heatmaps."""
    # Compute total errors if not present
    if 'total_errors' not in df.columns:
        df = df.copy()
        df['total_errors'] = df[ERROR_FAMILIES].sum(axis=1)
    
    # Average by dataset, model, method
    df_avg = df.groupby(['dataset', 'model', 'method'])['total_errors'].mean().reset_index()
    df_avg['label'] = df_avg['dataset'] + " - " + df_avg['model']
    
    # Pivot table: rows = label, columns = method, values = avg_errors
    pivot = df_avg.pivot_table(index='label', columns='method', values='total_errors')
    col_order = ['zero_shot', 'few_shot', 'nl_to_format']
    pivot = pivot.reindex(columns=[c for c in col_order if c in pivot.columns], fill_value=np.nan)
    pivot = pivot.sort_index()
    
    # Create normalized version (0=best, 100=worst)
    min_val = pivot.min().min()
    max_val = pivot.max().max()
    if max_val - min_val > 0:
        pivot_norm = ((pivot - min_val) / (max_val - min_val)) * 100
    else:
        pivot_norm = pivot * 0
    
    # Create figure with two subplots
    fig, axes = plt.subplots(1, 2, figsize=(18, max(8, len(pivot) * 0.5)))
    
    cmap = sns.color_palette("RdYlGn_r", as_cmap=True)
    
    # --- Raw heatmap ---
    ax = axes[0]
    sns.heatmap(
        pivot, annot=True, fmt='.1f', cmap=cmap,
        linewidths=2, linecolor='white',
        cbar_kws={'label': 'Average Total Errors'},
        square=True, annot_kws={'size': 11, 'fontweight': 'bold'},
        ax=ax, mask=pivot.isna()
    )
    ax.set_title('Raw Average Total Errors', fontsize=14, fontweight='bold')
    ax.set_xlabel('Method', fontsize=12, fontweight='bold')
    ax.set_ylabel('Dataset - Model', fontsize=12, fontweight='bold')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
    
    # --- Normalized heatmap ---
    ax = axes[1]
    sns.heatmap(
        pivot_norm, annot=True, fmt='.1f', cmap=cmap,
        linewidths=2, linecolor='white',
        cbar_kws={'label': 'Normalized Score (0=Best, 100=Worst)'},
        square=True, annot_kws={'size': 11, 'fontweight': 'bold'},
        ax=ax, mask=pivot_norm.isna(),
        vmin=0, vmax=100
    )
    ax.set_title('Normalized Average Errors (0=Best, 100=Worst)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Method', fontsize=12, fontweight='bold')
    ax.set_ylabel('Dataset - Model', fontsize=12, fontweight='bold')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
    
    plt.suptitle('📊 Average Total Errors by Dataset, Model, and Method', 
                 fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    
    save_path = OUTPUT_DIR / "heatmap_avg_errors.png"
    plt.savefig(save_path, dpi=200, bbox_inches='tight', facecolor='white')
    print(f"✅ Saved: {save_path}")
    plt.close()
    
    return pivot, pivot_norm

# ------------------------------------------------------------
# PLOT 2: Correlation Heatmap (Characteristics vs Errors)
# ------------------------------------------------------------
def plot_correlation_heatmap(df):
    """Create a correlation heatmap between characteristic and error families."""
    # Select the family columns
    char_cols = [c for c in CHAR_FAMILIES if c in df.columns]
    err_cols = [c for c in ERROR_FAMILIES if c in df.columns]
    
    if not char_cols or not err_cols:
        print("⚠️  Missing characteristic or error columns")
        return None
    
    # Compute correlation matrix
    corr_df = df[char_cols + err_cols].corr()
    
    # Extract only characteristic × error correlations
    corr_matrix = corr_df.loc[char_cols, err_cols]
    
    # Rename for nicer labels
    corr_matrix = corr_matrix.rename(index=CHAR_LABELS, columns=ERROR_LABELS)
    
    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))
    
    cmap = sns.diverging_palette(250, 10, as_cmap=True, s=100, l=50)
    
    sns.heatmap(
        corr_matrix,
        annot=True,
        fmt='.2f',
        cmap=cmap,
        linewidths=2,
        linecolor='white',
        cbar_kws={'label': 'Correlation Coefficient'},
        square=True,
        annot_kws={'size': 12, 'fontweight': 'bold'},
        ax=ax,
        center=0,
        vmin=-1,
        vmax=1
    )
    
    ax.set_title('📊 Characteristic-Error Correlation (Combined Data)',
                 fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Error Families', fontsize=13, fontweight='bold')
    ax.set_ylabel('Characteristic Families', fontsize=13, fontweight='bold')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    
    save_path = OUTPUT_DIR / "correlation_heatmap.png"
    plt.savefig(save_path, dpi=200, bbox_inches='tight', facecolor='white')
    print(f"✅ Saved: {save_path}")
    plt.close()
    
    # Print correlation values
    print("\n📊 Correlation Matrix (Characteristic vs Error):")
    print(corr_matrix.round(3).to_string())
    
    return corr_matrix

# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():
    print("\n" + "=" * 80)
    print("📊 GENERATING TWO KEY PLOTS")
    print("   Heatmap (raw + normalized) | Correlation Heatmap")
    print("=" * 80 + "\n")
    
    df = load_data()
    
    # Ensure method names are consistent
    df['method'] = df['method'].replace({
        'NL_to_format': 'nl_to_format',
        'nl_to_format': 'nl_to_format'
    })
    
    # Plot 1: average errors
    print("\n📊 Creating average error heatmap (raw + normalized)...")
    plot_avg_error_heatmap(df)
    
    # Plot 2: correlation heatmap
    print("\n📊 Creating characteristic-error correlation heatmap...")
    plot_correlation_heatmap(df)
    
    print("\n" + "=" * 80)
    print("✅ COMPLETE!")
    print(f"📁 Files saved to: {OUTPUT_DIR}")
    print("  ├── heatmap_avg_errors.png")
    print("  └── correlation_heatmap.png")
    print("=" * 80)

if __name__ == "__main__":
    main()