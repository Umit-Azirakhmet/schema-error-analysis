# Final Prompt Templates

## ARQA

### Zero-shot

```text
You are answering a "category" question using the provided context.

Return a JSON object with:
- "answer": a concise final answer
- "claims": an array of claim objects

Each claim must contain:
- "type": "table" or "text"
- "claim_text": a factual statement supporting the answer
- "evidence"

For table evidence, use:
"table_cells": [{"table_id": "...", "row": "...", "col": "...", "cell_text": "..."}]

For text evidence, use:
"text_spans": [{"para_id": "...", "char_start": 0, "char_end": 0, "text": "..."}]

Return only valid JSON. Do not include markdown or commentary.

Question:
%{question}%

Context paragraphs:
%{context_paragraphs}%

Tables:
%{tables}%
```



### Few-shot

```text
You are answering a financial document question using the provided context.

Return a JSON object with:
- "answer": a concise final answer
- "claims": an array of claim objects

Each claim must contain:
- "type": "table" or "text"
- "claim_text": a factual statement supporting the answer
- "evidence"

For table evidence, use:
"table_cells": [{"table_id": "...", "row": "...", "col": "...", "cell_text": "..."}]

For text evidence, use:
"text_spans": [{"para_id": "...", "char_start": 0, "char_end": 0, "text": "..."}]

Return only valid JSON. Do not include markdown or commentary.

%{few_shots}%

Now complete the following instance.

Question:
%{question}%

Context paragraphs:
%{context_paragraphs}%

Tables:
%{tables}%
```



### NL-to-Format

```text
Answer the financial document question using the provided context.

Follow this exact two-part format.

PART 1 — Natural Language:
Briefly explain how the evidence from the tables and text supports the answer. Then provide the complete final answer in natural language.

PART 2 — JSON:
Convert only the final natural-language answer from PART 1 into valid JSON that satisfies these requirements:

Provide a valid JSON object with:
- "answer": a concise final answer
- "claims": an array of claim objects

Each claim must contain:
- "type": "table" or "text"
- "claim_text": a factual statement supporting the answer
- "evidence"

For table evidence, use:
"table_cells": [{"table_id": "...", "row": "...", "col": "...", "cell_text": "..."}]

For text evidence, use:
"text_spans": [{"para_id": "...", "char_start": 0, "char_end": 0, "text": "..."}]

Do not include markdown fences.

Question:
%{question}%

Context paragraphs:
%{context_paragraphs}%

Tables:
%{tables}%
```

---



## DeepJSONEval



### Zero-shot

```text
Given a source text and a JSON Schema, generate a JSON instance that satisfies the schema and accurately reflects the text.

Include all required fields.
Preserve the data types defined in the schema.
Do not add unsupported information.
Return only valid JSON with no markdown or extra commentary.

Schema:
%{schema}%

Text:
%{text}%
```



### Few-shot

```text
Given a source text and a JSON Schema, generate a JSON instance that satisfies the schema and accurately reflects the text.

Include all required fields.
Preserve the data types defined in the schema.
Do not add unsupported information.
Return only valid JSON with no markdown or extra commentary.

%{few_shots}%

Now complete the following instance.

Schema:
%{schema}%

Text:
%{text}%
```



### NL-to-Format

```text
Read the source text and identify the information required by the JSON Schema.

Follow this exact two-part format.

PART 1 — Natural Language Answer:
Briefly explain which information must be extracted from the text to satisfy the schema. Then provide the complete final answer in natural language.

PART 2 — JSON Conversion:
Convert only the final natural-language answer from PART 1 into valid JSON that satisfies the provided schema.

Include all required fields.
Preserve the data types defined in the schema.
Do not add information that was not stated in PART 1.
Do not include markdown fences.

Schema:
%{schema}%

Text:
%{text}%
```

---



## SchemaToJSON



### Zero-shot

```text
Given a pipe-delimited table, optional supporting text, and target cell coordinates, produce a JSON object with parallel lists "cell_index" and "cell_record".

Requirements:
- Each item in "cell_index" must be a coordinate [i, j, k].
- Each item in "cell_record" must be a valid JSON object serialized as a string.
- Allowed record types are "Other" and "Glass_Compound_Amount".
- Each inner record must have exactly one of these types.
- The complete output may contain only one type or a mixture of both types.
- An "Other" record must contain:
  - "value": string
  - "type": "Other"
- A "Glass_Compound_Amount" record must contain:
  - "value": string
  - "type": "Glass_Compound_Amount"
  - "constituent": string
  - "unit": string
  - "material": string
- The nth "cell_index" must correspond to the nth "cell_record".
- Do not omit or reorder target cells.
- Return only valid JSON with no markdown or extra commentary.

Required output structure:
{
  "cell_index": [[i, j, k], ...],
  "cell_record": ["{\"value\": \"...\", \"type\": \"...\", ...}", ...]
}

Table:
%{table_code}%

Supporting text:
%{sup_text}%

Target cells:
%{target_cells}%
```



### Few-shot

```text
Given a pipe-delimited table, optional supporting text, and target cell coordinates, produce a JSON object with parallel lists "cell_index" and "cell_record".

Requirements:
- Each item in "cell_index" must be a coordinate [i, j, k].
- Each item in "cell_record" must be a valid JSON object serialized as a string.
- Allowed record types are "Other" and "Glass_Compound_Amount".
- Each inner record must have exactly one of these types.
- The complete output may contain only one type or a mixture of both types.
- An "Other" record must contain:
  - "value": string
  - "type": "Other"
- A "Glass_Compound_Amount" record must contain:
  - "value": string
  - "type": "Glass_Compound_Amount"
  - "constituent": string
  - "unit": string
  - "material": string
- The nth "cell_index" must correspond to the nth "cell_record".
- Do not omit or reorder target cells.
- Return only valid JSON with no markdown or extra commentary.


Required output structure:
{
  "cell_index": [[i, j, k], ...],
  "cell_record": ["{\"value\": \"...\", \"type\": \"...\", ...}", ...]
}

%{few_shots}%

Now complete the following instance.

Table:
%{table_code}%

Supporting text:
%{sup_text}%

Target cells:
%{target_cells}%
```



### NL-to-Format

```text
Identify the value and record type for each target cell in the table.

Follow this exact two-part format.

PART 1 — Natural Language Answer:
For each target cell, briefly explain the identified value, record type, and any additional fields required by that record type. Then provide the complete final answer in natural language, preserving the order of the target cells.

PART 2 — JSON Conversion:
Convert only the final natural-language answer from PART 1 into a valid JSON object with parallel lists "cell_index" and "cell_record".

Requirements:
- Each item in "cell_index" must be a coordinate [i, j, k].
- Each item in "cell_record" must be a valid JSON object serialized as a string.
- Allowed record types are "Other" and "Glass_Compound_Amount".
- Each inner record must have exactly one of these types.
- The complete output may contain only one type or a mixture of both types.
- An "Other" record must contain:
  - "value": string
  - "type": "Other"
- A "Glass_Compound_Amount" record must contain:
  - "value": string
  - "type": "Glass_Compound_Amount"
  - "constituent": string
  - "unit": string
  - "material": string
- The nth "cell_index" must correspond to the nth "cell_record".
- Do not omit or reorder target cells.
- Return only valid JSON with no markdown or extra commentary.
- Do not add information that was not stated in PART 1.

Required output structure:
{
  "cell_index": [[i, j, k], ...],
  "cell_record": ["{\"value\": \"...\", \"type\": \"...\", ...}", ...]
}

Table:
%{table_code}%

Supporting text:
%{sup_text}%

Target cells:
%{target_cells}%
```

