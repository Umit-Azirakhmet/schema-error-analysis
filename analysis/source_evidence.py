"""Recover verifiable ARQA source context without pretending it is an archived prompt."""
import csv
import json
from collections import Counter
from pathlib import Path

from scripts.opportunity_metrics import strict_parse, json_equal
from scripts.Error_detector import extract_json_candidate


class EvidenceIndex:
    def __init__(self, root=Path('data')):
        with (root / 'ARQA.csv').open(encoding='utf-8-sig', newline='') as f:
            self.questions = {r['qa_id']: r for r in csv.DictReader(f)}
        with (root / 'ARQA_DB.csv').open(encoding='utf-8-sig', newline='') as f:
            contexts = list(csv.DictReader(f))
        counts = Counter(r['table_id'] for r in contexts)
        self.contexts = {r['table_id']: r for r in contexts if counts[r['table_id']] == 1}

    def recover(self, record):
        if record['dataset'] != 'ARQA':
            return None, 'not_arqa'
        question = self.questions.get(str(record['row_id']))
        if not question:
            return None, 'qa_id_not_found'
        ok, current_gold = strict_parse(question['gold_answer'])
        gold_ok, archived_gold = strict_parse(record.get('gold_json_raw'))
        if not ok or not gold_ok or not json_equal(current_gold, archived_gold):
            return None, 'gold_mismatch_do_not_attach_current_context'
        context = self.contexts.get(question['table_id'])
        if not context:
            return None, 'missing_or_ambiguous_table_context'
        return dict(question=question['question'], table_id=question['table_id'],
            context=context, source='data/ARQA.csv + data/ARQA_DB.csv; qa_id and typed gold verified'), None

    def assess(self, record):
        source, reason = self.recover(record)
        result = dict(source_context_available=source is not None, source_context_reason=reason,
            grounding_assessable=False, grounding_errors=None, grounding_opportunities=None,
            grounding_rate=None, grounding_flag=None)
        if source is None:
            return result, None
        result['source_context_provenance'] = source['source']
        result['source_context_is_original_prompt'] = False
        candidate = extract_json_candidate(str(record.get('raw_response') or ''))[0]
        ok, output = strict_parse(candidate)
        if not ok or not isinstance(output, dict) or not isinstance(output.get('claims'), list):
            result['source_context_reason'] = 'unparseable_or_no_claims'
            return result, source
        paragraphs_ok, paragraphs = strict_parse(source['context']['paragraphs'])
        if not paragraphs_ok or not isinstance(paragraphs, list):
            result['source_context_reason'] = 'unusable_source_paragraphs'
            return result, source
        paragraph_map = {p['para_id']: p['text'] for p in paragraphs
                         if isinstance(p, dict) and 'para_id' in p and isinstance(p.get('text'), str)}
        errors = opportunities = unresolved = 0
        for claim in output['claims']:
            if not isinstance(claim, dict) or not isinstance(claim.get('evidence'), dict):
                unresolved += 1
                continue
            evidence = claim['evidence']
            for cell in evidence.get('table_cells', []) if isinstance(evidence.get('table_cells'), list) else []:
                if not isinstance(cell, dict):
                    unresolved += 1
                    continue
                # Only reference membership is tested here. Row/column labels,
                # cell text equivalence and claim truth are NOT inferred.
                opportunities += 1
                errors += cell.get('table_id') != source['table_id']
            for span in evidence.get('text_spans', []) if isinstance(evidence.get('text_spans'), list) else []:
                if not isinstance(span, dict):
                    unresolved += 1
                    continue
                opportunities += 1
                text = paragraph_map.get(span.get('para_id'))
                # Exact supporting snippet must occur in the referenced paragraph;
                # offsets are left unscored because historical conventions vary.
                errors += text is None or not isinstance(span.get('text'), str) or not span['text'] or span['text'] not in text
        result.update(grounding_assessable=opportunities > 0, grounding_errors=errors,
            grounding_opportunities=opportunities, grounding_unresolved_claims=unresolved,
            grounding_rate=errors / opportunities if opportunities else None,
            grounding_flag=(errors > 0) if opportunities else None,
            grounding_metric='table_id_membership_and_exact_paragraph_snippet_proxy')
        return result, source
