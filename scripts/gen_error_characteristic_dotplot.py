#!/usr/bin/env python3
"""Top-error characteristic beeswarm plots (option 1).

X = error types (top 8 by finding count)
Y = characteristic value min–max normalized to [0, 1] on eval rows
Color = characteristic

One dot = one finding on a row whose characteristic is in the high bin
(char >= median). Models and methods are pooled.

Datasets: SchemaToJSON, ARQA, DeepJSONEval.

Usage:
  python scripts/gen_error_characteristic_dotplot.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = ROOT / "pipeline" / "outputs"
OUT_DIR = OUTPUTS_DIR / "error_reports" / "dotplots"
ACTIVE_PATH = ROOT / "data" / "active_characteristics.json"

TOP_N_ERRORS = 8

S2J_ROW_RE = re.compile(r"^schema_to_json_(\d+)$")
DJ_ROW_RE = re.compile(r"^deepjson_(\d+)$")

ERROR_LABELS: dict[str, str] = {
    "s2j_cell_value_errors": "Cell Value Error",
    "s2j_array_instead_of_string": "Arrays Instead Of Strings",
    "s2j_hallucinated_type": "Hallucinated Type",
    "s2j_wrong_root_structure": "Wrong Root Structure",
    "s2j_wrong_constituent": "Wrong Constituent",
    "s2j_fields_not_allowed": "Fields Not Allowed",
    "s2j_missing_conditional_fields": "Missing Conditional Fields",
    "arqa_hallucinated_claims": "Hallucinated Claims",
    "arqa_wrong_claim_type": "Wrong Claim Type",
    "arqa_hallucinated_claim_type": "Hallucinated Claim Type",
    "arqa_hallucinated_table_id": "Hallucinated Table Id",
    "arqa_missing_cell_text": "Missing Cell Text",
    "arqa_wrong_coordinates": "Wrong Coordinates",
    "arqa_empty_evidence_span": "Empty Evidence Span",
    "arqa_inaccurate_claims_evidence": "Inaccurate Claims/Evidence",
    "arqa_missing_top_level_fields": "Missing Top-Level Fields",
    "dj_top_level_not_object": "Top Level Not Object",
    "dj_schema_echo": "Schema Echo",
    "dj_property_count": "Property Count Mismatch",
    "dj_enum_check": "Enum Check",
    "dj_required_fields": "Required Fields",
    "dj_property_type": "Property Type",
    "dj_titles_mismatch": "Titles Mismatch",
    "dj_wrong_schema": "Wrong Schema",
    "backslash_issues_count": "Backslash Issues",
    "different_language_count": "Different Language",
    "empty_response_count": "Empty Response",
    "explanatory_text_count": "Explanatory Text",
    "hallucinated_fields_count": "Hallucinated Fields",
    "incorrect_values_count": "Incorrect Values",
    "invalid_json_syntax_count": "Invalid JSON Syntax",
    "longer_shorter_count": "Longer/Shorter",
    "markdown_code_fence_count": "Markdown Code Fence",
    "missing_fields_count": "Missing Fields",
    "placeholder_values_count": "Placeholder Values",
    "python_code_count": "Python Code",
    "repetition_count": "Repetition",
    "trailing_commas_count": "Trailing Commas",
    "truncated_count": "Truncated",
    "unescaped_quotes_count": "Unescaped Quotes",
    "wrong_field_names_count": "Wrong Field Names",
    "wrong_nesting_count": "Wrong Nesting",
    "wrong_order_count": "Wrong Order",
    "wrong_types_count": "Wrong Types",
}

META_COLUMNS = {
    "row_id",
    "row_index",
    "model",
    "method",
    "dataset",
    "run_id",
    "total_errors",
}

EXCLUDE_ERROR_COLUMNS: dict[str, set[str]] = {
    "SchemaToJSON": {"explanatory_text_count"},
}

CHAR_CANDIDATES: dict[str, list[str]] = {
    "SchemaToJSON": [
        "cell_record_count",
        "duplicate_record_count",
        "escaping_count",
        "numeric_string_count",
        "table_cell_ref",
        "long_text",
        "gold_json_length",
    ],
    "ARQA": [
        "table_cell_total_refs_count",
        "max_evidence_items_per_claim",
        "claim_count",
        "gold_json_length",
        "total_object_count",
        "total_key_count",
        "max_value_length",
        "average_value_length",
    ],
    "DeepJSONEval": [
        "property_count",
        "has_enum",
        "gold_json_length",
        "nesting_depth",
        "total_object_count",
        "total_key_count",
        "max_array_length",
        "average_value_length",
    ],
}

ERROR_PREFIX: dict[str, str] = {
    "SchemaToJSON": "s2j_",
    "ARQA": "arqa_",
    "DeepJSONEval": "dj_",
}

DIR_TAG: dict[str, str] = {
    "SchemaToJSON": "schematojson",
    "ARQA": "arqa",
    "DeepJSONEval": "deepjsoneval",
}

DATASET_CSV: dict[str, Path] = {
    "SchemaToJSON": ROOT / "data" / "SchemaToJSON.csv",
    "ARQA": ROOT / "data" / "ARQA.csv",
    "DeepJSONEval": ROOT / "data" / "DeepJSONEval.csv",
}


def normalize_method(method: str) -> str:
    if method in ("nl_to_format", "NL_to_format"):
        return "nl_to_format"
    return method


def error_label(col: str) -> str:
    if col in ERROR_LABELS:
        return ERROR_LABELS[col]
    for prefix in ("s2j_", "arqa_", "dj_"):
        if col.startswith(prefix):
            col = col[len(prefix) :]
            break
    return col.replace("_", " ").title()


def parse_s2j_index(row_id: str) -> int:
    match = S2J_ROW_RE.match(str(row_id))
    if not match:
        raise ValueError(f"Unrecognized SchemaToJSON row_id: {row_id!r}")
    return int(match.group(1))


def parse_dj_index(row_id: str) -> int:
    match = DJ_ROW_RE.match(str(row_id))
    if not match:
        raise ValueError(f"Unrecognized DeepJSONEval row_id: {row_id!r}")
    return int(match.group(1))


def load_run_errors(dataset: str, outputs_dir: Path = OUTPUTS_DIR) -> pd.DataFrame:
    tag = DIR_TAG[dataset]
    frames: list[pd.DataFrame] = []
    for run_dir in sorted(outputs_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        if tag not in run_dir.name.lower():
            continue
        manifest_path = run_dir / "manifest.json"
        csv_path = run_dir / "error_analysis.csv"
        if not manifest_path.exists() or not csv_path.exists():
            continue

        with manifest_path.open(encoding="utf-8") as f:
            manifest = json.load(f)

        manifest_dataset = str(manifest.get("dataset", "")).lower()
        if manifest_dataset and manifest_dataset != dataset.lower():
            continue

        df = pd.read_csv(csv_path)
        model = manifest.get("model", "Unknown")
        if "/" in model:
            model = model.split("/")[-1]
        df["model"] = model
        df["method"] = normalize_method(manifest.get("method", "Unknown"))
        df["dataset"] = dataset
        df["run_id"] = run_dir.name
        frames.append(df)

    if not frames:
        raise FileNotFoundError(
            f"No {dataset} runs with error_analysis.csv under {outputs_dir}"
        )
    return pd.concat(frames, ignore_index=True)


def join_characteristics(dataset: str, errors: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    candidates = list(CHAR_CANDIDATES[dataset])
    if ACTIVE_PATH.exists():
        active = json.loads(ACTIVE_PATH.read_text(encoding="utf-8"))
        active_cols = set(active.get(dataset, {}).get("active_columns", []))
        if active_cols:
            candidates = [c for c in candidates if c in active_cols]

    csv_path = DATASET_CSV[dataset]
    data = pd.read_csv(csv_path)
    available = [c for c in candidates if c in data.columns]
    if not available:
        raise ValueError(f"None of {candidates} found in {csv_path}")

    if dataset == "SchemaToJSON":
        errors = errors.copy()
        errors["row_index"] = errors["row_id"].map(parse_s2j_index)
        chars = data[available].reset_index(names="row_index")
        return errors.merge(chars, on="row_index", how="left"), available

    if dataset == "DeepJSONEval":
        errors = errors.copy()
        errors["row_index"] = errors["row_id"].map(parse_dj_index)
        chars = data[available].reset_index(names="row_index")
        return errors.merge(chars, on="row_index", how="left"), available

    errors = errors.copy()
    errors["row_id"] = errors["row_id"].astype(str)
    data = data.copy()
    data["qa_id"] = data["qa_id"].astype(str)
    chars = data[["qa_id", *available]].rename(columns={"qa_id": "row_id"})
    merged = errors.merge(chars, on="row_id", how="left")
    id_to_idx = {rid: i for i, rid in enumerate(sorted(merged["row_id"].unique()))}
    merged["row_index"] = merged["row_id"].map(id_to_idx)
    return merged, available


def select_error_types(df: pd.DataFrame, dataset: str) -> list[str]:
    prefix = ERROR_PREFIX[dataset]
    joined_chars: set[str] = set()
    for chars in CHAR_CANDIDATES.values():
        joined_chars.update(chars)

    numeric_cols = [
        c
        for c in df.columns
        if c not in META_COLUMNS
        and c not in joined_chars
        and pd.api.types.is_numeric_dtype(df[c])
    ]
    nonzero = [c for c in numeric_cols if df[c].fillna(0).sum() > 0]
    excluded = EXCLUDE_ERROR_COLUMNS.get(dataset, set())
    nonzero = [c for c in nonzero if c not in excluded]
    typed = [c for c in nonzero if c.startswith(prefix)]
    general = [c for c in nonzero if not c.startswith(("s2j_", "arqa_", "dj_"))]
    typed.sort(key=lambda c: float(df[c].fillna(0).sum()), reverse=True)
    general.sort(key=lambda c: float(df[c].fillna(0).sum()), reverse=True)
    return typed + general


def select_top_errors(df: pd.DataFrame, error_types: list[str], n: int = TOP_N_ERRORS) -> list[str]:
    ranked = sorted(error_types, key=lambda c: float(df[c].fillna(0).sum()), reverse=True)
    return ranked[:n]


def _is_numeric_series(s: pd.Series) -> bool:
    if pd.api.types.is_bool_dtype(s) or pd.api.types.is_numeric_dtype(s):
        return True
    try:
        pd.to_numeric(s.dropna(), errors="raise")
        return True
    except (TypeError, ValueError):
        return False


def select_characteristics(df: pd.DataFrame, candidates: list[str]) -> list[str]:
    eval_rows = df.drop_duplicates(subset=["row_index"])
    selected: list[str] = []
    for col in candidates:
        if col not in eval_rows.columns:
            continue
        series = eval_rows[col]
        if not _is_numeric_series(series):
            continue
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.nunique(dropna=True) <= 1:
            continue
        selected.append(col)
    return selected


def characteristic_stats(
    df: pd.DataFrame, characteristics: list[str]
) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    eval_rows = df.drop_duplicates(subset=["row_index"])
    medians: dict[str, float] = {}
    mins: dict[str, float] = {}
    maxs: dict[str, float] = {}
    for c in characteristics:
        series = pd.to_numeric(eval_rows[c], errors="coerce")
        c_min = float(series.min())
        c_max = float(series.max())
        if not np.isfinite(c_min) or not np.isfinite(c_max) or c_max <= c_min:
            continue
        medians[c] = float(series.median())
        mins[c] = c_min
        maxs[c] = c_max
    return medians, mins, maxs


def minmax_norm(value: float, c_min: float, c_max: float) -> float:
    return (value - c_min) / (c_max - c_min)


def build_dot_records(
    df: pd.DataFrame,
    error_types: list[str],
    characteristics: list[str],
    medians: dict[str, float],
    mins: dict[str, float],
    maxs: dict[str, float],
) -> tuple[pd.DataFrame, dict[str, dict[str, int]]]:
    """Option 1 high-bin filter; one dot per (run, row, error, char) observation.

    Finding totals are still tracked in cell_totals for JSON; the plot uses one
    point per observation so beeswarms stay vertical clouds, not horizontal bands.
    """
    records: list[dict[str, Any]] = []
    cell_totals: dict[str, dict[str, int]] = {
        error_label(e): {c: 0 for c in characteristics} for e in error_types
    }

    for _, row in df.iterrows():
        for err_col in error_types:
            count = int(row[err_col]) if pd.notna(row[err_col]) else 0
            if count <= 0:
                continue
            err_name = error_label(err_col)
            for char in characteristics:
                raw = row[char]
                if pd.isna(raw):
                    continue
                value = float(raw)
                if value < medians[char]:
                    continue
                y = minmax_norm(value, mins[char], maxs[char])
                cell_totals[err_name][char] += count
                records.append(
                    {
                        "error_type": err_name,
                        "characteristic": char,
                        "y": y,
                        "findings": count,
                    }
                )

    dots = pd.DataFrame.from_records(
        records, columns=["error_type", "characteristic", "y", "findings"]
    )
    return dots, cell_totals


def _beeswarm_offsets(
    y_values: np.ndarray,
    rng: np.random.Generator,
    bin_height: float = 0.045,
    max_half_width: float = 0.08,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (x_offsets, y_jittered) for a vertical beeswarm cloud."""
    n = len(y_values)
    x_off = np.zeros(n, dtype=float)
    y_jit = y_values.astype(float).copy()
    if n == 0:
        return x_off, y_jit

    # Vertical jitter so discrete Y values form a cloud, not a ruler line.
    y_jit = y_jit + rng.normal(0.0, 0.035, size=n)
    y_jit = np.clip(y_jit, -0.02, 1.02)

    order = np.argsort(y_jit)
    y_sorted = y_jit[order]
    bins = np.round(y_sorted / bin_height).astype(int)
    i = 0
    while i < len(bins):
        j = i + 1
        while j < len(bins) and bins[j] == bins[i]:
            j += 1
        n_bin = j - i
        if n_bin > 1:
            # Keep stacks narrow around the category center (reference style).
            half = min(max_half_width, 0.02 + 0.012 * np.sqrt(n_bin))
            offsets = np.linspace(-half, half, n_bin)
            rng.shuffle(offsets)
            x_off[order[i:j]] = offsets
        i = j
    return x_off, y_jit


def plot_top_error_beeswarm(
    dots: pd.DataFrame,
    error_types: list[str],
    characteristics: list[str],
    dataset: str,
    out_path: Path,
) -> None:
    """Single panel: X=errors, Y=0-1, color=characteristic, mean±SD bars."""
    err_order = [error_label(e) for e in error_types]
    x_pos = {e: float(i) for i, e in enumerate(err_order)}
    cmap = plt.get_cmap("tab10")
    color_of = {c: cmap(i % 10) for i, c in enumerate(characteristics)}
    n_chars = max(len(characteristics), 1)
    # Slight dodge per characteristic so colors form adjacent vertical clouds.
    dodge_span = 0.28
    dodge_of = {
        c: -dodge_span / 2 + dodge_span * (i / max(n_chars - 1, 1))
        for i, c in enumerate(characteristics)
    }

    fig, ax = plt.subplots(figsize=(max(10, 1.5 * len(err_order)), 6.5))
    rng = np.random.default_rng(42)

    if dots.empty:
        ax.text(0.5, 0.5, "No high-bin findings", ha="center", va="center", transform=ax.transAxes)
    else:
        for char in characteristics:
            subset = dots[dots["characteristic"] == char]
            if subset.empty:
                continue
            for err_name, group in subset.groupby("error_type", sort=False):
                if err_name not in x_pos:
                    continue
                ys = group["y"].to_numpy(dtype=float)
                x_off, y_jit = _beeswarm_offsets(ys, rng)
                xs = x_pos[err_name] + dodge_of[char] + x_off
                ax.scatter(
                    xs,
                    y_jit,
                    s=22,
                    facecolors="none",
                    edgecolors=color_of[char],
                    linewidths=0.9,
                    alpha=0.8,
                    label=char,
                    zorder=2,
                )

        for err_name in err_order:
            vals = dots.loc[dots["error_type"] == err_name, "y"].to_numpy(dtype=float)
            if len(vals) == 0:
                continue
            mean = float(np.mean(vals))
            sd = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
            xc = x_pos[err_name]
            ax.vlines(xc, mean - sd, mean + sd, colors="black", linewidth=1.6, zorder=3)
            ax.scatter([xc], [mean], s=60, c="black", zorder=4)

    handles, labels = ax.get_legend_handles_labels()
    seen: dict[str, Any] = {}
    for h, lab in zip(handles, labels):
        if lab not in seen:
            seen[lab] = h
    if seen:
        ax.legend(
            seen.values(),
            seen.keys(),
            title="Characteristic",
            bbox_to_anchor=(1.02, 1),
            loc="upper left",
            frameon=False,
            fontsize=8,
            title_fontsize=9,
        )

    ax.set_xticks(list(x_pos.values()))
    ax.set_xticklabels(err_order, rotation=30, ha="right")
    ax.set_xlim(-0.6, len(err_order) - 0.4)
    ax.set_ylim(-0.05, 1.05)
    ax.set_ylabel("Normalized characteristic value (0–1)")
    ax.set_xlabel("Error type")
    ax.set_title(
        f"{dataset} · Top-error characteristic beeswarm\n"
        "Y = min–max normalized char value; color = characteristic; "
        "1 dot = 1 run×row with error on a high-char row (char ≥ median)"
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(False)
    ax.xaxis.grid(False)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def run_dataset(dataset: str) -> dict[str, Any]:
    errors = load_run_errors(dataset)
    merged, available = join_characteristics(dataset, errors)
    all_errors = select_error_types(merged, dataset)
    characteristics = select_characteristics(merged, available)

    if not all_errors:
        print(f"[{dataset}] skip: no non-zero typed errors")
        return {"dataset": dataset, "skipped": True, "reason": "no errors"}
    if not characteristics:
        print(f"[{dataset}] skip: no varying numeric characteristics")
        return {"dataset": dataset, "skipped": True, "reason": "no characteristics"}

    for c in characteristics:
        merged[c] = pd.to_numeric(merged[c], errors="coerce")

    medians, mins, maxs = characteristic_stats(merged, characteristics)
    characteristics = [c for c in characteristics if c in medians]
    if not characteristics:
        print(f"[{dataset}] skip: no characteristics with min<max")
        return {"dataset": dataset, "skipped": True, "reason": "no scalable characteristics"}

    top_errors = select_top_errors(merged, all_errors, TOP_N_ERRORS)
    dots, cell_totals = build_dot_records(
        merged, top_errors, characteristics, medians, mins, maxs
    )

    slug = DIR_TAG[dataset]
    png_path = OUT_DIR / f"{slug}_error_by_characteristic.png"
    json_path = OUT_DIR / f"{slug}_error_by_characteristic.json"
    plot_top_error_beeswarm(dots, top_errors, characteristics, dataset, png_path)

    ranking = [
        {"error": error_label(e), "total_findings": int(merged[e].fillna(0).sum())}
        for e in sorted(
            all_errors, key=lambda c: float(merged[c].fillna(0).sum()), reverse=True
        )
    ]

    payload: dict[str, Any] = {
        "dataset": dataset,
        "definition": (
            "X = top error types; Y = min-max normalized characteristic value on "
            "eval rows; color = characteristic; 1 dot = 1 run×row with that error "
            "on a high-bin row (char >= median); models/methods pooled"
        ),
        "n_runs": int(merged["run_id"].nunique()),
        "n_rows_eval": int(merged["row_index"].nunique()),
        "n_dots": int(len(dots)),
        "top_errors": [error_label(e) for e in top_errors],
        "error_ranking": ranking,
        "characteristics": characteristics,
        "medians": medians,
        "norm_min": mins,
        "norm_max": maxs,
        "cell_finding_totals": cell_totals,
        "png": str(png_path.relative_to(ROOT)).replace("\\", "/"),
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(
        f"[{dataset}] runs={payload['n_runs']} rows={payload['n_rows_eval']} "
        f"dots={payload['n_dots']} top_errors={payload['top_errors']}"
    )
    print(f"  Wrote {png_path}")
    print(f"  Wrote {json_path}")
    return payload


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for dataset in ("SchemaToJSON", "ARQA", "DeepJSONEval"):
        results.append(run_dataset(dataset))
    summary_path = OUT_DIR / "summary.json"
    summary_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
