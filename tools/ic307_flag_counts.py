#!/usr/bin/env python3
"""ic307_flag_counts.py -- are the flag counts on waveform-rom-format.md page 0 or chip-wide?

QUESTION ANSWERED
  waveform-rom-format.md's "Parameter Records" section says it describes page 0, and
  quotes 286 end-of-record pairs (flag bit 7), 258 bit-6 markers, 52 key-split values
  of 0x80, and a record-size histogram (1/31/25/44/45/46) with a largest record of 850
  bytes.  This prints each figure per page and for the whole chip, using the same record
  extents as kn7000_mame tools/kn5000-rom-structure/flagcensus.py (record = param_ptr up
  to the next strictly greater param_ptr, the last one up to the first PCM byte; pairs
  start after the redundant wave_offset word, little-endian {value, flag}).

  Prints counts only, never ROM bytes.  Run with python3 -I.

RUN
    python3 -I tools/ic307_flag_counts.py path/to/kn5000_waveform_rom.ic307
    (the dump is not in this repository)

Result 2026-10-15, whole chip: 7,203 pairs; bit 7 on 286 (284 on the record's last
pair); bit 6 on 258; split value 0x80 52 times (values above 0x7F 116 times).
"""
import sys
from collections import Counter

PAGE = 0x100000


def main():
    d = open(sys.argv[1], "rb").read()
    assert len(d) == 4 * PAGE
    u16 = lambda o: d[o] | d[o + 1] << 8
    tot = Counter()
    for p in range(4):
        b = p * PAGE
        n = u16(b) // 4
        idx = [(u16(b + 4 * i), u16(b + 4 * i + 2)) for i in range(n)]
        params = sorted(set(x[0] for x in idx))
        waves = sorted(set(x[1] for x in idx))
        c = Counter()
        sizes = Counter()
        maxsize = 0
        for pp, wo in idx:
            nx = [q for q in params if q > pp]
            end = nx[0] if nx else min(waves) * 16
            rec = d[b + pp:b + end]
            sizes[len(rec)] += 1
            maxsize = max(maxsize, len(rec))
            pairs = [(rec[j], rec[j + 1]) for j in range(2, len(rec) - 1, 2)]
            for v, f in pairs:
                c["pairs"] += 1
                if f & 0x80:
                    c["bit7"] += 1
                if f & 0x40:
                    c["bit6"] += 1
                if f == 0x00 and v == 0x80:
                    c["split_0x80"] += 1
                if f == 0x00 and v > 0x7F:
                    c["split_gt_7F"] += 1
            if pairs and pairs[-1][1] & 0x80:
                c["bit7_on_last"] += 1
        hist = {k: sizes[k] for k in (2, 4, 6, 8, 10)}
        hist["12+"] = sum(v for k, v in sizes.items() if k >= 12)
        print(f"page {p}: N {n}  pairs {c['pairs']}  bit7 {c['bit7']} (on last pair {c['bit7_on_last']})"
              f"  bit6 {c['bit6']}  split value 0x80 {c['split_0x80']} (>0x7F {c['split_gt_7F']})"
              f"  sizes {hist}  max {maxsize}")
        tot += c
    print(f"chip: pairs {tot['pairs']}  bit7 {tot['bit7']} (on last pair {tot['bit7_on_last']})"
          f"  bit6 {tot['bit6']}  split value 0x80 {tot['split_0x80']} (>0x7F {tot['split_gt_7F']})")


if __name__ == "__main__":
    main()
