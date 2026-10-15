---
layout: page
title: MIDI Serial I/O
permalink: /midi-serial-io/
---

# External MIDI Serial I/O

The KN5000 provides external MIDI communication through Serial Channel 0 (SC0) of the TMP94C241F Main CPU. The rear panel features three 5-pin DIN connectors (MIDI IN, MIDI OUT, MIDI THRU) and a COM SELECT switch that configures the serial port for different communication modes.

## Hardware Configuration

### Serial Channel 0 Registers

| Register | Address | Name | Purpose |
|----------|---------|------|---------|
| SC0BUF | `0xD0` | Serial Buffer | TX/RX data register |
| SC0CR | `0xD1` | Control Register | Serial control/status |
| SC0MOD | `0xD2` | Mode Register | Async mode, parity, stop bits |
| BR0CR | `0xD3` | Baud Rate Control | Clock divider for baud rate |
| INTES0 | `0xEA` | Interrupt Enable | TX/RX interrupt priority |

### Initialization (`SC0Init_EnableRegisters`)

```
SC0MOD (0xD2) = 0x29  ; 8N1, async mode
SC0CR  (0xD1) = 0x00  ; Clear errors/status
BR0CR  (0xD3) = 0x08  ; Standard: 31,250 baud (MIDI standard)
INTES0 (0xEA) = 0x5D  ; Enable TX/RX interrupts, priority 5
SC0BUF (0xD0) = 0xFE  ; Prime TX with Active Sense byte
```

The baud rate generator uses `fc/4/N` where `fc` = 16 MHz and `N` = BR0CR value. Standard mode: `16MHz / 4 / 8 = 500 kHz` internal clock, yielding the MIDI-standard 31,250 baud rate. An alternate variant (hardware revision dependent) uses BR0CR=6 for a `666.6 kHz` clock.

### COM SELECT Switch

The KN5000 rear panel has a rotary switch read from **Port Z** bits 7-4 (SFR `0x68`, shifted right by 4). The switch positions are **active low** — one bit low selects the mode, and any other pattern is treated as MIDI. It selects between four communication modes:

| Switch Position | Value | Mode | Protocol |
|----------------|-------|------|----------|
| MIDI | `0x00` | Standard MIDI | 31,250 baud, 8N1 |
| MAC | `0x01` | Apple Macintosh serial | (different baud/protocol) |
| PC1 | `0x02` | PC serial mode 1 | (different baud/protocol) |
| PC2 | `0x03` | PC serial mode 2 | (different baud/protocol) |

`READ_COM_SELECT_SWITCH` (`0xFCF8F6`) reads `PZ`, shifts the upper nibble down and indexes `MidiSerial_OffsetTable`, a 16-entry lookup that maps every bit pattern to one of the four modes; invalid switch states (more than one low bit) map to MIDI. The result is stored at DRAM `0xB7E0` (47072), the `COM_SELECT` byte.

The TX dispatch (`MIDI_SC0_TX_DISPATCH`) checks this value: `0x00` uses the MIDI-specific TX path (`MIDI_SC0_ENABLE_TX`); any other value calls `CompIface_SerialEnableTx`, an empty `ret`. Computer-interface output goes to the Sub CPU instead, as inter-CPU handler 4, which the Sub CPU's serial channel 1 transmits (see [Sub CPU Command Format]({{ site.baseurl }}/subcpu-command-format/#0x80-0x9f-serial-port-1-tx-serial1_datatransmit_loop)).

## Baud Rate Tables

Two sets of timing constants are computed during initialization based on hardware revision:

| Entry | Standard Mode | Alternate Mode | Purpose |
|-------|--------------|----------------|---------|
| DRAM 47060 | 31,250 | 23,437 | Base clock rate |
| DRAM 47062 | 10,416 | 7,812 | MIDI clock timing |
| DRAM 47064 | 4,166 | 3,125 | Fine timing |
| DRAM 47066 | 1,000 | 750 | Sub-timing |
| DRAM 47068 | 8 | 6 | BR0CR register value |

## MIDI Receive Path

### Interrupt Handler (`INTRX0_HANDLER` at `0xFCF1F0`)

When a byte arrives on SC0, the hardware triggers the RX interrupt:

1. **Error check:** Read SC0CR (0xD1) bits 4-2 (framing/parity/overrun errors). If any error bit is set, jump to `INTRX0_CLEAR_ERROR_STATE` (clear error flags, increment error counter at DRAM 47070, return from interrupt).

2. **Full context save:** Push all 7 extended registers (XWA, XBC, XDE, XHL, XIX, XIY, XIZ) to stack.

3. **Read byte:** Read SC0BUF (0xD0) — the received byte.

4. **Dispatch:** Call `MidiSeq_ReceiveAndForward` with the received byte as parameter. This routes to `MIDI_RX_BYTE_DISPATCHER`.

5. **Context restore and return from interrupt.**

### Byte Dispatcher (`MIDI_RX_BYTE_DISPATCHER`)

The dispatcher classifies each incoming byte:

```
Received byte
    |
    v
Bit 7 set? ──no──> MIDI_CHANNEL_MESSAGE_DISPATCHER (data byte)
    |yes
    v
Is it <= 0xF7? ──no──> MIDI_SYSTEM_MESSAGE_HANDLER (real-time)
    |yes
    v
Store as running status (DRAM 1059)
    |
    v
SysEx in progress? ──yes──> Handle SysEx end (0xF7) or error
    |no
    v
Return (wait for data bytes)
```

### Register Context Save/Restore

The MIDI RX handler maintains a full saved register context at DRAM 1080-1104. This allows MIDI processing to be interrupted and resumed without losing state:

| DRAM Address | Register | Size |
|-------------|----------|------|
| 1080 | XWA | 4 bytes |
| 1084 | XBC | 4 bytes |
| 1088 | XDE | 4 bytes |
| 1092 | XHL | 4 bytes |
| 1096 | XIX | 4 bytes |
| 1100 | XIY | 4 bytes |
| 1104 | XIZ | 4 bytes |

`MIDI_RX_CONTEXT_RESTORE` loads all 7 registers at entry; `MIDI_RX_CONTEXT_SAVE` stores them on exit. This design allows the MIDI parser to maintain multi-byte message parsing state across interrupts.

## Channel Message Routing

`MIDI_CHANNEL_MESSAGE_DISPATCHER` (`0xFCF733`) routes incoming data bytes based on the running status byte:

1. Extract the status type: `(running_status >> 4) & 0x7` → index into 8-entry jump table at `MIDI_CHANNEL_HANDLER_JUMP_TABLE` (`0xFCF760`).

2. Dispatch to the appropriate handler.

### Handler Jump Table

| Status | Type             | Handler                                         |
|--------|------------------|-------------------------------------------------|
| 0x80   | Note Off         | `ChanDisp_AwaitSecondDataByte` (two data bytes) |
| 0x90   | Note On          | `ChanDisp_AwaitSecondDataByte`                  |
| 0xA0   | Poly Aftertouch  | `ChanDisp_NoStatusReturn` (ignored)             |
| 0xB0   | Control Change   | `ChanDisp_AwaitSecondDataByte`                  |
| 0xC0   | Program Change   | `MIDI_QUEUE_EVENT_TO_SEQUENCER` (one data byte) |
| 0xD0   | Channel Pressure | `MIDI_QUEUE_EVENT_TO_SEQUENCER`                 |
| 0xE0   | Pitch Bend       | `ChanDisp_AwaitSecondDataByte`                  |
| 0xF0   | System           | `MIDI_SYSTEM_EXCLUSIVE_HANDLER`                 |

The table proper starts at `MIDI_CHANNEL_HANDLERS` (`0xFCF761`), after one pad byte.

### Channel Message Queueing

Channel messages are queued to the sequencer ring buffer at `0x1F37B` via `MIDI_QUEUE_EVENT_TO_SEQUENCER`:

- Checks buffer capacity (minimum 3 entries free)
- Writes status byte, then data byte(s)
- If buffer overflows: sets overflow flag (DRAM 1063 bit 2), increments error counter (DRAM 47069)

For Note On with velocity 0 in a full buffer, the event is silently dropped (effectively converting it to a Note Off that's already implied by the zero velocity).

### SysEx Message Handling

`MIDI_SYSTEM_EXCLUSIVE_HANDLER` (`0xFCF800`) handles system messages:

| Status | Message | Action |
|--------|---------|--------|
| `0xF0` | SysEx Start | Set SysEx-in-progress flag; check manufacturer ID |
| `0xF2` | Song Position | Set running status, capture LSB |
| `0xF3` | Song Select | Queue to sequencer |

**SysEx manufacturer ID filtering:** After `0xF0`, the next byte is checked against three accepted manufacturer IDs:
- `0x50` (Technics/Panasonic)
- `0x41` (Roland)
- `0x7E` (Universal Non-Realtime)

If matched: set SysEx capture flag (DRAM 1074 bit 1), write both bytes to `SeqBuf2`. Subsequent data bytes are accumulated until `0xF7` terminates the message. Unrecognized manufacturer IDs cause the SysEx to be silently ignored.

## MIDI Transmit Path

### Interrupt Handler (`INTTX0_HANDLER` at `0xFCF15B`)

The TX interrupt fires when SC0BUF is ready for the next byte:

1. **Check flag byte** (DRAM 1065) for pending system messages, in this priority order (each clears its flag):
   - Bit 0: Send `0xF8` (MIDI Clock)
   - Bit 4: Send `0xFE` (Active Sense)
   - Bit 1: Send `0xFA` (Start)
   - Bit 2: Send `0xFB` (Continue)
   - Bit 3: Send `0xFC` (Stop)

   While bit 4 of DRAM `0xFD50` is set, a pending clock, start, continue or stop flag is cleared but `0xFE` is sent in its place.

2. **Dequeue next byte** from the MIDI OUT queue via `SeqBuf_MidiOut_ReadByte`. If nothing is pending (`SeqBuf_MidiOut_CheckEmpty`), disable the TX interrupt (INTES0 = 0xFD).

3. **Write to SC0BUF** (register 0xD0) to transmit the byte.

### TX Enable (`MIDI_SC0_ENABLE_TX`)

Called when new data is available for transmission:

1. If DRAM 1140 == 0x55: reinitialize the queue (`SeqBuf_MidiOut_Init`) and clear the pending flags, without enabling the TX interrupt.
2. Otherwise: set TX interrupt enable (INTES0 = 0xDD) to trigger the TX interrupt handler.

## System Real-Time Messages

`MIDI_SYSTEM_MESSAGE_HANDLER` handles incoming real-time messages:

| Byte | Message | Action |
|------|---------|--------|
| `0xF8` | Timing Clock | Process MIDI clock tick |
| `0xFA` | Start | Reset playback position, arm sync |
| `0xFB` | Continue | Resume from current position |
| `0xFC` | Stop | Halt playback, save position |
| `0xFE` | Active Sense | Set alive flag (DRAM 1063 bit 7) |
| `0xFF` | System Reset | Ignored (in MIDI mode) |

### MIDI Clock Synchronization

The KN5000 supports full external MIDI clock sync with three independent clock sources:

**Source 1 (Primary Clock):**
- DRAM 1047: Sub-beat counter (increments by 4 per clock tick)
- DRAM 1048: Beat counter (increments when sub-beat reaches 96)
- DRAM 1056: Source state flags

**Source 2 (Secondary/Error-Corrected):**
- DRAM 1045/1046: Sub-beat and beat counters
- DRAM 1111: Previous sub-beat (for delta computation)
- DRAM 1120-1124: Error accumulator (phase-locked loop correction)
- DRAM 1076/1077: Coarse counters with overflow detection

**Source 3 (Alternate Sync):**
- DRAM 1051/1052: Sub-beat and beat counters
- DRAM 1057: Source state flags
- DRAM 1071/1072: Sync threshold comparison values

All sources use **96 PPQN** (pulses per quarter note) resolution, matching standard MIDI clock resolution (24 PPQN with 4x subdivision).

The error correction in Source 2 computes a running delta between clock ticks and applies a correction factor (`DRAM 1124` accumulates the error, wrapping at 96), effectively implementing a software PLL that smooths out jitter in the incoming MIDI clock.

### MIDI Transport Events

When external Start/Stop/Continue messages change the transport state, the firmware queues events to the internal sequencer:

| Event | Code | Trigger |
|-------|------|---------|
| `0x85` | Start/Reset | External Start (`0xFA`) received |
| `0x86` | Stop | External Stop (`0xFC`) received |

Events are queued via `MIDI_QUEUE_EVENT_PAIR` which writes both the event code and the current sub-beat position to the sequencer FIFO (ring buffer at `0x1E753`, capacity checked against 2 entries minimum).

## High-Level Processing (`MidiSerial_ProcessInput`)

Above the interrupt-driven byte-level I/O, `MidiSerial_ProcessInput` (`0xFCF9AE`) runs in the main task loop:

1. Check if MIDI processing is enabled (DRAM 64848 bit 4).
2. Compare read/write pointers of the ring buffer at `0x1F37B`.
3. For each buffered message:
   - Extract the status type: `(status >> 4) & 0x7`
   - Look up handler address from `MidiSerial_CmdJumpTable` (16-entry table at `0xFCFA67`)
   - Call the handler
4. After processing all messages: call `MidiStream_LoadAllPresets`.

### Command Jump Table

The 16-entry jump table at `MidiSerial_CmdJumpTable` covers the **system** messages
`F0`-`FF`, indexed by the status byte's low nibble (reader `MidiRx_SystemMsgDispatch`):

| Index | Status | Handler | Purpose |
|-------|--------|---------|---------|
| 0-1 | `F0`, `F1` | `MidiRx_SystemMsg_MarkIgnored` | sets bit 0 of RAM `0x428` |
| 2 | `F2` | `MidiSerial_HandleSongPosition` | Song Position Pointer: data word to RAM `0x42D`/`0x42E` (bit 7 of the high byte set per `0xFD52` bit 2) |
| 3 | `F3` | `MidiSerial_HandleSongSelect` | Song Select: data byte to RAM `0x42C` (bit 7 set per `0xFD51` bit 3) |
| 4-15 | `F4`-`FF` | `MidiRx_SystemMsg_MarkIgnored` | sets bit 0 of RAM `0x428` |

Slots 2 and 3 were earlier labelled `MidiSerial_HandleSysReset_Data` / `_HandleSysCommon_Data`.
The midi lane renamed them in September 2026 from the status bytes that reach them
(`scripts/renaming/rename_midi_syscommon.sed`).

## MIDI THRU

The MIDI THRU port is a hardware echo of the MIDI IN signal. It does not pass through software processing — the electrical signal from MIDI IN is directly routed to MIDI THRU via optocoupler output.

## DRAM State Variables

Key MIDI state variables maintained in DRAM:

| Address     | Size | Purpose                                                                                                                             |
|-------------|------|-------------------------------------------------------------------------------------------------------------------------------------|
| 1059        | 1    | Running status byte                                                                                                                 |
| 1063        | 1    | Status flags (bit 2: overflow, bit 6: SysEx active, bit 7: Active Sense)                                                            |
| 1065        | 1    | TX pending flags (bits 0-4: F8/FA/FB/FC/FE)                                                                                         |
| 1066        | 1    | Clock tempo accumulator                                                                                                             |
| 1074        | 1    | SysEx state (bit 0: in progress, bit 1: capturing, bit 5: error)                                                                    |
| 1080-1104   | 28   | RX context save area (7 registers x 4 bytes)                                                                                        |
| 1140        | 1    | Compared with 0x55: when equal, `MIDI_SC0_ENABLE_TX` discards the MIDI OUT queue and `Seq_EventProcessingTick` skips its event loop |
| 32523       | 1    | External sync mode                                                                                                                  |
| 47060-47068 | 10   | Baud rate configuration table                                                                                                       |
| 47069       | 1    | Queue overflow counter                                                                                                              |
| 47070       | 1    | Serial error counter                                                                                                                |
| 47071       | 1    | Last received byte                                                                                                                  |
| 47072       | 1    | COM SELECT switch value (0=MIDI, 1=MAC, 2=PC1, 3=PC2)                                                                               |
| 47074       | 1    | Transport flags                                                                                                                     |
| 64848       | 1    | MIDI control flags (bit 2: ext clock enable, bit 4: MIDI disable)                                                                   |

## Code References

| Symbol | Address | Purpose |
|--------|---------|---------|
| `SC0Init_Entry` | `0xFCF897` | Serial port initialization |
| `SC0Init_EnableRegisters` | `0xFCF940` | Configure SC0 registers |
| `READ_COM_SELECT_SWITCH` | `0xFCF8F6` | Read rear panel switch |
| `INTRX0_HANDLER` | `0xFCF1F0` | MIDI RX interrupt handler |
| `INTTX0_HANDLER` | `0xFCF15B` | MIDI TX interrupt handler |
| `INTRX0_CLEAR_ERROR_STATE` | `0xFCF13D` | RX error recovery |
| `MIDI_RX_BYTE_DISPATCHER` | `0xFCF224` | Classify and route RX bytes |
| `MIDI_CHANNEL_MESSAGE_DISPATCHER` | `0xFCF733` | Route channel messages |
| `MIDI_SYSTEM_MESSAGE_HANDLER` | `0xFCF297` | Process real-time messages |
| `MIDI_SYSTEM_EXCLUSIVE_HANDLER` | `0xFCF800` | SysEx start/end handling |
| `MIDI_RX_CONTEXT_SAVE` | `0xFCF87A` | Save 7 registers to DRAM |
| `MIDI_RX_CONTEXT_RESTORE` | `0xFCF85D` | Restore 7 registers from DRAM |
| `MIDI_SC0_TX_DISPATCH` | `0xFCF972` | TX path dispatch (MIDI vs serial) |
| `MIDI_SC0_ENABLE_TX` | `0xFCF991` | Enable TX interrupt |
| `MidiSerial_ProcessInput` | `0xFCF9AE` | Main-loop MIDI processing |
| `MidiSerial_WaitForData` | `0xFCFA25` | Wait for RX buffer data |
| `MIDI_QUEUE_EVENT_TO_SEQUENCER` | `0xFCF782` | Queue MIDI to sequencer buffer |
| `MIDI_START_PLAYBACK_REQUEST` | `0xFCF4F7` | External Start handler |
| `MIDI_RESET_PLAYBACK_STATE` | `0xFCF51B` | Reset all clock counters |
| `MIDI_QUEUE_TRACK_EVENT` | `0xFCF68F` | Queue beat event to FIFO |
| `MIDI_QUEUE_EVENT_PAIR` | `0xFCF6D5` | Queue event + position pair |

## References

- [MIDI Subsystem]({{ site.baseurl }}/midi-subsystem/) — Internal MIDI processing (Sub CPU)
- [SysEx Messages]({{ site.baseurl }}/sysex-messages/) — System Exclusive message formats
- [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) — Sound generation
- [Sequencer]({{ site.baseurl }}/sequencer/) — MIDI recording and playback
- [CPU Subsystem]({{ site.baseurl }}/cpu-subsystem/) — TMP94C241F serial channel details

---

*Last updated: October 2026*
