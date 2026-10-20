---
layout: page
title: KN7000 Effects DSP (ADSP-21065L)
permalink: /kn7000-effects-dsp/
---

# KN7000 Effects DSP (ADSP-21065L)

The KN7000's reverb, chorus, multi-effects and equalizer all run on **IC306**,
an **Analog Devices ADSP-21065L** — a 32-bit floating-point "SHARC" DSP (part
marking `S21065LKS240`, rated and run at 60 MHz), with two 16-Mbit SDRAMs
(IC307/IC308) for delay memory. It sits on the
[sound board]({{ site.baseurl }}/kn7000-sound-subsystem/) beside the tone
generators, which send it audio and mix its returns into the main DAC feed.

The striking result of reverse-engineering it: **the DSP has no boot ROM, and
its programs are embedded in the main firmware.** So the entire effects engine —
kernel and every effect algorithm — was recovered from `kn7000_program.rom`
alone, with no physical chip and no undumped ROM. All 80 programs are
disassembled and documented in the project's [`technics-roms-disasm`](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/kn7000) repository
(`kn7000/dsp/`); this page explains how it works.

> **The documentation pass over the pool is complete.** Every record — the
> kernel, the four boot probes, all 72 effect programs and the three data
> records — now has a full algorithm identification, with the GUI names pinned
> from the firmware's own descriptor tables. The consolidated result, from the
> Moorer/Dattorro reverb to the Leslie simulator's 7:6 rotors and the
> brass-simulator physical models, is on the companion page:
> **[The Complete Algorithm Catalog]({{ site.baseurl }}/kn7000-dsp-algorithms/)**.

## Host boot: the CPU loads the DSP

Because the SHARC has no external boot memory, the MN10300 **host-boots** it: it
writes a register index to `0x98000000` and streams program/data words to
`0x9C000000`. The firmware sends a **pool of 80 download records** stored in the
program flash at CPU `0x486BCEC4..0x486CE68D` (≈ 71.6 KB). Each record is a run
of blocks:

```
block  = id 0x2004 | mode (PM=program / DM=data) | target address | length | payload
record = one or more blocks, ended by a zero terminator
```

Program-memory payload is packed as 48-bit SHARC instruction words (the DSP's
native width); data-memory payload as 40-bit words. A small tool walks the pool,
unpacks it, and disassembles every program with `unidasm -arch sharc`. The
unpacking is verified correct because it reproduces the ADSP-2106x **reset and
interrupt vector table** exactly (an `IDLE` at the reset vector, a jump to the
init handler, and RTI-filled interrupt slots).

## The runtime: a 10-slot effect engine (the kernel)

One record is the **resident kernel** — downloaded once at boot; every effect
program then loads *on top of it*. From its disassembly:

- **The reset handler** configures a single interrupt (IRQ0, the per-sample /
  per-frame tick), sets up the serial audio ports (SPORTs) and their DMA, points
  the delay-line circular buffers at the external SDRAM, clears that delay RAM,
  and enters the main loop.
- **The main loop** waits for the IRQ0 tick, then walks a fixed chain of effect
  **units**, each with its own program (loaded at program address `0x8400`), a
  block of working **state**, and a block of tunable **parameters**. Audio
  arrives and leaves over the SPORTs at 44.1 kHz.
- Until a real effect is downloaded into a slot, that slot runs the kernel's own
  7-instruction **passthrough** (read input, write it dry to the outputs).

So the DSP is a **ten-slot insert processor**. The firmware assigns fixed roles
to the slots: reverb (unit 0), multi (unit 1), a pool of five per-part
Sound-DSP / Digital-Effect inserts (units 2–6), mic reverb (unit 7), equalizer
(unit 8) and chorus (unit 9). This matches the instrument's Reverb / Multi /
Sound-DSP / Mic / EQ / Chorus effect structure.

## How the CPU chooses an effect

When you change an effect on a menu, the firmware calls a selector with a
**(unit, type)** pair: *which* of the ten slots, and *which* effect type
(0–0x91). It validates the pair against a per-unit **whitelist**, whose contents
agree with the unit roles captured live on 2026-07-20:

| Unit | Role                                                                           | Accepted effect types                          |
|------|--------------------------------------------------------------------------------|------------------------------------------------|
| 0    | Reverb                                                                         | `0x00`, `0x09`, `0x10`–`0x1F`                  |
| 1–6  | Multi (unit 1) and the per-part Sound-DSP / Digital-Effect inserts (units 2–6) | large shared set                               |
| 7    | Mic reverb                                                                     | `0x00`, `0x58`–`0x5B`                          |
| 8    | Equalizer (final 5-band bus)                                                   | `0x4F` only                                    |
| 9    | Chorus                                                                         | `0x00`, `0x01`, `0x02`, `0x04`, `0x40`, `0x52` |

An effect **type** is turned into a pool record through a **master table in ROM**
(146 pointers). Decoding that table gives the authoritative type → program map —
this part is *fact*, not inference. The order of programs in the pool is not the
type order; the table remaps it.

## The effect catalogue

Reading the SHARC opcodes identifies what each program computes. The building
blocks are the classic ones of digital audio effects:

- **Delay lines** — a circular buffer in SDRAM, written each sample and read at
  an offset; with feedback this is a **comb filter**, the core of reverb and
  echo.
- **Allpass sections** and **diffusion** — an *allpass* filter passes all
  frequencies at equal level but delays them, and a cascade of allpass sections
  is a **diffuser**: it progressively smears a single sharp echo into a dense,
  smooth tail. Diffusion is the classic reverb-construction technique (the
  Schroeder / Moorer reverberator designs of the 1960s–70s): comb filters set
  the decay time, and allpass diffusers fill in the echo density so the result
  sounds like a real room rather than a series of distinct repeats.
- **Biquads** — two-pole/two-zero filter sections, used for the equalizer and
  for tone shaping inside other effects.
- **LFOs** — a phase accumulator reading a waveform table, modulating a delay
  tap (**chorus / flanger / phaser**) or a gain (**tremolo / auto-pan**).
- **Waveshapers** — a nonlinear transfer function (here a cubic soft-clip with an
  auto-gain front end) for **overdrive / distortion**.
- **Envelope followers + gain** — for **compressors / limiters**.

The 72 effect programs sort into these algorithm classes. Records whose program
code is **byte-identical** are pure preset variants — the same algorithm with
different coefficient values — and this was verified by comparing the extracted
code directly. Examples:

| Group                | Programs                                                                                                        | Algorithm                                                                                      |
|----------------------|-----------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| Reverb unit (0)      | rec51–56: essentially one program (two records differ only in four early-tap immediates), six coefficient banks | Moorer-style reverb: early-reflection taps, allpass diffuser, two damped combs                 |
| Chorus unit (9)      | rec06, 07, 09, 49, 70: five distinct programs                                                                   | quadrature-tap ensemble choruses, a flanger, the triangle-trio chorus and a delay+chorus combi |
| Mic-reverb unit (7)  | rec58–61: one program whose variants differ only in six tap immediates and their data                           | half-rate series-allpass (Schroeder) reverb                                                    |
| Equalizer (8)        | 1 program                                                                                                       | cascaded biquad, 5-band                                                                        |
| Multi / insert (1–6) | distortion, delay, tremolo, phaser, compressor, pitch-shift, filter…                                            | the full mix of the blocks above                                                               |

A per-program table — effect type, target unit/role, algorithm class, preset
family, and confidence — is maintained in the project notes alongside the
disassembly. The **algorithm** of each program is read with high confidence from
the code, and the exact **preset names** as they appear on the panel are ROM
fact: the firmware's preset-descriptor and group tables have been decoded (see
[The Complete Algorithm Catalog]({{ site.baseurl }}/kn7000-dsp-algorithms/)).

## Two more record kinds

- **SDRAM self-tests (4 records).** Before loading the kernel, the CPU runs four
  short programs that march-test the DSP's external SDRAM — two bit patterns over
  two address regions — and report pass/fail through a host register. They
  contain no audio processing; they are the "DSP alive / DSP RAM OK" power-on
  check.
- **LFO waveform tables (3 records).** Three data-only records hold alternate
  **modulation shapes** — sine, triangle and square — that the CPU can push to
  the DSP to change a modulated effect's LFO on the fly without reloading its
  program.

## Cross-model note

The KN6000 and KN6500 use the **same** ADSP-21065L and carry a **byte-identical**
program pool to one another; compared with the KN7000, all 80 records carry
byte-identical data (coefficients and tables), while the program code differs in
77 of them, the kernel included. The KN6000/KN6500 code is an older build. One
DSP model and one effect analysis therefore serve all three instruments — see the
[KN6000/KN6500 notes]({{ site.baseurl }}/kn6000-hardware/). (The KN5000 is
different: its effects run on an NEC uPD6383GF (IC311) and an MN19413 (IC310).
The sub CPU uploads IC311's microprograms at run time, but that chip's
instruction set has no public documentation and is only partly decoded; see the
KN5000 [Effects DSP]({{ site.baseurl }}/effects-dsp/) page.)

## Why this matters for emulation

Unlike the tone generators, whose samples had to be
[read from the instrument's own wave ROMs]({{ site.baseurl }}/kn7000-sound-subsystem/#wave-roms-ic203-ic204-ic207-ic208),
the effects DSP is **fully recoverable from the firmware alone**. Both the DSP core and its programs
exist, and the integration path is now completely mapped out:

- **The DSP core is already in MAME.** MAME emulates the ADSP-2106x SHARC family
  (the `ADSP21062`/`ADSP21060` devices) — the same instruction set the 21065L
  uses — with a mature interpreter, a recompiler and a disassembler proven in
  shipping arcade drivers. No new instruction decoding was needed, though the
  recompiler still needed the fixes listed under *Fix catalogue* below.
- **The programs are recovered** — all 80 records, kernel and effects, extracted
  and disassembled from the firmware (above).
- **The 21065L's memory personality has been reverse-engineered from the program
  itself.** The public summary datasheet doesn't give the internal-memory or I/O
  register map, so it was *derived from what the program actually uses*: its code
  lives at program address `0x8000`–`0x8Dxx`, its data at `0x9800`–`0x9Cxx` and
  `0xC000`–`0xC3xx`, its delay buffers in external SDRAM from `0x80000`, and it
  touches a specific, now-enumerated set of on-chip I/O registers (serial-port,
  SDRAM-controller and DMA control blocks). That is exactly what a MAME
  `adsp21065l` device variant needs.

All of that device work has since been done — see the update below. The 21065L
variant was added to the project's fork of MAME's SHARC core, the host-boot
upload (the `0x98000000`/`0x9C000000` port) was wired so the firmware loads the
DSP exactly as it does on hardware, and — the one piece with no MAME precedent —
the serial-audio ports were modelled so sound flows from the tone generators into
the DSP and back into the master tone generator, which mixes it into the DAC
feed. The recovered programs *run* on MAME's SHARC core, which independently
validated the whole disassembly. What was the best-understood path forward is
now the most complete part of the KN7000 sound story.

## 2026-07 update: it works — the emulated DSP now plays real effects

> **Where this runs.** Everything in this section is the project's own MAME work:
> the kn7000_mame overlay, and a branch prepared for upstream,
> `technics-kn7000-dsp`. That branch is queued behind the tone-generator branch
> and has not been published or submitted yet. The `kn7000` driver in upstream
> MAME ([mamedev/mame#16250](https://github.com/mamedev/mame/pull/16250), merged
> 2026-10-07) leaves the effects DSP out and makes no sound (`MACHINE_NO_SOUND`).

Everything above became a working emulation in July 2026: the MAME driver
host-boots the recovered kernel, uploads the firmware's effect chain, and a
piano note with reverb ON is clean audio with a naturally decaying tail. The
route there uncovered hardware truths that were not visible from the static
program alone; they are recorded here because they *are* the KN7000's design.

### How MAME runs it: an LLE kernel and a dry-passthrough bridge

The recovered kernel runs under **low-level emulation** on MAME's SHARC core: the
21065L personality (vector base, host-boot port, internal memory map and IOP
register set) was added as a device variant, the MN10300 host-boots it as the
hardware does, and the **recompiler is enabled** — so stepping the effects kernel
every audio frame costs little more than leaving the DSP idle (near-free).

A bridge sits between the tone generators and the speakers
and carries audio across the CPU/audio-thread boundary over two 44.1 kHz rings:
one pushes each TG frame into the DSP, the other pops the DSP's processed frame
back out. When the DSP is not yet producing (early boot) — or an effect is off —
the bridge simply passes the TG through, so the **dry baseline is bit-transparent**
(TG → DSP → speaker was verified spectrally identical to the DSP-off path within
1 %). Each audio-frame IRQ0 tick reads the DSP's unit-0 SPORT **return** buffer
(data memory `0xC342/43`, the runtime-derived TX0) and writes the TG **send** into
its unit-0 SPORT **input** buffer (`0xC362/63`, RX0); the ring buffering is what
keeps the CPU-timeline DSP and the audio-thread stream aligned (an earlier
fixed-slot exchange produced a ring-misalignment artifact, since resolved). In
the overlay the bridge is a `kn7000_dsp_bridge_device`; the branch prepared for
upstream moves its rings and returns into the tone-generator device (see
[why there is no bridge device]({{ site.baseurl }}/kn7000-driver-internals/#the-audio-path-and-why-there-is-no-bridge-device)).

### The runtime topology: a TDM patchbay into the tone generator

The DSP's serial outputs feed **no DAC**. All four SPORT transmit pins loop
back into the tone generator (`DT0A/DT0B/DT1A/DT1B → TG SDIE0-3`), and the DSP's
TX stream is a time-multiplexed **per-unit patchbay**: each of the kernel's 10
effect units owns a stereo *return* pair in the frame, and reads its *input*
from the matching slot 0x20 above it:

| unit                                | program         | return (L/R)               | input       |
|-------------------------------------|-----------------|----------------------------|-------------|
| 0 (panel REVERB)                    | selected type   | `0xC342/43`                | `0xC362/63` |
| 1 (MULTI) / 2..5 (per-part inserts) | selected types  | `0xC344/45` .. `0xC34C/4D` | +0x20 each  |
| 6                                   | per-part insert | `0xC358/59`                | `0xC378/79` |
| 7 (MIC REVERB)                      | rec58-family    | `0xC350/51`                | +0x20       |
| 8 (EQ)                              | rec34           | `0xC352/53`                | +0x20       |
| 9 (CHORUS)                          | rec49-family    | `0xC356/57`                | +0x20       |

The **tone generator** performs the final mix: its output-bus registers
(group 0x20) crossfade each DAC channel between the TG's direct sound and the
DSP *returns* — the panel REVERB button toggles exactly that crossfade
(`0x803A = 007F/7F00`), and REVERB TOTAL DEPTH is the return level
(`0x8338 = 0x8500|depth`). The TG's three effect sends enter at the input pairs
of unit 0 (REVERB, `0xC362/63`), unit 1 (MULTI, `0xC364/65`) and unit 9
(CHORUS, `0xC376/77`).

### Hardware truths required for a faithful emulation

- **MODE1 ALUSAT is load-bearing.** The kernel's only mode write
  (`BIT SET MODE1 0x3000`) enables integer *saturation*; the effects' triangle
  LFOs are saturate-then-reflect generators. An emulator that wraps integer
  adds turns every such LFO into a permanent ±2³¹ two-sample oscillation — the
  signature is an input-independent, never-decaying full-scale wash.
- **SPORT data is sign-extended** (`DTYPE=01`, right-justified): 24-bit samples
  must be delivered sign-extended into 32-bit words. Zero-padding turns every
  negative sample into ≈ +2× full scale (a rectified pedestal that rails every
  unit's output limiter).
- **The host interface is the stock ADSP-2106x IOP-register protocol** — the
  "index" written to `0x98000000` is literally the SHARC IOP register address
  (IIEP0/IMEP0/CEP0/DMAC-EP0/EPB0...). All runtime parameter and level traffic
  travels as ordinary framed DM/PM uploads; there are no hidden level registers.
- **The DSP runs 44,100 effect frames per second**, one host handshake per
  frame, as the owner's unit showed ([below](#the-chip-on-the-owners-instrument-2026-10-20)).
  Per frame the kernel walks the unit CALL chain (slots at PM `0x8080-0x80A0`,
  patched to relocated programs at `0x8400 + unit×0x100`). The part is the
  60 MHz speed grade (KS-240), which leaves about 1,360 cycles a frame; the
  overlay emulator clocks its SHARC at 66 MHz, and the chip's own clock has
  not been measured.

### Fix catalogue for MAME's SHARC core

Emulating this machine surfaced core bugs relevant to every SHARC system:
missing ALUSAT in the recompiler's entire fixed-point ALU family (add/sub,
carry forms, negate, inc/dec, dual add/sub — the interpreter had it), a
circular-buffer wrap off-by-one (`> B+L` vs `≥ B+L`), pre-modify addressing
never applying circular wrap, fixed-point AVG truncating where the TRM
specifies round-to-nearest, unrounded SSFR multiplier forms, and FIX-overflow
undefined behavior. A **performance** gap too: the recompiler translated *no*
fixed-point multiplier at all — the entire single-function multiply / MAC family
fell back to the interpreter. Measuring the fallback path showed the KN7000
effects kernel hits it ~66 million times per second of audio; giving those a
native code path (verified bit-identical) — together with the equally-unimplemented
fixed-point average the same kernel uses — removes over 99 % of all interpreter
fallbacks during a reverb (~82 million per run down to under half a million).
The 21065L personality (vector base, host boot, memory map, IOP set) lives, with
the fixes above, in the project's SHARC fork: the published kn7000_mame overlay,
and the branch `technics-kn7000-dsp` prepared for upstream, which has not been
published or submitted yet. One fix reached upstream independently: the
circular-buffer wrap, merged as
[mamedev/mame#16016](https://github.com/mamedev/mame/pull/16016) on 2026-09-25.

### Emulation status: which effects are audible (2026-07)

The MAME bridge carries tone-generator audio through the DSP. The boot-default
**reverb executes on unit 0** and is fully audible and faithful (clean, decaying,
robust under dense input). **Chorus is also audible** (July 2026): it runs on
unit 9 (rec49, the triangle-trio chorus), and the bridge now feeds that
unit its send (the low byte of sub-TG reg `0x8198`, tracking the on-screen CHORUS
DEPTH) and sums its return as an independent wet — verified as a real chorus
(LFO comb modulation, not a doubled note), with the reverb output kept
bit-identical when chorus is off. (Until 2026-07-20 the bridge fed the chorus
into unit 4 and SOUND DSP into unit 9. Each was audible only because the other
effect's program sat in that slot. A live capture of the firmware's effect
selections then re-pointed both.)

**SOUND DSP** (unit 2 for part RIGHT 1, rec08 Enhancer by default) and **MULTI**
(unit 1, rec15) are also audible (July 2026): each is fed from its send
register (SOUND DSP `0x8098`, MULTI `0x8298` — both low bytes track the
on-screen DEPTH) and summed as its own independent wet. MULTI's unit was pinned
by diffing the coefficient blocks between two of its *types* (a delay vs a
distortion) so the shared effect-bus refresh cancels — unit 1 rewrote 43 words
while the rest moved 1–2. **Four effects are now audible** (reverb, chorus,
SOUND DSP, MULTI), verified coexisting with no clipping. The remaining **EQ**
(unit 8) is a master/insert (a different integration) and is a follow-up. All
ten effect programs are loaded and run every frame; the silent ones were simply never fed
(the bridge historically filled only unit 0's input slot). A special case: four
of the seventy-two effect programs, the mic reverbs rec58–61 on unit 7,
gate on the SHARC **FLAG3** input pin, which the kernel uses as an fs/2
frame-parity strobe. The owner's unit confirmed it (FLAG3 high on every other
frame), and since 2026-10-20 the overlay drives FLAG3 that way, so their ring
scrolls at half rate as on the chip.

**Divergence sweep (July 2026): every effect type validated.** The reverb-rail
bug was root-caused to the recompiler missing the SHARC's fixed-point saturation
mode (a triangle LFO wrapped instead of clipping, and the feedback loop turned
that into a permanent full-scale buzz). To prove the fix held for *every*
effect type — not just the reverb — a harness walked every effect type on all
four screens (**241 selections**), reprogrammed each unit, played a note, and
watched two independent alarms: a 60 Hz sampler on the DSP's own output slots
(rail = 94 % of full scale, catches self-excitation even over silence) and a DAC
clip check (catches anything audible, by a separate path). Result: **zero rails,
zero clips**; the loudest was the Concert reverb at ≈12 % of full scale, over 8×
below the rail. The load-bearing cases are the LFO-driven flanger, phaser and
rotary programs — built on the same clip-and-fold arithmetic that sank the reverb
— which all pass at ≈5 %. The fix generalizes to the whole class. (Scope: the
non-reverb units mostly ran over near-silence during selection, so this proves no
program *self-excites* to the rail — the input-independent failure that actually
occurred; heavy per-effect drive is a separate follow-up.)

On real hardware the TG routes each part to multiple effect units through its
per-channel output-bus / effect-send matrix (sub-TG register group `0x20`, 64
channels × `0x10`) and sums all four returns into the DAC. Each effect has both a
**send** (reg 8, how much signal enters the effect) and its own **return** (reg
0xA low byte, how much of the effect's output reaches the DAC). (Decoded
2026-07-20: group `0x20` is a per-part send matrix, address
`0x8000 | row<<8 | part<<4 | reg`. Row 0 is the reverb send, row 1 the chorus
send, row 2 the multi send and row 3 the level/depth bank. The "channels" below
are therefore rows of mixer parts, and parts 3, 6 and 9 are the reverb, multi
and RIGHT 1 insert returns.)

**Per-effect returns (July 2026).** A live per-effect toggle capture pinned each
effect's own return register — REVERB = ch03 (`0x803A`), SOUND DSP = ch09
(`0x809A`), MULTI = ch06 (`0x806A`) — and proved the returns are **independent**:
pressing REVERB moves only ch03's return and leaves the others untouched. (CHORUS
is the exception: toggling it moves only its send `0x8198`; it has no separate
return register, so its wet is send-driven.) The emulation now scales each
effect's wet by its own return, so **turning reverb off no longer mutes chorus,
sound-DSP or multi** — they were previously (incorrectly) scaled by the reverb
return. Verified: the reverb-only output is bit-identical before/after, and with
reverb off the sound-DSP unit's output now reaches the DAC through ch09's return.

The one honest open item is **absolute wet level**. The routing, the on/off
behaviour and the per-effect independence are all correct and grounded in captured
hardware register traffic, but each effect's return is summed at a fixed makeup
constant that has **not yet been calibrated against a real KN7000** — so the exact
dry-vs-wet balance is still provisional and awaits an A/B against the instrument.
(This is the classic remaining gap once an algorithm is faithful: it does the
right thing, at a level that still needs a reference ear.)

## The chip on the owner's instrument (2026-10-20)

Three probe builds of the [ROM dumper]({{ site.baseurl }}/kn7000-rom-dumper/#the-probe-builds-passes-5-to-9)
read the running DSP on the owner's KN7000 (program 893), passes 6 to 8. They drive no port
themselves: they find the firmware's own host-port routines by code signature and call them, so
every access keeps the firmware's lock, its handshake wait and its "DSP dead" guard. The dead flag
stayed 0 through all three. The files hold the DSP program the firmware loads, so they are kept
privately; what they showed:

| question                  | what the chip said                                                                                                                                              |
|---------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| set-up (pass 6)           | as emulated: SYSCON `0x410` (16-bit host bus, low half first), the eight SPORT DMA chain pointers, DMAC0 `0xA0`, WAIT, SDRDIV, the SPORT control bits           |
| downloaded code (pass 7)  | identical to the emulator's, word for word: kernel, helpers, boot-init, the ten CALL slots and the nine effect programs (3,584 PM and 3,456 DM words read back) |
| frame rate (pass 8)       | **44.1 kHz, one handshake per frame**: the handshakes lie on a lattice of 22.68231 µs, 44,087 Hz by the firmware's tick                                         |
| FLAG3 (pass 8)            | high on **alternate frames**: the ring-3 pointer steps on 0.5000 of the frames                                                                                  |
| MSGR2 (passes 6 and 8)    | holds I3, the **ring-3 pointer**, and moves: the mic-reverb effects 58-61 save I3 there and read it back                                                        |
| state the chip keeps      | DMASTAT `0x33F` (all eight SPORT DMA channels running), SYSTAT `0x13`, IOSTAT `0x80000000`, STCTLx status bits, IOCTL bits 31 and 15 reading 0, MSGR3 `0`       |
| SPORT rings at every read | receive rings at their base + 3 (count 5), transmit rings at base + 5 (count 3): every firmware access lands at the same point of the frame                     |
| timers                    | unused (TPERIOD0/1 are 0)                                                                                                                                       |

**How the rate was measured.** Each of the firmware's data-port accesses first writes 1 to G17ICR
and waits for the DSP to raise interrupt group `0x17` again; if a wait runs out after `0x3FFFF` polls,
the firmware sets its dead flag and leaves the DSP alone until the next power-up. Pass 6 saw the
accesses come 24.15 µs apart but timed them only with the millisecond counter, which left two
readings open. Pass 8 stamped them with the main CPU's timer 4, which the firmware programs as its
1 kHz tick (`TM4BR` `0x7D0`, counting at 2 MHz). The stamps fit one kind of event every 22.68231 µs.
96.8 % of the firmware's accesses take one frame each. The 44,087 Hz figure takes the tick as
exactly 1 ms; the DSP and the CPU run from separate crystals.

**Pass 7 read the DSP's memory back** over the same port: external-port DMA channel 8 in transmit
direction (DMAC0 `0xA5` for program memory, `0x45` for data memory), one word through EPB0 at a
time. It restored the channel's four registers afterwards. Every word the firmware downloads
matched the emulator. Words the firmware never writes hold power-on SRAM contents on the chip
and 0 in MAME. Unit 0's slot read `06BE04008400`, "CALL (0x8400) (DB)".

### What the emulator took from it

All of it is in the project's overlay (kn7000_mame, `OVERLAY-GAPS.md` items G4 and G20), for the
KN7000 only:

- **MSGR read-back.** Pass 7 found one emulator bug. The kernel's own reads of IOP registers
  returned 0, so the mic reverbs restored I3 as 0. The kernel's ring-3 scrub then zeroed DM
  `0xC329`, a SPORT transfer control block, which survives on the chip. The kernel's reads of
  MSGR0-7 now return what was written, and the TCB survives.
- **Timer 4 and the handshake.** The 1 kHz tick is TM4 as the firmware programs it (1.0005 ms), no
  longer a fixed driver timer. The group-0x17 handshake is answered once per DSP frame after the
  boot, not at once. FLAG3 is high on every other frame. Pass 8 run in MAME now gives the unit's
  verdict, at 44,100.0 Hz.
- **SPORT DMA registers read live**: DMASTAT, every ring's index and count, and the transmit status
  read as on the unit, at the unit's phase. Not modelled: STCTL0's sticky start-up underflow bit, and
  the transfers themselves (the bridge still exchanges fixed ring slots).
