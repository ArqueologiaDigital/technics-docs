---
layout: page
title: Raw Byte Code Elimination
permalink: /raw-byte-code-elimination/
---

# Raw Byte Code Elimination Plan

**Status: IN PROGRESS.** All thirteen gated images are byte-identical to their physical
dumps, but that is a build-match guarantee, not a disassembly guarantee: a `.byte` run that spells real
code reassembles to the same bytes as an `.incbin` of those bytes, and passes the gate
identically either way. Measured code-as-`.byte` remains in the Main CPU and HDAE5000 ROMs;
the Sub CPU Payload reached zero.
**Goal:** Convert all executable code currently represented as raw `.byte` sequences to native TLCS-900 assembly mnemonics.

## Context

All thirteen gated images rebuild byte-identically from source. That is necessary for
correct disassembly but not sufficient: a `.byte` run that spells real code, or a data
region disassembled into plausible-but-wrong instruction mnemonics, both reassemble to the
same bytes and pass the gate cleanly. Whether a `.byte` run is undecoded code can only be
settled by a per-byte disassembly attempt (Step 1's method, below), not by counting
`.incbin` directives — the table under **Current Status** states what that measurement
currently finds, ROM by ROM.

**The sub-CPU payload is now at zero code-as-`.byte`.** Its last two blocked families are
both closed: `DSP_Bytecode_Op01/02/03` (569 B) needed a decoder fix before the encoder's own
output could round-trip (see [LLVM Semantic Instructions]({{ site.baseurl
}}/llvm-semantic-instructions/)), and the `TaskEvent`/`FIFO`/`TaskSched` family's apparent
~407 B gap turned out to be a measurement bug in the round-trip prober, not a decoder
limitation — of the 672 B it flagged, 50 B is genuine data (loaded as an address, never
executed) and the remaining 622 B decodes and reassembles byte-exact once the prober's own
undercount is corrected. Conversions in this image are proved by round trip: disassemble the
run, re-assemble that exact text, require the original bytes back.

**Counting `.incbin` distorts in both directions.** It hides real debt written as `.byte`,
and it equally rewards pushing legitimate data *into* `.byte` — respelling a viewable
PNG-backed image as hex reduces the metric while destroying the better representation.
Neither direction is progress.

**Scope:** `.byte` sequences that encode native TLCS-900 CPU instructions across all
thirteen gated images. Data tables, strings, bitmaps, firmware bytecode for software interpreters, and padding are out of scope (correct as-is).

## Current Status

### By ROM

| ROM | Code `.byte` remaining | Status |
|-----|---------------------|--------|
| Main CPU (v9 / v10, each) | confirmed-region backlog 0 B + misframed islands (partly converted; not a fixed pool — see below) | **Not complete** |
| Main CPU (v7) | 236,713 B in 789 confirmed regions, plus 29,032 B in 2,456 misframed islands — the largest code-as-`.byte` debt in the project | **Not complete** |
| Sub CPU Payload | **0** | **Complete** |
| Sub CPU Boot | **0** | **Complete** |
| Table Data | **0** | **Complete** |
| Custom Data | **0** (data only) | **Complete** |
| HDAE5000 | 13,168 B | **Not complete** |
| SX-WSA1R `prom_a` / `prom_b` | **0** — byte runs audited and typed | **Complete** |
| SX-WSA1R `prom_c` / `prom_d` | **0** — survived a falsification attack | **Complete** |

The misframed islands in the Main CPU rows are left as `.byte` on purpose: fixing one means
re-framing an instruction already present in a neighbouring converted region, not filling a
gap, and this work requires a round-trip proof per region rather than a bulk relabel.
Converting a confirmed region creates new islands at its boundary, so the island count is
not a fixed pool — it moves with the tree state and should be re-measured, not quoted from
this page, before being used for planning.

`scripts/analysis/v9_v10_undisassembled_census.py` is the v9/v10 and v7 census; it needs a
scratch tree and is run as `--prepare`, then `--judge v7` and `--islands v7 --max-island 63`.
`hdae5000/tools/measure_debt.py` is the HDAE5000 one and prints to stdout with no arguments.

> **The HD-AE5000 figure rises as work lands, and that is correct.** Twelve regions of
> mis-disassembled data were retyped *back* into `.byte`, which moved the measurement up
> rather than down. A number that only ever falls would mean the instrument cannot see
> data-framed-as-code, which is the third kind of debt and the one the byte gate is blind to
> in both directions.

### Native instruction counts are not currently measured

There is no committed script that reports native instruction counts per image, and the
figures that used to sit in the table above (239,683 for the main CPU, 35,721, 1,357, 1,678
and 502 for the others) cannot be reproduced from anything in the repository — they predate
the LLVM toolchain. Two instruments do exist, and they measure different things, so they
cannot be combined into one column:

- `notes/syntax-convergence-probes/mnemonic_census.py --root v10/maincpu` counts
  **instruction statements** in a source tree: 336,011 for v10's main CPU. See
  [ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/#instruction-census).
- `llvm-mc -g` emits one DWARF line row per instruction statement and none for data, which
  gives a per-image count. Values on record in the disassembly repository's notes:
  HD-AE5000 **36,391**, custom data **0**, `wsa1/prom_c` **76,647**, `prom_d` **0**.

Whether to grow the second into a per-image reporter is an open question; until then this
page states debt, which is measured, rather than progress, which is not.

### LLVM Backend Encodings Added

All previously missing instruction encodings have been implemented in the LLVM TLCS-900 backend:

| Category | Prefix | Count Converted | LLVM Status |
|----------|--------|-----------------|-------------|
| JR/JRL/CALR branch instructions | `0x1E` etc. | 1,214 | **Fixed** (label-based) |
| Compact register loads (d8 prefix) | `0xD8-0xEF` | 2,680 reg-reg + 831 ALU/LD/BIT | **Implemented** |
| PrevBank (D7 prefix) | `0xD7` | 147 | **Implemented** |
| Memory R+d8 addressing | various | 3,616 | **Implemented** |
| Compact dst (CALL/JP/CPW/LD) | various | 1,038 | **Implemented** |
| Short LD (compact load) | `0x20-0x3F` | 523 | **Implemented** |
| Compact imm32 loads | various | 684 | **Implemented** |
| ld A, (R+d16) source loads | `0xC3` | ~970 | **Implemented** (Mar 14) |
| ld (R+d16), A stores | `0xF3` | ~400 | **Implemented** |
| Shifts/Rotates/MUL/DIV | various | 246 | **Implemented** |

### HDAE5000: not complete

`hdae5000/tools/measure_debt.py` counts **13,168 B** of undocumented `.byte`/`.word` operand
bytes — overwhelmingly scattered single-byte numeric fields rather than one contiguous block
— plus **3,815 B** more that carries a decoding comment but has not been converted to real
instructions. Against a 512 KB ROM that is 2.5 % debt and 96.8 % real source. Most remaining
`.byte` in the tree is genuine data (custom-filesystem templates — the HD-AE5000 filesystem
is *not* FAT16 — string constants, UI bitmaps, etc.), but these figures are not yet zero.
There are **0 B** of raw `.incbin` with no rebuild rule.

## Execution Plan

### Step 1: Precise Automated Audit

Write a Python script (`scripts/audit_byte_code.py`) that:
1. Parses all `.s` files across all ROMs
2. Identifies `.byte` sequences between native instructions (code context)
3. Attempts `llvm-mc --triple=tlcs900 --disassemble` on each sequence
4. Classifies results: (a) already decodable by LLVM → immediate conversion, (b) needs LLVM backend addition, (c) confirmed data
5. Groups code `.byte` by first byte (opcode prefix) to identify LLVM encoding families
6. Outputs a report with: file, line, bytes, category, status

### Step 2: Convert Already-Decodable Instructions

Some `.byte` sequences may already have LLVM support but were written as `.byte` historically. Convert them directly to native mnemonics using the disassembler output.

**Verification:** `make clean && make all` + `compare_roms.py` after each batch.

### Step 3: LLVM Backend — Compact Register Loads

Add encoding support for compact register load instructions:
- `ld wa, 0` (D8 A8), `ld xde, 0` (EA A8), `ld xwa, 1` (E8 A9), etc.
- These are 2-byte compact forms vs the 3-4 byte extended forms

### Step 4: LLVM Backend — Compact Stack Pointer Arithmetic

Add encoding support for:
- `dec N, xsp` (EF 6A/6E) — decrement stack pointer by N
- `inc N, xsp` (EF 62/66) — increment stack pointer by N

### Step 5: LLVM Backend — calr Fix

Fix `calr` with numeric address targets. Currently broken — emits absolute bytes instead of relative offset. Either fix the encoder to compute the relative offset, or add a new mnemonic variant.

### Step 6: LLVM Backend — F2 Immediate-to-Memory Stores

Add encoding support for the F2-prefix `ld (mem), imm` instructions that store immediate values to memory addresses. ~358 occurrences.

### Step 7: LLVM Backend — C3 R+d16 Source Loads

Add encoding support for `ld A, (R+d16)` source addressing (C3 prefix). ~216 occurrences. Note: the D3/E3/F3 destination variants already work; this is the source (load) direction.

### Step 8: LLVM Backend — Remaining D7 Prevbank

Add `cps qiz, 0` and any other prevbank instructions not yet supported (~4 occurrences for cps, ~182 total D7-prefix).

### Step 9: Batch Convert .byte → Native Mnemonics

After each LLVM backend addition (Steps 3-8), convert the corresponding `.byte` sequences in the disassembly to native instructions. Use Python scripts with binary I/O (Latin-1 safety policy). Verify byte match after each batch.

### Step 10: Disassemble FDC Raw Byte Blocks

The FDC routines in `maincpu/storage/fdc_routines.s` contain ~434 lines of raw `.byte` that are actual instruction sequences. These need:
1. Disassembly using `llvm-mc --disassemble` or `llvm-objdump`
2. Analysis of each routine's purpose
3. Semantic labeling (no `LABEL_XXXXXX` allowed)
4. Documentation header comments

### Step 11: Disassemble Flash/Floppy Handler Blocks

`maincpu/storage/flash_floppy_handlers.s` and `maincpu/storage/single_load.s` contain ~2,272 lines of raw byte blocks that need full disassembly, semantic labeling, and documentation.

### Step 12: Iterative Jump/Call Table Discovery & Disassembly

Newly disassembled code may reveal previously unidentified jump tables or call tables. These must be found and their targets disassembled, repeating until exhaustion:

1. **Scan** for undiscovered tables in all newly disassembled code blocks (sequences of `.long` values in ROM range, `lda`+`jp (xwa)` patterns, indexed dispatch)
2. **Verify** table entries are code targets (not already-disassembled or false positives)
3. **Disassemble** newly discovered code targets with semantic labeling and documentation
4. **Recurse** — newly disassembled code may contain more tables
5. **Terminate** when no new tables or code targets are found

**Scope:** All ROMs (maincpu, subcpu, hdae5000, table_data).

### Step 13: Final Verification & Website Sync

1. `make gate-all` — thirteen images byte-identical, or the change does not land
2. Run `scripts/sync_docs_labels.py --apply` to update any new labels on the website
3. Update `rom-reconstruction.md`

## Ordering & Priorities

**Do first:** Step 1 (audit) — gives precise scope for everything else.
**Then:** Steps 2 (free wins), 3-4 (easy LLVM additions, high impact).
**Then:** Steps 5-8 (harder LLVM work, each unblocks batch conversions).
**Then:** Steps 9-11 (conversion work, depends on LLVM additions).
**Then:** Step 12 (iterative table discovery — feeds back into Steps 9-11).
**Finally:** Step 13 (verification & sync).

Steps 3-8 are independent of each other and can be parallelized.
Step 12 is iterative and may cycle back through Steps 3-11.

## Verification

After each step:
- `cd kn5000-roms-disasm && make gate-all` — thirteen images, byte-exact or non-zero exit
- LLVM tests: `cd llvm-project && build/bin/llvm-lit llvm/test/CodeGen/TLCS900/`

> **Do not accept a percentage in place of the gate.** `compare_roms.py` prints
> `Similarity: 100.00%` rounded to two decimals, which in a 2 MB ROM covers up to 104
> differing bytes, and it silently skips any section whose built file is missing — so a run
> that never assembled the six ASL mirror sections prints nine sections, all reading
> `100.00%`, and looks identical to a passing full run. See
> [Disassembly Workflow]({{ site.baseurl }}/disassembly-workflow/#-never-gate-on-a-percentage).

## Policy Compliance

All newly disassembled code MUST:
1. Have semantic label names (no `LABEL_XXXXXX`)
2. Have documentation header comments explaining what each routine does
3. Be verified with byte-match builds before committing
4. Have website docs updated if labels appear on documentation pages
