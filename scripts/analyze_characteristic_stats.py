#!/usr/bin/env python3
"""Summarize distributions of active characteristic columns per dataset.

Reads enriched CSVs + data/active_characteristics.json and writes a concise
markdown report to reports/characteristic_distributions.md.

Usage:
  python scripts/analyze_characteristic_stats.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_characteristics import DATASETS, characteristic_columns  # noqa: E402

MANIFEST_PATH = ROOT / "data" / "active_characteristics.json"
REPORT_PATH = ROOT / "reports" / "characteristic_distributions.md"


def load_active_columns(manifest_path: Path) -> dict[str, list[str]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {label: entry["active_columns"] for label, entry in manifest.items()}


def _is_flag(series: pd.Series) -> bool:
    values = pd.to_numeric(series, errors="coerce").dropna().unique()
    return len(values) > 0 and set(values).issubset({0, 1})


def summarize_column(series: pd.Series, n_rows: int) -> dict[str, Any]:
    if _is_flag(series):
        ones = int((pd.to_numeric(series, errors="coerce") == 1).sum())
        return {
            "kind": "flag",
            "summary": f"{ones}/{n_rows} ({ones / n_rows * 100:.1f}%) = 1",
        }

    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().all():
        non_zero = int((numeric != 0).sum())
        return {
            "kind": "numeric",
            "summary": (
                f"min={int(numeric.min())}, p25={numeric.quantile(0.25):.1f}, "
                f"med={numeric.median():.1f}, mean={numeric.mean():.1f}, "
                f"p75={numeric.quantile(0.75):.1f}, max={int(numeric.max())}, "
                f"nonzero={non_zero}/{n_rows} ({non_zero / n_rows * 100:.1f}%)"
            ),
        }

    counts = series.fillna("").astype(str).value_counts().head(5)
    parts = [f"{value} ({count}, {count / n_rows * 100:.1f}%)" for value, count in counts.items()]
    return {"kind": "categorical", "summary": "; ".join(parts)}


def analyze_dataset(label: str, path: Path, base_columns: list[str], active: list[str]) -> dict[str, Any]:
    df = pd.read_csv(path)
    n_rows = len(df)
    stats: dict[str, dict[str, Any]] = {}

    for column in active:
        if column not in df.columns:
            raise ValueError(f"{label}: missing active column {column!r}")
        stats[column] = summarize_column(df[column], n_rows)

    return {"rows": n_rows, "columns": stats}


def build_report(results: dict[str, dict[str, Any]]) -> str:
    lines = [
        "# Characteristic Distributions",
        "",
        "Active columns only (from `data/active_characteristics.json`).",
        "",
    ]

    for label, result in results.items():
        lines.extend([f"## {label} ({result['rows']} rows)", ""])
        lines.extend(["| Column | Distribution |", "|--------|--------------|"])
        for column, info in result["columns"].items():
            lines.append(f"| `{column}` | {info['summary']} |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Write concise characteristic distribution report.")
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args()

    if not args.manifest.exists():
        print(f"ERROR: manifest not found: {args.manifest}", file=sys.stderr)
        return 1

    active_by_dataset = load_active_columns(args.manifest)
    results: dict[str, dict[str, Any]] = {}

    for label, config in DATASETS.items():
        path = config["path"]
        if not path.exists():
            print(f"ERROR: file not found: {path}", file=sys.stderr)
            return 1
        active = active_by_dataset.get(label, [])
        if not active:
            char_cols = characteristic_columns(pd.read_csv(path, nrows=0), config["base_columns"])
            active = char_cols
        results[label] = analyze_dataset(label, path, config["base_columns"], active)
        print(f"[{label}] summarized {len(active)} columns")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(build_report(results), encoding="utf-8")
    print(f"Wrote report: {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
