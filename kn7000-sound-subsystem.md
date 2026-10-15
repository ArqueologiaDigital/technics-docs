---
layout: page
title: KN7000 Sound Subsystem
permalink: /kn7000-sound-subsystem/
---

# KN7000 Sound Subsystem

The KN7000 is a **PCM sample-playback** instrument with **128-note polyphony**
and a full digital effects chain. This page describes the sound hardware as
drawn in the service manual and as driven by the firmware: two tone-generator
LSIs playing samples from four wave ROMs, a floating-point effects DSP, and the
DACs and analog stages that reach the speakers. The dedicated
[Effects DSP page]({{ site.baseurl }}/kn7000-effects-dsp/) covers the DSP's programs in depth.

Addresses are decoded from `kn7000_program.rom` (mapped at CPU `0x48400000`);
I/O registers live in the `0x98000000` sound bank. Chip identities are from the
service-manual parts list and block diagram; low-level behaviour is from
firmware disassembly.

## The signal chain

<pre class="mermaid">
flowchart LR
    CPU["MN103002A CPU<br/>(MN10300)"]
    subgraph TG["Tone generators"]
      MTG["IC201 MASTER TG<br/>C1BB00000709"]
      STG["IC205 SUB TG<br/>C1BB00000709"]
    end
    WA["Wave ROMs<br/>IC203 / IC204<br/>(master)"]
    WB["Wave ROMs<br/>IC207 / IC208<br/>(sub)"]
    DSP["IC306 effects DSP<br/>ADSP-21065L SHARC"]
    SD["IC307 / IC308<br/>DSP SDRAM (4 MB)"]
    DAC["IC311 main DAC"]
    ANA["Analog: I/V filters,<br/>FAJ board, 5-band EQ,<br/>amps, speakers"]

    CPU -->|"TGCS regs<br/>0x98040000"| MTG
    CPU -->|"TGCS2 regs<br/>0x98050000"| STG
    CPU -->|"host port<br/>0x98000000 / 0x9C000000"| DSP
    WA --- MTG
    WB --- STG
    STG -->|"SUB0-3 serial mix"| MTG
    MTG <-->|"sends out,<br/>effect returns back"| DSP
    SD --- DSP
    MTG -->|"serial: direct mix<br/>+ effect returns"| DAC
    DAC --> ANA
</pre>

Read left to right: the CPU writes note and parameter data to the two tone
generators; each TG fetches PCM samples from its own private pair of wave ROMs
and renders voices; the **sub** TG mixes its output into the **master** TG over
a four-wire serial link; the master TG sends serial audio to the effects DSP
(reverb / chorus / EQ / insert effects) and takes the DSP's returns back on four
serial lines; the master TG mixes its direct sound with those returns into the
main stereo DAC, and the analog board applies the final EQ and drives the
speakers.

Everything digital sits on the **MAIN P.C.B.** The audio sample world runs at
**44.1 kHz**, clocked from a 16.9344 MHz tone-generator crystal (= 384 × 44.1
kHz) and an 11.2896 MHz system clock (= 256 × 44.1 kHz).

## Tone generators (IC201, IC205)

Both tone generators are the same custom Panasonic part, **C1BB00000709**, a
64-voice PCM wavetable LSI. IC201 is the **master**; IC205 is the **sub**. Two
chips give the instrument's 128-note polyphony. Both also scan the key bed in
hardware (the `KS`/`KF`/`KB` matrix pins), which is why the firmware can read key
events from a tone-generator port in parallel with the MIDI input.

Each TG presents a small **register-indirect** interface on the CPU bus:

| Port            | Master (IC201)              | Sub (IC205)                 | Meaning                                                                                              |
|-----------------|-----------------------------|-----------------------------|------------------------------------------------------------------------------------------------------|
| register write  | `0x98040000` / `0x98040002` | `0x98050000` / `0x98050002` | address half then data half of a 32-bit register write                                               |
| key/voice event | `0x98040004`                | `0x98050004`                | read a key-bed event (low byte = key index, bit 7 = release; high byte = velocity; `0xFFFF` = empty) |
| wave readback   | `0x98040006/8/A`            | `0x98050006/8/A`            | page / offset / **raw sample data** window (used by the service ROM checksum test)                   |

A register access packs a 16-bit **address** and 16-bit **data** into the two
adjacent ports. At idle the firmware writes a cyclic `0xFC0x` "system refresh"
pattern; a note-on writes a per-voice sequence (pitch, velocity, key-on strobe,
pan, effect sends) very much like the documented
[KN5000 tone generator]({{ site.baseurl }}/tone-generator/), whose register map is the working
template for decoding the KN7000's.

## Wave ROMs (IC203, IC204, IC207, IC208)

The PCM samples live in **four custom mask ROMs**, `C3CBQD00000x`, **128 Mbit
each** (≈ 64 MB total). They are wired to the tone generators on **private
buses** and never appear on the CPU bus, so software cannot read them by an
ordinary load — except through the **wave-ROM readback window** (`+6/+8/+A`
above), which the factory WAVE ROM test uses to page through every bank and
checksum it. Each TG drives **two** wave ROMs over two independent 24-bit
address ports (`AWAX`/`AWAY` on the master, `BWAX`/`BWAY` on the sub) so it can
fetch a pair of samples per cycle for interpolation.

| ROM | attaches to | address port | part |
|---|---|---|---|
| IC203 | master (IC201) | AWAY | C3CBQD000002 |
| IC204 | master (IC201) | AWAX | C3CBQD000001 |
| IC207 | sub (IC205) | BWAY | C3CBQD000004 |
| IC208 | sub (IC205) | BWAX | C3CBQD000003 |

These four ROMs are **not** contained in the firmware-update disks, so they are
currently **undumped** — the largest gap for faithful sound. The rhythm data is
undumped too: IC18, or IC20 on earlier units; see the
[ROM Dumping Roadmap]({{ site.baseurl }}/rom-dumping-roadmap/).
Wave-ROM expansion boards (SY-EW01…04) plug into connectors on the same TG
buses.

## Effects DSP (IC306)

IC306 is an **Analog Devices ADSP-21065L** ("SHARC", part `S21065LKS240`), a
floating-point DSP running at ~60 MHz with two 16-Mbit SDRAMs (IC307/IC308) for
delay memory. It has **no boot ROM** — the CPU host-boots it over a parallel
port (index register `0x98000000`, data register `0x9C000000`) and streams in
the reverb, chorus, multi-effect and equalizer programs. Remarkably, **those
programs are embedded in the dumped firmware**, so the entire effects engine is
recoverable without the physical chip. The dedicated
[Effects DSP page]({{ site.baseurl }}/kn7000-effects-dsp/) documents the host protocol, the
runtime, and every effect algorithm.

## DACs, ADCs and the analog path

- **IC311** (`C0FBBK000025`, "D/A CONVERTER") — the main stereo DAC, fed serial
  audio from the master tone generator (its direct sound mixed with the DSP's
  effect returns); differential current outputs go to I/V converters and
  low-pass filters (M5218 op-amps), then to the FAJ analog board.
- **IC310** (PCM69BU) — a second stereo DAC on the SUB-OUT path.
- **IC309 / IC410** (PCM1800E) — stereo ADCs that digitise MIC/LINE inputs (for
  the DSP's mic effects) and re-digitise the final mix for the recorder.
- A **CPU-writable latch** (IC25, a 74HC174) programs the main DAC's mode pins
  and the speaker-mute/relay lines.

The **FAJ board** carries the jacks (mic, line, aux, sub-out, main-out,
headphones), a multi-band **"EQUALIZING"** op-amp bank, and the power stages
driving the built-in speakers (two 12 cm and two 6.5 cm for mid/high, one
14 cm for bass; user's manual p. 208).

### A separate, DSP-bypassing audio path

SD-Audio playback (via the SD sub-system's decoder IC402) and USB audio (via
IC406) are mixed into the analog output by transistor switches and **never touch
the tone generators or the effects DSP** — a completely independent path for
playing back recorded audio.

## How software drives the sound hardware

The whole sound block lives in the `0x98000000` region of the MN10300 memory
map:

| Range                               | Function                                                                                                 |
|-------------------------------------|----------------------------------------------------------------------------------------------------------|
| `0x98040000` / `0x98050000`         | master / sub tone-generator register ports                                                               |
| `0x98040004` / `0x98050004`         | key-bed / voice-event FIFOs                                                                              |
| `0x98040006/8/A` / `0x98050006/8/A` | wave-ROM readback windows                                                                                |
| `0x9805000E`                        | not a sound register: the SD card's SPI clock-rate latch, next to the SPI shift register at `0x9805000C` |
| `0x98060000`                        | bit-banged serial config to the DAC/codec                                                                |
| `0x98070000`                        | read-only sound-board status / strap word                                                                |
| `0x98000000` + `0x9C000000`         | effects-DSP host port (index + data)                                                                     |

The firmware's sound engine allocates voices, writes them to the tone
generators, and separately manages the DSP effect units. The user-facing screens
that expose all of this — sound select, the Digital Drawbar and organ editors,
Reverb & Effect, the Sound DSP editor, the 5-band Equalizer, the mixer — are
catalogued in the KN7000 firmware notes; each maps onto the register traffic
described above.

### From a key press to a voice — the firmware signal path

Tracing an actual note through the disassembly (and confirming each step live in
the MAME driver) shows a clear pipeline:

1. **Key scan → FIFO.** The sub tone generator scans the key matrix in hardware
   and posts each event into its voice-event FIFO. The CPU reads it at
   `0x98050004` as a 16-bit word — low byte = key index (0 = the bottom C2; bit 7
   set = key release), high byte = velocity (`0xFF` on a release), `0xFFFF` =
   empty.
2. **Key-bed service task.** A scheduled task (firmware address `0x48448015`)
   drains the FIFO, reading events until it sees `0xFFFF`, and gathers the
   note/velocity pairs.
3. **Note → pitch.** Each event is decoded by a helper (`0x4844812D`) that turns
   the key index (plus 36, giving the MIDI note) into the tone generator's
   internal pitch value using the instrument's tuning tables and a
   divide-by-twelve (one octave = 12 semitones), then records it in a per-key
   voice descriptor.
4. **Voice allocation → tone-generator registers.** The sound engine assigns the
   note to a free tone-generator channel and programs that channel through the
   **register-indirect primitives** in the self-loaded library ROM. Voices
   **0–63** are written to the **sub** TG (`0x98050000`), voices **64–127** to
   the **master** TG (`0x98040000`); each register write packs a channel number,
   a register index and 16 bits of data. Between notes the same primitives emit
   the cyclic `0xFC0x` refresh.

All four steps now run in emulation, and the emulator turns the firmware's voice
writes into sound (see below).

## Factory diagnostics as documentation

The service diagnostic mode (entered by holding **C#3 + D#3 + C#4** at power-on)
includes several sound tests that double as precise hardware descriptions:

- **WAVE ROM test** — checksums all banks of IC203/204/207/208 through the
  readback window (30 s for 64 MB); proves the window returns raw sample data.
- **SOUND SYSTEM test** — plays a full-amplitude **sine per key**, with the
  C keys exercising IC203&204 and the C# keys IC207&208, plus pan / octave /
  touch check modes. (The sine samples themselves live in the wave ROMs, so this
  test still needs them.)
- **Other device test** — reports `DSP: IC306` and `DSP RAM: IC307/IC308` OK/NG.

## Emulation status

**In the project's own MAME builds, the KN7000 boots to its main play screen and
sings, driven by its own firmware voice engine.** These are the kn7000_mame
overlay and two branches prepared for upstream, `technics-kn7000-tonegen` (the
tone-generator voice engine) and `technics-kn7000-dsp` (the effects DSP). Both
branches are queued and neither has been published or submitted yet. All three
flag the machine `MACHINE_NOT_WORKING | MACHINE_IMPERFECT_SOUND`. Upstream MAME
differs: the `kn7000` driver merged as
[mamedev/mame#16250](https://github.com/mamedev/mame/pull/16250) on 2026-10-07
runs the same firmware, but it is `MACHINE_NOT_WORKING | MACHINE_NO_SOUND`. It decodes the tone-generator
registers without producing sound, and it does not emulate the effects DSP.
Playing a note (PC key bed or MIDI in) travels through the firmware exactly as
on hardware — key-event FIFO → key-bed task → note-to-pitch → voice allocation —
and the firmware programs the tone-generator voice registers, which the emulator
renders to audio. Pitch, polyphony and note timing are the firmware's own; sound
is on by default and needs no switch.

Getting there turned on one missing bit. The firmware only programs voices when a
**tone-generator-present strap** (read at `0x98070000`, tested at firmware
`0x484d7713`) says the TGs exist; otherwise a library gate flag stays set and every
per-voice register write is suppressed — which is why early builds were silent even
though the key press reached the firmware. The emulator now reports both tone
generators present (the KN7000 has both), so the gate opens and the voice engine
drives the hardware from the moment the home screen appears.

With the tone generators driven, the instrument **plays on the home screen**: key
bed, chord finder, rhythm accompaniment and the built-in demo songs all sound. The
demo songs and the auto-accompaniment run off a modelled on-chip tempo timer — the
16-bit timer TM5 (mode `0x34001082`, reload `0x34001092`, count `0x340010A2`) whose
underflow raises INTC group 7 and fires the firmware's **96-PPQN sequencer tick ISR**
(`0x48447084`). Clocked at IOCLK ÷ 8 (16 MHz ÷ 8 = 2 MHz), its reload works out to
1,250,000 ÷ BPM timer counts per sequencer tick (1/96 beat), so the sequenced
parts run at the tempo the panel sets.

## How a note's pitch really works

> **Two builds differ here.** The voice-record read described below is what the
> kn7000_mame overlay does. The tone-generator branch prepared for upstream MAME
> (`technics-kn7000-tonegen`, 2026-09-24, not yet submitted) drops it, because a
> tone generator cannot read CPU RAM. It decodes pitch from the register alone
> against one fixed anchor (pitch18 `0x1C838` = MIDI 96). That anchor is still
> unsettled.

The obvious reading of the TG pitch register — an absolute pitch value — turned
out to be wrong, and the correction is worth recording. The 18-bit pitch field
(register class `0x2400`, with bit 16 carried in the class's low bit) is
**sample-zone-relative**: 0x400 per semitone, but anchored to whichever PCM
sample zone the voice selected, not to a fixed frequency. The firmware computes
it in its sound library (`pitch16 = ((note − zoneCenter) << 8) >> keyScaleExp +
0x4280` plus coarse/fine/multisample corrections, then `pitch18 =
((pitch16 + 0x1800) << 2)`; key-scale exponent 7 means "fixed pitch" — drums).
Every tone therefore sits at its own offset, and a placeholder synthesizer that
reads the register as absolute pitch plays every non-piano part transposed.

The emulator instead recovers the **musical** pitch from the firmware's own
voice bookkeeping: at note-on the sound library fills a per-voice record
(`0x500AF940 + slot·0xB4`) whose `notePitch16` field holds the intended pitch —
note, part transpose, master tune and stretch tuning included — in 1/256-semitone
units, before the first TG register write of the note. Reading it makes the key
bed, the demo songs and the **chord finder** all play at true pitch (the chord
finder's notes were always computed correctly from its chord tables; only its
part's empty tone descriptors made the register value garbage). Pitch rewrites
on a sounding voice are applied as relative bends, so vibrato, portamento and
pitch bend behave. A by-product of the same analysis: the key-bed FIFO carries a
**key index** (0 = the 61-key bed's bottom C2), not a MIDI note — the firmware
adds 36.

### Note-off and the amplitude envelope

Note-release turned out **not** to be the `0x0001 = 0xC000` voice mute the register
map first suggested — that write is only boot init and voice-steal. On a real key-up
the firmware ramps the note down by rewriting registers 0, 1, 4, 5, 8, 9 of the
note's **odd companion block** with a decay target and rates (`reg0` drops from full
scale to `0x9180`), and it aims at the companion block even when only the even block
is sounding. The emulator models this: a below-full-scale `reg0` rewrite on either
half releases every gated voice of the pair `{v & ~1, v | 1}` that has been held
longer than 20 ms (the guard skips the note-on's own programming). Each voice's held
level comes from its programmed amplitude envelope — the sustain level (SUS1) and
decay-rate (DCY2) registers the firmware writes at note-on — so a Concert Grand
decays while an organ or string patch sustains.

The full **7-stage** amplitude envelope is only partially modelled. A few sounds
(the plucked guitar/mallet family) send no key-up write at all and let the sample
ring its own multi-stage envelope; the placeholder holds those at their sustain
level instead — a known limitation, alongside a still-provisional chip rate curve.

One honest caveat remains above all: **placeholder timbre**. The four PCM wave ROMs
are still undumped, so in the branches prepared for upstream each voice plays a
stand-in **sine**, stored as a one-cycle sample so it goes through the same
sample-playback path. The overlay instead plays a labelled synthetic wave pack
built from KN5000 donor samples. Real timbre awaits the ROMs. The tone
descriptors in the dumped table ROM already map every voice to its wave sample
number, so real-sample playback is ready to slot in once the ROMs are dumped (the
firmware's readback window can extract them from a real unit).

The **effects DSP** is fully recovered — its programs are in the firmware — and
the emulator boots its ADSP-21065L kernel (running as low-level SHARC code, with
MAME's SHARC recompiler enabled) and routes the tone-generator audio through it.
Four effect units are driven and audible, each with its own return level — reverb,
chorus, the Sound DSP, and the multi-effect — and the reverb's on/off tail works: a
MODE1 `ALUSAT` saturation fix in the SHARC recompiler stopped the reverb's feedback
path from railing. See the [Effects DSP page]({{ site.baseurl }}/kn7000-effects-dsp/).
