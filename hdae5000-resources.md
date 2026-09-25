---
layout: page
title: HDAE5000 Resources & Object Registry
permalink: /hdae5000-resources/
---

# HD-AE5000 Resources & Object Registry

The HD-AE5000 firmware publishes almost everything it owns to the KN5000's main CPU **by name**. Screens, UI classes, event types, message types, validation callbacks and even bitmaps are registered as name/pointer pairs, and the names are the original developers' own identifiers. Those tables survived in the ROM, and they are the closest thing to source code that exists for this product.

This page collects them. It is a companion to the [HDAE5000 Hard Disk Expansion]({{ site.baseurl }}/hdae5000/) overview page.

**Provenance.** Everything here comes from four disassembly packages landed in August 2026 — commits `db26eca`, `b893ee8`, `b7752bc` and `abdf0ea` in the `kn5000-roms-disasm` repository. Before them, the two largest tables on this page were being decoded as TLCS-900 instructions: the long runs of `nop` that the disassembler emitted were the tables' 0x00 string padding, and operands such as `ld xiy,0x5443454c` were ASCII (`"LECT"`).

## Where the tables live

| ROM | Bytes | Structure |
|-----|------:|-----------|
| 0x29BAFC | 1,252 | Name strings for the 69 registered objects |
| 0x29BFE0 | 202 | Parameter-name strings for the 13 UI classes |
| 0x29C0AA | 6,356 | `RECORD_TABLE` — 13 class records of 24 bytes, then the 13 class-name strings |
| 0x29D97E | 660 | Record-count word `0x000D`, then 44 `EV_*` / `MT_*` / `*Proc` name strings |
| 0x29DC12 | 33,050 | The 769 UI object descriptors — **still decoded as instructions** |
| 0x2A5D2C | 3,160 | `UiObject_PtrTable` — 790 `.long` |
| 0x2A6984 | 3,160 | `UiObjectName_PtrTable` — 790 `.long` |
| 0x2A75DC | 3,774 | `UiObjectName_Pool` — the object name strings |
| 0x2A849A | 244 | 15 screen and switch-catch name strings |
| 0x2F94B2 | 3,202 | The initialised `.data` image, copied to RAM 0x23952A at boot |

## The 69-object registry

`HDAE5000_Clear_Work_Buffer` copies the `.data` image to RAM `0x23952A`; `HDAE5000_Handler_Registration` then publishes two index-parallel 70-entry arrays from it — handler entry points (registration ID 0x012A) and their names (ID 0x042A), both on PPI port 0x01600002, both with the immediate count `0x45` = 69. Entry 69 of each is a terminator (a NULL pointer and an empty string).

Every one of the 69 code pointers lands inside this ROM, between 0x280395 and 0x28F2F7. That is what settles the old "Windows DLL callbacks" reading of these names: they are firmware objects, not PC-side callbacks.

Naming conventions visible in the list: `*Check` are validation callbacks, `*Catch` are event sinks, `*Page`/`*PAGE` are page constructors, `Bitmap*` are image resource providers, `Sfx*` are per-file-suffix handlers and `LBN*` belong to the LOAD BY NUMBER screen.

| # | Registered name | Handler |
|--:|-----------------|---------|
| 0 | `HardTestPage` | 0x282811 |
| 1 | `HDDNamingCheck` | 0x284298 |
| 2 | `HDD_DIRNAMECheck` | 0x28446D |
| 3 | `HDD_UTIL_PAGE` | 0x284596 |
| 4 | `PC_DATA_LINK_PAGE` | 0x284E53 |
| 5 | `SeparateOutputModeCheck` | 0x2850ED |
| 6 | `SaveOptNameCheck` | 0x28539F |
| 7 | `FileOptNameCheck` | 0x28577C |
| 8 | `SfxLswBitCheck` | 0x285802 |
| 9 | `SfxPmtBitCheck` | 0x2858B8 |
| 10 | `SfxSqtBitCheck` | 0x28596E |
| 11 | `SfxCmpBitCheck` | 0x285A24 |
| 12 | `SfxTmBitCheck` | 0x285ADA |
| 13 | `SfxMspBitCheck` | 0x285B90 |
| 14 | `SfxRcmBitCheck` | 0x285C46 |
| 15 | `SfxMdBitCheck` | 0x285CFC |
| 16 | `SfxTlxBitCheck` | 0x285DB2 |
| 17 | `WriteProtectEditCheck` | 0x285E97 |
| 18 | `WriteConfirmEditCheck` | 0x2860E4 |
| 19 | `QuickLoadModeEditCheck` | 0x28615F |
| 20 | `LoadByNumberModeEditCheck` | 0x2861CE |
| 21 | `JumpAfterLoadModeEditCheck` | 0x28623D |
| 22 | `HdTitleEventCatch` | 0x283498 |
| 23 | `FlsNamingCheck` | 0x288041 |
| 24 | `FlsNamingCheck2` | 0x288169 |
| 25 | `CP_FD_DIRNAMECheck` | 0x28A07E |
| 26 | `WrConfirmEventCatch` | 0x28A1A7 |
| 27 | `SaveOptSwEventCatch` | 0x2855C3 |
| 28 | `DelOptSwEventCatch` | 0x28A497 |
| 29 | `DelOptNameCheck` | 0x28A617 |
| 30 | `DelLswEditCheck` | 0x28A69D |
| 31 | `DelPmtEditCheck` | 0x28A738 |
| 32 | `DelSqtEditCheck` | 0x28A7D3 |
| 33 | `DelCmpEditCheck` | 0x28A86E |
| 34 | `DelTmEditCheck` | 0x28A909 |
| 35 | `DelMspEditCheck` | 0x28A9A4 |
| 36 | `DelRcmEditCheck` | 0x28AA3F |
| 37 | `DelMdEditCheck` | 0x28AADA |
| 38 | `DelTlxEditCheck` | 0x28AB75 |
| 39 | `BitmapHdd_icon` | 0x280395 |
| 40 | `LBNPage1SwCatch` | 0x286B72 |
| 41 | `LBNLoadSwCatch` | 0x286CED |
| 42 | `FileLBNNameCheck` | 0x287559 |
| 43 | `LBNLswBitCheck` | 0x2875FB |
| 44 | `LBNPmtBitCheck` | 0x287705 |
| 45 | `LBNSqtBitCheck` | 0x28780F |
| 46 | `LBNCmpBitCheck` | 0x287919 |
| 47 | `LBNTmBitCheck` | 0x287A23 |
| 48 | `LBNMspBitCheck` | 0x287B2D |
| 49 | `LBNRcmBitCheck` | 0x287C37 |
| 50 | `LBNMdBitCheck` | 0x287D41 |
| 51 | `FlsFileLoadSwCatch` | 0x288C20 |
| 52 | `AttenDelDirSwCatch` | 0x283F7F |
| 53 | `AttenDelFileSwCatch` | 0x2840A3 |
| 54 | `AttenHDFormatSwCatch` | 0x286666 |
| 55 | `AttenCpToHDSwCatch` | 0x28317B |
| 56 | `AttenCpToMarkSwCatch` | 0x283237 |
| 57 | `FlsDel1SwCatch` | 0x288FED |
| 58 | `FlsDel2SwCatch` | 0x2890EA |
| 59 | `FlsOverWrSwCatch` | 0x28952E |
| 60 | `SeparateDrumPartCheck` | 0x285192 |
| 61 | `SeparateBassPartCheck` | 0x28523B |
| 62 | `ErrMsgTimerCatch` | 0x28B403 |
| 63 | `ErrMsgTimerCatchLBN` | 0x28B48F |
| 64 | `LanguageTextReturn` | 0x28F2F7 |
| 65 | `BitmapButt01` | 0x28B527 |
| 66 | `LyricJumpEditCheck` | 0x285F1C |
| 67 | `LyricForeColorCheck` | 0x285FE6 |
| 68 | `LyricBackColorCheck` | 0x286065 |

Two entries in this list are bitmap resource descriptors rather than ordinary callbacks: `BitmapHdd_icon` (0x280395) is the routine this site used to call `HDAE5000_Alloc_Memory_4`, and `BitmapButt01` (0x28B527) provides a 42×15 "STORE" button. Their firmware names are what proves those routines return a **bitmap base**, not a palette pointer — see [Embedded Graphics]({{ site.baseurl }}/hdae5000/#embedded-graphics-rewritten).

Three names in the registry used to disagree with the disassembly's labels for their targets (`HDAE5000_Alloc_Memory_4`, `HDAE5000_Dir_Event_Check`, `HDAE5000_HD_Format_Dispatch`). The source now carries the firmware's names: `HDAE5000_BitmapHdd_icon` (0x280395), `HDAE5000_LanguageTextReturn` (0x28F2F7) and `HDAE5000_SEL_DIR_Screen` (0x2837F2).

## Screens and their procedures

Registration IDs 0x014A (procedures) and 0x044A (names), PPI port 0x01600003, count `0x0E` = 14. Unlike the UI classes there is no ROM-side descriptor array for these — the name is the only handle.

| Screen name | Procedure |
|-------------|-----------|
| `HDAETitleFunc` | 0x283518 |
| `SEL_DIR_Screen` | 0x2837F2 |
| `FILE_LOAD_Screen` | 0x283DA0 |
| `FILE_Naming_Screen` | 0x28426A |
| `SetupP2SwCatch` | 0x286502 |
| `SelectFlsScreen` | 0x28866B |
| `FlsLoadScreen` | 0x288822 |
| `FlsEditScreen` | 0x288CEE |
| `FlsDirSelScreen` | 0x2891E7 |
| `FlsFileSelScreen` | 0x28935E |
| `CopyToHDScreen` | 0x289781 |
| `CopyToHDDirSelScreen` | 0x289D72 |
| `HDDTitleSwCatch` | 0x28310D |
| `FileLoadSwCatch` | 0x2841E5 |

The 14 name strings live at `0x2A849A`-`0x2A858D`, under the label `HDAE5000_GFX_INIT_PARAMS` — a misnomer inherited from the era when this whole region was believed to be graphics parameters. The block also carries a fifteenth string, `TT_HDDEXT`, which is loaded directly by an `lda` at `0x2802E4` rather than through the pointer table.

## UI classes and their parameters

Registration IDs 0x010A (procedures) and 0x040A (names), class id 0x01600001 (`FunctionProc`; not a "PPI port"), count `0x0D` = 13. The same 13 classes are described by `HDAE5000_RECORD_TABLE` at `0x29C0AA`: 13 **class definitions** of 24 bytes, in the main CPU's format (field names from the firmware's root class `Class`; see [UI Framework]({{ site.baseurl }}/ui-framework/#the-class-system-describes-itself)):

| Record field | Contents |
|--------------|----------|
| +0x00 `proc` | Class procedure pointer (repeats the `.data` table entry) |
| +0x04 `parent` | Parent class id: a root class such as `0x0160001D` `AcTitleMenu` |
| +0x08 `allsize` / +0x0A `selfsize` | Record size including inherited fields / bytes this class adds |
| +0x0C `name` | Pointer to the class name string |
| +0x10 `propdata` | Pointer to a per-parameter type-signature string |
| +0x14 `propname` | Pointer to that class's parameter-name list, in the RAM copy of the `.data` image |

Each class's parent and the size check are on [HDAE5000 Homebrew]({{ site.baseurl }}/hdae5000-homebrew/#data-record-table-handler-0x016a-the-modules-classes).

The signature at +0x10 is one character per parameter, and its length equals the parameter-name count for all 13 records — which is how the boundaries of the 36-slot parameter-name area at `0x2F96E2` were fixed.

| Class | Procedure | Parameters (in table order) |
|-------|-----------|------------------------------|
| `SelectListProc` | 0x2807D9 | font, fontcolor, main_func, str_adr, column, row, sel_num, dial, auto_inc, en_paradraw, sel_type |
| `DbMemoClProc` | 0x28122A | color, fontcolor |
| `TtlScreenRProc` | 0x280489 | *(none)* |
| `AcHddNamingWindowProc` | 0x281411 | *(none)* |
| `IvHddNamingProc` | 0x282681 | func |
| `HDTitleMenuProc` | 0x2827A8 | *(none)* |
| `TtlScreenR2Proc` | 0x280567 | *(none)* |
| `TtlScreenR3Proc` | 0x280645 | *(none)* |
| `AcWindowPage1Proc` | 0x28043C | *(none)* |
| `IvScreenR2Proc` | 0x280723 | *(none)* |
| `AcLanguageText1Proc` | 0x28B554 | *(none)* |
| `LyricBoxProc` | 0x28CD08 | pEnable, font, fontcolor, reversecolor, infofont, infocolor |
| `FDFileSelectProc` | 0x28E61B | dial, sel_num, sel_pos |

Each list is terminated by a pointer to an empty string, so the six parameterless classes still occupy one slot each.

> **Known source defect.** The `.include` boundary between `hdae5000_utilities.s` and `hdae5000_data_tables.s` sits at `0x29BFE0`, which is six bytes inside the string `en_paradraw` (it starts at `0x29BFDA`). The rebuild is unaffected — the bytes are contiguous either way — but `sel_type` (0x29BFD0) and `en_paradraw` are emitted from a different file than the ten parameter names that follow them. Moving the boundary is a queued cleanup.

## UI object table (0x2A5D2C)

Two more index-parallel arrays, each 790 `.long` entries, registered as object-set 0x007F (descriptors, PPI port 0x01600010) and 0x037F (names, port 0x0160000F). Both registrations pass the word `0x315`; that word is an **entry count** — 789 objects plus a terminator — not a byte size, and the earlier "size = 789 bytes" annotation has been retracted in six places.

Structure of the descriptor array at `0x2A5D2C`:

| Kind | Count | Range |
|------|------:|-------|
| Pointers into the ROM descriptor pool | 769 | 0x29DC12-0x2A5D2B, strictly ascending |
| Pointers into sub-CPU work RAM | 20 | 0x239CC4-0x239FAE — objects whose descriptor is built at run time |
| Terminator | 1 | `0x00000000` |

All 20 RAM-descriptor entries are soft-key or tab objects (`HddNamingABC` / `abc` / `Symbol`, `*_SW_EDIT`, `CP_FD_HDSW*`, `*_EXIT`, `*inLyric`).

The name array at `0x2A6984` points into the string pool at `0x2A75DC`. **178 of the 789 objects carry a name**; the other 611 point at an empty string. The pool is stored in *reverse* index order — the original toolchain emitted the literals in reverse order of declaration — so `HdaeUiName_789` is first in memory and `HdaeUiName_000` (`HDDMENU`) is last, ending exactly at `0x2A849A` where the screen-name block begins.

### Why the names can be trusted

The names are index-parallel with the descriptors, and 49 of the 178 named descriptors also contain a human-readable on-screen title. **Every one of those titles agrees with the name**, with no counter-example — including two nine-object families that enumerate the KN5000 data types under two different prefixes. The agreements are listed in full below (the "Screen title" column is populated wherever the descriptor contains a printable run of four characters or more).

### The 178 named UI objects

| Index | Name | Descriptor | Screen title |
|------:|------|------------|--------------|
| 0 | `HDDMENU` | 0x29DC12 | HD-AE5000 |
| 10 | `HARD_DISK_OPT` | 0x29DE14 |  |
| 19 | `SETUPS_TOOLS` | 0x29DF98 | SETUP & TOOLS |
| 24 | `SELECT_FILE` | 0x29E048 |  |
| 26 | `HD_FILE_LOAD` | 0x29E08E |  |
| 27 | `HD_LOAD_OPTION` | 0x29E0AA |  |
| 34 | `SELECT_DIR` | 0x29E198 | HD DIR SELECT |
| 37 | `SEL_DIR` | 0x29E214 |  |
| 44 | `SELECT_DIR_SW_EDIT` | RAM 0x239CC4 |  |
| 49 | `SELECT_DIR2` | 0x29E3FA | DIRECTORY SELECT |
| 58 | `FD_FILE_SELECT` | 0x29E586 | FD FILE SELECT |
| 69 | `HARD_TEST` | 0x29E77C | HARDWARE TEST |
| 73 | `RUN_STOP` | 0x29E802 | STOP |
| 75 | `PPORT_SW` | 0x29E84E | PPORT |
| 76 | `FD_SW` | 0x29E882 |  |
| 77 | `HDD_SW` | 0x29E8B2 |  |
| 78 | `HDD_FILE_NAMING` | 0x29E8E2 | EDIT FILE NAME |
| 87 | `HD_FILE_NAME` | 0x29EA36 |  |
| 88 | `HDD_DIR_NAMING` | 0x29EA5A | EDIT DIRECTORY NAME |
| 94 | `HD_PLEASE_WIN` | 0x29EB48 |  |
| 96 | `HD_UTIL` | 0x29EB9A | HD UTILITY |
| 102 | `PC_DATA_LINK` | 0x29EC8E | PC DATA LINK |
| 104 | `PP_STATUS` | 0x29ECE2 |  |
| 110 | `SETUP_TOOLS_P1` | 0x29EDDA |  |
| 122 | `SETUP_TOOLS_P2` | 0x29F076 |  |
| 128 | `SW_HD_FORMAT` | RAM 0x239CEC |  |
| 133 | `OUTPUT_SETTING` | 0x29F218 | OUTPUT SETTING |
| 143 | `LOAD_BY_NUM` | 0x29F3F2 | LOAD BY NUMBER |
| 149 | `LBN_P1` | 0x29F4BC |  |
| 152 | `LBN_OPTION` | 0x29F530 |  |
| 168 | `LBN_DIRNO_BOX` | 0x29F7BA |  |
| 169 | `LBN_DIRNAME_BOX` | 0x29F7F6 |  |
| 170 | `LBN_FILENO_BOX` | 0x29F832 |  |
| 171 | `LBN_FILENAME_BOX` | 0x29F86E |  |
| 175 | `LBN_P2` | 0x29F918 |  |
| 210 | `CP_FD` | 0x29FF8A | COPY TECH TO HD |
| 215 | `CP_FD_LIST` | 0x2A0058 |  |
| 216 | `CP_FD_LINE2` | 0x2A0094 |  |
| 217 | `CP_FD_LINE1` | 0x2A00AE |  |
| 218 | `CP_FD_HDSWTO` | RAM 0x239D22 |  |
| 220 | `CP_FD_HDSWSEL` | RAM 0x239D4A |  |
| 222 | `CP_FD_VOLLABEL` | 0x2A0116 |  |
| 224 | `CP_FD_HDALLSEL` | RAM 0x239D72 |  |
| 226 | `CP_FD_DIRSEL` | 0x2A01AA | HD DIR SELECT |
| 230 | `CP_FD_DIRBOX` | 0x2A024A |  |
| 240 | `FLS_SELECT` | 0x2A0414 | F.L.S. SELECT |
| 248 | `FLS_SEL` | 0x2A058E |  |
| 249 | `FLS_SELECT_SW_EDIT` | RAM 0x239D9A |  |
| 251 | `SEL_FLS` | 0x2A05DC |  |
| 255 | `HD_FILE_LOAD_P1` | 0x2A0678 |  |
| 256 | `HD_FILE_LOAD_SW_SAVE` | RAM 0x239DC2 |  |
| 258 | `HD_FILE_OPTION` | 0x2A06C2 |  |
| 259 | `HD_FILE_LIST` | 0x2A06FE |  |
| 260 | `FILE_LOAD_DIRBOX` | 0x2A073A |  |
| 266 | `HD_FILE_LOAD_SW_DEL` | RAM 0x239DEA |  |
| 269 | `HD_FILE_LOAD_SW_DELFILE` | RAM 0x239E12 |  |
| 272 | `HD_FILE_LOAD_P2` | 0x2A08CC |  |
| 308 | `HDD_FLS_NAMING` | 0x2A0F6C | EDIT FLS NAME |
| 314 | `FLS_FILE_LOAD` | 0x2A1054 | F.L.S. FILE LOAD |
| 318 | `FLS_FILE_LOAD_SW_EDIT` | RAM 0x239E62 |  |
| 323 | `FLS_OPT_BOX` | 0x2A1198 |  |
| 324 | `FLS_LOC_BOX` | 0x2A11D4 |  |
| 325 | `FLS_NAME_BOX` | 0x2A1210 |  |
| 328 | `FLS_FILE_BOX` | 0x2A12A0 |  |
| 329 | `FLS_LOAD_LINE1` | 0x2A12DC |  |
| 330 | `FLS_LOAD_LINE2` | 0x2A12F6 |  |
| 334 | `FLS_DIR_SEL` | 0x2A137A | F.L.S. DIR SELECT |
| 337 | `FLS_DIR_BOX` | 0x2A13F8 |  |
| 345 | `FLS_FILE_SEL` | 0x2A1574 | F.L.S. FILE SELECT |
| 347 | `FLS_FILE_SEL_DIRBOX` | 0x2A15CC |  |
| 348 | `FLS_FILE_SEL_LISTBOX` | 0x2A1608 |  |
| 352 | `FLS_FILE_SEL_OPTBOX` | 0x2A16BE |  |
| 355 | `FLS_EDIT` | 0x2A174A | F.L.S. EDIT |
| 358 | `FLS_EDIT_NAME_BOX` | 0x2A17C4 |  |
| 361 | `FLS_EDIT_LIST_BOX` | 0x2A1854 |  |
| 362 | `FLS_EDIT_LINE2` | 0x2A1890 |  |
| 363 | `FLS_EDIT_LINE1` | 0x2A18AA |  |
| 374 | `FLS_EDIT_LOC_BOX` | 0x2A1A82 |  |
| 375 | `FLS_EDIT_OPT_BOX` | 0x2A1ABE |  |
| 379 | `CP_FD_DIR_NAMING` | 0x2A1B48 | EDIT DIRECTORY NAME |
| 386 | `SAVE_OPT_SCREEN` | 0x2A1C5A | SAVE OPTION |
| 404 | `RAM_EDIT_CMP` | 0x2A1F16 | COMPOSER |
| 406 | `RAM_EDIT_LSW` | 0x2A1FA4 | CURRENT PANEL |
| 407 | `RAM_EDIT_PMT` | 0x2A1FF6 | PANEL MEMORY |
| 408 | `RAM_EDIT_SQT` | 0x2A2048 | SEQUENCER |
| 409 | `RAM_EDIT_TM` | 0x2A209A | SOUND MEMORY |
| 410 | `RAM_EDIT_MSP` | 0x2A20EC | MSP |
| 411 | `RAM_EDIT_RCM` | 0x2A213E | RHYTHM CUSTOM |
| 412 | `RAM_EDIT_MD` | 0x2A2190 | USER MIDI SETTINGS |
| 426 | `RAM_EDIT_TLX` | 0x2A23A2 | TECHNICS LYRICS |
| 430 | `HddNamingWindow` | 0x2A245C |  |
| 442 | `HddNamingCursorBox` | 0x2A262E |  |
| 443 | `HddNamingABC` | RAM 0x239E8A |  |
| 444 | `HddNamingabc` | RAM 0x239EB6 |  |
| 445 | `HddNamingSymbol` | RAM 0x239EE2 |  |
| 449 | `HddNamingLabel` | 0x2A26E6 |  |
| 450 | `FILE_DEL_SCREEN` | 0x2A270A | HD FILE DELETE |
| 463 | `DEL_EDIT_LSW` | 0x2A28D8 | CURRENT PANEL |
| 464 | `DEL_EDIT_PMT` | 0x2A2926 | PANEL MEMORY |
| 465 | `DEL_EDIT_SQT` | 0x2A2974 | SEQUENCER |
| 466 | `DEL_EDIT_CMP` | 0x2A29C2 | COMPOSER |
| 467 | `DEL_EDIT_TM` | 0x2A2A10 | SOUND MEMORY |
| 468 | `DEL_EDIT_MSP` | 0x2A2A5E | MSP |
| 469 | `DEL_EDIT_RCM` | 0x2A2AAC | RHYTHM CUSTOM |
| 470 | `DEL_EDIT_MD` | 0x2A2AFA | USER MIDI SETTINGS |
| 489 | `DEL_EDIT_TLX` | 0x2A2E18 | TECHNICS LYRICS |
| 492 | `HDD_ICON_DISPLAY` | 0x2A2E9A |  |
| 493 | `HD_MENU_BMP` | 0x2A2EBC |  |
| 494 | `IV_HDDMENU` | 0x2A2ED6 |  |
| 495 | `ATTEN_DEL_DIR` | 0x2A2EF8 |  |
| 504 | `WAIT_DEL_DIR` | 0x2A3070 |  |
| 507 | `ATTEN_DEL_FILE` | 0x2A3106 |  |
| 516 | `ATTEN_OVER_FLS` | 0x2A327E |  |
| 525 | `ATTEN_DEL_FLS2` | 0x2A33F6 |  |
| 535 | `WAIT_DEL_FILE` | 0x2A3598 |  |
| 538 | `ATTEN_HD_FORMAT` | 0x2A3610 | HD FORMAT |
| 546 | `HD_FORMAT_CATCH` | 0x2A376A |  |
| 547 | `WAIT_HD_FORMAT` | 0x2A3784 |  |
| 551 | `SETUP_HDINFO` | 0x2A3826 |  |
| 554 | `HD_INFO_LIST` | 0x2A389A |  |
| 556 | `DBG_MEMO_SCREEN` | 0x2A38F0 | DEBUG MEMO SCREEN |
| 559 | `ATTEN_DEL_FLS1` | 0x2A395C |  |
| 571 | `ATTEN_OVER_FILE` | 0x2A3B58 |  |
| 580 | `HDD_FLS_NAMING2` | 0x2A3CD0 | EDIT FLS NAME |
| 586 | `ATTEN_CPHD_WR` | 0x2A3DB8 |  |
| 594 | `ERR_HD_NOT_FMT` | 0x2A3F00 |  |
| 599 | `ERR_HD_SRAM` | 0x2A3FD4 |  |
| 604 | `ERR_HD_RESET` | 0x2A40A8 |  |
| 609 | `ERR_HD_READ` | 0x2A417C |  |
| 614 | `ERR_HD_ID_READ` | 0x2A4250 |  |
| 619 | `ERR_HD_TRACK_0` | 0x2A4324 |  |
| 624 | `ERR_HD_FAT` | 0x2A43F8 |  |
| 629 | `ERR_HD_FSB` | 0x2A44CC |  |
| 634 | `ATTEN_CPFD_MARK` | 0x2A45A0 |  |
| 641 | `ABOUT_HELP` | 0x2A46BE |  |
| 660 | `WAIT_TR0_RECOVER` | 0x2A4A34 |  |
| 663 | `ERR_SAVE` | 0x2A4AAC |  |
| 664 | `ERR_SAVE_EXIT` | RAM 0x239F0E |  |
| 665 | `ERR_SAVE_CATCH` | 0x2A4ACE |  |
| 669 | `ERR_LOAD` | 0x2A4B66 |  |
| 670 | `ERR_LOAD_EXIT` | RAM 0x239F28 |  |
| 671 | `ERR_LOAD_CATCH` | 0x2A4B88 |  |
| 675 | `ERR_NO_HK_DATA` | 0x2A4C20 |  |
| 677 | `ERR_NO_HK_DATA_CATCH` | 0x2A4C5C |  |
| 681 | `ATTEN_FULL_DIR` | 0x2A4CF4 |  |
| 683 | `ATTEN_FULL_DIR_CATCH` | 0x2A4D30 |  |
| 688 | `ATTEN_CP_UNNAMED` | 0x2A4DF2 |  |
| 690 | `ATTEN_CP_UNNAMED_CATCH` | 0x2A4E2E |  |
| 695 | `DIR_OUT_RANGE` | 0x2A4EF0 |  |
| 696 | `DIR_OUT_RANGE_CATCH` | 0x2A4F12 |  |
| 700 | `FILE_OUT_RANGE` | 0x2A4FAA |  |
| 701 | `FILE_OUT_RANGE_CATCH` | 0x2A4FCC |  |
| 705 | `HD_PLEASE` | 0x2A5064 |  |
| 708 | `ERR_HD_FORMAT` | 0x2A50DA |  |
| 710 | `ERR_HD_FORMAT_CATCH` | 0x2A5116 |  |
| 715 | `AGAIN_HD_FORMAT` | 0x2A51D8 |  |
| 717 | `AGAIN_HD_FORMAT_CATCH` | 0x2A5214 |  |
| 722 | `SELECT_FILE_A_Z` | 0x2A52D6 |  |
| 728 | `FILE_LOAD_A_Z` | 0x2A5392 |  |
| 752 | `Tech_lyrics` | 0x2A57DA | TECH LYRICS |
| 755 | `SongTitle` | 0x2A5854 |  |
| 757 | `Conductor` | 0x2A58A2 |  |
| 758 | `bottom01` | 0x2A58C6 |  |
| 759 | `bottom02` | 0x2A58EA |  |
| 760 | `bottom03` | 0x2A590E |  |
| 761 | `bottom04` | 0x2A5932 |  |
| 762 | `bottom05` | 0x2A5956 |  |
| 763 | `bottom06` | 0x2A597A |  |
| 764 | `bottom07` | 0x2A599E |  |
| 765 | `bottom08` | 0x2A59C2 |  |
| 767 | `ChordinLyric` | RAM 0x239F42 |  |
| 768 | `TempoinLyric` | RAM 0x239F66 |  |
| 769 | `MeasureinLyric` | RAM 0x239F8A |  |
| 770 | `TimeSigInLyric` | RAM 0x239FAE |  |
| 772 | `LoadLyricFD` | 0x2A5A3E | LOAD LYRICS FROM FD |
| 777 | `FD_PLEASE` | 0x2A5B02 |  |
| 780 | `LyrSettings` | 0x2A5B82 | LYRICS OPTIONS |
| 788 | `WriteIn` | 0x2A5D08 |  |

## The nine KN5000 data types, named by the firmware

Two of the object families above enumerate the same nine data-type suffixes and pair each with an on-screen title. `RAM_EDIT_*` (objects 404, 406-412, 426) is the save-selection screen; `DEL_EDIT_*` (objects 463-470, 489) is the delete-selection screen. The two families were written independently and agree suffix-for-suffix:

| Suffix | Firmware's on-screen title | Older guess on this site |
|--------|---------------------------|--------------------------|
| LSW | CURRENT PANEL | "(Unknown) — possibly Live Sound Workshop" |
| PMT | PANEL MEMORY | Performance Memory Track |
| SQT | SEQUENCER | Sequencer Track |
| CMP | COMPOSER | Composer |
| TM | SOUND MEMORY | "Technical MIDI" |
| MSP | MSP | Music Style Programmer |
| RCM | RHYTHM CUSTOM | Rhythm Composer Memory |
| MD | USER MIDI SETTINGS | "Melody — MIDI melody files" |
| TLX | TECHNICS LYRICS | "Technics Link — exchange files" |

The same suffixes appear again in the object registry as the `Sfx*BitCheck` and `Del*EditCheck` families (all nine, in the order LSW, PMT, SQT, CMP, TM, MSP, RCM, MD, TLX) and as `LBN*BitCheck` (the first eight — there is no LBN entry for TLX). The `Sfx` prefix reads naturally as *suffix* — one handler per file extension — which ties these tokens to the file extensions `.LSW`, `.PMT`, `.SQT`, `.CMP`, `.TM`, `.MSP`, `.RCM`, `.MD` and `.TLX` used by the directory code. Object 752 is separately named `Tech_lyrics` with the title "TECH LYRICS", which corroborates the TLX row.

Where the firmware's own title and this site's earlier expansion disagree, the title should be preferred: it is what the instrument shows the user. The [File Types table]({{ site.baseurl }}/hdae5000/#file-types) on the overview page still carries the older expansions and is flagged there.

## The initialised .data image (0x2F94B2)

3,202 bytes copied verbatim to RAM `0x23952A` by `HDAE5000_Clear_Work_Buffer` before anything else in `HDAE5000_Boot_Init` runs. Nine pointer tables, 96 code pointers and 166 string pointers, followed by the initial contents of the window/dialog state records and a handful of scalars.

| ROM | RAM | Entries | Registration | Contents |
|-----|-----|--------:|--------------|----------|
| 0x2F94B2 | 0x23952A | 69 | ID 0x012A | Object handler entry points |
| 0x2F95CA | 0x239642 | 69 | ID 0x042A | Object names |
| 0x2F96E2 | 0x23975A | 36 slots | via `RECORD_TABLE+0x14` | Per-class parameter names (23 names + 13 terminators) |
| 0x2F9772 | 0x2397EA | 13 | ID 0x01CA | `EV_*` event names |
| 0x2F97AC | 0x239824 | 18 | ID 0x01EA | `MT_*` message names |
| 0x2F97FA | 0x239872 | 13 | ID 0x010A | UI class procedures |
| 0x2F9832 | 0x2398AA | 13 | ID 0x040A | UI class names |
| 0x2F986A | 0x2398E2 | — | — | Window/dialog run-time state, initial values (from 0x2F9CA6 it becomes a 40-byte-stride geometry array) |
| 0x2F9F5A | 0x239FD2 | 14 | ID 0x014A | Screen procedures |
| 0x2F9F96 | 0x23A00E | 14 | ID 0x044A | Screen names |
| 0x2F9FD2 | 0x23A04A | — | — | File-format version, name edit buffers, browser state, directory slots |

The first two words of that last group are `0x0002` and `0x0006` — the "2.06" of the ROM's own version string "V2.06i". The disassembly traces their low bytes into a saved-file header (0x238FF6/0x238FF7), with the major compared against 0x2390F4 on load, so they are the file-format version the HD-AE5000 stamps on what it writes. They are followed by a 30-character column ruler (`"123456789012345678901234567890"`) and a 30-space name edit buffer.

The counts registered by `HDAE5000_Handler_Registration` (`0x45` = 69, `0x0D` = 13, `0x0E` = 14) are exactly the entry counts of these tables, which is how every boundary was fixed. Two of the registrations do not use an immediate at all: handler 0x01CA reads its count from RAM `0x239822` and handler 0x01EA from RAM `0x239870` — both of which are count words that live *inside this same image*.

### Why the image must be copied, not read in place

Four pointers inside the block are already resolved to RAM addresses within the copy — `0x23999A`, `0x239B84`, `0x239B86` and `0x239B88`, which are `0x23952A + 0x470 / 0x65A / 0x65C / 0x65E`. They are only meaningful once the image sits at `0x23952A`. The three 44-byte records that carry them are the naming-screen character-set selectors: each cites two identical copies of its caption ("ABC", "abc", "!#$") plus a pointer back into the RAM copy.

### The window state block

The block from `0x2F986A` is kept in the disassembly as annotated 16-bit words rather than invented variables, because no code in this ROM reads it through a named address. Three motifs repeat:

- `0xFFFF` — the "unset" sentinel used throughout this firmware
- `0x0001 0x0002 0x0000` triplets — per-window state enumerations
- 8-byte records `{u16 0x0000; u32 handle; u16 0xFFFF}` whose 32-bit field always lands in `0x006FB0F5`-`0x00709078`

Those 32-bit fields look like pointers but are **not** treated as such: nothing in this ROM references them, and the address window they fall in belongs to the main CPU's rhythm ROM. They are recorded as opaque handles patched at run time, which is a deliberately weaker claim than "pointers".

From `0x2F9CA6` the block becomes a 40-byte-stride record array whose second word is always `0x0160` (352) and whose remaining words are the coordinate magnitudes `0x0137`, `0x00F2` and `0x00D2` that also appear in the UI descriptors at `0x29DC14`.

## What is still open

| Item | Status |
|------|--------|
| UI object pool, 0x29DC12-0x2A5D2B (33,050 B, 769 records) | **Typed** (Wave 2, `scripts/generators/gen_hdae5000_ui_pool.py`): each record's class id, links, attribute word and box. 13,334 B of class-specific body is still undecoded; the main CPU's class layouts cover it. The five old labels inside it are kept as `.set` aliases |
| Sixth palette/bitmap pair, 0x2E3064 / 0x2E3464 | Labelled: `HDAE5000_Palette_Button01` / `HDAE5000_Bitmap_Button01`. No code in this ROM reads the palette |
| `HDAE5000_Icon.bin` | 784 bytes, but the icon is 756 (27×27 with a 28-byte stride). The extra 28 bytes are the first bytes of the C program's `.rodata` — literally the ASCII "V2.06i" (`HDAE5000_Str_V206i`) |
| Gallery renders for Logo / Hands / FilePanel | `convert_images.py` gives all HD-AE5000 images the boot-splash palette; each bitmap actually has its own palette immediately above it in ROM |
| `en_paradraw` include boundary | Split across two source files at 0x29BFE0 |

## Related Documentation

- [HDAE5000 Hard Disk Expansion]({{ site.baseurl }}/hdae5000/) - Overview, ROM layout, graphics
- [HDAE5000 Filesystem]({{ site.baseurl }}/hdae5000-filesystem/) - disk layout, song records, lyric files
- [HDAE5000 Homebrew Development]({{ site.baseurl }}/hdae5000-homebrew/) - The main CPU's object dispatch system
- [Image Gallery]({{ site.baseurl }}/image-gallery/#hdae5000-hard-disk-expansion-rom-images) - The extracted bitmaps
- [UI Widget Types]({{ site.baseurl }}/ui-widget-types/) - The main firmware's equivalent widget vocabulary
