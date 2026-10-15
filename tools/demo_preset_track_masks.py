#!/usr/bin/env python3
"""demo_preset_track_masks.py -- what is in each demo preset's +0x1E track-enable mask?

QUESTION ANSWERED
  ssf-presentation.md once built sections on the demo presets' +0x1E word being
  0x0000.  It is not: the 16-bit track-enable mask at +0x1E of the decompressed
  preset is non-zero in all 19 demo presets.  This prints, per preset, its
  decompressed size and that mask, so the claim is a measurement.

HOW IT READS
  kn5000-roms-disasm keeps each demo preset's decompressed image as a YAML
  sidecar (table_data/includes/demo_presets/sidecar/demo_preset_NN.yaml): a
  `size:` field and the image as base64 in a `- [0, "..."]` chunk at offset 0.
  The mask is the little-endian u16 at offset 0x1E of that image.  Read-only.

RUN
    python3 tools/demo_preset_track_masks.py                     # ../kn5000-roms-disasm
    python3 tools/demo_preset_track_masks.py --repo /path/to/kn5000-roms-disasm
"""

import argparse
import base64
import glob
import os
import re
import struct


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--repo", default=os.path.join(here, "..", "kn5000-roms-disasm"))
    args = ap.parse_args()
    sidecars = os.path.join(os.path.abspath(args.repo), "table_data", "includes",
                            "demo_presets", "sidecar")
    nonzero = 0
    paths = sorted(glob.glob(os.path.join(sidecars, "demo_preset_*.yaml")))
    for path in paths:
        with open(path, encoding="utf-8") as f:
            text = f.read()
        image = base64.b64decode(re.search(r'-\s*\[0,\s*"([^"]+)"\]', text).group(1))
        size = int(re.search(r"^size:\s*(\d+)", text, re.M).group(1))
        mask = struct.unpack_from("<H", image, 0x1E)[0]
        nonzero += mask != 0
        print(f"{os.path.basename(path)}  size {size:6,}  +0x1E mask 0x{mask:04X}")
    print(f"presets: {len(paths)}; non-zero mask: {nonzero}")


if __name__ == "__main__":
    main()
