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

Since 2026-10-29 the data half of each image is typed source as well: the MILK widget records of
every screen (with a generated menu map per image), the Music Stylist, the note-conversion
tables, the factory panel memories, the sound hash tables and the plug-in's own GUI. That is on
its own page, [KN6000 / KN6500 Program Data & GUI]({{ site.baseurl }}/kn6000-program-data/).

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

| KN6000 file offsets   | KN6500 file offsets   | contents                                                                                                                                                                |
|-----------------------|-----------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `0x000000`-`0x000010` | `0x000000`-`0x000010` | boot header: `_reset` (jmp to `crt0_start`), 5 nops, `_vector_08`, 3 bytes, the last `FirmwareVersionByte` (`0x71` / `0x13`)                                            |
| `0x000010`-`0x000080` | `0x000010`-`0x000080` | erased (`0xFF`)                                                                                                                                                         |
| `0x000080`-`0x176037` | `0x000080`-`0x176839` | code: start-up, the application, the C runtime                                                                                                                          |
| `0x176037`-`0x3F47EC` | `0x176839`-`0x37E44C` | data                                                                                                                                                                    |
| `0x3F47EC`-`0x3F77E7` | `0x37E44C`-`0x381447` | code: the MILK kernel (uITRON services `del_mbx` ... `dly_tsk`), ending in its flash-resident routines `KernelInit` ... `KernelInitHook` (names since lane code-island) |
| `0x3F77E7`-`0x3F78B4` | `0x381447`-`0x381514` | typed data: the `MILK MN10300 Ver1.0R1` banner (`Str_MILK_MN10300_Ver1_0R1`), `KernelServiceHash`, `KernelRamLayout`, `KernelParams`                                    |
| `0x3F78B4`-`0x3F7A31` | `0x381514`-`0x381691` | code: `KernelStartStub` and the kernel's interrupt dispatchers `KernelGroup0IntDispatch`, `KernelIntDispatch` (a code range since lane generic-zero)                    |

The code ranges are the ones the sources were generated with (each Makefile's `CODE`). Their
ends are where the reached code stops: past them, no traced path enters and no named entry lies.
The two pieces of the code file outside every code range (115 + 586 bytes) were the last
`.incbin_range`s there; lane generic-zero (disassembly `c04e41079`) typed them through the
Makefile's `TYPED` and named them in `<model>_manual.sym`, each with the code that reads it:
`func_4C07B3D7` / `func_4C07B56B` answer `FirmwareVersionByte`; `KernelWaitRelease` (`0x4C3F7632` /
`0x4C381292`, formerly `func_4C3F7632` / `func_4C381292`)
probes `KernelServiceHash` (16 x {u32 key, handler}) by `(key & 0xF) * 8` and `jmp`s through `+4`;
`func_4C3F61BB` and three more kernel routines read `KernelRamLayout` (6 RAM addresses), `get_tid`
and two more `KernelParams` (14 u16; KN6000 names). The two dispatchers are reached only through the `jmp KernelIntDispatch` that
`func_4C000350` writes at `0x90000000`; they are decoded now. Their five `movm` of the `other3`
register group were `.byte` escapes until lane code-island taught `gen_image_s.py` movm's `other*`
registers, the long encodings the linker left (`call T:32`, `mov 0x30:32, d0`) and the `(d32, aN)`
loads unidasm swaps: the KN6000's 80, the KN6500's 93, the KN2400's 93 and the plug-in's 12
escaped instructions are instructions now, and no code range holds a `.byte` run. *[INFERENCE]* on what the hash keys, the RAM words and the u16
parameters mean.

The kernel routines that sit beside these tables are the same code the SX-KN7000 runs from its
flash, and they take its names (`kn6000_manual.sym`, `kn6500_manual.sym`, `kn2400_manual.sym`,
section "the MILK kernel's tail routines"; lane code-island,
[`kn7000/notes/code-island/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/code-island/README.md)):

| model  | `KernelInit` | `KernelWaitRelease` | hooks (`KernelErrorHook`, `KernelErrorHook2`, `KernelWaitAbortHook`) | `KernelStart` | `KernelInitHook` | calls of the hooks |
|--------|--------------|---------------------|----------------------------------------------------------------------|---------------|------------------|--------------------|
| KN7000 | `0x487B8B78` | `0x487B8E2F`        | `0x487B8F9B`, `0x487B8F9E`, `0x487B8FA1`                             | `0x487B8FA4`  | `0x487B8FAF`     | 26, 3, 1           |
| KN6000 | `0x4C3F7383` | `0x4C3F7632`        | `0x4C3F778A`, `0x4C3F778D`, `0x4C3F7790`                             | `0x4C3F7793`  | `0x4C3F779E`     | 27, 2, 2           |
| KN6500 | `0x4C380FE3` | `0x4C381292`        | `0x4C3813EA`, `0x4C3813ED`, `0x4C3813F0`                             | `0x4C3813F3`  | `0x4C3813FE`     | 27, 2, 2           |
| KN2400 | `0x48728165` | `0x4872841C`        | `0x48728588`, `0x4872858B`, `0x4872858E`                             | `0x48728591`  | `0x4872859C`     | 25, 3, 1           |

The names are *[INFERENCE]* from what the code does ([Firmware Images]({{ site.baseurl }}/kn7000-firmware/#the-kernels-flash-tail)).
The routine after `KernelInitHook` is `KernelTickIsrDefault` in every model (KN7000 `0x487B8FB2`,
KN6000 `0x4C3F77A1`, KN6500 `0x4C381401`, KN2400 `0x4872859F`): the kernel's default system-tick
interrupt handler, which nothing enters, because each application installs its own tick handler for
interrupt 1 / G6ICR (KN6000 `0x4C171C06`, KN6500 `0x4C172408`, KN2400 `0x5018B5FD`) through the def_int
service (lane mn10300-typer, *[INFERENCE]* that it is the configuration's default;
[Firmware Images]({{ site.baseurl }}/kn7000-firmware/#the-kernels-flash-tail)).

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
code: the 20 entry vectors, which the KN6000 and the KN6500 all call, each through a stub that tests
`XaprBoardDetect`'s result (start-up, an idle call, two interrupt handlers, a parameter hook, and a whole
file system the host's file layer forwards to while the hard disk is in use; named by lane mn10300-rest
in `hdsx3_manual.sym`, table on [Program Data & GUI]({{ site.baseurl }}/kn6000-program-data/#the-hd-sx6-plug-in)).
The ten words from `+0x58` to `+0x7C` all point at `0x80`, a bare `rets` (`XaprEmptySlot`). The plug-in
makes no direct call into the KN6000 firmware. Its indirect `calls (aN)` go through the KN6000's own
block-0 Function table, which it reads through the registry (slot `0x100`; 183 calls go through slot
`0x107`, block 7): that is how it registers 55 classes and 999 widget records of its own. Since lane
mn10300-rest every host call in the source carries the routine's name (`gen_image_s.py --host-calls`).

## Names

| tree     | from the image's own MILK reflection tables (`*.sym`)                              | by hand (`*_manual.sym`)                                                                              | carried from KN7000 program 941 (`*_ported.sym`) |
|----------|-----------------------------------------------------------------------------------:|-------------------------------------------------------------------------------------------------------|-------------------------------------------------:|
| `kn6000` | 1,251                                                                              | 27: `_reset`, `crt0_start`, data blocks and the MILK kernel's tail (`KernelInit`, `KernelStart`, ...) | 715                                              |
| `kn6500` | 1,391                                                                              | 26: `_reset`, `crt0_start`, data blocks and the MILK kernel's tail (`KernelInit`, `KernelStart`, ...) | 722                                              |
| `hdsx3`  | 98 (`Kss*` window procedures, `Debug_Wind_RW`, `Bitmap*` resource procedures, ...) | `XaprEmptySlot`, `XaprTrailerSignature`                                                               | 52                                               |

`gen_symbols.py` takes only tables whose procedures land in the code ranges. Counting the
whole image as code, it would also accept a `DiskMenu` table whose pointers lead into data
and name 38 (KN6000) or 39 (KN6500) more addresses wrongly
(`kn7000/notes/sibling-symbol-probes/whole_image_pairings.py`). `port_names_by_code.py`
carries a KN7000 name only when an unnamed entry is the same code as a named KN7000 routine:
the same instructions from the entry to the first return, with every number of 0x10000 or
more masked out (addresses, and MILK message codes, which are renumbered between models), at
least 8 of them unmasked, and the match unique on both sides; since 2026-11-06 a call entry
(`func_<ADDR>_entry`) is a candidate too (with the same lane's new KN7000 names, ported rows KN6000
778 -> 806, KN6500 803 -> 831, HD-SX3 52; `kn7000/notes/kn7000-names/README.md`). The other labels follow the
KN7000 convention: `func_<ADDR>` for an entry no table names, `<name>_entry` for the
register-save `call` entry behind a named prologue, `<entry>_L<offset>` for a branch target.
The site's [Firmware Names & Symbols]({{ site.baseurl }}/kn6000-names/) page covers the
reflection tables themselves. The counts above were taken 2026-10-31 at technics-roms-disasm `f4045a81c`, as each file's rows that
start with `0x` (`command grep -c '^0x' <folder>/<file>`). Each data tree's
`src/program/data/functions.sym` gives the code the firmware's own names of the procedures its
MILK function tables list (555 on the KN6000 at `f4045a81c`); the `entries` row below counts all of them.

**Where the names come from.** The KN6000, KN6500 and KN2400/KN2600 programs carry part of their
own names: the MILK framework's reflection tables name about 1,250 to 2,300 procedures per image
(the tables above), and its function tables some 550 more. Most other names are carried over from the KN7000, whose
program shares much of their code. A routine whose code is the same as a named KN7000 routine
takes its name; since November 2026 a routine too short to be told apart by its code alone (a
getter, a flag setter) takes it too when the routines that call it are the same on both sides and
call it at the same place, or when it uses the same variables. Variables are named the same way:
from the KN7000 when the same instruction of the same routine uses them, from the firmware's own
accessor routines (`GetSeqSongNo` reads `SeqSongNo`), or after the one named routine that uses
them.

The call-site, same-variable and accessor steps are lane sibling-names's (2026-11-06, disassembly
[`kn7000/notes/sibling-names/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/sibling-names/README.md),
merged in `5b72cf364`). `kn7000/tools/port_names_by_alignment.py` (`make aligned-names`, writing
`<model>_aligned.sym`) carries 941's names along the call sites and RAM operands of routines both
images already name; `kn7000/tools/name_ram_by_use.py` (`make ram-names`, `<model>_ram.sym`) names
a RAM address after a named accessor (`GetSeqPlySrtR` / `SetSeqPlySrtR` -> `SeqPlySrtR`) or after
the one named routine that spells it (`R_Ram`, `R_Ram_2`, ...). Every row states its class and its
evidence.

| tree     | `*_aligned.sym` rows (call site / same body / RAM =) | `*_ram.sym` rows (accessor / owner)     | `func_` labels before -> after | numeric work-RAM operands / addresses before -> after |
|----------|------------------------------------------------------|-----------------------------------------|--------------------------------|-------------------------------------------------------|
| `kn6000` | 116 (82 / 26 / 8)                                    | 483 (25 / 458)                          | 10,061 -> 9,917                | 20,128 / 2,996 -> 17,752 / 2,524                      |
| `kn6500` | 117 (81 / 27 / 9)                                    | 483 (25 / 458)                          | 10,116 -> 9,972                | 20,164 / 3,006 -> 17,788 / 2,533                      |
| `hdsx3`  | 2 (1 / 1 / 0)                                        | none (no RAM operand in the RAM ranges) | 768 -> 765                     | 0                                                     |

The `func_` and operand figures are `kn7000/notes/sibling-names-probes/sibling_name_census.py`, before
at `2bde950fa` and after on the lane's regenerated tree; the row counts are `grep -c '^0x'` at
`3834c8773`. Run where the answer is already known (a callee or same-body routine both images name),
the call-site rule is right 488 times and wrong 2 on the KN6000 (491 / 2 on the KN6500, 36 / 0 on the
HD-SX3), and the same-body rule 122 / 0 (125 / 0). The wrong ones read as two names for one routine
rather than wrong picks: `Draw2BpFile_Impl` against 941's `DrawBitmapFile_Impl` (the siblings draw
2-bit pictures there), `M3HookDispatch` against `M3SetSpecialDispatch`.

## How much of each image is code

`src/program.s` in each folder is generated by `make program-src`
(`../kn7000/tools/gen_image_s.py`, which needs MAME's `unidasm`). Only code a traced path
reaches becomes instructions, re-encoded by `mn10300_asm` and compared with the image; the
code halves of the MILK reflection tables are `.long` rows of names; everything else stays
`.incbin_range` from `baserom/`, so data is never spelled as instructions. An instruction
the encoder spells differently becomes a `.byte` escape with the disassembly beside it.

Each generator run writes `notes/conversion-stats.txt` in its folder. As committed at disassembly
`c04e41079` (2026-10-30, lane generic-zero; the plug-in's unchanged since `1a0e9e21f`):

| measure                      | KN6000    | KN6500    | `XAPR` plug-in |
|------------------------------|-----------|-----------|----------------|
| image bytes                  | 4,160,049 | 3,675,793 | 786,432        |
| code-range bytes             | 1,544,508 | 1,546,558 | 253,526        |
| entries                      | 13,523    | 13,578    | 991            |
| of which named               | 2,527     | 2,550     | 155            |
| derived `<name>_entry`       | 683       | 688       | 40             |
| still `func_<ADDR>`          | 10,313    | 10,340    | 796            |
| bytes emitted as code        | 1,531,131 | 1,533,155 | 252,331        |
| share of the code ranges     | 99.13%    | 99.13%    | 99.53%         |
| share of the image           | 36.81%    | 41.71%    | 32.09%         |
| instructions                 | 579,529   | 580,174   | 88,617         |
| `.byte` escapes              | 80        | 93        | 12             |
| local branch labels          | 49,528    | 49,601    | 9,257          |
| unreached code decoded       | 13,356    | 13,382    | 1,162          |
| code-range bytes left binary | 0         | 0         | 0              |
| reflection tables as `.long` | 21        | 22        | 3              |

At `1a0e9e21f` the KN6000 / KN6500 columns read 1,544,130 / 1,546,180 code-range bytes, 13,507 /
13,562 entries and 3 code-range bytes left binary (1 piece each). Lane generic-zero added the
dispatchers' 381 bytes as a code range (`--code 0x3f78b4:0x3f7a31` / `0x381514:0x381691`) and
ended the boot header's code range at `0xd` instead of `0x10`, so its last 3 bytes, the binary
piece, are typed data now: +378 code-range bytes.

At `2319e9b94` (2026-10-24) 19,825 (KN6000) / 16,003 (KN6500) / 1,162 (plug-in) code-range bytes
were still binary. `gen_image_s.py --decode-gaps` now decodes code that no traced path reaches,
run by run. The rest of each image is the data region, typed as described on
[Program Data & GUI]({{ site.baseurl }}/kn6000-program-data/).

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

- Names: most entries are still `func_<ADDR>` (9,917 / 9,972 `func_` labels after lane
  sibling-names, above). Most of 941's names the siblings lack belong to code the sibling changed
  or does not have; routines that differ slightly from their KN7000 versions need another method
  than exact matching or call-site alignment, and names from the KN2400's and from each other's
  reflection tables have not been carried across yet.
- Most RAM and I/O addresses are still numbers in the sources (17,752 / 17,788 numeric work-RAM
  operands): 941 itself names few RAM variables, so its RAM map carries 8 or 9 names per sibling;
  each KN7000 RAM name added later reaches them by a re-run of `make aligned-names`. Data addresses the code uses are
  named from the typed data's labels (`labels.sym`, read by `gen_image_s.py`), except a few that
  fall inside typed items.
- The data still declared opaque (54,782 / 59,027 / 2,981 bytes in the census snapshot
  `docs/coverage/data-incbin-2026-10-31-02`, where all three trees read generic 0; 39,985 / 44,212 / 594
  after lane mn10300-rest, measured by its `typer_stats.text_stats`); see
  [Program Data & GUI]({{ site.baseurl }}/kn6000-program-data/#what-is-left-the-census).
- ~~The plug-in's entry vectors, and names for its host calls in place of the table offsets~~: done by
  lane mn10300-rest.
- The table ROMs IC13 / IC14 need dumping before any table tree can exist; see the
  [ROM Dumping Roadmap]({{ site.baseurl }}/rom-dumping-roadmap/).

Each folder's `README.md` in the disassembly repository is the reference for the above.
