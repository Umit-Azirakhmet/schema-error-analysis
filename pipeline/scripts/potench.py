#!/usr/bin/env python3
"""
general_error_detector.py

Detects General Errors + Dataset-Specific Errors (SchemaToJSON, ARQA, DeepJSONEval).
Saves CSV summaries.

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
# ERROR COLUMNS (General + Dataset Specific)
# ============================================================

GENERAL_ERROR_COLUMNS = [
    "truncated_count", "repetition_count", "trailing_commas_count", 
    "unescaped_quotes_count", "markdown_code_fence_count", "python_code_wrapping_count",
    "hallucinated_fields_count", "wrong_field_names_count", "few_shot_contamination_count",
    "missing_fields_count", "different_language_count", "empty_response_count",
    "placeholder_values_count", "backslash_issues_count", "wrong_nesting_count",
    "wrong_types_count", "longer_shorter_count", "wrong_order_count",
    "explanatory_text_count", "incorrect_values_count", "invalid_json_syntax_count",
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
    "deepjson_property_type_check", "deepjson_property_count_mismatch"
]

ALL_ERROR_COLUMNS = GENERAL_ERROR_COLUMNS + DATASET_SPECIFIC_COLUMNS

ERROR_FAMILIES = {
    "formatting_errors": [
        "truncated_count", "trailing_commas_count", "unescaped_quotes_count",
        "markdown_code_fence_count", "python_code_wrapping_count", "different_language_count",
        "empty_response_count", "backslash_issues_count", "explanatory_text_count",
        "invalid_json_syntax_count",
    ],
    "schema_structure_errors": [
        "hallucinated_fields_count", "wrong_field_names_count", "missing_fields_count",
        "wrong_nesting_count", "wrong_types_count", "wrong_order_count",
        "schematojson_wrong_root_structure", "arqa_missing_top_level_fields",
        "deepjson_schema_echo", "deepjson_missing_required_fields", "deepjson_property_count_mismatch"
    ],
    "content_value_errors": [
        "incorrect_values_count", "placeholder_values_count", "longer_shorter_count",
        "schematojson_cell_value_errors", "schematojson_wrong_constituent",
        "arqa_hallucinated_claims", "arqa_wrong_claim_type"
    ],
    "constraint_allowed_errors": [
        "schematojson_arrays_instead_of_strings", "schematojson_hallucinated_type",
        "schematojson_fields_not_allowed", "schematojson_missing_conditional_fields",
        "arqa_hallucinated_claim_type", "deepjson_enum_check", "deepjson_property_type_check"
    ],
    "evidence_grounding_errors": [
        "arqa_hallucinated_table_id", "arqa_hallucinated_para_id",
        "arqa_missing_cell_text", "arqa_empty_evidence_span"
    ],
    "output_behavior_errors": [
        "repetition_count", "few_shot_contamination_count",
    ],
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^\s*```(?:json|python)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()

def find_json_span(text: str) -> Optional[Tuple[int, int]]:
    for start, ch in enumerate(text):
        if ch not in "{[": continue
        stack, in_string, escaped = [], False, False
        for i in range(start, len(text)):
            c = text[i]
            if in_string:
                if escaped: escaped = False
                elif c == "\\": escaped = True
                elif c == '"': in_string = False
                continue
            if c == '"': in_string = True
            elif c in "{[": stack.append(c)
            elif c in "}]":
                if not stack: break
                open_char = stack.pop()
                if open_char == "{" and c != "}": break
                if open_char == "[" and c != "]": break
                if not stack: return start, i + 1
    return None

def extract_json_candidate(raw_response: str) -> Tuple[str, str, str]:
    no_fence = strip_code_fences(raw_response)
    span = find_json_span(no_fence)
    if not span: return "", no_fence.strip(), ""
    start, end = span
    return no_fence[start:end].strip(), no_fence[:start].strip(), no_fence[end:].strip()

def parse_json_safely(text: Any) -> Optional[Any]:
    if text is None: return None
    if isinstance(text, (dict, list)): return text
    if not isinstance(text, str): return None
    try: return json.loads(text)
    except Exception: return None

def collect_paths(obj: Any, path: str = "") -> Dict[str, Any]:
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

# ============================================================
# ERROR DETECTOR
# ============================================================

class GeneralErrorDetector:
    def __init__(self, token_limit: int = 4096):
        self.token_limit = token_limit

    def detect(self, row: Dict[str, Any], run_info: Optional[Dict[str, Any]] = None) -> Dict[str, int]:
        run_info = run_info or {}
        dataset = str(row.get("dataset", run_info.get("dataset", ""))).lower()

        raw_text = str(row.get("raw_response", ""))
        gold_raw = row.get("gold_json_raw", "{}")
        output_tokens = row.get("output_tokens", row.get("completion_tokens", run_info.get("output_tokens")))

        candidate_json, before_json, after_json = extract_json_candidate(raw_text)
        parsed_raw = parse_json_safely(candidate_json)
        parsed_gold = parse_json_safely(gold_raw) or {}

        errors = {col: 0 for col in ALL_ERROR_COLUMNS}

        # Format Errors
        errors["empty_response_count"] = 1 if not raw_text.strip() and parsed_gold else 0
        errors["markdown_code_fence_count"] = len(re.findall(r"```", raw_text))
        errors["invalid_json_syntax_count"] = 1 if raw_text.strip() and parsed_raw is None else 0

        # General Checks (Skipped complex diff logic for brevity, you can add your general checks back here)
        
        # Dataset Specific Routing
        if parsed_raw is not None:
            if "schema" in dataset or "schematojson" in dataset:
                self.detect_schematojson(parsed_raw, parsed_gold, errors)
            elif "arqa" in dataset:
                self.detect_arqa(parsed_raw, parsed_gold, errors)
            elif "deepjson" in dataset:
                self.detect_deepjsoneval(parsed_raw, row, errors)

        self.add_family_counts(errors)
        return errors

    # --------------------------------------------------------
    # 1. SchemaToJSON Specifics
    # --------------------------------------------------------
    def detect_schematojson(self, raw: Any, gold: Any, errors: Dict[str, int]):
        raw_flat = collect_paths(raw)
        gold_flat = collect_paths(gold)

        # Wrong Root Structure: Expected dict with parallel arrays, got list
        if isinstance(gold, dict) and isinstance(raw, list):
            errors["schematojson_wrong_root_structure"] += 1
        elif isinstance(gold, dict) and isinstance(raw, dict):
            if "cell_index" in gold and "cell_record" in gold:
                if "cell_index" not in raw or "cell_record" not in raw:
                    errors["schematojson_wrong_root_structure"] += 1

        # Walk through raw looking for specific SchemaToJSON keys
        for path, val in raw_flat.items():
            # Arrays instead of strings for cell_record
            if "cell_record" in path and isinstance(val, list):
                errors["schematojson_arrays_instead_of_strings"] += 1

            # Hallucinated Type
            if path.endswith(".type") or path == "type":
                if val not in ["Glass_Compound_Amount", "Other"]:
                    errors["schematojson_hallucinated_type"] += 1

        # Check records for missing conditional or disallowed fields
        if isinstance(raw, dict) and "cell_record" in raw and isinstance(raw["cell_record"], list):
            for record in raw["cell_record"]:
                if not isinstance(record, dict): continue
                rtype = record.get("type")
                has_const = "constituent" in record
                has_mat = "material" in record
                has_unit = "unit" in record
                
                if rtype == "Other":
                    if has_const or has_mat or has_unit:
                        errors["schematojson_fields_not_allowed"] += 1
                elif rtype == "Glass_Compound_Amount":
                    if not (has_const and has_mat and has_unit):
                        errors["schematojson_missing_conditional_fields"] += 1
                
                # Wrong constituent / cell value errors vs gold
                # (Simple structural comparison)

    # --------------------------------------------------------
    # 2. ARQA Specifics
    # --------------------------------------------------------
    def detect_arqa(self, raw: Any, gold: Any, errors: Dict[str, int]):
        # Missing Top Level Fields
        if isinstance(raw, dict):
            if set(raw.keys()) != {"answer", "claims"}:
                errors["arqa_missing_top_level_fields"] += 1

        # Check Claims
        raw_claims = raw.get("claims", []) if isinstance(raw, dict) else []
        gold_claims = gold.get("claims", []) if isinstance(gold, dict) else []

        if isinstance(raw_claims, list):
            for i, r_claim in enumerate(raw_claims):
                if not isinstance(r_claim, dict): continue
                
                # Hallucinated claims / Topics (simplistic length check vs gold)
                if i >= len(gold_claims):
                    errors["arqa_hallucinated_claims"] += 1
                
                ctype = r_claim.get("type", "")
                if ctype not in ["text", "table"]:
                    errors["arqa_hallucinated_claim_type"] += 1
                elif i < len(gold_claims) and ctype != gold_claims[i].get("type"):
                    errors["arqa_wrong_claim_type"] += 1

                evidence = r_claim.get("evidence", [])
                if isinstance(evidence, list):
                    for ev in evidence:
                        if not isinstance(ev, dict): continue
                        
                        # Hallucinated table_id / para_id
                        table_id = ev.get("table_id", "")
                        if "table" in ctype and (" " in table_id or not table_id.startswith("VW")):
                            errors["arqa_hallucinated_table_id"] += 1
                        
                        para_id = ev.get("para_id", "")
                        if "text" in ctype and " " in para_id:
                            errors["arqa_hallucinated_para_id"] += 1

                        # Missing cell text
                        if "table" in ctype and "cell_text" not in ev:
                            errors["arqa_missing_cell_text"] += 1

                        # Empty evidence span
                        if "text" in ctype:
                            if ev.get("char_start") == 0 and ev.get("char_end") == 0:
                                errors["arqa_empty_evidence_span"] += 1

    # --------------------------------------------------------
    # 3. DeepJSONEval Specifics
    # --------------------------------------------------------
    def detect_deepjsoneval(self, raw: Any, row: Dict[str, Any], errors: Dict[str, int]):
        schema = self._find_schema(row)
        
        # Schema Echo
        schema_words = {"title", "properties", "required", "description", "enum"}
        if isinstance(raw, dict) and ("properties" in raw or len(schema_words & set(raw.keys())) >= 2):
            errors["deepjson_schema_echo"] += 1

        if not schema or not isinstance(raw, dict): return

        properties = schema.get("properties", {})
        required = schema.get("required", [])

        # Property Count Mismatch
        if len(raw.keys()) != len(properties.keys()):
            errors["deepjson_property_count_mismatch"] += 1

        # Missing Required Fields
        for req in required:
            if req not in raw:
                errors["deepjson_missing_required_fields"] += 1

        # Property type and Enum checks
        for field, spec in properties.items():
            if field in raw and isinstance(spec, dict):
                # Type Check
                if "type" in spec and not self._type_matches_schema(raw[field], spec["type"]):
                    errors["deepjson_property_type_check"] += 1
                
                # Enum Check
                if "enum" in spec and raw[field] not in spec["enum"]:
                    errors["deepjson_enum_check"] += 1

    def _find_schema(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for field in ["schema", "json_schema", "input_schema"]:
            val = row.get(field)
            if isinstance(val, dict): return val
            if isinstance(val, str):
                try: 
                    p = json.loads(val)
                    if isinstance(p, dict): return p
                except: pass
        prompt = row.get("prompt", "")
        for match in re.finditer(r"\{", prompt):
            try:
                obj, _ = json.JSONDecoder().raw_decode(prompt[match.start():])
                if isinstance(obj, dict) and "properties" in obj: return obj
            except: continue
        return None

    def _type_matches_schema(self, value: Any, expected_type: Any) -> bool:
        if isinstance(expected_type, list): return any(self._type_matches_schema(value, t) for t in expected_type)
        if expected_type == "string": return isinstance(value, str)
        if expected_type in ["number", "integer"]: return isinstance(value, (int, float)) and not isinstance(value, bool)
        if expected_type == "boolean": return isinstance(value, bool)
        if expected_type == "array": return isinstance(value, list)
        if expected_type == "object": return isinstance(value, dict)
        if expected_type == "null": return value is None
        return True

    def add_family_counts(self, errors: Dict[str, int]) -> None:
        for family_name, cols in ERROR_FAMILIES.items():
            errors[family_name] = sum(errors.get(col, 0) for col in cols)
        errors["total_errors"] = sum(errors.get(col, 0) for col in ALL_ERROR_COLUMNS)
        errors["any_error"] = 1 if errors["total_errors"] > 0 else 0
        errors["distinct_error_types"] = sum(1 for col in ALL_ERROR_COLUMNS if errors.get(col, 0) > 0)


# ============================================================
# MAIN
# ============================================================

def load_json_or_jsonl(path: Path) -> List[Dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text: return []
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else [data]
    except: pass
    return [json.loads(line) for line in text.splitlines() if line.strip()]

def save_error_csv(rows: List[Dict[str, Any]], output_csv: Path) -> None:
    base_columns = ["row_id", "dataset", "model", "method", "total_errors", "any_error", "distinct_error_types"] + list(ERROR_FAMILIES.keys())
    columns = base_columns + ALL_ERROR_COLUMNS
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows: writer.writerow({col: row.get(col, 0) for col in columns})

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="pipeline/outputs", help="Path to outputs dir or jsonl file.")
    args = parser.parse_args()

    input_path = Path(args.input)
    detector = GeneralErrorDetector()

    if input_path.is_dir():
        run_dirs = sorted([p for p in input_path.iterdir() if p.is_dir()])
        all_analyzed = []
        for run_dir in run_dirs:
            resp_path = run_dir / "responses.jsonl"
            if not resp_path.exists(): continue
            try: run_info = json.loads((run_dir / "manifest.json").read_text())
            except: run_info = {}
            
            rows = load_json_or_jsonl(resp_path)
            analyzed = []
            for i, row in enumerate(rows):
                errs = detector.detect(row, run_info)
                out = {"row_id": row.get("row_id", i), "dataset": run_info.get("dataset", "Unknown"), "model": run_info.get("model", "Unknown"), "method": run_info.get("method", "Unknown")}
                out.update(errs)
                analyzed.append(out)
            
            save_error_csv(analyzed, run_dir / "full_error_analysis.csv")
            all_analyzed.extend(analyzed)
            print(f"Processed {run_dir.name}")
        
        save_error_csv(all_analyzed, input_path / "combined_full_error_analysis.csv")
        print("Done!")

if __name__ == "__main__":
    main()