---
layout: page
title: Control Panel Protocol
permalink: /control-panel-protocol/
---

# Control Panel Serial Protocol - MAME HLE Implementation Guide

This document provides comprehensive information for implementing High Level Emulation (HLE) of the KN5000 control panel MCUs in MAME.

> ### ⚠ Known limitation of the current implementation (2026-07-22)
>
> This guide describes the protocol and the HLE as designed. The link still occasionally misframes or loses a packet, depending on the exact timing (phase) of a button press. The fault was already present in the February 2026 driver and is still open.
>
> **Do not gate the receiver's byte latch on the clock source.** The link is full-duplex, so the CPU's own transmit edges also shift eight bits in off the idle line, and the CPU-side receiver latches one spurious inbound byte per byte the CPU transmits. A gate that latched only when the external clock was selected (`(SCxMOD & 3) == 0 && IOC`) was added on 2026-07-21, on the theory that these bytes decoded as panel events (a spurious `0x00` being right-panel segment 0, the TRANSPOSE row). It was measured the next day and reverted. The spurious bytes never reach the firmware's receive ring (the segment-0 header count there is exactly 1 in every measured run, with or without the gate), the gate corrected no button mapping, and when it closed *mid-byte* it stranded the receiver's bit counter, so the internal baud generator free-ran and wedged the link for the rest of the session (see the sliding-window note in §"Critical implementation notes"). The serial device latches ungated, as it did before.
>
> Full state and measurements: `kn7000_mame/notes/kn5000-cpserial-INDEX.md`. Where its older sections disagree with the 2026-07-22 adjudication at the top, the adjudication is the measured result.
>
> **Terminology warning:** "phantom byte" is used in *two different senses*. In this document it means the firmware's own deliberate dummy `SC1BUF` writes (PFFC off), which the HLE filters. In the investigation notes and the blog it means the spurious RX-during-TX latches described above. They are unrelated.

## 1. Overview

### Purpose of Control Panel MCUs

The KN5000 control panel uses two dedicated Mitsubishi M37471M2196S microcontrollers to handle:

- **Button scanning** - Matrix scanning of all front panel buttons
- **LED control** - Multiplexed driving of status LEDs
- **Rotary encoders** - Data wheel, pitch bend, and modulation wheels
- **Analog inputs** - the pitch bend and modulation wheels and the MAIN VOLUME slider (CPL board)

### Why HLE is Needed

The control panel MCUs use **mask ROM** (M2196S suffix indicates a specific mask pattern). Without physical decapping and ROM extraction, the firmware is unavailable. However, the main CPU firmware extensively documents the communication protocol, making HLE feasible.

**HLE Strategy:**
1. Intercept serial commands from the main CPU
2. Maintain virtual button/LED/encoder state
3. Generate appropriate response packets
4. Interface with MAME input system for user interaction

## 2. Hardware Architecture

### MCU Identification

| Parameter | Value |
|-----------|-------|
| **Part Number** | Mitsubishi M37471M2196S |
| **Architecture** | 8-bit CMOS (Mitsubishi 740 series) |
| **Features** | Built-in A/D, Serial UART, 16 segment outputs |
| **Quantity** | 2 (CPL = Left panel, CPR = Right panel) |

### Physical Connections

```
Main CPU (TMP94C241F)                Control Panel MCUs
    Port F, SC1                    +---------+  +---------+
        |                          |   CPL   |  |   CPR   |
        |<----- SOUT --------------|   SOUT--|  |--SOUT   |
        |                          |         |  |         |
        |------ SIN -------------->|   SIN---|  |---SIN   |
        |                          |         |  |         |
        |------ SCLK1 ------------>|   CLK---|  |---CLK   |
        |                          |         |  |         |
        |------ CNTR1 ------------>|  CNTR1--|  |--CNTR1  |
        |                          +---------+  +---------+
        |
   PE.5 (INTA) <---- Interrupt from panels
   PF.6 (SCLK1) ---> Serial clock output / clock detect input
```

### Serial Interface Specifications

| Parameter            | Value                                                             | Notes                                                                                                                                                                                                                                                |
|----------------------|-------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Serial Channel**   | SC1 (Serial Channel 1)                                            | TMP94C241F SIO channel 1, I/O interface mode                                                                                                                                                                                                         |
| **Clock Source**     | Internal, derived from fc=16MHz                                   |                                                                                                                                                                                                                                                      |
| **TX Baud Rate**     | 250 kHz                                                           | fc/16/4 (BR1CR=0x14) during data TX                                                                                                                                                                                                                  |
| **Arming Baud Rate** | 31.25 kHz                                                         | fc/64/8 (BR1CR=0x28), written for the first (phantom) byte of every command by `CPanel_SendCommand`, by `CPanel_SM_TXComplete` when it chains the next queued command, and by `CPanel_InterruptPoll_MainLoop` when it starts sending queued LED data |
| **Data Format**      | 8-bit, LSB first, synchronous (I/O interface mode, SC1MOD = 0x00) | SC1MOD, SC1CR config                                                                                                                                                                                                                                 |
| **Flow Control**     | Software (CNTR1 pin for chip select)                              |                                                                                                                                                                                                                                                      |

### Clock Configuration (from BR1CR register)

| BR1CR Value | Prescaler  | Divider | Baud Rate | Usage                                                                                                                                       |
|-------------|------------|---------|-----------|---------------------------------------------------------------------------------------------------------------------------------------------|
| `0x14`      | T2 (fc/16) | /4      | 250 kHz   | The two real command bytes (`CPanel_SM_SendByte1`, `CPanel_SM_SendByteN`)                                                                   |
| `0x24`      | T8 (fc/64) | /4      | 62.5 kHz  | Phantom/turnaround bytes (`CPanel_SM_StartTX`, `CPanel_SM_TXDelay1`, `CPanel_SM_TXDelay2`); also the value left set when the link goes idle |
| `0x28`      | T8 (fc/64) | /8      | 31.25 kHz | Arming each command (`CPanel_SendCommand`, `CPanel_SM_TXComplete`, `CPanel_InterruptPoll_MainLoop`)                                         |

## 3. Protocol Specification

### Command Format

All commands are **2-byte sequences** sent from main CPU to control panel MCUs:

```
Byte 0: Command/Address byte
Byte 1: Data/Parameter byte
```

The command byte encodes both target panel and command type:

```
Command byte: [ Panel[7:5] | Type[4:0] ]
```

**Panel selection (bits 7-5):**

| Bits 7-5 | Binary | Target |
|----------|--------|--------|
| 001 | `0x20-0x3F` | Left panel (CPL) |
| 111 | `0xC0-0xFF` | Right panel (CPR) |

**Command type (bits 4-0):**

| Type | Bits 4-0 | Left | Right | Purpose |
|------|----------|------|-------|---------|
| 0 | `00000` | 0x20 | 0xE0 | Basic query (ping, poll segment, status) |
| 2 | `00010` | — | 0xE2 | Analog register query (encoder/ADC values) |
| 3 | `00011` | — | 0xE3 | Extended read (button state + status) |
| 5 | `00101` | 0x25 | — | Data mode (bulk button state request) |

### Complete Command Reference

#### Initialization Commands

| Command | Bytes | Purpose | Timing |
|---------|-------|---------|--------|
| `1F DA` | Init sequence 1 | Reset/sync left panel | 3000 loops wait |
| `1F 1A` | Init sequence 2 | Configure left panel | 3000 loops wait |
| `1D 00` | Init sequence 3 | Initialize left panel | 6000 loops wait |
| `DD 03` | Setup mode | Configure both panels | 6000 loops wait |
| `1E 80` | Init sequence 4 | Final init (left) | 9000 loops wait |

#### Query Commands

| Command | Bytes | Purpose | Expected Response |
|---------|-------|---------|-------------------|
| `20 00` | Ping left panel | Communication test (type 0) | Sync packet |
| `20 0B` | Poll left buttons | Read button segment 0x0B (type 0) | Button state packet |
| `20 10` | Query left panel | Read status/sync (type 0) | Button state packet |
| `25 01` | Left data mode | Bulk button state request (type 5) | Button state packets |
| `E0 00` | Ping right panel | Communication test (type 0) | Sync packet |
| `E0 13` | Poll right panel | Steady-state segment 3 poll (type 0) | Button state packet |
| `E2 04` | Query analog registers | Read analog controller values (type 2) | Type 2 encoder packet |
| `E2 11` | Query analog registers | Read analog controller values (type 2) | Type 2 encoder packet |
| `E3 10` | Extended right read | Button state + status (type 3) | Button state packet |

#### Data Commands

| Command | Bytes | Purpose |
|---------|-------|---------|
| `2B 00` | Init state array (left) | Initialize button state (22-byte multi-segment response) |
| `EB 00` | Init state array (right) | Initialize button state (22-byte multi-segment response) |

#### Steady-State Polling (via LED TX Buffer)

The `CPanel_InterruptPoll_MainLoop` queues one poll command every 42 main-loop iterations through the LED TX buffer (not via `CPanel_SendCommand`):

| Command | Bytes | Purpose | Expected Response |
|---------|-------|---------|-------------------|
| `E0 13` | Poll right panel | Query right panel segment 3 | Button state packet |

#### LED Control Commands (via LED TX Buffer)

LED commands are 2-byte pairs (row select + pattern) queued in `CPANEL_LED_TX_BUFFER` and transmitted by the TX state machine. The MCU processes these silently — **no response is generated**.

| Row | Panel | LEDs Controlled |
|-----|-------|-----------------|
| `0x00` | CPR | SUSTAIN, DIGITAL EFFECT, DSP EFFECT, DIGITAL REVERB, ACOUSTIC ILLUSION, SEQ:PLAY/REC/MENU |
| `0x01` | CPR | PIANO, GUITAR, STRINGS&VOCAL, BRASS, FLUTE, SAX&REED, MALLET, WORLD PERC |
| `0x02` | CPR | ORGAN, ORCHESTRAL PAD, SYNTH, BASS, DIGITAL DRAWBAR, ACCORDION REG, GM SPECIAL, DRUM KITS |
| `0x03` | CPR | PM 1-8 |
| `0x04` | CPR | PART: LEFT/RIGHT2/RIGHT1, ENTERTAINER, CONDUCTOR, TECHNI CHORD |
| `0x08` | CPR | MENU: SOUND/CONTROL/MIDI/DISK |
| `0x0A` | CPR | MEMORY A, MEMORY B |
| `0x0B` | CPR | SYNCHRO&BREAK, R1/R2 OCTAVE -/+, BANK VIEW |
| `0x0C` | CPR | START/STOP BEAT 1-4 |
| `0xC0` | CPL | COMPOSER, SOUND ARR, MUSIC STYLIST, FADE IN/OUT, DISPLAY HOLD |
| `0xC1` | CPL | Rhythm styles (U.S. TRAD through CUSTOM) |
| `0xC2` | CPL | Rhythm styles 2 (STANDARD ROCK through JAZZ COMBO), MSP:MENU |
| `0xC3` | CPL | VARIATION 1-4, MUSIC STYLE ARRANGER, AUTO PLAY CHORD |
| `0xC4` | CPL | FILL IN 1-2, INTRO&ENDING 1-2, SPLIT POINT (L/C/R), TEMPO/PROGRAM |
| `0xC8` | CPL | OTHER PARTS/TR |

##### Power-on LED sequence

The main CPU has no lamp test and no all-LEDs-off command.  `CPanel_LED_FlushImage` sends a row (`Set_LEDs`:
2-byte frame `{Protocol_values_for_LED_rows[r], pattern}` through `LED_WriteToPanel` and
`CPanel_LedQueue_PushByte`) only when `CPANEL_LED_IMAGE[r]` differs from `CPANEL_LED_IMAGE_SENT[r]`.
`Boot_InitWorkRAM` zeroes both images (0x400-0xE35C).  So after power-on, only rows with at least one lit LED are
ever sent.  What the panel MCUs show before the first frame is decided by their undumped mask ROMs.

Measured in MAME (tracker item kn5000-bq4; disassembly `notes/open4-kn5000-b/cpanel/probes/led_boot_tap.lua`, a
write tap on `CPANEL_LED_IMAGE_SENT`; logs `probes/led_boot_tap.cold.log` and `.second.log`, identical;
kn7000_mame build of 2026-10-31, romset `technics_romsets/kn5000`, cold start, which opens "ALL INITIAL
SETTING"):

| emulated time | row (protocol byte) | pattern | LEDs lit                                 |
|---------------|---------------------|---------|------------------------------------------|
| 7.754 s       | 2 (`0xC2`)          | `0x01`  | STANDARD ROCK                            |
| 7.754 s       | 3 (`0xC3`)          | `0x01`  | VARIATION 1                              |
| 7.754 s       | 6 (`0x00`)          | `0x08`  | DIGITAL REVERB                           |
| 7.754 s       | 7 (`0x01`)          | `0x01`  | PIANO                                    |
| 7.754 s       | 10 (`0x04`)         | `0x44`  | PART SELECT: RIGHT 1, CONDUCTOR: RIGHT 1 |
| 7.920 s       | 6 (`0x00`)          | `0x09`  | + SUSTAIN                                |
| 12.868 s      | 5 (`0xC8`)          | `0x01`  | OTHER PARTS/TR                           |

Before 7.75 s the panels receive only the init commands (`1F DA`, `1F 1A`, `1D 00`, `DD 03`, `1E 80`) and polls.
The times are MAME's, with the sub-CPU boot ROM a `BAD_DUMP`, and are not real-hardware measurements.  The LED
states are the firmware's factory defaults.  `CPanel_SendFramePolled` (0xFC4021, formerly misnamed
CPanel_InitLEDBuffer) sends one 2-byte frame on SC1 without the interrupt state machine; nothing calls it in v10
or v7 (its address occurs nowhere in the ROM images, `probes/ref_scan.py`).

### Response Packet Format

Responses from control panel MCUs are processed by `CPanel_RX_ParseNext` at address `0xFC492B`.

#### Packet Type Encoding

The packet type is encoded in bits 5-3 of the first response byte:

```
Byte 0: [ X | X | Type2 | Type1 | Type0 | X | X | X ]
                 \___________|__________/
                    Packet type (0-7)
```

#### Packet Type Handlers

| Type | Bits 5-3 | Handler                     | Address  | Purpose                                                                                            |
|------|----------|-----------------------------|----------|----------------------------------------------------------------------------------------------------|
| 0    | `000`    | `CPanel_RX_ButtonPacket`    | 0xFC4985 | Button state (left panel)                                                                          |
| 1    | `001`    | `CPanel_RX_ButtonPacket`    | 0xFC4985 | Button state (right panel)                                                                         |
| 2    | `010`    | `CPanel_RX_EncoderPacket`   | 0xFC49E0 | Analog value / data-wheel count (dispatched by encoder ID)                                         |
| 3    | `011`    | `CPanel_RX_SyncPacket`      | 0xFC4B10 | Sync/ACK                                                                                           |
| 4    | `100`    | `CPanel_RX_SyncPacket`      | 0xFC4B10 | Sync/ACK                                                                                           |
| 5    | `101`    | `CPanel_RX_SyncPacket`      | 0xFC4B10 | Sync/ACK                                                                                           |
| 6    | `110`    | `CPanel_RX_MultiBytePacket` | 0xFC4A40 | Run of 1-16 segment or controller states ([format](#multi-byte-packet-purpose-types-6-7-resolved)) |
| 7    | `111`    | `CPanel_RX_MultiBytePacket` | 0xFC4A40 | Run of 9-16 states (as type 6)                                                                     |

### Button State Packet Format (Types 0, 1)

```
Byte 0: [ Panel[7:6] | Type[5:3] | Segment[3:0] ]
Byte 1: [ Button bitmap - 8 buttons per segment ]
```

**Panel encoding (bits 7:6):**

| Bits 7:6 | Value | Panel |
|----------|-------|-------|
| `00` | 0x00 | Right panel (CPR) |
| `11` | 0xC0 | Left panel (CPL) |

**Important:** Bits 7:6=`01` (0x40) and bits 7:6=`10` (0x80) fall in a dead zone of the firmware's ROM lookup table at `0xEDA03C`. Using 0x40 for left panel headers maps every left panel event to index 0x1F, whose action list is empty, so no left-panel button press reaches an action. This was a long-standing bug in early HLE implementations.

**Firmware processing at `CPanel_RX_ButtonPacket` (0xFC4985):**
1. Extracts panel/segment: `W = byte0 & 0x4F`
2. Tests bit 6: if clear → right panel indices 0-10, if set → left panel (`SUB W, 0x30` → indices 16-26)
3. XORs new state with previous to detect changes
4. Stores result in `CPANEL_LAST_EVENT_VALUE` for edge detection

**Event dispatch via ROM lookup table at 0xEDA03C:**

The firmware translates header bytes to event indices using: `index = (header & 0xC0) >> 1 | (header & 0x1F)`

```
Table contents (128 entries):
[0x00-0x0A]: 0B 0C 0D 0E 0F 10 11 12 13 14 15   → right panel event indices 11-21
[0x0B-0x5F]: all 1F                                → dead zone (index 31)
[0x60-0x6A]: 00 01 02 03 04 05 06 07 08 09 0A     → left panel event indices 0-10
[0x6B-0x7F]: mostly 1F, with 0x16-0x19 at specific offsets (encoders/multi-byte)
```

In normal operation every record is queued at RAM `0x8E94` and runs the action list of its index (see [From a button change to an action](#from-a-button-change-to-an-action-2026-10-06)). The dead-zone index 0x1F has an empty list (`PanelActions_Event31`), so its records do nothing; this is why header encoding must use exactly `00` (right) and `11` (left) in bits 7:6. Only while title 251 (`TITLE_EXT`) is current does `PanelInput_QueueChange` split at 0x15: segment indexes go straight to `EffectMode_MidiSetLEDs`, and higher ones (except 0x19) are queued.

### Encoder Packet Format (Type 2)

```
Byte 0: [ ID_hi[1:0] | 0 | 1 | 0 | ID_lo[2:0] ]
         bits 7-6     5   4   3   bits 2-0

Byte 1: [ Value: absolute 8-bit ADC reading for the analog IDs; signed detent count for ID 31, the data wheel ]
```

**Encoder ID Encoding:**
- Bits 0-2 of byte 0 → bits 0-2 of encoder ID
- Bits 6-7 of byte 0 → bits 3-4 of encoder ID
- This gives a 5-bit encoder ID (0-31)

The encoder dispatch routine `CPanel_EncoderDispatch` (0xFC6C5F):
1. Extracts encoder ID: `ID = (byte0 & 0x07) | ((byte0 >> 3) & 0x18)`
2. Multiplies by 4 for jump table offset
3. Indexes into jump table at `ENCODER_HANDLER_TABLE` (0xEDA0BC)
4. Dispatches to encoder-specific handler
5. Returns 0xFFFF if invalid/no change

**Known Encoder IDs:**

| ID     | Handler                          | Control                  | Source                       |
|--------|----------------------------------|--------------------------|------------------------------|
| 2      | `Encoder_ProcessExpressionPedal` | expression pedal         | main CPU AN0 (not a frame)   |
| 5      | `Encoder_ProcessAfterTouch`      | after-touch sensor       | main CPU AN1 (not a frame)   |
| 25     | `Encoder_ProcessPitchBend`       | pitch bend wheel         | CPL frame `0xD1` (AD1, BEND) |
| 26     | `Encoder_ProcessModulation`      | modulation wheel         | CPL frame `0xD2` (AD2, MOD)  |
| 27     | `Encoder_ProcessMainVolume`      | MAIN VOLUME slider       | CPL frame `0xD3` (AD3, VR1)  |
| 31     | `Encoder_PassthroughIdentity`    | TEMPO/PROGRAM data wheel | CPL frame `0xD7`             |
| others | `Encoder_ReturnDefaultConstant`  | none (returns 1)         |                              |

IDs 2 and 5 are never sent by a panel.  The main CPU's own A/D poller (`AnalogIn_PollCpuAdc`) calls the table
with them.  The controls were identified from the schematics (CPL board sheet II-35, CPU SECTION (A) sheet
II-11) and from the panel records each handler's event posts (tracker item kn5000-3c7, disassembly notes
`notes/open4-kn5000-b/cpanel/README.md`).  [INFERENCE] The ID = 24 + AD channel mapping of the CPL frames
(AD1 -> 25, AD2 -> 26, AD3 -> 27) rests on the three handlers agreeing with the three wired inputs; the panel
MCU's mask ROM is not dumped, so the firmware cannot show it directly.

**Encoder Processing:**
- Raw input values are inverted (`CPL A`) and stored in `ENCODER_RAW_*` variables
- Values are divided by 2 (`SRL 1, A`) and used as lookup table indices
- Lookup tables at `ENCODER_LUT_*` convert raw values to 0-127 (they are not MIDI controller numbers)
- Change detection compares with previous value before storing

### Timing Requirements

| Operation           | Delay                     | Method                        |
|---------------------|---------------------------|-------------------------------|
| Post-command wait   | 6 system ticks            | `DELAY_6_TICKS` (0xFC4139)    |
| Init command wait   | 3000 loop iterations      | `DELAY_3000_LOOPS` (0xFC4118) |
| Ready check timeout | 200 attempts * 1500 loops | `CPanel_WaitTXReady`          |

### INTA Response Mechanism

The control panel MCUs use a bidirectional serial protocol. The CPU is master for **transmitting** commands (drives SCLK), but the panels are masters for **responding** — they drive their own SCLK via the INTA (interrupt acknowledge) mechanism:

```
  CPU (firmware)                    Control Panel MCU
  ──────────────                    ──────────────────
  TX state machine sends command
  (4 phantom + 2 real SC1BUF writes)
  SCLK stops
                                    Receives 2-byte command
                                    Queues response (2 bytes)
                                    Detects SCLK idle (50 µs)
                                    Asserts INTA on PE.5
  ┌──────────────────────────────────────────────────┐
  │ INTA_HANDLER:                                    │
  │   IOC = 1 (slave mode — CPU receives only)       │
  │   RXE = 1 (receive enable)                       │
  │   State → SM_RXByte1                             │
  └──────────────────────────────────────────────────┘
                                    Self-clocks response at 250 kHz
                                    ── SCLK edges ──>
  SM_RXByte1: reads SC1BUF (header byte)
  SM_RXByteN: reads SC1BUF (data byte)
  Response complete → IDLE
                                    Deasserts INTA
```

**INTA timing requirements:**
- Idle detection timeout: **50 µs** sliding window (retriggered on every SCLK edge)
- Self-clock startup delay: **20 µs** after INTA assertion (lets CPU enable slave mode)
- Self-clock rate: **250 kHz** (matches firmware's baud rate)
- Inter-packet pause: **20 µs** between 2-byte packets (firmware processes one packet per INTA cycle)

This mechanism is essential for:
- **Button change notifications**: Panel MCUs proactively push button state changes without being polled
- **Multi-segment responses**: Init commands (0x2B, 0xEB) send 22 bytes (11 segments × 2 bytes each) via successive INTA cycles

The firmware's steady-state polling only queries **one segment** (`E0 13` = right panel segment 3, approximately every 42 main loop iterations). All other button changes on all 22 segments (11 per panel) are delivered via INTA.

### Proactive Button Change Detection

The real panel MCUs continuously scan their button matrices and push change notifications to the CPU via INTA, independent of any command from the CPU. The HLE replicates this with a periodic **7 ms scan timer** (~143 Hz).

**Per-segment confirmation** filters single-scan glitches ("ghost toggles"):

```
Scan N:   port reads 0x04 (differs from confirmed 0x00) → record as PENDING
Scan N+1: port reads 0x04 (matches pending)              → CONFIRMED, report via INTA
                  OR
Scan N+1: port reads 0x00 (reverts to confirmed)          → clear pending, no report
```

A state change must be stable for **2 consecutive scans (14 ms)** before being reported. This filters MAME input port glitches where ports momentarily return single-bit non-zero values that revert within one scan interval. On real hardware, physical button presses last 50-100 ms minimum, so 14 ms confirmation is well within tolerance.

**Ghost toggle pattern** (filtered by per-segment confirmation):
1. Port reads 0xNN (single bit set) → would report button press
2. Next scan: port reads 0x00 → would report button release
3. Net effect: phantom press-release pair with no real user input

Without filtering, these produce 2 INTA sessions per ghost toggle, flooding the firmware's event queue with phantom events.

### From a button change to an action (2026-10-06)

A segment change becomes a 3-byte record `{event index, new state, changed bits}` in a queue at RAM `0x8E94`
(count at `0x8EC4`). The event index is the one above: 0-10 = left-panel segments 0-10,
11-21 = right-panel segments 0-10, 22-24 = left-panel headers `0xD1`, `0xD2`, `0xD3`: the pitch bend wheel, the modulation wheel and the MAIN VOLUME slider (encoder IDs 25-27), 25 = header `0xD7`, the TEMPO/PROGRAM data wheel (records
`{0x19, ±delta, 0xFF}`: MAME's panel device has sent the `[0xD7, count]` frame that produces these records since
[mamedev/mame#15919](https://github.com/mamedev/mame/pull/15919)), 26 = the
expression pedal and 27 = the after-touch sensor (main CPU AN0 / AN1, `ADC_AN0_OUTPUT` / `ADC_AN1_OUTPUT`, queued by
`PanelInput_QueueCpuAdcChanges`; see [Analog controllers](#analog-controller--encoder-format)),
28 = foot switches FS1/FS2 (PG.2-3), 29 = foot controllers FC1-FC4 (PG.4-7), 30 = PD.6 (the pedal records of
`PanelInput_ScanPedalPorts`; see [CPU Subsystem]({{ site.baseurl }}/cpu-subsystem/)). For each record, `PanelButton_DispatchChange` walks one **action list**, chosen by the event
index from `PanelButton_ActionLists` (ROM `0xED9C1E`), or from `PanelButton_HelpModeActionLists`
(`0xED9C9E`) in mode 20, `MD_HELP`. An action is 8 bytes:

| offset | field | use |
|---:|:---|:---|
| +0 | event_id | 0xFF ends the list |
| +1 | event_arg | |
| +2 | shift | bits 3-0 = count, bit 4 = shift left (else right) |
| +3 | mask | the button bits of the segment byte |
| +4 | handler | u32 code address |

For each action, `state & mask` and `changed & mask` are shifted by the count. When the masked changed bits
are not 0, the handler is called with the frame `{event_id, event_arg, state, changed}` and the raw `{0xAA,
index, state byte, changed byte}` after it. The pedal scan, `PanelInput_UpdatePedalRecord`, writes `new ^ old`
as the third byte, and `PanelButton_PairDown` tests the state byte for press or release, which confirms this
layout. Most handlers filter on the mode or a panel parameter, then post one or both 4-byte
events with `PanelEvent_Post` (a 16-deep queue at `(0xC039)`). The event ids `0x48`, `0x60`, `0x70`,
`0x90` and `0x98` are panel-record tags (see [Panel Memory Factory Data]({{ site.baseurl }}/panel-memory-factory-data/)).
An id of `0x00`, used by the sound-group buttons, is replaced by the byte at RAM `0x8D3A` before posting
(`PanelEvent_FillSelectedPart`). `0xA8` / `0xA9` are not tags.

For most actions `event_id` is a panel-record tag and `event_arg` a payload byte of it, and the shift
moves the button bit onto the record bit:

- VARIATION 1-4 → tag `0x48` byte 7, the variation slot of the style record (see
  [Music Stylist Database]({{ site.baseurl }}/music-stylist-database/));
- DIGITAL REVERB (`0x08` << 4) and ACOUSTIC ILLUSION (`0x10` << 2) → tag `0x60` byte 1, bits 7 and 6, the
  effect-slot ON/OFF bits;
- CONDUCTOR → tag `0x90` bytes 0-1, R1/R2 OCTAVE → tag `0x90` byte 4.

Not every action fits. PART SELECT's `event_arg` is `0x10`, beyond tag `0x90`'s 6-byte payload.

**The masks fall exactly on the buttons the MAME driver names per segment and bit**
(`kn5000.cpp`, `PORT_START("CPL_SEGn")` / `("CPR_SEGn")`). For example, VARIATION 1-4 is one action with
mask `0x0F`, the eight sound-group buttons one action with `0xFF`, and every UP / DOWN / LEFT / RIGHT
button one action of its own. That agreement is the evidence for this reading, and it is what names the
handlers.

The table below is the ordinary table, `PanelButton_ActionLists`. In `MD_HELP`, every button but
the LCD buttons and HELP goes to `PanelButton_HelpMode`. Produced by
`python3 scripts/converters/panel_button_actions_retype.py --report` (kn5000-roms-disasm); the lists are
typed in `ui_widgets/naka_extension_device.c` (`panel_button_action_t`, `PanelActions_*`).

| index | segment | buttons (mask)                                                                                                           | event id, arg  | handler                               |
|------:|:--------|:-------------------------------------------------------------------------------------------------------------------------|:---------------|:--------------------------------------|
| 0     | CPL 0   | STANDARD ROCK, R & ROLL & BLUES, POP & BALLAD, FUNK & FUSION, SOUL & MODERN DANCE, BIG BAND & SWING, JAZZ COMBO (`0x7F`) | `0x48`, `0x00` | `PanelButton_RhythmGroup`             |
| 1     | CPL 1   | MEMORY (`0x01`)                                                                                                          | `0x48`, `0x00` | `PanelButton_RhythmGroup`             |
| 1     | CPL 1   | MENU (`0x02`)                                                                                                            | `0xA9`, `0x20` | `PanelButton_ModeKey`                 |
| 1     | CPL 1   | SET (`0x04`)                                                                                                             | `0xA9`, `0x20` | `PanelButton_ModeKey`                 |
| 1     | CPL 1   | ON/OFF (`0x08`)                                                                                                          | `0xA8`, `0x06` | `PanelAction_PostUnlessDemoOrParamC0` |
| 1     | CPL 1   | MUSIC STYLIST (`0x10`)                                                                                                   | `0xA8`, `0x02` | `PanelAction_PostUnlessDemoOrParamC0` |
| 1     | CPL 1   | FADE IN (`0x20`)                                                                                                         | `0x98`, `0x0B` | `PanelAction_PostUnlessDemo`          |
| 1     | CPL 1   | FADE OUT (`0x40`)                                                                                                        | `0x98`, `0x0B` | `PanelAction_PostUnlessDemo`          |
| 2     | CPL 2   | FILL IN 1 (`0x01`)                                                                                                       | `0x48`, `0x05` | `PanelAction_PostUnlessDemo`          |
| 2     | CPL 2   | FILL IN 2 (`0x02`)                                                                                                       | `0x48`, `0x05` | `PanelAction_PostUnlessDemo`          |
| 2     | CPL 2   | INTRO & ENDING 1 (`0x04`)                                                                                                | `0x48`, `0x05` | `PanelAction_PostUnlessDemo`          |
| 2     | CPL 2   | INTRO & ENDING 2 (`0x08`)                                                                                                | `0x48`, `0x06` | `PanelAction_PostUnlessDemo`          |
| 2     | CPL 2   | PAGE DOWN (`0x40`)                                                                                                       | `0xA9`, `0x10` | `PanelButton_PairDown`                |
| 2     | CPL 2   | PAGE UP (`0x80`)                                                                                                         | `0xA9`, `0x10` | `PanelButton_PairUp`                  |
| 3     | CPL 3   | DEMO (`0x01`)                                                                                                            | `0xA9`, `0x20` | `PanelButton_ModeKey`                 |
| 3     | CPL 3   | MSP BANK (`0x02`)                                                                                                        | `0xA8`, `0x09` | `PanelAction_PostUnlessDemoOrParamC0` |
| 3     | CPL 3   | MSP MENU (`0x04`)                                                                                                        | `0xA9`, `0x20` | `PanelButton_ModeKey`                 |
| 3     | CPL 3   | MSP STOP/RECORD (`0x08`)                                                                                                 | `0xA8`, `0x09` | `PanelAction_PostUnlessDemoOrParamC0` |
| 4     | CPL 4   | VARIATION 1, VARIATION 2, VARIATION 3, VARIATION 4 (`0x0F`)                                                              | `0x48`, `0x07` | `PanelButton_Variation`               |
| 4     | CPL 4   | MUSIC STYLE ARRANGER (`0x10`)                                                                                            | `0x98`, `0x03` | `PanelButton_MusicStyleArranger`      |
| 4     | CPL 4   | SPLIT POINT (`0x20`)                                                                                                     | `0x70`, `0x00` | `PanelButton_SplitPoint`              |
| 4     | CPL 4   | AUTO PLAY CHORD (`0x40`)                                                                                                 | `0xA8`, `0x05` | `PanelButton_AutoPlayChord`           |
| 5     | CPL 5   | MSP 1, MSP 2, MSP 3, MSP 4, MSP 5, MSP 6 (`0x3F`)                                                                        | `0xA8`, `0x09` | `PanelButton_MspNumber`               |
| 6     | CPL 6   | U.S. TRAD, COUNTRY, LATIN, MARCH & WALTZ, PARTY TIME, SHOWTIME & TRAD DANCE, WORLD, CUSTOM (`0xFF`)                      | `0x48`, `0x00` | `PanelButton_RhythmGroup`             |
| 7     | CPL 7   | RIGHT 5 (`0x01`)                                                                                                         | `0xA9`, `0x0C` | `PanelButton_PairUp`                  |
| 7     | CPL 7   | RIGHT 4 (`0x02`)                                                                                                         | `0xA9`, `0x0B` | `PanelButton_PairUp`                  |
| 7     | CPL 7   | DISPLAY HOLD (`0x04`)                                                                                                    | `0xA8`, `0x03` | `PanelAction_PostUnlessDemo`          |
| 7     | CPL 7   | EXIT (`0x08`)                                                                                                            | `0xA9`, `0x0F` | `PanelButton_PairUp`                  |
| 7     | CPL 7   | DOWN 7 (`0x10`)                                                                                                          | `0xA9`, `0x06` | `PanelButton_PairDown`                |
| 7     | CPL 7   | UP 7 (`0x20`)                                                                                                            | `0xA9`, `0x06` | `PanelButton_PairUp`                  |
| 7     | CPL 7   | DOWN 8 (`0x40`)                                                                                                          | `0xA9`, `0x07` | `PanelButton_PairDown`                |
| 7     | CPL 7   | UP 8 (`0x80`)                                                                                                            | `0xA9`, `0x07` | `PanelButton_PairUp`                  |
| 8     | CPL 8   | RIGHT 3 (`0x01`)                                                                                                         | `0xA9`, `0x0A` | `PanelButton_PairUp`                  |
| 8     | CPL 8   | RIGHT 2 (`0x02`)                                                                                                         | `0xA9`, `0x09` | `PanelButton_PairUp`                  |
| 8     | CPL 8   | RIGHT 1 (`0x04`)                                                                                                         | `0xA9`, `0x08` | `PanelButton_PairUp`                  |
| 8     | CPL 8   | DOWN 5 (`0x10`)                                                                                                          | `0xA9`, `0x04` | `PanelButton_PairDown`                |
| 8     | CPL 8   | UP 5 (`0x20`)                                                                                                            | `0xA9`, `0x04` | `PanelButton_PairUp`                  |
| 8     | CPL 8   | DOWN 6 (`0x40`)                                                                                                          | `0xA9`, `0x05` | `PanelButton_PairDown`                |
| 8     | CPL 8   | UP 6 (`0x80`)                                                                                                            | `0xA9`, `0x05` | `PanelButton_PairUp`                  |
| 9     | CPL 9   | LEFT 5 (`0x01`)                                                                                                          | `0xA9`, `0x0C` | `PanelButton_PairDown`                |
| 9     | CPL 9   | LEFT 4 (`0x02`)                                                                                                          | `0xA9`, `0x0B` | `PanelButton_PairDown`                |
| 9     | CPL 9   | LEFT 3 (`0x04`)                                                                                                          | `0xA9`, `0x0A` | `PanelButton_PairDown`                |
| 9     | CPL 9   | DOWN 3 (`0x10`)                                                                                                          | `0xA9`, `0x02` | `PanelButton_PairDown`                |
| 9     | CPL 9   | UP 3 (`0x20`)                                                                                                            | `0xA9`, `0x02` | `PanelButton_PairUp`                  |
| 9     | CPL 9   | DOWN 4 (`0x40`)                                                                                                          | `0xA9`, `0x03` | `PanelButton_PairDown`                |
| 9     | CPL 9   | UP 4 (`0x80`)                                                                                                            | `0xA9`, `0x03` | `PanelButton_PairUp`                  |
| 10    | CPL 10  | LEFT 2 (`0x01`)                                                                                                          | `0xA9`, `0x09` | `PanelButton_PairDown`                |
| 10    | CPL 10  | LEFT 1 (`0x02`)                                                                                                          | `0xA9`, `0x08` | `PanelButton_PairDown`                |
| 10    | CPL 10  | HELP (`0x04`)                                                                                                            | `0xA9`, `0x20` | `PanelButton_ModeKey`                 |
| 10    | CPL 10  | OTHER PARTS/TR (`0x08`)                                                                                                  | `0xA9`, `0x0F` | `PanelButton_PairDown`                |
| 10    | CPL 10  | DOWN 1 (`0x10`)                                                                                                          | `0xA9`, `0x00` | `PanelButton_PairDown`                |
| 10    | CPL 10  | UP 1 (`0x20`)                                                                                                            | `0xA9`, `0x00` | `PanelButton_PairUp`                  |
| 10    | CPL 10  | DOWN 2 (`0x40`)                                                                                                          | `0xA9`, `0x01` | `PanelButton_PairDown`                |
| 10    | CPL 10  | UP 2 (`0x80`)                                                                                                            | `0xA9`, `0x01` | `PanelButton_PairUp`                  |
| 11    | CPR 0   | TRANSPOSE - (`0x20`)                                                                                                     | `0xA9`, `0x0E` | `PanelButton_PairDown`                |
| 11    | CPR 0   | TRANSPOSE + (`0x40`)                                                                                                     | `0xA9`, `0x0E` | `PanelButton_PairUp`                  |
| 12    | CPR 1   | ORGAN & ACCORDION, ORCHESTRAL PAD, SYNTH, BASS, DIGITAL DRAWBAR, ACCORDION REGISTER, GM SPECIAL, DRUM KITS (`0xFF`)      | `0x00`, `0x00` | `PanelButton_SoundGroup`              |
| 13    | CPR 2   | PIANO, GUITAR, STRINGS & VOCAL, BRASS, FLUTE, SAX & REED, MALLET & ORCH PERC, WORLD PERC (`0xFF`)                        | `0x00`, `0x00` | `PanelButton_SoundGroup`              |
| 14    | CPR 3   | SUSTAIN (`0x01`)                                                                                                         | `0x00`, `0x04` | `PanelButton_Sustain`                 |
| 14    | CPR 3   | DIGITAL EFFECT (`0x02`)                                                                                                  | `0x00`, `0x04` | `PanelButton_DigitalEffect`           |
| 14    | CPR 3   | DSP EFFECT (`0x04`)                                                                                                      | `0x00`, `0x05` | `PanelButton_DspEffect`               |
| 14    | CPR 3   | DIGITAL REVERB (`0x08`)                                                                                                  | `0x60`, `0x01` | `PanelButton_DigitalReverb`           |
| 14    | CPR 3   | ACOUSTIC ILLUSION (`0x10`)                                                                                               | `0x60`, `0x01` | `PanelButton_AcousticIllusion`        |
| 15    | CPR 4   | LEFT, RIGHT 2, RIGHT 1 (`0x07`)                                                                                          | `0x90`, `0x10` | `PanelButton_PartSelect`              |
| 15    | CPR 4   | ENTERTAINER (`0x08`)                                                                                                     | `0xA9`, `0x20` | `PanelButton_ModeKey`                 |
| 15    | CPR 4   | CONDUCTOR: LEFT (`0x10`)                                                                                                 | `0x90`, `0x01` | `PanelButton_Conductor`               |
| 15    | CPR 4   | CONDUCTOR: RIGHT 2 (`0x20`)                                                                                              | `0x90`, `0x00` | `PanelButton_Conductor`               |
| 15    | CPR 4   | CONDUCTOR: RIGHT 1 (`0x40`)                                                                                              | `0x90`, `0x00` | `PanelButton_Conductor`               |
| 15    | CPR 4   | TECHNI CHORD (`0x80`)                                                                                                    | `0x48`, `0x04` | `PanelAction_PostUnlessDemoOrParamC0` |
| 16    | CPR 5   | SEQUENCER: PLAY (`0x08`)                                                                                                 | `0xA8`, `0x14` | `PanelButton_SequencerPlay`           |
| 16    | CPR 5   | SEQUENCER: EASY REC (`0x10`)                                                                                             | `0xA9`, `0x20` | `PanelButton_ModeKey`                 |
| 16    | CPR 5   | SEQUENCER: MENU (`0x20`)                                                                                                 | `0xA9`, `0x20` | `PanelButton_ModeKey`                 |
| 17    | CPR 6   | PM 1, PM 2, PM 3, PM 4, PM 5, PM 6, PM 7, PM 8 (`0xFF`)                                                                  | `0x98`, `0x01` | `PanelButton_PanelMemoryNumber`       |
| 18    | CPR 7   | PANEL MEMORY: SET (`0x01`)                                                                                               | `0x98`, `0x01` | `PanelButton_PanelMemorySet`          |
| 18    | CPR 7   | PANEL MEMORY: NEXT BANK (`0x02`)                                                                                         | `0xA8`, `0x04` | `PanelButton_PanelMemoryNextBank`     |
| 18    | CPR 7   | PANEL MEMORY: BANK VIEW (`0x04`)                                                                                         | `0xA8`, `0x05` | `PanelButton_PanelMemorySet`          |
| 19    | CPR 8   | R1/R2 OCTAVE -, R1/R2 OCTAVE + (`0x18`)                                                                                  | `0x90`, `0x04` | `PanelButton_Octave`                  |
| 19    | CPR 8   | START/STOP (`0x20`)                                                                                                      | `0x48`, `0x05` | `PanelButton_StartStop`               |
| 19    | CPR 8   | SYNCHRO & BREAK (`0x40`)                                                                                                 | `0x48`, `0x05` | `PanelButton_SynchroBreak`            |
| 19    | CPR 8   | TAP TEMPO (`0x80`)                                                                                                       | `0xA8`, `0x12` | `PanelAction_PostUnlessDemo`          |
| 20    | CPR 9   | MEMORY A, MEMORY B (`0xC0`)                                                                                              | `0x00`, `0x00` | `PanelButton_SoundGroup`              |
| 21    | CPR 10  | MENU: SOUND (`0x04`)                                                                                                     | `0xA9`, `0x20` | `PanelButton_ModeKey`                 |
| 21    | CPR 10  | MENU: CONTROL (`0x08`)                                                                                                   | `0xA9`, `0x20` | `PanelButton_ModeKey`                 |
| 21    | CPR 10  | MENU: MIDI (`0x10`)                                                                                                      | `0xA9`, `0x20` | `PanelButton_ModeKey`                 |
| 21    | CPR 10  | MENU: DISK (`0x20`)                                                                                                      | `0xA9`, `0x20` | `PanelButton_ModeKey`                 |
| 22    | --      | pitch bend wheel (CPL `0xD1`) (`0xFF`)                                                                                   | `0xB1`, `0x00` | `PanelAction_PitchBend`               |
| 23    | --      | modulation wheel (CPL `0xD2`) (`0x7F`)                                                                                   | `0xB2`, `0x00` | `PanelAction_Modulation`              |
| 24    | --      | MAIN VOLUME (CPL `0xD3`) (`0x7F`)                                                                                        | `0xB0`, `0x00` | `PanelEvent_Post`                     |
| 25    | --      | TEMPO/PROGRAM data wheel (header 0xD7; records {0x19, delta, 0xFF}, mamedev/mame#15919) (`0xFF`)                         | `0xA9`, `0x21` | `PanelAction_PostUnlessDemo`          |
| 26    | --      | expression pedal (CPU AN0) (`0x7F`)                                                                                      | `0xB0`, `0x01` | `PanelAction_ExpressionPedal`         |
| 27    | --      | after touch (CPU AN1) (`0x7F`)                                                                                           | `0xB4`, `0x00` | `PanelAction_AfterTouch`              |
| 28    | --      | foot switch FS1 (PG.2) (`0x01`)                                                                                          | `0xA9`, `0x32` | `PanelAction_FootSwitch1`             |
| 28    | --      | foot switch FS2 (PG.3) (`0x02`)                                                                                          | `0xA9`, `0x33` | `PanelAction_FootSwitch2`             |
| 29    | --      | foot controller FC1 (PG.4) (`0x01`)                                                                                      | `0xA9`, `0x34` | `PanelAction_FootController1`         |
| 29    | --      | FC2 (PG.5) (`0x02`)                                                                                                      | `0xA9`, `0x35` | `PanelAction_FootController2`         |
| 29    | --      | FC3 (PG.6) (`0x04`)                                                                                                      | `0xA9`, `0x36` | `PanelAction_FootController3`         |
| 29    | --      | FC4 (PG.7) (`0x08`)                                                                                                      | `0xA9`, `0x37` | `PanelAction_FootController4`         |
| 30    | --      | PD.6 (`0x01`)                                                                                                            | `0xA8`, `0x41` | `PanelEvent_Post`                     |

**Held switches.**  `SwbtB3_OnPanelEvent` keeps two masks of the `0xA9` switch groups: bit N of `PANEL_SW_HELD_UP`
(0x02749A) is set while group N's UP switch is held, bit N of `PANEL_SW_HELD_DOWN` (0x02749E) while its DOWN switch
is.  Pressing the second half of a group posts `EVT_SW_BOTH`.  Their AND, `PANEL_SW_HELD_BOTH` (0x0274A2), picks
four combinations: 0x1100 (LEFT 1 + RIGHT 1 with LEFT 5 + RIGHT 5) saves an LCD screenshot (`CaptureLcd`) on a
debug build (version byte 0xFF); 0xA1 opens the software-version screen (`TITLE_SOFTVER`); 0x91 returns to
`TITLE_PS`; 0x89 posts `EVT_SHOW` to object 7.  All three masks are cleared on every mode or title change
(disassembly `notes/open4-kn5000-b/display/README.md`, kn5000-nmg; these words were once read as a screen
transition counter, timer and type, see [Display Subsystem]({{ site.baseurl }}/display-subsystem/)).

The tags of 22-27 are panel records: `0xB1` pitch bend, `0xB2` modulation, `0xB3` part expression, `0xB4`
channel pressure, `0xB0` byte +1 TOTAL EXPRESSION, byte +0 (inferred) master volume (see
[Panel Parameter Keys]({{ site.baseurl }}/panel-parameter-keys/)).  `PanelAction_PitchBend` spreads the byte over
a 14-bit bend (LSB `(b & 1) << 6`, MSB `b >> 1`).  `PanelAction_ExpressionPedal` follows the FOOT CONTROLLERS
assignment of the EXPRESSION PEDAL (key `0x2880`): 182 TOTAL EXPRESSION posts `{0xB0, 1}`, 183 retags to
`{0xB3, 0}`.  `PanelAction_AfterTouch` posts only while AFTER TOUCH is on (key `0x104`).

The `arg` of the LCD buttons is the sound editor's switch number (see [UI Framework]({{ site.baseurl }}/ui-framework/)):
0-7 the bottom columns, 8-12 the side rows. The `PanelButton_PairDown` side (DOWN n, LEFT n, PAGE DOWN,
TRANSPOSE -, OTHER PARTS/TR) keeps a held-button mask at RAM `0x8E84`, and the `PanelButton_PairUp` side
keeps one at `0x8E88`.

## 4. State Machine

### Serial Routine State Machine

The main CPU uses a state machine indexed by `CPANEL_STATE_MACHINE_INDEX` (address 0x8D8A) with values 0-10 (stored as byte offsets 0x00-0x28).

```
State Transition Diagram:

    ┌───────────────────────────────────────────────────────────────────────────────────┐
    │                                                                                   │
    │  IDLE (0)                                                                         │
    │    │                                                                              │
    │    │ CPanel_SendCommand called                                                    │
    │    v                                                                              │
    │  CPanel_SM_StartTX (1) ──> Start TX, check SCLK1                                  │
    │    │                       │                                                      │
    │    │ SCLK1=1               │ SCLK1=0 (panel talking)                              │
    │    v                       v                                                      │
    │  CPanel_SM_SendByte1 (2)   Back to IDLE (0)                                       │
    │    │                                                                              │
    │    │ TX byte, update LED index                                                    │
    │    v                                                                              │
    │  CPanel_SM_TXDelay1 (3) ──> Disable serial pins                                   │
    │    │                                                                              │
    │    v                                                                              │
    │  CPanel_SM_SendByteN (4) ──> Continue TX, count down CPANEL_PACKET_BYTE_COUNT     │
    │    │                         │                                                    │
    │    │ count > 1               │ count <= 1                                         │
    │    v                         v                                                    │
    │  CPanel_SM_TXDelay1 (loop)   CPanel_SM_TXDelay2 (5)                               │
    │                                │                                                  │
    │                                v                                                  │
    │                              CPanel_SM_TXComplete (6) ──> Check if more LED data  │
    │                                │                  │                               │
    │                                │ more             │ done                          │
    │                                v                  v                               │
    │                              CPanel_SM_StartTX    IDLE (0)                        │
    │                                                                                   │
    │  ═════════════════════════════════════════════════════════════════════════════    │
    │                                                                                   │
    │  CPanel_SM_RXByte1 (8) ──> RX phase 1, first byte from panel                      │
    │    │                                                                              │
    │    │ Byte received, calculate CPANEL_PACKET_BYTE_COUNT                            │
    │    v                                                                              │
    │  CPanel_SM_RXByteN (9) ──> RX phase 2, additional bytes                           │
    │    │                       │                                                      │
    │    │ count > 1             │ count <= 1                                           │
    │    v                       v                                                      │
    │  CPanel_SM_RXByteN (loop)  IDLE (0)                                               │
    │                                                                                   │
    └───────────────────────────────────────────────────────────────────────────────────┘
```

### CPANEL_PACKET_BYTE_COUNT Meaning

The variable `CPANEL_PACKET_BYTE_COUNT` (address 0x8D8B) tracks the expected byte count in multi-byte transfers:

| Value | Meaning                            |
|-------|------------------------------------|
| 0     | Idle/complete                      |
| 1     | Last byte expected                 |
| 2     | Standard 2-byte packet             |
| 3-18  | Extended packet, N bytes remaining |

**Calculation (from received byte A):**
```c
if ((A & 0x3F) < 0x30) {
    CPANEL_PACKET_BYTE_COUNT = 2;
} else {
    CPANEL_PACKET_BYTE_COUNT = (A & 0x0F) + 3;  // 3 to 18 bytes
}
```

### Serial Routine Jump Table

Located at `CPANEL_STATE_MACHINE_TABLE` (0xFC4489):

| Offset | Routine                | Address  | Purpose                 |
|--------|------------------------|----------|-------------------------|
| 0x00   | `CPanel_SM_Idle`       | 0xFC47E9 | Idle state              |
| 0x04   | `CPanel_SM_StartTX`    | 0xFC44F9 | Start TX sequence       |
| 0x08   | `CPanel_SM_SendByte1`  | 0xFC45A8 | Send LED data byte      |
| 0x0C   | `CPanel_SM_TXDelay1`   | 0xFC4544 | Disable pins, next byte |
| 0x10   | `CPanel_SM_SendByteN`  | 0xFC460D | Continue LED data       |
| 0x14   | `CPanel_SM_TXDelay2`   | 0xFC4573 | Finalize LED group      |
| 0x18   | `CPanel_SM_TXComplete` | 0xFC4672 | Check for more data     |
| 0x1C   | `CPanel_SM_Idle`       | 0xFC47E9 | (duplicate) Idle        |
| 0x20   | `CPanel_SM_RXByte1`    | 0xFC46EA | RX first byte           |
| 0x24   | `CPanel_SM_RXByteN`    | 0xFC4767 | RX subsequent bytes     |
| 0x28   | `CPanel_SM_Idle`       | 0xFC47E9 | (duplicate) Unreachable |

## 5. HLE Implementation Guide

### MAME Device Class Structure

```cpp
// kn5000_cpanel.h

#ifndef MAME_MATSUSHITA_KN5000_CPANEL_H
#define MAME_MATSUSHITA_KN5000_CPANEL_H

#pragma once
#include <queue>

class kn5000_cpanel_device : public device_t
{
public:
    kn5000_cpanel_device(const machine_config &mconfig, const char *tag, device_t *owner, uint32_t clock = 0);

    // Serial interface from main CPU
    void rxd(int state);             // Serial data in (from CPU TXD)
    void sioclk(int state);          // Serial clock
    void tx_start(int state);        // Called when CPU starts a new byte (1=real, 0=phantom)

    // Callbacks to main CPU
    auto txd() { return m_txd_cb.bind(); }         // Serial data out (to CPU RXD)
    auto sclk_out() { return m_sclk_out_cb.bind(); } // Self-clock output
    auto inta() { return m_inta_cb.bind(); }        // Interrupt acknowledge

    // Configuration
    void set_baudrate(uint16_t br);
    void set_cpl_port(int n, ioport_port *port);    // Left panel segment 0-10
    void set_cpr_port(int n, ioport_port *port);    // Right panel segment 0-10
    void encoder_detent(int delta);                 // one data-wheel step, reported on the next scan

protected:
    virtual void device_start() override;
    virtual void device_reset() override;

    TIMER_CALLBACK_MEMBER(timer_callback);          // Baud rate timer (self-clock)
    TIMER_CALLBACK_MEMBER(idle_detect_callback);    // SCLK idle → assert INTA
    TIMER_CALLBACK_MEMBER(self_clock_callback);     // Drive SCLK for response delivery
    TIMER_CALLBACK_MEMBER(button_scan_callback);    // Periodic button matrix scan (7 ms)

private:
    // Serial RX state
    uint8_t m_rx_clock_count;        // Bits remaining (8 = idle)
    uint8_t m_rx_shift_register;
    uint8_t m_rxd;                   // Current RXD line state
    uint8_t m_sioclk_state;          // Previous clock state

    // Serial TX state
    uint8_t m_tx_clock_count;        // Bits remaining in current byte
    uint8_t m_tx_shift_register;
    std::queue<uint8_t> m_tx_queue;  // Pipelined TX bytes

    // Command processing
    uint8_t m_cmd_buffer[2];
    uint8_t m_cmd_index;

    // Protocol state
    bool m_initialized;
    bool m_self_clocking;            // Currently driving SCLK for response
    bool m_inta_asserted;            // PE.5 interrupt line state
    bool m_accept_next_byte;         // false = skip phantom byte
    bool m_tx_output_enabled;        // false = suppress TX during phantom edges
    bool m_rx_waiting_for_start;     // Ignore edges until next tx_start

    // Button change detection
    uint8_t m_last_button_state[22];    // 11 segments × 2 panels (confirmed)
    uint8_t m_pending_button_state[22]; // Per-segment confirmation buffer

    // Callbacks
    devcb_write_line m_txd_cb;
    devcb_write_line m_sclk_out_cb;
    devcb_write_line m_inta_cb;

    // Input port pointers (set by main driver)
    ioport_port *m_cpl_ports[11];    // Left panel segments 0-10
    ioport_port *m_cpr_ports[11];    // Right panel segments 0-10
    int32_t m_encoder_accum;         // data-wheel detents not yet reported

    // LED outputs
    output_finder<50> m_cpl_leds;
    output_finder<69> m_cpr_leds;

    // Internal methods
    void process_command();
    void send_byte(uint8_t data);
    void process_received_byte(uint8_t data);
    void send_sync_packet();
    void send_button_packet(int segment, bool is_left_panel);
    void send_encoder_packet(int8_t detents);       // [0xD7, count]
    void send_all_button_states(bool is_left_panel);
    void process_led_command(uint8_t row, uint8_t data);
    uint8_t read_button_segment(int segment, bool is_left_panel);
};

DECLARE_DEVICE_TYPE(KN5000_CPANEL, kn5000_cpanel_device)

#endif // MAME_MATSUSHITA_KN5000_CPANEL_H
```

### Key Callbacks to Implement

```cpp
void kn5000_cpanel_device::process_command()
{
    uint8_t cmd = m_cmd_buffer[0];
    uint8_t param = m_cmd_buffer[1];

    // Panel selection: bits 7-5 >= 4 means right panel
    bool is_right_panel = (cmd & 0xE0) >= 0x80;

    switch (cmd)
    {
    // Initialization commands — respond with sync
    case 0x1F:  case 0x1D:  case 0x1E:  case 0xDD:
        send_sync_packet();  // Type 3: 0x18, 0x00
        m_initialized = true;
        break;

    // Query commands (left panel variants)
    case 0x20:  case 0x25:
    {
        int segment = param & 0x0F;
        if (param == 0x00)
            send_sync_packet();
        else if (segment <= 0x0A)
            send_button_packet(segment, true);   // left panel
        else if (segment == 0x0B)
            send_button_packet(segment, false);  // hardware status
        else
            send_sync_packet();
        break;
    }

    // Query commands (right panel variants)
    case 0xE0:  case 0xE2:  case 0xE3:
    {
        int segment = param & 0x0F;
        if (param == 0x00)
            send_sync_packet();
        else if (segment <= 0x0B)
            send_button_packet(segment, false);  // right panel
        else
            send_sync_packet();
        break;
    }

    // Init button state arrays — send all 11 segments
    case 0x2B:  send_all_button_states(true);   break;  // left
    case 0xEB:  send_all_button_states(false);  break;  // right

    // LED control commands — NO response (silent processing)
    // Right panel: rows 0x00, 0x01, 0x02, 0x03, 0x04, 0x08, 0x0A, 0x0B, 0x0C
    // Left panel:  rows 0xC0, 0xC1, 0xC2, 0xC3, 0xC4, 0xC8
    case 0x00: case 0x01: case 0x02: case 0x03: case 0x04:
    case 0x08: case 0x0A: case 0x0B: case 0x0C:
    case 0xC0: case 0xC1: case 0xC2: case 0xC3: case 0xC4: case 0xC8:
        process_led_command(cmd, param);
        break;

    default:
        // Unknown command — do NOT respond.
        // Sending spurious sync responses triggers INTA delivery,
        // disrupting the firmware's serial state machine.
        break;
    }

    // Start idle detection for INTA-based response delivery
    if (!m_self_clocking && (m_tx_clock_count > 0 || !m_tx_queue.empty()))
        m_idle_detect_timer->adjust(attotime::from_usec(50));
}

void kn5000_cpanel_device::send_button_packet(int segment, bool is_left_panel)
{
    uint8_t state = read_button_segment(segment, is_left_panel);

    // Header encoding: bits 7:6 select panel identity
    //   Right panel: 00 (header = segment)
    //   Left panel:  11 (header = 0xC0 | segment)
    // WARNING: 0x40 (bits 7:6=01) falls in ROM lookup table dead zone!
    uint8_t header = (segment & 0x0F);
    if (is_left_panel)
        header |= 0xC0;

    send_byte(header);
    send_byte(state);

    // Update confirmed state for change detection
    int state_idx = is_left_panel ? (segment + 11) : segment;
    m_last_button_state[state_idx] = state;
    m_pending_button_state[state_idx] = state;
}
```

**Critical implementation notes:**
- **LED commands must NOT generate responses.** The firmware sends LED commands in rapid batches via the TX state machine. If the HLE queues sync responses, they accumulate during continuous clocking (idle_detect never fires). When finally delivered via INTA, they set IOC=1, blocking the baud rate timer and deadlocking the TX state machine.
- **Phantom byte filtering:** The `tx_start` callback signals whether each byte is real (PFFC on) or phantom (PFFC off). The HLE uses deferred flag application to handle a MAME timing race where `tx_start` for byte N+1 fires before byte N's last rising edge.
- **Idle detect sliding window:** Every SCLK edge retriggers the 50 µs timer. This ensures INTA fires only after the firmware's last phantom byte completes, not during the TX state machine's inter-byte gaps. **⚠ This is also a hazard, not only a virtue** (see the known-limitation box at the top): because *every* edge retriggers it, a clock that runs when it should not — e.g. an internal baud generator free-running because the receiver's bit counter was stranded mid-byte — will retrigger this window faster than it can expire. INTA is then never asserted again and the panel link wedges for the whole session. If you implement the sliding window, make sure nothing can produce an unbounded stream of edges the protocol did not ask for.

### Button State Reporting Format

Buttons are organized in 11 segments per panel, with 8 buttons per segment.

#### Control Panel Right (CPR) Button Mapping

| Segment | Bit 0 | Bit 1 | Bit 2 | Bit 3 | Bit 4 | Bit 5 | Bit 6 | Bit 7 |
|---------|-------|-------|-------|-------|-------|-------|-------|-------|
| **CPR_SEG0** | - | - | - | - | - | TRANSPOSE - | TRANSPOSE + | - |
| **CPR_SEG1** | ORGAN & ACCORDION | ORCHESTRAL PAD | SYNTH | BASS | DIGITAL DRAWBAR | ACCORDION REGISTER | GM SPECIAL | DRUM KITS |
| **CPR_SEG2** | PIANO | GUITAR | STRINGS & VOCAL | BRASS | FLUTE | SAX & REED | MALLET & ORCH PERC | WORLD PERC |
| **CPR_SEG3** | SUSTAIN | DIGITAL EFFECT | DSP EFFECT | DIGITAL REVERB | ACOUSTIC ILLUSION | - | - | - |
| **CPR_SEG4** | LEFT | RIGHT 2 | RIGHT 1 | ENTERTAINER | CONDUCTOR: LEFT | CONDUCTOR: RIGHT 2 | CONDUCTOR: RIGHT 1 | TECHNI CHORD |
| **CPR_SEG5** | - | - | - | SEQUENCER: PLAY | SEQUENCER: EASY REC | SEQUENCER: MENU | - | - |
| **CPR_SEG6** | PM 1 | PM 2 | PM 3 | PM 4 | PM 5 | PM 6 | PM 7 | PM 8 |
| **CPR_SEG7** | PM: SET | PM: NEXT BANK | PM: BANK VIEW | - | - | - | - | - |
| **CPR_SEG8** | - | - | - | R1/R2 OCTAVE - | R1/R2 OCTAVE + | START/STOP | SYNCHRO & BREAK | TAP TEMPO |
| **CPR_SEG9** | - | - | - | - | - | - | MEMORY A | MEMORY B |
| **CPR_SEG10** | - | - | MENU: SOUND | MENU: CONTROL | MENU: MIDI | MENU: DISK | - | - |

#### Control Panel Left (CPL) Button Mapping

| Segment | Bit 0 | Bit 1 | Bit 2 | Bit 3 | Bit 4 | Bit 5 | Bit 6 | Bit 7 |
|---------|-------|-------|-------|-------|-------|-------|-------|-------|
| **CPL_SEG0** | STANDARD ROCK | R & ROLL & BLUES | POP & BALLAD | FUNK & FUSION | SOUL & MODERN DANCE | BIG BAND & SWING | JAZZ COMBO | - |
| **CPL_SEG1** | COMPOSER: MEMORY | COMPOSER: MENU | SOUND ARRANGER: SET | SOUND ARRANGER: ON/OFF | MUSIC STYLIST | FADE IN | FADE OUT | - |
| **CPL_SEG2** | FILL IN 1 | FILL IN 2 | INTRO & ENDING 1 | INTRO & ENDING 2 | - | - | PAGE DOWN | PAGE UP |
| **CPL_SEG3** | DEMO | MSP BANK | MSP MENU | MSP STOP/RECORD | - | - | - | - |
| **CPL_SEG4** | VARIATION 1 | VARIATION 2 | VARIATION 3 | VARIATION 4 | MUSIC STYLE ARRANGER | SPLIT POINT | AUTO PLAY CHORD | - |
| **CPL_SEG5** | MSP 1 | MSP 2 | MSP 3 | MSP 4 | MSP 5 | MSP 6 | - | - |
| **CPL_SEG6** | U.S. TRAD | COUNTRY | LATIN | MARCH & WALTZ | PARTY TIME | SHOWTIME & TRAD DANCE | WORLD | CUSTOM |
| **CPL_SEG7** | RIGHT 5 | RIGHT 4 | DISPLAY HOLD | EXIT | DOWN 7 | UP 7 | DOWN 8 | UP 8 |
| **CPL_SEG8** | RIGHT 3 | RIGHT 2 | RIGHT 1 | - | DOWN 5 | UP 5 | DOWN 6 | UP 6 |
| **CPL_SEG9** | LEFT 5 | LEFT 4 | LEFT 3 | - | DOWN 3 | UP 3 | DOWN 4 | UP 4 |
| **CPL_SEG10** | LEFT 2 | LEFT 1 | HELP | OTHER PARTS/TR | DOWN 1 | UP 1 | DOWN 2 | UP 2 |

**Known button combinations (from firmware):**

| Segment  | Bitmask | Buttons                                            | Effect                                                                            |
|----------|---------|----------------------------------------------------|-----------------------------------------------------------------------------------|
| CPL_SEG4 | 0x6C    | AUTO PLAY CHORD + SPLIT POINT + VAR4 + VAR3        | Display software build numbers                                                    |
| CPR_SEG1 | 0x70    | GM SPECIAL + ACCORDION REGISTER + DIGITAL DRAWBAR  | MPVersion screen (`EVT_MP_VERSION`) + firmware version on the LEDs                |
| CPL_SEG6 | 0x38    | SHOWTIME & TRAD DANCE + PARTY TIME + MARCH & WALTZ | Factory reset (Initial Setting); see [Test Modes]({{ site.baseurl }}/test-modes/) |
| CPR_SEG6 | 0x0F    | PM 1 + PM 2 + PM 3 + PM 4                          | Firmware update mode                                                              |

### LED Control Interface

LEDs are controlled via the `CPANEL_LED_TX_BUFFER` array (60 bytes at 0x8E01):

```cpp
void kn5000_cpanel_device::update_leds(int index, uint8_t pattern)
{
    // Index wraps at 0x3C (60)
    index %= 60;
    m_led_state[index] = pattern;

    // Map LED index to physical LEDs
    // The LED array is transmitted in 2-byte sequences
    // Byte 0: Row select (bits 5-0 = row, bits 7-6 = panel select)
    // Byte 1: Column pattern (which LEDs in row are lit)

    // Update MAME output for visual feedback
    for (int bit = 0; bit < 8; bit++) {
        machine().output().set_indexed_value("led", index * 8 + bit, BIT(pattern, bit));
    }
}
```

#### Control Panel Right (CPR) LED Mapping

| Row | Bit 0 | Bit 1 | Bit 2 | Bit 3 | Bit 4 | Bit 5 | Bit 6 | Bit 7 |
|-----|-------|-------|-------|-------|-------|-------|-------|-------|
| **0x00** | SUSTAIN | DIGITAL EFFECT | DSP EFFECT | DIGITAL REVERB | ACOUSTIC ILLUSION | SEQUENCER: PLAY | SEQUENCER: EASY REC | SEQUENCER: MENU |
| **0x01** | PIANO | GUITAR | STRINGS & VOCAL | BRASS | FLUTE | SAX & REED | MALLET & ORCH PERC | WORLD PERC |
| **0x02** | ORGAN & ACCORDION | ORCHESTRAL PAD | SYNTH | BASS | DIGITAL DRAWBAR | ACCORDION REGISTER | GM SPECIAL | DRUM KITS |
| **0x03** | PM 1 | PM 2 | PM 3 | PM 4 | PM 5 | PM 6 | PM 7 | PM 8 |
| **0x04** | PART: LEFT | PART: RIGHT 2 | PART: RIGHT 1 | ENTERTAINER | COND: LEFT | COND: RIGHT 2 | COND: RIGHT 1 | TECHNI CHORD |
| **0x08** | MENU: SOUND | MENU: CONTROL | MENU: MIDI | MENU: DISK | - | - | - | - |
| **0x0A** | MEMORY A | MEMORY B | - | - | - | - | - | - |
| **0x0B** | SYNCHRO & BREAK | R1/R2 OCTAVE - | R1/R2 OCTAVE + | BANK VIEW | - | - | - | - |
| **0x0C** | START/STOP BEAT 1 | START/STOP BEAT 2 | START/STOP BEAT 3 | START/STOP BEAT 4 | - | - | - | - |

#### Control Panel Left (CPL) LED Mapping

| Row | Bit 0 | Bit 1 | Bit 2 | Bit 3 | Bit 4 | Bit 5 | Bit 6 | Bit 7 |
|-----|-------|-------|-------|-------|-------|-------|-------|-------|
| **0xC0** | COMPOSER: MEMORY | COMPOSER: MENU | SOUND ARR: SET | SOUND ARR: ON/OFF | MUSIC STYLIST | FADE IN | FADE OUT | DISPLAY HOLD |
| **0xC1** | U.S. TRAD | COUNTRY | LATIN | MARCH & WALTZ | PARTY TIME | SHOWTIME & TRAD DANCE | WORLD | CUSTOM |
| **0xC2** | STANDARD ROCK | R & ROLL & BLUES | POP & BALLAD | FUNK & FUSION | SOUL & MODERN DANCE | BIG BAND & SWING | JAZZ COMBO | MSP: MENU |
| **0xC3** | VARIATION 1 | VARIATION 2 | VARIATION 3 | VARIATION 4 | MUSIC STYLE ARRANGER | AUTO PLAY CHORD | - | - |
| **0xC4** | FILL IN 1 | FILL IN 2 | INTRO & ENDING 1 | INTRO & ENDING 2 | SPLIT POINT (LEFT) | SPLIT POINT (CENTER) | SPLIT POINT (RIGHT) | TEMPO/PROGRAM |
| **0xC8** | OTHER PARTS/TR | - | - | - | - | - | - | - |

### Analog Controller / Encoder Format

The three analog controls of the CPL board (pitch bend, modulation, MAIN VOLUME) send **absolute 8-bit A/D values** in Type 2 frames — NOT signed deltas. The expression pedal and the after-touch sensor are read by the main CPU's own A/D converter, not by a panel: `AnalogIn_PollCpuAdc` feeds `ADREG04` (AN0) and `ADREG15` (AN1) through the handlers of IDs 2 and 5 (see [Main-CPU A/D: expression pedal and after touch](#main-cpu-ad-expression-pedal-and-after-touch)). The main CPU compares each value with the previous stored value to detect changes.

**What each one is (2026-10-31, tracker item kn5000-3c7).** The controls were read from the schematics (CPL board, sheet II-35; HB board, sheet II-26; CPU SECTION (A), sheet II-11) and confirmed by the events their records post, followed to the MIDI-out builders (disassembly notes `notes/open4-kn5000-b/cpanel/README.md`; the handler and variable names were renamed after this reading):

| input                     | record | action (`PanelButton_ActionLists`)                                                   | event tag                                                     | MIDI out (handler of `MidiDispatchCC_HandlerTable`)                                                                                                       | control                       |
|---------------------------|--------|--------------------------------------------------------------------------------------|---------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------|
| ID 25, header `0xD1`      | 22     | `PanelAction_PitchBend`: byte b as LSB `(b & 1) << 6`, MSB `b >> 1` (0xFF = 127/127) | 0xB1                                                          | `MidiCC_ChannelDispatch_CtrlFlags`: status `0xE0` \| channel, LSB, MSB, to `MidiTx_PartTargets_PitchBend`                                                 | pitch bend wheel              |
| ID 26, header `0xD2`      | 23     | `PanelAction_Modulation`                                                             | 0xB2                                                          | `MidiCC_ChannelDispatch_Ctrl1`: CC 1, to `MidiTx_PartTargets_CC1_Modulation`                                                                              | modulation wheel              |
| ID 27, header `0xD3`      | 24     | `PanelEvent_Post`                                                                    | 0xB0, controller 0                                            | `ExtData_Voice_CompareAndDispatch_Helper`: status 0xB0, controller 0 (it also re-flags `ANALOG_MAIN_VOLUME_PENDING`)                                      | MAIN VOLUME slider            |
| A/D channel 0 (`ADREG04`) | 26     | `PanelAction_ExpressionPedal`                                                        | 0xB0, controller 1; or 0xB3 when panel parameter 0x2880 = 183 | CC 1 (`MidiCh_ConfigVoiceAndParts`), or CC 11 (`MidiCC_ChannelDispatch_Ctrl3`, `MidiTx_PartTargets_CC11_Expression`); nothing unless 0x2880 is 182 or 183 | expression pedal (`EXP`)      |
| A/D channel 1 (`ADREG15`) | 27     | `PanelAction_AfterTouch`, only when panel parameter 0x104 is set                     | 0xB4                                                          | `MidiCC_ChannelDispatch_CtrlFlags2`: status `0xD0` \| channel, to `MidiTx_PartTargets_ChannelPressure`                                                    | after touch (`AFT`)           |

The event tag is the first byte of the panel event; `Audio_MainPeriodicUpdate` hands each queued event to `SoundProgram_DispatchTable[tag]`, whose 0xB1 / 0xB2 / 0xB3 / 0xB4 handlers pass the tag on as the status of `MIDI_DispatchCC`. The two main-CPU A/D inputs are wired on the CPU SECTION (A) sheet: `EXP` -> R71 -> pin 150 AN0, `AFT` -> MA110 clamp, R18 -> pin 151 AN1. [INFERENCE] Record 0xB0 byte +0 is the master volume: no panel-parameter key for it was found (byte +1 is TOTAL EXPRESSION, +3 the fade level).

**Type 2 Packet Format (2 bytes):**

| Byte | Bits | Field |
|------|------|-------|
| 0 | 7-6 | Encoder ID high bits (bits 4-3 of 5-bit ID) |
| 0 | 5-3 | `010` = Type 2 marker |
| 0 | 2-0 | Encoder ID low bits (bits 2-0 of 5-bit ID) |
| 1 | 7-0 | Raw 8-bit ADC value (absolute position) |

**Encoder ID Extraction (from `CPanel_EncoderDispatch`):**
```
encoder_id = (byte0 & 0x07) | ((byte0 & 0xC0) >> 3)  // 5-bit ID, range 0-31
```

**Active Encoder IDs and Handlers:**

| ID  | Handler                          | Control          | Processing                                                                                    | Output variable                 |
|-----|----------------------------------|------------------|-----------------------------------------------------------------------------------------------|---------------------------------|
| 2   | `Encoder_ProcessExpressionPedal` | expression pedal | invert, /2, `ENCODER_LUT_EXPRESSION_PEDAL` (128 B)                                            | `ANALOG_EXPRESSION_PEDAL_VALUE` |
| 5   | `Encoder_ProcessAfterTouch`      | after touch      | `ENCODER_LUT_AFTERTOUCH` (256 B), then threshold and curve (record 0x93 +5/+6)                | `ANALOG_AFTERTOUCH_VALUE`       |
| 25  | `Encoder_ProcessPitchBend`       | pitch bend       | invert, `ENCODER_LUT_PITCHBEND` (256 B, centre dead band); bend-range rescale while recording | `ANALOG_PITCHBEND_VALUE`        |
| 26  | `Encoder_ProcessModulation`      | modulation wheel | /2, `ENCODER_LUT_MODULATION` (128 B)                                                          | `ANALOG_MODULATION_VALUE`       |
| 27  | `Encoder_ProcessMainVolume`      | MAIN VOLUME      | invert, /2, `ENCODER_LUT_MAIN_VOLUME` (linear), never suppresses a repeat                     | `ANALOG_MAIN_VOLUME_VALUE`      |
| 31  | `Encoder_PassthroughIdentity`    | data wheel       | none (signed detent count)                                                                    | --                              |

None of these values is a MIDI controller number inside the firmware.

- **Pitch bend.** `ENCODER_LUT_PITCHBEND` has a plateau of 0x80 over raw 0x77..0x89: a centre dead band. While a part records (`CMP_RECORD_PART` bits 0-3) or `(0x7f0b)` is set, `Encoder_ProcessPitchBend` rescales to `64 + (v/2 - 64) * n/12` with `n = ENCODER_BEND_RANGE` (record 0x93 byte +4 bits 0-3, set by `Encoder_OnTouchSensitivityChange`); `ENCODER_LUT_BEND_RANGE_MULT[k] = round(256 (k+1) / 12)` and `ENCODER_LUT_BEND_RANGE_OFFSET[k] = 64 * MULT[k]`, 12 entries; `n = 0` sends nothing. [INFERENCE] It is a bend range in semitones, 1..12: the 12 steps of n/12 fit that and nothing else found; no screen that edits record 0x93 byte +4 was traced.
- **After touch.** `Encoder_AfterTouch_ApplyThresholdCurve` computes `(max(v, T) - T) * 256 / 236 * M[C] / 20`, clamped to 127, with `T = ENCODER_AFTERTOUCH_THRESHOLD` (record 0x93 byte +6 bits 0-6, `SndParam_AfterTouch_Threshold`) and `C = ENCODER_AFTERTOUCH_CURVE` (byte +5, `SndParam_AfterTouch_Curve`, range 1..10) indexing the 11-entry `ENCODER_LUT_AFTERTOUCH_CURVE_MULT`.

**Value Processing Pipeline (typical):**
1. Raw 8-bit value from MCU ADC (0-255)
2. Optional invert (`cpl a` = 255-value) for IDs 2, 25 and 27
3. Divide by 2 (`srl a, 1`) → 0-127 index
4. ROM lookup table (`ENCODER_LUT_*`) → 0-127
5. Compare with previously stored value; if unchanged, return 0xFFFF (no event)
6. Store new value, set "pending change" flag (bit 7 of `*_PENDING` variable)

**Lookup Tables (ROM at 0xEDAxxxh):**

| Table                               | Address  | Control                              |
|-------------------------------------|----------|--------------------------------------|
| `ENCODER_LUT_EXPRESSION_PEDAL`      | 0xEDA13C | expression pedal (128 B)             |
| `ENCODER_LUT_AFTERTOUCH`            | 0xEDA1BC | after touch (256 B)                  |
| `ENCODER_LUT_AFTERTOUCH_CURVE_MULT` | 0xEDA2BC | after-touch curve multipliers (11)   |
| `ENCODER_LUT_PITCHBEND`             | 0xEDA2D2 | pitch bend (256 B)                   |
| `ENCODER_LUT_BEND_RANGE_MULT`       | 0xEDA3D2 | bend-range rescale multipliers (12)  |
| `ENCODER_LUT_BEND_RANGE_OFFSET`     | 0xEDA3EA | bend-range rescale offsets (12)      |
| `ENCODER_LUT_MODULATION`            | 0xEDA402 | modulation wheel (128 B)             |
| `ENCODER_LUT_MAIN_VOLUME`           | 0xEDA482 | MAIN VOLUME (linear)                 |

**HLE Implementation:**
```cpp
void kn5000_cpanel_device::process_analog_input(int encoder_id, uint8_t adc_value)
{
    // Encoder packet: Type 2, absolute ADC value
    uint8_t response[2];
    response[0] = 0x10 | (encoder_id & 0x07) | ((encoder_id & 0x18) << 3);
    response[1] = adc_value;  // Absolute position, NOT delta
    send_response(response, 2);
}
```

For the CPL controls, `response[0]` is `0xD1` / `0xD2` / `0xD3` (IDs 25 / 26 / 27).

### Data Wheel (Jog Dial)

The data wheel is the large rotary encoder below the LCD, labelled TEMPO/PROGRAM. The service
manual puts **SW101 "ENCODER SWITCH" (QSRGT002AA)** on the CPL board, wired to the ROTA/ROTB
quadrature inputs of that board's `M37471M2196S` MCU. The MCU counts detents; the main CPU never
sees the quadrature.

The wheel travels the **same serial link, interrupt and parser as the button segments**, as a
two-byte frame:

```
[0xD7] [signed detent count]
```

`0xD7` is a Type 2 header (see below). Its bits 5:3 = `010` are the packet type, and the CPU reads
bits 7:6 = `11` and 2:0 = `111` as bits 4:3 and 2:0 of the encoder ID, 31, not as a button packet's
panel select and segment. The second byte is a **count** of detents accumulated since the last
report, not a direction. The header becomes a record index via `((A & 0xC0) >> 1) | (A & 0x1F)`,
so `0xD7` maps to index `0x77`, where the translation table holds record `0x19`. Only `0xD7` and
`0xF7` reach that index.

The translation table's address moves between revisions (`0xED9F28` on v5, `0xED9F40` on v6,
`0xEDA03C` on v7-v10) but its content is byte-identical in all six.

The wheel's frame *is* a Type 2 packet. Header `0xD7` has type bits 5:3 = `010`, so
`CPanel_RX_ParseNext` hands it to `CPanel_RX_EncoderPacket`. Its ID bits give
`(0xD7 & 0x07) | ((0xD7 & 0xC0) >> 3)` = 31: the pass-through entry `Encoder_PassthroughIdentity`
of the table at `0xEDA0BC`. That entry returns the count unchanged, with no lookup table and no
MIDI CC. `CPanel_RX_EncoderPacket` then queues `{0xD7, count, 0xFF}`, where `0xFF` is the record's
changed-bits byte. The analog IDs are 2 and 5 (the main CPU's A/D channels 0 and 1) and 25, 26 and 27
(the pitch-bend wheel, the modulation wheel and a third, unestablished control). Every other ID returns a
constant 1.

#### Segment 0x0B: a boot-time settling register

During boot only, `CPanel_PollStartup` / `CPanel_ButtonPollLoop` (`cpanel_routines.s:505-549`)
sends `0x20 0x0B` to the left panel MCU and stores the reply at DRAM[0x8E55]:

| Bit set in the reply | Derived state at DRAM[0x8E6A] |
|----------------------|-------------------------------|
| 7                    | 0x0D                          |
| 6 (bit 7 clear)      | 0x0E                          |
| neither              | 0x0C                          |

`CPanel_EncoderCheck` re-polls until the value repeats on two consecutive reads, then returns.
Steady state never sends `0x20 0x0B` again and never reads DRAM[0x8E55]; the only steady-state
poll command is `E0 13` (right panel segment 3 with flag 0x10). This register is a startup
settling check, not the rotation path.

#### Event chain

```
detent -> panel MCU count -> [0xD7, count] -> record 0x19
  -> SwbtWr event: payload 0x21 at DRAM[0xC07D], count at DRAM[0xC07E]
  -> CtrlPanel_HandleSerialPort (main_title_ctrl_panel.s:301)
  -> acceleration curve -> event 0x1C0001F
  -> GroupBox_HandleCursorNav (ui_control_panel.s:3985)
```

`CtrlPanel_HandleSerialPort` requires DRAM[0xC07D] == 0x21 and a non-zero count at DRAM[0xC07E].
It deletes any pending `0x1C0001F`, computes `sext8(count + 0x10)`, indexes a **33-entry table of
signed longs** (`0xEA98E2` on v10, `0xEA97CE` on v5) and posts `0x1C0001F` with the entry as its
parameter. The table is an acceleration curve running monotonically from `+7` at index 0 to `-7`
at index 32, so a **clockwise turn must be reported as a negative count** to raise the value, and
a larger magnitude moves the value further per detent.

> ⚠ The index is computed with no bounds check. The table (`CtrlPanel_DialStepByDelta`) has 33
> entries for deltas -16..+16, so only wire magnitudes **-16..+16** are legal (MAME clamps
> to -16..+15). Clamping is the panel's responsibility.

Full derivation, per-revision tables and the reproducing probes: see
[Data Wheel (TEMPO/PROGRAM Encoder)]({{ site.baseurl }}/data-wheel-investigation/).

#### Dial Callback System (RAM at 0x3EF50-0x3EF6A)

Once the 0x1C0001F event is posted, it reaches the focused widget through the NAKA event dispatch system:

| Address | Field | Description |
|---------|-------|-------------|
| 0x3EF50 | Dial Enable | Enable flag (word) |
| 0x3EF52 | SetDialUp callback | XWA component (clockwise) |
| 0x3EF56 | SetDialDown callback | XWA component (counter-clockwise) |
| 0x3EF5A | SetDialUp event | XBC component (event code 0x1C00007) |
| 0x3EF5E | SetDialDown event | XBC component |
| 0x3EF62 | SetDialUp param | XDE component |
| 0x3EF66 | SetDialDown param | XDE component |
| 0x3EF6A | Dial Focus | Currently focused UI object (32-bit) |

`SetDialUp` / `SetDialDown` (presentation_sound_nav.s:381-391) are **setup functions** that register callbacks — they store workspace, event code, and parameter into the dial callback table. The actual invocation of these callbacks is triggered by the 0x1C0001F event reaching `GroupBox_HandleCursorNav`.

**Related NAKA widget events:**
- 0x1E0006F: GroupBox_DialEnable
- 0x1E00070: GroupBox_DialDown (also posted by accompaniment_engine.s for sequencer parameter changes)
- 0x1E00071: GroupBox_DialUp (also posted by accompaniment_engine.s)
- 0x1E00087: GroupBox_SetDialFocus
- 0x1E00088: GroupBox_GetDialFocus

#### Two Polling Modes

The firmware has two separate polling loops:

1. **Startup mode** (`CPanel_PollStartup` + `CPanel_ButtonPollLoop`, lines 505-549): sends `0x20 0x0B`, repeats until the segment 0x0B reply is stable, runs only during boot.
2. **Steady-state mode** (`CPanel_InterruptPoll_MainLoop`, lines 1060-1177): sends `E0 13` periodically, updates LEDs, handles INTA packets. There is no encoder poll here — the wheel pushes its `[0xD7, count]` frames over INTA like any other panel change.


### Main-CPU A/D: expression pedal and after touch

The main loop calls `AnalogIn_PollCpuAdc` (0xFC6ED1) every iteration (when input processing is enabled) to detect changes in the main CPU's A/D results ADREG04 and ADREG15 and re-route them through the encoder value processing pipeline. Channel 0 is AN0 = expression pedal (ID 2), channel 1 is AN1 = after touch (ID 5), from the CPU SECTION (A) sheet: `EXP` -> R71 -> pin 150 AN0, `AFT` -> MA110 clamp, R18 -> pin 151 AN1 (see [Analog controllers](#analog-controller--encoder-format)). `AnalogIn_PollExpressionPedal` and `AnalogIn_PollAfterTouch` are the two per-channel halves.

**Two-channel processing:**

| Channel | Status Register           | Output Buffer             | Previous Value                | Encoder ID   | Controller               |
|---------|---------------------------|---------------------------|-------------------------------|--------------|--------------------------|
| 0       | `ADC_AN0_STATUS` (0x8F04) | `ADC_AN0_OUTPUT` (0x8F10) | `ADC_AN0_LAST_VALUE` (0x8EFC) | 2            | expression pedal         |
| 1       | `ADC_AN1_STATUS` (0x8F06) | `ADC_AN1_OUTPUT` (0x8F16) | `ADC_AN1_LAST_VALUE` (0x8EFE) | 5            | after touch              |

Each channel reads its current A/D result via `AnalogIn_ReadAdcHigh`, computes the delta against the previously stored value, applies debounce filtering through `AnalogIn_DebounceChange`, and if the delta is confirmed valid, re-dispatches through `CPanel_EncoderDispatch` to apply lookup table conversion. The result is stored in the output buffer with bit 7 of the flags byte set to indicate a value change; `PanelInput_QueueCpuAdcChanges` turns that into records `{26 or 27, value, 0x7F}`.

**`AnalogIn_DebounceChange` — Noise/Debounce Filter (0xFC6F86):**

This routine filters encoder value changes to reject electrical noise and debounce mechanical jitter. It uses a 3-level threshold system:

| Absolute Delta | Action                                                                                                                                                                       | Status Bits                      |
|----------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------|
| ≤ 2            | **Noise rejection** — ignore change, clear debounce counter and pending bit                                                                                                  | Clear bits 0-2                   |
| 3-6            | **Two-reading confirm** — the first such reading sets the pending bit; a second consecutive one accepts the change (sets bit 3, clears bits 0-2). The counter is not changed | Set bit 2, then bit 3            |
| > 6            | **Spike filter** — if the debounce counter is 3 (bits 0-1), accept the change; otherwise increment the counter and clear the pending bit                                     | Set bit 3 (valid) when confirmed |

So a 3-6 change is taken on the second consecutive 3-6 reading, and a > 6 change on the fourth > 6 reading
since the counter was last cleared; only a ≤ 2 reading or an acceptance clears the counter. (Corrected
2026-11-02: this table used to say that a 3-6 reading increments the counter. Source: disassembly
`notes/open4-kn5000-b/cpanel/README.md`, "`AnalogIn_DebounceChange`, step by step", re-read from
`v10/maincpu/audio/audio_control_engine.s`.)

Status register bit definitions:
- **Bits 0-1:** Debounce counter (0-3, saturates at 3 → triggers bit 3)
- **Bit 2:** Debounce active flag (change detected, awaiting confirmation)
- **Bit 3:** Valid delta flag (checked and cleared by caller to accept the change)

**`AnalogIn_ReadAdcHigh` (0xFC6EA7):**

Returns, in L, the high byte of one of the main CPU's four A/D conversion result registers (`ld l, (xbc + 1)` with XBC = 0x120 / 0x122 / 0x124 / 0x126, the TMP94C241's `ADREG04L` / `ADREG15L` / `ADREG26L` / `ADREG37L`, for index 0-3). Channels 0 and 1, processed by the ID 2 and ID 5 handlers, are read from `ADREG04` and `ADREG15` (index 0 and 1):

| Channel | Base Address (decimal) | Register        |
|---------|------------------------|-----------------|
| 0       | 288 (0x120)            | `ADREG04` (SFR) |
| 1       | 290 (0x122)            | `ADREG15` (SFR) |
| 2       | 292 (0x124)            | `ADREG26` (SFR) |
| 3       | 294 (0x126)            | `ADREG37` (SFR) |

### MIDI Controller Output

The analog values reach the sound engine as panel records, not as MIDI controller numbers (2026-10-31, kn5000-3c7):

| Variable                        | Control          | Sent as                                   | Sender                                    |
|---------------------------------|------------------|-------------------------------------------|-------------------------------------------|
| `ANALOG_PITCHBEND_VALUE`        | pitch bend       | record `0xB1` (14-bit)                    | `Audio_SendPitchBendToParts`              |
| `ANALOG_MODULATION_VALUE`       | modulation       | record `0xB2`                             | `Audio_SendModulationToParts`             |
| `ANALOG_EXPRESSION_PEDAL_VALUE` | expression pedal | record `0xB0` +1, or `0xB3` per part      | `Audio_SendExpressionToParts`             |
| `ANALOG_AFTERTOUCH_VALUE`       | after touch      | record `0xB4` (parts with AFTER TOUCH on) | `Audio_SendAfterTouchToParts`             |
| `ANALOG_MAIN_VOLUME_VALUE`      | MAIN VOLUME      | record `0xB0` +0                          | `ExtData_Voice_CompareAndDispatch_Helper` |

`Audio_SendExpressionToParts` sends tag 179 only when `PANEL_FOOT_CONTROLLERS+2` = 183 and the part's `_PartExp`
bit (part +4 bit 5) is set; `Audio_SendAfterTouchToParts` writes tag 180 only for parts whose `_AfterTouch` bit
(part +12 bit 4) is set.

**Change Detection:**

The `*_PENDING` variants (e.g., `ANALOG_EXPRESSION_PEDAL_PENDING`) use bit 7 as a "value changed" flag:
- When an encoder/ADC value changes, bit 7 is set
- The MIDI output routine checks bit 7, sends the value if set, then clears bit 7
- This prevents redundant MIDI messages for unchanged values

**MIDI Message Format (at 0x9127-0x912A):**

| Address | Field | Example |
|---------|-------|---------|
| 0x9127 | Status byte | 0xB0 (Control Change, channel 0) |
| 0x9128 | Controller # | 0x01 (Modulation) |
| 0x9129 | Value | 0x00-0x7F |
| 0x912A | Velocity/Range | 0x7F |

In the source (since 2026-10-03): `MIDI_MSG_STATUS` / `MIDI_MSG_DATA1` / `MIDI_MSG_DATA2` / `MIDI_MSG_DATA3`
-- generic names, because the writers stage more than Control Change here (statuses 0xB0-0xB3 and word
stores of status + first data byte); v7 0x9C lower.

## 6. Memory Map

### Control Panel RAM Variables

| Address | Name                                 | Size     | Description                                                             |
|---------|--------------------------------------|----------|-------------------------------------------------------------------------|
| 0x8D8A  | `CPANEL_STATE_MACHINE_INDEX`         | byte     | Current serial state machine index (0-10)                               |
| 0x8D8B  | `CPANEL_PACKET_BYTE_COUNT`           | byte     | Byte count for multi-byte packets                                       |
| 0x8D8C  | `CPANEL_TX_RX_FLAGS`                 | byte     | Flags: bits 0,1,2,4,6,7 used                                            |
| 0x8D8E  | `PFCR_VALUE`                         | byte     | Shadow of Port F Control Register                                       |
| 0x8D8F  | `PFFC_VALUE`                         | byte     | Shadow of Port F Function Control                                       |
| 0x8D92  | `CPANEL_PROTOCOL_FLAGS`              | byte     | Flags: bits 0,1,2,3,6,7 used                                            |
| 0x8D93  | `CPANEL_PANEL_DETECT_FLAGS`          | byte     | Communication test results                                              |
| 0x8D94  | `CPANEL_RX_PACKET_BYTE_1`            | byte     | First byte of received packet                                           |
| 0x8D95  | `CPANEL_RX_PACKET_BYTE_2`            | byte     | Second byte of received packet                                          |
| 0x8D96  | `CPANEL_LAST_EVENT_VALUE`            | byte     | Changed button bits (XOR result)                                        |
| 0x8D97  | `CPANEL_COUNTER_DOWN_FROM_200`       | byte     | Ready check timeout counter                                             |
| 0x8D98  | `CPANEL_COUNTER_UP_TO_20`            | byte     | General counter                                                         |
| 0x8D9A  | `CPANEL_COUNTER_UP_TO_42`            | byte     | Main loop iteration counter                                             |
| 0x8D9B  | `TIMESTAMP_FOR_DELAY`                | word     | Timestamp for delay routines                                            |
| 0x8D9D  | `CPANEL_RX_READ_PTR`                 | word     | Backup of RX buffer position                                            |
| 0x8D9F  | `CPANEL_RX_WRITE_PTR`                | word     | Current RX buffer write position                                        |
| 0x8DA1  | `CPANEL_RX_RING_BUFFER`              | 92 bytes | Circular RX buffer                                                      |
| 0x8DFD  | `CPANEL_LED_READ_PTR`                | word     | LED TX buffer read pointer                                              |
| 0x8DFF  | `CPANEL_LED_WRITE_PTR`               | word     | LED TX buffer write pointer                                             |
| 0x8E01  | `CPANEL_LED_TX_BUFFER`               | 60 bytes | LED state TX buffer                                                     |
| 0x8E4A  | `STATE_OF_CPANEL_BUTTONS`            | 16 bytes | Button state (right panel)                                              |
| 0x8E5A  | `STATE_OF_CPANEL_BUTTONS_LEFT`       | 16 bytes | Button state (left panel)                                               |
| 0x8EE0  | `ANALOG_EXPRESSION_PEDAL_PENDING`    | byte     | Last expression-pedal value sent, bit 7 = send pending                  |
| 0x8EE2  | `ANALOG_MAIN_VOLUME_PENDING`         | byte     | Last MAIN VOLUME value sent, bit 7 = send pending                       |
| 0x8EE4  | `ANALOG_EXPRESSION_PEDAL_VALUE`      | byte     | Expression pedal (CPU AN0), 0..127                                      |
| 0x8EE6  | `ANALOG_MAIN_VOLUME_VALUE`           | byte     | MAIN VOLUME (CPL AD3, ID 27), 0..127                                    |
| 0x8EE8  | `ANALOG_PITCHBEND_VALUE`             | byte     | Pitch bend wheel (CPL AD1, ID 25), 0..255, centre 0x80                  |
| 0x8EEA  | `ANALOG_MODULATION_VALUE`            | byte     | Modulation wheel (CPL AD2, ID 26), 0..127                               |
| 0x8EF4  | `ANALOG_AFTERTOUCH_VALUE`            | byte     | After touch (CPU AN1), 0..127                                           |
| 0x8EFC  | `ADC_AN0_LAST_VALUE`                 | byte     | Last accepted ADREG04 high byte (expression pedal)                      |
| 0x8EFE  | `ADC_AN1_LAST_VALUE`                 | byte     | Last accepted ADREG15 high byte (after touch)                           |
| 0x8F04  | `ADC_AN0_STATUS`                     | byte     | AN0 debounce state (bit 3 = accepted)                                   |
| 0x8F06  | `ADC_AN1_STATUS`                     | byte     | AN1 debounce state (bit 3 = accepted)                                   |
| 0x8F10  | `ADC_AN0_OUTPUT`                     | 2 bytes  | Expression-pedal value + flags (bit 7 of +1 = queue event 26)           |
| 0x8F16  | `ADC_AN1_OUTPUT`                     | 2 bytes  | After-touch value + flags (bit 7 of +1 = queue event 27)                |
| 0x8F18  | `CPANEL_LED_IMAGE`                   | 16 bytes | Wanted pattern of LED rows 0..14 (`Protocol_values_for_LED_rows` order) |
| 0x8F28  | `CPANEL_LED_IMAGE_SENT`              | 16 bytes | LED rows as last sent (`CPanel_LED_FlushImage`)                         |
| 0x8F38  | `CPANEL_LEDS__ROW_AND_PATTERN_BYTES` | word     | Current LED row/pattern                                                 |

### Circular Buffer Parameters

| Buffer | Base Address | Size | Modulus | Notes |
|--------|--------------|------|---------|-------|
| `CPANEL_RX_RING_BUFFER` | 0x8DA1 | 92 bytes | 0x5C | RX from panels |
| `CPANEL_RX_EVENT_QUEUE` | 0x200AD | 128 bytes | 0x80 | Processed button/encoder events |
| `CPANEL_LED_EVENT_QUEUE` | 0x20137 | 128 bytes | 0x80 | LED command queue |

### Flag Definitions

#### CPANEL_TX_RX_FLAGS (0x8D8C)

| Bit | Usage                                                                                                    |
|-----|----------------------------------------------------------------------------------------------------------|
| 0   | RX in progress (set by `INTA_HANDLER`, cleared when the last reply byte arrives)                         |
| 1   | TX in progress (set by `CPanel_SendCommand`, `CPanel_SM_TXComplete` and `CPanel_InterruptPoll_MainLoop`) |
| 2   | Set by `CPanel_RX_ProcessWithFlag`, cleared by `CPanel_RX_Process`; never read                           |
| 4   | Never set.  `CPanel_RX_MultiBytePacket` would drop unchanged segments when it is set: dead code          |
| 6-7 | 2-bit counter (`add 0x40`); bit 6 set by `CPanel_InitHardware`                                           |

#### CPANEL_PROTOCOL_FLAGS (0x8D92)

| Bit        | Usage                                                                                              |
|------------|----------------------------------------------------------------------------------------------------|
| 0          | RX ring full: `CPanel_SM_RXByteN` does not advance the write pointer (read in `CPanel_SM_RXByteN`) |
| 1, 3, 6, 7 | Written (TX start, sync frame, INTA count-down, idle) and never read                               |
| 2          | Written only by unreachable code after `CPanel_SM_Idle`; never set at run time                     |

`CPanel_SM_RXByte1` sets bit 0 when fewer than 3 bytes of the ring are free and clears it otherwise; the init
and reset paths set it until the next frame header recomputes it.  The bit-2 writer is the unlabelled code right
after `CPanel_SM_Idle`'s `jrl` (0xFC47F1 in v10): no source label sits there and no copy of the address is in the
ROM (disassembly `notes/open4-kn5000-b/cpanel/probes/ref_scan.py`; the flag accesses were listed by
`probes/flag_access_scan.py`; tracker item kn5000-9ye).

#### CPANEL_PANEL_DETECT_FLAGS (0x8D93)

| Bit | Usage                                                               |
|-----|---------------------------------------------------------------------|
| 0   | Left panel responded to ping                                        |
| 3   | Right panel responded to ping (`CPanel_PanelDetection` ORs in 0x08) |

## 7. Code Reference

### Initialization Routines

| Address  | Name                      | Description                                                                      |
|----------|---------------------------|----------------------------------------------------------------------------------|
| 0xFC3EF5 | `CPanel_InitHardware`     | Main initialization sequence                                                     |
| 0xFC3FA9 | `CPanel_SendInitSequence` | Send init commands (1F 1A, 1D 00, DD 03, 1E 80)                                  |
| 0xFC4021 | `CPanel_SendFramePolled`  | Sends WA as one 2-byte frame on SC1 with polled timing (no caller in this build) |
| 0xFC42FB | `CPanel_InitButtonState`  | Initialize button state arrays                                                   |

### Command Send/Receive

| Address | Name | Description |
|---------|------|-------------|
| 0xFC4375 | `CPanel_WaitTXReady` | TX ready check with timeout |
| 0xFC43C7 | `CPanel_SendCommand` | Send 2-byte command (A=cmd, W=param) |
| 0xFC490E | `CPanel_RX_ProcessWithFlag` | Process RX with flag set |
| 0xFC4915 | `CPanel_RX_Process` | Process RX with flag clear |
| 0xFC491A | `CPanel_RX_DispatchLoop` | Initialize RX processing pointers |
| 0xFC492B | `CPanel_RX_ParseNext` | Main RX packet dispatch loop |

### Packet Handlers

| Address | Name | Description |
|---------|------|-------------|
| 0xFC4965 | `CPanel_RX_PacketHandlers` | 8-entry jump table for packet types |
| 0xFC4985 | `CPanel_RX_ButtonPacket` | Process button state packets |
| 0xFC49E0 | `CPanel_RX_EncoderPacket` | Process rotary encoder packets |
| 0xFC4A40 | `CPanel_RX_MultiBytePacket` | Process multi-byte packets |
| 0xFC4B10 | `CPanel_RX_SyncPacket` | Process sync/ACK packets |

### LED Transmission

| Address | Name | Description |
|---------|------|-------------|
| 0xFC4B2D | `CPanel_UpdateLEDs` | Main LED transmission routine |
| 0xFC4B85 | `CPanel_LED_PacketHandlers` | 4-entry jump table for LED types |

### Serial Interrupt Handlers

| Address | Name | Description |
|---------|------|-------------|
| 0xFC44B5 | `INTTX1_HANDLER` | Serial TX complete interrupt |
| 0xFC44D7 | `INTRX1_HANDLER` | Serial RX complete interrupt |
| 0xFC4489 | `CPANEL_STATE_MACHINE_TABLE` | Jump table for state machine |

### Helper Routines

| Address | Name | Description |
|---------|------|-------------|
| 0xFC4C08 | `CPanel_IncRXPtr` | Increment RX buffer pointer (modulo 92) |
| 0xFC4C13 | `CPanel_IncLEDPtr` | Increment LED buffer pointer (modulo 60) |
| 0xFC4C1E | `CPanel_IncEventPtr` | Increment event queue pointer (modulo 128) |
| 0xFC4C29 | `CPanel_DecEventPtr` | Decrement event queue pointer (modulo 128) |
| 0xFC6C5F | `CPanel_EncoderDispatch` | Dispatch to encoder-specific handler via jump table |

### Delay Routines

| Address | Name | Iterations/Ticks |
|---------|------|------------------|
| 0xFC40DE | `DELAY_2_LOOPS` | 2 |
| 0xFC40E9 | `DELAY_6_LOOPS` | 6 |
| 0xFC40F4 | `DELAY_10_LOOPS` | 10 |
| 0xFC4100 | `DELAY_300_LOOPS` | 300 |
| 0xFC410C | `DELAY_1500_LOOPS` | 1500 |
| 0xFC4118 | `DELAY_3000_LOOPS` | 3000 |
| 0xFC4124 | `DELAY_2_TICKS` | 2 system ticks |
| 0xFC4139 | `DELAY_6_TICKS` | 6 system ticks |
| 0xFC414E | `DELAY_51_TICKS` | 51 system ticks |

### Button Detection

| Address | Name | Description |
|---------|------|-------------|
| 0xFC3EE5 | `CPanel_ScanButtons` | Main button scan entry point |
| 0xFC41FC | `CPanel_ReadAllButtons` | Read button states from both panels |
| 0xFC4165 | `CPanel_CheckSpecialCombos` | Check for special button combinations |
| 0xFC426A | `CPanel_PollStartup` | Poll buttons during startup |
| 0xFC4293 | `CPanel_ButtonPollLoop` | Button polling loop |
| 0xFC42B7 | `CPanel_EncoderCheck` | Check encoder state |
| 0xFC480F | `CPanel_InterruptPoll_MainLoop` | Interrupt-driven poll + LED update cycle |

## 8. MAME Serial Bugs (Found and Fixed)

The following bugs in MAME's TMP94C241 serial emulation were discovered and fixed during control panel HLE development. All fixes are compatible with the original KN5000 firmware.

| Bug                              | Root Cause                                                                         | Fix                                                                                                                                                                                                          |
|----------------------------------|------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Timer stops early**            | `timer_callback` only checked `m_tx_clock_count`, missing final rising edge for RX | Add `m_rx_clock_count != 8` condition                                                                                                                                                                        |
| **Queue byte corrupts last bit** | Loading next TX byte pre-output bit 0, overwriting bit 7 of previous byte          | Use `tx_clock_count = 8`, defer bit 0 to next falling edge                                                                                                                                                   |
| **Rising-edge race**             | CPU's `sioclk()` forwarded clock to cpanel before sampling `m_rxd`                 | Capture `m_rxd` before forwarding clock                                                                                                                                                                      |
| **SCLK ignores PFFC**            | Clock edges forwarded to cpanel even when PFFC disabled the pin                    | First gated `sclk_out_cb` on PFFC, which desynchronised the clock; superseded: SCLK is always forwarded and the PFFC state reaches the panel as the `tx_start` argument, so the panel discards phantom bytes |
| **TO2 checks wrong IOC bit**     | `BIT(m_serial_control, 1)` checked SCLKS instead of IOC (bit 0)                    | `BIT(m_serial_control, 0)`                                                                                                                                                                                   |
| **SC1MOD gate kills firmware**   | Gating `timer_callback` on `SC1MOD!=1` disabled the 250 kHz clock                  | Gate on `(SC1MOD & 3)==0 && IOC==1` only                                                                                                                                                                     |
| **TO2 prevents idle detect**     | Continuous TO2 at 12.5 kHz prevented cpanel idle detection (250 µs)                | Gate TO2_trigger on TX/RX activity                                                                                                                                                                           |
| **Missing INTRX1 interrupt**     | RX byte received but INTRX1 flag never set in compiled binary                      | Code existed in source, needed rebuild                                                                                                                                                                       |
| **Wrong header encoding**        | Left panel used `0x40\|segment` (bits 7:6=01, dead zone)                           | Changed to `0xC0\|segment` (bits 7:6=11)                                                                                                                                                                     |
| **Ghost button toggles**         | MAME input ports return momentary single-bit glitches                              | Per-segment confirmation (2 consecutive scans)                                                                                                                                                               |

See also: [Serial Firmware Compatibility]({{ site.baseurl }}/serial-firmware-compatibility/) for what the emulation must provide, and [Control-Panel Serial Timing]({{ site.baseurl }}/serial-debugging/) for the line-level rules these fixes implement.

## 9. Protocol Gaps (What We Don't Know)

### LED Packet Format

The LED handler uses bits 4-5 of the first byte to dispatch to one of 4 handlers via `CPanel_LED_PacketHandlers` (0xFC4B85): types 0-2 copy a 2-byte {row, pattern} pair; type 3 copies the header byte plus `(byte & 0x0F) + 2` more, `(byte & 0x0F) + 3` bytes in all (see "LED Packet Handlers" below).

### Multi-byte Packet Purpose (Types 6, 7) (RESOLVED)

**Type 6/7 frame** (`CPanel_RX_MultiBytePacket`, sized by `CPanel_SM_RXByte1`; tracker item kn5000-9ye, 2026-10-31):

| byte       | bits | meaning                                                                                  |
|------------|------|------------------------------------------------------------------------------------------|
| H0         | 7:6  | panel select, as in a button frame (00 right, 11 left)                                   |
| H0         | 5:4  | `11` (type 6 or 7)                                                                       |
| H0         | 3:0  | N - 1: N = 1..16 data bytes.  Bit 3 is also the low type bit, so type 7 = a run of 9..16 |
| H1         | 4:0  | first segment (bit 4 clear) or first controller id (bit 4 set); bits 7:5 ignored         |
| D0..D(N-1) | 7:0  | state of segment / id H1 + i                                                             |

`CPanel_SM_RXByte1` expects `(H0 & 0x0F) + 3` bytes when `(H0 & 0x3F) >= 0x30`, otherwise 2.  The parser waits
until all N + 2 bytes are in the ring.  It writes one 3-byte record per data byte:
`{(H0 & 0xC0) | (H1 + i), value, changed}`.

- Segment bytes are exchanged into `STATE_OF_CPANEL_BUTTONS` (0x8E4A + segment, + 0x10 for the left panel), with
  `changed = old ^ new`: the same as `CPanel_RX_ButtonPacket` does for a single segment.
- Controller bytes go through `CPanel_EncoderDispatch`, with `changed = 0xFF`.  There is no record when the
  handler returns 0xFFFF.

So one type 6/7 frame can carry up to 16 segments of one panel.  [INFERENCE] This is the reply format of the
`2B 00` / `EB 00` start-up requests, which ask for every segment at once; no capture of a real panel exists to
confirm it.  `CPANEL_TX_RX_FLAGS` bit 4, which would make the parser drop unchanged segments, is never set (see
[Flag Definitions](#flag-definitions)), so every segment of a multi-segment frame is queued, changed or not.

### ~~Button-to-Segment Mapping~~ (RESOLVED)

**Complete button mapping now documented** - see "Button State Reporting Format" section above.
- 11 segments per panel (CPR_SEG0-10 and CPL_SEG0-10)
- Each segment holds 8 button states
- Full mapping extracted from MAME INPUT_PORTS definitions

### ~~LED Row Mapping~~ (RESOLVED)

**Complete LED mapping now documented** - see "LED Control Interface" section above.
- Right panel: rows 0x00-0x0C
- Left panel: rows 0xC0-0xC8
- The same mapping is in MAME's `kn5000_cpanel_device::process_led_command()` (`kn5000_cpanel.cpp`)

**Button → LED map (firmware side).** `PanelButton_LedMap` (352 bytes in the program ROM, 0xEB7E8C in v10) gives,
for each of the 22 panel input segments and each of its 8 button bits, the `{LED row, LED pattern}` that
`EffectMode_MidiSetLEDs` passes to `Set_LEDs`: the pattern while the button is down, 0 when released. The row
indexes `Protocol_values_for_LED_rows` (0-5 left panel 0xC0-0xC8, 6-14 right panel 0x00-0x0C). Buttons without an
LED of their own hold `{0x0E, 0x0F}`, which is row 14, the four START/STOP beat LEDs. Source:
`scripts/converters/panel_led_map_retype.py` in the disassembly repository.

### Encoder Physical Mapping (RESOLVED)

Six encoder IDs have dedicated handlers (the five analog IDs carry **absolute 8-bit ADC values**; ID 31 carries the data wheel's signed detent count):
- **ID 2**: expression pedal, main-CPU A/D channel 0 (AN0, `EXP`; posts TOTAL EXPRESSION or part expression by key 0x2880) → `ANALOG_EXPRESSION_PEDAL_VALUE` (inverted, /2, 128-entry LUT)
- **ID 5**: after-touch sensor, main-CPU A/D channel 1 (AN1, `AFT`; channel pressure) → `ANALOG_AFTERTOUCH_VALUE` (256-entry LUT, threshold and curve)
- **ID 25**: pitch-bend wheel (event 0xB1, MIDI pitch bend) → `ANALOG_PITCHBEND_VALUE` (inverted, mode-dependent scaling)
- **ID 26**: modulation wheel (event 0xB2, CC 1) → `ANALOG_MODULATION_VALUE` (/2, LUT)
- **ID 27**: MAIN VOLUME slider, CPL AD3 (event 0xB0, record byte +0) → `ANALOG_MAIN_VOLUME_VALUE` (inverted, /2, LUT)
- **ID 31**: TEMPO/PROGRAM data wheel (header `0xD7`), signed detent count passed through unchanged

Physical assignments from the schematics and from the events each record posts (see [Analog controllers](#analog-controller--encoder-format), corrected 2026-10-31, tracker item kn5000-3c7; the earlier breath / foot / expression / volume reading came from the handlers' old names, since renamed). Remaining IDs (0-1, 3-4, 6-24, 28-30) return 1 (unused).

**Data wheel (jog dial)**: ROTA/ROTB quadrature on the CPL MCU. The panel reports `[0xD7, signed detent count]`, a Type 2 frame with encoder ID 31 (`Encoder_PassthroughIdentity`, which passes the count through). The count becomes record 0x19 and then `EVT_DIAL` (0x1C0001F); see [Data Wheel]({{ site.baseurl }}/data-wheel-investigation/).

### Baud Rate Transitions

The serial channel switches rate inside every command, not between phases: `CPanel_SendCommand` arms at 31.25 kHz (BR1CR=0x28), the phantom/turnaround states run at 62.5 kHz (0x24), and the two real bytes at 250 kHz (0x14). See [Serial Firmware Compatibility]({{ site.baseurl }}/serial-firmware-compatibility/) for the state-by-state sequence.

### LED Packet Handlers (Fully Disassembled)

| Address  | Label                    | Size     | Description                                                                                                          |
|----------|--------------------------|----------|----------------------------------------------------------------------------------------------------------------------|
| 0xFC4B95 | CPanel_LED_HandlePacket2 | 48 bytes | Types 0-2: transfers 2 bytes (row select + pattern) from event queue to LED TX buffer                                |
| 0xFC4BC5 | CPanel_LED_HandlePacketN | 66 bytes | Type 3: transfers variable-length data; the header's lower nibble n gives n + 3 bytes in all (the header plus n + 2) |

Both handlers are dispatched from CPanel_UpdateLEDs via a 4-entry jump table at 0xFC4B85.
After transferring data, both jump back to CPanel_UpdateLEDs to check for more pending events.

### ~~Remaining Undisassembled Routines~~ (RESOLVED)

All control panel routines have been fully disassembled. The routine at 0xFC4C34 is `ToneGen_IncrementWrap128` in `audio/tonegen_fileio_handlers.s` — a circular queue pointer increment/wrap utility (wraps at 128) used by the LED packet handlers. Encoder handlers (0xFC6C80-0xFC6E41) have also been fully disassembled.

## 10. Configuration Switches

### Main CPU Checking Device (CN11)

| Setting | Value | Effect |
|---------|-------|--------|
| On | 0x00 | Enable diagnostic mode |
| Off | 0x01 | Normal operation (default) |

### Sub CPU Checking Device (CN12)

| Setting | Value | Effect |
|---------|-------|--------|
| On | 0x00 | Enable diagnostic mode |
| Off | 0x01 | Normal operation (default) |

### Computer Interface Selection (COM_SELECT)

Read from main CPU Port Z bits 4-7:

| Value | Selection |
|-------|-----------|
| 0xE0 | MIDI |
| 0xD0 | PC1 |
| 0xB0 | PC2 |
| 0x70 | Mac |

### Area Selection

Read from main CPU Port H:

| Value | Regions |
|-------|---------|
| 0x02 | Thailand, Indonesia, Iran, U.A.E., Panama, Argentina, Peru, Brazil |
| 0x04 | USA, Mexico |
| 0x06 | All other regions (default) |

**Complete region list (from service documentation):**

| Code | Region |
|------|--------|
| (M) | U.S.A. |
| (MC) | Canada |
| (XM) | Mexico |
| (EN) | Norway, Sweden, Denmark, Finland |
| (EH) | Holland, Belgium |
| (EF) | France, Italy |
| (EZ) | Germany |
| (EW) | Switzerland |
| (EA) | Austria |
| (EP) | Spain, Portugal, Greece, South Africa |
| (EK) | United Kingdom |
| (XL) | New Zealand |
| (XR) | Australia |
| (XS) | Malaysia |
| (MD) | Saudi Arabia, Hong Kong, Kuwait |
| (XT) | Taiwan |
| (X) | Thailand, Indonesia, Iran, U.A.E., Panama, Argentina, Peru, Brazil |
| (XP) | Philippines |
| (XW) | Singapore |

## 11. DEMO Button Code Path (Case Study)

This section traces what happens when the DEMO button is pressed: the panel event selects the demo mode, and the mode change then sends `EVT_ACTIVATE_STATE` to `DemoModeFunc`.

### Button Press Detection

When DEMO is pressed (CPL_SEG3, bit 0):

```
Hardware interrupt (serial RX)
    ↓
CPanel_RX_ButtonPacket (0xFC4985)
    - Reads segment byte (3) and button state (bit 0)
    - XORs new state with previous to detect change
    - Queues event to CPANEL_RX_EVENT_QUEUE
```

### Event Queue

- **Location:** `CPANEL_RX_EVENT_QUEUE` (0x000200AD)
- **Size:** 128 bytes circular buffer
- **Content:** 3-byte records `{header byte, new state, changed bits}`

### Application Event Dispatch

```
CtrlPanel_HandlePortCommands (0xF98314)
    - panel payload 0x20 (a mode key) → ApPostEvent(EVT_SW_IN_MODE, mode)
    ↓
GroupBoxProc (0xF9983F) → GroupBox_HandleStateCompare (0xF99E57)
    - EVT_SW_IN_MODE becomes EVT_CHANGE_MODE
    ↓
GroupBox_HandlePartChange (0xF99961), the EVT_CHANGE_MODE case
    - SendEvent(old mode, EVT_ACTIVATE_STATE, 1)   phase 1 = mode deactivated
    - SendEvent(new mode, EVT_ACTIVATE_STATE, 0)   phase 0 = mode activated
    ↓
DemoModeFunc (0xF222CC), the MD_DEMO mode's MainFunction (NAKA_MAINFUNC_DemoModeFunc)
```

### Event Code `0x01c00013` Is `EVT_ACTIVATE_STATE`, Not a Button Event

`0x01C00013` is the firmware's `EV_ACTIVATE`, named `EVT_ACTIVATE_STATE` in the disassembly
(`shared/event_codes.s`): an activation-state notice that the UI sends to a mode or title object. It
encodes no panel segment and no handler index. Its parameter, in XDE, is a phase: 0 = mode activated,
1 = mode deactivated, 2-7 are title phases and 8 = switch complete. The DEMO button itself is CPL
segment 3 bit 0, whose action `{0xA9, 0x20}` goes to `PanelButton_ModeKey` (see
[From a button change to an action](#from-a-button-change-to-an-action-2026-10-06)).

### DemoModeFunc Handler (0xF222CC)

```asm
DemoModeFunc:
    CP XBC, 01c00013h        ; EVT_ACTIVATE_STATE?
    JR NZ, DemoModeFunc_Exit      ; Any other event? Exit
    CP XDE, 00000001h        ; Phase 1 = mode deactivated?
    JR Z, DemoModeFunc_Initialize       ; Deactivated → call DemoMode_Initialize
    OR XDE, XDE              ; Phase 0 = mode activated?
    JR NZ, DemoModeFunc_Exit      ; Any other phase? Exit
    ; Mode activated (XDE=0) → call DemoMode_Main_Operation
    CALL DemoMode_Main_Operation        ; Demo mode entry routine
```

### Key Addresses

| Component                      | Address    | Purpose                                                                                      |
|--------------------------------|------------|----------------------------------------------------------------------------------------------|
| `CPanel_RX_ButtonPacket`       | 0xFC4985   | Packet parsing, XOR change detection                                                         |
| `CPANEL_RX_EVENT_QUEUE`        | 0x000200AD | Event queue buffer                                                                           |
| `CtrlPanel_HandlePortCommands` | 0xF98314   | Turns the mode-key panel event (payload 0x20) into `EVT_SW_IN_MODE`                          |
| `GroupBox_HandlePartChange`    | 0xF99961   | `GroupBoxProc`'s `EVT_CHANGE_MODE` case: sends `EVT_ACTIVATE_STATE` to the old and new modes |
| `DemoModeFunc`                 | 0xF222CC   | Demo mode's EVT_ACTIVATE_STATE handler                                                       |
| `DemoMode_Main_Operation`      | 0xF8696F   | Demo mode entry (EVT_ACTIVATE_STATE phase 0, mode activated)                                 |
| `DemoMode_Initialize`          | 0xF869E3   | Called on EVT_ACTIVATE_STATE phase 1 (mode deactivated)                                      |

### Complete Call Chain

```
Hardware interrupt (serial RX)
    ↓
CPanel_RX_Process
    ↓
CPanel_RX_ParseNext (0xFC492B)
    ↓
CPanel_RX_ButtonPacket (0xFC4985)
    ├─ Read packet byte 1 (segment)
    ├─ Read packet byte 2 (button state)
    ├─ XOR with previous state → changed bits
    └─ Queue event to CPANEL_RX_EVENT_QUEUE
    ↓
PanelButton_ModeKey (DEMO's action {0xA9, 0x20})
    └─ PanelEvent_Post: panel event {0xA9, 0x20, mode code}
    ↓
CtrlPanel_HandlePortCommands (0xF98314)
    └─ panel payload 0x20 → ApPostEvent(EVT_SW_IN_MODE, mode)
    ↓
GroupBox_HandleStateCompare (0xF99E57), GroupBoxProc's EVT_SW_IN_MODE case
    └─ EVT_CHANGE_MODE
    ↓
GroupBox_HandlePartChange (0xF99961), GroupBoxProc's EVT_CHANGE_MODE case
    ├─ SendEvent(old mode, EVT_ACTIVATE_STATE, 1) - mode deactivated
    └─ SendEvent(new mode, EVT_ACTIVATE_STATE, 0) - mode activated
    ↓
DemoModeFunc (0xF222CC)
    ├─ CP XBC, 01c00013h  ← EVT_ACTIVATE_STATE?
    └─ Execute action based on XDE (the phase: 0 = mode activated, 1 = mode deactivated)
```

## References

- **Firmware Disassembly**: [kn5000-roms-disasm](https://github.com/ArqueologiaDigital/technics-roms-disasm) — `v10/maincpu/ui/cpanel_routines.s` (also in v9/ and v7/)
- **MAME Driver Source**: `src/mame/matsushita/kn5000_cpanel.cpp` (HLE), `kn5000.cpp` (wiring), in mainline MAME since [#15143](https://github.com/mamedev/mame/pull/15143) (control-panel HLE) and [#15919](https://github.com/mamedev/mame/pull/15919) (data wheel)
- **CPU Serial Emulation**: `src/devices/cpu/tlcs900/tmp94c241_serial.cpp`
- **Hardware Architecture**: [Hardware Architecture Page]({{ site.baseurl }}/hardware-architecture/)
- **Serial Debugging**: [Serial Firmware Compatibility]({{ site.baseurl }}/serial-firmware-compatibility/)
- **Service Manual**: EMID971655 A5 (Schematics II-9 through II-38)
