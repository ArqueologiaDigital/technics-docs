#!/usr/bin/env python3
"""Re-derive the claim on /wsa1-parameters/ that CPU 1's parameter records ARE a
combination record laid out in RAM.

QUESTION THIS ANSWERS
  Two facts are established separately in the SX-WSA1R disassembly:

    * prom_a's ParamNumber_RecordPtrs (0xFACDEA, 256 LE32) gives, for each
      parameter number, the CPU-1 work-RAM address of that number's record, or
      0xFFFFFFFF when it has none (header in wsa1/prom_a/wsa1_prom_a.s);
    * prom_c's preset bank (0xF80300 + 704*n, 129 records) is the factory
      COMBINATION memory, a chain of {tag, length, payload} chunks whose tags
      are parameter-record numbers, and prom_a sub_F98927 copies one 0x2C0-byte
      record to CPU-1 RAM 0x7620 (banner of
      wsa1/prom_c/data_tables/preset_bank.s, asserted by
      notes/lanes/promcd-2026-09-25/preset_bank_readers.py).

  If both are right, every chunk's payload, once the record sits at 0x7620,
  must land exactly on ParamNumber_RecordPtrs[tag].  This script checks that,
  for every chunk, and that all 129 records share one chunk layout.

WHAT COUNTS AS PASS
  * all 129 preset-bank records walk to the same (tag, length) sequence and end
    on the 0xFF terminator at +0x2BE;
  * for every chunk, 0x7620 + payload offset == ParamNumber_RecordPtrs[tag];
  * the tags cover part blocks 0x00-0x07 / 0x20-0x27 and nothing else in 0x00-0x3F.
  Exits non-zero otherwise.  Prints only derived numbers, never ROM content.

  A NEGATIVE CONTROL runs too: the same comparison with the RAM base shifted by
  +-2 must match nothing, so a PASS cannot come from a base that fits anything.

⚠ ROM IMAGES NEVER LEAVE THIS MACHINE.  Do not extend this to dump ROM contents.

USAGE
  python3 tools/wsa1_param_record_layout_check.py [--roms DIR]

  DIR defaults to ../kn5000-roms-disasm/wsa1/original_ROMs relative to this
  repository (the disassembly repository's own copy of the four images).
"""
import argparse
import os
import struct
import sys

PROM_A = ("wsa1_prom_a.ic12", 0xF80000)
PROM_C = ("wsa1_prom_c.ic28", 0xF80000)
RECORD_PTRS = 0xFACDEA          # prom_a ParamNumber_RecordPtrs
BANK_RECORDS = 0xF80300         # prom_c first combination record
RECORD_SIZE = 0x2C0             # 704, the readers' stride
RECORD_COUNT = 129
RAM_BASE = 0x7620               # where sub_F98927 copies one record


def walk(rom, base, addr):
    """-> list of (tag, length, payload offset) and the terminator offset."""
    o = addr - base
    off, out = 0, []
    while off < RECORD_SIZE:
        tag, ln = rom[o + off], rom[o + off + 1]
        if tag == 0xFF:
            return out, off
        out.append((tag, ln, off + 2))
        off += 2 + ln
    return out, None


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument("--roms", default=os.path.join(
        here, os.pardir, "kn5000-roms-disasm", "wsa1", "original_ROMs"))
    args = ap.parse_args()
    roms = {}
    for name, base in (PROM_A, PROM_C):
        p = os.path.join(args.roms, name)
        if not os.path.isfile(p):
            print("FAIL: %s not found (pass --roms DIR)" % p)
            return 1
        roms[name] = (open(p, "rb").read(), base)
    a, abase = roms[PROM_A[0]]
    c, cbase = roms[PROM_C[0]]
    ptrs = struct.unpack_from("<256I", a, RECORD_PTRS - abase)
    fails = 0

    layouts = set()
    for n in range(RECORD_COUNT):
        chunks, end = walk(c, cbase, BANK_RECORDS + RECORD_SIZE * n)
        layouts.add((tuple((t, l) for t, l, _ in chunks), end))
    if len(layouts) != 1:
        print("FAIL: %d distinct chunk layouts over %d records" % (len(layouts), RECORD_COUNT))
        fails += 1
    chunks, end = walk(c, cbase, BANK_RECORDS)
    print("preset bank: %d records, one layout of %d chunks, terminator at +0x%X"
          % (RECORD_COUNT, len(chunks), end))
    if end != 0x2BE:
        print("FAIL: terminator not at +0x2BE")
        fails += 1

    hit = 0
    for tag, ln, poff in chunks:
        ram = RAM_BASE + poff
        ok = ptrs[tag] == ram
        hit += ok
        print("  tag 0x%02X  len %3d  payload -> RAM 0x%04X   ParamNumber_RecordPtrs[0x%02X] = 0x%04X  %s"
              % (tag, ln, ram, tag, ptrs[tag] & 0xFFFF if ptrs[tag] != 0xFFFFFFFF else 0xFFFF,
                 "match" if ok else "MISMATCH"))
    print("matches: %d of %d chunks" % (hit, len(chunks)))
    if hit != len(chunks):
        fails += 1

    parts = sorted(t for t, _, _ in chunks if t < 0x40)
    want = sorted(list(range(0x00, 0x08)) + list(range(0x20, 0x28)))
    if parts != want:
        print("FAIL: part tags %s" % [hex(t) for t in parts])
        fails += 1

    for d in (-2, +2):
        ctl = sum(1 for t, _, poff in chunks if ptrs[t] == RAM_BASE + d + poff)
        print("control: RAM base 0x%04X matches %d of %d" % (RAM_BASE + d, ctl, len(chunks)))
        if ctl:
            fails += 1

    print("PASS" if not fails else "FAIL (%d)" % fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
