#!/usr/bin/env python3
"""ic307_wave_directory.py -- the wave-directory figures on waveform-rom-format.md, measured.

QUESTION ANSWERED
  waveform-rom-format.md says IC307 (the KN5000's 4 MB waveform ROM) is four
  independent 1 MB pages, each with its own directory of {param_ptr, wave_offset}
  pairs whose length N is declared by entry 0 (param_ptr = 4 x N), and quotes:
  N per page (198, 168, 1,072, 57), the 1,495 directory slots and 1,413 distinct
  waves of the whole chip, page 0's 186 distinct waves ranging from 80 samples up,
  and the sample lengths of page 0's last two waves (0xFCA6: 4,736; 0xFEF6: 2,128).
  This prints those numbers from the dump.

HOW IT MEASURES
  Per page: N = u16 at the page base / 4; the directory is N little-endian
  {u16 param_ptr, u16 wave_offset} pairs.  "backref" counts entries whose
  parameter record begins with the same wave_offset (a consistency check of the
  page model: it should equal N).  A wave's length in samples is the distance to
  the next distinct wave_offset (x 16 bytes; the last wave runs to the page end),
  divided by 2 for 16-bit PCM.

  It needs the ROM image, which this repository does not hold and never will.
  It prints counts and offsets only, never ROM bytes.  Run it with python3 -I so
  nothing next to the dump can be imported.

RUN
    python3 -I tools/ic307_wave_directory.py path/to/kn5000_waveform_rom.ic307

Result 2026-10-15: N 198/168/1072/57, 1,495 slots, backref 1,495/1,495,
1,413 distinct waves; page 0: 186 distinct, 80 to 37,520 samples, 0xFCA6 at
sorted index 184 = 4,736 samples, 0xFEF6 at 185 = 2,128 samples.
"""

import struct
import sys

PAGE = 0x100000


def page_directory(rom, page):
    base = page * PAGE
    n = struct.unpack_from("<H", rom, base)[0] // 4
    return base, [struct.unpack_from("<HH", rom, base + 4 * i) for i in range(n)]


def main():
    rom = open(sys.argv[1], "rb").read()
    if len(rom) != 4 * PAGE:
        sys.exit(f"expected a 4,194,304-byte image, got {len(rom):,} bytes")
    slots = distinct = 0
    for page in range(4):
        base, entries = page_directory(rom, page)
        backref = sum(1 for p, w in entries if struct.unpack_from("<H", rom, base + p)[0] == w)
        waves = sorted({w for _, w in entries})
        print(f"page {page}: N {len(entries):5,}  backref {backref:5,}  distinct waves {len(waves):5,}"
              f"  first PCM +0x{min(waves) * 16:06X}  last wave +0x{max(waves) * 16:06X}")
        slots += len(entries)
        distinct += len(waves)
    print(f"chip: {slots:,} directory slots, {distinct:,} distinct waves")

    _, entries = page_directory(rom, 0)
    waves = sorted({w for _, w in entries})
    ends = [w * 16 for w in waves[1:]] + [PAGE]
    lengths = [(end - w * 16) // 2 for w, end in zip(waves, ends)]
    print(f"page 0: {len(waves)} distinct waves, {min(lengths):,} to {max(lengths):,} samples")
    for w in (0xFCA6, 0xFEF6):
        i = waves.index(w)
        print(f"page 0 wave 0x{w:04X}: sorted index {i}, {lengths[i]:,} samples")


if __name__ == "__main__":
    main()
