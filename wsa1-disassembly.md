---
layout: page
title: SX-WSA1 Disassembly
permalink: /wsa1-disassembly/
---

# SX-WSA1R — the byte-exact disassembly

All four of the [SX-WSA1]({{ site.baseurl }}/wsa1/)'s EPROM images — 2,097,152
bytes in total — are being converted to TLCS-900 assembly source that
**reassembles to the original bytes**. The project is the sibling of the
[KN5000 ROM reconstruction]({{ site.baseurl }}/rom-reconstruction/) and follows
the same practices, including the same
[LLVM TLCS-900 backend](https://github.com/felipesanches/llvm-project/tree/tlcs900_backend).
⚠ As of 2026-10-15 that public branch is behind the commit `TOOLCHAIN_VERSION` pins, and
the current sources use operand spellings its build cannot parse, so the published tree
cannot be rebuilt from public sources until the branch is pushed.

> **Status.** All four images rebuild byte-identically from source, and that is
> checked centrally after every commit. **None of the four carries a single
> `.incbin` directive** — every byte of all 2,097,152 comes from real source,
> so there is no verbatim debt anywhere in this product.
> Recursive descent over the three code images finds no
> reachable-and-unconverted code left: with no `.incbin` remaining,
> `wsa1/notes/reachability.py` reports STRONG 0 and ANY 0 at `3417969c0`
> ([the column](#the-reachability-column-and-what-is-still-on-it)).
> Every figure on this page is regenerable; regenerate it rather than quoting it,
> because these numbers move within hours while conversion lanes run.

## The gate is the only thing that certifies this tree

```
make gate-wsa1     # the four SX-WSA1R images
make gate-all      # all thirteen: 9 KN5000 + 4 SX-WSA1R
```

Both rebuild first and then compare bytes, and must print
`PASS: every rebuilt ROM is byte-identical.` after **every** edit and at **every**
commit. `gate-wsa1` is `cd wsa1 && python3 scripts/analysis/assert_byte_identical.py`.

Never substitute a similarity percentage, and never use `--no-build` unless you
have just built; the reasons are in the script's own docstring. Commits
additionally carry an `LLVM: <branch>@<short> (<full>)` line, enforced by a commit
hook. **The pinned toolchain is recorded in `TOOLCHAIN_VERSION`, which is the
authority — read it rather than quoting a commit id from here.** The same LLVM
TLCS-900 backend assembles the KN5000 tree, so a backend change is gated on all
thirteen images at once.

## ⚠ The rule the gate cannot enforce

**The gate is blind to names, comments and interpretation.** It certifies that
the bytes come back; it certifies nothing about what they mean. Each of these is
gate-clean, and each has occurred in this tree:

* a routine header naming the wrong object, because the name was transplanted
  across a spliced image with every offset short by a fixed constant;
* a quantified claim ("zero exceptions", "243 of 244", a handler count) that no
  committed script reproduces;
* a "byte for byte" describing a partial match, or a borrowed name whose two
  sides differ in a peripheral base address;
* call sites cited one byte past the instruction, systematically;
* "no references" or "no call site" asserted without running the census;
* a title claiming producers were *named* when they were only *located*;
* **data framed as code** — a span that decodes into plausible mnemonics and
  re-assembles byte-exactly, because that is all the gate checks.

Hence the working rules: every semantic name needs an `Evidence:` line; every
quantified claim needs a committed script, tested on the **last** element as well
as the first; every borrowed name needs a byte diff with the differing count
stated. **Prefer `sub_XXXXXX` plus a stated gap over a plausible guess.**

The disassembly's README carries a measured **semantic score** (`make semantic-score`,
`scripts/analysis/semantic_score.py`). For the SX-WSA1R it was **92.62 %** when last
measured (2026-10-06, at `7936b0a2`): the mean of bytes understood (the census's strict
grade, 94.75 %), semantic names (83.11 %) and jump tables resolved (762 of 762). Quote it
with its date; the README badge is the current value.

## Coverage — three columns, and only one of them means understanding

```
python3 wsa1/scripts/analysis/source_coverage.py     # per-image, this product
python3 scripts/analysis/kn5000_source_coverage.py   # all 13 gated images
```

Every image's bytes fall into exactly three buckets, and they are not equivalent:

* **substantive** — decoded instructions and typed data structures;
* **verified filler** — long runs of a single pad byte, measured and emitted as
  `.fill`. Real, checked rather than sampled, and belongs in the source — but it
  is territory, not understanding, and prom_c/prom_d are mostly this;
* **verbatim `.incbin`** — a blob with no generating source. This is the debt.

Snapshot from the first command at disassembly commit `3417969c0` (2026-10-06; span
counts are `grep -rc '^\s*\.incbin' wsa1/prom_*/`):

| source    | image              | substantive            | verified filler | still `.incbin` | `.incbin` spans |
|-----------|--------------------|-----------------------:|----------------:|----------------:|----------------:|
| `prom_a`  | `wsa1_prom_a.ic12` | 457,875                | 66,413          | **0**           | 0               |
| `prom_b`  | `wsa1_prom_b.ic13` | 452,994                | 71,294          | **0**           | 0               |
| `prom_c`  | `wsa1_prom_c.ic28` | 395,072                | 129,216         | **0**           | 0               |
| `prom_d`  | `wsa1_prom_d.bin`  | 330,521                | 193,767         | **0**           | 0               |
| **total** |                    | **1,636,462 (78.0 %)** | 460,690         | **0**           | 0               |

`prom_a`'s substantive count is 3,297 bytes *lower* than on 2026-09-02 and its filler 3,297
higher, and that is correct: runs that had been framed as code were shown to be uniform pad
and are now emitted as verified `.fill` — for instance the two `nop` runs that
`notes/proma-2026-09-25/retire_zero_runs.py` (disassembly repository) proves unreached.
Territory moved from one column to the other; nothing was lost.

⚠ **Quote substantive, not the 100 % "incl. filler" total.** prom_c alone
contributes a verified 118,298-byte run of `0x0E` pad; counting it as equal to
decoded code inflates the headline without adding a byte of understanding.

⚠ **Never retype this table into a page that is not regenerated.** A hand-typed
copy of it is stale the moment any lane converts a span, and nothing in the build
can notice.

## The reachability column, and what is still on it

Coverage counts territory. A separate and stricter question — *is there any byte
that execution can reach and that this tree has not converted?* — is answered by
`wsa1/notes/reachability.py`, which walks the CPU vector table, the 1,910-slot
routine directory, framed pointer tables, branch targets in converted code and
32-bit immediates, and **grades every seed**:

* **STRONG** — a directory slot, a decoded branch, a hardware vector. An entry
  point, full stop. *Convert on this column.*
* **WEAK** — a `.long` table entry or a raw 32-bit immediate. That is a pointer,
  and a pointer is as likely to name a table as a routine; walking from one
  paints data as code.

```
python3 wsa1/notes/reachability.py            # the coverage report
python3 wsa1/notes/reachability.py --targets  # the ranked work list
```

At disassembly commit `3417969c0` (2026-10-06), with no `.incbin` left,
`--targets` reports **STRONG 0 bytes, ANY 0, in 0 spans**; on 2026-09-02 it
reported STRONG 9 and ANY (STRONG+WEAK) 1,531 bytes across 30 spans. `prom_d` is
data with no established load base and is not walked at all.

**Those 9 STRONG bytes were refused, not pending.** They sat inside one 149-byte
span of `prom_b`, `0xF283A8-0xF2843D`. Its only matching display-list handler was
the bare-`ret` family, whose implied-length rule is "min 2" — true of any byte
pair, so it corroborated nothing — and `unidasm` rendered the span as incoherent
code from that offset. It was the walk-decoded-its-way-into-data pattern, and was
documented as excluded at the source
(`wsa1/notes/gen_prom_b_untouched_pool_module.py`, `wsa1/notes/README-prom_b.md`).
The span has since been identified as data: it lies inside `Data_F283A7`, the
5 × 30 bitmap (150 bytes) that 32 interpreter-A op-0x03 display-list records draw
(`wsa1/notes/gen_promB5_spans.py`).

⚠ **The walk's own reach is a claim about the walk, not about the ROM.** A seed
of the wrong grade paints data as code, and the byte gate cannot object, because
re-assembling a wrong interpretation reproduces the same bytes. That is why the
grading exists and why the STRONG column is the only one converted on.

Nothing is left outside that column either. If a span ever goes back to
`.incbin`, the same rule applies: WEAK-only bytes need a byte-level audit before
anything is converted, and runs with no start evidence of any grade are refused
until evidence appears.

### ★ The number that measures meaning

Coverage measures territory. The count of routines that are **converted but
still unnamed** — every label of the form `sub_XXXXXX` — measures meaning, and it
is the half of the work that is furthest from done. Conversion adds unnamed
routines; only reading them retires one.

Run from the disassembly repo root; these are the definitions, and they drift
with every merge:

```
git ls-files 'wsa1/prom_*/*.s' | xargs cat | grep -aoE '^sub_[0-9A-Fa-f]{6}:' | sort -u | wc -l   # unnamed routines
git ls-files 'wsa1/prom_*/*.s' | xargs cat | grep -ac 'Evidence:'                                 # evidenced headers
git ls-files 'wsa1/notes/*.md' | wc -l                                                            # notes documents
git ls-files 'wsa1/*.py' | wc -l                                                                  # committed analysis scripts
```

At disassembly commit `3417969c0` (2026-10-06): **568 unnamed routines** (125 in `prom_a`,
272 in `prom_b`, 171 in `prom_c`'s sources), 9,811 `Evidence:` lines, 175 notes documents
(132 of them `FINDINGS-*`), 601 committed Python analysis scripts.

The command reads every source file under the `prom_*` roots: `prom_c` is now 27 source
files, 25 of them in subdirectories, which a one-level `wsa1/prom_*/*.s` glob silently
skips. The count rose from 4,752 (2026-09-02) to 6,294 (`be376096`) as conversion and the
operand symbolisers gave unlabelled entry points a `sub_` label. It then fell to 568 by
2026-10-06: 5,357 just before naming round 1, 4,570 after it (2026-10-03, 787 renames in
eight packs ending at `94f697933`), 1,613 after the subsystem-by-subsystem reading commits
of 2026-10-03 to 10-05, and 568 after naming waves 2–11 (2026-10-06, ending at
`3f4b6ad62`). It is not a number that only falls.

⚠ A label count depends on what you count — compiler-local `.L` labels in
particular — so a figure without its command is meaningless here.

### Named subsystems of CPU 1

Against that backlog, three subsystems of CPU 1's `prom_a` are named as
architecture rather than as addresses. The **parameter-number space** — one
four-byte record `[number][class][value][mask]` that MIDI-in, the panel and the
editors all produce, turned into the `0x2C00` queue by
`List2030_TranslateToQueue2C00` and `Dispatch_By_60F080`, with the part records,
their factory defaults in `prom_b` and the combination memory in `prom_c` all
addressed by the same numbers — is on its own page,
[Parameter Records & MIDI]({{ site.baseurl }}/wsa1-parameters/). The **UI screen-object system** —
`PanelScreen_VtableTable` (`0xF86EC1`), 256 screen objects each a three-method
Enter/Leave/Button vtable — is decoded, so a button press resolves to a named
screen and its methods (see
[the control panel]({{ site.baseurl }}/wsa1-panel/#the-screen-objects-how-a-screen-is-dispatched)).
And the **disk / block-device command layer** at `0xFE0000`-`0xFE54B6` — the
stack above the FDC driver, carrying `Disk_ReadSectors`, `Disk_WriteSectors`,
`Disk_RequestSenseDriveStatus`, `Disk_SetRequestGeometry` and
`Disk_CommandDispatch` — is named at the command-issue seam (see
[storage]({{ site.baseurl }}/wsa1/#storage-and-a-fixed-disk-that-may-never-have-shipped)).
Since the October naming rounds, most of `prom_a` is named: 125 `sub_XXXXXX` routines
remain in it (272 in `prom_b`, 171 in `prom_c`). No screen object's ENTER method, none of
the disk dispatcher's fifteen handlers (`DiskCmd_*`) and none of the four
parameter-dispatcher handlers with bodies (see
[the rest of the space]({{ site.baseurl }}/wsa1-parameters/#the-rest-of-the-space)) is
still `sub_XXXXXX`.

## ★★ ONE KERNEL, FOUR PROCESSORS, TWO PRODUCTS

**The two WSA1R processors share ONE SOURCE FILE.** `wsa1/kernel/kernel.s`,
with `kernel_maincpu.inc` or `kernel_subcpu.inc` supplying the equates,
assembles **twice**: into 2,180 bytes of `prom_a` and 2,180 bytes of `prom_c`,
both byte-identical to the EPROMs. **That dual build is the proof** — one wrong
equate and one of the two images stops rebuilding.

Of 941 instruction slots (939 present on both sides as source lines), 735 already
said the same thing, 129 differed only in house style, and **81 carry a per-CPU
value. Those 81 sites are 21 constants**, not 81 patches: twelve RAM addresses,
six array sizes, three ROM pointers. There is no `.if`/`.else` anywhere in the
file — an equate names each difference once and the body stays genuinely shared.

The array sizes are where the two processors' personalities live: CPU 1 runs **4
tasks, 8 semaphores, 4 message queues**; CPU 2 runs **3, 4 and 2**. The same
kernel over a different RAM map with different counts is the entire difference
between them.

**The same kernel is in both of the KN5000's processors too** — in its sub-CPU
payload and, as a separate build rather than a copy, in its main program ROM.
One kernel, four processors, two products
(`wsa1/notes/kernel_structural_match.py`, with a 14-check `--selftest`).

⚠ **Byte identity is the wrong instrument for that cross-product question, and
this tree's own result says why.** A byte search finds zero kernel routines in
any of the 41 KN5000 images — true about bytes, and no answer at all, because two
processors *in the same product, from the same build, running the same source*
already differ in 81 of 941 slots. The match has to be made structurally, on
decoded token sequences, and it has to be run against a foil.

### A second shared source: the DSP channel-register driver

The kernel is not the only source both processors share. `dsp/dsp_channel_regs.s` — four routines, 234 bytes, of which **231 are
byte-identical between the two CPUs** — is now a single file included by both
roots. Everything that differs is one equate:

| CPU | `DSP_REGS_BASE` |
|---|---|
| CPU 1 (`prom_a`) | `0x007F0000` |
| CPU 2 (`prom_c`) | `0x00E00000` |

Three use sites, and **no conditional assembly anywhere in the body**. The
byte-identity gate covers it: 13 images rebuild identically (9 KN5000 + 4
WSA1R), and the negative control — setting the sub-CPU equate wrong — fails
`prom_c` at exactly three bytes while leaving `prom_a` green, so the gate is
demonstrably load-bearing here.

⚠ **The merge produced a finding, not just a tidier tree.** With both files'
call-site annotations on one page, they disagree twice, in opposite directions:

| routine | CPU 1 | CPU 2 |
|---|---|---|
| `DSP_ChannelRegs_Init` | no call site found | called at boot from `0xF98B95` |
| `DSP_WriteAllChannelRegs` | published via `prom_b` thunk `0xF42DE4` | not traced |

Identical bytes, different reachability per processor — each one uses the
routine the other does not. This is **unexplained**. In either file alone an
untraced routine reads as ordinary coverage debt; only the merge makes it an
asymmetry.

The control that decides it is a **foil** — the identical search run over WSA1R
code that is *not* the kernel:

| | n | max | median | ≥ 0.70 |
|---|---:|---:|---:|---:|
| kernel routines (≥ 20 instr) | 20 | 1.000 | **0.909** | **20** |
| non-kernel foils, same lengths | 26 | **0.333** | 0.212 | **0** |

No overlap, a gap of 0.41. `prom_b` — same product, same compiler, no kernel —
tops out at 0.28, so it is not measuring the compiler; shuffling the query's
token order collapses the score, so it is measuring *order*, not vocabulary. Two
threshold-free instruments agree: the 26 sites appear in ROM order as a **21-long
increasing run** (200,000 permutations never exceeded 14), and the recovered RAM
map is **monotone** across all three processors.

**Not established:** who wrote it, or that the sources are identical —
`Kernel_Dispatch` scores 0.742, the KN5000 version having no tick-drain loop and
its lock depth moved out of a control register the TMP94C241 does not have.

---

## ★ The two processors run the same kernel — 35 of 36 routines identical to the byte

The strongest structural result in the tree is about the machine's relationship
to *itself*. `notes/prom_c_prom_a_routine_diff.py` aligns two routines
instruction by instruction and separates *different mnemonic* (structural) from
*same mnemonic, different operand* (a substituted address):

| | |
|---|---:|
| routine pairs | **36** (35 in the block, plus `INTT3_KernelTick`) |
| pairs whose prom_c length equals their prom_a length | **36 of 36** |
| pairs with **zero** structural differences | **35 of 36** |
| the exception | `Kernel_InitRam`, with **2** — both inside an 8-byte inline data block |

The routine boundaries are **checked, not asserted**: `notes/prom_c_kernel_map.py --pairs`
verifies that each
routine ends exactly where the next begins **in both images**, and fails
otherwise. *36 boundaries agreeing to the byte across two independently compiled
images is not something a wrong split survives.* `Kernel_ResumeTask` is the
extreme case — all nine bytes identical, with no operand to substitute.

**Every one of the ~120 operand differences is a RAM address, a ROM table
address, a loop bound or a branch target. The two images differ in their RAM map
and in nothing else.** CPU 1 publishes the kernel through two runs of prom_b
thunks (a register-argument face and a stack-argument face); prom_c has **no
thunk table** — the same routines at the same relative offsets, with the same
nine stack faces falling through into the register face.

### The kernel's RAM map is a proof, not a reading

`Kernel_InitRam` (prom_c `0xF9816B`) writes nine arrays with literal bases and
literal counts. `prom_c_kernel_map.py --map` reads all eighteen numbers out of the
**instruction bytes**:

```
base     n  stride  end      what
0x0100   3   12    0x0124   task control blocks
0x0124   2    4    0x012C   ready-queue heads
0x012C   4    4    0x013C   semaphore wait queues
0x013C   4    1    0x0140   semaphore counts
0x0140   2    4    0x0148   message WAIT queues
0x0148   2    4    0x0150   MESSAGE queues
0x0150   4    8    0x0170   free nodes
0x0170   1    4    0x0174   free-list head
0x0174   2    8    0x0184   software timers
```

**The nine arrays tile `0x0100`–`0x0183` with no gap and no overlap.** A wrong
count anywhere in that chain leaves a hole or an overlap — so "three tasks, two
priority levels, four semaphores, two message queues, four free nodes, two
software timers" is each pinned **twice**: by a literal loop count, and by the
array that starts where the previous one ends.

## ★ Shared code with the KN5000 — measured, with a null

Because **both machines are TLCS-900**, code can cross between them as literal
bytes. `scripts/analysis/kn5000_shared_runs.py` finds every maximal run of ≥ 16
bytes shared between the WSA1 images and the KN5000 sub-CPU payload, and grades
each one:

| | |
|---|---:|
| kept (survived the entropy guard) | **32,795 B** |
| rejected as low-entropy fill | 291,802 B |
| **shuffle null** (same byte histogram, sequence destroyed) | **0 B** |
| signal-to-null | **32,795×** |
| of the kept mass, held in **prom_c** | **28,916 B** |

*(Re-run 2026-08-26; the figures above are that run's output.)*

**The entropy guard is the whole script.** Without it, the "shared" mass is nine
parts erase-fill and padding. Runs are rejected when fewer than 12 distinct byte
values appear, when the modal byte is more than 60 % of the run, or when the run
is a repeating period of ≤ 4 bytes — and the rejected set is **printed, not
silently dropped**, because "the kinship is entirely in padding" is an outcome
this script exists to be able to report.

That **28,916 of 32,795 land in prom_c** is the structural finding: the KN5000
sub-CPU is *its* tone-generator controller, so **WSA1 CPU 2 and the KN5000
sub-CPU are the same design.** The data format follows the controller — prom_d's
81-byte per-element voice-parameter block is the KN5000's too, measured against
byte-shift and rotation nulls.

⚠ **Two different numbers exist and must not be conflated.** A separate,
earlier script in the project's private ROM archive (`wsa1_kinship.py`) reports **31,046 B in
588 runs (15.8 %)** with a null of 0 B against an unrelated Technics ROM. It is a
different script over a different corpus, with no entropy guard and the WSA1
images concatenated. **Pick one and name its script.** Do not average them.

⚠ A provenance caveat on the 32,795 figure: `kn5000_shared_runs.py` matches
against `kn5000_subprogram_v142.rom`, which the sibling Makefile builds as a
**spliced** image. The de-splicing was applied to the label transplanter, not to
this script. The count of WSA1 bytes is unaffected, but **payload offsets from
this script are not directly comparable to KN5000 addresses**.

### The label transplant

`wsa1/scripts/analysis/transplant_kn5000_labels.py` proposes KN5000 sub-CPU
routine names for WSA1 addresses **by byte identity**, writing
`wsa1/notes/kn5000-label-transplant-generated.md`. It emits **105 proposals, 0
dropped by the byte check** (re-run 2026-09-02).

Two properties of the script matter more than the count:

* **It matches against the ELF's own unspliced binary**, so `addr = 0x400 +
  offset` holds at every offset and there is no correction constant to get wrong.
  (The sibling Makefile also builds a *spliced* `kn5000_subprogram_v142.rom`;
  matching against that one shifts every offset past the first 256 bytes by
  60,160 = `0xEB00`, and the resulting names are thematically plausible enough to
  survive eye-checking.)
* **Every proposal is byte-verified at emission** and dropped if the bytes
  disagree, so a mis-based run emits nothing rather than plausible wrong names.

⚠ Byte identity establishes that the *code* is the same, not that the surrounding
machine is. Of the 105, 58 are now labels in the WSA1R sources, most with a header citing
the KN5000 sibling (for example `Voice_DepthMirror_Table`, prom_c `0xFDD5AB`, whose header
cites `v142/subcpu/subcpu_data_tables.s:1010`); 35 of the addresses carry a different name
and 12 none. One transplanted pair, `Int_SignedDiv` (prom_a `0xFE68F3`) and
`FP_UnsignedDiv` (`0xFE6948`), has been converted and read. A transplanted name records
byte identity, not a reading of the WSA1 code.

## What is left

**All four images are at zero verbatim debt.** None of them hands a byte back through an
`.incbin`. That is not the same as every byte being in its final form, in either direction:

* **code still spelled as `.byte`** — at disassembly commit `3417969c0` (2026-10-06),
  `prom_a` carries **82 certified `.byte` instruction sites (226 B, 42 forms)**; `prom_c`
  carries none. `prom_b` holds 68 `.byte` rows (221 B) that its source marks
  `[llvm-mc cannot encode this]`, all between instruction lines: 66 carry an instruction
  reading (`rrc`/`rlc` by a count, shift-by-A, `ldir`, `ex BC,QBC`, …) and two carry
  unidasm's `db` (`wsa1/notes/promb_macro_rewrite.py --census`;
  `tools/annotated_insn_bytes.py wsa1/prom_b` in this repository). The census script named
  below counts none of them, because their comments carry no byte echo, and it prints
  "every instruction in this image is spelt" for `prom_b`. How many of `prom_a`'s 82 have a
  spelling that reassembles byte-identically depends on the assembler build as well as the
  sources. Under the pin `TOOLCHAIN_VERSION` names (`a3a81863f87d`, llvm-mc sha256
  `118bb4d6766e`), **the census script spells one form, `decf`, and finds no spelling for
  81**; 34 of those 81, in 13 shift-by-A forms, reassemble byte-identically as
  `slaa`/`slla`/`srla`, which it does not try (`tools/wsa1_shift_by_a_spellings.py` in this
  repository), so 47 sites in 28 forms have no spelling found so far. At `be376096`
  (2026-09-25) there were 298 sites (1,318 B, 89 forms), 282 of them unspelt under the then
  pin `8e188b215251`; the respells of 2026-10-03 (`7a9cf4ff8`, `09cc4ae4d`) converted most
  of them. The commonest form with no spelling found is now `ex BC,QBC` (5 sites). Run
  `python3 notes/sound/wsa1_unspellable_forms.py` from `wsa1/` in the disassembly
  repository; it counts a line only if its byte echo, the ROM at its address, MAME's
  `unidasm` framing and a round trip all agree, and it uses whatever llvm-mc the shared
  build holds. `tools/wsa1_unspelt_by_toolchain.py` in this repository runs it at a pinned
  revision under named llvm-mc binaries and prints each binary's sha256.
* **data framed as code** — the earlier audit that called `prom_a` and `prom_b` clean did not
  hold: the 2026-09-25 lanes found and retyped data decoded as instructions in both (in
  `prom_a` 1,958 B plus eleven panel lookup tables and the LED wire maps; in `prom_b` nine
  tables). `prom_c` and `prom_d` survived a deliberate attack on this hazard.

| image | verbatim `.incbin` | source |
|---|---:|---:|
| `prom_a` | 0 | 100% |
| `prom_b` | 0 | 100% |
| `prom_c` | 0 | 100% |
| `prom_d` | 0 | 100% |

*(2026-09-02, `python3 scripts/analysis/kn5000_source_coverage.py`.)*

⚠ **Zero verbatim debt is a statement about `.incbin`, not about understanding.** The
per-range data census, run at `3417969c0` (2026-10-06), gives these images:

| image    | strict (CODE + evidenced data + filler) | UNKNOWN | name-only (KNOWN-B) | research targets |
|----------|----------------------------------------:|--------:|--------------------:|-----------------:|
| `prom_a` | 95.33 %                                 | 245 B   | 24,255 B            | 20,262 B         |
| `prom_b` | 85.86 %                                 | 436 B   | 73,687 B            | 61,020 B         |
| `prom_c` | 98.01 %                                 | 0       | 10,409 B            | 9,584 B          |
| `prom_d` | 99.79 %                                 | 0       | 1,096 B             | 1,096 B          |

A research target is a range whose purpose is not established — no explanation, a header
that admits a gap, or undocumented data between two instruction runs. `prom_b` is the
image with the most left to say. What the grades mean, and why "strict" is the
instrument's keyword grade rather than an audited figure, is on
[how much of the data is actually explained]({{ site.baseurl }}/rom-reconstruction/#how-much-of-the-data-is-actually-explained).

★ The last spans to close were **not undecoded code**. Every one of `prom_b`'s final
sixteen residual spans is data — display-list content named by pointers — and being data is
exactly what made them writable as source. The instrument that unlocked most of them was
that a display list is entered as `ld XIY,<start> / ld XIX,<end> / call 0xF417F0`, so a
list's first byte and its exclusive end are **two 32-bit constants sitting in code the tree
already disassembles**. Three findings outlive the bytes: *advance ≠ extent* (a length
disagreeing with its handler can be a deliberate list terminator, not a misframe);
*measure an object from the thing that names it*, never from an `.incbin` boundary cut by a
superseded walk; and one region's layout came off the `djnz` loop that walks it, where
entry 0 duplicates entry 1 because the loop counts down to 1 and never reads entry 0 — a
property of the reader that is invisible in the data.
(`notes/FINDINGS-prom_b-last-481-bytes-RESOLVED.md`, script
`wsa1/notes/prom_b_residue_481.py --selftest`.)

⚠ **Anchor an `.incbin` count to the start of the line.** `grep -ac '\.incbin'` over
`wsa1/prom_b/wsa1_prom_b.s` returns 319 at `3417969c0` — every one of them the word
`.incbin` inside a *comment*, because each conversion documented what the region used to be.
`grep -ac '^[[:space:]]*\.incbin'` returns 0. The unanchored form has already had a coverage
tool double-counting hundreds of kilobytes of debt out of dead comments.

`prom_d` contains **no code**. Flattened through the assembler it yields ten
instruction encodings totalling 30 bytes, and every one is a verified data
coincidence: a little-endian `u16` array where a field's low byte happens to be
`0xC7` and the following field's low byte falls inside an ERP sub-opcode range.
Quote the figure that way — "ten spurious encodings, all proven data" — rather
than "zero encodings", which is the weaker claim it is often shortened to.

That conclusion does not rest on the disassembler alone. A decoder-independent
scan for the encoder's exact SriRR-family byte shape
(`wsa1/notes/sound/prom_d_srirr_falsification.py`) finds **0 matches in `prom_d`
against 599 in `prom_a`, 1,261 in `prom_b` and 125 in `prom_c`** — all three
confirmed code images — so the method discriminates rather than simply failing to
fire anywhere, and prom_d's null survives an attack that does not depend on the
disassembler at all.

The same script re-verifies prom_d's erased region independently: one 193,767-byte
run of `0xFF` at file `0x050B09`, ending at `0x07FFF0`, with sixteen bytes of
content after it — the ASCII `wsad_54.ssf`. It is **not** a trailing tail.

### Among the largest open ranges

From the same census, merged the way its research-target list merges them
(`tools/census_research_by_image.py OUT.json --ranges prom_a,prom_b,prom_c,prom_d` in this
repository, over `data_range_census.py --json OUT.json`; re-run at `3417969c0`). The six
largest are all in `prom_a` and `prom_b`: the first four below, then `prom_b`'s
`Font_Svc06_8x14` (2,800 B) and `prom_a`'s `RecordTables_FB82A0` (2,566 B). Next in size
come `prom_b`'s `EffectNames_F147AC` (2,048 B), `prom_c`'s curve tables (1,772 B, below) and
`prom_b`'s `SmfExport_ParamSysExTemplates` (1,718 B). After the first four, the list notes
two former entries and is a selection, one entry per image for `prom_c` and `prom_d`.

* **`prom_b` `0xF212B0`–`0xF24DC0`** (15,120 B), fonts `Font_Svc16_8x14` … `Font_Svc1F_16x16`.
  Their roles and metrics are established; each header keeps one open question, which is
  enough for the census to list the whole range.
* **`prom_b` `0xF06800`–`0xF08CD8`** (9,432 B), `ScaleTuningOffsets` …
  `ProgramChangeOut_ByProgramAndBank`. `PanelSoundSel_ByProgramAndBank` (`0xF07134`) and
  `ProgramChangeOut_ByProgramAndBank` (`0xF08514`) are indexed by (program, bank).
  `SoundCodeByGroupMember_ModeOffsetGroup` (`0xF06EF4`) maps a panel selection to (program,
  bank) and `PanelSoundSel_ByProgramAndBank` maps it back, exact inverses on all 272 panel
  selections. What the words encode for a given sound is still open (the reader at prom_a
  `0xFC248D`, in `SoundSel_FromPresetProgramAndBank`, classifies the low byte against
  `0x0F`, `0x1F`, `0x20` and `0x21`).
* **`prom_a` `0xFED90A`–`0xFEF746`** (7,740 B), `DrumKitNames_Block7` … `DrumKitNames_Block12`. No
  reader: their 24-bit block and base addresses occur in none of the four images, and a
  multiply by 1290 or 129 was ruled out in `prom_a`.
* **`prom_b` `LinkTable_F4FF61`** (4,602 B) is the SysEx decode tree `prom_a` `SysExRx_MatchTrie`
  walks (entered at its record 767, `0xF5115B`); every one of the 74 SysEx bodies the SMF
  exporter writes is a complete seven-byte path through it
  (`notes/promb-2026-09-25/sysex_decode_tree_probe.py`). What a leaf's result and pair bytes
  select is still open.
* `prom_b`'s 32 `ButtonTable_*` tables (4,096 B, now evidenced data, with all but two of
  their 491 distinct handlers named by table and slot) and `RecordArray_F511DD` (3,139 B,
  the SysEx parameter descriptors `SysExParamDesc_*`, 56 B of it still a target) have left
  the top of the research list; the producer of button codes `0x0E` and `0x11`–`0x19` is
  still unfound.
* **`prom_c` `0xFDF7E0`–`0xFDFECC`** (1,772 B), `Curve_Fitting_Exp2Decay_256` …
  `Dev104_Reg0100_Const_251` — `prom_c`'s largest research target. The four voice-driver
  curve tables' fits and readers are established; their headers keep what is not, such as
  the rate at which the sound LSI steps the fitting curve (not in this ROM) and the unit of
  the constant `0x0100` that `Dev104_Reg0100_Const_251` feeds to register `0x0100`.
* **`prom_c` — the P7 stream pool** (`0xFCD0F7`–`0xFDD2AA`, 65,972 B) is no longer an
  unframed stream: its 297 length-prefixed streams are what `P7Stream_Run` sends out of port
  P7 to the DSPs, a unit's program 0–127 is a DSP effect number (56 directory records in
  one-to-one correspondence with `prom_b`'s `EffectNames_F147AC`), and every directory
  record, field array and stream is named by its effect. **24 streams (5,897 B) have no
  reader** — searched through the directory records, `.long` words and operands, LE24/LE32
  in `prom_c`, LE32 in `prom_a`/`prom_b` and pool-relative LE16 — and are stated as
  unreferenced, not explained. The largest of them are ~1 KB ranges on the census list
  (the biggest, `P7Stream_FCFA2A` …, 1,103 B), smaller than the curve tables above.
* **`prom_d`** — only `ToneDB_ToneOffsetTable` (1,096 B) remains, and its open question is
  narrow: the program order of `ToneDB_ToneNumBanks`.

## Older-build remnants, and why unreached code can be correct

**Parts of these EPROMs are relocated copies of live objects that nothing names — most
likely an earlier build's bytes, left where the new build did not overwrite them.** Three
stretches of `prom_b` are proven to be relocated copies of live
objects, each by its own script under `notes/promb-2026-09-25/` in the disassembly
repository (run from the repository root; one of the three needs the caveat below the
table):

| range | what it is | position | proof |
|---|---|---|---|
| `0xF0ED50`–`0xF0EFFF` (688 B) | the display-list interpreter's data block: the tail of its two handler tables, the value-glyph quantiser, the value-glyph table and the first four 24 × 24 value glyphs (`OldBuild_DLHandlerTables_Tail`, `OldBuild_ValueGlyph_*`) | live − `0x23001` | `stale_dl_tables_f0ed50.py` (its byte checks — see below) |
| `0xF17A5F`–`0xF17BFF` (417 B) | a second copy of the value-glyph data: quantiser tail, 29-word glyph table, glyphs 0–3 (`OldBuild2_ValueGlyph_*`) | live − `0x1A401` | `stale_value_glyphs_f17a5f.py` |
| `0xF6F000`–`0xF6F3FF` (1,024 B) | **code**: the module whose live copy is `0xF7AA00`–`0xF7ADFF`, identical except for the nine bytes relocation changes (`OldCopy_*`) | live − `0xBA00` | `old_module_copy_f6f000.py` |

⚠ `stale_value_glyphs_f17a5f.py` and `old_module_copy_f6f000.py` end `VERDICT: PASS` on the
current tree. `stale_dl_tables_f0ed50.py` does not: it is also the script that rewrote the
source (commit `37df48c0`, `--apply`), and it ends `VERDICT: FAIL (7)` on every tree from
that commit on. Its byte checks all pass — each of the 39 old words is the live entry
− `0x23000` or − `0x23001`, the quantiser, glyph table and glyphs 0–3 match at live
− `0x23001`, the block is 688 B ending on the 4 KB boundary `0xF0F000`, and the old handler
address `0xF0EA3A` lands at `Blink_Command_Table` + `0x26`. The seven failures are its label
checks, which look for the `sub_F0EA9F_Arm` … `sub_F0F676_Arm` labels that its own `--apply`
removed in `37df48c0`. Run against the `prom_b` source of `37df48c0^`, it passes in full.

They share a signature: each runs from the end of this build's live code up to a 1 KB or
4 KB boundary, nothing in `prom_a` or `prom_b` names any address inside it, and its own
pointers are the live ones shifted by one constant — so in *this* build they point into
unrelated bytes (the old handler addresses of the first land inside `Blink_Command_Table`
and in the middle of instructions). The checks prove the correspondence; that the image was
built over an older one is the natural reading, not something the bytes can prove.
`relocated_copy_scan.py --boundaries` in the same directory is the lead finder that surfaced
all three, and it is a lead list, not evidence: most of its hits are legitimate repetition.

`prom_a` shows the same pattern, at a distance of about `0x400`:
`PanelGroupQueue_ExpandToEvents_DeadCopy` (`0xF8A44B`), the `MessageScreenStale_*` tables
at `0xF98DE5`, `ScreenButtonHandlers_StaleCopy` (`0xF95D95`), and a 1,000-byte veneer bank at
`0xFAA018`–`0xFAA3FF` that differs from the live one at `0xFAA418`–`0xFAA7FF` in exactly ten
bytes (`wsa1/notes/FINDINGS-prom_a-message-module.md` §3a) — among it
`ParamRecord_WriteFieldAndStage_StaleCopy` and `Queue2C00_PublishStagedIfPending_StaleCopy`.
Separately, `prom_b` holds 474 bytes of **unreached** code — five routines and a small RAM
pointer table, decoded by round trip, that nothing branches to, calls or names
(`unreached_code_f6ea57.py`); that one is stated as unreached, not as a proven copy.

**Why it matters for emulation.** A routine the emulator never executes is not by itself
evidence of a missing interrupt, device or call path: it may be stale. Before treating
unreached code as a MAME defect, check whether it is a remnant — and never take a routine's
address from the stale half of a pair. That mistake has already happened on this site: the
tempo consumer on [System Exclusive Messages]({{ site.baseurl }}/sysex-messages/#the-one-traced-live-parameter-tempo-slot-9)
was cited at `0xFAA350`, inside the stale veneer copy; the live routine is `Tempo_ApplyBpm`
(`0xFAA742`), called directly from five places in `prom_a` and published through the `prom_b`
thunk `T_Tempo_ApplyBpm` (`0xF40794`).
A tool that "follows every pointer" has the complementary problem: a remnant's pointers name
unrelated live bytes, and walking them paints data as code.

## ⚠ Tools that mislead, named as such

* **`prom_c_frontier.py`: 132 of its 135 targets are phantoms**, produced by
  linearly disassembling ASCII descriptor strings and data zones. Its output is
  not a work list.
* **`prom_b_span_frontier.py`'s `proven 0` is not evidence of data.** Its
  call-site scanner recognises one calling idiom, so a well-evidenced region
  reached any other way scores 0 — a low score there ranks nothing.
* **A frontier count that does not fall after converting a data span is correct,
  not a failure** — data retires no call target. Do not quote a drop that did not
  happen.

There is a matching trap in the code tracer. A straight linear sweep of these
images is worthless for a memory map: prom_c holds an IEEE-754 double table at
file `0x4B27E` (the bytes at its head are π) which linearly disassembles into a
tidy stride-4 register file **that does not exist** — 280 phantom "registers" came
out of that before the recursive-descent walker was written. What the table really is:
the constant pool of CPU 2's double-precision maths library (`prom_c/mathlib/mathlib.s`).
Its coefficient sets are the Cody & Waite ones (*Software Manual for the Elementary
Functions*, 1980), all 29 within one ulp of the printed values, and each set is loaded by
exactly one routine — which is how `Double_Sin`, `Double_Cos`, `Double_Tan`, `Double_Exp`,
`Double_Log`, `Double_Pow`, `Double_Abs` and `Double_MakeInfinity` got their names
(`notes/lanes/promcd-2026-09-25/mathlib_names.py`, which asserts every coefficient and the
instructions that load them). Four helpers beside them are still `sub_XXXXXX`. Even the walker's
heuristic seeds drag data in as code, and three known false positives are named
in its README.

**And recursive descent does not reach everything.** `wsa1/notes/reachability.py`
reached 323,618 B of prom_a plus 262,049 B of prom_b (CPU 1) and 223,065 B of
prom_c (CPU 2) at `3417969c0` (2026-10-06) — well under each CPU's megabyte and
half-megabyte of EPROM. A device touched only from code the walk never reaches
would still be missing from the [memory map]({{ site.baseurl }}/wsa1/#memory-maps),
so absence from that map is not evidence that a device does not exist.

## Related

| Page | Description |
|------|-------------|
| [SX-WSA1 / SX-WSA1R Overview]({{ site.baseurl }}/wsa1/) | The machine, the hardware, the memory maps, the model strap |
| [Emulation Status]({{ site.baseurl }}/wsa1-emulation/) | The MAME driver the disassembly feeds, and which feeds it back |
| [Acoustic Modelling LSI (L7A1429)]({{ site.baseurl }}/wsa1-modeling-lsi/) | What the CPU 2 device drivers in this tree turned out to be driving |
| [Shared Codebase Map]({{ site.baseurl }}/technics-shared-codebase/) | Where this machine's code meets the KN5000's and the KN7000's |
| [KN5000 ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/) | The sibling project, and where these practices come from |
