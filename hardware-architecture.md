---
layout: page
title: Hardware Architecture
permalink: /hardware-architecture/
---

# KN5000 Hardware Architecture

Detailed hardware documentation extracted from the service manual schematics.

> **See Also**: [System Overview]({{ site.baseurl }}/system-overview/) for a high-level architecture diagram showing how all subsystems connect.

## System Overview

```
┌────────────────────────────────────────────────────────────────┐
│                         CONTROL PANEL                          │
│  ┌──────────────┐  ┌─────────┐  ┌─────────┐  ┌──────────────┐ │
│  │     CPL      │  │  CPCL   │  │  CPCR   │  │     CPR      │ │
│  │ M37471M2196S │  │ Switches│  │ Switches│  │ M37471M2196S │ │
│  │   8-bit MCU  │  │  LEDs   │  │         │  │   8-bit MCU  │ │
│  └──────┬───────┘  └────┬────┘  └────┬────┘  └──────┬───────┘ │
│         │ SIN/SOUT/CLK  │            │       SIN/SOUT/CLK │   │
└─────────┼───────────────┴────────────┴────────────────────┼───┘
          │                                                 │
          └────────────────────┬────────────────────────────┘
                               │ Serial Bus
┌──────────────────────────────┴─────────────────────────────────┐
│                          MAIN PCB                              │
│                                                                │
│  ┌─────────┐    Latch     ┌─────────┐                         │
│  │  IC5    │◄──0x140000──►│  IC27   │                         │
│  │Main CPU │              │ Sub CPU │                         │
│  │TLCS-900 │              │TLCS-900 │                         │
│  └────┬────┘              └─┬──┬──┬─┘                         │
│       │                     │  │  │                            │
│  ┌────┴────┐           ┌────┘  │  └────┐                      │
│  │ IC206   │           │       │       │                      │
│  │  LCD    │      ┌────┴───┐ ┌─┴────┐ ┌┴───────┐             │
│  │ MN89304 │      │ IC303  │ │IC311 │ │ IC310  │             │
│  └────┬────┘      │Tone Gen│ │ DSP1 │ │  DSP2  │             │
│       │           │TC183C..│ │Effect│ │Mix/EQ  │             │
│  ┌────┴────┐      └────┬───┘ └──────┘ └────────┘             │
│  │ IC207   │           │                                      │
│  │ VRAM    │      ┌────┴───┐                                  │
│  │4Mbit    │      │IC304-7 │   ┌────────┐                    │
│  └─────────┘      │Waveform│   │ IC208  │                    │
│                    │ ROMs   │   │  FDC   │                    │
│                    └────────┘   └────────┘                    │
└───────────────────────────────────────────────────────────────┘
```

**Signal flow:** Main CPU handles UI, sequencing, and high-level music control. It sends MIDI-like commands to the Sub CPU through a pair of latches (IC22/IC23) that it addresses at 0x140000 and the Sub CPU addresses at 0x120000. The Sub CPU translates these into low-level register writes for the tone generator (IC303) and DSP chips (IC310, IC311). Waveform data is stored in four mask ROMs, IC304-IC307; only **IC307 is dumped**. Audio output goes through the DSPs for effects processing and mixing before reaching the DAC.

## Control Panel MCUs

### Chip Identification

**Mitsubishi M37471M2196S** (both CPL and CPR boards)

- 8-bit CMOS microcomputer
- Mitsubishi 740 series architecture
- Built-in A/D converter (8 channels)
- Serial interface (UART)
- Up to 16 segment outputs for LED multiplexing
- Mask ROM version (M2196S = specific mask pattern)

### CPL Board (Control Panel Left)

| Pin/Signal | Function |
|------------|----------|
| `SIN` | Serial data input (from main CPU) |
| `SOUT` | Serial data output (to main CPU) |
| `CLK` | Serial clock |
| `CNTR1` | Control/chip select |
| `CMD0-CMD4` | Command lines |
| `SW0-SW7` | Switch matrix inputs |
| `SEG00-SEG10` | LED segment outputs |
| `ROTA`, `ROTB` | Rotary encoder inputs |
| `AD0-AD3` | A/D converter inputs |
| `BEND` | Pitch bend wheel (analog) |
| `MOD0`, `MOD1` | Modulation inputs (analog) |
| `MAIN VOLUME` | Master volume (analog) |

### CPR Board (Control Panel Right)

| Pin/Signal | Function |
|------------|----------|
| `SIN` | Serial data input |
| `SOUT` | Serial data output |
| `CLK` | Serial clock |
| `CNTR1` | Control/chip select |
| `CMD0-CMD4` | Command lines |
| `SW0-SW7` | Switch matrix inputs |
| `SEG00-SEG15` | LED segment outputs |

### LED Driver ICs

**HD74LS07P** - Hex buffer/driver with open-collector outputs
- Used for driving LED segments
- Multiple ICs per board (IC2, IC3)

## Main Board ICs

### Main CPU

**IC5: TMP94C241F**
- Toshiba 32-bit TLCS-900/H2 microcontroller
- 24-bit address space (16 MB); the board's own decode network uses A16-A22
- Data bus: D0-D15 (16-bit)
- Multiple serial channels
- DMA controller
- Timers

### Sub CPU (Tone Generator Controller)

**IC27: TMP94C241F**
- Toshiba 32-bit TLCS-900/H2 microcontroller (same as main CPU)
- Up to 20 MHz clock
- 16 MB linear address space (24-bit addresses)
- 2 KB on-chip RAM at 0x000400-0x000BFF

**Memory Map:**

| Address           | Size  | Description                                                      |
|-------------------|-------|------------------------------------------------------------------|
| 0x0000-0x00FF     | 256B  | Special Function Registers (SFR)                                 |
| 0x0100-0x01FF     | 256B  | Extended SFR (memory controller, DMA, watchdog)                  |
| 0x0400-0x04E0     | 225B  | Interrupt trampolines (copied from ROM)                          |
| 0x0500-0x05A2     | ~160B | RAM / Stack area                                                 |
| 0x000000-0x0FFFFF | 1MB   | Work DRAM (IC28/IC29)                                            |
| 0x100000          | -     | Tone generator IC303 registers (address +0, data +2)             |
| 0x110000          | -     | Tone generator keybed data (+0) / status (+2)                    |
| 0x120000          | -     | Inter-CPU communication latch                                    |
| 0x130000          | -     | DSP1-associated register block (4 channels; address +0, data +2) |
| 0xFE0000-0xFFFFFF | 128KB | Boot ROM                                                         |

**I/O Capabilities:**
- 2 serial channels (SC0, SC1)
- 4 8-bit timers (T0-T3)
- 16-bit timer (T4)
- DMA controller (channels 0 and 2 used)
- Multiple GPIO ports (P0-PB, PE, PF)
- DRAM controller with refresh

**Role:** Controls the tone generator at 0x100000 and the DSPs, handles audio synthesis, and communicates with main CPU via the latch pair, which sits at 0x120000 on *this* bus and 0x140000 on the main CPU's. Receives 192KB payload from main CPU at boot.

### Memory

| IC   | Part Number                                                                          | Type  | Size   | Function                                                                                                                                                                                                                                                                                                                                                   |
|------|--------------------------------------------------------------------------------------|-------|--------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| IC1  | QS6C5008E13                                                                          | ROM   | 8Mbit  | Table Data (ODD)                                                                                                                                                                                                                                                                                                                                           |
| IC3  | QS6C5D0ME11                                                                          | ROM   | 8Mbit  | Table Data (EVEN)                                                                                                                                                                                                                                                                                                                                          |
| IC4  | QV1GFKN5KAX1                                                                         | Flash | 8Mbit  | Program (ODD)                                                                                                                                                                                                                                                                                                                                              |
| IC6  | QV1GFKN5KAX1                                                                         | Flash | 8Mbit  | Program (EVEN)                                                                                                                                                                                                                                                                                                                                             |
| IC9  | M5M44260AJ7S                                                                         | DRAM  | 4Mbit  | Dynamic RAM                                                                                                                                                                                                                                                                                                                                                |
| IC10 | M5M44260AJ7S                                                                         | DRAM  | 4Mbit  | Dynamic RAM                                                                                                                                                                                                                                                                                                                                                |
| IC14 | QS6C303C301I (the kn7000_mame overlay's ROM record reads the part as `QSIGX3C23011`) | ROM   | 32Mbit | Rhythm Data ROM. ⚠ **The read this project holds had address lines A19 and A21 transposed.** Service-manual page 32 shows IC14 wired straight, so the defect is in the dump, not on the board; the correction is applied on disk once and the raw read is kept beside it. See the ROM record in the kn7000_mame overlay's `src/mame/matsushita/kn5000.cpp` |
| IC19 | QV1GFKN5KAX1                                                                         | Flash | 8Mbit  | Custom Data                                                                                                                                                                                                                                                                                                                                                |
| IC21 | -                                                                                    | SRAM  | 1Mbit  | Backup (battery)                                                                                                                                                                                                                                                                                                                                           |

> **Where each chip appears in the address space is set by software.** The TMP94C241 has
> six programmable chip-select blocks, and on top of them service-manual page 32 shows a
> discrete decode network (IC11 `TC74VHC138F` on A16–A18, IC12 `T7W139F` on A19, IC13
> `TC74VHC139F` on A19/A20/A22) that sub-divides each block. The address ranges quoted on
> this page are the post-boot steady state; they are different while the first-stage
> bootloader runs. See
> [TMP94C241 Memory Controller]({{ site.baseurl }}/tmp94c241-memory-controller/).
>
> Note also that IC1/IC3 are listed here as "ROM" from the parts list, but the firmware
> contains erase/program/verify handlers targeting `0x800000` and the update discs include
> "Table DATA FILE" types — so whether they are mask ROM or flash is **unresolved**.

#### ROM Interleaving Formats

The KN5000 uses different data organization depending on the ROM:

| ROM               | Chips                  | Interleaving       | Size  | Address Range                         |
|-------------------|------------------------|--------------------|-------|---------------------------------------|
| Program ROM       | IC6 (even) + IC4 (odd) | 16-bit word-level  | 2MB   | 0xE00000-0xFFFFFF                     |
| Table Data ROM    | IC3 (even) + IC1 (odd) | 16-bit word-level  | 2MB   | 0x800000-0x9FFFFF                     |
| Sub CPU Boot ROM  | IC30 (internal)        | None (single chip) | 128KB | 0xFE0000-0xFFFFFF                     |
| Custom Data Flash | IC19                   | None (single chip) | 1MB   | 0x300000-0x3FFFFF                     |
| HDAE5000 ROM      | IC4 (expansion)        | None (single chip) | 512KB | 0x280000-0x2FFFFF                     |
| Sub CPU Payload   | Transferred via latch  | None (in-memory)   | 192KB | 0x000400-0x0004FF + 0x00F000-0x03EEFF |

**16-bit word-level interleaving** means the two physical ROM chips store alternating 16-bit words:

```
Combined ROM:    [E0 E1] [O0 O1] [E2 E3] [O2 O3] ...   (E = even chip IC3, O = odd chip IC1)
```

To reconstruct the combined ROM from the two chip dumps:
```
combined[4*i + 0] = even[2*i]      (word 2i, low byte)
combined[4*i + 1] = even[2*i + 1]  (word 2i, high byte)
combined[4*i + 2] = odd[2*i]       (word 2i+1, low byte)
combined[4*i + 3] = odd[2*i + 1]   (word 2i+1, high byte)
```

This is **not** the same as byte-level interleaving (`even[0], odd[0], even[1], odd[1]`) — each chip stores complete 16-bit values, and the CPU's 16-bit data bus reads one word at a time from the appropriate chip.

### Audio / Sound Generation

| IC        | Part Number                                                        | Function                 | Interface                                                                                                                                                                                                                                                                                                            |
|-----------|--------------------------------------------------------------------|--------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| IC303     | TC183C230002                                                       | Tone Generator           | Memory-mapped at 0x100000 (SubCPU)                                                                                                                                                                                                                                                                                   |
| IC310     | MN19413                                                            | DSP2 (mixing/EQ)         | Serial GPIO bit-bang (SubCPU)                                                                                                                                                                                                                                                                                        |
| IC311     | uPD6383GF-3BA                                                      | DSP1 (effects)           | Memory-mapped at 0x130000 + parallel port (P7/PZ)                                                                                                                                                                                                                                                                    |
| IC304-307 | see [Waveform ROM Format]({{ site.baseurl }}/waveform-rom-format/) | Waveform ROMs, 4 MB each | Connected to IC303. **IC307 is dumped; IC304-306 are not** — the development driver in the kn7000_mame overlay fills their banks with a `BAD_DUMP`-flagged copy of IC307, so voices selecting them play real-but-wrong PCM through the real paged datapath instead of silence; upstream MAME declares them `NO_DUMP` |

The tone generator IC303 handles polyphonic synthesis with 64 voice channels, while IC311 (DSP1) provides digital effects (reverb, chorus, delay, distortion) and IC310 (DSP2) handles mixing and EQ. The SubCPU controls all three via dedicated interfaces.

See [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) for detailed protocol documentation.

### Peripherals

| IC | Part Number | Function |
|----|-------------|----------|
| IC24 | MN1382QTX | Reset Controller |
| IC206 | MN89304 | LCD Controller |
| IC207 | M5M44265CJ8S | 4Mbit Video RAM |
| IC208 | D72068GF-3B9 | Floppy Disk Controller |

### HDAE5000 Hard Disk Expansion (Optional)

The HD-AE5000 is an optional expansion providing 1.08GB storage.

| Component | Address | Description |
|-----------|---------|-------------|
| PPI (8255) | 0x160000-0x160006 | Programmable Peripheral Interface |
| ROM | 0x280000 | 512KB firmware ROM |

**PPI Port Mapping:**

| Address  | Port    | Function                                      |
|----------|---------|-----------------------------------------------|
| 0x160000 | Port A  | Data byte to/from the PC parallel port        |
| 0x160002 | Port B  | Status input from the PC                      |
| 0x160004 | Port C  | Control signals to the PC (strobe, handshake) |
| 0x160006 | Control | PPI mode configuration (0x82)                 |

**Detection:** PE port bit 0 (active low) indicates HDAE5000 presence and gates only the PPI set-up (`HDAE5000_Parport_Setup`); the extension ROM itself is found by its `XAPR` signature at `0x280000` (`Xapr_DetectAndCallBootInit`), independently of PE.0.

See [HDAE5000 page]({{ site.baseurl }}/hdae5000/) for firmware details.

### LCD Controller (MN89304)

The MN89304 provides a VGA-compatible register interface at I/O base `0x170000`.

**Memory Map:**

| Address               | Description                                   |
|-----------------------|-----------------------------------------------|
| `0x170000` + port     | VGA I/O registers                             |
| `0x1A0000`-`0x1DFFFF` | Video RAM window (256 KB of the 512 KB IC207) |

**VGA I/O Ports:**

| Port | Register | Description |
|------|----------|-------------|
| `0x3C0` | Attribute Controller | Address/Data |
| `0x3C2` | Misc Output | Write only |
| `0x3C4/3C5` | Sequencer | Address/Data |
| `0x3C6` | DAC Mask | Palette mask |
| `0x3C8/3C9` | DAC | Write address/Data |
| `0x3CE/3CF` | Graphics Controller | Address/Data |
| `0x3D4/3D5` | CRTC | Address/Data |
| `0x3DA` | Input Status 1 | Read only |

**CRTC Register Indices:**

| Index | Name | Description |
|-------|------|-------------|
| `0x00` | CRTC_HORIZ_TOTAL | Horizontal Total |
| `0x01` | CRTC_HORIZ_DISP_END | Horizontal Display End |
| `0x06` | CRTC_VERT_TOTAL | Vertical Total |
| `0x07` | CRTC_OVERFLOW | Overflow bits |
| `0x09` | CRTC_MAX_SCAN_LINE | Maximum Scan Line |
| `0x0C/0D` | CRTC_START_ADDR | Display start address |
| `0x10` | CRTC_VERT_RETRACE_START | Vertical Retrace Start |
| `0x11` | CRTC_VERT_RETRACE_END | Vertical Retrace End (bit 7 = protect) |
| `0x12` | CRTC_VERT_DISP_END | Vertical Display End |
| `0x17` | CRTC_MODE_CONTROL | Mode Control |

Registers `0x19` and `0x1A` are MN89304-specific extensions (not standard VGA).

### Logic ICs

| IC         | Part Number | Function                          |
|------------|-------------|-----------------------------------|
| IC11       | TC74VHC138F | 3-to-8 Decoder (A16-A18)          |
| IC12       | T7W139F     | 2-to-4 Decoder                    |
| IC13       | TC74VHC139F | Dual 2-to-4 Decoder (A19/A20/A22) |
| IC16B      | D74HC164GS  | Shift Register                    |
| IC17, IC31 | TC7W32FU    | Dual 2-input OR gates             |

## Button Mapping

### CPL Board (Left Side Panel)

**RHYTHM GROUP:**
- D1: Standard Rock
- D2: R & R Blues
- D3: Pop & Ballad
- D4: Funk & Fusion
- D5: Modern Dance
- D6: Swing
- D7: Jazz Combo

**COMPOSER:**
- D101: Memory
- D102: Menu
- D103: Set
- D104: On/Off
- D105: Music Stylist

**VARIATION & MEM:**
- D17: Demo
- D25-D28: Bank, Menu, Stoprecord, etc.

**FILL IN / INTRO & ENDING:**
- D125-D134: Various fill and ending controls

### CPR Board (Right Side Panel)

**SOUND GROUP:**
- D8: Accordion
- D9: Digital
- D10: Guitar
- D14: Flute
- D15: Sax & Reed
- D21: Piano
- D22: Strings & Vocal

**PART SELECT:**
- D33: Sustain
- D34: Left
- D35: Right 1
- D36: Right 2

**PANEL MEMORY:**
- D49-D56: Memory 1-8
- D57: Next Bank
- D58: Bank View

**SEQUENCER:**
- D160+: Easy Rec, Menu, Sound, Control, Mix, Disk

## Serial Protocol Hardware

The control panel MCUs communicate with the main CPU via a serial interface:

```
Main CPU (TMP94C241F)          Control Panel MCU (M37471M2196S)
        │                               │
        │<──────── SOUT ────────────────│ (Data from panel)
        │                               │
        │─────────> SIN ───────────────>│ (Data to panel)
        │                               │
        │─────────> CLK ───────────────>│ (Clock)
        │                               │
        │─────────> CNTR1 ─────────────>│ (Control)
        │                               │
        │─────────> CMD0-4 ────────────>│ (Commands?)
```

The protocol is reverse-engineered from the main CPU firmware disassembly and implemented as MAME HLE — see [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) for the full command/response reference.

## References

- **Service Manual**: EMID971655 A5 ([Download PDF]({{ site.baseurl }}/service_manual/technics_sx-kn5000.pdf) - 26MB)
- Schematic pages: II-9 through II-38
