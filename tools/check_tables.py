#!/usr/bin/env python3
"""check_tables.py -- are the Markdown tables space-padded with aligned columns?

QUESTION ANSWERED
  The owner reads these pages as raw Markdown, so every table is written with
  space-padded, aligned columns (`| cell   |`), never the compact `|a|b|` form,
  and has to be re-padded whenever a cell changes width.  This finds tables
  whose rows do not line up: a row is aligned when its `|` characters sit in the
  same columns as those of the separator row (`|----|:---:|`).

  By default only tables that contain a line changed since git HEAD are checked,
  which is what an edit should be held to; --all checks every table, including
  old ones that were never padded.  Escaped pipes (\\|), pipes inside Liquid
  {{ }} / {% %} and fenced code blocks are ignored; East Asian wide characters
  count as two columns.  Exits non-zero if any checked table is misaligned.

RUN
  python3 tools/check_tables.py page.md other.md     # tables touched since HEAD
  python3 tools/check_tables.py --all page.md        # every table on the page
"""

import argparse
import re
import subprocess
import sys
import unicodedata

SEPARATOR = re.compile(r"^\|[\s:|-]+\|?\s*$")
LIQUID = re.compile(r"\{\{.*?\}\}|\{%.*?%\}")


def pipe_columns(line):
    """Display columns of the unescaped `|` characters in a table row."""
    line = LIQUID.sub(lambda m: "x" * len(m.group(0)), line).replace("\\|", "xx")
    cols, width = [], 0
    for c in line.rstrip():
        if c == "|":
            cols.append(width)
        width += 2 if unicodedata.east_asian_width(c) in "WF" else 1
    return cols


def changed_lines(path):
    """Line numbers (1-based) of the working-tree file that differ from HEAD."""
    diff = subprocess.run(["git", "diff", "-U0", "HEAD", "--", path],
                          capture_output=True, text=True).stdout
    lines = set()
    for m in re.finditer(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@", diff, re.M):
        start, count = int(m.group(1)), int(m.group(2) or 1)
        lines.update(range(start, start + count))
    return lines


def tables(text):
    """Yield (first line number, rows) for every table outside a code fence."""
    lines = text.split("\n")
    i, fence = 0, False
    while i < len(lines):
        if lines[i].lstrip().startswith(("```", "~~~")):
            fence = not fence
        if not fence and lines[i].startswith("|"):
            j = i
            while j < len(lines) and lines[j].startswith("|"):
                j += 1
            if j - i >= 2 and SEPARATOR.match(lines[i + 1]):
                yield i + 1, lines[i:j]
            i = j
            continue
        i += 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--all", action="store_true", help="check every table, not only touched ones")
    args = ap.parse_args()

    checked = bad = 0
    for path in args.files:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        touched = None if args.all else changed_lines(path)
        for first, rows in tables(text):
            if touched is not None and not touched & set(range(first, first + len(rows))):
                continue
            checked += 1
            ref = pipe_columns(rows[1])
            wrong = [first + k for k, row in enumerate(rows) if pipe_columns(row) != ref]
            if wrong:
                bad += 1
                more = "..." if len(wrong) > 8 else ""
                print(f"{path}:{first}: misaligned rows {wrong[:8]}{more}")
    print(f"tables checked: {checked}; misaligned: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
