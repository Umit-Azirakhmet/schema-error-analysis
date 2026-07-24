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
Table code: %{table_code}%

Supplementary text: %{sup_text}%

Target cells: %{target_cells}%

Generate one valid JSON object for the supplied target cells.

The arrays "cell_value_processed", "i", "j", and "k" in target_cells are parallel arrays of equal length. For each position n:

cell_index[n] = [i[n], j[n], k[n]]
value[n] = cell_value_processed[n]

Zip the arrays strictly by position. Copy each coordinate and value exactly. Do not infer coordinates from the table, create new coordinates, combine values from different positions, sort entries, or treat any array as a range.

The lengths of "cell_index" and "cell_record" must both equal the length of "cell_value_processed". The nth cell_record must describe the nth cell_index.

Return exactly one object with these top-level fields:

{
  "cell_index": [[i, j, k], ...],
  "cell_record": ["serialized record", ...]
}

Determine each record type from the target cell's table context, especially its associated row and column headers.

Use "Glass_Compound_Amount" when:
1. the target cell represents the amount of a chemical constituent in a glass or glass-mixture composition, and
2. its associated composition unit is mol%, mol, wt%, or wt.

For "Glass_Compound_Amount":
- Use the associated chemical compound or component label as "constituent".
- Normalize mol% to "mol" and wt% to "wt".
- Use an explicit sample, material, or glass identifier as "material"; otherwise use "xx".
- Do not use experimental descriptions, measurement purposes, parameter names, or property names as "material".

A "Glass_Compound_Amount" record must contain exactly these fields:
"value", "type", "constituent", "unit", "material"

Use "Other" for every remaining value, including measurements, properties, parameters, identifiers, ratios, temperatures, densities, number densities, and rates.

An "Other" record must contain exactly these fields:
"value", "type"

Every item in "cell_record" must be one JSON object serialized as a JSON string. Do not return inner records as nested objects or arrays. Escape all internal double quotes.

Required structure:

{
  "cell_index": [[i, j, k], ...],
  "cell_record": [
    "{\"value\":\"...\",\"type\":\"Other\"}",
    "{\"value\":\"...\",\"type\":\"Glass_Compound_Amount\",\"constituent\":\"...\",\"unit\":\"...\",\"material\":\"...\"}"
  ]
}

Before returning, verify:
1. Both output arrays have exactly the same length as "cell_value_processed".
2. Every coordinate exactly equals [i[n], j[n], k[n]].
3. Every record value exactly equals cell_value_processed[n].
4. No coordinate or value was added, removed, reordered, or modified.
5. Every composition amount under a chemical constituent header is classified as "Glass_Compound_Amount".

Return raw JSON only. Do not return Python, Markdown, explanations, or multiple JSON objects.

### few_shot

Table code: %{table_code}%

Supplementary text: %{sup_text}%

Target cells: %{target_cells}%

Generate one valid JSON object for the supplied target cells.

The arrays "cell_value_processed", "i", "j", and "k" in target_cells are parallel arrays of equal length. For each position n:

cell_index[n] = [i[n], j[n], k[n]]
value[n] = cell_value_processed[n]

Zip the arrays strictly by position. Copy each coordinate and value exactly. Do not infer coordinates from the table, create new coordinates, combine values from different positions, sort entries, or treat any array as a range.

The k value only distinguishes multiple extracted values from the same table cell. It does not determine the record type.

The lengths of "cell_index" and "cell_record" must both equal the length of "cell_value_processed". The nth cell_record must describe the nth cell_index.

Return exactly one object with these top-level fields:

{
  "cell_index": [[i, j, k], ...],
  "cell_record": ["serialized record", ...]
}

Determine each record type from the target cell's table context, especially its associated row and column headers.

Use "Glass_Compound_Amount" when:
1. the target cell represents the amount of a chemical constituent in a glass or glass-mixture composition, and
2. its associated composition unit is mol%, mol, wt%, or wt.

For "Glass_Compound_Amount":
- Use the associated chemical compound or component label as "constituent".
- Normalize mol% to "mol" and wt% to "wt".
- Use an explicit sample, material, or glass identifier as "material"; otherwise use "xx".
- Do not use experimental descriptions, measurement purposes, parameter names, or property names as "material".

A "Glass_Compound_Amount" record must contain exactly these fields:
"value", "type", "constituent", "unit", "material"

Use "Other" for every remaining value, including measurements, properties, parameters, identifiers, ratios, temperatures, densities, number densities, and rates.

An "Other" record must contain exactly these fields:
"value", "type"

Every item in "cell_record" must be one JSON object serialized as a JSON string. Do not return inner records as nested objects or arrays. Escape all internal double quotes.

Required structure:

{
  "cell_index": [[i, j, k], ...],
  "cell_record": [
    "{\"value\":\"...\",\"type\":\"Other\"}",
    "{\"value\":\"...\",\"type\":\"Glass_Compound_Amount\",\"constituent\":\"...\",\"unit\":\"...\",\"material\":\"...\"}"
  ]
}

The examples demonstrate only classification and formatting. Do not copy their coordinates, values, number of entries, or table structure into the current answer.

%{few_shots}%

Before returning, verify:
1. Both output arrays have exactly the same length as "cell_value_processed".
2. Every coordinate exactly equals [i[n], j[n], k[n]].
3. Every record value exactly equals cell_value_processed[n].
4. No coordinate or value was added, removed, reordered, or modified.
5. Every composition amount under a chemical constituent header is classified as "Glass_Compound_Amount".

Return raw JSON only. Do not return Python, Markdown, explanations, or multiple JSON objects.

### nl_to_format
Table code: %{table_code}%

Supplementary text: %{sup_text}%

Target cells: %{target_cells}%

Read the table, supplementary text, and target cells.

Follow exactly this two-part format.

PART 1 - Natural Language Response:
In one short paragraph of fewer than 5 sentences, summarize the record types and required fields for the target cells while preserving their order. Do not include JSON, code, or detailed reasoning.

PART 2 - JSON Response:
Convert PART 1 into one valid JSON object using the rules below.

The arrays "cell_value_processed", "i", "j", and "k" in target_cells are parallel arrays of equal length. For each position n:

cell_index[n] = [i[n], j[n], k[n]]
value[n] = cell_value_processed[n]

Zip the arrays strictly by position. Copy each coordinate and value exactly. Do not infer coordinates from the table, create new coordinates, combine values from different positions, sort entries, or treat any array as a range.

The k value only distinguishes multiple extracted values from the same table cell. It does not determine the record type.

The lengths of "cell_index" and "cell_record" must both equal the length of "cell_value_processed". The nth cell_record must describe the nth cell_index.

Use exactly these two top-level fields:

{
  "cell_index": [[i, j, k], ...],
  "cell_record": ["serialized record", ...]
}

Determine each record type from the target cell's table context, especially its associated row and column headers.

Use "Glass_Compound_Amount" when:
1. the target cell represents the amount of a chemical constituent in a glass or glass-mixture composition, and
2. its associated composition unit is mol%, mol, wt%, or wt.

For "Glass_Compound_Amount":
- Use the associated chemical compound or component label as "constituent".
- Normalize mol% to "mol" and wt% to "wt".
- Use an explicit sample, material, or glass identifier as "material"; otherwise use "xx".
- Do not use experimental descriptions, measurement purposes, parameter names, or property names as "material".

A "Glass_Compound_Amount" record must contain exactly these fields:
"value", "type", "constituent", "unit", "material"

Use "Other" for every remaining value, including measurements, properties, parameters, identifiers, ratios, temperatures, densities, number densities, and rates.

An "Other" record must contain exactly these fields:
"value", "type"

Every item in "cell_record" must be one JSON object serialized as a JSON string. Do not return inner records as nested objects or arrays. Escape all internal double quotes.

Required structure:

{
  "cell_index": [[i, j, k], ...],
  "cell_record": [
    "{\"value\":\"...\",\"type\":\"Other\"}",
    "{\"value\":\"...\",\"type\":\"Glass_Compound_Amount\",\"constituent\":\"...\",\"unit\":\"...\",\"material\":\"...\"}"
  ]
}

Before returning PART 2, verify:
1. Both output arrays have exactly the same length as "cell_value_processed".
2. Every coordinate exactly equals [i[n], j[n], k[n]].
3. Every record value exactly equals cell_value_processed[n].
4. No coordinate or value was added, removed, reordered, or modified.
5. Every composition amount under a chemical constituent header is classified as "Glass_Compound_Amount".

Provide exactly one PART 1 and exactly one PART 2. Do not include text before PART 1 or after the final JSON object. The response must begin exactly with:

PART 1 - Natural Language Response:

and end immediately after the closing brace of the JSON object.