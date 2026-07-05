"""
Generation logic for zero-shot, few-shot, and NL-to-Format methods.
"""
import json
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

# Import dataset loaders
from src.datasets import (
    load_arqa_dataset,
    load_deepjson_dataset,
    load_schema_to_json_dataset
)

class GenerationRunner:
    """Main generation runner."""
    
    def __init__(self, config, prompt_manager, model_wrapper, output_dir, run_id):
        self.config = config
        self.prompt_manager = prompt_manager
        self.model_wrapper = model_wrapper
        self.output_dir = output_dir
        self.run_id = run_id
        
    def _get_dataset_loader(self):
        """Get appropriate dataset loader based on config."""
        dataset = self.config['dataset']
        if dataset == 'ARQA':
            return load_arqa_dataset
        elif dataset == 'DeepJSONEval':
            return load_deepjson_dataset
        elif dataset == 'SchemaToJSON':
            return load_schema_to_json_dataset
        else:
            raise ValueError(f"Unknown dataset: {dataset}")
    
    # ... (rest of the class remains the same)