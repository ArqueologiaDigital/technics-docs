---
layout: page
title: "LLVM TLCS-900: Semantic Instruction Migration"
permalink: /llvm-semantic-instructions/
---

# LLVM TLCS-900 Backend: Semantic Instruction Migration

The LLVM TLCS-900 backend originally used 118 custom "wrapper" mnemonics encoding raw addressing mode bytes. This page tracks the ongoing work to replace them with proper semantic instructions.

## Why This Matters

Wrapper mnemonics like `st_dri3b L, 0xfd, 0xb8, 0x01` are unreadable. The same instruction in standard TLCS-900 syntax is `lda xsp, (xsp+440)` — immediately clear that it's deallocating 440 bytes of stack frame. Semantic mnemonics make the disassembly comprehensible and cross-version diffs meaningful.

## Progress Summary

**Forty-one of the forty-three wrapper families are at zero. Two are not.**
`lda_dpi` and `bit_dri` still stand in the sources, and they are the hardest
kind: their operands are literal mode and displacement bytes
(`bit_dri 7, 0x07, 0xec, 0xf4`), so no rename reaches them until the operand
is modelled. Both are still defined in the backend
(`TLCS900InstrInfo.td`).

| Phase | Description | Instances (at time of scoping) | Status |
|-------|-------------|-----------|--------|
| Phase 1 | Mnemonic renames (81 mnemonics) | 53,603 | **Complete** |
| Phase 1b | Parenthesized direct addresses | 61,436 | **Complete** |
| Phase 2 | 24-bit addressing semantics | ~1,700 | **Complete** |
| Phase 3 | Extended register pair modes | ~3,300 | **Complete** |
| Phase 4 | SRI/DRI indirect modes | ~3,500 | **Two families remain** |
| Phase 5 | Miscellaneous | ~700 | **Complete** |

Sites remaining, counted over the 547 tracked `.s` files:

| Mnemonic | Total | v7 | v9 | v10 | v142 | hdae5000 | wsa1 | table_data |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `lda_dpi` | **669** | 135 | 187 | 187 | 9 | 11 | 138 | 2 |
| `bit_dri` | **189** | 33 | 68 | 68 | 11 | 9 | — | — |

Reproduce with `python3 tools/wrapper_mnemonic_census.py` in this repository,
which counts the leading mnemonic on every instruction line of
`git ls-files '*.s'` in the disassembly repository and prints the table above.
⚠ The sources are latin-1, not UTF-8 — decoding them as UTF-8, or running GNU
grep over them in a UTF-8 locale, can silently return zero matches on a file
that plainly contains the string.

The per-phase instance counts in the tables below are the counts from when each
phase was scoped, kept for context; apart from those two families they have not
been re-verified against the current tree.

## Completed Work

### Phase 1: Mnemonic Renames (Complete — March 2026)

81 wrapper mnemonics renamed to semantic forms across 53,603 instruction instances:

| Old | New | Category |
|-----|-----|----------|
| `push_sr` | `push sr` | Status register push/pop |
| `pop_sr` | `pop sr` | |
| `ld8_24` | `ldb_da` | Direct address loads |
| `st8_24` | `stb_da` | Direct address stores |
| `sti8_24` | `stib_da` | Direct address immediate stores |
| `ldto_berp` | `stb_erp` | Extended register pair |
| `ldfr_berp` | `ldb_erp` | |
| `st_dri3b` | `stb_dri` | Displacement register indirect |
| ... | ... | (81 total) |

### Phase 1b: Parenthesized Direct Address Syntax (Complete — March 2026)

Added `directaddr` operand class to LLVM backend. All 61,436 direct address operands across 155 `.s` files now use parenthesized syntax:

| Before | After |
|--------|-------|
| `ldb_da a, 0xe12345` | `ldb_da a, (0xe12345)` |
| `stw_da 0xe12345, wa` | `stw_da (0xe12345), wa` |
| `cpw_da 0x3ef50, 0` | `cpw_da (0x3ef50), 0` |
| `incdi8_24 1, 0xcee5` | `incdi8_24 1, (0xcee5)` |
| `bitda_24 3, 0xe12345` | `bitda_24 3, (0xe12345)` |

Changes:
- `TLCS900InstrInfo.td` — 167 instruction definitions updated to use `directaddr` operand class
- `TLCS900AsmParser.cpp` — Added `parseDirectAddrOperand()` for `(expr)` syntax
- `TLCS900InstPrinter.cpp` — Added `printDirectAddr()` to wrap output in parentheses
- Both old (bare) and new (parenthesized) syntax accepted for backward compatibility

## Phases 2-5

These tables record the mnemonics as originally scoped. Every wrapper mnemonic
listed in them has zero occurrences left in the KN5000 or SX-WSA1R trees
**except `lda_dpi` and `bit_dri`**, counted above. The semantic replacement
shapes were not individually re-audited here, so read these as "what was
migrated away from," not as a live inventory of current mnemonics.

### Phase 2: 24-bit Addressing Mode Semantics (~1,700 instances)

| Current | Semantic | Count | Status |
|---------|----------|-------|--------|
| `ld16_24 reg, addr` | `ld reg, (addr24)` | 645 | Complete |
| `ld32_24 reg, addr` | `ld reg, (addr24)` | 161 | Complete |
| `st16_24 addr, reg` | `ld (addr24), reg` | 252 | Complete |
| `st32_24 addr, reg` | `ld (addr24), reg` | 139 | Complete |
| `sti16_24 addr, imm` | `ld (addr24), imm16` | 209 | Complete |
| `cpi8_24 addr, imm` | `cp (addr24), imm8` | 63 | Complete |
| `cpdi16_24 addr, imm` | `cp (addr24), imm16` | 120 | Complete |

### Phase 3: Extended Register Pair Modes (~3,300 instances)

| Current | Semantic | Count | Status |
|---------|----------|-------|--------|
| `ldto_berp` | `ld (erp+off), val` | 1,251 | Complete |
| `ldfr_berp` | `ld val, (erp+off)` | 597 | Complete |
| `ldto_werp` | `ld (erp+off), val` | 459 | Complete |
| `ldfr_werp` | `ld val, (erp+off)` | 221 | Complete |
| `ldi_berp` | `ld (erp+off), imm` | 316 | Complete |
| `ldi_werp` | `ld (erp+off), imm` | 281 | Complete |
| `push_werp` / `pop_werp` | `push (erp)` / `pop (erp)` | 325 | Complete |
| `cpi_berp` / `cpi_werp` | `cp (erp+off), imm` | 260 | Complete |
| `inc1_berp` / `inc1_werp` | `inc 1, (erp+off)` | 281 | Complete |
| `cp_werp` / `cp_srib_im` | `cp (erp), val` | 184 | Complete |

### Phase 4: SRI/DRI Indirect Modes (~3,500 instances)

| Current | Semantic | Count | Status |
|---------|----------|-------|--------|
| `st_dri3b/w/l` | `ld (reg+d16), val` | 2,105 | Complete |
| `ld_srib3` / `ld_sriw3` | `ld val, (reg+d16)` | 1,073 | Complete |
| `lda_dri3` | `lda reg, (reg+d16)` | 396 | Complete |
| `lda_dpi` | `lda reg, (reg+d16)` | 164 | **Open** — 669 sites remain |
| `ld_spib` | `ld val, (xsp+d8)` | 129 | Complete |
| `jp_dri` | `jp (reg+d16)` | 240 | Complete |
| `stib_dri` / `stib_dpi` | `ld (reg+d16), imm` | 326 | Complete |
| `st_dpiw` / `stiw_dri` | `ld (reg+d16), imm16` | 120 | Complete |
| `bit_dri` | `bit n, (reg+d16)` | 68 | **Open** — 189 sites remain |

### Phase 5: Miscellaneous (~700 instances)

| Current | Semantic | Count | Status |
|---------|----------|-------|--------|
| `ld_srib` / `ld_sriw` | `ld val, (reg)` | 341 | Complete |
| `mrid2` | Various | 48 | Complete |
| `ldada` / `ldda8` / `stda8` | `ld` with direct addressing | ~200 | Complete |
| `addm32_24` / `addmi16` / etc. | `add (addr), imm` | ~100 | Complete |

## Assembly syntax: native LLVM mnemonics, with the form in the operand

The tree's source language is **native LLVM TLCS-900 mnemonics, with whatever a
form-selecting mnemonic used to encode moved into the operand** — the direction
the direct-address width suffix already established. MAME's `unidasm` is kept as
a second opinion, cited in trailing comments, and is never a source language.

That is a decision about what can carry a byte-identity gate, and it is measured
rather than argued. `unidasm`'s output renders more than one encoding with the
same text, so it cannot be assembled back:

| feeding unidasm's own text to this assembler | spellings | sites | share |
|---|---:|---:|---:|
| accepted, **correct** bytes | 36,280 | 701,697 | 66.9 % |
| accepted, **wrong** bytes — silent | 25,553 | **246,622** | **23.5 %** |
| rejected outright | 12,574 | 100,267 | 9.6 % |

The 9.6 % is cheap: spellings a parser could learn. The 23.5 % is
disqualifying, because nothing reports it. The direct proof is a count of
distinct byte strings that print as the same text, measured with its own control:

| notation | distinct texts | ambiguous texts | sites under them |
|---|---:|---:|---:|
| `unidasm` | 133,690 | **134** | 3,172 |
| this tree's LLVM text | 89,904 | **0** | 0 |

`ldirw` is both `93 11` and `95 11`; `ld W,0x00` is both `20 00` and
`c8 03 00`; `ret GE` is both `b0 f9` and `b6 f9`. Zero ambiguity on the LLVM
side is by design — the printer and the parser are one component and the byte
gate depends on their being inverse.

**The two decoders do not disagree about the machine.** Over 1,113,485
instruction sites, `unidasm` and this backend consume the same bytes every time
(`LEN_DIFFER = 0`, with a foil control that injects a one-byte lengthening every
seventh record and is detected 5,763 times). The mnemonic *text* differs at
333,866 sites — 30.0 % — and that difference is entirely notational.

What the divergence is made of, from the census over all 547 tracked `.s` files:

| bucket | sites | distinct names |
|---|---:|---:|
| a name `unidasm` also has | 1,034,935 | 71 |
| a backend name `unidasm` does not have | 265,116 | 459 |
| a `.macro` defined in this tree | 16,922 | 113 |

Retiring the 459 synthetic names splits three ways, and the split is what makes
the work stageable:

1. **The name carries a form the operand can already express.** 81,858 sites
   across 71 mnemonics (`ldb_d8`, `stdi8`, `stb_d8`, `ldw_d16`, `stda16`, …)
   assemble to the ROM's exact bytes today under the native spelling plus a
   width annotation, with no backend change. `incm` → `incw` (1,535 sites) and
   `ldda32 xwa, 4160` → `ld xwa, (4160:16)` (4,991 sites) are done.
2. **The name selects between two legal encodings.** 78,364 sites over nine
   mnemonics. These cannot be renamed until the operand syntax can say which
   form — see [the size/form families]({{ site.baseurl }}/tlcs900-instruction-encoding/#two-legal-encodings-one-operation-the-sizeform-families)
   and the three backend features below.
3. **Byte emitters wearing a mnemonic's name.** 98 names, 22,135 sites, whose
   `$b0,$b1,$b2` operands are literal bytes rather than modelled operands
   (`add_sril_rm xix, 7, 236, 232`). No rename reaches these; the operand has to
   be modelled first, and the backend deliberately makes an unmodelled
   `(xix+iz)` a **parse error** rather than guessing.

### The three backend features that would retire the form selectors

| feature | covers | what it adds |
|---|---|---|
| **A — immediate field width** | `cps`, `lds`, `lds32` — 52,064 sites | a `:3` / `:8` / `:16` / `:32` suffix on an *immediate*, exactly parallel to `(addr:16)` on a direct address: `cp a, 4:3` → `c9 dc`, `cp a, 4:8` → `c9 cf 04`. Also retires `lds8`/`lds`/`lds32` as three names for one operation, since the register class already carries the size |
| **B — naming the alternative encoding** | `ldb`, `ldio`, `ldwio` — 19,603 sites | a suffix that names the *encoding* rather than a width, because both forms carry an immediate of the same width. Each family has exactly two legal encodings |
| **C — a `PrevGR8` register class** | `stb_erp`, `ldb_erp` — 6,697 sites | the 8-bit counterpart of the existing `PrevGR16` (`QWA`–`QSP`), so the C7-prefix byte forms take a register name instead of a raw code byte. 42 and 45 distinct codes are in use; naming them also normalises the `0xFB` / `0xfb` / `251` spellings the sources currently mix |

⚠ **Feature A's default must stay the long form.** 2,658 `cp Xrr, n` and 53
`ld Xrr, n` sites in the tree have an immediate of 0–7 and use the long
encoding anyway. An assembler rule of "pick the short form when it fits" would
silently rewrite every one of them.

⚠ **Feature B's suffix must not be defined as "the shortest form."** That is a
derived property; the day a third encoding is added, every existing use silently
means something else. It has to name an explicit per-instruction alternative
recorded in the `.td`.

Feature A would also retire the `(Xrr+0)` sentinel, in which a displacement
written as **256** means "force the d8 form with displacement 0" — 1,132 sites
carry it, spelled `256` (931), `0x0100` (200) and `0x100` (1), so a text match
undercounts by 201. `(xix+0:8)` would say the same thing in the idiom the rest
of the backend already uses.

Sources for every figure above:
`notes/ASSESSMENT-syntax-convergence-2026-09-02.md` and
`notes/TRIAGE-size-form-mnemonics-2026-09-02.md` in the disassembly repository,
with the scripts in `notes/syntax-convergence-probes/`
(`mnemonic_census.py`, `oracle_ab.py`, `diff_causes.py`,
`native_convergence.py`, `size_family_convert.py --triage`).

### The printer still emits the retired names

A conversion in the sources is only half a fix. `incm` and `ldda32` are gone
from the `.s` files, but the disassembler still *prints* them, so any region
disassembled from here on reintroduces the spellings — and the tree grows by
disassembly. Two backend changes close it and neither can move a byte: giving
`INC16m`'s `InstAlias` a zero emit priority (its own `AsmString` is already
`incw`), and giving `LD32_da16` the `AsmString` `ld` with `AddrBytes = 2` set on
the operand so the printer emits the `:16` it already knows how to print.

## Architecture

The LLVM TLCS-900 backend lives at `/home/fsanches/compartilhado/llvm-project/llvm/lib/Target/TLCS900/`.

**Key files:**
- `TLCS900InstrFormats.td` — 83 instruction format class definitions (1,093 lines; was 79 formats when this page was first written)
- `TLCS900InstrInfo.td` — 5,521 lines of instruction definitions
- `TLCS900BaseInfo.h` — TSFlags bit-field definitions (283 lines)
- `AsmParser/TLCS900AsmParser.cpp` — 569 lines, including the direct-address width-request parser (see below)
- `MCTargetDesc/TLCS900MCCodeEmitter.cpp` — 1,657 lines, manual encoding
- `Disassembler/TLCS900Disassembler.cpp` — 2,920 lines, manual decoding, including the register-indexed `SriRR*` family and the `ERP` (extended register pair) prefix forms (see below)

**Encoding strategy:** The backend uses manual encoding via a giant `switch(Format)` in `MCCodeEmitter::encodeInstruction()`, NOT auto-generated TableGen encoding. Each of the 83 format classes has a dedicated switch case that emits bytes using TSFlags metadata.

**TSFlags layout (32 bits, unchanged since this page was written):**
```
[6:0]   InstFormat  — selects encoding strategy (83 values in use; field holds up to 128)
[14:7]  Opcode      — primary prefix/opcode byte
[16:15] OpSize      — 0=8-bit, 1=16-bit, 2=32-bit
[17]    AddrWidth   — 0=16-bit addr, 1=24-bit addr
[20:18] RegIdx      — block transfer register index
[28:21] SubOpcode   — secondary operation byte
[31:29] NumPreOps   — pre-SubOpcode operand count
```

## Direct-address width-request syntax

A direct-address operand takes an optional explicit width suffix —
`(0x8a:8)`, `(0x2075:16)`, `(0x8a:24)` — parsed by
`parseDirectAddrOperand()` in `AsmParser/TLCS900AsmParser.cpp`. The TLCS-900
has three direct-address widths and picks between them in the prefix byte, so
the width is a spelling choice the source has to make: this firmware writes
`set 7,(0x00008a)` as `F2 8A 00 00 BF` for an address that fits in eight
bits, so the width is **not derivable from the address value alone**. An
operand with no suffix keeps the 24-bit default.

## Register-indexed and extended-register-pair decoding

The disassembler decodes two families that the assembler has always
encoded correctly but that had no decoder path: the register-indexed
`SriRR*` group (`st_rr*`, `ld_rr*`, `lda_rr`, `jp_rr`, `call_rr`, mode
bytes `07`/`03`) and the `ERP` (extended register pair) byte/long forms
(`decodeERPPrefix()`, prefix bytes `C7`/`E7`). Both are exercised by the
regression suite against literal bytes pulled from `kn5000_v10_program.rom`
and `wsa1/original_ROMs/wsa1_prom_a.ic12`, and both are what let the KN5000
and WSA1R disassembly trees name instructions that used to sit as
undecoded `.byte` runs purely because no decoder case existed for the mode
byte, not because the bytes were unclear.

## Encoding subtleties this backend gets right

A handful of forms look ambiguous or interchangeable but are not; each is
covered by a regression test tied to real ROM bytes rather than a
hand-picked example.

- A direct-memory operand can be requested at 8, 16, or 24-bit width —
  `(0x8a:8)`, `(0x2075:16)`, `(0x8a:24)` — because the TLCS-900 picks the
  width in the prefix byte and it is **not derivable from the address value
  alone**: this firmware writes `set 7,(0x00008a)` as `F2 8A 00 00 BF` for an
  address that fits in eight bits. An operand with no suffix keeps the
  24-bit default.
- `push (addr)` and `mul reg,(addr)` each take a genuine memory operand, not
  an immediate — `push (0x1234)` and `mul WA,(0x1234)` are distinct from
  their immediate counterparts and encode to their own byte forms.
- The 8-bit **INDEX register**'s file address is `A=0xE0` (not `0xE1`); the
  register file is byte-addressed and little-endian, so a word register's
  low half sits at offset 0.
- The direct-address ALU family (`addda16`/`subda16`/…/`cpda16` and the
  `_da24`/mem-dest siblings) takes a 32-bit GPR operand — spell it
  `addda16 xwa, (4160)`, not `addda16 wa, (4160)` — because every one of
  those instructions' TableGen definition is 32-bit regardless of the
  mnemonic's `16`/`24` suffix.
- `(Xrr+d8)` is **signed**. A displacement written as `+151` does not fit
  the signed 8-bit field and legitimately assembles to the 5-byte
  `(Xrr+d16)` form instead — `+151` and `-105` are different addresses, not
  two spellings of the same byte. To reproduce a raw disp8 byte `0x97` in
  the 2-byte encoding, write the signed form `-105`.

The pinned toolchain commit is recorded in the disassembly repository's
`TOOLCHAIN_VERSION` file, which is the authority — read it rather than quoting a
hash from here. It also carries the byte-level proofs and the `make gate-all`
verification across all thirteen KN5000 and SX-WSA1R images.

## Process for Each Phase

1. **Define new instruction in `.td`** with semantic mnemonic and proper operand types
2. **Add encoding case** in `MCCodeEmitter.cpp` (or reuse existing format)
3. **Add decoding case** in `TLCS900Disassembler.cpp` to emit semantic mnemonic
4. **Build LLVM:** `ninja -C /home/fsanches/compartilhado/llvm-project/build llc llvm-mc`
5. **Update all `.s` files** in every tree that uses the mnemonic — the three KN5000 maincpu versions, the sub-CPU, HD-AE5000 and the four SX-WSA1R images (Python script with binary I/O)
6. **Rebuild ROMs:** `make gate-all` — all thirteen images byte-identical, or the change does not land
7. **Run LLVM tests:** `build/bin/llvm-lit llvm/test/CodeGen/TLCS900/`

## See Also

- [TLCS-900 Instruction Encoding]({{ site.baseurl }}/tlcs900-instruction-encoding/) — Hardware instruction format reference
- [ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/) — Disassembly progress
- [Source Code Map]({{ site.baseurl }}/source-map/) — Guide to every source file
