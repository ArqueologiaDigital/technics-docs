#!/usr/bin/env python3
"""Count numeric and all branch operands per source tree, at a git revision of
the disassembly repository -- the table under "numeric cross-references" on
/rom-reconstruction/.

QUESTION THIS ANSWERS
  How many `jr`/`jrl`/`calr`/`call`/`jp`/`djnz` statements in each tree still
  have a NUMBER as their operand, out of how many branch statements in all?

  The numeric pattern is the one-liner in the disassembly repository's
  scripts/converters/README-symbolize-branches.md, applied per line; "all" is
  the same pattern without the operand constraint.  It reads COMMITTED BLOBS
  (git ls-tree + git show), never the working tree, so a revision's figures do
  not depend on anybody's uncommitted edits.  At the commit before the
  symboliser landed (b0bfd371^) it reproduces the "before" figures in
  symbolize_numeric_branches.py's own docstring exactly (13,344 / 74,282 for
  v10 ... 2,479 / 10,241 for prom_c) -- that is the check that the pattern is
  the same one.

USAGE
  python3 tools/branch_operand_counts.py [REV] [--repo DIR]
  REV defaults to HEAD; DIR to ../kn5000-roms-disasm relative to this repository.
"""
import argparse
import os
import re
import subprocess

TREES = ["v10/maincpu", "v9/maincpu", "v7/maincpu", "v142/subcpu", "hdae5000",
         "table_data", "wsa1/prom_a", "wsa1/prom_b", "wsa1/prom_c"]
NUM = re.compile(rb'^\s*(\S+:)?\s*(jr|jrl|calr|call|jp|djnz)\s+([a-z]+,\s*)?'
                 rb'(-?[0-9]+|0x[0-9a-fA-F]+)\s*(;.*)?$', re.M)
ALL = re.compile(rb'^\s*(\S+:)?\s*(jr|jrl|calr|call|jp|djnz)\s+\S', re.M)


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument("rev", nargs="?", default="HEAD")
    ap.add_argument("--repo", default=os.path.join(here, os.pardir, "kn5000-roms-disasm"))
    a = ap.parse_args()
    print("%-14s %8s %8s   (at %s)" % ("tree", "numeric", "all", a.rev))
    for t in TREES:
        files = subprocess.run(["git", "-C", a.repo, "ls-tree", "-r", "--name-only", a.rev, "--", t],
                               capture_output=True, check=True, text=True).stdout.split("\n")
        n = m = 0
        for f in files:
            if not f.endswith(".s"):
                continue
            b = subprocess.run(["git", "-C", a.repo, "show", "%s:%s" % (a.rev, f)],
                               capture_output=True, check=True).stdout
            n += len(NUM.findall(b))
            m += len(ALL.findall(b))
        print("%-14s %8d %8d" % (t, n, m))


if __name__ == "__main__":
    main()
