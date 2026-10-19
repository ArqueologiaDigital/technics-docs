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
1. Searches the program flash for the firmware routines it needs. It finds them by their code, or,
   for the file routines, also by the shape of the firmware's table of them.
2. Fills a table of services for the application: file open, read, write and close on the SD card,
   raw sector access, folder creation, the build numbers, and text drawing. Only file access is
   required; the application works around anything else that is missing.
3. Reads `C:\KN7APP.BIN` and checks its header and CRC-32.

From then on it passes every converter call to the application. The floppy never needs to change:
a new version of the dumper, or any other application, is just a new `KN7APP.BIN` copied to the
card from a computer.

## Using it

**For a first run, use the SAFE build** (`build/safe/KN7APP.BIN`, shown as "KN7000 ROM DUMPER 1.0
SAFE"). It dumps only the program flash, the table flash and IC21: plain reads of memory the
firmware itself runs from. It writes ordinary files to the card's root folder and nothing else:
no folder, no long names, no raw sector access. That is about 10 MB.

**Then the IC19 build** (`build/ic19/KN7APP.BIN`, "KN7000 ROM DUMPER 1.0 IC19") dumps the picture
window alone, 8 MB, the same way. The firmware's own picture code addresses `0x57800000`, but the
window's extent was an assumption, so it got a pass of its own once the first was safe on a computer.
On the real instrument the window turned out to hold one 2 MB image four times: the
[100 Slide Show pictures]({{ site.baseurl }}/kn7000-picture-rom/).

**Then the WAVE build** (`build/wave/KN7APP.BIN`, "KN7000 ROM DUMPER 1.0 WAVE") dumps the four wave
ROMs alone, the same way, 64 MB. On the owner's instrument it read all four twice, byte-identical,
and each chip's byte sum was exactly the one the firmware's own WAVE ROM test expects (2026-10-19).
See [what the tests can show](#what-the-tests-can-and-cannot-show).

**Then the SURVEY build** (`build/survey/KN7APP.BIN`, "KN7000 ROM DUMPER 1.0 SURVEY") looks for the
rhythm ROM, whose CPU address nobody knows.

- **Where the firmware looks.** At every power-on it compares 16 bytes against "Technics Rhythms"
  at `0x48010000`, `0x40610000`, `0x40010000`, `0x54E10000` and `0x40810000`. If none matches, it
  uses `0x54E00000` without checking. Builds 893 and 941 use the same list.
- **What the survey reads.** The two whole regions those addresses lie in, as six 8 MB files,
  48 MB in all:
  - CS0, `0x40000000`-`0x40FFFFFF`;
  - CS5, `0x54000000`-`0x55FFFFFF`.

  The first address is the table flash, and is already dumped. Table 80 has no header there.
- **What `find_rhythm.py` does with the files.**
  - It finds the header.
  - It repeats the firmware's own checksum over the data behind the header (`StyleResourceVerify`).
  - It reads the RHYTHM number the SOFT VERSION screen would show.
  - It compares the data with the truncated copy of the header that table 84 carries.
- **What it found on the owner's instrument (2026-10-19).**
  - **IC18 answers on CS0** at `0x40000000`–`0x403FFFFF` and repeats at `0x40400000`. Its address
    pins take A1–A21, and its top pin is set by jumper JP7, so the CPU sees 4 MB of the 64 Mbit chip.
  - **The firmware's own check passes.** The header sits at `0x40010000`, the firmware's third probe
    address. Its checksum over 1 Mi words passes, it declares 220 styles, and the version string at
    the top is `"jkr_33.ssf"`, which SOFT VERSION shows as RHYTHM 33.
  - **The rest of the survey.** The windows show IC21 at `0x54800000` and IC19 at `0x55800000`,
    byte for byte the earlier dumps; everything else is open bus.
  - **IC18's first 64 KB is the boot ROM.** It is the code the CPU runs at reset, and it ends with
    `jmp 0x48400000`. It also holds the **flash updater**, with write windows for the program and
    table flash, IC21, the expansion boards, IC20 and the picture ROM.
  - **In MAME.** With the image mapped there, the firmware drops its "8 Beat 1" stub and shows the
    rhythm as "8Bt Standard".

1. Write the loader floppy (`kn7load_floppy.img`) to a 1.44 MB disk, and copy `KN7APP.BIN` to
   the SD card's root folder.
2. **DISK MENU** > **STYLE CONVERT**, choose `KN7LOAD.CNV`, **OK**.
3. The dumper shows each ROM's MAME name, the address range or port it is reading, and a progress
   bar, above the list of all ROMs with their CRC-32 as they finish.
4. When it says **Done**, the results stay on screen for 15 seconds. Then the firmware asks
   "Continue Next?": **NO** leaves, **YES** dumps again.
5. On a computer, `C:\KN7DUMP` holds the files under MAME's names, plus `DUMPLIST.TXT`. That lists
   each file's size, CRC-32 and byte sum, and what the loader found in the firmware. For a wave ROM
   it also gives the sum the firmware's own WAVE ROM test expects, so a bad wave dump shows up on the
   instrument already (`[SUM?]`).

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
| `c3cbmd000098.ic19`                            | CPU `0x57800000`–`0x57FFFFFF`: picture ROM (2 MB, 4 copies)       | 8 MB       |

- **Names.** The program and table names follow the driver's pattern, filled in with the build
  numbers the firmware reports on its SOFT VERSION screen: `…_v1.6_b941`, `…_b84` on build 941,
  and `…_v1.3_b893` on the owner's instrument. IC21's whole chip has no file name in the driver;
  the driver's `01ctmini.ic21` is the part of it from `0x20000` on.
- **Wave ROMs.** These are not on the CPU bus. They are read exactly the way the firmware's own
  service-mode WAVE ROM test reads them, through each tone generator's test latches, 16 MB per chip.

**Other parts worth dumping**, as far as we know the hardware:
- **IC18, rhythm data** (`c3cbnd000046.ic18`): found and read by the SURVEY build (above), at
  `0x40000000`.
- **IC23, the 256 KB battery-backed SRAM** at `0x44000000`: the user's panel memories and
  settings. It is user data, not a ROM, and has no MAME file, but it could be added.
- **Not readable from the main CPU:** the SD sub-CPU's flash (IC414), the panel controllers' mask
  ROMs, and the effects DSP, which has no ROM.

## How it stays safe

- **Memory.** It uses only the 192 KB the firmware sets aside for a style converter
  (`0x502B8000`–`0x502E7FFF`): loader, application, buffers and variables. Beyond that it writes
  only the converter mailbox, the LCD and the tone generators' wave-test latches.
- **No hard-coded firmware addresses.** The routines it calls are found in the program flash, by
  their code with only the operands that change between builds masked. A signature counts only if
  it matches exactly once. On builds 941, 942 (SP7001) and 935, every one does.
- **The firmware keeps running.** Every call does one 32 KB step and returns, so the firmware's
  main loop runs between steps. The file layer is switched to the SD card only during a step.
- **Long file names.** The firmware's FAT library writes 8.3 names only. The dumper writes
  `PRGEVEN.BIN` and so on, then rewrites its own folder's directory cluster with VFAT long-name
  entries in front of the unchanged 8.3 entries. It reads the cluster back to check it. It touches
  nothing else, and does nothing if the folder holds other files. `fsck.fat` finds no errors on a
  card written this way.

## Made for firmware nobody has dumped

It was made for an instrument running a build nobody had dumped. So the dumper never stops because
something looks unfamiliar; it writes down what it finds.

- **File access has two independent sources.** The firmware keeps its file routines in a table:
  eleven records of three code pointers, one each for the floppy, the SD card and a third backend.
  The loader finds that table by its shape alone, with no code signature: pointers into the program
  flash, two columns each in ascending order within 64 KB, three columns that do not overlap. That
  shape occurs exactly once in builds 941, 942 and 935. It even occurs in the surviving upper half
  of 929, which has none of the routines' code. Failing that, the loader looks for the dispatcher
  routines by their code.
- **Everything else is optional:**

  | when the loader does not find  | the dumper                                                          |
  |--------------------------------|---------------------------------------------------------------------|
  | raw SD sector access           | keeps the 8.3 names (`PRGEVEN.BIN` ...); `DUMPLIST.TXT` maps them   |
  | the folder routines            | writes into the card's current folder instead of `KN7DUMP`          |
  | a build number                 | names the files `…_bunknown…` and shows `?`                         |
  | the kernel's millisecond clock | holds the result screen about 15 s by a delay loop instead          |

- **What it reads is never judged.** Each ROM is written as it comes. A wave ROM whose byte sum is
  not the one the firmware's own test expects is marked `[SUM?]`, but still written. The release
  byte goes into the file names as it is.
- **A file that cannot be written** is marked `[FAIL]`, and its error code goes in `DUMPLIST.TXT`.
  The dump goes on with the next ROM.
- **Only one case writes nothing:** neither the file table nor the file routines found. Then the
  loader cannot even read `KN7APP.BIN`, and says so on the screen.

## What the tests can and cannot show

- **Program, table and IC21:** strong. MAME's hashes for these come from real chips, so a dump that
  matches them is right.
- **Wave ROMs:** weak in MAME. The real chips are undumped, so MAME was given random test data,
  and MAME's handler for the wave port is ours, written from the same reading of the firmware's
  WAVE ROM test as the dumper. A match shows the dumper and that model agree: every bank and word
  read, the files complete. It cannot show that the real tone generator answers the same way.
  - On the instrument, each chip's byte sum is compared with the sum the firmware's own test
    expects. A match shows every byte of the chip was read.
  - A sum does not depend on order, so the order of the words, and of the two bytes in each word,
    had to be checked on the real data.
  - **On the real instrument (2026-10-19):** all four sums matched, in two identical reads. The
    data are 16-bit samples, stored low byte first:
    - neighbouring samples correlate at about 0.85 when read low byte first, and 0.07 byte-swapped;
    - each tone generator's Y and X ROMs are the even and odd samples of one stream, aligned word
      for word;
    - excerpts show instrument tones.

    Whether waveforms start where the tone tables say is not yet checked. A permutation of whole
    banks would not show in any of these tests.
- **Picture window:** none in MAME, where the test served data at exactly that address. On the
  real instrument the read speaks for itself: a directory and 100 JPEGs that all decode, exactly the
  100 the firmware's picture code accepts ([Picture ROM (IC19)]({{ site.baseurl }}/kn7000-picture-rom/)).

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

All 11 files matched, about 74 MB, in about 11 minutes of emulated time, boot included. The SAFE
build's five files also matched at full size, in about two minutes, and the IC19 build's 8 MB
file in under two. These final runs used the very files handed over for the first run on the
instrument.

The fallbacks were tested by switching parts of the firmware search off:

| switched off                               | result                                                               |
|--------------------------------------------|----------------------------------------------------------------------|
| the file table search                      | the file routines found by their code; all files match               |
| everything optional, file routines by code | the file table alone; 8.3 names in the root, `_bunknown`; all match  |
| the kernel clock                           | all match; the screens held about 15 s by a timed delay loop         |
| both ways to the file routines             | nothing written; the loader says what it found and why it stopped    |

Upstream MAME maps the wave ports the other way round from the firmware: its `0x98050000` reads
`waveform_sub_*`, while the firmware's test screen calls that port the MAIN tone generator with
IC203/IC204. That is a driver issue for a later fix; the dumper follows the firmware.

## Limits

- **Run once on a real instrument so far (2026-10-19).** The owner's KN7000 runs **PROGRAM 893 /
  TABLE 80**, which had never been dumped. The SAFE build found everything it looks for in 893 and
  wrote all five files intact. The table flash came out byte-identical to SP7001's table 83, apart
  from the build digit and the data the SP7001 adds at the end. The IC19 build then read the picture
  ROM intact (CRC-32 as the instrument computed it), and a second IC19 read was byte-identical to
  the first. A second run of the SAFE build was byte-identical too: every file, and the
  instrument's manifest.
- **Without file access** (no file table and no file routines found in some other build), the
  loader cannot read `KN7APP.BIN`; it says so, and nothing is written. Getting past that would take
  an SD card driver of our own, which is not written: it could not be checked in MAME first.
- **Time.** About 74 MB go to the card. In MAME that takes about 11 minutes of emulated time; on
  the instrument it depends on the card.
- **Do not play during the dump.** The wave ROMs are read through the tone generators' test mode.

## Sources

- [`technics-roms-disasm`](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/kn7000), `kn7000/tools/cnv_romdump/`:
  - the loader, the dumper, their README;
  - the firmware search run over every program image (`find_fw.py`);
  - the probes behind the design (`probes/`);
  - the end-to-end test (`test/run_test.sh`, `prefill.lua`, `verify_dump.py`).
- `notes/wave-rom-port.md`: the wave ROM test protocol and the inventory of the other parts.
- [Your Own Code from a Floppy (.CNV)]({{ site.baseurl }}/kn7000-cnv-homebrew/): what a converter
  gets.
- [Style Converter (.CNV)]({{ site.baseurl }}/kn7000-style-converter/).
