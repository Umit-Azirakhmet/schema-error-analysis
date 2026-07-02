#!/usr/bin/env python3
"""Count duplicate JSON records in SchemaToJSON gold responses.

Reads data/SchemaToJSON_characteristics_final.csv, parses gold_json_records.cell_record,
counts the maximum frequency among duplicated records, and writes duplicate_record_count
back in place.

Run after organize_datasets.py (re-running organize drops this column).

Usage:
  python scripts/analyze_duplicate_records.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from organize_datasets import DEFAULT_PATHS, try_parse_json  # noqa: E402

DUPLICATE_COLUMN = "duplicate_record_count"
DATASET_KEY = "schematojson"
GOLD_COLUMN = "gold_json_records"


def canonical_record(item: Any) -> str:
    if isinstance(item, dict):
        return json.dumps(item, sort_keys=True, separators=(",", ":"))
    if isinstance(item, str):
        return item
    return json.dumps(item, sort_keys=True, separators=(",", ":"))


def count_duplicate_records(records: list[Any]) -> int:
    """Return max occurrence count among records that appear more than once."""
    if not records:
        return 0
    counts = Counter(canonical_record(record) for record in records)
    dup_freqs = [n for n in counts.values() if n > 1]
    return max(dup_freqs) if dup_freqs else 0


def _parse_cell_record(raw: Any) -> Any:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return raw
    parsed = try_parse_json(raw)
    if isinstance(parsed, dict):
        return parsed
    return raw


def extract_cell_records(gold: Any) -> list[Any]:
    if not isinstance(gold, dict):
        return []
    cell_record = gold.get("cell_record")
    if not isinstance(cell_record, list):
        return []
    return [_parse_cell_record(raw) for raw in cell_record]


def count_row_duplicates(gold_raw: Any) -> int:
    gold = try_parse_json(gold_raw)
    if gold is None:
        return 0
    return count_duplicate_records(extract_cell_records(gold))


def enrich_csv(input_path: Path, output_path: Path) -> dict[str, int]:
    df = pd.read_csv(input_path)

    if GOLD_COLUMN not in df.columns:
        raise ValueError(f"{input_path}: missing gold column {GOLD_COLUMN!r}")

    counts = [count_row_duplicates(row.get(GOLD_COLUMN)) for _, row in df.iterrows()]
    df[DUPLICATE_COLUMN] = counts

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    dup_series = pd.Series(counts, dtype=int)
    return {
        "rows_processed": len(df),
        "rows_with_dupes": int((dup_series > 0).sum()),
        "max_count": int(dup_series.max()) if len(dup_series) else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Count duplicate gold JSON records in SchemaToJSON cell_record "
            "and append duplicate_record_count column."
        )
    )
    parser.parse_args()

    input_path = DEFAULT_PATHS[DATASET_KEY]["output"]
    if not input_path.exists():
        print(f"ERROR: file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        stats = enrich_csv(input_path, input_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        f"[SchemaToJSON] {stats['rows_processed']} rows processed, "
        f"{stats['rows_with_dupes']} rows with duplicates, "
        f"max count {stats['max_count']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
