#!/usr/bin/env python3
"""Universal dataset organizer: append all characteristic columns to each CSV.

Merges every *organization*.py script into one pipeline. Each output CSV
contains the same unified characteristic columns; values are computed from
whatever JSON/fields exist in that row (0 or empty when not applicable).

Sources:
  - ARQA-organization.py
  - ARQA-organization2.py
  - DeepJSONEval-organization-TF.py + DeepJSONEval-organization.py
  - SchemaToJSON-organization.py + SchemaToJSON-organization2.py

Duplicate policy: table-cell reference counts are kept instead of the
boolean char_has_table_ref flag from ARQA-organization.py.

Usage:
  python scripts/organize_datasets.py --dataset all
  python scripts/organize_datasets.py --dataset arqa
  python scripts/organize_datasets.py --dataset deepjsoneval --input data/raw.csv
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

# ---------------------------------------------------------------------------
# Dataset field definitions
# ---------------------------------------------------------------------------

ARQA_BASE_COLUMNS = [
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
]

DEEPJSONEVAL_BASE_COLUMNS = ["schema", "text", "json", "category"]

SCHEMATOJSON_BASE_COLUMNS = [
    "paper_id",
    "table_id",
    "table_code",
    "sup_text",
    "target_cells",
    "gold_json_records",
]

# All characteristic columns from every *organization*.py script (deduplicated).
# char_has_table_ref is omitted — table_cell_*_count columns cover that signal.
UNIFIED_CHAR_COLUMNS = [
    # ARQA-organization.py (boolean flags; table ref bool dropped)
    "char_has_para_ref",
    "char_has_table_cells",
    "char_has_text_spans",
    "char_has_actual_null",
    "char_has_string_null",
    "char_is_valid_json",
    # ARQA-organization2.py (counts preferred over booleans)
    "table_cell_row_only_count",
    "table_cell_column_only_count",
    "table_cell_column_and_row_count",
    "table_cell_total_refs_count",
    # DeepJSONEval-organization-TF.py + reverse-engineered schema features
    "primitive_types",
    "has_object",
    "has_array",
    "array_of_objects",
    "array_of_primitives",
    "detected_nesting_depth",
    "has_enum",
    "has_anyOf",
    "has_oneOf",
    "has_allOf",
    "has_ref",
    "has_default",
    "has_description",
    "has_pattern",
    "has_required",
    "has_format",
    "has_numeric_constraints",
    "has_length_constraints",
    "has_array_constraints",
    "property_count",
    # SchemaToJSON-organization.py (+ organization2.py checks)
    "mixed_data",
    "polymorphic",
    "repeated_key",
    "table_cell_ref",
    "required_field",
    "long_text",
    "char_span_ref",
    "has_start_end",
]

COUNT_CHAR_COLUMNS = {
    "table_cell_row_only_count",
    "table_cell_column_only_count",
    "table_cell_column_and_row_count",
    "table_cell_total_refs_count",
    "detected_nesting_depth",
    "property_count",
}

STRING_CHAR_COLUMNS = {"primitive_types"}

FLAG_CHAR_COLUMNS = [
    column
    for column in UNIFIED_CHAR_COLUMNS
    if column not in COUNT_CHAR_COLUMNS and column not in STRING_CHAR_COLUMNS
]

ARQA_JSON_SOURCE_COLUMN = {
    "arqa": "gold_answer",
    "deepjsoneval": "json",
    "schematojson": "gold_json_records",
}

DEFAULT_PATHS = {
    "arqa": {
        "input": DATA_DIR / "ARQA_cleaned.csv",
        "output": DATA_DIR / "ARQA_characteristics_final.csv",
    },
    "deepjsoneval": {
        "input": DATA_DIR / "DeepJSONEval_characteristics-v2.csv",
        "output": DATA_DIR / "DeepJSONEval_characteristics_final.csv",
    },
    "schematojson": {
        "input": DATA_DIR / "SchemaToJSON_characteristics.csv",
        "output": DATA_DIR / "SchemaToJSON_characteristics_final.csv",
    },
}

PRIMITIVE_TYPES = {"string", "integer", "number", "boolean", "null"}


def default_characteristics() -> dict[str, Any]:
    values: dict[str, Any] = {column: "" for column in STRING_CHAR_COLUMNS}
    for column in COUNT_CHAR_COLUMNS:
        values[column] = 0
    for column in FLAG_CHAR_COLUMNS:
        values[column] = 0
    return values


def normalize_characteristics(chars: dict[str, Any]) -> dict[str, Any]:
    normalized = default_characteristics()
    for column in UNIFIED_CHAR_COLUMNS:
        value = chars.get(column, normalized[column])
        if column in STRING_CHAR_COLUMNS:
            normalized[column] = "" if value is None or (isinstance(value, float) and pd.isna(value)) else str(value)
        elif column in COUNT_CHAR_COLUMNS:
            normalized[column] = int(value or 0)
        else:
            normalized[column] = int(bool(value))
    return normalized


# ---------------------------------------------------------------------------
# ARQA (from ARQA-organization.py)
# ---------------------------------------------------------------------------


def check_null_types(obj: Any) -> tuple[bool, bool]:
    """Recursively checks for actual null (None) and string 'null'."""
    has_string_null = False
    has_actual_null = False

    if isinstance(obj, dict):
        for value in obj.values():
            if value == "null":
                has_string_null = True
            elif value is None:
                has_actual_null = True
            if isinstance(value, (dict, list)):
                s_null, a_null = check_null_types(value)
                has_string_null = has_string_null or s_null
                has_actual_null = has_actual_null or a_null
    elif isinstance(obj, list):
        for item in obj:
            if item == "null":
                has_string_null = True
            elif item is None:
                has_actual_null = True
            if isinstance(item, (dict, list)):
                s_null, a_null = check_null_types(item)
                has_string_null = has_string_null or s_null
                has_actual_null = has_actual_null or a_null

    return has_string_null, has_actual_null


def characterize_arqa_row(gold_answer_str: Any) -> dict[str, int]:
    """ARQA-organization.py flags (char_has_table_ref omitted — use counts)."""
    result = {
        "char_has_para_ref": 0,
        "char_has_table_cells": 0,
        "char_has_text_spans": 0,
        "char_has_actual_null": 0,
        "char_has_string_null": 0,
        "char_is_valid_json": 1,
    }

    if pd.isna(gold_answer_str):
        result["char_is_valid_json"] = 0
        return result

    try:
        gold_answer = json.loads(gold_answer_str)
    except (json.JSONDecodeError, TypeError):
        result["char_is_valid_json"] = 0
        return result

    has_string_null, has_actual_null = check_null_types(gold_answer)
    result["char_has_string_null"] = int(has_string_null)
    result["char_has_actual_null"] = int(has_actual_null)

    for claim in gold_answer.get("claims", []):
        evidence = claim.get("evidence", {})
        if "table_cells" in evidence:
            result["char_has_table_cells"] = 1
        if "text_spans" in evidence:
            result["char_has_text_spans"] = 1
            for span in evidence.get("text_spans", []):
                if "para_id" in span:
                    result["char_has_para_ref"] = 1

    return result


# ---------------------------------------------------------------------------
# ARQA-organization2.py — table cell reference counts
# ---------------------------------------------------------------------------


def try_parse_json(value: Any) -> Any:
    if pd.isna(value):
        return None
    if not isinstance(value, str):
        return value
    value = value.strip()
    if value == "":
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return None


def count_refs_in_object(obj: Any) -> dict[str, int]:
    counts = {
        "table_cell_row_only_count": 0,
        "table_cell_column_only_count": 0,
        "table_cell_column_and_row_count": 0,
        "table_cell_total_refs_count": 0,
    }
    seen: set[int] = set()

    def count_cell(cell: Any) -> None:
        if not isinstance(cell, dict):
            return
        cell_id = id(cell)
        if cell_id in seen:
            return
        seen.add(cell_id)

        has_row = "row" in cell and cell["row"] not in (None, "")
        has_col = "col" in cell and cell["col"] not in (None, "")

        if has_row or has_col:
            counts["table_cell_total_refs_count"] += 1
            if has_row and has_col:
                counts["table_cell_column_and_row_count"] += 1
            elif has_row:
                counts["table_cell_row_only_count"] += 1
            elif has_col:
                counts["table_cell_column_only_count"] += 1

    def search(node: Any) -> None:
        if isinstance(node, dict):
            if "table_cells" in node and isinstance(node["table_cells"], list):
                for cell in node["table_cells"]:
                    count_cell(cell)
            if "cell" in node and isinstance(node["cell"], dict):
                count_cell(node["cell"])
            if "table_id" in node and ("row" in node or "col" in node):
                count_cell(node)
            for value in node.values():
                search(value)
        elif isinstance(node, list):
            for item in node:
                search(item)

    search(obj)
    return counts


def count_refs_in_row(row: pd.Series) -> dict[str, int]:
    totals = {
        "table_cell_row_only_count": 0,
        "table_cell_column_only_count": 0,
        "table_cell_column_and_row_count": 0,
        "table_cell_total_refs_count": 0,
    }
    for value in row:
        parsed = try_parse_json(value)
        if parsed is None:
            continue
        counts = count_refs_in_object(parsed)
        for key in totals:
            totals[key] += counts[key]
    return totals


# walk_keys / check_key_characteristics are defined with SchemaToJSON helpers below.


# ---------------------------------------------------------------------------
# DeepJSONEval (organization-TF + organization + extra characteristics)
# ---------------------------------------------------------------------------


def walk_schema(schema: Any):
    if isinstance(schema, dict):
        yield schema
        if "properties" in schema:
            for child in schema["properties"].values():
                yield from walk_schema(child)
        if "items" in schema:
            yield from walk_schema(schema["items"])
        for key in ["anyOf", "oneOf", "allOf"]:
            if key in schema:
                for child in schema[key]:
                    yield from walk_schema(child)


def collect_primitive_types(schema: dict[str, Any]) -> str:
    types: set[str] = set()
    for node in walk_schema(schema):
        node_type = node.get("type")
        if isinstance(node_type, str) and node_type in PRIMITIVE_TYPES:
            types.add(node_type)
        elif isinstance(node_type, list):
            for item in node_type:
                if item in PRIMITIVE_TYPES:
                    types.add(item)
    return ", ".join(sorted(types))


def schema_has_type(schema: dict[str, Any], target: str) -> bool:
    for node in walk_schema(schema):
        node_type = node.get("type")
        if node_type == target or (isinstance(node_type, list) and target in node_type):
            return True
    return False


def schema_has_array(schema: dict[str, Any]) -> bool:
    return any(node.get("type") == "array" for node in walk_schema(schema))


def schema_array_of_objects(schema: dict[str, Any]) -> bool:
    for node in walk_schema(schema):
        if node.get("type") == "array":
            items = node.get("items", {})
            if isinstance(items, dict) and items.get("type") == "object":
                return True
    return False


def schema_array_of_primitives(schema: dict[str, Any]) -> bool:
    for node in walk_schema(schema):
        if node.get("type") == "array":
            items = node.get("items", {})
            if isinstance(items, dict):
                item_type = items.get("type")
                if item_type in PRIMITIVE_TYPES:
                    return True
    return False


def schema_has_keyword(schema: dict[str, Any], keyword: str) -> bool:
    return any(keyword in node for node in walk_schema(schema))


def schema_has_ref(schema: dict[str, Any]) -> bool:
    return any("$ref" in node for node in walk_schema(schema))


def schema_has_numeric_constraints(schema: dict[str, Any]) -> bool:
    keys = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf"}
    return any(keys & node.keys() for node in walk_schema(schema))


def schema_has_length_constraints(schema: dict[str, Any]) -> bool:
    keys = {"minLength", "maxLength", "minItems", "maxItems"}
    return any(keys & node.keys() for node in walk_schema(schema))


def schema_has_array_constraints(schema: dict[str, Any]) -> bool:
    keys = {"uniqueItems", "additionalItems", "contains", "minContains", "maxContains"}
    return any(keys & node.keys() for node in walk_schema(schema))


def schema_property_count(schema: dict[str, Any]) -> int:
    count = 0
    for node in walk_schema(schema):
        if node.get("type") == "object" and "properties" in node:
            count += len(node["properties"])
    return count


def schema_nesting_depth(schema: dict[str, Any]) -> int:
    """Maximum object/array nesting depth (root object = depth 1).

    Note: DeepJSONEval-organization-TF.py used a variant that did not increment
    depth when entering arrays. The stored characteristics files use this
    array-inclusive definition instead.
    """

    def dfs(node: Any, depth: int) -> int:
        max_depth = depth
        if isinstance(node, dict):
            if node.get("type") == "object":
                for child in node.get("properties", {}).values():
                    max_depth = max(max_depth, dfs(child, depth + 1))
            elif node.get("type") == "array":
                items = node.get("items", {})
                max_depth = max(max_depth, dfs(items, depth + 1))
            else:
                if "items" in node:
                    max_depth = max(max_depth, dfs(node["items"], depth))
                if "properties" in node:
                    for child in node["properties"].values():
                        max_depth = max(max_depth, dfs(child, depth + 1))
                for key in ["anyOf", "oneOf", "allOf"]:
                    if key in node:
                        for child in node[key]:
                            max_depth = max(max_depth, dfs(child, depth))
        return max_depth

    start = 1 if schema.get("type") == "object" else 0
    return dfs(schema, start)


def characterize_deepjsoneval_schema(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "primitive_types": collect_primitive_types(schema),
        "has_object": int(schema_has_type(schema, "object")),
        "has_array": int(schema_has_array(schema)),
        "array_of_objects": int(schema_array_of_objects(schema)),
        "array_of_primitives": int(schema_array_of_primitives(schema)),
        "detected_nesting_depth": schema_nesting_depth(schema),
        "has_enum": int(schema_has_keyword(schema, "enum")),
        "has_anyOf": int(schema_has_keyword(schema, "anyOf")),
        "has_oneOf": int(schema_has_keyword(schema, "oneOf")),
        "has_allOf": int(schema_has_keyword(schema, "allOf")),
        "has_ref": int(schema_has_ref(schema)),
        "has_default": int(schema_has_keyword(schema, "default")),
        "has_description": int(schema_has_keyword(schema, "description")),
        "has_pattern": int(schema_has_keyword(schema, "pattern")),
        "has_required": int(schema_has_keyword(schema, "required")),
        "has_format": int(schema_has_keyword(schema, "format")),
        "has_numeric_constraints": int(schema_has_numeric_constraints(schema)),
        "has_length_constraints": int(schema_has_length_constraints(schema)),
        "has_array_constraints": int(schema_has_array_constraints(schema)),
        "property_count": schema_property_count(schema),
    }


def organize_deepjsoneval(input_path: Path, output_path: Path) -> dict[str, Any]:
    return enrich_dataset(input_path, output_path, DEEPJSONEVAL_BASE_COLUMNS, "deepjsoneval")


# ---------------------------------------------------------------------------
# SchemaToJSON (from SchemaToJSON-organization.py + organization2.py)
# ---------------------------------------------------------------------------

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
ROW_REQUIRED_FIELDS = ("paper_id", "table_id")
CELL_BASE_REQUIRED_FIELDS = ("value", "type")

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


@dataclass
class Finding:
    row_index: int
    cell_index: int | None
    error_type: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


def parse_json_column(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return {}
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str) and value.strip():
        return json.loads(value)
    return {}


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

    _, cell_records = get_gold_records(row)
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


def check_key_characteristics(obj: Any) -> dict[str, int]:
    keys = walk_keys(obj)
    return {
        "char_span_ref": int(bool(keys & SPAN_CHARACTERISTIC_KEYS)),
        "has_start_end": int(bool(keys & START_END_CHARACTERISTIC_KEYS)),
    }


def aggregate_errors_by_row(findings: list[Finding]) -> dict[int, dict[str, int]]:
    error_columns = list(ERROR_TYPE_TO_COLUMN.values())
    by_row: dict[int, dict[str, int]] = defaultdict(lambda: {column: 0 for column in error_columns})
    for finding in findings:
        column = ERROR_TYPE_TO_COLUMN.get(finding.error_type)
        if column:
            by_row[finding.row_index][column] = 1
    return by_row


def load_schematojson_row_from_series(record: pd.Series) -> dict[str, Any]:
    row = {column: record.get(column, "") for column in SCHEMATOJSON_BASE_COLUMNS}
    row["target_cells"] = parse_json_column(row["target_cells"])
    row["gold_json_records"] = parse_json_column(row["gold_json_records"])
    return row


def enrich_row_characteristics(
    row: pd.Series,
    dataset: str,
    schematojson_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    chars = default_characteristics()

    chars.update(count_refs_in_row(row))

    json_column = ARQA_JSON_SOURCE_COLUMN.get(dataset)
    if json_column and json_column in row.index:
        chars.update(characterize_arqa_row(row.get(json_column)))

    span_ref = 0
    has_start_end = 0
    for value in row:
        parsed = try_parse_json(value)
        if parsed is None:
            continue
        key_flags = check_key_characteristics(parsed)
        span_ref = max(span_ref, key_flags["char_span_ref"])
        has_start_end = max(has_start_end, key_flags["has_start_end"])
    chars["char_span_ref"] = max(chars["char_span_ref"], span_ref)
    chars["has_start_end"] = max(chars["has_start_end"], has_start_end)

    if "schema" in row.index:
        schema = try_parse_json(row.get("schema"))
        if isinstance(schema, dict):
            chars.update(characterize_deepjsoneval_schema(schema))

    if schematojson_row is not None:
        findings = run_all_checks([schematojson_row])
        row_errors = aggregate_errors_by_row(findings).get(0, {})
        chars.update(row_errors)
        chars.update(check_key_characteristics(schematojson_row))

    return normalize_characteristics(chars)


def enrich_dataset(
    input_path: Path,
    output_path: Path,
    base_columns: list[str],
    dataset: str,
) -> dict[str, Any]:
    if dataset == "schematojson":
        df = pd.read_csv(input_path, dtype=str, keep_default_na=False)
    else:
        df = pd.read_csv(input_path)

    missing = [column for column in base_columns if column not in df.columns]
    if missing:
        raise ValueError(f"{dataset} input missing columns: {missing}")

    df = df[base_columns].copy()
    characteristics = []
    for _, row in df.iterrows():
        schematojson_row = (
            load_schematojson_row_from_series(row) if dataset == "schematojson" else None
        )
        characteristics.append(enrich_row_characteristics(row, dataset, schematojson_row))

    char_df = pd.DataFrame(characteristics, columns=UNIFIED_CHAR_COLUMNS)
    output = pd.concat([df.reset_index(drop=True), char_df], axis=1)

    if dataset == "schematojson":
        output.to_csv(output_path, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)
    else:
        output.to_csv(output_path, index=False)

    return {"rows": len(output), "output_path": str(output_path)}


def organize_arqa(input_path: Path, output_path: Path) -> dict[str, Any]:
    return enrich_dataset(input_path, output_path, ARQA_BASE_COLUMNS, "arqa")


def organize_schematojson(input_path: Path, output_path: Path) -> dict[str, Any]:
    return enrich_dataset(input_path, output_path, SCHEMATOJSON_BASE_COLUMNS, "schematojson")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

ORGANIZERS = {
    "arqa": organize_arqa,
    "deepjsoneval": organize_deepjsoneval,
    "schematojson": organize_schematojson,
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Append the unified characteristic columns (from all organization scripts) to each dataset CSV."
    )
    parser.add_argument(
        "--dataset",
        choices=["all", *ORGANIZERS.keys()],
        default="all",
        help="Which dataset to process (default: all)",
    )
    parser.add_argument("--input", type=Path, help="Override input CSV path")
    parser.add_argument("--output", type=Path, help="Override output CSV path")
    args = parser.parse_args()

    datasets = list(ORGANIZERS.keys()) if args.dataset == "all" else [args.dataset]
    exit_code = 0

    for dataset in datasets:
        defaults = DEFAULT_PATHS[dataset]
        input_path = args.input if args.input and len(datasets) == 1 else defaults["input"]
        output_path = args.output if args.output and len(datasets) == 1 else defaults["output"]

        if not input_path.exists():
            print(f"[{dataset}] ERROR: input not found: {input_path}", file=sys.stderr)
            exit_code = 1
            continue

        print(f"[{dataset}] Loading {input_path} ...")
        summary = ORGANIZERS[dataset](input_path, output_path)
        print(f"[{dataset}] Wrote {summary['rows']} rows to {summary['output_path']}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
