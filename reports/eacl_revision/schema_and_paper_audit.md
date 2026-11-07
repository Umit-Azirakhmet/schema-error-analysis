# Schema provenance and paper wording audit

## Schema availability

All current and older local CSV headers were checked. Only DeepJSONEval files
contain a `schema` column. ARQA, ARQA_DB, ARQA raw/validated variants and all
SchemaToJSON variants do not. Archived schemas/prompts are already searched by
the canonical builder. A missing formal schema here is not necessarily a lost
artifact: the latest local ACL manuscript, section 3.1, explicitly distinguishes
DeepJSONEval JSON Schema, SchemaToJSON implicit record grammar and ARQA fixed
JSON template with grounding rules.

Inspect these sources in order:

1. The actual archived prompt for each run/response, when stored. This is the
   strongest evidence of the output specification the model received.
2. Historical `pipeline/prompts/prompts.md` and `pipeline/prompts/prompting.md`
   at the generation-era commit. Their ARQA sections define `answer`, `claims`
   and evidence structures; their SchemaToJSON sections define coordinates,
   serialized cell records and conditional record fields. Current templates may
   differ from historical ones, so do not silently substitute the latest prompt.
3. `pipeline/src/datasets/arqa.py`: `_format_schema` reads a column that the
   actual local data lacks, yielding an empty string. The SchemaToJSON loader
   supplies table/context/target cells and does not load a JSON Schema.
4. Original dataset distributions and upstream task specifications, if the team
   has them. Determine whether they define formal JSON Schema or only task rules;
   an upstream schema is not proof it was supplied during these archived runs.

Report formal JSON Schema validity for DeepJSONEval. For ARQA and SchemaToJSON,
keep schema stages unassessable or separately implement documented template/grammar
conformance. A schema formalized now is retrospective: version its rules and
report it as a new evaluation contract, not an original supplied schema. Do not
derive mandatory fields merely from a particular gold answer.

## Paper wording

Local drafts inspected in `C:/Users/pierc/Downloads/`:

- `Stress_Testing_Structured_Outputs__ACL_ (1).pdf`: no claim that detector labels
  were human validated was found. Page 2 describes an automated detector; page 8
  limitations describes automated path-level alignment. Page 3 defines explicit
  schema versus implicit grammar versus fixed-template output specifications.
- `Stress_Testing_Structured_Outputs__NeurIPS_ (1).pdf`, page 8, explicitly says
  the detector is not validated against human judgment.
- `Stress_Testing_Structured_Outputs__NeurIPS_.pdf`, page 21, has an appendix TODO
  asking for a human-annotator validation subsection and a hand-label comparison.
  Replace that planned task if that older draft is still used; it is a TODO,
  not evidence that human validation occurred. Page 10 also disclaims human validation.
- The other matching local structured-output drafts were text-searched for
  human/annotation/adjudication/agreement claims; no completed human detector
  validation claim was identified. This does not cover an unseen Overleaf revision.

After the new review finishes, describe it as an independent blinded LLM-agent
audit and report inter-agent agreement, source availability, model identity as
available, limitations and agent-reference performance. Retain an explicit
no-human-validation limitation. Do not reuse the prior Phase7 brief's human
wording or interpretation as independent human evidence.

The completed audit is in `agent_review/README.md`: two independent judgments per
response, three first-pass agents sharing the workload, and a fresh adjudicator
for 67 disputes. It remains an agent audit with incomplete source evidence, not
human validation. Detector corrections and corpus reruns remain subsequent work.
