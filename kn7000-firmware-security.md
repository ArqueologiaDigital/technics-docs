---
layout: page
title: Firmware Robustness & ROM Archival
permalink: /kn7000-firmware-security/
---

# Firmware Robustness & ROM Archival

Two questions about the KN7000's main‑CPU firmware, answered by static reverse engineering of the
program ROM:

1. **Can data from outside the instrument make the CPU run code?** — the expansion connector and the
   SD card are the two places, besides MIDI, where an outside party supplies bytes. Could either one
   seat a ROM, or a crafted file, that the firmware would *execute*?
2. **Can the instrument non‑destructively archive its own firmware?** — some KN7000 units carry an
   **undocumented earlier program‑ROM revision** that deserves preservation. What can the machine's own
   diagnostics tell us, and hand us, without desoldering a chip?

The short answers: **no, external data cannot run code** on the KN7000's stock firmware (build 941,
by construction, on both surfaces; the SP7001 PLUG-iN release, build 942, is the exception — it loads
plug-in code from the SD card, see [SD PLUG-iN (SP7001)]({{ site.baseurl }}/kn7000-sd-plugin/)); and
the instrument can **identify** its firmware revision non‑destructively but **cannot hand over its
contents** — a full dump needs a hardware read or a code‑execution route. The detail is
below. All of it is ordinary preservation reverse engineering; nothing here is an attack recipe, and
the one memory‑safety wrinkle it turns up is something a faithful emulator should *reproduce*, not fix.

---

## 1. The two external surfaces, and the pattern that closes the door

Bytes reach the KN7000 from outside through the expansion connectors, the SD card and its sibling
floppy, and MIDI. This page examines the first two:

- the **SY-EW expansion connectors** (`CN202/203/205/207` for the SOUND-RAM windows, `CN204/206/208/209`
  for the wave bus — see
  [Expansion Bus & Wave‑ROM Dump]({{ site.baseurl }}/kn7000-expansion-and-wave-dump/)), and
- the **SD card** (and its sibling floppy — see [Storage & File System]({{ site.baseurl }}/kn7000-storage-subsystem/)).

Both are handled by the same shape of code, and it is that shape that makes code execution
impossible. The firmware never takes an address *from the data* and jumps to it. Instead it **matches**
the data against fixed tables to derive a small **bounded index**, and calls a **fixed handler** baked
into the ROM. The outside bytes choose *which* of a fixed set of routines runs; they never supply the
routine's *address*.

For the SD card this is the disk‑file dispatcher at `0x4852B6B0`: it matches a file's tag/extension
against the string tables `DiskFileTagTable` (`0x48664090`) and `DiskFileExtTable` (`0x48664438`),
turns the match into an index (`asl 3` / `mulu 0xc`), and calls a fixed PC‑relative handler. A scan of
the whole dispatcher finds **zero** register‑indirect calls or jumps that take their target from file
data. The expansion connector's board‑probe path has the identical property.

---

## 2. The expansion connector — a capability that was removed

The older SX‑KN6000 / KN6500 firmware *did* have a way for an expansion board to run code: a routine
that memory‑compares an `XAPR` signature on the board window and then calls vectors read from the
board. On the KN7000, **that facility was excised.** The KN7000 firmware's only access to the
`0x97800000` window is a 2 MiB byte-sum checksum stub at `0x4849FD9E`. It is not dead code but a
service-mode test: it is called, at entry+2 (which an early caller search missed), from `0x4849FE30`
inside `MainRomTestFunc` and from `0x484A501C`. The conclusion below does not rest on it. The stock
KN7000 program (build 941) contains `XAPR` and `HD-SX3` zero times; the lone `EXTAPR` and `HDDEXT`
strings that look like support are shared-codebase residue — the KN2400, which has *no expansion
connector at all*, shows the same singletons. (The SP7001 PLUG-iN release, build 942, brings the
signature-and-vectors check back, pointed at table flash instead of the expansion window: its
`PlugInProbe` validates an `XAPR` block at `0x483E8000` and calls entries in that block's header.
See [SP7001 Firmware]({{ site.baseurl }}/kn7000-sp7001-firmware/#the-plug-in-host).)

Three independent reverse‑engineering passes (~0.97 confidence) confirmed there is **no native
code‑execution vector** and **no memory‑corruption path to the program counter** from the expansion
board. What a malformed board *can* do is bounded to an **arbitrary read** (information disclosure back
into the instrument) and a **denial of service** (a hang/crash). Board content that the firmware does
copy lands in **fixed** work‑RAM buffers (the copy base is a compile‑time constant, `*(0x501496B8) =
0x840327E8`), never a pointer that is later called.

---

## 3. SD media — seven parsers, five clean, two that overflow

Every SD file format was reverse‑engineered and classified on two axes: does any file byte become a
control‑transfer target or store base (control‑flow), and is any copy sized by a file‑supplied number
into an unbounded buffer (memory‑safety)?

| Format (extension) | Control‑flow | Memory‑safety | Notes |
|---|---|---|---|
| `.AST` custom data (zlib) | fixed‑table | **safe** | zlib 1.0.4 streaming inflate into a fixed scratch cap, then a fixed flash region; the claimed decompressed size is range‑checked, never trusted as a copy count |
| SMF `.MID` / `.SEQ` / `.SQF` | fixed‑table | **safe** | table‑driven MIDI state machine; SysEx/meta lengths streamed‑and‑discarded, not trusted to size a copy |
| `.ACT` demo script | fixed‑table | **safe** | a *text/markup* interpreter dispatched through a fixed handler table keyed by a string‑matched token |
| `.FAV` / `.MD` / `.HMP` → SRAM | fixed‑table | **safe** | compile‑time‑fixed byte counts into fixed SRAM; no file‑supplied count governs any copy |
| SD µ‑COM transport | fixed‑table | **safe** | every SD byte consumed as data; no execute‑from‑SD, no SD firmware update; the runtime library loads from **program flash**, not the card |
| **`.JPG` (JFIF/JPEG)** | fixed‑table | **⚠ unbounded write** | §3.1 |
| **`.HMP` embedded BMP** | fixed‑table | **⚠ unbounded write** | §3.2 |

In build 941 there is no execute-from-SD path of any kind — no overlay loader, no plug-in, no firmware
update from the card. (The SP7001 PLUG-iN release, program 942 / table 83, adds one. Its resident
plug-in in table flash has a loader, `KssPluginLoad`, which reads an `.XAP` file of up to `0x1D000`
bytes from the floppy or the SD card to work RAM `0x5029B000` and calls its first byte, checking the
plug-in id and compile id the code returns only after that call; the setup copies `BASEEXT.XAP`, MN10300
code, to the card for it. See [SD PLUG-iN (SP7001)]({{ site.baseurl }}/kn7000-sd-plugin/) and
[SP7001 Firmware]({{ site.baseurl }}/kn7000-sp7001-firmware/#the-plug-in-in-table-flash).) Five of the seven parsers are also
cleanly bounded. The two exceptions are the image decoders, and they fail the same way.

### 3.1 JPEG

`.JPG` is a genuine SD file type (the picture/wallpaper feature). The SOF0 marker parser reads the
declared height and width and checks **only that they are positive** — it never compares them against
the fixed **640×240** display plane (`0x500D4080` / `0x500F9880`) they are about to fill, and it
decodes *before* it asks how big the image is. The pixel writer computes its destination as
`base + (y_origin + row)·640 + x_origin + col` with **no clamp against the plane**. A well‑formed JPEG
declaring, say, 640×480 is decoded at full size and the writer walks off the bottom of the buffer,
laying file‑derived pixels into the RAM that follows.

### 3.2 BMP

The BMP header validation is otherwise careful (signature, header size, bit depth, compression,
palette) but **never validates the width**. Height is clipped to the 240 rows; width is not. Each row
is copied with a length taken straight from the file into a buffer with a fixed 640‑pixel stride, so a
wide enough BMP overruns it. Because the home‑page code *centres* the picture with
`X = (screen − width)/2`, an oversized width wraps `X` to a huge unsigned value and the destination
wanders.

### 3.3 What it is — and what it is not

In both cases **control‑flow stays safe**: the file controls the *length* and *offset* of a write, not
a pointer that is loaded and called. This is memory corruption, not a jump to attacker code — and
whether it could be steered all the way to the program counter is **unproven** (the writes land in
work RAM ahead of the display plane, not on the stack). It is the same open residual the expansion
board leaves.

For emulation this is reassuring rather than alarming: MAME runs the instrument's *real* decoder on the
real CPU core over RAM the memory map keeps bounded, so the host is never wild‑written and the emulated
instrument corrupts its own RAM exactly as hardware would. **Faithfulness means not adding the bounds
check the firmware never had.**

---

## 4. Archiving the firmware — what the instrument will and won't give up

The second question is preservation: a KN7000 with an undocumented early program‑ROM revision. The
firmware's own diagnostics were mapped to see how far they get.

### 4.1 It tells you its version (the easy, zero‑risk win)

The KN7000 has a built‑in **SOFTWARE VERSION** screen. Each firmware component prints a decimal number
via a `%4d` format string — `PROGRAM : %4d` (`0x485D67E0`), `TABLE : %4d`, `RHYTHM : %4d`,
`PICTURE : %4d`, under the header `--- SOFTWARE VERSION ---` (`0x485D5D9C`). The **PROGRAM** number is a
single 16‑bit build stamp read straight out of program flash:

```
mov   (0x4873660C), d0        ; the PROGRAM build stamp, in flash at file offset 0x33660C
movhu d0, (0x50007DC4)        ; -> formatted as "PROGRAM : %4d"
```

In the reference firmware image this cell reads **941** (`0x03AD`, verified). An earlier revision will
show a *smaller* integer — and **that integer is the revision identifier.** The owner opens the Version
screen and reads it off the LCD; no tools, no risk, no disassembly. Once a unit is dumped by any means,
the same `u16` at the equivalent of `0x4873660C` re‑identifies the build. The cell moves between
builds — build 935 keeps it at `0x487365A8` and build 942 at `0x48737630` — so find it through the
instruction that loads it, not by a fixed offset.

This has already found an unpreserved firmware: a real instrument reports `PROGRAM : 893`
and `TABLE : 80`. For where each of the four numbers comes from — only PROGRAM is a
compiled-in constant; TABLE, RHYTHM and PICTURE are parsed as ASCII decimal out of their
own flash devices — see the [SOFT VERSION screen]({{ site.baseurl }}/kn7000-soft-version/).

### 4.2 The ROM device test checks integrity, but shows no fingerprint

Service diagnostic **§8.1 "ROM device test"** (`MainRomTestFunc` `0x4849FDF8`, reached by holding
**C#3 + D#3 + C#4** at power‑on, then PAGE to the item and **EXECUTE**) sweeps the full 8 MB flash
window `0x48000000`–`0x487FFFFF` — the table half and the program half of the IC16/IC17 flash pair
(§4.5) — as interleaved halfwords, accumulating two 32‑bit additive sums. But it runs the sweep **twice and compares the two sums for
self‑consistency** (its golden‑value seed table is all zeros in this build), and reports only **OK / NG**
on the LCD. No number is shown; the sums are discarded. So the test confirms the flash *reads back
cleanly* but **cannot fingerprint a revision** on‑screen. Usefully, its algorithm is now fully
specified, so a unique fingerprint can be computed **offline** from any dump: two 32‑bit additive
halfword sums over `0x48000000`–`0x487FFFFF`.

### 4.3 No firmware‑mediated byte dump exists

The decisive negative: **no KN7000 diagnostic ever emits program‑flash bytes** to MIDI, serial, or
disk. The ROM test posts only UI OK/NG events; the firmware‑update path is strictly **write‑only**
(disk → flash); and there is no CPU‑observable program‑flash read port analogous to the tone‑generator
[wave‑ROM read port]({{ site.baseurl }}/kn7000-expansion-and-wave-dump/) that made the wave ROMs
dumpable. The firmware can **identify** the revision but not **reproduce** it.

### 4.4 So how do you get the contents?

| Route                                                                                         | Non‑destructive?                                                | Status                                                                                                                                                                                                                                                                                                                                  |
|-----------------------------------------------------------------------------------------------|-----------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **SOFTWARE VERSION screen**                                                                   | yes — read `PROGRAM : NNNN` off the LCD                         | ✅ identifies the revision now, zero risk                                                                                                                                                                                                                                                                                               |
| **§8.1 ROM device test**                                                                      | yes — OK/NG integrity                                           | ✅ confirms the flash reads cleanly                                                                                                                                                                                                                                                                                                     |
| **In‑circuit clip read of IC16/IC17** (CPU held in reset)                                     | yes — reading doesn't modify the chip                           | pragmatic path to full contents; extends the [ROM‑dumping roadmap]({{ site.baseurl }}/rom-dumping-roadmap/)                                                                                                                                                                                                                             |
| **[Video capture of the MEMORY DUMP screen]({{ site.baseurl }}/kn7000-rom-from-the-screen/)** | yes — the viewer cannot write and cannot export; it only paints | 99.87 % byte‑exact **in emulation**; the batch decoder **declines every real composite frame captured so far** (the composite path loses the 5×7 strokes). ~50 min of held button per 4 MB. No chip has been read this way; the live camera reader that followed (`kn7000live`) has so far committed bytes only from a simulated camera |
| **[Photographing the MEMORY DUMP screen]({{ site.baseurl }}/kn7000-build-893-recovery/)**     | yes                                                             | done, partially: 37 screenfuls = 9,472 bytes of build 893 transcribed by hand. ~16,000 photographs would be needed for a whole chip, so this is a *calibration* method, not an archival one                                                                                                                                             |
| **Code‑execution dumper** (CPU runs a small flash reader → observable port)                   | yes                                                             | the only *firmware‑only* route to full contents; uncertain — no proven corruption→PC path exists                                                                                                                                                                                                                                        |
| **Desolder + programmer**                                                                     | no (risks the part)                                             | the route this whole investigation exists to avoid                                                                                                                                                                                                                                                                                      |

The first step costs nothing and should be done first: photograph the Version screen and record the
§8.1 result. The full dump then follows by clip read (recommended) or, if a path is ever found, by a
firmware‑only dumper.

A third route is measured in emulation and has been tried on real composite captures, which the batch
decoder declines: the instrument cannot *export* bytes, but it can **display** them, and the rear
composite VIDEO OUT carries whatever the hidden hex viewer shows. See
[Reading ROM out of the screen]({{ site.baseurl }}/kn7000-rom-from-the-screen/). And 9,472 bytes of
build 893 have already been recovered the slow way, by transcribing photographs of that screen —
[Recovering build 893]({{ site.baseurl }}/kn7000-build-893-recovery/).

### 4.5 Where does the flash updater live? (unresolved)

The KN7000 unquestionably *has* a flash updater — holding PANEL MEMORY 1+2+3+4 at power‑on enters
Flash Memory Update, and the public update disks work. The question is which device the updater code
sits in, because that device is the one place a program‑flash update cannot erase, and it is
therefore where a *rescue* or *dump* routine would have to be found.

> **This section replaces `notes/rom-backup-and-update-format.md` §2.2 (in the same repository as the
> findings notes listed under Sources), which is refuted.** That section
> concluded the resident updater lives in the un‑dumped top `0x90FF` of the program flash
> (`0x487F6F01`–`0x487FFFFF`). **It does not.**

**What killed it.** An owner hardware read on 2026‑08‑09, via the instrument's own
[MEMORY DUMP screen]({{ site.baseurl }}/kn7000-memory-dump-screen/) on a PROGRAM 893 machine:
**`0x487F55CF`–`0x487FFFFF` is one unbroken block of `0xFF`**, with code immediately below it. A
factory‑programmed resident block would be build‑independent, so that null applies to build 941 too.

| Hypothesis                                                     | Verdict                                                                                                                                                       |
|----------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| H1 — a resident block in the top `0x90FF` of program flash     | **REFUTED** (the region is erased on real hardware)                                                                                                           |
| H2 — the update writes the payload and leaves the rest erased  | **SUPPORTED** — but it describes the *payload*, and says nothing about where the machinery lives                                                              |
| H3 — the updater is somewhere in the dumped 8 MB, unidentified | **REFUTED** for uncompressed forms                                                                                                                            |
| H4 — the updater is loaded from the update floppy              | **REFUTED** for the disks held on 2026-08-09 (kn7-16 and the kn7-14 table disks); further update disks (v1.4 disk 2, v1.5, SP7001) were found in October 2026 |
| H5 — the updater is in another device                          | **SUPPORTED** — the only survivor; *which* device is undecided                                                                                                |

**The cross‑reference evidence behind §2.2 was a byte‑misframing artifact.** It rested partly on "33
dword cross‑references into `0x487Fxxxx`, several past the dump end". Two independent kills:

1. **Noise floor.** Scanning 4,157,185 unaligned positions for a 37,119‑byte window has an expected
   *random* yield of ~36 hits. The scan finds 12 — **below chance**.
2. **Mechanism identified.** At `0x485D6860` there is an 8‑byte‑record `{u32 id, u32 handler}` table.
   Every real pointer in it (`0x48487E00`, `0x48487FA7`, `0x48487FBC`, `0x48487FEA`, `0x48487E60`) is
   **inside** the dumped image. Read three bytes early, they become the phantoms `0x487FA700`,
   `0x487FBC00` and `0x487FEA00`×6 — and the "individually improbable" six‑fold repeat is simply one
   default handler slot occurring six times.

An opcode‑anchored `imm32` scan (28,000+ sites) finds **zero** references into
`0x487F6F01`–`0x48800000`, and a linear disassembly of `0x48400000`–`0x4858FFFF` yielding 128,781
branch targets finds **zero** real branches above `0x487F6F00`.

**H3 was tested four ways, each with a measured control.** The AMD unlock idiom scores 4 hits in the
program image and 1 in the table image, while three control constant pairs with comparable load
counts score 0/0/0 in both — and the only real flash driver in the whole 8 MB is
`0x4847E7C0`–`0x4847FB96`, hardwired to absolute `0x9680AAAA` / `0x96805554` — that is the KN7000's
**custom‑data flash IC21**, **not** IC16/IC17. Command sequences
stored as data tables: 0 hits in the KN7000 program image, 0 in the table image, 0 in the KN5000
program image. The uncached write alias (proven by the firmware's own boot, which writes work RAM
through `0x90000000`) puts the program flash's command window at **`0x88400000`** — and `imm32` loads
with high byte `0x88` number **zero** in both images. A per‑64 KB code‑density map shows the table
half contains no MN10300 code at all (max 1 hit per 64 KB across 63 blocks, versus 103–970 in program
code blocks), where a relocatable blob would spike.

Stated honestly: a **packed or compressed** updater cannot be excluded by any of those tests. Nothing
supports one, and the KN5000 analogue is not packed.

**The KN5000 template says where to look.** De‑interleaving the KN5000's table‑data ROM pair gives, at
CPU `0x9FA000`, the update‑disk signature records (`Technics KN5000 Program  DATA FILE 1/2`, …) in a
block running **`0x9FA000`–`0x9FFFCF` — the top `0x6000` of the 2 MB table‑data mask ROM** — with a
real flash driver inside it and its own interrupt vector table at `0x9FFF00`. Decisively, the KN5000's
*resident* firmware cannot write its own program flash either. **The updater lives in a device no
update can erase.** That is the pattern to look for on the KN7000.

**Where the KN7000's positional analogue is.** IC16 + IC17 are **one 8 MB pair spanning
`0x48000000`–`0x487FFFFF`** — 21 address lines (A2–A22) on a 32‑bit bus, corroborated by the
firmware's own §8.1 ROM test at `0x4849FC54` sweeping `0x200000` iterations of a 4‑byte stride under
the row `PROGRAM ROM: IC16 = , IC17 = `. So the "table ROM" is the **lower half of the same flash
pair**, and there is no unread upper half at `0x48800000`. That leaves exactly one never‑read region:

> ### ★ The unread hole: `0x483E94D4` – `0x483FFFFF` (92,972 bytes)
>
> The top of the lower half, immediately above where our table image ends
> (`kn7000_table.rom` is `0x3E94D4` bytes). It is the exact positional analogue of the KN5000's
> `0x9FA000`. **Probe `0x483FFF00` first.**

> ⚠ The SP7001 PLUG-iN release does put content in this range. Its table (build 83) is a full
> `0x400000` bytes: erased from `0x483E0660` to `0x483E7FFF`, then a PLUG-iN block that starts with an
> `XAPR` header at `0x483E8000` and runs to `0x483FB59F`, then erased to the end (see
> [SD PLUG-iN (SP7001)]({{ site.baseurl }}/kn7000-sd-plugin/)). On a unit running that release, probe 5
> (`0x483E9400`) reads plug-in content rather than table data, and probe 1 (`0x483FFF00`) reads `0xFF`.

| #   | Address to dial  | Why                                                                                                                                                | What would be interesting                                          |
|-----|------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| 1   | **`0x483FFF00`** | top of the lower half; the KN5000 positional analogue; the only part of the 8 MB that no stock (build-84) table payload covers                     | dense code, a vector table, or ASCII signature records — or `0xFF` |
| 2   | `0x40000000`     | IC18 rhythm window; the firmware's prober `strncmp`s `Technics Rhythms` at region_base+`0x10000`, so the first 64 KB is *not* rhythm data          | anything non‑`0xFF` means a device is there                        |
| 3   | `0x97800000`     | IC19 picture ROM (64 Mbit mask): **no update disk targets it**, so it survives every flash operation by construction — exactly the KN5000 property | graphics data, or better                                           |
| 4   | `0x97FFFF00`     | top of IC19 — the KN5000 template position translated                                                                                              | code / vectors / `0xFF` / a mirror of probe 3                      |
| 5   | `0x483E9400`     | bounds the hole from below on a build‑80 table                                                                                                     | our build 84 ends at `0x483E94D3`                                  |

**Size: unknown.** We cannot yet say the updater exists in *any* reachable flash. For scale, the
KN5000's analogous block is `0x6000` = 24,576 bytes ≈ 96 screenfuls at 256 bytes per screen.

> ⚠ **Do not dial `0x88400000`.** The `+0x40000000` uncached‑alias convention is real, so that is the
> program flash's *command* window, and the viewer repaints the address it is parked on.
>
> ⚠ **If probe 1 shows real content, do not run a TABLE update on that instrument** until the region
> is dumped — the table payload ends at `0x483E94D3` and erase‑sector geometry may take the block
> with it.
>
> ★ A preservation risk found on the way: the shipped firmware **can erase and fully rewrite the 2 MB
> custom‑data flash IC21** — `0x4847FB68` is a whole‑chip programmer.
>
> ⚠ Do not re‑run raw byte‑pattern searches for addresses in `0x487Fxxxx` / `0x483Fxxxx` without
> computing a noise floor first. That is the error this section corrects.

---

## Sources & related pages

- [SOFT VERSION Screen]({{ site.baseurl }}/kn7000-soft-version/) · [MEMORY DUMP Screen]({{ site.baseurl }}/kn7000-memory-dump-screen/)
- [Recovering build 893]({{ site.baseurl }}/kn7000-build-893-recovery/) · [Reading ROM out of the screen]({{ site.baseurl }}/kn7000-rom-from-the-screen/)
- [Program‑ROM Clip Read (IC16/IC17)]({{ site.baseurl }}/kn7000-program-rom-clip-read/)
- [ROM Dumping Roadmap]({{ site.baseurl }}/rom-dumping-roadmap/) · [Wave‑ROM Dump Tutorial]({{ site.baseurl }}/kn7000-wave-rom-dump/)
- [Expansion Bus & Wave‑ROM Dump]({{ site.baseurl }}/kn7000-expansion-and-wave-dump/) · [Storage & File System]({{ site.baseurl }}/kn7000-storage-subsystem/)
- Findings notes in the [MAME_Technics_Research repository](https://github.com/ArqueologiaDigital/MAME_Technics_Research/tree/main/notes): `FINDINGS-expansion-buses-and-code-exec.md`,
  `FINDINGS-sd-media-codeexec-and-parsers.md`, `FINDINGS-program-rom-version-and-dump-paths.md`,
  `FINDINGS-updater-location-2026-08-09.md`.

*This page is preservation reverse engineering of hardware the project maintains. The memory‑safety
observations are documented so that emulation stays faithful; they are not exploitation instructions.*
