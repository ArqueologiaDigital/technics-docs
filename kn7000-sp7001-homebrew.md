---
layout: page
title: "KN7000 Custom SD Apps (SP7001 .XAP)"
permalink: /kn7000-sp7001-homebrew/
---

# Writing custom KN7000 apps that load from the SD card

On a KN7000 running the [SP7001 "SD PLUG-iN" firmware]({{ site.baseurl }}/kn7000-sp7001-firmware/)
(program 942 / table 83; MAME `kn7000 -bios sp7001`), the instrument loads program code from the
SD card and runs it on its own CPU — that is what the product was for. This page records how that
loading works, what a custom app can call, a toolchain for building one, and the first demo built
with it: an **uptime clock**. It is the KN7000 counterpart of the KN5000's
[HD-AE5000 extension-ROM homebrew]({{ site.baseurl }}/hdae5000-homebrew/).

> **Status (2026-10-16).** Custom apps run: the uptime-clock demo
> (`kn5000_homebrew/demos/kn7000_clock`) works in MAME, alongside the SP7001's own SD features, and
> loading a modified `BASEEXT.XAP` was also confirmed by the project owner. It has not been tried on
> an instrument yet. There is no C compiler for the MN10300 yet: apps are hand-written assembly.

![The uptime clock in the bottom-right corner of the SP7001 main screen, in MAME]({{ site.baseurl }}/assets/images/kn7000-uptime-clock.png)
*The uptime clock (bottom right) over the SP7001 main screen in MAME, 35 seconds after power-on.*

## How the firmware loads an app

The resident SP7001 plug-in (in table flash) has a loader, `KssPluginLoad` (`0x483EEAA9`). Given a
plug-in id it:

1. opens `A:\<name>.XAP` on floppy, or `<dir>\<name>.XAP` on the SD card (the SP7001 setup installs
   the base plug-in at `C:\TECHNICS\DATA\BASEEXT.XAP`);
2. **rejects a file larger than `0x1D000` bytes**, then reads exactly `0x1D000` bytes to the fixed
   work-RAM address **`0x5029B000`**;
3. **calls the first byte** with the entry contract below;
4. checks the plug-in id and the compile id the code returned (`0x3F47B8C6` for `BASEEXT.XAP`),
   stores the returned object in its handle table at `0x50299ED0[id]`, and marks the plug-in loaded.

The base plug-in (id 3) is loaded by `Ap_Ce_StartUp` the first time the **SD card screen** is
opened (the orange SD CARD button), once per power-on, and before any activation check.

## The `.XAP` file format

A `.XAP` is a **flat absolute image linked for `0x5029B000`**, at most `0x1D000` bytes, entered at
offset 0; it has no magic. The stock `BASEEXT.XAP` is `0x1D000` bytes: code `0x00000`–`0x1321D`,
initialised data to `0x16B4B`. Its init clears its variables up to `0x502B4D78` (file `0x19D78`);
everything from there to the end of the file is `0xFF` and never addressed — free room for an
add-on.

### The entry contract (`XapEntry`, offset 0)

| register | in                                               | the app must, on return                     |
|----------|--------------------------------------------------|---------------------------------------------|
| `a0`     | the MILK **framework object** (`*(0x50299298)`)  | return in `a0` its **plug-in object**       |
| `a1`     | a context pointer (`0x502992E4`)                 | —                                           |
| `d0`     | `&compile_id`                                    | `*d0` = compile id (the base's is checked)  |
| `d1`     | `&plug_in_id`                                    | `*d1` = plug-in id (the base plug-in is 3)  |

The plug-in object is a table of method pointers that the SP7001 screens call: about 50 different
slots on the base plug-in (`Ap_CE_Main`, `Ap_Ce_StartUp`, `Ap_Ce_JukeBox`, …). A missing method falls
back to a resident stub that opens an error box. So an app that **replaced** `BASEEXT.XAP` would
have to implement those methods; an app that **rides along** with it does not. The demos use the
second way: they keep the stock plug-in and add a module to its free tail.

## What an app can call

Two interfaces, both found in the firmware:

- **The plug-in export table** (program 942, `0x487B1BB8`): 231 services exported by name, among
  them the micro-ITRON task calls and helpers. An app built for program 942 can call them at their
  addresses. Those used so far:

  | service        | address      | call                                  | notes                                                      |
  |----------------|--------------|---------------------------------------|------------------------------------------------------------|
  | `cre_tsk_X`    | `0x48585D42` | `d0` = task id, `a0` = `&T_CTSK`      | `T_CTSK`: exinf, attribute, entry, priority (16-bit), stack size |
  | `sta_tsk`      | `0x4C03DCD3` | `d0` = task id, `d1` = start code     |                                                            |
  | `dly_tsk`      | `0x4C03E295` | `d0` = milliseconds                   | waits on the kernel tick, yielding to tasks of the same priority |
  | `GetVRAMAddr`  | `0x48585C7A` | → `a0` = `0x500D4090`                 | the first of the two draw planes (see below)               |
  | `GetTimBase`   | `0x48585C9E` | → `d0` = `(0x50151C0C)` low 16 bits   | a **2 ms** counter (measured 499.8 counts/s)               |

- **The MILK framework object's method table**: `framework+0x1C` points at a static method table
  at `0x487280D0` (`RegisterObjectTable` `+0xEC`, `SendEvent` `+0x108`, `PostEvent` `+0x10C`,
  `RegisterTitle` `+0x27C`, `SetVisible` `+0x2A4`, `GetViewInstance` `+0x2D4`, `SetApTimer` `+0x3EC`,
  …), the way `BASEEXT.XAP` itself drives the UI. Building screens this way needs the widget tables
  decoded; see [SP7001 Firmware]({{ site.baseurl }}/kn7000-sp7001-firmware/#baseextxap).

Facts an app needs about the system, measured or read in build 942:

| what                  | where                   | detail                                                                                                                                                    |
|-----------------------|-------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| time since power-on   | `0x500D3C68`            | the kernel's 32-bit millisecond counter, incremented by `KernelTickHandler` at **1 kHz** (measured 999.5/s); starts about 0.27 s after power-on           |
| LCD frame             | `0x9CE00000`            | 640×240 RGB565, 1280 bytes per row, presented as is                                                                                                       |
| how the frame is made | compositor `0x48414D40` | redraws one rectangle at a time from the two draw planes, so pixels written to the frame stay until the firmware repaints that spot                       |
| tasks                 | TCB table `0x50380000`  | 11 slots (ids 0–10); at boot ids 0–4, 7 and 8 exist, 5 and 6 are created on demand, 9 and 10 are free and no task-creation call passes them as a constant |
| task priority         | all firmware tasks      | priority **3** (attribute 1), stacks `0xC00`–`0x6000`                                                                                                     |

More on the tasks: [Tasks & Scheduler]({{ site.baseurl }}/kn7000-task-scheduler/#kernel-tasks-and-the-tick-build-942);
on the compositor: [Display]({{ site.baseurl }}/kn7000-display-subsystem/#the-compositor).

## Toolchain

The `kn7000/` tree of the [`technics-roms-disasm`](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/kn7000) repository provides:

| tool                 | what it does                                                                                                                              |
|----------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| `tools/xapasm.py`    | two-pass MN10300 assembler for new code: labels are CPU addresses usable before their definition, operands take expressions               |
| `tools/xap_addon.py` | copies a module into `BASEEXT.XAP`'s free tail (default `0x502B6000`) and replaces `XapEntry`'s first two instructions with a `jmp` to it |
| `tools/sd_splice.py` | overwrites a same-size file in place on a FAT SD-card image (`C:\TECHNICS\DATA\BASEEXT.XAP`)                                              |

Contract for an add-on module: its first byte is the hook. It gets control exactly as `XapEntry`
would (arguments in `d0`, `d1`, `a0`, `a1`); it may set itself up, must leave those registers and
the stack as it found them, then run the two displaced instructions (`movm [a2,a3],(sp)`,
`add -8,sp`) and `jmp 0x5029B005`. The vendor plug-in is never redistributed: the build adds the
module to the user's own copy, extracted from the SP7001 update disks.

To run under MAME: `kn7000 -bios sp7001 -harddisk <card>`, then press the orange **SD CARD**
button (input "SD CARD LOAD (SW7)"). A clean MAME build needs `-str N` rather than
`-skip_gameinfo` for an `-autoboot_script` to start.

## Reading files from the SD card

The firmware exports a C-like file API to plug-ins. It is available both by name in program 942 and
as methods on the framework object (`framework+0x2E1C` slots `+0x2D0`/`+0x2D8`/`+0x2DC` are the same
three functions):

| call                                                       | address      | returns                    |
|------------------------------------------------------------|--------------|----------------------------|
| `fopen_api(a0 = path, a1 = mode)`                          | `0x48585E2A` | `a0` = FILE*, 0 on failure |
| `fread_api(a0 = buffer, a1 = FILE, d0 = size, d1 = count)` | `0x48585E50` | `d0` = bytes read          |
| `fclose_api(a0 = FILE)`                                    | `0x48585E65` | —                          |

This is exactly how the firmware loads `BASEEXT.XAP` itself. Three things matter, each learned by
getting it to work in MAME (and each a pitfall that silently fails or faults otherwise):

- **Call it from the hook, not from a task you created.** On the firmware's own loading task (where
  the hook runs) it works; called from a task made with `cre_tsk_X` it faults, because that task has
  no per-task C-runtime. So do the loading in the hook, before handing control to your task.
- **Write the path with single backslashes**, e.g. `fopen_api("C:\TECHNICS\DATA\MYFILE.BIN", "rb")`.
  (`xapasm`'s `.asciz` does not interpret escapes, so one `\` in the source is one byte.) The SD card
  is drive `C:`.
- **Read into work RAM (`0x50000000`–`0x503FFFFF`), not the `0x44000000` window.** The SD transfer
  cannot target the external-memory window; a `fread_api` into it returns nothing. Read with
  `size = 1`, `count = N` to get up to `N` bytes; copy on to `0x44…` with the CPU if you need the
  larger window. This is what lets an app load data far bigger than the `0x1D000`-byte plug-in file —
  the route the [Another World port](#a-larger-example-another-world) takes for its game data.

## Demo: an uptime clock
## Demo: an uptime clock

`kn5000_homebrew/demos/kn7000_clock` (about 1.2 KB of MN10300 assembly) draws how long the
instrument has been on, `HH:MM:SS`, in a 149×29 box in the bottom-right corner of the LCD, on every
screen, five times a second:

1. The hook calls `cre_tsk_X` for id 10 (falling back to 9) with priority 3 and a `0xC00` stack —
   the firmware's own conventions — then `sta_tsk`, and resumes `XapEntry`. The SD card features
   work as before.
2. The task reads `0x500D3C68`, divides it into hours, minutes and seconds, draws the box straight
   into the frame at `0x9CE00000` from a pre-scaled 5×7 font (every pixel written once, so no
   flicker), and calls `dly_tsk(200)`.

The KN7000 has no real-time clock, so time since power-on is what it can show. The clock appears
the first time the SD card screen is opened (when the plug-in loads); hours wrap at 100.

`make test` checks it in MAME: it presses the SD CARD button, then reads the eight digit cells
back out of the frame. On 2026-10-16 the task took slot 10 and the digits read `00:00:19`,
`00:00:27` and `00:00:35` at 20, 28 and 36 s of emulated time — each the value of the kernel
counter at that moment.

    make -C technics-roms-disasm/kn7000 baserom/sp7001_baseext.xap
    make -C kn5000_homebrew/demos/kn7000_clock          # build/BASEEXT.XAP
    make -C kn5000_homebrew/demos/kn7000_clock card     # an SD-card image with it in place

## A larger example: Another World

The [Another World](https://en.wikipedia.org/wiki/Another_World_(video_game)) bytecode VM runs on
the KN7000 as a ride-along plug-in. It loads its game data from the SD card with the API above
and blits a 320×200 frame into the LCD. In MAME the intro and the lake are pixel-identical to the
reference VM, every part opens identically, and the game takes input from the keybed, MIDI IN 1
and the panel. There is no sound yet. Source: the `kn7000/` directory of the Another World
repository.

The same VM also runs on a KN7000 **without** SP7001, from a floppy, as a style converter:
[Your Own Code from a Floppy (.CNV)]({{ site.baseurl }}/kn7000-cnv-homebrew/).

## Limits and open work

- **No high-level toolchain.** A C toolchain would need an MN10300 LLVM/GCC target (the KN5000
  side has a TLCS-900 LLVM backend; the KN7000's CPU is different).
- **Screens of one's own** need the MILK widget tables decoded; until then a demo draws straight
  into the frame.
- **The plug-in's run-time objects.** About 700 of `BASEEXT.XAP`'s calls go through objects it
  creates, whose method tables are not mapped yet.

## Sources

- [SP7001 Firmware: What Changed, and the Plug-in]({{ site.baseurl }}/kn7000-sp7001-firmware/)
  (the loader, entry contract, export table, the framework-object method table).
- [SD PLUG-iN (SP7001)]({{ site.baseurl }}/kn7000-sd-plugin/) (the product).
- Disassembly ([`technics-roms-disasm`](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/kn7000), `kn7000/`): `KssPluginLoad` `0x483EEAA9`, `XapEntry`
  `0x5029B000`, `cre_tsk` `0x4C03D46B`, `KernelTickHandler` `0x4C02BB5F`, the compositor `0x48414D40`;
  the tick rates and the task table come from `notes/sp7001-probes/rate_probe.lua` in the same repository.
