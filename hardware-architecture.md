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

| Pin/Signal                   | Function                                                                          |
|------------------------------|-----------------------------------------------------------------------------------|
| `SIN`                        | Serial data input (from main CPU)                                                 |
| `SOUT`                       | Serial data output (to main CPU)                                                  |
| `CLK`                        | Serial clock                                                                      |
| `CNTR1`                      | Control/chip select                                                               |
| `CMD0-CMD4`                  | Command lines                                                                     |
| `SW0-SW7`                    | Switch matrix inputs                                                              |
| `SEG00-SEG10`                | LED segment outputs                                                               |
| `AD0` (pin 11)               | grounded, unused                                                                  |
| `AD1` (pin 12)               | `BEND`, pitch bend wheel VR2 50 kΩ (B) on the HB board (CN3 pin 2), 1 kΩ + 0.1 µF |
| `AD2` (pin 13)               | `MOD`, modulation wheel VR1 10 kΩ on the HB board (CN3 pin 4), 1 kΩ + 0.1 µF      |
| `AD3` (pin 14)               | `MAIN VOLUME`, VR1 20 kΩ (B) on the CPL board, 1 kΩ + 0.1 µF                      |
| `ROTA`, `ROTB` (pins 30, 31) | SW101 TEMPO/PROGRAM encoder, see below                                            |

Read from the CPL sheet (service manual II-35, PDF page 45) and the HB sheet (II-26, PDF page 40), tracker items
kn5000-3c7 and kn5000-xhi (disassembly notes `notes/open4-kn5000-b/cpanel/README.md`).  The same sheet gives
X1 4 MHz; serial SIN pin 5, SOUT pin 4, CLK pin 3, CNTR1 pin 29.  The main connector CN1 carries +36V, +5D,
DATA, SCK, CPRST, VCON; CN2 passes DATA/SCK/CPRST/+5D on to the CPR board.  Which encoder ID each A/D channel
reports as is on [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/#analog-controller--encoder-format).

#### Data-wheel encoder (SW101)

One encoder, SW101 TEMPO/PROGRAM (part QSRGT002AA, "ENCODER SWITCH"), three pins:

| SW101 pin | to                                                                                                  |
|-----------|-----------------------------------------------------------------------------------------------------|
| A         | ground (common)                                                                                     |
| B         | R11 4.7 kΩ pull-up to +5D; R13 47 kΩ series to IC1 pin 30 `ROTA`; C7 0.001 µF from pin 30 to ground |
| C         | R12 4.7 kΩ pull-up to +5D; R14 47 kΩ series to IC1 pin 31 `ROTB`; C8 0.001 µF from pin 31 to ground |

Each phase is an RC low-pass of 47 kΩ x 1 nF = 47 µs time constant, which debounces the switch contacts.  The
MCU counts detents and reports a signed count in frame `[0xD7, count]`; the main CPU never sees the quadrature
(see [Data Wheel]({{ site.baseurl }}/data-wheel-investigation/)).

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
- Analog inputs: AN0 (pin 150) = `EXP`, expression-pedal jack (R71 100 Ω, C79 0.1 µF); AN1 (pin 151) = `AFT`,
  after-touch sensor (MA110 clamp diodes D1/D2, R18 1 kΩ, C80/C16 0.1 µF).  Sheet II-11.  They are read by
  `AnalogIn_PollCpuAdc` (see [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/#main-cpu-ad-expression-pedal-and-after-touch)).

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
- Four 16-bit timers (T4, T6, T8, TA)
- DMA controller (channels 0 and 2 used)
- Multiple GPIO ports (P0-P8, PA-PH, PZ); the Sub CPU uses PD for the inter-CPU handshake and P7, PZ and PH for the DSP1 host port
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
| Sub CPU Boot ROM  | IC30 (mask ROM)        | None (single chip) | 128KB | 0xFE0000-0xFFFFFF                     |
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

| IC        | Part Number                                                        | Function                 | Interface                                                                                                                                                                                                                                                                                                                                                                                                                          |
|-----------|--------------------------------------------------------------------|--------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| IC303     | TC183C230002                                                       | Tone Generator           | Memory-mapped at 0x100000 (SubCPU)                                                                                                                                                                                                                                                                                                                                                                                                 |
| IC310     | MN19413                                                            | DSP2 (mixing/EQ)         | Serial GPIO bit-bang (SubCPU)                                                                                                                                                                                                                                                                                                                                                                                                      |
| IC311     | uPD6383GF-3BA                                                      | DSP1 (effects)           | Parallel host port (SubCPU): data on PZ, strobes and C/D on P7, ready on PH.0. The 4-channel register block at 0x130000 is a separate register file, not its host interface; its chip is unidentified (see [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/#dsp-channel-register-map-memory-mapped-at-0x130000))                                                                                                              |
| IC304-307 | see [Waveform ROM Format]({{ site.baseurl }}/waveform-rom-format/) | Waveform ROMs, 4 MB each | Connected to IC303. **IC307 is dumped; IC304-306 are not.** IC307 is the Y half of a word-interleaved pair (2026-10-30), so the four are two pairs, not one linear space — the development driver in the kn7000_mame overlay fills their banks with a `BAD_DUMP`-flagged copy of IC307, so voices selecting them play real-but-wrong PCM through the real paged datapath instead of silence; upstream MAME declares them `NO_DUMP` |

The tone generator IC303 handles polyphonic synthesis with 64 voice channels, while IC311 (DSP1) provides digital effects (reverb, chorus, delay, distortion) and IC310 (DSP2) handles mixing and EQ. The SubCPU controls all three via dedicated interfaces.

See [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) for detailed protocol documentation.

#### DAC: IC313, Burr-Brown PCM69AU

The main mix is converted by **IC313, a PCM69AU** (18-bit stereo), on Tone Generator Section (B)
(service manual p. II-18).  Not IC310, which is the MN19413 DSP2 that feeds it (tracker item kn5000-xel;
disassembly notes `notes/open4-kn5000-b/hwaudio/README.md`, which also has the full pin table).

| signal       | from                       | to IC313       |
|--------------|----------------------------|----------------|
| serial data  | IC310 `SDO1`, R326 470 ohm | DA-L (pin 17)  |
| word clock   | `LRCK`, IC303 pin 208      | WDCK (pin 16)  |
| system clock | `DACCK`, from section (A)  | SYSCK (pin 15) |
| bit clock    | `BCK`, IC303 pin 207       | BCK (pin 14)   |

DA-R (pin 13) is grounded: both channels share the one data line, selected by LRCK ([INFERENCE] from the
wiring; the PCM69A datasheet was not consulted for the mode a grounded DA-R selects).  The three clocks are
generated by the tone generator IC303 and shared with IC310 and IC311 (which IC303 pin drives `DACCK` was not
followed; [INFERENCE] `MCKOUT`, pin 42); the sample rate is 44.1 kHz
([Effects DSP]({{ site.baseurl }}/effects-dsp/#board-facts-verified-on-the-kn5000-by-felipe)).

The outputs are currents: LOUT (pin 4) and ROUT (pin 7) feed the inverting inputs of the dual op-amp
**IC314 (M5218AFP, ±15 V)**, wired as current-to-voltage converters (6.8 kΩ ∥ 680 pF feedback, a first-order
roll-off at 34.4 kHz) with the DAC's VCOML/VCOMR as reference.  Their outputs, `LOUT` and `ROUT`, go to the FAJ
board on CN9; see [Audio Output Path](#audio-output-path).

IC303's crystal X301 is printed 36.8688 MHz on the schematic; the replacement parts list's part QSXG1I3386A is
33.8688 MHz (768 x 44.1 kHz), see [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/#clock-and-output-rate).

#### Audio Output Path

The main mix leaves the DAC (IC313, above) as two currents, converted to voltages by IC314 on the main board
and sent to the **FAJ board** as `LOUT` / `ROUT` (main CN9, with ±15 V and `MICIN`); tracker item kn5000-jy9.

| stage             | parts (FAJ board unless noted) | notes                                                                  |
|-------------------|--------------------------------|------------------------------------------------------------------------|
| I/V converter     | IC314 M5218AFP (main board)    | 6.8 kΩ parallel 680 pF, roll-off 34.4 kHz                              |
| mixing amp        | IC4A/B M5218AL                 | DAC in at 10 kΩ (gain -3.3), second input at 15 kΩ                     |
| "low pass filter" | IC7A/B                         | labelled so, but drawn as a high-pass: 60.4 Hz, Q 1.44                 |
| equaliser         | IC8, IC10, IC11, IC12          | four fixed gyrator shunts: dips at 245 Hz, 790 Hz and 2.27 kHz         |
| output summers    | IC14A/B                        | to the SWA board as LIN / RIN                                          |
| speaker amp       | SWA board                      | switching amplifier: integrator, comparator, gate drive, MOSFET bridge |
| headphone amp     | IC5, IC6 + Q5-Q8               | to the PHONES jack on the HB board                                     |
| microphone amp    | IC13 + Q9                      | MIC jack -> `MICIN` -> IC310 on the main board                         |

**Speaker equaliser.**  IC7's output reaches a bus through R55 (3.3 kΩ); four gyrator networks (an M5218AL half
wired as a follower, with RC around it) shunt that bus to ground, and IC14 (82 kΩ in, 150 kΩ feedback) buffers it.
Each network can only cut, where its impedance is lowest.  Computed from the printed values (both channels
identical):

| section | network                                    | effect (alone)                                        |
|---------|--------------------------------------------|-------------------------------------------------------|
| IC7     | MFB high-pass, 10k / 150k, 47n / 68n / 68n | high-pass 60.4 Hz, Q 1.44 (manual: "low pass filter") |
| IC8     | second-order gyrator, 6.8k / 4.7k / 150k   | dip at 800 Hz, about -6.7 dB                          |
| IC10    | the same, with 10n / 47n                   | dip at 245 Hz, about -5.9 dB                          |
| IC11    | 15n in series with a 0.33 H gyrator, 1k    | notch at 2.26 kHz, Q 4.1, about -11 dB                |
| IC12    | gyrator 10k / 8.2k / 15n                   | almost flat (0.45 dB)                                 |

From `LOUT` to the speaker amplifier the path gains +8.4 dB at 1 kHz and, relative to that, is -3 dB at 50 Hz,
-4.9 dB at 245 Hz, -4.2 dB at 790 Hz, -8.7 dB at 2.27 kHz and -3.7 dB at 20 kHz.  *[INFERENCE]* The headphone
amplifier (IC5 / IC6) is fed ahead of IC7, so headphones and LINE OUT do not get this EQ; the SWA board's bass
channel sums LIN and RIN, so it gets the 60 Hz high-pass and the 245 Hz dip.  *[INFERENCE]* The dips voice the
cabinet and drivers; no acoustic measurement exists.  Computed by `notes/open6-kn5000-d/misc/probes/faj_eq_response.py`
(technics-roms-disasm) from service manual p. II-25; the full 1/3-octave table is its output
`probes/faj_eq_response.txt`.

**Speakers.**  The SWA board drives three channels: left and right (Q32 SLA5007, 60 µH output filters) and a
bass channel that sums L and R through its own low-pass filter (IC3) into a MOSFET pair (Q33 2SJ425 / Q34
2SK1188).  [INFERENCE, strong] It is a switching (class-D) amplifier: each channel is drawn as integrator ->
comparator -> gate drive -> power drive, with power MOSFETs and 60 µH output inductors.  The specification gives
66 W (18 W x 2 mid/high, 30 W bass) into 12 cm x 2 (4 ohm), 6.5 cm x 2 (8 ohm, through capacitors) and one
14 cm (3 ohm) bass speaker.

**Muting.**  A `MUTE` line from the main board, and the PHONES jack's switch (`HPS`), drive muting transistors
on the FAJ and SWA boards ([INFERENCE] plugging headphones in mutes the speakers).

**Jacks.**  PHONES (HB board), LINE OUT R/R+L and L, AUX IN R/R+L and L, MIC.  AUX IN is summed into both the
speaker and the headphone paths.  [INFERENCE] The LINE OUT and AUX IN nets were followed on the scan, not
continuity-checked.  Levels are not given in the service manual.

Source: service manual pp. II-24 to II-28 (FAJ/ACP/JACK/HB and SWA sheets).

### Peripherals

| IC | Part Number | Function |
|----|-------------|----------|
| IC24 | MN1382QTX | Reset Controller |
| IC206 | MN89304 | LCD Controller |
| IC207 | M5M44265CJ8S | 4Mbit Video RAM |
| IC208 | D72068GF-3B9 | Floppy Disk Controller |

### HDAE5000 Hard Disk Expansion (Optional)

The HD-AE5000 is an optional expansion providing 1.08GB storage.

| Component                                                         | Address           | Description                       |
|-------------------------------------------------------------------|-------------------|-----------------------------------|
| PPI (NEC uPD71055 at IC9 on the expansion board; 8255-compatible) | 0x160000-0x160006 | Programmable Peripheral Interface |
| ROM                                                               | 0x280000          | 512KB firmware ROM                |

**PPI Port Mapping:**

| Address  | Port    | Function                                                             |
|----------|---------|----------------------------------------------------------------------|
| 0x160000 | Port A  | Data byte to/from the PC parallel port (bidirectional)               |
| 0x160002 | Port B  | Handshake lines to the PC (output in PC-link mode)                   |
| 0x160004 | Port C  | Handshake lines from the PC (input in PC-link mode)                  |
| 0x160006 | Control | 0x82 at boot (`HDAE5000_Parport_Setup`); 0x89 / 0x99 in PC-link mode |

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
