---
layout: page
title: Inter-CPU Protocol
permalink: /inter-cpu-protocol/
---

# Inter-CPU Protocol

The KN5000 uses two TMP94C241F CPUs that communicate via a pair of memory-mapped latches — mapped at 0x140000 on the Main CPU's bus and at 0x120000 on the Sub CPU's bus (confirmed by the MAME driver's address maps in `kn5000.cpp`; on the Main CPU, 0x120000 is unrelated floppy-DMA hardware). The Main CPU handles UI, MIDI, and control while the Sub CPU handles all audio generation.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        MAIN CPU (TMP94C241F)                          │
│                                                                       │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐   │
│  │ Audio_Lock_     │    │ Audio_DMA_      │    │ Audio_Lock_     │   │
│  │ Acquire         │───>│ Transfer        │───>│ Release         │   │
│  │ (0xEF1FEE)      │    │ (0xEF341B)      │    │ (0xEF1F0F)      │   │
│  └─────────────────┘    └────────┬────────┘    └─────────────────┘   │
│                                  │                                    │
│         Lock counter at (0x0532 + lock_index)                         │
│         Linked list of waiting requests at 0x0487                     │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   v
                    ┌──────────────────────────┐
                    │         LATCH            │
                    │  0x140000 (Main CPU)     │
                    │  0x120000 (Sub CPU)      │
                    │  Bidirectional Data      │
                    │  DMA-capable transfer    │
                    └──────────────────────────┘
                                   │
                                   v
┌──────────────────────────────────────────────────────────────────────┐
│                        SUB CPU (TMP94C241F)                           │
│                                                                       │
│  ┌──────────────────┐    ┌──────────────────┐    ┌────────────────┐  │
│  │ InterCPU_Latch_  │    │ MicroDMA CH0/2   │    │ CMD_DISPATCH_  │  │
│  │ Setup (0x020C15) │───>│ Handlers         │───>│ TABLE          │  │
│  └──────────────────┘    └──────────────────┘    └────────────────┘  │
│                                                          │            │
│                          ┌───────────────────────────────┘            │
│                          v                                            │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                    COMMAND HANDLERS                             │  │
│  │                                                                │  │
│  │  0x00-0x1F: Audio_CmdHandler_00_1F (MIDI/notes → 0x2B0D)      │  │
│  │  0x20-0x3F: Audio_CmdHandler_20_3F (Stub)                     │  │
│  │  0x40-0x5F: Audio_CmdHandler_40_5F (...)                       │  │
│  │  0x60-0x7F: Audio_CmdHandler_60_7F (Audio/DSP → 0x3B60)      │  │
│  │  0x80-0x9F: Serial port setup (38400 baud)                    │  │
│  │  0xA0-0xBF: Audio_CmdHandler_A0_BF (System audio)             │  │
│  │  0xC0-0xFF: Audio_CmdHandler_C0_FF (Extended system)          │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

## Main CPU: Sending Commands

### Lock Mechanism

The Main CPU uses a semaphore system to serialize access to the inter-CPU latch. The two
routines are the multitasking kernel's **generic** semaphore P/V: `Audio_Lock_Release` is a byte
twin of the sub CPU's `TaskSem_Release`, and the "lock index" is a semaphore number. The names
are historical; see [CPU Subsystem]({{ site.baseurl }}/cpu-subsystem/#the-two-kn5000-cpus-share-kernel-code-byte-for-byte).

```asm
; Acquire lock before sending
    LD A, lock_index        ; Lock index 0-7
    CALL Audio_Lock_Acquire ; Decrements counter, waits if busy

; ... send audio commands via DMA ...

; Release lock when done
    LD A, lock_index
    CALL Audio_Lock_Release ; Increments counter, signals waiters
```

**Lock Variables:**
- Counter: `(0x0532 + lock_index)` - Decremented on acquire, incremented on release
- Wait List: `0x0487` - Linked list of pending requests

### DMA Transfer

The `Audio_DMA_Transfer` routine handles bulk data transfer:

```asm
Audio_DMA_Transfer:
    ; Data pointer at 0x05DA
    ; Byte count at 0x05DE
    ; Transfers in chunks to latch at 0x140000
```

**Transfer Variables:**
- Data Pointer: 0x05DA (XWA)
- Byte Count: 0x05DE (16-bit)
- Completion Flag: 0x05E0

## Sub CPU: Receiving Commands

### Interrupt Configuration

The `InterCPU_Latch_Setup` routine (0x020C15) configures the Sub CPU's interrupt controller for inter-CPU DMA reception:

```asm
InterCPU_Latch_Setup:
    LD (INTETC01), 005h    ; INTTC0 level = 5 (DMA ch0 completion)
    LD (INTETC23), 005h    ; INTTC2 level = 5 (DMA ch2 completion)
    LD (INTE0AD), 001h     ; INT0 level = 1 (latch data pending)
```

**Interrupt Priority Hierarchy:**

| Interrupt | Level | Source | Purpose |
|-----------|-------|--------|---------|
| INT0 | 1 | Latch data_pending callback | New command byte available |
| INTTC0 | 5 | HDMA ch0 transfer complete | Command payload received |
| INTTC2 | 5 | HDMA ch2 transfer complete | Response data sent |

The firmware normally runs with `EI 6` (IFF=6), which means only level 6+ interrupts are accepted. Since INT0 is at level 1, it only fires during brief `EI 0` windows. INTTC0/INTTC2 at level 5 are also normally masked — they fire during EI 0 windows or when the ISR handler lowers IFF.

**INT0 Detection Mode:**

The Sub CPU configures INT0 as **level-triggered** (IIMC bit 1 = 0). This means the interrupt flag is asserted whenever the latch `data_pending` signal is high, and deasserted when the latch is read (clearing `data_pending`).

### HDMA-Based Command Reception Flow

The complete flow for receiving a command from the Main CPU involves three interrupt sources working in sequence:

```
Main CPU writes command byte to latch (0x140000)
    │
    v
generic_latch data_pending → set_input_line(INT0, ASSERT)
    │
    v
┌──────────────────────────────────────────────────┐
│  INT0 ISR (INT0_HANDLER at 0x020E86)             │
│                                                   │
│  1. Read command byte from latch (0x120000)       │
│     → This clears data_pending → deasserts INT0   │
│                                                   │
│  2. Decode command type:                          │
│     - E1: DMAD0=0x1116, DMAC0=6                  │
│     - E2: DMAD0=0x111C, DMAC0=10                 │
│     - E3: Set PAYLOAD_LOADED_FLAG, return         │
│     - Standard (0x00-0xDF):                       │
│       DMAD0=0x10F0, DMAC0=(byte & 0x1F)+1        │
│                                                   │
│  3. Write DMA0V = 0x0A (INT0 vector)              │
│     → Configures HDMA ch0 to steal future INT0    │
│       triggers for automatic byte-by-byte xfer    │
│                                                   │
│  4. Return from interrupt                         │
└──────────────────────────────────────────────────┘
    │
    v
Main CPU writes data bytes to latch (one at a time)
    │
    v
Each data_pending → INT0 flag set → HDMA ch0 steals it
    (HDMA has priority over ISR dispatch)
    │
    v
HDMA ch0 transfers: latch (DMAS0) → DMAD0++
    DMAC0 decremented each transfer
    │
    v
When DMAC0 reaches 0:
    │
    v
┌──────────────────────────────────────────────────┐
│  INTTC0 ISR (MICRODMA_CH0_HANDLER at 0x020F1F)  │
│                                                   │
│  1. DMA0V cleared automatically (HDMA disabled)   │
│                                                   │
│  2. Dispatch based on CMD_PROCESSING_STATE:       │
│     - State 0: Standard command → dispatch via    │
│       CMD_DISPATCH_TABLE (upper 3 bits)           │
│     - State 2: E1 phase 1 → set up phase 2       │
│     - State 3: E2 processing → handle ext. cmd    │
│                                                   │
│  3. Process command data from receive buffer      │
└──────────────────────────────────────────────────┘
```

**Key design insight:** The INT0 ISR only fires for the **first byte** (the command header). After that, HDMA ch0 takes over and silently transfers remaining bytes without CPU intervention. The ISR configures `DMA0V = 0x0A` (INT0's DMA start vector) so that subsequent INT0 flag assertions trigger HDMA instead of the ISR.

### MicroDMA Handlers

| Handler | Channel | Purpose |
|---------|---------|---------|
| `MICRODMA_CH0_HANDLER` | CH0 | Command payload reception (triggered by INTTC0) |
| `MICRODMA_CH2_HANDLER` | CH2 | Response data transmission (triggered by INTTC2) |

### Command Dispatch

Commands are dispatched based on upper 3 bits of the command byte:

```asm
CMD_DISPATCH_TABLE:                         ; Address: 0x00F46C
    dd Audio_CmdHandler_00_1F   ; 0x00-0x1F: MIDI/note commands → ring buffer at 0x2B0D
    dd Audio_CmdHandler_20_3F   ; 0x20-0x3F: Stub (returns 0)
    dd Audio_CmdHandler_40_5F   ; 0x40-0x5F: (line 9619)
    dd Audio_CmdHandler_60_7F   ; 0x60-0x7F: Audio/DSP commands → ring buffer at 0x3B60
    dd Serial1_DataTransmit_Loop ; 0x80-0x9F: Serial port 1 data
    dd Audio_CmdHandler_A0_BF   ; 0xA0-0xBF: (line 51502)
    dd Audio_CmdHandler_C0_FF   ; 0xC0-0xDF: (line 10951)
    dd Audio_CmdHandler_C0_FF   ; 0xE0-0xFF: Same as 0xC0-0xDF
```

## Audio Command Format

### Ring Buffer at 0x2B0D (MIDI/Note Commands)

Commands 0x00-0x1F write MIDI-like data to a 4KB ring buffer:

| Variable | Address | Description |
|----------|---------|-------------|
| Write Pointer | 0x2B0D | 12-bit circular index |
| Read Pointer | 0x2B0F | Current read position |
| Byte Count | 0x2B11 | Bytes available |
| Base Address | 0x2B13 | Buffer start |
| Buffer Data | +0x06 | 4KB circular buffer |

### Ring Buffer at 0x3B60 (DSP/Audio Config)

Commands 0x60-0x7F write audio config data to a 2KB ring buffer:

| Variable | Address | Description |
|----------|---------|-------------|
| Write Pointer | 0x3B60 | 11-bit circular index (wraps at 0x800) |
| (reserved) | 0x3B62 | Padding |
| Available Count | 0x3B64 | Bytes queued for processing |
| Buffer Base | 0x3B66 | 3-byte pointer to actual data area |

`Audio_Process_DSP` (called from main loop) reads commands from this buffer. The most important command is **0x2D** (DSP configuration change). See [Audio Subsystem — Command 0x2D Protocol]({{ site.baseurl }}/audio-subsystem/#inter-cpu-command-protocol-command-0x2d--dsp-configuration) for the full 4-layer protocol.

### Command Byte Format

The command byte sent to the latch encodes both the handler index and payload length:

```
Bits 7-5: Handler index (0-7) → selects CMD_DISPATCH_TABLE entry
Bits 4-0: Payload length - 1 (0-31 = 1 to 32 bytes)

Examples:
  0x02 = Handler 0 (MIDI), 3 bytes   → Note On/Off or Control Change
  0x01 = Handler 0 (MIDI), 2 bytes   → Program Change
  0x7F = Handler 3 (DSP config), 32 bytes
```

Special command bytes bypass this encoding:
- `0xE1`: Bulk transfer setup (6 bytes: dest_addr[4] + count[2])
- `0xE2`: Extended parameter block (10 bytes)
- `0xE3`: Payload ready signal (no data, sets boot flag)

### MIDI Message Format (Ring Buffer at 0x2B0D)

The ring buffer contains standard MIDI messages parsed by `MIDI_Dispatch` (0x034D93):

| Status Byte | Length | Format | Handler |
|-------------|--------|--------|---------|
| 0x80-0x8F | 3 | `[0x8n] [note] [velocity]` | Note Off (→ `Voice_NoteOn` with vel=0) |
| 0x90-0x9F | 3 | `[0x9n] [note] [velocity]` | Note On (`Voice_NoteOn` at 0x2CF97) |
| 0xB0-0xBF | 3 | `[0xBn] [CC#] [value]` | Control Change (`Voice_CtrlChange` at 0x2A282) |
| 0xC0-0xCF | 2 | `[0xCn] [program]` | Program Change (`Voice_ProgChange` at 0x34A4A) |
| 0xD0-0xDF | 2 | `[0xDn] [pressure]` | Channel Pressure (`Voice_ChanPressure` at 0x2A4EA) |
| 0xE0-0xEF | 3 | `[0xEn] [LSB] [MSB]` | Pitch Bend (`Voice_PitchBend` at 0x2A5E6) |
| 0xF0-0xFF | var | `[0xF0] ... [0xF7]` | System Message (`Voice_SystemMsg` at 0x2A7AF) |

The channel number (`n`) is in the low nibble of the status byte (bits 3-0). The Sub CPU supports up to **26 channels** (0x00-0x19).

### Supported MIDI Control Changes

| CC# | Name | Description |
|-----|------|-------------|
| 0x01 | Mod Wheel | Modulation depth |
| 0x07 | Volume | Channel volume |
| 0x0A | Pan | Stereo position |
| 0x0B | Expression | Expression controller |
| 0x40 | Sustain | Sustain pedal (on/off) |
| 0x5B | Sostenuto | Sostenuto pedal |
| 0x5D | Soft | Soft pedal |
| 0x5E | Portamento | Portamento control |
| 0x78-0x81 | Extended | Proprietary extended functions (lookup table dispatch) |
| 0x91-0x9D | Effects | Proprietary effects depth control |

### Voice Processing

Note On processing (`Voice_NoteOn` at 0x2CF97):
1. Validates channel (must be < 0x1A = 26)
2. If velocity = 0: triggers note off (voice release)
3. If velocity > 0: allocates voice slot, sets pitch and velocity

Voice parameters are stored in per-channel structures of **287 bytes** each at base address `0x041381`:
```
channel_params[channel] = 0x041381 + channel * 0x11F
```

Pitch bend uses a **14-bit value** (MSB and LSB combined): `value = (MSB << 7) | LSB`, with bit 15 set as a sign marker.

## Sub CPU Response

The Sub CPU can send data back to the Main CPU via `InterCPU_DMA_Send`:

```asm
InterCPU_DMA_Send:
    ; Entry: XDE = source data pointer
    ;        BC = byte count
    ;        A = command/channel identifier

    ; Splits large transfers into 32-byte chunks
    ; Used by tone generator for status responses
```

## Boot Sequence Transfer

During boot, the Main CPU loads the 192KB Sub CPU payload:

1. Main CPU initializes DMA channels via `SubCPU_Init_DMA_Channels`
2. Main CPU writes payload in chunks to latch
3. Sub CPU's MicroDMA handler receives data
4. Sub CPU executes payload from internal RAM
5. Sub CPU enters `Audio_System_Init` and starts processing loop

## Code References

### Main CPU (`maincpu/kn5000_v10_program.asm`)

| Routine | Address | Description |
|---------|---------|-------------|
| `SubCPU_Init_DMA_Channels` | 0xEF329E | Initialize DMA channels for inter-CPU communication |
| `SubCPU_Send_Payload` | 0xEF068A | Transfer 192KB payload to Sub CPU |
| `InterCPU_E1_Bulk_Transfer` | 0xEF3457 | E1 two-phase bulk transfer protocol |
| `InterCPU_E2_Send` | 0xEF33AA | E2 extended transfer command |
| `InterCPU_Send_Data_Block` | 0xEF3345 | Send variable-length data packet |
| `Audio_DMA_Transfer` | 0xEF341B | Core DMA transfer routine |
| `Audio_Lock_Acquire` | 0xEF1FEE | Acquire communication lock |
| `Audio_Lock_Release` | 0xEF1F0F | Release communication lock |

### Sub CPU (`subcpu/kn5000_subprogram_v142.asm`)

| Routine | Address | Description |
|---------|---------|-------------|
| `InterCPU_Latch_Setup` | 0x020C15 | Configure DMA and interrupts |
| `InterCPU_DMA_Send` | 0x020C6B | Send data to Main CPU |
| `Audio_CmdHandler_00_1F` | 0x034D5F | Audio command handler |
| `MICRODMA_CH0_HANDLER` | 0x020F1F | DMA channel 0 interrupt |
| `MICRODMA_CH2_HANDLER` | 0x020F01 | DMA channel 2 interrupt |

## Related Pages

- [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) - Sound generation details
- [CPU Subsystem]({{ site.baseurl }}/cpu-subsystem/) - Both CPU specifications
- [Boot Sequence]({{ site.baseurl }}/boot-sequence/) - Startup process
- [System Overview]({{ site.baseurl }}/system-overview/) - Overall architecture

## Boot ROM Protocol (Sub CPU Side)

During boot, the Sub CPU boot ROM implements a DMA-based protocol for receiving the 192KB payload from the Main CPU.

### Boot ROM INT0 Handler (0xFF881F)

The Sub CPU boot ROM's INT0 handler processes commands from the latch:

```asm
InterCPU_RX_Handler:           ; 0xFF881F
    push XWA
    bit  2, (0x34)             ; Check busy flag
    jr   NZ, .exit
    ld   A, (0x120000)         ; Read command from latch
    ld   (0x051A), A           ; Store for processing
    cp   A, 0xE1               ; E1 command?
    jr   NZ, .check_e2
    ; ... set up DMA for 6-byte header ...
    jr   .done

.check_e2:
    cp   A, 0xE2               ; E2 command?
    jr   NZ, .check_e3
    ; ... set up DMA for 10-byte header ...
    jr   .done

.check_e3:
    cp   A, 0xE3               ; E3 command? (CRITICAL!)
    jr   NZ, .data_packet
    set  6, (0x04FE)           ; SET PAYLOAD_LOADED_FLAG bit 6!
    jr   .cleanup

.data_packet:
    ; Handle variable-length data packet
    ...

.cleanup:
    res  1, (0x34)             ; Clear handshake flag
.exit:
    pop  XWA
    reti
```

### E1/E2/E3 Command Protocol

| Command | Byte | Action | Data Size |
|---------|------|--------|-----------|
| E1 | 0xE1 | Bulk data transfer header | 6 bytes (dest addr + count) |
| E2 | 0xE2 | Extended transfer header | 10 bytes |
| E3 | 0xE3 | **Payload complete signal** | 0 bytes |
| Data | 0x00-0xDF | Data packet | Low 5 bits + 1 |

### PAYLOAD_LOADED_FLAG (0x04FE)

| Bit | Meaning |
|-----|---------|
| 6 | Payload ready - triggers `call 0x000400` in boot ROM main loop |
| 7 | Transfer active flag |

### Boot ROM Main Loop (0xFF840C)

```asm
Boot_Main_Loop:                ; 0xFF840C
    res  6, (0x04FE)           ; Clear payload-ready flag
.poll:
    bit  6, (0x04FE)           ; Check if payload ready
    jr   Z, .check_status
    ei   6                     ; Enable interrupts level 6
    call 0x000400              ; CALL PAYLOAD ENTRY POINT!
.check_status:
    ; Update SSTAT signals based on MSTAT
    ldcf 1, (0x30)             ; Read Port D bit 1
    ; ... process and update Port D ...
    jr   T, .poll              ; Loop forever
```

## Main CPU Payload Transfer

### SubCPU_Init_DMA_Channels (0xEF329E)

Configures MicroDMA channels for inter-CPU communication:

```asm
SubCPU_Init_DMA_Channels:      ; 0xEF329E
    ; Configure interrupt priorities
    AND  (INTET23), 0xF8
    RES  2, (T8RUN)
    ; ... more interrupt config ...

    ; Set DMA destination 2 to latch address
    LDA  XWA, INTER_CPU_COMM_LATCHES   ; 0x140000
    LDC_DMAD2_XWA

    ; Set DMA source 0 to latch address
    LDA  XWA, INTER_CPU_COMM_LATCHES
    LDC_DMAS0_XWA

    ; Clear state variables
    LD   (0x05E0), 0x00
    LD   (0x05E2), 0x00
    RET
```

### SubCPU_Send_Payload (0xEF068A)

Sends the 192KB payload to Sub CPU in chunks. This is the core routine for loading the Sub CPU firmware during boot.

> **See Also:**
> - [Boot Sequence: SubCPU_Send_Payload Details]({{ site.baseurl }}/boot-sequence/#subcpu_send_payload-details) - Transfer sequence table, timing, error handling
> - [LZSS Compression]({{ site.baseurl }}/lzss-compression/) - Optional preset data decompression

**Source:** `maincpu/kn5000_v10_program.asm:134212`

```asm
SubCPU_Send_Payload:           ; 0xEF068A
    PUSH XIZ
    CP   (0xFFFEEF), 0xFF      ; Check transfer enable flag
    JRL  NZ, .skip_transfer

    ; Initial timing delay (0x2000 iterations)
    LD   XIZ, 0
.delay_loop:
    INC  1, XIZ
    CP   XIZ, 0x2000
    JR   C, .delay_loop

    ; Send 64KB chunks from Table Data ROM (0x830000-0x870000)
    LD   XWA, 0x830000         ; Source: table_data + 0x30000
    LD   XBC, 0x10000          ; Count: 64KB
    LD   XDE, 0x050000         ; Dest: Sub CPU RAM
    CALL InterCPU_E1_Bulk_Transfer

    LD   XWA, 0x840000         ; Next 64KB
    LD   XBC, 0x10000
    LD   XDE, 0x060000
    CALL InterCPU_E1_Bulk_Transfer

    ; ... 3 more 64KB chunks (0x850000, 0x860000, 0x870000) ...

    ; Optional LZSS decompression from 0x3E0000
    CP   (0xFFFEED), 0xFF      ; Check decompression flag
    JR   Z, .skip_decompress
    CALL SLIDE_Parse_Header          ; Decompress SLIDE4K data
    ; ... copy decompressed data to Sub CPU ...

.skip_transfer:
    POP  XIZ
    RET
```

**Transfer Summary:**

| Chunk | Source | Sub CPU Dest | Size |
|-------|--------|--------------|------|
| 1-5 | 0x830000-0x870000 | 0x050000-0x090000 | 5 × 64KB | *(the [tone database]({{ site.baseurl }}/tone-database/) — data, not the Sub CPU executable)* |
| 6-8 | Decompressed/Fallback | 0x00F000-0x02F000 | 3 × 64KB |
| 9 | Buffer | 0x000400 | 256 bytes |

### InterCPU_E1_Bulk_Transfer (0xEF3457)

Implements the E1 two-phase transfer protocol:

```asm
InterCPU_E1_Bulk_Transfer:     ; 0xEF3457
    PUSH IZ
    ; Wait for previous transfer to complete
    ...

.wait_ready:
    BIT  3, (PZ)               ; Check SSTAT1 (Sub CPU ready)
    JRL  Z, .timeout

    ; Send E1 command
    RES  0, (PZ)               ; Clear MSTAT0
    LD   (0x05E0), 0x02        ; Set state = 2 (two-phase)
    LD   (INTER_CPU_COMM_LATCHES), 0xE1  ; Send E1 command!

.wait_ack:
    BIT  3, (PZ)               ; Wait for Sub CPU response
    JRL  NZ, .ack_timeout
    SET  0, (PZ)               ; Set MSTAT0

    ; Send 6-byte header (dest addr + byte count)
    LDA  XHL, 0x0608
    LD   (XHL), XWA            ; Store dest address
    LDA  XWA, 0x05D0
    LD   (XWA), XDE            ; Store source address
    LD   (XHL+4), BC           ; Store count
    LD   (XWA+4), BC
    LD   (0x05DA), XWA         ; Setup for Audio_DMA_Transfer
    LDW  (0x05DE), 0x0006      ; 6 bytes for header
    CALR Audio_DMA_Transfer    ; Send header

    ; Wait for phase 1 complete, then send actual data
    ...
    CALR Audio_DMA_Transfer    ; Send data

    POP  IZ
    RET
```

## Command 0x2B: Sound Name Query

The Main CPU uses command 0x2B to query the Sub CPU for the display name of the currently selected voice/sound in a given keyboard part. This is used to populate the on-screen voice name display.

### Request Format (10 bytes, Main CPU → Sub CPU)

| Offset | Value | Description |
|--------|-------|-------------|
| 0 | 0x2B | Command: sound/voice query |
| 1 | 0x30–0x3F | Voice slot (0x30 = slot 0, 0x3F = slot 15) |
| 2 | 0x7F | Parameter selector |
| 3 | 0x20 | Address/routing byte |
| 4–5 | 0x00 0x00 | Reserved |
| 6 | 0x02 | Sub-command group |
| 7 | 0x12–0x16 | Part identifier (see table below) |
| 8 | XX | Voice/sound index within bank |
| 9 | 0x00 | Padding/terminator |

### Response Format (25 bytes, Sub CPU → Main CPU)

| Offset | Value | Description |
|--------|-------|-------------|
| 0–7 | (echo) | Echo of request bytes 0–7 |
| 8–23 | ASCII | 16-character sound name (space-padded) |
| 24 | 0x10/0x20 | Status/category byte |

### Part Identifiers (byte 7)

| Value | Part | Default Voice (from trace) |
|-------|------|----------------------------|
| 0x12 | Right 1 | Modern E.P.1 (idx 0x06) |
| 0x13 | Right 2 | Bigband Brass (idx 0x38) |
| 0x14 | Left | Piano (idx 0x00) |
| 0x15 | Right 1 (conductor) | Modern E.P.1 (idx 0x06) |
| 0x16 | Right 2 (conductor) | Bigband Brass (idx 0x38) |

### Sub CPU Handling

- Processed in `Audio_Process_DSP` (0x035AC8), not the standard command dispatch table
- Sub-command 0x00 at offset 0x436B triggers sound name lookup from RAM tables at 0x041xxx
- Names are pre-loaded during boot from Table Data ROM, not queried from tone generator
- Response sent via `InterCPU_DMA_Send` with HDMA ch2

### Example Exchange (from MAME trace)

```
Request:  2B 30 7F 20 00 00 02 14 00 00
Response: 2B 30 7F 20 00 00 02 14 "Piano           " 10
```

## MAME Emulation Notes

### Latch Pending State and INT0

The MAME `generic_latch_8_device` tracks a `data_pending` flag that drives the Sub CPU's INT0 input. Two emulation issues were discovered and fixed:

**Issue 1: Stale pending state blocking INT0 (latch write without read)**

On real hardware, each latch write generates a new INT0 edge/level regardless of previous state. In MAME, `generic_latch`'s `data_pending_callback` only fires on state *changes* — if the latch is already marked "written" (because the previous value wasn't read due to a handshake flag check), subsequent writes silently update the value without triggering INT0.

**Fix:** Force-clear the pending state (`acknowledge_w(0)`) before each latch write, then write the new data. This ensures `data_pending` transitions 0→1 and the callback fires.

**Issue 2: INT0 level-detect re-assertion causing runaway ISR loop**

The TMP94C241 uses level-triggered INT0 (IIMC bit 1 = 0). On real hardware, the ISR reads the latch, which deasserts INT0 within the same clock cycle. In MAME, `set_input_line(CLEAR_LINE)` goes through `synchronize()` (see `diexec.cpp:663-691`), which defers the actual `execute_set_input()` call until **after the current timeslice ends**. This creates a window where `m_level[INT0]` remains `ASSERT_LINE` even though the latch has been read.

The TMP94C241's `check_irqs()` contains a level-detect re-assertion path: after dispatching an INT0 ISR, if `m_level[INT0] == ASSERT_LINE`, it re-sets the INT0 interrupt flag. With the stale `m_level`, this causes INT0 to fire again immediately — creating a runaway loop where the ISR fires ~20 times, each reading stale/empty latch data, corrupting the command protocol.

**Symptoms observed during boot:**
1. Main CPU sends E2 command byte to latch
2. INT0 fires correctly, ISR reads E2
3. INT0 re-fires spuriously (stale `m_level`), ISR reads 0xFF
4. ISR interprets 0xFF as standard command: count=(0xFF & 0x1F)+1=32, dest=0x10F0
5. HDMA ch0 now expects 32 bytes, but only 10 data bytes follow E2
6. DMAC0 reaches 21 (not 0), so INTTC0 never fires
7. Sub CPU never processes the E2 command → never responds to Main CPU
8. Main CPU times out after 10 seconds waiting at `0xFB770F`

**Failed first approach:** Removing the re-assertion code entirely fixed boot but broke button input — both CPUs' INT0 lines are driven by latches, and the Main CPU needs re-assertion for processing Sub CPU responses during normal operation.

**Fix:** Added `clear_int0_level()` public method to `tmp94c241_device` that synchronously updates `m_level[INT0]` and clears the INT0 interrupt flag. The driver's latch-read wrappers (`subcpu_latch_r()`, `maincpu_latch_r()`) call this immediately after `generic_latch::read()`, bypassing the deferred `synchronize()` mechanism.

This is safe because:
1. **Same-CPU context** — the latch read occurs during the CPU's own memory read (HDMA or instruction), so we're modifying the CPU's own state within its execution context
2. **Idempotent** — the deferred `set_input_line(CLEAR)` callback runs later but `m_level` is already `CLEAR_LINE`, so `execute_set_input()` becomes a no-op
3. **Re-assertion preserved** — the level-detect re-assertion code in `check_irqs()` stays intact, but now checks the *correct* `m_level` value
4. **New ASSERT works normally** — when new data is written to the latch, `set_input_line(INT0, ASSERT)` fires through the normal deferred path

### CPU Scheduling for Latch Transfers

Each latch write must be followed by a context switch so the receiving CPU can process it via HDMA. Without this, the writing CPU continues its timeslice and writes multiple bytes before the receiver gets a chance to read, causing data loss.

**Fix:** After each latch write:
1. `machine().scheduler().perfect_quantum(100µs)` — ensures tight interleaving
2. `writing_cpu->abort_timeslice()` — forces immediate context switch

## Main CPU → Sub CPU Cross-Reference

This table maps Main CPU sending routines to the Sub CPU handlers that process their commands, showing the complete data flow for each command range.

### Command Flow Overview

```
Main CPU                          Sub CPU
────────                          ───────
Audio_SendCommand
  → Sprintf_Core (retired name: Audio_CommandEncoder)
    → AssswbWr (ring buffer)
      → sendCOMM
        → InterCPU_Send_Data_Block  → INT0 / MICRODMA_CH0_HANDLER
          (latch write @ 0x140000)     → CMD_DISPATCH_TABLE[bits 7-5]
                                          → Audio_CmdHandler_XX_XX
                                            → MIDI_Dispatch (for 0x00-0x1F)
```

### Command Range Cross-Reference

| Cmd Range | Main CPU Sender | Main CPU Address | Sub CPU Handler | Purpose |
|-----------|----------------|-----------------|-----------------|---------|
| 0x00-0x1F | `sendCOMM` (A=0) | 0xEF32F4 | `Audio_CmdHandler_00_1F` | MIDI/audio data → ring buffer → `MIDI_Dispatch` |
| 0x20-0x3F | `sendCOMM` (A=1) | 0xEF32F4 | `Audio_CmdHandler_20_3F` | Tone generator (stub/reserved) |
| 0x40-0x5F | `sendCOMM` (A=2) | 0xEF32F4 | `Audio_CmdHandler_40_5F` | Buffer drain/flush (skips data) |
| 0x60-0x7F | `sendCOMM` (A=3) | 0xEF32F4 | `Audio_CmdHandler_60_7F` | DSP streaming state machine |
| 0x80-0x9F | `sendCOMM` (A=4) | 0xEF32F4 | `Serial1_DataTransmit_Loop` | Serial/MIDI TX to external port |
| 0xA0-0xBF | `sendCOMM` (A=5) | 0xEF32F4 | `Audio_CmdHandler_A0_BF` | Tone generator mode/config |
| 0xC0-0xDF | `sendCOMM` (A=6) | 0xEF32F4 | `Audio_CmdHandler_C0_FF` | Reserved (stub) |
| 0xE0-0xFF | `sendCOMM` (A=7) | 0xEF32F4 | `Audio_CmdHandler_C0_FF` | Reserved (stub); E1/E2/E3 handled separately |

### Special Command Cross-Reference

| Command | Main CPU Routine | Main CPU Address | Sub CPU Handler | Purpose |
|---------|-----------------|-----------------|-----------------|---------|
| 0xE1 | `InterCPU_E1_Bulk_Transfer` | 0xEF3457 | `InterCPU_RX_Handler` (boot) / `CH0_State2_E1` | Two-phase bulk DMA (6-byte header + payload) |
| 0xE2 | `InterCPU_E2_Send` | 0xEF33AA | `InterCPU_RX_Handler` (boot) / `CH0_State3_E2` | Extended parameter transfer (10-byte header) |
| 0xE3 | `SubCPU_Send_Payload` | 0xEF068A | `InterCPU_RX_Handler` (boot) | Payload ready signal (sets bit 6 of 0x04FE) |

### Boot-Time Transfer Cross-Reference

| Step | Main CPU Routine | Main CPU Address | Sub CPU Handler | Description |
|------|-----------------|-----------------|-----------------|-------------|
| 1 | `SubCPU_Send_Payload` | 0xEF068A | `InterCPU_RX_Handler` | Transfer 192KB firmware payload via E1 bulk transfers |
| 2 | `SubCPU_Send_Payload` (E3) | 0xEF068A | `InterCPU_RX_Handler` | Signal payload ready → Sub CPU jumps to payload entry |
| 3 | `SubCPU_Init_DMA_Channels` | 0xEF329E | `InterCPU_Latch_Setup` | Both CPUs configure DMA channels for runtime communication |
| 4 | `SubCPU_Payload_Verify` | 0xEF092B | — | Main CPU verifies payload checksums (no Sub CPU involvement) |

### Audio Command Pipeline (Runtime)

The Main CPU's `Audio_SendCommand` (called from 197+ locations) is the primary interface for sending audio parameters to the Sub CPU:

| Stage | Routine | Address | CPU | Description |
|-------|---------|---------|-----|-------------|
| 1. Lock | `Audio_Lock_Acquire` | 0xEF1FEE | Main | Acquire lock #7 (serializes audio commands) |
| 2. Format | `Sprintf_Core` | 0xFF1048 | Main | Printf-like formatter builds command packet (retired name: `Audio_CommandEncoder`) |
| 3. Queue | `AssswbWr` | 0xFDB1F3 | Main | Write to ring buffer at 0xBD3C (max 0x1FC bytes) |
| 4. Send | `sendCOMM` | 0xEF32F4 | Main | Chunk into ≤32-byte blocks, call `InterCPU_Send_Data_Block` |
| 5. Transfer | `InterCPU_Send_Data_Block` | 0xEF3345 | Main | Handshake + DMA write to latch at 0x140000 |
| 6. Receive | `MICRODMA_CH0_HANDLER` | 0x020F1F | Sub | DMA interrupt reads from latch, dispatches to handler |
| 7. Parse | `MIDI_Dispatch` | 0x034D93 | Sub | Parse MIDI status bytes, route to voice handlers |
| 8. Unlock | `Audio_Lock_Release` | 0xEF1F0F | Main | Release lock #7 |

### Sub CPU MIDI Voice Handlers

After `MIDI_Dispatch` parses the ring buffer, it routes MIDI messages to these voice processing routines:

| MIDI Status | Handler | Description |
|-------------|---------|-------------|
| 0x80/0x90 | `Voice_NoteOn` | Note On/Off (velocity 0 = Note Off) |
| 0xB0 | `Voice_CtrlChange` | Control Change (CC0-CC127 + proprietary 0x78-0x9D) |
| 0xC0 | `Voice_ProgChange` | Program Change (voice selection) |
| 0xD0 | `Voice_ChanPressure` | Channel Pressure (aftertouch) |
| 0xE0 | `Voice_PitchBend` | Pitch Bend (14-bit value) |
| 0xF0 | `Voice_SystemMsg` | System messages (reset, timing, etc.) |

### Naming Conventions

The following naming patterns are used consistently across both CPUs:

| Main CPU Pattern | Sub CPU Pattern | Relationship |
|-----------------|-----------------|--------------|
| `Audio_Lock_*`, `AudioLock_*` | `TaskSem_*`, `TaskSched_Wait` | Kernel semaphores (the same code on both CPUs; the main-CPU names are historical) |
| `Audio_DMA_Transfer` | `InterCPU_DMA_Send` | Core DMA routines (one per CPU direction) |
| `InterCPU_E1_*` | `InterCPU_E1_DMA_Transfer` | E1 bulk transfer protocol (both sides) |
| `InterCPU_E2_Send` | `Cmd_Check_E2_Pending` | E2 parameter transfer (send vs. deferred receive) |
| `InterCPU_Send_Data_Block` | `MICRODMA_CH0_HANDLER` | Standard command send vs. receive dispatch |
| `SubCPU_Send_Payload` | `InterCPU_RX_Handler` (boot) | Boot-time payload transfer |
| `SubCPU_Init_DMA_Channels` | `InterCPU_Latch_Setup` | DMA channel initialization |
| `sendCOMM` | `Audio_CmdHandler_*` | High-level send wrapper vs. per-range handlers |

## Research Needed

- [x] Document exact latch register bit layout - See Boot ROM Protocol above
- [x] Analyze handshaking timing requirements - Uses 60,000 iteration timeout (~300ms)
- [x] Document command 0x2D (DSP configuration) format — Complete: 4-layer protocol fully traced
- [x] Document two ring buffers (0x2B0D for MIDI, 0x3B60 for DSP) — Complete
- [x] Document command 0x2B (sound name query) format — Complete
- [x] Document Sub CPU interrupt configuration (INTETC01, INTE0AD) — Complete
- [x] Document HDMA-based command reception flow — Complete
- [x] Document INT0 level-detect emulation issues — Complete
- [x] Document MIDI message format in ring buffer (Note On/Off, CC, ProgramChange, PitchBend, etc.)
- [x] Document command byte encoding (handler index in bits 7-5, length in bits 4-0)
- [x] Document supported MIDI Control Changes (standard + proprietary 0x78-0x9D)
- [x] Document voice processing architecture (26 channels, 287 bytes/channel at 0x041381)
- [x] Cross-reference Main CPU and Sub CPU symbol names — Complete: see cross-reference tables above
- [ ] Document handlers 2 (0x40-0x5F), 5 (0xA0-0xBF), 6-7 (0xC0-0xFF) — undocumented command ranges
- [ ] Map status response message formats
- [ ] Determine actual subprogram storage location (table_data vs custom_data flash)
