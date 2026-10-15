---
layout: page
title: Sub-CPU Firmware Images
permalink: /subcpu-firmware-images/
---

# Sub-CPU Firmware Images (v1.40 / v1.41 / v1.42)

The KN5000's sub-CPU has a 128 KB boot ROM of its own (`kn5000_subcpu_boot.ic30`, mapped at
`0xFE0000`) but no flash holding its 192 KB *runtime* payload: that payload is pushed across
the inter-CPU link at every boot by `SubCPU_Send_Payload` (see
[SubCPU Payload Loading]({{ site.baseurl }}/subcpu-payload-loading/)).

**Where the main CPU is *supposed* to read it from is now settled; where our dumps put it
is not.** The routine takes one of two source bases: the SLIDE4K image at Custom Data flash
`0x3E0000`, or — only when that fails its magic check — table-data `0x800000`. The first is
the live path on every firmware version we hold, and a File Type 007 update disc is proven
to write the compressed payload there verbatim. But in our IC19 dump that region is 131,072
bytes of `0xFF` with no `SLIDE` magic anywhere in the image, and the table-data fallback at
`0x800000` is a section directory followed by a bank of 8bpp bitmaps (picture data). A
machine matching our dumps could not start its sub-CPU. That is a **dump-provenance**
problem, not a firmware one; the full evidence and the measurements that would settle it
are on
[Sub-CPU Payload Provenance]({{ site.baseurl }}/subcpu-payload-provenance/).

Three revisions of that payload survive, and they survive in two different shapes — which
turns out to matter for preservation.

## The two shapes

**Decompressed payload (196,608 bytes).** What the sub-CPU actually executes. This is the
form the disassembly reconstructs and the form `compare_roms.py` checks.

**Firmware-update image (~93 KB).** What ships on a system-update floppy: an 11-byte
header — `"SLIDE4K"` + NUL, then the decompressed size as a 24-bit **big-endian** value
(`03 00 00` = 196,608) — followed by the LZSS stream. The update handler for File Type 007
("Technics KN5000 Program DATA FILE PCK") writes it into Custom Data flash at `0x3E0000`
**verbatim**, exactly `0x20000` bytes, after erasing the two sectors there. It is not a
transient staging area: the main CPU decompresses it afresh on **every** boot.

The `SubCPU_Send_Payload` fallback branch points at table-data `0x800000` (not `0x830000`,
which is the start of the five *unconditional* tone-database transfers that run whichever
source is chosen). `0x800100` onward is a bank of 8bpp bitmaps (transparent colour `0xF7`),
so the fallback would ship picture data. That is a strong lead on the "Preset Data Destination"
dispute, not yet confirmed in MAME; see
[LZSS Compression]({{ site.baseurl }}/lzss-compression/#preset-data-destination-dispute).

All three compressed images in the repository were extracted from the
[system update floppy disk images](https://archive.org/details/technics-kn5000-system-update-disks)
on the Internet Archive.

## Dump provenance

### The compressed images are carved artifacts, not tool output

`kn5000_subprogram_v142_compressed.rom` is byte-identical to bytes `[0x0F03A9, +93203)` of
`kn5000_v10_disk.img` (sha1 `a892bedc…`) — it was cut out of that floppy. Recompressing the
payload with this project's own encoder produces 93,171 bytes, a different length, so the
file cannot be a tool output. Decoding the two SLIDE4K streams that disc carries reproduces
`kn5000_v10_program.rom` (2,097,152 B) and `kn5000_subprogram_v142.rom` (196,608 B) exactly,
which makes the **v10 ↔ v1.42 pairing a measured fact**.

The v1.42 → v9, v1.41 → v7/v8 and v1.40 → v5/v6 pairings that MAME's BIOS options assert
are **not** measured — only the v10 update disc is available to this project. They rest on
filename inference and should be treated as such until a v5–v9 disc turns up.

### The boot ROM `kn5000_subcpu_boot.ic30` is only 11% dumped

**Owner testimony (Felipe, 2026-08-08).** IC30 was dumped **partially and deliberately**.
The tooling could copy only small chunks at a time, so he read the regions that appeared to
hold the boot code needed to make the emulator work, analysed that code, and — as far as he
could assess at the time — found no references into the regions he had not read. He
concluded the rest was very likely `0xFF`. **He calls this an educated guess, not a
measurement**, and intends a full dump when he regains physical access to the instrument
(it is in storage in another country).

Measured: 14,336 bytes were read (10.9% of the chip); **116,736 bytes, 89.1%, are `0xFF` by
assumption**; a further 9,984 bytes were read and came back `0xFF`; and only **4,352 bytes
of the whole 128 KB chip — 3.3% — are real data**. Turned round, **97% of the chip is
`0xFF`, and most of that is assumed rather than measured**. The content sits in two blocks,
CPU `0xFF8000-0xFF904C` and `0xFFFE80-0xFFFFFF`; the second contains a 60-byte blank gap at
`0xFFFFB4-0xFFFFEF` between the interrupt vector table and the four reserved words at the
very top, which is why some pages count three blocks rather than two.

The guess has been tested, but it has not been settled. A structure-aware census over the
byte-identical disassembly found 220 ROM-address references, all in dumped windows and none
in an undumped range, and the loaded v1.42 payload calls back into IC30 at only two
addresses, both dumped; the one counter-example (`ROM_CHECKSUM` reading past the dumped
window at `0xFE0000`) is content-independent and does not run in a normal boot. Against
that, an adversarial re-verification grades the guess **UNDECIDED**:
the enumeration it asks for — control-flow targets and vector entries taken out of a
disassembly, not byte scans — has never been run as an auditable artifact, and raw byte
scans do turn up candidate pointers into undumped space (most of them coincidences at this
data volume, but that is the point). See
[Sub-CPU Boot ROM (IC30)]({{ site.baseurl }}/subcpu-boot-rom/) for the carved contents and
the full provenance record, and
[ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/#dump-provenance) for the
figures. Note that a full IC30 dump would *not* answer the payload-source question — the
payload is larger than the entire chip and IC30 is not in the main CPU's address space.

MAME flags the file `BAD_DUMP` and states the assumption inline. That flag should stay until
the chip is read in full.

## Status of each revision

| Revision | Update image | Decompressed payload                 | Source tree    | In `make all`        |
|----------|-------------:|-------------------------------------:|----------------|----------------------|
| v1.40    | 93,124 B     | 196,608 B — **recovered, committed** | no             | no                   |
| v1.41    | 93,181 B     | 196,608 B                            | no             | no                   |
| v1.42    | 93,203 B     | 196,608 B                            | `v142/subcpu/` | **yes, both shapes** |

### v1.42 — fully covered

The v1.42 payload is source-built and byte-identical. Since August 2026 its *update image*
is a verification target too: the build recompresses the source-built payload with
`compress_lzss.py --strict --with-header --reference` — replaying the factory encoder's
own match/literal decisions — and `cmp`s the result against
`original_ROMs/kn5000_subprogram_v142_compressed.rom`. It appears in `compare_roms.py` as
the *subcpu v142 update image* section, at 100.00%.

sha256 of the payload: `16a1b654cea132ac433c16162db4a72ef7227fcc962ff6fae0ce088aa7c6e76e`.

### v1.40 — a preservation recovery

**Before August 2026, no decompressed copy of the v1.40 sub-CPU payload existed anywhere
in this project.** The only artifact was the compressed update image, and nothing in the
build ever unpacked it. A corrupted or lost 93 KB file would have taken the revision with
it.

The 196,608-byte payload has now been decompressed out of that single copy and committed
as `original_ROMs/kn5000_subprogram_v140.rom` (commit `2fb8a95`):

```
sha256  a39025fe7c3968102196c5e20c18c76ec42e31a6c535f48addd58e13dacd7ef0
size    196,608 bytes
```

The recovery is self-checking in both directions: recompressing the extracted payload with
`compress_lzss.py --strict --with-header --reference` against the factory image reproduces
that image **byte for byte** (93,124/93,124). The extraction is therefore not an
interpretation — it is the exact preimage of the shipped file.

There is still no v1.40 source tree, and the payload is not part of any build target. What
exists is an honest, hash-pinned artifact plus a reversible path back to the original.

### v1.41 — internally consistent, no source tree

Both v1.41 artifacts verify against each other: the compressed image decompresses
byte-exactly to `original_ROMs/kn5000_subprogram_v141.rom` (196,608/196,608, consuming
93,181/93,181 input bytes), and recompressing that payload reproduces the image
byte-for-byte. What is missing is a `v141/subcpu/` source tree, so `compare_roms.py`
cannot cover either artifact.

sha256 of the payload: `04212fa6799e75db64b399242b762ce7377669a0a877984659c78c148453d9fe`.

The proposed route is the one the main-CPU v7/v9/v10 trees already use: start from the
v142 source and reconcile against the v141 ROM. The raw byte diff looks daunting but is
not — most of it is address-constant ripple that symbolic assembly absorbs for free:

| Pair | Differing bytes | Contiguous runs |
|------|----------------:|----------------:|
| v1.40 ↔ v1.41 | 56,018 | 2,508 |
| v1.41 ↔ v1.42 | 124,033 | 2,875 |
| v1.40 ↔ v1.42 | 124,032 | 2,590 |

v1.40 is much closer to v1.41 than to v1.42, so a future v1.40 tree should be diffed
against v1.41 rather than against the current target.

## Why the update-image target matters

Verifying only the decompressed payload leaves a gap: the bytes a real KN5000 receives from
a firmware-update disk are the *compressed* ones. Adding the compress-and-compare rule
closes it, and it does so without weakening anything — `--strict` aborts the build the
moment the encoder's output diverges from the factory stream, so the check cannot degrade
into "close enough". The same guarantee already covers the in-ROM SLIDE4K demo presets and
the SLIDE8K help databases; see
[ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/).
