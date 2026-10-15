---
layout: page
title: Data Wheel (TEMPO/PROGRAM Encoder)
permalink: /data-wheel-investigation/
---

# Data Wheel (TEMPO/PROGRAM Encoder)

## Overview

The KN5000 has a large rotary encoder below the LCD, labelled TEMPO/PROGRAM. It is the
control used to change whatever numeric value the focused on-screen widget owns. This page
describes the whole path, from the detent to the UI event.

The wheel is a **control-panel serial input**, carried on the same link, the same interrupt
and the same packet parser (`CPanel_RX_ParseNext`) as the button segments. Its header's type
bits are `010`, so the parser hands it to the Type 2 handler. There it is encoder ID 31, the
pass-through entry, so the count reaches the firmware untouched, with no lookup table and no
MIDI CC. It is *not* delivered by poking main-CPU DRAM.

## Hardware

The service manual puts **SW101 "ENCODER SWITCH" (QSRGT002AA)** on the **CPL** (left) control
panel board, wired to the ROTA/ROTB quadrature inputs of that board's `M37471M2196S` MCU. The
panel MCU counts detents and reports them; the main CPU never sees the quadrature.

## Wire Format

The panel sends a two-byte frame:

```
[0xD7] [signed detent count]
```

- `0xD7` = `0xC0 | 0x17`. Bits 7:6 = `11` select the **left** panel, exactly as button packets
  encode it, and `0x17` is the encoder sub-address. (The KN7000 panel uses the same `0x17`
  index for its own TEMPO/PROGRAM knob.)
- The second byte is a **count** of detents accumulated since the previous report, not a
  direction. Sending a larger magnitude is how a fast spin is expressed.

The firmware turns a header byte into a record index with `((A & 0xC0) >> 1) | (A & 0x1F)`,
so `0xD7` maps to index `0x77`. The translation table holds `0x19` there — the data-wheel
record. Only `0xD7` and `0xF7` reach that index.

The translation table sits at a different address in each firmware revision but its **content
is byte-identical across all six** (`sha1 48d964b1…`):

| Revision | Translation table |
|---|---|
| v5 | `0xED9F28` |
| v6 | `0xED9F40` |
| v7, v8, v9, v10 | `0xEDA03C` |

The encoding is a constant of the machine; the addresses are not. This is why the wheel must
be implemented at the wire and not by writing a firmware data structure at a hardcoded address.

Regenerate the table above with `notes/kn5000-wheel-probes/tblid.py` in the kn7000_mame
repository.

## Acceleration Curve

`CtrlPanel_HandleSerialPort` (`main_title_ctrl_panel.s:301`) is the consumer:

```asm
CtrlPanel_HandleSerialPort:
	cp (SWBTWR_PAYLOAD_1:16), 33    ; payload 0x21 = the data wheel
	jrl nz, UIEvent_Epilogue
	cp (SWBTWR_PAYLOAD_2:16), 0     ; zero count = nothing to do
	jrl z, UIEvent_Epilogue
	ld xwa, 0xffffffff
	ld xbc, EVT_DIAL                ; 0x1C0001F
	call DeleteEvent                ; drop any pending dial event
	ld a, (SWBTWR_PAYLOAD_2:16)     ; the signed detent count
	add a, 0x10
	exts wa
	sla wa, 2                       ; x4: table of 33 signed longs
	lda xbc, (CtrlPanel_DialStepByDelta:24)
	...                             ; posts EVT_DIAL with the table entry
```

The table indexed by `sext8(count + 0x10)` is a **33-entry signed acceleration curve**,
`CtrlPanel_DialStepByDelta` (`0xEA98E2` on v10, `0xEA97CE` on v5). It runs monotonically
**decreasing**, from `+7` at index 0 down to `-7` at index 32:

| wire count  | -16..-12 | -11..-9 | -8..-6 | -5,-4 | -3 | -2 | -1 | 0 | +1 | +2 | +3 | +4,+5 | +6..+8 | +9..+11 | +12..+16 |
|-------------|----------|---------|--------|-------|----|----|----|---|----|----|----|-------|--------|---------|----------|
| **UI step** | +7       | +6      | +5     | +4    | +3 | +2 | +1 | 0 | -1 | -2 | -3 | -4    | -5     | -6      | -7       |

Because the curve is decreasing, **clockwise rotation must be reported as a negative count**
to raise the on-screen value.

> ⚠ **The index is not bounds-checked.** The firmware computes `sext8(count + 0x10)` and
> indexes a 33-entry table (deltas -16..+16) with no clamp, so the only legal wire
> magnitudes are **-16..+16**. Keeping within that range is the panel's job; nothing in the
> firmware will catch a violation.

Regenerate the curve with `notes/kn5000-wheel-probes/curve.py`.

## Event Chain

```
detent on SW101 (CPL board, ROTA/ROTB)
  -> panel MCU accumulates a signed count
  -> CP serial frame [0xD7, count]
  -> type bits 010 -> CPanel_RX_EncoderPacket -> encoder ID 31 (Encoder_PassthroughIdentity):
     count unchanged, queued as {0xD7, count, 0xFF}
  -> header 0xD7 -> record index 0x77 -> translation table -> record 0x19
  -> SwbtWr event: payload 0x21 at DRAM[0xC07D], count at DRAM[0xC07E]
  -> CtrlPanel_HandleSerialPort: index the acceleration curve, post event 0x1C0001F
  -> GroupBox_HandleCursorNav (ui_control_panel.s:3985) navigates the focused widget
```

## The Wheel Is the Type 2 Pass-Through Entry

Type 2 packets are dispatched by `CPanel_EncoderDispatch` (`midi_encoder_routines.s:33`) through
a jump table at ROM `0xEDA0BC`, indexed by the encoder ID in the header. The analog IDs carry
absolute 8-bit ADC values; ID 31 carries the data wheel's signed detent count:

| Index | Header | Handler                       | Controller                                      |
|-------|--------|-------------------------------|-------------------------------------------------|
| 2     | 0x12   | `Encoder_ProcessModwheel`     | Modulation wheel                                |
| 5     | 0x15   | `Encoder_ProcessVolume`       | Volume slider                                   |
| 25    | 0xD1   | `Encoder_ProcessBreath`       | Breath controller                               |
| 26    | 0xD2   | `Encoder_ProcessFoot`         | Foot controller                                 |
| 27    | 0xD3   | `Encoder_ProcessExpression`   | Expression pedal                                |
| 31    | 0xD7   | `Encoder_PassthroughIdentity` | TEMPO/PROGRAM data wheel (count passed through) |

Entry 31 is the data wheel's: `Encoder_PassthroughIdentity` returns the count unchanged, and
`CPanel_RX_EncoderPacket` queues `{0xD7, count, 0xFF}`. Every other ID returns a constant 1.

## Segment 0x0B Is a Boot-Time Status Register, Not the Wheel

Segment `0x0B` sits in the gap between the right-panel scan columns (0–10) and the left-panel
ones. During boot only, `CPanel_PollStartup` / `CPanel_ButtonPollLoop`
(`cpanel_routines.s:505-549`) sends `20 0B`, stores the reply at DRAM[0x8E55], and derives a
three-valued state from bits 7 and 6:

| Bit set | Derived state at DRAM[0x8E6A] |
|---|---|
| 7 | `0x0D` |
| 6 | `0x0E` |
| neither | `0x0C` |

The loop re-polls until the value is stable on two consecutive reads, then returns. Steady-state
operation never sends `20 0B` again and never reads DRAM[0x8E55]. This register is a settling
check at startup; it is not how rotation reaches the UI.

## Key DRAM Addresses

| Address | Decimal | Name                      | Purpose                          |
|---------|---------|---------------------------|----------------------------------|
| 0x8E4A  | 36426   | `STATE_OF_CPANEL_BUTTONS` | Button state array base          |
| 0x8E55  | 36437   | Segment 0x0B status byte  | Boot-time settling check only    |
| 0x8E6A  | 36458   | Derived boot state        | 0x0C / 0x0D / 0x0E               |
| 0xBD3C  | —       | `SWBTWR_EVENT_QUEUE`      | 4-byte events, 0xFF sentinel     |
| 0xC07D  | 49277   | `SWBTWR_PAYLOAD_1`        | `0x21` identifies the data wheel |
| 0xC07E  | 49278   | `SWBTWR_PAYLOAD_2`        | The signed detent count          |
| 0xC07F  | 49279   | `SWBTWR_PAYLOAD_3`        | —                                |
| 0xC080  | 49280   | `SWBTWR_EVENT_TYPE`       | Written during dispatch          |

SwbtWr events are 4-byte structures queued by `SwbtWr_QueueMainEvent(DE, WA)`
(`dsp_config_sysex.s:1002-1013`) and dispatched by `SwbtWr_DispatchLoop`
(`dsp_config_sysex.s:930-984`), which stores the type at DRAM[0xC080] and the three payload
bytes at DRAM[0xC07D-F] before calling the registered callback. Note that DRAM[0xC07D] holds
the **payload**, not the event type.

## Dial Callback Table (RAM 0x3EF50-0x3EF6A)

Once event `0x1C0001F` is posted it reaches the focused widget through the NAKA dispatch:

| Address | Field | Description |
|---------|-------|-------------|
| 0x3EF50 | Dial Enable | Enable flag (word) |
| 0x3EF52 | `SetDialUp` callback | XWA component (clockwise) |
| 0x3EF56 | `SetDialDown` callback | XWA component (counter-clockwise) |
| 0x3EF5A | `SetDialUp` event | XBC component (event code 0x1C00007) |
| 0x3EF5E | `SetDialDown` event | XBC component |
| 0x3EF62 | `SetDialUp` param | XDE component |
| 0x3EF66 | `SetDialDown` param | XDE component |
| 0x3EF6A | Dial Focus | Currently focused UI object (32-bit) |

Named in the source since 2026-10-03 (each maincpu tree's `shared/ram_variables.s`, the same addresses
in v7, v9 and v10): `DIAL_ENABLE`, `DIAL_UP_CALLBACK`, `DIAL_DOWN_CALLBACK`, `DIAL_UP_EVENT`,
`DIAL_DOWN_EVENT`, `DIAL_UP_PARAM`, `DIAL_DOWN_PARAM`, `DIAL_FOCUS`.

`SetDialUp` / `SetDialDown` (`presentation_sound_nav.s:381-391`) are **setup** functions: they
register workspace, event code and parameter into this table. The callbacks themselves fire
when `0x1C0001F` reaches `GroupBox_HandleCursorNav`.

Related NAKA widget events: `0x1E0006F` GroupBox_DialEnable, `0x1E00070` GroupBox_DialDown,
`0x1E00071` GroupBox_DialUp, `0x1E00087` GroupBox_SetDialFocus, `0x1E00088`
GroupBox_GetDialFocus. The accompaniment engine posts `0x1E00070` / `0x1E00071` for its own
sequencer parameter changes.

## MAME Implementation

The wheel has been emulated in mainline MAME since [mamedev/mame#15919](https://github.com/mamedev/mame/pull/15919)
(merged 2026-08-31). The driver declares two input ports whose detent deltas are **summed**, so
keys and mouse both work and either may move between two scans:

| Port | Type | Notes |
|---|---|---|
| `ENCODER` | `IPT_POSITIONAL`, 24 positions, `PORT_WRAPS`, sensitivity 20, key delta 1 | Keys `[` and `]`; `PORT_FULL_TURN_COUNT(24)` |
| `ENCODER_DRAG` | `PORT_ADJUSTER(50)` | Written by the layout's Lua script as the knob is dragged in a circle |

Because the wheel is an *infinite relative* encoder, the absolute value of either control is
meaningless to the firmware — only the change between scans matters. Mainline turns each port
change into a wrap-aware delta in `kn5000_state::encoder_moved()` (a jump of more than half a
full turn is a wrap, not a move) and accumulates it with `kn5000_cpanel_device::encoder_detent()`.
The kn7000_mame overlay instead polls both ports from the panel device on each scan with
`encoder_delta()`, whose first call adopts the startup position silently.

The panel scan timer runs every 7 ms (~143 Hz). When the summed delta is non-zero the device
negates it, clamps to -16..+15, and sends `[0xD7, count]` through `send_encoder_packet()` —
deliberately **not** through `send_button_packet()`, which masks the sub-address to four bits
and so cannot carry `0x17`. Delivery is then triggered by the same INTA path as a button change.

Mainline logs each report under `LOG_BUTTONS` ("Encoder packet"); the overlay has a separate
`LOG_ENCODER`.

## Reproducibility

The static evidence lives in `notes/kn5000-wheel-probes/` in the kn7000_mame repository; each
script names the question it answers in that directory's README. `tblid.py` and `curve.py`
produced the two tables on this page. Related rigs: `tools/rigs/kn5000_wheel_bios_sweep.py`
(cross-revision verdict), `tools/rigs/kn5000_wheel_rate_test.lua` (detent-loss measurement) and
`tools/rigs/kn5000_wheel_idle.lua` (the negative control: record `0x19` never appears at idle).

## Related Pages

- [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) — the serial link the
  wheel shares with the buttons and LEDs
- [Event Codes]({{ site.baseurl }}/event-codes/) — the firmware event dispatch system
