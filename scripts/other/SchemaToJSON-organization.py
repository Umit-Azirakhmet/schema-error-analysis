"""Enrich SchemaToJSON_discomatTrain.csv with error flags and data characteristics.

Appends columns matching the ARQA_validated.csv style:
  mixed_data, polymorphic, repeated_key, table_cell_ref,
  required_field, long_text, char_span_ref, has_start_end

Per-row values are 0 (absent / no error) or 1 (present / at least one finding).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from project_script import (  # noqa: E402
    ALL_ERROR_TYPES,
    ERROR_LONG_TEXT_FIELDS,
    ERROR_MIXED_DATA_TYPES,
    ERROR_POLYMORPHIC_FIELDS,
    ERROR_REPEATED_KEY_NAMES,
    ERROR_REQUIRED_FIELDS,
    ERROR_TABLE_CELL_REFERENCES,
    run_all_checks,
)

DEFAULT_INPUT = (
    Path(__file__).resolve().parent.parent / "data" / "SchemaToJSON_discomatTrain.csv"
)
DEFAULT_OUTPUT = DEFAULT_INPUT

BASE_COLUMNS = [
    "paper_id",
    "table_id",
    "table_code",
    "sup_text",
    "target_cells",
    "gold_json_records",
]

ENRICHMENT_COLUMNS = [
    "mixed_data",
    "polymorphic",
    "repeated_key",
    "table_cell_ref",
    "required_field",
    "long_text",
    "char_span_ref",
    "has_start_end",
]

ERROR_TYPE_TO_COLUMN = {
    ERROR_MIXED_DATA_TYPES: "mixed_data",
    ERROR_POLYMORPHIC_FIELDS: "polymorphic",
    ERROR_REPEATED_KEY_NAMES: "repeated_key",
    ERROR_TABLE_CELL_REFERENCES: "table_cell_ref",
    ERROR_REQUIRED_FIELDS: "required_field",
    ERROR_LONG_TEXT_FIELDS: "long_text",
}

SPAN_CHARACTERISTIC_KEYS = frozenset({"text_spans", "spans", "char_span"})
START_END_CHARACTERISTIC_KEYS = frozenset({"start", "end", "char_start", "char_end"})


def parse_json_column(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return {}
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str) and value.strip():
        return json.loads(value)
    return {}


def load_csv_rows(path: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    rows: list[dict[str, Any]] = []
    for _, record in df.iterrows():
        row = {column: record.get(column, "") for column in BASE_COLUMNS}
        row["target_cells"] = parse_json_column(row["target_cells"])
        row["gold_json_records"] = parse_json_column(row["gold_json_records"])
        rows.append(row)
    return rows


def walk_keys(obj: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(obj, dict):
        keys.update(obj.keys())
        for value in obj.values():
            keys.update(walk_keys(value))
    elif isinstance(obj, list):
        for item in obj:
            keys.update(walk_keys(item))
    elif isinstance(obj, str) and obj.strip().startswith("{"):
        try:
            keys.update(walk_keys(json.loads(obj)))
        except json.JSONDecodeError:
            pass
    return keys


def check_characteristics(row: dict[str, Any]) -> dict[str, int]:
    keys = walk_keys(row)
    has_char_spans = int(bool(keys & SPAN_CHARACTERISTIC_KEYS))
    has_start_end = int(bool(keys & START_END_CHARACTERISTIC_KEYS))
    return {
        "char_span_ref": has_char_spans,
        "has_start_end": has_start_end,
    }


def aggregate_errors_by_row(findings: list) -> dict[int, dict[str, int]]:
    by_row: dict[int, dict[str, int]] = defaultdict(
        lambda: {column: 0 for column in ENRICHMENT_COLUMNS if column not in ("char_span_ref", "has_start_end")}
    )
    for finding in findings:
        column = ERROR_TYPE_TO_COLUMN.get(finding.error_type)
        if column:
            by_row[finding.row_index][column] = 1
    return by_row


def enrich_csv(input_path: Path, output_path: Path) -> dict[str, Any]:
    df = pd.read_csv(input_path, dtype=str, keep_default_na=False)
    rows = load_csv_rows(input_path)

    findings = run_all_checks(rows)
    errors_by_row = aggregate_errors_by_row(findings)

    for column in ENRICHMENT_COLUMNS:
        df[column] = 0

    char_span_count = 0
    start_end_count = 0
    error_row_counts = {column: 0 for column in ENRICHMENT_COLUMNS if column not in ("char_span_ref", "has_start_end")}

    for row_index in range(len(rows)):
        characteristics = check_characteristics(rows[row_index])
        df.at[row_index, "char_span_ref"] = characteristics["char_span_ref"]
        df.at[row_index, "has_start_end"] = characteristics["has_start_end"]
        char_span_count += characteristics["char_span_ref"]
        start_end_count += characteristics["has_start_end"]

        row_errors = errors_by_row.get(row_index, {})
        for column, value in row_errors.items():
            df.at[row_index, column] = value
            if value:
                error_row_counts[column] += 1

    output_columns = list(df.columns)
    for column in ENRICHMENT_COLUMNS:
        if column not in output_columns:
            output_columns.append(column)

    df = df[output_columns]
    df.to_csv(output_path, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)

    return {
        "rows": len(df),
        "char_span_ref_rows": char_span_count,
        "has_start_end_rows": start_end_count,
        "error_rows_by_type": error_row_counts,
        "total_findings": len(findings),
        "findings_by_type": {
            error_type: sum(1 for finding in findings if finding.error_type == error_type)
            for error_type in ALL_ERROR_TYPES
        },
        "output_path": str(output_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enrich SchemaToJSON discomat CSV with error and characteristic columns."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input CSV (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV (default: overwrite {DEFAULT_INPUT})",
    )
    args = parser.parse_args()

    summary = enrich_csv(args.input, args.output)

    print(f"Wrote {summary['rows']} rows to {summary['output_path']}")
    print("\nCharacteristic presence (rows with flag=1):")
    print(f"  char_span_ref:  {summary['char_span_ref_rows']}")
    print(f"  has_start_end:  {summary['has_start_end_rows']}")
    print("\nError rows by type (rows with flag=1):")
    for column, count in summary["error_rows_by_type"].items():
        print(f"  {column}: {count}")
    print("\nTotal findings by type (cell-level):")
    for error_type, count in summary["findings_by_type"].items():
        column = ERROR_TYPE_TO_COLUMN.get(error_type, error_type)
        print(f"  {column}: {count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
