#!/usr/bin/env python3
"""Re-derive the claim that the tone databases' name index maps are exact inverses
of their wave catalogues -- on the SX-WSA1R (prom_d) AND on the KN5000 (table data).

QUESTION THIS ANSWERS
  Each tone database carries 16-byte wave-catalogue rows whose bytes +14/+15 are a
  selector pair (program, bank-family), and 1024-entry LE16 "name" index maps.
  On the SX-WSA1R, prom_c's readers form
        i = (bank & 0x0F) * 128 + (program & 0x7F)
  and pick the map by the family bits 7:6 (disassembly repository,
  notes/lanes/promcd-2026-09-25/prom_d_index_maps.py, which proves that on prom_d
  only).  The Wave 2 lane report states that the same inverse property holds on
  the KN5000 but commits no check for that half; this script is that check, and
  it re-runs the prom_d half with the same code so both are measured one way.

  For every row r of a catalogue: look its own selector up in the family's name
  map; PASS requires the map to return r for EVERY row.

  CONTROL: the same rows through the map of the OTHER catalogue pair must NOT
  reproduce the rows -- fewer than a quarter of them (a "match everything"
  artefact would pass both).  The percussion maps share their first entries, so
  their control lands on a few coincident low rows (16 of 141..208), not zero.

DIRECTORY LAYOUT USED (identical on both machines; slot values are offsets from
the directory base)
  catalogue +0x50 via maps +0x44 (family 0x00/0xC0) / +0x48 (family 0x80)
  catalogue +0x64 via maps +0x58 / +0x5C
  catalogue +0x8C via map  +0x4C (family 0x40)
  catalogue +0x94 via map  +0x60 (family 0x40)
  directory base: prom_d file offset 0; KN5000 table data 0x830000.
  Row counts: prom_d 307 / 314 / 208 / 161; KN5000 333 / 339 / 141 / 144 (the
  counts tone-database.md and the prom_d banners give).

USAGE
  python3 tools/tone_db_index_map_inverse_check.py [--disasm DIR]
  DIR defaults to ../kn5000-roms-disasm relative to this repository.  Prints only
  counts, never ROM content.  Exit 0 on PASS.
"""
import argparse
import os
import struct
import sys

CATS = [  # (catalogue slot, {family: map slot})
    (0x50, {0x00: 0x44, 0xC0: 0x44, 0x80: 0x48}),
    (0x64, {0x00: 0x58, 0xC0: 0x58, 0x80: 0x5C}),
    (0x8C, {0x40: 0x4C}),
    (0x94, {0x40: 0x60}),
]
CONTROL = {0x44: 0x58, 0x48: 0x5C, 0x58: 0x44, 0x5C: 0x48, 0x4C: 0x60, 0x60: 0x4C}
IMAGES = [
    ("SX-WSA1R prom_d", "wsa1/original_ROMs/wsa1_prom_d.bin", 0x000000, [307, 314, 208, 161]),
    ("KN5000 table data", "original_ROMs/kn5000_table_data.rom", 0x030000, [333, 339, 141, 144]),
]


def slot(img, base, s):
    return base + struct.unpack_from("<I", img, base + s)[0]


def count(img, base, cat, maps, n, swap=False):
    rows = slot(img, base, cat)
    hit = 0
    for r in range(n):
        prog, bank = img[rows + 16 * r + 14], img[rows + 16 * r + 15]
        m = maps.get(bank & 0xC0)
        if m is None:
            return None
        if swap:
            m = CONTROL[m]
        i = (bank & 0x0F) * 128 + (prog & 0x7F)
        hit += struct.unpack_from("<H", img, slot(img, base, m) + 2 * i)[0] == r
    return hit


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser()
    ap.add_argument("--disasm", default=os.path.join(here, os.pardir, "kn5000-roms-disasm"))
    a = ap.parse_args()
    fails = 0
    for name, rel, base, counts in IMAGES:
        path = os.path.join(a.disasm, rel)
        if not os.path.isfile(path):
            print("FAIL: %s not found (pass --disasm DIR)" % path)
            return 1
        img = open(path, "rb").read()
        print(name)
        for (cat, maps), n in zip(CATS, counts):
            hit = count(img, base, cat, maps, n)
            ctl = count(img, base, cat, maps, n, swap=True)
            ok = hit == n and ctl is not None and ctl < n // 4
            fails += not ok
            print("  catalogue +0x%02X  %3d rows  inverse %3d/%d   control (other map) %3d   %s"
                  % (cat, n, hit or 0, n, ctl or 0, "ok" if ok else "FAIL"))
    print("PASS" if not fails else "FAIL (%d)" % fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
