#!/usr/bin/env python3
"""check_doc_paths.py -- do the file paths cited by the docs still exist?

QUESTION ANSWERED
  Documentation cannot be run, so it rots silently.  But one part of it IS
  mechanically checkable: every `backticked/path.ext` a page cites either
  resolves in the source repos or it does not.  This checks all of them.

  It found 33 dead paths out of 182 on source-map.md alone, in four
  different ways: files renamed, files moved, files converted from assembly
  to C (so both path and extension were wrong), and one file whose IDENTITY
  had been corrected upstream -- audio_cmd_encoder.s became sprintf_core.s
  once the routines were shown to be a general string formatter.

  ⚠ WHAT A GREEN RUN DOES NOT MEAN.  This checks EXISTENCE, not accuracy.
  A page can cite a path that resolves perfectly and say something false
  about what is inside it -- the sprintf case was exactly that for a while,
  described as an "audio command encoder" while the path still resolved.
  A clean run here narrows where to look; it never certifies a page.

  Only git-TRACKED files count, so a page that names a BUILD ARTEFACT
  (`apploader.bin`, `mines_disk.bin`) or a ROM-DUMP filename (`*.rom`, `*.ic*`)
  is reported dead and always will be -- no dump is committed to either repo.
  Those are expected; do not "fix" them by deleting the filename.

  Resolution is deliberately generous: a path resolves if it exists
  relative to a repo root OR if its basename exists anywhere in the repo.
  That undercounts rot (a file moved between directories still "resolves"),
  which is the safe direction for a tool meant to produce leads.

RUN
    python3 tools/check_doc_paths.py                # every page
    python3 tools/check_doc_paths.py source-map.md  # one page
    python3 tools/check_doc_paths.py --selftest

SELFTEST asserts the ABSENT DEFECT: that a path known not to exist is
actually reported.  A checker that cannot go red is not evidence.
"""
import os, re, subprocess, sys

DOCS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPOS = [DOCS,   # the pages cite this repository's own tools/ scripts
         os.path.expanduser("~/compartilhado/kn5000-roms-disasm"),
         os.path.expanduser("~/compartilhado/kn7000_mame"),
         # Homebrew trees the tutorials cite: the App Loader extension ROM and
         # the Mines port built against it.  Without these, every path on
         # app-loader.md reads as dead when the files are simply in another repo.
         os.path.expanduser("~/compartilhado/custom-kn5000-roms"),
         os.path.expanduser("~/compartilhado/Mines")]
PATH_RE = re.compile(r'`([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:s|py|c|h|cpp|inc|json|rom|bin|ld))`')

def index(repo):
    """basename -> True, for every tracked file in the repo."""
    try:
        out = subprocess.run(["git", "-C", repo, "ls-files"], capture_output=True,
                             text=True, timeout=120).stdout
    except Exception:
        return set(), set()
    full = set(out.split())
    return full, {os.path.basename(f) for f in full}

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    selftest = "--selftest" in sys.argv
    idx = [(r, *index(r)) for r in REPOS if os.path.isdir(r)]
    if not idx:
        sys.exit("no source repos found -- nothing could be checked (refusing to report a vacuous pass)")

    def resolves(p):
        return any(p in full or os.path.basename(p) in bases for _, full, bases in idx)

    if selftest:
        bad = "definitely_not_a_real_file_xyzzy.s"
        assert not resolves(bad), "selftest FAILED: checker cannot detect a missing path"
        anyreal = next(iter(idx[0][2]))
        assert resolves(anyreal), "selftest FAILED: checker rejects a path that exists"
        print("selftest: 2 checks, 0 failures (it can go red, and it does not cry wolf)")
        return

    pages = args or sorted(f for f in os.listdir(DOCS) if f.endswith(".md"))
    total = dead = 0
    for page in pages:
        try:
            text = open(os.path.join(DOCS, page)).read()
        except OSError:
            continue
        cited = sorted(set(PATH_RE.findall(text)))
        missing = [p for p in cited if not resolves(p)]
        total += len(cited); dead += len(missing)
        if missing:
            print(f"{page}: {len(missing)} dead of {len(cited)} cited")
            for m in missing:
                print(f"    {m}")
    print(f"\n{dead} dead paths out of {total} cited, across {len(pages)} page(s)")

main()
