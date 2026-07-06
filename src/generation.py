"""
Generation logic for zero-shot, few-shot, and NL-to-Format methods.
"""
import json
import random
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Set

import numpy as np
from tqdm import tqdm

from src.datasets import (
    load_arqa_dataset,
    load_deepjson_dataset,
    load_schema_to_json_dataset,
)


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

    def __init__(self, config, prompt_manager, model_wrapper, output_dir, run_id):
        self.config = config
        self.prompt_manager = prompt_manager
        self.model_wrapper = model_wrapper
        self.output_dir = Path(output_dir)
        self.run_id = run_id
        self.created_at = datetime.now().isoformat()

    def _get_dataset_loader(self):
        """Get appropriate dataset loader based on config."""
        dataset = self.config["dataset"]
        if dataset == "ARQA":
            return load_arqa_dataset
        if dataset == "DeepJSONEval":
            return load_deepjson_dataset
        if dataset == "SchemaToJSON":
            return load_schema_to_json_dataset
        raise ValueError(f"Unknown dataset: {dataset}")

    def _resolve_path(self, path: str) -> Path:
        """Resolve dataset paths relative to pipeline or project root."""
        pipeline_root = Path(__file__).parent.parent
        project_root = pipeline_root.parent

        candidates = [
            Path(path),
            Path.cwd() / path,
            pipeline_root / path,
            project_root / path,
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        searched = "\n".join(f"  - {candidate}" for candidate in candidates)
        raise FileNotFoundError(f"Could not find file: {path}\nSearched:\n{searched}")

    def _load_rows(self) -> List[Dict]:
        """Load dataset rows based on config."""
        loader = self._get_dataset_loader()
        dataset = self.config["dataset"]
        dataset_path = str(self._resolve_path(self.config["dataset_path"]))

        if dataset == "ARQA":
            context_path = str(self._resolve_path(self.config["context_path"]))
            rows = loader(dataset_path, context_path)
        else:
            rows = loader(dataset_path)

        max_rows = self.config.get("max_rows")
        if max_rows is not None:
            rows = rows[:max_rows]

        return rows

    def _num_shots_for_method(self) -> int:
        if self.config["method"] == "few_shot":
            return self.config.get("num_shots", 3)
        return 0

    def _format_few_shot_example(self, row: Dict) -> str:
        """Format a single few-shot demonstration."""
        lines = ["Example:"]
        for key, value in row["prompt_fields"].items():
            if value:
                label = key.replace("_", " ").title()
                lines.append(f"{label}: {value}")

        gold = row.get("gold_json_raw", "")
        if gold:
            lines.append(f"JSON Response: {gold}")

        return "\n".join(lines)

    def _build_few_shots(self, rows: List[Dict], current_index: int) -> str:
        """Build few-shot examples from other rows in the dataset."""
        num_shots = self.config.get("num_shots", 3)
        seed = self.config.get("random_seed", 42)

        candidates = [i for i, row in enumerate(rows) if row["row_index"] != current_index]
        if not candidates:
            return ""

        rng = random.Random(seed + current_index)
        shot_indices = rng.sample(candidates, min(num_shots, len(candidates)))
        examples = [self._format_few_shot_example(rows[i]) for i in shot_indices]
        return "\n\n".join(examples)

    def _build_prompt(self, row: Dict, rows: List[Dict]) -> str:
        """Build the filled prompt for a single row."""
        dataset = self.config["dataset"]
        method = self.config["method"]

        template = self.prompt_manager.get_template(dataset, method)
        if not template:
            raise ValueError(f"No template found for {dataset}/{method}")

        fields = dict(row["prompt_fields"])
        if method == "few_shot":
            fields["few_shots"] = self._build_few_shots(rows, row["row_index"])

        return self.prompt_manager.fill_prompt(template, fields)

    def _responses_path(self) -> Path:
        return self.output_dir / "responses.jsonl"

    def _manifest_path(self) -> Path:
        return self.output_dir / "manifest.json"

    def _load_completed_ids(self) -> Set[str]:
        """Load row IDs that were already successfully processed."""
        responses_path = self._responses_path()
        completed = set()

        if not responses_path.exists():
            return completed

        with open(responses_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if record.get("error") is None:
                    completed.add(record["row_id"])

        return completed

    def _load_existing_responses(self) -> List[Dict]:
        responses_path = self._responses_path()
        if not responses_path.exists():
            return []

        responses = []
        with open(responses_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    responses.append(json.loads(line))
        return responses

    def _save_manifest(self, total_rows: int, completed_rows: int, failed_rows: int):
        context_path = self.config.get("context_path")
        manifest = {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "dataset": self.config["dataset"],
            "dataset_path": self.config["dataset_path"],
            "context_path": context_path if self.config["dataset"] == "ARQA" else None,
            "prompts_path": self.config["prompts_path"],
            "model": self.config["model"],
            "method": self.config["method"],
            "num_shots": self._num_shots_for_method(),
            "generation_config": self.config.get("generation_config", {}),
            "max_rows": self.config.get("max_rows"),
            "total_rows": total_rows,
            "completed_rows": completed_rows,
            "failed_rows": failed_rows,
        }

        with open(self._manifest_path(), "w", encoding="utf-8") as handle:
            json.dump(self._to_json_safe(manifest), handle, indent=2)

    def _append_result(self, result: Dict):
        """Append a single generation result to the output file."""
        with open(self._responses_path(), "a", encoding="utf-8") as handle:
            handle.write(json.dumps(self._to_json_safe(result), ensure_ascii=False) + "\n")

    def _build_result(self, row: Dict, prompt: str, generation: Dict) -> Dict:
        return {
            "run_id": self.run_id,
            "dataset": row["dataset"],
            "row_id": row["row_id"],
            "row_index": row["row_index"],
            "method": self.config["method"],
            "model": self.config["model"],
            "num_shots": self._num_shots_for_method(),
            "prompt": prompt,
            "raw_response": generation.get("raw_response"),
            "gold_json_raw": row.get("gold_json_raw", ""),
            "characteristics": row.get("characteristics", {}),
            "input_tokens": generation.get("input_tokens"),
            "output_tokens": generation.get("output_tokens"),
            "latency_ms": generation.get("latency_ms"),
            "error": generation.get("error"),
            "timestamp": datetime.now().isoformat(),
        }

    def run(self, resume: bool = False):
        """Run generation over the configured dataset."""
        print(f"Starting generation run: {self.run_id}")
        print(f"Dataset: {self.config['dataset']}, Method: {self.config['method']}")
        print(f"Output directory: {self.output_dir}")

        rows = self._load_rows()
        print(f"Loaded {len(rows)} rows")

        completed_ids = self._load_completed_ids() if resume else set()
        if resume and completed_ids:
            print(f"Resuming: skipping {len(completed_ids)} completed rows")

        pending_rows = [row for row in rows if row["row_id"] not in completed_ids]
        print(f"Processing {len(pending_rows)} rows")

        existing_responses = self._load_existing_responses() if resume else []
        failed_rows = sum(1 for record in existing_responses if record.get("error") is not None)

        for row in tqdm(pending_rows, desc="Generating"):
            prompt = self._build_prompt(row, rows)
            generation = self.model_wrapper.generate(prompt)
            result = self._build_result(row, prompt, generation)
            self._append_result(result)
            if result["error"] is not None:
                failed_rows += 1

        completed_rows = len(self._load_completed_ids())
        self._save_manifest(
            total_rows=len(rows),
            completed_rows=completed_rows,
            failed_rows=failed_rows,
        )

        print(f"Generation complete. Results saved to {self._responses_path()}")
