"""
Prompt template management for the generation pipeline.
"""
import re
import os
from pathlib import Path
from typing import Dict

class PromptManager:
    """Manage prompt templates from prompting.md."""
    
    def __init__(self, prompts_path: str):
        # Try multiple locations for the prompts file
        possible_paths = [
            Path(prompts_path),
            Path.cwd() / prompts_path,
            Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / prompts_path,
            Path(__file__).parent.parent / prompts_path,
        ]
        
        self.prompts_path = None
        for path in possible_paths:
            if path.exists():
                self.prompts_path = path
                break
        
        if self.prompts_path is None:
            print("ERROR: Could not find prompts file. Searched in:")
            for path in possible_paths:
                print(f"  - {path}")
            raise FileNotFoundError(f"Could not find prompts file: {prompts_path}")
        
        print(f"Loading prompts from: {self.prompts_path}")
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict:
        """Load and parse prompt templates from prompting.md."""
        with open(self.prompts_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        templates = {}
        
<<<<<<< HEAD
        # Split by dataset sections (## ARQA, ## DeepJSONEval, ## SchemaToJSON)
        dataset_sections = re.split(r'##\s+', content)
        
        for section in dataset_sections:
=======
        # Split only on level-2 headers (##), not method headers (###)
        sections = re.split(r'(?m)^##\s+', content)
        for section in sections:
>>>>>>> 1b4301fa5fa5691a639c379431f8d29270174332
            if not section.strip():
                continue
            
            lines = section.strip().split('\n')
            if not lines:
                continue
            
            # First line is the dataset name
            dataset = lines[0].strip()
            
            # Skip if not a valid dataset
            if dataset not in ['ARQA', 'DeepJSONEval', 'SchemaToJSON']:
                continue
            
            # Join remaining lines
            section_content = '\n'.join(lines[1:])
            
            # Split by method headers (### Zero-shot, ### Few-shot, ### NL-to-Format)
            method_sections = re.split(r'###\s+', section_content)
            
            for method_section in method_sections:
                if not method_section.strip():
                    continue
                
                method_lines = method_section.strip().split('\n')
                if not method_lines:
                    continue
                
                # First line is the method name
                method_header = method_lines[0].strip()
                
                # Map method names to our internal naming
                method_map = {
                    'Zero-shot': 'zero_shot',
                    'Few-shot': 'few_shot',
                    'NL-to-Format': 'nl_to_format',
                    'Zero Shot': 'zero_shot',
                    'Few Shot': 'few_shot',
                    'NL to Format': 'nl_to_format',
<<<<<<< HEAD
=======
                    'zero_shot': 'zero_shot',
                    'few_shot': 'few_shot',
                    'nl_to_format': 'nl_to_format',
>>>>>>> 1b4301fa5fa5691a639c379431f8d29270174332
                }
                
                method = method_map.get(method_header, method_header.lower().replace(' ', '_'))
                
                # Get the template content (everything after the header)
                template_content = '\n'.join(method_lines[1:]).strip()
                
                # Remove markdown code fences (```text ... ```)
                template_content = re.sub(r'```\w*\n?', '', template_content)
                template_content = template_content.strip()
                
                # Remove any extra separators
                template_content = re.sub(r'^---\s*$', '', template_content, flags=re.MULTILINE)
                template_content = template_content.strip()
                
                if dataset not in templates:
                    templates[dataset] = {}
                
                templates[dataset][method] = template_content
        
        return templates
    
    def get_template(self, dataset: str, method: str) -> str:
        """Get template for specific dataset and method."""
        # Try exact match first
        if dataset in self.templates and method in self.templates[dataset]:
            return self.templates[dataset][method]
        
        # Try case-insensitive match
        for key in self.templates.get(dataset, {}):
            if key.lower() == method.lower():
                return self.templates[dataset][key]
        
        return ""
    
    def fill_prompt(self, template: str, fields: Dict) -> str:
        """Fill template placeholders with values."""
        prompt = template
        for key, value in fields.items():
            placeholder = f"%{{{key}}}%"
            prompt = prompt.replace(placeholder, str(value) if value is not None else '')
        return prompt