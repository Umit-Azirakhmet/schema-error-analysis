"""Retrospective output contracts. These were NOT supplied JSON Schemas.

Versioning explicit rules avoids using a single gold instance as a schema.
ARQA follows the answer/claims/evidence template; SchemaToJSON follows its paired
coordinate / serialized-record grammar. Grounding and value fidelity are separate.
"""
from jsonschema import Draft202012Validator


def object_schema(properties, required=None, extras=True):
    return dict(type='object', properties=properties,
                required=list(properties) if required is None else required, additionalProperties=extras)


STRING = {'type': 'string'}
ARQA_CELL = object_schema({'table_id': STRING, 'row': {'type': ['string', 'integer']},
    'col': {'type': ['string', 'integer']}, 'cell_text': STRING})
ARQA_SPAN = object_schema({'para_id': STRING, 'char_start': {'type': 'integer', 'minimum': 0},
    'char_end': {'type': 'integer', 'minimum': 0}, 'text': STRING})
ARQA_EVIDENCE = object_schema({'table_cells': {'type': 'array', 'items': ARQA_CELL},
    'text_spans': {'type': 'array', 'items': ARQA_SPAN}}, required=[])
ARQA_CLAIM = object_schema({'type': {'enum': ['text', 'table']}, 'claim_text': STRING,
    'evidence': ARQA_EVIDENCE})
ARQA_CLAIM['allOf'] = [
    {'if': {'properties': {'type': {'const': kind}}, 'required': ['type']},
     'then': {'properties': {'evidence': {'required': [field]}}}}
    for kind, field in [('table', 'table_cells'), ('text', 'text_spans')]]
ARQA_TEMPLATE = object_schema({'answer': STRING, 'claims': {'type': 'array', 'items': ARQA_CLAIM}}, extras=False)
S2J_GRAMMAR = object_schema({'cell_index': {'type': 'array', 'items': {'type': 'array',
    'items': {'type': 'integer'}, 'minItems': 3, 'maxItems': 3}},
    'cell_record': {'type': 'array', 'items': STRING}}, extras=False)


def assess_contract(dataset, output, parse_ok, schema_valid=None):
    try:
        from .opportunity_metrics import strict_parse
    except ImportError:
        from opportunity_metrics import strict_parse
    if dataset == 'DeepJSONEval':
        return dict(contract_kind='supplied_json_schema', contract_version='supplied',
            contract_assessable=schema_valid is not None, contract_valid=schema_valid,
            contract_error_count=None if schema_valid is None else int(not schema_valid))
    schema = ARQA_TEMPLATE if dataset == 'ARQA' else S2J_GRAMMAR if dataset == 'SchemaToJSON' else None
    result = dict(contract_kind='retrospective_arqa_template' if dataset == 'ARQA' else
        'retrospective_cell_record_grammar' if dataset == 'SchemaToJSON' else 'unavailable',
        contract_version='retrospective-v1', contract_assessable=False,
        contract_valid=None, contract_error_count=None)
    if not parse_ok or schema is None:
        return result
    errors = list(Draft202012Validator(schema).iter_errors(output))
    count = len(errors)
    if dataset == 'SchemaToJSON' and isinstance(output, dict):
        coords, records = output.get('cell_index'), output.get('cell_record')
        if isinstance(coords, list) and isinstance(records, list):
            count += len(coords) != len(records)
            for record in records:
                ok, decoded = strict_parse(record) if isinstance(record, str) else (False, None)
                if not ok or not isinstance(decoded, dict):
                    count += 1
                    continue
                required = {'value', 'type'}
                kind = decoded.get('type')
                if kind == 'Glass_Compound_Amount':
                    required |= {'constituent', 'unit', 'material'}
                count += kind not in ('Other', 'Glass_Compound_Amount')
                count += len(set(decoded) ^ required)
                count += sum(not isinstance(v, str) for v in decoded.values())
    if dataset == 'ARQA' and isinstance(output, dict):
        for claim in output.get('claims', []) if isinstance(output.get('claims'), list) else []:
            if not isinstance(claim, dict) or not isinstance(claim.get('evidence'), dict):
                continue
            for span in claim['evidence'].get('text_spans', []) if isinstance(claim['evidence'].get('text_spans'), list) else []:
                if isinstance(span, dict) and type(span.get('char_start')) is int and type(span.get('char_end')) is int:
                    count += span['char_end'] < span['char_start']
    result.update(contract_assessable=True, contract_valid=count == 0, contract_error_count=count)
    return result
