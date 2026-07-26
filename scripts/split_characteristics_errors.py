#!/usr/bin/env python3
"""
Split merged CSV into separate files per characteristic family and error family.
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path

# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------
INPUT_CSV = Path(
    r"C:\Users\Justin\SIP-git\schema-error-analysis\pipeline\outputs\full_merged_characteristics_and_errors.csv"
)
OUTPUT_DIR = INPUT_CSV.parent / "split_data"

IDENTIFIER_COLS = ["row_id", "dataset", "model", "method"]

# ---------- CHARACTERISTIC FAMILIES ----------
CHARACTERISTIC_FAMILIES: dict[str, list[str]] = {
    "Complexity": [
        "gold_json_length", "nesting_depth", "total_object_count",
        "max_array_nesting_depth", "total_array_count", "max_array_length",
        "total_key_count", "unique_key_count", "max_key_length"
    ],
    "ValueTypes": [
        "long_text_value_count", "numeric_value_count",
        "alphanumeric_value_count", "max_value_length", "average_value_length"
    ],
    "Structural": [
        "char_has_table_cells", "char_has_text_spans",
        "table_cell_total_refs_count", "claim_count",
        "max_evidence_items_per_claim"
    ],
    "TableFeatures": [
        "escaping_count", "numeric_string_count", "cell_record_count",
        "duplicate_record_count", "table_cell_ref", "long_text"
    ],
    "SchemaFeatures": [
        "property_count", "has_enum", "array_of_objects",
        "array_of_primitives", "category"
    ]
}

# ---------- ERROR FAMILIES (exactly as you provided) ----------
ERROR_FAMILIES: dict[str, list[str]] = {
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
        "wrong_order_count",
    ],
    "Content": [
        "incorrect_values_count",
        "placeholder_values_count",
        "longer_shorter_count",
        "different_language_count",
    ],
}

# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV)
    print(f"✅ Loaded {len(df)} rows from {INPUT_CSV.name}")

    missing_id = [c for c in IDENTIFIER_COLS if c not in df.columns]
    if missing_id:
        raise KeyError(f"Missing identifier columns: {missing_id}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- Characteristics ---
    print("\n📊 Characteristic families:")
    for family, cols in CHARACTERISTIC_FAMILIES.items():
        existing = [c for c in cols if c in df.columns]
        if not existing:
            print(f"  ⚠️  {family}: no columns found")
            continue
        subset_cols = IDENTIFIER_COLS + existing
        subset_df = df[subset_cols].copy()
        out_path = OUTPUT_DIR / f"characteristics_{family}.csv"
        subset_df.to_csv(out_path, index=False)
        print(f"  ✅ {family}: {len(existing)} columns → {out_path.name}")

    all_char_cols = [c for cols in CHARACTERISTIC_FAMILIES.values() for c in cols if c in df.columns]
    if all_char_cols:
        subset_cols = IDENTIFIER_COLS + all_char_cols
        subset_df = df[subset_cols].copy()
        out_path = OUTPUT_DIR / "characteristics_all.csv"
        subset_df.to_csv(out_path, index=False)
        print(f"  ✅ All characteristics ({len(all_char_cols)} columns) → {out_path.name}")

    # --- Errors ---
    print("\n❌ Error families:")
    for family, cols in ERROR_FAMILIES.items():
        existing = [c for c in cols if c in df.columns]
        if not existing:
            print(f"  ⚠️  {family}: no columns found")
            continue
        subset_cols = IDENTIFIER_COLS + existing
        subset_df = df[subset_cols].copy()
        out_path = OUTPUT_DIR / f"errors_{family}.csv"
        subset_df.to_csv(out_path, index=False)
        print(f"  ✅ {family}: {len(existing)} columns → {out_path.name}")

    all_err_cols = [c for cols in ERROR_FAMILIES.values() for c in cols if c in df.columns]
    if all_err_cols:
        subset_cols = IDENTIFIER_COLS + all_err_cols
        subset_df = df[subset_cols].copy()
        out_path = OUTPUT_DIR / "errors_all.csv"
        subset_df.to_csv(out_path, index=False)
        print(f"  ✅ All errors ({len(all_err_cols)} columns) → {out_path.name}")

    print(f"\n✅ All files saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()  