#!/usr/bin/env python3
"""
general_error_detector.py

Detects General Errors + Dataset-Specific Errors (SchemaToJSON, ARQA, DeepJSONEval).
Saves CSV summaries.

Example:
   python general_error_detector.py --input pipeline/outputs
   python general_error_detector.py --input path/to/responses.jsonl
"""

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set

try:
    from .opportunity_metrics import evaluate, strict_parse
    from .error_taxonomy import RAW_LEAVES, family_flags
    from .response_assessment import code_response, completion
except ImportError:
    from opportunity_metrics import evaluate, strict_parse
    from error_taxonomy import RAW_LEAVES, family_flags
    from response_assessment import code_response, completion


# ============================================================
# ERROR COLUMNS (General + Dataset Specific)
# ============================================================

GENERAL_ERROR_COLUMNS = [
    "truncated_count", "repetition_count",
    "hallucinated_fields_count", "missing_fields_count",
    "different_language_count", "empty_response_count",
    "placeholder_values_count", "backslash_issues_count", "wrong_nesting_count",
    "wrong_nesting_depth_count", "wrong_types_count", "longer_shorter_count",
    "wrong_order_count", "explanatory_text_count", "incorrect_values_count",
    "invalid_json_syntax_count", "markdown_code_fence_count",
    "python_code_wrapping_count",
]

DATASET_SPECIFIC_COLUMNS = [
    # SchemaToJSON
    "schematojson_cell_value_errors", "schematojson_arrays_instead_of_strings",
    "schematojson_hallucinated_type", "schematojson_wrong_root_structure",
    "schematojson_wrong_constituent", "schematojson_fields_not_allowed",
    "schematojson_missing_conditional_fields",
    # ARQA
    "arqa_hallucinated_claims", "arqa_wrong_claim_type", "arqa_hallucinated_claim_type",
    "arqa_hallucinated_table_id", "arqa_hallucinated_para_id", "arqa_missing_cell_text",
    "arqa_empty_evidence_span", "arqa_missing_top_level_fields",
    # DeepJSONEval
    "deepjson_enum_check", "deepjson_schema_echo", "deepjson_missing_required_fields",
    "deepjson_property_type_check", "deepjson_property_count_mismatch",
]

ALL_ERROR_COLUMNS = GENERAL_ERROR_COLUMNS + DATASET_SPECIFIC_COLUMNS

GENERAL_ACCEPTABLE_FIELDS = {
    # ARQA
    "answer", "claims", "type", "claim_text", "evidence",
    "table_cells", "text_spans", "table_id", "row", "col",
    "cell_text", "para_id", "char_start", "char_end", "text",

    # SchemaToJSON
    "cell_index", "cell_record", "value", "constituent", "unit", "material",

    # Schema keywords / common DeepJSONEval fields
    "Year", "IsSequel", "Ratings", "Crew", "GameInfo", "GameStatistics", "DLCs",
    "PersonalInfo", "MedicalHistory", "BasicInfo", "TechnicalSpecs", "Features",
}

PLACEHOLDER_STRINGS = {"unknown", "n/a", "na", "none", "null", "nan", "xx", ""}
SCHEMATOJSON_ALLOWED_TYPES = {"Glass_Compound_Amount", "Other"}
ARQA_ALLOWED_CLAIM_TYPES = {"text", "table"}
ARQA_ID_PATTERN = re.compile(r"^VW.{12}$")


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^\s*```(?:json|python)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def find_json_span(text: str) -> Optional[Tuple[int, int]]:
    """Find the first outer candidate span; never salvage a nested subtree.

    A truncated parent containing a complete child must remain truncated.
    """
    first = find_first_json_opener(text)
    if first is None:
        return None
    for start in (first,):
        stack: List[str] = []
        in_string = False
        escaped = False

        for i in range(start, len(text)):
            c = text[i]

            if in_string:
                if escaped:
                    escaped = False
                elif c == "\\":
                    escaped = True
                elif c == '"':
                    in_string = False
                continue

            if c == '"':
                in_string = True
            elif c in "{[":
                stack.append(c)
            elif c in "}]":
                if not stack:
                    break
                open_char = stack.pop()
                if open_char == "{" and c != "}":
                    break
                if open_char == "[" and c != "]":
                    break
                if not stack:
                    return start, i + 1

    return None


def find_first_json_opener(text: str) -> Optional[int]:
    positions = [p for p in (text.find("{"), text.find("[")) if p >= 0]
    return min(positions) if positions else None


def count_json_structure_chars(text: str) -> Tuple[int, int, int, int]:
    """
    Count structural braces and brackets while ignoring characters inside
    JSON strings. Returns:
        open_braces, close_braces, open_brackets, close_brackets
    """
    open_braces = close_braces = 0
    open_brackets = close_brackets = 0
    in_string = False
    escaped = False

    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            open_braces += 1
        elif char == "}":
            close_braces += 1
        elif char == "[":
            open_brackets += 1
        elif char == "]":
            close_brackets += 1

    return open_braces, close_braces, open_brackets, close_brackets


def extract_json_candidate(raw_response: str) -> Tuple[str, str, str, bool]:
    """
    Strip outer code fences, then:
      1. Use the first complete JSON object/array when one exists.
      2. Otherwise, if an opening { or [ exists, use everything from it to the end.
      3. Otherwise return no candidate.

    Returns:
        candidate_json, before_json, after_json, has_complete_span
    """
    no_fence = strip_code_fences(raw_response)
    if strict_parse(no_fence)[0]:
        return no_fence, '', '', True
    # An explicit answer section takes priority over illustrative objects in
    # PART 1. Never accept an intermediate dictionary as an executable answer.
    answer = re.search(r'(?im)^\s*PART\s*2\b\s*(?:-\s*)?(?:JSON(?:\s+Response)?\s*)?(?::\s*|(?=[{\[]))', no_fence)
    if answer:
        candidate, before, after, complete = extract_json_candidate(no_fence[answer.end():])
        return candidate, no_fence[:answer.end()] + before, after, complete
    if code_response(no_fence):
        return '', no_fence, '', False
    span = find_json_span(no_fence)

    if span:
        start, end = span
        # A stray closing delimiter belongs to the malformed answer, not to a
        # prose envelope. Dropping it would turn a syntax defect into a pass.
        extra_closers = re.match(r'(?:\s*[}\]])+', no_fence[end:])
        if extra_closers:
            end += extra_closers.end()
        return (
            no_fence[start:end].strip(),
            no_fence[:start].strip(),
            no_fence[end:].strip(),
            True,
        )

    opener = find_first_json_opener(no_fence)
    if opener is None:
        return "", no_fence.strip(), "", False

    return no_fence[opener:].strip(), no_fence[:opener].strip(), "", False


def parse_json_safely(text: Any) -> Optional[Any]:
    if text is None:
        return None
    if isinstance(text, (dict, list)):
        return text
    if not isinstance(text, str):
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def is_empty_json_value(value: Any) -> bool:
    if value is None:
        return True
    if value == {} or value == []:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"", "null", "none", "nan"}
    return False


def collect_paths(obj: Any, path: str = "") -> Dict[str, Any]:
    """Flatten JSON into path -> scalar/container value."""
    out: Dict[str, Any] = {}
    if isinstance(obj, dict):
        if path:
            out[path] = obj
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else str(k)
            out.update(collect_paths(v, new_path))
    elif isinstance(obj, list):
        if path:
            out[path] = obj
        for i, v in enumerate(obj):
            new_path = f"{path}[{i}]"
            out.update(collect_paths(v, new_path))
    else:
        out[path] = obj
    return out


def collect_scalar_paths(obj: Any, path: str = "") -> Dict[str, Any]:
    """Flatten JSON into path -> scalar only."""
    out: Dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else str(k)
            out.update(collect_scalar_paths(v, new_path))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_path = f"{path}[{i}]"
            out.update(collect_scalar_paths(v, new_path))
    else:
        out[path] = obj
    return out


def collect_container_paths(obj: Any, path: str = "") -> Dict[str, str]:
    """Collect paths and mark each as object, array, or scalar."""
    out: Dict[str, str] = {}
    if isinstance(obj, dict):
        out[path or "$root"] = "object"
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else str(k)
            out.update(collect_container_paths(v, new_path))
    elif isinstance(obj, list):
        out[path or "$root"] = "array"
        for i, v in enumerate(obj):
            new_path = f"{path}[{i}]"
            out.update(collect_container_paths(v, new_path))
    else:
        out[path or "$root"] = "scalar"
    return out


def max_json_depth(obj: Any) -> int:
    """Return maximum object/array nesting depth. A scalar has depth 0."""
    if isinstance(obj, dict):
        if not obj:
            return 1
        return 1 + max(max_json_depth(v) for v in obj.values())
    if isinstance(obj, list):
        if not obj:
            return 1
        return 1 + max(max_json_depth(v) for v in obj)
    return 0


def collect_key_names(obj: Any) -> List[str]:
    keys: List[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.append(str(k))
            keys.extend(collect_key_names(v))
    elif isinstance(obj, list):
        for item in obj:
            keys.extend(collect_key_names(item))
    return keys


def normalize_scalar(value: Any) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    return str(value).strip().lower()


def normalize_text(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text).strip().lower())


def token_set(text: Any) -> Set[str]:
    return set(re.findall(r"[a-zA-Z0-9]+", normalize_text(text)))


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def same_jsonish_type(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b)
    if (
        isinstance(a, (int, float))
        and isinstance(b, (int, float))
        and not isinstance(a, bool)
        and not isinstance(b, bool)
    ):
        return True
    return type(a) is type(b)


def json_word_count(obj: Any) -> int:
    return len(re.findall(r"\w+", json.dumps(obj, ensure_ascii=False)))


def maybe_parse_record(record: Any) -> Any:
    """SchemaToJSON cell_record items are often JSON strings; parse when possible."""
    if isinstance(record, str):
        parsed = parse_json_safely(record)
        return parsed if parsed is not None else record
    return record


def get_schematojson_records(obj: Any) -> List[Any]:
    """Return SchemaToJSON records in comparable list form."""
    if isinstance(obj, dict):
        records = obj.get("cell_record", [])
        if isinstance(records, list):
            return [maybe_parse_record(r) for r in records]
        return [maybe_parse_record(records)]
    if isinstance(obj, list):
        return [maybe_parse_record(r) for r in obj]
    return []


def collect_named_field_values(obj: Any, field_name: str) -> List[Any]:
    """Collect field values recursively in JSON traversal order."""
    values: List[Any] = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == field_name:
                values.append(value)
            values.extend(collect_named_field_values(value, field_name))
    elif isinstance(obj, list):
        for item in obj:
            values.extend(collect_named_field_values(item, field_name))

    return values


def walk_values(obj: Any) -> List[Any]:
    values: List[Any] = []
    if isinstance(obj, dict):
        for v in obj.values():
            values.extend(walk_values(v))
    elif isinstance(obj, list):
        for item in obj:
            values.extend(walk_values(item))
    else:
        values.append(obj)
    return values


def extract_table_cells_from_evidence(evidence: Any) -> List[Dict[str, Any]]:
    if isinstance(evidence, dict):
        cells = evidence.get("table_cells", [])
        return cells if isinstance(cells, list) else []
    if isinstance(evidence, list):
        return [
            e for e in evidence
            if isinstance(e, dict)
            and ("table_id" in e or "cell_text" in e or "row" in e or "col" in e)
        ]
    return []


def extract_text_spans_from_evidence(evidence: Any) -> List[Dict[str, Any]]:
    if isinstance(evidence, dict):
        spans = evidence.get("text_spans", [])
        return spans if isinstance(spans, list) else []
    if isinstance(evidence, list):
        return [
            e for e in evidence
            if isinstance(e, dict)
            and ("para_id" in e or "char_start" in e or "char_end" in e)
        ]
    return []


def collect_arqa_table_ids(claims: List[Any]) -> Set[str]:
    ids: Set[str] = set()
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        for cell in extract_table_cells_from_evidence(claim.get("evidence", {})):
            tid = cell.get("table_id")
            if tid:
                ids.add(str(tid))
    return ids


def collect_arqa_para_ids(claims: List[Any]) -> Set[str]:
    ids: Set[str] = set()
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        for span in extract_text_spans_from_evidence(claim.get("evidence", {})):
            pid = span.get("para_id")
            if pid:
                ids.add(str(pid))
    return ids


# ============================================================
# ERROR DETECTOR
# ============================================================

class GeneralErrorDetector:
    def __init__(self, token_limit: int = 4096, acceptable_fields: Optional[Set[str]] = None):
        self.token_limit = token_limit
        self.acceptable_fields = acceptable_fields or GENERAL_ACCEPTABLE_FIELDS

    def detect(self, row: Dict[str, Any], run_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        run_info = run_info or {}
        raw = str(row.get('raw_response') or '')
        candidate, before, after, complete_span = extract_json_candidate(raw)
        result = self._detect_legacy(row, run_info)
        dataset = str(row.get('dataset', run_info.get('dataset', '')))
        result.update(evaluate(candidate, row.get('gold_json_raw', row.get('gold')), self._find_schema(row), dataset))
        result['raw_valid_parse'] = strict_parse(raw)[0]
        # The legacy regexes can match prose/code words INSIDE JSON values.
        # Only material outside the intended candidate is an envelope error.
        result['envelope_contamination_detected'] = bool(
            not result['raw_valid_parse'] and (before or after or strip_code_fences(raw) != raw.strip()))
        result['has_json_candidate'] = bool(candidate)
        complete, reason = completion(raw, candidate, row.get('output_tokens'),
            self.token_limit, row.get('error'), row.get('finish_reason'))
        result.update(is_complete=complete, completion_rule=reason,
                      detector_version='eacl-v2')
        # No comparison detector is allowed to convert an absent/unparseable
        # candidate or missing gold into zero errors.
        if not result['is_content_assessable']:
            for col in ALL_ERROR_COLUMNS:
                if col not in RAW_LEAVES:
                    result[col] = None
        dataset = str(row.get('dataset', run_info.get('dataset', ''))).lower()
        for col in DATASET_SPECIFIC_COLUMNS:
            prefix = col.split('_')[0]
            applicable = (prefix == 'deepjson' and 'deepjson' in dataset or
                          prefix == 'arqa' and 'arqa' in dataset or
                          prefix == 'schematojson' and ('schema' in dataset))
            if not applicable:
                result[col] = None
        if not result['is_schema_assessable']:
            for col in DATASET_SPECIFIC_COLUMNS:
                if col.startswith('deepjson_') and col != 'deepjson_schema_echo':
                    result[col] = None
        result['invalid_json_syntax_count'] = int(not result['valid_parse'])
        result['total_errors'] = sum(result[c] for c in ALL_ERROR_COLUMNS if isinstance(result[c], int))
        result.update(family_flags(result))
        result['contract_non_conformance_flag'] = (None if result['contract_valid'] is None else not result['contract_valid'])
        return result

    def _detect_legacy(self, row: Dict[str, Any], run_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        run_info = run_info or {}
        dataset = str(row.get("dataset", run_info.get("dataset", ""))).lower()

        raw_value = row.get("raw_response", "")
        raw_text = "" if raw_value is None else str(raw_value)
        gold_raw = row.get("gold_json_raw", row.get("gold", "{}"))
        output_tokens = row.get(
            "output_tokens",
            row.get("completion_tokens", run_info.get("output_tokens")),
        )

        candidate_json, before_json, after_json, has_complete_span = extract_json_candidate(raw_text)
        parsed_raw = parse_json_safely(candidate_json)
        parsed_gold = parse_json_safely(gold_raw)
        if parsed_gold is None:
            parsed_gold = {}

        schema = self._find_schema(row)
        errors: Dict[str, Any] = {col: 0 for col in ALL_ERROR_COLUMNS}

        # --------------------
        # General raw-text errors
        # --------------------
        errors["empty_response_count"] = self.detect_empty_field_values(parsed_raw, parsed_gold)
        errors["markdown_code_fence_count"] = self.detect_markdown_code_fence(raw_text)
        errors["invalid_json_syntax_count"] = self.detect_invalid_json_syntax(
            raw_text=raw_text,
            candidate_json=candidate_json,
            parsed_raw=parsed_raw,
            has_complete_span=has_complete_span,
        )
        errors["truncated_count"] = self.detect_truncated(
            raw_text=raw_text,
            output_tokens=output_tokens,
        )
        errors["backslash_issues_count"] = self.detect_backslash_issues(
            raw_text,
            candidate_json,
            gold_raw,
        )
        errors["python_code_wrapping_count"] = self.detect_python_code_wrapping(raw_text)
        errors["explanatory_text_count"] = self.detect_explanatory_text(
            raw_text,
            before_json,
            after_json,
            parsed_raw,
        )
        errors["different_language_count"] = self.detect_different_language(raw_text)

        # If raw JSON cannot be parsed, comparison-based checks cannot safely run.
        if parsed_raw is None:
            errors["missing_fields_count"] = self.detect_missing_fields(None, parsed_gold)
            if "deepjson" in dataset:
                self.detect_deepjsoneval(
                    parsed_raw,
                    row,
                    errors,
                    raw_text=raw_text,
                    schema=schema,
                )
            errors["total_errors"] = sum(
                value for value in errors.values() if isinstance(value, int)
            )
            return errors

        # --------------------
        # General parsed JSON vs gold errors
        # --------------------
        dynamic_allowed = set(self.acceptable_fields)
        dynamic_allowed.update(collect_key_names(parsed_gold))
        if schema:
            dynamic_allowed.update(self._schema_key_names(schema))

        errors["repetition_count"] = self.detect_repetition(parsed_raw, parsed_gold)
        errors["hallucinated_fields_count"] = self.detect_hallucinated_fields(
            parsed_raw,
            parsed_gold,
            dynamic_allowed,
        )
        errors["missing_fields_count"] = self.detect_missing_fields(parsed_raw, parsed_gold)
        errors["wrong_nesting_count"] = self.detect_wrong_nesting(parsed_raw, parsed_gold)
        errors["wrong_nesting_depth_count"] = self.detect_wrong_nesting_depth(
            parsed_raw,
            parsed_gold,
        )
        errors["wrong_types_count"] = self.detect_wrong_types(parsed_raw, parsed_gold)
        errors["wrong_order_count"] = self.detect_wrong_order(parsed_raw, parsed_gold)
        errors["incorrect_values_count"] = self.detect_incorrect_values(parsed_raw, parsed_gold)
        errors["placeholder_values_count"] = self.detect_placeholder_values(
            parsed_raw,
            parsed_gold,
        )
        errors["longer_shorter_count"] = self.detect_longer_shorter(parsed_raw, parsed_gold)

        # --------------------
        # Dataset-specific routing
        # --------------------
        if "schema" in dataset or "schematojson" in dataset or "schema_to_json" in dataset:
            self.detect_schematojson(parsed_raw, parsed_gold, errors)
        elif "arqa" in dataset:
            self.detect_arqa(parsed_raw, parsed_gold, errors)
        elif "deepjson" in dataset:
            self.detect_deepjsoneval(
                parsed_raw,
                row,
                errors,
                raw_text=raw_text,
                schema=schema,
            )

        errors["total_errors"] = sum(
            errors.get(col, 0)
            for col in ALL_ERROR_COLUMNS
            if isinstance(errors.get(col, 0), int)
        )
        return errors

    # ========================================================
    # General detectors
    # ========================================================

    def detect_empty_field_values(self, parsed_raw: Any, parsed_gold: Any) -> int:
        """
        Count fields whose generated value is empty while the gold value at the
        same path is non-empty. Empty includes "", whitespace, null/None, "none",
        "nan", [], and {}.
        """
        if parsed_raw is None:
            return 0

        raw_paths = collect_paths(parsed_raw)
        gold_paths = collect_paths(parsed_gold)
        count = 0

        for path, raw_value in raw_paths.items():
            if path not in gold_paths:
                continue
            gold_value = gold_paths[path]
            if is_empty_json_value(raw_value) and not is_empty_json_value(gold_value):
                count += 1

        return count

    def detect_markdown_code_fence(self, raw_text: str) -> int:
        return len(re.findall(r"```(?:json|python)?", raw_text, flags=re.IGNORECASE))

    def detect_invalid_json_syntax(
        self,
        raw_text: str,
        candidate_json: str,
        parsed_raw: Any,
        has_complete_span: bool,
    ) -> int:
        if not raw_text.strip():
            return 1

        count = 0

        # Nonempty response with no complete JSON object or array.
        if not has_complete_span:
            count += 1

        # Complete candidate exists but cannot be parsed: base error.
        if has_complete_span and parsed_raw is None:
            count += 1

        if not candidate_json:
            return count

        # Unbalanced structural braces and brackets, ignoring any that occur
        # inside quoted JSON strings.
        open_braces, close_braces, open_brackets, close_brackets = (
            count_json_structure_chars(candidate_json)
        )
        count += abs(open_braces - close_braces)
        count += abs(open_brackets - close_brackets)

        # Field names without double quotes.
        unquoted_field_pattern = r'(?m)(?:^|[{,]\s*)([A-Za-z_][A-Za-z0-9_\- ]*)\s*:'
        count += len(re.findall(unquoted_field_pattern, candidate_json))

        # Quoted field name not followed by a colon.
        missing_colon_pattern = r'(?m)(?:^|[{,]\s*)"[^"\n]+"\s+(?=["{\[\d\-tfn])'
        count += len(re.findall(missing_colon_pattern, candidate_json))

        # Trailing comma immediately before } or ].
        if re.search(r",\s*[}\]]", candidate_json):
            count += 1

        return count

    def detect_truncated(self, raw_text: str, output_tokens: Any) -> int:
        token_limit_hit = False
        try:
            token_limit_hit = (
                output_tokens is not None
                and int(output_tokens) >= self.token_limit
            )
        except Exception:
            token_limit_hit = False

        cleaned = strip_code_fences(raw_text)
        open_braces, close_braces, open_brackets, close_brackets = (
            count_json_structure_chars(cleaned)
        )
        has_unclosed_brace = open_braces > close_braces
        has_unclosed_bracket = open_brackets > close_brackets

        return 1 if token_limit_hit or has_unclosed_brace or has_unclosed_bracket else 0

    def detect_backslash_issues(self, raw_text: str, candidate_json: str, gold_raw: Any) -> int:
        text = candidate_json or raw_text
        if not text:
            return 0
        count = len(re.findall(r'\\(?!["\\/bfnrtu])', text))
        gold_text = (
            json.dumps(gold_raw, ensure_ascii=False)
            if not isinstance(gold_raw, str)
            else gold_raw
        )
        diff = abs(text.count("\\") - gold_text.count("\\"))
        if diff > 2:
            count += diff
        return count

    def detect_python_code_wrapping(self, raw_text: str) -> int:
        patterns = [
            r"\bimport\s+\w+",
            r"\bdef\s+\w+\s*\(",
            r"\bprint\s*\(",
            r"\breturn\s+",
            r"json\.dumps",
            r"json\.loads",
        ]
        return sum(1 for pattern in patterns if re.search(pattern, raw_text))

    def detect_explanatory_text(
        self,
        raw_text: str,
        before_json: str,
        after_json: str,
        parsed_raw: Any,
    ) -> int:
        count = 0
        if before_json:
            count += 1
        if after_json:
            count += 1
        if parsed_raw is None and re.search(
            r"\b(here|sure|answer|explanation|json|the output)\b",
            raw_text,
            flags=re.I,
        ):
            count += 1
        return count

    def detect_hallucinated_fields(
        self,
        parsed_raw: Any,
        parsed_gold: Any,
        allowed_fields: Set[str],
    ) -> int:
        raw_keys = set(collect_key_names(parsed_raw))
        gold_keys = set(collect_key_names(parsed_gold))
        return len(raw_keys - gold_keys - allowed_fields)

    def detect_missing_fields(self, parsed_raw: Any, parsed_gold: Any) -> int:
        if parsed_gold in ({}, [], "", None):
            return 0
        gold_scalar_paths = set(collect_scalar_paths(parsed_gold).keys())
        if parsed_raw is None:
            return len(gold_scalar_paths)
        raw_scalar_paths = set(collect_scalar_paths(parsed_raw).keys())
        return len(gold_scalar_paths - raw_scalar_paths)

    def detect_wrong_nesting(self, parsed_raw: Any, parsed_gold: Any) -> int:
        raw_paths = collect_container_paths(parsed_raw)
        gold_paths = collect_container_paths(parsed_gold)
        count = 0
        for path, gold_kind in gold_paths.items():
            if path in raw_paths and raw_paths[path] != gold_kind:
                count += 1
        return count

    def detect_wrong_nesting_depth(self, parsed_raw: Any, parsed_gold: Any) -> int:
        return abs(max_json_depth(parsed_raw) - max_json_depth(parsed_gold))

    def detect_wrong_types(self, parsed_raw: Any, parsed_gold: Any) -> int:
        raw_all = collect_paths(parsed_raw)
        gold_all = collect_paths(parsed_gold)
        count = 0
        for path, gold_val in gold_all.items():
            if path not in raw_all:
                continue
            raw_val = raw_all[path]
            if not same_jsonish_type(raw_val, gold_val):
                count += 1
        return count

    def detect_wrong_order(self, parsed_raw: Any, parsed_gold: Any) -> int:
        count = 0

        def walk(raw_obj: Any, gold_obj: Any) -> None:
            nonlocal count
            if isinstance(raw_obj, dict) and isinstance(gold_obj, dict):
                raw_keys = list(raw_obj.keys())
                gold_keys = list(gold_obj.keys())
                if set(raw_keys) == set(gold_keys) and raw_keys != gold_keys:
                    count += 1
                for key in set(raw_keys) & set(gold_keys):
                    walk(raw_obj[key], gold_obj[key])
            elif isinstance(raw_obj, list) and isinstance(gold_obj, list):
                for r_item, g_item in zip(raw_obj, gold_obj):
                    walk(r_item, g_item)

        walk(parsed_raw, parsed_gold)
        return count

    def detect_incorrect_values(self, parsed_raw: Any, parsed_gold: Any) -> int:
        raw_flat = collect_scalar_paths(parsed_raw)
        gold_flat = collect_scalar_paths(parsed_gold)
        count = 0
        for path, gold_val in gold_flat.items():
            if path not in raw_flat:
                continue
            raw_val = raw_flat[path]
            if same_jsonish_type(raw_val, gold_val) and raw_val != gold_val:
                count += 1
        return count

    def detect_placeholder_values(self, parsed_raw: Any, parsed_gold: Any) -> int:
        raw_flat = collect_scalar_paths(parsed_raw)
        gold_flat = collect_scalar_paths(parsed_gold)
        count = 0
        for path, raw_val in raw_flat.items():
            gold_val = gold_flat.get(path)
            if isinstance(raw_val, str):
                raw_norm = raw_val.strip().lower()
                gold_norm = (
                    gold_val.strip().lower()
                    if isinstance(gold_val, str)
                    else str(gold_val).lower()
                )
                if raw_norm in PLACEHOLDER_STRINGS and raw_norm != gold_norm:
                    count += 1
            if raw_val == 0 and gold_val != 0:
                count += 1
        return count

    def detect_longer_shorter(self, parsed_raw: Any, parsed_gold: Any) -> int:
        gold_words = max(1, json_word_count(parsed_gold))
        raw_words = json_word_count(parsed_raw)
        ratio = raw_words / gold_words
        return 1 if ratio >= 1.5 or ratio <= 0.5 else 0

    def detect_different_language(self, raw_text: str) -> int:
        return 1 if re.search(r"[\u4e00-\u9fff]", raw_text) else 0

    def detect_repetition(self, parsed_raw: Any, parsed_gold: Any) -> int:
        raw_values = [normalize_scalar(v) for v in walk_values(parsed_raw)]
        gold_values = [normalize_scalar(v) for v in walk_values(parsed_gold)]
        raw_counts = Counter(raw_values)
        gold_counts = Counter(gold_values)
        count = 0
        for value, raw_count in raw_counts.items():
            if len(value) < 2:
                continue
            allowed = gold_counts.get(value, 1)
            if raw_count > allowed:
                count += raw_count - allowed
        return count

    # --------------------------------------------------------
    # 1. SchemaToJSON Specifics
    # --------------------------------------------------------
    def detect_schematojson(self, raw: Any, gold: Any, errors: Dict[str, Any]) -> None:
        if not isinstance(raw, dict):
            errors["schematojson_wrong_root_structure"] += 1
        else:
            if "cell_index" not in raw or "cell_record" not in raw:
                errors["schematojson_wrong_root_structure"] += 1
            else:
                if (
                    not isinstance(raw.get("cell_index"), list)
                    or not isinstance(raw.get("cell_record"), list)
                ):
                    errors["schematojson_wrong_root_structure"] += 1
                elif len(raw.get("cell_index", [])) != len(raw.get("cell_record", [])):
                    errors["schematojson_wrong_root_structure"] += 1

        if isinstance(raw, dict) and "cell_record" in raw:
            raw_cell_record = raw["cell_record"]
            if isinstance(raw_cell_record, list):
                for item in raw_cell_record:
                    if isinstance(item, (dict, list)):
                        errors["schematojson_arrays_instead_of_strings"] += 1
            elif isinstance(raw_cell_record, (dict, list)):
                errors["schematojson_arrays_instead_of_strings"] += 1

        raw_records = get_schematojson_records(raw)
        gold_records = get_schematojson_records(gold)

        for i, record in enumerate(raw_records):
            if not isinstance(record, dict):
                continue

            gold_record = (
                gold_records[i]
                if i < len(gold_records) and isinstance(gold_records[i], dict)
                else {}
            )

            r_val = record.get("value")
            g_val = gold_record.get("value")
            if r_val != g_val and (r_val is not None or g_val is not None):
                errors["schematojson_cell_value_errors"] += 1

            rtype = record.get("type")
            if rtype is not None and rtype not in SCHEMATOJSON_ALLOWED_TYPES:
                errors["schematojson_hallucinated_type"] += 1

            has_const = "constituent" in record
            has_mat = "material" in record
            has_unit = "unit" in record
            if rtype == "Other" and (has_const or has_mat or has_unit):
                errors["schematojson_fields_not_allowed"] += 1
            elif rtype == "Glass_Compound_Amount":
                missing = [
                    field
                    for field in ["constituent", "material", "unit"]
                    if field not in record
                ]
                errors["schematojson_missing_conditional_fields"] += len(missing)

        # Compare constituent values by occurrence order across the complete JSON:
        # first generated constituent to first gold constituent, second to second, etc.
        raw_constituents = collect_named_field_values(raw, "constituent")
        gold_constituents = collect_named_field_values(gold, "constituent")
        for index in range(max(len(raw_constituents), len(gold_constituents))):
            raw_value = raw_constituents[index] if index < len(raw_constituents) else None
            gold_value = gold_constituents[index] if index < len(gold_constituents) else None
            if raw_value != gold_value:
                errors["schematojson_wrong_constituent"] += 1

    # --------------------------------------------------------
    # 2. ARQA Specifics
    # --------------------------------------------------------
    def detect_arqa(self, raw: Any, gold: Any, errors: Dict[str, Any]) -> None:
        if not isinstance(raw, dict):
            errors["arqa_missing_top_level_fields"] += 2
            return

        for req in ["answer", "claims"]:
            if req not in raw:
                errors["arqa_missing_top_level_fields"] += 1
        if "claims" in raw and not raw.get("claims"):
            errors["arqa_missing_top_level_fields"] += 1

        raw_claims = (
            raw.get("claims", [])
            if isinstance(raw.get("claims", []), list)
            else []
        )
        gold_claims = (
            gold.get("claims", [])
            if isinstance(gold, dict) and isinstance(gold.get("claims", []), list)
            else []
        )

        gold_claim_texts = [
            normalize_text(c.get("claim_text", ""))
            for c in gold_claims
            if isinstance(c, dict)
        ]
        gold_claim_tokens = [token_set(t) for t in gold_claim_texts]
        gold_table_ids = collect_arqa_table_ids(gold_claims)
        gold_para_ids = collect_arqa_para_ids(gold_claims)

        for i, r_claim in enumerate(raw_claims):
            if not isinstance(r_claim, dict):
                continue

            raw_claim_text = normalize_text(r_claim.get("claim_text", ""))
            raw_tokens = token_set(raw_claim_text)
            if i >= len(gold_claims):
                errors["arqa_hallucinated_claims"] += 1
            elif raw_claim_text and gold_claim_tokens:
                best = max(
                    jaccard(raw_tokens, g_tokens)
                    for g_tokens in gold_claim_tokens
                )
                if best < 0.30 and raw_claim_text not in gold_claim_texts:
                    errors["arqa_hallucinated_claims"] += 1

            # Claim type is read directly from each object in raw["claims"].
            ctype = r_claim.get("type")
            if ctype not in ARQA_ALLOWED_CLAIM_TYPES:
                errors["arqa_hallucinated_claim_type"] += 1
            elif i < len(gold_claims) and isinstance(gold_claims[i], dict):
                gold_type = gold_claims[i].get("type")
                if ctype != gold_type:
                    errors["arqa_wrong_claim_type"] += 1

            evidence = r_claim.get("evidence", {})
            table_cells = extract_table_cells_from_evidence(evidence)
            text_spans = extract_text_spans_from_evidence(evidence)

            for cell in table_cells:
                table_id = str(cell.get("table_id", ""))
                if not ARQA_ID_PATTERN.fullmatch(table_id):
                    errors["arqa_hallucinated_table_id"] += 1
                elif gold_table_ids and table_id not in gold_table_ids:
                    errors["arqa_hallucinated_table_id"] += 1

                if "cell_text" not in cell or cell.get("cell_text") in [None, ""]:
                    errors["arqa_missing_cell_text"] += 1

            for span in text_spans:
                para_id = str(span.get("para_id", ""))
                if not ARQA_ID_PATTERN.fullmatch(para_id):
                    errors["arqa_hallucinated_para_id"] += 1
                elif gold_para_ids and para_id not in gold_para_ids:
                    errors["arqa_hallucinated_para_id"] += 1

                char_start = span.get("char_start")
                char_end = span.get("char_end")

                invalid_span = (
                    char_start is None
                    or char_end is None
                    or isinstance(char_start, bool)
                    or isinstance(char_end, bool)
                    or not isinstance(char_start, (int, float))
                    or not isinstance(char_end, (int, float))
                    or char_start < 0
                    or char_end < 0
                    or (char_start == 0 and char_end == 0)
                    or char_end <= char_start
                )
                if invalid_span:
                    errors["arqa_empty_evidence_span"] += 1

    # --------------------------------------------------------
    # 3. DeepJSONEval Specifics
    # --------------------------------------------------------
    def detect_deepjsoneval(
        self,
        raw: Any,
        row: Dict[str, Any],
        errors: Dict[str, Any],
        raw_text: str = "",
        schema: Optional[Dict[str, Any]] = None,
    ) -> None:
        schema = schema or self._find_schema(row)

        schema_words = {"title", "properties", "required", "description", "enum", "items"}
        if isinstance(raw, dict):
            raw_keys = set(collect_key_names(raw))
            if "properties" in raw_keys or len(schema_words & raw_keys) >= 2:
                errors["deepjson_schema_echo"] += 1
        elif raw_text:
            if (
                re.search(r'"properties"\s*:', raw_text)
                and re.search(r'"required"\s*:', raw_text)
            ):
                errors["deepjson_schema_echo"] += 1

        if not schema or not isinstance(schema, dict) or not isinstance(raw, dict):
            return

        validation = self._validate_against_schema(raw, schema)
        errors["deepjson_enum_check"] += validation["enum"]
        errors["deepjson_missing_required_fields"] += validation["required"]
        errors["deepjson_property_type_check"] += validation["type"]
        errors["deepjson_property_count_mismatch"] += validation["property_count"]

    def _find_schema(self, row: Dict[str, Any]) -> Optional[Any]:
        for field in ["schema", "json_schema", "input_schema"]:
            val = row.get(field)
            if isinstance(val, (dict, bool)):
                return val
            if isinstance(val, str):
                parsed = parse_json_safely(val)
                if isinstance(parsed, (dict, bool)):
                    return parsed

        prompt = str(row.get("prompt", ""))
        for match in re.finditer(r"\{", prompt):
            try:
                obj, _ = json.JSONDecoder().raw_decode(prompt[match.start():])
                if isinstance(obj, dict) and "properties" in obj:
                    return obj
            except Exception:
                continue
        return None

    def _schema_key_names(self, schema: Dict[str, Any]) -> Set[str]:
        names: Set[str] = set()

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                props = node.get("properties")
                if isinstance(props, dict):
                    names.update(str(k) for k in props.keys())
                    for sub in props.values():
                        walk(sub)
                items = node.get("items")
                if isinstance(items, dict):
                    walk(items)
                for key in ("anyOf", "oneOf", "allOf"):
                    options = node.get(key)
                    if isinstance(options, list):
                        for option in options:
                            walk(option)

        walk(schema)
        return names

    def _resolve_ref(
        self,
        schema_root: Dict[str, Any],
        ref: str,
    ) -> Optional[Dict[str, Any]]:
        if not ref.startswith("#/"):
            return None

        node: Any = schema_root
        for part in ref[2:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]

        return node if isinstance(node, dict) else None

    def _type_matches_schema(self, value: Any, expected_type: Any) -> bool:
        if isinstance(expected_type, list):
            return any(self._type_matches_schema(value, t) for t in expected_type)
        if expected_type == "string":
            return isinstance(value, str)
        if expected_type == "number":
            return (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
            )
        if expected_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected_type == "boolean":
            return isinstance(value, bool)
        if expected_type == "array":
            return isinstance(value, list)
        if expected_type == "object":
            return isinstance(value, dict)
        if expected_type == "null":
            return value is None
        return True

    def _schema_branch_valid(
        self,
        value: Any,
        node: Dict[str, Any],
        schema_root: Dict[str, Any],
    ) -> bool:
        return sum(self._validate_node(value, node, schema_root).values()) == 0

    def _validate_node(
        self,
        value: Any,
        node: Any,
        schema_root: Dict[str, Any],
    ) -> Dict[str, int]:
        counts = {"enum": 0, "required": 0, "type": 0, "property_count": 0}

        if not isinstance(node, dict):
            return counts

        if "$ref" in node:
            resolved = self._resolve_ref(schema_root, str(node["$ref"]))
            if resolved is not None:
                return self._validate_node(value, resolved, schema_root)

        any_of = node.get("anyOf")
        if isinstance(any_of, list) and any_of:
            if not any(
                isinstance(branch, dict)
                and self._schema_branch_valid(value, branch, schema_root)
                for branch in any_of
            ):
                counts["type"] += 1
            return counts

        one_of = node.get("oneOf")
        if isinstance(one_of, list) and one_of:
            valid_count = sum(
                1
                for branch in one_of
                if isinstance(branch, dict)
                and self._schema_branch_valid(value, branch, schema_root)
            )
            if valid_count != 1:
                counts["type"] += 1
            return counts

        all_of = node.get("allOf")
        if isinstance(all_of, list):
            for branch in all_of:
                branch_counts = self._validate_node(value, branch, schema_root)
                for key in counts:
                    counts[key] += branch_counts[key]

        expected_type = node.get("type")
        if (
            expected_type is not None
            and not self._type_matches_schema(value, expected_type)
        ):
            counts["type"] += 1
            return counts

        if "enum" in node:
            allowed = node.get("enum", [])
            if value not in allowed:
                counts["enum"] += 1

        if isinstance(value, dict):
            properties = node.get("properties", {})
            required = node.get("required", [])
            required_set = set(required) if isinstance(required, list) else set()

            if isinstance(properties, dict):
                actual_known = set(value.keys()) & set(properties.keys())

                # Optional fields may be omitted. Count mismatch only when:
                #   - a required property is absent, or
                #   - extra properties are present while additionalProperties is false.
                missing_required = required_set - set(value.keys())
                counts["required"] += len(missing_required)

                extra_fields = set(value.keys()) - set(properties.keys())
                if node.get("additionalProperties") is False and extra_fields:
                    counts["property_count"] += len(extra_fields)

                min_properties = node.get("minProperties")
                max_properties = node.get("maxProperties")
                if isinstance(min_properties, int) and len(value) < min_properties:
                    counts["property_count"] += 1
                if isinstance(max_properties, int) and len(value) > max_properties:
                    counts["property_count"] += 1

                for field in actual_known:
                    counts_for_field = self._validate_node(
                        value[field],
                        properties[field],
                        schema_root,
                    )
                    for key in counts:
                        counts[key] += counts_for_field[key]

        elif isinstance(value, list):
            items = node.get("items")
            if isinstance(items, dict):
                for item in value:
                    item_counts = self._validate_node(item, items, schema_root)
                    for key in counts:
                        counts[key] += item_counts[key]

        return counts

    def _validate_against_schema(
        self,
        data: Any,
        schema: Dict[str, Any],
    ) -> Dict[str, int]:
        """
        Recursive DeepJSONEval schema checks supporting:
        enum, required fields, primitive/container types, anyOf, oneOf,
        allOf, and local JSON Pointer $ref values.
        """
        return self._validate_node(data, schema, schema)


# ============================================================
# MAIN / FILE IO
# ============================================================

def load_json_or_jsonl(path: Path) -> List[Dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else [data]
    except Exception:
        pass

    rows = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            print(f"Skipping invalid JSONL line {line_no} in {path}: {exc}")
    return rows


def save_error_csv(rows: List[Dict[str, Any]], output_csv: Path) -> None:
    base_columns = [
        "row_id", "dataset", "model", "method", "total_errors",
    ]
    columns = list(dict.fromkeys(base_columns + ALL_ERROR_COLUMNS + [key for row in rows for key in row]))
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col) for col in columns})


def load_manifest(run_dir: Path) -> Dict[str, Any]:
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def analyze_rows(
    rows: List[Dict[str, Any]],
    run_info: Dict[str, Any],
    detector: GeneralErrorDetector,
) -> List[Dict[str, Any]]:
    analyzed = []
    for i, row in enumerate(rows):
        errs = detector.detect(row, run_info)
        out = {
            "run_id": row.get("run_id", run_info.get("run_id")),
            "row_id": row.get("row_id", row.get("id", i)),
            "dataset": row.get("dataset", run_info.get("dataset", "Unknown")),
            "model": row.get("model", run_info.get("model", "Unknown")),
            "method": row.get("method", run_info.get("method", "Unknown")),
        }
        out.update(errs)
        analyzed.append(out)
    return analyzed


def process_outputs_dir(input_path: Path, detector: GeneralErrorDetector,
                        output_path: Path = Path('reports/eacl_revision/detector')) -> None:
    if output_path.resolve() == input_path.resolve() or input_path.resolve() in output_path.resolve().parents:
        raise ValueError('Detector output must be outside the archived input directory')
    run_dirs = sorted([p for p in input_path.iterdir() if p.is_dir()])
    all_analyzed: List[Dict[str, Any]] = []

    for run_dir in run_dirs:
        if run_dir.name.lower() == 'sample' or not (run_dir / 'manifest.json').exists():
            continue
        resp_path = run_dir / "responses.jsonl"
        if not resp_path.exists():
            continue

        run_info = load_manifest(run_dir)
        rows = load_json_or_jsonl(resp_path)
        analyzed = analyze_rows(rows, run_info, detector)
        save_error_csv(analyzed, output_path / run_dir.name / "full_error_analysis.csv")
        all_analyzed.extend(analyzed)
        print(f"Processed {run_dir.name}: {len(analyzed)} rows")

    save_error_csv(
        all_analyzed,
        output_path / "combined_full_error_analysis.csv",
    )
    print(f"Done! Combined rows: {len(all_analyzed)}")


def process_single_file(
    input_path: Path,
    detector: GeneralErrorDetector,
    output: Optional[str] = None,
) -> None:
    rows = load_json_or_jsonl(input_path)
    analyzed = analyze_rows(rows, {}, detector)
    output_csv = (
        Path(output)
        if output
        else input_path.with_name(
            input_path.stem + "_full_error_analysis.csv"
        )
    )
    save_error_csv(analyzed, output_csv)
    print(f"Done! Analyzed {len(analyzed)} rows")
    print(f"Saved: {output_csv}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="pipeline/outputs",
        help="Path to outputs dir or jsonl/json file.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV for single-file mode, or output directory for archive mode.",
    )
    parser.add_argument(
        "--token-limit",
        type=int,
        default=4096,
        help="Token limit used for truncation detection.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input path not found: {input_path}")
        print(f"Current working directory: {Path.cwd()}")
        print(
            "Try ../pipeline/outputs or ../outputs "
            "if you are running from a scripts folder."
        )
        return

    detector = GeneralErrorDetector(token_limit=args.token_limit)

    if input_path.is_dir():
        process_outputs_dir(input_path, detector, Path(args.output) if args.output else Path('reports/eacl_revision/detector'))
    else:
        process_single_file(input_path, detector, output=args.output)


if __name__ == "__main__":
    main()
