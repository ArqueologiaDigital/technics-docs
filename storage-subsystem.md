---
layout: page
title: Storage Subsystem
permalink: /storage-subsystem/
---

# Storage Subsystem

The KN5000 has multiple storage options for factory data, user data, and removable media.

## Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           STORAGE ARCHITECTURE                                │
└──────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐
│  TABLE DATA ROM │  │ CUSTOM DATA     │  │ FLOPPY DISK     │  │  HDAE5000    │
│                 │  │ FLASH           │  │                 │  │  (Optional)  │
│  2MB Read-Only  │  │ 1MB Read/Write  │  │ 1.44MB          │  │  1.08GB      │
│  @ 0x800000     │  │ @ 0x300000      │  │ Removable       │  │  @ 0x130010  │
│                 │  │                 │  │ @ 0x110000      │  │              │
│  Factory:       │  │  User:          │  │                 │  │  Expansion:  │
│  ├─ Styles      │  │  ├─ Settings    │  │  ├─ Songs       │  │  ├─ Songs    │
│  ├─ Sounds      │  │  ├─ Custom      │  │  ├─ Styles      │  │  ├─ Styles   │
│  ├─ Demos       │  │  │   Sounds     │  │  ├─ Patches     │  │  ├─ Backups  │
│  └─ Presets     │  │  └─ Sequences   │  │  └─ Sequences   │  │  └─ Quick    │
│                 │  │                 │  │                 │  │     Load     │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └──────────────┘
```

## Table Data ROM

The Table Data ROM contains factory-installed content.

### Specifications

| Property | Value |
|----------|-------|
| Size | 2MB (2,097,152 bytes) |
| Address | 0x800000-0x9FFFFF |
| Type | Read-only mask ROM |
| Organization | 16-bit word-level interleave (odd IC1 + even IC3) |

### Physical Layout

| Chip | File | Description |
|------|------|-------------|
| IC1 | `kn5000_table_data_rom_odd.ic1` | Odd bytes |
| IC3 | `kn5000_table_data_rom_even.ic3` | Even bytes |

### Contents (Known)

| Type | Description |
|------|-------------|
| Styles | Auto-accompaniment patterns |
| Sound Data | Voice parameters |
| Demo Songs | Factory demonstration sequences |
| Presets | Factory sound combinations |
| Graphics | UI images and icons |

### Reconstruction Status

| Metric | Value |
|--------|-------|
| Documented | 32.42% |
| Binary Assets | 67.58% remaining |
| Challenge | Complex data structures |

## Custom Data Flash

User-writable storage for personal settings and content.

### Specifications

| Property | Value |
|----------|-------|
| Size | 1MB (1,048,576 bytes) |
| Address | 0x300000-0x3FFFFF |
| Type | Flash memory |
| Access | Read/Write |

### Contents

| Type | Description |
|------|-------------|
| User Settings | System preferences |
| Custom Sounds | User-created voices |
| Custom Styles | User-created patterns |
| Registration | Sound/style combinations |
| Sequences | User compositions |

### Reconstruction Status

Not reconstructed - contains user data, varies per unit.

## Floppy Disk Controller

The FDC handles 3.5" floppy disk I/O for data exchange.

### Hardware

| Component | Value |
|-----------|-------|
| Controller | NEC uPD72068GF-3B9 |
| Address | 0x110000-0x11FFFF |
| Drive | Standard 3.5" 1.44MB |
| Format | MS-DOS compatible |

### FDC Registers

| Offset | Register | Description |
|--------|----------|-------------|
| 0x00 | Status A | Drive status |
| 0x02 | Status B | Controller status |
| 0x04 | DOR | Digital Output Register |
| 0x06 | TDR | Tape Drive Register |
| 0x08 | MSR | Main Status Register |
| 0x0A | DSR | Data Rate Select |
| 0x0C | Data FIFO | Data transfer |
| 0x0E | DIR | Digital Input Register |
| 0x10 | CCR | Configuration Control |

### File Formats

The KN5000 uses these file types on floppy:

| Extension | Type ID | Description |
|-----------|---------|-------------|
| .MID | - | Standard MIDI File |
| .SQT | - | Sequencer Track |
| .STY | - | Style Data |
| .PMT | - | Performance Memory Track |
| .RCM | - | Rhythm Composer Memory |
| .TM | - | Technical MIDI |

See [FDC Subsystem]({{ site.baseurl }}/fdc-subsystem/) for detailed handler documentation.

## HDAE5000 Hard Disk Expansion

Optional expansion providing 1.08GB storage.

### Hardware

| Component | Value |
|-----------|-------|
| Drive | 2.5" IDE HDD |
| Capacity | 1.08GB |
| Interface | ATA/IDE |
| ATA Address | 0x130010-0x130020 |
| PPI Address | 0x160000-0x160007 |
| ROM | 512KB @ 0x280000 |

### Features

| Feature | Description |
|---------|-------------|
| Quick Load | Fast file access |
| PC Link | Transfer via parallel port |
| Large Storage | 1000+ songs |
| Backup | System data backup |

### Addressing Mode

The HDAE5000 uses **CHS (Cylinder/Head/Sector)** addressing:

| Parameter | Source |
|-----------|--------|
| Cylinders | From IDENTIFY DEVICE |
| Heads | From IDENTIFY DEVICE |
| Sectors | From IDENTIFY DEVICE |

### File System

The HDAE5000 uses a **custom filesystem** (not FAT):

| Structure | Description |
|-----------|-------------|
| FSB | File System Block (master) |
| FGB | File Group Block |
| FEB | File Entry Block |

See [HDAE5000]({{ site.baseurl }}/hdae5000/) and [HDAE5000 Disk Interface]({{ site.baseurl }}/hdae5000-disk-interface/) for details.

## System Update Procedure

The KN5000 can receive firmware updates via floppy disk. See [System Update Discs]({{ site.baseurl }}/system-update-discs/) for full format documentation.

### Update File Format

| Component | Header | Target Address | Size |
|-----------|--------|----------------|------|
| Main ROM | "Technics KN5000 FLASH DATA FILE" | 0xE00000 | 2MB |
| HDAE5000 | "Technics KN5000 HD-AEPRG DATA FILE" | 0x280000 | 512KB |

### Update Process

1. Insert update disk
2. Power on with specific key held
3. Firmware detects update file
4. Flash programming begins
5. Verification and reboot

### No Code Execution from Floppy

The floppy subsystem is strictly a data transport. The firmware **never executes code loaded from floppy** — all 8 disc types write to flash memory, and standard file I/O handles only data formats (MIDI, styles, registrations). The boot sector is never read, and there is no disc type signature for executable content. Custom code can only be installed via flash update (replacing the entire Program ROM or Extension ROM). See [System Update Discs]({{ site.baseurl }}/system-update-discs/#no-code-execution-from-floppy) for full analysis.

## Related Pages

- [System Overview]({{ site.baseurl }}/system-overview/) - Overall architecture
- [FDC Subsystem]({{ site.baseurl }}/fdc-subsystem/) - Floppy handler details
- [HDAE5000]({{ site.baseurl }}/hdae5000/) - Hard disk expansion
- [HDAE5000 Disk Interface]({{ site.baseurl }}/hdae5000-disk-interface/) - ATA protocol
- [Memory Map]({{ site.baseurl }}/memory-map/) - Address space

## Code References

### Floppy Disk Controller

| Symbol | Address | Purpose |
|--------|---------|---------|
| `FDC_INIT` | `0xF96BBF` | FDC hardware initialization |
| `FDC_CONFIG_VERIFY` | `0xF96BD0` | FDC configuration verification |
| `FDC_CMD_EXEC` | `0xF976E4` | FDC command execution |
| `FDC_ReadSectors` | `0xF96E00` | Read sectors from floppy disc |
| `FDC_WriteSectors` | `0xF97000` | Write sectors to floppy disc |
| `Check_for_Floppy_Disk_Change` | `0xEF4F5E` | Detect disc insertion/removal |
| `Detect_Disk_Type` | `0xEF42FE` | Identify update disc type (38-byte signature) |

### Flash Memory

| Symbol | Address | Purpose |
|--------|---------|---------|
| `Flash_IdentifyAndValidateChip` | `0xEF37A5` | Probe flash chip (AMD/Fujitsu ID) |
| `Flash_ProgramWord` | `0xEF381A` | Program one word to flash |
| `FLASH_MEM_UPDATE` | `0xEF4F6F` | Main firmware update entry point |
| `Erase_and_Burn____when_disk_is_valid` | `0xEF4745` | Update type dispatcher |

### HDAE5000 Storage

| Symbol | Address | Purpose |
|--------|---------|---------|
| `HDAE5000_ATA_IdentifyDevice` | `0x297884` | Read drive parameters (HDAE5000 ROM) |
| `HDAE5000_ATA_ReadSector` | `0x297788` | Read one sector (1-based, head-major CHS) |
| `HDAE5000_ATA_WriteSector` | `0x29769B` | Write one sector |
| `HDAE5000_HD_Init` | `0x2971B7` | Bring the drive up: SRAM test, IDENTIFY, signature, tables |
| `HDAE5000_HD_ReadTables` / `HDAE5000_HD_WriteTables` | `0x297BE9` / `0x297A8D` | The 323 filesystem-table sectors |
| `HDAE5000_HD_WriteFile` / `HDAE5000_HD_ReadFile` | `0x297E16` / `0x29811C` | A file as a FAT cluster chain |

(The rows this table used to carry, `ATA_ReadSectors` at `0x28C100`, `FSB_Init` at `0x28D000`
and so on, matched no routine. See [HDAE5000 Filesystem]({{ site.baseurl }}/hdae5000-filesystem/).)

## External References

- [NEC uPD72068 Datasheet](https://www.alldatasheet.com/) - FDC controller
- [ATA/ATAPI-4 Specification](http://www.t13.org/) - IDE interface standard
- [System Update Disks](https://archive.org/details/technics-kn5000-system-update-disks) - Firmware archive
