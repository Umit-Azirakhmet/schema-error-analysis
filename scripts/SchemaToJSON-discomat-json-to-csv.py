import argparse
import csv
import json
from pathlib import Path


DEFAULT_INPUT = (
    Path(__file__).resolve().parent.parent / "data" / "SchemaToJSON_discomatTrain.json"
)
DEFAULT_OUTPUT = (
    Path(__file__).resolve().parent.parent / "data" / "SchemaToJSON_discomatTrain.csv"
)

FIELDNAMES = [
    "paper_id",
    "table_id",
    "table_code",
    "sup_text",
    "target_cells",
    "gold_json_records",
]


def json_cell(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def load_records(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "records" in data:
        return data["records"]
    raise ValueError("Expected a JSON array of records or an object with a 'records' key")


def iter_rows(data):
    for record in load_records(data):
        yield {
            "paper_id": record.get("paper_id", ""),
            "table_id": record.get("table_id", ""),
            "table_code": record.get("table_code", ""),
            "sup_text": record.get("sup_text", ""),
            "target_cells": json_cell(record.get("target_cells")),
            "gold_json_records": json_cell(record.get("gold_json_records")),
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
    parser = argparse.ArgumentParser(
        description="Convert SchemaToJSON discomat JSON to CSV."
    )
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
