---
layout: page
title: Sound Parameter Protocol
permalink: /sound-parameter-protocol/
---

# Sound Parameter Protocol

This page documents the protocol used by the KN5000 Main CPU to send sound parameter changes to the Sub CPU, traced from the UI widgets all the way to the DSP hardware. The investigation starts with the Reverb settings as a proof of concept, then systematically maps all parameters.

## Architecture (3 layers)

```
┌─────────────────────────────────────────────────────────┐
│  LAYER 1: UI (Main CPU — NAKA Widget System)            │
│                                                         │
│  Widget event (e.g. slider changed)                     │
│    → Lsw* handler function (e.g. LswReverb at F7CFA5)  │
│    → AssswbWr (ring buffer write at FDB1F3)             │
└──────────────────────┬──────────────────────────────────┘
                       │ 4-byte command packets
                       │ via ring buffer at RAM 0xBD3C
                       ▼
┌─────────────────────────────────────────────────────────┐
│  LAYER 2: Inter-CPU Transport                           │
│                                                         │
│  sendCOMM (EF32F4) → DMA latch at 0x140000             │
│  Command byte: bits 7-5 = handler, bits 4-0 = count    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  LAYER 3: Sub CPU (Sound Processing)                    │
│                                                         │
│  INT0 ISR → ring buffer 0x2B0D                          │
│  CC dispatch → Voice_CC_91 (reverb depth, at 0x02A46C) │
│    → Voice_CC_SetReverbDepth: store at voice[ch × 0x11F + 0x7F]   │
│  Voice param structure: 287 bytes/voice at 0x041300     │
└─────────────────────────────────────────────────────────┘
```

## Concrete trace: Reverb Depth (CC#91)

**Sub CPU side (already decoded):**
- `Voice_CC_91` loads channel from `(xiz+1)`, value from `(xiz+3)`
- Calls `Voice_CC_SetReverbDepth`: computes `wa × 0x11F`, points to `0x04137F` (= base 0x041300 + offset 0x7F)
- Stores reverb depth in the per-voice parameter structure

**For comparison, other CC handlers at nearby offsets:**

| CC | Handler | Sub CPU function | Voice offset | Meaning |
|----|---------|-----------------|-------------|---------|
| 0x91 | Voice_CC_91 | Voice_CC_SetReverbDepth | +0x7F | Reverb depth |
| 0x95 | Voice_CC_95 | Voice_CC_SetChorusEnable | +0x72 | Chorus depth |
| (sustain) | Voice_CC_Sostenuto | Voice_CC_SetPortamentoTime | +0x7E | Sostenuto |

## Reverb preset loading path

When a reverb preset is selected on the REVERB & EQ PRESETS screen:
1. `MainRevEqPresetLoad` (at F746F4) dispatches on preset type (reverb-only / EQ-only / combined)
2. `SoundPreset_Dispatch` → `ReverbPreset_Load` takes the preset index (0-9) through
   `ReverbPreset_Table` (**0xEDB36C**, 10 pointers) to a **24-byte reverb record**, copies it to
   RAM `0xFC8E`, and sends the 24 bytes to the Sub CPU with command `0x63`. EQ presets go the same
   way: `EQPreset_Load`, `EQPreset_Table` (9 pointers), 24 bytes to `0xFCA8`, command `0x64`. A
   combined preset is one reverb record followed by one EQ record (`CombinedPreset_Table`)
3. The records (10 reverb, 9 EQ, 9 combined, at `0xEDA6EC-0xEDAA63`) carry the algorithm id in
   byte 0 and `99` in byte 22; every EQ record starts `0x4F`. The `*_FindMatch` routines compare
   the RAM copies with every record to show which preset is current

(Earlier text here read step 3 as "a loop sending 24 commands, one per MIDI channel". It is one
24-byte record sent with one command code. Source: the ext lane's header over the records in
`v10/maincpu/extensions/extension_data.s` and `ReverbPreset_Load`'s header in
`v10/maincpu/audio/audio_control_engine.s`.)

## What we have to work with

**32 Lsw\* functions** — each is a per-parameter widget handler:
- LswReverb, LswDSPEffect, LswDigitalEffect
- LswVolume, LswPan, LswMute
- LswSustain, LswSustainLength, LswSustainPedal
- LswKeyShift, LswTuning, LswBendRange
- LswGlidePedal, LswAfterTouch, LswPartExp
- LswLocalControl, LswMidiChannel, LswOrchestrator
- LswMasterTuning, LswKeyScaling, LswSound
- LswLeftHold, LswEditCheck
- LswPercDecay, LswPercLevel, LswDrawAttack, LswDrawRelease
- LswScalingType/Shift/Shift2/Mode/KeyX

All reference the same parameter table at **0xE952AA** (per-channel config) and **0xE953CE** (value lookup). They all follow the same pattern — they share the exit code at AudioCtrl_PopIzRet1.

## Investigation plan

### Phase 1: Proof of concept — Reverb Depth end-to-end trace

Fully trace LswReverb end-to-end — from the event `0x1E00042` through `Audio_SendCommand` → `Audio_CommandEncoder` → `AssswbWr` → `sendCOMM` → Sub CPU `Voice_CC_91` → voice param offset 0x7F. Verify the command byte encoding.

**Status:** Complete

### Phase 2: Lsw\* function analysis

For each of the 32 Lsw\* functions, identify:
- Which command code it sends (e.g., 0x63 for reverb)
- Which Sub CPU CC handler receives it
- Which offset in the 287-byte voice structure it writes to
- The valid value range

**Status:** Partially complete — see Phase 2 Results below

### Phase 3: Preset tables and DSP parameter mapping

Decode the preset data tables, per-algorithm parameter config blocks, DSP command protocol on the Sub CPU, and complete parameter name catalog.

**Status:** Complete — see Phase 3 Results below

### Phase 4: DSP hardware commands

Trace the DSP configuration path (0x130000 interface) to understand how the Sub CPU programs the actual DSP chips.

**Status:** Not started

---

## Phase 1 Results: Sub CPU Voice Parameter Structure

### Voice_CtrlChange Dispatcher (Sub CPU 0x02A46C)

The Sub CPU function `Voice_CtrlChange` receives 4-byte command packets via the inter-CPU ring buffer and dispatches them to per-CC handler functions. The packet format is:

```
Byte 0: Command type (determines dispatch to Voice_CtrlChange vs other handlers)
Byte 1: Channel number (0x00-0x19, 26 channels total)
Byte 2: CC number (MIDI Control Change number)
Byte 3: CC value (0x00-0x7F typically)
```

The channel number is validated: `cp (xiz + 1), 0x1A` — any channel >= 26 is rejected.

### Per-Voice Parameter Structure

Each voice has a **287-byte (0x11F)** parameter block, with 26 voices starting at base address **0x041300** in Sub CPU DRAM.

**Address formula:** `0x041300 + (channel × 0x11F) + offset`

### Complete CC → Voice Offset Mapping

| MIDI CC | Name | Handler | Voice Offset | Size | Operation | Default |
|---------|------|---------|-------------|------|-----------|---------|
| 0x01 | Mod Wheel | Voice_ModWheel_Apply | (complex) | - | Multi-register update | - |
| 0x07 | Volume | Voice_CC_SetVolume | +0x74 | 2 | Lookup table at 0x011D16 | 0xFE00 |
| 0x0A | Pan | Voice_CC_SetPan | +0x76 | 2 | Store direct | - |
| 0x0B | Expression | Voice_CC_SetExpression | +0x78 | 2 | Lookup table at 0x011D16 | 0xFE00 |
| 0x40 | Sustain | Voice_CC_SetSustain | +0x72 | bit 0 | Set/clear bit 0 | 0 |
| 0x5B | Sostenuto | Voice_CC_SetSostenuto | +0x77 | 2 | Store direct | - |
| 0x5D | Soft Pedal | Voice_CC_SetSoftPedal | +0x7A | 2 | Store direct | - |
| 0x5E | Portamento | Voice_Portamento_OnHandler | (complex) | - | Multi-function chain | - |
| 0x78-0x82 | (Extended) | Jump table at 0x00F739 | various | - | See extended table | - |
| 0x91 | **Reverb Depth** | **Voice_CC_SetReverbDepth** | **+0x7F** | **2** | **Store direct** | **0x00** |
| 0x95 | Chorus Enable | Voice_CC_SetChorusEnable | +0x72 | bit 2 | Set/clear bit 2 | 0 |
| 0x97 | Unknown | Voice_CC_SetChorusDepth | +0x80 | 2 | Store direct | 0x06 |
| 0x9B | Unknown | Voice_CC_SetDelayDepth | +0x8D | 2 | Store direct | 0x01 |
| 0x9C | Pedal Control | Voice_CC_SetDelayEnable | +0x6A | bit 8 | Set/clear bit 8 | 0x00 |
| 0x9D | Unknown | Voice_CC_SetDelayFeedback | +0x8E | 2 | Store direct | 0x00 |

### Extended CC Table (0x78-0x82)

CCs 0x78-0x82 are dispatched via a jump table at Sub CPU ROM 0x00F739 (11 word entries) with base 0x02A306. These include:

| CC | Target | Voice Offset | Purpose |
|----|--------|-------------|---------|
| 0x7B | Voice_CC_SetPortamentoRate | +0x7B | Portamento amount |
| 0x7C | Voice_CC_SetPortamentoDepth | +0x7C | Pitch bend (stores `(value - 0x80) × 2`) |
| 0x7D | Voice_CC_SetPortamentoTime | +0x7E | Sostenuto depth (stores `value - 0x40`) |

### Flags Word at Offset +0x72

The 16-bit word at offset +0x72 is a bitfield shared by multiple CC handlers:

| Bit | CC | Meaning | Set mask | Clear mask |
|-----|-----|---------|----------|------------|
| 0 | 0x40 | Sustain pedal on | 0x0001 | 0xFFFE |
| 2 | 0x95 | Chorus enable | 0x0004 | 0xFFFB |
| 14 | (0x5E chain) | Alt sustain mode | 0x4000 | 0xBFFF |

### Volume and Expression: Lookup Table

CC 0x07 (Volume) and CC 0x0B (Expression) don't store the raw CC value — they use a **lookup table at ROM 0x011D16** to translate the 7-bit CC value into a 16-bit hardware value. This implements a non-linear response curve (likely logarithmic for perceived loudness).

When CC value is 0, a special "mute" value 0xFE00 is stored instead.

### Reverb Depth Trace (CC 0x91) — Complete Path

```
Main CPU UI:
  LswReverb (F7CFA5) handles event 0x1E00042 (value changed)
    → Audio_SendCommand: acquires audio lock #7, formats command
      → Audio_CommandEncoder: command encoding engine (parses format string)
        → AssswbWr (FDB1F3): writes 4-byte packet to ring buffer at 0xBD3C
          Ring buffer: max 127 entries (508 bytes), 4 bytes each

Inter-CPU Transport:
  sendCOMM (EF32F4): reads from ring buffer, acquires audio lock #2
    → InterCPU_Send_Data_Block (EF3345): encodes command byte
      Command byte = (handler_id << 5) | (byte_count - 1)
    → Audio_DMA_Transfer (EF341B): writes payload to DMA latch at 0x140000
      Handshake: wait SSTAT1 high → write → wait SSTAT1 low → DMA

Sub CPU:
  INT0 ISR: receives from latch, HDMA transfers payload to ring buffer 0x2B0D
  Main loop: reads 4-byte packet [type, channel, cc#, value]
    → Voice_CtrlChange (02A46C):
      channel = (xiz+1) = 0x00-0x19
      cc# = (xiz+2) = 0x91
      value = (xiz+3) = 0x00-0x7F
    → Voice_CC_SetReverbDepth:
      extz wa                      ; wa = channel
      muls wa, 0x11F               ; wa = channel × 287
      lda_24 xde, 0x04137f         ; de = base + 0x7F
      lda_dri3 XHL, 0x07, 0xE8, 0xE0  ; store value at [de + wa]
      ret
    → Reverb depth stored at: 0x041300 + (channel × 0x11F) + 0x7F
```

### Reverb Preset Loading Path — Complete

When the user selects a reverb preset on the REVERB & EQ PRESETS screen:

```
Main CPU:
  NAKA widget generates event 0x1E3000A/B/C (preset type: reverb/EQ/combined)
    → MainRevEqPresetLoad (F746F4): dispatches on event
      → SoundPreset_Dispatch: selects preset handler by type
        type 0 (reverb): preset data from ROM 0xEDB36C
        type 1 (EQ):     preset data from ROM 0xEDB394
        type 2 (combined): calls CombinedPreset_Load

  For type 0 (reverb preset):
    → 0xFF0D99: unpacks preset data (24 bytes) from ROM table
    → Loop 24 times (iz = 0..23, one per MIDI channel):
        pushw 0xFF          ; target specifier
        ldw wa, 0x63        ; command code 0x63
        call AssswbWr       ; write to ring buffer
    → SoundParam_NotifyChange: refresh UI display (event 0x4002, widget 0x7F)
```

### Key Addresses Summary

| Address | CPU | Purpose |
|---------|-----|---------|
| 0xBD3C | Main (internal RAM) | Command ring buffer (127 × 4 bytes) |
| 0x140000 | Shared (latch) | Inter-CPU DMA communication port |
| 0x041300 | Sub (DRAM) | Voice parameter structure base |
| 0x011D16 | Sub (ROM) | Volume/Expression lookup table |
| 0x00F739 | Sub (ROM) | CC 0x78-0x82 jump table |
| 0xE952AA | Main (ROM) | Per-channel config table (Lsw functions) |
| 0xE953CE | Main (ROM) | Per-channel value lookup table |
| 0xEDB36C | Main (ROM) | Reverb preset data table |
| 0xEDB394 | Main (ROM) | EQ preset data table |

---

## Phase 2 Results: Lsw\* Function Architecture

### Key Finding: Data-Driven Widget System

The 32 Lsw\* functions are **generic widget callbacks**, not per-parameter command generators. The actual CC/command identity comes from the **NAKA widget configuration data**, not from the Lsw function code.

Each Lsw function handles a specific widget TYPE (slider, on/off toggle, etc.):
- **LswVolume, LswExpression** → numeric slider with mute state (bit 15 check)
- **LswPan** → center-left-right slider (3-way display: "CTR", "L%2d", "R%2d")
- **LswReverb, LswDSPEffect** → numeric slider ("%3d" format)
- **LswSustain, LswDigitalEffect** → on/off toggle ("ON ", "OFF")
- **LswKeyShift** → signed slider ("%+3d")
- **LswTuning** → signed fine-tune ("%+4d")

### Command Flow

```
NAKA Widget Config Data
  (contains: CC number, value range, channel)
    │
    ▼
Lsw* Function (generic handler for widget type)
  handles event 0x1E00042 (value changed)
    │
    ├─ bit 13 set? → Audio_SendCommand (send command to Sub CPU)
    │                  │
    │                  ├─ st32_24 0x03c21c, widget_data  (buffer the widget config)
    │                  ├─ Audio_CommandEncoder (command encoder, reads template at 0x0AD8)
    │                  └─ AssswbWr → ring buffer → sendCOMM → DMA → Sub CPU
    │
    └─ bit 13 clear? → Strcpy (format display string only, no sound command)
```

The per-channel configuration table at **0xE952AA** contains 4-byte flag words. The bit tested by each Lsw function determines whether the parameter is "active" for that channel:

| Lsw Function | Bit Tested | Display Format | Send Command? |
|-------------|-----------|---------------|---------------|
| LswVolume | bit 15 | `"%4d"` / `"MUTE"` | Yes |
| LswMute | bit 15 | `"%4d"` / `"MUTE"` | Yes |
| LswPan | bit 14 | `"CTR"` / `"L%2d"` / `"R%2d"` | Yes |
| LswReverb | bit 13 | `"%3d"` | Yes |
| LswDSPEffect | bit 12 | `"%3d"` | Yes |
| LswSustain | bit 11 | `"ON "` / `"OFF"` | No (Strcpy only) |
| LswSustainLength | bit 10 | `"%2d"` | Yes |
| LswDigitalEffect | bit 3 | `"ON "` / `"OFF"` | No (Strcpy only) |
| LswKeyShift | - | `"%+3d"` | Yes |
| LswTuning | - | `"%+4d"` | Yes |
| LswBendRange | - | `"%3d"` | Yes |
| LswSound | - | `" ------"` | No (Strcpy only) |
| LswGlidePedal | - | `"ON "` / `"OFF"` | No (Strcpy only) |
| LswSustainPedal | - | `"ON "` / `"OFF"` | No (Strcpy only) |
| LswAfterTouch | - | `"ON "` / `"OFF"` | No (Strcpy only) |
| LswKeyScaling | - | `"ON "` / `"OFF"` | No (Strcpy only) |
| LswOrchestrator | - | various | No (Strcpy only) |
| LswLocalControl | - | various | No (special) |
| LswMidiChannel | - | `"CH%2d"` / `"OFF"` | Yes (3 variants) |
| LswMasterTuning | - | `"%+4d"` | Yes (loop-based) |
| LswLeftHold | - | (format at E952A6) | Yes |

### Functions That Send Sub CPU Commands

18 of the 32 Lsw functions call `Audio_SendCommand` to send commands to the Sub CPU. The remaining 14 only update display strings via `Strcpy` — these handle parameters that are processed locally by the Main CPU (sustain toggle, digital effect on/off, sound name display, etc.).

### Remaining Work

To complete the CC-to-Lsw mapping, the NAKA widget configuration data for each screen needs to be decoded. The widget config contains the actual CC number for each parameter control. This is a data-driven system — the same LswReverb handler is used for ALL reverb depth sliders across all screens.

---

## Phase 3 Results: DSP Command Path and Effect Type Mapping

### Two Separate Command Paths

The sound subsystem uses **two completely independent command paths** based on the inter-CPU command byte:

```
CC Path (Voice Parameters):
  Command 0x00-0x1F → Audio_CmdHandler_00_1F
    → Voice ring buffer (0x2B0D)
    → Voice_CtrlChange (02A46C)
    → Per-voice parameter store at 0x041300 + ch × 0x11F + offset

DSP Path (Effect Parameters):
  Command 0x60-0x7F → Audio_CmdHandler_60_7F
    → DSP ring buffer (0x3B60)
    → Audio_Process_DSP (035AE5)
    → DSP algorithm configuration and parameter setting
```

**Command byte encoding:** `(handler_id << 5) | payload_byte_count`
- Reverb presets use **0x63** = handler 3 (DSP), count 3
- EQ presets use **0x64** = handler 3 (DSP), count 4

### DSP Effect Name Table (ROM 0xE331E4)

The firmware maintains a master table of **all DSP effect types** as 16-character display strings starting at 0xE331E4. Each entry is 18 bytes (16 chars + null + 0xFF pad). The full table has 51 entries covering all effect categories:

| Flat Index | Address | Name | Category |
|------------|---------|------|----------|
| 0x00 | E331E4 | VIBRATO | Modulation |
| 0x01 | E331F6 | PITCH SHIFTER | Modulation |
| 0x02 | E33208 | AUTO PAN | Modulation |
| 0x05 | E3323E | CELM | Internal |
| 0x06 | E33250 | CEL | Internal |
| 0x0B | E332AA | PARAMETRIC EQ | EQ |
| 0x0C | E332BC | NOISE FLANGER | Modulation |
| 0x0D | E332CE | SLOW ATTACKER | Dynamics |
| 0x0E | E332E0 | COMPRESSOR | Dynamics |
| 0x0F | E332F2 | EXCITER | Dynamics |
| 0x10 | E33304 | FUZZ | Distortion |
| 0x11 | E33316 | OVERDRIVE | Distortion |
| 0x12 | E33328 | DISTORTION | Distortion |
| 0x17 | E33382 | WAVE REVERB 2 | Reverb |
| 0x18 | E33394 | WAVE REVERB 1 | Reverb |
| 0x19-0x22 | E333A6-E33448 | *(10 more reverbs)* | Reverb |
| 0x23 | E3345A | ROCK ROTARY | Modulation |
| 0x27 | E334A2 | MODULATION DELAY | Delay |
| 0x28 | E334B4 | MULTI TAP DELAY | Delay |
| 0x29 | E334C6 | SINGLE DELAY | Delay |
| 0x2A | E334D8 | GATED REVERB | Reverb |
| 0x2C-0x32 | E334FC-E33568 | ENSEMBLE..NO OPERATION | Various |

(Unused/placeholder entries with "----------" at indices 0x03-0x04, 0x07-0x0A, 0x13-0x16, 0x24-0x26, 0x2B omitted.)

### DSP Algorithm ID → Name Mapping (Pointer Table at 0xE32A7A)

The firmware does NOT use the flat name table index as the DSP algorithm ID. Instead, it uses an **indirect pointer table** at `0xE32A7A` with **40 entries** (4 bytes each). This table maps DSP algorithm IDs (0-39) to name table entries in **reverse display order**:

| Algo ID | Name | Category |
|---------|------|----------|
| 0 | NO OPERATION | None |
| 1 | CHORUS | Modulation |
| 2 | MODULATED CHORUS | Modulation |
| 3 | ENHANCER | Dynamics |
| 4 | FLANGER | Modulation |
| 5 | PHASER | Modulation |
| 6 | ENSEMBLE | Modulation |
| 7 | *(reserved)* | - |
| 8 | GATED REVERB | Reverb |
| 9 | SINGLE DELAY | Delay |
| 10 | MULTI TAP DELAY | Delay |
| 11 | MODULATION DELAY | Delay |
| 12-14 | *(reserved)* | - |
| 15 | ROCK ROTARY | Modulation |
| **16** | **ROOM REVERB 1** | **Reverb** |
| **17** | **ROOM REVERB 2** | **Reverb** |
| **18** | **PLATE REVERB 1** | **Reverb** |
| **19** | **PLATE REVERB 2** | **Reverb** |
| **20** | **CONCERT REVERB 1** | **Reverb** |
| **21** | **CONCERT REVERB 2** | **Reverb** |
| **22** | **DARK REVERB 1** | **Reverb** |
| **23** | **DARK REVERB 2** | **Reverb** |
| **24** | **BRIGHT REVERB 1** | **Reverb** |
| **25** | **BRIGHT REVERB 2** | **Reverb** |
| **26** | **WAVE REVERB 1** | **Reverb** |
| **27** | **WAVE REVERB 2** | **Reverb** |
| 28-31 | *(reserved)* | - |
| 32 | DISTORTION | Distortion |
| 33 | OVERDRIVE | Distortion |
| 34 | FUZZ | Distortion |
| 35 | EXCITER | Dynamics |
| 36 | COMPRESSOR | Dynamics |
| 37 | SLOW ATTACKER | Dynamics |
| 38 | NOISE FLANGER | Modulation |
| 39 | PARAMETRIC EQ | EQ |

The display code at `DspItem0CngFunc` (F355F3) resolves names by: `name_ptr = pointer_table[algo_id]`, then copies the 16-char string to the widget display buffer.

The reverb algorithms occupy IDs **16-27** (12 types = 6 pairs of variant 1/variant 2).

### Per-Algorithm DSP Parameter Configuration (ROM 0xE4465C-0xE4485B)

The firmware uses a data-driven system to map DSP parameter slots to named parameters. Four 128-byte configuration blocks (512 bytes total) at ROM 0xE4465C are organized as **8 rows of 16 bytes**, where each row corresponds to an algorithm **category**:

```
Block layout (4 blocks × 128 bytes):
  Block 0 (E4465C): DSP1 master parameter list (algorithm browser)
  Block 1 (E446DC): DSP1 per-category name indices (UI display mapping)
  Block 2 (E4475C): DSP2 master parameter list
  Block 3 (E447DC): DSP2 per-category name indices
```

**Block 1 — DSP1 Per-Category Name Indices (E446DC):**

| Row | ROM Addr | Category | Slot 0 | Slot 1 | Slot 2 | Slot 3 | Slot 4 | Slot 5 | Slot 6 | Slot 7 |
|-----|----------|----------|--------|--------|--------|--------|--------|--------|--------|--------|
| 0 | E446DC | Distortion/Dynamics | FF | VOLUME | REV SEND | DRIVE | ADJUST | EMPH.GAIN | DEPTH | VOLUME |
| 2 | E446FC | Rotary (treble) | SLOW LFO | FAST LFO | RESONANCE | MANUAL | SLOW/FAST | TREB.FAST | - | SLOW |
| 3 | E4470C | Rotary (bass) | WIND UP | - | WIND DN | - | BASS FAST | BASS SLOW | OSC SPD | - |
| 4 | E4471C | Delay/Chorus/Flng/Phs | DELAY L | DELAY R | FEEDBACK L | DRY/WET D | DRY/WET C | - | DRY/WET F | DRY/WET P |
| **6** | **E4473C** | **Reverb** | **REV TIME** | **PRE DLY** | **HI DAMP** | **ER.LEVEL** | - | - | - | - |

(Rows 1, 5, 7 are empty/unused. Name abbreviations from parameter name table at E324C4.)

**The reverb category has exactly 4 named UI parameters:**
1. **REVERB TIME** (name index 0x22) — Reverb decay time
2. **PRE DELAY** (name index 0x23) — Time before reverb onset
3. **HIGH DAMP GAIN** (name index 0x24) — High-frequency absorption
4. **ER.LEVEL** (name index 0x25) — Early reflections level

The UI display loop at `DspItem0CngFunc` (F355F3) reads: `name_index = ROM[DRAM[10668] + DRAM[0x021098] + slot]`, then resolves the display string from the parameter name table at E324C4.

The category offset in DRAM[0x021098] selects the row: 0x00 for distortion/dynamics, 0x20 for rotary treble, 0x40 for delay/chorus, **0x60 for reverb**, etc.

### Complete DSP Parameter Name Catalog (ROM 0xE324C4)

The parameter name table has **86 entries × 17 bytes**: 16 display characters followed by
a `:` separator — **not** a null terminator (the firmware `Strncpy`s exactly 17 bytes).
Slot 0 and slot 85 are blank spares carrying no colon. Both this table and the unit table
below are now carved and labelled in the disassembly as `DspParamName_Table` /
`DspParamUnit_Table`; the full 86-slot listing, their consumers and the effect-name
tables that sit beside them are on
[DSP Name Tables (Main CPU)]({{ site.baseurl }}/dsp-name-tables/). Key entries:

| Index | Name | Typical Unit | Used by |
|-------|------|-------------|---------|
| 0x01 | VOLUME | - | Distortion/Dynamics |
| 0x03 | REV SEND | - | Distortion/Dynamics |
| 0x04 | DRIVE | - | Distortion/Dynamics |
| 0x07 | DEPTH | - | Modulation effects |
| 0x08 | LFO SPEED | Hz | Modulation effects |
| 0x16-0x17 | DELAY L / DELAY R | ms | Delay effects |
| 0x18-0x19 | FEEDBACK L / FEEDBACK R | - | Delay effects |
| 0x1A-0x1D | DRY/WET (Delay/Chorus/Flanger/Phaser) | - | Various |
| **0x22** | **REVERB TIME** | **s** | **Reverb** |
| **0x23** | **PRE DELAY** | **ms** | **Reverb** |
| **0x24** | **HIGH DAMP GAIN** | - | **Reverb** |
| **0x25** | **ER.LEVEL** | - | **Reverb** |
| 0x26-0x27 | PITCH L / PITCH R | - | Pitch shifter |
| 0x28-0x2D | THRESHOLD / RATIO / ATTACK / RELEASE / SENS. / RATE | - | Compressor/Gate |

A companion unit suffix table at **0xE32418** (86 entries × 2 bytes ASCII, one index shared with the name table) provides the display unit for each parameter. Only four values occur in the whole table: `"  "` (55 slots), `"Hz"` (13), `"ms"` (11) and `"s "` (7) — the one-character units are padded with a trailing **space**, not a NUL.

### Reverb Preset Table — Complete Data (ROM 0xEDA6EC)

All 10 reverb presets stored contiguously at 0xEDA6EC (24 bytes each, 240 bytes total). The pointer table at 0xEDB36C indexes into this region.

| Preset | Algo ID | Algorithm Name | REV TIME | (pad) | PRE DLY | HI DAMP | ER.LVL | Param5 | Param6 | Param7 | B22 |
|--------|---------|---------------|----------|-------|---------|---------|--------|--------|--------|--------|-----|
| 0 | 0x11 (17) | ROOM REVERB 2 | 50 | 0 | 12 | 20 | 50 | 93 | 0 | 0 | 99 |
| 1 | 0x10 (16) | ROOM REVERB 1 | 24 | 0 | 97 | 24 | 99 | 94 | 0 | 0 | 99 |
| 2 | 0x12 (18) | PLATE REVERB 1 | 2 | 0 | 45 | 12 | 50 | 80 | 0 | 0 | 99 |
| 3 | 0x14 (20) | CONCERT REVERB 1 | 46 | 0 | 29 | 20 | 58 | 80 | 0 | 0 | 99 |
| 4 | 0x15 (21) | CONCERT REVERB 2 | 32 | 0 | 60 | 24 | 80 | 78 | 0 | 0 | 99 |
| 5 | 0x16 (22) | DARK REVERB 1 | 20 | 0 | 21 | 24 | 52 | 73 | 0 | 0 | 99 |
| 6 | 0x18 (24) | BRIGHT REVERB 1 | 33 | 0 | 2 | 0 | 96 | 79 | 0 | 0 | 99 |
| 7 | 0x19 (25) | BRIGHT REVERB 2 | 43 | 0 | 26 | 0 | 5 | 58 | 0 | 0 | 99 |
| 8 | 0x1A (26) | WAVE REVERB 1 | 15 | 0 | 17 | 21 | 23 | 79 | 0 | 0 | 99 |
| 9 | 0x1B (27) | WAVE REVERB 2 | 60 | 0 | 26 | 18 | 50 | 86 | 18 | 84 | 99 |

**24-byte preset block structure:**
- **B0:** DSP algorithm ID (0x10-0x1B for reverb types)
- **B1:** REVERB TIME (param slot 0) — range 2-60
- **B2:** Always 0 (padding / unused param slot 1)
- **B3:** PRE DELAY (param slot 2) — range 2-97
- **B4:** HIGH DAMP GAIN (param slot 3) — range 0-24
- **B5:** ER.LEVEL (param slot 4) — range 5-99
- **B6:** Unnamed param 5 — range 58-105 (possibly wet/dry mix or output level)
- **B7-B8:** Unnamed params 6-7 — usually 0 (non-zero only in WAVE REVERB 2: 18, 84)
- **B9-B21:** Zero-padded (unused)
- **B22:** Level — always 99 (0x63, master output level)
- **B23:** Zero

**Note:** B2 (PRE DELAY) is 0 in all 10 factory presets, meaning factory presets use no pre-delay. The user can adjust pre-delay manually via the UI. Preset 9 (WAVE REVERB 2) is the only one with non-zero B7-B8, suggesting the WAVE REVERB algorithm accepts additional modulation parameters.

### EQ Preset Table — Complete Data (ROM 0xEDA7DC)

9 standalone EQ presets stored at 0xEDA7DC (24 bytes each, 216 bytes total). The pointer table at 0xEDB394 indexes into this region.

**EQ presets use algorithm type 0x4F (79)**, which is outside the 40-entry DSP algorithm table — EQ parameters are handled by a separate subsystem.

**24-byte EQ preset structure:**
- **B0:** Algorithm type (always 0x4F)
- **B1:B2:** Band 1 frequency (big-endian 16-bit, range 18-600)
- **B3:B4:** Band 2 frequency (big-endian 16-bit, range 424-1258)
- **B5:B6:** Band 3 frequency (big-endian 16-bit, range 788-1520)
- **B7:B8:** Band 4 frequency (big-endian 16-bit, range 1026-1712)
- **B9:** Constant 0x54 (84)
- **B10-B21:** Zero-padded
- **B22:** Level — always 99
- **B23:** Zero

The four 16-bit values form a monotonically increasing sequence within each preset, strongly suggesting they are **4-band EQ crossover/center frequencies** in Hz.

### Combined Reverb+EQ Preset Table (ROM 0xEDA8B4)

9 combined presets at 0xEDA8B4 (**48 bytes each** = 24 bytes reverb + 24 bytes EQ). The pointer table at 0xEDB3B8 indexes into this region.

The combined preset loader (`CombinedPreset_Load`) reads the first 24 bytes as a reverb preset (sent with command 0x63) and computes `lda xwa, (xwa + 24)` to get the EQ portion's address (sent with command 0x64). Note: `lda` in TLCS-900 is an address calculation, not a memory dereference.

### Sub CPU DSP Command Processing

`Audio_Process_DSP` (035AE5) reads commands from the DSP ring buffer (2KB at 0x3B60) as a byte stream. Each message consists of a 1-byte framing code followed by a 7-byte header:

```
DSP Ring Buffer Message Format (8 bytes):
┌─────────────────────────────────────────────────────────┐
│ [framing] Framing byte: 0x2B/0x2C/0x2D   → DRAM 17256 │
│ [hdr 0]  Voice group (0x30-0x3F, low nibble = voice#)  │
│ [hdr 1]  Sub-qualifier (0x7F for main path)             │
│ [hdr 2]  Sub-command type (see dispatch table below)    │
│ [hdr 3]  Parameter data MSB                             │
│ [hdr 4]  Payload size MSB                               │
│ [hdr 5]  Payload size LSB / additional byte count       │
│ [hdr 6]  End marker / modifier                          │
└─────────────────────────────────────────────────────────┘

Framing byte dispatch:
  0x2B → Voice DSP parameter update (per-voice params)
  0x2C → Channel/voice configuration
  0x2D → DSP effect configuration (preset loads, algorithm changes)

Sub-command types (header byte 2, for framing 0x2B):
  0x00 → Select DSP algorithm (→ DSP_AlgoSelect)
         Stores algo ID in voice structure at offset +0x68
         Multiplies voice# × 0x11F to index into voice table at 0x041368
  0x03 → Effect state control (→ DSP_EffectStateQuery)
  0x10 → Set DSP parameter 0 (→ DSP_VoiceParamReadWrite, bc=0)
  0x11 → Set DSP parameter 1 (→ DSP_VoiceParamReadWrite, bc=1)
  0x12 → Set DSP parameter 2 (→ DSP_VoiceParamReadWrite, bc=2)
  ...
  0x17 → Set DSP parameter 7 (→ DSP_VoiceParamReadWrite, bc=7)
  0x20 → DSP mix/send routing (→ DSP_MixSendConfig)
  0x22 → Additional config (→ DSP_ReadVoiceParam5D)
  0x24 → Additional config (→ DSP_SetVoiceCoefficients)
  0x27 → Additional config (→ DSP_ReadVoiceParam11)
  0x30 → No-op (returns 0)
```

The 0x10-0x17 commands are dispatched via a **jump table at Sub CPU ROM 0x0121DB** (8 word entries).

**DSP_VoiceParamReadWrite** (parameter setter): Takes voice number (wa), parameter index (bc), and data pointer (xde). Computes voice structure address as `0x041368 + voice × 0x11F`, reads/stores the parameter value at offset `0x1D8 + param_index` within the global parameter table at 0x44FCE.

**DSP_AlgoSelect** (algorithm selector): Takes algorithm type ID, validates `< 0x28` (40), allocates/configures the voice slot in the 287-byte voice structure array. Sets bit 0 of the voice flags to mark as allocated.

### DSP Ring Buffer Control Structure (Sub CPU 0x3B60)

| Offset | Address | Field |
|--------|---------|-------|
| +0 | 0x3B60 | Write pointer (16-bit, wraps at 0x800 = 2KB) |
| +2 | 0x3B62 | Read pointer (16-bit) |
| +4 | 0x3B64 | Available byte count (16-bit) |
| +6 | 0x3B66 | Data area base address (32-bit pointer) |

### DSP Parameter Register Addresses

After the effect name table at 0xE3357A, a lookup table maps effect slots to DSP register addresses. The addresses increment by 0x10 per slot:

```
First set:  0x45, 0x55, 0x65, 0x75, 0x85, 0x95, 0xA5, 0xB5
Second set: 0x47, 0x57, 0x67, 0x77, 0x87, 0x97, 0xA7, 0xB7
```

These correspond to the DSP chip's register-indirect access via `0x130000`/`0x130002`, suggesting 8 effect processing slots with parameters addressable in 0x10-byte increments.

### Extended Algorithm Table (80 entries)

The pointer table at 0xE32A7A actually contains **80 entries** (not just 40), covering additional algorithm types including combination effects and the graphic EQ:

| Algo ID Range | Category |
|---------------|----------|
| 0 | NO OPERATION |
| 1-6 | Modulation (Chorus, Mod.Chorus, Enhancer, Flanger, Phaser, Ensemble) |
| 8 | GATED REVERB |
| 9-11 | Delays (Single, Multi-tap, Modulation) |
| 15 | ROCK ROTARY |
| 16-27 | Reverbs (Room/Plate/Concert/Dark/Bright/Wave × 1/2) |
| 32-39 | Distortion/Dynamics (Dist, OD, Fuzz, Exciter, Comp, SlowAtk, NoiseFlng, PEQ) |
| 44-45 | CEL, CELM |
| 48-56 | Extended (AutoPan, PitchShift, Vibrato, PedalWah, AutoWah, RotarySpeaker, RingMod, HARS, MixUp) |
| 57-60, 63 | Presets (Standard, Percussive, Symphonic, Deep Space, String) |
| 64-75 | Combination effects (e.g., S.DELAY+CHORUS, PEQ+COMPRESSOR) |
| 79 | GEQ (Graphic EQ) |

### Key Addresses Summary (DSP Path)

| Address | CPU | Purpose |
|---------|-----|---------|
| 0xE324C4 | Main (ROM) | DSP parameter name table (86 × 17 bytes) |
| 0xE32418 | Main (ROM) | DSP parameter unit suffix table (86 × 2 bytes) |
| 0xE32A7A | Main (ROM) | `DspEffectName_PtrTable` — effect number → name pointer (**128** × 4 bytes) |
| 0xE32C7A | Main (ROM) | `DspEffectName_Strings` — effect names (**128** × 18 bytes, stored in *descending* effect order; the address `0xE331E4` quoted in earlier revisions is where effect 50 lands, i.e. the tail half of the same block) |
| 0xE34DA4 | Main (ROM) | DspItem0CngFunc dispatch table (17 × 2 bytes) |
| 0xE4465C | Main (ROM) | DSP1 master parameter list (128 bytes) |
| 0xE446DC | Main (ROM) | DSP1 per-category parameter name indices (128 bytes) |
| 0xE4475C | Main (ROM) | DSP2 master parameter list (128 bytes) |
| 0xE447DC | Main (ROM) | DSP2 per-category parameter name indices (128 bytes) |
| 0xEDA6EC | Main (ROM) | Reverb preset data (10 × 24 bytes) |
| 0xEDA7DC | Main (ROM) | EQ preset data (9 × 24 bytes) |
| 0xEDA8B4 | Main (ROM) | Combined preset data (9 × 48 bytes) |
| 0xEDB36C | Main (ROM) | Reverb preset pointer table (10 × 4 bytes) |
| 0xEDB394 | Main (ROM) | EQ preset pointer table (9 × 4 bytes) |
| 0xEDB3B8 | Main (ROM) | Combined preset pointer table (9 × 4 bytes) |
| 0x3B60 | Sub (DRAM) | DSP command ring buffer control (2KB, at 15200) |
| 0x0121DB | Sub (ROM) | DSP parameter 0-7 jump table (8 × 2 bytes) |
| 0x041368 | Sub (DRAM) | Voice structure base + 0x68 (DSP algo config) |
| 0x44FCE | Sub (DRAM) | Global DSP parameter storage table |

### Remaining Questions

1. **Main CPU dispatch formatting:** The function `HdaeRom_ProcessBlock` reformats the 4-byte AssswbWr entries into DMA payloads. Further analysis would reveal exactly how preset bytes map to DSP ring buffer message fields.
2. **DSP hardware registers:** The exact register protocol for writing to the DSP chip at 0x130000/0x130002 requires tracing the Sub CPU's DSP parameter output functions (Phase 4).
3. **WAVE REVERB extra parameters:** Preset 9 (WAVE REVERB 2) has non-zero B7-B8 values (18, 84). These likely control waveform modulation parameters unique to the WAVE REVERB algorithm.
4. **EQ crossover frequencies:** The 4 big-endian 16-bit values in EQ presets need verification as frequency values (Hz). The monotonic ordering suggests crossover points for a 4-band parametric EQ.
