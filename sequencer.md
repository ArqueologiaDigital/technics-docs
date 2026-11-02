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
3. `Seq_StartMainControlAlt` sends `MT_ExitPresentation` (`EVT_EXIT_PRESENTATION`). `MainPreControl` calls `SeqSong_ResetAll` only when the presentation-loaded flag at `0x0251D8` is set, and then clears it (`demo/file_demo_proc.s:199-203`; the clear is `MainPreControl_Dispatch`, `:158-159`). Only a presentation started from disk sets that flag, so during the ROM Feature Demo it is 0 and the call is skipped.

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

## Song storage

Ten songs live in RAM: their 0x800-byte records at 0xAB000 (`SEQ_SONG_SLOTS`; the current one,
`SEQ_CURRENT_SONG`, is copied to 0xF180, `SEQ_SONG_RECORD`, and back) and their events in a shared pool of
1,240 blocks of 256 bytes at 0xB0000 (`SEQ_BLOCK_POOL`, `SEQ_BLOCK_TOTAL`; block n at 0xB0000 + (n - 1) x
0x100). A block is {flags (bit 7 = used), u16 previous, u16 next (0xFFFF = last)} and 251 event bytes;
events run on across blocks. A track is a chain of blocks whose first block is in the song record's track
table. Free blocks form a list through the next link. An .SQT file is these records and blocks
([Floppy Disk Formats]({{ site.baseurl }}/floppy-disk-formats/#kn5000-disk-files)).

Song-record fields used by the storage code (offsets from 0xF180; the rest of the record, the song's panel
memory among it, is on the floppy page):

| offset | size     | field                                                            | evidence                                     |
|--------|----------|------------------------------------------------------------------|----------------------------------------------|
| +0x1E  | u16      | `SEQ_TRACK_MASK`, one bit per track holding data                 | `shared/ram_variables_by_use.s`              |
| +0x20  | 16 B     | `SEQ_TRACK_ASSIGN` (13 CHORD, 14 APC, 15 CONTROL, 16 RHYTHM ...) | `shared/ram_variables_by_use.s`              |
| +0x78  | 16 x u16 | each track's tail block (where recording appends)                | `SeqTrack_AdvanceCursor`                     |
| +0x98  | 16 B     | each track's write offset in its tail block                      | `SeqTrack_AdvanceCursor`                     |
| +0xAF  | u16      | `SEQ_FREE_LIST_HEAD`                                             | `shared/ram_variables_by_use.s`              |
| +0xB1  | u16      | `SEQ_FREE_BLOCKS`                                                | `shared/ram_variables_by_use.s`              |
| +0xD0  | 16 x 3 B | `SEQ_TRACK_TABLE`: {flags (bit 7 = has data), u16 first block}   | `ram_variables_by_use.s`, the softlist disks |

Each track's play cursor is a block number (u16, RAM 0x0C9E + 2(t - 1)) and an offset in it (u8, 5..255,
0x0CBE + (t - 1)). `SeqTrack_AdvanceCursor` moves a cursor on: within a block it only stores the offset; past
255 it follows the next link once per 251 bytes; in the track's tail block it refuses to pass the write
offset. `SeqTrack_ReadByteAndAdvance` reads one byte and steps; it is the reader the event parsers use (49 call
sites). Both were misnamed `VoiceSlot_*` until 2026-10-31.

The step sequencer edits the same memory through the cursors: `SeqBlock_Select` points `SEQ_BLOCK_PTR` at a
block, `SeqTrack_ReadCursorByte`, `SeqTrack_StepEvent`, `SeqTrack_NextEvent` / `SeqTrack_PrevEvent` move the cursor
by bytes or events, and `SeqTrack_WriteBytesAtCursor` / `SeqTrack_DeleteBytesAtCursor` edit the track in place.
`SeqEvent_CheckStatusByte` accepts a status of 0x80..0x86 except 0x83, or 0x90..0xD3 except 0xAn. The step-edit
screens save the cursor in eight 8-byte snapshots at 0x0DFF (`SeqCursor_Save` / `SeqCursor_Restore`). These 39
routines and their branch targets were the 212 `VoiceSlot_*` labels of v10 `display/scoop_display.s` until
2026-11-02 (disassembly `notes/open6-kn5000-d/naming/README.md`, section "kn5000-zc1", with the reason for each
name).

`SeqTrack_ScanActiveChannels` scans the tracks to find which hold data, and `SeqTrack_AssignFloppyChannels`
assigns loaded tracks to voice channels after a floppy load.

## Events

An event is a status byte and, for events of two bytes or more, the tick within the beat and its data;
`SeqEvent_GetParamLength` (0xF3E37B) gives each event's total length, status included. Time is 96 ticks per
beat (`SEQ_BEAT_TICK` 0..95), and a `0x81` event marks each beat, so a position is (beat count, tick): there
are no delta times. The layouts below are measured on the 14 KN5000 softlist disks (the disassembly's
`floppy/kn5000/*/files/*.SQT.s`, counted by `notes/open4-kn5000-b/engine/probes/sqt_event_census.py`); the
meanings cite the player's case in `SeqNoteCh_DispatchEventType` (`sequencer/sequencer_engine.s`) or the
routine named.

| status | len | layout after the tick                     | meaning                                                                                                                                                                                                                                                                                                                                             | evidence                                                                                                                                                                                                       |
|--------|-----|-------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 0x81   | 1   | -                                         | beat marker                                                                                                                                                                                                                                                                                                                                         | `SeqPart_ReadEventStream` counts them                                                                                                                                                                          |
| 0x82   | 1   | -                                         | end of track (bytes after it are stale)                                                                                                                                                                                                                                                                                                             | the case clears the part's active bit                                                                                                                                                                          |
| 0x84   | -   | -                                         | skipped by the player (2 occurrences on the disks); `SeqEvent_GetParamLength` returns 0xFFFF                                                                                                                                                                                                                                                        | `SeqPlay_IterateCh_CheckEventType`                                                                                                                                                                             |
| 0x85   | 2   | -                                         | **accompaniment start** in the song                                                                                                                                                                                                                                                                                                                 | sets `SEQ_RTMCFG` bit 1 (accompaniment runs with the song); `MIDI_RESET_PLAYBACK_STATE` queues 0x85 when MIDI Start arrives while recording                                                                    |
| 0x86   | 2   | -                                         | **accompaniment stop**                                                                                                                                                                                                                                                                                                                              | clears `SEQ_RTMCFG` bit 1                                                                                                                                                                                      |
| 0x80   | 4   | tempo low 7 bits, tempo bit 7 + high      | **tempo change**: tempo = byte2 or bit 0 of byte3 << 7, stored in panel record 0x48 fields 8/9                                                                                                                                                                                                                                                      | `SeqNoteCh_HandleTempoEvent` -> `SeqEvt_ApplyTempoEvent`; disks hold 102..127                                                                                                                                  |
| 0x9n   | 6   | key, velocity, duration lo7, duration hi7 | note (duration in ticks, 7-bit little-endian)                                                                                                                                                                                                                                                                                                       | sent on as a 5-byte record without the duration (`SeqNote_SetupVoice`)                                                                                                                                         |
| 0xBn   | 6   | record, field, value, mask                | **panel-parameter change**: the panel event {record, field, value, mask}, low 7 bits each; n bit 0 / 1 / 2 carry bit 7 of value / mask / record.  On playback {record, field} is matched against the track type's list (`SeqTrackAssign_PlaybackMapTable`) and the mask ANDed with the entry's; record 0x48 (style) fields 5 / 6 get extra handling | recorder `MIDI_EmitRecord_B0`; playback `VoiceMode3_InitChannelMatch`; `SeqPlay_IterateCh_CheckControlChange` tests record 0x48 field 5 / 6; `AccPedalConfig_ApplyChannel0` applies it                         |
| 0xCn   | 6   | part tag, 0, sound, variation             | **sound select** of a part record: bytes +0 (panel sound number, Lsw 0x000) and +1 (variation bank, Lsw 0x020), n bit 0 / 1 = their bit 7; record 0x48 field 0 on track 16 selects a rhythm                                                                                                                                                         | recorder `MIDI_EmitRecord_C0`; playback `VoiceMode4_RestoreValueHighBits` -> `VoiceMode_ParamHandler_4`; `SeqCh_DispatchMidi_CheckResult` -> `Rhythm_NoteDispatchWrapper`; `AccPedalConfig_ApplyChannelDirect` |
| 0xD0   | 3   | value                                     | **channel pressure** (aftertouch) of the track's part                                                                                                                                                                                                                                                                                               | `SeqNoteCh_HandleEventD0`; recorded by `MIDI_EmitRecord_D0`                                                                                                                                                    |
| 0xD1   | 3   | value                                     | **modulation** (CC 1; 2,170 on the disks, values 19..94)                                                                                                                                                                                                                                                                                            | `SeqNoteCh_HandleEventD1`; `MIDI_EmitRecord_D1`                                                                                                                                                                |
| 0xD2   | 4   | lsb, msb                                  | **pitch bend** (3,809 on the disks; rest value 0, 64)                                                                                                                                                                                                                                                                                               | `SeqNoteCh_HandleEventD2`; `MIDI_EmitRecord_D2`                                                                                                                                                                |
| 0xD3   | 3   | 0 or 127 (few others)                     | **expression** (CC 11); on a CONTROL track the expression pedal; the player also sets `DEMO_CONTROL_FLAGS` bit 6                                                                                                                                                                                                                                    | `SeqNoteCh_HandleEventD3`, `SeqPlay_IterateCh_NotControlChange`; `MIDI_EmitRecord_D3`                                                                                                                          |
| 0xA0   | 3   | value                                     | in the length table, absent from the disks                                                                                                                                                                                                                                                                                                          | `SeqEvent_GetParamLength`                                                                                                                                                                                      |

So the second value byte of 0xBn is the panel event's write mask, not a second value, and the two value bytes
of 0xCn are the part record's bytes +0 and +1.

### Controller events on playback

The player adds the track's part to 0xD0-0xD3 (`SeqNoteCh_SendControllerEvent`; 0xD2 through
`SeqNoteCh_SendPitchBendEvent`) and queues them with the other non-note events (`SeqBuf_WriteMidiEvent`).
`Audio_ReinitAndProcessEvents` keeps the newest value per track (the arrays MIDI IN uses for CC 1, CC 11 and
pitch bend) and `PendingParam_ScanAllTables` sends each as a panel event: 0xB4 channel pressure, 0xB2 modulation,
0xB1 pitch bend, 0xB3 expression, with field = the part's tag. That reaches the sub CPU as `D0 part 00 value`,
`B0 part 01 value`, `E0 part lsb msb` and `B0 part 0B value` (`SndPart_SetParam`). An event is dropped unless the
track's TRACK ASSIGN is a sound part (0xD3 also on DRUMS and CONTROL); 0xD3 on a CONTROL track becomes the
expression pedal level ({0xB0, 1}). Recording runs the other way: the same four panel events become D0 / D1 / D2 /
D3 (`SeqTrackAssign_RecordMapTable`, `MIDI_EmitRecord_D0`...`MIDI_EmitRecord_D3`). D0 is recorded only while bit 0
of RAM 0xFFC2 is set; what sets it was not traced. Only v10 was read. Source: disassembly
`notes/open6-kn5000-d/subcmd/README.md`, section "kn5000-a1f" (probe `probes/subcmd_probe.py recordmap`).

The tempo itself is computed by `SeqTrack_ComputeTempoScaling`.

## Playback

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
- a zero locator is not "no style": it is offset 0, the first style record (bank 0, program 90); see [Rhythm ROM (IC14)]({{ site.baseurl }}/rhythm-rom/), whose descrambled layout these addresses assume
- every non-zero locator is a multiple of 0x800; `RhythmROM_LoadPattern` copies 0x400 words (2 KB) from that address into the 2 KB buffer that `AccPat_Dispatch_AllocAndProcess` allocates (`Malloc(0x800)`, pointer at RAM 0x3564)
- the section index at RAM 0x34D6 (0..29, the 3 × 10 sections) selects, through `RhythmTiming_OffsetTable`, the pointer into `RHYTHM_PATTERN_BUF_A` (0x94800) kept at RAM 0x3560

#### Chord Detection

The chord recognizer, its 41 chord types and the voicing are on
[Accompaniment Engine]({{ site.baseurl }}/accompaniment-engine/#chord-recognition). The five maps in the style data
that this page used to read as chord-detection modes (Fingered, Single Finger, ...) are the Composer style's five
**COMPOSER CHORD MAPs** at style image +0xBA0 (32 bytes each): per map, four values, one per variation (0..11 or 0xFF),
copied by `CmpNcp_StepSlotInGroup2`; selecting map n sets `PANEL_STYLE` to 0xF0 + n
([Floppy Disk Formats]({{ site.baseurl }}/floppy-disk-formats/#the-composer-style-bank)).

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
- [x] ~~Document sequence data structure format~~ — [Song storage](#song-storage) and [Events](#events); open: the sub-CPU records of events 0xD0 / 0xD1 / 0xD3 (kn5000-a1f)
- [ ] Analyze playback timing engine (Timer7 involvement)
- [ ] Map recording routines
- [ ] Decode full pattern data format within the 2 KB rhythm blocks
- [x] ~~Map chord detection algorithm (chord maps 1-5)~~ — [Accompaniment Engine]({{ site.baseurl }}/accompaniment-engine/#chord-recognition); the chord maps 1-5 are the COMPOSER CHORD MAPs
- [ ] Identify quantization algorithms
- [x] ~~Understand style format in Rhythm ROM~~ — 3 groups × 10 sections (30), 5 channels per pattern, rhythms located through `RhythmROM_BankProgramLocators`
- [x] ~~Document chord recognition~~ — [Accompaniment Engine]({{ site.baseurl }}/accompaniment-engine/#chord-recognition)
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
