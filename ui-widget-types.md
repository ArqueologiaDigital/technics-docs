---
layout: page
title: UI Widget Types (NAKA System)
permalink: /ui-widget-types/
---

# UI Widget Types (NAKA System)

The KN5000 firmware uses a widget object system (internally referred to as "NAKA") for structured UI elements. The **NAKA_UIObjectTable** at ROM address `0xE1344E` contains 478 `.long` pointers to widget structures, registered by `InitializeNaka` (`0xF165EB`) with handler `ViewableProc` at `0xFA5995`. Beyond this table, there are approximately **1,410 total widget structures** across the entire Program ROM using 9 distinct type bytes.

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
Class table at object-table index 0x160. 2,869 of the 3,340 v10 records use a
root class. The rest use classes of modules 1-8 (`0x0161KKKK`-`0x0168KKKK`).

## Type Byte Inventory

The class names in the second column are the firmware's own, read from the root
Class table (`python3 scripts/analysis/nakarest_objtab_map.py v10 --classes`).
The counts and characteristics are the older field analysis.

| Type Byte | Count | Class (firmware name) | Key Characteristics |
|-----------|-------|----------------|---------------------|
| `0x16` | 3 | `PsNumEditBox` | FD SAVE/LOAD TEST only, counter display with label string |
| `0x1e` | 31 | `PsEditSwBox` | 4 sub-widget indices, full-screen bounding box |
| `0x2b` | 765 | `Label` | String pointer (e.g. "200 Preset"), bounding box |
| `0x2e` | 148 | `Line` | Fixed 26 bytes, bounding box, no string pointer |
| `0x2f` | 18 | `Frame` | Similar to 0x2e but with different flags |
| `0x30` | 16 | `EditSw` | Range parameters (min/max), data pointer |
| `0x31` | 120 | `Box` | Links to child indices, bounding box, 22-26 bytes |
| `0x34` | 196 | `TtlScreen` | Defines screen bounds, string pointer, 42-44 bytes |
| `0x66` | 110 | `AcLanguageText` | Dual coordinate sets, count fields, 38-42 bytes |
| `0x6c` | 6 | `VwUserBitmapByName` | FTDEMO_SCREEN only, references FTBMPXX strings |

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

Widget dispatch uses a two-level architecture:

### Level 1: ViewableProc (Event Dispatch)

`ViewableProc` at `0xFA5995` is the primary event handler registered via the `RegObjTabl` macro in `InitializeNaka`. It dispatches on 32-bit event IDs (not on the 8-bit widget type byte):

| Event ID | Handler |
|----------|---------|
| `0x1E00052` | Viewable_GetBoundsY |
| `0x1E0004F` | Viewable_GetBoundsX |
| `0x1E000B5` | Viewable_MatchClass |
| `0x1E00024` | Viewable_Dispatch |
| `0x1E0009C` | Viewable_SetVisible |
| `0x1E00039` | Viewable_GetClass |
| `0x1E00038` | Viewable_GetChild |
| `0x1E00037` | Viewable_GetOwner |
| `0x1E00036` | Viewable_GetParent |
| `0x1E0000F` | Viewable_GetInstance |

These event IDs correspond to widget lifecycle events (creation, property changes, visibility, rendering) rather than widget type identifiers.

### Level 2: Type Byte Classifier (SeMenu_SetObjectFlags)

`SeMenu_SetObjectFlags` classifies the 8-bit type byte into rendering priority groups using a cascading comparison:

| Type Byte Range | Group | Priority |
|-----------------|-------|----------|
| `0x41`-`0x44` | 4 | Highest |
| `0x31`-`0x34` | 3 | High |
| `0x21`-`0x24` | 2 | Medium |
| `0x11`-`0x14` | 1 | Low |
| Lower values | Bit-based | Varies |

Types `0x31` and `0x34` fall directly into group 3. Types `0x2b`, `0x2e`, `0x66`, and `0x6c` fall into the bit-based classification path (lower nibble checks).

## InitializeNaka Registration

`InitializeNaka` (ROM `0xF165EB`) registers eleven object tables, verbatim from
`v10/maincpu/storage/flash_floppy_handlers.s`:

```asm
InitializeNaka:
	lda xsp, (xsp - 14)

	RegObjTable 0x1600004, 0xfa44e2, 0xe0e95c, 0xe0e944, 0x16b
	RegObjTable 0x160000c, 0xfa58fb, 0xe0e962, 0xe0e95e, 0x1cb
	RegObjTable 0x160000d, 0xfa5948, 0xe0e968, 0xe0e964, 0x1eb
	RegObjTabl 0x1600002, 0xfa496c, 0x12, 0xe0e7ae, 0x12b
	RegObjTabl 0x1600002, 0xfa496c, 0x12, 0xe0e7fa, 0x42b
	RegObjTabl 0x1600001, 0xfa48a9, 0x0, 0xe0e96a, 0x10b
	RegObjTabl 0x1600001, 0xfa48a9, 0x0, 0xe0e96e, 0x40b
	RegObjTabl 0x1600003, 0xfa4a18, 0x0, 0xe14824, 0x14b
	RegObjTabl 0x1600003, 0xfa4a18, 0x0, 0xe14828, 0x44b
	RegObjTabl 0x1600010, 0xfa5995, 0x1de, NAKA_UIObjectTable, 0xfd
	RegObjTabl 0x160000f, 0xfa62cb, 0x1de, 0xe13bca, 0x3fd

	RegTitle 0xb, 0xe1, 0x481a, 0xfd, 0x1200000, 0xfd0000
	lda xsp, (xsp + 14)
	ret
```

The `ViewableProc` handler (`0xFA5995`) is associated with type ID `0x1600010` and a count of `0x1DE` (478 decimal) entries in `NAKA_UIObjectTable` — that third argument is where the 478 comes from.

`InitializeNaka` is one of thirty-one module initialisers called from `InitializeObjectTable`
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
> Nobody has yet traced how `InheritedProc` uses them. The earlier reading
> follows, kept for its evidence.

The `handler_table` field (offset +30 in CONTAINER, +38 in MENU_ITEM) is **not a function pointer** — it is a DRAM address pointing to an **event handler dispatch table**. The firmware's `InheritedProc` function:

1. Loads the widget's object record from the DRAM object table at `0x27ED2`
2. Extracts the handler dispatch table address from offset +10 of the record
3. Indexes into the table by event code to find the actual handler function
4. Calls the handler via indirect `call (xhl)`

Evidence: handler_table values increment by 2 per consecutive menu item (e.g., `0x0003F434`, `0x0003F436`, `0x0003F438`...) and fall in the `0x0003xxxx` address range (unmapped by ROM — written to DRAM at runtime). In contrast, dispatch widget `proc_addr` values resolve to actual ROM function symbols like `IvDrawbarProc`.

### Conversion Script

`scripts/naka_struct_decode.py` performs automated conversion:
1. Reads ROM bytes at the block's base address
2. Forward-scans for NAKA headers, strings, pointer tables, padding
3. Resolves pointers via ELF symbol table (36,849 symbols)
4. Generates C struct + linker script with `_Static_assert` size verification
5. All 23 auto-generated files verified byte-perfect

### Source Files

| File | Contents |
|------|----------|
| `maincpu/ui_widgets/naka_types.h` | Packed struct definitions and macros |
| `maincpu/ui_widgets/*.c` | 26 C data files (3 hand-crafted, 23 auto-generated) |
| `maincpu/ui_widgets/*_link.ld` | Linker scripts for extern symbol resolution |
| `scripts/naka_struct_decode.py` | Automated conversion tool |
| `scripts/naka_to_c.py` | Original conversion tool (used for hand-crafted files) |

---

## FD SAVE/LOAD TEST — Diagnostic Screen

The FD SAVE/LOAD TEST is a factory diagnostic screen that exercises the floppy disk I/O subsystem. It is the only user of type `0x16` (DIAGLIST) widgets and provides a complete example of the Title-based screen activation system.

### Activation Path

The diagnostic screen is part of the **HAMA** (file/disk) subsystem, initialized at boot by `InitializeHama` (ROM `0xF1E39E`):

1. **Boot registration.** `InitializeHama` calls `RegisterTitle` twice to register two diagnostic titles with the firmware's title management system:

   | Title String | Address | Widget Table | Purpose |
   |-------------|---------|-------------|---------|
   | `TT_HDDEXT` | `0xE1FD18` | `0x7f` | FDD / HD extension test |
   | `TT_EXTAPR` | `0xE1FD22` | `0xfc` | Extension APR test |

   Both titles share the same lifecycle callback: `TestTitleFunc` at `0xF1E39A` (pointer stored at `0xE1FD2C` in `fd_test_data.s`).

2. **Title activation.** When the user navigates to the diagnostic screen (exact UI path not yet fully traced; likely a hidden service mode), the title system activates the corresponding title and sends lifecycle events to `TestTitleFunc`:

   | Event | Parameter (xde) | Meaning |
   |-------|-----------------|---------|
   | `0x1C00007` | 0 | Title new |
   | `0x1C00007` | 1 | Title old |
   | `0x1C00007` | 2 | Title activate |
   | `0x1C00007` | 3 | Title inactivate |
   | `0x1C00007` | 4--5 | Title interrupt / return |
   | `0x1C00007` | 6 | TBIOS test |

3. **User actions.** Once the screen is active, button presses generate event `0x1C00013` dispatched to `TestTitleFunc`:

   | Parameter (xde) | Action |
   |-----------------|--------|
   | 2 | STOP FDD TEST |
   | 3 | START FDD TEST LOOP |
   | 4 | DIR (directory listing) |
   | 5--6 | Debug test |

4. **Dialog widget events.** The 7 dialog buttons generate events `0x1C00017`--`0x1C0001D`, handled by `FDTestDialogProc` via a word-offset jump table at `0xE1FF34`.

5. **File selection.** `HamaListProc` handles event `0x1E00086` (list item selection) for the file browser widget, forwarding unhandled events to the default handler.

### Screen Layout

The diagnostic screen uses 3 type-`0x16` DIAGLIST widgets displaying live counters:

| Widget | Address | Label | Purpose |
|--------|---------|-------|---------|
| 1 | `0xE1F794` | `" TOTAL :"` | Total test iterations |
| 2 | `0xE1F7D2` | `"    NG :"` | Failed iterations |
| 3 | `0xE1F810` | `"    OK :"` | Passed iterations |

The test writes a 2KB counting pattern (`0x0000`--`0x03FF`) to `A:IMMUNITY.TST`, reads it back, and compares byte-by-byte. Directory listing uses the pattern `A:\HAMA\*.LSW`.

### Source Files

| File | Contents |
|------|----------|
| `maincpu/fd_test_code.s` | `FDLoadSaveTest`, `FDListDirectory`, `FDTestDialogProc`, `HamaListProc` |
| `maincpu/fd_test_data.s` | DIAGLIST widgets, NAKA structures, pointer tables, diagnostic strings |
| `maincpu/kn5000_v10_program.s` | `InitializeHama`, `TestTitleFunc`, `FDTest_PrintDiag` |

### Standard Library Functions

Analysis of the FD test code identified several standard library functions used throughout the firmware:

| Label | Name | References | Description |
|-------|------|-----------|-------------|
| `0xFF0E80` | `Malloc` | 91 | Heap allocator (size on stack, returns pointer in xhl) |
| `0xFF0AF2` | `Free` | 70 | Heap deallocator (pointer on stack) |
| `0xFF0FFA` | `Memset` | 43 | Memory fill (buffer, byte, count on stack) |
| `0xFF0F4D` | `Strcpy` | 314 | String copy with null termination |
| `0xF4EB97` | `FileOpen` | 22 | Open file (mode flags: r/w/a/b/+/~/d) |
| `0xF4EEB9` | `FileWrite` | 10 | Write to file (handle, buffer, size) |
| `0xF4EE70` | `FileRead` | 10 | Read from file (handle, buffer, size) |
| `0xF4F05A` | `FileClose` | 9 | Close file handle |
| `0xF4F21F` | `FileOpenDefault` | 3 | Open file with default flags |

---

## Related Pages

- [UI Framework]({{ site.baseurl }}/ui-framework/) -- Widget system and event handling
- [Feature Demo & Presentation System]({{ site.baseurl }}/feature-demo/) -- SSF presentation that uses NAKA widgets

---

*Last updated: March 2026*
