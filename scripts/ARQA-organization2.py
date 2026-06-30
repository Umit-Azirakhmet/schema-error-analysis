import pandas as pd
import json
import ast

# Input file: your original ARQA dataset
CSV_FILE = "/Users/kiratpersonal/Downloads/arqa - ARQA_validated.csv"

# Output file: same rows, but with extra count columns added
OUTPUT_FILE = "/Users/kiratpersonal/Downloads/ARQA_with_table_cell_reference_counts.csv"

df = pd.read_csv(CSV_FILE)


def try_parse_json(value):
    """
    Tries to parse JSON-like text from the CSV.
    """
    if pd.isna(value):
        return None

    if not isinstance(value, str):
        return value

    value = value.strip()

    if value == "":
        return None

    try:
        return json.loads(value)
    except:
        try:
            return ast.literal_eval(value)
        except:
            return None


def count_refs_in_object(obj):
    """
    Searches one parsed object and counts table cell references.

    Categories:
    - row only
    - column only
    - column & row
    """

    counts = {
        "table_cell_row_only_count": 0,
        "table_cell_column_only_count": 0,
        "table_cell_column_and_row_count": 0,
        "table_cell_total_refs_count": 0
    }

    seen = set()

    def count_cell(cell):
        if not isinstance(cell, dict):
            return

        # Avoid double-counting the exact same dictionary object
        cell_id = id(cell)
        if cell_id in seen:
            return
        seen.add(cell_id)

        has_row = "row" in cell and cell["row"] not in [None, ""]
        has_col = "col" in cell and cell["col"] not in [None, ""]

        if has_row or has_col:
            counts["table_cell_total_refs_count"] += 1

            if has_row and has_col:
                counts["table_cell_column_and_row_count"] += 1
            elif has_row:
                counts["table_cell_row_only_count"] += 1
            elif has_col:
                counts["table_cell_column_only_count"] += 1

    def search(obj):
        if isinstance(obj, dict):

            # Format 1: {"table_cells": [...]}
            if "table_cells" in obj and isinstance(obj["table_cells"], list):
                for cell in obj["table_cells"]:
                    count_cell(cell)

            # Format 2: {"cell": {...}}
            if "cell" in obj and isinstance(obj["cell"], dict):
                count_cell(obj["cell"])

            # Format 3: direct table cell reference
            if "table_id" in obj and ("row" in obj or "col" in obj):
                count_cell(obj)

            # Keep searching deeper
            for value in obj.values():
                search(value)

        elif isinstance(obj, list):
            for item in obj:
                search(item)

    search(obj)
    return counts


def count_refs_in_row(row):
    """
    Counts table cell references across one full CSV row.
    """

    row_counts = {
        "table_cell_row_only_count": 0,
        "table_cell_column_only_count": 0,
        "table_cell_column_and_row_count": 0,
        "table_cell_total_refs_count": 0
    }

    # Search every cell in the row because references may appear in gold_answer,
    # program, evidence, etc.
    for value in row:
        parsed = try_parse_json(value)
        counts = count_refs_in_object(parsed)

        for key in row_counts:
            row_counts[key] += counts[key]

    return pd.Series(row_counts)


# Add count columns to the original dataframe
count_columns = df.apply(count_refs_in_row, axis=1)

df_output = pd.concat([df, count_columns], axis=1)

# Save the new full CSV
df_output.to_csv(OUTPUT_FILE, index=False)

print("Done!")
print(f"Saved full row-by-row CSV to: {OUTPUT_FILE}")
print()
print("Total counts:")
print(df_output[
    [
        "table_cell_row_only_count",
        "table_cell_column_only_count",
        "table_cell_column_and_row_count",
        "table_cell_total_refs_count"
    ]
].sum())