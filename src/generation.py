import random
from datetime import datetime

from src.prompts import build_prompt


def format_few_shot_example(row):
    """
    Format one few-shot example using the row's prompt fields and gold JSON.

    This is intentionally simple.
    It does not parse, validate, or clean the gold answer.
    """

    fields = row["prompt_fields"]

    lines = ["Example input:"]

    for key, value in fields.items():
        lines.append(f"{key}: {value}")

    lines.append("")
    lines.append("Example output:")
    lines.append(row.get("gold_json_raw", ""))

    return "\n".join(lines)


def build_few_shots(current_row, all_rows, num_shots, random_seed):
    """
    Select fixed few-shot examples from the same dataset.

    Requirements from assignment:
    - select other rows from same dataset
    - exclude the current row
    - use fixed random seed for reproducibility
    """

    if num_shots <= 0:
        return ""

    candidates = [
        row for row in all_rows
        if row["row_id"] != current_row["row_id"]
    ]

    rng = random.Random(random_seed + current_row["row_index"])

    if len(candidates) <= num_shots:
        selected = candidates
    else:
        selected = rng.sample(candidates, num_shots)

    examples = []

    for i, example_row in enumerate(selected, start=1):
        examples.append(f"Example {i}:")
        examples.append(format_few_shot_example(example_row))

    return "\n\n".join(examples)


def generate_one_row(
    row,
    all_rows,
    dataset,
    method,
    model,
    model_name,
    num_shots,
    random_seed,
    generation_config,
    run_id,
):
    """
    Generate one model response for one dataset row.

    This function:
    1. Builds few-shot examples if needed.
    2. Fills the prompt template.
    3. Sends the prompt to the model.
    4. Returns a response record.

    It does NOT:
    - validate JSON
    - validate schema
    - clean output
    - calculate accuracy
    - do error analysis
    """

    few_shots = ""

    if method == "few_shot":
        few_shots = build_few_shots(
            current_row=row,
            all_rows=all_rows,
            num_shots=num_shots,
            random_seed=random_seed,
        )

    prompt = build_prompt(
        dataset=dataset,
        method=method,
        prompt_fields=row["prompt_fields"],
        few_shots=few_shots,
    )

    timestamp = datetime.now().isoformat(timespec="seconds")

    try:
        model_result = model.generate(
            prompt=prompt,
            generation_config=generation_config,
        )

        return {
            "run_id": run_id,
            "dataset": row["dataset"],
            "row_id": row["row_id"],
            "row_index": row["row_index"],
            "method": method,
            "model": model_name,
            "num_shots": num_shots,
            "prompt": prompt,
            "raw_response": model_result.get("raw_text"),
            "gold_json_raw": row.get("gold_json_raw", ""),
            "characteristics": row.get("characteristics", {}),
            "input_tokens": model_result.get("input_tokens"),
            "output_tokens": model_result.get("output_tokens"),
            "latency_ms": model_result.get("latency_ms"),
            "error": None,
            "timestamp": timestamp,
        }

    except Exception as e:
        return {
            "run_id": run_id,
            "dataset": row["dataset"],
            "row_id": row["row_id"],
            "row_index": row["row_index"],
            "method": method,
            "model": model_name,
            "num_shots": num_shots,
            "prompt": prompt,
            "raw_response": None,
            "gold_json_raw": row.get("gold_json_raw", ""),
            "characteristics": row.get("characteristics", {}),
            "input_tokens": None,
            "output_tokens": None,
            "latency_ms": None,
            "error": str(e),
            "timestamp": timestamp,
        }