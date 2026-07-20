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

def remove_outliers(data):
    """Remove outliers using IQR method."""
    if len(data) == 0:
        return data
    q1 = np.percentile(data, 25)
    q3 = np.percentile(data, 75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    return data[(data >= lower_bound) & (data <= upper_bound)]

def create_merged_box_whisker(df, dataset_name, characteristic_mapping):
    """Create a single merged box and whisker plot with all characteristics."""
    
    df_ds = df[df['dataset'] == dataset_name]
    
    if df_ds.empty:
        print(f"No data for {dataset_name}")
        return
    
    # Prepare data for all characteristics
    all_data = []
    all_labels = []
    all_colors = []
    
    # Color map for present vs absent
    present_color = '#E74C3C'  # Red
    absent_color = '#3498DB'   # Blue
    
    for char_col, char_label in characteristic_mapping.items():
        if char_col not in df_ds.columns:
            continue
        
        # Split data by characteristic presence
        present = df_ds[df_ds[char_col] > 0]['total_errors'].dropna().values
        absent = df_ds[df_ds[char_col] == 0]['total_errors'].dropna().values
        
        # Remove outliers
        present_clean = remove_outliers(present)
        absent_clean = remove_outliers(absent)
        
        # Only add if there's enough data
        if len(present_clean) > 3 and len(absent_clean) > 3:
            all_data.append(present_clean)
            all_labels.append(f'{char_label}\nPresent')
            all_colors.append(present_color)
            
            all_data.append(absent_clean)
            all_labels.append(f'{char_label}\nAbsent')
            all_colors.append(absent_color)
    
    if not all_data:
        print(f"No valid characteristics found for {dataset_name}")
        return
    
    # Calculate statistics for annotations
    stats = []
    for data in all_data:
        stats.append({
            'mean': np.mean(data),
            'median': np.median(data),
            'std': np.std(data),
            'n': len(data),
            'q1': np.percentile(data, 25),
            'q3': np.percentile(data, 75),
            'min': np.min(data),
            'max': np.max(data)
        })
    
    # Find global min and max for consistent scaling
    global_min = min([s['min'] for s in stats])
    global_max = max([s['max'] for s in stats])
    y_range = global_max - global_min
    
    # Calculate number of groups
    n_groups = len(all_data) // 2
    n_boxes = len(all_data)
    
    # Create figure with dynamic size
    fig_width = max(10, n_groups * 1.8)
    fig_height = max(6, 5 + n_groups * 0.3)
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    
    # Create box plot
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
    
    # Color the boxes
    for patch, color in zip(bp['boxes'], all_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)
        patch.set_edgecolor('#2C3E50')
        patch.set_linewidth(1.2)
    
    # Add jittered individual points (only if not too many)
    for i, data in enumerate(all_data):
        if len(data) <= 50:
            x = np.random.normal(i + 1, 0.06, size=len(data))
            ax.scatter(x, data, alpha=0.15, s=8, color=all_colors[i], zorder=1)
    
    # Add mean markers
    for i, stat in enumerate(stats):
        ax.scatter(i + 1, stat['mean'], color='#E74C3C', marker='D', 
                  s=50, zorder=3, edgecolor='white', linewidth=1)
    
    # Formatting
    ax.set_ylabel('Total Errors', fontsize=12, fontweight='bold', color='#2C3E50')
    ax.set_title(f'{dataset_name}: Error Distribution by Characteristic\n(Outliers Removed)', 
                 fontsize=14, fontweight='bold', pad=15, color='#2C3E50')
    
    # Set x-ticks
    ax.set_xticks(range(1, n_boxes + 1))
    ax.set_xticklabels(all_labels, fontsize=8, fontweight='bold', color='#2C3E50', rotation=45, ha='right')
    
    # Scale y-axis
    ax.set_ylim(global_min - 0.1 * y_range, global_max + 0.1 * y_range)
    
    # Clean up
    ax.tick_params(axis='y', labelsize=10, colors='#2C3E50')
    ax.grid(axis='y', alpha=0.2, linestyle='--', color='#BDC3C7')
    ax.set_axisbelow(True)
    
    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#2C3E50')
    ax.spines['bottom'].set_color('#2C3E50')
    
    # Add effect annotations below the plot
    for i in range(0, n_boxes, 2):
        if i + 1 < n_boxes:
            char_label = all_labels[i].replace('\nPresent', '')
            diff = stats[i]['mean'] - stats[i+1]['mean']
            effect = "⬆️" if diff > 0 else "⬇️" if diff < 0 else "➖"
            ax.text(i + 1.5, -0.06 * y_range, f'{effect} {abs(diff):.1f}',
                   ha='center', va='top', fontsize=7, color='#2C3E50',
                   transform=ax.get_xaxis_transform())
    
    # Legend
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    
    legend_elements = [
        Patch(facecolor='#E74C3C', alpha=0.5, edgecolor='#2C3E50', label='Present'),
        Patch(facecolor='#3498DB', alpha=0.5, edgecolor='#2C3E50', label='Absent'),
        Line2D([0], [0], marker='D', color='w', markerfacecolor='#E74C3C', 
               markersize=8, label='Mean'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#BDC3C7', 
               markersize=5, alpha=0.15, label='Data Points')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=9, 
              framealpha=0.9, edgecolor='#BDC3C7', fancybox=True)
    
    plt.tight_layout()
    
    # Save
    save_path = f'{dataset_name}_merged_box_whisker.png'
    plt.savefig(save_path, dpi=200, bbox_inches='tight', 
                facecolor='white', edgecolor='none', pad_inches=0.05)
    print(f"✅ Merged box and whisker saved to: {save_path}")
    plt.close()
    
    # Print summary
    print(f"\n📊 {dataset_name} - Merged Box and Whisker Summary")
    print("=" * 100)
    print(f"{'Characteristic':<30} {'Group':<8} {'Mean':<10} {'Median':<10} {'Std':<10} {'N':<8} {'Effect':<10}")
    print("-" * 100)
    
    for i, (label, stat) in enumerate(zip(all_labels, stats)):
        char_name = label.replace('\nPresent', '').replace('\nAbsent', '')
        group = 'Present' if 'Present' in label else 'Absent'
        if i % 2 == 0 and i + 1 < len(stats):
            diff = stats[i]['mean'] - stats[i+1]['mean']
            effect = "⬆️" if diff > 0 else "⬇️" if diff < 0 else "➖"
        else:
            effect = ""
        
        print(f"{char_name:<30} {group:<8} {stat['mean']:<10.1f} {stat['median']:<10.1f} {stat['std']:<10.1f} {stat['n']:<8} {effect:<10}")

def create_all_merged_box_whiskers(df):
    """Create merged box and whisker plots for all datasets."""
    
    configs = {
        'ARQA': {
            'arqa_hallucinated_claims': 'Hallucinated Claims',
            'arqa_wrong_claim_type': 'Wrong Claim Type',
            'arqa_hallucinated_table_id': 'Hallucinated Table ID',
            'arqa_missing_cell_text': 'Missing Cell Text',
            'arqa_wrong_coordinates': 'Wrong Coordinates',
            'arqa_empty_evidence_span': 'Empty Evidence Span',
            'arqa_inaccurate_claims_evidence': 'Inaccurate Claims Evidence'
        },
        'DeepJSONEval': {
            'dj_wrong_schema': 'Wrong Schema',
            'dj_schema_echo': 'Schema Echo',
            'dj_required_fields': 'Required Fields Error',
            'dj_property_count': 'Property Count Error',
            'dj_enum_check': 'Enum Check Error',
            'dj_property_type': 'Property Type Error'
        },
        'SchemaToJSON': {
            's2j_wrong_root_structure': 'Wrong Root Structure',
            's2j_cell_value_errors': 'Cell Value Errors',
            's2j_array_instead_of_string': 'Array Instead of String',
            's2j_hallucinated_type': 'Hallucinated Type',
            's2j_fields_not_allowed': 'Fields Not Allowed'
        }
    }
    
    for dataset_name, char_mapping in configs.items():
        if dataset_name not in df['dataset'].unique():
            print(f"\n⚠️  No data for {dataset_name}, skipping...")
            continue
        
        print(f"\n{'=' * 80}")
        print(f"📊 Processing: {dataset_name}")
        print("=" * 80)
        
        create_merged_box_whisker(df, dataset_name, char_mapping)

def main():
    print("=" * 80)
    print("📊 MERGED BOX AND WHISKER PLOTS")
    print("=" * 80 + "\n")
    
    df = load_all_data('outputs')
    
    if df.empty:
        print("❌ No data found!")
        return
    
    print(f"✅ Loaded {len(df)} responses")
    print(f"   Datasets: {df['dataset'].unique().tolist()}")
    
    create_all_merged_box_whiskers(df)
    
    print("\n" + "=" * 80)
    print("✅ COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    main()