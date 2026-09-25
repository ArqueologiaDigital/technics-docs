#!/usr/bin/env python3
"""hdae5000_fn_table_check.py -- are the HD-AE5000's RootFn_/HamaFn_ names the firmware's own?

QUESTION ANSWERED
  hdae5000-homebrew.md and hdae5000-filesystem.md say the HD-AE5000 reaches the
  main CPU through two function tables and that every offset it uses carries
  the name the main-CPU firmware itself files under that index: 99 functions
  at 953 call sites.  This re-derives every one of those rows from the v10
  program ROM and checks it against the current disassembly sources.

  The disassembly repo's scripts/converters/hdae5000_symbolize_fn_tables.py
  produced the RootFn_/HamaFn_ constants, but it can no longer be re-run as a
  check: it refuses when the literal line
    RegObjTablHama 0x1600001, FunctionProc, 0x4b, 0xe1f0ec, 0x109
  is missing from v10/maincpu/factory_test/test_init.s, and that line now
  reads `... HamaObj_109_Data, 0x109`; its call-site scan also looks for the
  numeric operands 0x0e0a / 0x0e88, which it itself replaced with
  WS_RootFnTable / WS_HamaFnTable.  This script starts from the constants
  instead.

WHAT IT DOES
  1. Checks the four registration lines it relies on are in the main-CPU
     sources (spelled as they are now):
       InitializeRoot  RegObjTabl ... 0x160, 0xeafa6e, 0x100            (functions)
                       RegObjTabl ... 0x160, WidgetName_InitPtrTable, 0x400 (names)
       InitializeHama  RegObjTablHama ... 0x4b, HamaObj_109_Data, 0x109    (functions)
                       RegObjTablHama ... 0x4b, Hama_ModeParam_Table, 0x409 (names)
     and resolves the three labels through the v10 ELF (llvm-nm).
  2. Reads every `.equ RootFn_<X>, off` / `.equ HamaFn_<X>, off` from
     hdae5000/hd-ae5000_v2_06i.s.
  3. For each: function pointer = u32 at (function table + off) and name =
     C string at u32(name table + off), both read from
     original_ROMs/kn5000_v10_program.rom.  PASS needs <X> == that name.  The
     v10 build's label at the function address is printed beside it (it may
     legitimately differ: the build names some of these routines itself).
  4. Counts operands `+ RootFn_*` / `+ HamaFn_*` in every hdae5000/*.s, read as
     bytes (several of those files hold non-UTF-8 bytes).

  Expected (2026-09-25): 99 constants (table 0x100: 41, table 0x109: 58),
  99/99 names match, the v10 build's label equals the firmware name for 99/99,
  953 call sites naming 99 distinct constants, PASS.  (The build-label count
  is reported, not required.)

RUN
  python3 tools/hdae5000_fn_table_check.py --repo ../kn5000-roms-disasm
  (needs rebuilt_ROMs/kn5000_v10_program.llvm.elf there: `make` builds it)
"""
import argparse
import collections
import os
import pathlib
import re
import struct
import subprocess
import sys

NM = os.path.expanduser("~/compartilhado/llvm-project/build/bin/llvm-nm")
REGISTRATIONS = [
    ("v10/maincpu/display/graphics_text_vga.s", "RegObjTabl 0x1600001, FunctionProc, 0x160, 0xeafa6e, 0x100"),
    ("v10/maincpu/display/graphics_text_vga.s",
     "RegObjTabl 0x1600001, FunctionProc, 0x160, WidgetName_InitPtrTable, 0x400"),
    ("v10/maincpu/factory_test/test_init.s",
     "RegObjTablHama 0x1600001, FunctionProc, 0x4b, HamaObj_109_Data, 0x109"),
    ("v10/maincpu/factory_test/test_init.s",
     "RegObjTablHama 0x1600001, FunctionProc, 0x4b, Hama_ModeParam_Table, 0x409"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="../kn5000-roms-disasm")
    repo = pathlib.Path(ap.parse_args().repo).resolve()
    fail = []

    for rel, text in REGISTRATIONS:
        if text.encode() not in (repo / rel).read_bytes():
            fail.append("registration line gone from %s: %r" % (rel, text))
    if fail:
        sys.exit("REFUSED: " + "; ".join(fail))

    out = subprocess.run([NM, "--defined-only", str(repo / "rebuilt_ROMs" / "kn5000_v10_program.llvm.elf")],
                         capture_output=True, text=True, check=True).stdout
    byname, lab = {}, {}
    for ln in out.splitlines():
        p = ln.split()
        if len(p) == 3:
            byname[p[2]] = int(p[0], 16)
            lab.setdefault(int(p[0], 16), p[2])
    tables = {  # prefix: (function table, name table)
        "RootFn_": (0xEAFA6E, byname["WidgetName_InitPtrTable"]),
        "HamaFn_": (byname["HamaObj_109_Data"], byname["Hama_ModeParam_Table"]),
    }

    rom = (repo / "original_ROMs" / "kn5000_v10_program.rom").read_bytes()
    u32 = lambda a: struct.unpack_from("<I", rom, a - 0xE00000)[0]

    def cstr(a):
        o = a - 0xE00000
        return rom[o:rom.index(b"\0", o)].decode("latin-1")

    src = (repo / "hdae5000" / "hd-ae5000_v2_06i.s").read_bytes()
    consts = [(m.group(1).decode(), m.group(2).decode(), int(m.group(3), 16)) for m in
              re.finditer(rb"^\s*\.equ\s+(RootFn_|HamaFn_)(\w+)\s*,\s*(0x[0-9a-fA-F]+)", src, re.M)]
    per = collections.Counter(pre for pre, _, _ in consts)
    ok = same_build = 0
    for pre, name, off in consts:
        ftab, ntab = tables[pre]
        fn, fw = u32(ftab + off), cstr(u32(ntab + off))
        good = fw == name
        ok += good
        if not good:
            fail.append("%s%s at +0x%03X: firmware name is %r" % (pre, name, off, fw))
        bl = lab.get(fn, "?")
        same_build += bl == fw
        print("  %s %s%-24s +0x%03X -> 0x%06X  firmware %-24s v10 build %s"
              % ("ok  " if good else "FAIL", pre, name, off, fn, fw, bl))

    uses = collections.Counter()
    for p in sorted((repo / "hdae5000").rglob("*.s")):
        for m in re.finditer(rb"\+\s*((?:RootFn|HamaFn)_\w+)", p.read_bytes()):
            uses[m.group(1).decode()] += 1
    defined = {pre + name for pre, name, _ in consts}
    if set(uses) - defined:
        fail.append("operands naming no constant: %s" % sorted(set(uses) - defined))

    print("constants %d (table 0x100: %d, table 0x109: %d); names matching the firmware's %d/%d; "
          "v10 build label equal to the firmware name %d/%d; call sites %d naming %d distinct constants"
          % (len(consts), per["RootFn_"], per["HamaFn_"], ok, len(consts), same_build, len(consts),
             sum(uses.values()), len(uses)))
    if fail:
        print("FAIL: " + "; ".join(fail))
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
