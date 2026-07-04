import json
import sys
from datetime import datetime
from pathlib import Path

# Let this script import from src/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.datasets import load_dataset
from src.generation import generate_one_row
from src.models import load_model


def load_simple_yaml(path):
    """
    Tiny YAML reader for this assignment config.
    Supports simple key: value pairs and one nested generation block.
    Avoids requiring PyYAML.
    """

    config = {}
    current_section = None

    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()

        if not line.strip() or line.strip().startswith("#"):
            continue

        # Nested generation section
        if not raw_line.startswith(" ") and line.endswith(":"):
            current_section = line[:-1]
            config[current_section] = {}
            continue

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        # Convert values
        if value.lower() == "null":
            value = None
        elif value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        else:
            # Try int/float
            try:
                if "." in value:
                    value = float(value)
                else:
                    value = int(value)
            except ValueError:
                value = value.strip('"').strip("'")

        if raw_line.startswith(" ") and current_section:
            config[current_section][key] = value
        else:
            config[key] = value
            current_section = None

    return config


def make_run_id(dataset, model_name, method):
    """
    Create run folder name like:
    20260704_arqa_qwen3_zero_shot
    """

    today = datetime.now().strftime("%Y%m%d")

    clean_dataset = dataset.lower().replace(" ", "_")
    clean_model = (
        model_name.lower()
        .replace("/", "_")
        .replace("-", "_")
        .replace(".", "_")
        .replace(" ", "_")
    )

    return f"{today}_{clean_dataset}_{clean_model}_{method}"


def load_completed_row_ids(responses_path):
    """
    Support resume:
    if responses.jsonl already exists, skip successful rows already saved.
    """

    completed = set()

    if not responses_path.exists():
        return completed

    with open(responses_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                record = json.loads(line)
                if record.get("error") is None:
                    completed.add(record.get("row_id"))
            except json.JSONDecodeError:
                continue

    return completed


def write_jsonl_record(path, record):
    """
    Append one result row to responses.jsonl immediately.
    """

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_manifest(path, manifest):
    """
    Write manifest.json.
    """

    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def main():
    config_path = "configs/run.yaml"
    config = load_simple_yaml(config_path)

    dataset = config["dataset"]
    dataset_path = config["dataset_path"]
    context_path = config.get("context_path")
    prompts_path = config.get("prompts_path")
    model_name = config["model_name"]
    method = config["method"]
    num_shots = int(config.get("num_shots", 0))
    random_seed = int(config.get("random_seed", 42))
    max_rows = config.get("max_rows")
    generation_config = config.get("generation", {})
    output_root = Path(config.get("output_root", "outputs"))

    # Load selected dataset
    rows = load_dataset(
        dataset_name=dataset,
        dataset_path=dataset_path,
        context_path=context_path,
        max_rows=max_rows,
    )

    # Create run folder
    run_id = make_run_id(dataset, model_name, method)
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = run_dir / "manifest.json"
    responses_path = run_dir / "responses.jsonl"

    # Load model ONCE
    model = load_model(model_name)

    completed_row_ids = load_completed_row_ids(responses_path)

    completed_rows = 0
    failed_rows = 0

    created_at = datetime.now().isoformat(timespec="seconds")

    print(f"Run ID: {run_id}")
    print(f"Dataset: {dataset}")
    print(f"Rows loaded: {len(rows)}")
    print(f"Method: {method}")
    print(f"Model: {model_name}")
    print(f"Output: {run_dir}")

    for row in rows:
        row_id = row["row_id"]

        if row_id in completed_row_ids:
            print(f"Skipping already completed row: {row_id}")
            completed_rows += 1
            continue

        print(f"Generating row {row['row_index']}: {row_id}")

        result = generate_one_row(
            row=row,
            all_rows=rows,
            dataset=dataset,
            method=method,
            model=model,
            model_name=model_name,
            num_shots=num_shots,
            random_seed=random_seed,
            generation_config=generation_config,
            run_id=run_id,
        )

        write_jsonl_record(responses_path, result)

        if result["error"] is None:
            completed_rows += 1
        else:
            failed_rows += 1

    manifest = {
        "run_id": run_id,
        "created_at": created_at,
        "dataset": dataset,
        "dataset_path": dataset_path,
        "context_path": context_path if context_path else None,
        "prompts_path": prompts_path,
        "model": model_name,
        "method": method,
        "num_shots": num_shots,
        "generation_config": generation_config,
        "max_rows": max_rows,
        "total_rows": len(rows),
        "completed_rows": completed_rows,
        "failed_rows": failed_rows,
    }

    write_manifest(manifest_path, manifest)

    print()
    print("Done.")
    print(f"Wrote manifest: {manifest_path}")
    print(f"Wrote responses: {responses_path}")


if __name__ == "__main__":
    main()