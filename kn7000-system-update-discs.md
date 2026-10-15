---
layout: page
title: KN7000 System Update Discs
permalink: /kn7000-system-update-discs/
---

# KN7000 System Update Disc Format

The Technics SX-KN7000 receives firmware and data updates from floppy disks
containing LZSS-compressed `.SLD` files. The container is the same family as the
[KN5000's `SLIDE4K` format]({{ site.baseurl }}/system-update-discs/) and the same
[LZSS scheme]({{ site.baseurl }}/lzss-compression/), with different magic strings.

All findings below were verified by extracting the images and checking them
against the checksums shipped on the disks.

## Disc contents

Program and table updates each span two floppies; the v1.4 update (kn7-14)
carried both, on four. The sets this project holds:

| Set                   | Purpose                  | Disk 1                                                   | Disk 2                                    |
|-----------------------|--------------------------|----------------------------------------------------------|-------------------------------------------|
| **kn7-16**            | Program v1.6 (build 941) | `JK1.SLD`, `SMCKPR1.INF`, `TECHNICS.PR1`                 | `JK2.SLD`, `SMCKPR2.INF`, `TECHNICS.PR2`  |
| **kn7-15**            | Program v1.5 (build 935) | `JK1.SLD`, `SMCKPR1.INF`, `TECHNICS.PR1`                 | `JK2.SLD`, `SMCKPR2.INF`, `TECHNICS.PR2`  |
| **kn7-14**, disks 1–2 | Program v1.4 (build 929) | lost (the archived copy is only a 'page not found' stub) | `JK2.SLD`, `SMCKPR2.INF`, `TECHNICS.PR2`  |
| **kn7-14**, disks 3–4 | Table (build 84)         | `JKT1.SLD`, `SMCKTB1.INF`, `TECHNICS.TB1`                | `JKT2.SLD`, `SMCKTB2.INF`, `TECHNICS.TB2` |

Key Soft Service's SP7001 PLUG-iN update (program build 942, table build 83)
follows the same two-disk scheme and adds `BASEEXT.XAP` to its second table
disk; see [SD PLUG-iN]({{ site.baseurl }}/kn7000-sd-plugin/).

- `*.SLD` — one LZSS-compressed flash payload each.
- `SMCK*.INF` — checksum manifest for the combined image (identical on both disks of a set).
- `TECHNICS.*` — human-readable disk identification strings (e.g. `KN7KP1 Technics KN7000 Program  DATA 1/2`).
- `DUMMY.2` — a 10-byte placeholder (`Technics\r\n`).

## The `.SLD` container

An `.SLD` file is a header followed by a single LZSS stream:

| Offset | Size | Field |
|--------|------|-------|
| 0 | 8 | Magic string (see below) |
| 8 | 3 | **24-bit big-endian** size of the decompressed data |
| 11 | … | LZSS stream (4 KB sliding window pre-filled with `0x00`) |

Magic strings — the trailing "4K" denotes the 4-kilobyte LZSS window, exactly as
in the KN5000's `SLIDE4K`:

| Magic | Used by |
|-------|---------|
| `JKPRG4K\0` | `JK1.SLD`, `JK2.SLD` (program) |
| `JKTB14K\0` | `JKT1.SLD` (table, disk 1) |
| `JKTB24K\0` | `JKT2.SLD` (table, disk 2) |

The 24-bit size field retroactively decodes the KN5000 headers too:
`SLIDE4K\0\x20\x00\x00` = `0x200000` (2 MB program) and
`SLIDE4K\0\x03\x00\x00` = `0x030000` (192 KB sub-CPU payload).

### The two disks concatenate into one image

The decompressed payloads of the two disks are simply concatenated to form one
linear flash image (a JPEG straddles the `JK1`/`JK2` seam at `0x200000`, proving
linearity):

| Update | Disk 1 raw + Disk 2 raw | Combined image |
|--------|-------------------------|----------------|
| Program | `0x200000` + `0x1F6F01` | **`kn7000_program.rom`, 0x3F6F01 bytes** |
| Table | `0x200000` + `0x1E94D4` | **`kn7000_table.rom`, 0x3E94D4 bytes** |

## The `.INF` checksum oracle

Both disks of a set carry an identical `SMCK*.INF` text file describing the
combined image — a `@`-prefixed hex value per line:

```
@18CE8702	;	TOTAL SUM CHECK      <- 32-bit sum of every byte of the image
@4C81		;	BLOCK	 0           <- 16-bit sum of the bytes in flash block 0
@0412		;	BLOCK	 1
...                                          16 blocks of 0x40000 (the last is partial)
```

The target flash is nominally 4 MB (16 × `0x40000`); the Program update ships
`0x3F6F01` bytes, leaving the top `0x90FF` of the part unwritten (the length
varies by build). Both extracted images verify perfectly against these manifests:

| Image | Total sum | Blocks |
|-------|-----------|--------|
| Program | `0x18CE8702` | 16/16 match |
| Table | `0x13DCD1A3` | 16/16 match |

Of the builds found since: the v1.5 program also verifies 16/16; the surviving
v1.4 disk 2 verifies its eight blocks (8–15); the SP7001 program's shipped
`.INF` matches none of the 16 blocks, because it predates the final payload;
and the SP7001 table matches all but blocks 14–15, the plug-in area.

## Extraction

The `kn7000_extraction` tool decompresses the `.SLD` files, concatenates the two
disks of each set, and verifies the result against the `.INF` manifest before
writing `kn7000_program.rom` and `kn7000_table.rom`. It reuses the same LZSS
decompressor used for the KN5000 (`pylzss`, 4 KB window, zero-initialized).

> **What that omitted `0x90FF` is *not*.** It is not the home of the resident flash
> updater. On the owner's build-893 instrument the top of the program flash
> (`0x487F55CF`–`0x487FFFFF`) reads as one unbroken block of `0xFF`, so nothing
> resident lives there. Nor is the omission a reserved block: the payload length
> simply varies by build (`0x3F6E9D` bytes for v1.5, `0x3F6F01` for v1.6,
> `0x3F8BDB` for the SP7001 build 942, which writes into the very range v1.6
> leaves blank). See
> [Where does the flash updater live?]({{ site.baseurl }}/kn7000-firmware-security/#45-where-does-the-flash-updater-live-unresolved).
>
> The only never-read part of the IC16/IC17 pair on a unit without the SP7001
> PLUG-iN is at the *other* end of the address space: **`0x483E94D4`–`0x483FFFFF`**,
> immediately above where the standard table payload stops. The SP7001 PLUG-iN
> table update does write it: its table image is a full `0x400000` bytes, with
> plug-in code and strings up to `0x483FB59F`.

See the [Firmware Images]({{ site.baseurl }}/kn7000-firmware/) page for what the extracted images
contain.
