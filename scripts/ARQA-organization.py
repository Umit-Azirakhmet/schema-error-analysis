import pandas as pd
import json

def check_null_types(obj):
    """Recursively checks for actual null (None) and string 'null'."""
    has_string_null = False
    has_actual_null = False
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            if value == "null":
                has_string_null = True
            elif value is None:
                has_actual_null = True
                
            # Recurse deeper
            if isinstance(value, (dict, list)):
                s_null, a_null = check_null_types(value)
                has_string_null = has_string_null or s_null
                has_actual_null = has_actual_null or a_null
                
    elif isinstance(obj, list):
        for item in obj:
            if item == "null":
                has_string_null = True
            elif item is None:
                has_actual_null = True
                
            # Recurse deeper
            if isinstance(item, (dict, list)):
                s_null, a_null = check_null_types(item)
                has_string_null = has_string_null or s_null
                has_actual_null = has_actual_null or a_null
                
    return has_string_null, has_actual_null

def append_characteristics(input_file, output_file):
    """Scans the dataset and appends characteristic flags as new CSV columns."""
    print(f"Loading dataset: {input_file}...")
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: Could not find {input_file}.")
        return

    # Initialize new columns to track our 3 characteristics
    df['char_has_table_ref'] = False
    df['char_has_para_ref'] = False
    df['char_has_table_cells'] = False
    df['char_has_text_spans'] = False
    df['char_has_actual_null'] = False
    df['char_has_string_null'] = False
    df['char_is_valid_json'] = True

    print("Analyzing schema characteristics...")
    
    for index, row in df.iterrows():
        gold_answer_str = row.get('gold_answer', '{}')
        if pd.isna(gold_answer_str):
            df.at[index, 'char_is_valid_json'] = False
            continue
            
        try:
            gold_answer = json.loads(gold_answer_str)
        except json.JSONDecodeError:
            df.at[index, 'char_is_valid_json'] = False
            continue

        # --- 3. Nullable Fields ---
        has_string_null, has_actual_null = check_null_types(gold_answer)
        df.at[index, 'char_has_string_null'] = has_string_null
        df.at[index, 'char_has_actual_null'] = has_actual_null

        # Flags for References and Optional Fields
        row_has_table_ref = False
        row_has_para_ref = False
        row_has_table_cells = False
        row_has_text_spans = False

        claims = gold_answer.get("claims", [])
        for claim in claims:
            evidence = claim.get("evidence", {})
            
            # --- 2. Optional Fields ---
            if "table_cells" in evidence:
                row_has_table_cells = True
                # --- 1. References (Table) ---
                for cell in evidence.get("table_cells", []):
                    if "table_id" in cell:
                        row_has_table_ref = True
                        
            # --- 2. Optional Fields ---
            if "text_spans" in evidence:
                row_has_text_spans = True
                # --- 1. References (Para) ---
                for span in evidence.get("text_spans", []):
                    if "para_id" in span:
                        row_has_para_ref = True
                        
        # Apply findings to the dataframe
        df.at[index, 'char_has_table_ref'] = row_has_table_ref
        df.at[index, 'char_has_para_ref'] = row_has_para_ref
        df.at[index, 'char_has_table_cells'] = row_has_table_cells
        df.at[index, 'char_has_text_spans'] = row_has_text_spans

    # Save the updated dataframe to a new CSV
    df.to_csv(output_file, index=False)
    
    print("-" * 40)
    print("PROCESSING COMPLETE")
    print("-" * 40)
    print(f"Total rows processed: {len(df)}")
    print(f"Output saved to:      {output_file}")
    print("\nNew columns added:")
    print(" - char_has_table_ref")
    print(" - char_has_para_ref")
    print(" - char_has_table_cells")
    print(" - char_has_text_spans")
    print(" - char_has_actual_null")
    print(" - char_has_string_null")

if __name__ == "__main__":
    # Ensure ARQA_cleaned.csv is in the same folder as this script
    append_characteristics('ARQA_cleaned.csv', 'ARQA_characteristics.csv')