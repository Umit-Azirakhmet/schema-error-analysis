# TTD for agent review and the paper

Engineering code and offline outputs are reviewable on `codex/eacl-revision`.
The study owner replaced human validation with independent agent review. The
following work remains pending unless explicitly marked complete. Do not describe
agent labels or inter-agent agreement as human validation.

- [x] Complete two blinded agent passes on all 230 sampled responses; freeze both
  files, adjudicate disagreements with a fresh agent and preserve provenance under
  `agent_review/`. Report inter-agent agreement, agent-reference performance,
  eligibility, rare-family support, shared-model limitations and sampling weights.
  Existing single-pass files do not establish human validation or a second review.
- [x] Apply detector corrections supported by the agent audit, especially semantic
  completion versus delimiter defects and intended-answer extraction from Python
  wrappers. Rerun versioned offline analyses and score them against the frozen
  agent reference without regenerating/overwriting the audit sample.
- [x] Audit structural completion rules against independently reviewed completion labels.
  Decide whether balanced malformed or no-candidate responses can be adjudicated
  as complete; keep unknowns explicit until then.
- [x] Add supported ARQA source-grounding diagnostics with question/gold-verified
  current dataset context. They are limited reference/snippet checks, not full
  semantic accuracy. Frozen uncertain agent labels remain unchanged.
- [ ] Resolve the remaining ARQA semantic-content uncertainty, including acceptable paraphrases
  and evidence fidelity. Current automated content rates use strict gold equality;
  do not call them human-validated task accuracy.
- [x] Separate formal JSON Schema validity (DeepJSONEval) from ARQA template and
  SchemaToJSON record-grammar conformance. Current and older local CSVs contain
  no schemas for the latter two. Inspect historical prompts and upstream task
  specifications; any newly formalized schemas must be labeled retrospective,
  not supplied to the original models. Keep unsupported schema stages unassessable.
- [x] Audit historical ARQA evidence examples: no malformed arrays in 112 checked
  template-snapshot occurrences or 20,894 occurrences in 3,210 stored prompts.
  Another 3,210 archived ARQA prompts are absent; their exact text is unverified.
- [x] Audit token-budget hits and shared NL-to-format budget; prepare replacement
  wording for the unsupported sufficient-capacity claim. Exact gold token fit
  remains unverified without model tokenizer snapshots.
- [x] Research STED and prepare citation/positioning in `sted_reference.bib` and
  `sted_positioning.md`; integration into manuscript remains below.
- [x] Qwen rerun decision audited in chat `01a1aef7-ac62-7d70-a6eb-3628cb406fab`.
  The audit supports treating final runs as configured non-thinking and found no
  tags in all 3,894 final Qwen responses. No regeneration is justified solely by
  thinking mode. Effective per-run settings were not logged; retain that caveat.
- [ ] Select and justify primary hypotheses before any new confirmatory study.
  Current retrospective characteristic/outcome tests are marked exploratory.
- [x] Review the DeepJSONEval few-shot contrasts in `v2/prompting_effects.csv` by
  family and normalized outcome, including eligible/paired N and CIs. State
  whether the previously reported effect persists instead of relying on raw counts.
- [ ] Incorporate the model- and family-specific prompting results and their
  paired-eligibility Ns/CIs into the manuscript; do not present a uniform effect.
- [ ] Revise methods to define all eligibility rules, units of opportunity,
  denominator scope, proxy content outcomes, completion rules, schema provenance,
  paired resampling, condition confounding and multiple-comparison treatment.
- [ ] Revise results and figures from the corrected benchmark-specific outputs;
  demote total-errors and prior Pearson/raw-count figures to sensitivity material.
  Describe unconditional detected versus eligible prevalence and ARQA unknowns.
- [ ] Report envelope-cleaning as a paired deterministic ablation; distinguish raw
  JSON compliance from intentional two-part NL-to-format prompting.
- [ ] Update abstract, discussion, limitations and conclusions after agent review
  and necessary detector corrections/reruns. Keep claims association-only and
  explicitly state that no human validation was performed. Replace the older
  NeurIPS appendix TODO requesting human annotators with the actual agent audit.
