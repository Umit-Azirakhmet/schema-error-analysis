# Independent agent review protocol

## Scope and status

The study owner replaced the proposed human annotation workstream with independent
agent review. This is a model-based detector audit. It does not establish human
validation, human inter-annotator agreement, or independently measured semantic
ground truth. Separate reviewers can still share a model and systematic biases.

The prior manual checklist and its Word export remain historical alternatives.
Existing `annotator_a.csv`, `adjudicated_labels.csv`, validation metrics and
`Phase7_Adjudication_Brief.docx` are preserved but are not evidence that this new
two-agent review has been completed. Their label authorship is not established
by their filenames. New review artifacts live in `reports/eacl_revision/agent_review/`.

## Review design

1. Give fresh agents only `annotation_sample.csv` and the decision rules.
   Do not provide earlier labels, detector implementation, annotation key,
   automatic reports or either reviewer's judgments.
2. Obtain two independent reviews of all 230 responses and all five families.
   Reviewer A covers all rows. To reduce elapsed time, reviewers B and C split
   the second pass: B covers A0000-A0099 and C covers A0100-A0229. Neither sees
   A's judgments or the other's work. The sample comprises 180 balanced and
   50 targeted challenge examples.
3. Allow strict JSON parsing and an independent general JSON Schema validator
   for objective checks. Semantic judgments must inspect source material rather
   than reproduce detector heuristics or use gold inequality as an error label.
4. Preserve each first-pass CSV and source hash before comparison. Record reviewer
   identity, actual model if exposed, source availability, tools and limitations.
   Never invent distinct model identities. Report process independence separately
   from model diversity.
5. Compare the five labels per row and report agreement separately for balanced
   and challenge samples. Agreement with another agent is not proof of correctness.
6. Send disagreements to a fresh adjudicating agent with the source and frozen
   reviewer rationales, but without detector predictions. Preserve all conflicting
   labels and the resolution. Unresolved judgments remain `not-assessable`.
7. Score the detector against the resolved agent reference, clearly naming the
   reference as agent-generated. Use balanced sampling weights for population
   summaries; challenge results are diagnostic only. Report eligible sample sizes
   and all unassessable counts alongside agreement/precision/recall/F1.

The reproducible coordinator commands are `python -m
validation.compare_agent_reviews prepare` once all first-pass files are frozen,
then `python -m validation.compare_agent_reviews finalize` after adjudication.
Preparation verifies review/source hashes, freezes the matching sample, key and
detector report under `agent_review/inputs/`, and writes a disagreement packet
without detector predictions. Finalization preserves agreed labels, resolves
only disputed labels, and writes separately named inter-agent and agent-reference
metrics. These commands never overwrite the earlier human-named label artifacts.

## Labels and evidence

`yes` means an error, `no` means no detected error, and `not-assessable` means
insufficient evidence. Record all five families independently with concise notes.

- Completion: distinguish a response that stops mid-output from an answer that
  finishes with malformed delimiters or wrong facts. Length alone is insufficient.
  An unclosed delimiter alone is also insufficient. Require evidence of an
  interrupted token/value/field or visibly abandoned semantic section for `yes`;
  ambiguous unfinished-versus-malformed parents are `not-assessable`. Blank and
  ambiguous prose/refusal cases can be unassessable. This clarification was sent
  to all reviewers before their first-pass files were frozen.
- Syntax: assess the intended full JSON answer without repairing it. Outer prose
  and fences can be separated. A complete nested child in an unfinished parent,
  or an intermediate dictionary in a Python program, is not the intended answer.
- Envelope: assess literal material outside the intended JSON, including prose
  intentionally requested by two-part prompting. Do not detect code words inside
  JSON values as surrounding contamination.
- Schema: validate only against an available authoritative schema. Never infer a
  schema from gold. Python-repr schema cells may be decoded with `ast.literal_eval`,
  never `eval`. Missing/unresolvable schemas are unassessable.
- Content: accept justified paraphrases; evaluate numbers, units, references,
  source evidence and coordinate-aligned parsed cell records. Case changes or
  moved fields are not universally equivalent. SchemaToJSON's embedded record
  strings can be semantically equivalent despite whitespace differences. Missing
  prompts/evidence must restrict conclusions; an unequal gold value alone does
  not establish a semantic error. Unparseable intended JSON is content-unassessable.
  A genuine contradiction between response assertions with the same scope, units
  and time can support an error without external evidence; different scopes or
  numbers alone cannot. Citation offsets may refer to an original paragraph
  rather than an included snippet, so snippet-length differences alone are not
  sufficient without the relevant source/convention. This evidence clarification
  was recorded during adjudication; frozen first-pass judgments are preserved.

The sample lacks prompts for many rows. Report that limitation explicitly and
do not silently reconstruct original prompts or evidence from the gold answer.

## Manuscript wording

After both passes and resolution are actually complete, describe the procedure
as a blinded independent LLM-agent audit. State sample composition, agent/model
identities as available, blinding, tools, missing evidence and adjudication rules.
Name agreement as inter-agent agreement and performance as agreement with an
agent reference. Retain the limitation that no human validation was performed.

The latest local ACL draft inspected does not claim that this detector was human
validated. An older NeurIPS draft contains a TODO requesting human annotators;
replace that proposed task with the actual agent-audit method. Preserve the
explicit lack-of-human-validation limitation wherever applicable.
