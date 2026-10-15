#!/usr/bin/env python3
"""hdae5000_byte_runs.py -- how are the HD-AE5000's undocumented `.byte` bytes distributed?

QUESTION ANSWERED
  hdae5000/tools/measure_debt.py in kn5000-roms-disasm counts 1,713 B of
  undocumented `.byte` operand bytes in the HD-AE5000 sources.  Are they scattered
  single bytes or contiguous blocks?  raw-byte-code-elimination.md says nearly all
  of it is two blocks (a 1,024-byte palette and a 630-byte bitmap) and the other
  59 B are 15 short runs.  This groups consecutive uncommented `.byte` lines into
  runs and prints them, largest first.

HOW IT COUNTS
  The per-line rule is measure_debt.py's: a `.byte` line with no trailing comment
  is undocumented, and each comma-separated operand is one byte.  Consecutive such
  lines form one run.  Read-only.

RUN
    python3 tools/hdae5000_byte_runs.py                  # ../kn5000-roms-disasm
    python3 tools/hdae5000_byte_runs.py --repo /path/to/kn5000-roms-disasm

Result 2026-10-15 (kn5000-roms-disasm 3417969c0): total 1,713 B in 17 runs;
hdae5000_data_tables.s:14779 1,024 B (HDAE5000_Palette_Button01) and :14851
630 B (HDAE5000_Bitmap_Button01); the other 15 runs 59 B.
"""

import argparse
import os
import re

FILES = ["hdae5000/hd-ae5000_v2_06i.s", "hdae5000/hdae5000_data_tables.s",
         "hdae5000/hdae5000_filesystem.s", "hdae5000/hdae5000_hd_driver.s",
         "hdae5000/hdae5000_init_data.s", "hdae5000/hdae5000_ui_display.s",
         "hdae5000/hdae5000_utilities.s", "hdae5000/shared/event_codes.s"]
BYTE = re.compile(r"^\s*(?:\S+\s*:\s*)?\.byte\b(.*)$", re.I)


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--repo", default=os.path.join(here, "..", "kn5000-roms-disasm"))
    args = ap.parse_args()
    runs = []
    for rel in FILES:
        current = None
        with open(os.path.join(args.repo, rel), encoding="latin-1") as f:
            lines = f.read().split("\n")
        for i, line in enumerate(lines, 1):
            m = BYTE.match(line)
            if m and ";" not in m.group(1):
                n = len([p for p in m.group(1).split(",") if p.strip()])
                if current and current[2] == i - 1:
                    current[1] += n
                    current[2] = i
                else:
                    current = [f"{rel}:{i}", n, i]
                    runs.append(current)
    runs.sort(key=lambda r: -r[1])
    print(f"total {sum(r[1] for r in runs):,} B in {len(runs)} runs")
    for where, n, _ in runs:
        print(f"  {where}  {n:,} B")
    if len(runs) > 2:
        print(f"all but the two largest: {sum(r[1] for r in runs[2:]):,} B in {len(runs) - 2} runs")


if __name__ == "__main__":
    main()
