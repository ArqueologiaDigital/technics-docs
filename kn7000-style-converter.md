---
layout: page
title: Style Converter (.CNV)
permalink: /kn7000-style-converter/
---

# Style Converter: loadable programs on a floppy (KN6000, KN7000)

DISK MENU > STYLE CONVERT turns other keyboards' styles into Technics styles. The conversion
code is not in the instrument. It comes on the **Style Convert Disk** (`scd6000` for the KN6000,
`scd7000` for the KN7000, both in the floppy software lists) as six small MN10300 programs, the
`.CNV` files, which the firmware loads into RAM and runs. Traced on 2026-10-18 from the KN7000's
PROGRAM 941 and the KN6000 program, the two disks, and one RAM read on a booted KN7000.
Details, addresses and scripts are in the [technics-roms-disasm](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/kn7000) repository,
`kn7000/notes/style-converter.md`.

## What is on the disk

| file                     | converts styles of                  | same on both disks?                  |
|--------------------------|-------------------------------------|--------------------------------------|
| `GEM_WS2.CNV`            | GEM (General Music) WS2             | identical                            |
| `GEM_WX2.CNV`            | GEM WX2                             | identical                            |
| `KORG.CNV`               | Korg i1 - i5 series                 | identical                            |
| `ROLAND.CNV`             | Roland                              | identical                            |
| `SOLTON.CNV`             | Solton                              | identical                            |
| `TECHNICS.CNV`           | Technics KN 800/770 and KN 1000/750 | two builds: 4 of 128 routines differ |
| `V1%0_.ver`, `V2%0_.ver` | nothing: a version tag              | same content, different name         |

The converters carry their own texts: 120 to 299 strings each. Among them are their disk
prompts ("Insert Style Disk of Korg i1 - i5 series"), file patterns such as `*.STY,***`, menu
texts and sixteen error messages. (This page said until 2026-10-24 that they contain no text;
that was wrong.) `ROLAND.CNV` is spelled `Roland.cnv` in the installer.

## How it works

- **A converter is a raw program.** It has no header and is linked to run at one fixed address,
  `0x502B8000`. Its first instruction branches to `main`; a few bytes of C start-up code clear
  and initialise its variables on the first call.
- **The firmware loads and calls it.** STYLE CONVERT lists `*.CNV` (with none, it asks you to
  insert the Style Convert Disk). It clears a 192 KB area at `0x502B8000`, reads the chosen
  file into it whole, and calls its first byte.
- **The converter never calls the firmware.** No call or jump in any of the six leaves the
  file. Every conversation goes through a small mailbox at `0x5031BC00`. The converter does one
  step, writes a request and returns. The firmware serves the request, writes `0xFF` ("go on")
  and calls it again. The converter keeps its place in a state variable of its own.
- **The requests are services the converter cannot do alone:**
  - list files by name pattern (`*`, `?`);
  - open, read, seek, tell, rewind and close the other keyboard's files, through the
    firmware's floppy file layer;
  - show a text or a choice on the converter screens.

  When it has finished, the firmware moves to the STORE screen to save the converted style. An
  error leads to its own screen.
- **The contract is all memory.** It consists of the load address, the mailbox and one
  "initialised" flag (`0x5031BBFE`), and both firmwares implement it with the same code. That is
  why five of the six converters are the very same files on the KN6000 and KN7000 disks.

Two special cases sit in the firmware itself:
- **The `.VER` file is read by its name.** `V1%0_` means "V1.0", with `%` standing for the
  second dot an 8.3 name cannot hold. Its content, a Cakewalk file header, is ignored. The
  KN7000 disk is V1.0, the KN6000 disk V2.0.
- **The Technics converter is recognised by name.** The firmware compares the chosen file's
  name with `TECHNICS`, kept in RAM, and treats it differently. It shows its own prompt, "Insert
  Style Disk of Technics KN 1000/750", and finishes along another path.

## The disassembly

All seven converters are disassembled, byte-exact, in the repository's
[`kn7000/src/cnv/`](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/kn7000/src/cnv);
`make verify-cnv` rebuilds each one from its source. The sources are complete: no file is
included as raw bytes, and every code byte is an instruction.

| converter           | bytes   | instructions | routines | of them, never called |
|---------------------|---------|--------------|----------|-----------------------|
| `GEM_WS2.CNV`       | 99,857  | 19,640       | 140      | 23                    |
| `GEM_WX2.CNV`       | 108,049 | 21,822       | 149      | 25                    |
| `KORG.CNV`          | 108,912 | 22,593       | 144      | 24                    |
| `ROLAND.CNV`        | 91,872  | 17,247       | 132      | 25                    |
| `SOLTON.CNV`        | 96,706  | 18,945       | 137      | 23                    |
| `TECHNICS.CNV` 6000 | 101,992 | 16,920       | 128      | 35                    |
| `TECHNICS.CNV` 7000 | 101,992 | 16,941       | 128      | 35                    |

What the disassembly shows:
- **A shared library.** 75 routines have the same code in all seven: the mailbox and error
  routines, the C string and memory functions, IEEE double arithmetic and byte-order helpers.
  Several are byte-identical to routines of the firmware's own library.
- **The file is laid out by its C start-up code.** Code comes first, then constant data and
  strings, then the image of the initialised variables. Zeros follow, up to the end of the
  file: the room those variables are copied into, and the uninitialised ones. So the firmware's
  load is a plain copy of the file.
- **Requests from the converter side.** A request is byte 0 of the mailbox. The text it sends
  follows from byte 1, or from byte 2 after a sub-code at byte 1. The firmware's answer is read
  back from byte 0: `0xFF` means served.
- **The file size comes with the first call.** The firmware passes the converter's own size at
  mailbox+2, and the converter's free memory starts after it.
- **Errors.** Codes 1 to 16 index the sixteen error texts, from "Nullpointer assignment!" to
  "No Drum Track in this song!". A higher code is shown as "Fcode = n".

## Screens

| title  | name              | when                                                               |
|--------|-------------------|--------------------------------------------------------------------|
| `0x46` | `_TT_STYLCNVWAIT` | no converter on the disk ("Please Insert the Style Convert Disk!") |
| `0x47` | `_TT_STYLCNVMODL` |                                                                    |
| `0x48` | `_TT_STYLCNVCNVT` | opened from the file-access request                                |
| `0x49` | `_TT_STYLCNVSTOR` | conversion finished: store the style                               |
| `0x4A` | `_TT_STYLCNVTXT`  | the converter asks for a text to be shown (request 5)              |
| `0x4B` | `_TT_STYLCNVSEL`  | the converter asks for a choice                                    |
| `0x4C` | `_TT_STYLCNVCONT` | an error (request `0xFE`), or an unknown request                   |

## Running a program of one's own

The firmware runs whatever `.CNV` it finds, and nothing stops a converter from being some other
program. A converter that answers request 5 on every call parks the firmware on its text screen.
The firmware keeps calling it about 20 times a second, while the panel and keybed keep working.
Meanwhile a task the converter started can run a program of its own. Request `0xFE` ends it: the
firmware shows its message box, then "Continue Next?". YES calls the converter again, NO returns
to the main screen. The project's loader, `KN7LOAD.CNV`, uses this door to run programs from the SD
card, Another World among them, on the owner's stock KN7000:
[Your Own Code on a Stock KN7000]({{ site.baseurl }}/kn7000-cnv-homebrew/).

## Not yet known

- **Request arguments:** the layout of the file-access requests' arguments in the mailbox (the
  text requests are above).
- **The result:** where a finished conversion is left for the STORE screen.
- **The Technics path:** what it does after finishing.
- **A real run:** no conversion has been run end to end in the emulator yet.
