---
layout: page
title: "KN7000 Menu Map"
permalink: /kn7000-menu-map/
---

# KN7000: the GUI objects in the source, and the menu map

The KN7000 draws every screen from data. Program build 941 holds **8,509 widget records** in 36
blocks, each one an instance of one of **518 MILK classes** that the firmware describes itself:
name, parent class, size, and a name and a type character for every field. Since 2026-10-29 the
disassembly writes each record as one line named by its class, nested under its parent, with its
links, colours, borders, titles and procedures by name, and a generated menu map lists every
block, screen and widget. This page summarises both. The other data of the same region (tables,
records, songs, the resource-id trie) is on [Program Data Region]({{ site.baseurl }}/kn7000-data-region/).

The lane notes behind this page are
[`kn7000/notes/gui-data-region/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/gui-data-region/README.md)
in the disassembly repository (lane gui-kn7000 of the 2026-10-29 data-semantics effort).
Builds 942 (SP7001), 935 and 893 get the same source from the same generator, and the SP7001's
table-flash plug-in has its own screens, on [SP7001 Plug-in Screens]({{ site.baseurl }}/kn7000-sp7001-plugin/).

## What the source looks like

```
	Screen	PanelSimulator, sub=PanelSimulator_ExitMode1, flag=VF_Const, X=0, Y=0, W=640, H=240, color=CL_Green, border=BD_Double1, index=0xFFFF, exit=TT_PS, window=PanelSimulator_window
		IvExitMode	PanelSimulator_ExitMode1, super=PanelSimulator, next=PanelSimulator_TitleMenu_DEBUG_TOOLS, flag=VF_Const|VF_InvisibleBox, X=0, Y=0, W=32, H=32, mode=MD_NORMAL
		AcTitleMenu	PanelSimulator_TitleMenu_DEBUG_TOOLS, super=PanelSimulator, ..., X=327, Y=200, W=305, H=38, ..., editsw=ES_Right5, str=Str_DEBUG_TOOLS, title=TT_DEBUG, icon=1	# str "DEBUG TOOLS"
```

(`kn7000/src/program/data/data_00.s`, abridged.) The indentation is the widget tree. Links are
object names, `title=TT_DEBUG` is the title the entry opens, and `gui_ids.inc` says which screen
each title shows (`TT_DEBUG` opens `TtDebug`).

| file                                | what it holds                                                                    |
|-------------------------------------|----------------------------------------------------------------------------------|
| `src/program/data/data.s`           | the region's top file: includes the constants, the two `.inc` files, the parts   |
| `src/program/data/data_NN.s`        | the region in address order: tables, records, strings, gaps                      |
| `src/program/data/gui_classes.inc`  | one assembler macro per MILK class that a record uses, plus CLASS / OBJ / IDNAME |
| `src/program/data/gui_ids.inc`      | the TT_ (title), MD_ (mode) and OTB_ (OT block) ids, each with its screen        |
| `src/program/data/labels.sym`       | every data label (address, name, item size), read by `gen_program_s.py`          |
| `notes/gui-data-region/menu-map.md` | the generated menu map                                                           |

(Paths under `kn7000/`.) The tools are `kn7000/tools/milk_model.py` (which bytes are MILK classes,
tables and widget records, and what each field is; `--check`), `gen_data_s.py` (the region as typed
source, `make data-src`), `gui_menu_map.py` (`make gui-map`, `make verify-gui-map`) and
`gui_readability.py` (records typed, ids, links and addresses still spelled as numbers). The
assembler `kn7asm.py` gained `.macro` / `.endm` with defaults and keyword arguments for this.

## The registry

`RegisterObjectTable` (CPU `0x4842A717`) copies a 16-byte `{u32 class, u32 proc, u16 count, u16 pad,
u32 table}` to `0x5011FAAC + 16 * slot`. The program makes 400 such calls, 396 of them from the 36
`InitializeBlockNN` routines, 11 per block, at slots `16 * N + k`:

| k | class        | table holds                                                    |
|---|--------------|----------------------------------------------------------------|
| 0 | Viewable     | pointers to the block's widget records                         |
| 1 | Function     | code pointers (9: their names)                                 |
| 2 | ApFunction   | code pointers (10: their names)                                |
| 3 | MainFunction | code pointers (11: their names)                                |
| 4 | Class        | 24-byte class records                                          |
| 5 | Event        | pointers to EV_ names                                          |
| 6 | Method       | pointers to MT_ names                                          |
| 8 | ResName      | pointers to the widget records' names, index-parallel to k = 0 |

An id is `(slot << 16) | index`: class ids `0x0004KKKK`, event ids `0x0005KKKK`, method ids
`0x0006KKKK`, an object of block N `(16N << 16) | index`, a function `((16N + k) << 16) | index`.
The evidence is `ClassProc` (`0x4842A802`), which indexes the table of registry slot `id >> 16` with
`id & 0xFFFF` times `0x18`, and itself sends method `0x00060025`, block 0's Method entry `0x25`.
`RegisterOTBlock` (`0x484317D1`, slot `0xC`), `RegisterTitle` (`0x48431836`, slot `0xF`; the
`0x1C`-byte records at `0x50031C64` hold the screen object's id and the OT block) and
`RegisterMode` (`0x484317EC`, slot `0xE`) give **36 OT blocks, 283 titles and 21 modes**, written as
the ids of `gui_ids.inc`.

This is not the KN5000's layout. The KN5000 groups its tables by kind (all Viewable tables, then all
Function tables, ...), and so do the KN6000, KN6500 and the HD-SX plug-in
([KN6000 Program Data]({{ site.baseurl }}/kn6000-program-data/)); the KN7000 and the KN2400 group
them by block.

## Classes

The 24-byte class record and its field names are the KN5000's (see
[UI Framework]({{ site.baseurl }}/ui-framework/)): proc `+0`, parent `+4`, u16 allsize `+8`, u16
selfsize `+10`, name `+12`, propdata `+16` (one type character per own field) and propname `+20`
(pointers to the own fields' names). 518 classes are in 36 tables.

What differs is the layout: the KN7000's compiler **aligns**. A class's own fields form a C struct
(each field at a multiple of its size, the rect at a multiple of 2, padded to its widest field); it
starts at the parent's `allsize` rounded up to its alignment, and `allsize` is the end rounded up
to 4. `milk_model.py --check` asserts selfsize and allsize for all 518 classes, and every super /
sub / next / prev link of the 8,509 records: 0 failures. The padding the macros write as `.space`
is zero in every record.

## Widget records

A record is its class chain's fields, root first. Viewable's are the class id `+0`, super / sub /
next / prev `+4`..`+10` (indices in the same Viewable table, `0xFFFF` for none), flag `+12` and the
rect `+14` as {left, top, right, bottom}. *[INFERENCE]* right and bottom are inclusive: the
full-screen `Screen` objects hold 0, 0, 639, 239 on the 640 x 240 LCD, so the macros take X / Y /
W / H and store X + W - 1 and Y + H - 1.

33 records, and every state variable a record points at (selected, onoff, window, parent, child,
...), are in the initialised work-RAM image that `ResetEntry` (`0x4840FF7E`) copies from ROM
`0x487B0B78` to RAM `0x50000010` (`0x7F34` bytes). That image is assembled under
`.mnbase 0x4FC4F498`, so its labels are the RAM addresses the code and the records use.

How a field value is spelled; the type character is the class table's own:

| type            | fields (most common)                      | spelled as                                          |
|-----------------|-------------------------------------------|-----------------------------------------------------|
| `[`             | super sub next prev                       | object name                                         |
| `P`             | rect                                      | `X=, Y=, W=, H=`                                    |
| `\`             | flag                                      | `VF_*` bits                                         |
| `]`             | color fontcolor ...                       | `CL_*`                                              |
| `^`             | border                                    | `BD_*`                                              |
| `e`             | editsw editsw2                            | `ES_*`, the soft key the widget answers             |
| `X`             | str caption title stron stroff            | string label, the text in the line's comment        |
| `a`             | exit title titleNowN ...                  | `TT_*` title id                                     |
| `` ` ``         | mode                                      | `MD_*` mode id                                      |
| `s` `N`         | window screen                             | `<object>_id`                                       |
| `j` `k`         | func main_func                            | `FN_*` function id                                  |
| `l` `m` `q` `r` | selected onoff window parent ...          | label of the RAM state variable, `<object>_<field>` |
| others          | index, length, font, icon, bmp, align ... | decimal                                             |

The `CL_` / `BD_` / `ES_` / `VF_` names are the firmware's own name / value tables
(`kn7000/src/constants.inc`, `tools/gen_constants.py`).

**Object names.** A record whose ResName is not empty (2,200 of 8,509) is named by it. The others
are named `<nearest named ancestor>_<class without its Vw/Ac/Ps/Iv prefix>`, plus the label text
when the record shows one, numbered when that repeats. Those names are the source's own: the
firmware has none for those objects.
Since 2026-11-06 they are frozen: each tree's `<src>/data/gui_object_names.tsv` (941: 6,309 rows;
object id = slot << 16 plus the index, class, name) is read before any name is made and written back
by each run, so a regeneration reproduces every name, and editing one row renames that object and
its `next` / `prev` / `OBJ` references and nothing else; a name is invented only for an object the
table lacks or whose class changed (lane mn10300-data3, disassembly
`kn7000/notes/mn10300-data3/README.md`).

**Ids in the code.** `gui_event_ids.inc` and `gui_code_ids.inc` define the ids the data registers,
and the code generator writes them by name in `mov IMM, dN` / `cmp IMM, dN`: 11,405 EV_ / MT_
immediates in 941, and 902 `FN_`, 333 `CLASS_`, 176 `TT_` and 64 `MD_` ids, besides object ids
such as `DiskWaitWin_id`. The IDNAME tables compute the same values from their positions and the
code's bytes check them: an id that disagreed would change an instruction.

## The menu map

[`kn7000/notes/gui-data-region/menu-map.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/gui-data-region/menu-map.md)
is generated from the typed source by `tools/gui_menu_map.py`:

```
make -C kn7000 gui-map          # regenerate
make -C kn7000 verify-gui-map   # exit 1 when stale; part of make gate-kn7000
```

Per object it gives the class, name, label text, rect (X,Y WxH), and where a title menu, screen
menu or exit leads; its last section is the title index (title, screen, which entries lead to it).
It is a static reading of the records: a screen chosen at run time by code is not in it.

The blocks at a glance (top-level objects are the `###` headings of the map, objects its widget
lines; the table is printed by `tools/menu_map_summary.py --blocks` in this site's repository):

| block     | top-level | objects | first top-level objects                                             |
|-----------|-----------|---------|---------------------------------------------------------------------|
| PS        | 3         | 9       | PanelSimulator, ClipBoard, DefaultWindow                            |
| APSTYLE   | 7         | 81      | OneTouchPlay, MusicStylistMenu, MusicStylistCategory, ...           |
| DEBUG     | 8         | 61      | TtSoftver, TtDebug, TtMemoryDump, ...                               |
| NAMING    | 2         | 45      | NamingWindow, TtNaming                                              |
| MESSAGE   | 9         | 29      | MESSAGE_TtMessage, NoMessage, Completed, ...                        |
| WELCOME   | 4         | 7       | WELCOME_TtWelcome, AllInitial, FactoryInitial, ...                  |
| SOUND     | 24        | 323     | TtSdmenu, SOUND_TtSdpart, SpsPage1, ...                             |
| HOMEPAGE  | 41        | 595     | TtHomepage, HpParts1, HpVolNm1, ...                                 |
| SNDRHY    | 19        | 239     | SNDRHY_TtSvari, SvariNormal, SvariDrawbar, ...                      |
| FAVORITE  | 6         | 83      | TtFavorite, TtCtFavorite, FavBankNaming, ...                        |
| APSTCNV   | 7         | 40      | STYLCNVWAIT, STYLCNVMODL, STYLCNVCNVT, ...                          |
| DIAG      | 53        | 372     | stest1, test1_ram, test1_rhyrom, ...                                |
| CUSTOM    | 11        | 80      | writeprt, cusmenu, custommem, ...                                   |
| CONTROL   | 12        | 75      | controlmenu, initial, CONTROL_Window1, ...                          |
| MIDI      | 20        | 154     | MdMenu, MdPart, MdCtrl, ...                                         |
| PMEM      | 7         | 48      | PmBkSel, PmBkSelWindow1, PmBkSelWindow2, ...                        |
| VOCALIST  | 3         | 23      | VocalistWorkstation, VocalistWindow1, VocalistWindow2               |
| SOUNDEDIT | 49        | 1143    | TtSeMenu, TtSeTone, Tone1, ...                                      |
| APDP      | 14        | 140     | APDP_SeqTrackSwitchWin, APDP_SeqCycleClearWin, DirectPlaySwWin, ... |
| CMPMSPCMN | 6         | 139     | CmpMspStepScreen, CmpStepWin1, CmpStepWin2, ...                     |
| SND_ARG   | 1         | 6       | SndArgrScreen                                                       |
| CMP       | 47        | 584     | CmpMenuScreen, CmpBkslScreen, CmpBkslSScreen, ...                   |
| MSP       | 29        | 398     | MspMenuScreen, MspBkslScreen, MspRealScreen, ...                    |
| VDOUT     | 1         | 4       | VideoOutScr                                                         |
| FMA       | 54        | 632     | DiskMenu, DiskWaitWin, DiskDeleteSureWin, ...                       |
| SEQUENCER | 91        | 1308    | SeqMenuScreen, SeqEasyRecScreen, SeqPlayScreen, ...                 |
| DEMO      | 3         | 37      | TtDemoMenu, TtDemoMenuPR804, TtDemoMenuPR604                        |
| CONTRAST  | 2         | 9       | TtContrast, WriteWindow                                             |
| SDFM      | 57        | 839     | SdCardMenu, SdCardLoad, SdCardTools, ...                            |
| EFF       | 21        | 326     | Aloc, LoadFilter, Mixing, ...                                       |
| APC       | 5         | 63      | SplitSel, ApcSel, ChdFdr, ...                                       |
| APSDPLY   | 10        | 176     | SDAudPlayScreen, SDAudLsSelScreen, SDSndPlayScreen, ...             |
| SLIDESHOW | 3         | 16      | TtSswRun, TtSswList, TtSswListRename                                |
| HELP      | 5         | 35      | HelpFunction, HelpText, HelpAPCMENU, ...                            |
| PCCOM     | 2         | 3       | PCCom, AMCOM                                                        |
| DEMORUN   | 118       | 387     | demo1_1, fdemo_a1, fdemo_a2, ...                                    |

The [Sound GUI Map]({{ site.baseurl }}/kn7000-sound-gui-map/) draws the sound screens' navigation
from the owner's manual; the generated map is the firmware's own view of the same screens (blocks
SOUND, SNDRHY, SOUNDEDIT and EFF).

## Readability census

`kn7000/tools/gui_readability.py`, before at the plan's baseline (disassembly `b58b8f696`) and after
at `3ce1d3fcb`:

| tree                 | records typed | records in blobs | raw ids | numeric links | numeric addresses | code -> data nums | unnamed fields |
|----------------------|---------------|------------------|---------|---------------|-------------------|-------------------|----------------|
| before, 941          | 0             | 8509             | 0       | 0             | 0                 | 12433             | 0              |
| after, 941           | 8509          | 0                | 0       | 0             | 7                 | 1                 | 0              |
| after, 942 (sp7001)  | 8510          | -                | 0       | 0             | 7                 | 1                 | 0              |
| after, 935           | 8509          | -                | 0       | 0             | 6                 | 1                 | 0              |
| after, 893           | 8501          | -                | 0       | 0             | 7                 | 8                 | 0              |

"raw ids" counts record fields given as a hex number shaped like a MILK id. The numeric addresses
left are pointers into the library image that no label names; "code -> data nums" are ROM views of
the RAM-init image (the copy loop's source address and the like), kept as numbers on purpose.

## Open

- *[INFERENCE]* the rect's right / bottom are inclusive (from the full-screen objects only).
- `D` (the type character of `IvSDPlayTimer` / `IvSDFwdRewTimer`) may be 1 byte rather than 2;
  both classes pad to 8 either way.
- The names given to the 6,309 objects with an empty ResName are invented (parent + class +
  text). ~~They are stable across regenerations only while the tree is~~: since 2026-11-06 they are
  frozen in `gui_object_names.tsv` ([Widget records](#widget-records)).
