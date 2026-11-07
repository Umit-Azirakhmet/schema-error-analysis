import json
import unittest
import tempfile
import csv
from pathlib import Path
from scripts.Error_detector import GeneralErrorDetector, extract_json_candidate
from scripts.opportunity_metrics import evaluate
from analysis.cleanup_ablation import conditions
from analysis.protocol_audit import evidence_arrays
from analysis.source_evidence import EvidenceIndex


class RevisedDetectorTests(unittest.TestCase):
    def detect(self, raw, **extra):
        return GeneralErrorDetector().detect(dict(raw_response=raw, gold_json_raw='{}', **extra))

    def test_finished_broken_delimiter_is_not_cutoff(self):
        result = self.detect('{"a": {"b": 1}}]')
        self.assertFalse(result['valid_parse'])
        self.assertTrue(result['is_complete'])
        missing_root = self.detect('{"a": {"b": 1}')
        self.assertTrue(missing_root['is_complete'])
        self.assertNotEqual(missing_root['completion_rule'], 'unclosed_candidate')
        self.assertIsNone(self.detect('{"a": {"b": {"c": {"d":1}')['is_complete'])

    def test_limit_alone_and_dangling_value(self):
        self.assertTrue(self.detect('{"a":1}', output_tokens=4096)['is_complete'])
        self.assertFalse(self.detect('{"a":')['is_complete'])
        self.assertIsNone(self.detect('{"a": "some value')['is_complete'])
        self.assertFalse(self.detect('{"a": "some value', output_tokens=4096)['is_complete'])

    def test_never_accept_interior_python_dictionary(self):
        raw = 'import json\ndata = {"a":1}\nprint(json.dumps(data))'
        result = self.detect(raw)
        self.assertFalse(result['valid_parse'])
        self.assertTrue(result['is_complete'])
        self.assertIsNone(result['content_correct'])
        self.assertEqual(conditions(raw)['complete_span'], raw)
        self.assertFalse(self.detect('```python\n' + raw + '\n```')['valid_parse'])

    def test_program_markers_inside_string_are_not_code(self):
        raw = json.dumps({'a': 'import json\ndata = {"a": 1}\nprint(data)'})
        self.assertTrue(self.detect(raw)['valid_parse'])

    def test_explicit_part_two_takes_priority(self):
        raw = 'PART 1: Example {"wrong": 1}\nPART 2 - JSON Response:\n{"right": 2}'
        self.assertEqual(extract_json_candidate(raw)[0], '{"right": 2}')
        short_header = 'PART 1: Example {"wrong": 1}\nPART 2 - {"root":{"a":1}}'
        self.assertEqual(extract_json_candidate(short_header)[0], '{"root":{"a":1}}')

    def test_contract_does_not_create_formal_schema(self):
        result = GeneralErrorDetector().detect(dict(dataset='ARQA', raw_response='{}', gold_json_raw='{}'))
        self.assertIsNone(result['schema_valid'])
        self.assertFalse(result['contract_valid'])
        self.assertIsNone(result['schema_non_conformance_flag'])
        self.assertTrue(result['contract_non_conformance_flag'])

    def test_serialized_records_and_duplicate_coordinates(self):
        gold = dict(cell_index=[[1, 2, 0], [1, 2, 0]], cell_record=[
            '{"value":"2","type":"Other"}', '{"value":"3","type":"Other"}'])
        output = dict(cell_index=[[1, 2, 0], [1, 2, 0]], cell_record=[
            '{ "type": "Other", "value": "3" }', '{"value": "2", "type": "Other"}'])
        result = evaluate(json.dumps(output), json.dumps(gold), dataset='SchemaToJSON')
        self.assertFalse(result['strict_content_correct'])
        self.assertTrue(result['content_correct'])
        self.assertTrue(result['contract_valid'])
        self.assertEqual(result['cell_record_errors'], 0)
        self.assertEqual(result['cell_record_opportunities'], 2)
        output['cell_record'][0] = '{"value":"9","type":"Other"}'
        self.assertEqual(evaluate(json.dumps(output), json.dumps(gold), dataset='SchemaToJSON')['cell_record_errors'], 1)

    def test_unpaired_and_nested_records_are_contract_errors(self):
        for records in [[], [{'value': '2', 'type': 'Other'}], ['{"value":"2","type":"Other","unit":"kg"}']]:
            result = evaluate(json.dumps(dict(cell_index=[[1, 2, 0]], cell_record=records)), '{}', dataset='SchemaToJSON')
            self.assertFalse(result['contract_valid'])

    def test_actual_array_example_parsing(self):
        self.assertTrue(evidence_arrays('"table_cells": [{"table_id":"..."}]')[0]['valid'])
        self.assertFalse(evidence_arrays('"table_cells": ["table_id":"..."]')[0]['valid'])

    def test_context_recovery_requires_matching_gold(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, row in [('ARQA.csv', dict(qa_id='q', gold_answer='{"answer":"x"}',
                    question='What?', table_id='t')),
                    ('ARQA_DB.csv', dict(table_id='t', paragraphs='[{"para_id":"p","text":"source text"}]'))]:
                with (root / name).open('w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=list(row)); writer.writeheader(); writer.writerow(row)
            index = EvidenceIndex(root)
            row = dict(dataset='ARQA', row_id='q', gold_json_raw='{"answer":"x"}', raw_response=json.dumps(
                dict(claims=[dict(evidence=dict(text_spans=[dict(para_id='p', text='invented')]))])))
            result, source = index.assess(row)
            self.assertTrue(result['source_context_available'])
            self.assertFalse(result['source_context_is_original_prompt'])
            self.assertEqual(result['grounding_errors'], 1)
            row['gold_json_raw'] = '{"answer":"different"}'
            self.assertFalse(index.assess(row)[0]['source_context_available'])

    def test_unknown_string_stop_stays_unknown(self):
        self.assertIsNone(self.detect('{"text":"finished sentence.')['is_complete'])


if __name__ == '__main__':
    unittest.main()
