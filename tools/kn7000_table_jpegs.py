#!/usr/bin/env python3
"""kn7000_table_jpegs.py -- the JPEG figures on kn7000-table-rom.md, measured.

Question: how many JFIF streams does a KN7000 table-ROM image hold, how many
decode with an ordinary decoder (Pillow), and what sizes are they?
Recipe as on kn7000-table-rom.md: scan for ff d8 ff e0, end at the next ff d9.
Run: python3 tools/kn7000_table_jpegs.py path/to/kn7000_table.rom   (needs Pillow; the
image, as rebuilt from the update discs by technics-roms-disasm kn7000/, is not in this repository)
Prints counts only, never ROM contents.
Result 2026-10-15: 119 SOI+APP0 hits, all tagged JFIF; 117 decode, 2 fail."""
import io, sys, collections
from PIL import Image
d = open(sys.argv[1], 'rb').read()
print('image size', len(d))
starts = []
i = d.find(b'\xff\xd8\xff\xe0')
while i >= 0:
    starts.append(i)
    i = d.find(b'\xff\xd8\xff\xe0', i + 4)
print('SOI+APP0 hits', len(starts))
jfif = [s for s in starts if d[s+6:s+11] == b'JFIF\x00']
print('of which JFIF tag', len(jfif))
ok = 0
sizes = collections.Counter()
bad = 0
for k, s in enumerate(starts):
    nxt = starts[k+1] if k + 1 < len(starts) else len(d)
    # full stream up to the next SOI (decoder stops at EOI itself)
    blob = d[s:nxt]
    try:
        im = Image.open(io.BytesIO(blob)); im.load()
        ok += 1; sizes[im.size] += 1
    except Exception as e:
        bad += 1
print('decoded', ok, 'failed', bad)
for sz, n in sizes.most_common(): print(sz, n)
