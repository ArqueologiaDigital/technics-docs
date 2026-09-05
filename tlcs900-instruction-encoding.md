---
layout: page
title: TLCS-900/H Instruction Encoding Reference
permalink: /tlcs900-instruction-encoding/
---

# TLCS-900/H Instruction Encoding Reference

This page documents the instruction encoding format of the Toshiba TLCS-900/H2 CPU (TMP94C241F) as used in the Technics KN5000. This reference was built through systematic reverse engineering of the KN5000 firmware ROMs and verification against both the MAME disassembler (`unidasm`) and our custom LLVM TLCS-900 backend.

## Overview

TLCS-900/H instructions are variable-length (1–7 bytes) using a prefix-based encoding system. The first byte determines the instruction category, operand size, and addressing mode. Subsequent bytes encode the operation (sub-opcode), register operands, displacements, and immediates.

## Register Encoding

All register classes share a consistent 3-bit encoding (0–7):

| Enc | 8-bit | 16-bit | 32-bit (GPR) | Address Reg | Q Reg (PrevBank) |
|-----|-------|--------|--------------|-------------|------------------|
| 0   | W     | WA     | XWA          | XWA         | QWA              |
| 1   | A     | BC     | XBC          | XBC         | QBC              |
| 2   | B     | DE     | XDE          | XDE         | QDE              |
| 3   | C     | HL     | XHL          | XHL         | QHL              |
| 4   | D     | IX     | XIX          | XIX         | QIX              |
| 5   | E     | IY     | XIY          | XIY         | QIY              |
| 6   | H     | IZ     | XIZ          | XIZ         | QIZ              |
| 7   | L     | SP     | XSP          | XSP         | QSP              |

**Note:** SP (enc=7) is not a member of the GR8 or GR16 register classes. Instructions that specify a GR8/GR16 operand cannot use SP/L as the operand.

## Instruction Format Categories

### 1. Compact 32-bit Immediate Loads (0x40–0x47)

5-byte instructions that load a 32-bit immediate into a GPR register.

```
Byte:   [0x40+R] [imm_lo] [imm_b1] [imm_b2] [imm_hi]
```

- `R` = register encoding (0–7)
- Immediate is 32 bits, little-endian

Example: `ld xbc, 0x01E0007F` → `41 7F 00 E0 01`

### 2. Register Source Prefix (0xC8–0xEF)

2-byte minimum instructions where the first byte encodes a source register and operand size, and the second byte is a sub-opcode that determines the operation and destination.

```
Byte:   [prefix] [sub_opc]
```

| Prefix Range | Operand Size | Source Register |
|-------------|-------------|-----------------|
| 0xC8–0xCF   | 8-bit       | R = prefix − 0xC8 |
| 0xD8–0xDF   | 16-bit      | R = prefix − 0xD8 |
| 0xE8–0xEF   | 32-bit      | R = prefix − 0xE8 |

#### Register-to-Register Sub-Opcode Table

The sub-opcode byte encodes both the operation and the destination register:

| Sub-Opc Range | Operation | Format | Direction |
|--------------|-----------|--------|-----------|
| 0x04         | PUSH r    | Unary (16-bit only) | — |
| 0x05         | POP r     | Unary (16-bit only) | — |
| 0x06         | CPL r     | Unary | — |
| 0x07         | NEG r     | Unary | — |
| 0x12         | EXTZ r    | Unary (16-bit only) | — |
| 0x13         | EXTS r    | Unary (16-bit only) | — |
| 0x20+d       | LD d, r   | LD to register | d ← r |
| 0x28+d       | LD r, d   | LD from register (reverse) | r ← d |
| 0x40+d       | MUL d, r  | Multiply (16→32, uses GPR names) | — |
| 0x48+d       | MULS d, r | Multiply signed | — |
| 0x50+d       | DIV d, r  | Divide (32/16, uses GPR names) | — |
| 0x58+d       | DIVS d, r | Divide signed | — |
| 0x60+n       | INC n, r  | Increment by n (1–7) | — |
| 0x68+n       | DEC n, r  | Decrement by n (1–7) | — |
| 0x78+cc      | SCC cc, r | Set if condition code | — |
| 0x80+d       | ADD d, r  | Add | d ← d + r |
| 0x88+d       | LD d, r   | Load (alternate encoding) | d ← r |
| 0x90+d       | ADC d, r  | Add with carry | d ← d + r + C |
| 0x98+d       | LD r, d   | Load reverse | r ← d |
| 0xA0+d       | SUB d, r  | Subtract | d ← d − r |
| 0xA8+n       | ld r, n:i3 | Load small immediate (0–7) | r ← n |
| 0xB0+d       | SBC d, r  | Subtract with borrow | d ← d − r − C |
| 0xC0+d       | AND d, r  | Bitwise AND | d ← d & r |
| 0xD0+d       | XOR d, r  | Bitwise XOR | d ← d ^ r |
| 0xD8+n       | cp r, n:i3 | Compare small immediate (0–7) | r − n |
| 0xE0+d       | OR d, r   | Bitwise OR | d ← d \| r |
| 0xF0+d       | CP d, r   | Compare | d − r |

Where `d` = destination register encoding (3 bits), `r` = source register from prefix, `n` = small immediate (3 bits), `cc` = condition code (4 bits).

**LD encoding note:** Two encodings exist for register-to-register LD: sub-opcode 0x88+d and 0x20+d (for `LD d, r`), and 0x98+d and 0x28+d (for `LD r, d`). Both forms are semantically identical but produce different byte sequences. The LLVM assembler always uses the 0x88/0x20 forms.

#### Register Prefix + Immediate

When the sub-opcode indicates an immediate operand, additional bytes follow:

```
Byte:   [prefix] [sub_opc] [imm_bytes...]
```

| Sub-Opc | Operation | Imm Size (8-bit/16-bit/32-bit prefix) |
|---------|-----------|--------------------------------------|
| 0x03    | LD r, #imm | 1 / 2 / 4 bytes |
| 0xC8    | ADD r, #imm | 1 / 2 / 4 bytes |
| 0xC9    | ADC r, #imm | 1 / 2 / 4 bytes |
| 0xCA    | SUB r, #imm | 1 / 2 / 4 bytes |
| 0xCB    | SBC r, #imm | 1 / 2 / 4 bytes |
| 0xCC    | AND r, #imm | 1 / 2 / 4 bytes |
| 0xCD    | XOR r, #imm | 1 / 2 / 4 bytes |
| 0xCE    | OR r, #imm | 1 / 2 / 4 bytes |
| 0xCF    | CP r, #imm | 1 / 2 / 4 bytes |

**Shift/rotate sub-opcodes** (1-byte immediate count):

| Sub-Opc | Operation |
|---------|-----------|
| 0xE8    | RLC count, r |
| 0xE9    | RRC count, r |
| 0xEA    | RL count, r |
| 0xEB    | RR count, r |
| 0xEC    | SLA count, r |
| 0xED    | SRA count, r |
| 0xEE    | SLL count, r |
| 0xEF    | SRL count, r |

**BIT operations** (16-bit prefix only, 1-byte bit number):

| Sub-Opc | Operation |
|---------|-----------|
| 0x30    | RES bit, r |
| 0x31    | SET bit, r |
| 0x33    | BIT bit, r |

### 3. Compact Source Addressing Modes (0x80–0xAF)

These prefixes specify a memory source operand with the operand size and addressing mode encoded in the prefix byte:

| Prefix Range | Size | Addressing Mode | Additional Bytes |
|-------------|------|-----------------|-----------------|
| 0x80+R      | 8-bit  | (R) register indirect | sub_opc |
| 0x88+R      | 8-bit  | (R+d8) reg + displacement | d8, sub_opc |
| 0x90+R      | 16-bit | (R) register indirect | sub_opc |
| 0x98+R      | 16-bit | (R+d8) reg + displacement | d8, sub_opc |
| 0xA0+R      | 32-bit | (R) register indirect | sub_opc |
| 0xA8+R      | 32-bit | (R+d8) reg + displacement | d8, sub_opc |
| 0xB0+R      | 32-bit | (R+d16) reg + 16-bit displacement | d16_lo, d16_hi, sub_opc |

Where `R` = address register encoding (0–7, mapped to XWA–XSP).

The sub-opcode table is the **same** as for register source prefix instructions (0x20+d = LD, 0x80+d = ADD, etc.), except the source is a memory location instead of a register.

### 4. Compact Destination Addressing Mode (0xB8–0xBF)

Encodes stores to memory and LDA (load effective address):

```
Byte:   [0xB8+R] [d8] [sub_opc] [optional_imm...]
```

| Sub-Opc Range | Operation |
|--------------|-----------|
| 0x30+d       | LDA d, (R+d8) — load effective address |
| 0x50+s       | LD (R+d8), reg16 — store 16-bit register |
| 0x60+s       | LD (R+d8), reg32 — store 32-bit register |

### 5. Extended Addressing Modes (0xC0–0xF7)

The first byte encodes both operand size and addressing mode:

| Prefix     | Size   | Mode | Addressing | Bytes After Prefix |
|-----------|--------|------|------------|-------------------|
| 0xC0–0xC7 | 8-bit  | 0–7  | See below  | Varies |
| 0xD0–0xD7 | 16-bit | 0–7  | See below  | Varies |
| 0xE0–0xE7 | 32-bit | 0–7  | See below  | Varies |
| 0xF0–0xF7 | Store  | 0–7  | See below  | Varies |

**Mode encoding (low 3 bits of prefix):**

| Mode | Addressing | Data After Prefix |
|------|-----------|-------------------|
| 0    | (R) register indirect | reg_byte, sub_opc |
| 1    | (R+d8) reg indirect + 8-bit disp | reg_byte, d8, sub_opc |
| 2    | (addr24) direct 24-bit address | addr_lo, addr_mid, addr_hi, sub_opc |
| 3    | (R+d16) reg indirect + 16-bit disp | reg_byte, d16_lo, d16_hi, sub_opc |
| 4    | (−R) predecrement | reg_byte, sub_opc |
| 5    | (R+) postincrement | reg_byte, sub_opc |
| 7    | Previous bank (D7 only) | mode_byte, sub_opc [, imm...] |

**Address width is not a function of the address value.** The direct-memory prefix's low two bits select an 8-, 16-, or 24-bit address form independently of how large the address is — shipped firmware writes `set 7,(0x00008a)` as `F2 8A 00 00 BF`, the 24-bit form, for an address that fits in a single byte. The LLVM assembler cannot guess the intended width from the number, so it is requested explicitly with a suffix: `(0x8a:8)`, `(0x1234:16)`, `(0x123456:24)`. An operand with no suffix keeps the 24-bit default, which is also the only width a relocation (as opposed to a constant) can use.

**Register byte encoding** (for modes 0, 1, 3, 4, 5):
```
reg_byte = 0xE0 + (register_enc × 4) + inner_mode
```

The `inner_mode` field provides additional addressing information.

### 6. Previous Register Bank (0xD7)

Accesses the previous register bank using Q registers (QWA–QSP):

```
Byte:   0xD7 [mode_byte] [sub_opc] [optional_imm...]
```

Mode byte encoding: `0xE0 + (reg_enc × 4) + 2`

| Mode Byte | Q Register |
|-----------|-----------|
| 0xE2      | QWA       |
| 0xE6      | QBC       |
| 0xEA      | QDE       |
| 0xEE      | QHL       |
| 0xF2      | QIX       |
| 0xF6      | QIY       |
| 0xFA      | QIZ       |
| 0xFE      | QSP       |

Sub-opcode table same as register source prefix, plus additional formats for BIT/SET/RES, LD/CP with word immediate, and LDW/CPW.

### 6b. The 8-bit previous-bank register codes

The `0xD7` word forms above are one half of the previous-bank machinery. The
byte forms sit behind the `0xC7` prefix and take a **register code byte** rather
than a register operand: `c7 fb 89` is *"store `A` into previous-bank byte
register `0xFB`"*, and `c7 fb 99` is the matching load. `0xFB` is the code for
`QIZH` — the high byte of the previous bank's `IZ`.

This is a real register class, not an address: the firmware uses **42 distinct
code bytes** on the store side and **45** on the load side, concentrated in
`0xE0-0xFF` with a small tail at `0x3C` and `0x60`. `0xFB` alone accounts for
2,717 of the 6,697 sites in the two families. The 16-bit counterpart of the
class (`QWA`-`QSP`, the table above) is the one the LLVM backend models; the
8-bit codes are still carried as raw bytes, which is why they print as
`stb_erp a, 0xFB` / `ldb_erp a, 0xFB` rather than under a register name.

Counts from `notes/syntax-convergence-probes/size_family_convert.py --triage`
in the disassembly repository.

## Two legal encodings, one operation: the size/form families

Several TLCS-900/H operations have **two encodings that differ in the shape of
the opcode rather than in the width of any operand**, and a byte sequence in the
ROM commits to one of them. This is the single most important fact about the
instruction set for anyone re-assembling a dump: *the operands do not determine
the encoding*, so an assembler that is told only "compare `A` with 4" cannot
know which of the two byte sequences the ROM used.

Two mechanisms produce the pairs.

**A short immediate carried in the opcode's own 3-bit field.** LD and CP place
an immediate of 0-7 directly in the sub-opcode byte (`prefix+r, 0xA8+imm` for
LD, `prefix+r, 0xD8+imm` for CP), or use a trailing 8/16/32-bit immediate field.
Both are legal for the same small value:

| operation | short form | bytes | long form | bytes |
|---|---|---|---|---|
| compare `a` with 4 | 3-bit field | `c9 dc` | imm8 | `c9 cf 04` |
| load `hl` with 0 | 3-bit field | `db a8` | imm16 | `db 03 00 00` |
| load `xiz` with 0 | 3-bit field | `ee a8` | imm32 | `46 00 00 00 00` |

**And the firmware does not always take the short one.** The KN5000 and
SX-WSA1R sources contain **2,658 `cp Xrr, n` sites and 53 `ld Xrr, n` sites
whose immediate is 0-7 and which nevertheless use the long encoding** — for
example a 6-byte `cp xwa, 5`. "Pick the short form when the immediate fits" is
therefore a rule that would silently rewrite thousands of real instructions.

**A dedicated compact opcode alongside the general prefixed form.** Here both
encodings carry an immediate of the same width; only the opcode shape differs:

| operation | compact form | bytes | general form | bytes |
|---|---|---|---|---|
| load `d` with 4 | one-byte opcode `0x20+r`, imm8 | `24 04` | prefix `C8+r`, sub-op `0x03`, imm8 | `cc 03 04` |
| store `0xFF` at `(0x07)` | dedicated `LD (n),n` | `08 07 ff` | direct-address form | `f0 07 00 ff` |
| store `0x8E00` at `(237)` | dedicated word form | `0a ed 00 8e` | direct-address form | `f0 ed 02 00 8e` |

The disassembly carries the distinction on the **operand**, as an encoding-selector
suffix, so both forms keep the instruction's real mnemonic. The 3-bit-field short
forms take `:i3` (`cp a, 4:i3` = `c9 dc`, against the untagged long `cp a, 4` =
`c9 cf 04`); the dedicated compact opcode takes `:opc` (`ld d, 4:opc` = `24 04`,
against `ld d, 4` = `cc 03 04`); the dedicated I/O forms take `:io` on a
direct-address operand (`ld (0x07:8), 0xff:io` = `08 07 ff`, against the
direct-address form `f0 07 00 ff`). The six size/form families once spelled
`cps`/`lds`/`lds32`/`ldb`/`ldio`/`ldwio` — **71,667 instruction sites** — are all
written this way, and the parse-only aliases for the old spellings have been
deleted, so an un-suffixed operand can only mean the untagged default. This is
what makes the selector necessary rather than cosmetic: because thousands of 0-7
immediates take the long form anyway (above), the selector records the choice the
bytes actually made, where "pick the shortest that fits" would silently rewrite
them.

Two related synthetic names are pure spellings and carry no encoding choice:
`incm` (prints as `incw`) and `ldda32` (fully expressible as `ld xwa, (4160:16)`).
`stb_erp`/`ldb_erp` remain their own mnemonics: their distinction is a register
class (a previous-bank GR8), not an immediate a selector could ride.

⚠ The size suffix on a **memory** operand is load bearing for the same reason: a
memory operand carries no size of its own. `incw 1, (xsp+4)` is `9f 04 61` and
`inc 1, (xsp+4)` is `8f 04 61` — a one-nibble difference between a 16-bit and an
8-bit read-modify-write.

A third, smaller instance of the same design question is the `(Xrr)` /
`(Xrr+0)` pair: `(xix)` is the 2-byte `94 60`, while `(xix+0x00)` is the 3-byte
`9c 00 60` with the displacement field present and zero. The two are distinct
encodings of the same effective address, and the source distinguishes them by
writing a displacement of 256 as a sentinel meaning "force the d8 form with
displacement 0" — 1,132 sites in the tree carry it.

Evidence and per-family site counts:
`notes/TRIAGE-size-form-mnemonics-2026-09-02.md` and its script
`notes/syntax-convergence-probes/size_family_convert.py --triage`, both in the
disassembly repository.

## LLVM Backend Support Status

The following summarizes what the custom LLVM TLCS-900 backend supports for assembly (llvm-mc):

### Fully Supported

| Category | Notes |
|----------|-------|
| Register-to-register ALU | ADD, SUB, ADC, SBC, AND, XOR, OR, CP |
| Register-to-register LD | Both 0x88 and 0x20 forms |
| Register prefix + immediate ALU | ADD/SUB/CP/AND/OR/XOR/ADC/SBC with 8/16/32-bit imm |
| Register prefix + immediate LD | 8-bit and 16-bit (32-bit uses compact form) |
| BIT/SET/RES with 16-bit register | Via register prefix |
| PUSH/POP (16-bit register) | Via register prefix |
| NEG/CPL (16-bit register) | Via register prefix |
| EXTS/EXTZ (16-bit register) | Via register prefix |
| INC/DEC with count (1–7) | Via register prefix |
| MUL/MULS/DIV/DIVS (reg-reg) | Uses GPR (32-bit) register names |
| SCC condition code set | 8-bit and 16-bit |
| Compact 32-bit immediate load | 0x40–0x47 |
| Compact (R) memory indirect | All sizes (8/16/32-bit) |
| Compact (R+d8) memory | All sizes, d8 must be 0–127 |
| LDA (load effective address) | d8 must be 0–127 |
| Memory store (R+d8) | reg16 and reg32, d8 must be 0–127 |
| Extended E2 direct memory load | 32-bit operand, 24-bit address |
| Extended F2 direct memory store | reg16 and reg32 stores |
| Previous bank (D7) operations | Full Q register support |
| Small-immediate 3-bit form | `:i3` suffix on `ld`/`cp`, all sizes, e.g. `cp a, 4:i3` |
| Dedicated compact 8-bit load | `:opc` suffix, e.g. `ld d, 4:opc` (`0x20+r`) |
| Dedicated I/O load/store | `:io` suffix on a direct address, e.g. `ld (0x07:8), 0xff:io` |
| Direct-memory address width | Explicit `:8` / `:16` / `:24` suffix on `(addr)`, e.g. `(0x8a:8)`; no-suffix defaults to 24-bit |
| PUSH/POP (memory operand) | Native mnemonic, e.g. `push (0x1234)` |
| MUL/MULS/DIV/DIVS (memory operand) | Native mnemonic, e.g. `mul WA,(0x1234)` |
| EX, shift/rotate, carry-flag group, JP/CALL cc (memory operand) | Native mnemonics added alongside the PUSH/POP and MUL/DIV memory forms |
| Register-indexed load/store `(Xrr+Rn)` | `ld`/`st` forms for byte/word/long (`ldb_dri`/`ldw_dri`/`ldl_dri`, `stb_dri`/`stw_dri`/`stl_dri`), plus `cpib_ind` (register-indexed compare with immediate) |
| ERP-byte (previous-bank) LD short-immediate and LD register | e.g. `ld QIZH,1` and `ld C,QIZH` |

### Encoding gaps closed during the `.byte` code elimination effort

The backend can now *encode* every category below. The disassembler has
since gained matching decoder support for the two families that used to
lag behind the encoder — see [Register-indexed and extended-register-pair
decoding](#register-indexed-and-extended-register-pair-decoding) below.

| Category | Resolution |
|----------|-----------|
| (R+d16) 16-bit displacement | SRI prefix encoding (C3/D3/E3/F3) implemented |
| 16-bit direct memory | F0 8-bit direct and E2/F2 extended direct implemented |
| CALR (relative call) | Fixed for label-based targets |
| Shift/rotate operations | Full support for all variants |
| LD (addr), #imm16 via F2 | Sub-opcode fixed to 0x02 |
| Auto-increment addressing | Implemented |
| .word/.hword directives | Added for data emission |

### Known Encoding Issues

1. **Displacement is signed:** The 8-bit displacement in `(R+d8)` addressing modes is **signed** (range −128 to +127). This is confirmed by MAME's TLCS-900 emulator (`(int8_t)m_op` cast in `900tbl.hxx`). The LLVM backend correctly handles both positive and negative displacements. Example: `ld wa, (xsp-56)` produces byte `0xC8` for the displacement (−56 in two's complement).

2. **d8=0 optimization:** When displacement is 0, LLVM optimizes `(R+0)` to the shorter `(R)` form, producing different byte sequences than the firmware which uses explicit `(R+0)`.

3. **LD immediate to memory sub-opcode:** Previously LLVM used sub-opcode 0x00 for `LD (addr), #imm16` but the hardware encoding uses 0x02. This has been **fixed** in the LLVM backend.

4. **32-bit LD immediate always compact:** `LD XWA, #imm32` always uses the compact 5-byte form (0x40+R) rather than the 6-byte prefix form (E8+R, 0x03, imm32). Cannot reproduce the prefix form.

5. **Fixed, but previously silent:** before a native memory form existed for them, `push (0x1234)` and `mul WA,(0x1234)` were accepted by the parser as if the parenthesised address were an *immediate operand* rather than a memory reference — `push (0x1234)` assembled to `[0x09,0x34]` (the address truncated to 8 bits) and `mul WA,(0x1234)` assembled to `[0xd8,0x08,0x34,0x12]` (multiplying by the address value itself, not by its contents). Both mnemonics now have proper memory forms and the syntax means what it says; no error was ever raised for the old, wrong reading, so any object code assembled before this fix should be treated as suspect.

6. **`(Xrr+Rn)` register-indexed operand is now refused, not silently mis-encoded:** `(Xrr+Rn)` (e.g. `(xix+iz)`) is a distinct addressing mode from `(Xrr+d16)` and is not accepted through the displacement operand syntax. It used to fall through to the expression parser, which treated the index register name as an undefined symbol — `ld wa,(xix+iz)` assembled to `d3 f1 00 00 20` instead of the hardware's `d3 07 f0 f8 20`, and was diagnosed (if at all) only at link time. This is now a parse-time error. The register-indexed forms the KN5000/WSA1R firmware actually uses (`ld`/`st` byte/word/long via `(Xrr+Rn)`, and the register-indexed immediate compare) have their own dedicated mnemonics — see the Backend Support Status table above — rather than reusing the displacement syntax.

### Register-indexed and extended-register-pair decoding

The encoder and disassembler are two separate hand-written implementations
(`TLCS900MCCodeEmitter.cpp` and `TLCS900Disassembler.cpp`); they were not
always symmetric, but the two families where the assembler could produce
bytes the disassembler could not read back are now both decoded.

- **The register-indexed `SriRR*` family** — `st_rrb`, `ld_rr*`, `lda_rr`,
  `jp_rr`, `call_rr` and the other forms behind the `0xC3`/`0xD3`/`0xE3`/`0xF3`
  prefixes with encoder mode bytes `0x07`/`0x03` — is decoded by
  `decodeSriRRPrefix()`, reached from `decodeSRIPrefix()` once it recognises
  either mode byte. Before this existed the gap hid 312 B of real code from
  every automated audit for months, and was why 33 of 34 v7 code slices
  failed a disassemble/re-assemble round trip.
- **`decodeERPPrefix()`** decodes the previous-register-bank (Q-register)
  forms behind the `0xC7`/`0xE7` prefixes, replacing what used to be a
  literal stub that always returned `Fail`.

Both are exercised by the regression suite against literal bytes pulled
from `kn5000_v10_program.rom` and `wsa1/original_ROMs/wsa1_prom_a.ic12`, and
re-assembling the printed mnemonic reproduces the exact consumed bytes in
each case.

**`ST_RRB`, `ST_RRW` and `ST_RRL` encode distinctly, not ambiguously.**
Each ends in its own trailing byte — `0x41`, `0x50`, `0x60` respectively —
confirmed with `llvm-mc --show-encoding`; the three sizes are not
collapsed by the `Opcode < 0xF0` size-adjustment guard, which only ever
applies to formats below `0xF0` and does not gate this family's fixed
`0xF3` prefix. A full audit of all 22 call sites of that guard found no
instance where it loses size information.

## Condition Codes

Used with SCC, JP, CALL, and other conditional instructions:

| Code | Value | Condition |
|------|-------|-----------|
| F    | 0     | False (never) |
| LT   | 1     | Less than (signed) |
| LE   | 2     | Less than or equal (signed) |
| ULE  | 3     | Unsigned less than or equal |
| OV   | 4     | Overflow |
| MI   | 5     | Minus (negative) |
| Z    | 6     | Zero |
| C    | 7     | Carry |
| T    | 8     | True (always) |
| GE   | 9     | Greater than or equal (signed) |
| GT   | 10    | Greater than (signed) |
| UGT  | 11    | Unsigned greater than |
| NOV  | 12    | No overflow |
| PL   | 13    | Plus (positive) |
| NZ   | 14    | Not zero |
| NC   | 15    | No carry |

## References

- TMP94C241F Datasheet (Toshiba) — **link unverified**: `https://archive.org/details/tmp94c241f` 404s as of this review (2026-09) and no confirmed replacement item on archive.org was found by name/part-number search
- TLCS-900 Programming Manual — **link unverified**: `https://archive.org/details/tlcs900programmingmanual` 404s as of this review (2026-09). Candidates that exist on archive.org but were not confirmed to be the same document: `manuallib-id-2619783` ("TOSHIBA TLCS-900/H series datasheet") and `tlcs-900-cpu-docs` ("Toshiba TLCS-900 CPU Documentation")
- [MAME TLCS-900 CPU core](https://github.com/mamedev/mame/tree/master/src/devices/cpu/tlcs900)
- [LLVM TLCS-900 Backend (custom)](https://github.com/ArqueologiaDigital/llvm-project)
