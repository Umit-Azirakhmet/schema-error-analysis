import pandas as pd
import json
import re

# Regex to match valid numbers (integers, decimals, scientific notation)
NUMERIC_REGEX = re.compile(r'^[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$')

def count_both_metrics(obj):
    """
    Recursively scans the JSON object.
    Returns a tuple: (numeric_string_count, cell_record_count)
    """
    num_count = 0
    cell_rec_count = 0
    
    # --- DOUBLE ENCODING & STRING CHECK ---
    if isinstance(obj, str):
        stripped = obj.strip()
        # If it looks like a hidden JSON object/array, unpack it
        if (stripped.startswith('{') and stripped.endswith('}')) or (stripped.startswith('[') and stripped.endswith(']')):
            try:
                unpacked_json = json.loads(stripped)
                return count_both_metrics(unpacked_json)
            except json.JSONDecodeError:
                pass 
                
        # If it's just a normal string, check if it's a numeric string
        elif NUMERIC_REGEX.match(stripped):
            return (1, 0)
            
        return (0, 0)
            
    # --- DICTIONARY RECURSION ---
    elif isinstance(obj, dict):
        if "cell_record" in obj and isinstance(obj["cell_record"], list):
            cell_rec_count += len(obj["cell_record"])
            
        for value in obj.values():
            n_c, c_r_c = count_both_metrics(value)
            num_count += n_c
            cell_rec_count += c_r_c
            
    # --- LIST RECURSION ---
    elif isinstance(obj, list):
        for item in obj:
            n_c, c_r_c = count_both_metrics(item)
            num_count += n_c
            cell_rec_count += c_r_c
            
    return (num_count, cell_rec_count)

def append_counts_to_csv(input_file, output_file):
    print(f"Loading dataset: {input_file}...\n")
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: Could not find {input_file}.")
        return

    if 'gold_json_records' not in df.columns:
        print("Error: The column 'gold_json_records' was not found in the CSV.")
        return

    # Initialize the two new columns with 0
    df['numeric_string_count'] = 0
    df['cell_record_count'] = 0

    print("Processing rows and adding new columns...")

    for index, row in df.iterrows():
        json_str = str(row['gold_json_records']).strip()
        if not json_str or json_str.lower() == 'nan':
            continue
            
        try:
            json_data = json.loads(json_str)
            
            # Get the counts for this specific row
            nums, cell_recs = count_both_metrics(json_data)
            
            # Inject those counts into the dataframe
            df.at[index, 'numeric_string_count'] = nums
            df.at[index, 'cell_record_count'] = cell_recs
                
        except json.JSONDecodeError:
            continue

    # Save the updated dataframe to a new CSV file
    df.to_csv(output_file, index=False)

    print("-" * 50)
    print("UPDATE COMPLETE")
    print("-" * 50)
    print(f"Total rows processed: {len(df)}")
    print(f"New columns added:    'numeric_string_count', 'cell_record_count'")
    print(f"Saved new file to:    {output_file}")
    print("-" * 50)

if __name__ == "__main__":
    # Ensure this matches your exact input file name
    input_filename = 'SchemaToJSON_characteristics_final.csv'
    output_filename = 'SchemaToJSON_characteristics_updated.csv'
    
    append_counts_to_csv(input_filename, output_filename)