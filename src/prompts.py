from pathlib import Path


def load_prompt_file(prompts_path):
    """
    Load the full prompt markdown file as text.

    For this first version, we keep it simple:
    - Read prompting.md
    - Later we will improve template extraction
    """
    return Path(prompts_path).read_text(encoding="utf-8")


def replace_placeholders(template, prompt_fields, few_shots=""):
    """
    Replace placeholders like:
      %{question}%
      %{schema}%
      %{text}%
      %{few_shots}%

    with values from prompt_fields.
    """

    filled = template

    # Few-shot examples are handled separately
    filled = filled.replace("%{few_shots}%", few_shots)
    filled = filled.replace("{few_shots}", few_shots)

    # Replace every prompt field
    for key, value in prompt_fields.items():
        filled = filled.replace(f"%{{{key}}}%", str(value))
        filled = filled.replace(f"{{{key}}}", str(value))

    return filled


def get_simple_template(dataset, method):
    """
    Return a simple working template for each dataset and prompting method.

    This avoids complicated markdown parsing for the first baseline.
    The goal is just to generate model responses and save raw output.
    """

    dataset = dataset.lower()
    method = method.lower()

    if dataset == "arqa":
        if method == "zero_shot":
            return """Follow the instruction to complete the task: You are answering a financial document question using the provided context. Produce a JSON object with top-level fields "answer" and "claims". Evidence should be included inside each claim.

Instruct: Return only valid JSON. No markdown fences, no commentary outside the JSON object. Required top-level keys: "answer", "claims". Each claim must have "type", "claim_text", and "evidence".

For table evidence, each table cell should include "table_id", "row", "col", and "cell_text".
For text evidence, each text span should include "para_id", "char_start", "char_end", and "text".

Question:
%{question}%

Context paragraphs:
%{context_paragraphs}%

Table:
%{tables}%
"""

        if method == "few_shot":
            return """Follow the instruction to complete the task: You are answering a financial document question using the provided context. Produce a JSON object with top-level fields "answer" and "claims". Evidence should be included inside each claim.

Instruct: Return only valid JSON. No markdown fences, no commentary outside the JSON object. Required top-level keys: "answer", "claims". Each claim must have "type", "claim_text", and "evidence".

For table evidence, each table cell should include "table_id", "row", "col", and "cell_text".
For text evidence, each text span should include "para_id", "char_start", "char_end", and "text".

%{few_shots}%

Now answer the following question.

Question:
%{question}%

Context paragraphs:
%{context_paragraphs}%

Table:
%{tables}%
"""

        if method == "nl_to_format":
            return """Answer the following financial document question using the provided context.

Follow this two-part format:

PART 1 (Natural Language):
Explain your reasoning briefly, then give your final answer in natural language.

PART 2 (JSON):
Convert your answer into valid JSON with this structure:
{
  "answer": "<string>",
  "claims": [
    {
      "type": "table" | "text",
      "claim_text": "<string>",
      "evidence": {
        "table_cells": [
          {
            "table_id": "<string>",
            "row": "<string>",
            "col": "<string>",
            "cell_text": "<string>"
          }
        ],
        "text_spans": [
          {
            "para_id": "<string>",
            "char_start": 0,
            "char_end": 0,
            "text": "<string>"
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

Table:
%{tables}%
"""

    if dataset in ["deepjsoneval", "deepjson"]:
        if method == "zero_shot":
            return """Given the source text and JSON Schema, generate a JSON object that satisfies the schema and accurately reflects the text.

Source text:
%{text}%

JSON Schema:
%{schema}%

Return only valid JSON. Do not include markdown or extra commentary.
"""

        if method == "few_shot":
            return """Given the source text and JSON Schema, generate a JSON object that satisfies the schema and accurately reflects the text.

%{few_shots}%

Now complete the next one.

Source text:
%{text}%

JSON Schema:
%{schema}%

Return only valid JSON. Do not include markdown or extra commentary.
"""

        if method == "nl_to_format":
            return """Read the following text and extract the relevant information.

Follow this two-part format:

PART 1 (Natural Language):
Explain what information should be extracted, then provide the extracted answer in natural language.

PART 2 (JSON):
Convert the extraction into valid JSON that matches the provided schema.

Source text:
%{text}%

JSON Schema:
%{schema}%
"""

    if dataset in ["schematojson", "schema_to_json", "schema-to-json"]:
        if method == "zero_shot":
            return """Given the table, optional supporting text, and target cell coordinates, produce gold_json_records.

Return only valid JSON with this structure:
{
  "cell_index": [[i, j, k], ...],
  "cell_record": ["<JSON string per cell>", ...]
}

Table code:
%{table_code}%

Supplementary text:
%{sup_text}%

Target cells:
%{target_cells}%
"""

        if method == "few_shot":
            return """Given the table, optional supporting text, and target cell coordinates, produce gold_json_records.

Return only valid JSON with this structure:
{
  "cell_index": [[i, j, k], ...],
  "cell_record": ["<JSON string per cell>", ...]
}

%{few_shots}%

Now complete the next one.

Table code:
%{table_code}%

Supplementary text:
%{sup_text}%

Target cells:
%{target_cells}%
"""

        if method == "nl_to_format":
            return """Identify the values and record types for each target cell in the provided table.

Follow this two-part format:

PART 1 (Natural Language):
Explain what values and record types should be identified, then give the answer in natural language.

PART 2 (JSON):
Convert your extraction into valid JSON with "cell_index" and "cell_record" lists of equal length.

Table code:
%{table_code}%

Supplementary text:
%{sup_text}%

Target cells:
%{target_cells}%
"""

    raise ValueError(f"No prompt template for dataset={dataset}, method={method}")


def build_prompt(dataset, method, prompt_fields, few_shots=""):
    """
    Build the final prompt for one row.
    """
    template = get_simple_template(dataset, method)
    return replace_placeholders(template, prompt_fields, few_shots=few_shots)