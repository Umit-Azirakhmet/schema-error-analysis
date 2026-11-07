import json
import hashlib
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from analysis.common import FAMILIES
from validation.compare_agent_reviews import prepare, finalize
from validation.evaluate_annotations import evaluate


class AgentReviewTests(unittest.TestCase):
    def test_only_disputed_labels_are_resolved(self):
        with tempfile.TemporaryDirectory() as temp:
            reports = Path(temp)
            directory = reports / 'agent_review'
            directory.mkdir()
            first = pd.DataFrame([dict(annotation_id=identity, notes='Independent first review',
                **{family: 'no' for family in FAMILIES}) for identity in ['A0000', 'A0001']])
            second = first.copy()
            second.loc[0, 'completion'] = 'yes'
            first.to_csv(directory / 'reviewer_a.csv', index=False)
            second.iloc[:1].to_csv(directory / 'reviewer_b.csv', index=False)
            second.iloc[1:].to_csv(directory / 'reviewer_c.csv', index=False)
            pd.DataFrame({'annotation_id': ['A0000', 'A0001'], 'raw_response': ['{}', '{}']}).to_csv(
                reports / 'annotation_sample.csv', index=False)
            key = pd.DataFrame(dict(annotation_id=['A0000', 'A0001'], run_id=['r', 'r'],
                row_id=['1', '2'], sample_type=['balanced', 'challenge'], sampling_weight=[2, None]))
            key.to_csv(reports / 'annotation_key.csv', index=False)
            automatic = pd.DataFrame(dict(run_id=['r', 'r'], row_id=['1', '2'],
                **{family + '_flag': [False, False] for family in FAMILIES}))
            automatic.to_csv(reports / 'normalized_errors.csv', index=False)
            source_hash = hashlib.sha256((reports / 'annotation_sample.csv').read_bytes()).hexdigest()
            for name in ['reviewer_a', 'reviewer_b', 'reviewer_c']:
                provenance = dict(source_sha256=source_hash,
                    review_csv_sha256=hashlib.sha256((directory / f'{name}.csv').read_bytes()).hexdigest())
                (directory / f'{name}_provenance.json').write_text(json.dumps(provenance))
            self.assertEqual(prepare(reports), (1, 1))
            packet = json.loads((directory / 'adjudication_packet.jsonl').read_text())
            self.assertEqual(packet['disputed_families'], ['completion'])
            self.assertNotIn('automatic', packet)
            adjudicated = first.iloc[:1].copy()
            adjudicated.loc[0, 'completion'] = 'not-assessable'
            # An adjudicator cannot silently change an agreed label.
            adjudicated.loc[0, 'syntax'] = 'yes'
            adjudicated.to_csv(directory / 'adjudicator.csv', index=False)
            metadata = finalize(reports)
            result = pd.read_csv(directory / 'agent_reference_labels.csv')
            self.assertEqual(result.loc[0, 'completion'], 'not-assessable')
            self.assertEqual(result.loc[0, 'syntax'], 'no')
            self.assertIn('not_human_validation', metadata['status'])
            self.assertTrue((directory / 'inter_agent_agreement.csv').exists())

    def test_missing_automatic_rows_fail_instead_of_disappearing(self):
        labels = pd.DataFrame(dict(annotation_id=['A'], **{f: ['yes'] for f in FAMILIES}))
        key = pd.DataFrame(dict(annotation_id=['A'], run_id=['r'], row_id=['1']))
        automatic = pd.DataFrame(dict(run_id=['r'], row_id=['2']))
        with self.assertRaisesRegex(ValueError, 'missing keyed'):
            evaluate(labels, key, automatic)


if __name__ == '__main__':
    unittest.main()
