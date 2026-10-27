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
> - starts from the menu and shows ProTracker's screen;
> - loads each of the six Pinball Fantasies modules, sends its samples to the DSP and plays it;
> - plays the keybed's notes on the current sample and writes them into the pattern in the edit mode.
>
> Its sound matches what the port's replayer should give, worked out on a PC with a model of the DSP's mixer. That in
> turn matches libopenmpt's rendering of the same modules ([How it was checked](#how-it-was-checked)).

## On the screen and the panel

![ProTracker's main screen on the KN7000's LCD, playing Pinball Fantasies' INTRO.MOD, in MAME]({{ site.baseurl }}/assets/images/kn7000/protracker-main-screen.png)

ProTracker's screen is 320 x 255; the KN7000's LCD is 640 x 240. The screen is drawn in the middle at 1:1. The
pattern shows 13 rows instead of 15, so that it fits the 240 lines. The 160 columns either side carry the labels of
the soft keys beside the display.

| control             | ProTracker's                                                                       |
|---------------------|------------------------------------------------------------------------------------|
| LCDL 1-5            | PLAY (song), PATTERN, STOP, EDIT, the quadrascope or the spectrum analyzer         |
| LCDR 1-5            | the module before or after (from `MODS.TXT`), the sample before or after, mute all |
| START/STOP          | PLAY, or STOP while playing                                                        |
| PAGE UP, PAGE DOWN  | the song position (in the edit mode, the row)                                      |
| TEMPO/PROGRAM wheel | the row (stopped), the sample (playing)                                            |
| MUTE UP 1-4         | channel 1-4 muted or not                                                           |
| MUTE DOWN 1-4       | the edit cursor to channel 1-4                                                     |
| the keybed          | the note keys: C2 is ProTracker's C-1, three octaves                               |
| EXIT held 1.5 s     | the end                                                                            |

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
- **The controls.** The spectrum analyzer, the mute buttons, the edit mode and the keybed's notes, the sample and
  module buttons and PAGE DOWN all work as the table above says.
