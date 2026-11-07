"""Conservative intended-answer and observable-completion rules for eacl-v2."""
import ast
import re
try:
    from .opportunity_metrics import strict_parse
except ImportError:
    from opportunity_metrics import strict_parse


def code_response(text):
    """Recognize executable Python without mistaking words in JSON values for code."""
    if strict_parse(text.strip())[0]:
        return False
    try:
        tree = ast.parse(text.strip())
        return any(not isinstance(node, ast.Expr) or isinstance(node.value, ast.Call)
                   for node in tree.body)
    except (SyntaxError, ValueError):
        return bool(re.search(r'(?m)^\s*(?:import\s+\w|from\s+\w+\s+import\b|'
                              r'def\s+\w+\(|class\s+\w+|[A-Za-z_]\w*\s*=\s*[\[{]|'
                              r'(?:print|json\.dumps|json\.loads)\s*\()', text))


def completion(raw, candidate, output_tokens=None, token_limit=4096, error=None, finish_reason=None):
    """Observable completion proxy, not a semantic-answer-quality judgment.

    Delimiter imbalance alone never implies a cutoff. Unknowns remain explicit.
    A malformed value plus a limit/length stop or an unfinished lexical slot is
    evidence of interruption. A finished terminal container with at most one
    missing ancestor delimiter is treated as observably finished; multiple open
    ancestors remain ambiguous. The rule is independent of the reference labels.
    """
    if strict_parse(candidate)[0]:
        return True, 'parseable_intended_answer'
    if not raw.strip() or error:
        return None, 'blank_or_generation_error'
    cleaned = re.sub(r'^\s*```(?:python|json)?\s*', '', raw.strip(), flags=re.I)
    cleaned = re.sub(r'\s*```\s*$', '', cleaned)
    if code_response(cleaned):
        try:
            ast.parse(cleaned)
            return True, 'complete_python_program_not_json'
        except (SyntaxError, ValueError):
            return None, 'unparseable_program'
    if not candidate:
        return None, 'no_identifiable_json_answer'
    try:
        token_limit_hit = output_tokens is not None and int(output_tokens) >= token_limit
    except (TypeError, ValueError):
        token_limit_hit = False
    # Track the lexical state of the candidate. Values inside strings are never
    # mistaken for structural delimiters or Python markers.
    inside = escaped = False
    outside = []
    for char in candidate:
        if inside:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                inside = False
                outside.append('"STRING"')
        elif char == '"':
            inside = True
        else:
            outside.append(char)
    tail = ''.join(outside).rstrip()
    if inside:
        if token_limit_hit or finish_reason in ('length', 'max_tokens'):
            return False, 'unterminated_string_at_length_limit'
        return None, 'unterminated_string_unknown_stop'
    # A missing value/next item or an unfinished JSON literal/number differs from
    # a finished payload that merely omitted its ancestor's closing delimiter.
    if tail.endswith((':', ',', '[')) or re.search(r'(?:[:\[,]\s*)(?:t|tr|tru|f|fa|fal|fals|n|nu|nul|-|\d+[eE][+-]?)$', tail):
        return False, 'unfinished_value_or_item'
    if tail.endswith(('}', ']')):
        unclosed = tail.count('{') + tail.count('[') - tail.count('}') - tail.count(']')
        if unclosed > 1:
            return None, 'multiple_ancestors_unfinished_or_malformed'
        return True, 'finished_payload_with_syntax_defect'
    return None, 'ambiguous_missing_delimiter'
