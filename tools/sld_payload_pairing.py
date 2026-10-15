#!/usr/bin/env python3
"""sld_payload_pairing.py -- which sub-CPU payload does each KN5000 program-update disc carry?

QUESTION ANSWERED
  subcpu-firmware-images.md and subcpu-payload-provenance.md (section 5 H5, section 7
  row 6) say the v1.42->v9, v1.41->v7/v8 and v1.40->v5/v6 pairings in MAME's BIOS
  list "rest on filename inference" because "only the v10 update disc is available".
  The Internet Archive item technics-kn5000-system-update-disks carries the
  extracted HKMSPRG.SLD of every program update disc v5..v10.  Each SLD is two
  concatenated SLIDE4K streams (main program, then sub-CPU payload).  This finds
  every "SLIDE4K" header in each SLD, prints its offset and 24-bit big-endian size
  field, and tests whether the stream that starts at the second header is
  byte-identical to (and the same length as) any of the compressed payload files
  given with --payload.

SIGNAL
  "stream2 == <file>" means the disc's sub-CPU stream is that compressed payload,
  byte for byte, and the SLD ends exactly where it ends.

RUN
  SLDs (public): curl -sSL -o kn5000_v9_HKMSPRG.SLD \
    "https://archive.org/download/technics-kn5000-system-update-disks/Technics%20KN5000%20System%20Update%20Disks/03-Extracted_contents_of_the_disks/kn5000_v9_disk/HKMSPRG.SLD"
  (likewise v5..v10; IA sha1s: v5 c8a08ddee5ff, v6 9952e5bf3278, v7 35d6b79ff9f7,
   v8 c7cf5e13ac9a, v9 c1e8aa9ac563, v10 213854ed1e79)
  python3 -I tools/sld_payload_pairing.py --payload kn5000_subprogram_v14?_compressed.rom -- kn5000_v*_HKMSPRG.SLD
  (the compressed payloads are the files of MAME's kn5000 ROM set; this
  repository does not hold them)

Result 2026-10-15: stream 2 of v5 and v6 == v1.40 (93,124 B), of v7 and v8 ==
v1.41 (93,181 B), of v9 and v10 == v1.42 (93,203 B), each ending the SLD exactly.
"""
import sys

args = sys.argv[1:]
payloads, slds = [], []
target = slds
i = 0
while i < len(args):
    a = args[i]
    if a == "--payload":
        target = payloads
    elif a == "--":
        target = slds
    else:
        target.append(a)
    i += 1

pdata = {p: open(p, "rb").read() for p in payloads}
for s in slds:
    d = open(s, "rb").read()
    offs = []
    pos = d.find(b"SLIDE4K")
    while pos != -1:
        offs.append(pos)
        pos = d.find(b"SLIDE4K", pos + 1)
    desc = ", ".join(f"0x{o:06X} size=0x{int.from_bytes(d[o+8:o+11], 'big'):06X}" for o in offs)
    print(f"{s}: len={len(d)} headers: {desc}")
    if len(offs) >= 2:
        tail = d[offs[1]:]
        hits = [p for p, b in pdata.items() if b == tail]
        print(f"   stream1 = {offs[1]} B, stream2 = {len(tail)} B; stream2 == {hits if hits else 'none of the given payloads'}")
