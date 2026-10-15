#!/usr/bin/env python3
"""sld_program_chooser.py -- decode the main-program stream of each public KN5000
update disc and read the sub-CPU payload chooser bytes from it.

QUESTION ANSWERED
  Does every preserved KN5000 program version try the IC19 sub-CPU image first?
  subcpu-payload-provenance.md (sections 2, 3 and 7) once said the v5/v6 program
  ROMs were not available, and that one byte at file offset 0x1FFEED of either
  would decide whether the table-data fallback (candidate A) was ever live.
  The Internet Archive item technics-kn5000-system-update-disks carries every
  program update disc's HKMSPRG.SLD (public).  Stream 1 of each SLD is the
  SLIDE4K-compressed 2 MB main program.  This decodes stream 1 with an inline
  SLIDE4K decoder (match length = low nibble + 3, as in kn5000-roms-disasm
  scripts/build/compress_lzss.py decode_compressed and the firmware's own
  LZSS_Decompress copy loop, table_data/kn5000_table_data.s:4395-4430; NOT
  scripts/build/decompress_lzss.py, whose decompress_slide4k uses + 2 and comes
  out 1,871,xxx bytes short) and prints the decoded size, CRC32 (compare with MAME's
  BIOS list: v5 fbd035e3, v6 0205db30, v7 a5a25eb0, v8 46b4b242, v9 c791d765,
  v10 00303406) and bytes 0x1FFEEB-0x1FFEEF.

SIGNAL
  bytes@0x1FFEEB "ff ff ff 00 ff": 0x1FFEED (SubCPU_FlashPayloadEnableFlag) = 0xFF,
  i.e. that firmware tries the IC19 0x3E0000 image first, like v7/v9/v10.

RUN
  Fetch the public SLDs first (see tools/sld_payload_pairing.py for the URLs and
  sha1s), then:
    python3 -I tools/sld_program_chooser.py kn5000_v*_HKMSPRG.SLD

Result 2026-10-15: v5 fbd035e3, v6 0205db30, v7 a5a25eb0, v8 46b4b242,
v9 c791d765, v10 00303406 (each 2,097,152 B, MAME's CRCs), and every one reads
ff ff ff 00 ff at 0x1FFEEB.
"""
import os
import sys
import zlib


def decompress_slide4k(src, size):
    window = bytearray(4096)
    wpos = 0xFEE
    out = bytearray()
    i = 0
    while i < len(src) and len(out) < size:
        flags = src[i]
        i += 1
        for bit in range(8):
            if i >= len(src) or len(out) >= size:
                break
            if flags & (1 << bit):
                b = src[i]
                i += 1
                out.append(b)
                window[wpos] = b
                wpos = (wpos + 1) & 0xFFF
            else:
                lo, hi = src[i], src[i + 1]
                i += 2
                off = ((hi & 0xF0) << 4) | lo
                for k in range((hi & 0x0F) + 3):
                    b = window[(off + k) & 0xFFF]
                    out.append(b)
                    window[wpos] = b
                    wpos = (wpos + 1) & 0xFFF
    return bytes(out[:size])


for path in sys.argv[1:]:
    d = open(path, "rb").read()
    second = d.find(b"SLIDE4K", 1)
    hdr = d[:11]
    assert hdr[:7] == b"SLIDE4K", path
    size = int.from_bytes(hdr[8:11], "big")
    prog = decompress_slide4k(d[11:second], size)
    print(f"{os.path.basename(path)}: decoded={len(prog)} crc32={zlib.crc32(prog):08x} "
          f"bytes@0x1FFEEB={prog[0x1FFEEB:0x1FFEF0].hex(' ')}")
