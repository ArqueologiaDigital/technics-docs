---
layout: page
title: Acoustic Modelling LSI (L7A1429)
permalink: /wsa1-modeling-lsi/
---

# The L7A1429 acoustic modelling LSI — the device at `0x00104000`

The [SX-WSA1 / SX-WSA1R]({{ site.baseurl }}/wsa1/) is named after its modelling
engine, and this is that engine: **IC3, the service manual's `L7A1429 MODELING
LSI`**, sitting in CPU 2's address space at `0x00104000` behind a two-word port
pair. MAME models it as `l7a1429_device`, "Technics Acoustic Modeling LSI".

It is **a per-channel pair of coupled linear resonators**, sixty-four channels
of them. Each channel is programmed with a tuning, a damping one-pole filter, an
excitation shaping pair, and a position along the resonator that the firmware
modulates in real time. A third, independently indexed copy of the damping
filter sits in the register set with a fixed, tone-specified index that no editor
control can reach. **It is not a sample player**: not one of its nineteen
per-channel registers carries an address, a length or a loop point, and its own
output is not audio — it is a 13-bit waveform stream handed to the tone
generator on request. The sample player is the *other* chip.

> **Where the line between measurement and inference runs on this page.** What
> the firmware *writes* is measured, instruction by instruction. What the
> silicon *does* with it is reconstructed from the numbers' closed forms and the
> tone editor's own captions. Every row of every table below carries a grade, and
> [What is not known](#what-is-not-known) is a section rather than a footnote.

## ⚠ Two limits that do not move

**1. The part identity is settled by the schematic, not inferred.** No WSA1R ROM
names any part — but the service manual closes the chain in two steps. IC27, a
D74HC139GS, decodes CPU 2's `SCS0` with `SA14`/`SA15` into four selects, and
`1Y1` is **`WFICS` = `0x104000`** (its siblings being `SMIF` = `0x100000`, the
link; `KSCS` = `0x108000`, the keybed; and `SGCS` = `0x10C000`, the tone
generator — all four in the order the disassembly derived them). IC3's host port
then takes **`NSGCE ← WFICS`**, and IC3 is labelled **`L7A1429 MODELING LSI`**.

The interface matches the one read off the instruction stream, pin for pin:
**`NAD ← SA1`** means a single address line selects address-versus-data, which
*is* the driver's `+0 = select, +2 = data`.

⚠ What remains inference is the **internal signal path** — a vocabulary and a
coefficient set are not a block diagram. See
[What is not known](#what-is-not-known).

**1b. Its output is not audio — it feeds the tone generator.** IC3's `RQWFI` and
`IOWFI(0..12)` outputs are the nets `RQWFI` and `DWFI0..DWFI12` arriving on
**IC4's pins 25-40**: a 13-bit stream with a request line. IC4 is
`TC183C230002`, the sheet's own spelling being "TONE GENELATOR LSI", and its
crystal `X4` runs at 33.8688 MHz = 768 x 44100, which is where this page's
44.1 kHz sample rate comes from. So the modelling LSI and the tone generator are
**two stages of one signal path**, not two independent voice engines — which
settles a question the firmware alone could not.

**2. "No executable payload crosses this device" is a claim about the BUS, not
about the silicon.** The whole 2 MB image holds nine `0x00104000` literals, none
of them a read, and a live bus trace sees writes only. But **an engine with fixed
on-die microcode exposing only coefficients would produce exactly this traffic**.
The bus carries a fixed destination set with `block * 0x40 + channel` numbering
and values marshalled out of a packed record — no opaque byte stream, no
handshake, no micro-DMA channel. That constrains the algorithm from outside; it
does not open it.

## The bus interface

```
0x00104000 + 0x00   write   16-bit REGISTER NUMBER   (select)
0x00104000 + 0x02   write   that register's 16-bit VALUE   (data)
0x00104000 + 0x04   -- no located access

register number = block * 0x40 + channel        channel = 0x00 .. 0x3F
```

All nineteen per-channel registers are **16 bits**: every store into the staging
struct and every store to the data port is a word store. The eighteen non-zero
blocks run `0x0040 .. 0x0480` with no gap, each `0x40` from the last, and block
`0` is the channel with no arithmetic at all.

**The device is write-only as far as this firmware is concerned.** There is no
read port anywhere in the image — and that is a *difference from its neighbour*,
not an assumption: the companion tone generator at `0x0010C000` has a documented
read port at `+0x04` and a dedicated read accessor. A model should return 0 for a
read and log it, because a read would be new information.

**The `(select, data)` pair is the only atomic unit.** Every write is a store of
the register number followed by a store of the value, in that order, in all eight
driver routines, with one to four unrelated instructions in between and **no
interrupts disabled**. Nothing larger is atomic, and there is no commit strobe —
see [Timing](#timing-the-note-lifecycle).

**No write-recovery delay is needed.** Every `0x0010C000` data write in this
firmware is followed by five `nop`s of bus padding. Inside the eight
`0x00104000` routines that five-`nop` run occurs **zero** times; consecutive
register writes are separated only by the three to five instructions that build
the next select value. The `0x0010C000` loops of the very same reset routine are
the positive control, and they have it.

## The register table

`chan` is `0x00 .. 0x3F`; the register number is `block + chan`. Names in bold
are the tone editor's own captions, drawn by the MODELING pages' display lists.
`Q` is the 43-byte **wave-select record**, and `pN` is tone-edit parameter `N` =
wave-select byte `+0x0N` in hex.

*This is the page's `CROSSCHECK-NAME-TABLE`: `wsa1/notes/l7a1429_crosscheck.py`
reads the name column below and fails if it disagrees with the disassembly's
notes, its HLE guide or the MAME driver's `block_name()`.*

| reg | what the firmware writes | name | role | grade |
|---|---|---|---|---|
| `0x0000` | <code>(R[+0x07]&lt;&lt;8) &#124; P[+0x07]</code>; bit 7 cleared when its own bits 6..4 are non-zero; bits 13..8 = the channel on the power-on path; bit 2 set by every note event, on *and* off | — | a mode / enable word.  Its **fields** are named — bits 15 and 14 are the MAIN and SUB `RESO MODE` flags, bits 6..4 a part-level enable that gates `0x0300`, bit 7 the sign of `SUB GAIN` — but the word as a whole is not, and bits 3, 1 and 0 are unaccounted for | **UNIDENTIFIED** |
| `0x0040` | `SatAsym(P[+0x0A] + P[+0x12] + d1)`, saturating to `[0x0000, 0x7FFF]` | **MAIN RESONATOR `KEY SHIFT` + `DETUNE`** | a tuning offset in 1/256 semitone: `p29` whole semitones, `p30` ≈ 0.78 cent a step | **PROVEN** |
| `0x0080` | the same, from `P[+0x0C] + P[+0x14]` and `d2` | **SUB RESONATOR `KEY SHIFT` + `DETUNE`** | as above, from `p41` / `p42` | **PROVEN** |
| `0x00C0` | `Curve_Log2_251[clamp(R[+0x12]+R[+0x16]+R[+0x21], 0..250)] + (0x4280 − R[+0x0E]) − R[+0x0C]`, forced to `0x0000` / `0x7F00` on underflow | **resonator `P0SITI0N`**, with its `TOUCH` and its `P0SITI0N M0VEMENT` | a **log-domain period**, 3072 counts per octave = 1/256 semitone, pitch entering **negated**, pivot note 66.5, range `[0, 0x7F00]` = 10.58 octaves.  Its key-follow term is switched on and off by `FORMANT` (`FIX` / `MOVE`, p14 bit 7) | name **PROVEN**, unit and direction **STRONG**; **absolute scale UNIDENTIFIED** |
| `0x0100` | `Const_0100_251[the same index as 0x00C0]` = `0x0100` in all 251 entries; `0x0000` on the ROM-image path | — | `0x00C0`'s table-pair companion | value **PROVEN**, unit **UNIDENTIFIED** |
| `0x0140` | `Curve_Exp2Decay_256[clampU8(0xCF − g(v1) + (s8)(0x00E08C))] & 0xFFF8`, or `0x0000` on the gated arm; `g(v) = v<48 ? v/2+24 : v` | **MAIN `FITTING`**, decay form | a Q15 quantity on a 0.3763 dB/step exponential, 13 bits used, 78.6 dB span; `p21` value, `p23` touch | name **PROVEN**, role **UNIDENTIFIED** |
| `0x0180` | the same, with `v2`, from `p31` / `p34` | **SUB `FITTING`**, decay form | as above | **PROVEN / UNIDENTIFIED** |
| `0x01C0` | `high16( fold(reg 0x0400's word) × Curve_Exp2Rise_128[clamp(v1, 0..PART[+0x11])] )` | **MAIN `FITTING`**, rise form | section A's cutoff coefficient scaled by `1 − 2^(−v1/16)` ∈ [0, 0.996) = 0 to −4.56 octaves | name **PROVEN**; **STRONG** that it is the same quantity as `0x0400`; see [the one undecided reading](#the-one-arithmetic-that-reads-two-ways) |
| `0x0200` | the same, with `v2` and reg `0x0440`'s word | **SUB `FITTING`**, rise form | as above | **PROVEN** |
| `0x0240` | <code>( high16( fold(reg 0x0480's word) × Curve_Exp2Rise_128[clamp(R[+0x14]+R[+0x18]+abs(R[+0x21])/4, 0..0x7F)] ) &amp; 0xFFF8 ) &#124; 7</code> | the register **`DEPTH`** scales | section C's Rise-scaled coefficient.  Its index is `DEPTH` (p14 bits 0-6) plus `SUB GAIN` plus the `P0SITI0N M0VEMENT` term; low 3 bits a separate field | structure **PROVEN**, name **PROVEN** |
| `0x0280` | `Curve_Exp2Decay_101[clamp(R[+0x10]+R[+0x23], 0..100)]` | **`SUB GAIN`** | a Q15 gain over a 0..100 percent control with an explicit OFF, 37.3 dB taper; `p33` value, `p36` touch | **PROVEN** |
| `0x02C0` | the literal `0xFF00`, always, on every path | — | — | **UNIDENTIFIED** |
| `0x0300` | `b = ExpCurve_0_to_0x80[Q[+0x13]]`, written as <code>(b&lt;&lt;8) &#124; b</code>; `0x0000` when reg 0's bits 6..4 are clear | **`INTERACTION GAIN`** | an 8-bit gain over a 0..127 control, 42.1 dB, **duplicated into both halves**, and zero unless the part has layers grouped | **PROVEN** |
| `0x0340` | `Curve_FE05C9[i3]` | **MAIN `MUTING`**, Q13 form | the Q13 companion of `0x0400`'s cutoff — **computable from it** | **PROVEN** |
| `0x0380` | `Curve_FE05C9[i4]` | **SUB `MUTING`**, Q13 form | as above, of `0x0440` | **PROVEN** |
| `0x03C0` | `Curve_FE05C9[i5]`, `i5 = clamp(Q[+0x0F], 44..96)` | — *no editor name exists* | section C's companion coefficient | table identity **PROVEN**; name **resolved, negatively** |
| `0x0400` | `Curve_FE04C9[i3]` | **MAIN `MUTING`**, Q16 form | ★ a **one-pole lowpass cutoff**, index = MIDI note − 36; clamped `Table_FDFF96[zone] .. PART[+0x12]` = **466 Hz .. 16.7 kHz** | fit **PROVEN**, name **PROVEN** |
| `0x0440` | `Curve_FE04C9[i4]` | **SUB `MUTING`**, Q16 form | as above | **PROVEN** |
| `0x0480` | `Curve_FE04C9[i5]` | — *no editor name exists* | section C's cutoff, clamped 44..96 = **831 Hz .. 16.7 kHz** | fit **PROVEN**; name **resolved, negatively** |
| `0x0800` *(no channel)* | the literal `0x1100`, once, at power-on | — | a 20th register number, outside the per-channel map | **UNIDENTIFIED** |

Fourteen of the nineteen carry a name in the machine's own vocabulary, two are
known constants, two are **refused** a name with a reason, and one — `0x0000` —
is named only in its fields.

⚠ The two refusals are an answer, not a gap. `0x03C0` and `0x0480` have exactly
one input, `p15`, and **no editor field writes `p15`**: of 258 call sites across
the firmware's twenty tone-message builders, exactly one passes parameter
`0x0F`, and that one addresses a different record on a different screen. `p15`
is set by the `RESONATOR TYPE` preset instead. The firmware has no caption to
give those two registers, so the right result is a name withheld — not a name
guessed, and not a question left open.

### The registers group into two pairs and three triples

The A/B twinning is not a reading of the addresses; it is measured in the code,
in the ROM's own reset image and in the factory data.

```
pair     0x0040  0x0080                        MAIN / SUB tuning
pair     0x0140  0x0180                        MAIN / SUB FITTING, decay form
triple   0x01C0  0x0200  0x0240                three Rise-scaled coefficients
triple   0x0340  0x0380  0x03C0                three Curve_FE05C9 coefficients
triple   0x0400  0x0440  0x0480                three Curve_FE04C9 coefficients
alone    0x0000  0x00C0  0x0100  0x0280  0x02C0  0x0300
```

*In the code*: for each claimed pair the two code runs agree byte for byte at
0.91–0.98, against a null that slides the second run over 122 nearby offsets and
peaks at 0.20. *In the ROM*: the power-on reset image's words satisfy w5 = w6,
w7 = w8, w13 = w14, w16 = w17. *In the data*: over 133 factory wave-select
records whose framing self-checks, the ten twinned parameters are equal per
record in 130–133 cases each — and the null over all 43 × 42 ordered column
pairs finds no other cross-half twinning outside the four envelope-descriptor
parameters, which the firmware's own case table treats as a separate group.

**The third instance is real, not an artefact of the addressing.**
`Curve_FE04C9`, `Curve_FE05C9` and `Curve_Exp2Rise_128` are each cited **exactly
three times in the whole 512 KB image**, at three independent indices: two
key-scaled ones for MAIN and SUB, and a third, `i5 = clamp(Q[+0x0F], 44..96)`,
computed and cached earlier. Two further ROM images agree from paths that never
run the packer, and the third slot's index of 84 is the value the factory data
carries in 123 of 133 records.

**And the factory tones drive MAIN and SUB identically.** The two resonators
differ only through `SUB GAIN` — 100 in 131 of 133 records — and, in three
records, a −12 semitone `SUB KEY SHIFT`. They are a matched pair, not two
independent voices.

**The pairs are not "two elements per voice".** A four-element tone occupies
**four channels**, each with its own full nineteen-register set: the packer's
sub-record selector is driven by a loop counter bounded by 4 and by 2, and each
iteration re-reads a different channel byte. Element multiplicity is already
spent on channels. MAIN and SUB live *inside* one channel.


## How the names were established

The nineteen registers are named from the tone editor's seven MODELING pages,
and the instrument that reads those pages is the **screen geometry**, not a
guess at which caption goes with which parameter.

**Every value the firmware draws carries its display-RAM byte address.** The
LCD controller's own SYSTEM SET bytes give `C/R + 1 = 40` bytes per line, so
`row = address / 40` and `x = 8 · (address % 40)` put every drawn value into the
same coordinate space as the captions the same routine draws. The stride is not
fitted: sweeping every stride from 4 to 256, four of them make `PAGE1/3`'s ten
values fall into two rows with identical column sets, and what picks 40 is the
controller's own initialisation.

**A page's read-back order is its parameter map.** Each page's ENTER routine
fires a run of read-back requests at CPU 2 and stores reply *n* at
`((u8 *)0x27A6)[n]`, so the request order *is* the map from tone-edit parameter
to the RAM byte the page draws. That is checked, not assumed: the per-field
editors name an (index, parameter) pair directly, in two immediates a few bytes
apart, and **all thirty-three such bindings agree** with this map — zero
contradictions, where ten indices are in play per page, so an unrelated map could
not (see [the field editors and their limits](#the-field-editors-and-each-fields-limits) below).

That gives, among others:

| control | where it lives | what it reaches |
|---|---|---|
| `P0SITI0N` | p13, drawn as `p13/5 . 2·(p13%5)` | `0x00C0` |
| `DEPTH` | **p14 bits 0-6** | the index of `0x0240` |
| `FORMANT` | **p14 bit 7**, drawn `FIX` / `MOVE` | not a register: the packer tests that exact bit to switch `0x00C0`'s key-follow term on or off |
| `INTERACTION GAIN` | p19 | `0x0300` |
| `RESO MODE` | **p21 / p31 bit 7**, drawn `OFF` / `ON` | `0x0000` bits 15 / 14, **and** `0x0C00` = one octave added to that resonator's tuning |
| `RESO SCALE` | **p22 / p32 bit 7**, drawn `OFF` / `ON` | `R[+0x1A]` — and no further; see [What is not known](#what-is-not-known) |
| `GROUP` | p11 bits 7:6, on the MODELING top page | the part-level enable in `0x0000` bits 6..4, which gates `0x0300` |

⚠ `DEPTH` and `FORMANT` are two halves of one byte, and the firmware splits it
at exactly the bit the screen splits it at: one consumer masks p14 with `0x80`
and skips a key-follow term when it is set, the other clears bit 7 and stores
the remainder as `0x0240`'s index. A formant that is fixed or moves with the
note is what that control is for.

**`INTERACTION GAIN` has a second, independent argument** beyond its field
editor: register `0x0300` is written as zero
unless the part has layers grouped. A gain that only exists once layers are
grouped, on a screen whose grouping control decides which layers interact,
captioned `INTERACTION GAIN`. `DEPTH` and `FORMANT` have no reason to be
mode-gated; this register is.

### MAIN and SUB, from the row labels

`PAGE1/3` draws ten values on two rows with identical column sets, and the
**same paint routine** draws the labels `MAIN RESONATOR` and `SUB RESONATOR`.
Value row 156 is `+4` display rows below the `MAIN` label and value row 187 is
`+4` below the `SUB` label — the *same* offset. Swapped, the offsets are `+35`
and `−27`: unequal, and one would put a value above its own label.

That argument never mentions `SUB GAIN`, which is the other, independent reason
to call the sub side the sub side: it is the one parameter belonging to one
resonator and not the other, and the editor captions it on two pages. Two routes,
one answer. `FITTING` and `MUTING` are likewise held by two facts — the same
page's own column headers stand over their own fields, and only one of the two
families carries a key-follow stage, which is the one the editor heads
`MUTING`. The five headers are two-line stacks — `FIT`/`TING`, `MUT`/`ING`,
`KEY`/`SHIFT`, `DE`/`TUNE`, `RESO`/`SCALE` — which is why the fourth column is
`DETUNE` and the fifth is `RESO SCALE`.

### The field editors, and each field's limits

Each MODELING page routes its DATA-dial edits through a table of handler pointers
indexed by the panel event code — **twenty-four editors in all**, none of them
the target of a `call`, which is why they carried no name until the tables that
reach them were decoded. Every editor builds one 11-byte edit descriptor and
hands it to `ToneEdit_ApplyStep` (`0xFD6CE1`), which reads a **MASK**, a
**SHIFT**, a **MIN** and a **MAX** — all immediates inside the editor — and
clamps `(packed >> SHIFT) & MASK` into `[MIN, MAX]`. So **each field's limits are
read straight from the ROM**, and consumed by code read from the ROM, with
nothing interpreted between. The step is `±1`, or `±3` for the coarse key group.

Thirty-three `(screen, RAM index, parameter)` bindings come out of the
twenty-four, and **every one agrees with the read-back-order map above — zero
contradictions**; the cross-check is verified able to fail (a run against a map
with `MAIN`/`SUB FITTING` swapped registers exactly two clashes). Two independent
instruments — the order in which a page's ENTER routine fires its read-back
requests, and immediates inside routines those ENTER routines never touch — land
on the same map.

| control | parameter (MAIN / SUB) | limits |
|---|---|---|
| `RESONATOR TYPE` | p11 bits 0-5 | 0..63 (the 64-name table) |
| `GROUP` | p11 bits 7:6 | 0..4 |
| `P0SITI0N` | p13 | 0..250 = 0.0..50.0 in 0.2 |
| `DEPTH` | p14 bits 0-6 | 0..127 |
| `FORMANT` | p14 bit 7 | 0..1 (`FIX` / `MOVE`) |
| `INTERACTION GAIN` | p19 | 0..127 |
| `WIDTH` | p17 | 0..50 |
| `SPEED` | p18 | 0..50 |
| `S/H` | p18 bit 7 | 0..1 |
| `TOUCH` | p16 | −50..+50 |
| `FITTING` | p21 / p31 | 0..127 |
| `MUTING` | p22 / p32 | 0..127 |
| `KEY SHIFT` | p29 / p41 | −60..+60 (five octaves either way) |
| `DETUNE` | p30 / p42 | −128..+127 |
| `RESO SCALE` | p22 / p32 bit 7 | 0..1 (`OFF` / `ON`) |
| `SUB GAIN` | p33 (SUB only) | −100..+100, **signed** |
| `FITTING` touch | p23 / p34 | −50..+50 |
| `MUTING` touch | p24 / p35 | −50..+50 |
| `SUB GAIN` touch | p36 (SUB only) | −50..+50 |
| `RESO MODE` | p21 / p31 bit 7 | 0..1 (`OFF` / `ON`) |
| `MUTING SLOPE` | p28 / p40 | −50..+50 |
| `KEY FOLLOW` low / break / high | p26·p25·p27 / p38·p37·p39 | mutually clamped `low ≤ break ≤ high` |

Two of these settle earlier open points. **`RESO SCALE`** is edited by
`ToneEditField_A5_ResoScale` (`0xFD4EFB`) — the *same* parameter as `MUTING`
(p22 / p32) with `MASK 0x01`, `SHIFT 7` — so it is a bit-field editor over bit 7
of that byte, not a separate parameter. And the three **`KEY FOLLOW`** notes
bound one another: the editor takes its MAX and MIN from the *other two* RAM
cells, so the firmware itself enforces `low ≤ break ≤ high`, pinning the ordering
independently of any screen coordinate. `SUB GAIN` being **signed** `−100..+100`
is what makes `0x0000`'s bit 7 (the sign of `SUB GAIN`) a state a user can
actually reach.

*(`wsa1/notes/wsa1_toneedit_field_editors.py --selftest`, 61 checks.)*


## The units

This is the most useful thing on the page. Six of the nineteen registers have an
exact closed form, and the closed forms name physical quantities.

### The storage format has to be undone first

Read as `s16`, `Curve_FE04C9` is not monotone. Passed through the firmware's
**own** `fold()` — the step the packer already applies on the way to register
`0x01C0` —

```
fold(x) = (x & 0x8000) ? 0x8000 − (x & 0x7FFF) : x + 0x8000
```

both coefficient tables become strictly monotone over all 128 entries. `fold` is
a sign-magnitude → offset-binary converter, and it is the *inverse of the
table's encoding*: applying it is what makes the numbers admit any fit at all.
**The null is the two's-complement reading, which is not monotone.**

### ★★ `MUTING` is a bilinear one-pole lowpass, and its index is a SEMITONE

Over the live band `k = 9..100`, with `g = tan(π·f_k/44100)` and
`f_k = 440·2^((k−33)/12)`:

```
fold(Curve_FE04C9)[k] = round(65536 · g/(1+g))          max |residual| = 1 count
fold(Curve_FE05C9)[k] = round( 8192 · (1 − 1/(128·g)))  max |residual| = 5 counts
```

`g/(1+g)` with `g = tan(π f/fs)` is **the coefficient of a one-pole lowpass under
the bilinear transform**, and `g` is the prewarped cutoff.

⚠ **The slope is fitted, not assumed**, and the rivals are all far worse:

| fit over `k = 9..100` | R² | max residual |
|---|---:|---:|
| straight line in `F` | 0.7781 | 25678 counts |
| straight line in `log2 F` — a plain exponential | 0.9982 | 0.155 in log2 |
| **straight line in `log2 atan(F/(65536−F))`** — the claimed law | **0.99999998** | **0.00136 in log2 = 1.63 cents** |

The fitted slope is **1 / 12.0017 per index step** — twelve steps per octave to
0.01%. Forcing the slope to exactly 1/12 and solving the ROM's own entries for
the index-0 frequency gives **65.4201 Hz = MIDI note 36.0036**, which is
**0.36 cents** from note 36 exactly against a fit scatter of 1.63 cents. So

> **the cutoff index is a semitone, and `k = MIDI note − 36`.**

Four rival value-to-frequency maps were fitted as the control, and the best of
them is **50× worse** than the bilinear reading:

| map | steps/octave | max residual |
|---|---:|---:|
| **bilinear, `f = atan((1+a)/(1−a))/π`** | **12.0016** | **0.8 cents** |
| `b0` read as `f` directly | 13.3058 | 188.5 cents |
| one-pole alpha, `−ln(1−b0)/2π` | 12.4414 | 41.6 cents |
| the word read as a POLE, `−ln(abs(a))/2π` | 10.9995 | 1333.2 cents |
| `K` read as `f` | 11.6180 | 317.0 cents |

**The sample rate is 44,100 Hz and it was fixed independently.** IC4's crystal
is 33.8688 MHz = 768 × 44100; the f64 constant pool in prom_c holds `44100`,
`1/44100`, `1/220500` and `1/441000`. Requiring `f(i) = 440·2^((i+36−69)/12)` of
the ROM entries alone implies a sample rate of **44,091 ± 11 Hz** — 44,100 to
within **a third of a cent** — and no other standard rate family is reachable,
because 32 k and 48 k would need a non-integer note offset. A curve table's
closed form and a crystal on a schematic agree to 0.33 cent by wholly
independent routes.

★ **And the ceiling is Nyquist, which needs no external constant at all.** Both
tables saturate at exactly `k = 100` and hold that value for the remaining 28
entries: `θ(100) = 1.50285 rad < π/2 < θ(101) = 1.59221`. A table of a `tan()`
that stops one step before its own pole is a bilinear filter coefficient.

★ **The two coefficient tables are ONE parameter, not two.** They imply the same
prewarped cutoff to 17.4 cents worst case over the live band and 3.4 cents over
`k = 9..60`; entry for entry, `(1 − G/8192)·g = 1/128`. So `0x0340` / `0x0380` /
`0x03C0` are **computable** from `0x0400` / `0x0440` / `0x0480`. An emulator has
**one degree of freedom per section** there, not two.

```c
// registers 0x0400 / 0x0440 / 0x0480
static double a1_from_word(uint16_t w) {          // sign-magnitude Q15 -> [-1, +1)
    int mag = (w & 0x8000) ? -(int)(w & 0x7FFF) : (int)w;
    return mag / 32768.0;
}
static double cutoff_hz(uint16_t w, double fs) {
    double a1 = a1_from_word(w);
    if (a1 >= 1.0) return fs / 2.0;
    double K = (1.0 + a1) / (1.0 - a1);           // K = tan(pi * fc / fs), the prewarp
    return fs * atan(K) / M_PI;
}
```

Musical sanity, and the reason this is a filter and not a pitch: the readers
clamp the index to `44..96` and to `Table_FDFF96[zone] .. PART[+0x12]`, i.e.
**831 Hz to 16.7 kHz** and **466 Hz to 16.7 kHz**. A pitch parameter would not be
clamped to start at 831 Hz.

### ★★ `P0SITI0N` is a log-domain PERIOD at 1/256 semitone per count

```
T[0] = 0x6C00 = 27648 = 108.000 semitones
T[k] = round(27543 − 3072 · log2 k)     for k >= 1,   max |residual| = 1 count
```

**3072 counts per halving is 12 × 256**, so one count is **1/256 semitone** — the
same unit the tone generator's own pitch register uses. Null: a straight line in
`T` against `k` gives R² = 0.781; against `log2 k`, R² = 1.000000 with a max
residual of 0.56 counts.

The register the table feeds subtracts the key-followed pitch from `0x4280` =
note 66 plus the half-step centre, so **the pitch enters negated with a slope of
exactly −1**, and the result is clamped to `[0x0000, 0x7F00]` = 10.58 octaves.

> **A log-domain quantity that falls by one octave when the note rises by one
> octave is a period or a time, not a frequency.** In a resonator, an excitation
> or pickup position along the medium *is* a delay-tap time, and it scales with
> the pitch period — which is exactly a slope of −1 against key.

★ **Two independent routes meet here.** From the ROM numbers alone `0x00C0` is a
log-domain period with slope −1 against key; from the drawn captions alone it is
the resonator `P0SITI0N`, with its own `P0SITI0N M0VEMENT` page. Likewise
`0x0400`/`0x0440` are a one-pole cutoff by fit and `MUTING` by caption — and
muting a string or a bore *is* damping, which is modelled by a one-pole lowpass
in the loop. A slope of exactly −1 against key is the single strongest
discriminator available: a filter envelope's time may track the key partially; a
delay-tap position must track it exactly.

⚠ **The absolute scale is unidentified.** The unit per count, the direction and
the 10.58-octave span are fixed. The constant that turns a register value into a
time in samples is nowhere in the image, and there is no reader in the firmware
to supply one.

### The gain controls: 37 to 42 dB, and their index ranges name them

All the exponential tables share one slope — **16 steps per doubling =
0.3763 dB per step**.

| table | closed form | max residual | span |
|---|---|---:|---|
| `Curve_Exp2Decay_256` | `round(32768·2^((k−255)/16))` | 4 counts | `0` for `k ≤ 46`, then 78.6 dB |
| `Curve_Exp2Rise_128` | `32768·(1 − 2^(−k/16))` | **0 — exact on all 128** | `0` .. `0x7F7A` |
| `Curve_Exp2Decay_101` | `T[0]=0`; `round(32768·2^((k−100)/16))` | 4 counts | `0`, then **37.28 dB** |
| `ExpCurve_0_to_0x80` | `T[0]=0`; `max(1, round(128·2^((k−127)/16)))` | **0 — exact on all 128** | `0`, then **42.1 dB** |

★ **Two of them have index ranges that are UI controls, and say so.**
`Curve_Exp2Decay_101` is indexed by a value clamped `0..100`: a **0..100 percent
control with an explicit OFF position**, given a 37 dB logarithmic taper — and it
is exactly what `SUB GAIN` needs. `ExpCurve_0_to_0x80` is indexed by a record
byte `0..127`: a **0..127 control** over 42 dB, written into register `0x0300` as
one byte in **both halves**, which is the shape of a device with two 8-bit fields
fed the same number.

Nulls, over bands where quantisation is under 0.0014 in log2 so the comparison is
about the law and not the rounding: a straight line in `T` reaches R² 0.70–0.97;
a straight line in `log2 T` reaches R² 0.99985–1.000000.

### Touch scaling has an exact unit too

Four `LinCoef_*` ramps scale a record depth by the **touch level**,
`(T[D]·A) >> 5`, with the curve mirrored — not negated — for a negative depth,
so a negative depth flips which end of the range is the pivot rather than the
sign of the contribution. Each ramp is **exact** against its integer law on every
entry.

The index is the velocity: it is `voice[+0x0C] & 0x7F`, and the note is held
separately in the same record at `+0x05` as `note | 0x80`. The editor agrees six
for six — the six depth bytes these ramps consume are exactly the six fields of
the page captioned `TOUCH DEPTH`, plus `TOUCH` on `P0SITI0N M0VEMENT`.

| table | law | Q5 range | destination, and therefore its unit |
|---|---|---|---|
| `LinCoef_Position_TouchRamp_Q5_128` | `2k − 128` | −4.000 .. +3.938 | the `Curve_Log2_251` index |
| `LinCoef_Fitting_TouchRamp_Q5_128` | `65k//128 − 32` | ±1.000, bipolar, single zero at `k=64` | an exp2 index — so one unit is **0.3763 dB** |
| `LinCoef_Muting_TouchRamp_Q5_128` | `k//2 − 64`, `T[127]=0` | −2.000 .. −0.031 | **the cutoff index, in semitones** |
| `LinCoef_SubGain_TouchRamp_Q5_128` | byte-identical to the `Muting` ramp | — | a percentage of `SUB GAIN`: one point = 0.376 dB |

★ The `Muting` ramp's slope is 1/64 of a Q5 unit per touch step and its
destination is in semitones of cutoff, so **a depth byte of 64 is exactly one
semitone of cutoff per touch step**, and the signed byte's ±127 range is ±198%.
The `SubGain` ramp is the second exact one: a depth of 64 moves `SUB GAIN` by one
point of its 0..100 control per touch step = 0.376 dB, so a depth of 50 sweeps
the whole control and anything above it saturates.

⚠ **The cutoff index carries a second scaling stage, and that one *is* keyed on
the note.** `ks(Q, o)` takes a breakpoint, two note bounds and a Q5 slope, and
its slope byte is a Q5 where **32 = 100%**, not 64. The two stages differ in
their variable *and* in their constant; an implementation that shares one
constant between them is wrong by a factor of two, and one that shares the
variable is wrong about what the control does.

★ In the factory data every one of these depth bytes but a single `−5` is a
multiple of ten, so the editor's control moves in steps of ten: 15.6% of cutoff
follow per click. The `SUB GAIN` touch depth is zero in every factory record,
which is what an unused control looks like.

`Table_FDFF96` — 256 bytes, 27 distinct values `0x22..0x3C`, indexed by the key
zone — is the **lower clamp** on the cutoff index, i.e. a **minimum cutoff of
466 Hz to 2093 Hz per key zone**, a floor that keeps the filter above the zone's
own band. It has no closed form; the values are data.

### ⚠ One table is musically absurd at the sample rate

`Curve_Exp2Decay_256`'s two largest entries are `0x8000` (= 1.0) and `0x7A90`
(= 0.957520), with **nothing in between**. As a per-sample pole at 44.1 kHz,
0.957520 is a time constant of **0.522 ms**, and even 1 ms is unrepresentable. A
per-sample reading of that table is wrong.

★ Stepped instead at the firmware's own 40.69 Hz control rate, the same table
gives τ = 8.9–566 ms and T60 = **24 ms to 3.9 s**, which is musical. ⚠ But that
refresh rate is measured for the `0x00C0` / `0x0100` / `0x0240` trio, **not** for
`0x0140` / `0x0180`, and nothing in the ROM says the LSI advances anything on the
host's write cadence. It is a hypothesis with a number attached. An
implementation should make the rate a named constant and not bury it.

### The one arithmetic that reads two ways

`0x01C0` carries `b0 × r`, where `b0` is section A's own bilinear coefficient
(register `0x0400`) and `r = 1 − 2^(−v1/16)`. That number reads two ways and
**the arithmetic is identical under both**:

* as **a second, lower cutoff** for the same section — which is what the
  editor's caption structure supports, `FITTING` having a rise form and a decay
  form, the two halves of a filter envelope;
* as **an input gain pre-multiplied into the coefficient**, which is what a
  filter implementation does to save a multiply, and which explains why `0x01C0`
  lands in Q15 (`b0·r` peaks at `0x775A`) while `fold(0x0400)` is Q16.

⚠ **Nothing in the ROM decides it.** Store `b0·r` and expose both derived views;
do not commit a device to either.

## Timing: the note lifecycle

### 64 channels

Not by analogy with the neighbour, and not from the `0x40` block stride, but from
the loops that drive *this* device: the power-on reset routine contains two loops
closed by `cp HL,0x0040`, each calling a `0x00104000` writer with the loop
counter as the channel argument. Five further runtime paths bound their channel
argument with `cp H,0x40` and skip the device on `NC`, 5 of 5.

⚠ **The null matters.** On the companion device a channel argument of
`0x40..0x7F` is *not* a 65th channel — six of its routines branch on
`cp HL,0x0040` and the high arm re-aims the same staging field at another slot.
This device has none of that: `cp HL,0x0040` occurs **0** times inside the eight
`0x00104000` routines, against **6** in the companion's driver blocks. So 64 is a
count, not a re-encoding. **PROVEN.**

### Power-on

The equivalent of a device reset is the second half of the shared reset routine,
called from the very first thing the main loop does. In order: register `0x0800`
takes the literal `0x1100`; a nineteen-word ROM image is copied into the staging
struct; all 64 channels take a full nineteen-register write with the channel
number placed in word 0's bits 13..8; then all 64 channels take a block-0-only
write with bit 2 cleared.

**Total power-on traffic: 1 + 64×19 + 64×1 = 1281 register writes = 2562 word
writes to the port pair.**

★ **The reset image independently checks the register map.** Its word 4 is
`0x0100` — and register `0x0100`'s table holds `0x0100` in all 251 entries; its
word 11 is `0xFF00` — and register `0x02C0` is the literal `0xFF00`, the only
value any instruction ever puts in that word. An off-by-one in the
word↔register mapping would break both.

⚠ **Bit 2 of block 0 is not a key gate**, though it has exactly that shape:
cleared once at the end of the power-on sweep, set at every note event. The
routine that sets it has five call sites and **all five are note handlers,
including the note-OFF tail**. Recorded so it is not re-derived as a gate.

### Periodic versus one-shot

CPU 2's timer 1 interrupts at **488.28 Hz** (φT256, `TREG1` = 28, fc = 28 MHz).
Its handler steps a six-phase counter; one phase's flag reaches a dispatcher that
alternates between two paths on every call, and the odd path walks the
active-voice list. So

> **the periodic refresh runs at 488.28 / 6 / 2 = 40.69 Hz — a period of
> 24.6 ms.**

⚠ That is an upper bound as well as a rate: the flag is a level, so a main-loop
iteration longer than 12.3 ms coalesces two settings. It can be slower, never
faster.

| register | class | rate / trigger |
|---|---|---|
| `0x00C0` | **periodic — model as a stream** | 40.69 Hz per sounding voice, plus parameter edit, plus every full write |
| `0x0100` | **periodic**, but a constant on this firmware | as above; an emulator that ignores the value must still expect the writes |
| `0x0240` | **periodic** | 40.69 Hz per sounding voice on one arm, plus parameter edit, plus every full write |
| `0x0280` | one-shot + parameter edit | full writes, plus a parameter-change arm |
| `0x0140`, `0x0180` | one-shot, with a conditional extra write at note time | full writes, plus a pair write at all five note sites when a predicate returns non-zero |
| `0x0000` | one-shot, but written **twice** per note event and twice per channel at power-on | — |
| the other twelve | one-shot — voice parameters | only ever inside a full nineteen-register write |

★ **Producer and shipper match, register for register.** The sub-packer that
recomputes staging words `{+0x06, +0x08, +0x12}` has exactly the callers that
pairing predicts, and the accessor that ships them writes exactly `0x00C0`,
`0x0100`, `0x0240`. Three producers, three consumers, no leftovers. ★ And the two
periodic registers whose index carries the movement term are precisely `0x00C0`
and `0x0240` — the `P0SITI0N M0VEMENT` modulation, and nothing else.

A parameter edit or MIDI controller reaches this device through exactly three of
the parameter dispatcher's 49 arms, and they touch **four** registers — the same
three plus `0x0280`. The other 46 arms never touch it.

### Block 0 is not a commit strobe

Two independent reasons the latch reading fails:

1. **The four routines that never write block 0 are exactly the four with real
   callers.** Every parameter change that actually happens on this firmware — the
   40.69 Hz refresh, every MIDI-CC edit, the note-time `0x0140`/`0x0180` pair —
   lands on the device with **no block-0 write after it**. 4 of 4.
2. **The order is not even consistent.** Block 0 is written last in one routine,
   first in two others, alone in one, and absent from four. A commit strobe
   cannot be both first and last.

**A write to any single register takes effect on its own.** Nothing has to be
buffered until a later write arrives — and the firmware's own behaviour is the
strongest evidence: the periodic refresh rewrites 3 registers of 19 and leaves
the other 16 standing, forty times a second.

### ★ There is no key-off register

A note-off is **the same full nineteen-register re-program** with release values.
The note-off routine is byte-for-byte a different routine from the note-on one —
205 of 278 bytes differ — but its device traffic is the same shape in the same
order: block 0, then all nineteen, then all nineteen again, then the conditional
`0x0140`/`0x0180` pair.

⚠ **And then nothing.** The periodic refresh only visits voices still on the
active list, so once the voice is retired the device sees **no further traffic at
all** for that channel. The last thing written is the note-off's own nineteen
words, and **the entire decay to silence happens inside the chip, with no input.**

> That is the most load-bearing consequence of the write-only bus for an
> emulation. The release envelope is not driven from the CPU. A device that
> treats the registers as instantaneous parameters will cut every note off; the
> register values are the **initial conditions and time constants of an internal
> process**, and the model must sustain and decay a voice autonomously.

Worst case per note-on, on the busiest part mode: 1 + 19 + 2 + 1 + 19 + 19 + 2 =
**63 register writes = 126 word writes**. The two full nineteen-register bursts
back to back are real — nothing between them recomputes the staging struct — so a
model matching a bus trace must expect the burst twice.

## ⚠ `RESONATOR TYPE` is a UI preset selector the chip never sees

The tone editor's MODELING pages offer a resonator family out of a 64-name list:
`ORIGINAL STRING CYLINDER CONE FLARE PLATE L PLATE H MEMB L MEMB H THROUGH
MELLOW MUTE BRIGHT MOVE RANDOM OCTAVE HARMONIC METAL BOTTLE … SPECIAL1
SPECIAL2`. That control is wave-select byte `+0x0B`, and it is the one parameter
closed end to end from the drawn caption through the CPU 1 sender to the CPU 2
receiver.

**Writing it overwrites bytes 13..42 of the record — every coefficient in the
table above — from a preset.** Over the whole factory set the byte reads
`ORIGINAL` in **455 of 459** records; four carry a real family (types 1, 14, 32
and 63). `ORIGINAL` means "no family — these are the record's own coefficients".

⚠ **State the denominator with the rate.** 459 is the loose framing of the tone
database; a stricter one that self-checks against the element blocks yields 133
records, and every rate over *that* set excludes the tones which use the other
field of this same byte. Nothing on this page rests on a count taken over the
strict set alone.

**The other two bits of the byte are a separate control.** `p11` bits 7:6 are
`GROUP`, the second column of the MODELING top page's own legend `ON/OFF GROUP
DRIVER RESONATOR INTERACTION`. Its editor is a five-state control that ORs
`0x40` into two layers, `0x80` into all four, and can never produce `0xC0` — and
the factory data carries exactly those three values and never `0xC0`. `GROUP` is
what opens the `0x0300` gate, and eight factory tones use it: `Fantasia`,
`Dream`, `Mist`, `Halo Pad`, `Voxmosphere`, `Dark Universe`, `Goblins` and
`Windy Sweep`. **Every one is a pad**, which is what a control that makes layers
interact would be used for.

> **An emulation must implement the coefficients, not the families.** There is no
> `if (type == CYLINDER)` anywhere to write: the family list exists only to bulk
> load thirty bytes into a record, and the factory tones have all been edited
> past it. Nothing tells the chip which family it is.

The captions are **drawn**, not merely present: the WSA1R has no string table, so
every caption is a byte run inside a display-list record, and the interpreter
executes every record of the list it is handed. ⚠ The null says why that matters:
prom_b holds **2,325** runs of four or more bytes drawn only from `[A-Z ]`, and
only **594 (25.5%)** start inside a walked display-list text payload. **Three
quarters of UI-label-shaped ASCII in this image is not a UI label.** Membership
of a walked record is the discriminator, and `strings` is the wrong instrument.

The chain from caption to register is measured at every link: a tone-edit
parameter number **is** a record byte offset (the receiver computes
`base + parameter` with no indirection in between), and the control that grades
the method is one whose answer is already known — element bytes `+0x02`/`+0x03`
taken as a key into prom_d's 307-entry wave catalogue hit **392 of 392**, where
chance over the 65,536-pair key space would give 1.8, and the names round-trip
(`E.Piano 1` → `E.Piano 1`, `Marimba` → `Marimba`).

## What is not known

1. **The absolute scale of `P0SITI0N`.** Unit, direction and name are STRONG;
   the constant that turns register `0x00C0` into a time in samples is nowhere in
   the image. **This is the single most valuable missing number**, and a device
   should expose it as one named, adjustable parameter.
2. **The internal signal path.** Series or parallel; where the excitation
   waveform enters; whether `MUTING`'s two coefficients are two cascaded poles or
   one stage; how MAIN and SUB are coupled. `INTERACTION GAIN` names a register
   and a condition, but not a topology: what it is a gain *on* is not traced.
3. **What `RESO SCALE` does to the coefficients.** The control and its editor are
   located — `ToneEditField_A5_ResoScale` sets bit 7 of `p22` / `p32` (`OFF` /
   `ON`), the *same* parameter as `MUTING`, which the packer folds into the field
   `R[+0x1A]` — but what the silicon does with that field is not traced: a named,
   editable control with no traced effect on the coefficients.
4. **Whether `0x01C0` is a gain or a lower cutoff.** The arithmetic is the same
   under both readings; the chip decides, and nothing in the ROM does.
5. **Register `0x0000`'s remaining bits.** Bits 3, 1 and 0 are unaccounted for by
   any reading. The rest of the word is decoded: bits 15 and 14 are `RESO MODE`,
   bits 13..8 the channel on the power-on path, bit 7 the sign of `SUB GAIN`
   (cleared whenever bits 6..4 are non-zero), bits 6..4 the `GROUP` enable that
   gates `0x0300`, and bit 2 is set by every note event including note-off.
6. **`0x02C0` = `0xFF00`, `0x0300`'s mirrored byte, and the global `0x0800` =
   `0x1100`.**
7. **What the four private DRAM banks hold.** IC3 has four private 16-bit DRAM
   ports, `M1`, `M2`, `S1`, `S2` — the "SOUND RAM" the firmware's own bank-name
   strings refer to. The CPU never addresses that memory, and nothing in the ROMs
   can seed it. ★ The `M`/`S` naming lines up with MAIN and SUB, but that is a
   coincidence of initials between a schematic and a screen, and it is graded
   **WEAK**.
8. **`0x00E093`**, a per-element block the three gate-opening routines fill with
   both gains and both tuning words — the shape of a mix or coupling matrix over
   the four elements. It has eleven writers and **no located reader**.

**The cheapest thing that would close most of this list is still not the
instrument.** The controls are named; what is missing is what the silicon does
with three of them. The two nearest items are what the coefficients do with
`R[+0x1A]` — where `RESO SCALE` reaches them — and the reader of `0x00E093`.

## What a first implementation should do

* **Build the register file and the plumbing before any DSP.** 64 channels × 19
  registers plus the single global `0x0800`; an address latch at `+0`, data at
  `+2`; no read port; no write-recovery delay; no commit-on-block-0 model.
* **Come up in the power-on state** — `0x0800 = 0x1100`, all 64 channels loaded
  with the reset image, then block 0 rewritten with bit 2 cleared.
* **Decode the coefficients**, because that part is understood — and label it
  "the coefficient decode", not "the filter". What is proven is that the
  *numbers* are bilinear one-pole coefficients; that the chip runs a one-pole
  with them is STRONG.
* **Derive `0x0340` / `0x0380` / `0x03C0`** from their cutoff partners rather
  than treating them as a second degree of freedom.
* **Where you must fake, fake with the real mechanism**: two resonators per
  channel mixed by `SUB GAIN`, each with its tuning, its damping one-pole and its
  `FITTING` pair, and one shared `P0SITI0N` as a delay-tap time proportional to
  `2^(v/3072)` with the unknown constant exposed as a named parameter. Route the
  third coefficient set in **inert** — decoded, exposed, multiplied by nothing.
  Store `0x0000`, `0x02C0`, `0x0300` and `0x0800` and model nothing from them —
  but decode them in the debugger, because two of the four are understood:
  `0x0000`'s bits 6..4 are a part-level enable taking only `0x00`, `0x10` or
  `0x20`, and `0x0300` is `INTERACTION GAIN` written into both halves of the
  word, zeroed unless that enable is non-zero. Put every stand-in behind one
  switch so it is drop-in replaceable.
* **Do not call it a sound device.** IC3's output leaves on `RQWFI` and
  `DWFI0..DWFI12` into IC4, the tone generator at `0x0010C000`: a 13-bit word on
  request, not audio. Until the tone generator is modelled and the six 16 Mbit
  wave mask ROMs are dumped, a device here emits into nothing. The right first
  device is a register file with a decoded, inspectable parameter view.

## The resonator coupling

The two resonators interact, and **not through a register** — there is none. Three routines fill a
68-byte argument block whenever layers are grouped, and a solver evaluates the loop characteristic
function of the grouped resonators, converting the phase error into a pitch offset:

    D = -3072 * log2(1 - dphi / 2pi)        in 1/256 semitone

which is added to the MAIN and SUB tuning words before they reach `chan+0x0040` and `chan+0x0080`.
Its constants are Q11 renderings of named quantities — `0x555` = 2/3, `0x1922` = π, `0x3244` = 2π,
`0x146` = 1/2π — and `INTERACTION GAIN` sets the solver's pole radius through the same curve that
feeds register `0x0300`.

★ **So an emulation faithful to `chan+0x0040` and `chan+0x0080` already models the interaction.**
The offset is quantised to 13.28 cents per index step and bounded to +1146 / −675 cents; it is
exactly zero when `INTERACTION GAIN` is zero, and when every grouped resonator shares one tuning
word. Derivation and controls: `wsa1/notes/FINDINGS-l7a1429-e093-block.md`, probe
`wsa1/notes/w24_e093_coupling_solver.py`.

## Where this lives in the disassembly

The register blocks are `.equ` symbols in the driver's own header, so the source
reads in the same vocabulary as this page rather than in bare numbers:

| symbol | block | |
|---|---|---|
| `DEV104_BASE` | `0x00104000` | `+0x00` select, `+0x02` data |
| `DEV104_MAIN_TUNE` / `DEV104_SUB_TUNE` | `0x0040` / `0x0080` | KEY SHIFT + TUNE |
| `DEV104_POSITION` | `0x00C0` | the log-domain period |
| `DEV104_MAIN_FITTING_DECAY` / `_SUB_` | `0x0140` / `0x0180` | |
| `DEV104_MAIN_FITTING_RISE` / `_SUB_` | `0x01C0` / `0x0200` | |
| `DEV104_SUB_GAIN` | `0x0280` | |
| `DEV104_MAIN_MUTING_Q13` / `_SUB_` | `0x0340` / `0x0380` | |
| `DEV104_MAIN_MUTING_Q16` / `_SUB_` | `0x0400` / `0x0440` | the bilinear cutoff |
| `DEV104_BLK_0000`, `_0100`, `_0240`, `_02C0`, `_0300`, `_03C0`, `_0480`, `_0800` | | **named by block number on purpose** — a symbol that guessed would be believed |

Two of those block-number symbols now have an earned name, and the MAME driver
prints it in a bus trace: `0x0240` is the register `DEPTH` scales and `0x0300` is
`INTERACTION GAIN`. The other six stay numbers: `0x0000`, `0x0100`, `0x02C0` and
`0x0800` are unidentified, and `0x03C0` and `0x0480` have no name to give.

The curve tables carry the same vocabulary — `Curve_Muting_Cutoff_Q16_128`,
`Curve_Muting_Cutoff_Q13_128`, `Curve_Position_Log2Period_251`,
`Curve_Fitting_Exp2Decay_256`, `Curve_Fitting_Exp2Rise_128`,
`Table_Muting_CutoffFloor_ByKeyZone_256`, and the four `LinCoef_*_TouchRamp_Q5_128`
touch ramps — indexed by VELOCITY, not by key: their index is `voice[+0x0C] & 0x7F`,
and the voice record holds the note separately at `+0x05` as `note|0x80` — each documented above its definition with its fit, endpoints, unit
and grade.

| file | what is in it |
|---|---|
| `wsa1/prom_c/devices/dev10c_dev104_drivers.s` | the driver, the symbol definitions, and the full register map |
| `wsa1/prom_c/data_tables/tail_data_zone.s` | the curve tables and the touch ramps |
| `wsa1/prom_c/field_accessors.s` | the packers that compute each register's value |

⚠ Note that `dev10c_dev104_drivers.s` holds the drivers for **two** devices. The
four routines in it that are still `sub_XXXXXX` drive `0x0010C000`, the tone
generator's register file, not this chip — their block numbers merely overlap.

## Reproducing every number on this page

Each script reads the ROM images and no `.s` file, and each carries a
`--selftest` that must reject a wrong value. All paths are relative to the
[disassembly tree](https://github.com/ArqueologiaDigital/kn5000-roms-disasm).

| script | the question it answers |
|---|---|
| `wsa1/notes/dev104_topology_probe.py` | what kind of engine the nineteen registers add up to — the section census, the code-pairing nulls, the factory-data twinning, the shift adjudication |
| `wsa1/notes/lsi_curve_tables.py` | what quantity each ROM curve produces — every fit, with its residual **and** its null (`--fit`, `--summary`, `--dump NAME`) |
| `wsa1/notes/wsa1_l7a1429_write_timing_probe.py` | when each register is written and how often — the channel count, the bus surface, the refresh rate, the note lifecycle |
| `wsa1/notes/wsa1_toneedit_vocabulary.py` | what the machine calls each register — the walked display lists of the SOUND EDIT screens, with the `strings` null |
| `wsa1/notes/wsa1_toneedit_field_editors.py` | each field's limits and step — the 24 DATA-dial editors, their edit descriptors, and the 33-binding cross-check against the read-back map |
| `wsa1/notes/wsa1_tone_record_probe.py` | the 43 wave-select columns, the factory-data signatures, and the wave-catalogue control |
| `wsa1/notes/prom_c_dev104_regmap_checks.py` | what the firmware writes into each register, decoded from the instructions that compute it |
| `wsa1/notes/l7a1429_crosscheck.py` | do those documents agree — every register block named in both the sequencing and the curve account; **the name of every block, compared across four artefacts at once**: this page's register table, the disassembly's editor-pages note, its HLE guide and the MAME driver's `block_name()`; the sample rate re-derived from the crystal; and the semitone claim re-derived from equal temperament |

The register map's own prose lives in the disassembly beside the code it
describes, in `wsa1/prom_c/devices/dev10c_dev104_drivers.s`.

## Related

| Page | Description |
|------|-------------|
| [SX-WSA1 / SX-WSA1R Overview]({{ site.baseurl }}/wsa1/) | The machine, the hardware, the memory maps, the model strap |
| [Emulation Status]({{ site.baseurl }}/wsa1-emulation/) | The MAME driver, what is modelled and what is not |
| [Disassembly]({{ site.baseurl }}/wsa1-disassembly/) | The byte-exact reassembly the register decode comes out of |
| [Control Panel & Switch Matrix]({{ site.baseurl }}/wsa1-panel/) | The panel the tone editor is driven from |
| [KN5000 Tone Generator]({{ site.baseurl }}/tone-generator/) | The PCM sibling: the KN5000 commands no such per-channel modelling device |
