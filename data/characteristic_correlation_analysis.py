import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from pathlib import Path
import json
import warnings
warnings.filterwarnings('ignore')

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica']

# -------------------------------------------------------------------
# 1. Find directories
# -------------------------------------------------------------------
def find_outputs_dir():
    base_paths = [Path.cwd(), Path(__file__).parent, Path(__file__).parent.parent,
                  Path(__file__).parent.parent.parent]
    possible = ['outputs', 'pipeline/outputs', 'src/outputs', '../outputs', '../../outputs']
    for base in base_paths:
        for loc in possible:
            test_path = base / loc
            if test_path.exists() and test_path.is_dir():
                print(f"✅ Found outputs at: {test_path}")
                return str(test_path)
    raise FileNotFoundError("Outputs directory not found.")

# -------------------------------------------------------------------
# 2. Load error data
# -------------------------------------------------------------------
def load_error_data(outputs_dir=None):
    if outputs_dir is None:
        outputs_dir = find_outputs_dir()
    outputs_path = Path(outputs_dir)
    all_data = []
    for run_dir in outputs_path.iterdir():
        if not run_dir.is_dir():
            continue
        manifest_path = run_dir / "manifest.json"
        csv_path = run_dir / "error_analysis.csv"
        if not manifest_path.exists() or not csv_path.exists():
            continue
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        dataset = manifest.get('dataset')
        model = manifest.get('model', '').split('/')[-1]
        method = manifest.get('method', '')
        df_errors = pd.read_csv(csv_path)
        df_errors['dataset'] = dataset
        df_errors['model'] = model
        df_errors['method'] = method
        all_data.append(df_errors)
    if not all_data:
        raise ValueError("No error data loaded.")
    combined = pd.concat(all_data, ignore_index=True)
    return combined

# -------------------------------------------------------------------
# 3. Load characteristics
# -------------------------------------------------------------------
def load_characteristics(dataset_name, data_dir):
    csv_path = Path(data_dir) / f"{dataset_name}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV for {dataset_name} not found at {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"\n📋 Columns in {dataset_name}.csv: {list(df.columns)}")
    return df

# -------------------------------------------------------------------
# 4. Merge with aggregated errors (INTELLIGENT MERGE)
# -------------------------------------------------------------------
def merge_data_for_dataset(dataset_name, error_df, char_df):
    err_ds = error_df[error_df['dataset'] == dataset_name].copy()
    err_ds['row_id'] = err_ds['row_id'].astype(str)

    print(f"\n🔍 Sample row_id from error: {err_ds['row_id'].head(5).tolist()}")

    # --------------------------------------------------------------
    # CASE 1: ARQA – merge on 'qa_id'
    # --------------------------------------------------------------
    if dataset_name == 'ARQA':
        if 'qa_id' not in char_df.columns:
            print("❌ ARQA: 'qa_id' column missing in characteristic CSV")
            return None
        char_df['qa_id'] = char_df['qa_id'].astype(str)
        # Aggregate errors
        error_cols = [c for c in err_ds.columns if c.startswith(('arqa_', 'dj_', 's2j_'))]
        if not error_cols:
            print("❌ No error columns found")
            return None
        err_agg = err_ds.groupby('row_id', as_index=False)[error_cols].sum()
        if 'total_errors' in err_ds.columns:
            total_agg = err_ds.groupby('row_id')['total_errors'].sum().reset_index()
            err_agg = pd.merge(err_agg, total_agg, on='row_id', how='left')
        merged = pd.merge(char_df, err_agg, left_on='qa_id', right_on='row_id', how='inner')
        if merged.empty:
            print("⚠️  No rows matched on qa_id ↔ row_id")
            return None
        return merged

    # --------------------------------------------------------------
    # CASE 2: DeepJSONEval – row_id is "deepjson_0", "deepjson_1", ...
    # --------------------------------------------------------------
    elif dataset_name == 'DeepJSONEval':
        # Extract integer index from row_id
        try:
            err_ds['row_id_int'] = err_ds['row_id'].str.replace('deepjson_', '').astype(int)
        except:
            print("❌ Could not parse row_id for DeepJSONEval (expected 'deepjson_<int>')")
            return None
        # Use the row index of the characteristic CSV as key
        char_df = char_df.reset_index(drop=True)
        char_df['__index'] = char_df.index
        # Aggregate errors
        error_cols = [c for c in err_ds.columns if c.startswith(('arqa_', 'dj_', 's2j_'))]
        if not error_cols:
            print("❌ No error columns found")
            return None
        err_agg = err_ds.groupby('row_id_int', as_index=False)[error_cols].sum()
        if 'total_errors' in err_ds.columns:
            total_agg = err_ds.groupby('row_id_int')['total_errors'].sum().reset_index()
            err_agg = pd.merge(err_agg, total_agg, on='row_id_int', how='left')
        merged = pd.merge(char_df, err_agg, left_on='__index', right_on='row_id_int', how='inner')
        if merged.empty:
            print("⚠️  No rows matched on index ↔ row_id_int for DeepJSONEval")
            return None
        merged = merged.drop(columns=['__index', 'row_id_int'])
        return merged

    # --------------------------------------------------------------
    # CASE 3: SchemaToJSON – row_id is "schema_to_json_000000", ...
    # --------------------------------------------------------------
    elif dataset_name == 'SchemaToJSON':
        # Extract integer index from row_id
        try:
            err_ds['row_id_int'] = err_ds['row_id'].str.replace('schema_to_json_', '').astype(int)
        except:
            print("❌ Could not parse row_id for SchemaToJSON (expected 'schema_to_json_<int>')")
            return None
        char_df = char_df.reset_index(drop=True)
        char_df['__index'] = char_df.index
        # Aggregate errors
        error_cols = [c for c in err_ds.columns if c.startswith(('arqa_', 'dj_', 's2j_'))]
        if not error_cols:
            print("❌ No error columns found")
            return None
        err_agg = err_ds.groupby('row_id_int', as_index=False)[error_cols].sum()
        if 'total_errors' in err_ds.columns:
            total_agg = err_ds.groupby('row_id_int')['total_errors'].sum().reset_index()
            err_agg = pd.merge(err_agg, total_agg, on='row_id_int', how='left')
        merged = pd.merge(char_df, err_agg, left_on='__index', right_on='row_id_int', how='inner')
        if merged.empty:
            print("⚠️  No rows matched on index ↔ row_id_int for SchemaToJSON")
            return None
        merged = merged.drop(columns=['__index', 'row_id_int'])
        return merged

    else:
        print(f"❌ Unknown dataset: {dataset_name}")
        return None

# -------------------------------------------------------------------
# 5. Characteristic families
# -------------------------------------------------------------------
def get_characteristic_families():
    return {
        'Complexity': [
            'gold_json_length', 'nesting_depth', 'total_object_count',
            'max_array_nesting_depth', 'total_array_count', 'max_array_length',
            'total_key_count', 'unique_key_count', 'max_key_length'
        ],
        'Value   Types': [
            'long_text_value_count', 'numeric_value_count', 'value_types',
            'alphanumeric_value_count', 'max_value_length', 'average_value_length'
        ],
        'Structural': [
            'char_has_table_cells', 'char_has_text_spans',
            'table_cell_total_refs_count', 'claim_count',
            'max_evidence_items_per_claim'
        ],
        'Table Features': [
            'escaping_count', 'numeric_string_count', 'cell_record_count',
            'duplicate_record_count', 'table_cell_ref', 'long_text'
        ],
        'Schema Features': [
            'property_count', 'has_enum', 'array_of_objects',
            'array_of_primitives'
        ]
    }

# -------------------------------------------------------------------
# 6. Error groups (dataset-specific)
# -------------------------------------------------------------------
def get_error_groups():
    return {
        'ARQA': {
            'Hallucination': ['arqa_hallucinated_claims', 'arqa_hallucinated_claim_type', 'arqa_hallucinated_table_id'],
            'Claim Issues': ['arqa_wrong_claim_type', 'arqa_inaccurate_claims_evidence'],
            'Evidence Problems': ['arqa_missing_cell_text', 'arqa_empty_evidence_span'],
            'Structure': ['arqa_wrong_coordinates', 'arqa_missing_top_level_fields']
        },
        'DeepJSONEval': {
            'Schema Violations': ['dj_wrong_schema', 'dj_required_fields', 'dj_enum_check'],
            'Type Issues': ['dj_property_type', 'dj_top_level_not_object'],
            'Structure': ['dj_property_count', 'dj_titles_mismatch', 'dj_schema_echo']
        },
        'SchemaToJSON': {
            'Value Errors': ['s2j_cell_value_errors', 's2j_array_instead_of_string'],
            'Type Issues': ['s2j_hallucinated_type', 's2j_wrong_root_structure'],
            'Structure': ['s2j_fields_not_allowed', 's2j_missing_conditional_fields']
        }
    }

# -------------------------------------------------------------------
# 7. Correlation helper
# -------------------------------------------------------------------
def safe_corr(x, y):
    if not pd.api.types.is_numeric_dtype(x) or not pd.api.types.is_numeric_dtype(y):
        return None
    if x.nunique() <= 1 or y.nunique() <= 1:
        return None
    corr = x.corr(y)
    return corr if not pd.isna(corr) else None

# -------------------------------------------------------------------
# 8. Heatmap
# -------------------------------------------------------------------
def create_characteristic_error_heatmap(df_merged, dataset_name):
    if df_merged is None or df_merged.empty:
        return None

    char_families = get_characteristic_families()
    error_groups = get_error_groups().get(dataset_name, {})
    numeric_cols = df_merged.select_dtypes(include=[np.number]).columns.tolist()

    avail_chars = {}
    for family, cols in char_families.items():
        existing = [c for c in cols if c in numeric_cols]
        if existing:
            avail_chars[family] = existing

    avail_errors = {}
    for group, cols in error_groups.items():
        existing = [c for c in cols if c in numeric_cols]
        if existing:
            avail_errors[group] = existing

    if not avail_chars or not avail_errors:
        print(f"No numeric matching columns for {dataset_name}")
        return None

    family_avg = {}
    for fname, fcols in avail_chars.items():
        row_corrs = []
        for gname, ecols in avail_errors.items():
            all_corrs = []
            for c in fcols:
                c_data = df_merged[c]
                for e in ecols:
                    e_data = df_merged[e]
                    corr = safe_corr(c_data, e_data)
                    if corr is not None:
                        all_corrs.append(corr)
            if all_corrs:
                row_corrs.append(np.mean(all_corrs))
            else:
                row_corrs.append(0)
        if row_corrs:
            family_avg[fname] = row_corrs

    if not family_avg:
        print(f"No correlations computed for {dataset_name}")
        return None

    corr_df = pd.DataFrame(family_avg, index=list(avail_errors.keys())).T

    fig, ax = plt.subplots(figsize=(12, max(6, len(corr_df) * 0.8)))
    im = ax.imshow(corr_df.values, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)
    plt.colorbar(im, ax=ax, label='Average Correlation')
    ax.set_xticks(np.arange(len(corr_df.columns)))
    ax.set_yticks(np.arange(len(corr_df.index)))
    ax.set_xticklabels(corr_df.columns, rotation=45, ha='right', fontsize=10)
    ax.set_yticklabels(corr_df.index, fontsize=11)
    for i in range(len(corr_df.index)):
        for j in range(len(corr_df.columns)):
            val = corr_df.iloc[i, j]
            color = 'white' if abs(val) > 0.5 else 'black'
            ax.text(j, i, f'{val:.2f}', ha='center', va='center', color=color, fontsize=10, fontweight='bold')
    ax.set_title(f'{dataset_name}: Characteristic Families vs Error Groups\nCorrelation Heatmap',
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('Error Groups', fontsize=12, fontweight='bold')
    ax.set_ylabel('Characteristic Families', fontsize=12, fontweight='bold')
    ax.set_xticks(np.arange(-0.5, len(corr_df.columns), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(corr_df.index), 1), minor=True)
    ax.grid(which='minor', color='white', linestyle='-', linewidth=2)
    plt.tight_layout()
    plt.savefig(f'{dataset_name}_characteristic_heatmap.png', dpi=300, bbox_inches='tight')
    print(f"✅ Heatmap saved to: {dataset_name}_characteristic_heatmap.png")
    plt.close()

    print(f"\n📊 {dataset_name} - Characteristic-Error Correlations")
    print("=" * 80)
    for family in corr_df.index:
        print(f"\n{family}:")
        for err_group in corr_df.columns:
            val = corr_df.loc[family, err_group]
            strength = "Strong" if abs(val) > 0.5 else "Moderate" if abs(val) > 0.3 else "Weak"
            direction = "Positive" if val > 0 else "Negative" if val < 0 else "Neutral"
            print(f"  └─ {err_group}: {val:.3f} ({direction}, {strength})")
    return corr_df

# -------------------------------------------------------------------
# 9. Detailed correlation plot
# -------------------------------------------------------------------
def create_detailed_correlation_plot(df_merged, dataset_name):
    if df_merged is None or df_merged.empty:
        return

    numeric_cols = df_merged.select_dtypes(include=[np.number]).columns.tolist()
    char_families = get_characteristic_families()
    error_groups = get_error_groups().get(dataset_name, {})

    all_chars = []
    char_to_family = {}
    for family, cols in char_families.items():
        for col in cols:
            if col in numeric_cols:
                all_chars.append(col)
                char_to_family[col] = family

    all_errors = []
    error_to_group = {}
    for group, cols in error_groups.items():
        for col in cols:
            if col in numeric_cols:
                all_errors.append(col)
                error_to_group[col] = group

    if not all_chars or not all_errors:
        return

    corr_data = []
    for c in all_chars:
        c_data = df_merged[c]
        row = []
        for e in all_errors:
            e_data = df_merged[e]
            corr = safe_corr(c_data, e_data)
            row.append(corr if corr is not None else 0)
        corr_data.append(row)

    if not corr_data:
        return

    corr_df = pd.DataFrame(corr_data, index=all_chars, columns=all_errors)

    fig, axes = plt.subplots(1, 2, figsize=(20, max(8, len(corr_df) * 0.3)))
    im = axes[0].imshow(corr_df.values, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)
    axes[0].set_xticks(np.arange(len(corr_df.columns)))
    axes[0].set_yticks(np.arange(len(corr_df.index)))
    axes[0].set_xticklabels(corr_df.columns, rotation=90, fontsize=8)
    axes[0].set_yticklabels([col.replace('arqa_', '').replace('dj_', '').replace('s2j_', '')
                             for col in corr_df.index], fontsize=9)
    axes[0].set_title('Detailed Characteristic-Error Correlations', fontsize=12, fontweight='bold')
    plt.colorbar(im, ax=axes[0], label='Correlation Coefficient')

    if len(corr_df) > 1:
        family_corrs = {}
        for family in char_families.keys():
            family_cols = [col for col in corr_df.index if char_to_family.get(col) == family]
            if family_cols:
                family_corrs[family] = corr_df.loc[family_cols].mean()
        if family_corrs:
            family_df = pd.DataFrame(family_corrs).T
            im2 = axes[1].imshow(family_df.values, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)
            axes[1].set_xticks(np.arange(len(family_df.columns)))
            axes[1].set_yticks(np.arange(len(family_df.index)))
            axes[1].set_xticklabels(family_df.columns, rotation=45, ha='right', fontsize=9)
            axes[1].set_yticklabels(family_df.index, fontsize=10)
            for i in range(len(family_df.index)):
                for j in range(len(family_df.columns)):
                    val = family_df.iloc[i, j]
                    color = 'white' if abs(val) > 0.5 else 'black'
                    axes[1].text(j, i, f'{val:.2f}', ha='center', va='center', color=color, fontsize=9)
            axes[1].set_title('Family-Level Correlations', fontsize=12, fontweight='bold')
            plt.colorbar(im2, ax=axes[1], label='Average Correlation')

    plt.suptitle(f'{dataset_name}: Characteristic-Error Correlation Analysis',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(f'{dataset_name}_detailed_correlations.png', dpi=300, bbox_inches='tight')
    print(f"✅ Detailed correlation plot saved to: {dataset_name}_detailed_correlations.png")
    plt.close()

# -------------------------------------------------------------------
# 10. Main
# -------------------------------------------------------------------
def main():
    print("=" * 80)
    print("📊 CHARACTERISTIC-ERROR CORRELATION ANALYSIS")
    print("=" * 80 + "\n")

    try:
        error_df = load_error_data()
        data_dir = Path(r'C:\Users\Justin\SIP-git\schema-error-analysis\data')
        print(f"✅ Using data directory: {data_dir}")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return

    datasets = ['ARQA', 'DeepJSONEval', 'SchemaToJSON']
    for ds in datasets:
        print(f"\n{'=' * 80}")
        print(f"📊 Processing: {ds}")
        print("=" * 80)

        try:
            char_df = load_characteristics(ds, data_dir)
        except FileNotFoundError as e:
            print(f"⚠️  {e}")
            continue

        merged = merge_data_for_dataset(ds, error_df, char_df)
        if merged is None:
            continue

        print(f"✅ Merged {len(merged)} rows for {ds}")

        # Debug
        print("\n🔍 Debug info:")
        print(f"  Shape: {merged.shape}")
        numeric_cols = merged.select_dtypes(include=[np.number]).columns.tolist()
        print(f"  Numeric characteristic columns present: {[c for c in get_characteristic_families().values() if any(c2 in numeric_cols for c2 in c)]}")
        print(f"  Numeric error columns present: {[c for c in merged.columns if c.startswith(('arqa_', 'dj_', 's2j_')) and c in numeric_cols]}")
        sample_chars = ['gold_json_length', 'total_object_count', 'total_key_count']
        existing = [c for c in sample_chars if c in numeric_cols]
        if existing:
            print(f"  Variance of {existing}:")
            print(merged[existing].var())
        sample_errors = ['arqa_hallucinated_claims', 'dj_wrong_schema', 's2j_cell_value_errors']
        existing_err = [c for c in sample_errors if c in numeric_cols]
        if existing_err:
            print(f"  Variance of {existing_err}:")
            print(merged[existing_err].var())

        create_characteristic_error_heatmap(merged, ds)
        create_detailed_correlation_plot(merged, ds)

    print("\n" + "=" * 80)
    print("✅ COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    main()