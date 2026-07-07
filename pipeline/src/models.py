"""
Model wrapper for Hugging Face and vLLM.
"""
import time
from typing import Dict, Any, Optional
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

class ModelWrapper:
    """Wrapper for language model inference."""
    
    def __init__(self, model_name: str, generation_config: Dict):
        self.model_name = model_name
        self.generation_config = generation_config
        self.tokenizer = None
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load model and tokenizer once."""
        print(f"Loading model: {self.model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        print("Model loaded successfully")
    
    def generate(self, prompt: str) -> Dict[str, Any]:
        """
        Generate response from the model.
        
        Returns:
            Dict with raw_response, input_tokens, output_tokens, latency_ms
        """
        start_time = time.time()
        
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt")
            input_tokens = inputs['input_ids'].shape[1]
            
            # Move to same device as model
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    **self.generation_config,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode response
            raw_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Remove prompt from response if it's included
            if raw_response.startswith(prompt):
                raw_response = raw_response[len(prompt):].strip()
            
            output_tokens = outputs.shape[1] - input_tokens
            
            latency_ms = (time.time() - start_time) * 1000
            
            return {
                'raw_response': raw_response,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'latency_ms': latency_ms,
                'error': None
            }
            
        except Exception as e:
            return {
                'raw_response': None,
                'input_tokens': None,
                'output_tokens': None,
                'latency_ms': (time.time() - start_time) * 1000,
                'error': str(e)
            }