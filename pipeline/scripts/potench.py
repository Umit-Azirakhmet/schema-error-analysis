#!/usr/bin/env python3
"""
general_error_detector.py

Detects the General List of Errors in model outputs and saves CSV summaries.

Works on:
1. A single JSONL file
2. A single JSON list file
3. An outputs/ directory containing run folders with:
   - manifest.json
   - responses.jsonl

Example:
    python general_error_detector.py
"""

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# ERROR COLUMNS
# ============================================================

GENERAL_ERROR_COLUMNS = [
    "truncated_count",
    "repetition_count",
    "trailing_commas_count",
    "unescaped_quotes_count",
    "markdown_code_fence_count",
    "python_code_wrapping_count",
    "hallucinated_fields_count",
    "wrong_field_names_count",
    "few_shot_contamination_count",
    "missing_fields_count",
    "different_language_count",
    "empty_response_count",
    "placeholder_values_count",
    "backslash_issues_count",
    "wrong_nesting_count",
    "wrong_types_count",
    "longer_shorter_count",
    "wrong_order_count",
    "explanatory_text_count",
    "incorrect_values_count",
    "invalid_json_syntax_count",
]


ERROR_FAMILIES = {
    "formatting_errors": [
        "truncated_count",
        "trailing_commas_count",
        "unescaped_quotes_count",
        "markdown_code_fence_count",
        "python_code_wrapping_count",
        "different_language_count",
        "empty_response_count",
        "backslash_issues_count",
        "explanatory_text_count",
        "invalid_json_syntax_count",
    ],
    "schema_structure_errors": [
        "hallucinated_fields_count",
        "wrong_field_names_count",
        "missing_fields_count",
        "wrong_nesting_count",
        "wrong_types_count",
        "wrong_order_count",
    ],
    "content_value_errors": [
        "incorrect_values_count",
        "placeholder_values_count",
        "longer_shorter_count",
    ],
    "output_behavior_errors": [
        "repetition_count",
        "few_shot_contamination_count",
    ],
}


# ============================================================
# FIELD LISTS
# ============================================================

GENERAL_ACCEPTABLE_FIELDS = {
    # ARQA
    "answer", "claims", "type", "claim_text", "evidence",
    "table_cells", "text_spans", "table_id", "row", "col",
    "cell_text", "para_id", "char_start", "char_end", "text",

    # SchemaToJSON
    "cell_index", "cell_record", "value", "constituent",
    "unit", "material",

    # DeepJSONEval common/schema-like names
    "Year", "IsSequel", "Ratings", "Crew",
    "GameInfo", "GameStatistics", "DLCs",
    "PersonalInfo", "MedicalHistory",
    "BasicInfo", "TechnicalSpecs", "Features",
}


PLACEHOLDER_STRINGS = {
    "unknown", "n/a", "na", "none", "null", "xx", ""
}


FEW_SHOT_MARKERS = {
    # Add more if your examples have obvious repeated terms.
    "Crew",
}


# ============================================================
# JSON EXTRACTION / PARSING
# ============================================================

def strip_code_fences(text: str) -> str:
    """Removes outer markdown fences for parsing, but detection still happens separately."""
    text = text.strip()
    text = re.sub(r"^\s*```(?:json|python)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def find_json_span(text: str) -> Optional[Tuple[int, int]]:
    """
    Finds the first complete JSON object/array span in text.

    This scans brackets while respecting quoted strings.
    It does not guarantee validity, but it finds a likely JSON region.
    """
    for start, ch in enumerate(text):
        if ch not in "{[":
            continue

        stack = []
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


def extract_json_candidate(raw_response: str) -> Tuple[str, str, str]:
    """
    Returns:
        candidate_json_text, text_before_json, text_after_json
    """ 
    no_fence = strip_code_fences(raw_response)
    span = find_json_span(no_fence)

    if not span:
        return "", no_fence.strip(), ""

    start, end = span
    before = no_fence[:start].strip()
    candidate = no_fence[start:end].strip()
    after = no_fence[end:].strip()

    return candidate, before, after


def parse_json_safely(text: Any) -> Optional[Any]:
    """Parses JSON if possible."""
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


# ============================================================
# JSON WALKING HELPERS
# ============================================================

def collect_key_names(obj: Any) -> List[str]:
    """Collects every dictionary key name anywhere in a JSON object."""
    keys = []

    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.append(str(k))
            keys.extend(collect_key_names(v))

    elif isinstance(obj, list):
        for item in obj:
            keys.extend(collect_key_names(item))

    return keys


def collect_paths(obj: Any, path: str = "") -> Dict[str, Any]:
    """
    Flattens JSON into path -> value.

    Example:
        {"a": {"b": 1}} becomes {"a.b": 1}
    """
    out = {}

    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else str(k)
            out.update(collect_paths(v, new_path))

    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_path = f"{path}[{i}]"
            out.update(collect_paths(v, new_path))

    else:
        out[path] = obj

    return out


def collect_container_paths(obj: Any, path: str = "") -> Dict[str, str]:
    """
    Collects paths and whether each path is object/list/scalar.
    Used for wrong nesting.
    """
    out = {}

    if isinstance(obj, dict):
        out[path or "$"] = "object"
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else str(k)
            out.update(collect_container_paths(v, new_path))

    elif isinstance(obj, list):
        out[path or "$"] = "array"
        for i, v in enumerate(obj):
            new_path = f"{path}[{i}]"
            out.update(collect_container_paths(v, new_path))

    else:
        out[path or "$"] = "scalar"

    return out


def normalize_scalar(value: Any) -> str:
    """Normalizes scalar values for repetition counting."""
    if isinstance(value, str):
        return value.strip().lower()
    return str(value).strip().lower()


def json_word_count(obj: Any) -> int:
    """Counts approximate words in a JSON object."""
    text = json.dumps(obj, ensure_ascii=False)
    return len(re.findall(r"\w+", text))


def same_scalar_type(a: Any, b: Any) -> bool:
    """Checks whether two scalar values have the same JSON-ish type."""
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return True
    return type(a) is type(b)


# ============================================================
# ERROR DETECTOR
# ============================================================

class GeneralErrorDetector:
    """
    Detects the General List of Errors.

    Main idea:
    - Some errors are detected from raw text before parsing.
    - Some errors require parsed JSON.
    - Some errors compare parsed raw JSON against gold JSON.
    """

    def __init__(self, token_limit: int = 4096, acceptable_fields: Optional[set] = None):
        self.token_limit = token_limit
        self.acceptable_fields = acceptable_fields or GENERAL_ACCEPTABLE_FIELDS

    def detect(self, row: Dict[str, Any], run_info: Optional[Dict[str, Any]] = None) -> Dict[str, int]:
        """Runs all general error detectors on one response row."""
        run_info = run_info or {}

        raw_response = row.get("raw_response", "")
        gold_raw = row.get("gold_json_raw", "{}")

        output_tokens = row.get("output_tokens")
        if output_tokens is None:
            output_tokens = row.get("completion_tokens")
        if output_tokens is None:
            output_tokens = run_info.get("output_tokens")

        if raw_response is None:
            raw_response = ""

        raw_text = str(raw_response)
        candidate_json, before_json, after_json = extract_json_candidate(raw_text)

        parsed_raw = parse_json_safely(candidate_json)
        parsed_gold = parse_json_safely(gold_raw)

        if parsed_gold is None:
            parsed_gold = {}

        errors = {col: 0 for col in GENERAL_ERROR_COLUMNS}

        # --------------------------
        # raw-text / formatting checks
        # --------------------------
        errors["empty_response_count"] = self.detect_empty_response(raw_text, parsed_gold)
        errors["markdown_code_fence_count"] = self.detect_markdown_code_fence(raw_text)
        errors["python_code_wrapping_count"] = self.detect_python_code(raw_text)
        errors["different_language_count"] = self.detect_different_language(raw_text)
        errors["trailing_commas_count"] = self.detect_trailing_commas(candidate_json or raw_text)
        errors["backslash_issues_count"] = self.detect_backslash_issues(candidate_json or raw_text)
        errors["truncated_count"] = self.detect_truncated(raw_text, output_tokens, candidate_json)
        errors["explanatory_text_count"] = self.detect_explanatory_text(before_json, after_json)
        errors["invalid_json_syntax_count"] = self.detect_invalid_json_syntax(candidate_json, parsed_raw, raw_text)
        errors["unescaped_quotes_count"] = self.detect_unescaped_quotes(candidate_json, parsed_raw)
        errors["few_shot_contamination_count"] = self.detect_few_shot_contamination(raw_text, parsed_gold, row)

        # If no parsed raw JSON, comparison-based checks cannot run.
        if parsed_raw is None:
            # Still count expected missing top-level fields when gold exists.
            errors["missing_fields_count"] = self.detect_missing_fields(None, parsed_gold)
            self.add_family_counts(errors)
            return errors

        # --------------------------
        # parsed JSON vs gold checks
        # --------------------------
        errors["hallucinated_fields_count"] = self.detect_hallucinated_fields(parsed_raw, parsed_gold)
        errors["wrong_field_names_count"] = self.detect_wrong_field_names(parsed_raw)
        errors["missing_fields_count"] = self.detect_missing_fields(parsed_raw, parsed_gold)
        errors["placeholder_values_count"] = self.detect_placeholder_values(parsed_raw, parsed_gold)
        errors["wrong_nesting_count"] = self.detect_wrong_nesting(parsed_raw, parsed_gold)
        errors["wrong_types_count"] = self.detect_wrong_types(parsed_raw, parsed_gold)
        errors["longer_shorter_count"] = self.detect_longer_shorter(parsed_raw, parsed_gold)
        errors["wrong_order_count"] = self.detect_wrong_order(parsed_raw, parsed_gold)
        errors["incorrect_values_count"] = self.detect_incorrect_values(parsed_raw, parsed_gold)
        errors["repetition_count"] = self.detect_repetition(parsed_raw, parsed_gold)

        self.add_family_counts(errors)
        return errors

    # ========================================================
    # Individual detectors
    # ========================================================

    def detect_empty_response(self, raw_text: str, parsed_gold: Any) -> int:
        """Detects empty raw responses, unless gold is also empty."""
        cleaned = raw_text.strip().lower()

        empty_like = {"", '""', "null", "none", "nan", "[]", "{}"}

        if cleaned in empty_like:
            if parsed_gold not in ({}, [], "", None):
                return 1
            return 0

        return 0

    def detect_markdown_code_fence(self, raw_text: str) -> int:
        """Detects markdown fences like ```json or ```python."""
        return len(re.findall(r"```(?:json|python)?", raw_text, flags=re.IGNORECASE))

    def detect_python_code(self, raw_text: str) -> int:
        """Detects cases where model outputs Python code instead of JSON."""
        patterns = [
            r"\bimport\s+\w+",
            r"\bdef\s+\w+\s*\(",
            r"\bprint\s*\(",
            r"\breturn\s+",
            r"json\.dumps",
        ]

        return sum(1 for p in patterns if re.search(p, raw_text))

    def detect_different_language(self, raw_text: str) -> int:
        """Detects Chinese characters as a non-English output signal."""
        return 1 if re.search(r"[\u4e00-\u9fff]", raw_text) else 0

    def detect_trailing_commas(self, text: str) -> int:
        """Detects trailing commas before } or ]."""
        return len(re.findall(r",\s*[}\]]", text))

    def detect_backslash_issues(self, text: str) -> int:
        """Detects invalid JSON escape sequences."""
        if not text:
            return 0

        # Valid JSON escapes are: \" \\ \/ \b \f \n \r \t \uXXXX
        invalid_escapes = re.findall(r'\\(?!["\\/bfnrtu])', text)
        return len(invalid_escapes)

    def detect_truncated(self, raw_text: str, output_tokens: Any, candidate_json: str) -> int:
        """
        Detects likely truncation:
        - output hit token limit
        - raw output does not end with } or ]
        - extracted JSON candidate exists but is not balanced/closed
        """
        count = 0
        cleaned = strip_code_fences(raw_text).strip()

        try:
            if output_tokens is not None and int(output_tokens) >= self.token_limit:
                count += 1
        except Exception:
            pass

        if cleaned and cleaned[-1] not in {"}", "]"}:
            count += 1

        # If there is an opener but no candidate JSON span, likely cut off.
        if not candidate_json and re.search(r"[\{\[]", cleaned):
            count += 1

        return count

    def detect_explanatory_text(self, before_json: str, after_json: str) -> int:
        """Detects natural language before or after JSON."""
        count = 0

        if before_json:
            count += 1
        if after_json:
            count += 1

        return count

    def detect_invalid_json_syntax(self, candidate_json: str, parsed_raw: Any, raw_text: str) -> int:
        """Detects JSON parse failure."""
        if not raw_text.strip():
            return 1

        if not candidate_json:
            return 1

        if parsed_raw is None:
            return 1

        return 0

    def detect_unescaped_quotes(self, candidate_json: str, parsed_raw: Any) -> int:
        """
        Detects likely unescaped quotes.

        Best practical rule:
        If parsing failed and parser often says this when quotes are unescaped,
        flag patterns like: "field": "text "bad" text"
        """
        if not candidate_json or parsed_raw is not None:
            return 0

        suspicious = re.search(r':\s*"[^"\n]*"[^,\}\]\n]+["]', candidate_json)
        return 1 if suspicious else 0

    def detect_few_shot_contamination(self, raw_text: str, parsed_gold: Any, row: Dict[str, Any]) -> int:
        """
        Detects obvious few-shot contamination.

        This is hard to do perfectly, so this script uses:
        - manual marker list, like Crew
        - optional row fields: few_shot_markers, few_shot_examples, examples
        """
        gold_text = json.dumps(parsed_gold, ensure_ascii=False).lower()
        raw_lower = raw_text.lower()

        markers = set(FEW_SHOT_MARKERS)

        optional_markers = row.get("few_shot_markers", [])
        if isinstance(optional_markers, list):
            markers.update(str(x) for x in optional_markers)

        # If examples are stored in the row, collect longer strings from them.
        for field in ["few_shot_examples", "examples", "demonstrations"]:
            val = row.get(field)
            if val:
                example_text = json.dumps(val, ensure_ascii=False)
                strings = re.findall(r'"([^"]{4,80})"', example_text)
                markers.update(strings)

        count = 0
        for marker in markers:
            marker_l = str(marker).lower().strip()
            if len(marker_l) < 4:
                continue
            if marker_l in raw_lower and marker_l not in gold_text:
                count += 1

        return count

    def detect_hallucinated_fields(self, parsed_raw: Any, parsed_gold: Any) -> int:
        """
        Detects fields in raw that are not in gold and not in acceptable field list.
        """
        raw_keys = set(collect_key_names(parsed_raw))
        gold_keys = set(collect_key_names(parsed_gold))
        allowed = gold_keys | self.acceptable_fields

        extras = raw_keys - allowed
        return len(extras)

    def detect_wrong_field_names(self, parsed_raw: Any) -> int:
        """
        Detects field names not in acceptable field list.

        This is broader than hallucinated_fields: it checks all key names,
        regardless of whether gold happens to contain them.
        """
        raw_keys = set(collect_key_names(parsed_raw))
        wrong = raw_keys - self.acceptable_fields

        return len(wrong)

    def detect_missing_fields(self, parsed_raw: Any, parsed_gold: Any) -> int:
        """
        Detects fields present in gold but missing from raw.
        Uses path-level comparison so nested fields count too.
        """
        if parsed_gold in ({}, [], "", None):
            return 0

        gold_paths = set(collect_paths(parsed_gold).keys())

        if parsed_raw is None:
            return len(gold_paths)

        raw_paths = set(collect_paths(parsed_raw).keys())
        missing = gold_paths - raw_paths

        return len(missing)

    def detect_placeholder_values(self, parsed_raw: Any, parsed_gold: Any) -> int:
        """
        Detects placeholder values like Unknown, N/A, null, or 0
        only when the gold value at the same path is not the same placeholder.
        """
        raw_flat = collect_paths(parsed_raw)
        gold_flat = collect_paths(parsed_gold)

        count = 0

        for path, raw_val in raw_flat.items():
            gold_val = gold_flat.get(path, None)

            if isinstance(raw_val, str):
                raw_norm = raw_val.strip().lower()
                gold_norm = gold_val.strip().lower() if isinstance(gold_val, str) else str(gold_val).lower()

                if raw_norm in PLACEHOLDER_STRINGS and raw_norm != gold_norm:
                    count += 1

            # 0 can be a real value, so only flag if gold at the same path is not 0.
            if raw_val == 0 and gold_val != 0:
                count += 1

        return count

    def detect_wrong_nesting(self, parsed_raw: Any, parsed_gold: Any) -> int:
        """
        Detects object/list/scalar structure differences at the same paths.
        Example: raw has array where gold has object.
        """
        raw_containers = collect_container_paths(parsed_raw)
        gold_containers = collect_container_paths(parsed_gold)

        count = 0

        for path, gold_kind in gold_containers.items():
            if path in raw_containers and raw_containers[path] != gold_kind:
                count += 1

        # Root mismatch matters.
        if raw_containers.get("$") != gold_containers.get("$"):
            count += 1

        return count

    def detect_wrong_types(self, parsed_raw: Any, parsed_gold: Any) -> int:
        """
        Detects scalar type mismatches.
        Example: string vs number, array vs string, boolean vs string.
        """
        raw_flat = collect_paths(parsed_raw)
        gold_flat = collect_paths(parsed_gold)

        count = 0

        for path, gold_val in gold_flat.items():
            if path not in raw_flat:
                continue

            raw_val = raw_flat[path]

            # Ignore values where either side is container.
            if isinstance(raw_val, (dict, list)) or isinstance(gold_val, (dict, list)):
                continue

            if not same_scalar_type(raw_val, gold_val):
                count += 1

        return count

    def detect_longer_shorter(self, parsed_raw: Any, parsed_gold: Any) -> int:
        """
        Detects responses much longer or shorter than gold.
        Uses a ratio threshold instead of absolute word count only.
        """
        raw_words = json_word_count(parsed_raw)
        gold_words = max(1, json_word_count(parsed_gold))

        ratio = raw_words / gold_words

        if ratio >= 1.5:
            return 1
        if ratio <= 0.5:
            return 1

        return 0

    def detect_wrong_order(self, parsed_raw: Any, parsed_gold: Any) -> int:
        """
        Detects key order differences when raw and gold have the same key set.
        This recursively checks dictionaries.
        """
        count = 0

        def walk(raw_obj: Any, gold_obj: Any):
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
        """
        Detects value mismatches at matching paths when types are compatible.
        """
        raw_flat = collect_paths(parsed_raw)
        gold_flat = collect_paths(parsed_gold)

        count = 0

        for path, gold_val in gold_flat.items():
            if path not in raw_flat:
                continue

            raw_val = raw_flat[path]

            if isinstance(raw_val, (dict, list)) or isinstance(gold_val, (dict, list)):
                continue

            if same_scalar_type(raw_val, gold_val) and raw_val != gold_val:
                count += 1

        return count

    def detect_repetition(self, parsed_raw: Any, parsed_gold: Any) -> int:
        """
        Detects repeated values in raw beyond what gold allows.

        Example:
        If gold has A:B repeated 2 times, raw can repeat it 2 times.
        If raw repeats it 5 times, count extra repetition.
        """
        raw_values = [
            normalize_scalar(v)
            for v in collect_paths(parsed_raw).values()
            if not isinstance(v, (dict, list))
        ]

        gold_values = [
            normalize_scalar(v)
            for v in collect_paths(parsed_gold).values()
            if not isinstance(v, (dict, list))
        ]

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

    # ========================================================
    # Family counts and summary columns
    # ========================================================

    def add_family_counts(self, errors: Dict[str, int]) -> None:
        """Adds family totals, total_errors, any_error, and distinct_error_types."""
        for family_name, cols in ERROR_FAMILIES.items():
            errors[family_name] = sum(errors.get(col, 0) for col in cols)

        errors["total_errors"] = sum(errors.get(col, 0) for col in GENERAL_ERROR_COLUMNS)
        errors["any_error"] = 1 if errors["total_errors"] > 0 else 0
        errors["distinct_error_types"] = sum(
            1 for col in GENERAL_ERROR_COLUMNS if errors.get(col, 0) > 0
        )


# ============================================================
# FILE LOADING / SAVING
# ============================================================

def load_json_or_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Loads a JSONL file or a JSON file containing a list/dict."""
    text = path.read_text(encoding="utf-8").strip()

    if not text:
        return []

    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        pass

    rows = []
    for line in text.splitlines():
        if line.strip():
            rows.append(json.loads(line))

    return rows


def load_manifest(run_dir: Path) -> Dict[str, Any]:
    """Loads manifest.json if it exists."""
    manifest_path = run_dir / "manifest.json"

    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    return {}


def save_error_csv(rows: List[Dict[str, Any]], output_csv: Path) -> None:
    """Saves analyzed rows to CSV."""
    base_columns = [
        "row_id",
        "dataset",
        "model",
        "method",
        "total_errors",
        "any_error",
        "distinct_error_types",
        "formatting_errors",
        "schema_structure_errors",
        "content_value_errors",
        "output_behavior_errors",
    ]

    columns = base_columns + GENERAL_ERROR_COLUMNS

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()

        for row in rows:
            writer.writerow({col: row.get(col, 0) for col in columns})


# ============================================================
# PROCESSING LOGIC
# ============================================================

def analyze_rows(rows: List[Dict[str, Any]], run_info: Dict[str, Any], detector: GeneralErrorDetector) -> List[Dict[str, Any]]:
    """Runs detector on each row and returns CSV-ready records."""
    analyzed = []

    for i, row in enumerate(rows):
        errors = detector.detect(row, run_info=run_info)

        out = {}

        out["row_id"] = row.get("row_id", row.get("id", i))
        out["dataset"] = row.get("dataset", run_info.get("dataset", "Unknown"))
        out["model"] = row.get("model", run_info.get("model", "Unknown"))
        out["method"] = row.get("method", run_info.get("method", "Unknown"))

        out.update(errors)
        analyzed.append(out)

    return analyzed


def process_single_file(input_path: Path, output_csv: Optional[Path], detector: GeneralErrorDetector) -> None:
    """Processes one JSON/JSONL file."""
    rows = load_json_or_jsonl(input_path)
    run_info = {}

    analyzed = analyze_rows(rows, run_info, detector)

    if output_csv is None:
        output_csv = input_path.with_name(input_path.stem + "_error_analysis.csv")

    save_error_csv(analyzed, output_csv)

    print(f"Analyzed {len(analyzed)} responses")
    print(f"Saved: {output_csv}")


def process_outputs_dir(outputs_dir: Path, detector: GeneralErrorDetector) -> None:
    """
    Processes an outputs directory containing run folders.
    Each run folder should contain responses.jsonl.
    """
    run_dirs = sorted([p for p in outputs_dir.iterdir() if p.is_dir()])

    print(f"Found {len(run_dirs)} run folders")

    all_analyzed = []

    for run_dir in run_dirs:
        responses_path = run_dir / "responses.jsonl"
        if not responses_path.exists():
            continue

        run_info = load_manifest(run_dir)
        rows = load_json_or_jsonl(responses_path)
        analyzed = analyze_rows(rows, run_info, detector)

        run_csv = run_dir / "general_error_analysis.csv"
        save_error_csv(analyzed, run_csv)

        all_analyzed.extend(analyzed)

        dataset = run_info.get("dataset", "Unknown")
        model = run_info.get("model", "Unknown")
        method = run_info.get("method", "Unknown")

        print(f"Processed {run_dir.name}: {len(analyzed)} rows | {dataset} | {model} | {method}")
        print(f"  Saved: {run_csv}")

    combined_csv = outputs_dir / "combined_general_error_analysis.csv"
    save_error_csv(all_analyzed, combined_csv)

    print()
    print(f"Combined rows: {len(all_analyzed)}")
    print(f"Saved combined CSV: {combined_csv}")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Detect general JSON/output errors in model responses.")
    parser.add_argument(
        "--input",
        default="pipeline/outputs",
        help="Path to outputs directory, responses.jsonl, or JSON file. Defaults to 'pipeline/outputs'."
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional CSV output path for single-file mode."
    )
    parser.add_argument(
        "--token-limit",
        type=int,
        default=4096,
        help="Token limit used for truncation detection."
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_csv = Path(args.output) if args.output else None

    detector = GeneralErrorDetector(token_limit=args.token_limit)

    if input_path.is_dir():
        process_outputs_dir(input_path, detector)
    else:
        process_single_file(input_path, output_csv, detector)


if __name__ == "__main__":
    main()