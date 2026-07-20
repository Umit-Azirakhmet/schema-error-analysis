"""
Run error detection on all output JSONL files and save CSV per run.
Standalone version - no external imports needed.
"""
import json
import os
import sys
import csv
import re
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from collections import Counter

# =====================================================================
# ERROR DETECTOR CLASS
# =====================================================================

class ErrorDetector:
    """
    Main class for detecting errors in LLM outputs.
    """
    
    def __init__(self, token_limit: int = 4096, acceptable_fields: Optional[Set[str]] = None):
        self.token_limit = token_limit
        self.acceptable_fields = acceptable_fields or set()
        self.gold_json = None
        self.raw_response = ""
        self.parsed_raw = None
        self.dataset = ""
        self.schema = None
        self.context = {}
        self.errors = {}
        self.output_tokens = None
        
    def detect_all(self, raw_response: str, gold_json: Union[str, Dict], 
                   dataset: str = "ARQA", token_limit: Optional[int] = None,
                   schema: Optional[Dict] = None, context: Optional[Dict] = None,
                   output_tokens: Optional[int] = None) -> Dict[str, Any]:
        
        self.raw_response = raw_response
        self.dataset = dataset
        self.schema = schema
        self.context = context or {}
        if token_limit is not None:
            self.token_limit = token_limit
        self.output_tokens = output_tokens
        
        if isinstance(gold_json, str):
            try:
                self.gold_json = json.loads(gold_json)
            except:
                self.gold_json = None
        else:
            self.gold_json = gold_json
            
        self.parsed_raw = None
        try:
            cleaned = self._clean_raw(raw_response)
            if cleaned:
                self.parsed_raw = json.loads(cleaned)
        except:
            pass
        
        self.errors = {}
        
        # General errors - each returns count (int)
        self.errors['truncated_count'] = self._detect_truncated()
        self.errors['repetition_count'] = self._detect_repetition()
        self.errors['markdown_code_fence_count'] = self._detect_markdown_code_fence()
        self.errors['python_code_count'] = self._detect_python_code()
        self.errors['hallucinated_fields_count'] = self._detect_hallucinated_fields()
        self.errors['wrong_field_names_count'] = self._detect_wrong_field_names()
        self.errors['missing_fields_count'] = self._detect_missing_fields()
        self.errors['different_language_count'] = self._detect_different_language()
        self.errors['empty_response_count'] = self._detect_empty_response()
        self.errors['placeholder_values_count'] = self._detect_placeholder_values()
        self.errors['backslash_issues_count'] = self._detect_backslash_issues()
        self.errors['wrong_nesting_count'] = self._detect_wrong_nesting()
        self.errors['wrong_types_count'] = self._detect_wrong_types()
        self.errors['longer_shorter_count'] = self._detect_longer_shorter()
        self.errors['wrong_order_count'] = self._detect_wrong_order()
        self.errors['explanatory_text_count'] = self._detect_explanatory_text()
        self.errors['incorrect_values_count'] = self._detect_incorrect_values()
        self.errors['invalid_json_syntax_count'] = self._detect_invalid_json_syntax()
        self.errors['trailing_commas_count'] = self._detect_trailing_commas()
        self.errors['unescaped_quotes_count'] = self._detect_unescaped_quotes()
        
        # Dataset-specific - each returns count (int)
        if dataset == "SchemaToJSON":
            self.errors.update(self._detect_schematojson())
        elif dataset == "ARQA":
            self.errors.update(self._detect_arqa())
        elif dataset == "DeepJSONEval":
            self.errors.update(self._detect_deepjsoneval())
            
        return self.errors
    
    def _clean_raw(self, raw: str) -> Optional[str]:
        cleaned = re.sub(r'```(?:json|python)?\s*', '', raw)
        cleaned = re.sub(r'```\s*', '', cleaned)
        match = re.search(r'(\{.*\}|\[.*\])', cleaned, re.DOTALL)
        if match:
            return match.group(1)
        return None
    
    def _is_valid_json(self, text: str) -> bool:
        try:
            json.loads(text)
            return True
        except:
            return False
    
    def _get_fields(self, obj: Any, prefix: str = "") -> Set[str]:
        fields = set()
        if isinstance(obj, dict):
            for k, v in obj.items():
                fields.add(prefix + k)
                fields.update(self._get_fields(v, prefix + k + "."))
        elif isinstance(obj, list):
            for item in obj:
                fields.update(self._get_fields(item, prefix))
        return fields
    
    def _get_nested_value(self, obj: Any, path: str, default=None):
        """Get nested value from dict using dot notation path."""
        parts = path.split('.')
        current = obj
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit():
                idx = int(part)
                if idx < len(current):
                    current = current[idx]
                else:
                    return default
            else:
                return default
        return current
    
    def _compare_nested_dicts(self, dict1: Dict, dict2: Dict, path: str = "") -> List[str]:
        """Compare two nested dicts and return list of differences."""
        differences = []
        all_keys = set(dict1.keys()) | set(dict2.keys())
        
        for key in all_keys:
            current_path = f"{path}.{key}" if path else key
            val1 = dict1.get(key)
            val2 = dict2.get(key)
            
            if key not in dict1:
                differences.append(f"Missing key: {current_path}")
            elif key not in dict2:
                differences.append(f"Extra key: {current_path}")
            elif isinstance(val1, dict) and isinstance(val2, dict):
                differences.extend(self._compare_nested_dicts(val1, val2, current_path))
            elif isinstance(val1, list) and isinstance(val2, list):
                if len(val1) != len(val2):
                    differences.append(f"List length mismatch at {current_path}: {len(val1)} vs {len(val2)}")
                else:
                    for i, (item1, item2) in enumerate(zip(val1, val2)):
                        if isinstance(item1, dict) and isinstance(item2, dict):
                            differences.extend(self._compare_nested_dicts(item1, item2, f"{current_path}[{i}]"))
                        elif item1 != item2:
                            differences.append(f"Value mismatch at {current_path}[{i}]: {item1} vs {item2}")
            elif val1 != val2:
                differences.append(f"Value mismatch at {current_path}: {val1} vs {val2}")
        
        return differences
    
    # ====== General Error Detectors (Return Counts) ======
    
    def _detect_truncated(self) -> int:
        """Detect if the response was truncated by hitting the token limit."""
        count = 0
        
        # Only flag truncation if output_tokens reached token limit
        if self.output_tokens is not None and self.output_tokens >= self.token_limit:
            count += 1
        
        return count
    
    def _detect_repetition(self) -> int:
        count = 0
        if not self.gold_json or not self.parsed_raw:
            return count
        gold_str = json.dumps(self.gold_json, ensure_ascii=False)
        raw_str = json.dumps(self.parsed_raw, ensure_ascii=False)
        def count_repeats(text: str) -> int:
            words = re.findall(r'\b\w{4,}\b', text)
            counter = Counter(words)
            repeats = sum(1 for c in counter.values() if c > 2)
            return repeats
        gold_repeats = count_repeats(gold_str)
        raw_repeats = count_repeats(raw_str)
        diff = raw_repeats - gold_repeats
        if diff > 2:
            count = diff
        return count
    
    def _detect_markdown_code_fence(self) -> int:
        count = 0
        matches = re.findall(r'```(?:json|python)?', self.raw_response)
        count = len(matches)
        return count
    
    def _detect_python_code(self) -> int:
        count = 0
        python_patterns = [r'\bimport\s+\w+', r'\bdef\s+\w+\s*\(', r'\bprint\s*\(', r'\breturn\s+', r'json\.dumps']
        for pat in python_patterns:
            if re.search(pat, self.raw_response):
                count += 1
        return count
    
    def _detect_hallucinated_fields(self) -> int:
        count = 0
        if not self.parsed_raw or not self.gold_json:
            return count
        raw_fields = self._get_fields(self.parsed_raw)
        gold_fields = self._get_fields(self.gold_json)
        all_allowed = gold_fields.union(self.acceptable_fields)
        hallucinated = raw_fields - all_allowed
        count = len(hallucinated)
        return count
    
    def _detect_wrong_field_names(self) -> int:
        """Count top-level field names that are not in acceptable_fields."""
        count = 0
        if not self.parsed_raw or not self.acceptable_fields:
            return count
        
        # Only check top-level fields, not nested dot-notation paths
        if isinstance(self.parsed_raw, dict):
            raw_fields = set(self.parsed_raw.keys())
        else:
            raw_fields = set()
        
        wrong = raw_fields - self.acceptable_fields
        count = len(wrong)
        return count
    
    def _detect_missing_fields(self) -> int:
        count = 0
        if not self._is_valid_json(self.raw_response):
            if self.dataset == "SchemaToJSON":
                required = ['cell_index', 'cell_record']
                return len(required)
            elif self.dataset == "ARQA":
                required = ['answer', 'claims']
                return len(required)
        
        if not self.parsed_raw or not self.gold_json:
            return count
        gold_fields = self._get_fields(self.gold_json)
        raw_fields = self._get_fields(self.parsed_raw)
        missing = gold_fields - raw_fields
        count = len(missing)
        return count
    
    def _detect_different_language(self) -> int:
        count = 0
        if re.search(r'[\u4e00-\u9fff]', self.raw_response):
            count += 1
        return count
    
    def _detect_empty_response(self) -> int:
        count = 0
        cleaned = self.raw_response.strip()
        if not cleaned or cleaned in ['""', "[]", "{}", "null"]:
            count += 1
        return count
    
    def _detect_placeholder_values(self) -> int:
        """Detect placeholder values like Unknown, N/A, xx, 0.0, 0."""
        count = 0
        
        # Check for placeholder strings (case insensitive)
        placeholder_strings = ['Unknown', 'N/A', 'xx']
        for ph in placeholder_strings:
            if re.search(rf'"{ph}"', self.raw_response, re.IGNORECASE):
                count += 1
        
        # Check for standalone "0" placeholder (not part of a larger number)
        # Look for "0" as a value, not as part of "10", "20", etc.
        if re.search(r':\s*"0"\s*[,}]', self.raw_response):
            count += 1
        if re.search(r':\s*0\s*[,}]', self.raw_response):
            count += 1
        
        return count
    
    def _detect_backslash_issues(self) -> int:
        count = 0
        backslash_count = self.raw_response.count('\\')
        if backslash_count % 2 == 1:
            count += 1
        return count
    
    def _detect_wrong_nesting(self) -> int:
        count = 0
        if not self.parsed_raw or not self.gold_json:
            return count
        if type(self.parsed_raw) != type(self.gold_json):
            count += 1
        return count
    
    def _detect_wrong_types(self) -> int:
        count = 0
        if not self.parsed_raw or not self.gold_json:
            return count
        def compare_types(obj1, obj2, path=""):
            nonlocal count
            if type(obj1) != type(obj2):
                count += 1
            elif isinstance(obj1, dict):
                for k in set(obj1.keys()) | set(obj2.keys()):
                    if k in obj1 and k in obj2:
                        compare_types(obj1[k], obj2[k], path + "." + k if path else k)
            elif isinstance(obj1, list):
                if len(obj1) == len(obj2):
                    for i, (item1, item2) in enumerate(zip(obj1, obj2)):
                        compare_types(item1, item2, f"{path}[{i}]")
        compare_types(self.parsed_raw, self.gold_json)
        return count
    
    def _detect_longer_shorter(self) -> int:
        count = 0
        if not self.parsed_raw or not self.gold_json:
            return count
        raw_str = json.dumps(self.parsed_raw, ensure_ascii=False)
        gold_str = json.dumps(self.gold_json, ensure_ascii=False)
        raw_words = len(re.findall(r'\w+', raw_str))
        gold_words = len(re.findall(r'\w+', gold_str))
        diff = raw_words - gold_words
        if abs(diff) > 20:
            count = abs(diff) // 10
        return count
    
    def _detect_wrong_order(self) -> int:
        count = 0
        if not self.parsed_raw or not self.gold_json or not isinstance(self.parsed_raw, dict) or not isinstance(self.gold_json, dict):
            return count
        raw_keys = list(self.parsed_raw.keys())
        gold_keys = list(self.gold_json.keys())
        if raw_keys != gold_keys:
            for i, (r, g) in enumerate(zip(raw_keys, gold_keys)):
                if r != g:
                    count += 1
        return count
    
    def _detect_explanatory_text(self) -> int:
        count = 0
        if not self._is_valid_json(self.raw_response):
            if self.parsed_raw is not None:
                cleaned = self._clean_raw(self.raw_response)
                if cleaned and len(cleaned) < len(self.raw_response):
                    extra_chars = len(self.raw_response) - len(cleaned)
                    count = extra_chars // 10
        return count
    
    def _detect_incorrect_values(self) -> int:
        count = 0
        if not self.parsed_raw or not self.gold_json:
            return count
        def compare_values(obj1, obj2, path=""):
            nonlocal count
            if type(obj1) != type(obj2):
                return
            if isinstance(obj1, dict):
                for k in set(obj1.keys()) | set(obj2.keys()):
                    if k in obj1 and k in obj2:
                        compare_values(obj1[k], obj2[k], path + "." + k if path else k)
            elif isinstance(obj1, list):
                if len(obj1) == len(obj2):
                    for i, (item1, item2) in enumerate(zip(obj1, obj2)):
                        compare_values(item1, item2, f"{path}[{i}]")
            else:
                if obj1 != obj2:
                    count += 1
        compare_values(self.parsed_raw, self.gold_json)
        return count
    
    def _detect_invalid_json_syntax(self) -> int:
        """Detect invalid JSON syntax in the raw response."""
        count = 0
        
        # Skip if response is empty
        if not self.raw_response or not self.raw_response.strip():
            count += 1
            return count
        
        # Try to extract JSON from the response (handles nl_to_format with PART 1)
        json_match = re.search(r'(\{.*\}|\[.*\])', self.raw_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            try:
                json.loads(json_str)
                # JSON is valid, no syntax errors
                return count
            except json.JSONDecodeError:
                # JSON has syntax errors
                count += 1
        
        # Check for unbalanced braces/brackets in the raw response
        open_braces = self.raw_response.count('{') - self.raw_response.count('}')
        open_brackets = self.raw_response.count('[') - self.raw_response.count(']')
        if open_braces != 0:
            count += abs(open_braces)
        if open_brackets != 0:
            count += abs(open_brackets)
        
        # Check for trailing commas
        if re.search(r',\s*}', self.raw_response) or re.search(r',\s*]', self.raw_response):
            count += 1
        
        return count
    
    def _detect_trailing_commas(self) -> int:
        count = 0
        trailing = re.findall(r',\s*}', self.raw_response)
        count += len(trailing)
        trailing = re.findall(r',\s*]', self.raw_response)
        count += len(trailing)
        return count
    
    def _detect_unescaped_quotes(self) -> int:
        """Detect unescaped quotes within JSON string values."""
        count = 0
        
        # Skip if response is empty
        if not self.raw_response or not self.raw_response.strip():
            return count
        
        # Try to extract JSON from the response
        json_match = re.search(r'(\{.*\}|\[.*\])', self.raw_response, re.DOTALL)
        if not json_match:
            return count
        
        json_str = json_match.group(1)
        
        # Check for unescaped quotes inside string values
        # Pattern: find quotes that are not escaped and appear inside a string value
        if re.search(r':\s*"[^"]*"[^"]*"', json_str):
            # This pattern matches strings that have quotes inside them
            # Look for sequences where a quote appears inside a string without a backslash
            if re.search(r':\s*"[^"\\]*(?<!\\)"(?=[^",}\]]*")', json_str):
                count += 1
        
        return count
    
    # ====== Dataset-specific detectors ======
    
    def _detect_schematojson(self) -> Dict:
        errors = {}
        errors['s2j_cell_value_errors'] = self._s2j_cell_value_errors()
        errors['s2j_array_instead_of_string'] = self._s2j_array_instead_of_string()
        errors['s2j_hallucinated_type'] = self._s2j_hallucinated_type()
        errors['s2j_wrong_root_structure'] = self._s2j_wrong_root_structure()
        errors['s2j_wrong_constituent'] = self._s2j_wrong_constituent()
        errors['s2j_fields_not_allowed'] = self._s2j_fields_not_allowed()
        errors['s2j_missing_conditional_fields'] = self._s2j_missing_conditional_fields()
        return errors
    
    def _s2j_cell_value_errors(self) -> int:
        """Count cell value mismatches between gold and response."""
        count = 0
        if not self.parsed_raw or not self.gold_json:
            return 0
        
        if not isinstance(self.parsed_raw, dict):
            return 0
        
        raw_records = self.parsed_raw.get('cell_record', [])
        gold_records = self.gold_json.get('cell_record', [])
        
        # Count missing entries (gold has more than raw)
        if len(gold_records) > len(raw_records):
            count += len(gold_records) - len(raw_records)
        
        # Count extra entries (raw has more than gold)
        if len(raw_records) > len(gold_records):
            count += len(raw_records) - len(gold_records)
        
        # Compare values and types for existing entries
        for i in range(min(len(raw_records), len(gold_records))):
            try:
                r_obj = json.loads(raw_records[i]) if isinstance(raw_records[i], str) else raw_records[i]
                g_obj = json.loads(gold_records[i]) if isinstance(gold_records[i], str) else gold_records[i]
                
                r_val = r_obj.get('value') if isinstance(r_obj, dict) else None
                g_val = g_obj.get('value') if isinstance(g_obj, dict) else None
                
                r_type = r_obj.get('type') if isinstance(r_obj, dict) else None
                g_type = g_obj.get('type') if isinstance(g_obj, dict) else None
                
                # Count as error if value mismatches OR type mismatches
                if r_val != g_val:
                    count += 1
                elif r_type != g_type:
                    count += 1
            except:
                count += 1
        
        return count
    
    def _s2j_array_instead_of_string(self) -> int:
        count = 0
        if self.parsed_raw and isinstance(self.parsed_raw, dict):
            rec = self.parsed_raw.get('cell_record')
            if rec and isinstance(rec, list):
                for item in rec:
                    if isinstance(item, dict):
                        count += 1
            return count
        
        if not self._is_valid_json(self.raw_response):
            if 'cell_record.append' in self.raw_response:
                count += 1
            if '"cell_record": [' in self.raw_response:
                count += 1
            if "['cell_record']" in self.raw_response:
                count += 1
        
        return count
    
    def _s2j_hallucinated_type(self) -> int:
        count = 0
        if self.parsed_raw and isinstance(self.parsed_raw, dict):
            rec = self.parsed_raw.get('cell_record', [])
            allowed = {'Glass_Compound_Amount', 'Other'}
            for rec_str in rec:
                try:
                    obj = json.loads(rec_str) if isinstance(rec_str, str) else rec_str
                    typ = obj.get('type')
                    if typ and typ not in allowed:
                        count += 1
                except:
                    pass
        return count
    
    def _s2j_wrong_root_structure(self) -> int:
        count = 0
        if not self._is_valid_json(self.raw_response):
            count += 1
            return count
        
        if self.parsed_raw:
            if isinstance(self.parsed_raw, list):
                count += 1
            elif isinstance(self.parsed_raw, dict):
                if 'cell_index' not in self.parsed_raw or 'cell_record' not in self.parsed_raw:
                    count += 1
        return count
    
    def _s2j_wrong_constituent(self) -> int:
        return 0
    
    def _s2j_fields_not_allowed(self) -> int:
        count = 0
        if self.parsed_raw and isinstance(self.parsed_raw, dict):
            rec = self.parsed_raw.get('cell_record', [])
            for rec_str in rec:
                try:
                    obj = json.loads(rec_str) if isinstance(rec_str, str) else rec_str
                    if obj.get('type') == 'Other':
                        if any(k in obj for k in ['constituent', 'unit', 'material']):
                            count += 1
                except:
                    pass
        return count
    
    def _s2j_missing_conditional_fields(self) -> int:
        count = 0
        if self.parsed_raw and isinstance(self.parsed_raw, dict):
            rec = self.parsed_raw.get('cell_record', [])
            required = {'constituent', 'unit', 'material'}
            for rec_str in rec:
                try:
                    obj = json.loads(rec_str) if isinstance(rec_str, str) else rec_str
                    if obj.get('type') == 'Glass_Compound_Amount':
                        missing = required - set(obj.keys())
                        count += len(missing)
                except:
                    pass
        return count
    
    # ====== ARQA Specific Detectors ======
    
    def _detect_arqa(self) -> Dict:
        errors = {}
        errors['arqa_hallucinated_claims'] = self._arqa_hallucinated_claims()
        errors['arqa_wrong_claim_type'] = self._arqa_wrong_claim_type()
        errors['arqa_hallucinated_claim_type'] = self._arqa_hallucinated_claim_type()
        errors['arqa_hallucinated_table_id'] = self._arqa_hallucinated_table_id()
        errors['arqa_missing_cell_text'] = self._arqa_missing_cell_text()
        errors['arqa_wrong_coordinates'] = self._arqa_wrong_coordinates()
        errors['arqa_empty_evidence_span'] = self._arqa_empty_evidence_span()
        errors['arqa_inaccurate_claims_evidence'] = self._arqa_inaccurate_claims_evidence()
        errors['arqa_missing_top_level_fields'] = self._arqa_missing_top_level_fields()
        return errors
    
    def _arqa_hallucinated_claims(self) -> int:
        """Count difference in number of claims between gold and response."""
        count = 0
        if not self.parsed_raw or not self.gold_json:
            return count
        
        raw_claims = self.parsed_raw.get('claims', [])
        gold_claims = self.gold_json.get('claims', [])
        
        count = abs(len(raw_claims) - len(gold_claims))
        return count
    
    def _arqa_wrong_claim_type(self) -> int:
        """Count claim type mismatches (table vs text) for matching claims only."""
        count = 0
        if not self.parsed_raw or not self.gold_json:
            return count
        
        raw_claims = self.parsed_raw.get('claims', [])
        gold_claims = self.gold_json.get('claims', [])
        
        for i in range(min(len(raw_claims), len(gold_claims))):
            raw_type = raw_claims[i].get('type')
            gold_type = gold_claims[i].get('type')
            if raw_type != gold_type:
                count += 1
        
        return count
    
    def _arqa_hallucinated_claim_type(self) -> int:
        """Count claims with invalid type values (not 'table' or 'text')."""
        count = 0
        if self.parsed_raw:
            allowed = {'table', 'text'}
            for claim in self.parsed_raw.get('claims', []):
                typ = claim.get('type')
                if typ and typ not in allowed:
                    count += 1
        return count
    
    def _arqa_hallucinated_table_id(self) -> int:
        """Count table cells with invalid or missing table_id."""
        count = 0
        if self.parsed_raw:
            pattern = r'^VW2015_T[a-f0-9]{6}$'
            for claim in self.parsed_raw.get('claims', []):
                cells = claim.get('evidence', {}).get('table_cells', [])
                for cell in cells:
                    tid = cell.get('table_id', '')
                    if not tid or not re.match(pattern, tid):
                        count += 1
        return count
    
    def _arqa_missing_cell_text(self) -> int:
        """Count table cells missing the cell_text field or with empty cell_text."""
        count = 0
        if self.parsed_raw:
            for claim in self.parsed_raw.get('claims', []):
                cells = claim.get('evidence', {}).get('table_cells', [])
                for cell in cells:
                    # Check if cell_text is missing, empty, or None
                    if 'cell_text' not in cell or not cell['cell_text']:
                        count += 1
                    # Also check if cell_text is a placeholder or invalid
                    elif cell['cell_text'] in ['', 'None', 'null', 'undefined']:
                        count += 1
        return count
    
    def _arqa_wrong_coordinates(self) -> int:
        """Count table cells with wrong row or col values compared to gold."""
        count = 0
        if not self.parsed_raw or not self.gold_json:
            return count
        
        raw_claims = self.parsed_raw.get('claims', [])
        gold_claims = self.gold_json.get('claims', [])
        
        for i in range(min(len(raw_claims), len(gold_claims))):
            raw_cells = raw_claims[i].get('evidence', {}).get('table_cells', [])
            gold_cells = gold_claims[i].get('evidence', {}).get('table_cells', [])
            
            for j in range(min(len(raw_cells), len(gold_cells))):
                raw_cell = raw_cells[j]
                gold_cell = gold_cells[j]
                
                raw_row = str(raw_cell.get('row', ''))
                gold_row = str(gold_cell.get('row', ''))
                if raw_row != gold_row:
                    count += 1
                
                raw_col = str(raw_cell.get('col', ''))
                gold_col = str(gold_cell.get('col', ''))
                if raw_col != gold_col:
                    count += 1
        
        return count
    
    def _arqa_empty_evidence_span(self) -> int:
        """Count text spans with char_start=0 and char_end=0 (likely hallucinated)."""
        count = 0
        if self.parsed_raw:
            for claim in self.parsed_raw.get('claims', []):
                spans = claim.get('evidence', {}).get('text_spans', [])
                for span in spans:
                    if span.get('char_start') == 0 and span.get('char_end') == 0:
                        count += 1
        return count
    
    def _arqa_inaccurate_claims_evidence(self) -> int:
        """Count claims where evidence text doesn't match the claim_text."""
        count = 0
        if not self.parsed_raw or not self.gold_json:
            return count
        
        raw_claims = self.parsed_raw.get('claims', [])
        gold_claims = self.gold_json.get('claims', [])
        
        for i in range(min(len(raw_claims), len(gold_claims))):
            raw_claim = raw_claims[i]
            gold_claim = gold_claims[i]
            
            raw_text = raw_claim.get('claim_text', '').strip()
            gold_text = gold_claim.get('claim_text', '').strip()
            
            if raw_text and gold_text:
                if gold_text not in raw_text and raw_text not in gold_text:
                    count += 1
                    continue
            
            raw_cells = raw_claim.get('evidence', {}).get('table_cells', [])
            gold_cells = gold_claim.get('evidence', {}).get('table_cells', [])
            
            for j in range(min(len(raw_cells), len(gold_cells))):
                raw_cell = raw_cells[j]
                gold_cell = gold_cells[j]
                
                raw_text = str(raw_cell.get('cell_text', '')).strip()
                gold_text = str(gold_cell.get('cell_text', '')).strip()
                if raw_text and gold_text and raw_text != gold_text:
                    count += 1
                    break
            
            raw_spans = raw_claim.get('evidence', {}).get('text_spans', [])
            gold_spans = gold_claim.get('evidence', {}).get('text_spans', [])
            
            for j in range(min(len(raw_spans), len(gold_spans))):
                raw_span = raw_spans[j]
                gold_span = gold_spans[j]
                
                raw_text = str(raw_span.get('text', '')).strip()
                gold_text = str(gold_span.get('text', '')).strip()
                if raw_text and gold_text and raw_text != gold_text:
                    count += 1
                    break
        
        return count
    
    def _arqa_missing_top_level_fields(self) -> int:
        """Count missing top-level fields (answer, claims)."""
        count = 0
        if self.parsed_raw:
            if 'answer' not in self.parsed_raw:
                count += 1
            if 'claims' not in self.parsed_raw:
                count += 1
        if self.parsed_raw and 'claims' in self.parsed_raw:
            if not self.parsed_raw['claims']:
                count += 1
        return count
    
    # ====== DeepJSONEval Specific Detectors ======
    
    def _detect_deepjsoneval(self) -> Dict:
        """Run all DeepJSONEval specific checks."""
        errors = {
            'dj_top_level_not_object': 0,
            'dj_schema_echo': 0,
            'dj_property_count': 0,
            'dj_enum_check': 0,
            'dj_required_fields': 0,
            'dj_property_type': 0,
            'dj_titles_mismatch': 0,
            'dj_wrong_schema': 0
        }
        
        if not self.schema:
            return errors
        
        schema_data = self._safe_parse_schema(self.schema)
        if not schema_data:
            return errors
        
        if not self.parsed_raw:
            if self.raw_response and 'properties' in self.raw_response and 'required' in self.raw_response:
                errors['dj_schema_echo'] = 1
                errors['dj_wrong_schema'] = 1
            return errors
        
        if not isinstance(self.parsed_raw, dict):
            errors['dj_top_level_not_object'] = 1
            return errors
        
        if self._dj_schema_echo():
            errors['dj_schema_echo'] = 1
            errors['dj_wrong_schema'] = 1
            return errors
        
        errors['dj_property_count'] = self._dj_property_count()
        
        # Check if response matches the schema's top-level structure
        schema_top_fields = set(schema_data.get('properties', {}).keys())
        response_top_fields = set(self.parsed_raw.keys())
        
        # If there's no overlap at top level, it's definitely the wrong schema
        overlap = schema_top_fields & response_top_fields
        if len(overlap) == 0:
            errors['dj_wrong_schema'] = 1
        elif len(overlap) < len(schema_top_fields) * 0.5:
            errors['dj_wrong_schema'] = 1
        
        # Only do deep validation if there's some overlap (not completely wrong schema)
        if errors['dj_wrong_schema'] == 0:
            deep_results = self._dj_traverse_schema_and_validate(schema_data, self.parsed_raw)
            errors['dj_enum_check'] = len(deep_results.get('enum_violations', []))
            errors['dj_required_fields'] = len(deep_results.get('missing_required', []))
            errors['dj_property_type'] = len(deep_results.get('type_violations', []))
            errors['dj_titles_mismatch'] = len(deep_results.get('title_mismatches', []))
        else:
            # If wrong schema, count missing required fields at top level
            required = schema_data.get('required', [])
            missing = [f for f in required if f not in self.parsed_raw]
            errors['dj_required_fields'] = len(missing)
        
        return errors
    
    def _safe_parse_schema(self, schema_str: Any) -> Optional[Dict]:
        if schema_str is None:
            return None
        if isinstance(schema_str, dict):
            return schema_str
        if isinstance(schema_str, str):
            try:
                return json.loads(schema_str)
            except json.JSONDecodeError:
                cleaned = re.sub(r'```(?:json)?\s*', '', schema_str)
                cleaned = re.sub(r'```\s*', '', cleaned)
                try:
                    return json.loads(cleaned)
                except:
                    return None
        return None
    
    def _dj_schema_echo(self) -> int:
        if not self.parsed_raw or not isinstance(self.parsed_raw, dict):
            return 0
        
        schema_keywords = {'properties', 'required', 'type', 'description', 'title', 'enum', 'items'}
        raw_keys = set(self.parsed_raw.keys())
        
        if 'properties' in raw_keys:
            overlap = raw_keys.intersection(schema_keywords)
            if len(overlap) >= 2:
                return 1
        
        if self.raw_response:
            if re.search(r'"properties"\s*:', self.raw_response) and re.search(r'"required"\s*:', self.raw_response):
                return 1
        
        return 0
    
    def _dj_property_count(self) -> int:
        if not self.parsed_raw or not isinstance(self.parsed_raw, dict):
            return 0
        
        schema_data = self._safe_parse_schema(self.schema)
        if not schema_data:
            return 0
        
        expected_count = len(schema_data.get('properties', {}))
        actual_count = len(self.parsed_raw.keys())
        
        return abs(expected_count - actual_count)
    
    def _dj_traverse_schema_and_validate(self, schema_node: Dict, data_node: Any, path: str = "root") -> Dict:
        results = {
            'enum_violations': [],
            'missing_required': [],
            'type_violations': [],
            'title_mismatches': []
        }
        
        if not schema_node or data_node is None:
            return results
        
        if not isinstance(schema_node, dict):
            return results
        
        expected_type = schema_node.get('type')
        
        if expected_type:
            type_mapping = {
                'string': str,
                'number': (int, float),
                'integer': int,
                'boolean': bool,
                'object': dict,
                'array': list
            }
            if expected_type in type_mapping:
                allowed_types = type_mapping[expected_type]
                is_valid = isinstance(data_node, allowed_types)
                if expected_type == 'boolean' and type(data_node) is not bool:
                    is_valid = False
                if expected_type in ['number', 'integer'] and type(data_node) is bool:
                    is_valid = False
                if not is_valid:
                    results['type_violations'].append(
                        f"{path}: Expected '{expected_type}', got '{type(data_node).__name__}'"
                    )
        
        if 'enum' in schema_node:
            allowed_enum = schema_node['enum']
            if data_node not in allowed_enum:
                results['enum_violations'].append(
                    f"{path}: '{data_node}' not in allowed list {allowed_enum}"
                )
        
        if expected_type == 'object' and isinstance(data_node, dict):
            required_fields = schema_node.get('required', [])
            for req in required_fields:
                if req not in data_node:
                    results['missing_required'].append(f"{path}.{req}")
            
            properties = schema_node.get('properties', {})
            for key, prop_schema in properties.items():
                expected_title = prop_schema.get('title')
                if expected_title and expected_title != key:
                    if expected_title in data_node and key not in data_node:
                        results['title_mismatches'].append(
                            f"{path}: Used title '{expected_title}' instead of key '{key}'"
                        )
                
                if key in data_node:
                    sub_results = self._dj_traverse_schema_and_validate(
                        prop_schema, data_node[key], f"{path}.{key}"
                    )
                    results['enum_violations'].extend(sub_results['enum_violations'])
                    results['missing_required'].extend(sub_results['missing_required'])
                    results['type_violations'].extend(sub_results['type_violations'])
                    results['title_mismatches'].extend(sub_results['title_mismatches'])
        
        if expected_type == 'array' and isinstance(data_node, list):
            items_schema = schema_node.get('items', {})
            for i, item in enumerate(data_node):
                sub_results = self._dj_traverse_schema_and_validate(
                    items_schema, item, f"{path}[{i}]"
                )
                results['enum_violations'].extend(sub_results['enum_violations'])
                results['missing_required'].extend(sub_results['missing_required'])
                results['type_violations'].extend(sub_results['type_violations'])
                results['title_mismatches'].extend(sub_results['title_mismatches'])
        
        return results


# =====================================================================
# MAIN RUNNER
# =====================================================================

def load_manifest(manifest_path: Path) -> Dict:
    if manifest_path.exists():
        with open(manifest_path, 'r') as f:
            return json.load(f)
    return {}

def load_responses(responses_path: Path, run_info: Dict) -> List[Dict]:
    results = []
    if responses_path.exists():
        with open(responses_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    data['run_info'] = run_info
                    results.append(data)
    return results

def save_csv(output_path: Path, responses: List[Dict]) -> str:
    csv_path = output_path / 'error_analysis.csv'
    
    if not responses:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['row_id', 'total_errors'])
        return str(csv_path)
    
    error_columns = set(['row_id', 'total_errors'])
    for response in responses:
        errors = response.get('error_analysis', {})
        for key in errors.keys():
            error_columns.add(key)
    
    columns = sorted(list(error_columns))
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        
        for response in responses:
            row = {
                'row_id': response.get('row_id', ''),
                'total_errors': 0
            }
            
            errors = response.get('error_analysis', {})
            for key, value in errors.items():
                if isinstance(value, (int, float)):
                    row[key] = value
                    if value > 0:
                        row['total_errors'] += value
                else:
                    row[key] = str(value)
            
            for col in columns:
                if col not in row:
                    row[col] = 0
            
            writer.writerow(row)
    
    return str(csv_path)

def process_run(run_dir: Path, detector: ErrorDetector) -> Dict:
    """Process a single run directory."""
    run_info = load_manifest(run_dir / 'manifest.json')
    dataset = run_info.get('dataset', 'Unknown')
    model = run_info.get('model', 'Unknown')
    method = run_info.get('method', 'Unknown')
    run_id = run_dir.name
    
    print(f"  Processing: {run_id}")
    print(f"    Dataset: {dataset}, Model: {model}, Method: {method}")
    
    responses_path = run_dir / 'responses.jsonl'
    responses = load_responses(responses_path, run_info)
    
    if not responses:
        print("    No responses found")
        return {'run_id': run_id, 'total': 0, 'csv_path': None}
    
    analyzed = []
    for response in responses:
        gold_json = response.get('gold_json_raw', '{}')
        raw_response = response.get('raw_response', '')
        output_tokens = response.get('output_tokens', 0)
        
        schema = None
        if dataset == "DeepJSONEval":
            prompt = response.get('prompt', '')
            schema = extract_schema_from_prompt(prompt)
        
        errors = detector.detect_all(
            raw_response=raw_response,
            gold_json=gold_json,
            dataset=dataset,
            output_tokens=output_tokens,
            token_limit=4096,
            schema=schema
        )
        
        response['error_analysis'] = errors
        analyzed.append(response)
    
    csv_path = save_csv(run_dir, analyzed)
    
    error_counts = {}
    for response in analyzed:
        errors = response.get('error_analysis', {})
        for key, value in errors.items():
            if isinstance(value, (int, float)) and value > 0:
                error_counts[key] = error_counts.get(key, 0) + value
    
    print(f"    Total responses: {len(analyzed)}")
    print(f"    CSV saved: {csv_path}")
    
    return {
        'run_id': run_id,
        'total': len(analyzed),
        'error_counts': error_counts,
        'csv_path': csv_path
    }

def extract_schema_from_prompt(prompt: str) -> Optional[Dict]:
    """Extract schema from DeepJSONEval prompt."""
    if not prompt:
        return None
    
    try:
        schema_start = prompt.find("Schema:\n")
        if schema_start == -1:
            schema_start = prompt.find("Schema:")
        
        if schema_start != -1:
            schema_start = schema_start + len("Schema:\n") if "\n" in prompt[schema_start:] else schema_start + len("Schema:")
            
            text_start = prompt.find("\n\nText:", schema_start)
            if text_start == -1:
                text_start = prompt.find("\nText:", schema_start)
            if text_start == -1:
                text_start = len(prompt)
            
            schema_str = prompt[schema_start:text_start].strip()
            
            if schema_str:
                schema_str = re.sub(r'```(?:json)?\s*', '', schema_str)
                schema_str = re.sub(r'```\s*', '', schema_str)
                return json.loads(schema_str)
    except:
        pass
    
    return None

def main():
    parser = argparse.ArgumentParser(description='Run error analysis on outputs')
    parser.add_argument('--outputs', type=str, default='outputs',
                       help='Path to outputs directory')
    parser.add_argument('--run', type=str, default=None,
                       help='Specific run ID to analyze (optional)')
    args = parser.parse_args()
    
    outputs_dir = Path(args.outputs)
    
    if not outputs_dir.exists():
        print(f"Error: Directory not found: {outputs_dir}")
        return
    
    print("="*60)
    print("ERROR ANALYSIS")
    print("="*60)
    
    if args.run:
        run_dirs = [outputs_dir / args.run]
    else:
        run_dirs = [d for d in outputs_dir.iterdir() if d.is_dir()]
    
    run_dirs = sorted(run_dirs)
    print(f"Found {len(run_dirs)} runs to analyze\n")
    
    # Initialize detector with ALL acceptable fields (top-level only)
    detector = ErrorDetector(
        token_limit=4096,
        acceptable_fields={
            # ARQA fields
            "answer", "claims", "type", "claim_text", "evidence",
            "table_cells", "text_spans", "table_id", "row", "col",
            "cell_text", "para_id", "char_start", "char_end",
            
            # SchemaToJSON fields
            "cell_index", "cell_record", "value", "constituent",
            "unit", "material", "Glass_Compound_Amount", "Other",
            
            # DeepJSONEval - Movie schema (top-level only)
            "Year", "IsSequel", "Ratings", "Crew",
            
            # DeepJSONEval - Game schema (top-level only)
            "GameInfo", "GameStatistics", "DLCs",
            
            # DeepJSONEval - Patient schema (top-level only)
            "PersonalInfo", "MedicalHistory",
            
            # DeepJSONEval - Car schema (top-level only)
            "BasicInfo", "TechnicalSpecs", "Features"
        }
    )
    
    all_results = []
    total_responses = 0
    
    for run_dir in run_dirs:
        result = process_run(run_dir, detector)
        all_results.append(result)
        total_responses += result['total']
        print()
    
    print("="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total runs: {len(all_results)}")
    print(f"Total responses analyzed: {total_responses}")
    
    all_errors = {}
    for result in all_results:
        for error_type, count in result.get('error_counts', {}).items():
            all_errors[error_type] = all_errors.get(error_type, 0) + count
    
    if all_errors:
        print("\nError breakdown (counts):")
        for error_type, count in sorted(all_errors.items(), key=lambda x: -x[1]):
            avg = count / total_responses if total_responses > 0 else 0
            bar = "█" * int(avg * 2) if avg > 0 else ""
            print(f"  {error_type:35} {count:4} (avg: {avg:.2f}) {bar}")
    
    print("\n" + "="*60)
    print("DONE")
    print("="*60)


if __name__ == "__main__":
    main()