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

> **Status (2026-11-06).**
> - **The loader** (`KN7LOAD.CNV`, SHA-1 `6b81f382fd29b9bc5a025854af0e20a194e68bec`, unchanged since
>   2026-10-19) has run on the owner's unit in every pass of the [ROM dumper]({{ site.baseurl }}/kn7000-rom-dumper/).
> - **Another World** ran on the unit on 2026-10-20, from the card's root: first slowly, then with
>   the faster blit at about 20 frames per second. Its sound played there too, first on the tone
>   generator over MIDI and, since 2026-10-21, as the game's own samples on the effects DSP
>   ([below](#sound)). Since 2026-11-01 the owner has played its new builds, logging the sessions
>   for replay in MAME: 384x240 pages, the LCD at 8 bits a pixel with an ambilight, a settings
>   page, and the panel's LEDs following the game ([below](#another-world-on-the-instrument)).
> - **The program menu** passes its tests in MAME, on program 893 with the owner's loader floppy
>   image and a copy of their card. On the unit it has started Another World from `AW\`, DSPTONE
>   (2026-10-21), Pinball Fantasies and ProTracker. Since 2026-11-04 it draws in an LCD frame of its
>   own, so nothing of the firmware's screen shows, and each row says what the program is.
> - **DSPTONE**, a program of our own on the effects DSP, ran on the unit on 2026-10-21: the owner
>   heard its tone and its sweep, and the reverb came back after STOP
>   ([Effects DSP]({{ site.baseurl }}/kn7000-effects-dsp/#dsptone-iteration-1-a-tone-and-a-sweep)).
> - **Pinball Fantasies**, a port of the PC game (the Pinball repository, `kn7000/`), is an
>   application of the loader too. On the owner's unit (program 893, 2026-10-26/27) its tables
>   played with their sound on the effects DSP and the panel's controls, and its front end (the
>   game's own slides, menu and music) came up. Since then, in MAME: the TEMPO/PROGRAM wheel types
>   a best score's letters while its LED blinks, and the sides of the table show the game's logos
>   and best scores, drawn in the LCD controller's ink layer. It uses RAM outside the converter's
>   area ([Work RAM Map]({{ site.baseurl }}/kn7000-work-ram/#ram-a-program-of-ones-own-can-use)), and
>   a failure on the unit changed how a program [syncs the caches](#the-caches).

## Running a program

1. Switch on and wait for the main screen. Insert the KN7LOAD floppy and the SD card.
2. **DISK MENU**, then **STYLE CONVERT** (left button 3). The list shows `KN7LOAD.CNV`. Press
   **OK** (right button 4).
3. The loader's screen flashes by. Then "KN7000 PROGRAMS": the list, five rows to a page, one
   beside each left button. A row is a program or a menu folder (Games, Tools, Other apps, HW
   Probes), with its icon, its name, and under it the program's folder on the card and what it is
   (the manifest's `DESC=`). Press the **left button** beside a row to select it; a folder's row
   opens the folder, and right button 1 (**BACK**) goes up again. PART SELECT LEFT / RIGHT 1 move
   the selection, across pages; PAGE DOWN shows the next page, PAGE UP the one before.
4. **RUN** (right button 5) reads the program, checks it as the loader would, and starts it. A
   damaged or foreign `KN7APP.BIN` is refused: its line says why, in red, and nothing starts.
5. When the program ends, the firmware shows its message, then "Continue Next?". (Another World
   goes straight back to the menu instead, [below](#another-world-on-the-instrument).) **YES** (right
   button 3) brings the menu back; **NO** (right button 4) returns to the main screen. EXIT on
   "Continue Next?" cancels to the STYLE CONVERT screen, so do not press it there.
6. To leave the menu itself: **LEAVE** (right button 4), or hold EXIT for 1.5 s and let go. The main screen
   comes back with no message (since 2026-11-06, in MAME; until then the firmware put up "ERROR!" and
   "Continue Next?", which it does for every converter that ends with request 0xFE). To open the menu again:
   DISK MENU, STYLE CONVERT, OK.

## The card

The menu's build (`make card` in `kn7000/tools/kn7menu`) writes the menu, Another World, Pinball
Fantasies and the probes; the KN7000 repository's `tools/sdcard/stage.sh` adds the programs of
other repositories and stages the whole tree, as on the owner's card (2026-11-05):

| on the card              | what                                                                                                     |
|--------------------------|----------------------------------------------------------------------------------------------------------|
| `KN7APP.BIN`             | the program menu (14,706 bytes)                                                                          |
| `KN7MENU.TOC`            | the menu's table of contents, made with the card: every program's name, menu folder, icon and size       |
| `AW\`                    | Games: Another World: its `KN7APP.BIN`, a manifest, an icon and 73 files made from your copy of the game |
| `PINBALL\`               | Games: Pinball Fantasies, the 1994 DOS game's four tables, from your own copy                            |
| `DOOM\`                  | Games: [Doom]({{ site.baseurl }}/kn7000-doom/) (Chocolate Doom, the shareware episode)                   |
| `KEYFALL\`               | Games: [Keyfall]({{ site.baseurl }}/kn7000-keyfall/), a falling-notes piano game                         |
| `PDF\`                   | Tools: the [PDF viewer]({{ site.baseurl }}/kn7000-pdf-viewer/) (MuPDF)                                   |
| `PROTRACK\`              | Other apps: [ProTracker 2.3D]({{ site.baseurl }}/kn7000-protracker/), which plays and edits modules      |
| `DSPTONE\`               | Other apps: our own program on the effects DSP, iteration 1                                              |
| `PFDIAG\`                | Other apps: Pinball Fantasies with its start-up logged to the card                                       |
| `SURVEY2\` .. `CPUTIME\` | HW Probes / ROM dumper passes: passes 5 (SURVEY2) to 9 (the CPU's timing), the DSP probes between        |
| `PFHELLO\`, `PFT1\` ..   | HW Probes / Pinball probes: the probes that settled the CPU's and the LCD's behaviour for the ports      |

A program's menu folder and its description come from its `MANIFEST.TXT` (`FOLDER=`, `DESC=`).
[KN7FM]({{ site.baseurl }}/kn7000-fm-synth/), a DX7-style FM synthesizer on the effects DSP, is a program for the same
card but not part of the staged tree: its folder `KN7FM\` comes from its own `make card-dir` (kn5000_homebrew
`demos/kn7000_fm`). So far it has run in MAME only.

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
      FOLDER=Games
      DESC=Eric Chahi's 1991 cinematic adventure

  `NAME` is what the list shows (ASCII, up to 63 characters). `ICON` names an icon file in the same
  folder. Without a usable name the list shows the folder's long name, or its 8.3 name. `FOLDER`
  is the menu folder the program is listed in (a path such as `HW Probes/Pinball probes`; without
  it, the top of the menu), and `DESC` what the row's second line says after the program's folder.
  Both are read when the card is made (`mktoc.py`, which writes `KN7MENU.TOC`), not by the menu.
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

| offset | field       | size | what                                                          |
|--------|-------------|------|---------------------------------------------------------------|
| `0x00` | `LB_MAGIC`  | 4    | `0x4C374E4B` ("KN7L")                                         |
| `0x04` | `LB_ABI`    | 4    | 1                                                             |
| `0x08` | `LB_SIZE`   | 4    | the bytes of `KN7APP.BIN` the menu put at the load address    |
| `0x0C` | `LB_CRC`    | 4    | its CRC-32, as in its header                                  |
| `0x10` | `LB_DIR`    | 16   | the folder's 8.3 name, `AW`, NUL-ended                        |
| `0x20` | `LB_PREFIX` | 16   | the same with a backslash, `AW\`: put in front of a file name |
| `0x30` | `LB_PATH`   | 32   | `C:\AW`, for the firmware's set-folder routine                |
| `0x50` | `LB_NAME`   | 64   | the name the menu showed, NUL-ended                           |
| `0xFC` | `LB_CHECK`  | 4    | `0xB3C8B1B4`, the bitwise NOT of the magic                    |

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
   launch block, syncs both caches, and returns to the loader. From the next converter call on,
   the loader calls the new program, as if it had loaded it itself.

### The caches

The CPU's data cache is write-back, and the instruction cache can still hold the menu's code at
the addresses the new program now occupies
([CPU clock and caches]({{ site.baseurl }}/kn7000/#cpu-clock-64-mhz-with-caches-measured)). So
after a copy the menu and its trampoline do what program 893's own routines do (its
instruction-cache routine at `0x48407B..` and its data-cache purge `func_48407C39`), with
interrupts off for the few microseconds it takes, because while the data cache is off an
interrupt handler would read RAM that its dirty lines have not reached:

1. **The data cache**, if on: clear bit 1 of CHCTR (`0x20000070`) and wait for bit 3 to clear.
   Write each line of both ways back by reading the purge window, 128 lines of 16 bytes at
   `0x28400000` (way 0) and at `0x28401000` (way 1); this step is skipped when bit 6 (write-through)
   is set, and for one way when bit 12 or 13 (that way locked) is. Set bit 5 to invalidate, then
   bit 1 again.
2. **The instruction cache**, if on: clear bit 0, wait for bit 2 to clear, set bit 4 to
   invalidate, then bit 0 again.

Until 2026-10-27 the trampoline emptied the data cache by reading 64 KB of program flash, one load
per 16-byte line, and the instruction cache by running a 32 KB sled of `nop`s twice, without
writing any cache register. The Pinball Fantasies port did the same between its programs, and on
the owner's unit that failed: as the port's menu came back after a table, the CPU stopped with a
system-error NMI (NMICR `0004`) at `0x5031C75C`, 0x75C bytes into its sled. A line of the sled had
stayed in the data cache, and the instruction fetch read what RAM held there before, the table's
heap. The menu (`cachesync.inc`, technics-roms-disasm `b58b8f696`) and the port now use the
firmware's sequence. MAME could not have shown the failure: its model times the caches, but every
access reaches memory
([MAME Emulation Gaps]({{ site.baseurl }}/mame-emulation-gaps/#kn7000-the-overlay-emulator)).

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
  use is `0x502BA000`-`0x50379FFF`, less the firmware's mailbox page. More RAM outside that area
  stays unused while a converter runs, on program 893 checked on the unit
  ([Work RAM Map]({{ site.baseurl }}/kn7000-work-ram/#ram-a-program-of-ones-own-can-use)).
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
- **What request 5 costs.** Program 893 answers request 5 with `ChangeTitle(0x4A)` on every call
  (`func_48479771`), the new title calls the converter again, and each change repaints the screen:
  a loop on the main task, through `ScreenProc`'s paint (`DrawWall`, a 150 KB copy of the wallpaper
  plane) and a copy of the changed areas to the LCD a dot at a time. In MAME the Pinball Fantasies
  port's game got 35 % of the CPU while that ran (`cpu_split.py`, session notes 2026-10-26). The
  port points `ScreenProc`'s view record at a copy without the paint (the class table at
  `0x5011FA88`), rests each converter call for up to 100 ms on `dly_tsk`, and holds the
  firmware's draw switch `DrawEnable` (`0x5002A018`) at 0 while the game owns the LCD, setting it
  only while `0x5002A01C` reads 1 (a `DrawWall` under way waits on it). Its game then got 82 %.
- **A task of its own.** The converter can start a task (`cre_tsk`, then `sta_tsk`, at priority 3,
  the firmware's own priority) and answer request 5 from then on. The task can run a game loop,
  read input and draw. The kernel does not time-slice, so the task must yield each frame with
  `dly_tsk`.
- **Input.** The panel's switch bitmaps, debounced and held, are in work RAM. Every keybed note
  goes to the MIDI OUT 1 transmit ring, and MIDI IN 1 bytes arrive in their own ring. The
  TEMPO/PROGRAM wheel's steps arrive in the panel's receive ring, where a program can take them
  before the firmware changes the tempo, and the panel LEDs can be set through the firmware's LED
  shadow ([Control Panel]({{ site.baseurl }}/kn7000-control-panel/#leds)).
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
the MN10300, is a program of this kind: `AW\KN7APP.BIN` on the card, listed under **Games** in the
menu. It takes no address from any build: it finds the firmware's task services, millisecond
counter, panel bitmaps, LED shadow and MIDI rings by signature, and runs on programs 893, 935, 941
and 942.

> **Status (2026-11-06).** The latest build, `KN7APP.BIN` `aafd752e…` (technics-anotherworld
> `fb549ff`), is staged on the owner's card. It adds three things to `7c2d2c06…`, so far checked in MAME
> only: the music at the Amiga original's tempo ([Sound](#sound)), a code wheel page in the help screen,
> and the code wheel setting taking effect at once ([below](#the-code-wheel)).
> - **On the unit.** The owner has played the builds of 2026-11-01 to 2026-11-04 on program 893 and
>   asked for changes from what was seen there, among them:
>   - the firmware's screen showing through while a part loaded;
>   - a flash of the next picture in the old colours at the splash's cuts;
>   - "Loading..." coming up only after a black screen;
>   - the PANEL MEMORY ring being green, where the parts list says amber.
>
>   The first session the game logged there, on 2026-11-01, found a bug in the VM
>   ([below](#replaying-a-session)).
> - **On the unit, 2026-11-06:** the owner played this build and reports that the credits' light show works
>   and the code wheel's retry is what they asked for. Both sessions the game logged are in technics-anotherworld
>   `kn7000/probes/sessions/2026-11-06-felipe-unit-1` and `-2`.

- **Memory.** Everything the game writes is in `0x502BA000`-`0x50379FFF`: code, VM state, the four
  pages, the current part's files. It holds one part at a time and loads each part's files from the
  card when the part starts, as the original engine does. It never touches IC23 or the user-memory
  pools: a build-time guard, run-time range checks and MAME write taps over whole sessions check
  it. The procedure for a run on the unit records IC23 before and after the session with the
  dumper's SURVEY2 pass, so that any change would show. Outside that range it writes the mailbox's
  request, the LCD's display memory and controller registers (put back at the quit), the firmware's
  LED shadow and MIDI IN 1 ring, three words of program 893's screen code (put back), its own files
  on the card, and the effects DSP's memory ([below](#sound)).
- **Starting.** The whole LCD goes black at the first call and "Loading... NN%" counts up in its
  middle, drawn from the first frame: the firmware search, the font and strings, the sound tables,
  then the game's samples on the effects DSP (the first time after power-on) and the first part.
  Each later part loads behind a black screen.
- **Controls.** Since the third round (2026-10-21) the game is played on the **keybed only**, or
  over MIDI IN 1 on channels 1-3; no panel button moves the player (the keys: the table below).
  A♭5 and B♭5 are the black keys either side of A5; B5 is no control (the owner's choice). With
  three keys down at once (an action key, a direction and up: run and jump) the keybed's scan
  matrix can lose A♭5 or B♭5. The panel's buttons are the port's own (second table).
- **Quitting.** Hold EXIT for 1.5 s. Started from the program menu, the game goes straight back to
  the menu: it reads and checks the menu's `KN7APP.BIN` and starts it through the menu's own
  trampoline, so no firmware message and no "Continue Next?" come between them (in MAME, 5.5 s from
  EXIT going down, the 1.5 s hold included). Started from the card's root, it ends with the
  firmware's message and "Continue Next?" as before.
- **The end.** After the credits the game's last words scroll up and the picture stops, as in the
  original. Then any key of the keybed, or 3 s of the still picture, starts the intro again.
- **The keybed's own sound.** The instrument plays its own voice for every key that steers the
  game. PART SELECT RIGHT 1 mutes those notes and brings them back: the game sends expression
  (MIDI CC 11) 0 on channels 1-3 (RIGHT 1, RIGHT 2, LEFT) through the firmware's MIDI IN path, and
  127 again when it leaves and at every new game. Expression is a live controller, so nothing is
  stored. The help screen's first page shows "KEYBED SOUND: ON" or "OFF". In MAME the firmware's
  expression byte goes to 0 and back, but the mute cannot be heard there: the overlay's tone
  generator ignores the level word the firmware writes for it.

| game   | key (or MIDI IN 1, channels 1-3) |
|--------|----------------------------------|
| up     | A♭5 or B♭5                       |
| down   | A5                               |
| left   | F5                               |
| right  | C6                               |
| action | C4 or any key below              |

| what         | panel                                                                                                |
|--------------|------------------------------------------------------------------------------------------------------|
| codes        | OTHER PART & FR: the level-code screen                                                               |
| help         | HELP; PAGE UP / PAGE DOWN turn pages; EXIT, HELP or any key returns; OTHER PART & FR the code screen |
| code wheel   | HELP at the code wheel question, or PAGE DOWN four times; TEMPO/PROGRAM turns the disk               |
| settings     | HELP, then PAGE DOWN three times ([below](#settings))                                                |
| sound        | PART SELECT RIGHT 2: the game's sound, DSP / tone generator / off ([below](#sound))                  |
| keybed sound | PART SELECT RIGHT 1: the instrument's own notes for your keys on / off                               |
| screen       | PAGE UP: 384x240 (the default); PAGE DOWN: 320x200                                                   |
| quit         | hold EXIT for 1.5 s                                                                                  |

The help screen has five pages: the controls, with the current sound mode and keybed sound; two pages of level
codes, in the game's order, each with where it starts, centred as one block, the second ending with the project's
address (`github.com/felipesanches/technics-anotherworld`); the settings; and the code wheel
([below](#the-code-wheel)). R1/R2 OCTAVE + / − and SUSTAIN do nothing
in the game, but the firmware still does their own job while it runs, and keeps the change. **Do not press
DISPLAY HOLD**: once in MAME it made the firmware repaint its screen and stop calling the game for good.

### The screen

- **Two resolutions** (since 2026-11-02). By default the game's four pages are **384x240**, the LCD's whole
  height, 6/5 of the original both ways, centred with strips at the sides. The polygons are computed and filled
  at that resolution, not enlarged afterwards. The text keeps its 8x8 glyphs, pixel for pixel, each placed at
  6/5 of where the game puts it. The twelve background bitmaps, which the game has at 320x200, come from the
  card at 384x240, enlarged at build time with Catmull-Rom interpolation restricted to the source's own nearby
  colours. **PAGE DOWN** switches to the original **320x200** in the middle of the LCD, PAGE UP back; the
  pages are converted on the spot.
- **8 bits a pixel through the look-up table.** The LCD controller
  ([S1D13806]({{ site.baseurl }}/kn7000-display-subsystem/)) shows a frame of the game's own at display memory
  `0x50000` at 8 bits a pixel through its 256-entry look-up table, as Pinball Fantasies does on the unit. Each
  byte is the page's colour index, so a palette change is 16 table entries, not a repainted window. A new
  palette goes into the table only after the page's pixels; when a quarter of the window or more changes at
  once, the game's 16 entries are black while the pixels are written. At the quit, or when the firmware stops
  calling the game, the controller's registers go back and the firmware's own screen shows again.
- **The ambilight.** The strips beside the window glow with the picture's colours, by palette changes alone.
  The border is drawn once per window size with table entries 16-255: 2 sides × 8 bands of rows × 15 levels of
  distance, dithered. For each picture shown, each band's colour is the average of the window's quarter on
  its side in those rows, smoothed, fading as the square of the distance to black at the LCD's edge. Only the
  entries that change are written.
- **The firmware's screen stays out.** Program 893 repaints its STYLE CONVERT screen at every converter call,
  which showed through during part loads on the unit. As Pinball Fantasies does, the game points ScreenProc's
  record in the firmware's view class table at a copy that answers the paint event without the wallpaper copy,
  and turns the firmware's drawing off at every yield (DrawEnable `0x5002A018`, `0x5002A01C`); both go back at
  the quit. On any other program build nothing is hooked. In MAME the intro's and the lake's loads stayed black
  and took 0.58 and 0.53 s instead of 0.98 and 0.93 s.

### Settings

The help screen's fourth page holds six settings, chosen with UP and DOWN and changed with LEFT and RIGHT. A
change applies at once. The game keeps them in `AWPREFS.CFG` in the card's root (16 bytes: "AWP1", then one byte
a setting), reads it at the start and writes it after a change, at a call with no panel button down and no part
loading, or at the quit.

| setting       | values                         | default | what it does                                                                        |
|---------------|--------------------------------|---------|-------------------------------------------------------------------------------------|
| resolution    | 384x240, 320x200               | 384x240 | the display mode the game starts in                                                 |
| ambilight     | on, off                        | on      | the glow in the strips beside the picture                                           |
| light scatter | short, medium, long, very long | long    | how far the glow reaches into the strips                                            |
| keybed sound  | on, off                        | on      | the instrument's own notes for the keys that steer the game                         |
| LED effects   | on, off                        | on      | the panel LEDs following the game ([below](#the-panels-leds))                       |
| code wheel    | off, on                        | off     | the original game's copy protection ([below](#the-code-wheel))                      |

### The code wheel

With the setting off, the game starts as the KN5000 port does: part 0x3E80's logo and credits, with the variables
the copy protection would set (0xBC, 0xC6, 0xF2) already set. With it on, the game starts where the DOS game does:
part 0x3E80 from its beginning, whose thread 20 asks for the three symbols at a position of the code wheel that came
with the game, entered with the game's own controls. A right answer sets those variables by the game's own code and
goes on to the logo and the intro. A wrong one shows the game's ERROR page, where the DOS game stays for good; here,
3 s later, the part starts again with a new random seed and asks for another position (`src/interp.s` WheelRetry,
since 2026-11-05). In MAME, two wrong answers in a row each showed ERROR, and the question came back 3.20 and 3.18 s
later, the second time for position K14.

Since 2026-11-06 the setting takes effect at once until play begins. At the question, its ERROR wait, the logo or
the intro, turning it on asks the question, with a new random seed; turning it off at the question goes on to the
logo. Once play has begun nothing restarts, and the row reads "ON, next start" or "OFF, next start". A restart is a
`G` record in the input log, so replays repeat it. In MAME, `probes/cnv/run_wheelnow.sh` passes its 5 checks.

**The code wheel page.** The help screen's fifth page is the code wheel that came with the game, drawn from
`AnotherWorld_VMTools/aw_codewheel.svg` by `tools/codewheel_render.py` into five files on the card
(`AWWH0.AW`-`AWWH4.AW`, 55,624 bytes). HELP at the question opens this page; elsewhere HELP opens the first page
and PAGE DOWN reaches it. Each step of the TEMPO/PROGRAM wheel turns the upper disk to the next or previous of
the 20 numbers, in 280 ms, eased; steps taken during a turn add up. The numbers' angles are measured from the
drawing (17.51° to 18.35° apart, not even 18° steps). The game takes the wheel's steps from the panel's receive
ring before the firmware does, so the tempo does not change; a step the firmware takes first is undone with one
the other way. The disk is rotated as it is drawn: the nearest texel while turning, bilinear at rest, writing only
the LCD words that changed. The page borrows VM pages 2-3, LUT entries 16-255 and the 8-bit frame while it shows
and gives them back unchanged. In MAME (`probes/cnv/run_wheel.sh`, 11 checks pass) a picture during a turn takes
24.4 to 68.9 ms (median 45.5) and one at rest about 364 ms; all 13 pictures read from the LCD equal the renderer's.
The page shows its own drawing times on the instrument.

### The panel's LEDs

With the LED effects on, every LED of the panel goes dark once the firmware search is done, and from then on only
the game lights them. It writes the firmware's own LED shadow, so the firmware's 24 ms flush carries the pattern;
at the quit the LEDs go back to what the firmware had them showing. The shadow's address is known for programs
893, 935, 941 and 942; on any other build the game leaves the LEDs alone. The moments are recognised in the
game's own bytecode as it runs, by a sound and the thread or pc that plays it, a variable, a thread's pc, or a
palette, the signals found by logging the reference VM (rustyworld) over the same sessions:

| moment                                                          | LEDs                                                                                                                                |
|-----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| a guard's laser shot                                            | every red LED, 150 ms                                                                                                               |
| Lester's laser shot                                             | the red LEDs on the half of the panel he shoots towards, 150 ms                                                                     |
| the gun charging; the big ball                                  | the PANEL MEMORY ring pulses; twice as fast, with every green LED, for the big ball                                                 |
| a shield; the big blast                                         | a random 30% of the red LEDs for 150 ms; every LED while the blast shows                                                            |
| a skeleton exploding, a lamp holder shot down                   | every green LED (the PANEL MEMORY ring's too), 200 ms                                                                               |
| the gun recharging at a station                                 | the green LEDs blinking fast at random for 1.4 s                                                                                    |
| the waterfall; the lift's bouncing light                        | LEDs at random while the falls are on screen; a chase along the PANEL MEMORY ring following the light                               |
| the battle tank's panel                                         | its buttons and lamps mirrored on the panel's                                                                                       |
| a guard's red lamp (code TXHF); the guard under the glass globe | the red LATIN & WORLD LED blinking with it; PANEL MEMORY 1-4 following his reflection, and a sparkle for 1.8 s when the globe falls |
| a door blasted open (the corridor of code HBHK)                 | the green LEDs flash for 0.6 s at each panel a blast knocks out                                                                     |
| the intro's lightning and thunder; the lab struck               | every LED at each flash or loud clap; every LED blinking three times                                                                |
| the explosion in the lake                                       | every green LED, 300 ms                                                                                                             |
| the dragon spreading its wings (the end, code KRTD)             | the RHYTHM GROUP's red LEDs are its left wing, the SOUND GROUP's its right, lit column by column from the centre out as each opens  |
| the dragon flying away                                          | a wave along both wings with its wing beats, over fewer columns as it shrinks into the distance                                     |
| the credits                                                     | a light show over all 101 LEDs, stepping with the music (below)                                                                     |

**The credits' light show** (2026-11-05). Each LED is lit by where it is on the panel, as the MAME layout places it,
in six patterns that take turns, each lasting at least 4 s and changing on a note:
- a marquee: every third LED, one step at each beat of the bass and drums;
- rings from the centre: one further out at each bass note;
- sparkles: two random LEDs at each note, 250 ms each;
- two bouncing beams: the top rows' with the chords, the bottom rows' the other way with the bass;
- a checkerboard swapping with the bass and drums;
- a meter from the centre out, full at each bass note and falling back in 0.25 s.

The music ends about 11 s before the credits do. From 1 s after the last bass or drum note, the show keeps its own
beat, a step every 0.3 s. Over the credits of the same replayed session in MAME (`probes/finalecheck.py`):

| over the credits             | the blinking before (2026-11-04) | the light show |
|------------------------------|----------------------------------|----------------|
| LEDs lit at some frame       | 59 of 101                        | 101 of 101     |
| different on-off timelines   | 4 (four groups)                  | 101            |
| longest with no LED changing | 10,078 ms (dark after the music) | 976 ms         |

### Replaying a session

Every game keeps an **input log** (since 2026-11-01): everything the VM was given from outside, frame by frame,
the input mask, the music's sync marks and the parts asked for. It is written to the card's root as `AWIN00.BIN`,
`AWIN01.BIN`, ... (8 KB each), between part loads and at the quit. The VM is otherwise deterministic, so a session
played on the instrument can be played again exactly in MAME and in the reference VM (rustyworld), and the two
compared frame by frame, page and variables.

The owner's first logged session (2026-11-01: 1,346 frames, the splash, the intro, a code, part 0x3E86 until the
hero died) differed from rustyworld from frame 1,143 on: a black bar in the wrong room. The first variable to
differ was 0x4B, and rustyworld's opcode trace showed a SHR of 0x8000 by 6. The port shifted arithmetically, the
original's engine logically. With SHR fixed, the replay matched rustyworld on all 1,346 frames and all 256
variables at every frame. The LED effects above are checked the same way: in MAME, by replaying a logged session
with an LED log and comparing it with the reference VM's events of the same session.

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
samples on the **effects DSP**, the **tone generator** over MIDI, and **off**. The key works inside
the help screen too, whose first page names the current mode at once ("NOW: DSP SAMPLES", "NOW:
TONE GENERATOR", "NOW: OFF"), with "NO DSP n" when the DSP was given up. The game starts in the DSP mode when it could set the DSP
up, and in the tone generator's otherwise. The DSP mixer's output gain is 2 since 2026-11-02 (it was 128,
36 dB louder), ProTracker's value: with 128, ProTracker on the owner's unit was comfortable only at the bottom of
MAIN VOLUME's travel. In every mode the music player runs and writes the
**sync marks** the intro reads (variable `0xF4`), so the intro's scenes follow the music, as in the
original, whether the sound is on or off.

**The music's tempo** (2026-11-06). A row of the module lasts what it does on the Amiga original, whose player
loads the module's delay into CIA-A timer A and plays a row every sixth interrupt: 6 × delay / 709,379 s, 132.79 ms
for the intro's module. The port had used rawgl's formula, 0.9 % faster. On the owner's unit the intro's music
still runs ahead of its picture: in a session of 2026-11-06 the frames took 17.7 % longer than the game asked for
(110.0 s for 93.5 s by the countdown), so the countdown's loop began 2.7 s before "THE EXPERIMENT WILL BEGIN"
came up. The game can only cut scenes short when the music is ahead, never wait for it. rawgl, Sanglard's
interpreter and rustyworld time each frame as if drawing were free, which brings their picture to the countdown
10 to 12 s before the music, so none of them settles the question; the Amiga original measured in an emulator
would. Evidence: technics-anotherworld `kn7000/probes/MUSIC-TIMING.md`.

#### The DSP mode: the game's own samples

> **On the instrument (2026-10-21, `KN7APP.BIN` `a2fbbaa6…`, program 893).** By the owner's
> report the sounds play perfectly, with REVERB on and with REVERB off (on is a little louder),
> at about a piano note's level. Nothing was garbled or stuck, and the reverb and the chorus came
> back after quitting. The first load of the sounds felt slow. The builds the owner has played
> since 2026-11-01 carry the coded bank (below); its load time on the unit has not been measured.

The tone generators play only their wave ROMs, so the game's own sounds have to come from the
effects DSP. The game puts a sample mixer of its own into the DSP's running kernel, as
[DSPTONE]({{ site.baseurl }}/kn7000-effects-dsp/#dsptone-iteration-1-a-tone-and-a-sweep) did,
through the firmware's own host-port routines.

- **The bank, once per power-on.** The 93 sounds the game plays, 684,980 samples, go into the
  DSP's SDRAM at the first start after power-on; "LOADING ANOTHER WORLD: SOUNDS" and the load bar
  show while it runs. Since the third round the bank is **coded losslessly** (Rice-coded, each
  sample against the one before) into 14 card files of 431,724 bytes; the bank itself is 686,304
  bytes, and the 93 packed files it replaced held 574,084. The DSP
  decodes it into SDRAM itself, then computes a checksum of what it wrote, and the game uses the
  bank only when that checksum is the one the build recorded. The first load went from 25.9 s to
  **11.6 s in MAME**. On the instrument it should take about 9.5 s, against about 22 s for the
  build before by the same estimate (from the unit's handshake rate, one DSP frame each; not a
  measurement). A marker left in DSP memory lets every later start have the DSP check the bank (0.4 s
  in MAME) instead of sending it again.
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
