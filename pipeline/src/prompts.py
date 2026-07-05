"""
Prompt template management for the generation pipeline.
"""
import re
import os
from pathlib import Path
from typing import Dict, List, Optional

class PromptManager:
    """Manage prompt templates from prompting.md."""
    
    def __init__(self, prompts_path: str):
        # Try multiple locations for the prompts file
        possible_paths = [
            Path(prompts_path),  # As provided
            Path.cwd() / prompts_path,  # Relative to current working directory
            Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / prompts_path,  # Relative to project root
            Path(__file__).parent.parent / prompts_path,  # From src directory
        ]
        
        self.prompts_path = None
        for path in possible_paths:
            if path.exists():
                self.prompts_path = path
                break
        
        if self.prompts_path is None:
            # List all files to help debug
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
        
        # Parse templates by dataset and method
        templates = {}
        
        # Split by headers (### or ##)
        sections = re.split(r'#{2,3}\s+', content)
        for section in sections:
            if not section.strip():
                continue
            
            lines = section.strip().split('\n')
            if not lines:
                continue
                
            # Try to find the dataset and method in the header
            header = lines[0].strip()
            
            # Parse header like "ARQA - zero_shot" or "ARQA\n### zero_shot"
            if ' - ' in header:
                dataset, method = header.split(' - ', 1)
                template = '\n'.join(lines[1:]).strip()
                
                if dataset not in templates:
                    templates[dataset] = {}
                templates[dataset][method] = template
            elif header in ['ARQA', 'DeepJSONEval', 'SchemaToJSON']:
                dataset = header
                # Look for method headers in the content
                method_sections = re.split(r'###\s+', '\n'.join(lines[1:]))
                for method_section in method_sections:
                    if not method_section.strip():
                        continue
                    method_lines = method_section.strip().split('\n')
                    if method_lines:
                        method = method_lines[0].strip()
                        template = '\n'.join(method_lines[1:]).strip()
                        if dataset not in templates:
                            templates[dataset] = {}
                        templates[dataset][method] = template
        
        return templates
    
    def get_template(self, dataset: str, method: str) -> str:
        """Get template for specific dataset and method."""
        return self.templates.get(dataset, {}).get(method, "")
    
    def fill_prompt(self, template: str, fields: Dict) -> str:
        """Fill template placeholders with values."""
        prompt = template
        for key, value in fields.items():
            placeholder = f"%{{{key}}}%"
            prompt = prompt.replace(placeholder, str(value) if value is not None else '')
        return prompt