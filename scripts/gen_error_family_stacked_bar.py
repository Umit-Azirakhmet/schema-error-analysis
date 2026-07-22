#!/usr/bin/env python3
"""100%-normalized stacked bars of shared error families.

Pools all pipeline/outputs/*/error_analysis.csv runs (all datasets/models/methods),
sums a strict set of shared error columns into five families, and renders one
chart where each bar is the within-family composition of leaf errors.

Usage:
  python scripts/gen_error_family_stacked_bar.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = ROOT / "pipeline" / "outputs"
OUT_DIR = OUTPUTS_DIR / "error_reports" / "stacked_bars"

# Fixed X-axis family order and strict column membership (omit Few-shot
# contamination; keep empty_response_count; ignore trailing_commas /
# unescaped_quotes and all arqa_/s2j_/dj_* extras).
FAMILY_COLUMNS: dict[str, list[str]] = {
    "Completion": [
        "truncated_count",
        "repetition_count",
        "empty_response_count",
    ],
    "Syntax": [
        "invalid_json_syntax_count",
        "backslash_issues_count",
    ],
    "Contamination": [
        "markdown_code_fence_count",
        "python_code_count",
        "explanatory_text_count",
    ],
    "Schema": [
        "hallucinated_fields_count",
        "wrong_field_names_count",
        "missing_fields_count",
        "wrong_nesting_count",
        "wrong_types_count",
        "wrong_order_count",
    ],
    "Content": [
        "incorrect_values_count",
        "placeholder_values_count",
        "longer_shorter_count",
        "different_language_count",
    ],
}

ERROR_LABELS: dict[str, str] = {
    "truncated_count": "Truncated",
    "repetition_count": "Repetition",
    "empty_response_count": "Empty responses",
    "invalid_json_syntax_count": "Invalid JSON syntax",
    "backslash_issues_count": "Backslash issues",
    "markdown_code_fence_count": "Markdown code fence",
    "python_code_count": "Python code",
    "explanatory_text_count": "Explanatory text",
    "hallucinated_fields_count": "Hallucinated fields",
    "wrong_field_names_count": "Wrong field names",
    "missing_fields_count": "Missing fields",
    "wrong_nesting_count": "Wrong nesting",
    "wrong_types_count": "Wrong types",
    "wrong_order_count": "Wrong order",
    "incorrect_values_count": "Incorrect values",
    "placeholder_values_count": "Placeholder values",
    "longer_shorter_count": "Longer/shorter than gold",
    "different_language_count": "Different language",
}

FAMILY_ORDER = list(FAMILY_COLUMNS.keys())
MAPPED_COLUMNS = [c for cols in FAMILY_COLUMNS.values() for c in cols]


def load_all_run_errors(outputs_dir: Path = OUTPUTS_DIR) -> tuple[pd.DataFrame, int]:
    """Load every error_analysis.csv under outputs (no dataset filter)."""
    frames: list[pd.DataFrame] = []
    for run_dir in sorted(outputs_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        csv_path = run_dir / "error_analysis.csv"
        if not csv_path.exists():
            continue
        df = pd.read_csv(csv_path)
        df["run_id"] = run_dir.name
        frames.append(df)

    if not frames:
        raise FileNotFoundError(f"No error_analysis.csv under {outputs_dir}")

    return pd.concat(frames, ignore_index=True), len(frames)


def aggregate_families(df: pd.DataFrame) -> dict[str, Any]:
    """Sum mapped columns and compute within-family shares."""
    missing = [c for c in MAPPED_COLUMNS if c not in df.columns]
    if missing:
        raise KeyError(f"Missing mapped error columns: {missing}")

    families: dict[str, Any] = {}
    for family in FAMILY_ORDER:
        errors: dict[str, Any] = {}
        total = 0
        for col in FAMILY_COLUMNS[family]:
            count = int(df[col].fillna(0).sum())
            total += count
            errors[col] = {"label": ERROR_LABELS[col], "count": count, "share": 0.0}

        for col, entry in errors.items():
            if total > 0:
                entry["share"] = entry["count"] / total
            else:
                entry["share"] = 0.0

        families[family] = {"total": total, "errors": errors}

    return families


def plot_stacked_bars(families: dict[str, Any], out_path: Path) -> None:
    """Draw 100% stacked bars with absolute family totals above each bar."""
    # Distinct colors for every leaf error (stable order across families).
    leaf_order = MAPPED_COLUMNS
    cmap = plt.get_cmap("tab20")
    color_of = {col: cmap(i % 20) for i, col in enumerate(leaf_order)}

    fig, ax = plt.subplots(figsize=(10, 6.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    x = list(range(len(FAMILY_ORDER)))
    bottoms = [0.0] * len(FAMILY_ORDER)
    legend_handles: list[Any] = []
    legend_labels: list[str] = []
    seen_labels: set[str] = set()

    for col in leaf_order:
        heights = []
        for family in FAMILY_ORDER:
            entry = families[family]["errors"].get(col)
            heights.append(100.0 * entry["share"] if entry else 0.0)

        bars = ax.bar(
            x,
            heights,
            bottom=bottoms,
            width=0.65,
            color=color_of[col],
            edgecolor="white",
            linewidth=0.6,
            label=ERROR_LABELS[col],
        )
        bottoms = [b + h for b, h in zip(bottoms, heights)]

        label = ERROR_LABELS[col]
        if label not in seen_labels:
            seen_labels.add(label)
            legend_handles.append(bars)
            legend_labels.append(label)

    for i, family in enumerate(FAMILY_ORDER):
        total = families[family]["total"]
        ax.text(
            i,
            102.5,
            f"{total:,}",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(FAMILY_ORDER)
    ax.set_ylabel("Share of family findings (%)")
    ax.set_xlabel("Error family")
    ax.set_ylim(0, 112)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_title("Error family composition (100% stacked, all runs pooled)")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(False)
    ax.xaxis.grid(False)

    ax.legend(
        legend_handles,
        legend_labels,
        title="Leaf error",
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        frameon=False,
        fontsize=8,
        title_fontsize=9,
    )

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def build_payload(families: dict[str, Any], n_runs: int, png_path: Path) -> dict[str, Any]:
    family_out: dict[str, Any] = {}
    for family in FAMILY_ORDER:
        err_out: dict[str, Any] = {}
        for col, entry in families[family]["errors"].items():
            err_out[ERROR_LABELS[col]] = {
                "column": col,
                "count": entry["count"],
                "share": entry["share"],
            }
        family_out[family] = {
            "total": families[family]["total"],
            "errors": err_out,
        }

    return {
        "definition": (
            "100% stacked bars: X = error family; stack segments = leaf errors "
            "from a strict shared-column map; Y = share within family; "
            "counts pooled across all pipeline/outputs runs"
        ),
        "n_runs": n_runs,
        "families": family_out,
        "png": str(png_path.relative_to(ROOT)).replace("\\", "/"),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df, n_runs = load_all_run_errors()
    families = aggregate_families(df)

    png_path = OUT_DIR / "error_family_composition.png"
    json_path = OUT_DIR / "error_family_composition.json"

    plot_stacked_bars(families, png_path)
    payload = build_payload(families, n_runs, png_path)
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"runs={n_runs}")
    for family in FAMILY_ORDER:
        total = families[family]["total"]
        parts = ", ".join(
            f"{ERROR_LABELS[c]}={families[family]['errors'][c]['count']}"
            for c in FAMILY_COLUMNS[family]
        )
        print(f"  {family}: total={total} ({parts})")
    print(f"Wrote {png_path}")
    print(f"Wrote {json_path}")


if __name__ == "__main__":
    main()
