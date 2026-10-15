---
layout: page
title: System Update Discs
permalink: /system-update-discs/
---

# System Update Disc Format

The KN5000 uses 3.5" HD floppy discs (1.44 MB) for firmware updates. This page documents the disc format based on analysis of original Technics update discs archived at [archive.org](https://archive.org/details/technics-kn5000-system-update-disks).

## Disc Layout

Update discs use a **FAT12 filesystem** with a Technics-specific boot sector. The firmware reads specific files by their on-disc location (reading raw sectors at known offsets) rather than parsing the FAT directory by filename.

### Boot Sector (BPB)

The boot sector uses standard FAT12 BIOS Parameter Block fields with OEM ID "Technics":

| Offset | Size | Field | Value |
|--------|------|-------|-------|
| 0x00 | 3 | Jump + NOP | `EB 1C 90` |
| 0x03 | 8 | OEM ID | `Technics` |
| 0x0B | 2 | Bytes/sector | 512 |
| 0x0D | 1 | Sectors/cluster | 1 |
| 0x0E | 2 | Reserved sectors | 1 |
| 0x10 | 1 | Number of FATs | 2 |
| 0x11 | 2 | Root dir entries | 224 |
| 0x13 | 2 | Total sectors | 2880 |
| 0x15 | 1 | Media descriptor | 0xF0 (3.5" HD) |
| 0x16 | 2 | Sectors/FAT | 9 |
| 0x18 | 2 | Sectors/track | 18 |
| 0x1A | 2 | Number of heads | 2 |
| 0x1C | 4 | Hidden sectors | 0 |
| 0x1E | 2 | Boot code | `EB FE` (see note below) |

**Note on `EB FE`:** On x86, `EB FE` decodes as `JMP $` (an infinite loop), which is the standard boot code for non-bootable FAT floppies. However, on the KN5000's TLCS-900 CPU, these same bytes decode as `SLL A, XHL` (Shift Left Logical XHL by A bit positions) — a completely different instruction. This is irrelevant in practice because the **firmware never reads or executes sector 0** (see [No Code Execution from Floppy](#no-code-execution-from-floppy) below). The boot sector exists purely for PC compatibility.

Bytes 32–511 are zero except byte 37 which is `0x01` on v10 discs (extended BPB "current head" field, non-functional).

### Sector Map

| Sectors | Offset | Content |
|---------|--------|---------|
| 0 | 0x0000 | Boot sector (BPB) |
| 1–9 | 0x0200 | FAT 1 |
| 10–18 | 0x1400 | FAT 2 (copy of FAT 1) |
| 19–32 | 0x2600 | Root directory (224 entries × 32 bytes) |
| 33+ | 0x4200 | Data area (cluster 2 starts here) |

### Data Area Layout

Files occupy contiguous clusters starting at cluster 2:

| Cluster | Sector | Offset | File |
|---------|--------|--------|------|
| 2 | 33 | 0x4200 | Signature file (TECHNICS.PRP or TECHNICS.AE) |
| 3 | 34 | 0x4400 | DUMMY.1 |
| 4 | 35 | 0x4600 | DUMMY.2 |
| 5+ | 36+ | 0x4800 | Data file (HKMSPRG.SLD or HKEXTROM.XAP) |

Unused sectors in the data area are filled with `0xE5` (standard DOS format fill byte).

---

## File Contents

### Program ROM Update Disc (Type 7)

Used for compressed program ROM updates (versions 5–10).

| File           | Size     | Content                                                             |
|----------------|----------|---------------------------------------------------------------------|
| `TECHNICS.PRP` | 56 bytes | Signature + author credit                                           |
| `DUMMY.1`      | 64 bytes | Table data signature placeholder                                    |
| `DUMMY.2`      | 64 bytes | Table data signature placeholder                                    |
| `HKMSPRG.SLD`  | ~1 MB    | SLIDE4K compressed program ROM, then the compressed sub-CPU payload |

**TECHNICS.PRP** (56 bytes):
```
Technics KN5000 Program  DATA FILE PCK  by T.Nishino\r\n\r\n
```

The first 38 bytes are the disc type signature matched by the firmware (see [Disc Type Detection](#disc-type-detection) below).

**DUMMY.1** and **DUMMY.2** (64 bytes each):
```
Technics KN5000 Table    DATA FILE 1/2 by Nishino Teruhiko !!!\r\n
```

These are non-functional placeholders. Their content matches the Table Data disc type 3 signature, suggesting they were leftover from the uncompressed 2-disc format (types 1–4) where program and table data were split across multiple floppies.

**HKMSPRG.SLD** — two SLIDE4K streams back to back: the compressed program ROM, then the compressed sub-CPU payload (see [Update Handlers by Type](#update-handlers-by-type)). The first stream's header:

| Offset | Size | Field |
|--------|------|-------|
| 0x00 | 8 | Magic: `SLIDE4K\0` |
| 0x08 | 3 | Decompressed size (24-bit big-endian) |
| 0x0B | var | LZSS compressed data stream |

For the 2 MB program ROM, the size bytes are `20 00 00` (0x200000 = 2,097,152). See [LZSS Compression](lzss-compression.md) for the SLIDE4K format specification.

Observed compressed sizes across firmware versions:

| Version | HKMSPRG.SLD Size | Compression Ratio |
|---------|------------------|-------------------|
| v5 | 1,056,514 bytes | 50.4% |
| v7 | 1,057,941 bytes | 50.4% |
| v10 | 1,058,748 bytes | 50.5% |

### HD-AE5000 Extension Update Disc (Type 6)

Used for HDAE5000 expansion board firmware.

| File | Size | Content |
|------|------|---------|
| `TECHNICS.AE` | 65 bytes | Signature + author credit |
| `DUMMY.1` | 64 bytes | Table data signature placeholder |
| `DUMMY.2` | 64 bytes | Table data signature placeholder |
| `HKEXTROM.XAP` | 524,288 bytes | Raw (uncompressed) extension ROM |

**TECHNICS.AE** (65 bytes):
```
Technics KN5000 HD-AEPRG DATA FILE      by Nishino Teruhiko !!!\r\n\n
```

**HKEXTROM.XAP** — Raw 512 KB extension ROM binary, not compressed.

---

## Disc Type Detection

The firmware identifies update discs by comparing a **38-byte signature** against a table of signature strings, which the Table Data ROM holds at `0x9FA000` and the Program ROM holds again at `0xE00038`.

### Detection Algorithm

Two routines do this: the bootloader's `Boot_DetectDiskType` (`0x9FBFC4`), against `FileIdentifierStringsTable` at `0x9FA000`, and the program ROM's `Detect_Disk_Type` (`0xEF42FE`), against its own copy of the strings at `0xE00038`–`0xE00150` (`FILETYPE_SIG_*` in `boot/boot_data_tables.s`). Both:

1. Reads sectors from the floppy into a 512-byte buffer
2. Compares buffer content against each of 8 known signatures (38 bytes each)
3. Returns type code 1–8 on match, or `0xFF` if unknown

The signature is found at the start of TECHNICS.PRP (sector 33, offset 0x4200), which is the first file in the data area.

### Signature Table

All 8 signature strings are stored consecutively in the Table Data ROM:

| Type | ROM Address | Signature (38 bytes)                     | Purpose                                         |
|------|-------------|------------------------------------------|-------------------------------------------------|
| 1    | 0x9FA000    | `Technics KN5000 Program  DATA FILE 1/2` | Program ROM disk 1 of 2 (uncompressed)          |
| 2    | 0x9FA028    | `Technics KN5000 Program  DATA FILE 2/2` | Program ROM disk 2 of 2 (uncompressed)          |
| 7    | 0x9FA050    | `Technics KN5000 Program  DATA FILE PCK` | Program ROM (SLIDE4K compressed)                |
| 3    | 0x9FA078    | `Technics KN5000 Table    DATA FILE 1/2` | Table Data ROM disk 1 of 2                      |
| 4    | 0x9FA0A0    | `Technics KN5000 Table    DATA FILE 2/2` | Table Data ROM disk 2 of 2                      |
| 8    | 0x9FA0C8    | `Technics KN5000 Table    DATA FILE PCK` | Table Data ROM (SLIDE4K compressed)             |
| 5    | 0x9FA0F0    | `Technics KN5000 CMPCUSTOMDATA FILE    ` | Custom data (`CMPCUSTOMDATA`, written verbatim) |
| 6    | 0x9FA118    | `Technics KN5000 HD-AEPRG DATA FILE    ` | HDAE5000 extension firmware                     |

Types 7 and 8 ("PCK" = packed/compressed) replaced the older 2-disc uncompressed format (types 1–4). All archived update discs from v5 onward use type 7.

---

## Update Flow

The firmware update runs at boot when all four PANEL MEMORY buttons are held at power-on with an update disc in the drive, and the version byte at `0xFFFFE8` reads `0xFF`. No routine writes that byte (v10 holds `0x0A` there); how the check is met on a stock unit is open (see [MAME Emulation Gaps]({{ site.baseurl }}/mame-emulation-gaps/)).

### Sequence

1. **Detect floppy** — Check port PD bit 6 for disc change signal
2. **Read signature** — Read sectors from the floppy, match against signature table
3. **Display status** — Show "Flash Memory Update" on the LCD
4. **Erase flash** — Display "Now Erasing!!" and erase the target flash chip
5. **Program flash** — Read data sectors from floppy and program flash memory
6. **Complete** — Display "Completed!" and "Turn On AGAIN!!"

### Update Handlers by Type

| Type                        | Handler Address | Destination                                                      | Method                                             |
|-----------------------------|-----------------|------------------------------------------------------------------|----------------------------------------------------|
| 1 (Program 1/2)             | `0xEF4784`      | the `0x800000` flash pair, 1 MB + 1 MB                           | chip-erase, then direct copy (2-disc set)          |
| 3 (Table 1/2)               | `0xEF47A4`      | the `0x800000` flash pair, 1 MB + 1 MB                           | chip-erase, then direct copy (2-disc set)          |
| 2, 4 (second disc of a set) | `0xEF482A`      | —                                                                | refused: "Illegal Disk!" and halt                  |
| 5 (CMPCUSTOMDATA)           | `0xEF47C7`      | Custom Data Flash `0x300000`, all 1 MB                           | chip-erase, then verbatim write of the whole image |
| 6 (HDAE5000)                | `0xEF47DF`      | Extension ROM `0x280000`, 512 KB                                 | chip-erase bank 2, then direct copy                |
| 7 (Program PCK)             | `0xEF47FA`      | **both**: the `0x800000` pair *and* Custom Data Flash `0x3E0000` | see below                                          |
| 8 (Table PCK)               | `0xEF481E`      | the `0x800000` pair                                              | SLIDE4K decompress from floppy                     |

**Type 7 in detail** — a `.SLD` file holding *two* concatenated SLIDE4K streams:

1. stream 1 (the 2 MB main-program image) is decompressed straight into the `0x800000`
   window during the install;
2. IC19 sectors `0x3E0000` and `0x3F0000` are erased and stream 2 (the compressed
   **sub-CPU payload**) is written there **verbatim**, exactly `0x20000` bytes.

> ⚠ `0x3E0000` is **not** a staging area for the program ROM. It holds the compressed
> **sub-CPU payload**, permanently, and `SubCPU_Send_Payload` reads it on **every** boot.
> The main program is programmed during the install itself, not by a later boot.
> See [Sub-CPU Payload Provenance]({{ site.baseurl }}/subcpu-payload-provenance/).

Note that the `0x800000` window is the target for both program and table images. Which
physical chip pair answers there depends on which of the two updater copies is running —
the bootloader's or the program flash's — because the memory map differs between them.
See [TMP94C241 Memory Controller]({{ site.baseurl }}/tmp94c241-memory-controller/).
See also [Flash Programming](flash-programming.md).

---

## Available Update Discs

The following original update disc images are archived at the [Internet Archive](https://archive.org/details/technics-kn5000-system-update-disks):

| Filename | Type | Version | Format |
|----------|------|---------|--------|
| `kn5000_v5_disk.img` | 7 | v5 | FAT12 + SLIDE4K |
| `kn5000_v6_disk.img` | 7 | v6 | FAT12 + SLIDE4K |
| `kn5000_v7_disk.img` | 7 | v7 | FAT12 + SLIDE4K |
| `kn5000_v8_disk.img` | 7 | v8 | FAT12 + SLIDE4K |
| `kn5000_v9_disk.img` | 7 | v9 | FAT12 + SLIDE4K |
| `kn5000_v10_disk.img` | 7 | v10 | FAT12 + SLIDE4K |
| `hd-ae5000_disk.img` | — | — | Contains AE5-115.EXE (DOS installer) |

Note: The `hd-ae5000_disk.img` contains a DOS executable (`AE5-115.EXE`) that creates the actual update disc when run on a PC, rather than being a ready-to-use update disc itself. The extracted HD-AE5000 update files (TECHNICS.AE, DUMMY.1, DUMMY.2, HKEXTROM.XAP) are available separately in the archive.

### Boot Sector Variations

All program update discs share identical BPB parameters. The OEM ID field varies between versions:

| Version | OEM ID |
|---------|--------|
| v5 | `(O%W{IHC` (garbage — created by non-standard tool) |
| v7, v8, v9, v10 | `Technics` |

This difference is cosmetic and does not affect functionality.

---

## Creating Update Discs

The [kn5000-anotherworld](https://github.com/felipesanches/kn5000-anotherworld) homebrew repository includes a tool for creating update discs, `tools/make_update_disc.py`:

```bash
# Create compressed program ROM update disc
python tools/make_update_disc.py out/custom_program.rom out/update_disc.img --type 7

# Create HDAE5000 extension update disc
python tools/make_update_disc.py out/extension.rom out/update_disc.img --type 6
```

The tool reproduces the original disc layout (boot sector, FAT structure, file layout, fill bytes), but not the original `HKMSPRG.SLD`. It writes a single SLIDE4K stream, a plain re-encoding of the ROM: valid, but not the factory bytes (see [Byte-Exact Recompression]({{ site.baseurl }}/lzss-compression/#byte-exact-recompression)), and with no second stream.

> ⚠ **A type-7 disc made with this tool lacks the sub-CPU payload.** An original `HKMSPRG.SLD`
> carries the compressed sub-CPU payload as a second stream (see [Update Handlers by Type](#update-handlers-by-type)).
> The type-7 handler erases IC19 `0x3E0000`–`0x3FFFFF` before it reads `HKMSPRG.SLD` and rewrites
> that area only when a second `SLIDE` header follows the program stream. Read from the code, not
> tested: installing such a disc would leave that area erased, and `SubCPU_Send_Payload` would then
> fall back to `0x800000`, which holds table data, not a payload.

---

## No Code Execution from Floppy

An important architectural finding: **none of the 8 system-update disc types makes the KN5000 execute code from floppy disc.** Each of them either writes data to flash memory or is refused; none load code into RAM for execution. The one exception in the firmware is a hidden factory loader, not an update disc: on the "DEBUG SCREEN for HD-AE" page, the LOAD switch reads `A:HKEXT.XAP` (32 KB) from floppy into RAM at `0x200000`, and the GO switch checks for the `XAPR` id there and jumps to `0x200008` (`HamaDeb_HdaeDebugScreenFunc`, `CheckFDStatusLoad_Entry` and `LoadExtROM_Entry` in `factory_test/test_init.s`). How a user reaches that page has not been established.

### Evidence

1. **Boot sector is never read.** All 9 calls to the FDC read routine (`FDC_ReadSectors`) use sector 33 or higher. The `Detect_Disk_Type` routine reads the data area to find the signature file — it never examines sector 0, the BPB, or any boot code.

2. **Update handlers write to flash or halt.** The handlers for types 1, 3 and 5–8 program flash memory; after "Completed!" and "Turn On AGAIN!!" the boot code spins in an endless loop (`Boot_MainSequence_Trampoline`, `0xEF05E6`). Types 2 and 4, and an unrecognised disc, halt at "Illegal Disk!" (`SHOW_ILLEGAL_DISK_MESSAGE`) without writing; on a Region 4 unit, or when the `0x800000` pair is not recognised, every disc except type 6 is ignored without a message and the boot code still ends in that loop (see [Firmware Update Validation]({{ site.baseurl }}/firmware-update-validation/#7-region-code-check)). No handler copies data to RAM and jumps to it.

3. **No disc type for executable content.** The 8-entry signature table at `0x9FA000` covers firmware images (types 1–4, 7–8), custom data (type 5), and HDAE5000 extension firmware (type 6). There is no signature for an executable or loadable code disc.

4. **Standard file I/O is data-only.** Beyond system updates, floppy I/O handles MIDI songs, registrations, styles and sequencer data, all interpreted by existing firmware routines. The one exception is the factory HD-AE debug loader described above (`A:HKEXT.XAP`).

### Implications

Apart from that factory loader, the floppy subsystem is strictly a data transport, and custom code can only be installed via flash update (replacing the entire Program ROM or Extension ROM); no update disc loads and runs it directly. This is consistent with the KN5000's embedded architecture — there is no operating system with a program loader.

---

## References

- [LZSS Compression](lzss-compression.md) — SLIDE4K format specification and decompression routines
- [Flash Programming](flash-programming.md) — Flash erase/program routines and update handlers
- [FDC Subsystem](fdc-subsystem.md) — Floppy disk controller hardware and driver routines
- [Storage Subsystem](storage-subsystem.md) — Overview of KN5000 storage architecture
- [Floppy Security Analysis](floppy-security-analysis.md) — Code injection vectors via crafted update discs
- [Internet Archive: Technics KN5000 System Update Disks](https://archive.org/details/technics-kn5000-system-update-disks) — Original disc images

---

*Last updated: October 2026*
