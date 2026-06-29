import pandas as pd

# Load the CSV file
df = pd.read_csv('DeepJSONEval_English_characterized (1).csv')

# Drop the true_depth column if it exists
if 'true_depth' in df.columns:
    df = df.drop(columns=['true_depth'])

# Convert boolean columns to numeric (1 for True, 0 for False)
# Identify columns with boolean values
bool_columns = ['has_array', 'array_of_objects', 'array_of_primitives', 'has_enum']

for col in bool_columns:
    if col in df.columns:
        # Convert True/False to 1/0
        df[col] = df[col].astype(int)

# Save the modified DataFrame to a new CSV file
df.to_csv('DeepJSONEval_English_characterized_modified.csv', index=False)

print("Conversion complete! Modified file saved as 'DeepJSONEval_English_characterized_modified.csv'")