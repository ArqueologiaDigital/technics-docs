---
layout: page
title: "Doom on the KN7000"
permalink: /kn7000-doom/
---

# Doom on the KN7000

id Software's Doom, as Chocolate Doom plays it, running on a stock KN7000:
- its startup log, title screen, demos and game on the instrument's LCD;
- its sound effects on the [effects DSP]({{ site.baseurl }}/kn7000-effects-dsp/#our-own-programs-on-the-dsp);
- the keybed and the panel as its game pad and keyboard.

It is a port of [Chocolate Doom](https://github.com/chocolate-doom/chocolate-doom) (GPL 2), the source port that
reproduces the DOS version of the game, with its own sources unchanged but for a few lines. It is a program of the
[program menu]({{ site.baseurl }}/kn7000-cnv-homebrew/) (folder `DOOM\`, listed in the menu's Games folder as
"Doom (Chocolate Doom)"), started from DISK MENU > STYLE CONVERT. It plays id Software's shareware `DOOM1.WAD`
(version 1.9), which the port's `tools/get_wad.sh` fetches from id's shareware release and checks by its MD5; the WAD is
not part of the source.

Source: `kn5000_homebrew/demos/kn7000_doom/` (its `README.md` has the details).

> **Status (2026-11-06): runs in MAME, and works on the owner's KN7000.** In MAME (program 893, the loader floppy, the
> program menu on a copy of the owner's card) it:
> - starts from the program menu, prints Chocolate Doom's startup log on the LCD, shows the title screen and plays
>   the demos;
> - starts a game and plays it from the keybed and the panel: walk, turn, fire, change weapon, the automap;
> - plays its sound effects on the effects DSP;
> - ends when EXIT is held, and gives the instrument back with the firmware's RAM it borrowed as it was.
>
> The `DOOM\` folder has been staged for the owner's SD card since 2026-10-29. On 2026-11-06 the owner reported
> that they had run it on the unit and that it works. Doom keeps no log on the card, so there are no figures from
> the unit. Not yet done: the music, and saving games and settings.

## Playing it

DISK MENU, STYLE CONVERT, OK (the loader floppy), and in the program menu's Games folder, "Doom (Chocolate Doom)".
In MAME the start takes 47 s from the menu's RUN; the startup log shows what is being done. The title screen and the
demos follow, as on a PC.

![Doom's title screen on the KN7000's LCD, with the soft keys' labels either side, in MAME]({{ site.baseurl }}/assets/images/kn7000/doom-title-screen.png)

| control                           | what it does                                  |
|-----------------------------------|-----------------------------------------------|
| keybed G#4                        | forward                                       |
| keybed G4                         | back                                          |
| keybed F4, A4                     | turn left, turn right                         |
| keybed F#4, A#4                   | strafe left, strafe right                     |
| keybed E4 (held)                  | run                                           |
| keybed C5                         | fire; in the menus, choose                    |
| keybed D5                         | use (doors, switches, lifts)                  |
| keybed E5                         | the automap                                   |
| keybed C6 D6 E6 F6 G6 A6 B6       | weapons 1 to 7                                |
| sustain pedal                     | fire                                          |
| soft keys left: MENU              | Esc: the menu (pressing EXIT does it too)     |
| ENTER, YES, NO                    | Enter, y, n: the menus and their questions    |
| MAP                               | the automap                                   |
| soft keys right: PAUSE            | pause                                         |
| VIEW -, VIEW + (and PAGE DOWN/UP) | the view's size (a smaller view draws faster) |
| GAMMA                             | brighter or darker (F11)                      |
| QUIT                              | Doom's quit question (YES ends it)            |
| EXIT held 1.5 s                   | ends it at once and gives the instrument back |

The game's keys lie above C4. The keys below the split point are the arranger's chord keys, and the firmware sends
them nowhere a program can read: in MAME, C3 held at the title screen never reached the program. While Doom runs, the
keybed plays no sound of its own.

The frame rate shows at the bottom left. If the game stops, the startup log's last line, or the blue crash screen with
its program counter, says where.

## How it works

The program has two parts, as ProTracker's and the Pinball Fantasies port's have:
- **`KN7APP.BIN`, the platform** (ProTracker's, at ABI 13). The loader runs it on each converter call. It finds the
  firmware's routines, starts a task for the game, serves its file reads, keeps the firmware from drawing, and hands
  the panel's switches over.
- **`DOOM.BIN`, Chocolate Doom.** Its sources are copied from upstream commit `a2dfd51`, with the KN7000's changes
  behind `CHOCO_KN7`. A KN7000 layer takes SDL's place: the LCD, the timer, the input, the sound, the WAD, the C
  library's files and formatted I/O.

![E1M1 on the KN7000's LCD after G#4 was held 2 s, in MAME]({{ site.baseurl }}/assets/images/kn7000/doom-e1m1.png)

### Memory

Doom needs about 1.7 MB: an image of 356 KB, 317 KB of static data, a zone (Doom's own heap) of up to 953 KB for the
shareware maps (E1M6 needs the most) and 50 KB of heap. A program has 1.3 MB of free RAM on the KN7000, in the regions
`ARENA1`-`ARENA7` ([RAM a program of one's own can use]({{ site.baseurl }}/kn7000-work-ram/#ram-a-program-of-ones-own-can-use)).
The port fits it this way:
- the image is linked to `ARENA2`; the static data goes to the program area, except the visplanes and openings
  (123 KB), which go to `ARENA1`;
- Chocolate Doom's `printf` and `scanf` families are replaced by a small formatter of the port's own, 70 KB smaller;
- the zone is one zone over every free region, the gaps between them filled by blocks that are never freed;
- on programs 893 and 941 the platform lends Doom 584 KB of the firmware's RAM that only the firmware's user interface
  and drawing use: the frame buffers, the SD player's lists, the LZSS trees and two file buffers. It keeps their
  contents in the LCD controller's display memory while Doom runs, and puts them back at the end.

### The WAD

The firmware's file routines read a file only from its start. So the platform reads the WAD where Doom asks, a few
sectors at a time, with the program menu's FAT16 reader over the loader's raw sector read. It serves the reads during
the converter call's rest. Sprite sizes come from the sprites' 8-byte headers, read alone, not from the whole lumps.

### The screen

The LCD is set to 8 bits a pixel through its look-up table, which holds Doom's palette (4 bits a colour). Doom's
320 x 200 frame sits in the middle of the 640 x 240 LCD, its lines shown as 240, as Chocolate Doom's aspect ratio
correction does. A line goes to the LCD only when it changed. The columns either side carry the soft keys' labels and
the frame rate. See [How the controller shows its memory]({{ site.baseurl }}/kn7000-display-subsystem/#how-the-controller-shows-its-memory).

### The input

The keybed's notes come from the firmware's MIDI rings, as Another World and ProTracker read them. A key struck and
let go between two frames still counts. On program 893 the panel's switches are taken from the panel's receive ring
before the firmware decodes them, so the firmware does not act on them.

### The sound

At start, the WAD's sound effects (534 KB, 11,025 samples a second) go into the effects DSP's SDRAM, coded as Another
World's mixer decodes them (with ProTracker's coder). Each of Doom's eight sound channels is a voice of that mixer. The
mixer is mono, so a sound's left-right placement is not heard.

## How it was checked

All of this was in MAME, program 893 (the scripts and their results are in `tests/` of the source):

- **A whole session.** `tests/mame/doom_test.lua` starts Doom from the program menu, and with `DOOM_PLAY=1` opens the
  menu, starts a new game on E1M1, holds G#4 for 2 s, holds F4 for 1 s, fires with C5, takes the fist with C6 and opens
  the automap with E5. It checks each step in Doom's memory: the player's position, angle, ammunition, weapon and the
  automap's flag. It makes 11 checks; the last run in the commit log passed 11 of 11. The run kept in
  `tests/results/`, from an earlier version of the script with 9 checks, passed 9 of 9.
- **The borrowed RAM.** After EXIT the test reads the platform's check of the copy kept in display memory: it came back
  as it went (`borrow_bad 0`). An earlier run had `borrow_bad 1`: the frame-rate text drew past line 240 into the copy.
  That was fixed. With `DOOM_TAPS=1` the test also logs every access to the borrowed RAM from code that is neither the
  platform's nor Doom's; the runs kept in `tests/results/` were made without it.
- **Speed.** Startup took 47.1 s from RUN. E1M1 was loaded and running (35 game tics on) 9.4 s after the skill was
  chosen. In a separate run's startup timeline the platform took 12.6 s, `R_Init` 11.7 s and sending the sound effects
  to the DSP 17 s. On E1M1, after the checks, the frame rate was 11.0 to 13.1 frames a second.
- **A read cache for the WAD.** At startup a 32 KB cache cut the card reads from 850 to 154 but read 4,772 KB instead
  of 2,198 KB, and was slower: startup 54.0 s against 51.9 s, E1M1 12.9 s against 9.6 s. It is off. Reading only the
  sprites' headers then brought startup to 47.1 s.
- **The sound.** The session's sound, second by second: the menu's and the game's effects are heard at about
  -44 dBFS, and it is silent while the player stands still.
- **The game code on a PC.** `make host` builds the same game code as a 32-bit PC program, so its structures have the
  KN7000's sizes. It found the smallest zone each shareware demo and each E1 map runs in: 635 KB (E1M1) to 953 KB
  (E1M6). A hash of every demo frame showed that reading only the sprites' headers changes 2 to 6 frames a demo, as a
  smaller zone does in the unchanged game.
- **The build.** Every link refuses a load or store with a register-plus-32-bit-displacement operand (`(d32,An)`), on
  which probes restarted the owner's unit, and an `addc` or `subc` right after a flag update. Built with the older GCC,
  Doom had 32 such `addc`/`subc`; with the GCC patched to put a `nop` before each, it has none.

## Limits and open items

- **No figures from the instrument.** The owner reports that it works there; the timings above are from MAME.
- **No music.** Probes found that bytes put into MIDI IN 1's ring while Doom draws are taken 0.6 to 159 ms later
  (median 55 ms): the firmware reads the ring only when the game's task yields, once a frame. Music played from Doom's
  task needs that task to yield more often, or another timer. Whether GM2 banks select GM sounds could not be told in
  MAME, where the programs' spectra differ too little; that needs the instrument.
- **No saved games or settings.**
- **Mono sound effects.**
- **Keys below C4** cannot be used: the firmware gives the arranger's chord keys to no program.

## Sources

- `kn5000_homebrew/demos/kn7000_doom/README.md`: status, controls, building, how it works.
- `kn5000_homebrew/demos/kn7000_doom/src/app/`: the platform (`borrow.c`, the borrowed RAM; `folder.c`, the WAD's
  reads).
- `kn5000_homebrew/demos/kn7000_doom/src/choco/`: Chocolate Doom (upstream commit in `UPSTREAM`).
- `kn5000_homebrew/demos/kn7000_doom/src/kn7/`: what takes SDL's place (`doom.ld`, `fmt.c`, `i_input.c`,
  `i_sound_kn7.c`, `i_video.c`).
- `kn5000_homebrew/demos/kn7000_doom/tests/mame/`: `run_doom.sh`, `doom_test.lua`, `sound_report.py`, and `probes/`
  for the music.
- `kn5000_homebrew/demos/kn7000_doom/tests/host/`: the PC build, `sweep.sh`, `zone_tags.py`.
- `kn5000_homebrew/demos/kn7000_doom/tests/results/README.md`: every result file, with the script that made it.
- `kn5000_homebrew` commits `892efb3`-`2b77770` (2026-10-29), `33b277a` (2026-10-31, the `addc`/`subc` check).
- `KN7000/tools/sdcard/`: the card staging that puts `DOOM\` on the owner's card (commit `5e6984c`).
