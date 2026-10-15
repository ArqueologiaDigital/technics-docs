---
layout: page
title: Accompaniment Engine
permalink: /accompaniment-engine/
---

# Accompaniment Engine

## Overview

The KN5000's accompaniment (auto-accompaniment) system automatically generates musical backing tracks based on the player's chord input on the lower keyboard. The engine plays patterns from built-in styles, transposing and voicing them according to the detected chord. This is one of the largest firmware subsystems, spanning chord detection, pattern sequencing, bass/chord/rhythm generation, variation/fill switching, and real-time MIDI event dispatch.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   LOWER KEYBOARD                      │
│        (Left half of keybed, split point)             │
└──────────────────────────────────────────────────────┘
                          │
                          v
┌──────────────────────────────────────────────────────┐
│              CHORD DETECTION (AccChord)               │
│  Scans held keys, matches chord type + root note     │
│  Sets dirty flags when chord changes                 │
└──────────────────────────────────────────────────────┘
                          │
                          v
┌──────────────────────────────────────────────────────┐
│           ACCOMPANIMENT SEQUENCER (AccompSeq)         │
│  Two independent channels (0 and 1)                  │
│  Each has: position, beat counter, pattern pointer   │
│  Processes events: notes (0x90/0x91), CC (0xD1-D7),  │
│  program change (0xC0), timing (0x84), beat (0x81)   │
└──────────────────────────────────────────────────────┘
              │                    │
              v                    v
┌────────────────────┐  ┌─────────────────────┐
│  BASS GENERATION   │  │  CHORD GENERATION   │
│  (AccBass)         │  │  (AccChord voices)  │
│  Single-note bass  │  │  Multi-note chords  │
│  lines from style  │  │  transposed to root │
└────────────────────┘  └─────────────────────┘
              │                    │
              v                    v
┌──────────────────────────────────────────────────────┐
│              RHYTHM GENERATION (AccRhythm)            │
│  Drum patterns, percussion mapping                   │
│  DrumChannel_MapToIndex for note routing             │
└──────────────────────────────────────────────────────┘
              │
              v
┌──────────────────────────────────────────────────────┐
│          VOICE ASSIGNMENT (AccVoice/AccPart)          │
│  Maps accompaniment parts to tone generator voices   │
│  Handles program changes, tuning, velocity           │
└──────────────────────────────────────────────────────┘
              │
              v
┌──────────────────────────────────────────────────────┐
│          TONE GENERATOR / MIDI OUTPUT                 │
│  SubCPU receives note events for sound generation    │
│  MIDI OUT sends accompaniment to external devices    │
└──────────────────────────────────────────────────────┘
```

## Main Loop Integration

The accompaniment engine is called from the main firmware loop in Phase 6 (Sequencer Finalization):

| Function                  | Address    | Main-loop phase / purpose                            |
|---------------------------|------------|------------------------------------------------------|
| `AccWrap_FlagSync`        | `0xF59B01` | Phase 1: synchronize accompaniment wrapper flags     |
| `AccDir_PeriodicEntry`    | `0xF5BD7A` | Phase 5: accompaniment direction periodic processing |
| `AccompSeq_PeriodicEntry` | `0xF6DCA9` | Phase 6: main accompaniment sequencer tick           |

`AccompSeq_PeriodicEntry` is the primary entry point, called once per main loop iteration. It:

1. Reads timing state from interrupt-updated counters at RAM 1128-1131
2. Copies to working state at RAM 32284-32291
3. Checks the start/stop bit (bit 2 of state byte at 32287)
4. If running, processes both accompaniment channels sequentially

## Accompaniment Sequencer

### Dual-Channel Architecture

The sequencer runs **two independent channels** (channel 0 and channel 1), each with its own:
- Pattern data pointer (RAM 32332/32333)
- Pattern read position (RAM 32322/32324): in pool mode a block number and an offset into a pool of 256-byte blocks at 0x1E8B00, in the battery-backed SRAM; otherwise a 32-bit address
- Beat counter (RAM 32326), incremented at each 0x81 beat marker
- Pointer at RAM 32328 (set at channel setup to 0x7E40 for the first channel, 0x7E41 for the second)
- Pattern state (RAM 32372)

Channel 0 uses state at offsets 32300-32302, channel 1 at 32304-32306. The `AccompSeq_InitEventDispatch` routine processes events for the current channel.

### Event Types

The sequencer reads a stream of events from pattern data at the read position, which `ResolveVRAMAddressForVoice` turns into an address (in pool mode a block of the pool at 0x1E8B00, which is SRAM, not VRAM). Each event starts with a type byte:

| Type          | Name            | Description                                                                                                              |
|---------------|-----------------|--------------------------------------------------------------------------------------------------------------------------|
| 0x81          | Beat marker     | Advances beat counter, checks pattern end                                                                                |
| 0x83          | Part transition | Handled by `AccompSeq_HandlePartTransition` (immediate)                                                                  |
| 0x84          | Position        | Update sequencer position                                                                                                |
| 0x90          | Note (small)    | Note-on/off event (compact format)                                                                                       |
| 0x91          | Note (large)    | Note-on/off event (extended format)                                                                                      |
| 0xC0          | Program change  | Change instrument patch                                                                                                  |
| 0xD1-D5, 0xD7 | Part control    | Part-specific control (voice, volume, pan, etc.); there is no 0xD6 case, so a 0xD6 byte is skipped like any unknown byte |

### Event Processing Loop

`AccompSeq_EventDispatchLoop` reads events until a timing boundary is reached:

1. Read event type byte from pattern data (via `ResolveVRAMAddressForVoice`)
2. Dispatch by type:
   - 0x84: Call `AccompSeq_UpdatePosition` (immediate, no timing)
   - 0x83: Call `AccompSeq_HandlePartTransition` (immediate)
   - 0x81: Check beat boundary with delta time comparison
   - 0x90/0x91/0xC0/0xD1-D5/0xD7: Check timing via `AccompSeq_CalcDeltaTime`
3. If delta time <= 24 ticks (a sixteenth note at 96 ticks per beat): process event via `AccompSeq_ParseEvents`
4. If delta time > 24 ticks: set wait flag (bit 0 of 32339) and exit loop

### Timing

The accompaniment uses a 96-tick-per-beat timing resolution (PPQN = 96), with each beat divided into 96 sub-ticks. The firmware compares the current tick position against event timestamps using `AccompSeq_CalcDeltaTime`:

- Delta = 0: event is exactly on time
- Delta <= 24: event is within tolerance (play now)
- Delta > 24: event is in the future (wait)

A beat marker (event type 0x81) that falls due increments the beat counter (32326) and calls `AccompSeq_AdvancePosition`, which:
1. Advances the read position by one byte (offset 32324, carrying into 32322)
2. If the byte there is a block link (0x87), reads the next block number from the block header via `AccompSeq_ReadBeatHeader` and continues at offset 6 of that block

### Pattern End and Looping

A 0x87 byte links to the next 256-byte block: `AccompSeq_ReadBeatHeader` reads the next block's number from the current block's header (the word at offset 3), and reading resumes at offset 6 of that block. The loop is the 0x83 event: `AccompSeq_HandlePartTransition` reloads the read position saved for the channel (RAM 32308/32310 for the first channel, 32312/32314 for the second) when bit 3 of RAM 32295 is set, and otherwise stops the part.

## Style Data Format

### Style Variation Groups

Styles are organized into variation groups; the factory patterns are read from the Rhythm ROM at 0x400000 (see [Sequencer]({{ site.baseurl }}/sequencer/#pattern-loading-pipeline)). Each style has multiple variations:

| Variation | Description |
|-----------|-------------|
| Vari1-4 | Main pattern variations (increasing complexity) |
| Fill1-2 | Fill-in patterns (short transitional phrases) |
| Int1-2 | Intro patterns |
| End1-2 | Ending patterns |

Each variation group (A, B, C) has these sections. The `StyleVarGrp_*` labels are not pattern data: they are the one-letter group strings ("A", "B", "C") that the UI shows, in the Program ROM (`ui_widgets/naka_screen_dispatch.s`, listed by `PtrTbl_StyleVarGroupCodes`).

### Style Groups (Built-in Styles)

The Program ROM holds the style browser's group tables, one per category; each entry is a style-name pointer and a variation-table pointer (`ui_widgets/style_bitmaps.s`):

| Table                          | Address    | Style Category      |
|--------------------------------|------------|---------------------|
| `StyleGroup_ModernDance_Table` | `0xECE2F0` | Modern Dance styles |
| `StyleGroup_PopBallad_Table`   | `0xECE980` | Pop/Ballad styles   |
| `StyleGroup_Swing_Table`       | `0xECED38` | Swing/Jazz styles   |
| `StyleGroup_FunkFusion_Table`  | `0xECEF18` | Funk/Fusion styles  |
| `StyleGroup_JazzCombo_Table`   | `0xECF228` | Jazz Combo styles   |
| `StyleGroup_WorldMusic_Table`  | `0xECF7E8` | World Music styles  |
| `StyleGroup_LatinDance_Table`  | `0xECFCA8` | Latin Dance styles  |

## Chord Detection

`AccChord_ReadAndStoreKeys` scans the lower keyboard for held notes and determines the current chord:

1. Read pressed keys from the keyboard state
2. Match against chord recognition patterns (root + quality)
3. Set dirty flags via `AccChord_CompareAndSetDirty` when the chord changes
4. Trigger `AccVoice_SetChordChangeFlags` to notify voice assignment

The chord change triggers real-time transposition of the accompaniment pattern to the new chord root.

## Voice Assignment

The `AccVoice` subsystem manages the mapping between accompaniment parts and tone generator voices:

### Part Types

| Part | Function | Description |
|------|----------|-------------|
| Bass | `AccBass_*` | Single-note bass lines |
| Chord | `AccChord_*` | Multi-note chord voicings |
| Rhythm | `AccRhythm_*` | Drum/percussion patterns |

### Voice Allocation Pipeline

1. `AccVoice_SelectPartOffset` - Select the parameter offset for the current part
2. `AccVoice_ComputeParamAddr` - Calculate the voice parameter memory address
3. `AccPatch_SetVoiceParam` - Set voice parameters (instrument, volume, etc.)
4. `AccVoice_AssignPerPart` - Assign tone generator voices to the part
5. `AccVoice_SendProgChange` - Send MIDI program change for the instrument

### Part Parameters

Each accompaniment part has parameters stored at calculated offsets:

| Parameter | Function |
|-----------|----------|
| Voice/Instrument | `AccVoice_SelectAndApplyPatch` |
| Tuning | `AccTuning_SetAllFromLookup`, `AccTuning_CopyAllPartsFromStyle` |
| Rhythm mapping | `RhythmPart3_ProcessAccentData/4/5` |
| Channel assignment | `AccVoice_CheckChannelSetActive` |

The `AccPart_*` functions manage part data access:

| Function | Purpose |
|----------|---------|
| `AccPart_InitPositionsAndBase` | Initialize part position and base address |
| `AccPart_GetVoiceParamOffsetTable` | Look up voice parameter offset table |
| `AccPart_ResolveStyleAddr` | Resolve style data address for a part |
| `AccPart_CheckEndOfDataMarker` | Check for end-of-data in part stream |
| `AccPart_SelectSource` | Select data source (keyboard, Acc1-4) |
| `AccPart_Deactivate` | Deactivate a part (with pedal/sync options) |

## Accompaniment Wrapper (AccWrap)

`AccWrap_FlagSync` and `AccWrap_DispatchAndWaitSync` provide a synchronization layer:

- `AccWrap_ClearPositionAndReset` - Clear position counters and reset state
- `AccWrap_DispatchAndWaitSync` - Dispatch accompaniment events with synchronization

These ensure accompaniment state changes (start/stop, variation switch) are synchronized with the sequencer timing.

## Fade Effects

`AccompSeq_FadeOutTick` handles smooth fade-out when accompaniment stops:
- Called each tick while fade-out is active (bit 5 of state 32339 clear)
- Gradually reduces volume over multiple ticks

## Rhythm Note Dispatch

The rhythm section uses a specialized note dispatch system:

| Function | Purpose |
|----------|---------|
| `Rhythm_NoteDispatchWrapper` | Wrapper for rhythm note events |
| `Rhythm_NoteOnAfterSetup_A/B/C` | Note-on for three rhythm channels |
| `Rhythm_NoteRangeCheck` | Validate note is in playable range |
| `Rhythm_NoteOffMax_Dispatch` | Note-off with part-specific dispatch (D4-D7) |
| `DrumChannel_MapToIndexA/B` | Map drum MIDI notes to internal indices |

## Display Integration

`AccDisplay_RefreshIfDiskActive` refreshes the accompaniment display when disk operations are active (style loading from floppy/flash).

The `AccIll` (Accompaniment Illustration) subsystem handles the visual representation:
- `AccIllProc` - Main illustration processor
- `AccIll_HandleLowerPanelEvent` / `AccIll_HandleUpperPanelEvent` - Panel input
- `AccIll_HandleHorizSlider` / `AccIll_HandleVertSlider` - Slider controls
- `AccIll_HandleUpScroll` / `AccIll_HandleDownScroll` - Scroll navigation

## Style UI

The `StyleUI_*` labels define parameter blocks and screen layouts for the style editing interface:

| Label | Purpose |
|-------|---------|
| `StyleUI_ParamBlock_BAL` | Balance parameter display |
| `StyleUI_ParamBlock_VALUE` | Value parameter display |
| `StyleUI_ScreenData_Main` | Main style screen layout |
| `StyleUI_ScreenData_MeasCursor` | Measure cursor display |

## Related Pages

- [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) - Overall audio architecture
- [Tone Generator]({{ site.baseurl }}/tone-generator/) - Voice synthesis hardware
- [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/) - MainCPU-SubCPU communication
- [Display Subsystem]({{ site.baseurl }}/display-subsystem/) - UI rendering

## Research Needed

- [ ] Decode chord recognition algorithm (which chord types are supported, how root is determined)
- [ ] Map the complete style data format (header, part assignments, note data encoding)
- [ ] Document the variation/fill-in switching state machine
- [ ] Analyze the bass pattern generation algorithm (how bass notes are derived from chord)
- [ ] Document style conversion routines (`StylCnv_*`) for loading custom styles
- [ ] Map the accompaniment pedal interaction (`AccPedal_ScanVoiceSlots`)
