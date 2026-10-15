---
layout: page
title: "Control-Panel Serial Timing"
permalink: /serial-debugging/
---

# Control-Panel Serial Timing (TMP94C241 I/O Interface Mode)

The KN5000's main CPU (TMP94C241) talks to the two control-panel MCUs (Mitsubishi
`M37471M2196S`, one per panel board) over **SIO channel 1** in *I/O Interface Mode* — a
synchronous, clocked serial link. No dump of the panel MCUs exists, so the panels are High
Level Emulated: the MAME device implements the protocol rather than running panel code.

This page states the timing rules that link imposes. The protocol carried over it — commands,
button packets, LED writes, the data wheel — is described in
[Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/).

## Line-Level Rules

| Property     | Value                                                                                                                                                                                                                |
|--------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Direction    | CPU drives SCLK1 while it transmits; after asserting INTA the panel drives SCLK1 for its reply (the CPU sets IOC=1)                                                                                                  |
| Bit order    | LSB first, 8 bits per byte                                                                                                                                                                                           |
| Rising edge  | Both sides **sample** the incoming bit                                                                                                                                                                               |
| Falling edge | Both sides **output** the next bit                                                                                                                                                                                   |
| Idle level   | HIGH on both data lines                                                                                                                                                                                              |
| Clock source | Timer 2 output-compare trigger (TO2)                                                                                                                                                                                 |
| Bit rate     | Reprogrammed per state through BR1CR: 31.25 kHz (0x28) to arm each command, 62.5 kHz (0x24) for the phantom bytes, 250 kHz nominal (0x14) for the two real command bytes; the panel self-clocks its reply at 250 kHz |

Pin assignment on the main CPU's Port F: bit 4 = TXD1, bit 5 = RXD1 (both are `CPDATA`), and
bit 6 reads back the SCLK1 (`CPSCK`) pin state.

### Port F bit 6 is a boot gate

The firmware's panel routine polls Port F bit 6 to confirm the serial clock is idle (HIGH)
before it sends a command. If that bit never reads high, `CPanel_WaitTXReady` gives up after 200
retries and returns as if ready. The transmit state machine (`CPanel_SM_StartTX`) then reads the
pin low and abandons the command, so the boot ping probe (`CPanel_PanelDetection`) gets no answer,
and the self-test shows **"ERROR in CPU data transmission"** (view `TEST1CP`). The driver
satisfies the check with `m_maincpu->portf_read().set_constant(0x40)`.

## Clock Gating

Mode 0 (TO2 trigger) and mode 1 (baud-rate generator) gate the clock differently:

- **Mode 0**: `IOC` (bit 0 of `SCxCR`) set to 1 means the clock arrives from the **external
  device** — the panel self-clocks over the SCLK pin after asserting INTA. The baud-rate timer
  must then not drive the line, or it injects extra edges and corrupts the byte being received.
- **Mode 1**: the baud-rate timer is the clock source regardless of `IOC`, so only mode 0 gates.

The timer keeps clocking while a TX byte is in flight, while an RX byte is incomplete, or while
a **trailing rising edge** is still owed. That trailing edge matters: without it the timer stops
on TX's last falling edge, the CPU services INTTX1 and pre-outputs bit 0 of the *next* byte, and
the following rising edge would sample that as bit 7 of the *previous* byte — corrupting every
byte's MSB.

## Byte-Boundary Synchronisation

The clock runs continuously, so both ends must agree where a byte begins. The serial device
raises a `tx_start` callback to the panel at the start of each new transmission, and the panel
resets its receive bit counter on it.

`tx_start` fires **only on an idle-to-active transition**. During initialisation the firmware
rewrites the transmit buffer repeatedly before a byte completes; if every write signalled a
start, the panel would be reset after two or three bits, forever. A write while the shift
register is busy therefore goes into the **TX buffer** (the TMP94C241 is double-buffered) and
auto-loads when the current byte finishes.

### Pre-output and the skipped falling edge

On loading the shift register the device pre-outputs bit 0 immediately, so the slave can sample
it on the very first rising edge. Whether the following falling edge must be skipped depends on
the clock phase at the moment of the write:

| Clock at write | Next edge | Behaviour |
|---|---|---|
| HIGH | falling | **Skip it.** Otherwise bit 1 is output before the receiver has sampled bit 0. |
| LOW | rising | Do not skip. The receiver samples bit 0 on that rising edge, and the following falling edge legitimately outputs bit 1. |

In code this is `m_tx_skip_first_falling = (m_sioclk_state == 1);`.

## Phantom Bytes and PFFC

`PFFC` controls whether the SCLK pin is actually driven outside the chip. On real hardware a
byte clocked out with `PFFC` off never reaches the panel, because the pin is high-impedance.

The internal shift register runs anyway — it must, so that INTTX1 fires and the firmware's TX
state machine advances. The device therefore does **not** gate the baud-rate clock or
`sclk_out_cb` on `PFFC` (gating either desynchronises the clock). Instead it passes the `PFFC`
state as the `tx_start` argument, and the panel filters: `tx_start(0)` clears
`accept_next_byte`, so the panel assembles the phantom byte and then discards it.

## SCxCR Writes Do Not Abort a Reception

Writing `SCxCR` configures IOC, SCLKS, parity and error flags; it does **not** reset the receive
bit counter. The RX shift register has its own counter that completes independently. This is
load-bearing: the firmware writes SC1CR inside the INTRX1 ISR (`CPanel_SM_RXByte1`,
`CPanel_SM_RXByteN`) to hold `IOC=1 / SCLKS=0` between received bytes, and that ISR can fire
between rising edges of the *next* byte.

## Where the Code Is

| File | Role |
|---|---|
| `src/devices/cpu/tlcs900/tmp94c241_serial.cpp` | CPU-side SIO: clock gating, shift registers, `tx_start`, TX double buffering |
| `src/mame/matsushita/kn5000_cpanel.cpp` | Panel-side HLE: bit assembly, `accept_next_byte`, packet framing |
| `src/mame/matsushita/kn5000.cpp` | Port F wiring, including the bit-6 SCLK1 idle read |

Firmware side: the `CPanel_*` routines in the disassembly's `cpanel_routines.s`.

## Related Pages

- [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) — the packet layer
- [Serial Firmware Compatibility]({{ site.baseurl }}/serial-firmware-compatibility/) — what
  custom firmware must do to drive this link
- [Data Wheel (TEMPO/PROGRAM Encoder)]({{ site.baseurl }}/data-wheel-investigation/)
