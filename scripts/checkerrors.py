#!/usr/bin/env python3
"""Unified multi-dataset error checker (Phase 1: SchemaToJSON).

All framework, general, and SchemaToJSON-specific checks live in this one file.
ARQA / DeepJSONEval are stubbed for future team co-development.

Writes errors.csv next to each responses.jsonl (per-row error type counts).

Examples:
  python scripts/checkerrors.py --dataset SchemaToJSON
  python scripts/checkerrors.py --dataset SchemaToJSON \\
      --runs pipeline/outputs/.../responses.jsonl \\
      --findings-jsonl pipeline/outputs/error_reports/schematojson_findings.jsonl
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

# ---------------------------------------------------------------------------
# Paths / defaults
# ---------------------------------------------------------------------------

REPO = Path(__file__).resolve().parents[1]
TOKEN_LIMIT = 4096
SUPPORTED_DATASETS = ("SchemaToJSON", "ARQA", "DeepJSONEval")
RESPONSE_OMIT_FIELDS = frozenset({"prompt", "raw_response", "gold_json_raw"})

# Fixed CSV column order — only active SchemaToJSON checks for now.
# General + other dataset checks temporarily disabled.
ERROR_COLUMN_ORDER: list[str] = [
    "schematojson_cell_value_error",
    "schematojson_objects_instead_of_strings",
    "schematojson_hallucinated_type",
    "schematojson_wrong_root_structure",
    "schematojson_wrong_constituent",
    "schematojson_fields_not_allowed",
    "schematojson_missing_conditional_fields",
]

ERROR_DISPLAY_NAMES: dict[str, str] = {
    "schematojson_cell_value_error": "Cell Value Error",
    "schematojson_objects_instead_of_strings": "Arrays Instead Of Strings",
    "schematojson_hallucinated_type": "Hallucinated Type",
    "schematojson_wrong_root_structure": "Wrong Root Structure",
    "schematojson_wrong_constituent": "Wrong Constituent",
    "schematojson_fields_not_allowed": "Fields Not Allowed",
    "schematojson_missing_conditional_fields": "Missing Conditional Fields",
}

ASSIGNED_SCHEMATOJSON_RUNS: list[str] = [
    "pipeline/outputs/20260710_222504_schematojson_qwen3-8b_zero_shot/responses.jsonl",
    "pipeline/outputs/20260710_222840_schematojson_qwen3-8b_few_shot/responses.jsonl",
    "pipeline/outputs/20260710_223737_schematojson_qwen3-8b_nl_to_format/responses.jsonl",
    "pipeline/outputs/20260710_235853_schematojson_llama-3.1-8b-instruct_zero_shot/responses.jsonl",
    "pipeline/outputs/20260711_000500_schematojson_llama-3.1-8b-instruct_few_shot/responses.jsonl",
    "pipeline/outputs/20260711_000906_schematojson_llama-3.1-8b-instruct_nl_to_format/responses.jsonl",
    "pipeline/outputs/20260711_002147_schematojson_mistral-7b-instruct-v0.3_zero_shot/responses.jsonl",
    "pipeline/outputs/20260711_002657_schematojson_mistral-7b-instruct-v0.3_few_shot/responses.jsonl",
    "pipeline/outputs/20260711_003247_schematojson_mistral-7b-instruct-v0.3_nl_to_format/responses.jsonl",
    "pipeline/outputs/20260711_134855_schematojson_gemma-3-4b-it_zero_shot/responses.jsonl",
    "pipeline/outputs/20260711_135256_schematojson_gemma-3-4b-it_few_shot/responses.jsonl",
    "pipeline/outputs/20260711_135753_schematojson_gemma-3-4b-it_nl_to_format/responses.jsonl",
]

# ---------------------------------------------------------------------------
# Acceptable fields / SchemaToJSON record schemas
# ---------------------------------------------------------------------------

SCHEMATOJSON_TOP_LEVEL: set[str] = {"cell_index", "cell_record"}
SCHEMATOJSON_INNER_OTHER: set[str] = {"value", "type"}
SCHEMATOJSON_INNER_GCA: set[str] = {
    "value",
    "type",
    "constituent",
    "unit",
    "material",
}
SCHEMATOJSON_TYPES: set[str] = {"Other", "Glass_Compound_Amount"}

RECORD_SCHEMAS: dict[str, dict[str, set[str]]] = {
    "Other": {
        "required": set(SCHEMATOJSON_INNER_OTHER),
        "allowed": set(SCHEMATOJSON_INNER_OTHER),
    },
    "Glass_Compound_Amount": {
        "required": set(SCHEMATOJSON_INNER_GCA),
        "allowed": set(SCHEMATOJSON_INNER_GCA),
    },
}

ACCEPTABLE_FIELDS: dict[str, set[str]] = {
    "SchemaToJSON": SCHEMATOJSON_TOP_LEVEL | SCHEMATOJSON_INNER_GCA,
    "ARQA": set(),
    "DeepJSONEval": set(),
}


def acceptable_fields_for(dataset: str) -> set[str]:
    return set(ACCEPTABLE_FIELDS.get(dataset, set()))


# ---------------------------------------------------------------------------
# Core: Finding, CheckContext, registry
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    """One error finding emitted as a JSONL line."""

    dataset: str
    run_id: str
    model: str
    method: str
    row_id: str
    row_index: int
    error_type: str
    scope: str  # "general" | "dataset"
    message: str
    cell_index: int | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CheckContext:
    """Shared state for checks run against one responses.jsonl record."""

    record: dict[str, Any]
    dataset: str
    raw_response: str
    gold_json_raw: str
    method: str
    model: str
    run_id: str
    row_id: str
    row_index: int
    output_tokens: int
    json_part: str | None = None
    characteristics: dict[str, Any] = field(default_factory=dict)

    candidate_json: str = ""
    extract_note: str = ""
    model_obj: Any | None = None
    model_parse_error: str = ""
    gold_obj: Any | None = None
    gold_parse_error: str = ""
    normalized_obj: Any | None = None
    structure_variant: str = ""
    target_cells: dict[str, Any] | None = None

    def base_finding(
        self,
        error_type: str,
        scope: str,
        message: str,
        *,
        cell_index: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> Finding:
        return Finding(
            dataset=self.dataset,
            run_id=self.run_id,
            model=self.model,
            method=self.method,
            row_id=self.row_id,
            row_index=self.row_index,
            error_type=error_type,
            scope=scope,
            message=message,
            cell_index=cell_index,
            details=details or {},
        )


CheckFn = Callable[[CheckContext], list[Finding]]


@dataclass
class RegisteredCheck:
    name: str
    error_type: str
    scope: str
    fn: CheckFn
    skip_if_characteristic: str | None = None


class CheckRegistry:
    """Ordered registry of checks for a dataset."""

    def __init__(self) -> None:
        self._checks: list[RegisteredCheck] = []

    def register(
        self,
        fn: CheckFn,
        *,
        name: str,
        error_type: str,
        scope: str,
        skip_if_characteristic: str | None = None,
    ) -> CheckFn:
        self._checks.append(
            RegisteredCheck(
                name=name,
                error_type=error_type,
                scope=scope,
                fn=fn,
                skip_if_characteristic=skip_if_characteristic,
            )
        )
        return fn

    @property
    def checks(self) -> list[RegisteredCheck]:
        return list(self._checks)


def context_from_record(record: dict[str, Any], dataset: str) -> CheckContext:
    return CheckContext(
        record=record,
        dataset=dataset,
        raw_response=record.get("raw_response") or "",
        gold_json_raw=record.get("gold_json_raw") or record.get("gold_response") or "",
        method=record.get("method") or "",
        model=record.get("model") or "",
        run_id=record.get("run_id") or "",
        row_id=record.get("row_id") or "",
        row_index=int(record.get("row_index") or 0),
        output_tokens=int(record.get("output_tokens") or 0),
        json_part=record.get("json_part"),
        characteristics=dict(record.get("characteristics") or {}),
    )


# ---------------------------------------------------------------------------
# Characteristics suppression
# ---------------------------------------------------------------------------


def should_skip_check(
    skip_if_characteristic: str | None,
    row_characteristics: dict[str, Any],
    constant_characteristics: Optional[dict[str, bool]] = None,
) -> bool:
    """Skip a check when its characteristic is always true/false across the dataset."""
    if not skip_if_characteristic:
        return False
    if constant_characteristics is not None:
        if skip_if_characteristic in constant_characteristics:
            return True
    value = row_characteristics.get(skip_if_characteristic)
    if value in ("always_true", "always_false", "constant"):
        return True
    return False


def load_constant_characteristics_csv(path: str) -> dict[str, bool]:
    """Load CSV of characteristic columns that are constant T/F across the dataset."""
    result: dict[str, bool] = {}
    p = Path(path)
    if not p.exists():
        return result
    with p.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            name = (row.get("characteristic") or row.get("name") or "").strip()
            if not name:
                continue
            raw = (row.get("always_true_or_false") or row.get("value") or "true").strip().lower()
            result[name] = raw in ("true", "1", "yes", "always_true", "t")
    return result


def run_checks_for_record(
    record: dict[str, Any],
    dataset: str,
    registry: CheckRegistry,
    *,
    constant_characteristics: Optional[dict[str, bool]] = None,
    prepare_fn: Callable[[CheckContext], None] | None = None,
) -> list[Finding]:
    """Run all registered checks for one response record."""
    ctx = context_from_record(record, dataset)
    if prepare_fn is not None:
        prepare_fn(ctx)

    findings: list[Finding] = []
    for check in registry.checks:
        if should_skip_check(
            check.skip_if_characteristic,
            ctx.characteristics,
            constant_characteristics,
        ):
            continue
        findings.extend(check.fn(ctx))
    return findings


# ---------------------------------------------------------------------------
# Parse / extract helpers
# ---------------------------------------------------------------------------


def balanced_slice(text: str, start: int, open_ch: str, close_ch: str) -> str | None:
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def locate_json_span(raw: str) -> tuple[int, int, str]:
    """Return (start, end_exclusive, note) for the main JSON span in raw_response."""
    if not raw:
        return -1, -1, "empty"

    fenced = list(re.finditer(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL | re.IGNORECASE))
    for match in reversed(fenced):
        candidate = match.group(1).strip()
        if candidate.startswith("{") or candidate.startswith("["):
            return match.start(), match.end(), "fenced_codeblock"

    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = raw.find(open_ch)
        if start < 0:
            continue
        sliced = balanced_slice(raw, start, open_ch, close_ch)
        if sliced:
            return start, start + len(sliced), "balanced"
        return start, len(raw), "unbalanced_truncated"

    return -1, -1, "no_json"


def extract_candidate_json(raw: str, json_part: str | None = None) -> tuple[str, str]:
    """Extract the best JSON candidate from raw_response or json_part."""
    if json_part and json_part.strip():
        text = json_part.strip()
        try:
            json.loads(text)
            return text, "json_part"
        except json.JSONDecodeError:
            pass

    text = raw or ""
    if "PART 2" in text:
        after = text.split("PART 2", 1)[-1]
        after = re.sub(r"^[^\{,\[]*", "", after, count=1)
        start, end, note = locate_json_span(after)
        if start >= 0:
            span = after[start:end].strip()
            if note == "fenced_codeblock":
                match = re.search(
                    r"```(?:json)?\s*(.*?)\s*```", span, re.DOTALL | re.IGNORECASE
                )
                if match:
                    return match.group(1).strip(), "part2_" + note
            return span, "part2_" + note

    start, end, note = locate_json_span(text)
    if start < 0:
        return "", note
    if note == "fenced_codeblock":
        match = re.search(
            r"```(?:json)?\s*(.*?)\s*```", text[start:end], re.DOTALL | re.IGNORECASE
        )
        if match:
            return match.group(1).strip(), note
    return text[start:end].strip(), note


def try_parse_json(text: str) -> tuple[Any | None, str]:
    if not text or not text.strip():
        return None, "empty"
    try:
        return json.loads(text), ""
    except json.JSONDecodeError as exc:
        return None, f"{exc.msg} (line {exc.lineno} col {exc.colno})"


def parse_inner_record(item: Any) -> tuple[dict[str, Any] | None, str | None]:
    """Parse one cell_record item into a dict. Returns (parsed, error)."""
    if isinstance(item, dict):
        return item, None
    if not isinstance(item, str):
        return None, f"expected JSON string, got {type(item).__name__}"
    duplicate_keys: list[str] = []

    def object_pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        seen: set[str] = set()
        for key, _ in pairs:
            if key in seen:
                duplicate_keys.append(key)
            seen.add(key)
        return dict(pairs)

    try:
        parsed = json.loads(item, object_pairs_hook=object_pairs_hook)
    except json.JSONDecodeError as exc:
        return None, str(exc)
    if not isinstance(parsed, dict):
        return None, f"expected JSON object, got {type(parsed).__name__}"
    if duplicate_keys:
        return parsed, f"duplicate keys: {sorted(set(duplicate_keys))}"
    return parsed, None


def parse_inner_records(obj: Any | None) -> list[dict[str, Any] | None]:
    if not isinstance(obj, dict):
        return []
    recs = obj.get("cell_record")
    if not isinstance(recs, list):
        return []
    return [parse_inner_record(item)[0] for item in recs]


def classify_root_structure(obj: Any | None) -> str:
    """Classify top-level model JSON shape."""
    if obj is None:
        return "missing"
    if isinstance(obj, list):
        if obj and isinstance(obj[0], dict) and (
            "cell_index" in obj[0] or "cell_record" in obj[0]
        ):
            return "per_item_objects"
        return "top_level_array"
    if isinstance(obj, dict):
        keys = set(obj.keys())
        if keys == {"cell_index", "cell_record"}:
            return "parallel_lists"
        if "cell_index" in keys and "cell_record" not in keys:
            return "missing_cell_record"
        if "cell_record" in keys and "cell_index" not in keys:
            return "missing_cell_index"
        if "cell_index" in keys and "cell_record" in keys:
            extra = keys - {"cell_index", "cell_record"}
            return "parallel_lists_extra_keys" if extra else "parallel_lists"
        return "unexpected_object"
    return f"unexpected_{type(obj).__name__}"


def normalize_to_parallel(obj: Any) -> tuple[dict[str, Any] | None, str]:
    """Flatten per-item object arrays into parallel lists for downstream checks."""
    variant = classify_root_structure(obj)
    if variant == "per_item_objects" and isinstance(obj, list):
        indices: list[Any] = []
        records: list[Any] = []
        for item in obj:
            if not isinstance(item, dict):
                continue
            idx = item.get("cell_index")
            if isinstance(idx, list) and len(idx) == 1 and isinstance(idx[0], list):
                idx = idx[0]
            indices.append(idx)
            rec = item.get("cell_record")
            if isinstance(rec, list) and len(rec) == 1:
                rec = rec[0]
            records.append(rec)
        return {"cell_index": indices, "cell_record": records}, variant
    if isinstance(obj, dict):
        return obj, variant
    return None, variant


def parse_target_cells_from_prompt(prompt: str) -> dict[str, Any] | None:
    """Parse the Target cells: {...} block from a SchemaToJSON prompt."""
    if not prompt:
        return None
    marker = "Target cells:\n"
    idx = prompt.find(marker)
    if idx < 0:
        return None
    rest = prompt[idx + len(marker) :]
    end = rest.find("\n\n")
    block = (rest if end < 0 else rest[:end]).strip()
    try:
        parsed = ast.literal_eval(block)
    except (SyntaxError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def prepare_schematojson_context(ctx: CheckContext) -> None:
    """Fill CheckContext with parsed model/gold/target state for SchemaToJSON."""
    candidate, note = extract_candidate_json(ctx.raw_response, ctx.json_part)
    ctx.candidate_json = candidate
    ctx.extract_note = note
    model_obj, model_err = try_parse_json(candidate)
    ctx.model_obj = model_obj
    ctx.model_parse_error = model_err

    gold_obj, gold_err = try_parse_json(ctx.gold_json_raw)
    ctx.gold_obj = gold_obj
    ctx.gold_parse_error = gold_err

    if model_obj is not None:
        normalized, variant = normalize_to_parallel(model_obj)
        ctx.normalized_obj = normalized
        ctx.structure_variant = variant
    else:
        ctx.normalized_obj = None
        ctx.structure_variant = "unparseable"

    ctx.target_cells = parse_target_cells_from_prompt(ctx.record.get("prompt") or "")


# ---------------------------------------------------------------------------
# General checks (Phase 1)
# ---------------------------------------------------------------------------

# _PYTHON_HINTS = re.compile(
#     r"```python|\bimport\s+json\b|\bdef\s+\w+\(|\bprint\s*\(|\breturn\s+|json\.dumps",
#     re.IGNORECASE,
# )
# _FENCE_RE = re.compile(r"```(?:json|python)?", re.IGNORECASE)


# def _is_empty_raw(raw: Any) -> bool:
#     if raw is None:
#         return True
#     if isinstance(raw, float) and math.isnan(raw):
#         return True
#     if not isinstance(raw, str):
#         return False
#     stripped = raw.strip()
#     return stripped == "" or stripped.lower() in ("null", "none", "nan") or stripped in ("[]", "{}")


# def check_empty_response(ctx: CheckContext) -> list[Finding]:
#     if not _is_empty_raw(ctx.raw_response):
#         return []
#     if _is_empty_raw(ctx.gold_json_raw):
#         return []
#     return [
#         ctx.base_finding(
#             "empty_response",
#             "general",
#             "raw_response is empty/null while gold_json_raw is non-empty",
#             details={"raw_preview": repr(ctx.raw_response)[:80]},
#         )
#     ]


# def check_python_code(ctx: CheckContext) -> list[Finding]:
#     raw = ctx.raw_response or ""
#     if not _PYTHON_HINTS.search(raw):
#         return []
#     return [
#         ctx.base_finding(
#             "python_code_wrapping",
#             "general",
#             "raw_response contains Python code (import/def/print/json.dumps/```python)",
#             details={"snippet": raw[:240].replace("\n", "\\n")},
#         )
#     ]


# def check_markdown_fence(ctx: CheckContext) -> list[Finding]:
#     raw = ctx.raw_response or ""
#     if not _FENCE_RE.search(raw):
#         return []
#     if ctx.method == "nl_to_format":
#         part2 = raw.split("PART 2", 1)[-1] if "PART 2" in raw else raw
#         if not _FENCE_RE.search(part2):
#             return []
#     return [
#         ctx.base_finding(
#             "markdown_fence_wrapping",
#             "general",
#             "raw_response wraps output in a markdown code fence (```json / ```python / ```)",
#             details={"method": ctx.method},
#         )
#     ]


# def check_explanatory_text(ctx: CheckContext) -> list[Finding]:
#     """Flag leading prose for zero_shot/few_shot (bare JSON required).

#     nl_to_format PART 1 is expected and is checked by check_nl_to_format_envelope.
#     """
#     raw = (ctx.raw_response or "").strip()
#     if not raw or ctx.method == "nl_to_format":
#         return []
#     if raw.startswith("{") or raw.startswith("[") or raw.startswith("```"):
#         return []
#     if raw.startswith("PART 1"):
#         return [
#             ctx.base_finding(
#                 "explanatory_text",
#                 "general",
#                 "zero_shot/few_shot response begins with PART 1 (expected bare JSON only)",
#                 details={"method": ctx.method, "preview": raw[:160].replace("\n", "\\n")},
#             )
#         ]
#     prose_starts = ("Here is", "Okay", "The ", "Sure", "I ", "Below", "Based on", "Looking")
#     if any(raw.startswith(p) for p in prose_starts) or (
#         not raw.startswith("{")
#         and not raw.startswith("[")
#         and not raw.startswith("```")
#     ):
#         return [
#             ctx.base_finding(
#                 "explanatory_text",
#                 "general",
#                 "raw_response is not bare JSON (leading explanatory text or unexpected wrapper)",
#                 details={"method": ctx.method, "preview": raw[:160].replace("\n", "\\n")},
#             )
#         ]
#     return []


# def check_truncated(ctx: CheckContext) -> list[Finding]:
#     hit_limit = ctx.output_tokens >= TOKEN_LIMIT
#     raw = ctx.raw_response or ""
#     _start, _end, span_note = locate_json_span(raw)
#     unbalanced = span_note == "unbalanced_truncated"
#     brace_imbalance = raw.count("{") > raw.count("}")
#     if not hit_limit and not unbalanced:
#         return []
#     msg_parts = []
#     if hit_limit:
#         msg_parts.append(
#             f"output_tokens ({ctx.output_tokens}) reached token limit {TOKEN_LIMIT}"
#         )
#     if unbalanced or brace_imbalance:
#         msg_parts.append("JSON appears truncated/unbalanced")
#     return [
#         ctx.base_finding(
#             "truncated",
#             "general",
#             "; ".join(msg_parts) or "response truncated",
#             details={
#                 "output_tokens": ctx.output_tokens,
#                 "token_limit": TOKEN_LIMIT,
#                 "span_note": span_note,
#                 "brace_imbalance": brace_imbalance,
#             },
#         )
#     ]


# def check_invalid_json(ctx: CheckContext) -> list[Finding]:
#     raw = (ctx.raw_response or "").strip()
#     if not raw or ctx.model_obj is not None:
#         return []
#     note = ctx.extract_note or "no_json"
#     msg = f"could not parse JSON from raw_response ({note})"
#     if ctx.model_parse_error:
#         msg = f"{msg} - {ctx.model_parse_error}"
#     return [
#         ctx.base_finding(
#             "invalid_json",
#             "general",
#             msg,
#             details={
#                 "extract_note": ctx.extract_note,
#                 "parse_error": ctx.model_parse_error,
#                 "candidate_preview": (ctx.candidate_json or "")[:200],
#             },
#         )
#     ]


# def check_wrong_nesting(ctx: CheckContext) -> list[Finding]:
#     if ctx.model_obj is None or ctx.gold_obj is None:
#         return []
#     model_is_list = isinstance(ctx.model_obj, list)
#     gold_is_list = isinstance(ctx.gold_obj, list)
#     model_is_dict = isinstance(ctx.model_obj, dict)
#     gold_is_dict = isinstance(ctx.gold_obj, dict)
#     if model_is_list == gold_is_list and model_is_dict == gold_is_dict:
#         return []
#     return [
#         ctx.base_finding(
#             "wrong_nesting",
#             "general",
#             f"top-level nesting differs from gold: model="
#             f"{'array' if model_is_list else 'object' if model_is_dict else type(ctx.model_obj).__name__}, "
#             f"gold={'array' if gold_is_list else 'object' if gold_is_dict else type(ctx.gold_obj).__name__}",
#             details={
#                 "model_type": type(ctx.model_obj).__name__,
#                 "gold_type": type(ctx.gold_obj).__name__,
#                 "structure_variant": ctx.structure_variant,
#             },
#         )
#     ]


# def _signature_counts(obj: Any) -> Counter[str]:
#     counts: Counter[str] = Counter()
#     if not isinstance(obj, dict):
#         return counts
#     for inner in parse_inner_records(obj):
#         if not isinstance(inner, dict):
#             continue
#         value, typ = inner.get("value"), inner.get("type")
#         if value is not None and typ is not None:
#             sig = f"{value!r}:{typ!r}"
#         else:
#             sig = str(sorted(inner.items()))
#         counts[sig] += 1
#     return counts


# def _record_count(obj: Any) -> int | None:
#     if not isinstance(obj, dict):
#         return len(obj) if isinstance(obj, list) else None
#     idx = obj.get("cell_index")
#     if isinstance(idx, list):
#         return len(idx)
#     rec = obj.get("cell_record")
#     if isinstance(rec, list):
#         return len(rec)
#     return None


# def check_repetition(ctx: CheckContext) -> list[Finding]:
#     findings: list[Finding] = []
#     model = ctx.normalized_obj if ctx.normalized_obj is not None else ctx.model_obj
#     gold = ctx.gold_obj
#     gold_n = _record_count(gold)
#     model_n = _record_count(model)
#     if gold_n is not None and model_n is not None:
#         if model_n > gold_n:
#             findings.append(
#                 ctx.base_finding(
#                     "repetition",
#                     "general",
#                     f"model has more records than gold (model={model_n}, gold={gold_n})",
#                     details={"model_count": model_n, "gold_count": gold_n, "signal": "record_count"},
#                 )
#             )
#         elif model_n < gold_n:
#             findings.append(
#                 ctx.base_finding(
#                     "short_response",
#                     "general",
#                     f"model has fewer records than gold (model={model_n}, gold={gold_n})",
#                     details={"model_count": model_n, "gold_count": gold_n, "signal": "record_count"},
#                 )
#             )
#     if isinstance(model, dict) and isinstance(gold, dict):
#         gold_counts = _signature_counts(gold)
#         model_counts = _signature_counts(model)
#         for sig, allowed in gold_counts.items():
#             if allowed <= 1:
#                 continue
#             actual = model_counts.get(sig, 0)
#             if actual > allowed:
#                 findings.append(
#                     ctx.base_finding(
#                         "repetition",
#                         "general",
#                         f"signature {sig} appears {actual} times in model vs {allowed} in gold",
#                         details={
#                             "signature": sig,
#                             "gold_count": allowed,
#                             "model_count": actual,
#                             "signal": "duplicate_signature",
#                         },
#                     )
#                 )
#             elif 0 < actual < allowed:
#                 findings.append(
#                     ctx.base_finding(
#                         "short_response",
#                         "general",
#                         f"signature {sig} appears only {actual} times in model vs {allowed} in gold",
#                         details={
#                             "signature": sig,
#                             "gold_count": allowed,
#                             "model_count": actual,
#                             "signal": "duplicate_signature",
#                         },
#                     )
#                 )
#     return findings


# def check_wrong_field_names(ctx: CheckContext) -> list[Finding]:
#     obj = ctx.model_obj
#     if not isinstance(obj, dict):
#         return []
#     if ctx.dataset == "SchemaToJSON":
#         allowed = SCHEMATOJSON_TOP_LEVEL
#     else:
#         allowed = acceptable_fields_for(ctx.dataset)
#         if not allowed:
#             return []
#     extra = set(obj.keys()) - allowed
#     if not extra:
#         return []
#     return [
#         ctx.base_finding(
#             "wrong_field_names",
#             "general",
#             f"top-level fields not in acceptable list: {sorted(extra)}",
#             details={"extra": sorted(extra), "allowed": sorted(allowed)},
#         )
#     ]


# def register_general_checks(registry: CheckRegistry) -> None:
#     """Register Phase 1 general checks in execution order."""
#     for fn, name, error_type in (
#         (check_empty_response, "empty_response", "empty_response"),
#         (check_python_code, "python_code", "python_code_wrapping"),
#         (check_markdown_fence, "markdown_fence", "markdown_fence_wrapping"),
#         (check_explanatory_text, "explanatory_text", "explanatory_text"),
#         (check_truncated, "truncated", "truncated"),
#         (check_invalid_json, "invalid_json", "invalid_json"),
#         (check_wrong_nesting, "wrong_nesting", "wrong_nesting"),
#         (check_repetition, "repetition", "repetition"),
#         (check_wrong_field_names, "wrong_field_names", "wrong_field_names"),
#     ):
#         registry.register(fn, name=name, error_type=error_type, scope="general")


# Deferred stubs (not registered) for future team work:
# check_different_language, check_placeholder_values, check_backslashes,
# check_few_shot_contamination


# ---------------------------------------------------------------------------
# SchemaToJSON dataset-specific checks
# ---------------------------------------------------------------------------


def _gold_parallel(ctx: CheckContext) -> tuple[list[Any], list[Any]]:
    gold = ctx.gold_obj
    if not isinstance(gold, dict):
        return [], []
    idx = gold.get("cell_index") if isinstance(gold.get("cell_index"), list) else []
    rec = gold.get("cell_record") if isinstance(gold.get("cell_record"), list) else []
    return idx, rec


def _model_parallel(ctx: CheckContext) -> tuple[list[Any], list[Any]]:
    obj = ctx.normalized_obj if ctx.normalized_obj is not None else ctx.model_obj
    if not isinstance(obj, dict):
        return [], []
    idx = obj.get("cell_index") if isinstance(obj.get("cell_index"), list) else []
    rec = obj.get("cell_record") if isinstance(obj.get("cell_record"), list) else []
    return idx, rec


def _target_coords(ctx: CheckContext) -> list[list[int]] | None:
    t = ctx.target_cells
    if not isinstance(t, dict):
        return None
    try:
        i_list, j_list, k_list = t["i"], t["j"], t["k"]
    except KeyError:
        return None
    if not (len(i_list) == len(j_list) == len(k_list)):
        return None
    return [[int(i), int(j), int(k)] for i, j, k in zip(i_list, j_list, k_list)]


def _target_values(ctx: CheckContext) -> list[str] | None:
    t = ctx.target_cells
    if not isinstance(t, dict):
        return None
    vals = t.get("cell_value_processed")
    if not isinstance(vals, list):
        return None
    return [str(v) for v in vals]


def check_nl_to_format_envelope(ctx: CheckContext) -> list[Finding]:
    if ctx.method != "nl_to_format":
        return []
    raw = (ctx.raw_response or "").lstrip()
    if raw.startswith("PART 1"):
        return []
    return [
        ctx.base_finding(
            "nl_to_format_envelope",
            "dataset",
            "nl_to_format response must begin with 'PART 1 - Natural Language Response:'",
            details={"preview": raw[:120].replace("\n", "\\n")},
        )
    ]


def check_wrong_root_structure(ctx: CheckContext) -> list[Finding]:
    if ctx.model_obj is None:
        return []
    variant = ctx.structure_variant or ""
    if variant == "parallel_lists":
        return []
    return [
        ctx.base_finding(
            "schematojson_wrong_root_structure",
            "dataset",
            f"expected object with parallel cell_index / cell_record lists, "
            f"got structure_variant={variant!r}",
            details={
                "structure_variant": variant,
                "model_type": type(ctx.model_obj).__name__,
            },
        )
    ]


def check_length_mismatch(ctx: CheckContext) -> list[Finding]:
    if ctx.model_obj is None and ctx.normalized_obj is None:
        return []
    m_idx, m_rec = _model_parallel(ctx)
    g_idx, _g_rec = _gold_parallel(ctx)
    findings: list[Finding] = []
    if m_idx or m_rec:
        if len(m_idx) != len(m_rec):
            findings.append(
                ctx.base_finding(
                    "schematojson_length_mismatch",
                    "dataset",
                    f"len(cell_index)={len(m_idx)} != len(cell_record)={len(m_rec)}",
                    details={"cell_index_len": len(m_idx), "cell_record_len": len(m_rec)},
                )
            )
    if g_idx and m_idx and len(m_idx) != len(g_idx):
        findings.append(
            ctx.base_finding(
                "schematojson_length_mismatch",
                "dataset",
                f"len(model cell_index)={len(m_idx)} != len(gold cell_index)={len(g_idx)}",
                details={"model_len": len(m_idx), "gold_len": len(g_idx), "vs": "gold"},
            )
        )
    obj = ctx.normalized_obj if ctx.normalized_obj is not None else ctx.model_obj
    if isinstance(obj, dict) and "cell_index" in obj and "cell_record" not in obj:
        findings.append(
            ctx.base_finding(
                "schematojson_length_mismatch",
                "dataset",
                "cell_record key missing from model output",
                details={"keys": sorted(obj.keys())},
            )
        )
    return findings


def check_objects_instead_of_strings(ctx: CheckContext) -> list[Finding]:
    _m_idx, m_rec = _model_parallel(ctx)
    if not m_rec:
        return []
    findings: list[Finding] = []
    for i, item in enumerate(m_rec):
        if isinstance(item, dict):
            findings.append(
                ctx.base_finding(
                    "schematojson_objects_instead_of_strings",
                    "dataset",
                    f"cell_record[{i}] is a nested object; expected JSON string",
                    cell_index=i,
                    details={"item_type": "object", "keys": sorted(item.keys())},
                )
            )
        elif isinstance(item, list):
            findings.append(
                ctx.base_finding(
                    "schematojson_objects_instead_of_strings",
                    "dataset",
                    f"cell_record[{i}] is an array; expected JSON string",
                    cell_index=i,
                    details={"item_type": "array", "length": len(item)},
                )
            )
        elif item is not None and not isinstance(item, str):
            findings.append(
                ctx.base_finding(
                    "schematojson_objects_instead_of_strings",
                    "dataset",
                    f"cell_record[{i}] has type {type(item).__name__}; expected JSON string",
                    cell_index=i,
                    details={"item_type": type(item).__name__},
                )
            )
    return findings


def check_per_cell_semantics(ctx: CheckContext) -> list[Finding]:
    """Active SchemaToJSON per-cell checks only (others temporarily disabled).

    Emits: hallucinated_type, fields_not_allowed, missing_conditional_fields,
    cell_value_error, wrong_constituent.
    """
    m_idx, m_rec = _model_parallel(ctx)
    g_idx, g_rec = _gold_parallel(ctx)
    if not m_rec and not m_idx:
        return []

    target_vals = _target_values(ctx)
    findings: list[Finding] = []
    n = min(len(m_rec), len(g_rec)) if g_rec else len(m_rec)

    for i in range(max(len(m_rec), len(m_idx))):
        # Temporarily disabled: schematojson_wrong_cell_index
        if i >= len(m_rec):
            continue

        item = m_rec[i]
        parsed, parse_err = parse_inner_record(item)

        if parse_err and parse_err.startswith("duplicate keys"):
            findings.append(
                ctx.base_finding(
                    "schematojson_fields_not_allowed",
                    "dataset",
                    f"cell_record[{i}] has duplicate keys: {parse_err}",
                    cell_index=i,
                    details={"issue": parse_err},
                )
            )

        if parsed is None:
            # Temporarily disabled: schematojson_inner_json_parse_failure
            continue

        record_type = parsed.get("type")
        if record_type not in SCHEMATOJSON_TYPES:
            findings.append(
                ctx.base_finding(
                    "schematojson_hallucinated_type",
                    "dataset",
                    f"cell_record[{i}] type={record_type!r} not in {sorted(SCHEMATOJSON_TYPES)}",
                    cell_index=i,
                    details={"type": record_type},
                )
            )
            continue

        schema = RECORD_SCHEMAS[record_type]
        keys = set(parsed.keys())
        missing = set(schema["required"] - keys)
        for field_name in schema["required"]:
            if field_name in parsed and parsed[field_name] in (None, ""):
                missing.add(field_name)
        extra = keys - schema["allowed"]

        if missing:
            findings.append(
                ctx.base_finding(
                    "schematojson_missing_conditional_fields",
                    "dataset",
                    f"cell_record[{i}] type={record_type} missing required fields: {sorted(missing)}",
                    cell_index=i,
                    details={"type": record_type, "missing": sorted(missing)},
                )
            )
        if extra:
            findings.append(
                ctx.base_finding(
                    "schematojson_fields_not_allowed",
                    "dataset",
                    f"cell_record[{i}] type={record_type} has unexpected fields: {sorted(extra)}",
                    cell_index=i,
                    details={"type": record_type, "extra": sorted(extra)},
                )
            )

        if i >= n:
            continue
        gold_parsed, _ = parse_inner_record(g_rec[i])
        if gold_parsed is None:
            continue
        gold_type = gold_parsed.get("type")

        # Temporarily disabled: schematojson_wrong_record_type

        model_val = parsed.get("value")
        gold_val = gold_parsed.get("value")
        if model_val != gold_val:
            findings.append(
                ctx.base_finding(
                    "schematojson_cell_value_error",
                    "dataset",
                    f"cell_record[{i}] value={model_val!r} != gold value={gold_val!r}",
                    cell_index=i,
                    details={"model_value": model_val, "gold_value": gold_val},
                )
            )
        if target_vals is not None and i < len(target_vals):
            target_val = target_vals[i]
            if str(model_val) != target_val and model_val == gold_val:
                findings.append(
                    ctx.base_finding(
                        "schematojson_cell_value_error",
                        "dataset",
                        f"cell_record[{i}] value matches gold but not target_cells "
                        f"({model_val!r} != {target_val!r})",
                        cell_index=i,
                        details={
                            "model_value": model_val,
                            "target_value": target_val,
                            "vs": "target_cells",
                        },
                    )
                )

        if (
            record_type == "Glass_Compound_Amount"
            and gold_type == "Glass_Compound_Amount"
        ):
            if parsed.get("constituent") != gold_parsed.get("constituent"):
                findings.append(
                    ctx.base_finding(
                        "schematojson_wrong_constituent",
                        "dataset",
                        f"cell_record[{i}] constituent={parsed.get('constituent')!r} "
                        f"!= gold {gold_parsed.get('constituent')!r}",
                        cell_index=i,
                        details={
                            "model": parsed.get("constituent"),
                            "gold": gold_parsed.get("constituent"),
                        },
                    )
                )
            # Temporarily disabled: schematojson_wrong_unit, schematojson_wrong_material

    return findings


def register_schematojson_checks(registry: CheckRegistry) -> None:
    for fn, name, error_type in (
        # Temporarily disabled (treat as general / out of focus):
        # (check_nl_to_format_envelope, "nl_to_format_envelope", "nl_to_format_envelope"),
        # (check_length_mismatch, "length_mismatch", "schematojson_length_mismatch"),
        (check_wrong_root_structure, "wrong_root_structure", "schematojson_wrong_root_structure"),
        (
            check_objects_instead_of_strings,
            "objects_instead_of_strings",
            "schematojson_objects_instead_of_strings",
        ),
        (check_per_cell_semantics, "per_cell_semantics", "schematojson_per_cell"),
    ):
        registry.register(fn, name=name, error_type=error_type, scope="dataset")


# ---------------------------------------------------------------------------
# Dataset dispatch (SchemaToJSON implemented; ARQA / DeepJSONEval stubs)
# ---------------------------------------------------------------------------


def get_registry(dataset: str) -> CheckRegistry:
    if dataset == "SchemaToJSON":
        registry = CheckRegistry()
        # register_general_checks(registry)  # temporarily disabled
        register_schematojson_checks(registry)
        return registry
    if dataset == "ARQA":
        raise NotImplementedError(
            "ARQA error checks are not implemented yet (Phase 1 = SchemaToJSON only)."
        )
    if dataset == "DeepJSONEval":
        raise NotImplementedError(
            "DeepJSONEval error checks are not implemented yet "
            "(Phase 1 = SchemaToJSON only)."
        )
    raise ValueError(
        f"Unknown dataset {dataset!r}. Supported: {', '.join(SUPPORTED_DATASETS)}"
    )


def get_prepare_fn(dataset: str) -> Callable[[CheckContext], None] | None:
    if dataset == "SchemaToJSON":
        return prepare_schematojson_context
    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def resolve_run_paths(runs: list[str] | None, dataset: str) -> list[Path]:
    if runs:
        paths = [Path(r) if Path(r).is_absolute() else REPO / r for r in runs]
    elif dataset == "SchemaToJSON":
        paths = [REPO / r for r in ASSIGNED_SCHEMATOJSON_RUNS]
    else:
        raise SystemExit(
            f"No default runs for dataset {dataset!r}; pass --runs explicitly."
        )
    missing = [p for p in paths if not p.exists()]
    if missing:
        for p in missing:
            print(f"WARNING: run file not found: {p}", file=sys.stderr)
        paths = [p for p in paths if p.exists()]
    if not paths:
        raise SystemExit("No existing responses.jsonl run files to process.")
    return paths


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"WARNING: skip {path}:{line_no}: {exc}", file=sys.stderr)
    return rows


def response_cell(record: dict[str, Any]) -> str:
    """Serialize the record for the Response column (omit bulky fields)."""
    slim = {k: v for k, v in record.items() if k not in RESPONSE_OMIT_FIELDS}
    return json.dumps(slim, ensure_ascii=False)


def write_errors_csv(
    run_path: Path,
    records: list[dict[str, Any]],
    findings: list[Finding],
) -> Path:
    """Write errors.csv next to responses.jsonl with per-row error-type counts."""
    out_path = run_path.parent / "errors.csv"
    counts_by_row: dict[int, Counter[str]] = defaultdict(Counter)
    for f in findings:
        counts_by_row[f.row_index][f.error_type] += 1

    header = ["Response"] + [
        ERROR_DISPLAY_NAMES.get(et, et) for et in ERROR_COLUMN_ORDER
    ]
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for i, record in enumerate(records):
            row_index = record.get("row_index", i)
            if not isinstance(row_index, int):
                row_index = i
            counts = counts_by_row[row_index]
            row = [response_cell(record)]
            for et in ERROR_COLUMN_ORDER:
                row.append(counts.get(et, 0))
            writer.writerow(row)
    return out_path


def print_summary(findings: list[Finding]) -> None:
    if not findings:
        print("No findings.")
        return
    by_type = Counter(f.error_type for f in findings)
    by_model_method = Counter((f.model, f.method) for f in findings)
    by_type_mm = Counter((f.error_type, f.model, f.method) for f in findings)

    print(f"\nTotal findings: {len(findings)}")
    print("\nBy error_type:")
    for et, n in by_type.most_common():
        print(f"  {n:5d}  {et}")

    print("\nBy model x method:")
    for (model, method), n in sorted(by_model_method.items(), key=lambda x: -x[1]):
        short = model.split("/")[-1] if "/" in model else model
        print(f"  {n:5d}  {short} / {method}")

    print("\nTop error_type x model x method:")
    for (et, model, method), n in by_type_mm.most_common(25):
        short = model.split("/")[-1] if "/" in model else model
        print(f"  {n:5d}  {et}  |  {short} / {method}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Unified schema error checker")
    parser.add_argument(
        "--dataset",
        required=True,
        choices=list(SUPPORTED_DATASETS),
        help="Dataset to evaluate (Phase 1: only SchemaToJSON is implemented)",
    )
    parser.add_argument(
        "--runs",
        nargs="+",
        default=None,
        help="One or more responses.jsonl paths (default: 12 assigned SchemaToJSON runs)",
    )
    parser.add_argument(
        "--findings-jsonl",
        default=None,
        help="Optional path to also write the detailed findings JSONL dump",
    )
    parser.add_argument(
        "--characteristics-csv",
        default=None,
        help="Optional CSV of constant characteristics used to suppress checks",
    )
    args = parser.parse_args(argv)

    if args.dataset != "SchemaToJSON":
        print(
            f"ERROR: dataset {args.dataset!r} checks are not implemented yet "
            "(Phase 1 = SchemaToJSON only).",
            file=sys.stderr,
        )
        return 1

    constant_chars = None
    if args.characteristics_csv:
        constant_chars = load_constant_characteristics_csv(args.characteristics_csv)

    registry = get_registry(args.dataset)
    prepare_fn = get_prepare_fn(args.dataset)
    run_paths = resolve_run_paths(args.runs, args.dataset)

    all_findings: list[Finding] = []
    rows_processed = 0
    csv_paths: list[Path] = []
    for path in run_paths:
        records = load_jsonl(path)
        print(f"Processing {path.relative_to(REPO)} ({len(records)} rows)...")
        run_findings: list[Finding] = []
        for record in records:
            dataset = record.get("dataset") or args.dataset
            if dataset != args.dataset:
                print(
                    f"  WARNING: record dataset={dataset!r} != --dataset {args.dataset!r}",
                    file=sys.stderr,
                )
            findings = run_checks_for_record(
                record,
                args.dataset,
                registry,
                constant_characteristics=constant_chars,
                prepare_fn=prepare_fn,
            )
            run_findings.extend(findings)
            all_findings.extend(findings)
            rows_processed += 1

        csv_path = write_errors_csv(path, records, run_findings)
        csv_paths.append(csv_path)
        print(f"  Wrote {len(run_findings)} findings -> {csv_path.relative_to(REPO)}")

    if args.findings_jsonl:
        out_path = Path(args.findings_jsonl)
        if not out_path.is_absolute():
            out_path = REPO / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as fh:
            for finding in all_findings:
                fh.write(json.dumps(finding.to_dict(), ensure_ascii=False) + "\n")
        print(f"\nAlso wrote findings JSONL -> {out_path}")

    print(
        f"\nWrote {len(csv_paths)} errors.csv files "
        f"({len(all_findings)} findings from {rows_processed} rows)"
    )
    print_summary(all_findings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
