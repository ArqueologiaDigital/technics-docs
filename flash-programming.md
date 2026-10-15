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

| Operation | Address 1 | Data 1 | Address 2 | Data 2 | Address 3 | Data 3 |
|-----------|-----------|--------|-----------|--------|-----------|--------|
| Unlock | base+0x5555 | 0xAA | base+0x2AAA | 0x55 | - | - |
| Software Reset | base+0x5555 | 0xAA | base+0x2AAA | 0x55 | base+0x5555 | 0xF0 |
| Read ID | base+0x5555 | 0xAA | base+0x2AAA | 0x55 | base+0x5555 | 0x90 |
| Program Byte | base+0x5555 | 0xAA | base+0x2AAA | 0x55 | base+0x5555 | 0xA0 |
| Chip Erase | See below | | | | | |

### Chip Erase Sequence (6 bytes)
1. base+0x5555 = 0xAA
2. base+0x2AAA = 0x55
3. base+0x5555 = 0x80
4. base+0x5555 = 0xAA
5. base+0x2AAA = 0x55
6. base+0x5555 = 0x10

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
- XIZ = device ID if valid, 0xFFFFFFFF otherwise

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
- XIZ = data (32 bits)

### Flash_ChipErase_32bit (0x9FBD17)

**Purpose:** Erase Table Data ROM

## Program ROM Routines (32-bit)

Located in `v10/maincpu/boot/system_handlers.s`.

### TableDataFlash_ChipErase (0xEF3DBB)

**Purpose:** Erase Table Data ROM using 32-bit access -- the six-cycle CHIP ERASE command
(FLASH_CMD_UNLOCK1, _UNLOCK2, _ERASE_SETUP, _UNLOCK1, _UNLOCK2, _CHIP_ERASE). Formerly labelled
`HDAE5000_Flash_Verify`, a name that described it as an ID check.

**Sequence:** Same as Flash_ChipErase_32bit in boot ROM

### HDAE5000_Detect (0xEF3D0E)

**Purpose:** Detect presence of HDAE5000 expansion board

**Method:** Probe Table Data ROM with flash ID command

**Exit:**
- XWA at (XSP+8) = 0 if detected, 0xFFFFFFFF if not present

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

| Address  | Function                | Purpose                                   |
|----------|-------------------------|-------------------------------------------|
| 0x9FBF07 | `FDC_Reset`             | Initialize FDC controller for update mode |
| 0x9FBF37 | `FDC_ReadSector`        | Read a single sector from floppy          |
| 0x9FBF92 | `FDC_ReadSectorWrapper` | Read multiple sectors with retry loop     |
| 0x9FBFC4 | `Boot_DetectDiskType`   | Check disk header signatures              |

### FDC_Reset (0x9FBF07)

Initializes the FDC controller:
- Allocates 16-byte stack frame
- Builds a 16-byte FDC parameter block on the stack (drive 0, data-rate code `0xD3`)
- Calls `FDC_Request` (`0x9FE944`, boot-time alias `0xFFE944`)

### FDC_ReadSector (0x9FBF37)

Reads a single sector:
- Entry: XWA = sector info, BC = sector number, XDE = destination buffer
- Calculates head/track from sector number
- Uses parameters at RAM 0x0C10

### FDC_ReadSectorWrapper (0x9FBF92)

Multi-sector read with retry:
- Calls FDC_ReadSector in a loop
- On failure, calls FDC_Reset and retries
- Returns success in HL

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
4. **Erase:** Display "Now Erasing!!" and erase target flash
5. **Program:** Read sectors from floppy and program flash
6. **Complete:** Display "Completed!" and "Turn On AGAIN!!"

## References

- AMD Flash Memory Programming Guide
- Atmel AT29 Series Datasheet
- `table_data/kn5000_table_data.s` - Boot code at 0x9FB7F2-0x9FC8C1
- `v10/maincpu/boot/system_handlers.s` - FlashWrite at 0xEF3C3C, HDAE5000_Detect at 0xEF3D0E
