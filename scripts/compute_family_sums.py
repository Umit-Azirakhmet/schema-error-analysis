#!/usr/bin/env python3
"""
Compute the sum of each characteristic family and error family for every row.

Usage:
  python scripts/compute_family_sums.py
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
OUTPUT_CSV = INPUT_CSV.parent / "family_sums.csv"

# ---------- CHARACTERISTIC FAMILIES ----------
CHAR_FAMILIES = {
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

# ---------- ERROR FAMILIES ----------
ERROR_FAMILIES = {
    "Completion": [
        "truncated_count", "repetition_count", "empty_response_count"
    ],
    "Syntax": [
        "invalid_json_syntax_count", "backslash_issues_count"
    ],
    "Contamination": [
        "markdown_code_fence_count", "explanatory_text_count"
    ],
    "Schema_Error": [
        "hallucinated_fields_count", "missing_fields_count",
        "wrong_nesting_count", "wrong_types_count", "wrong_order_count"
    ],
    "Content": [
        "incorrect_values_count", "placeholder_values_count",
        "longer_shorter_count", "different_language_count"
    ]
}

# Identifier columns to keep
ID_COLS = ["row_id", "dataset", "model", "method"]

# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)
    print(f"✅ Loaded {len(df)} rows from {INPUT_CSV.name}")

    # Ensure all columns are numeric (coerce errors to NaN, then fill with 0)
    all_family_cols = []
    for fam, cols in {**CHAR_FAMILIES, **ERROR_FAMILIES}.items():
        all_family_cols.extend(cols)

    for col in all_family_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Start with the identifier columns
    result_df = df[ID_COLS].copy()

    # Compute sums for each characteristic family
    print("\n📊 Computing characteristic family sums...")
    for fam, cols in CHAR_FAMILIES.items():
        existing = [c for c in cols if c in df.columns]
        if existing:
            result_df[f"{fam}_sum"] = df[existing].sum(axis=1)
            print(f"  ✅ {fam}: {len(existing)} columns summed")
        else:
            result_df[f"{fam}_sum"] = 0
            print(f"  ⚠️  {fam}: no columns found → sum set to 0")

    # Compute sums for each error family
    print("\n❌ Computing error family sums...")
    for fam, cols in ERROR_FAMILIES.items():
        existing = [c for c in cols if c in df.columns]
        if existing:
            result_df[f"{fam}_sum"] = df[existing].sum(axis=1)
            print(f"  ✅ {fam}: {len(existing)} columns summed")
        else:
            result_df[f"{fam}_sum"] = 0
            print(f"  ⚠️  {fam}: no columns found → sum set to 0")

    # Save to CSV
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(OUTPUT_CSV, index=False)
    print(f"\n✅ Family sums saved to: {OUTPUT_CSV}")
    print(f"   Shape: {result_df.shape}")

    # Show a preview of the first few rows
    print("\n🔍 Preview (first 3 rows):")
    print(result_df.head(3).to_string())

if __name__ == "__main__":
    main()