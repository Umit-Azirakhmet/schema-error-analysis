"""Two-stage NL-to-Format and direct FRI generation interfaces.

Stub module for the evaluation pipeline. Full model integration is deferred;
prompt templates live in ``prompts/example_prompts.md``.

Error attribution (NL-to-Format vs direct FRI):
  - Wrong task answer in NL ........................ Stage 1
  - Valid NL, invalid JSON syntax .................. Stage 2
  - Valid JSON, schema violation ................... Stage 2
  - Schema-valid but wrong content ................. Stage 1 or Stage 2

Direct FRI collapses formatting and task solving into one call; failures
cannot be attributed to a separate formatting stage.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass
class GenerationResult:
    """Output from a generation run (FRI or NL-to-Format)."""

    stage1_nl: str | None
    """Natural-language response from Stage 1 (NL-to-Format only)."""

    stage2_json_raw: str
    """Raw model output for the JSON stage (FRI: sole output; NL-to-Format: Stage 2)."""

    stage2_json_parsed: dict | list | None
    """Parsed JSON object, or None if ``json.loads`` fails (no repair)."""

    schema_valid: bool
    """Whether ``stage2_json_parsed`` passes ``jsonschema.validate``."""

    json_valid: bool
    """Whether ``stage2_json_parsed`` is non-None."""


class Model(Protocol):
    """Minimal model interface for generation stubs."""

    def generate(self, prompt: str) -> str:
        """Return the model's text completion for *prompt*."""


def run_nl_to_format(
    row: dict[str, Any],
    dataset: str,
    model: Model,
    prompts_path: Path | str,
) -> GenerationResult:
    """Run two-stage NL-to-Format generation for one dataset row.

    Stage 1: prompt with task description and NL format instructions only
    (no JSON schema). Model produces free-text reasoning + answer.

    Stage 2: prompt with Stage 1 response, target schema / output structure,
    and conversion instruction. Model produces JSON only.

    Args:
        row: One dataset record (fields depend on dataset).
        dataset: One of ``"arqa"``, ``"deepjsoneval"``, ``"schematojson"``.
        model: Object implementing ``generate(prompt) -> str``.
        prompts_path: Path to ``prompts/example_prompts.md`` (or split templates).

    Returns:
        GenerationResult with both stages populated. Evaluation should compare
        Stage 1 extracted answer vs gold (task accuracy) and Stage 2 vs schema
        (compliance) and vs gold JSON (semantic).
    """
    raise NotImplementedError(
        "Load NL-to-Format templates from prompts_path, run Stage 1 then Stage 2."
    )


def run_direct_fri(
    row: dict[str, Any],
    dataset: str,
    model: Model,
    num_shots: int,
    prompts_path: Path | str,
) -> GenerationResult:
    """Run direct format-restricting instruction (FRI) generation.

    Single call with task input, JSON schema (or output structure), and
    instruction to return only valid JSON. When ``num_shots > 0``, few-shot
    examples are included from the dataset CSV at generation time.

    Args:
        row: One dataset record.
        dataset: One of ``"arqa"``, ``"deepjsoneval"``, ``"schematojson"``.
        model: Object implementing ``generate(prompt) -> str``.
        num_shots: 0 for zero-shot; 2+ for few-shot (examples sampled per run).
        prompts_path: Path to prompt templates.

    Returns:
        GenerationResult with ``stage1_nl=None``; only ``stage2_*`` fields set.
    """
    raise NotImplementedError(
        "Load FRI templates from prompts_path, fill row placeholders, call model."
    )
