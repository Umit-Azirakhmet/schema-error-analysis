# Detector annotation protocol

Current study decision: use the [independent agent review protocol](agent_review_protocol.md).
The manual procedure below is retained as an alternative, not the active workstream.

For assignments, worked examples, independent review, adjudication and handoff,
use the [manual annotation team checklist](manual_annotation_checklist.md).

Review the full response, prompt, supplied schema and gold independently. Do not
open `annotation_key.csv` or automatic reports until both annotations are frozen.
Use `yes`, `no`, or `not-assessable` for each family; explain uncertainty in notes.

- Completion: unfinished task output, not simply a long response. Validate the
  automatic structural completion rule against these labels. Token-limit and
  brace heuristics alone do not establish semantic completion.
- Syntax: the extracted intended JSON is not valid JSON. Empty objects and arrays
  are valid syntax. Record absent JSON as syntax failure; mark schema and content
  not-assessable. Surrounding prose is assessed under envelope contamination.
- Envelope contamination: fences, code or prose outside the intended JSON.
  NL-to-format prompts intentionally request two parts: label the literal raw
  envelope consistently and note that prompt design explains this contamination.
- Schema non-conformance: a violation of the supplied schema. Without a supplied
  schema use not-assessable. Do not infer required fields from a gold example.
- Content fidelity: judge the answer against evidence, not just wording equality.
  Distinguish unsupported claims, wrong numbers, and incorrect cell references
  from acceptable paraphrases. Automatic strict gold matching is only a proxy.

`annotation_sample.csv` contains 180 balanced examples (five per condition) and a
separate challenge supplement. The private key identifies two examples per cell
for independent double annotation (72 balanced examples), plus every challenge
example. Give the same blind rows to a second annotator. Preserve separate CSVs
for each annotator. Discuss disagreements after independent labeling; write the
resolved labels into a copy of `adjudicated_labels_template.csv` named
`adjudicated_labels.csv`. Keep a rationale in notes. Never treat automatic labels
as adjudication. Include every keyed sample row, with explicit not-assessable as
needed, before running the evaluator.

Run `python -m validation.evaluate_annotations --labels PATH --annotator-a PATH
--annotator-b PATH` from the repository root. The evaluator reports per-family
precision, recall, F1, eligibility, three-state agreement and Cohen's kappa.
Population estimates use inverse sampling weights for the balanced strata;
challenge metrics are reported separately without population extrapolation.
Inspect excluded automatic/human unassessable counts before interpreting scores.
Patch systematic defects, rerun offline analysis, and freeze a new detector
version before making validated research claims.
