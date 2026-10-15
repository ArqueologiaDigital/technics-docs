#!/usr/bin/env python3
"""naka_record_class_tables.py -- which class table do the firmware's widget records use?

QUESTION ANSWERED
  ui-widget-types.md says that 2,894 of the 3,365 v10 widget records use a class
  from the root Class table (object-table index 0x160) and the rest use one of the
  other registered Class tables.  This counts the records per class table, so the
  figure is a measurement.

HOW IT COUNTS
  It uses kn5000-roms-disasm's own map of the registered object tables
  (scripts/analysis/nakarest_objtab_map.py): every address that a registered
  Viewable table points at inside the ROM is a widget record.  A record's first
  32-bit word is its class id, 0x016TKKKK, and T selects the class table
  (index 0x160 + T).  Read-only; it needs the disassembly checkout, including the
  ROM images that nakarest_objtab_map.py reads.

RUN
    python3 tools/naka_record_class_tables.py                    # v10, ../kn5000-roms-disasm
    python3 tools/naka_record_class_tables.py --version v9 --repo /path/to/kn5000-roms-disasm

Result 2026-10-15 (kn5000-roms-disasm 3417969c0, v10): 3,365 records; 0x160 2,894,
0x161 99, 0x162 35, 0x163 16, 0x164 66, 0x165 119, 0x167 64, 0x168 72.
"""

import argparse
import collections
import os
import sys


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--repo", default=os.path.join(here, "..", "kn5000-roms-disasm"))
    ap.add_argument("--version", default="v10")
    args = ap.parse_args()
    repo = os.path.abspath(args.repo)
    os.chdir(repo)  # the map resolves its sources and ROM images relative to the repo
    sys.path.insert(0, os.path.join(repo, "scripts", "analysis"))
    import nakarest_objtab_map as naka

    m = naka.Map(args.version)
    records = sorted({addr for addr, uses in m.addr.items()
                      for kind, _, _ in uses if kind == "record" and m.inrom(addr)})
    per_table = collections.Counter((m.u32(addr) >> 16) & 0xFFF for addr in records)
    print(f"{args.version}: {len(records):,} widget records")
    for table, n in sorted(per_table.items()):
        print(f"  class table 0x{table:03X}: {n:,}")


if __name__ == "__main__":
    main()
