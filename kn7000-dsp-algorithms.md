---
layout: page
title: "KN7000 Effects DSP: The Complete Algorithm Catalog"
permalink: /kn7000-dsp-algorithms/
---

# KN7000 Effects DSP: The Complete Algorithm Catalog

The KN7000's effects processor — IC306, an Analog Devices **ADSP-21065L**
"SHARC" — has no boot ROM: every program it ever runs is embedded in the main
MN10300 firmware as a pool of **80 download records** (CPU
`0x486BCEC4..0x486CE68D`, about 71.6 KB) and streamed into the chip at boot.
[The Effects DSP page]({{ site.baseurl }}/kn7000-effects-dsp/) explains that
host-boot mechanism and how the pool was extracted and disassembled.

This page records the end state of the reverse-engineering pass over that
pool: **every record is now fully documented** — the resident kernel, the four
boot-time SDRAM probes, all **72 effect microprograms**, and the three
data-only records. Every program-memory instruction of every record is
disassembled and accounted for; every delay length, filter coefficient, LFO
rate and gain quoted below is read off the listings. The GUI names are not
guesses either: the firmware's own **preset-descriptor table** (600 ROM
descriptors) and its 24-byte **group table** were decoded, closing the chain
GUI name → effect type → pool record as ROM fact for the whole inventory.

The result is a complete picture of a 2002 commercial effects engine — from
its 4.6 KB operating system down to the pole placement of individual filter
sections.

## The kernel in brief

One record (rec04, 4,597 bytes) is the **resident kernel** — a tiny
static-priority operating system that is downloaded once and never replaced.
Its architecture, in five facts:

- **The host protocol is the chip's own host interface.** The MN10300 reaches
  the DSP through two mapped ports — `0x98000000` (register-index latch) and
  `0x9C000000` (data) — and the "registers" it pokes are simply the
  ADSP-21065L's documented IOP registers: the boot probe reads `SYSCON`
  expecting its reset value, downloads are external-port DMA setups
  (`IIEP0`/`IMEP0`/`CEP0`, `DMAC0 = 0xA1` for 48-bit program words or `0x41`
  for data words) draining the `EPB0` FIFO, and the SDRAM self-tests report
  their verdicts through message register `MSGR3`. Nothing about the boot path
  is custom silicon — it is a textbook ADI host boot.
- **Ten call slots per sample frame.** The main loop waits for the 44.1 kHz
  IRQ0 tick, then walks ten `CALL` instructions — one per effect unit. In ROM
  they all target a null stub; when the firmware loads an effect into slot
  *n* it patches that `CALL`'s target word to `0x8400 + n*0x100` with a
  single program-memory poke. Each unit gets a fixed parameter block, state
  block, and delay-arena window, all advanced by cursor arithmetic hidden in
  the calls' delay slots.
- **Eight self-chaining SPORT DMA rings.** Audio enters and leaves over four
  serial lines in and four out (to and from the tone generator, which is the
  clock master). Each line's DMA transfer-control block points *at itself* —
  an infinite autobuffer moving 8 words per sample frame with zero software
  attention, which is why all the SPORT interrupt vectors are `RTI` stubs.
- **The FLAG3 half-rate strobe.** The loop polls the FLAG3 input pin once per
  frame and scrolls a third delay ring (I3, 18,000 words of SDRAM) only when
  it is high. The four mic-reverb programs (below) prove by construction that
  FLAG3 is a **fs/2 frame-parity strobe**: they split their algorithm across
  the two phases, turning I3 into a 22.05 kHz arena with **816 ms** of reach.
- **BUSLK hot-patching.** The IRQ0 interrupt handler locks the external bus
  (`MODE2` bit `BUSLK`) and the main loop releases it only after the
  delay-critical units have run. Host parameter writes therefore land in the
  frame tail, and because every effect re-reads its whole coefficient bank
  each frame, an update takes effect atomically at the next frame — race-free
  mid-note parameter changes with at most one sample frame of latency, with
  no mailbox and no DSP-side cooperation at all.

The full annotation — vector table, delay-arena grant table, the scrub stubs
that zero-fill a slot's delay memory between effects, the effect ABI — lives
in `kernel-architecture.md` in the disassembly repository (see
[Sources](#sources) below).

## Highlights of the catalog

Eight findings stand out from the pool. Each is a one-paragraph summary; the
family documents carry the full instruction-level annotation.

### The main reverb was filed under "Enhancer"

The instrument's principal reverb is the **rec51–56 family**: a mono-in /
stereo-out **Moorer-style reverberator with Dattorro-style input diffusion**
— filtered early-reflection taps, a series diffuser of four allpasses, one
*absorbing* allpass, and two long lowpass-damped feedback combs, closed by an
output tone filter and a short stereo-decorrelation delay. The six records
are essentially one program (four are byte-identical; two differ only in four
early-tap immediates) with per-preset coefficient banks. The surprise was
where the host keeps it: the effect types `0x10`–`0x1F`, which had been read
as the whitelist's "Enhancer" group, *are* this reverb engine. Meanwhile the
unit-9 types first labelled "Reverb" resolve to ensemble and flanger programs
with no tail-capable structure. A live capture of the firmware's effect
selections (2026-07-20) settled it: unit 0 is the REVERB unit and unit 9 the
CHORUS unit. Only the role labels first attached to the whitelist were wrong.

### The rotary speaker is a real Leslie simulation

The rec30 family (eight records plus the one-word variant rec16) is a full
**rotary-speaker simulator**, not a renamed tremolo: an input crossover
splits the signal into drum and horn bands, and two independent
"magic-circle" sine/cosine oscillators spin the virtual rotors — drum at
5.512 Hz (331 RPM), horn at 6.431 Hz (386 RPM), a ratio of **exactly 7:6**
with the horn faster, matching real Leslie practice. Speed changes glide
with a 93 ms time constant (rotor inertia), and the rotors drive
**Doppler-modulated delay taps** — two quadrature taps swinging ±29 samples
for the horn, one tap swinging ±40 samples for the drum — so the effect
produces true pitch modulation, not just amplitude wobble.

### The mic reverbs run at half sample rate

Records 58–61 (the microphone-channel reverbs Room / Karaoke / Stage / Cave)
are a third, entirely separate reverb architecture: a **series-allpass
Schroeder reverberator** — the textbook "colorless" cascade of six allpass
sections, no combs, no global feedback — run at **22.05 kHz**. The program
is phase-split across the kernel's FLAG3 parity strobe: half the tank
executes on even frames, half on odd, over the u7-exclusive I3 ring, doubling
both the delay reach and the effective memory budget. Audio-rate lowpass
biquads bracket the half-rate core as decimation and interpolation filters.
Data alone spans the family from a 2.3 s room to a 3.7 s cave — and the
Karaoke preset zeroes four allpass gains, degenerating the tank into a single
363 ms regenerating slap echo: the classic karaoke-machine mic sound from
the same program.

### The brass simulators are physical modeling

Records 67–69 ("Brass Simulator 1–3") are the only physical-modeling cluster
in the pool: all three integrate a two-state **nonlinear "lip" oscillator
ODE** per sample (with cubic and quadratic stiffness terms) and condition its
output through a cubic soft-clipper. rec68 is the naked lip — a constant
brassy edge; rec67 adds a **pitch tracker** and re-excites the lip with
period-locked grains of the input; and rec69 couples the lip to a
**512-sample bore delay line in a Karplus-Strong-style negative-feedback
loop** — an odd-mode comb, i.e. a closed-tube resonator with modes at odd
multiples of ≈43 Hz: lip drives bore, bore pressure re-excites lip. A
genuine, if stylized, coupled lip–bore waveguide inside a 2002 home
keyboard.

### Four wahs, one of which does not listen

The pool holds four distinct wah programs: rec28 **Auto Wah**
(envelope-driven, sweeping *up* from a parked 447 Hz resonance past 6 kHz as
the player digs in), rec47 **Reverse Wah** (envelope-driven, sweeping
*down* — playing harder closes the filter), rec48 **LFO Wah** (LFO-swept
bandpass, Q = 8), and rec29 **Pedal Wah** — the curiosity of the set. rec29
still computes the audio envelope of its fork-parent rec28 **and never uses
it**: the detector is dead code, a fossil. What actually sweeps the filter
is a **host-written control cell** — the expression pedal, relayed by the
CPU — smoothed by the same attack/release slew, repurposed as click-free
pedal glide. (rec74's touch-wah front end and rec46's 10-pole LFO filter
round out the swept-filter census.)

### The EQs are mirror-flat by construction

Both equalizers — rec23 (the 8-preset Parametric EQ) and rec34 (the unit-8
output 5-band EQ, a 13-word wrapper around kernel helper `0x831B`) — share a
remarkable template: every section's numerator is the **bit-exact mirror**
of its denominator (identical mantissas, flipped sign bits), so each of the
five cascaded sections computes exactly unity and the flat preset passes
signal through untouched. But the denominators are not trivial — the poles
are **pre-placed at real, octave-spaced band centers** (rec23: about 124 /
496 / 992 / 1985 Hz; rec34: about 124 / 484 / 969 / 1940 Hz; each with a high
band). At run time the host ignores rec34's template and computes the output
EQ's bank from the screen's FC/GAIN/Q, with flat poles at 125 / 500 / 1k / 2k /
8k Hz. A preset "boosts a band" by moving that
section's zeros off its poles; an untouched band stays *exactly* flat rather
than approximately flat. (Relatedly, the GUI "Enhancer" (rec08) turned out
to be fully linear — a phase rotator with low/high emphasis and a Haas
offset — while the pool's real **harmonic exciter** is rec20: a waveshaper
whose products are selected by a unity-peak 3.56 kHz bandpass and added to
dry.)

### Three LFO idioms

Every modulated effect in the pool uses one of exactly three oscillator
constructions. (1) The **table-lookup LFO**: a 32-bit phase accumulator
(one cycle = 2³¹ counts) indexing a 16-step waveform table with linear
interpolation — and the three data-only records (rec77–79) are alternate
sine/triangle/square tables the CPU can push into that window to reshape a
running effect's modulation without reloading its program. (2) The
**magic-circle sine** — the coupled-form recurrence `sin' = sin + ε·cos;
cos' = cos − ε·sin'` — which spins the Leslie rotors and the trio-chorus
shimmer. (3) The **overflow-reflect triangle**: `phase += inc; if overflow,
inc = −inc` — the accumulator ping-pongs between the arithmetic rails, its
signed increment flipping at each saturation. That third idiom is the
signature of the triangle-trio chorus engine (rec49/50).

### Saturation arithmetic is load-bearing

The kernel's only arithmetic-mode write (`BIT SET MODE1 0x3000` at PM
`0x8074`) enables **ALUSAT** — fixed-point ALU saturation — and the effects
are *designed against it*: the overflow-reflect triangle LFOs bounce off
saturated rails instead of wrapping, rec07's modulator sums (which can reach
±1.15) clip cleanly at ±1.0 to keep its tap swing bounded, and the gate
reverb's hold-gate debounce counts on saturating adds. An emulator that
wraps where the chip saturates turns every such LFO into a permanent
full-scale two-sample oscillation — exactly the reverb-rail bug found and
fixed in the project's fork of MAME's SHARC recompiler (the kn7000_mame
overlay and the branch `technics-kn7000-dsp`, not yet submitted upstream; see
the [Effects DSP page]({{ site.baseurl }}/kn7000-effects-dsp/), fix
catalogue). ALUSAT is not a detail; it is part of the algorithms.

## The full inventory

The complete pool, record by record. GUI names come from the firmware's own
descriptor and group tables (ROM fact); "engine" is the algorithm class read
from the disassembly.

| Record(s) | GUI name / role | Engine | One-line description |
|---|---|---|---|
| 00–03 | boot probes | SDRAM self-test | Four board-variant march tests of the DSP's external SDRAM, tried in turn at boot; verdicts via `MSGR3` |
| 04 | resident kernel | kernel | 10-slot per-sample dispatcher, 8 self-chaining SPORT DMA rings, 3 scrolling delay arenas, BUSLK update window |
| 05 | effect off | mute stub | Two zero writes — silences a send slot |
| 06 | Chorus / Celeste / GM Chorus 1/3 | ensemble chorus | Quadrature two-voice ensemble chorus |
| 07 | Modulated Chorus / Mod. Celeste / GM Chorus 2/4 | ensemble chorus | Dual-rate ensemble chorus (its LFO sums rely on ALUSAT) |
| 08 | Enhancer 1–6 | phase rotator | Phase rotator + low/high emphasis + Haas offset — fully linear, no exciter nonlinearity |
| 09 | Flanger | flanger | Stereo resonant flanger, 0.70 floating-point regeneration |
| 10 | Phaser | phaser | True phaser: 5+5 swept allpasses, quadrature LFOs |
| 11 | Ensemble | chorus | Hexaphase three-voice chorus, taps 67.5° apart |
| 12 | Medium / Short / Long Gate | gate reverb | Damped allpass-ring tank + hold-gate with saturation-dependent debounce |
| 13 | Dual Delay | echo | Dual-mono damped echo, 181 / 227 ms |
| 14 | Multi Tap Delay | echo | Four-tap panning echo |
| 15 | Cross Delay | echo | Cross-feedback ping-pong echo |
| 16 | Rock Rotary (Standard trio) | rotary speaker | The rec30 Leslie engine as a one-word variant |
| 17 | Distortion (Normal/Mild/Hard/H.C.) | waveshaper | AGC waveshaper, transfer curve A, no tone filter |
| 18 | Overdrive (Normal/Mild/Hard/H.C.) | waveshaper | AGC waveshaper, curve B + smoother + lowpass |
| 19 | Fuzz | waveshaper | AGC waveshaper, rail curve C, quiet-gate |
| 20 | Exciter 1–3 | harmonic exciter | LUT waveshaper → unity-peak 3.56 kHz bandpass product selector → summed with dry |
| 21 | Compressor (Comp. 1–4) | dynamics | Closed-form reciprocal gain law, Newton-refined, curve-meets-clamp continuity |
| 22 | Slow Attacker 1–4 | dynamics | Two-target gain machine: 743 ms swell, 2.9 ms reset |
| 23 | Parametric EQ (8 presets) | EQ | Mirror-flat five-section cascade, octave-spaced pre-placed bands |
| 24 | Tremolo 1–8 | LFO amplitude | In-phase LFO amplitude modulation (rec26 plus one word) |
| 25 | Limiter 1–4 | dynamics | Same program as rec21 with the Limiter coefficient banks |
| 26 | Auto Pan 1–7 | LFO amplitude | Quadrature-LFO stereo panner |
| 27 | Vibrato 1–8 | modulated delay | Wet-only modulated delay — no dry path, mono |
| 28 | Auto Wah (Wah 1–5) | swept filter | Envelope-swept resonator, upward sweep |
| 29 | Pedal Wah (Wah 1–3) | swept filter | Host-cell-swept resonator; the onboard audio detector is dead code |
| 30, 35, 36, 41–45 | Rotary Speaker / Rock Rotary Twins | rotary speaker | Full Leslie: crossover, two gliding rotors at exactly 7:6, Doppler taps |
| 31 | Ring Mod. 1–4 | ring modulator | Bipolar quadrature AM with an audio-rate carrier |
| 32 | Mixup 1–4 | modulated delay | Burst vibrato: sin·sin product modulators |
| 33 | Spreader (group "Space") | stereo widener | Decorrelation micro-FIRs + 349 Hz bell + antiphase Haas echoes |
| 34 | output equalizer (unit 8) | EQ | Five-band wrapper around kernel helper `0x831B` |
| 37 | Distortion "Bright" | waveshaper | Curve-A LUT + AGC + presence biquad + Haas offset |
| 38–40 | Distortion / Overdrive "Fat" / "Bright" | waveshaper | Voicing deltas over rec37 / rec18 — same engines, new coefficients |
| 46 | LFO Filter | swept filter | 10-pole computed-bilinear lowpass sweep |
| 47 | Reverse Wah (Wah 1–8) | swept filter | Envelope-swept bilinear bandpass, downward sweep |
| 48 | LFO Wah | swept filter | LFO-swept bilinear bandpass, Q = 8 |
| 49 | Chorus 1–4 (CHORUS screen) | triangle-trio chorus | Three overflow-reflect triangle LFOs + a magic-circle sine |
| 50 | Trio Chorus | triangle-trio chorus | The same engine as a deeper insert build |
| 51–56 | REVERB screen (Room / Plate / Concert / Dark / Bright / Stage …) | Moorer/Dattorro reverb | Early-reflection taps + 4-allpass diffuser + absorbing allpass + two damped combs |
| 57 | Voice Changer 1/2 | granular pitch | Dual-saw granular detune with an exact equal-gain crossfade |
| 58–61 | mic reverbs Room / Karaoke / Stage / Cave (unit 7) | half-rate Schroeder reverb | Series-allpass tank at 22.05 kHz, phase-split across the FLAG3 strobe on the exclusive I3 ring |
| 62–65 | Distorted Amp (Loud/Normal/Soft 1–4) | waveshaper | Cubic soft-clip overdrive, four tone banks |
| 66 | Vocal Harmonizer | granular pitch | Three-voice reflected-ramp granular pitch shifter |
| 67–69 | Brass Simulator 1–3 | physical model | Nonlinear lip ODE; rec67 adds pitch-locked grains, rec69 a Karplus-Strong-style bore waveguide |
| 70–72 | Delay+Chorus / +Flanger / +Vibrato | delay combi | Floating-point echo front end into the rec06 / rec09 / rec27 back ends |
| 73 | Delay+Phaser | delay combi | Floating-point echo into a three-stage swept-allpass phaser |
| 74 | Autowah+Delay | delay combi | Touch wah front end + stereo echo |
| 75–76 | Comp+Dst+Delay / Comp+Ovd+Delay | delay combi | AGC compressor → float-LUT distortion curve A/B → echo |
| 77–79 | LFO waveform tables | data | Sine / triangle / square tables pushed into the running LFO window |

## What remains provisional

Everything structural above is ROM fact. What static analysis cannot pin is
**host-runtime behavior**: the live values the CPU writes into each
preset's coefficient bank at select time (the templates are known, the
per-preset values are not), the handful of host-fed control cells (rec29's
pedal cell, rec75/76's `PM 0x9801`, rec14's regeneration), FLAG3's
physical driver on the board (its *function* is pinned by
design necessity), and a few perceptual readings flagged as such.

Two live experiments, run on 2026-07-20, closed the unit-role questions. The
first captured the firmware's effect selector (`DspEffectSelect`,
`0x48405815`) and the host downloads while GUI effects were switched. It gives
the unit map — 0 REVERB, 1 MULTI, 2–6 the per-part insert pool, 7 MIC REVERB,
8 EQUALIZER, 9 CHORUS — and shows that the three TG send buses land on TDM
input pairs of units 0, 1 and 9. The second, a data-memory dump of the running
EQ, shows that its flat bank is an exact mirror bank, which the host computes
from the EQUALIZER screen's FC/GAIN/Q instead of taking it from rec34's ROM
template.

## Cross-model note

The KN6000 and KN6500 carry the same ADSP-21065L and a byte-identical record
pool to one another; against the KN7000 all 80 records' data (coefficient
banks and tables) match byte-for-byte, while the program code differs in 77 of
them, the kernel included (an older build) — so this catalog's preset
voicings carry over to those models nearly wholesale. See the
[KN6000/KN6500 notes]({{ site.baseurl }}/kn6000-hardware/).

## Sources

The instruction-level annotations live in the `dsp/` tree of the
`kn7000/` folder of the `technics-roms-disasm` repository (see
[Firmware Images]({{ site.baseurl }}/kn7000-firmware/)): the kernel in
`kernel-architecture.md`, and the effect families in `reverb-algorithm.md`,
`chorus-family-algorithms.md`, `insert-effects-algorithms.md`,
`tremolo-rotary-family.md`, `phaser-enhancer-gate.md`,
`dynamics-eq-exciter.md`, `modulation-pitch-family.md` and
`final-batch-algorithms.md`, alongside the generated SHARC listings and
per-record symbol files. The emulation side — how these programs run today
under MAME — is on the
[Effects DSP page]({{ site.baseurl }}/kn7000-effects-dsp/).
