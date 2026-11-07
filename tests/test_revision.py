import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from scripts.Error_detector import GeneralErrorDetector, ALL_ERROR_COLUMNS
from scripts.error_taxonomy import FAMILY_LEAVES, LEAF_FAMILY
from scripts.opportunity_metrics import evaluate, metric, paths, strict_parse
from analysis.association_analysis import clustered_ci, bh_adjust
from analysis.cleanup_ablation import conditions
from analysis.conditional_reliability import funnel
from analysis.common import paired_effect, load_metrics
from analysis.build_dataset import build
from validation.evaluate_annotations import validate_labels, agreement


class DetectorTests(unittest.TestCase):
    def detect(self, raw, **extra):
        return GeneralErrorDetector().detect(dict(raw_response=raw, dataset='DeepJSONEval',
            gold_json_raw='{"a": 1}', schema={'type': 'object', 'required': ['a'],
                'properties': {'a': {'type': 'integer'}}}, **extra))

    def test_taxonomy_covers_every_leaf_once(self):
        self.assertEqual(set(ALL_ERROR_COLUMNS), set(LEAF_FAMILY))
        self.assertEqual(len(ALL_ERROR_COLUMNS), sum(map(len, FAMILY_LEAVES.values())))

    def test_empty_valid_but_schema_invalid(self):
        for text in ['{}', '[]']:
            result = self.detect(text)
            self.assertTrue(result['valid_parse'])
            self.assertTrue(result['schema_non_conformance_flag'])
            self.assertEqual(result['missing_gold_scalar_paths_errors'], 1)

    def test_absent_and_malformed_are_unassessable(self):
        for text in ['', 'no answer', '{"a":', '{"a": 1,}']:
            result = self.detect(text)
            self.assertFalse(result['valid_parse'])
            self.assertIsNone(result['missing_fields_count'])
            self.assertIsNone(result['schema_non_conformance_flag'])
            self.assertIsNone(result['content_fidelity_flag'])
            self.assertTrue(result['syntax_flag'])

    def test_fences_separate_from_syntax(self):
        result = self.detect('```json\n{"a": 1}\n```')
        self.assertTrue(result['valid_parse'])
        self.assertFalse(result['raw_valid_parse'])
        self.assertTrue(result['envelope_contamination_flag'])

    def test_prose_and_fences_inside_values_are_not_envelope(self):
        self.assertFalse(self.detect('{"a":"print(hello) ```json"}')['envelope_contamination_flag'])

    def test_wrong_value_schema_valid(self):
        result = self.detect('{"a": 2}')
        self.assertTrue(result['schema_valid'])
        self.assertTrue(result['content_fidelity_flag'])
        self.assertEqual(result['wrong_value_rate'], 1)

    def test_missing_gold_not_invented(self):
        result = GeneralErrorDetector().detect({'raw_response': '{}'})
        self.assertFalse(result['is_content_assessable'])
        self.assertFalse(result['is_schema_assessable'])

    def test_completion_not_token_limit_alone(self):
        result = self.detect('{"a": 1}', output_tokens=4096)
        self.assertTrue(result['is_complete'])
        self.assertEqual(result['truncated_count'], 1)
        self.assertIsNone(self.detect('no answer')['is_complete'])

    def test_truncated_parent_never_becomes_complete_child(self):
        result = self.detect('{"a": {"nested": 1}, "b":')
        self.assertFalse(result['valid_parse'])
        self.assertFalse(result['is_complete'])
        self.assertEqual(conditions('{"a": {"nested": 1}, "b":')['complete_span'],
                         '{"a": {"nested": 1}, "b":')

    def test_scalar_json_and_nonstandard_constants(self):
        self.assertTrue(self.detect('null')['valid_parse'])
        self.assertFalse(strict_parse('NaN')[0])
        self.assertFalse(strict_parse('{"a": Infinity}')[0])


class OpportunityTests(unittest.TestCase):
    def test_paths_do_not_collide(self):
        self.assertEqual(len(paths({'a.b': 1, 'a': {'b': 2}})), 2)

    def test_nonzero_and_zero_denominators(self):
        self.assertIsNone(metric(0, 0, True)['rate'])
        self.assertIsNone(metric()['opportunities'])
        result = evaluate('{"optional": 2}', '{"optional": 1,"required":3}',
            {'type': 'object', 'properties': {'optional': {'type': 'integer'}}})
        self.assertEqual(result['missing_gold_scalar_paths_errors'], 1)
        self.assertEqual(result['missing_required_schema_fields_errors'], 0)
        self.assertEqual(result['wrong_value_rate'], .5)

    def test_bool_is_not_number(self):
        result = evaluate('{"a": true}', '{"a": 1}')
        self.assertEqual(result['gold_type_mismatch_rate'], 1)
        self.assertFalse(result['content_correct'])

    def test_constraints_and_refs(self):
        schema = {'type': 'object', 'properties': {'a': {'$ref': '#/$defs/a'}},
                  '$defs': {'a': {'type': 'integer', 'minimum': 5}}, 'required': ['a']}
        result = evaluate('{"a": 2}', '{"a": 5}', schema)
        self.assertFalse(result['schema_valid'])
        self.assertEqual(result['type_mismatch_rate'], 0)

    def test_complex_schema_no_fabricated_denominator(self):
        result = evaluate('1', '1', {'oneOf': [{'type': 'integer'}, {'type': 'string'}]})
        self.assertTrue(result['schema_valid'])
        self.assertFalse(result['type_mismatch_eligible'])

    def test_boolean_schema(self):
        self.assertFalse(evaluate('{}', '{}', False)['schema_valid'])
        self.assertTrue(evaluate('{}', '{}', True)['schema_valid'])

    def test_no_remote_schema_retrieval(self):
        result = evaluate('{}', '{}', {'$ref': 'https://invalid.example/schema'})
        self.assertFalse(result['is_schema_assessable'])

    def test_escaping_unit(self):
        result = evaluate(r'{"a":"x\q\n"}', '{}')
        self.assertEqual(result['escaping_failure_errors'], 1)
        self.assertEqual(result['escaping_failure_opportunities'], 2)
        self.assertEqual(result['escaping_failure_rate'], .5)

    def test_coordinate_alignment(self):
        gold = {'cell_index': [[1], [2]], 'cell_record': [{'value': 'a'}, {'value': 'b'}]}
        output = {'cell_index': [[2], [1]], 'cell_record': [{'value': 'b'}, {'value': 'a'}]}
        self.assertEqual(evaluate(json.dumps(output), gold)['cell_value_rate'], 0)


class AnalysisTests(unittest.TestCase):
    def test_csv_nullable_boolean_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'metrics.csv'
            pd.DataFrame({'row_id': ['001', '002', '003'],
                          'schema_non_conformance_flag': [None, True, False]}).to_csv(path, index=False)
            frame = load_metrics(path)
            self.assertEqual(frame.row_id.iloc[0], '001')
            self.assertTrue(pd.isna(frame.schema_non_conformance_flag.iloc[0]))
            self.assertEqual(frame.schema_non_conformance_flag.eq(True).sum(), 1)

    def test_cleanup_never_repairs_values(self):
        cases = conditions('Here is JSON: {"a":"```"} thanks')
        self.assertEqual(cases['raw'], cases['outer_fence'])
        self.assertEqual(cases['complete_span'], '{"a":"```"}')
        invalid = '```json\n{"a": 1}'
        self.assertEqual(conditions(invalid)['outer_fence'], invalid)
        malformed = conditions('{"a":1,}')
        self.assertFalse(strict_parse(malformed['complete_span'])[0])

    def test_funnel_retains_unknown_stage_counts(self):
        frame = pd.DataFrame(dict(dataset=['ARQA']*3, model=['m']*3, method=['z']*3,
            is_complete=[True, True, None], valid_parse=[True, True, False],
            schema_valid=[True, None, None], content_correct=[True, True, None]))
        result = funnel(frame)
        schema = result.loc[result.stage.eq('schema_valid')].iloc[0]
        self.assertEqual(schema.denominator, 2)
        self.assertEqual(schema.eligible_n, 1)
        self.assertEqual(schema.unassessable_n, 1)

    def test_clustered_ci_and_constant(self):
        frame = pd.DataFrame({'row_id': np.repeat(np.arange(10), 3), 'x': np.repeat(np.arange(10), 3)})
        frame['y'] = frame.x
        result = clustered_ci(frame, 'x', 'y', 100)
        self.assertEqual(result['input_n'], 10)
        self.assertEqual(result['n'], 30)
        self.assertAlmostEqual(result['ci_low'], 1)
        frame['y'] = 1
        self.assertTrue(np.isnan(clustered_ci(frame, 'x', 'y', 100)['rho']))

    def test_pairing_excludes_unmatched_inputs(self):
        result = paired_effect(pd.Series([0, 1], index=['a', 'b']), pd.Series([1, 0], index=['a', 'c']), 100)
        self.assertEqual(result['n'], 1)
        self.assertEqual(result['difference'], 1)

    def test_bh_preserves_missing(self):
        result = bh_adjust([.01, .04, np.nan])
        np.testing.assert_allclose(result[:2], [.02, .04])
        self.assertTrue(np.isnan(result[2]))

    def test_annotation_refuses_blank_labels(self):
        labels = pd.DataFrame({'annotation_id': ['a']})
        for family in FAMILY_LEAVES:
            labels[family] = ''
        with self.assertRaises(ValueError):
            validate_labels(labels)
        for family in FAMILY_LEAVES:
            labels[family] = 'not-assessable'
        self.assertEqual(agreement(labels, labels).agreement.iloc[0], 1)

    def test_canonical_reconciliation_and_conflicts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = root / 'archive' / 'r'
            run.mkdir(parents=True)
            manifest = dict(run_id='r', dataset='d', model='m', method='z', total_rows=2)
            (run / 'manifest.json').write_text(json.dumps(manifest))
            row = dict(row_id='a', raw_response='{}', gold_json_raw='{}')
            (run / 'responses.jsonl').write_text(json.dumps(row) + '\n' + json.dumps(row))
            records = build(root / 'archive', root / 'out', expected_conditions=1)
            self.assertEqual(len(records), 1)
            row['raw_response'] = '[]'
            with (run / 'responses.jsonl').open('a') as handle:
                handle.write('\n' + json.dumps(row))
            with self.assertRaisesRegex(ValueError, 'Conflicting generation'):
                build(root / 'archive', root / 'out', expected_conditions=1)


if __name__ == '__main__':
    unittest.main()
