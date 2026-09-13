#!/usr/bin/env python3
"""test_hle_permanence.py -- PROVE that removing MAME cannot remove the HLE reference from the docs.

WHY THIS EXISTS
    The project's standing instruction is explicit: *"I want to make sure we never remove the HLE
    reference code from the documentation pages, even though we'll eventually remove them from
    MAME sources."*  `gen_effect_impl_pages.py` implements that -- when the MAME source is absent
    it falls back to the ```cpp blocks already committed in each page.  But an untested guarantee
    is a claim, not a guarantee, and the day it matters is the day the source is deleted, which is
    exactly the day nobody will notice a silent regression.

    So this exercises the failure it promises to survive:

      1. copy the committed pages into a scratch directory;
      2. run the generator against a MAME path that DOES NOT EXIST;
      3. assert every ```cpp block in every page comes back BYTE-IDENTICAL.

    A generator change that breaks the fallback fails here instead of on the day of the removal.

USAGE
    python3 tools/test_hle_permanence.py          # exit 0 = the HLE reference is permanent
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent
PAGES = DOCS / "effect-impl"
GEN = HERE / "gen_effect_impl_pages.py"
CPP = re.compile(r"```cpp\n(.*?)\n```", re.DOTALL)


def blocks(d):
    out = {}
    for p in sorted(d.glob("*.md")):
        out[p.name] = CPP.findall(p.read_text())
    return out


def main():
    if not PAGES.is_dir():
        print("FAIL: %s does not exist -- the committed pages ARE the archive" % PAGES)
        return 1
    before = blocks(PAGES)
    n_pages = len(before)
    n_blocks = sum(len(v) for v in before.values())
    if n_blocks == 0:
        print("FAIL: the committed pages carry NO ```cpp blocks -- there is no HLE reference to preserve")
        return 1

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "effect-impl"
        shutil.copytree(PAGES, out)
        missing = Path(td) / "no-such-mame-tree"      # the removal this must survive
        r = subprocess.run([sys.executable, str(GEN), "--mame", str(missing), "--out", str(out)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print("FAIL: the generator EXITED %d with MAME absent -- it must not fail, it must fall back"
                  % r.returncode)
            print(r.stdout[-2000:]); print(r.stderr[-2000:])
            return 1
        after = blocks(out)

    bad = []
    for name, bs in before.items():
        if name not in after:
            bad.append("%s: page DISAPPEARED" % name)
        elif after[name] != bs:
            bad.append("%s: %d block(s) before, %d after, and they DIFFER"
                       % (name, len(bs), len(after[name])))
    if bad:
        print("FAIL: the HLE reference did NOT survive the removal of the MAME source:")
        for b in bad:
            print("   " + b)
        return 1

    print("PASS: %d pages, %d ```cpp blocks -- every one byte-identical with the MAME source absent."
          % (n_pages, n_blocks))
    print("      The HLE reference in the documentation is PERMANENT, and this test says so on"
          " every run rather than on the day of the removal.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
