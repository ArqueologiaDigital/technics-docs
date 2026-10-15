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

| Enc | 8-bit | 16-bit | 32-bit (GPR) | Address Reg | Q Reg (upper 16 bits) |
|-----|-------|--------|--------------|-------------|-----------------------|
| 0   | W     | WA     | XWA          | XWA         | QWA                   |
| 1   | A     | BC     | XBC          | XBC         | QBC                   |
| 2   | B     | DE     | XDE          | XDE         | QDE                   |
| 3   | C     | HL     | XHL          | XHL         | QHL                   |
| 4   | D     | IX     | XIX          | XIX         | QIX                   |
| 5   | E     | IY     | XIY          | XIY         | QIY                   |
| 6   | H     | IZ     | XIZ          | XIZ         | QIZ                   |
| 7   | L     | SP     | XSP          | XSP         | QSP                   |

**Note:** in the LLVM backend, SP (enc=7) is not a member of the `GR16` register class; it belongs to a wider class used where the hardware allows SP (e.g. `ld wa, sp`, `push sp`). L (enc=7) is an ordinary member of `GR8`.

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

| Sub-Opc Range | Operation                        | Format                                                                                                                                                                           | Direction       |
|---------------|----------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------|
| 0x04          | PUSH r                           | Unary (all sizes; for a 32-bit register the LLVM assembler emits the one-byte 0x38+r form)                                                                                       | —               |
| 0x05          | POP r                            | Unary (all sizes; for a 32-bit register the LLVM assembler emits the one-byte 0x58+r form)                                                                                       | —               |
| 0x06          | CPL r                            | Unary                                                                                                                                                                            | —               |
| 0x07          | NEG r                            | Unary                                                                                                                                                                            | —               |
| 0x12          | EXTZ r                           | Unary (16- and 32-bit)                                                                                                                                                           | —               |
| 0x13          | EXTS r                           | Unary (16- and 32-bit)                                                                                                                                                           | —               |
| 0x20–0x24     | ANDCF/ORCF/XORCF/LDCF/STCF #n, r | Carry flag with bit n of r (8- and 16-bit; bit number in the next byte)                                                                                                          | —               |
| 0x28–0x2C     | ANDCF/ORCF/XORCF/LDCF/STCF A, r  | Carry flag with bit A of r (8- and 16-bit)                                                                                                                                       | —               |
| 0x2E / 0x2F   | LDC cr, r / LDC r, cr            | Load control register (selector in the next byte)                                                                                                                                | cr ← r / r ← cr |
| 0x40+d        | MUL d, r                         | Multiply; d names the double-width result: a 32-bit register after a 16-bit prefix (`d9 40` = `mul xwa, bc`), a 16-bit pair after an 8-bit prefix, d odd (`ca 41` = `mul wa, b`) | —               |
| 0x48+d        | MULS d, r                        | Multiply signed                                                                                                                                                                  | —               |
| 0x50+d        | DIV d, r                         | Divide; d names the double-width dividend (`d9 50` = `div xwa, bc`)                                                                                                              | —               |
| 0x58+d        | DIVS d, r                        | Divide signed                                                                                                                                                                    | —               |
| 0x60+n        | INC n, r                         | Increment by n (1–7)                                                                                                                                                             | —               |
| 0x68+n        | DEC n, r                         | Decrement by n (1–7)                                                                                                                                                             | —               |
| 0x70+cc       | SCC cc, r                        | Set if condition code                                                                                                                                                            | —               |
| 0x80+d        | ADD d, r                         | Add                                                                                                                                                                              | d ← d + r       |
| 0x88+d        | LD d, r                          | Load                                                                                                                                                                             | d ← r           |
| 0x90+d        | ADC d, r                         | Add with carry                                                                                                                                                                   | d ← d + r + C   |
| 0x98+d        | LD r, d                          | Load reverse                                                                                                                                                                     | r ← d           |
| 0xA0+d        | SUB d, r                         | Subtract                                                                                                                                                                         | d ← d − r       |
| 0xA8+n        | ld r, n:i3                       | Load small immediate (0–7)                                                                                                                                                       | r ← n           |
| 0xB0+d        | SBC d, r                         | Subtract with borrow                                                                                                                                                             | d ← d − r − C   |
| 0xC0+d        | AND d, r                         | Bitwise AND                                                                                                                                                                      | d ← d & r       |
| 0xD0+d        | XOR d, r                         | Bitwise XOR                                                                                                                                                                      | d ← d ^ r       |
| 0xD8+n        | cp r, n:i3                       | Compare small immediate (0–7)                                                                                                                                                    | r − n           |
| 0xE0+d        | OR d, r                          | Bitwise OR                                                                                                                                                                       | d ← d \| r      |
| 0xF0+d        | CP d, r                          | Compare                                                                                                                                                                          | d − r           |

Where `d` = destination register encoding (3 bits), `r` = source register from prefix, `n` = small immediate (3 bits), `cc` = condition code (4 bits).

**LD encoding note:** Register-to-register LD has two sub-opcodes, 0x88+d (`LD d, r`, source in the prefix) and 0x98+d (`LD r, d`, destination in the prefix), so every move has two byte sequences: `ld b, a` is `c9 8a` or `ca 99`. The LLVM assembler always uses the 0x88 form, and its disassembler does not decode the 0x98 form: llvm-mc (backend `a3a81863f87d`) reports `ca 99` as an invalid encoding, where MAME reads `ld B,A`. Sub-opcodes 0x20–0x2F are not LD in this table; they are the carry-flag and LDC rows above.

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

**BIT operations** (8- and 16-bit prefix, 1-byte bit number):

| Sub-Opc | Operation   |
|---------|-------------|
| 0x30    | RES bit, r  |
| 0x31    | SET bit, r  |
| 0x32    | CHG bit, r  |
| 0x33    | BIT bit, r  |
| 0x34    | TSET bit, r |

CHG and TSET are listed as hardware encodings: the LLVM backend does not accept
`chg` or `tset` on a register yet.

### 3. Compact Source Addressing Modes (0x80–0xAF)

These prefixes specify a memory source operand with the operand size and addressing mode encoded in the prefix byte:

| Prefix Range | Size   | Addressing Mode           | Additional Bytes |
|--------------|--------|---------------------------|------------------|
| 0x80+R       | 8-bit  | (R) register indirect     | sub_opc          |
| 0x88+R       | 8-bit  | (R+d8) reg + displacement | d8, sub_opc      |
| 0x90+R       | 16-bit | (R) register indirect     | sub_opc          |
| 0x98+R       | 16-bit | (R+d8) reg + displacement | d8, sub_opc      |
| 0xA0+R       | 32-bit | (R) register indirect     | sub_opc          |
| 0xA8+R       | 32-bit | (R+d8) reg + displacement | d8, sub_opc      |

Where `R` = address register encoding (0–7, mapped to XWA–XSP).

The sub-opcode table follows the register-prefix one for the ALU rows (0x80+d = ADD, 0xA0+d = SUB, …), but it is not the same table: in the memory form 0x20+d is `LD d, (mem)` and 0x30+d is `EX (mem), d`, rows the register prefix uses for the carry-flag and bit operations, and 0x88+d is `ADD (mem), d` where the register prefix has LD.

### 4. Compact Destination Addressing Modes (0xB0–0xBF)

Encodes stores to memory and LDA (load effective address):

`0xB0+R` addresses `(R)` with no displacement (`b4 41` = `ld (xix), a`); `0xB8+R` addresses `(R+d8)` (`bc 10 41` = `ld (xix+16), a`). A 16-bit displacement uses the extended prefix, mode 3 (`c3`/`d3`/`e3`/`f3`).

```
Byte:   [0xB0+R or 0xB8+R] [d8 (B8 only)] [sub_opc] [optional_imm...]
```

| Sub-Opc Range | Operation                                                                |
|---------------|--------------------------------------------------------------------------|
| 0x00          | LD (mem), imm8 (`bc 10 00 05` = `ld (xix+16), 5`)                        |
| 0x02          | LDW (mem), imm16 (`bc 10 02 05 00` = `ldw (xix+16), 5`)                  |
| 0x20+d        | LDA d, (mem) — 16-bit effective address (`bf fc 20` = `lda wa, (xsp-4)`) |
| 0x30+d        | LDA d, (mem) — 32-bit effective address                                  |
| 0x40+s        | LD (mem), reg8 — store 8-bit register                                    |
| 0x50+s        | LD (mem), reg16 — store 16-bit register                                  |
| 0x60+s        | LD (mem), reg32 — store 32-bit register                                  |

`(mem)` is `(R)` after `0xB0+R` and `(R+d8)` after `0xB8+R`.

### 5. Extended Addressing Modes (0xC0–0xF7)

The first byte encodes both operand size and addressing mode:

| Prefix     | Size   | Mode | Addressing | Bytes After Prefix |
|-----------|--------|------|------------|-------------------|
| 0xC0–0xC7 | 8-bit  | 0–7  | See below  | Varies |
| 0xD0–0xD7 | 16-bit | 0–7  | See below  | Varies |
| 0xE0–0xE7 | 32-bit | 0–7  | See below  | Varies |
| 0xF0–0xF7 | Store  | 0–7  | See below  | Varies |

**Mode encoding (low 3 bits of prefix):**

| Mode | Addressing                                                                                  | Data After Prefix                                      |
|------|---------------------------------------------------------------------------------------------|--------------------------------------------------------|
| 0    | (n) direct, 8-bit address                                                                   | addr, sub_opc                                          |
| 1    | (nn) direct, 16-bit address                                                                 | addr_lo, addr_hi, sub_opc                              |
| 2    | (nnn) direct, 24-bit address                                                                | addr_lo, addr_mid, addr_hi, sub_opc                    |
| 3    | (mem) register-indirect: (R), (R+d16), (R+r8), (R+r16), chosen by the mode byte             | mode/reg byte [, d16 or base and index codes], sub_opc |
| 4    | (−R) predecrement                                                                           | reg_byte, sub_opc                                      |
| 5    | (R+) postincrement                                                                          | reg_byte, sub_opc                                      |
| 7    | register by code (C7 / D7 / E7): any register, including other banks and the Q upper halves | reg_code, sub_opc [, imm...]                           |

**Address width is not a function of the address value.** The direct-memory prefix's low two bits select an 8-, 16-, or 24-bit address form independently of how large the address is — shipped firmware writes `set 7,(0x00008a)` as `F2 8A 00 00 BF`, the 24-bit form, for an address that fits in a single byte. The LLVM assembler cannot guess the intended width from the number, so it is requested explicitly with a suffix: `(0x8a:8)`, `(0x1234:16)`, `(0x123456:24)`. An operand with no suffix keeps the 24-bit default, and that is the only width that always links correctly for a symbol the linker places. At `:16` the backend emits an `R_TLCS900_LO16` relocation, and the linker silently keeps the low 16 bits. At `:8` it emits an `R_TLCS900_NONE` relocation, which does nothing, so the field stays 0. Neither case produces a diagnostic.

**Register byte encoding** (for modes 3, 4 and 5):
```
reg_byte = 0xE0 + (register_enc × 4) + inner_mode
```

The `inner_mode` field provides additional addressing information.

### 6. Registers by code: the Q registers (0xD7)

The `0xC7`/`0xD7`/`0xE7` prefixes (mode 7) name a register by its **register-file
code** instead of a 3-bit field. The word form reaches the Q registers
(QWA–QSP), the upper 16 bits of the current `XWA`–`XSP`, which no 3-bit field
can name:

```
Byte:   0xD7 [reg_code] [sub_opc] [optional_imm...]
```

Q register code: `0xE0 + (reg_enc × 4) + 2`

| Code | Q Register |
|------|------------|
| 0xE2 | QWA        |
| 0xE6 | QBC        |
| 0xEA | QDE        |
| 0xEE | QHL        |
| 0xF2 | QIX        |
| 0xF6 | QIY        |
| 0xFA | QIZ        |
| 0xFE | QSP        |

Sub-opcode table same as register source prefix, plus additional formats for BIT/SET/RES, LD/CP with word immediate, and LDW/CPW.

### 6b. Byte registers by code (0xC7)

The byte forms sit behind the `0xC7` prefix and take the same kind of
**register code byte**: `c7 fb 89` is `ld A,QIZH` (load `A` from the register
with code `0xFB`), and `c7 fb 99` is the reverse, `ld QIZH,A`. `0xFB` is
`QIZH`, the top byte of `XIZ`. The index registers are not banked, so this is
not a previous-bank register.

The code byte is a register-file address. `0xE0`-`0xEF` are the current bank's
`XWA`-`XHL`, `0xF0`-`0xFF` are `XIX`-`XSP`, `0xD0`-`0xDF` are the previous
bank's `XWA`-`XHL`, and `0x00`-`0x3F` name banks 0-3 directly (MAME's
`900tbl.hxx`, function get_reg). The low two bits pick the byte within the 32-bit
register, so `0xFB` is `0xF8` (`XIZ`) + 3.

The firmware uses 22 distinct codes in the two byte families (`ldto_berp`,
`ldfr_berp`), 7,866 sites at disassembly `3417969c0`. `0xFB` alone accounts
for 4,123 of them, and the only codes below `0xE0` are `0x31`, `0x34`, `0x38`,
`0x3C` and `0x3D`, byte registers of bank 3. The LLVM backend names the 16-bit
Q registers (the table above: `ld wa, qiz` = `d7 fa 88`) but not the byte
codes, which is why these forms are written `ldto_berp a, 0xFB` /
`ldfr_berp a, 0xFB` (named `stb_erp` / `ldb_erp` until 2026-09-25) rather than
under a register name.

Counts over `git ls-files '*.s'` in the disassembly repository, read as bytes
(`LC_ALL=C grep -a -i -E '^\s*ld(to|fr)_berp\b'` gives the 7,866 lines; adding
`[^;]*,\s*(0xfb|251)\b` gives the 4,123).

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
`ldto_berp`/`ldfr_berp` (named `stb_erp`/`ldb_erp` until 2026-09-25) remain
their own mnemonics. Their operand is a byte register named by its
register-file code, a class the backend does not model yet, not an immediate a
selector could ride.

⚠ The size suffix on a **memory** operand is load bearing for the same reason: a
memory operand carries no size of its own. `incw 1, (xsp+4)` is `9f 04 61` and
`inc 1, (xsp+4)` is `8f 04 61` — a one-nibble difference between a 16-bit and an
8-bit read-modify-write.

A third, smaller instance of the same design question is the `(Xrr)` /
`(Xrr+0)` pair: `(xix)` is the 2-byte `94 60`, while `(xix+0x00)` is the 3-byte
`9c 00 60` with the displacement field present and zero. The two are distinct
encodings of the same effective address. The source distinguishes them with a
width suffix on the displacement: `(xix+0:8)` forces the d8 form with
displacement 0 (1,044 sites at disassembly `3417969c0`). Until 2026-09-25 this
was spelled as a displacement of 256, a sentinel that backend `24782ed406f3`
retired; 256 now means 256.

Evidence and per-family site counts:
`notes/TRIAGE-size-form-mnemonics-2026-09-02.md` and its script
`notes/syntax-convergence-probes/size_family_convert.py --triage`, both in the
disassembly repository.

## LLVM Backend Support Status

The following summarizes what the custom LLVM TLCS-900 backend supports for assembly (llvm-mc):

### Fully Supported

| Category                                                              | Notes                                                                                                                                                                                                                                                                                                                                                                                         |
|-----------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Register-to-register ALU                                              | ADD, SUB, ADC, SBC, AND, XOR, OR, CP                                                                                                                                                                                                                                                                                                                                                          |
| Register-to-register LD                                               | 0x88+d form (`ld b, a` = `c9 8a`); the 0x98+d form is neither emitted nor decoded                                                                                                                                                                                                                                                                                                             |
| Register prefix + immediate ALU                                       | ADD/SUB/CP/AND/OR/XOR/ADC/SBC with 8/16/32-bit imm                                                                                                                                                                                                                                                                                                                                            |
| Register prefix + immediate LD                                        | 8-bit and 16-bit (32-bit uses compact form)                                                                                                                                                                                                                                                                                                                                                   |
| BIT/SET/RES with 8- and 16-bit register                               | Via register prefix                                                                                                                                                                                                                                                                                                                                                                           |
| PUSH/POP (8- and 16-bit register)                                     | Via register prefix                                                                                                                                                                                                                                                                                                                                                                           |
| NEG/CPL (8- and 16-bit register)                                      | Via register prefix                                                                                                                                                                                                                                                                                                                                                                           |
| EXTS/EXTZ (16- and 32-bit register)                                   | Via register prefix                                                                                                                                                                                                                                                                                                                                                                           |
| INC/DEC with count (1–7)                                              | Via register prefix                                                                                                                                                                                                                                                                                                                                                                           |
| MUL/MULS/DIV/DIVS (reg-reg)                                           | Named by the double-width register the CPU writes (`mul xwa, bc` = `d9 40`, `mul wa, b` = `ca 41`), since backend `8e188b215251` (2026-09-25)                                                                                                                                                                                                                                                 |
| SCC condition code set                                                | 8-bit and 16-bit                                                                                                                                                                                                                                                                                                                                                                              |
| Compact 32-bit immediate load                                         | 0x40–0x47                                                                                                                                                                                                                                                                                                                                                                                     |
| Compact (R) memory indirect                                           | All sizes (8/16/32-bit)                                                                                                                                                                                                                                                                                                                                                                       |
| Compact (R+d8) memory                                                 | All sizes; d8 is signed, −128..+127 (`ld wa, (xsp-56)` = `9f c8 20`)                                                                                                                                                                                                                                                                                                                          |
| LDA (load effective address)                                          | d8 signed (`lda xwa, (xsp-4)` = `bf fc 30`)                                                                                                                                                                                                                                                                                                                                                   |
| Memory store (R+d8)                                                   | reg8, reg16 and reg32; d8 signed (`ld (xsp-8), a` = `bf f8 41`)                                                                                                                                                                                                                                                                                                                               |
| Extended E2 direct memory load                                        | 32-bit operand, 24-bit address                                                                                                                                                                                                                                                                                                                                                                |
| Extended F2 direct memory store                                       | reg16 and reg32 stores                                                                                                                                                                                                                                                                                                                                                                        |
| Q-register (D7) operations                                            | QWA–QSP (upper 16 bits) by name, e.g. `ld wa, qiz` = `d7 fa 88`                                                                                                                                                                                                                                                                                                                               |
| Small-immediate 3-bit form                                            | `:i3` suffix on `ld`/`cp`, all sizes, e.g. `cp a, 4:i3`                                                                                                                                                                                                                                                                                                                                       |
| Dedicated compact 8-bit load                                          | `:opc` suffix, e.g. `ld d, 4:opc` (`0x20+r`)                                                                                                                                                                                                                                                                                                                                                  |
| Dedicated I/O load/store                                              | `:io` suffix on a direct address, e.g. `ld (0x07:8), 0xff:io`                                                                                                                                                                                                                                                                                                                                 |
| Direct-memory address width                                           | Explicit `:8` / `:16` / `:24` suffix on `(addr)`, e.g. `(0x8a:8)`; no-suffix defaults to 24-bit                                                                                                                                                                                                                                                                                               |
| PUSH/POP (memory operand)                                             | Native mnemonic, e.g. `push (0x1234)`                                                                                                                                                                                                                                                                                                                                                         |
| MUL/MULS/DIV/DIVS (memory operand)                                    | Native mnemonic, e.g. `mul WA,(0x1234)`                                                                                                                                                                                                                                                                                                                                                       |
| EX, shift/rotate, carry-flag group, JP/CALL cc (memory operand)       | Native mnemonics added alongside the PUSH/POP and MUL/DIV memory forms                                                                                                                                                                                                                                                                                                                        |
| Register-indexed `(Xrr+Rr)`                                           | Native operand on every memory instruction since backend `a3a81863f87d` (2026-10-02): `ld wa, (xix+iz)` = `d3 07 f0 f8 20`. The older `ldb_dri`/`stw_dri`/`cpib_ind` wrappers still assemble. The 8-bit-index form `(Xrr+r8)` is accepted on LD (`ld a, (xhl+a)` = `c3 03 ec e0 21`, `ld (xhl+a), b` = `f3 03 ec e0 42`); BIT/SET/CP/INC with it (e.g. `bit n, (xhl+a)`) are not modelled yet |
| Byte register by code (C7 prefix): LD short-immediate and LD register | Wrapper mnemonics `lds_erpb 0xfb, 1` (`c7 fb a9`, MAME `ld QIZH,1`) and `ld_erpb_rr c, 0xfb` (`c7 fb 8b`, MAME `ld C,QIZH`). The native text `ld c, qizh` is not parsed as a register: it assembles to `cb 03` plus a relocation for an undefined symbol `qizh`                                                                                                                               |

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

2. **d8=0 is requested explicitly (resolved 2026-09-25):** a plain `(R+0)` still assembles to the shorter `(R)` form, so the firmware's explicit d8-with-zero encoding is written `(R+0:8)`: `ld a, (xix+0:8)` = `8c 00 21`, against `ld a, (xix)` = `84 21`.

3. **LD immediate to memory sub-opcode:** Previously LLVM used sub-opcode 0x00 for `LD (addr), #imm16` but the hardware encoding uses 0x02. This has been **fixed** in the LLVM backend.

4. **32-bit LD immediate always compact:** `LD XWA, #imm32` always uses the compact 5-byte form (0x40+R) rather than the 6-byte prefix form (E8+R, 0x03, imm32). Cannot reproduce the prefix form.

5. **Fixed, but previously silent:** before a native memory form existed for them, `push (0x1234)` and `mul WA,(0x1234)` were accepted by the parser as if the parenthesised address were an *immediate operand* rather than a memory reference — `push (0x1234)` assembled to `[0x09,0x34]` (the address truncated to 8 bits) and `mul WA,(0x1234)` assembled to `[0xd8,0x08,0x34,0x12]` (multiplying by the address value itself, not by its contents). Both mnemonics now have proper memory forms and the syntax means what it says; no error was ever raised for the old, wrong reading, so any object code assembled before this fix should be treated as suspect.

6. **`(Xrr+Rr)` register-indexed operand, modelled since 2026-10-02.** `(Xrr+Rr)` (e.g. `(xix+iz)`) is a distinct addressing mode from `(Xrr+d16)`. It used to fall through to the expression parser, which treated the index register name as an undefined symbol: `ld wa,(xix+iz)` assembled to `d3 f1 00 00 20` instead of the hardware's `d3 07 f0 f8 20`. It was then made a parse-time error. Since backend `a3a81863f87d` (TOOLCHAIN_VERSION UPDATE 21) it is an ordinary operand of every memory instruction: `ld wa,(xix+iz)` assembles to `d3 07 f0 f8 20`, and the sources write such operands natively (`cp (xhl+iy), 0x7b`, `bit 7, (xde+ix)`). The disassembler still prints the older wrapper spelling (`ld_rrw wa, xix, iz`), which reassembles to the same bytes.

7. **`di` meant the opposite of DI (found 2026-09-25).** The backend defined
   `di` as an alias of `EI 0` and printed the bytes `06 00` back as `di`. On the
   TLCS-900, `EI n` loads the interrupt mask IFF with *n* and an interrupt is
   accepted when its level is at least IFF (MAME `op_EI`:
   `m_sr.b.h = (m_sr.b.h & 0x8f) | ((imm & 7) << 4)`), so `06 00` sets IFF = 0 and
   **accepts every level**; the real DI is `EI 7` = `06 07`. The byte gate could
   never notice, because `di` and `ei 0` assemble identically — every one of the
   213 `di` lines in the KN5000 and SX-WSA1R sources therefore read as the
   opposite of what the CPU does. The sources now spell all 213 as `ei 0`
   (`scripts/tools/fix_di_ei_semantics.py` in the disassembly repo, same bytes,
   gate green), together with nine same-line comments that stated the inverted
   effect, such as HD-AE5000's `ei 0x07 ; enable interrupts`. The alias itself
   was corrected the same day (backend `6488ae7d520a`): `di` is now a
   parse-only alias for `EI 7` (`06 07`), and `06 00` prints as `ei 0`, so no
   decode can reintroduce the inverted reading.

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
- **`decodeERPPrefix()`** decodes the register-by-code forms (the Q registers
  and other register-file codes) behind the `0xC7`/`0xE7` prefixes, replacing
  what used to be a literal stub that always returned `Fail`.

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
- [LLVM TLCS-900 Backend (custom)](https://github.com/felipesanches/llvm-project/tree/tlcs900_backend) — the commit the disassembly is built with is named in its `TOOLCHAIN_VERSION`. ⚠ As of 2026-10-15 that commit (`a3a81863f87d`) has not been pushed; the public branch stops at `86332721969d` (2026-09-02), whose build cannot parse the current sources.
