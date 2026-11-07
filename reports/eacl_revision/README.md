# EACL offline re-evaluation

The latest corrected outputs are in [v2](v2/README.md). The root-level CSVs and
plots remain the original eacl-v1 baseline and the agent study remains frozen.
Use v2 for the next manuscript revision and read its metric/eligibility caveats.

The independent agent audit and detector-v2 corrections/rerun are complete.
Manuscript interpretation and unresolved semantic evidence remain pending. The
study owner dropped the proposed human validation workstream; agent judgments
must not be described as human ground truth. See `validation/agent_review_protocol.md`.
Archived generations and published analyses are unchanged. All results
join to `(run_id, row_id)`; each normalized row includes its source file and line.

The completed [agent audit](agent_review/README.md) contains two independent
judgments per sampled response and adjudication of all 67 disputed labels. Corpus
statistics in this root directory are the pre-correction baseline; use v2. The audit
does not substantiate content correctness on its 115 content-unassessable rows.

From the repository root, install `analysis/requirements.txt`, then run:

```powershell
python -m unittest discover -s tests -v
python -m analysis.run_revision --bootstrap 2000
```

The current local dependency installation is in `.revision-deps`. In this
workspace, set `$env:PYTHONPATH = "$PWD/.revision-deps"` before those commands.
The pipeline loads 36 conditions and 15,576 unique generations: 6,420 ARQA,
3,156 DeepJSONEval and 6,000 SchemaToJSON. It fails on conflicting primary keys,
unmatched input sets, manifest disagreement or incomplete condition coverage.
Exact repeated source records are explicitly reconciled and deduplicated.

`source_reconciliation.csv` records run counts and SHA256 source hashes.
`canonical_generations.parquet` retains raw generations, gold, characteristics,
token metadata, prompt, available schema and legacy detector columns. It is
locally generated and excluded from Git because it duplicates the large archive.
`normalized_errors.csv` contains corrected detectors, independently assessed
eligibility, leaf numerators/denominators/rates and the five reporting flags.
`analysis_manifest.json` records versions, seed, hypotheses and resample count.

DeepJSONEval and SchemaToJSON archived `characteristics` dictionaries are empty.
For consistent association analysis, gold structural features are recomputed for
all three datasets from the archived gold JSON using `gold_json_analysis.py`.
The canonical dataset stores these under `revision_characteristics`; original
characteristics remain unchanged. Normalized rows retain original values with
an `archived_characteristic_` prefix alongside the common recomputed features.

Metric definitions:

- Missing gold scalar paths: absent expected scalar paths / all gold scalar paths.
  Paths use exact key/index tuples. Null is a scalar; an embedded JSON string is
  one scalar slot. This is distinct from required fields in a JSON Schema.
- Wrong value: different comparable, same-type scalar values / all expected scalar
  slots. Omitted and wrong-type values have separate metrics; a zero wrong-value
  rate does not establish content correctness.
- Gold type mismatch: wrong types at existing expected scalar paths / comparable
  existing expected slots. Booleans are distinct from numbers.
- Missing required schema fields: absent required fields / required field slots
  on existing output objects. Nested objects that are absent are not invented.
- Schema type mismatch: wrong typed present nodes / applicable typed present
  nodes, including the root. Required/type denominator traversal supports simple
  property/item schemas and nonrecursive local references. Branching, conditional,
  dynamic-property, tuple and recursive-reference denominators are unassessable;
  full schema validation still runs. These denominators depend on output structure.
- Cell value: wrong or missing values / expected coordinate-aligned gold cells.
  Duplicate or unusable coordinate maps are unassessable. This does not reuse the
  legacy occurrence-order cell comparison as a normalized numerator.
- Escaping: invalid escape lexemes / backslash-initiated escape lexemes within
  quoted candidate strings. A Unicode escape consumes four hex characters. This
  measures lexical escaping, including malformed candidates, and does not measure
  omitted escapes. The archived `escaping_count` is never its denominator.

Every rate is null when ineligible or when its opportunity denominator is zero.
Numerators and denominators remain available for eligible zero-opportunity cases.
JSON Schema validation uses the available schema and format checker, including
constraints beyond the legacy detector. Missing/invalid/unresolvable schemas are
explicitly unassessable. Remote schema retrieval is disabled. No schema is inferred
from gold. A schema in an archived prompt is recovered without altering the source.

Each legacy leaf maps to exactly one family in `scripts/error_taxonomy.py`.
Gold-relative structure leaves remain diagnostic proxies; a mismatch with gold is
not proof of schema non-conformance. Schema family flags use full validation.
Content fidelity uses strict typed JSON gold equality and is a proxy for semantic
accuracy. The legacy backslash heuristic and other legacy diagnostics remain
visible but do not override strict syntax, schema validity or gold-match outcomes.
`total_errors` is retained only in `appendix_legacy_totals.csv`.

Completion is an explicit observable rule: generation errors, length finish
reasons, blank responses and unclosed candidates fail; parseable candidates pass;
balanced malformed spans and no-candidate prose are unknown. A token-limit count
alone does not make a parseable response incomplete. This rule needs human
validation and does not establish semantic task completion.

Candidate extraction uses the first outer object/array; it never salvages a
complete nested child from an unfinished parent. Envelope flags inspect only
surrounding material, so code words or fences inside valid JSON strings are not
mistaken for contamination. The legacy regex counts remain available separately.

`family_prevalence.csv` reports detected errors / all responses and errors /
eligible responses with both counts. Unknowns are not treated as error-free.
`prompting_effects.csv` pairs the same input IDs within dataset/model for each
method contrast. Difference is **after minus before**. Eligibility changes across
methods affect the paired subset and should be reported alongside paired N.
Families overlap, so the replacement graphics use separate prevalence bars.

`correlations_by_dataset.csv` and `correlations_bootstrap_ci.csv` contain individual
feature/outcome Spearman coefficients, eligible N, input N and 95% percentile CIs.
Bootstrap sampling copies every observation for each sampled input, preserving
model/prompt clusters. At least 90% of resamples must have a defined coefficient
to report an interval. Both pooled and within-condition associations are emitted.
Within-condition asymptotic p-values receive Benjamini-Hochberg correction across
the reported tests; pooled response-level p-values are suppressed. Associations
do not imply causality. The checked-in hypothesis list is exploratory, not a
preregistered primary analysis. Omitted heatmap cells and constant outcomes are
missing values, not zero correlations. Three benchmark heatmaps and a forest plot
use the same estimates. Prior Pearson/count figures remain archived sensitivity
material and are not used as revised headline results.

`conditional_reliability.csv` reports ARQA transition numerator, prior-stage
denominator, eligible N, unknown N, eligible conditional rate, transition rate,
and all-generation rate. An unassessable schema stage cannot be silently passed.
Use schema availability and completion validation before interpreting the funnel.

`cleanup_ablation_results.csv` evaluates strict raw parsing, matched outer-fence
removal and complete-span extraction. No JSON values are repaired. All conditions
are evaluated separately; raw parsing never uses the extraction result. Paired
condition differences are in `cleanup_ablation_deltas.csv`. Literal raw envelope
contamination includes intentionally requested NL-to-format prose, so it is not
automatically an instruction-following failure.

Annotation files include 180 balanced samples plus a distinct targeted challenge
supplement. `annotation_key.csv` is private to the study coordinator; give only
`annotation_sample.csv` to annotators. The adjudication template is intentionally
blank. Single-pass label/metric files subsequently appeared in this directory;
their filenames do not establish human authorship or independent adjudication.
Preserve them as prior artifacts. The active independent review writes separate
files under `agent_review/`; follow `validation/agent_review_protocol.md`.

The Qwen audit incorporates the completed chat audit of all 3,894 final Qwen
responses and the decision that thinking mode alone does not justify a rerun.
Code and outputs support configured non-thinking operation; effective per-run
runtime settings were not logged. Future generation manifests now capture commit, dirty status,
resolved model/tokenizer revisions, transformers version, thinking setting, chat
template and actual template arguments. No model outputs were regenerated.
