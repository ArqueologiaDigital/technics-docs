#!/usr/bin/env python3
"""kn7000_style_catalog.py -- what does the KN7000 Music Stylist catalog really hold?

QUESTION ANSWERED
  kn7000-rhythm-catalog.md lists 270 names walked from StyleGenreTable
  (program ROM 0x4873ACC0) and calls them "styles".  Each sub-table entry is
  {u32 namePtr, u32 idxListPtr}; idxListPtr points at u16 style numbers ended
  by 0xFFFF.  This walks the structure and reports:
    - names per genre and the style numbers each name indexes;
    - whether every style number k is StyleRecordTable[k] (0x4873BEE8,
      24-byte records, +4 = namePtr) and whether those name pointers are the
      contiguous 17-byte list at 0x485D1038 + 17*k;
    - optionally (--page), how many headings / styles are missing from the
      "Style / Music-Stylist Names" list of kn7000-sound-names.md.

SIGNAL READ
  program ROM = CPU 0x48400000 + file offset (kn7000_program.rom, as rebuilt by technics-roms-disasm kn7000/).
  Pass = every catalog entry has exactly 4 indices, 1080 distinct indices
  0..1079, and StyleRecordTable[k].namePtr == 0x485D1038 + 17*k for all k.

RUN
  python3 -I tools/kn7000_style_catalog.py PATH/kn7000_program.rom [--page kn7000-sound-names.md]
  (the 8 MB program image as rebuilt from the update discs by technics-roms-disasm kn7000/;
  this repository does not hold it)

OUTPUT on 2026-10-15 (kn7000_disassembly baserom/kn7000_program.rom):
  11 genres, 270 entries, 4 indices each, 1080 refs / 1080 distinct (0..1079);
  StyleRecordTable: 1080 records match the 17-byte list.
  sound-names page: 931 names; 74 of 270 headings and 355 of 1080 styles missing.
Prints names only to stdout; publishes nothing.
"""
import argparse, html, struct, sys

BASE = 0x48400000
GENRE_TABLE = 0x4873ACC0
STYLE_RECORDS = 0x4873BEE8
NAME_LIST = 0x485D1038

ap = argparse.ArgumentParser()
ap.add_argument('rom')
ap.add_argument('--page')
ap.add_argument('-v', action='store_true', help='print every heading and its styles')
a = ap.parse_args()
rom = open(a.rom, 'rb').read()
def r32(x): return struct.unpack_from('<I', rom, x - BASE)[0]
def r16(x): return struct.unpack_from('<H', rom, x - BASE)[0]
def s16(x): return rom[x - BASE:x - BASE + 16].decode('latin1').rstrip()
def inrom(x): return BASE <= x < BASE + len(rom)

heads, refs, counts = [], [], set()
g = GENRE_TABLE; ng = 0
while inrom(r32(g)):
    gname = s16(r32(g)); sub = r32(g + 4); n = 0
    while inrom(r32(sub)):
        h = s16(r32(sub)); q = r32(sub + 4); idx = []
        while r16(q) != 0xFFFF:
            idx.append(r16(q)); q += 2
        heads.append(h); refs += idx; counts.add(len(idx)); n += 1
        if a.v: print(f'  {gname} / {h}: {idx}')
        sub += 8
    print(f'{gname}: {n} entries'); ng += 1; g += 8
print(f'{ng} genres, {len(heads)} entries, indices per entry {sorted(counts)}, '
      f'{len(refs)} refs / {len(set(refs))} distinct ({min(refs)}..{max(refs)})')
ok = 0
for k in range(max(refs) + 1):
    if r32(STYLE_RECORDS + 24 * k + 4) == NAME_LIST + 17 * k: ok += 1
print(f'StyleRecordTable: {ok} of {max(refs)+1} records point at {NAME_LIST:#x} + 17*k')
styles = [s16(NAME_LIST + 17 * k) for k in range(max(refs) + 1)]
if a.page:
    lines = open(a.page, encoding='utf-8').read().splitlines()
    s = lines.index('# Style / Music-Stylist Names')
    e = next(i for i in range(s, len(lines)) if lines[i].startswith('## Sound Arranger PAD presets'))
    names = {html.unescape(l[:-4]).rstrip() for l in lines[s:e] if l.endswith('<br>')}
    mh = [h for h in heads if h not in names]; ms = [x for x in styles if x not in names]
    print(f'page list: {len(names)} distinct names; missing {len(mh)} of {len(heads)} headings, '
          f'{len(ms)} of {len(styles)} styles; first missing styles: {ms[:5]}')
