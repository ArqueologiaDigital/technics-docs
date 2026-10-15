---
layout: page
title: "SNS NMI Emulation"
permalink: /sns-nmi-emulation/
---

# SNS NMI Emulation — Power-Off Checksum Mechanism

> **Update (2026-08).** The problem this page describes is **fixed**. The sections below on
> the boot-time write tap and the proposed `MACHINE_NOTIFY_POWER_OFF` upstream hook describe
> an earlier, abandoned attempt — the write tap was removed (it caused the KN5000 "Sound Name
> Error" bug) and no MAME core change was needed. The shipped fix is a **modelled POWER
> switch** (see "Current Solution" below) that pulses the CPU's real `~NMI` line and gives
> the firmware's own `NMI_StorePayloadChecksums` handler real CPU cycles to run before MAME
> exits. The technical description of the firmware's own checksum behaviour in the sections
> that follow is unchanged and still accurate.
>
> The POWER switch lives only in the `kn7000_mame` overlay. Mainline MAME's `kn5000` has
> neither it nor the write tap, so there the firmware's power-down code never runs.

## The Problem

The KN5000 shows "ALL INITIAL SETTING!" on every boot instead of the splash animation when payload checksums at DRAM[0xFFD4/0xFFD2] are invalid.

## Real Hardware Behavior

On the real KN5000, the power supply has an SNS (sense) monitoring circuit that detects when AC mains power is removed. Before the DC voltage drops below the CPU's operating threshold, the SNS circuit asserts the CPU's `~NMI` pin. The CPU has a few milliseconds of execution time on remaining capacitor charge.

### Boot Sequence

1. `Boot_DisplayScreen` (0xEF0620) writes 0x80 to internal CPU RAM[0x0400] (arms the NMI guard)
2. `Boot_DisplayScreen` then clears DRAM[0xFFD4] = 0 (invalidates old checksum)
3. Normal operation proceeds

### Power-Off Sequence

1. User presses power button → power supply begins shutdown
2. SNS circuit asserts `~NMI` on the CPU
3. CPU vectors to NMI handler at 0xEF08A5
4. NMI handler calls `NMI_StorePayloadChecksums` at 0xEF08D4:
   - Checks NMI guard: internal RAM[0x0400] == 0x80? If not, returns immediately
   - Saves voice presets and flush data to SRAM
   - Computes checksums for two DRAM regions:
     - **Region 1**: DRAM[0xF180], 0x800 bytes (2 KB) → checksum → DRAM[0xFFD4]
     - **Region 2**: DRAM[0xF980], 0x280 bytes (640 bytes) → checksum → DRAM[0xFFD2]
   - If `Seq_IsMelodyActive` returns non-zero, adds 1000 to the stored DRAM[0xFFD4] value, so it no longer equals region 1's checksum and the next boot's `SubCPU_Payload_Verify` comparison fails
   - Copies DRAM[0xF980..] to backup SRAM at 0x1E8000
   - Executes `halt` instruction (CPU stops; power dies shortly after)

### Next Boot

`SubCPU_Payload_Verify` (0xEF092B) compares stored checksums against freshly computed ones:
- If match: boot proceeds normally → splash animation plays
- If mismatch: firmware enters factory reset → "ALL INITIAL SETTING!" displayed

## MAME Emulation Challenge

MAME's exit sequence calls `eat_all_cycles()` simultaneously with `schedule_exit()`, preventing any CPU execution after exit is requested. The exit path is:

```
schedule_exit() → eat_all_cycles() → [main loop exits] → nvram_save() → EXIT notifiers
```

There is **no hook point** between "user requested exit" and "NVRAM saved to disk" where driver code can run the emulated CPU.

## Abandoned Approach: Boot-Time Write Tap

An earlier attempt intercepted `Boot_DisplayScreen`'s clearing of DRAM[0xFFD4] using `install_write_tap`: when the firmware wrote zero to 0xFFD4, the tap read the actual DRAM payload regions, computed the same one's-complement checksums the NMI handler would, and substituted the result so `SubCPU_Payload_Verify` would pass on the same boot.

**This was removed** (`kn7000_mame`, commit `b1cf7db`): the tap itself was the root cause of the KN5000 "Sound Name Error" bug. Intercepting the DRAM[0xFFD4] clear made the firmware's `SubCPU_Payload_Verify` treat the boot as "payload already valid, skip the transfer" — since the checksum regions (0xF180/0xF980) don't yet hold the values the verify step expects at that early point in boot — so the Sub-CPU ran with no (or stale) firmware and never answered the Main CPU's sound-name query. The unmodelled power-down transaction this left behind was also the root of a virgin NVRAM growing a spurious `<Db>` transpose on its own second boot with no input at all.

## Current Solution: A Modelled POWER Switch

The shipped fix does not intercept or substitute anything the firmware computes — it gives the firmware's own `NMI_StorePayloadChecksums` handler real CPU cycles to run, by modelling the instrument's POWER switch as a MAME machine control rather than mapping it to MAME's own exit:

- Pressing the modelled POWER control calls `pulse_input_line(INPUT_LINE_NMI, ...)` on the main CPU — the NMI is edge-triggered in `tmp94c241_device::execute_set_input`, so a pulse is enough.
- A `poweroff_timer` then lets the CPU keep running for a fixed **100 ms** window (`POWER_DOWN_MS`, a deliberately generous upper bound — not a hardware measurement) before the driver calls `machine().schedule_exit()`.
- During that window the real firmware NMI handler runs natively: it computes both one's-complement checksums, stores them at DRAM[0xFFD4]/[0xFFD2], copies the DRAM[0xF980..] block to the battery-backed IC21 SRAM at `0x1E8000`, and halts.
- On the next boot the firmware restores that SRAM block (`0xEF0580`, guarded by the `0x5AA5` magic value at DRAM[0xFFCA]) before `SubCPU_Payload_Verify` runs, so the checksums it finds are the real ones the firmware itself produced.

Nothing in the driver computes a checksum or writes NVRAM directly; the driver's only job is supplying the CPU cycles the real power-down code needs, which is why no MAME core change was required. See `kn7000_mame`'s `src/mame/matsushita/kn5000.cpp` (the "modelled POWER switch" block and `power_switch`/`poweroff_done`) for the implementation, and the KN7000 repository's `side-quests/pending/kn5000_splash_animation.txt` for the investigation history.

### Checksum Algorithm

The algorithm below is the firmware's own — unchanged by which emulation strategy runs it:

```
For each region (start, length in bytes):
    sum = 0                               (32-bit, XHL)
    for each 32-bit long in region:       (ADD XHL,(XWA+4))
        sum = (sum + long) & 0xFFFFFFFF
    checksum = ~sum & 0xFFFF              (CPL HL: only the low 16 bits are kept)
```

Because only the low 16 bits survive, the result depends only on the low word (offset 0 mod 4) of each long (`Checksum_ComputeComplement`, `0xEF18E7`).

## Key Addresses

| Address                   | Description                                                 |
|---------------------------|-------------------------------------------------------------|
| 0x0400 (internal CPU RAM) | NMI guard flag (0x80 = armed)                               |
| 0xEF0620                  | `Boot_DisplayScreen` — arms guard, clears 0xFFD4            |
| 0xEF092B                  | `SubCPU_Payload_Verify` — checks checksums                  |
| 0xEF08A5                  | NMI handler entry (`NMI_HANDLER`)                           |
| 0xEF08D4                  | `NMI_StorePayloadChecksums` — computes and stores checksums |
| 0xEF18E7                  | `Checksum_ComputeComplement` — the checksum routine         |
| 0xFFD2                    | Payload checksum 2 (Region 2)                               |
| 0xFFD4                    | Payload checksum 1 (Region 1)                               |
| 0xF180                    | Region 1 start (0x800 bytes)                                |
| 0xF980                    | Region 2 start (0x280 bytes)                                |
