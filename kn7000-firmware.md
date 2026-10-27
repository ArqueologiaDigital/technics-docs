---
layout: page
title: KN7000 Firmware Images
permalink: /kn7000-firmware/
---

# KN7000 Firmware Images

Flash images are recovered from the [system-update discs]({{ site.baseurl }}/kn7000-system-update-discs/).
This page describes `kn7000_program.rom` (main firmware, build 941) and
`kn7000_table.rom` (resource archive, build 84); the other builds now held are
listed under [Version numbers](#version-numbers).
Offsets below are file offsets in hex; integers are little-endian **except** the
`.SLD` size field.

## Program image (`kn7000_program.rom`, 0x3F6F01 bytes)

Panasonic **MN10300** code (the MN103002A, an MN1030-series CPU), mapped at CPU address `0x48400000`
(file offset + base). See the [KN7000 overview]({{ site.baseurl }}/kn7000/) for the full memory map.

### Boot header (0x0 – 0x80)

Two absolute jumps and a configuration byte, then `0xFF` fill to the start of code:

```
0x00: dc 7e ff 00 00   jmp  0x4840FF7E     ; reset entry
0x05: cb ×5            nop                  ; padding
0x0a: dc c5 77 0d 00   jmp  0x484D77CF
0x0f: 16               configuration byte   ; 0x15 in v1.5; compared with 0xFF and 0x77 (see MEMORY DUMP Screen)
0x10..0x7f: ff         fill
0x80: code begins
```

`jmp` on the MN10300 is `0xDC` + a 32-bit little-endian target; the stored value
plus the `0x48400000` base gives the destination. There is **no in-image
reset-vector table**: the CPU starts executing at the base of the program flash
itself (the board's MMODE/BMODE straps select that boot mode; MAME sets the reset
PC to `0x48400000`). The library/kernel code at `0x4C000000` is copied out of
this image at boot (see below).

### The library at `0x4C000000` is copied out of this image

The firmware makes **7,965 calls to 298 distinct entry points** at `0x4C000000`:
the **C runtime + MILK kernel**, e.g. `0x4C001A48` (1,201 calls — a
`printf`/`sprintf`-family formatter), `0x4C003051` (a `memcpy`/`strcpy`) and
`0x4C0019D5` (a numeric formatter). That code is **not a separate ROM**. Early in
kernel init `InitializeBlock27` (`0x484D7BBD`) copies ~253 KB from program-flash
`0x487B8FD1` (file `0x3B8FD1`–`0x3F6EE8`, inside code region 2 below) into RAM
that is aliased at both `0x4C000000` and `0x8C000000`. Every entry point the
firmware calls (the highest is `0x4C03DE26`) lies inside that block, so MAME maps
the two aliases to one RAM and runs the real library code, with no dump and no
HLE.

That RAM is IC14/IC15, two 1 Mbit x16 fast SRAMs: 256 KB on chip select CS3, repeating every
256 KB through its 64 MB window ([memory map]({{ site.baseurl }}/kn7000/#memory-map-as-used-by-the-firmware)).
The boot's copy table entry is `{source, 0x4C000000, flags, source end, 0x4C03FFF0}`, followed by
3 bytes copied to `0x4C03FFF0`. The library's length differs per build (the Pinball Fantasies
port's `lib_extent.py` reads it from each image):

| build        | copy table   | source       | library length | free above it, to `0x4C03FFF0` |
|--------------|--------------|--------------|----------------|--------------------------------|
| 893 (v1.3)   | `0x487F55BA` | `0x487B76B1` | `0x3DF02`      | 8,430 bytes                    |
| 929 (v1.4)   | `0x487F6938` | `0x487B8A31` | `0x3DF00`      | 8,432 bytes                    |
| 935 (v1.5)   | `0x487F6E89` | `0x487B8F6D` | `0x3DF15`      | 8,411 bytes                    |
| 941 (v1.6)   | `0x487F6EED` | `0x487B8FD1` | `0x3DF15`      | 8,411 bytes                    |
| 942 (SP7001) | `0x487F8BC7` | `0x487BA785` | `0x3E43B`      | 7,093 bytes                    |

Nothing writes the SRAM above the library. On the owner's unit (program 893) the SURVEY2 dump
of the [ROM dumper]({{ site.baseurl }}/kn7000-rom-dumper/) found power-on noise there after a
whole dumper run: 8,312 of its 8,430 bytes are not zero, with pointer-like words at chance rate.
In program 893 only two instructions name `0x4C03FFF0`, and both concern the 3 copied bytes: a RAM
test at `0x4849FF0C` saves, tests and puts back the 8 bytes from `0x4C03FFF0`, and a check at
`0x4857DE18` tests whether the library RAM's top lies in the work RAM. The library's own variables live
in work RAM (`.bss` from `0x50007F40` in 893). A program of one's own can use the tail
([Work RAM Map]({{ site.baseurl }}/kn7000-work-ram/#ram-a-program-of-ones-own-can-use)).

### Region map

| Range                     | Contents                                                                                                                                                         |
|---------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `0x000080` – ~`0x186000`  | Main firmware code (region 1)                                                                                                                                    |
| ~`0x185DC0` – `0x186208`  | `float64` decibel-ratio table (137 IEEE-754 doubles, e.g. `1.25892544` = 10^0.1)                                                                                 |
| ~`0x186208` – ~`0x3B8000` | Data / resources: multi-language UI text, FAT boot template, flash-chip ID strings, RGB palettes, fonts, GUI resource tables, 9 JPEGs, two Windows `.BMP` images |
| ~`0x3B8000` – `0x3F6F01`  | Code region 2: the `MILK MN10300` kernel + zlib 1.0.4                                                                                                            |

### Version numbers

The package labels come from the download filenames: `kn7-16` is the v1.6
program update, and `kn7-14` is the four-disk v1.4 update, whose table disks
(3–4) the table image comes from. The firmware carries **its own internal build
numbers**, unrelated to those:

| Component | Value   | Where                                                                                                                  |
|-----------|---------|------------------------------------------------------------------------------------------------------------------------|
| PROGRAM   | **941** | `u16` at file `0x33660C` (the loader reads 32 bits but keeps only the low half), shown by `PROGRAM : %4d` (`0x1D67E0`) |
| TABLE     | **84**  | ASCII `"84\n"` at table file `0x139EE8`, reached via the pointer at table offset `0x1C`                                |

Three more program builds have since been recovered from update disks, and all
four have been MAME BIOS options since
[mamedev/mame#16394](https://github.com/mamedev/mame/pull/16394) (2026-10-11):
**942** with table **83** (Key Soft Service's SP7001 PLUG-iN update, stamp at CPU
`0x48737630`; see [SD PLUG-iN]({{ site.baseurl }}/kn7000-sd-plugin/)), **935**
(v1.5, complete, stamp at `0x487365A8`) and the upper half of **929** (v1.4; its
first program floppy is lost).

RHYTHM and PICTURE versions are read from devices not covered by these
updates (the rhythm ROM and the picture ROM IC19 at `0x57800000`; the picture ROM has
since been read from an instrument, see [Picture ROM (IC19)]({{ site.baseurl }}/kn7000-picture-rom/)).

PROGRAM and TABLE are what the instrument's hidden **SOFT VERSION** screen
prints; RHYTHM and PICTURE appear only on the developer DEBUG TOOLS screen. At least one surviving KN7000 reports `PROGRAM : 893` / `TABLE : 80` —
an earlier pair of images, unpreserved until that instrument's own chips were read on
2026-10-19 with the [ROM dumper]({{ site.baseurl }}/kn7000-rom-dumper/); see the
[SOFT VERSION screen]({{ site.baseurl }}/kn7000-soft-version/).

9,472 bytes of that earlier pair have since been transcribed by hand from
photographs of the instrument's own hex viewer. They put build 941 at build 893
**plus several insertions totalling 6,451 bytes** in the program half, and plus a
single 3-byte insertion in the table half. It is a transcription and **not a
dump**, and no reconstructed image exists — see
[Recovering build 893]({{ site.baseurl }}/kn7000-build-893-recovery/), and
[Reading ROM out of the screen]({{ site.baseurl }}/kn7000-rom-from-the-screen/)
for the capture route meant to replace hand photography.

### Notable strings

- Version screen: `SOFT VERSION` (`0x1D5AD8`), `--- SOFTWARE VERSION ---` (`0x1D5D9C`), `PROGRAM : %4d` / `TABLE   : %4d` / `RHYTHM  : %4d` / `PICTURE : %4d` (`0x1D67E0`+)
- Kernel banner `MILK MN10300 Ver1.0R1` (`0x3B8AAC`); zlib deflate/inflate banners (`0x3B8604` / `0x3B863C`)
- FAT boot template `Technics    NO NAME    FAT12   FAT16` (`0x1BA4BB`)
- Flash-chip IDs `MBM29LV160B`, `MX29LV160B`, `AT49BV16X4` (`0x1CF9E0`+): the table at `0x485CF9E0` of parts the firmware accepts for the custom-data flash IC21, checked against the chip's autoselect ID before it programs it
- Model-compatibility list `@Expansion Board KN7000 SOUND RAM`, then `KN6000`/`KN5000`/`KN3000`/`KN2000`/`KN1600 SOUND RAM` (`0x1B8517`+)
- UI languages: English / German / French / Spanish / Indonesian message blocks (Italian has a menu entry but no translated text), plus an EUC-JP developer easter-egg entry at `0x1A0C4D`
- Developer symbol tables: `_TT_*` tag names, `*Proc` window-procedure names (`AcProgVerBoxProc`, `IvMpVerWinProc`, …), `MT_*` API names (`MT_GetLanguagePtr`, `MT_FLASHWRITE`), GUI object names (`PanelSimulator`, `ClipBoard`, `DefaultWindow`) — the same conventions as the KN5000 (see [Shared Codebase Map]({{ site.baseurl }}/technics-shared-codebase/))

### Embedded images

9 JPEGs plus two genuine Windows `.BMP` files — a 26×46 1bpp treble-clef icon at
`0x19E704` and a 160×100 8bpp photo at `0x345718`. Unlike the KN5000's
headerless raw 8bpp bitmaps, the KN7000 uses standard file formats for at least
part of its artwork, and none of the KN5000 bitmap pixel data is reused.

## Table image (`kn7000_table.rom`, 0x3E94D4 bytes)

A resource archive fronted by an offset directory:

| Offset  | Contents                                                                                                                               |
|---------|----------------------------------------------------------------------------------------------------------------------------------------|
| `0x000` | 85 × `uint32` little-endian offsets: `dir[0]=0x200` (first segment) … `dir[84]=0x3E94D4` (= file size, end sentinel) → **84 segments** |
| `0x154` | zero padding to `0x200`                                                                                                                |
| `0x200` | segment data                                                                                                                           |

Segment *i* spans `dir[i]..dir[i+1]`. The 84 segments break down as **57
baseline JPEGs** (built-in demo slideshows, all verified decodable, 160×80 up to
640×240) and 27 tagged data chunks whose first bytes are an ASCII type tag
(`TCMP`, `TPAD`, `JK`, …). Two 4-byte segments hold the ASCII strings `"84\n"`
(the table version) and a `"ZZZ\n"` placeholder.

In the disassembly (since 2026-10-24, commits `c8d16a271`, `b7f9b8a68`, `5db37967b` and
`dafa442b3`, merged as `70b363ca5`), `kn7000/src/table.s` spells the directory as offsets to
84 labelled segments, named by `tools/table_segments.py`. The 57 JPEG segments, and the 102
pictures of the six picture-group segments, are files in `kn7000/src/table/`. The help texts
(four language indexes, page lists and the texts as `.ascii`) and the GUI resource tables (366
bitmap, frame and icon rows and 12 font descriptors) are typed; the rest is `.incbin_range`.

> **Where the image stops is not where the chip stops.** IC16 + IC17 are one
> 8 MB flash pair spanning `0x48000000`–`0x487FFFFF`, with this table image as the
> lower half and the program image as the upper half. The table payload ends at
> `0x483E94D3`, which leaves **`0x483E94D4`–`0x483FFFFF` (92,972 bytes)** that no
> standard update ships. The SP7001 PLUG-iN table update is a full `0x400000`
> bytes and writes its plug-in code and strings there (up to `0x483FB59F`); what a
> stock unit holds in that range has never been read. See
> [Where does the flash updater live?]({{ site.baseurl }}/kn7000-firmware-security/#45-where-does-the-flash-updater-live).

The SP7001's table, build 83, keeps this layout: 78 of its 84 segments are
byte-identical to build 84's. It differs in the version string (`"83\n"`), in three
more 4-byte markers (segments 68–70, `"80\n"` where build 84 has `"84\n"`), in one
shorter data segment, and in a 4-byte stub where build 84 has a `Tech` asset. Its
plug-in starts at `0x483E8000`; see
[SP7001 Firmware]({{ site.baseurl }}/kn7000-sp7001-firmware/#table-83-against-table-84).

## Byte-exact disassembly project

The `kn7000/` folder of the [`technics-roms-disasm`](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/kn7000) repository (until 2026-10-19 the separate
`kn7000_disassembly`) holds a reconstruction project for the
MN10300 firmware. Because no GNU binutils MN10300 target is available in common
distributions, it ships a small self-contained assembler whose only job is
byte-exact reconstruction: the source starts as a skeleton in which every byte is
pulled in verbatim (a raw range), and reverse engineering proceeds by replacing
those ranges with real disassembled instructions and typed data. A `make verify`
step asserts the rebuilt images stay **100% byte-identical** to the originals at
every step. Disassembly listings are generated with MAME's `unidasm`
(`-arch mn10300`).

This mirrors the KN5000 approach, whose
[ROM reconstruction]({{ site.baseurl }}/rom-reconstruction/) rebuilds sixteen TLCS-900 images
byte-identically from source; `make gate-all` there covers those, the fifteen KN7000 images
(`make gate-kn7000`: program 941, tables 84 and 80, the IC18 boot ROM, the SP7001 set, the
picture ROM and the seven Style Convert converters) and the four MN10300 sibling trees in one run.

### 2,302 functions named by reusing KN5000 knowledge

The disassembly gets a large head start from the
[shared codebase]({{ site.baseurl }}/technics-shared-codebase/): the KN7000 embeds the same "MILK"
UI-toolkit **runtime reflection tables** the KN5000 does — code-pointer arrays
each followed by an index-parallel name-pointer array, used by the firmware's
`MT_GetProcedure`-style lookup. There are **~114 such tables** (one per
widget/handler group), and parsing them all recovers **2,302 named functions** —
`SleepMainTask`, `DispatchEvent`, and the whole `Ac*`/`Vw*`/`Ps*`/`Iv*`/`Tt*`
widget window-procedure set (518 `*Proc` + 353 `*Func` handlers), i.e. the **same
names documented for the KN5000**. These become the named anchors for the
instruction-level disassembly. Build 942 adds a table of its own, the services it
exports to SP7001 plug-ins by name; 186 of those names belong to routines build 941
has too, and they now name them in build 941's disassembly as well
([details]({{ site.baseurl }}/kn7000-sp7001-firmware/#the-export-table)).

### Readable, re-assemblable source

With a purpose-built MN10300 encoder (99.9% round-trip) wired into
the assembler, named functions are converted from raw bytes into real MN10300
source that still rebuilds byte-for-byte. Call targets are resolved to labels —
recovered names where known, else a synthetic `func_<ADDR>` for the internal
helpers — so the reconstruction reads like ordinary source. For example the
object-visibility accessor `SetVisible`:

```
SetVisible:                        # CPU 0x4842D3DF
    movm    [d2], (sp)
    add     -0xc, sp
    mov     d1, d2                 # the requested state
    call    GetViewInstance, 0, 0  # a0 = the view object
    cmp     0, d2
    beq     0x4842d3fa
    add     0xc, a0
    movhu   (a0), d0               # its flag word
    and     0xfffe, d0             # state != 0: clear bit 0 (shown)
    movhu   d0, (a0)
    bra     0x4842d403
    add     0xc, a0
    movhu   (a0), d0
    or      0x01, d0               # state == 0: set bit 0 (hidden)
    movhu   d0, (a0)
    ret     [d2], 0x10
```

Since 2026-10-24 every function of code region 1 and of the library image is converted this
way (disassembly commits `47737623a` and `d87382628`, merged as `069d6000b`).
`tools/coverage_score.py` reports all 3,658 function blocks converted, 670,646 instruction
lines and no `.byte` escape, and counts 44.58% of the image's bytes, 1,853,232 of 4,157,185,
as real source (it was 3.88% before, with 998 functions converted by hand-picked sets). What
still passes through as `.incbin_range` is the data region, file `0x186000`-`0x3B8FD1`, apart
from the typed display palette. The functions read by hand before the bulk conversion keep
their notes, among them the task/event and display/object framework clusters, the complete
Techni-Chord harmony engine and the complete control-panel serial protocol (the
`PanelTransaction`/ISR/state-machine chain that drove the MAME panel HLE).

The converted source is symbolic. Every function keeps its symbol-file name as a label; a
function no symbol file names yet is `func_<ADDR>`; every branch target is a label,
`loc_<ADDR>` unless something names it. A function that can also be reached through a pointer
starts with a register-save prologue (`movm [regs], (sp)` and/or `add -N, sp`) and is entered
by `call` right after it, so its label sits on the prologue and `<name>_entry` on the `call`
entry. Naming the `func_` functions and the `loc_` labels is the next step.

### A second target: the SP7001 firmware

The same repository rebuilds the SP7001 firmware (program 942, table 83) and its
plug-in program `BASEEXT.XAP` byte-exactly too. It does so by carrying everything
recovered for build 941 across, not by starting again. An exact alignment of the two
builds shows program 942 is build 941 plus a few small edits. It names every byte that
moved, so build 941's function split, names, converted functions and notes all
transfer. Only the code that is new in 942 had to be read afresh. See
[SP7001 Firmware: What Changed, and the Plug-in]({{ site.baseurl }}/kn7000-sp7001-firmware/).
