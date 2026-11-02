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
                     Latch 0x140000 → 0x120000 │
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

| Status | Range                                      | Handler                                                                                     | Voice Handler                                             | Description                                                                                                            |
|--------|--------------------------------------------|---------------------------------------------------------------------------------------------|-----------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------|
| 0x80   | Parameter query/action (not MIDI Note Off) | inline in `MIDI_Dispatch_ParseStatus` (bit 3 set → `MIDI_Status_NoteOn_Extended`, misnamed) | `Voice_ParamFinalize`                                     | 6-byte record staged at 0x2AE8 (0x2AEE when bit 3 is set); bit 3 set = action, no reply; clear = query, always replies |
| 0x90   | Note On                                    | `MIDI_Status_NoteOn`                                                                        | `Voice_NoteOn` (`Voice_Poly_NoteOn` when byte +1 >= 0xF0) | Note On (3 bytes)                                                                                                      |
| 0xB0   | Control Change                             | `MIDI_Status_CtrlChange`                                                                    | `Voice_CtrlChange`                                        | CC messages (3 bytes)                                                                                                  |
| 0xC0   | Program Change                             | `MIDI_Status_ProgChange`                                                                    | `Voice_ProgChange`                                        | Patch selection (4 bytes)                                                                                              |
| 0xD0   | Channel Pressure                           | `MIDI_Status_ChanPressure`                                                                  | `Voice_ChanPressure`                                      | Aftertouch (3 bytes)                                                                                                   |
| 0xE0   | Pitch Bend                                 | `MIDI_Status_PitchBend`                                                                     | `Voice_PitchBend`                                         | Pitch wheel (3 bytes)                                                                                                  |
| 0xF0   | System                                     | `MIDI_Status_System`                                                                        | `Voice_SystemMsg`                                         | System messages (3 bytes)                                                                                              |

### Message Format

Messages are read from the ring buffer at 0x2B0D:

```
Note On (standard):     [status] [channel] [note] [velocity]
Parameter record (0x8n): [status] [part] [offset] [length] [reply tag] [spare]
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
    CALL MIDI_Backlog_Publish   ; Publish byte count to the backlog gauge at 0x27E7
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

| CC#  | Handler                  | Parameter        | Notes                                                   |
|------|--------------------------|------------------|---------------------------------------------------------|
| 0x01 | `Voice_CC_ModWheel`      | Modulation Wheel | Vibrato depth                                           |
| 0x07 | `Voice_CC_Volume`        | Main Volume      | Channel volume                                          |
| 0x0A | `Voice_CC_Pan`           | Pan              | Stereo position                                         |
| 0x0B | `Voice_CC_Expression`    | Expression       | Dynamics control                                        |
| 0x40 | `Voice_CC_Sustain`       | Sustain Pedal    | Hold notes                                              |
| 0x5B | `Voice_CC_ReverbSend`    | Reverb send      | The part's reverb send level (part parameter 0x05B)     |
| 0x5D | `Voice_CC_DspEffectSend` | DSP-effect send  | The part's DSP-effect send level (part parameter 0x05D) |
| 0x5E | `Voice_CC_Portamento`    | Portamento       | Glide control                                           |

### Proprietary Controllers

Offsets are from the part record at `0x041368 + part × 0x11F`. Each setter stores one byte of the part record;
the readers of those bytes say what the controller is (traced 2026-10-31, disassembly
`notes/open4-kn5000-b/midi/README.md`, issue kn5000-5ck).

| CC#  | Handler                    | Parameter                            | Part byte   | Notes                                                                                                                              |
|------|----------------------------|--------------------------------------|-------------|------------------------------------------------------------------------------------------------------------------------------------|
| 0x91 | `Voice_CC_VelSwitchConfig` | velocity-switch configuration (part) | +0x17       | `Voice_CC_SetVelSwitchConfig`; read by the `Voice_Env_ApplyVelocity_*` dispatchers; sent by `SwbtB2_Code9A_Listener` for parts 0-2 |
| 0x95 | `Voice_CC_GlidePedal`      | glide pedal on/off                   | +0x0A bit 2 | `Voice_CC_SetGlidePedal` (part parameter 0x603)                                                                                    |
| 0x97 | `Voice_CC_SustainLength`   | sustain length                       | +0x18       | `Voice_CC_SetSustainLength`, raw byte (part parameter 0x600)                                                                       |
| 0x9B | `Voice_CC_GateRoutingMode` | gate-word routing override           | +0x25       | `Voice_CC_SetGateRoutingMode`; nibbles 0/1/2 force bits 11:9 / 14:12 of the gate word to 7 / leave / 1; no sender found            |
| 0x9C | `Voice_CC_KeyScaling`      | key scaling on/off                   | +0x02 bit 8 | `Voice_CC_SetKeyScaling` (part parameter 0x602)                                                                                    |
| 0x9D | `Voice_CC_TgPanMode`       | TG register 0x180 (pan) override     | +0x26       | `Voice_CC_SetTgPanMode`; 1 = 0x00, 2 = 0x7F, else the voice's own value; no sender found                                           |

What the three bytes do, from their readers (sub CPU v1.42):

- **0x91** (`0x04137F`): read by `Voice_Env_ApplyVelocity_Type0` / `_Type2`, sub-cases 2 and 3 only. It is the
  part's own velocity-switch configuration, twin of the global byte `0x04134B` (`Voice_SetVelSwitchConfig`,
  sub-command `F0 50 91`). Bit 3 (type 0/1) or bit 4 (type 2) set = nothing; else bit 0 (case 2), or bit 0 with
  bit 1 clear (case 3), lets `Instrument_LookupProgram_HiNibble` / `_LoNibble` install the patch's +0x2A
  octave-shift nibble into part +0x6D. Reset value 0.
- **0x9B** (`0x04138D`): read by `Voice_Apply_GateRouting`, called by `Voice_Build_GateCommand` and
  `Voice_Build_GateCommand_NoPartial`. It patches the voice's gate/control word (TG bank +0x000). Low nibble:
  0 = force bits 11:9 to 7, 1 = leave, 2 = force to 1. High nibble 0x00 / 0x10 / 0x20: the same for bits 14:12.
  Reset value 1.
- **0x9D** (`0x04138E`): read by `Voice_Level_ClearAllOutputRegs`, `Voice1_UpdatePitch_WriteStereoField` and
  `Voice_Step_ExprRamp`. It chooses the low 7 bits of the voice's TG register 0x180 (pan on
  [Tone Generator]({{ site.baseurl }}/tone-generator/), 0x40 = centre): 1 = 0x00, 2 = 0x7F, anything else = the
  voice's own value. Reset value 0.

The reset values are those `Voice_ResetAllControllers` writes. **Senders.** `SndPart_SetParam` sends none of the
three. A search of every `MIDI_SendControlChange` call in the v10 tree finds one sender of 0x91 and none of
0x9B / 0x9D: `SwbtB2_Code9A_Listener` (`audio/note_voice_mapping.s`), which for parts 0, 1 and 2 sends CC 0x91
with value payload 3 AND payload 2. The global byte is sent by `AudioInit_VoiceParamCtrl` as `F0 50 91 <(0xC5A8)>`.
Controllers above 0x7F cannot arrive on MIDI IN, so 0x9B and 0x9D stay at their reset values unless code the search
did not find sends them (the HD-AE5000 was searched too). That they are dormant in v10 is a finding of the search,
not a proof.

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
    JRL Z, Voice_CC_TgPanMode
    CP A, 09Ch
    JRL Z, Voice_CC_KeyScaling
    ; ... check other CC numbers
    CP A, 001h
    JR Z, Voice_CC_ModWheel
    ; etc.
```

## External MIDI (Main CPU)

The Main CPU handles external MIDI I/O via serial ports:

| Function  | Description                                              |
|-----------|----------------------------------------------------------|
| MIDI IN   | Receives external MIDI, routes to internal synth or THRU |
| MIDI OUT  | Transmits keyboard events, sequencer playback            |
| MIDI THRU | Hardware echo of MIDI IN                                 |

### MIDI Implementation

Traced from the firmware (2026-10-31, issue kn5000-ake; the Technics SysEx formats are on
[SysEx Messages]({{ site.baseurl }}/sysex-messages/#technics-0x50-messages-on-midi)):

| Feature          | What the firmware does                                                                                                                                             | Where                                                |
|------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------|
| Channel messages | 8n, 9n, Bn, Cn, Dn, En dispatched; An (poly pressure) is ignored                                                                                                   | `MIDI_CHANNEL_MESSAGE_DISPATCHER`, midi-serial-io.md |
| Parts            | 26 internal parts (0x00-0x19) in the sub CPU; the main CPU maps MIDI channels to parts                                                                             | `Voice_CtrlChange` rejects part >= 0x1A              |
| Controllers      | 0x01, 0x07, 0x0A, 0x0B, 0x40, 0x5B, 0x5D, 0x5E, the channel-mode range 0x78-0x7F (0x7A, 0x7C-0x7F ignored), internal 0x80-0x82, 0x91, 0x95, 0x97, 0x9B, 0x9C, 0x9D | `Voice_CtrlChange`; table above                      |
| Program change   | `{5, C0, part, program, bank, effect}` record to the sub CPU after `SndParam_ApplyMaskClamp`                                                                       | `SndPart_SendProgramChange`, sound-categories.md     |
| Bank select      | received Cn remapped through descriptor +0x38 into Bn 00, Bn 20, Cn                                                                                                | `SndParam_LookupFromPointerTable`                    |
| System real time | F8 clock (96 PPQN internal), FA/FB/FC; F8 sent on MIDI OUT; FE sent while bit 4 of 0xFD50 is set                                                                   | midi-serial-io.md                                    |
| SysEx            | Technics 0x50 (handshake, dump, parameter change/request, tempo), Universal 7E (GM On/Off), Roland 41 GS (reverb/chorus)                                           | sysex-messages.md                                    |
| GM mode          | descriptor mode 1 (128 GM voices, GS drum-set map) selected by `SndParam_LookupReadOnly(0xC0)`                                                                     | sound-categories.md                                  |

## MIDI Channel Assignment and Voice Routing

The KN5000 supports 26 internal voice channels (0x00-0x19) mapped to 16 external MIDI channels (0-15). The Main CPU manages the voice-to-channel mapping via data structures in DRAM.

### Voice Data Tables

| Address    | Purpose                                                                               | Stride   |
|------------|---------------------------------------------------------------------------------------|----------|
| `0xEDB264` | `PanelTlv_CompanionByPart`: companion-record payload pointer by part tag (32 entries) | 4 bytes  |
| `0xEDAE64` | `PanelTlv_PayloadByTag`: RAM address of each panel-memory record's payload, by tag    | 4 bytes  |
| `0xEE8EB8` | Voice channel configuration                                                           | variable |
| `0xEE8ED8` | Channel assignment data (active flags)                                                | variable |
| `0xEE8F22` | Voice allocation table                                                                | 5 bytes  |
| `0xEE8F2E` | Voice layer table (layers 0-4)                                                        | 13 bytes |
| `0xED92F2` | `PanelTlv_CompanionPartTags`: the 23 part tags `PanelTlv_ResolvePartCompanions` walks | 1 byte   |

### Channel Lookup Functions

These two routines are panel-memory TLV lookups, not MIDI-channel voice tables; the record tags are documented on [Panel Memory Factory Data]({{ site.baseurl }}/panel-memory-factory-data/).

**`PanelTlv_CompanionOfPart`** (Main CPU, `audio/audio_control_engine.s`):
- Input: A = part tag (0x00-0x1F), or 0x48 = the style record
- For a part tag, looks up its companion record's payload at `0xEDB264 + tag * 4`; for 0x48, returns tag 0x49's payload (RAM 0xFF92)
- Returns the pointer in XHL (0xFFFFFFFF for any other tag)

**`PanelTlv_PayloadOfTag`** (Main CPU, `audio/audio_control_engine.s`):
- Input: A = record tag
- Looks up the RAM address of that record's payload at `0xEDAE64 + tag * 4`
- Returns the pointer in XHL (0xFFFFFFFF = none)

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

**`PanelVari_SetGroupSlot`** (`audio/audio_control_engine.s`):
- Stores companion[group] = slot: the sound (or, for 0x48, the style) last chosen in a SOUND GROUP / RHYTHM GROUP
  ([companion records]({{ site.baseurl }}/floppy-disk-formats/#how-each-kind-is-typed)); `PanelVari_GetGroupSlot`
  reads it back when a group button is pressed
- Input: A = part tag (0x00-0x1F; 0x48 = the style record), C = group, E = slot
- Writes through `PanelTlv_CompanionOfPart`; for 0x48 the index limit is 0x0F
- Formerly misnamed `MIDI_DistributeParamToChannels` (renamed 2026-11-02, disassembly
  `notes/open6-kn5000-d/panel/README.md`)

### Voice Channel Architecture

The KN5000 uses a multi-layer voice system where each MIDI channel can have multiple voice layers:

- **26 internal voice channels** (0x00-0x19): Used by Sub CPU for tone generation
- **16 external MIDI channels** (0-15): Standard MIDI, mapped to voice channels
- **Voice layers** (0-4): Each MIDI channel can split into up to 5 layers (e.g., left hand, right hand, split zones)
- **Tag 0x48** is special-cased by `PanelTlv_CompanionOfPart` and `PanelVari_SetGroupSlot`: it is the panel memory's style record (companion: tag 0x49 at RAM 0xFF92), not a drum channel

### Sub CPU Voice Filtering

**`Voice_LoadFilterTable_Ch`** (Sub CPU, 0x027534):
- Input: A = part, C = ramp position; loads the part's filter frequency and Q
- Writes to the tone-generator staging block in DRAM (`ToneGen_StagingBlock`, 0x0451CC), not to tone-generator registers:
  - `0x04520A`: Filter frequency
  - `0x04520E`: Filter Q
  - the part record fields at 0x0413C1 / 0x0413BF + part × 0x11F, then broadcast via `Voice_BuildOutputList` and `ToneGen_WriteExtParams_56b`
- Floors the filter frequency at 0x1C (smaller values are raised to 0x1C)

**`Voice_LoadFilterTable_All`** (Sub CPU, 0x027623):
- Input: A = part; the unscaled counterpart of `Voice_LoadFilterTable_Ch`
- Writes 0x04520A / 0x04520E and broadcasts with `ToneGen_WriteExtParams_56b`

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

| Routine                     | Address  | Description                                                           |
|-----------------------------|----------|-----------------------------------------------------------------------|
| `MIDI_Dispatch`             | 0x034D93 | Main MIDI message dispatcher                                          |
| `MIDI_Dispatch_ParseStatus` | 0x034DA2 | Parse status byte                                                     |
| `MIDI_Status_NoteOn`        | 0x034E65 | Note On handler (0x90 only; 0x80 records go to `Voice_ParamFinalize`) |
| `MIDI_Status_CtrlChange`    | 0x034EB2 | Control Change handler                                                |
| `MIDI_Status_ProgChange`    | 0x034EEB | Program Change handler                                                |
| `MIDI_Status_ChanPressure`  | 0x034F2D | Channel Pressure handler                                              |
| `MIDI_Status_PitchBend`     | 0x034F65 | Pitch Bend handler                                                    |
| `MIDI_Status_System`        | 0x034F9C | System message handler                                                |
| `Voice_NoteOn`              | 0x02CF97 | Voice note-on processing                                              |
| `Voice_CtrlChange`          | 0x02A282 | Voice CC processing                                                   |
| `Voice_CC_ModWheel`         | 0x02A306 | Mod wheel handler                                                     |
| `Voice_CC_Volume`           | 0x02A31C | Volume handler                                                        |
| `Voice_CC_Pan`              | 0x02A340 | Pan handler                                                           |

### Main CPU (`maincpu/`)

| Routine                           | File                              | Description                                                                         |
|-----------------------------------|-----------------------------------|-------------------------------------------------------------------------------------|
| `MIDI_CHANNEL_MESSAGE_DISPATCHER` | `midi_serial_routines.s`          | External MIDI message dispatcher                                                    |
| `MIDI_DispatchCC`                 | `midi/midi_dispatch_handlers.s`   | CC dispatch via jump table at 0xFD175E                                              |
| `MidiChannel_ConfigureController` | `midi/midi_dispatch_handlers.s`   | Configure MIDI controller for voice channel                                         |
| `PanelVari_SetGroupSlot`          | `audio/audio_control_engine.s`    | Distribute param to all active channels                                             |
| `PanelTlv_CompanionOfPart`        | `audio/audio_control_engine.s`    | Part tag → companion record's payload (0xEDB264; 0x48 = style record)               |
| `PanelTlv_PayloadOfTag`           | `audio/audio_control_engine.s`    | Record tag → payload address (0xEDAE64)                                             |
| `NoteMap_LookupVoice`             | `note_voice_mapping.s`            | Find voice slot for note event                                                      |
| `NoteMap_SetChannelParam`         | `note_voice_mapping.s`            | Set MIDI channel parameter in note map                                              |
| `Voice_DecodeNoteChannel`         | `sequencer/seq_event_playback.s`  | Decode note channel to voice assignment                                             |
| `PanelTlv_ResolvePartCompanions`  | `audio/tonegen_fileio_handlers.s` | Resolve the companion record of each of the 23 tags in `PanelTlv_CompanionPartTags` |

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
- [x] ~~Document MIDI filter and channel assignment settings~~ — Complete: 26 voice channels, voice data tables (0xEDB264, 0xEDAE64, 0xEE8EB8-0xEE8F70), channel lookup functions, multi-layer voice system (0-4 layers per channel), style-record special-casing (tag 0x48), Sub CPU filter tables, accompaniment MIDI filtering
- [x] ~~Map remaining proprietary CC handlers~~ — 0x91 = per-part velocity-switch configuration, 0x95 = glide pedal, 0x97 = sustain length, 0x9B = gate routing override, 0x9C = key scaling, 0x9D = TG pan override (2026-10-31; the earlier reverb/chorus/delay readings had no reader behind them).
