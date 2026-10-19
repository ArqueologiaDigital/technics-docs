#!/usr/bin/env python3
# kn7000_picture_gallery.py -- print the gallery block of kn7000-picture-rom.md from the 100 pictures in
# assets/images/kn7000-picture-rom/ (copied from kn7000_disassembly src/picture/).
#
# Each caption gives the PRESET number and where the picture sits in IC19, as the CPU sees it at
# 0x57800000. Those offsets are recomputed here the way the chip lays them out (first picture at 0x404,
# each one padded to a 4-byte boundary), so the captions need nothing but the pictures.
#   python3 tools/kn7000_picture_gallery.py > /tmp/gallery.html   (then paste between the markers)
import os

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'images', 'kn7000-picture-rom')
FIG = ('<figure style="margin:0;text-align:center;"><a href="{{{{ "/assets/images/kn7000-picture-rom/{name}" | relative_url }}}}">'
       '<img src="{{{{ "/assets/images/kn7000-picture-rom/{name}" | relative_url }}}}" loading="lazy" alt="PRESET {n}" '
       'style="max-width:100%;height:auto;border:1px solid #ccc;border-radius:3px;"></a>'
       '<figcaption style="font-size:0.7rem;color:#777;">PRESET {n} · 0x{addr:08X} · {kb:.1f} KB</figcaption></figure>')

GROUPS = ['Landscapes', 'Coasts, harbours, gardens and houses', 'Cities by day and by night',
          'Streets and towns', 'Interiors and still lifes', 'Christmas and winter',
          'Music: stages, instruments, a Technics keyboard and turntables', 'Animals',
          'Title cards', 'Numbers 1 to 10']
off = 0x404
for g, title in enumerate(GROUPS):
    print(f'### PRESET {10 * g}-{10 * g + 9}: {title}\n')
    print('<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;margin:1rem 0;">')
    for n in range(10 * g, 10 * g + 10):
        name = f'preset_{n:02d}.jpg'
        size = os.path.getsize(os.path.join(DIR, name))
        print(FIG.format(name=name, n=n, addr=0x57800000 + off, kb=size / 1024))
        off += size + (-size % 4)
    print('</div>\n')
assert off == 0x1FF49C, f'the pictures end at {off:#x}, not 0x1FF49C: the files are not the chip\'s'
