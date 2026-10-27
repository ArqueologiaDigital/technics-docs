---
layout: page
title: "ProTracker on the KN7000"
permalink: /kn7000-protracker/
---

# ProTracker 2.3D on the KN7000

The Amiga's ProTracker 2.3D running on a stock KN7000:
- its main screen on the instrument's LCD;
- its replayer playing modules through the [effects DSP]({{ site.baseurl }}/kn7000-effects-dsp/);
- the panel and the keybed as its keys.

It is a port of **pt2-clone** by Olav Sørensen (8bitbubsy), the faithful C reimplementation of ProTracker 2.3D
(BSD 3-Clause). It is a program of the [program menu]({{ site.baseurl }}/kn7000-cnv-homebrew/) (folder `PROTRACK\`),
started from DISK MENU > STYLE CONVERT. Its test modules are the soundtrack of Pinball Fantasies, from the player's own
copy of the game.

Source: `kn5000_homebrew/demos/kn7000_protracker/` (its `README.md` has the details).

> **Status (2026-10-27): runs in MAME; not yet tried on an instrument.** In MAME (program 893, the loader floppy, the
> program menu on a copy of the owner's card) it:
> - starts from the menu, plays the six Pinball Fantasies modules and edits them with the panel and the keybed;
> - saves the result as a module that other trackers play.
>
> **User manual:** [ProTracker on the KN7000 (PDF, 15 pages)]({{ site.baseurl }}/assets/manuals/protracker-kn7000-manual.pdf).
>
> Its sound matches what the port's replayer should give, worked out on a PC with a model of the DSP's mixer. That in
> turn matches libopenmpt's rendering of the same modules ([How it was checked](#how-it-was-checked)).

## On the screen and the panel

![ProTracker's main screen on the KN7000's LCD, playing Pinball Fantasies' INTRO.MOD, in MAME]({{ site.baseurl }}/assets/images/kn7000/protracker-main-screen.png)

ProTracker's screen is 320 x 255; the KN7000's LCD is 640 x 240. The screen is drawn in the middle at 1:1. The
pattern shows 13 rows instead of 15, so that it fits the 240 lines. The 160 columns either side show:
- **the song** (left): its positions and the pattern each plays;
- **the samples** (right): all 31;
- **the soft keys' tags**, short, at the outer edges;
- **values** at the bottom: four boxes either side, each right above a MUTE UP/DOWN pair under the LCD, showing the
  value that pair changes.

The KN7000 has no computer keyboard and no mouse. Its panel takes their place, each control chosen so that what it does
on the KN7000 suggests what it does in ProTracker:

| KN7000                              | ProTracker                                                                            |
|-------------------------------------|---------------------------------------------------------------------------------------|
| the keybed                          | the note keys (C2 is C-1); chords go across the channels                              |
| SEQUENCER PLAY, EASY REC            | play the song; the edit mode (while playing: record)                                  |
| START/STOP, SYNCHRO & BREAK         | play / stop; play the pattern                                                         |
| SOUND GROUP (2 rows of 8)           | the hex keypad: 0-7 and 8-F; its ninth buttons delete                                 |
| RHYTHM GROUP (2 rows of 8)          | the samples 1-16 (SHIFT: 17-31), as ProTracker's numeric keypad                       |
| TEMPO/PROGRAM wheel                 | the row (while playing: the tempo; with SHIFT: the value under the cursor)            |
| PART SELECT                         | the cursor's column and channel                                                       |
| VARIATION 1-4, INTRO & ENDING       | rows 0, 16, 32, 48 (F6-F9); the start, row 63                                         |
| FILL IN 1, 2                        | insert, delete a row                                                                  |
| TRANSPOSE, R1/R2 OCTAVE             | the note (SHIFT: the track) a semitone, an octave                                     |
| PERFORMANCE PADS                    | cut, copy, paste the track and the pattern; BANK: undo                                |
| PANEL MEMORY 1-8, SET               | the effect macros: recall, and store (SET, then the number)                           |
| CONDUCTOR                           | the edited pattern; insert or delete a position                                       |
| MUTE UP/DOWN 1-4                    | POS, PATT, LEN, BPM                                                                   |
| MUTE UP/DOWN 5-12 (under the tracks)| each channel: heard, muted, solo, the cursor there                                    |
| MUTE UP/DOWN 13-16                  | the sample, its volume, its finetune, the edit skip                                   |
| DISPLAY HOLD                        | SHIFT                                                                                 |
| HELP                                | five pages of help on the LCD                                                         |
| LCDR 1-5, the Disk Op.              | the module before, after; load, save, save as new; clear                              |

![The edit mode: C3, E3 and G3 from the keybed went into rows 55-57 of channel 1, in MAME]({{ site.baseurl }}/assets/images/kn7000/protracker-edit-mode.png)

## How it works

The program has two parts:
- **`KN7APP.BIN`** is the Pinball Fantasies port's platform. It finds the firmware's routines, loads Another World's
  eight-voice sample mixer into the DSP, starts a task, and reads `PT.BIN`.
- **`PT.BIN`** is pt2-clone's replayer, module loader, text output, pattern view and bitmaps, compiled for the MN10300
  without SDL, a mouse or an audio thread.

What pt2-clone did through its own Paula emulation and SDL is done this way on the KN7000:

- **Paula on the DSP.** The replayer writes Paula's registers as it would on the Amiga. A note's sample and its loop
  become one voice command of the mixer: the start word in the DSP's SDRAM, the end, and the loop length. Period
  and volume changes update the voice's step and volume. When a loop is changed while a sample plays, the DSP can't
  be told in advance. The program then follows the voice's position on the CPU and starts the DSP voice on the new
  loop once the old part has ended.
- **The samples.** When a module is loaded, the program codes its samples with Another World's lossless code (about
  79 % of their bytes for the Pinball Fantasies modules). The converter calls send them through the host port; the
  DSP decodes them into its SDRAM and confirms them with a checksum. This is the platform's new `dspSend` call.
  Sending takes 0.5-2 s.
- **Time.** The replayer ticks by the kernel's millisecond counter and timer 4, 2.5/BPM seconds a tick, as the Amiga's
  CIA timer does.
- **The screen.** ProTracker's 12-bit colours go into the LCD controller's look-up table, and the screen is shown at 8
  bits a pixel. Only the 16-bit words that changed are written to display memory.
- **The panel, kept from the firmware.** The firmware keeps decoding the panel while a converter runs. In MAME it still
  acted on some buttons: PANEL MEMORY recalled a registration, which reloaded the effects DSP over the mixer, and
  R1/R2 OCTAVE moved the keybed's notes an octave. So the platform reads every switch frame from the panel's receive
  ring before the firmware's main task decodes it, as the Pinball port already did for the TEMPO/PROGRAM wheel. It
  keeps the real state for the program and clears the switches in the frame, so the firmware sees no change. CONTRAST
  stays the firmware's.

What differs from the Amiga: the DSP's mix is mono and has no Paula filters; a voice starts on a whole word (four
samples); EFx (invert loop) changes only the CPU's copy of a sample. The disk op., saving and the sample editor are
not part of the port.

## How it was checked

All of this was in MAME, program 893 (the scripts and their results are in `tests/` of the source):

- **What the port should play.** The port's replayer and Paula were built for a PC, with a model of the DSP's mixer.
  Their output was compared with libopenmpt's rendering of the same modules: the loudness envelopes correlate at
  r 0.86-0.95 in every 5 s window, at lag 0 and a constant level, for INTRO.MOD, MOD2.MOD and TABLE1.MOD.
- **What MAME's DSP played.** The emulator's sound was compared with that PC rendering, waveform against waveform, in
  2 s windows: r median 0.66-0.83, at a constant level, with the lag creeping by about 0.45 ms a second. That creep
  is the DSP's frame clock against the kernel's millisecond counter. On the instrument the DSP runs at 44,087 Hz by
  that counter, so the port's pitch is about half a cent off there.
- **Timing.** INTRO.MOD's positions over 26 s match the song's timeline. With the screen busy (the spectrum analyzer,
  the edit mode), 79 % of the replayer's ticks ran within 1 ms of when they were due and 1.9 % 10 ms or more late; the
  latest was 19 ms late.
- **Editing.** A scripted session makes an edit with the panel and the keybed and reads each step back from the
  program's memory: 24 of 24 checks pass. It covers notes, hex digits, delete and undo, macros, transposing, rows, a
  track copied and pasted, a chord, positions, HELP, and saving. The module it saved, taken off the card afterwards,
  differs from the original in exactly those edits, and libopenmpt plays it.
