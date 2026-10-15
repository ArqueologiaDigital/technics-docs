---
layout: page
title: "Serial Firmware Compatibility"
permalink: /serial-firmware-compatibility/
---

# Driving the Control-Panel Serial Link from Firmware

The MAME KN5000 driver runs the **original KN5000 program ROM** and the **Another World VM**
custom ROM over the same emulated serial hardware. Both boot without the "ERROR in CPU data
transmission" dialog, and the control-panel buttons on both panel boards produce the correct LED
and menu responses, apart from an occasional phase-dependent packet misframe that is still open
(see the known-limitation note on [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/)).

The two firmwares drive the link in completely different ways, and the driver has to satisfy
both. This page states what each one does and what the emulation must therefore provide. The
line-level timing rules are in [Control-Panel Serial Timing]({{ site.baseurl }}/serial-debugging/).

## Two Ways to Drive the Same Link

| Feature | AW VM | Original Firmware |
|---------|-------|-------------------|
| Clock source | Baud rate generator (SC1MOD=0x01) | TO2 trigger (SC1MOD=0x00) |
| TX method | Polled (write + delay + read) | Interrupt-driven state machine (11 states) |
| RX method | Read SC1BUF after TX | INTA interrupt → slave mode → self-clock |
| Baud rates | Fixed 250 kHz | Varies: 31.25 / 62.5 / 250 kHz per state |
| Phantom bytes | None (all bytes are real) | 4 phantom bytes per 2-byte command |
| Response clocking | CPU sends dummy 0xFF bytes | Panel self-clocks after INTA |

## The Firmware's TX State Machine

The firmware uses an interrupt-driven state machine triggered by INTTX1 (serial transmit complete interrupt). Each SC1BUF write triggers the next state after the byte finishes transmitting:

```
CPanel_SendCommand          SM_StartTX            SM_SendByte1
─────────────────          ──────────            ────────────
BR1CR = 0x28 (31 kHz)     BR1CR = 0x24 (63 kHz) BR1CR = 0x14 (250 kHz)
PFFC off (SCLK disabled)  PFFC still off         PFFC ON (SCLK enabled)
IOC = 0 (master mode)     Write SC1BUF           Write REAL byte 1
Write SC1BUF (phantom)    (phantom)              from LED_TX_BUFFER
        │                       │                       │
        └── INTTX1 ─────────────┘── INTTX1 ─────────────┘── INTTX1 ──>

    SM_TXDelay1           SM_SendByteN           SM_TXDelay2
    ───────────           ────────────           ───────────
    DELAY_10 (~6 µs)      BR1CR = 0x14 (250 kHz) DELAY_10 (~6 µs)
    PFFC OFF               PFFC ON                PFFC OFF
    BR1CR = 0x24 (63 kHz) Write REAL byte 2       BR1CR = 0x24 (63 kHz)
    Write SC1BUF           from LED_TX_BUFFER      Write SC1BUF
    (phantom)                     │                (phantom)
         │                        │                     │
<────────┘── INTTX1 ──────────────┘── INTTX1 ───────────┘── INTTX1 ──>

    SM_TXComplete
    ─────────────
    More data? → restart SM_StartTX
    No data?   → go IDLE, disable SCLK
```

**Key observation:** Each 2-byte command produces **6 SC1BUF writes**: 4 phantom (PFFC off) + 2 real (PFFC on). The baud rate changes per state.

## The INTA Response Mechanism

After the firmware finishes transmitting, it waits for the panel to assert INTA:

```
  CPU (firmware)                    Control Panel (HLE)
  ──────────────                    ───────────────────
  TX state machine completes
  SM_TXComplete → IDLE
  SCLK stops
                                    Receives 2-byte command
                                    Queues response (2 bytes)
                                    Detects SCLK idle (50 µs)
                                    Asserts INTA on PE.5
  ┌─────────────────────────────────────────────┐
  │ INTA_HANDLER:                               │
  │   IOC = 1 (slave mode)                      │
  │   RXE = 1 (receive enable)                  │
  │   State → SM_RXByte1                        │
  └─────────────────────────────────────────────┘
                                    Self-clocks response at 250 kHz
                                    ── SCLK edges ──>
  SM_RXByte1: reads SC1BUF
  SM_RXByteN: reads SC1BUF
  Response complete → IDLE
                                    Deasserts INTA
```

## CPanel_WaitTXReady: The Timeout Gate

Before each command, the firmware calls `CPanel_WaitTXReady` which polls five conditions:

```
┌─────────────────────────────────────────────────────────┐
│  CPanel_WaitTXReady (200 retries × ~1 ms each)          │
│                                                         │
│  1. PF.6 == HIGH?    (SCLK pin at idle pull-up)         │
│  2. PE.5 == LOW?     (INTA not asserted)                │
│  3. TX flag == 0?    (no transmission in progress)      │
│  4. RX flag == 0?    (no reception in progress)         │
│  5. LED buffer empty? (no queued LED commands)          │
│                                                         │
│  ALL must pass → proceed to send command                │
│  ANY fails → DELAY_1500_LOOPS (~1 ms), retry            │
│  200 failures → stop waiting, send anyway (bit 7 set)   │
└─────────────────────────────────────────────────────────┘
```

After 200 retries (~200 ms) the firmware stops waiting and sends anyway; both exits set bit 7 of `CPANEL_PROTOCOL_FLAGS`. The "ERROR in CPU data transmission" view (`TEST1CP`) is posted by the boot self-test (`SelfTest_SramAndRom_CheckROM`) when `CPanel_ProbePanelMcus` reports that the left (bit 0) or right (bit 3) panel did not answer its ping.

## Boot Sequence Timing Diagram

```
Time    CPU Firmware                  MAME Serial Device    Control Panel HLE
─────   ────────────────────────────  ───────────────────   ──────────────────
0 ms    Hardware init (watchdog,
        memory controller, DRAM)
        │
~5 ms   Timer setup (T0/T1 cascade)
        Prescaler start (T16RUN)
        │
~8 ms   CPanel_InitHardware:
        │ SC1MOD = 0x00 (TO2 trigger)
        │ BR1CR  = 0x14 (250 kHz)     Timer starts at 250 kHz
        │ SC1CR  = 0x01 (IOC=1)
        │ INTA interrupt enabled
        │
~8.5    DELAY_6_TICKS (480 µs)
        │
~9 ms   SendCommand(0x1F, 0xDA):
        │ BR1CR = 0x28 (31 kHz)       Timer adjusts to 31 kHz
        │ PFFC off, IOC = 0 (master)
        │ SC1BUF = phantom                                  tx_start(0), reject
        │   └─INTTX1─>
        │ SM_StartTX: phantom SC1BUF                        tx_start(0), reject
        │   └─INTTX1─>
        │ SM_SendByte1: REAL 0x1F      250 kHz              tx_start(1), accept
        │   └─INTTX1─>                                      cmd_buf[0] = 0x1F
        │ SM_TXDelay1: phantom SC1BUF  62.5 kHz             tx_start(0), reject
        │   └─INTTX1─>
        │ SM_SendByteN: REAL 0xDA      250 kHz              tx_start(1), accept
        │   └─INTTX1─>                                      cmd_buf[1] = 0xDA
        │                                                   process_command()
        │                                                    → queue sync
        │                                                       response
        │                                                    → start idle_detect
        │                                                        (50 µs timer)
        │ SM_TXDelay2: phantom SC1BUF  62.5 kHz             tx_start(0), reject
        │   └─INTTX1─>                                      *** MUST NOT cancel
        │ SM_TXComplete → IDLE                                 idle_detect! ***
        │
~11 ms  DELAY_3000_LOOPS (~2 ms)                            idle_detect fires
        │                                                    → assert INTA
        │                                                    → self-clock
        │                                                       response
        │
        │ [INTA fires]
        │ INTA_HANDLER: IOC=1, RXE=1                      self-clock: 0x18, 0x00
        │ SM_RXByte1: read 0x18
        │ SM_RXByteN: read 0x00
        │ Response received OK
        │
~13 ms  Reset LED ptr
        DELAY_3000_LOOPS (~2 ms)
        │
~15 ms  CPanel_SendInitSequence:
        │ SendCommand(0x1F, 0x1A)
        │ DELAY_3000 + reset + DELAY_3000
        │ SendCommand(0x1D, 0x00)
        │ DELAY_3000 + reset + 2×DELAY_3000
        │ SendCommand(0xDD, 0x03)
        │ DELAY_3000 + reset + 2×DELAY_3000
        │ SendCommand(0x1E, 0x80)
        │ 3×DELAY_3000
        │ Enable interrupts
        │
~40 ms  CPanel_PollStartup:
        │ CPanel_WaitTXReady              <── Must pass all 5 checks
        │ SendCommand(0x20, 0x0B)
        │ DELAY_6_TICKS
        │ Process response
        │ ... (repeat until the segment 0x0B reply is stable)
        │
~55 ms  CPanel_InitButtonState:
        │ WaitTXReady + Send(0x2B, 0x00)  <── Query all left segments
        │                                       (22 bytes response)
        │ WaitTXReady + Send(0xEB, 0x00)  <── Query all right segments
        │                                       (22 bytes response)
        │ WaitTXReady + Send(0x20, 0x10)
        │
        │ WaitTXReady + Send(0xE3, 0x10)
        │
~70 ms  Init complete, enter main loop
```

## What the Emulation Must Provide

Seventeen behaviours are load-bearing. Removing any one of them reintroduces a visible failure.

### CPU serial device (`tmp94c241_serial.cpp`)

| Behaviour                                                                                             | Why                                                                                                                                           |
|-------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| The clock keeps running while **either** a TX or an RX byte is incomplete                             | Bytes complete correctly                                                                                                                      |
| A trailing rising edge is owed after TX's last falling edge                                           | Bit 7 is sampled before INTTX1 fires                                                                                                          |
| RXD is captured **before** the clock is forwarded                                                     | No sampling race                                                                                                                              |
| `IOC` is **bit 0** of `SCxCR`, and only gates the timer in TO2 mode (`SC1MOD & 3 == 0`)               | The AW VM sets IOC=1 in baud-rate mode; gating on IOC alone would stop its clock                                                              |
| TO2 trigger drives SCLK only during active transfers                                                  | Idle detection can fire                                                                                                                       |
| PFFC state is passed to the panel through `tx_start`, and the internal shift register runs regardless | Phantom bytes reach neither the panel nor a stalled TX state machine                                                                          |
| INTRX1 is flagged when RX completes                                                                   | The firmware is told a byte arrived                                                                                                           |
| Writing `SC1MOD` does **not** raise INTTX                                                             | The firmware writes SC1MOD at the start of every TX sequence; a spurious INTTX advances the state machine a byte early and corrupts LED state |
| Writing `SCxCR` does **not** abort an in-progress RX byte                                             | The INTRX1 ISR rewrites SC1CR between bytes                                                                                                   |

### Control-panel HLE (`kn5000_cpanel.cpp`)

| Behaviour | Why |
|---|---|
| INTA assert, idle detect, then panel self-clocking | The bidirectional half of the protocol |
| `accept_next_byte`, set only by `tx_start(1)` and consumed after one byte | Phantom bytes are assembled and discarded rather than parsed |
| `tx_start` flags are applied at byte boundaries, not when they arrive | MAME's synchronous execution fires `tx_start` for byte N+1 before byte N's last rising edge |
| `rx_waiting_for_start` ignores orphan clock edges after a completed byte | No byte-boundary desync |
| The idle-detect window slides: every `sioclk()` edge retriggers the 50 µs timer | It fires after the **last** byte of a burst, phantoms included |
| LED commands generate no response | The firmware batches LED writes; an INTA during the next TX sets IOC=1 and deadlocks the baud-rate timer |
| Left-panel headers are `0xC0 \| segment`, right-panel `segment` | See below |
| A segment change must be stable for **2 consecutive scans** (14 ms) before it is reported | MAME input ports momentarily return single-bit values that revert within one scan interval; a plain 100 ms debounce turns each glitch into a full press-release cycle |

### The Header Lookup Table

The firmware maps a packet header byte to a record index through a ROM table at `0xEDA03C`
(v7-v10; `0xED9F28` on v5 and `0xED9F40` on v6, with byte-identical content). Only two of the
four `bits 7:6` encodings are live:

```
[0x00-0x0A]: 0B 0C 0D 0E 0F 10 11 12 13 14 15   -> right panel (bits 7:6 = 00)
[0x20-0x2A]: all 1F                              -> DEAD ZONE   (bits 7:6 = 01)
[0x60-0x6A]: 00 01 02 03 04 05 06 07 08 09 0A   -> left panel  (bits 7:6 = 11)
```

A left-panel header of `0x40 | segment` lands in the dead zone: every event resolves to index
`0x1F`, whose action list (`PanelActions_Event31`) is empty, so no left-panel button press reaches
an action. The left panel must use `0xC0 | segment`.

This is the same table that resolves the data wheel's `0xD7` header to record `0x19`; see
[Data Wheel]({{ site.baseurl }}/data-wheel-investigation/).

## Known Deviation From Hardware

### Baud rate runs at half speed

The baud rate timer fires at `m_hz` but toggles SCLK, so the effective bit rate is `m_hz / 2`. At BR1CR=0x14 (250 kHz nominal), the actual SCLK frequency is 125 kHz. This does not break correctness; it makes the link twice as slow as real hardware.

## Key Delay Calculations

All calculations assume 16 MHz CPU clock (2 × 8 MHz XTAL).

| Delay Routine | Iterations | Time per Iteration | Total Time |
|---------------|------------|-------------------|------------|
| DELAY_6_TICKS | 6 timer ticks | 80 µs/tick | **480 µs** |
| DELAY_51_TICKS | 51 timer ticks | 80 µs/tick | **4.08 ms** |
| DELAY_10_LOOPS | 10 | ~625 ns | **~6 µs** |
| DELAY_300_LOOPS | 300 | ~625 ns | **~188 µs** |
| DELAY_1500_LOOPS | 1500 | ~625 ns | **~938 µs** |
| DELAY_3000_LOOPS | 3000 | ~625 ns | **~1.875 ms** |

Timer tick rate: 12,500 Hz (T0/T1 cascade from 16 MHz ÷ prescaler).
Loop timing: DEC 1, WA (2) + CP WA, 0 (2) + JR Z (2) + JR T (4) = ~10 cycles = 625 ns.

## Code References

**MAME driver files (editable):**
- `src/devices/cpu/tlcs900/tmp94c241_serial.cpp` — CPU serial channel
- `src/mame/matsushita/kn5000_cpanel.cpp` — Control panel HLE
- `src/mame/matsushita/kn5000.cpp` — Main driver wiring

**Firmware reference (read only):**
- `v10/maincpu/ui/cpanel_routines.s` — TX state machine, `CPanel_WaitTXReady`, INTA handler
- `v10/maincpu/shared/sfr_tmp94c241.s` — SFR register addresses

**Related documentation:**
- [Control-Panel Serial Timing]({{ site.baseurl }}/serial-debugging/) — edge roles, byte-boundary sync, phantom bytes
- [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) — Command format, button segments, LED commands

---

*This is part of the ongoing effort to create a working MAME emulator for the Technics KN5000 music keyboard. See the [main documentation]({{ site.baseurl }}/) for more details on the project.*
