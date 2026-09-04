---
layout: page
title: UI Framework
permalink: /ui-framework/
---

# UI Framework

The KN5000 firmware contains an object-oriented UI framework with 550+ widget handlers ("Proc" classes), event-driven dispatch, property introspection, and a drawing primitives API. The framework manages the 320x240 LCD display, processes control panel input, and routes MIDI events to UI elements.

## Architecture

The UI framework is organized in layers:

1. **ClassProc hierarchy** - Object-oriented widget system with inheritance
2. **Event dispatch** - Two event spaces: actions (0x1C0xxxx) and getters (0x1E0xxxx)
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

| Module | Init Routine | Address (v10) | Source file | Purpose |
|--------|-------------|---------|---------|---------|
| **Murai** | `InitializeMurai` | 0xF7AD77 | `ui/drawbar_panel_ui.s` | Core UI framework, event dispatch |
| **Toshi** | `InitializeToshi` | 0xFC311A | `extensions/extension_init.s` | Extension device support |
| **East** | `InitializeEast` | 0xF72BAC | `sequencer/seq_event_playback.s` | Eastern region/style UI |
| **Suna** | `InitializeSuna` | 0xF19636 | `storage/flash_floppy_handlers.s` | Sound parameter UI |
| **Cheap** | `InitializeCheap` | 0xF9426A | `file_io/medley.s` | Basic parameter editing |
| **Scoop** | `InitializeScoop` | 0xF028E3 | `display/scoop_display.s` | Display update manager |
| **Yoko** | `InitializeYoko` | 0xF29E6D | `sequencer/sequencer_ui.s` | Horizontal layout/scrolling |
| **Kubo** | `InitializeKubo` | 0xF2D2C4 | `sequencer/sequencer_ui.s` | Grid/table layout |
| **Hama** | `InitializeHama` | 0xF1E146 | `factory_test/test_init.s` | Factory diagnostic tests |
| **KSS** | `InitializeKSS` | 0xFC3E4F | `kn5000_v10_program.s` | Keyboard/panel status |
| **Naka** | `InitializeNaka` | 0xF165EB | `storage/flash_floppy_handlers.s` | UI widget descriptor tables |

Three of the code names also name directories in the disassembly, which is what fixes their
scope: `ui_widgets/` is NAKA, `extensions/` is TOSHI, `factory_test/` is HAMA. The other eight
purposes are read from what each module registers, not from an independent source.

Each module registers "object tables" that define UI component hierarchies using the `RegObjTable` / `RegObjTabl` macros.

## Widget Type System (ClassProc Hierarchy)

All UI widgets are implemented as "Proc" handlers — functions that receive events and respond based on their widget type. The framework uses a class hierarchy with inheritance.

### Base Classes

| Proc | Description |
|------|-------------|
| `DefaultClassProc` | Root of the class hierarchy |
| `ClassProc` | Base class handler |
| `ObjectProc` | Object-level handler |
| `ViewableProc` | Base for all visible widgets |
| `FunctionProc` | Function dispatch handler |
| `InheritedProc` | Calls parent class handler |

### Primitive Widgets

| Proc | Description |
|------|-------------|
| `BoxProc` | Basic rectangular container |
| `GroupBoxProc` | Grouped container with title |
| `WindowProc` | Top-level window |
| `ScreenProc` | Full-screen display |
| `StringBoxProc` | Text display box |
| `TextBoxProc` | Text content area |
| `LabelProc` | Static text label |
| `BitmapProc` | Image display |
| `IconProc` | Small icon display |
| `LineProc` | Line element |
| `FrameProc` | Bordered frame |
| `EditSwProc` | Edit switch/toggle |

### View Widgets (Vw* prefix)

View widgets are interactive display containers:

| Proc | Description |
|------|-------------|
| `VwBoxProc` | Interactive box container |
| `VwMenuBoxProc` | Menu container |
| `VwEditSwBoxProc` | Edit switch box |
| `VwUserBitmapProc` | User bitmap display |
| `VwUserBitmapByNameProc` | Bitmap by name lookup |
| `VwScreenTitleProc` | Screen title bar |

### Page/Settings Widgets (Ps* prefix)

Settings-page widgets for parameter display:

| Proc | Description |
|------|-------------|
| `PsParaBoxProc` | Parameter box |
| `PsPageBoxProc` | Page container |
| `PsMenuBoxProc` | Settings menu |
| `PsEditSwBoxProc` | Settings edit switch |
| `PsToggleBoxProc` | Toggle button |
| `PsListBoxProc` | Scrollable list |
| `PsGridBoxProc` | Grid/table layout |
| `PsEditBoxProc` | Text edit field |
| `PsNumEditBoxProc` | Numeric editor |
| `PsTblEditBoxProc` | Table editor |
| `PsRadioBoxProc` | Radio button group |
| `PsMixerControlProc` | Mixer fader control |

### Action/Control Widgets (Ac* prefix)

Interactive control widgets that respond to user input:

| Proc | Description |
|------|-------------|
| `AcOnOffBoxProc` | On/off toggle |
| `AcIndexToggleProc` | Index selector toggle |
| `AcFuncToggleProc` | Function toggle |
| `AcNumEditBoxProc` | Numeric edit control |
| `AcBitEditBoxProc` | Bit-level edit |
| `AcStrRadioBoxProc` | String-based radio buttons |
| `AcTempoBoxProc` | Tempo display/edit |
| `AcGridBoxProc` | Interactive grid |
| `AcListBoxProc` | Interactive list |
| `AcDrawbarNameProc` | Drawbar organ label |
| `AcAccordionTabProc` | Accordion tab control |
| `AcMixerVolProc` | Mixer volume fader |
| `AcPartMixerProc` | Part mixer control |
| `AcTrackMixerProc` | Track mixer control |
| `AcPresentationBoxProc` | SSF presentation display |
| `AcPresentationControlProc` | SSF presentation controller |
| `AcNamingWindowProc` | File/item naming dialog |

### Specialized Grid Widgets

Many domain-specific grid configurations exist:

| Proc | Domain |
|------|--------|
| `AcEasyCmpGridBoxProc` | Easy Composer settings |
| `AcCmpSetGridBoxProc` | Composer set grid |
| `AcSndArgGridBoxProc` | Sound argument grid |
| `AcCtlMsgGridBoxProc` | Control message grid |
| `AcFadeSetGridBoxProc` | Fade settings grid |
| `AcInOutGridBoxProc` | Input/output routing grid |
| `AcMidiPartGridBoxProc` | MIDI part assignment grid |
| `AcParaLoadOptGridBoxProc` | Parameter load options |

### Screen Types

| Proc | Description |
|------|-------------|
| `IvScreenProc` | Interactive screen |
| `TtlScreenProc` | Title screen |
| `NormScreenProc` | Normal operating screen |
| `MsaModeScreenProc` | MSA mode screen |
| `VariScreenProc` | Variation screen |
| `RVariScreenProc` | Registration variation screen |
| `PmBankScreenProc` | Panel memory bank screen |
| `SineWaveScreenProc` | Sine wave test screen |
| `AcFdemoScreenProc` | Feature demo screen |
| `AcWelcomScreenProc` | Welcome/startup screen |

### Interactive View Widgets (Iv* prefix)

Controller widgets for page navigation and lifecycle:

| Proc | Description |
|------|-------------|
| `IvPageControlProc` | Page control handler |
| `IvWindowPageCtlProc` | Window-based page control |
| `IvPmemWindowPageCtlProc` | Panel memory page control |
| `IvExitProc` | Exit handler |
| `IvExitWindowProc` | Window exit handler |
| `IvWaitWinCtlProc` | Wait dialog control |
| `IvNamingProc` | Naming dialog controller |
| `IvShowHideProc` | Visibility toggle |
| `IvCatchEventProc` | Event capture handler |
| `IvDrawbarProc` | Drawbar organ display |
| `IvAccordionProc` | Accordion display |

### Property Type System

The framework includes a complete type system for widget properties with introspection:

**Primitive types:** `swordProc`, `uwordProc`, `scharProc`, `ucharProc`, `slongProc`, `ulongProc`, `boolProc`

**Pointer types:** `pSwordProc`, `pUwordProc`, `pScharProc`, `pUcharProc`, `pSlongProc`, `pUlongProc`, `pBoolProc`, `pFuncProc`, `pProcProc`, `pStringProc`

**Geometry types:** `RECTWProc`, `POINTWProc`, `PointXProc`, `PointYProc`, `RectX1Proc`, `RectY1Proc`, `RectX2Proc`, `RectY2Proc`

**ID types:** `ColorIDProc`, `BorderIDProc`, `AlignmentIDProc`, `LineModeIDProc`, `FontIDProc`, `IconIDProc`, `BitmapIDProc`, `UserIDProc`, `PartIDProc`, `TrackIDProc`, `EventIDProc`

**Resource types:** `ResourceProc`, `ResEventProc`, `ResMethodProc`, `ResNameProc`, `ResBitmapProc`, `ResFrameProc`, `ResIconProc`, `ResFontProc`, `ResStringProc`

## Event System

### Event Code Spaces

Events use 32-bit codes divided into two spaces:

**Action events (0x1C0xxxx)** — Request something to happen:

| Event | Code | Description |
|-------|------|-------------|
| `EVT_MENU_OPEN` | 0x1C00001 | Open DISK MENU display |
| `EVT_SELECT_CONFIRM` | 0x1C00002 | Confirm current selection |
| `EVT_ACTIVATE` | 0x1C00008 | Activate entry via button press |
| `EVT_POST_INIT` | 0x1C0000D | Post-initialization hook |
| `EVT_INIT_HOOK` | 0x1C0000F | Custom initialization |
| `EVT_CPANEL_EVENT` | 0x1C00013 | Control panel button/encoder event |
| `EVT_HD_INIT_PARAMS` | 0x1C00016 | Hard disk parameter init |
| `EVT_BUTTON_FOCUS` | 0x1C00039 | Button focus during selection |
| `EVT_DISPLAY_CALLBACK` | 0x1CA0000 | Display update callback |
| `EVT_DISPLAY_UPDATE` | 0x1CA0004 | Force display update |

**Getter events (0x1E0xxxx)** — Query widget state:

| Event | Code | Description |
|-------|------|-------------|
| `EVT_IDENTITY` | 0x1E00000 | Return widget identity |
| `EVT_GET_HL` | 0x1E00001 | Return value in XHL |
| `EVT_GET_IZ` | 0x1E00002 | Return value in XIZ |
| `EVT_GET_CONFIG` | 0x1E00003 | Return config at XHL+0x0C |
| `EVT_KEYPRESS` | 0x1E0000D | Keypress query |
| `EVT_INPUT` | 0x1E0000E | Input event query |
| `EVT_RETURN_ZERO` | 0x1E0000F | No-op (returns zero) |
| `EVT_REDRAW` | 0x1E00014 | Request UI refresh |
| `EVT_OBJECT_STATE_QUERY` | 0x1E0008F | Query object state |
| `EVT_POST_ACTIVATE` | 0x1E0009C | Post-activation query |

### Event Dispatch Functions

| Function | Description |
|----------|-------------|
| `MainDispatchEvent` | Primary event router |
| `MainSendEvent` | Direct event send |
| `MainPostEvent` | Post event to queue |
| `SendEvent` | Generic send |
| `PostEvent` | Generic post |
| `BroadcastEvent` | Send to all listeners |
| `DispatchEvent` | Route by type |
| `ApPostEvent` | Application-level post |

## Drawing Primitives API

The firmware provides a complete set of drawing primitives that render to the offscreen buffer (0x43C00) and VRAM (0x1A0000-0x1DFFFF). These are defined in `drawing_primitives.s`.

### Line Drawing

| Function | Description |
|----------|-------------|
| `DrawLine` | Draw a line between two points |
| `DrawLineEx` | Extended line with pattern support |

### Geometric Shapes

| Function | Description |
|----------|-------------|
| `DrawBox` | Filled rectangle |
| `DrawFrame` | Rectangle outline |
| `DrawFrameEx` | Extended frame with style |
| `DrawFrameSP` | Frame with special properties |
| `DrawWall` | Tiled background fill |

### Bitmap Rendering

| Function | Description |
|----------|-------------|
| `DrawBitmap` | Standard bitmap render |
| `DrawBitmapFast` | Optimized bitmap render |
| `DrawBitmapSP` | Bitmap with transparency |
| `DrawBitmapSPFast` | Optimized transparent bitmap |
| `DrawBitmapSP2` | Bitmap variant 2 |
| `DrawBitmapFile` | Render bitmap from file data |

### Text Rendering

| Function | Description |
|----------|-------------|
| `DrawString` | Basic text output |
| `DrawStringCentered` | Centered text within bounds |
| `DrawStringLeftJustify` | Left-aligned text |
| `DrawStringRightJustify` | Right-aligned text |
| `DrawStringAlignment` | Text with specified alignment |
| `DrawStringReverse` | Right-to-left text |

### Pixel Operations

| Function | Description |
|----------|-------------|
| `MovePixels` | Block pixel copy/move |
| `DrawIcons` | Render icon set |

## Page Management

The UI uses a hierarchy of Screens > Windows > Pages:

- **Screens** (`ScreenProc`, `IvScreenProc`) — Full-screen layouts that own the entire display
- **Windows** (`WindowProc`, `IvWindowPageCtlProc`) — Contained regions within a screen
- **Pages** (`IvPageControlProc`, `PsPageBoxProc`) — Switchable content within a window

Page controllers (`IvPageControlProc`) manage which page is visible and handle transitions when the user switches tabs or modes. Window-level controllers (`IvWindowPageCtlProc`) coordinate multiple pages within a single window.

### Known Page Identifiers

| Page | Description |
|------|-------------|
| MAIN_PAGE | Main operating screen |
| SOUND_PAGE | Sound/voice selection |
| STYLE_PAGE | Style selection |
| RECORD_PAGE | Sequencer recording |
| PLAY_PAGE | Playback controls |
| MIDI_PAGE | MIDI settings |
| UTILITY_PAGE | System utilities |
| PC_DATA_LINK_PAGE | PC connection (HDAE5000) |
| HDD_UTIL_PAGE | Hard disk utilities |

## Presentation System (SSF)

The firmware includes an **XML-based presentation scripting system** used for the built-in Feature Demo. This is a separate subsystem from the general widget framework, with its own XML parser, event handlers (`EV_READPRESENTATION`, `EV_READACTION`, `EV_READSONG`), and tag vocabulary (`PRESENTATION`, `ACTION`, `SHOW`, `IMG`, `SONG`, `EXEC`, etc.).

The presentation controller (`AcPresentationControlProc` at `0xF8450B`) dispatches actions via a jump table, and the Feature Demo script (`hkst_55.ssf`) drives a 27-step automated demonstration with bitmap images and instrument displays.

See [Feature Demo & Presentation System]({{ site.baseurl }}/feature-demo/) for full documentation.

## Code References

### Include Files

⚠ The line counts below are stale — the repo now holds three ROM versions (v7/v9/v10) and none
of them matches these figures exactly for every file (checked directly: `drawing_primitives.s` is
close at 4,575 in v10, but `semenu_routines.s` is 7,506 in v9/v10 — more than double the 3,431
here — and `fdemotext_routines.s` is 3,259 in v9/v10 against 2,334 here). Current v10 line counts,
for reference: `drawing_primitives.s` 4,575; `semenu_routines.s` 7,506; `bitmap_out_routines.s`
4,669; `psgridbox_routines.s` 1,146; `rvari_routines.s` 2,761; `fdemotext_routines.s` 3,259;
`setwall_routines.s` 2,193; `bmdredit_routines.s` 4,436. Paths also moved under per-subsystem
directories, e.g. `v10/maincpu/ui/drawing_primitives.s`, `v10/maincpu/audio/semenu_routines.s`,
`v10/maincpu/demo/fdemotext_routines.s`, `v10/maincpu/sequencer/bmdredit_routines.s`.

| File | Lines (as originally documented) | Contents |
|------|-------|----------|
| `drawing_primitives.s` | 4,567 | Line, box, frame, bitmap, string rendering |
| `semenu_routines.s` | 3,431 | Sound editor menu system |
| `bitmap_out_routines.s` | 4,347 | Bitmap output/display compositing |
| `psgridbox_routines.s` | 1,138 | Performance settings grid box UI |
| `rvari_routines.s` | 2,752 | Registration variation selection UI |
| `fdemotext_routines.s` | 2,334 | Feature demo text rendering |
| `setwall_routines.s` | 1,940 | Accompaniment style wall parser |
| `bmdredit_routines.s` | 4,434 | Beat/drum editor |

### Key Routines

| Symbol | Address | Description |
|--------|---------|-------------|
| `InitializeObjectTable` | 0xFA40B3 | Boot-time UI module registration |
| `MainDispatchEvent` | — | Primary event router |
| `MainFuncCall` | — | Widget function call dispatcher |
| `GetViewInstance` | — | Get widget view instance |
| `RegisterObjectTable` | — | Register widget object table |
| `DrawLine` | — | Line drawing primitive |
| `DrawBitmapFile` | — | File-based bitmap rendering |
| `DrawStringCentered` | — | Centered text rendering |

## Related Pages

- [Feature Demo & Presentation System]({{ site.baseurl }}/feature-demo/) - SSF XML scripting system
- [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) - Input handling
- [Display Subsystem]({{ site.baseurl }}/display-subsystem/) - Screen rendering
- [Image Gallery]({{ site.baseurl }}/image-gallery/) - UI graphics
- [Event Codes]({{ site.baseurl }}/event-codes/) - Complete event code reference

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

| Opcode | Name | Size | Description |
|--------|------|------|-------------|
| 0x01 | HLINE | 10 | Horizontal line: `op + 0x0a + x1(2) + y1(2) + x2(2) + y2(2)` |
| 0x02/0x0a | VLINE | 10 | Vertical line: `op + 0x0a + x1(2) + y1(2) + x2(2) + y2(2)` |
| 0x02/other | WIDGET | 15 | Widget ref: `op + sub + id(2) + flags(2) + handler(7) + x(1) + y(1)` |
| 0x03 | SETUP | var | Setup block with coordinate arrays |
| 0x04 | CONTROL | var | Control metadata |
| 0x06 | REF | var | Reference (sometimes with text label) |
| 0x07 | SHORTREF | var | Short reference |
| 0x09 | RECT | 10 | Rectangle outline: same coord format as HLINE |
| 0x0a | FILLED_RECT | 10 | Filled rectangle: same coord format as HLINE |
| 0x0b | BLOCK | var | Block data |
| 0x0e | CALLBACK | var | Callback reference |
| 0x20 | STRING | var | Text: `op + len + x(1) + y(1) + text_bytes...` |

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

| Byte | Character |
|------|-----------|
| 0x20-0x7E | Standard ASCII |
| 0x88 | ♭ (flat) |
| 0x8C | ♯ (sharp) |
| 0x8D | │ (vertical bar / up arrow) |
| 0x8E | ~ (down arrow) |

### Decoded Files

These blocks are typed C struct source per `<version>/maincpu/style_ui/*.c`, compiled and
`.incbin`'d into `ui_widgets/style_ui_params.s` — see
**[ScreenData C Conversion]({{ site.baseurl }}/screendata-c-conversion/)** for the full
inventory across all three ScreenData subsystems:

| File | Bytes | Commands | Contents |
|------|-------|----------|----------|
| `style_ui/main.c` | 3531 | 375 | Style editor main grid: chord boxes, parameter widgets, chord name tables, bottom bar |
| `style_ui/meascursor.c` | 184 | 18 | Measure cursor: MEAS/CURSOR/CTL labels, BAL/ERS refs, navigation arrows |
| `style_ui/yesctl.c` | 228 | 29 | Yes/No confirmation + measure cursor + CTL value |
| `style_ui/ctlonly.c` | 551 | 4+tables | CTL-only: 4 commands + LCD charset translation table + format strings |

### Decoder Scripts

⚠ **Stale**: both scripts below still hardcode the path from before the tree moved to the typed
`.c` layout above (`maincpu/includes/style_ui_screendata_main.s`, which does not exist at any
version) and fail with `FileNotFoundError` — reproduced directly. Their command-format
documentation earlier on this page is still correct; only the file-loading path is broken.

- `scripts/analysis/decode_screendata.py` — Generic bytecode parser, outputs human-readable command descriptions
- `scripts/tools/annotate_screendata_main.py` — Section-aware annotation generator for the main screen

## Research Needed

- [ ] Document widget property layout (offset table per widget type)
- [ ] Map complete event dispatch chain (post → queue → dispatch → handler)
- [ ] Document focus/navigation system (tab order, encoder routing)
- [ ] Trace widget creation flow (alloc → init → register → display)
- [ ] Decode ScreenData for other UI screens beyond StyleUI
