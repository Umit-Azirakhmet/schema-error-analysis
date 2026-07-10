#!/usr/bin/env python3
"""Generate the zero-shot model-vs-gold comparison canvas.

Stripping policy (model side only)
----------------------------------
Gold ``gold_json_raw`` is never modified.

For ``raw_response``, we keep only the JSON fragment and drop surrounding
natural language:

- **Leading NL** — everything before the first ``{`` is discarded (e.g.
  ARQA responses that start with ``Answer:\\n...`` prose).
- **Trailing NL** — everything after the first *balanced* top-level ``{…}``
  object is discarded (chain-of-thought, duplicate answers, etc.).

Two extraction cases once we locate the first ``{``:

1. **Balanced JSON** — walk from the first ``{``, track brace depth
   (string-aware), and return everything through the matching closing
   ``}``. Anything after that closing brace is discarded.

2. **Unbalanced / truncated JSON** — if brace depth never returns to 0
   (model hit token limit mid-object), cut at the first newline after the
   opening ``{``. Rationale: these responses are usually one compact JSON
   line followed by blank line + prose. No characters *inside* the first
   line are removed.

3. **No brace** — if the response contains no ``{`` at all, the entire
   response is treated as NL and discarded (empty model JSON).

Run with ``--verify`` to print per-row diagnostics (suffix preview, method
used) without writing the canvas. Run with ``--write-canvas`` (default) to
regenerate the .canvas.tsx file.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CANVAS_OUT = Path(
    r"C:\Users\pierc\.cursor\projects"
    r"\c-Users-pierc-OneDrive-Documents-GitHub-schema-error-analysis"
    r"\canvases\schematojson-zero-shot-comparison.canvas.tsx"
)

SOURCES = [
    {
        "run_id": "20260708_171903_arqa_qwen3-8b_zero_shot",
        "label": "ARQA · Qwen3-8B zero-shot",
        "path": REPO
        / "pipeline/outputs/20260708_171903_arqa_qwen3-8b_zero_shot/responses.jsonl",
    },
    {
        "run_id": "20260708_182500_schematojson_qwen3-8b_zero_shot",
        "label": "SchemaToJSON · Qwen3-8B zero-shot",
        "path": REPO
        / "pipeline/outputs/20260708_182500_schematojson_qwen3-8b_zero_shot/responses.jsonl",
    },
]


@dataclass
class StripResult:
    json_text: str
    method: str  # "balanced_braces" | "first_newline" | "no_brace" | "empty"
    raw_len: int
    stripped_len: int
    suffix: str  # trailing text removed (empty if nothing)
    leading_prefix: str  # text before extracted JSON (empty if JSON starts at 0)


def _balanced_brace_slice(text: str, start: int) -> tuple[str, str] | None:
    """Return (json_text, trailing_suffix) if braces balance from start."""
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1].strip(), text[i + 1 :]
    return None


def _extract_from_fenced(text: str) -> tuple[str, str, str, str] | None:
    """Return (json_text, method, leading, suffix) from markdown fences."""
    blocks = list(
        re.finditer(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    )
    for match in reversed(blocks):
        candidate = match.group(1).strip()
        if not candidate.startswith("{"):
            continue
        balanced = _balanced_brace_slice(candidate, 0)
        if balanced:
            json_text, inner_suffix = balanced
            leading = text[: match.start()]
            suffix = text[match.end() :]
            if inner_suffix.strip():
                suffix = inner_suffix + suffix
            return json_text, "fenced_codeblock", leading, suffix
    return None


def strip_to_json(text: str) -> StripResult:
    """Extract JSON only; return diagnostics about removed NL."""
    if not text:
        return StripResult("", "empty", 0, 0, "", "")

    fenced = _extract_from_fenced(text)
    if fenced:
        json_text, method, leading_prefix, suffix = fenced
        return StripResult(
            json_text,
            method,
            len(text),
            len(json_text),
            suffix,
            leading_prefix,
        )

    start = text.find("{")
    if start < 0:
        # Pure NL — model never emitted JSON.
        return StripResult(
            "",
            "no_json_found",
            len(text),
            0,
            "",
            text,
        )

    leading_prefix = text[:start]
    balanced = _balanced_brace_slice(text, start)
    if balanced:
        json_text, suffix = balanced
        return StripResult(
            json_text,
            "balanced_braces",
            len(text),
            len(json_text),
            suffix,
            leading_prefix,
        )

    nl = text.find("\n", start)
    if nl != -1:
        json_text = text[start:nl].strip()
        suffix = text[nl:]
        return StripResult(
            json_text,
            "first_newline",
            len(text),
            len(json_text),
            suffix,
            leading_prefix,
        )

    json_text = text[start:].strip()
    return StripResult(
        json_text,
        "truncated_no_newline",
        len(text),
        len(json_text),
        "",
        leading_prefix,
    )


def caption_from_prompt(prompt: str) -> str:
  if "Caption:" in prompt:
    return prompt.split("Caption:")[1].split("\n")[0].strip()
  if "Question:" in prompt:
    return prompt.split("Question:")[1].split("\n")[0].strip()
  return prompt.strip().split("\n")[0][:120]


def js_literal(s: str) -> str:
  return json.dumps(s, ensure_ascii=False)


def load_datasets() -> list[dict]:
  datasets: list[dict] = []
  for src in SOURCES:
    rows: list[dict] = []
    for line in src["path"].read_text(encoding="utf-8").splitlines():
      if not line.strip():
        continue
      record = json.loads(line)
      raw = record.get("raw_response", "")
      strip = strip_to_json(raw)
      rows.append(
        {
          "rowId": record["row_id"],
          "rowIndex": record["row_index"],
          "dataset": record.get("dataset", ""),
          "caption": caption_from_prompt(record.get("prompt", "")),
          "outputTokens": record["output_tokens"],
          "inputTokens": record["input_tokens"],
          "strippedChars": strip.stripped_len,
          "rawChars": strip.raw_len,
          "stripMethod": strip.method,
          "stripSuffix": strip.suffix,
          "leadingPrefix": strip.leading_prefix,
          "modelJson": strip.json_text,
          "goldJson": record.get("gold_json_raw", ""),
        }
      )
    datasets.append(
      {
        "runId": src["run_id"],
        "label": src["label"],
        "rows": rows,
      }
    )
  return datasets


def verify(datasets: list[dict]) -> None:
  print("=" * 72)
  print("NL strip verification")
  print("=" * 72)
  for ds in datasets:
    print(f"\n## {ds['label']} ({ds['runId']})")
    for row in ds["rows"]:
      suffix = row["stripSuffix"]
      leading = row["leadingPrefix"]
      trailing_removed = len(suffix)
      leading_removed = len(leading)
      total_removed = trailing_removed + leading_removed
      print(f"\n  {row['rowId']}  method={row['stripMethod']}")
      print(
        f"    raw={row['rawChars']}  json={row['strippedChars']}  "
        f"removed={total_removed} (lead={leading_removed}, trail={trailing_removed})"
      )
      if row["stripMethod"] == "no_json_found":
        print("    entire response was NL (no JSON object found)")
      elif leading_removed > 0:
        lead_preview = leading[:120].replace("\n", "\\n")
        if len(leading) > 120:
          lead_preview += "…"
        print(f"    leading prefix dropped: {lead_preview!r}")
      if trailing_removed == 0:
        if leading_removed == 0:
          print("    (nothing removed)")
      else:
        preview = suffix[:200].replace("\n", "\\n")
        if len(suffix) > 200:
          preview += "…"
        print(f"    trailing suffix preview: {preview!r}")
        first_non_ws = suffix.lstrip()
        if first_non_ws.startswith(("{", "[", '"')):
          print("    WARNING: suffix starts like JSON — review this row")


def build_canvas_tsx(datasets: list[dict]) -> str:
  parts: list[str] = []
  for ds in datasets:
    row_parts: list[str] = []
    for row in ds["rows"]:
      row_parts.append(
        "      {\n"
        f"        rowId: {js_literal(row['rowId'])},\n"
        f"        rowIndex: {row['rowIndex']},\n"
        f"        dataset: {js_literal(row['dataset'])},\n"
        f"        caption: {js_literal(row['caption'])},\n"
        f"        outputTokens: {row['outputTokens']},\n"
        f"        inputTokens: {row['inputTokens']},\n"
        f"        strippedChars: {row['strippedChars']},\n"
        f"        rawChars: {row['rawChars']},\n"
        f"        modelJson: {js_literal(row['modelJson'])},\n"
        f"        goldJson: {js_literal(row['goldJson'])},\n"
        "      },"
      )
    parts.append(
      "  {\n"
      f"    runId: {js_literal(ds['runId'])},\n"
      f"    label: {js_literal(ds['label'])},\n"
      f"    rows: [\n"
      + "\n".join(row_parts)
      + "\n    ],\n"
      "  },"
    )

  data_literal = "[\n" + "\n".join(parts) + "\n]"

  return CANVAS_TEMPLATE.replace("__DATA__", data_literal)


CANVAS_TEMPLATE = r'''import {
  Callout,
  Card,
  CardBody,
  CardHeader,
  Code,
  CollapsibleSection,
  Grid,
  H1,
  H2,
  IconButton,
  Pill,
  Stack,
  Table,
  Text,
  useCanvasState,
  useHostTheme,
} from "cursor/canvas";

const MIDDOT = "\u00b7";
const ELLIPSIS = "\u2026";

type RowComparison = {
  rowId: string;
  rowIndex: number;
  dataset: string;
  caption: string;
  outputTokens: number;
  inputTokens: number;
  strippedChars: number;
  rawChars: number;
  modelJson: string;
  goldJson: string;
};

type DatasetRun = {
  runId: string;
  label: string;
  rows: RowComparison[];
};

const DATASETS: DatasetRun[] = __DATA__;

function CopyButton({ id, text }: { id: string; text: string }) {
  const [copiedId, setCopiedId] = useCanvasState<string | null>(
    "copiedField",
    null,
  );
  const copied = copiedId === id;

  const handleCopy = () => {
    try {
      const nav = (globalThis as { navigator?: Navigator }).navigator;
      if (nav?.clipboard?.writeText) {
        nav.clipboard.writeText(text);
      }
    } catch {
      // Clipboard access can be blocked; ignore and still show feedback.
    }
    setCopiedId(id);
    setTimeout(() => {
      setCopiedId((prev) => (prev === id ? null : prev));
    }, 1500);
  };

  return (
    <IconButton
      title={copied ? "Copied" : "Copy JSON"}
      size="sm"
      onClick={handleCopy}
    >
      {copied ? (
        <svg width={12} height={12} viewBox="0 0 12 12" fill="none">
          <path
            d="M2.5 6.5l2.5 2.5 4.5-5"
            stroke="currentColor"
            strokeWidth={1.4}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ) : (
        <svg width={12} height={12} viewBox="0 0 12 12" fill="none">
          <rect
            x={3.5}
            y={3.5}
            width={6}
            height={6}
            rx={1}
            stroke="currentColor"
            strokeWidth={1.2}
          />
          <path
            d="M2 8V2.5A0.5 0.5 0 0 1 2.5 2H8"
            stroke="currentColor"
            strokeWidth={1.2}
            strokeLinecap="round"
          />
        </svg>
      )}
    </IconButton>
  );
}

export default function PipelineZeroShotComparison() {
  const theme = useHostTheme();
  const t = theme.tokens;

  const preStyle = {
    margin: 0,
    whiteSpace: "pre-wrap" as const,
    wordBreak: "break-word" as const,
    fontFamily: "ui-monospace, monospace",
    fontSize: 11,
    lineHeight: 1.5,
    color: t.text.primary,
    maxHeight: 420,
    overflow: "auto" as const,
  };

  const totalRows = DATASETS.reduce((n, ds) => n + ds.rows.length, 0);

  return (
    <Stack gap={32} style={{ padding: 24, maxWidth: 1280 }}>
      <Stack gap={8}>
        <H1>Model JSON vs gold (zero-shot)</H1>
        <Text tone="secondary" size="small">
          {DATASETS.length} runs {MIDDOT} {totalRows} rows {MIDDOT} responses.jsonl
        </Text>
      </Stack>

      <Callout tone="info">
        <Text size="small">
          Left panels show <Code>raw_response</Code> with all natural-language
          stripped {MIDDOT} only a JSON object is kept when one exists. Rows
          with no JSON show an empty model panel. Right panels show{" "}
          <Code>gold_json_raw</Code> unchanged. Use the clipboard icon to copy
          either field.
        </Text>
      </Callout>

      {DATASETS.map((ds) => {
        const overviewRows = ds.rows.map((row) => [
          <Text size="small" weight="semibold">
            {row.rowId}
          </Text>,
          <Text size="small">
            {row.caption.length > 70
              ? row.caption.slice(0, 70) + ELLIPSIS
              : row.caption}
          </Text>,
          <Text size="small">{row.inputTokens}</Text>,
          <Text size="small">{row.outputTokens}</Text>,
          <Text size="small">
            {row.rawChars} {MIDDOT} {row.strippedChars}
          </Text>,
        ]);

        return (
          <Stack gap={16}>
            <Stack gap={4}>
              <H2>{ds.label}</H2>
              <Text tone="tertiary" size="small">
                {ds.runId} {MIDDOT} {ds.rows.length} rows
              </Text>
            </Stack>

            <Table
              headers={[
                "Row ID",
                "Caption / question",
                "Input tok",
                "Output tok",
                "Chars raw / json",
              ]}
              rows={overviewRows}
              columnAlign={["left", "left", "right", "right", "right"]}
              framed
              striped
            />

            <Stack gap={12}>
              {ds.rows.map((row) => (
                <CollapsibleSection
                  title={row.rowId}
                  defaultOpen={row.rowIndex === 0}
                  trailing={<Pill size="sm">{row.outputTokens} out tok</Pill>}
                >
                  <Stack gap={16} style={{ paddingTop: 8 }}>
                    <Text size="small" tone="secondary">
                      {row.caption}
                    </Text>

                    <Grid columns={2} gap={16}>
                      <Card>
                        <CardHeader
                          trailing={
                            <CopyButton
                              id={ds.runId + "-" + row.rowId + "-model"}
                              text={row.modelJson}
                            />
                          }
                        >
                          Model JSON (NL stripped)
                        </CardHeader>
                        <CardBody>
                          <pre style={preStyle}>
                            {row.modelJson ||
                              "(no JSON in raw_response)"}
                          </pre>
                        </CardBody>
                      </Card>

                      <Card>
                        <CardHeader
                          trailing={
                            <CopyButton
                              id={ds.runId + "-" + row.rowId + "-gold"}
                              text={row.goldJson}
                            />
                          }
                        >
                          Gold (gold_json_raw)
                        </CardHeader>
                        <CardBody>
                          <pre style={preStyle}>{row.goldJson}</pre>
                        </CardBody>
                      </Card>
                    </Grid>
                  </Stack>
                </CollapsibleSection>
              ))}
            </Stack>
          </Stack>
        );
      })}
    </Stack>
  );
}
'''


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument(
    "--verify",
    action="store_true",
    help="Print per-row strip diagnostics (suffix preview) and exit",
  )
  parser.add_argument(
    "--write-canvas",
    action="store_true",
    default=True,
    help="Write the .canvas.tsx file (default)",
  )
  parser.add_argument(
    "--no-write-canvas",
    action="store_true",
    help="Skip writing the canvas (use with --verify only)",
  )
  args = parser.parse_args()

  datasets = load_datasets()

  if args.verify:
    verify(datasets)

  if not args.no_write_canvas:
    tsx = build_canvas_tsx(datasets)
    CANVAS_OUT.write_text(tsx, encoding="utf-8")
    print(f"\nWrote {CANVAS_OUT} ({len(tsx)} chars)")

  return 0


if __name__ == "__main__":
  sys.exit(main()