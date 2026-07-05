"""
DeepJSONEval dataset loader.
"""
import pandas as pd
from typing import Dict, List

def load_deepjson_dataset(dataset_path: str) -> List[Dict]:
    """Load DeepJSONEval dataset."""
    df = pd.read_csv(dataset_path)
    
    rows = []
    for idx, row in df.iterrows():
        # Create row ID if not present
        row_id = row.get('id', f'deepjson_{idx}')
        
        # Prepare prompt fields
        prompt_fields = {
            'schema': row.get('schema', ''),
            'text': row.get('text', '')
        }
        
        # Create row wrapper
        row_data = {
            'dataset': 'DeepJSONEval',
            'row_id': str(row_id),
            'row_index': idx,
            'prompt_fields': prompt_fields,
            'gold_json_raw': row.get('gold_json', ''),
            'characteristics': {},  # Will be filled later
            'original_row': row.to_dict()
        }
        rows.append(row_data)
    
    return rows
    