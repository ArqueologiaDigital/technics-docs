#!/usr/bin/env python3
"""How many of the SX-WSA1R prom_a "NO SPELLING" sites does llvm-mc actually spell?

QUESTION IT ANSWERS
    kn5000-roms-disasm's wsa1/notes/sound/wsa1_unspellable_forms.py reports, at
    3417969c0, "82 certified sites ... 81 with NO SPELLING".  For the shift-by-A
    forms (`sla A,r`, `sra A,r`, `sll A,r`, `srl A,r`; bytes `<prefix> fc..ff`) it
    only tries the unidasm rendering (`srl a,c`), which llvm-mc rejects.  The
    TLCS-900 backend spells those forms `slaa`/`sraa`/`slla`/`srla`
    (TLCS900InstrInfo.td, SLA_A_8/16/32 ... SRL_A_8/16/32).  This script takes
    the census's per-form output, tries that spelling for every shift-by-A form
    with the given llvm-mc, and counts the sites whose bytes come back exactly.

RUN
    (cd ../kn5000-roms-disasm/wsa1 && python3 notes/sound/wsa1_unspellable_forms.py --sites) > forms.txt
    python3 tools/wsa1_shift_by_a_spellings.py forms.txt ../llvm-project/build/bin/llvm-mc

    Measured 2026-10-15 at kn5000-roms-disasm 3417969c0 with llvm-mc sha256
    118bb4d6766e (tlcs900_backend a3a81863f87d):
        13 forms / 34 sites spelled byte-exact; 81 - 34 = 47 sites in 28 forms left.

SIGNAL
    "PASS" for a form means llvm-mc -show-encoding printed exactly the bytes the
    census quotes for that form.  Acceptance alone is never counted.
"""
import re
import subprocess
import sys

FORM_RE = re.compile(r"^\s+(\d+) x (\d+)B\s+(sla|sra|sll|srl) A,(\S+)\s+\[")
BYTES_RE = re.compile(r"^\s+((?:[0-9a-f]{2} ?)+)\s+★ NO SPELLING")


def encode(mc, text):
    p = subprocess.run([mc, "-triple=tlcs900", "-show-encoding"], input=text + "\n",
                       capture_output=True, text=True)
    m = re.search(r"encoding: \[([^\]]*)\]", p.stdout)
    if not m:
        return None
    return " ".join(b.strip()[2:] for b in m.group(1).split(","))


def main(forms_path, mc):
    lines = open(forms_path, encoding="utf-8").read().splitlines()
    forms = sites = 0
    for i, line in enumerate(lines):
        m = FORM_RE.match(line)
        if not m:
            continue
        n, _, op, reg = m.groups()
        # the byte line follows the form line (possibly after --sites lines)
        want = None
        for nxt in lines[i + 1:i + 40]:
            b = BYTES_RE.match(nxt)
            if b:
                want = b.group(1).strip()
                break
        spelling = f"{op}a {reg.lower()}"
        got = encode(mc, spelling)
        ok = want is not None and got == want
        print(f"{'PASS' if ok else 'FAIL'}  {n:>2} x  {op} A,{reg:<5} want [{want}]  "
              f"`{spelling}` -> [{got}]")
        if ok:
            forms += 1
            sites += int(n)
    print(f"{forms} shift-by-A form(s), {sites} site(s) spelled byte-exact")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
