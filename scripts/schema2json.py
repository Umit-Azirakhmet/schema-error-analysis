import pandas as pd
from pathlib import Path

# ==========================================================
# PURPOSE:
# For each row in the SchemaToJSON CSV, count \"
#
# It only looks at the gold answer column:
#   gold_json_records
#
# It adds one new column:
#   escaping_count
#
# Example:
# If a row's gold_json_records contains 50 instances of \",
# then escaping_count = 50 for that row.
# ==========================================================

# Find SchemaToJSON CSV in the same folder
csv_files = list(Path(".").glob("*SchemaToJSON*characteristics*final*.csv"))

if not csv_files:
    csv_files = list(Path(".").glob("*jsontoschema*final*.csv"))

if not csv_files:
    raise FileNotFoundError(
        "Could not find the SchemaToJSON CSV. Make sure the CSV is in the same folder as this script."
    )

INPUT_FILE = csv_files[0]
print(f"Using file: {INPUT_FILE}")

# Load CSV
df = pd.read_csv(INPUT_FILE)

# Gold answer column
GOLD_COL = "gold_json_records"

if GOLD_COL not in df.columns:
    raise ValueError(
        f"Column '{GOLD_COL}' not found. Available columns are: {list(df.columns)}"
    )

# Count ONLY escaped quotes: \"
df["escaping_count"] = df[GOLD_COL].fillna("").astype(str).apply(lambda x: x.count('\\"'))

# Save new CSV with the new per-row column
OUTPUT_FILE = "SchemaToJSON_with_per_row_escaping_count.csv"
df.to_csv(OUTPUT_FILE, index=False)

print()
print("Done.")
print(f"Total rows: {len(df)}")
print(f"Saved output to: {OUTPUT_FILE}")
print()
print("First 10 rows:")
print(df[["escaping_count"]].head(10).to_string(index=False))