---
layout: page
title: HDAE5000 Hard Disk Interface
permalink: /hdae5000-disk-interface/
---

# HD-AE5000 Hard Disk Interface

This page documents the low-level hard disk interface used by the HD-AE5000 expansion for the Technics KN5000 keyboard. Understanding this interface is essential for MAME emulation and homebrew development.

## Overview

The HD-AE5000 uses an **IDE/ATA compatible hard disk drive** with **direct memory-mapped registers**. The ATA registers are accessible at addresses 0x130010-0x130020 from the main CPU.

A separate **Intel 8255 PPI** at 0x160000 provides a parallel port interface for communication with a PC running the HD-TechManager5000 software.

```
┌──────────────────┐                           ┌──────────────────┐
│   TMP94C241F     │  Direct Memory Access     │   IDE Hard Disk  │
│   Main CPU       │<─────────────────────────>│   @ 0x130010     │
│                  │                           │   (ATA Registers)│
│                  │                           └──────────────────┘
│                  │
│                  │     ┌─────────────────┐
│                  │<───>│   Intel 8255    │<───> PC Parallel Port
└──────────────────┘     │   PPI @ 0x160000│
                         └─────────────────┘
```

## IDE/ATA Background

### What is IDE/ATA?

**IDE (Integrated Drive Electronics)** and **ATA (AT Attachment)** are standards for connecting hard disk drives to computers. The HD-AE5000 uses a 2.5" laptop-style IDE drive with 1.08GB capacity, which was a substantial amount for 1996-era consumer electronics.

### ATA Register Set (Firmware-Verified)

The HD-AE5000 maps ATA registers directly to memory addresses. The register layout was verified by analyzing firmware code at 0x2974DD-0x297501 and 0x2976AB-0x297883:

| Address | Register | Read | Write |
|---------|----------|------|-------|
| 0x130010 | Data (16-bit) | Sector data | Sector data |
| 0x130012 | Error/Features | Error code | Features |
| 0x130014 | Sector Count | Sector count | Sector count |
| 0x130016 | Sector Number | Sector/LBA Low | Sector/LBA Low |
| 0x130018 | Cylinder Low | Cylinder Low/LBA Mid | Cylinder Low/LBA Mid |
| 0x13001A | Cylinder High | Cylinder High/LBA High | Cylinder High/LBA High |
| 0x13001C | Device/Head | Device/Head | Device/Head (0xA0 \| head) |
| 0x13001E | Status/Command | Status | Command |
| 0x130020 | Device Control | - | Device Control |

The HD-AE5000 firmware uses **CHS (Cylinder/Head/Sector)** addressing, as evidenced by debug strings in the ROM:
- `hddtrck` - Track (cylinder) count
- `hddhead` - Head count
- `hddsctr` - Sectors per track
- `hddscby` - Bytes per sector (typically 512)

### ATA Commands Used by Firmware

The following commands were identified by analyzing firmware writes to the Command Register (0x13001E):

| Command | Hex | Address | Description |
|---------|-----|---------|-------------|
| Read Sectors | 0x20 | 0x29781D | Read one or more sectors (PIO mode) |
| Write Sectors | 0x30 | 0x29772B | Write one or more sectors (PIO mode) |
| Standby | 0x94 | 0x297501 | Spin down drive with timeout parameter |
| Identify Device | 0xEC | 0x2978C3 | Return 512-byte device identification block |

## PPI Parallel Port Interface

### Purpose

The Intel 8255 PPI at 0x160000 is **NOT** used for IDE communication - the IDE registers are directly memory-mapped. Instead, the PPI provides a **parallel port interface for PC communication** with the HD-TechManager5000 Windows software.

This allows file transfer between a PC and the HDAE5000's hard disk via the PC's parallel port.

### PPI Port Assignments

| Address | Port | Direction | Function |
|---------|------|-----------|----------|
| 0x160000 | Port A | Bidirectional | Data byte to/from PC |
| 0x160002 | Port B | Input | Status byte from PC |
| 0x160004 | Port C | Output | Control signals to PC |
| 0x160006 | Control | Write | PPI mode configuration |

## Disk Access Protocol

Based on firmware analysis at 0x2974C7-0x297924, disk access follows this pattern:

### 1. Wait for Drive Ready

```
HDAE5000_ATA_WaitReady (0x297438):
    1. Read Status register (0x13001E)
    2. Check bits: BSY=0 (bit 7), DRDY=1 (bit 6)
    3. Mask with 0xC0, compare to 0x40
    4. Repeat until ready or timeout (0x3FFFFF iterations)
```

### 2. Standby (0x2974C7)

This is `HDAE5000_ATA_Standby`. It spins the drive down, and `HDAE5000_HD_Init` ends with it; it does not initialise anything.

```
HDAE5000_ATA_Standby:
    1. Wait for drive ready
    2. Write 0xFF to Features (0x130012)
    3. Write 0x00 to Sector Count (0x130014)
    4. Write 0xFF to Sector/Cyl Low/Cyl High (0x130016/18/1A)
    5. Write 0xA0 to Device/Head (0x13001C)
    6. Write 0x94 (Standby) to Command (0x13001E)
```

### 3. Read Sectors (0x297788)

`HDAE5000_ATA_ReadSector`: XHL = sector number, **1-based**, split head-major into CHS (see [HDAE5000 Filesystem — Sector Numbers]({{ site.baseurl }}/hdae5000-filesystem/#sector-numbers-and-chs)).

```
HDAE5000_ATA_ReadSector:
    1. Wait for drive ready (Status & 0xC0 == 0x40)
    2. Write 0x01 to Sector Count (0x130014)
    3. Write (0xA0 | head) to Device/Head (0x13001C)
    4. Write cylinder low to 0x130018
    5. Write cylinder high to 0x13001A
    6. Write sector number to 0x130016
    7. Write 0x20 (Read) to Command (0x13001E)
    8. Wait for DRQ (Status & 0xC8 == 0x48)
    9. Read 256 words from Data register (0x130010)
    10. Wait for completion (Status & 0xC0 == 0x40)
    11. Check error bit (Status & 0x01)
```

### 4. Write Sectors (0x29769B)

```
HDAE5000_ATA_WriteSector:
    1. Wait for drive ready
    2. Write 0x01 to Sector Count (0x130014)
    3. Write (0xA0 | head) to Device/Head (0x13001C)
    4. Write CHS address to registers
    5. Write 0x30 (Write) to Command (0x13001E)
    6. Wait for DRQ
    7. Write 256 words to Data register (0x130010)
    8. Wait for completion
    9. Check error bit
```

### 5. Identify Device (0x297884)

```
HDAE5000_ATA_IdentifyDevice:
    1. Wait for drive ready
    2. Write 0xFF to all address registers
    3. Write 0xA0 to Device/Head (0x13001C)
    4. Write 0xEC (Identify) to Command (0x13001E)
    5. Wait for DRQ
    6. Read 256 words from Data register to 0x200000
    7. Parse CHS geometry from identification data (HDAE5000_HD_ParseIdentify)
```

### 6. Reset Controller (0x29747A)

```
HDAE5000_ATA_SoftReset:
    1. Write 0x0E to Device Control (0x130020) - SRST + nIEN
    2. Write 0x0A to Device Control (0x130020) - Clear reset, keep nIEN
    3. Wait for drive ready
```

## Error Handling

The firmware includes multilingual error messages for various disk failures:

| Error | English Message | Likely Cause |
|-------|-----------------|--------------|
| SRAM Error | "Hard disk SRAM error" | Cache RAM failure on HDAE5000 |
| Reset Error | "Hard disk reset error" | Controller not responding |
| Read Error | "Hard disk read error" | Bad sector or media failure |
| ID Read Error | "Hard disk ID read error" | Identify Device command failed |
| Track 0 Error | "Hard disk track 0 error" | Cannot seek to track 0 |
| FSB Error | "Hard disk FSB read error" | Filesystem block corrupted |
| FAT Error | "Hard disk FAT read error" | File allocation table corrupted |

These errors are also available in German and French translations.

## Filesystem Structure

The HDAE5000 uses a **custom filesystem**, not FAT12/16/32, though it has a
32-bit allocation table of its own. In firmware sector numbers (1-based,
head-major CHS):

| Sectors | Contents |
|---------|----------|
| 1 | signature longs `0xAA55AA55`, `0xF4F1F2F3`; six setting bytes at +0x78 |
| 2 - 3907 | FAT: 32-bit entries, 0 = free, `0xFFFFFFFE` = end of chain |
| 3908 - 4230 | 323 table sectors: 120 directory names, 1,920 song records, 120 FLS records |
| 4231 on | data clusters (0x20 or 0x40 sectors each) |

The PC link calls the three tables the "Dir block", "FileSystem block" and "Fls
block". A debug trace calls the first two "FGB" and "FEB". The full description,
with the evidence, is on [HDAE5000 Filesystem]({{ site.baseurl }}/hdae5000-filesystem/).

## PPORT Commands for Disk Operations

The PC parallel port (PPORT) protocol includes these disk-related commands:

| Code | Command | Description |
|------|---------|-------------|
| 01 | Send Infos About HD | Report CHS parameters and model |
| 03 | Read FSB from HD | Read filesystem block |
| 04 | Send FSB to PC | Transfer FSB to PC |
| 05 | Rcv FSB from PC | Receive FSB from PC |
| 06 | Write FSB to HD | Write filesystem block |
| 07 | Load HD to Memory | Load file into KN5000 RAM |
| 08 | Send data to PC | Send data block to PC |
| 10 | Rcv data from PC | Receive data from PC |
| 11 | Save memory to HD | Save RAM contents to file |
| 16 | Delete files | Remove files from disk |
| 17 | Format HD | Low-level disk format |
| 18 | Switch HD-motor off | Spin down drive motor |

## PC Parallel Port Protocol

The HD-TechManager5000 Windows software (ppkn50.dll) communicates with the HDAE5000 using a bidirectional parallel port protocol. This section documents the low-level handshaking derived from disassembly of ppkn50.dll.

### Parallel Port Mode: PS/2 Bidirectional

The protocol requires **PS/2 bidirectional mode** (also called "byte mode"), **not** SPP nibble mode, EPP, or ECP.

#### Why not SPP nibble mode?

On a pure unidirectional SPP port, the standard way to receive data from a peripheral is **nibble mode**: the peripheral puts 4 bits on the status lines (base+1, bits 3--7), the PC reads them, then the peripheral sends the other 4 bits --- two reads per byte through the status port.

The ppkn50.dll does **not** use nibble mode. The receive-byte function (at address `0x10001360` in ppkn50.dll) reads data from `base+0` (the data port) via a single `in (%dx), %al` instruction at address `0x1000142A`, after setting control bit 5 to switch the data bus direction. There is no status-port bit shifting, no two-nibble reassembly --- it's a direct 8-bit read from the data port.

#### Why not EPP or ECP?

EPP adds hardware-handshaked registers at base+3 (address) and base+4 (data). ECP adds DMA and FIFO registers. The ppkn50.dll **never accesses** any port beyond base+0, base+1, and base+2. All handshaking is software-driven (strobe/busy polling).

#### Evidence from ppkn50.dll binary

The send-byte and receive-byte functions explicitly switch the data port direction via control register bit 5:

**Send byte** (ppkn50.dll address `0x100011E0`):
```asm
100011f0:  ec              in     (%dx),%al      ; read control (base+2)
100011f1:  24 5e           and    $0x5e,%al      ; clear bit 5 (output mode) + bit 0 + bit 7
100011f3:  ee              out    %al,(%dx)      ; write control
100011f8:  8a 45 0c        mov    0xc(%ebp),%al  ; load data byte
100011fb:  ee              out    %al,(%dx)      ; write to data port (base+0)
```

**Receive byte** (ppkn50.dll address `0x10001360`):
```asm
10001372:  ec              in     (%dx),%al      ; read control (base+2)
10001373:  0c a1           or     $0xa1,%al      ; set bit 5 (input mode) + bit 0 + bit 7
10001375:  ee              out    %al,(%dx)      ; write control
    ; ... poll status bit 7, wait for data ready ...
1000142a:  ec              in     (%dx),%al      ; read data port (base+0)
```

The `AND $0x5E` clears bit 5 (switch to output), the `OR $0xA1` sets bit 5 (switch to input). This is the defining characteristic of PS/2 bidirectional mode. A pure SPP port ignores bit 5, and reading base+0 returns the output latch --- which would corrupt received data.

**Direction switching summary:**

| Control bit 5 | Data port (base+0) | Operation |
|---------------|-------------------|-----------|
| 0 (cleared) | Output | PC writes data to HDAE5000 |
| 1 (set) | Input | PC reads data from HDAE5000 |

**Compatibility:** A PC with only unidirectional SPP (no PS/2 bidirectional support) will **not** work with TechManager5000 --- data reads will return the output latch value instead of the HDAE5000's data. The PC must have at least a PS/2-compatible parallel port (standard on PCs from 1987 onwards).

**MAME emulation note:** MAME's `pc_lpt_device` required a fix to support PS/2 bidirectional mode. The original `data_r()` implementation always returned `m_data & peripheral_data` (SPP pull-up behavior), which masks out peripheral data bits wherever the output latch has zeros. For example, after sending byte 0x01 and switching to input mode, only bit 0 of the peripheral's response would be visible. The fix (March 2026, branch `kn5000_research_techmanager`) checks the inverted control bit 5 and returns pure peripheral data when bidirectional mode is active.

### Physical Interface

**PC Parallel Port (PS/2 Bidirectional):**

| Port Address | Register | Direction | Function |
|--------------|----------|-----------|----------|
| base+0 (0x378) | Data | Bidirectional | 8-bit data byte (direction controlled by ctrl bit 5) |
| base+1 (0x379) | Status | Input | Status signals from HDAE5000 |
| base+2 (0x37A) | Control | Output | Control signals to HDAE5000 (bit 5 = direction) |

**HDAE5000 PPI (Intel 8255 at 0x160000):**

| Address | Port | Direction | Function |
|---------|------|-----------|----------|
| 0x160000 | Port A | Bidirectional | Data byte to/from PC |
| 0x160002 | Port B | Input | Status from PC |
| 0x160004 | Port C | Output | Control signals to PC |

### Status Port Bits (base+1)

| Bit | Name | Description |
|-----|------|-------------|
| 7 | BUSY | Inverted; 0=HDAE5000 busy, 1=ready |
| 6 | ACK | Acknowledge signal |
| 4 | SELECT | HDAE5000 online indicator |
| 3 | ERROR | Error condition |

**Note:** Bit 7 (BUSY) is inverted in hardware by the PC parallel port. The ppkn50.dll XORs with 0x80 after reading to compensate.

### Control Port Bits (base+2)

| Bit | Name | Description |
|-----|------|-------------|
| 3 | SELECT_IN | Select printer |
| 2 | INIT | Initialize/reset |
| 1 | AUTOFEED | Strobe acknowledge |
| 0 | STROBE | Data strobe signal |

### Byte Transfer Handshaking

**Send Byte to HDAE5000:**

```
PC                          HDAE5000
 |                              |
 |-- Write Data to Data Port -->|
 |-- Assert Strobe (bit 1) ---->|
 |                              |
 |<---- BUSY goes LOW ----------|  (data received)
 |                              |
 |-- Deassert Strobe ---------->|
 |                              |
 |<---- BUSY goes HIGH ---------|  (ready for next)
```

**Receive Byte from HDAE5000:**

```
PC                          HDAE5000
 |                              |
 |<---- BUSY goes LOW ----------|  (data available)
 |                              |
 |-- Read Data from Data Port --|
 |-- Assert ACK (bit 1) ------->|
 |                              |
 |<---- BUSY goes HIGH ---------|  (acknowledged)
 |                              |
 |-- Deassert ACK ------------->|
```

### Timeout Values

- **Byte transfer timeout**: 10,000ms (0x2710)
- **Polling iterations**: 512 before time check
- **Connection test retries**: 5 times with 1000ms delay

### Error Codes (from ppkn50.dll)

| Code | Meaning |
|------|---------|
| 0 | Success |
| -1 | DLL not initialized |
| -2 | Port not open / connection failed |
| -3 | Handshake timeout |
| -4 | Transfer error |
| -5 | Port busy |
| -10 | Escape pressed |
| -20 | Invalid port number |

### DLL Exported Functions

The ppkn50.dll exports these functions for PC applications:

| Function | Command | Description |
|----------|---------|-------------|
| `InitializeTheDllPP50` | - | Initialize DLL |
| `OpenThePortNumberPP50` | - | Select LPT port (1-3) |
| `CloseThePortPP50` | - | Close parallel port |
| `TestTheKNPPPP50` | 0x01 | Test connection |
| `ReadFsbFromKnHdToKnMemPP50` | 0x03 | Read FSB from HD |
| `SendFsbFromKnMemToPCPP50` | 0x04 | Transfer FSB to PC |
| `SendFsbFromPCToKnMemPP50` | 0x05 | Transfer FSB to KN |
| `LoadFileFromKnHdToKnMemPP50` | 0x07 | Load file HD→KN |
| `DeleteFileOnKnHdPP50` | 0x16 | Delete file |
| `FormatTheKn50HardDiskPP50` | 0x17 | Format HD |
| `TurnOffTheKn50HdMotorPP50` | 0x18 | Spin down motor |

## RAM Variables

Key RAM locations used by disk routines:

| Address | Name | Purpose |
|---------|------|---------|
| 0x200222 | `HDAE5000_RAM_AtaError` | drive error byte, 0 = ok; tested after every disk operation |
| 0x229C32 / 0x229C34 / 0x200220 | — | cylinders / heads / sectors per track from IDENTIFY (`HDAE5000_HD_ParseIdentify`) |
| 0x229C5C | `HDAE5000_RAM_SectorsPerCluster` | 0x20, or 0x40 on drives of at least 0x14DC93 sectors |
| 0x229D92 | `HDAE5000_RAM_HdInitResult` | `HDAE5000_HD_Init`'s step code, 0 = ready and formatted |
| 0x229D98 | `HDAE5000_RAM_HdSignatureOk` | 1 when sector 1 carries the signature |
| 0x229D99 / 0x229D9A | `HDAE5000_RAM_WriteProtect` / `HDAE5000_RAM_WriteConfirm` | "WRITE PROTECTION" / "WRITE CONFIRM" settings |
| 0x229DA9-0x229DAE | — | the six setting bytes from sector 1 +0x78 (quick load, load by number, jump after load, lyric jump, lyric colours) |
| 0x230EDA | `HDAE5000_RAM_HdPresent` | `HDAE5000_Check_HD_Present`'s result (the step code above) |

The older names in this table (HD_STATUS_FLAG, HD_CONFIG "drive configuration flags", "0=no HD, non-zero=HD present") did not survive the hdae lane's reading of the code. The full layout is on [HDAE5000 Filesystem]({{ site.baseurl }}/hdae5000-filesystem/).

## Design Considerations

### Why CHS Instead of LBA?

The HDAE5000 uses CHS (Cylinder/Head/Sector) addressing rather than the newer LBA (Logical Block Addressing). This was common for drives of this era (1996) and provides:
- Direct physical addressing
- Compatibility with older drive firmware
- Simpler sector calculation

### Drive Protection

The firmware includes protective features:
- **Motor timeout**: Spins down drive during inactivity
- **No real-time playback**: Files must be loaded to RAM first
- **Verification**: Reads back written data to confirm

### Sector Size

Standard 512-byte sectors are used, as indicated by the `hddscby` (sector bytes) debug string.

## Emulation Considerations

For MAME emulation, the HDAE5000 disk interface requires:

1. **Direct ATA Register Mapping**: ATA registers at 0x130010-0x130020
   - Data register (16-bit): 0x130010
   - Command block registers (8-bit): 0x130012-0x13001E
   - Device Control (8-bit): 0x130020
2. **PPI Emulation**: Full 8255 PPI at 0x160000 for PC communication (not for IDE)
3. **IDE Drive Model**: CHS-addressed IDE drive simulation
4. **Status Bits**: Proper BSY/DRDY/DRQ/ERR flag handling
5. **PIO Mode**: All transfers are PIO (no DMA observed)
6. **Custom Filesystem**: only needed for tools outside the firmware (the firmware formats and reads its own layout; see [HDAE5000 Filesystem]({{ site.baseurl }}/hdae5000-filesystem/))

## Verified Implementation Details

The following details were confirmed through firmware analysis:

- **Base Address**: ATA registers start at 0x130010, not 0x130000
- **Transfer Mode**: All data transfers use PIO mode via 16-bit Data register
- **Sector Size**: 512 bytes (256 word transfers)
- **Addressing**: CHS mode only (no LBA observed)
- **Timeout**: Drive ready timeout uses 0x3FFFFF (~4M) iteration loop
- **Status Polling**: Firmware polls Status register in tight loops (no interrupts)

## Further Research

Areas requiring additional investigation:
- Which of a song record's ten first-cluster slots holds which part, and the FLS item bytes at +80/+112 ([HDAE5000 Filesystem]({{ site.baseurl }}/hdae5000-filesystem/#open-questions))
- Error recovery procedures
- Exact timing requirements for real hardware

**Completed:**
- PC parallel port protocol details (documented above from ppkn50.dll analysis)

## Related Documentation

- [HDAE5000 Overview]({{ site.baseurl }}/hdae5000/) - Firmware and initialization
- [Memory Map]({{ site.baseurl }}/memory-map/) - Address space layout
- [Hardware Architecture]({{ site.baseurl }}/hardware-architecture/) - System overview

## References

- ATA/ATAPI-4 Specification (T13/1153D)
- Intel 8255A PPI Datasheet
- HDAE5000 ROM disassembly analysis
- ppkn50.dll disassembly (HD-TechManager5000 parallel port DLL)
