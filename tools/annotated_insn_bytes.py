#!/usr/bin/env python3
"""Which `.byte` lines does a tree's own source annotate as an unspelt instruction?

QUESTION IT ANSWERS
    raw-byte-code-elimination.md lists the sub-CPU payload (v142) and SX-WSA1R
    prom_b at zero code-as-`.byte`.  wsa1_unspellable_forms.py only counts lines
    whose comment is `; ADDR  b0 b1 ...` (a byte echo); prom_b's convention is
    `; ADDR  mnemonic   [llvm-mc cannot encode this]` and v142's is
    `; mnemonic  (unidasm; no llvm-mc spelling)`, so neither is seen.  This script
    lists every `.byte` line whose comment (or the comment line straight after it)
    says the assembler cannot spell or encode it, and sums sites and bytes.

RUN
    python3 tools/annotated_insn_bytes.py v142/subcpu wsa1/prom_b wsa1/prom_a v10/maincpu
    python3 tools/annotated_insn_bytes.py --repo /path/to/kn5000-roms-disasm v142/subcpu
    (tree arguments are relative to the kn5000-roms-disasm root; default ../kn5000-roms-disasm)

    Measured 2026-10-15 at kn5000-roms-disasm 3417969c0 (clean tree):
        v142/subcpu   12 sites, 46 B   (10 x `minc1 ...,IX`, 2 x `ldc` to DMA control regs)
        wsa1/prom_b   68 sites, 221 B  (66 instruction readings, 216 B; 2 unidasm `db`, 5 B)
                      -- agrees with the committed wsa1/notes/promb_macro_rewrite.py --census
                         ("prom_b `cannot encode` rows: 68")
        v10/maincpu    9 sites, 18 B   v9/maincpu 9, 18 B   v7/maincpu 11, 30 B
        wsa1/prom_a, wsa1/prom_c, subcpu/boot, table_data, hdae5000: 0

SIGNAL
    A line counts when it is a `.byte` directive and its comment matches
    "cannot encode", "cannot spell" or "no llvm-mc spelling".  It is a list of
    what the source itself admits, not a verdict that every line is code.
"""
import glob
import os
import re
import sys

BYTE = re.compile(r"^\s*(?:\S+:)?\s*\.byte\s+([^;]*);(.*)$", re.I)
ADMIT = re.compile(r"cannot encode|cannot spell|no llvm-mc spelling", re.I)


def main(roots):
    for root in roots:  # relative to the current directory (main() chdirs to --repo)
        sites = nbytes = 0
        for path in sorted(glob.glob(os.path.join(root, "**", "*.s"), recursive=True)):
            lines = open(path, encoding="latin-1").read().split("\n")
            for i, line in enumerate(lines):
                m = BYTE.match(line)
                if not m:
                    continue
                comment = m.group(2)
                nxt = lines[i + 1] if i + 1 < len(lines) else ""
                if ADMIT.search(comment) or (nxt.lstrip().startswith(";") and ADMIT.search(nxt)
                                             and not BYTE.match(nxt)):
                    n = len([b for b in m.group(1).split(",") if b.strip()])
                    sites += 1
                    nbytes += n
                    print(f"  {path}:{i + 1}  {n} B  ;{comment.strip()[:70]}")
        print(f"{root}: {sites} site(s), {nbytes} B")


if __name__ == "__main__":
    import argparse
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description="annotated .byte instruction sites per tree")
    ap.add_argument("--repo", default=os.path.join(here, "..", "kn5000-roms-disasm"))
    ap.add_argument("trees", nargs="+")
    args = ap.parse_args()
    os.chdir(args.repo)
    main(args.trees)
