---
layout: page
title: "NEC uPD6383GF - unofficial datasheet"
permalink: /upd6383-datasheet/
---

# NEC µPD6383GF — unofficial datasheet

> ⚠ **THIS IS NOT AN NEC DOCUMENT.** It is a reverse-engineering result, assembled from ROM
> corpora, service-manual schematics and live emulator traces by the Technics preservation
> project. NEC published no datasheet for this part that anyone has found — 0 hits for `638x`
> across bitsavers' complete NEC data-book holdings — and the only vendor documentation located is
> a block diagram and pin table in the Pioneer CDJ-500 service manual, where the part is IC302.
>
> Every claim carries a grade: **MEASURED**, **PROVEN BY CONSTRUCTION**, **INFERRED**, or
> **OPEN**. Nothing here is a guess dressed as a fact, and where something is unknown the entry
> says so rather than omitting the row.
>
> **Source of truth:** `dsp/instruction-set.md` in the
> [disassembly repository](https://github.com/ArqueologiaDigital/kn5000-roms-disasm), which is
> kept in step with the Python disassembler and with MAME's `upd6383d.cpp`. This page can drift
> from it; that one is authoritative.

---

## 1. Overview

A fixed-point audio effects DSP, part of NEC's µPD638x consumer-audio line. Its immediate
predecessor by part number, the µPD6382GF, is listed by distributors as a *"19-Bit Digital Signal
Processor, QFP-80"*; no databook covers either.

| | |
|---|---|
| Package | **100-pin QFP**. Pin 1 bottom-left, numbering counter-clockwise — MEASURED |
| Clock | **25 MHz** (KN5000, X301) — MEASURED |
| Frame rate | **44.1 kHz**, hardware-restarted — MEASURED four ways |
| Cycles per frame | 25 MHz / 44.1 kHz = **567**, against 384 words of instruction RAM |
| Instruction word | **36 bits**, in a 5-byte big-endian right-aligned container; bits 36-39 always zero — MEASURED |
| Data width | **24-bit**; coefficients signed **Q0.23** — MEASURED |
| External memory | **17 address lines, 16 data lines** for delay DRAM — MEASURED from the pinout |
| Known part suffixes | `µPD6383GF-3BA`; a dealer lists it against Panasonic house number `GGC1163` |

**Known applications.** Technics SX-KN5000 (IC311), SX-KN1500 (IC3), SX-WSA1 / SX-WSA1R (IC5,
IC6, IC30 — three per machine), Pioneer CDJ-500 / CDJ-500G (IC302).

The chip is used **in pairs of effect "units"** in the Technics machines: one microprogram holds a
common header, a call to unit 0's body, a call to unit 1's body, and a shared output stage.

---

## 2. Pinout

Read at 400 dpi from the SX-WSA1R service manual, sheet II-15/II-16, where IC30 is drawn complete.
The full table with wiring notes is in
[`dsp/hardware/upd6383-pinout.md`](https://github.com/ArqueologiaDigital/kn5000-roms-disasm).

### Pins 1-30 — bottom edge: host port, reset, serial audio

| pin | name | pin | name | pin | name |
|---|---|---|---|---|---|
| 1 | `/CS` | 11 | `/BR-RQ` | 21 | `DI2` |
| 2 | `/C/D` | 12 | `/BR-AK` | 22 | `DI3` |
| 3 | `/SCK` | 13 | `/Fs-RST` | 23 | `DO1` |
| 4 | `SI` | 14 | `/Fs-MASK` | 24 | `DO2` |
| 5 | `SO` | 15 | `VDD` | 25 | `DO3` |
| 6 | `EIFLAG` | 16 | `GND` | 26 | `BCLKO` |
| 7 | `EOFLAG` | 17 | `BCLKI` ⚠ | 27 | `LRCKO` |
| 8 | `RDY` | 18 | `LRCKI` | 28 | `XFsO1` |
| 9 | `/RST` | 19 | `XFsI` | 29 | `XFsO2` |
| 10 | `/RST2` | 20 | `DI1` | 30 | `TEST` |

⚠ Pin 17's number is obscured in the drawing by a ground stub; `BCLKI` is placed there because the
run 15/16/[17]/18 is otherwise unbroken at uniform pitch. Every other cell was read directly.

### Pins 31-50 — right edge: mode straps, oscillator, DRAM control

| pin | name | pin | name | pin | name | pin | name |
|---|---|---|---|---|---|---|---|
| 31 | `/EROF` | 36 | `GND` | 41 | `GND` | 46 | `A0` |
| 32 | `MD1` | 37 | `EOSC` | 42 | `VDD` | 47 | `A1` |
| 33 | `MD2` | 38 | `SEL` | 43 | `/RAS` | 48 | `A2` |
| 34 | `MD3` | 39 | `XI` | 44 | `/CAS` | 49 | `A3` |
| 35 | `MD4` | 40 | `XO` | 45 | `/WE` | 50 | `A4` |

### Pins 51-80 — top edge: DRAM address and data

| pins | name |
|---|---|
| 51-62 | `A5` … `A16`, ascending with pin number |
| 63 | `VDD` |
| 64 | `GND` |
| 65-80 | `I/O1` … `I/O16`, ascending with pin number |

### Pins 81-100 — left edge: flags and parallel host port

| pin | name | pin | name |
|---|---|---|---|
| 81 | `GND` | 89 | `/P/S` |
| 82 | `VDD` | 90 | `/WRITE` |
| 83 | `GF1` | 91 | `/READ` |
| 84 | `GF2` | 92-99 | `D0` … `D7` |
| 85 | `GF3` | 100 | `SETRDY` |
| 86 | `RQ1` | | |
| 87 | `RQ2` | | |
| 88 | `RQ3` | | |

---

## 3. Functional description

### 3.1 Host interface — two of them, selected by `/P/S`

The chip offers a **serial** and a **parallel** host port, and the two known Technics designs use
different ones — which is how we know the pin is a selector.

| | serial | parallel |
|---|---|---|
| pins | `/CS` 1, `/C/D` 2, `/SCK` 3, `SI` 4, `SO` 5, `RDY` 8 | `D0-D7` 92-99, `/WRITE` 90, `/READ` 91 |
| used by | **SX-KN5000** (IC311) | **SX-WSA1R** (IC30, with `/P/S` tied to +5 V) |

`/C/D` selects command versus data. `RDY` is open-drain — on the KN5000 it is pulled up by a 4.7 kΩ
to +5 V and leaves the sheet as the net `DSPRDY`.

⚠ **The host port is write-oriented.** No route has been found by which the host reads a DSP
result back, which is why every measurement of the chip's behaviour so far has had to come out
through the audio path.

### 3.2 Flags — `RQ1-3` in, `GF1-3` out

From the CDJ-500 pin table: `RQ1`–`RQ3` are **host-written and testable by an instruction's
condition field**, and `GF1`–`GF3` are **set by instructions and host-readable**.

⛔ **Neither the condition field nor the flag-setting instruction has been located in any
microcode**, and neither Technics board makes them usable:

| board | `RQ1-3` | `GF1-3` |
|---|---|---|
| SX-KN5000 | strapped | — |
| SX-WSA1R (IC30) | **all three tied together to GND** | **unconnected stubs** |

So on the machines we can reach, the host can neither vary `RQ` nor read `GF`. ⇒ predication is
**OPEN and unobservable here**, and the correct statement is *"not available on this board"*.

### 3.3 Clock, reset and frame timing

`XI`/`XO` (39/40) are the oscillator pins and `EOSC` (37) is an external-oscillator input.
`/RST` (9) and `/RST2` (10) are two resets. **`/Fs-RST` (13) restarts the program counter every
sample** — there is no software frame loop, and the per-frame instruction budget is fixed by the
clock ratio. `/Fs-MASK` (14) gates that. `XFsI` (19) is the frame-sync input and `XFsO1`/`XFsO2`
(28/29) the outputs, so several chips can be chained on one frame clock.

`MD1`–`MD4` (32-35) are mode straps. **What they select is OPEN** — no source documents it. On the
WSA1R's IC30, `MD1` is grounded and `MD2`/`MD3`/`MD4` go to +5 V.

**`SETRDY` (100) and `/BR-RQ` (11) gate an emulator mode.** On the KN5000 `SETRDY` is left open and
`BR-RQ` is strapped high, which disables it: *"no PC trace without board modification"*. What the
mode delivers is **OPEN**; that it exists is the reason the pins are named as they are.
`/BR-AK` (12) is the matching acknowledge.

### 3.4 Audio interface

`BCLKI` (17) / `LRCKI` (18) clock in; `BCLKO` (26) / `LRCKO` (27) clock out. **Three serial data
inputs `DI1`-`DI3` (20-22) and three outputs `DO1`-`DO3` (23-25)**, so one chip can take three
stereo lanes from a tone generator and return three processed lanes.

### 3.5 Memories

| space | size | addressing | grade |
|---|---|---|---|
| **Instruction RAM** | 384 words | host-loaded; PC restarts each frame | MEASURED |
| **Coefficient RAM** | 256 cells, signed Q0.23 | an implicit **cursor**, +1 per coefficient-consuming word, reset by one instruction | MEASURED; the whole cell map is recovered |
| **Data RAM** | per-unit state | an 8-bit **wrapping data pointer** with a signed post-increment from the `addr8` field | MEASURED; origin pinned 85/85 |
| **Register file** | indexed by `addr8`, bit 7 = unit | named cells include per-unit output level and state-block base | MEASURED |
| **External delay DRAM** | 17 address lines | `address = (descriptor[cursor] + G) mod 2^N` | PROVEN BY CONSTRUCTION |

The delay arena is split per unit — on the KN5000, 32 768 words each = **743.0 ms** per unit. A
delay line's length is the **difference of two descriptor cells**, and the ROM ships
`15 435 = 350 × 44100/1000` exactly, which is how the arithmetic was confirmed.

⚠ `N` in `mod 2^N` is **OPEN**: the firmware never uses more than 16 bits, so it is unobservable
from software. The chip provides 17 address pins, which bounds it from the silicon side.

---

## 4. Instruction word

```
 35             24 23  20 19        12 11                     0
+-----------------+------+------------+------------------------+
|      hi12       |class4|   addr8    |          lo12          |
+-----------------+------+------------+------------------------+
```

### 4.1 `hi12` is a horizontal microword, not an opcode — MEASURED

Its 54 observed values contain **77 Hamming-distance-1 pairs** against a popcount-matched null of
43.4 ± 4.3 (**z = +7.9**), spread over all twelve bit positions.

| bit | meaning | grade |
|---|---|---|
| 11 | **FORMAT ESCAPE** — bits [10:0] mean something else | MEASURED |
| 10 | **END OF BLOCK** (when bit 11 clear); the word still does its datapath work | MEASURED |
| 9:8 | `f98` — a proven **field**, meaning **UNKNOWN**; arity 3 | field MEASURED, meaning OPEN |
| 7 | gates bit 4's store; its own meaning **OPEN** | 12 minimal pairs |
| 6 | third bit of the alternate-encoding flag | MEASURED, 0 exceptions in 6441 words |
| 5 | no reading; rendered as residue | OPEN |
| 4 | **STORE** accumulator → `mem[ptr]`, **before** the word's own ALU step, gated by bit 7 | MEASURED; timing FORCED |
| 3:1 | `f31` — **the accumulator operation** | see below |
| 0 | "`addr8` is an absolute immediate" | PROVEN BY CONSTRUCTION for one family |

**`f31` (`hi12[3:1]`)** — 8 of 8 values observed, **three anchored**:

| value | operation | grade |
|---|---|---|
| 0 | `acc ← P` (LOAD) | anchored |
| 1 | `acc += P` (ADD) | anchored |
| 2 | `acc` unchanged (HOLD) | anchored |
| 3, 4, 5, 6, 7 | **OPEN** | 189 words blocked on them |

### 4.2 `class4` — addressing mode and cursor fetch — MEASURED

Bit 23 enables a **coefficient-cursor fetch** (fetch is not advance — only class `0xA` advances
the cursor). Bits 2:0 are the addressing mode, and **`hi12` bit 11 picks the space**:

| mode | meaning |
|---|---|
| 0 | pointer, no move |
| 1 | **register file** (without escape) / **external delay DRAM** (with escape, 324/324) |
| 2 | pointer with **post-increment by `s8(addr8)`** — the only mode that moves the pointer, and never escaped: 0 of 2399 |
| 3-6 | uncharacterised — OPEN |

### 4.3 `lo12` — operand routing

```
      11 10           6 5 4              0
     +--+--------------+-+----------------+
     |G |     SRC      |M|     ACTION     |
     +--+--------------+-+----------------+
```

**Bit 11 selects a second encoding with no SRC and no ACTION field** — the device executes nothing
for such a word. 169 undecoded words carry it; this is the single largest open block.

**SRC — 7 of 18 observed codes anchored:** `0x07` `mem[ptr]`, `0x10` accumulator, `0x19` tempA,
`0x1A` tempB, `0x08` coefficient, plus `0x00` and `0x0B` which are **split by the word's own
class**. `0x11` is the second accumulator `accb` (located, but its two write forms are not yet
separable). `0x1C` is the effect's control bus — LFO for modulation programs, envelope for
dynamics; it is **not LFO-specific**.

**ACTION — 9 of 24 observed codes anchored:** `0x00` (accumulator input term), `0x07`
(`mem[ptr] ← bus`), `0x12` (no side effect), `0x13` (tempA), `0x14` (tempB), `0x15`, `0x19`,
`0x0D`/`0x0E`. `ACT 0x0B` is anchored **only on class A**, as an all-pass multiplicand route.

⚠ How `ACT 0x12` and `ACT 0x15` differ is **OPEN**; both read as "no side effect".

### 4.4 The ALU — VERIFIED

```
  L := src[ lo12[10:6] ]
  if hi12 bit 4 and not (bit 7 and f31 != 2):
      mem[p] <- acc ; acc := 0                 store AND clear, BEFORE the operation
  acc := SRC_TERM + P_TERM                     ONE ADDER, TWO SELECTORS
           SRC_TERM = L    if lo12[4:0] == 0
                    = 0    if f31 == 0
                    = acc  otherwise
           P_TERM   = 0    if f31 == 2
                    = P    otherwise
  if class4 == A:      P := (coef[cursor++] * L) >> 6
  if class4 & 7 == 2:  p += (s8)addr8
```

The single adder is **FORCED**: two independent passes reached opposite orderings, and both demand
the expression `bus + P`, which no ordering delivers and one adder does.

**Fixed point** — MEASURED live: `P = (coef[N-1] × L[N]) >> 6` with the coefficient latched one
word early and the operand one slot late (`L[N] = mem[N-1]`); one-slot accumulator pipeline; store
`datum = acc >> 16`.

⚠ The **total** scale is contested — shift 22 rails 19 of 48 biquad state cells where shift 23
rails none, while a counter-proposal is refuted on other evidence. The *relative* datapath is not
in doubt.

### 4.5 Control flow — PROVEN BY CONSTRUCTION

Hardware PC restart per frame; a resident kernel of two canned blobs (header + output stage); a
**two-level call stack** with entry addresses in host-loaded registers, not a vector table; and
**straight-line, hand-unrolled bodies** — an exhaustive field scan for a branch instruction is
negative, and one program repeats 32 words at period 8 varying only `addr8`.

⚠ Loop counters `LC1`-`LC3` appear in the pin table's feature list but no encoding has been found.
One word = one slot, 285 slots per frame, holds in all 91 programs.

---

## 5. What is not known

| unknown | why it resists |
|---|---|
| `f31` 3, 4, 5, 6, 7 | Separable and reproducible, but their carrier programs are ones no anchored criterion can see |
| The `lo12` bit-11 alternate encoding | 169 words; addressing and accumulator function already characterised, the encoding itself is the one unknown |
| `f98` (`hi12[9:8]`) | Proven a field; the accumulator-op-selector reading was tested and failed |
| `hi12` bits 0, 5, 7 | Bit 7 provably gates the store, but has no meaning of its own yet |
| `ACT 0x0B` off class A | Three readings survive; three separate criteria measured blind |
| `SRC 0x11`'s two write forms | A structural dependency cycle — every reachable program feeds it a frame-invariant constant |
| Class 6's table index | The word that computes it is a bit-11 word; six index sources enumerated and refuted |
| Addressing modes 3-6 | No characterised twin |
| `COND` / predication | Unobservable on both Technics boards (§3.2) |
| `MD1`-`MD4` mode straps | Undocumented anywhere |
| DRAM read latency | Forced to a window; the exact value needs the emulator mode |
| `N` in `mod 2^N` | Unobservable from software; 17 address pins bound it |

**Coverage today: 80.8 %** of 7273 distinct pooled microwords. The route from here is in
[state of play and the route to 100 %]({{ site.baseurl }}/upd6383-decode-status/).

---

## Related

| Page | Description |
|------|-------------|
| [State of play, and the route to 100 %]({{ site.baseurl }}/upd6383-decode-status/) | What is left and how to get it |
| [Effects DSP (NEC uPD6383GF)]({{ site.baseurl }}/effects-dsp/) | The full technical reference |
| [SX-WSA1 / SX-WSA1R]({{ site.baseurl }}/wsa1/) | The machine the pinout was read from |
