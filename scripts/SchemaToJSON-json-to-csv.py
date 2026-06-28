import argparse
import csv
import json
from pathlib import Path


DEFAULT_INPUT = Path(__file__).resolve().parent / "chemtables" / "train.json"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "chemtables" / "train.csv"


def json_cell(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def iter_rows(data):
    headers = data["headers"]
    for row in data.get("rows", []):
        if len(row) != len(headers):
            raise ValueError(f"Row length {len(row)} does not match headers {len(headers)}")
        yield {header: json_cell(value) for header, value in zip(headers, row)}


def convert(input_path: Path, output_path: Path) -> int:
    with input_path.open(encoding="utf-8") as f:
        data = json.load(f)

    headers = data["headers"]
    rows = list(iter_rows(data))

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Convert chemtables JSON (headers/rows) to CSV."
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
