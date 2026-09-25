#!/usr/bin/env python3
"""check_doc_symbols_rev.py -- which symbol-like names a site page quotes in backticks do NOT exist in the
disassembly sources?

QUESTION THIS ANSWERS
  The Symbol Name Synchronization policy says every symbol a page quotes must
  exist in the current disassembly.  This lists, per page, the backticked
  identifiers that look like symbols (contain an underscore next to a capital,
  or a lower-to-upper case change) and occur nowhere in any committed .s / .inc
  / .c / .h / .ld file of the disassembly repository at REV.

  It reads COMMITTED BLOBS (git cat-file), so a result does not depend on
  anybody's uncommitted edits, and it reads them as bytes (many .s files carry
  non-UTF-8 bytes that a text grep silently skips).

  ⚠ A hit is a lead, not a verdict: prefixes written as `Foo_*` or `Foo_`,
  register or MAME macro names, notes-file stems and names quoted on purpose as
  retired all show up.  Read each one.

USAGE
  python3 tools/check_doc_symbols.py PAGE.md [PAGE.md ...] [--rev REV] [--repo DIR]
  REV defaults to HEAD; DIR to ../kn5000-roms-disasm relative to this repository.
"""
import argparse
import os
import re
import subprocess


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument("pages", nargs="+")
    ap.add_argument("--rev", default="HEAD")
    ap.add_argument("--repo", default=os.path.join(here, os.pardir, "kn5000-roms-disasm"))
    a = ap.parse_args()
    files = subprocess.run(["git", "-C", a.repo, "ls-tree", "-r", "--name-only", a.rev],
                           capture_output=True, text=True, check=True).stdout.split("\n")
    files = [f for f in files if f.endswith((".s", ".inc", ".c", ".h", ".ld"))]
    idents = set()
    p = subprocess.Popen(["git", "-C", a.repo, "cat-file", "--batch"],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    for f in files:
        p.stdin.write(("%s:%s\n" % (a.rev, f)).encode())
        p.stdin.flush()
        hdr = p.stdout.readline().split()
        data = p.stdout.read(int(hdr[2]))
        p.stdout.read(1)
        idents.update(re.findall(rb'[A-Za-z_][A-Za-z0-9_]*', data))
    p.stdin.close()
    idents = {i.decode() for i in idents}
    for page in a.pages:
        t = open(page, encoding="utf-8").read()
        toks = set(re.findall(r'`([A-Za-z_][A-Za-z0-9_]*)', t))
        miss = sorted(k for k in toks
                      if re.search(r'[A-Z].*_|_.*[A-Z]|[a-z][A-Z]', k) and k not in idents)
        print("%s: %s" % (page, " ".join(miss) if miss else "all present"))


if __name__ == "__main__":
    main()
