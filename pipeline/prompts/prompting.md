# Prompt Templates for Generation Pipeline

## ARQA

### zero_shot

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

Return a TWO-PART response with exactly this format:

PART 1 - Natural Language Response:
Provide a brief explanation of how the evidence supports the answer, then state the complete final answer in natural language.

PART 2 - JSON Response:
Convert only the final natural-language answer from PART 1 into valid JSON that satisfies these requirements:

The JSON object must have exactly these top-level fields:
- "answer"
- "claims"

Do NOT use "citations".
Do NOT use markdown.
Do NOT include explanation outside the JSON.
Do not repeat the question, context, tables, or instructions. 
Do not write "Answer:" before or after the JSON. 
Stop immediately after the final closing brace.

Each item in "claims" must be one factual claim that supports the answer. Use only the minimum number of claims needed to support the answer. Do not add extra related claims that are not necessary.


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
For text_spans[].text, copy only the exact few sentences that prove the claim; do not copy the full paragraph. Do not invent table IDs, paragraph IDs, rows, columns, cell values, or character spans.

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
Now answer the current question only. Return one JSON object and one short NL answer.



## DeepJSONEval

### zero_shot

Schema:
%{schema}%

Text:
%{text}%

Given the source text and JSON Schema, generate exactly one JSON object that satisfies the schema and accurately reflects the text.

Include all required fields.
Preserve the field names, nesting, and data types defined in the schema.
Do not add unsupported information.

Now generate the JSON object for the Schema and Text above.

Output rules:

Output exactly one JSON object.
Output raw JSON only.
Do not repeat the JSON.
Do not include Markdown code blocks.
Do not include introductory text, reasoning, explanations, or commentary.
The first character of your response must be {.
The last character of your response must be }.
Stop generating immediately after the final closing brace.



### few_shot

Schema:
%{schema}%

Text:
%{text}%

Given the source text and JSON Schema, generate exactly one JSON object that satisfies the schema and accurately reflects the text.

Include all required fields.
Preserve the field names, nesting, and data types defined in the schema.
Do not add unsupported information.

%{few_shots}%

Now generate the JSON object for the Schema and Text above.

Output rules:

Output exactly one JSON object.
Output raw JSON only.
Do not repeat the JSON.
Do not include Markdown code blocks.
Do not include introductory text, reasoning, explanations, or commentary.
The first character of your response must be {.
The last character of your response must be }.
Stop generating immediately after the final closing brace.


### nl_to_format

Schema:
%{schema}%

Text:
%{text}%

Read the source text and identify the information required by the JSON Schema.

Follow this exact two-part format exactly once:

PART 1 - Natural Language Response:
Briefly explain which information must be extracted from the text to satisfy the schema. Then provide the complete final answer in natural language. Limit reasoning to one small paragraph of fewer than 5 sentences.

PART 2 - JSON Response:
Convert only the final natural-language answer from PART 1 into valid JSON that satisfies the provided schema. Include all required fields. Preserve the data types defined in the schema. Do not add information that was not stated in PART 1. Do not include markdown fences.

Provide exactly one PART 1 and exactly one PART 2.
Do not repeat PART 1 or PART 2.
Do not restart the response after completing PART 2.
Do not include any text before PART 1 or after the final JSON object.
Your response must begin exactly with "PART 1 - Natural Language Response:" and end immediately after the closing brace of the JSON object.

## SchemaToJSON

### zero_shot

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