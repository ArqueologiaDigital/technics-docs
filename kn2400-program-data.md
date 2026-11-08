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
  through `func_486D4A2A`, as the KN7000's `DemoSongLoad` / `func_48533758` do. The song record's
  signature is `01 0E` (`0x8E0` bytes), measured on the 8 songs; all 24 streams are typed inside
  `.zlib 6` blocks.
- **Built-in style**: `TechnicsRhythmsResource` (`0x4852BD9C`), IC18's format with one style.
- **Bitmaps**: 45 bitmap resources, PNG in `media/`, besides 3 JPEG and 2 BMP files.
- **`RamCodeTrailer`** (`0x487965B8`, 27 bytes after the RAM-linked code): 7 bytes, then
  `0x487285BE`, `0x50120000`, `0x00038003`, `0x487965B8`, `0x5018FFF0`, a copy descriptor; its
  immediates are spelled `RamCodeTrailer+3` ... and `RamCodeTrailerWords+N`. `RamSectionsCopy` (`0x4870587E`), crt0_start's last call before `KernelStart`, walks
  the 12-byte records {u16 flags (bit 15 = last), u16 length, u32 source, u32 dest} from `RamCodeTrailer+3`, each
  field read byte by byte: {`0x0002`, `0xDFFA`, `0x487285BE`, `0x50120000`} copies the RAM-linked code, `0x6DFFA`
  bytes (the next record's source minus this one's), and {`0x8003`, 3, `0x487965B8`, `0x5018FFF0`} copies the
  trailer's first 3 bytes (`de 00 00`, `retf [], 0`) to `0x5018FFF0`. So the KN2400/KN2600 copies its RAM-linked
  tone-generator library itself (settled 2026-11-02, lane mn10300-names; disassembly
  `kn2400/notes/data-region/README.md` and the row of `RamSectionsCopy` in `kn2400/kn2400_manual.sym`). (Corrected by lane generic-zero, disassembly `c65a62c5b`: the notes, and
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

**The Music Stylist.** `StyleRecordTable` (720 records at `0x48571564`) and `StyleRecordTableKN2400`
(680 records at `0x48577738`, was `StyleRecordTableAlt`) are the KN7000's 24-byte `MusicStylistSetup`
records. Lane mn10300-formats (2026-10-31, [`kn7000/notes/mn10300-formats/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/mn10300-formats/README.md), section 1) settled which list is whose:
`KnprModelGet` (`0x487055C4`, was `func_487055C4`) reads the board strap at `0x98070000` and answers
0 for the KN2600, 1 for the KN2400 and 2 for the PR54
([the strap table]({{ site.baseurl }}/kn2400-kn2600/#one-firmware-image-three-models)). Five routines
pick the KN2400's list for 1 and the other for 0 and 2:

| routine (was)                      | KN2600 / PR54 list (count)         | KN2400 list (count)                  |
|------------------------------------|------------------------------------|--------------------------------------|
| `MssSetupGet` (func_48641CCD)      | `StyleRecordTable` (720 x 24 B)    | `StyleRecordTableKN2400` (680)       |
| `MssSetupIndexGet` (func_48641D02) | `StyleSetupIndexTable` (720 x u16) | `StyleSetupIndexTableKN2400` (684)   |
| `MssGenreGet` (func_48641D2F)      | `StyleGenreTable` (11 x 8 B)       | `StyleGenreTableKN2400` (11)         |
| `MssLetterGet` (func_48641D5E)     | `StyleAlphabetTable` (34 x 8 B)    | `StyleAlphabetTableKN2400` (34)      |
| `MssEraGet` (func_48641D8D)        | `StyleEraTable` (10 x 12 B)        | `StyleEraTableKN2400` (10)           |

The record kinds are the KN6000's (`StyleGenre`, `StyleLetter`, `StyleEra`, `MusicStylistSetup`).
Both sets point at the same one-touch settings. Those are `0xA0` bytes, the KN7000 layout with `PM_PART_TAIL` x 4, typed with the
one-touch macros ([Panel Memory Records]({{ site.baseurl }}/kn7000-panel-memory/)): 719 of the 720;
the one left out does not fit the masks.

**The note-conversion rules.** The KN2400's copy of `NoteConvRules` (`0x4854B24C`, 128 x 8 bytes) is
read by `NoteConvApply` in the RAM-linked code, which the reader walk follows: `+4` is loaded at
`NoteConvApply_entry_L13` (`0x50173F61`), and the answers for `+1` / `+2` / `+3` come from `NoteConvRuleByte1Get`,
`NoteConvRuleByte2Get` and `NoteConvRuleByte3Get`. The tables it points at are the KN7000's `NoteConvTable`, as on
the [KN6000]({{ site.baseurl }}/kn6000-program-data/#the-note-conversion-rules).

**The built-in "Technics Pads" bank.** `TechnicsPadsResource` (`0x48532260`), the table flash's
segment 4 format, typed with the pads' events one per line.

## The DSP-effect descriptors (lane mn10300-formats)

The "1,089 small pieces between effect names" at `0x48439000..` were one structure: **107 effect
descriptors and their 809 parameter records**, tiling `0x48439000..0x48440898` (30,872 bytes) with no
gap ([`kn7000/notes/mn10300-formats/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/mn10300-formats/README.md), section 3; `kn7000/notes/mn10300-formats-probes/kn2400_fx_desc.py`).
`FxDescGet` (`0x4863CDEF`) answers `FxDescTable[FxDescIndexGet(effect code)]` (`0x4856C74C`, 260
pointers); `FxCategoryGet` maps the effect code to one of 15 categories whose jump tables decide how
the index is found. Each field is named by the routine that reads it:

| record           | fields                                                                                                                                                                                                                                                                                                                               |
|------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `FX_DESC`, 16 B  | `count` records at `params` (right before the descriptor); `nparams` (`FxDescNParamsGet`); `connection` (`FxDescConnectionGet`); `speed_param`, `tempo_param`, `drive_param`, each a parameter number or -1 (`FxDescSpeedParamGet`, `FxDescTempoParamGet`, `FxDescDriveParamGet`); `send_param` (`FxDescSendParamGet`); 3 zero bytes |
| `FX_PARAM`, 36 B | the name, NUL-padded to 20 bytes; `number`, `min`, `max` (`FxParamNumberGet`, `FxParamMinGet`, `FxParamMaxGet`); `band` and `sub` (`FxParamBandGet`, `FxParamSubGet`); `variant` (`FxParamVariantGet`); `depth_link` (searched by `FxParamNextDepthLinked`); 2 zero bytes; `values`, the value texts (`FxParamValuesGet`)            |

- `send_param` is the REVERB SEND parameter's number ("106 of 106" in the lane's count) and -1 in the
  reverbs.
- The four fields that were `mode`, `pnum9`, `pnum10` and `pnum11`, and FX_PARAM's `x29`, were named by
  lane mn10300-rest from their readers ([`kn7000/notes/mn10300-rest/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/mn10300-rest/README.md),
  section 1; probe `kn2400_fx_pnums.py`):
  - `connection` (+8): `FxConnectionGet` maps it to the unit's connection message (kind 9), and
    `SndUnitDbGroupQuery` and `FxDepthApply` act for 1 and 2. It is 0 for reverbs, choruses and gates, 1
    for depth effects, 2 for rotary / amp / wah / pitch, 3 for Dry/Wet (*[INFERENCE]* a connection type);
  - `speed_param` (+9): `FxSpeedNudge` (`0x4863B51E`, which nothing calls) moves that parameter by
    (value - 0x40) within its min / max: LFO SPEED, SLOW LFO SPEED or PEDAL, in the 27 descriptors that
    set it;
  - `tempo_param` (+10): `FxParamValueGet` answers GetM3Em id 4 (TEMPO) for that parameter instead of its
    stored value: the two "TEMPO" effects;
  - `drive_param` (+11): an effect of the same type is reloaded with its parameters kept (kind 5) only
    when it is -1; it is the DRIVE of the 9 rotary / amp twins;
  - `depth_link` (FX_PARAM +0x1D): 0 when the parameter follows the depth control; `FxDepthApply` scales
    every such parameter by the control / 0x50, clamps it and posts it.
- `band` / `sub` are 0..4 / 0..2 in the EQ's band parameters: frequency, Q, gain.
- `variant` is 0 and 1 for two alternative records of one number ("DEPTH" / "DEPTH (V)", "SPEED FAST" /
  "SLOW"), 0xFF for a record always shown.

`gen_data_s.py`'s `fx_descriptors()` pass (profile key `fx_descriptors`, the KN2400 only) writes them
one line a record. The KN7000's `SndUnitDbGroupQuery` / `SndRec*` routines are the same family, but the
KN7000's records are not this layout.

## The effect DSP's programs, scripts and maps (lane mn10300-rest)

The SX-KN2400 downloads a program into its effect DSP for each effect type. The "20 KB of
`7c aa aa 7d 55 55 ...` streams" were one family, `0x48533EAC..0x48541618` (55,148 bytes): for each of the
208 DSP types a **program stream**, a **parameter script** and an **address map**, plus the six units' idle
programs, the boot and clear streams and three coefficient waves
([`kn7000/notes/mn10300-rest/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/mn10300-rest/README.md),
section 1; probe `kn2400_fx_streams.py`). Nothing loads from them directly: four pointer tables are their
only readers, which is why the reader search had called them opaque.

| table                    | reader                                                        | blocks |
|--------------------------|---------------------------------------------------------------|--------|
| `FxTypeProgramTable`     | `FxDspProgramLoad` (`0x50189F4E`)                             | 103    |
| `FxUnitIdleProgramTable` | `FxDspProgramLoad` (type 0)                                   | 6      |
| `FxTypeScriptTable`      | `FxDspParamApply` (`0x5018A267`)                              | 89     |
| `FxTypeMapTable`         | `FxDspParamApply`                                             | 85     |
| boot / clear / waves     | `FxDspBoot`, `FxDspClearRun`, `FxDspQueueFlush`               | 9      |
| orphans (nothing points) | parsed as the kind they parse as (*[INFERENCE]* older copies) | 22     |

- **Program streams** (`FxDspStreamExec`): records of a kind byte and a 12-bit length counting the whole
  record. 0xFB raw bytes (sent after a 12-byte command), 0xFC 4-byte program words (word i to step
  `FxUnitProgramBase[unit]` + i, `FxDspStepWrite`; 6,785 words), 0xFD / 0xF7 big-endian u24 coefficients
  from an address (0xFD as one burst, `FxDspBurstWrite`; 0xF7 each after register 0xFF = its address),
  0xFE {u16 register, u24 value} pairs (`FxDspIndirectWrite`), 0xFF the end. The `7c aa aa 7d 55 55 ...`
  bytes are 19 0xF7 records at coefficient 0x8D, 33 values each, a curve from 0x800000 to 0x7FFFFF.
- **The chip's interface.** The DSP sits behind the halfword registers at `0x98050000 + 2 x reg`
  (`FxSerialRegWrite`), busy on bit 2 of `0x98070000`; its chip select, reset and strobe are bits 4, 2 and
  1 of the write-only latch `0x98000000` (`Latch98000000Set` / `Latch98000000Clear`).
- **Parameter scripts** (`FxParamScriptRun`, `FxScriptGroupFind`, `FxParamEntryExec`): one group per
  parameter number, {u16 big-endian length, entries {kind, index into the kind's map group, operands},
  0x7A}, 0xFF after the last group. They turn the panel value v into coefficients: kinds 0x64 / 0x66 /
  0x21 take {u24 lo, u24 hi} and give lo + (hi - lo) x v / 99 (0x21 doubled), 0x67 an offset plus v
  milliseconds in samples, 0x68 x v / 180, and 0x79 bypasses the unit and runs `FxDspClearStream`. Eight
  groups of types 96..99 (no descriptor, no name) and the map of type 127 do not tile; they stay bytes
  (*[INFERENCE]* never reached).
- **Address maps** (`FxMapAddrFind`): groups {u16 BE length, kind, u16 BE DSP addresses}, 0xFF after the
  last: the DSP addresses each script entry writes.

`gen_data_s.py`'s `fx_streams()` pass (profile key `fx_streams`) writes them one macro a record (`FXP_*`,
`FXS_*`, `FXM_*` in `src/include/data_tables.inc`), labelled `FxProgram_<type>`, `FxScript_<type>`,
`FxMap_<type>` and `FxUnitIdleProgram<unit>`, each header naming the types and their effect names. The type
is the `FxDescTable` index, which the effect presets (`FxPresetTable`) hold at +0x12 (`FxDescIndexGet`).

**zlib's tables and field names.** Lane mn10300-formats named zlib 1.0.4's 19 data tables, found by
their contents, in this tree's manual symbol file too (`cplens`, `cplext`, `static_l_desc`,
`inflate_mask`, `z_errmsg` ...), and the record macros' fields are now named after what the code does
with them: 524 of the KN2400's 1,281 fields have a name, against 36 before
(`field_names_census.py`). The method and every tree's figures are on
[KN7000 Program Data Region]({{ site.baseurl }}/kn7000-data-region/#field-names-from-their-use).

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

## Blocks a routine is handed

Lane callee-walk (2026-10-30,
[`kn7000/notes/callee-walk/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/callee-walk/README.md))
follows a block's address into the routine it is passed to, through register and stack arguments
([calling convention]({{ site.baseurl }}/kn7000-firmware/#calling-convention)); most of the KN2400's
address-only pieces are handed over on the stack, or parked in the caller's frame and reloaded just
before the call. With the frame slots, address joins and return sets it shares with the KN6000
([KN6000 / KN6500]({{ site.baseurl }}/kn6000-program-data/#blocks-a-routine-is-handed)), its switch
descriptors are records (`func_5016B726_Result`, 18 bytes) and the blocks the routines read are
`REC_<routine>_Arg<slot>` records. Measured against disassembly `2a7b45be5`
(`kn7000/notes/callee-walk-probes/callee_walk_stats.py`; n / bytes):

| measure                     | before        | after         |
|-----------------------------|---------------|---------------|
| address-only reader rows    | 380 / 18,475  | 123 / 7,849   |
| read-at-a-width reader rows | 3 / 109       | 51 / 1,833    |
| all reader rows             | 431 / 18,853  | 221 / 9,949   |
| callee records              | -             | 30 / 420      |
| pointed records             | 2406 / 37,688 | 2700 / 42,535 |

The 51 "read" pieces are switch descriptors the code now reads (at +4, s16) whose records did not fit.
With the walk on the KN2400 types 8,378 more bytes of its data region (`callee_off_on.py`); 8 bytes
(`TtSdkeyscl_Table` tails and two table pieces) that reader tables held are rows now. The 123
address-only blocks left are rows because the routine hands the pointer on or stores it and reads no
field (42 / 5,789 bytes), it goes to a library routine (31 / 496), a routine stores it in a timer,
registry or queue (27 / 892), the address reaches no call the walk sees (18 / 504), or the routine's
reads are lost inside it (5 / 168).

**The opaque count rose** (5,051 / 196,479 -> 5,131 / 196,924: +80 pieces, +445 bytes). The switch
descriptors had been the heads of 32-byte address-only pieces; now that they are records, the 12-byte
blocks their `p8` field points at are pieces of their own, which no instruction reads, so they are
declared opaque ("a typed pointer ... holds their address, but nothing is read through it"). They were
rows before only by being after an address the code loads.

## Pointers, arrays and loops (lane mn10300-typer)

Lane mn10300-typer (2026-10-31, [`kn7000/notes/mn10300-typer/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/mn10300-typer/README.md)) changed the shared typer for every MN10300 tree: a
32-bit field is a pointer into code only where it lands on the first byte of an instruction (a length
decoder, `kn7000/tools/mn10300_insn_len.py`, walks the code from its known entry points; 0 disagreements
with the assembler in any tree), a pointer loop proven to stop at an address ends the array it walks, a
loop's counter is an index, a block a routine steps through is an array of records, and a chain a loop
walks is typed record by record. The rules and the KN7000's figures are on
[KN7000 Program Data Region]({{ site.baseurl }}/kn7000-data-region/#pointers-arrays-and-loops-lane-mn10300-typer).
Here (`typer_stats.py`, all rules off against all on, the same inputs; n / bytes):

| tree   | typed before | typed after | change  | reader rows before | after       | opaque before   | opaque after    |
|--------|--------------|-------------|---------|--------------------|-------------|-----------------|-----------------|
| kn2400 | 1,670,358    | 1,688,962   | +18,604 | 218 / 9,889        | 184 / 8,255 | 4,448 / 172,071 | 3,419 / 155,297 |
The second word of the pointer run at `0x48501B38` (once `ptrs_48501B38`), text typed as a pointer, is text again, so `code_in_data.py` finds no
mid-instruction pointer in the KN2400 any more (1 before). `copied_blocks()` now runs for the siblings:
the 12-byte blocks the switch descriptors' `p8` leads to (`memcpy(.., 12)`) are typed copies. The
doc-quality census rose here (routines without a header 21,233 -> 21,242, `loc_` locals 4,967 -> 4,975):
newly typed records' pointer fields name code addresses no label had (a table of handlers), and a
pointed-to label counts as a routine.
## More of the data typed from the code that reads it (lane mn10300-data)

Every widget's state variable in the initialised RAM -- the selected item of a list, the value of a
number box, the window a screen opens -- is now written at the width its class's procedure reads it,
with that instruction cited. The chord and code maps (128 rows by 64 entries, one row per note, one
column per chord type) and the chord voicings (twelve keys, up to seven notes each, and the
inversions) are tables of their own; so are the lists the firmware walks until an end marker (the
panel buttons' descriptors, the effect programs' command lists, the style lists) and the tables whose
size the code checks before indexing them (the 32-slot hash tables, the 101-entry curves, the 99 words
the hard-disk defaults copy). The SX-KN2400's 548 DSP effect presets are typed with their names and parameters (name, descriptor index, parameter count, parameters, key; read by `FxPresetGet` and `FxDescIndexGet`).

| tree   | typed bytes before | typed bytes after | opaque pieces / bytes before | opaque pieces / bytes after |
|--------|--------------------|-------------------|------------------------------|-----------------------------|
| KN2400 | 1,783,452          | 1,906,859         | 2,885 / 61,226               | 1,192 / 27,313              |

Measured by `kn7000/notes/mn10300-data-probes/data_stats.py --dirs BEFORE AFTER --brief` (typed bytes from
`labels.sym`'s item sizes; opaque pieces as the generator counts them, not the data-incbin census), before =
disassembly `c240d1c0b`, after = the lane's regenerated sources; the rules are the `gen_data_s.FEATURES` keys
(disassembly `kn7000/notes/mn10300-data/README.md`). The census below predates this lane.

## Value names, boot sectors, style lists (lane mn10300-data2)

**The framework's value names, the disk formats' boot sectors, the style lists.** Each of the MILK
framework's 54 support classes (the integer, ID, pointer, rectangle and flag types an object's
properties have) points at a list of value names, `{name, value}` pairs ended by an empty name:
"True" / "False", the view flags `VF_*`, the colours `CL_*`, the borders `BD_*` ...; the classes'
common handler turns a value into its name and back with them. The disk formatters' boot sectors are
typed too: the jump, the OEM name "Technics" and the BIOS parameter block of a 720 KB disk (1,440
sectors, media 0xF9) and of a 1.44 MB one (2,880 sectors, media 0xF0), then a two-byte `jmp $`. The
Music Stylist's genre lists now show every style with its four setups. `gui_ids.inc` also gains the
25 `TT_` names `TitleNameTable` holds for titles no `RegisterTitle` call names (the firmware's 17
placeholders, `_TT_13e` ..., stay unnamed).

| tree   | typed bytes before | typed bytes after | opaque pieces / bytes before | opaque pieces / bytes after |
|--------|--------------------|-------------------|------------------------------|-----------------------------|
| KN2400 | 1,906,859          | 1,916,287         | 1,192 / 27,313               | 801 / 18,746                |

Measured by `kn7000/notes/mn10300-data-probes/data_stats.py --dirs BEFORE AFTER --brief`, before = disassembly
`1345995bc`'s committed data directories, after = the lane's regenerated sources; the rules are the
`gen_data_s.FEATURES` keys `support_values`, `sibling_support`, `boot_sectors`, `panel_700`, `style_lists`,
`reclaim_strings` and `curated_counts` (disassembly
[`kn7000/notes/mn10300-data2/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/mn10300-data2/README.md)).

## Stable names, track lists, the APC / SEQUENCER slider (lane mn10300-data3)

**Stable names, track parameter lists and the APC / SEQUENCER slider.** The firmware's screens
hold thousands of widgets with no resource name of their own; the disassembly invents a name for
each (its screen, its class and the text it shows) and now keeps those names in a table beside the
source (`<src>/data/gui_object_names.tsv`), so that they no longer change when the source is
regenerated: a run reads the table before it makes any name and writes it back, and editing one row
renames that object and nothing else. The five lists of parameter ids that `func_4861CCC5` walks by
index to the end marker -1 (one 32-bit word per id; picked by the sequencer track kind, through the
byte table `func_4861CCC5_Table` for kinds 0..0x12 and `cmp 0x40` / `0x41` / `0x42` for APC, CONTROL and RHYTHM)
are typed as lists; they are the ids a song track of that kind may carry (on the KN7000 82 for a part
track, 62 for PART 10, 12 for APC, 32 for CONTROL, 8 for RHYTHM; see
[Sequencer]({{ site.baseurl }}/kn7000-sequencer/#what-a-song-can-carry)). In the one-touch settings and panel memories, the
byte that was called `m008008` is `apc_volume`, the APC VOLUME (parameter `0x008008`): the APC /
SEQUENCER VOLUME slider (on the KN7000 the panel CPU's input AD2, VR1102; on the KN6000 / KN6500 AD6,
VR1; the KN2400's input was not traced) sets the APC VOLUME while no song plays and the SEQ VOLUME
(`0x008006`) while the sequencer plays, holding the other at full level (127). The other `m<id>`
fields the firmware's own parameter dump names were renamed with it: `master_tune`, `msa_on`,
`apc_type`, `apc_type_alt`, `rhythm_sync`, `drawbar_type`, `tabs_1`, `tabs_2`
([Panel Memory Records]({{ site.baseurl }}/kn7000-panel-memory/#what-is-named)). The C library's
locale tables (`LconvMonetary` / `LconvNumeric`), the voice directory's hash chains and the
chord-recognition table's 2,048 entries are typed in every build.

| tree   | typed bytes before | typed bytes after | opaque pieces / bytes before | opaque pieces / bytes after |
|--------|--------------------|-------------------|------------------------------|-----------------------------|
| KN2400 | 1,916,287          | 1,920,463         | 801 / 18,746                 | 790 / 16,682                |

Measured by `kn7000/notes/mn10300-data-probes/data_stats.py --dirs BEFORE AFTER --brief`, before = disassembly
`2bde950fa`'s committed data directories, after = the lane's regenerated sources; the rules are the
`gen_data_s.FEATURES` keys `sentinel_indexed`, `frozen_obj_names` and `host_widget_vars` (disassembly
[`kn7000/notes/mn10300-data3/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/mn10300-data3/README.md),
merged in `3834c8773`).

## Name tables, message tables, field names (lane mn10300-data4)

The GUI's resource name tables are 512 slots: 256 names, then the 256 file names of the same resources;
the second half is now typed as such. The KN2400's icon table (`names_48545C20`) holds 241 pointers to
"kari.bmp", "i0.bmp" ... in the 256 slots after its names, 1,080 bytes that had been an opaque table
tail. The per-language message tables are typed too: runs of words, each 0 or the address of a
NUL-ended string, that no item held. `ToneTypeFeature` names the per-tone-type record the LFO EDIT
loaders read, as in every tree.

| tree   | typed bytes before | typed bytes after | opaque pieces / bytes before | opaque pieces / bytes after |
|--------|--------------------|-------------------|------------------------------|-----------------------------|
| KN2400 | 1,920,463          | 1,923,193         | 790 / 16,682                 | 769 / 13,880                |

Measured by `kn7000/notes/mn10300-data-probes/data_stats.py --dirs BEFORE AFTER --brief`, before = disassembly
`e53dc9b3a`'s committed data directories, after = the lane's regenerated sources; the rules are the
`gen_data_s.FEATURES` keys `string_ptr_runs` and `named_base_not_end` (disassembly
[`kn7000/notes/mn10300-data4/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/mn10300-data4/README.md),
merged in `8d0865c27`).
Offset-named fields with a reader fell from 160 to 142. Two opaque classes rose a little (binary
program flash 461 / 10,264 -> 462 / 10,282 bytes): remainders of pieces the string rule split, whose rest
now classifies as binary. What is left, largest first: 6,013 bytes inside labelled items (the switch blocks
of `func_5016594F`, and around `func_50186924_Selected_6` 856 bytes of 44-byte records of 24-bit DSP
coefficients in 32-bit words, of which the code selects 7, followed by single-precision floats that the
doubles pass misreads as doubles), and 3,859 bytes of table tails. *Corrected by lane mn10300-data5
([below](#hook-dispatch-lists-accordion-diagrams-copies-lane-mn10300-data5)):* the 856 bytes after
`func_50186924_Selected_6` and the 496 "doubles" after them are the second, unreferenced copy of the
interpolation and float tables, now typed as such.

## Hook dispatch lists, accordion diagrams, copies (lane mn10300-data5)

**Hook dispatch lists.** Parameter changes are fanned out through lists of {mask, value, handler}
records, 12 bytes each: for a parameter id the firmware calls every handler whose `(id & mask) == value`,
until a record whose handler is 0. The dispatcher picks the list by the parameter's group, and the
lists are now typed whole. **Accordion register diagrams.** The accordion tab's register symbols are
18-byte pictures, three cells of five characters and a NUL, blanks and bullets (`0x95` in the
firmware's font), which `AcAcdnTabProc` copies whole (`memcpy` of `0x12` bytes) for drawing; they had
been guessed as strings. **Copies.** Some tables stand twice in an image with nothing seen to read the
second copy; the copies are now written as copies of the typed originals, each item by its own rule,
under `<item>_Copy`. Every image keeps the EQ band labels ("   20", "   25", " 31.5" ...) twice.
The SX-KN2400 keeps its whole set of interpolation tables twice: the 11-point curves `func_50186924`
reads between points (x / 10, so 0 .. 100), the tables of `func_50186981`, and the single-precision
curves of `func_50189206`, `func_5018884C` and `func_5018888A`; the second copy, 1,352 bytes, has nothing
pointing at it. Part of it had been read as doubles: a run of 8-byte words whose halves are each a
plausible single (61 of its 62 words; for real doubles about one in four) is now left to the later
passes, which type it as floats (`gen_data_s.FEATURES` key `float_pairs`, checked by
`kn7000/notes/mn10300-data5-probes/float_pairs.py`).

| tree   | opaque pieces / bytes before | opaque pieces / bytes after | offset-named fields with a reader, lane | at `486525b6e` |
|--------|------------------------------|-----------------------------|-----------------------------------------|----------------|
| KN2400 | 769 / 13,880                 | 729 / 12,004                | 142 -> 131                              | 126            |

By class (`kn7000/notes/mn10300-data-probes/opaque_left.py --tree kn2400`, bytes, base -> after):
false-string 1,795 -> 1,691, table-tail 3,859 -> 2,351, after-string 1,497 -> 1,233, labelled-held 6,013
-> 6,013, other groups 716 -> 716. Before = the base `92b5cc4a7`'s data directories; nothing became newly
opaque (`opaque_diff.py`), and `opaque_left.py` gives the same totals at `486525b6e`; fields by
`kn7000/notes/mn10300-formats-probes/field_names_census.py --md` (disassembly
[`kn7000/notes/mn10300-data5/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/mn10300-data5/README.md),
merged in `4e1d77a5b`). The interpolation tables themselves are still split by the generator into a
4-byte record and a ten-word table, and one is mistyped as a string (`Str_empty_1216`); typed, not opaque,
so outside the census. Next: the switch blocks of `func_5016594F` (the 6,013 labelled-held bytes).

## What is left: the census

The fourth committed snapshot,
[`docs/coverage/data-incbin-2026-10-30-04.txt`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/docs/coverage/data-incbin-2026-10-30-04.txt)
(measured at `b84f732aa`, committed in `a25c88274`; its rows for these trees are those of `-03`, measured at `a9b5cf764` after lanes media-files, code-island and callee-walk merged),
reads for `kn2400` (count / bytes): generated 127 / 134,756 (all of it from PNG files), media 5 /
43,175, opaque 5131 / 196,924, generic 0 pieces, 0 bytes. Before the work the tree held 1,993,350
generic bytes; after lane sib-kn2400, 590,773; in the first snapshot (`data-incbin-2026-10-30-01`)
431 pieces, 18,853 bytes, with opaque 5048 / 197,205; in the second (`-02`, at `141313939`, lane
generic-zero) 0, with opaque 5051 / 196,479. Opaque rose from `-02` to `-03` (`-04` the same) by 80 pieces / 445
bytes, for the reason given [above](#blocks-a-routine-is-handed). The current snapshot,
[`docs/coverage/data-incbin-2026-10-31-02.txt`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/docs/coverage/data-incbin-2026-10-31-02.txt) (measured at `6ca33e656`, committed in `c58fe3de7`), reads generic 0 and opaque 3419 / 155,297, the other columns unchanged: 5131 / 196,924
-> 4448 / 172,071 is the effect descriptors ([above](#the-dsp-effect-descriptors-lane-mn10300-formats)),
the rest lane mn10300-typer's ([above](#pointers-arrays-and-loops-lane-mn10300-typer)).

Lane mn10300-rest (2026-10-31) then took the opaque pieces from 3,419 / 155,297 to 2,885 / 61,226
(measured on its branch's committed sources by `typer_stats.text_stats`, the table "Measurements" of
[`kn7000/notes/mn10300-rest/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/mn10300-rest/README.md);
no census snapshot holds that figure yet): the effect DSP's streams (55,111 bytes,
[above](#the-effect-dsps-programs-scripts-and-maps-lane-mn10300-rest)), the C library's powers of ten
(`Pow10Table` at `0x485288D8`, 309 doubles that `PfDoubleToDecimal` reads), the alphabetical sound lists
of both strap sets, and the parameter-id trie (`ResourceIdTrie`, walked by `ResourceIdFind`, the
KN7000's design). The over-long record array that had run from the trie's 16-entry root over what follows
it is gone.

Lane generic-zero (disassembly `c65a62c5b`; `kn6000/notes/siblings-data-final/README.md`, section
"generic-zero") took it to 0. Every generic piece had a reader, so none could stay a binary include
or be declared opaque:

- `record_start()` stops a record that the walk reads past its first bytes from being taken for a
  short string, so the `func_5014A95C_Records_p0` records (before: `Str_empty_1261`, `Str_4_33`
  ...; the parameter-id trie's leaves, under `ResourceIdTrie` since lane mn10300-rest) are typed;
- the 431 generic pieces are rows at the width and signedness of the reads that land in them
  (`tab_u8` ... `tab_u32`), address words as `.long Label` / `Label+N`, under a header naming the
  readers: 3 pieces / 109 bytes read at a known width, 380 / 18,475 whose address the code only
  takes, and 48 strings. Among them are the KN7000's 260-way switch descriptors
  (at `0x48409720`, `0x48409740`, ... 32 bytes each, `{u32, u16, u16, pointer, u16 ...}` and
  the SysEx the pointer names): u8 rows then, since the code reaches them only as `mov data_X, d0`
  (*[INFERENCE]* by the KN7000's `REC_func_484C01F1_Result`). Others, at `0x48409F34` and
  `0x4840D9C4`, were u8 and u32 rows whose address the code loads as a base. Since lane callee-walk
  all of these are records of the switches that select them: `func_5016B726_Result_0`,
  `func_5016B396_Result_0`, `func_5016B396_Result_23` (all `REC_func_5016B726_Result`, 18 bytes)
  and `func_50186924_Selected_0` (`REC_func_50186924_Selected`, 44 bytes; [below](#blocks-a-routine-is-handed)).

A reader row kept the **reader's** widths, not the callee's layout, until lane callee-walk
([above](#blocks-a-routine-is-handed)); the KN7000 profiles' whole extended walk, tried here, typed
78.1% instead of 82.6% and lost bitmaps, so only its slots, joins and return sets were applied. The opaque bytes fell by 726
while the opaque piece count rose by 3: pieces were split at labels the new records and reader rows
name (not traced one by one). The largest opaque pieces, which no instruction reads:

| run                      | bytes  | what it is, as far as known                                                                                                                                                                               |
|--------------------------|--------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `0x4853C5BE..0x48541488` | 20,065 | `7c aa aa 7d 55 55 7e aa aa 7f ...` command streams; since lane mn10300-rest typed as the effect DSP's programs, scripts and maps ([above](#the-effect-dsps-programs-scripts-and-maps-lane-mn10300-rest)) |
| `0x48430000..0x4843FFFF` | 44,299 | 1,089 small pieces between effect names; since lane mn10300-formats typed as the DSP-effect descriptors ([above](#the-dsp-effect-descriptors-lane-mn10300-formats))                                       |
| `0x4853AF63..0x4853C5AA` | 5,703  | high-entropy bytes, inside the effect-DSP family `0x48533EAC..0x48541618` that lane mn10300-rest typed                                                                                                    |
| `0x484FE008..`           | 5,147  | 8-byte rows of a count and up to 4 notes, *[INFERENCE]* chord voicings (the KN6500 has them too)                                                                                                          |

## Open

- ~~Which of the two Music Stylist lists belongs to which model~~: settled by the model strap
  ([above](#typed-from-its-readers-lane-siblings-final)). Of the other strap-chosen tables, lane
  mn10300-rest named two: `SoundAlphaListTable` / `SoundAlphaListTableKN2400` are the alphabetical sound
  lists that `SoundAlphaListGet` picks (the KN2400's when `KnprModelGet` answers 1), and
  `func_5015A8CC_entry_L21_Table` is the KN2600's parameter-group lists. `func_4865F898_Table` /
  `func_4865F898_Table_2` are still not traced.
- ~~The 20 KB of `7c aa aa 7d 55 55 ...` streams~~: the effect DSP's programs
  ([above](#the-effect-dsps-programs-scripts-and-maps-lane-mn10300-rest)).
- The groups whose reader lane mn10300-rest found but which no generator pass types yet (KN2400 bytes:
  FX presets 18,434, style / setup lists 7,694, chord voicings 5,147, 128 x 64 code / chord maps 4,426,
  terminator-ended lists 4,189, widget variables in the initialised RAM image 3,876, fixed-count tables
  896), and what stays opaque and why: the chord-name tables (no word of the image points into them) and
  the coefficient curves at `0x4840DAF8` (no holder). The list is section 7 of the lane's README.
- ~~Who copies the RAM-linked code to `0x50120000`~~: `RamSectionsCopy`, from the two records of
  `RamCodeTrailer` ([above](#the-kn7000s-milk-layout-throughout)).
- The 123 address-only blocks the callee walk leaves as rows, and the 12-byte blocks the switch
  descriptors' `p8` points at, which nothing reads.
