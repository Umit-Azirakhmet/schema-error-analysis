import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

# Set professional style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica']

def load_all_data(outputs_dir: str = "outputs"):
    """Load all error analysis data."""
    data = []
    outputs_path = Path(outputs_dir)
    
    for run_dir in outputs_path.iterdir():
        if not run_dir.is_dir():
            continue
        
        manifest_path = run_dir / "manifest.json"
        csv_path = run_dir / "error_analysis.csv"
        
        if not manifest_path.exists() or not csv_path.exists():
            continue
        
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        df_errors = pd.read_csv(csv_path)
        dataset = manifest.get('dataset')
        model = manifest.get('model', '').split('/')[-1]
        method = manifest.get('method', '')
        
        for _, row in df_errors.iterrows():
            data.append({
                'dataset': dataset,
                'model': model,
                'method': method,
                'row_id': row.get('row_id', ''),
                'total_errors': row.get('total_errors', 0),
                **row.to_dict()
            })
    
    return pd.DataFrame(data)

def calculate_correlations(df, dataset_name, characteristic_cols):
    """Calculate correlation between characteristics and total_errors."""
    
    df_ds = df[df['dataset'] == dataset_name]
    
    if df_ds.empty:
        print(f"No data for {dataset_name}")
        return None
    
    results = []
    
    for col in characteristic_cols:
        if col not in df_ds.columns:
            continue
        
        # Get the data
        char_data = df_ds[col]
        error_data = df_ds['total_errors']
        
        # Skip if all values are the same (zero variance)
        if char_data.nunique() <= 1:
            continue
        
        # Calculate correlation
        corr = char_data.corr(error_data)
        
        # Skip if correlation is NaN
        if pd.isna(corr):
            continue
        
        # Calculate 95% confidence interval
        n = len(df_ds)
        if n > 2:
            z = 0.5 * np.log((1 + corr) / (1 - corr))
            se = 1 / np.sqrt(n - 3)
            ci_low = z - 1.96 * se
            ci_high = z + 1.96 * se
            ci_low_corr = (np.exp(2 * ci_low) - 1) / (np.exp(2 * ci_low) + 1)
            ci_high_corr = (np.exp(2 * ci_high) - 1) / (np.exp(2 * ci_high) + 1)
        else:
            ci_low_corr = corr - 0.2
            ci_high_corr = corr + 0.2
        
        # Clean up the characteristic name
        clean_name = col.replace('s2j_', '').replace('dj_', '').replace('arqa_', '').replace('_', ' ').title()
        
        results.append({
            'characteristic': clean_name,
            'correlation': corr,
            'ci_low': ci_low_corr,
            'ci_high': ci_high_corr,
            'n': n
        })
    
    return pd.DataFrame(results)

def create_improved_forest_plot(results_df, dataset_name):
    """Create a clean, professional forest plot."""
    
    if results_df.empty:
        print(f"No results to plot for {dataset_name}")
        return
    
    # Sort by absolute correlation
    results_df = results_df.sort_values('correlation', ascending=False)
    
    # Filter out any remaining NaN values
    results_df = results_df.dropna(subset=['correlation', 'ci_low', 'ci_high'])
    
    if results_df.empty:
        print(f"No valid results to plot for {dataset_name}")
        return
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, max(6, len(results_df) * 0.6)))
    
    # Colors based on correlation direction
    colors = []
    for corr in results_df['correlation']:
        if corr > 0.1:
            colors.append('#E74C3C')  # Red - positive
        elif corr < -0.1:
            colors.append('#3498DB')  # Blue - negative
        else:
            colors.append('#95A5A6')  # Gray - no effect
    
    y_pos = np.arange(len(results_df))
    
    # Plot error bars (confidence intervals)
    for i, (corr, ci_low, ci_high) in enumerate(zip(
        results_df['correlation'], 
        results_df['ci_low'], 
        results_df['ci_high']
    )):
        ax.hlines(y=i, xmin=ci_low, xmax=ci_high, 
                 color='#2C3E50', linewidth=2.5, alpha=0.7)
    
    # Plot points (diamonds)
    scatter = ax.scatter(
        results_df['correlation'],
        y_pos,
        s=300,
        c=colors,
        marker='D',
        edgecolors='#2C3E50',
        linewidth=1.5,
        zorder=3
    )
    
    # Add correlation values with better positioning
    for i, (corr, ci_low, ci_high) in enumerate(zip(
        results_df['correlation'], 
        results_df['ci_low'], 
        results_df['ci_high']
    )):
        # Position label based on correlation sign
        if corr > 0:
            x_pos = corr + 0.06
            ha = 'left'
        elif corr < 0:
            x_pos = corr - 0.06
            ha = 'right'
        else:
            x_pos = 0.06
            ha = 'left'
        
        # Format label with CI
        label = f'{corr:.2f}'
        ax.text(x_pos, i, label, 
                va='center', ha=ha, fontsize=10, fontweight='bold',
                color='#2C3E50')
    
    # Vertical line at 0
    ax.axvline(x=0, color='#7F8C8D', linestyle='--', linewidth=1.5, alpha=0.5)
    
    # Reference lines at ±0.3
    ax.axvline(x=0.3, color='#BDC3C7', linestyle=':', linewidth=1, alpha=0.5)
    ax.axvline(x=-0.3, color='#BDC3C7', linestyle=':', linewidth=1, alpha=0.5)
    
    # Add threshold labels
    ax.text(0.3, -0.5, 'moderate', ha='center', va='top', fontsize=8, color='#7F8C8D', alpha=0.7)
    ax.text(-0.3, -0.5, 'moderate', ha='center', va='top', fontsize=8, color='#7F8C8D', alpha=0.7)
    
    # Formatting
    ax.set_yticks(y_pos)
    ax.set_yticklabels(results_df['characteristic'], fontsize=11)
    ax.set_xlabel('Correlation Coefficient', fontsize=13, fontweight='bold', color='#2C3E50')
    ax.set_title(f'{dataset_name}: Characteristic Correlation with Total Errors', 
                 fontsize=15, fontweight='bold', pad=20, color='#2C3E50')
    ax.set_xlim(-1.1, 1.1)
    
    # Clean up
    ax.grid(axis='x', alpha=0.2, linestyle='--', color='#BDC3C7')
    ax.set_axisbelow(True)
    ax.set_facecolor('#F8F9FA')
    fig.patch.set_facecolor('white')
    
    # Legend
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    
    legend_elements = [
        Patch(facecolor='#E74C3C', label='Positive Correlation (↑ Errors)'),
        Patch(facecolor='#3498DB', label='Negative Correlation (↓ Errors)'),
        Patch(facecolor='#95A5A6', label='No Correlation'),
        Line2D([0], [0], marker='D', color='w', markerfacecolor='#2C3E50', 
               markersize=8, label='Correlation Coefficient'),
        Line2D([0], [0], color='#2C3E50', linewidth=2.5, 
               label='95% Confidence Interval')
    ]
    ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1.02, 1), 
              fontsize=10, framealpha=0.95, edgecolor='#BDC3C7')
    
    plt.tight_layout()
    plt.savefig(f'{dataset_name}_forest_plot.png', dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    print(f"✅ Forest plot saved to: {dataset_name}_forest_plot.png")
    plt.close()
    
    # Print summary
    print(f"\n📊 {dataset_name} - Correlation Summary")
    print("=" * 80)
    print(f"{'Characteristic':<35} {'Correlation':<12} {'95% CI':<20} {'Effect':<15}")
    print("-" * 80)
    for _, row in results_df.iterrows():
        if row['correlation'] > 0.1:
            effect = "⬆️ Increases"
        elif row['correlation'] < -0.1:
            effect = "⬇️ Decreases"
        else:
            effect = "➖ No effect"
        print(f"{row['characteristic']:<35} {row['correlation']:<12.3f} [{row['ci_low']:.2f}, {row['ci_high']:.2f}] {effect}")
    
    return results_df

def create_all_forest_plots(df):
    """Create forest plots for all datasets."""
    
    # Define characteristics for each dataset
    configs = {
        'ARQA': {
            'characteristics': [
                'arqa_hallucinated_claims', 'arqa_wrong_claim_type',
                'arqa_hallucinated_claim_type', 'arqa_hallucinated_table_id',
                'arqa_missing_cell_text', 'arqa_wrong_coordinates',
                'arqa_empty_evidence_span', 'arqa_inaccurate_claims_evidence',
                'arqa_missing_top_level_fields'
            ]
        },
        'DeepJSONEval': {
            'characteristics': [
                'dj_enum_check', 'dj_property_count', 'dj_property_type',
                'dj_required_fields', 'dj_schema_echo', 'dj_titles_mismatch',
                'dj_top_level_not_object', 'dj_wrong_schema'
            ]
        },
        'SchemaToJSON': {
            'characteristics': [
                's2j_cell_value_errors', 's2j_array_instead_of_string',
                's2j_hallucinated_type', 's2j_wrong_root_structure',
                's2j_fields_not_allowed', 's2j_missing_conditional_fields'
            ]
        }
    }
    
    for dataset_name, config in configs.items():
        if dataset_name not in df['dataset'].unique():
            print(f"\n⚠️  No data for {dataset_name}, skipping...")
            continue
        
        print(f"\n{'=' * 80}")
        print(f"📊 Processing: {dataset_name}")
        print("=" * 80)
        
        results = calculate_correlations(df, dataset_name, config['characteristics'])
        
        if results is not None and not results.empty:
            create_improved_forest_plot(results, dataset_name)
        else:
            print(f"⚠️  No valid characteristics found for {dataset_name}")

def main():
    print("=" * 80)
    print("📊 FOREST PLOT: Characteristic vs Total Errors")
    print("=" * 80 + "\n")
    
    df = load_all_data('outputs')
    
    if df.empty:
        print("❌ No data found!")
        return
    
    print(f"✅ Loaded {len(df)} responses")
    print(f"   Datasets: {df['dataset'].unique().tolist()}")
    
    create_all_forest_plots(df)
    
    print("\n" + "=" * 80)
    print("✅ COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    main()