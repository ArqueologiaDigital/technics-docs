#!/usr/bin/env python3
"""sound_categories_counts.py -- do sound-categories.md's per-category counts match its lists?

QUESTION ANSWERED
  sound-categories.md lists the string scan's sound names under headings of the
  form `### Category (N)`, with the names on the second line below, comma-separated,
  and gives a total ("~311 names found by the string scan").  This recounts each
  list, reports every heading whose N disagrees, and prints the total.

HOW IT COUNTS
  One name per comma-separated item; an item ending in " 1-8" stands for eight
  numbered names (e.g. "Drum Kit 1-8"), so it counts 8.

RUN
    python3 tools/sound_categories_counts.py               # sound-categories.md
    python3 tools/sound_categories_counts.py path/to/page.md

Result 2026-10-15: no mismatched heading; 311 names in total.
"""

import os
import re
import sys

HEADING = re.compile(r"### (.*) \((\d+)\)$")


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "sound-categories.md")
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    total = bad = 0
    for i, line in enumerate(lines):
        m = HEADING.match(line)
        if not m or i + 2 >= len(lines):
            continue
        names = [x.strip() for x in lines[i + 2].split(",") if x.strip()]
        n = sum(8 if re.search(r" 1-8$", x) else 1 for x in names)
        total += n
        if n != int(m.group(2)):
            bad += 1
            print(f"{path}:{i + 1}: heading says {m.group(2)}, list has {n}")
    print(f"mismatched headings: {bad}; names listed: {total}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
