#!/usr/bin/env python3
"""Split the data census's research-target bytes per image, and list the largest
merged research-target ranges of chosen images -- the per-image research figures
on /rom-reconstruction/ and the "largest research targets" list on
/wsa1-disassembly/.

QUESTION THIS ANSWERS
  data_range_census.py prints one research-target total for all twelve images.
  How is it distributed per image, and which ranges of a given image are the
  largest?  A research target is what the census's own is_target() says:
  grade UNKNOWN, or a self-admitted gap, or embedded-in-code; contiguous targets
  from the same source file are merged into one range, as its RESEARCH TARGETS
  block does.  The per-image sums must add up to the census's printed total;
  this script prints both so the reader can see they do.

INPUT
  the JSON written by the disassembly repository's census:
      python3 scripts/analysis/data_range_census.py --json OUT.json

USAGE
  python3 tools/census_research_by_image.py OUT.json [--ranges prom_a,prom_b --top 25]
"""
import argparse
import json

BASES = {"prom_a": 0xF80000, "prom_b": 0xF00000, "prom_c": 0xF80000, "prom_d": 0}


def is_target(r):
    return r["grade"] == "UNKNOWN" or r.get("admits") or r.get("embedded_in_code")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json")
    ap.add_argument("--ranges", default="")
    ap.add_argument("--top", type=int, default=25)
    a = ap.parse_args()
    recs = json.load(open(a.json))["regions"]
    per = {}
    for r in recs:
        if is_target(r):
            per[r["image"]] = per.get(r["image"], 0) + r["size"]
    for k, v in per.items():
        print("%-11s %9d" % (k, v))
    print("%-11s %9d" % ("TOTAL", sum(per.values())))
    want = [x for x in a.ranges.split(",") if x]
    if not want:
        return
    merged = []
    for img in want:
        rs = sorted((r for r in recs if r["image"] == img and is_target(r)), key=lambda r: r["lo"])
        cur = None
        for r in rs:
            if cur and r["lo"] == cur["hi"] and r["rel"] == cur["rel"]:
                cur["hi"] = r["hi"]
                cur["labels"].append(r["label"] or "-")
            else:
                if cur:
                    merged.append(cur)
                cur = dict(image=img, lo=r["lo"], hi=r["hi"], rel=r["rel"], labels=[r["label"] or "-"])
        if cur:
            merged.append(cur)
    merged.sort(key=lambda m: -(m["hi"] - m["lo"]))
    for m in merged[:a.top]:
        base = BASES.get(m["image"], 0)
        print("%-7s 0x%06X-0x%06X %6d  %s .. %s  %s" % (
            m["image"], m["lo"] + base, m["hi"] + base, m["hi"] - m["lo"],
            m["labels"][0], m["labels"][-1], m["rel"]))


if __name__ == "__main__":
    main()
