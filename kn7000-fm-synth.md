---
layout: page
title: "KN7FM: an FM Synthesizer on the Effects DSP"
permalink: /kn7000-fm-synth/
---

# KN7FM: a DX7-style FM synthesizer for the KN7000

KN7FM turns a stock KN7000 into a six-operator FM synthesizer in the manner of the Yamaha DX7, with an editor on
the instrument's own screen and panel. The sound is computed by a program of ours in the
[effects DSP]({{ site.baseurl }}/kn7000-effects-dsp/) (IC306, an ADSP-21065L). It is loaded through the
firmware's own host-port routines, as DSPTONE and Another World load theirs. KN7FM is a program of the
[program menu]({{ site.baseurl }}/kn7000-cnv-homebrew/) (folder `KN7FM\`), started from DISK MENU > STYLE CONVERT.

Source: `kn5000_homebrew/demos/kn7000_fm/` (its `README.md` has the details).

> **Status (2026-10-23): runs in MAME; not yet tried on an instrument.** In MAME (program 893, the loader floppy, the
> program menu) KN7FM:
> - finds the firmware, loads and hooks the DSP;
> - plays the keybed's notes, with the DSP's output equal to the model's sample for sample under both of MAME's
>   SHARC cores;
> - edits, loads and saves banks;
> - puts the firmware's effects back when it ends.
>
> How many voices the instrument's DSP has time for is not known: in MAME, five.

## What it does

- **Sound.** Up to eight voices (five to start: [Voices](#voices)) of six operators, the DX7's 32 algorithms, operator feedback, four-rate/four-level
  envelopes, keyboard level and rate scaling, velocity sensitivity, ratio and fixed frequencies with fine tuning and
  detune, the pitch envelope, the LFO (six waveforms, delay, pitch and amplitude modulation), oscillator key sync,
  transpose, the sustain pedal. Played from the keybed (and MIDI IN). The instrument's own sound for the keys is
  muted with expression 0 on MIDI channels 1-3, as Another World does, and comes back when KN7FM ends.
- **Patches.** DX7 voices: a 32-voice bulk dump (`BANKn.SYX`, 4,104 bytes) in the program's folder is read at the
  start (`BANK0.SYX`) and on LOAD, and written on SAVE. A bank of 16 voices of our own is built in.
- **Editing on the screen.** The LCD shows the algorithm as a diagram, the selected operator's envelope (or the
  pitch envelope) as a graph, and 16 parameter columns. The KN7000 has a pair of UP/DOWN buttons under each of the
  16 columns (the part MUTE buttons), and each pair changes its column's value. The side buttons pick the page:
  OP1-OP6, VOICE, and BANK (file, LOAD, SAVE, name). PAGE UP/DOWN step through the bank. Every change reaches the DSP
  at once.

## The engine

The reference model, `tools/fm_model.py`, defines every number the DSP computes. It follows msfa (Raph Levien's
engine, Google, Apache License 2.0, as Dexed carries it), fitted to the DSP:

| part       | how                                                                                                          |
|------------|--------------------------------------------------------------------------------------------------------------|
| operator   | a 24-bit phase, a 256-point sine with linear interpolation, times a gain                                     |
| gain       | moves linearly over 64 frames between control values (msfa's own interpolation over its 64-sample blocks)    |
| control    | one thing of one voice per frame: each operator's envelope, gain and frequency every 64 frames, msfa's rate  |
| exp2       | a cubic for 2^f, then SCALB/FIX, in float: no room for tables (1.4e-4 relative error)                        |
| algorithms | msfa's encoding: two buses, the output, self-feedback; the DSP runs code generated for the patch's algorithm |
| carriers   | scaled 1/32 of msfa's, so that 8 voices of 6 carriers sum without overflow; one at full level is -18 dBFS    |

Checked against msfa built from source (`tests/msfa_ref/`). For 32 random voices, one per algorithm, C4 at
velocity 100: level median 0.00 dB (worst -0.52 dB), envelope error median 0.13 dB (worst 0.97 dB). Steady-state
spectra, peaks within 40 dB, differ by a median of 0.1-1.2 dB for 31 algorithms. The 32nd, algorithm 5 at feedback
7, is chaotic and differs by 4.5 dB.

## The DSP program

`tools/fm_dsp.py` generates it, and every word is checked against MAME's SHARC disassembler. It is an effect unit
of the firmware's resident kernel, CALLed from the slots of unit 0 (REVERB) and unit 9 (CHORUS), as Another
World's mixer is. Its rules are the ones DSPTONE and Another World established:
- only I5 and I7, saved and put back;
- no M registers;
- the kernel's own effect epilogue;
- nothing that may overflow (the kernel sets ALUSAT, MAME's recompiler wraps);
- only instructions both MAME SHARC cores implement.

That last rule rules out a single-function fractional multiply, and ASHIFT and FDEP by a register: neither core
has them.

| memory                             | what                                                                                          |
|------------------------------------|-----------------------------------------------------------------------------------------------|
| PM 0x8102-0x82FF, 0x8340-0x83FF    | the resident program: commands, the control step, the LFO, exp2 (535 words)                   |
| PM 0x8E00-0x8FFF                   | the algorithm's kernel, two buffers: the host writes one, then points a trampoline at it      |
| DM 0x9D00-0x9EFF                   | 8 voices x 64 words: phases, increments, gains, envelope state, pitch                         |
| DM 0x9B20-0x9C3F, 0x9C60-0x9CFF    | the sine table, the variables, the patch's 70 words                                           |
| DM 0x9F00-0x9F75                   | msfa's "static" table, the key-on staging block                                               |

A kernel runs about 14 cycles per operator. The commands are MSGR6: key-on bits 0-7 (the voice's words from the
staging block), key-off bits 8-15.

`tools/fm_sim.py` runs the generated words in a simulator of the instructions they use. The simulator follows the
semantics of MAME's cores, and stops at any overflow or any access outside the program's memory. It compares
every sample and every voice word with the model, frame by frame, with notes starting, ending and stealing voices.

## The main CPU's program

The MN10300 program (`src/`) is an application of KN7LOAD.CNV:

- **The firmware search** is Another World's `fwfind.s`: the panel, the clock, the loader's file routines, the
  task services, the MIDI rings and the DSP's host-port routines, found by their code. It works on programs 893,
  935, 941 and 942.
- **The DSP's load and hook** are Another World's `dsp.s` (DSPTONE's): checked, uploaded, read back, hooked, and
  put back on every way out.
- **The notes:** a task yields every millisecond and reads the keybed's notes from the MIDI OUT 1 ring (and MIDI
  IN's), from a read pointer of its own. It computes msfa's key-on words in integers on msfa's tables, so they are
  exactly the model's, and gives them to a voice.
- **The editor** draws a piece at a time between note polls.

## Checked in MAME

| what                             | result                                                                                                                                              |
|----------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| the main CPU's words for the DSP | the bank, every patch word and every key-on word equal the model's (`tests/mame/check_words.py`)                                                    |
| the DSP's output                 | one C4, 2 s, every DSP frame recorded with a write tap: all 88,200 samples equal the model's under the recompiler, all 35,217 under the interpreter |
| the editor                       | an envelope rate, the algorithm (its kernel swapped into the other buffer), the volume: each reaches the DSP                                        |
| LOAD and SAVE                    | `BANK1.SYX` loaded; `BANK2.SYX`, read back off the card image, equals it byte for byte                                                              |
| the end                          | EXIT held 1.5 s: both CALL slots back as the firmware had them, read back; MSGR4-MSGR7 zero                                                         |

In MAME the keybed's own sound is still heard under KN7FM's: the expression it sends to mute it is not emulated
(Another World records the same).

## Voices

The kernel's other eight units run in the same 44.1 kHz frame. In MAME, which counts one cycle per instruction, the
DSP keeps every frame with five KN7FM voices of the E.PIANO and drops to 30,731 frames a second with six. KN7FM
therefore takes three measures:
- it plays five voices to start;
- the BANK page's POLY column sets 1-8;
- every second it reads the DSP's frame counter, and below 43,500 frames a second it plays a voice less, with a
  message.

On the chip a frame probably costs more than MAME counts: taken branches, SDRAM wait states. Fewer voices may fit
there.

Two findings about MAME came out of this:
- The KN7000 driver writes a host-port IOP register at each 16-bit half (kn7000_mame
  `notes/dsp-host-iop-write-halves.md`). A command in MSGR6's low half was taken twice, so KN7FM's commands are in
  the high half.
- Under `-nodrc` the DSP runs about 17,800 frames a second with any unit, DSPTONE's too. That is the interpreter's
  doing, not the units'.
