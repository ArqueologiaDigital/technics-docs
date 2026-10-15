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

**Thirty-eight of the forty-three wrapper families are at zero.** `lda_dpi`
left the tree on 2026-09-25, when the sources were respelled to the real
`(R+)` / `(-R)` operand (disassembly `166c9dc3e`). The backend then deleted
the pseudo (llvm `bcb142d6ee97`): `lda_dpi xbc, 232` was really
`ld (XDE+),A`. `bit_dri` is down to 12 sites, `bit n, (XHL+A)` and
`bit n, (XHL+C)` (mode byte `0x03`, an 8-bit index register). The parser
accepts that operand only on LD (`ld a, (xhl+a)` = `c3 03 ec e0 21`), not on
BIT, and the decoder rejects the BIT bytes, so `bit_dri` is still defined in
`TLCS900InstrInfo.td`. The four extended-register LD families `ldto_berp` /
`ldfr_berp` / `ldto_werp` / `ldfr_werp` are nonzero because they are the live
spelling again. On 2026-09-25 the backend found that the old names
`stb_erp` / `ldb_erp` and their word-form twins named the direction backwards
(llvm `ff454781b90e`), and the sources were respelled to the ldto/ldfr names
(disassembly `c71a6d512`, 9,929 lines). The byte forms take a register-file
code byte that no register name covers yet (Feature C below). Most word-form
sites do not need that: 1,846 of their 2,092 sites use the Q-register codes `0xE2`-`0xFA`,
which the backend already names (`ld wa, qiz` = `d7 fa 88`, the bytes of
`ldto_werp wa, 0xfa`). The other 246 use bank-3 codes (`0x30`-`0x3E`).

| Phase    | Description                     | Instances (at time of scoping) | Status                                                                                                                                                                                                                                                                                        |
|----------|---------------------------------|--------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Phase 1  | Mnemonic renames (81 mnemonics) | 53,603                         | **Complete**                                                                                                                                                                                                                                                                                  |
| Phase 1b | Parenthesized direct addresses  | 61,436                         | **Complete**                                                                                                                                                                                                                                                                                  |
| Phase 2  | 24-bit addressing semantics     | ~1,700                         | **Complete**                                                                                                                                                                                                                                                                                  |
| Phase 3  | Extended register pair modes    | ~3,300                         | **Not complete**: the C7 byte-register forms are still wrapper mnemonics (`ldto_berp`, `ldfr_berp`, `ldib_erp`, `cp_erpb`, `inc1b_erp`, …; see Feature C), and the D7 word forms keep wrapper names although their Q-register codes already have a native spelling (`ld wa, qiz`, `push qiz`) |
| Phase 4  | SRI/DRI indirect modes          | ~3,500                         | **One family remains** (`bit_dri`, 12 sites)                                                                                                                                                                                                                                                  |
| Phase 5  | Miscellaneous                   | ~700                           | **Complete**                                                                                                                                                                                                                                                                                  |

Sites remaining at disassembly `3417969c0`, counted over the 550 tracked `.s` files:

| Mnemonic    | Total | v7    | v9    | v10   | v142 | hdae5000 | wsa1 | table_data | subcpu boot |
|-------------|------:|------:|------:|------:|-----:|---------:|-----:|-----------:|------------:|
| `ldto_berp` | 5,211 | 1,575 | 1,635 | 1,635 |  340 |       10 |    — |         12 |           4 |
| `ldfr_berp` | 2,655 |   818 |   836 |   836 |  119 |       12 |   26 |          7 |           1 |
| `ldto_werp` | 1,386 |   363 |   467 |   467 |   64 |        6 |    — |         16 |           3 |
| `ldfr_werp` |   706 |   197 |   229 |   229 |   46 |        1 |    — |          3 |           1 |
| `bit_dri`   |    12 |     4 |     4 |     4 |    — |        — |    — |          — |           — |

Reproduce with `python3 tools/wrapper_mnemonic_census.py` in this repository,
which counts the leading mnemonic on every instruction line of
`git ls-files '*.s'` in the disassembly repository and prints the table above.
⚠ The sources are latin-1, not UTF-8 — decoding them as UTF-8, or running GNU
grep over them in a UTF-8 locale, can silently return zero matches on a file
that plainly contains the string.

The per-phase instance counts in the tables below are the counts from when each
phase was scoped, kept for context; apart from the five families counted above
they have not been re-verified against the current tree.

## Completed Work

### Phase 1: Mnemonic Renames (Complete — March 2026)

81 wrapper mnemonics renamed to semantic forms across 53,603 instruction instances:

| Old         | New                                                                                            | Category                        |
|-------------|------------------------------------------------------------------------------------------------|---------------------------------|
| `push_sr`   | `push sr`                                                                                      | Status register push/pop        |
| `pop_sr`    | `pop sr`                                                                                       |                                 |
| `ld8_24`    | `ldb_da`                                                                                       | Direct address loads            |
| `st8_24`    | `stb_da`                                                                                       | Direct address stores           |
| `sti8_24`   | `stib_da`                                                                                      | Direct address immediate stores |
| `ldto_berp` | `stb_erp` (reversed 2026-09-25: the name read the direction backwards; `ldto_berp` is current) | Extended register pair          |
| `ldfr_berp` | `ldb_erp` (reversed 2026-09-25; `ldfr_berp` is current)                                        |                                 |
| `st_dri3b`  | `stb_dri`                                                                                      | Displacement register indirect  |
| ...         | ...                                                                                            | (81 total)                      |

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
**except `bit_dri` and the four extended-register LD families**, counted
above. The semantic replacement shapes were not individually re-audited here,
so read these as "what was migrated away from," not as a live inventory of
current mnemonics.

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

| Current                   | Semantic                                                     | Count | Status                                          |
|---------------------------|--------------------------------------------------------------|-------|-------------------------------------------------|
| `ldto_berp`               | `ld r, <byte register by code>` (`c7 fb 89` = `ld A,QIZH`)   | 1,251 | **Live spelling**: 5,211 sites; needs Feature C |
| `ldfr_berp`               | `ld <byte register by code>, r` (`c7 fb 99` = `ld QIZH,A`)   | 597   | **Live spelling**: 2,655 sites                  |
| `ldto_werp`               | `ld rr, <word register by code>` (`d7 30 88` = `ld WA,RWA3`) | 459   | **Live spelling**: 1,386 sites                  |
| `ldfr_werp`               | `ld <word register by code>, rr` (`d7 30 98` = `ld RWA3,WA`) | 221   | **Live spelling**: 706 sites                    |
| `ldi_berp`                | `ld (erp+off), imm`                                          | 316   | Complete                                        |
| `ldi_werp`                | `ld (erp+off), imm`                                          | 281   | Complete                                        |
| `push_werp` / `pop_werp`  | `push (erp)` / `pop (erp)`                                   | 325   | Complete                                        |
| `cpi_berp` / `cpi_werp`   | `cp (erp+off), imm`                                          | 260   | Complete                                        |
| `inc1_berp` / `inc1_werp` | `inc 1, (erp+off)`                                           | 281   | Complete                                        |
| `cp_werp` / `cp_srib_im`  | `cp (erp), val`                                              | 184   | Complete                                        |

### Phase 4: SRI/DRI Indirect Modes (~3,500 instances)

| Current                 | Semantic                                                     | Count | Status                                                                                                                                                      |
|-------------------------|--------------------------------------------------------------|-------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `st_dri3b/w/l`          | `ld (reg+d16), val`                                          | 2,105 | Complete                                                                                                                                                    |
| `ld_srib3` / `ld_sriw3` | `ld val, (reg+d16)`                                          | 1,073 | Complete                                                                                                                                                    |
| `lda_dri3`              | `lda reg, (reg+d16)`                                         | 396   | Complete                                                                                                                                                    |
| `lda_dpi`               | misnamed: `lda_dpi xbc, 232` was `ld (XDE+),A`               | 164   | **Complete**: the tree writes the real `(R+)` / `(-R)` operand (disassembly `166c9dc3e`), and the backend deleted the pseudo on 2026-09-25 (`bcb142d6ee97`) |
| `ld_spib`               | `ld val, (xsp+d8)`                                           | 129   | Complete                                                                                                                                                    |
| `jp_dri`                | `jp (reg+d16)`                                               | 240   | Complete                                                                                                                                                    |
| `stib_dri` / `stib_dpi` | `ld (reg+d16), imm`                                          | 326   | Complete                                                                                                                                                    |
| `st_dpiw` / `stiw_dri`  | `ld (reg+d16), imm16`                                        | 120   | Complete                                                                                                                                                    |
| `bit_dri`               | `bit n, (XHL+A)` / `bit n, (XHL+C)` (register + 8-bit index) | 68    | **Open**: 12 sites remain; the parser takes the `(Xrr+r8)` operand on LD only, not on BIT                                                                   |

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

What the divergence was made of on 2026-09-02, from the census over the 547
tracked `.s` files of that day:

| bucket | sites | distinct names |
|---|---:|---:|
| a name `unidasm` also has | 1,034,935 | 71 |
| a backend name `unidasm` does not have | 265,116 | 459 |
| a `.macro` defined in this tree | 16,922 | 113 |

The same census at disassembly `3417969c0`, over 550 files, counts 1,275,163
sites under 75 shared names, 43,347 under 220 synthetic names and 29,563 under
125 macros.

Retiring the 459 synthetic names of 2026-09-02 splits three ways, and the split
is what makes the work stageable:

1. **The name carries a form the operand can already express.** 81,858 sites
   across 71 mnemonics (`ldb_d8`, `stdi8`, `stb_d8`, `ldw_d16`, `stda16`, …)
   assemble to the ROM's exact bytes today under the native spelling plus a
   width annotation, with no backend change. `incm` → `incw` (1,535 sites) and
   `ldda32 xwa, 4160` → `ld xwa, (4160:16)` (4,991 sites) are done.
   `incm` has since come back at 34 sites (29 of them in v7), all in regions
   disassembled on 2026-09-25 before backend `910b50efab49` stopped the
   printer emitting it; the alias still parses, so they assemble.
2. **The name selects between two legal encodings.** 78,364 sites over nine
   mnemonics on 2026-09-02. These could not be renamed until the operand syntax
   could say which form. It can now: the backend parses the encoding selectors
   `:i3`, `:opc` and `:io` since `adfbb55cf835` (2026-09-04), the sources were
   respelled with them, and the legacy names were deleted on 2026-09-05
   (`da00420dba8d`) — see [the size/form families]({{ site.baseurl }}/tlcs900-instruction-encoding/#two-legal-encodings-one-operation-the-sizeform-families)
   and the three backend features below.
3. **Byte emitters wearing a mnemonic's name.** 98 names and 22,135 sites on
   2026-09-02; 46 names and 3,301 sites at `3417969c0` by the same census
   (largest `inc1b_erp` 960, `popw_erp` 509, `pushw_erp` 500). Their operands
   are written as literal bytes. The byte-register forms need the operand
   modelled first (`inc 1, qizh` is rejected). The word forms on the Q
   registers already have a native spelling with the same bytes
   (`push qiz` = `d7 fa 04`, the bytes of `pushw_erp 0xfa`), so those are a
   rename away. The register-indexed `(xix+iz)`, once a deliberate parse error,
   has been modelled on every memory operation since backend `a3a81863f87d`
   (2026-10-02).

### The three backend features for the form selectors

| feature                                 | covers                                                                                             | status                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
|-----------------------------------------|----------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **A — immediate field width**           | `cps`, `lds`, `lds32`                                                                              | **Done.** The `:i3` selector: `cp a, 4:i3` → `c9 dc`, untagged `cp a, 4` → `c9 cf 04` (parser since backend `adfbb55cf835`, 2026-09-04)                                                                                                                                                                                                                                                                                                                                                                                                                                |
| **B — naming the alternative encoding** | `ldb`, `ldio`, `ldwio`                                                                             | **Done.** The `:opc` and `:io` selectors: `ld d, 4:opc` → `24 04`, `ld (0x07:8), 0xff:io` → `08 07 ff`. The nine legacy names were deleted on 2026-09-05 (`da00420dba8d`); the sources carry 71,239 selector uses at disassembly `3417969c0`                                                                                                                                                                                                                                                                                                                           |
| **C — a `PrevGR8` register class**      | `ldto_berp`, `ldfr_berp` (named `stb_erp`/`ldb_erp` until 2026-09-25) — 7,866 sites at `3417969c0` | **Open.** An 8-bit counterpart of the existing `PrevGR16` (`QWA`–`QSP`; the backend's "Prev" is a misnomer, since the Q registers are the upper halves of the current registers), so the C7-prefix byte forms take a register name instead of a raw code byte. It must name more than the Q bytes (`0xFB` = `QIZH`): the sites also use the index registers' low bytes (`0xF0`/`0xF1`/`0xF4`/`0xF8`/`0xF9`, IXL…IZH) and bank-3 bytes (`0x31`, `0x34`, `0x38`, `0x3C`, `0x3D`). Naming them would also normalise the `0xFB` / `0xfb` / `251` spellings the sources mix |

⚠ **Feature A's default must stay the long form.** 2,658 `cp Xrr, n` and 53
`ld Xrr, n` sites in the tree have an immediate of 0–7 and use the long
encoding anyway. An assembler rule of "pick the short form when it fits" would
silently rewrite every one of them.

⚠ **Feature B's suffix must not be defined as "the shortest form."** That is a
derived property; the day a third encoding is added, every existing use silently
means something else. It has to name an explicit per-instruction alternative
recorded in the `.td`.

The `(Xrr+0)` sentinel is retired. A displacement written as 256 used to mean
"force the d8 form with displacement 0". Backend `24782ed406f3` (2026-09-25)
made 256 an ordinary displacement, and the sources now write the d8-with-zero
form as `(xix+0:8)`: 1,044 sites at `3417969c0`, respelled in disassembly
`ff9bdf682`.

Sources for every figure above:
`notes/ASSESSMENT-syntax-convergence-2026-09-02.md` and
`notes/TRIAGE-size-form-mnemonics-2026-09-02.md` in the disassembly repository,
with the scripts in `notes/syntax-convergence-probes/`
(`mnemonic_census.py`, `oracle_ab.py`, `diff_causes.py`,
`native_convergence.py`, `size_family_convert.py --triage`).

### The printer no longer emits the retired names

Both printer gaps this section used to list were closed in backend
`910b50efab49` (2026-09-25). The legacy memory-form aliases (`incm`, `pushm`,
`bitm`, …) became parse-only, and direct-address forms are decoded through the
ordinary memory-operand table, so `e1 40 10 20` prints as `ld xwa, (4160:16)`
and `d2 00 80 00 61` as `incw 1, (32768:24)`. The fix came a few hours too late
for 34 `incm` lines: regions disassembled earlier that day, with the old
printer, brought them back. They still assemble because the alias still
parses.

## Architecture

The LLVM TLCS-900 backend lives at `llvm/lib/Target/TLCS900/` on the `tlcs900_backend` branch of [felipesanches/llvm-project](https://github.com/felipesanches/llvm-project/tree/tlcs900_backend). The commit the disassembly is built with is named in its `TOOLCHAIN_VERSION`. ⚠ As of 2026-10-15 that commit (`a3a81863f87d`, 2026-10-02) has not been pushed: the public branch stops at `86332721969d` (2026-09-02), 32 commits earlier, before the `:i3`/`:opc`/`:io` selector parser (`adfbb55cf835`), so its build cannot assemble the current sources.

**Key files** (counts at backend `a3a81863f87d`):
- `TLCS900BaseInfo.h` — the InstFormat enum (88 values) and the TSFlags bit-field definitions (417 lines)
- `TLCS900InstrFormats.td` — the instruction format classes (1,159 lines)
- `TLCS900InstrInfo.td` — 5,738 lines of instruction definitions
- `AsmParser/TLCS900AsmParser.cpp` — 1,427 lines, including the direct-address width-request parser and the encoding-selector parser
- `MCTargetDesc/TLCS900MCCodeEmitter.cpp` — 1,853 lines, manual encoding
- `Disassembler/TLCS900Disassembler.cpp` — 3,226 lines, manual decoding, including the register-indexed `SriRR*` family and the `ERP` prefix forms (see below)

**Encoding strategy:** The backend uses manual encoding via a giant `switch(Format)` in `MCCodeEmitter::encodeInstruction()`, NOT auto-generated TableGen encoding. Each of the 88 format values has a dedicated switch case that emits bytes using TSFlags metadata.

**TSFlags layout (32 bits, unchanged since this page was written):**
```
[6:0]   InstFormat  — selects encoding strategy (88 values in use; field holds up to 128)
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
- The 8- and 16-bit direct-address ALU forms take their real register and a
  width suffix: `add wa, (4160:16)` is `d1 40 10 80`. The old GPR-typed
  pseudos (`addda16`, `cpda16`, `cpda8 xbc, …`, …) took a 32-bit register
  encoded by index, so `cpda8 xbc, (8990)` assembled `cp A,(0x231e)`. They
  were deleted on 2026-09-25 (backend `bcb142d6ee97`): `addda16 xwa, (4160)`
  is now an unrecognized mnemonic and `cpda8 xbc, (8990)` an invalid operand.
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
4. **Build LLVM:** `ninja -C build llc llvm-mc` (from the llvm-project checkout)
5. **Update all `.s` files** in every tree that uses the mnemonic: the three KN5000 main-CPU versions, the sub-CPU payload and boot ROM, table data, HD-AE5000 and the SX-WSA1R images. The sources are latin-1. Where the new spelling needs a new assembler, the tree and the `TOOLCHAIN_VERSION` pin move in one commit.
6. **Rebuild ROMs:** `make gate-all` — all thirteen images byte-identical, or the change does not land
7. **Run LLVM tests:** `build/bin/llvm-lit llvm/test/MC/TLCS900/ llvm/test/MC/Disassembler/TLCS900/ llvm/test/CodeGen/TLCS900/`

## See Also

- [TLCS-900 Instruction Encoding]({{ site.baseurl }}/tlcs900-instruction-encoding/) — Hardware instruction format reference
- [ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/) — Disassembly progress
- [Source Code Map]({{ site.baseurl }}/source-map/) — Guide to every source file
