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

The **KN5000** uses two distinct SysEx formats: **Roland GS** for incoming voice parameter control, and **Technics proprietary** for outgoing mode commands. It also implements a bulk data transfer system for panel memory, sound memory, composer data, sequences, and music style programmer (MSP) data. The **WSA1R** shares Technics' `0x50` manufacturer id but uses model byte `0x11` and its own command set (see [SX-WSA1R System Exclusive](#sx-wsa1r-system-exclusive) below).

## Outgoing: Technics SysEx

The KN5000 sends short proprietary SysEx messages via `MIDI_SendSysExCmd` (`0xFEBDA1`).

### Packet Format

```
F0 50 87 <param> F7
```

| Byte | Value | Meaning |
|------|-------|---------|
| `F0` | SysEx start | Standard MIDI SysEx header |
| `50` | Manufacturer ID | Technics/Panasonic (Matsushita) |
| `87` | Model ID | KN5000 identifier |
| `param` | Command byte | See table below |
| `F7` | SysEx end | (implicit, appended by `MIDI_SendCmdPacket`) |

### Known Command Bytes

| Param | Context | Description |
|-------|---------|-------------|
| `0x08` | Sequencer play/stop, drum voice changes, tempo changes, sound mode changes | Sound mode reset — signals downstream devices that the KN5000's sound configuration has changed |
| `0x10` | Panel button press (specific modes) | Mode change notification — sent when switching between certain operating modes |
| `0x68` | Sound initialization | Full sound reset — sent during major sound engine reconfiguration |

The `0x08` command is by far the most common, with 13 call sites across the firmware. It is sent after any operation that alters the active sound configuration (sequencer start/stop, drum kit selection, tempo changes, accompaniment mode switching).

### Implementation

`MIDI_SendSysExCmd` builds a 4-byte payload on the stack:

```
ld (xsp + 1), 0xF0    ; SysEx start
ld (xsp + 2), 0x50    ; Manufacturer: Technics
ld (xsp + 3), 0x87    ; Model: KN5000
ld (xsp + 4), a       ; Command byte (from A register)
```

It then calls `MIDI_SendCmdPacket` to transmit the packet through the MIDI output port, followed by `MIDI_PostSendStub` (likely a post-send flush or delay).

## Incoming: Roland GS SysEx

The KN5000 receives and processes **Roland GS** System Exclusive messages for real-time voice parameter control. This is validated by `SysEx_ValidateRolandHeader` (`0xFDADF6`).

### Expected Header

```
F0 41 42 12 40 01 <cmd> <data> F7
```

| Byte | Value | Meaning |
|------|-------|---------|
| `F0` | SysEx start | Standard MIDI SysEx header |
| `41` | Manufacturer ID | Roland |
| `42` | Device ID | Fixed device address |
| `12` | Command ID | DT1 (Data Transfer 1) |
| `40` | Model ID | GS (General Sound) |
| `01` | Sub-category | Address high byte |
| `cmd` | Address mid byte | Selects parameter group (see below) |
| `data` | Parameter value | Written to DSP configuration |
| `F7` | SysEx end | Standard MIDI SysEx terminator |

The firmware validates all 6 header bytes sequentially, returning immediately if any mismatch occurs. A maximum of 10 data bytes are accepted (checked via `cp c, 0xA` at entry).

### Command Dispatch

After header validation, the firmware reads the command byte and dispatches to one of four parameter handlers:

| Command | Handler | DSP Config | Voice Range | Description |
|---------|---------|------------|-------------|-------------|
| `0x30` | `SysEx_ApplyVoiceParam_4B` | `0x4B00` | 0-7 (8 voices) | Standard voice parameter, bank 4B |
| `0x33` | `SysEx_ApplyVoiceParam_4B_128` | `0x4B00` | 0-127 (128 voices) | Extended voice parameter, bank 4B |
| `0x38` | `SysEx_ApplyVoiceParam_49` | `0x4900` | 0-7 (8 voices) | Standard voice parameter, bank 49 |
| `0x3A` | `SysEx_ApplyVoiceParam_49_128` | `0x4900` | 0-127 (128 voices) | Extended voice parameter, bank 49 |

Commands `0x30`/`0x33` control DSP parameter bank `0x4B` (likely mixer/effects), while `0x38`/`0x3A` control bank `0x49` (likely oscillator/filter). The `_128` variants allow addressing up to 128 voice slots instead of the standard 8.

### Channel Routing

The header's implicit channel (derived from the SysEx stream position) determines the target voice data base address:

- **Channel 0:** Base at `0x00F180 + 0x2E0` — main voice parameter area
- **Channels 1-15:** Base at `0x0AB000 + (channel - 1) * 0x800 + 0x2E0` — per-channel voice areas (each channel gets a 2KB block)

### Voice Parameter Application

Each handler follows the same pattern:

1. **Clamp** the voice index to valid range (0-7 or 0-127) via `SysEx_ClampVoiceIndex*`
2. **Look up** the voice slot from a table (at `0xEE33A4` for 8-voice, `0xEE33AC` for 128-voice)
3. **Write** the parameter value via `DSPCfg_WriteParamSimple`
4. **Iterate** active voice slots (from `DSPCfg_ReadParam_Map0` at `0x4B04`/`0x4904`), applying the same parameter to all matching slots
5. **Restore** the original slot ID if the base address was temporarily modified

The per-channel dispatch tables (`SysEx_DispatchByChannel` at `0xFDACEA`, `SysEx_DispatchByChannel_49` at `0xFDAD71`) route parameters to up to 8 hardware channels, using jump tables at `0xEE3520`.

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

The KN5000 supports bulk data transfer for six data types, each with a named handler function (names stored as ROM strings at `0xE555A4`-`0xE555EC`):

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

1. Subtract `0x1E0003E` from the index parameter (XBC) to normalize
2. Validate range 0-9
3. Look up a 16-bit handler offset from the type-specific jump table
4. Dispatch via `jp_dri` (jump through indexed table)

The handlers support 10 sub-operations (indices 0-9) per data type, covering operations like initiate transfer, send data block, receive data block, verify checksum, and complete transfer.

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

- **External sequencers** using Roland GS protocol to control the KN5000's voice parameters in real time
- **GS-format MIDI files** to play back with correct voice assignments
- **MIDI accompaniment files** that embed GS SysEx for voice setup

The command mapping (`0x30`/`0x33` → bank 4B, `0x38`/`0x3A` → bank 49) corresponds to Roland GS address space `40 01 3x`, which covers Part parameters in the GS specification:

| GS Address | Meaning |
|-----------|---------|
| `40 01 30` | Tone number (instrument) |
| `40 01 33` | Rx. Note On |
| `40 01 38` | Scale tuning |
| `40 01 3A` | CAf Pitch Control |

## SX-WSA1R System Exclusive

The **SX-WSA1** / **SX-WSA1R** "Advanced Acoustic Modeling" synthesizer shares
Technics' `0x50` manufacturer ID with the KN5000 but uses a different model
designation and a different (larger) command vocabulary. Everything in this
section was read directly from the WSA1R firmware disassembly
(`kn5000-roms-disasm/wsa1/`); the tone-parameter and tempo paths were traced
end-to-end, the bulk-dump command bytes are taken verbatim from the ROM message
templates, and each claim below carries a confidence grade.

### Packet shape

```
F0 50 <cmd> 04 00 11 <address…> <data…> F7
```

| Byte | Value | Meaning |
|------|-------|---------|
| `F0` | SysEx start | Standard MIDI SysEx header |
| `50` | Manufacturer ID | Technics/Panasonic (Matsushita) — **MEASURED**, `prom_a 0xF8AE7E` comments it as "the Matsushita manufacturer ID" |
| `cmd` | Command byte | Selects the operation (see the tables below) |
| `04 00 11` | Device / model | `0x11` is the SX-WSA1R model id (set as `ld (XIX-1),0x11` at `prom_a 0xF8AE7E`); `04 00` precede it in every template — **MEASURED** |
| `address…` | Target address | Present on the transfer commands; 3 bytes in the bulk templates |
| `data…` | Payload | Length depends on the command |
| `F7` | SysEx end | Standard terminator |

The WSA1R also accepts MIDI's **Universal Non-Real Time** id `0x7E` (used for GM
System On/Off), exactly as the KN5000 does.

### Transmit vocabulary (message templates)

The firmware carries a table of literal outgoing-message templates at
**`prom_b 0xF4FEC8`–`0xF4FF60`** (read verbatim from the ROM data — **MEASURED**):

| Template bytes | Command | Meaning |
|----------------|---------|---------|
| `F0 50 29 7E F7`, `F0 50 2A 7E F7` | `0x29`/`0x2A` + `7E` | Acknowledge (the `7E` before `F7` is the ACK marker) |
| `F0 50 21 04 00 11 F7` | `0x21` | Request (dump request, form A) |
| `F0 50 22 04 00 11 F7` | `0x22` | Request (dump request, form B) |
| `F0 50 25 …` | `0x25` | (request/response family) |
| `F0 7E 7F 09 01 F7` | GM | **General MIDI System ON** |
| `F0 7E 7F 09 02 F7` | GM | **General MIDI System OFF** |
| `F0 50 2C 04 00 11 …` | `0x2C` | Open / begin a bulk transfer |
| `F0 50 2D 04 00 11 <addr3> <len3> …` | `0x2D` | Bulk **data dump** block |

The `0x2D` templates additionally pin down the WSA1R's **bulk-transfer memory
map**: each template embeds a 3-byte start address and a 3-byte length, and the
banks seen are `0x20xxxx`, `0x40xxxx`, `0x50xxxx`, `0x60xxxx` and `0x62xxxx`
(e.g. `40 00 00 · 00 00 20`, `40 00 20 · 00 12 60`, `50 06 00 · 05 40 00`).

The transmit builders are `sub_FB6E7F` / `sub_FB6F24` / `sub_FB71BB` /
`sub_FB8081`, feeding the byte-emit primitive `sub_FB7FEB` (`0xFB7FEB`).
**Crucially, these are reached only from (i) request→response — a received dump
request — and (ii) explicit menu actions** (the ROM strings `"BULK DUMP"`,
`"SYSEX BULK DUMP"`, `"GROUP DUMP"` exist in `prom_b`). No per-parameter edit
handler calls any transmit builder (**STRONG**, from a caller census). The unit
does **not** echo panel edits as SysEx.

### Receive dispatch

Incoming messages are routed through two parallel dispatch tables — one for data
loaded from file, one for live MIDI:

| Table | Address | Role |
|-------|---------|------|
| `PtrTable_F4F800` | `prom_b 0xF4F800` | File / load path |
| `PtrTable_F4F888` | `prom_b 0xF4F888` | Live-MIDI path (a subset of the file path) |

Dispatchers `sub_FB2160` (file) and `sub_FB21CB` (live) index these tables by a
command slot. **Slot 9** of *both* tables points at handler `0xFB33FE`.

### The one traced live parameter: TEMPO (slot 9)

The slot-9 handler `0xFB33FE` is, specifically, a **live tempo change** — traced
end-to-end (**PROVEN**):

1. It reads two payload nibbles from the received-SysEx buffer
   (`(0x60fc80)+0x11` / `+0x12`) and reconstructs a value `(H<<4)|L`.
2. It range-checks the value to **`0x28`–`0x12C` (40–300 BPM)**.
3. It passes the value to `sub_FB57ED` (`0xFB57ED`), which writes the 16-bit
   store **`(0x7EE2)`** (plus bit 0 of `(0x7EE3)`) — a 9-bit tempo.
4. `TempoSetter` (`0xFAA350`) reads `(0x7EE2)`, clamps 40–300 (default 120), and
   programs the sequencer timer: `TREG5 = 140,000,000 / (BPM · 64)`.

This received-SysEx path and the **front-panel tempo dial** converge on one
store, with byte-identical range logic:

| | Panel tempo dial | Received SysEx (slot 9) |
|---|---|---|
| entry | `PanelEvent_Code21_Dial` `0xF86833` | `0xFB33FE` |
| edit | `PanelDial_ApplyStep` `0xF8688E` (floor `0x0028`, cap `0x012C`) | value decoded, range-checked `0x0028`–`0x012C` |
| write | class-`0x7A` event → sink `sub_F448A3` (`0xF448A3`) → `(0x7EE2)` | `sub_FB57ED` → `(0x7EE2)`/`(0x7EE3)` directly |
| consumer | `TempoSetter` `0xFAA350` | `TempoSetter` `0xFAA350` |

Acceptance is gated at runtime (`0xFB33FE` checks `(0x207A)≠0x79`,
`(0x7f32)&0x04==0`, `(0x7f38)&0x08` set; `sub_FB57ED` needs `(0x7f32)&0x10==0`),
i.e. only in certain transport/clock states.

#### The tempo message on the wire

The command byte that routes to the tempo handler is **`0x25`**, and it is a
*leaf* of the receive decoder's trie (`0xF5115B`, record byte `0x25` → slot 9) —
so the tempo message carries **no `04 00 11` model bytes** (those belong to the
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
The SysEx module never touches `0x27A6`. Received SysEx reaches these parameters
only through a **whole-record bulk-dump load** (`0x2C`/`0x2D`), not addressable
per field (**STRONG**).

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
  DRAM `0x34100`). An emulator that watches its own parameter store and emits the
  equivalent GS message drives the real unit's parameter identically.
- **WSA1R: viable for TEMPO (proven), and for any parameter that has a dedicated
  receive slot.** The tempo example above is a complete, faithful sync channel:
  `F0 50 <cmd→slot 9> 04 00 11 <addr> <val 40..300> F7` → `(0x7EE2)` → `TREG5`.
  It does **not** extend to per-parameter *tone* editing, which is settable on
  receive only via a whole-record bulk-dump load, not per field.
- **In both cases the emulator must *originate* the messages.** Neither unit
  emits SysEx when the operator turns a knob (see §2) — so you cannot rely on the
  hardware echoing its own edits; the emulated side has to construct and send
  them.

### 2. Reverse direction (real → emulator), per edit — **not viable**

Neither machine transmits per-edit SysEx. The KN5000 does transmit real-time
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

- **WSA1R: not viable.** It fails on the transmit half — the unit emits neither
  its cursor/screen state nor its parameters on edit — so the real→emulator
  direction has no source, and buttons/screens cannot be driven the other way
  (§3).
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

**This is implemented for the WSA1R.** Wiring the WSA1R's MIDI OUT (its SC0
transmit path had been a stub) already mirrors every *performance* parameter for
free — the firmware transmits volume/pan/expression/modulation/sustain, pitch
bend and aftertouch as ordinary CC/AT/bend as you play (confirmed by capturing
the machine's own power-on MIDI). On top of that, a default-off **"Live parameter
mirror"** driver option transmits the one proven *config* value the firmware
never emits on edit: on a tempo change it sends `F0 50 25 <lo> <hi> F7` out MIDI
OUT. Verified end to end by capturing MIDI OUT off an ALSA port — writing
120/200/300 BPM emits `F0 50 25 08 07 F7` / `08 0C F7` / `0C 12 F7`, the exact
bytes above.

Button injection, per-edit reverse sync, and full bidirectional UI mirroring are
ruled out by the firmware and are not implemented. (The KN5000 already has MIDI
OUT wired and transmits its performance params the same way; a config mirror
there would follow the same shape, once each parameter's receive address is
mapped.)

## Code References

| Symbol | Address | Purpose |
|--------|---------|---------|
| `MIDI_SendSysExCmd` | `0xFEBDA1` | Send Technics SysEx (F0 50 87 param) |
| `MIDI_SendCmdPacket` | `0xFEBF48` | Low-level MIDI packet transmit |
| `SysEx_ValidateRolandHeader` | `0xFDADF6` | Validate incoming Roland GS header |
| `SysEx_ApplyVoiceParam_4B` | `0xFDAE7F` | Apply voice param, bank 4B, 8 voices |
| `SysEx_ApplyVoiceParam_4B_128` | `0xFDAF32` | Apply voice param, bank 4B, 128 voices |
| `SysEx_ApplyVoiceParam_49` | `0xFDAFD7` | Apply voice param, bank 49, 8 voices |
| `SysEx_ApplyVoiceParam_49_128` | `0xFDB08A` | Apply voice param, bank 49, 128 voices |
| `SysEx_DispatchByChannel` | `0xFDACEA` | Route param to channel (bank 4B) |
| `SysEx_DispatchByChannel_49` | `0xFDAD71` | Route param to channel (bank 49) |
| `SysEx_ClampVoiceIndex8` | `0xFDAB44` | Clamp voice index to 0-7 |
| `SysEx_ClampVoiceIndex128` | `0xFDABC8` | Clamp voice index to 0-127 |
| `SysEx_ParserLoop` | `0xFD8D33` | SysEx stream parser state machine |
| `SysEx_InitiateSend` | `0xFD8CAE` | Initiate bulk SysEx send |
| `MidiSysEx_CmdDispatchLoop` | `0xF2417E` | MIDI status byte dispatcher (0x81-0xF0) |
| `ExcSendFunc` | `0xF7661B` | Main SysEx send handler |
| `ExcDotFunc` | `0xF7666C` | Data Object Transfer handler |
| `ExcPmemFunc` | `0xF766D9` | Panel Memory SysEx handler |
| `ExcSmemFunc` | `0xF76737` | Sound Memory SysEx handler |
| `ExcCompFunc` | `0xF76795` | Composer SysEx handler |
| `ExcSeqFunc` | `0xF767F3` | Sequence SysEx handler |
| `ExcMspFunc` | `0xF76851` | MSP SysEx handler |

*(Addresses above were re-verified 2026-09 against `nm` on the rebuilt v10 ELF
(`kn5000-roms-disasm/rebuilt_ROMs/kn5000_v10_program.llvm.elf`); every address in this table
and in the prose above it was wrong in the previous revision of this page — several of the
`Exc*Func` entries were off by exactly the offset to that function's internal jump table
label, e.g. the old `ExcPmemFunc` address was actually `ExcPmemFunc_HandlerJumpTable`.)*

### WSA1R symbols

All addresses are on CPU 1 (`prom_a` = code @ `0xF80000`, `prom_b` = data @
`0xF00000`) and were read from `kn5000-roms-disasm/wsa1/`.

| Symbol | Address | Purpose |
|--------|---------|---------|
| SysEx receive dispatch (file) | `prom_b 0xF4F800` | `PtrTable_F4F800`, indexed by command slot |
| SysEx receive dispatch (live MIDI) | `prom_b 0xF4F888` | `PtrTable_F4F888`, live-MIDI subset |
| `sub_FB2160` | `0xFB2160` | File-path dispatcher |
| `sub_FB21CB` | `0xFB21CB` | Live-MIDI dispatcher |
| slot-9 handler | `0xFB33FE` | Live TEMPO change (decode + range-check) |
| `sub_FB57ED` | `0xFB57ED` | Writes tempo store `(0x7EE2)`/`(0x7EE3)` |
| `TempoSetter` | `0xFAA350` | `(0x7EE2)` → `TREG5` sequencer reload |
| Outgoing message templates | `prom_b 0xF4FEC8`–`0xF4FF60` | Literal `F0 50 …` / GM templates |
| `sub_FB7FEB` | `0xFB7FEB` | Byte-emit primitive |
| `sub_FB6E7F`/`FB6F24`/`FB71BB`/`FB8081` | — | Transmit builders (bulk/group dump, replies) |
| `PanelEvent_Code21_Dial` | `0xF86833` | Front-panel value/tempo dial |
| `PanelDial_ApplyStep` | `0xF8688E` | Dial edit, floor `0x0028` / cap `0x012C` |
| `sub_F448A3` | `0xF448A3` | Class-`0x7A` event sink → `(0x7EE2)` |
| `ToneEdit_CommitField` | `0xFD7435` | Tone-parameter commit (separate `0x27A6` store) |
| `UiEvent_RouteByCode` | `0xF8659B` | Routes class-`0xA9` UI events (button/screen/dial) |
| `PanelButton_Accept` | `0xF86609` | Button-press handler (reached only from SC1 link) |
| `SC1_RxOp0_ThreeByte` | `prom_b 0xF5B0D5` | Fills panel wire ring `0x2B40` from SC1 |

## References

- [MIDI Subsystem]({{ site.baseurl }}/midi-subsystem/) — MIDI dispatch and channel handling
- [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) — Sound generation and DSP configuration
- [Sequencer]({{ site.baseurl }}/sequencer/) — MIDI recording and playback
- [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/) — Main/Sub CPU MIDI routing

---

*Last updated: September 2026 — added the SX-WSA1R SysEx vocabulary and the
emulator↔hardware live-sync viability analysis; KN5000 addresses re-verified
against the symbol table September 2026.*
