#!/usr/bin/env python3
"""source_map_counts.py -- the file counts on source-map.md, measured, not remembered.

QUESTION ANSWERED
  How many source files does each part of the disassembly tree hold right
  now?  source-map.md quotes per-directory counts; this prints them, so the
  page states a measured number instead of a remembered one.

HOW IT COUNTS
  Literally `find <dir> -name '*.<ext>' | wc -l`, one subprocess per cell, so
  the page's claim ("measured with find | wc -l") is exactly what runs here.
  `find` counts what is on disk, tracked or not; a generated `.bin` never
  matches these extensions, so build products do not inflate the table, but
  an untracked stray `.s` would.  Compare against `git ls-files` if a number
  looks wrong.

  The SX-WSA1R total excludes `wsa1/notes/`, which holds a probe's `.s`
  image (`.image-wsa1_prom_c.s`) that is not part of any build.

READ-ONLY.  Writes nothing, builds nothing, touches no git state.

RUN
    python3 tools/source_map_counts.py
    python3 tools/source_map_counts.py --repo /path/to/kn5000-roms-disasm
    python3 tools/source_map_counts.py --selftest

SELFTEST builds a throwaway tree with known contents and asserts the counts
come back exactly, and that a directory that does not exist is reported as
missing rather than silently counted as zero.  A counter that cannot go red
is not evidence.
"""
import argparse
import os
import subprocess
import sys
import tempfile

DEFAULT_REPO = os.path.expanduser("~/compartilhado/kn5000-roms-disasm")

# (label, directory, extensions, extra find arguments)
ROWS = [
    ("KN5000 main CPU v10",      "v10/maincpu",        ("s", "c", "h", "ld"), ()),
    ("KN5000 main CPU v9",       "v9/maincpu",         ("s", "c", "h", "ld"), ()),
    ("KN5000 main CPU v7",       "v7/maincpu",         ("s", "c", "h", "ld"), ()),
    ("KN5000 sub-CPU payload",   "v142/subcpu",        ("s", "ld"), ()),
    ("KN5000 sub-CPU boot ROM",  "subcpu/boot",        ("s", "ld"), ()),
    ("HD-AE5000",                "hdae5000",           ("s", "ld"), ()),
    ("KN5000 table data",        "table_data",         ("s", "ld"), ()),
    ("KN5000 custom data",       "custom_data",        ("s", "ld"), ()),
    ("SX-WSA1R (all, excl. notes)", "wsa1",            ("s", "inc", "ld"),
                                                       ("-not", "-path", "*/notes/*")),
    ("SX-WSA1R prom_a",          "wsa1/prom_a",        ("s", "ld"), ()),
    ("SX-WSA1R prom_b",          "wsa1/prom_b",        ("s", "ld"), ()),
    ("SX-WSA1R prom_c",          "wsa1/prom_c",        ("s", "ld"), ()),
    ("SX-WSA1R prom_d",          "wsa1/prom_d",        ("s", "ld"), ()),
    ("SX-WSA1R kernel (shared)", "wsa1/kernel",        ("s", "inc"), ()),
    ("SX-WSA1R DSP driver (shared)", "wsa1/dsp",       ("s", "inc"), ()),
    ("SX-WSA1R include",         "wsa1/include",       ("inc",), ()),
    ("SX-WSA1R maincpu/shared",  "wsa1/maincpu",       ("s",), ()),
]

MAINCPU_SUBDIRS_EXTS = ("s", "c")


def find_count(repo, directory, ext, extra=()):
    """`find <dir> -name '*.<ext>' [extra] | wc -l`, or None if <dir> is absent."""
    path = os.path.join(repo, directory)
    if not os.path.isdir(path):
        return None
    cmd = ["find", path, "-name", f"*.{ext}", *extra]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    # wc -l on find's output: one path per line.
    return len(out.splitlines())


def head_commit(repo):
    try:
        return subprocess.run(["git", "-C", repo, "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "(not a git checkout)"


def report(repo):
    print(f"# kn5000-roms-disasm at {head_commit(repo)}  ({repo})")
    print()
    print("| Tree | Directory | `.s` | `.c` | `.h` | `.ld` | `.inc` |")
    print("|------|-----------|-----:|-----:|-----:|------:|-------:|")
    missing = []
    for label, directory, exts, extra in ROWS:
        cells = []
        for ext in ("s", "c", "h", "ld", "inc"):
            if ext in exts:
                n = find_count(repo, directory, ext, extra)
                if n is None:
                    missing.append(directory)
                    cells.append("MISSING")
                else:
                    cells.append(str(n))
            else:
                cells.append("—")
        print(f"| {label} | `{directory}/` | " + " | ".join(cells) + " |")
    print()
    print("## v10/maincpu by directory")
    print()
    print("| Directory | `.s` | `.c` | other |")
    print("|-----------|-----:|-----:|-------|")
    root = os.path.join(repo, "v10/maincpu")
    if os.path.isdir(root):
        root_s = len([f for f in os.listdir(root) if f.endswith(".s")])
        root_c = len([f for f in os.listdir(root) if f.endswith(".c")])
        print(f"| `v10/maincpu/` (top level only) | {root_s} | {root_c} | `maincpu.ld` |")
        for d in sorted(os.listdir(root)):
            p = os.path.join(root, d)
            if not os.path.isdir(p):
                continue
            s = find_count(repo, f"v10/maincpu/{d}", "s")
            c = find_count(repo, f"v10/maincpu/{d}", "c")
            h = find_count(repo, f"v10/maincpu/{d}", "h")
            ld = find_count(repo, f"v10/maincpu/{d}", "ld")
            other = ", ".join(x for x in (f"{h} `.h`" if h else "", f"{ld} `.ld`" if ld else "") if x)
            print(f"| `{d}/` | {s} | {c} | {other} |")
    else:
        missing.append("v10/maincpu")
    print()
    print("Each cell is `find <dir> -name '*.<ext>' | wc -l`; the SX-WSA1R total adds "
          "`-not -path '*/notes/*'`.")
    if missing:
        print(f"\nMISSING directories: {sorted(set(missing))}", file=sys.stderr)
        return 1
    return 0


def selftest():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "a/sub"))
        os.makedirs(os.path.join(tmp, "a/notes"))
        for name in ("a/x.s", "a/y.s", "a/sub/z.s", "a/sub/w.c", "a/notes/probe.s",
                     "a/data.bin"):
            open(os.path.join(tmp, name), "w").close()
        assert find_count(tmp, "a", "s") == 4, "counts .s recursively"
        assert find_count(tmp, "a", "c") == 1, "counts .c"
        assert find_count(tmp, "a", "ld") == 0, "absent extension is zero"
        assert find_count(tmp, "a", "s", ("-not", "-path", "*/notes/*")) == 3, \
            "the notes exclusion drops exactly the probe"
        assert find_count(tmp, "does/not/exist", "s") is None, \
            "a missing directory must be reported, not counted as zero"
    print("selftest: OK")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    return report(args.repo)


if __name__ == "__main__":
    sys.exit(main())
