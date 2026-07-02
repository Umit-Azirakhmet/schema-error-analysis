import pandas as pd
import json
import ast

# Read the CSV file
df = pd.read_csv('SchemaToJSON_characteristics_final.csv')

# Function to extract unique types from gold_json_records
def count_types_from_gold_records(gold_json_str):
    """
    Extract unique types from the cell_record entries in gold_json_records.
    """
    if pd.isna(gold_json_str) or gold_json_str == '':
        return 0
    
    try:
        # Parse the JSON
        if isinstance(gold_json_str, str):
            # Try to parse as JSON
            try:
                data = json.loads(gold_json_str)
            except json.JSONDecodeError:
                # Try using ast.literal_eval for Python-like dict strings
                try:
                    data = ast.literal_eval(gold_json_str)
                except:
                    return 0
        else:
            data = gold_json_str
        
        # Extract cell_record list
        if isinstance(data, dict) and 'cell_record' in data:
            cell_records = data['cell_record']
        else:
            return 0
        
        # Collect all unique types
        unique_types = set()
        for record in cell_records:
            try:
                # Parse the record if it's a string
                if isinstance(record, str):
                    try:
                        record_data = json.loads(record)
                    except json.JSONDecodeError:
                        try:
                            record_data = ast.literal_eval(record)
                        except:
                            continue
                else:
                    record_data = record
                
                # Extract the type field
                if isinstance(record_data, dict) and 'type' in record_data:
                    unique_types.add(record_data['type'])
                elif isinstance(record_data, str):
                    # Try to parse again if it's still a string
                    try:
                        nested_data = json.loads(record_data)
                        if 'type' in nested_data:
                            unique_types.add(nested_data['type'])
                    except:
                        pass
            except Exception as e:
                continue
        
        return len(unique_types)
    
    except Exception as e:
        return 0

# Alternative function to count primitive types from the actual data structure
def count_primitive_types_from_data(gold_json_str):
    """
    Count primitive types by looking at the structure of the data.
    """
    if pd.isna(gold_json_str) or gold_json_str == '':
        return 0
    
    try:
        # Parse the JSON
        if isinstance(gold_json_str, str):
            try:
                data = json.loads(gold_json_str)
            except json.JSONDecodeError:
                try:
                    data = ast.literal_eval(gold_json_str)
                except:
                    return 0
        else:
            data = gold_json_str
        
        # Get the cell_record
        if isinstance(data, dict) and 'cell_record' in data:
            cell_records = data['cell_record']
        else:
            return 0
        
        # Look for type information in the first few records
        types_found = set()
        for record in cell_records[:10]:  # Check first 10 records
            try:
                if isinstance(record, str):
                    # Try to find type pattern in the string
                    if '"type":' in record or "'type':" in record:
                        try:
                            record_data = json.loads(record)
                        except:
                            try:
                                record_data = ast.literal_eval(record)
                            except:
                                continue
                        
                        if isinstance(record_data, dict) and 'type' in record_data:
                            types_found.add(record_data['type'])
                elif isinstance(record, dict) and 'type' in record:
                    types_found.add(record['type'])
            except:
                continue
        
        return len(types_found) if types_found else 0
    
    except Exception as e:
        return 0

# Function to inspect the actual structure of gold_json_records for debugging
def inspect_record(gold_json_str):
    """
    Helper function to inspect the structure of gold_json_records.
    """
    if pd.isna(gold_json_str) or gold_json_str == '':
        return "Empty record"
    
    try:
        if isinstance(gold_json_str, str):
            try:
                data = json.loads(gold_json_str)
            except:
                try:
                    data = ast.literal_eval(gold_json_str)
                except:
                    return "Cannot parse"
        else:
            data = gold_json_str
        
        # Get the cell_record
        if isinstance(data, dict) and 'cell_record' in data:
            records = data['cell_record']
            if records:
                sample_record = records[0]
                # Try to parse the sample
                if isinstance(sample_record, str):
                    try:
                        parsed = json.loads(sample_record)
                        return parsed
                    except:
                        try:
                            parsed = ast.literal_eval(sample_record)
                            return parsed
                        except:
                            return sample_record[:100] + "..."
                else:
                    return sample_record
        return "No cell_record found"
    except:
        return "Error"

# Debug: Inspect a sample row
print("Inspecting a sample record:")
sample_gold = df['gold_json_records'].iloc[2]  # Using row with index 2
print(f"Raw gold_json_records: {sample_gold[:200]}...")
print(f"\nParsed structure: {inspect_record(sample_gold)}")
print("-" * 80)

# Apply the function to create the new column
df['number_of_types'] = df['gold_json_records'].apply(count_types_from_gold_records)

# Display the first few rows with the new column
print("\nSample of data with the new 'number_of_types' column:")
print(df[['paper_id', 'table_id', 'number_of_types']].head(20))

# Show distribution of types
print("\nDistribution of number_of_types:")
print(df['number_of_types'].value_counts().sort_index())

# Save the updated DataFrame
df.to_csv('SchemaToJSON_characteristics_final_with_types.csv', index=False)
print("\nUpdated CSV file saved as 'SchemaToJSON_characteristics_final_with_types.csv'")

# Show some examples of what types were found
print("\nNote: If all values are still 0, the type information may be stored differently.")
print("Let me check the actual structure of gold_json_records more carefully...")

# Check if there's any non-zero value
if df['number_of_types'].sum() == 0:
    print("\nAll values are 0. Let me try an alternative approach...")
    
    # Alternative: Look for type keywords in the raw string
    def count_types_raw(text):
        if pd.isna(text) or text == '':
            return 0
        # Look for "type" patterns
        import re
        # Find all occurrences of "type": "XXX"
        pattern = r'"type":\s*"([^"]+)"'
        matches = re.findall(pattern, str(text))
        return len(set(matches))
    
    df['number_of_types_alt'] = df['gold_json_records'].apply(count_types_raw)
    print("\nAlternative approach results:")
    print(df[['paper_id', 'table_id', 'number_of_types_alt']].head(20))
    print(f"Sum of types: {df['number_of_types_alt'].sum()}")
    
    # Use the alternative approach if it works
    if df['number_of_types_alt'].sum() > 0:
        df['number_of_types'] = df['number_of_types_alt']
        df.to_csv('SchemaToJSON_characteristics_final_with_types.csv', index=False)
        print("\nUpdated CSV file saved with the alternative approach.")