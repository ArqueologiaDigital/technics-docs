---
layout: page
title: Feature Demo & Presentation System
permalink: /feature-demo/
---

# Feature Demo & Presentation System

The KN5000 firmware contains a **full XML-based presentation scripting system** used for the built-in Feature Demo. This system is significantly more sophisticated than a simple slideshow — it includes an XML parser, an event-driven presentation controller, and a rich tag vocabulary suggesting it was designed for general-purpose use.

## SSF Presentation Format

### Files in Table Data ROM

Two `.ssf` file names (the expansion of SSF is not established) appear in the Table Data ROM; only the first has a script:

| File          | ROM Address                                                                               | Purpose                                                                                                                                                                                                                           |
|---------------|-------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `hkst_55.ssf` | 0x87FFF0 (metadata), 0x88000E (XML data)                                                  | Feature Demo presentation script                                                                                                                                                                                                  |
| `hkt_87.ssf`  | 0x9FFFC0, after the table-data ROM's vector table (`table_data/kn5000_table_data.s:5203`) | A name string only, with no script after it. A signature record in the program ROM, `RomTest_RomSignatures`, expects `"hkt_"` at this address (v10 `ui_widgets/style_bitmaps.s:431-434`; no reader of that record has been found) |

**Source file:** `../../kn5000-roms-disasm/table_data/includes/hkst_55.ssf`

### XML Format

The Feature Demo script is real XML with a defined structure:

```xml
<ACTION>
  <ACT NO=1><SHOW OBJ="ftdemo01"></ACT>
  <ACT NO=2><SHOW OBJ="ftdemo04"></ACT>
  <ACT NO=3><SHOW OBJ="ftdemo05"></ACT>
  ...
  <ACT NO=27><SHOW OBJ="ftdemo25"></ACT>
</ACTION>
```

The script defines 27 sequential actions, each showing a named display object: `ftdemo01`, `ftdemo04`–`ftdemo10`, `ftdemo20`–`ftdemo25` and `ftdemo41`–`ftdemo48`, plus the live screens `Accordion` (actions 16-17), `Drawbar` (19-20) and `Sdmixer` (25). The script text is `Feature_Demo_XML` in `table_data/kn5000_table_data.s:189-218`.

---

## XML Tag Vocabulary

The firmware carries a complete XML tag name table in the Program ROM. (`FDemoText_MarkupTagTable`, `v10/maincpu/ui_widgets/naka_technichord_strings.c:9715-9748`, pairs each tag with its handler. `PRESENTATION`, `ACTION` and their closing tags have none. `SONG`, `SRC` and `NAME` are attribute names of `EXEC`, listed in `FDemoText_ExecTagAttrNames` at :9785.)

### Structure Tags

| Tag | Close Tag | Purpose |
|-----|-----------|---------|
| `PRESENTATION` | `/PRESENTATION` | Top-level presentation wrapper |
| `ACTION` | `/ACTION` | Action sequence container |
| `ACT` | `/ACT` | Individual action step (with `NO=` attribute) |

### Content Tags

| Tag      | Close Tag | Purpose                           |
|----------|-----------|-----------------------------------|
| `SHOW`   | —         | Show/display a named UI object    |
| `IMG`    | —         | Display an image                  |
| `FONT`   | `/FONT`   | Font selection for text rendering |
| `CENTER` | `/CENTER` | Text centering                    |
| `BR`     | —         | Line break                        |

### Attribute Tags

| Tag    | Purpose                          |
|--------|----------------------------------|
| `SONG` | Attribute of `EXEC`              |
| `SRC`  | Source reference (file/resource) |
| `NAME` | Name identifier                  |

### Command Tags

| Tag        | Purpose                                                                                           |
|------------|---------------------------------------------------------------------------------------------------|
| **`EXEC`** | **Names the presentation: `SONG` number, `SRC` base name of the `.SQT` and `.ACT`, `NAME` title** |

The name suggests more than it does. On the KN6000, whose tag table is the same, the `EXEC` handler stores a song number, a base file name (used for both the `.SQT` and the `.ACT`) and a title, then posts UI messages (what they trigger was not traced); it executes nothing from the script. The KN7000 dropped `EXEC` altogether and reads `FEATURE.PRE` as two plain lines (see [KN7000 Slide Shows]({{ site.baseurl }}/kn7000-slideshow/#the-kn5000kn6000-presentations-and-why-they-do-not-play-here)).

---

## Presentation Handler Functions

The firmware implements a full event-driven presentation controller:

### Core Handlers

| Function                    | ROM Address | Source (`ui/drawbar_panel_ui.s`) | Purpose                      |
|-----------------------------|-------------|----------------------------------|------------------------------|
| `AcFdemoScreenProc`         | 0xF84149    | :18161                           | Feature Demo screen handler  |
| `AcPresentationBoxProc`     | 0xF842B4    | :18322                           | Presentation display widget  |
| `AcPresentationControlProc` | 0xF8450B    | :18544                           | Main presentation controller |
| `IvDemofeature1Proc`        | 0xF841EE    | :18228                           | Feature Demo event handler 1 |
| `IvDemofeature2Proc`        | 0xF8422F    | :18262                           | Feature Demo event handler 2 |

`AcPresentationControlProc` is the main dispatch routine. It uses a jump table at `0xE9F9B2` to handle different presentation states/events.

### Event System

The firmware defines dedicated events for presentation processing (source: `shared/event_codes.s:99-101`):

| Event (firmware name)                           | Value      | Meaning                                                                   |
|-------------------------------------------------|------------|---------------------------------------------------------------------------|
| `EVT_READ_PRESENTATION` (`EV_READPRESENTATION`) | 0x01C10001 | The presentation (`.PRE`) file has been read; the parameter is the result |
| `EVT_READ_ACTION` (`EV_READACTION`)             | 0x01C10002 | The action (`.ACT`) file has been read                                    |
| `EVT_READ_SONG` (`EV_READSONG`)                 | 0x01C10003 | The song (`.SQT`) file has been read                                      |

These events integrate with the KN5000's broader UI event system (see [UI Framework]({{ site.baseurl }}/ui-framework/)).

---

## Feature Demo Assets

### Bitmap Images (Table Data ROM)

The Feature Demo includes 6 bitmap images stored in Windows BMP format:

| Asset | ROM Address | Size (bytes) | Content |
|-------|-------------|-------------|---------|
| `FTBMP01.BMP` | 0x880418 | 77,878 | Technics logo with world globe |
| `FTBMP02.BMP` | 0x89344E | 42,678 | Subwoofers |
| `FTBMP03.BMP` | 0x89DB04 | 39,478 | Floppy discs |
| `FTBMP04.BMP` | 0x8A753A | 39,478 | Inserting discs |
| `FTBMP05.BMP` | 0x8B0F70 | 41,078 | Surround sound arrows |
| `FTBMP06.BMP` | 0x8BAFE6 | 77,878 | KN5000 name with rainbow comet |

**Total bitmap storage:** 318,468 bytes (~311 KB)

### File Entry Index (0x8CE01C)

The bitmap file entries use a fixed record format:

```
struct FeatureDemo_FileEntry {
    char   filename[12];    // +0x00: null-terminated filename (e.g., "FTBMP01.BMP")
    uint32 reserved;        // +0x0C: always 0
    uint32 data_ptr;        // +0x10: pointer to BMP data in ROM
    uint32 file_size;       // +0x14: size in bytes
};                          // Total: 24 bytes per entry
```

Six entries are stored contiguously at 0x8CE01C, referenced by the metadata header at 0x87FFF0 via `FeatureDemo_FileEntry1`.

**Readers** (v10, from the source headers written by the `tdata` lane in September 2026):
`FDemo_LinkedListSearch` (0xF8682F) starts its bitmap-name search at the metadata header's
`+0x18` (`ld xiz,(0x880008)`), and `FDemo_LinkedListLookupField` (0xF868EF) returns an entry's
data pointer. `VwUserBitmapByNameProc` (0xF9C5FC) appends ".BMP" to a widget's key ("FTBMP01")
before the search, and `DrawBitmapFile` (0xFAC697) draws the result. `DrawBitmapFile_Impl`
(0xFAC6F3) checks the BMP header: "BM", `biSize` 40, `biPlanes` 1, `biBitCount` ≤ 8, `biClrUsed`
≤ 256, `bfOffBits − 54` ≤ 1024. All six files pass.

### Metadata Header (0x87FFF0)

The presentation file metadata at 0x87FFF0 links the SSF script and asset index:

```
struct FeatureDemo_FileMetadata {
    char   filename[12];    // +0x00: "hkst_55.ssf"
    uint32 reserved;        // +0x0C: 0
    uint32 padding_ptr;     // +0x10: pointer to 2-byte padding (HKstSSF_Padding)
    uint32 xml_ptr;         // +0x14: pointer to XML data (Feature_Demo_XML at 0x88000E)
    uint32 entries_ptr;     // +0x18: pointer to file entries (FeatureDemo_FileEntry1 at 0x8CE01C)
};
```

Three readers use the header. `Boot_ParseSubCPUTimestamp` (0xEF07E6) parses the "55" in the
filename as the table-data revision. `Seq_CopyResourcePtrs` (0xF862B5) loads `+0x14` as the
SSF script position for demo number 18 only. `FDemo_LinkedListSearch` reads `+0x18`. Demo
number 18 is also the Feature Demo's preset slot (`DemoSongPreset18` at 0x8E0000, decompressed
to RAM 0x69800 through `DemoSongPreset_PointerTable[18]`). Fields `+0x0C` and `+0x10` have no
reader.

### UI Objects (Program ROM)

The NAKA UI widget system manages all structured UI elements. See [UI Widget Types]({{ site.baseurl }}/ui-widget-types/) for full documentation of the 9 widget type bytes, structure layouts, and dispatch mechanism.

Viewable slot 0xFD holds 26 `ftdemo` screens (`ftdemo01`–`ftdemo48` with gaps). The script shows 22 of them (`ftdemo02`, `ftdemo03`, `ftdemo26` and `ftdemo40` are not used), plus three live screens:

- `ftdemo01`–`ftdemo10`, `ftdemo20`–`ftdemo26` and `ftdemo40`–`ftdemo48` — the slide screens, elements of Viewable slot 0xFD in `v10/maincpu/ui_widgets/naka_perf_style.c` (from :223)
- `Accordion` — accordion register display (container object with sub-objects: `Accordion1`, `Accordion2`, `AcAccordionTab`)
- `Drawbar` — digital drawbar organ display (container with `IvDrawbar1`, `IvDrawbar2`, `AcDrawbarName`)
- `Sdmixer` — sound/sequencer mixer display (container with child parameter structures)

The `ftdemoNN` names are **screens**, not bitmap names. Each is a `TtlScreen` (class 0x01600034) whose children are labels, boxes, lines, frames and language texts; across the slot there are 260 `Label`, 52 `Box`, 72 `Line` and 15 `AcLanguageText` elements. Only six slides show a BMP file, through the `VwUserBitmapByName` children `ftdemobmptop`, `ftdemobmp3D`, `ftdemobmpsoft`, `ftdemobmpcnv`, `ftdemobmpill` and `ftdemobmpend`, whose 8-byte keys are `"FTBMP01"` to `"FTBMP06"`.

The interactive objects (`Accordion`, `Drawbar`, `Sdmixer`) are **container objects** with child sub-objects, handler procedures, and rendering routines spanning hundreds of lines each:

| Object    | Handler                        | Code Location                                                                               |
|-----------|--------------------------------|---------------------------------------------------------------------------------------------|
| Accordion | `IvAccordionProc` (0xF7E250)   | `ui/drawbar_panel_ui.s:9248`; view slot 0xEB                                                |
| Drawbar   | `IvDrawbarProc` (0xF824C4)     | `ui/drawbar_panel_ui.s:15354`; view slot 0xEA                                               |
| Sdmixer   | (title TT_SDMIXER, 0x01A00008) | registered at `ui/drawbar_panel_ui.s:4550`; view slot 0x08 (`naka_technichord_part.c:1590`) |

### Object Dispatch Architecture

When `AcPresentationControlProc` (0xF8450B) processes a `<SHOW OBJ="...">` action:

1. The XML parser extracts the OBJ name string
2. The name is matched against the resource/object name table
3. For the slide screens (`ftdemoNN`): shows the screen; six of them draw a BMP through a `VwUserBitmapByName` child
4. For container objects (Accordion, Drawbar, Sdmixer): activates the interactive UI handler

The dispatch uses a **jump table at 0xE9F9B2** indexed by event type:
- Event codes 0x1C00002 through 0x1C0000C branch to specific handlers
- Each handler extracts its object pointer from the workspace and processes render/update/event actions

Handler call pattern:
```
AcPresentationControlProc:
    ; Calculate jump table offset from event code
    sub xbc, 0x1C00002
    add xbc, xbc               ; multiply by 2
    add xbc, 0xE9F9B2          ; jump table base
    ld bc, (xbc)               ; load handler pointer
    ; ... dispatch to handler
```

`AcPresentationBoxProc` (0xF842B4, `ui/drawbar_panel_ui.s:18322`) handles `EVT_CHECK_SELECTED` (0x1E0003C), `EVT_GET_STRING` (0x1E0003A), `EVT_INDEX_SELECT` (0x1C0001B), `EVT_END_SONG`, `EVT_START_SONG`, `EVT_SW_IN`, `EVT_SET_SELECTED`, `EVT_SELE_DRAW`, `EVT_DRAW` and `EVT_SHOW`. On its own switch's `EVT_SW_IN` (`PresBox_OK`, :18408-18424) it stores the entry index held in its view instance in `DEMO_ACTIVE_ENTRY` and calls `Demo_SelectEntry_ProcessSongList`. The routines at 0xFA6266 and 0xFA4409 are `GetViewInstance` and `InheritedProc`, not display routines.

---

## Demo Mode Handlers (Program ROM)

The Feature Demo uses a multi-mode event-driven architecture with separate handlers for different demo stages:

| Handler                   | Address  | Event               | Purpose                                        |
|---------------------------|----------|---------------------|------------------------------------------------|
| `DemoModeFunc`            | 0xF222CC | 0x1C00013           | Main demo mode dispatcher (init vs. run)       |
| `DemoMenuTtlFunc`         | 0xF222FD | —                   | Demo menu title (stub)                         |
| `DemoStyleTtlFunc`        | 0xF22300 | 0x1C00007/0x1C00013 | Style selection with encoder/direction input   |
| `DemoSoundTtlFunc`        | 0xF223CB | 0x1C00007/0x1C00013 | Sound selection with encoder/direction input   |
| `DemoRhyTtlFunc`          | 0xF22491 | 0x1C00007/0x1C00013 | Rhythm selection with encoder/direction input  |
| `DemoMode_Initialize`     | 0xF869E3 | —                   | First-time demo setup (voice save, audio init) |
| `DemoMode_Main_Operation` | 0xF8696F | —                   | Main demo playback loop                        |
| `AcDemoSongBoxProc`       | 0xF2CA5C | —                   | Song selection display widget                  |
| `DemoSongSelFunc`         | 0xF2CC16 | —                   | Song selection handler                         |
| `AcDemoMedleyDispBoxProc` | 0xF2D03C | —                   | Medley display widget                          |

The first five are in `demo/demo_routines.s`, `DemoMode_Initialize` and `DemoMode_Main_Operation` in `demo/file_demo_proc.s`, and the last three in `sequencer/sequencer_ui.s` (:3381, :3580, :4021).

Each selection handler (Style/Sound/Rhythm) has a dispatch table and supports three input types:
- **Encoder / Direction** switch groups (the disassembly's names): request one of the other two demo titles through `UI_PostModeChangeEvent` (0xF99490). Style goes to 0xE2 (TT_DEMOSOUND) or 0xE3 (TT_DEMORHY), sound to 0xE1 (TT_DEMOSTYLE) or 0xE3, and rhythm to 0xE1 or 0xE2. A press is ignored while a part is playing or the countdown is running.
- **Enter**: Calls shared handler at 0xF86A47

## Presentations Loaded from Disk

The ROM script is not the only source: the shipped v10 firmware also **loads presentations from floppy disc files**:

1. **`FEATURE.PRE` is picked up when a disk is inserted.** The disk-change event (Port D bit 6; SwbtWr code 0xA8, payload 0x41) is handled by `FileIO_ErrorCodeByteBlock`. If the Feature Presentation (title 0xE4) is on screen with nothing playing (`FDemo_MultiGuardCheck`) and the floppy's media type is 2 or 3, it calls `FileIO_CheckFileExists` on `"FEATURE .PRE"`. If the file exists, it posts `EVT_EXEC_PRESENTATION` (0x01C10007) with the name `"FEATURE "` (`demo/file_demo_proc.s:8844-8980`).

2. **A presentation is three files.** `ApPreControl` hands `EVT_EXEC_PRESENTATION` to `Seq_InitializeAndStart` (`demo/fdemotext_routines.s:2917`), which sets the presentation-loaded flag at DRAM `0x0251D8` to 1 and requests `EVT_READ_PRESENTATION_REQ`. `Seq_LoadDisplayResource` (:2959) opens `<name>.PRE` and reads its `<PRESENTATION>` block, `Seq_LoadNamedResource` (:3013) opens `<name>.ACT` and keeps the `<ACTION>` buffer at DRAM `0x0249D0`, and `FDemo_DisplayResourceData` (`demo/file_demo_proc.s:9`) opens `<name>.SQT`. All three open their file through `FileIO_OpenWithMode`, and each result is reported by one of the `EVT_READ_*` events above.

3. **Only demo number 18 uses the ROM script.** `Seq_CopyResourcePtrs` (`demo/fdemotext_routines.s:2883`) takes the script from the Table Data ROM (`Feature_Demo_XML`, through the metadata header's `+0x14`) when the demo number is 18, and otherwise uses the `.ACT` buffer at `0x0249D0`.

No disc holding a `FEATURE.PRE` is known, and it is not established whether such a disc was distributed. The [disc type signature table]({{ site.baseurl }}/system-update-discs/#disc-type-detection), which covers firmware updates, custom data and HDAE5000, plays no part here: the check above looks for the file by name.

---

## Bitmap Loading Chain

When `AcPresentationControlProc` processes a `<SHOW OBJ="ftdemo01">` action, the firmware:

1. **Looks up the object name** (`ftdemo01`) in the UI object table (`NAKA_UIObjectTable`, Viewable slot 0xFD, 478 entries; their names are in the parallel ResName table, slot 0x3FD). The entry is a `TtlScreen`; its bitmap is drawn by a `VwUserBitmapByName` child (`ftdemobmptop` for the globe).

2. **Takes the file key** stored inside that child: an 8-byte string, `.ftdemobmptop_file = "FTBMP01"` (`naka_perf_style.c:2179`).

3. **Looks up the filename** in the file entry index at `0x8CE01C` (Table Data ROM). The index stores 6 entries of 24 bytes each:

   ```c
   struct FeatureDemo_FileEntry {
       char   filename[12];  // "FTBMP01.BMP"
       uint32 reserved;      // 0
       uint32 data_ptr;      // ROM address (e.g. 0x880418)
       uint32 file_size;     // in bytes
   };
   ```

4. **Reads the BMP data** directly from the Table Data ROM using the pointer.

5. **Renders to VRAM** (0x1A0000–0x1DFFFF, 256KB) via `VwUserBitmapByNameProc` / `DrawBitmapFile`. The 8-bit BMP palette is loaded to the hardware palette register; pixel data is DMA-copied to the display.

The entire pipeline is **ROM-resident** — no disk I/O occurs for the Feature Demo. The `"FTBMP01"` filename in the `VwUserBitmapByName` element is a logical key, not a filesystem path.

---

## Button Sequence for Feature Demo

The correct button sequence to activate the Feature Demo from the home screen:

1. Press **DEMO** button → `8D38` transitions from `0x01` (normal) to `0xE0` (DEMONSTRATION menu appears)
2. Press **LEFT 4** (4th from top, CPL_SEG9) → `8D38` transitions to `0xE4` (FEATURE PRESENTATION sub-menu appears)
3. Press **LEFT 2** (CPL_SEG10, "Start the internal DEMO") → the presentation starts; `8D38` stays `0xE4` (TT_DEMOFEATURE) while it runs

### Demo Menu UI States

| State (`0x8D38`) | Description                                                                                             |
|------------------|---------------------------------------------------------------------------------------------------------|
| `0x01`           | Normal operation (home screen)                                                                          |
| `0xE0`           | DEMONSTRATION menu (top-level)                                                                          |
| `0xE4`           | FEATURE PRESENTATION sub-menu                                                                           |
| `0xE1`           | TT_DEMOSTYLE, the style demo (`0xE2` TT_DEMOSOUND and `0xE3` TT_DEMORHY are the sound and rhythm demos) |

---

## Two Distinct Activation Paths

> **Correction (October 2026).** `DemoMenu_BuildItemWorkspace` is not called by the demo timer or by `DemoMode_Main_Operation`. Its only callers are `MainMemDrawControl` and `FDemoText_ParseControlMessage` (title 0xEA), and its `0x82xx` values are LSW (panel-setting) ids, not a wrong workspace tag. "Path 2" below is therefore not a path into the presentation.

The March 2026 notes described two activation paths for the visual presentation, and their diagnosis of why it did not start in MAME rested on this distinction (see [MAME Emulation Status](#mame-emulation-status)).

### Path 1 — Manual (Physical Button Press): WORKS

This is the path triggered by a real user pressing a physical panel button while in the Feature Presentation sub-menu:

```
Physical button press
  → UIState_KeyScan_Dispatch
    → event 0x1C00038
      → GroupBoxProc (UI container widget handler)
        → GroupBoxProc_StartSSFPresentation (0xF9A273)
          → allocates workspace with tag 0xB80A
            → event 0x1C0001C
              → AcPresentCtrl_CheckSSFStart (0xF84625)
                → tag == 0xB80A? YES
                  → event 0x1C00006
                    → SSF XML parser starts
                      → FTBMP bitmaps rendered to VRAM
```

Key: `GroupBoxProc_StartSSFPresentation` builds the workspace bytes individually from stack-resident parameters, producing `workspace[0]=0x0A, workspace[1]=0xB8, workspace[2..3]=0x00` — the type-tag `0x0000B80A`. It then sends event `0x1C0001C` via **direct** `SendEvent` (`0xFA9660`).

### Path 2 — `MainMemDrawControl` → `DemoMenu_BuildItemWorkspace`: tag check fails

The March 2026 notes took this for the path of the automated demo sequencer; its actual caller is `MainMemDrawControl`:

```
MainMemDrawControl (0xF83BDA)
  → DemoMenu_BuildItemWorkspace (0xF83CEA)
    → allocates workspace with tag 0x82xx (from table at 0xE9F88C)
      → event 0x1C0001C (via ApPostEvent, queued)
        → AcPresentCtrl_CheckSSFStart (0xF84625)
          → tag == 0xB80A? NO (tag is 0x82xx)
            → event 0x1C00006 NEVER SENT
              → SSF parser never starts
                → FTBMP bitmaps never render
```

`DemoMenu_BuildItemWorkspace` reads a "part select" index `R` from DRAM `0x8D3A` and computes `workspace[0..3] = table[0xE9F88C + iz*2] + R*1024`. The table holds 16-bit values in the `0x82xx`-`0x82CC` range. This formula can **never** produce `0x0000B80A` for any byte `R`, because the difference `0xB80A - 0x82xx` is never divisible by 1024.

### Why This Path Cannot Trigger SSF

The workspace tag mismatch is architectural: `MainMemDrawControl` uses `DemoMenu_BuildItemWorkspace`, which creates records tagged with memory-drawbar LSW ids (`0x82xx`, `MemDraw_LswIdTable`), not with the SSF presentation's `0xB80A`. The SSF-correct tag is only produced by `GroupBoxProc_StartSSFPresentation`, which is only reached via the manual button-press path through event `0x1C00038`.

Additionally, the presentation-loaded flag at DRAM `0x0251D8` stays `0x0000`. That is expected: only `Seq_InitializeAndStart`, which starts a presentation from disk, sets it, and it stays 0 while the ROM presentation runs.

### SSF Gate State 0xE4

The gate table entry for state `0xE4` (FEATURE PRESENTATION sub-menu) contains the **unconditional marker** `0xFFFE`. This means any key press in state `0xE4` should broadcast event `0x1C00038` — the gate is wide open. This confirms the manual path would work if physical button input were simulated.

### Key Code Locations

| Function                            | ROM Address | Source File                                 | Purpose                                               |
|-------------------------------------|-------------|---------------------------------------------|-------------------------------------------------------|
| `GroupBoxProc_StartSSFPresentation` | 0xF9A273    | `presentation_sound_nav.s:33`               | Builds correct `0xB80A` workspace, sends direct event |
| `AcPresentCtrl_CheckSSFStart`       | 0xF84625    | `drawbar_panel_ui.s:18662`                  | Checks workspace tag, gates SSF start                 |
| `DemoMenu_BuildItemWorkspace`       | 0xF83CEA    | `drawbar_panel_ui.s:17734`                  | Builds `0x82xx` workspace (wrong tag for SSF)         |
| `MemDraw_LswIdTable`                | 0xE9F88C    | `ui_widgets/technichord_string_data.s:4106` | 15 LSW (panel-setting) ids, 0x8280–0x82CC             |

---

## MAME Emulation Status

> **Superseded (October 2026).** This status dates from March 2026. [#15878](https://github.com/mamedev/mame/pull/15878) (merged 2026-08-17) makes the Feature Presentation run in mainline MAME, without sound because the tone generator is not emulated: DEMO, LEFT 4, LEFT 2 starts it. The visual presentation does start. Its first slide, the Technics globe (FTBMP01), is drawn, so the `0xB80A` workspace-tag explanation in the March record below is wrong (kn7000_mame `notes/HANDOFF-kn5000-demo-playback.md`, §1–2). The four defects it fixed are the IC14 rhythm-ROM dump (address lines A19 and A21 swapped), the TMP94C241 16-bit timer interrupts, the IC21 backup SRAM (now NVRAM) and INT0 re-assertion under micro-DMA; none of them is the workspace-tag mechanism blamed below. In the kn7000_mame overlay build (2026-08-15), one song plays to a correct STOP at about 139 s and nothing follows. The demo countdown at 0x0D2F is armed once and not re-armed. Whether anything should follow is open: the owner describes the presentation as one continuous piece. What follows records the March 2026 investigation.

**Partially working (March 2026).** The Demo Timer System (song cycling) works correctly in MAME — the timer counts down, songs cycle, and `PlaySong` returns after ~16 seconds of SwbtWr buffer processing. The SSF Visual Presentation (FTBMP bitmap rendering) does not trigger because the automated demo path uses workspace tags (`0x82xx`) that fail the `0xB80A` check in `AcPresentCtrl_CheckSSFStart`.

**Root cause summary:**
- `MainMemDrawControl`, through `DemoMenu_BuildItemWorkspace`, creates workspaces with `0x82xx` tags
- The SSF presentation requires workspace tag `0xB80A`, which is only created by the manual button-press path (`GroupBoxProc_StartSSFPresentation`)
- The presentation-loaded flag at DRAM `0x0251D8` stays `0x0000`, which is expected: only a presentation started from disk sets it
- The March traces read DRAM hex `0x10420` as the sequencer-part word ("0xFFFF, all parts active"). That is the wrong location: the part word the firmware tests is `SEQ_ACTIVE_PARTS`, DRAM 0x28B4 (10420 decimal), and its value during the demo has not been measured. An August 2026 write tap found that 0x10420 is written only in one setup burst, and that all voices are released at the stop, so the waveform-ROM explanation does not hold.

**Two independent bugs remain:**
1. **Song cycling stuck:** Sequencer parts never complete, preventing the timer from resetting for the next song
2. **SSF never triggers in automated mode:** The automated path fundamentally cannot produce the correct workspace tag; only the manual button-press path through `GroupBoxProc_StartSSFPresentation` creates tag `0xB80A`

> ⚠ The Lua script that produced the traces below (`ftdemo_v3.lua`, automated navigation from
> boot to Feature Demo activation) was never committed and no longer exists. Anyone re-running
> this analysis has to rebuild it; the instrumentation constraints it hit are recorded under
> *Instrumentation pitfalls* below so that rebuild does not repeat them.

---

---

## Workspace Allocation — Concept Explained

Before describing the root cause, it helps to understand what "allocating a workspace" means in the KN5000 firmware's event system.

The KN5000 event system (centered on `SendEvent` at `0xFA9660` and `ApPostEvent` at `0xFA9D58`) passes three registers as event parameters: XWA (target), XBC (event code), and XDE (data/parameter). For events that need to carry more than a single 32-bit value, the firmware uses a **workspace** pattern:

1. A small block of memory (typically 12 bytes) is allocated from the firmware heap by calling `Malloc` (the workspace allocator). The returned pointer is stored in DRAM (usually somewhere in `0x000000–0x0FFFFF`).
2. The workspace fields are populated: the first 4 bytes act as a **type-tag** (a magic 32-bit value identifying the kind of data the workspace carries), followed by payload fields.
3. The workspace **pointer** is passed as XDE when calling `SendEvent` or `ApPostEvent`.
4. The receiving handler reads the workspace via the pointer, checks the type-tag, and processes the payload.

Think of the workspace as a small heap-allocated struct passed by pointer via the event system.

Because workspaces are allocated from a pool in DRAM and may be reused, it is critical that the event fires and the workspace is consumed **before** the memory is overwritten by another allocation or unrelated code. This is why the two distinct event-dispatch paths (queued vs. direct) produce different results.

---

## The Two Paths in Detail

Two different code paths send event `0x1C0001C` to `AcPresentationControlProc`:

#### Path 1 — `DemoMenu_BuildItemWorkspace` (0xF83CEA) — QUEUED, WRONG TAG

Its callers are `MainMemDrawControl` and, on the drawbar screen (title 0xEA), `FDemoText_ParseControlMessage`. Each call sends one of the 15 memory-drawbar panel settings (`MemDraw_LswIdTable`) as an `EVT_LSW_DATA` record. For that item it:

1. Allocates a 12-byte workspace via the heap allocator (`FF0E80`).
2. Reads the "part select" index `R` from DRAM address `0x8D3A` via `GetPartSelect()`.
3. Computes `workspace[0..3] = table[0xE9F88C + iz*2] + R*1024`.
   The table (at ROM `0xE9F88C`) holds 16-bit values all in the range `0x82xx–0x82CC`.
   **This formula can never produce the value `0x0000B80A`** for any byte `R`, because the difference `0xB80A − 0x82xx` is never divisible by 1024.
4. Posts event `0x1C0001C` via `ApPostEvent` (`FA9D58`) — a **queued** (deferred) dispatch.

When this queued event eventually reaches `AcPresentationControlProc` (`0xF8450B`), it is handled by `AcPresentCtrl_CheckSSFStart` (`0xF84625`), which checks `*(XDE) == 0xB80A`. The check **always fails** because the workspace type-tag is never `0xB80A`.

#### Path 2 — `GroupBoxProc_StartSSFPresentation` (0xF9A273) — DIRECT, CORRECT TAG

`GroupBoxProc` (`~0xF998xx`) is a UI container widget handler. Its event dispatch table includes:

```
cp xde, 0x1C00038
jrl z, GroupBoxProc_StartSSFPresentation    ; direct entry

cp xde, 0x1C00030
jrl z, GroupBoxProc_Ev1C00030              ; via show-item handler
```

`GroupBoxProc_StartSSFPresentation` (0xF9A273) builds the workspace bytes **individually** from stack-resident parameters, producing `workspace[0]=0x0A, workspace[1]=0xB8, workspace[2..3]=0x00` — the type-tag `0x0000B80A`. It then sends event `0x1C0001C` via **direct** `SendEvent` (`FA9660`).

When this event reaches `AcPresentCtrl_CheckSSFStart`, the type-tag check **passes**, and the handler sends event `0x1C00006` — which starts SSF presentation parsing, loads the XML from ROM, and begins rendering FTBMP images.

#### Root cause summary

March 2026, superseded (see [MAME Emulation Status](#mame-emulation-status)): the Feature Demo has two distinct activation paths with fundamentally different workspace tag behavior (see "Two Distinct Activation Paths" above):

- **Manual path** (physical button press in state `0xE4`): `UIState_KeyScan_Dispatch` → event `0x1C00038` → `GroupBoxProc_StartSSFPresentation` → workspace tag `0xB80A` → `AcPresentCtrl_CheckSSFStart` passes → SSF starts
- **`MainMemDrawControl` path** (not the demo timer): `DemoMenu_BuildItemWorkspace` → workspace tag `0x82xx` → `AcPresentCtrl_CheckSSFStart` fails → SSF never starts

The `MainMemDrawControl` path cannot produce the correct workspace tag by design. The `0x82xx` tags from the table at `0xE9F88C` serve a different purpose (memory-drawbar panel settings, `MemDraw_LswIdTable`). Only `GroupBoxProc_StartSSFPresentation` constructs the `0xB80A` tag needed for SSF, and it is only reachable through the manual button-press event chain.

### Call-chain overview

```
Feature Demo activated
  → DemoModeFunc (0xF222CC)  [event 0x1C00013, XDE=1]
    → DemoMode_Initialize (0xF869E3)
    → DemoMode_Main_Operation (0xF8696F)
      → jp Seq_StartMainControl
        (DemoMenu_BuildItemWorkspace is not called on this path)

Separately, MainMemDrawControl (0xF83BDA)
  → DemoMenu_BuildItemWorkspace (0xF83CEA)  [one call per memory-drawbar item]
    → ApPostEvent (0xFA9D58)
      → AcPresentCtrl_CheckSSFStart (0xF84625)
        *(workspace) == 0xB80A?  NO → SSF never starts

Expected (but missing in MAME):
  GroupBoxProc receives event 0x1C00038
    → GroupBoxProc_StartSSFPresentation (0xF9A273)
      → SendEvent (0xFA9660) with workspace tag 0x0000B80A
        → AcPresentCtrl_CheckSSFStart
          *(workspace) == 0xB80A?  YES
            → sends 0x1C00006 → SSF parser starts → FTBMP images rendered
```

### Why GroupBoxProc doesn't receive 0x1C00038 in MAME

March 2026, superseded (see [MAME Emulation Status](#mame-emulation-status)): `UIState_KeyScan_Dispatch` IS called during boot initialization — approximately 900+ times — but all calls occur when DRAM `0x8D38 = 0x00`. This maps to ROM table entry[0] at `0xE014CE`, which contains the sentinel array `{0xFFFF}` (immediately terminating). Every boot-time call returns immediately with no event sent.

The dispatcher mechanism consists of:
- **FDB3D1** (event buffer writer): fills a circular buffer at DRAM `0xBD3C` with 4-byte entries encoding chain index (`C080`) and param (`C07D`)
- **FDB328/FDB32E** (main dispatcher loop): reads entries from `0xBD3C`, selects handler chains from table `EE7CA7`, calls ALL functions in the selected chain

During boot initialization, FDB3D1 sweeps all chain indices `0x00`→`0x9A` with 24 C07D params each (~4,608 total events). `UIState_KeyScan_Dispatch` is invoked for every event whose chain (at `EE7CA7[C080*4]`) includes it. At boot time, `8D38=0x00` → `table[0]={0xFFFF}` → returns early every time.

After boot stabilizes (`8D38` changes to `0x01`), the event buffer at `0xBD3C` drains and FDB3D1 is never called again — because no user input occurs in MAME's automated test run. With an empty buffer, the dispatcher has nothing to process, so `UIState_KeyScan_Dispatch` is never invoked again.

**Critically, the logic would work correctly with user input:** Table entry[1] (at ROM `0xE014D0`, used when `8D38=0x01`) contains a 16-bit array with `0x7002` at index [79] (ROM address `0xE0156E`). The comparison key is `(C080 << 8) | C07D = (0x70 << 8) | 0x02 = 0x7002`. So if `UIState_KeyScan_Dispatch` were called post-boot with chain `0x70` and param `0x02`, it WOULD find a match and send event `0x1C00038`.

**The real hardware** presumably triggers FDB3D1 via user button presses or directional encoder navigation, which posts events to the `0xBD3C` buffer. In MAME's automated Feature Demo test mode, no such input is simulated. The Feature Demo would work on real hardware if a user navigated to it with actual button input.

### Ruled out as blocking points

| Issue | Ruling |
|-------|--------|
| Audio initialization delay | `Audio_WaitForReady` has a 61,440-iteration timeout — exits gracefully even if SubCPU doesn't respond; not a hard block |
| VRAM display mode | VRAM writes do occur; display mode itself is not the primary blocker |
| XML parser state | SSF parser never starts because `0x1C00006` is never sent |
| `DemoMode_Main_Operation` loop | Expected behaviour (`jp Seq_StartMainControl`); not a hang |

### Floppy drive type

The real hardware uses **1.44 MB HD (high-density)** drives, confirmed by the FDC's format
configuration (1440K, 18 sectors/track, 80 tracks) and by `update_disc.img`: FAT12, OEM-ID
`"Technics"`, 2880 sectors, 18 sectors/track, 2 heads. Mainline MAME's `kn5000_floppies` slot
offers only `35hd` (since [#16415](https://github.com/mamedev/mame/pull/16415)). The kn7000_mame
overlay also offers `35dd`. Both default `fdc:0` to **`35hd`**.

### How event 0x1C00038 is generated — detailed analysis

#### `UIState_KeyScan_Dispatch` — the event sender

The function `UIState_KeyScan_Dispatch` (ROM `0xF98697`) is the code that sends event `0x1C00038`. It is **not called directly** — instead, it appears as a function-pointer entry in many UI widget handler chains (in the SwbtWr bank-2 listener lists such as `SwbtB2_Code00_Listeners`, `SwbtB2_Code01_Listeners` and `SwbtB2_Code02_Listeners`, formerly labelled `UIState_HandlerTable_WithProbe`, `UIState_HandlerTable_Standard` and `UIState_HandlerTable_Compact`). When any widget using one of these handler chains processes certain events (typically user interaction events), it walks its handler chain and calls `UIState_KeyScan_Dispatch`.

`UIState_KeyScan_Dispatch` logic:

1. Calls `0xEF0797` to check bit 7 of DRAM `0x0406`. This flag is SET once during boot by `Boot_DisplayScreen`, through `Boot_SetConfigFlag7` (called at `v10/maincpu/kn5000_v10_program.s:1435`; the `set 7` is at :1553). It is cleared by `Boot_ClearConfigFlag7` at the start of `Boot_InitPeripherals` (:1323). It should be set throughout normal operation, so this check passes.
2. Reads a byte from DRAM `0x8D38` (an array selector index `R`).
3. Reads a ROM pointer `P = ROM[0xE01F80 + R×4]`. The pointer `P` points to a ROM array of 16-bit state values ending in `0xFFFF`.
4. Walks the array at `P`, comparing each entry to the current selection state built from DRAM bytes `0xC07D` and `0xC080` (packed as `(0xC080 << 8) | 0xC07D`).
5. If a match is found (or if the first array entry is `0xFFFE`, indicating "always send"), builds a 32-bit XDE parameter from `0xC07D`–`0xC080` and sends event `0x1C00038` to `XWA=0xFFFFFFFF` via `FA9945`.

#### `FA9945` (`EventDispatch_Direct`) — posts the key event

`FA9945` (`EventDispatch_Direct`) is called by `UIState_KeyScan_Dispatch` to post the key event. `0x02BC34` is not a routing table but the event queue that `FA9752` fills (below; see also [Event Queue]({{ site.baseurl }}/event-codes/#event-queue-postevent)). If the queue is empty (read index `0x02EC34` equal to write index `0x02EC36`), it posts the event through `ApPostEvent` (`FA9D58`). Otherwise it first cancels every queued `0x1C00038` whose upper 16 bits match the new event's, by overwriting its event code with `EVT_NONE`, merges their low bytes into the new event and then posts it (`ui/ui_widget_defs.s:18139-18257`). It forwards nothing to a registered handler: `GetEvent` replaces the broadcast target `0xFFFFFFFF` with the current target when it dequeues the event (`ui/ui_widget_defs.s:17959-17965`).

#### `FA9752` — the event queue writer (`PostEvent`)

`FA9752` (labeled `PostEvent` in the disassembly) **inserts events into a circular event queue** at DRAM `0x02BC34` (head/tail pointers at `0x02EC34`/`0x02EC36`). Each 12-byte queue entry holds:

```
entry[0..3]  = self pointer (XWA) — object ID posting the event
entry[4..7]  = event code (XBC)
entry[8..11] = param (XDE)
```

The event routing for `0x1C00038` therefore works through the standard event queue. `UIState_KeyScan_Dispatch` acts as the PRODUCER: it checks state bytes, then pushes `0x1C00038` + packed XDE into the queue via `FA9945`. The CONSUMER is whichever widget handler receives the queued event — presumably GroupBoxProc, once it has received its own event setup during initialization.

For GroupBoxProc to receive the queued `0x1C00038`, it must be the current target when `GetEvent` dequeues the event, or be reached from the current target's handler.

### Instrumentation pitfalls

Anything that instruments this path with MAME Lua autoboot scripts hits the same four traps.

**MAME Lua API constraints:**
- `install_read_tap` requires **word-aligned ranges** (even→odd address pair, e.g., `0xF98696-0xF98697`)
- Notifier handles from `add_machine_frame_notifier` / `add_machine_stop_notifier` must be **saved to outer-scope variables** to prevent garbage collection — otherwise callbacks silently stop
- **Critical conflict:** `emu.add_machine_frame_notifier` + `install_read_tap` are mutually exclusive — when both are active, read taps stop firing entirely

**The `0xF9A272` false positive.** A read tap placed at `0xF9A272-0xF9A273` to catch
`GroupBoxProc_StartSSFPresentation` fires on **every** call to `0xFA9660` instead. The
instruction at `0xF9A26F` is `call 0xfa9660`, encoded `1D 60 96 FA`; its third word occupies
`0xF9A272-0xF9A273`, so the tap sees an instruction fetch, not an execution of the SSF entry
point. A conclusion that "the Feature Demo works" drawn from hits on that tap is an artefact.
The accompanying "FTBMP01.BMP in VRAM" sighting comes from boot initialisation, not the demo.

**What the instrumented path actually shows.** `UIState_KeyScan_Dispatch` is entered around 900
times, all during boot with `8D38 = 0x00`, and the `0xEF0797` pre-condition (bit 7 of DRAM
`0x0406`) blocks every one of them in the emulation context. `FA9945` never dispatches
`0x1C00038`. DRAM `0x8D38` reads `0x00` at ~12 s, `0xEF` at ~25 s and `0x01` at ~37 s.

### Observed behaviour

March 2026, superseded (see [MAME Emulation Status](#mame-emulation-status)): pressing DEMO in state `0xE4` transitions directly to `0x01` (normal mode), exiting the demo menu entirely. It does NOT trigger SSF. Pressing LEFT 2 starts the demo timer (song cycling) but does NOT trigger SSF visual presentation. The presentation-loaded flag at DRAM `0x0251D8` remains `0x0000` throughout, which is expected: only a presentation started from disk sets it.

**Two independent bugs remain:**
1. **Song cycling stuck:** Sequencer parts never complete, preventing the timer from resetting for the next song
2. **SSF never triggers in automated mode:** The `MainMemDrawControl` path through `DemoMenu_BuildItemWorkspace` creates workspace tags in the `0x82xx` range (from table at `0xE9F88C`), which always fail the `0xB80A` check in `AcPresentCtrl_CheckSSFStart`. Only the manual button-press path through `GroupBoxProc_StartSSFPresentation` (0xF9A273, in `presentation_sound_nav.s:33`) can produce the correct tag

---

## SSF Presentation Gate Table (`SSF_PresentationGateTable`, 0xE01F80)

The firmware uses a 256-entry ROM lookup table at **0xE01F80** to control which UI states allow the Feature Demo to be triggered. This table is the gating mechanism that determines whether pressing a panel button sends event `0x1C00038` — the event that ultimately starts the SSF presentation.

### Structure

The table occupies 1024 bytes (0xE01F80–0xE02380) and consists of 256 `.long` (32-bit little-endian) pointer entries. Each pointer points to a **state-value array** — a list of 16-bit values terminated by `0xFFFF` — stored elsewhere in the ROM (0xE014CE–0xE01F7E).

```
SSF_PresentationGateTable:
    .long SSF_GateStates_Mode00    ; entry[0x00] — boot/init state
    .long SSF_GateStates_Mode01    ; entry[0x01] — normal operation
    .long SSF_GateStates_Mode02    ; entry[0x02]
    ...                   ; (256 entries total)
    .long SSF_GateStates_ModeFF    ; entry[0xFF]
```

### How It Works

1. **Index selection:** The current UI mode is stored as a byte at DRAM address `0x8D38`. The getter function at `0xF0618F` loads this value. Common values include:
   - `0x00` — boot/initialization
   - `0x01` — normal operation
   - `0xE0` — DEMONSTRATION menu
   - `0xE4` — FEATURE PRESENTATION sub-menu

2. **Table lookup:** `UIState_KeyScan_Dispatch` (0xF98697) reads the byte `R` from `0x8D38` and loads the pointer `P = SSF_PresentationGateTable[R]`.

3. **State matching:** The 16-bit array at `P` is checked against the current panel selection state (packed from DRAM bytes `0xC07D` and `0xC080` as `(C080 << 8) | C07D`):
   - `{0xFFFE}` — **always match**: the event fires unconditionally
   - `{0xFFFF}` — **never match**: the entry is disabled, no event sent
   - `{val1, val2, ..., 0xFFFF}` — **conditional**: each value is compared to the packed state; if any matches, the event fires

4. **Event dispatch:** When a match is found, `UIState_KeyScan_Dispatch` sends event `0x1C00038` via `EventDispatch_Direct` (`0xFA9945`), which posts it to the event queue; `GetEvent` later delivers it to the current target.

### Role in Feature Demo Activation

The gate table ensures the Feature Demo can only be activated from specific UI states. During boot (`0x8D38 = 0x00`), `entry[0]` points to `{0xFFFF}` — immediately terminating, blocking any SSF events. After boot stabilizes and the user navigates to the DEMONSTRATION menu, `0x8D38` transitions to values whose table entries contain valid state arrays.

In practice the presentation is started from the FEATURE PRESENTATION sub-menu (state `0xE4`) by LEFT 2. Pressing DEMO there leaves the demo menu (see *Observed behaviour* above).

The gate table's primary role appears to be **gating hardware button events** — when the event buffer dispatcher (`0xFDB328`) processes button presses from the key scanner, it invokes `UIState_KeyScan_Dispatch` as part of widget handler chains. The table then determines whether those hardware button events should propagate as SSF trigger events based on the current UI mode.

### State-Value Arrays

Each gate table entry points to a **state-value array** — a sequence of 16-bit little-endian values terminated by `0xFFFF`. Each value encodes `(chain_index << 8) | param`, matching the packed panel selection state from DRAM bytes `0xC080` (chain index) and `0xC07D` (param).

Known arrays in ROM range 0xE014CE–0xE01F7E:

| Label                       | Address  | Entries | Content                                                    | Used by mode     |
|-----------------------------|----------|---------|------------------------------------------------------------|------------------|
| `SSF_GateStates_Mode00`     | 0xE014CE | 0       | `{0xFFFF}` — disabled                                      | 0x00 (boot/init) |
| `SSF_GateStates_Mode01`     | 0xE014D0 | 86      | Chains 0x00–0x18, 0x43, 0x48, 0x70, 0x72, 0x80, 0x91, 0x98 | 0x01 (normal)    |
| `SSF_GateStates_Mode02`     | 0xE0157E | 0       | `{0xFFFF}` — disabled                                      | 0x02             |
| `SSF_GateStates_Mode03`     | 0xE01580 | 228     | Chains 0x00–0x18, 0x43, 0x72, 0x98                         | 0x03             |
| `SSF_GateStates_Mode04`     | 0xE0174A | 1       | Chain 0x91, param 0x00                                     | 0x04             |
| **`SSF_GateStates_Mode05`** | 0xE0174E | 14      | Chain 0x92, params 0x00–0x0D                               | **0x05**         |
| `SSF_GateStates_Mode06`     | 0xE0176C | 14      | Chain 0x92, params 0x00–0x0D                               | 0x06             |
| `SSF_GateStates_ModeE4`     | 0xE01EA0 | —       | `{0xFFFE}` — unconditional                                 | 0xE4             |

The `SSF_GateStates_Mode05` array (0xE0174E) is a representative example: when the UI is in mode 5 (`0x8D38 = 0x05`), the SSF event fires only if the current panel state has chain index `0x92` and a param value between `0x00` and `0x0D`. All other panel states are blocked.

### Source Location

- **Table definition:** `v10/maincpu/sequencer/ssf_gate_states.s:1236`, label `SSF_PresentationGateTable` (0xE01F80)
- **Getter function:** `SeMenu_LoadRawAddr` — loads index from DRAM 0x8D38
- **Consumer function:** `UIState_KeyScan_Dispatch` (0xF98697) — reads and evaluates the table
- **State-value arrays:** ROM range 0xE014CE–0xE01F7E (pointed to by table entries)
- **Example array:** `SSF_GateStates_Mode05` (0xE0174E) — 14-entry filter for UI mode 5

---

## Interpretation

The XML presentation system — with its `EXEC` tag, `SONG` playback, `IMG` display, rich tag vocabulary, and event-driven architecture — was almost certainly designed to be more flexible than the one script the ROM carries (the Feature Demo).

The most likely explanation: **Technics designed a general-purpose presentation engine**, perhaps intended for:

- **Dealer demonstration discs** — scripted presentations showcasing the keyboard's features at retail stores
- **Educational materials** — step-by-step tutorials loaded from floppy
- **Trade show content** — automated demonstrations for NAMM or music trade events

The infrastructure was built, and the shipped firmware can also load presentations from disk: a disc holding `FEATURE.PRE` and its `.ACT`/`.SQT` companions is picked up from the Feature Presentation screen (see [Presentations Loaded from Disk](#presentations-loaded-from-disk)). The ROM itself carries only the one Feature Demo script.

The user's memory of "feature presentation discs" may refer to discs of this kind, or to the commercially-sold style/song demo discs that showcased the keyboard's capabilities using standard MIDI file playback.

---

## Demo Timer State Machine

The Feature Demo uses a timer-driven state machine to sequence through demo items. The timer variable is at DRAM address 3375 (0xD2F).

### Timer-Driven Entry Point

`Demo_SelectEntry_TimerTick` (0xF86BE4, `demo/file_demo_proc.s:758`) is called from the main loop timer. Each tick:

1. Checks control panel state (`Demo_SelectEntry_CheckCPanel`)
2. Decrements the countdown at address 3375
3. At count=10 (`0x0A`): loads the next song pattern and starts playback
4. At count=3: calls `Demo_SelectEntry_StartPlayback` to begin accompaniment
5. At count=1: writes 0x85 to DRAM 0x2966, which arms the sequencer transport

### Song Processing Flow

`Demo_SelectEntry_ProcessSongList` (0xF86B7C, `demo/file_demo_proc.s:721`) manages song selection:

1. If no sequencer part is playing (`SEQ_ACTIVE_PARTS`, DRAM 10420 = 0x28B4, is 0), restarts the countdown
2. Checks bit 3 of address 10413 for auto-play vs manual mode
3. In auto-play: compares current song index (10404) with target (4439)
4. Calls `Demo_WaitForDisplayBit` — busy-wait until bit 2 of address 1056 (0x420, sequencer transport running) clears, with 0xFFFFFF timeout
5. Calls `Banner_Loop_Check` — sends note-off commands (status 0xD3) to all 16 channels, cleaning up active notes
6. Increments song index at address 4440 and loops

### Transport Wait

`Demo_WaitForDisplayBit` (0xF86F2E) is a timeout-protected busy-wait:

```
Loop 0xFFFFFF times:
    If bit 2 of DRAM[0x420] == 0: return (transport stopped)
Return after timeout
```

It waits for the sequencer transport to stop before `Banner_Loop_Check` silences the channels. The timeout prevents a hard hang if the transport never stops. (Despite its name, the routine does not test the display: bit 2 of 0x420 marks the transport running, and `INTTR4_HANDLER` and `AccPlayMode_Dispatch` test the same bit.)

### Demo Timer Behavior in MAME

When the timer reaches 10, `Demo_SelectEntry_PlaySong` is called. It calls `SwbtWr_ReinitBothBanks`, which runs the SwbtWr dispatch loop inline, so the main loop and the countdown wait until every buffered parameter-change event has been handed to its listeners (see [SwbtWr Event Dispatch]({{ site.baseurl }}/swbwr-tone-init/)). In the March 2026 MAME build that took about 16 seconds; in the August 2026 kn7000_mame overlay build the countdown goes from 10 to 9 in about half a second (kn7000_mame `notes/p9-countdown-2026-08-15.log`).

`PlaySong` then sets `DRAM[0x8F4E]` to `0x06` and returns, and the countdown resumes from 10. In the overlay build one song plays to a correct STOP at about 139 s and the countdown is not re-armed, so nothing follows (see [MAME Emulation Status](#mame-emulation-status)).

**Note:** Neither duration need match real hardware, where the tone generator writes go to hardware registers rather than through HLE. See [Feature Demo Timer Behaviour]({{ site.baseurl }}/feature-demo-investigation-2026-03-09/) for both measurements.

The sequencer tick counters are driven by **INTTR4** (`INTTR4_HANDLER`, 0xEF0E21). Boot gives INTTR4 priority 3, and the INTTR5 vector holds `Empty_Handler`. TREG5 sets the period (T4MOD clears the counter on a TREG5 match), and the TREG4 = 1 match raises INTTR4 once per period. MAME's old `timer_16bits` code in `tmp94c241.cpp` never raised it: it processed a compare match only when the matching `T4FFCR` flip-flop bit was set, and the firmware writes `T4FFCR` = 0. It also raised the lower flag (`0x08`) for a TREG5 match. Both are fixed upstream in [#15878](https://github.com/mamedev/mame/pull/15878). See [Timer 4/5 and the Sequencer Clock]({{ site.baseurl }}/feature-demo-timer-bug-2026-03-09/).

### Key DRAM Addresses

| Address        | Description                                                    |
|----------------|----------------------------------------------------------------|
| 1056 (0x420)   | Sequencer transport lane (bit 2 = running)                     |
| 3375 (0xD2F)   | Demo timer countdown value                                     |
| 3379 (0xD33)   | Debounce counter                                               |
| 4439 (0x1157)  | Target song index                                              |
| 4440 (0x1158)  | Current song index                                             |
| 10404 (0x28A4) | Active demo entry index                                        |
| 10413 (0x28AD) | Demo control flags (bit 3 = auto-play)                         |
| 10420 (0x28B4) | `SEQ_ACTIVE_PARTS`: one bit per sequencer part that is playing |
| 36148 (0x8D34) | UI state byte                                                  |
| 36152 (0x8D38) | UI sub-state byte (0xE4 = Feature Presentation)                |
| 36686 (0x8F4E) | Playback state flag                                            |

In the source (since 2026-10-03, `shared/ram_variables.s`): `DEMO_TIMER_COUNTDOWN` (0xD2F), `DEMO_TARGET_SONG`
(0x1157), `DEMO_CURRENT_SONG` (0x1158), `DEMO_ACTIVE_ENTRY` (0x28A4), `DEMO_CONTROL_FLAGS` (0x28AD); the
"UI state" and "UI sub-state" bytes are the current mode and the active title (`CURRENT_MODE` 0x8D34,
`ACTIVE_TITLE` 0x8D38 -- the values 0x01 / 0xE0 / 0xE4 are TT_NORMAL / TT_DEMOMENU / TT_DEMOFEATURE).

## Related Pages

- [UI Framework]({{ site.baseurl }}/ui-framework/) — Widget system and event handling
- [System Update Discs]({{ site.baseurl }}/system-update-discs/) — Floppy disc format and update process
- [Storage Subsystem]({{ site.baseurl }}/storage-subsystem/) — Storage architecture overview
- [FDC Subsystem]({{ site.baseurl }}/fdc-subsystem/) — Floppy disk controller handlers
- [Image Gallery]({{ site.baseurl }}/image-gallery/) — Extracted graphics including FTBMP images

---


