# Prompt Templates for Generation Pipeline

## ARQA

### zero_shot

Question:
%{question}%

Context paragraphs:
%{context_paragraphs}%

Tables:
%{tables}%

Answer the financial document question using the provided context and return one valid JSON object.

Requirements:

The JSON object must have exactly these top-level fields:
- "answer"
- "claims"
Do not use "citations".
Each item in "claims" must be one factual claim that directly supports the answer.
Use only the minimum number of claims needed.
Each claim must contain:
- "type": "table" or "text"
- "claim_text": a specific factual statement
- "evidence": evidence supporting only that claim
Use table evidence when the claim is supported by a table.
Use text evidence when the claim is supported by a paragraph.
Do not combine evidence for different claims.
Do not invent paragraph IDs, table IDs, rows, columns, cell values, character spans, or evidence text.
For "text_spans[].text", copy only the exact supporting text, not the full paragraph.
Return one raw JSON only, without Markdown, explanations, or additional text.
Stop immediately after the final closing brace.


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

Now answer the question.

### few_shot
Question:
%{question}%

Context paragraphs:
%{context_paragraphs}%

Tables:
%{tables}%

Answer the financial document question using the provided context and return one valid JSON object.

Requirements:

The JSON object must have exactly these top-level fields:
- "answer"
- "claims"
Do not use "citations".
Each item in "claims" must be one factual claim that directly supports the answer.
Use only the minimum number of claims needed.
Each claim must contain:
- "type": "table" or "text"
- "claim_text": a specific factual statement
- "evidence": evidence supporting only that claim
Use table evidence when the claim is supported by a table.
Use text evidence when the claim is supported by a paragraph.
Do not combine evidence for different claims.
Do not invent paragraph IDs, table IDs, rows, columns, cell values, character spans, or evidence text.
For "text_spans[].text", copy only the exact supporting text, not the full paragraph.
Return one raw JSON only, without Markdown, explanations, or additional text.
Stop immediately after the final closing brace.


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

Now answer the question.

### nl_to_format

Question:
%{question}%

Context paragraphs:
%{context_paragraphs}%

Tables:
%{tables}%

Answer the financial document question using the provided context.


Follow this exact two-part format:

PART 1 - Natural Language Response:
In one short paragraph of fewer than 5 sentences, identify the required information and provide the complete answer in natural language.

PART 2 - JSON Response:
Convert the answer from PART 1 into one valid JSON object using the requirements below.

Requirements:
The JSON object must have exactly these top-level fields:
- "answer"
- "claims"
Do not use "citations".
Each item in "claims" must be one factual claim that directly supports the answer.
Use only the minimum number of claims needed.
Each claim must contain:
- "type": "table" or "text"
- "claim_text": a specific factual statement
- "evidence": evidence supporting only that claim
Use table evidence when the claim is supported by a table.
Use text evidence when the claim is supported by a paragraph.
Do not combine evidence for different claims.
Do not invent paragraph IDs, table IDs, rows, columns, cell values, character spans, or evidence text.
For "text_spans[].text", copy only the exact supporting text, not the full paragraph.
Do not add information that was not stated in PART 1.
Do not use Markdown code blocks.
Do not repeat the question, context, tables, or instructions. 


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

Provide exactly one PART 1 and exactly one PART 2.
Do not include any text before PART 1 or after the final JSON object.
Your response must begin exactly with "PART 1 - Natural Language Response:" and end immediately after the closing brace of the JSON object.

Now answer the question.

## DeepJSONEval

### zero_shot

Schema:
%{schema}%

Text:
%{text}%

Generate one valid JSON object that satisfies the provided JSON Schema and accurately reflects the source text.

Requirements:

Include all required fields.
Preserve the exact field names, nesting, and data types defined in the schema.
Do not add unsupported information.
Return one raw JSON only, without Markdown, explanations, or additional text.
Do not repeat the JSON.
The first character of your response must be {.
The last character of your response must be }.

Now generate the JSON object for the Schema and Text above.


### few_shot

Schema:
%{schema}%

Text:
%{text}%

Generate one valid JSON object that satisfies the provided JSON Schema and accurately reflects the source text.

Requirements:

Include all required fields.
Preserve the exact field names, nesting, and data types defined in the schema.
Do not add unsupported information.
Return one raw JSON only, without Markdown, explanations, or additional text.
Do not repeat the JSON.
The first character of your response must be {.
The last character of your response must be }.


%{few_shots}%

Now generate the JSON object for the Schema and Text above.


### nl_to_format

Schema:
%{schema}%

Text:
%{text}%

Read the source text and identify the information required by the JSON Schema.

Follow this exact two-part format:

PART 1 - Natural Language Response:
In one short paragraph of fewer than 5 sentences, identify the required information and provide the complete answer in natural language.

PART 2 - JSON Response:
Convert the answer from PART 1 into one valid JSON object that satisfies the schema. Include all required fields and preserve the exact field names, nesting, and data types. Do not add information not stated in PART 1. Do not use Markdown code blocks.

Provide exactly one PART 1 and exactly one PART 2.
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

Given a pipe-delimited table, optional supplementary text, and an ordered list of target cells, geenerate one valid JSON object containing the gold record for every target cell.

Requirements:
Use exactly these top-level fields: "cell_index" and "cell_record".
Produce one "cell_index" and one "cell_record" for each target-cell entry.
Preserve the original order of the target cells.
Do not omit, merge, deduplicate, add, or reorder entries.
Copy each target coordinate exactly as [i, j, k].
The k value identifies a specific numeric value when a table cell contains multiple extracted values.
The nth "cell_index" must correspond to the nth "cell_record".
Copy "value" exactly from the processed value in target_cells.
Keep "value" as a string and preserve formatting such as trailing zeros.

Record types:

The "type" field must be exactly one of:
- "Glass_Compound_Amount"
- "Other"

Use "Glass_Compound_Amount" only when the value represents the amount of a chemical constituent in a glass or glass-mixture composition.
A "Glass_Compound_Amount" record must contain these fields in this order:
- "value"
- "type"
- "constituent"
- "unit"
- "material"

Field rules:
- "constituent": the chemical compound or component associated with the value.
- "unit": the normalized composition unit, such as "mol" or "wt", without a percent sign.
- "material": the sample, material, or glass identifier.
- If no explicit material identifier is provided for a glass composition, use "xx".
- Include all five fields for every "Glass_Compound_Amount" record.

Use "Other" for all remaining target values, including measurements, properties, identifiers, ratios, temperatures, and densities.
An "Other" record must contain only these fields in this order:
- "value"
- "type"

Serialization requirements:
Every item in "cell_record" must be an inner JSON object serialized as a JSON string.
Do not return inner records as nested JSON objects.
Escape all double quotes inside each serialized object.
Use standard JSON double quotes, not single quotes.
Do not include null, comments, Markdown, explanations, or additional fields.
Return raw JSON only.

Required JSON shape:
{
"cell_index": [
[i, j, k]
],
"cell_record": [
"{"value":"...","type":"Other"}",
"{"value":"...","type":"Glass_Compound_Amount","constituent":"...","unit":"...","material":"..."}"
]
}

Now complete the earlier given instance.

### few_shot

Table code:
%{table_code}%

Supplementary text:
%{sup_text}%

Target cells:
%{target_cells}%

Given a pipe-delimited table, optional supplementary text, and an ordered list of target cells, geenerate one valid JSON object containing the gold record for every target cell.

Requirements:
Use exactly these top-level fields: "cell_index" and "cell_record".
Produce one "cell_index" and one "cell_record" for each target-cell entry.
Preserve the original order of the target cells.
Do not omit, merge, deduplicate, add, or reorder entries.
Copy each target coordinate exactly as [i, j, k].
The k value identifies a specific numeric value when a table cell contains multiple extracted values.
The nth "cell_index" must correspond to the nth "cell_record".
Copy "value" exactly from the processed value in target_cells.
Keep "value" as a string and preserve formatting such as trailing zeros.

Record types:

The "type" field must be exactly one of:
- "Glass_Compound_Amount"
- "Other"

Use "Glass_Compound_Amount" only when the value represents the amount of a chemical constituent in a glass or glass-mixture composition.
A "Glass_Compound_Amount" record must contain these fields in this order:
- "value"
- "type"
- "constituent"
- "unit"
- "material"

Field rules:
- "constituent": the chemical compound or component associated with the value.
- "unit": the normalized composition unit, such as "mol" or "wt", without a percent sign.
- "material": the sample, material, or glass identifier.
- If no explicit material identifier is provided for a glass composition, use "xx".
- Include all five fields for every "Glass_Compound_Amount" record.

Use "Other" for all remaining target values, including measurements, properties, identifiers, ratios, temperatures, and densities.
An "Other" record must contain only these fields in this order:
- "value"
- "type"

Serialization requirements:
Every item in "cell_record" must be an inner JSON object serialized as a JSON string.
Do not return inner records as nested JSON objects.
Escape all double quotes inside each serialized object.
Use standard JSON double quotes, not single quotes.
Do not include null, comments, Markdown, explanations, or additional fields.
Return raw JSON only.

Required JSON shape:
{
"cell_index": [
[i, j, k]
],
"cell_record": [
"{"value":"...","type":"Other"}",
"{"value":"...","type":"Glass_Compound_Amount","constituent":"...","unit":"...","material":"..."}"
]
}

%{few_shots}%

Return raw JSON only.

### nl_to_format

Table code:
%{table_code}%

Supplementary text:
%{sup_text}%

Target cells:
%{target_cells}%

Read the table, supplementary text, and target cells.

Follow this exact two-part format:

PART 1 - Natural Language Response:
In one short paragraph of fewer than 5 sentences, identify the record type and required information for each target cell while preserving the target-cell order.

PART 2 - JSON Response:
Convert the answer from PART 1 into one valid JSON object using the requirements below.

Requirements:
Use exactly these top-level fields: "cell_index" and "cell_record".
Produce one "cell_index" and one "cell_record" for each target-cell entry.
Preserve the original order of the target cells.
Do not omit, merge, deduplicate, add, or reorder entries.
Copy each target coordinate exactly as [i, j, k].
The nth "cell_index" must correspond to the nth "cell_record".
Copy "value" exactly from the processed value in target_cells.
Keep "value" as a string and preserve formatting such as trailing zeros.

The "type" field must be exactly one of:
- "Glass_Compound_Amount"
- "Other"

Use "Glass_Compound_Amount" only for the amount of a chemical constituent in a glass or glass-mixture composition.
A "Glass_Compound_Amount" record must contain these fields in this order:
- "value"
- "type"
- "constituent"
- "unit"
- "material"

For these records:
- "constituent" is the associated chemical compound or component.
- "unit" is the normalized composition unit without a percent sign.
- "material" is the associated sample, material, or glass identifier.
- Use "xx" when no explicit material identifier is provided.

Use "Other" for all remaining values.
An "Other" record must contain only:
- "value"
- "type"

Serialization requirements:
Every "cell_record" item must be an inner JSON object serialized as a JSON string.
Escape all double quotes inside each serialized object.
Do not return inner records as nested JSON objects.
Do not use single quotes, null, comments, Markdown, explanations, or additional fields.
Do not add information that was not stated in PART 1.

Required JSON shape:
{
"cell_index": [
[i, j, k]
],
"cell_record": [
"{"value":"...","type":"Other"}",
"{"value":"...","type":"Glass_Compound_Amount","constituent":"...","unit":"...","material":"..."}"
]
}

Provide exactly one PART 1 and exactly one PART 2.
Do not include any text before PART 1 or after the final JSON object.
Your response must begin exactly with "PART 1 - Natural Language Response:" and end immediately after the closing brace of the JSON object.