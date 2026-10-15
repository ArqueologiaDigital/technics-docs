---
layout: page
title: Sequencer
permalink: /sequencer/
---

# Sequencer

The KN5000 includes a full-featured 16-track MIDI sequencer with real-time and step recording, playback, and editing capabilities. It also runs the auto-accompaniment style system and Feature Demo playback.

## Architecture

The sequencer engine runs on the **Main CPU** and generates MIDI events that are sent to the Sub CPU via the inter-CPU latch for sound generation. The architecture has three main stages: a tick-driven dispatcher, a ring buffer pipeline, and MIDI event processing.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     MAIN CPU SEQUENCER ENGINE                           │
│                                                                         │
│  MainLoop (0xEF1245) ─── continuous loop ──────────────────────┐        │
│       │                                                        │        │
│       ├─ Seq_TickWrapper (0xEF1388) ─────────────────┐         │        │
│       │       │                                      │         │        │
│       │       └─ Seq_DispatcherEntry (0xF532E1)      │         │        │
│       │               │                              │         │        │
│       │               └─ Seq_DispatcherTick           │         │        │
│       │                       │                      │         │        │
│       │              ┌────────┴─────────┐            │         │        │
│       │              │ State Check      │            │         │        │
│       │              │ (8D36h)          │            │         │        │
│       │              │ skip if 0x10-0x16│            │         │        │
│       │              └────────┬─────────┘            │         │        │
│       │                       │                      │         │        │
│       │              Seq_DispatcherTick_Process       │         │        │
│       │                       │                      │         │        │
│       │              ┌────────┴─────────┐            │         │        │
│       │              │ RhythmROM_       │            │         │        │
│       │              │ CheckValid       │            │         │        │
│       │              │ (3277h check)    │            │         │        │
│       │              └────────┬─────────┘            │         │        │
│       │                       │                      │         │        │
│       │              Seq_RhythmProcessor (0xF5EC75)   │         │        │
│       │              RhythmROM_PatternDispatcher       │         │        │
│       │                       │                      │         │        │
│       │               ┌───────┴────────┐             │         │        │
│       │               │  Song Engine   │             │         │        │
│       │               │  writes MIDI   │─────────┐   │         │        │
│       │               │  to ring buf   │         │   │         │        │
│       │               └────────────────┘         │   │         │        │
│       │                                          v   │         │        │
│       │                              ┌──────────────────┐      │        │
│       │                              │  RING BUFFER     │      │        │
│       │                              │  Base: 0x01F37B  │      │        │
│       │                              │  WrPos: 0x01F377 │      │        │
│       │                              │  RdPos: 0x01F373 │      │        │
│       │                              └────────┬─────────┘      │        │
│       │                                       │                │        │
│       ├─ Seq_EventProcessingTick (0xEF14A3) ──┘                │        │
│       │       │                                                │        │
│       │       └─ Seq_ProcessEventLoop (0xEF14CA)               │        │
│       │               │                                        │        │
│       │       ┌───────┴──────────┐                             │        │
│       │       │ Seq_CheckSongEnd │                             │        │
│       │       │ WrPos == RdPos?  │                             │        │
│       │       └───────┬──────────┘                             │        │
│       │               │ (if data available)                    │        │
│       │               v                                        │        │
│       │       Seq_ProcessMidiEvent (0xEF13CD)                  │        │
│       │               │                                        │        │
│       │       ┌───────┴──────────────────────────┐             │        │
│       │       │ Parse MIDI status byte:           │             │        │
│       │       │  0x90 = Note On                   │             │        │
│       │       │  0x80 = Note Off                  │             │        │
│       │       │  0xB0 = Control Change            │             │        │
│       │       │  0xC0 = Program Change            │             │        │
│       │       │  0xE0 = Pitch Bend                │             │        │
│       │       └──────────────────────────────────┘             │        │
│       │                       │                                │        │
│       │                       v                                │        │
│       │               sendCOMM (0xEF32F4)                      │        │
│       │               Inter-CPU Latch → Sub CPU                │        │
│       │                                                        │        │
│       └────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────┘
```

## Main Loop

The Main CPU firmware's main application loop at `MainLoop` (0xEF1245) runs continuously after boot. Each iteration calls two sequencer functions:

| Routine | Address | Purpose |
|---------|---------|---------|
| `Seq_TickWrapper` | 0xEF1388 | Drives the sequencer tick dispatcher (song position advance, pattern loading) |
| `Seq_EventProcessingTick` | 0xEF14A3 | Reads MIDI events from the ring buffer and dispatches them to the Sub CPU |

The main loop also handles other firmware tasks (UI updates, floppy I/O, MIDI processing) between sequencer calls, with control flow returning to `MainLoop` via `JRL T`.

## Sequencer Dispatcher

The tick dispatcher processes sequencer timing and loads song/pattern data. It runs through a guarded pipeline:

### Entry and Guards

| Routine | Address | Purpose |
|---------|---------|---------|
| `Seq_DispatcherEntry` | 0xF532E1 | Entry point from `Seq_TickWrapper` |
| `Seq_DispatcherTick` | 0xF53318 | Guard: skips processing while the current title (`CURRENT_TITLE`, 8D36h) is a style-conversion title, 0x10-0x16 |
| `Seq_DispatcherTick_Process` | 0xF53328 | Rhythm ROM guard: calls `RhythmROM_CheckValid`, skips if validation fails |
| `Seq_RhythmProcessor` | 0xF5EC75 | Main rhythm/sequencer processing after guards pass |

### The current title (8D36h) -- formerly read as a "master sequencer state"

`0x8D36` is the id of the **current title** (screen): `MainTitleControl` handles `EVT_CHANGE_TITLE`
by jumping to `MainTitleCtrl_ChangeTitle` (0xF9936D), which saves the old value in `0x8D37`
(`PREVIOUS_TITLE`) and stores the new one with `LD (8D36h), L`. The neighbours belong to the same
object: `0x8D34` / `0x8D35` are the current / previous **mode** (`EVT_CHANGE_MODE`), `0x8D38` /
`0x8D39` the title actually on screen (`EVT_RETURN_TITLE` and `EVT_INTERRUPT_TITLE` change only it)
and its previous value. Since 2026-10-03 the code names them `CURRENT_TITLE`, `PREVIOUS_TITLE`,
`CURRENT_MODE`, `PREVIOUS_MODE`, `ACTIVE_TITLE`, `ACTIVE_TITLE_PREVIOUS` (v7: all 0x9C lower).

This page used to call `0x8D36` the master sequencer state. The evidence says title: its "skip
range" is exactly the style-conversion titles:

| Value | Title (`TITLE_*` in `shared/event_codes.s`) | `Seq_DispatcherTick` |
|-------|----------|----------|
| 0x10-0x16 | `TITLE_STYLCNVWAIT` .. `TITLE_STYLCNVCONT` (style conversion) | **skips** |
| anything else | | processes |

**Observed during Feature Demo (from MAME log)**, read as titles:

| Value | Title | When |
|-------|---------|------|
| 0x00 | (none yet) | Boot through initialization |
| 0x01 | `TITLE_NORMAL`, the normal play screen | Brief transition state |
| 0xE0 | `TT_DEMOMENU` (`RegTitle ..., 0xe0, ..., NAKA_VIEW_DemoMenu`) | Demo playback active (t=21s) |
| 0xE4 | `TT_DEMOFEATURE` (`RegTitle ..., 0xe4, ..., NAKA_VIEW_Demofeature`) | Demo init complete (t=22.6s) |

None of these values fall in the 0x10-0x16 skip range, confirming the sequencer dispatcher IS active during demo mode.

## Ring Buffer Pipeline

The sequencer uses a ring buffer at RAM `0x01F37B` to queue MIDI events for processing:

| Variable | Address | Purpose |
|----------|---------|---------|
| Read Position | 0x01F373 | Current read index |
| Write Position | 0x01F377 | Current write index |
| Buffer Data | 0x01F37B | Circular buffer start |

### Ring Buffer Routines

Multiple ring buffer instances exist for different sequencer channels. The core ring buffer implementation provides:

| Routine | Address | Purpose |
|---------|---------|---------|
| `Seq_RingBuf_Init_256` | 0xEF2F69 | Initialize 256-byte ring buffer |
| `Seq_RingBuf_Init_512` | 0xEF2FF8 | Initialize 512-byte ring buffer |
| `Seq_RingBuf_Init_1024` | 0xEF3087 | Initialize 1024-byte ring buffer |
| `Seq_RingBuf_Init_2048` | 0xEF3116 | Initialize 2048-byte ring buffer |
| `Seq_RingBuf_ReadByte` | 0xEF2F83 | Read one byte from ring buffer |
| `Seq_RingBuf_ReadData` | 0xEF30BF | Read data block from ring buffer |
| `Seq_RingBuf_WriteByte` | 0xEF30F5 | Write one byte to ring buffer |
| `Seq_RingBuf_WriteByte_Small` | 0xEF2FD7 | Write byte (small buffer variant) |

### SeqMain Buffer Wrappers (buffer at 0x01F37B)

| Routine | Address | Purpose |
|---------|---------|---------|
| `SeqMain_WriteByte` | 0xEF276D | Write one byte to main sequencer buffer |
| `SeqMain_WriteBytes` | 0xEF2783 | Write multiple bytes |
| `SeqMain_GetTimingValue` | 0xEF27B7 | Get timing/delta value |
| `SeqMain_InitBuffer` | 0xEF27BD | Initialize main buffer |
| `SeqMain_SaveWritePos` | 0xEF27CB | Save current write position |
| `SeqMain_ReadData` | 0xEF27D8 | Read data from main buffer |

### Additional Buffer Instances

| Buffer    | Base Address | Read Routine                           | Write Routine                          |
|-----------|--------------|----------------------------------------|----------------------------------------|
| MidiOut   | 0x01F785     | `SeqBuf_MidiOut_ReadByte` (0xEF280E)   | —                                      |
| DspSysEx  | 0x01FCA3     | —                                      | `SeqBuf_DspSysEx_WriteByte` (0xEF2A25) |
| VoiceMap  | 0x0201C1     | `SeqBuf_VoiceMap_ReadByte` (0xEF2C22)  | —                                      |
| SoundEdit | 0x0204DF     | `SeqBuf_SoundEdit_ReadByte` (0xEF2E2C) | —                                      |

### Event Processing

`Seq_EventProcessingTick` (0xEF14A3) calls `Seq_ProcessEventLoop` (0xEF14CA), which:

1. Calls `Seq_CheckSongEnd` (0xEF27A5) — compares write position `(0x01F377)` with read position `(0x01F373)`
2. If positions are equal (buffer empty), returns 0 — no events to process
3. If data available, reads MIDI bytes and calls `Seq_ProcessMidiEvent` (0xEF13CD)
4. `Seq_ProcessMidiEvent` parses the MIDI status byte and dispatches via `sendCOMM` to the Sub CPU

## Rhythm ROM

The 4MB Rhythm ROM (0x400000-0x7FFFFF) contains factory preset rhythm patterns, drum kits, and style data.

### Validation

At boot, the firmware validates the rhythm ROM:

| Routine                    | Address  | Purpose                                                                                                                                                                                        |
|----------------------------|----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `RhythmROM_ValidateHeader` | 0xF54651 | Compares the 12 bytes at 0x400000 with `RHYTHMROM_SIG_0`-`RHYTHMROM_SIG_2` (LE words 0x05040100, 0x04010083, 0x01008305); sets `RHYTHM_ROM_BASE` (0x3277) to 0, or to 0xFFFFFFFF on a mismatch |
| `RhythmROM_CheckValid`     | 0xF5452F | Checks if `(3277h)` == 0xFFFFFFFF; if so, returns C=1 (invalid)                                                                                                                                |

The validation result is stored at RAM `0x3277`:
- **0x00000000** = Valid (rhythm ROM present and header matches)
- **0xFFFFFFFF** = Invalid (no rhythm ROM or header mismatch)

When `RhythmROM_CheckValid` returns C=1, `Seq_DispatcherTick_Process` skips ALL rhythm/sequencer processing.

### Pattern Loading

| Routine | Address | Purpose |
|---------|---------|---------|
| `RhythmROM_PatternDispatcher` | 0xF634F3 | Dispatches pattern loading by type |
| `RhythmROM_LoadPattern` | 0xF6358D | Loads a pattern from rhythm ROM into RAM |
| `RhythmROM_CalcPatternAddr` | 0xF636E4 | Calculates pattern address from index |
| `RhythmROM_LoadDrumKit` | 0xF64550 | Loads a drum kit configuration |

## Audio Mixer (0x150000)

The Main CPU configures an audio mixer/attenuator at address 0x150000 during initialization:

| Routine | Address | Purpose |
|---------|---------|---------|
| `AudioMix_Init` | 0xEF17F4 | Initialize audio mixer hardware |
| `AudioMix_EnableChannels_Loop` | 0xEF1830 | Enable mixer channels |
| `AudioMix_WriteChannelGroup` | 0xEF183D | Write channel group configuration |
| `AudioMix_WriteChannelGroup_Loop` | 0xEF184B | Per-channel write loop |

## Demo Mode Integration

The Feature Demo uses the sequencer engine to play pre-recorded demonstration songs. See [Feature Demo]({{ site.baseurl }}/feature-demo/) for the SSF presentation system and [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/#feature-demo) for the detailed playback analysis.

### Demo Mode Entry

| Routine | Address | Purpose |
|---------|---------|---------|
| `DemoMode_Main_Operation` | 0xF8696F | Normal demo playback (disables Timer7, posts events, calls `Seq_StartMainControl`) |
| `DemoMode_Initialize` | 0xF869E3 | First-time demo init (calls `Seq_StartMainControlAlt`, initializes buffers) |

### Demo Mode State

The demo mode handler `SeqState_DemoModeHandler` (0xF993AD) responds to event `EVT_ACTIVATE_STATE` (`0x01c00013`). During demo playback:

1. The current title (`CURRENT_TITLE`, 0x8D36) becomes 0xE0, `TT_DEMOMENU` (`DemoMode_Main_Operation` entry)
2. The current title becomes 0xE4, `TT_DEMOFEATURE` (`DemoMode_Initialize` completion)
3. `Seq_StartMainControlAlt` sends `MT_ExitPresentation` (`EVT_EXIT_PRESENTATION`). `MainPreControl` calls `Part_InitFromPreset` only when the presentation-loaded flag at `0x0251D8` is set, and then clears it (`demo/file_demo_proc.s:199-203`; the clear is `MainPreControl_Dispatch`, `:158-159`). Only a presentation started from disk sets that flag, so during the ROM Feature Demo it is 0 and the call is skipped.

### Built-in demo/default style image

The built-in demo/default style image `Demo_StyleRhythmData` (0xF5CFCC, 0x674 bytes, copied to 0x94800 by the `AccDemo_*` loaders) contains:
- Rhythm/style parameter bytes (96 bytes)
- ASCII variation names: "a-variation1" through "c-variation4" (12 variations)
- Section names: " a-intro 1", " a-fill in 1", " a-ending 1", etc. (18 sections; 30 names with the variations)

## Medley Playback System

The KN5000 supports several medley playback modes for playing multiple songs in sequence.

### Medley Types

| Type             | Function                  | Description                                              |
|------------------|---------------------------|----------------------------------------------------------|
| Internal Medley  | `FmmIntMedleyFunc`        | Plays user-recorded sequences from the song slots in RAM |
| Disk Medley      | `FmmDiskMedleySelectFunc` | Plays sequences from floppy disk                         |
| SMF Medley       | `FmmSmfMedleyFunc`        | Plays Standard MIDI Files                                |
| Performance Data | `FmmPdMedleyFunc`         | Plays performance data files                             |
| Document Medley  | `FmmDocMedleyFunc`        | Plays document files                                     |

### Internal Medley Memory Layout

Internal medley songs are held in work DRAM (volatile; see [Memory Map]({{ site.baseurl }}/memory-map/)):

| Address | Size | Description |
|---------|------|-------------|
| `0xAB000` | 20KB | 10 song slots (0x800 bytes each) (`SEQ_SONG_SLOTS` in the source, the same address in v7 / v9 / v10) |
| `0xF180` | 2KB | Current playback buffer |

Each slot is 2048 bytes (0x800) and stores one user-recorded sequence.

### Key Routines

| Routine | Address | Purpose |
|---------|---------|---------|
| `SongBank_ScanActiveVoices` | 0xF2065A | Check if slot has valid data |
| `SongBank_SwitchAndUpdateTempo` | 0xF20BCE | Load and play a song from slot |
| `SongBank_LoadToWorkArea` | 0xF20BFA | Copy slot to playback buffer (LDIR) |
| `Medley_GetPlaybackStatus` | 0xF2076D | Get current playback state |

### Medley State Variables

| Address  | Name                   | Description                                   |
|----------|------------------------|-----------------------------------------------|
| `0x84FE` | `MEDLEY_PLAY_FLAG`     | 0=stopped, 1=playing                          |
| `0x889A` | `MEDLEY_SONG_COUNT`    | Number of songs in playlist                   |
| `0x889C` | `MEDLEY_CURRENT_INDEX` | Currently playing song                        |
| `0x889E` | `MEDLEY_REPEAT_FLAG`   | 0=no repeat, 1=repeat                         |
| `0x8890` | `MEDLEY_ORDER_ARRAY`   | 10-byte play order (0xFF=unused, 0xFE=marked) |

### Source Code

The medley system is implemented in `v10/maincpu/file_io/medley.s` (4,702 lines of disassembled code), including:
- Song selection UI handlers
- Playback state machine
- Repeat/shuffle logic
- Multi-format file loading

---

## Event Storage Format

The sequencer stores events in a MIDI-like format with extensions. The `SeqEvent_GetParamLength` routine (0xF3E37B) defines the event record sizes:

### Event Types and Sizes

| Status Byte | Size (bytes) | Type             | Description                                                                                                        |
|-------------|--------------|------------------|--------------------------------------------------------------------------------------------------------------------|
| 0x90+ch     | 6            | Note On          | Channel note-on with velocity                                                                                      |
| 0xB0+ch     | 6            | Control Change   | Controller number + value                                                                                          |
| 0xC0+ch     | 6            | Program Change   | Program number + bank info                                                                                         |
| 0xA0        | 3            | Aftertouch       | Channel pressure data                                                                                              |
| 0xD0        | 3            | Channel Pressure | Mono aftertouch                                                                                                    |
| 0xD1        | 3            | Extended         | Internal event type                                                                                                |
| 0xD3        | 3            | Extended         | Internal event type                                                                                                |
| 0x80        | 4            | Note Off         | Note-off (exactly 0x80; 0x81, 0x82, 0x85 and 0x86 are separate internal events below, and 0x83/0x84 return 0xFFFF) |
| 0xD2        | 4            | Extended         | Internal event type                                                                                                |
| 0x85        | 2            | Compact          | Short internal event                                                                                               |
| 0x86        | 2            | Compact          | Short internal event                                                                                               |
| 0x81        | 1            | Minimal          | Single-byte internal event                                                                                         |
| 0x82        | 1            | Minimal          | Single-byte internal event                                                                                         |

The format is optimized for storage efficiency — common MIDI events (Note On, CC, Program Change) use the standard 6-byte format while internal events use shorter encodings. Status bytes 0x81, 0x82, 0x85 and 0x86 are non-standard extensions used for compact representation of sequencer-internal control events.

### Ring Buffer Write Dispatch

Events enter the ring buffers via the dispatch table `SeqRingBuf_WriteDispatch_Table` at ROM 0xE00012:

| Slot | Handler                       | Description          |
|------|-------------------------------|----------------------|
| 0    | `SeqDMA_MultiWrite_NoteEvent` | Block write          |
| 1    | `SeqDMA_MultiWrite_SoundEdit` | Block write          |
| 2    | `SeqDMA_WriteMidi_NoteOn`     | MIDI Note On (0x90)  |
| 3    | `SeqDMA_MultiWrite_VoiceMap`  | Block write          |
| 4    | `SeqDMA_MultiWrite_DspSysEx`  | Block write          |
| 5-7  | `SeqDMA_Nop`                  | No-op (unused slots) |

### Playback Processing

`SeqPlay_ProcessTempoVoiceEvent` dispatches incoming events by status:

| Status Range | Handler | Purpose |
|-------------|---------|---------|
| 0x90-0x9F | Note processing | Assign voices, set velocity |
| 0x80-0x8F | Note off | Release voices |
| 0xB0-0xBF | Control change | Apply CC values |
| 0xC0-0xCF | Program change | Switch instrument |
| 0xE0-0xEF | Pitch bend | Apply pitch bend |

### Track Organization

The sequencer supports 16 tracks with the following part assignments:

| Track Group | Parts | Purpose |
|------------|-------|---------|
| Right 1 | Part 1 | Melody voice 1 |
| Right 2 | Part 2 | Melody voice 2 |
| Left | Part 3 | Left hand voice |
| Part 4-15 | Parts 4-15 | Additional voices |
| Part 16 | Part 16 | Accompaniment/control |

The `SeqTrack_ScanActiveChannels` routine scans all tracks to determine which have data, and `SeqTrack_AssignFloppyChannels` assigns loaded tracks to voice channels when loading from floppy disk.

### Timing

Events use delta-time encoding relative to the previous event. The timing resolution is handled by `SeqMain_GetTimingValue` (0xEF27B7) and the tempo is computed by `SeqTrack_ComputeTempoScaling`.

### Note Pool

`SeqNotePool_Init` (0xF3E3D9) initializes a note tracking pool for managing active notes during playback. The pool uses a linked-list structure starting at DRAM address 7602, with entries containing note number (0xFF = empty), velocity, and status bytes.

## Known Information

### Features

Based on KN5000 specifications:

| Feature    | Description                                    |
|------------|------------------------------------------------|
| Tracks     | 16 MIDI tracks                                 |
| Resolution | 96 PPQ (`SEQ_BEAT_TICK` counts 0..95 per beat) |
| Recording  | Real-time and step modes                       |
| Playback   | Variable tempo, loop                           |
| Editing    | Quantize, transpose, copy                      |
| Storage    | Save to floppy or HD                           |

### Style System

#### Structure

Each auto-accompaniment style has **3 variation groups** (A, B, C), each with **10 sections** (4 variations, 2 intros, 2 fill-ins, 2 endings), 30 in all:

| Section Type     | Count       | Purpose                                                                |
|------------------|-------------|------------------------------------------------------------------------|
| Intro            | 2 per group | Opening pattern (e.g., "a-intro 1", "a-intro 2")                       |
| Main (Variation) | 4 per group | Main accompaniment loops (e.g., "a-variation1" through "a-variation4") |
| Fill-In          | 2 per group | Transition fills (e.g., "a-fill in 1", "a-fill in 2")                  |
| Ending           | 2 per group | Closing pattern (e.g., "a-ending 1", "a-ending 2")                     |

Variation names are stored as ASCII strings in ROM (e.g., at `Demo_StyleRhythmData` 0xF5CFCC).

#### Accompaniment Channels

Each pattern includes **5 accompaniment parts** loaded from the Rhythm ROM:

| Channel | Pattern Buffer Offset | Purpose |
|---------|----------------------|---------|
| Drums | +0x22 | Percussion: kick, snare, hi-hat, cymbals |
| Bass | +0x2A | Bass line pattern |
| Accomp1 | +0x32 | Harmony part 1 (chords) |
| Accomp2 | +0x3A | Harmony part 2 |
| Accomp3 | (additional) | Harmony part 3 |

Each channel's metadata block is stored at a fixed offset within the pattern buffer (0x94800 or 0x95C00).

#### Pattern Loading Pipeline

`RhythmROM_PatternDispatcher` (0xF634F3) finds a rhythm by its program (RAM 0x34ED) and bank (RAM 0x34EE): it reads a {high, low} word pair from `RhythmROM_BankProgramLocators` (8 banks × 128 programs), and `RhythmROM_CalcPatternAddr` forms the address:

```
ROM address = 0x400000 + RHYTHM_ROM_BASE + ((high & 0xFF) << 16) + low
```

Where:
- `RHYTHM_ROM_BASE` is RAM 0x3277, which is 0 once the Rhythm ROM header has validated
- every non-zero locator is a multiple of 0x800; `RhythmROM_LoadPattern` copies 0x400 words (2 KB) from that address into the 2 KB buffer that `AccPat_Dispatch_AllocAndProcess` allocates (`Malloc(0x800)`, pointer at RAM 0x3564)
- the section index at RAM 0x34D6 (0..29, the 3 × 10 sections) selects, through `RhythmTiming_OffsetTable`, the pointer into `RHYTHM_PATTERN_BUF_A` (0x94800) kept at RAM 0x3560

#### Chord Detection

The firmware supports multiple chord detection modes, with **5 chord maps** identified in the style data. These likely correspond to:

| Mode | Description |
|------|-------------|
| Fingered | Full chord recognition from held notes |
| Single Finger | Root note + major/minor/7th from minimal input |
| Full Keyboard | Split keyboard with left-hand chord area |
| AI Fingered | Intelligent chord detection with voice leading |
| Pianist | Chord detection across full keyboard range |

Each chord map stores note-to-chord mappings that translate detected chord roots and types into bass and accompaniment note patterns for the 5 channels.

#### Key RAM Addresses

| Address       | Purpose                                                                                                                                   |
|---------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| 0x8D36        | `CURRENT_TITLE`, the current title id (formerly read as the sequencer's master state)                                                     |
| 0x041B        | `SEQ_BEAT_TICK` (firmware name `sq_beadt`): tick within the beat, 0..95                                                                   |
| 0x041C        | `SEQ_BEAT_COUNT` (`sqbtof`): beats since the start (word)                                                                                 |
| 0x0421        | `SEQ_TRANSPORT_STATE` (`sqsrtc`): bit 0 start pending, bits 1-2 running (bit 2 gates the clock), bit 3 stop requested, bit 4 stopped      |
| 0x3277        | `RHYTHM_ROM_BASE`: Rhythm ROM validation (0 = valid, 0xFFFFFFFF = invalid), added to the Rhythm ROM addresses the pattern loaders compute |
| 0x34ED-0x34EF | Program (0x34ED) and bank (0x34EE) of the rhythm `RhythmROM_PatternDispatcher` loads, and the part within it (0x34EF)                     |
| 0x34D6        | Section within the style, 0..29 (`RhythmROM_PatternDispatcher` treats 0x1E and above as 0)                                                |
| 0x35A0-0x35A1 | Error flags and drum kit selection                                                                                                        |
| 0x94800       | Pattern buffer A (`RHYTHM_PATTERN_BUF_A`)                                                                                                 |
| 0x95C00       | `RHYTHM_PATTERN_BUF_B`: a pool of 256-byte entries, entry n at 0x95C00 + n × 0x100 (`AccPatch_GetEntryAddr`)                              |

#### Drum Kit Loading

`RhythmROM_LoadDrumKit` (0xF64550) loads drum kit definitions from the Rhythm ROM. Each kit maps MIDI note numbers to specific drum/percussion sounds. Up to 10 drum kit configurations can be loaded.

### File Formats

Sequences and styles can be stored:

| Format | Extension | Description |
|--------|-----------|-------------|
| KN Sequence | .SQT | Native sequencer format |
| Standard MIDI | .MID | Import/export |
| Style | .STY | Auto-accompaniment |

## MAME Emulation Status

### What Works

- Sequencer dispatcher runs and rhythm ROM is validated successfully
- The current title changes correctly (0x00 → 0x01 → 0xE0 → 0xE4 during demo)
- Rhythm ROM data is read from 0x400000 during demo (1800-3800 reads/second)
- Sequencer processing code executes (PCs in F5CFxx-F641xx range during demo)

### Known Issues

> ⚠ These are the symptoms recorded in early 2026, before kn7000_mame `3fd44f3` (2026-08-05) fixed a duplicate `/INT0` dispatch in MAME's TMP94C241 core that wedged the sub→main link. Since that fix the demo runs well past 100 seconds with real voice names; see [Audio Subsystem - Feature Demo]({{ site.baseurl }}/audio-subsystem/#feature-demo). They are kept as the record of that investigation, not as current behaviour.

- **Ring buffer never written**: The main sequencer ring buffer at 0x01F37B always has write position == read position (both 0x0000). The song engine never generates MIDI events into the buffer.
- **Startup flag stuck at 0**: The flag at `0x0251D8` read 0 throughout. This is expected. It is the presentation-loaded flag, which `Seq_InitializeAndStart` sets only when a presentation is started from disk (`demo/fdemotext_routines.s:2917-2921`), so it stays 0 during the ROM Feature Demo. It gates no audio hardware configuration (see [Feature Demo]({{ site.baseurl }}/feature-demo/#presentations-loaded-from-disk)).
- **Event loop rate drops 60x**: After demo initialization, the event processing loop drops from ~11,500 iterations/sec to ~168-180/sec. The sequencer is busy processing but producing no output.
- **No Note On/Off events**: The demo sends CC, Pitch Bend, Channel Pressure, and SysEx commands, but never Note On (0x90) or Note Off (0x80).

See [Audio Subsystem - Feature Demo]({{ site.baseurl }}/audio-subsystem/#feature-demo) for detailed diagnostic log analysis.

## Related Pages

- [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) - Sound playback and Sub CPU
- [Feature Demo]({{ site.baseurl }}/feature-demo/) - SSF presentation system
- [MIDI Subsystem]({{ site.baseurl }}/midi-subsystem/) - MIDI I/O handling
- [Storage Subsystem]({{ site.baseurl }}/storage-subsystem/) - File save/load
- [System Overview]({{ site.baseurl }}/system-overview/) - Overall architecture

## Research Needed

- [ ] Re-measure the ring-buffer behaviour after the 2026-08-05 /INT0 fix
- [ ] Trace the path from rhythm ROM data reading to ring buffer writing
- [ ] Document sequence data structure format
- [ ] Analyze playback timing engine (Timer7 involvement)
- [ ] Map recording routines
- [ ] Decode full pattern data format within the 2 KB rhythm blocks
- [ ] Map chord detection algorithm (chord maps 1-5)
- [ ] Identify quantization algorithms
- [x] ~~Understand style format in Rhythm ROM~~ — 3 groups × 10 sections (30), 5 channels per pattern, rhythms located through `RhythmROM_BankProgramLocators`
- [x] ~~Document chord recognition~~ — Partial: 5 chord maps identified, chord detection modes documented
- [x] Document medley playback system
- [x] Document main loop and dispatcher architecture
- [x] Document ring buffer pipeline and instances
- [x] Document rhythm ROM validation and loading
- [x] Document sequencer state machine

## Code References

### Sequencer Core

| Symbol | Address | Purpose |
|--------|---------|---------|
| `Seq_TickWrapper` | `0xEF1388` | Main loop sequencer tick driver |
| `Seq_EventProcessingTick` | `0xEF14A3` | MIDI event dispatch from ring buffer |
| `Seq_ProcessEventLoop` | `0xEF14CA` | Event processing loop |
| `Seq_ProcessMidiEvent` | `0xEF13CD` | Parse MIDI status byte and dispatch |
| `Seq_DispatcherEntry` | `0xF532E1` | Dispatcher entry point |
| `Seq_DispatcherTick` | `0xF53318` | State guard (skip if 0x10-0x16) |
| `Seq_RhythmProcessor` | `0xF5EC75` | Main rhythm/sequencer processing |
| `MainTitleCtrl_ChangeTitle` | `0xF9936D` | State machine transition (writes 0x8D36) |
| `sendCOMM` | `0xEF32F4` | Send MIDI event to Sub CPU via latch |

### Ring Buffers

| Symbol | Address | Purpose |
|--------|---------|---------|
| `SeqMain_WriteByte` | `0xEF276D` | Write to main sequencer buffer (0x01F37B) |
| `SeqMain_ReadData` | `0xEF27D8` | Read from main sequencer buffer |
| `SeqMain_InitBuffer` | `0xEF27BD` | Initialize main buffer |
| `Seq_CheckSongEnd` | `0xEF27A5` | Check if buffer empty (WrPos == RdPos) |
| `Seq_RingBuf_Init_256` | `0xEF2F69` | Init 256-byte ring buffer |
| `Seq_RingBuf_Init_1024` | `0xEF3087` | Init 1024-byte ring buffer |

### Rhythm ROM

| Symbol | Address | Purpose |
|--------|---------|---------|
| `RhythmROM_ValidateHeader` | `0xF54651` | Validate magic bytes at 0x400000 |
| `RhythmROM_CheckValid` | `0xF5452F` | Check validation flag (0x3277) |
| `RhythmROM_PatternDispatcher` | `0xF634F3` | Dispatch pattern loading by type |
| `RhythmROM_LoadPattern` | `0xF6358D` | Load pattern from ROM to RAM |
| `RhythmROM_CalcPatternAddr` | `0xF636E4` | Calculate pattern ROM address |
| `RhythmROM_LoadDrumKit` | `0xF64550` | Load drum kit configuration |

### Audio Mixer

| Symbol | Address | Purpose |
|--------|---------|---------|
| `AudioMix_Init` | `0xEF17F4` | Initialize audio mixer at 0x150000 |
| `AudioMix_EnableChannels_Loop` | `0xEF1830` | Enable mixer channels |
| `AudioMix_WriteChannelGroup` | `0xEF183D` | Write channel group config |

### Demo Mode

| Symbol | Address | Purpose |
|--------|---------|---------|
| `DemoMode_Main_Operation` | `0xF8696F` | Demo playback handler |
| `DemoMode_Initialize` | `0xF869E3` | First-time demo initialization |
| `SeqState_DemoModeHandler` | `0xF993AD` | Demo mode event handler |
