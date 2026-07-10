<<<<<<< HEAD
﻿# Prompt Templates for Generation Pipeline
=======
# Prompt Templates for Generation Pipeline
>>>>>>> 1b4301fa5fa5691a639c379431f8d29270174332

## ARQA

### zero_shot
<<<<<<< HEAD
Given the following context and question, generate a JSON response.

Context paragraphs: %{context_paragraphs}%

Tables: %{tables}%

Schema: %{schema}%

Question: %{question}%

Generate a JSON response:

### few_shot
Given the following context and question, generate a JSON response.

Context paragraphs: %{context_paragraphs}%

Tables: %{tables}%

Schema: %{schema}%

Question: %{question}%

%{few_shots}%

Generate a JSON response:

### nl_to_format
Given the following context and question, provide a natural language response and a JSON response.

Context paragraphs: %{context_paragraphs}%

Tables: %{tables}%

Schema: %{schema}%

Question: %{question}%

PART 1 - Natural Language Response:
[Provide a natural language answer to the question]

PART 2 - JSON Response:
[Provide the JSON response]
=======

Question:
%{question}%

Context paragraphs:
%{context_paragraphs}%

Tables:
%{tables}%

You are answering a financial document question using the provided context.

Return ONLY a valid JSON object.

The JSON object must have exactly these top-level fields:
- "answer"
- "claims"

Do NOT use "citations".
Do NOT use markdown.
Do NOT include explanation outside the JSON.

Each item in "claims" must be one factual claim that supports the answer.

Each claim must have:
- "type": "table" or "text"
- "claim_text": a specific factual statement
- "evidence": evidence for that specific claim only

For table evidence, use:
"evidence": {
 "table_cells": [
   {
     "table_id": "...",
     "row": "...",
     "col": "...",
     "cell_text": "..."
   }
 ]
}

For text evidence, use:
"evidence": {
 "text_spans": [
   {
     "para_id": "...",
     "char_start": 0,
     "char_end": 0,
     "text": "..."
   }
 ]
}

Do not cite an entire paragraph generally.
Do not put all evidence in one citations list.
Each claim needs its own evidence.
Use table evidence when the answer is supported by a table.
For text_spans[].text, copy only the exact few sentences that prove the claim; do not copy the full paragraph.

Required JSON shape:
{
 "answer": "...",
 "claims": [
   {
     "type": "table",
     "claim_text": "...",
     "evidence": {
       "table_cells": [
         {
           "table_id": "...",
           "row": "...",
           "col": "...",
           "cell_text": "..."
         }
       ]
     }
   },
   {
     "type": "text",
     "claim_text": "...",
     "evidence": {
       "text_spans": [
         {
           "para_id": "...",
           "char_start": 0,
           "char_end": 0,
           "text": "..."
         }
       ]
     }
   }
 ]
}


### few_shot
Question:
%{question}%

Context paragraphs:
%{context_paragraphs}%

Tables:
%{tables}%

You are answering a financial document question using the provided context.

Return ONLY a valid JSON object.

The JSON object must have exactly these top-level fields:
- "answer"
- "claims"

Do NOT use "citations".
Do NOT use markdown.
Do NOT include explanation outside the JSON.

Each item in "claims" must be one factual claim that supports the answer.

Provide Paragraph IDs or Table IDs of where you find the answers.

Each claim must have:
- "type": "table" or "text"
- "claim_text": a specific factual statement
- "evidence": evidence for that specific claim only

For table evidence, use:
"evidence": {
 "table_cells": [
   {
     "table_id": "...",
     "row": "...",
     "col": "...",
     "cell_text": "..."
   }
 ]
}

For text evidence, use:
"evidence": {
 "text_spans": [
   {
     "para_id": "...",
     "char_start": 0,
     "char_end": 0,
     "text": "..."
   }
 ]
}

Do not cite an entire paragraph generally.
Do not put all evidence in one citations list.
Each claim needs its own evidence.
Use table evidence when the answer is supported by a table.
For text_spans[].text, copy only the exact few sentences that prove the claim; do not copy the full paragraph.

Required JSON shape:
{
 "answer": "...",
 "claims": [
   {
     "type": "table",
     "claim_text": "...",
     "evidence": {
       "table_cells": [
         {
           "table_id": "...",
           "row": "...",
           "col": "...",
           "cell_text": "..."
         }
       ]
     }
   },
   {
     "type": "text",
     "claim_text": "...",
     "evidence": {
       "text_spans": [
         {
           "para_id": "...",
           "char_start": 0,
           "char_end": 0,
           "text": "..."
         }
       ]
     }
   }
 ]
}

%{few_shots}%

Now complete the earlier given instance.


### nl_to_format

Question:
%{question}%

Context paragraphs:
%{context_paragraphs}%

Tables:
%{tables}%

Answer the financial document question using the provided context.

Follow this exact two-part format.

PART 1 - Natural Language Response:
Briefly explain how the evidence from the tables and text supports the answer. Then provide the complete final answer in natural language.

PART 2 - JSON Response:
Convert only the final natural-language answer from PART 1 into valid JSON that satisfies these requirements:

The JSON object must have exactly these top-level fields:
- "answer"
- "claims"

Do NOT use "citations".
Do NOT use markdown.
Do NOT include explanation outside the JSON.

Each item in "claims" must be one factual claim that supports the answer.

Provide Paragraph IDs or Table IDs of where you find the answers.

Each claim must have:
- "type": "table" or "text"
- "claim_text": a specific factual statement
- "evidence": evidence for that specific claim only

For table evidence, use:
"evidence": {
 "table_cells": [
   {
     "table_id": "...",
     "row": "...",
     "col": "...",
     "cell_text": "..."
   }
 ]
}

For text evidence, use:
"evidence": {
 "text_spans": [
   {
     "para_id": "...",
     "char_start": 0,
     "char_end": 0,
     "text": "..."
   }
 ]
}

Do not cite an entire paragraph generally.
Do not put all evidence in one citations list.
Each claim needs its own evidence.
Use table evidence when the answer is supported by a table.
For text_spans[].text, copy only the exact few sentences that prove the claim; do not copy the full paragraph.

Required JSON shape:
{
 "answer": "...",
 "claims": [
   {
     "type": "table",
     "claim_text": "...",
     "evidence": {
       "table_cells": [
         {
           "table_id": "...",
           "row": "...",
           "col": "...",
           "cell_text": "..."
         }
       ]
     }
   },
   {
     "type": "text",
     "claim_text": "...",
     "evidence": {
       "text_spans": [
         {
           "para_id": "...",
           "char_start": 0,
           "char_end": 0,
           "text": "..."
         }
       ]
     }
   }
 ]
}

>>>>>>> 1b4301fa5fa5691a639c379431f8d29270174332

## DeepJSONEval

### zero_shot
<<<<<<< HEAD
Given the following schema and text, generate a JSON response.

Schema: %{schema}%

Text: %{text}%

Generate a JSON response:

### few_shot
Given the following schema and text, generate a JSON response.

Schema: %{schema}%

Text: %{text}%

%{few_shots}%

Generate a JSON response:

### nl_to_format
Given the following schema and text, provide a natural language response and a JSON response.

Schema: %{schema}%

Text: %{text}%

PART 1 - Natural Language Response:
[Provide a natural language interpretation]

PART 2 - JSON Response:
[Provide the JSON response]
=======

Schema:
%{schema}%

Text:
%{text}%

Given a source text and a JSON Schema, generate a JSON instance that satisfies the schema and accurately reflects the text.

Include all required fields.
Preserve the data types defined in the schema.
Do not add unsupported information.
Return only valid JSON with no markdown or extra commentary.


### few_shot

Schema:
%{schema}%

Text:
%{text}%

Given a source text and a JSON Schema, generate a JSON instance that satisfies the schema and accurately reflects the text.

Include all required fields.
Preserve the data types defined in the schema.
Do not add unsupported information.
Return only valid JSON with no markdown or extra commentary.

%{few_shots}%

Now complete the earlier given instance.


### nl_to_format

Schema:
%{schema}%

Text:
%{text}%

Read the source text and identify the information required by the JSON Schema.

Follow this exact two-part format.

PART 1 - Natural Language Response:
Briefly explain which information must be extracted from the text to satisfy the schema. Then provide the complete final answer in natural language.

PART 2 - JSON Response:
Convert only the final natural-language answer from PART 1 into valid JSON that satisfies the provided schema.

Include all required fields.
Preserve the data types defined in the schema.
Do not add information that was not stated in PART 1.
Do not include markdown fences.

>>>>>>> 1b4301fa5fa5691a639c379431f8d29270174332

## SchemaToJSON

### zero_shot
<<<<<<< HEAD
Given the following table code, supplementary text, and target cells, generate a JSON response.

Table code: %{table_code}%

Supplementary text: %{sup_text}%

Target cells: %{target_cells}%

Generate a JSON response:

### few_shot
Given the following table code, supplementary text, and target cells, generate a JSON response.

Table code: %{table_code}%

Supplementary text: %{sup_text}%

Target cells: %{target_cells}%

%{few_shots}%

Generate a JSON response:

### nl_to_format
Given the following table code, supplementary text, and target cells, provide a natural language response and a JSON response.

Table code: %{table_code}%

Supplementary text: %{sup_text}%

Target cells: %{target_cells}%

PART 1 - Natural Language Response:
[Provide a natural language description]

PART 2 - JSON Response:
[Provide the JSON response]
=======

Table code:
%{table_code}%

Supplementary text:
%{sup_text}%

Target cells:
%{target_cells}%

Given a pipe-delimited table, optional supporting text, and target cell coordinates, produce a JSON object with parallel lists "cell_index" and "cell_record".

Requirements:
- Each item in "cell_index" must be a coordinate [i, j, k].
- Each item in "cell_record" must be a valid JSON object serialized as a string.
- Each inner JSON object must contain:
  - "value": string
  - "type": string
- Depending on the record type, the inner object may also contain:
  - "constituent": string
  - "unit": string
  - "material": string
- The nth "cell_index" must correspond to the nth "cell_record".
- Do not omit or reorder target cells.
- Use the record type and required fields supported by the table context and dataset examples.
- Return only valid JSON with no markdown or extra commentary.

Required output structure:
{
  "cell_index": [[i, j, k], ...],
  "cell_record": ["{\"value\": \"...\", \"type\": \"...\", ...}", ...]
}


### few_shot

Table code:
%{table_code}%

Supplementary text:
%{sup_text}%

Target cells:
%{target_cells}%

Given a pipe-delimited table, optional supporting text, and target cell coordinates, produce a JSON object with parallel lists "cell_index" and "cell_record".

Requirements:
- Each item in "cell_index" must be a coordinate [i, j, k].
- Each item in "cell_record" must be a valid JSON object serialized as a string.
- Each inner JSON object must contain:
  - "value": string
  - "type": string
- Depending on the record type, the inner object may also contain:
  - "constituent": string
  - "unit": string
  - "material": string
- The nth "cell_index" must correspond to the nth "cell_record".
- Do not omit or reorder target cells.
- Use the record type and required fields supported by the table context and dataset examples.
- Return only valid JSON with no markdown or extra commentary.

Required output structure:
{
  "cell_index": [[i, j, k], ...],
  "cell_record": ["{\"value\": \"...\", \"type\": \"...\", ...}", ...]
}

%{few_shots}%

Now complete the earlier given instance.


### nl_to_format

Table code:
%{table_code}%

Supplementary text:
%{sup_text}%

Target cells:
%{target_cells}%

Identify the value and record type for each target cell in the table.

Follow this exact two-part format.

PART 1 - Natural Language Response:
For each target cell, briefly explain the identified value, record type, and any additional fields required by that record type. Then provide the complete final answer in natural language, preserving the order of the target cells.

PART 2 - JSON Response:
Convert only the final natural-language answer from PART 1 into a valid JSON object with parallel lists "cell_index" and "cell_record".

Requirements:
- Each item in "cell_index" must be a coordinate [i, j, k].
- Each item in "cell_record" must be a valid JSON object serialized as a string.
- Each inner JSON object must contain:
  - "value": string
  - "type": string
- Depending on the record type, the inner object may also contain:
  - "constituent": string
  - "unit": string
  - "material": string
- The nth "cell_index" must correspond to the nth "cell_record".
- Do not omit or reorder target cells.
- Use the record type and required fields supported by the table context and dataset examples.
- Return only valid JSON with no markdown or extra commentary.
- Do not add information that was not stated in PART 1.

Required output structure:
{
  "cell_index": [[i, j, k], ...],
  "cell_record": ["{\"value\": \"...\", \"type\": \"...\", ...}", ...]
}
>>>>>>> 1b4301fa5fa5691a639c379431f8d29270174332
