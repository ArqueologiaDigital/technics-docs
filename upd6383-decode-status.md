---
layout: page
title: "Decoding the uPD6383GF: state of play and the route to 100%"
permalink: /upd6383-decode-status/
---

# Decoding the µPD6383GF — state of play, and the route to 100 %

This is a standalone summary of the effects-DSP reverse-engineering effort: what the chip is, how
much of its instruction set is decoded, what has been tried and failed, and — in more detail than
the rest — **what to do next, why each experiment should work, and what it costs**.

> **Status.** Pooled decode coverage is **80.8 %** — 5876 of 7273 distinct microcode words across
> the SX-KN5000 and the SX-WSA1R, leaving **1397 undecoded**. The word format, the datapath and
> two whole algorithms are decoded; most individual instruction codes are not.
>
> **The headline for planning: no hardware is on the critical path to 95 %.** Closing the
> questions already answerable from the corpus and the emulator would take coverage to **95.2 %**
> without touching an instrument. The hardware routes matter for the last few points, and one of
> them got considerably more attractive today.

Confidence is labelled **MEASURED / PROVEN BY CONSTRUCTION**, **INFERRED**, or **OPEN**, matching
the research notes. Where a claim needs real hardware, it says so.

---

## 1. The chip, and why this is hard

The **NEC µPD6383GF** is the effects DSP of the Technics SX-KN5000 (IC311) and the SX-WSA1R
(three of them: IC5, IC6, IC30). It is a 100-pin QFP running at 25 MHz, processing a 36-bit
microword at a 44.1 kHz frame rate — 567 clocks per frame — with its program restarted by the
sample clock rather than by a software loop.

**There is no datasheet with an instruction set, and that is now a measured fact rather than a
complaint.** NEC's 638x line is a Japanese consumer-audio family absent from every reachable
NEC publication: 0 hits for `638x` across bitsavers' complete NEC data-book holdings, including
the 1989 and 1992 DSP data books and the 1989 Product Selection Guide. The only vendor
documentation anyone has found is a **block diagram and pin table** in the Pioneer CDJ-500 service
manual, where the same part is IC302.

So every statement about this instruction set comes from one of: the ROM corpus, the Sub CPU code
that assembles the words, an exhaustive constraint search, or a live emulator trace.

⚠ **The project's own standing rule is that a wrong decode costs more than a missing one.** Six
readings have been retracted, two of them within hours of being committed. The
[instruction set reference](https://github.com/ArqueologiaDigital/kn5000-roms-disasm) opens with
its own list of corrections, and that list is part of the result.

---

## 2. Where we are

### The numbers, and which denominator

| corpus | words | undecoded | decoded |
|---|---|---|---|
| **pooled, de-duplicated** | **7273** | **1397** | **80.8 %** |
| SX-KN5000 | 3057 | 644 | 78.9 % |
| SX-WSA1R | 4216 | 753 | 82.1 % |

Pooled rates are quoted over **distinct** images. The WSA1R tree carries byte-identical duplicates
— and they are reverbs, better decoded than average — so counting them inflates every figure.

⚠ **Two counts exist and they are not the same.** The per-program flowcharts report *opaque*
instructions — words with **no name at all** — and that count is now **0** on all 38 KN5000
programs. It is much the weaker bar: a word can be named and still undecoded, and **612 of the
KN5000's 2974 words are exactly that**. Each flowchart now prints both, e.g. chorus is *"0 still
opaque, 18 of 70 not yet decoded"*. A zero in the first column is not a finished decode.

### What is actually decoded

- **The word format** — MEASURED. 36 bits in a 5-byte container, split `hi12 / class4 / addr8 /
  lo12`. `hi12` is a **horizontal microword, not an opcode**: its 54 observed values contain 77
  Hamming-distance-1 pairs against a null of 43.4 ± 4.3 (z = +7.9).
- **The datapath, bit-exactly** — MEASURED from live traces. The multiplier is
  `P[N] = (coef[N-1] × L[N]) >> 6` with the coefficient latched one word early; the accumulator is
  a **single adder with two selectors**, not a sequence; the store is `datum = acc >> 16`. Bit-exact
  on the parametric EQ (27/27 MACs), and the multiplier generalises to SINGLE DELAY 16/16,
  CHORUS 5/5, FLANGER 11/11.
- **Two algorithms end to end** — the parametric EQ and the reverb diffuser, reconstructed to
  **0.094 dB** worst case over 8 coefficient banks, 11 biquad sections and 4 programs.
- **All four memory spaces** — coefficient RAM (the whole 256-cell map), the state D-RAM (origin
  pinned, 85/85 streams), the external delay DRAM (`address = (descriptor[cursor] + G) mod 2^N`,
  PROVEN BY CONSTRUCTION, validated against a ROM shipping `15 435 = 350 × 44100/1000` exactly),
  and the internal register file.
- **Control flow** — PROVEN BY CONSTRUCTION. Hardware PC restart per frame, an 83-word resident
  kernel in two canned blobs, a two-level call stack, and **straight-line hand-unrolled bodies**:
  an exhaustive scan for a branch instruction is negative, and there is a positive reason for it.
- **The store gate**, settled 2026-09-14 after months as a two-way tie. See §3.

### And the [pinout]({{ site.baseurl }}/upd6383-datasheet/), as of today

The 100-pin package has never been documented in one place. It is now, read at 400 dpi off the
WSA1R schematic — which turned out to draw the chip more clearly than the CDJ-500 manual we
expected to need. Three results from it appear below.

---

## 3. What has moved the number, and what has not

**Methods that paid:**

| method | what it bought |
|---|---|
| Exhaustive static constraint search | The adder, the store timing, `ACTION 0x19`. A 19.7-million-point search; a 276 480-machine LFO search that left 0 survivors unconditionally |
| Pooling a second product (the WSA1R) | The minimal pairs the KN5000 alone does not contain |
| **The relocation test** | *A field that is an address shifts with a relocation; one that is data does not.* +11 words and **+143 words**, on two separate occasions |
| **The two-sided gate** (`pair_gate.sh`) | The project's strongest arbiter — four criteria that must pass at one setting. It broke the store-gate tie |
| Seeded LLE frame traces | Every bit-exact datapath result above |

**And the dead ends, recorded so nobody repeats them.** The register is 44 numbered entries long.
The three worth knowing:

- ⛔ **The KN1500 as a third corpus — tested to a negative.** It genuinely uses the chip (Felipe
  confirmed a D6383GF-3BA as its IC3), and extraction works: 37 streams, 2389 words. But **87 % of
  them already appear in the pooled corpus**, its bodies are not relocations (best cross-product
  match ≥ 0.90 for 1 of 31), and its one true twin is 111 of 116 words byte-identical with **zero
  single-field differences**. On the 175 genuinely novel words, every isolating axis returned
  **fewer new minimal pairs than chance**.
- ⛔ **The uPD6380 cross-decode** — refuted, 24-bit words against our 36-bit. Do not re-run.
- ⛔ **A criterion that could not fail.** A promotion passed "all four gate criteria" and was
  disqualified when the chorus LFO phase was read over *eight consecutive frames* instead of
  within one: the arm freezes every LFO at phase 0, and the within-frame delta reads a healthy
  114 even when the phase is reset to zero every frame. The rule earned: **a criterion must be
  able to fail in the way the thing fails.**

---

## 4. What is left

The 1397 undecoded words are blocked on **54 distinct open axes** — but not evenly, and not
deeply: **591 of them are blocked on exactly one axis.**

| if this question were answered… | words unlocked | coverage |
|---|---|---|
| `f31` 3/4/5/7 — the five unknown accumulator operations | 189 | 83.4 % |
| `ACT 0x0B` off class A | 159 | 83.0 % |
| `SRC 0x11` — the second accumulator `accb` | 139 | 82.7 % |
| addressing classes 0/1/4 | 99 | 82.2 % |
| class 6 + `SRC 0x13` — the table-lookup idiom | 90 | 82.0 % |
| `SRC 0x1C` + the store gate at `f31 1` | 89 | 82.0 % |

Closing them in the best order cascades, because most words are blocked on two axes and free up
only when both fall:

```
   1. f31 3..7                      +189  ->  83.4 %
   2. ACT 0x0B                      +163  ->  85.6 %
   3. SRC 0x11                      +149  ->  87.7 %
   4. addressing classes 0/1/4      +114  ->  89.2 %
   5. the bit-11 alternate encoding +169  ->  91.6 %
   6. SRC 0x1C + store gate f31 1    +93  ->  92.9 %
   7. class 6 + SRC 0x13             +90  ->  94.1 %
   8. ACT 0x08                      +108  ->  95.6 %
   9. ACT 0x01 + SRC 0x01            +77  ->  96.6 %
  10. ACT 0x1A / 0x1B / 0x0C         +62  ->  97.5 %
      ------------------------------------------------
      residue: 183 words, ~20 further small axes
```

⚠⚠ **Read this as reach, not as a schedule.** These counts come from the decoder's own model of
what blocks each word: how many words a decision would unlock, **not how hard the decision is**.
Several of these have resisted for months *with the blockage proved* rather than merely
unsolved — and that is the useful part:

- **`SRC 0x11` is a documented dependency cycle, not a capture problem.** Splitting `accb ← acc`
  from `accb ← P` needs a program whose `accb` input varies; every reachable program feeds it the
  same frame-invariant kernel constant, so `acc == P` is *structural*. **Do not run another
  capture campaign at it.**
- **`f31 3`'s carriers appear in no program any anchored criterion can see.** Single delay, the
  parametric EQ and room reverb 1 carry **zero** `f31 = 3` words, so every anchored criterion is
  blind to the axis by construction. It is separable and reproducible; it is unrankable.
- **The class-6 lookup is blocked on its index**, and the word that computes the index is itself a
  bit-11 word the device executes nothing for. Six index sources have been enumerated and refuted:
  **do not build a seventh.**
- **The bit-11 family turns on one question.** 169 undecoded words over nine shapes, two of which
  are 87.6 % of the family. **169 of 169 are in a characterised addressing mode** and 158 of 169
  carry an anchored accumulator function — the disassembler refuses them by an explicit policy
  guard, not because anything else about them is open. The single unknown is what the alternate
  `lo12` encoding means.

---

## 5. The routes, ranked cheapest and safest first

### R1 — More of what already works · free · **80.8 % → 95.2 %**

Everything in the cascade above is corpus work and emulator work. No hardware, no acquisitions,
no risk. **This is the recommendation**, and the ranking is not close: it is fourteen points, and
the two instruments that have delivered every recent promotion — the relocation test and the
two-sided gate — are already built and documented.

The best-posed single target is the **bit-11 alternate encoding**: nine shapes, two carrying most
of the family, everything else about those words already characterised, and a named first target
(`8801308BC`, 37 occurrences, a register-file access aimed at the very table its largest sibling's
idiom reads — which a relocation-style test can attack).

### R2 — A Pioneer CDJ-500 firmware dump · a cheap second-hand player · **+2.9 points, but only after R1**

The CDJ-500 uses the same chip as IC302, and unlike the KN1500 its DSP-shaped feature is genuinely
different: **Master Tempo**, key-lock pitch shifting. The KN5000 ships PITCH SHIFTER as a
byte-identical copy of NO OPERATION, so this is microcode neither existing corpus contains.

The project's strategic review names it as *the only route* to the six `SRC` hapaxes, the
kernel-only classes 9/C/D, and the bit-11 drought.

**But order matters, and the measurement is blunt about it:**

| | words unlocked |
|---|---|
| the CDJ-500 bundle **alone** | **+2** |
| everything internal (R1) | +1045 → 95.2 % |
| the CDJ-500 bundle **after** R1 | **+214** → **98.1 %** |

Its axes are entangled with the internal ones, so on its own it buys essentially nothing.
Afterwards it is worth three points. ⇒ **Order a player now, ignore it until R1 is done.** What is
needed is the **firmware dump, not the manual** — we have the manual.

### R3 — The debug port, extended to CPU 2 · the instrument, not a result

A [custom-ROM SysEx monitor]({{ site.baseurl }}/wsa1-emulation/#a-debug-port-into-the-machine)
already answers over MIDI on the WSA1R and can read CPU-1 memory back as exact integers. The next
commands wanted — `LOAD`, `POKE`, `RUN`, `DUMP` — are **not extensions of it**: the µPD6383s hang
off **CPU 2**'s ports, and between the processors is an octal-latch mailbox speaking CPU 2's
existing protocol. That is a second agent on the other processor, and it is the real cost.

⚠ Worth stating plainly, because it bounds every hardware plan: **the WSA1R never executes its own
effect bodies.** IC30's instruction RAM is written **once, at boot** — a 63-word resident kernel —
and only **45 of 918 distinct static corpus words are ever resident**. So on that machine there is
nothing to observe until you can upload microcode yourself.

### R4 — Readback: tap CN14 · ★ cheap, and better than it looked

See §6. Short version: **tap the connector, do not rebuild the board.**

### R5 — The chip's own emulator mode · highest information, highest risk

The µPD6383 has a debug facility. On the KN5000 it is disabled by the board: **`SETRDY` (pin 100)
open and `BR-RQ` strapped high ⇒ no PC trace without board modification.** A PC trace would be
worth more than any audio experiment — it is the difference between inferring what a word does and
watching the machine do it.

The cost is soldering on a rare instrument, and the prerequisite is knowing what the pins want,
which no datasheet tells us. Rank it last, and only after R1–R4 have been exhausted.

### R6 — What may be genuinely undecidable, and the doctrine for it

Some fields have a **measured proof of blindness** — not an absence of effort. `ACT 0x0D` has no
anchored pair anywhere in 91 programs and all three known-mathematics contexts measure blind; the
exact DRAM read latency inside its forced window is unobtainable from either board; `N` in
`mod 2^N` is unobservable from software because the firmware never uses more than 16 bits.

The existing doctrine is the right one and should not be softened: **name the equivalence class,
pick a member, mark the row ARBITRARY — not GUESSED — and make the choice a single toggle** a
future datasheet or corpus flips in one line. A field proved unobservable is a different kind of
result from a field nobody has got to.

---

## 6. Would building the digital-output board help?

**Short answer: the digital output is worth having, but do not manufacture the board. Tap the
connector it plugs into — and tap a different lane than you would expect.**

### What the board is

The **Technics SY-ES1 "Output Expansion Board"** (ORDER NO. EMID951602, © 1995), for the SX-WSA1
and SX-WSA1R. Its service manual is
[on archive.org](https://archive.org/details/Technics-SY-ES1/). It adds SUB OUT 2, SUB OUT 3, and:

> **DIGITAL AUDIO OUT (S/P DIF standard)** — The stereo signals form [*sic*] the main output are
> output as digital signals through one connector. Sampling frequency: 44.1 kHz · Number of
> quantizing bits: 20 bits linear · Channels: 2 channels (stereo) · Connector: RCA pin jack

Ten ICs: `TC9271F` (the IEC-958 transmitter), `D74HC04GS` (line driver), **4× PCM1702U** 20-bit
DACs and 4× `M5218AFP` op-amps for the two analogue sub-outs. The S/PDIF path is
`TC9271F → 74HC04 → 470 Ω → pulse transformer → RCA`. Coaxial, transformer-isolated, and
**nothing in it re-quantises or re-mixes** — it is a bit-exact tap of a serial audio lane.

### Why not to build it

**It has no ROM, no bus buffer and no address decoder.** Its two connectors are `CN1` ← main-board
`CN11` (power only: ±5 V, ±VCF, +VCM, ground) and `CN2` ← main-board **`CN14`**, which is a plain
serial audio bus. The board is **electrically incapable of being detected by the firmware**, which
also answers the question of whether it needs firmware support: it cannot, and it does not. (The
`"WSA1 EXTBD"` signature the firmware looks for at `0x00C00000` belongs to a bus-attached board —
the wave expansion, SY-EW1 — not to this one.)

So everything that makes the digital output valuable is **already present on CN14**, which is
fitted on a stock machine:

| CN14 | | | |
|---|---|---|---|
| 1 `MCK` | 2 `LRCK` | 3 `BCK` | 4 `LEL` |
| 5 `LER` | 6 `SDO2` ← `SUBOUT2` | 7 `SDO3` ← `SUBOUT3` | 8 `MOUT` ← `MAINOUT` |
| 9 `FS1` | 10 `FS2` | 11 `+5D` | 12-14 ground |

Three independent data lanes on one shared clock group. A four-wire tap — `MCK`, `BCK`, `LRCK` and
the lane you want — into any modern I²S receiver gets the same bits, avoids two long-discontinued
parts (`PCM1702U` is a favourite of counterfeiters, `TC9271F` is gone), and may give you **24 bits
where the board's S/PDIF is configured for 20**.

### ★ And tap `SUBOUT2` / `SUBOUT3`, not the main output

This is the part worth the schematic render. Reading the nets below IC30 — the **program** DSP:

```
   tone generator  SDO1, SDO2, SDO3  ->  IC30  DI1, DI2, DI3
   IC30  DO1 -> SUBOUT1   (to the machine's own SUB OUT 1 jacks)
         DO2 -> SUBOUT2   (470R, to CN14 pin 6 -- and nowhere else)
         DO3 -> SUBOUT3   (470R, to CN14 pin 7 -- and nowhere else)
```

**`SUBOUT2` and `SUBOUT3` are program-DSP outputs that a stock machine never listens to.**

Every probe design so far has had to reckon with the DSP's output arriving **already mixed with
the dry signal** — the wet/dry crossfade is a parameter *inside the microprogram*, so no wiring
downstream can separate them, and the best available workaround was `WET = 100 %` plus a
pass-through program as the dry null. These two lanes sidestep that entirely: they carry DSP
output with nothing summed into them.

That turns the readback problem from *"count steps in a staircase through a DAC, an analogue
path and an ADC of unknown gain"* into *"read a 24-bit integer per DSP frame"*. At 44.1 kHz one
frame in equals one sample out, so it is ~1 Mbit/s of exact integers.

⚠ **What is not established, and it is the obvious next check:** whether the shipped microprogram
ever writes anything to `DO2`/`DO3`. The hardware path exists and is idle; nobody has looked at
whether the firmware drives it. That is a corpus question — the output stage of the resident
kernel — and it costs nothing to answer.

⚠ And the honest bound on all of this: **a digital tap cannot touch the bit-11 block.** Those 169
words are control words — register and pointer loads — and no audio measurement, at any precision,
can see them. The digital output improves the *quality* of an audio experiment; it does not
enlarge the set of questions audio can answer.

---

## 7. What else is needed to reach 100 %

Honestly: the cascade above reaches **97.5 %**, and the CDJ-500 corpus takes the combination to
**98.1 %**. The residue is **138 words** across roughly twenty small axes — hapax `SRC` codes,
kernel-only classes, single-site `ACT` codes.

Reaching a true 100 % needs at least one of:

1. **A fourth and fifth application of the chip.** The µPD6383 was a consumer-audio part; the
   CDJ-500 is one more product, and there are others nobody has identified. Each new application
   exercises codes the others never use. *(The KN1500 shows the failure mode: a sibling that runs
   the same programs adds nothing.)*
2. **The emulator mode (R5)**, which would replace inference with observation for the whole
   residue at once.
3. **A datasheet.** Documented exhausted across every reachable channel, with the single remaining
   lead a 1995 NEC selection guide behind a paywall — *and a selection guide never carries an
   instruction format.* Treat this as closed.
4. **Accepting ARBITRARY-WITHIN-EQUIVALENCE-CLASS for the genuinely blind fields (R6)** and
   defining 100 % as "every word either decoded or proved unobservable, with its class named".
   This is the only one of the four that is certainly achievable, and it is not a cop-out: a field
   whose value cannot change any observable is decided as far as the machine is concerned.

---

## 8. What to do, in order

| # | action | cost | risk | why now |
|---|---|---|---|---|
| **1** | **The bit-11 alternate encoding.** Nine shapes, two carrying 87.6 %; a named first target and a relocation-style test that fits it | days, no hardware | none | Biggest single block, and everything else about those words is already characterised |
| **2** | **Does the kernel write `DO2`/`DO3`?** A corpus question about the output stage | hours | none | Decides whether the isolated DSP lanes are usable at all — and it gates item 5 |
| **3** | The rest of the R1 cascade — `f31 3..7`, `ACT 0x0B`, the addressing classes | weeks | none | 80.8 % → 95.2 % |
| **4** | **Order a CDJ-500**, dump it, then set it aside until 1–3 are done | one cheap player | low | Weeks of latency; worth +2.9 points *afterwards* |
| **5** | **A CN14 tap** on `SUBOUT2`/`SUBOUT3` into an I²S receiver | four wires + a cheap receiver | low — a connector, no soldering to the board | Exact integers, and the only un-summed DSP output on the machine |
| **6** | Extend the debug monitor across the CPU-2 mailbox | substantial | medium | Nothing can be uploaded to the DSP without it |
| **7** | The emulator mode (`SETRDY` / `BR-RQ`) | board modification | **high** | Only after everything above |

⛔ **And one route that closed today.** The `RQ`/`GF` flag experiments — using the chip's
host-visible flags to read results back — are **dead on the SX-WSA1R**. On IC30, `RQ1`–`RQ3`
(pins 86-88) are strapped to ground, so the host can never vary them; `GF1`–`GF3` (pins 83-85) are
unconnected stubs, so the host can never read them. The honest report is *"not available on this
machine"* — **not** *"the chip has no COND field"*. The pins exist on the die, and the CDJ-500
may well wire them.

---

## Related

| Page | Description |
|------|-------------|
| [µPD6383GF unofficial datasheet]({{ site.baseurl }}/upd6383-datasheet/) | Pinout, memories, host interface, instruction set |
| [Effects DSP (NEC uPD6383GF)]({{ site.baseurl }}/effects-dsp/) | The full technical reference this page summarises |
| [SX-WSA1 / SX-WSA1R]({{ site.baseurl }}/wsa1/) | The second instrument carrying the chip |
| [SX-WSA1 Emulation Status]({{ site.baseurl }}/wsa1-emulation/) | Including the custom-ROM debug port |
| [Help Wanted]({{ site.baseurl }}/help-wanted/) | Contributor-actionable items |
