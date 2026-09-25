---
layout: page
title: Feature Demo & Presentation System
permalink: /feature-demo/
---

# Feature Demo & Presentation System

The KN5000 firmware contains a **full XML-based presentation scripting system** used for the built-in Feature Demo. This system is significantly more sophisticated than a simple slideshow — it includes an XML parser, an event-driven presentation controller, and a rich tag vocabulary suggesting it was designed for general-purpose use.

## SSF Presentation Format

### Files in Table Data ROM

Two SSF (presumably "Show/Script/Sequence File") files are embedded in the Table Data ROM:

| File | ROM Address | Purpose |
|------|-------------|---------|
| `hkst_55.ssf` | 0x87FFF0 (metadata), 0x88000E (XML data) | Feature Demo presentation script |
| `hkt_87.ssf` | Near boot vectors (table_data.asm line 3855) | Unknown — possibly a second presentation |

**Source file:** `../../kn5000-roms-disasm/table_data/includes/hkst_55.ssf`

### XML Format

The Feature Demo script is real XML with a defined structure:

```xml
<ACTION>
  <ACT NO=1><SHOW OBJ="ftdemo01"></ACT>
  <ACT NO=2><SHOW OBJ="ftdemo04"></ACT>
  <ACT NO=3><SHOW OBJ="ftdemo05"></ACT>
  ...
  <ACT NO=27><SHOW OBJ="ftdemo48"></ACT>
</ACTION>
```

The script defines 27 sequential actions, each referencing a named UI object. Objects include `ftdemo01`–`ftdemo48` plus instrument-specific displays like `Accordion`, `Drawbar`, and `Sdmixer`.

---

## XML Tag Vocabulary

The firmware carries a complete XML tag name table in the Program ROM. (The tag strings sit in a data region that the split disassembly emits as raw bytes, so there is no source line to cite.)

### Structure Tags

| Tag | Close Tag | Purpose |
|-----|-----------|---------|
| `PRESENTATION` | `/PRESENTATION` | Top-level presentation wrapper |
| `ACTION` | `/ACTION` | Action sequence container |
| `ACT` | `/ACT` | Individual action step (with `NO=` attribute) |

### Content Tags

| Tag | Close Tag | Purpose |
|-----|-----------|---------|
| `SHOW` | — | Show/display a named UI object |
| `IMG` | — | Display an image |
| `SONG` | — | Play a song or MIDI sequence |
| `FONT` | `/FONT` | Font selection for text rendering |
| `CENTER` | `/CENTER` | Text centering |
| `BR` | — | Line break |

### Attribute Tags

| Tag | Purpose |
|-----|---------|
| `SRC` | Source reference (file/resource) |
| `NAME` | Name identifier |

### Command Tags

| Tag | Purpose |
|-----|---------|
| **`EXEC`** | **Execute a command or routine** |

The `EXEC` tag is particularly notable — it strongly suggests the presentation format was designed to support executing code or commands as part of scripted presentations, going beyond simple display and playback.

---

## Presentation Handler Functions

The firmware implements a full event-driven presentation controller:

### Core Handlers

| Function | ROM Address | Line | Purpose |
|----------|-------------|------|---------|
| `AcFdemoScreenProc` | 0xF84149 | 308910 | Feature Demo screen handler |
| `AcPresentationBoxProc` | 0xF842B4 | 309070 | Presentation display widget |
| `AcPresentationControlProc` | 0xF8450B | 309287 | Main presentation controller |
| `IvDemofeature1Proc` | — | ~310702 | Feature Demo event handler 1 |
| `IvDemofeature2Proc` | — | ~310736 | Feature Demo event handler 2 |

`AcPresentationControlProc` is the main dispatch routine. It uses a jump table at `0xE9F9B2` to handle different presentation states/events.

### Event System

The firmware defines dedicated events for presentation processing:

| Event Constant | Line | Purpose |
|----------------|------|---------|
| `EV_READPRESENTATION` | 78181 | Read and parse a presentation file |
| `EV_READACTION` | 78180 | Read and process an action step |
| `EV_READSONG` | 78178 | Load and play a song reference |

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

48 named UI objects are referenced in the Program ROM:

- `ftdemo01` through `ftdemo48` — bitmap resource names (aligned strings at lines 6240-6648)
- `Accordion` — accordion register display (container object with sub-objects: `Accordion1`, `Accordion2`, `AcAccordionTab`)
- `Drawbar` — digital drawbar organ display (container with `IvDrawbar1`, `IvDrawbar2`, `AcDrawbarName`)
- `Sdmixer` — sound/sequencer mixer display (container with child parameter structures)

The `ftdemo01`–`ftdemo48` names are **bitmap resource references**, not complex widget structures. They are simple filename strings (e.g., `aligned_string "ftdemo43"`) that identify image resources loaded during the demo.

The interactive objects (`Accordion`, `Drawbar`, `Sdmixer`) are **container objects** with child sub-objects, handler procedures, and rendering routines spanning hundreds of lines each:

| Object | Handler | Code Location |
|--------|---------|---------------|
| Accordion | `IvAccordionProc` | Lines 257980-258362 |
| Drawbar | `IvDrawbarProc` | Lines 262262-264436 |
| Sdmixer | (TT_SDMIXER) | Line 45566 |

### Object Dispatch Architecture

When `AcPresentationControlProc` (0xF8450B) processes a `<SHOW OBJ="...">` action:

1. The XML parser extracts the OBJ name string
2. The name is matched against the resource/object name table
3. For bitmap resources (ftdemo01-48): loads the image and renders to VRAM
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

`AcPresentationBoxProc` (0xF842B4) handles the visual frame rendering, responding to message types 0x1E0003C, 0x1E0003A, 0x1C0001B and calling display routines at 0xFA6266, 0xFA4409.

---

## Demo Mode Handlers (Program ROM)

The Feature Demo uses a multi-mode event-driven architecture with separate handlers for different demo stages:

| Handler | Address | Event | Purpose |
|---------|---------|-------|---------|
| `DemoModeFunc` | `demo_routines.s` | 0x1C00013 | Main demo mode dispatcher (init vs. run) |
| `DemoMenuTtlFunc` | `demo_routines.s` | — | Demo menu title (stub) |
| `DemoStyleTtlFunc` | `demo_routines.s` | 0x1C00007/0x1C00013 | Style selection with encoder/direction input |
| `DemoSoundTtlFunc` | `demo_routines.s` | 0x1C00007/0x1C00013 | Sound selection with encoder/direction input |
| `DemoRhyTtlFunc` | `demo_routines.s` | 0x1C00007/0x1C00013 | Rhythm selection with encoder/direction input |
| `DemoMode_Initialize` | 0xF869E3 | — | First-time demo setup (voice save, audio init) |
| `DemoMode_Main_Operation` | 0xF8696F | — | Main demo playback loop |
| `AcDemoSongBoxProc` | ~line 194533 | — | Song selection display widget |
| `DemoSongSelFunc` | ~line 194728 | — | Song selection handler |
| `AcDemoMedleyDispBoxProc` | ~line 195115 | — | Medley display widget |

Each selection handler (Style/Sound/Rhythm) has a dispatch table and supports three input types:
- **Direction** (up/down): Posts event 0xE2 (style) or 0xE3 (sound/rhythm)
- **Encoder** (rotary): Posts event 0xE2 (rhythm) or 0xE1 (sound) via 0xF99490
- **Enter**: Calls shared handler at 0xF86A47

## No Floppy Loading Path

Despite the sophisticated XML presentation infrastructure, **the current firmware does NOT load SSF files from floppy disc:**

1. **SSF parser reads from hardcoded ROM addresses.** The `AcPresentationControlProc` and related handlers are wired to data in the Table Data ROM (0x800000+), not to a floppy loading pipeline.

2. **No floppy disc type for presentations.** The [disc type signature table]({{ site.baseurl }}/system-update-discs/#disc-type-detection) has 8 entries covering firmware updates, custom data, and HDAE5000 — none for SSF or presentation files.

3. **Floppy I/O handles only data formats.** Beyond system updates, the floppy subsystem handles: MIDI songs (.MID), sequencer tracks (.SQT), styles (.STY), performance memories (.PMT), rhythm data (.RCM) — but NOT SSF presentations.

---

## Bitmap Loading Chain

When `AcPresentationControlProc` processes a `<SHOW OBJ="ftdemo01">` action, the firmware:

1. **Looks up the object name** (`ftdemo01`) in the UI object table (`NAKA_UIObjectTable`, ~141 entries). The corresponding entry is a `FTDEMO_SCREEN*` structure.

2. **Extracts the filename** from the structure — the last field is a `.long` pointer to a null-terminated string like `"FTBMP01"` (stored as `FTDEMO_BMP01_TECHNICS_GLOBE`).

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

The entire pipeline is **ROM-resident** — no disk I/O occurs for the Feature Demo. The `"FTBMP01"` filename in the `FTDEMO_SCREEN` structure is a logical key, not a filesystem path.

---

## Button Sequence for Feature Demo

The correct button sequence to activate the Feature Demo from the home screen:

1. Press **DEMO** button → `8D38` transitions from `0x01` (normal) to `0xE0` (DEMONSTRATION menu appears)
2. Press **LEFT 4** (4th from top, CPL_SEG9) → `8D38` transitions to `0xE4` (FEATURE PRESENTATION sub-menu appears)
3. Press **LEFT 2** (CPL_SEG10) → `8D38` transitions to `0xE1` (demonstration/performances begin playing)

### Demo Menu UI States

| State (`0x8D38`) | Description |
|-------------------|-------------|
| `0x01` | Normal operation (home screen) |
| `0xE0` | DEMONSTRATION menu (top-level) |
| `0xE4` | FEATURE PRESENTATION sub-menu |
| `0xE1` | Demonstration/performances playing |

---

## Two Distinct Activation Paths

The Feature Demo's visual SSF presentation has TWO completely different activation paths. Understanding the distinction is critical to diagnosing why the automated demo fails in MAME.

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

### Path 2 — Automated (Demo Timer/Sequencer): FAILS

This is the path taken by the automated demo sequencer when cycling through demo items:

```
Demo timer/sequencer
  → DemoMenu_BuildItemWorkspace (0xF83CEA)
    → allocates workspace with tag 0x82xx (from table at 0xE9F88C)
      → event 0x1C0001C (via PostEventWithParam, queued)
        → AcPresentCtrl_CheckSSFStart (0xF84625)
          → tag == 0xB80A? NO (tag is 0x82xx)
            → event 0x1C00006 NEVER SENT
              → SSF parser never starts
                → FTBMP bitmaps never render
```

`DemoMenu_BuildItemWorkspace` reads a "part select" index `R` from DRAM `0x8D3A` and computes `workspace[0..3] = table[0xE9F88C + iz*2] + R*1024`. The table holds 16-bit values in the `0x82xx`-`0x82CC` range. This formula can **never** produce `0x0000B80A` for any byte `R`, because the difference `0xB80A - 0x82xx` is never divisible by 1024.

### Why the Automated Path Cannot Trigger SSF

The workspace tag mismatch is architectural: the automated demo sequencer uses `DemoMenu_BuildItemWorkspace` which creates workspaces tagged for song/style selection (`0x82xx`), not for SSF presentation (`0xB80A`). The SSF-correct tag is only produced by `GroupBoxProc_StartSSFPresentation`, which is only reached via the manual button-press path through event `0x1C00038`.

Additionally, the demo state machine variable at DRAM `0x0251D8` stays `0x0000` throughout the automated demo. This state machine is what should drive the visual SSF through its presentation sequence, but it never advances because the sequencer parts (`DRAM[0x10420] = 0xFFFF`, all 16 parts active) never complete without waveform ROMs.

### SSF Gate State 0xE4

The gate table entry for state `0xE4` (FEATURE PRESENTATION sub-menu) contains the **unconditional marker** `0xFFFE`. This means any key press in state `0xE4` should broadcast event `0x1C00038` — the gate is wide open. This confirms the manual path would work if physical button input were simulated.

### Key Code Locations

| Function | ROM Address | Source File | Purpose |
|----------|-------------|-------------|---------|
| `GroupBoxProc_StartSSFPresentation` | 0xF9A273 | `presentation_sound_nav.s:33` | Builds correct `0xB80A` workspace, sends direct event |
| `AcPresentCtrl_CheckSSFStart` | 0xF84625 | `drawbar_panel_ui.s:18086` | Checks workspace tag, gates SSF start |
| `DemoMenu_BuildItemWorkspace` | 0xF83CEA | `drawbar_panel_ui.s:17186` | Builds `0x82xx` workspace (wrong tag for SSF) |
| Workspace tag table | 0xE9F88C | — | 16-bit values in `0x82xx` range |

---

## MAME Emulation Status

**Partially working.** The Demo Timer System (song cycling) works correctly in MAME — the timer counts down, songs cycle, and `PlaySong` returns after ~16 seconds of SwbtWr buffer processing. The SSF Visual Presentation (FTBMP bitmap rendering) does not trigger because the automated demo path uses workspace tags (`0x82xx`) that fail the `0xB80A` check in `AcPresentCtrl_CheckSSFStart`.

**Root cause summary:**
- The automated demo sequencer (`DemoMenu_BuildItemWorkspace`) creates workspaces with `0x82xx` tags
- The SSF presentation requires workspace tag `0xB80A`, which is only created by the manual button-press path (`GroupBoxProc_StartSSFPresentation`)
- `demo_state` at DRAM `0x0251D8` stays `0x0000` — the visual state machine never advances
- Sequencer parts never complete (`DRAM[0x10420] = 0xFFFF`) without waveform ROMs

**Two independent bugs remain:**
1. **Song cycling stuck:** Sequencer parts never complete without waveform ROMs, preventing the timer from resetting for the next song
2. **SSF never triggers in automated mode:** The automated path fundamentally cannot produce the correct workspace tag; only the manual button-press path through `GroupBoxProc_StartSSFPresentation` creates tag `0xB80A`

> ⚠ The Lua script that produced the traces below (`ftdemo_v3.lua`, automated navigation from
> boot to Feature Demo activation) was never committed and no longer exists. Anyone re-running
> this analysis has to rebuild it; the instrumentation constraints it hit are recorded under
> *Instrumentation pitfalls* below so that rebuild does not repeat them.

---

---

## Workspace Allocation — Concept Explained

Before describing the root cause, it helps to understand what "allocating a workspace" means in the KN5000 firmware's event system.

The KN5000 event system (centered on `SendEvent` at `0xFA9660` and `PostEventWithParam` at `0xFA9D58`) passes three registers as event parameters: XWA (target), XBC (event code), and XDE (data/parameter). For events that need to carry more than a single 32-bit value, the firmware uses a **workspace** pattern:

1. A small block of memory (typically 12 bytes) is allocated from the firmware heap by calling `Malloc` (the workspace allocator). The returned pointer is stored in DRAM (usually somewhere in `0x000000–0x0FFFFF`).
2. The workspace fields are populated: the first 4 bytes act as a **type-tag** (a magic 32-bit value identifying the kind of data the workspace carries), followed by payload fields.
3. The workspace **pointer** is passed as XDE when calling `SendEvent` or `PostEventWithParam`.
4. The receiving handler reads the workspace via the pointer, checks the type-tag, and processes the payload.

Think of the workspace as a small heap-allocated struct passed by pointer via the event system.

Because workspaces are allocated from a pool in DRAM and may be reused, it is critical that the event fires and the workspace is consumed **before** the memory is overwritten by another allocation or unrelated code. This is why the two distinct event-dispatch paths (queued vs. direct) produce different results.

---

## The Two Paths in Detail

Two different code paths send event `0x1C0001C` to `AcPresentationControlProc`:

#### Path 1 — `DemoMenu_BuildItemWorkspace` (0xF83CEA) — QUEUED, WRONG TAG

This function is called in a loop for each of the ~15 demo menu items (styles, sounds, rhythms). For each item it:

1. Allocates a 12-byte workspace via the heap allocator (`FF0E80`).
2. Reads the "part select" index `R` from DRAM address `0x8D3A` via `GetPartSelect()`.
3. Computes `workspace[0..3] = table[0xE9F88C + iz*2] + R*1024`.
   The table (at ROM `0xE9F88C`) holds 16-bit values all in the range `0x82xx–0x82CC`.
   **This formula can never produce the value `0x0000B80A`** for any byte `R`, because the difference `0xB80A − 0x82xx` is never divisible by 1024.
4. Posts event `0x1C0001C` via `PostEventWithParam` (`FA9D58`) — a **queued** (deferred) dispatch.

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

The Feature Demo has two distinct activation paths with fundamentally different workspace tag behavior (see "Two Distinct Activation Paths" above):

- **Manual path** (physical button press in state `0xE4`): `UIState_KeyScan_Dispatch` → event `0x1C00038` → `GroupBoxProc_StartSSFPresentation` → workspace tag `0xB80A` → `AcPresentCtrl_CheckSSFStart` passes → SSF starts
- **Automated path** (demo timer/sequencer): `DemoMenu_BuildItemWorkspace` → workspace tag `0x82xx` → `AcPresentCtrl_CheckSSFStart` fails → SSF never starts

The automated path cannot produce the correct workspace tag by design. The `0x82xx` tags from the table at `0xE9F88C` serve a different purpose (song/style selection). Only `GroupBoxProc_StartSSFPresentation` constructs the `0xB80A` tag needed for SSF, and it is only reachable through the manual button-press event chain.

### Call-chain overview

```
Feature Demo activated
  → DemoModeFunc (0xF222CC)  [event 0x1C00013, XDE=1]
    → DemoMode_Initialize (0xF869E3)
    → DemoMode_Main_Operation (0xF8696F)
      → DemoMenu_BuildItemWorkspace (0xF83CEA)  [×15, for each menu item]
        → PostEventWithParam (0xFA9D58)
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

`UIState_KeyScan_Dispatch` IS called during boot initialization — approximately 900+ times — but all calls occur when DRAM `0x8D38 = 0x00`. This maps to ROM table entry[0] at `0xE014CE`, which contains the sentinel array `{0xFFFF}` (immediately terminating). Every boot-time call returns immediately with no event sent.

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
`"Technics"`, 2880 sectors, 18 sectors/track, 2 heads. The driver's `kn5000_floppies` slot
offers `35hd` and `35dd`, and `fdc:0` defaults to **`35hd`**.

### How event 0x1C00038 is generated — detailed analysis

#### `UIState_KeyScan_Dispatch` — the event sender

The function `UIState_KeyScan_Dispatch` (ROM `0xF98697`) is the code that sends event `0x1C00038`. It is **not called directly** — instead, it appears as a function-pointer entry in many UI widget handler chains (in the SwbtWr bank-2 listener lists such as `SwbtB2_Code00_Listeners`, `SwbtB2_Code01_Listeners` and `SwbtB2_Code02_Listeners`, formerly labelled `UIState_HandlerTable_WithProbe`, `UIState_HandlerTable_Standard` and `UIState_HandlerTable_Compact`). When any widget using one of these handler chains processes certain events (typically user interaction events), it walks its handler chain and calls `UIState_KeyScan_Dispatch`.

`UIState_KeyScan_Dispatch` logic:

1. Calls `0xEF0797` to check bit 7 of DRAM `0x0406`. This flag is SET once during boot by `Boot_DisplayScreen` (call at line 89160) and CLEARED only during flash memory updates. It should be set throughout normal operation, so this check passes.
2. Reads a byte from DRAM `0x8D38` (an array selector index `R`).
3. Reads a ROM pointer `P = ROM[0xE01F80 + R×4]`. The pointer `P` points to a ROM array of 16-bit state values ending in `0xFFFF`.
4. Walks the array at `P`, comparing each entry to the current selection state built from DRAM bytes `0xC07D` and `0xC080` (packed as `(0xC080 << 8) | 0xC07D`).
5. If a match is found (or if the first array entry is `0xFFFE`, indicating "always send"), builds a 32-bit XDE parameter from `0xC07D`–`0xC080` and sends event `0x1C00038` to `XWA=0xFFFFFFFF` via `FA9945`.

#### `FA9945` — the broadcast event router

`FA9945` is the intermediate event-routing function called by `UIState_KeyScan_Dispatch`. It checks a dynamic routing table in DRAM at `0x02BC34` (populated at runtime by `FA9752`). For each registered entry, it checks whether the entry's event code matches `0x1C00038` **and** whether the entry's "match value" equals the upper 16 bits of the XDE parameter. If a match is found, the event is forwarded to the registered handler (GroupBoxProc instance).

#### `FA9752` — the event queue writer (`PostEvent`)

`FA9752` (labeled `PostEvent` in the disassembly) **inserts events into a circular event queue** at DRAM `0x02BC34` (head/tail pointers at `0x02EC34`/`0x02EC36`). Each 12-byte queue entry holds:

```
entry[0..3]  = self pointer (XWA) — object ID posting the event
entry[4..7]  = event code (XBC)
entry[8..11] = param (XDE)
```

`FA9945` is the queue **processor/router**: it reads pending entries from `0x02BC34`, and for each entry with event code `0x1C00038`, checks whether the upper 16 bits of the parameter match a value stored in the entry. If the queue is empty, it posts the new event directly via `FA9D58`.

The event routing for `0x1C00038` therefore works through the standard event queue. `UIState_KeyScan_Dispatch` acts as the PRODUCER: it checks state bytes, then pushes `0x1C00038` + packed XDE into the queue via `FA9945`. The CONSUMER is whichever widget handler receives the queued event — presumably GroupBoxProc, once it has received its own event setup during initialization.

For GroupBoxProc to receive the queued `0x1C00038`, it must either:
- Be the current "active" widget receiving events from the queue, OR
- Have registered via some dispatch mechanism that routes `0x1C00038` to it specifically

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

Pressing DEMO in state `0xE4` transitions directly to `0x01` (normal mode), exiting the demo menu entirely. It does NOT trigger SSF. Pressing LEFT 2 starts the demo timer (song cycling) but does NOT trigger SSF visual presentation. The `demo_state` at DRAM `0x0251D8` remains `0x0000` throughout — the visual state machine never advances because sequencer parts never complete (`DRAM[0x10420] = 0xFFFF` without waveform ROMs).

**Two independent bugs remain:**
1. **Song cycling stuck:** Sequencer parts (`DRAM[0x10420]=0xFFFF`) never complete without waveform ROMs, preventing the timer from resetting for the next song
2. **SSF never triggers in automated mode:** The automated demo path through `DemoMenu_BuildItemWorkspace` creates workspace tags in the `0x82xx` range (from table at `0xE9F88C`), which always fail the `0xB80A` check in `AcPresentCtrl_CheckSSFStart`. Only the manual button-press path through `GroupBoxProc_StartSSFPresentation` (0xF9A273, in `presentation_sound_nav.s:33`) can produce the correct tag

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

2. **Table lookup:** `GroupBoxNotify_SendSSFEvent` (0xF98697) reads the byte `R` from `0x8D38` and loads the pointer `P = SSF_PresentationGateTable[R]`.

3. **State matching:** The 16-bit array at `P` is checked against the current panel selection state (packed from DRAM bytes `0xC07D` and `0xC080` as `(C080 << 8) | C07D`):
   - `{0xFFFE}` — **always match**: the event fires unconditionally
   - `{0xFFFF}` — **never match**: the entry is disabled, no event sent
   - `{val1, val2, ..., 0xFFFF}` — **conditional**: each value is compared to the packed state; if any matches, the event fires

4. **Event dispatch:** When a match is found, `GroupBoxNotify_SendSSFEvent` sends event `0x1C00038` via the broadcast router at `0xFA9945`, which forwards it to registered widgets (typically `GroupBoxProc`).

### Role in Feature Demo Activation

The gate table ensures the Feature Demo can only be activated from specific UI states. During boot (`0x8D38 = 0x00`), `entry[0]` points to `{0xFFFF}` — immediately terminating, blocking any SSF events. After boot stabilizes and the user navigates to the DEMONSTRATION menu, `0x8D38` transitions to values whose table entries contain valid state arrays.

In practice the activation bypasses this table: pressing DEMO in the FEATURE PRESENTATION sub-menu (state `0xE4`) reaches `GroupBoxProc_StartSSFPresentation` directly through the soft-button event path, not through `GroupBoxNotify_SendSSFEvent`.

The gate table's primary role appears to be **gating hardware button events** — when the event buffer dispatcher (`0xFDB328`) processes button presses from the key scanner, it invokes `GroupBoxNotify_SendSSFEvent` as part of widget handler chains. The table then determines whether those hardware button events should propagate as SSF trigger events based on the current UI mode.

### State-Value Arrays

Each gate table entry points to a **state-value array** — a sequence of 16-bit little-endian values terminated by `0xFFFF`. Each value encodes `(chain_index << 8) | param`, matching the packed panel selection state from DRAM bytes `0xC080` (chain index) and `0xC07D` (param).

Known arrays in ROM range 0xE014CE–0xE01F7E:

| Label | Address | Entries | Content | Used by mode |
|-------|---------|---------|---------|--------------|
| `SSF_GateStates_Mode00` | 0xE014CE | 0 | `{0xFFFF}` — disabled | 0x00 (boot/init) |
| `SSF_GateStates_Mode01` | 0xE014D0 | ~215 | Chains 0x00–0x0C, 0x91 — many states | 0x01 (normal) |
| `SSF_GateStates_Mode02` | 0xE0157E | 0 | `{0xFFFF}` — disabled | 0x02 |
| `SSF_GateStates_Mode03` | 0xE01580 | ~215 | Chains 0x00–0x0C, 0x43, 0x48, 0x70, 0x80, 0x91, 0x98 | 0x03 |
| `SSF_GateStates_Mode04` | 0xE0174A | 1 | Chain 0x91, param 0x00 | 0x04 |
| **`SSF_GateStates_Mode05`** | 0xE0174E | 14 | Chain 0x92, params 0x00–0x0D | **0x05** |
| `SSF_GateStates_Mode06` | 0xE0176C | — | Binary data (incbin) | 0x06+ |

The `SSF_GateStates_Mode05` array (0xE0174E) is a representative example: when the UI is in mode 5 (`0x8D38 = 0x05`), the SSF event fires only if the current panel state has chain index `0x92` and a param value between `0x00` and `0x0D`. All other panel states are blocked.

### Source Location

- **Table definition:** `maincpu/kn5000_v10_program.s`, label `SSF_PresentationGateTable` (0xE01F80)
- **Getter function:** `SeMenu_LoadRawAddr` — loads index from DRAM 0x8D38
- **Consumer function:** `GroupBoxNotify_SendSSFEvent` (0xF98697) — reads and evaluates the table
- **State-value arrays:** ROM range 0xE014CE–0xE01F7E (pointed to by table entries)
- **Example array:** `SSF_GateStates_Mode05` (0xE0174E) — 14-entry filter for UI mode 5

---

## Interpretation

The XML presentation system — with its `EXEC` tag, `SONG` playback, `IMG` display, rich tag vocabulary, and event-driven architecture — was almost certainly designed to be more flexible than its single current usage (a hardcoded Feature Demo in ROM).

The most likely explanation: **Technics designed a general-purpose presentation engine**, perhaps intended for:

- **Dealer demonstration discs** — scripted presentations showcasing the keyboard's features at retail stores
- **Educational materials** — step-by-step tutorials loaded from floppy
- **Trade show content** — automated demonstrations for NAMM or music trade events

The infrastructure was built (XML parser, event system, tag vocabulary, `EXEC` command support), but the floppy loading path was either never completed or was removed before release. What shipped was a single ROM-resident Feature Demo using a fraction of the system's capabilities.

The user's memory of "feature presentation discs" may refer to this planned-but-unshipped feature, or to the commercially-sold style/song demo discs that showcased the keyboard's capabilities using standard MIDI file playback.

---

## Demo Timer State Machine

The Feature Demo uses a timer-driven state machine to sequence through demo items. The timer variable is at DRAM address 3375 (0xD2F).

### Timer-Driven Entry Point

`Demo_SelectEntry_TimerTick` (0xF86D45) is called from the main loop timer. Each tick:

1. Checks control panel state (`Demo_SelectEntry_CheckCPanel`)
2. Decrements the countdown at address 3375
3. At count=10 (`0x0A`): loads the next song pattern and starts playback
4. At count=3: calls `Demo_SelectEntry_StartPlayback` to begin accompaniment
5. At count=1: updates display state

### Song Processing Flow

`Demo_SelectEntry_ProcessSongList` (0xF86D86) manages song selection:

1. Checks if song list at address 10420 is empty — if so, goes to countdown
2. Checks bit 3 of address 10413 for auto-play vs manual mode
3. In auto-play: compares current song index (10404) with target (4439)
4. Calls `Demo_WaitForDisplayBit` — busy-wait loop checking bit 2 of address 1056 (display ready flag) with 0xFFFFFF timeout
5. Calls `Banner_Loop_Check` — sends note-off commands (status 0xD3) to all 16 channels, cleaning up active notes
6. Increments song index at address 4440 and loops

### Display Wait

`Demo_WaitForDisplayBit` (0xF86F2C) is a timeout-protected busy-wait:

```
Loop 0xFFFFFF times:
    If bit 2 of DRAM[0x420] == 0: return (display ready)
Return after timeout
```

This ensures display operations complete before the next slide loads. The timeout prevents a hard hang if the display never becomes ready.

### Demo Timer Behavior in MAME

When the timer reaches 10, `Demo_SelectEntry_PlaySong` is called. This function calls `SwbtWr_ReinitBothBanks`, which runs the SwbtWr dispatch loop inline — processing 450+ buffered tone generator events. Each callback takes ~35ms, causing a **~16 second blocking period** where the main loop is paused.

After SwbtWr processing completes (~960 frames), PlaySong returns (sets `DRAM[0x8F4E]` from `0x04` to `0x06`), and the timer resumes counting down from 10. The tone generator hold timer (2 seconds per voice) then controls the pacing of subsequent song transitions.

**Note:** The 16-second initial delay may differ from real hardware, where the tone generator writes go to hardware registers rather than through HLE. See [Feature Demo Timer Behaviour]({{ site.baseurl }}/feature-demo-investigation-2026-03-09/) for the frame-by-frame measurement.

The sequencer tick counters are driven by **INTTR5**. Two defects in `tmp94c241.cpp`'s `timer_16bits` lambda used to stop it firing — a TREG_HIGH match raised `0x08` (INTTR4) instead of `0x80` (INTTR5), and the `T4FFCR` bits gated the whole match instead of just the flip-flop. Both are fixed, upstream in [#15878](https://github.com/mamedev/mame/pull/15878). See [Timer 4/5 and the Sequencer Clock]({{ site.baseurl }}/feature-demo-timer-bug-2026-03-09/).

### Key DRAM Addresses

| Address | Description |
|---------|-------------|
| 1056 (0x420) | Display status flags (bit 2 = display busy) |
| 3375 (0xD2F) | Demo timer countdown value |
| 3379 (0xD33) | Debounce counter |
| 4439 (0x1157) | Target song index |
| 4440 (0x1158) | Current song index |
| 10404 (0x28A4) | Active demo entry index |
| 10413 (0x28AD) | Demo control flags (bit 3 = auto-play) |
| 10420 (0x28B4) | Song list pointer |
| 36148 (0x8D34) | UI state byte |
| 36152 (0x8D38) | UI sub-state byte (0xE4 = Feature Presentation) |
| 36686 (0x8F4E) | Playback state flag |

## Related Pages

- [UI Framework]({{ site.baseurl }}/ui-framework/) — Widget system and event handling
- [System Update Discs]({{ site.baseurl }}/system-update-discs/) — Floppy disc format and update process
- [Storage Subsystem]({{ site.baseurl }}/storage-subsystem/) — Storage architecture overview
- [FDC Subsystem]({{ site.baseurl }}/fdc-subsystem/) — Floppy disk controller handlers
- [Image Gallery]({{ site.baseurl }}/image-gallery/) — Extracted graphics including FTBMP images

---


