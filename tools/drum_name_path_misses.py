#!/usr/bin/env python3
"""drum_name_path_misses.py -- how do the 92 drum-kit notes whose two name paths disagree differ?

QUESTION ANSWERED
  tone-database.md ("Drum kits and percussion") says the instrument path
  (DrumKit_NoteMapA -> PercInst, 13-char names) and the independent name path
  (DrumKit_NoteMapB -> PercName_Pack, 10-char names) agree on 3,236 of the
  3,328 kit notes.  That figure comes from the disassembly repo's probe
  notes/tonedb-2026-09-25/drum_chain_probe.py, which prints only the first 12
  of the 92 misses.  This script walks the same 26 kits x 128 notes with the
  probe's own ROM readers and match test, and sorts every miss into the
  groups the page quotes:

    numbering     the names agree once digits are dropped ("Scratch 3" / "Scratch 2")
    abbreviation  the same instrument abbreviated differently ("SambaWhistleL" / "SambaWhiLo")
    different     "Zap 1" / "High Q"
    hat pedal     "DanceHHPedal" / "HatPedal 5"

  "numbering" is decided mechanically (the probe's subsequence test passes
  after digits are removed from both names).  The last two groups are the
  pairs listed in OUTRIGHT below; every other miss is "abbreviation".  Those
  group names are a reading of the text, not something the ROM states.

  Expected output (2026-09-25, original_ROMs/kn5000_table_data.rom):
    misses 92: numbering 37, abbreviation 37, different 16, hat pedal 2

  Reads kn5000-roms-disasm; writes nothing.

RUN
  python3 tools/drum_name_path_misses.py --repo ../kn5000-roms-disasm
"""
import argparse
import collections
import pathlib
import re
import sys

OUTRIGHT = {
    ("Zap 1", "High Q"): "different",
    ("DanceHHPedal", "HatPedal 5"): "hat pedal",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="../kn5000-roms-disasm")
    repo = pathlib.Path(ap.parse_args().repo).resolve()
    sys.dont_write_bytecode = True  # leave no __pycache__ behind in the disassembly repo
    sys.path.insert(0, str(repo / "notes" / "tonedb-2026-09-25"))
    import drum_chain_probe as P  # the probe's ROM readers, kit list and match test

    rom, B = P.ROM, P.B
    nmA, pi, nmB, pn = P.dslot(0x74), P.dslot(0x78), P.dslot(0x7C), P.dslot(0xB0)
    st = P.u16(P.DB + 0xEE)
    pname = lambda k: rom[pi + st * k - B:pi + st * k - B + 13].decode("latin-1").rstrip()
    bname = lambda k: rom[pn + 10 * k - B:pn + 10 * k - B + 10].decode("latin-1").rstrip()
    nodigits = lambda s: re.sub(r"[0-9]", "", P.norm(s))

    groups = collections.Counter()
    pairs = collections.Counter()
    total = 0
    for k in range(26):
        a = 0x863079 + 295 * k
        for n in range(128):
            lo, hi = P.u8(a + 0x27 + 2 * n), P.u8(a + 0x28 + 2 * n)
            idx = ((hi & 0x1F) << 7) | lo
            inst, pack = pname(P.u16(nmA + 2 * idx)), bname(P.u16(nmB + 2 * idx))
            total += 1
            if P.subseq(P.norm(pack), P.norm(inst)):
                continue
            if (inst, pack) in OUTRIGHT:
                g = OUTRIGHT[(inst, pack)]
            elif P.subseq(nodigits(pack), nodigits(inst)):
                g = "numbering"
            else:
                g = "abbreviation"
            groups[g] += 1
            pairs[(g, inst, pack)] += 1

    for (g, inst, pack), c in sorted(pairs.items(), key=lambda t: (t[0][0], -t[1])):
        print("  %-12s %3d  %-15r %r" % (g, c, inst, pack))
    miss = sum(groups.values())
    print("kit notes %d, agree %d, misses %d: numbering %d, abbreviation %d, different %d, hat pedal %d"
          % (total, total - miss, miss, groups["numbering"], groups["abbreviation"],
             groups["different"], groups["hat pedal"]))


if __name__ == "__main__":
    main()
