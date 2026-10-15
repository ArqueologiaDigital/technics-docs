#!/usr/bin/env python3
"""incbin_bytes.py -- how many bytes does each ROM tree still take in through `.incbin`?

QUESTION ANSWERED
  rom-reconstruction.md ("Where the source still holds raw ROM slices") gives, per
  ROM tree of kn5000-roms-disasm, the total bytes that the LLVM build pulls in as
  opaque binary through live `.incbin` directives.  This prints those totals, so
  the table quotes a measurement instead of a remembered number.

HOW IT COUNTS
  Every tracked `.s` file of a tree (`git ls-files <tree>/*.s`) is scanned for
  uncommented `.incbin "file"[, offset[, length]]` lines.  The emitted length is
  `length` if given, else the file's size minus `offset`.  The file is looked up
  next to the including source, then under the tree, then at the repository root,
  the order the assembler's include path gives.  Offsets and lengths are integer
  expressions (`0x7F2D8`, `0x400*4`).

  Many included files are build products (`includes/generated/*.bin`), so run it
  in a tree where `make` has been run; a file that does not exist is counted as
  "missing" and adds nothing, so a non-zero "missing" column means the total is
  low.  The last column splits the bytes by the directory the files live in.

READ-ONLY.  Builds nothing, writes nothing, touches no git state.

RUN
    python3 tools/incbin_bytes.py                       # ../kn5000-roms-disasm
    python3 tools/incbin_bytes.py --repo /path/to/kn5000-roms-disasm
"""

import argparse
import ast
import operator
import os
import re
import subprocess
import sys

TREES = ["v10/maincpu", "v9/maincpu", "v7/maincpu", "v142/subcpu", "subcpu/boot",
         "hdae5000", "table_data", "custom_data", "wsa1"]
INCBIN = re.compile(r'^\s*(?:[A-Za-z_.$][\w.$]*:\s*)?\.incbin\s+"([^"]+)"'
                    r'\s*(?:,\s*([^,;]+?))?\s*(?:,\s*([^,;]+?))?\s*(?:;.*)?$', re.I)
OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.FloorDiv: operator.floordiv, ast.LShift: operator.lshift}


def integer(expr):
    """Evaluate an integer expression of literals and + - * // <<, nothing else."""
    def ev(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            return OPS[type(node.op)](ev(node.left), ev(node.right))
        raise ValueError(f"not an integer expression: {expr!r}")
    return ev(ast.parse(expr.strip(), mode="eval").body)


def measure(repo, tree):
    files = subprocess.run(["git", "-C", repo, "ls-files", "--", tree + "/*.s"],
                           capture_output=True, text=True, check=True).stdout.split()
    total = count = missing = 0
    by_dir = {}
    for rel in files:
        src = os.path.join(repo, rel)
        with open(src, encoding="utf-8", errors="surrogateescape") as f:
            for line in f:
                if ".incbin" not in line:
                    continue
                m = INCBIN.match(line)
                if not m:
                    if re.match(r"^\s*[^;]*\.incbin", line):
                        print(f"  UNPARSED {rel}: {line.strip()[:100]}", file=sys.stderr)
                    continue
                name, off, length = m.groups()
                candidates = [os.path.join(os.path.dirname(src), name),
                              os.path.join(repo, tree, name), os.path.join(repo, name)]
                path = next((c for c in candidates if os.path.exists(c)), None)
                if path is None:
                    missing += 1
                    continue
                start = integer(off) if off else 0
                n = integer(length) if length else os.path.getsize(path) - start
                total += n
                count += 1
                d = os.path.relpath(os.path.dirname(path), repo)
                by_dir[d] = by_dir.get(d, 0) + n
    return total, count, missing, by_dir


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--repo", default=os.path.join(here, "..", "kn5000-roms-disasm"))
    args = ap.parse_args()
    repo = os.path.abspath(args.repo)
    head = subprocess.run(["git", "-C", repo, "rev-parse", "--short=9", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    print(f"kn5000-roms-disasm at {head}")
    print(f"{'tree':14s} {'directives':>10s} {'bytes':>11s} {'missing':>7s}  bytes by directory")
    for tree in TREES:
        total, count, missing, by_dir = measure(repo, tree)
        dirs = ", ".join(f"{d}: {n:,}" for d, n in sorted(by_dir.items(), key=lambda x: -x[1]))
        print(f"{tree:14s} {count:10d} {total:11,d} {missing:7d}  {dirs}")


if __name__ == "__main__":
    main()
