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
Details, addresses and scripts are in the kn7000_disassembly repository,
`notes/style-converter.md`.

## What is on the disk

| file                     | converts styles of                                  | same on both disks?                            |
|--------------------------|-----------------------------------------------------|------------------------------------------------|
| `GEM_WS2.CNV`            | GEM (General Music) WS2                             | identical                                      |
| `GEM_WX2.CNV`            | GEM WX2                                             | identical                                      |
| `KORG.CNV`               | Korg                                                | identical                                      |
| `Roland.cnv`             | Roland                                              | identical                                      |
| `SOLTON.CNV`             | Solton                                              | identical                                      |
| `TECHNICS.CNV`           | Technics KN1000 / KN750, per the firmware's prompt  | same program, relinked (data addresses moved)  |
| `V1%0_.ver`, `V2%0_.ver` | nothing: a version tag                              | same content, different name                   |

The brand names are only in the file names; the converters contain no text at all.

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

## Screens

| title  | name              | when                                                               |
|--------|-------------------|--------------------------------------------------------------------|
| `0x46` | `_TT_STYLCNVWAIT` | no converter on the disk ("Please Insert the Style Convert Disk!") |
| `0x47` | `_TT_STYLCNVMODL` |                                                                    |
| `0x48` | `_TT_STYLCNVCNVT` | opened from the file-access request                                |
| `0x49` | `_TT_STYLCNVSTOR` | conversion finished: store the style                               |
| `0x4A` | `_TT_STYLCNVTXT`  | the converter asks for a text to be shown                          |
| `0x4B` | `_TT_STYLCNVSEL`  | the converter asks for a choice                                    |
| `0x4C` | `_TT_STYLCNVCONT` | an error, or an unknown request                                    |

## Not yet known

- **Request arguments:** the exact layout of each request's arguments in the mailbox.
- **The result:** where a finished conversion is left for the STORE screen.
- **The Technics path:** what it does after finishing.
- **A real run:** no conversion has been run end to end in the emulator yet.
