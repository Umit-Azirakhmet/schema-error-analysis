#!/usr/bin/env python3
"""Analyze per-dataset characteristic columns: filter constants, compute stats, write report.

Loads *_characteristics_final.csv files, drops columns constant within each dataset,
computes summary statistics for active columns, and writes:
  - data/active_characteristics.json
  - reports/characteristic_statistics_report.md

Usage:
  python scripts/analyze_characteristics.py
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from organize_datasets import (  # noqa: E402
    COUNT_CHAR_COLUMNS,
    DEFAULT_PATHS,
    FLAG_CHAR_COLUMNS,
    STRING_CHAR_COLUMNS,
    UNIFIED_CHAR_COLUMNS,
)

REPORTS_DIR = ROOT / "reports"
MANIFEST_PATH = ROOT / "data" / "active_characteristics.json"
REPORT_PATH = REPORTS_DIR / "characteristic_statistics_report.md"

DATASET_LABELS = {
    "arqa": "ARQA",
    "deepjsoneval": "DeepJSONEval",
    "schematojson": "SchemaToJSON",
}


def load_characteristics(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [col for col in UNIFIED_CHAR_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"{path}: missing characteristic columns: {missing}")
    return df[UNIFIED_CHAR_COLUMNS]


def identify_constant_columns(df: pd.DataFrame) -> tuple[list[str], list[str], dict[str, Any]]:
    """Return (active, constant, constant_values)."""
    active: list[str] = []
    constant: list[str] = []
    constant_values: dict[str, Any] = {}

    for column in UNIFIED_CHAR_COLUMNS:
        nunique = df[column].nunique(dropna=False)
        if nunique <= 1:
            constant.append(column)
            constant_values[column] = df[column].iloc[0] if len(df) else None
        else:
            active.append(column)

    return active, constant, constant_values


def apply_active_column_safeguard(
    df: pd.DataFrame,
    active: list[str],
    constant: list[str],
    constant_values: dict[str, Any],
    dataset_label: str,
) -> tuple[list[str], list[str], dict[str, Any], str | None]:
    """Ensure at least one active column; fallback to highest-variance column."""
    note: str | None = None

    if active:
        return active, constant, constant_values, note

    warnings.warn(
        f"{dataset_label}: all {len(UNIFIED_CHAR_COLUMNS)} characteristic columns are constant; "
        "keeping highest-variance column as fallback.",
        stacklevel=2,
    )

    numeric = df[UNIFIED_CHAR_COLUMNS].apply(pd.to_numeric, errors="coerce")
    variances = numeric.var(numeric_only=True)
    if variances.isna().all():
        fallback = UNIFIED_CHAR_COLUMNS[0]
    else:
        fallback = str(variances.idxmax())

    active = [fallback]
    constant = [c for c in constant if c != fallback]
    constant_values = {k: v for k, v in constant_values.items() if k != fallback}
    note = (
        f"Fallback applied: all columns were constant; kept `{fallback}` "
        f"(highest variance among unified columns)."
    )
    return active, constant, constant_values, note


def compute_flag_stats(series: pd.Series, n_rows: int) -> dict[str, Any]:
    ones = int((series == 1).sum())
    pct = (ones / n_rows * 100) if n_rows else 0.0
    return {"count_eq_1": ones, "pct_eq_1": round(pct, 2)}


def compute_count_stats(series: pd.Series, n_rows: int) -> dict[str, Any]:
    numeric = pd.to_numeric(series, errors="coerce").fillna(0)
    non_zero = int((numeric != 0).sum())
    pct_non_zero = (non_zero / n_rows * 100) if n_rows else 0.0
    return {
        "count_non_zero": non_zero,
        "pct_non_zero": round(pct_non_zero, 2),
        "mean": round(float(numeric.mean()), 4),
        "min": int(numeric.min()),
        "max": int(numeric.max()),
    }


def compute_string_stats(series: pd.Series, n_rows: int) -> dict[str, Any]:
    counts = series.fillna("").astype(str).value_counts()
    frequencies = [
        {"value": str(value), "count": int(count), "pct": round(count / n_rows * 100, 2)}
        for value, count in counts.items()
    ]
    return {"frequencies": frequencies}


def compute_column_stats(df: pd.DataFrame, column: str) -> dict[str, Any]:
    n_rows = len(df)
    series = df[column]

    if column in STRING_CHAR_COLUMNS:
        stats = compute_string_stats(series, n_rows)
        col_type = "string"
    elif column in COUNT_CHAR_COLUMNS:
        stats = compute_count_stats(series, n_rows)
        col_type = "count"
    else:
        stats = compute_flag_stats(series, n_rows)
        col_type = "flag"

    return {"type": col_type, **stats}


def analyze_dataset(dataset_key: str, path: Path) -> dict[str, Any]:
    label = DATASET_LABELS[dataset_key]
    df = load_characteristics(path)
    n_rows = len(df)

    active, constant, constant_values = identify_constant_columns(df)
    active, constant, constant_values, safeguard_note = apply_active_column_safeguard(
        df, active, constant, constant_values, label
    )

    if constant:
        print(f"[{label}] Removed {len(constant)} constant column(s):")
        for col in constant:
            print(f"  - {col} = {constant_values[col]!r}")
    print(f"[{label}] {n_rows} rows, {len(active)} active / {len(constant)} removed columns")

    column_stats = {col: compute_column_stats(df, col) for col in active}

    return {
        "label": label,
        "dataset_key": dataset_key,
        "path": str(path),
        "n_rows": n_rows,
        "active_columns": active,
        "removed_constant_columns": constant_values,
        "safeguard_note": safeguard_note,
        "column_stats": column_stats,
    }


def build_manifest(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    manifest: dict[str, Any] = {}
    for dataset_key, result in results.items():
        label = result["label"]
        manifest[label] = {
            "active_columns": result["active_columns"],
            "removed_constant_columns": {
                k: _json_serializable(v) for k, v in result["removed_constant_columns"].items()
            },
        }
        if result["safeguard_note"]:
            manifest[label]["safeguard_note"] = result["safeguard_note"]
    return manifest


def _json_serializable(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, (int, float, str, bool)):
        return value
    return str(value)


def _format_flag_table(stats: dict[str, dict[str, Any]]) -> list[str]:
    lines = ["| Column | Count (=1) | % (=1) |", "|--------|------------|--------|"]
    for col, s in stats.items():
        if s["type"] != "flag":
            continue
        lines.append(f"| `{col}` | {s['count_eq_1']} | {s['pct_eq_1']}% |")
    return lines


def _format_count_table(stats: dict[str, dict[str, Any]]) -> list[str]:
    lines = [
        "| Column | Count (≠0) | % (≠0) | Mean | Min | Max |",
        "|--------|------------|--------|------|-----|-----|",
    ]
    for col, s in stats.items():
        if s["type"] != "count":
            continue
        lines.append(
            f"| `{col}` | {s['count_non_zero']} | {s['pct_non_zero']}% | "
            f"{s['mean']} | {s['min']} | {s['max']} |"
        )
    return lines


def _format_string_tables(stats: dict[str, dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for col, s in stats.items():
        if s["type"] != "string":
            continue
        lines.append(f"#### `{col}`")
        lines.append("")
        lines.append("| Value | Count | % |")
        lines.append("|-------|-------|---|")
        for row in s["frequencies"]:
            lines.append(f"| {row['value']} | {row['count']} | {row['pct']}% |")
        lines.append("")
    return lines


def build_report(results: dict[str, dict[str, Any]]) -> str:
    lines: list[str] = [
        "# Characteristic Statistics Report",
        "",
        "Generated by `scripts/analyze_characteristics.py`. "
        "Statistics cover **variable** unified characteristic columns only "
        "(constant columns removed per dataset).",
        "",
        "## Executive Summary",
        "",
        "| Dataset | Rows | Active Columns | Removed (Constant) |",
        "|---------|------|----------------|---------------------|",
    ]

    for result in results.values():
        n_removed = len(result["removed_constant_columns"])
        lines.append(
            f"| {result['label']} | {result['n_rows']} | {len(result['active_columns'])} | {n_removed} |"
        )

    lines.extend(["", "## Per-Dataset Statistics", ""])

    for result in results.values():
        label = result["label"]
        lines.append(f"### {label}")
        lines.append("")
        lines.append(f"- **Source:** `{result['path']}`")
        lines.append(f"- **Rows:** {result['n_rows']}")
        lines.append(f"- **Active columns:** {len(result['active_columns'])}")
        if result["safeguard_note"]:
            lines.append(f"- **Note:** {result['safeguard_note']}")
        lines.append("")

        if result["removed_constant_columns"]:
            lines.append("#### Removed Constant Columns")
            lines.append("")
            lines.append("| Column | Constant Value |")
            lines.append("|--------|----------------|")
            for col, val in result["removed_constant_columns"].items():
                lines.append(f"| `{col}` | `{_json_serializable(val)}` |")
            lines.append("")

        stats = result["column_stats"]
        flag_stats = {k: v for k, v in stats.items() if v["type"] == "flag"}
        count_stats = {k: v for k, v in stats.items() if v["type"] == "count"}
        string_stats = {k: v for k, v in stats.items() if v["type"] == "string"}

        if flag_stats:
            lines.append("#### Boolean Flags")
            lines.append("")
            lines.extend(_format_flag_table(flag_stats))
            lines.append("")

        if count_stats:
            lines.append("#### Count Columns")
            lines.append("")
            lines.extend(_format_count_table(count_stats))
            lines.append("")

        if string_stats:
            lines.append("#### String Columns")
            lines.append("")
            lines.extend(_format_string_tables(string_stats))

    lines.extend(
        [
            "## Cross-Dataset Notes",
            "",
            "- **ARQA:** Active columns reflect evidence structure (paragraph/table refs, text spans, "
            "table-cell reference counts). DeepJSONEval schema-keyword columns are constant (all zero).",
            "- **DeepJSONEval:** Active columns capture JSON Schema shape (primitive types, arrays, "
            "nesting depth, enums, property count). ARQA- and SchemaToJSON-specific flags are constant.",
            "- **SchemaToJSON:** Only two unified columns vary (`table_cell_ref`, "
            "`long_text`). Most JSON-Schema-style features are zero because "
            "gold outputs use record-type schemas in `gold_json_records`, not JSON Schema objects.",
            "",
            "### SchemaToJSON Sparsity Caveat",
            "",
            "With only ~2 varying unified characteristics, SchemaToJSON error-correlation analysis "
            "against the full unified column set is limited. Future enrichment (e.g., record-type "
            "distribution, cell-count features) is recommended but out of scope for this report.",
            "",
            "## Next Steps",
            "",
            "- Use `data/active_characteristics.json` when correlating errors with characteristics.",
            "- See `prompts/example_prompts.md` for generation prompt templates (FRI and NL-to-Format).",
            "- Implement `scripts/generation/nl_to_format.py` for two-stage generation experiments.",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze characteristic columns per dataset and write manifest + report."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=MANIFEST_PATH,
        help=f"Output JSON manifest path (default: {MANIFEST_PATH})",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=REPORT_PATH,
        help=f"Output markdown report path (default: {REPORT_PATH})",
    )
    args = parser.parse_args()

    results: dict[str, dict[str, Any]] = {}
    exit_code = 0

    for dataset_key, paths in DEFAULT_PATHS.items():
        output_path = paths["output"]
        if not output_path.exists():
            print(f"[{DATASET_LABELS[dataset_key]}] ERROR: file not found: {output_path}", file=sys.stderr)
            exit_code = 1
            continue
        results[dataset_key] = analyze_dataset(dataset_key, output_path)

    if not results:
        return exit_code

    manifest = build_manifest(results)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote manifest: {args.manifest}")

    report = build_report(results)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(f"Wrote report: {args.report}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
