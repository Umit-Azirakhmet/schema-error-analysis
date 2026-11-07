"""One primary reporting family per legacy detector; diagnostics are subtypes.

Gold-relative structure diagnostics are proxies, not proof of schema violation.
Only full JSON Schema validation determines the schema family flag.
"""
FAMILY_LEAVES = {
    'completion': ['truncated_count'],
    'syntax': ['invalid_json_syntax_count', 'backslash_issues_count'],
    'envelope_contamination': ['markdown_code_fence_count', 'python_code_wrapping_count', 'explanatory_text_count'],
    'schema_non_conformance': [
        'hallucinated_fields_count', 'missing_fields_count', 'wrong_nesting_count',
        'wrong_nesting_depth_count', 'wrong_types_count', 'wrong_order_count',
        'schematojson_arrays_instead_of_strings', 'schematojson_hallucinated_type',
        'schematojson_wrong_root_structure', 'schematojson_fields_not_allowed',
        'schematojson_missing_conditional_fields', 'arqa_wrong_claim_type',
        'arqa_hallucinated_claim_type', 'arqa_missing_top_level_fields',
        'deepjson_enum_check', 'deepjson_schema_echo', 'deepjson_missing_required_fields',
        'deepjson_property_type_check', 'deepjson_property_count_mismatch'],
    'content_fidelity': ['repetition_count', 'different_language_count', 'empty_response_count',
        'placeholder_values_count', 'longer_shorter_count', 'incorrect_values_count',
        'schematojson_cell_value_errors', 'schematojson_wrong_constituent',
        'arqa_hallucinated_claims', 'arqa_hallucinated_table_id', 'arqa_hallucinated_para_id',
        'arqa_missing_cell_text', 'arqa_empty_evidence_span'],
}
LEAF_FAMILY = {leaf: family for family, leaves in FAMILY_LEAVES.items() for leaf in leaves}
RAW_LEAVES = {'truncated_count', 'invalid_json_syntax_count', 'markdown_code_fence_count',
              'python_code_wrapping_count', 'explanatory_text_count', 'different_language_count',
              'backslash_issues_count'}


def family_flags(result):
    flags = {
        'completion': None if result['is_complete'] is None else not result['is_complete'],
        'syntax': not result['valid_parse'],
        'envelope_contamination': result['envelope_contamination_detected'],
        'schema_non_conformance': None if result['schema_valid'] is None else not result['schema_valid'],
        'content_fidelity': None if result['content_correct'] is None else not result['content_correct'],
    }
    return {f'{family}_flag': flag for family, flag in flags.items()}
