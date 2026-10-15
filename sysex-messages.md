---
layout: page
title: SysEx Messages
permalink: /sysex-messages/
---

# MIDI System Exclusive Messages

This page documents the SysEx vocabularies of two Technics instruments: the
**KN5000** arranger keyboard and the **SX-WSA1R** acoustic-modeling synthesizer.
It also analyzes whether a driver could keep a real unit live-synced to the
emulated one.

The **KN5000** receives **Roland GS** SysEx for its reverb and chorus macros and levels, and builds a SysEx-shaped internal record, `F0 50 87 <param>`, that it sends to its own Sub CPU rather than to MIDI OUT. It also implements a bulk data transfer system for panel memory, sound memory, composer data, sequences, and music style programmer (MSP) data. The **WSA1R** shares Technics' `0x50` manufacturer id but identifies itself with `04 md 11` and has its own command set (see [SX-WSA1R System Exclusive](#sx-wsa1r-system-exclusive) below).

## Technics-Shaped Record to the Sub CPU

`MIDI_SendSysExCmd` (`0xFEBDA1`) does not send SysEx on MIDI OUT. It builds a 4-byte record shaped like a Technics SysEx header, and `MIDI_SendCmdPacket` hands it to `sendCOMM` with handler 0, so it travels as an inter-CPU command into the Sub CPU's MIDI ring (see [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/)). There, `Voice_SystemMsg` reads byte +2 (`0x87`) as a sub-command and calls `Voice_SetRhythmMode` with the parameter byte.

### Packet Format

```
F0 50 87 <param>
```

| Byte    | Value                          | Meaning                                                                  |
|---------|--------------------------------|--------------------------------------------------------------------------|
| `F0`    | Record status                  | Routes the record to the `0xF0` class (`Voice_SystemMsg`) on the Sub CPU |
| `50`    | Technics manufacturer-ID value | Not read on the `Voice_SetRhythmMode` path                               |
| `87`    | Sub-command                    | `Voice_SystemMsg` index 7 → `Voice_SetRhythmMode` (not a model ID)       |
| `param` | Rhythm-mode byte               | See table below                                                          |
| (none)  | No `F7`                        | `MIDI_SendCmdPacket` sends exactly the 4 bytes (count byte = 4)          |

### Known Command Bytes

| Param  | Context                                                                    | Description                                                                 |
|--------|----------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| `0x08` | Sequencer play/stop, drum voice changes, tempo changes, sound mode changes | Rhythm-mode byte for `Voice_SetRhythmMode` (0x08: bit 3 set → 0x04135E = 3) |
| `0x10` | Panel button press (specific modes)                                        | Rhythm-mode byte (bits 7-4 = 1 → word table 0x00F6F3 index 1 → 0x041360)    |
| `0x68` | Sound initialization                                                       | Rhythm-mode byte (bits 7-4 = 6, bit 3 set)                                  |

The `0x08` value is the most common; it is sent after operations that change the rhythm/sound configuration (sequencer start/stop, drum kit selection, tempo changes, accompaniment mode switching). `MIDI_SendSysExFromW` (`0xEF6085`) is a second entry point that copies W into A; its callers, all in `display/scoop_display.s`, pass `0x62`, `0x68`, `0x72` and `0x76`, and one passes a byte of `SysInit_BytecodeBlock` with bit 1 set.

### Implementation

`MIDI_SendSysExCmd` builds a counted 4-byte record on the stack:

```
ld (xsp + 0), 0x04    ; count byte
ld (xsp + 1), 0xF0    ; record status (0xF0 class)
ld (xsp + 2), 0x50    ; Technics manufacturer-ID value
ld (xsp + 3), 0x87    ; Voice_SystemMsg sub-command (index 7)
ld (xsp + 4), a       ; rhythm-mode byte (from A register)
```

It then calls `MIDI_SendCmdPacket`, which copies the 4 bytes to `0xD090` and passes them to `sendCOMM` with handler 0 (inter-CPU command byte `0x03`), followed by `MIDI_PostSendStub`, a bare `ret`.

## Incoming: Roland GS SysEx

The KN5000 receives and processes **Roland GS** System Exclusive messages that set its reverb and chorus (macro and level). This is validated by `SysEx_ValidateRolandHeader` (`0xFDADF6`).

### Expected Header

```
F0 41 <dev> 42 12 40 01 <cmd> <data> F7
```

| Byte    | Value              | Meaning                                       |
|---------|--------------------|-----------------------------------------------|
| `F0`    | SysEx start        | Standard MIDI SysEx header                    |
| `41`    | Manufacturer ID    | Roland                                        |
| `dev`   | Device ID          | Skipped by the validator (any value accepted) |
| `42`    | Model ID           | GS                                            |
| `12`    | Command ID         | DT1 (Data Set 1)                              |
| `40 01` | Address high / mid | GS reverb and chorus block                    |
| `cmd`   | Address low byte   | Selects the parameter (see below)             |
| `data`  | Parameter value    | Macro number or level                         |
| `F7`    | SysEx end          | Standard MIDI SysEx terminator                |

The firmware checks `F0`, `41`, `42`, `12`, `40` and `01` in turn, stepping over the device-ID byte (and over one byte between `F0` and `41`), and returns at the first mismatch. The `cp c, 0xA` at entry bounds the target slot passed in C (0 = live area, 1-10 = a song slot), not a data-byte count.

### Command Dispatch

After header validation, the firmware reads the command byte and dispatches to one of four parameter handlers:

| Command | Handler                        | DSP Config | Value Range | Description                |
|---------|--------------------------------|------------|-------------|----------------------------|
| `0x30`  | `SysEx_ApplyVoiceParam_4B`     | `0x4B00`   | 0-7         | GS Reverb Macro (8 macros) |
| `0x33`  | `SysEx_ApplyVoiceParam_4B_128` | `0x4B00`   | 0-127       | GS Reverb Level            |
| `0x38`  | `SysEx_ApplyVoiceParam_49`     | `0x4900`   | 0-7         | GS Chorus Macro            |
| `0x3A`  | `SysEx_ApplyVoiceParam_49_128` | `0x4900`   | 0-127       | GS Chorus Level            |

Commands `0x30`/`0x33` set the reverb (DSP parameter bank `0x4B`) and `0x38`/`0x3A` the chorus (bank `0x49`). The macro commands clamp to 0-7, one of the eight GS macros; the level commands clamp to 0-127. These are GS addresses `40 01 30`/`33`/`38`/`3A`.

### Target Slot

The caller passes a target slot in C (checked `<= 10` at entry), which selects the area the parameter is written to:

- **C = 0:** Base at `0x00F180 + 0x2E0` — the live area
- **C = 1-10:** Base at `SEQ_SONG_SLOTS` (`0x0AB000`) `+ (C - 1) * 0x800 + 0x2E0` — one of the 10 song slots of 0x800 bytes

### Voice Parameter Application

Each handler follows the same pattern:

1. **Clamp** the value to its range (0-7 for a macro, 0-127 for a level) via `SysEx_ClampVoiceIndex*`
2. **Map** it through a table (`SysEx4B_VoiceIndexMap8` at `0xEE33A4` for a macro, `SysEx4B_LevelCurve128` at `0xEE33AC` for a level)
3. **Write** the parameter value via `DSPCfg_WriteParamSimple`
4. **Iterate** the effect's parameter slots (count from `DSPCfg_ReadParam_Map0` at `0x4B04`/`0x4904`), writing DSP params `0x4B10+i` / `0x4910+i`
5. **Restore** the original slot ID if the base address was temporarily modified

The macro switches (`SysEx_DispatchByChannel` at `0xFDACEA`, chorus macros; `SysEx_DispatchByChannel_49` at `0xFDAD71`, reverb macros, labelled `SysEx_DispatchByChannel_49_ReverbMacroRoom1` … `SysEx_DispatchByChannel_49_ReverbMacroPanningDelay`) pick each macro's parameter words, which the callers write to DSP params `0x4910+i` / `0x4B10+i`.

## SysEx Parser State Machine

`SysEx_ParserLoop` (`0xFD8D33`) implements a 3-state parser for incoming SysEx streams read from the sequencer buffer:

### States (stored at DRAM address 48414)

| State | Action | Transition |
|-------|--------|------------|
| 0 | Wait for `0xF0` (SysEx start) | → State 1 on match |
| 1 | Check manufacturer ID | → State 2 if `0x50`, `0x7E`, or `0x41`; → State 0 otherwise |
| 2+ | Accumulate data bytes | → Process on `0xF7` (SysEx end); → State 0 on invalid |

### Accepted Manufacturer IDs

| ID | Manufacturer | Usage |
|----|-------------|-------|
| `0x41` | Roland | GS voice parameter commands |
| `0x50` | Technics (Panasonic) | Proprietary mode commands |
| `0x7E` | Universal Non-Realtime | Standard MIDI extensions (GM System On, etc.) |

Data bytes (bit 7 clear) are accumulated via `VoiceQueue_Append`. The buffer limit is checked against address 48212 (if the 16-bit value at that address reaches `0xFF`, further data is rejected). When `0xF7` is received, the accumulated message is processed by `SeqData_InitPlaybackFromField`.

## Bulk Data Transfer (SysEx Exclusive Functions)

The KN5000 supports bulk data transfer for six data types, each with a named handler function (widget instances `NakaInst_Exc*Func` at `0xE555A4`-`0xE555EC`):

| Function | ROM String | Data Type | Jump Table Base |
|----------|-----------|-----------|-----------------|
| `ExcSendFunc` | "ExcSendFunc" | Main send dispatch | N/A (dispatches to others) |
| `ExcDotFunc` | "ExcDotFunc" | Data Object Transfer | `0xE7FD8A` |
| `ExcPmemFunc` | "ExcPmemFunc" | Panel Memory (PM1-PM8) | `0xE7FDD6` |
| `ExcSmemFunc` | "ExcSmemFunc" | Sound Memory banks | `0xE7FDEA` |
| `ExcCompFunc` | "ExcCompFunc" | Composer/arranger data | `0xE7FDFE` |
| `ExcSeqFunc` | "ExcSeqFunc" | Sequencer song data | `0xE7FE12` |
| `ExcMspFunc` | "ExcMspFunc" | Music Style Programmer | `0xE7FE26` |

### Handler Architecture

Each `Exc*Func` handler (except `ExcSendFunc`) follows an identical pattern:

1. Subtract `EVT_GET_LARGE_STEP` (`0x1E0003E`) from the event code (XBC) to normalize
2. Validate range 0-9
3. Look up a 16-bit handler offset from the type-specific jump table
4. Dispatch via `jp t, (xix+bc)` into the `*_HandlerJumpTable`

The cases are NAKA widget events (in `ExcPmemFunc`: `ExcPmemFunc_OnGetLargeStep`, `ExcPmemFunc_OnGetMax`, `ExcPmemFunc_OnGetRamAddress`, with twins in the other handlers), plus a status-string formatter using `FileTransfer_Status_Table`. These are UI callbacks of the bulk-dump screen, not transfer steps.

### ExcSendFunc

`ExcSendFunc` (`0xF7661B`) is the top-level entry point. It validates the message type (`0x1C00007`), then calls `MainExcSend`, which dispatches to `SysEx_InitiateSend` based on an index (0-5) looked up from a table at `0xE7FD84`.

### SysEx_InitiateSend

`SysEx_InitiateSend` (`0xFD8CAE`) configures the SysEx send mode:

1. Sets bit 7 of the mode byte (DRAM 48380)
2. Sets the SysEx active flag (bit 6 of DRAM 48408)
3. Clears all MIDI channel states (`MidiChan_ClearAllStates`)
4. Dispatches to one of 6 mode-specific handlers via a jump table at `0xEE2F7E`

When the mode is deactivated (bit 7 clear), it clears the SysEx flag and calls `SoundMode_ResetAllParams`.

## Roland GS Compatibility

The KN5000's acceptance of Roland GS SysEx (manufacturer `0x41`) provides compatibility with Roland-format MIDI files and sequencers. This allows:

- **External sequencers** using Roland GS protocol to set the KN5000's reverb and chorus in real time
- **GS-format MIDI files** to play back with their GS reverb and chorus settings
- **MIDI accompaniment files** that embed GS SysEx for effect setup

The command mapping (`0x30`/`0x33` → bank 4B, `0x38`/`0x3A` → bank 49) corresponds to the Roland GS addresses `40 01 3x` for the reverb and chorus settings:

| GS Address | Meaning              |
|------------|----------------------|
| `40 01 30` | Reverb Macro (0-7)   |
| `40 01 33` | Reverb Level (0-127) |
| `40 01 38` | Chorus Macro (0-7)   |
| `40 01 3A` | Chorus Level (0-127) |

## SX-WSA1R System Exclusive

The **SX-WSA1** / **SX-WSA1R** "Advanced Acoustic Modeling" synthesizer shares
Technics' `0x50` manufacturer ID with the KN5000 but has its own framing
(`04 md 11`) and a different (larger) command vocabulary. Everything in this
section was read directly from the WSA1R firmware disassembly
(`kn5000-roms-disasm/wsa1/`); the tone-parameter and tempo paths were traced
end-to-end, the bulk-dump command bytes are taken verbatim from the ROM message
templates, and each claim below carries a confidence grade.

### Packet shape

```
F0 50 <cmd> 04 <md> 11 [<adr×3> <siz×3> <data…> <cn> <sm>] F7
```

| Byte       | Value           | Meaning                                                                                                                                                                                      |
|------------|-----------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `F0`       | SysEx start     | Standard MIDI SysEx header                                                                                                                                                                   |
| `50`       | Manufacturer ID | Technics/Panasonic (Matsushita) — `MIDI_SysExHeader`, `prom_a 0xFA5CB8`                                                                                                                      |
| `cmd`      | Command byte    | Selects the operation (see the tables below)                                                                                                                                                 |
| `04 md 11` | PC / MD / VER   | `04` = product, `md` = `00` on the SX-WSA1 keyboard and `01` on the SX-WSA1R rack (both are accepted), `11` = exclusive-spec version (`wsa1/docs/system-exclusive-reference/sec-glance.tex`) |
| `adr×3`    | Address         | On `2B`, `2C` and `2D` (not on `7E` continuation frames): a 21-bit address in three 7-bit bytes, most significant first                                                                      |
| `siz×3`    | Size            | On the same commands: the length in source bytes (before the nibble split), same 21-bit encoding                                                                                             |
| `data…`    | Payload         | Each source byte goes out as two bytes, high nibble first; length depends on the command                                                                                                     |
| `cn`       | Continue        | `01` while more frames follow, `00` on the last                                                                                                                                              |
| `sm`       | Checksum        | `(0 − S) & 0x7F`, where S sums every byte from `50` through `cn`; verified on reception for `7E`, `2B`, `2C` and `2D` only                                                                   |
| `F7`       | SysEx end       | Standard terminator                                                                                                                                                                          |

(Field rules: `wsa1/docs/system-exclusive-reference/sec-glance.tex` and `sec-message-set.tex`.)

The WSA1R also accepts MIDI's **Universal Non-Real Time** id `0x7E` (used for GM
System On/Off), exactly as the KN5000 does.

### Transmit vocabulary (message templates)

The firmware carries a table of literal outgoing-message templates at
**`prom_b 0xF4FEB4`–`0xF4FF60`** (`SysExMessageStrings_F4FEB4`):

| Template bytes                       | Command       | Meaning                                                               |
|--------------------------------------|---------------|-----------------------------------------------------------------------|
| `F0 50 23/24/27/28/29/2A 7E F7`      | `0x23`…`0x2A` | ACK, NAK, end of category, end of dump, error/abort, destination full |
| `F0 50 21 04 00 11 F7`               | `0x21`        | HRQ, handshake request (opens a bulk dump)                            |
| `F0 50 22 04 00 11 F7`               | `0x22`        | HRT, handshake routine                                                |
| `F0 50 25 …`                         | `0x25`        | TMP, tempo                                                            |
| `F0 7E 7F 09 01 F7`                  | GM            | **General MIDI System ON**                                            |
| `F0 7E 7F 09 02 F7`                  | GM            | **General MIDI System OFF**                                           |
| `F0 50 2C 04 00 11 …`                | `0x2C`        | ITR, write one parameter                                              |
| `F0 50 2D 04 00 11 <addr3> <len3> …` | `0x2D`        | Bulk **data dump** block                                              |

The `0x2D` templates additionally pin down the WSA1R's **bulk-transfer memory
map**: each template embeds a 3-byte start address and a 3-byte length, and the
banks seen are `0x20xxxx`, `0x40xxxx`, `0x50xxxx`, `0x60xxxx` and `0x62xxxx`
(e.g. `40 00 00 · 00 00 20`, `40 00 20 · 00 12 60`, `50 06 00 · 05 40 00`).

**Command `0x2C` also carries single-parameter changes.** The SMF writer holds 74
nineteen-byte templates (`SmfExport_ParamSysExTemplates`, `prom_b 0xF74FCF`) of the form
`F0 50 2C 04 00 11 00 <hi> <lo> 00 00 01 <nh> <nl> …`: a two-byte address, then the value
as two nibbles. The SMF reader's `SmfEvent_SysEx` decodes exactly that shape back, besides
GM System On/Off, and every one of the 74 bodies is a complete seven-byte path through the
receive decoder's tree described below (`notes/promb-2026-09-25/smf_param_sysex_probe.py`,
`smf_sysex_param_change.py` and `sysex_decode_tree_probe.py` in the disassembly repository).
For address-hi `0x11`, templates 4–70 read RAM `0x7622 + lo` — the work-RAM parameter records
([Parameter Records]({{ site.baseurl }}/wsa1-parameters/#factory-defaults-and-the-combination-memory));
`11 20` is `0x7642`, DSP effect block 1. `0x2C` is ITR, the single-parameter write, so the two
readings agree.

The transmit side is `SysExTx_Append` (append n bytes to the frame at 0x60FC88),
`SysExTx_AppendAndSendOnF7`, `SysExTx_SendFrameBothPorts` and `SysExTx_SwapBuffers`;
`SysExBuf_Reset` (`0xFB7FEB`) resets a frame buffer.
**Crucially, these are reached only from (i) request→response (a received dump
request), (ii) explicit menu actions** (the ROM strings `"BULK DUMP"`,
`"SYSEX BULK DUMP"`, `"GROUP DUMP"` exist in `prom_b`), **and (iii) the SX-WSA1
keyboard's tempo message**: `Tempo_ApplyBpm` calls `SysExTx_Tempo` on a tempo change
unless `MidiCfg_ModeBits` bit 4 is set or the tempo came from SysEx, and `SysExTx_Tempo`
then applies the receiver's gates (see the acceptance gate below) plus `(0x0922)` bit 0
clear, so the rack never sends it and the keyboard sends it only while
`MidiFilter_Exclusive` bit 3 is set. No other per-parameter edit
handler calls a transmit builder (**STRONG**, from a caller census). Apart from
tempo, the unit does **not** echo panel edits as SysEx.

### Receive dispatch

Incoming messages are routed through two parallel dispatch tables — one for data
loaded from file, one for live MIDI:

| Table | Address | Role |
|-------|---------|------|
| `PtrTable_F4F800` | `prom_b 0xF4F800` | File / load path |
| `PtrTable_F4F888` | `prom_b 0xF4F888` | Live-MIDI path (a subset of the file path) |

Dispatchers `SysExRx_ParseDispatch_Ring601646` (`0xFB2160`, file) and `SysExRx_PollRing601C6E` (`0xFB21CB`, live) index these tables by a
command slot. **Slot 9** of *both* tables points at handler `0xFB33FE`.

### How a byte physically leaves on MIDI OUT — **MEASURED**

Knowing the message templates is not the same as knowing the path a byte takes to the
DIN socket, and that path had one trap in it worth documenting.

The transmit interrupt handler **`MIDI_TX_Ready`** (`prom_a 0xFA542F`, vector slot `0x64`
via the `prom_b` thunk at `0xF40718`) owns the `SC0BUF` register. It first drains the five
**System Real Time** request bits in `(0xA0)` — writing the literal bytes `F8` clock, `FE`
active sensing, `FA` start, `FB` continue, `FC` stop, in **that** priority order, which is
*not* the bit order; putting the timing clock first is the correct choice, because it is
the one message whose jitter is audible. Only if none is pending does it pull a byte from
the output queue and write it to `SC0BUF` at `0xFA547E`.

That output queue is a **256-byte ring at `0x601432`** with the usual eleven veneers. So an
ordinary MIDI transmission is:

| Step | Routine | Convention |
|------|---------|------------|
| queue a block | `Ring601432_PutBlock` — slot `0xF41DF8`, body `prom_a 0xF8481C` | `push <buffer:4>`, `pushw <count:2>`, call, clean 6. The frame is read as `ld BC,(XIZ+0x08)` = count, `ld XIY,(XIZ+0x0a)` = buffer |
| wake the transmitter | `MIDI_PostSendWork` — `prom_a 0xFA590F` | no arguments; sets the `(0x77)` mailbox to `0xDD`, which restarts a transmitter that has already run dry. `MIDI_TX_Ready` writes `0xFD` there when it runs out |
| queue one byte | `Ring601432_Put` — slot `0xF41DF4` | one byte at `(XIZ+0x08)` |

`MIDI_SendBankAndProgram` (`0xFA5B5F`) shows the pair in use at `0xFA5BC6`–`0xFA5BD5`, in
the arm its own header calls *"port A"*.

> ⛔ **`0xF40ED4` is not the MIDI transmitter, despite appearances.** Its body is
> `Link_SendBlockIn32ByteChunks` (`prom_a 0xF8E02C`): it splits a buffer into `0x20`-byte
> pieces and hands each to `Link_SendCountedBlock`, which builds the header byte
> `((selector << 5) | (count - 1))` and writes it to **`0x007C0000`** — the **CPU1↔CPU2
> link port** — then micro-DMAs the body there. Its third argument looks like a port number
> at the call sites (three push `0x00`, one pushes `0x02`) but is the **three-bit selector**
> in that link header. `MIDI_SendBankAndProgram`'s header states the distinction outright:
> *"bit 4 of the first argument picks the destination: clear sends through `0xF41DF8`
> (`Ring601432_PutBlock`) … set sends through `0xF40ED4`, the block sender that carries
> port B's stream to the other CPU."* Anything sent through `0xF40ED4` reaches CPU 2, not
> the DIN socket. This cost a day of debugging on the emulator and is recorded so it costs
> nobody else one.

⚠ **Port B is not a second DIN socket.** The `_PortB` twins (`MIDI_PostSendWork_PortB`,
`0xFA5C12`) drain their own ring `0x60153C` and forward the result *over the link*, so
"port B" is a stream carried to the other processor, not an independent MIDI output.

**Why any of this matters for interrupt-time code.** The ring is written under the
firmware's own critical section, `push sr` / `ei 6` / … / `pop sr` — the **save-and-restore**
form. `MIDI_SendBankAndProgram`, being main-loop code, can afford `ei 0x00` instead; code
running inside the *receive* interrupt cannot, because forcing the mask to zero there
unmasks a re-entrant MIDI receive on top of itself. Level 6 masks `INTTX0`, the ring's
other writer. Note also that nothing transmits from inside an interrupt handler: a handler
appends to the ring, and the byte leaves later, in `INTTX0`.

### The one traced live parameter: TEMPO (slot 9)

The slot-9 handler `0xFB33FE` is, specifically, a **live tempo change** — traced
end-to-end (**PROVEN**):

1. It reads two payload nibbles from the received-SysEx buffer
   (`(0x60fc80)+0x11` / `+0x12`) and reconstructs a value `(H<<4)|L`.
2. It range-checks the value to **`0x28`–`0x12C` (40–300 BPM)**.
3. It passes the value to `SysExRx_ApplyTempo` (`0xFB57ED`), which writes the 16-bit
   store **`(0x7EE2)`** (plus bit 0 of `(0x7EE3)`) — a 9-bit tempo.
4. `Tempo_ApplyBpm` (`0xFAA742`) reads `(0x7EE2)`, clamps 40–300 (default 120), and
   programs the sequencer timer: `TREG5 = 140,000,000 / (BPM · 64)`.

   ⚠ Earlier revisions of this page put this step at `0xFAA350`. That
   address is inside a **stale copy** of the routine bank, `0xFAA018`–`0xFAA3FF`, which
   differs from the live bank `0x400` higher in exactly ten bytes and which nothing
   publishes or calls. The routine that runs is its live twin `Tempo_ApplyBpm`, called from
   18 places and published through the `prom_b` thunk `T_Tempo_ApplyBpm`. See
   [older-build remnants]({{ site.baseurl }}/wsa1-disassembly/#older-build-remnants-and-why-unreached-code-can-be-correct).

This received-SysEx path and the **front-panel tempo dial** converge on one
store, with byte-identical range logic:

|          | Panel tempo dial                                                                                                                                                      | Received SysEx (slot 9)                               |
|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------|
| entry    | `PanelEvent_Code21_Dial` `0xF86833`                                                                                                                                   | `0xFB33FE`                                            |
| edit     | `PanelDial_ApplyStep` `0xF8688E` (floor `0x0028`, cap `0x012C`)                                                                                                       | value decoded, range-checked `0x0028`–`0x012C`        |
| write    | class-`0x7A` event → `(0x7EE2)` (the sink is not re-verified; `0xF448A3`, cited here before, is `Seq_ApplyStoredSongTempo`, which sets `(0x7EE2)` from a loaded song) | `SysExRx_ApplyTempo` → `(0x7EE2)`/`(0x7EE3)` directly |
| consumer | `Tempo_ApplyBpm` `0xFAA742`                                                                                                                                           | `Tempo_ApplyBpm` `0xFAA742`                           |

Acceptance is gated at runtime. `SysExCmd_TempoReceive` (`0xFB33FE`) first calls
`SysEx_FeatureWordForVariant(5)`, which returns `0xFFFF` on the SX-WSA1R rack, so the
rack refuses the message; it then checks `(0x207A)≠0x79`, `MidiCfg_ModeBits` (`0x7F32`)
`&0x04==0` and `MidiFilter_Exclusive` (`0x7F38`) `&0x08` set, and `SysExRx_ApplyTempo`
needs `MidiCfg_ModeBits` bit 4 clear. These are model and MIDI-configuration checks,
not transport or clock states.

#### The tempo message on the wire

The command byte that routes to the tempo handler is **`0x25`**, and it is a
*leaf* of the receive decoder's trie (`LinkTable_F4FF61`, whose root record sits at
`0xF5115B` (`SysExDecodeTree_Root`) and which `prom_a` `SysExRx_MatchTrie` walks; record byte `0x25` → slot 9) —
so the tempo message carries **no `04 md 11` bytes** (those belong to the
transfer commands). The BPM is a 9-bit value split across the two data bytes as
**low-nibble first, then the high part** — `value = (H<<4)|L`, range-checked
40–300 — so the complete message is:

```
F0 50 25 <BPM & 0x0F> <BPM >> 4> F7
```

| BPM | message |
|-----|---------|
| 120 (`0x078`) | `F0 50 25 08 07 F7` |
| 200 (`0x0C8`) | `F0 50 25 08 0C F7` |
| 300 (`0x12C`) | `F0 50 25 0C 12 F7` |

Both data bytes are always < 0x80, so the parser never mistakes them for status
bytes. The value lands in the receive accumulator at offsets +0x11/+0x12 and is
stored to `(0x7EE2)` (low 8 bits) + `(0x7EE3)` bit 0 (bit 8).

### Tone-edit parameters use a separate store

The tone-editing parameters (RESONATOR TYPE, POSITION, DEPTH, KEY SHIFT, DETUNE,
key-follow, …) do **not** flow through the slot-9 style per-parameter SysEx
path. They live in a different field array (`(u8*)0x27A6`) and are committed by
`ToneEdit_CommitField` (`0xFD7435`) / `ToneEdit_CommitNoteField` (`0xFDA3E2`).
The SysEx module never touches `0x27A6` directly. Received SysEx reaches sound parameters
through a bulk-dump load (`0x2D`) or through single-parameter writes (`0x2C` ITR) to the
normal/drum sound areas (ADR `10 xx xx` / `18 xx xx`); the disassembly's SysEx reference
lays those areas out (chapter "The sound areas": a 713-byte NORMAL SOUND of one GENERAL,
four TONE and four MODELING blocks). How such a write reaches the tone-edit fields at
`0x27A6` has not been traced.

## Live-Sync Between an Emulated Unit and Real Hardware

A recurring question for these emulators is whether a "special mode" could keep
a **real** KN5000 or WSA1R in step with the **emulated** one — mirroring every
value edit to the hardware over MIDI, or even synchronizing what the operator
sees on screen. The firmware answers this precisely; the verdicts below are
derived from the receive/transmit paths documented above and from the panel and
UI event buses.

> **Caveat, stated up front:** these verdicts are grounded in the firmware
> disassembly, which is identical between an emulator and a real unit — so a
> message the *emulated* firmware accepts on its receive path, the *real*
> firmware (running the same ROM) accepts too. They have **not** been checked
> against physical hardware.

### 1. Mirroring value edits emulator → real, via SysEx — **partially viable**

- **KN5000: viable.** A received Roland-GS voice parameter is applied through the
  *same* store and notifier as a front-panel edit (`SoundParam_NotifyChange`,
  DRAM `0x34100`, `SNDPARAM_HASH_TABLE`). An emulator that watches its own parameter store and emits the
  equivalent GS message drives the real unit's parameter identically.
- **WSA1R: viable for TEMPO towards the SX-WSA1 keyboard (proven); the SX-WSA1R
  rack refuses it.** The tempo example above is a complete, faithful sync channel
  to the keyboard: `F0 50 25 <BPM & 0x0F> <BPM >> 4> F7` → `(0x7EE2)` → `TREG5`.
  The rack refuses the tempo message in both directions
  (`SysEx_FeatureWordForVariant(5)`), so a tempo mirror cannot drive a real rack.
  Per-parameter writes use ITR (`0x2C`) at the addresses given in the
  disassembly's SysEx reference; this page has not traced them through the
  firmware.
- **In both cases the emulator must *originate* the messages.** Apart from the
  SX-WSA1 keyboard's tempo message, neither unit emits SysEx when the operator
  turns a knob (see §2) — so you cannot rely on the hardware echoing its own
  edits; the emulated side has to construct and send them.

### 2. Reverse direction (real → emulator), per edit — **not viable**

Apart from the SX-WSA1 keyboard's own tempo message (`Tempo_ApplyBpm` → `SysExTx_Tempo`), neither machine transmits per-edit SysEx. The KN5000 does transmit real-time
**CC / aftertouch / pitch-bend** (config-gated), and both machines transmit
SysEx **only** on explicit bulk/group-dump menu actions and as replies to a
received dump request. So there is no per-edit source to drive a real→emulator
value sync. (Bulk dump can move a whole configuration in one shot, but not live
per-parameter.)

### 3. Triggering button presses on the real unit via SysEx — **not viable (WSA1R: proven)**

On the WSA1R, panel buttons enter the system **only** through the SC1
control-panel serial link (a channel entirely separate from MIDI/SC0): button
wire records fill ring `0x2B40` (`SC1_RxOp0_ThreeByte`, `prom_b 0xF5B0D5`), are
drained by `PanelWireQueue_DrainToGroupQueue` (`0xF8A088`), and only there become
class-`0xA9` UI events routed by `UiEvent_RouteByCode` (`0xF8659B`) to
`PanelButton_Accept` (`0xF86609`). No MIDI/SysEx handler writes ring `0x2B40` or
produces a class-`0xA9` event; the single UI event a received SysEx can inject is
the class-`0x7A` *tempo value* — a value change, not a button, not a screen
change (**STRONG→PROVEN**, from enumerated callers and enumerated ring writers).

### 4. Two-way UI / screen-state sync — **not viable in general**

- **WSA1R: not viable.** It fails on the transmit half: the rack emits neither
  its cursor/screen state nor its parameters on edit (the keyboard sends only
  tempo), so the real→emulator direction has no source, and buttons/screens
  cannot be driven the other way (§3).
- **KN5000: one-directional only.** An *inbound* MIDI parameter change posts a
  panel event (`0x570006` / `0x1e000a7`, `ParaLoadOpt` — commented as "bridges
  SysEx processing to the UI control panel") that repaints the affected control.
  So sending a parameter to the KN5000 does update its on-screen value
  (firmware-driven UI-sync, **viable one way**). Reflecting the KN5000's screen
  *back* to the emulator is available only via bulk dump, not live.

### What this means for the drivers

The genuinely implementable, firmware-faithful feature is a driver **"live
parameter mirror"** option that watches the emulated unit's parameter store and
emits the corresponding SysEx out a MIDI-OUT port. Its correctness is argued
**without hardware**: the receive path is the same firmware a real unit runs, so
a message the emulator builds and the real unit accepts changes the identical
store.

**This is implemented for the WSA1R in the kn7000_mame overlay build** (upstream
MAME's `wsa1.cpp` has no such option). Wiring the WSA1R's MIDI OUT (its SC0
transmit path had been a stub) already mirrors every *performance* parameter for
free — the firmware transmits volume/pan/expression/modulation/sustain, pitch
bend and aftertouch as ordinary CC/AT/bend as you play (confirmed by capturing
the machine's own power-on MIDI). On top of that, a default-off **"Live parameter
mirror"** driver option transmits tempo: on a tempo change it sends
`F0 50 25 <lo> <hi> F7` out MIDI OUT. Verified end to end by capturing MIDI OUT off
an ALSA port — writing 120/200/300 BPM emits `F0 50 25 08 07 F7` / `08 0C F7` /
`0C 12 F7`, the exact bytes above. The SX-WSA1 keyboard firmware sends this message
itself (`Tempo_ApplyBpm` → `SysExTx_Tempo`) unless `MidiCfg_ModeBits` bit 4 is set,
and a real SX-WSA1R rack refuses it, so the mirror can drive only a real SX-WSA1
keyboard.

Button injection, per-edit reverse sync, and full bidirectional UI mirroring are
ruled out by the firmware and are not implemented. (In the kn7000_mame overlay the
KN5000 also has MIDI OUT wired and transmits its performance params the same way;
upstream `kn5000.cpp` has no MIDI port. A config mirror there would follow the
same shape, once each parameter's receive address is mapped.)

## Code References

| Symbol                         | Address    | Purpose                                                         |
|--------------------------------|------------|-----------------------------------------------------------------|
| `MIDI_SendSysExCmd`            | `0xFEBDA1` | Build the `F0 50 87 param` record for the Sub CPU (rhythm mode) |
| `MIDI_SendCmdPacket`           | `0xFEBF48` | Send a counted record to the Sub CPU via `sendCOMM` (handler 0) |
| `SysEx_ValidateRolandHeader`   | `0xFDADF6` | Validate incoming Roland GS header                              |
| `SysEx_ApplyVoiceParam_4B`     | `0xFDAE7F` | GS Reverb Macro (0-7), bank 4B                                  |
| `SysEx_ApplyVoiceParam_4B_128` | `0xFDAF32` | GS Reverb Level (0-127), bank 4B                                |
| `SysEx_ApplyVoiceParam_49`     | `0xFDAFD7` | GS Chorus Macro (0-7), bank 49                                  |
| `SysEx_ApplyVoiceParam_49_128` | `0xFDB08A` | GS Chorus Level (0-127), bank 49                                |
| `SysEx_DispatchByChannel`      | `0xFDACEA` | Chorus macro switch: a macro's parameter words                  |
| `SysEx_DispatchByChannel_49`   | `0xFDAD71` | Reverb macro switch: a macro's parameter words                  |
| `SysEx_ClampVoiceIndex8`       | `0xFDAB44` | Clamp a macro number to 0-7 and map it                          |
| `SysEx_ClampVoiceIndex128`     | `0xFDABC8` | Clamp a level to 0-127 and map it                               |
| `SysEx_ParserLoop`             | `0xFD8D33` | SysEx stream parser state machine                               |
| `SysEx_InitiateSend`           | `0xFD8CAE` | Initiate bulk SysEx send                                        |
| `MidiSysEx_CmdDispatchLoop`    | `0xF2417E` | MIDI status byte dispatcher (0x81-0xF0)                         |
| `ExcSendFunc`                  | `0xF7661B` | Main SysEx send handler                                         |
| `ExcDotFunc`                   | `0xF7666C` | Data Object Transfer handler                                    |
| `ExcPmemFunc`                  | `0xF766D9` | Panel Memory SysEx handler                                      |
| `ExcSmemFunc`                  | `0xF76737` | Sound Memory SysEx handler                                      |
| `ExcCompFunc`                  | `0xF76795` | Composer SysEx handler                                          |
| `ExcSeqFunc`                   | `0xF767F3` | Sequence SysEx handler                                          |
| `ExcMspFunc`                   | `0xF76851` | MSP SysEx handler                                               |

*(Addresses above were re-verified 2026-09 against `nm` on the rebuilt v10 ELF
(`kn5000-roms-disasm/rebuilt_ROMs/kn5000_v10_program.llvm.elf`); every address in this table
and in the prose above it was wrong in the previous revision of this page — several of the
`Exc*Func` entries were off by exactly the offset to that function's internal jump table
label, e.g. the old `ExcPmemFunc` address was actually `ExcPmemFunc_HandlerJumpTable`.)*

### WSA1R symbols

All addresses are on CPU 1 (`prom_a` = code @ `0xF80000`, `prom_b` = data @
`0xF00000`) and were read from `kn5000-roms-disasm/wsa1/`.

| Symbol                                                      | Address                              | Purpose                                                                                                               |
|-------------------------------------------------------------|--------------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| SysEx receive dispatch (file)                               | `prom_b 0xF4F800`                    | `PtrTable_F4F800`, indexed by command slot                                                                            |
| SysEx receive dispatch (live MIDI)                          | `prom_b 0xF4F888`                    | `PtrTable_F4F888`, live-MIDI subset                                                                                   |
| `SysExRx_ParseDispatch_Ring601646`                          | `0xFB2160`                           | File-path dispatcher                                                                                                  |
| `SysExRx_PollRing601C6E`                                    | `0xFB21CB`                           | Live-MIDI dispatcher                                                                                                  |
| `SysExCmd_TempoReceive` (slot 9)                            | `0xFB33FE`                           | Live TEMPO change (model gate, decode + range-check)                                                                  |
| `SysExRx_ApplyTempo`                                        | `0xFB57ED`                           | Writes tempo store `(0x7EE2)`/`(0x7EE3)`                                                                              |
| `Tempo_ApplyBpm`                                            | `0xFAA742`                           | `(0x7EE2)` → `TREG5` sequencer reload, then `SysExTx_Tempo` on the keyboard (its stale twin at `0xFAA342` never runs) |
| `SysExMessageStrings_F4FEB4`                                | `prom_b 0xF4FEB4`–`0xF4FF60`         | Literal `F0 50 …` / GM templates                                                                                      |
| `MIDI_TX_Ready`                                             | `0xFA542F`                           | `INTTX0`: real-time bytes, then the output ring → `SC0BUF`                                                            |
| `Ring601432_PutBlock`                                       | slot `0xF41DF8` → `0xF8481C`         | append a block to the **MIDI OUT** ring at `0x601432`                                                                 |
| `Ring601432_Get`                                            | slot `0xF41DF0` → `0xF847F7`         | what `MIDI_TX_Ready` drains (`0xFFFF` = empty)                                                                        |
| `MIDI_PostSendWork`                                         | `0xFA590F`                           | wake a transmitter that ran dry — `(0x77) = 0xDD`                                                                     |
| `Link_SendBlockIn32ByteChunks`                              | slot `0xF40ED4` → `0xF8E02C`         | ⛔ **CPU1↔CPU2 link** at `0x007C0000`, *not* MIDI                                                                     |
| `MIDI_RX_Byte` / `MIDI_RX_SysExStart` / `MIDI_RX_SysExData` | `0xFA5496` / `0xFA584D` / `0xFA586E` | `INTRX0` and the SysEx parser; `(0xA9)` is its state byte                                                             |
| `SysExBuf_Reset`                                            | `0xFB7FEB`                           | Reset a SysEx frame buffer                                                                                            |
| `SysExTx_Append`                                            | `0xFB6F24`                           | Append n bytes to the frame at `0x60FC88` (transmit side: bulk/group dump, replies, keyboard tempo)                   |
| `SysExTx_AppendAndSendOnF7`                                 | `0xFB6E7F`                           | Transmit side                                                                                                         |
| `SysExTx_SendFrameBothPorts`                                | `0xFB71BB`                           | Transmit side                                                                                                         |
| `SysExTx_SwapBuffers`                                       | `0xFB8081`                           | Transmit side                                                                                                         |
| `PanelEvent_Code21_Dial`                                    | `0xF86833`                           | Front-panel value/tempo dial                                                                                          |
| `PanelDial_ApplyStep`                                       | `0xF8688E`                           | Dial edit, floor `0x0028` / cap `0x012C`                                                                              |
| `Seq_ApplyStoredSongTempo`                                  | `0xF448A3`                           | Song's stored tempo → `(0x7EE2)`, then `Tempo_ApplyBpm`                                                               |
| `ToneEdit_CommitField`                                      | `0xFD7435`                           | Tone-parameter commit (separate `0x27A6` store)                                                                       |
| `UiEvent_RouteByCode`                                       | `0xF8659B`                           | Routes class-`0xA9` UI events (button/screen/dial)                                                                    |
| `PanelButton_Accept`                                        | `0xF86609`                           | Button-press handler (reached only from SC1 link)                                                                     |
| `SC1_RxOp0_ThreeByte`                                       | `prom_b 0xF5B0D5`                    | Fills panel wire ring `0x2B40` from SC1                                                                               |

## References

- [MIDI Subsystem]({{ site.baseurl }}/midi-subsystem/) — MIDI dispatch and channel handling
- [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) — Sound generation and DSP configuration
- [Sequencer]({{ site.baseurl }}/sequencer/) — MIDI recording and playback
- [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/) — Main/Sub CPU MIDI routing

---

*Last updated: October 2026. September 2026: added the SX-WSA1R SysEx vocabulary and the
emulator↔hardware live-sync viability analysis; KN5000 addresses re-verified
against the symbol table September 2026.*
