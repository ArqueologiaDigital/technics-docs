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
│  2MB (flash?)   │  │ 1MB Read/Write  │  │ 1.44MB          │  │  1.08GB      │
│  @ 0x800000     │  │ @ 0x300000      │  │ Removable       │  │  @ 0x130010  │
│                 │  │                 │  │ @ 0x110000      │  │              │
│  Factory:       │  │  User:          │  │                 │  │  Expansion:  │
│  ├─ Stylist     │  │  ├─ Custom      │  │  ├─ Songs       │  │  ├─ Songs    │
│  ├─ Sounds      │  │  │   styles     │  │  ├─ Styles      │  │  ├─ Styles   │
│  ├─ Demos       │  │  ├─ Sound banks │  │  ├─ Patches     │  │  ├─ Backups  │
│  └─ Presets     │  │  ├─ Wallpapers  │  │  └─ Sequences   │  │  └─ Quick    │
│                 │  │  └─ Sub-CPU     │  │                 │  │     Load     │
│                 │  │      payload    │  │                 │  │              │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └──────────────┘
```

## Table Data ROM

The Table Data ROM contains factory-installed content.

### Specifications

| Property     | Value                                                                                                                                                                     |
|--------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Size         | 2MB (2,097,152 bytes)                                                                                                                                                     |
| Address      | 0x800000-0x9FFFFF                                                                                                                                                         |
| Type         | Unresolved: mask ROM or flash (see [MAME Emulation Gaps]({{ site.baseurl }}/mame-emulation-gaps/)); the table update discs (types 3 and 8) program it with flash commands |
| Organization | 16-bit word-level interleave (odd IC1 + even IC3)                                                                                                                         |

### Physical Layout

| Chip | File | Description |
|------|------|-------------|
| IC1 | `kn5000_table_data_rom_odd.ic1` | Odd bytes |
| IC3 | `kn5000_table_data_rom_even.ic3` | Even bytes |

### Contents (Known)

| Type          | Description                                          |
|---------------|------------------------------------------------------|
| Tone database | Voice parameter records, key maps, drum kits         |
| Music Stylist | 1000 style-recommendation records                    |
| Panel Memory  | 80 factory Panel Memory presets and their bank names |
| HELP          | HELP index and SLIDE8K databases                     |
| Demo songs    | Feature-demo assets and demo presets                 |
| Graphics      | Fonts, wallpapers, icons, UI bitmaps                 |
| Bootloader    | The first-stage bootloader and its floppy driver     |

Auto-accompaniment patterns are not here: they are read from the Rhythm ROM at `0x400000`. See [Table Data ROM]({{ site.baseurl }}/table-data-rom/).

### Reconstruction Status

| Metric              | Value                                                          |
|---------------------|----------------------------------------------------------------|
| Rebuild             | Byte-identical from `table_data/` (one of the 13 gated images) |
| Census strict grade | 98.93 % (2026-10-06)                                           |
| Verbatim `.incbin`  | 318,468 B, the six FTBMP bitmaps                               |

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

| Type            | Description                                                                  |
|-----------------|------------------------------------------------------------------------------|
| Custom Styles   | Sections 0-6: user-created styles (`0x300000`)                               |
| Slot store      | Section 7: blocks kept from the SRAM work area (`0x3B0000`)                  |
| Wallpaper       | LCD wallpaper/screenshot storage (`0x3C0000`)                                |
| Sound banks     | Three user banks of sound-parameter settings (`0x3D3000`)                    |
| Sub-CPU payload | The compressed sub-CPU program, written by a type 7 update disc (`0x3E0000`) |

Panel Memory (registration) lives in battery-backed SRAM, not here, and user songs are held in RAM. See [Custom Data Flash]({{ site.baseurl }}/custom-data-flash/).

### Reconstruction Status

Rebuilt byte-identically from `custom_data/kn5000_custom_data.s` (one of the 13 gated images). The image is a dump of one unit's IC19, a flash the user rewrites (custom styles, sound-parameter banks, wallpapers), so another unit's contents may differ. See [Custom Data Flash]({{ site.baseurl }}/custom-data-flash/).

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

| Address  | Register          | Description                                                                                                                                     |
|----------|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| 0x110008 | MSR / aux command | Main status register (read); auxiliary command register (write): 36h reset, `0Bh` OR the rate bits for control internal mode, 4Fh select format |
| 0x11000A | Data              | uPD765-style commands, parameters and result bytes                                                                                              |
| 0x120000 | DMA acknowledge   | Data port for DMA channel 3 and the PIO fallback                                                                                                |

### File Formats

The KN5000 uses these file types on floppy:

| Extension | Type ID | Description                          |
|-----------|---------|--------------------------------------|
| .MID      | -       | Standard MIDI File                   |
| .SQT      | -       | Sequencer (firmware title SEQUENCER) |
| .STY      | -       | Style Data                           |
| .PMT      | -       | Panel Memory (PANEL MEMORY)          |
| .RCM      | -       | Rhythm Custom (RHYTHM CUSTOM)        |
| .TM       | -       | Sound Memory (SOUND MEMORY)          |

The titles in capitals are the firmware's own; see [the nine data types]({{ site.baseurl }}/hdae5000-resources/#the-nine-kn5000-data-types-named-by-the-firmware).

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

The HD-AE5000 uses a **custom filesystem**: no boot sector or BPB, but its own file allocation table of 32-bit entries linking cluster chains. Files are parts of songs in a fixed table of 120 directories × 16 songs, each song record holding the first cluster of each part (see [HDAE5000 Filesystem]({{ site.baseurl }}/hdae5000-filesystem/)).

See [HDAE5000]({{ site.baseurl }}/hdae5000/) and [HDAE5000 Disk Interface]({{ site.baseurl }}/hdae5000-disk-interface/) for details.

## System Update Procedure

The KN5000 can receive firmware updates via floppy disk. See [System Update Discs]({{ site.baseurl }}/system-update-discs/) for full format documentation.

### Update File Format

| Component | Header                                                                                             | Target Address | Size  |
|-----------|----------------------------------------------------------------------------------------------------|----------------|-------|
| Main ROM  | `Technics KN5000 Program  DATA FILE PCK` (type 7; two-disc sets use `... DATA FILE 1/2` and `2/2`) | 0xE00000       | 2MB   |
| HDAE5000  | `Technics KN5000 HD-AEPRG DATA FILE    `                                                           | 0x280000       | 512KB |

### Update Process

1. Insert the update disc
2. Hold all four PANEL MEMORY buttons and power on
3. The firmware matches the disc's 38-byte signature
4. The target flash is erased and programmed
5. "Completed!" and "Turn On AGAIN !!" appear; the unit stays there until it is powered off and on again

### No Code Execution from Floppy

None of the 8 update disc types makes the firmware **execute code loaded from floppy**: each of them writes to flash memory or is refused, and standard file I/O handles only data formats (MIDI, styles, registrations). The boot sector is never read, and there is no disc type signature for executable content. Custom code can only be installed via flash update (replacing the entire Program ROM or Extension ROM). The one exception is a hidden factory loader, not an update disc: on the "DEBUG SCREEN for HD-AE" page, LOAD reads `A:HKEXT.XAP` into the HD-AE5000's SRAM at `0x200000` (present only with the board fitted) and GO jumps to `0x200008`. See [System Update Discs]({{ site.baseurl }}/system-update-discs/#no-code-execution-from-floppy) for full analysis.

## Related Pages

- [System Overview]({{ site.baseurl }}/system-overview/) - Overall architecture
- [FDC Subsystem]({{ site.baseurl }}/fdc-subsystem/) - Floppy handler details
- [HDAE5000]({{ site.baseurl }}/hdae5000/) - Hard disk expansion
- [HDAE5000 Disk Interface]({{ site.baseurl }}/hdae5000-disk-interface/) - ATA protocol
- [Memory Map]({{ site.baseurl }}/memory-map/) - Address space

## Code References

### Floppy Disk Controller

| Symbol                         | Address    | Purpose                                       |
|--------------------------------|------------|-----------------------------------------------|
| `FDC_INIT`                     | `0xF96BBF` | FDC hardware initialization                   |
| `FDC_CONFIG_VERIFY`            | `0xF96BD0` | Controller and drive (re)initialization       |
| `FDC_CMD_EXEC`                 | `0xF976E4` | FDC command execution                         |
| `FDC_ReadSectors`              | `0xEF42CC` | Read sectors from floppy disc                 |
| `FDC_WriteSectors`             | `0xEF441B` | Write sectors to floppy disc                  |
| `Check_for_Floppy_Disk_Change` | `0xF98001` | Detect disc insertion/removal                 |
| `Detect_Disk_Type`             | `0xEF42FE` | Identify update disc type (38-byte signature) |

### Flash Memory

| Symbol                                 | Address    | Purpose                           |
|----------------------------------------|------------|-----------------------------------|
| `Flash_IdentifyAndValidateChip`        | `0xEF379A` | Probe flash chip (AMD/Fujitsu ID) |
| `Flash_ProgramWord`                    | `0xEF3815` | Program one word to flash         |
| `FLASH_MEM_UPDATE`                     | `0xEF4F6F` | Main firmware update entry point  |
| `Erase_and_Burn____when_disk_is_valid` | `0xEF4745` | Update type dispatcher            |

### HDAE5000 Storage

| Symbol | Address | Purpose |
|--------|---------|---------|
| `HDAE5000_ATA_IdentifyDevice` | `0x297884` | Read drive parameters (HDAE5000 ROM) |
| `HDAE5000_ATA_ReadSector` | `0x297788` | Read one sector (1-based, head-major CHS) |
| `HDAE5000_ATA_WriteSector` | `0x29769B` | Write one sector |
| `HDAE5000_HD_Init` | `0x2971B7` | Bring the drive up: SRAM test, IDENTIFY, signature, tables |
| `HDAE5000_HD_ReadTables` / `HDAE5000_HD_WriteTables` | `0x297BE9` / `0x297A8D` | The 323 filesystem-table sectors |
| `HDAE5000_HD_WriteFile` / `HDAE5000_HD_ReadFile` | `0x297E16` / `0x29811C` | A file as a FAT cluster chain |

## External References

- [NEC uPD72068 Datasheet](https://www.alldatasheet.com/) - FDC controller
- [ATA/ATAPI-4 Specification](http://www.t13.org/) - IDE interface standard
- [System Update Disks](https://archive.org/details/technics-kn5000-system-update-disks) - Firmware archive
