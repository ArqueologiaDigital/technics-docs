---
layout: page
title: HDAE5000 MAME Setup Guide
permalink: /hdae5000-mame-setup/
---

# HD-AE5000 MAME Setup Guide

This guide explains how to set up and use the HD-AE5000 hard disk expansion board in MAME's KN5000 emulation.

> **See Also**: [HDAE5000 Overview]({{ site.baseurl }}/hdae5000/) for firmware analysis, [Disk Interface]({{ site.baseurl }}/hdae5000-disk-interface/) for the low-level ATA protocol, [Filesystem]({{ site.baseurl }}/hdae5000-filesystem/) for the on-disk format.

## Quick Start

### Running with HDAE5000 (no disk)

To boot the KN5000 with the HDAE5000 extension board but no hard disk attached:

```bash
mame kn5000 -ui_active -window -extension hdae5000
```

The firmware will display the HD-AE5000 splash screen ("Start-up! Please wait..."), poll for the drive, time out after a few seconds, and display **"Hard disk reset error"**. This is normal --- it means the firmware correctly detected that no drive is present. After dismissing the error, the keyboard boots normally with disk-related features disabled.

### Running with a Hard Disk Image

```bash
mame kn5000 -ui_active -window -extension hdae5000 -harddisk kn5000_disk.hd
```

`-harddisk` (short form `-hard`) attaches a raw disk image to the ATA slot on the HDAE5000.
`-harddisk1` / `-hard1` are registered aliases and work too; with only one hard-disk image
device in the machine, MAME's canonical, unnumbered names are the ones to prefer.

## Creating a Disk Image

### Blank Disk

The HDAE5000 firmware uses CHS (Cylinder/Head/Sector) addressing and a custom filesystem (its own 32-bit FAT and cluster chains, not a FAT12/16/32 volume). The geometry is read from the drive's ATA IDENTIFY DEVICE response, and `HDAE5000_HD_ParseIdentify` sizes the FAT and data area from the reported capacity (clusters of 0x20 sectors, or 0x40 on drives of at least 0x14DC93 sectors). An earlier version of this page gave a "firmware sector limit of 20,457 sectors". That number is a bound in the lyric-file parser (the 0x5000-byte lyric buffer), not a disk limit. See [HDAE5000 Filesystem]({{ site.baseurl }}/hdae5000-filesystem/#disk-layout).

Create a blank raw disk image:

```bash
# ~10 MB disk (within firmware's 20,457-sector addressable range)
dd if=/dev/zero of=kn5000_disk.hd bs=512 count=20480
```

MAME's ATA HLE device calculates CHS geometry from the file size automatically.

### Use raw images

| Format | Extension | Notes |
|--------|-----------|-------|
| Raw image | `.hd` | Plain sector dump, no header. What everything here is tested with. |
| Raw image | `.img` | Same format, different extension. Note `.img` is not in the image device's `file_extensions()` list, so MAME's file browser will not offer it — pass it on the command line. |
| CHD | `.chd` | **Untested through this path.** |

> ⚠ Earlier guidance here said CHD "returns header bytes, not sector data". That mechanism is
> not what MAME does: `harddisk_image_device::internal_load_hd()` sniffs the `MComprHD` magic and
> opens the file as a CHD, falling through to the raw path only when the magic is absent. Whatever
> was observed, it was not this. Use raw images because that is what is exercised, not because CHD
> is known broken.

If you have a CHD image, extract it first:

```bash
chdman extracthd -i disk.chd -o disk.hd
```

### Using an Existing FAT16 Image

If you have a disk image from the [App Loader]({{ site.baseurl }}/app-loader/) or other tools, copy it with the `.hd` extension:

```bash
cp your_disk.img kn5000_disk.hd
```

## Boot Sequence with HDAE5000

When the KN5000 boots with the HDAE5000 extension:

1. **Main firmware boot** --- Normal KN5000 initialization (SubCPU payload, NVRAM validation)
2. **Extension detection** --- Main CPU detects the HDAE5000 ROM at 0x280000
3. **HD-AE5000 splash screen** --- Displays "Start-up! Please wait..."
4. **ATA drive polling** --- Firmware polls status register at 0x13001E, checking for BSY=0 and DRDY=1
5. **Drive identification** --- If a drive responds, firmware issues IDENTIFY DEVICE (0xEC) to read CHS geometry
6. **Filesystem check** --- Reads the FSB (File System Block) and validates the custom filesystem
7. **Normal operation** --- Disk menu becomes available for file management

### What Happens Without a Disk

Without a disk image (or with an empty ATA slot), step 4 times out after ~4 million polling iterations. The firmware then displays:

```
!SYSTEM ERROR!
Hard disk reset error.
Please call your dealer or service center.
```

This is the expected behavior. After dismissing the error, the KN5000 boots normally --- disk-related menu items are simply unavailable.

### What Happens With a Blank Disk

With a blank (all-zeros) disk image, the drive responds to ATA commands but the filesystem is not initialized. The firmware will detect the drive but report an FSB error.

### Formatting the Hard Disk

The HD-AE5000 firmware has a built-in format function accessible from the disk menu (**HD FORMAT**). To use it:

1. **Write protection must be OFF** (the HD FORMAT icon is grayed out when write-protected)
2. The firmware prompts for a **6-digit safety code**: **0 5 0 3 5 4**
3. Enter the code using the **soft buttons along the LCD edges**, which act as a numeric keypad:

```
LEFT side:     RIGHT side:
 1  3  5  7  9
 0  2  4  6  8
```

![HD FORMAT instructions from the HD-AE5000 owner's manual]({{ site.baseurl }}/assets/images/hdae5000-hd-format-manual.png)

This runs `HDAE5000_HD_FormatDrive`, which calls `HDAE5000_HD_Format` between main-CPU callbacks. The layout a formatted disk carries is on [HDAE5000 Filesystem]({{ site.baseurl }}/hdae5000-filesystem/#disk-layout).

Alternatively, the original HD-TechManager5000 PC software could format the disk via the parallel port interface (command 0x17).

## ATA Interface Details

The HDAE5000 maps ATA registers directly to the main CPU address space:

| Address | ATA Register | Width |
|---------|-------------|-------|
| 0x130010 | Data | 16-bit |
| 0x130012 | Error / Features | 8-bit |
| 0x130014 | Sector Count | 8-bit |
| 0x130016 | Sector Number / LBA Low | 8-bit |
| 0x130018 | Cylinder Low / LBA Mid | 8-bit |
| 0x13001A | Cylinder High / LBA High | 8-bit |
| 0x13001C | Device/Head | 8-bit |
| 0x13001E | Status / Command | 8-bit |
| 0x130020+ | Alt Status / Device Control (CS1) | 8-bit |

The firmware uses **CHS addressing** exclusively and **PIO mode** for all data transfers (no DMA). The ATA INTRQ signal is routed through the extension slot connector to the main CPU's INT9.

## Troubleshooting

### Boot hangs at splash screen

If the emulator appears stuck on "Start-up! Please wait..." for more than 10 seconds, the ATA device is instantiated but not answering with DRDY.

**Mechanism**: MAME's ATA HLE device goes through a multi-millisecond reset/diagnostic sequence during which the status register returns BSY=1. The firmware's tight polling loop (4M iterations) becomes extremely slow when every read hits the ATA device subsystem.

**The slot is populated by default.** `hdae5000.cpp` configures
`ATA_INTERFACE(config, m_ata).options(ata_devices, "hdd", nullptr, false)`, so a drive exists
whether or not you pass an image. The alternative — defaulting the slot to empty and
instantiating a drive only when an image is given — exists on the older `kn5000_pr6_hdae5000`
branch (`options(ata_devices, nullptr, nullptr, false)`) and is **not** what the shipped
overlay build does.

### "Hard disk reset error" with a disk image attached

Verify:
1. The disk image is a **raw image** (not CHD)
2. The file extension is `.hd` or `.img`
3. The image is attached with `-harddisk` (or its `-hard` / `-hard1` aliases)
4. The image file is not zero bytes

### Drive detected but filesystem errors

A blank disk image will pass the ATA polling but fail filesystem validation. The firmware expects the signature longs `0xAA55AA55`, `0xF4F1F2F3` in filesystem sector 1; without them `HDAE5000_HD_Init` reports the disk as unformatted (step code 1). Creating a properly formatted disk requires either:
- The original HD-TechManager5000 PC software (via parallel port emulation --- not yet implemented)
- A disk image tool that creates the HDAE5000 filesystem format (not yet available)

## Current Emulation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Extension board detection | Working | ROM mapped at 0x280000-0x2FFFFF |
| Extension RAM | Working | 512KB at 0x200000-0x27FFFF |
| ATA register access | Working | CS0 (0x130010-0x13001F) and CS1 (0x130020-0x13002F) |
| ATA INTRQ routing | Working | Routed to main CPU INT9 via extension slot |
| Drive identification | Working | IDENTIFY DEVICE returns geometry from image size |
| Sector read/write | Working | PIO mode, 512-byte sectors |
| PPI parallel port | Stub | 8255 device instantiated but callbacks not wired |
| PC communication | Not implemented | Requires PPI callback wiring + PC-side emulation |
| Audio output | Not implemented | Extension board audio DAC not emulated |

## Related Pages

- [HDAE5000 Overview]({{ site.baseurl }}/hdae5000/) --- Firmware structure and initialization
- [HDAE5000 Disk Interface]({{ site.baseurl }}/hdae5000-disk-interface/) --- Low-level ATA protocol
- [HDAE5000 Filesystem]({{ site.baseurl }}/hdae5000-filesystem/) --- On-disk data structures
- [HDAE5000 Homebrew]({{ site.baseurl }}/hdae5000-homebrew/) --- Writing custom software
- [App Loader]({{ site.baseurl }}/app-loader/) --- Loading applications from disk
- [MAME Branch Review]({{ site.baseurl }}/mame-branch-review/) --- Development roadmap
