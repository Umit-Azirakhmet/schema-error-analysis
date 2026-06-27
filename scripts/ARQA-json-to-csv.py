import argparse
import csv
import json
from pathlib import Path


DEFAULT_INPUT = Path(__file__).resolve().parent / "ARQA_validated.json"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "ARQA_validated.csv"

FIELDNAMES = [
    "year",
    "pack_table_id",
    "paragraph_ids",
    "qa_id",
    "q_type",
    "question",
    "answer_text",
    "value",
    "value_canonical",
    "unit",
    "answer_value",
    "arith_type",
    "gold_answer",
    "program",
    "evidence",
    "table_id",
    "verified",
]


def json_cell(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def iter_rows(data):
    for pack in data.get("packs", []):
        year = pack.get("year", "")
        pack_table_id = pack.get("table_id", "")
        paragraph_ids = json.dumps(pack.get("paragraph_ids", []), ensure_ascii=False)

        for qa in pack.get("qas", []):
            yield {
                "year": year,
                "pack_table_id": pack_table_id,
                "paragraph_ids": paragraph_ids,
                "qa_id": qa.get("qa_id", ""),
                "q_type": qa.get("q_type", ""),
                "question": qa.get("question", ""),
                "answer_text": qa.get("answer_text", ""),
                "value": qa.get("value", ""),
                "value_canonical": qa.get("value_canonical", ""),
                "unit": qa.get("unit", ""),
                "answer_value": qa.get("answer_value", ""),
                "arith_type": qa.get("arith_type", ""),
                "gold_answer": json_cell(qa.get("gold_answer")),
                "program": json_cell(qa.get("program")),
                "evidence": json_cell(qa.get("evidence")),
                "table_id": qa.get("table_id", ""),
                "verified": qa.get("verified", ""),
            }


def convert(input_path: Path, output_path: Path) -> int:
    with input_path.open(encoding="utf-8") as f:
        data = json.load(f)

    rows = list(iter_rows(data))

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def main():
    parser = argparse.ArgumentParser(description="Convert ARQA_validated.json to CSV.")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input JSON file (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV file (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    row_count = convert(args.input, args.output)
    print(f"Wrote {row_count} rows to {args.output}")


if __name__ == "__main__":
    main()
