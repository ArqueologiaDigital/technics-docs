#!/usr/bin/env python3
"""menu_map_summary.py -- the at-a-glance tables of the MN10300 menu-map pages.

QUESTION ANSWERED
  The disassembly repository generates one GUI menu map per MILK image
  (kn7000/tools/gui_menu_map.py: kn7000/notes/gui-data-region/menu-map.md,
  kn7000/notes/sp7001-plugin-menu-map.md, kn2400/notes/gui-menu-map.md, ...).
  The site links those maps instead of copying them, and shows one summary
  table per map.  This prints that table, so the figures on the page can be
  re-derived from the generated map and checked against a newer one.

  --blocks   one row per block (`## Block NAME`): how many top-level objects
             (`### ` headings) and how many widget objects (`- ` bullets that
             start with a backticked class name) the block holds, and the
             first few top-level object names.
  --screens  one row per top-level object: its class (the line after the
             heading), how many widget objects its tree holds, and the first
             captions it shows (`title "..."`, `str "..."`, `init_str "..."`,
             `text "..."`; the plug-in's placeholder title "KssBg" skipped).

  The counts are of the map's lines, so they equal the map's own header
  ("8509 widget objects in 36 OT blocks; 754 top-level objects") when every
  object is listed once; the total is printed to stderr for that check.
  The tables are Markdown with space-padded, aligned columns.

RUN (from technics-docs, with the disassembly repository beside it)
  python3 tools/menu_map_summary.py --blocks  ../technics-roms-disasm/kn7000/notes/gui-data-region/menu-map.md
  python3 tools/menu_map_summary.py --blocks  ../technics-roms-disasm/kn2400/notes/gui-menu-map.md
  python3 tools/menu_map_summary.py --screens ../technics-roms-disasm/kn7000/notes/sp7001-plugin-menu-map.md
"""
import argparse
import re
import sys

OBJ = re.compile(r'^\s*- `(\w+)`')
CAPTION = re.compile(r'\b(?:title|str|init_str|text) "([^"]*)"')


def table(hdr, rows):
    w = [max(len(r[i]) for r in rows + [hdr]) for i in range(len(hdr))]
    line = lambda r: '| ' + ' | '.join(r[i].ljust(w[i]) for i in range(len(hdr))) + ' |'
    out = [line(hdr), '|' + '|'.join('-' * (x + 2) for x in w) + '|']
    return '\n'.join(out + [line(r) for r in rows])


def blocks(path, k):
    rows, cur, total = [], None, 0
    for ln in open(path, encoding='utf-8', errors='replace'):
        if ln.startswith('## Block '):
            cur = [ln[9:].strip(), 0, 0, []]
            rows.append(cur)
        elif ln.startswith('## '):
            cur = None
        elif cur is not None and ln.startswith('### '):
            cur[1] += 1
            cur[3].append(ln[4:].strip())
        elif cur is not None and OBJ.match(ln):
            cur[2] += 1
            total += 1
    out = [(b, str(t), str(o), ', '.join(s[:k]) + (', ...' if len(s) > k else ''))
           for b, t, o, s in rows]
    print('widget objects counted: %d, top-level: %d' % (total, sum(r[1] for r in rows)),
          file=sys.stderr)
    return table(('block', 'top-level', 'objects', 'first top-level objects'), out)


def screens(path, k):
    rows, cur, total = [], None, 0
    for ln in open(path, encoding='utf-8', errors='replace'):
        if ln.startswith('### '):
            cur = [ln[4:].strip(), '', 0, []]
            rows.append(cur)
        elif ln.startswith('## '):
            cur = None
        elif cur is None:
            continue
        elif not cur[1] and ln.startswith('`'):
            cur[1] = ln.split('`')[1]
        elif OBJ.match(ln):
            cur[2] += 1
            total += 1
            for c in CAPTION.findall(ln):
                c = c.strip()
                if c and c != 'KssBg' and c not in cur[3] and len(cur[3]) < k:
                    cur[3].append(c)
    out = [(n, '`%s`' % c, str(o), ', '.join('"%s"' % s for s in caps)) for n, c, o, caps in rows]
    print('widget objects counted: %d, top-level: %d' % (total, len(rows)), file=sys.stderr)
    return table(('screen', 'class', 'objects', 'first captions'), out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--blocks', action='store_true')
    g.add_argument('--screens', action='store_true')
    ap.add_argument('map')
    ap.add_argument('-k', type=int, default=3, help='names / captions per row (default 3)')
    a = ap.parse_args()
    print(blocks(a.map, a.k) if a.blocks else screens(a.map, a.k))


if __name__ == '__main__':
    main()
