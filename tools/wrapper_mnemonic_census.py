#!/usr/bin/env python3
"""wrapper_mnemonic_census.py -- how many LLVM wrapper mnemonics are actually left?

QUESTION ANSWERED
  llvm-semantic-instructions.md claims a migration status per phase.  For a
  long time it said "all five phases are complete ... zero remaining
  occurrences of every wrapper mnemonic named below" while its own Phase 4
  table still listed `lda_dpi` and `bit_dri`, both of which are still in the
  sources and still defined in the backend.  This counts them, so the page
  states a measured number instead of a remembered one.

  A wrapper mnemonic is one whose NAME encodes the operand form
  (`st_dri3b L, 0xfd, 0xb8, 0x01`) rather than the operation.  The two that
  survive are the hardest kind: their operands are literal mode and
  displacement bytes, not modelled operands, so no rename reaches them until
  the backend models the operand.  See ASSESSMENT-syntax-convergence in the
  disassembly repo, bucket 3, "byte emitters wearing a mnemonic's name".

WHAT COUNTS AS A SITE
  One source line whose first token is the mnemonic.  That is deliberately
  the same rule the disassembly repo's own notes/syntax-convergence-probes/
  mnemonic_census.py uses, so the two agree.

  /!\\ The sources are latin-1, NOT UTF-8.  Decoding them as UTF-8 -- or
  running GNU grep over them in a UTF-8 locale -- can silently return ZERO
  matches on a file that plainly contains the string.  Read as latin-1.

READ-ONLY.  Writes nothing, builds nothing, touches no git state.

RUN
    python3 tools/wrapper_mnemonic_census.py
    python3 tools/wrapper_mnemonic_census.py --repo /path/to/kn5000-roms-disasm

EXPECTED
  41 of the 43 Phase 2-5 families at zero; `lda_dpi` and `bit_dri` nonzero.
  A family that has just reached zero is good news -- update the page.
  A family that has RISEN from zero means a conversion regressed: find out
  why before touching the page.
"""
import argparse
import collections
import os
import re
import subprocess
import sys

# The Phase 2-5 wrapper families, exactly as llvm-semantic-instructions.md
# lists them. Kept as one flat list because the page's claim is about the
# whole set ("41 of 43"), not about any one phase.
FAMILIES = [
    # Phase 2 -- 24-bit addressing semantics
    "ld16_24", "ld32_24", "st16_24", "st32_24", "sti16_24", "cpi8_24", "cpdi16_24",
    # Phase 3 -- extended register pair modes
    "ldto_berp", "ldfr_berp", "ldto_werp", "ldfr_werp", "ldi_berp", "ldi_werp",
    "push_werp", "pop_werp", "cpi_berp", "cpi_werp", "inc1_berp", "inc1_werp",
    "cp_werp", "cp_srib_im",
    # Phase 4 -- SRI/DRI indirect modes
    "st_dri3b", "st_dri3w", "st_dri3l", "ld_srib3", "ld_sriw3", "lda_dri3",
    "lda_dpi", "ld_spib", "jp_dri", "stib_dri", "stib_dpi", "st_dpiw",
    "stiw_dri", "bit_dri",
    # Phase 5 -- miscellaneous
    "ld_srib", "ld_sriw", "mrid2", "ldada", "ldda8", "stda8", "addm32_24", "addmi16",
]

FIRST_TOKEN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\b")


def tracked_sources(repo):
    out = subprocess.run(["git", "ls-files", "*.s"], cwd=repo,
                         capture_output=True, text=True, check=True).stdout
    return [os.path.join(repo, p) for p in out.split()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo",
                    default=os.path.expanduser("~/compartilhado/kn5000-roms-disasm"),
                    help="the disassembly repository (read only)")
    a = ap.parse_args()
    if not os.path.isdir(os.path.join(a.repo, ".git")):
        sys.exit("not a git repository: %s" % a.repo)

    wanted = set(FAMILIES)
    total = collections.Counter()
    per_tree = collections.defaultdict(collections.Counter)

    files = tracked_sources(a.repo)
    for path in files:
        with open(path, "rb") as fh:
            text = fh.read().decode("latin-1")     # NOT utf-8; see the docstring
        tree = os.path.relpath(path, a.repo).split(os.sep)[0]
        for line in text.splitlines():
            m = FIRST_TOKEN.match(line)
            if m and m.group(1) in wanted:
                total[m.group(1)] += 1
                per_tree[m.group(1)][tree] += 1

    trees = sorted({t for c in per_tree.values() for t in c})
    print("tracked .s files: %d in %s" % (len(files), a.repo))
    print()
    nonzero = [f for f in FAMILIES if total[f]]
    print("families at zero : %d of %d" % (len(FAMILIES) - len(nonzero), len(FAMILIES)))
    print()
    if not nonzero:
        print("every Phase 2-5 wrapper family is at zero.")
        return
    head = "%-12s %7s" % ("mnemonic", "total")
    print(head + "".join("%12s" % t for t in trees))
    for f in nonzero:
        row = "%-12s %7d" % (f, total[f])
        print(row + "".join("%12s" % (per_tree[f][t] or "-") for t in trees))


if __name__ == "__main__":
    main()
