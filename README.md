# schema-error-analysis

Fine-grained error analysis of JSON schema-guided generation across open-source LLMs and prompting strategies.

## Overview

This project investigates how and why open-source LLMs fail when generating JSON under a given schema.

The main focus is not only overall JSON validity, but also:

- which schema characteristics cause errors,
- which error types occur most often,
- how failures differ across models and prompting methods,
- whether structurally valid outputs contain the correct task answer.

Latency, token usage, and STED similarity are retained as supporting metrics rather than primary research targets.

## Research Questions

1. What types of JSON and schema-compliance errors do open-source LLMs produce?
2. Which schema characteristics are associated with higher error rates?
3. How do zero-shot, few-shot, and Natural Language → JSON generation affect error patterns?
4. Are error patterns consistent across model families?
5. How often are schema-valid outputs still semantically incorrect?

## Pipeline

```text
Datasets
├── DeepJSON
├── ARQA
└── Schema-to-JSON
        │
        ▼
Models
├── Qwen3-8B
├── Llama-3.1-8B-Instruct
├── Mistral-7B-Instruct-v0.3
└── Gemma 4E 4-bit
        │
        ▼
Generation Methods
├── Direct prompting
│   ├── Zero-shot
│   └── Few-shot
└── Natural Language → JSON
        │
        ▼
Evaluation
├── Structural correctness
│   ├── JSON validity
│   ├── Schema compliance
│   └── Field-level compliance
├── Semantic correctness
│   └── Task accuracy
└── Supporting metrics
    ├── STED similarity
    ├── Latency
    └── Token usage
        │
        ▼
Error Analysis
├── By schema characteristic
│   ├── Nesting depth
│   ├── Array depth
│   ├── Number of required fields
│   ├── Enums and constants
│   ├── References ($ref)
│   ├── Regex constraints
│   ├── oneOf / anyOf / allOf
│   ├── Escaping requirements
│   └── ...
└── By error type
    ├── Syntax and parsing errors
    ├── Truncated outputs
    ├── Missing required fields
    ├── Additional fields
    ├── Incorrect types
    ├── Incorrect nesting
    ├── Enum or constant violations
    ├── Regex or format violations
    ├── Array constraint violations
    ├── Reference or union errors
    ├── Escaping errors
    ├── Schema-valid but incorrect answers
    └── ...
```

## Datasets

- **DeepJSON**
- **ARQA**
- **Schema-to-JSON**

## Models

The project evaluates four similarly sized open-source instruction-tuned models:

- **Qwen3-8B**
- **Llama-3.1-8B-Instruct**
- **Mistral-7B-Instruct-v0.3**
- **Gemma 4E 4-bit**

Keeping models within a relatively small size range helps isolate the effects of prompting strategy and schema complexity.

## Generation Methods

### Direct Prompting

The model receives:

- the task input,
- the JSON Schema,
- an instruction to return only valid JSON.

Two settings are evaluated:

- **Zero-shot:** no solved examples.
- **Few-shot:** several input-schema-output demonstrations are included.

### Natural Language → JSON

A two-stage generation method:

1. Generate the task answer in natural language.
2. Convert that answer into the required JSON structure.

This separates task solving from formatting.

## Main Evaluation

### JSON Validity

The raw output is parsed without repair.

Examples of failures:

- invalid quotes,
- missing brackets,
- missing commas or colons,
- invalid escaping,
- extra text outside JSON,
- incomplete or truncated JSON.

### Schema Compliance

Valid JSON outputs are checked against the provided JSON Schema.

The validator records:

- whether the response is fully compliant,
- all validation errors,
- the JSON path of each error,
- the number of errors per response.

### Field-Level Compliance

Measure how many expected fields are:

- present,
- correctly typed,
- correctly nested,
- compliant with their field constraints.

### Task Accuracy

The relevant answer field is compared with the gold task answer using the dataset-specific metric.

Task accuracy is reported:

- across all outputs,
- among JSON-valid outputs,
- among schema-valid outputs.

## Error Analysis

### Schema Characteristics

Each schema is automatically annotated with features such as:

- maximum nesting depth,
- maximum array depth,
- number of properties,
- number of required fields,
- number of enums and constants,
- number of `$ref` references,
- presence of regex or format constraints,
- presence of `oneOf`, `anyOf`, or `allOf`,
- escaping requirements.

These features are connected to observed error rates.

### Error Taxonomy

Each response may contain multiple errors.

Primary categories:

1. Parser or syntax error
2. Truncated output
3. Missing required field
4. Additional unexpected field
5. Incorrect type
6. Incorrect nesting
7. Enum or constant violation
8. Regex or format violation
9. Array constraint violation
10. Reference or union violation
11. Escaping error
12. Schema-valid but incorrect answer

The complete validator error list should be preserved rather than assigning only one label.

## Supporting Metrics

These metrics provide additional context but are not the main contribution.

### STED Similarity

A structure-aware similarity score between the generated JSON and gold JSON.

STED complements strict schema validation but does not replace it.

### Efficiency

- End-to-end latency
- Output-token count
- Total token usage
- Tokens per valid response
- Tokens per valid and correct response

## Characteristics & Prompts

- Run `python scripts/analyze_characteristics.py` to build the active-column manifest (`data/active_characteristics.json`) and statistics report (`reports/characteristic_statistics_report.md`).
- Example generation prompts (zero-shot, few-shot, NL-to-Format): [`prompts/example_prompts.md`](prompts/example_prompts.md).

## Status

Work in progress.
