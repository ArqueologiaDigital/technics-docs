---
layout: page
title: Keybed Scanning
permalink: /keybed-scanning/
---

# Keybed Scanning

The KN5000's 61-key velocity-sensitive keyboard connects directly to the tone generator IC303 (TC183C230002), which performs hardware key scanning internally. The Sub CPU reads completed note events from IC303's keyboard output interface — the CPU does **not** scan the keyboard matrix itself.

> **Status:** Note encoding and voice slot management fully reverse-engineered from SubCPU firmware. HLE keybed implemented in the kn7000_mame overlay's driver (`kn5000.cpp` feeding `kn5000_tonegen`); mainline MAME still maps 0x110000 as a stub, so it has no keybed.
>
> **Correction (2026).** The disassembly has since renamed the two routines this page
> describes and corrected their behaviour: `ToneGen_Read_Voice_Data` is `Keybed_Read_Event`
> (same address, 0x03D0C5) and `ToneGen_Calc_Pitch` is `Keybed_Decode_Event` (same address,
> 0x03D11F) — the old names were wrong, because neither routine touches tone-generator voice
> state. More importantly, **the high byte at 0x110000 is not a linear velocity.** It is a
> raw touch/key-travel-time reading that indexes a lookup-table curve; a *small* raw value
> means a *hard*, loud strike. The sections below have been corrected to describe the real
> curve instead of a direct pass-through.

## Architecture

The note flow is bidirectional — keybed events travel through the Sub CPU to the Main CPU (for display and MIDI output), then note-on commands travel back from the Main CPU through the Sub CPU to IC303 (for sound generation):

```
┌──────────────────────────────────────────────────────────────────┐
│                        NOTE EVENT FLOW                           │
│                                                                  │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │
│  │ KEYBED  │───>│  IC303   │───>│ SUB CPU  │───>│ MAIN CPU │     │
│  │ (keys)  │    │ ToneGen  │    │ firmware │    │ firmware │     │
│  └─────────┘    └──────────┘    └──────────┘    └──────────┘     │
│                   0x110000        DMA latch       Display,       │
│                  (HW scan)       @ 0x120000       MIDI out       │
│                                                                  │
│                 ┌──────────┐    ┌──────────┐    ┌──────────┐     │
│                 │  IC303   │<───│ SUB CPU  │<───│ MAIN CPU │     │
│                 │ ToneGen  │    │ firmware │    │ firmware │     │
│                 └──────────┘    └──────────┘    └──────────┘     │
│                   0x100000        DMA latch     Sound select,    │
│                  (voice cfg)     @ 0x120000     note routing     │
└──────────────────────────────────────────────────────────────────┘
```

**Forward path** (keybed to display):
1. Physical key press detected by IC303 hardware scanner
2. IC303 presents the key index and a raw touch reading at 0x110000, sets status bit at 0x110002
3. `Keybed_Read_Event` (formerly mis-named `ToneGen_Read_Voice_Data`) reads the event, calls `Keybed_Decode_Event` to curve-map the touch reading into a MIDI velocity, and allocates a voice slot
4. `InterCPU_DMA_Send` transmits `[0x90, note, velocity]` to Main CPU via latch
5. Main CPU updates display (key indicators, voice allocation) and emits MIDI

**Return path** (sound generation):
1. Main CPU sends note-on command via latch to Sub CPU
2. Sub CPU `Voice_NoteOn` configures IC303 voice parameters at 0x100000
3. IC303 begins waveform playback from ROMs IC304-IC307

## Hardware Interface

| Address | Width | Direction | Purpose |
|---------|-------|-----------|---------|
| 0x110002 | 16-bit | Read | Status register |
| 0x110000 | 16-bit | Read | Keybed event data (key index + raw touch reading) |

### Status Register (0x110002)

| Bit | Name | Description |
|-----|------|-------------|
| 0 | DATA_READY | 1 = an event is queued; 0 = FIFO empty, data port left untouched |
| 1 | RELEASE_QUALIFIER | 1 = treat this event the same as a `0xFF` touch byte (release path), even though the touch byte itself may not be `0xFF` |
| 15:2 | — | Never tested by either firmware copy |

### Data Register (0x110000)

| Bits | Name | Description |
|------|------|-------------|
| 6:0 | KEY_INDEX | Key index |
| 7 | KEY_STATE | SET = key DOWN, CLEAR = key UP (not a "has velocity" or release flag) |
| 15:8 | RAW_TOUCH | Raw touch/key-travel-time reading — **not a velocity**. It indexes a lookup-table curve (`Keybed_Decode_Event`) that produces the actual MIDI velocity; a *small* value here means a *hard* strike. `0xFF` means "no touch value for this event" and routes to the release/note-off arm. |

## Note Encoding

### Raw Note to MIDI Note

`Keybed_Decode_Event` (at 0x03D11F, formerly mis-named `ToneGen_Calc_Pitch`) adds a fixed offset of **0x24 (36)** to the low 7 bits of the key byte to get the MIDI note:

```
MIDI_note = (key_byte & 0x7F) + 0x24
```

| Raw Note | MIDI Note | Name | Octave |
|----------|-----------|------|--------|
| 0 | 36 | C2 | 2 |
| 12 | 48 | C3 | 3 |
| 24 | 60 | C4 (Middle C) | 4 |
| 36 | 72 | C5 | 5 |
| 48 | 84 | C6 | 6 |
| 60 | 96 | C7 | 7 |

The KN5000 has 61 keys: C2 (raw 0) through C7 (raw 60).

### Touch-to-Velocity Curve

**Correction:** earlier revisions of this page described the high byte as a linear velocity
carried straight through to the DMA packet. It is not — `Keybed_Decode_Event` runs it through
a touch-sensitivity curve (the same curve family as the sub-CPU boot ROM's
`NOTE_VELOCITY_LOOKUP_CALCULATE`, see [Sub-CPU Boot ROM]({{ site.baseurl }}/subcpu-boot-rom/)):

```
raw   = high byte of the 0x110000 word            ; 0xFF = "no touch value" (release)
x     = ToneGen_Velocity_Input_Curve[raw]         ; 256-byte LUT @ 0x01F43E, MONOTONICALLY DECREASING
y     = (x - pivot) * gain / divisor + pivot_out   ; pivot/divisor @ 0x01F418/0x01F41A; gain/pivot_out
                                                    ; from the 3-byte-per-curve table @ 0x01F420
y    -= black_key_trim   if note % 12 in {1,3,6,8,10}   ; the five black keys (table @ 0x01F422)
clamp y to 0..255
velocity = ToneGen_Velocity_Output_Curve[y]        ; 256-byte LUT @ 0x01F53E, MONOTONICALLY INCREASING, max 0x7F (127)
```

`curve` (the touch-sensitivity mode, 0-9) is the byte at RAM `0x4A48`, initialised to **6**
by `ToneGen_Init` and changeable only by `Audio_CmdHandler_A0_BF`. Curve 0 has zero gain: with
touch sensitivity off, every note lands at a fixed level (MIDI velocity 80). The input curve
is monotonically *decreasing* — a **small** raw touch reading means a **hard, loud** strike
(consistent with the raw value being a key-travel *time*, not a force). The black-key trim is
a real mechanical compensation: the five black keys (note % 12 in {1, 3, 6, 8, 10}) sit higher
and travel further, so the same physical force reads as a smaller raw value and needs an
explicit subtraction to land at the same delivered velocity as a white key.

### Note-On / Note-Off Event Format

```
data_word (0x110000) = (raw_touch << 8) | (key_index | key_state_bit7)
status (0x110002):      bit 0 = 1 (data ready), bit 1 = release qualifier
```

- Bit 7 of the low byte is the key **state**: SET = key DOWN, CLEAR = key UP.
- A raw touch byte of `0xFF`, or status bit 1 set, routes the event to the release/note-off
  arm regardless of the key-state bit; `Keybed_Decode_Event` still runs (for the note number)
  but the delivered velocity is forced to 0.

## Voice Slot Table

The Sub CPU maintains a 16-entry voice slot table at RAM address **0x4A4C**:

| Address | Size | Description |
|---------|------|-------------|
| 0x4A4A | 2 bytes | DMA enable flag (non-zero = DMA relay active) |
| 0x4A4C | 16 bytes | Voice slot states (one byte per slot) |

Each slot byte:
- **0xFF** = note active (slot in use)
- **0x00** = slot available

When a note-on event arrives, `Keybed_Read_Event` scans the 16 slots for an available one. When a note-off arrives, the corresponding slot is freed.

## DMA Packet Format

After processing a note event, the Sub CPU relays it to the Main CPU via the inter-CPU latch using `InterCPU_DMA_Send`:

### Note-On Packet

```
Byte 0: 0x90 (MIDI Note On status)
Byte 1: MIDI note number ((key_index & 0x7F) + 0x24)
Byte 2: velocity — the curve-mapped output of Keybed_Decode_Event (see Touch-to-Velocity
        Curve above), not the raw touch byte; the output curve's range is 0x01-0x7F (1-127)
```

### Note-Off Packet

```
Byte 0: 0x90 (MIDI Note On status — velocity 0 = note off per MIDI convention)
Byte 1: MIDI note number ((key_index & 0x7F) + 0x24)
Byte 2: 0x00 (zero velocity = note off)
```

## Key Firmware Routines

| Routine                 | Address  | Description                                                                                                                                    |
|-------------------------|----------|------------------------------------------------------------------------------------------------------------------------------------------------|
| `ToneGen_Init`          | 0x03D016 | Set tone generator mode to 6, begin polling                                                                                                    |
| `ToneGen_Process_Notes` | 0x03D01E | Main loop: read and process all pending events                                                                                                 |
| `Keybed_Read_Event`     | 0x03D0C5 | Read one event from 0x110000, manage voice slots (formerly mis-named `ToneGen_Read_Voice_Data` — it does not touch tone-generator voice state) |
| `Keybed_Decode_Event`   | 0x03D11F | Convert raw key byte + touch reading to MIDI note and curve-mapped velocity (formerly mis-named `ToneGen_Calc_Pitch`)                          |
| `ToneGen_Poll_Init`     | 0x03D1FB | Initial polling: read 16 slots with delay loops (`ToneGen_Poll_Delay`, the inner busy-wait sub-block, is at 0x03D227)                          |
| `ToneGen_Config_Init`   | 0x02DFCF | Configure all 64 IC303 voices and global registers                                                                                             |
| `InterCPU_DMA_Send`     | 0x020C6B | Send 3-byte note packet to Main CPU via latch                                                                                                  |

## MAME HLE Implementation

Since IC303 is a custom ASIC with no public documentation, the MAME driver uses an HLE (High-Level Emulation) device to inject keybed events:

- **6 input ports** (KEY0-KEY5) map PC keyboard keys to 61 piano notes
- A **1ms scan timer** compares current key states against previous states
- Key press/release transitions generate events in the IC303 output format
- Events are queued and served when the SubCPU reads 0x110000/0x110002

In the overlay, the same `kn5000_tonegen` device also takes the IC303 voice writes at 0x100000 and produces sound (the overlay's kn5000 is `MACHINE_IMPERFECT_SOUND`). A host MIDI controller on the overlay's separate `kbdmidi` input (`-kbdmidi <port>`; not the instrument's rear MIDI IN) can also play the key bed with velocity: the overlay converts each velocity back into the raw key-travel time the sub-CPU expects. Mainline MAME stubs both 0x100000 and 0x110000.

### PC Keyboard Mapping

The keybed notes are available as MAME input entries (visible in the Tab menu under "Input (This Machine)") but have **no default PC keyboard assignments** because all candidate keys conflict with control panel button mappings.

To play notes, use MAME's input configuration UI (Tab menu) to assign keys. A suggested piano layout:

**Lower octave (Z row — assign to KEY2 / C4-B4):**

| Suggested Key | Note | MAME Input Name |
|---------------|------|-----------------|
| Z | C4 | C4 |
| S | C#4 | C#4 |
| X | D4 | D4 |
| D | D#4 | D#4 |
| C | E4 | E4 |
| V | F4 | F4 |
| G | F#4 | F#4 |
| B | G4 | G4 |
| H | G#4 | G#4 |
| N | A4 | A4 |
| J | A#4 | A#4 |
| M | B4 | B4 |

**Upper octave (Q row — assign to KEY3 / C5-B5):**

| Suggested Key | Note | MAME Input Name |
|---------------|------|-----------------|
| Q | C5 | C5 |
| 2 | C#5 | C#5 |
| W | D5 | D5 |
| 3 | D#5 | D#5 |
| E | E5 | E5 |
| R | F5 | F5 |
| 5 | F#5 | F#5 |
| T | G5 | G5 |
| 6 | G#5 | G#5 |
| Y | A5 | A5 |
| 7 | A#5 | A#5 |
| U | B5 | B5 |

**Note:** Assigning these keys will also trigger control panel buttons that share the same keys. This is a known limitation — the control panel and keybed share the same physical keyboard namespace.

Fixed velocity of **100** for all key presses (PC keyboards have no velocity sensitivity).

## Related Pages

- [Tone Generator]({{ site.baseurl }}/tone-generator/) — IC303 register map and voice configuration
- [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) — Overall audio architecture and DSP details
- [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/) — Latch communication for note relay
- [Hardware Architecture]({{ site.baseurl }}/hardware-architecture/) — Physical keyboard and PCB layout
