---
layout: page
title: "Prince of Persia on the KN7000"
permalink: /kn7000-prince-of-persia/
---

# Prince of Persia on the KN7000

Jordan Mechner's Prince of Persia (1989), as [SDLPoP](https://github.com/NagyD/SDLPoP) plays it, on a stock KN7000:
- its title, story scenes, demo and game on the instrument's LCD;
- its sound effects on the [effects DSP]({{ site.baseurl }}/kn7000-effects-dsp/#our-own-programs-on-the-dsp);
- the keybed and the panel as the keyboard SDLPoP reads.

SDLPoP (GPL 3) is the open-source port of the DOS game, made from its disassembly. The port vendors its sources
unchanged at upstream commit `3c5add5` and keeps the KN7000's changes behind `POP_KN7`. It is a program of the
[program menu]({{ site.baseurl }}/kn7000-cnv-homebrew/) (folder `PRINCE\`, listed in the menu's Games folder as
"Prince of Persia (SDLPoP)"), started from DISK MENU > STYLE CONVERT. The game's data is what the SDLPoP repository
itself ships in its `data/` folder, at the same commit. The port's `tools/get_data.sh` fetches it and checks every
file's SHA-256, and the build packs it unchanged into one file on the card.

Source: `kn5000_homebrew/demos/kn7000_sdlpop/` (its `README.md` has the details).

> **Status (2026-11-09): in progress.** The source is written, and the same code built for the PC matches SDLPoP on
> the real SDL 2, frame for frame (below). Its first runs in MAME follow.

## Playing it

DISK MENU, STYLE CONVERT, OK (the loader floppy), and in the program menu's Games folder, "Prince of Persia
(SDLPoP)". SDLPoP's information screen comes first; any key goes on to the title.

| control                         | what it does                                                       |
|---------------------------------|--------------------------------------------------------------------|
| keybed F4, A4                   | left, right (run; with E4 held, a careful step)                    |
| keybed G#4                      | up: jump, climb up, raise the sword to block                       |
| keybed G4                       | down: crouch, climb down, put the sword away                       |
| keybed F#4, A#4                 | jump left, jump right (Home and Page Up on a PC)                   |
| keybed E4, C5, sustain pedal    | Shift: grab a ledge, pick up, drink, strike with the sword         |
| keybed D5, E5                   | up and down for the right hand                                     |
| soft keys left: MENU            | Esc: SDLPoP's pause menu (pressing EXIT does it too)               |
| ENTER                           | Enter: choose in the menu                                          |
| TIME                            | Space: the minutes left                                            |
| SOUND                           | Ctrl+S: the sound on or off                                        |
| RESTART                         | Ctrl+A: this level again                                           |
| soft keys right: SAVE, LOAD     | F6, F9: quicksave and quickload                                    |
| NEW GAME                        | Ctrl+R: back to the title                                          |
| REPLAYS                         | Tab: on the title, the replays in the folder                       |
| QUIT                            | Ctrl+Q                                                             |
| EXIT held 1.5 s                 | ends it at once and gives the instrument back                      |

The game's keys lie above C4, as Doom's do: the keys below the split point are the arranger's chord keys, which the
firmware sends nowhere a program can read. While the game runs, the keybed plays no sound of its own.

## How it works

The program has two parts, as Doom's has:
- **`KN7APP.BIN`, the platform:** Doom's, renamed. The loader runs it on each converter call. It finds the firmware's
  routines, starts a task for the game, serves its file reads, keeps the firmware from drawing, hands the panel's
  switches over, and plays samples on the DSP's mixer.
- **`POP.BIN`, SDLPoP:** its sources, and a layer that stands in for the part of SDL 2 that SDLPoP calls (surfaces
  and blits, palettes, events, timers, files). SDLPoP's own code draws, times and plays the game unchanged.

**The screen.** SDLPoP draws 8-bit images into 24-bit surfaces. On the KN7000 a 24-bit surface holds one byte a pixel:
the index of its colour in one palette of 252 colours that all such surfaces share. That palette is the LCD
controller's look-up table, so a frame goes to the LCD as it is, a line only when it changed. This keeps SDLPoP's
screens to a third of their RAM. SDLPoP's fades darken every pixel by the same amount, so here they darken the look-up
table instead. The 320 x 200 picture is in the middle of the 640 x 240 LCD, its lines shown as 240. The columns
either side carry the soft keys' labels and the frame rate.

**Memory.** `POP.BIN`'s image (about 330 KB) is linked to the free region ARENA2, and its static data (about 106 KB) to
the program area. Everything else is malloc's: a heap in each free region and in the firmware RAM that the platform
lends while the game runs, as it does for Doom. The C library's own allocator can only grow forward through the
regions, and SDLPoP keeps blocks of up to 256 KB.

**The data** is one file on the card, `POPDATA.PAK`: every file of SDLPoP's `data/` folder, with its bytes unchanged.
SDLPoP opens `data/KID/res401.png` and the like; the port finds them in the pack, which it reads off the card 32 KB at
a time.

**The sound.** SDLPoP plays one sampled sound at a time through an audio callback. Here its sampled sounds go into the
effects DSP's sample bank when the game starts, coded as Doom's are, and each plays on a voice of the DSP's mixer.
The PC speaker sounds that have no sampled version are rendered into the bank too. The music is MIDI, which SDLPoP
plays on an emulated OPL3. On the KN7000 its own sequencer still keeps the music's time, so the scenes that wait for a
song wait as long as before, but no notes sound yet.

## How it is checked

The port's code is built for the PC as well (`make host`), with a virtual clock and no window. So is SDLPoP exactly as
vendored, with the real SDL 2 (`make ref`). Both write the hash of every frame they show. With the attract mode
(seed 1, 200 s: the story, the princess, the title, the credits and the demo fight: 1,835 distinct frames) and seven
of the replays SDLPoP ships as test cases (levels 2, 5 and 12 among them), the two builds show the same frames.
The same hashes from the KN7000 build in MAME are the main test of the port (`tests/mame`, `kn7hash` in the card's
`ARGS.TXT`).
