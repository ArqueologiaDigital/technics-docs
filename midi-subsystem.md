---
layout: page
title: MIDI Subsystem
permalink: /midi-subsystem/
---

# MIDI Subsystem

The KN5000 has two distinct MIDI paths: external MIDI I/O (handled by Main CPU) and internal MIDI-like messages between Main CPU and Sub CPU for audio synthesis.

## Architecture

```
                    ┌──────────────────────────────────────────┐
                    │            MAIN CPU                       │
                    │                                           │
   MIDI IN ────────>│  ┌──────────────┐   ┌──────────────┐    │
   (5-pin DIN)      │  │ MIDI Parser  │──>│ MIDI Router  │    │
                    │  └──────────────┘   └──────┬───────┘    │
                    │                            │             │
   MIDI OUT <───────│  ┌──────────────┐         │             │
   (5-pin DIN)      │  │ MIDI Output  │<────────┤             │
                    │  └──────────────┘         │             │
                    │                            │             │
   MIDI THRU <──────│  (Hardware echo)          │             │
   (5-pin DIN)      │                            v             │
                    │                   ┌──────────────┐       │
                    │                   │ Audio_DMA_   │       │
                    │                   │ Transfer     │       │
                    │                   └──────┬───────┘       │
                    └──────────────────────────┼───────────────┘
                                               │
                              Latch @ 0x120000 │
                                               v
                    ┌──────────────────────────────────────────┐
                    │             SUB CPU                       │
                    │                                           │
                    │  ┌────────────────────────────────────┐  │
                    │  │         MIDI_Dispatch              │  │
                    │  │         (0x034D93)                 │  │
                    │  │                                    │  │
                    │  │  Parse status byte (0x80-0xF0)     │  │
                    │  │  Route to voice parameter handlers │  │
                    │  └────────────────────────────────────┘  │
                    │                    │                      │
                    │     ┌──────────────┼──────────────┐      │
                    │     v              v              v      │
                    │  Voice_NoteOn  Voice_CtrlChange  ...     │
                    │  (0x02CF97)    (0x02A282)                │
                    └──────────────────────────────────────────┘
```

## Internal MIDI Processing (Sub CPU)

The Sub CPU's `MIDI_Dispatch` routine processes MIDI-like messages from the Main CPU via a ring buffer.

### Status Byte Dispatch

| Status | Range | Handler | Voice Handler | Description |
|--------|-------|---------|---------------|-------------|
| 0x80 | Note Off | `MIDI_Status_NoteOn` | `Voice_NoteOn` | Handled as Note On with velocity 0 |
| 0x90 | Note On | `MIDI_Status_NoteOn` | `Voice_NoteOn` | Note On (3-6 bytes) |
| 0xB0 | Control Change | `MIDI_Status_CtrlChange` | `Voice_CtrlChange` | CC messages (3 bytes) |
| 0xC0 | Program Change | `MIDI_Status_ProgChange` | `Voice_ProgChange` | Patch selection (4 bytes) |
| 0xD0 | Channel Pressure | `MIDI_Status_ChanPressure` | `Voice_ChanPressure` | Aftertouch (3 bytes) |
| 0xE0 | Pitch Bend | `MIDI_Status_PitchBend` | `Voice_PitchBend` | Pitch wheel (3 bytes) |
| 0xF0 | System | `MIDI_Status_System` | `Voice_SystemMsg` | System messages (3 bytes) |

### Message Format

Messages are read from the ring buffer at 0x2B0D:

```
Note On (standard):     [status] [channel] [note] [velocity]
Note On (extended):     [status|0x08] [channel] [note] [vel] [param1] [param2]
Control Change:         [status] [channel] [cc#] [value]
Program Change:         [status] [channel] [program] [bank_lsb] [bank_msb]
Channel Pressure:       [status] [channel] [pressure] [param]
Pitch Bend:             [status] [channel] [lsb] [msb]
System:                 [status] [data1] [data2] [data3]
```

### Dispatch Flow

```asm
MIDI_Dispatch:
    PUSH XIZ
    LDA XIZ, 2B0Dh              ; Ring buffer control structure
    LD WA, (XIZ + 004h)         ; Get byte count
    CALL RingBuf_SetOffsetHi    ; Set read position
    JRL T, MIDI_Dispatch_NextByte

MIDI_Dispatch_ParseStatus:
    LD WA, HL
    AND WA, 00F0h               ; Mask to get status nibble
    CP WA, 00F0h
    JRL Z, MIDI_Status_System   ; 0xF0: System messages
    CP WA, 00E0h
    JRL Z, MIDI_Status_PitchBend ; 0xE0: Pitch Bend
    CP WA, 00D0h
    JRL Z, MIDI_Status_ChanPressure ; 0xD0: Channel Pressure
    ; ... continue for other status bytes
```

## Control Change Handlers

The `Voice_CtrlChange` routine dispatches to specific handlers based on CC number:

### Standard MIDI Controllers

| CC# | Handler | Parameter | Notes |
|-----|---------|-----------|-------|
| 0x01 | `Voice_CC_ModWheel` | Modulation Wheel | Vibrato depth |
| 0x07 | `Voice_CC_Volume` | Main Volume | Channel volume |
| 0x0A | `Voice_CC_Pan` | Pan | Stereo position |
| 0x0B | `Voice_CC_Expression` | Expression | Dynamics control |
| 0x40 | `Voice_CC_Sustain` | Sustain Pedal | Hold notes |
| 0x5B | `Voice_CC_Sostenuto` | Sostenuto | Selective sustain |
| 0x5D | `Voice_CC_Soft` | Soft Pedal | Reduce volume/brightness |
| 0x5E | `Voice_CC_Portamento` | Portamento | Glide control |

### Proprietary Controllers

| CC# | Handler | Parameter | Voice Offset | Notes |
|-----|---------|-----------|-------------|-------|
| 0x91 | `Voice_CC_91` | Frequency Multiplier | +0x11 | Via lookup table at 0x011D16 |
| 0x95 | `Voice_CC_95` | Portamento Enable | +0x04 | Boolean flag (set/clear bit) |
| 0x97 | `Voice_CC_97` | Fine Pitch Tuning | +0x12 | Semitone-level adjustment, via lookup table |
| 0x9B | `Voice_CC_9B` | Vibrato Depth | +0x1F | Via lookup table at 0x011D16 |
| 0x9C | `Voice_CC_9C` | Vibrato Enable | — | Bit 8 toggle (enable/disable) |
| 0x9D | `Voice_CC_9D` | Tremolo/AM Depth | +0x20 | Amplitude modulation depth, via lookup table |

### CC Handler Structure

```asm
Voice_CtrlChange:
    ; Entry: XIZ = pointer to 4-byte message
    ;   XIZ+0 = status (0xBn)
    ;   XIZ+1 = channel (0-25)
    ;   XIZ+2 = CC number
    ;   XIZ+3 = CC value

    CP (XIZ + 001h), 01Ah       ; Channel must be < 26
    JRL NC, Voice_CC_Exit

    LD A, (XIZ + 002h)          ; Get CC number
    CP A, 09Dh
    JRL Z, Voice_CC_9D
    CP A, 09Ch
    JRL Z, Voice_CC_9C
    ; ... check other CC numbers
    CP A, 001h
    JR Z, Voice_CC_ModWheel
    ; etc.
```

## External MIDI (Main CPU)

The Main CPU handles external MIDI I/O via serial ports:

| Function | Description |
|----------|-------------|
| MIDI IN | Receives external MIDI, routes to internal synth or THRU |
| MIDI OUT | Transmits keyboard events, sequencer playback |
| MIDI THRU | Hardware echo of MIDI IN |

### MIDI Implementation

Based on KN5000 specifications:

| Feature | Support |
|---------|---------|
| Channels | 1-16 transmit and receive |
| Notes | Full 0-127 range |
| Velocity | Note On/Off |
| Aftertouch | Channel and polyphonic |
| Controllers | Standard + proprietary |
| Program Change | With bank select |
| System | Clock, Start/Stop/Continue |
| SysEx | Technics-specific messages |

## MIDI Channel Assignment and Voice Routing

The KN5000 supports 26 internal voice channels (0x00-0x19) mapped to 16 external MIDI channels (0-15). The Main CPU manages the voice-to-channel mapping via data structures in DRAM.

### Voice Data Tables

| Address | Purpose | Stride |
|---------|---------|--------|
| `0xEDB264` | Voice data pointer by MIDI channel (32 entries) | 4 bytes |
| `0xEDAE64` | Voice data pointer by index | 4 bytes |
| `0xEE8EB8` | Voice channel configuration | variable |
| `0xEE8ED8` | Channel assignment data (active flags) | variable |
| `0xEE8F22` | Voice allocation table | 5 bytes |
| `0xEE8F2E` | Voice layer table (layers 0-4) | 13 bytes |
| `0xED92F2` | Voice index lookup table | variable |

### Channel Lookup Functions

**`PanelTlv_CompanionOfPart`** (Main CPU, `audio/audio_control_engine.s`):
- Input: A = MIDI channel (0x00-0x1F standard, 0x48 = drum)
- Looks up pointer at `0xEDB264 + channel * 4`
- Returns pointer in XHL (or 0xFFFFFFFF if not found)

**`PanelTlv_PayloadOfTag`** (Main CPU, `audio/audio_control_engine.s`):
- Input: A = voice index
- Looks up pointer at `0xEDAE64 + index * 4`
- Returns pointer in XHL

**`NoteMap_LookupVoice`** (Main CPU, `note_voice_mapping.s`):
- Input: E = voice layer (0-4), C = MIDI channel (rejects > 0x20)
- Searches voice tables at `0xEE8F2E` with 13-byte stride
- Matches channel + instrument + layer to find voice slot

### MIDI Message Routing (Main CPU)

**`MIDI_CHANNEL_MESSAGE_DISPATCHER`** (`midi_serial_routines.s`):
- Entry point for external MIDI input
- Routes to channel-specific handlers via jump table
- Supports Note On/Off, CC, Program Change, Pitch Bend, Pressure

**`MIDI_DispatchCC`** (`midi/midi_dispatch_handlers.s`):
- Dispatches Control Change by CC number
- Jump table at `0xFD175E` (192 entries × 4 bytes for CC 0x00-0xBF)
- CC > 0xBF rejected

**`MIDI_DistributeParamToChannels`** (`audio/audio_control_engine.s`):
- Distributes a parameter update across all active channels
- Input: A = channel (0x00-0x1F standard), C = parameter, E = value
- Special case: channel 0x48 = drum channel (max 16 parameters)

### Voice Channel Architecture

The KN5000 uses a multi-layer voice system where each MIDI channel can have multiple voice layers:

- **26 internal voice channels** (0x00-0x19): Used by Sub CPU for tone generation
- **16 external MIDI channels** (0-15): Standard MIDI, mapped to voice channels
- **Voice layers** (0-4): Each MIDI channel can split into up to 5 layers (e.g., left hand, right hand, split zones)
- **Drum channel** (0x48): Special-cased in routing code, uses separate voice assignment

### Sub CPU Voice Filtering

**`Voice_LoadFilterTable_Ch`** (Sub CPU, 0x22071):
- Loads per-channel filter frequency and LPF tables
- Writes to tone generator registers:
  - `0x04520A`: Filter frequency
  - `0x04520E`: Filter Q
  - `0x0451CC`: Output register
- Clamps filter frequency to max 0x1C

**`Voice_LoadFilterTable_All`** (Sub CPU, 0x22161):
- Applies filter settings across all voice channels
- Dispatches per-channel filter loads in a loop

### Accompaniment MIDI Filtering

The accompaniment engine has its own MIDI filter system:

**`AccompSeq_MidiFilterCodeBlock`** (`accompseq_routines.s`):
- Embedded code block for accompaniment channel filtering
- Filters MIDI events based on chord changes and accompaniment state
- Manages state machine for accompaniment voice allocation

**`AccVoice_DispatchWithChannel`** (`accompaniment_engine.s`):
- Dispatches accompaniment voice events with channel info
- Three dispatch types: 0x0E (indexed table), 0x0F (ROM lookup), default (computed copy)

## Code References

### Sub CPU (`v142/subcpu/kn5000_subprogram_v142.s`)

| Routine | Address | Description |
|---------|---------|-------------|
| `MIDI_Dispatch` | 0x034D93 | Main MIDI message dispatcher |
| `MIDI_Dispatch_ParseStatus` | 0x034DA2 | Parse status byte |
| `MIDI_Status_NoteOn` | 0x034E65 | Note On/Off handler |
| `MIDI_Status_CtrlChange` | 0x034EB2 | Control Change handler |
| `MIDI_Status_ProgChange` | 0x034EEB | Program Change handler |
| `MIDI_Status_ChanPressure` | 0x034F2D | Channel Pressure handler |
| `MIDI_Status_PitchBend` | 0x034F65 | Pitch Bend handler |
| `MIDI_Status_System` | 0x034F9C | System message handler |
| `Voice_NoteOn` | 0x02CF97 | Voice note-on processing |
| `Voice_CtrlChange` | 0x02A282 | Voice CC processing |
| `Voice_CC_ModWheel` | 0x02A306 | Mod wheel handler |
| `Voice_CC_Volume` | 0x02A31C | Volume handler |
| `Voice_CC_Pan` | 0x02A340 | Pan handler |

### Main CPU (`maincpu/`)

| Routine | File | Description |
|---------|------|-------------|
| `MIDI_CHANNEL_MESSAGE_DISPATCHER` | `midi_serial_routines.s` | External MIDI message dispatcher |
| `MIDI_DispatchCC` | `midi/midi_dispatch_handlers.s` | CC dispatch via jump table at 0xFD175E |
| `MidiChannel_ConfigureController` | `midi/midi_dispatch_handlers.s` | Configure MIDI controller for voice channel |
| `MIDI_DistributeParamToChannels` | `audio/audio_control_engine.s` | Distribute param to all active channels |
| `PanelTlv_CompanionOfPart` | `audio/audio_control_engine.s` | Channel → voice data pointer (0xEDB264) |
| `PanelTlv_PayloadOfTag` | `audio/audio_control_engine.s` | Index → voice data pointer (0xEDAE64) |
| `NoteMap_LookupVoice` | `note_voice_mapping.s` | Find voice slot for note event |
| `NoteMap_SetChannelParam` | `note_voice_mapping.s` | Set MIDI channel parameter in note map |
| `Voice_DecodeNoteChannel` | `kn5000_v10_program.s` | Decode note channel to voice assignment |
| `PanelTlv_ResolvePartCompanions` | `kn5000_v10_program.s` | Initialize all 23 voice channel entries |

## Related Pages

- [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) - Sound generation
- [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/) - Main/Sub CPU communication
- [Sequencer]({{ site.baseurl }}/sequencer/) - MIDI recording/playback
- [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) - Local keyboard control
- [SysEx Messages]({{ site.baseurl }}/sysex-messages/) - System Exclusive message formats
- [MIDI Serial I/O]({{ site.baseurl }}/midi-serial-io/) - External MIDI hardware and serial port

## Research Needed

- [x] ~~Document external MIDI serial port configuration~~ — Complete: see [MIDI Serial I/O]({{ site.baseurl }}/midi-serial-io/)
- [x] ~~Analyze MIDI routing logic in Main CPU~~ — Complete: see [MIDI Serial I/O]({{ site.baseurl }}/midi-serial-io/)
- [x] ~~Document Technics SysEx message format~~ — Complete: see [SysEx Messages]({{ site.baseurl }}/sysex-messages/)
- [x] ~~Document MIDI filter and channel assignment settings~~ — Complete: 26 voice channels, voice data tables (0xEDB264, 0xEDAE64, 0xEE8EB8-0xEE8F70), channel lookup functions, multi-layer voice system (0-4 layers per channel), drum channel special-casing (0x48), Sub CPU filter tables, accompaniment MIDI filtering
- [x] ~~Map remaining proprietary CC handlers (0x97, 0x9B-0x9D)~~ — Complete: CC91=freq mult, CC95=portamento, CC97=fine pitch, CC9B=vibrato depth, CC9C=vibrato enable, CC9D=tremolo depth
