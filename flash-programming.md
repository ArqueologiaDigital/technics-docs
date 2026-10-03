---
layout: page
title: Flash Programming
permalink: /flash-programming/
---

# Flash Programming Routines

## Overview

The KN5000 firmware contains two sets of flash programming routines for different target memories:

1. **Table Data Boot ROM** (`table_data/kn5000_table_data.asm`) - First-stage bootloader
2. **Program ROM** (`maincpu/kn5000_v10_program.asm`) - Main firmware

Both use the standard AMD/Atmel flash command sequences but with different bus widths and address offsets.

## Memory Targets

| Target | Base Address | Bus Width | ROM |
|--------|--------------|-----------|-----|
| HDAE5000 Expansion | 0x280000 | 16-bit | Table Data Boot |
| Custom Data Flash | 0x300000 | 16-bit | Table Data Boot |
| Table Data ROM | 0x800000 | 32-bit | Both |
| Program Flash | 0xE00000 | 32-bit | Program ROM |

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
- 0x2223 - AM29F040
- 0x22AB - AM29F400B
- 0x22D6 - AM29F800B
- 0x2258 - AM29LV800B

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
- Odd bytes in IC1
- Even bytes in IC3

This creates different address offsets:

| 16-bit Offset | 32-bit Offset | Notes |
|---------------|---------------|-------|
| 0x5555 | 0xAAAA | Unlock address 1 |
| 0x2AAA | 0x5554 | Unlock address 2 |

But for **command** addresses, the 32-bit values are:

| 16-bit Offset | 32-bit Offset | Notes |
|---------------|---------------|-------|
| 0x5555 | 0x15554 | Bit 16 set due to A16 routing |
| 0x2AAA | 0x0AAA8 | Different routing |

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

Located in `maincpu/kn5000_v10_program.asm`.

### HDAE5000_Flash_Verify (0xEF38F0)

**Purpose:** Erase Table Data ROM using 32-bit access

**Sequence:** Same as Flash_ChipErase_32bit in boot ROM

### HDAE5000_Detect (0xEF3CD1)

**Purpose:** Detect presence of HDAE5000 expansion board

**Method:** Probe Table Data ROM with flash ID command

**Exit:**
- XWA at (XSP+8) = 0 if detected, 0xFFFFFFFF if not present

### FlashWrite (0xEF3B6C)

**Purpose:** High-level flash write with sector management

**Notes:** Handles sector boundaries and verification

## Code Sharing Analysis

### Similarities

Both ROM sets implement:
- Same AMD/Atmel flash protocol
- Same chip ID validation
- Similar control flow and error handling

### Differences

| Aspect | Table Data Boot | Program ROM |
|--------|-----------------|-------------|
| Bus width | 16-bit AND 32-bit | 32-bit only |
| Unlock addresses | 0xAAAA/0x5554 (16-bit) | 0x15554/0xAAA8 (32-bit) |
| Data values | 0xAA/0x55 | 0x00AA00AA/0x00550055 |
| Target memories | HDAE, Custom, Table | Table, Program |

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

| Address | Function | Purpose |
|---------|----------|---------|
| 0x9FBF07 | `FDC_Reset` | Initialize FDC controller for update mode |
| 0x9FBF37 | `FDC_ReadSector` | Read a single sector from floppy |
| 0x9FBF92 | `FDC_MultiSectorRead` | Read multiple sectors with retry loop |
| 0x9FBFC4 | `Detect_Disk_Type` | Check disk header signatures |

### FDC_Reset (0x9FBF07)

Initializes the FDC controller:
- Allocates 16-byte stack frame
- Sets up FDC parameters at 0x0C10
- Calls FFE944 (FDC initialization)

### FDC_ReadSector (0x9FBF37)

Reads a single sector:
- Entry: XWA = sector info, BC = sector number, XDE = destination buffer
- Calculates head/track from sector number
- Uses parameters at RAM 0x0C10

### FDC_MultiSectorRead (0x9FBF92)

Multi-sector read with retry:
- Calls FDC_ReadSector in a loop
- On failure, calls FDC_Reset and retries
- Returns success in HL

## Disk Type Detection

### Boot ROM Detect_Disk_Type (0x9FBFC4)

Checks floppy disk header against 8 signature strings at Table Data ROM 0x9FA000:

| Type | ROM Offset | Signature | Purpose |
|------|------------|-----------|---------|
| 1 | 0x9FA000 | "Technics KN5000 Program  DATA FILE 1/2" | Program ROM disk 1 |
| 2 | 0x9FA028 | "Technics KN5000 Program  DATA FILE 2/2" | Program ROM disk 2 |
| 3 | 0x9FA078 | "Technics KN5000 Table    DATA FILE 1/2" | Table Data disk 1 |
| 4 | 0x9FA0A0 | "Technics KN5000 Table    DATA FILE 2/2" | Table Data disk 2 |
| 5 | 0x9FA0F0 | "Technics KN5000 CMPCUSTOMDATA FILE" | Compressed custom data |
| 6 | 0x9FA118 | "Technics KN5000 HD-AEPRG DATA FILE" | HDAE5000 firmware |
| 7 | 0x9FA050 | "Technics KN5000 Program  DATA FILE PCK" | Compressed Program ROM |
| 8 | 0x9FA0C8 | "Technics KN5000 Table    DATA FILE PCK" | Compressed Table Data |

**Detection algorithm:**
1. Allocate 512-byte sector buffer
2. Read first sector from floppy
3. Compare sector data against each signature at ROM offsets (38 bytes each)
4. Return type code (1-8) on match, or 0xFF if unknown

### Program ROM Detect_Disk_Type (0xEF42FE)

Uses the same signature table and similar logic.

## Update Flow

1. **Boot-time check:** If firmware version = 0xFF and floppy disk present, enter update mode
2. **Disk detection:** Read header and identify update type
3. **Validation:** Verify disk signature and flash hardware
4. **Erase:** Display "Now Erasing!!" and erase target flash
5. **Program:** Read sectors from floppy and program flash
6. **Verify:** Check programmed data matches source
7. **Complete:** Display "Completed!" and "Turn On AGAIN!!"

## References

- AMD Flash Memory Programming Guide
- Atmel AT29 Series Datasheet
- `table_data/kn5000_table_data.asm` - Boot code at 0x9FB7F2-0x9FC8C1
- `maincpu/kn5000_v10_program.asm` - FlashWrite at 0xEF3B6C, HDAE5000_Detect at 0xEF3CD1
