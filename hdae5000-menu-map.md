---
layout: page
title: HD-AE5000 Menu Map
permalink: /hdae5000-menu-map/
---

# HD-AE5000 Menu Map

The HD-AE5000's whole user interface is one NAKA object table: Viewable table `0x7F`, which
`HDAE5000_Handler_Registration` registers with the main CPU's GUI framework. Version 2.06i has
**789 objects in 78 top-level trees** (screens, windows and dialogs). Version 2.01i has 786 objects
in the same 78 trees. This page shows how the disassembly writes that table, and it summarises the
78 top-level objects. The full per-widget maps are generated files in the disassembly repository:

- [`menu-map-v2_06i.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/notes/data-gui-hdae5000-2026-10-29/menu-map-v2_06i.md): v2.06i, 789 objects;
- [`menu-map-v2_01i.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/notes/data-gui-hdae5000-2026-10-29/menu-map-v2_01i.md): v2.01i, 786 objects.

Both are written by [`scripts/analysis/hdae5000_menu_map.py`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/scripts/analysis/hdae5000_menu_map.py)
from the source (`make hdae5000-menu-map`). `make gate` runs it with `--check`, so a map that no
longer matches the source fails the gate. The lane notes that produced all of this are
[`notes/data-gui-hdae5000-2026-10-29/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/notes/data-gui-hdae5000-2026-10-29/README.md).

## How the source writes the GUI

Each tree writes its GUI in `<tree>/hdae5000_ui_tree.s`
([v2.06i](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/hdae5000/hdae5000_ui_tree.s), [v2.01i](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/hdae5000_v2_01i/hdae5000_ui_tree.s)): one
class-macro line per object, nested with `ui_sub` / `ui_endsub`.

```
	TtlScreenR	HDDMENU, x=0, y=0, w=320, h=240, exit=TITLE_DKMENU, window=HdaeUiVar_HDDMENU_window, icon=idICON_i129, title="HD-AE5000"
	ui_sub
		AcScreenMenu	HDDMENU_SETUP_TOOLS, x=8, y=72, w=149, h=26, editsw=ES_Left2, selected=HdaeUiVar_HDDMENU_SETUP_TOOLS_selected, screen=HDAE5000_OBJ_SETUPS_TOOLS, icon=idICON_i6, str="SETUP & TOOLS  "
		AcScreenMenu	HDDMENU_Go_LOAD_BY_NUM, x=163, y=114, w=149, h=26, editsw=ES_Right3, ..., screen=HDAE5000_OBJ_LOAD_BY_NUM, icon=idICON_i172, str=""
		ui_sub
			AcLanguageText1	HDDMENU_Go_LOAD_BY_NUM_Text6, x=170, y=114, w=112, h=32, index=6, font=idCHARA1, fontcolor=CL_White, alignment=AL_LeftJustify, lines=2
		ui_endsub
		...
	ui_endsub
```

How to read a line:

| part           | what it is                                                                                                                                                                                                                                                                                                                         |
|----------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| the macro      | the object's NAKA class, by name: one macro per class the HD-AE5000 instantiates (42), in [`hdae5000/shared/naka_ui_macros.s`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/hdae5000/shared/naka_ui_macros.s), shared by both trees. Each macro's header lists every field with its offset and type letter |
| the parameters | the firmware's own field names: the `propname` lists of the class chain (the main CPU's class tables for classes `0x160`, `HDAE5000_RECORD_TABLE` for the HD-AE5000's own 13 classes in table `0x16A`)                                                                                                                             |
| first argument | the object's name: the firmware's resource name wherever its name table has one (178 objects); otherwise made up from the parent and the caption, the object it opens, its language text or its class (`HDDMENU_Go_LOAD_BY_NUM`, `SELECT_DIR_Exit_HDDMENU`)                                                                        |
| `x, y, w, h`   | the geometry. The record stores `Viewable.rect` as x1, y1, x2, y2 inclusive; the macro converts                                                                                                                                                                                                                                    |
| the nesting    | the tree. The macros number the objects in order of appearance and compute each record's `super` / `sub` / `next` / `prev` links from the nesting; no index is written anywhere                                                                                                                                                    |
| `fld="text"`   | an inline caption stored after the record; `fld_at=Label` is a pointer to a string elsewhere                                                                                                                                                                                                                                       |

Values are spelled by name wherever the firmware or the source has one:

- object ids: `HDAE5000_OBJ_<name>` (`0x007F0000` + index), and `NAKA_NO_OBJECT`;
- function ids: `NAKA_APFUNC_*` (`0x012A0000` + k, entry k of `HDAE5000_ObjHandler_Table`) and
  `NAKA_MAINFUNC_*` (`0x014A0000` + k, entry k of `HDAE5000_ScreenProc_Table`); the procedure is
  `HDAE5000_<name>`;
- titles: `TITLE_*`;
- property values by the firmware's own names, read from the main CPU's
  `SupportClass_PropTypeRecords`: colours `CL_*`, borders `BD_*`, alignment `AL_*`, edit
  switches `ES_*`, styles `SS_*`, line modes `LM_*`, view flags `VF_*`; fonts and icons by
  their dump names (`idCHARA1`, `idICON_i6`). These are the same names the main-CPU GUI uses in its
  C ([UI Framework]({{ site.baseurl }}/ui-framework/)). One generator,
  `scripts/generators/gen_naka_gui_headers.py`, writes the C `#define`s and their `.equ` twins in
  [`hdae5000/shared/naka_values.s`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/hdae5000/shared/naka_values.s);
- RAM-variable pointers: `HdaeUiVar_<object>_<field>`, the label of the variable's initial value
  in the `.data` image (322 labels in v2.06i, 318 in v2.01i).

`ui_ram_object NAME, Class` marks one of the 20 objects whose record lives in the `.data` image
(written with the same class macro between `ui_ram_records` and `ui_ram_records_end` in
`hdae5000_init_data.s`). `ui_object_table` generates `HDAE5000_UiObject_PtrTable` and
`ui_name_table` generates `HDAE5000_UiObjectName_PtrTable`; the name pool
`HDAE5000_UiObjectName_Pool` is one `ui_name` / `ui_noname` line per object, highest index first.
The macros also define `HdaeUi_<name>` (the record), `HdaeUi_<name>_<field>` (a caption),
`HdaeUiRam_<name>` (a `.data`-image record), `HdaeUiName_<name>` (the name string) and
`HDAE5000_UI_OBJECT_COUNT` (789 in v2.06i).

The button texts are this ROM's own: `HDAE5000_AcLanguageText1Proc` draws message `index` of its
switch (`HDAE5000_LangText_CaseTable`, indices 1-67 and 200-212) from the strings
`HDAE5000_LangMsg_001_EN` and its German and French twins `HDAE5000_LangMsg_001_DE` and `HDAE5000_LangMsg_001_FR`. Every tree line of an `AcLanguageText1`
object ends in `; EN "<text>"`, and the maps show the text.

### What backs it

- **Class ids.** Every record starts with `0x016S_KKKK`: class table `0x16S`, entry `KKKK`
  (the main CPU's `ClassProc`). Every record of both versions resolves to a class, and the converter
  refuses otherwise. A class's fields sum to its `allsize`, and in every record the inline captions
  start exactly there.
- **Links.** Viewable `+4` super, `+6` sub, `+8` next and `+10` prev are object indices, and the
  table is the preorder walk of the forest they describe: 0 inconsistent links in either version
  (`notes/data-gui-hdae5000-2026-10-29/probes/tree_preorder.py`). So the nesting carries all the
  information, and the macros reproduce the links byte for byte.
- **Edit switches.** `ES_Bottom1-8` = 0-7, `ES_Right1-5` = 8-12, `ES_Left1-5` = `0x88`-`0x8C`,
  `ES_Exit` = `0x0F`, `ES_None` = `0xFF` (the firmware's own names). `probes/editsw_geometry.py`
  checks that every side-row value sits on that side at that row's height and every Bottom value on
  the bottom row, in both versions.
- **The `0x0070xxxx` words of the UI state block** are the initial values of 29 of the 31
  `SelectList.str_adr` variables. They are inert: `HDAE5000_SelectListProc` draws only while the
  list's `en_paradraw` is 1, all 31 start at 0, and a screen gives the list its strings with
  `EVT_HDAE_SET_STR_ADR` (`probes/str_adr_initial_values.py`). [INFERENCE] They are link-time
  addresses of another build; no base maps them onto this ROM.

The converter that wrote the tree from the ROM is
[`scripts/converters/hdae5000_ui_tree.py`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/scripts/converters/hdae5000_ui_tree.py)
(`python3 scripts/converters/hdae5000_ui_tree.py v2_06i v2_01i --macros --write`; it refuses on any
layout surprise). `scripts/analysis/hdae5000_gui_readability.py` counts what is still numeric: at the
lane's base (`9dbc03088`) v2.06i had 789 numeric class ids, 3,156 numeric links and 6,379 unnamed
field words; after the lane, every column is 0 for both versions.

## How the screens connect

From the main screen, `HDDMENU` ("HD-AE5000"; its EXIT goes to `TITLE_DKMENU`). Arrows are
object-id fields (an `AcScreenMenu.screen` button, an `IvPageControl.window` page switch), with the
LCD switch that carries them; the other screens are opened by the routine named beside them, or by
nothing the map can see.

- `HDDMENU` -- the HD-AE5000 main screen
  - Right1 -> `Tech_lyrics` ("TECH LYRICS"): the lyrics display; `LoadLyricFD` loads lyrics from floppy
  - Right2 -> `SELECT_DIR` ("HD DIR SELECT", select by name) -> `SELECT_FILE` -> pages
    `HD_FILE_LOAD_P1` / `HD_FILE_LOAD_P2`; `SELECT_FILE_A_Z` with `FILE_LOAD_A_Z`
  - Right3 -> `LOAD_BY_NUM` ("LOAD BY NUMBER") -> pages `LBN_P1` / `LBN_P2`
  - Right4 -> `FLS_SELECT` (" F.L.S. SELECT", file load scripts) -> `FLS_FILE_LOAD`,
    `FLS_DIR_SEL`, `FLS_FILE_SEL`, `FLS_EDIT`, `HDD_FLS_NAMING` / `HDD_FLS_NAMING2`
  - Left2 -> `SETUPS_TOOLS` (" SETUP & TOOLS ") -> pages
    - `SETUP_TOOLS_P1`: WRITE PROTECT, WRITE CONFIRM, QUICK LD MODE, LD BY NUM. M., JUMP AFTER LD.;
      -> `PC_DATA_LINK`, -> `LyrSettings` ("LYRICS OPTIONS")
    - `SETUP_TOOLS_P2`: SAVE SETUP, HD-AE INFOS, HD FORMAT (`SW_HD_FORMAT`), -> `ABOUT_HELP`;
      its switch catch `HDAE5000_SetupP2SwCatch` opens `SETUP_HDINFO` and `ATTEN_HD_FORMAT`
  - Left3: COPY FD TO HARD DISK; `CP_FD` ("COPY TECH TO HD") is opened by code
    (`HDAE5000_FdList_Scan`, `HDAE5000_CopyToHd_Execute`, ...); with `CP_FD_DIRSEL`, `CP_FD_DIR_NAMING`
  - Left4 -> `OUTPUT_SETTING`
- saving: `SAVE_OPT_SCREEN` ("SAVE OPTION", opened by `HDAE5000_HDDNamingCheck_Join`) ->
  `HDD_FILE_NAMING`, with `HddNamingWindow`
- deleting: `FILE_DEL_SCREEN` ("HD FILE DELETE"), with the `ATTEN_DEL_*` and `WAIT_DEL_*` dialogs
- service: `HARD_TEST` ("HARDWARE TEST"), `HD_UTIL` ("HD UTILITY") and `DBG_MEMO_SCREEN` ("DEBUG
  MEMO SCREEN"): no object-id field and no routine in this ROM names them
- dialogs: `ATTEN_*` confirmations, `ERR_HD_*` system errors ("Hard disk FAT read error." ...),
  `ERR_SAVE` / `ERR_LOAD`, `HD_PLEASE` ("Please wait ...", named by nine routines)

## The 78 top-level objects (v2.06i)

In tree order, which is object-table order. "Opened by an object on" lists the top-level trees
holding an object whose object-id field names this one (a button, an EXIT or a page switch);
"code refs" counts the routines whose code names its id. Each name is the firmware's resource name.

| object                | class             | caption                | children | opened by an object on                                                                                            | code refs |
|-----------------------|-------------------|------------------------|----------|-------------------------------------------------------------------------------------------------------------------|-----------|
| `HDDMENU`             | TtlScreenR        | "HD-AE5000"            | 18       | SETUPS_TOOLS, SELECT_DIR, HARD_TEST, OUTPUT_SETTING, LOAD_BY_NUM, CP_FD, FLS_SELECT, DBG_MEMO_SCREEN, Tech_lyrics | 2         |
| `SETUPS_TOOLS`        | TtlScreenR        | " SETUP & TOOLS "      | 4        | HDDMENU, HD_UTIL, SETUP_HDINFO, ABOUT_HELP, LyrSettings                                                           | 3         |
| `SELECT_FILE`         | TtlScreenR2       | -                      | 9        | SELECT_DIR2, FD_FILE_SELECT, HDD_FILE_NAMING, FILE_DEL_SCREEN                                                     | 9         |
| `SELECT_DIR`          | TtlScreenR2       | "HD DIR SELECT"        | 14       | HDDMENU, SELECT_FILE, HDD_DIR_NAMING, SELECT_FILE_A_Z                                                             | 1         |
| `SELECT_DIR2`         | TtlScreenR2       | " DIRECTORY SELECT   " | 8        | -                                                                                                                 | 0         |
| `FD_FILE_SELECT`      | TtlScreenR2       | " FD FILE SELECT   "   | 10       | -                                                                                                                 | 0         |
| `HARD_TEST`           | TtlScreenR2       | "HARDWARE TEST"        | 8        | -                                                                                                                 | 0         |
| `HDD_FILE_NAMING`     | TtlScreenR        | "EDIT FILE NAME"       | 8        | SAVE_OPT_SCREEN                                                                                                   | 2         |
| `HD_FILE_NAME`        | AcNamingWindow    | -                      | 0        | -                                                                                                                 | 0         |
| `HDD_DIR_NAMING`      | TtlScreenR        | "EDIT DIRECTORY NAME"  | 5        | -                                                                                                                 | 1         |
| `HD_PLEASE_WIN`       | Window            | -                      | 1        | -                                                                                                                 | 0         |
| `HD_UTIL`             | TtlScreenR2       | "HD UTILITY"           | 5        | -                                                                                                                 | 0         |
| `PC_DATA_LINK`        | TtlScreenR2       | "   PC DATA LINK"      | 7        | SETUP_TOOLS_P1                                                                                                    | 0         |
| `SETUP_TOOLS_P1`      | Window            | -                      | 11       | SETUPS_TOOLS                                                                                                      | 0         |
| `SETUP_TOOLS_P2`      | Window            | -                      | 10       | SETUPS_TOOLS                                                                                                      | 0         |
| `OUTPUT_SETTING`      | TtlScreenR        | "OUTPUT SETTING"       | 9        | HDDMENU                                                                                                           | 0         |
| `LOAD_BY_NUM`         | TtlScreenR2       | "LOAD BY NUMBER"       | 5        | HDDMENU                                                                                                           | 3         |
| `LBN_P1`              | Window            | -                      | 25       | LOAD_BY_NUM                                                                                                       | 0         |
| `LBN_P2`              | Window            | -                      | 34       | LOAD_BY_NUM                                                                                                       | 0         |
| `CP_FD`               | TtlScreenR2       | "COPY TECH TO HD"      | 15       | CP_FD_DIRSEL, ERR_NO_HK_DATA                                                                                      | 4         |
| `CP_FD_DIRSEL`        | TtlScreenR2       | "HD DIR SELECT"        | 13       | CP_FD_DIR_NAMING, ATTEN_FULL_DIR, ATTEN_CP_UNNAMED                                                                | 3         |
| `FLS_SELECT`          | TtlScreenR2       | " F.L.S. SELECT"       | 14       | HDDMENU, HDD_FLS_NAMING, FLS_FILE_LOAD                                                                            | 1         |
| `HD_FILE_LOAD_P1`     | Window            | -                      | 16       | SELECT_FILE                                                                                                       | 0         |
| `HD_FILE_LOAD_P2`     | Window            | -                      | 35       | SELECT_FILE, SELECT_FILE_A_Z                                                                                      | 0         |
| `HDD_FLS_NAMING`      | TtlScreenR        | "EDIT FLS NAME"        | 5        | -                                                                                                                 | 1         |
| `FLS_FILE_LOAD`       | TtlScreenR2       | "F.L.S. FILE LOAD"     | 19       | FLS_DIR_SEL, FLS_EDIT                                                                                             | 4         |
| `FLS_DIR_SEL`         | TtlScreenR2       | "F.L.S. DIR SELECT"    | 10       | FLS_FILE_SEL                                                                                                      | 1         |
| `FLS_FILE_SEL`        | TtlScreenR2       | "F.L.S. FILE SELECT"   | 9        | -                                                                                                                 | 1         |
| `FLS_EDIT`            | TtlScreenR2       | "F.L.S. EDIT"          | 23       | HDD_FLS_NAMING2                                                                                                   | 10        |
| `CP_FD_DIR_NAMING`    | TtlScreenR        | "EDIT DIRECTORY NAME"  | 5        | -                                                                                                                 | 1         |
| `Root_AcNamingWindow` | AcNamingWindow    | -                      | 0        | -                                                                                                                 | 0         |
| `SAVE_OPT_SCREEN`     | TtlScreenR2       | "SAVE OPTION"          | 43       | -                                                                                                                 | 1         |
| `HddNamingWindow`     | AcHddNamingWindow | -                      | 19       | -                                                                                                                 | 6         |
| `FILE_DEL_SCREEN`     | TtlScreenR2       | "HD FILE DELETE"       | 41       | -                                                                                                                 | 2         |
| `HDD_ICON_DISPLAY`    | Screen            | -                      | 1        | -                                                                                                                 | 0         |
| `IV_HDDMENU`          | IvScreenR2        | -                      | 0        | -                                                                                                                 | 1         |
| `ATTEN_DEL_DIR`       | TtlScreenR2       | -                      | 8        | -                                                                                                                 | 1         |
| `WAIT_DEL_DIR`        | Window            | -                      | 2        | -                                                                                                                 | 1         |
| `ATTEN_DEL_FILE`      | TtlScreenR2       | -                      | 8        | -                                                                                                                 | 1         |
| `ATTEN_OVER_FLS`      | TtlScreenR        | -                      | 8        | -                                                                                                                 | 1         |
| `ATTEN_DEL_FLS2`      | TtlScreenR        | -                      | 9        | -                                                                                                                 | 1         |
| `WAIT_DEL_FILE`       | Window            | -                      | 2        | -                                                                                                                 | 1         |
| `ATTEN_HD_FORMAT`     | TtlScreenR2       | "   HD FORMAT"         | 8        | ERR_HD_FORMAT, AGAIN_HD_FORMAT                                                                                    | 2         |
| `WAIT_HD_FORMAT`      | Window            | -                      | 3        | -                                                                                                                 | 1         |
| `SETUP_HDINFO`        | TtlScreenR2       | -                      | 4        | -                                                                                                                 | 1         |
| `DBG_MEMO_SCREEN`     | TtlScreenR        | "DEBUG MEMO SCREEN"    | 2        | -                                                                                                                 | 0         |
| `ATTEN_DEL_FLS1`      | TtlScreenR        | -                      | 11       | -                                                                                                                 | 1         |
| `ATTEN_OVER_FILE`     | TtlScreenR        | -                      | 8        | -                                                                                                                 | 2         |
| `HDD_FLS_NAMING2`     | TtlScreenR        | "EDIT FLS NAME"        | 5        | -                                                                                                                 | 1         |
| `ATTEN_CPHD_WR`       | TtlScreenR        | -                      | 7        | -                                                                                                                 | 1         |
| `ERR_HD_NOT_FMT`      | TtlScreenR        | -                      | 4        | -                                                                                                                 | 0         |
| `ERR_HD_SRAM`         | TtlScreenR        | -                      | 4        | -                                                                                                                 | 0         |
| `ERR_HD_RESET`        | TtlScreenR        | -                      | 4        | -                                                                                                                 | 0         |
| `ERR_HD_READ`         | TtlScreenR        | -                      | 4        | -                                                                                                                 | 0         |
| `ERR_HD_ID_READ`      | TtlScreenR        | -                      | 4        | -                                                                                                                 | 0         |
| `ERR_HD_TRACK_0`      | TtlScreenR        | -                      | 4        | -                                                                                                                 | 0         |
| `ERR_HD_FAT`          | TtlScreenR        | -                      | 4        | -                                                                                                                 | 0         |
| `ERR_HD_FSB`          | TtlScreenR        | -                      | 4        | -                                                                                                                 | 0         |
| `ATTEN_CPFD_MARK`     | TtlScreenR        | -                      | 6        | -                                                                                                                 | 1         |
| `ABOUT_HELP`          | TtlScreenR        | "            "         | 18       | SETUP_TOOLS_P2                                                                                                    | 0         |
| `WAIT_TR0_RECOVER`    | Window            | -                      | 2        | -                                                                                                                 | 1         |
| `ERR_SAVE`            | IvScreenR2        | -                      | 5        | -                                                                                                                 | 6         |
| `ERR_LOAD`            | IvScreenR2        | -                      | 5        | -                                                                                                                 | 1         |
| `ERR_NO_HK_DATA`      | IvScreenR2        | -                      | 5        | -                                                                                                                 | 1         |
| `ATTEN_FULL_DIR`      | IvScreenR2        | -                      | 6        | -                                                                                                                 | 1         |
| `ATTEN_CP_UNNAMED`    | IvScreenR2        | -                      | 6        | -                                                                                                                 | 1         |
| `DIR_OUT_RANGE`       | IvScreenR2        | -                      | 4        | -                                                                                                                 | 1         |
| `FILE_OUT_RANGE`      | IvScreenR2        | -                      | 4        | -                                                                                                                 | 1         |
| `HD_PLEASE`           | IvScreenR2        | -                      | 2        | -                                                                                                                 | 9         |
| `ERR_HD_FORMAT`       | IvScreenR2        | -                      | 6        | -                                                                                                                 | 1         |
| `AGAIN_HD_FORMAT`     | IvScreenR2        | -                      | 6        | -                                                                                                                 | 1         |
| `SELECT_FILE_A_Z`     | TtlScreenR2       | -                      | 5        | -                                                                                                                 | 0         |
| `FILE_LOAD_A_Z`       | Window            | -                      | 23       | SELECT_FILE_A_Z                                                                                                   | 0         |
| `Tech_lyrics`         | TtlScreenR2       | "TECH LYRICS"          | 19       | HDDMENU, LoadLyricFD                                                                                              | 6         |
| `LoadLyricFD`         | TtlScreenR3       | "LOAD LYRICS FROM FD"  | 4        | -                                                                                                                 | 1         |
| `FD_PLEASE`           | TtlScreenR2       | -                      | 2        | -                                                                                                                 | 0         |
| `LyrSettings`         | TtlScreenR2       | "LYRICS OPTIONS"       | 7        | SETUP_TOOLS_P1                                                                                                    | 0         |
| `WriteIn`             | Window            | -                      | 0        | -                                                                                                                 | 0         |

## What differs in v2.01i

The two maps have the same 78 top-level trees in the same order. The differences, read from the
two generated maps:

| object           | v2.06i                                                                       | v2.01i                                                                          |
|------------------|------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| `HDDMENU`        | 18 children; "LYRICS WINDOW" text box                                        | 19 children: an extra "Evaluation 01-01-99" text; "LYRIC WINDOW"                |
| `SETUP_TOOLS_P1` | "LYRICS OPTIONS" button                                                      | "LYRIC SETTINGS" button, with an HD icon                                        |
| `ATTEN_OVER_FILE`| English language-text objects (YES / NO / "!ATTENTION!")                     | German text boxes (JA / NEIN / "!ACHTUNG!")                                     |
| `Tech_lyrics`    | caption "TECH LYRICS"                                                        | caption "TECH LYRIC"                                                            |
| `LoadLyricFD`    | "LOAD LYRICS FROM FD", 4 children                                            | "Load Lyric From FD", 6 children (adds "New" and "Save" labels)                 |
| `LyrSettings`    | "LYRICS OPTIONS": load mode, active and passive colours                      | "Lyric Settings": "Jump after Load" only                                        |

Both versions are byte-identical rebuilds (`make gate`); see
[HD-AE5000 Overview]({{ site.baseurl }}/hdae5000/#firmware-versions) for the versions themselves.

## Related

- [HD-AE5000 Overview]({{ site.baseurl }}/hdae5000/): the ROM layout these tables sit in
- [Resources & Object Registry]({{ site.baseurl }}/hdae5000-resources/): the 69-object registry, the 178 named UI objects, the `.data` image
- [UI Framework]({{ site.baseurl }}/ui-framework/) and [UI Widget Types]({{ site.baseurl }}/ui-widget-types/): the main CPU's class system these objects instantiate
