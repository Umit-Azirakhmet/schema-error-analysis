import time


class SimpleTestModel:
    """
    Temporary model wrapper for testing the generation pipeline.

    This has the same interface as a real model:
    - load_model(model_name)
    - model.generate(prompt, generation_config)
    """

    def __init__(self, model_name):
        self.model_name = model_name

    def generate(self, prompt, generation_config=None):
        start = time.time()

        raw_text = '{"answer": "TEST RAW RESPONSE", "claims": []}'

        latency_ms = int((time.time() - start) * 1000)

        return {
            "raw_text": raw_text,
            "input_tokens": None,
            "output_tokens": None,
            "latency_ms": latency_ms,
        }


def load_model(model_name):
    """
    Load the model once at the beginning of the run.

    For now, this returns a test model so the pipeline can run.
    Later, this can be replaced with Hugging Face or vLLM.
    """

    print(f"Loading model once: {model_name}")
    return SimpleTestModel(model_name)