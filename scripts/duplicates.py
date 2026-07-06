import pandas as pd
import re

# Load the CSV (same folder as this script)
input_file = "SchemaToJSON_characteristics_final_with_types.csv"
df = pd.read_csv(input_file)

# Column containing the primitive types
column_name = "primitive_types"

def count_record_types(value):
    # Handle missing values
    if pd.isna(value):
        return 0

    value = str(value).strip()

    # Empty string or empty list
    if value == "" or value == "[]":
        return 0

    # Remove brackets and quotes if present
    value = value.replace("[", "").replace("]", "")
    value = value.replace("'", "").replace('"', "")

    # Split on commas, semicolons, or pipes
    items = re.split(r"[,;|]", value)

    # Remove whitespace and empty entries
    items = [item.strip() for item in items if item.strip()]

    return len(items)

# Add the new numeric column
df["record_type_count"] = df[column_name].apply(count_record_types)

# Save the updated CSV in the same folder
output_file = "SchemaToJSON_characteristics_final_with_types_count.csv"
df.to_csv(output_file, index=False)

print(f"Done! File saved as: {output_file}")