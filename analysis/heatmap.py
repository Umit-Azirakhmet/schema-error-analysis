import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io

# --- STEP 1: Full Raw Data Reconstruction (Based on image_0.png) ---
# We use the raw values from the left heatmap of image_0.png.
# We also pre-split the 'Dataset - Model' field.
raw_data_string = """
Dataset,Model,zero_shot,few_shot,to_format
ARQA,Qwen/Qwen3-8B,19212.5,17635.2,15781.4
ARQA,google/gemma-3-4b-it,18476.7,18112.1,17989.5
ARQA,meta-llama/Llama-3.1-8B-Instruct,18413.9,19034.4,18218.0
ARQA,mistralai/Mistral-7B-Instruct-v0.3,17989.6,17377.1,18827.8
DeepJSONEval,Qwen/Qwen3-8B,1109.2,8931.5,7146.6
DeepJSONEval,google/gemma-3-4b-it,1987.4,945059.5,2280.4
DeepJSONEval,meta-llama/Llama-3.1-8B-Instruct,84117.5,35749.8,57017.5
DeepJSONEval,mistralai/Mistral-7B-Instruct-v0.3,101600.8,41893.4,12855.8
SchemaToJSON,Qwen/Qwen3-8B,92207.8,63963.1,80988.5
SchemaToJSON,google/gemma-3-4b-it,245433.8,44781.0,27339.4
SchemaToJSON,meta-llama/Llama-3.1-8B-Instruct,2096024.2,282188.0,160440.0
SchemaToJSON,mistralai/Mistral-7B-Instruct-v0.3,176589.2,55154.4,77765.0
"""

# Load string data into DataFrame
df = pd.read_csv(io.StringIO(raw_data_string.strip()))

# Define the columns that represent numerical error scores
methods_cols = ['zero_shot', 'few_shot', 'to_format']


# --- STEP 2: Calculate Global Normalization M (Based on image_1.png) ---
# Flatten the data to find the 95th percentile (M) of ALL errors.
all_raw_errors = df[methods_cols].values.flatten()
M = np.percentile(all_raw_errors, 95)
print(f"Calculated Global 95th Percentile (M): {M:.2f}")


# --- STEP 3: Apply the Log Normalization Formula ---
# x' = log(1+x) / log(1+M)
# Scaled by 100 for visual consistency.
def apply_log_norm_formula(x_raw, M_bound):
    """
    Applies the log normalization, clips values above M, and scales to 0-100.
    """
    # np.clip handles the "values above M clipped to 1" rule (after division).
    # np.log1p handles log(1+x) cleanly, preventing errors with zero values.
    normalized = np.log1p(np.clip(x_raw, 0, M_bound)) / np.log1p(M_bound)
    return normalized * 100

# Create a normalized version of the numeric columns
df_normalized = df.copy()
for method in methods_cols:
    df_normalized[method] = apply_log_norm_formula(df_normalized[method], M)


# --- STEP 4: Generate Distinct Heatmaps per Dataset ---
unique_datasets = df_normalized['Dataset'].unique()

# Pre-define some plotting parameters for consistency
plt.rcParams['font.family'] = 'DejaVu Sans' # A common, clean font
heatmap_aspect_ratio = 1.0 # Force heatmaps to be roughly square
color_scale = "RdYlGn_r" # Red (Bad) -> Green (Good) diverging colormap

for dataset_name in unique_datasets:
    print(f"Generating heatmap for: {dataset_name}")
    
    # Subset data for the current dataset and drop the dataset column for plotting
    subset_df = df_normalized[df_normalized['Dataset'] == dataset_name]
    subset_plotting_df = subset_df.drop(columns=['Dataset'])
    
    # Set the Model column as index (this creates the Y-axis labels)
    pivoted_df = subset_plotting_df.set_index('Model')
    
    # Ensure column order matches image (X-axis)
    pivoted_df = pivoted_df[methods_cols]

    # Initialize the plot figure
    fig, ax = plt.subplots(figsize=(8, 6), dpi=120)
    
    # Generate the Seaborn Heatmap
    sns.heatmap(
        pivoted_df,
        annot=True,              # Overlay numeric values
        fmt=".1f",              # One decimal place
        cmap=color_scale,        # Red-Green colormap
        linewidths=.5,           # Small grid spacing
        vmin=0,                  # Fixed scale starting at 0 (Best)
        vmax=100,                # Fixed scale ending at 100 (Worst)
        cbar_kws={'label': 'Normalized Score (0=Best, 100=Worst)'},
        square=True              # Forces square cells
    )
    
    # Set Plot Formatting
    plt.title(f"Normalized Errors: {dataset_name}\n(Log Normalization based on Global M={M:.1f})", fontsize=14, weight='bold')
    plt.ylabel('Model', fontsize=12)
    plt.xlabel('Method', fontsize=12)
    
    # Save the plot as a PNG
    output_filename = f"Heatmap_{dataset_name.replace('/', '_')}.png"
    plt.savefig(output_filename, bbox_inches='tight', pad_inches=0.1)
    
    # Close the plot to free memory
    plt.close()

print("\nDone. Heatmaps generated as separate PNG files.")