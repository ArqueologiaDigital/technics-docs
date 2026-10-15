---
layout: page
title: UI Widget Types (NAKA System)
permalink: /ui-widget-types/
---

# UI Widget Types (NAKA System)

The KN5000 firmware uses a widget object system (internally referred to as "NAKA") for structured UI elements. The **NAKA_UIObjectTable** at ROM address `0xE1344E` contains 478 `.long` pointers to widget structures, registered by `InitializeNaka` (`0xF165EB`) with handler `ViewableProc` at `0xFA5995`. In all, the 211 Viewable tables the firmware registers hold 3,365 widget records in v10, these 478 among them. An older byte-pattern scan, kept in the inventory below, found 1,413 records with 10 distinct type bytes.

> **Superseded model.** In September 2026 the firmware's own class definitions
> were decoded (lanes nakabig and nakarest; see
> [UI Framework — The class system describes itself]({{ site.baseurl }}/ui-framework/#the-class-system-describes-itself)).
> The "type byte" on this page is the index of the record's **class** in the
> root module's Class table. The "header" is the record's class id. The class
> definitions name every field. The sections below keep the older field-analysis
> names beside the firmware's names.

## Widget Structure Header

Every widget record starts with its **class id**, a 32-bit little-endian value:

```
Byte 0: class index (the "type byte" of older notes)
Byte 1: high byte of the class index (0x00 in every record seen)
Byte 2: low byte of the Class-table index (0x60 = root module, 0x61-0x68 = other modules)
Byte 3: 0x01
```

For the root module the value is `0x01600000 | index`: entry *index* of the
Class table at object-table index 0x160. 2,894 of the 3,365 v10 records use a
root class. The rest use classes of modules 1-8 (`0x0161KKKK`-`0x0168KKKK`);
`tools/naka_record_class_tables.py` in this repository counts them per table.

## Type Byte Inventory

The class names in the second column are the firmware's own, read from the root
Class table (`python3 scripts/analysis/nakarest_objtab_map.py v10 --classes`).
The counts and characteristics are the older field analysis.

| Type Byte | Count | Class (firmware name) | Key Characteristics                                                                                                      |
|-----------|-------|-----------------------|--------------------------------------------------------------------------------------------------------------------------|
| `0x16`    | 3     | `PsNumEditBox`        | FD SAVE/LOAD TEST only, counter display with label string                                                                |
| `0x1e`    | 31    | `PsEditSwBox`         | 4 sub-widget indices, full-screen bounding box                                                                           |
| `0x2b`    | 765   | `Label`               | String pointer (e.g. "200 Preset"), bounding box                                                                         |
| `0x2e`    | 148   | `Line`                | Fixed 26 bytes, bounding box, no string pointer                                                                          |
| `0x2f`    | 18    | `Frame`               | Similar to 0x2e but with different flags                                                                                 |
| `0x30`    | 16    | `EditSw`              | Range parameters (min/max), data pointer                                                                                 |
| `0x31`    | 120   | `Box`                 | Links to child indices, bounding box, 22-26 bytes                                                                        |
| `0x34`    | 196   | `TtlScreen`           | Defines screen bounds, string pointer, 42-44 bytes                                                                       |
| `0x66`    | 110   | `AcLanguageText`      | Dual coordinate sets, count fields, 38-42 bytes                                                                          |
| `0x6c`    | 6     | `VwUserBitmapByName`  | Feature Demo slides only (children of six `ftdemoNN` screens in Viewable slot 0xFD), 8-byte keys `"FTBMP01"`–`"FTBMP06"` |

The tentative names this table used to carry (Diagnostic List, Panel/Dialog,
Label/Button, Value Display, Option/Choice, Slider/Range, Composite/Group,
Container/Frame, List/Selector, Bitmap/Image) came from field analysis. The
class names replace them.

## Common Structure Layout

Every widget class descends from `Viewable`, so every record starts with
`Viewable`'s 22 bytes. The names are the firmware's (`propname` of class
`Viewable`); the meanings were established independently by the ext lane
(`scripts/analysis/ext_lane_checks.py widgets` / `test1`):

```
Offset  Size   Field    Meaning
------  ----   -----    -------
 0      4      class    class id (the "type byte" header)
 4      2      super    element index of the PARENT            (0xFFFF = none)
 6      2      sub      element index of the FIRST CHILD       (0xFFFF = none)
 8      2      next     element index of the NEXT SIBLING       (0xFFFF = none)
10      2      prev     element index of the PREVIOUS SIBLING   (0xFFFF = none)
12      2      flag     (0x08 in most records, 0x0A in TtlScreen records)
14      8      rect     x1, y1, x2, y2: screen rectangle inside the parent's
22+     ...    the fields each subclass adds, in class-chain order
```

The indices are elements of the same Viewable table the record is registered
in (for NAKA's own screens, `NAKA_UIObjectTable`). The older reading here, one
"primary parent/group index" followed by three "related" indices, and the
`naka_type_0x48_t` member names `parent_idx` / `prev_sibling` / `self_idx` /
`next_sibling` in `naka_types.h`, are superseded. The "screen group / widget
index" comments some sources still carry are also wrong.

## Dispatch Mechanism

Widget dispatch is by class procedure:

### ViewableProc (Event Dispatch)

`ViewableProc` at `0xFA5995` is the primary event handler registered via the `RegObjTabl` macro in `InitializeNaka`. It dispatches on 32-bit event IDs (not on the 8-bit widget type byte):

| Event ID    | Firmware method (constant)                | Handler label          |
|-------------|-------------------------------------------|------------------------|
| `0x1E00052` | MT_SetEditSwRect (`EVT_SET_EDIT_SW_RECT`) | `Viewable_GetBoundsY`  |
| `0x1E0004F` | MT_SetMenuRect (`EVT_SET_MENU_RECT`)      | `Viewable_GetBoundsX`  |
| `0x1E000B5` | MT_SearchLink (`EVT_SEARCH_LINK`)         | `Viewable_MatchClass`  |
| `0x1E00024` | MT_SearchClass (`EVT_SEARCH_CLASS`)       | `Viewable_Dispatch`    |
| `0x1E0009C` | MT_SetVisible (`EVT_SET_VISIBLE`)         | `Viewable_SetVisible`  |
| `0x1E00039` | MT_GetPrevview (`EVT_GET_PREVVIEW`)       | `Viewable_GetClass`    |
| `0x1E00038` | MT_GetNextview (`EVT_GET_NEXTVIEW`)       | `Viewable_GetChild`    |
| `0x1E00037` | MT_GetSubview (`EVT_GET_SUBVIEW`)         | `Viewable_GetOwner`    |
| `0x1E00036` | MT_GetSuperview (`EVT_GET_SUPERVIEW`)     | `Viewable_GetParent`   |
| `0x1E0000F` | MT_GetInstance (`EVT_GET_INSTANCE`)       | `Viewable_GetInstance` |

These are firmware methods (the `0x01E0` `MT_*` space), not lifecycle events, and they are only the first ten tests. `ViewableProc` also handles `EVT_SET_NAME`, `EVT_GET_NAME`, `EVT_DELIVERY_EVENT`, `EVT_SHOW`, `EVT_HIDE` and `EVT_GET_CLASS_SP`, and dispatches `EVT_PAINT` (`0x1C0000B`) through `0x1C00011` through `ViewableProc_CaseTable` (`ViewableProc_OnPaint`, `ViewableProc_OnRepaint`, ...). Several handler labels predate the method names and do not describe the handler (`Viewable_GetClass` answers MT_GetPrevview).

### Not part of widget dispatch: `SeMenu_SetObjectFlags`

Older notes made `SeMenu_SetObjectFlags` (`0xF06898`) a second, type-byte level of widget dispatch. It is not. Its only callers are `SeMenu_RegisterElement_Extended` and `SeMenu_RegisterElement_Type1` in `audio/semenu_routines.s`. It sets flag bits in a sound-editor display element according to an element code (0–4, 0x11–0x14, 0x21–0x24, 0x31–0x34, 0x41–0x44), and returns without action for any other value. NAKA records are dispatched by their class's procedure through `SendEvent`.

## InitializeNaka Registration

`InitializeNaka` (ROM `0xF165EB`) registers eleven object tables, verbatim from
`v10/maincpu/storage/flash_floppy_handlers.s`:

```asm
InitializeNaka:
	lda xsp, (xsp - 14)

	RegObjTable NAKA_CLASS_Class, ClassProc, Naka_ClassCount_16B, ToneGen_ParamTable_0x53D, 0x16b
	RegObjTable NAKA_CLASS_ResEvent, ResEventProc, Naka_ResEventCount_1CB, ToneGen_ParamTable_0x557, 0x1cb
	RegObjTable NAKA_CLASS_ResMethod, ResMethodProc, Naka_ResMethodCount_1EB, ToneGen_ParamTable_0x55D, 0x1eb
	RegObjTabl NAKA_CLASS_ApFunction, ApFunctionProc, 0x12, Naka_ApFuncTable_12B, 0x12b
	RegObjTabl NAKA_CLASS_ApFunction, ApFunctionProc, 0x12, Naka_ApFuncNameTable_42B, 0x42b
	RegObjTabl NAKA_CLASS_Function, FunctionProc, 0x0, ToneGen_ParamTable_0x563, 0x10b
	RegObjTabl NAKA_CLASS_Function, FunctionProc, 0x0, ToneGen_ParamTable_0x567, 0x40b
	RegObjTabl NAKA_CLASS_MainFunction, MainFunctionProc, 0x0, Naka_MainFunctionTable_14B, 0x14b
	RegObjTabl NAKA_CLASS_MainFunction, MainFunctionProc, 0x0, Naka_MainFunctionTable_44B, 0x44b
	RegObjTabl NAKA_CLASS_Viewable, ViewableProc, 0x1de, NAKA_UIObjectTable, 0xfd
	RegObjTabl NAKA_CLASS_ResName, ResNameProc, 0x1de, Naka_ResNameTable_3FD, 0x3fd

	RegTitle 0xb, InitializeNaka_Str_TT_FDMSP, 0xfd, NAKA_APFUNC_DefaultFunction, NAKA_VIEW_ftdemo01
	lda xsp, (xsp + 14)
	ret
```

The `ViewableProc` handler (`0xFA5995`) is associated with class id `NAKA_CLASS_Viewable` (`0x1600010`) and a count of `0x1DE` (478 decimal) entries in `NAKA_UIObjectTable` — that third argument is where the 478 comes from.

`InitializeNaka` is one of the thirty-two initialisers (eleven named modules, twenty
`InitializeUser12`–`InitializeUser31` slots and `InitializeRoot`) called from `InitializeObjectTable`
(`0xFA40B3`); the full sequence is on
[Architecture Flowchart]({{ site.baseurl }}/firmware-flowchart/#subsystem-registration).

## Source Location

The main-CPU sources are split per subsystem under `v10/maincpu/`; a routine's file is not
predictable from its purpose, because the split follows ROM address ranges.

| Item | Location |
|------|----------|
| NAKA_UIObjectTable (`0xE1344E`) | `v10/maincpu/ui_widgets/performance_style_screens.s` — a label at offset `0x4ADA` inside the descriptor blob |
| InitializeNaka (`0xF165EB`) | `v10/maincpu/storage/flash_floppy_handlers.s` |
| ViewableProc (`0xFA5995`) | `v10/maincpu/ui/ui_widget_defs.s` |
| SeMenu_SetObjectFlags (`0xF06898`) | `v10/maincpu/audio/semenu_routines.s` |
| Type constants | `v10/maincpu/shared/macros.s` |

## Assembly Macros

The disassembly uses EQU constants for type bytes and a `naka_header` macro for the common 4-byte header:

```asm
; Usage in the disassembly source:
    naka_header NAKA_TYPE_LABEL        ; emits: .byte 0x2b, 0x00, 0x60, 0x01
    .byte 0x1a, 0x00, 0xff, 0xff, ...  ; type-specific body fields
```

## C Struct Conversion (Complete)

All 26 NAKA widget data blocks have been converted from raw `.byte` assembly directives to **typed C struct initializers** with named fields, readable string literals, and symbolic pointer references. The conversion uses packed C structs compiled by the LLVM TLCS-900 backend, linked against symbol addresses from the main ELF, producing byte-identical ROM binaries.

### Available Struct Types (naka_types.h)

| Type Code | C Struct | Fixed Size | Trailing String |
|-----------|----------|------------|-----------------|
| `0x34` | `naka_container_t` | 42 bytes | Yes (title text) |
| `0x1D` | `naka_menu_item_t` | 54 bytes | Yes (button text) |
| `0x2B` | `naka_label_t` | 32 bytes | Yes (display text) |
| `0x30` | `naka_slider_t` | 44 bytes | No |
| `0x31` | `naka_group_t` | 26 bytes | No |
| `0x48` | `naka_type_0x48_t` | 26 bytes | No |
| Dispatch types | `naka_dispatch_t` | 24 bytes | No |

**Dispatch types** (0x00, 0x10, 0x12, 0x15, 0x20, 0x21, 0x22, 0x26, 0x27, 0x33, 0x40, 0x44, 0x45, 0x47, 0x54, and others) all share a compact 24-byte layout: 4-byte header + `field_04` (uint16) + `field_06` (uint16) + `name_ptr` + `inst_ptr` + `link_ptr` + `proc_addr` (four uint32 pointers).

> **These are not widgets.** A `naka_dispatch_t` is a 24-byte **class
> definition** read 4 bytes late. Its "header" is the class's `parent` id,
> `field_04`/`field_06` are `allsize`/`selfsize`, `name_ptr` is `name`,
> `inst_ptr` is `propdata` (the type letters) and `link_ptr` is `propname`.
> `proc_addr` is the `proc` of the **next** class definition. The nakarest lane
> retyped 151 whole class definitions (plus one split record) as
> `naka_classdef_t {proc, parent, allsize, selfsize, name, propdata, propname}`.
> The 27 class definitions in `naka_master_style.c` are still untyped. See
> [UI Framework — The class system describes itself]({{ site.baseurl }}/ui-framework/#the-class-system-describes-itself).

### Pointer Resolution Macros

| Macro | Purpose |
|-------|---------|
| `NAKA_HDR(type)` | 4-byte widget header initializer |
| `NAKA_ADDR(symbol)` | External ROM address (resolved by linker) |
| `SELF(field)` | Self-referential pointer within same data block |
| `ALIGNED_STRING(s)` | NUL-terminated string with 0xFF pad to even boundary |

### handler_table Field (CONTAINER / MENU_ITEM)

> **Superseded.** The class definitions name these fields. In a CONTAINER
> (class `TtlScreen`, 0x34) offset +30 is `window`, a field inherited from
> `Screen` (`Screen` adds `exit` at +26 and `window` at +30). In a MENU_ITEM
> (class `AcTitleMenu`, 0x1D) offset +38 is `selected`, inherited from
> `PsMenuBox`. Both have 4-byte type letters (`r` and `m`). The +2 step from
> one menu item to the next fits `selected` pointing at consecutive 16-bit RAM
> cells. The values seen, 0x0003F434 and up, fall inside the work-RAM image that
> `Boot_InitWorkRAM` copies to 0x3D524-0x3F6C1 at boot (see
> [Memory Map — Work-RAM image]({{ site.baseurl }}/memory-map/#work-ram-initial-image)).
> Each is the widget's own value cell: every mutable widget property holds the
> RAM address of a cell of its own (see
> [UI Framework — Where a widget's live values are kept]({{ site.baseurl }}/ui-framework/#where-a-widgets-live-values-are-kept-2026-10-06)).
> Nobody has yet traced how `InheritedProc` uses them. The earlier reading
> follows, kept for its evidence.

The `handler_table` field (offset +30 in CONTAINER, +38 in MENU_ITEM) is **not a function pointer** — it is a DRAM address pointing to an **event handler dispatch table**. The firmware's `InheritedProc` function:

1. Loads the widget's object record from the DRAM object table at `0x27ED2`
2. Extracts the handler dispatch table address from offset +10 of the record
3. Indexes into the table by event code to find the actual handler function
4. Calls the handler via indirect `call (xhl)`

Evidence: handler_table values increment by 2 per consecutive menu item (e.g., `0x0003F434`, `0x0003F436`, `0x0003F438`...) and fall in the `0x0003xxxx` address range (unmapped by ROM — written to DRAM at runtime). In contrast, dispatch widget `proc_addr` values resolve to actual ROM function symbols like `IvDrawbarProc`.

### Conversion Script

`scripts/converters/naka_struct_decode.py` performs automated conversion:
1. Reads ROM bytes at the block's base address
2. Forward-scans for NAKA headers, strings, pointer tables, padding
3. Resolves pointers via ELF symbol table (36,849 symbols)
4. Generates C struct + linker script with `_Static_assert` size verification
5. All 23 auto-generated files verified byte-perfect

### Source Files

| File                                       | Contents                                               |
|--------------------------------------------|--------------------------------------------------------|
| `v10/maincpu/ui_widgets/naka_types.h`      | Packed struct definitions and macros                   |
| `v10/maincpu/ui_widgets/*.c`               | 26 C data files (3 hand-crafted, 23 auto-generated)    |
| `v10/maincpu/ui_widgets/*_link.ld`         | Linker scripts for extern symbol resolution            |
| `scripts/converters/naka_struct_decode.py` | Automated conversion tool                              |
| `scripts/converters/naka_to_c.py`          | Original conversion tool (used for hand-crafted files) |

---

## FD SAVE/LOAD TEST — Diagnostic Screen

The FD SAVE/LOAD TEST is a factory diagnostic screen that exercises the floppy disk I/O subsystem. It is the only user of class 0x16, `PsNumEditBox` (`NAKA_TYPE_DIAGLIST` in the sources), and provides a complete example of the Title-based screen activation system.

### Activation Path

The diagnostic screen is part of the **HAMA** (file/disk) subsystem, initialized at boot by `InitializeHama` (ROM `0xF1E146`):

1. **Boot registration.** `InitializeHama` calls `RegisterTitle` twice to register two titles with the firmware's title management system:

   | Title string | Address    | Title  | Purpose                                                                            |
   |--------------|------------|--------|------------------------------------------------------------------------------------|
   | `TT_HDDEXT`  | `0xE1FD18` | `0x7F` | The hard-disk title: the HD-AE5000 re-registers it with its own view and procedure |
   | `TT_EXTAPR`  | `0xE1FD22` | `0xFC` | FD SAVE/LOAD TEST, the service manual's Test 8                                     |

   Both titles share the same lifecycle callback, `TestTitleFunc` at `0xF1E39A` (pointer stored at `0xE1FD2C` in `fd_test_data.s`), and the same view, `NAKA_VIEW_FDD_TEST` (`0x00FC0000`, entry 0 of Viewable table 0xFC). The Viewable table `InitializeHama` registers at 0x7F is empty.

2. **Title activation.** The 0xFC title (`TT_EXTAPR`) is the service manual's Test 8: holding B3 + B4 at power-on makes `SelfTest_FirmwareVersionCheck` request title `0x01A000FC` (see [Test Modes]({{ site.baseurl }}/test-modes/#test-8-floppy-disk-saveload-test-b3--b4)). Title 0x7F is the HD-AE5000's hard-disk title: the DISK MENU's "HARD DISK MAIN MENU" item points at it, and the HD-AE5000 re-registers it with its own view and requests it at boot with `EVT_INTERRUPT_TITLE`, depending on `HDAE5000_Check_HD_Present`'s result (see [HDAE5000 Homebrew]({{ site.baseurl }}/hdae5000-homebrew/#disk-menu-slot-registration-workspace0x0e0a0x02c4)). The title system sends `EVT_ACTIVATE_STATE` (`0x1C00013`) to `TestTitleFunc`, and phases 2-7 each print one line through `FDTest_PrintDiag` (`TestTitleFunc_CaseTable`, `0xE1FE0E`):

   | Event       | Parameter (xde) | Prints                  |
   |-------------|-----------------|-------------------------|
   | `0x1C00013` | 2               | `Title new`             |
   | `0x1C00013` | 3               | `Title old`             |
   | `0x1C00013` | 4               | `Title Inactivate`      |
   | `0x1C00013` | 5               | `Title Activate`        |
   | `0x1C00013` | 6               | `Title INTERUPT`        |
   | `0x1C00013` | 7               | `Title INTERUPT RETURN` |

3. **User actions.** Panel switches arrive as `EVT_SW_IN` (`0x1C00007`, parameter = switch number), dispatched through `TitleFunc_LifecycleDispatch_CaseTable` (`0xE1FDFE`):

   | Switch (xde) | Prints                | Action                                                                                 |
   |--------------|-----------------------|----------------------------------------------------------------------------------------|
   | 0            | `TBIOS Test`          | `FDTest_ProbeDiskFormat`                                                               |
   | 1            | `STOP FDD TEST`       | kills the test-loop timer                                                              |
   | 2            | `START FDD TEST LOOP` | one `FDLoadSaveTest` pass (`RunTestCounters_Entry`), then a timer posts switch 2 again |
   | 3            | `DIR`                 | `FDListDirectory`                                                                      |
   | 4            | `Debug Test`          | `format_FD` with WA = 2, then volume label `TEST_HAMA` (`RegHamaTitle1_Entry`)         |
   | 5            | `Debug Test`          | `format_FD` with WA = 3, then volume label `TESTHAMA2HD` (`RegHamaTitle2_Entry`)       |
   | 6            | —                     | lists `A:\HAMA\*.LSW` (`ListDir2_Entry`)                                               |

4. **Dialog widget events.** `FDTestDialogProc` answers `EVT_REQUEST_GRID_DRAW` (`0x1E0008D`) by sending `EVT_GRID_DRAW` for the requested cell, with the text `File Name 20 charact`, to the focus object. Through a word-offset table at `0xE1FF34` (`FDTestDialogProc_CaseTable`) it swallows the index-switch and dial events `0x1C00017`--`0x1C0001D` (`EVT_INDEXSW_UP` … `EVT_RAM_DATA`), returning 0. Every other event also returns 0.

5. **File selection.** `HamaListProc`, the procedure of Hama's one class `HamaList` (a subclass of `AcListBox`), handles `EVT_SET_STRING` (`0x1E00086`, MT_SetString) by copying the given string into the buffer that the widget's `list` field (+42) points at, and forwards every other event to `InheritedProc`.

### Screen Layout

The diagnostic screen uses 3 `PsNumEditBox` (class 0x16) widgets displaying live counters:

| Widget | Address | Label | Purpose |
|--------|---------|-------|---------|
| 1 | `0xE1F794` | `" TOTAL :"` | Total test iterations |
| 2 | `0xE1F7D2` | `"    NG :"` | Failed iterations |
| 3 | `0xE1F810` | `"    OK :"` | Passed iterations |

The test writes a 2KB counting pattern (`0x0000`--`0x03FF`) to `A:IMMUNITY.TST`, reads it back, and compares byte-by-byte. Directory listing uses the pattern `A:\HAMA\*.LSW`.

### Source Files

| File                                      | Contents                                                                |
|-------------------------------------------|-------------------------------------------------------------------------|
| `v10/maincpu/factory_test/fd_test_code.s` | `FDLoadSaveTest`, `FDListDirectory`, `FDTestDialogProc`, `HamaListProc` |
| `v10/maincpu/factory_test/fd_test_data.s` | DIAGLIST widgets, NAKA structures, pointer tables, diagnostic strings   |
| `v10/maincpu/factory_test/test_init.s`    | `InitializeHama`, `TestTitleFunc`, `FDTest_PrintDiag`                   |

### Standard Library Functions

Analysis of the FD test code identified several standard library functions used throughout the firmware:

| Address    | Name              | v10 call sites | Description                                            |
|------------|-------------------|----------------|--------------------------------------------------------|
| `0xFF0E80` | `Malloc`          | 107            | Heap allocator (size on stack, returns pointer in xhl) |
| `0xFF0AF2` | `Free`            | 85             | Heap deallocator (pointer on stack)                    |
| `0xFF0FFA` | `Memset`          | 46             | Memory fill (buffer, byte, count on stack)             |
| `0xFF0F4D` | `Strcpy`          | 421            | String copy with null termination                      |
| `0xF4EB97` | `FileOpen`        | 20             | Open file (mode flags: r/w/a/b/+/~/d)                  |
| `0xF4EEB9` | `FileWrite`       | 3              | Write to file (handle, buffer, size)                   |
| `0xF4EE70` | `FileRead`        | 11             | Read from file (handle, buffer, size)                  |
| `0xF4F05A` | `FileClose`       | 25             | Close file handle                                      |
| `0xF4F21F` | `FileOpenDefault` | 3              | Open file with default flags                           |

---

## Related Pages

- [UI Framework]({{ site.baseurl }}/ui-framework/) -- Widget system and event handling
- [Feature Demo & Presentation System]({{ site.baseurl }}/feature-demo/) -- SSF presentation that uses NAKA widgets
