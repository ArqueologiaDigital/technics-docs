---
layout: page
title: Floppy Security Analysis
permalink: /floppy-security-analysis/
---

# Floppy Security Analysis

Security analysis of the KN5000 v10 Program ROM's floppy handling code, examining whether bugs could be exploited to inject arbitrary code from a crafted floppy disc.

**Target:** Program ROM v10, as disassembled in `v10/maincpu/` (157 `.s` files)
**Scope:** All floppy-related code paths — update handlers, LZSS decompression, normal file I/O

---

## Executive Summary

The firmware has **no cryptographic authentication** of floppy disc content — disc type detection uses a 38-byte ASCII string comparison against known signatures. Combined with an LZSS decompressor that trusts a header-specified output size, there is a viable chain for injecting attacker-controlled data into RAM during boot. No exploit is needed for code execution. A type 7 disc *is* a program update: anyone who writes its 38-byte signature and a SLIDE4K image gets an arbitrary main-CPU program installed by the bootloader's updater, and a type 6 disc installs an arbitrary HD-AE5000 extension ROM the same way. The site's homebrew ROM replacements can be packaged as such a disc with `tools/make_update_disc.py` (see [Firmware Update Procedure]({{ site.baseurl }}/firmware-update-procedure/)). The same disc's second stream, written to `0x3E0000`, is the sub-CPU's executable payload, which `SubCPU_Send_Payload` decompresses and sends to the sub CPU on every boot. The unbounded decompression below matters as a way to corrupt main-CPU RAM, not as the route to code execution.

---

## Findings

### 1. LZSS Decompressor Trusts Attacker-Controlled Size

**Severity:** High
**Routine:** `SLIDE_Decompress_4K_Init` (4KB-window LZSS) at `0xEF3FAB`

The LZSS decompressor reads the expected decompressed size from the [SLIDE4K]({{ site.baseurl }}/lzss-compression/) stream header:

```asm
LD E, (XWA + 002h)     ; Byte 2 of header
SLL 8, XDE
LD L, (XWA + 003h)     ; Byte 3 of header
ADD XHL, XDE
...
ADD XIX, XHL            ; XIX = expected decompressed size (24-bit)
```

The main loop terminates only when `XHL >= XIX`:
```asm
CP XHL, XIX             ; Current output count vs expected
JRL NC, SLIDE_Decompress_4K_Done   ; Exit when done
```

The decompressed size is read directly from the compressed data, which originates from floppy. The output pointer (`XDE3`) advances without any bounds checking against the destination buffer size. The dictionary index wraps with `AND BC, 0fffh`, protecting the 4KB dictionary buffer — but NOT the output buffer.

A parallel 8KB-window variant (`SLIDE_Decompress_8K_Init` at `0xEF40C5`) has the same unbounded output behavior.

---

### 2. Type 7 Update Creates Exploitable Boot Chain

**Severity:** High
**Impact:** Persistent control of the main program and of the sub-CPU payload

This is the most viable attack vector, chaining two operations across a reboot.

#### Step 1 — Update disc writes to flash

The type 7 handler (`HANDLE_UPDATE_FILE_TYPE_ID_007h` at `0xEF47FA`) calls:
- `LZ_Decompress_Init` — decompresses stream 1, the 2 MB main-program image, from floppy into the `0x800000` window. Which chip pair answers there depends on which updater copy runs: a type 7 disc is installed by the bootloader's own copy of this handler (`Boot_LoadDiskData`, Table Data ROM), before the chip-select handover, when the program flash pair answers; under this Program-ROM copy the window is the table-data pair (see [System Update Discs]({{ site.baseurl }}/system-update-discs/#update-handlers-by-type) and [TMP94C241 Memory Controller]({{ site.baseurl }}/tmp94c241-memory-controller/)).
- `LZSS_Decompress_ToFlash` — despite its name, decompresses nothing: it checks the `SLIDE` header of stream 2 and copies the stream verbatim (still compressed), exactly `0x20000` bytes, to Custom Data Flash at `0x3E0000`

The attacker controls the entire compressed payload on the floppy disc.

#### Step 2 — Every boot decompresses to RAM

During every boot, in `SubCPU_Send_Payload` (at `0xEF0710`):
```asm
CP (0FFFEEDh), 0ffh       ; SubCPU_FlashPayloadEnableFlag (ROM byte, 0xFF in v7/v9/v10)
JR NZ, SubCPU_Payload_TransferPart2       ; Use the 0x800000 copy if not 0xFF
LD XIZ, 00050000h
LD XWA, 003e0000h         ; Source: Custom Data Flash
LD XBC, 00050000h         ; Destination: RAM
CALL SLIDE_Parse_Header         ; Decompress SLIDE4K → RAM
```

The SLIDE4K wrapper validates the "SLIDE" magic string, then calls the LZSS decompressor with `XBC = 0x050000` (RAM). If the attacker's payload at `0x3E0000` specifies a large decompressed size, the decompressor writes attacker-controlled bytes **sequentially from `0x050000` upward in RAM** with no bounds check.

#### Step 3 — The decompressed data is sent to the sub CPU as its program

Immediately after decompression:
```asm
LDW (0404h), (XIZ + 0100h)   ; Read from decompressed data + 0x100
LD XWA, XIZ
ADD XWA, 00000100h
LD XBC, 00010000h            ; Byte count: 0x10000 (64 KB)
LD XDE, 0000f000h            ; Destination: sub-CPU address 0x00F000
CALL InterCPU_E1_Bulk_Transfer
```

`SubCPU_Send_Payload` (`0xEF068A`) then sends the decompressed image to the **sub CPU** with `InterCPU_E1_Bulk_Transfer` (XWA = source, XBC = byte count, XDE = destination in the sub-CPU's address space): 64 KB from offset `0x100` to sub-CPU `0x00F000`, the next 64 KB to `0x01F000`, `0xFF00` bytes to `0x02F000`, and so on. The decompressed data is the sub-CPU's program, so the attacker controls the code the sub CPU runs.

#### Full chain diagram

```
Floppy Disc (Type 7: "Technics KN5000 Program  DATA FILE PCK")
    │
    ├──> LZ_Decompress_Init: Decompress → 0x800000 window
    │    [Attacker controls the main-program image]
    │
    └──> LZSS_Decompress_ToFlash: copy verbatim (still compressed) → Custom Data Flash (0x3E0000)
         [Attacker controls the compressed sub-CPU payload read on every boot]
             │
             v (on every boot, ROM byte 0xFFFEED == 0xFF)
         SLIDE_Parse_Header: Decompress 0x3E0000 → RAM 0x050000
             │   [LZSS output size = attacker-controlled header value]
             │   [No bounds check on output buffer]
             v
         InterCPU_E1_Bulk_Transfer: (0x050000 + 0x100 ..) → sub-CPU 0x00F000, 0x01F000, 0x02F000
             [Attacker controls the sub-CPU program]
```

---

### 3. No Disc Authentication

**Severity:** High
**Routine:** `Detect_Disk_Type` at `0xEF42FE`

Disc type detection is a plain 38-byte ASCII string comparison. The 8 signatures are known plaintext strings stored in ROM (see [System Update Discs — Signature Table]({{ site.baseurl }}/system-update-discs/#signature-table)):

| Type | Signature |
|------|-----------|
| 1 | `Technics KN5000 Program  DATA FILE 1/2` |
| 2 | `Technics KN5000 Program  DATA FILE 2/2` |
| 3 | `Technics KN5000 Table    DATA FILE 1/2` |
| 4 | `Technics KN5000 Table    DATA FILE 2/2` |
| 5 | `Technics KN5000 CMPCUSTOMDATA FILE    ` |
| 6 | `Technics KN5000 HD-AEPRG DATA FILE    ` |
| 7 | `Technics KN5000 Program  DATA FILE PCK` |
| 8 | `Technics KN5000 Table    DATA FILE PCK` |

There is no HMAC, CRC, RSA signature, or any other integrity check. Anyone with the signature string can create a disc that the firmware accepts as a valid update.

The handler dispatch does validate the type range (1–8) before jumping:
```asm
DEC 1, WA
CP WA, 0
JRL LT, SHOW_ILLEGAL_DISK_MESSAGE
CP WA, 7
JRL GT, SHOW_ILLEGAL_DISK_MESSAGE
```

---

### 4. Type 7 Decompressor Reads Size from Floppy Stream

**Routine:** `LZ_Decompress_Init` at `0xEF4D95`

The inline LZSS decompressor for type 7/8 updates reads the decompressed size directly from the floppy data stream (3 bytes → 24-bit value stored at `0x063E`). The decompression loop continues until the byte counter reaches this value. Each decompressed byte is accumulated in a 4-byte buffer, then written to flash via `Flash_ProgramByte`.

The flash destination starts at `TABLE_DATA_ROM__BASE_ADDR` (`0x800000`) and advances by 4 each write. If the attacker sets the decompressed size larger than 2 MB (the Table Data ROM size), writes continue past `0x9FFFFF`, outside the 2 MB `0x800000` window to which `Flash_ProgramByte` sends its unlock sequence (see [Flash chip-select isolation](#flash-chip-select-isolation)).

---

### 5. Compressed Stream Exhaustion → Infinite Loop

**Severity:** Low (denial of service only)

The byte reader `Parport_ReadNextByte` refills the sector buffer from floppy in 4-track chunks. If the attacker inflates the expected decompressed size but provides a short compressed stream, the decompressor exhausts the floppy data. The FDC read routine (`FDC_ReadSectors`) then retries indefinitely, creating an **infinite loop** requiring a power cycle.

---

## Mitigating Factors

### Hardcoded sector counts and flash destinations

Sector counts and flash write addresses are hardcoded in the firmware, not read from disc data:

| Type | Starting Sector | Flash Destination                                                |
|------|-----------------|------------------------------------------------------------------|
| 1    | 0x24 (36)       | `0x800000` window (the program pair during a bootloader install) |
| 3    | 0x24 (36)       | `0x800000` (Table Data ROM)                                      |
| 5    | 0x24 (36)       | `0x300000` (Custom Data Flash)                                   |
| 6    | 0x24 (36)       | `0x280000` (HDAE5000 ROM)                                        |
| 7    | 4-track chunks  | `0x800000` + `0x3E0000`                                          |
| 8    | 4-track chunks  | `0x800000`                                                       |

The attacker cannot redirect writes to arbitrary flash regions. The disc type determines which hardcoded handler runs.

### Flash chip-select isolation

This is not a barrier against a malicious update disc. `Flash_ProgramByte` (the Program ROM's writer) unlocks at `0x815554`/`0x80AAA8` in the `0x800000` window, and which chip pair answers in that window depends on which updater copy is running (provisional; see [TMP94C241 Memory Controller]({{ site.baseurl }}/tmp94c241-memory-controller/)). Program discs (types 1/2 and 7) are installed by the bootloader's own copy of the updater in the Table Data ROM (`Boot_LoadDiskData`), with its own base-relative unlock routines, before the chip-select handover, when the program flash pair answers at `0x800000`. That is how those discs reprogram the Program ROM (see [System Update Discs]({{ site.baseurl }}/system-update-discs/#update-handlers-by-type)).

### Code runs from ROM

The TLCS-900/H2 executes code from Program ROM (`0xE00000`–`0xFFFFFF`). Interrupt vectors are also in ROM. A RAM buffer overflow from `0x050000` upward corrupts RAM data but does not directly overwrite executable code.

### Stack location

The boot stack starts at `0xC00`, the top of on-chip RAM (`0x000400`–`0x000BFF`; `ld xsp, 0xc00` in `kn5000_v10_program.s`), and `TaskSched_Init` later moves it to `0x01E53A` in work DRAM. Both are below the overflow origin at `0x050000`, so a sequential upward overflow cannot reach the stack.

### LZSS dictionary wraps safely

The dictionary index in both LZSS variants uses `AND BC, 0fffh` (4KB) or `AND BC, 01fffh` (8KB), preventing dictionary buffer overflow.

### Normal file I/O uses ROM sources

The SLIDE4K wrapper `SLIDE_Parse_Header` has only 3 callers:

| Call Site | Source | Destination | Floppy-Reachable? |
|-----------|--------|-------------|-------------------|
| Boot (`0xEF0710`) | Custom Data Flash `0x3E0000` | RAM `0x050000` | **Yes** (via type 7 update) |
| `0xF477D3` | Table Data ROM `0x988018`+ | RAM `0x069800` | Indirectly (if Table Data ROM corrupted) |
| `0xF871A0` | Table Data ROM `0x9C4000`+ | RAM `0x069800` | Indirectly (if Table Data ROM corrupted) |

No callers decompress directly from floppy to RAM. The boot-time path is the only one reachable from floppy data, via the sub-CPU payload that a type 7 disc writes to Custom Data Flash.

---

## Open Questions

These areas require further investigation to determine whether the data-control primitive can be elevated to code execution:

1. **What a malicious sub-CPU program can do to the main CPU**: the decompressed `0x3E0000` stream is the sub-CPU's executable payload, so the open question is whether main-CPU handlers that trust sub-CPU messages over the inter-CPU latch can be driven into misbehaviour.

2. **Secondary LZSS payloads via Table Data ROM**: Since a type 8 (Table PCK) update gives the attacker full control of Table Data ROM content, and two routines decompress from Table Data ROM to RAM at `0x069800`, the attacker could embed secondary malicious SLIDE4K payloads that overflow during normal firmware operation.

3. **The `EXEC` tag in the SSF presentation system**: If the XML parser at `AcPresentationControlProc` (`0xF8450B`) implements the `EXEC` tag by dispatching to data-specified routines, and Table Data ROM content influences those routines, this could provide a code execution path. See [Feature Demo & Presentation System]({{ site.baseurl }}/feature-demo/).

---

## Key Code References

| Routine                                | Address    | Purpose                                                                 |
|----------------------------------------|------------|-------------------------------------------------------------------------|
| `SLIDE_Decompress_4K_Init`             | `0xEF3FAB` | 4KB-window LZSS decompressor                                            |
| `SLIDE_Decompress_8K_Init`             | `0xEF40C5` | 8KB-window LZSS decompressor                                            |
| `SLIDE_Parse_Header`                   | `0xEF41E3` | SLIDE4K/8K wrapper (magic check, dispatch)                              |
| `Flash_ProgramByte`                    | `0xEF3D7B` | Flash write — Table Data ROM (AMD protocol)                             |
| `Flash_ProgramWord`                    | `0xEF3815` | Flash write — Custom Data / HDAE5000                                    |
| `FDC_ReadSectors`                      | `0xEF42CC` | FDC sector read loop                                                    |
| `Detect_Disk_Type`                     | `0xEF42FE` | 38-byte signature matching                                              |
| `Erase_and_Burn____when_disk_is_valid` | `0xEF4745` | Update handler dispatch (validates type 1–8)                            |
| `FDC_WriteSectors`                     | `0xEF441B` | Uncompressed disc → flash writer                                        |
| `FDC_WriteSectors_Compressed`          | `0xEF454D` | Extension/custom data → flash writer                                    |
| `LZ_Decompress_Init`                   | `0xEF4D95` | Type 7/8 inline LZSS → `0x800000` window                                |
| `LZSS_Decompress_ToFlash`              | `0xEF4CF8` | Type 7 stream 2 → Custom Data Flash, copied verbatim (no decompression) |
| `Parport_ReadNextByte`                 | `0xEF4C07` | Byte reader with floppy refill                                          |
| `Flash_AccumWrite_Byte`                | `0xEF4C7A` | Decompressed byte → flash accumulator                                   |
| `FLASH_MEM_UPDATE`                     | `0xEF4F6F` | Top-level update entry point                                            |
| `String_Compare`                       | `0xFF0CC1` | Byte-by-byte string comparison                                          |

---

## Related Pages

- [System Update Discs]({{ site.baseurl }}/system-update-discs/) — Disc format, signatures, update flow, no-code-execution finding
- [LZSS Compression]({{ site.baseurl }}/lzss-compression/) — SLIDE4K format specification
- [Flash Programming]({{ site.baseurl }}/flash-programming/) — Flash erase/program routines
- [FDC Subsystem]({{ site.baseurl }}/fdc-subsystem/) — Floppy disk controller handlers
- [Feature Demo & Presentation System]({{ site.baseurl }}/feature-demo/) — SSF XML system with `EXEC` tag
- [Storage Subsystem]({{ site.baseurl }}/storage-subsystem/) — Storage architecture overview
- [Boot Sequence]({{ site.baseurl }}/boot-sequence/) — Power-on initialization including SLIDE4K decompression

---

*Last updated: October 2026*
