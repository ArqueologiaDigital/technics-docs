---
layout: page
title: Flash Programming
permalink: /flash-programming/
---

# Flash Programming Routines

## Overview

The KN5000 firmware contains two sets of flash programming routines for different target memories:

1. **Table Data Boot ROM** (`table_data/kn5000_table_data.s`) - First-stage bootloader
2. **Program ROM** (`v10/maincpu/boot/system_handlers.s`) - Main firmware

Both use the standard AMD/Atmel flash command sequences, each in a 16-bit form (single chips) and a 32-bit form (the interleaved pair).

## Memory Targets

| Target                              | Base Address | Bus Width | ROM  |
|-------------------------------------|--------------|-----------|------|
| HDAE5000 Expansion                  | 0x280000     | 16-bit    | Both |
| Custom Data Flash                   | 0x300000     | 16-bit    | Both |
| The `0x800000` window (32-bit pair) | 0x800000     | 32-bit    | Both |

No routine sends flash commands at `0xE00000`; which physical pair answers at `0x800000` depends on which updater is running (see [TMP94C241 Memory Controller]({{ site.baseurl }}/tmp94c241-memory-controller/)).

## AMD/Atmel Flash Protocol

### Standard 16-bit Commands

| Operation      | Address 1                                                                                                                               | Data 1 | Address 2   | Data 2 | Address 3   | Data 3 |
|----------------|-----------------------------------------------------------------------------------------------------------------------------------------|--------|-------------|--------|-------------|--------|
| Unlock         | base+0x5555                                                                                                                             | 0xAA   | base+0x2AAA | 0x55   | -           | -      |
| Software Reset | base+0x5555                                                                                                                             | 0xAA   | base+0x2AAA | 0x55   | base+0x5555 | 0xF0   |
| Read ID        | base+0x5555                                                                                                                             | 0xAA   | base+0x2AAA | 0x55   | base+0x5555 | 0x90   |
| Program Byte   | base+0x5555                                                                                                                             | 0xAA   | base+0x2AAA | 0x55   | base+0x5555 | 0xA0   |
| Chip Erase     | See [below](#chip-erase-sequence-6-bytes) and [Flash_ChipErase](#flash_chiperase-0xef387a-and-flash_erasesectorwithbankselect-0xef3929) |        |             |        |             |        |

### Chip Erase Sequence (6 bytes)
1. base+0x5555 = 0xAA
2. base+0x2AAA = 0x55
3. base+0x5555 = 0x80
4. base+0x5555 = 0xAA
5. base+0x2AAA = 0x55
6. base+0x5555 = 0x10

The addresses above are JEDEC word addresses. The KN5000 routines write them as byte offsets: `base+0xAAAA`/`base+0x5554` for a single ×16 chip and `0x815554`/`0x80AAA8` for the 32-bit pair (see [Address Translation](#address-translation-16-bit--32-bit)).

## Table Data Boot ROM Routines (16-bit)

These routines operate on HDAE5000 and Custom Data Flash using 16-bit bus access.

### Flash_Reset_16bit (0x9FB812)

**Purpose:** Send software reset command to flash chip

**Entry:**
- A = target (0=HDAE5000 at 0x280000, 1=Custom Data at 0x300000)

**Sequence:**
```
; Wait for P7 bit 5 (flash ready; SFR 0x1C)
; EI 6 - disable lower-priority interrupts
(base+0xAAAA) = 0xAA
(base+0x5554) = 0x55
(base+0xAAAA) = 0xF0    ; Software reset command
; Read any address to complete cycle
; EI 0 - re-enable interrupts
; If region code = 4, repeat for high bank (base+0x80000)
```

### Flash_ReadID_16bit (0x9FB888)

**Purpose:** Read flash manufacturer and device ID

**Entry:**
- A = target

**Exit:**
- HL = device ID (or 0xFFFF if not recognized)

**Validated Device IDs:**
- 0x2223 - AM29F400BT (4 Mbit, top boot block)
- 0x22AB - AM29F400BB (4 Mbit, bottom boot block)
- 0x22D6 - AM29F800BT (8 Mbit, top boot block)
- 0x2258 - AM29F800BB (8 Mbit, bottom boot block)

**Manufacturer IDs:**
- 0x01 - AMD/Spansion
- 0x04 - Fujitsu

### Flash_ProgramWord_16bit (0x9FB903)

**Purpose:** Program a word to flash memory

**Entry:**
- A = target
- XBC = destination address
- DE = data word

**Notes:**
- Skips programming if data = 0xFFFF (erased state)
- Handles high bank (0x380000+) for Custom Data when region code = 4

### Flash_ChipErase_16bit (0x9FB968)

**Purpose:** Erase entire flash chip

**Entry:**
- A = target

**Notes:**
- Uses 6-byte chip erase sequence
- For Custom Data with region code = 4, also erases high bank

## Table Data Boot ROM Routines (32-bit)

These routines operate on the interleaved Table Data ROM using 32-bit bus access.

### Address Translation (16-bit → 32-bit)

The Table Data ROM uses two interleaved 16-bit chips:
- Odd 16-bit words in IC1
- Even 16-bit words in IC3

The unlock addresses are the JEDEC word addresses `0x5555` and `0x2AAA` scaled by the bus width: ×2 (`0xAAAA`/`0x5554`) for a single ×16 device, and ×4 (`0x15554`/`0xAAA8`) for this 32-bit pair.

### Flash_Reset_32bit (0x9FBC2D)

**Purpose:** Reset Table Data ROM flash chips

**Sequence:**
```
(0x815554) = 0x00AA00AA
(0x80AAA8) = 0x00550055
(0x815554) = 0x00F000F0  ; Reset both chips simultaneously
```

### Flash_ReadID_32bit (0x9FBC6A)

**Purpose:** Read Table Data ROM flash IDs

**Exit:**
- XHL = device-ID pair (`0x22D622D6` or `0x22582258`) if valid, 0xFFFFFFFF otherwise

**Sequence:**
```
(0x815554) = 0x00AA00AA
(0x80AAA8) = 0x00550055
(0x815554) = 0x00900090  ; ID command to both chips
; Read ID from 0x800000 and 0x800004
```

### Flash_ProgramWord_32bit (0x9FBCD7)

**Purpose:** Program 32-bit word to Table Data ROM

**Entry:**
- XWA = destination address
- XBC = data (32 bits; a value of 0xFFFFFFFF is skipped)

### Flash_ChipErase_32bit (0x9FBD17)

**Purpose:** Erase Table Data ROM

## Program ROM Routines (32-bit)

Located in `v10/maincpu/boot/system_handlers.s`.

### TableDataFlash_ChipErase (0xEF3DBB)

**Purpose:** Erase Table Data ROM using 32-bit access -- the six-cycle CHIP ERASE command
(FLASH_CMD_UNLOCK1, _UNLOCK2, _ERASE_SETUP, _UNLOCK1, _UNLOCK2, _CHIP_ERASE). Formerly labelled
`HDAE5000_Flash_Verify`, a name that described it as an ID check.

**Sequence:** Same as Flash_ChipErase_32bit in boot ROM

### Flash_ChipErase (0xEF387A) and Flash_EraseSectorWithBankSelect (0xEF3929)

Traced in `v10/maincpu/boot/system_handlers.s` (the same routines are in v9 and v7;
kn5000-roms-disasm `notes/open4-kn5000-b/tools/README.md`, section 4).

The 16-bit flash chips (Custom Data Flash IC19 at 0x300000 when A = 1, otherwise the HD-AE5000
flash at 0x280000) are erased with the AMD/JEDEC sequence: `AA` to base+0xAAAA, `55` to
base+0x5554, `80` to base+0xAAAA, `AA`, `55`, then `10` to base+0xAAAA for a chip erase or `30` to
the sector address for a sector erase. The sector is `address & 0xFF0000`. Interrupts run at level 6
during the sequence (`ei 6`, back to `ei 0` after). On region-4 units (`Get_Region_Code` 0xEF0865
returns 4) IC19 is two chips: the chip erase goes to 0x300000 and again to 0x380000, and sectors
from 0x380000 use the second chip's command base (base + 0x80000).

The boot-block sub-sectors are added by more `30` writes right after the first, with no new
unlock, chosen by the device id that `Flash_InitAllBanks` (0xEF3B05) stores at start-up (RAM
0x205E0 for IC19, 0x205E2 for the HD-AE5000 chip):

| case                               | sector erased        | extra `30` writes                                                       | decided in                                        |
|------------------------------------|----------------------|-------------------------------------------------------------------------|---------------------------------------------------|
| IC19, id 0x2258 (bottom boot)      | 0x300000             | +0x4000, +0x6000, +0x8000                                               | `cpw (0x205e0), 8792`                             |
| IC19, other id (top boot)          | 0x3F0000             | +0xF8000, +0xFA000, +0xFC000; if XBC = 0x3FFFFF also +0xE0000           | `Flash_EraseSector_TopSector` (0xEF3A3E)          |
| IC19, region 4                     | 0x370000 or 0x3F0000 | chip base +0x78000, +0x7A000, +0x7C000; if XBC = 0x3FFFFF also +0x60000 | `Flash_EraseSector_BootBlock_HighBank` (0xEF39D6) |
| HD-AE5000, id 0x22AB (bottom boot) | 0x280000             | +0x4000, +0x6000, +0x8000                                               | `cpw (0x205e2), 8875`                             |
| HD-AE5000, other id (top boot)     | 0x2F0000             | +0x78000, +0x7A000, +0x7C000                                            | `Flash_EraseSector_Bank2Check` (0xEF3A82)         |

0x2258 and 0x22AB are the AMD device ids of the Am29F800B and Am29F400B bottom-boot parts (from the
datasheets; the part numbers on the boards were not checked). No caller passing XBC = 0x3FFFFF was
found: the type-7 handler passes 0x3E0000 and 0x3F0000.

**No verification and no timeout.** Neither routine reads anything back. Completion is the chips'
ready line, port 7 bit 5 (`Flash_CheckReady`, 0xEF3AE1); `Flash_WaitUntilReady` (0xEF3AED, chip
erase and wait), `Flash_EraseSectorAndWrite` (0xEF3BFC) and `FlashWrite` (0xEF3C3C) poll it with
no time limit. The type-7 updater (`HANDLE_UPDATE_FILE_TYPE_ID_007h`, 0xEF47FA) erases 0x3E0000 and
0x3F0000 back to back without waiting between them; how the chip treats the second unlock sequence
while the first erase is starting was not determined (**[inference]** from the datasheet: an AMD
part ignores or rejects commands other than `30` / `B0` inside the sector-erase window).

**Callers.** Chip erase: `Flash_WaitUntilReady`, for update types 5 (IC19) and 6 (HD-AE5000).
Sector erase: the type-7 handler, `Flash_EraseSectorAndWrite` (the splash-screen save,
`Flash_SaveSplashScreen`) and `FlashWrite` (custom-data saves from the file, tone-generator and
MIDI code).

### HDAE5000_Detect (0xEF3D0E)

**Purpose:** Read the flash IDs of the 32-bit pair at `0x800000` -- the program ROM's twin of `Flash_ReadID_32bit`. Despite its name it does not look for the HD-AE5000 board.

**Method:** 32-bit Read ID sequence at `0x815554`/`0x80AAA8`; accepts manufacturer `0x01` or `0x04` and device `0x22D6` or `0x2258` on both chips

**Exit:**
- XHL = the device-ID pair (`0x22D622D6` or `0x22582258`), or `0xFFFFFFFF` if not recognised

### FlashWrite (0xEF3C3C)

**Purpose:** High-level flash write with sector management

**Notes:** A 16-bit routine (IC19 or HD-AE5000): copies the sector into the RAM buffer at `0x69800`, erases it (`Flash_EraseSectorWithBankSelect`), merges the new data and programs the sector back (`Flash_WriteBufferToChip`). Nothing is read back to verify.

## Code Sharing Analysis

### Similarities

Both ROM sets implement:
- Same AMD/Atmel flash protocol
- Same chip ID validation
- Similar control flow and error handling

### Differences

| Aspect           | Table Data Boot                                         | Program ROM       |
|------------------|---------------------------------------------------------|-------------------|
| Bus width        | 16-bit and 32-bit                                       | 16-bit and 32-bit |
| Unlock addresses | 0xAAAA/0x5554 (16-bit), 0x15554/0xAAA8 (32-bit)         | the same          |
| Data values      | 0xAA/0x55 (16-bit), 0x00AA00AA/0x00550055 (32-bit)      | the same          |
| Target memories  | HDAE5000 0x280000, Custom 0x300000, the 0x800000 window | the same          |

### Feasibility of Shared Source

Creating shared source code is **possible** but complex:

1. **Requires conditional assembly** for:
   - Bus width (16-bit vs 32-bit data writes)
   - Address offset calculations
   - Target memory selection

2. **Macro-based approach:**
   ```asm
   IF BUS_WIDTH_32
       LD XWA, 00AA00AAh
       LD (BASE + 015554h), XWA
   ELSE
       LD WA, 00AAh
       LD (BASE + 0AAAAh), WA
   ENDIF
   ```

3. **Benefits:**
   - Single source of truth
   - Easier maintenance
   - Consistent bug fixes

4. **Drawbacks:**
   - Added complexity
   - Risk of introducing errors
   - Both ROMs are already byte-accurate

**Recommendation:** Keep separate implementations but document the relationship thoroughly. The cost of potential errors from merging outweighs the maintenance benefit for ROM disassembly.

## Boot ROM FDC Routines

The Table Data Boot ROM contains simplified FDC routines for firmware updates:

| Address  | Function                | Purpose                                                        |
|----------|-------------------------|----------------------------------------------------------------|
| 0x9FBF07 | `FDC_Reset`             | Initialize FDC controller for update mode                      |
| 0x9FBF37 | `FDC_ReadSector`        | Build a read request (LBA, sector count, buffer) at RAM 0x0C10 |
| 0x9FBF92 | `FDC_ReadSectorWrapper` | Issue that read; reset the FDC and retry on failure            |
| 0x9FBFC4 | `Boot_DetectDiskType`   | Check disk header signatures                                   |

### FDC_Reset (0x9FBF07)

Initializes the FDC controller:
- Allocates 16-byte stack frame
- Builds a 16-byte FDC parameter block on the stack (drive 0, data-rate code `0xD3`)
- Calls `FDC_Request` (`0x9FE944`, boot-time alias `0xFFE944`)

### FDC_ReadSector (0x9FBF37)

Builds a read request; it does not touch the FDC itself:
- Entry: XWA = first sector (linear, LBA), BC = sector count, XDE = destination buffer
- Converts the LBA to track, head and sector (18 sectors per track, two heads)
- Writes the request into the FDC parameter block at RAM 0x0C10

### FDC_ReadSectorWrapper (0x9FBF92)

Read with retry:
- Calls FDC_ReadSector, sets command 3 (read) in the block at 0x0C10 and passes it to `FDC_Request`
- On failure, calls FDC_Reset and retries, with no retry limit
- Returns HL = 0 on success

## Disk Type Detection

### Boot ROM Boot_DetectDiskType (0x9FBFC4)

Checks floppy disk header against 8 signature strings at Table Data ROM 0x9FA000:

| Type | ROM Offset | Signature                                | Purpose                                         |
|------|------------|------------------------------------------|-------------------------------------------------|
| 1    | 0x9FA000   | "Technics KN5000 Program  DATA FILE 1/2" | Program ROM disk 1                              |
| 2    | 0x9FA028   | "Technics KN5000 Program  DATA FILE 2/2" | Program ROM disk 2                              |
| 3    | 0x9FA078   | "Technics KN5000 Table    DATA FILE 1/2" | Table Data disk 1                               |
| 4    | 0x9FA0A0   | "Technics KN5000 Table    DATA FILE 2/2" | Table Data disk 2                               |
| 5    | 0x9FA0F0   | "Technics KN5000 CMPCUSTOMDATA FILE"     | Custom data (`CMPCUSTOMDATA`, written verbatim) |
| 6    | 0x9FA118   | "Technics KN5000 HD-AEPRG DATA FILE"     | HDAE5000 firmware                               |
| 7    | 0x9FA050   | "Technics KN5000 Program  DATA FILE PCK" | Compressed Program ROM                          |
| 8    | 0x9FA0C8   | "Technics KN5000 Table    DATA FILE PCK" | Compressed Table Data                           |

**Detection algorithm:**
1. Allocate 512-byte sector buffer
2. Read sector 33 (0x21), the first sector of the FAT data area
3. Compare sector data against each signature at ROM offsets (38 bytes each)
4. Return type code (1-8) on match, or 0xFF if unknown

### Program ROM Detect_Disk_Type (0xEF42FE)

Same logic, but against the program ROM's own copy of the strings at `0xE00038`–`0xE00150` (`FILETYPE_SIG_*`).

## Update Flow

1. **Boot-time check:** If PANEL MEMORY 1-4 are held at power-on, a floppy disk is present and the version byte at 0xFFFFE8 reads 0xFF, enter update mode
2. **Disk detection:** Read header and identify update type
3. **Validation:** Verify disk signature and flash hardware
4. **Erase:** Display "Now Erasing!!" and erase target flash: a chip erase of IC19 (type 5) or the HD-AE5000 chip (type 6), and for type 7 the two sector erases of 0x3E0000 and 0x3F0000 (see [Flash_ChipErase](#flash_chiperase-0xef387a-and-flash_erasesectorwithbankselect-0xef3929)); the `0x800000` pair is erased whole by `TableDataFlash_ChipErase`
5. **Program:** Read sectors from floppy and program flash
6. **Complete:** Display "Completed!" and "Turn On AGAIN!!"

## References

- AMD Flash Memory Programming Guide
- Atmel AT29 Series Datasheet
- `table_data/kn5000_table_data.s` - Boot code at 0x9FB7F2-0x9FC8C1
- `v10/maincpu/boot/system_handlers.s` - FlashWrite at 0xEF3C3C, HDAE5000_Detect at 0xEF3D0E
