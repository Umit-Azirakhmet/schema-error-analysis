# Manual annotation guide and team checklist

We are checking whether the detector agrees with human judgments about five error
families. Read each response against its prompt, available schema, gold answer
and evidence. Record your own judgment before seeing automatic labels or another
reviewer's answers.

**Every column asks whether an error is present. `yes` means an error;
`no` means no error; `not-assessable` means there is not enough information.**
Fill all five columns. Multiple errors can occur in the same response.

## Files and workload

Paths below are relative to the repository root.

| File in `reports/eacl_revision/` | Who uses it | Purpose |
|---|---|---|
| `annotation_sample.csv` | Annotators | Response, prompt, gold, available schema and blank labels |
| `annotation_key.csv` | Coordinator only | Source joins, sampling strata, weights and double-review assignments |
| `adjudicated_labels_template.csv` | Coordinator and adjudicator | Blank final-label template |
| `normalized_errors.csv` | Coordinator only, after human judgments are frozen | Detector predictions for evaluation |

The current sample has 230 distinct responses: 180 balanced examples (five per
dataset/model/prompting condition) and 50 targeted challenge examples. Independently
double-review 122 responses: 72 balanced and all 50 challenge examples. The other
108 receive one review. This is 352 response reviews total, with five labels per
review. Two annotators can review 176 responses each if single-review rows are
split evenly. With more teammates, distribute the same assignments while ensuring
two different people review every overlap row.

Challenge examples help find defects. Keep them separate from balanced examples
when estimating population performance. Annotators should not see sample type.

## Coordinator setup checklist

- [ ] Choose a coordinator, annotators and an adjudicator. Prefer an adjudicator
  who did not provide the disputed judgments when staffing allows.
- [ ] Copy the four files above and this guide into a dated, frozen study folder.
  Work in that copy: rerunning the analysis pipeline regenerates the originals.
- [ ] Keep the key and detector reports private to the coordinator. Give each
  annotator only assigned source rows and this guide.
- [ ] Keep a private assignment log with `annotation_id`, first reviewer, second
  reviewer where required, and submission status. Use the key's `double_annotate`
  field to select the overlap; do not choose it based on convenience or difficulty.
- [ ] Assign all 230 responses once and all 122 overlap responses to a second
  person. Spread work across the private sampling strata.
- [ ] Use separate files or access-controlled sheets for independent reviewers.
  Give both reviewers identical source material for overlap rows.
- [ ] Preserve IDs as text and all source columns unchanged. Reviewers edit only
  the five label columns and `notes`. Keep their names in the private assignment
  log rather than changing the evaluator's column names.
- [ ] Import CSV into the editor instead of pasting comma-separated text. Check
  that multiline JSON and prompts remain inside their original cells. Export
  UTF-8 CSV with the original headers.
- [ ] Calibrate on a few practice examples outside the evaluation sample where
  possible. Discuss ambiguity, agree on the rules below, and date the protocol.
- [ ] If evaluation examples are discussed during practice, record that exposure.
  Do not count discussed judgments as independently blinded agreement evidence.

## Annotator checklist for every assigned response

1. Read the prompt: identify the requested answer, format and source evidence.
2. Read the entire raw response. Identify the intended answer JSON and any
   surrounding prose/fences. Do not confuse prompt examples or evidence objects
   with the model's answer.
3. Judge completion and syntax independently.
4. Check schema compliance only against an actual supplied schema.
5. Compare content with the gold and evidence: check meaning, numbers, units,
   claims, references and aligned table cells.
6. Fill all five labels with exactly `yes`, `no`, or `not-assessable`.
7. Explain every `yes`, every `not-assessable`, and difficult `no` in `notes`.
   Give a field/path and an evidence reference where possible.
8. Save your independent judgment. Discuss evaluation rows only after both
   first-pass submissions are frozen.

A local JSON parser may check syntax without repair. Do not repair JSON, fill
missing values, or ask an LLM to supply labels for this human annotation study.

## Label definitions

| Column | `yes` means | `no` means | Use `not-assessable` when |
|---|---|---|---|
| `completion` | Output clearly stops before finishing | Output is finished, even if factually or syntactically wrong | You cannot tell whether it stopped early or intentionally ended |
| `syntax` | Intended JSON is malformed, or there is no JSON answer | Intended JSON parses without editing; `{}` and `[]` are valid | The intended answer cannot be identified reliably |
| `envelope_contamination` | Prose, code, fences or other material surrounds the intended JSON | Only intended JSON and whitespace are present | The intended answer boundary cannot be established |
| `schema_non_conformance` | Parseable intended JSON violates the supplied schema | Parseable intended JSON satisfies the supplied schema | No authoritative schema exists, JSON cannot be parsed, or the schema cannot be interpreted reliably |
| `content_fidelity` | An assessable answer has a substantive error, unsupported claim, wrong reference/value, or missing required task content | The assessable answer is substantively correct, including acceptable paraphrases | No parseable JSON answer exists, necessary evidence is missing, or correctness cannot be resolved |

Under this protocol, schema and content labels require a parseable intended JSON
answer. Note identifiable mistakes in malformed responses separately; those
partial observations do not establish a full schema or content judgment.
Uncertainty is `not-assessable`, not `no`.

Completion rules:

- A cut-off string or an abandoned requested section supports `yes`. Length or
  reaching a token limit alone does not establish an unfinished response.
- A trailing comma in an otherwise finished object is a syntax error; it does
  not by itself establish a completion error.
- A polished wrong answer is not automatically unfinished. A deliberately empty
  object is syntactically complete; assess missing task content separately.
- For blank output or ambiguous refusal/prose-only cases without clear evidence
  of interruption, use `not-assessable` and explain why.

Syntax and envelope rules:

- Judge the intended JSON after allowing removal of outer prose or matched
  fences, without repairing inner quotes, commas, escapes or values.
- Fenced valid JSON has `syntax=no`, `envelope_contamination=yes`.
- Fences or code words inside a valid JSON string are part of its value and do
  not constitute envelope contamination.
- Two-part NL-to-format prompts intentionally request prose. Still label the
  literal raw envelope `yes` and note `prompt_requested_prose`. This does not
  automatically mean the model disobeyed the prompt.
- Do not select a complete nested child to hide a truncated parent. If several
  plausible answer candidates remain, explain the ambiguity.

Schema rules:

- Required fields come from the schema, not the gold example. Do not invent a
  schema from familiar dataset structure.
- This archive has no recovered supplied ARQA or SchemaToJSON schemas. Label
  their schema family `not-assessable` unless the coordinator obtains
  authoritative schemas and documents a protocol update.
- Missing external schema references also require `not-assessable` if they
  prevent a reliable judgment.

Content rules:

- Accept paraphrases that preserve required meaning. Exact wording is not the
  criterion for ARQA free-text answers.
- Check numbers, sign, units, dates and entities. Do not introduce an unagreed
  numerical tolerance; refer borderline equivalence for adjudication.
- ARQA: check answers and claims against supplied paragraphs/tables and evidence
  references. Gold wording alone does not override contradictory source evidence.
- DeepJSONEval: check whether JSON values reflect the supplied text; valid schema
  does not establish correct content.
- SchemaToJSON: align records by cell coordinates before comparing values and
  attributes. Do not assume position in a list alone identifies a cell.
- Object key order is irrelevant. Determine whether array order matters from
  the task/schema. Missing required task content may be a content error even if
  JSON parses; multiple family labels may apply.
- If essential evidence is absent, alignment is ambiguous, or gold and evidence
  conflict, mark unresolved correctness `not-assessable` and explain the issue.

## Examples

These are illustrative examples, not study labels.

| Situation | Label or action |
|---|---|
| Gold says “Revenue increased by 10%”; response says “Revenue rose ten percent,” supported by evidence | `content_fidelity=no`; assess other families separately |
| Complete valid JSON reports 12% where evidence requires 10% | `completion=no`, `syntax=no`, `content_fidelity=yes` |
| Response stops at `{"answer": "Revenue increased` | `completion=yes`, `syntax=yes`, schema/content `not-assessable` |
| Finished response is `{"answer": 10,}` | `syntax=yes`; trailing comma alone does not establish a completion error; schema/content `not-assessable` |
| Valid answer JSON is inside an outer code fence | `syntax=no`, `envelope_contamination=yes`; assess schema/content normally |
| Response is `{}` and an actual supplied schema requires `answer` | `completion=no`, `syntax=no`, `schema_non_conformance=yes`; content depends on the task |
| Valid JSON has no supplied schema | Schema `not-assessable`; content may still be assessable from evidence |

Suggested note: `content_fidelity: claims[1].value is 12; table row X shows 10.
schema_non_conformance: no supplied schema.` Keep notes short and specific.

## Annotator submission checklist

- [ ] Every assigned ID appears exactly once.
- [ ] All five labels contain an allowed value.
- [ ] Errors and uncertainties have notes; source columns are unchanged.
- [ ] Judgments were independent of other reviewers and the detector. Any
  accidental exposure to prior labels is disclosed.
- [ ] The coordinator has an immutable UTF-8 first-pass CSV named with reviewer
  ID, date and protocol version.

## Agreement and adjudication checklist

- [ ] Coordinator checks IDs, duplicates, labels, notes and assignment coverage.
- [ ] Combine independent overlap submissions into `overlap_a.csv` and
  `overlap_b.csv`, each containing the same 122 IDs and standard label columns.
  Retain actual reviewer identities and A/B assignment in the private log.
- [ ] Freeze these first-pass files before discussion. Agreement uses independent
  judgments, never the resolved labels.
- [ ] Compare each family on every overlap row, including disagreements involving
  `not-assessable`.
- [ ] Review disagreements using prompt/evidence and this guide. An adjudicator
  resolves remaining disputes; the detector is not the tie-breaker.
- [ ] Keep an adjudication log: ID, family, original labels, final label, reason,
  adjudicator and date. Leave genuinely unresolved cases `not-assessable`.
- [ ] Fill a copy of the final template named `adjudicated_labels.csv`, covering
  all 230 IDs. Carry forward singly reviewed labels while retaining their
  single-review status in the study record.
- [ ] If a decision rule changes, version it and revisit all affected rows.
  Preserve original first-pass labels for agreement reporting.
- [ ] Report agreement separately for the 72 balanced overlap rows and 50
  challenge rows. Combined agreement is supplementary, with composition stated.
  The evaluator does not split agreement by sample type automatically.

## Evaluation and handoff

From the repository root, install `analysis/requirements.txt`. The existing
workspace installation additionally needs
`$env:PYTHONPATH = "$PWD/.revision-deps"` in PowerShell.

Replace `PATH_TO_FROZEN_STUDY` with the folder containing the matching key,
detector report, completed final labels and overlap submissions:

```powershell
python -m validation.evaluate_annotations --reports "PATH_TO_FROZEN_STUDY" --labels "PATH_TO_FROZEN_STUDY/adjudicated_labels.csv" --annotator-a "PATH_TO_FROZEN_STUDY/overlap_a.csv" --annotator-b "PATH_TO_FROZEN_STUDY/overlap_b.csv"
```

This writes `detector_validation_metrics.csv` and `annotator_agreement.csv`.
For separate balanced/challenge agreement, subset both overlap files using the
private key and rerun. Keep the complete final labels and key for detector
scoring. Rename/save the agreement output after each run; repeated evaluation
overwrites the same output filenames.

Scores include per-family precision, recall, F1, support and unassessable counts;
balanced population estimates use sampling weights and challenge results are
separate. Agreement includes all three states and Cohen's kappa. Unassessable
automatic/human cases are excluded from binary performance scores and counted
separately. Inspect those exclusions before interpreting scores.

Content scoring compares human meaning judgments with an automatic strict
gold-match proxy. A mismatch may reveal that the proxy rejects acceptable
paraphrases; it is not evidence that the human judgment must be wrong.

Final handoff checklist:

- [ ] Frozen source files, detector snapshot and dated guide.
- [ ] Assignment log and untouched first-pass submissions.
- [ ] Overlap A/B files and separate agreement summaries.
- [ ] Adjudication log and complete final labels.
- [ ] Detector metrics, exclusions, rare-family support and systematic defects.
- [ ] Methods notes: reviewer count/expertise, calibration, blinding, single and
  double-review counts, adjudication, sampling and limitations.

Fix systematic detector defects and rerun versioned analyses before final paper
claims. Preserve the original study snapshot and independent agreement labels.
