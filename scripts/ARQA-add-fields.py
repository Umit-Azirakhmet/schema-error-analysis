#!/usr/bin/env python3
"""Add characteristic columns to ARQA raw CSV.

Reads data/other-versions/ARQA_raw.csv, computes per-row characteristics from
gold_answer (and supporting row fields), and writes data/ARQA.csv.

New columns (appended after all raw columns):
  - char_has_table_cells         — from organize_datasets.py: any claim uses table_cells
  - char_has_text_spans          — from organize_datasets.py: any claim uses text_spans
  - table_cell_total_refs_count  — from organize_datasets.py: table cell refs in the row
  - claim_count                  — number of items in gold_answer.claims
  - max_evidence_items_per_claim — max(table_cells + text_spans) across claims
  - gold_json_length             — character length of the raw gold_answer string
  - nesting_depth                — max object/array nesting depth (root object = 1)
  - total_object_count           — number of JSON objects in the fully unpacked tree
  - max_array_nesting_depth      — deepest stack of nested arrays
  - total_array_count            — number of JSON arrays in the fully unpacked tree
  - max_array_length             — largest array length anywhere in the tree
  - total_key_count              — total key occurrences across all objects
  - unique_key_count             — distinct key names across all objects
  - max_key_length               — longest object key name (characters)
  - long_text_value_count        — leaf strings that look sentence/paragraph-like
  - numeric_value_count          — leaf values that are numbers or numeric strings
  - alphanumeric_value_count     — leaf strings with both letters and digits
  - max_value_length             — longest leaf value when rendered as text
  - average_value_length         — mean leaf value length (0 when no leaf values)
  - value_types                  — comma-separated present leaf types: boolean, number, string

Usage:
  python scripts/ARQA-add-fields.py
  python scripts/ARQA-add-fields.py --input path/to/raw.csv --output path/to/out.csv
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
    characterize_arqa_row,
    count_refs_in_row,
    try_parse_json,
)

DEFAULT_INPUT = ROOT / "data" / "other-versions" / "ARQA_raw.csv"
DEFAULT_OUTPUT = ROOT / "data" / "ARQA.csv"

GOLD_COLUMN = "gold_answer"
NEW_COLUMNS = [
    "char_has_table_cells",
    "char_has_text_spans",
    "table_cell_total_refs_count",
    "claim_count",
    "max_evidence_items_per_claim",
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

STRUCTURE_COLUMNS = NEW_COLUMNS[5:]


def analyze_arqa_claims(gold_raw: object) -> tuple[int, int]:
    """Return (claim_count, max_evidence_items_per_claim) from gold_answer."""
    parsed = try_parse_json(gold_raw)
    if not isinstance(parsed, dict):
        return 0, 0

    claims = parsed.get("claims", [])
    if not isinstance(claims, list):
        return 0, 0

    claim_count = len(claims)
    max_evidence_items = 0

    for claim in claims:
        if not isinstance(claim, dict):
            continue
        evidence = claim.get("evidence", {})
        if not isinstance(evidence, dict):
            continue

        table_cells = evidence.get("table_cells", [])
        text_spans = evidence.get("text_spans", [])
        table_count = len(table_cells) if isinstance(table_cells, list) else 0
        text_count = len(text_spans) if isinstance(text_spans, list) else 0
        max_evidence_items = max(max_evidence_items, table_count + text_count)

    return claim_count, max_evidence_items


def enrich_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if GOLD_COLUMN not in df.columns:
        raise ValueError(f"Missing required column {GOLD_COLUMN!r}")

    added_columns: dict[str, list[Any]] = {column: [] for column in NEW_COLUMNS}

    for _, row in df.iterrows():
        gold_raw = row[GOLD_COLUMN]

        arqa_flags = characterize_arqa_row(gold_raw)
        added_columns["char_has_table_cells"].append(arqa_flags["char_has_table_cells"])
        added_columns["char_has_text_spans"].append(arqa_flags["char_has_text_spans"])

        ref_counts = count_refs_in_row(row)
        added_columns["table_cell_total_refs_count"].append(
            ref_counts["table_cell_total_refs_count"]
        )

        claim_count, max_evidence_items = analyze_arqa_claims(gold_raw)
        added_columns["claim_count"].append(claim_count)
        added_columns["max_evidence_items_per_claim"].append(max_evidence_items)

        structure = analyze_gold_json_structure(gold_raw)
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
        description="Add gold_answer characteristic columns to ARQA raw CSV."
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
