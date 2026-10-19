---
layout: page
title: "Your Own Code from a Floppy (.CNV)"
permalink: /kn7000-cnv-homebrew/
---

# Running your own code on a stock KN7000, from a floppy

A KN7000 is known to run machine code from outside in two vendor-sanctioned ways. One is the
[SP7001 SD plug-in]({{ site.baseurl }}/kn7000-sp7001-homebrew/), which needs the SP7001 firmware.
The other is the [style converter]({{ site.baseurl }}/kn7000-style-converter/): DISK MENU >
STYLE CONVERT loads a `.CNV` program from a floppy and runs it on the main CPU. That one works
on the stock firmware (PROGRAM 941). Any MN10300 program linked to the converters' load address
can use it, not only a style converter.

The [Another World]({{ site.baseurl }}/another-world-vm/) VM runs this way: `AW.CNV`, on a
floppy with the original game data.

> **Status (2026-10-18): works in MAME on program 941.** The game loads from the floppy and the
> intro is pixel-identical to the reference VM. The keybed, the panel, quitting and playing again
> all work.
>
> **Not for a real KN7000 yet.** The game keeps its 1.7 MB of data in the `0x44000000` window.
> MAME maps 16 MB of RAM there, but on the real instrument that window is the 256 KB
> battery-backed backup SRAM, which holds the panel memories ([below](#limits)).

![Another World's intro, run from a floppy as a style converter, in MAME]({{ site.baseurl }}/assets/images/kn7000/another-world-cnv-intro.png)

## Playing Another World this way

1. Build the floppy (`make floppy` in the `kn7000/` directory of the Another World repository) and
   put it in the drive. In MAME: `make cnvrun`.
2. Press **DISK MENU**, then **STYLE CONVERT**. The list shows `AW.CNV`. Press **OK**.
3. A white bar fills as the 13 game data files are read and unpacked: about 75 seconds in MAME.
   Then the intro starts.
4. Play with the keyboard, MIDI IN 1 or the panel, as in the SP7001 build. **HELP** shows the
   controls.
5. **Hold EXIT for 1.5 seconds** to quit. The firmware shows a message box. Press EXIT, and it
   asks "Continue Next?". **YES** plays again at once; **NO** returns to the main screen.

![The firmware's "Continue Next?" screen after quitting the game]({{ site.baseurl }}/assets/images/kn7000/another-world-cnv-continue.png)

## What a converter gets

The [Style Converter]({{ site.baseurl }}/kn7000-style-converter/) page describes how the firmware
runs Technics' own converters. Another World and three small probe converters added what a
program of one's own needs to know (measured in MAME on program 941):

- **Where it runs.** The firmware zeroes `0x30000` bytes at `0x502B8000` and reads the file there
  whole. It then calls the first byte with `calls (a0)`, so the program starts with a normal
  function prologue.
- **When it runs.** The converter is called on the firmware's **main task**. That task also
  decodes the panel buttons and passes keybed notes to MIDI OUT.
- **It must return.** A converter that loops forever keeps running, even if it yields to other
  tasks, but no panel button and no keybed note gets through any more.
- **Request 5 parks the user interface.** On each return the firmware reads a request from the
  mailbox at `0x5031BC00`. Request 5, "show this text", keeps it on the converter's text screen.
  It calls the converter again about 20 times a second and ignores EXIT, while the panel and the
  keybed keep working.
- **A task of its own.** On its first call, the converter can start a task (`cre_tsk`, then
  `sta_tsk`, at priority 3, the firmware's own priority) and answer request 5 from then on. The
  task can run a game loop, read input and draw. The kernel does not time-slice, so the task must
  yield each frame with `dly_tsk`.
- **Input.** The panel's switch bitmaps, debounced and held, are in work RAM. Every keybed note
  goes to the MIDI OUT 1 transmit ring, and MIDI IN 1 bytes arrive in their own ring.
- **Display.** The parked screen does not repaint, so the task draws straight into the LCD frame
  at `0x9CE00000` (640×240, RGB565).
- **Files.** The firmware's own file routines can be called directly from the first call. AW.CNV
  reads 16 files from the floppy with them.
- **Quitting.** The task ends itself with `exd_tsk`, and the converter's next return answers
  request **0xFE**. The firmware stops calling and shows its message box, then "Continue Next?".
  YES calls the converter again without reloading it, so a program must expect to be started
  again with its variables intact. NO returns to the main screen.

Program 941's addresses (the SP7001 firmware, 942, has its own):

| what                                         | 941                                                                                           |
|----------------------------------------------|-----------------------------------------------------------------------------------------------|
| load address, zeroed area                    | `0x502B8000`, `0x30000` bytes                                                                 |
| mailbox (request byte, text from byte 1)     | `0x5031BC00`                                                                                  |
| `cre_tsk`, `sta_tsk`, `dly_tsk`, `exd_tsk`   | `0x4C03D0C8`, `0x4C03D8AB`, `0x4C03DD6F`, `0x4C03D5A1`                                        |
| open in the current folder, `fmmread`, close | `0x48531AC5`, `0x48532463`, `0x485323BC`                                                      |
| kernel millisecond counter                   | `0x500D3C58`                                                                                  |
| panel switch bitmaps                         | `0x5006BE50` + n (CPR_SEGn), `0x5006BE80` + n (CPL/CPC_SEGn); EXIT is `0x5006BE8B` bit `0x80` |
| MIDI IN 1, MIDI OUT 1 ring headers           | `0x5001F050`, `0x5001F864`                                                                    |

The RAM addresses are 942's minus `0x10`, as measured. The task services were paired with 942's
by the kernel routine each entry stub enters. The disassembly's ported symbols had named
`0x4C03D8AB` `ext_tsk`; it is `sta_tsk`, and the probes show it starting a task.

**One assembly pitfall.** On the MN10300, `call` stores the return address at the top of the
stack and does not move the stack pointer. A routine entered with `call X, 0, 0` that calls
another before making a frame of its own overwrites that address, and its return goes astray.
That hung AW.CNV's first unpacker, so the build now checks every routine for it.

**Parking without a repaint.** Request 5 makes the firmware repaint its converter screen. Its display
task also recomposes the LCD while the SD routines sleep, so a program that draws its own screen loses
it under request 5. **Request 1**, "copy four bytes and call again", parks the firmware just as well
and leaves the screen alone. An idle request-1 loop calls back much faster than request 5's ~20 times a
second. The [ROM dumper]({{ site.baseurl }}/kn7000-rom-dumper/) parks this way.

**A loader instead of one program per floppy.** The ROM dumper is split in two. `KN7LOAD.CNV`, on the
floppy, finds the firmware routines by their code rather than by address, so it is not tied to one
build. It loads the real application, `KN7APP.BIN`, from the SD card. A new application is then just a
file copied to the card.

## How Another World uses it

- **The program.** `AW.CNV` (13,840 bytes) is the same VM source as the SP7001 build, with a
  platform layer for 941 and an unpacker for the game's original packed data.
- **The floppy.** It holds `AW.CNV`, the original MS-DOS release's `BANK01`–`BANK0D` unchanged,
  and the font and string tables. It is built on a blank disk the KN7000 formatted itself, as
  every KN7000 image of the project is ([Floppy Disk Images]({{ site.baseurl }}/floppy-disk-images/)).
- **The first call** reads and unpacks the whole game, starts the game task and answers
  request 5. Later calls watch EXIT and answer request 5 until the player quits.

How it was checked, in MAME:
- **The game data.** After loading, the 1,730,376 bytes of resources in RAM are identical to the
  SD build's, and so are the font and string tables.
- **The intro.** All 2612 frames are identical to the reference VM (rustyworld), compared as for
  the SP7001 build.
- **A whole session.** A script checks the start, skipping the intro, the panel and keybed
  controls, quitting, YES and NO on "Continue Next?", and running AW.CNV again: 9 of 9 pass.

## Limits

- **The `0x44000000` window.** The game keeps its pages, resources and file buffer in this window,
  as the SD build does. MAME maps 16 MB of RAM there as a placeholder. The disassembly identifies
  it as the **256 KB battery-backed backup SRAM**, which holds the panel settings and PANEL MEMORY,
  and the firmware writes exactly its first 256 KB. On a real KN7000 the game's RAM is not there.
  If the address decoding is partial, its writes would overwrite the stored settings.
- **What a real-hardware build needs.** Build 941 leaves a converter about 928 KB of work RAM
  (`0x50298000`–`0x50380000`). That is not enough to unpack the whole game at once. It would
  have to load each part's data from the floppy when the part starts, as the original game does.
- **No sound**, as in the SP7001 build.
- **Load time.** About 75 s in MAME, reading and unpacking 1.15 MB from the floppy. Real-drive
  timing is unknown.

## Sources

- Another World repository, `kn7000/README-CNV.md` (the build) and `kn7000/probes/cnv/README.md`
  (the probes, their commands and results).
- `technics-roms-disasm`, `kn7000/`: `notes/style-converter.md` (the firmware side, and what a
  converter of one's own showed) and `tools/itron_stubs.py` (the task services).
- [Work RAM Map]({{ site.baseurl }}/kn7000-work-ram/) (what the firmware leaves free) and
  [Tasks & Scheduler]({{ site.baseurl }}/kn7000-task-scheduler/).
