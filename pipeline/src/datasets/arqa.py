"""
ARQA dataset loader with context joining.
"""
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional

def load_arqa_dataset(dataset_path: str, context_path: str) -> List[Dict]:
    """Load ARQA dataset and join with context database."""
    # Load datasets
    df = pd.read_csv(dataset_path)
    context_df = pd.read_csv(context_path)
    
    # Join with context on table_id
    df_joined = df.merge(context_df, on='table_id', how='left')
    
    rows = []
    for idx, row in df_joined.iterrows():
        # Prepare prompt fields
        prompt_fields = {
            'question': row.get('question', ''),
            'schema': row.get('schema', ''),
            'tables': row.get('tables', ''),
            'context_paragraphs': row.get('context_paragraphs', '')
        }
        
        # Create row wrapper
        row_data = {
            'dataset': 'ARQA',
            'row_id': str(row.get('qa_id', f'arqa_{idx}')),
            'row_index': idx,
            'prompt_fields': prompt_fields,
            'gold_json_raw': row.get('gold_json', ''),
            'characteristics': {},  # Will be filled later
            'original_row': row.to_dict()
        }
        rows.append(row_data)
    
    return rows