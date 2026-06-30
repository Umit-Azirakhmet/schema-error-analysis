# Example Prompts

Prompt templates for schema-guided JSON generation, adapted from [Let Me Speak Freely](https://arxiv.org/pdf/2408.02442) Appendix G.

**Universal template:**

```
Follow the instruction to complete the task: {task_description}
Instruct: {format_description}
{few_shots}
{question}
```

Three prompting methods are defined per dataset:

1. **Direct zero-shot (FRI)** — format-restricting instructions with schema in a single call.
2. **Direct few-shot (FRI)** — same as zero-shot plus in-context examples.
3. **NL-to-Format** — Stage 1: natural language only; Stage 2: convert NL response to JSON.

> **Note:** Few-shot `{example_*}` placeholders should be sampled from each dataset's CSV at generation time (not fixed in this file).

---

## ARQA

### Zero-shot (FRI)

**Task description:**

```
You are answering a financial document question. Given the question and supporting context,
produce a JSON object with fields "answer" (string), "claims" (array of claim objects),
and evidence (table_cells and/or text_spans) matching the gold structure.
```

**Format description:**

```
Return only valid JSON. No markdown fences, no commentary outside the JSON object.
Required top-level keys: "answer", "claims".
Each claim must have "type", "claim_text", and "evidence".
```

**Question (filled example, truncated):**

```
Question: Discuss the distinct roles of the Automotive Division and the Financial Services Division
in the Volkswagen Group's operations.

Context paragraphs: [VW2015_P5e55fd, ...]
Table: VW2015_T4e9153
```

**Full prompt example:**

```
Follow the instruction to complete the task: You are answering a financial document question. Given the question and supporting context, produce a JSON object with fields "answer" (string), "claims" (array of claim objects), and evidence (table_cells and/or text_spans) matching the gold structure.
Instruct: Return only valid JSON. No markdown fences, no commentary outside the JSON object. Required top-level keys: "answer", "claims". Each claim must have "type", "claim_text", and "evidence".

Question: Discuss the distinct roles of the Automotive Division and the Financial Services Division in the Volkswagen Group's operations.
Context paragraphs: [VW2015_P5e55fd]
Table: VW2015_T4e9153
```

### Few-shot (FRI)

Same as zero-shot, with examples inserted before the target question:

```
{few_shots}

Example 1 input:
{example_1_input}

Example 1 output:
{example_1_output}

Example 2 input:
{example_2_input}

Example 2 output:
{example_2_output}
```

**Filled example (truncated output):**

```
Example 1 input:
Question: What was Volkswagen Passenger Cars sales revenue in 2015?
Table: VW2015_T19a389

Example 1 output:
{"answer": "Sales revenue was €106,240 million in 2015.", "claims": [{"type": "table", "claim_text": "...", "evidence": {"table_cells": [{"table_id": "VW2015_T19a389", "row": "Volkswagen Passenger Cars", "col": "SALES REVENUE 2015", "cell_text": "106240"}]}}]}
```

### NL-to-Format

**Stage 1 — NL format description:**

```
Step by step reasoning: Explain your reasoning before giving the final answer.
Answer: The final answer is ...
```

**Stage 1 prompt (no schema):**

```
Follow the instruction to complete the task: Answer the financial document question using the provided context. Do not output JSON.
Instruct: Step by step reasoning: Explain your reasoning before giving the final answer.
Answer: The final answer is ...

Question: Discuss the distinct roles of the Automotive Division and the Financial Services Division...
```

**Stage 2 — conversion (schema / structure in prompt):**

```
Follow the instruction to complete the task: Convert the natural language answer below into the required JSON structure for ARQA claims and evidence.
Instruct: Return only valid JSON with keys "answer" and "claims". Each claim needs "type", "claim_text", and "evidence".

Natural language response:
{stage1_nl_response}

Target structure:
{
  "answer": "<string>",
  "claims": [
    {
      "type": "table" | "text",
      "claim_text": "<string>",
      "evidence": { "table_cells": [...] } | { "text_spans": [...] }
    }
  ]
}
```

---

## DeepJSONEval

### Zero-shot (FRI)

**Task description:**

```
Given a source text and a JSON Schema, generate a JSON instance that satisfies the schema
and accurately reflects the information in the text.
```

**Format description:**

```
Return only valid JSON matching the schema below. No extra keys, no markdown fences.

Schema:
{schema}
```

**Question (filled example, truncated):**

```
Text: The movie "Inception" was directed by Christopher Nolan and released in 2010. It stars Leonardo DiCaprio...

Schema:
{
  "title": "Movie",
  "type": "object",
  "properties": {
    "title": {"type": "string"},
    "director": {"type": "string"},
    "year": {"type": "integer"},
    ...
  },
  "required": ["title", "director", "year"]
}
```

**Full prompt example:**

```
Follow the instruction to complete the task: Given a source text and a JSON Schema, generate a JSON instance that satisfies the schema and accurately reflects the information in the text.
Instruct: Return only valid JSON matching the schema below. No extra keys, no markdown fences.

Schema:
{"title": "Movie", "type": "object", "properties": {"title": {"type": "string"}, "director": {"type": "string"}, "year": {"type": "integer"}}, "required": ["title", "director", "year"]}

Text: The movie "Inception" was directed by Christopher Nolan and released in 2010...
```

### Few-shot (FRI)

```
{few_shots}

Example 1:
Text: {example_1_text}
Schema: {example_1_schema}
JSON: {example_1_json}

Example 2:
Text: {example_2_text}
Schema: {example_2_schema}
JSON: {example_2_json}

Text: {text}
Schema: {schema}
```

### NL-to-Format

**Stage 1:**

```
Follow the instruction to complete the task: Read the text and extract the relevant information to answer the implicit structured-data task. Do not output JSON.
Instruct: Step by step reasoning: ...
Answer: The final answer is ...

Text: {text}
```

**Stage 2:**

```
Follow the instruction to complete the task: Convert the natural language extraction below into JSON that validates against the given schema.
Instruct: Return only valid JSON. No markdown.

Natural language response:
{stage1_nl_response}

Schema:
{schema}
```

---

## SchemaToJSON

### Zero-shot (FRI)

**Task description:**

```
Given a pipe-delimited table (`table_code`), optional supporting text (`sup_text`), and target cell coordinates,
produce `gold_json_records`: a JSON object with parallel lists `cell_index` and `cell_record` (each cell_record is a JSON string).
```

**Format description:**

```
Return only valid JSON. Record types include "Other" and "Glass_Compound_Amount" with dataset-specific required fields.

Output structure:
{
  "cell_index": [[i, j, k], ...],
  "cell_record": ["{\"value\": \"...\", \"type\": \"...\", ...}", ...]
}
```

**Question (filled example, truncated):**

```
table_code:
| ... | Alkali germanate glasses | ...
| Li | Na | K | ...

sup_text: (optional excerpt)

target_cells: {"i": [2], "j": [3], "k": [0], "cell_value_processed": ["12.5"]}
```

### Few-shot (FRI)

```
Example 1:
table_code: {example_1_table_code}
target_cells: {example_1_target_cells}
Output: {example_1_gold_json_records}

Example 2:
table_code: {example_2_table_code}
target_cells: {example_2_target_cells}
Output: {example_2_gold_json_records}

table_code: {table_code}
sup_text: {sup_text}
target_cells: {target_cells}
```

**Truncated example output:**

```json
{
  "cell_index": [[2, 3, 0]],
  "cell_record": ["{\"value\": \"12.5\", \"type\": \"Glass_Compound_Amount\", \"constituent\": \"Na2O\", \"unit\": \"mol%\", \"material\": \"glass\"}"]
}
```

### NL-to-Format

**Stage 1:**

```
Follow the instruction to complete the task: Identify the values and record types for each target cell in the table. Do not output JSON.
Instruct: Step by step reasoning: ...
Answer: The final answer is ...

table_code: {table_code}
sup_text: {sup_text}
target_cells: {target_cells}
```

**Stage 2:**

```
Follow the instruction to complete the task: Convert the natural language cell extractions into the gold_json_records JSON structure.
Instruct: Return only valid JSON with "cell_index" and "cell_record" lists of equal length.

Natural language response:
{stage1_nl_response}

Required structure:
{
  "cell_index": [[i, j, k], ...],
  "cell_record": ["<JSON string per cell>", ...]
}
```

---

## NL-to-Format: How It Works

NL-to-Format decouples **task solving** (Stage 1) from **formatting** (Stage 2), following the restriction hierarchy in [Let Me Speak Freely](https://arxiv.org/pdf/2408.02442):

1. **JSON-mode** (constrained decoding) — strictest; not in initial scope.
2. **FRI (format-restricting instructions)** — single call with schema in prompt (direct zero/few-shot above).
3. **NL-to-Format** — two LLM calls; loosest formatting constraint at Stage 1.

**Flow:**

```
User → LLM: Stage 1 task + NL format (no schema)
LLM → User: natural_language_response
User → LLM: Stage 2 schema + NL response + convert instruction
LLM → User: structured_json_output
```

**Why use it:** Preserves task accuracy closer to unrestricted NL while still yielding parseable JSON. Errors in Stage 2 (syntax, schema) can be attributed separately from task-solving errors in Stage 1.

**Error attribution:**

| Failure | Likely stage |
|---------|--------------|
| Wrong task answer in NL | Stage 1 |
| Valid NL, invalid JSON syntax | Stage 2 |
| Valid JSON, schema violation | Stage 2 |
| Schema-valid but wrong content | Stage 1 or Stage 2 |

**Evaluation notes:**

- Parse Stage 2 with `json.loads` (no repair), then `jsonschema.validate` where applicable.
- Store both stages in results JSONL for error analysis.
- Compare Stage 1 extracted answer vs gold (task accuracy); Stage 2 vs schema (compliance); Stage 2 vs gold JSON (semantic).
- Implementation stub: `scripts/generation/nl_to_format.py`.
