---
layout: page
title: "Program-ROM Dump: In-Circuit Read of IC16/IC17 (draft)"
permalink: /kn7000-program-rom-clip-read/
---

# Program-ROM Dump: In-Circuit Read of IC16 / IC17

**Status: working draft.** This is the *gentle way in* from
[Firmware Robustness & ROM Archival]({{ site.baseurl }}/kn7000-firmware-security/): reading the
KN7000's main program flash **without desoldering it**, to archive an undocumented firmware revision.
Everything about the *chips and the bus* below is confirmed from the SX-KN7000 service manual
(schematic diagram-2 and the parts list) and the firmware. The **pin-level wiring is delegated to a
universal programmer** so that nobody hand-wires 48 pins — and the honest feasibility limits are stated
in §6. Verify the chip identity on your own board before you start.

> **First, the free step.** Before any clip touches the board, read the revision off the instrument
> itself: open the **SOFTWARE VERSION** service screen and photograph `PROGRAM : NNNN`. That names your
> revision at zero risk (see the [ROM archival page]({{ site.baseurl }}/kn7000-firmware-security/)).
> The dump below is for capturing the *contents*, which no built-in diagnostic will hand over.

## 1. What you are reading

|                                |                                                                                                                                                                                                                                                                                                                       |
|--------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Program ROM**                | **IC16 + IC17**, service part `RFKFXKN7000` ("FLASH MEMORY"), part code `C3FBNG000016` ("32M FLASH")                                                                                                                                                                                                                  |
| **Type**                       | 32 Mbit **×16 NOR flash**, 3.3 V, with `BYTE`, `RESET`, `CE`, `OE`, `WE`, `RY/BY` pins — almost certainly **TSOP-48** (the standard package for this class; confirm on your chip)                                                                                                                                     |
| **Bus**                        | The two chips form a **32-bit** word on the CPU bus: one carries `D[15:0]`, the other `D[31:16]` — exactly like the DRAM pair (IC12/IC13) and SRAM pair (IC14/IC15)                                                                                                                                                   |
| **Host CPU**                   | **IC4 = MN103002A**, 32-bit micro-controller — drives the shared address/data bus                                                                                                                                                                                                                                     |
| **Neighbours on the same bus** | DRAM IC12/13, fast SRAM IC14/15, rhythm mask ROM IC18 (rhythm flash IC20 on earlier units), picture ROM IC19, custom flash IC21 (the table data is not a separate chip: it is the A22-low half of IC16/IC17 themselves) — all share the address and data lines; each has its own chip-select from an on-board decoder |

**Consequence for the dump:** the program image is *split across two chips*. You read **IC16** and
**IC17** separately and **interleave** their 16-bit halves into 32-bit words (§5). Reading a NOR flash
needs no command sequence — it behaves like a ROM: put an address on the pins, assert `CE#`/`OE#`, read
the data. So a plain parallel-NOR read (what every universal programmer does) is all that is required;
the AMD/Fujitsu command set only matters for *writing*, which we never do.

## 2. The one real difficulty: a shared bus

These are not standalone chips on a socket — they sit on the CPU's live 32-bit bus, and so do seven other
memory devices. An in-circuit read only works if **nothing else drives those lines** while you read.
Two things must be true:

1. **The CPU must release the bus.** Hold **IC4 (MN103002A) in reset** so its address/data pins go
   high-impedance. (Find the RESET net at the reset controller on the schematic; assert it and keep it
   asserted for the whole read.)
2. **The other memory chips must stay deselected.** With the CPU in reset and the programmer driving the
   address, the on-board decoder should hold the non-selected chips' `CE#` inactive — but this is the
   part that is *board-dependent and not guaranteed*. See §6 for how to tell whether it worked and what
   to do if it didn't.

This is why in-circuit reads of *parallel* flash are more delicate than the serial-bus wave-ROM snoop:
there is real potential for **bus contention**. Respect it; verify the read (§7) rather than trusting it.

## 3. Tools

- A **universal programmer with a TSOP-48 clip / socket adapter** — e.g. XGecu **T48/T56** or a
  **TL866II Plus** with a TSOP-48 SOP/clip adapter. *This is the recommended path:* you select the chip
  type and the programmer drives the correct 48-pin interface — **you do not wire individual pins.**
- A **TSOP-48 test clip** (e.g. 3M/Pomona-style) if you read in place, or a **ZIF adapter** if you ever
  remove the chips.
- A bench supply or the instrument's own 3.3 V rail, and a wire to **hold IC4 in reset**.
- Optional: a **Raspberry Pi Pico** for a bit-bang reader — possible but *advanced* (§8), because a
  ×16 chip needs ~22 address + 16 data + control lines, more than a Pico's GPIO without multiplexing.

## 4. Procedure (programmer + clip)

1. **Identify the die.** With the board unpowered, read the markings on IC16/IC17, or let the
   programmer's **autodetect** report the manufacturer/device ID once clipped. Expect a **32 Mbit ×16
   3.3 V NOR flash** (the KN7000's custom flash IC21 identifies as Fujitsu/Macronix 29LV-series, so this
   pair is most likely a **29LV320-class** part — MBM29LV320 / MX29LV320 / M29W320 or equivalent). If
   the house number hides it, select a compatible 32 Mbit ×16 profile or the programmer's **generic
   parallel-NOR ×16** read mode.
2. **Hold the CPU in reset.** Assert IC4's RESET and keep it asserted. Confirm the bus is quiet.
3. **Clip IC16.** Seat the TSOP-48 clip squarely (pin-1 aligned). Provide 3.3 V per the programmer.
4. **Read IC16** at full size and **save it** (`ic16.bin`). Note the size the programmer reports
   (4 MB for a 32 Mbit ×16 part).
5. **Re-read IC16** and compare — an in-circuit read must be **identical twice** (this is exactly the
   consistency check the instrument's own §8.1 ROM test performs). If the two reads differ, stop and see
   §6.
6. **Repeat for IC17** → `ic17.bin`, with its own double-read check.
7. Keep both raw dumps. Reassembly and verification are done offline (§5, §7).

## 5. Reassembling the 32-bit image

Each chip holds **half of every 32-bit program word**. One chip is `D[15:0]`, the other `D[31:16]`; the
schematic pairs them top/bottom, but rather than trust a silk label, determine the order **empirically**
by which interleave verifies (§7). The reassembly is a two-way byte interleave:

```python
# reassemble.py — interleave the two 16-bit halves into the 32-bit program image
import struct, sys
lo = open("ic17.bin","rb").read()   # candidate D[15:0] (MAME loads IC17 as the even halfword)
hi = open("ic16.bin","rb").read()   # candidate D[31:16]
assert len(lo) == len(hi)
out = bytearray()
for i in range(0, len(lo), 2):
    out += lo[i:i+2]                 # low  halfword (little-endian on the bus)
    out += hi[i:i+2]                 # high halfword
open("kn7000_program.rebuilt.bin","wb").write(out)
print("wrote", len(out), "bytes")
# If verification (§7) fails, swap lo/hi and/or the two halfword lines and retry.
```

The result is the whole 8 MB window `0x48000000`–`0x487FFFFF`, a stream of little-endian 32-bit words:
the first 4 MB is the table half (CPU A22 low; its first `0x3E94D4` bytes correspond to
`kn7000_table.rom`), the last 4 MB the program half (its first `0x3F6F01` bytes correspond to
`kn7000_program.rom`).

## 6. Did it actually work? (and what if not)

The read is only trustworthy if it survives these checks:

- **Double-read identical** (step 5/6). Contention or a poor clip shows up here first.
- **Not all `0xFF` / not all `0x00`** — a floating or deselected chip reads flat.
- **§7 verification passes.**

If a read is inconsistent, the bus was contended. Options, least-invasive first:

1. **Confirm the CPU is truly held in reset** and that reset actually tri-states its bus (some designs
   don't); try powering the board *off* and letting the programmer power only the clipped chip (watch
   for back-powering through neighbours).
2. **Lift a single pin** — the target's `CE#` (or `OE#`) — so the programmer fully controls selection
   while the chip stays otherwise soldered. One reworked pin is far short of removing the part.
3. **Last resort: hot-air the two chips off** onto a ZIF adapter, read, and reflow them back. Done with
   proper temperature and flux this need not harm the chips — but it is exactly the risk this method
   exists to avoid, so treat it as the fallback, not the plan.

## 7. Verification — prove you captured the real ROM

Two independent checks, both derived from the firmware itself:

1. **The version cell.** In the reference image the PROGRAM build stamp is a little-endian `u16` at file
   offset **`0x33660C`** of the 4 MB program image — **`0x73660C`** of the reassembled 8 MB image (reads
   **941** there). The cell moves between builds (build 935: CPU `0x487365A8`; build 942: `0x48737630`),
   so in your rebuilt image find the value through the instruction that loads it rather than at a fixed
   offset; it should be a sensible small integer **equal to the `PROGRAM : NNNN` you photographed off
   the Version screen** in the free first step. This simultaneously confirms the dump *and* the
   interleave order.
2. **The §8.1 fingerprint.** The instrument's ROM device test computes two 32-bit **additive** sums over
   the flash — over the halfword streams of the 8 MB window `0x48000000`–`0x487FFFFF` (table + program).
   You can compute the program-region contribution offline and record it as a revision fingerprint:

```python
# fingerprint.py — additive halfword sums over the program window, per the 8.1 ROM test
import struct
d = open("kn7000_program.rebuilt.bin","rb").read()
s_lo = sum(struct.unpack_from("<H", d, i)[0] for i in range(0, len(d), 4)) & 0xFFFFFFFF
s_hi = sum(struct.unpack_from("<H", d, i)[0] for i in range(2, len(d), 4)) & 0xFFFFFFFF
print(f"program-window sums: lo=0x{s_lo:08X} hi=0x{s_hi:08X}")
```

Also sanity-check that the first bytes disassemble as valid MN10300/AM33 code and that strings like the
version format `PROGRAM : %4d` appear. When the version number matches and the image disassembles, you
have an honest dump of that revision.

## 8. Advanced: a Pi Pico bit-bang reader

The [wave-ROM tutorial]({{ site.baseurl }}/kn7000-wave-rom-dump/) used a Pico to snoop a *serial-ish*
bus. A parallel ×16 flash needs ~22 address lines out, 16 data lines in, and `CE#`/`OE#` — more than the
Pico's 26 GPIO. It is doable **one chip at a time** by (a) running the chip in **×8 mode** (`BYTE#` low,
8 data lines) and reading it twice for the two byte lanes, or (b) driving the address through a couple of
**74HC595** shift registers to free up GPIO. This is a real project in its own right; the
programmer-plus-clip route above is strongly preferred unless you specifically want the Pico exercise.

## 9. Safety

- 3.3 V part — never present 5 V to the clip.
- Seat the clip fully and check pin-1 orientation before powering.
- Keep the CPU in reset for the *entire* read; a mid-read release contends the bus.
- Reading does not modify a NOR flash; the only write path (erase/program) is never used here.

## See also

- [Firmware Robustness & ROM Archival]({{ site.baseurl }}/kn7000-firmware-security/) — why the firmware won't dump itself, and where `0x33660C` / the §8.1 sums come from
- [ROM Dumping Roadmap]({{ site.baseurl }}/rom-dumping-roadmap/) · [Wave-ROM Dump Tutorial]({{ site.baseurl }}/kn7000-wave-rom-dump/)

*Confirmed from the SX-KN7000 service manual (schematic diagram-2, parts list p.54) and firmware. The
pin-level interface is handled by the programmer when you select the chip; nothing here should be
hand-wired from an unverified pinout.*
