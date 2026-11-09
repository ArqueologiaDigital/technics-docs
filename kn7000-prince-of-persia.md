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

> **Status (2026-11-09): runs on the owner's KN7000.** The owner ran it from the card on 2026-11-09 and found the
> controls awkward, so the keybed now uses Another World's keys (below). In MAME (program 893,
> the loader floppy, the program menu on a copy of the owner's card) it:
> - starts from the program menu and shows the story, the title and the demo (SDLPoP's information screen, written
>   for a PC keyboard, is turned off);
> - starts a game and plays level 1 from the keybed and the panel at the game's own speed, 12 ticks a second;
> - plays its sound effects on the effects DSP and its music on the instrument's own tone generator;
> - draws the same frames as the same code built for the PC, and as SDLPoP itself on the real SDL 2 (below);
> - ends when EXIT is held or QUIT pressed, and gives the instrument back with the firmware's RAM it borrowed as it
>   was, straight to the main screen as the program menu does, with no "ERROR!";
> - stops the music before a level loads from the card, so no note hangs during the load;
> - saves and loads a quicksave on the card (SAVE, LOAD); on the instrument this is not tried yet.
>
> Loads: the first picture 7.8 s after RUN in MAME and a level about 5 s (26.7 s and 10 to 15 s before 2026-11-09:
> SDLPoP's look-ups of files that are not in the folder each read the folder from the card).
>
> Not yet: the music's instruments are a first guess. The port has a
> manual in the style of the instrument's Operating Instructions (`manual/` in its folder).

![Prince of Persia's title on the KN7000's LCD, with the soft keys' labels either side, in MAME]({{ site.baseurl }}/assets/images/kn7000/pop-title.png)

## Playing it

DISK MENU, STYLE CONVERT, OK (the loader floppy), and in the program menu's Games folder, "Prince of Persia
(SDLPoP)". The title comes first; ENTER starts the game.

| control                         | what it does                                                       |
|---------------------------------|--------------------------------------------------------------------|
| keybed F5, C6                   | left, right (run; with the action held, a careful step)            |
| keybed Ab5 or Bb5               | up: jump (with a direction, a running jump), climb up, block       |
| keybed A5                       | down: crouch, climb down, put the sword away                       |
| keybed C4 or any key below      | the action (Shift): grab a ledge, pick up, drink, strike           |
| sustain pedal                   | the action too                                                     |
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

![Level 1 on the KN7000's LCD in MAME: the Kid at the start, the frame rate at the bottom left]({{ site.baseurl }}/assets/images/kn7000/pop-level1.png)

The keybed keys are the same as [Another World's]({{ site.baseurl }}/another-world-vm/) on the KN7000: the right hand steers
with F5, Ab5/Bb5, A5 and C6, and the left hand acts with C4 or any key below it. While the game runs, the keybed plays
no sound of its own.

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
plays on an emulated OPL3; here SDLPoP's own sequencer keeps the music's time, so the scenes that wait for a song wait
as long as before, and its notes go to the instrument's own tone generator through MIDI IN 1, on parts 4 to 13, each of
SDLPoP's 18 OPL instruments as a GM2 sound chosen from its envelope.

**Two things SDLPoP does on the PC that the KN7000's CPU cannot.** The MN10300 cannot load or store 16 bits at an odd
address. SDLPoP's settings parser wrote some settings through such pointers into packed structures (so in MAME the first
level read 0 and every key started the demo), and its animation interpreter read jump targets from odd offsets of its
sequence table. The port leaves those structures unpacked, as upstream SDLPoP does for the PSP for the same reason, and
reads the jump targets a byte at a time. Plain `char` is unsigned on this compiler and signed on the PC, so the game is
built with `-fsigned-char`.

## How it is checked

The port's code is built for the PC as well (`make host`), with a virtual clock and no window. So is SDLPoP exactly as
vendored, with the real SDL 2 (`make ref`). Both write the hash of every frame they show. With the attract mode
(seed 1, 200 s: the story, the princess, the title, the credits and the demo fight: 1,835 distinct frames) and seven
of the replays SDLPoP ships as test cases (levels 2, 5 and 12 among them), the two builds show the same frames. A third
PC build runs the KN7000's own allocator over arenas of the KN7000's sizes, which is how the port's memory was fitted:
the attract mode peaks at 0.90 MB of the 1.45 MB the KN7000 has for it.

In MAME, the KN7000 build plays the same replays from the card (`kn7hash` in its `ARGS.TXT` makes it count frames by a
hash that the PC build writes too) and logs SDLPoP's state at each tick (the tick, the random seed, the Kid's place):
each of the seven replays shows the same frames as on the PC up to its end, and SDLPoP's state is the same on 548 of the
549 ticks both runs logged (the last of one replay was read at different moments of the return to the title). SDLPoP's story scenes, unlike its gameplay, fade inside their animation's timer loop, so how many fade
steps fall in each animation frame depends on the machine's speed; the attract mode is compared up to the first such
scene.
