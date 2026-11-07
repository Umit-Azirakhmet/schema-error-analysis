# Paper impact of detector v2

The corrected offline pipeline has been run over all 15,576 archived generations
and 36 conditions. Original responses, baseline reports and frozen agent labels
are unchanged. This is a change to measurement, not new model performance.

## Counts that changed

| Dataset | N | Parseable v1 | Parseable v2 | Incomplete v1 | Incomplete v2 | Completion unknown v2 | Content proxy matches v1 | Content proxy matches v2 |
|---|---|---|---|---|---|---|---|---|
| ARQA | 6420 | 5741 | 5741 | 660 | 4 | 54 | 0 | 0 |
| DeepJSONEval | 3156 | 2671 | 2611 | 471 | 1 | 43 | 1140 | 1133 |
| SchemaToJSON | 6000 | 5382 | 4914 | 425 | 282 | 260 | 181 | 1340 |

Parseable counts concern the intended full JSON answer after candidate extraction,
not strict raw-response parsing. More Python wrappers are correctly rejected.
Completion is an observable interruption proxy with unknown states, not proof that
all semantic task content was supplied. The manuscript's legacy completion family
also included other leaves, so its percentages cannot be equated with this revised
cutoff definition. Replace or carefully relabel that column rather than claiming
models suddenly improved.

SchemaToJSON content now compares decoded, coordinate-aligned record instances.
Its large match-count change primarily reflects avoiding representation-dependent
penalties such as whitespace inside serialized JSON strings. ARQA and DeepJSONEval
retain strict typed gold-match proxies; zero ARQA exact matches is not a measured
zero semantic-accuracy result. Additional recovered ARQA source checks are separate.

## Regression against the frozen agent reference

| Family | Joint eligible v1 / v2 | Precision v1 / v2 | Recall v1 / v2 | F1 v1 / v2 |
|---|---|---|---|---|
| completion | 176 / 176 | 0.250 / 1.000 | 1.000 / 1.000 | 0.400 / 1.000 |
| syntax | 180 / 180 | 1.000 / 1.000 | 0.625 / 0.938 | 0.769 / 0.968 |
| envelope_contamination | 180 / 180 | 0.981 / 0.990 | 1.000 / 1.000 | 0.990 / 0.995 |
| schema_non_conformance | 49 / 49 | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 |
| content_fidelity | 98 / 98 | 0.821 / 0.885 | 1.000 / 1.000 | 0.902 / 0.939 |

These are unweighted balanced-sample scores, not human validation. The rules were
revised after the audit, so this is a development/regression comparison, not a
held-out performance estimate. The completion positive support is very small;
perfect sampled scores do not establish perfect corpus performance. Eligibility
changes and all remaining disagreements are retained in the CSV outputs.

## Few-shot finding

The broad claim that few-shot consistently increases one aggregate error score
should be replaced with model- and family-specific results. Differences below
are **few-shot minus zero-shot**, in percentage points. Positive values mean a
higher detected-error rate under few-shot. The existing generic contrast CSV uses
after-minus-before; the dedicated CSV reverses the sign and CI endpoints explicitly.

| Model | Outcome | Paired N | Few minus zero pp | 95% percentile CI pp |
|---|---|---|---|---|
| Qwen3-8B | syntax_flag | 263 | 71.48 | [65.78, 76.81] |
| Qwen3-8B | schema_non_conformance_flag | 75 | 14.67 | [6.67, 22.67] |
| Qwen3-8B | content_fidelity_flag | 75 | 10.67 | [1.33, 20.00] |
| gemma-3-4b-it | syntax_flag | 263 | -0.38 | [-1.14, -0.00] |
| gemma-3-4b-it | schema_non_conformance_flag | 262 | 87.79 | [83.59, 91.60] |
| gemma-3-4b-it | content_fidelity_flag | 262 | 52.29 | [45.80, 58.40] |
| Llama-3.1-8B-Instruct | syntax_flag | 263 | 56.27 | [50.19, 62.36] |
| Llama-3.1-8B-Instruct | schema_non_conformance_flag | 115 | 8.70 | [-0.00, 16.52] |
| Llama-3.1-8B-Instruct | content_fidelity_flag | 115 | 7.83 | [1.74, 14.78] |
| Mistral-7B-Instruct-v0.3 | syntax_flag | 263 | 6.46 | [-0.00, 12.93] |
| Mistral-7B-Instruct-v0.3 | schema_non_conformance_flag | 170 | 17.06 | [9.40, 24.71] |
| Mistral-7B-Instruct-v0.3 | content_fidelity_flag | 170 | 14.71 | [7.06, 22.35] |

Gemma has almost no syntax-rate change but a large conditional schema-error
increase. Qwen and Llama show large syntax increases; schema/content comparisons
for them use smaller mutually parseable subsets. Mistral's syntax interval reaches
zero at the reported precision, whereas its conditional schema/content effects
are clearer. Do not use these conditional Ns to infer unconditional semantic
failure for the outputs excluded by syntax. All effects remain retrospective
associations within the evaluated conditions.

## Prompt and token-budget findings

No malformed evidence arrays were found in 112 occurrences checked across
committed template snapshots or 20,894 occurrences in 3,210 stored ARQA prompts.
Another 3,210 ARQA prompts are absent. The current ACL (3) PDF's appendix A.2,
page 10, also shows arrays containing enclosed objects. That earlier transcription
criticism is not present in this rendering; do not invent a prompt defect or
claim missing historical prompts have been verified.

| Dataset | Zero shot cap hits / N | Few shot cap hits / N | NL to format cap hits / N |
|---|---|---|---|
| ARQA | 2 / 2140 | 1 / 2140 | 1 / 2140 |
| DeepJSONEval | 0 / 1052 | 0 / 1052 | 1 / 1052 |
| SchemaToJSON | 126 / 2000 | 174 / 2000 | 152 / 2000 |

There are 457 observed limit hits: 452 on SchemaToJSON, four on ARQA, and one on
DeepJSONEval. NL-to-format spends one shared cap on prose plus JSON. Character
lengths of gold outputs do not establish token fit, and no model tokenizer
snapshots were cached locally. Suggested replacement for the capacity claim:

> We capped total generated output at 4,096 tokens. For NL-to-format, this budget
> covers both the prose and JSON sections. Some generations reached the limit,
> especially on SchemaToJSON; the cap may therefore affect observed failure rates.

## What to change in the manuscript

- Replace old headline raw totals with the corrected family prevalence and
  normalized leaf measures; retain legacy totals only as sensitivity material.
- Replace old Pearson/Fisher-z graphics with the v2 dataset-specific Spearman and
  clustered-bootstrap outputs. The selected hypotheses remain exploratory.
- Report formal JSON Schema validity for DeepJSONEval separately from retrospective
  ARQA template and SchemaToJSON grammar conformance. Do not call retrospective
  contracts schemas supplied to the original model.
- Use the ARQA conditional diagnostic CSV for completed/parseable/template-valid
  subsets. Its content endpoint remains a gold-match proxy, not semantic accuracy.
- Keep the agent-audit limitations, support, unknowns and dependence on missing
  evidence visible. The frozen 115 content-unknown labels were not overwritten
  by the recovered current-dataset context.
- Update Figure 1's counts/association labels and the taxonomy presentation;
  domain-specific diagnostics remain subtypes of five primary families.
- Replace unsupported capacity and causal language. No model inference or
  constrained-decoding experiment was added.
- Incorporate the STED citation and related-work paragraph from the parent
  directory; no STED superiority claim or new embedding experiment was made.

All new scientific outputs are in this v2 directory. `README.md` defines the
rules and exclusions; `analysis_manifest.json` records source/code versions.
