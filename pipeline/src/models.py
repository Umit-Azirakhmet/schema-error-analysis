"""
Model wrapper for Hugging Face inference.
"""
import importlib.util
import time
from typing import Dict, Any
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM


class ModelWrapper:
    """Wrapper for language model inference."""

    def __init__(self, model_name: str, generation_config: Dict):
        self.model_name = model_name
        self.generation_config = generation_config
        self.tokenizer = None
        self.model = None
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self._load_model()

    def _resolve_dtype(self):
        """Pick a stable dtype for the model.

        Gemma-3 is trained in bfloat16; float16 causes numerical blow-up
        that fills the generation with special tokens (empty decode, hits
        max_new_tokens). Prefer bf16 when available, else fall back.
        """
        name = self.model_name.lower()
        if "gemma-3" in name or "gemma3" in name:
            if torch.cuda.is_available() and torch.cuda.is_bf16_supported():
                return torch.bfloat16
            return torch.float32
        return torch.float16

    def _resolve_attn_implementation(self):
        """Prefer Flash Attention 2 when installed; otherwise use SDPA."""
        if importlib.util.find_spec("flash_attn") is not None:
            return "flash_attention_2"
        return "sdpa"

    def _load_model(self):
        """Load model and tokenizer once on a single GPU."""
        dtype = self._resolve_dtype()
        preferred_attn = self._resolve_attn_implementation()
        attn_attempts = [preferred_attn]
        if preferred_attn != "sdpa":
            attn_attempts.append("sdpa")

        print(f"Loading model: {self.model_name} (dtype={dtype}, device={self.device})")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

        last_error = None
        for attn_impl in attn_attempts:
            try:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=dtype,
                    attn_implementation=attn_impl,
                ).to(self.device)
                self.model.eval()
                print(f"Model loaded successfully (attn_implementation={attn_impl})")
                return
            except Exception as exc:
                last_error = exc
                print(f"Failed to load with attn_implementation={attn_impl}: {exc}")

        raise RuntimeError(f"Could not load model {self.model_name}") from last_error

    def _format_prompt(self, prompt: str) -> str:
        """Apply chat template; disable Qwen3 thinking via enable_thinking=False."""
        if not getattr(self.tokenizer, "chat_template", None):
            return prompt

        messages = [{"role": "user", "content": prompt}]
        kwargs = {
            "tokenize": False,
            "add_generation_prompt": True,
        }
        # Qwen3 hard switch: disable thinking/reasoning blocks
        if "qwen3" in self.model_name.lower():
            kwargs["enable_thinking"] = False

        return self.tokenizer.apply_chat_template(messages, **kwargs)

    def generate(self, prompt: str) -> Dict[str, Any]:
        """
        Generate response from the model.

        Returns:
            Dict with raw_response, input_tokens, output_tokens, latency_ms
        """
        start_time = time.time()

        try:
            formatted_prompt = self._format_prompt(prompt)
            inputs = self.tokenizer(formatted_prompt, return_tensors="pt")
            input_tokens = inputs["input_ids"].shape[1]

            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.inference_mode():
                outputs = self.model.generate(
                    **inputs,
                    **self.generation_config,
                    pad_token_id=self.tokenizer.eos_token_id,
                    use_cache=True,
                )

            generated_ids = outputs[0][input_tokens:]
            raw_response = self.tokenizer.decode(
                generated_ids, skip_special_tokens=True
            ).strip()

            output_tokens = outputs.shape[1] - input_tokens
            latency_ms = (time.time() - start_time) * 1000

            return {
                "raw_response": raw_response,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "latency_ms": latency_ms,
                "error": None,
            }

        except Exception as e:
            return {
                "raw_response": None,
                "input_tokens": None,
                "output_tokens": None,
                "latency_ms": (time.time() - start_time) * 1000,
                "error": str(e),
            }
