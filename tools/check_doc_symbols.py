#!/usr/bin/env python3
"""check_doc_symbols.py -- do the symbol names a page quotes exist in the disassembly?

QUESTION ANSWERED
  The site's policy (roms-disasm CLAUDE.md, "Symbol Name Synchronization") is
  that every symbol quoted in backticks must be a name the CURRENT assembly and
  C sources carry.  Labels get renamed all the time -- Wave 2 (2026-09-25)
  alone retired about 3,700 names -- so pages rot.  This lists every
  `Backticked_Identifier` on the given pages that occurs NOWHERE in the
  disassembly sources, with the line numbers it appears on.

  An identifier counts as "symbol-like" (and is checked) if it contains an
  underscore or a lower-to-upper case change (`ClassProc`, `HDAE5000_Foo`).
  Plain words and hex numbers are skipped.

  WHAT A HIT MEANS.  A name that is absent from every .s/.c/.h/.ld/.inc file.
  Expect three kinds of hit, only the first of which is a defect:
    - a stale label (renamed or retired in the sources) -- fix the page;
    - a name deliberately quoted as history ("was `HDAE5000_File_Save`");
    - a name from another code base (MAME C++, Python, the Mines project).
  A clean run does not certify a page: a name can exist and the page can
  still say something false about it.

  The sources are read as BYTES (65 .s files hold non-UTF-8 bytes inside
  .ascii literals; a text-mode or `grep -I` search silently skips them).

RUN
  python3 tools/check_doc_symbols.py event-codes.md hdae5000-homebrew.md
  python3 tools/check_doc_symbols.py --repo ../kn5000-roms-disasm *.md
"""
import argparse
import os
import re
import sys

TOPS = ['v10', 'v9', 'v7', 'v142', 'subcpu', 'table_data', 'custom_data',
        'hdae5000', 'shared', 'wsa1']
EXTS = ('.s', '.c', '.h', '.ld', '.inc')
NAME = re.compile(r'`([A-Za-z_][A-Za-z0-9_]*)(?:\(\))?`')


def source_tokens(repo):
    toks = set()
    for top in TOPS:
        for root, _dirs, files in os.walk(os.path.join(repo, top)):
            for f in files:
                if f.endswith(EXTS):
                    with open(os.path.join(root, f), 'rb') as fh:
                        data = fh.read()
                    toks.update(m.decode() for m in re.findall(rb'[A-Za-z_][A-Za-z0-9_]*', data))
    return toks


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('pages', nargs='+')
    ap.add_argument('--repo', default=os.path.join(here, '..', 'kn5000-roms-disasm'),
                    help='kn5000-roms-disasm checkout (default: sibling of this repo)')
    args = ap.parse_args()
    if not os.path.isdir(os.path.join(args.repo, 'v10')):
        sys.exit('no disassembly at %s (use --repo)' % args.repo)
    toks = source_tokens(args.repo)
    total = 0
    for page in args.pages:
        with open(page, encoding='utf-8', errors='replace') as fh:
            lines = fh.read().splitlines()
        missing = {}
        for i, line in enumerate(lines, 1):
            for m in NAME.finditer(line):
                n = m.group(1)
                if n in toks:
                    continue
                if '_' not in n and not re.search(r'[a-z][A-Z]', n):
                    continue
                missing.setdefault(n, []).append(i)
        for n, ls in sorted(missing.items()):
            print('%s\t%s\t%s' % (page, n, ','.join(map(str, ls[:8]))))
        total += len(missing)
    print('%d name(s) not found in the sources' % total, file=sys.stderr)


if __name__ == '__main__':
    main()
