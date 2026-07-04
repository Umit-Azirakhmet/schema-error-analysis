import csv
from pathlib import Path


def read_csv_rows(path):
    """
    Read a CSV file into a list of dictionaries.
    """
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def make_target_cells(row):
    """
    Format target cell information for SchemaToJSON prompts.

    The assignment says to use original table_code, sup_text, and target_cells fields.
    Your CSV already has a target_cells column, so preserve it directly.
    """
    return row.get("target_cells", "")


def load_schema_to_json(dataset_path, max_rows=None):
    """
    Load SchemaToJSON rows.

    SchemaToJSON has no dedicated ID column, so this creates one:
      schematojson_0, schematojson_1, ...

    It keeps original row values unchanged.
    """

    dataset_path = Path(dataset_path)
    rows = read_csv_rows(dataset_path)

    loaded = []

    for row_index, row in enumerate(rows):
        if max_rows is not None and row_index >= max_rows:
            break

        row_id = row.get("table_id", "") or row.get("paper_id", "") or f"schematojson_{row_index}"

        loaded.append({
            "dataset": "SchemaToJSON",
            "row_id": f"schematojson_{row_index}",
            "row_index": row_index,

            "prompt_fields": {
                "table_code": row.get("table_code", ""),
                "sup_text": row.get("sup_text", ""),
                "target_cells": make_target_cells(row),
            },

            # Save gold answer exactly as stored
            "gold_json_raw": row.get("gold_json_records", ""),

            "characteristics": {},
            "original_row": row,
        })

    return loaded