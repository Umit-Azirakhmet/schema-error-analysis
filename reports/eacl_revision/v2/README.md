# Detector v2 offline revision

This directory is the versioned rerun after the independent agent audit. The
original model generations, baseline reports and frozen agent study remain in
their existing locations. No model responses were regenerated.

Run from the repository root after installing `analysis/requirements.txt`:

```powershell
python -m unittest discover -s tests -v
python -m analysis.run_revision --output reports/eacl_revision/v2
```

The existing local dependency installation needs
`$env:PYTHONPATH = "$PWD/.revision-deps"` in PowerShell. The default output is now
this version directory. The runner rejects the parent directory containing the
frozen study and does not resample annotations unless explicitly requested for a
separate study. Source and code hashes are recorded in `analysis_manifest.json`.

## Completion and intended answer

Python assignments/imports/functions and executable calls are recognized without
executing them. Their intermediate dictionaries are not accepted as JSON answers.
An explicit PART 2 answer takes priority over illustrative objects in PART 1.
Complete nested children are not salvaged from unfinished parents. Extra trailing
closing delimiters are retained as syntax defects rather than stripped as prose.

Completion is a conservative observable proxy. Parseable intended answers and
syntactically complete Python programs are observably finished (a finished Python
program still fails JSON syntax). A finished terminal container with at most one
missing ancestor delimiter is classified as a finished syntax defect. Multiple
open ancestors and other ambiguous cases remain unknown. An unfinished value/item
or an unterminated string at a length limit is evidence of interruption. A limit
hit alone does not invalidate a complete answer. Blank/error cases remain unknown.
The rule does not establish whether every requested semantic fact was supplied.

Legacy `truncated_count` remains available for comparison; revised completion
family flags use `is_complete` and `completion_rule` instead. Changes in these
definitions are measurement revisions, not improved model behavior.

## Formal schema versus retrospective contract

`schema_valid` and the schema-family flag retain their formal supplied-schema
meaning. ARQA and SchemaToJSON remain schema-unassessable when no schema exists.

Separate `contract_valid`, `contract_kind`, `contract_version` and
`contract_non_conformance_flag` fields describe retrospective evaluation contracts:

- ARQA: answer/claims/evidence object structure, primitive field types,
  claim-type-specific evidence keys and nonnegative ordered span endpoints.
  Row/column labels may be strings or integer indices. Grounding is separate.
- SchemaToJSON: paired arrays, integer coordinate triples, JSON-serialized record
  strings and permitted fields/types for Other and Glass_Compound_Amount records.
- DeepJSONEval: its actual supplied JSON Schema, without substituting a new one.

These contracts are new versioned evaluation rules, not proof that formal schemas
were supplied during generation. They are separate diagnostics, not a sixth
primary reporting family. `contract_prevalence.csv` reports their own eligibility.

`conditional_reliability.csv` preserves the formal ARQA schema funnel, including
unassessable stages. `arqa_template_reliability.csv` and its graphic use the
retrospective template stage. `arqa_conditional_diagnostics.csv` reports all,
completed, completed-and-parseable, and template-valid subsets with denominators
and unknowns. Content at the final stage remains an exact-gold proxy.

## Content and recovered evidence

`strict_content_correct` preserves typed JSON gold equality. For DeepJSONEval and
ARQA, `content_correct` remains that proxy; acceptable paraphrases are not
automatically scored as semantically correct. No global case folding or arbitrary
field relocation is used to declare equivalence.

For SchemaToJSON, `content_correct` compares decoded cell records aligned by
coordinate, preserving duplicate-coordinate instances. JSON key order and
whitespace in equivalent embedded record strings do not create content errors.
The comparison is order-insensitive across paired cells; strict root array order
and serialization-format differences remain visible in the strict comparator and
contract diagnostics. `cell_record_rate` normalizes unmatched expected record
instances by expected records; extra/nonmatching output records are separate.
Use this decoded-record proxy rather than literal serialized-string differences
when discussing SchemaToJSON content. It still compares against gold, not full
semantic truth from the table.

`arqa_recovered_context.jsonl` attaches current dataset context only after matching
the question ID and typed gold JSON to the archive. This is recovered input, not a
reconstructed original prompt. `arqa_source_grounding.csv` checks only table-ID
membership and exact snippet occurrence in referenced paragraphs. It does not
validate row/column resolution, full cell values, offset conventions, answer
paraphrases or claim truth. Its eligibility and unresolved counts are explicit.
The frozen audit's 115 content-unassessable judgments are not rewritten.

## Audit and inferential limits

`detector_audit_comparison.csv` compares v1 and v2 with the same frozen agent
reference. Rules were revised after inspecting that audit, so improvements are
development/regression evidence, not held-out validation. Some metrics and
eligibility counts can worsen; report both versions and denominators. Agent
reference agreement is not human validation or independently established truth.

Dataset-specific Spearman estimates, within-condition estimates, input-cluster
bootstrap intervals, family prevalence, paired prompting differences and cleanup
ablations are regenerated. Existing exploratory hypotheses remain exploratory.
Do not interpret correlation as causal feature attribution. Paired schema/content
comparisons use the subset assessable under both methods; report its N because
syntax failure can change that subset substantially.

## Historical prompt and budget audits

`historical_prompt_examples.csv` records evidence-array checks across committed
template snapshots, including commit IDs and content hashes. Repeated examples
across snapshots are repeated checks, not independent experimental examples.
`archived_arqa_prompt_audit.csv` separates stored prompts from missing ones.
The inspected ACL (3) PDF, appendix A.2 on page 10, shows arrays containing objects;
the earlier malformed-example criticism does not apply to that current rendering.
Committed code history alone cannot prove the effective per-run checkout.

`token_budget_summary.csv` and `token_budget_records.csv` record observed output
tokens, limit hits and outcome eligibility. NL-to-format uses one shared budget
for prose and JSON. Gold character lengths are not gold token counts; no cached
model tokenizers were available to establish exact gold fit. Replace unsupported
"sufficient capacity" language with the actual shared cap and observed hit rates.

See `paper_impact.md` for measured changes and remaining manuscript actions. STED
citation and positioning notes are in the parent directory; no new paid model or
embedding calls were made.
