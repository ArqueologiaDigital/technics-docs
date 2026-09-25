#!/usr/bin/env python3
"""Count SX-WSA1R prom_a's code-as-.byte sites at one disassembly revision,
once per assembler build -- the figures quoted on /wsa1-disassembly/,
/raw-byte-code-elimination/, /help-wanted/ and /rom-reconstruction/.

QUESTION THIS ANSWERS
  The disassembly repository's wsa1/notes/sound/wsa1_unspellable_forms.py
  prints two numbers for prom_a:
      "298 certified site(s), 1318 byte(s), 89 form(s)"
      "292 of those site(s) have NO SPELLING"
  The first depends only on the sources.  The second ALSO depends on the
  llvm-mc it runs -- "no spelling" means no route that script tries made that
  llvm-mc emit the ROM's bytes -- and the script always runs
  $PROJECTS_ROOT/llvm-project/build/bin/llvm-mc, the shared build, which moves.
  So the same revision gives different "no spelling" counts under different
  builds.  This script pins both: it exports <rev>'s wsa1/ and
  scripts/converters/ with `git archive` into a temporary directory (the
  repository is only read), and runs the census once per llvm-mc given,
  through a temporary PROJECTS_ROOT whose llvm-project/build/bin/llvm-mc is a
  symlink to that binary.  It prints each binary's sha256 beside its counts,
  because a commit hash alone does not name a build (the disassembly
  repository's TOOLCHAIN_VERSION explains why).

MEASURED 2026-09-25, rev be376096:
  llvm-mc a7ee33d53676 (da00420dba8d, the pin TOOLCHAIN_VERSION names)  298 / 298
  llvm-mc 9c0c0033a21f (6488ae7d)                                       298 / 298
  llvm-mc b211a23195df (910b50efab49)                                   298 / 292
  llvm-mc a67c563269fc (8e188b215251, the pin since bc571542)           298 / 282
  (certified / NO SPELLING).  And rev e5f6cea1 under a67c563269fc: 293 / 282,
  1,303 B, 84 forms -- 1485d941 had respelled the five post-increment /
  pre-decrement sites, leaving mul wa,(xiz-2) and tset 0,(0x2a1b76) spellable.
  The binaries were at
  ~/compartilhado/toolchain-snapshot/llvm-mc.snap.da00420dba8d-a7ee33d5 and
  ~/compartilhado/disasm-lanes/wave3a-scratch/llvm-mc.{L1-6488ae7d,
  L4-910b50efab49,L5-8e188b215251}; the last three are in scratch, so check
  the sha256 before trusting a re-run.

USAGE
  python3 tools/wsa1_unspelt_by_toolchain.py --disasm ~/compartilhado/kn5000-roms-disasm \\
      --rev be376096 --mc /path/to/llvm-mc [--mc /path/to/another-llvm-mc ...]
"""
import argparse
import hashlib
import os
import re
import subprocess
import tempfile

TOOLS = ("ld.lld", "llvm-objcopy", "llvm-nm", "llvm-objdump", "clang")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:12]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--disasm", required=True, help="the kn5000-roms-disasm checkout (read only)")
    ap.add_argument("--rev", required=True)
    ap.add_argument("--mc", action="append", required=True, help="an llvm-mc binary; repeatable")
    ap.add_argument("--shared-bin", default=os.path.expanduser(
        "~/compartilhado/llvm-project/build/bin"),
        help="where the non-llvm-mc tools are taken from")
    a = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix="wsa1-unspelt-") as tmp:
        tree = os.path.join(tmp, "tree")
        os.mkdir(tree)
        arc = subprocess.run(["git", "-C", a.disasm, "archive", a.rev, "wsa1", "scripts/converters"],
                             check=True, capture_output=True).stdout
        subprocess.run(["tar", "-x", "-C", tree], input=arc, check=True)
        for mc in a.mc:
            proj = os.path.join(tmp, "proj-" + sha(mc))
            bindir = os.path.join(proj, "llvm-project", "build", "bin")
            os.makedirs(bindir, exist_ok=True)
            os.symlink(os.path.abspath(mc), os.path.join(bindir, "llvm-mc"))
            for t in TOOLS:
                src = os.path.join(a.shared_bin, t)
                if os.path.exists(src):
                    os.symlink(src, os.path.join(bindir, t))
            env = dict(os.environ, PROJECTS_ROOT=proj, PYTHONDONTWRITEBYTECODE="1")
            out = subprocess.run(["python3", "notes/sound/wsa1_unspellable_forms.py"],
                                 cwd=os.path.join(tree, "wsa1"), env=env,
                                 capture_output=True, text=True).stdout
            sect = out.split("=== prom_a ===", 1)[1].split("=== prom_b ===", 1)[0]
            cert = re.search(r"(\d+) certified site\(s\), (\d+) byte\(s\), (\d+) form\(s\)", sect)
            nosp = re.search(r"(\d+) of those site\(s\) have NO SPELLING", sect)
            spellable = re.findall(r"spellable: (.*)", sect)
            print("rev %s  llvm-mc sha256 %s  (%s)" % (a.rev, sha(mc), mc))
            print("  prom_a: %s certified sites, %s B, %s forms; %s with NO SPELLING"
                  % (cert.group(1), cert.group(2), cert.group(3), nosp.group(1)))
            for s in spellable:
                print("    spellable form: " + s)


if __name__ == "__main__":
    main()
