"""
Generation logic for zero-shot, few-shot, and NL-to-Format methods.
"""
import json
import random
<<<<<<< HEAD
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
=======
import re
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
import numpy as np
>>>>>>> 1b4301fa5fa5691a639c379431f8d29270174332
import pandas as pd

# Import dataset loaders
from src.datasets import (
    load_arqa_dataset,
    load_deepjson_dataset,
    load_schema_to_json_dataset
)

<<<<<<< HEAD
class GenerationRunner:
    """Main generation runner."""
    
=======
# Instance field order/labels for few-shot examples (matches prompting.md).
FEW_SHOT_FIELD_LAYOUT = {
    'ARQA': [
        ('question', 'Question'),
        ('context_paragraphs', 'Context paragraphs'),
        ('tables', 'Tables'),
    ],
    'DeepJSONEval': [
        ('schema', 'Schema'),
        ('text', 'Text'),
    ],
    'SchemaToJSON': [
        ('table_code', 'Table code'),
        ('sup_text', 'Supplementary text'),
        ('target_cells', 'Target cells'),
    ],
}

# Matches "PART 1 - Natural Language Response:" and "PART 1:" style headers.
_PART1_PATTERN = re.compile(
    r'PART\s*1\s*(?:-\s*[^\n]*)?\s*:\s*(.*?)(?=PART\s*2\s*(?:-\s*[^\n]*)?\s*:|$)',
    re.DOTALL | re.IGNORECASE,
)
_PART2_PATTERN = re.compile(
    r'PART\s*2\s*(?:-\s*[^\n]*)?\s*:\s*(.*?)$',
    re.DOTALL | re.IGNORECASE,
)

_PART_LABEL_PREFIXES = {
    'natural language response',
    'natural language',
    'json response',
    'json',
}


def _strip_part_label(text: str) -> str:
    """Drop a repeated section title if it appears as the first content line."""
    text = text.strip()
    first_newline = text.find('\n')
    if first_newline == -1:
        return text

    first_line = text[:first_newline].strip().lower()
    if first_line in _PART_LABEL_PREFIXES:
        return text[first_newline + 1:].strip()
    return text


class GenerationRunner:
    """Main generation runner."""

    @staticmethod
    def _to_json_safe(value: Any) -> Any:
        """Convert numpy/pandas scalars to native Python types for JSON output."""
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, dict):
            return {key: GenerationRunner._to_json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [GenerationRunner._to_json_safe(item) for item in value]
        return value

>>>>>>> 1b4301fa5fa5691a639c379431f8d29270174332
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
<<<<<<< HEAD
            raise ValueError(f"Unknown dataset: {dataset}")
=======
            raise ValueError(f"Unknown dataset: {dataset}. Dataset options are: ARQA, DeepJSONEval, SchemaToJSON")
>>>>>>> 1b4301fa5fa5691a639c379431f8d29270174332
    
    # ===== FEW-SHOT HELPERS =====
    
    def _get_few_shot_examples(self, all_rows, current_index, num_shots):
        """
        Select few-shot examples from other rows in the dataset.
        
        Args:
            all_rows: List of all dataset rows
            current_index: Index of the current row being processed
            num_shots: Number of examples to select
            
        Returns:
<<<<<<< HEAD
            List of example dictionaries with 'input' and 'gold_json' fields
=======
            List of example dictionaries with 'prompt_fields' and 'gold_json' fields
>>>>>>> 1b4301fa5fa5691a639c379431f8d29270174332
        """
        # Set fixed random seed for reproducibility
        random.seed(self.config.get('random_seed', 42))
        
        # Get indices of ALL OTHER rows (exclude current)
        other_indices = [i for i in range(len(all_rows)) if i != current_index]
        
        # If there aren't enough rows, use all available
        num_to_select = min(num_shots, len(other_indices))
        
        # Randomly select examples
        selected_indices = random.sample(other_indices, num_to_select)
        
        examples = []
        for idx in selected_indices:
            row = all_rows[idx]
<<<<<<< HEAD
            # Format the input fields
            input_text = '\n'.join([
                f"{k}: {v}" for k, v in row['prompt_fields'].items() 
                if v and v != ''  # Only include non-empty fields
            ])
            
            example = {
                'input': input_text,
                'gold_json': row['gold_json_raw']
            }
            examples.append(example)
        
        return examples
    
    def _format_few_shots(self, examples):
=======
            examples.append({
                'prompt_fields': row['prompt_fields'],
                'gold_json': row['gold_json_raw'],
            })
        
        return examples
    
    def _format_example_input(self, prompt_fields: Dict, dataset: str) -> str:
        """Format one few-shot example input using the same labels as prompting.md."""
        layout = FEW_SHOT_FIELD_LAYOUT.get(dataset, [])
        sections = []

        for field_key, label in layout:
            value = prompt_fields.get(field_key, '')
            if value is None or not str(value).strip():
                continue
            sections.append(f"{label}:\n{value}")

        return '\n\n'.join(sections)
    
    def _format_few_shots(self, examples, dataset=None):
>>>>>>> 1b4301fa5fa5691a639c379431f8d29270174332
        """
        Format few-shot examples for insertion into the prompt template.
        
        Args:
            examples: List of example dictionaries
<<<<<<< HEAD
=======
            dataset: Dataset name for field layout (defaults to config dataset)
>>>>>>> 1b4301fa5fa5691a639c379431f8d29270174332
            
        Returns:
            Formatted string with all examples
        """
        if not examples:
            return ""
        
<<<<<<< HEAD
        formatted = "\n\nExamples:\n"
        for i, example in enumerate(examples, 1):
            formatted += f"\nExample {i}:\n"
            formatted += f"Input:\n{example['input']}\n"
            formatted += f"Expected JSON:\n{example['gold_json']}\n"
=======
        dataset = dataset or self.config.get('dataset', '')
        formatted = "\n\nExamples:\n"
        for i, example in enumerate(examples, 1):
            input_text = self._format_example_input(example['prompt_fields'], dataset)
            formatted += f"\nExample {i}:\n"
            formatted += f"{input_text}\n\n"
            formatted += f"JSON Response:\n{example['gold_json']}\n"
>>>>>>> 1b4301fa5fa5691a639c379431f8d29270174332
        
        return formatted
    
    # ===== NL-TO-FORMAT HELPERS =====
    
    def _build_nl_to_format_prompt(self, template, prompt_fields):
        """
        Build NL-to-Format prompt with special formatting.
        
        NL-to-Format requires the model to respond in two parts:
        PART 1: Natural language explanation
        PART 2: JSON response
        
        Args:
            template: The template string
            prompt_fields: Dictionary of fields to fill
            
        Returns:
            Filled prompt string
        """
        # For NL-to-Format, we use the same fill_prompt logic
        # The template itself contains the PART 1 and PART 2 structure
        return self.prompt_manager.fill_prompt(template, prompt_fields)
    
    def _parse_nl_to_format_response(self, raw_response):
        """
        Parse NL-to-Format response to extract PART 1 and PART 2.
        
        Args:
            raw_response: The raw model response
            
        Returns:
            Dictionary with 'nl_part' and 'json_part'
        """
<<<<<<< HEAD
        # Try to find PART 1 and PART 2 in the response
        import re
        
        nl_part = ""
        json_part = ""
        
        # Look for PART 1 and PART 2 markers
        part1_match = re.search(r'PART 1[:\-]\s*(.*?)(?=PART 2[:\-]|$)', raw_response, re.DOTALL | re.IGNORECASE)
        part2_match = re.search(r'PART 2[:\-]\s*(.*?)$', raw_response, re.DOTALL | re.IGNORECASE)
        
        if part1_match:
            nl_part = part1_match.group(1).strip()
        
        if part2_match:
            json_part = part2_match.group(1).strip()
        
        # If no markers found, try to find JSON at the end
        if not json_part and '```json' in raw_response:
            # Extract from code block
            json_match = re.search(r'```json\s*(.*?)\s*```', raw_response, re.DOTALL)
            if json_match:
                json_part = json_match.group(1).strip()
        
=======
        nl_part = ""
        json_part = ""

        if not raw_response:
            return {'nl_part': nl_part, 'json_part': json_part}

        part1_match = _PART1_PATTERN.search(raw_response)
        part2_match = _PART2_PATTERN.search(raw_response)

        if part1_match:
            nl_part = _strip_part_label(part1_match.group(1))

        if part2_match:
            json_part = _strip_part_label(part2_match.group(1))

        # Strip markdown fences from JSON part if present
        if json_part.startswith('```'):
            fenced = re.search(r'^```(?:json)?\s*(.*?)\s*```', json_part, re.DOTALL | re.IGNORECASE)
            if fenced:
                json_part = fenced.group(1).strip()

        # Fallback: extract from a ```json code block anywhere in the response
        if not json_part and '```json' in raw_response:
            json_match = re.search(r'```json\s*(.*?)\s*```', raw_response, re.DOTALL | re.IGNORECASE)
            if json_match:
                json_part = json_match.group(1).strip()

>>>>>>> 1b4301fa5fa5691a639c379431f8d29270174332
        return {
            'nl_part': nl_part,
            'json_part': json_part
        }
    
    # ===== MANIFEST HELPERS =====
    
    def _save_manifest(self, total_rows, completed_rows, failed_rows):
        """
        Save run manifest with metadata about the entire run.
        
        Args:
            total_rows: Total number of rows processed
            completed_rows: Number of rows successfully processed
            failed_rows: Number of rows that failed
        """
        manifest = {
            'run_id': self.run_id,
            'created_at': datetime.now().isoformat(),
            'dataset': self.config['dataset'],
            'dataset_path': self.config['dataset_path'],
            'context_path': self.config.get('context_path'),
            'prompts_path': self.config['prompts_path'],
            'model': self.config['model'],
            'method': self.config['method'],
            'num_shots': self.config.get('num_shots', 0),
            'generation_config': self.config['generation_config'],
            'max_rows': self.config.get('max_rows'),
            'total_rows': total_rows,
            'completed_rows': completed_rows,
            'failed_rows': failed_rows
        }
        
        manifest_path = self.output_dir / 'manifest.json'
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
    
    def _get_processed_ids(self, responses_path):
        """
        Get set of already processed row IDs for resume support.
        
        Args:
            responses_path: Path to the responses.jsonl file
            
        Returns:
            Set of row IDs that have been processed
        """
        if not responses_path.exists():
            return set()
        
        processed = set()
        with open(responses_path, 'r') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    processed.add(data.get('row_id'))
        return processed
    
    # ===== MAIN RUN METHOD =====
    
    def run(self, resume=False):
        """
        Run the generation pipeline.
        
        Args:
            resume: If True, skip already processed rows
        """
        print(f"Starting run: {self.run_id}")
        print(f"Dataset: {self.config['dataset']}")
        print(f"Method: {self.config['method']}")
        print(f"Model: {self.config['model']}")
        print("-" * 50)
        
        # Load dataset
        dataset_path = self.config['dataset_path']
        context_path = self.config.get('context_path')
        loader = self._get_dataset_loader()
        
        # Load rows with appropriate loader
        if self.config['dataset'] == 'ARQA' and context_path:
            all_rows = loader(dataset_path, context_path)
        else:
            all_rows = loader(dataset_path)
        
        # Apply max_rows limit
        max_rows = self.config.get('max_rows')
        if max_rows:
            all_rows = all_rows[:max_rows]
            print(f"Limited to {max_rows} rows (for testing)")
        
        print(f"Total rows to process: {len(all_rows)}")
        
        # Setup output file
        responses_path = self.output_dir / 'responses.jsonl'
        
        # Get already processed IDs (for resume)
        processed_ids = set()
        if resume:
            processed_ids = self._get_processed_ids(responses_path)
            print(f"Resuming: {len(processed_ids)} rows already processed")
        
        # Get prompt template
        dataset_name = self.config['dataset']
        method = self.config['method']
        template = self.prompt_manager.get_template(dataset_name, method)
        
        if not template:
            print(f"WARNING: No template found for {dataset_name} - {method}")
            print("Available templates:")
            for ds in self.prompt_manager.templates:
                print(f"  {ds}: {list(self.prompt_manager.templates[ds].keys())}")
            return
        
        num_shots = self.config.get('num_shots', 3)
        
        # Initialize counters
        completed = 0
        failed = 0
        total = len(all_rows)
        
        # Process each row
        for idx, row_data in enumerate(all_rows):
            row_id = row_data['row_id']
            
            # Skip if already processed (resume)
            if row_id in processed_ids:
                print(f"Skipping row {idx+1}/{total}: {row_id} (already processed)")
                continue
            
            print(f"Processing row {idx+1}/{total}: {row_id}")
            
            try:
                # Build prompt fields from row data
                prompt_fields = row_data['prompt_fields'].copy()
                
                # ===== FEW-SHOT LOGIC =====
                if method == 'few_shot':
                    # Get examples from other rows
                    examples = self._get_few_shot_examples(all_rows, idx, num_shots)
                    # Format them
<<<<<<< HEAD
                    prompt_fields['few_shots'] = self._format_few_shots(examples)
=======
                    prompt_fields['few_shots'] = self._format_few_shots(examples, dataset_name)
>>>>>>> 1b4301fa5fa5691a639c379431f8d29270174332
                    print(f"  Using {len(examples)} few-shot examples")
                else:
                    # Zero-shot or NL-to-Format: no examples
                    prompt_fields['few_shots'] = ""
                
                # Fill the template with all fields
                full_prompt = self.prompt_manager.fill_prompt(template, prompt_fields)
                
                # ===== NL-TO-FORMAT: SEND PROMPT =====
                # For NL-to-Format, we use the same generate() call
                # The template already contains the PART 1 / PART 2 structure
                result = self.model_wrapper.generate(full_prompt)
                
                # ===== NL-TO-FORMAT: PARSE RESPONSE =====
                nl_part = None
                json_part = None
                
                if method == 'nl_to_format' and result['raw_response']:
                    # Parse the response to extract NL and JSON parts
                    parsed = self._parse_nl_to_format_response(result['raw_response'])
                    nl_part = parsed['nl_part']
                    json_part = parsed['json_part']
                    print(f"  Extracted NL part: {len(nl_part) if nl_part else 0} chars")
                    print(f"  Extracted JSON part: {len(json_part) if json_part else 0} chars")
                
                # Create record
                record = {
                    'run_id': self.run_id,
                    'dataset': dataset_name,
                    'row_id': row_id,
                    'row_index': idx,
                    'method': method,
                    'model': self.config['model'],
                    'num_shots': num_shots if method == 'few_shot' else 0,
                    'prompt': full_prompt,
                    'raw_response': result['raw_response'],
                    'gold_json_raw': row_data['gold_json_raw'],
                    'characteristics': row_data.get('characteristics', {}),
                    'input_tokens': result['input_tokens'],
                    'output_tokens': result['output_tokens'],
                    'latency_ms': result['latency_ms'],
                    'error': result['error'],
                    'timestamp': datetime.now().isoformat(),
                    # NL-to-Format specific fields
                    'nl_part': nl_part,
                    'json_part': json_part
                }
                
                # Update counters
                if result['error']:
                    failed += 1
                    print(f"  ❌ Error: {result['error']}")
                else:
                    completed += 1
                    print(f"  ✅ Success ({result['output_tokens']} output tokens)")
                
                # Save to JSONL
                with open(responses_path, 'a', encoding='utf-8') as f:
<<<<<<< HEAD
                    f.write(json.dumps(record) + '\n')
=======
                    f.write(json.dumps(self._to_json_safe(record), ensure_ascii=False) + '\n')
>>>>>>> 1b4301fa5fa5691a639c379431f8d29270174332
                
            except Exception as e:
                failed += 1
                print(f"  ❌ Error processing row {row_id}: {str(e)}")
                
                # Save error record
                record = {
                    'run_id': self.run_id,
                    'dataset': dataset_name,
                    'row_id': row_id,
                    'row_index': idx,
                    'method': method,
                    'model': self.config['model'],
                    'num_shots': num_shots if method == 'few_shot' else 0,
                    'prompt': full_prompt if 'full_prompt' in locals() else None,
                    'raw_response': None,
                    'gold_json_raw': row_data.get('gold_json_raw', ''),
                    'characteristics': row_data.get('characteristics', {}),
                    'input_tokens': None,
                    'output_tokens': None,
                    'latency_ms': None,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat(),
                    'nl_part': None,
                    'json_part': None
                }
                
                with open(responses_path, 'a', encoding='utf-8') as f:
<<<<<<< HEAD
                    f.write(json.dumps(record) + '\n')
=======
                    f.write(json.dumps(self._to_json_safe(record), ensure_ascii=False) + '\n')
>>>>>>> 1b4301fa5fa5691a639c379431f8d29270174332
        
        # Save manifest
        self._save_manifest(total, completed, failed)
        
        # Print summary
        print("-" * 50)
        print("Run complete!")
        print(f"  ✅ Completed: {completed}")
        print(f"  ❌ Failed: {failed}")
        print(f"  📊 Total: {total}")
        print(f"  📁 Output: {self.output_dir}")