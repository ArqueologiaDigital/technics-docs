---
layout: page
title: Firmware Update Validation
permalink: /firmware-update-validation/
---

# Firmware Update Validation and Error Handling

This page documents the validation checks, error handling, and security properties of the KN5000's firmware update process, based on analysis of the Program ROM code.

## Pre-Update Validation

The firmware performs several checks before beginning a flash update. All must pass for the update to proceed.

### 1. Update Mode Sentinel (0xFFFFE8)

The firmware version byte at ROM address `0xFFFFE8` must equal `0xFF` to enter update mode. This sentinel value is written by the firmware before triggering a reset to signal that an update should be attempted on next boot.

**Code:** `Get_Firmware_Version` at boot (`0xFFFFE5`), compared to `0xFF`.

### 2. Floppy Disc Presence

`Check_for_Floppy_Disk_Change` reads the disc-change signal on Port D bit 6. If no disc is present, the update is skipped and normal boot continues.

### 3. Button Held During Boot

The control panel scan (`CPanel_ScanButtons`) must return value 4, indicating a specific button combination is held during boot. Without this, the update is skipped even if the sentinel and disc are present.

**Code:** `cpdi8 1026, 4` at `0xEF05CF`.

### 4. Disc Type Signature Match

`Detect_Disk_Type` (`0xEF42FE`) reads sector 33 (offset 0x4200) from the floppy — the first file in the FAT data area — and compares the first **38 bytes** (0x26) against 8 known signature strings stored in the Table Data ROM at `0x9FA000`.

**Algorithm:**
1. Allocate 512-byte buffer via `Malloc`
2. Read 1 sector starting at sector 0x21 (33) via `FDC_ReadSectors`
3. For each of 8 signatures: call string compare at `0xFF0CC1` with length 0x26 (38 bytes)
4. On match: store type code (1-8) and return
5. No match: return `0xFF` (unknown disc)

The comparison uses the ROM offsets relative to `0x9FA000`:

| Offset | Type | Signature |
|--------|------|-----------|
| 0x000 (+0x38) | 1 | `Technics KN5000 Program  DATA FILE 1/2` |
| 0x028 (+0x60) | 2 | `Technics KN5000 Program  DATA FILE 2/2` |
| 0x050 (+0x88) | 7 | `Technics KN5000 Program  DATA FILE PCK` |
| 0x078 (+0xB0) | 3 | `Technics KN5000 Table    DATA FILE 1/2` |
| 0x0A0 (+0xD8) | 4 | `Technics KN5000 Table    DATA FILE 2/2` |
| 0x0C8 (+0x100) | 5 | `Technics KN5000 CMPCUSTOMDATA FILE    ` |
| 0x0F0 (+0x128) | 6 | `Technics KN5000 HD-AEPRG DATA FILE    ` |
| 0x118 (+0x150) | 8 | `Technics KN5000 Table    DATA FILE PCK` |

The offsets in the second column are as passed to the compare function (relative to base `0xE0` which encodes the full ROM address `0x9FA000` through register pointer indirection).

### 5. Flash Chip Identification

`Flash_IdentifyAndValidateChip` (`0xEF379A`) probes the target flash memory using the standard AMD/Atmel flash Read ID command sequence:

1. Write `0xAA` to base+0xAAAA
2. Write `0x55` to base+0x5554
3. Write `0x90` to base+0xAAAA (Read ID command)
4. Read manufacturer ID and device ID

**Accepted manufacturer IDs:** `0x01` (AMD/Spansion), `0x04` (Fujitsu)

**Accepted device IDs:**

| ID | Device | Capacity |
|----|--------|----------|
| `0x2223` | AM29F040 | 512 KB |
| `0x22AB` | AM29F400B | 512 KB |
| `0x22D6` | AM29F800B | 1 MB |
| `0x2258` | AM29LV800B | 1 MB |

If the flash chip is not recognized, the function returns `0xFFFF` and the update for that target is skipped.

**Target flash chips:**
- A=0 → HDAE5000 Extension ROM at `0x280000`
- A=1 → Custom Data Flash at `0x300000`
- A=2 → Table Data ROM at `0x800000`

### 6. Type Range Validation

`Erase_and_Burn____when_disk_is_valid` (`0xEF4745`) validates the disc type code is in range 1-8 (after subtracting 1, checking 0-7). Out-of-range values trigger the "Illegal Disk!" fatal error.

### 7. Region Code Check (HDAE5000 Only)

For the HDAE5000 update path, the firmware checks the region code (derived from hardware port H bits 1-2). Region 4 units are excluded from HDAE5000 initialization (`call_24 nz, 0xEF4BCC`).

## What is NOT Validated

The firmware update process has several notable omissions in its validation:

### No Data Integrity Checks

- **No checksum** — The update data read from floppy is not checksummed or CRC-verified before or after writing to flash.
- **No hash verification** — No cryptographic hash of the update payload is computed or compared.
- **No size validation** — For uncompressed updates (types 1-4, 5, 6), the firmware reads a fixed number of sectors without verifying the total size matches expectations.
- **No LZSS integrity check** — The SLIDE4K decompressor reads a 3-byte decompressed size from the header but does not verify the compressed stream's integrity. Decompression terminates when either the byte count is reached or `Parport_ReadNextByte` returns `0xFFFF` (end of data).

### No Cryptographic Verification

- **No digital signature** — Any floppy disc with a matching 38-byte text signature will be accepted as a valid update disc.
- **No encryption** — Update data is stored in plaintext (raw ROM image or SLIDE4K compressed).

### No Version Checking

- **No downgrade prevention** — The firmware does not check whether the update version is newer, older, or the same as the currently installed version. Any valid disc can overwrite any version.
- **No compatibility check** — No hardware revision or model variant validation beyond the region code.

### No Post-Write Flash Verification

- `Flash_ProgramWord` (`0xEF3815`) writes a word to flash using the AMD program command sequence but **does not read back the programmed value** to verify it was written correctly.
- The word `0xFFFF` (erased state) is silently skipped (optimization — programming 0xFFFF to already-erased flash is a no-op).

## Post-Update Verification (Boot-Time Only)

Some verification routines exist but are used during **normal boot**, not during the update process itself:

### TableData_ROM_Verify (0xEF48AE)

Scans the Table Data ROM (`0x800000`-`0xA00000`) in 64-byte blocks, checking if the first word of each block is `0xFFFFFFFF` (erased). Returns immediately (non-zero) if any non-erased block is found. Returns 0 if the entire ROM is erased.

This is used at boot to detect whether the Table Data ROM has been erased (requiring re-programming from the staging area), not to verify the integrity of a completed update.

### HDAE5000_ROM_Transfer (0xEF48CF)

Transfers data between Table Data ROM and HDAE5000 ROM via the PPI interface at `0x160000`. This routine **does** verify each word transferred matches the source:

```
; Verify loop (simplified)
read_word_from_destination
compare_with_source
if_mismatch: return error (XHL != 0)
```

However, this is used for HDAE5000 ROM initialization at boot, not during the floppy update process.

## Error States

### Fatal: "Illegal Disk!" (Infinite Halt)

**Trigger:** Disc type code outside range 1-8, or types 2/4 used as the starting disc (these are "disc 2 of 2" types that cannot initiate an update).

**Handler:** `SHOW_ILLEGAL_DISK_MESSAGE` (`0xEF482A`)

**Behavior:**
1. Display "Illegal Disk!" bitmap at Y=160
2. Enter infinite loop: `jr IllegalDisk_HaltLoop` at address `0xEF4841`
3. **No recovery** — only power cycling the keyboard exits this state.

### Fatal: Flash Hardware Missing (Silent Skip)

**Trigger:** `Flash_IdentifyAndValidateChip` returns `0xFFFF` (no recognized flash chip found).

**Behavior:** The update for that target is silently skipped. No error message is displayed. The firmware continues to the next target (if any) or returns from `FLASH_MEM_UPDATE`.

For the main ROM path: if `0xEF3D0E` returns `0xFFFFFFFF`, the non-HDAE5000 erase/burn is skipped entirely.

### Fatal: Flash Not Ready (Hang)

**Trigger:** Port 7 bit 5 does not assert (flash busy/not responding).

**Behavior:** `Flash_ProgramWord` spins in a tight polling loop:
```asm
Flash_ProgramWord_WaitReady:
    bit 5, (P7:8)      ; Check P7 bit 5 (flash ready; SFR 0x1C is P7)
    jr z, Flash_ProgramWord_WaitReady  ; Spin until ready
```

There is no timeout. If the flash chip fails to become ready, the firmware hangs indefinitely.

### Recoverable: Disc Swap Mismatch

**Trigger:** During 2-disc updates (types 1/3), after prompting "Change FD (2/2)", the new disc's type doesn't match the expected second disc.

**Behavior:** The "Change FD (2/2)" message is displayed again and the firmware waits for another disc swap. This loops indefinitely until the correct disc is inserted. Not fatal — the user can keep trying.

### Recoverable: No Disc Present

**Trigger:** `Check_for_Floppy_Disk_Change` returns 0 (no disc detected).

**Behavior:** The firmware skips the update entirely and proceeds to normal boot. No error message.

### Fatal: Boot-Time ROM Verification Failure

**Trigger:** After boot, if Table Data ROM is found to be entirely erased (all 0xFFFFFFFF).

**Behavior:** At `0xEF4B54`, the firmware re-programs the Table Data ROM from the staging area. If flash identification fails (`0xEF3D0E` returns `0xFFFFFFFF`), it enters an infinite loop at `Infinite_Loop_at_EF4B6B` with no error message. If re-programming succeeds, boot continues normally.

## Security Implications

The lack of cryptographic verification means:

1. **Custom firmware installation is trivial** — Any disc with the correct 38-byte text signature will be accepted. The update data itself requires no special formatting beyond the standard SLIDE4K compression (for types 7/8) or raw binary layout.

2. **No rollback protection** — Older firmware versions can be installed over newer ones without restriction.

3. **Flash chip ID is the only hardware gate** — If the expected flash chip type is not present, the update is skipped. This prevents accidentally writing to incompatible memory but provides no security function.

4. **Physical access required** — The update requires a specific button held during boot with a floppy disc inserted, plus the firmware version sentinel set to 0xFF. This provides some protection against accidental triggering but not against intentional custom firmware installation.

For a detailed analysis of the floppy update attack surface, see [Floppy Security Analysis]({{ site.baseurl }}/floppy-security-analysis/).

## Code References

| Symbol | Address | Purpose |
|--------|---------|---------|
| `Get_Firmware_Version` | `0xFFFFE5` | Read version byte from 0xFFFFE8 |
| `Detect_Disk_Type` | `0xEF42FE` | 38-byte signature matching |
| `Flash_IdentifyAndValidateChip` | `0xEF379A` | Flash chip ID validation |
| `Flash_ProgramWord` | `0xEF3815` | AMD flash program (no read-back verify) |
| `Flash_WaitUntilReady` | `0xEF3AED` | Flash ready polling |
| `Erase_and_Burn____when_disk_is_valid` | `0xEF4745` | Type range validation + dispatch |
| `TableData_ROM_Verify` | `0xEF48AE` | Boot-time ROM erasure check |
| `HDAE5000_ROM_Transfer` | `0xEF48CF` | Verified ROM-to-ROM transfer |
| `SHOW_ILLEGAL_DISK_MESSAGE` | `0xEF482A` | Fatal error display + halt |
| `Detect_Region_Code` | `0xEF083E` | Hardware region detection |

## References

- [Firmware Update Display]({{ site.baseurl }}/firmware-update-display/) — LCD message state machine
- [System Update Discs]({{ site.baseurl }}/system-update-discs/) — Disc format and file contents
- [Flash Programming]({{ site.baseurl }}/flash-programming/) — Flash erase/program routines
- [Floppy Security Analysis]({{ site.baseurl }}/floppy-security-analysis/) — Attack surface analysis

---

*Last updated: March 2026*
