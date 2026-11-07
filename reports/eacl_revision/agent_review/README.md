# Independent agent audit results

The agent audit is complete for the frozen 230-response sample. Every response
received two independent first-pass judgments on five families. Reviewer A
reviewed all 230; B reviewed A0000-A0099 and C reviewed A0100-A0229. A fresh
adjudicator reviewed all 67 disputed labels across 67 responses. The first-pass
agents did not see detector predictions or other reviewers' labels; adjudication
used source material and frozen rationales without detector predictions.

This is not human validation. Exact serving model snapshots were unavailable,
model diversity is not established, and agents may share systematic biases.
Precision, recall and F1 here compare the detector with an agent reference,
not independently established human ground truth.

## Independent agreement before adjudication

| Family | Balanced agreement out of 180 | Challenge agreement out of 50 |
|---|---:|---:|
| Completion | 95.6% | 86.0% |
| Syntax | 100.0% | 100.0% |
| Envelope contamination | 100.0% | 98.0% |
| Schema non-conformance | 100.0% | 100.0% |
| Content fidelity | 75.6% | 86.0% |

These are three-state agreements and include agreement on `not-assessable`.
For example, 131 of 180 balanced schema judgments are jointly unassessable;
only 49 balanced schema rows are jointly assessable. The detailed CSV also
reports Cohen's kappa, jointly assessable N, jointly unassessable N and agreement
restricted to jointly assessable cases. Challenge results are not population
estimates: challenge examples were selected from detector-positive cases.

## Resolved reference labels

| Family | Error | No error | Not assessable |
|---|---:|---:|---:|
| Completion | 11 | 218 | 1 |
| Syntax | 55 | 175 | 0 |
| Envelope contamination | 133 | 97 | 0 |
| Schema non-conformance | 26 | 32 | 172 |
| Content fidelity | 85 | 30 | 115 |

The source sample lacks prompts for 137 responses and supplied schemas for 153.
All rows were reviewed, but the audit cannot substantiate semantic correctness
for every row. Missing evidence is retained as uncertainty rather than converted
to an error-free label. Genuine response-internal arithmetic/unit contradictions
can establish a content error without external evidence; gold mismatch alone
cannot. Citation offsets need their original source context for reliable checking.

Adjudication resolved the 67 disputed labels as 5 errors, 15 no-errors and 47
unassessable judgments. Original independent labels and disagreement records are
preserved; agreement was not recomputed from adjudicated labels.

## Detector implications

On the unweighted balanced subset, relative to this agent reference:

- Completion precision is 0.25 on 176 mutually assessable rows. Unclosed
  delimiters should not automatically be treated as semantic cutoffs.
- Syntax recall is 0.625 on 180 rows. Intended-answer extraction requires further
  review, particularly Python programs that contain parseable interior objects.
- Envelope precision is approximately 0.981 and recall 1.0 on 180 rows.
- Schema agreement is exact on 49 mutually assessable balanced rows. This is
  limited DeepJSONEval evidence, not validation of absent ARQA/SchemaToJSON schemas.
- Content precision is approximately 0.821 on 98 mutually assessable balanced
  rows. This evaluates the strict gold-match proxy only where the agent reference
  could judge content; it does not establish semantic accuracy on excluded rows.

See the metrics CSV for weighted balanced estimates, challenge diagnostics,
support and exclusions. High sampled recall does not prove corpus-wide recall,
an error bound or an upper bound on semantic incompleteness.

The detector was not patched and corpus analyses were not rerun as part of this
agent audit. Those are subsequent implementation tasks. Existing human-named
files in the parent directory and the prior Phase7 brief are not this audit's
reference or proof of human annotation.

## Files and reproducibility

- `reviewer_a.csv`, `reviewer_b.csv`, `reviewer_c.csv`: frozen independent labels.
- Matching reviewer provenance JSONs: scope, source hash, tools, model limitations.
- `disagreements.csv`: all disputed fields before adjudication.
- `adjudication_packet.jsonl`: source and frozen reviewer rationales, without
  detector predictions. Partial/remaining packets record the incremental handoff.
- `adjudicator.csv` and provenance: resolutions and evidence rationales.
- `agent_reference_labels.csv`: agreed labels plus resolutions of disputed fields.
- `adjudication_log.csv`: field-level original/resolved labels and rationales.
- `inter_agent_agreement.csv`: independent agreement by sample type and family.
- `detector_vs_agent_reference_metrics.csv`: explicitly agent-reference scores.
- `inputs/`: frozen source sample, private key and detector-v1 report used to score.
- `audit_manifest.json`: scopes, hashes and limitations.

Coordinator commands, from the repository root with analysis dependencies loaded:

```powershell
python -m validation.compare_agent_reviews prepare
python -m validation.compare_agent_reviews finalize
```

Preparation rejects changed reviewer/source hashes or changed frozen inputs.
Finalization changes only disputed family labels and scores against the frozen
detector report. Keep the study snapshot intact when patching/rerunning analyses.
