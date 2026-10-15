---
layout: page
title: Audio Subsystem
permalink: /audio-subsystem/
---

# Audio Subsystem

The KN5000 audio subsystem handles all sound generation, processing, and output. The Sub CPU runs dedicated audio firmware that processes MIDI-like commands from the Main CPU and drives the DSP and DAC hardware.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      MAIN CPU (TMP94C241F)                          │
│                                                                     │
│  Audio_Lock_Acquire ──> Audio_DMA_Transfer ──> Audio_Lock_Release   │
│                                 │                                   │
│              Latch @ 0x140000 (Inter-CPU Communication)             │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  v
┌───────────────────────────────────────────────────────────────────────┐
│                       SUB CPU (TMP94C241F)                            │
│                                                                       │
│  Boot ROM: 128KB @ 0xFE0000      Payload: 192KB (from Main CPU)       │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │                  AUDIO PROCESSING LOOP                         │   │
│  │                                                                │   │
│  │  ToneGen_Process_Notes ──> MIDI_Dispatch ──> Audio_Process_DSP │   │
│  │         │                       │                    │         │   │
│  │         v                       v                    v         │   │
│  │   [Keyboard Input]        [Ring Buffer]         [DSP State]    │   │
│  │      @ 0x110000             @ 0x2B0D             @ 0x3B60      │   │
│  └────────────────────────────────────────────────────────────────┘   │
└──────────┬─────────────────────┬─────────────────────┬────────────────┘
           │                     │                     │
      [0x100000]             [IC310 SO]           [0x130000]
       Register               serial                  DSP
        Config                 audio                Config
           │                     │                     │
           v                     v                     v
  ┌─────────────────┐   ┌─────────────────┐   ┌──────────────────┐
  │  TONE GENERATOR │   │   DAC (IC313)   │   │   DUAL DSP       │
  │  IC303          │   │   PCM69AU       │   │   IC310 + IC311  │
  │                 │   │                 │   │                  │
  │  64 voices      │   │  18-bit stereo  │   │  4 channels      │
  │  32 regs each   │   │  (via serial)   │   │  0x20 bytes/ch   │
  └────────┬────────┘   └────────┬────────┘   └──────────────────┘
           │                     │
       [0x110000]          [BCK/SDOR/SDOF]
     Keyboard Input        Serial Audio Bus
```

## Hardware Addresses

| Component | Address | Description |
|-----------|---------|-------------|
| Tone Gen Registers | 0x100000/0x100002 | Register-indirect config (64 voices, addr/data) |
| Tone Gen Keyboard | 0x110000/0x110002 | Voice events (status + note/velocity data) |
| Inter-CPU Latch | 0x120000 | Bidirectional data register |
| DSP Registers | 0x130000/0x130002 | Register-indirect config (4 channels, addr/data) |
| HDAE5000 PPI | 0x160000 | Parallel port interface (expansion) |

See [Tone Generator]({{ site.baseurl }}/tone-generator/) for the complete register map and chip inventory, and [Effects DSP (NEC uPD6383GF)]({{ site.baseurl }}/effects-dsp/) for the IC311 effects processor's architecture, instruction word, decoded algorithms and the full 50-effect parameter catalogue.

### DSP Port I/O Control (Sub CPU Internal Ports)

The dual DSP chips are controlled via the Sub CPU's internal I/O ports. DSP1 (IC311, uPD6383GF-3BA) uses a parallel bus protocol with Port PZ/P7 for command/data handshake. DSP2 (IC310, MN19413) uses GPIO bit-bang serial on Port F. Both share chip-select lines:

| Port | Bit | Signal | Function |
|------|-----|--------|----------|
| 0x1C (P7) | 6 | DSPCD | Command/Data select (0=command, 1=data) |
| 0x1C (P7) | 5 | DSP1_CS | DSP1 chip select (active low) |
| 0x1C (P7) | 4 | RD | Read strobe (active low) |
| 0x1C (P7) | 3 | WR | Write strobe (active low) |
| 0x38 (PE) | 6 | DSP2_CS | DSP2 chip select (active low) |
| 0x38 (PE) | 0 | MUTE | Audio mute control |
| 0x44 (PH) | 2 | DSP2_RST | DSP2 reset (active low) |
| 0x44 (PH) | 1 | DSP1_RST | DSP1 reset (active low) |
| 0x44 (PH) | 0 | DSP_RDY | DSP ready/status (read) |
| 0x68 (PZ) | 7:0 | DATA | 8-bit data port (command/data bytes) |

**Write Protocol (command or data byte):**

```
1. Deassert RD and WR (both high)
2. Select chip: assert DSP1_CS or DSP2_CS (drive low)
3. Poll DSP_RDY until ready (timeout: 8000 iterations)
4. Set DSPCD: 0 for command byte, 1 for data byte
5. Assert WR (drive low)
6. Write byte to PZ (port 0x68)
7. Deassert WR (drive high)
8. Deselect chip: deassert CS
9. Set DSPCD back to data mode (1)
```

**Key Low-Level Functions:**

| Function               | Address  | Description                                  |
|------------------------|----------|----------------------------------------------|
| `DSP1_Assert_Reset`    | 0x038396 | Reset DSP1 (clear PH.1)                      |
| `DSP1_Deassert_Reset`  | 0x03839A | Release DSP1 reset (set PH.1)                |
| `DSP2_Assert_Reset`    | 0x03839E | Reset DSP2 (clear PH.2)                      |
| `DSP2_Deassert_Reset`  | 0x0383A2 | Release DSP2 reset (set PH.2)                |
| `DSP_Set_Command_Mode` | 0x0383A7 | DSPCD=0 (command register)                   |
| `DSP_Set_Data_Mode`    | 0x0383AB | DSPCD=1 (data register)                      |
| `DSP_Select_Chip`      | 0x0383BF | Assert CS for chip 0 or 1                    |
| `DSP_Deselect_Chip`    | 0x0383DB | Deassert CS                                  |
| `DSP_Read_Status`      | 0x0383F7 | Read ready bit from PH.0                     |
| `DSP_Send_Command`     | 0x036331 | Full command byte write (with polling)       |
| `DSP_Send_Data`        | 0x0367EE | Full data byte write (with polling)          |
| `DSP2_Send_Command`    | 0x03666B | DSP2-specific command write                  |
| `DSP2_Send_Data`       | 0x0368BA | DSP2-specific data write                     |
| `DSP_DispatchCommand`  | 0x036A2E | Route command to DSP1 or DSP2                |
| `DSP_DispatchData`     | 0x036A4F | Route data to DSP1 or DSP2                   |
| `DSP_WriteParamWord`   | 0x038405 | Write 16-bit parameter (high byte, low byte) |

### DSP Channel Register Map (Memory-Mapped at 0x130000)

⚠ **Which chip actually decodes this block is UNCERTAIN, and it is confirmed NOT the
uPD6383GF's own command/data port** (that is the Port PZ/P7 parallel handshake described
above). MAME's driver maps 0x130000 to IC311 as a board-level convenience while explicitly
recording that this is not the DSP's host interface; the boot ROM itself named it
`TONE_GEN_BASE`, but it is also confirmed **not** the tone generator (no access to it is
bracketed by the tone generator's P6.7 select strobe, unlike every genuine tone-generator
write). Treat "DSP Channel Register Map" below as a working label for a real, distinct
4-channel register block whose owning chip has not been identified — not as a second path
into the same registers IC311 exposes over the parallel bus.

The memory-mapped interface at 0x130000 provides a second access path to DSP-*related*
registers, used for channel initialization:

```
Channel register address = channel_number × 0x20 + 0x10

Channel 0: registers 0x10-0x17 (8 bytes)
Channel 1: registers 0x30-0x37
Channel 2: registers 0x50-0x57
Channel 3: registers 0x70-0x77

Write sequence:
  (0x130000) ← register address byte
  (0x130002) ← register data byte
```

Initialization writes test pattern 0x5A5A5A5A to all 4 channels, then sets initial config value 0x101001F with 0x20 channel spacing.

## Sub CPU Audio Processing

### Main Loop

The Sub CPU runs a continuous audio processing loop in the payload firmware:

```
Audio_System_Init:
    CALL InterCPU_Latch_Setup     ; Configure DMA channels
    CALL DSP_System_Init          ; Clear DSP state buffers
    CALL DSP2_Init                ; Initialize second DSP
    CALL DSP_Init_Channels        ; Configure 4 DSP channels
    CALL ToneGen_Init             ; Keybed init (touch curve 6), power-on key scan

Main_Loop:
    CALL ToneGen_Process_Notes    ; Read keyboard input
    CALL MIDI_Dispatch            ; Process MIDI commands
    CALL Audio_Process_DSP        ; Update DSP state
    CALL Audio_Process_Final      ; Final audio update
    JR Main_Loop
```

### Command Dispatch Table

Commands from the Main CPU are dispatched based on the upper 3 bits:

| Cmd Range | Handler | Purpose |
|-----------|---------|---------|
| 0x00-0x1F | `Audio_CmdHandler_00_1F` | DSP/audio control - writes to ring buffer |
| 0x20-0x3F | `Audio_CmdHandler_20_3F` | Extended audio control |
| 0x40-0x5F | `Audio_CmdHandler_40_5F` | Audio parameters |
| 0x60-0x7F | `Audio_CmdHandler_60_7F` | Voice/DSP configuration |
| 0x80-0x9F | (Serial port setup) | 38400 baud configuration |
| 0xA0-0xBF | `Audio_CmdHandler_A0_BF` | System audio commands |
| 0xC0-0xFF | `Audio_CmdHandler_C0_FF` | Extended system commands |

### Ring Buffer

Audio commands use a 4KB circular ring buffer:

| Variable | Address | Description |
|----------|---------|-------------|
| Write Pointer | 0x2B0D | 12-bit circular index |
| Read Pointer | 0x2B0F | Current read position |
| Byte Count | 0x2B11 | Bytes available |
| Base Address | 0x2B13 | Buffer start |

**Key Routines:**
- `RingBuf_ReadByte` - Read single byte (returns 0xFFFF if empty)
- `RingBuf_SkipToEnd` - Skip remaining bytes in current message

## MIDI Message Processing

The `MIDI_Dispatch` routine parses MIDI-like status bytes and routes to handlers:

| Status | Handler | Voice Handler | Description |
|--------|---------|---------------|-------------|
| 0x80/0x90 | `MIDI_Status_NoteOn` | `Voice_NoteOn` | Note On/Off (velocity 0 = off) |
| 0xB0 | `MIDI_Status_CtrlChange` | `Voice_CtrlChange` | Control Change |
| 0xC0 | `MIDI_Status_ProgChange` | `Voice_ProgChange` | Program Change |
| 0xD0 | `MIDI_Status_ChanPressure` | `Voice_ChanPressure` | Channel Aftertouch |
| 0xE0 | `MIDI_Status_PitchBend` | `Voice_PitchBend` | Pitch Bend |
| 0xF0 | `MIDI_Status_System` | `Voice_SystemMsg` | System messages |

### Control Change Sub-handlers

The `Voice_CtrlChange` handler supports these controllers:

| CC#       | Handler                                    | Parameter                                                                                         |
|-----------|--------------------------------------------|---------------------------------------------------------------------------------------------------|
| 0x01      | `Voice_CC_ModWheel`                        | Modulation Wheel                                                                                  |
| 0x07      | `Voice_CC_Volume`                          | Main Volume                                                                                       |
| 0x0A      | `Voice_CC_Pan`                             | Pan/Balance                                                                                       |
| 0x0B      | `Voice_CC_Expression`                      | Expression                                                                                        |
| 0x40      | `Voice_CC_Sustain`                         | Sustain Pedal                                                                                     |
| 0x5B      | `Voice_CC_Sostenuto`                       | Sostenuto Pedal                                                                                   |
| 0x5D      | `Voice_CC_Soft`                            | Soft Pedal                                                                                        |
| 0x5E      | `Voice_CC_Portamento`                      | Portamento                                                                                        |
| 0x91      | `Voice_CC_91` → `Voice_CC_SetReverbDepth`  | Reverb depth (label; see Proprietary Control Changes)                                             |
| 0x95      | `Voice_CC_95` → `Voice_CC_SetChorusEnable` | Chorus on/off (label)                                                                             |
| 0x97-0x9D | `Voice_CC_97`-`Voice_CC_9D`                | Chorus depth, delay depth, delay on/off, delay feedback (labels; see Proprietary Control Changes) |

## DSP Configuration

### Dual DSP Architecture

The Sub CPU controls two DSP chips:

- **DSP1**: Primary sound synthesis (initialized by `DSP_System_Init`)
- **DSP2**: Additional processing (initialized by `DSP2_Init`)

### DSP State Buffers

| Buffer           | Address     | Size       | Purpose                                                  |
|------------------|-------------|------------|----------------------------------------------------------|
| DSP State 1      | 0x041342    | 38 bytes   | Primary DSP state                                        |
| DSP State 2      | 0x041368    | 7462 bytes | Per-part records (26 × 287 B)                            |
| DSP Config       | 0x045310-18 | 12 bytes   | Configuration parameters                                 |
| DSP Ring Buffer  | 0x3B60-64   | 6 bytes    | Command ring buffer for DSP                              |
| EFF Slot Active  | 0x4930      | 10 bytes   | Per-slot active word (5 words), tested by `EFF_MuteLoop` |
| EFF State        | 0x4940      | variable   | Per-EFF dirty/change flags                               |
| EFF Params       | 0x4944      | variable   | Per-EFF parameter dirty flags                            |
| Argo Change Flag | 0x493E      | 2 bytes    | Algorithm/routing change pending                         |
| EFF Slot→Chip    | 0x1ED6D     | 5 bytes    | Chip of each effect slot (00 00 01 01 01, ROM constant)  |

### DSP Channel Configuration

Each of the 4 DSP channels has 0x20 bytes of register space at 0x130000:

```
Channel 0: 0x130000 - 0x13001F
Channel 1: 0x130020 - 0x13003F
Channel 2: 0x130040 - 0x13005F
Channel 3: 0x130060 - 0x13007F
```

**Key Routines:**
- `DSP_Init_Channels` - Initialize all 4 channels with test pattern
- `DSP_Write_Channel` - Write 8 bytes of config to a channel (loop)
- `DSP_WriteAllChannelRegs` - Write register data to all 4 channels
- `DSP_WriteChannelRegs_Inner` - Write 8 sequential registers to one channel
- `DSP_Send_Command` - Send command byte to DSP
- `DSP_Send_Data` - Send data byte to DSP

### DSP Voice Coefficient Routing

The Sub CPU firmware includes a coefficient routing subsystem that maps voice parameters to DSP coefficient buffers. This system sits between the voice parameter tables and the DSP hardware, computing which coefficient set to apply based on voice allocation and routing type.

**Memory Layout:**

| Address  | Size       | Purpose                                                      |
|----------|------------|--------------------------------------------------------------|
| 0x041368 | 7462 bytes | Per-part records (26 parts × 287 bytes)                      |
| 0x045210 | variable   | DSP coefficient output buffer (written by routing functions) |
| 0x045310 | 4 bytes    | Base pointer for routing table computation                   |
| 0x045314 | 4 bytes    | Pointer to routing configuration structure                   |

The routing configuration structure (pointed to by 0x045314) contains pointers to coefficient source tables at various offsets:

| Offset | Purpose |
|--------|---------|
| +0x44 | Type-A coefficient table (group 0, default) |
| +0x48 | Type-A coefficient table (group 2, 128-191) |
| +0x4C | Type-A coefficient table (group 1, 64-127) |
| +0x50 | Type-A output pointer table |
| +0x54 | Algorithm coefficient table (default) |
| +0x58 | Type-B coefficient table (group 0, default) |
| +0x5C | Type-B coefficient table (group 2) |
| +0x60 | Type-B coefficient table (group 1) |
| +0x64 | Type-B output pointer table |
| +0x70 | Algorithm table (type 1) |
| +0x7C | Algorithm table (type 2) |
| +0x80-0x98 | Extended algorithm tables (types 3-4) |

**Routing Algorithm:**

The routing functions share a common pattern:

1. **Extract parameters**: Mask voice number to 7 bits, extract channel (low 4 bits of BC) and type (bits 6-7 of BC)
2. **Type dispatch**: 4-way branch based on type bits (0/64/128/192) to select coefficient source table
3. **Compute index**: `index = (channel << 7 + voice) × 2`, used as offset into the selected table
4. **Load source pointer**: Read 32-bit pointer from `table_base + index + (0x45310)`
5. **Copy coefficients**: Copy 13 bytes from source to DSP coefficient buffer at 0x45210

**Voice-specific routing** (`DSP_VoiceCoeffRoute`) adds a nested lookup:
1. Compute voice allocation index: `voice × 287 + channel × 37 + 110`
2. Read routing type from allocation entry at `0x41368 + index`
3. Use routing type bits to select coefficient source
4. Copy 13 coefficient bytes plus 3 extra configuration bytes

**Routing Functions (Sub CPU):**

| Function | Purpose |
|----------|---------|
| `DSP_RouteCoeffs_TypeA` | Route coefficients via type-A tables (offsets 0x44-0x50) |
| `DSP_RouteCoeffs_TypeB` | Route coefficients via type-B tables (offsets 0x58-0x64) |
| `DSP_CopyCoeffs_TypeA` | Direct coefficient copy (offset 0x50, no type dispatch) |
| `DSP_CopyCoeffs_TypeB` | Direct coefficient copy (offset 0x64, no type dispatch) |
| `DSP_VoiceCoeffRoute` | Voice-specific routing with allocation table lookup |
| `DSP_VoiceCoeffRoute2` | Extended voice routing with filter/vibrato coefficients |
| `DSP_AlgoCoeffLookup` | Algorithm-based coefficient selection (5-way dispatch, algo 0-4) |

### DSP Register Write Protocol

The `DSP_WriteChannelRegs_Inner` function reveals the register-level protocol for writing to DSP channels via 0x130000:

```
Register address = channel_number × 32 + 0x10

For each of 8 registers (sequential):
  1. Write register address byte to (0x130000)   ; select register
  2. Write data byte to (0x130002)               ; write value
  3. Increment register address

Data sources for 8 registers:
  Reg 0-1: From BC (caller's direct parameters)
  Reg 2-3: From QBC (upper word of XBC)
  Reg 4-5: From DE (caller's direct parameters)
  Reg 6-7: From QDE (upper word of XDE)
```

The caller passes the 8 bytes in two 32-bit registers, XBC and XDE. `ld bc, qbc` / `ld bc, qde` fetch their upper words. No register bank is involved: QBC/QDE are current-bank register codes 0xE6/0xEA.

**Utility Functions (Sub CPU):**

| Function | Purpose |
|----------|---------|
| `DSP_BlockCopyWords` | Block copy words via `ldirw` instruction |
| `DSP_FillMemWords` | Fill memory with repeated word value |
| `DSP_ChecksumRange` | Compute one's complement checksum of 32-bit word range |

### DSP State Dispatcher Architecture

The Sub CPU firmware contains a master DSP state dispatcher at `DSP_State_Dispatcher` that orchestrates all DSP configuration changes. It is called via this chain:

```
Audio_System_Init (0x01FACB)        -- on boot
  -> DSP_System_Init (0x034C45)
    -> DSP_Reset (0x0360A3)
      -> DSP_State_LoadAndApplyAll               -- full DSP reconfigure
        -> DSP_State_ApplyAll              -- DSP state apply orchestrator
          -> DSP_State_Dispatcher    -- master DSP state dispatcher

Audio_Main_Loop (0x01FAEB)          -- at runtime
  -> Audio_Process_DSP (0x035A7D)   -- reads ring buffer at 0x3B60
    -> command 0x2D dispatch
      -> DSP_CmdHandler_2D                -- sub-command router
        -> ... -> DSP_State_ApplyAll -> DSP_State_Dispatcher (same chain)
```

The master dispatcher (`DSP_State_Dispatcher`) takes a pointer to a state structure in XWA:

```
State structure (at RAM, passed via XWA → XIZ):
  +0: (base)
  +2: algorithm change flag (1 = needs algorithm change)
  +4: mode flag (1 = reset/disconnect mode, other = normal)
  +6: algorithm number
```

The dispatcher follows a conditional 11-step pipeline:

| Step | Routine | Condition | Description |
|------|---------|-----------|-------------|
| 1a | `DSP_ResetLoop` | mode == 1 | Reset both DSP chips (assert/deassert reset lines) |
| 1b | `EFF_MuteLoop` | mode != 1 | Mute all 5 EFF channels via `DSP_WriteEFFConfig` |
| 2 | `DSP_MuteLoop` | always | Mute DSP hardware chips 0-1 via `DSP_WriteGlobalConfig` |
| 3 | `DSP_AlgorithmChangeCheck` | always | If global algo-change flag set, call `DSP_AlgorithmChange` |
| 4a | `EFF_WriteHeader` | mode==1 or algo_change | Write EFF header config for channel 0 |
| 4b | `EFF_DisconnectLoop` | mode==1 or algo_change | Disconnect all effect slots (iterate 4→0) |
| 5 | `DSP_UnmuteLoop` | always | Unmute DSP hardware chips 0-1 via `DSP_WriteGlobalConfig` |
| 6 | `EFF_HeaderChangeDataLoop` | always | Process per-slot header changes + parameter changes (5 slots) |
| 7 | `EFF_LinkLoop` | always | Re-link connected effect slots (iterate 4→0) |
| 8 | `EFF_VolumeLoop` | always | Update volume parameters for all effect slots (iterate 4→0) |
| 9 | `EFF_SecondaryLinkPath` | always | Two-pass: compute max delay, then re-link secondary paths |
| 10 | Algo state update loop | always | Iterate slots 4→0, update algorithm state at 0x12226 |

**EFF_MuteLoop Detail (Step 1b):**
Iterates EFF slots 0-4. For each slot whose active word is 1 (RAM 0x4930 + slot×2), sends mute config from pointer table at 0x1F3BC via `DSP_WriteEFFConfig`. If any slot was muted, schedules a 20-unit delay via `DSP_ScheduleDelay`.

**DSP_AlgorithmChange Detail (Step 3):**
When the DSP algorithm changes, loads 8 bytecode programs (`DSP_AlgoChange_Program`, `DSP1_BootProgram`, `DSP2_BootProgram_Step1`-`Step6`) sequentially from ROM:

| Order | ROM Address    | Chip | Purpose                                  |
|-------|----------------|------|------------------------------------------|
| 1     | 0x01E63C       | 0    | Common header (`DSP_AlgoChange_Program`) |
| 2     | 0x01E6BE       | 0    | DSP1 boot program (`DSP1_BootProgram`)   |
| 3     | 0x01E996       | 1    | `DSP2_BootProgram_Step1`                 |
| 4     | 0x01EA12       | 1    | `DSP2_BootProgram_Step2`                 |
| —     | (1-unit delay) | —    | Wait for DSP to settle                   |
| 5     | 0x01E7C5       | 1    | `DSP2_BootProgram_Step3`                 |
| 6     | 0x01E8A7       | 1    | `DSP2_BootProgram_Step4`                 |
| 7     | 0x01E891       | 1    | `DSP2_BootProgram_Step5`                 |
| 8     | 0x01E947       | 1    | `DSP2_BootProgram_Step6`                 |

If mode == 1, de-asserts DSP2 reset before loading channel configs.

**EFF_HeaderChangeDataLoop Detail (Step 6):**
Calls `EFF_Change_Handler` for each dirty slot. The handler dispatches by slot number:
- Slots 0-1: Standard EFF change path → `EFF_Change_WithDebug`
- Slots 2-4: Algorithm-dependent path (mode==1 uses `EFF_Change_WithDebug`, otherwise `EFF_DataChange_WithDebug`)

`EFF_Change_WithDebug` writes two config blocks per change: a primary config from table at 0x1ED7C and a secondary from 0x1EF0C, both indexed by the change type. Special handling for channel 1 with types 0x9 and 0xA (hardcoded reverb/chorus ROM addresses).

All 13 diagnostic format strings (at ROM 0x0122CC-0x012397) are triggered through this dispatcher. The strings are output via `Debug_Print_String` (0x038365) which calls the boot ROM's `DEBUG_OUTPUT_STRING` at `0xFFFEA1`. In the dumped IC30, that routine's character sink (`DEBUG_OUTPUT_CHAR_STUB`, 0xFFFEC1) is `ld iz,0xFE00` plus 12 `nop`s and `ret`, so nothing is actually output.

### Inter-CPU Command Protocol (Command 0x2D — DSP Configuration)

The Main CPU sends DSP effect configuration changes to the Sub CPU via a layered protocol:

**Layer 1 — Latch Protocol:**

The Main CPU writes bytes to the inter-CPU latch at `0x140000` (the Sub CPU reads it at `0x120000`). The first byte is a header:

| Bits | Meaning                                                   |
|------|-----------------------------------------------------------|
| 7-5  | Handler index (0-7 into `CMD_DISPATCH_TABLE` at `0xF46C`) |
| 4-0  | Payload length minus 1 (DMA count = value + 1)            |

For DSP config changes, header byte `0x7F` is used:
- Handler index = 3 → `Audio_CmdHandler_60_7F` (0x035893)
- Payload = 32 bytes (0x1F + 1)

The `INT0_HANDLER` (0x020E86) reads the header byte directly, then sets up HDMA channel 0 to transfer the payload to buffer at `0x10F0`. After DMA completion, `MICRODMA_CH0_HANDLER` (0x020F1F) dispatches to the handler.

| Handler | Range     | Routine                     | Purpose                                      |
|---------|-----------|-----------------------------|----------------------------------------------|
| 0       | 0x00-0x1F | `Audio_CmdHandler_00_1F`    | MIDI/note commands → ring buffer at `0x2B0D` |
| 1       | 0x20-0x3F | `Audio_CmdHandler_20_3F`    | Stub (unused)                                |
| 2       | 0x40-0x5F | `Audio_CmdHandler_40_5F`    | (function at 0x01FC7F)                       |
| 3       | 0x60-0x7F | `Audio_CmdHandler_60_7F`    | Audio/DSP commands → ring buffer at `0x3B60` |
| 4       | 0x80-0x9F | `Serial1_DataTransmit_Loop` | Serial port 1 data                           |
| 5       | 0xA0-0xBF | `Audio_CmdHandler_A0_BF`    | (function at 0x03CFEE)                       |
| 6       | 0xC0-0xDF | `Audio_CmdHandler_C0_FF`    | (function at 0x020C12)                       |
| 7       | 0xE0-0xFF | `Audio_CmdHandler_C0_FF`    | Same as handler 6                            |

**Layer 2 — Ring Buffer:**

`Audio_CmdHandler_60_7F` copies the 32-byte payload into a ring buffer at `0x3B60`:
- Write pointer: `(3B60h)` — 11-bit, wraps at 0x800 (2KB)
- Available count: `(3B64h)` — number of bytes queued
- Buffer base: `(3B66h)` — pointer to actual data area

Two consecutive 32-byte payloads give 64 bytes in the ring buffer for a single DSP config command.

**Layer 3 — Command Processing:**

`Audio_Process_DSP` (called from main loop) reads from the ring buffer. `DSP_Cmd_DequeueHeader` reads 7 header bytes into RAM `4369h`-`436Fh`, plus the command byte at `4368h`.

For command `0x2D` (DSP configuration), the 8-byte header is:

| Byte | RAM Address | Description |
|------|-------------|-------------|
| 0 | 4368h | Command byte = `0x2D` |
| 1 | 4369h | Sub-command (0 = normal config) |
| 2 | 436Ah | EFF slot selector (0x0A-0x0E → slot 0-4) |
| 3 | 436Bh | Reserved |
| 4 | 436Ch | Reserved |
| 5 | 436Dh | Reserved |
| 6 | 436Eh | Data length (0x38 = 56 bytes) |
| 7 | 436Fh | Update mode (0x00 = partial, 0xFF = full) |

Then `DSP_RingBuf_ReadAndCompare` (at 0x035A7E) reads 56 data bytes from the ring buffer into `4370h`-`43A7h`, comparing each byte with the existing slot buffer and counting changes.

**Layer 4 — EFF Slot Storage:**

The 56-byte parameter block is compared against the current slot buffer at `4496h + slot × 0x38`:

| EFF Slot | Buffer Address |
|----------|---------------|
| 0 | 0x4496 |
| 1 | 0x44CE |
| 2 | 0x4506 |
| 3 | 0x453E |
| 4 | 0x4576 |

Each slot contains 28 word-sized parameters. Word[0] is the **algorithm ID** (e.g., 0x0014 = algorithm 20 = CONCERT REVERB 1). The remaining words are effect-type-specific parameter values.

If any parameters changed, `DSP_ApplyConfig` (at 0x03616A) copies the full 290-byte DSP state (8-byte header + 5 × 56-byte slots) from `0x448E` to an allocated work buffer via `DSP_State_ApplyBuf` (at 0x038E31), which marks it as dirty and triggers processing by the DSP state dispatcher.

### DSP Data Tables

The Sub CPU uses several lookup tables for DSP configuration:

| Address | Size          | Description                                                      |
|---------|---------------|------------------------------------------------------------------|
| 0x1E496 | variable      | EFF header config table                                          |
| 0x1ED6D | 5 bytes       | Per-EFF-slot DSP channel byte                                    |
| 0x1ED72 | 5 bytes       | Per-EFF-slot settle time (`EFF_SlotSettleTime_Table`)            |
| 0x1ED7C | variable      | EFF change config table (per sub-change)                         |
| 0x1EF0C | variable      | EFF data change config table                                     |
| 0x1F09C | 100 × 4 bytes | Per-effect parameter VALUE record pointers                       |
| 0x1F22C | 100 × 4 bytes | Per-effect parameter DESCRIPTOR record pointers                  |
| 0x1F3BC | variable      | EFF mute config table                                            |
| 0x1F3D0 | variable      | DSP mute config table                                            |
| 0x1F3E0 | variable      | DSP unmute config table                                          |
| 0x1F3F0 | variable      | EFF disconnect config table                                      |
| 0x1F404 | variable      | EFF link config table                                            |
| 0x122A6 | 2 × 11 bytes  | Sparse parameter update sequences (for algorithms 0x0F and 0x35) |
| 0x12226 | variable      | Per-algorithm byte (DSP channel assignment lookup)               |

**Parameter Translation Chain:**

`DSP_WriteParameter` (at 0x03C190) translates a parameter index + algorithm ID into DSP register writes:

1. Look up `0x1F22C[effect]` → descriptor records (each lists the DSP register cells for one parameter id), passed in XDE
2. Look up `0x1F09C[effect]` → value records (translator opstreams ending 0x7A), pushed as an argument (XBC = `ToneGen_WorkArea`)
3. Call `DSP_ParameterWriteEngine` (0x03C9E6), which walks those variable-length records
4. The inner loop reads 3 words per parameter from the mapping data
5. The resulting DSP writes go out through `DSP_DispatchCommand`/`DSP_DispatchData` (Port PZ/P7 for DSP1, the PF serial link for DSP2), not through 0x130000

Special cases: algorithms 9 and 10 for EFF slot 1 use hardcoded tables at `0x1E17F`/`0x1E19E` and `0x1E40A`/`0x1E42D` respectively.

The DSP write routines used by the dispatcher:

| Routine                        | Address  | Description                                           |
|--------------------------------|----------|-------------------------------------------------------|
| `DSP_WriteEFFConfig`           | 0x03C161 | Per-EFF DSP write (uses EFF-specific bytecode tables) |
| `DSP_WriteGlobalConfig`        | 0x03C181 | Global DSP write (direct bytecode config)             |
| `DSP_WriteParameter`           | 0x03C190 | Parameter-specific DSP write (algo-indexed tables)    |
| `DSP_ParameterWriteEngine`     | 0x03C9E6 | Core DSP parameter write engine                       |
| `DSP_BytecodeInterpreter_Init` | 0x03C259 | Bytecode interpreter entry point                      |

### DSP Bytecode Interpreter

The Sub CPU uses a bytecode interpreter to batch-write DSP register configurations. This is **not** DSP microcode — it's a Sub CPU-side interpreter that translates compact ROM-resident programs into sequences of hardware register writes to the DSP chips.

**Entry Points:**

| Routine | Address | Config Table | Purpose |
|---------|---------|-------------|---------|
| `DSP_WriteEFFConfig` | 0x03C161 | 0x14777 | Per-effect channel writes (looks up DSP chip from channel mapping at 0x1ED6D) |
| `DSP_WriteGlobalConfig` | 0x03C181 | 0x147B3 | Global DSP writes (always targets DSP chip 0) |

Both call `DSP_BytecodeInterpreter_Init` (0x03C259) which loads a 12-byte config entry from the table and begins execution.

**Config Entry Format (12 bytes per entry, indexed by channel/slot):**

```
Offset  Size  Description
+0      word  Config parameter 0 (passed to handlers via stack)
+2      word  Config parameter 1
+4      word  Config parameter 2
+6      word  Config parameter 3
+8      long  Pointer to bytecode program data in ROM
```

Entries are indexed by channel number: entry address = table_base + channel × 12.

**Bytecode Format:**

Each instruction has a 2-byte header followed by data bytes:

```
Byte 0: [opcode:4][count_high:4]
Byte 1: [count_low:8]

count = (count_high << 8) | count_low - 2
```

The `count` field gives the number of data bytes following the header (after subtracting 2 for the header itself).

**Opcode Set:**

| Opcode | Name | Description |
|--------|------|-------------|
| 0x0 | DSP Write Type 0 | Basic DSP register write (offset 0x000 in handler table) |
| 0x1 | DSP Write Type 1 | Extended parameter write (offset 0x23A) |
| 0x2 | DSP Write Type 2 | Multi-register write variant (offset 0x333) |
| 0x3 | DSP Write Type 3 | Complex routing write (offset 0x3DA) |
| 0x4 | DSP Write Type 4 | Short parameter write (offset 0x473) |
| 0x5 | DSP Write Type 5 | Short config write (offset 0x48D) |
| 0x6-0xC | — | Invalid (skipped) |
| 0xD | State Change | `DSP_Bytecode_NotifyStateChange`: releases kernel semaphore 1 (`TaskSem_Release`, WA = 1 is the semaphore id, not a priority), waking the task blocked on it, then switches tasks; continues when this task is next dispatched |
| 0xE | Send Command | Sends command byte + data bytes directly to DSP hardware |
| 0xF | End | Terminates bytecode execution |

**Opcode 0xE Detail (Send Command):**

```
[0xE | count] [cmd_byte] [data_byte_1] ... [data_byte_N]
```

1. First data byte sent via `DSP_DispatchCommand` (sets command register)
2. Remaining bytes sent via `DSP_DispatchData` (writes data to selected register)
3. `DSP_DispatchCommand`/`DSP_DispatchData` route to DSP1 or DSP2 based on the channel parameter

**Opcodes 0-5 Detail (Native Code Handlers):**

Opcodes 0-5 dispatch to native TLCS-900 machine code subroutines at `DSP_Bytecode_Op00_Groups5_ParamMix` (0x03C32E) through `DSP_Bytecode_Op05_Groups5_Masked` (0x03C7BB). The dispatch table at `DSP_BytecodeInterpreter_CaseOffsets` (0x014739) contains 16-bit offsets from 0x03C32E:

| Opcode | Offset | Handler Address | Approximate Size |
|--------|--------|----------------|-----------------|
| 0 | 0x000 | 0x03C32E | 570 bytes |
| 1 | 0x23A | 0x03C568 | 249 bytes |
| 2 | 0x333 | 0x03C661 | 167 bytes |
| 3 | 0x3DA | 0x03C708 | 153 bytes |
| 4 | 0x473 | 0x03C7A1 | 26 bytes |
| 5 | 0x48D | 0x03C7BB | 448 bytes |

Total native handler code: 1,613 bytes. These handlers keep a status word in QIZ (the upper word of XIZ, reached through the D7 extended-register prefix) and use auto-increment addressing `ld C,(XWA+)` and register-indirect compact forms to efficiently read data from the bytecode stream and route it to the DSP hardware via the parallel bus protocol. After completing, each handler jumps to `DSP_BytecodeInterpreter_CheckEnd` to continue the interpreter loop.

**Common Handler Idiom:**

All opcode 0-5 handlers share this recurring 13-byte "read-and-send" pattern:
```
ld XWA,(XSP+0x1a)     ; load bytecode stream pointer
ld C,(XWA+)            ; read next byte (auto-increment pointer)
ld (XSP+0x1a),XWA     ; store updated pointer
ld A,C                 ; copy byte to A
extz WA                ; zero-extend to 16-bit
ld BC,(XSP+0x14)       ; load DSP chip_id from stack (0=DSP1, 1=DSP2)
call DSP_DispatchCommand ; or DSP_DispatchData
ld QIZ,HL              ; save return status in the upper word of XIZ
```

**Stack Frame Layout (set up by `DSP_BytecodeInterpreter_Init`):**

| Offset | Size | Contents |
|--------|------|----------|
| +0x04 | word | Loop counter |
| +0x06 | word | Data count (from bytecode header, 12-bit) |
| +0x08 | word | Accumulator (handler 1) |
| +0x0A | word | Accumulator (handler 0) |
| +0x0C | word | Accumulator (handler 5) |
| +0x0E | word | Accumulator (handler 3) |
| +0x10 | long | Runtime parameter value (32-bit, from caller) |
| +0x14 | word | DSP chip_id (BC register) |
| +0x1A | long | Bytecode stream pointer (XWA register) |

**Handler 4 — Simple Command (26 bytes):**

Reads 1 byte from stream, sends as DSP command. No data follows. Used for standalone operations like algorithm select or mode switch.

**Handler 3 — Command + 16-bit Address + Raw Data (153 bytes):**

1. Read 1 byte → send as DSP command
2. Read 2-byte field → compute 16-bit DSP coefficient address:
   - `addr = (byte0 << 8) | byte1 + accumulator[0x0E]`
   - Send `(addr >> 8) & 0xFF` as data (address high byte)
   - Send `addr & 0xFF` as data (address low byte)
3. Advance stream by 2
4. Loop: read and send 1 raw data byte per iteration, for remaining `(count - 3)` bytes

Used for coefficient writes that need a full 16-bit address prefix.

**Handler 2 — Command + 2 Preamble + Groups of 3 (167 bytes):**

1. Read 1 byte → send as DSP command
2. Read 2 bytes → send as 2 data values
3. Loop: `(count - 3) / 3` iterations, each reads 3 bytes and sends as 3 data values

Used for bulk writes of 3-byte coefficient entries (e.g., 24-bit parameters or address+value pairs).

**Handler 1 — Command + 2 Preamble + Groups of 5 with 4-bit Address (249 bytes):**

1. Read 1 byte → send as DSP command
2. Read 2 bytes → send as 2 preamble data values
3. Loop: `(count - 3) / 5` iterations, each processing 5 stream bytes:
   a. Read 2 raw bytes → send as data
   b. Read 2-byte field → compute 12-bit coefficient address:
      - `addr = (byte0 << 4) | (byte1 >> 4) + accumulator[0x08]`
      - Send `(addr >> 4) & 0xFF` as data (address high nibble)
      - Send `((addr << 4) & 0xFF) | 1` as data (address low nibble + flag)
   c. Advance stream by 2, read 1 more raw byte → send as data

Used for interleaved coefficient/address writes with 12-bit packed addresses.

**Handler 0 — Command + 2 Preamble + Groups of 5 with 3-way Branching (570 bytes):**

Most complex handler. Processes data in groups of 5 bytes but branches based on the first byte of each group:

1. Read 1 byte → send as DSP command
2. Read 2 bytes → send as 2 preamble data values
3. Loop: `(count - 3) / 5` iterations, with 3-way branch per group:

   **Branch A** (first byte == 0x00 — static coefficient):
   - Read 2 raw bytes → send as data
   - Read 2-byte field → compute 12-bit address (4-bit shift), send as 2 data bytes
   - Advance stream by 2, read 1 more raw byte → send

   **Branch B** (first byte == 0x0A — raw passthrough):
   - Read and send 5 raw bytes directly as data (no computation)

   **Branch C** (any other value — parameter-modified coefficient):
   - Read 1 raw byte → send as data
   - Use 32-bit runtime parameter from `(XSP+0x10)` to compute 4 data bytes:
     - `data0 = stream[0] + ((param >> 1) & 0x7F)`
     - `data1 = stream[1] + ((param >> 9) & 0xFF)`
     - `data2 = stream[2] + ((param >> 1) & 0xFF)`
     - `data3 = stream[3] + ((param << 7) & 0x80)`
   - Send 4 computed data bytes, advance stream by 4

This is the key handler for **real-time parameter control**: bytecode programs contain template coefficient data, and the Branch C path mixes in the runtime parameter value to create dynamically-adjusted coefficients. Branch A handles static coefficients (address writes), Branch B handles raw data, and Branch C applies the parameter offset.

**Handler 5 — Command + 2 Preamble + Groups of 5, Variant (448 bytes):**

Very similar to Handler 0 but with different branching logic:

1. Read 1 byte → send as DSP command
2. Read 2 bytes → send as 2 preamble data values
3. Loop: `(count - 3) / 5` iterations, with 2-way branch:

   **Branch A** (first byte == 0x08 — 12-bit address with mask):
   - Same as Handler 0 Branch A, but additionally masks IZ high byte to 0
   - Uses `ld IZH, 0` to ensure address stays within 8-bit range

   **Branch B** (any other value — parameter-modified):
   - Same computation as Handler 0 Branch C

Handler 5 is used for DSP programs that need both address-masked coefficient writes and parameter-modified coefficients.

**Parameter Packing Summary:**

| Opcode | Address Width | Shift | Group Size | Loop Divisor | Accumulator |
|--------|-------------|-------|-----------|-------------|-------------|
| 0 | 12-bit | 4 | 5 bytes | 5 | stack[0x0A] |
| 1 | 12-bit | 4 | 5 bytes | 5 | stack[0x08] |
| 2 | — (raw) | — | 3 bytes | 3 | — |
| 3 | 16-bit | 8 | 1 byte | 1 | stack[0x0E] |
| 4 | — | — | — | — | — |
| 5 | 12-bit | 4 | 5 bytes | 5 | stack[0x0C] |

For 12-bit parameters, the value is packed across 2 bytecode bytes as `byte0[7:0] << 4 | byte1[7:4]`. This is split into two DSP data writes: high byte (`value >> 4`) and low byte (`(value << 4) & 0xFF`). This indicates **DSP registers use 12-bit parameter values** for most effect parameters.

For 16-bit parameters (opcode 3), the full 16-bit value is packed as `byte0[7:0] << 8 | byte1[7:0]`, split into high byte and low byte data writes.

**Execution Flow Example:**

When `DSP_WriteGlobalConfig` is called to mute DSP chip 0:

```
1. DSP_WriteGlobalConfig called with WA=0 (channel 0), XBC=pointer to mute config
2. Sets DE=0 (fixed for global writes)
3. Pushes XBC (config pointer), loads bytecode table pointer 0x147B3
4. Calls DSP_BytecodeInterpreter_Init:
   a. Loads 12-byte entry from 0x147B3 + 0*12 (channel 0)
   b. Copies 4 config words + 1 program pointer to stack frame
   c. Falls through to DSP_BytecodeInterpreter_CheckEnd
5. Interpreter reads first bytecode header from program pointer
6. Dispatches on opcode:
   - 0xE → sends command+data to DSP hardware
   - 0x0-0x5 → jumps to native handler for bulk register writes
   - 0xD → releases kernel semaphore 1 and switches tasks, then continues
   - 0xF → terminates
7. Repeats until 0xF terminator encountered
```

**Real-Time Parameter Modification:**

The `DSP_ParameterWriteEngine` (0x03C9E6) enables real-time control of DSP effects. When a MIDI parameter changes (e.g., reverb depth, chorus rate), the engine:

1. Looks up the effect slot's chip (0x1ED6D, `EFF_SlotToChip_Table`) and the effect's descriptor and value records (0x1F22C / 0x1F09C, indexed by effect number)
2. Walks the effect's descriptor records (from 0x1F22C, chosen by its caller `DSP_WriteParameter`) against its value records (0x1F09C)
3. Calls `DSP_PerParameterTranslator` to map the MIDI value to a 32-bit DSP parameter
4. Re-runs the bytecode program with the new parameter value in `(XSP+0x10)`
5. Handler 0/5 Branch C applies the parameter offset to template coefficients during write

This allows a single MIDI parameter change to update multiple DSP registers simultaneously, with the bytecode program encoding which registers to modify and how to transform the parameter value for each one.

### Effect Type Bytecode Programs

Each of the 16 effect types has two bytecode programs: an **algorithm program** (Primary Table at 0x1ED7C) that loads the DSP algorithm, and a **coefficient program** (0x1EF0C) that writes tunable coefficients.

**Algorithm Programs (Primary Table):** All use a single Handler 3 instruction with CMD=0x01 and DSP address 0x0054 (generic channels) or 0x00C8 (channel 1 reverb/chorus). The Handler 3 data size varies by algorithm complexity:

| Type | Algorithm Program | Size | Shared With | Notes |
|------|------------------|------|-------------|-------|
| 0 | 0x017263 | 250B | 7, 11-14 | Default/base algorithm |
| 1 | 0x0153C1 | 355B | — | |
| 2 | 0x015664 | 430B | — | |
| 3 | 0x015986 | 500B | — | |
| 4 | 0x015D43 | 330B | — | |
| 5 | 0x015FFE | 535B | — | Largest generic algorithm |
| 6 | 0x0177C3 | 485B | — | |
| 8 | 0x01743B | 515B | — | |
| 9 | 0x017F1F | 245B | — | |
| 10 | 0x018141 | 345B | — | |
| 15 | 0x016ACF | 435B | — | |

Types 0, 7, 11, 12, 13, and 14 share the same algorithm (0x017263). This indicates 10 distinct algorithms and 6 aliases.

**Channel 1 Special Programs:** Reverb (type 0x9) and Chorus (type 0xA) have hardcoded programs bypassing the table lookup, using DSP address 0x00C8 instead of 0x0054:

| Effect | Algorithm | Param Program | Algorithm Size |
|--------|-----------|--------------|----------------|
| Reverb (P1) | 0x1DFA5 | — | 275B |
| Reverb (P2) | — | 0x1E0B9 | 197B |
| Chorus (P1) | 0x1E1DE | — | 355B |
| Chorus (P2) | — | 0x1E342 | 199B |

**Parameter Program Structure:** All 16 types follow the same template:

```
H0 (9-31 groups × 5B)     ← Static/parameter-modified coefficients
H4 CMD=0x03               ← Section separator
H5 (3-21 groups × 5B)     ← Runtime-adjustable coefficients
H4 CMD=0x03               ← Section separator
H1 (8B)                   ← Address computation block
H2 (12-31 groups × 3B)    ← Bulk coefficient data
H4 CMD=0x03               ← Section separator
END
```

The number of H0/H5/H2 groups varies by effect type (more complex effects have more parameters). Type 5 (Flanger?) and types 3/15 have an extra H0 block before H5, suggesting additional parameter stages.

**EFF Chip Mapping (0x1ED6D):** Maps effect channels to DSP hardware:

| Channel | DSP Chip             | Settle time | Notes                            |
|---------|----------------------|-------------|----------------------------------|
| 0       | DSP1 (uPD6383GF-3BA) | 28          |                                  |
| 1       | DSP1                 | 24          | Hardcoded reverb/chorus programs |
| 2       | DSP2 (MN19413)       | 46          |                                  |
| 3       | DSP2                 | 20          |                                  |
| 4       | DSP2                 | 20          |                                  |
| 5-9     | (invalid)            | —           | Channel IDs > 4 not used for DSP |

Per-slot settle times are stored at 0x1ED72 (5 bytes, one per slot).

### Algorithm and Parameter ROM Tables

The SubCPU ROM contains 6 key tables for DSP effect configuration:

| Table                 | Address | Format   | Entries | Purpose                                                                              |
|-----------------------|---------|----------|---------|--------------------------------------------------------------------------------------|
| Chip Mapping          | 0x1ED6D | 1B × 5   | 5       | Channel → DSP chip (0=DSP1, 1=DSP2)                                                  |
| Slot settle time      | 0x1ED72 | 1B × 5   | 5       | Per-slot settle time (28, 24, 46, 20, 20), max-folded by the dispatcher              |
| Algorithm Programs    | 0x1ED7C | 4B × 100 | 100     | Pointers to algorithm bytecode (indexed by full algo ID 0-99)                        |
| Coefficient Programs  | 0x1EF0C | 4B × 100 | 100     | Pointers to coefficient bytecode streams (59 distinct), uploaded after the algorithm |
| Parameter values      | 0x1F09C | 4B × 100 | 100     | Per-effect parameter VALUE record pointers (0 = none)                                |
| Parameter descriptors | 0x1F22C | 4B × 100 | 100     | Per-effect parameter DESCRIPTOR record pointers (0x017425 = NO OPERATION stub)       |

**Algorithm Program Table (0x1ED7C):** 100 entries indexed by full algorithm ID. Unique programs for types 2-6, 8-10, 15 (Rotary). Types 0, 7, 11 share a common program at 0x017263. Extended IDs 16-27 (reverb subtypes) share algorithm programs with their base type but have unique coefficient programs.

**Coefficient Program Table (0x1EF0C, `EFF_CoefProgram_PtrTable`):** 59 distinct coefficient streams; 42 effect numbers share the NO OPERATION stream `DSP_Eff00_Coef_Bytecode`. The per-effect list is on [DSP Effect Data Zone]({{ site.baseurl }}/dsp-effect-data-zone/).

**Parameter Value and Descriptor Tables (0x1F09C, 0x1F22C):** Both are 100-entry arrays indexed by effect number (0-99). 41 effects (0, 7, 11-14 and others) have a NULL value pointer, and their descriptor pointer is the NO OPERATION stub 0x017425. Value records (0x1F09C) are translator opstreams (opcodes 0x21/0x24/0x40 and 0x61-0x79) ending in 0x7A. The descriptor record with the same id (0x1F22C) lists the DSP register cells that the value stream's field-index bytes select. Both tables end in 0xF0. See [DSP Effect Data Zone]({{ site.baseurl }}/dsp-effect-data-zone/).

### Parameter Translation Opcodes (Level 2 Bytecodes)

The `DSP_PerParameterTranslator` at SubCPU 0x03CAAE dispatches parameter translation opcodes that convert MIDI parameter values (0-127) into DSP chip coefficient writes. Each opcode implements a different mathematical transformation:

**Special Opcodes:**

| Opcode | Name | Description |
|--------|------|-------------|
| 0x21 | Interp2Point | 2-point linear interpolation (same as 0x66) |
| 0x24 | InterpMultiStep | Multi-step interpolation with breakpoints |
| 0x40 | PanScale | Pan/balance simple scaling |
| 0x7A | EndSection | End of parameter section |
| 0xF0 | Terminate | End of entire table |

**Regular Opcodes (0x61-0x78), dispatched via jump table at SubCPU 0x014745:**

| Opcode | Transform | Output | Description |
|--------|-----------|--------|-------------|
| 0x61 | SingleTableFetch | OscParam | Direct LUT lookup |
| 0x62 | AlgoTypeTableFetch | FreqParam | Algorithm-specific LUT |
| 0x63 | AlgoParamDecode | OscParam | Effect type/variant selection |
| 0x64 | PitchScale | FreqParam | Frequency domain scaling |
| 0x65 | VolumeScale | OscParam | Amplitude domain scaling |
| 0x66 | Interp2Point | OscParam | 2-point coefficient blend |
| 0x67 | InterpFPScale | OscParam+Offset | Fixed-point scaling with offset |
| 0x68 | InterpDiv0xB4 | FreqParam | Time constant ÷ 0xB4 |
| 0x69 | VolumeCurveFP | OscParam | Fixed-point volume curve |
| 0x6A | FreqCurveFP | FreqParam | Fixed-point frequency curve |
| 0x6B | FreqInterp2Point | FreqParam | Frequency 2-point interpolation |
| 0x6C | Interp3PointOffset | FreqParam | 3-point interpolation with offset |
| 0x6D | ReverbCurveFP | OscParam | Reverb decay time curve |
| 0x6E | InterpFPComplex | OscParam | Complex fixed-point interpolation |
| 0x6F | PanPiecewiseLin | OscParam | Piecewise-linear pan curve |
| 0x70 | BiquadCoeff | (direct) | Biquad filter coefficient computation |
| 0x71 | DetuneSigned | OscParam | Signed detune curve |
| 0x72 | BiquadWarp | (direct) | Biquad frequency warping |
| 0x73 | InterpDiv0xC6 | OscParam | Time constant ÷ 0xC6 |
| 0x74 | LUTParamSet | (direct) | Multi-parameter LUT write |
| 0x75 | ParamEQCurve | OscParam | Parametric EQ curve |
| 0x76 | SOSCoeff | (direct) | Second-order section coefficients |
| 0x77 | Interp2PointB | OscParam | 2-point variant B |
| 0x78 | VolScaleB | OscParam | Volume scale variant B |

Output targets: **OscParam** writes oscillator/amplitude registers, **FreqParam** writes frequency/timing registers, **(direct)** writes multiple registers directly.

### Named Effect Parameters

The MainCPU ROM at 0xE324C4 contains 86 parameter name entries (17 bytes each: 16-char name + ':' separator). Key named parameters:

| Index | Name             | Index | Name             |
|-------|------------------|-------|------------------|
| 0x01  | VOLUME           | 0x22  | REVERB TIME      |
| 0x03  | REV SEND         | 0x23  | PRE DELAY        |
| 0x04  | DRIVE            | 0x24  | HIGH DAMP GAIN   |
| 0x05  | ADJUST           | 0x25  | ER.LEVEL         |
| 0x06  | EMPHASIS GAIN    | 0x26  | PITCH L          |
| 0x07  | DEPTH            | 0x27  | PITCH R          |
| 0x08  | LFO SPEED        | 0x28  | THRESHOLD        |
| 0x09  | SLOW LFO SPEED   | 0x29  | RATIO            |
| 0x0A  | FAST LFO BALANCE | 0x33  | BAND EMPHASIS FC |
| 0x0B  | RESONANCE        | 0x34  | BAND EMPHASIS Q  |
| 0x0C  | MANUAL           | 0x35  | BAND EMPHASIS G  |
| 0x0D  | SLOW/FAST        | 0x39  | FEEDBACK         |
| 0x1D  | PHASER DRY/WET   | 0x3B  | WAH CENTER FC    |
| 0x53  | INTENSITY        | —     | —                |

### Effect Algorithm Type Summary

Each algorithm defines which named parameters control the DSP, and which translation opcodes transform MIDI values.

**Parameter Mapping Bytecode Format:** Each entry is `[flags:1] [total_length:1] [opcode:1] [data:length-3]`. The first data byte is the primary parameter index. Additional data bytes may be secondary parameter indices or coefficient data. Programs terminate with 0xF0.

**Complete Parameter→Transform Mappings (decoded from ROM tables at 0x1EF0C):**

⚠ The Algo column below is the effect number (0 NO OPERATION, 1 CHORUS … 10 MULTI TAP DELAY), read from the first entries of the 100-entry arrays; the Effects column groupings are not supported by the ROM.

| Algo | Effects | Parameter Mappings (ordered) |
|------|---------|------------------------------|
| 0,7,11 | PERCUSSIVE, STANDARD, MIX UP, HARS, SLOW ATTACKER, COMPRESSOR, EXCITER | Interp2Point(DRIVE) → InterpFPScale(PITCH L) → InterpFPComplex(ADJUST,EMPHASIS GAIN) → AlgoParamDecode(EMPHASIS GAIN) → Interp2Point(GLOBAL_SCALE) |
| 1 | (base type 1) | Interp2Point(SLOW LFO SPEED,FAST LFO BAL) → VolumeScale(VOLUME) → AlgoParamDecode(EMPHASIS GAIN) → Interp2Point(GLOBAL_SCALE) → LUTParamSet(DRY/WET) |
| 2 | STAGE, BATH ROOM, KARAOKE, ROOM... | Interp2Point(RESONANCE,MANUAL,SLOW/FAST,+2more) → VolumeScale(VOLUME) → AlgoParamDecode(EMPHASIS GAIN) → Interp2Point(GLOBAL_SCALE) → LUTParamSet(DRY/WET) |
| 3 | PEQ+COMPRESSOR, PEQ+VIBRATO, PEQ+FLANGER | AlgoTypeTableFetch(LFO SPEED,SLOW LFO,+2more) → PitchScale(RESONANCE,MANUAL) → SOSCoeff(VOLUME,DRIVE,SLOW/FAST,+1) → FreqInterp2Point(+2) → AlgoParamDecode(EMPHASIS GAIN) → Interp2Point(GLOBAL_SCALE) → LUTParamSet(DRY/WET) |
| 4 | PEQ+S.DELAY, PEQ+CHORUS, AUTO WAH+S.DELAY | Interp2Point(LFO SPEED,MANUAL) → VolumeScale(ADJUST,SLOW LFO) → Interp3PointOffset(PARAM_50,INTENSITY) → InterpDiv0xB4(LFO SPEED,SLOW LFO) → InterpDiv0xC6(VOLUME,+3) → AlgoParamDecode(EMPHASIS GAIN) → Interp2Point(GLOBAL_SCALE) → LUTParamSet(DRY/WET) |
| 5 | S.DELAY+PHASER/VIBRATO/FLANGER | Interp2Point(ADJUST,EMPHASIS GAIN,LFO SPEED,SLOW LFO) → VolumeScale(VOLUME,MANUAL) → InterpDiv0xB4(+2) → InterpDiv0xC6(+2) → AlgoParamDecode(EMPHASIS GAIN) → Interp2Point(GLOBAL_SCALE) → LUTParamSet(DRY/WET) |
| 6 | STRING, DEEP SPACE, SYMPHONIC | VolumeScale(VOLUME) → Interp2PointB(REV RETURN,DRIVE,EMPHASIS GAIN,SLOW LFO,RESONANCE,SLOW/FAST) → AlgoParamDecode(EMPHASIS GAIN) → Interp2Point(GLOBAL_SCALE) → LUTParamSet(DRY/WET) |
| 8 | RING MOD, ROTARY, AUTO WAH, PEDAL WAH | Interp2Point(+1) → ParamEQCurve(REV SEND) → SOSCoeff(DEPTH,+1) → PanPiecewiseLin(+2) → ReverbCurveFP(+2) → InterpFPScale(PITCH L) → AlgoParamDecode(EMPHASIS GAIN) → Interp2Point(GLOBAL_SCALE) |
| 9 | VIBRATO, PITCH SHIFTER, AUTO PAN | InterpFPScale(PITCH L,THRESHOLD) → SOSCoeff(REV SEND,EMPHASIS GAIN,MANUAL,+1) → InterpDiv0xC6(VOLUME,+3) → AlgoParamDecode(EMPHASIS GAIN) → Interp2Point(GLOBAL_SCALE) → LUTParamSet(DRY/WET) |
| 10 | CELM, CEL, PARAMETRIC EQ, NOISE FLANGER | Interp2Point(REV SEND,DRIVE,ADJUST,EMPHASIS GAIN) → InterpFPScale(PITCH L,THRESHOLD,RATIO,+1) → SOSCoeff(LFO SPEED,RESONANCE) → InterpDiv0xC6(DEPTH) → AlgoParamDecode(EMPHASIS GAIN) → Interp2Point(GLOBAL_SCALE) → LUTParamSet(DRY/WET) |

**Common suffix:** Every algorithm ends with AlgoParamDecode(EMPHASIS GAIN) for effect variant selection, Interp2Point(GLOBAL_SCALE) for output level, and (most) LUTParamSet(PHASER DRY/WET) for dry/wet mix control.

⚠ **Twelve of the named effects appearing in these tables ship a DSP microcode program
byte-identical to NO OPERATION (the same 49-word image, hash `2baadb775ff5eb84`)** —
having a decoded parameter-translation path (which named parameters map to which DSP
coefficients, described above) is independent of whether the uploaded algorithm actually
does anything. The twelve: `MODULATION DELAY`, `SLOW ATTACKER`, `NOISE FLANGER`, `CEL`,
`CELM`, `PITCH SHIFTER`, `PEDAL WAH`, `HARS EFFECT`, `STRING`, `PEDAL WAH+DELAY`, `DS_D`,
`OVER_D`. Of these, only `SLOW ATTACKER` is reachable from a front-panel effect-type list
(DSP EFFECT TYPE 14); the rest are not selectable through either array-driven editor page.

**Register cells (descriptor records at 0x1F22C):** The DSP register cells each parameter writes are listed in the effect's descriptor records at 0x1F22C, not in the value records at 0x1F09C. The 12-bit or 16-bit DSP coefficient addresses belong to the coefficient streams at 0x1EF0C. Effects whose 0x1F09C entry is NULL (0, 7, 11-14 and others) have no value records.

### DSP Coefficient Setup Pipeline

The coefficient setup subsystem configures DSP processing parameters through a multi-stage pipeline. Eight functions handle different aspects of coefficient configuration:

| Function | Size | Purpose |
|----------|------|---------|
| `DSP_SetCoeff_CopyDirect` | 69B | Direct coefficient copy from routing tables |
| `DSP_SetCoeff_CopyDirect2` | 69B | Direct copy variant 2 |
| `DSP_SetCoeff_RouteComplex` | 344B | Complex routing with multi-table lookup |
| `DSP_SetCoeff_RouteWithCallback` | 291B | Routing with callback (calls 0x032AE0) |
| `DSP_SetCoeff_FullPipeline` | 384B | Multi-stage processing (0x032AE0 + 0x032682) |
| `DSP_SetCoeff_WithDispatch` | 135B | Type-dispatched coefficient selection |
| `DSP_SetCoeff_WriteParams` | 90B | Individual parameter writes to 0x045216/17 |
| `DSP_SetCoeff_MasterConfig` | 706B | Master configuration (calls 0x02B014) |

### Voice-to-DSP Output Configuration

The voice output configuration functions map synthesized voices to DSP effect channels:

| Function | Size | Purpose |
|----------|------|---------|
| `Voice_DSP_OutputConfig` | 237B | Configure voice→DSP routing (type 1) |
| `Voice_DSP_OutputConfig2` | 237B | Configure voice→DSP routing (type 2) |
| `Voice_DSP_SimpleCopy` | 91B | Simple voice parameter copy to DSP |
| `Voice_DSP_SimpleCopy2` | 91B | Simple copy variant 2 |
| `DSP_VoiceParam_Dispatch` | 155B | Voice parameter dispatch with bit-5 routing |

These functions implement the voice→DSP routing pipeline:
1. Call `DSP_AlgoType_Dispatch1` to determine the algorithm type for the voice
2. Store result to DSP state (0x04520E or 0x04520C)
3. Call `Voice_BuildOutputList` to enumerate active voice outputs
4. Iterate the output list, configuring each via `ToneGen_WriteReg0640` (writes TG register 0x0640+ch)
5. Loop until all voices processed (up to 128 for full config, 64 for simple copy)

## Synthesis Architecture

The KN5000 implements a **hardware wavetable synthesis** architecture: the Sub CPU firmware handles MIDI event processing, voice allocation, and parameter management, while the actual sound generation is performed entirely by the tone generator hardware (IC303, TC183C230002).

### Polyphony and Voice Management

| Parameter              | Value                                           |
|------------------------|-------------------------------------------------|
| MIDI Channels          | 26 (channels 0-25)                              |
| Hardware Voices        | 64 simultaneous                                 |
| Voice Parameter Size   | 287 bytes per MIDI channel (0x11F)              |
| Hardware Voice Size    | 71 bytes per voice (0x47)                       |
| Voice Template         | 68 bytes at ROM 0xF8D5 (34 × 16-bit words)      |
| Channel Parameter Base | 0x04136E (Sub CPU RAM)                          |
| Hardware Voice Pool    | 0x04308E (Sub CPU RAM, 64 × 71 = 4544 bytes)    |
| Held-Key Map           | 0x4A4C + note (per-note bytes, not voice slots) |

**Channel address formula:** `0x04136E + (channel_number × 0x11F)`

The firmware implements **dynamic voice allocation**: any of the 26 MIDI channels can be assigned to any of the 64 hardware voices on demand. A Note On with nonzero velocity goes to `Voice_SetVelocity` (which picks 2 or 4 tone-generator channels according to the part mode) and then `Voice_SetPitch` (for part mode 0x40 only: parks the voice silent, writes its register block and then the key-on word). Velocity 0 goes to `Voice_Allocate` (0x02CCAD; despite its name it builds a match packet and walks the 64-entry voice table), `Voice_ParamInit` and `Voice_NoteOff`.

### Voice Parameter Structure (287 bytes per MIDI channel)

Each MIDI channel maintains a 287-byte parameter block:

| Offset | Size | Parameter                       | Set By         |
|--------|------|---------------------------------|----------------|
| +0x00  | 4    | Pitch base                      | Note On        |
| +0x04  | 2    | see Proprietary Control Changes | CC 0x95        |
| +0x06  | 2    | Volume (scaled)                 | CC 0x07        |
| +0x08  | 2    | Pan                             | CC 0x0A        |
| +0x0A  | 2    | Expression (scaled)             | CC 0x0B        |
| +0x11  | 1    | see Proprietary Control Changes | CC 0x91        |
| +0x12  | 1    | see Proprietary Control Changes | CC 0x97        |
| +0x1F  | 1    | see Proprietary Control Changes | CC 0x9B        |
| +0x20  | 1    | see Proprietary Control Changes | CC 0x9D        |
| +0x67  | var  | Extended parameter refs         | Program Change |

### Note-On Processing Pipeline

When a MIDI Note On arrives at `Voice_NoteOn` (0x02CF97):

```
MIDI Note On (channel, note, velocity)
  │
  ├─ velocity = 0? ──yes──> Voice_Allocate (0x02CCAD) → Voice_ParamInit → Voice_NoteOff
  │
  ├─ Voice_SetVelocity
  │     └─ switch on part mode (tone record +0x10 & 0xC0): 0x80 2 TG channels, 0x40/0x00 4, 0xC0 nothing
  │
  ├─ Voice_SetPitch (0x02C6CD, part mode 0x40 only)
  │     └─ mute the slot, build its registers (Voice_Init_Type1), write the key-on word
  │
  └─ ToneGen_WriteVoiceParams
        └─ 23 writes to 22 registers through 0x100000/0x100002
        └─ mid-burst: literal 0x8100 to the control register (+0x000); bit 15 of +0x080 is a frame strobe (up on write 2, down on write 23)
```

### Keybed Event Decoding

`Keybed_Decode_Event` (0x03D11F, formerly mis-named `ToneGen_Calc_Pitch`) turns a raw keybed event into a MIDI note and a curved velocity. It is on the keybed path, not the MIDI Note On path. Note = `(key & 0x7F) + 0x24`, so key 0 is MIDI note 36. The raw touch reading indexes `ToneGen_Velocity_Input_Curve` (0x01F43E) and is scaled by the touch-curve parameters (the words at 0x01F418/0x01F41A and the per-curve byte triplets from 0x01F420; curve number at 0x4A48, default 6). Note classes C#, D#, F#, G# and A# then lose a black-key trim. The result is clamped to 0-255 and mapped through `ToneGen_Velocity_Output_Curve` (0x01F53E). See [Keybed Scanning]({{ site.baseurl }}/keybed-scanning/).

### Volume and Expression

Volume (CC 0x07) and Expression (CC 0x0B) both use a shared **scaling lookup table** at ROM 0x011D16. The final output level is the product of volume and expression, applied to the tone generator's volume registers (groups 0x08-0x09).

Pan (CC 0x0A) is a direct value (0-127) written to channel offset +0x08 and translated to left/right balance via `EnvTranspose_UpdateLoop`.

### Envelope Processing

The KN5000 uses **hardware envelopes** in the tone generator IC303 — the Sub CPU firmware does not implement software ADSR:

- **Key-on** (Note On): `ToneGen_WriteVoiceParams` writes the literal `0x8100` to the voice's control register (`+0x000`) in the middle of its 23-write burst. The disassembly reads this as the note-on gate from its position in the burst. Bit 15 of `+0x080` only frames the burst: it is raised on the second write and dropped on the last.
- **Key-off** (Note Off): Clears the enable flag, triggering hardware release
- **Sustain pedal** (CC 0x40): `Voice_CC_Sustain` (0x02A383) stores the pedal state (`Voice_CC_SetSustain`, 0x028962), then runs `Voice_AllocateForSustain` and the sustain retrigger scan over the part's held notes
- **Sostenuto** (CC 0x5B): Similar hold behavior for notes already sounding
- **Soft pedal** (CC 0x5D): Reduces velocity/volume scaling

Attack, decay, sustain level, and release times are determined by the tone generator hardware and the per-voice register template, not by CPU-side envelope generators.

### LFO and Modulation

The Mod Wheel (CC 0x01) is applied by `Voice_ModWheel_Apply` (0x029F73). It switches on the part mode, bits [7:6] of tone-record byte +0x10, and sends up to two destination commands per patch through `AudioChannel_Dispatch`:

| Bits [7:6]         | Descriptors read                   |
|--------------------|------------------------------------|
| 0x00 / 0x40 / 0xC0 | patch+0x17, two 3-byte descriptors |
| 0x80               | patch+0x15, two 3-byte descriptors |

Proprietary CCs formerly read as modulation parameters:

| CC   | Offset | Parameter                       |
|------|--------|---------------------------------|
| 0x9B | +0x1F  | see Proprietary Control Changes |
| 0x9C | —      | see Proprietary Control Changes |
| 0x9D | +0x20  | see Proprietary Control Changes |

The actual LFO oscillator runs inside the tone generator hardware; the firmware only sets depth and mode parameters.

### Filter Control

No explicit filter envelope or cutoff sweep exists in the CPU firmware. The tone generator hardware likely contains internal filters controlled by:

- **Tone gen registers 0x0800-0x08C0** (Volume/Level group): Likely include filter-related parameters
- **Tone gen registers 0x09C0-0x0A40** (Aux group): Extended parameters potentially including resonance

Filter behavior is fixed per voice preset — no real-time filter sweeps are implemented in firmware.

### Proprietary Control Changes (0x91-0x9D)

| CC   | Handler                     | Channel Offset                             | Function                                                                                                             |
|------|-----------------------------|--------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| 0x91 | `Voice_CC_SetReverbDepth`   | +0x11                                      | raw byte; tested bitwise by `Voice_Env_ApplyVelocity_Type0`                                                          |
| 0x95 | `Voice_CC_SetChorusEnable`  | +0x04 bit 2                                | flag                                                                                                                 |
| 0x97 | `Voice_CC_SetChorusDepth`   | +0x12                                      | raw byte                                                                                                             |
| 0x9B | `Voice_CC_SetDelayDepth`    | +0x1F                                      | raw byte; its nibbles select gate routing                                                                            |
| 0x9C | `Voice_CC_SetDelayEnable`   | -0x04 (`Part_PresentWord`, 0x04136A) bit 8 | flag                                                                                                                 |
| 0x9D | `Voice_CC_SetDelayFeedback` | +0x20                                      | raw byte; 1 / 2 force TG reg 0x180 to 0x00 / 0x7F, otherwise the tone default (the overlay HLE renders 0x180 as pan) |

Offsets are relative to 0x04136E + channel × 0x11F. These handlers store the controller value as is; only CC 7 and CC 11 go through the lookup table at 0x011D16. The labels (reverb/chorus/delay) are inherited and the meanings are not established.

## Tone Generator

The tone generator (IC303, TC183C230002) is a custom Matsushita 64-voice wavetable synthesis LSI. It has two interfaces:

- **Register config** at 0x100000/0x100002: Write voice parameters and global settings via register-indirect addressing (32 registers per voice across 8 groups × 4 banks, 13 global registers)
- **Keyboard input** at 0x110000/0x110002: Read voice events (note on/off with velocity)

See [Tone Generator]({{ site.baseurl }}/tone-generator/) for the complete register map, initialization sequence, and chip inventory.

### Where the tone parameters come from

The parameter records the Sub CPU pushes into IC303 are not built in code: they are read from the
**tone database**, the 320 KB block at Table Data ROM `0x830000`-`0x87FFEF` that the Main CPU
bulk-copies to Sub CPU RAM `0x50000` at boot. See [Tone Database]({{ site.baseurl }}/tone-database/)
for the directory, the 629-entry tone-record offset table, drum kits and percussion banks.

### Held-Key Map

`0x4A4C + note` (note = (key & 0x7F) + 0x24) holds 0xFF while a key is down and 0x00 when it is up. Its only job is to drop a key-up that has no matching key-down.

### Key Routines

| Routine                 | Address  | Description                                                                                   |
|-------------------------|----------|-----------------------------------------------------------------------------------------------|
| `ToneGen_Config_Init`   | 0x02DFCF | Configure all 64 voices and global registers                                                  |
| `ToneGen_Init`          | 0x03D016 | Keybed init (misnomer): touch curve 6 into 0x4A48, then `ToneGen_Poll_Init`                   |
| `ToneGen_Poll_Init`     | 0x03D1FB | Keybed power-on scan                                                                          |
| `ToneGen_Process_Notes` | 0x03D01E | Keybed service: forwards key events to the Main CPU as MIDI (when forwarding flag 0x4A4A = 1) |
| `Keybed_Read_Event`     | 0x03D0C5 | Read one key event from 0x110002/0x110000                                                     |
| `Keybed_Decode_Event`   | 0x03D11F | Key index → MIDI note, touch reading → velocity                                               |

### Hardware Access

- P6.7 controls A23 address line for tone generator access
- Status read: 0x110002 (bit 0 = data ready)
- Data read: 0x110000 (16-bit: low byte = note, high byte = raw touch reading, a curve index; 0xFF = no touch value)
- Register write: 0x100000 (address), 0x100002 (data) with P6.7 chip-select protocol

## Sound Categories

The Main CPU organizes sounds into 16 categories with pointers at 0xE023B0:

| Index | Category |
|-------|----------|
| 0 | PIANO |
| 1 | GUITAR |
| 2 | STRINGS & VOCAL |
| 3 | BRASS |
| 4 | FLUTE |
| 5 | SAX & REED |
| 6 | MALLET & ORCH PERC |
| 7 | WORLD PERC |
| 8 | ORGAN & ACCORDION |
| 9 | ORCHESTRAL PAD |
| 10 | SYNTH |
| 11 | BASS |
| 12 | DIGITAL DRAWBAR |
| 13 | ACCORDION REG. |
| 14 | GM SPECIAL |
| 15 | DRUM KITS |

## Feature Demo

⚠ **Update 2026-09-01: the "zero Note On/Off events" diagnosis below predates a MAME
core-level fix and is no longer the current state.** Commit `3fd44f3` (2026-08-05) found
that the sub→main inter-CPU link was wedged by a **duplicate `/INT0` dispatch** in MAME's
TLCS-900 (`tmp94c241`) core itself — a preempted, non-reentrant receive ISR got re-entered
by an acceptance-time `/INT0` re-assertion, ate the packet header a second time, and the
resumed original dispatch then parsed a payload byte as a header, wedging the link for
good. Dropping that re-assertion made latch writes, INT0 dispatches and latch reads 1:1:1,
and the demo now runs well past 100 seconds with real voice names on the play screen. The
detailed logs below (zero `putc_mrx` hits, ring buffer never written, etc.) describe the
**pre-fix** symptom and are kept as the record of that investigation, not as the current
emulation behavior. Separately, IC14's rhythm ROM dump had address lines A19 and A21
transposed. The corrected image (CRC aa4917ce) went upstream with mamedev/mame#15878
(merged 2026-08-17); only a confirming re-dump remains.

The Feature Demo plays pre-recorded MIDI sequences to demonstrate the keyboard's capabilities. Pressing the DEMO button triggers a complex initialization and playback sequence.

### Demo Initialization Flow

```
DemoModeFunc (entry point)
  ├─ First call → DemoMode_Initialize
  │     ├─ Demo_PreSetup (general preparation)
  │     ├─ Audio_WaitForReady (poll bit 2 of 0x0420)
  │     ├─ Voice_SavePreset (save current voice state)
  │     ├─ SeqInit_PostEventSequence (post events 0xE1, 0xE2, 0xE3)
  │     └─ Seq_StartMainControlAlt (enter main control with event 0x01E1000D)
  └─ Subsequent calls → DemoMode_Main_Operation
        ├─ Voice_InitializeAll (allocates 0x1F0 bytes, inits 16 voices × 26 params)
        ├─ Audio_ConfigureDSP (DSP and hardware setup)
        ├─ Voice_LoadVoiceTable (load 16 voice presets)
        ├─ Demo_PreSetup
        ├─ Voice_CopyPreset (restore voice data)
        ├─ Timer7_DisableInterrupt
        ├─ Audio_CheckSubsystemReady
        ├─ SeqInit_PostEventSequence
        ├─ SeqInit_FinalEvent (post event 0x1B with 0xFFFFFFFF)
        └─ Seq_StartMainControl (enter main control with event 0x01E1000C)
```

### Sequencer Event Processing

The sequencer reads song events from an internal buffer and dispatches them via inter-CPU latch:

| Routine | Address | Purpose |
|---------|---------|---------|
| `Seq_ProcessEventLoop` | 0xEF14CA | Main event processing loop |
| `Seq_CheckSongEnd` | 0xEF27A5 | Checks if song position (0x01F377) == end position (0x01F373) |
| `Seq_ProcessMidiEvent` | 0xEF13CD | Processes individual MIDI events (0x90=NoteOn, 0x80=NoteOff, 0xB0=CC) |

### Demo Song Data

The demo's style/rhythm preset data is at `Demo_StyleRhythmData` (0xF5CFCC), which contains:
- Rhythm/style parameter bytes (96 bytes)
- ASCII variation names: "a-variation1" through "c-variation4" (12 variations)
- Section names: "a-intro 1", "a-fill in 1", "a-ending 1", etc. (24 sections)
- Additional parameter data

The data loading uses LDIR block copy loops at `Demo_LoadVariationData` (0xF5CF8B) and `Demo_LoadVariationC_Data` (0xF5CFAE).

### Emulation Behavior Before the 2026-08-05 Fix (historical)

When the DEMO button is pressed in MAME, the Feature Demo enters its playback loop but **only sends configuration commands** (Control Change, Pitch Bend, Channel Pressure, SysEx). No Note On (0x90) or Note Off (0x80) events are ever dispatched. Analysis of a test session showed:

| Command Type | Count | Description |
|-------------|-------|-------------|
| 0xB0 (CC) | 2,555 | Control Change — Pan (1109), Expression (1099), Volume (73), others |
| 0xF0 (SysEx) | 36 | System Exclusive messages |
| 0xE0 (Pitch Bend) | 19 | Pitch Bend changes |
| 0xD0 (Chan Pressure) | 15 | Channel Pressure (aftertouch) |
| **0x90 (Note On)** | **0** | **No note events sent** |
| **0x80 (Note Off)** | **0** | **No note events sent** |

### Diagnostic Log Analysis

Detailed MAME logging with sequencer state instrumentation reveals:

**Rhythm ROM validation passes:**
- `rhy_ofs=00000000` at RAM `(3277h)` — NOT 0xFFFFFFFF, so `RhythmROM_CheckValid` returns success
- Rhythm ROM reads occur during demo mode (1800-3800 reads/second from 0x400000+ addresses)
- First rhythm ROM read at t=5.5s from 0x400000, PC=0xF5465E (inside `RhythmROM_ValidateHeader`)

**Sequencer state machine transitions:**

| Time | State | Event |
|------|-------|-------|
| Boot | 0x00 | Initial idle state |
| ~5s | 0x01 | Transition during initialization |
| ~21s | 0xE0 | `DemoMode_Main_Operation` entered |
| ~22.6s | 0xE4 | `DemoMode_Initialize` completed |

All observed states (0x00, 0x01, 0xE0, 0xE4) are outside the 0x10-0x16 skip range, confirming the sequencer dispatcher is NOT blocked by state checks.

**Ring buffer never written:**
- `putc_mrx=0` in every heartbeat — the function that writes MIDI events to the main sequencer ring buffer (`SeqMain_WriteByte` at 0xEF276D) has ZERO execution hits
- `SeqBuf wr=0000 rd=0000` — write and read positions are always equal (buffer empty)
- `Seq_CheckSongEnd` always returns 0 (no events to process)

**Startup flag always zero:**
- `startflag=0000` at RAM `(0x0251D8)` — never set to a non-zero value
- This flag controls whether `Seq_StartMainControlAlt` (called from `DemoMode_Initialize`) calls `Part_InitFromPreset` (0xF42EA4)
- It is the presentation-loaded flag. Only `Seq_InitializeAndStart` sets it, when a presentation is executed (`EVT_EXEC_PRESENTATION_REQ`). `Seq_StartMainControlAlt` sends `EVT_EXIT_PRESENTATION`, which calls `Part_InitFromPreset` only if the flag is set and then clears it. So 0 is the expected value during the ROM Feature Demo.

**Event loop rate drops 60x after demo init:**
- Before demo: ~11,500 event loop iterations/sec
- After demo init (state=0xE4): ~168-180 iterations/sec
- This indicates the sequencer dispatcher IS running heavier processing (rhythm ROM reads, pattern loading), consuming CPU time, but never producing MIDI events into the ring buffer

**Sequencer processing PC addresses during demo:**
- PCs in range F5CFxx-F641xx confirm rhythm/sequencer processing code is executing
- This range covers `Seq_RhythmProcessor` through `RhythmROM_CalcPatternAddr`

### Root Cause Analysis

The pipeline breaks between "rhythm data loaded from ROM" and "MIDI events generated into ring buffer":

```
Rhythm ROM (4MB) ──read──> Pattern Data in RAM ──???──> Ring Buffer (0x01F37B)
     ✓ working              ✓ executing                  ✗ NEVER written
```

Causes considered at the time (superseded by the /INT0 fix above):
1. **Startup flag (0x0251D8)** is never set, potentially skipping a critical initialization step
2. A missing Timer7 tick or other timing mechanism that drives MIDI event generation
3. An inter-CPU response or hardware register that gates the final event write stage

## Code References

### Main CPU (`v10/maincpu/kn5000_v10_program.s`)

| Routine | Address | Description |
|---------|---------|-------------|
| `Audio_Lock_Acquire` | 0xEF1FEE | Kernel semaphore P (wait); the audio path uses semaphore 7 |
| `Audio_Lock_Release` | 0xEF1F0F | Kernel semaphore V (release); byte twin of the sub CPU's `TaskSem_Release` |
| `Audio_DMA_Transfer` | 0xEF341B | Core DMA transfer |
| `SubCPU_Init_DMA_Channels` (was `Audio_InitDMAChannels`) | 0xEF329E | Initialize DMA channels |
| `sendCOMM` | 0xEF32F4 | Send command/audio data to Sub CPU (chunks 32-byte blocks) |
| `InterCPU_Send_Data_Block` | 0xEF3345 | Send 1-32 byte packet via inter-CPU latch |
| `Audio_CheckSubsystemReady` | 0xFDDE6F | Check if audio subsystem is ready for commands |
| `Audio_CheckInitStatus` | 0xFDF08A | Verify audio init state (checks 0xF19E) |
| `Voice_InitializeAll` | 0xFE0E75 | Initialize all 16 voices (26 params each) |
| `Audio_ConfigureDSP` | 0xFDBD52 | Configure DSP hardware and state |
| `DemoMode_Initialize` | 0xF869E3 | Feature Demo first-time initialization |
| `DemoMode_Main_Operation` | 0xF8696F | Feature Demo normal playback handler |

### Sub CPU (`v142/subcpu/kn5000_subprogram_v142.s`)

| Routine                  | Address  | Description                 |
|--------------------------|----------|-----------------------------|
| `Audio_System_Init`      | 0x01FACB | Master audio initialization |
| `MIDI_Dispatch`          | 0x034D93 | MIDI message dispatcher     |
| `Audio_CmdHandler_00_1F` | 0x034D5F | Audio command handler       |
| `Voice_NoteOn`           | 0x02CF97 | Note On processing          |
| `Voice_CtrlChange`       | 0x02A282 | Control Change processing   |
| `DSP_System_Init`        | 0x034C45 | DSP initialization          |
| `ToneGen_Init`           | 0x03D016 | Keybed init (misnomer)      |

## Serial Port 1 Interface

The Sub CPU's serial port 1 is used as a **Computer Interface** (TO HOST connector). The "SA" designation in the service manual schematics refers to "Sub Address" bus lines, not a chip name.

| Parameter | Value |
|-----------|-------|
| Mode | 8-bit UART (SC1MOD = 0x29) |
| Baud Rate | ~500kHz (20MHz / 4 / 10) |
| Sync Byte | 0xFE (sent at init and periodically) |
| TX Buffer | 1024 bytes at 0x0A00-0x0DFF |
| RX Buffer | 512 bytes at 0x0E16-0x1015 |

### MIDI Active Sensing

MAME emulation confirms that the Sub CPU transmits **0xFE (MIDI Active Sensing)** on this port approximately every 276ms. This is a standard MIDI heartbeat message indicating the device is alive and ready for communication. No other data has been observed on this port during normal operation or Feature Demo playback.

See [Tone Generator]({{ site.baseurl }}/tone-generator/#serial-port-1-sa-interface) for details.

## Related Pages

- [Tone Generator]({{ site.baseurl }}/tone-generator/) -- Register map and chip inventory
- [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/) -- Communication details
- [SubCPU Payload Loading]({{ site.baseurl }}/subcpu-payload-loading/) -- How firmware reaches the SubCPU
- [Tone Database]({{ site.baseurl }}/tone-database/) -- Factory tone/voice records, drum kits, wave catalogues
- [MIDI Subsystem]({{ site.baseurl }}/midi-subsystem/) -- External MIDI handling
- [CPU Subsystem]({{ site.baseurl }}/cpu-subsystem/) -- Main and Sub CPU details
- [System Overview]({{ site.baseurl }}/system-overview/) -- Overall architecture

## DSP Chip Identification

The KN5000 uses two custom DSP chips for effects processing:

| IC | Part Number | Manufacturer | Notes |
|----|-------------|-------------|-------|
| IC310 | MN19413 | Matsushita (Panasonic) | Custom ASIC, no public documentation |
| IC311 | uPD6383GF-3BA | NEC | No datasheet or programming manual is public; identified from the Pioneer CDJ-500 service manual (see [Effects DSP]({{ site.baseurl }}/effects-dsp/)) |

The two DSPs use different transports: IC311 a parallel byte port (PZ data; /WR /RD CS C/D on P7; READY on PH.0), and IC310 a write-only bit-banged serial link (PF.0 data, PF.2 clock, PE.6 select) with no ready line. Both are programmable: the Sub CPU uploads their microcode.

### DSP Control Pin Mapping

The Sub CPU controls both DSPs via GPIO pins:

| Pin     | Port         | Function                                      |
|---------|--------------|-----------------------------------------------|
| P7.3    | Port 7 bit 3 | Write strobe (active low)                     |
| P7.4    | Port 7 bit 4 | Read strobe (active low)                      |
| P7.5    | Port 7 bit 5 | CS1 — DSP1 chip select (IC311, uPD6383GF-3BA) |
| P7.6    | Port 7 bit 6 | Command/Data select (0=command, 1=data)       |
| PE.6    | Port E bit 6 | CS2 — DSP2 chip select (IC310, MN19413)       |
| PH.0    | Port H bit 0 | Status input (busy/ready)                     |
| PZ[7:0] | Port Z       | 8-bit bidirectional data bus                  |

**DSP1 handshake sequence:** see the Write Protocol under [DSP Port I/O Control](#dsp-port-io-control-sub-cpu-internal-ports).

**DSP2 serial protocol** (GPIO bit-bang):

DSP2 uses a different interface from DSP1. Instead of the parallel bus, it uses GPIO bit-bang serial on Port F:

| Pin | Function |
|-----|----------|
| PF.0 | SDA — Serial data to DSP2 |
| PF.2 | SCLK — Serial clock to DSP2 |
| PE.6 | CS2 — Chip select (active low) |

Each byte is transmitted MSB-first with one CS assert/deassert cycle per byte. Both `DSP2_Send_Command` and `DSP2_Send_Data` produce **9 SCLK rising edges** per byte (8 data bits + 1 trailing). The command variant adds an extra `DSP2_SPI_ClockPulseHigh` (the START condition) before the bit loop, but this doesn't create an additional rising edge because the first bit loop iteration's SCLK-high is absorbed (SCLK already high from the pulse).

```
Command byte: CS↓ → ClkHigh → [SDA=bit7, CLK↑(absorbed), CLK↓] → [SDA=bit6, CLK↑, CLK↓] × 7 → trailing CLK↑ → CS↑
Data byte:    CS↓ → [SDA=bit7, CLK↑, CLK↓] × 8 → trailing CLK↑ → CS↑
```

Transaction boundaries are marked by `DSP2_SPI_BusIdle` (PF.0=0, PF.2=0), called by bytecode Op0D between command groups.

Register writes use CMD 0x30 followed by 4-byte data groups: `[0x00, addr, val_hi, val_lo]`. Boot-time writes observed: REG[0xD0]=0x0000, REG[0xD3]=0x0000, REG[0x3C]=0x4000.

### DSP Firmware / Microcode Loading

**The Sub CPU DOES upload microcode to IC311, and this section's own earlier framing (below) was wrong about that.**

1. **The DSPs are programmable, and the firmware programs them at run time.** An earlier revision of this page claimed both chips carry fixed internal microcode. That is **superseded**: the Sub CPU uploads bytecode microprograms to IC311 (uPD6383GF) through the [DSP bytecode interpreter]({{ site.baseurl }}/dsp-bytecode-interpreter/), which is how the effect algorithms are switched. See [Effects DSP]({{ site.baseurl }}/effects-dsp/). The MAME driver corroborates this independently: the emulated host interface has verified that uploaded microcode lands in the chip's I-RAM.

2. **Sub CPU controls DSPs via register writes only** — DSP1 uses the parallel handshake (Port PZ data, Port P7 control); DSP2 uses the serial link described above. The Sub CPU sends:
   - **Command bytes** (P7.6=0): Select DSP register or operation mode
   - **Data bytes** (P7.6=1): Write parameter values to selected register

3. **Configuration via bytecode interpreter** — The Sub CPU has a bytecode interpreter (`DSP_BytecodeInterpreter_Init` at 0x03C259) that reads compact bytecode programs from ROM and translates them into sequences of DSP command+data writes, including the microcode upload itself. This is a **Sub CPU-side** interpreter that emits DSP-side bytecode; it is not the DSP's own instruction set.

**Evidence:** The `DSP_WriteEFFConfig` and `DSP_WriteGlobalConfig` routines both call `DSP_BytecodeInterpreter_Init` with ROM pointers to bytecode tables (at 0x14777 for EFF configs, 0x147B3 for global configs). These tables contain opcodes like:
- `0x0-0x4`: DSP register write operations
- `0x0D`: State change notification
- `0x0E`: Send command+data sequence
- `0x0F`: End of program

**Implication for emulation:** What blocks audio emulation is **not** a missing ROM dump — the uploaded bytecode is Sub-CPU ROM content and is already fully carved (see the [DSP Effect Data Zone]({{ site.baseurl }}/dsp-effect-data-zone/)). What is missing is the **uPD6383GF's own instruction-set semantics**: its instruction set is only partly decoded (see [uPD6383 decode status]({{ site.baseurl }}/upd6383-decode-status/)), so even with the microcode upload traffic captured, the chip's audio-domain behavior cannot yet be fully reproduced. This is the primary remaining challenge for accurate sound emulation.

### DSP Preset Structure

The 0x91-word (290-byte) block at SubCPU RAM address 0xF01E contains **effect parameter presets**, not DSP microcode. The structure is:

| Offset | Size | Content |
|--------|------|---------|
| +0x00 | 20 words | Header / global effect config |
| +0x28 | 5 × ~24 words | Effect parameter blocks |

Each effect block contains parameters:
- **Type** (effect algorithm selector: 1, 3, 4, 8)
- **Level** (0-99)
- **Depth** (0-99)
- **Time** (0-99)
- **Rate** (0-99)
- **Mix** (dry/wet balance, 0-99)
- **Feedback** (0-99)

### Effect Type Name Table

The Main CPU ROM contains a 128-entry effect type name table at address `0xE32A7A` (pointer table) with 16-character padded strings at `0xE32C7A`-`0xE33579`. 71 entries, all within effect numbers 0-99, are named; the rest are unused (`----------`).

**Modulation Effects (0-6):**

| Index | Name |
|-------|------|
| 0 | NO OPERATION |
| 1 | CHORUS |
| 2 | MODULATED CHORUS |
| 3 | ENHANCER |
| 4 | FLANGER |
| 5 | PHASER |
| 6 | ENSEMBLE |

**Delay & Gated Effects (8-11):**

| Index | Name |
|-------|------|
| 8 | GATED REVERB |
| 9 | SINGLE DELAY |
| 10 | MULTI TAP DELAY |
| 11 | MODULATION DELAY |

**Reverbs (15-27):**

| Index | Name |
|-------|------|
| 15 | ROCK ROTARY |
| 16 | ROOM REVERB 1 |
| 17 | ROOM REVERB 2 |
| 18 | PLATE REVERB 1 |
| 19 | PLATE REVERB 2 |
| 20 | CONCERT REVERB 1 |
| 21 | CONCERT REVERB 2 |
| 22 | DARK REVERB 1 |
| 23 | DARK REVERB 2 |
| 24 | BRIGHT REVERB 1 |
| 25 | BRIGHT REVERB 2 |
| 26 | WAVE REVERB 1 |
| 27 | WAVE REVERB 2 |

**Drive & Dynamics (32-39):**

| Index | Name |
|-------|------|
| 32 | DISTORTION |
| 33 | OVERDRIVE |
| 34 | FUZZ |
| 35 | EXCITER |
| 36 | COMPRESSOR |
| 37 | SLOW ATTACKER |
| 38 | NOISE FLANGER |
| 39 | PARAMETRIC EQ |

**Special Effects (44-60, 63):**

| Index | Name |
|-------|------|
| 44 | CEL |
| 45 | CELM |
| 48 | AUTO PAN |
| 49 | PITCH SHIFTER |
| 50 | VIBRATO |
| 51 | PEDAL WAH |
| 52 | AUTO WAH |
| 53 | ROTARY SPEAKER |
| 54 | RING MODULATOR |
| 55 | HARS EFFECT |
| 56 | MIX UP |
| 57 | STANDARD |
| 58 | PERCUSSIVE |
| 59 | SYMPHONIC |
| 60 | DEEP SPACE |
| 63 | STRING |

**Combination Effects (64-75, 79-81, 88-91, 96-99):**

| Index | Name |
|-------|------|
| 64 | S.DELAY+CHORUS |
| 65 | S.DELAY+S.DELAY |
| 66 | S.DELAY+FLANGER |
| 67 | S.DELAY+VIBRATO |
| 68 | S.DELAY+PHASER |
| 69 | PEDAL WAH+DELAY |
| 70 | AUTO WAH+S.DELAY |
| 71 | PEQ+CHORUS |
| 72 | PEQ+S.DELAY |
| 73 | PEQ+FLANGER |
| 74 | PEQ+VIBRATO |
| 75 | PEQ+COMPRESSOR |
| 79 | GEQ |
| 80 | DS_D |
| 81 | OVER_D |
| 88 | ROOM |
| 89 | KARAOKE |
| 90 | BATH ROOM |
| 91 | STAGE |
| 96 | PEQ+COMPR+DIST |
| 97 | PEQ+COMPR+OVERDR |
| 98 | PEQ+DIST+DELAY |
| 99 | PEQ+OVERDR+DELAY |

### Effect Parameter Names

86 entries of 17 bytes at Main CPU ROM `0xE324C4`-`0xE32A79` (`DspParamName_Table`): entries 0 and 85 are blank, entries 1-84 hold the names. ⚠ The indices in the table below are one lower than the firmware's and the `DspParamName_NN_*` labels: add 1 to each.

| Index | Name | Index | Name |
|-------|------|-------|------|
| 0-1 | VOLUME | 33 | REVERB TIME |
| 2 | REV SEND | 34 | PRE DELAY |
| 3 | DRIVE | 35 | HIGH DAMP GAIN |
| 4 | ADJUST | 36 | ER.LEVEL |
| 5 | EMPHASIS GAIN | 37-38 | PITCH L/R |
| 6 | DEPTH | 39 | THRESHOLD |
| 7 | LFO SPEED | 40 | RATIO |
| 8 | SLOW LFO SPEED | 41-42 | ATTACK/RELEASE SENS. |
| 9 | FAST LFO BALANCE | 43-44 | ATTACK/RELEASE RATE |
| 10 | RESONANCE | 45-46 | GATE/MASK TIME |
| 11 | MANUAL | 47 | HARS TIME |
| 12 | SLOW/FAST | 48-49 | LFO/OSC WAVEFORM |
| 13 | TREBLE FAST | 50-52 | BAND EMPHASIS FC/Q/G |
| 14 | SLOW | 53-54 | LOW/HIGH MIX |
| 15-16 | WIND UP/DOWN | 55 | PHASE |
| 17-18 | BASS FAST/SLOW | 56 | FEEDBACK |
| 19 | VOLUME ADJUST | 57 | SWEEP RANGE |
| 20 | OSC SPEED | 58 | WAH CENTER FC |
| 21-22 | DELAY L/R | 59-60 | HARS TIME L/R |
| 23-24 | FEEDBACK L/R | 61-62 | BALANCE L/R |
| 25-28 | DRY/WET (various) | 63-64 | FAST LFO SPEED L/R |
| 29-32 | EMPHASIS FC/G | 65 | MODULATION DEPTH |
| 66-69 | DRY/WET (combos) | 82 | INTENSITY |
| 70 | FAST LFO SPEED | 83 | EXCITE |
| 71-73 | TREBLE/BASS DEPTH | 74-77 | DELAY 1-4 |
| 78-81 | PAN 1-4 | | |

### Known DSP Commands

These are the hardware command bytes sent to the DSP chips via the parallel bus (P7.6=0 for command, P7.6=1 for subsequent data). They are sent by bytecode opcode 0xE and by direct calls to `DSP_DispatchCommand`/`DSP_DispatchData`.

| Command | Direction | Via | Description |
|---------|-----------|-----|-------------|
| 0x01 | Write | OP3 (16-bit) | **Bulk initialization** — uploads full DSP state (150-350 data bytes). Used for EFF header (302B), reverb (272B), chorus (352B), algorithm init (117B). |
| 0x03 | Write | OP4 (cmd only) | **Algorithm select** — sent before coefficient data blocks (OP1/OP2). No data bytes. |
| 0x0F | Write | OP4 (cmd only) | **Disable/flush** — sent during algorithm init cleanup. No data bytes. |
| 0x10 | Write | OP4 (cmd only) | **Enable/start** — sent during algorithm init sequence. No data bytes. |
| 0x30 | Write | SEND_CMD (0xE) | **Parameter write** — sub-addressed, large data blocks (up to 190 bytes). Format: `0x30 [sub_addr] [data...]`. Sub-addresses 0x00, 0x03, 0x05, 0x0D seen. |
| 0x60 | Write | OP0 | **Bulk transfer** — used in standard parameter write sequences via opcode 0 handler. |

**Algorithm Configuration Sequence (from `DSP_AlgorithmChange`):**

The complete algorithm change writes 8 bytecode programs to the DSPs in order:

```
1. AlgoChange_Init (0x01E63C):
   - OP3: cmd=0x01, 117 bytes (16-bit packed DSP state init)
   - OP4: cmd=0x10 (enable)
   - OP4: cmd=0x10 (enable again)
   - OP4: cmd=0x0F (flush)

2. AlgoChange_Ch0 (0x01E6BE):
   - OP0: cmd=0x01, 23 bytes (12-bit packed init)
   - OP4: cmd=0x03 (select algorithm)
   - OP1: 8 bytes (algorithm header)
   - OP2: 93 bytes (coefficient data block 1)
   - OP4: cmd=0x03 (select algorithm)
   - OP1: 8 bytes (algorithm header 2)
   - OP2: 93 bytes (coefficient data block 2)

3-8. AlgoChange_Ch1 (6 programs, `DSP2_BootProgram_Step1`-`Step6`, with a delay after the second):
   - SEND_CMD: cmd=0x30 sub=0x03 + 2 data bytes (mode select)
   - STATE_CHANGE (release semaphore 1 and switch tasks)
   - SEND_CMD: cmd=0x30 sub=0x05 + 100-189 data bytes (coefficients)
   - SEND_CMD: cmd=0x30 sub=0x00 + variable data (parameters)
   - SEND_CMD: cmd=0x30 sub=0x0D + variable data (delay line config)
```

**Parameter Data Formats:**

Reverb and chorus configs share a common 28-byte header (first 14 word pairs) starting with `0x00C8 0x0880 0x1300 0x0B00 0x0028 0x9415 0x0212...`, suggesting a common DSP state initialization structure where effect-specific parameters follow.

The `DSP_DispatchCommand` function (0x036A2E) routes commands to DSP1 (`DSP_Send_Command`) or DSP2 (`DSP2_Send_Command`) based on the chip number in BC. DSP1 bytes go through the PZ/P7 handshake; DSP2 bytes are bit-banged on PF.0/PF.2 with no ready poll.

### DSP Boot Sequence (MAME Dynamic Trace)

The following sequence was captured from MAME emulation during the first 60 seconds of boot. All DSP1 activity occurs via the parallel port (CMD 0x01); no CMD 0x30 register writes target DSP1 during boot (DSP2 receives CMD 0x30 writes for addr 0xD0, 0xD3, 0xF6, 0x3C).

```
Phase 1 — Hardware Init:
  DSP2: REG WRITE addr=0xD0 value=0x0000
  DSP2: REG WRITE addr=0xD3 value=0x0000
  DSP1: INIT CONFIG [0xFB 0xDA 0x3F 0xA0 0x1A]  (CMD 0x04, 5 bytes)
  DSP1: STATUS/MODE value=0x003C                  (CMD 0x09)
  DSP1: CONTROL [0x00 0x55 0x55]                  (CMD 0x0C)

Phase 2 — DSP Program Loading (CMD 0x01, bytecode):
  DSP1: PROGRAM module=0x3C (117 bytes)   — AlgoChange_Init bytecode
  DSP1: RESET × 2, SYNC
  DSP1: coefficient clear (ch1, @0x06/@0x86 = 0)
  DSP1: COEFF UPLOAD @0x50 (92 bytes) — lookup table A
  DSP1: COEFF UPLOAD @0x6E (92 bytes) — lookup table B
  DSP1: COEFF UPLOAD @0x8C (2 bytes)  — table terminator

Phase 3 — DSP2 Enable:
  DSP2: REG WRITE addr=0xD0 value=0x4000
  DSP2: REG WRITE addr=0xF6 value=0x4FB0

Phase 4 — Effect Configuration:
  DSP1: PROGRAM module=0x00 (302 bytes) — EFF header (main program)
  DSP1: PROGRAM module=0x47 (7 bytes)   — config patch A
  DSP1: PROGRAM module=0x40 (7 bytes)   — config patch B
  DSP1: second INIT CONFIG [0xFB 0xDA 0x00 0xA0 0x1A]
  DSP2: REG WRITE addr=0x3C value=0x4000
  DSP1: second STATUS/MODE value=0x003C

Phase 5 — Effect Algorithm Loading:
  DSP1: PROGRAM module=0x00 (302 bytes) — EFF header (repeated)
  DSP1: PROGRAM module=0x47 (7 bytes)
  DSP1: PROGRAM module=0xC8 (667 bytes) — reverb algorithm bytecode
    → Heavy coefficient upload: 30 blocks, many with 4-coeff groups
    → Addresses: @0xD0, @0x85, @0x94, @0x87, @0x8A (init zeros)
    → then @0x00-0x3D (26 coefficient pairs — delay line taps)
    → @0x1E (master reverb level = 32767 = 0x7FFF)
    → @0x90, @0xAE (lookup tables)
    → @0x97, @0x9E-0xB2 (reverb tail coefficients)
    → @0x1D-0x3D (groups of 4: all-pass filter stages × 8)
    → @0x90 (final gain = 103268)
  DSP1: PROGRAM module=0x00 (302 bytes) — third EFF header
  DSP1: PROGRAM module=0x40 (7 bytes)
  DSP1: PROGRAM module=0x54 (352 bytes) — chorus/modulation algorithm
    → Coefficient upload: @0x07-0x0E (zeros), @0x26 (10 delay params)
    → @0x00 table upload (62 bytes), @0x09/@0x0A (LFO rates)
    → @0x1D-0x3D (all-pass stages × 4)

Phase 6 — Final Configuration:
  DSP1: PROGRAM module=0x47 (7 bytes)   — updated config patch
  DSP1: PROGRAM module=0x40 (7 bytes)   — updated config patch
  DSP1: coefficient write @0x06 = 0, @0x86 = 101643 (dry/wet mix)
  DSP1: Memory-mapped register writes: ch0-ch3 param[0-7] = 0
  DSP1: ch0-ch3 config = 0x01 (enable all channels)
```

**Key findings from dynamic trace:**
- The default boot effect is reverb on channel 1 with coefficients loaded at DSP internal addresses 0x00-0xB2
- All coefficient uploads target channel 1 (base 0x60); channels 0, 2, 3 receive only parameter clears
- The coefficient data structure matches a late-reflection reverb: 8 all-pass filter stages (addresses 0x1D-0x3D in groups of 4), 26 delay line taps (0x00+ sequence), and lookup tables (0x90, 0xAE)
- DSP program module indices: 0x00=EFF header, 0x3C=init, 0x40/0x47=patches, 0x54=chorus, 0xC8=reverb
- The INIT CONFIG byte[2] changes from 0x3F (init mode) to 0x00 (run mode) between phases

### DSP2 Register Map (CMD 0x30 Writes)

The MN19413 (DSP2) receives register writes via CMD 0x30 + 4-byte groups `[0x00, addr, val_hi, val_lo]`. During the first 60 seconds of boot, 679 writes target 112 unique register addresses across the full 0x00-0xFF range.

**Initialization Registers (written first):**

| Order | Address | Value | Function |
|-------|---------|-------|----------|
| 1 | 0xD0 | 0x0000 | Reset/control (cleared on init) |
| 2 | 0xD3 | 0x0000 | Reset/control (cleared on init) |
| 3 | 0xD0 | 0x4000 | Enable (set during Phase 3) |
| 4 | 0x3C | 0x4000 | Master enable (set during Phase 4) |

REG[0xD0] and REG[0xD3] are cleared first, then 0xD0 is set to 0x4000 to enable the DSP. REG[0x3C] = 0x4000 appears to be a master configuration enable.

**Channel Registers (stride 0x10, offset 0x_8 — 16 channels):**

All 16 addresses at offset 0x_8 (0x08, 0x18, 0x28, ... 0xF8) are written during boot. Initial values suggest delay line tap positions:

| Channel | Address | Init Value | Final Value | Writes |
|---------|---------|-----------|-------------|--------|
| 0 | 0x08 | 0x02F6 | 0x02F6 | 1 |
| 1 | 0x18 | 0x3FC0 | 0x860C | 3 |
| 2 | 0x28 | 0x2FD0 | 0x0014 | 3 |
| 3 | 0x38 | 0x1FE0 | 0x0093 | 9 |
| 4 | 0x48 | 0x0FF0 | 0x0FF0 | 1 |
| 5 | 0x58 | 0x0093 | 0x0093 | 1 |
| 6 | 0x68 | 0x4510 | 0x4510 | 1 |
| 7 | 0x78 | 0x00E3 | 0x8001 | 5 |
| 8 | 0x88 | 0x2530 | 0x0203 | 15 |
| 9 | 0x98 | 0x1540 | 0x1540 | 1 |
| 10 | 0xA8 | 0x8092 | 0x0077 | 3 |
| 11 | 0xB8 | 0x4A60 | 0xCC18 | 3 |
| 12 | 0xC8 | 0x3A70 | 0x3A70 | 1 |
| 13 | 0xD8 | 0x8002 | 0x2A80 | 3 |
| 14 | 0xE8 | 0x0000 | 0x1A90 | 2 |
| 15 | 0xF8 | 0x0AA0 | 0xD230 | 2 |

**High-Traffic Registers (control/routing):**

| Address | Writes | Unique Values | Function Hypothesis |
|---------|--------|---------------|---------------------|
| 0x40 | 107 | 32 | Primary control/routing register |
| 0x00 | 87 | 47 | Secondary control/routing register |
| 0x80 | 86 | 26 | Tertiary control/routing register |
| 0x89 | 29 | 4 | Effect parameter A |
| 0xA9 | 29 | 9 | Effect parameter B |
| 0x02 | 26 | 11 | Algorithm/mode selector |
| 0x81 | 17 | 4 | Effect parameter C |
| 0xA1 | 16 | 2 | Effect parameter D |
| 0x88 | 15 | 3 | Channel 8 config (also 0x_8 family) |
| 0x04 | 13 | 8 | Configuration register |
| 0x42 | 11 | 8 | Routing configuration |

REG[0x00], REG[0x40], and REG[0x80] are the most-written addresses, each receiving 80+ writes with dozens of unique values. These likely serve as command/data ports for a secondary register-indirect interface within the DSP.

**Coefficient Registers (monotonically incrementing):**

| Address | Values | Range | Avg Step |
|---------|--------|-------|----------|
| 0xE6 | 7 | 0x7C13 - 0x7CCD | 31.0 |
| 0xE7 | 8 | 0x7405 - 0x74E7 | 32.3 |

These registers receive steadily increasing values, consistent with filter coefficient ramp tables or LFO modulation parameters.

**Common Value Patterns:**

| Value | Registers Hit | Possible Meaning |
|-------|---------------|------------------|
| 0x8002 | 18 registers | Enable flag (type 2) |
| 0x8001 | 12 registers | Enable flag (type 1) |
| 0x0093 | 9 registers | Bypass/mute or default coefficient |
| 0xD003 | 6 registers | Routing/connection descriptor |
| 0x4000 | 13 registers | Master enable or half-scale coefficient |
| 0x0203 | 6 registers | Status/mode flag |

The pattern of 0x80xx values written to many registers suggests a register format where bit 15 is an enable/valid flag and the lower bits encode type or parameter data.

### DSP Effect Types and Algorithm Mapping

⚠ **Retracted (2026-10).** Earlier revisions mapped 40 effect indices to algorithm types 2-11 through a lookup table at SubCPU ROM 0x01F596. No such table exists. 0x01F596 is byte 88 of `ToneGen_Velocity_Output_Curve` (0x01F53E-0x01F63D, the keybed touch-to-velocity curve, read only by `Keybed_Decode_Event`), and nothing in the payload references 0x01F596. The values were that curve's ramp. Effect numbers 0-99 index the per-effect pointer arrays directly; see [DSP Effect Data Zone]({{ site.baseurl }}/dsp-effect-data-zone/).

**Effect Parameter Names** (stored at MainCPU 0xE324C4, colon-delimited 16-char fields):

Each effect has up to 8 adjustable parameters selected from a shared pool of 84 parameter names. Key parameters include: VOLUME, DEPTH, LFO SPEED, RESONANCE, MANUAL, REVERB TIME, PRE DELAY, HIGH DAMP GAIN, ER.LEVEL, FEEDBACK L/R, DELAY L/R, THRESHOLD, RATIO, ATTACK/RELEASE SENS/RATE, GATE TIME.

**Algorithm Selection Mechanism:**

The MainCPU sends the effect index (0-39) to the SubCPU (cmd 0x4D8C, category 0xE3). ⚠ This
page used to name the sending routine `Audio_SendCommand`; that symbol does not exist any
more — it was renamed `Sprintf_Locked` in March 2026 (`b5d34b75`) once it was shown to be a
general sprintf()-style formatter, called from 128+ sites across MIDI, sequencer and demo
code, not an audio-specific command interface. Which routine actually performs *this*
send has not been re-verified; treat the sender's identity as unconfirmed pending that
work. The SubCPU's `DSP_Cmd2B_AlgoSelect` handler (sub-command 0x00) receives this index, passes payload[0] to `DSP_AlgoSelect`, which rejects values >= 40 (`DSP_WriteAlgoBuffer`'s header calls this a DSP slot index, 0-39), initializes the voice structure (287 bytes per slot, base 0x041368, stride 0x11F), then uploads the appropriate DSP program modules and coefficient data to DSP1.

The algo type is stored at offset 0x5D of the voice structure. The full byte encodes both the algo type (lower nibble) and additional routing state (upper nibble). For example, 0x93 = algo type 3 with upper state 9, 0x25 = algo type 5 with upper state 2.

The SubCPU maintains up to 26 voice slots. At boot, the default configuration loads reverb-type effects (algo byte low nibbles 3 and 5) on several slots, with DSP program modules 0xC8 (reverb) and 0x54 (chorus) uploaded to DSP1.

**Effect Name Table:** MainCPU ROM address 0xE32A7A contains 128 pointers, one per effect number (71 named, all within 0-99; the rest, including all of 100-127, are "----------" spares), to 16-character fixed-width effect name strings (padded with spaces).

### DSP1 Internal Address Map

The DSP1 coefficient address space is organized by algorithm type. Each coefficient is a 17-bit value encoded as `((B4>>7)&1) | (B3<<1) | (B2<<9)`. Addresses are per-channel (channel base: 0x40=ch0, 0x60=ch1, 0x80=ch2, 0xA0=ch3).

**Reverb Algorithm (module 0xC8, 667 bytes):**

| Address | Function | Boot Default |
|---------|----------|-------------|
| @0x00 | Delay line tap array (26 pairs = 52 coefficients) | 33268, 0, 41925, 32768, ... |
| @0x06 | Dry signal level | 0 (muted) |
| @0x1D-0x3D | All-pass filter bank (8 stages × 4 coefficients each) | Stage-specific values |
| @0x1E | Master reverb level | 32767 (0x7FFF = maximum) |
| @0x85-0x8A | Init registers | 0 (cleared) |
| @0x86 | Wet (reverb) output level | 101643 |
| @0x90 | Output gain | 103268 |
| @0x94 | Init register | 0 (cleared) |
| @0x97 | Reverb tail feedback coefficient | 63251 |
| @0x9E | Reverb tail filter coefficients (4 blocks) | 65566, 119222, 31803, 16916 |
| @0xB2 | Reverb tail final coefficient | 51634 |
| @0xD0 | Init block | 0 (cleared) |

**Chorus/Modulation Algorithm (module 0x54, 352 bytes):**

| Address | Function | Boot Default |
|---------|----------|-------------|
| @0x00 | LFO waveform table (62 bytes via CMD 0x02) | Sine/triangle LUT |
| @0x05-0x10 | Init registers | 0 (cleared) |
| @0x09 | LFO rate A | — |
| @0x0A | LFO rate B / depth | — |
| @0x1D-0x29 | All-pass filter bank (4 stages × 4 coefficients) | Stage-specific |
| @0x26 | Delay parameters (10 coefficients) | 400, 4161, ... |

**Hypothesized Parameter ↔ DSP Address Mapping:**

| UI Parameter | DSP Address(es) | Notes |
|-------------|----------------|-------|
| REVERB TIME | @0x1D-0x3D | All-pass filter coefficients control decay time |
| PRE DELAY | @0x00 array | Delay line tap positions set initial reflection gap |
| HIGH DAMP GAIN | @0x9E | Tail filter coefficients control high-frequency damping |
| ER.LEVEL | @0x1E or @0x90 | Early reflection / output gain level |
| DRY/WET | @0x06 / @0x86 | Dry = 0 (muted), Wet = 101643 (full reverb) |
| LFO SPEED | @0x09, @0x0A | Chorus LFO rate registers |
| DEPTH | @0x26 | Chorus delay modulation depth |

### DSP Voice Structure Layout

The SubCPU keeps one 287-byte (0x11F) record per part (MIDI channel 0-25) at DRAM 0x041368, the structure described under [Voice Parameter Structure](#voice-parameter-structure-287-bytes-per-midi-channel) (whose offsets count from +0x06). The effect-related fields below sit inside it. Fields discovered through MAME dynamic analysis:

| Offset      | Size | Field        | Description                                                               |
|-------------|------|--------------|---------------------------------------------------------------------------|
| +0x00       | 2    | flags        | Voice configuration flags                                                 |
| +0x06       | 3    | rom_ptr      | ROM data pointer (24-bit)                                                 |
| +0x0E       | 2    | config       | Configuration word                                                        |
| +0x13       | 1    | unknown      | Always 0x02 in active slots                                               |
| +0x18       | 1    | algo_related | Value matches algo type (5 for reverb)                                    |
| +0x19       | 1    | param_a      | First effect parameter (e.g., REVERB TIME=26, GATED=6)                    |
| +0x1A       | 1    | param_b      | Second parameter (usually 0)                                              |
| +0x1B       | 1    | param_c      | Third parameter (default 64 = 0x40)                                       |
| +0x1C       | 1    | param_d      | Fourth parameter (default 64 = 0x40)                                      |
| +0x1D-0x20  | 4    | params_e-h   | Parameters 5-8 (usually 0)                                                |
| +0x21       | 1    | enable       | Enable flag (1 = active)                                                  |
| +0x57       | 1    | routing      | Routing state (matches upper nibble of algo byte)                         |
| +0x5D       | 1    | algo_byte    | Algorithm: lower nibble = type, upper nibble = routing                    |
| +0x5E       | 1    | effect_idx   | Value seen in MAME traces; meaning not established (no ROM table maps it) |
| +0x6E-0x70  | 3    | cfg_ptr_1    | Configuration data pointer 1                                              |
| +0x71-0x86  |      | algo_data_1  | Algorithm-specific coefficient data block 1                               |
| +0x87       | 1    | block_flags  | Flags between data blocks                                                 |
| +0x90-0xB3  |      | algo_data_2  | Algorithm-specific coefficient data block 2                               |
| +0xB4-0xD0  |      | algo_data_3  | Algorithm-specific coefficient data block 3                               |
| +0xD1-0x100 |      | algo_data_4  | Algorithm-specific coefficient data block 4                               |

**Boot-time default voice slots (MAME 60s trace):**

| Slot | Algo Type | Routing | param_a | Description                        |
|------|-----------|---------|---------|------------------------------------|
| 2    | 3         | 9       | 6       | Gated reverb default               |
| 16   | 5         | 2       | 26      | Room reverb 1                      |
| 17   | 5         | 2       | 29      | Room reverb 1 (alt params)         |
| 18   | 3         | 9       | 6       | Gated reverb (duplicate of slot 2) |
| 21   | 3         | 9       | 6       | Gated reverb (duplicate of slot 2) |

### Effect Routing Configuration

⚠ Retracted: the table formerly given here, at 0x00F490, was a misaligned read of `Voice_PolyphonyLimits_Table` (0x00F48C, a per-part group id 0-3, indexed by part & 0x1F) running into `Voice_IndexMapping_Table`. It does not assign effects to routing groups.

## Keybed Architecture

The physical keyboard (keybed) connects **directly** to the tone generator IC303, NOT to the Sub CPU. IC303 performs hardware key scanning internally and presents note events to the Sub CPU via the keyboard input interface at 0x110000.

This means:
- The CPU does **not** scan the keyboard matrix
- IC303 scans the keys and reports a key index plus a raw touch reading; the Sub CPU curve-maps the reading into a velocity (`Keybed_Decode_Event`) and assigns tone-generator voices itself
- The Sub CPU simply reads completed note events from IC303's output register

See [Keybed Scanning]({{ site.baseurl }}/keybed-scanning/) for the complete note flow, encoding format, and voice slot management.

## MAME Emulation Status

*(⚠ re-checked 2026-09-01 against the overlay driver, `kn7000_mame/src/mame/matsushita/kn5000.cpp` — several claims below were stale.)*

None of this is in mainline MAME. Upstream `kn5000` maps, on the Sub CPU's bus, the tone generator (0x100000), keybed (0x110000), DSP1 (0x130000) and waveform RAM (0x1E0000) as `noprw` stubs and is flagged `MACHINE_NOT_WORKING | MACHINE_NO_SOUND`. Everything below describes the kn7000_mame overlay build.

The MAME driver includes device classes for the audio chips. The tone generator produces basic audio output (waveform playback from ROM). **DSP1 (IC311) now has a real device (`upd6383_device`)** behind a compile-time switch (`KN5000_ENABLE_DSP1`, off by default): its host interface is exercised and uploaded microcode is verified to land in the chip's I-RAM; its instruction set is partly decoded (80.8 % of distinct microcode words, pooled over the KN5000 and the SX-WSA1R; see [uPD6383 decode status]({{ site.baseurl }}/upd6383-decode-status/)) and the core can run, but its output is discarded. DSP2 (IC310) is still handled via SubCPU GPIO port callbacks rather than a dedicated device — and per the driver's own hardware notes, IC310, not IC311, is the chip the main audio mix actually passes through (IC303 SDO0 → IC310 → IC313 PCM69AU), which is why DSP1 being silent does not mute the instrument.

### Audio Chip Device Classes

| Device         | Chip          | IC    | Interface                      | MAME Class                                                               | Status                                                                                                          |
|----------------|---------------|-------|--------------------------------|--------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| Tone Generator | TC183C230002  | IC303 | Memory-mapped (0x100000)       | `kn5000_tonegen_device`                                                  | 64-voice PCM with pitch/pan/volume, keybed input, voice status readback                                         |
| DSP1           | uPD6383GF-3BA | IC311 | Parallel Port PZ/P7 (`host_w`) | `upd6383_device` (`m_dsp1`), optional, `KN5000_ENABLE_DSP1=0` by default | Partial core: host interface, I-RAM upload and decoded words run; output discarded. HLE effects via `DSPHLE`    |
| DSP2           | MN19413       | IC310 | Serial (GPIO bit-bang)         | (port callbacks)                                                         | Not yet a separate device; serial protocol handled by SubCPU GPIO; this is the chip the main mix passes through |

**Tone Generator (`kn5000_tonegen_device`):**
- Register-indirect config interface (address port + data port)
- 64-voice PCM wavetable playback at 48kHz from waveform ROMs (IC304-IC307)
- Waveform selection from `+0x040` (reg[1]) alone: `bank = bits[15:14]` (1 = IC307, the one
  hardware-rooted dump), `page = bits[13:12]`, `chunk = bits[11:0]` — a plain 0-based index
  into that 1 MB page's own self-delimiting directory
- Pitch: the played note (recovered from the key-bed/MIDI event that caused the voice) plus
  the transpose/detune the `+0x400` (reg[8]) log-pitch register carries, resampling the
  recording's measured fundamental to the target frequency
- Loudness: a per-sample amplitude EG. By default (since 2026-08-06, kn7000_mame `cb1c144`) the level code L renders as linear gain `L/255` with `+0x080` as a per-voice output level: a provisional joint calibration. The derived log law `2^((L-255)/16)` is selectable with `KN5000_EGLAW=log`.
- Timbre: a per-voice low-pass filter whose cutoff is the 7-bit TVF parameter in `+0x100`
  (reg[4]), gated on bit 10 (the firmware's own "this word carries a computed cutoff" flag)
- Pan: stereo, from `+0x180` (reg[6]) bits [6:0]; 0x40 = centre
- KEY ON (0x8100) / KEY OFF (0x7E00), with a 100 ms hold after key-off
- Voice status: the status port reports the envelope-running latch; the per-voice readback
  reports KEY ON (0x8100) while a key is held or within 100 ms of key-off
- Keyboard input interface with `push_keybed_event()` for MAME input port integration

**DSP1 (`upd6383_device`, member `m_dsp1`, optional and `set_disable()`d by default):**
- The real device's host interface is the parallel Port PZ/P7 handshake (`host_w`), not a
  memory-mapped port; I-RAM, C-RAM and D-RAM are mapped by the device itself, and only the
  external digital-delay DRAM (IC309) is the driver's to map.
- Held disabled on purpose: uploaded microcode is captured into a real, debugger-visible
  I-RAM, but the instruction set is only partly decoded, so the core's output is discarded —
  a partially-correct effects DSP was exactly the failure mode that produced
  audible-but-wrong sound on the KN7000.
- The **separate** 0x130000/0x130002 register block described above (`dsp_reg_addr_w` /
  `dsp_reg_data_w` / `dsp_reg_data_r` on `kn5000_state`, not on the DSP device) is a
  read-back model only; an earlier driver revision wrongly modelled it as the DSP's
  command/data port, which is why an upload capture hooked there saw nothing but zeros.

**DSP2 (MN19413 — not yet a MAME device):**
- Serial interface via SubCPU GPIO (Port PF bit 0 = SDA, bit 2 = SCLK, PE.6 = CS)
- 9-bit serial transactions (MSB-first), bit-bang protocol
- CMD 0x30 register writes: 4-byte groups [0x00, addr, val_hi, val_lo]
- Boot writes: REG[0xD0]=0, REG[0xD3]=0, REG[0x3C]=0x4000
- Future work: create separate device class for serial protocol decoding

### Key Emulation Challenges

1. **The uPD6383GF's instruction set is only partly decoded (80.8 %)** — this is the actual blocker, not a missing ROM dump. The bytecode the Sub CPU uploads to IC311 is Sub-CPU ROM content and is fully carved (see the [DSP Effect Data Zone]({{ site.baseurl }}/dsp-effect-data-zone/)); what remains unknown is the rest of what the chip's own core does when it executes that upload. IC310 (MN19413) is a separate, undocumented custom ASIC with no public programming information at all.
2. **Tone generator wavetable ROM — largely solved.** IC307 (one of the four wave ROMs IC304-IC307 that hang off IC303) is a hardware-rooted dump and is already used for 64-voice PCM playback (see "Tone Generator" above and [Waveform ROM Format]({{ site.baseurl }}/waveform-rom-format/)). IC304-IC306 are currently `BAD_DUMP` copies of IC307, not independent dumps, so waveform *selection* across banks is not yet faithful even though single-bank playback works.
3. **Serial port 1** is the Computer Interface (TO HOST) link, not part of the audio path; see [Serial Port 1 Interface](#serial-port-1-interface). The DAC (IC313) is fed by IC310's serial outputs.

### What Works Now

- SubCPU firmware loads and executes (192KB payload transfer via HDMA)
- All inter-CPU audio commands (0x2D DSP config, 0x2B sound name query, etc.) are dispatched correctly
- DSP state dispatcher runs all 11 sub-routines, generating complete register write sequences
- Effect configurations flow from MainCPU → SubCPU → DSP device stubs
- Keybed input from MAME input ports reaches the tone generator device
- SubCPU Serial Port 1 (Computer Interface) wired with UART byte decoder and logging

### Known Issues

- **Feature Demo timing** — the HLE keeps a released voice reported active for 100 ms (4,800 samples) so the firmware's per-tick status polls see it; whether this matches real envelope times is not measured.
- **DSP effects audio is opt-in** — the default build has none. In a `KN5000_ENABLE_DSP1=1` build, the `DSPHLE` configuration option (default Off) makes 34 effect settings audible as high-level reconstructions from the decoded C-RAM ([Effects DSP]({{ site.baseurl }}/effects-dsp/) §9-§21). The `DSPCFG` option runs the decoded microcode on the low-level core, but its output is discarded; a further speculative-ISA setting runs guessed semantics, and its output is not known to be right. DSP2 (IC310) has no device. The tone generator plays real PCM from IC307; a diagnostic sine mode is selectable through the `:TGMODE` port.

## Research Needed

- [x] ~~Document waveform ROM format and sample layout~~ -- Complete: IC307 analyzed. 198-entry index table, 186 unique signed 16-bit PCM waveforms, x16 byte offset addressing, key zone parameter records. See [Waveform ROM Format]({{ site.baseurl }}/waveform-rom-format/)
- [x] ~~Decode per-algorithm parameter mapping tables at `0x1F22C`/`0x1F09C`~~ — Complete: both are 100-entry pointer arrays indexed by effect number: 0x1F09C points to value records (translator opstreams ending 0x7A) and 0x1F22C to descriptor records (register-cell lists), each table ending in 0xF0
- [x] ~~Map MainCPU parameter indices to EFF block word positions~~ — Partial: 84 named parameters extracted from MainCPU 0xE324C4. DSP2 master list at 0xE4475C maps 14 SubCPU param indices to UI names. Final register-to-parameter mapping requires runtime bytecode tracing
- [x] ~~Decode DSP register semantics per channel~~ — Partial: DSP2 112-register map from boot-time analysis (stride-0x10 channel regs at offset 0x_8, control regs 0x00/0x40/0x80, coefficient regs 0xE6/0xE7). DSP1 channel regs 0x10-0x17 still need semantic mapping.
- [ ] Document remaining inter-CPU command types (beyond 0x2D and 0xE1/E2/E3)
- [x] ~~Investigate why song engine never writes MIDI events to ring buffer~~ — resolved by the 2026-08-05 /INT0 fix (kn7000_mame 3fd44f3)
- [x] ~~Determine what sets the startup flag at 0x0251D8~~ — it is the presentation-loaded flag (EVT_EXIST/INIT/EXIT_PRESENTATION): `Seq_InitializeAndStart` sets it to 1 (fdemotext_routines.s:2921) and the MT_InitPresentation method clears it (file_demo_proc.s:159). The zero reading above is from the pre-2026-08-05 session.
- [ ] Trace the path from rhythm ROM pattern data to ring buffer write calls — partially addressed by Feature Demo analysis
- [ ] Decode voice parameter template at ROM 0xF8D5 (34 words — which map to pitch, waveform select, envelope mode, etc.)
- [x] ~~Investigate why Feature Demo sequencer never reaches Note On events~~ — Ring buffer at 0x01F37B is never written; sequencer dispatcher and rhythm ROM reading work correctly but event generation stage never fires
- [x] ~~Identify the timing mechanism or subcpu response that advances the sequencer~~ — Partially resolved: Timer7, state machine, and dispatcher pipeline traced; the issue is in the song engine output stage, not the input/timing stage
- [x] ~~Identify exact device on Serial Port 1~~ — Computer Interface (TO HOST connector), sends 0xFE Active Sensing
- [x] ~~Analyze DSP1/DSP2 command sets~~ — Partial: 4 commands identified, preset structure decoded
- [x] ~~Extract effect type names from ROM~~ — Complete: 71 named effect types at MainCPU 0xE32A7A
- [x] ~~Extract effect parameter names from ROM~~ — Complete: 84 parameter names at MainCPU 0xE324C4
- [x] ~~Document DSP state dispatcher architecture~~ — Complete: `DSP_State_Dispatcher` and 11 sub-routines traced
- [x] ~~Trace inter-CPU command 0x2D protocol~~ — Complete: 4-layer protocol fully documented
- [x] ~~Map effect type indices to DSP register configurations~~ — Partial: translation chain traced through `DSP_WriteParameter` → `DSP_ParameterWriteEngine`, but per-algorithm ROM tables not yet decoded
- [x] ~~Determine if DSP microcode is loaded from ROM~~ — **Yes.** The Sub CPU uploads IC311 and IC310 microcode from its own ROM through the bytecode interpreter (see [DSP Firmware / Microcode Loading](#dsp-firmware--microcode-loading) above)
- [x] ~~Map remaining proprietary CC handlers (0x97-0x9D)~~ — Storage traced (see Proprietary Control Changes); meanings open
- [x] ~~Decode tone generator register semantics~~ — Partial: voice control state machine, key-on/off flags, volume/level groups, latched parameter updates documented; pitch/envelope/filter register mapping still needs work
- [x] ~~Document synthesis architecture~~ — Complete: 64-voice wavetable, 26 MIDI channels, dynamic voice allocation, hardware ADSR, LFO modes, proprietary CCs
- [ ] Reverse-engineer DSP register semantics by runtime bytecode tracing — static analysis decoded all table structures (6 ROM tables, 59 distinct coefficient streams, 100 algorithm entries) but actual register addresses are embedded in variable-length bytecode and require interpreter execution to extract
- [x] ~~Analyze the native code handlers (DSP_Bytecode_Op00 … Op05)~~ — **Fully decoded** (1,613 bytes → 6 handlers). Op0/5: complex 5-byte groups with 3-way branching (static/raw/parameter-modified coefficients). Op1: 5-byte groups with 12-bit address. Op2: 3-byte raw groups. Op3: 16-bit address + raw tail. Op4: command-only. Key finding: Handlers 0/5 Branch C implement real-time parameter control by mixing a 32-bit runtime parameter into template coefficient data during DSP writes.
- [x] ~~Document bytecode interpreter opcode set completely (opcodes 0x0-0xF)~~ — Complete: 2-byte header format, opcodes 0-5 (native code dispatch), 0xD (yield), 0xE (send command+data), 0xF (end). Config entries are 12 bytes (4 words + 1 pointer). The handlers, `DSP_Bytecode_Op00_Groups5_ParamMix` (0x3C32E) through `DSP_Bytecode_Op05_Groups5_Masked`, are native TLCS-900 subroutines.
