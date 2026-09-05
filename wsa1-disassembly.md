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

> **Status.** All four images rebuild byte-identically from source, and that is
> checked centrally after every commit. **None of the four carries a single
> `.incbin` directive** — every byte of all 2,097,152 comes from real source,
> so there is no verbatim debt anywhere in this product.
> Recursive descent over the three code images finds essentially no
> reachable-and-unconverted code left — the entire STRONG total is one span of
> `prom_b`, and it is formally refused ([why](#the-reachability-column-and-what-is-still-on-it)).
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

Snapshot from the two commands above, 2026-09-02 (span counts are
`grep -rc '^\s*\.incbin' wsa1/prom_*/`):

| source | image | substantive | verified filler | still `.incbin` | `.incbin` spans |
|---|---|---:|---:|---:|---:|
| `prom_a` | `wsa1_prom_a.ic12` | 461,172 | 63,116 | **0** | 0 |
| `prom_b` | `wsa1_prom_b.ic13` | 452,984 | 71,304 | **0** | 0 |
| `prom_c` | `wsa1_prom_c.ic28` | 395,072 | 129,216 | **0** | 0 |
| `prom_d` | `wsa1_prom_d.bin` | 330,521 | 193,767 | **0** | 0 |
| **total** | | **1,639,749 (78.2 %)** | 457,403 | **0** | 0 |

⚠ **Quote substantive, not the ~99 % "incl. filler" total.** prom_c alone
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

As of 2026-09-02 the whole product reports **STRONG 9 bytes** and **ANY
(STRONG+WEAK) 1,531 bytes across 30 spans**, with `prom_a` and `prom_c` at zero
STRONG. `prom_d` is data with no established load base and is not walked at all.

**Those 9 STRONG bytes are refused, not pending.** They sit inside one 149-byte
span of `prom_b`, `0xF283A8-0xF2843D`. Its only matching display-list handler is
the bare-`ret` family, whose implied-length rule is "min 2" — true of any byte
pair, so it corroborates nothing — and `unidasm` renders the span as incoherent
code from that offset. It is the walk-decoded-its-way-into-data pattern, and it
is documented as excluded at the source
(`wsa1/notes/gen_prom_b_untouched_pool_module.py`, `wsa1/notes/README-prom_b.md`).

⚠ **The walk's own reach is a claim about the walk, not about the ROM.** A seed
of the wrong grade paints data as code, and the byte gate cannot object, because
re-assembling a wrong interpretation reproduces the same bytes. That is why the
grading exists and why the STRONG column is the only one converted on.

What remains outside that column: the WEAK-only bytes, which need a byte-level
audit before anything is converted; and runs with no start evidence of any
grade, which are refused until evidence appears.

### ★ The number that measures meaning

Coverage measures territory. The count of routines that are **converted but
still unnamed** — every label of the form `sub_XXXXXX` — measures meaning, and it
is the half of the work that is furthest from done. Conversion adds unnamed
routines; only reading them retires one.

Run from the disassembly repo root; these are the definitions, and they drift
with every merge:

```
grep -rhoE '^sub_[0-9A-Fa-f]{6}:' wsa1/prom_*/*.s | sort -u | wc -l   # unnamed routines
grep -rh 'Evidence:' wsa1/prom_*/*.s | wc -l                          # evidenced headers
git ls-files 'wsa1/notes/*.md' | wc -l                                # notes documents
git ls-files 'wsa1/*.py' | wc -l                                      # committed analysis scripts
```

2026-09-02: 4,752 unnamed routines, 7,561 `Evidence:` lines, 113 notes documents
(86 of them `FINDINGS-*`), 410 committed Python analysis scripts.

⚠ A label count depends on what you count — compiler-local `.L` labels in
particular — so a figure without its command is meaningless here.

### Two named subsystems of CPU 1

Against that backlog, two subsystems of CPU 1's `prom_a` are named as
architecture rather than as addresses. The **UI screen-object system** —
`PanelScreen_VtableTable` (`0xF86EC1`), 256 screen objects each a three-method
Enter/Leave/Button vtable — is decoded, so a button press resolves to a named
screen and its methods (see
[the control panel]({{ site.baseurl }}/wsa1-panel/#the-screen-objects-how-a-screen-is-dispatched)).
And the **disk / block-device command layer** at `0xFE0000`-`0xFE54B6` — the
stack above the FDC driver, carrying `Disk_ReadSectors`, `Disk_WriteSectors`,
`Disk_RequestSenseDriveStatus`, `Disk_SetRequestGeometry` and
`Disk_CommandDispatch` — is named at the command-issue seam (see
[storage]({{ site.baseurl }}/wsa1/#storage-and-a-fixed-disk-that-may-never-have-shipped)).
⚠ These are two named subsystems, not a finished CPU: most of `prom_a` is still
`sub_XXXXXX`, including the screen-object system's own ENTER methods and the disk
dispatcher's handlers.

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
earlier script — `technics_roms/tools/wsa1_kinship.py` — reports **31,046 B in
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
machine is. Of the 105, exactly **one** (`Int_SignedDiv` / `FP_UnsignedDiv` at
prom_a `0xFE68F3`) has been converted and read; the other 104 are **proposals,
not renames.**

## What is left

**All four images are at zero verbatim debt.** None of them hands a byte back through an
`.incbin`, and none carries a `.byte`-dressed remainder either — the byte runs are audited
and typed, and `prom_c` and `prom_d` additionally survived a deliberate attack on the
inverse hazard, code typed as data.

| image | verbatim `.incbin` | source |
|---|---:|---:|
| `prom_a` | 0 | 100% |
| `prom_b` | 0 | 100% |
| `prom_c` | 0 | 100% |
| `prom_d` | 0 | 100% |

*(2026-09-02, `python3 scripts/analysis/kn5000_source_coverage.py`.)*

⚠ **Zero verbatim debt is a statement about `.incbin`, not about understanding.** The
per-range data census still grades 9,034 B of `prom_b`, 8,772 B of `prom_d` and 2,295 B of
`prom_a` as UNKNOWN — a label with no explanatory header — and much more than that rests
on a descriptive name alone. See
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
(`wsa1/notes/FINDINGS-prom_b-last-481-bytes-RESOLVED.md`, script
`wsa1/notes/prom_b_residue_481.py --selftest`.)

⚠ **Anchor an `.incbin` count to the start of the line.** `grep -ac '\.incbin'` over
`wsa1/prom_b/wsa1_prom_b.s` returns 322 — every one of them the word `.incbin` inside a
*comment*, because each conversion documented what the region used to be. `grep -ac
'^[[:space:]]*\.incbin'` returns 0. The unanchored form has already had a coverage tool
double-counting hundreds of kilobytes of debt out of dead comments.

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

### The largest spans still unconverted

* **prom_a** — `0xFE8000-0xFEB330` (13,104 B) and `0xFEF746-0xFF3800` (16,570 B),
  the code halves of the sequencer/UI module. Deferred because about **15 string
  constants sit inside the instruction stream** (`SEQUENCER`, `NOTE EDIT`,
  `DRUM EDIT`, an 838-byte effect-name table at `0xFF047F`); their bounds must be
  pinned first or the linear decode desynchronises. **That bounding is the next
  pass's first job.**
* **prom_b** — the top span is `0xF067A6-0xF0D79B` (28,662 B).
* **prom_c** — `0xFCD0F7-0xFDD2AA` (65,972 B) is a byte-code/command stream left
  **whole**, because the existing 16-bit big-endian framing desynchronises at the
  fifth record. It needs its interpreter found first: *guessing a stride is this
  project's known failure mode.*

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
out of that before the recursive-descent walker was written. Even the walker's
heuristic seeds drag data in as code, and three known false positives are named
in its README.

**And recursive descent does not reach everything.** `wsa1/notes/reachability.py`
reached 377,559 B of prom_a plus 302,686 B of prom_b (CPU 1) and 232,116 B of
prom_c (CPU 2) on 2026-09-02 — well under each CPU's megabyte and half-megabyte
of EPROM. A device touched only from code the walk never reaches would still be
missing from the [memory map]({{ site.baseurl }}/wsa1/#memory-maps), so absence
from that map is not evidence that a device does not exist.

## Related

| Page | Description |
|------|-------------|
| [SX-WSA1 / SX-WSA1R Overview]({{ site.baseurl }}/wsa1/) | The machine, the hardware, the memory maps, the model strap |
| [Emulation Status]({{ site.baseurl }}/wsa1-emulation/) | The MAME driver the disassembly feeds, and which feeds it back |
| [Acoustic Modelling LSI (L7A1429)]({{ site.baseurl }}/wsa1-modeling-lsi/) | What the CPU 2 device drivers in this tree turned out to be driving |
| [Shared Codebase Map]({{ site.baseurl }}/technics-shared-codebase/) | Where this machine's code meets the KN5000's and the KN7000's |
| [KN5000 ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/) | The sibling project, and where these practices come from |
