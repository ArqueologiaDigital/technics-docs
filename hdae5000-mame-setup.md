---
layout: page
title: HDAE5000 MAME Setup Guide
permalink: /hdae5000-mame-setup/
---

# HD-AE5000 MAME Setup Guide

This guide explains how to set up and use the HD-AE5000 hard disk expansion board in MAME's KN5000 emulation.

> **Build.** Everything on this page needs the kn7000_mame overlay build of MAME, which carries the unmerged patch `kn5000-19-hdae5000-ata-intrq`. In upstream MAME (the `hdae5000` device from mamedev/mame#14068) the ATA registers are stubs that read 0 and ignore writes, so the extension ROM boots but no drive ever becomes ready.

> **See Also**: [HDAE5000 Overview]({{ site.baseurl }}/hdae5000/) for firmware analysis, [Disk Interface]({{ site.baseurl }}/hdae5000-disk-interface/) for the low-level ATA protocol, [Filesystem]({{ site.baseurl }}/hdae5000-filesystem/) for the on-disk format.

## Quick Start

### Running with HDAE5000 (no disk)

To boot the KN5000 with the HDAE5000 extension board but no hard disk attached:

```bash
mame kn5000 -ui_active -window -extension hdae5000
```

In the overlay build a drive is fitted to the ATA slot by default (see [Boot hangs at splash screen](#boot-hangs-at-splash-screen)), so "no disk" means a drive with no image, and what the firmware then does has not been recorded. A MAME drive without an image still reports DRDY but answers IDENTIFY DEVICE with an error and no DRQ, and `HDAE5000_ATA_IdentifyDevice` waits for DRQ without a timeout, so expect the splash screen to stay up. The **"Hard disk reset error"** described [below](#what-happens-without-a-disk) (the soft reset times out, step code 3) was seen on the fork branch `kn5000_pr6_hdae5000`, whose ATA slot is empty by default.

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
# ~10 MB raw disk (20,480 sectors; the fixed FAT and table area ends at sector 4230)
dd if=/dev/zero of=kn5000_disk.hd bs=512 count=20480
```

MAME guesses a CHS geometry from the file size (`hard_disk_file` in `src/lib/util/harddisk.cpp`), and the drive reports it in IDENTIFY DEVICE words 54-58, which is what `HDAE5000_HD_ParseIdentify` reads.

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

These images are for the [App Loader]({{ site.baseurl }}/app-loader/) ROM, which replaces the HD-AE5000 firmware; the HD-AE5000 firmware itself does not read FAT16 and reports such a disk as not formatted.

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

With an empty ATA slot (the default on the fork branch `kn5000_pr6_hdae5000`, not in the overlay build), step 4 times out after ~4 million polling iterations. The firmware then displays:

```
!SYSTEM ERROR!
Hard disk reset error.
Please call your dealer or service center.
```

This is the expected behavior. After dismissing the error, the KN5000 boots normally --- disk-related menu items are simply unavailable.

### What Happens With a Blank Disk

With a blank (all-zeros) disk image, the drive responds to ATA commands but the filesystem is not initialized. The firmware will detect the drive but report it as not formatted ("The hard disk is not formatted!"): sector 1 lacks the signature (`HDAE5000_HD_Init` step code 1).

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

Alternatively, the original HD-TechManager5000 PC software could format the disk via the parallel port interface (command 17, sent as byte 0x11).

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

The firmware uses **CHS addressing** exclusively and **PIO mode** for all data transfers (no DMA). The ATA INTRQ line is wired through the extension connector (CN6 pin 58) to the main CPU's INT9, but the firmware never uses it: it sets nIEN in Device Control (0x0A), leaves `INTE89` at 0 and polls the status register.

## Troubleshooting

### Boot hangs at splash screen

If the emulator appears stuck on "Start-up! Please wait..." for more than 10 seconds, check that an image is mounted. The overlay build always fits a drive (below). A MAME drive without an image still reports DRDY, but it answers IDENTIFY DEVICE with an error and no DRQ, and `HDAE5000_ATA_IdentifyDevice` waits for DRQ with no timeout. The drive's own reset holds BSY for only a few milliseconds of emulated time (`DETECT_DEVICE1_TIME` and `DIAGNOSTIC_TIME` in MAME's `src/devices/machine/atahle.cpp`), so the drive-ready poll cannot by itself cause a long hang. No run of the overlay build without an image has been recorded.

**The slot is populated by default.** `hdae5000.cpp` configures
`ATA_INTERFACE(config, m_ata).options(ata_devices, "hdd", nullptr, false)`, so a drive exists
whether or not you pass an image. The alternative — defaulting the slot to empty and
instantiating a drive only when an image is given — exists on the older `kn5000_pr6_hdae5000`
branch (`options(ata_devices, nullptr, nullptr, false)`) and is **not** what the shipped
overlay build does.

### "Hard disk reset error" with a disk image attached

Verify:
1. The disk image is a **raw image** (CHD through this path is untested)
2. The file extension is `.hd` or `.img`
3. The image is attached with `-harddisk` (or its `-hard` / `-hard1` aliases)
4. The image file is not zero bytes

### Drive detected but filesystem errors

A blank disk image will pass the ATA polling but fail filesystem validation. The firmware expects the signature longs `0xAA55AA55`, `0xF4F1F2F3` in filesystem sector 1; without them `HDAE5000_HD_Init` reports the disk as unformatted (step code 1). Creating a properly formatted disk requires either:
- The firmware's own HD FORMAT ([above](#formatting-the-hard-disk)); whether it completes under emulation has not been recorded
- The original HD-TechManager5000 PC software (a PC-link prototype exists only on the fork branch `kn5000_research_techmanager`, not validated with the real software)
- A disk image tool that creates the HDAE5000 filesystem format (not yet available)

## Current Emulation Status (overlay build)

| Feature                   | Status          | Notes                                                                                                    |
|---------------------------|-----------------|----------------------------------------------------------------------------------------------------------|
| Extension board detection | Working         | ROM mapped at 0x280000-0x2FFFFF                                                                          |
| Extension RAM             | Working         | 512KB at 0x200000-0x27FFFF                                                                               |
| ATA register access       | Working         | CS0 (0x130010-0x13001F) and CS1 (0x130020-0x13002F)                                                      |
| ATA INTRQ routing         | Wired, unused   | Routed to main CPU INT9 via the extension slot; the firmware keeps nIEN set and INT9 disabled, and polls |
| Drive identification      | Working         | IDENTIFY DEVICE returns geometry from image size                                                         |
| Sector read/write         | Working         | PIO mode, 512-byte sectors                                                                               |
| PPI parallel port         | Stub            | 8255 device instantiated but callbacks not wired                                                         |
| PC communication          | Not implemented | Requires PPI callback wiring + PC-side emulation                                                         |
| Audio output              | Not implemented | Extension board audio DAC not emulated                                                                   |

## Related Pages

- [HDAE5000 Overview]({{ site.baseurl }}/hdae5000/) --- Firmware structure and initialization
- [HDAE5000 Disk Interface]({{ site.baseurl }}/hdae5000-disk-interface/) --- Low-level ATA protocol
- [HDAE5000 Filesystem]({{ site.baseurl }}/hdae5000-filesystem/) --- On-disk data structures
- [HDAE5000 Homebrew]({{ site.baseurl }}/hdae5000-homebrew/) --- Writing custom software
- [App Loader]({{ site.baseurl }}/app-loader/) --- Loading applications from disk
- [MAME Branch Review]({{ site.baseurl }}/mame-branch-review/) --- Development roadmap
