#!/usr/bin/env python3
"""Add characteristic columns to DeepJSONEval raw CSV.

Reads data/other-versions/DeepJSONEval_raw.csv, computes per-row characteristics
from the json column (and schema-based features from the schema column), and
writes data/DeepJSONEval.csv.

New columns (appended after all raw columns):
  - array_of_objects       — from organize_datasets.py: schema has array-of-object fields
  - array_of_primitives    — from organize_datasets.py: schema has array-of-primitive fields
  - has_enum               — from organize_datasets.py: schema uses enum keyword
  - property_count         — from organize_datasets.py: total properties across schema objects
  - gold_json_length       — character length of the raw json string
  - nesting_depth          — max object/array nesting depth in json (root object = 1)
  - total_object_count     — number of JSON objects in the fully unpacked json tree
  - max_array_nesting_depth — deepest stack of nested arrays in json
  - total_array_count      — number of JSON arrays in the fully unpacked json tree
  - max_array_length       — largest array length anywhere in json
  - total_key_count        — total key occurrences across all json objects
  - unique_key_count       — distinct key names across all json objects
  - max_key_length         — longest object key name in json (characters)
  - long_text_value_count  — leaf strings that look sentence/paragraph-like
  - numeric_value_count    — leaf values that are numbers or numeric strings
  - alphanumeric_value_count — leaf strings with both letters and digits
  - max_value_length       — longest leaf value when rendered as text
  - average_value_length   — mean leaf value length (0 when no leaf values)
  - value_types            — comma-separated present leaf types: boolean, number, string

Usage:
  python scripts/DeepJSONEval-add-fields.py
  python scripts/DeepJSONEval-add-fields.py --input path/to/raw.csv --output path/to/out.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from gold_json_analysis import analyze_gold_json_structure  # noqa: E402
from organize_datasets import (  # noqa: E402
    characterize_deepjsoneval_schema,
    try_parse_json,
)

DEFAULT_INPUT = ROOT / "data" / "other-versions" / "DeepJSONEval_raw.csv"
DEFAULT_OUTPUT = ROOT / "data" / "DeepJSONEval.csv"

JSON_COLUMN = "json"
SCHEMA_COLUMN = "schema"
SCHEMA_COLUMNS = [
    "array_of_objects",
    "array_of_primitives",
    "has_enum",
    "property_count",
]
STRUCTURE_COLUMNS = [
    "gold_json_length",
    "nesting_depth",
    "total_object_count",
    "max_array_nesting_depth",
    "total_array_count",
    "max_array_length",
    "total_key_count",
    "unique_key_count",
    "max_key_length",
    "long_text_value_count",
    "numeric_value_count",
    "alphanumeric_value_count",
    "max_value_length",
    "average_value_length",
    "value_types",
]
NEW_COLUMNS = SCHEMA_COLUMNS + STRUCTURE_COLUMNS


def analyze_schema_characteristics(schema_raw: object) -> dict[str, int]:
    """Return schema-based DeepJSONEval characteristics from organize_datasets.py."""
    defaults = {column: 0 for column in SCHEMA_COLUMNS}
    parsed = try_parse_json(schema_raw)
    if not isinstance(parsed, dict):
        return defaults

    schema_chars = characterize_deepjsoneval_schema(parsed)
    return {column: int(schema_chars.get(column, 0)) for column in SCHEMA_COLUMNS}


def enrich_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if JSON_COLUMN not in df.columns:
        raise ValueError(f"Missing required column {JSON_COLUMN!r}")
    if SCHEMA_COLUMN not in df.columns:
        raise ValueError(f"Missing required column {SCHEMA_COLUMN!r}")

    added_columns: dict[str, list[Any]] = {column: [] for column in NEW_COLUMNS}

    for _, row in df.iterrows():
        schema_chars = analyze_schema_characteristics(row[SCHEMA_COLUMN])
        for column in SCHEMA_COLUMNS:
            added_columns[column].append(schema_chars[column])

        structure = analyze_gold_json_structure(row[JSON_COLUMN])
        for column in STRUCTURE_COLUMNS:
            added_columns[column].append(structure[column])

    out = df.copy()
    for column in NEW_COLUMNS:
        out[column] = added_columns[column]
    return out


def add_fields(input_path: Path, output_path: Path) -> dict[str, int]:
    df = pd.read_csv(input_path, dtype=str, keep_default_na=False)
    enriched = enrich_dataframe(df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(output_path, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)

    return {
        "rows_processed": len(enriched),
        "columns": len(enriched.columns),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add json/schema characteristic columns to DeepJSONEval raw CSV."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input raw CSV (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        return 1

    try:
        stats = add_fields(args.input, args.output)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        f"Wrote {stats['rows_processed']} rows ({stats['columns']} columns) to {args.output}"
    )
    print(f"New columns: {', '.join(NEW_COLUMNS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
