---
layout: page
title: "Event Codes Reference"
permalink: /event-codes/
---

# Firmware Event Codes Reference

The KN5000 firmware uses a **hierarchical event dispatch system** to communicate between UI components, DISK MENU handlers, and extension ROMs. Events are 32-bit codes dispatched via `SendEvent` (synchronous) or `PostEvent` (asynchronous queue). This page documents all known event codes, their dispatch paths, and how they interact with the handler chain.

> **Freshness policy**: This page must be updated whenever new event codes are discovered during reverse engineering or homebrew development. See [Documentation Freshness Policy](#documentation-freshness-policy) below.


> **Corrected 2026-10-02.** The 26 `EVT_*` constants this page used to list were named from
> one observed use each. The firmware names every code itself: NAKA registers a ResEvent
> (`EV_*`) and a ResMethod (`MT_*`) name table beside each dispatch table, so `0x01Cm00nn` is
> entry nn of module m's ResEvent table and `0x01Em00nn` of its ResMethod table. The constants
> were renamed to those names (for example `EVT_IDENTITY` is `EVT_GET_CLASS_SP` = MT_GetClassSp,
> `EVT_MENU_OPEN` is `EVT_SHOW` = EV_SHOW), and the rows below now carry the corrected meanings.
> The full catalog -- 725 named codes and object ids, each with handler and sender evidence -- is
> `notes/event-codes-2026-10-02/catalog.json` in the disassembly repository. Some of this page's
> framing ("0x01E0 = lifecycle", "0x01E4 = widget responses") is superseded by it and awaits a
> rewrite.

## Event Code Format

Event codes are 32-bit values with a structured layout:

```
  0x01E0009C
  ├── 0x01E0  = Event port/category prefix
  └── 0x009C  = Event number within that category
```

The prefix determines which dispatch layer handles the event:

| Prefix | Category | Dispatch Layer | Description |
|--------|----------|----------------|-------------|
| `0x01E0` | Lifecycle / Object | ClassProc → ObjectProc → InheritedProc | Object lifecycle, getters, activation |
| `0x01C0` | Request / Action | Record function directly | Button presses, UI actions, initialization |
| `0x01E4` | Grid/Check Response | UI widget system | Widget state query responses |

## Dispatch Architecture

```
Event arrives (via SendEvent or PostEvent queue)
    │
    ▼
SendEvent (0xFA9660)
    │  Saves global state, looks up handler from object table
    │  Calls handler function (typically ClassProc)
    │
    ▼
ClassProc (0xFA44E2) ─── Layer 1: Simple Getters & Specials
    │  Handles: 0x01E00000-0x01E00007 (getters via jump table)
    │           0x01E0000D (keypress), 0x01E0000E (input)
    │           0x01E0000F (return immediately)
    │           0x01E00015 (return config pointer)
    │
    │  Everything else falls through to:
    ▼
ObjectProc (0xFA3D85) ─── Layer 2: Lifecycle Events
    │  Handles: 0x01E00010-0x01E00023 (20 lifecycle cases)
    │           via jump table at 0xEAA8A4
    │
    │  Everything else falls through to:
    ▼
InheritedProc (0xFA4409) ─── Layer 3: Handler Chain
    │  Follows "next handler" chain in data record (+0x04)
    │  Calls chained handler's implementation function
    │
    ▼
Record Function (implementation) ─── Layer 4: Handler-Specific
    │  Called by SendEvent (step 9) for ALL events
    │  Receives: XWA=object_id, XBC=event_code, XDE=param
    │  This is where extension ROM handlers intercept events
    │
    ▼
Default Handler (workspace[0x0E0A][0x00DC] = InheritedProc)
    Handles remaining lifecycle management if delegated
```

The "default handler" that extension ROMs delegate to, `workspace[0x0E0A][0x00DC]`,
is the firmware's own `InheritedProc` (0xFA4409). The firmware's function-name
table names the entry at that offset, as it does for every other offset an
extension calls (see [HDAE5000 Homebrew — Workspace Pointer]({{ site.baseurl }}/hdae5000-homebrew/#workspace-pointer)).

**Key insight:** The record function (Layer 4) receives ALL events, regardless of which layer processed them first. For extension ROMs, the record function is the primary interception point.

## Object ids: functions, modes and titles

Not every value in `0x01000000..0x01FFFFFF` is an event. The same object system names its
**objects** with the same layout, `0x01SSnnnn` = entry `nnnn` of registry slot `SS`, and the
firmware names those too, through the calls that register them:

| range | object | registered by | the firmware's name comes from | constant |
|---|---|---|---|---|
| `0x0100nnnn`-`0x010Fnnnn` | Function | `RegObjTabl NAKA_CLASS_Function, FunctionProc, n, table, 0x10m` | the same class registered at slot + 0x300: u32 pointers to strings | `NAKA_FUNC_<name>` |
| `0x0120nnnn`-`0x012Fnnnn` | ApFunction | `RegObjTabl NAKA_CLASS_ApFunction, ...` | likewise | `NAKA_APFUNC_<name>` |
| `0x0140nnnn`-`0x014Fnnnn` | MainFunction | `RegObjTabl NAKA_CLASS_MainFunction, ...` | likewise | `NAKA_MAINFUNC_<name>` |
| `0x01800000 + i` | Mode | `RegMode module, "MD_X", i, proc, home title` | the `MD_X` string | `NAKA_MODE_MD_X` |
| `0x01A00000 + i` | Title (screen) | `RegTitle module, "TT_X", i, ...` | the `TT_X` string | `TITLE_X` |
| `0x016Skkkk` | Class (widget class) | `RegObjTable NAKA_CLASS_Class, ClassProc, count, table, 0x16S` | the class definition's +12 name pointer | `NAKA_CLASS_<name>` |

For example `RegMode 0x4, InitializeSuna_Str_MD_SND_ARG, 0x11, NAKA_MAINFUNC_SndArgModeFunc,
TITLE_SNDARG` registers mode `0x01800011` ("MD_SND_ARG"), whose procedure is MainFunction
`0x01440016` -- entry 22 of Suna's MainFunction table (slot 0x144), named "SndArgModeFunc" by
its name table at slot 0x444 -- and whose home title is `0x01A000DC` ("TT_SNDARG").

`scripts/analysis/naka_object_id_names.py` derives all of them from the v10 source's
registration calls and the ROM: 1,395 ids, of which the 122 the 2026-10-02 event catalog had
already named from handlers and senders all agree with the derived name. The other 1,273 are
in `notes/event-codes-2026-10-02/object-ids/catalog_derived.json` and are `.equ` constants in
every tree's `shared/event_codes.s`; the registration macros' arguments use them since then.

A widget record's first word is its class id, and a class definition names its parent by
class id, so the class constants also appear in data: the HD-AE5000's 13 own classes
(`hdae5000/hdae5000_data_tables.s`, registered under ClassProc) derive from the root classes
`NAKA_CLASS_VwBox`, `_DbMemo`, `_TtlScreen`, `_Window`, `_PsInvisibleBox`, `_AcTitleMenu`,
`_AcWindowPage`, `_IvScreen` and `_AcLanguageText` (e.g. LyricBox: parent VwBox, allsize 46,
selfsize 18). Their records follow the main CPU's class layout field for field -- proc,
parent, allsize, selfsize, name, propdata, propname -- proved for all 13 by
`notes/hdae-class-records-2026-10-02/hdae_class_fields_probe.py` (2026-10-02).

## Known Event Codes

### ClassProc Getter Events (0x01E00000-0x01E00007)

Handled by ClassProc's jump table at `0xEAA8F8`. These are fast property queries.

| Code | Name | Handler | Return Value |
|------|------|---------|-------------|
| `0x01E00000` | `EVT_GET_CLASS_SP` | ClassProc_Event_LoadFromWA | MT_GetClassSp. Asks an object table's proc for the class id of the object. SendEvent asks this of every target first, then calls ... |
| `0x01E00001` | `EVT_GET_PARENT_CLASS_SP` | ClassProc_Event_LoadFromHL | MT_GetParentClassSp. Class-level query that returns the parent class id (Class record +4 'parent'). |
| `0x01E00002` | `EVT_GET_PROCEDURE_SP` | ClassProc_Event_LoadFromIZ | MT_GetProcedureSp. Returns the class procedure pointer (Class record +0 'proc'). |
| `0x01E00003` | `EVT_GET_INSTANCE_SIZE_SP` | ClassProc_Event_LoadFromOffset | MT_GetInstanceSizeSp. Returns the instance size of the class (WORD at Class record +8 'allsize'). Not *(XHL+0x0C), as the ... |
| `0x01E00004` | `EVT_GETTER_4` | (complex) | Linked object operation |
| `0x01E00005` | `EVT_GETTER_5` | (complex) | Linked object operation |
| `0x01E00006` | `EVT_GETTER_6` | (complex) | Linked object operation |
| `0x01E00007` | `EVT_GETTER_7` | (complex) | Linked object operation |

### ClassProc Special Events

| Code | Name | Dispatch | Description |
|------|------|----------|-------------|
| `0x01E0000D` | `EVT_GET_PROP_DATA_SP` | ClassProc special | MT_GetPropDataSp. Returns entry #n of an ID-typed property's value domain: FontIDProc returns the n-th font from the table at ... |
| `0x01E0000E` | `EVT_GET_PROP_DATA_COUNT_SP` | ClassProc special | MT_GetPropDataCountSp. Number of entries in an ID-typed property's value domain; FontIDProc returns the font count. It is not an ... |
| `0x01E0000F` | `EVT_GET_INSTANCE` | ClassProc special | MT_GetInstance. Returns a pointer to the object's instance record: the class record for a class, the mode or title record, the ... |
| `0x01E00015` | `EVT_GET_NAME` | ClassProc special | MT_GetName. Returns the object's name string pointer. For a class this is record+12; for Function, ApFunction, MainFunction ... |

### ObjectProc Lifecycle Events (0x01E00010-0x01E00023)

Handled by ObjectProc's jump table at `0xEAA8A4`. These manage object lifecycle (creation, destruction, state changes). Each maps to a specific lifecycle phase.

| Code | Name | Description |
|------|------|-------------|
| `0x01E00010` | `EVT_LIFECYCLE_10` | Lifecycle phase 0x10 |
| `0x01E00011` | `EVT_LIFECYCLE_11` | Lifecycle phase 0x11 |
| `0x01E00012` | `EVT_LIFECYCLE_12` | Lifecycle phase 0x12 |
| `0x01E00013` | `EVT_LIFECYCLE_13` | Lifecycle phase 0x13 |
| `0x01E00014` | `EVT_CHECK_CLASS` | MT_CheckClass. Object-level is-a test: returns 1 if the object's class is, or derives from, the class id in the parameter. ObjectProc forwards it as ... |
| `0x01E00015` | `EVT_LIFECYCLE_15` | Lifecycle phase 0x15 (also ClassProc special) |
| `0x01E00016` | `EVT_LIFECYCLE_16` | Lifecycle phase 0x16 |
| ... | ... | Phases 0x17-0x22 (not yet individually documented) |
| `0x01E00023` | `EVT_LIFECYCLE_23` | Lifecycle phase 0x23 (last) |

### DISK MENU Selection Events (0x01C0xxxx)

These are **request/action events** that reach the record function directly. They are the primary events extension ROMs should intercept.

| Code | Name | Context | Description |
|------|------|---------|-------------|
| `0x01C00001` | `EVT_SHOW` | DISK MENU opens | View shown (firmware EV_SHOW). Sent to a title's view after it becomes current; ViewableProc broadcasts it down the view tree. ... |
| `0x01C00002` | `EVT_HIDE` | Entry selected | View hidden/closed (firmware EV_HIDE); broadcast down the view tree like EV_SHOW. |
| `0x01C00008` | `EVT_SW_ON` | firmware `EV_SWON` | Panel switch pressed (firmware EV_SWON), param = switch number. Not specific to DISK MENU. |
| `0x01C0000F` | `EVT_PARA_DRAW` | Menu initialized | Draw the parameter/value text (firmware EV_PARADRAW); param = string pointer, or 0 to fetch the text with 0x1E0003A. Sibling ... |
| `0x01C00039` | `EVT_NEW_TITLE` | Entry selected | Broadcast to the current view tree that a title has just become the new current title (firmware EV_NEW_TITLE). |

### Activation Events

| Code | Name | Source | Description |
|------|------|--------|-------------|
| **`0x01C00008`** | **`EVT_SW_ON`** | Button press | Sent by firmware when user selects a DISK MENU entry via LCD panel button. **This is the event to intercept for button-press activation.** |
| `0x01E0009C` | `EVT_SET_VISIBLE` | firmware `MT_SetVisible` | Firmware method MT_SetVisible. It shows or hides a view: parameter 0 sets bit 0 of the view flags at instance+12 (hidden), and a non-zero parameter ... |

### Bitmap Resource Query Events

Used by the HD-AE5000's bitmap resource descriptors — the routines named `Alloc_Memory*`
in the disassembly, which despite the name allocate nothing and simply answer three
constant queries about one bitmap:

| Code | Name | Return Value | Description |
|------|------|-------------|-------------|
| `0x01E000A1` | `EVT_GET_BITMAP_DATA` | ROM pointer | Firmware method MT_GetBitmapData. A bitmap resource answers it with the ROM address of its pixel data. |
| `0x01E000A2` | `EVT_GET_BITMAP_WIDTH` | 0x140 (320), or 0x1B / 0x2A | Firmware method MT_GetBitmapWidth. A bitmap resource answers it with its width in pixels. |
| `0x01E000A3` | `EVT_GET_BITMAP_HEIGHT` | 0xF0 (240), or 0x1B / 0x0F | Firmware method MT_GetBitmapHeight. A bitmap resource answers it with its height in pixels. |

See [HDAE5000 — Embedded Graphics]({{ site.baseurl }}/hdae5000/#embedded-graphics-rewritten) for the six descriptors and the bitmaps they describe.

### Grid/Check Widget Events (0x01E4xxxx)

Used by the UI widget system for checkbox and grid controls:

| Code | Name | Description |
|------|------|-------------|
| `0x01E40008` | `EVT_PAN_UP` | Firmware method MT_PanUp: composer-set grid: increment the pan byte (record +2, max 127) of part XDE, then MT_RequestGridDraw (0x01E0008D) to 0xB4000E |
| `0x01E40009` | `EVT_GRIDCHECK_RESP_A2` | Grid/Check widget response variant A2 |
| `0x01E4000A` | `EVT_RLMT_UP` | Grid/Check widget response variant B |
| `0x01E4000B` | `EVT_GRIDCHECK_RESP_B2` | Grid/Check widget response variant B2 |

### Mode and Title Requests (0x01C00014-0x01C00016)

These three events switch the instrument's current **mode** and **title** (the
top-level screen). The parameter is the id of the mode or title that is wanted,
not a hard-disk parameter block:

| Code | Parameter | Main-CPU handler | Meaning |
|------|-----------|------------------|---------|
| `0x01C00014` | `0x0180nnnn` = mode id | `ModeProc`, case label `ObjectEnum_Close` | Mode request |
| `0x01C00015` | `0x01A0nnnn` = title id | `TitleProc`, case label `EventDispatch_SelectMatch` | Title request |
| `0x01C00016` | `0x01A0nnnn` = title id | `TitleProc`, case label `EventDispatch_OK` | Title request (second form) |

`ModeProc` also has a case for `0x01C00013` (`EVT_ACTIVATE_STATE` below), labelled
`ObjectEnum_Default`.

`ObjectEnum_Close`, `EventDispatch_SelectMatch` and `EventDispatch_OK` are the
case labels the disassembly currently carries. Their names were given before
anyone knew what these cases do.

**Mode and title ids.** A mode id `0x0180nnnn` is entry *nnnn* of object table
0x180. `InitializeObjectTable` registers that table with class id `0x01600006`,
proc `ModeProc`, 0x20 entries at RAM `0x0328FC` (`RegisterMode` fills them). A title id
`0x01A0nnnn` is entry *nnnn* of object table 0x1A0: class id `0x01600007`, proc
`TitleProc`, 0x100 entries of 22 bytes at RAM `0x032ABC` (`RegisterTitle`). `GetModeNow`
returns RAM `0x03EF82`, `GetModeOld` `0x03EF86`, `GetTitleNow` `0x03EF8A` and
`GetTitleOld` `0x03EF8E`. The mode case (`ObjectEnum_Close`) updates those four
variables. It then passes `0x01C00014` and `0x01C00015` on through `MainFuncCall`.

Titles quoted by the code:

| Title | Name (registered string) | Registered by | Requested by |
|-------|--------------------------|---------------|--------------|
| 0x7F | `TT_HDDEXT` | `InitializeHama` (module 9); **re-registered by the HD-AE5000** (module 0x0A) with its own view object | HD-AE5000 boot (`0x01C00016`), depending on `HDAE5000_Check_HD_Present`'s result ([note]({{ site.baseurl }}/boot-sequence/#hdae5000_boot_init-0x28f576)); `HDAE5000_RequestTitle15` from the frame handler |
| 0xEE | `TT_MESAGE` | `drawbar_panel_ui.s` `RegTitle 0x1, ..., 0xee` | `HDAE5000_ShowErrorMessageTitle` (`0x01C00016`) |
| 0xEF | `TT_WELCOM` | same block | `MainTitle_InitGraphicsAndEvents` at boot (`0x01C00016`) |
| 0xF0 | `TT_SOFTVER` | same block | `CtrlPanel_PostScrollEvent` (`0x01C00016`), when the held-switch accumulator is 0xA1 |
| 0xFC | `TT_EXTAPR` | `InitializeHama` | factory test entry — see [Test Modes]({{ site.baseurl }}/test-modes/) |
| 0x00 | — | — | `CtrlPanel_PostDisplayEvent` (`0x01C00015`), accumulator 0x91 — the [memory dump screen]({{ site.baseurl }}/memory-dump-screen/) |

**Dispatch path.** Requesters post to object `0xFFFFFFFF`. `SendEvent`
replaces that id with the current target (`GetCurrentTarget`, RAM `0x02F83C`)
before it looks up a proc. The `UI_Post*` and `HDAE5000_Request*` helpers below
(and `HDAE5000_ShowErrorMessageTitle`) first cancel any request of the same kind
that is still queued (`DeleteEvent` with the same object and event), then queue
the new one with `ApPostEvent`. The other requesters do not cancel first: the
boot request uses `PostEvent`, and the control-panel chords and the HD-AE5000
boot request call `ApPostEvent` directly. The requesters are:

- Main CPU: `UI_PostPartChangeEvent` (despite its name, it posts the **mode**
  request `0x01C00014` with `0x01800000 + A`) and `UI_PostModeChangeEvent`
  (despite *its* name, it posts the **title** request `0x01C00015` with
  `0x01A00000 + A`). At boot, `MainTitle_InitGraphicsAndEvents` posts mode
  `0x01800001` and then title 0xEF with plain `PostEvent`.
  `CtrlPanel_PostDisplayEvent` (`0x01C00015`, title 0x00) and
  `CtrlPanel_PostScrollEvent` (`0x01C00016`, title 0xF0) post with
  `ApPostEvent`.
- HD-AE5000: `HDAE5000_RequestMode` (twin of `UI_PostPartChangeEvent`, used
  after a song load when JUMP AFTER LOAD is on), `HDAE5000_RequestTitle15` (twin
  of `UI_PostModeChangeEvent`), `HDAE5000_RequestTitle16` (the same with
  `0x01C00016`; no caller found), and `HDAE5000_ShowErrorMessageTitle`, all
  through `RootFn_DeleteEvent` and `RootFn_ApPostEvent`. `HDAE5000_Boot_Init`
  posts title 0x7F (`0x01C00016`) through `RootFn_ApPostEvent` alone, when
  `HDAE5000_Check_HD_Present` finds a drive.

**Not established:** what distinguishes `0x01C00015` from `0x01C00016`. Both
reach `TitleProc` with a title id, but they take different cases. Listed on
[Open Questions]({{ site.baseurl }}/questions/).

Evidence: `hdae5000/hdae5000_ui_display.s` (the `HDAE5000_Request*` headers),
`v10/maincpu/ui/ui_widget_defs.s` (`ModeProc`, `TitleProc`, `GetModeNow`,
`RegisterTitle`, `SendEvent`), `v10/maincpu/ui/ui_control_panel.s`,
`v10/maincpu/boot/main_title_ctrl_panel.s` and the `RegTitle` blocks in
`v10/maincpu/ui/drawbar_panel_ui.s` and `v10/maincpu/factory_test/test_init.s`.
The finding is the `hdae` lane's, in
`notes/lanes/wave2-2026-09-25/lane-reports/hdae.json`.

> **Stale constant name.** Both `hdae5000/shared/event_codes.s` and
> `v10/maincpu/shared/event_codes.s` still define `0x01C00016` as
> `EVT_INTERRUPT_TITLE` ("hard disk initialization parameters"). That reading is
> wrong. Renaming the constant is a pending disassembly change.

### HD-AE5000 Events (0x01CA0000-0x01CA000C)

`0x01CA0000 + n` addresses entry *n* of object table 0x1CA, which the HD-AE5000
registers with class id `0x0160000C` (`ResEventProc`). Its 13 entries are the
names in `HDAE5000_EventName_Table`, in order. The code's own uses fit that
reading:

| Code | Entry name | Use in the code |
|------|------------|-----------------|
| `0x01CA0000` | `EV_SeqStop` | constant `EVT_HDAE_SEQ_STOP` in the sources (a misnomer) |
| `0x01CA0002` | `EV_TimerBack` | error-message timers (`RootFn_SetApTimer` with event `0x01CA0002`) |
| `0x01CA0004` | `EV_TICKS` | posted by `HDAE5000_Frame_Handler` to the open lyric box with the song position; `HDAE5000_LyricBoxProc` then runs `HDAE5000_Lyrics_PlayToPosition`. Constant `EVT_HDAE_TICKS` in the sources (a misnomer) |
| `0x01CA0008` / `0x01CA0009` | `EV_Alldraw` / `EV_Drawsyllable` | lyric-box redraw requests (`HDAE5000_Lyrics_PlayToPosition`) |

`HDAE5000_LyricBoxProc` dispatches `0x01CA0003`-`0x01CA0009` through a 7-entry
switch table. The table is typed in `hdae5000/hdae5000_data_tables.s`.

### Object State Query Events

| Code | Name | Description |
|------|------|-------------|
| `0x01E0008F` | `EVT_GET_SELECTED_CEL` | Firmware method MT_GetSelectedCel. It returns the selected cell packed as (col<<16)/row. |
| `0x01C0000D` | `EVT_DRAW` | Draw this view only (firmware EV_DRAW); EV_PAINT and EV_REPAINT send it to self. |
| `0x01C00013` | `EVT_ACTIVATE_STATE` | Activation-state notification to a mode or title object (firmware EV_ACTIVATE). The param is a phase: 0 = mode activated, 1 = mode deactivated, 2 = ... |

## Event Queue (PostEvent)

`PostEvent` (0xFA9752) enqueues events for asynchronous dispatch:

```
Queue base:   0x02BC34
Entry size:   12 bytes
Max entries:  1,024 (indices 0x0000-0x03FF)
Write index:  0x02EC36 (16-bit)
Counter:      0x02F840

Entry layout:
  +0x00  4 bytes  Target object ID (e.g., 0x016A0005)
  +0x04  4 bytes  Event code (e.g., 0x01E0009C)
  +0x08  4 bytes  Parameter
```

Events are dequeued by the main event loop and dispatched via `SendEvent`.

`ApPostEvent` (0xFA9D58) writes the same 12-byte entries into the same ring. It
differs in what it does when the queue is full: it yields to other tasks
(`TaskSched_YieldToQueue`) and retries, or gives up, depending on
`Boot_CheckConfigFlag7`. All the mode and title requests above use `ApPostEvent`
except the boot-time pair from `MainTitle_InitGraphicsAndEvents`, which uses
`PostEvent`.
`DeleteEvent` (0xFA9868) removes queued entries that match an object and an
event. (This page previously gave `PostEvent`'s address as 0xFAD61F. The
firmware's own function-name table and the v10 build both put it at 0xFA9752.)

## DISK MENU Activation Flow

The complete sequence when a user selects a DISK MENU entry by pressing a panel button:

```
1. User presses RIGHT 5 button on LCD panel
2. Control panel HLE sends scan code via SC1 serial
3. Firmware interprets button as DISK MENU selection
4. SendEvent dispatches events to registered handler:

   Step 1: EVT_SW_ON (0x01C00008)
       → ClassProc → ObjectProc → InheritedProc → Record function
       → Mines_Handler intercepts: sets GAME_ACTIVE=1, skips delegation

   Step 2: EVT_NEW_TITLE (0x01C00039)
       → Delegated to default handler (Mines_Handler doesn't intercept)

   Step 3: EVT_HIDE (0x01C00002)
       → Delegated to default handler

   Step 4: EVT_CHECK_CLASS (0x01E00014)
       → Handled by ObjectProc lifecycle, then delegated

5. Next Frame_Handler call detects GAME_ACTIVE=1
6. C runtime initialized, main() called
7. Game renders minesweeper board to VRAM
```

For comparison, programmatic activation via `PostEvent`:

```
1. FileIO_DiskRemoved calls PostEvent(0x00600002, 0x01E0009C, 0)
2. Main loop dequeues event
3. SendEvent(slot[+0x00], 0x01E0009C, 0)
4. ClassProc: not a getter → ObjectProc
5. ObjectProc: not in 0x10-0x23 range → InheritedProc
6. InheritedProc: follows handler chain
7. Record function (Mines_Handler) intercepts: sets GAME_ACTIVE=1
```

## Implementing Event Handlers

For homebrew extension ROMs that register handlers via `RegisterObjectTable`:

```c
// Pseudo-code for a handler record function
void My_Handler(uint32_t object_id, uint32_t event_code, uint32_t param) {
    switch (event_code) {
    case 0x01C00008:  // Button-press activation (DISK MENU selection)
        GAME_ACTIVE = 1;
        return;       // Skip delegation to prevent default handler UI

    case 0x01E0009C:  // Programmatic activation (PostEvent injection)
        GAME_ACTIVE = 1;
        return;       // Skip delegation

    default:
        // Delegate everything else to default handler
        call_default_handler(object_id, event_code, param);
        break;
    }
}
```

Assembly implementation (TLCS-900, from the Mines project):

```asm
Mines_Handler:
    push  xix
    push  xiz

    ; Check for DISK MENU selection event
    ld    xix, 0x01C00008
    cp    xbc, xix
    jr    z, .activate

    ; Check for PostEvent activation
    ld    xix, 0x01E0009C
    cp    xbc, xix
    jr    z, .activate

    ; Delegate to default handler
    ld    xiz, (WORKSPACE_PTR)
    add   xiz, 0x0E0A
    ld    xiz, (xiz)
    add   xiz, 0x00DC
    ld    xix, (xiz)
    call  (xix)
    jr    .done

.activate:
    ; Set game active flag
    ld    xhl, GAME_ACTIVE
    ld    xwa, 0x00000001
    ld    (xhl), xwa
    ; Fall through to .done (skip default handler)

.done:
    pop   xiz
    pop   xix
    ret
```

## Documentation Freshness Policy

This event codes reference and the following related documentation must be updated whenever new event codes are discovered or existing codes are better understood:

1. **This page** (`event-codes.md`) -- Add new codes, update descriptions, correct dispatch paths
2. **[HDAE5000 Homebrew Development]({{ site.baseurl }}/hdae5000-homebrew/)** -- Update handler examples and activation flow
3. **ROM disassembly** (`~/devel/kn5000-roms-disasm/`) -- Update symbolic names (`EVT_*` constants) in assembly source
4. **Symbol reference files** -- Keep `hdae5000_symbols_reference.txt` and `maincpu_symbols_reference.txt` in sync with assembly

See also: [HDAE5000 Homebrew Development]({{ site.baseurl }}/hdae5000-homebrew/) for the full handler registration and dispatch system documentation.
