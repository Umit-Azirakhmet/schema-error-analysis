# Prompt Templates for Generation Pipeline

## ARQA

### zero_shot

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

Question:
%{question}%

Context paragraphs:
%{context_paragraphs}%

Tables:
%{tables}%
"""



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

## DeepJSONEval

### zero_shot
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

## SchemaToJSON

### zero_shot
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