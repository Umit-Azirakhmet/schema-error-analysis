"""Evaluate DiSCoMat parquet gold labels for schema and data-quality errors.

Dependencies: pip install pandas pyarrow
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

DEFAULT_INPUT = (
    Path(__file__).resolve().parent
    / "data"
    / "train-00000-of-00001-da665c816af059b3.parquet"
)

ERROR_MIXED_DATA_TYPES = "mixed_data_types"
ERROR_POLYMORPHIC_FIELDS = "polymorphic_fields"
ERROR_REPEATED_KEY_NAMES = "repeated_key_names"
ERROR_TABLE_CELL_REFERENCES = "table_cell_references"
ERROR_REQUIRED_FIELDS = "required_fields"
ERROR_LONG_TEXT_FIELDS = "long_text_fields"

ALL_ERROR_TYPES = (
    ERROR_MIXED_DATA_TYPES,
    ERROR_POLYMORPHIC_FIELDS,
    ERROR_REPEATED_KEY_NAMES,
    ERROR_TABLE_CELL_REFERENCES,
    ERROR_REQUIRED_FIELDS,
    ERROR_LONG_TEXT_FIELDS,
)

ROW_REQUIRED_FIELDS = ("paper_id", "table_id")
CELL_BASE_REQUIRED_FIELDS = ("value", "type")

RECORD_SCHEMAS: dict[str, dict[str, set[str]]] = {
    "Other": {
        "required": {"value", "type"},
        "allowed": {"value", "type"},
    },
    "Glass_Compound_Amount": {
        "required": {"value", "type", "constituent", "unit", "material"},
        "allowed": {"value", "type", "constituent", "unit", "material"},
    },
}

SEPARATOR_RE = re.compile(r"^\|?[\s\-:|]+\|?$")


@dataclass
class Finding:
    row_index: int
    cell_index: int | None
    error_type: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


def to_jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return [to_jsonable(item) for item in value.tolist()]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def load_parquet(path: Path) -> list[dict[str, Any]]:
    df = pd.read_parquet(path)
    return [
        {column: to_jsonable(row[column]) for column in df.columns}
        for _, row in df.iterrows()
    ]


def parse_pipe_table(table_code: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in table_code.strip().split("\n"):
        stripped = line.strip()
        if not stripped or SEPARATOR_RE.match(stripped):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        rows.append(cells)
    return rows


def get_cell_at(table: list[list[str]], i: int, j: int, k: int) -> str | None:
    if i < 0 or i >= len(table):
        return None
    row = table[i]
    if j < 0 or j >= len(row):
        return None
    cell = row[j]
    if ":" in cell:
        parts = [part.strip() for part in cell.split(":")]
        if k < 0 or k >= len(parts):
            return None
        return parts[k]
    if k == 0:
        return cell
    return None


def parse_cell_record(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    duplicate_keys: list[str] = []

    def object_pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        seen: set[str] = set()
        for key, _ in pairs:
            if key in seen:
                duplicate_keys.append(key)
            seen.add(key)
        return dict(pairs)

    try:
        parsed = json.loads(raw, object_pairs_hook=object_pairs_hook)
    except json.JSONDecodeError as exc:
        return None, str(exc)

    if not isinstance(parsed, dict):
        return None, f"expected JSON object, got {type(parsed).__name__}"

    if duplicate_keys:
        return parsed, f"duplicate keys: {sorted(set(duplicate_keys))}"

    return parsed, None


def collect_key_paths(obj: Any, prefix: str = "") -> dict[str, list[str]]:
    paths: dict[str, list[str]] = defaultdict(list)

    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else key
            paths[key].append(path)
            for child_key, child_paths in collect_key_paths(value, path).items():
                paths[child_key].extend(child_paths)
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            child_prefix = f"{prefix}[{index}]"
            for child_key, child_paths in collect_key_paths(item, child_prefix).items():
                paths[child_key].extend(child_paths)

    return paths


def is_numeric_value(value: Any) -> bool:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return True
    if not isinstance(value, str):
        return False
    candidate = value.strip().replace("+-", "").split()[0] if value.strip() else ""
    if not candidate:
        return False
    try:
        float(candidate)
        return True
    except ValueError:
        return False


def get_gold_records(row: dict[str, Any]) -> tuple[list[list[int]], list[str]]:
    gold = row.get("gold_json_records") or {}
    cell_index = gold.get("cell_index") or []
    cell_record = gold.get("cell_record") or []
    return cell_index, cell_record


def get_target_cells(row: dict[str, Any]) -> dict[str, list[Any]]:
    target = row.get("target_cells") or {}
    return {
        "i": target.get("i") or [],
        "j": target.get("j") or [],
        "k": target.get("k") or [],
        "cell_value_processed": target.get("cell_value_processed") or [],
    }


def check_mixed_data_types(row: dict[str, Any], row_index: int) -> list[Finding]:
    findings: list[Finding] = []
    _, cell_records = get_gold_records(row)

    for cell_index, raw in enumerate(cell_records):
        parsed, parse_error = parse_cell_record(raw)
        if parsed is None:
            findings.append(
                Finding(
                    row_index=row_index,
                    cell_index=cell_index,
                    error_type=ERROR_MIXED_DATA_TYPES,
                    message="cell_record is not valid JSON",
                    details={"parse_error": parse_error},
                )
            )
            continue

        value = parsed.get("value")
        if isinstance(value, bool):
            findings.append(
                Finding(
                    row_index=row_index,
                    cell_index=cell_index,
                    error_type=ERROR_MIXED_DATA_TYPES,
                    message="value is a JSON boolean",
                    details={"value": value, "record_type": parsed.get("type")},
                )
            )
        elif isinstance(value, (int, float)):
            findings.append(
                Finding(
                    row_index=row_index,
                    cell_index=cell_index,
                    error_type=ERROR_MIXED_DATA_TYPES,
                    message="value is stored as a JSON number instead of a string",
                    details={"value": value, "record_type": parsed.get("type")},
                )
            )
        elif parsed.get("type") == "Glass_Compound_Amount" and not is_numeric_value(value):
            findings.append(
                Finding(
                    row_index=row_index,
                    cell_index=cell_index,
                    error_type=ERROR_MIXED_DATA_TYPES,
                    message="Glass_Compound_Amount value is not numeric",
                    details={"value": value},
                )
            )

    return findings


def check_polymorphic_fields(row: dict[str, Any], row_index: int) -> list[Finding]:
    findings: list[Finding] = []
    _, cell_records = get_gold_records(row)

    for cell_index, raw in enumerate(cell_records):
        parsed, parse_error = parse_cell_record(raw)
        if parsed is None:
            findings.append(
                Finding(
                    row_index=row_index,
                    cell_index=cell_index,
                    error_type=ERROR_POLYMORPHIC_FIELDS,
                    message="cell_record is not valid JSON",
                    details={"parse_error": parse_error},
                )
            )
            continue

        record_type = parsed.get("type")
        if record_type not in RECORD_SCHEMAS:
            findings.append(
                Finding(
                    row_index=row_index,
                    cell_index=cell_index,
                    error_type=ERROR_POLYMORPHIC_FIELDS,
                    message="unknown record type",
                    details={"type": record_type, "keys": sorted(parsed.keys())},
                )
            )
            continue

        schema = RECORD_SCHEMAS[record_type]
        keys = set(parsed.keys())
        missing = schema["required"] - keys
        extra = keys - schema["allowed"]

        if missing:
            findings.append(
                Finding(
                    row_index=row_index,
                    cell_index=cell_index,
                    error_type=ERROR_POLYMORPHIC_FIELDS,
                    message=f"{record_type} record is missing expected fields",
                    details={"missing": sorted(missing), "type": record_type},
                )
            )
        if extra:
            findings.append(
                Finding(
                    row_index=row_index,
                    cell_index=cell_index,
                    error_type=ERROR_POLYMORPHIC_FIELDS,
                    message=f"{record_type} record has unexpected fields",
                    details={"extra": sorted(extra), "type": record_type},
                )
            )

    return findings


def check_repeated_key_names(row: dict[str, Any], row_index: int) -> list[Finding]:
    findings: list[Finding] = []
    key_paths = collect_key_paths(row)

    for key, paths in sorted(key_paths.items()):
        if len(paths) > 1:
            findings.append(
                Finding(
                    row_index=row_index,
                    cell_index=None,
                    error_type=ERROR_REPEATED_KEY_NAMES,
                    message=f"key '{key}' appears at multiple paths in the row",
                    details={"key": key, "paths": paths},
                )
            )

    _, cell_records = get_gold_records(row)
    for cell_index, raw in enumerate(cell_records):
        _, parse_error = parse_cell_record(raw)
        if parse_error and parse_error.startswith("duplicate keys"):
            findings.append(
                Finding(
                    row_index=row_index,
                    cell_index=cell_index,
                    error_type=ERROR_REPEATED_KEY_NAMES,
                    message="duplicate keys in cell_record JSON string",
                    details={"issue": parse_error},
                )
            )

    return findings


def check_table_cell_references(
    row: dict[str, Any],
    row_index: int,
    table_grid: list[list[str]],
) -> list[Finding]:
    findings: list[Finding] = []
    cell_indices, cell_records = get_gold_records(row)
    target = get_target_cells(row)

    lengths = {
        "cell_index": len(cell_indices),
        "cell_record": len(cell_records),
        "target_i": len(target["i"]),
        "target_j": len(target["j"]),
        "target_k": len(target["k"]),
        "cell_value_processed": len(target["cell_value_processed"]),
    }
    if len(set(lengths.values())) != 1:
        findings.append(
            Finding(
                row_index=row_index,
                cell_index=None,
                error_type=ERROR_TABLE_CELL_REFERENCES,
                message="parallel cell lists have mismatched lengths",
                details=lengths,
            )
        )
        return findings

    for cell_index in range(lengths["cell_index"]):
        i = target["i"][cell_index]
        j = target["j"][cell_index]
        k = target["k"][cell_index]
        expected_index = [i, j, k]
        actual_index = cell_indices[cell_index]

        if list(actual_index) != expected_index:
            findings.append(
                Finding(
                    row_index=row_index,
                    cell_index=cell_index,
                    error_type=ERROR_TABLE_CELL_REFERENCES,
                    message="cell_index does not match target_cells coordinates",
                    details={
                        "cell_index": actual_index,
                        "target_cells": expected_index,
                    },
                )
            )

        raw_cell = get_cell_at(table_grid, i, j, k)
        if raw_cell is None:
            findings.append(
                Finding(
                    row_index=row_index,
                    cell_index=cell_index,
                    error_type=ERROR_TABLE_CELL_REFERENCES,
                    message="index_out_of_bounds for parsed table_code",
                    details={"i": i, "j": j, "k": k, "table_rows": len(table_grid)},
                )
            )

        processed = str(target["cell_value_processed"][cell_index]).strip()
        parsed, parse_error = parse_cell_record(cell_records[cell_index])
        if parsed is None:
            findings.append(
                Finding(
                    row_index=row_index,
                    cell_index=cell_index,
                    error_type=ERROR_TABLE_CELL_REFERENCES,
                    message="cell_record is not valid JSON",
                    details={"parse_error": parse_error},
                )
            )
            continue

        record_value = str(parsed.get("value", "")).strip()
        if record_value != processed:
            findings.append(
                Finding(
                    row_index=row_index,
                    cell_index=cell_index,
                    error_type=ERROR_TABLE_CELL_REFERENCES,
                    message="cell_record.value does not match cell_value_processed",
                    details={
                        "record_value": record_value,
                        "cell_value_processed": processed,
                    },
                )
            )

        if raw_cell is not None:
            raw_stripped = raw_cell.strip()
            if raw_stripped != processed and processed not in raw_stripped:
                findings.append(
                    Finding(
                        row_index=row_index,
                        cell_index=cell_index,
                        error_type=ERROR_TABLE_CELL_REFERENCES,
                        message="cell_value_processed is not contained in table cell text",
                        details={
                            "table_cell": raw_cell,
                            "cell_value_processed": processed,
                            "i": i,
                            "j": j,
                            "k": k,
                        },
                    )
                )

    return findings


def check_required_fields(row: dict[str, Any], row_index: int) -> list[Finding]:
    findings: list[Finding] = []

    for field_name in ROW_REQUIRED_FIELDS:
        value = row.get(field_name)
        if value is None or str(value).strip() == "":
            findings.append(
                Finding(
                    row_index=row_index,
                    cell_index=None,
                    error_type=ERROR_REQUIRED_FIELDS,
                    message=f"missing required row field '{field_name}'",
                    details={"field": field_name},
                )
            )

    _, cell_records = get_gold_records(row)
    for cell_index, raw in enumerate(cell_records):
        parsed, parse_error = parse_cell_record(raw)
        if parsed is None:
            findings.append(
                Finding(
                    row_index=row_index,
                    cell_index=cell_index,
                    error_type=ERROR_REQUIRED_FIELDS,
                    message="cell_record is not valid JSON",
                    details={"parse_error": parse_error},
                )
            )
            continue

        for field_name in CELL_BASE_REQUIRED_FIELDS:
            if field_name not in parsed or parsed[field_name] in (None, ""):
                findings.append(
                    Finding(
                        row_index=row_index,
                        cell_index=cell_index,
                        error_type=ERROR_REQUIRED_FIELDS,
                        message=f"missing required cell field '{field_name}'",
                        details={"field": field_name, "type": parsed.get("type")},
                    )
                )

        record_type = parsed.get("type")
        schema = RECORD_SCHEMAS.get(record_type)
        if schema:
            for field_name in schema["required"]:
                if field_name not in parsed or parsed[field_name] in (None, ""):
                    findings.append(
                        Finding(
                            row_index=row_index,
                            cell_index=cell_index,
                            error_type=ERROR_REQUIRED_FIELDS,
                            message=f"missing required field '{field_name}' for {record_type}",
                            details={"field": field_name, "type": record_type},
                        )
                    )

    return findings


def check_long_text_fields(
    row: dict[str, Any],
    row_index: int,
    table_grid: list[list[str]],
) -> list[Finding]:
    findings: list[Finding] = []
    table_code = row.get("table_code") or ""
    sup_text = row.get("sup_text") or ""

    if sup_text and str(sup_text).strip():
        if str(sup_text) not in table_code:
            findings.append(
                Finding(
                    row_index=row_index,
                    cell_index=None,
                    error_type=ERROR_LONG_TEXT_FIELDS,
                    message="sup_text is not an exact substring of table_code",
                    details={"sup_text_length": len(str(sup_text))},
                )
            )

    cell_indices, cell_records = get_gold_records(row)
    target = get_target_cells(row)

    for cell_index, raw in enumerate(cell_records):
        parsed, parse_error = parse_cell_record(raw)
        if parsed is None:
            continue

        for text_field in ("constituent", "material"):
            if text_field not in parsed:
                continue
            text_value = str(parsed[text_field])
            if text_value and text_value not in table_code:
                findings.append(
                    Finding(
                        row_index=row_index,
                        cell_index=cell_index,
                        error_type=ERROR_LONG_TEXT_FIELDS,
                        message=f"{text_field} is not an exact substring of table_code",
                        details={text_field: text_value},
                    )
                )

        if cell_index >= len(target["i"]):
            continue

        i = target["i"][cell_index]
        j = target["j"][cell_index]
        k = target["k"][cell_index]
        raw_cell = get_cell_at(table_grid, i, j, k)
        if raw_cell is None:
            continue

        processed = str(target["cell_value_processed"][cell_index]).strip()
        raw_stripped = raw_cell.strip()
        if (
            raw_stripped != processed
            and processed
            and processed in raw_stripped
            and len(processed) < len(raw_stripped)
        ):
            findings.append(
                Finding(
                    row_index=row_index,
                    cell_index=cell_index,
                    error_type=ERROR_LONG_TEXT_FIELDS,
                    message="processed_value_subset_of_raw_cell",
                    details={
                        "raw_cell": raw_cell,
                        "cell_value_processed": processed,
                        "i": i,
                        "j": j,
                        "k": k,
                    },
                )
            )

    return findings


def run_all_checks(rows: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    for row_index, row in enumerate(rows):
        table_grid = parse_pipe_table(row.get("table_code") or "")
        findings.extend(check_mixed_data_types(row, row_index))
        findings.extend(check_polymorphic_fields(row, row_index))
        findings.extend(check_repeated_key_names(row, row_index))
        findings.extend(check_table_cell_references(row, row_index, table_grid))
        findings.extend(check_required_fields(row, row_index))
        findings.extend(check_long_text_fields(row, row_index, table_grid))
    return findings


def build_summary(rows: list[dict[str, Any]], findings: list[Finding]) -> dict[str, Any]:
    cell_count = sum(len(get_gold_records(row)[1]) for row in rows)
    counts_by_type = Counter(finding.error_type for finding in findings)
    return {
        "rows_checked": len(rows),
        "cells_checked": cell_count,
        "total_findings": len(findings),
        "findings_by_type": {error_type: counts_by_type.get(error_type, 0) for error_type in ALL_ERROR_TYPES},
    }


def format_text_report(
    summary: dict[str, Any],
    findings: list[Finding],
    examples_per_type: int = 3,
) -> str:
    lines = [
        "DiSCoMat Dataset Error Report",
        "=============================",
        f"Rows checked:  {summary['rows_checked']}",
        f"Cells checked: {summary['cells_checked']}",
        f"Total findings: {summary['total_findings']}",
        "",
        "Findings by type:",
    ]

    for error_type in ALL_ERROR_TYPES:
        count = summary["findings_by_type"][error_type]
        lines.append(f"  {error_type}: {count}")

    grouped: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        grouped[finding.error_type].append(finding)

    lines.append("")
    lines.append("Examples:")
    for error_type in ALL_ERROR_TYPES:
        type_findings = grouped[error_type]
        if not type_findings:
            continue
        lines.append(f"\n[{error_type}]")
        for finding in type_findings[:examples_per_type]:
            location = f"row={finding.row_index}"
            if finding.cell_index is not None:
                location += f", cell={finding.cell_index}"
            lines.append(f"  - {location}: {finding.message}")
            if finding.details:
                lines.append(f"    details: {finding.details}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate DiSCoMat parquet gold labels for schema and data-quality errors."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input parquet file (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output file for the full report",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Report format (default: text)",
    )
    parser.add_argument(
        "--examples",
        type=int,
        default=3,
        help="Number of example findings per error type in text output (default: 3)",
    )
    args = parser.parse_args()

    rows = load_parquet(args.input)
    findings = run_all_checks(rows)
    summary = build_summary(rows, findings)
    report = {
        "summary": summary,
        "findings": [asdict(finding) for finding in findings],
    }

    if args.format == "json":
        rendered = json.dumps(report, ensure_ascii=False, indent=2)
    else:
        rendered = format_text_report(summary, findings, examples_per_type=args.examples)

    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Wrote report to {args.output}")
    else:
        print(rendered)

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
