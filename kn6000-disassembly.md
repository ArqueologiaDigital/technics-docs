---
layout: page
title: KN6000 / KN6500 / HD-SX Disassembly
permalink: /kn6000-disassembly/
---

# KN6000 / KN6500 / HD-SX — the disassembly trees

Since 2026-10-24 the disassembly repository has three folders for this family, each
rebuilding one image byte for byte from MN10300 assembly source:

| folder    | image                                                                                     | linked at    | bytes     | disassembly commit |
|-----------|-------------------------------------------------------------------------------------------|--------------|----------:|--------------------|
| `kn6000/` | SX-KN6000 program flash, update v7.1 (`IK1.SLD` + `IK2.SLD`)                              | `0x4C000000` | 4,160,049 | `93b74d224`        |
| `kn6500/` | SX-KN6500 program flash, update v1.3 (`IKV1.SLD` + `IKV2.SLD`)                            | `0x4C000000` | 3,675,793 | `2a5871be2`        |
| `hdsx3/`  | the expansion board's `XAPR` plug-in, update sx6-113 (`EXTAPR.SLD`), most probably HD-SX6 | `0x97800000` | 786,432   | `1d21c4fde`        |

All three were merged as `921314742`, together with the
[KN2400 / KN2600 tree]({{ site.baseurl }}/kn2400-disassembly/). Like it, they are made with
the KN7000 tree's own tools, used by relative path (`../kn7000/tools`) and not copied: the
assembler `kn7asm.py`, the source generator `gen_image_s.py`, the MILK reflection-table
walker `gen_symbols.py`, the name porter `port_names_by_code.py` and the update-disk decoders.
The hardware the images run on is on [Hardware Architecture]({{ site.baseurl }}/kn6000-hardware/).

    make kn6000 kn6500 hdsx3                 # from the repository root: assemble
    make gate-kn6000 gate-kn6500 gate-hdsx3  # byte-identity gates (all three are in make gate-all)

Since 2026-10-29 `kn6000/` also rebuilds a second image, the factory **custom-data bank** of the
KN6000 / KN6500 custom flash IC18 (`kn6000/src/customdata/`, see
[below](#the-custom-data-bank-ic18)); `make gate-kn6000` runs `verify verify-customdata`.

**What is not here: the table ROMs IC13 / IC14.** Both models keep their built-in style and
sound tables in two 16 Mbit table-data ROMs (KN6000 `QSIGX3C16008` / `QSIGX3C16007`, KN6500
`C3FBMD000069` / `C3FBMD000068`). They are undumped, and the update floppies do not carry
them, because only the program flash can be updated in the field. These trees reproduce the
program flash (IC11 / IC12) and the plug-in only.

## The reference images are regenerated, not committed

The images are copyrighted and the repository has a public remote, so each `baserom/` is
git-ignored. `make baserom` rebuilds each image from the manufacturer's update in the private
customer-service mirror beside the repository (`CA_MIRROR=`), without running any of its
programs: `sfx_extract.py` reads the ZIP archive appended to each self-extracting `.exe`, and
`sld_decompress.py` undoes the LZSS.

| image          | update package | floppy files                          | decompressed        | checksum file                                                   | recorded SHA-1                             |
|----------------|----------------|---------------------------------------|---------------------|-----------------------------------------------------------------|--------------------------------------------|
| KN6000 program | `kn6-71.zip`   | `IK1.SLD`, `IK2.SLD`, `SMCKPR1.INF`   | 0x200000 + 0x1F7A31 | `SMCKPR1.INF`: total 0x166ADB67, 16/16 blocks                   | `fa4cdb0618c18cdd549f067a388cabe3ecb8f9d4` |
| KN6500 program | `kn65-13.zip`  | `IKV1.SLD`, `IKV2.SLD`, `SMCKPV1.INF` | 0x200000 + 0x181691 | `SMCKPV1.INF`: total 0x157ED142, 15/15 blocks                   | `a507de3977def5d4148c4d3dbc16e3f6ff9f01c8` |
| `XAPR` plug-in | `sx6-113.zip`  | `EXTAPR.SLD` (434,964 B, `SLIDE4K`)   | 0xC0000             | none; the private romset's `hd-sx3_v1_1.bin` has the same bytes | `88699a7e9584e0c30c175babd1482e5aa586ad3d` |

## The two program images

The KN6000 and KN6500 images have the same layout. The whole image is linked for
`0x4C000000`, the window the firmware runs its program from:

| KN6000 file offsets   | KN6500 file offsets   | contents                                                                   |
|-----------------------|-----------------------|----------------------------------------------------------------------------|
| `0x000000`-`0x000010` | `0x000000`-`0x000010` | boot header: `_reset` (jmp to `crt0_start`), 5 nops, `_vector_08`, 3 bytes |
| `0x000010`-`0x000080` | `0x000010`-`0x000080` | erased (`0xFF`)                                                            |
| `0x000080`-`0x176037` | `0x000080`-`0x176839` | code: start-up, the application, the C runtime                             |
| `0x176037`-`0x3F47EC` | `0x176839`-`0x37E44C` | data                                                                       |
| `0x3F47EC`-`0x3F77E7` | `0x37E44C`-`0x381447` | code: the MILK kernel (uITRON services `del_mbx` ... `dly_tsk`)            |
| `0x3F77E7`-`0x3F7A31` | `0x381447`-`0x381691` | data, including the `MILK MN10300 Ver1.0R1` banner                         |

The code ranges are the ones the sources were generated with (each Makefile's `CODE`). Their
ends are where the reached code stops: past them, no traced path enters and no named entry lies.

## The XAPR plug-in (HD-SX3 or HD-SX6)

The keyboard's own MN10300 runs this image from `0x97800000`, where the expansion board
appears with the signature `XAPR`. The folder, its make targets and the private romset's file
name all say HD-SX3, but the evidence points at the HD-SX6 by Key Soft Service: the update's
own instructions (`install.pdf` in `sx6-113.zip`) are titled for the HD-SX6, the image's
strings name `KEY SOFT SERVICE` and its `Kss*` procedures, and the installer's
`TECHNICS.HDD` labels the file `KN6KHD Technics KN6000 HDD-FIRMWARE`. Whether to rename the
folder is the owner's decision. See also
[Expansion Bus & Wave-ROM Dump]({{ site.baseurl }}/kn7000-expansion-and-wave-dump/).

| file offsets          | contents                                                                        |
|-----------------------|---------------------------------------------------------------------------------|
| `0x000000`-`0x000004` | signature `XAPR`                                                                |
| `0x000004`-`0x000080` | 31 header words, emitted as `.long` rows                                        |
| `0x000080`-`0x03DED6` | code                                                                            |
| `0x03DED6`-`0x0B6560` | data: bitmaps, text, the plug-in's MILK reflection tables, then a second `XAPR` |
| `0x0B6560`-`0x0C0000` | erased (`0xFF`)                                                                 |

The header word at `+0x04` points at the second `XAPR` (`XaprTrailerSignature`, at
`0xB655C`); no code in the image refers to it. The words from `+0x08` to `+0x54` point at
code, and the KN6000 firmware calls `+0x08`, `+0x0C` and `+0x10` through `calls (aN)` once
the signature checks out. The ten words from `+0x58` to `+0x7C` all point at `0x80`, a bare
`rets` (`XaprEmptySlot`). The entry vectors' roles are not worked out yet, so they keep
`func_<ADDR>` names. The plug-in makes no direct call into the KN6000 firmware: its 2,625
indirect `calls (aN)` go through pointers it loads at run time, not traced yet.

## Names

| tree     | from the image's own MILK reflection tables (`*.sym`)                              | by hand (`*_manual.sym`)                | carried from KN7000 program 941 (`*_ported.sym`) |
|----------|-----------------------------------------------------------------------------------:|-----------------------------------------|-------------------------------------------------:|
| `kn6000` | 1,255                                                                              | `_reset`, `_vector_08`, `crt0_start`    | 546                                              |
| `kn6500` | 1,395                                                                              | `_reset`, `_vector_08`, `crt0_start`    | 552                                              |
| `hdsx3`  | 98 (`Kss*` window procedures, `Debug_Wind_RW`, `Bitmap*` resource procedures, ...) | `XaprEmptySlot`, `XaprTrailerSignature` | 29                                               |

`gen_symbols.py` takes only tables whose procedures land in the code ranges. Counting the
whole image as code, it would also accept a `DiskMenu` table whose pointers lead into data
and name 38 (KN6000) or 39 (KN6500) more addresses wrongly
(`kn7000/notes/sibling-symbol-probes/whole_image_pairings.py`). `port_names_by_code.py`
carries a KN7000 name only when an unnamed entry is the same code as a named KN7000 routine:
the same instructions from the entry to the first return, with every number of 0x10000 or
more masked out (addresses, and MILK message codes, which are renumbered between models), at
least 8 of them unmasked, and the match unique on both sides. The other labels follow the
KN7000 convention: `func_<ADDR>` for an entry no table names, `<name>_entry` for the
register-save `call` entry behind a named prologue, `<entry>_L<offset>` for a branch target.
The site's [Firmware Names & Symbols]({{ site.baseurl }}/kn6000-names/) page covers the
reflection tables themselves.

## How much of each image is code

`src/program.s` in each folder is generated by `make program-src`
(`../kn7000/tools/gen_image_s.py`, which needs MAME's `unidasm`). Only code a traced path
reaches becomes instructions, re-encoded by `mn10300_asm` and compared with the image; the
code halves of the MILK reflection tables are `.long` rows of names; everything else stays
`.incbin_range` from `baserom/`, so data is never spelled as instructions. An instruction
the encoder spells differently becomes a `.byte` escape with the disassembly beside it.

Each generator run writes `notes/conversion-stats.txt` in its folder; at disassembly
`2319e9b94`:

| measure                      | KN6000                    | KN6500                    | `XAPR` plug-in          |
|------------------------------|---------------------------|---------------------------|-------------------------|
| image bytes                  | 4,160,049                 | 3,675,793                 | 786,432                 |
| code-range bytes             | 1,544,130                 | 1,546,180                 | 253,526                 |
| entries                      | 13,146                    | 13,323                    | 990                     |
| of which named               | 1,804                     | 1,950                     | 128                     |
| derived `<name>_entry`       | 553                       | 557                       | 20                      |
| still `func_<ADDR>`          | 10,789                    | 10,816                    | 842                     |
| bytes emitted as code        | 1,524,300                 | 1,530,172                 | 252,331                 |
| share of the code ranges     | 98.72%                    | 98.96%                    | 99.53%                  |
| share of the image           | 36.64%                    | 41.63%                    | 32.09%                  |
| instructions                 | 572,295                   | 574,135                   | 88,217                  |
| `.byte` escapes              | 272                       | 285                       | 12                      |
| local branch labels          | 43,192                    | 43,667                    | 9,198                   |
| code-range bytes left binary | 19,825 in 300 pieces      | 16,003 in 303 pieces      | 1,162 in 25 pieces      |
| reflection tables as `.long` | 21                        | 22                        | 3                       |

## The custom-data bank (IC18)

The KN6000 and KN6500 keep their 20 CUSTOM styles in the upper 1,920 KB of their 16 Mbit custom
flash IC18 (the bank at `0x96820000`), in the same format as the KN7000's IC21, written by the
same firmware module: a block-0 directory (`"IK"`, 20 slot descriptors, a 60-block map), then one
record per slot holding the style ("TCMP"), its pads ("TPAD"), its four One Touch Settings and
any user sounds. The format is on
[Custom Style Memory (IC21) & .AST Files]({{ site.baseurl }}/kn7000-custom-style-memory/).

| image (reference)               | floppy (MAME softlist)  | file           | SHA-1 of the bank                          |
|---------------------------------|-------------------------|----------------|--------------------------------------------|
| KN6000 / KN6500 `01ctmini.ic18` | `kn6000_flop` `idd6000` | `01CTMINI.AST` | `8c6d62a8afab717a2b59e9242bbf897b01369416` |

The reference is made from the Initial Data Disk, not from a chip: the Makefile extracts
`01CTMINI.AST` from the floppy image, inflates it (`../kn7000/tools/ast_file.py`) and checks the
SHA-1. `kn6000/src/customdata/01ctmini.s` and its folder `01ctmini/` are generated by
`../kn7000/tools/gen_customdata_s.py --model kn6000` and use the KN7000 tree's macros; every
style event is a typed line, and the data-incbin census finds no binary include left (0 generic,
0 opaque). The KN6000's One Touch Settings are `0x90` bytes, not `0xA0`, and all 80 of them hold
part 3 as all `0xFF`, which the v7.1 writer would not produce: an earlier program wrote this file.
The bank has no stale records and no residue, unlike the KN7000 sets.

    make -C kn6000 verify-customdata       # the bank, rebuilt and compared (in make gate-kn6000)
    make -C kn6000 verify-customdata-ast   # 01CTMINI.AST rebuilt from the bank with the zlib 1.0.4 port
    make -C kn6000 customdata-src          # regenerate src/customdata/

The `.AST` header carries the tag `"I K"` where the KN7000's carries `"J K"`.

## Open work

- Names: most entries are still `func_<ADDR>`. Routines that differ slightly from their
  KN7000 versions need another method than exact matching, and names from the KN2400's and
  from each other's reflection tables have not been carried across yet.
- RAM, I/O and data addresses are still numbers in the sources.
- The program images' data is untyped `.incbin_range`, apart from the reflection tables' code halves (and,
  in the plug-in, its header and the two `XAPR` signatures).
- The plug-in's entry vectors and the targets of its indirect calls.
- The table ROMs IC13 / IC14 need dumping before any table tree can exist; see the
  [ROM Dumping Roadmap]({{ site.baseurl }}/rom-dumping-roadmap/).

Each folder's `README.md` in the disassembly repository is the reference for the above.
