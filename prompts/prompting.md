
## ARQA

### Zero-shot (FRI)


**Full prompt example:**

```
Follow the instruction to complete the task: You are answering a financial document question. Given the question and supporting context, produce a JSON object with fields "answer" (string), "claims" (array of claim objects), and evidence (table_cells and/or text_spans) matching the gold structure.
Instruct: Return only valid JSON. No markdown fences, no commentary outside the JSON object. Required top-level keys: "answer", "claims". Each claim must have "type", "claim_text", and "evidence".

Question: %Discuss the distinct roles of the Automotive Division and the Financial Services Division in the Volkswagen Group's operations.%
Context paragraphs: %[VW2015_P5e55fd]%
Table: %VW2015_T4e9153%
```

### Few-shot (FRI)


{few_shots}

Example 1 input:
%{example_1_input}%

Example 1 output:
%{example_1_output}%

Example 2 input:
%{example_2_input}%

Example 2 output:
%{example_2_output}%
```



### NL-to-Format
Answer the following question using the provided context.

Follow this two-part format:

PART 1 (Natural Language):
Explain your reasoning step by step, then give your final answer in natural language.

PART 2 (JSON):
Convert your reasoning and answer into the following JSON structure:

{
  "answer": "<string>",
  "claims": [
    {
      "type": "table" | "text",
      "claim_text": "<string>",
      "evidence": {
        "table_cells": [{"table_id": "<string>", "cell_text": "<string>"}],
        "text_spans": [{"para_id": "<string>", "span_text": "<string>"}]
      }
    }
  ]
}



Context:
%{context}%

Question:
%{question}%



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
%{schema}%
```


**Full prompt example:**

```
Follow the instruction to complete the task: Given a source text and a JSON Schema, generate a JSON instance that satisfies the schema and accurately reflects the information in the text.
Instruct: Return only valid JSON matching the schema below. No extra keys, no markdown fences.

Schema:
%{"title": "Movie", "type": "object", "properties": {"title": {"type": "string"}, "director": {"type": "string"}, "year": {"type": "integer"}}, "required": ["title", "director", "year"]}%

Text: %The movie "Inception" was directed by Christopher Nolan and released in 2010..%.
```

### Few-shot (FRI)

```
{few_shots}

Example 1:
Text: %{example_1_text}%
Schema: %{example_1_schema}%
JSON: %{example_1_json}%

Example 2:
Text: %{example_2_text}%
Schema: %{example_2_schema}%
JSON: %{example_2_json}%

Text: %{text}%
Schema: %{schema}%
```

### NL-to-Format

Read the following text and extract the relevant information to answer the implicit structured-data task.

Follow this two-part format:

PART 1 (Natural Language):
First, explain your reasoning about what information you need to extract and why.
Then, provide the extracted answer in natural language.

PART 2 (JSON):
Convert your extraction into valid JSON that validates against the provided schema.
Return only valid JSON. No markdown.

Schema:
%{schema}%

Text:
%{text}%


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
%| ... | Alkali germanate glasses | ...
| Li | Na | K | ...%

sup_text: %(optional excerpt)%

target_cells: %{"i": [2], "j": [3], "k": [0], "cell_value_processed": ["12.5"]}%
```

### Few-shot (FRI)

```
Example 1:
table_code: %{example_1_table_code}%
target_cells: %{example_1_target_cells}%
Output: %{example_1_gold_json_records}%

Example 2:
table_code: %{example_2_table_code}%
target_cells: %{example_2_target_cells}%
Output: %{example_2_gold_json_records}%

table_code: %{table_code}%
sup_text: %{sup_text}%
target_cells: %{target_cells}%
```


### NL-to-Format

Identify the values and record types for each target cell in the provided table.

Follow this two-part format:

PART 1 (Natural Language):
First, explain your reasoning about what values and record types you need to identify.
Then, provide the answer in natural language.

PART 2 (JSON):
Convert your extraction into valid JSON with "cell_index" and "cell_record" lists of equal length.
Return only valid JSON. No markdown.

Table Code:
%{table_code}%

Supplementary Text:
%{sup_text}%

Target Cells (to extract):
%{target_cells}%

Required JSON Structure:
{
  "cell_index": [[i, j, k], ...],
  "cell_record": ["<JSON string per cell>", ...]
}

---



