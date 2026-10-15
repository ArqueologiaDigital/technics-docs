---
layout: page
title: Boot CP-Serial Link
permalink: /boot-cpserial-link/
---

# Boot-Time Control-Panel Serial Link

The first-stage bootloader in the Table Data ROM carries **its own, complete
control-panel serial driver** — an interrupt-driven link over serial channel 1 with a
ring-buffered packet layer, a handshake, a device probe and a device classifier. It is
**not** the `CPanel_*` stack documented in
[Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/): that one lives in
the Program ROM and only starts running after the bootloader has handed control to the
main firmware.

> **Keep the two apart.** They speak the same command vocabulary to the same panel MCUs,
> but they are two independent implementations with different state machines, different
> RAM layouts and different failure modes. Nothing measured on one transfers to the
> other. The source module says this in as many words
> (`table_data/boot_cpserial.s:9-16`).

Source of truth for this page (all byte-matching disassembly, table_data ROM):

| module | ROM range | boot-time alias | contents |
|--------|-----------|-----------------|----------|
| `table_data/boot_cpserial.s` | 0x9FEC6E-0x9FF228 | 0xFFEC6E-0xFFF228 | setup, handshake, probe, polling half |
| `table_data/boot_cpserial_isr.s` | 0x9FF229-0x9FF2F1 | 0xFFF229-0xFFF2F1 | the three ISRs + state dispatch table |
| `table_data/boot_cpserial_states.s` | 0x9FF2F2-0x9FFB2E | 0xFFF2F2-0xFFFB2E | state handlers, packet codecs, ring helpers |

At reset the Table Data ROM is visible at 0xE00000-0xFFFFFF, so this code executes at its
**boot-time alias** = ROM address + 0x600000. Labels in the disassembly carry the ROM
(0x9Fxxxx) address; the 0xFFxxxx form is what the CPU actually runs and what the
interrupt vector table stores.

## Where it sits in the boot flow

The link is not brought up unconditionally. `Boot_Init` gates it on a floppy being
present, and only a specific device answer diverts the boot into the firmware-update UI:

```
Boot_Init
    │
    ├── Boot_CheckDiskPresent (0xFFEC63) — Port D bit 6, active low
    │       │
    │       └── no disk ──> skip everything below, jump to the Program ROM
    │
    ├── BootSerial_InitVectorTable[0] (0xFFEC6E) ──> BootSerial_Init (0xFFEC7E)
    │       delays · BootSerial_FullInit · handshake · BootSerial_WaitDeviceIdent
    │
    ├── Boot_ProbeExternalDevice (0xFFED0E)
    │       BootSerial_ProbeSequence + Boot_ClassifyDeviceID ──> HL = device class
    │
    ├── class != 4 ──> jump to the Program ROM (normal boot)
    │
    └── class == 4 ──> firmware-update UI (display, prompt, Boot_PerformUpdate)
```

`BootSerial_InitVectorTable` is a 4-entry `.long` table of boot-time entry points; only
entry 0 is ever fetched in this build, and the other three point at bare `ret` stubs.

## Hardware

| SFR | address | role |
|-----|---------|------|
| `SC1BUF` / `SC1CR` / `SC1MOD` / `BR1CR` | 0xD4-0xD7 | serial channel 1 |
| `PF` / `PFCR` / `PFFC` | 0x3C / 0x3E / 0x3F | SC1 pin setup; shadowed in RAM at (0x0F66)/(0x0F67) |
| `PE` / `PECR` / `PEFC` | 0x38 / 0x3A / 0x3B | PE bit 5 is the link-busy status line |
| `INTEAB` / `INTES1` | 0xE3 / 0xEB | INTA and serial-1 interrupt enables |
| `INTCLR` | 0xF8 | 0x12 = INTA, 0x22 = INTRX1, 0x23 = INTTX1 |
| `TAMOD` | 0xC8 | timer-A baud source select |

Port F bit 6 is the **line-request / line-grant** signal. A frame is armed by clearing
`PF` bit 6 with `PFCR` bit 6 set; the next state clears `PFCR` bit 6 and samples `PF`
bit 6 again — high means the line was granted and the pending INTTX1 continues the frame,
low means arbitration failed and the machine resets to idle with status bit 1 set in
(0x0F6A).

Three baud settings are used, the same three values the runtime driver uses:
`BR1CR = 0x14` while frame bytes move, `0x24` for the idle/turnaround states and `0x28`
when a frame is being armed.

## The three interrupt handlers

`boot_cpserial_isr.s` holds the whole interrupt half:

| handler | boot address | role |
|---------|--------------|------|
| `Handler_INTA` | 0xFFF229 | external interrupt A — the panel asks to send, and paces an RX transfer |
| `Handler_INTTX1` | 0xFFF2AE | SC1 transmit-buffer-empty — drives the TX states |
| `Handler_INTRX1` | 0xFFF2D0 | SC1 receive-buffer-full — drives the RX states |

`Handler_INTA` has two arms. When (0x0F63) is zero the link is idle: it reprograms the
SC1 pins for receive, arms **state 0x20** and sets the RX-active flag. When a receive is
already in flight it just steps the RX progress counter (reloading it with the 0x5C ring
size when it hits zero) and records status bit 6. Both arms exit through the same
`INTCLR` triple.

Both SC1 handlers push XWA/XHL/XIY, load the state byte and jump through the dispatch
table; the state handlers jump back to `BootSerial_TxIsrEpilogue` or
`BootSerial_RxIsrEpilogue`, which pop and `reti`.

## The 11-entry state machine

`BootSerial_StateDispatchTable` (0xFFF282, 11 × `.long` boot-time addresses) is indexed
by the state byte at RAM (0x0F62). **The state byte is a raw table offset**: it holds
0x00, 0x04, … 0x28 and is advanced or retreated with `inc 4` / `dec 4`, so the ISR needs
no scaling before the lookup.

| state | handler | what it does |
|-------|---------|--------------|
| 0x00 | `BootSerial_State_Abort` | idle/abort: sets done-abort bit 7 in (0x0F6A) |
| 0x04 | `BootSerial_State04_TxLineRequest` | requests the line, then samples PF bit 6; on refusal resets to idle with status bit 1 |
| 0x08 | `BootSerial_State08_TxFirstByte` | pushes the first frame byte and derives the frame byte count |
| 0x0C | `BootSerial_State0C_TxByteGap` | inter-byte turnaround (spin-10, pin restore, dummy `SC1BUF` write) |
| 0x10 | `BootSerial_State10_TxNextByte` | pushes a further byte; loops back to 0x0C or advances to 0x14 |
| 0x14 | `BootSerial_State14_TxTail` | closing turnaround, two dummy `SC1BUF` writes |
| 0x18 | `BootSerial_State18_TxFrameDone` | frame complete: re-arms the next frame if ≥ 2 bytes are still pending, else goes idle |
| 0x1C | `BootSerial_State_Abort` | abort |
| 0x20 | `BootSerial_State20_RxFirstByte` | stores the first received byte, derives the frame count |
| 0x24 | `BootSerial_State24_RxNextByte` | stores further bytes; on the last one clears RX-active and returns to state 0 |
| 0x28 | `BootSerial_State_Abort` | abort |

### Frame length rule

Both `State08` (TX) and `State20` (RX) derive the per-frame byte countdown at (0x0F63)
from the *first byte of the frame*, with the same rule:

```
count = 2                                  if (byte & 0x3F) <  0x30
count = (byte & 0x0F) + 3                  if (byte & 0x3F) >= 0x30
```

This is bit-for-bit the rule the runtime driver applies to `CPANEL_PACKET_BYTE_COUNT`
(the "STATE_0_TO_17" calculation in
[Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/)).
Two independent implementations, one wire format.

## Rings and transfer-control blocks

There are two levels of buffering: byte-level *serial rings* driven by the ISR, and
packet-level *transfer-control blocks* driven by the codecs.

| buffer | base | size | indices |
|--------|------|------|---------|
| RX serial ring | 0x0F79 | 0x5C bytes | tail (0x0F75), head (0x0F77) |
| TX serial ring | 0x0FD9 | 0x3C bytes | send index (0x0FD5), pending count (0x0FD7) |
| RX transfer-control block | 0x988A | 0x80 bytes | tail at base−8, head at base−4, free-slot count at base−2 |
| TX transfer-control block | 0x9914 | 0x80 bytes | same layout |

The `(base−8 / −4 / −2)` displacements are **signed**; the free-slot word is initialised
to 0x0080 by `BootSerial_FullInit` and stepped by the parser and encoder as they fill and
drain the ring.

Link state bytes worth knowing:

| address | meaning |
|---------|---------|
| 0x0F62 | state byte (raw dispatch-table offset) |
| 0x0F63 | per-frame byte countdown |
| 0x0F64 | flags: bit 0 RX active, bit 1 TX pending, bit 2 RX busy, bit 4 decode-collapse sentinel, bits 7:6 link mode |
| 0x0F6A | status/abort bits (bit 0 RX overflow, bit 1 TX arbitration failed, bit 3 frame discarded, bit 7 done/abort) |
| 0x1022+ | decoded-packet buffer (also the XOR-scramble state) |

Named in the source since 2026-10-03 (each maincpu tree's `shared/ram_variables.s`): `BOOTSERIAL_STATE`,
`BOOTSERIAL_FLAGS` and `BOOTSERIAL_STATUS`, at the same addresses in v7, v9 and v10. The rings and
transfer-control blocks have v10 names only (`BOOTSERIAL_RX_TAIL` .. `BOOTSERIAL_TX_TCB`): no v10
instruction names those addresses directly, so `name_kn5000_ram.py` had no instruction to derive the
v9/v7 addresses from.

## RX packet classes

`BootSerial_RX_ParsePackets` (0xFFF6F6) drains the RX serial ring into the RX
transfer-control ring. Each frame is classified by `(first byte & 0x38) >> 1` — the
parser shifts right by one only, so the eight entries of
`BootSerial_RxPacketDispatchTable` (0xFFF746) are 4 bytes apart and index directly.

| class | handler | behaviour |
|-------|---------|-----------|
| 0, 1 | `BootSerial_RxPkt_TwoByteScrambled` | both bytes stored, plus a third byte produced by exchanging into the 0x1022 scramble buffer and XORing with its old contents (3 control-ring slots) |
| 2 | `BootSerial_RxPkt_TwoByteDecode` | first byte stored raw, then `(C, A)` handed to an **external decoder hook** |
| 3, 4, 5 | `BootSerial_RxPkt_Discard` | both bytes consumed and dropped; status bit 3 set |
| 6, 7 | `BootSerial_RxPkt_VarLengthRun` | run header's low nibble gives `(header & 0x0F) + 1` payload bytes; each is either externally decoded (run-tag bit 4) or XOR-mixed like class 0/1 |

Parsing stops when fewer than 4 free slots remain in the control ring, or fewer than 2
bytes are available in the serial ring.

### ★ Class-2 packets always fail on a stock machine

`BootSerial_RxPkt_TwoByteDecode` does not decode anything itself. It calls
`BootSerial_CallExternalDecode` (0xFFF817), a register-saving wrapper whose whole body is:

```asm
BootSerial_CallExternalDecode:
        push    xde
        push    xiz
        push    xix
        calr    BootStub_ReturnError        ; ROM 0x9FB80E
        pop     xix
        pop     xiz
        pop     xde
        ret
```

And `BootStub_ReturnError` in the shipped ROM is two instructions:

```asm
BootStub_ReturnError:            ; ROM 0x9FB80E — bytes 33 FF FF 0E
        ldw     hl, 0xFFFF
        ret
```

The caller treats `HL == 0xFFFF` as *decode failure*: it takes the already-stored first
byte back out of the control ring (`BootSerial_CtrlRingRetreatIX`), commits the serial
tail and drops the packet. So **every class-2 packet is discarded on a stock KN5000** —
the hook exists for a decoder that this firmware does not contain. The same is true of
the decode arm of the class 6/7 variable-length handler, which calls the same wrapper.
The stub sits in a bank of five one-line stubs at 0x9FB802-0x9FB811 — four returning 0,
this one returning 0xFFFF. That grouping *looks* like the residue of optional modules
that were not linked into this build, but that reading is an interpretation; what the ROM
proves is only that the hook resolves to a constant-error return.

This is worth remembering before attributing any boot-time panel misbehaviour to the
decode path: on real hardware that path cannot succeed.

## TX packet classes

`BootSerial_TX_EncodePackets` (0xFFF90E) is the mirror image: it reads packets from the
TX transfer-control ring at 0x9914, classifies each by `(tag & 0x30) >> 4` through
`BootSerial_TxPacketDispatchTable` (0xFFF966, 4 entries), and emits frame bytes into the
TX serial ring.

| class | handler | behaviour |
|-------|---------|-----------|
| 0, 1, 2 | `BootSerial_TxPkt_TwoByte` | plain 2-byte frame |
| 3 | `BootSerial_TxPkt_VarLengthRun` | header plus `(header & 0x0F) + 2` payload bytes |

## Handshake, probe and device classification

`BootSerial_FullInit` (0xFFED1E) resets both transfer-control blocks, programs the port
F/E pin functions (keeping `PFCR`/`PFFC` shadows in RAM), sets `SC1MOD = 0x00`,
`BR1CR = 0x14`, `SC1CR = 0x01`, enables INTA and the SC1 interrupts, selects the timer-A
baud source, sends the opening frame `(0x1F, 0xDA)` and falls into
`BootSerial_HandshakeSequence` (0xFFEDD2), which sends four more frames with 3000-iteration
spin delays between them.

| stage | frames sent |
|-------|-------------|
| `BootSerial_FullInit` | `1F DA` |
| `BootSerial_HandshakeSequence` | `1F 1A`, `1D 00`, `DD 03`, `1E 80` |
| `BootSerial_ProbeSequence` (0xFFF00E) | `25 01`, `E2 04`, `20 10`, `E2 11` |
| `BootSerial_WaitDeviceIdent` (0xFFF077) | `20 0B`, repeated until the answer is stable |
| `BootSerial_ResetAndIdent` (0xFFF0FE) | `2B 00`, `EB 00`, `20 10`, `E3 10` |

Every one of these command bytes also appears in the runtime driver's command reference —
same panel MCUs, same vocabulary, different code.

`BootSerial_WaitDeviceIdent` derives an ident code from the decoded response byte at
(0x102D): bit 7 → 0x0D, else bit 6 → 0x0E, else 0x0C, and loops until two consecutive
polls agree (previous value kept at (0x1042)). This is the boot-time twin of the runtime
driver's segment-0x0B settling check (`CPanel_ButtonPollLoop`, the same bit 7 → 0x0D / bit 6 →
0x0E / else 0x0C rule). That register is not the data wheel; see
[Data Wheel]({{ site.baseurl }}/data-wheel-investigation/).

`Boot_ClassifyDeviceID` (0xFFEF89) then inspects four bytes of the decoded-packet buffer,
in this order:

| test | result |
|------|--------|
| (0x1036) == 0x6C | class 3 |
| (0x1023) == 0x70 | class 2 |
| (0x1038) == 0x38 | class 1 |
| (0x1028) == 0x0F | class 4 — **flash-update service device** |
| otherwise | class 0 (none / unknown) |

Only class 4 changes the boot path: `Boot_Init` compares `L` against 4 and runs the
firmware-update UI on a match. What classes 1-3 correspond to physically is not
established from the ROM alone — the classifier only tells us which byte of which
response distinguishes them.

## Dead and unreferenced code

A noticeable fraction of this driver is unreachable in the shipped firmware. The
disassembly marks each case with an explicit "Callers: NONE FOUND" after searching the
table_data and maincpu ROMs for both the ROM and boot-time address forms:

* `BootSerial_ModeSwitch`, `BootSerial_TestLoopback`, `BootSerial_SendTwoBytes_Bitbang`
  (a manual bit-banged transmitter), `BootSerial_PollTX` and its sync-injection block,
  and several thunks — factory or diagnostic code.
* `BootSerial_UnusedIsrEpilogue` (0xFFF5EA): a complete ISR tail with no vector, jump or
  fall-through reaching it — most likely the epilogue of a removed fourth handler.
* `BootSerial_CtrlRingRetreatIX_Dup`: one of two byte-identical duplicate pairs of the
  ring-index helpers (the RX parser calls the first pair, the TX encoder the duplicates),
  which looks like two compiler instantiations of the same inline function.

## A shared library at the tail

The last 259 bytes of `boot_cpserial_states.s` (ROM 0x9FFA2C-0x9FFB2E) are not part of
the serial driver at all. They are a hardware-channel + memory library that appears
**three times** in the KN5000 firmware:

| copy | address | peripheral base |
|------|---------|-----------------|
| table_data bootloader | 0x9FFA2C-0x9FFB2E | 0x150000 |
| maincpu program ROM (`AudioMix_*`) | 0xEF17F4-0xEF18F6 | 0x150000 |
| sub-CPU boot ROM (`INIT_TONE_GEN`, `TONE_GEN_WRITE`, …) | 0xFF84A8-0xFF85AA | 0x130000 |

The table_data and sub-CPU copies are byte-identical except for the three base-address
immediates — 259 bytes, exactly 3 differing bytes, verified by direct comparison. The
register protocol is the same in all three: `A = (channel << 5) | 0x10` is written to
base+0 as a register-address latch, then each data byte goes to base+2 with `A`
incremented between bytes. Factoring these into a shared module is a recorded follow-up,
not yet done.

## Emulation status

There is **no HLE of this driver** in MAME today; the existing
`kn5000_cpanel` device targets the runtime protocol. Because the bootloader only brings
the link up when a disk is present, and only diverts on device class 4, a normal
emulated boot never depends on it. Anyone who does implement it should note the two
traps above: the state byte is a raw table offset (not a state index), and class-2
packets can never be decoded successfully by stock firmware.

---

## See Also

- [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) — the *runtime* driver in the Program ROM (different implementation)
- [Boot Sequence]({{ site.baseurl }}/boot-sequence/) — where this link is brought up and what gates it
- [FDC Subsystem]({{ site.baseurl }}/fdc-subsystem/) — the bootloader's other big driver, disassembled in the same wave
- [Firmware Update Procedure]({{ site.baseurl }}/firmware-update-procedure/) — the path device class 4 leads to
