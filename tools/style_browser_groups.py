#!/usr/bin/env python3
"""style_browser_groups.py -- the MSTYLE browser's ten style groups, read from the firmware.

Question: which style-group table does each entry of the MstStyle browser root point to, and
what group name does the firmware show for it?  (accompaniment-engine.md "Style Groups" table)
Reads the build-generated v10/maincpu/includes/generated/naka_style_bitmaps.bin (built from the
committed v10/maincpu/ui_widgets/naka_style_bitmaps.c), whose first byte is ROM 0xEB71BE.
The root is at ROM 0xECFCA4 (MstStyle1Grid_CellSelect_Data): 10 x {u32 group-name ptr, u32 group-table ptr},
little-endian; each group table is {u32 style name, u32 variation table} x n + an all-zero entry
(style_bitmaps.s:2842-2845, :3519-3533).
Run `make` in kn5000-roms-disasm first (the .bin is a build product).
Usage: python3 tools/style_browser_groups.py [/path/to/kn5000-roms-disasm]   (default ../kn5000-roms-disasm)

Result 2026-10-15 (kn5000-roms-disasm 3417969c0): group 0 Easy Listening at 0xECE2F0
(StyleGroup_ModernDance_Table), 31 styles ... group 9 Latin / World at 0xECF9AA, 29 styles;
the per-group counts match music-stylist-database.md.
"""
import struct, sys, os
root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'kn5000-roms-disasm')
b = open(os.path.join(root, 'v10/maincpu/includes/generated/naka_style_bitmaps.bin'), 'rb').read()
BASE = 0xEB71BE
def cstr(a):
    o = a - BASE
    return b[o:o + 16].split(b'\0')[0].decode('latin1').rstrip()
syms = {}
for line in open(os.path.join(root, 'symbols/maincpu_v10_symbols_reference.txt')):
    p = line.split()
    if len(p) >= 2:
        try: syms.setdefault(int(p[1], 16), []).append(p[0])
        except ValueError: pass
for i in range(10):
    name, table = struct.unpack_from('<II', b, 0xECFCA4 - BASE + 8 * i)
    n = 0
    while struct.unpack_from('<I', b, table - BASE + 8 * n)[0]:
        n += 1
    print(f"group {i}: {cstr(name)!r:20} table 0x{table:06X} {syms.get(table, ['(no label)'])} styles={n}")
