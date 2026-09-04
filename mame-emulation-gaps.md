---
layout: page
title: MAME Emulation Gaps
permalink: /mame-emulation-gaps/
---

# MAME Emulation Gaps

The KN5000 driver boots, plays and runs its UI. What it cannot do is **start the way real
hardware starts** or **install a firmware update from a floppy** — and those two are the
same problem seen from two ends, because everything the update path touches is also
everything the first-stage bootloader owns.

This page inventories what the emulator does not model, distinguishes what is a fidelity
defect from what is merely a shortcut that happens to land in the right place, and gives
the order in which the three prerequisites have to be built.

> Every claim here was checked against the MAME sources in
> `kn7000_mame/src/` and `mame/src/` in August 2026. Line numbers drift; the file and
> symbol names are the durable part.

## What the emulator does today

| Aspect | Hardware | MAME | Verdict |
|---|---|---|---|
| Address decode | six programmable chip-select blocks | registers stored, never consulted | not modelled |
| Reset entry | table-data bootloader at `0xFFB4E8` | program flash at `0xEF03C6` | wrong path, right end state |
| Program flash IC4/IC6 | writable flash pair | `.rom()` region | not modelled |
| Table data IC1/IC3 | mask ROM *or* flash — unresolved | `.rom()` region | unknown |
| Custom data IC19 | AM29F400/800B-family flash | `.rom()` region + overlay | not modelled |
| FDC | µPD72068GF | `UPD72067` device | approximation |
| Floppy formats | 1.44 MB PC-format discs | MFM containers only, no `FLOPPY_PC_FORMAT` | cannot mount `.img` |
| Main-CPU pedals | Port G bits 2–7 = 2 foot switches + 4 foot controllers, active low | Port G unbound, reads `0x00` | all six read as permanently engaged |
| Extension slot strap | Port E bit 0, low when a board is fitted | `porte_read` returns bit 0 = 1 always | HD-AE5000 mapped but never initialised |
| Sub-CPU DRAM strap | Port G bit 0 selects chip-select-3 sizing | hardcoded, sub-CPU port G unimplemented | one variant silently chosen |
| Region code | 4 values on a two-pin strap | `AREA` dip offers 3 | Region 4 unreachable |
| HD-AE5000 window | firmware treats `0x280000` as banked | flat 512 KB `.rom()` | possibly a superset never exercised |

## Gap 1 — the FDC and its disc formats

**The cheapest blocker, and the one that gates any end-to-end test.**

`kn5000.cpp` registers the floppy connector with
`floppy_image_device::default_mfm_floppy_formats`. That helper calls
`format_registration::add_mfm_containers()`, which adds MFI/HFE/TD0/IMD/86F/D88/CQM/DSK —
and **not** `FLOPPY_PC_FORMAT`. Only `add_pc_formats()` adds that. So the driver cannot
open a raw 1.44 MB `.img`, which is exactly the form every archived Technics update disc
takes. Mainline additionally still defaults the drive to `35dd`, which cannot read an HD
disc at all; the working branch already uses `35hd`.

Switching to `default_pc_floppy_formats` is a one-line change and is a prerequisite for
everything below.

**Second, smaller issue.** The driver instantiates `UPD72067` with the comment that the
real part is a **µPD72068GF-3B9**. MAME's own precedent for a 72068 is elsewhere
(`akai/mpc2000.cpp` uses `UPD72069` with the comment "actually UPD72068, which is
software-identical"). The two device classes differ in `auxcmd_w`: `upd72067_device`
switches on `data & 0x0f` and its source comment says only the minimum needed for one
other driver's diagnostic was implemented, whereas `upd72069_device` decodes the full byte
including the "control internal mode" data-rate command. Whether that matters here is
**unmeasured** — it depends on which aux bytes the KN5000 firmware actually writes to
`0x110008`, and nobody has logged a boot with a disc operation. Graded **strong** that the
device choice is questionable, **undecided** whether it is load-bearing.

## Gap 2 — real flash devices

Three flash populations exist on the main board, and MAME models none of them as flash:

| Window | Devices | Bus | MAME today |
|---|---|---|---|
| `0x300000-0x3FFFFF` | IC19, one ×16 part (or two on Region 4) | 16-bit | `.rom()` + overlay |
| `0x800000-0x9FFFFF` | pair of ×16 dies | 32-bit | `.rom()` |
| `0xE00000-0xFFFFFF` | pair of ×16 dies | 32-bit | `.rom()` |

**The good news: for IC19, MAME already has an exact-match device.**
`amd_29f800b_16bit_device` is `0x100000` bytes, 16-bit, manufacturer `MFG_AMD`, device ID
`0x2258` — the right size, the right bus width, and an ID the KN5000's
`Flash_IdentifyAndValidateChip` explicitly accepts. Its AMD command decoder already accepts
the address form the firmware emits: the firmware unlocks at `base + 0xAAAA` and
`base + 0x5554` (byte) = word `0x5555`/`0x2AAA`, and `intelfsh.cpp` matches on
`(address & 0xffff) == 0x5555 / 0x2aaa`. So this collapses from "write a new device" to
"instantiate an existing one".

Note that `FUJITSU_29LV800B` (ID `0x225b`) would be **rejected** by this firmware, so
picking the wrong device silently breaks chip identification.

> **A trap for whoever does it.** Preloading an `intelfsh16` device from a ROM region
> **byte-swaps** the contents. `nvram_default()` reads `m_region->as_u16(offs/2)` and stores
> it big-endian (`m_data[offs] = v >> 8`), while `read_raw()` returns
> `m_data[offset*2] | (m_data[offset*2+1] << 8)`. A `ROM_REGION16_LE` preload of the IC19
> dump therefore reads back wrong.

**Open question that changes the shape of the work:** are IC1/IC3 mask ROM or flash? The
service-manual parts list calls them ROM, but IC4/IC6 (program) and IC19 (known flash) all
share the same house number `QV1GFKN5KAX1`, the firmware has erase/program/verify handlers
targeting `0x800000`, and the update-disc catalogue includes "Table DATA FILE" types.
Graded **plausible**, unresolved — and worth asking someone who can read the chip markings.

Is IC19 a top-boot or bottom-boot part? The firmware accepts both. MAME's 16-bit AMD device
is bottom-boot, so a drop-in gives bottom-boot geometry; the distinction only matters once
the firmware starts erasing.

## Gap 3 — the dynamic memory map

`tmp94c241.cpp` stores `MSAR`, `MAMR` and `BnCS` and never consults them: `bNcs_w()` is a
bare `COMBINE_DATA`, `mamr_w`/`msar_w` are plain assignments, and the members appear only in
the constructor, `save_item()`, `device_reset()` and the accessors. `device_reset()` fills
the arrays with `0xFF` and sets `m_block_cs[2] = 0x1000; //FIXME!`. `BnCSL`/`BnCSH` are
mapped write-only, `BEXCS` is not mapped, and the DRAM-controller/`PMEMCR` registers at
`0x160`–`0x167` are not mapped at all — so those firmware writes fall through the internal
map into the driver's work DRAM.

The consequence for the KN5000 is that reset reads the vector from `program[0x1FFF00]` and
control starts at `0xEF03C6`. **The table-data first-stage bootloader never executes.**
Everything reachable only through it is dead code under emulation: the boot FDC driver
(`0x9FD8A5`–`0x9FEA9C`), the 16-bit flash routines (`0x9FB812`+), `Detect_Disk_Type`
(`0x9FBFC4`), `Boot_CheckDiskPresent`, `Boot_ProbeExternalDevice` and the whole boot
CP-serial stack — none of which any regression would ever catch a mistake in.

The static map happens to equal the post-handover steady state, so this is *accidentally*
correct rather than actively wrong. One known deviation: only the upper of the program
flash's two mirrors is modelled; the `0xC00000`–`0xDFFFFF` mirror that the reconstruction
predicts is absent. (A cheap check before relying on the "accidentally correct" framing:
scan both 2 MB images for 24-bit immediates in `0xC00000`–`0xDFFFFF`.)

### What implementing it would take

**Do not build a full chip-select decoder yet.** The exact `MSAR`/`MAMR` decode rule is
*not* established — no datasheet exists on this project's machines, and two mutually
incompatible calibrations were each reported as confirmed before the contradiction was
noticed. A decoder built on the wrong rule will not reproduce the one behaviour that
matters. See
[TMP94C241 Memory Controller]({{ site.baseurl }}/tmp94c241-memory-controller/).

The one behaviour that matters is a **single 4 MB window swap** at the boot handover. A
`memory_view` with two states — table-data-high and program-high — reproduces it without
committing to a decode rule, and is the pragmatic option.

Two things will need rework when it lands:

- The driver already performs runtime installs: `machine_start()` calls
  `m_extension->program_map(m_maincpu->space(AS_PROGRAM))`, and the HD-AE5000 card does
  `space.install_device(0x000000, 0x2fffff, …)` against the root space. If any of that
  range becomes the interior of a view it will be shadowed, and the install must move into
  the view slot or be re-applied on every switch.
- The interrupt vector table is ROM-resident at `0xFFFF00` and is never copied to RAM, so
  it swaps identity with the ROM. The view has to switch code and vectors atomically; a
  bootloader interrupt taken one cycle late would dispatch into the wrong ROM.

### Resolve this contradiction first

There are **two complete copies** of the flash-update subsystem — one in the table-data
bootloader around `0x9FA000`–`0x9FFFFF`, one in the program flash — and each can only
program the chip the other executes from. That is a natural consequence of the single CS2
swap: pre-handover `0x800000` is the program pair, post-handover it is the table pair.

But the **program-flash** copy of the type-007 handler decompresses stream 1 (the 2 MB main
program) to `0x800000`, which post-handover is the *table-data* pair. Either that handler
is unreachable in practice — updates always enter through the bootloader, which owns the
boot FDC driver — or a second remap exists that nobody has found. **Settle this before
designing the view**, because a second remap would change its shape.

## Dependency order

```
  [1] FDC container formats  (one line; nothing else can be tested without it)
        │
        ├──> [2] flash devices for IC19 and the 0x800000 pair
        │         (instantiate amd_29f800b_16bit; watch the byte-swap trap)
        │          │
        │          └──> [4] run a type-007 install end to end from
        │                    kn5000_v10_disk.img, and diff the resulting
        │                    IC19 image against the predicted post-install
        │                    content (93,203 B stream + 68 x 0x00 + 37,801 x 0xE5)
        │
        └──> [3] update-mode entry  (see below -- the real blocker)

  [5] dynamic memory map (memory_view, two states)
        - NOT a prerequisite for [4]: the type-7 handler that MAME can reach
          lives in the program flash, which the static map already provides
        - IS a prerequisite for a faithful cold boot and for exercising the
          bootloader's own copy of the updater
        - blocked on: resolving the two-updaters contradiction above, and
          ideally on obtaining the TMP94C241 datasheet
```

**Gap 3.5 — entering update mode is the real unresolved blocker.** The update path is gated
on a sentinel byte at ROM `0xFFFFE8` being `0xFF` (read by `Get_Firmware_Version`, `0xFFFEE5`,
and tested in `Boot_RunSelfTest`, `0xEF0529`) and, on hardware, on a panel button held through power-on. Which button, and
how to hold it from reset through the HLE'd `kn5000_cpanel_device`, is not established. This
is the same class of problem as the still-unsolved KN7000 self-test entry.

Even with all of that, the boot path has further gates that MAME cannot currently reach:
Port E bit 0 (HD-AE5000 present strap), `Boot_CheckDiskPresent` (Port D bit 6, active low),
`BootSerial_Init`, and `Boot_ProbeExternalDevice` needing to return device class 4.

## Secondary gaps

- **Region 4.** `Detect_Region_Code` reads Port H bits 2 and 1; `00` = Region 4. The
  driver's `AREA` dip offers only `0x02`/`0x04`/`0x06`, so **Region 4 has never run under
  emulation**. Its branches assume the IC19 slot holds two 512 KB devices with a `+0x80000`
  command base, and skip the HD-AE5000 factory init. Deferrable (the default is not
  Region 4) but it should be recorded in the driver.
- **Sub-CPU DRAM strap.** Port G bit 0 selects `MAMR3` `0x1F`/`0x0F` and `B3CSH`
  `0x8A`/`0x89` — a genuine two-board-variant DRAM configuration. MAME hardcodes 1 MB at
  `0x000000` and does not configure sub-CPU port G at all, so the emulator silently picks
  one revision.
- **Sub-CPU CS2 window.** MAME maps IC30 as 128 KB at `0xFE0000`. Under one reading of the
  decode rule the CPU's own chip select covers only 64 KB at `0xFF0000` — and *all* 4,352
  non-`0xFF` bytes of the dump lie in that upper 64 KB, while the 2 KB read at `0xFE0000`
  came back blank. Worth confirming against the schematic before the full re-dump, because
  it bounds how much of IC30 can matter.
- **HD-AE5000 window banking.** The firmware programs `0x280000` in 8 × 128 KB banks
  selected through the 8255 PPI at `0x160000`, and reads an `hkt_` signature at `0x2FFFC0`
  with bank 7 selected. `hdae5000.cpp` maps a flat read-only 512 KB with no bank register.
  Possibly a superset never exercised in normal operation; unverified.
- **Bus widths.** `BnCSH` also carries per-block data-bus width. MAME's TLCS-900 core fixes
  the external width for the whole space via `m_am8_16`, and the KN5000 driver never calls
  `set_am8_16` for either CPU. Whether any block is genuinely 8-bit, and whether it matters,
  is unmeasured.
- **Keybed service test modes: not established.** The factory keybed diagnostics (Tests 3–8,
  mode codes `0xF5`–`0xFC`) are entered by holding one key pair at power-on;
  `SelfTest_FirmwareVersionCheck` asks the sub-CPU for the held-key bitmap over the inter-CPU
  link (command `0xF002`) once the payload is running, and only Test 4 needs the checking
  device. Under emulation the sub-CPU sees the keybed through `kn5000_tonegen_device`'s event
  FIFO (`push_keybed_event`, `m_keybed_queue`), which `keybed_scan` feeds every millisecond
  from machine start; whether the sub-CPU's reply then reflects keys held from power-on has
  not been measured, and no keybed test mode is on record as entered. These self-tests are
  among the cheapest fidelity evidence available, so one measured run settles it. See
  [Test Modes]({{ site.baseurl }}/test-modes/).

## Gap 4 — port bits nobody bound

The TMP94C241's `port_r` returns `(latch & direction) | (external & ~direction)`, and the
external term comes from a driver callback. Where no callback is bound the callback returns
0, silently, and the firmware reads a valid-looking value that happens to be the wrong one.
Two of those are load-bearing.

**Port G is unbound, so both foot switches and all four foot controllers read as
permanently engaged.** The pins are active low: the firmware's own idle test is
`cp a, 0xf` on the upper nibble, so a released panel is `0xFC` and `0x00` is the
all-six-pressed encoding. `MIDI_ProcessVoiceAssignment` reads `PG` three times per
periodic tick and writes the foot-switch byte to DRAM `0x8EB6` and the foot-controller byte
to `0x8EBA`; because the idle test never matches, the 500-count debounce at `0x8EC8` is
never armed and the fully-engaged values are written on every tick. The fix is an ioport
bound with `portg_read().set_ioport(...)` whose released state is `0xFC`; failing that,
`set_constant(0xFC)` is strictly better than the present silence.

*Verification:* memory-tap `0x8EB6`, `0x8EBA` and `0x8EC8` over a few seconds of idle
running. Today `0x8EC8` must stay 0 and `0x8EBA` must be rewritten every tick; after the
fix, with no pedal pressed, `0x8EC8` must be armed to 500 and `0x8EBA` must stop being
rewritten. That before/after pair is the null the claim needs.

**Port E bit 0 is hard-coded to "no extension board".** `porte_read` returns bit 0 = 1
unconditionally, and `Boot_FlashAndExtensions` reads bit 0 = 1 as "slot empty" and skips
`HDAE5000_Parport_Setup`. So although the driver instantiates a real extension connector
and `hdae5000` is a selectable card that installs an ATA interface, a uPD71055 PPI and 1 MB
of SRAM+ROM, the firmware is told the slot is empty: the PPI is never programmed and the
hard disk is never probed. Everything the card provides is mapped and unreachable. The fix
is a card-present query on the connector, with `porte_read` returning bit 0 = 0 when a card
is fitted.

*Verification:* run with `-extension hdae5000` and break on the write of `0x82` to
`0x160006`, the PPI mode word and the first thing `HDAE5000_Parport_Setup` does. It must be
reached with the card and **not** reached in a no-card control run, and the `AREA` ioport
must not select region 4 (the firmware skips the board there regardless).

Port assignments and the firmware sites behind them are on
[CPU Subsystem]({{ site.baseurl }}/cpu-subsystem/#io-ports).

## Acceptance tests worth writing

Two of these are exact and mechanical, which is unusual and worth exploiting:

1. **Install replay.** Boot with `kn5000_v10_disk.img` in the drive, run a type-007 update,
   then dump `0x3E0000`–`0x3FFFFF` and compare against the predicted post-install image:
   93,203 bytes of SLIDE4K stream, 68 bytes of `0x00`, 37,801 bytes of `0xE5`. Any
   deviation is a bug in the emulated flash or FDC, not an interpretation dispute.
2. **Bootloader liveness.** Once the memory view exists, assert that the CPU executes at
   `0xFFB4E8` before `0xEF050F`, and that a read of `0xFFFEDC` returns `FF FF FF FF` before
   the `MSAR2` store and `1B 0F 05 EF` after it.

## See also

- [TMP94C241 Memory Controller]({{ site.baseurl }}/tmp94c241-memory-controller/)
- [Sub-CPU Payload Provenance]({{ site.baseurl }}/subcpu-payload-provenance/)
- [Boot Sequence]({{ site.baseurl }}/boot-sequence/)
- [System Update Discs]({{ site.baseurl }}/system-update-discs/)
- [FDC Subsystem]({{ site.baseurl }}/fdc-subsystem/)
- [MAME Branch Review & Roadmap]({{ site.baseurl }}/mame-branch-review/)
- [MAME Pull Requests]({{ site.baseurl }}/mame-pull-requests/)
