---
layout: page
title: "DSP Sample Playback — Research Plan"
permalink: /kn5000-dsp-sample-playback-research/
---

# Playing our own samples on the KN5000's DSPs — a research plan

On the KN7000, Another World plays the game's own samples: an eight-voice mixer of ours runs in the
effects DSP, the samples in the DSP's SDRAM ([KN7000 converter page]({{ site.baseurl }}/kn7000-cnv-homebrew/#sound)).
The KN5000 port plays its sound on the instrument's voices instead
([KN5000 converter page]({{ site.baseurl }}/kn5000-cnv-homebrew/#sound)), and in MAME, with three of
the four wave ROMs undumped, few voices sound. A mixer of ours on the KN5000's effects DSP would
play the game's own sounds on any KN5000 and in MAME alike.

**Status (2026-10-23, second pass): a four-channel mixer of ours runs on IC311 in MAME, and plays
Another World's own sound effects and music** ([results](#results-second-pass-a-mixer-fed-by-the-sub-cpu)).
It takes a route the plan's first pass held in reserve: the sub CPU steps the four channels over the
samples in its own DRAM and writes their current values into IC311 4000 times a second; the DSP
program only multiplies and sums. It has not run on a real KN5000. What runs is the MAME core's
*model* of the chip, and several of the words it relies on are that model's readings, not decoded
facts. The delay-memory sample player the plan was built around (questions Q1-Q4) is still open.

## What the KN7000 had that the KN5000 does not, yet

| a mixer needs                   | KN7000 (ADSP-21065L)                                     | KN5000 (IC311, uPD6383GF), as known today                                                                                                   |
|---------------------------------|----------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|
| an instruction set we can write | documented; an assembler of ours                         | about 81 % of the distinct microwords decoded ([decode status]({{ site.baseurl }}/upd6383-decode-status/)); no assembler                    |
| memory for the samples          | 1M words of SDRAM the host writes                        | 256K x 16 delay DRAM that only the DSP's own write words reach; the host writes coefficients and registers, five bytes a value              |
| reading at a computed position  | any address                                              | a delay address is a descriptor plus the frame counter, **plus a modulation offset** on CHORUS-type words (below): range and precision open |
| getting a program in            | the firmware's own host-port routines, from the main CPU | only the sub CPU writes the DSP; the converter runs on the main CPU                                                                         |
| knowing what the DSP did        | host reads of DSP memory                                 | none: the host port is write-only, the condition flags are strapped on this board                                                           |
| hearing it                      | its unit slots' returns, measured on the unit            | IC311 is a send/return insert: its wet return goes back into IC303, which mixes it; which return is heard when is not measured              |
| developing it in MAME           | the SHARC core                                           | a draft core, not in the default build, and its return is not mixed                                                                         |

## Why there is hope

- **The chip reads its delay memory at a moving, computed position.** CHORUS is decoded as an
  LFO-modulated delay: a phase accumulator (`phase += increment`, wrapped at 2²³−1) drives a waveform
  lookup whose output sweeps the read tap of a delay line, through the step the decode calls *apply
  modulation offset* (`lo12 = 0x44C`). Captured live, CHORUS's phase cell ramps +114 a frame, and the
  LFO-SPEED knob moves the step ([Effects DSP]({{ site.baseurl }}/effects-dsp/#modulation--a-quadrature-lfo-swept-delay-strong-by-composition)).
  A sample player is that same machine with a slow ramp in place of the LFO: a position accumulator
  stepping by the pitch, reading the delay memory where the sample is.
- **The chip keeps state across frames and runs a fixed budget**: 567 cycles a frame at 25 MHz
  against 384 instruction words, straight-line. Four voices of accumulate, read, scale and sum fit
  that budget easily; the KN7000 mixer spends about 40 instructions on a sounding voice.
- **A delivery path exists in principle.** The sub CPU's effect programs are bytecode streams in its
  DRAM, in the program image the main CPU downloads at power-on
  ([DSP Effect Data Zone]({{ site.baseurl }}/dsp-effect-data-zone/),
  [DSP Bytecode Interpreter]({{ site.baseurl }}/dsp-bytecode-interpreter/)). The main CPU writes the
  sub CPU's DRAM with E1 transfers, and selects an algorithm with command `0x2D`. Replacing one
  algorithm's stream and selecting it would have the sub CPU's own, tested routines upload our
  program, much as the KN7000 port used the firmware's host-port routines.
- **The output is audible on the real instrument**: every DSP effect is heard, and IC311's returns
  are mixed by IC303.

## The open questions, and what settles each

| #   | question                                                                                                                                                                       | how to settle it                                                                                                                                                                                                      | what it decides                                         |
|-----|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------|
| Q1  | **The modulation offset's range and precision.** Does the `0x44C` step add an offset as wide as the delay memory, or a bounded one? Integer, or fractional with interpolation? | trace CHORUS, FLANGER and the delays live in the emulator's LLE (`dsp/hle/lle_trace_diff.py`), with the HLE as oracle; census every `0x44C` word in both products' corpora; compare the sweep depths the programs use | whether a voice can play a sample at an arbitrary pitch |
| Q2  | **Writing at a known place.** Can a write word take the modulated address, or only descriptor + frame counter?                                                                 | the same census for write words; if only the frame counter, check Q3                                                                                                                                                  | how samples get into the delay memory                   |
| Q3  | **A frame counter of our own.** Can a program keep a cell that steps by one each frame and use it to turn frame-relative addresses into fixed ones?                            | follows from Q1 (a phase accumulator with step 1)                                                                                                                                                                     | loading without readback                                |
| Q4  | **The width of the delay address** (`mod 2^N`, N open: the firmware never uses more than 16 bits; 17 address pins)                                                             | a program that writes past 64K words and reads back through the audio path, on the unit                                                                                                                               | 128K or 256K words for samples                          |
| Q5  | **Feeding samples in.** How fast can the sub CPU write coefficient or register cells, and can the DSP copy one into the delay memory each frame?                               | time the firmware's own coefficient uploads (bytecode interpreter) in MAME; design a loader word sequence from decoded steps                                                                                          | how long a part's sounds take to load                   |
| Q6  | **Delivery.** Does the running sub-CPU program accept E1 transfers into its DRAM, and does selecting a replaced algorithm with `0x2D` upload it unchanged?                     | in MAME: replace the NO OPERATION program's stream with a known variant and compare what the core receives with what was written                                                                                      | whether we need our own sub-CPU code                    |
| Q7  | **Which return is heard.** IC311's outputs DO1/DO2 return into IC303 (`SDIA`/`SDIB`); which is mixed always, which only with an effect on                                      | on the unit, a program that outputs a known tone on one return at a time (as the KN7000's DSPTONE did)                                                                                                                | where the mixer's output goes                           |
| Q8  | **The bank's size.** The game's 93 sounds are 684,980 8-bit samples; one word per sample does not fit 256K words, two need unpacking in the DSP                                | the decode of shifts and masks; else only the sounds of the part being played                                                                                                                                         | load per part, or once                                  |
| Q9  | **MAME.** The IC311 core in a build where its return is mixed                                                                                                                  | behind the existing `KN5000_ENABLE_DSP1` switch; confirm a firmware effect against a recording from the unit before trusting our own program on it                                                                    | whether development can happen in the emulator          |
| Q10 | **IC310 (MN19413) instead.** The whole main mix passes through it, and it has its own 1-Mbit DRAM                                                                              | its instruction set is undecoded and it is not emulated: a project of its own, of the size IC311's has been                                                                                                           | a second route if IC311's fails                         |

## Results so far

**Step 1, first pass (2026-10-23).**

- **Q1, partly answered from the ROM, positive.** The decode's register (technics-roms-disasm
  `dsp/analysis/SPECULATIVE-APPLIED-REGISTER.md` §152) already shows the modulation offset carries a
  **sample count**: ENHANCER's DELAY L of 350 ms reaches its word as 15,435 = 350 x 44,100 / 1,000.
  And the word's class selects **interpolation**: class 3 keeps the fraction and reads two adjacent
  words, class 2 truncates. So a read at a fractional, computed position is something the chip does.
  Still open: the offset's full width, and its sign handling past what the effects use.
- **Q2, negative in the corpus.** Of the 99 delay reads in the 38 programs, 35 follow an
  apply-modulation-offset word within three words; **none of the 101 delay writes does**
  (`dsp/tools/mod_write_census.py`). Every shipped program writes its delay memory at descriptor +
  frame counter only. Whether a write *can* take the offset is untested; nothing shipped shows it.
- **A blocker the plan had not listed: the output stage.** The word that hands a unit's result to
  DO1 (output stage `w73`, `E30.C.00.404`) and the DO write itself are undecoded
  (`dsp/analysis/k5-output-stage.md` §3.2), and in MAME's core DO1 and DO2 have been **exactly zero
  for every program ever run** (1.2 M frames, "§54 VERDICT: SILENT"). Until that is decoded, no
  program on IC311, the firmware's or ours, is heard in MAME (Q9), and on the instrument a program of
  ours would have to hand its result to the firmware's output stage the way effect bodies do, which is
  also undecoded. **This now comes first**: it is the decode project's own open problem, and Q9
  depends on it.

A design that avoids writing samples into the delay memory (Q2) stays possible: the sub CPU keeps the
sample bank in its own DRAM, steps each channel, and writes the four current samples into DSP
registers at a fixed rate; the DSP program multiplies them by the four volumes and sums them, using
only the multiply-accumulate words the decode has measured. It still needs the output stage.

## Results, second pass: a mixer fed by the sub CPU

That design is now built, in MAME's IC311 build (`KN5000_ENABLE_DSP1=1`), as the `DSND=1` build of
technics-anotherworld `kn5000cnv/` (its README, "A DSP mixer of ours in IC311", has every number below
with the probe that made it).

| piece                          | what it does                                                                                                                                                                                                     |
|--------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| the mixer (`tools/dspmix.py`)  | 92 I-RAM words: the per-unit CALL, four multiply-accumulates (volume x sample), the return, the output stage's presentation word, the firmware's own frame terminator                                            |
| the streamer (`src/awsub.asm`) | in the sub CPU's DRAM; hooked onto the sub program's audio tick (INTT1) to load the mixer and start timer 4, then on each timer 4 tick (4000 Hz) steps four channels and writes samples and volumes              |
| AW.CNV (`src/cnv_dspsnd.asm`)  | puts the streamer in with E1 transfers and rewrites two of the sub program's RAM trampolines; per part, decodes its sounds (IMA ADPCM) and sends them; PLAY_SOUND and the music module's rows drive the channels |

**What the core's model required of the program**, each found on the test program and measured
(kn7000_mame `notes/kn5000-dsp-mixer/README.md`):

- No decoded word loads the D-RAM pointer; only the **per-unit CALL** sets it (to `0x05` for unit 0).
  A program whose walk does not net to zero drifts across frames.
- The return from a body lands **two words** after the CALL.
- A multiply-accumulate whose accumulator step is HOLD **skips the multiply**.
- The presentation word scales the accumulator by a **level in D-RAM `0x06`** (`0x86` for unit 1),
  so that cell holds 0x7FFFFF and no sample.
- The input stage writes the tone generator's mix at the pointer's frame-start value + 2 and + 5.
- Coefficients scale as **Q1.22** (`0x400000` is 1.0).
- The presentation words are not decoded: the core discards every frame that holds them unless
  `UPD6383_PRESENT_ASIS=1` lets them present the accumulator through the level.

**Measured in MAME:**

| measurement                                                   | result                                                                                                                                                           |
|---------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| test program, four sines of 220-660 Hz in D-RAM               | the speakers carry the four tones; everything else 35 dB below (DO1 itself: 50 dB)                                                                               |
| the streamer's test sine (62.5 Hz) through E1, sub CPU, IC311 | heard from the converter's start; timer 4 ticks 4000 times a second                                                                                              |
| the game's intro                                              | its own sound effects and music on the four channels, nothing clipped                                                                                            |
| loading a part's sounds (the intro: 148,508 bytes of samples) | 7.9 s: one open of `AWSND.BIN`, one read per run of sounds that follow each other in it (an open costs the firmware about 1.5 s); the bank checked byte for byte |
| leaving the game                                              | IC311's I-RAM and C-RAM identical to before the game                                                                                                             |

**An emulator fault it found**: IC311 runs inside the tone generator's sound-stream update, so a whole
batch of DSP frames saw only the D-RAM the sub CPU had left at the end of the batch: samples written at
4 kHz came out updated about 90 times a second. The driver now brings the stream up to date before each
host byte (kn7000_mame `38ee146`).

**Leaving restores IC311 through the sub program's own machinery**: its kernel and epilogue uploaded
from its own copies, then a full rewrite of all five effect slots, set off by a `0x2D` message queued in
its own DSP command ring.

**Where the questions stand:**

| #   | now                                                                                                                                                                                                          |
|-----|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Q1  | as in the first pass; not needed by this design                                                                                                                                                              |
| Q2  | as in the first pass; side-stepped: no sample enters the delay memory                                                                                                                                        |
| Q5  | the sub CPU writes 33 bytes a tick (four samples, the output level, changed volumes): at 4000 ticks a second that takes 55 % of it in MAME (87 % with the firmware's byte writer, which could not pass 4709) |
| Q6  | the running sub program accepts E1 transfers into its DRAM, and its RAM interrupt trampolines can be pointed at code of ours; delivery needs no replaced algorithm stream                                    |
| Q7  | open (the unit)                                                                                                                                                                                              |
| Q9  | answered for development: the IC311 build mixes DO1 and DO2, and a program of ours is heard; the firmware's own effects still are not                                                                        |

**Limits.** Four thousand samples a second leaves 2 kHz of bandwidth, so the sounds are dull. The
CALL and its rebase, the return address and the output level are the core's readings of the shipped
kernel, and the real chip may differ in any of them. The streamer's addresses (trampoline targets,
the DSP command ring, the slot buffers, the kernel's copies) are checked for sub programs v1.40, v1.41
and v1.42 only.

## The order

Steps 0, 2 and 3 are done in MAME for the sub-CPU-fed design (above), with the output stage taken
on the core's reading. Steps 1 and 4 belong to the delay-memory player, which stays open.

0. **The output stage** (above): how a body hands its result to DO1/DO2. Without it nothing is heard
   in MAME, and a program of ours cannot be checked anywhere but on the unit.
1. **Desk work, in the emulator and the ROM corpora (Q1, Q2, Q3, Q8).** No hardware. If the
   modulation offset is narrow and integer-only, and writes are frame-relative only, a mixer of
   arbitrary pitch is out of reach on IC311, and the route is Q10 or nothing; record that here.
2. **Delivery in MAME (Q6, Q5).** Replace the NO OPERATION algorithm's program with a variant and
   see it reach the chip unchanged, then time a coefficient stream.
3. **A tone of our own (Q9, then Q7 and Q4 on the unit).** A KN5000 DSPTONE: a phase accumulator
   reading a waveform table, its step from a coefficient the converter writes. In MAME first, then on
   the instrument when it is back, one return at a time.
4. **One voice from the delay memory**: load a sample through the loader words, play it at two
   pitches.
5. **The mixer**: four voices for PLAY_SOUND, four for the music, as the KN7000's; a command
   protocol through coefficient cells; the bank per part or once. The instrument-voice sound stays as
   the fallback, as the KN7000's tone-generator mode did.

Each step's result goes on this page, and in the decode's own records
([uPD6383 decode status]({{ site.baseurl }}/upd6383-decode-status/)).

## Tools to build on

- The decode's own: the HLE models and `lle_trace_diff.py`, the two-sided gate `pair_gate.sh`, the
  program catalogue and flowcharts ([Effects-DSP Flowcharts]({{ site.baseurl }}/effects-dsp/flowcharts/)).
- The KN7000's mixer (technics-anotherworld `kn7000/tools/dsp_mixer.py`) as the design to follow.
- The KN5000 converter's sound path: records to the sub CPU, a test build that plays a note list
  before the game, and a level meter for MAME recordings (technics-anotherworld `kn5000cnv/`).
