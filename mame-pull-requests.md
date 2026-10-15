---
layout: page
title: MAME Pull Requests
permalink: /mame-pull-requests/
---

# MAME Pull Requests for KN5000 Emulation

This page records the series of pull requests (all merged by 2026-03-24) to upstream MAME that implement functional emulation of the Technics KN5000 music keyboard. The changes span the TLCS-900/H CPU core, the TMP94C241 microcontroller, and the KN5000 machine driver.

> **Context**: The Technics KN5000 is a 1997 professional arranger keyboard built around dual Toshiba TMP94C241F processors (TLCS-900/H family). Its program (v5-v10, extracted from the update floppies), table-data, custom-data and rhythm ROMs, and one of its four waveform ROMs (IC307), are preserved. Program v3/v4 and waveform IC304-IC306 are not, the sub-CPU boot ROM (IC30) is only partly read, and the control-panel MCU ROMs are undumped. The v7, v9 and v10 programs, the table data, the custom data, the sub-CPU payload and boot ROM and the HD-AE5000 ROM are disassembled into sources that rebuild byte-identically. A MAME skeleton driver has existed since 2024 but could not get beyond early boot because the CPU core lacked features. These PRs fixed that: the driver now boots to its main screen with real voice names and responds to the control panel. Upstream it is still flagged `MACHINE_NOT_WORKING | MACHINE_NO_SOUND`: it has no tone generator and no MIDI port, and its floppy controller is not mapped.
>
> **See Also**: [SubCPU Payload Loading]({{ site.baseurl }}/subcpu-payload-loading/) for the investigation that identified these issues, [Boot Sequence]({{ site.baseurl }}/boot-sequence/) for overall firmware flow, and [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) for the serial protocol implemented by the HLE.

## Dependency Graph

The PRs form a dependency chain. PR 1 and PR 2 are independent and can be reviewed simultaneously. Each subsequent PR builds on the previous.

```
PR 1 (LDC CR mapping) ──┐
                         ├── PR 3 (DMA + port fix) ── PR 4 (serial) ── PR 5 (KN5000 driver)
PR 2 (EI/RETI shadow) ──┘
```

## Overview of Changes

| PR | Scope | Files Changed | New Files | Risk Level |
|----|-------|---------------|-----------|------------|
| [1](#pr1) | TLCS-900/H core | 900tbl.hxx, dasm900.cpp, dasm900.h, tmp94c241.cpp, tmp95c061.cpp, tmp95c063.cpp, tmp96c141.cpp | --- | None (additive + structural refactor) |
| [2](#pr2) | TLCS-900/H core | 900tbl.hxx, tlcs900.cpp, tlcs900.h | --- | Low (all variants) |
| [3](#pr3) | TMP94C241 only | tmp94c241.cpp, tmp94c241.h | --- | None (TMP94C241 only) |
| [4](#pr4) | TMP94C241 only | tmp94c241.cpp, tmp94c241.h | tmp94c241_serial.cpp/h | None (TMP94C241 only) |
| [5](#pr5) | KN5000 driver | kn5000.cpp, kn5000.lay | kn5000_cpanel.cpp/h | None (KN5000 only) |

---

## PR 1: TLCS-900/H --- LDC Control Register Mapping for TMP94C241 DMA Registers {#pr1}

<div style="background: #d4edda; border: 3px solid #28a745; border-radius: 8px; padding: 16px; margin: 16px 0; font-size: 1.1em;">
<strong>&#10003; STATUS (October 2026):</strong> All 5 PRs were <strong>merged upstream</strong> by 2026-03-24. Three later KN5000 PRs have merged too: #15878 (Feature Presentation demo), #15919 (TEMPO/PROGRAM data wheel) and #16415 (floppy software list, 35hd drive). See the <a href="{{ site.baseurl }}/mame-branch-review/">Branch Review &amp; Roadmap</a> page for the full upstreaming state and the remaining candidates.
</div>

**Upstream PR:** [mamedev/mame#14970](https://github.com/mamedev/mame/pull/14970) (merged)

**Branch:** [`kn5000_pr1_ldc_cr_mapping`](https://github.com/felipesanches/mame/tree/kn5000_pr1_ldc_cr_mapping)

### Summary

Add TMP94C241 DMA control register encodings to the TLCS-900/H CPU core's `LDC` instruction handler, and refactor the disassembler's CR register name resolution from hardcoded switch blocks into model-specific symbol tables.

### Problem

The `LDC` (Load Control Register) instruction uses an immediate byte to select which internal register to access. The TLCS-900/H family shares the same instruction encoding, but different chip variants place their DMA registers at different offsets within the control register space.

MAME's existing implementation only handles the TMP96C141/TMP95C061/TMP95C063 encodings:

| Register | TMP96C141/TMP95C061/TMP95C063 | TMP94C241 |
|----------|-------------------------------|-----------|
| DMAM0-3 (CR8) | 0x22, 0x26, 0x2A, 0x2E | 0x42, 0x46, 0x4A, 0x4E |
| DMAC0-3 (CR16) | 0x20, 0x24, 0x28, 0x2C | 0x40, 0x44, 0x48, 0x4C |
| DMAD0-3 (CR32) | 0x10, 0x14, 0x18, 0x1C | 0x20, 0x24, 0x28, 0x2C |

Without the TMP94C241 cases, `LDC cr,DMAMn` instructions write to a dummy register and DMA never configures correctly. This was the first bug identified in the KN5000 payload loading investigation --- the Main CPU's firmware uses `LDC` extensively to set up the HDMA transfers that carry the 192 KB sub-CPU payload (nine blocks, 524,288 B in all).

Additionally, the disassembler had all variants' CR register names hardcoded in the shared `dasm900.cpp`, which doesn't scale well as new variants are added. The existing SFR symbolic names already use a model-specific table pattern --- CR register names should follow the same approach.

### Changes

- **`900tbl.hxx`**: Add TMP94C241 cases to the six existing `switch` blocks in `prepare_operands()` (three for operand 1, three for operand 2). Each block gains four new `case` entries mapping the TMP94C241 offsets to the same `m_dmam[]`, `m_dmac[]`, and `m_dmad[]` arrays. Existing TMP96C141/TMP95C061/TMP95C063 cases are unchanged.

- **`dasm900.h`**: Add a `cr_sym` struct (`{size, encoding, name}`) for model-specific control register names, a new constructor overload accepting a CR symbol table alongside the existing SFR symbol table, and a private `cr_name()` lookup helper.

- **`dasm900.cpp`**: Replace six hardcoded `switch` blocks for `O_CR8`/`O_CR16`/`O_CR32` operands (two copies --- one for operand 1, one for operand 2) with table-driven lookups via `cr_name()`. This removes all variant-specific register names from the shared disassembler code.

- **`tmp94c241.cpp`**: Define a `tmp94c241_cr_syms[]` table with TMP94C241 DMA register encodings and pass it to the disassembler constructor.

- **`tmp96c141.cpp`**, **`tmp95c061.cpp`**, **`tmp95c063.cpp`**: Move their existing DMA CR register names (previously hardcoded in `dasm900.cpp`) into model-specific `*_cr_syms[]` tables, following the same pattern.

### Risk Assessment

**None.** The CPU core change only adds new `case` entries to existing `switch` statements --- all existing cases are untouched and the new encodings do not overlap with any existing variant's register map. The disassembler refactoring is purely structural: the same register names are resolved for the same encodings, just driven by per-variant tables instead of a shared switch. No existing driver is affected.

### Design Note: Why `900tbl.hxx` Is Not Model-Specific

The disassembler's CR register names were moved to model-specific files, but the emulation-side CR register mapping in `900tbl.hxx` (`prepare_operands()`) was intentionally left as a shared switch with all variants' cases together. We considered the same model-specific split but decided against it for three reasons:

1. **Performance.** `prepare_operands()` runs on every instruction in `execute_run()` --- it is the hottest path in the CPU emulation. The compiler optimizes the `switch` into a jump table. Replacing it with virtual dispatch or a table lookup would add overhead to every LDC instruction for no functional benefit.

2. **No overlap.** The encoding values are disjoint between variants (TMP94C241 uses 0x42--0x4e for DMAM, TMP96C141 uses 0x22--0x2e). A TMP94C241 binary will never contain TMP96C141 encodings, and vice versa. Both sets of `case` entries coexist harmlessly in the same switch --- extra cases that are never reached have zero runtime cost.

3. **Alternatives are worse.** Separating the behavior would require one of: (a) virtual method dispatch per LDC instruction, (b) a runtime table search, (c) overriding the entire 2000+ line `prepare_operands()` in each variant, duplicating 99% shared logic, or (d) an `if (type() == TMP94C241)` guard before variant-specific switch blocks, which adds a runtime branch on every LDC and duplicates the shared DMAS0--3 cases into both branches. None of these improve correctness, and all add complexity or overhead.

The encoding byte itself acts as an implicit variant discriminator --- a TMP94C241 binary will never emit encoding `0x22` for DMAM0, so the TMP96C141 case for `0x22` is simply never reached when running TMP94C241 firmware. The compiler merges all cases into a single jump table where unreachable entries cost nothing. Each `case` in the source is annotated with a comment identifying which variant(s) use that encoding, making the shared switch self-documenting.

The disassembler refactoring was worthwhile because disassembly is not performance-critical and the model-specific symbol table pattern was already established. For the instruction decoder, extra `case` entries in a shared switch are the idiomatic MAME approach for handling variant differences in the TLCS-900 core.

### Datasheet Reference

The TMP94C241 control register map is documented in the Toshiba TMP94C241F Data Sheet, Section 5 "DMA Controller", Table 5-1 "DMA Register Map". The offsets differ from TMP96C141 because the TMP94C241 has a larger internal register file with additional peripheral blocks occupying the 0x20-0x3F range.

---

## PR 2: TLCS-900/H --- EI/RETI Interrupt Acceptance Shadow {#pr2}

**Upstream PR:** [mamedev/mame#14995](https://github.com/mamedev/mame/pull/14995) (merged)

**Branch:** [`kn5000_pr2_irq_inhibit`](https://github.com/felipesanches/mame/tree/kn5000_pr2_irq_inhibit)

### Summary

Implement the documented 1-instruction interrupt deferral after `EI` and `RETI` instructions, matching real TLCS-900/H hardware behavior.

### Problem

Per the Toshiba TLCS-900/H Programming Manual (Section 8.2 "Interrupt Processing"), interrupt acceptance is inhibited for one instruction following `EI` or `RETI`. This is an architectural feature of the TLCS-900/H family, not specific to any single variant.

Without this deferral, the common firmware pattern:

```asm
EI 0        ; Enable all interrupt levels
NOP         ; This MUST execute before any IRQ is accepted
EI 6        ; Restrict to level 6+ only
```

fails because `EI 0` immediately triggers a pending interrupt before `NOP` executes. The interrupt handler runs, returns via `RETI`, and the CPU re-enters the handler infinitely --- `EI 6` never executes, and the CPU is stuck.

This pattern appears extensively in the KN5000 firmware (hundreds of occurrences) and likely in other TLCS-900/H firmware as well. The real hardware's 1-instruction shadow prevents this problem.

### Changes

- **`tlcs900.h`**: Add `bool m_irq_inhibit` member to `tlcs900_device` (the base class for all TLCS-900/H variants).

- **`tlcs900.cpp`**:
  - Register `m_irq_inhibit` in `device_start()` for save states.
  - Initialize to `false` in both `tlcs900_device::device_reset()` and `tlcs900h_device::device_reset()`.
  - In `execute_run()`: when `m_check_irqs` is set and `m_irq_inhibit` is true, clear the inhibit flag but skip the IRQ check for this cycle. On the next iteration (after one instruction has executed), the IRQ check proceeds normally. If `m_check_irqs` is not set, clear `m_irq_inhibit` unconditionally.

- **`900tbl.hxx`**: Set `m_irq_inhibit = true` in `op_EI()` and `op_RETI()`.

### Risk Assessment

**Low.** This change affects all TLCS-900/H variants (TMP96C141, TMP95C061, TMP95C063, TMP94C241). It is documented hardware behavior, and the implementation is minimal (a single boolean flag). If any existing driver were relying on the incorrect immediate-acceptance behavior (e.g., using `EI` without a guard `NOP`), it could see a timing change. However, real hardware has always had this shadow, so any such driver was already accidentally working.

Drivers using TLCS-900/H variants that should be regression-tested:
- `ngp` (Neo Geo Pocket --- TMP95C061)
- `taitotz` and `taitopjc` (Taito Type-Zero and Taito Power-JC System, whose I/O CPU is a TMP95C063)

### Datasheet Reference

Toshiba TLCS-900/H Programming Manual, Section 8.2: "After the EI instruction or RETI instruction is executed, the interrupt acceptance is inhibited for one instruction period."

---

## PR 3: TMP94C241 --- DMA Subsystem (HDMA + DMAR) and Port Read Fix {#pr3}

**Upstream PR:** [mamedev/mame#15003](https://github.com/mamedev/mame/pull/15003) (merged)

**Branch:** [`kn5000_pr3_dma_and_port`](https://github.com/felipesanches/mame/tree/kn5000_pr3_dma_and_port)

**Depends on:** PR 1 + PR 2

### Summary

Implement the TMP94C241's complete DMA subsystem and fix the port read behavior to match real hardware.

### Problem

The existing TMP94C241 device in MAME has empty stubs for `tlcs900_check_hdma()` and no DMA transfer logic. The KN5000's Main CPU relies heavily on DMA for two critical operations:

1. **HDMA (Hardware DMA)**: Triggered by interrupt events. The Main CPU uses HDMA for the sub-CPU boot transfers: 524,288 B in all, five 64 KB blocks from table data plus the 192 KB payload. Each time the SubCPU acknowledges a byte via INT5, the HDMA engine automatically transfers the next byte without CPU intervention. Nine bulk transfers (5x 64KB config blocks + 4 payload blocks) use this mechanism.

2. **DMAR (Software DMA)**: Triggered by writing to SFR register 0x109. The SubCPU uses DMAR to receive inter-CPU command bytes --- each INT0 event triggers one DMAR write, transferring a single byte from the latch at `0x120000` to RAM. This is how the SubCPU receives sound program change commands, mixer settings, and other real-time data from the Main CPU after boot.

Additionally, `port_r()` always returned the external pin level, but real TMP94C241 hardware returns the output latch value for bits configured as output. Firmware that reads back its own output port state (a common pattern for read-modify-write operations) got wrong values.

### Changes

- **`tmp94c241.h`**:
  - Add declarations for `tlcs900_process_hdma()`, `tlcs900_process_software_dma()`, and `dmar_w()`.

- **`tmp94c241.cpp`**:
  - **`tlcs900_process_hdma(channel)`**: Implements one HDMA transfer for a channel. Looks up the channel's DMA start vector, checks if the corresponding interrupt flag is pending (the DMA trigger condition), performs one transfer according to the DMAM mode register, decrements the transfer count, and fires INTTC on completion. Clears the triggering interrupt flag after the transfer (consuming the interrupt instead of dispatching to the handler).
  - **`tlcs900_process_software_dma(channel)`**: Same transfer logic as HDMA but triggered by DMAR register writes instead of interrupt events. One write = one transfer unit.
  - **`tlcs900_check_hdma()`**: Checks all four channels in priority order (0 highest). Only processes one transfer per call to maintain correct timing. Skips processing when all interrupts are masked.
  - **`tlcs900_check_irqs()`**: Added HDMA priority --- interrupts targeted by active HDMA channels are skipped (consumed by DMA instead of dispatching to the interrupt handler). Added INT0 level-detect re-assertion for level-triggered interrupt mode. Added `debug()->interrupt_hook()` for MAME debugger integration.
  - **`dmar_w()`**: Handler for SFR 0x109 writes. Each set bit triggers one software DMA transfer on the corresponding channel.
  - **`port_r()`**: Now returns `(latch & direction) | (external & ~direction)`, correctly mixing output latch bits with external pin levels based on the port control register.
  - **DMAM decoding**: Uses switch-based transfer mode decoding (byte/word/long, increment/decrement/fixed) matching the proven TMP95C061 implementation already in MAME.

### Risk Assessment

**None.** All changes are within the TMP94C241 device. No other TLCS-900/H variant or driver is affected.

### Datasheet Reference

TMP94C241F Data Sheet:
- Section 5.1 "HDMA Operation" --- interrupt-triggered DMA with priority over normal interrupt dispatch
- Section 5.2 "DMAR Register" --- software DMA trigger at SFR 0x109
- Section 5.3 "DMAM Register" --- transfer mode encoding (bits 4:0)
- Section 9.2 "Port Read Operation" --- output latch vs. external pin multiplexing based on PxCR

---

## PR 4: TMP94C241 --- Serial Port Sub-Device {#pr4}

**Upstream PR:** [mamedev/mame#15015](https://github.com/mamedev/mame/pull/15015) (merged)

**Branch:** [`kn5000_pr4_serial`](https://github.com/felipesanches/mame/tree/kn5000_pr4_serial)

**Depends on:** PR 3

### Summary

Replace the inline serial port stubs with a proper sub-device implementation supporting synchronous I/O interface mode, baud rate generation, TX double buffering, and data callbacks for connecting external devices.

### Problem

The existing TMP94C241 serial implementation consists of inline stubs that immediately set the TX-complete interrupt flag on every write to `SCxBUF`. This was sufficient for early bringup but cannot support any real serial communication. The KN5000 uses both serial channels:

- **Serial Channel 0**: MIDI In/Out at 31.25 kbaud (standard MIDI rate). Uses UART mode with the baud rate generator.
- **Serial Channel 1**: Control panel communication at 250 kHz (fc/16 / 4, `BR1CR = 0x14`; 31.25 kHz during initialisation) using synchronous I/O interface mode. The Main CPU exchanges button/LED/encoder data with the control panel MCU (whose ROM is not dumped) via a clocked serial protocol.

### Changes

- **`tmp94c241_serial.h`** (new file): Device class for `tmp94c241_serial_device`. Exposes:
  - `txd()`, `rxd()`, `sclk_out()`, `sclk_in()` callbacks for connecting to external devices
  - `tx_start()` callback signaling the start of each byte transmission (with PFFC pin function state, allowing connected devices to distinguish real transmissions from phantom ones during pin reconfiguration)
  - SFR register accessors: `scNbuf_r/w`, `scNcr_r/w`, `scNmod_r/w`, `brNcr_r/w`

- **`tmp94c241_serial.cpp`** (new file): Full implementation:
  - **I/O interface mode** (SCxMOD bits 1:0 = 0): Synchronous clocked serial. Supports internal clock (baud rate generator) and external clock (IOC=1) sources. Data is shifted MSB-first on clock edges.
  - **Baud rate generator**: Configurable via BRxCR register with 4-bit divisor and clock source selection. Drives a timer that toggles SCLK at the configured rate.
  - **TX double buffering**: CPU writes to SCxBUF go to the TX buffer. If the shift register is idle, the buffer auto-transfers immediately. If the shift register is busy, the buffer holds data until the current byte finishes, then auto-loads on the trailing rising edge. This matches real TMP94C241 hardware behavior and prevents byte loss during back-to-back transmissions.
  - **TX/RX shift registers**: 8-bit shift with proper edge timing. TX pre-outputs bit 0 before the first clock edge so the receiver can sample it on the rising edge. RX samples on rising edges and fires INTRX when 8 bits are received.
  - **SCLK output**: Forwarded to connected devices via callbacks, enabling clocked protocols.
  - **TO2 trigger**: Timer 1 match events are forwarded to serial channels for mode 0 transfer gating.

- **`tmp94c241.cpp`**: Replace inline serial stubs with sub-device delegation. Serial register mappings in `internal_mem()` now route to `m_serial[0]` and `m_serial[1]`. Add `device_add_mconfig()` to instantiate the two serial sub-devices. Set TX-complete flags (`INTES0`/`INTES1` bit 7) at `device_reset()` to indicate empty TX buffers at power-on.

- **`tmp94c241.h`**: Add `#include "tmp94c241_serial.h"`, friend declaration, `device_add_mconfig()` override, `required_device_array<tmp94c241_serial_device, 2> m_serial`. Remove old inline serial member variables (`m_serial_control`, `m_serial_mode`, `m_baud_rate`).

### Risk Assessment

**None.** All changes are within the TMP94C241 device and its new sub-device. No other driver is affected. The sub-device's callbacks are optional --- if not connected by a driver, they are no-ops, preserving backward compatibility.

### Datasheet Reference

TMP94C241F Data Sheet:
- Section 7 "Serial Interface" --- I/O interface mode, UART mode, baud rate generator
- Section 7.3 "Baud Rate Generator" --- divisor and clock source configuration
- Section 7.4 "Transmit/Receive Operation" --- shift register timing, double buffering
- Table 7-1 "Serial Control Register (SCxCR)" --- IOC, SCLKS, error flags

---

## PR 5: KN5000 Driver --- Control Panel HLE, SubCPU Payload Transfer {#pr5}

**Upstream PR:** [mamedev/mame#15143](https://github.com/mamedev/mame/pull/15143) (merged)

**Branch:** [`kn5000_interactive_control_panel`](https://github.com/felipesanches/mame/tree/kn5000_interactive_control_panel) (the head that merged; `kn5000_pr5_driver` is an earlier, larger version that also carried MIDI ports and `perfect_quantum`)

**Depends on:** PR 4

### Summary

Rework the KN5000 machine driver from a non-functional skeleton to a working system that boots to normal operation with sound program selection and control panel interaction.

### Problem

The existing KN5000 driver defines the basic hardware layout (two TMP94C241 CPUs, ROM regions, LCD) but cannot proceed past early boot because:

1. The firmware validates backup SRAM contents and enters diagnostic mode if validation fails (NVRAM is empty on first run). Not addressed by the merged PR: IC21 became NVRAM only in #15878, and no factory-default seeding was merged.
2. The SubCPU memory map lacks mappings for the tone generator, DSP, inter-CPU latch, and waveform RAM, causing unmapped memory accesses.
3. No scheduling synchronization between CPUs, making the latched inter-CPU communication unreliable. Not addressed by the merged PR, which has no `perfect_quantum`.
4. The control panel MCU ROM is not dumped, so the serial protocol to the panel has no responder.
5. No keybed input mechanism exists. Not addressed: the keybed port is a `noprw()` stub.

### Changes

- **`kn5000.cpp`** (major rework):
  - **Sub-CPU payload**: Replaces the never-mapped, uncompressed `subprogram` region with version-matched compressed sub-CPU payloads (v1.40-v1.42) overlaid on the `custom_data` region (IC19) at `0xE0000`, which is where the system update floppies write them. During boot the Main CPU decompresses the payload from there and sends it to the SubCPU through the inter-CPU latches.
  - **SubCPU memory map stubs**: Maps the tone generator (IC303) at `0x100000`, its keybed data/status port at `0x110000`, DSP1 (IC311) at `0x130000` and the waveform RAM at `0x1E0000` as `noprw()` stubs, so the SubCPU's initialisation no longer reads `0xFF` from unmapped space and the inter-CPU handshake completes. Device emulation was left for later changes.
  - **Not merged**: The earlier, larger `kn5000_pr5_driver` branch also seeded the backup SRAM with factory defaults, called `perfect_quantum` on inter-CPU latch writes and wired serial channel 0 to `midi_port` devices. None of that is in #15143: IC21 is plain RAM there, and no MIDI port is wired.

- **`kn5000_cpanel.cpp`** (new file): Control panel HLE implementing the serial protocol between the Main CPU and the control panel MCU. The control panel MCU's ROM is not dumped, so HLE is the only option. Key features:
  - **INTA-driven sessions**: The panel asserts INTA to request attention, then exchanges button/LED data via synchronous serial on channel 1. Each session consists of 8 segments of 8 bytes each (64 bytes total), carrying button states inbound and LED states outbound.
  - **Button mapping**: 85+ buttons mapped to MAME input ports, organized by panel region (transport, sound selection, accompaniment, registration, numeric pad, etc.).
  - **LED output routing**: LED states received from the firmware are routed to MAME layout output elements, enabling the layout to display button backlighting.
  - **Rotary encoder input**: Tempo, volume, and data entry encoders generate delta values in the protocol format expected by the firmware.

- **`kn5000_cpanel.h`** (new file): Header for the control panel HLE device class.

- **`kn5000.lay`**: LED output element names updated to match the names emitted by the control panel HLE, enabling proper LED visualization.

### Result

With all five PRs applied, the KN5000 driver:
1. Boots from power-on through the complete boot sequence (ROM validation, SubCPU payload transfer, hardware initialization)
2. Displays the main screen with voice names (Piano, Bigband Brass, Modern E.P.1), rhythm patterns, and mixer levels
3. Responds to control panel buttons for sound selection, menu navigation, and parameter editing
4. SubCPU processes inter-CPU commands in real-time (no "Sound Name Error" messages)

### Risk Assessment

**None.** All changes are within the KN5000 driver and its new HLE device. No other driver or shared code is affected.

---

## Testing Notes

The complete change set has been tested with the following ROM set:

- `kn5000_v10_program.rom` (Main CPU program, 2 MB; BIOS `v10`)
- `kn5000_subcpu_boot.ic30` (SubCPU boot ROM, 128 KB; `BAD_DUMP`, partly read)
- `kn5000_table_data_rom_even.ic3` + `kn5000_table_data_rom_odd.ic1` (Table data, 2 x 1 MB)
- `kn5000_custom_data_rom.ic19` (Custom data, 1 MB)
- `kn5000_subprogram_v142_compressed.rom` (compressed sub-CPU payload v1.42, loaded into the custom-data region at `0xE0000`)
- `kn5000_rhythm_data_rom.ic14` (Rhythm data, 4 MB)
- `kn5000_waveform_rom.ic307` (Wave ROM, 4 MB; IC304-IC306 are `NO_DUMP`)

**Test scenarios verified:**
- Cold boot with empty NVRAM
- Warm boot with existing NVRAM (user settings preserved)
- SubCPU boot transfers complete (9 HDMA blocks, 524,288 B, including the 192 KB payload)
- Sound program selection via control panel buttons
- Menu navigation (display updates correctly)

---

# MN10300 family: the ROM-record contribution

*Submitted 2026-08-18, merged 2026-08-23. A separate line of work from the KN5000 PRs above:
those improve an existing driver, this creates one.*

**Upstream PR:** [mamedev/mame#15911](https://github.com/mamedev/mame/pull/15911) — "matsushita/kn7000.cpp:
add ROM records for the Technics SX-KN series" (merged 2026-08-23)

## Why a driver with no CPU

When this was submitted, MAME had an MN10300 **disassembler** but no execution core
(`scripts/src/cpu.lua` said "disassembler only"), so no CPU device could be instantiated for the
KN7000, KN6000, KN6500, KN2400 or KN2600. Rather than wait, the first contribution declares **ROM
records only**, following the precedent of `src/mame/bfm/bfm_sc6.cpp` — an 80-line driver with no
CPU and a machine-config body reading `// nothing yet`. The part is named in a commented-out line in
each machine configuration so the hardware stays documented until a core exists. That has since
changed: [#16250](https://github.com/mamedev/mame/pull/16250) (merged 2026-10-07) added the MN10300
execution core (`MN103002A`) and the running driver for all five machines, still flagged
`MACHINE_NOT_WORKING | MACHINE_NO_SOUND`.

## What it contains

As merged (one commit, 403 insertions, two files — `src/mame/mame.lst` and
`src/mame/matsushita/kn7000.cpp`, nothing modified or deleted): five machines, eleven dumped
images, thirty undumped declarations.

Every device gets a line under its real part number and manual-verified capacity. Anything that is
not an honest dump of that machine's own part is **`NO_DUMP` with the correct expected size**, never
shipped as substitute data — see [ROM Dumping Roadmap]({{ site.baseurl }}/rom-dumping-roadmap/) for what remains.

**Follow-up work since then:** the flash-device type went upstream in
[#16192](https://github.com/mamedev/mame/pull/16192) (merged 2026-09-19), which added
`FUJITSU_29LV160B` (the MBM29LV160B) with the KN7000 as its consumer. No `MX29LV160B` type was
added. The **KN6000 expansion connector** and its board are open as
[#16220](https://github.com/mamedev/mame/pull/16220) (separate `bus/technics/kn6000/` files). The
board is now named the **HD-SX6**, because the firmware held is the HD-SX6's; the HD-SX3's firmware
has not been dumped.

## The flash device IDs were read, not guessed

MAME can model a flash chip well enough to answer real erase and program command sequences, but the
manufacturer and device ID are functional: the firmware performs a JEDEC autoselect and compares the
response against its own table before it will program anything. Get them wrong and the firmware
silently refuses the part.

The table is in the ROM, and it carries the part names as plain ASCII:

```
  mfr 0x04  dev 0x2249  35 sectors   " MBM29LV160B "
  mfr 0xc2  dev 0x2249  35 sectors   " MX29LV160B  "
  mfr 0x1f  dev 0x00c0  40 sectors   " AT49BV16X4  "
```

35 sectors is exactly a 16 Mbit bottom-boot map (16K + 2x8K + 32K + 31x64K). The KN6000 and KN6500
tables hold the first and third entries only; the KN7000 (2002) adds Macronix, which the KN6000
(1999) does not have — Panasonic second-sourced over time, so **absence from a table is not
evidence that a part number is wrong**.

> This also corrected the driver: the KN7000 service manual captions IC21 as "32M FLASH", but every
> part the firmware accepts is 16 Mbit, so a 32 Mbit device would fail its own autoselect check.
> With a `0x200000` sector map and a 2 MB decode window, that is three independent reasons against
> one printed caption.

## Custom-data flash as a BIOS choice

The custom flash is populated from a floppy, not at the factory. Nine images are declared for the
KN7000 as `ROM_SYSTEM_BIOS` options — the factory Initial Data Disk plus eight published data sets
(Blue Bayou, Piano Player, Jazz Organ Soloist, Bob's Band, Traditional Melody, Jogeh 1, Vibraphone,
Italian Accordion 7) — because a real instrument holds exactly one at a time. They load at offset
`0x20000` in a `ROMREGION_ERASEFF` region, so the untouched boot sectors read `0xFF` as erased flash
does.

> **Superseded upstream (2026-10-11).** [#16394](https://github.com/mamedev/mame/pull/16394) freed
> the BIOS axis for the program firmware builds (`sp7001`, `v16` (default), `v15`, `v14`). `kn7000`
> now loads only the factory default `01ctmini.ic21` directly. The nine data sets moved to the
> `kn7000_flop` software list as three reconstructed floppies (`idd7000`, `custom1`, `custom2`).

## Build notes

```
make SUBTARGET=kn7000 SOURCES=src/mame/matsushita/kn7000.cpp USE_QTDEBUG=0 -j6
./kn7000 -validate
```

> **Adding a new `#include` to a driver requires `REGENIE=1`** on a `SOURCES=` build. Without it the
> dependency scan stays cached, the new device's source is never compiled, and the link fails with
> an undefined constructor that reads like a missing definition rather than a stale project.
