#!/usr/bin/env python3
"""100%-normalized stacked bars of shared error families.
Binary version: reads the binary error CSV (0/1 presence).
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# ------------------------------------------------------------
# CONFIGURATION: USE THE BINARY CSV
# ------------------------------------------------------------
INPUT_CSV = r"C:\Users\Justin\SIP-git\schema-error-analysis\pipeline\outputs\full_error_analysis_binary.csv"
# ------------------------------------------------------------

# Output directory
OUTPUT_DIR = Path(INPUT_CSV).parent / "error_reports" / "stacked_bars_binary"

# Fixed X-axis family order and strict column membership
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
        "explanatory_text_count",
    ],
    "Schema": [
        "hallucinated_fields_count",
        "missing_fields_count",
        "wrong_nesting_count",
        "wrong_types_count",
        "wrong_order_count",              # <-- fixed: use full name
        "wrong_nesting_depth_count",      # <-- fixed: use full name
    ],
    "Content": [
        "incorrect_values_count",
        "placeholder_values_count",
        "longer_shorter_count",
        "different_language_count",       # <-- fixed: use full name
    ],
}

ERROR_LABELS: dict[str, str] = {
    "truncated_count": "Truncated",
    "repetition_count": "Repetition",
    "empty_response_count": "Empty responses",
    "invalid_json_syntax_count": "Invalid JSON syntax",
    "backslash_issues_count": "Backslash issues",
    "markdown_code_fence_count": "Markdown code fence",
    "explanatory_text_count": "Explanatory text",
    "hallucinated_fields_count": "Hallucinated fields",
    "missing_fields_count": "Missing fields",
    "wrong_nesting_count": "Wrong nesting",
    "wrong_types_count": "Wrong types",
    "wrong_order_count": "Wrong order",
    "wrong_nesting_depth_count": "Wrong nesting depth",   # <-- ADD THIS
    "incorrect_values_count": "Incorrect values",
    "placeholder_values_count": "Placeholder values",
    "longer_shorter_count": "Longer/shorter than gold",
    "different_language_count": "Different language",
}

FAMILY_ORDER = list(FAMILY_COLUMNS.keys())
MAPPED_COLUMNS = [c for cols in FAMILY_COLUMNS.values() for c in cols]


def load_single_file(csv_path: str) -> pd.DataFrame:
    """Load the single combined CSV file and clean numeric columns."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    df = pd.read_csv(path)
    print(f"✅ Loaded {len(df)} rows from {path.name}")

    # Ensure all mapped columns are numeric (binary), fill NaN with 0
    for col in MAPPED_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            print(f"⚠️  Warning: Column '{col}' not found, skipping")
            df[col] = 0

    return df


def aggregate_families(df: pd.DataFrame) -> dict[str, any]:
    """Sum mapped columns and compute within-family shares."""
    families: dict[str, any] = {}
    for family in FAMILY_ORDER:
        errors: dict[str, any] = {}
        total = 0
        for col in FAMILY_COLUMNS[family]:
            count = int(df[col].sum())
            total += count
            errors[col] = {"label": ERROR_LABELS[col], "count": count, "share": 0.0}

        for col, entry in errors.items():
            if total > 0:
                entry["share"] = entry["count"] / total
            else:
                entry["share"] = 0.0

        families[family] = {"total": total, "errors": errors}

    return families


def plot_stacked_bars(families: dict[str, any], out_path: Path) -> None:
    """Draw 100% stacked bars with absolute family totals above each bar."""
    leaf_order = MAPPED_COLUMNS
    cmap = plt.get_cmap("tab20")
    color_of = {col: cmap(i % 20) for i, col in enumerate(leaf_order)}

    fig, ax = plt.subplots(figsize=(10, 6.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    x = list(range(len(FAMILY_ORDER)))
    bottoms = [0.0] * len(FAMILY_ORDER)
    legend_handles: list[any] = []
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
    ax.set_title("Error family composition")

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


def build_payload(families: dict[str, any], png_path: Path) -> dict[str, any]:
    family_out: dict[str, any] = {}
    for family in FAMILY_ORDER:
        err_out: dict[str, any] = {}
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
        "definition": "100% stacked bars using binary error presence (0/1).",
        "source_file": str(INPUT_CSV),
        "families": family_out,
        "png": str(png_path.relative_to(Path(INPUT_CSV).parent.parent.parent)).replace("\\", "/"),
    }


def main() -> None:
    df = load_single_file(INPUT_CSV)
    families = aggregate_families(df)

    png_path = OUTPUT_DIR / "error_family_composition_binary.png"
    json_path = OUTPUT_DIR / "error_family_composition_binary.json"

    plot_stacked_bars(families, png_path)
    payload = build_payload(families, png_path)
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"\n📊 Results (binary):")
    for family in FAMILY_ORDER:
        total = families[family]["total"]
        parts = ", ".join(
            f"{ERROR_LABELS[c]}={families[family]['errors'][c]['count']}"
            for c in FAMILY_COLUMNS[family]
        )
        print(f"  {family}: total={total} ({parts})")
    print(f"\n✅ PNG saved to: {png_path}")
    print(f"✅ JSON saved to: {json_path}")


if __name__ == "__main__":
    main()