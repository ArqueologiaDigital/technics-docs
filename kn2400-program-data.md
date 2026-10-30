---
layout: page
title: "KN2400 / KN2600 Program Data & GUI"
permalink: /kn2400-program-data/
---

# KN2400 / KN2600: the program data and the screens

The SX-KN2400 / SX-KN2600 program (v1.1) draws its GUI from **7,322 widget records** in 35 blocks,
instances of 491 MILK classes the firmware describes itself. Since 2026-10-29 the disassembly spells
each record as one macro line named by its class, nested by the widget tree, with its links, rect,
colours, strings, titles and procedures by name (`kn2400/src/program/data/`), and the rest of the
data half of the image is typed from the code that reads it. The KN2600 runs the same image
([KN2400 / KN2600 / PR54]({{ site.baseurl }}/kn2400-kn2600/)); how it is rebuilt is on
[KN2400 / KN2600 Disassembly]({{ site.baseurl }}/kn2400-disassembly/).

The tree uses the KN7000 tree's tools with a profile (`../kn7000/tools/gen_data_s.py --profile
kn2400`), so the [KN7000 Menu Map]({{ site.baseurl }}/kn7000-menu-map/) and
[Program Data Region]({{ site.baseurl }}/kn7000-data-region/) pages describe the method. The lane
notes in the disassembly repository:
[`kn2400/notes/data-region/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn2400/notes/data-region/README.md)
(lane sib-kn2400) and
[`kn6000/notes/siblings-data-final/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn6000/notes/siblings-data-final/README.md)
(lane siblings-final, which covers all four MN10300 siblings).

## The KN7000's MILK layout throughout

Unlike the KN6000, the KN2400 groups its registry tables by block, 16 slots per block, exactly as
the KN7000 does, and `milk_model.py` reads it unchanged: `RegisterObjectTable` `0x48601E82`,
`ClassProc` `0x48601F6D`, `RegisterOTBlock` `0x48608F3C`, `RegisterMode` `0x48608F57`,
`RegisterTitle` `0x48608FA1`. It finds 389 registrations, 491 classes, 7,322 widget records in 35
Viewable tables, 35 OT blocks, 278 titles and 23 modes; `milk_model --check`: 0 failures.

- **Initialised RAM**: `crt0_start` (`0x48705BDF`) copies `.data` from `0x485DD334` to `0x50000010`,
  `0x6E78` bytes.
- **Function names**: `gen_symbols.py` had paired 90 procedures of the SDFM MainFunctions (slot
  `0x213`: names at `0x485CFC18`, 111 entries, an identifier run of 90) 21 entries late. With the
  start-aligned pairing, `kn2400/notes/data-region-probes/fn_table_pairing.py` reads 2,283 table
  entries agreeing and 0 disagreeing, where it read 2,193 and 90 before (disassembly `8037f3750`).
  No page of this site quoted any of the 90 names.
- **Demo songs**: `func_486183E3` inflates song n's three streams (record, events, panel memory)
  through `func_486D4A2A`, as the KN7000's `func_48457350` / `func_48533758` do. The song record's
  signature is `01 0E` (`0x8E0` bytes), measured on the 8 songs; all 24 streams are typed inside
  `.zlib 6` blocks.
- **Built-in style**: `TechnicsRhythmsResource` (`0x4852BD9C`), IC18's format with one style.
- **Bitmaps**: 45 bitmap resources, PNG in `media/`, besides 3 JPEG and 2 BMP files.
- **`RamCodeTrailer`** (`0x487965B8`, 27 bytes after the RAM-linked code): 7 bytes, then
  `0x487285BE`, `0x50120000`, `0x00038003`, `0x487965B8`, `0x5018FFF0`. *[INFERENCE]* a copy
  descriptor. `func_4870587E` reads it, byte by byte from `+3`, 12 bytes a record (`movbu`, each
  word assembled little-endian with `asl 8 / 16 / 24`); its immediates are spelled
  `RamCodeTrailer+3` ... and `RamCodeTrailerWords+N`. What it does with the three words of each
  record was not traced. (Corrected by lane generic-zero, disassembly `c65a62c5b`: the notes, and
  this page, had said nothing reads it.)

- **The MILK kernel's tables and routines** (lane code-island, 2026-10-30,
  [`kn7000/notes/code-island/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/code-island/README.md)):
  the data region holds the three tables the kernel reads, named as on the KN6000 and KN7000 in
  `kn2400_manual.sym`: `KernelServiceHash` (`0x485E41C4`, 16 x {u32 key, code pointer}),
  `KernelRamLayout` (`0x485E4244`, 6 RAM addresses) and `KernelParams` (`0x485E425C`, 14 u16). The code
  that reads them is the KN7000's flash tail, under the same names: `KernelInit` (`0x48728165`),
  `KernelWaitRelease` (`0x4872841C`), the hooks `KernelErrorHook` / `KernelErrorHook2` /
  `KernelWaitAbortHook`, `KernelStart` (`0x48728591`) and `KernelInitHook` (`0x4872859C`); names
  *[INFERENCE]* from what the code does
  ([KN7000 Firmware Images]({{ site.baseurl }}/kn7000-firmware/#the-kernels-flash-tail)).

## Typed from its readers (lane siblings-final)

**The Music Stylist.** `StyleRecordTable` (720 records at `0x48571564`) and `StyleRecordTableAlt`
(680 records at `0x48577738`) are the KN7000's 24-byte `MusicStylistSetup` records. `func_48641CCD`
returns `&StyleRecordTableAlt[i]` when `func_487055C4` answers 1 and `&StyleRecordTable[i]`
otherwise; `func_487055C4` reads bits 0 and 1 of `0x98070000`, the board straps that tell a KN2400
from a KN2600. *[INFERENCE]* The two lists are the two models'; both point at the same one-touch
settings. Those are `0xA0` bytes, the KN7000 layout with `PM_PART_TAIL` x 4, typed with the
one-touch macros ([Panel Memory Records]({{ site.baseurl }}/kn7000-panel-memory/)): 719 of the 720;
the one left out does not fit the masks.

**The note-conversion rules.** The KN2400's copy of `NoteConvRules` (`0x4854B24C`, 128 x 8 bytes) is
read by `func_50173F49` in the RAM-linked code, which the reader walk follows: `+4` is loaded at
`func_50173F49_entry_L13` (`0x50173F61`), and the answers for `+1` / `+2` / `+3` come from `func_50173EF8`,
`func_50173F13` and `func_50173F2E`. The tables it points at are the KN7000's `NoteConvTable`, as on
the [KN6000]({{ site.baseurl }}/kn6000-program-data/#the-note-conversion-rules).

**The built-in "Technics Pads" bank.** `TechnicsPadsResource` (`0x48532260`), the table flash's
segment 4 format, typed with the pads' events one per line.

## The menu map

[`kn2400/notes/gui-menu-map.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn2400/notes/gui-menu-map.md)
is generated by `tools/gui_menu_map.py` (`make -C kn2400 gui-map`, checked by `make
verify-gui-map`). Its header reads 7,322 widget objects in 35 Viewable tables, 686 top-level objects
and 278 titles. The blocks at a glance (printed by `tools/menu_map_summary.py --blocks` in this
site's repository):

| block     | top-level | objects | first top-level objects                                             |
|-----------|-----------|---------|---------------------------------------------------------------------|
| PS        | 4         | 17      | PanelSimulator, ClipBoard, DefaultWindow, ...                       |
| APSTYLE   | 7         | 79      | OneTouchPlay, MusicStylistMenu, MusicStylistCategory, ...           |
| DEBUG     | 8         | 57      | TtSoftver, TtDebug, TtMemoryDump, ...                               |
| NAMING    | 4         | 24      | NAMING_NamingWindow1, NAMING_NamingWindow2, TtNaming, ...           |
| MESSAGE   | 9         | 29      | MESSAGE_TtMessage, NoMessage, Completed, ...                        |
| WELCOME   | 4         | 7       | WELCOME_TtWelcome, AllInitial, FactoryInitial, ...                  |
| SOUND     | 24        | 309     | TtSdmenu, SOUND_TtSdpart, SpsPage1, ...                             |
| HOMEPAGE  | 6         | 76      | TtHomepage, NormVol1, NormVol2, ...                                 |
| SNDRHY    | 17        | 177     | SNDRHY_TtSvari, SvariNormal, SvariDrawbar, ...                      |
| FAVORITE  | 6         | 87      | FAVORITE_TtFavorite, FAVORITE_TtCtFavorite, FavBankNaming, ...      |
| DIAG      | 55        | 346     | stest1, test1_ram, test1_rhyrom, ...                                |
| CUSTOM    | 17        | 96      | writeprt, cusmenu, custommem, ...                                   |
| CONTROL   | 25        | 128     | controlmenu, initial, InitSelPR604, ...                             |
| MIDI      | 20        | 152     | MdMenu, MdPart, MdCtrl, ...                                         |
| PMEM      | 7         | 49      | PmBkSel, PmBkSelWindow1, PmBkSelWindow2, ...                        |
| SOUNDEDIT | 53        | 845     | TtSeMenu, TtSeTone, Tone1, ...                                      |
| APDP      | 14        | 120     | APDP_SeqTrackSwitchWin, APDP_SeqCycleClearWin, DirectPlaySwWin, ... |
| CMPMSPCMN | 8         | 151     | CmpMspStepScreen, CmpStepP1Win, CmpStepWin2, ...                    |
| SND_ARG   | 1         | 6       | SndArgrScreen                                                       |
| CMP       | 47        | 596     | CmpMenuScreen, CmpBkslScreen, CmpBkslSScreen, ...                   |
| MSP       | 30        | 387     | MspMenuScreen, MspBkslScreen, MspRealScreen, ...                    |
| FMA       | 53        | 581     | DiskMenu, DiskWaitWin, DiskDeleteSureWin, ...                       |
| SEQUENCER | 94        | 1330    | SeqMenuScreen, SeqEasyRecScreen, SeqPlayScreen, ...                 |
| DEMO      | 5         | 53      | DEMO_TtDemoMenu, TtDemoMenuKN2400, TtDemoMenuPR54, ...              |
| CONTRAST  | 1         | 5       | CONTRAST_TtContrast                                                 |
| EFF       | 19        | 242     | Aloc, LoadFilter, Mixing, ...                                       |
| APC       | 5         | 63      | SplitSel, ApcSel, ChdFdr, ...                                       |
| SP        | 2         | 16      | SimplePiano, SP_NamingWindow1                                       |
| HSS       | 2         | 12      | HssScreen, StrdptScreen                                             |
| SLIDESHOW | 3         | 16      | SLIDESHOW_TtSswRun, SLIDESHOW_TtSswList, TtSswListRename            |
| PCCOM     | 1         | 2       | PCCom                                                               |
| HELP      | 6         | 46      | HelpFunction, HelpText, HelpAPCMENU, ...                            |
| DEMORUN   | 61        | 207     | demo1_1, fdemo_a1, fdemo_a2, ...                                    |
| SDFM      | 58        | 830     | SdCardMenu, SdCardLoad, SdCardTools, ...                            |
| APSDPLY   | 10        | 181     | SDAudPlayScreen, SDAudLsSelScreen, SDSndPlayScreen, ...             |

The block names are the KN7000's, less its APSTCNV, VOCALIST and VDOUT, plus two of the KN2400's
own, SP (`SimplePiano`) and HSS. Three record fields name a title that no `RegisterTitle` call
registers (ids `0x000F000F` and `0x000F0102`); they stay numbers.

## What is left: the census

The second committed snapshot,
[`docs/coverage/data-incbin-2026-10-30-02.txt`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/docs/coverage/data-incbin-2026-10-30-02.txt)
(measured at disassembly `141313939`, the merge of lane generic-zero), reads for `kn2400` (count /
bytes): generated 127 / 134,756, media 5 / 43,175, opaque 5051 / 196,479, generic 0 pieces, 0 bytes.
Before the work the tree held 1,993,350 generic bytes; after lane sib-kn2400, 590,773; in the first
snapshot (`data-incbin-2026-10-30-01`) 431 pieces, 18,853 bytes, with opaque 5048 / 197,205.

Lane generic-zero (disassembly `c65a62c5b`; `kn6000/notes/siblings-data-final/README.md`, section
"generic-zero") took it to 0. Every generic piece had a reader, so none could stay a binary include
or be declared opaque:

- `record_start()` stops a record that the walk reads past its first bytes from being taken for a
  short string, so the `func_5014A95C_Records_p0` records (before: `Str_empty_1261`, `Str_4_33`
  ...) are typed;
- the 431 generic pieces are rows at the width and signedness of the reads that land in them
  (`tab_u8` ... `tab_u32`), address words as `.long Label` / `Label+N`, under a header naming the
  readers: 3 pieces / 109 bytes read at a known width, 380 / 18,475 whose address the code only
  takes, and 48 strings. Among them are the KN7000's 260-way switch descriptors
  (`data_48409720`, `data_48409740`, ... 32 bytes each, `{u32, u16, u16, pointer, u16 ...}` and
  the SysEx the pointer names): u8 rows with `.long data_48409720+20`, since the code reaches
  them only as `mov data_X, d0` (*[INFERENCE]* by the KN7000's `REC_func_484C01F1_Result`).
  Others, such as `data_48409F34` and `data_4840D9C4`, are u8 and u32 rows whose address the
  code loads as a base.

A reader row keeps the **reader's** widths, not the callee's layout: the walk does not carry a
register argument into the routine that reads it (the KN7000 profiles' extended walk, tried here,
typed 78.1% instead of 82.6% and lost bitmaps, so it was not applied). The opaque bytes fell by 726
while the opaque piece count rose by 3: pieces were split at labels the new records and reader rows
name (not traced one by one). The largest opaque pieces, which no instruction reads:

| run                      | bytes  | what it is, as far as known                                                                                                                                                          |
|--------------------------|--------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `0x4853C5BE..0x48541488` | 20,065 | `7c aa aa 7d 55 55 7e aa aa 7f ...` command streams with names, and more at `0x48537CDC..` / `0x48539DD5..`: *[INFERENCE]* effect-DSP programs, not the KN7000's SHARC record format |
| `0x48430000..0x4843FFFF` | 44,299 | 1,089 small pieces between effect names: effect parameter records nothing reads directly                                                                                             |
| `0x4853AF63..0x4853C5AA` | 5,703  | high-entropy bytes                                                                                                                                                                   |
| `0x484FE008..`           | 5,147  | 8-byte rows of a count and up to 4 notes, *[INFERENCE]* chord voicings (the KN6500 has them too)                                                                                     |

## Open

- *[INFERENCE]* which of the two Music Stylist lists belongs to which model.
- The effect-program blocks' format.
- Who copies the RAM-linked code to `0x50120000`: `func_4870587E` reads `RamCodeTrailer`, but
  what it does with each record's three words was not traced.
- The reader rows of address-only pieces: their layout is the callee's.
