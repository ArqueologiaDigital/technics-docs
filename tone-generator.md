---
layout: page
title: Tone Generator
permalink: /tone-generator/
---

# Tone Generator (IC303)

The KN5000's tone generator is a custom Matsushita LSI (TC183C230002, IC303) that provides 64-voice polyphonic wavetable synthesis. It is controlled by the Sub CPU via a register-indirect interface and reads waveform data from four 32Mbit ROMs (IC304-IC307).

> **Status:** Register map reverse-engineered from the SubCPU firmware. The tone generator **makes sound only in the
> `kn7000_mame` overlay driver**: mainline MAME maps IC303 (`0x100000`), the keybed port (`0x110000`) and `0x130000` as
> `noprw()` stubs and flags the KN5000 `MACHINE_NO_SOUND`. In the overlay each voice plays the IC307 recording its `+0x040`
> selector names. Voices that select the undumped IC304-IC306 are muted in the default PCM rendering, or sound as a sine
> at their own pitch and envelope under the "PCM from wave ROM (with sine substitutes)" rendering; the wrong-instrument
> copy of IC307 loaded in those sockets is heard only when the build is run with `KN5000_UNDUMPED=play`. See
> [MAME Emulation Status](#mame-emulation-status) below and
> [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/#mame-emulation-status).

## Hardware Overview

| Property             | Value                                                                                                                                                                                                   |
|----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Chip                 | TC183C230002 (Matsushita custom)                                                                                                                                                                        |
| Package Location     | IC303                                                                                                                                                                                                   |
| Voice Count          | 64 independent voices                                                                                                                                                                                   |
| Parameters per Voice | 32 registers (8 groups × 4 banks), staged in a 34-word (68-byte) firmware record                                                                                                                        |
| Global Registers     | 13 (system config + DSP/effects)                                                                                                                                                                        |
| Interface            | Memory-mapped register-indirect (address/data pair)                                                                                                                                                     |
| Address Lines        | SubCPU memory bus + P6.7 (A23, an inference)                                                                                                                                                            |
| Waveform ROMs        | IC304 (QS6GU3C32375), IC305 (QS6GT3C33A01), IC306 (QS6GU3C32374), IC307 (QS6GX3C32008)                                                                                                                  |
| Waveform RAM         | *(none — see note)* IC303 has **no** external work RAM. IC308/IC309 are the two **effects DSPs'** delay DRAMs and are not connected to IC303 (corrected 2026-07-26 from the service-manual schematics). |

## Memory-Mapped Interface

The tone generator uses two separate memory regions with different purposes:

### Register Configuration Interface (0x100000)

Used by the SubCPU to configure voice parameters, system settings, and effects:

| Address  | Width  | Direction    | Purpose                                                                                                                                              |
|----------|--------|--------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| 0x100000 | 16-bit | Write / Read | Register address latch (write); status word (read: latch 0x0000-0x0003 → that bank's active-voice bitmap, 0x0180+ch → that channel's envelope level) |
| 0x100002 | 16-bit | Write        | Register data port (the firmware never reads it)                                                                                                     |

Every register write follows a strict bus protocol:

```asm
RES 7, (P6)          ; P6.7 low
LD (100000h), WA     ; Write register address
NOP                  ; Setup time
SET 7, (P6)          ; P6.7 high
LD (100002h), data   ; Write data value
JR T, next           ; Delay (unconditional jump)
NOP; NOP; NOP        ; Hold time before next write
```

P6 bit 7 is driven LOW before every 0x100000 access and HIGH before every 0x100002 access. The disassembly reads it, as an inference, as the A23 line taken out of bus mode. The sub-CPU boot ROM performs the same burst without touching P6.7, so whether the chip needs it is unresolved.

### Keyboard Input Interface (0x110000)

Used by the SubCPU to read key events from the keybed scanner hosted on IC303 (`Keybed_Read_Event`; see [Keybed Scanning]({{ site.baseurl }}/keybed-scanning/)):

| Address  | Width  | Direction | Purpose                                                                                                                 |
|----------|--------|-----------|-------------------------------------------------------------------------------------------------------------------------|
| 0x110002 | 16-bit | Read      | Status register (bit 0 = event queued, bit 1 = release qualifier)                                                       |
| 0x110000 | 16-bit | Read      | Key event: low byte bits 0-6 = key index, bit 7 = key down; high byte = raw touch reading, not a velocity (0xFF = none) |

P6.7 (A23 address line) also controls which port is accessed: status reads go to 0x110002, data reads go to 0x110000.

## Register Address Encoding

The 16-bit register address has a structured encoding:

```
Bits 15-8: Register Group (function selector)
Bits  7-6: Sub-bank (0-3, for multi-parameter per-voice registers)
Bits  5-0: Channel number (0-63)
```

This gives up to 256 register groups, each with 4 sub-banks of 64 channels.

## Per-Voice Registers

Each of the 64 voices has registers organized into groups. The register address for voice N is calculated as:
`base_offset + (bank * 0x40) + channel_number`

| Offset  | Group | Banks | Struct Offset | Description                                                                                                                               |
|---------|-------|-------|---------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| +0x0000 | 0x00  | 0     | +0x00         | **Control / gate**: 0x8100 note-on gate, 0x7E00 free, 0xF0xx/0xFExx hand-off; latches 0x0000-0x0003 read back as the active-voice bitmaps |
| +0x0040 | 0x00  | 1     | +0x02         | **Recording selector** `(class << 12) + entry` (voice-engine path)                                                                        |
| +0x0080 | 0x00  | 2     | +0x04         | **Output level** (bits 11-0) + 3-bit per-recording field (bits 14-12); bit 15 = burst strobe                                              |
| +0x00C0 | 0x00  | 3     | +0x06         | **Coarse level + expression** (cleared before a voice is freed)                                                                           |
| +0x0100 | 0x01  | 0     | +0x08         | **TVF cutoff**                                                                                                                            |
| +0x0140 | 0x01  | 1     | +0x0A         | **TVF depth / bias**                                                                                                                      |
| +0x0180 | 0x01  | 2     | +0x0C         | **Pan** (0x0040 = centre); latch 0x0180+ch reads back that channel's envelope level                                                       |
| +0x01C0 | 0x01  | 3     | +0x38         | Written by `EGEnv_Compute_B`; not in the note-on burst                                                                                    |
| +0x0400 | 0x04  | 0     | +0x0E         | **Absolute log pitch** (`Pitch_Emit_Reg400`)                                                                                              |
| +0x0440 | 0x04  | 1     | +0x10         | (no reading yet)                                                                                                                          |
| +0x0480 | 0x04  | 2     | +0x12         | (no reading yet)                                                                                                                          |
| +0x04C0 | 0x04  | 3     | +0x14         | **Oscillator config + slot**                                                                                                              |
| +0x0500 | 0x05  | 0     | +0x16         | **Detune / bend pair**                                                                                                                    |
| +0x0540 | 0x05  | 1     | +0x3A         | **Extended param 1** (bit 15 = latch strobe)                                                                                              |
| +0x0580 | 0x05  | 2     | +0x3C         | **Extended param 2** (bit 15 = latch strobe)                                                                                              |
| +0x05C0 | 0x05  | 3     | +0x3E         | **Extended param 3** (bit 15 = latch strobe)                                                                                              |
| +0x0600 | 0x06  | 0     | +0x40         | **Aux routing param 0**                                                                                                                   |
| +0x0640 | 0x06  | 1     | +0x42         | **Aux routing param 1**                                                                                                                   |
| +0x0800 | 0x08  | 0     | +0x18         | **Amplitude envelope, segment 0**: `(target << 8) + rate`, target an attenuation (0xFF = silent; mute word 0xFF80)                        |
| +0x0840 | 0x08  | 1     | +0x1A         | **Amplitude envelope, segment 1** (mute word 0xFF00)                                                                                      |
| +0x0880 | 0x08  | 2     | +0x1C         | **Amplitude envelope, segment 2**                                                                                                         |
| +0x08C0 | 0x08  | 3     | +0x1E         | **Amplitude envelope, segment 3**                                                                                                         |
| +0x0900 | 0x09  | 0     | +0x20         | **Second envelope, segment 0**                                                                                                            |
| +0x0940 | 0x09  | 1     | +0x22         | **Second envelope, segment 1**                                                                                                            |
| +0x0980 | 0x09  | 2     | +0x24         | **Second envelope, segment 2**                                                                                                            |
| +0x09C0 | 0x09  | 3     | +0x26         | **Third envelope, segment 0**                                                                                                             |
| +0x0A00 | 0x0A  | 0     | +0x28         | **Third envelope, segment 1**                                                                                                             |
| +0x0A40 | 0x0A  | 1     | +0x2A         | **Third envelope, segment 2**                                                                                                             |

### ToneGen_WriteVoiceParams Sequence

The firmware's `ToneGen_WriteVoiceParams` function (at subcpu 0x02D101) writes 23 register/data pairs (22 distinct registers) per voice from a 34-word (68-byte) staging record, of which it sends words 1-21. The write order is:

| Step | Register | Struct Offset | Notes                                                                        |
|------|----------|---------------|------------------------------------------------------------------------------|
| 1    | +0x040   | +2            | **Recording selector** `(class << 12) + entry`, sent before the strobe rises |
| 2    | +0x080   | +4            | **Output level** (bit 15 SET = strobe up)                                    |
| 3    | +0x0C0   | +6            | Coarse level + expression                                                    |
| 4    | +0x100   | +8            | TVF cutoff                                                                   |
| 5    | +0x140   | +10           | TVF depth / bias                                                             |
| 6    | +0x180   | +12           | Pan (0x0040 = centre)                                                        |
| 7    | +0x400   | +14           | **Absolute log pitch**                                                       |
| 8    | +0x440   | +16           | (no reading yet)                                                             |
| 9    | +0x480   | +18           | (no reading yet)                                                             |
| 10   | +0x4C0   | +20           | Oscillator config + slot                                                     |
| 11   | +0x500   | +22           | Detune / bend pair                                                           |
| 12   | +0x800   | +24           | Amplitude envelope, segment 0                                                |
| 13   | +0x000   | —             | Control = **0x8100** (note-on gate, an immediate)                            |
| 14   | +0x840   | +26           | Amplitude envelope, segment 1                                                |
| 15   | +0x880   | +28           | Amplitude envelope, segment 2                                                |
| 16   | +0x8C0   | +30           | Amplitude envelope, segment 3                                                |
| 17   | +0x900   | +32           | Second envelope, segment 0                                                   |
| 18   | +0x940   | +34           | Second envelope, segment 1                                                   |
| 19   | +0x980   | +36           | Second envelope, segment 2                                                   |
| 20   | +0x9C0   | +38           | Third envelope, segment 0                                                    |
| 21   | +0xA00   | +40           | Third envelope, segment 1                                                    |
| 22   | +0xA40   | +42           | Third envelope, segment 2                                                    |
| 23   | +0x080   | +4            | Output level again (bit 15 CLEAR = strobe down)                              |

Note: Step 13 writes the constant 0x8100 (key-on) to the voice control register, NOT from the struct. Steps 2 and 23 form a SET/CLEAR strobe pair on register +0x080 bit 15.

### Voice Register Build Chain (Voice_Build_Register_Set)

Before a voice's registers are written, `Voice_Build_Register_Set` (`0x02B4E3`) calls 17 routines in order, each filling part of the staging block at `0x0451CC`:
1. `WaveSel_StageB_Build_Reg040` — recording selector for `+0x040`
2. `Pitch_Apply_Partial_Detune` — per-partial detune
3. `Pitch_Emit_Reg400` — absolute log pitch for `+0x400`
4. `Voice_Level_ComputeTriplet` — second envelope (`+0x900`..`+0x980`)
5. `TVF_Build_Dispatch` — filter
6. `TVF_Emit_Registers` — filter registers (`+0x100`/`+0x140`)
7. `Voice_StereoLevel_Compute` — third envelope (`+0x9C0`..`+0xA40`)
8. `Voice_PortaLevel_Compute` — registers `+0x500` and `+0x8C0`
9. `ExtVoice_Build_SlotRegisters`
10. `Voice_SubVoice_ComputeAndTrigger`
11. `Voice2_UpdatePitch`
12. `Level_Build_Reg0C0` — coarse level + expression for `+0x0C0`
13. `Voice_Build_GateCommand` — the hand-off control word
14. `Voice_Calc_LevelPair_PatchAtk` — amplitude envelope (`+0x800`..`+0x880`)
15. `Voice_WriteChPanShift` (BC = 0)
16. `Voice_ComputePitch`
17. `Voice_ApplyPortamento`

Then `ToneGen_WriteVoiceParams` bursts the block to IC303. The only caller is `Voice_SetVelocity_Type0_BranchA`. (`Voice_Allocate_Typed` only builds a staging slot record for a note-on and touches no hardware.)

### Voice Control State Machine

The voice control register at offset +0x0000 (group 0x00, bank 0) receives these commands:

| Value           | State        | Description                                                                                                                                                                              |
|-----------------|--------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 0x7E00          | Free         | Releases the voice (`ToneGen_SilenceChannel`, `ToneGen_Config_Init`)                                                                                                                     |
| 0x8100          | Note-on gate | A literal, written mid-burst by `ToneGen_WriteVoiceParams`; never computed                                                                                                               |
| 0xF0xx / 0xFExx | Hand-off     | Written once after the burst: routing fields in bits 14-9, output level in the low byte (measured values `F0FF`, `F000`, `F1D7`, `F187`); with bit 15 clear it updates without re-gating |

### Latched Parameter Updates

Several registers use bit 15 as a write strobe: the firmware writes the data value with bit 15 SET, then immediately rewrites the same value with bit 15 CLEAR. This SET-then-CLEAR pattern is used for registers at offsets +0x0080, +0x0540, +0x0580, and +0x05C0.

## Global Registers

These system-wide registers configure overall synthesis and effects:

| Register | Init Value | Description |
|----------|-----------|-------------|
| 0x0200 | 0x0060 | System config 0 (bit 3 conditionally set/cleared) |
| 0x0201 | 0x0993 | System config 1 |
| 0x0202 | 0x0001 | System config 2 |
| 0x0203 | 0x0004 | System config 3 |
| 0x0204 | 0x0004 | System config 4 |
| 0x0205 | 0x000C | System config 5 |
| 0x0C00 | 0x0000 | Effects config 0 |
| 0x0C01 | 0x0000 | Effects config 1 |
| 0x0C02 | 0x0000 | Effects config 2 |
| 0x0C03 | 0x0000 | Effects config 3 |
| 0x0C04 | 0x0020 | Effects config 4 |
| 0x0C05 | 0x0001 | Effects config 5 |
| 0x0E00 | 0x0000 | Master control |

## Initialization Sequence

`DSP_Config_Init` (at `0x02DFA8`), whose per-channel body is `ToneGen_Config_Init` (`0x02DFCF`), performs the following sequence during boot:

1. **Write global config** -- 13 registers (0x0200-0x0205, 0x0C00-0x0C05, 0x0E00) from the ROM table `ToneGen_GlobalConfig_Defaults` (`0x00F8BB`)
2. **Copy voice template** -- 68 bytes from ROM 0xF8D5 to RAM 0x2AA4 (per-voice parameter template)
3. **For each of 64 channels** (0x00-0x3F):
   - Mute volume: register 0x0840 = 0xFF00, register 0x0800 = 0xFF80
   - Write 22 voice parameters from template struct
   - Re-mute volume
   - Set voice to idle: register 0x00C0 = 0x0000, register 0x0000 = 0x7E00
   - Write extended parameters (groups 0x01, 0x05, 0x06) with bit-15 strobe

This produces 2,317 register/data write pairs (confirmed in MAME log analysis).

After configuration, `ToneGen_Poll_Init` runs the keybed's power-on scan, once, from `ToneGen_Init`:
- For each of 16 keybed scan groups:
  - Delay loop (10,000 iterations)
  - Read status from 0x110002
  - Read data from 0x110000
  - Process as "note-off" events

## DSP Interface (0x130000)

A second register-indirect interface at 0x130000 controls DSP processing, accessed by the boot ROM during early initialization:

| Address | Width | Direction | Purpose |
|---------|-------|-----------|---------|
| 0x130000 | 8-bit | Write | DSP register address |
| 0x130002 | 8-bit | Write | DSP register data |

The DSP has 4 processing blocks at 0x20-byte spacing:

| Block | Register Range | Init Register | Init Value |
|-------|---------------|---------------|-----------|
| 0 | 0x00-0x1F | 0x1F | 0x01 |
| 1 | 0x20-0x3F | 0x3F | 0x01 |
| 2 | 0x40-0x5F | 0x5F | 0x01 |
| 3 | 0x60-0x7F | 0x7F | 0x01 |

Registers 0x50-0x57 are zeroed during boot for each block.

### DSP Command Protocol

DSP1 (IC311, uPD6383GF-3BA) uses an 8-bit parallel bus protocol, while DSP2 (IC310, MN19413) uses GPIO bit-bang serial. Both are controlled via Sub CPU GPIO pins:

| Pin | Port | Function |
|-----|------|----------|
| P7.3 | Port 7 bit 3 | Write strobe (active low) |
| P7.4 | Port 7 bit 4 | Read strobe (active low) |
| P7.5 | Port 7 bit 5 | CS1 — DSP1 chip select (IC311, uPD6383GF-3BA) |
| P7.6 | Port 7 bit 6 | Command/Data select (1=command, 0=data) |
| PE.6 | Port E bit 6 | CS2 — DSP2 chip select (IC310, MN19413) |
| PH.0 | Port H bit 0 | Status input (busy/ready) |
| PZ[7:0] | Port Z | 8-bit bidirectional data bus |

**Write handshake:**
1. Set Port Z = data byte
2. Set P7.6 high (command) or low (data)
3. Assert chip select (P7.5 or PE.6 low)
4. Assert write strobe (P7.3 low)
5. Poll PH.0 until ready
6. Deassert write strobe and chip select

### Known DSP Commands

| Command | Description |
|---------|-------------|
| 0x01 | Initialize / reset DSP |
| 0x03 | Set processing mode / algorithm |
| 0x30 | Parameter update (followed by data bytes) |
| 0x60 | Bulk transfer start |

See [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/#dsp-preset-structure) for the effect preset data format.

## Serial Port 1 ("SA" Interface)

The Sub CPU's serial port 1 (UART mode, ~500kHz clock) is the **Computer Interface** (TO HOST connector); in MAME it has been seen to transmit only `0xFE` (MIDI Active Sensing). The "SA" designation found in the service manual schematics refers to "Sub Address" bus lines, not a chip name.

### Serial Configuration

| Parameter | Value |
|-----------|-------|
| Mode | 8-bit UART (SC1MOD = 0x29) |
| Clock | Internal baud rate generator |
| BR1CR | 0x0A (divisor = 10, clock = fCPU/4) |
| Baud Rate | ~500kHz serial clock (20MHz / 4 / 10) |

### Protocol

- **Sync byte**: 0xFE sent during initialization and periodically (every ~135 audio ticks)
- **TX ring buffer**: 1024 bytes at 0x0A00-0x0DFF
- **RX ring buffer**: 512 bytes at 0x0E16-0x1015
- **Special commands**: 0xF4 and 0xF5 trigger baud rate switching and RX enable

## Tone Generator Section IC Inventory

From the service manual schematics (Tone Generator Sections A and B):

| IC | Part Number | Function |
|----|-------------|----------|
| IC303 | TC183C230002 | **Tone Generator LSI** (custom Matsushita) |
| IC304 | QS6GU3C32375 | 32Mbit Waveform ROM |
| IC305 | QS6GT3C33A01 | 32Mbit Waveform ROM |
| IC306 | QS6GU3C32374 | 32Mbit Waveform ROM |
| IC307 | QS6GX3C32008 | 32Mbit Waveform ROM |
| IC308 | M5M418128AJ-6 | 1Mbit DRAM — delay memory for **DSP2 (IC310, MN19413)** |
| IC309 | M5M44260AJ-7S | 4Mbit DRAM — delay memory for **DSP1 (IC311, uPD6383GF)**. Only address lines A0–A8 reach it; A9–A16 are unconnected. |
| IC310 | MN19413 | **DSP2** (Matsushita, serial interface) |
| IC311 | uPD6383GF-3BA | **DSP1** (parallel + memory-mapped) |
| IC312 | M5218AFP | Dual op-amp (DAC output buffer) |
| IC313 | PCM69AU | **D-A Converter** (18-bit stereo, Burr-Brown) |
| IC314 | M5218AFP | Dual op-amp (output buffer) |
| IC315 | D74HC244GS | 3-state buffer |

## Audio Signal Chain

```
Waveform ROMs (IC304-307) ──> Tone Generator LSI (IC303)
                                      │
                                [Memory bus]
                                      │
                                Sub CPU (IC27, TMP94C241F)
                                      │
                        ┌─────────────┼─────────────┐
                        │             │             │
                   [0x100000]     [Serial1]    [0x130000]
                    Register        UART           DSP
                     Config        TO HOST       Config
                        │             │             │
                        v             v             v
                    Tone Gen      Computer      DSP1/DSP2
                     (IC303)      Interface    (IC310/311)
                                      │
                            [Serial Audio: BCK, SDOR/SDOF]
                                      │
                                      v
                                DAC (IC313, PCM69AU)
                                      │
                                Op-amps (IC312, IC314)
                                      │
                                FAJ board (mixing, LPF)
                                      │
                                Power amp ──> Speakers
```

## MAME Emulation Status

The KN5000 tone generator **makes sound** in the `kn7000_mame` overlay driver (not in mainline MAME,
where IC303 is a `noprw()` stub and the machine is flagged `MACHINE_NO_SOUND`): a keyed note plays real
PCM from the one dumped wave ROM (IC307), shaped by the firmware's own envelope, sustains while held, and responds
to velocity — verified in July 2026. The sub-CPU runs its **dumped ROM**, so the envelope, voice
lifecycle and pitch math are executed as real firmware, not re-implemented; the emulation's job is
to model the IC303 chip faithfully enough that those firmware writes produce the right audio.

| Component                   | Address          | Status                                                                                                                                                                                                                                                                       |
|-----------------------------|------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Register Config (0x100000)  | Write **+ Read** | **Tone gen device** — register-address latch on write; **active-voice bitmap on read** (see below)                                                                                                                                                                           |
| Register Data (0x100002)    | Read/Write       | **Tone gen device** — data port, voice status readback                                                                                                                                                                                                                       |
| Keyboard Input (0x110000)   | Read-only        | **Tone gen device** — keybed event queue (note/velocity)                                                                                                                                                                                                                     |
| DSP Config (0x130000)       | Read/Write       | **Driver register file**: `dsp_reg_addr_w` / `dsp_reg_data_w` / `dsp_reg_data_r` on `kn5000_state`, a read-back model of the 4-channel × 8-register block. It is not the uPD6383GF host interface; the optional `upd6383_device`, off by default, takes that over Port PZ/P7 |
| Serial1 (SA interface)      | UART             | **No receiver** — TX sends into void                                                                                                                                                                                                                                         |
| 0x1E0000 (not waveform RAM) | —                | **Nothing there**: the sub CPU never accesses `0x1E0000` on its own bus. Its `0x1E0000` literals are DMA destinations in the main CPU's battery SRAM, and the `noprw()` line only documents the hole                                                                         |
| Sound output                | Stereo 48kHz     | **Audible PCM playback** — real IC307 samples, software envelope, sustain, per-semitone pitch, velocity, polyphony                                                                                                                                                           |

The `kn5000_tonegen_device` (in `kn5000_tonegen.cpp`) implements:
- Register-indirect interface matching the hardware protocol (address latch at 0x100000, data at 0x100002)
- 64 voice states with 32 registers each (8 groups × 4 banks, including group 0xA)
- 13 global configuration registers; voice control state machine (key on/off via group 0 bank 0)
- Waveform ROM reading from the `waveform` region (IC304-IC307, 16 MB); stereo 48 kHz stream with linear interpolation

### Sound generation

- **Real IC307 PCM is audible.** ⚠ A "does this voice have sample data?" test must probe a
  *window* of samples, never the first byte alone: real waveforms routinely start at a
  zero-crossing — IC307 index 0 is a sine beginning at sample 0 — so a first-byte test
  rejects them and the voice falls silent.
- **Envelopes.** The firmware programs three envelopes per voice into IC303: registers `+0x800`..`+0x8C0` (amplitude,
  four segments), `+0x900`..`+0x980` and `+0x9C0`..`+0xA40`. Each segment word is `(target << 8) | rate`, and the
  amplitude target is an attenuation (`0xFF` = silent). The `0xF0xx` word written to group 0/bank 0 is a one-time
  hand-off after the note-on burst (routing fields and output level), not a per-tick amplitude: a held note receives exactly
  one. No rate-to-time law has been measured. The overlay driver runs these segments as an envelope generator inside its
  IC303 model, with an exponential rate law whose two constants are calibrated, not measured. GUI editors
  `SEAMPENV/SEPITENV/SEFILENV` = amplitude/pitch/filter envelopes (same three domains as the KN7000).
- **Held notes sustain.** The firmware polls an **active-voice bitmap by *reading* 0x100000** (it writes a
  bank index 0-3, then reads back a 16-bit "which voices are sounding" word); its software voice-manager
  frees any voice commanded ON but reported silent. The address had been modelled write-only, so the read
  returned 0 and every held note was released after ~45 ms. A `status_r()` handler now returns the
  active-voice bitmap, and note-off is detected from the firmware's release-envelope burst (a real key-up
  programs a release ramp rather than writing `0x7E00`).
- **Per-semitone pitch.** The IC303 is a PCM **multisample** chip: `reg[8]` (group 4/bank 0) steps +0x100
  per semitone *within* a sample zone and resets at zone boundaries, and `reg[1]` (`+0x040`) names the
  recording — so no single register holds an absolute note, and the per-zone sample roots are not in the chip
  registers. An earlier "reg[1] = semitone ratio, reg[8] = octave" model was wrong (every semitone
  collapsed to one pitch). MAME anchors each voice's absolute pitch on the key-bed or MIDI event that
  started it. Demo and rhythm voices have no such event, so for them it uses a per-selector constant, built
  at start-up from the firmware's own multisample SET descriptors. Verified: a chromatic scale
  produces 12 distinct rising pitches; octaves double.
- **Velocity.** The firmware's per-voice loudness is a **log-domain attenuation** in the high byte of
  reg[20] (lower value = louder), velocity-scaled through a log table (`0x0118FE`). MAME expands it
  log→linear, giving a proper dynamic range (soft-vs-hard ≈ 6.5×). Panel Touch-Sensitivity scaling happens
  upstream in the sub-CPU curve, so this widens whatever curve the setting selects.
- **Polyphony.** Simultaneous chord notes share one keybed-scan timestamp, so a naive "most-recent note"
  correlation gave every voice the same note (a chord played as three copies of the root). Fixed with a
  register-anchored pairing: the voices of one chord are distinguished by a monotonic pitch index built
  from `reg[1]` (zone) and `reg[8]` (within-zone offset) and paired in order to the chord's input notes —
  so C-E-G rings as C-E-G, and dual-layer voices (identical index) collapse to the same note.
- **MIDI → internal keybed bridge (velocity).** A host MIDI controller can play the machine's own 61-key
  bed with velocity (`-kbdmidi midiin`), separate from the rear MIDI jacks — a MIDI UART deserializes to
  `kbd_midi_rx()`, which pushes note-on/off events in the same wire format the physical keybed scanner
  uses. See [Keybed Scanning]({{ site.baseurl }}/keybed-scanning/).

**Open / honest limitations:**
- **Waveform selection follows the firmware.** `+0x040` is decoded as `(class << 12) + entry`: the class picks a 1 MB page of
  the 16 MB wave space, and the entry indexes that page's own directory ([Waveform ROM Format]({{ site.baseurl }}/waveform-rom-format/),
  [Tone Database]({{ site.baseurl }}/tone-database/#wave-selection-end-to-end)). A voice whose selector lands on an undumped
  socket (IC304-IC306) is muted in the default PCM rendering, or plays a sine at its own pitch and envelope under
  "PCM from wave ROM (with sine substitutes)"; the `BAD_DUMP` copy of IC307 in those sockets is heard only with
  `KN5000_UNDUMPED=play`. Still open: which physical socket is bank 0, and why `Voice_Init_Type1` adds `(tick & 7)`
  to the whole selector.
- **Waveform ROMs IC304-IC306 are NO_DUMP** (only IC307 is dumped). Whether per-waveform root note / tuning
  / loop points live in IC307's dumped parameter records or elsewhere is being decoded — *not* assumed to
  be in the undumped ROMs.
  - **No CPU wave-read port.** IC303's CPU-facing ports (`0x100000`/`0x100002` register+voice-status,
    `0x110000` keybed events) do not let the CPU address a wave-ROM location and read the sample back. The
    service-mode Wave ROM Check is an *acoustic* test (sine playback, listen for distortion), not a
    checksum. This is unlike the KN7000, whose tone generators expose a wave-memory read port that its
    §8.9 test sweeps digitally — so the KN7000's clean software dump route does **not** transfer here.
    See [KN7000 Expansion Bus & Wave-ROM Dump Routes]({{ site.baseurl }}/kn7000-expansion-and-wave-dump/).
- **No DSP effects in the default build** (reverb, chorus, EQ): the effects DSP (IC311) is a separate
  subsystem. A build with `KN5000_ENABLE_DSP1=1` offers experimental HLE previews of the decoded effects
  through the "Effects, HLE-audible" setting.

The keybed scanner generates note-on/note-off events from MAME input ports. Events are queued in the tone
gen device and read by `Keybed_Read_Event` at 0x110000/0x110002. The full bidirectional note flow
works: keybed (or MIDI bridge) → subcpu → maincpu (for display/chord detection) → subcpu → tone gen
registers. See [Keybed Scanning]({{ site.baseurl }}/keybed-scanning/) for the note encoding format.

## Related Pages

- [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) -- Overall audio architecture
- [Tone Database]({{ site.baseurl }}/tone-database/) -- The factory tone/voice records these registers are loaded from
- [SubCPU Payload Loading]({{ site.baseurl }}/subcpu-payload-loading/) -- How firmware reaches the SubCPU
- [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/) -- Latch communication details
- [Hardware Architecture]({{ site.baseurl }}/hardware-architecture/) -- Full system hardware

## Voice Setup Procedures

The SubCPU firmware provides two voice setup paths, both called via a dispatch table at `0x012159`:

### ToneGen_SetupPolyVoice (Melodic Voices)

Called through `Voice_PolyNoteOn_Setup_PtrTable` for the melodic entries of the auxiliary 8-voice pool (see below); ordinary note-ons do not use it. Performs:

1. **Copy template**: Copies the 68-byte (0x22-word) template `ToneGen_Voice_Param_Template` from ROM `0x012115` to the working buffer at `0x3B1C`. Its first words (LE) are `0xF000, 0x0000, 0x8000, 0x0000, 0x017C, 0x7F7C, 0x0040, 0x0080`, then mostly zeros.
2. **Compute pitch**: MIDI note lookup → octave calculation (`note / 12`), remainder used for fine pitch from table at `0x01217D`
3. **Apply velocity**: `DSP_VelocityToVolume` converts MIDI velocity to volume level, OR'd into struct offset +4 (staging `0x3B20`, register `+0x080`)
4. **Apply effect routing**: `DSP_GetEffectRouting` determines reverb/chorus send levels, OR'd into struct offset +6 (staging `0x3B22`, register `+0x0C0`)
5. **Write all parameters**: Calls `ToneGen_WriteVoiceParams` (23 writes: 21 block words, the `0x8100` gate and the strobe release)
6. **Write control register**: `ToneGen_WriteSingleReg` writes the voice control word

### ToneGen_SetupPercussionVoice (Drum Voices)

Similar to poly but with percussion-specific pitch handling:

1. **Copy template**: Same 68-byte template from `0x012115` to `0x3B1C`
2. **Percussion pitch**: Uses `note / 12` for octave, `note % 12` as drum index (bit 7 cleared). Shifted left 8 bits and OR'd with key-on flag
3. **Octave lookup**: Uses separate table at `0x012195` (vs `0x01217D` for melodic)
4. **Effect routing**: Same `DSP_GetEffectRouting` call
5. **Fixed velocity**: Volume set to 0x0FFF (maximum)
6. **Write parameters**: Same `ToneGen_WriteVoiceParams` + `ToneGen_WriteSingleReg` sequence

The burst order is in [ToneGen_WriteVoiceParams Sequence](#tonegen_writevoiceparams-sequence) above. Every write is padded by a `jr` to the next instruction and three NOPs. The firmware never polls the chip during the burst.

## Keybed Event Decoding

`Keybed_Decode_Event` (at `0x03D11F`, formerly mis-named `ToneGen_Calc_Pitch`) turns a raw keybed event into a MIDI note and a velocity. It computes no tone-generator pitch.

1. **Note**: `(key byte & 0x7F) + 0x24`, so key 0 is MIDI note 36. Bit 7 clear means key up: velocity 0, return.
2. **Velocity**: the raw touch reading indexes `0x01F43E`. Subtract the word at `0x01F418`, multiply by `byte[0x01F420 + 3*curve]`, divide by the word at `0x01F41A`, and add `byte[0x01F421 + 3*curve]`.
3. **Black-key trim**: for note mod 12 in {1, 3, 6, 8, 10}, subtract `byte[0x01F422 + 3*curve]` (`Keybed_Vel_BlackKey_Trim`).
4. **Clamp** to 0-255, then look up `0x01F53E` for the final velocity.

`curve` is the touch-sensitivity byte at `0x004A48` (default 6). See [Keybed Scanning]({{ site.baseurl }}/keybed-scanning/).

## Freeing a Voice

`ToneGen_SilenceChannel` (`0x02B4A1`, formerly `ToneGen_WriteNoteKey`) frees one voice with a two-step register write. Its only caller, `Voice_Manager_PollBank_SlotLoop`, calls it for each voice whose bit in the active-voice bitmap read back from `0x100000` has just gone from 1 to 0. A key-up does not call it directly:
1. Write register `+0xC0` (group 0, bank 3) = `0x0000` — clear coarse level + expression
2. Write register `+0x00` (group 0, bank 0) = `0x7E00` — FREE

## Auxiliary-Pool Note-On (Voice_Poly_NoteOn)

`Voice_Poly_NoteOn` is not the instrument's general note-on path. It handles the internal pseudo-MIDI packets (status ≥ 0xF0) that the DSP code injects to make the tone generator sound a reference tone, and it drives an auxiliary pool of 8 voices:

1. **Counter**: RAM `0x3B13` holds a 3-bit counter, incremented on each note-on and wrapped with `AND 0x7`. It is a pure round robin: the active-voice bitmap is never consulted
2. **Mute**: on the selected slot, register `+0x840` = `0xFF00` and register `+0x800` = `0xFF80`
3. **Dispatch**: the packet's channel (`status & 0x0F`, values above 5 forced to 0) indexes the 6-entry table `Voice_PolyNoteOn_Setup_PtrTable` (`0x012159`). Entry 1 is `ToneGen_SetupPercussionVoice`; the other five are `ToneGen_SetupPolyVoice`
4. **Mark active**: `(0x3B14 + slot)` = note | 0x80

Ordinary note-ons go through the voice engine (`Voice_Build_Register_Set`, above).

## Research Needed

- [x] ~~Determine exact register semantics~~ — Partially: voice control, volume, aux sends documented from write sequence
- [x] ~~Decode voice parameter template at ROM 0xF8D5~~ — two 34-word (68-byte) templates: `ToneGen_VoiceParamShadow_Defaults` (`0x00F8D5`, copied to `0x2AA4` by `DSP_Config_Init` to program all 64 voices at boot) and `ToneGen_Voice_Param_Template` (`0x012115`, copied to `0x3B1C` for each auxiliary-pool note)
- [ ] Map the per-voice registers that still have no reading: `+0x440` and `+0x480`, plus the registers outside the note-on burst (`+0x1C0`, `+0x540`..`+0x5C0`, `+0x600`/`+0x640`)
- [x] ~~Analyze waveform ROM format and sample addressing~~ -- Complete: IC307 format documented. See [Waveform ROM Format]({{ site.baseurl }}/waveform-rom-format/)
- [ ] Document DSP1/DSP2 command sets and processing algorithms
- [ ] Trace the PCM audio serial bus (BCK/SDOR/SDOF) connections
- [x] ~~Identify the exact device connected to Serial Port 1~~ — Computer Interface (TO HOST connector), sends 0xFE Active Sensing
