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

The firmware version byte at ROM address `0xFFFFE8` must equal `0xFF` to enter update mode. The byte is part of the ROM image (`FW_VERSION_BYTE`, `0x0A` in v10, `boot/rom_end_structure.s`), and no routine writes it. In the table-data boot ROM the same boot-time address holds `0xFF`, which is why the code after the check is labelled `We_seem_to_be_running_boot_ROM_code`. How the check is met on a stock unit is open: see [MAME Emulation Gaps]({{ site.baseurl }}/mame-emulation-gaps/).

**Code:** `Get_Firmware_Version` (`0xFFFEE5`), compared to `0xFF` in `Boot_RunSelfTest` and again in `BootInit_SeqAndPanel`.

### 2. Floppy Disc Presence

`Check_for_Floppy_Disk_Change` reads the disc-change signal on Port D bit 6. If no disc is present, the update is skipped and normal boot continues.

### 3. Button Held During Boot

The control panel scan (`CPanel_ScanButtons`) must return value 4, indicating a specific button combination is held during boot. Without this, the update is skipped even if the sentinel and disc are present.

**Code:** `cp (1026:16), 4` at `0xEF05DB` (in `BootInit_SeqAndPanel`).

### 4. Disc Type Signature Match

`Detect_Disk_Type` (`0xEF42FE`) reads sector 33 (offset 0x4200) from the floppy — the first file in the FAT data area — and compares the first **38 bytes** (0x26) against the program ROM's own copy of the 8 signature strings (`FILETYPE_SIG_PROGRAM_1` … `FILETYPE_SIG_HDAE_PRG`, `0xE00038`–`0xE00150`); the bootloader's `Boot_DetectDiskType` (`0x9FBFC4`) uses the table-data copy at `0x9FA000`.

**Algorithm:**
1. Allocate 512-byte buffer via `Malloc`
2. Read 1 sector starting at sector 0x21 (33) via `FDC_ReadSectors`
3. For each of 8 signatures: call `String_Compare` (`0xFF0CC1`) with length 0x26 (38 bytes)
4. On match: store type code (1-8) and return
5. No match: return `0xFF` (unknown disc)

The eight signature strings, at their addresses in each ROM:

| Table Data ROM | Program ROM | Program ROM symbol         | Type | Signature                                |
|----------------|-------------|----------------------------|------|------------------------------------------|
| `0x9FA000`     | `0xE00038`  | `FILETYPE_SIG_PROGRAM_1`   | 1    | `Technics KN5000 Program  DATA FILE 1/2` |
| `0x9FA028`     | `0xE00060`  | `FILETYPE_SIG_PROGRAM_2`   | 2    | `Technics KN5000 Program  DATA FILE 2/2` |
| `0x9FA050`     | `0xE00088`  | `FILETYPE_SIG_PROGRAM_PCK` | 7    | `Technics KN5000 Program  DATA FILE PCK` |
| `0x9FA078`     | `0xE000B0`  | `FILETYPE_SIG_TABLE_1`     | 3    | `Technics KN5000 Table    DATA FILE 1/2` |
| `0x9FA0A0`     | `0xE000D8`  | `FILETYPE_SIG_TABLE_2`     | 4    | `Technics KN5000 Table    DATA FILE 2/2` |
| `0x9FA0C8`     | `0xE00100`  | `FILETYPE_SIG_TABLE_PCK`   | 8    | `Technics KN5000 Table    DATA FILE PCK` |
| `0x9FA0F0`     | `0xE00128`  | `FILETYPE_SIG_CMPCUSTOM`   | 5    | `Technics KN5000 CMPCUSTOMDATA FILE    ` |
| `0x9FA118`     | `0xE00150`  | `FILETYPE_SIG_HDAE_PRG`    | 6    | `Technics KN5000 HD-AEPRG DATA FILE    ` |

`Detect_Disk_Type` passes each string's full address to `String_Compare` as two 16-bit pushes (`FILETYPE_SIG_*@hi16`, the high word `0x00E0`, then `@lo16`); there is no base-relative indirection.

### 5. Flash Chip Identification

`Flash_IdentifyAndValidateChip` (`0xEF379A`) probes the target flash memory using the standard AMD/Atmel flash Read ID command sequence:

1. Write `0xAA` to base+0xAAAA
2. Write `0x55` to base+0x5554
3. Write `0x90` to base+0xAAAA (Read ID command)
4. Read manufacturer ID and device ID

**Accepted manufacturer IDs:** `0x01` (AMD/Spansion), `0x04` (Fujitsu)

**Accepted device IDs:**

| ID       | Device                         | Capacity |
|----------|--------------------------------|----------|
| `0x2223` | AM29F400BT (top boot block)    | 512 KB   |
| `0x22AB` | AM29F400BB (bottom boot block) | 512 KB   |
| `0x22D6` | AM29F800BT (top boot block)    | 1 MB     |
| `0x2258` | AM29F800BB (bottom boot block) | 1 MB     |

If the flash chip is not recognized, the function returns `0xFFFF` and the update for that target is skipped.

**Target flash chips:**
- A=1 → Custom Data Flash at `0x300000`
- any other value → HDAE5000 Extension ROM at `0x280000` (the update path passes A=2)

The table-data pair at `0x800000` is probed separately by `HDAE5000_Detect` (`0xEF3D0E`), a 32-bit routine that accepts only device ID `0x22D6` or `0x2258` on both chips.

### 6. Type Range Validation

`Erase_and_Burn____when_disk_is_valid` (`0xEF4745`) validates the disc type code is in range 1-8 (after subtracting 1, checking 0-7). Out-of-range values trigger the "Illegal Disk!" fatal error.

### 7. Region Code Check

`FLASH_MEM_UPDATE` reads the region code (`Get_Region_Code`; derived from hardware port H bits 1-2) right after detecting the disc type. On a Region 4 unit it jumps straight to the HD-AE5000 branch (`Flash_CheckAndValidate`), so program, table and custom-data discs are ignored and only a type-6 disc is acted on. The normal boot path makes a separate region test: `Boot_FlashAndExtensions` calls `HDAE5000_Parport_Setup` (`0xEF4BCC`) only when Port E bit 0 reads low and the region code is not 4.

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

Some verification routines exist, but they belong to the HD-AE5000 programming path, not to the floppy update process:

### TableData_ROM_Verify (0xEF48AE)

Scans the Table Data ROM (`0x800000`-`0xA00000`) in 64-byte blocks, checking if the first word of each block is `0xFFFFFFFF` (erased). Returns immediately (non-zero) if any non-erased block is found. Returns 0 if the entire ROM is erased.

Its callers are `HDAE5000_Init_DetectAndVerify` (`0xEF4B54`) and `HDAE5000_Init_BytecodeBlock` (`0xEF49F7`, which has no direct caller in the source), both HD-AE5000 programming code. `HDAE5000_Init_DetectAndVerify` is entered from the bootloader's handoff stub at `0xFFFED8`, and from the program ROM's own boot when Port E bit 0 reads low and the region code is not 4: `HDAE5000_Parport_Setup` then never returns, but waits for bit 0 of the PPI's port C (`0x160002`) to clear and jumps there. If the table-data flash is not blank it is chip-erased first; it is then reprogrammed from the HD-AE5000 window at `0x280000`. It does not verify a floppy update.

### HDAE5000_VerifyFlashAgainstWindow (0xEF48CF)

This routine was named `HDAE5000_ROM_Transfer` and described as a transfer. It writes nothing: it compares a
flash with a 512 KB window, bank by bank. Each bank number is written to the port at `0x160000`, and the routine
compares `0x40000` words. It returns `XHL = 0` when everything matches, and otherwise the flash address just
after the first mismatch.

`HDAE5000_TableData_Write` (`0xEF49A5`) uses it as the read-back check of its own programming. It runs:

1. `HDAE5000_ProgramTableDataFlash` (`0xEF4953`): programs the 2 MB table-data flash at `0x800000` from the window
   at `0x280000`, banks 0-3.
2. `HDAE5000_ProgramCustomDataFlash` (`0xEF4901`): programs the custom-data flash at `0x300000` from the window
   at `0x200000`, banks 0-1.
3. This routine, on each of the two flashes. On a mismatch the firmware halts in `LED_BlinkBit2Forever` or
   `LED_BlinkBit3Forever`.

That path runs from the HD-AE5000 side at boot, not during the floppy update process.

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

**Trigger:** entry to `HDAE5000_Init_DetectAndVerify`, either from the bootloader's handoff stub at `0xFFFED8` or from `HDAE5000_Parport_Setup` during boot when Port E bit 0 reads low and the region code is not 4 (that routine waits for bit 0 of `0x160002` to clear, then jumps here). It does not depend on the table data being erased.

**Behavior:** `HDAE5000_Init_DetectAndVerify` (`0xEF4B54`) first probes the table-data flash pair with `HDAE5000_Detect` (`0xEF3D0E`). If that returns `0xFFFFFFFF`, it sets bit 2 of `0x160004` and loops forever at `Infinite_Loop_FlashVerifyFail`, with no error message. Otherwise, if `TableData_ROM_Verify` finds the flash not blank, it is chip-erased; `HDAE5000_TableData_Write` then reprograms it from the HD-AE5000 window at `0x280000`, `HDAE5000_VerifyFlashAgainstWindow` compares the result (halting in `LED_BlinkBit2Forever` on a mismatch), and the routine halts in `HDAE5000_Init_HaltLoop`. Boot never continues.

## Security Implications

The lack of cryptographic verification means:

1. **Custom firmware installation is trivial** — Any disc with the correct 38-byte text signature will be accepted. The update data itself requires no special formatting beyond the standard SLIDE4K compression (for types 7/8) or raw binary layout.

2. **No rollback protection** — Older firmware versions can be installed over newer ones without restriction.

3. **Flash chip ID is the only hardware gate** — If the expected flash chip type is not present, the update is skipped. This prevents accidentally writing to incompatible memory but provides no security function.

4. **Physical access required** — The update requires a specific button held during boot with a floppy disc inserted, plus the firmware version sentinel set to 0xFF. This provides some protection against accidental triggering but not against intentional custom firmware installation.

For a detailed analysis of the floppy update attack surface, see [Floppy Security Analysis]({{ site.baseurl }}/floppy-security-analysis/).

## Code References

| Symbol                                 | Address    | Purpose                                                        |
|----------------------------------------|------------|----------------------------------------------------------------|
| `Get_Firmware_Version`                 | `0xFFFEE5` | Read version byte from 0xFFFFE8                                |
| `Detect_Disk_Type`                     | `0xEF42FE` | 38-byte signature matching                                     |
| `Flash_IdentifyAndValidateChip`        | `0xEF379A` | Flash chip ID validation                                       |
| `Flash_ProgramWord`                    | `0xEF3815` | AMD flash program (no read-back verify)                        |
| `Flash_WaitUntilReady`                 | `0xEF3AED` | Chip erase (`Flash_ChipErase`), then poll until ready          |
| `Erase_and_Burn____when_disk_is_valid` | `0xEF4745` | Type range validation + dispatch                               |
| `TableData_ROM_Verify`                 | `0xEF48AE` | Boot-time ROM erasure check                                    |
| `HDAE5000_VerifyFlashAgainstWindow`    | `0xEF48CF` | Read-back compare of a programmed flash with its banked window |
| `SHOW_ILLEGAL_DISK_MESSAGE`            | `0xEF482A` | Fatal error display + halt                                     |
| `Detect_Region_Code`                   | `0xEF083E` | Hardware region detection                                      |

## References

- [Firmware Update Display]({{ site.baseurl }}/firmware-update-display/) — LCD message state machine
- [System Update Discs]({{ site.baseurl }}/system-update-discs/) — Disc format and file contents
- [Flash Programming]({{ site.baseurl }}/flash-programming/) — Flash erase/program routines
- [Floppy Security Analysis]({{ site.baseurl }}/floppy-security-analysis/) — Attack surface analysis

---

*Last updated: October 2026*
