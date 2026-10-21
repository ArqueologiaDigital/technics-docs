---
layout: page
title: "Your Own Code on a Stock KN7000"
permalink: /kn7000-cnv-homebrew/
---

# Running your own code on a stock KN7000

A KN7000 runs machine code from outside in two vendor-sanctioned ways. One is the
[SP7001 SD plug-in]({{ site.baseurl }}/kn7000-sp7001-homebrew/), which needs the SP7001 firmware.
The other is the [style converter]({{ site.baseurl }}/kn7000-style-converter/): DISK MENU >
STYLE CONVERT loads a `.CNV` program from a floppy and runs it on the main CPU. That one works on
the stock firmware, and any MN10300 program linked to the converters' load address can use it, not
only a style converter.

The project runs all of its own code on the owner's instrument (program 893) through the second
door, in a fixed way:

1. **One floppy, made once and kept write-protected**, holds `KN7LOAD.CNV`, a generic loader.
   STYLE CONVERT runs it like any converter.
2. **The loader reads `C:\KN7APP.BIN` from the SD card** and calls it on every converter call.
3. **That `KN7APP.BIN` is a program menu.** It lists the programs in the card's folders, one per
   folder, each with a name and an icon, and starts the one picked.

A new program is a new folder on the card. Nothing on the floppy changes.

> **Status (2026-10-21).**
> - **The loader** (`KN7LOAD.CNV`, SHA-1 `6b81f382fd29b9bc5a025854af0e20a194e68bec`, unchanged since
>   2026-10-19) has run on the owner's unit in every pass of the [ROM dumper]({{ site.baseurl }}/kn7000-rom-dumper/).
> - **Another World** ran on the unit on 2026-10-20, from the card's root: first slowly, then with
>   the faster blit at about 20 frames per second. Its sound played there too, first on the tone
>   generator over MIDI and, since 2026-10-21, as the game's own samples on the effects DSP
>   ([below](#sound)).
> - **The program menu** passes its tests in MAME, on program 893 with the owner's loader floppy
>   image and a copy of his card. On the unit it has started Another World from `AW\` and DSPTONE
>   (2026-10-21).
> - **DSPTONE**, a program of our own on the effects DSP, ran on the unit on 2026-10-21: the owner
>   heard its tone and its sweep, and the reverb came back after STOP
>   ([Effects DSP]({{ site.baseurl }}/kn7000-effects-dsp/#dsptone-iteration-1-a-tone-and-a-sweep)).

## Running a program

1. Switch on and wait for the main screen. Insert the KN7LOAD floppy and the SD card.
2. **DISK MENU**, then **STYLE CONVERT** (left button 3). The list shows `KN7LOAD.CNV`. Press
   **OK** (right button 4).
3. The loader's screen flashes by. Then "KN7000 PROGRAMS": the list, five to a page, one program
   beside each left button. Press the **left button** beside a program to select it. PART SELECT
   LEFT / RIGHT 1 move the selection; right button 2 or PAGE DOWN shows the next page, right button
   1 or PAGE UP the one before.
4. **RUN** (right button 5) reads the program, checks it as the loader would, and starts it. A
   damaged or foreign `KN7APP.BIN` is refused: its line says why, in red, and nothing starts.
5. When the program ends, the firmware shows its message, then "Continue Next?". **YES** (right
   button 3) brings the menu back; **NO** (right button 4) returns to the main screen. EXIT on
   "Continue Next?" cancels to the STYLE CONVERT screen, so do not press it there.
6. To leave the menu itself: **LEAVE** (right button 4), or hold EXIT for 1.5 s and let go; then NO.

## The card

The menu's build (`make card` in `kn7000/tools/kn7menu`) writes everything for the card's root:

| on the card  | what                                                                                    |
|--------------|-----------------------------------------------------------------------------------------|
| `KN7APP.BIN` | the program menu (12,739 bytes)                                                         |
| `AW\`        | Another World: its `KN7APP.BIN` and 140 game files, made from your own copy of the game |
| `SURVEY2\`   | the ROM dumper's pass 5                                                                 |
| `DSPPROBE\`  | pass 6, the DSP probe, phase 1                                                          |
| `DSPMEM\`    | pass 7, the DSP probe, phase 2                                                          |
| `DSPRATE\`   | pass 8, the DSP frame rate                                                              |
| `CPUTIME\`   | pass 9, the CPU timing probe                                                            |
| `DSPTONE\`   | our own program on the effects DSP, iteration 1                                         |

The probes' binaries are the released ones, byte for byte; the build checks each against its
release's `SHA1SUMS`. The probes still write their result files to the card's root, as they did
when each was the root's `KN7APP.BIN`: the loader keeps the card's current folder empty around every
call, so every name an application opens is relative to `C:\`.

### Adding a program

A program is a folder in the card's root with a `KN7APP.BIN` in it: any application of
`KN7LOAD.CNV` (made with the loader's `mkapp.py`, which writes its header and CRC-32), at most
188,160 bytes. Beside it, optionally:

- **`MANIFEST.TXT`**, plain text, one `KEY=VALUE` per line, `#` for comments:

      # Another World for the KN7000
      NAME=Another World
      ICON=ICON.BMP

  `NAME` is what the list shows (ASCII, up to 63 characters). `ICON` names an icon file in the same
  folder. Without a usable name the list shows the folder's long name, or its 8.3 name.
- **The icon**: a Windows BMP of exactly 32 × 32 pixels, 24 or 32 bits per pixel, uncompressed.
  `png2icon.py my.png ICON.BMP` makes one from any PNG. Without a usable icon the list shows a
  default one.

`fatscan.py FOLDER` shows, on a computer, what the menu will list for a card with that folder's
contents in its root, and whether RUN would start each program. The menu looks at up to 64
folders.

### The launch block

A program that wants its own files from its folder reads the **launch block**: 256 bytes at
`0x502E7F00`, the last of the application area, which the menu writes before it starts a program.
The loader zeroes the whole area before it loads anything, so a program started straight from
`C:\KN7APP.BIN` finds zeros there. No program may keep data of its own in these 256 bytes.

| offset | field       | size | what                                                              |
|--------|-------------|------|-------------------------------------------------------------------|
| `0x00` | `LB_MAGIC`  | 4    | `0x4C374E4B` ("KN7L")                                             |
| `0x04` | `LB_ABI`    | 4    | 1                                                                 |
| `0x08` | `LB_SIZE`   | 4    | the bytes of `KN7APP.BIN` the menu put at the load address        |
| `0x0C` | `LB_CRC`    | 4    | its CRC-32, as in its header                                      |
| `0x10` | `LB_DIR`    | 16   | the folder's 8.3 name, `AW`, NUL-ended                            |
| `0x20` | `LB_PREFIX` | 16   | the same with a backslash, `AW\`: put in front of a file name     |
| `0x30` | `LB_PATH`   | 32   | `C:\AW`, for the firmware's set-folder routine                    |
| `0x50` | `LB_NAME`   | 64   | the name the menu showed, NUL-ended                               |
| `0xFC` | `LB_CHECK`  | 4    | `0xB3C8B1B4`, the bitwise NOT of the magic                        |

Another World copies `LB_PREFIX` on its first call and opens every file as that prefix and its
name (`AW\AWR11.AW`), through the loader's open routine. In the root, without the menu, the prefix
stays empty and the names are the old ones.

### How the menu starts a program

The menu writes nothing to the card. It reads it through one routine the loader found in the
firmware, the raw sector read that the firmware's own FAT library uses, and a read-only FAT16
reader of its own. RUN then:

1. reads the program's `KN7APP.BIN` into a staging area above the application area;
2. checks it exactly as the loader checks what it loads: the magic, the loader ABI, the link
   address, the size, the entry point, the CRC-32;
3. starts it through a small trampoline, copied out of the way first. The trampoline copies the
   program over the menu, zeroes the rest of the area, compares the copy byte for byte, writes the
   launch block, empties both caches, and returns to the loader. From the next converter call on,
   the loader calls the new program, as if it had loaded it itself.

**The caches** need that step: the CPU's data cache is write-back, and the instruction cache could
still hold the menu's code at the addresses the new program now occupies. The trampoline empties
the data cache by reading 64 KB of program flash, one load per 16-byte line, which replaces every
line and writes the dirty ones back. It empties the instruction cache by running a 32 KB sled of
`nop`s twice. Only ordinary loads and fetches are used: no cache register is written. MAME's MN10300
had no caches when the menu was written, so this part rests on reasoning, not a test
([CPU clock and caches]({{ site.baseurl }}/kn7000/#cpu-clock-64-mhz-with-caches-measured)).

**Safety.** The menu and the loader's other applications keep the same rules: no write to IC23
(the panel memories, `0x44000000` and its uncached view `0x84000000`) or to the user-memory pools
(`0x50180000`-`0x50297FFF`), no write to the loader's resident area, and every loop bounded. A
build-time guard checks every address the code can produce, and the MAME tests tap every write.
None of the fifteen buttons the menu reads changed a setting in those tests.

## What a converter gets

The [Style Converter]({{ site.baseurl }}/kn7000-style-converter/) page describes how the firmware
runs Technics' own converters. Another World, the loader and a few probe converters added what a
program of one's own needs to know (measured in MAME on programs 941 and 893):

- **Where it runs.** The firmware zeroes `0x30000` bytes at `0x502B8000` and reads the file there
  whole. It then calls the first byte with `calls (a0)`, so the program starts with a normal
  function prologue. With the loader in place, an application runs at `0x502BA000`; the RAM it may
  use is `0x502BA000`-`0x50379FFF`, less the firmware's mailbox page.
- **When it runs.** The converter is called on the firmware's **main task**. That task also
  decodes the panel buttons and passes keybed notes to MIDI OUT.
- **It must return.** A converter that loops forever keeps running, even if it yields to other
  tasks, but no panel button and no keybed note gets through any more.
- **Request 5 parks the user interface.** On each return the firmware reads a request from the
  mailbox at `0x5031BC00`. Request 5, "show this text", keeps it on the converter's text screen.
  It calls the converter again about 20 times a second and ignores EXIT, while the panel and the
  keybed keep working. The firmware still acts on R1/R2 OCTAVE + / − and SUSTAIN there.
- **Request 1 parks without a repaint.** Request 5 makes the firmware repaint its converter screen,
  and after a call that ran long it repaints the whole screen. **Request 1**, "copy four bytes and
  call again", parks the firmware just as well and leaves the screen alone. The ROM dumper parks
  this way.
- **A task of its own.** The converter can start a task (`cre_tsk`, then `sta_tsk`, at priority 3,
  the firmware's own priority) and answer request 5 from then on. The task can run a game loop,
  read input and draw. The kernel does not time-slice, so the task must yield each frame with
  `dly_tsk`.
- **Input.** The panel's switch bitmaps, debounced and held, are in work RAM. Every keybed note
  goes to the MIDI OUT 1 transmit ring, and MIDI IN 1 bytes arrive in their own ring.
- **Display.** The parked screen does not repaint, so the program draws straight into the LCD frame
  at `0x9CE00000` (640×240, RGB565). Stores there are slow, about 28 CPU cycles each at best
  ([what the LCD costs]({{ site.baseurl }}/kn7000-display-subsystem/#what-the-lcd-costs-the-cpu)).
- **Quitting.** Answering request **0xFE** ends the conversion. The firmware shows its message box,
  then "Continue Next?". With the loader, YES loads `KN7APP.BIN` again; NO returns to the main
  screen.

The addresses differ between program builds, so the loader and every application find them in
the firmware by code signatures at run time and carry none. What they find:

| what                             | 893 (v1.3, the owner's)     | 941 (v1.6)                  | 942 (SP7001)                |
|----------------------------------|-----------------------------|-----------------------------|-----------------------------|
| `cre_tsk`                        | `0x4C03D0B5`                | `0x4C03D0C8`                | `0x4C03D46B`                |
| `sta_tsk`                        | `0x4C03D898`                | `0x4C03D8AB`                | `0x4C03DCD3`                |
| `dly_tsk`                        | `0x4C03DD5C`                | `0x4C03DD6F`                | `0x4C03E295`                |
| `exd_tsk`                        | `0x4C03D58E`                | `0x4C03D5A1`                | `0x4C03D944`                |
| kernel millisecond counter       | `0x500C53F8`                | `0x500D3C58`                | `0x500D3C68`                |
| panel switch bitmaps, CPR / CPL  | `0x5006BE4C` / `0x5006BE7C` | `0x5006BE50` / `0x5006BE80` | `0x5006BE60` / `0x5006BE90` |
| MIDI IN 1 ring / MIDI OUT 1 ring | `0x5001F020` / `0x5001F834` | `0x5001F050` / `0x5001F864` | `0x5001F060` / `0x5001F874` |

Build 935 matches 941 for the task services. The disassembly's ported symbols had named
`0x4C03D8AB` `ext_tsk`; it is `sta_tsk`, and the probes show it starting a task.

**One assembly pitfall.** On the MN10300, `call` stores the return address at the top of the
stack and does not move the stack pointer. A routine entered with `call X, 0, 0` that calls
another before making a frame of its own overwrites that address, and its return goes astray.
The game's build checks every routine for it.

## Another World on the instrument

The same [Another World VM]({{ site.baseurl }}/another-world-vm/) that runs on the KN5000, ported to
the MN10300, is a program of this kind: `AW\KN7APP.BIN` on the card. It takes no address from any
build: it finds the firmware's task services, millisecond counter, panel bitmaps and MIDI rings by
signature, and runs on programs 893, 935, 941 and 942.

- **Memory.** Everything the game writes is in `0x502BA000`-`0x50379FFF`: code, VM state, the four
  pages, the current part's files. It holds one part at a time and loads each part's files from the
  card when the part starts, as the original engine does. It never touches IC23 or the user-memory
  pools: a build-time guard, run-time range checks and MAME write taps over whole sessions check
  it. The procedure for a run on the unit records IC23 before and after the session with the
  dumper's SURVEY2 pass, so that any change would show.
- **Controls.** The keybed (or MIDI IN 1 on channels 1-3) is preferred: F5 left, C6 right, Bb5 or
  B5 up, A5 down, C4 or any lower key for action. The panel works too: PART SELECT LEFT / RIGHT 1,
  R1/R2 OCTAVE + / − and SUSTAIN; but the firmware still acts on OCTAVE and SUSTAIN while the game
  runs. HELP shows the controls and the level codes; hold EXIT for 1.5 s to quit.

### Speed

The first build ran on the unit on 2026-10-20 at **1.5 frames per second**. Every VM tick it
blitted the whole page to the LCD twice and repainted the border each time: 217,600 stores into the
LCD frame per tick. MAME then gave the LCD no wait states, so it showed none of it; the unit's
pass 9 measured a 16-bit LCD store at 439 ns. The next build:

- writes only the pixels that changed, against a copy in RAM of what the LCD shows, two pixels per
  32-bit store;
- paints the border once, and again only when something may have drawn over it (checked with 47
  sentinel pixels);
- measures itself on the instrument, against the CPU's timer 4, and writes a report to the card at
  each quit (`AWPERFn.TXT`).

The owner ran that build the same day. Its own figures, from two reports:

| blit     | frames/s (whole run)                 | blit, ms/frame | border, ms/frame | LCD pixels/frame |
|----------|--------------------------------------|----------------|------------------|------------------|
| new blit | 19.0-21.2 (25-30 in the last second) | 22-27          | 1.4-1.7          | 3,500-5,300      |
| old blit | 1.5                                  | 268-270        | 347              | 128,000          |

The game's benchmark put a 16-bit LCD store at 1.3-1.8 µs while the game ran, three to four times
pass 9's figure. Page operations (10-15 ms per frame) are now the next cost after the blit. The
overlay emulator now models the CPU's real timing, so MAME shows the slow LCD too
([MAME Emulation Gaps]({{ site.baseurl }}/mame-emulation-gaps/#kn7000-the-overlay-emulator)).

### Sound

The game has three sound modes, and **PART SELECT RIGHT 2** cycles through them: the game's own
samples on the **effects DSP**, the **tone generator** over MIDI, and **off**. The first page of
the help screen names the current mode. The game starts in the DSP mode when it could set the DSP
up, and in the tone generator's otherwise. In every mode the music player runs and writes the
**sync marks** the intro reads (variable `0xF4`), so the intro's scenes follow the music, as in the
original, whether the sound is on or off.

#### The DSP mode: the game's own samples

> **On the instrument (2026-10-21, `KN7APP.BIN` `a2fbbaa6…`, program 893).** By the owner's
> report the sounds play perfectly, with REVERB on and with REVERB off (on is a little louder),
> at about a piano note's level. Nothing was garbled or stuck, and the reverb and the chorus came
> back after quitting. The first load of the sounds felt slow.

The tone generators play only their wave ROMs, so the game's own sounds have to come from the
effects DSP. The game puts a sample mixer of its own into the DSP's running kernel, as
[DSPTONE]({{ site.baseurl }}/kn7000-effects-dsp/#dsptone-iteration-1-a-tone-and-a-sweep) did,
through the firmware's own host-port routines.

- **The bank, once per power-on.** The 93 sounds the game plays, 684,980 samples, are their own
  card files. At the first start after power-on the game sends them all into the DSP's SDRAM;
  "LOADING ANOTHER WORLD: SOUNDS" and the load bar show while it runs (25.9 s in MAME). A marker
  left in DSP memory lets every later start skip it.
- **Eight voices**: the original's four sound-effect channels and its module player's four, mixed
  on the DSP at the samples' own rates and volumes.
- **Where it is heard.** The mixer takes over two of the kernel's effect units, the REVERB's and the
  CHORUS's, so the panel's reverb and chorus are off while it plays and the keybed sounds dry.
  Quitting, switching to another sound mode, any failure, and the firmware no longer calling the
  game all put both units back, read back.
- **Safety.** Only the firmware's routines touch the DSP. The game checks the DSP before it starts,
  reads its mixer back before using it, and watches the firmware's "DSP dead" flag at every step.
  If the DSP cannot be used, the help screen says "NO DSP" with a reason code, and the game falls
  back to the tone generator. Nothing of this outlives a power cycle.

The details, with what the run showed about the DSP, are on
[Effects DSP]({{ site.baseurl }}/kn7000-effects-dsp/#another-worlds-own-samples-iteration-2).

#### The tone generator mode: MIDI notes

The first sound build played the game's sounds on the **KN7000's own tone generator**. It outputs
no samples: it becomes a MIDI source inside the instrument. The owner reported that it plays
properly on his instrument (2026-10-21, `KN7APP.BIN` `97fbd9e6…`).

- **The way in.** The game writes each MIDI message into the firmware's **MIDI IN 1 receive ring**,
  as the receive interrupt does, with interrupts masked so that neither the interrupt nor a task
  switch can come in the middle. A firmware task then parses it like any byte from the MIDI IN
  jack. The game never touches the read pointer.
- **Which channels.** As the KN7000 is initialised, MIDI channels 1-3 play the panel's RIGHT 1,
  RIGHT 2 and LEFT, and channels 4-16 play PART 4-16. The game sends on channels 4-7 (the sound
  effects, one per Another World mixer channel), 10 (drums) and 11-14 (the music, one per module
  channel), so **it never touches the panel's parts**. It selects each sound with GM bank select and
  a program change.
- **Sound effects.** Each of the game's sounds has a GM program and a note, or a GM drum key, from
  a hand-made table. The game's frequency index moves the note by semitones, the volume is the
  velocity, and the note lasts as long as the sample would.
- **Music.** The original's module player runs on the kernel's millisecond counter and sends each
  row's notes.
- **Leaving the mode** sends all notes off and all sound off. **Quitting** sends all notes off,
  all sound off and reset all controllers on every channel the game used.

Two limits remain in this mode. The GM sounds were chosen without hearing the KN7000 play them, and
the routing is the instrument's initial one. If PART 4-14 have been given other channels, the game
may sound different or not at all.

## History: `AW.CNV`, one program per floppy (retired)

Until 2026-10-20 the game was its own style converter, `AW.CNV`, on a floppy of its own with the
original game data, and it ran only in MAME. It kept its 1.7 MB of data in the `0x44000000` window,
which MAME then mapped as 16 MB of RAM; on the instrument that window is IC23, which repeats every
256 KB, so the game would have overwritten the panel memories. The loader route replaced it.

![Another World's intro, run from a floppy as a style converter, in MAME]({{ site.baseurl }}/assets/images/kn7000/another-world-cnv-intro.png)

![The firmware's "Continue Next?" screen after quitting the game]({{ site.baseurl }}/assets/images/kn7000/another-world-cnv-continue.png)

## Sources

- [`technics-roms-disasm`](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/kn7000),
  `kn7000/`: `tools/cnv_romdump/` (the loader, `kn7cnv.inc`, the dumper and its probe passes),
  `tools/kn7menu/README.md` (the menu, the card, the launch block, the caches),
  `tools/dsptone/README.md`, and `notes/style-converter.md` (the firmware side).
- The Another World repository, `kn7000/README-CNV.md` (the build, its memory, speed and sound),
  `kn7000/probes/cnv/README.md` (the probes and the MAME tests) and
  `kn7000/probes/cnv/unit-results-2026-10-20/README.md` (the unit's figures).
- [Work RAM Map]({{ site.baseurl }}/kn7000-work-ram/) (what the firmware leaves free) and
  [Tasks & Scheduler]({{ site.baseurl }}/kn7000-task-scheduler/).
