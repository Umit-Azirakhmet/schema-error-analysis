"""Shared gold JSON structural analysis used by dataset add-fields scripts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

NUMERIC_STRING_RE = re.compile(r"^[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$")
LONG_TEXT_MIN_CHARS = 40
LONG_TEXT_MIN_WORDS = 5


def scalar_paths(value: Any, prefix: tuple = ()) -> dict[tuple, Any]:
    """Gold opportunity slots, including nulls, with collision-free tuple paths.

    Embedded JSON strings remain one scalar slot. Structural feature extraction
    below deliberately expands embedded JSON; those feature counts must not be
    substituted for these normalization denominators.
    """
    if isinstance(value, dict):
        return {path: leaf for key, child in value.items()
                for path, leaf in scalar_paths(child, prefix + (key,)).items()}
    if isinstance(value, list):
        return {path: leaf for index, child in enumerate(value)
                for path, leaf in scalar_paths(child, prefix + (index,)).items()}
    return {prefix: value}


@dataclass
class GoldJsonStructureMetrics:
    nesting_depth: int = 0
    total_object_count: int = 0
    max_array_nesting_depth: int = 0
    total_array_count: int = 0
    max_array_length: int = 0
    total_key_count: int = 0
    unique_keys: set[str] = field(default_factory=set)
    max_key_length: int = 0
    long_text_value_count: int = 0
    numeric_value_count: int = 0
    alphanumeric_value_count: int = 0
    value_lengths: list[int] = field(default_factory=list)
    value_types: set[str] = field(default_factory=set)


def _looks_like_embedded_json(value: str) -> bool:
    stripped = value.strip()
    return (stripped.startswith("{") and stripped.endswith("}")) or (
        stripped.startswith("[") and stripped.endswith("]")
    )


def _is_numeric_leaf(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        return bool(NUMERIC_STRING_RE.match(value.strip()))
    return False


def _is_alphanumeric_leaf(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return False
    has_letter = any(char.isalpha() for char in text)
    has_digit = any(char.isdigit() for char in text)
    return has_letter and has_digit


def _is_long_text_leaf(value: Any) -> bool:
    """Treat multi-word or long strings as sentence/paragraph-like values."""
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return False
    words = [word for word in text.split() if word]
    if len(text) >= LONG_TEXT_MIN_CHARS:
        return True
    if len(words) >= LONG_TEXT_MIN_WORDS:
        return True
    if len(words) >= 2 and any(punct in text for punct in ".!?;:"):
        return True
    return False


def _record_leaf_value(value: Any, metrics: GoldJsonStructureMetrics) -> None:
    if isinstance(value, bool):
        metrics.value_types.add("boolean")
        text = str(value).lower()
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        metrics.value_types.add("number")
        text = str(value)
        metrics.numeric_value_count += 1
    elif isinstance(value, str):
        metrics.value_types.add("string")
        text = value
        if _is_numeric_leaf(value):
            metrics.numeric_value_count += 1
        if _is_alphanumeric_leaf(value):
            metrics.alphanumeric_value_count += 1
        if _is_long_text_leaf(value):
            metrics.long_text_value_count += 1
    else:
        return

    metrics.value_lengths.append(len(text))


def _walk_gold_json(obj: Any, struct_depth: int, array_depth: int, metrics: GoldJsonStructureMetrics) -> None:
    if isinstance(obj, dict):
        metrics.total_object_count += 1
        metrics.nesting_depth = max(metrics.nesting_depth, struct_depth)
        for key, value in obj.items():
            key_text = str(key)
            metrics.total_key_count += 1
            metrics.unique_keys.add(key_text)
            metrics.max_key_length = max(metrics.max_key_length, len(key_text))
            _walk_gold_json(value, struct_depth + 1, array_depth, metrics)
        return

    if isinstance(obj, list):
        metrics.total_array_count += 1
        metrics.nesting_depth = max(metrics.nesting_depth, struct_depth)
        metrics.max_array_length = max(metrics.max_array_length, len(obj))
        next_array_depth = array_depth + 1
        metrics.max_array_nesting_depth = max(metrics.max_array_nesting_depth, next_array_depth)
        for item in obj:
            _walk_gold_json(item, struct_depth + 1, next_array_depth, metrics)
        return

    if isinstance(obj, str) and _looks_like_embedded_json(obj):
        try:
            unpacked = json.loads(obj)
            _walk_gold_json(unpacked, struct_depth, array_depth, metrics)
            return
        except json.JSONDecodeError:
            pass

    _record_leaf_value(obj, metrics)


def analyze_gold_json_structure(gold_raw: object) -> dict[str, Any]:
    """Compute structural and leaf-value metrics from a raw gold JSON string."""
    metrics = GoldJsonStructureMetrics()
    gold_text = str(gold_raw if gold_raw is not None else "")
    gold_json_length = len(gold_text)

    json_str = gold_text.strip()
    if json_str and json_str.lower() != "nan":
        try:
            parsed = json.loads(json_str)
            _walk_gold_json(parsed, struct_depth=1, array_depth=0, metrics=metrics)
        except json.JSONDecodeError:
            pass

    if metrics.value_lengths:
        average_value_length = round(sum(metrics.value_lengths) / len(metrics.value_lengths), 2)
        max_value_length = max(metrics.value_lengths)
    else:
        average_value_length = 0.0
        max_value_length = 0

    type_order = ("boolean", "number", "string")
    value_types = ", ".join(
        label for label in type_order if label in metrics.value_types
    )

    return {
        "gold_json_length": gold_json_length,
        "nesting_depth": metrics.nesting_depth,
        "total_object_count": metrics.total_object_count,
        "max_array_nesting_depth": metrics.max_array_nesting_depth,
        "total_array_count": metrics.total_array_count,
        "max_array_length": metrics.max_array_length,
        "total_key_count": metrics.total_key_count,
        "unique_key_count": len(metrics.unique_keys),
        "max_key_length": metrics.max_key_length,
        "long_text_value_count": metrics.long_text_value_count,
        "numeric_value_count": metrics.numeric_value_count,
        "alphanumeric_value_count": metrics.alphanumeric_value_count,
        "max_value_length": max_value_length,
        "average_value_length": average_value_length,
        "value_types": value_types,
    }
