#!/usr/bin/env python3
"""check_doc_retired_labels.py -- which names a page quotes were LABELS at one disassembly commit and
are no longer labels at a later one?

QUESTION ANSWERED
  `check_doc_symbols.py` accepts a name if it occurs anywhere in the sources, comments
  included.  A rename usually leaves the old name behind in a "formerly X" comment, so a
  page that still quotes X as live passes that lint.  This tool is stricter and narrower:
  it takes two commits of the disassembly repository, OLD and NEW, collects the names that
  are DEFINED at each one, and lists every backticked name on the given pages that was
  defined at OLD and is not defined at NEW.  That is exactly the set of names a body of
  work between OLD and NEW retired (renamed or deleted), whatever comments survive.

  "Defined" means, read from committed blobs (git cat-file, as bytes, because many .s files
  hold non-UTF-8 bytes inside .ascii literals):
    - .s / .inc / .asm: a column-0 label `NAME:`, or `.equ NAME,` / `.set NAME,` /
      `NAME = value` / `.globl NAME`;
    - .sym (the MN10300 trees' symbol files): the name column of a non-comment row;
    - .c / .h / .ld: every identifier (C definitions are not parsed; this errs towards
      "still defined", so it can only under-report).

  WHAT A HIT MEANS.  The name was a label at OLD and is not one at NEW.  The page either
  quotes it as history on purpose ("formerly `X`") or is stale.  Read each line.
  A clean run does not certify a page.

RUN
  python3 tools/check_doc_retired_labels.py --old ea51f2d51 --new HEAD *.md
  (--repo defaults to ../technics-roms-disasm)
"""
import argparse
import os
import re
import subprocess
import sys

NAME = re.compile(r'`([A-Za-z_][A-Za-z0-9_]*)(?:\(\))?`')
LABEL = re.compile(rb'^([A-Za-z_][A-Za-z0-9_]*):', re.M)
EQU = re.compile(rb'^\s*\.(?:equ|set|globl|global)\s+([A-Za-z_][A-Za-z0-9_]*)', re.M)
ASSIGN = re.compile(rb'^([A-Za-z_][A-Za-z0-9_]*)\s*=', re.M)
IDENT = re.compile(rb'[A-Za-z_][A-Za-z0-9_]*')


def defined_names(repo, rev):
    files = subprocess.run(['git', '-C', repo, 'ls-tree', '-r', '--name-only', rev],
                           capture_output=True, check=True).stdout.decode().split('\n')
    files = [f for f in files if f.endswith(('.s', '.inc', '.asm', '.sym', '.c', '.h', '.ld'))
             and not f.startswith('archive/')]
    names = set()
    proc = subprocess.Popen(['git', '-C', repo, 'cat-file', '--batch'],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    for f in files:
        proc.stdin.write(('%s:%s\n' % (rev, f)).encode())
        proc.stdin.flush()
        header = proc.stdout.readline().split()
        if len(header) < 3 or header[1] != b'blob':
            continue
        data = proc.stdout.read(int(header[2]))
        proc.stdout.read(1)
        if f.endswith(('.s', '.inc', '.asm')):
            for rx in (LABEL, EQU, ASSIGN):
                names.update(m.decode() for m in rx.findall(data))
        elif f.endswith('.sym'):
            for line in data.split(b'\n'):
                line = line.split(b';')[0].split(b'#')[0].split()
                for tok in line:
                    if IDENT.fullmatch(tok) and not re.fullmatch(rb'(0x)?[0-9A-Fa-f]+', tok):
                        names.add(tok.decode())
        else:
            names.update(m.decode() for m in IDENT.findall(data))
    proc.stdin.close()
    proc.wait()
    return names


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('pages', nargs='+')
    ap.add_argument('--old', required=True)
    ap.add_argument('--new', default='HEAD')
    ap.add_argument('--repo', default=os.path.join(here, '..', 'technics-roms-disasm'))
    a = ap.parse_args()
    retired = defined_names(a.repo, a.old) - defined_names(a.repo, a.new)
    total = 0
    for page in a.pages:
        with open(page, encoding='utf-8', errors='replace') as fh:
            lines = fh.read().splitlines()
        hits = {}
        for i, line in enumerate(lines, 1):
            for m in NAME.finditer(line):
                if m.group(1) in retired:
                    hits.setdefault(m.group(1), []).append(i)
        for n, ls in sorted(hits.items()):
            print('%s\t%s\t%s' % (page, n, ','.join(map(str, ls[:8]))))
        total += len(hits)
    print('%d retired name(s) quoted; %d names retired between %s and %s'
          % (total, len(retired), a.old, a.new), file=sys.stderr)


if __name__ == '__main__':
    main()
