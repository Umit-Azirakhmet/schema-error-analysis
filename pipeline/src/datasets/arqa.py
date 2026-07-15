"""
ARQA dataset loader with context joining.
"""
import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


def _cell_value(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def _load_active_characteristics() -> Dict[str, Any]:
    pipeline_root = Path(__file__).parent.parent.parent
    project_root = pipeline_root.parent

    candidates = [
        Path.cwd() / "data" / "active_characteristics.json",
        pipeline_root / "data" / "active_characteristics.json",
        project_root / "data" / "active_characteristics.json",
    ]

    for candidate in candidates:
        if candidate.exists():
            with open(candidate, "r", encoding="utf-8") as handle:
                return json.load(handle)

    return {}


def _extract_characteristics(row: pd.Series) -> Dict[str, Any]:
    config = _load_active_characteristics().get("ARQA", {})
    active_columns = config.get("active_columns", [])
    constant_columns = config.get("constant_columns", {})

    characteristics = {}
    for column in active_columns:
        if column in row.index:
            value = row[column]
            characteristics[column] = "" if pd.isna(value) else value

    for column, value in constant_columns.items():
        characteristics[column] = value

    return characteristics


def _format_context_paragraphs(row: pd.Series) -> str:
    if "context_paragraphs" in row.index:
        value = row.get("context_paragraphs", "")
        if not pd.isna(value) and str(value).strip():
            return str(value)

    paragraphs = row.get("paragraphs", "")
    return str(paragraphs) if not pd.isna(paragraphs) else ""


def _format_tables(row: pd.Series) -> str:
    if "tables" in row.index:
        value = row.get("tables", "")
        if not pd.isna(value) and str(value).strip():
            return str(value)

    parts = []
    for key in ("title", "headers", "merged_headers", "rows", "stub_col"):
        value = row.get(key, "")
        if not pd.isna(value) and str(value).strip():
            parts.append(f"{key}: {value}")

    return "\n\n".join(parts)


def _format_schema(row: pd.Series) -> str:
    schema = row.get("schema", "")
    return str(schema) if not pd.isna(schema) else ""


def _format_gold_json(row: pd.Series) -> str:
    if "gold_json" in row.index:
        value = row.get("gold_json", "")
        if not pd.isna(value) and str(value).strip():
            return str(value)

    gold_answer = row.get("gold_answer", "")
    return str(gold_answer) if not pd.isna(gold_answer) else ""


def load_arqa_dataset(dataset_path: str, context_path: str) -> List[Dict]:
    """Load ARQA dataset and join with context database."""
    qa_df = pd.read_csv(dataset_path).reset_index(drop=True)
    context_df = pd.read_csv(context_path)

    joined_df = qa_df.merge(context_df, on="table_id", how="left")

    rows = []
    for row_index, joined_row in joined_df.iterrows():
        qa_row = qa_df.iloc[row_index]

        prompt_fields = {
            "question": _cell_value(joined_row.get("question", "")),
            "schema": _format_schema(joined_row),
            "tables": _format_tables(joined_row),
            "context_paragraphs": _format_context_paragraphs(joined_row),
        }

        row_data = {
            "dataset": "ARQA",
            "row_id": str(qa_row.get("qa_id", f"arqa_{row_index}")),
            "row_index": row_index,
            "prompt_fields": prompt_fields,
            "gold_json_raw": _format_gold_json(qa_row),
            "characteristics": _extract_characteristics(qa_row),
            "original_row": qa_row.to_dict(),
        }
        rows.append(row_data)

    return rows
