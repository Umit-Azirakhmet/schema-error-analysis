import csv
from pathlib import Path


def read_csv_rows(path):
    """
    Read a CSV file into a list of dictionaries.
    """
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def find_first_existing(row, candidates):
    """
    Return the first column value that exists in the row.
    This helps because DeepJSONEval column names may vary slightly.
    """
    for col in candidates:
        if col in row and row[col] != "":
            return row[col]
    return ""


def load_deepjson(dataset_path, max_rows=None):
    """
    Load DeepJSONEval rows.

    DeepJSONEval has no dedicated ID column, so this creates one:
      deepjson_0, deepjson_1, ...

    It keeps original row values unchanged.
    """

    dataset_path = Path(dataset_path)
    rows = read_csv_rows(dataset_path)

    loaded = []

    for row_index, row in enumerate(rows):
        if max_rows is not None and row_index >= max_rows:
            break

        # Try common possible column names
        text = find_first_existing(row, [
            "text",
            "source_text",
            "input_text",
            "prompt",
            "content"
        ])

        schema = find_first_existing(row, [
            "schema",
            "json_schema",
            "Schema",
            "JSON Schema"
        ])

        gold = find_first_existing(row, [
            "gold_json",
            "gold",
            "answer",
            "output",
            "target_json",
            "json_output"
        ])

        loaded.append({
            "dataset": "DeepJSONEval",
            "row_id": f"deepjson_{row_index}",
            "row_index": row_index,

            "prompt_fields": {
                "text": text,
                "schema": schema,
            },

            "gold_json_raw": gold,
            "characteristics": {},
            "original_row": row,
        })

    return loaded