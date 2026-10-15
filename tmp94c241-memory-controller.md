---
layout: page
title: TMP94C241 Memory Controller
permalink: /tmp94c241-memory-controller/
---

# TMP94C241 Memory Controller & Chip Selects

Both KN5000 CPUs are Toshiba **TMP94C241F** (TLCS-900/H2) parts whose external address
decode is *software defined*: six programmable chip-select blocks, each with a start
address register, an address mask register and two control bytes. Nothing on the board
tells the CPU where the ROMs are — the firmware tells it, at boot, and can change its mind
later.

It does change its mind exactly once, and that single register write is the
bootloader-to-program-flash handover. This page records what is measured, what is
reconstructed, and what is still unknown.

> **Confidence summary.**
>
> - **Proven from ROM bytes:** the register addresses; the exact values every firmware
>   writes; that the map is written once per CPU in one init block; that CS2 is
>   reprogrammed once at the boot handover; that no firmware ever moves the block
>   containing the custom-data flash.
> - **Reconstruction (strong, not proven):** the MSAR/MAMR decode rule and therefore
>   every address range in the tables below. **No TMP94C241 datasheet exists anywhere on
>   this project's machines**, and two mutually incompatible readings of the mask
>   semantics were each "confirmed" by different analyses before the contradiction was
>   spotted. Treat window boundaries as interpretation.
> - **Unknown:** the reset-default configuration; the priority rule when two blocks
>   overlap; which physical /CS pin drives which IC.
> - **MAME models none of this** — see [what MAME does](#what-mame-models) below.

## The registers

Twenty-four bytes at SFR `0x140`–`0x157`, four per block
(`kn5000-roms-disasm/v10/maincpu/shared/sfr_tmp94c241.s`):

| Block | BnCSL | BnCSH | MAMRn | MSARn |
|---|---|---|---|---|
| 0 | `0x140` | `0x141` | `0x142` | `0x143` |
| 1 | `0x144` | `0x145` | `0x146` | `0x147` |
| 2 | `0x148` | `0x149` | `0x14A` | `0x14B` |
| 3 | `0x14C` | `0x14D` | `0x14E` | `0x14F` |
| 4 | `0x150` | `0x151` | `0x152` | `0x153` |
| 5 | `0x154` | `0x155` | `0x156` | `0x157` |

- **MSARn** — block start address, in units of 64 KB (`MSAR << 16`).
- **MAMRn** — address mask / block size.
- **BnCSL** — bus timing (wait states).
- **BnCSH** — bus width and output mode.

> **A documentation trap worth recording.** An earlier scouting pass grepped the
> disassembly for writes to these registers and found *nothing*, and concluded the
> firmware never programs them. That was a false negative: the disassembler emits direct
> SFR addresses in **decimal**, so the writes appear as `ld (331:16), 192` (formerly
> `stdi8 (331), 192`) rather than `LD (MSAR2), 0xC0`. Search the binary, or search for
> `320`–`343`, not for the names.

## What the firmware actually writes

Measured by scanning all six dumped images for the `F1 <addr16> 00 <imm8>` direct-store
form. The scan is exhaustive over that encoding and reproduces independently across two
analyses.

**Main CPU** — the identical 24-write block appears twice, once in the table-data
bootloader and once in the program flash, byte for byte:

| Register | Value | Bootloader copy | Program-flash copy |
|---|---|---|---|
| MSAR0–5 | `1E 10 C0 00 80 00` | `0x9FB57B`–`0x9FB594` | `0xEF0459`–`0xEF0472` |
| MAMR0–5 | `0F 3F 7F 1F FF FF` | `0x9FB599`–`0x9FB5B2` | `0xEF0477`–`0xEF0490` |
| B0–5CSL | `11 33 11 22 11 22` | `0x9FB5E4`–`0x9FB5FD` | `0xEF04C2`–`0xEF04DB` |
| B0–5CSH | `80 81 C2 8A 82 81` | `0x9FB602`–`0x9FB61B` | `0xEF04E0`–`0xEF04F9` |

The same block also programs the DRAM controller (`DRAM1REF` `0x81` then `0x71`,
`DRAM1CRL` `0x8B`, `DRAM1CRH` `0x58`) and clears bit 4 of `PMEMCR`. Note that the last
instruction is `RES 4,(PMEMCR)`, a read-modify-write on one bit — some earlier pages
render it as `LD (PMEMCR), 0xF1`, which is a mis-decode of the `F1` opcode prefix.

**Sub CPU** — a separate, different map, programmed by its boot ROM and then re-programmed
with the *same address decode but different timings* by the payload:

| Register | IC30 boot ROM | v1.42 payload |
|---|---|---|
| MSAR0–5 | `10 11 FF 00 12 13` | `10 11 FF 00 12 13` |
| MAMR0–5 | `07 03 01 1F/0F 01 01` | `07 03 01 1F 01 01` |
| B0–5CSL | `66 66 22 22 66 66` | `55 55 22 22 62 66` |
| B0–5CSH | `81 81 C0 8A/89 80 81` | `81 81 C0 8A 80 81` |

IC30's writes are at `0xFF8323`–`0xFF83EA`; the payload's are at file offset
`0x010AD7`–`0x010F95` of `kn5000_subprogram_v142.rom` (sub-CPU address `0x01F9D7` once
loaded). The payload hardcodes `MAMR3 = 0x1F` — it does **not** re-test the DRAM strap
that the boot ROM tests (see [below](#the-sub-cpu-dram-strap)).

**Nothing else writes these registers anywhere.** `kn5000_custom_data.ic19` and
`hd-ae5000_v2_06i.ic4` contain zero accesses to `0x140`–`0x157` in any encoding.

## The one runtime change: the boot handover

Outside the init block, the main-CPU firmware touches a chip-select register in only two
places:

1. **`MSAR2 := 0x80`** — the bootloader-to-program-flash handover. Two sites, both in the
   table-data ROM: `0x9FB6D3` (normal boot, `Boot_PrepareJump`) and `0x9FC806` (the
   HD-AE5000 factory path). A third copy lives in the program flash at `0xEF4B4B`.
2. **`B5CSL := 0x66`** (from `0x22`) — at `0x9FC6C7`, `0x9FC887`, `0xEF4A0C` and
   `0xEF4BCC`, all immediately before HD-AE5000 PPI / flash access. This changes *timing*,
   not addresses; `MSAR5`/`MAMR5` are never rewritten.

The handover is a single store, deliberately surrounded by padding. Bytes at table-data
file offset `0x1FB6BE` (CPU `0xFFB6BE` at boot time):

```
47 00 0C 00 00     LD   XSP, 0x000C00
40 DC FE FF 00     LD   XWA, 0x00FFFEDC      ; the address to jump to
34 4B 01           LDW  IX, 0x014B           ; MSAR2
EC 12              EXTZ XIX
E9 EE 00           SLL  0, XBC               ; no-op padding
E9 EE 00           SLL  0, XBC               ; no-op padding
B4 00 80           LD   (XIX), 0x80          ; <-- the memory map changes here
B0 D8              JP   (XWA)
```

**Why this is a real remap, independent of any decode rule.** Two measurements settle it
without needing to know what `MAMR2 = 0x7F` means:

- The code doing the store *is table-data content* executing at `0xFFB6D3`. In
  `kn5000_v10_program.rom` the same file offsets `0x1FB6B0`–`0x1FB6DF` are **all `0xFF`**
  — there is no such code in the program flash. So before the store, `0xFFB6xx` is the
  table-data ROM.
- The jump target `0xFFFEDC` reads `FF FF FF FF` in the table-data image but
  `1B 0F 05 EF` = `JP 0xEF050F` in the program image. So after the store, `0xFFFExx` is
  the program flash.

The device answering `0xFFxxxx` therefore demonstrably differs before and after one
instruction. The two 3-byte `SLL 0,XBC` no-ops exist so that only the already-prefetched
2-byte `JP (XWA)` has to execute after the swap.

Control enters the program flash at **`Boot_InitIOPorts` (`0xEF050F`)**, not at the
program flash's own `RESET_HANDLER` (`0xEF03C6`): the handover deliberately skips the
program flash's duplicate copy of the hardware-init block, which the bootloader has
already run.

### The interrupt vector table swaps with it

The IVT is ROM-resident at `0xFFFF00` and is never copied to RAM. Before the handover it
is the table-data IVT (handlers at `0xFFB705` and friends, inside the bootloader); after
it, the very same addresses read the program-flash IVT (`0xEF086A`, …). One store to
`MSAR2` re-points every interrupt in the machine. Any future emulation of the dynamic map
must swap the IVT atomically with the code.

### The +0x600000 boot alias

Because the block that holds the ROM is larger than the ROM, the table-data image appears
more than once inside its window, and its boot-time address is its normal address
+ `0x600000`. The firmware relies on this arithmetic literally: `boot_cpserial.s` builds
its vector table as `.long BootSerial_Init + 0x600000`, and `Boot_ClearRAM` copies from
`0xFFB4DC`/`0xFFB4D2`, which are the table-data ROM's `0x9FB4DC`/`0x9FB4D2`.

The data side confirms it independently: the runtime firmware reads the table-data
timestamp string at `0x9FFFC4` (`"hkt_87.ssf"` at file offset `0x1FFFC0`), while the
bootloader reads its own tables through `0xFFxxxx`. Same chip, two windows, two eras.

## Decoding MSAR/MAMR — a reconstruction, not a reading

This is the weakest link on the page and it should be treated as such.

The reconstruction that fits the most independent constraints is:

> block size = 32 KB × (MAMRn + 1); MSARn bit *k* is address bit A(16+*k*); MAMRn bit *k*
> masks (don't-cares) A(15+*k*); MSAR bits below the block size are ignored.

Under that rule `MAMR2 = 0x7F` is a 4 MB window with only A23/A22 compared, so
`MSAR2 = 0xC0` → `0xC00000-0xFFFFFF` and `MSAR2 = 0x80` → `0x800000-0xBFFFFF`: the
handover is a real 4 MB swap. Four things must hold simultaneously and do:

1. the `0xFFFEDC` byte difference proves *some* decode change happens;
2. a 2 MB device in a 4 MB window mirrors at base and base+`0x200000`, which reproduces
   the firmware's own `+0x600000` alias constant exactly;
3. CS4 (`80/FF`) and CS5 (`00/FF`) then tile the whole 16 MB space, with CS2 carving its
   4 MB out of CS4's half — so the program flash occupies whichever half CS2 vacates;
4. the BnCSH bus widths line up with the actual chips (below).

**The competing reading.** A "MAMR bit *k* masks A(16+*k*)" rule — 64 KB granularity —
was independently calibrated on the sub-CPU and appeared to fit two data points exactly
(IC30 as 128 KB at `0xFE0000`, sub DRAM as 1 MB at `0x000000`). It cannot be right for the
main CPU, because under it `MSAR2` `0xC0 → 0x80` changes nothing at all and the proven
handover becomes a no-op. Conversely the 32 KB rule makes sub-CPU CS2 a 64 KB window at
`0xFF0000`, which is *smaller* than the 128 KB IC30 part.

Both analyses reported "exact confirmation" from the same MAME map. At most one can be
correct, and possibly neither is; the honest position is that **only the CS2 swap is
established**, and every window boundary below is provisional.

### Reconstructed windows (provisional)

Main CPU, after the handover:

| Block | MSAR/MAMR | Window (32 KB rule) | Believed to select |
|---|---|---|---|
| CS0 | `1E`/`0F` | 512 KB @ `0x180000` | IC21 battery-backed SRAM |
| CS1 | `10`/`3F` | 2 MB @ `0x000000` | I/O block (FDC, latches, LCD) |
| CS2 | `C0`→`80` / `7F` | 4 MB @ `0xC00000` → `0x800000` | **table-data ROM pair IC1/IC3** |
| CS3 | `00`/`1F` | 1 MB @ `0x000000` | DRAM IC9/IC10 |
| CS4 | `80`/`FF` | 8 MB @ `0x800000` | **program flash pair IC4/IC6** |
| CS5 | `00`/`FF` | 8 MB @ `0x000000` | custom-data flash IC19 (+ IC14) |

Sub CPU:

| Block | MSAR/MAMR | Window (32 KB rule) | Believed to select |
|---|---|---|---|
| CS0 | `10`/`07` | 256 KB @ `0x100000` | — |
| CS1 | `11`/`03` | 128 KB @ `0x110000` | — |
| CS2 | `FF`/`01` | 64 KB @ `0xFF0000` | IC30 boot ROM |
| CS3 | `00`/`1F` | 1 MB @ `0x000000` (strap) | DRAM IC28/IC29 |
| CS4 | `12`/`01` | 64 KB @ `0x120000` | inter-CPU latches |
| CS5 | `13`/`01` | 64 KB @ `0x130000` | tone-generator registers |

**Which physical /CS pin drives which IC has never been read off the schematic.** The
right-hand column is inference from firmware behaviour plus the MAME driver's own
comments, and the two sources do not fully agree — a comment in
`shared/boot_hw_init.s` labels Block 4 as "Table Data", whereas the reading above (and
`kn5000.cpp`) puts the table-data pair on CS2. The CS2/CS4 assignment above is preferred
because it is the only one under which both firmware-update paths make sense: the
bootloader's copy of the updater writes a *program* image to `0x800000` (pre-handover,
where CS4's residue is the program flash), and the program flash's copy writes a *table*
image to the same address (post-handover, where CS2 holds the table data). Two updaters,
each able to program only the chip the other executes from.

Service-manual page 32 ("CPU SECTION (A) P.C. Diagram") additionally shows a discrete
decode network — IC11 `TC74VHC138F` fed by A16/A17/A18, IC12 `T7W139F` fed by A19, IC13
`TC74VHC139F` fed by A22/A20/A19 — sitting between the CPU's chip selects and the
individual devices. So the CPU registers are only half the story, and the sub-division
inside a block (IC19 vs IC14 vs the HD-AE5000 window) is done in glue logic that no
register can move. Tracing IC19 pin 12 (/CE) and pin 14 (/OE) back to their drivers would
settle the physical half of the question in an afternoon.

## BnCSL and BnCSH

The local TMP94C241 register reference documents `BnCSL` as read/write wait-state counts
and `BnCSH` as bus width plus output mode, but does not describe `MSAR`/`MAMR` at all.

Every `BnCSL` value the KN5000 writes has two equal nibbles — `11`, `22`, `33`, `55`,
`66` — except the sub-CPU payload's `B4CSL = 0x62`. That is consistent with a
nibble-aligned "write waits / read waits" pair, and it makes `B5CSL 0x22 → 0x66`
(only ever written immediately before HD-AE5000 access, and never restored) read as
"switch this block to external `/WAIT` handshaking for the slow expansion board". Graded
**plausible**: it is a pattern argument, not a datasheet reading.

`BnCSH` is more useful, because its low nibble cross-checks against bus widths that are
known independently from the flash unlock addresses:

| Value | Block | Low nibble | Independent evidence |
|---|---|---|---|
| `0xC2` | main CS2 | 2 | table-data pair — MAME loads it with `ROM_LOAD32_WORD` |
| `0x82` | main CS4 | 2 | program pair — unlock cycles at `0x815554`/`0x80AAA8` = 4 × word address |
| `0x81` | main CS5 | 1 | IC19, single ×16 device — unlock at `0xAAAA`/`0x5554` = 2 × word address |
| `0x80` | main CS0 | 0 | IC21 SRAM, 8-bit |
| `0xC0` | sub CS2 | 0 | IC30 mask ROM, 8-bit |

Five agreements with independently-known chip widths. An earlier note speculated that
`BnCSH` bit 7 is a per-block enable (every value written has it set); the local register
reference assigns bit 7 to nothing, so that speculation should be dropped.

### The sub-CPU DRAM strap

The sub-CPU boot ROM contains the system's only **strap-conditional** chip-select writes.
It tests Port G bit 0 (SFR `0x40`) twice:

```
FF8352:  f0 40 c8            BIT  0,(PG)
         6e 07               JR   NZ,+7
         f1 4e 01 00 1f      LD   (MAMR3), 0x1F
         68 05               JR   +5
         f1 4e 01 00 0f      LD   (MAMR3), 0x0F
```

and again at `0xFF83D3`, selecting `B3CSH = 0x8A` versus `0x89` — i.e. a different DRAM
bus width to match. This is a genuine **board variant**: two sub-CPU DRAM
configurations exist and the firmware detects which one it is running on. MAME hardcodes
one of them and does not implement sub-CPU port G at all.

## Reset defaults: unknown

What the six blocks decode to *before* the firmware programs them is not established, and
cannot be established from the material this project holds. No TMP94C241 datasheet is
present on any of the project's machines.

The firmware constrains the answer only weakly. Disassembling forward from
`Boot_Init` (`0xFFB4E8`), every instruction up to the chip-select block targets internal
SFRs only — watchdog `0x0110`/`0x0111`, DMA `0x010A`, ports, timers — and the stack
pointer is not loaded until *after* the block. So the reset default has to make the
table-data ROM readable at `0xFFFF00` and across `0xFFB4E8`–`0xFFB61F`, and nothing more.

Which chip answers `0xFFFF00` at reset on the real board is likewise not settled by the
images: **both** ROMs carry a self-consistent reset vector at file offset `0x1FFF00`
(table data → `0xFFFEE0` → `JP 0xFFB4E8`; program flash → `0xEF03C6`). Only the schematic
or a scope on the /CE lines can decide.

Also unknown: the **priority rule** when blocks overlap. Under the reconstruction above,
main-CPU CS0, CS1, CS3 and CS5 all claim parts of low memory simultaneously, and
`MAMR4 = MAMR5 = 0xFF` claim 8 MB each. Either lower-numbered blocks win, or `MAMR = 0xFF`
means something other than "match the maximum window", or both.

## What MAME models

**Nothing.** `src/devices/cpu/tlcs900/tmp94c241.cpp` stores the registers and hands them
back; `m_msar` and `m_mamr` appear only in the constructor, `save_item()`, `device_reset()`
and the plain accessor templates, and are never consulted by any address computation.
`bNcs_w()` is a bare `COMBINE_DATA`. `device_reset()` fills `m_msar`/`m_mamr` with `0xFF`
and sets `m_block_cs[2] = 0x1000; //FIXME!`. `BnCSL`/`BnCSH` are mapped write-only.

The KN5000 driver therefore uses a static map, and because it places the program flash at
the top of memory the emulated CPU reads its reset vector from `program[0x1FFF00]` and
starts at `0xEF03C6` — **it never executes one instruction of the table-data first-stage
bootloader.**

The static map happens to equal the post-handover steady state, so this is *accidentally*
correct rather than wrong, with two known deviations:

- `map(0xe00000, 0xffffff).mask(0x1fffff)` models only the upper of the program flash's
  two mirrors; under the reconstruction the `0xC00000`–`0xDFFFFF` mirror also exists on
  hardware.
- everything reachable only through the bootloader is dead code under MAME: the boot FDC
  driver (`0x9FD8A5`–`0x9FEA9C`), the 16-bit flash routines (`0x9FB812`+),
  `Boot_DetectDiskType` (`0x9FBFC4`), `Boot_ProbeExternalDevice`, and the boot CP-serial
  stack.

See [MAME Emulation Gaps]({{ site.baseurl }}/mame-emulation-gaps/) for what implementing
this would take and in what order.

## What would settle the open questions

| Question | Measurement |
|---|---|
| Exact MSAR/MAMR decode | The TMP94C241 (or TMP94C241F) hardware manual, chip-select/wait-controller section. Nothing short of it is conclusive. |
| Reset defaults | Same document; or a logic analyser on /CE of IC1/IC3 and IC4/IC6 through the first few hundred cycles after reset. |
| Which /CS drives which IC | Service-manual page 32: trace IC19 pin 12 and pin 14, IC14's /CE, and IC11 pins 4 and 6 back to their drivers. |
| Overlap priority | Datasheet; or an in-emulator experiment once a decoder exists. |
| Is the `0xC00000` program mirror real? | Scan the program and table-data images for 24-bit immediates in `0xC00000`–`0xDFFFFF`. If the firmware uses that mirror, MAME's map is incomplete. |

## See also

- [Memory Map]({{ site.baseurl }}/memory-map/) — the address space as the runtime firmware sees it
- [Boot Sequence]({{ site.baseurl }}/boot-sequence/) — the two-stage boot in full
- [CPU Subsystem]({{ site.baseurl }}/cpu-subsystem/)
- [Sub-CPU Payload Provenance]({{ site.baseurl }}/subcpu-payload-provenance/) — where the dynamic-map hypothesis was tested and refuted
- [MAME Emulation Gaps]({{ site.baseurl }}/mame-emulation-gaps/)
