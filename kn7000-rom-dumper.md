---
layout: page
title: "ROM Dumper (floppy loader + SD card)"
permalink: /kn7000-rom-dumper/
---

# Dumping a KN7000's ROMs with a floppy and an SD card

A ROM dumper that runs on the instrument itself, through the stock firmware's **STYLE CONVERT**, the
same door Technics' [style converters]({{ site.baseurl }}/kn7000-style-converter/) use. It needs
no SP7001, no opened case and no hardware: one floppy, made once, and an SD card. It writes every
ROM it can reach to the card, under the file names MAME's `kn7000` driver uses.

> **Status (2026-10-19): works in MAME.** Every file it writes matches: the program and table
> flash match MAME's hashes, and the undumped ROMs match the test data MAME was given. It has not
> run on a real KN7000 yet; see [the limits](#limits).

## Two parts: a loader on the floppy, the application on the card

| on the       | file          | what it does                                                                          |
|--------------|---------------|---------------------------------------------------------------------------------------|
| floppy       | `KN7LOAD.CNV` | finds the firmware routines it needs, loads `KN7APP.BIN` from the SD card, runs it    |
| SD card root | `KN7APP.BIN`  | the application, here the ROM dumper                                                  |

**The loader** is a style converter. On its first call it:
1. Searches the program flash for the firmware routines it needs, by their code.
2. Fills a table of services for the application: file open, read, write and close on the SD card,
   raw sector access, folder creation, the build numbers, and text drawing.
3. Reads `C:\KN7APP.BIN` and checks its header and CRC-32.

From then on it passes every converter call to the application. The floppy never needs to change:
a new version of the dumper, or any other application, is just a new `KN7APP.BIN` copied to the
card from a computer.

## Using it

1. Write the loader floppy (`kn7load_floppy.img`) to a 1.44 MB disk, and copy `KN7APP.BIN` to
   the SD card's root folder.
2. **DISK MENU** > **STYLE CONVERT**, choose `KN7LOAD.CNV`, **OK**.
3. The dumper shows each ROM's MAME name, the address range or port it is reading, and a progress
   bar, above the list of all ROMs with their CRC-32 as they finish.
4. When it says **Done**, the results stay on screen for 15 seconds. Then the firmware asks
   "Continue Next?": **NO** leaves, **YES** dumps again.
5. On a computer, `C:\KN7DUMP` holds the files under MAME's names, plus `DUMPLIST.TXT`. That lists
   each file's size, CRC-32 and byte sum. For a wave ROM it also gives the sum the firmware's own
   WAVE ROM test expects, so a bad wave dump shows up on the instrument already (`[SUM?]`).

## What it dumps

| file                                           | read from                                                         | size       |
|------------------------------------------------|-------------------------------------------------------------------|------------|
| `kn7000_program_even_v<release>_b<build>.ic17` | CPU `0x48400000`–`0x487FFFFF`, bytes 0–1 of each 32-bit word      | 2 MB       |
| `kn7000_program_odd_v<release>_b<build>.ic16`  | the same window, bytes 2–3                                        | 2 MB       |
| `kn7000_table_even_b<table>.ic17`              | CPU `0x48000000`–`0x483FFFFF`, bytes 0–1                          | 2 MB       |
| `kn7000_table_odd_b<table>.ic16`               | the same window, bytes 2–3                                        | 2 MB       |
| `custom_data.ic21`                             | CPU `0x96800000`–`0x969FFFFF`: the custom data flash, whole       | 2 MB       |
| `c3cbqd000002.ic203`, `c3cbqd000001.ic204`     | main tone generator's wave port `0x98050000`, select 0 and 1      | 16 MB each |
| `c3cbqd000004.ic207`, `c3cbqd000003.ic208`     | sub tone generator's wave port `0x98040000`, select 0 and 1       | 16 MB each |
| `c3cbmd000098.ic19`                            | CPU `0x57800000`–`0x57FFFFFF`: picture flash (window unconfirmed) | 8 MB       |

- **Names.** The program and table names follow the driver's pattern, filled in with the build
  numbers the firmware reports on its SOFT VERSION screen: `…_v1.6_b941`, `…_b84` on build 941,
  and `…_v1.3_b893` on the owner's instrument. IC21's whole chip has no file name in the driver;
  the driver's `01ctmini.ic21` is the part of it from `0x20000` on.
- **Wave ROMs.** These are not on the CPU bus. They are read exactly the way the firmware's own
  service-mode WAVE ROM test reads them, through each tone generator's test latches, 16 MB per chip.

**Other parts worth dumping**, as far as we know the hardware:
- **IC18, rhythm data** (`c3cbnd000046.ic18`, 8 MB): not dumped yet, because no CPU window for it
  is confirmed. That would have to be found first.
- **IC23, the 256 KB battery-backed SRAM** at `0x44000000`: the user's panel memories and
  settings. It is user data, not a ROM, and has no MAME file, but it could be added.
- **Not readable from the main CPU:** the SD sub-CPU's flash (IC414), the panel controllers' mask
  ROMs, and the effects DSP, which has no ROM.

## How it stays safe

- **Memory.** It uses only the 192 KB the firmware sets aside for a style converter
  (`0x502B8000`–`0x502E7FFF`): loader, application, buffers and variables. Beyond that it writes
  only the converter mailbox, the LCD and the tone generators' wave-test latches.
- **No hard-coded firmware addresses.** The routines it calls are found by their code, with only
  the operands that change between builds masked. Each must be found exactly once, or the loader
  says "Unsupported firmware" and does nothing. On every program image we have, each routine is
  found exactly once: builds 941, 942 (SP7001) and 935, and the surviving half of 929 for the one
  routine in that half.
- **The firmware keeps running.** Every call does one 32 KB step and returns, so the firmware's
  main loop runs between steps. The file layer is switched to the SD card only during a step.
- **Long file names.** The firmware's FAT library writes 8.3 names only. The dumper writes
  `PRGEVEN.BIN` and so on, then rewrites its own folder's directory cluster with VFAT long-name
  entries in front of the unchanged 8.3 entries. It reads the cluster back to check it. It touches
  nothing else, and does nothing if the folder holds other files. `fsck.fat` finds no errors on a
  card written this way.

## How it was tested

The test runs upstream MAME's `kn7000` with the loader floppy and a copy of the real KN7000's SD
card, with `KN7APP.BIN` added.

The wave ROMs are undumped, so MAME was given test data: its four wave ROM regions were filled with
seeded pseudo-random data. The picture flash window, which the driver does not map, answered with
the same kind of data.

The dumper ran through STYLE CONVERT like a user would. A script then checked every file on the
card:
- its long name is a ROM name from the driver;
- the program and table halves match the driver's CRC-32 and SHA-1;
- the custom data flash matches what the CPU reads there;
- the wave and picture files match the test data.

All 11 files matched, about 74 MB, in about 11 minutes of emulated time.

Upstream MAME maps the wave ports the other way round from the firmware: its `0x98050000` reads
`waveform_sub_*`, while the firmware's test screen calls that port the MAIN tone generator with
IC203/IC204. That is a driver issue for a later fix; the dumper follows the firmware.

## Limits

- **Not run on a real instrument yet.** The owner's KN7000 runs **PROGRAM 893 / TABLE 80**, which
  has never been dumped. The loader looks for its routines by their code rather than by address,
  so it may well find them in 893. If it does not, it says so and writes nothing.
- **Time.** About 74 MB go to the card. In MAME that takes about 11 minutes of emulated time; on
  the instrument it depends on the card.
- **Do not play during the dump.** The wave ROMs are read through the tone generators' test mode.

## Sources

- `kn7000_disassembly` (unpublished), `tools/cnv_romdump/`:
  - the loader, the dumper, their README;
  - the firmware search run over every program image (`find_fw.py`);
  - the probes behind the design (`probes/`);
  - the end-to-end test (`test/run_test.sh`, `prefill.lua`, `verify_dump.py`).
- `notes/wave-rom-port.md`: the wave ROM test protocol and the inventory of the other parts.
- [Your Own Code from a Floppy (.CNV)]({{ site.baseurl }}/kn7000-cnv-homebrew/): what a converter
  gets.
- [Style Converter (.CNV)]({{ site.baseurl }}/kn7000-style-converter/).
