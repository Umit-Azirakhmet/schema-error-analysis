#!/usr/bin/env python3
"""
Main entry point for the baseline generation pipeline.
"""
import os
import sys
import json
import yaml
import argparse
from datetime import datetime
from pathlib import Path

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.prompts import PromptManager
from src.models import ModelWrapper
from src.generation import GenerationRunner

def load_config(config_path):
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def generate_run_id(config):
    """Generate a run ID based on config."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dataset = config['dataset'].lower()
    model = config['model'].split('/')[-1].lower()
    method = config['method']
    return f"{timestamp}_{dataset}_{model}_{method}"

def main():
    parser = argparse.ArgumentParser(description='Run baseline generation pipeline')
    parser.add_argument('--config', type=str, default='configs/run.yaml',
                       help='Path to configuration file')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from existing output')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Generate run ID
    run_id = generate_run_id(config)
    print(f"Run ID: {run_id}")
    
    # Setup output directory
    output_dir = Path(config['output_path']) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize components
    prompt_manager = PromptManager(config['prompts_path'])
    model_wrapper = ModelWrapper(config['model'], config['generation_config'])
    
    # Create generation runner
    runner = GenerationRunner(
        config=config,
        prompt_manager=prompt_manager,
        model_wrapper=model_wrapper,
        output_dir=output_dir,
        run_id=run_id
    )
    
    # Run generation
    runner.run(resume=args.resume)

if __name__ == "__main__":
    main()