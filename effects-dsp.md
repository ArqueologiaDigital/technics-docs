---
layout: page
title: Effects DSP (NEC uPD6383GF)
permalink: /effects-dsp/
---

# Effects DSP — NEC uPD6383GF (IC311)

The KN5000's primary effects processor is **IC311**, an **NEC uPD6383GF-3BA** — a
24-bit fixed-point audio DSP with an external delay-DRAM controller. It runs the
reverbs, choruses, delays, EQ and dynamics effects; a second chip (IC310, an MN19413)
runs **nine** of the 100 effect-algorithm numbers — see
[Chip partition](#chip-partition-nine-effects-belong-to-ic310) below.

This page is the reference distillation of the reverse-engineering of that chip. The
narrative — how each result was found — is in the MAME development blog (Parts 78–84);
the conclusions are stated here. Confidence is labelled throughout as **PROVEN /
MEASURED**, **INFERRED**, or **OPEN**, matching the underlying research notes. Where a
claim needs real hardware to settle, it says so plainly.

> **Status.** The host upload path, word format, coefficient format, sample rate,
> memory map, control-flow model and several instruction roles are established, and two
> whole algorithms (the parametric EQ and the reverb diffuser) are decoded to the bit.
> The instruction set as a whole is **not** fully decoded — honest coverage is ~18 % of
> the microcode words. MAME now carries an experimental, opt-in partial-execution core for
> the chip (compile-time `KN5000_ENABLE_DSP1`, default off; a runtime `DSPCFG` port, also
> default off) that runs one uPD6383GF frame per tone-generator sample and logs which words
> trap — 199 of the 285 words on the frame path execute, 108 of them fully. It is a decoding
> instrument, not an audio feature: every frame is still discarded before it reaches the mix
> (0 of 1,368,001 sampled frames complete), so the default build's audio is unaffected either
> way and there is still no audio from this chip.
>
> **Update (2026-09-11) — the biquad DATAPATH is now decoded end to end.** Beyond the two
> algorithms' *transfer functions* (below), the chip's own **microarchitecture** — how a word
> multiplies, accumulates, stores and addresses — is now recovered **bit-exactly from live
> emulator traces**: multiply `P = (coef × operand) >> 6`, accumulate/load on the `hi12[3:1]`
> field, operand from the D-RAM pointer one slot late, and store `datum = acc >> 16`. Both
> fixed-point shifts (`P_SHIFT = 6`, `ACC_SHIFT = 16`) are confirmed from the data, and the
> multiplier form reproduces across two different programs. See [§10](#10-the-biquad-datapath-decoded-end-to-end-lle-2026-09-11). The remaining gap to
> *audible* LLE is the **input route** (audio reaches the chip's DI-latch cells but the
> stage that carries it into the effect bodies is undecoded) — a short, enumerated list of
> open routing codes, not a fog.

This page supersedes, in part, the older
[DSP Bytecode Interpreter]({{ site.baseurl }}/dsp-bytecode-interpreter/) page, which was
written before the chip was identified and refers to it by the wrong part number. That
page remains correct about the **Sub CPU-side** bytecode interpreter (the mechanism that
*uploads* configurations); everything it says about the DSP chip's own architecture is
refined here. See also the [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) for how
the Sub CPU reaches the DSP in the first place.

The **data** the Sub CPU uploads — the per-effect microprogram/coefficient bytecode
streams and the parameter record tables, all 39,372 bytes of them — now has its own
reference page:
[DSP Effect Data Zone (Sub-CPU ROM)]({{ site.baseurl }}/dsp-effect-data-zone/). That
page carries the block-by-block address map; this page states the conclusions drawn
from it.

---

## 1. The chip

**NEC uPD6383GF-3BA**, 100-pin QFP, Panasonic service-parts code GGC1163.

For years this part was recorded in the project's notes as *"DS3613GF-3BA, a custom ASIC
with no public documentation."* That was a **transcription error** — the marking is
`uPD6383GF-3BA`. The correct identification came from the **Pioneer CDJ-500 / CDJ-500G
service manual** (order RRV1087), which documents the very same part as **IC302** and
includes a block diagram and a 100-pin description. It is the only substantial public
document for the chip.

No datasheet, databook page or programming manual for the uPD6383 exists on the public
web (**verified** exhaustively: it is absent from every NEC databook and from NEC's own
October 1996 selection guide, and even distinctive strings from its CDJ pin table return
zero hits worldwide). It was a set-maker ASSP, sold direct and never catalogued. Its
documented sibling, the **uPD6380** (used in NEC's own PC-98GS / PC-9801-73 sound board),
was likewise never published and never reverse-engineered. **The instruction set has had
to be inferred from the microcode itself.**

### Architecture (from the CDJ-500 block diagram — PROVEN for the block level)

| Block | Detail |
|---|---|
| Instruction RAM (I-RAM) | **384 words × 36 bits**, uploaded by the host; both effect units resident at once |
| Coefficient / data RAM | Two **256 × 24-bit** internal spaces (C-RAM and D-RAM) plus a bank register |
| Multiplier | **24 × 24** fixed-point |
| ALU | **44-bit**, with two accumulators (**ACCA / ACCB**) and two shifters |
| Delay memory | On-chip controller for **external DRAM**; ring-buffer address generation (echo / reverb-A / reverb-B regions) |
| Audio I/O | Serial audio in/out, **three DI and three DO ports — all six wired on this board** (corrected 2026-07-26; the earlier "one stereo pair" reading was falsified by the schematics). LRCKI selects L/R on every line. |

### Signal topology — IC311 is a SEND/RETURN INSERT (MEASURED, service manual)

IC311 is **not** in the main output path. It hangs off the tone generator:

```
IC303.SDOA -> DI1        DO1 -> IC303.SDIA
IC303.SDOB -> DI2        DO2 -> IC303.SDIB
IC303.SDO1 -> DI3        DO3 -> leaves the block (destination open)

main mix:  IC303.SDO0 -> IC310 (DSP2) -> IC313 PCM69AU DAC -> analog board
```

The wet output returns *into* IC303, which mixes it; the main mix leaves on a different bus.
**Consequence: nothing IC311 does can remove or attenuate the dry sound — it can only add.**
The per-sample frame restart is the chip's internal PC-RST cadenced by **LRCKI, which IC303
generates**; the Fs-RST and Fs-MASK pins are strapped inactive on this board.

### Board facts (verified on the KN5000 by Felipe)

* **25 MHz** master clock on IC311.
* Delay DRAM = **M5M44260AJ** (IC309), the external reverb/delay memory.
* **Sample rate = 44,100 Hz** — **PROVEN three independent ways**:
  1. the firmware's own millisecond→samples conversion `ms × 0xAC44 / 0x3E8`;
  2. a ROM `double` constant equal to `pi / 44100` (`0x012F57`), used by the biquad
     designer;
  3. the LFO rate constants — nine effect defaults decode to round numbers of Hz
     (0.2, 0.4, 0.6, 1.2, 3.0, 4.0, 5.2, 7.4, 1000 Hz) only under 44,100 Hz, and miss a
     0.1 Hz grid by up to 8.7 % at 48,000 Hz.

---

## 2. How programs reach the chip

The Sub CPU (TMP94C241F) is the host. It reaches the DSP through a **parallel
microcontroller interface** — port **PZ** carries an 8-bit data byte, and port 7 supplies
the strobes: command/data select (C/D), write (`/WR`), read (`/RD`) and chip select
(`/CS`). Status bits (ready, read-busy, I-RAM-modify, GF, OVF) are polled back. This is
the physical layer documented on the
[Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) page.

Above that sits the Sub CPU's **bytecode interpreter**
([its own page]({{ site.baseurl }}/dsp-bytecode-interpreter/)): compact ROM-resident
programs that expand into the sequences of register writes which upload a microprogram
and stream its coefficients. A **36-bit instruction word is packed into 5 bytes**
(right-aligned big-endian; bits 36–39 are always zero). A **coefficient is 3 bytes**,
signed **Q0.23** for static program constants (the value `0x517CC1 = 2/π` recurs 53
times). Parameter-path biquad coefficients are written per-word as Q1.22 or Q0.23 instead.

"One algorithm, many coefficient banks" is now an exact count. Reading the four 100-entry
pointer arrays straight out of the payload image gives, across the 100 effect-algorithm
numbers, **41 distinct algorithm bytecode streams**, **59 distinct coefficient streams**,
**41 distinct parameter-descriptor tables** and **59 non-empty parameter-value tables**
(the earlier "~40 microprograms" estimate was right). The arrays are at Sub-CPU
`0x01ED7C` (algorithm), `0x01EF0C` (coefficients), `0x01F09C` (parameter values) and
`0x01F22C` (parameter descriptors); the
[DSP Effect Data Zone]({{ site.baseurl }}/dsp-effect-data-zone/) page lists every entry.
The collapse from 100 to 41 comes from deliberate pointer sharing: the twelve standalone
reverbs share one microprogram, ROCK ROTARY shares ROTARY SPEAKER's, the two IC310 groups
share one each — and 42 effect numbers share a single **NO OPERATION** program (§6).

---

## 3. The instruction word

Each 36-bit word divides into four fields (**MEASURED**):

```
   hi12[35:24] . class4[23:20] . addr8[19:12] . lo12[11:0]
```

* **`hi12` is not an opcode — it is a horizontal microword of independent enable bits**
  (**MEASURED**: values one bit apart recur far more than an enumerated field would
  allow, `z = +7.9`). Three of its twelve bits have assigned meanings:
  * **bit 4 = write the accumulator to `mem[ptr]`** (a store);
  * **bit 10 = end of block** (with bit 11 clear); the terminating instruction still does
    its datapath work — it is a modifier, not a halt code;
  * **bit 11 = format escape** (selects a second word format used by host-poke and
    DRAM-bracket words).
  Bits [9:8] and [3:1] are proven to be *fields* but their meaning is **OPEN**; the rest
  are unassigned.
* **`class4` = a cursor-fetch enable (bit 23) plus a 3-bit `MODE = class4 & 7`.** Bit 23
  was **corrected**: it is *not* a multiply-enable (eighteen phaser all-pass sections
  multiply with no class-A word), but a **cursor-fetch** enable — a class-A word pulls the
  next coefficient from the implicit cursor.
* **`addr8`** is, in the addressing modes (`class4 & 7 == 2`), a **signed post-increment**
  applied to an 8-bit data pointer that **wraps mod 256** (INFERRED, with a measured
  floor). In other modes it is frozen to a constant or is a table selector.
* **`lo12`** carries operand routing and some ALU-step identity (e.g. `0x647`/`0x687` =
  latch-store steps, `0x44C` = apply modulation offset).

The source-operand routing lives in `lo12`, and its dominant code is settled.
**`SRC 0x00`** — the value on 599 words, 572 of them exactly `lo12 == 0x000` —
reads **`mem[ptr]`**, the current data-pointer cell, and that is the reading the
emulator ships. Of the six candidate readings it was tested against, four
(`zero`, the `P` register, the delay-RAM read register `DR`, and `tempA`) leave
no survivor in the one block that forces `SRC 0x00` to carry data, and the only
rival, the accumulator `acc`, becomes reachable only if a host parameter write
gives the input-mix words a non-zero gain — which the factory coefficients never
do. The tempting "`lo12 == 0x000` is a null routing" reading is **falsified**:
the single-delay block needs `SRC 0x00` to carry its input. ⚠ This is one
routing code; most of `lo12`'s codes, like most arithmetic words, remain OPEN.

Two implicit cursors run alongside the word stream: the **coefficient cursor** (+1 per
class-A word, reset by `801.0.00.021`) and the **data pointer** just described.

**What is OPEN.** The **absolute origin** of the data pointer cannot be pinned from the
ROM — the per-unit base is reset by the header to a value the instruction stream never
names (unit 0 = `0x70`, unit 1 = `0x50`, loaded via register `0x821`), and every static
falsifier is a *difference*, hence origin-free. The **audio-input** instruction, the
meaning of most individual arithmetic words, and the `COND`/`BRAKST` control fields named
in the CDJ pin table are all unidentified. **Honest coverage is ~18 %** (545 of 2974
microcode words) — the structural results are worth far more than that number, but the
number is reported straight.

### Control flow (PROVEN BY CONSTRUCTION)

The program is **restarted by the sample clock** — there is no software frame loop. Per
sample, the PC is reset to 0; a 60-word **common header** runs the input stage, LFOs and
mixes, then **calls unit 0's body and, on return, unit 1's body**, using a shared
call/return encoding (`class4==1 && addr8 ∈ {0x0E, 0x0F}`, the unit tag) on a two-level
stack; a 23-word epilogue does the output/effect-return stage and waits for the next
sample edge. The effect **bodies are straight-line and hand-unrolled** — there is no loop
in a body, which is why an exhaustive search for a branch instruction found none. The
per-frame instruction budget (~286–326 slots) fits comfortably inside the 25 MHz clock at
44.1 kHz.

---

## 4. The algorithms solved to the bit

### Parametric EQ — a bilinear-transform biquad (PROVEN BY CONSTRUCTION)

The `PARAMETRIC EQ` effect (5 bands × 2 channels) is fully decoded. Each band is a
second-order section whose coefficients are computed at run time — not tabulated — by a
software floating-point **biquad designer** in the Sub CPU (`LABEL_03A933`, reached by
parameter opcode `0x70`). It:

* reads the three user values as **frequency in Hz** (ISO ⅓-octave table, 40 Hz…16 kHz),
  **Q** (0.1…20), and **gain in dB** (−12…+12 in 0.5 dB steps);
* computes `K = tan(pi·f0 / 44100)` in IEEE double, then the classic
  `a0 = 1 + K/Q + K²`, `a1 = 2(K²−1)`, `a2 = 1 − K/Q + K²`;
* emits **five** coefficients — `b1, b0, b2, −a1/a0, −a2/a0` — the recursive pair stored
  **negated** so the DSP runs a pure multiply-accumulate. (A "sixth coefficient" in an
  earlier note was **falsified**: it is padding.)
* implements *cut* by reciprocating the whole section, not by inverting the poles.

The DSP-side realisation is **Direct Form I** with four state cells `{x₁, x₂, v₁, v₂}`,
recovered by an exhaustive constraint search (19,674,720 candidate assignments → one
dataflow). Two of the four state writes are folded into multiply instructions, which is
why the topology "refused every textbook form" for so long. Running the recovered
semantics as an interpreter against the transfer function computed from the same ROM
words gives **`max|err| = 0.000e+00`** (bit-identical) on nine real coefficient blocks,
and the full 42,336-preset design grid is **0 unstable**, with f0/Q/gain recovered to
~1e-10.

### Reverb — pre-delay into all-pass diffuser ladders (MEASURED counts / INFERRED dataflow)

The reverb (the corpus's only unit-1 program) is a pre-delay feeding **nine first-order
all-pass diffusers arranged in two descending-gain ladders** (five + four; gains read
live from `CONCERT REVERB 1` as `0x98…0x9C | 0xA1…0xA4`), plus damping filters and
recirculation. The 8-word all-pass motif matches the **only** first-order all-pass
realisable with a single multiply, on instruction *count and position*, not by fitting.
With the ROM's own gains and delay lengths every stage is a **true all-pass** to nine
digits (impulse energy 1.000000000) and the nine-stage cascade is a dense, colourless
diffuser (28 taps/ms). Its decay comes from the damping filters and recirculation
*outside* the motif — the diffuser alone is loss-less by construction, so "does it decay
like a reverb" is **not** answered by the diffuser and is flagged as such.

### Modulation — a quadrature LFO-swept delay (STRONG, by composition)

Tracing `CHORUS` end to end shows it is a textbook **LFO-modulated delay**, built entirely
from fields decoded independently by cross-program correlation: an **LFO phase accumulator**
(`phase += increment`, then a wrap against the MEASURED `0x7FFFFF` = 2²³−1 mask) drives a
**class-6 waveform lookup**, whose output sweeps the read tap of a delay line; the wet taps
are scaled by a near-unity makeup gain (C-format load to register `0x44C`). The **number of
distinct LFO-waveform tables an effect reads is its detuned-voice count** — `ENSEMBLE` reads
four (`0x18/1A/1E/20`), the chorus family two (a quadrature pair, `0x18`+`0x20`), and
`FLANGER / PHASER / VIBRATO / AUTO PAN / RING MODULATOR` one. This is literally why a chorus
sounds richer than a vibrato and an ensemble richer than a chorus, and it is identical on
both products.

### Distortion — pre-gain · waveshaper · optional tone filter (STRONG, by composition)

The distortion family is a static-curve waveshaper with an AGC around it: **input → drive
gain → waveshaper table (class-6 selector `0x28`) → output level**, run per stereo channel.
Whether a second-order tone filter sits in the chain, and where, separates the named effects:
`FUZZ` and `DISTORTION` are the bare curve; `OVERDRIVE` and `EXCITER` add a **post** tone
filter that smooths the clipping harmonics; the `PEQ+DIST / PEQ+OVERDR` combinations put a
full parametric **pre**-EQ ahead of the drive. The curve itself is C-RAM data, not code.

### Two filter primitives, not one (STRONG)

The chip realises filters two different ways, and they separate cleanly by effect family. The
parametric EQ uses the **Direct-Form-I latch biquad** above (`ld.ta`/`mac.tb`/a class-8
normalise step/makeup) — and *only* the EQ, PEQ-combo and wah programs do (91 % of its
section-entry op). Every other family — reverb, modulation, delay — instead uses a general
**two-state update pair** (a `z⁻¹`/`z⁻²` op-pair that is adjacent in 80 % of the corpus) for
the resonant and damping filters inside its feedback paths. An emulator therefore needs both
kernels; conflating them is a mistake. The parametric EQ is the same Direct-Form-I biquad on
both products (KN5000 five bands, SX-WSA1R six), whereas the reverb primitive genuinely
differs between them (§8) — "same effect name" does not imply "same algorithm".

*(Grades above are STRONG: each is a composition of individually-decoded, mostly-measured
fields, cross-checked across both products, but not an exhaustive constraint proof like the
EQ. Full evidence and the reproducing tools are in the disassembly repo's
`dsp/analysis/DECODE-by-correlation-2026-09-08.md` and `EFFECT-ALGORITHMS-implementation-spec.md`.)*

---

## 5. The complete effect + parameter catalogue

This is the newest and most complete result: **50 distinct effect algorithms**, each with
its ordered, named, unit-tagged parameter list — **read live from Sub CPU RAM** while the
edit page was on screen in MAME, and **pixel-verified against the LCD**. The binding
mechanism (a per-effect array of name indices at RAM `0x29AC` into an 85-name table in the
main-CPU program) is confirmed end-to-end.

Two universal tails recur: every DSP-effect list ends with **VOLUME** then **REV SEND**
(the send to the reverb bus); the standalone reverbs drop REV SEND (a reverb *is* the
bus). Parameter names bind to the actual DSP writes — **HIGH DAMP GAIN** appears only on
reverbs and delays, **THRESHOLD / RATIO** only on the compressor, **LFO SPEED / LFO
WAVEFORM** only on LFO effects, and the EQ's five **BAND EMPHASIS FC/Q/G** triples are
exactly the solved biquad's five bands.

### DSP EFFECT page (38 effects, in TYPE-selector order)

| # | Effect | Parameters (in order) |
|---|--------|-----------------------|
| 0 | CHORUS | DEPTH, LFO SPEED, LFO WAVEFORM, VOLUME, REV SEND |
| 1 | MODULATED CHORUS | DEPTH, SLOW LFO SPEED, FAST LFO SPEED, FAST LFO BALANCE, LFO WAVEFORM, VOLUME, REV SEND |
| 2 | ENHANCER | MANUAL, LOW MIX, HIGH MIX, DELAY L, DELAY R, VOLUME, REV SEND |
| 3 | FLANGER | DEPTH, LFO SPEED, RESONANCE, MANUAL, PHASE, LFO WAVEFORM, VOLUME, REV SEND |
| 4 | PHASER | DEPTH, LFO SPEED, RESONANCE, MANUAL, PHASE, LFO WAVEFORM, VOLUME, REV SEND |
| 5 | ENSEMBLE | DEPTH, LFO SPEED, LFO WAVEFORM, VOLUME, REV SEND |
| 6 | GATED REVERB | GATE TIME, HIGH DAMP GAIN, THRESHOLD, MASK TIME, VOLUME, REV SEND |
| 7 | SINGLE DELAY | DELAY L, DELAY R, FEEDBACK L, FEEDBACK R, HIGH DAMP GAIN, VOLUME, REV SEND |
| 8 | MULTI TAP DELAY | DELAY 1–4, PAN 1–4, FEEDBACK, HIGH DAMP GAIN, VOLUME, REV SEND |
| 9 | DISTORTION | DRIVE, ADJUST, VOLUME, REV SEND |
| 10 | OVERDRIVE | DRIVE, ADJUST, VOLUME, REV SEND |
| 11 | FUZZ | DRIVE, ADJUST, VOLUME, REV SEND |
| 12 | EXCITER | DRIVE, ADJUST, HIGH EMPHASIS FC, EMPHASIS GAIN, VOLUME, REV SEND |
| 13 | COMPRESSOR | THRESHOLD, RATIO, ATTACK SENS., RELEASE SENS., VOLUME, REV SEND |
| 14 | SLOW ATTACKER | THRESHOLD, ATTACK RATE, RELEASE RATE, VOLUME, REV SEND |
| 15 | PARAMETRIC EQ | (BAND EMPHASIS FC / Q / G) × 5 bands, VOLUME, REV SEND |
| 16 | AUTO PAN | DEPTH, LFO SPEED, PHASE, LFO WAVEFORM, VOLUME, REV SEND |
| 17 | VIBRATO | DEPTH, LFO SPEED, PHASE, LFO WAVEFORM, VOLUME, REV SEND |
| 18 | AUTO WAH | RESONANCE, MANUAL, SWEEP RANGE, VOLUME, REV SEND |
| 19 | ROTARY SPEAKER | DRIVE, VOLUME ADJUST, TREBLE DEPTH, TREBLE FAST, TREBLE SLOW, TREBLE WIND UP/DOWN, BASS DEPTH, BASS FAST, BASS SLOW, BASS WIND UP/DOWN, VOLUME, SLOW/FAST, REV SEND |
| 20 | ROCK ROTARY | (identical to ROTARY SPEAKER) |
| 21 | RING MODULATOR | OSC SPEED, PHASE, LFO WAVEFORM, VOLUME, REV SEND |
| 22 | MIX UP | DEPTH, SLOW LFO SPEED, FAST LFO SPEED L, FAST LFO SPEED R, PHASE, LFO WAVEFORM, VOLUME, REV SEND |
| 23 | S. DELAY + CHORUS | DELAY DRY/WET, DELAY L/R, FEEDBACK L/R, CHORUS DRY/WET, DEPTH, LFO SPEED, LFO WAVEFORM, VOLUME, REV SEND |
| 24 | S. DELAY + S. DELAY | (two single-delay blocks) VOLUME, REV SEND |
| 25 | S. DELAY + FLANGER | delay block + FLANGER block, VOLUME, REV SEND |
| 26 | S. DELAY + VIBRATO | delay block + VIBRATO block, VOLUME, REV SEND |
| 27 | S. DELAY + PHASER | delay block + PHASER block, VOLUME, REV SEND |
| 28 | AUTO WAH + S. DELAY | RESONANCE, MANUAL, SWEEP RANGE, delay block, VOLUME, REV SEND |
| 29 | PEQ + CHORUS | BAND EMPHASIS FC/Q/G, CHORUS DRY/WET, DEPTH, LFO SPEED, LFO WAVEFORM, VOLUME, REV SEND |
| 30 | PEQ + S. DELAY | BAND EMPHASIS FC/Q/G, delay block, VOLUME, REV SEND |
| 31 | PEQ + FLANGER | BAND EMPHASIS FC/Q/G, FLANGER block, VOLUME, REV SEND |
| 32 | PEQ + VIBRATO | BAND EMPHASIS FC/Q/G, VIBRATO block, VOLUME, REV SEND |
| 33 | PEQ + COMPRESSOR | BAND EMPHASIS FC/Q/G, THRESHOLD, RATIO, ATTACK/RELEASE SENS., VOLUME, REV SEND |
| 34 | PEQ + COMPR + DIST | PEQ + compressor + DRIVE/ADJUST, VOLUME, REV SEND |
| 35 | PEQ + COMPR + OVERDR | (identical to PEQ + COMPR + DIST) |
| 36 | PEQ + DIST + DELAY | PEQ + DRIVE/ADJUST + delay block, VOLUME, REV SEND |
| 37 | PEQ + OVERDR + DELAY | (identical to PEQ + DIST + DELAY) |

`S. DELAY` = SINGLE DELAY; `PEQ` = PARAMETRIC EQ; a "delay block" = DELAY DRY/WET, DELAY
L/R, FEEDBACK L/R. Effects sharing an identical parameter list (FLANGER ≡ PHASER in UI,
DISTORTION ≡ OVERDRIVE ≡ FUZZ, ROTARY ≡ ROCK ROTARY) differ only in DSP coefficients, not
in the exposed parameter set.

> The `#` column above is the **TYPE-selector position**, not the effect-algorithm number
> used everywhere else on this page and in the ROM tables. The mapping is not the identity:
> selector 14 (SLOW ATTACKER) is effect-algorithm **37**, selector 15 (PARAMETRIC EQ) is
> effect **39**, and so on — the
> [DSP Effect Data Zone]({{ site.baseurl }}/dsp-effect-data-zone/) table is indexed by the
> algorithm number. Selector 14 / effect 37 is a **stub** (§6): the parameter page is real,
> the program behind it is NO OPERATION.

### DIGITAL REVERB page (12 reverbs + 2 delays)

All twelve standalone reverbs share **one** parameter list:

| Effect(s) | Parameters |
|---|---|
| ROOM 1/2, PLATE 1/2, CONCERT 1/2, DARK 1/2, BRIGHT 1/2, WAVE 1/2 | REVERB TIME, PRE DELAY, HIGH DAMP GAIN, ER. LEVEL, VOLUME |
| SINGLE DELAY (reverb page) | DELAY L, DELAY R, FEEDBACK L, FEEDBACK R, HIGH DAMP GAIN, VOLUME |
| MULTI TAP DELAY (reverb page) | DELAY 1–4, PAN 1–4, FEEDBACK, HIGH DAMP GAIN, VOLUME |

The **EQUALIZER** (master 4-band) and **ACOUSTIC ILLUSION** pages use fixed hard-coded
layouts rather than this array and are outside the 50-effect catalogue.

---

## 6. Twelve named effects are stubs (ROM-VERIFIED)

Of the 100 effect-algorithm numbers, **42 point all three of algorithm bytecode,
coefficient bytecode and parameter descriptors at one shared trio** — the **NO OPERATION**
program at Sub-CPU `0x017263` / `0x01735E` / `0x017425`, a dry pass-through that still
runs a level detector. This is **pointer sharing, not duplication**: the 42 entries in the
`0x01ED7C` array hold the identical value `0x017263`, and no second byte-identical copy of
the program exists anywhere in the effect data zone.

Twenty-nine of the 42 are the unnamed `----------` placeholders in the main-CPU effect-name
table, which is unsurprising. The other thirteen carry real names — effect **0 NO
OPERATION**, plus **twelve named effects that the firmware ships as a dry pass-through**:

| # | name | # | name | # | name |
|---|------|---|------|---|------|
| 11 | MODULATION DELAY | 45 | CELM | 63 | STRING |
| 37 | SLOW ATTACKER | 49 | PITCH SHIFTER | 69 | PEDAL WAH+DELAY |
| 38 | NOISE FLANGER | 51 | PEDAL WAH | 80 | DS_D |
| 44 | CEL | 55 | HARS EFFECT | 81 | OVER_D |

Names are read from the main-CPU name table (`0x033568 - 18n`, stride 18 descending).
Only one of the twelve — SLOW ATTACKER — appears in the TYPE-selector list captured in §5;
the other eleven names are in the name table but were never seen offered by that selector.

**Effect 37 SLOW ATTACKER is the interesting one.** It is the *only* member of the 42 with
its own live parameter **value** table (`0x0173F2`) and a real 5-slot UI page — THRESHOLD /
ATTACK RATE / RELEASE RATE / VOLUME / REV SEND — yet those parameter writes land on the
dry pass-through program. That makes it the one stub worth testing on real hardware, and
the prediction is falsifiable: it should be **indistinguishable from no effect**. If it
audibly does something on a real KN5000, the algorithm-selection path substitutes a program
the algorithm table does not name, and the model above is wrong.

### Chip partition: nine effects belong to IC310

**Nine** effect numbers are **IC310 (MN19413)** programs, not uPD6383 programs:
**57 STANDARD, 58 PERCUSSIVE, 59 SYMPHONIC, 60 DEEP SPACE** (the ACOUSTIC ILLUSION types),
**79 GEQ, 88 ROOM, 89 KARAOKE, 90 BATH ROOM, 91 STAGE**. The criterion is mechanical: their
bytecode streams are the only ones carrying `0x0E`-opcode records whose first payload byte
is the DSP2 register-write command `0x30`. Walking all 200 algorithm/coefficient streams
with that test returns exactly that set of nine and nothing else.

An earlier note counted **five** ("the malformed streams") — that count came from a
uPD6383-shaped parser choking on five of them and is superseded. Their descriptor bytes are
IC310 parameter-word addresses, *not* uPD6383 cell numbers, so nothing in §3 or §4 of this
page applies to them; in the disassembly their labels carry a `DSP2_` prefix.

Note that the chip a *slot* talks to is a separate lookup: the byte table at Sub-CPU
`0x01ED6D` holds `0, 0, 1, 1, 1` for effect slots 0–4, i.e. slots 0–1 are IC311 and slots
2–4 are IC310.

---

## 7. What still needs real hardware

The reverse engineering behind the conclusions above is entirely **static** — none of it
depends on the chip or an emulator actually completing a frame. MAME's own draft core (§ above)
does not change that: it is gated off by default, and every frame it attempts still traps and
is discarded before reaching the mix, so it has not produced a validated result either. Five
things need a running core (a real uPD6383, or MAME's once it can complete a frame) and are
honestly OPEN:

1. **The absolute pointer origin** — a single address-bus read on the first data access
   after the header would convert every `addr8` in the corpus into a real address.
2. **The audio-input instruction** — the input stage is *located* (header blocks 0–1) but
   no word is decoded.
3. **Direct confirmation of the mod-256 pointer wrap** (INFERRED from a measured floor).
4. **Validation of the whole chain against a real impulse response** — the biquad and
   diffuser are proven against the firmware's own arithmetic, which is strong but is not
   the same as measuring the physical chip.
5. **SLOW ATTACKER on a real KN5000** (§6) — the one stub that carries live parameter
   values. Static analysis predicts "no audible effect"; only the instrument can settle it.

A datasheet would retire most of the remaining inference in one stroke; none has been
found, and the search is documented as exhausted.

---

## 8. The same chip on the SX-WSA1R — three instances (MEASURED, 2026-09-07)

The 1995 **Technics SX-WSA1R** rack synthesizer carries **three** of this exact chip
(uPD6383GF: IC5, IC6, IC30), and its firmware is fully dumped — so the same ISA model
disassembles it, and it is a second, independent silicon witness for every conclusion above.

- **Every effect program is now listed and commented.** The WSA1R's P7 stream pool holds
  the effect microcode; each of its **56 named effects** resolves (via
  `PoolDir_RecordForUnitProgram` → `PoolDir_Records` field +12) to an I-RAM program body.
  All 48 with a distinct body are disassembled — mirror of this page's KN5000 tree — in the
  repo at `kn5000-roms-disasm/wsa1/dsp/disasm/` (`gen_wsa1_dsp_disasm.py` regenerates it).
- **The algorithms are the same, confirmed structurally.** The `PARAMETRIC EQ` is the same
  Direct-Form-I bilinear biquad as the KN5000's SOLVED one — identical `[5,2]` coefficient-band
  pattern, 6 bands × 2 channels versus the KN5000's 5 × 2 — so its decode is validated by
  construction on a second chip. `SINGLE DELAY`, the distortions, the modulation effects all
  match their KN5000 counterparts' idiom sequence.
- **One real difference: the reverbs.** The DRAM access order shows the KN5000 reverb is an
  **all-pass diffuser ladder** (read/write alternation) while the WSA1R reverb is a
  **write-heavy multi-tap / comb (FDN)** — the same effect name, a different reverb
  architecture between the two products.
- **What actually executes at runtime (MEASURED on the emulated WSA1R).** Only **one** DSP
  program is ever uploaded during normal SOUND play: a **63-word shared kernel** loaded to
  IC30 at boot (`disasm/kernel.dsm`; it contains all 45 runtime-resident words). Selecting an
  effect **re-uploads only C-RAM coefficients**, never the microcode — so the per-effect
  bodies in ROM are not loaded in play; the resident kernel is parameterised by coefficients.
  (A raw bus-capture proof is in `wsa1/dsp/analysis/dsp_bus_program_scan.py`.)

Cross-product tooling: `dsp/tools/dsp_topology_fingerprint.py` (idiom counts vs the textbook
algorithm), `dsp_idiom_sequence.py` (per-word structure), `dsp_residue_sudoku.py` (the
prioritised decode roadmap over both corpora, 1002 distinct words, 86.7 % executable).

---

## 9. A high-level-emulation reference now makes the effects audible (2026-09-10)

Section 7 is about the *low-level* core (executing the microcode) and hardware; it stands. But
the decode is now complete enough to implement each effect's **behaviour** directly, and that
reference exists and runs: `dsp/hle/` in the disassembly repo. It is **HLE, not LLE** — it
reproduces the transfer function / block diagram of each effect, not the chip's 36-bit
execution — and it is deliberately not wired into the delicate LLE device.

Every effect is a wiring of four kernels — a Direct-Form-I biquad, a one-pole damping filter, an
LFO (phase accumulator → shaped table), and a delay line — plus a waveshaper, driven by the
host-side coefficient designers (the bilinear peaking-EQ formula, the ms→samples delay, the LFO
rate). It is self-validating: the parametric-EQ band reproduces its solved biquad **exactly**
(+12.00 dB peak at f₀; impulse response equal to the analytic transfer function to **0.000 dB**);
the reverb all-pass diffuser is flat and unity-energy; the KN5000 reverb is the proven nine-stage
all-pass ladder; distortion adds harmonics; the multi-band EQ boosts and cuts as designed. Fed
the **real coefficients captured from the running SX-WSA1R chip**, all twelve captured biquad
sections are stable in the decoded `b1,b0,b2,−a1,−a2,makeup` order (the recursive term stored as
`−a`) — the reference runs that chip's own numbers.

> **⚠ Convention note (2026-09-11):** the "12/12 stable" result above is the **SX-WSA1R** capture,
> where the stored recursive coefficient is `−a` (so `a = −stored`). The **KN5000's own** EQ
> coefficients, captured live this session, are **NOT** stable in that convention — in the naive
> `a = −stored` reading a pole lands at 1.001 (a positive-feedback runaway). The KN5000 EQ is a real,
> stable peaking filter (poles ≈ 0.71) only under the **opposite sign**: the stored recursive value
> is the true `+a`, i.e. the feedback **subtracts**. So the two products, though the same DSP core,
> use **different recursive-coefficient conventions**; do not carry the WSA1R sign over to the
> KN5000. See [§10](#10-the-biquad-datapath-decoded-end-to-end-lle-2026-09-11) and
> `dsp/tools/biquad_stability_probe.py`.

The SX-WSA1R acoustic-modeling LSI (L7A1429) has a matching reference (`wsa1/hle/`): coupled
digital-waveguide resonators that ring at pitch, sustain and decay autonomously (the chip has no
key-off), with `MUTING` as loop damping and a `SUB GAIN` coupling. Two inputs remain honest
stand-ins, each behind a switch: the `DRIVER` excitation (IC4's wave mask ROMs are undumped) and
the `POSITION` absolute scale (needs a hardware trace). So it is a faithful realization of the
**documented model**, not the instrument's exact sound.

⇒ "no audio from this chip" (§7) remains true of the *emulated hardware path*; what is new is a
validated behavioural reference — the payoff of the paper decode, and the model a future MAME HLE
path would port in (`dsp/hle/PORTING-TO-MAME.md`).

---

## 10. The biquad datapath, decoded end to end (LLE, 2026-09-11)

Sections 4 and 9 give the effects' *transfer functions* (what each block computes) and a
behavioural HLE reference. This section is the complementary result: the chip's **datapath**
— the actual per-word arithmetic the microcode drives — recovered **bit-exactly from live
emulator frame traces** of the running parametric-EQ program. The method is a falsifiable,
over-determined fit: take the chip's own product/accumulator columns as ground truth and
require a *single* model to reproduce them across many words of distinct coefficients at once.

**The multiplier — MEASURED.** `P[N] = (coef[N-1] × L[N]) >> 6`. Three facts fall out
together, bit-exact on **27 of 27** in-band MAC words (the nearest rival model matches 11):

* the **coefficient is latched one word early** (a depth-1 coefficient pipeline);
* the operand is the **current-row latch** `L`, which is the D-RAM cell at the pointer read
  by the *previous* word (`L[N] = mem[N-1]`), i.e. the microword's own addressing, one slot late;
* the shift is **6** — an independent live confirmation of the documented `P_SHIFT`.

The same `(coef[N-1] × L[N]) >> 6` reproduces on a **second, unrelated program** (the boot
default, running a real note — 18 of 21 words, the three misses being frame-startup words
whose product register still holds the previous frame's accumulator). So it is the chip's
**general** multiplier, not an EQ-specific coincidence.

**The accumulator — MEASURED.** The `hi12[3:1]` field (called `f31`), left **OPEN** in §3, is
now read: **0 → `acc ← P`** (load), **1 → `acc += P`** (accumulate), **2 → hold**. The
accumulate is a one-slot pipeline — `acc[N] = acc[N-1] + P[N-1]`, the product formed at one
word lands in the accumulator at the next — and the load form was verified on 8 of 8 load
words. Codes **4–7 remain OPEN**: `f31 = 5` is genuinely anomalous (it behaves as
accumulate, then hold, then a partial `≈ 5/6·P` across its occurrences — not one clean op,
and not bit-exact), and it lives in the shared kernel, effect-independent.

**The store — MEASURED.** A band's output is written down to a 24-bit datum as
**`datum = acc >> 16`** (an independent live confirmation of the documented `ACC_SHIFT = 16`),
bit-exact on all four cascaded bands. That datum feeds the next band's input cell — the
cascade. (It was decoded with a deliberately *small* injected stimulus so the output would
not saturate at the store; the full-scale stimulus that proved the datapath is *live* had
railed it.)

**The coefficient layout — partially decoded (Phase-2 progress).** Read directly from the
addressing (no longer assumed): each EQ band multiplies its **input cell by `b0 = 0.125`**
in *every* band — the parametric-EQ signature, confirming the input cell is `x0` — then reads
its neighbours in a fixed order that is **not** the SX-WSA1R `[b1,b0,b2,−a1,−a2,makeup]`
order (which is why feeding the KN5000's coefficients in that order is unstable). The exact
`x1/x2` vs `y1/y2` role assignment still needs a cross-frame capture (how the delay line
shifts between frames) and is **OPEN**.

**The reverb datapath — same multiplier, plus a delay-line.** The reverb (unit 1) reads its
feedback operand as the delayed output from the external delay DRAM into `tempB` (source
`SRC 0x1A ← SRC 0x0B` delay read) and multiplies it by its gains (e.g. `0.91`) with the **same
class-A MAC** as the biquad — consistent with the all-pass ladder identity in §4. (An earlier
draft here claimed the reverb "uses no class-A multiplies"; that was a class4-extraction bug —
the 0.91/`tempB` word is class-A/multiply-enabled — and is retracted.) What is genuinely open for
the reverb is the **external delay-line advance** (how the delay DRAM pointer moves per frame),
which the core's own research notes leave speculative — that pipeline is the reverb's remaining
decode target, not the arithmetic.

**The input route — LOCALISED, OPEN.** The external audio *does* reach the chip: the tone
generator's send is deposited into two D-RAM cells (the DI latches), confirmed live. What is
undecoded is the handful of input-stage words that carry those latches into the effect
bodies — a **named, enumerated** set of unanchored routing codes (source codes `0x08`,
`0x11`; action codes `0x08`, `0x0D`, `0x0E`, `0x17`), plus admitting the "operand unchanged"
accumulator code on the port-read words. Because those words are executed as addressing-only
today, their arithmetic cannot be *observed* in a trace (an unexecuted word emits no effect),
so closing this last mile is an instruction-encoding question, not a matter of capturing more
frames. **This is the single gate between the decoded datapath and audible low-level
emulation**, and every downstream stage (reverb feedback, the second-accumulator source) sits
behind it.

Every figure on this page's §10 is reproduced from committed evidence traces by
`dsp/tools/run_decode_regression.sh` in the disassembly repo (no emulator build required).

---

## 11. Every program run live, and topology matched to instructions (2026-09-11)

With the datapath decoded, two things became possible: **run every effect on the emulator** and
**match each program's shape to the textbook DSP topology it implements** — and the two together
turned several "opaque" instructions into named operations.

### Every distinct program runs, and the decode is cross-validated live

All 20 distinct DSP-EFFECT program images were selected from the panel and captured live (the rest
are the NO-OP stubs and the reverb presets that share one image). For every one, the number of
program words that execute in the live frame **matches the static disassembly's image size exactly**
(0 mismatches, corpus-wide), and the frame decomposes cleanly as **resident kernel (82 words) +
selected program image + unit-1 reverb (133 words)**. The disassembly's program sizes are now
confirmed against what the chip actually runs, not just against the ROM bytes.

The one live-vs-static gap is illuminating rather than a defect: a few class-A multiplies per program
do **not** fire in a steady frame — and they are exactly the **input/state-conditional** ops (an
LFO-phase gate, a compressor threshold). Distortion and delay fire all their multiplies; every
modulation and dynamics effect gates two or three.

### The LFO, measured live

A modulation effect's LFO is a phase accumulator — one memory cell that increments by a fixed step
each sample. Captured live, CHORUS's LFO cell ramps **+114 per frame**, exactly the value the
paper decode predicted; driving the LFO-SPEED knob up moved it to **+494 per frame**, proving the
ramp increment *is* the LFO-SPEED parameter. The modulation model is now verified on the running chip.

### Classic topologies, and what they say about the instruction set

Each program's flowchart is now annotated with the canonical topology its shape matches — cascaded
Direct-Form-I biquads (parametric EQ), a Schroeder delay / all-pass reverb tank, an LFO-modulated
delay or a swept all-pass chain (chorus/flanger vs phaser), a memoryless waveshaper with an optional
tone filter (distortion), an envelope-follower-plus-gain (compressor), and so on. Testing those
predictions against an idiom census over all 38 images gave concrete instruction-decoding gains:

- **A trio of action codes are the state-update ops of a 2nd-order section** (a biquad *or* an
  all-pass stage) — present only where the topology has such a section, and their count equals the
  number of sections: the phaser's long all-pass chain shows twenty, OVERDRIVE's single tone filter
  one, the bare FUZZ none.
- **The chip's table-lookup is one operation serving three roles** — the LFO waveform table, the
  distortion waveshaper, and the ring-modulator carrier — present in exactly those families and
  absent from the pure filters and delays.
- **A "coefficient-squaring" source code marks the LFO/envelope path**, appearing only in the
  modulation, tremolo/pan, and dynamics families.
- And a correction: an action pair previously thought to be a biquad-only delay-stage update turns
  out to be **universal** (it is in the plain delays too), so it is really a general delay/state
  mixing operation.

In short, matching each program to its classic topology, then checking the match against both the
static ROM and the live run, anchors instructions to the effect stage they serve — raising confidence
across the corpus and pinning the remaining unknowns (the audio input route into the biquad; the exact
biquad realization) as the specific things still to solve. Full detail: the disassembly repo's
`dsp/analysis/DSP-TOPOLOGY-INSTRUCTION-INSIGHT-2026-09-11.md` and the per-program flowchart
annotations.

---

## 12. The parametric EQ is now audible in MAME (2026-09-11)

The first effect from this decode now **produces audio inside the emulator**. A new, default-off
option (`DSPHLE` config port, in the DSP1-enabled build) makes the tone generator filter the dry
mix through a five-band biquad cascade — and the coefficients are read **live from the effects
DSP's own C-RAM**, i.e. from the numbers the firmware computed for whatever the player dialled on
the panel.

The path deliberately does **not** try to run the raw C-RAM cells as biquad coefficients: an
exhaustive search showed no assignment of the six cells to a peaking filter reproduces a boost
(that requires the still-open recursion/realization, §10), so reading the cells as `b/a` gives
nonsense. Instead it recovers the **design parameters** the firmware started from and rebuilds a
textbook RBJ peaking filter — the same route the offline reference uses (§9):

- **Centre frequency** comes from cell `0x03`, which holds `2·cos ω₀`; the five bands land at
  ≈ 673, 966, 1405, 2091 and 3219 Hz.
- **Gain** comes from cell `0x01`: it sits at exactly `0.5` at 0 dB (for every band, and it does
  not move when only the frequency is changed) and rises with boost, so `A² = 1 + G·(cell01 − 0.5)`.
  A +12 dB panel edit reads back as `A² ≈ 3.98`. The slope `G` is **not the same for every band** —
  each was calibrated by driving that band's gain +12 dB on the panel and reading its cell:

  | band | centre | G |
  |---|---|---|
  | 0 | 673 Hz | 465.8 |
  | 1 | 966 Hz | 225.8 |
  | 2 | 1405 Hz | 114.2 |
  | 3 | 2091 Hz | 58.3 |
  | 4 | 3219 Hz | 30.5 |

  The gain cell moves about twice as far per dB with each band up the scale (the slope roughly
  halves), so a single constant would over-boost the higher bands.

One wrinkle worth recording: the values in C-RAM at run time are at the *operand* scale — exactly
**half** the values seen in the earlier coefficient dumps (cell `0x03` reads `cos ω₀`, not
`2·cos ω₀`). This is the same factor of two noted in §10 ("operand = C-RAM ≫ 1"); the emulator
detects the scale and normalises before designing the filter.

The result was checked two ways, not by ear:

1. **Offline** — the exact formula run against three real captured C-RAM presets (flat, +12 dB
   boost, and a frequency sweep) gives 0.0 dB flat, +11.9 dB at 673 Hz for the boost, and a peak
   that migrates correctly for the frequency edit.
2. **In the emulator** — the same note played with the EQ bypassed and with it active, compared
   spectrally at two well-separated bands: a +12 dB edit produces **+10.4 dB at the 673 Hz band-0
   centre** and **+10.5 dB at the 1405 Hz band-2 centre**, each with a flat response everywhere
   else.

When the option is off, the output is bit-for-bit what it was before. All five bands' gain slopes
are now calibrated; only the exact filter Q remains an assumption (it sets bandwidth, not the peak
height the A/B checks). Reproducibility: `dsp/tools/eq_rbj_reconstruct_ab.py` (offline),
`dsp/tools/eq_band_gain_calibrate.py` (per-band gain), and `dsp/tools/eq_hle_ab.lua` +
`eq_hle_ab_fft.py` (in-emulator A/B) in the disassembly repo.

---

## 13. The single delay is now audible too (2026-09-11)

The second effect to be reconstructed from the decode. SINGLE DELAY is the seventh entry on the DSP
EFFECT page; its two parameters were located the same way the EQ's were — by an intervention that
drives one panel control and watches which decoded cell moves:

- Driving **feedback** moved exactly one coefficient, **C-RAM cell 0x00** (and its stereo twin
  0x09 for the right channel) — so that is the feedback gain (about −0.29 at the default, matching
  the documented value).
- The **delay length** is **descriptor cell 0x26 = 15437 samples = 350 ms** at the ROM default —
  precisely the figure the static decode predicted, which also confirms the effect's identity (an
  EQ has no delay descriptor).

The emulator inserts a feedback delay line per channel with these values (internal wet/dry mix ≈
0.5, the designed constant). Two wrinkles had to be handled: the delay descriptor is stored at
half scale unless the speculative-descriptor decode is enabled (a new DSPCFG option supplies it
without any low-level audio), and the descriptor counts samples at 44.1 kHz while the emulator
renders at 48 kHz, so the length is converted.

The check is **temporal**, not spectral — a delay's signature is lag. Cross-correlating the
delay-on output against the dry shows a delayed copy of the signal at **350.6 ms** — the decoded
delay time — with nothing there in the dry control. Still open, pending their own interventions:
the high-damp (in-loop tone) cell, the exact right-channel delay pairing, and the mix cell.
Reproducibility: `dsp/tools/delay_ab.lua` + `delay_ab_echo.py`.

A note on the distortion family: an earlier reading that called OVERDRIVE's post filter a
"polynomial waveshaper" has been **retracted** — that stage is the tone biquad. A second claim,
that the clipping curve is a ROM table that has not been dumped, has **also** been retracted (see
[§20](#20-distortion-is-not-undumped-either-2026-09-12)): the class-6 waveshaper reads its table
from C-RAM, and C-RAM is populated entirely from dumped ROM.

---

## 14. The chorus is now audible too (2026-09-11)

The third effect, and the first modulation effect. CHORUS is the first entry on the DSP EFFECT
page; it is a **quadrature LFO-swept delay** — a short delay line read at two taps whose delay is
swept by the sine and cosine of one slow oscillator. Its parameters were located by the same kind
of intervention as the EQ, delay and (now) here:

- Driving **LFO SPEED** moved exactly one cell, **C-RAM 0x00** — from 114 to 494 — matching the
  live phase-accumulator ramp the earlier work had already measured. That cell is the LFO's
  per-frame phase increment; the rate is `increment × 44100 / 2²³`, so 114 ≈ **0.6 Hz** at rest.
- Driving the panel **DEPTH** moved **C-RAM 0x09/0x0A** (0.303 → 0.505), so on this instrument
  "depth" is the **wet amount**, not the modulation depth.
- The modulation sweep amplitude is a **fixed** cell (0x02 = 240 samples ≈ 5.4 ms) that no knob
  moves — matching the earlier finding that the modulation value is constant.

The emulator runs a per-channel delay line read at two quadrature taps and crossfades the two wet
voices with the dry by the decoded wet gain. The check is on the **modulation**: with a single
sustained note, the chorus amplitude-modulates the note's harmonics at **0.62 Hz** — the decoded
LFO rate — nearly 19× more than the dry note does, and **driving LFO SPEED moves that modulation to
1.40 Hz**, so the rate follows the panel knob (and cell 0x00) exactly. The instrument voice's own
tremolo sits higher (~2.6 Hz) and is present in the dry too, so it is excluded from the test.

Still open: the chorus's own base pre-delay (a fixed value is used), the flanger variant (a
feedback all-pass chain, with its LFO phase in a different cell), and the LFO waveform selector.
Reproducibility: `dsp/tools/chorus_ab.lua` + `chorus_ab.py`.

That makes three effects reconstructed from the decode and validated in the emulator — a
parametric EQ, a single delay, and a chorus — each pinned by driving one panel control and watching
which decoded cell moves.

---

## 15. The flanger is now audible too (2026-09-11)

The fourth effect, and a close relative of the chorus: a **flanger is an LFO-swept delay with
feedback**. The feedback (the panel's RESONANCE) is what turns the moving comb into the deep,
resonant flange sweep. It is the fourth entry on the DSP EFFECT page, and — as the chorus work had
warned — it keeps its parameters in **different** cells from the chorus, so it was probed on its own:

- Driving **LFO SPEED** moved **C-RAM cell 0x05** (from 38 to 418) — the LFO phase increment. At
  rest that is a slow **0.2 Hz** sweep (the chorus's rate lived in a different cell and ran faster).
- Driving **RESONANCE** moved **C-RAM cell 0x00** (0.594 → 0.792). Read at the operand scale that is
  a feedback of about **0.3** — exactly the documented flanger feedback.
- Driving **DEPTH** moved **C-RAM cell 0x08**, which scales the sweep amount.

The emulator runs a single swept delay tap fed back into its own line (feedback = the decoded
resonance) and mixes it 50/50 with the dry. Because the rest sweep (0.2 Hz) is too slow to see
inside one held note, the check drives LFO SPEED up: the flanger then modulates the note at
**0.77 Hz** — the rate its cell now decodes to — nearly **45× more than the dry note**, confirming
the LFO, its rate cell, and the feedback path all work together.

Still open: the flanger's MANUAL (centre-delay) and PHASE (stereo L/R offset) controls, and the
waveform selector; and the chip's faithful structure is a swept all-pass chain, where the emulator
uses a feedback delay that produces the same swept resonant notches. Reproducibility: the chorus
harness reused with `TYPEIDX=3` (`chorus_ab.lua` + `chorus_ab.py`).

Four effects are now reconstructed from the decode and validated in the emulator: a parametric EQ,
a single delay, a chorus, and a flanger.

---

## 16. The phaser is now audible too (2026-09-11)

The fifth effect. A **phaser is a cascade of all-pass filters whose break frequency is swept by an
LFO**, with feedback — the swept phase shift, mixed with the dry, creates notches that glide through
the spectrum. It is the fifth entry on the DSP EFFECT page, and — as with every modulation effect so
far — it keeps its parameters in its own cells, so it was probed separately:

- Driving **LFO SPEED** moved **C-RAM cell 0x00** (76 → 456) — the phase increment, ≈ **0.4 Hz** at
  rest.
- Driving **MANUAL** moved **C-RAM cell 0x06** — the all-pass **centre coefficient** (where the
  notches sit). There is a single such cell, so the stages share one coefficient.
- Driving **DEPTH** moved **C-RAM cell 0x05** — how far that coefficient is swept.
- Driving **RESONANCE** moved **C-RAM cell 0x02** — the feedback (≈ 0.3), which deepens the notches.

The emulator runs six first-order all-pass stages sharing one coefficient `a = MANUAL + DEPTH·sin(LFO)`,
feeds the cascade back into itself by the resonance amount, and mixes 50/50 with the dry. As with the
flanger, the rest sweep (0.4 Hz) is slow, so the check drives LFO SPEED: the phaser then modulates the
held note at **0.77 Hz** — the rate its cell decodes to — over **55× more than the dry note**.

Still open: the exact number and order of all-pass stages (the emulator uses six first-order stages —
this sets the notch pattern, not the sweep rate the A/B measures), the PHASE (stereo L/R offset) and
waveform controls. Reproducibility: the chorus harness reused with `TYPEIDX=4`.

Five effects are now reconstructed from the decode and validated in the emulator: a parametric EQ, a
single delay, a chorus, a flanger, and a phaser — every one pinned by driving a single panel control
and watching which decoded cell moves.

---

## 17. Ensemble and vibrato (2026-09-11)

Two more members of the chorus family, both LFO-swept delays, done together because they reuse the
same machinery:

**Ensemble** (the sixth entry) is a **multi-voice chorus**. Driving its DEPTH knob moved *six*
small-integer cells at once — three per channel (0x02/0x04/0x06 and 0x09/0x0B/0x0D), the delay times
of three detuned voices whose spread widens with depth. The emulator reads one delay line per channel
at those three taps, sweeps each by the LFO at a staggered phase, and sums them for the characteristic
ensemble shimmer. Its LFO rate lives in cell 0x00 (≈ 0.4 Hz); with the rate driven up the ensemble
modulates a held note at 0.77 Hz, **101× more than the dry note**.

**Vibrato** (the seventeenth entry) is **pitch modulation** — a single swept tap, mostly wet, so the
ear hears the pitch wobble rather than a chorus's dry-vs-wet beating. Its rate cell (0x02) sits at
about **4 Hz** — noticeably faster than the chorus or flanger, as a vibrato should be — and its depth
is cell 0x05. The check confirms it modulates the note squarely at **4.0 Hz**, **289× more than the
dry note**, with nothing added at the instrument voice's own ~2.6 Hz tremolo.

Seven effects are now reconstructed from the decode and validated in the emulator: EQ, single delay,
chorus, flanger, phaser, ensemble, and vibrato.

---

## 18. The S.DELAY+X combination effects (2026-09-11)

Several panel presets are *combinations* — a single delay chained with a second effect. Because the
building blocks (delay, chorus, flanger, phaser, a second delay) are already reconstructed and
validated, a combination is those two blocks run in series. The catch is that each combo packs both
effects' parameters into **its own** C-RAM layout, different from the standalone versions, so each
was pinned on its own by driving one control and watching which cell moved:

| Combination | delay feedback | second-stage rate | validated |
|---|---|---|---|
| S.Delay + Chorus  | cell 0x02 | chorus 0x00 (0.6 Hz) | echo 299 ms **and** chorus 0.62 Hz |
| S.Delay + Flanger | cell 0x04 | flanger 0x00 (0.2 Hz) | modulation 0.77 Hz (driven) |
| S.Delay + Vibrato | cell 0x04 | vibrato 0x00 (0.6 Hz) | modulation 0.62 Hz |
| S.Delay + Phaser  | cell 0x00 | phaser 0x03 (0.4 Hz) | modulation 0.77 Hz (driven) |
| S.Delay + S.Delay | 0x00 / 0x05 | (two delays) | echo 178 ms |
| PEQ + S.Delay | 0x06 | emphasis band (freq 0x03, gain 0x01) | +16.7 dB at 3.2 kHz **and** echo 299 ms |

Each is implemented as the shared feedback delay followed by the second block run on the delayed
signal (reusing that block's own delay lines — only one effect is ever selected). For S.Delay+Chorus
both stages were confirmed at once — a **299 ms echo *and* a 0.62 Hz chorus sweep** in the same
output — proving the chaining works end to end; the others were confirmed by the stage that
distinguishes them (the second effect's modulation rate, or the second delay's echo). Where a combo's
layout does not separately expose a second-stage feedback or sweep, a fixed value is used; the
decoded, validated quantity in each case is the modulation rate (or the echo time).

PEQ+S.Delay adds the emphasis band of §1–3: its parameters reuse the **standalone EQ's exact cell
layout** (frequency in cell 0x03, gain in cell 0x01, the same −2.0 structural constant in 0x05), so
it is the EQ biquad chained into the delay — and both stages were confirmed at once: a **+16.7 dB
emphasis at 3.2 kHz** and a **299 ms echo** in the same output.

That brings the count to thirteen effects reconstructed from the decode and validated in the
emulator: the seven standalone effects above plus the six delay combinations. Still to come are the
effects that need a block not yet built — the enhancer and auto-wah (whose parameters do not sit in
the C-RAM coefficient bank) and the rotary speaker (a full dual-rotor Leslie).

---

## 19. The reverb — audible from the decoded coefficients (2026-09-12)

An earlier version of this page described the reverb as "walled," alongside distortion. That was an
overstatement and has been corrected: **the reverb needs no undumped data.** Its entire program (the
one reverb image, shared by all twelve reverb presets) is decoded to the bit, with every C-RAM
coefficient dumped and role-assigned — input scaling (0x90–0x92), three damping filters, the
decay / REVERB-TIME coefficient (0x97 = 0.4), the two diffuser ladders of five and four stages
(0x98–0x9C, 0xA1–0xA4), and the stereo output-tail mix (0xA9–0xB0). The external delay pipeline is
decoded too, and the reverb's linear feedback **measurably decays in the emulator** when its state
cells are impulse-seeded. The only genuinely missing data near here is the acoustic-modeling chip's
undumped wave ROMs (a separate chip). Distortion's clipping curve was once grouped in as "undumped"
too — that is also wrong and has since been retracted (see [§20](#20-distortion-is-not-undumped-either-2026-09-12)):
its waveshaper reads a table from C-RAM, and C-RAM is populated entirely from dumped ROM.

What remains is a **decode refinement, not missing data**: the exact micro-topology is narrowed to
a comb family (a pipe-comb or series-comb cascade; first-order all-pass, the parallel comb bank,
Moorer and the lattice are all ruled out), and the mapping from the measured decay ratios to the
ladder gains still needs the delay-line lengths — the same kind of intervention-driven decode that
pinned the other effects.

To prove the point, the emulator now carries an audible reverb (default off) reconstructed from
those decoded coefficients — a comb-plus-all-pass network whose diffusion, damping and decay-time
control come from the decoded cells. With it on, a plucked note leaves a decaying reverberant tail
**six times** louder than the dry note's own release, absent with it off. It is labelled a preview:
the diffusion and decay-control are decoded, but the exact topology and absolute reverb time await
the decode above.

---

## 20. Distortion is not "undumped" either (2026-09-12)

For a long time this page grouped distortion with the genuine data walls: "the clipping curve is a
ROM table that has not been dumped." That is **wrong**, and it is now retracted.

The nonlinearity is a **class-6 table lookup** — the same idiom the chip uses for an LFO waveform
and a ring-mod carrier. Two facts put its data in dumped memory:

- The class-6 lookup reads its table **from C-RAM** (the index sits in a temp register; the
  `C63` + class-6 pair is measured as one idiom across the corpus). C-RAM is populated **entirely
  from dumped ROM** — the per-preset parameter streams plus a resident table written once at boot
  from a literal blob at Sub CPU ROM `0x01E6BE`.
- This is **proven for the same idiom's LFO-waveform role**: that table is a 24-entry sine the host
  uploads, and decoding the 24 packets matches `0.95·2²³·sin(2πk/24 + 0.1)` to within one LSB.
  There is no internal silicon lookup ROM on this path.

A runtime C-RAM capture that reads zeros where the table should be is a **capture artifact** — it
replays the parameter streams from a zeroed C-RAM and never replays the boot blob — not missing
data. (The earlier "polynomial waveshaper" reading of OVERDRIVE's post-filter was a separate error,
already retracted in §13: that stage is the tone biquad.)

What is still open is a **decode refinement, not a data wall**: exactly which C-RAM cells hold the
waveshaper table (the selector is `0x28`) and the index arithmetic, which the chip's own class-6
probe is built to pin.

To make the point audible, the emulator now carries a default-off DISTORTION preview (selector 15).
It reads the DISTORTION program's structure from the decode — an AGC (envelope-normalising) stage,
a waveshaper, a DRIVE pre-gain from C-RAM cell `0x00` and an output VOLUME from cell `0x02` — and
applies it to the mix. The **DRIVE and VOLUME gains are decoded from C-RAM**; the clip transfer
curve is a **labelled stand-in** (a tanh soft-clip) pending the table-cell decode above. Fed a pure
tone (the diagnostic sine render), the effect off is clean (total harmonic distortion 0.01 %), and
on it generates the **odd-harmonic series of a symmetric waveshaper** — THD 11 %, about 1360× the
dry tone, third harmonic 8 %, fifth 6 %, with the even harmonics absent. Reproducibility:
`dsp/tools/distortion_ab.lua` + `distortion_ab.py`.

---

## 21. The rest of the effect catalogue, reconstructed (2026-09-12)

With EQ, the delays, the modulation family, reverb and distortion audible, the remaining programs
were reconstructed in one pass — **enhancer, exciter, auto-wah, auto-pan, ring modulator, multi-tap
delay, compressor, gated reverb, mix-up, rotary speaker**, and the **PEQ + X** / **auto-wah + delay**
combinations. The disassembly of each program was decoded for its C-RAM cell usage and topology,
the textbook DSP block was rebuilt from those, and each was added as a default-off option on the
same `DSPHLE` selector (now selectors `0x10`–`0x22`).

These are **honestly graded a notch below** the first effects. The first fifteen were each pinned by
*intervention* — drive one panel control, watch which C-RAM cell moves. For this batch only a few
numbers are that firmly pinned (the multi-tap delay times 136/272/408/544 ms and the mix-up LFO
rates 3.0/5.2/7.4 Hz are host-named; the auto-pan ~1.2 Hz and ring-mod ~1 kHz oscillator rates are
measured); most panel→cell *role* assignments are position-decoded from the program order, not yet
A/B-confirmed. So every one ships as a labelled **preview**.

Each was checked in the emulator against a dry control (`dsp/tools/fx_ab.lua` + `fx_features.py`):

- **Cleanly demonstrated:** ring modulator (spectral centre moves from the 262 Hz note to the
  ~1 kHz carrier, fully inharmonic); auto-pan (L and R amplitudes modulate in antiphase); mix-up
  (three-LFO modulation, ×8 envelope depth, chorus detuning); rotary speaker (a ~7 Hz tremolo warble
  with stereo motion and Doppler pitch-smear); exciter and enhancer (added high-band energy and
  brightness on a harmonically-rich source); auto-wah (envelope-swept resonant filtering). The
  combos chain correctly too — PEQ + chorus (emphasis + 3 Hz modulation), PEQ + distortion + delay
  (added odd harmonics and an echo tail), PEQ + compressor (emphasis + sustain lift).
- **Reconstructed and audible, signature gentle on a pure tone:** multi-tap delay (built on the
  *measured* tap times — the firmest data here), compressor (the decaying tail is lifted ~1.7×), and
  gated reverb (the tank runs and the gate chops the tail). A percussive source would show their
  echoes/gate more plainly than the sustained test tone does.

The rotary speaker carries one honest gap: its rotor **rotation rate is not in the program** (the
firmware supplies it from outside the decoded microcode), so the preview uses canonical Leslie
speeds — the Doppler delay lengths it sweeps, however, are decoded. None of this batch needs any
undumped data; what is soft is the parameter *mapping*, recoverable by the same per-control
intervention that pinned the first fifteen.

---

## 22. The HLE as an oracle for the LLE (2026-09-12)

The HLE of §9–§21 exists to make the effects audible *now*; the goal remains a faithful
low-level emulation of the chip, and the **bytecode, not the HLE, is the source of truth** — the
HLE can be wrong (the bytecode already corrected it once, adding the single delay's in-loop HIGH
DAMP filter that the first reconstruction had omitted). This section is the first round of using
the two against each other in the other direction: the HLE's known signal flow as an **oracle** for
what the LLE's per-word columns *must* show.

**The instrument.** A default-off diagnostic (`UPD6383_DLYSEED2`) writes a known impulse
(0x4000 → 0x400000 on the bus, 0.5 FS) into the external delay DRAM at the tap address the chip
itself has just computed, so the genuine read → per-line latch → publish → ALU pipeline carries a
value whose fate can be followed word by word in a one-frame trace. `dsp/tools/dlyseed_run.sh`
captures one program (the trace frame is derived from the harness's own note-on schedule) and
`dlyseed_confront.py` asks the questions: does the impulse reach the operand latch, is it
multiplied by the measured multiplier rule, does the accumulator behave, and where does it die.

**What generalized (MEASURED).** The biquad's datapath (§10) is the whole chip's: the multiplier
`P[N] = coef[N−1] × L[N] >> 6` is bit-exact on the **single delay (16/16)**, the **chorus (5/5)**
and the **flanger (11/11)**, and the one-slot accumulator classifies every row of all three
programs once two device forms are named (a "bus-add" of the operand at datum scale, and
"P ← bus"). The chorus's LFO phase cell advances by exactly **114 per frame** — the HLE's
increment for its 0.6 Hz rate, with the increment itself visible on the bus at the phase word — and
the HLE's cell→role map is confirmed **at word level**: cell `0x00` = 114 (rate) at the phase
word, `0x02`/`0x04` = +240 and `0x0D`/`0x0F` = −240 (sweep depth in samples) at the four sweep
words, `0x09`/`0x0A` = the wet gain after the waveform lookup, `0x08` = 24 (the lookup-index
scale); the flanger's rate cell `0x05` = 38 likewise. Two HLE refinements surfaced from the
bytecode while doing it (⚠ **the first is corrected below**): the chorus's second sweep pair runs
with **negated depth** (its depth coefficients
are negated), and the flanger runs **two** phase accumulators — both are candidates, not yet
validated changes.

**Where the LLE breaks, now localized to single words.** In both modulation programs the seeded
tap datum reaches the bus at the delay-READ word and **dies there**: the word after every such READ
carries an operand code (`SRC 0x13`) the device decodes as the table-lookup source, which reads
zero. An arm that stored the datum under the pointer instead was **run and refuted** — the datum
then persisted, but into cells the programs use as state (the chorus folded it into its tap
offset). The flanger showed the real carrier: its delay-WRITE word captures the datum into
**tempA** (the single delay's proven route), and a *speculative* blanket rule in the device — five
action codes all overwrite tempA — let the tap-offset word clobber it four words before `mac ta`
reads it. Excusing that one code (`UPD6383_NOTA0C`) was **predicted to and did** deliver the tap
to `mac ta` on both channels. The tap now reaches its consumer's operand latch; folding it into the
feedback sum and the wet (the class-2 mixing words, the same open family the delay left) is the
next decode.

**The coefficient scale, pinned by two programs (MEASURED).** The LLE had shipped with a
multiply-to-datum shift of 22 (unity = `0x400000`), chosen by fitting the device's own columns —
a fit that is scale-free and so never decided the absolute scale. Reading the single delay's
recurrence off its seeded trace at the fixed point (`dsp/tools/dlyseed_recurrence.py`) gives the
damping cascade's DC gain in closed form: **1.45× (amplifying) at shift 22, 0.18× (damping) at
shift 23**, and the feedback cell reads −0.58 vs **−0.29** — the "0.3 feedback" the program's own
header carries. The parametric EQ decides it independently: its `−a2` cell is `0x81227B`, which is
a stable `a2 = 0.991` at Q23 and an impossible `1.98` at Q22 — and the LLE's biquad state block
**rails at shift 22 (19 of 48 cell sightings at full scale) and is finite at shift 23 (0 of 48)**,
with the multiplier still bit-exact (16/16 at `>> 7`). So on those words the coefficient field
is **Q0.23, unity `0x7FFFFF`**. The refinement that the register already held, and that this
measurement now sharpens, and the EQ settles what any account must produce. An RBJ peaking
biquad has `b1 == a1` exactly, at every gain and frequency; reading each band's five ROM cells at
one scale gives ratios `b0/1 = 0.2500`, `b1/a1 = 0.5000`, `b2/a2 = 0.2500` — **identical in all
five bands, spread 0.00000** — and scaling `b0`, `b2` by 4 and `b1` by 2 makes the numerator
exactly `[1, a1, a2]`, so `|H|` is **flat to 0.00 dB** where every rival scaling leaves 46–109 dB
of ripple. Three distinct scales among five coefficients, from the ROM alone. That refutes both
candidate selectors outright: word bit 12 cannot produce them (`b0` is the only bit-clear word
yet shares `b2`'s scale), and neither can the ACT code (`b2` and `a2` share ACT 0x15 with
different scales) — both were also built as device arms and both railed. What mechanism *does*
carry the three scales is open; a first answer read off the operand cells was **retracted** the
same day, because the traces available were either saturated or seeded with a 1:2:3:4 ramp into
the very cells being compared. For the HLE this is per cell: the
chorus's wet gain (a bit-clear word) had been read as `q22 × cs` — right for the program's
integer cells (LFO increment 114, 240-sample sweep), 2× hot for that gain (0.30 where the chip's
is 0.15) — corrected in the HLE and on its [impl page]({{ site.baseurl }}/effects-dsp/impl/);
the delay's feedback sits on a bit-SET word (Q1.22, −0.58) where the HLE reads −0.29, so it is
queued for the same per-word audit along with the distortion's DRIVE/VOLUME.

**The audio gate — located at one word, and opened.** The project's oldest open item is that
external audio reaches the chip but never the effect body, so every program computes on stale
state. The instrument that settled it is a **frame-pair diff**: capture frame *F* and frame *F+1*
with an otherwise identical command line and compare every D-RAM cell and every executed row. A
body fed live audio cannot produce two identical frames, so this replaces a judgement call with a
two-sided test. On the shipped emulation it reports: the audio *does* arrive (the deposit cells
move between frames), the shared kernel *is* live — and from one specific instruction onward,
including the entire effect body, the two frames are **bit-identical**.

The break is a single word of the shared kernel. It carries a `lo12` bit that the emulation reads
as *"addressing only, no ALU effect"*, so the branch returns before the word's **capture action**
runs; its target register stays frozen at a boot-time value, the next word consumes that frozen
value, and what it computes becomes the body's input for every frame thereafter. Corpus-wide only
95 of 3057 words carry that bit and just **two** carry a capture action — one of them this
kernel word, on every effect's audio path. Performing the capture (a default-off diagnostic) makes
the body run on live audio for the first time: body cells moving 0 → 3, executed rows 0 → 15 of
105, and the input history shifting along like the delay line it is.

**A second decode followed immediately: what the biquad's post-sum word does.** The parametric EQ's
listing — the project's reference program — still carried one step marked *OPERATION UNKNOWN*,
sitting between the five-term sum and the makeup multiply. The corpus says what it is: that
encoding occurs at **35 sites with identical neighbours at every one**, only in the 17 programs
carrying a biquad, ten times in the EQ = once per band per channel, and its own fields take the
**accumulator** as operand while writing no memory. With the body finally running, a one-bit
post-sum scale at that word is the unique small integer that un-saturates the filter: the
no-op leaves 33 rows pinned at full scale with only the first band alive, and one bit of scaling
leaves **nothing** at the rail with all five bands propagating. So the word is a **post-sum
accumulator scale**, not a no-op — invisible until the body was live, because the evidence for
"no-op" had been a *ratio*, which is blind to a uniform gain. The exact amount is not yet pinned.

**An HLE refinement the bytecode points at, recorded but not yet applied.** With the effect body
running, the chorus's tap-sweep word can be read directly, and it does not do what the HLE does.
Its operand is the **LFO phase itself** — the same cell the phase accumulator steps by 114 every
frame — and its product is `depth × phase`, which checks to the last bit (`240 × 2 800 600 >> 7 =
5 251 125`) and sweeps `0…240` samples as the phase ramps through its modulus. That is a **ramp**,
where the HLE reconstruction sweeps its two delay taps with the sine and cosine of the phase. The
program does contain the waveform lookups — two of them, and the 24-entry sine they read is
present and verified — but their result is consumed by a *different* word four slots later, not by
the sweep. So the open question is which stage the table shapes, and until that is answered the HLE
keeps its sine sweep: changing it on half the picture would trade a validated behaviour for an
unvalidated one. Recorded here because the bytecode is the source of truth and this is what it
says; the HLE page keeps the reconstruction exactly as it stands.

**Why a fix that works on one program is not a decode, and what a proper test looks like.** The
work above left one configuration in which the chorus's LFO phase came out right *and* its body
stayed live, and it was tempting to call that the answer. Run on the **parametric EQ** — the
reference program, the one decoded to the bit — the same configuration starves the filter: the
band state stops moving almost entirely. So the two programs want opposite things at the same
setting, which is exactly what a correct decode must not do.

That turned into a standing instrument (`dsp/tools/pair_gate.sh`): a candidate rule is run against
**both** programs at one setting, and is admissible only if the chorus's phase increment is right,
the chorus's body is live, **and** the EQ's body is live. Four structurally unrelated
interventions have now been through it — flushing the product register at the block call, driving
it per word, clearing the coefficient-cursor seed, and the unmodified baseline — and they lie on a
single trade curve: every rule that makes the phase right does so by removing product from the EQ,
and the more it removes the more completely the EQ dies. A trade is not a decode. It also shows
that the phase landmark **on its own is nearly vacuous**: the right value is what the machine
reports whenever that register happens to be empty, including when it has been emptied by
something that destroys everything else.

Reading the EQ's body entry word by word says why, and it is the most useful single result of the
round. Two words after the pickup arrives, the live input is sitting in the accumulator; two words
later still, a word that performs **no multiply** loads the accumulator from the product register
anyway — and so overwrites the input with whatever the previous block happened to leave. Without
any intervention that leftover is the *kernel's* product, which is itself derived from audio, so
the EQ's bands keep moving and the filter looks alive. **It was never being fed its own input; it
was being fed the kernel's residue.** Clear the residue by any means and the bands get a clean
zero instead. The chip's own rule is therefore expected to be of the form the device already names
in its source — *a load that brought no fresh product is an erasure, not an operation* — and that
is what the next round tests, on both programs at once.

**And then it passed — the first configuration to satisfy every criterion at once.** The criterion
the HLE supplies turned out to be the one that mattered: *the equaliser's input is one copy of the
pickup.* Measured that way, the configuration the liveness test had marked worst was the only one
delivering a correct input, and the liveness test had been rewarding contamination all along. With
that settled, the remaining fault was a single cell: the entry stored the input to a cell nothing
reads, while the first filter band read a cell nothing writes. The two are adjacent, and the word
that stores is the same word whose pointer steps from one to the other — its store was aimed at the
pointer before the step rather than after it.

Aiming it after the step does deliver: **each of the five filter bands then receives exactly one
copy of the input** — five cells spaced four apart, precisely the five-band, four-cell-per-band
structure the bytecode was already known to have, with the filtered histories moving beside them,
and the equaliser's body moves 94 of its 105 executed rows where it had moved 9.

**And it breaks the chorus, which took a further correction to see.** The test being used for the
modulation was the phase cell's change *within a single frame*, and the two instructions involved
load the increment and then store it — so that number reads correctly even when the phase is reset
to zero on every frame and the oscillator never advances at all. The chip's own diagnostic had been
reporting the right quantity in every capture taken: the phase value on eight consecutive frames.
Read that way, the redirected store leaves the phase at zero on all eight. The modulation is dead.

So there is still no configuration that satisfies everything, and the change that fixes the
equaliser's delivery costs the chorus its oscillator. What the correction leaves is stronger than
what it removes, though: measured across eight frames, the flush alone gives the chorus a perfectly
constant step equal to its own increment — a correct free-running ramp — where the unmodified
device wanders. That is now two unrelated tests, on two different programs, agreeing on the same
change. Everything stays off by default.

The lesson is recorded against the result it cost: a test must be able to fail in the way the thing
actually fails. A four-part test was built precisely because single measures had been misleading
this work, and then the most important of its parts was a quantity that stays constant under the
very failure it existed to detect.

**One change is now part of the emulation rather than an experiment.** Running the candidate
against ten programs — the modulation family, both reverbs, both delay shapes and the equaliser —
settled which half of the pair was right. The redirected store fails everywhere: every program with
a modulation oscillator loses it, and the equaliser gains nine saturated cells. The other half, the
rule that the multiplier's pending result does not survive a call into an effect body, passes with
no regression on any of the ten, and **five of them gain a correct free-running oscillator where
the unmodified device had none** — the phase advances by exactly its own increment, frame after
frame, in the chorus, the modulated chorus, the flanger, the phaser and the ensemble.

That is four independent lines of evidence for a single change, on ten programs rather than two, so
it is now the default behaviour, with a switch to restore the old one for comparison. It is the
first body-side finding in this investigation to earn that.

Two caveats travel with it and are worth stating. The equaliser's arithmetic drops sharply under
the change, and that is understood: what the unmodified device was busily filtering was the
preceding block's leftover product, and removing the leftover leaves the filter correctly fed at a
location nothing reads — the open problem described above. The enhancer's arithmetic also drops, by
a factor of four, and **that is not understood**. It has no oscillator and nothing saturates. It is
the standing argument against the change and the first thing to examine.

**And then the gap closed.** With the residue gone, the remaining fault was a single cell: the
entry stored the input where nothing reads it, and the first filter band read a cell nothing writes.
Comparing the programs that work against the two that did not narrowed the cause to one field. A
program whose body reads live data fills its state cells with a different store instruction
entirely; the equaliser's only store at its entry is the one whose target was in question, and the
enhancer has none at all. And the equaliser's entry store and the chorus's oscillator store are the
same instruction but for the sign of their pointer step — one moves forward sixty-four cells, the
other back twelve. That is a measured constraint rather than a guess: **no single store target can
serve both**, which is why redirecting all of them fixes one program and breaks every oscillator.

Making the target depend on that sign — forward steps store after the move, backward steps before —
passes everything. The chorus keeps its free-running oscillator, and the equaliser's five bands each
receive exactly one copy of their own input. Across the same ten programs there are no regressions
at all: every oscillator still runs at its own rate, one program even loses a saturated cell, and
the equaliser goes from two moving cells to thirty, from nine multiplications to ninety. Seven of
the ten are untouched, which is what should happen — their entry stores step backward or do not
store.

So the input path through an effect body is now closed on the reference program: the kernel
delivers, the entry assembles one clean copy, the store lands where the first band reads, and the
bands filter their own signal. Both changes are on by default with switches to restore the old
behaviour, each promoted only after ten programs agreed.

Three things remain open and are worth naming. The enhancer is unchanged, because it has no store
of that kind at its entry at all, so how its body is meant to be fed is still unknown. The
sign rule is a hypothesis that survived rather than one that was derived — the sign may be standing
in for something the trace does not record. And the output stage, which turns a finished body result
into sound, is a separate problem that none of this touches.

**A correction to one of those refinements, from the trace rather than the coefficients.** The
"right channel sweeps in antiphase" reading was taken from the sign of the depth coefficients: two
of the four sweep instructions carry +240 samples and two carry −240. Checking which part of the
frame each one runs in shows the attribution was wrong. **All four are in the same processing
unit's body.** Whatever the sign distinguishes, it is not the two units, so it cannot be the two
output channels — it is a difference between the two voices of one channel, or between a read tap
and a write tap, and the trace as it stands does not separate those. The measured fact keeps its
value; the label it was given does not, and the reconstruction is unchanged either way. This is the
third time on this device that a plausible "left and right" reading has not survived being checked
against which unit the instruction actually belongs to.

**Retractions, kept in the record.** The device's delay-age census had been read as "the
single delay's line depth matches the descriptor (~350–400 ms)". It does not measure that: the
census pools every program since boot and its addresses carry a stale speculative modulation
offset, so its maximum moved between runs with identical hit counts. The LLE's realized line depth
is **unmeasured**. Details, recipes and graded evidence: `dsp/analysis/N-DLYSEED2-SINGLE-DELAY-
CONFRONT-2026-09-12.md` and `N-DLYSEED2-CHORUS-CONFRONT-2026-09-12.md`.

---

## Related pages

- [DSP Effect Data Zone (Sub-CPU ROM)]({{ site.baseurl }}/dsp-effect-data-zone/) — the
  block-by-block map of the 39,372-byte zone this page's conclusions are drawn from:
  the four pointer arrays, both stream grammars, and a per-effect address table.
- [Effects-DSP Program Flowcharts]({{ site.baseurl }}/effects-dsp/flowcharts/) — one
  structural signal-flow diagram per microprogram (the shared kernel + 38 effect bodies),
  synced from the disassembly tree and rendered as Mermaid.
- [Effect HLE + bytecode]({{ site.baseurl }}/effects-dsp/impl/) — one page per effect
  pairing the disassembled **microprogram** with the MAME **HLE reconstruction** that renders
  it (the educational bridge described in [§21](#21-the-rest-of-the-effect-catalogue-reconstructed-2026-09-12)
  — reading the two together is how the bytecode is understood, toward a faithful LLE).
- [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) — the Sub CPU audio firmware and
  the parallel host interface that reaches this chip.
- [DSP Bytecode Interpreter]({{ site.baseurl }}/dsp-bytecode-interpreter/) — the Sub
  CPU-side interpreter that uploads microprograms and streams coefficients (partly
  superseded here regarding the DSP chip itself).
- [Tone Generator]({{ site.baseurl }}/tone-generator/) — IC303, the wavetable voice engine
  upstream of the effects.
