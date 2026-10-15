# Cross-model probes for the MN10300 Technics firmwares (round-2 review, lane other-models)

Written 2026-10-15 while re-checking `kn6000-roadmap.md` and `kn2400-kn2600.md` on the
technics-docs site. Every script reads the even/odd program ROM halves that MAME's
`src/mame/matsushita/kn7000.cpp` declares (CRC32s are the upstream ones: kn7000 v16 build 941
even `529b87ce`, kn6000 even `56c2cfe3`, kn6500 even `f42a2fcf`, kn2400 even `b94fc8a8`),
weaves them as `ROM_LOAD32_WORD` does, and prints counts only. `ROMDIR` holds one
subdirectory per machine (`ROMDIR/kn7000/kn7000_program_even.rom`, ...). Nothing is written
except to stdout.

Committed in kn5000-docs `tools/cross_model_probes/`; the site pages cite this path. The ROM
images are not in this repository.

| script              | question it answers                                                                                                                         | command                                                        |
|---------------------|---------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------|
| `string_share.py`   | What share of one firmware's distinct >=8-char printable-ASCII strings occurs verbatim in another's? Also re-runs the KN6000 low-2-MB case  | `python3 string_share.py ROMDIR`                               |
| `code_windows.py`   | What share of the KN2400's aligned 16-byte windows (>= N distinct byte values, < 12 printable) occurs anywhere in the KN7000 / KN6000 image | `python3 code_windows.py ROMDIR 6`                             |
| `crt0_compare.py`   | Where does each reset `jmp` land, and is the KN2400 crt0 byte-identical to the KN7000's apart from the stack address?                       | `python3 crt0_compare.py ROMDIR 0x80`                          |
| `names_offsets.py`  | Do the IK2/IKV2 offsets quoted on kn6000-names.md hold the strings the page names?                                                          | `python3 names_offsets.py ROMDIR`                              |
| `rhythm_records.py` | Layout of the KN6000 72-byte rhythm-genre records at IK2 `0x0580f8`                                                                         | `python3 rhythm_records.py ROMDIR`                             |
| `inf_check.py`      | Does a woven program image match the `SMCK*.INF` oracle shipped on its update disk (32-bit total + 16-bit sum per 0x40000 block)?           | `python3 inf_check.py ROMDIR SRCDIR kn2400 3965D3 SMCKPR1.INF` |

## Results (2026-10-15), and what they mean

`string_share.py` (the signal: set intersection of `re.findall(rb'[\x20-\x7e]{8,}')`):

    kn2400 in kn7000: 11499/15444 = 74.5 %
    kn2400 in kn6000:  9077/15444 = 58.8 %
    kn6000 in kn7000: 11137/16503 = 67.5 %
    kn6000 low 2 MB (IK1 only) distinct 5234
    kn6000-IK1-only in kn7000: 4479/5234 = 85.6 %
    kn2400 in kn6000-IK1-only: 3717/15444 = 24.1 %

The site's "4,479 of the KN6000's 5,234" (~85 %) is reproduced EXACTLY by the low 2 MB
(IK1.SLD) alone: it was measured on 2026-07-07 (site commit bf90e4a), before kn7000_mame
bfe6522 (same day, 23:13) found the upper half (IK2.SLD) had been left out of the image.
The KN2400 page's KN6000 column (23.6 %, 3587/15220) has the same cause.

`code_windows.py` with MINDISTINCT 4 / 6 / 8: KN2400->KN7000 31.2 / 29.3 / 28.6 %,
->KN6000 (full) 19.5 / 17.8 / 16.8 %, ->KN6000 IK1 only 12.7 / 12.3 / 12.7 %. The page's
11.0 % for the KN6000 fits the IK1-only case; its 38.9 % for the KN7000 is not reproduced by
any of these definitions (the original producer was never committed).

`names_offsets.py` / grep: the `MILK MN10300 Ver1.0R1` banner IS in the KN6000 image at
program offset 0x3F77E8 (IK2 half), so "absent in KN6000" is the same half-image artefact.

`crt0_compare.py`: kn7000 reset `jmp` -> 0x4840FF7E (bytes `dc 7e ff 00 00`), kn2400 ->
0x48705BDF, kn6000 -> 0x484002E3; 0x80 bytes compared, the only differing bytes are +0x7D..0x7F
(the stack address). kn7000_mame 142655e ("the KN7000 reset vector is jmp 0x48407EFF") is wrong:
it read the displacement as `ff 7e`, but the image holds `7e ff`.

`inf_check.py`: kn2400 15/15 blocks, kn6000 16/16, kn6500 15/15 — all match their oracles.

`crt0_compare.py ROMDIR 0x100`: 117 of 256 bytes differ; the first divergence after the stack
constant is at +0x86, the kernel-init call (`dd ... call 0x484d7111` in the KN7000, `cd ...
call 0x48704f8a` in the KN2400). So "identical apart from the stack address" holds for the
first 0x86 bytes, up to that call; after it the same instructions follow, but shifted.

The KN2400 page's example of relocated identical code, KN2400 0x48420000 == KN7000 0x485BBFB0,
is 1,028 identical bytes of a table of 4-byte records (`08 0b 0c 11 06 09 0c 0e ...`), not
code: unidasm decodes it as a run of `clr`/`movhu dN,(abs16)`, which no compiler emits.
