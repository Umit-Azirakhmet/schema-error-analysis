import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig

def load_model(model_name):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)
    return tokenizer, model

def generate_response(model, tokenizer, prompt, num_shots, random_seed, generation_config):
    prompt = prompt.format(num_shots=num_shots, random_seed=random_seed)
    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(**inputs, **generation_config)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

def evaluate_response(response, ground_truth):
    return response == ground_truth

def evaluate_model(model, tokenizer, prompt, num_shots, random_seed, generation_config, ground_truth):
    response = generate_response(model, tokenizer, prompt, num_shots, random_seed, generation_config)
    return evaluate_response(response, ground_truth)

def main():
    model_name = "Qwen/Qwen3-8B"
    tokenizer, model = load_model(model_name)
    prompt = "What is the capital of France?"
    num_shots = 3
    random_seed = 42
    generation_config = {
        "do_sample": False,
        "temperature": 0,
        "max_new_tokens": 2048
    }
    response = generate_response(model, tokenizer, prompt, num_shots, random_seed, generation_config)