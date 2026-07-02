#!/usr/bin/env python3
"""Add characteristic columns to SchemaToJSON raw CSV.

Reads data/other-versions/SchemaToJSON_raw.csv, computes per-row characteristics
from gold_json_records (and supporting row fields), and writes data/SchemaToJson.csv.

New columns (appended after all raw columns):
  - escaping_count          — from schema2json.py: count of \\\" in gold_json_records
  - numeric_string_count    — from s2janalyze.py: numeric strings in parsed JSON
  - cell_record_count       — from s2janalyze.py: length of cell_record list
  - duplicate_record_count  — from analyze_duplicate_records.py: max duplicate frequency
  - table_cell_ref          — from organize_datasets.py: table cell reference errors
  - long_text               — from organize_datasets.py: long-text field errors
  - gold_json_length        — character length of the raw gold_json_records string
  - nesting_depth           — max object/array nesting depth (root object = 1)
  - total_object_count      — number of JSON objects in the fully unpacked tree
  - max_array_nesting_depth — deepest stack of nested arrays (e.g. [[1,2]] = 2)
  - total_array_count       — number of JSON arrays in the fully unpacked tree
  - max_array_length        — largest array length anywhere in the tree
  - total_key_count         — total key occurrences across all objects
  - unique_key_count        — distinct key names across all objects
  - max_key_length          — longest object key name (characters)
  - long_text_value_count   — leaf strings that look sentence/paragraph-like
  - numeric_value_count     — leaf values that are numbers or numeric strings
  - alphanumeric_value_count — leaf strings with both letters and digits (e.g. GaS3/2)
  - max_value_length        — longest leaf value when rendered as text
  - average_value_length    — mean leaf value length (0 when no leaf values)
  - value_types             — comma-separated present leaf types: boolean, number, string

Usage:
  python scripts/SchemaToJson-add-fields.py
  python scripts/SchemaToJson-add-fields.py --input path/to/raw.csv --output path/to/out.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_duplicate_records import count_row_duplicates  # noqa: E402
from gold_json_analysis import analyze_gold_json_structure  # noqa: E402
from organize_datasets import (  # noqa: E402
    aggregate_errors_by_row,
    load_schematojson_row_from_series,
    run_all_checks,
)
from s2janalyze import count_both_metrics  # noqa: E402

DEFAULT_INPUT = ROOT / "data" / "other-versions" / "SchemaToJSON_raw.csv"
DEFAULT_OUTPUT = ROOT / "data" / "SchemaToJson.csv"

GOLD_COLUMN = "gold_json_records"
NEW_COLUMNS = [
    "escaping_count",
    "numeric_string_count",
    "cell_record_count",
    "duplicate_record_count",
    "table_cell_ref",
    "long_text",
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

def count_escaping(gold_raw: object) -> int:
    """Count escaped quotes (\\\") in the raw gold_json_records string (schema2json.py)."""
    return str(gold_raw if gold_raw is not None else "").count('\\"')


def count_s2j_metrics(gold_raw: object) -> tuple[int, int]:
    """Return (numeric_string_count, cell_record_count) from s2janalyze.py."""
    json_str = str(gold_raw).strip()
    if not json_str or json_str.lower() == "nan":
        return 0, 0
    try:
        json_data = json.loads(json_str)
    except json.JSONDecodeError:
        return 0, 0
    return count_both_metrics(json_data)


def schematojson_error_flags(row: pd.Series) -> tuple[int, int]:
    """Return (table_cell_ref, long_text) flags from organize_datasets.py checks."""
    schematojson_row = load_schematojson_row_from_series(row)
    findings = run_all_checks([schematojson_row])
    row_errors = aggregate_errors_by_row(findings).get(0, {})
    return int(bool(row_errors.get("table_cell_ref", 0))), int(bool(row_errors.get("long_text", 0)))


def enrich_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if GOLD_COLUMN not in df.columns:
        raise ValueError(f"Missing required column {GOLD_COLUMN!r}")

    added_columns: dict[str, list[Any]] = {column: [] for column in NEW_COLUMNS}

    for _, row in df.iterrows():
        gold_raw = row[GOLD_COLUMN]

        added_columns["escaping_count"].append(count_escaping(gold_raw))

        nums, cell_recs = count_s2j_metrics(gold_raw)
        added_columns["numeric_string_count"].append(nums)
        added_columns["cell_record_count"].append(cell_recs)

        added_columns["duplicate_record_count"].append(count_row_duplicates(gold_raw))

        table_cell_ref, long_text = schematojson_error_flags(row)
        added_columns["table_cell_ref"].append(table_cell_ref)
        added_columns["long_text"].append(long_text)

        structure = analyze_gold_json_structure(gold_raw)
        for column in NEW_COLUMNS[6:]:
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
        description="Add gold_json_records characteristic columns to SchemaToJSON raw CSV."
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
