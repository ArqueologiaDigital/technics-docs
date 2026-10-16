---
layout: page
title: ROM Dumping Roadmap
permalink: /rom-dumping-roadmap/
---

# ROM Dumping Roadmap

Where every ROM in the MN10300 family of Technics keyboards stands: what is preserved, what is
not, and — for each device still missing — a concrete proposal for how to obtain it.

*Last reviewed: 2026-10-15. Status is taken from the MAME driver (mainline
`src/mame/matsushita/kn7000.cpp`), which is the authoritative inventory; run `mame -listroms <machine>` to regenerate it.*

---

## 1. Summary

| machine   | devices preserved                                                                                                                                       | devices still undumped        | missing volume |
|-----------|---------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------|----------------|
| SX-KN7000 | 4 program builds (v1.4 upper half only) + 2 table builds + the factory-default custom flash (all nine data sets are in the `kn7000_flop` software list) | **7**                         | 80.5 MB        |
| SX-KN6000 | 2 program + 1 custom-flash image                                                                                                                        | **7**                         | 40 MB          |
| SX-KN6500 | 2 program + 1 custom-flash image                                                                                                                        | **9**                         | 56 MB          |
| SX-KN2400 | half of the 2-device program pair                                                                                                                       | **3** + the pair's other half | 28 MB          |
| SX-KN2600 | half of the program pair (shared with KN2400)                                                                                                           | **4** + the pair's other half | 28.5 MB        |

**30 undumped entries across the five ROM sets, but only 22 distinct physical devices** — five
parts are fitted to both the KN6000 and the KN6500, and three to both the KN2400 and the KN2600,
so one donor instrument serves two machines.

Everything preserved so far was obtained **without opening an instrument**. That is the headline
fact of this roadmap and it shapes every proposal below.

---

## 2. What is sorted out

**Program firmware — all five machines; table data — the KN7000 only.** Extracted from
Panasonic's own update disks (`.SLD` payloads, SLIDE4K LZSS), not from chips. (The KN6000/KN6500
`IK2`/`IKV2` parts are the program's upper half; their table/font devices are listed in §3.) The
images validate against **Panasonic's own checksum oracles** — the `SMCK*.INF` files shipped
alongside them, giving a 32-bit total plus 16-bit sums of every `0x40000` block — with two KN7000
exceptions. In the SP7001 PLUG-iN set, both shipped checksums predate the final payload. The
table's describes the table without the plug-in and with three version markers reading `83` instead
of `80`, which it matches exactly; the two table disks themselves are byte-identical to the dumped
table ([SP7001 Firmware]({{ site.baseurl }}/kn7000-sp7001-firmware/#the-update-disks)). Of v1.4 only
update disk 2 survives, and its eight blocks match.

| model                           | oracle        | total        | blocks                                                                  |
|---------------------------------|---------------|--------------|-------------------------------------------------------------------------|
| KN7000 program v1.6 (build 941) | `SMCKPR1.INF` | `0x18CE8702` | 16/16                                                                   |
| KN7000 program v1.5 (build 935) | `SMCK*.INF`   | `0x18C70719` | 16/16                                                                   |
| KN7000 table                    | `SMCKTB1.INF` | `0x13DCD1A3` | 16/16                                                                   |
| KN7000 SP7001 table (build 83)  | `SMCKTB1.INF` | `0x13B84EFF` | 16/16 for the earlier table it describes; 14/16 against the shipped one |
| KN6000                          | `SMCKPR1.INF` | `0x166ADB67` | 16/16                                                                   |
| KN6500                          | `SMCKPV1.INF` | `0x157ED142` | 15/15                                                                   |
| KN2400                          | `SMCKPR1.INF` | `0x16DA58C4` | 15/15                                                                   |

> ⚠ The KN6000/KN6500/KN2400 oracles sit **inside the self-extracting `.exe`**, not at the top
> level of the `.zip`. A tool that reads only the archive's top level finds none and will report
> that no `.INF` oracle shipped with those models. It did.

**Custom-data flash — KN7000, KN6000, KN6500.** Not chip reads, but the exact bytes the firmware
writes: the Initial Data Disk payload is inflated and written **verbatim to flash offset
`0x20000`**, the top 30 of the 64 KiB sectors of a 16 Mbit bottom-boot device. For the KN7000,
MAME preloads the factory default (`01ctmini.ic21`) and carries all nine data sets (the Initial
Data Disk plus eight published sets) as three reconstructed floppies in the `kn7000_flop`
software list (mamedev/mame#16394). One shared IDD6000 payload serves the KN6000 and KN6500. See [Custom Data Flash]({{ site.baseurl }}/custom-data-flash/) and
[KN7000 Initial Data]({{ site.baseurl }}/kn7000-initial-data/).

**HD-SX6 expansion firmware** (Key Soft Service's HD-SX6 OS v1.1 REV3, for the KN6000/KN6500).
768 KiB, decompressed from `EXTAPR.SLD` on 2026-08-02 — the first time this image had been
recovered. No HD-SX3 image has been found.

---

## 3. What remains

### SX-KN7000 — 7 devices, 80.5 MB

| device | part           | size   | type     | role                                                                                                                                |
|--------|----------------|--------|----------|-------------------------------------------------------------------------------------------------------------------------------------|
| IC203  | `C3CBQD000002` | 16 MB  | mask ROM | wave, main TG bank Y                                                                                                                |
| IC204  | `C3CBQD000001` | 16 MB  | mask ROM | wave, main TG bank X                                                                                                                |
| IC207  | `C3CBQD000004` | 16 MB  | mask ROM | wave, sub TG bank Y                                                                                                                 |
| IC208  | `C3CBQD000003` | 16 MB  | mask ROM | wave, sub TG bank X                                                                                                                 |
| IC18   | `C3CBND000046` | 8 MB   | mask ROM | rhythm (later production)                                                                                                           |
| IC20   | `C3FBMD000050` | 4 MB   | flash    | rhythm, earlier production — the alternative fitted at IC18's site (a unit carries one or the other, so it is not counted in the 7) |
| IC19   | `C3CBMD000098` | 8 MB   | mask ROM | picture                                                                                                                             |
| IC414  | `C3FBKD000162` | 512 KB | flash    | SD card sub-CPU program                                                                                                             |

Not devices, but still missing: the lower half of the v1.4 program (update disk 1,
`kn7-14_1.exe`, which the Wayback Machine archived only as a 'page not found' stub), and
build 893 / table 80, the firmware of the owner's unit, of which only 9,472 hand-transcribed
bytes exist ([Build 893 Recovery]({{ site.baseurl }}/kn7000-build-893-recovery/)).

### SX-KN6000 — 7 devices, 40 MB

| device | part | size | type | role |
|---|---|---|---|---|
| IC13 | `QSIGX3C16008` | 2 MB | mask ROM | table / font |
| IC14 | `QSIGX3C16007` | 2 MB | mask ROM | table / font |
| IC205 · IC206 | `QSIGX3C64004` · `QSIGX3C64005` | 8 MB each | mask ROM | wave |
| IC207 · IC208 | `QSIGX3C64006` · `QSIGX3C64007` | 8 MB each | mask ROM | wave |
| IC15 | `QSIGX3C32021` | 4 MB | mask ROM | rhythm data |

### SX-KN6500 — 9 devices, 56 MB

**Five are the same parts as the KN6000** (IC205–IC208, IC15) — dump a KN6000 and most of the
KN6500 comes with it. KN6500-only:

| device | part | size | type | role |
|---|---|---|---|---|
| IC13 | `C3FBMD000069` | 2 MB | **flash** | table / font |
| IC14 | `C3FBMD000068` | 2 MB | **flash** | table / font |
| IC209 · IC210 | `QSIGX3C64020` · `QSIGX3C64019` | 8 MB each | mask ROM | wave (extra pair) |

> Note the KN6500 uses **flash** where the KN6000 uses mask ROM for table/font — the pinout
> settles it (`RESET#`, `RY/BY#`, `VPP` are present). The two models' table/font parts are not
> interchangeable evidence for each other.

### SX-KN2400 / SX-KN2600 — 3 and 4 devices plus half the program pair, 28 / 28.5 MB

| device                  | part           | size                  | type  | role                                                                                                        |
|-------------------------|----------------|-----------------------|-------|-------------------------------------------------------------------------------------------------------------|
| IC12 · IC13, other half | `C3FBNG000007` | 4 MB of the 8 MB pair | flash | the half the firmware reads at `0x48000000`; never read; on the KN7000 the same layout holds the table data |
| IC14                    | `C3ZBNG000023` | 8 MB                  | flash | rhythm and other data                                                                                       |
| IC302                   | `C3ZBP0000003` | 8 MB                  | flash | wave bank Y                                                                                                 |
| IC303                   | `C3ZBP0000004` | 8 MB                  | flash | wave bank X                                                                                                 |
| IC404                   | `C3ZBK0000020` | 512 KB                | flash | SD sub-CPU (KN2600 only)                                                                                    |

**Everything undumped on these two models is flash, not mask ROM** — the easiest category to read,
and the only family where that is true.

---

## 4. How to dump them

Ranked by risk to the instrument. Prefer the earliest method that can work.

### Method A — find the update files *(zero risk; a search problem, not an engineering one)*

Every image we already hold came this way. Panasonic's own `TECHNICS.HDD` descriptor **enumerates
update payload classes we have never located**, including **Table DATA, Rhythm and
Wave-Expansion**. If those files were ever distributed, they contain the contents of several of the
mask ROMs above without anyone touching hardware.

It has already worked on the KN7000 three more times. Wayback Machine captures of `kn7000.de`
yielded the v1.4 update, a four-disk set (program `JK1`/`JK2`, table `JKT1`/`JKT2`) whose disk 1
was archived only as a 'page not found' stub, and the complete v1.5 program; the SP7001 PLUG-iN
update has been recovered too (all in MAME since #16394). **Still wanted: `kn7-14_1.exe`, disk 1
of the v1.4 update.**

**Proposal.** Sweep dealer archives, the Wayback Machine, European Technics user groups (the
KN-series had an active German-language community), and collector CD-ROMs for `.SLD`/`.AST` files
whose 8-byte magic is not one we already recognise. The container is documented in
[LZSS Compression]({{ site.baseurl }}/lzss-compression/); from the KN6000 on, the magic begins with
the model's project code (KN6000 `IKPRG4K`, KN7000 `JKPRG4K`, KN2400 `LKGP14K`); the KN5000's
magic is the generic `SLIDE4K`, though its file names carry its code `HK` (`HKMSPRG.SLD`).

*Applies to:* potentially the table/font and rhythm devices on every model. Not the wave ROMs,
which were almost certainly never updatable.

### Method B — read it with the instrument's own CPU *(no desoldering)*

The main CPU can address several of these devices directly. A small program run on that CPU can
read a ROM and stream it out. On the KN7000 the stock firmware runs no outside code, so the program
needs the same carrier as Method B′ (a modified update disk or an SP7001 plug-in), with the same
restriction: only on a unit whose build is already preserved.

**Proposal.** Establish which regions the CPU can see from the memory map
([Memory Map]({{ site.baseurl }}/memory-map/)), then use one of the exfiltration routes the firmware already
implements — MIDI system-exclusive dump, the serial port, floppy write, or SD write on models that
have it. This is how homebrew on the HD-AE5000 already works; see
[HD-AE5000 Homebrew]({{ site.baseurl }}/hdae5000-homebrew/).

*Applies to:* IC18/IC19 on the KN7000, IC15 and the table/font devices on the KN6xxx — anything on
the CPU bus. On the **KN7000 the wave ROMs also qualify** (see Method B′); on the KN5000 they do not.

### Method B′ — read the KN7000 wave ROMs through the tone-generator port *(no desoldering, no harness)*

The KN7000's wave ROMs are reachable from the CPU: the tone generators expose a
**wave-memory read port**, and the service-mode §8.9 WAVE ROM test already sweeps the full 16 MiB of
each part through it. The read loop (checksum core `0x484839A1`) is simply:

```
  side A (IC203/IC204):  write hi-addr -> 0x98050006 ; write addr -> 0x98050008 ; read WORD <- 0x9805000A
  side B (IC207/IC208):  write hi-addr -> 0x98040006 ; write addr -> 0x98040008 ; read WORD <- 0x9804000A
```

The side labels are an assumption: nothing confirms which chips each port reaches, and mainline
MAME maps the two ports the other way round (see [§5](#5-verifying-a-dump)).

**Proposal.** Run a small routine that drives that port across the whole address space and streams
the words out over MIDI or SD. The stock firmware (build 941) never executes code from the SD card
or an expansion board (see [Firmware Robustness & ROM Archival]({{ site.baseurl }}/kn7000-firmware-security/)),
and no route from MIDI to running code is known, so the routine needs a carrier: a modified
firmware-update disk, or a plug-in under the SP7001 PLUG-iN release (build 942), which does load
code from the SD card: its resident plug-in reads an `.XAP` file of up to `0x1D000` bytes to work RAM
`0x5029B000` and calls its first byte, at startup and **without any activation check** (see
[SD PLUG-iN (SP7001)]({{ site.baseurl }}/kn7000-sd-plugin/) and
[SP7001 Firmware]({{ site.baseurl }}/kn7000-sp7001-firmware/#the-plug-in-in-table-flash)); a dumper
`.XAP` in place of `BASEEXT.XAP` therefore runs on any SP7001 unit. Either
replaces the instrument's firmware, so it is acceptable only on a unit whose build is already
preserved, never on the owner's build-893 unit. Verify against the firmware's own
[golden checksums](#5-verifying-a-dump). This reaches all four KN7000 wave ROMs (64 MB) without
opening the instrument. Full write-up: [KN7000 Expansion Bus & Wave-ROM Dump Routes]({{ site.baseurl }}/kn7000-expansion-and-wave-dump/).

*Applies to:* KN7000 IC203/204/207/208 only. **The KN5000's IC303 has no equivalent read port** — its
Wave ROM Check is an acoustic (listen-for-distortion) test — so its wave ROMs still need Method C or D.

### Method C — in-circuit read on the tone-generator bus *(no desoldering, needs a harness)*

For the machines with **no** CPU-side wave read (the KN5000, and if Method B′'s port arithmetic cannot
be pinned down) the wave ROMs are the bulk of what is missing and must be read on their own bus.

**Proposal.** Hold the tone generator in reset so it stops driving its bus, then clip onto the ROM
and drive address lines from an external microcontroller, reading data back. Practical notes: these
are TSOP packages, so a purpose-made clip or a set of tack-soldered wires to the address/data lines
is required; verify the TG is genuinely tri-stated before driving anything; and read each device
twice with different address orderings to catch a floating line.

*Applies to:* all wave ROMs — KN7000 IC203/204/207/208, KN6xxx IC205–IC210, KN2400 IC302/303.

### Method D — desolder and read on a programmer *(highest risk, highest certainty)*

Hot-air rework, TSOP adapter socket, universal programmer.

**Proposal of last resort.** These parts are irreplaceable and the boards are consumer instruments
more than twenty years old; lifting a pad ends that instrument. Reserve for a machine that is already
beyond repair — a water-damaged or otherwise dead unit is the ideal donor and is far cheaper to
acquire than a working one. **Prefer a dead donor over a working instrument in every case.**

*Applies to:* any device, but should only ever be needed for the mask ROMs.

### Method E — sub-CPU flash over the inter-CPU protocol

`IC414` (KN7000) and `IC404` (KN2600) are the SD-card sub-CPU's own program flash.

**Proposal.** The inter-CPU protocol is already documented for this family
([Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/), [Sub-CPU Command Format]({{ site.baseurl }}/subcpu-command-format/)).
Check whether the sub-CPU implements a memory-read or firmware-verify command; the main CPU has to
be able to validate a sub-CPU update somehow, and whatever mechanism does that is likely readable.
This is a firmware reverse-engineering task, not a hardware one, and costs nothing to attempt.

---

## 5. Verifying a dump

Any dump obtained by any method above can be checked **against the instrument itself**, which is
better than checking it against our own expectations.

**The ROM DEVICE TEST.** These machines have a service-mode self-test that computes and displays
checksums per device — the KN7000 firmware contains display strings of the form
`CUSTOM FLASH:     IC21 =`. Entering that mode on a real instrument and photographing the values
gives an oracle for every device it covers. See [Test Modes]({{ site.baseurl }}/test-modes/).

> **This is the single highest-value thing an owner can contribute without any disassembly**:
> enter the ROM device test and photograph the screen. It costs nothing, risks nothing, and turns
> every future dump from "plausible" into "verified".

**The KN7000 wave-ROM golden checksums** are already extracted from the firmware (table `0x485CFD18`),
so a Method B′ dump of those four parts can be verified with no instrument at all. The value is
Σ(hi+lo) over every 16-bit word of the device:

| device | expected checksum |
|---|---|
| IC203 | `0x8164C77C` |
| IC204 | `0x815CFC83` |
| IC207 | `0x8331EF0B` |
| IC208 | `0x83254F9D` |

Which value belongs to which chip is not settled. The four values are stored per firmware test, not
per chip: port `0x9805` first, then `0x9804`, and for each port bit 0 of the `+8` latch = 0, then 1.
Which chip each port and bit reach has not been confirmed. The names above follow the side
assignment in the Method B′ read loop, and mainline MAME assumes the opposite side (its `0x98040000`
port reads IC203/IC204). A Method B′ dump can still be verified, because it reads through the same
port and bit as the test. What remains open is only the chip name each file gets. See the ⚠ note on
[KN7000 Expansion Bus & Wave-ROM Dump Routes]({{ site.baseurl }}/kn7000-expansion-and-wave-dump/#-the-wave-roms-are-cpu-readable-through-the-tone-generator).

**The `.INF` oracles**, where an update disk exists for that device, as in §2.

**Cross-model agreement.** Five KN6000 parts are fitted to the KN6500. Dumps from two different
instruments that agree byte-for-byte are strong evidence against a bad read.

---

## 6. Priorities

1. **Method A sweep** — free, non-invasive, and could resolve several devices at once; it has
   already recovered KN7000 v1.4 (upper half), v1.5 and SP7001. First target: disk 1 of the v1.4
   update.
2. **ROM DEVICE TEST photographs** from any owner of any model — free, and makes everything else
   verifiable.
3. **Method E** on the sub-CPU flash — pure firmware work, no hardware access needed.
4. **A dead donor KN6000** — five of its devices also serve the KN6500, the best ratio available.
5. **Method B′** on the KN7000's four wave ROMs — 64 MB, no hardware work, and verifiable against
   the firmware's own golden checksums before anyone opens a case; its carrier replaces the
   firmware, so only on a unit whose build is already preserved.
6. **The remaining wave ROMs** (KN5000, KN6xxx, KN2400) — the bulk of the missing data, and the
   only devices with no non-invasive route at all.

---

## See also

- [MAME Pull Requests]({{ site.baseurl }}/mame-pull-requests/) — how these declarations reach upstream
- [Custom Data Flash]({{ site.baseurl }}/custom-data-flash/) · [KN7000 Initial Data]({{ site.baseurl }}/kn7000-initial-data/)
- [ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/) · [LZSS Compression]({{ site.baseurl }}/lzss-compression/)
- [Flash Programming]({{ site.baseurl }}/flash-programming/) · [Test Modes]({{ site.baseurl }}/test-modes/)
