import csv
from pathlib import Path


def read_csv_rows(path):
    """
    Read a CSV file into a list of dictionaries.
    Each row becomes one dict where keys are column names.
    """
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_arqa(dataset_path, context_path=None, max_rows=None):
    """
    Load ARQA rows and join them with ARQA_DB.csv.

    ARQA dataset row uses:
      - qa_id as row ID
      - pack_table_id as the table ID for joining

    ARQA_DB.csv uses:
      - table_id as the join key

    This function does NOT modify the original CSV.
    It returns clean row objects for the generation pipeline.
    """

    dataset_path = Path(dataset_path)
    context_path = Path(context_path) if context_path else None

    # Load ARQA main dataset
    arqa_rows = read_csv_rows(dataset_path)

    # Load ARQA DB context and index it by table_id
    db_by_table_id = {}

    if context_path is not None:
        db_rows = read_csv_rows(context_path)

        for db_row in db_rows:
            table_id = db_row.get("table_id", "")
            if table_id:
                db_by_table_id[table_id] = db_row

    loaded = []

    for row_index, row in enumerate(arqa_rows):
        if max_rows is not None and row_index >= max_rows:
            break

        # ARQA characteristics file uses pack_table_id
        pack_table_id = row.get("pack_table_id", "")

        # Find matching DB row using table_id
        db_context = db_by_table_id.get(pack_table_id, {})

        # Prepare table/context text for prompts.
        # Keep these raw for now. Do not parse or rewrite.
        context_paragraphs = db_context.get("paragraphs", "")
        table_rows = db_context.get("rows", "")
        table_headers = db_context.get("headers", "")
        merged_headers = db_context.get("merged_headers", "")

        tables_text = (
            f"table_id: {pack_table_id}\n"
            f"headers: {table_headers}\n"
            f"merged_headers: {merged_headers}\n"
            f"rows: {table_rows}"
        )

        loaded.append({
            "dataset": "ARQA",
            "row_id": row.get("qa_id", f"arqa_{row_index}"),
            "row_index": row_index,

            # These fields are what prompt templates will use
            "prompt_fields": {
                "question": row.get("question", ""),
                "context": context_paragraphs,
                "context_paragraphs": context_paragraphs,
                "table": tables_text,
                "tables": tables_text,
                "table_id": pack_table_id,
                "q_type": row.get("q_type", ""),
            },

            # Save gold answer exactly as stored
            "gold_json_raw": row.get("gold_answer", ""),

            # Characteristics can be filled later
            "characteristics": {},

            # Preserve original values
            "original_row": row,
            "db_context": db_context,
        })

    return loaded