import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import json

# Set style for prettier plots
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("Set2")

def load_error_data(outputs_dir: str = "outputs"):
    """Load error analysis data from all runs."""
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
        
        df = pd.read_csv(csv_path)
        
        # Calculate average total_errors
        avg_errors = df['total_errors'].mean()
        
        # Get model name
        model = manifest.get('model', 'Unknown')
        if '/' in model:
            model = model.split('/')[-1]
        
        # Get method
        method = manifest.get('method', 'Unknown')
        if method == 'nl_to_format' or method == 'NL_to_format':
            method = 'nl_to_format'
        
        data.append({
            'dataset': manifest.get('dataset', 'Unknown'),
            'model': model,
            'method': method,
            'avg_errors': avg_errors,
            'num_rows': len(df),
            'run_id': run_dir.name
        })
    
    return pd.DataFrame(data)

def create_heatmap(df, dataset_name):
    """Create a heatmap for a specific dataset."""
    df_filtered = df[df['dataset'] == dataset_name]
    
    if df_filtered.empty:
        print(f"⚠️  No data found for dataset: {dataset_name}")
        return None
    
    # Pivot table
    pivot = df_filtered.pivot_table(
        index='model', 
        columns='method', 
        values='avg_errors',
        aggfunc='mean'
    )
    
    # Reorder columns
    column_order = ['zero_shot', 'few_shot', 'nl_to_format']
    pivot = pivot.reindex(columns=[c for c in column_order if c in pivot.columns], fill_value=np.nan)
    pivot = pivot.sort_index()
    
    print(f"\n📊 {dataset_name} Heatmap Data:")
    print("┌" + "─" * 60 + "┐")
    print(pivot.round(2).to_string())
    print("└" + "─" * 60 + "┘")
    
    # Create heatmap
    fig, ax = plt.subplots(figsize=(12, max(6, len(pivot) * 0.6)))
    
    # Use a colormap where lower is better
    cmap = sns.color_palette("RdYlGn_r", as_cmap=True)
    
    # Calculate vmin/vmax for consistent coloring
    vmin = pivot.min().min()
    vmax = pivot.max().max()
    
    sns.heatmap(
        pivot, 
        annot=True, 
        fmt='.1f',
        cmap=cmap,
        linewidths=2,
        linecolor='white',
        cbar_kws={'label': 'Average Total Errors'},
        square=True,
        annot_kws={'size': 13, 'fontweight': 'bold'},
        ax=ax,
        mask=pivot.isna(),
        vmin=vmin,
        vmax=vmax
    )
    
    # Formatting
    ax.set_title(f'📈 {dataset_name} - Average Total Errors by Model and Method', 
                 fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Method', fontsize=13, fontweight='bold')
    ax.set_ylabel('Model', fontsize=13, fontweight='bold')
    
    # Rotate x-axis labels
    plt.xticks(rotation=0, ha='center')
    plt.yticks(fontsize=11)
    
    plt.tight_layout()
    
    # Save
    save_path = f'{dataset_name}_heatmap.png'
    plt.savefig(save_path, dpi=200, bbox_inches='tight', facecolor='white')
    print(f"✅ Heatmap saved to: {save_path}")
    plt.close()
    
    return pivot

def create_combined_heatmap(df):
    """Create a combined heatmap across all datasets."""
    df['label'] = df['dataset'] + ' - ' + df['model']
    
    pivot = df.pivot_table(
        index='label', 
        columns='method', 
        values='avg_errors',
        aggfunc='mean'
    )
    
    column_order = ['zero_shot', 'few_shot', 'nl_to_format']
    pivot = pivot.reindex(columns=[c for c in column_order if c in pivot.columns], fill_value=np.nan)
    pivot = pivot.sort_index()
    
    print(f"\n📊 Combined Heatmap Data:")
    print("┌" + "─" * 70 + "┐")
    print(pivot.round(2).to_string())
    print("└" + "─" * 70 + "┘")
    
    fig, ax = plt.subplots(figsize=(14, max(8, len(pivot) * 0.5)))
    
    cmap = sns.color_palette("RdYlGn_r", as_cmap=True)
    
    vmin = pivot.min().min()
    vmax = pivot.max().max()
    
    sns.heatmap(
        pivot, 
        annot=True, 
        fmt='.1f',
        cmap=cmap,
        linewidths=2,
        linecolor='white',
        cbar_kws={'label': 'Average Total Errors'},
        square=True,
        annot_kws={'size': 10, 'fontweight': 'bold'},
        ax=ax,
        mask=pivot.isna(),
        vmin=vmin,
        vmax=vmax
    )
    
    ax.set_title('📊 Combined: Average Total Errors by Dataset, Model, and Method', 
                 fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Method', fontsize=13, fontweight='bold')
    ax.set_ylabel('Dataset - Model', fontsize=13, fontweight='bold')
    
    plt.xticks(rotation=0, ha='center')
    plt.tight_layout()
    
    plt.savefig('combined_heatmap.png', dpi=200, bbox_inches='tight', facecolor='white')
    print("✅ Combined heatmap saved to: combined_heatmap.png")
    plt.close()
    
    return pivot

def create_bar_chart(df):
    """Create a bar chart comparing all models and methods."""
    fig, ax = plt.subplots(figsize=(14, max(8, len(df) * 0.4)))
    
    # Sort and prepare data
    df_sorted = df.sort_values(['dataset', 'model', 'method'])
    df_sorted['label'] = df_sorted['dataset'] + ' - ' + df_sorted['model'] + ' (' + df_sorted['method'] + ')'
    
    # Colors
    colors = {'zero_shot': '#4A90D9', 'few_shot': '#F5A623', 'nl_to_format': '#7ED321'}
    df_sorted['color'] = df_sorted['method'].map(colors)
    
    # Create horizontal bar chart
    bars = ax.barh(df_sorted['label'], df_sorted['avg_errors'], color=df_sorted['color'], edgecolor='white', linewidth=1)
    
    # Add value labels
    for bar, val in zip(bars, df_sorted['avg_errors']):
        ax.text(val + 0.5, bar.get_y() + bar.get_height()/2, f'{val:.1f}', 
                va='center', ha='left', fontsize=9, fontweight='bold')
    
    ax.set_xlabel('Average Total Errors', fontsize=13, fontweight='bold')
    ax.set_title('📊 Model Performance Comparison by Dataset and Method', 
                 fontsize=16, fontweight='bold', pad=20)
    
    # Custom legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#4A90D9', label='zero_shot'),
        Patch(facecolor='#F5A623', label='few_shot'),
        Patch(facecolor='#7ED321', label='nl_to_format')
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=11)
    
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    plt.savefig('bar_chart_comparison.png', dpi=200, bbox_inches='tight', facecolor='white')
    print("✅ Bar chart saved to: bar_chart_comparison.png")
    plt.close()

def create_summary_table(df):
    """Create a summary table of best and worst performers."""
    print("\n" + "=" * 80)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 80)
    
    datasets = sorted(df['dataset'].unique())
    
    summary_data = []
    for dataset in datasets:
        df_ds = df[df['dataset'] == dataset]
        
        best = df_ds.loc[df_ds['avg_errors'].idxmin()]
        worst = df_ds.loc[df_ds['avg_errors'].idxmax()]
        
        summary_data.append({
            'Dataset': dataset,
            '🏆 Best Model': best['model'],
            'Best Method': best['method'],
            'Best Score': f"{best['avg_errors']:.1f}",
            '💀 Worst Model': worst['model'],
            'Worst Method': worst['method'],
            'Worst Score': f"{worst['avg_errors']:.1f}"
        })
    
    summary_df = pd.DataFrame(summary_data)
    print(summary_df.to_string(index=False))
    print("=" * 80)

def create_normalized_heatmap(df, dataset_name):
    """Create a normalized heatmap (0-100 scale)."""
    df_filtered = df[df['dataset'] == dataset_name]
    
    if df_filtered.empty:
        return None
    
    pivot = df_filtered.pivot_table(
        index='model', 
        columns='method', 
        values='avg_errors',
        aggfunc='mean'
    )
    
    column_order = ['zero_shot', 'few_shot', 'nl_to_format']
    pivot = pivot.reindex(columns=[c for c in column_order if c in pivot.columns], fill_value=np.nan)
    pivot = pivot.sort_index()
    
    # Normalize to 0-100 (0 = best, 100 = worst)
    min_val = pivot.min().min()
    max_val = pivot.max().max()
    if max_val - min_val > 0:
        normalized = ((pivot - min_val) / (max_val - min_val)) * 100
    else:
        normalized = pivot * 0
    
    fig, ax = plt.subplots(figsize=(12, max(6, len(pivot) * 0.6)))
    
    cmap = sns.color_palette("RdYlGn_r", as_cmap=True)
    
    sns.heatmap(
        normalized, 
        annot=True, 
        fmt='.1f',
        cmap=cmap,
        linewidths=2,
        linecolor='white',
        cbar_kws={'label': 'Normalized Score (0=Best, 100=Worst)'},
        square=True,
        annot_kws={'size': 13, 'fontweight': 'bold'},
        ax=ax,
        mask=pivot.isna(),
        vmin=0,
        vmax=100
    )
    
    ax.set_title(f'📊 {dataset_name} - Normalized Performance (0=Best, 100=Worst)', 
                 fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Method', fontsize=13, fontweight='bold')
    ax.set_ylabel('Model', fontsize=13, fontweight='bold')
    
    plt.xticks(rotation=0, ha='center')
    plt.tight_layout()
    
    save_path = f'{dataset_name}_normalized_heatmap.png'
    plt.savefig(save_path, dpi=200, bbox_inches='tight', facecolor='white')
    print(f"✅ Normalized heatmap saved to: {save_path}")
    plt.close()
    
    return normalized

def main():
    print("\n" + "=" * 80)
    print("📊 LOADING ERROR ANALYSIS DATA")
    print("=" * 80 + "\n")
    
    # Load data
    df = load_error_data('outputs')
    
    if df.empty:
        print("❌ No data found! Run error analysis first.")
        print("   python run_error_analysis_standalone.py --outputs outputs")
        return
    
    # Clean up method names
    df['method'] = df['method'].replace({
        'NL_to_format': 'nl_to_format',
        'nl_to_format': 'nl_to_format'
    })
    
    # Print summary
    print(f"✅ Loaded {len(df)} runs:")
    print("┌" + "─" * 80 + "┐")
    print(df[['dataset', 'model', 'method', 'avg_errors']].round(2).to_string(index=False))
    print("└" + "─" * 80 + "┘")
    
    # Create summary table
    create_summary_table(df)
    
    # Create heatmaps for each dataset
    datasets = sorted(df['dataset'].unique())
    for dataset in datasets:
        print(f"\n{'=' * 80}")
        print(f"📊 Creating visualizations for: {dataset}")
        print("=" * 80)
        
        create_heatmap(df, dataset)
        create_normalized_heatmap(df, dataset)
    
    # Create combined heatmap
    print(f"\n{'=' * 80}")
    print("📊 Creating combined visualizations")
    print("=" * 80)
    create_combined_heatmap(df)
    create_bar_chart(df)
    
    print("\n" + "=" * 80)
    print("✅ ALL VISUALIZATIONS COMPLETE!")
    print("=" * 80)
    print("\n📁 Generated files:")
    print("  ├── ARQA_heatmap.png")
    print("  ├── ARQA_normalized_heatmap.png")
    print("  ├── DeepJSONEval_heatmap.png")
    print("  ├── DeepJSONEval_normalized_heatmap.png")
    print("  ├── SchemaToJSON_heatmap.png")
    print("  ├── SchemaToJSON_normalized_heatmap.png")
    print("  ├── combined_heatmap.png")
    print("  └── bar_chart_comparison.png")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()