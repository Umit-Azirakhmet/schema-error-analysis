"""Version 1 offline metrics. Never infer a JSON Schema from a gold example."""
import json
import re
from functools import lru_cache

from jsonschema import validators, FormatChecker
try:
    from .gold_json_analysis import scalar_paths
except ImportError:
    from gold_json_analysis import scalar_paths


def strict_parse(text):
    try:
        value = json.loads(text, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
        return True, value
    except (TypeError, ValueError):
        return False, None


def paths(value, prefix=(), scalar_only=True):
    if scalar_only:
        return scalar_paths(value, prefix)
    result = {}
    if not scalar_only or not isinstance(value, (dict, list)):
        result[prefix] = value
    if isinstance(value, dict):
        for key, child in value.items():
            result.update(paths(child, prefix + (key,), scalar_only))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            result.update(paths(child, prefix + (index,), scalar_only))
    return result


def same_type(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b)
    return (isinstance(a, (int, float)) and isinstance(b, (int, float))) or type(a) is type(b)


def json_equal(a, b):
    if not same_type(a, b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(json_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(json_equal(x, y) for x, y in zip(a, b))
    return a == b


def metric(errors=None, opportunities=None, eligible=False):
    return {'errors': errors if eligible else None,
            'opportunities': opportunities if eligible else None,
            'eligible': bool(eligible),
            'rate': errors / opportunities if eligible and opportunities else None}


@lru_cache(maxsize=4096)
def _validator(encoded):
    schema = json.loads(encoded)
    cls = validators.validator_for(schema)
    cls.check_schema(schema)
    # No remote retrieval: the Registry has no network retriever.
    from referencing import Registry
    return cls(schema, registry=Registry(), format_checker=FormatChecker())


def schema_errors(value, schema):
    if schema is None:
        return None, 'missing_schema'
    try:
        return list(_validator(json.dumps(schema, sort_keys=True)).iter_errors(value)), None
    except Exception as exc:
        return None, f'{type(exc).__name__}: {exc}'


def schema_slots(value, schema):
    """Applicable *present* typed nodes and required slots on existing objects.

    Branching/conditional schemas are not normalized: full validation still runs.
    Avoid a misleading denominator for ambiguous branches or recursive references.
    """
    typed = required = missing = wrong = 0
    root = schema
    def visit(obj, node, refs=()):
        nonlocal typed, required, missing, wrong
        if isinstance(node, bool):
            return
        if any(k in node for k in ('anyOf', 'oneOf', 'allOf', 'if', 'dependentSchemas',
                                    'dependentRequired', 'dependencies', '$dynamicRef')):
            raise ValueError('branch-dependent opportunities')
        if '$ref' in node:
            ref = node['$ref']
            if not ref.startswith('#/') or ref in refs:
                raise ValueError('unsupported opportunity reference')
            target = root
            for part in ref[2:].split('/'):
                target = target[part.replace('~1', '/').replace('~0', '~')]
            visit(obj, target, refs + (ref,))
            if len(node) > 1:
                raise ValueError('reference siblings')
            return
        if 'type' in node:
            typed += 1
            cls = validators.validator_for(root)
            types = node['type'] if isinstance(node['type'], list) else [node['type']]
            wrong += not any(cls.TYPE_CHECKER.is_type(obj, t) for t in types)
        if isinstance(obj, dict):
            req = node.get('required', [])
            required += len(req)
            missing += sum(k not in obj for k in req)
            if node.get('patternProperties') or isinstance(node.get('additionalProperties'), dict):
                raise ValueError('dynamic property opportunities')
            for key, child in node.get('properties', {}).items():
                if key in obj:
                    visit(obj[key], child, refs)
        if isinstance(obj, list):
            if 'prefixItems' in node or isinstance(node.get('items'), list):
                raise ValueError('tuple opportunities')
            for child in obj:
                visit(child, node.get('items', {}), refs)
    try:
        visit(value, schema)
        return metric(missing, required, True), metric(wrong, typed, True)
    except (ValueError, KeyError, TypeError):
        return metric(), metric()


def escaping_metric(candidate):
    """Unit: one backslash-initiated escape lexeme inside a quoted candidate string.

    Unicode lexemes consume four hex digits; a trailing backslash is one failure.
    This measures lexical escaping only, not omitted escapes or gold fidelity.
    """
    inside = False
    i = errors = opportunities = 0
    while i < len(candidate):
        char = candidate[i]
        if char == '"':
            inside = not inside
        elif inside and char == '\\':
            opportunities += 1
            nxt = candidate[i + 1:i + 2]
            if nxt == 'u':
                code = candidate[i + 2:i + 6]
                errors += not bool(re.fullmatch(r'[0-9a-fA-F]{4}', code))
                i += 5
            else:
                errors += not bool(nxt and nxt in '"\\/bfnrt')
                i += 1
        i += 1
    return metric(errors, opportunities, bool(candidate))


def cell_metric(output, gold):
    def cells(obj):
        if not isinstance(obj, dict):
            raise ValueError('no cell index')
        coords, records = obj.get('cell_index'), obj.get('cell_record')
        if not isinstance(coords, list) or not isinstance(records, list) or len(coords) != len(records):
            raise ValueError('unaligned cells')
        result = {}
        for coord, record in zip(coords, records):
            key = json.dumps(coord)
            if key in result:
                raise ValueError('duplicate coordinates')
            if isinstance(record, str):
                ok, record = strict_parse(record)
                if not ok:
                    raise ValueError('unparseable cell')
            if not isinstance(record, dict) or 'value' not in record:
                raise ValueError('no cell value')
            result[key] = record['value']
        return result
    try:
        expected, actual = cells(gold), cells(output)
        return metric(sum(k not in actual or not same_type(v, actual[k]) or v != actual[k]
                          for k, v in expected.items()), len(expected), True)
    except ValueError:
        return metric()


def decoded_cell_records(obj):
    """Pair records with coordinates, preserving duplicate-coordinate instances."""
    if not isinstance(obj, dict) or not isinstance(obj.get('cell_index'), list) or not isinstance(obj.get('cell_record'), list):
        raise ValueError('missing paired cell arrays')
    if len(obj['cell_index']) != len(obj['cell_record']):
        raise ValueError('unpaired cell arrays')
    paired = []
    for coord, record in zip(obj['cell_index'], obj['cell_record']):
        if not isinstance(coord, list) or len(coord) != 3 or any(type(v) is not int for v in coord):
            raise ValueError('invalid cell coordinates')
        if isinstance(record, str):
            ok, record = strict_parse(record)
            if not ok:
                raise ValueError('invalid serialized record')
        if not isinstance(record, dict):
            raise ValueError('invalid record object')
        paired.append((tuple(coord), record))
    return paired


def cell_records_equal(output, gold):
    try:
        expected, actual = decoded_cell_records(gold), decoded_cell_records(output)
    except ValueError:
        return False
    if len(expected) != len(actual):
        return False
    remaining = list(actual)
    for coord, record in expected:
        match = next((i for i, (key, value) in enumerate(remaining)
                      if key == coord and json_equal(record, value)), None)
        if match is None:
            return False
        remaining.pop(match)
    return True


def evaluate(candidate, gold_raw, schema=None, dataset=''):
    ok, output = strict_parse(candidate)
    gold_ok, gold = strict_parse(gold_raw) if isinstance(gold_raw, str) else (gold_raw is not None, gold_raw)
    result = {'valid_parse': ok, 'is_content_assessable': ok and gold_ok,
              'content_correct': None, 'strict_content_correct': None,
              'content_metric': 'strict_gold_match_proxy',
              'schema_valid': None, 'schema_assessment_reason': None}
    metrics = {name: metric() for name in ('missing_gold_scalar_paths', 'wrong_value',
               'gold_type_mismatch', 'missing_required_schema_fields', 'type_mismatch', 'cell_value', 'cell_record')}
    metrics['escaping_failure'] = escaping_metric(candidate)
    errors, reason = schema_errors(output, schema) if ok else (None, 'invalid_parse')
    result.update(is_schema_assessable=errors is not None, schema_assessment_reason=reason)
    if errors is not None:
        result['schema_valid'] = not errors
        metrics['missing_required_schema_fields'], metrics['type_mismatch'] = schema_slots(output, schema)
    if ok and gold_ok:
        expected, actual = paths(gold), paths(output)
        all_actual = paths(output, scalar_only=False)
        metrics['missing_gold_scalar_paths'] = metric(sum(p not in actual for p in expected), len(expected), True)
        metrics['wrong_value'] = metric(sum(p in actual and same_type(v, actual[p]) and v != actual[p]
                                          for p, v in expected.items()), len(expected), True)
        comparable = [p for p in expected if p in all_actual]
        metrics['gold_type_mismatch'] = metric(sum(not same_type(expected[p], all_actual[p]) for p in comparable), len(comparable), True)
        # This is a strict gold-match proxy, not semantic human task accuracy.
        result['content_correct'] = json_equal(output, gold)
        result['strict_content_correct'] = result['content_correct']
        if dataset == 'SchemaToJSON':
            result['content_correct'] = cell_records_equal(output, gold)
            result['content_metric'] = 'decoded_coordinate_aligned_cell_record_gold_proxy'
            try:
                expected_records, actual_records = decoded_cell_records(gold), decoded_cell_records(output)
                remaining = list(actual_records)
                failures = 0
                for coord, record in expected_records:
                    match = next((i for i, (key, value) in enumerate(remaining)
                                  if key == coord and json_equal(record, value)), None)
                    if match is None:
                        failures += 1
                    else:
                        remaining.pop(match)
                metrics['cell_record'] = metric(failures, len(expected_records), True)
                result['extra_or_nonmatching_cell_records'] = len(remaining)
            except ValueError:
                pass
        metrics['cell_value'] = cell_metric(output, gold)
    for name, values in metrics.items():
        result.update({f'{name}_{key}': value for key, value in values.items()})
    try:
        from .output_contracts import assess_contract
    except ImportError:
        from output_contracts import assess_contract
    result.update(assess_contract(dataset, output, ok, result['schema_valid']))
    return result
