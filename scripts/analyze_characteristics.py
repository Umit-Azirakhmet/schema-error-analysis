#!/usr/bin/env python3
"""Identify active characteristic columns per dataset CSV.

Loads data/ARQA.csv, data/DeepJSONEval.csv, and data/SchemaToJson.csv,
marks characteristic columns as active when they have more than one distinct
value (not constant across all rows), and writes data/active_characteristics.json.

Usage:
  python scripts/analyze_characteristics.py
  python scripts/analyze_characteristics.py --manifest path/to/output.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "data" / "active_characteristics.json"

DATASETS: dict[str, dict[str, Any]] = {
    "ARQA": {
        "path": ROOT / "data" / "ARQA.csv",
        "base_columns": [
            "year",
            "pack_table_id",
            "paragraph_ids",
            "qa_id",
            "q_type",
            "question",
            "answer_text",
            "value",
            "value_canonical",
            "unit",
            "answer_value",
            "arith_type",
            "gold_answer",
            "program",
            "evidence",
            "table_id",
            "verified",
        ],
    },
    "DeepJSONEval": {
        "path": ROOT / "data" / "DeepJSONEval.csv",
        "base_columns": ["schema", "text", "json", "category"],
    },
    "SchemaToJSON": {
        "path": ROOT / "data" / "SchemaToJson.csv",
        "base_columns": [
            "paper_id",
            "table_id",
            "table_code",
            "sup_text",
            "target_cells",
            "gold_json_records",
        ],
    },
}


def _json_serializable(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, (int, float, str, bool)):
        return value
    return str(value)


def characteristic_columns(df: pd.DataFrame, base_columns: list[str]) -> list[str]:
    missing = [column for column in base_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing expected base columns: {missing}")
    return [column for column in df.columns if column not in base_columns]


def analyze_dataset(label: str, path: Path, base_columns: list[str]) -> dict[str, Any]:
    df = pd.read_csv(path)
    char_columns = characteristic_columns(df, base_columns)

    active_columns: list[str] = []
    removed_constant_columns: dict[str, Any] = {}

    for column in char_columns:
        if df[column].nunique(dropna=False) <= 1:
            removed_constant_columns[column] = (
                _json_serializable(df[column].iloc[0]) if len(df) else None
            )
        else:
            active_columns.append(column)

    print(
        f"[{label}] {len(df)} rows, "
        f"{len(active_columns)} active / {len(removed_constant_columns)} constant columns"
    )
    if removed_constant_columns:
        for column, value in removed_constant_columns.items():
            print(f"  - constant: {column} = {value!r}")

    return {
        "active_columns": active_columns,
        "removed_constant_columns": removed_constant_columns,
    }


def build_manifest(datasets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    manifest: dict[str, Any] = {}
    for label, config in datasets.items():
        path = config["path"]
        if not path.exists():
            raise FileNotFoundError(f"{label}: file not found: {path}")
        manifest[label] = analyze_dataset(label, path, config["base_columns"])
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build active characteristic manifest from enriched dataset CSVs."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=MANIFEST_PATH,
        help=f"Output JSON path (default: {MANIFEST_PATH})",
    )
    args = parser.parse_args()

    try:
        manifest = build_manifest(DATASETS)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote manifest: {args.manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
