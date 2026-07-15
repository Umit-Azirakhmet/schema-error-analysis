"""
SchemaToJSON dataset loader.

This module handles loading the SchemaToJSON dataset,
formatting target cells as coordinate lists,
and preparing prompt fields for the generation pipeline.
"""

import pandas as pd
import ast
from typing import Dict, List, Any, Optional


def load_schema_to_json_dataset(dataset_path: str) -> List[Dict[str, Any]]:
    """
    Load SchemaToJSON dataset and prepare rows for generation.
    
    Args:
        dataset_path: Path to the SchemaToJSON CSV file
        
    Returns:
        List of dictionaries, each containing:
            - dataset: "SchemaToJSON"
            - row_id: Generated ID or existing ID
            - row_index: Index in the dataset
            - prompt_fields: Fields needed for prompt templates
            - gold_json_raw: Original gold JSON value
            - characteristics: Empty dict (to be filled later)
            - original_row: Complete original row data
    """
    # Load the dataset
    df = pd.read_csv(dataset_path)
    
    rows = []
    
    for idx, row in df.iterrows():
        # Create row ID if not present, otherwise use existing
        if 'id' in df.columns and pd.notna(row.get('id')):
            row_id = str(row['id'])
        else:
            row_id = f"schema_to_json_{idx:06d}"
        
        # Parse target_cells if it's a string representation of a list
        target_cells = row.get('target_cells', '[]')
        if isinstance(target_cells, str):
            try:
                # Try to parse as Python literal (list of coordinates)
                target_cells_parsed = ast.literal_eval(target_cells)
                # Format as coordinate lists (i, j, k)
                if isinstance(target_cells_parsed, list):
                    # Convert to string representation of coordinate lists
                    target_cells_formatted = str(target_cells_parsed)
                else:
                    target_cells_formatted = str(target_cells_parsed)
            except (ValueError, SyntaxError):
                # If parsing fails, keep as is
                target_cells_formatted = str(target_cells)
        else:
            # If already a list or other type, convert to string
            target_cells_formatted = str(target_cells)
        
        # Prepare prompt fields
        prompt_fields = {
            'table_code': str(row.get('table_code', '')),
            'sup_text': str(row.get('sup_text', '')),
            'target_cells': target_cells_formatted
        }
        
        # Get gold JSON - keep exactly as in CSV
        gold_value = row.get("gold_json", row.get("gold_json_records", ""))
        gold_json_raw = str(gold_value) if pd.notna(gold_value) else ""
        
        # Create row wrapper
        row_data = {
            'dataset': 'SchemaToJSON',
            'row_id': row_id,
            'row_index': idx,
            'prompt_fields': prompt_fields,
            'gold_json_raw': gold_json_raw,
            'characteristics': {},  # Will be filled by active_characteristics.json later
            'original_row': row.to_dict()
        }
        
        rows.append(row_data)
    
    return rows


def format_target_cells(target_cells: Any) -> str:
    """
    Format target cells as coordinate lists (i, j, k).
    
    This is a helper function that can be used separately if needed.
    
    Args:
        target_cells: Target cells in various formats
        
    Returns:
        Formatted string representation of target cells
    """
    if target_cells is None:
        return '[]'
    
    if isinstance(target_cells, str):
        try:
            parsed = ast.literal_eval(target_cells)
            return str(parsed)
        except:
            return target_cells
    elif isinstance(target_cells, list):
        return str(target_cells)
    else:
        return str(target_cells)


def get_dataset_info() -> Dict[str, Any]:
    """
    Return dataset metadata for SchemaToJSON.
    
    Returns:
        Dictionary with dataset metadata
    """
    return {
        'name': 'SchemaToJSON',
        'description': 'Dataset for converting table schemas to JSON',
        'required_fields': ['table_code', 'sup_text', 'target_cells'],
        'optional_fields': ['id', 'gold_json'],
        'has_gold_json': True,
        'id_column': 'id'  # or generated if not present
    }


# Example usage (commented out)
if __name__ == "__main__":
    # Test loading the dataset
    # rows = load_schema_to_json_dataset('data/schema_to_json.csv')
    # print(f"Loaded {len(rows)} rows")
    # if rows:
    #     print(f"First row: {rows[0]['row_id']}")
    #     print(f"Prompt fields: {rows[0]['prompt_fields'].keys()}")
    pass