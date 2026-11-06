---
layout: page
title: UI Framework
permalink: /ui-framework/
---

# UI Framework

The KN5000 firmware contains an object-oriented UI framework with 293 classes in v10 (each class record names its "Proc" procedure), event-driven dispatch, property introspection, and a drawing primitives API. The framework manages the 320x240 LCD display, processes control panel input, and routes MIDI events to UI elements.

## Architecture

The UI framework is organized in layers:

1. **ClassProc hierarchy** - Object-oriented widget system with inheritance
2. **Event dispatch** - Two code spaces: events `0x01Cm00nn` (firmware `EV_*` names) and methods `0x01Em00nn` (firmware `MT_*` names), m = module
3. **Drawing primitives** - Line, box, frame, bitmap, string rendering to VRAM
4. **Page/Window navigation** - Screen, window, and page management
5. **Resource properties** - Type-safe property system with introspection

## Internal Module Names (Developer Code Names)

The firmware contains 11 UI subsystem modules with internal code names (likely named after
original Technics/Matsushita developers). They are initialised during boot from
`InitializeObjectTable` (0xFA40B3), which calls them in the order below and then twenty
generic `InitializeUser12`–`InitializeUser31` slots and `InitializeRoot`.

Addresses are v10, from `symbols/maincpu_v10_symbols_reference.txt`; the source file is the one
that carries the routine's ROM address range, which is why several sit outside `ui/`.

| Module    | Init Routine      | Address (v10) | Source file                       | Purpose (from the modes, titles and classes it registers)                                                                                                                                                                                                                           |
|-----------|-------------------|---------------|-----------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Murai** | `InitializeMurai` | 0xF7AD77      | `ui/drawbar_panel_ui.s`           | Sound mode (`MD_SOUND`): sound menu, part, master-tune, scale-type, mixer and `TT_SDTECD` titles; drawbar, accordion, welcome, message, software-version and feature-demo screens; 37 classes                                                                                       |
| **Toshi** | `InitializeToshi` | 0xFC311A      | `extensions/extension_init.s`     | Normal, control and one-touch-play modes (`MD_NORMAL`, `MD_CONTROL`, `MD_OTP`): normal screen, control menu (`TT_CT*`), MSA, Music Stylist (`TT_MUSICSTYL`, `TT_MS*`), panel memory (`TT_PM*`), `TT_SVARI` / `TT_RVARI`, test titles `TT_TEST1`–`TT_TEST6` and `TT_EXT`; 28 classes |
| **East**  | `InitializeEast`  | 0xF72BAC      | `sequencer/seq_event_playback.s`  | MIDI mode (`TT_MD*` titles), reverb and EQ presets, entertainer vocal and fade-in, split select; 16 classes (MIDI, in/out, control-message and vocal grids)                                                                                                                         |
| **Suna**  | `InitializeSuna`  | 0xF19636      | `storage/flash_floppy_handlers.s` | Composer (`MD_CMP`), MSP (`MD_MSP`, `MD_MSP_REC`) and sound-arranger (`MD_SND_ARG`) modes, Style Converter titles (`TT_STYLCNV*`); 41 classes                                                                                                                                       |
| **Cheap** | `InitializeCheap` | 0xF9426A      | `file_io/medley.s`                | Disk mode (`MD_DISK`): load, save, utility, format and medley titles (`TT_DK*`); file-name boxes, screen title, wait and one-shot timers; 13 classes                                                                                                                                |
| **Scoop** | `InitializeScoop` | 0xF028E3      | `display/scoop_display.s`         | Sound Editor mode and its 32 titles (`TT_SEMENU`, `TT_SE*`; [Sound Editor Screens]({{ site.baseurl }}/sound-editor-screens/)); no classes                                                                                                                                           |
| **Yoko**  | `InitializeYoko`  | 0xF29E6D      | `sequencer/sequencer_ui.s`        | Demo mode and the sequencer step mode: disk direct play (`TT_DP*`) and medleys, track select, step, track assign, song select and song name, demo menus; 22 classes                                                                                                                 |
| **Kubo**  | `InitializeKubo`  | 0xF2D2C4      | `sequencer/sequencer_ui.s`        | Entertainer, sequencer (play, easy record, real-time record, edit) and help modes; reverb, DSP-effect, equalizer and `TT_SDACCILL` titles; 26 classes                                                                                                                               |
| **Hama**  | `InitializeHama`  | 0xF1E146      | `factory_test/test_init.s`        | Factory floppy test (title 0xFC); title 0x7F, `TT_HDDEXT`, on the same `TestTitleFunc` until the HD-AE5000 re-registers it as its hard-disk title; 1 class, `HamaList`; Function table 0x109, the file, disk and system calls the HD-AE5000 uses                                    |
| **KSS**   | `InitializeKSS`   | 0xFC3E4F      | `kn5000_v10_program.s`            | None: the routine is a bare `ret` in v7, v9 and v10, so it registers nothing                                                                                                                                                                                                        |
| **Naka**  | `InitializeNaka`  | 0xF165EB      | `storage/flash_floppy_handlers.s` | UI widget descriptor tables (Viewable table 0xFD, 478 entries) and the `TT_FDMSP` title                                                                                                                                                                                             |

Three of the code names also name directories in the disassembly: `ui_widgets/` is NAKA,
`extensions/` is TOSHI, `factory_test/` is HAMA. The directory names do not fix the modules'
scope; like the other files, they follow ROM address ranges. The purposes in the table are read
from the modes, titles and classes each module registers (the `RegMode` / `RegTitle` lines of
each `Initialize*` routine; `python3 scripts/analysis/nakarest_objtab_map.py v10 --classes`
lists every class by table), not from an independent source. KSS registers nothing.

Each module registers "object tables" that define UI component hierarchies using the `RegObjTable` / `RegObjTabl` macros.

### Module numbers and the object table

Every module registers its tables in one object table in RAM at `0x027ED2`.
`RegisterObjectTable` copies a 14-byte record `{class id, proc, count, data}`
to `0x027ED2 + 14 × index`. For most kinds of table the index is a **kind
number plus the module number**:

| Kind               | Index          | Class id     | Proc               | Holds                                      |
|--------------------|----------------|--------------|--------------------|--------------------------------------------|
| Class table        | 0x160 + module | `0x01600004` | `ClassProc`        | the module's class definitions (see below) |
| Function table     | 0x100 + module | `0x01600001` | `FunctionProc`     | code addresses; names at index + 0x300     |
| ApFunction table   | 0x120 + module | `0x01600002` | `ApFunctionProc`   | code addresses; names at index + 0x300     |
| MainFunction table | 0x140 + module | `0x01600003` | `MainFunctionProc` | code addresses; names at index + 0x300     |
| ResEvent table     | 0x1C0 + module | `0x0160000C` | `ResEventProc`     | event names                                |
| ResMethod table    | 0x1E0 + module | `0x0160000D` | `ResMethodProc`    | method names                               |

The Class-table registrations in v10 give the module numbers: Root 0
(`InitializeRoot`), Murai 1, Toshi 2, East 3, Suna 4, Cheap 5, Scoop 6, Yoko 7,
Kubo 8, Hama 9 and Naka 0x0B. **The HD-AE5000 expansion ROM registers as module
0x0A**, with the same class ids and procs, so its class table sits at 0x16A (see
[HDAE5000 Homebrew]({{ site.baseurl }}/hdae5000-homebrew/#complete-handler-table)).
Viewable tables (class id `0x01600010`, `ViewableProc`) and their name tables
(`0x0160000F`, `ResNameProc`, index + 0x300) are numbered per screen family
rather than per module. Examples are Naka's 0xFD, the HD-AE5000's 0x7F and
Hama's 0xFC. Three further tables belong to the root: 0x180 holds the modes,
0x260 the support classes (`SupportClassProc`, 0x37 entries) and
0x1A0 the titles (see [Event Codes — Mode and Title Requests]({{ site.baseurl }}/event-codes/#mode-and-title-requests-0x01c00014-0x01c00016)).

An **object id** is `index << 16 | entry`. `SendEvent` takes bits 16-27 of the
id as the table index, so `0x016A0005` is entry 5 of table 0x16A and
`0x007F01EE` is entry 0x1EE of Viewable table 0x7F. This is also why ids in the
firmware so often begin `0x0160`: `0x016000nn` is entry *nn* of the root's class
table, a class id. Several older pages called that value a "PPI port" or a "port
address".

## Widget Type System (ClassProc Hierarchy)

All UI widgets are implemented as "Proc" handlers — functions that receive events and respond based on their widget type. The framework uses a class hierarchy with inheritance.

### The class system describes itself

The NAKA object model is **self-describing**. Each module's Class table holds
24-byte class definitions. The fields of a class definition are named by the
root class that describes class definitions, `Class` (entry 4 of table 0x160):

| Offset | Field      | Size | Meaning                                                                 |
|--------|------------|------|-------------------------------------------------------------------------|
| +0     | `proc`     | 4    | the class procedure (e.g. `ViewableProc`, `EffectBoxProc`)              |
| +4     | `parent`   | 4    | class id of the parent class                                            |
| +8     | `allsize`  | 2    | size of an instance record, inherited fields included                   |
| +10    | `selfsize` | 2    | bytes this class adds to its parent's record                            |
| +12    | `name`     | 4    | → class name string                                                     |
| +16    | `propdata` | 4    | → one type letter per own field                                         |
| +20    | `propname` | 4    | → one name pointer per letter, then a pointer to `""`, then the strings |

**Class ids.** A class id is `0x016S_KKKK`, entry *KKKK* of the Class table at
index 0x16S. `ClassProc` computes it with `srl 16; and 0xFFF` and a ×24 index.
The C side calls the same record `naka_class_t` (members `proc`, `base_class`,
`record_size`, `props_size`, `name`, `sig`, `props`) in
`v10/maincpu/ui_widgets/naka_types.h`. The nakarest lane's typed copies use
`naka_classdef_t`. In the C sources a class id is written `NAKA_CLASS(<Class>)`, and the
generated header `naka_classes.h` defines one `NAKA_CLASS_<Class>` constant and one
`naka_cls_<Class>_t` struct per class (see
[Widget records in the C sources](#widget-records-in-the-c-sources)).

**Every widget record starts with its class id.** The 4-byte "header"
`TT 00 60 01` of older notes, read little-endian, is class id `0x016000TT`:
entry *TT* of the root's class table. The "type byte" is therefore a class
index: 0x2B `Label`, 0x2E `Line`, 0x31 `Box`, 0x34 `TtlScreen`, 0x35 `Window`,
0x1D `AcTitleMenu`, 0x66 `AcLanguageText`, 0x6C `VwUserBitmapByName`. Records
of classes defined by other modules carry 0x0161-0x0168 in the high half.

**Field names come from the firmware.** The fields of every record are the
concatenation of its class chain's own fields, and `propname` names each of
them. The root of all widgets is `Viewable` (allsize 22):

| Offset | Viewable field | What it holds (from the code)                                              |
|--------|----------------|----------------------------------------------------------------------------|
| +0     | `class`        | the record's class id                                                      |
| +4     | `super`        | element index of the **parent** in the same Viewable table (0xFFFF = none) |
| +6     | `sub`          | index of the **first child**                                               |
| +8     | `next`         | index of the **next sibling**                                              |
| +10    | `prev`         | index of the **previous sibling**                                          |
| +12    | `flag`         |                                                                            |
| +14    | `rect`         | the screen rectangle x1, y1, x2, y2 (4 × 16 bits), inside the parent's     |

The ext lane established the four links and the rectangle by checking them
against each other (`scripts/analysis/ext_lane_checks.py widgets` / `test1`).
The nakarest lane found the firmware's own names for them. Subclasses append
their fields. `Label` adds `str`, `font` and `fontcolor` (allsize 32).
`TtlScreen` adds `title` and `icon` to `Screen`'s `exit` and `window` (allsize
42). `AcTitleMenu` adds `str`, `title` and `icon` to `PsMenuBox`'s `font`,
`fontcolor`, `align`, `editsw` and `selected` (allsize 54).

**Type letters.** `propdata` has one letter per own field. The sizes were solved
so that the letters' sizes sum to `selfsize` for all 293 classes:

| Size    | Letters                                                                             |
|---------|-------------------------------------------------------------------------------------|
| 1 byte  | `C`                                                                                 |
| 2 bytes | `A` `B` `G` `[` `]` `^` `_` `d` `e` `f` `g` `h` `l` `u` `v` `w`                     |
| 4 bytes | `F` `I` `J` `K` `L` `M` `N` `X` `` ` `` `a` `b` `c` `i` `j` `k` `m` `n` `r` `s` `t` |
| 8 bytes | `P` (a rectangle)                                                                   |

The nakabig lane found one exception to its smaller letter table: `AcCmpRecBox`
with `"CC"`. The nakarest table resolves it with `C` = 1 byte.

**Measured invariants** (v10, v9 and v7 alike):

- 293 classes in the 11 Class tables the main CPU registers. By table: 0x160
  Root 109, 0x161 Murai 37, 0x162 Toshi 28, 0x163 East 16, 0x164 Suna 41, 0x165
  Cheap 13, 0x167 Yoko 22, 0x168 Kubo 26 and 0x169 Hama 1 (`HamaList`); Scoop's
  0x166 and Naka's 0x16B are registered empty.
- `allsize = parent.allsize + selfsize` for all 292 classes that have a parent.
  The root class `Object` (`0x01600000`) contributes no prefix.
- All 3,365 widget records in the 211 registered Viewable tables resolve to a
  class, and none lies closer to the next record than its `allsize`.
- nakabig's independent count (2026-09-25): 3,340 of the 3,367 Viewable-registered
  records matched a known class, and none overlapped the next record. Its extractor,
  `scripts/analysis/naka_class_descriptors.py`, matches only the numeric spelling
  `RegObjTable 0x1600004` and finds no tables in the current sources.

Reproduce with `python3 scripts/analysis/nakarest_objtab_map.py v10 --classes`,
which prints every class with its fields at their offsets, and with
`--check-classes`, which asserts the invariants. Both need a built
`rebuilt_ROMs/kn5000_v10_program.llvm.elf`.

The widget records in the NAKA C blobs are typed through this model. Since
2026-10-29 the struct for every class, `naka_cls_<Class>_t`, is generated once
into `naka_classes.h`, and 3,242 records in 18 C files are typed with it and
spelled with the firmware's names, in all five trees (v10, v9, v7, v6, v5). See
[Widget records in the C sources](#widget-records-in-the-c-sources).

The class-name lists below predate this model. They sort the procs by prefix
and are not the class tree.

### Base Classes

| Proc               | Description                  |
|--------------------|------------------------------|
| `DefaultClassProc` | Root of the class hierarchy  |
| `ClassProc`        | Base class handler           |
| `ObjectProc`       | Object-level handler         |
| `ViewableProc`     | Base for all visible widgets |
| `FunctionProc`     | Function dispatch handler    |
| `InheritedProc`    | Calls parent class handler   |

### Primitive Widgets

| Proc            | Description                                   |
|-----------------|-----------------------------------------------|
| `BoxProc`       | Basic rectangular container                   |
| `GroupBoxProc`  | Grouped container with title                  |
| `WindowProc`    | Top-level window                              |
| `ScreenProc`    | Full-screen display                           |
| `StringBoxProc` | Text display box                              |
| `TextBoxProc`   | Text content area                             |
| `LabelProc`     | Static text label                             |
| `BitmapProc`    | Image display                                 |
| `IconProc`      | Small icon display                            |
| `LineProc`      | Line element                                  |
| `FrameProc`     | Bordered frame                                |
| `EditSwProc`    | Label that handles `EVT_SW_IN` (not a toggle) |

### View Widgets (Vw* prefix)

View widgets are interactive display containers:

| Proc                     | Description               |
|--------------------------|---------------------------|
| `VwBoxProc`              | Interactive box container |
| `VwMenuBoxProc`          | Menu container            |
| `VwEditSwBoxProc`        | Edit switch box           |
| `VwUserBitmapProc`       | User bitmap display       |
| `VwUserBitmapByNameProc` | Bitmap by name lookup     |
| `VwScreenTitleProc`      | Screen title bar          |

### Page/Settings Widgets (Ps* prefix)

Settings-page widgets for parameter display:

| Proc                 | Description          |
|----------------------|----------------------|
| `PsParaBoxProc`      | Parameter box        |
| `PsPageBoxProc`      | Page container       |
| `PsMenuBoxProc`      | Settings menu        |
| `PsEditSwBoxProc`    | Settings edit switch |
| `PsToggleBoxProc`    | Toggle button        |
| `PsListBoxProc`      | Scrollable list      |
| `PsGridBoxProc`      | Grid/table layout    |
| `PsEditBoxProc`      | Text edit field      |
| `PsNumEditBoxProc`   | Numeric editor       |
| `PsTblEditBoxProc`   | Table editor         |
| `PsRadioBoxProc`     | Radio button group   |
| `PsMixerControlProc` | Mixer fader control  |

### Action/Control Widgets (Ac* prefix)

Interactive control widgets that respond to user input:

| Proc                        | Description                 |
|-----------------------------|-----------------------------|
| `AcOnOffBoxProc`            | On/off toggle               |
| `AcIndexToggleProc`         | Index selector toggle       |
| `AcFuncToggleProc`          | Function toggle             |
| `AcNumEditBoxProc`          | Numeric edit control        |
| `AcBitEditBoxProc`          | Bit-level edit              |
| `AcStrRadioBoxProc`         | String-based radio buttons  |
| `AcTempoBoxProc`            | Tempo display/edit          |
| `AcGridBoxProc`             | Interactive grid            |
| `AcListBoxProc`             | Interactive list            |
| `AcDrawbarNameProc`         | Drawbar organ label         |
| `AcAccordionTabProc`        | Accordion tab control       |
| `AcMixerVolProc`            | Mixer volume fader          |
| `AcPartMixerProc`           | Part mixer control          |
| `AcTrackMixerProc`          | Track mixer control         |
| `AcPresentationBoxProc`     | SSF presentation display    |
| `AcPresentationControlProc` | SSF presentation controller |
| `AcNamingWindowProc`        | File/item naming dialog     |

### Specialized Grid Widgets

Many domain-specific grid configurations exist:

| Proc                       | Domain                    |
|----------------------------|---------------------------|
| `AcEasyCmpGridBoxProc`     | Easy Composer settings    |
| `AcCmpSetGridBoxProc`      | Composer set grid         |
| `AcSndArgGridBoxProc`      | Sound argument grid       |
| `AcCtlMsgGridBoxProc`      | Control message grid      |
| `AcFadeSetGridBoxProc`     | Fade settings grid        |
| `AcInOutGridBoxProc`       | Input/output routing grid |
| `AcMidiPartGridBoxProc`    | MIDI part assignment grid |
| `AcParaLoadOptGridBoxProc` | Parameter load options    |

### Screen Types

| Proc                 | Description                                |
|----------------------|--------------------------------------------|
| `IvScreenProc`       | Interactive screen                         |
| `TtlScreenProc`      | Title screen                               |
| `NormScreenProc`     | Normal operating screen                    |
| `MsaModeScreenProc`  | MSA mode screen                            |
| `VariScreenProc`     | Variation screen                           |
| `RVariScreenProc`    | Rhythm variation screen (title `TT_RVARI`) |
| `PmBankScreenProc`   | Panel memory bank screen                   |
| `SineWaveScreenProc` | Sine wave test screen                      |
| `AcFdemoScreenProc`  | Feature demo screen                        |
| `AcWelcomScreenProc` | Welcome/startup screen                     |

### Interactive View Widgets (Iv* prefix)

Controller widgets for page navigation and lifecycle:

| Proc                      | Description               |
|---------------------------|---------------------------|
| `IvPageControlProc`       | Page control handler      |
| `IvWindowPageControlProc` | Window-based page control |
| `IvPmemWindowPageCtlProc` | Panel memory page control |
| `IvExitProc`              | Exit handler              |
| `IvExitWindowProc`        | Window exit handler       |
| `IvWaitWinCtlProc`        | Wait dialog control       |
| `IvNamingProc`            | Naming dialog controller  |
| `IvShowHideProc`          | Visibility toggle         |
| `IvCatchEventProc`        | Event capture handler     |
| `IvDrawbarProc`           | Drawbar organ display     |
| `IvAccordionProc`         | Accordion display         |

### Property Type System

The framework includes a complete type system for widget properties with introspection:

**Primitive types:** `swordProc`, `uwordProc`, `scharProc`, `ucharProc`, `slongProc`, `ulongProc`, `boolProc`

**Pointer types:** `pSwordProc`, `pUwordProc`, `pScharProc`, `pUcharProc`, `pSlongProc`, `pUlongProc`, `pBoolProc`, `pFuncProc`, `pProcProc`, `pStringProc`

**Geometry types:** `RECTWProc`, `POINTWProc`, `PointXProc`, `PointYProc`, `RectX1Proc`, `RectY1Proc`, `RectX2Proc`, `RectY2Proc`

**ID types:** `ColorIDProc`, `BorderIDProc`, `AlignmentIDProc`, `LineModeIDProc`, `FontIDProc`, `IconIDProc`, `BitmapIDProc`, `UserIDProc`, `PartIDProc`, `TrackIDProc`, `EventIDProc`

**Resource types:** `ResourceProc`, `ResEventProc`, `ResMethodProc`, `ResNameProc`, `ResBitmapProc`, `ResFrameProc`, `ResIconProc`, `ResFontProc`, `ResStringProc`

#### Where a widget's live values are kept (2026-10-06)

Widget records are in ROM, so a widget cannot write its own state into the record. Instead, every mutable property
holds the RAM address of a cell of its own. For example, `selected`, `onoff`, `page`, `selrow`/`selcol`, `window`,
`parent`, `child`, `nowstyle`, `nowsong` and an edit box's `data` (its value) all work this way. Over all the
in-ROM widgets of v10 there are 1,367 such fields and 1,367 distinct cells; no two widgets share one. The cells
lie in the work-RAM image that `Boot_InitWorkRAM` copies from ROM `0xEED8C8` to RAM `0x3D524` at boot. The part from
RAM `0x3DCD4` on is the C file `naka_sequencer_channels.c` in technics-roms-disasm, so the image is also where each
cell's initial value is set. The C source names each cell after its widget and field: `TrAsGrid_SelCol`,
`SdpartMain_AcLswPartEditBox_2_Value` (the REV. DEPTH box's value cell), `STYLE2_AcMstStyle2GridBox_Nowstyle`
(`scripts/converters/name_widget_value_cells.py`).

Since 2026-10-29 a widget record names its cell, not its address: `.window = RAM_DiskMenu_Window`. The generated
header `naka_ram_cells.h` defines every `RAM_<cell>` (v10 layout). It also names the cells outside the C-spelled part
of the image, after the widget field that keeps its live value there (`<record>_<Field>`, read from the ROM records),
and the 18 `field_XXXX` members of `naka_sequencer_channels.c` that are such cells now carry the cell's name. No
widget field in the C sources is spelled as a raw RAM address any more (1,541 before, 0 now, per tree).

#### The property-type protocol (2026-10-06)

A property type is a procedure called with the event in XBC. It converts one property value between its stored form and its text form, for the dump and edit machinery. The ID types answer a common set of events, and `CommonIDProc` handles whatever a type leaves out:

| Event                                                 | What the type does                                                                                |
|:------------------------------------------------------|:--------------------------------------------------------------------------------------------------|
| `EVT_SET_PROPERTY_EX`                                 | parse the text, store the value (via `IDCursorAdvance`)                                           |
| `EVT_GET_PROPERTY_EX` / `EVT_DUMP_PROPERTY_EX`        | read the value at the cursor and write its text                                                   |
| `EVT_MAKE_DUMP`                                       | build the dump name: a prefix (`"id"`, `"idICON_"`, `"idf"`, `"idc"`) + the value's name          |
| `EVT_GET_PROP_DATA_COUNT_SP` / `EVT_GET_PROP_DATA_SP` | the number of choices, and choice *n*'s text                                                      |
| `EVT_GET_PROP_MEMBER` / `EVT_CHECK_PROP_STRING`       | the geometry types: the member name (`"x"`, `"y"`, `"height"`) and a check or rewrite of the text |

Three storage shapes recur, and the labels inside each routine are named after these roles (`<Type>_OnSetPropertyEx`, `<Type>_SetProp_CompareName`, `<Type>_ForwardToCommon` ...):

* **Plain value** (`ColorIDProc`, `BorderIDProc`, `AlignmentIDProc`, `EditSwStyleIDProc`, `EditSwIDProc`, `LineModeIDProc`, `FrameIDProc`, `UserIDProc`, `PartIDProc`, `TrackIDProc`, `IntTimeIDProc`, `ViewFlagProc`): GET/DUMP store the id, SET parses through `CommonIDProc`, and everything else is forwarded to it.
* **Index into a name table** (`FontIDProc` uses the RAM table at `0x3EFAC`; `IconIDProc` uses `IconIDProc_NameTable`; `BitmapIDProc` uses `BitmapIDProc_PtrTable`, which has 34 entries): SET searches the table with `Strcmp`, GET/DUMP copy `table[id]`, and the choice count is `<Type>_EntryCount`.
* **Object id** (`ApFuncIDProc`, `MainFuncIDProc`, `ClassIDProc`): first build a list of every object id in registry slots `0x120-0x13F`, `0x140-0x15F` or `0x160-0x17F` with `CountObject`, then search it by `EVT_GET_NAME`.

`RectY2Proc` stores a rectangle's y2 but edits it as `"height"`: SET stores y1 + height - 1.

The property types themselves are the table `SupportClass_PropTypeRecords` (0xEB7690), which `InitializeObjectTable` registers at registry slot 0x260 with 0x37 entries, one per letter `A`..`w`. `ClassProc` selects entry *letter* - 'A' (`sub a, 0x41; add xwa, 0x2600000`). Each entry is {`proc`, `count`, `size`, `values`}: the property-type procedure, the number of named values that `CommonIDProc` walks, the property's size in bytes (`SupportClassProc_OnGetPropSize` reads it at +6), and a pointer to the {name, value} pairs. Those pairs are where the C sources' value names (`CL_White`, `BD_Single2`, `VF_Fixed`, ...) come from. In the C the entries for letters `A`..`s` are a typed array, `naka_prop_type_t SupportClass_PropTypeRecords[51]` in `naka_style_bitmaps.c` (`scripts/converters/retype_prop_type_records.py`).

The names come from `scripts/renaming/gen_idproc_names.py`, `gen_name_table_idproc_names.py`, `gen_objlist_idproc_names.py` and `gen_point_class_idproc_names.py` in technics-roms-disasm. Each asserts the shape it relies on in v10, v9 and v7. The labels these routines had before (`FrameVariant_*`, `DrawHelper_*`, `SliderH_*`, `ShadowBox_*`, `EdgeVariant_*`) were borrowed from unrelated code.

## How Widgets Paint Themselves

Painting is three events, answered by `ViewableProc` (0xFA5995, the base of every view; `ui/ui_widget_defs.s`)
unless a class overrides them:

| Event                     | Viewable's answer                                                                                                                                   |
|---------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| `EVT_PAINT` (0x1C0000B)   | if visible: `EVT_DRAW` to self and `EVT_PAINT` to the first subview; then, visible or not, `EVT_PAINT` to the next sibling (`ViewableProc_OnPaint`) |
| `EVT_REPAINT` (0x1C0000C) | if visible: `EVT_DRAW` to self and `EVT_PAINT` to the subview, no siblings (`ViewableProc_OnRepaint`)                                               |
| `EVT_DRAW` (0x1C0000D)    | nothing (`Viewable_ReturnZero`); each visible class draws its own rectangle here                                                                    |

So painting a screen is a depth-first walk of its view tree (self, children, then siblings), and a hidden view
(`GetVisible`: flag word +12 bit 0 set) hides its subtree; `EVT_REPAINT` redraws one widget and its children after a
value change. The tree links are the record's +4 super, +6 sub, +8 next and +10 prev words (`GetSuperView`,
`GetSubView`, `GetNextView`, `GetPrevView`; ViewableProc's `EVT_GET_SUPERVIEW` / `EVT_GET_SUBVIEW` / `EVT_GET_NEXTVIEW` /
`EVT_GET_PREVVIEW` cases are `Viewable_OnGetSuperView` and its siblings). These helpers were mislabelled before
2026-10-31: the one that reads +6, the subview, was called View_GetSuperViewInstance.

The `Ps*` value widgets draw in two steps: `EVT_DRAW` paints the box and the marker beside the panel switch that
operates them (`DrawEditSw`), and `EVT_PARA_DRAW` (0x1C0000F) paints the value text, so a value change redraws
only the text. Grids add `EVT_SELE_DRAW` for the cursor, and `VwBox` answers `EVT_DRAW_SELECTED`.

What each class's `EVT_DRAW` calls, read from the source of each proc ("base" = the parent class's proc, called
first; `notes/open4-kn5000-b/display/probes/widget_paint_calls.py` in the disassembly repository lists the
candidate primitives of every proc):

| class (proc)                                       | base       | draws                                                                                                                                                                                                                                                                                                                                                                                |
|----------------------------------------------------|------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Viewable (`ViewableProc`)                          | -          | nothing                                                                                                                                                                                                                                                                                                                                                                              |
| Box (`BoxProc`, 0xF99581)                          | Viewable   | `DrawDesignBox` of the rectangle                                                                                                                                                                                                                                                                                                                                                     |
| VwBox (`VwBoxProc`)                                | Viewable   | `DrawDesignBox(rect, border +24, colour +22)`; `EVT_DRAW_SELECTED` (`VwBox_OnDrawSelected`): `DrawDesignFrame` 2 px inside the client box, colour 0xF2 to select, the box colour to deselect                                                                                                                                                                                         |
| GroupBox (`GroupBoxProc`)                          | Box        | the box; its last switch case, `GroupBoxProc_OnAllPaint`, re-sends `EVT_PAINT` to the view (the whole group repainted); the rest of GroupBoxProc handles switches, the dial and title events                                                                                                                                                                                         |
| Screen (`ScreenProc`, 0xF9A69F)                    | GroupBox   | `Screen_Paint`: `DrawWall` (the 320 x 240 wallpaper) only; the wall and its palette are chosen on `EVT_SHOW` (`Screen_Init_SetWall`: `ChangeWall`, `ChangeWallPalette`)                                                                                                                                                                                                              |
| TtlScreen (`TtlScreenProc`, 0xF9AA6D)              | Screen     | `DrawTitleBar`: icon (`DrawDesignBox` + `DrawIcons`) and title text (`DrawStringCentered` / `DrawStringLeftJustify` / `DrawStringRightJustify`)                                                                                                                                                                                                                                      |
| Label (`LabelProc`, 0xF9C4B6)                      | Viewable   | `DrawString` at (x1 + 2, y1 + 1), font +26, colour +30 on 0xF7                                                                                                                                                                                                                                                                                                                       |
| StringBox (`StringBoxProc`, 0xF9C44E)              | Box        | the box, then `DrawStringAlignment` of the string, centred in the client box (`GetClientBox`, `GetBoxCenter`)                                                                                                                                                                                                                                                                        |
| Line (`LineProc`, 0xF9C723)                        | Viewable   | `DrawLine` (horizontal or vertical by field +24)                                                                                                                                                                                                                                                                                                                                     |
| Frame (`FrameProc`, 0xF9C7A5)                      | Viewable   | `DrawDesignFrame`: `DrawFrame` repeated, shrinking one pixel per pass, for the frame thickness (style 1 only)                                                                                                                                                                                                                                                                        |
| Bitmap (`BitmapProc`)                              | Viewable   | `DrawBitmap` of bitmap id +22 at (x1, y1)                                                                                                                                                                                                                                                                                                                                            |
| VwUserBitmap (`VwUserBitmapProc`)                  | Viewable   | asks the application function for data / width / height (`EVT_GET_BITMAP_*`) and draws with `DrawBitmapSPFast` (fallback `DrawBitmap`)                                                                                                                                                                                                                                               |
| Icon (`IconProc`)                                  | Viewable   | `DrawDesignBox` (a 28 x 28 frame, style 0xC4, colour 0xF0) and `DrawIcons`                                                                                                                                                                                                                                                                                                           |
| EditSw (`EditSwProc`, 0xF9C8BE)                    | Label      | the label's text; it handles only `EVT_SW_IN` itself                                                                                                                                                                                                                                                                                                                                 |
| PsMenuBox (`PsMenuBoxProc`)                        | VwBox      | EVT_DRAW: the box, then `DrawEditSw` (the one-character marker beside the operating switch); `EVT_PARA_DRAW`: the text from `EVT_GET_STRING` with `DrawStringAlignment`                                                                                                                                                                                                              |
| PsEditBox (`PsEditBoxProc`)                        | VwBox      | as PsMenuBox, with `DrawStringReverse` for the highlighted value                                                                                                                                                                                                                                                                                                                     |
| PsEditSwBox (`PsEditSwBoxProc`)                    | VwBox      | the box, `DrawEditSw`, `DrawBox` and the button-state painter `ButtonState_PaintProc`                                                                                                                                                                                                                                                                                                |
| AcTitleMenu (`AcTitleMenuProc`)                    | PsMenuBox  | menu text (`DrawString`, width by `CalcTotalWidth` / `GetCharHeight`) and the entry's icon (`DrawDesignBox` + `DrawIcons`)                                                                                                                                                                                                                                                           |
| PsGridBox (`PsGridBoxProc`) and every `Ac*GridBox` | VwBox      | EVT_DRAW (`PsGridBox_OnDraw`): the box, then `EVT_PARA_DRAW` to itself (`PsGridBox_OnParaDraw`: cell dividers with `DrawLine`, cell text with `DrawStringAlignment`, the derived class supplying text through `EVT_REQUEST_GRID_DRAW` / `EVT_GET_FIXED_ROW_STR` / `EVT_GET_FIXED_COL_STR`), then `EVT_SELE_DRAW` (`PsGridBox_OnSeleDraw`: `DrawDesignFrame` round the selected cell) |
| PsMixerControl (`PsMixerControlProc`)              | its parent | the parent's box, then `EVT_REFRESH_PARA_DRAW`: for each control record the per-type painter `PsMixer_CtlTypeProc0..10` (`PsMixer_ControlProcTable`), built from `DrawEditSw`, `PsMixer_DrawFrameBox` / `PsMixer_DrawFrameBoxWithDividers` / `PsMixer_DrawCaptionFrame`, `DrawStringCentered`, `DrawLine`                                                                            |
| AcMixerVol (`AcMixerVolProc`)                      | VwBox      | `DrawBox`, `DrawBitmapFast`, `DrawStringCentered` / `DrawStringReverse` (`[INFERENCE]` the mixer fader: a bar, the knob bitmap, the value)                                                                                                                                                                                                                                           |
| AcLswPartPan (`AcLswPartPanProc`)                  | its parent | the pan meter: `DrawBox`, `DrawLine`, `DrawDesignBox`                                                                                                                                                                                                                                                                                                                                |
| IvDrawbar (`IvDrawbarProc`, 0xF824C4)              | its parent | nothing of its own: `IvDrawbar_OnDraw` calls the parent and sends `EVT_PARA_DRAW`; the `Iv*` classes are invisible controllers that send refresh events to the drawbar widgets                                                                                                                                                                                                       |

No class draws a keyboard picture or a waveform; the level and pan meters are the mixer classes above. The other
derived classes mostly call their parent (`InheritedProc`) and add one of these primitives.

All drawing goes to the off-screen buffer; `UpdateScreen` copies the changed rectangle to VRAM (see
[Display Subsystem]({{ site.baseurl }}/display-subsystem/#rendering-pipeline)).

## Widget records in the C sources

Since 2026-10-29 the widget records in the NAKA C sources (`v10/maincpu/ui_widgets/*.c`, and the same files in v9,
v7, v6 and v5; v8 builds from v9's sources) are written with the firmware's own names, so a screen can be read from
its source. Each tree compiles those files with clang into `includes/generated/*.bin` and includes the bins with
`.incbin`; every step is byte-identical, and `make gui-check` is part of `make gate`. Here is the DISK MENU screen,
from `naka_disk_menu_file_io.c`, cut short:

```c
    /* ==== SCREEN TITLE_DKMENU "DISK MENU" -- "TT_DKMENU", title id 0x60, function NAKA_APFUNC_DefaultFunction ====
     * Path: mode MD_DISK
     * Menu: "STYLE CONVERT" -> TITLE_STYLCNVWAIT
     * Menu: "HARD DISK MAIN MENU" -> TITLE_HDDEXT
     * Menu: "LOAD" -> by code, NAKA_MAINFUNC_LoadTtlJgFunc
     * EXIT -> TITLE_PS */
    .DiskMenu = {
        .class_ = NAKA_CLASS(TtlScreen),
        .super = NAKA_NONE,
        .sub = OBJ_StyleConvert_AcTitleMenu,
        .flag = VF_Fixed | VF_Const,
        .rect = NAKA_XYWH(0, 0, 320, 240),
        .color = CL_Gray,
        .border = BD_Single2,
        .exit = TITLE_PS,
        .window = RAM_DiskMenu_Window,
        .title = SELF(DiskMenu_text),
        .icon = idICON_i147,
    },
    .DiskMenu_text = "DISK MENU",
    .StyleConvert_AcTitleMenu = {
        .class_ = NAKA_CLASS(AcTitleMenu),
        .super = OBJ_DiskMenu,
        .next = OBJ_Cheap_HardDiskMenuView,
        .rect = NAKA_XYWH(8, 114, 149, 26),
        .font = idCHARA1, .fontcolor = CL_White, .align = AL_Center,
        .editsw = ES_Left3,
        .selected = RAM_StyleConvert_AcTitleMenu_Selected,
        .str = SELF(StyleConvert_text),
        .title = TITLE_STYLCNVWAIT,
    },
```

Each file also declares its object tree once, before the initializer: one enum per Viewable table, with one `OBJ_*`
constant per element in index order, indented by depth in the tree:

```c
#define Toshi_Viewable_NORMAL_SLOT 0x001u
enum Toshi_Viewable_NORMAL_objects {
    OBJ_Normal,                          /*  0 TtlScreen "Normal" */
    OBJ_normal,                          /*  1 NormScreen "normal" */
      OBJ_normal_AcTempoBox,             /*  2 AcTempoBox */
      ...
      OBJ_normal_AcSoundName_2,          /*  6 AcSoundName */
        OBJ_RIGHT2_StringBox,            /*  7 StringBox */
```

### How each field is spelled, and the evidence for the name

| what                  | spelled as                                                                                                             | evidence (v10)                                                                                                                                                                                                 |
|-----------------------|------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| class id              | `NAKA_CLASS(TtlScreen)`; `naka_cls_<Class>_t`                                                                          | `ClassProc` maps id 0x016S_KKKK to entry KKKK of the Class table at slot 0x16S; all 293 classes come from the 9 populated Class tables                                                                         |
| field names           | the class chain's `propname` strings                                                                                   | the same Class tables                                                                                                                                                                                          |
| object links          | `.super = OBJ_normal`; an enum per table, indented by depth                                                            | Viewable +4/+6/+8/+10 are element indices of the same table; `naka_gui_model.py --check` asserts each constant's index, that the indentation is the depth `super` gives, and that sub/next/prev agree          |
| rectangle             | `NAKA_XYWH(x, y, w, h)`                                                                                                | `RectX2Proc` and `RectY2Proc` edit x2 and y2 as "width" and "height": GET answers x2 - x1 + 1, SET stores x1 + width - 1                                                                                       |
| enumerated properties | `CL_White`, `BD_None`, `VF_Fixed \| VF_Const`, `AL_Center`, `ES_Left3`, `SS_*`, `LM_*`, `FR_*`, `PT_*`, `TR_*`, `IT_*` | the {name, value} pairs of `SupportClass_PropTypeRecords`, selected by the field's propdata letter (see [the property-type protocol](#the-property-type-protocol-2026-10-06))                                  |
| fonts                 | `idCHARA1` .. `idCHARA5W`                                                                                              | `FontIDProc` reads RAM 0x3EFAC, whose work-RAM image is `FontIDProc_FontNameTable`; the dump prefix is `FontIDProc_DumpPrefix` = "id"                                                                          |
| bitmaps               | `idTrashIcon` ...                                                                                                      | `BitmapIDProc` reads `BitmapIDProc_PtrTable` (34 entries); prefix "id"                                                                                                                                         |
| icons                 | `idICON_None`, `idICON_Default`, `idICON_i0` ...                                                                       | `IconIDProc` reads `IconIDProc_NameTable` (177 names); prefix "idICON_". The firmware names most icons only `iNN`                                                                                              |
| title ids             | `TITLE_*`                                                                                                              | letter `a` is `TitleIDProc`; `RegTitle` / `RegisterTitle` bind each title to its view object; names from `shared/event_codes.s`                                                                                |
| mode / function ids   | `NAKA_MODE_*`, `NAKA_APFUNC_*`, `NAKA_FUNC_*`, `NAKA_MAINFUNC_*`                                                       | letters `` ` `` `j` `k` (`ModeIDProc`, `ApFuncIDProc`, `MainFuncIDProc`); names from `shared/event_codes.s`                                                                                                    |
| view object ids       | `NAKA_VIEW_ID(Table, OBJ_x)`                                                                                           | letters `t` and `N` (`WindowIDProc`, `ScreenIDProc`); the id is 0x0SSS_KKKK, and all 113 ids point into a table of the same file                                                                               |
| live-value cells      | `RAM_<cell>`                                                                                                           | letters `m`..`s` (`pBoolProc` .. `pUlongProc`) hold the address of a DRAM cell in the `Boot_InitWorkRAM` image (see [Where a widget's live values are kept](#where-a-widgets-live-values-are-kept-2026-10-06)) |
| screen headers        | `/* ==== SCREEN TITLE_X "TEXT" ...` / `/* ==== VIEW ...`                                                               | generated: the title's text, its menu path, its menu entries and where EXIT goes (the screen's `exit` field)                                                                                                   |

Records registered at DRAM addresses are read through the two `Boot_InitWorkRAM` images (ROM 0xEED8C8 to RAM 0x3D524,
and ROM 0xEEFA66 to RAM 0xE35E). 28 records are of that kind, among them the DISK MENU's "HARD DISK MAIN MENU"
entry, `Cheap_HardDiskMenuView`.

### Titles and modes opened by code

Three routines in `ui/ui_control_panel.s` post a title or mode change from an index:

| routine                    | posts                                     | old name (before 2026-10-29) |
|----------------------------|-------------------------------------------|------------------------------|
| `UI_ChangeTitleByIndex`    | `EVT_CHANGE_TITLE`, `TITLE_PS + A`        | `UI_PostModeChangeEvent`     |
| `UI_InterruptTitleByIndex` | `EVT_INTERRUPT_TITLE`, `TITLE_PS + A`     | `SoundCtrl_SendCommand`      |
| `UI_ChangeModeByIndex`     | `EVT_CHANGE_MODE`, `NAKA_MODE_MD_PS + A`  | `UI_PostPartChangeEvent`     |

Each `shared/event_codes.s` ends with a generated block of `TT_X` / `MD_X` index constants, the firmware's own names
(`scripts/generators/gen_title_mode_index_equs.py`). `scripts/converters/name_title_index_operands.py` walks each
file's control flow back from every call, including the two stack-spilling forwarders `FileIO_DiskEventDispatch` and
`FileIO_GetDiskCapacity`, and names the operand: `ldw wa, TT_DKLD`. That names 279 title and 30 mode operands per
tree; 18 title sites and 1 mode site take the index from memory.

Panel buttons enter modes through `PanelButton_ModeKey` (`audio/audio_control_engine.s`), which maps a mode key's
lowest set button bit through the `PanelButton_ModeKeyCodes*` maps (`naka_extension_device.c`, one `MD_*` byte per
button, commented with the MAME driver's port names) and posts `EVT_SW_IN_MODE`. The screen headers and the
[KN5000 Menu Map]({{ site.baseurl }}/kn5000-menu-map/) start each path at its button:
`MENU DISK button (mode MD_DISK) > "LOAD" (by LoadTtlJgFunc)`.

### Records outside the C

Records that live in the assembly are written as one keyword-argument macro call each, `NAKA_REC_<Class>`, defined
in the generated `shared/naka_gui.s` (class ids, value names, `IDX_<label>` element indices and one macro per class;
`scripts/converters/naka_asm_records.py`). 86 asm records are spelled this way in v10 (88 in v6 and v5). The class-name
and propdata strings carry labels, `ClassName_<Class>` and `ClassPropdata_<Class>`, and 283 pointers to them per tree
(281 in v6/v5) are spelled `NAKA_ADDR()` (`scripts/converters/name_class_string_pointers.py`).

### Headers, tools and checks

| file                                         | role                                                                                         |
|----------------------------------------------|----------------------------------------------------------------------------------------------|
| `<tree>/maincpu/ui_widgets/naka_classes.h`   | generated: `NAKA_CLASS_*` constants, one typedef per class, the property value names         |
| `<tree>/maincpu/ui_widgets/naka_ids.h`       | generated: every `shared/event_codes.s` constant as a `#define`                              |
| `<tree>/maincpu/ui_widgets/naka_ram_cells.h` | generated: `RAM_<cell>` addresses (v10 layout)                                               |
| `<tree>/maincpu/ui_widgets/naka_types.h`     | includes the three, plus `NAKA_XYWH`, `NAKA_XYXY` and `NAKA_VIEW_ID`                         |
| `scripts/generators/gen_naka_gui_headers.py` | writes the headers into all five trees (`--check`)                                           |
| `scripts/converters/naka_gui_symbolize.py`   | the rewrite; recompiles each changed file and refuses any whose bin would change             |
| `scripts/analysis/naka_gui_model.py`         | the parser and GUI graph (titles, modes, edges); `--check` tests the enums against the links |
| `scripts/generators/gen_naka_menu_map.py`    | writes `docs/gui/kn5000-menu-map.md` (`--check`)                                             |
| `scripts/analysis/naka_gui_census.py`        | the readability census (`--rev` for before/after, `--files TREE` per file)                   |
| `scripts/converters/naka_asm_records.py`     | `shared/naka_gui.s` and the `NAKA_REC_` macro records                                        |

The headers are generated from v10 and copied unchanged into v9, v7, v6 and v5. `make menu-map` regenerates the menu
map, `make gui-census` prints the census, and `make gui-check` checks the headers, the enums against the links, the
spelling and SCREEN headers of all five trees, and the menu map.

The census counts, outside comments and strings, what is still spelled as a number (v10;
`python3 scripts/analysis/naka_gui_census.py`, "before" with `--rev 9dbc03088`):

| measure                                  | before | now   |
|------------------------------------------|--------|-------|
| class ids as numbers                     | 3,445  | 0     |
| object links as numbers                  | 7,940  | 0     |
| view ids as numbers                      | 113    | 0     |
| property values with a name, as numbers  | 15,460 | 0     |
| property values with no name             | 1      | 1     |
| ROM addresses as numbers                 | 384    | 73    |
| RAM cells as numbers                     | 1,541  | 0     |
| `field_XX` members                       | 645    | 525   |
| records                                  | 3,206  | 3,242 |

What remains: 65 Viewable elements have no typed record (20 straddle two C members, 13 are DRAM records in the asm's
`WorkRamInit_Image`, 32 asm records sit in blocks the macro rewrite skips); 73 ROM addresses point into string or
record interiors that have no label yet; 525 `field_XX` members (291 of them in `naka_sequencer_channels.c`) need the
routines that reach them through a base pointer; one property value, `TEST3.fontcolor = 0x0043`, has no name. The
lane's notes are
[`notes/data-semantics-2026-10-29/gui-kn5000/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/notes/data-semantics-2026-10-29/gui-kn5000/README.md).

The whole GUI, every title with its menu path, menu entries, EXIT target and widget tree, is the generated
[`docs/gui/kn5000-menu-map.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/docs/gui/kn5000-menu-map.md); the [KN5000 Menu Map]({{ site.baseurl }}/kn5000-menu-map/)
page summarises it.

Since 2026-11-06 the records the first typing had cut across (an IvExit read together with the record after it)
are typed too (`scripts/converters/naka_type_straddling_records.py`), so a record's 32-bit words are never read
as pointers when they are rectangle words. The sound editor's pages (TITLE_SE*) are DirmdEmulator screens: their
menu paths come from each page's method table and switch handlers, and the docs/gui menu map now gives 158 of the
211 titles a path. In v10 that lane took the typed records from 3,242 to 3,259 and the `field_XX` members from 523
to 434 (`naka_gui_census.py`; 291 are still in `naka_sequencer_channels.c`); by its probe's rule 52 Viewable
elements are still untyped (69 before), 49 of them in the asm. Notes:
[`notes/kn5000-notes-2026-11-06/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/notes/kn5000-notes-2026-11-06/README.md).

## Event System

### Event Code Spaces

Events use 32-bit codes divided into two spaces:

**Events (0x01Cm00nn, firmware `EV_*`)** — notifications and requests:

| Event                 | Code      | Description                                                                                                                     |
|-----------------------|-----------|---------------------------------------------------------------------------------------------------------------------------------|
| `EVT_SHOW`            | 0x1C00001 | View shown (firmware EV_SHOW). Sent to a title's view after it becomes current; ViewableProc broadcasts it down the ...         |
| `EVT_HIDE`            | 0x1C00002 | View hidden/closed (firmware EV_HIDE); broadcast down the view tree like EV_SHOW.                                               |
| `EVT_SW_ON`           | 0x1C00008 | Panel switch pressed (firmware EV_SWON), param = switch number. Not specific to DISK MENU.                                      |
| `EVT_DRAW`            | 0x1C0000D | Draw this view only (firmware EV_DRAW); EV_PAINT and EV_REPAINT send it to self.                                                |
| `EVT_PARA_DRAW`       | 0x1C0000F | Draw the parameter/value text (firmware EV_PARADRAW); param = string pointer, or 0 to fetch the text with 0x1E0003A. ...        |
| `EVT_ACTIVATE_STATE`  | 0x1C00013 | Activation-state notification to a mode or title object (firmware EV_ACTIVATE). The param is a phase: 0 = mode ...              |
| `EVT_CHANGE_MODE`     | 0x1C00014 | Mode request, parameter `0x0180nnnn` ([details]({{ site.baseurl }}/event-codes/#mode-and-title-requests-0x01c00014-0x01c00016)) |
| `EVT_CHANGE_TITLE`    | 0x1C00015 | Title request, parameter `0x01A0nnnn`                                                                                           |
| `EVT_INTERRUPT_TITLE` | 0x1C00016 | Show a title temporarily on top of the current one (firmware EV_INTERRUPT_TITLE), e.g. a message, error, welcome or ...         |
| `EVT_NEW_TITLE`       | 0x1C00039 | Broadcast to the current view tree that a title has just become the new current title (firmware EV_NEW_TITLE).                  |
| `EVT_HDAE_SEQ_STOP`   | 0x1CA0000 | The sequencer stopped while HD-AE5000 song-list (FLS) playback is active. FlsLoadScreen reacts by arming a 0x53-tick AP ...     |
| `EVT_HDAE_TICKS`      | 0x1CA0004 | Song-position tick for the open lyric box. The parameter points to HDAE5000_RAM_LyricPosEvt (sqbtof, step, position) ...        |

**Methods (0x01Em00nn, firmware `MT_*`)** — queries and commands sent to an object:

| Event                        | Code      | Description                                                                                                                |
|------------------------------|-----------|----------------------------------------------------------------------------------------------------------------------------|
| `EVT_GET_CLASS_SP`           | 0x1E00000 | MT_GetClassSp. Asks an object table's proc for the class id of the object. SendEvent asks this of every target first ...   |
| `EVT_GET_PARENT_CLASS_SP`    | 0x1E00001 | MT_GetParentClassSp. Class-level query that returns the parent class id (Class record +4 'parent').                        |
| `EVT_GET_PROCEDURE_SP`       | 0x1E00002 | MT_GetProcedureSp. Returns the class procedure pointer (Class record +0 'proc').                                           |
| `EVT_GET_INSTANCE_SIZE_SP`   | 0x1E00003 | MT_GetInstanceSizeSp. Returns the instance size of the class (WORD at Class record +8 'allsize'). Not *(XHL+0x0C), as ...  |
| `EVT_GET_PROP_DATA_SP`       | 0x1E0000D | MT_GetPropDataSp. Returns entry #n of an ID-typed property's value domain: FontIDProc returns the n-th font from the ...   |
| `EVT_GET_PROP_DATA_COUNT_SP` | 0x1E0000E | MT_GetPropDataCountSp. Number of entries in an ID-typed property's value domain; FontIDProc returns the font count. It ... |
| `EVT_GET_INSTANCE`           | 0x1E0000F | MT_GetInstance. Returns a pointer to the object's instance record: the class record for a class, the mode or title ...     |
| `EVT_CHECK_CLASS`            | 0x1E00014 | MT_CheckClass. Object-level is-a test: returns 1 if the object's class is, or derives from, the class id in the ...        |
| `EVT_GET_SELECTED_CEL`       | 0x1E0008F | Firmware method MT_GetSelectedCel. It returns the selected cell packed as (col<<16)/row.                                   |
| `EVT_SET_VISIBLE`            | 0x1E0009C | Firmware method MT_SetVisible. It shows or hides a view: parameter 0 sets bit 0 of the view flags at instance+12 ...       |

### Event Dispatch Functions

| Function            | Description            |
|---------------------|------------------------|
| `MainDispatchEvent` | Primary event router   |
| `MainSendEvent`     | Direct event send      |
| `MainPostEvent`     | Post event to queue    |
| `SendEvent`         | Generic send           |
| `PostEvent`         | Generic post           |
| `DispatchEvent`     | Route by type          |
| `ApPostEvent`       | Application-level post |

### Sound-editor title functions (`DirmdEmulator`)

Each of the 32 sound-editor titles has an event proc, `SeXxxTitleFunc` (the firmware's own names, e.g.
`SeAmpEnv1TitleFunc`). The proc copies a 16-byte method table, `SeXxxTitleFunc_Methods`, to the stack and calls
`DirmdEmulator` with the event in XBC and its parameter in XDE. `DirmdEmulator` subtracts `EVT_NONE` and rejects
anything outside 0..15. It then looks up a 16-bit offset in `DirmdEmulator_CaseTable`, one per event, and jumps to
`DirmdEmulator_Dispatch` plus that offset. Only four events have a case:

| event                            | case                     | method called                                                                        |
|----------------------------------|--------------------------|--------------------------------------------------------------------------------------|
| `EVT_HIDE`                       | `DirmdEmulator_Dispatch` | +4 `SeXxxTitleFunc_OnHide` (`SeMenu_SetCurrentStep(0)`, then `SeMenu_ResetSubIndex`) |
| `EVT_SW_IN`, switch number ≤ 255 | `DirmdEmu_OnSwitchIn`    | +8 `SeXxxTitleFunc_OnSwitchIn`, with (switch & 31, bit 7) pushed                     |
| `EVT_ALL_PAINT`                  | `DirmdEmu_OnAllPaint`    | +0 `SeXxxTitleFunc_OnDraw`, after the drawing state is reset                         |
| `EVT_PARA_DRAW`                  | `DirmdEmu_OnParaDraw`    | +0 `SeXxxTitleFunc_OnDraw`, with the redraw mode byte set to 16                      |

The fourth method, +12 `SeXxxTitleFunc_Nop`, is a `jp` to a bare `ret`, and `DirmdEmulator` never calls it. Every
event, handled or not, then runs `DirmdEmu_DefaultCase`, which posts the part-change, mode-change, refresh and
other events whose request flags a method left set.

`SeXxxTitleFunc_OnSwitchIn` jumps to the title's `SeXxxTitleFunc_DispatchSwitch`, which calls `SeTitle_DecodeSwitch`:

| switch number | handler index             | bank byte                     |
|---------------|---------------------------|-------------------------------|
| 0–16          | the switch number         | 1 for the second bank, else 0 |
| 17–24         | switch − 17               | bit 7 set                     |
| 25            | 16                        | as above                      |
| anything else | not handled (HL = 0xFFFF) |                               |

The index names a control on the LCD. A button pair shares one switch number: the panel code posts
`EVT_SW_IN` with the pair's number, or with the number OR 0x80 for the pair's other button.
`GetEditSwPoint` places the numbers on screen:

| handler index | switch number                               | control                                                   | handler label                             |
|---------------|---------------------------------------------|-----------------------------------------------------------|-------------------------------------------|
| 0–7           | 0–7 (17–24 also land here, with bank bit 7) | the eight button columns under the LCD (x = 20, 60 … 300) | `SeXxx_OnColumn1` … `8`                   |
| 8–12          | 8–12, and 0x88–0x8C with bit 7              | side rows 1–5: RIGHT is the plain number, LEFT adds bit 7 | `SeXxx_OnSideRow1` … `5`                  |
| 13–14         | 13–14                                       | not identified                                            | `SeMenu_SwitchNop` in every table         |
| 15            | 15                                          | not identified                                            | `SeXxx_OnSwitch15`                        |
| 16            | 16 and 25                                   | not identified                                            | `SeXxx_OnSwitch25`, or `SeMenu_SwitchNop` |

For 31 titles, `SeXxxTitleFunc_DispatchSwitch` then calls `SeXxxTitleFunc_SwitchHandlers[index]` with WA = the
bank byte. In v10, 30 of those tables hold 17 code pointers (indices 0–16) and a zero. A slot a title does not use
holds `SeMenu_SwitchNop`, a bare `ret`. SeFilLfo1's is cut by a label after 14 slots and continues past it. Only
`SeMenu` decodes the switch the same way but acts on it in code, with no table. Source: `audio/sound_editor_routines.s`
(the stubs), `audio/presentation_sound_nav.s` (`DirmdEmulator`), `audio/semenu_routines.s` (`SeTitle_DecodeSwitch`),
and the tables in `kn5000_v*_program.s`. The same in v7, v9 and v10.

## Drawing Primitives API

The firmware provides a complete set of drawing primitives that render to the offscreen buffer (0x43C00) and VRAM (0x1A0000-0x1DFFFF). These are defined in `drawing_primitives.s`.

### Line Drawing

| Function     | Description                        |
|--------------|------------------------------------|
| `DrawLine`   | Draw a line between two points     |
| `DrawLineEx` | Extended line with pattern support |

### Geometric Shapes

| Function      | Description                                                                                                                                                          |
|---------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `DrawBox`     | Filled rectangle                                                                                                                                                     |
| `DrawFrame`   | Rectangle outline                                                                                                                                                    |
| `DrawFrameEx` | Extended frame with style                                                                                                                                            |
| `DrawFrameSP` | Frame with special properties                                                                                                                                        |
| `DrawWall`    | Full-screen background (wallpaper): copies the 320 × 240 image (76,800 bytes) whose address is held in RAM `0x030452` (set by `SetWall_X`) into the offscreen buffer |

### Bitmap Rendering

| Function           | Description                  |
|--------------------|------------------------------|
| `DrawBitmap`       | Standard bitmap render       |
| `DrawBitmapFast`   | Optimized bitmap render      |
| `DrawBitmapSP`     | Bitmap with transparency     |
| `DrawBitmapSPFast` | Optimized transparent bitmap |
| `DrawBitmapSP2`    | Bitmap variant 2             |
| `DrawBitmapFile`   | Render bitmap from file data |

### Text Rendering

| Function                 | Description                                                                           |
|--------------------------|---------------------------------------------------------------------------------------|
| `DrawString`             | Basic text output                                                                     |
| `DrawStringCentered`     | Centered text within bounds                                                           |
| `DrawStringLeftJustify`  | Left-aligned text                                                                     |
| `DrawStringRightJustify` | Right-aligned text                                                                    |
| `DrawStringAlignment`    | Text with specified alignment                                                         |
| `DrawStringReverse`      | Reverse-video text on a filled box (colours swapped), centred, left- or right-aligned |

### Pixel Operations

| Function     | Description           |
|--------------|-----------------------|
| `MovePixels` | Block pixel copy/move |
| `DrawIcons`  | Render icon set       |

## Page Management

The UI uses a hierarchy of Screens > Windows > Pages:

- **Screens** (`ScreenProc`, `IvScreenProc`) — Full-screen layouts that own the entire display
- **Windows** (`WindowProc`, `IvWindowPageControlProc`) — Contained regions within a screen
- **Pages** (`IvPageControlProc`, `PsPageBoxProc`) — Switchable content within a window

Page controllers (`IvPageControlProc`) manage which page is visible and handle transitions when the user switches tabs or modes. Window-level controllers (`IvWindowPageControlProc`) coordinate multiple pages within a single window.

### Known Page Identifiers

The firmware has no table of page identifiers. Of the names this page used to list, only `PC_DATA_LINK_PAGE`
(PC connection) and `HDD_UTIL_PAGE` (hard-disk utilities) exist. Both are entries in the HD-AE5000 ROM's own object
registry and name its routines `HDAE5000_PC_DATA_LINK_PAGE` and `HDAE5000_HDD_UTIL_PAGE`. The main firmware names
its screens by title (`TT_*` strings such as `TT_NORMAL` or `TT_SQMENU`) and by the view names in its ResName
tables. The [KN5000 Menu Map]({{ site.baseurl }}/kn5000-menu-map/) lists every title and mode, with its menu path
from the panel.

## Presentation System (SSF)

The firmware includes an **XML-based presentation scripting system** used for the built-in Feature Demo. This is a separate subsystem from the general widget framework, with its own XML parser, event handlers (`EV_READPRESENTATION`, `EV_READACTION`, `EV_READSONG`), and tag vocabulary (`PRESENTATION`, `ACTION`, `SHOW`, `IMG`, `SONG`, `EXEC`, etc.).

The presentation controller (`AcPresentationControlProc` at `0xF8450B`) dispatches actions via a jump table, and the Feature Demo script (`hkst_55.ssf`) drives a 27-step automated demonstration with bitmap images and instrument displays.

See [Feature Demo & Presentation System]({{ site.baseurl }}/feature-demo/) for full documentation.

## Code References

### Include Files

| File (under `v10/maincpu/`)     | Contents                                                                                                             |
|---------------------------------|----------------------------------------------------------------------------------------------------------------------|
| `ui/drawing_primitives.s`       | Line, box, frame, bitmap, string rendering                                                                           |
| `audio/semenu_routines.s`       | Sound editor menu (SeMenu) event handling and navigation                                                             |
| `ui/bitmap_out_routines.s`      | Bitmap blitting and palette loading                                                                                  |
| `ui/psgridbox_routines.s`       | PS Grid Box widget                                                                                                   |
| `ui/rvari_routines.s`           | RVari (rhythm variation) screen renderer and interaction                                                             |
| `demo/fdemotext_routines.s`     | Feature-demo text processing                                                                                         |
| `ui/setwall_routines.s`         | Sequencer TRACK ASSIGN page (SqTrAs) and the routines after it (historical `SetWall_` prefix); it loads no wallpaper |
| `sequencer/bmdredit_routines.s` | Bitmap drum editor                                                                                                   |

### Key Routines

| Symbol                  | Address  | Description                      |
|-------------------------|----------|----------------------------------|
| `InitializeObjectTable` | 0xFA40B3 | Boot-time UI module registration |
| `MainDispatchEvent`     | —        | Primary event router             |
| `MainFuncCall`          | —        | Widget function call dispatcher  |
| `GetViewInstance`       | —        | Get widget view instance         |
| `RegisterObjectTable`   | —        | Register widget object table     |
| `DrawLine`              | —        | Line drawing primitive           |
| `DrawBitmapFile`        | —        | File-based bitmap rendering      |
| `DrawStringCentered`    | —        | Centered text rendering          |

## Related Pages

- [Feature Demo & Presentation System]({{ site.baseurl }}/feature-demo/) - SSF XML scripting system
- [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) - Input handling
- [Display Subsystem]({{ site.baseurl }}/display-subsystem/) - Screen rendering
- [Image Gallery]({{ site.baseurl }}/image-gallery/) - UI graphics
- [Event Codes]({{ site.baseurl }}/event-codes/) - Complete event code reference
- [KN5000 Menu Map]({{ site.baseurl }}/kn5000-menu-map/) - Every title and mode, with its menu path

## ScreenData Bytecode Format

The UI framework uses a **bytecode format** to define screen layouts. Each screen has a `ScreenData` blob — a sequence of variable-length commands that describe the visual elements (lines, rectangles, widgets, strings, references) to render.

### Command Format

Each command starts with an opcode byte followed by a sub-type/length byte:

```
[opcode:1] [sub_or_len:1] [data:variable]
```

**Critical rule for op=0x02:** Byte 2 is a **sub-type**, NOT a length.
- sub=0x0a → VLINE (10 bytes total)
- any other sub → WIDGET (always 15 bytes total)

For all other opcodes, byte 2 is the total command length.

### Opcode Reference

| Opcode     | Name        | Size | Description                                                          |
|------------|-------------|------|----------------------------------------------------------------------|
| 0x01       | HLINE       | 10   | Horizontal line: `op + 0x0a + x1(2) + y1(2) + x2(2) + y2(2)`         |
| 0x02/0x0a  | VLINE       | 10   | Vertical line: `op + 0x0a + x1(2) + y1(2) + x2(2) + y2(2)`           |
| 0x02/other | WIDGET      | 15   | Widget ref: `op + sub + id(2) + flags(2) + handler(7) + x(1) + y(1)` |
| 0x03       | SETUP       | var  | Setup block with coordinate arrays                                   |
| 0x04       | CONTROL     | var  | Control metadata                                                     |
| 0x06       | REF         | var  | Reference (sometimes with text label)                                |
| 0x07       | SHORTREF    | var  | Short reference                                                      |
| 0x09       | RECT        | 10   | Rectangle outline: same coord format as HLINE                        |
| 0x0a       | FILLED_RECT | 10   | Filled rectangle: same coord format as HLINE                         |
| 0x0b       | BLOCK       | var  | Block data                                                           |
| 0x0e       | CALLBACK    | var  | Callback reference                                                   |
| 0x20       | STRING      | var  | Text: `op + len + x(1) + y(1) + text_bytes...`                       |

### WIDGET Structure (15 bytes)

```
[02] [sub] [id_lo id_hi] [flags_lo flags_hi] [06 addr_lo addr_mid addr_hi 00 param 00] [x] [y]
       │         │              │                            │                            │
       │         │              │                   handler reference (7 bytes)           position
       │         │              └─ widget flags (e.g., 0x00FF, 0x8560)
       │         └─ widget ID (little-endian 16-bit)
       └─ sub-type (0x0f=standard, 0x0d=variant, 0x14=extended)
```

### Coordinate Encoding

All coordinates are **little-endian 16-bit** values. The LCD display is 320×240 pixels.

### LCD Character Codes

| Byte      | Character                   |
|-----------|-----------------------------|
| 0x20-0x7E | Standard ASCII              |
| 0x88      | ♭ (flat)                    |
| 0x8C      | ♯ (sharp)                   |
| 0x8D      | │ (vertical bar / up arrow) |
| 0x8E      | ~ (down arrow)              |

### Decoded Files

These blocks are typed C struct source per `<version>/maincpu/style_ui/*.c`, compiled and
`.incbin`'d into `ui_widgets/style_ui_params.s` — see
**[ScreenData C Conversion]({{ site.baseurl }}/screendata-c-conversion/)** for the full
inventory across all three ScreenData subsystems:

| File                    | Bytes | Commands | Contents                                                                              |
|-------------------------|-------|----------|---------------------------------------------------------------------------------------|
| `style_ui/main.c`       | 3531  | 375      | Style editor main grid: chord boxes, parameter widgets, chord name tables, bottom bar |
| `style_ui/meascursor.c` | 184   | 18       | Measure cursor: MEAS/CURSOR/CTL labels, BAL/ERS refs, navigation arrows               |
| `style_ui/yesctl.c`     | 228   | 29       | Yes/No confirmation + measure cursor + CTL value                                      |
| `style_ui/ctlonly.c`    | 551   | 4+tables | CTL-only: 4 commands + LCD charset translation table + format strings                 |

### Decoder Scripts

⚠ **Stale**: both scripts below still hardcode the path from before the tree moved to the typed
`.c` layout above (`maincpu/includes/style_ui_screendata_main.s`, which does not exist at any
version) and fail with `FileNotFoundError` — reproduced directly. Their command-format
documentation earlier on this page is still correct; only the file-loading path is broken.

- `scripts/analysis/decode_screendata.py` — Generic bytecode parser, outputs human-readable command descriptions
- `scripts/tools/annotate_screendata_main.py` — Section-aware annotation generator for the main screen

## Research Needed

- [x] Document widget property layout (offset table per widget type): the class definitions name every field; see [The class system describes itself](#the-class-system-describes-itself).
- [ ] Map complete event dispatch chain (post → queue → dispatch → handler)
- [ ] Document focus/navigation system (tab order, encoder routing)
- [ ] Trace widget creation flow (alloc → init → register → display)
- [ ] Decode ScreenData for other UI screens beyond StyleUI
