# Prompt Templates for Generation Pipeline

## ARQA

### zero_shot
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
