---
layout: page
title: Sub-CPU Payload Provenance
permalink: /subcpu-payload-provenance/
---

# The Sub-CPU Payload Provenance Question

The KN5000's sub-CPU has no firmware of its own beyond a small boot ROM. Its real
program — 192 KB of code — is pushed across the inter-CPU link by the main CPU at every
power-on. The main CPU reads that 192 KB out of its own address space, from one of two
places selected by a single byte.

**In the ROM images this project holds, neither place contains it.** The emulator only
runs because the MAME driver overlays a file extracted from a firmware-update floppy onto
the region where the payload is supposed to live.

This page is the complete record of that problem: what the firmware does, what our dumps
actually contain, which explanations have been tested, which survived, and exactly what
measurement would close each remaining question. It assumes no prior context.

> **Bottom line.** The mechanism is fully understood and proven from ROM bytes. The
> *provenance* of one dump is not. The most likely remaining explanations are that the
> IC19 custom-data flash dump is incomplete, or that the chip really was blank in that
> region when it was read. Two questions to the instrument's owner would decide between
> them; no desoldering is required.

## 1. How the sub-CPU gets its firmware

`SubCPU_Send_Payload` (main CPU `0xEF068A`, source
`v10/maincpu/kn5000_v10_program.s`) performs the whole transfer. In order:

1. **Gate.** `CP (0xFFFEEF), 0xFF` — if that ROM byte is not `0xFF`, return immediately
   and send nothing.
2. **Five unconditional 64 KB blocks**, table-data `0x830000`–`0x87FFFF` → sub-CPU
   `0x050000`–`0x09FFFF`. This is the tone database — *data*, not the executable — and it
   is sent regardless of which source is chosen next.
3. **Choose a source.** `LD XIZ, 0x800000`; then `CP (0xFFFEED), 0xFF`. If that byte is
   **not** `0xFF`, keep `XIZ = 0x800000` (candidate A) and skip ahead. If it **is** `0xFF`,
   try candidate B: decompress the SLIDE4K image at `0x3E0000` into main-CPU DRAM
   `0x050000` via `SLIDE_Parse_Header`, and if that returns `HL != 0xFFFF` use
   `XIZ = 0x50000`. On failure, fall back to `XIZ = 0x800000`.
4. **Four transfers** totalling exactly `0x30000` = 196,608 bytes:

   | Source | Destination (sub-CPU) | Size |
   |---|---|---|
   | `XIZ + 0x00100` | `0x00F000` | `0x10000` |
   | `XIZ + 0x10100` | `0x01F000` | `0x10000` |
   | `XIZ + 0x20100` | `0x02F000` | `0x0FF00` |
   | `XIZ + 0x00000` | `0x000400` | `0x00100` |

The last transfer is the interesting one: sub-CPU RAM `0x400`–`0x4FF` holds the boot ROM's
own interrupt trampoline block, and the payload's first 256 bytes are 45 five-byte
`JP <24-bit>` trampolines that overwrite it. The boot ROM's main loop then executes
`CALL 0x000400` and the payload takes over.

For the receiving side of the protocol see
[Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/) and
[SubCPU Payload Loading]({{ site.baseurl }}/subcpu-payload-loading/).

## 2. The marker bytes

Three bytes sit in a five-byte island of `0xFF` immediately after the reset trampoline, at
main-CPU `0xFFFEEB`–`0xFFFEEF` (`ROM_PaddingFF` at `0xFFFEEB`-`0xFFFEEC`, then
`SubCPU_FlashPayloadEnableFlag`, `Boot_InitHandlersEnableFlag` and
`SubCPU_SendPayloadEnableFlag` at `0xFFFEED`-`0xFFFEEF`). They are individually
patchable flash bytes, not incidental padding:

| Address | ROM file offset | Measured | Effect |
|---|---|---|---|
| `0xFFFEED` | `0x1FFEED` | `0xFF` | `0xFF` → try the IC19 `0x3E0000` source; anything else → use table-data `0x800000` |
| `0xFFFEEE` | `0x1FFEEE` | `0x00` | `0xFF` would enable `Boot_CallInitHandlers`; `0x00` disables it |
| `0xFFFEEF` | `0x1FFEEF` | `0xFF` | `0xFF` → send the payload at all |

Measured across every main-CPU image the project holds — `kn5000_v7_program.rom`,
`kn5000_v9_program.rom`, `kn5000_v10_program.rom` — bytes `0x1FFEEB`–`0x1FFEEF` are
`FF FF FF 00 FF` in **all three**. The v10 image decompressed from the update floppy
agrees. So on every dumped firmware the machine takes the IC19 branch, and candidate A is
only ever reached as a failure fallback.

This also disposes of a tempting hypothesis: the marker does **not** differ across firmware
versions, so version skew is not the explanation. (v5, v6 and v8 agree as well: decoding
stream 1 of each public update disc's `HKMSPRG.SLD` gives images whose CRCs match MAME's
BIOS list and whose bytes `0x1FFEEB`–`0x1FFEEF` are `FF FF FF 00 FF`; `tools/sld_program_chooser.py` in this repository.)

## 3. The two candidates, and what our dumps contain

### Candidate B — custom-data flash IC19 at `0x3E0000`

This is the live path. Measured on `original_ROMs/kn5000_custom_data.ic19` (1 MB):

- last non-`0xFF` byte at chip offset `0x0D344F`;
- chip `0x0E0000`–`0x0FFFFF` (= CPU `0x3E0000`–`0x3FFFFF`) is **131,072 bytes of `0xFF`**;
- the ASCII string `SLIDE` occurs **zero times** in the entire image.

`SLIDE_Parse_Header` validates that magic, so on this image it returns `0xFFFF` and the
firmware falls back to candidate A.

### Candidate A — table-data `0x800000`

In the table-data ROM (`kn5000_table_data.rom`), CPU `0x800000`–`0x800087` is
`SectionDirectory_Table`, 33 LE32 pointers and a null terminator (`0x800088`, `0x802D10`,
`0x805998`, …). From `0x800088` the region is the bitmap bank they point at: 26 8bpp images
whose transparent colour is `0xF7`, the KN-5000 wordmark, and 17 accessor routines at
`0x82F000`. See
[Table Data ROM]({{ site.baseurl }}/table-data-rom/#section-directory-and-bitmap-bank-0x800000).

So the fallback would ship 192 KB of picture data across the link and then `CALL 0x400`
into a pointer table. **A machine whose ROMs matched our dumps could not run its sub-CPU at all**
— no sound.

That is the crux. Felipe's KN5000 works. Therefore the IC19 image we hold is not the state
that machine was in while it was working, and the discrepancy is a question about *the
dump*, not about the firmware.

> Candidate A may be a **legacy path** rather than a broken one. Its source layout
> (`XIZ+0x100` for the 192 KB, `XIZ+0x00` for the trampoline block) is identical to
> candidate B's, and the *unconditional* part of the same routine already reads sub-CPU
> material out of table data at `0x830000`. That is what one would expect if the sub-CPU
> program originally lived entirely in the table-data mask ROM and was later moved to
> updatable flash, with the vacated space reused for the section bitmaps. Graded **plausible** —
> but v5 and v6 read `0xFF` at `0x1FFEED` too (see §2), so the test is negative on every
> preserved firmware; only an earlier, undumped version (v3 or v4 in MAME's list) could still
> show candidate A live.

## 4. How the payload is *supposed* to arrive — proven end to end

The chain from firmware-update floppy to `0x3E0000` is closed and verified byte for byte.

**The disc.** The v10 system-update floppy image (`kn5000_v10_disk.img`) is a
1.44 MB FAT12 image, OEM string `Technics`, sha1
`a892bedc68f06c431c154ab503bee8ae87d2b3e9`. At LBA 33 (`0x4200`) it carries the ASCII
signature `Technics KN5000 Program  DATA FILE PCK  by T.Nishino`, which is exactly where
`Detect_Disk_Type` reads it. Its root directory is:

| File | Size | Cluster | LBA |
|---|---:|---:|---:|
| `TECHNICS.PRP` | 56 | 2 | 33 |
| `DUMMY.1` | 64 | 3 | 34 |
| `DUMMY.2` | 64 | 4 | 35 |
| `HKMSPRG.SLD` | 1,058,748 | 5 | **36** |

The two `DUMMY` files exist to pin the payload file to LBA 36, which every update handler
uses as a hard-coded start sector (`0x24`). The updater bypasses the FAT entirely.

**The payload file.** `HKMSPRG.SLD` is two concatenated SLIDE4K images with no padding:

| Stream | Disc offset | Header size field | Compressed | Decodes to |
|---|---|---|---|---|
| 1 | `0x004800` | `0x200000` | 965,545 B | `kn5000_v10_program.rom`, byte-identical |
| 2 | `0x0F03A9` | `0x030000` | 93,203 B | `kn5000_subprogram_v142.rom`, byte-identical |

965,545 + 93,203 = 1,058,748 = the directory size exactly. And
`original_ROMs/kn5000_subprogram_v142_compressed.rom` is byte-identical to disc bytes
`[0x0F03A9, +93203)` — i.e. that file was **carved from this floppy**, not synthesised.
(Recompressing the payload with the project's own encoder yields 93,171 bytes, a different
length, so it cannot be a tool output.)

This also makes the v10 ↔ v1.42 pairing a measured fact rather than an assumption.

**The installer.** `HANDLE_UPDATE_FILE_TYPE_ID_007h` (`0xEF47FA`) erases exactly the two
sectors `0x3E0000` and `0x3F0000` of IC19 (128 KB), then:

- `LZ_Decompress_Init` (`0xEF4D95`) — despite the name, this *is* the SLIDE4K decompressor,
  and its destination is the `0x800000` window, where it writes stream 1 (the 2 MB main
  program) four bytes at a time through `Flash_ProgramByte`;
- `LZSS_Decompress_ToFlash` (`0xEF4CF8`) — despite *its* name, this performs **no**
  decompression. It sets the flash write pointer to `0x300000 + 0xE0000` = `0x3E0000`,
  checks the `SLIDE` magic, and then copies bytes 1:1 until it has written exactly
  `0x20000` = 131,072 bytes, two at a time via `Flash_ProgramWord` with the chip selector
  that picks command base `0x300000` (IC19).

So the compressed stream is stored **verbatim** at `0x3E0000` and decompressed afresh on
every boot. 128 KB erased = 128 KB written = the 93,203-byte stream plus slack. The
apparent paradox of "128 KB erased for a 192 KB payload" dissolves: what is stored is the
compressed form.

**Exact post-installation content** of `0x3E0000`–`0x3FFFFF` after a v10 install from this
disc: 93,203 bytes of SLIDE4K stream, then 68 bytes of `0x00` (the tail of the last
cluster — the file ends 68 bytes before the sector boundary), then 37,801 bytes of `0xE5`
(FAT12 format filler). The installer unconditionally over-reads 37,869 bytes past
end-of-file. None of those trailing bytes is ever read back, because the decoder stops
after emitting `0x030000` output bytes.

A second route exists: update type **005h** (`CMPCUSTOMDATA`) chip-erases IC19 and writes
the *entire* 1 MB image verbatim from the disc, which would also populate `0x3E0000`. No
such disc image is available here.

## 5. Hypotheses and verdicts

Five explanations were tested against the bytes. Confidence grades are the investigation's
own and are not inflated here.

### H1 — the memory map is reprogrammed at runtime, so the boot-time map differs from the steady-state map

**SUPPORTED (proven).** The main CPU's `MSAR2` is rewritten from `0xC0` to `0x80` by
`Boot_PrepareJump`, three instructions before the jump into the program flash, and the
device answering `0xFFxxxx` demonstrably differs across that store. Full detail and the
byte-level proof are on
[TMP94C241 Memory Controller]({{ site.baseurl }}/tmp94c241-memory-controller/).

This is the general phenomenon the instrument's owner suspected, and he is right about it.
It is also *not* the explanation for the missing payload — see H2.

### H2 — IC19 was dumped while mapped at a different address range

**REFUTED**, in every form that could be constructed.

*Rotation / offset form.* Eight style-section base offsets were re-derived from the
program ROM itself (`0x116A57`: `LDA XWA, 0x300000` followed by
`ADD XBC, #0x19800 / 0x30000 / 0x49800 / 0x60000 / 0x79800 / 0x90000 / 0xB0000`). The
section marker `48 00 4B 00` occurs in the 1 MB dump at exactly `0x000000`, `0x019800`,
`0x030000`, `0x049800`, `0x060000`, `0x079800`, `0x090000`, `0x0B0000` — eight for eight,
with **no spurious hits anywhere else in the image**. Two more anchors agree: the wallpaper
zero-run begins exactly at chip `0x0C0000` and is exactly 77,824 bytes
(320 × 240 + 1024), and the registration magic `HK \0` sits exactly at chip `0x0D3000`.
A read taken at a different base, rotated, or wrapped cannot produce ten independent
anchors in the right places.

*Window form.* `MSAR5 = 0x00` / `MAMR5 = 0xFF` are written once, inside the single
init block, in the table-data ROM, v7, v9, v10, IC30 and the payload — and **never
rewritten anywhere in any image**. IC19 and the HD-AE5000 ROM contain zero chip-select
accesses in any encoding. There is no machine state in which `0x3E0000` selects a
different chip.

*Region-4 two-die form.* Some boards populate the IC19 slot with two 512 KB devices at
`0x300000` and `0x380000`. The dump's last non-`0xFF` byte is at chip `0x0D344F`, i.e.
inside the *upper* die, so both dies were read.

*Physical form.* IC19's own window is set by the discrete decoders on service-manual
page 32 (A19–A23), not by a CPU register, so no register write could relocate it.

What survives of the owner's hypothesis is its general half (H1), not its application to
IC19.

### H3 — the region genuinely was never programmed on this unit

**UNDECIDED.** It has to be split, because the three variants do not stand or fall
together.

**H3a — the two staging sectors were blank *in the chip* at the moment of the dump.**
*Supported (strong).* The image is a genuine chip read: the 77,824-byte block of `0x00` at
`0x0C0000` can only be actively programmed content, because flash erases to `0xFF`. And
`0x0E0000`–`0x0FFFFF` is sector-clean under both the top-boot and bottom-boot sector maps
of the AM29F400/800 family.

**H3b — no `007h` update was *ever* applied.** *Undecided.* The measured state — every
sector written except exactly the two the `007h` handler erases — is equally consistent
with (i) never installed, (ii) an install whose erase phase completed and whose write
phase did not, and (iii) a dump truncated somewhere in `0x0D3450`–`0x0FFFFF` and padded
with `0xFF`. Variant (iii) is byte-indistinguishable from (i) and no statistic computed
from the file can separate them. An earlier note argued that the data stopping at a *data*
boundary rather than a transfer boundary favours "never programmed"; that argument does
not hold — the last non-`0xFF` byte marks where the data ended, not where the dump ended.

**H3c — this unit worked in the dumped state.** *Refuted.* See §3: with `0x1FFEED = 0xFF`
in every firmware and a blank `0x3E0000`, the fallback ships picture data and the sub-CPU
cannot run.

### H4 — the payload could be resident in the undumped 116 KB of the sub-CPU boot ROM

**REFUTED**, three independent ways.

*Wiring.* The payload is sourced by the **main** CPU from its **own** address space
(`XIZ` = `0x50000` main DRAM, or `0x800000` table data). IC30 is not in the main CPU's
address space at all; the two CPUs share only the 8-bit latches. There is no path.

*Arithmetic.* The payload is 196,608 bytes. The whole of IC30 is 131,072 bytes and only
116,736 of those are undumped. Even the 93,203-byte compressed form would be dead on
arrival: the boot ROM contains no decompressor, and the main CPU unconditionally
overwrites sub-CPU `0x400`–`0x4FF` and `0xF000`–`0x3EEFF` before `CALL 0x400`.

*Reachability.* A complete structure-aware reference census of the disassembled boot ROM
found **220 ROM-address operand references, every one of them inside a dumped window and
none in an undumped range**. The single indirect control transfer (`CALL T, XWA` at
`0xFF88FB`) is bounded by an 8-entry table whose every target is dumped. The loaded v1.42
payload calls back into IC30 at exactly two addresses, `0xFFFEA1` and `0xFFFE86`, both
dumped.

There is one honest counter-example: `ROM_CHECKSUM` (`0xFF8AB4`) reads
`0xFE0000`–`0xFE0FFF`, which runs 2 KB past the dumped window. It is content-independent
(both "banks" re-initialise the same pointer, so the two accumulators sum identical bytes
and can never differ) and its only caller returns immediately unless a strap on Port C is
asserted. It does not run in a normal boot.

### H5 — MAME's overlay of the update-floppy payload is a faithful reconstruction

**SUPPORTED (proven) for all six dumped BIOS options.**

`kn5000.cpp` does `ROMX_LOAD("kn5000_subprogram_v142_compressed.rom", 0x0e0000, …)` into
the `custom_data` region, which the driver maps at `0x300000`. Offset `0x0E0000` is
therefore CPU `0x3E0000` — precisely the installer's target, in precisely the form the
installer writes (the raw SLIDE4K stream including its 11-byte header), with content
carved from the genuine update floppy. **Every byte the firmware ever reads is correct.**

The only deviation is the 37,869 trailing bytes, which MAME leaves at `0xFF` where a real
install leaves `0x00`/`0xE5`; the decoder never reaches them.

Two caveats, neither a fidelity defect but both worth stating plainly:

- The pairings rest on the update discs, not on a dump of any instrument: the second SLIDE4K
  stream of each public `HKMSPRG.SLD` is byte-identical to the compressed file MAME pairs with
  that version — v5 and v6 carry v1.40 (93,124 B), v7 and v8 v1.41 (93,181 B), v9 and v10
  v1.42 (93,203 B) (`tools/sld_payload_pairing.py` in this repository). v3 and v4 are `NO_DUMP`.
- The composite — a genuine chip dump that lacks the update image at `0x3E0000` (H3b,
  undecided: never installed, install interrupted, or dump truncated), plus a
  payload carved from a floppy — is a **reconstruction**, and nothing in the ROM definition
  marks it as such. The base `ROM_LOAD` carries a clean CRC/SHA1 and the `ROMX_LOAD`
  overlay carries no `BAD_DUMP` flag.

## 6. What MAME does today

| Aspect                  | Hardware                                      | MAME                                                                                                                 |
|-------------------------|-----------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| IC19 `0x3E0000` content | populated by a `007h` (or `005h`) update disc | supplied by a `ROMX_LOAD` overlay                                                                                    |
| IC19 device             | AM29F400/800B-family flash, writable          | mainline: `.rom()` region, read-only; kn7000_mame overlay (since 2026-09-05): a writable `amd_29f800b_16bit_device`  |
| Payload source decision | reads `0xFFFEED`, then the SLIDE magic        | same code runs; succeeds because of the overlay                                                                      |
| Running an install      | erase + program IC19 and the `0x800000` pair  | impossible: the `0x800000` and `0xE00000` pairs are still `.rom()`, the map is static, and the bootloader never runs |

So the emulator reaches the right state by a different route. That is defensible today, but
it means the install path itself has never been executed under emulation and nothing would
catch a mistake in it. See
[MAME Emulation Gaps]({{ site.baseurl }}/mame-emulation-gaps/).

## 7. What would settle each remaining question

Ordered by cost. The first two are free and block everything else.

| #   | Question                                                      | Measurement                                                                                                                                                                                                                                                                                                                                                      |
|-----|---------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1   | H3b — was `0x3E0000` ever programmed on this unit?            | On the real instrument, open the built-in memory-dump screen (`DbMemoryDumpProc`, `0xFA2EE6`) at `0x3E0000` and look for ASCII `SLIDE4K`. Present → our dump is incomplete. Absent → the region was genuinely never programmed.                                                                                                                                  |
| 2   | H3b/H3c — was the instrument making sound when IC19 was read? | Ask the owner. If it was, a blank `0x3E0000` is impossible and the dump must be incomplete.                                                                                                                                                                                                                                                                      |
| 3   | Was IC19 read in-system or on a programmer?                   | Ask the owner. An in-system read through the CPU has a readback-window limit that would explain a truncated tail; an off-board programmer read would not.                                                                                                                                                                                                        |
| 4   | Definitive                                                    | Re-read IC19 in full with a device programmer (off-board, or in-circuit with the CPU held in reset) and search for `53 4C 49 44 45 34 4B`.                                                                                                                                                                                                                       |
| 5   | Was candidate A ever live?                                    | **Answered for v5–v10: no.** The program images decoded from the public v5, v6 and v8 update discs (CRCs `0xfbd035e3`, `0x0205db30`, `0x46b4b242`, MAME's) read `FF FF FF 00 FF` at `0x1FFEEB`–`0x1FFEEF`, like the dumped v7, v9 and v10 (`tools/sld_program_chooser.py` in this repository). Only an earlier, undumped version (v3 or v4) could still show it. |
| 6   | Are the BIOS/payload pairings right?                          | **Answered: yes.** Stream 2 of each public v5–v10 `HKMSPRG.SLD` is byte-identical to the compressed payload MAME pairs with that version (`tools/sld_payload_pairing.py` in this repository).                                                                                                                                                                    |
| 7   | What should IC19's other 896 KB contain?                      | A `CMPCUSTOMDATA` (`005h`) disc image — the only artifact that would settle whether the dump is complete *below* `0x0D3450`.                                                                                                                                                                                                                                     |

## 8. Corrections this investigation forced

Recorded here so they do not creep back in:

- **`0x3E0000` does not stage the main program ROM.** An earlier version of
  [System Update Discs]({{ site.baseurl }}/system-update-discs/) said the type-7 disc
  writes the compressed *program* ROM to `0x3E0000` and that a later boot programs the
  program flash from it. What is written there is the compressed **sub-CPU payload**, it is
  read on **every** boot, and the main program image is a separate stream decompressed
  straight into the `0x800000` window during the install. The staging area is permanent,
  not transient.
- **`LZ_Decompress_Init` decompresses; `LZSS_Decompress_ToFlash` does not.** The names are
  backwards relative to what the routines do. Other misleading names in the same subsystem:
  `Parport_ReadNextByte` (`0xEF4C07`) is the floppy stream reader and has nothing to do
  with a parallel port; `Flash_ProgramByte` (`0xEF3D7B`) programs a 32-bit long;
  `Flash_BurnWithProgress` (`0xEF4702`) chip-erases the `0x800000` pair and burns nothing.
- **`0x3E0000` is not "the table data ROM"** — a comment in the table-data source says so;
  it is IC19 custom-data flash, and the routine's own code (`LDA XWA, (0x300000)` /
  `ADD XWA, 0xE0000`) proves it.
- **The fallback address is `0x800000`, not `0x830000`.** `0x830000` is the start of the
  five *unconditional* transfers that run whichever source is chosen.
- **The chip-select registers *are* written by the firmware.** See
  [TMP94C241 Memory Controller]({{ site.baseurl }}/tmp94c241-memory-controller/).

## See also

- [SubCPU Payload Loading]({{ site.baseurl }}/subcpu-payload-loading/) — the transfer in detail
- [Sub-CPU Firmware Images]({{ site.baseurl }}/subcpu-firmware-images/) — the three payload revisions and their dump provenance
- [Custom Data Flash]({{ site.baseurl }}/custom-data-flash/) — IC19 layout
- [System Update Discs]({{ site.baseurl }}/system-update-discs/) — all eight disc types
- [LZSS Compression]({{ site.baseurl }}/lzss-compression/) — the SLIDE4K container
- [ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/) — dump provenance record
- [MAME Emulation Gaps]({{ site.baseurl }}/mame-emulation-gaps/)
