---
layout: page
title: Boot Sequence
permalink: /boot-sequence/
---

# KN5000 Boot Sequence

This page documents the complete boot sequence of the Technics KN5000, from power-on to a fully functional system. The KN5000 uses a dual-CPU architecture where the Main CPU orchestrates startup and loads firmware to the Sub CPU.

> **See Also**: [System Overview]({{ site.baseurl }}/system-overview/) for overall architecture and [CPU Subsystem]({{ site.baseurl }}/cpu-subsystem/) for detailed CPU specifications.

## Overview

```
Power On
    │
    v
┌─────────────────┐     ┌─────────────────┐
│   Main CPU      │     │    Sub CPU      │
│  TMP94C241F     │     │   TMP94C241F    │
│  (IC5)          │     │   (IC27)        │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │  1. Table Data ROM    │  1. Boot ROM
         │     First-stage boot  │     0xFF8290
         │                       │
         v                       v
    Memory Remap            Init Hardware
    Program ROM → 0xE00000  Wait for payload
         │                       │
         │  2. Program ROM       │
         │     Boot_InitIOPorts  │
         │                       │
         v                       v
    Init Hardware           Receive payload
    Load Sub CPU            at 0x0400
    Payload (192KB)              │
         │                       │
         │   <─── DMA ───>       │
         │   (0x120000 latch)    │
         │                       │
         v                       v
    Start Subsystems        Execute Payload
    (UI, MIDI, FDC...)      (Audio Engine)
         │                       │
         v                       v
    ┌─────────────────────────────┐
    │     System Ready            │
    └─────────────────────────────┘
```

## Main CPU Boot Sequence

### Discovery: Two-Stage Boot Process

**Important finding**: The Main CPU uses a **two-stage boot process**. On reset, the **Table Data ROM** is initially mapped at 0xE00000-0xFFFFFF and contains a first-stage bootloader. This bootloader configures the memory controller to remap the Program ROM to 0xE00000, then jumps to the main firmware.

### Stage 1: Table Data ROM Bootloader

> **Status (August 2026)**: the first-stage bootloader is **fully disassembled** — there
> are no raw `.incbin` blobs left anywhere in it, and the rebuilt `kn5000_table_data.rom`
> is byte-identical to the dump. See `table_data/kn5000_table_data.s` and the six
> dedicated modules listed under [First-Stage Bootloader: No Raw Blobs Left](#first-stage-bootloader-no-raw-blobs-left).

#### Reset Vector (0xFFFEE0)

On CPU reset, the Table Data ROM is mapped at 0xE00000-0xFFFFFF. The reset vector at 0xFFFEE0 (table_data offset 0x1FFEE0) contains:

```asm
JP 0x00FFB4E8    ; Jump to first-stage boot code
```

#### First-Stage Boot Code (0xFFB4E8)

The table_data bootloader at 0xFFB4E8 performs critical memory controller configuration:

```asm
; Memory Start Address Registers - define where each block appears
LD (MSAR0), 0x1E    ; Block 0 → 0x1E0000 (SRAM)
LD (MSAR1), 0x10    ; Block 1 → 0x100000 (I/O)
LD (MSAR2), 0xC0    ; Block 2 → 0xC00000
LD (MSAR3), 0x00    ; Block 3 → 0x000000 (DRAM)
LD (MSAR4), 0x80    ; Block 4 → 0x800000 (believed: program flash; the table data is block 2, moved by MSAR2 later)
LD (MSAR5), 0x00    ; Block 5 → 0x000000

; Memory Address Mask Registers - define block sizes
LD (MAMR0), 0x0F    ; Block 0 mask
LD (MAMR1), 0x3F    ; Block 1 mask
LD (MAMR2), 0x7F    ; Block 2 mask
LD (MAMR3), 0x1F    ; Block 3 mask
LD (MAMR4), 0xFF    ; Block 4 mask
LD (MAMR5), 0xFF    ; Block 5 mask

; DRAM Controller initialization
LD (DRAM1REF), 0x81      ; then 0x71
LD (DRAM1CRL), 0x8B
LD (DRAM1CRH), 0x58
RES 4, (PMEMCR)          ; a one-bit RMW -- NOT "LD (PMEMCR), 0xF1";
                         ; the 0xF1 is the opcode prefix, not the operand
```

Also programmed in the same block, and omitted from earlier versions of this page: the
twelve wait-state/bus-width bytes `B0-5CSL = 11 33 11 22 11 22` and
`B0-5CSH = 80 81 C2 8A 82 81`.

> **This block does *not* perform the remap.** It sets `MSAR2 = 0xC0`. The swap happens
> later and separately, in `Boot_PrepareJump`, as a single store `MSAR2 := 0x80` three
> instructions before the jump — see below and
> [TMP94C241 Memory Controller]({{ site.baseurl }}/tmp94c241-memory-controller/).

After the handover store:
- **Table Data ROM** is reachable at 0x800000-0x9FFFFF
- **Program ROM** becomes visible at 0xE00000-0xFFFFFF
- The bootloader jumps to `0xFFFEDC`, a 4-byte slot that exists **only in the program
  flash** (`1B 0F 05 EF` = `JP 0xEF050F`), landing at **`Boot_InitIOPorts` (0xEF050F)** —
  *not* at the program ROM's own `RESET_HANDLER` (0xEF03C6). The handover deliberately
  skips the program flash's duplicate copy of the hardware-init block, which has just been
  run, and the four SC0 serial-setup instructions at 0xEF0500-0xEF050E.
  (MAME, which starts at 0xEF03C6, therefore runs both.)

#### Boot_ClearRAM Routine (0xFFB740)

The first-stage bootloader calls `Boot_ClearRAM` to initialize RAM and copy essential data from ROM:

```asm
Boot_ClearRAM:
    ; Clear 35,146 bytes at RAM 0x104E (general RAM area)
    LD XDE, 0x0000104E    ; Destination
    LD XBC, 0x0000894A    ; Count
    ; Uses LDIRW for efficient word-mode fill with zeros

    ; Clear 1,091 bytes at RAM 0x0C00 (boot variables)
    LD XDE, 0x00000C00
    LD XBC, 0x00000443

    ; Copy 10 bytes from ROM 0xFFB4D2 to RAM 0x1044
    ; Data: 00 40 20 08 10 04 02 00 01 00 (bit mask table)

    ; Copy 12 bytes from ROM 0xFFB4DC to RAM 0x9998
    ; Data: 7E 00 10 00 00 00 80 00 00 00 00 00 (init params)
```

The bit mask table at 0x1044 is used for bit manipulation operations throughout the firmware. The initialization parameters at 0x9998 appear to be related to stack/display setup.

#### Flash Programming Routines (0xFFB812-0xFFC8C1)

The bootloader contains a complete set of flash programming routines for all target memories:

| Group | Address Range | First routine | Targets |
|-------|---------------|---------------|---------|
| 16-bit flash routines | 0xFFB812-0xFFBBF2 | `Flash_Reset_16bit` | HDAE5000 ROM, Custom Data Flash |
| Flash init + helper | 0xFFBBF3-0xFFBC2C | `Flash_Init_Custom_And_Table`, `MemBlock_FillWithZeros` | called from `Boot_Init` |
| 32-bit flash routines | 0xFFBC2D-0xFFBF06 | `Flash_Reset_32bit` | Table Data ROM (interleaved) |
| Boot sector reads | 0xFFBF07-0xFFBFC3 | `FDC_Reset`, `FDC_ReadSector` | thin wrappers over `FDC_Request` |
| Disk type detection | 0xFFBFC4-0xFFC0D3 | `Boot_DetectDiskType` | eight update-disk signatures, compared with `Boot_memcmp` |

(Boundaries above are the symbol addresses from the rebuilt ELF, so the ranges no longer
overlap the way the earlier table did.)

> **See Also**: [Flash Programming]({{ site.baseurl }}/flash-programming/) for detailed protocol documentation and comparison with Program ROM flash routines.

#### LZSS Decompressor Suite (0xFFC8C2-0xFFCC29)

The bootloader includes a complete LZSS decompression subsystem for handling compressed firmware data. This is the "SLIDE4K" format used by the firmware update system.

> **Status**: All LZSS routines (872 bytes total) are now **100% byte-matching** disassembly in `table_data/kn5000_table_data.s`.

##### Decompressor Routines

| Routine | Address | Size | Purpose |
|---------|---------|------|---------|
| `LZSS_ReadByte` | 0xFFC8C2 | 115 bytes | Read from compressed stream with sector buffering |
| `LZSS_OutputByte` | 0xFFC935 | 63 bytes | Write decompressed bytes with 32-bit batching |
| `LZSS_OutputByte_Alt` | 0xFFC974 | 63 bytes | Alternative output for flash update mode |
| `LZSS_ParseHeader` | 0xFFC9B3 | 157 bytes | Parse/validate firmware header, setup source |
| `LZSS_Decompress` | 0xFFCA50 | 474 bytes | Main decompression loop with sliding window |

##### Format Characteristics

| Parameter        | Value                     | Description                                              |
|------------------|---------------------------|----------------------------------------------------------|
| Window Size      | 4096 bytes (0x1000)       | Standard SLIDE4K                                         |
| Pre-fill         | 0x00 for first 4078 bytes | Window positions 0-0x0FED                                |
| Initial Position | 0x0FEE                    | First write position                                     |
| Offset Bits      | 12 bits                   | Masked with 0x0FFF                                       |
| Length Bits      | 4 bits                    | Low nibble of the second byte; match length = nibble + 3 |
| Flag Byte        | High bit = sentinel       | Bit 0: 1=literal, 0=back-ref                             |
| Header           | "SLIDE4K" + size          | 11+ byte header with magic and decompressed size         |

##### RAM Variables (0x0C20-0x0C38)

| Address | Name            | Purpose                                                      |
|---------|-----------------|--------------------------------------------------------------|
| 0x0C20  | Expected Size   | Target decompressed size (3 bytes, big-endian in the header) |
| 0x0C24  | Output Position | Current output byte count                                    |
| 0x0C28  | Dest Address    | Destination pointer for decompressed data                    |
| 0x0C2C  | Buffer Pointer  | Sector read buffer (typically 0x0099A4)                      |
| 0x0C30  | Display X       | Progress indicator X coordinate                              |
| 0x0C32  | Display Y       | Progress indicator Y coordinate                              |
| 0x0C34  | Sector Offset   | Current sector read offset                                   |
| 0x0C36  | Byte Counter    | Output byte counter (0-3 for 32-bit writes)                  |
| 0x0C38  | Source Address  | Compressed data source pointer                               |

##### Decompression Algorithm

```
1. Allocate 4KB window buffer (via malloc at 0xFFFB56)
2. Pre-fill window[0..0xFED] with 0x00
3. Set window_pos = 0x0FEE
4. Read 8-byte header, then 3-byte size (big-endian)
5. Main Loop:
   a. Shift flag byte right
   b. If bit 8 clear, read new flag byte (set bit 8 as sentinel)
   c. If bit 0 = 1: read literal byte, output to dest and window
   d. If bit 0 = 0:
      - Read offset low byte (8 bits)
      - Read offset high + length byte
      - Offset = (high_nibble << 8) | low_byte (12 bits)
      - Length = low_nibble + 3 (the routine stores low_nibble + 2 and its copy loop runs while counter <= that value)
      - Copy (length) bytes from window[offset] to output
   e. Update window_pos (masked to 12 bits)
6. Continue until output_size reached
7. Free window buffer (via free at 0xFFFCDD)
```

##### Compressed Data Locations

| Location           | Address  | Contents                                                                                | Header                           |
|--------------------|----------|-----------------------------------------------------------------------------------------|----------------------------------|
| **Table Data ROM** | 0x8E0000 | Demo-song preset 18, ~28 KB compressed (27,956 B, `table_data/kn5000_table_data.s:356`) | `"SLIDE4K", 0x00, 0x00, 0x95...` |
| **Boot Headers**   | 0x9FA000 | Update file type signatures                                                             | `"SLIDE"` markers                |
| **Boot UI**        | 0x9FA150 | Flash update UI bitmaps                                                                 | `"SLIDE"` marker + bitmap        |

**Note:** The data at 0x8E0000 does NOT contain the Sub CPU executable. See [Subprogram Storage Location](#subprogram-storage-location-under-investigation) below.

##### Callers of LZSS Decoder

The LZSS decoder is invoked during flash firmware updates:

| Routine | Address | File Type | Source |
|---------|---------|-----------|--------|
| `HANDLE_UPDATE_FILE_TYPE_ID_007h` | 0xEF47FA | Program DATA FILE PCK | 0x3E0000, 0x3F0000 |
| `HANDLE_UPDATE_FILE_TYPE_ID_008h` | 0xEF481E | Table DATA FILE PCK | Table Data ROM |
| `LZSS_ParseHeader` | 0xFFC9B3 | Flash update mode | 0x3E0000 (boot context) |

##### Update File Types

The firmware update system recognizes these LZSS-compressed file types:

| ID | File Type String | Description |
|----|-----------------|-------------|
| 0x07 | `"Technics KN5000 Program  DATA FILE PCK"` | Compressed program ROM |
| 0x08 | `"Technics KN5000 Table    DATA FILE PCK"` | Compressed table data |
| - | `"Technics KN5000 CMPCUSTOMDATA FILE"` | Compressed custom data |

The `PCK` suffix indicates LZSS-compressed content using the SLIDE4K format.

#### First-Stage Bootloader: No Raw Blobs Left

Until August 2026 six regions of the bootloader were carried in the build as raw binary
includes with guessed labels. All six are now labelled assembly, and the 2 MB Table Data
ROM still rebuilds byte-identical to the dump:

| former blob | ROM range | now built from | commit |
|-------------|-----------|----------------|--------|
| `bootcode_hdae_to_lzss.bin` | 0x9FC6F7-0x9FC8C1 | inline in `kn5000_table_data.s` (HD-AE5000 boot-flash tail) | `22ecfb5` |
| `bootcode_flash_handlers.bin` | 0x9FD8A5-0x9FEA9C | `table_data/boot_fdc_driver.s` | `65c79cb` |
| `bootcode_utils.bin` | 0x9FEB2B-0x9FF228 | `boot_disk_probe.s` + `boot_cpserial.s` | `72242c0` |
| `bootcode_serial_handlers.bin` | 0x9FF229-0x9FF2F1 | `boot_cpserial_isr.s` | `3de6871` |
| `bootcode_serial_state.bin` | 0x9FF2F2-0x9FFB55 | `boot_cpserial_states.s` (tail `Boot_sbrk` opens `boot_clib.s`) | `3de6871` |
| `bootcode_malloc_and_after.bin` | 0x9FFB56-0x9FFEDF | `boot_clib.s` + `boot_debug.s` | `670077e` |

The blob files themselves are still on disk untouched, because the archived ASL mirror of
the build still includes them.

Two of the old labels were simply wrong, and the corrections matter:

* `bootcode_flash_handlers.bin` is **not** a set of "flash update type handlers". It is
  the complete command layer of the bootloader's **floppy disk driver** for the uPD72068
  at IC208 (see below).
* the CP-serial half of `bootcode_utils.bin` was described as "motor control / VGA
  display / progress bar". It is the bootloader's own control-panel serial driver.

> **A cautionary detail.** The `bootcode_hdae_to_lzss.bin` include used to start
> *mid-instruction*: the source emitted a 4-byte fragment and the fifth byte of a 5-byte
> `LD A, (0x160002)` was byte 0 of the blob. The ROM still rebuilt byte-identical — a
> byte-match gate cannot see this — but any disassembly of the blob starting at its own
> first byte begins in the middle of an instruction, so everything decoded from there was
> suspect; the surrounding comment also described the instruction as a *store* when it is
> a PPI Port B *read*. Wave 0 emitted the instruction
> whole and skipped blob byte 0 with `.incbin "file", 1, 459` (commit `f79fcb1`). When a
> blob boundary lands inside an instruction, the disassembly around it is untrustworthy
> even though the build is green.

#### The Bootloader's Own Floppy Driver (0xFFD8A5-0xFFEA9C)

4,600 bytes, entered through the single public routine `FDC_Request` (boot 0xFFE944),
which takes a pointer to a 14-byte request block and supports twelve commands
(initialize, recalibrate, seek, read, write, format, motor on/off, get last error, set
disk-changed, controller reset, sense drive status). It is a compact port of the main
firmware's FDC driver, rebuilt for the boot-time update path, and each routine's header
in `table_data/boot_fdc_driver.s` cites its main-CPU twin.

Dispatch runs through three tables of 16-bit offsets packed together at ROM
0x9FB496-0x9FB4D1 — media-type stanzas, per-command validators, per-command execution
stubs — each consumed by a `jp T, XIX+WA` computed jump. Full detail, including the
request-block layout, the error codes and the disk-format probe, is on the
[FDC Subsystem]({{ site.baseurl }}/fdc-subsystem/#the-bootloaders-fdc-driver-rom-0x9fd8a5-0x9fea9c)
page.

#### Boot C Runtime (0xFFFB2F-0xFFFE7F)

The bootloader links a small compiler-runtime/libc subset. Every block, free or
allocated, carries a 6-byte header: `u32 next`, `u16 size`, then the data the caller sees.

| routine | boot address | notes |
|---------|--------------|-------|
| `Boot_sbrk` | 0xFFFB2F | bump allocator over the arena at RAM (0x009998)/(0x00999C); returns 0xFFFFFFFF when exhausted |
| `Boot_malloc` | 0xFFFB56 | first-fit over the free list at RAM (0x0099A0); splits a block when the leftover is ≥ 10 bytes; falls back to `Boot_sbrk` |
| `Boot_free` | 0xFFFCDD | address-ordered insertion with forward *and* backward coalescing; each merge reclaims the absorbed block's 6-byte header |
| `Boot_memcmp` | 0xFFFBDC | bounded compare — but a matching 0x00 byte ends it early, so the semantics are `strncmp`, not `memcmp` |
| `Boot_SDivMod32` / `Boot_UDivMod32` | 0xFFFC0E / 0xFFFC63 | signed wrapper + unsigned 32/32 core; hardware `div` when the divisor fits in 16 bits, restoring shift-subtract otherwise; divide-by-zero returns 0xFFFFFFFF |

Only two callers use the heap: `Boot_DetectDiskType` (sector-signature buffer) and
`LZSS_Decompress` (the 4 KB sliding window) — which is exactly the `malloc at 0xFFFB56` /
`free at 0xFFFCDD` pair named in the decompression algorithm above.

The divide runtime is the compiler's, not the bootloader's: the same routine is linked
into the main CPU firmware (`DivMod32` / `Math_DivideU32`) and into the HD-AE5000
extension ROM (`HDAE5000_UMod32` / `HDAE5000_UDivMod32` at 0x29B8BF /
0x29B8C5). The three copies share the algorithm and the entry structure but are not
byte-identical — a few instruction encodings differ. The HD-AE5000 labels used to be
`HDAE5000_Divide_Unsigned` / `HDAE5000_Divide_Signed`, swapped with respect to the code.
The hdae lane renamed them in September 2026 (`scripts/renaming/rename_hdae5000_libc.sed`):
0x29B8C5 is the unsigned core, and 0x29B8BF its modulo entry.

The tail of the region ends in dead code: `Boot_free_DeadTail9998` (0xFFFD7D) is a
byte-for-byte copy of `Boot_free` from its `extz xhl` onward with the list head address
changed from 0x0099A0 to 0x009998, with no prologue and no reference anywhere in the ROM.
It is **not** a callable "secondary-heap free" — control cannot reach it.

#### Boot-Time Control-Panel Serial Link

The bootloader also carries a complete control-panel serial driver of its own — three
interrupt handlers, an 11-entry state machine, ring buffers and a packet codec — spread
across `boot_cpserial.s`, `boot_cpserial_isr.s` and `boot_cpserial_states.s`. It is
**independent of the runtime `CPanel_*` stack** in the Program ROM.

It is only brought up when a disk is present, and only one probe answer changes the boot
path:

```
Boot_Init
    ├── Boot_CheckDiskPresent (0xFFEC63)  — Port D bit 6, active low
    │        └── no disk ──> jump to Program ROM
    ├── BootSerial_Init (0xFFEC7E)        — handshake + device ident
    ├── Boot_ProbeExternalDevice (0xFFED0E) ──> HL = device class
    │        ├── class != 4 ──> jump to Program ROM
    │        └── class == 4 ──> firmware update UI
```

One finding is worth carrying here: the driver's external-decode hook for class-2
received packets resolves to `BootStub_ReturnError` (ROM 0x9FB80E, `ldw hl, 0xFFFF; ret`),
and the caller treats 0xFFFF as failure — so **class-2 packets are always dropped on a
stock machine**.

Full documentation: [Boot CP-Serial Link]({{ site.baseurl }}/boot-cpserial-link/).

#### Evidence

The table_data ROM contains a complete interrupt vector table at offset 0x1FFF00:

| Vector | Address | Target | Description |
|--------|---------|--------|-------------|
| 0 (Reset) | 0xFFFEE0 | 0xFFB4E8 | First-stage boot code |
| 1-7 | 0xFFB705 | Handler | Common interrupt handler |
| 11 | 0xFFEAB2 | Handler | Specific handler |

The memory controller values in the table_data bootloader are **identical** to those in the Program ROM boot code (`v10/maincpu/shared/boot_hw_init.s`, which `RESET_HANDLER` includes), confirming this is the intended configuration.

### Stage 2: Program ROM Main Boot

#### Reset Handler (0xEF03C6)

After memory remapping, execution continues at `Boot_InitIOPorts` (0xEF050F), reached through the program flash's slot at 0xFFFEDC. The program flash's own `RESET_HANDLER` (0xEF03C6), which repeats the shared hardware-init block (`shared/boot_hw_init.s`), runs only when the program flash answers the reset vector, as it does in MAME. The TMP94C241F CPU now sees the Program ROM at 0xE00000-0xFFFFFF.

#### Hardware Initialization

The reset handler performs additional hardware setup (note: memory controller is already configured by Stage 1):

| Step | Description | Key Registers |
|------|-------------|---------------|
| 1 | Disable watchdog | WDMOD, WDCR |
| 2 | Configure clock | CLKMOD |
| 3 | Initialize ports | P0-PZ, PxCR, PxFC |
| 4 | Set up memory controller | MSARx, MAMRx, BxCS |
| 5 | Initialize DRAM | DREFCR, DMEMCR |
| 6 | Configure timers | T01MOD, T4MOD, etc. |
| 7 | Initialize stack | XSP = stack address |
| 8 | Initialize work DRAM | `Boot_InitWorkRAM` (called from `Boot_InitIOPorts` right after `ld xsp,0xc00`) |

`Boot_InitWorkRAM` zero-fills DRAM `0x010000-0x03D523` and `0x000400-0x00E35C`.
It then copies two ROM images of initialised RAM: ROM `0xEED8C8` → RAM `0x3D524`
(0x219E bytes) and ROM `0xEEFA66` → RAM `0xE35E` (0x95B bytes; v7: 0x931 bytes to
`0xE2C2`). Because the code reads these variables and tables at their **RAM**
addresses, a search for readers of the ROM bytes must look for the RAM copy;
see [Memory Map — Work-RAM initial image]({{ site.baseurl }}/memory-map/#work-ram-initial-image).
It ends with `jrl Boot_RunSelfTest`.

#### Sub CPU Payload Loading

After hardware initialization, the main CPU loads a 192KB firmware payload to the sub CPU via DMA through the inter-CPU latch at `0x140000` (main CPU side) / `0x120000` (sub CPU side).

> **Deep Dive: Sub CPU Payload Transfer**
>
> The payload transfer is handled by `SubCPU_Send_Payload` (0xEF068A) using the E1 bulk transfer protocol. This is one of the most complex boot operations, involving:
> - Multiple 64KB chunk transfers from Table Data ROM
> - SLIDE4K decompression of the sub-CPU executable from custom-data flash 0x3E0000 (fallback base: table-data 0x800000)
> - Careful timing with delay loops
>
> **Quick Reference:**
> - [`SubCPU_Send_Payload`](#subcpu_send_payload-details) - Main transfer routine (see below)
> - [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/#subcpu_send_payload-0xef068a) - Full technical details with code examples
> - [Open Questions](#subprogram-storage-location-under-investigation) - What the two source bases hold, and the dump-provenance question that remains

**Main CPU Boot Sequence:**
```
Boot_Init (0xFFB4E8, table-data bootloader; MAME starts at RESET_HANDLER 0xEF03C6)
    │
    ├── LD (PA), 0xFE         ; Hold Sub CPU in reset (bit 0 = 0)
    │
    ├── ... Boot_InitIOPorts (0xEF050F) and the rest of hardware init ...
    │
    ├── SET 0, (PA)           ; Release Sub CPU from reset (0xEF05F8)
    │
    ├── CALL SubCPU_Init_DMA_Channels  ; Set up DMA at 0xEF329E
    │
    ├── EI 0                  ; Enable interrupts
    │
    └── CALR SubCPU_Send_Payload       ; Send 192KB payload at 0xEF068A
```

**E1 Transfer Protocol Summary:**
1. Main CPU waits for SSTAT1 high (Sub CPU ready)
2. Main CPU sends E1 command byte (0xE1) to latch
3. Main CPU sends 6-byte header (destination address + byte count)
4. Main CPU sends actual data via DMA
5. Repeat for each 64KB chunk
6. The last block (256 bytes to sub-CPU 0x400-0x4FF) writes bit 6 of PAYLOAD_LOADED_FLAG (0x4FE); no E3 command is sent
7. Sub CPU boot ROM calls payload at 0x000400

See [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/) for detailed protocol documentation.

#### Subsystem Initialization

After the sub CPU payload is loaded:

| Subsystem | Description |
|-----------|-------------|
| Display | VGA-compatible LCD controller at 0x1A0000 |
| Control Panel | Serial communication with MCU (SC1, 250kHz) |
| FDC | Floppy disk controller at 0x110000 |
| MIDI | External MIDI I/O |
| HDAE5000 | Hard disk expansion (if present) at 0x160000 |

#### Welcome Screen and Boot Animation

After subsystem initialization and Sub CPU payload loading, the firmware displays a welcome screen. The exact screen shown depends on two factors: a **power-on button combination scan** and the **Sub CPU payload transfer result**.

**Power-on button scan** (`CPanel_ScanButtons` / `CPanel_CheckSpecialCombos`): At early boot (before the welcome screen), the firmware scans the control panel buttons. If specific combinations are held during power-on, special boot modes are activated:

| Button Combination                                 | Code | Effect                                                                                                                                                    |
|----------------------------------------------------|------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| No special combo                                   | 0    | Normal boot — splash animation                                                                                                                            |
| SHOWTIME & TRAD DANCE + PARTY TIME + MARCH & WALTZ | 1    | Factory reset (Initial Setting): only when DRAM[0xFFCA] != 0x5AA5, `Boot_HandleFactoryReset` zero-fills work DRAM and the IC21 SRAM and restarts the boot |
| GM SPECIAL + ACCORDION REGISTER + DIGITAL DRAWBAR  | 2    | Firmware version on the panel LEDs (`Boot_HandleComboDisplay`) and the MPVersion screen (`EVT_MP_VERSION`)                                                |
| AUTO PLAY CHORD + SPLIT POINT + VAR4 + VAR3        | 3    | SOFT VERSION screen: MAIN PROGRAM, MAIN TABLE, SUB PROGRAM and SOUND TABLE numbers (`Boot_HandleComboDisplay` opens view 0xF0)                            |
| PM1 + PM2 + PM3 + PM4 (all 4 Panel Memory buttons) | 4    | Firmware flash update mode                                                                                                                                |

The scanned combo code is stored in internal RAM at address 0x402 (byte at offset 1026).

**Welcome screen decision tree** (in `AcWelcomScreenProc` at 0xF7F4A6):

```
EVT_SHOW (0x1C00001):
    │
    ├─ Get_Region_Code
    │  Region 2 → WelcomeScript_Steps_A (0xE9DF4E)
    │  Other    → WelcomeScript_Steps_B (0xE9E806)
    │
    ├─ Boot_GetButtonComboCode (RAM 0x402)
    │  │
    │  ├─ Combo == 2 → "MPVersion" screen (firmware version)
    │  │               (posts EVT_MP_VERSION 0x1C10009)
    │  │
    │  └─ Combo != 2 → SubCPU_Payload_GetErrorFlag
    │     │
    │     ├─ Negative (0xFF: checksum of DRAM 0xF980 != DRAM[0xFFD2]) →
    │     │      "ALL INITIAL SETTING!" screen
    │     │      (posts EVT_ALL_INITIAL 0x1C10004 → "AllInitial" view)
    │     │
    │     └─ 0 or 1 → Normal splash animation
    │                 (sends EVT_SET_KEEP 0x1E000B3)
```

**Normal splash animation**: On a successful boot with no special buttons held, the firmware displays a splash screen with the Technics/KN5000 logo and animated palette effects (palette cycling, spotlight-like illumination). The animation uses region-specific data tables — Region 2 uses different graphics than other regions. The boot code reaches it through `ScreenGroup_Dispatch` (0xFDDB46), which runs one init phase of every subsystem (see [Subsystem Init Phases](#subsystem-init-phases)); the drawing is done by the subsystems' phase handlers.

The welcome screen's letters are **in the program ROM** (the nakarest lane, September 2026).
`AcWelcomScreenProc` (0xF7F4A6) runs a small **welcome script**: 12-byte steps
`{delay, x, y, op, arg}` interpreted by `AcWelcomScreen_RenderBytecode` through a 13-entry
op table. There are two step tables: table A (186 steps) is used when `Get_Region_Code`
returns 2, table B (191 steps) otherwise. The ops draw seven 16×17 1-bpp glyphs (C, I, L, N,
O, R, U; rows stored bottom-up, drawn by `DrawBitmapSP2_Impl`) one letter at a time. Table A
spells **IN COLOR**, table B **IN COLOUR**. The glyphs sit under older labels that predate this
reading (`Bitmap_Digit1` is the I, `Bitmap_DigitD` the U). The Technics logo (312×45,
`Bitmap_Technics_Logo`) and the KN-5000 logo (199×36, `Bitmap_KN5000_Logo`) are ROM bitmaps
too. Source: the welcome-script headers in `v10/maincpu/ui_widgets/technichord_string_data.s`
and `welcome_step_t` in `naka_technichord_strings.c`. This page used to say the assets were
pre-rendered bitmaps on the boot floppy (`FTBMP01`–`FTBMP06`). Those six are the
[Feature Demo]({{ site.baseurl }}/feature-demo/)'s slides, stored in the table-data ROM at `0x880418`-`0x8CE01B`.

**"ALL INITIAL SETTING!" screen**: the welcome screen opens it (`EVT_ALL_INITIAL`, view `AllInitial`) when `SubCPU_Payload_GetErrorFlag` is negative (0xFF). `SubCPU_Payload_Verify` sets 0xFF when the checksum of DRAM `0xF980` (0x280 bytes) does not match the value the power-off NMI stored at `0xFFD2`. A mismatch of the `0xF180` region alone gives 1, which the welcome screen treats as success. A cold start with no saved power-down state therefore shows this screen. Holding combo 2 (GM SPECIAL + ACCORDION REGISTER + DIGITAL DRAWBAR) opens the `MPVersion` screen instead and shows the firmware version on the panel LEDs.

> **MAME Note**: In MAME, as on hardware, a cold boot with no saved power-down checksums shows "ALL INITIAL SETTING!". The kn7000_mame overlay's modelled POWER switch lets the firmware's own NMI handler save them, so the next boot shows the splash. See [SNS NMI Emulation]({{ site.baseurl }}/sns-nmi-emulation/).

#### Sub CPU Payload Verification and the SNS (Power-Off) NMI

After the Main CPU transfers the 192KB Sub CPU firmware payload, `SubCPU_Payload_Verify` (0xEF092B) verifies it by computing one's-complement checksums of two DRAM regions and comparing them against reference values:

| Region   | DRAM range | Size                | Reference stored at |
|----------|------------|---------------------|---------------------|
| Region 1 | 0xF180     | 0x800 bytes (2 KB)  | DRAM[0xFFD4]        |
| Region 2 | 0xF980     | 0x280 bytes (640 B) | DRAM[0xFFD2]        |

`Checksum_ComputeComplement` sums each region as 32-bit longwords and complements the low 16 bits of the sum.

**How reference checksums are stored**: `Boot_DisplayScreen` (0xEF0620) arms the NMI guard by writing `0x80` to internal CPU RAM[0x0400], then immediately clears `DRAM[0xFFD4] = 0`. On real hardware, the **SNS signal** (the power supply's "SNS" monitoring line) asserts the CPU's `~NMI` pin when power is removed. The NMI handler (at 0xEF08A5) calls `NMI_StorePayloadChecksums` (0xEF08D4), which:

1. Checks the NMI guard (internal RAM[0x0400] == 0x80); returns immediately if not set
2. Saves voice presets and flush data to SRAM
3. Computes checksums for both regions and stores them at DRAM[0xFFD4/0xFFD2]
4. Copies DRAM[0xF980..] to backup SRAM at 0x1E8000
5. Executes `halt` (machine powers off)

This means: every **clean power-off** stores fresh checksums; every **boot** clears them (`Boot_DisplayScreen`); the NMI at the *previous* power-off provides the values for `SubCPU_Payload_Verify` at the *next* boot.

> **MAME Implementation**: the kn7000_mame overlay models the instrument's POWER switch. Pressing it pulses the CPU's ~NMI and gives the firmware's own `NMI_StorePayloadChecksums` a power-down window before MAME exits (kn7000_mame `84aba70`, 2026-08-15). An earlier boot-time write tap on DRAM[0xFFD4] was removed (`b1cf7db`, 2026-07-20) because it caused the "Sound Name Error". Mainline MAME models neither. See [SNS NMI Emulation]({{ site.baseurl }}/sns-nmi-emulation/).

#### Battery-Backed SRAM Validation

During boot, the firmware validates the battery-backed SRAM at 0x1E0000-0x1FFFFF:

1. Reads 0x24B8 little-endian 16-bit words from 0x1E0010
2. Computes a one's complement checksum
3. Compares against the stored checksum at offset 0x72A8
4. Before the checksum, compares the 16-byte header at 0x1E0000 with "KN5000 SOUND RAM" only (the "KN3000 SOUND RAM" and "KN1500 SOUND RAM" identifiers are recognised by a different routine, `SendPartDataBlock_InitVal4`, which the sound-RAM data handlers use; this boot check does not)

If both checks pass, the routine (`SendPartDataBlock_ClearByte4`) bulk-transfers the 0x72AA-byte image at 0x1E0000 to sub-CPU 0x7800; if either fails, it sends the sub CPU a 0xFF/0xFF packet instead and shows no message (`v10/maincpu/audio/note_voice_mapping.s:26502-26532`). The **"ERROR in back-up SRAM"** screen (view `TEST1RAM`) comes from a different check: the boot self-test `SelfTest_SramAndRom` posts it only when the 0x5A/0xA5 write test `Test_SRAM_IC21` fails (`v10/maincpu/ui/ui_mode_handlers.s:1657-1679`). The factory defaults are embedded in Program ROM at offset 0x0A0150 (0x72A6 bytes, starting with "KN5000 SOUND RAM" header).

The kn7000_mame overlay driver implements this with a custom NVRAM handler (`kn5000_state::nvram_init`) that copies the factory defaults and computes the checksum on first run; mainline MAME declares a plain `NVRAM(config, "nvram")` without it.

#### Main Loop

The main CPU enters its event loop, handling:
- User interface events
- Control panel button/encoder input
- MIDI I/O
- Disk operations
- Display updates

### Subsystem Init Phases

`ScreenGroup_Dispatch` (WA = slot 0-3) walks `Subsys_HandlerTableList`, 19 tables of four routine pointers, one per
subsystem, and calls `table[WA]` of each, in list order. The boot code calls it four times:

| Call | When | Slot |
|------|------|------|
| 1 | right after `SubCPU_Send_Payload` / `SubCPU_Payload_Verify` (also runs `ScreenGroup_InitState` before and `ScreenGroup_ReInit` after) | 0 |
| 2 | `SubCPU_Payload_GetErrorFlag` = 0 | 1 |
| 2 | `SubCPU_Payload_GetErrorFlag` != 0 (also `MainSysCtrl_DispatchTable` entry 0) | 2 |
| 3 | after `(1024) = 6` | 3 |

The audio subsystem's table confirms the reading: `Audio_InitAllDefaults`, `Audio_ReinitToneGenAndOutput`,
`Audio_ResetAfterPayloadError`, `Audio_FullReinitWithPreset`. Older pages called WA a "screen group ID"
(0 = initial boot screen, 2 = error screen, ...). The routine draws nothing itself. Several table names below
predated this reading and said nothing about the subsystem. Since 2026-10-06 they are named after the subsystem
they serve: `VGA_InitFuncTable` (was `WidgetStyleDataTable`), `PanelEvent_InitPhaseHandlers` (was
`SoundParam_EncoderMappingData`; its phase-0 handler, still called `Encoder_MarkInvalid`, empties the panel event
queue at RAM 0xC039), `FileIO_InitFuncTable` (was `DiskOp_ChannelCfgTable`) and `PanelInput_InitFuncTable` (was
`EffectMode_DispatchTable`).

| # | Table | Slot 0 | Slot 1 | Slot 2 | Slot 3 |
|---|-------|--------|--------|--------|--------|
| 0 | `Seq_InitFuncTable` | `Seq_FullInit` | `Seq_InitStub_Nop2` | `Seq_InitStub_Nop1` | `Seq_InitStub_Nop3` |
| 1 | `Subsys_HandlerTable01` | `COMM_ResetSentValues` | `COMM_ResetSentValues_Phase1` | `CommParam_SetComplete_Return2` | `CommParam_SetComplete_Return3` |
| 2 | `WidgetDispatch_FDTestPtrTable` | `Xapr_DetectOnInit` | `Xapr_InitPhase1_NullRet` | `Xapr_InitPhase2_NullRet` | `Xapr_InitPhase3_NullRet` |
| 3 | `MIDI_SC0_DISPATCH_TABLE` | `SC0Init_Entry` | `SC0Init_PaddingStub` | `SC0Init_PaddingStub` | `SC0Init_PaddingStub` |
| 4 | `SeqFormat_HandlerTable` | `SoundMode_ResetJump2` | `SoundMode_RetStub_A` | `SoundMode_RetStub_B` | `SoundMode_RetStub_C` |
| 5 | `NakaInst_SoundConfig_LookupTable` | `MIDI_INIT_SEQUENCES` | `MidiInit_Stub1` | `MidiInit_Stub2` | `MidiInit_Stub3` |
| 6 | `SoundProgram_ParamPtrTable` | `Audio_InitAllDefaults` | `Audio_ReinitToneGenAndOutput` | `Audio_ResetAfterPayloadError` | `Audio_FullReinitWithPreset` |
| 7 | `FileIO_InitFuncTable` | `FileIO_DiskInserted` | `FileIO_DiskInserted_Stub1` | `FileIO_DiskInserted_Stub2` | `FileIO_DiskRemoved` |
| 8 | `VGA_InitFuncTable` | `VGA_Initialize` | `VGA_Stub_1` | `VGA_Stub_2` | `VGA_Stub_3` |
| 9 | `PanelInput_InitFuncTable` | `PanelInput_InitPedalRecords` | `Audio_NullHandler_A` | `Audio_NullHandler_B` | `Audio_NullHandler_C` |
| 10 | `PanelEvent_InitPhaseHandlers` | `Encoder_MarkInvalid` | `Encoder_Stub1` | `Encoder_Stub2` | `Encoder_Stub3` |
| 11 | `Subsys_HandlerTable11` | `SoundData_InitPhase0` | `Param_SignExtendRetu_Return` | `Param_SignExtendRetu_Return` | `Param_SignExtendRetu_Return` |
| 12 | `WidgetData_CharsetMappingTable` | `SeqInit_SetBaseAddress` | `SeqInit_ReturnStub` | `SeqInit_JumpToPartInit` | `SeqInit_FullReset` |
| 13 | `SeqByteBlock_DispatchJumpTable` | `SeqDispatch_ResetAndValidate` | `SeqDispatch_ReturnNop` | `SeqDispatch_InitWithPayload` | `SeqDispatch_ReturnNop` |
| 14 | `AccompSeq_InitFuncTable` | `AccompSeq_ResetToFactoryBanks` | `AccompSeq_VoiceResetStub` | `AccompSeq_InitBankIfNoError` | `AccompSeq_VoiceResetStub` |
| 15 | `AccPatch_InitFuncTable` | `AccTone_StubReturn_B` | `AccTone_StubReturn_A` | `AccDemo_InitDone` | `AccPatch_InitAndCountSlots` |
| 16 | `SoundRam_HandlerTable` | `SendPartDataBlock_ClearByte4` | `SendPartDataBlock_Return4` | `SendPartDataBlock_DoGetError` | `SendPartDataBlock_Return5` |
| 17 | `FDemoText_InitFuncTable` | `FDemoText_StubReturn_A` | `FDemoText_StubReturn_B` | `FDemoText_StubReturn_C` | `FDemoText_RescanAllVoices` |
| 18 | `CharMap_Preamble_Table` | `CharMap_NullPreamble_0` | `CharMap_NullPreamble_1` | `CharMap_NullPreamble_2` | `CharMap_ActivePreamble` |

Source: `boot/screen_group_dispatch.s` and `ui_widgets/widget_dispatch.s` (`Subsys_HandlerTableList`);
`scripts/tools/label_subsys_init_tables.py` in the disassembly repository.

### Complete Boot Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                         POWER ON / RESET                             │
│                                                                      │
│  Initial Memory Map:                                                 │
│    0xE00000-0xFFFFFF = Table Data ROM (contains first-stage boot)    │
│    Program ROM not yet visible                                       │
└──────────────────────────────────────────────────────────────────────┘
                                   │
                                   v
┌──────────────────────────────────────────────────────────────────────┐
│                   STAGE 1: TABLE DATA BOOTLOADER                     │
│                                                                      │
│  1. CPU fetches reset vector from 0xFFFF00 (table_data @ 0x1FFF00)   │
│  2. Vector points to 0xFFFEE0 → JP 0xFFB4E8                          │
│  3. Boot code configures MSAR0-5, MAMR0-5, DRAM controller           │
│  4. Memory remap: Table Data → 0x800000, Program ROM → 0xE00000      │
│  5. Jump via 0xFFFEDC to Boot_InitIOPorts (0xEF050F)                 │
└──────────────────────────────────────────────────────────────────────┘
                                   │
                                   v
┌──────────────────────────────────────────────────────────────────────┐
│                    STAGE 2: PROGRAM ROM BOOT                         │
│                                                                      │
│  Final Memory Map:                                                   │
│    0x000000-0x0FFFFF = DRAM (1MB)                                    │
│    0x100000-0x1FFFFF = I/O (FDC, latches, VGA, SRAM)                 │
│    0x300000-0x3FFFFF = Custom Data Flash                             │
│    0x400000-0x7FFFFF = Rhythm Data ROM                               │
│    0x800000-0x9FFFFF = Table Data ROM (remapped)                     │
│    0xE00000-0xFFFFFF = Program ROM (now visible)                     │
│                                                                      │
│  1. Boot_InitIOPorts at 0xEF050F (RESET_HANDLER 0xEF03C6 skipped)    │
│  2. Remaining hardware init (shared init block already run)          │
│  3. Release Sub CPU from reset                                       │
│  4. Send 192KB payload to Sub CPU                                    │
│  5. Initialize subsystems and enter main loop                        │
└──────────────────────────────────────────────────────────────────────┘
```

### Implications for MAME Emulation

The discovery of the two-stage boot process has significant implications for accurate MAME emulation:

#### Current Driver (Incorrect)

The current MAME driver uses a static memory map:
```cpp
map(0x800000, 0x9fffff).rom().region("table_data", 0);
map(0xe00000, 0xffffff).rom().region("program", 0);
```

This assumes the Program ROM is always at 0xE00000, which is only true **after** the memory controller is configured.

#### Required Fix

For accurate emulation, the MAME driver needs to:

1. **On reset**: Map Table Data ROM at 0xE00000-0xFFFFFF
2. **Emulate MSAR/MAMR register writes**: When the bootloader writes to memory controller registers (0x0142-0x0157), update the address mapping dynamically
3. **After reconfiguration**: Program ROM becomes visible at 0xE00000, Table Data at 0x800000

#### Workaround

If implementing dynamic remapping is complex, a workaround might be to:
- Pre-configure the memory map to the final state
- Patch the table_data reset vector to jump directly to Program ROM's RESET_HANDLER

However, this violates the project's strict accuracy policy and may cause issues with code that expects the original boot sequence.

> **Update (August 2026).** What MAME does today is effectively the second workaround
> without the patch: it maps the program flash at the top, so reset reads
> `program[0x1FFF00]` and starts at `0xEF03C6`. The static map equals the post-handover
> steady state, so this is *accidentally* correct rather than wrong — but everything
> reachable only through the bootloader is dead code under emulation.
>
> Two refinements to the "required fix" above. First, only **one** register changes at
> runtime (`MSAR2`), so a two-state `memory_view` reproduces the behaviour without
> implementing a full chip-select decoder — which is just as well, because the exact
> `MSAR`/`MAMR` decode rule is **not established**. Second, the interrupt vector table is
> ROM-resident at `0xFFFF00` and swaps identity with the ROM, so code and vectors must
> switch atomically.
>
> See [MAME Emulation Gaps]({{ site.baseurl }}/mame-emulation-gaps/) for the dependency
> order, and [TMP94C241 Memory Controller]({{ site.baseurl }}/tmp94c241-memory-controller/)
> for the measured register values.

### SubCPU_Send_Payload Details

The `SubCPU_Send_Payload` routine at **0xEF068A** is responsible for transferring the Sub CPU firmware during boot. This section provides implementation details; see [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/#subcpu_send_payload-0xef068a) for full code examples.

#### Memory Map State at Execution

When `SubCPU_Send_Payload` is called, the memory map has been configured by the Stage 1 bootloader with these settings:

**Memory Controller Configuration (MSAR/MAMR Registers):**

| Register | Value | Resulting Mapping |
|----------|-------|-------------------|
| MSAR0 | 0x1E | Block 0 starts at 0x1E0000 (SRAM) |
| MSAR1 | 0x10 | Block 1 starts at 0x100000 (I/O) |
| MSAR2 | 0xC0 → **0x80** | Block 2 — moved by `Boot_PrepareJump` |
| MSAR3 | 0x00 | Block 3 starts at 0x000000 (DRAM) |
| MSAR4 | 0x80 | Block 4 starts at 0x800000 |
| MSAR5 | 0x00 | Block 5 starts at 0x000000 |

> **Caveat.** The right-hand column reads `MSAR` literally as a base address and ignores
> the `MAMR` mask, which determines block *size* and how many address bits are compared.
> That is safe enough for blocks whose start is size-aligned but is not a decode. The exact
> mask semantics are **not established** — see
> [TMP94C241 Memory Controller]({{ site.baseurl }}/tmp94c241-memory-controller/), where
> the measured values, the reconstruction and its limits are recorded. Note also that by
> the time `SubCPU_Send_Payload` runs, `MSAR2` has already been changed to `0x80`.

**Effective Memory Map:**

| Address Range     | Component          | Notes                                                       |
|-------------------|--------------------|-------------------------------------------------------------|
| 0x000000-0x0FFFFF | DRAM (1MB)         | Main CPU working RAM                                        |
| 0x100000-0x1DFFFF | I/O Peripherals    | FDC, LCD, Latch, etc.                                       |
| 0x1E0000-0x1FFFFF | SRAM (IC21)        | Battery-backed static RAM, 128 KB                           |
| 0x300000-0x3FFFFF | Custom Data Flash  | IC19, believed to sit in the CS5 block (provisional decode) |
| 0x800000-0x9FFFFF | **Table Data ROM** | Contains the tone database at offset 0x30000                |
| 0xE00000-0xFFFFFF | Program ROM        | Currently executing code                                    |

**Address Resolution for Key Accesses:**

- **0x830000** → Table Data ROM offset 0x30000 (tone database — data for the Sub CPU, *not* its executable)
- **0x8E0000** → Table Data ROM offset 0xE0000 (LZSS compressed preset data)
- **0x3E0000** → Custom Data Flash offset 0xE0000 (firmware update staging area)

#### Control Flags

Two bytes in Program ROM control the payload transfer behavior:

| Address | ROM Offset | Value | Effect |
|---------|------------|-------|--------|
| 0xFFFEEF | 0x1FFEEF | **0xFF** | Payload transfer proceeds |
| 0xFFFEEE | 0x1FFEEE | **0x00** | `Boot_CallInitHandlers` is *disabled* (would need 0xFF) |
| 0xFFFEED | 0x1FFEED | **0xFF** | LZSS decompression from 0x3E0000 is attempted |

Measured `FF FF FF 00 FF` at 0x1FFEEB-0x1FFEEF in **v7, v9 and v10** — the chooser does not
differ across firmware versions.

#### Transfer Sequence

| Step | Source Address | Destination | Size | Notes |
|------|----------------|-------------|------|-------|
| 1-5 | 0x830000-0x870000 | Sub CPU 0x050000-0x090000 | 5 × 64KB | Tone database from Table Data ROM (data), sent unconditionally |
| 6 | 0x3E0000 | Main CPU DRAM 0x050000 | 192KB out | SLIDE4K decompression of the **sub-CPU payload** |
| 7 | Buffer + 0x100 | Main CPU 0x0404 | 2 bytes | Copies word to Main CPU RAM |
| 8-10 | Buffer/Fallback | Sub CPU 0x00F000-0x02F000 | 0x10000 + 0x10000 + 0xFF00 | The executable |
| 11 | Buffer + 0x000 | Sub CPU 0x000400 | 256 bytes | 45 jump trampolines — overwrites the boot ROM's own |

> Step 6 previously read "~33 KB of optional LZSS preset data". It is not preset data and
> it is not optional on any dumped firmware: it is the 192 KB sub-CPU executable, and steps
> 8-11 total exactly `0x30000` = 196,608 bytes. A File Type 007 update writes that image to
> custom-data `0x3E0000`; why our IC19 dump lacks it is still open — see
> [Sub-CPU Payload Provenance]({{ site.baseurl }}/subcpu-payload-provenance/).

#### Timing

The routine includes two delay loops for hardware timing:
- **Initial delay**: 0x2000 (8,192) iterations before the first transfer
- **Final delay**: 0x100000 (1,048,576) iterations after the last block, before the routine returns

#### LZSS Decompression of the Sub-CPU Executable {#lzss-preset-data-handling}

After the five unconditional 64 KB tone-database transfers, the routine chooses the base of the executable:

**Code Flow:**
```asm
LD XIZ, TABLE_DATA_ROM__BASE_ADDR    ; Default: 0x800000
CP (0xFFFEED), 0xFF                  ; Check decompression flag
JR NZ, skip_decompress               ; Skip if flag != 0xFF

; Attempt LZSS decompression from Custom Data Flash
LD XIZ, 0x050000                     ; Output buffer (DRAM)
LD XWA, 0x3E0000                     ; Source: Custom Data Flash!
CALL SLIDE_Parse_Header                    ; Decompress
CP HL, 0xFFFF                        ; Check for failure
JR NZ, skip_decompress               ; Success: use decompressed data
LD XIZ, TABLE_DATA_ROM__BASE_ADDR    ; Failure: fall back to ROM

skip_decompress:
; Use data at XIZ+0x100 for subsequent transfers
```

**Key Finding: Address 0x3E0000 is NOT in Table Data ROM**

The address `0x3E0000` maps to **Custom Data Flash** (0x300000-0x3FFFFF), NOT Table Data ROM. It is believed to sit in the CS5 chip-select block (`MSAR5 = 0x00`, `MAMR5 = 0xFF`), with board glue logic dividing that block between IC19, IC14 and the HD-AE5000 window; the decode is provisional, see [TMP94C241 Memory Controller]({{ site.baseurl }}/tmp94c241-memory-controller/).

| Address  | Maps To                          | Normal Boot State                                                                                            |
|----------|----------------------------------|--------------------------------------------------------------------------------------------------------------|
| 0x3E0000 | Custom Data Flash offset 0xE0000 | SLIDE4K image of the sub-CPU executable, written by a File Type 007 (or 005) update (blank in our IC19 dump) |
| 0x8E0000 | Table Data ROM offset 0xE0000    | LZSS compressed preset data                                                                                  |

**Boot Behavior:**

| Scenario                                 | 0x3E0000 Contents | Decompression  | Data Source                                                    |
|------------------------------------------|-------------------|----------------|----------------------------------------------------------------|
| **After firmware update**                | Valid LZSS data   | Succeeds       | Custom Data Flash (updated firmware)                           |
| **Blank 0x3E0000** (as in our IC19 dump) | All 0xFF          | Fails (0xFFFF) | Table Data 0x800000 fallback: picture data, sub-CPU cannot run |

**Firmware Update Integration:**

The File Type 007 handler (`HANDLE_UPDATE_FILE_TYPE_ID_007h` at 0xEF47FA) writes compressed Sub CPU payload to Custom Data Flash:

```asm
; "Technics KN5000 Program DATA FILE PCK"
HANDLE_UPDATE_FILE_TYPE_ID_007h:
    LD WA, 1                    ; Select Custom Data Flash
    LD XBC, 003e0000h           ; Destination: 0x3E0000
    CALL Flash_EraseSectorWithBankSelect           ; Flash write routine
    LD WA, 1
    LD XBC, 003f0000h           ; Destination: 0x3F0000
    CALL Flash_EraseSectorWithBankSelect           ; Flash write routine
```

This explains the design:
1. **Firmware updates** write compressed payload to Custom Data Flash at 0x3E0000
2. **On next boot**, `SubCPU_Send_Payload` decompresses the updated firmware
3. **Without an image at 0x3E0000** the fallback base 0x800000 ships picture data, so the sub-CPU cannot run (the provenance page discusses why our IC19 dump is blank there)

> **✅ RESOLVED:** The 0x3E0000 address mystery is now understood. See [Firmware Update System]({{ site.baseurl }}/lzss-compression/#firmware-update-system-and-0x3e0000) for full details.

#### Related Routines

| Routine                       | Address  | Purpose                                   |
|-------------------------------|----------|-------------------------------------------|
| `SubCPU_Init_DMA_Channels`    | 0xEF329E | Must be called before payload transfer    |
| `InterCPU_E1_Bulk_Transfer`   | 0xEF3457 | Underlying protocol for each 64KB chunk   |
| `SubCPU_Payload_Verify`       | 0xEF092B | Verifies payload checksums after transfer |
| `SubCPU_Payload_GetErrorFlag` | 0xEF0979 | Returns error status for boot sequence    |

#### Error Handling

If the checksum verification fails:
1. `SubCPU_Payload_Verify` sets error flag at `0x01E53E`
2. Boot sequence reads flag via `SubCPU_Payload_GetErrorFlag`
3. A non-zero result makes the boot run init phase 2 instead of phase 1 (`ScreenGroup_Dispatch(2)`, see [Subsystem Init Phases](#subsystem-init-phases)); a negative one (0xFF) also makes the welcome screen open "ALL INITIAL SETTING!" (see [Welcome Screen and Boot Animation](#welcome-screen-and-boot-animation))
4. The "ERROR in CPU data transmission" view (`TEST1CP`, message line `ErrorDialog_CPUTransmissionError` at 0xED66C4) is not opened from this path: the boot self-test `SelfTest_SramAndRom_CheckROM` posts it when `CPanel_ProbePanelMcus` reports a control-panel MCU that did not answer (`v10/maincpu/ui/ui_mode_handlers.s:1681-1717`)

#### Source Code Reference

Assembly: `v10/maincpu/kn5000_v10_program.s` (`SubCPU_Send_Payload` through `SubCPU_Payload_Done`)

```asm
; Entry point
SubCPU_Send_Payload:                ; 0xEF068A
    PUSH XIZ
    CP (0xFFFEEF), 0xFF              ; Check if transfer should proceed
    JRL NZ, SubCPU_Payload_Done             ; Skip if not 0xFF
    ; ... 5 x 64KB transfers via InterCPU_E1_Bulk_Transfer ...
    ; ... LZSS decompression handling ...
    ; ... Final data blocks to Sub CPU ...
    POP XIZ
    RET
```

### Subprogram Storage Location {#subprogram-storage-location-under-investigation}

> ⚠ **Retraction (2026-08).** This section previously read "RESOLVED" and stated that the
> Sub CPU's 192 KB executable is stored uncompressed at Table Data ROM `0x830000`. That is
> **wrong and is withdrawn.** `0x830000-0x87FFEF` is the **tone database** — sound-parameter
> data, copied into the Sub CPU's *data* window. Where the executable comes from at run time
> is a separate question, answered below; only the IC19 dump's provenance is still open. See
> [Tone Database]({{ site.baseurl }}/tone-database/) and
> [SubCPU Payload Loading]({{ site.baseurl }}/subcpu-payload-loading/).

**What the 320 KB transfer actually carries: the tone database**

| Source | Address | ROM Offset | Size | Destination |
|--------|---------|------------|------|-------------|
| Table Data ROM | 0x830000-0x87FFEF | 0x30000-0x7FFEF | 320KB | Sub CPU **data** RAM 0x050000-0x09FFFF |

`SubCPU_Send_Payload` moves this as 5×64KB chunks via `InterCPU_E1_Bulk_Transfer`. Its
contents are the factory tone/voice records, drum kits, percussion bank, wave-source name
catalogues and envelope pool — not code.

**Where the executable comes from: the mechanism is closed, the dump provenance is not**

The same routine transfers the code blocks (Sub CPU `0x400` and `0xF000`-`0x3EEFF`) from a
base held in `XIZ`: the LZSS image at Custom Data Flash `0x3E0000` if it decompresses, and
table-data `0x800000` otherwise. In the images this project holds, **neither is the
payload** — custom-data `0x3E0000` is blank (all `0xFF`; whether the region was never
programmed or the dump is incomplete cannot be told from the file — see
[Sub-CPU Payload Provenance]({{ site.baseurl }}/subcpu-payload-provenance/)), and no byte of
`kn5000_subprogram_v142.rom` appears anywhere in the table-data or custom-data dumps. The
executable is known only from its own ROM dump and from the compressed update-disc images.

**LZSS Compressed Region at 0x8E0000 (Preset Parameters, NOT Executable):**

There is SLIDE4K compressed data at Table Data ROM offset 0x0E0000 (address 0x8E0000 after remap):

```
Address: 0x8E0000 (Table Data ROM, post-remap)
Header:  "SLIDE4K" + 0x00 + 0x00 + 0x95 + 0x00 + "}Z" + 0xEE
Format:  LZSS SLIDE4K compressed
```

**Important Finding:** This compressed region does **NOT** contain the Sub CPU executable:
- Decompresses to 38,144 bytes (0x9500): demo-song preset 18, read by the demo code into main-CPU RAM `0x69800`
- Sub CPU ROM (`kn5000_subprogram_v142.rom`) is ~192KB
- Decompressed bytes are mostly MIDI-range values (0-127), not code

**Address 0x3E0000 Clarification:**

The code references `0x3E0000` for LZSS decompression, but this address maps to **Custom Data Flash** (not Table Data ROM):

| Address  | Memory Region                      | Typical Contents                                                                                             |
|----------|------------------------------------|--------------------------------------------------------------------------------------------------------------|
| 0x3E0000 | Custom Data Flash (offset 0xE0000) | SLIDE4K image of the sub-CPU executable, written by a File Type 007 (or 005) update (blank in our IC19 dump) |
| 0x8E0000 | Table Data ROM (offset 0xE0000)    | LZSS compressed preset data                                                                                  |

If the image at 0x3E0000 fails its SLIDE check, the code falls back to `TABLE_DATA_ROM__BASE_ADDR` (0x800000). That region is the section directory and bitmap bank, so a working sub-CPU needs the image; see [Sub-CPU Payload Provenance]({{ site.baseurl }}/subcpu-payload-provenance/).

**Remaining Open Questions:**

1. What data is at `0x830000`? **Answered:** the tone database (data, not code).
2. ~~Where does the ~192 KB executable come from?~~ **Answered (August 2026):** from the
   SLIDE4K stream a File Type 007 update disc writes verbatim to custom-data `0x3E0000`,
   decompressed on every boot. What is open is why the IC19 dump lacks it; see
   [Sub-CPU Payload Provenance]({{ site.baseurl }}/subcpu-payload-provenance/).
3. Does the Sub CPU have its own ROM chip? **Yes** — the 128 KB Sub CPU Boot ROM (IC30)
   holds the boot loader. It does *not* hold the 192 KB runtime payload.
4. ~~What is the purpose of the preset data at 0x8E0000, and when is it used?~~ **Answered
   (September 2026):** it is demo-song preset 18, the Feature Demo's. `DemoSongPreset_PointerTable[18]`
   points at it, and `Demo_ParseSlideHeader` decompresses it (38,144 bytes) into main-CPU RAM
   `0x69800` like presets 0-17. `SubCPU_Send_Payload` does not read it.
5. **What does the `0x800000` fallback ship?** `0x800000` is the section directory and a bank of
   8bpp bitmaps whose transparent colour is `0xF7`, so the fallback sends picture data to the
   Sub CPU. This is a strong lead on the "Preset Data Destination" dispute, not confirmed in
   MAME; see [LZSS Compression]({{ site.baseurl }}/lzss-compression/#preset-data-destination-dispute).
6. ~~Under what conditions does the 0x3E0000 LZSS path succeed?~~ **Answered:** whenever a
   File Type 007 (or 005) update has written the SLIDE4K image there; see
   [Sub-CPU Payload Provenance]({{ site.baseurl }}/subcpu-payload-provenance/).

See [LZSS Compression](lzss-compression.md) for decompression details.

---

## Sub CPU Boot Sequence

The sub CPU has a dedicated 128KB boot ROM (`kn5000_subcpu_boot.ic30`) that initializes hardware and waits for the payload.

### 1. Reset Vector (0xFFFEE0)

The sub CPU's reset vector jumps to `BOOT_INIT` at `0xFF8290`.

### 2. Hardware Initialization (BOOT_INIT)

```
Address: 0xFF8290
Size: ~400 bytes
```

**Initialization steps:**

| Step | Registers                    | Values           | Purpose                                                                     |
|------|------------------------------|------------------|-----------------------------------------------------------------------------|
| 1    | WDMOD_REAL                   | 0x00             | Disable watchdog                                                            |
| 2    | CLKMOD (0x10A)               | 0x04             | Clock mode (the source's unused equate for 0x10A is `INT_CTRL`)             |
| 3    | P1FC-P3FC                    | 0xFF             | Ports 1-3 all function mode                                                 |
| 4    | P7, P7FC, P7CR               | Various          | Port 7 configuration                                                        |
| 5    | P8, P8FC, P8CR               | Various          | Port 8 (chip select)                                                        |
| 6    | PA, PAFC, PB, PBFC           | Various          | DRAM signals                                                                |
| 7    | PC, PCFC, PCCR               | 0x03, 0x00, 0x02 | Port C (SFR 0x30, formerly misnamed `INTTC01`)                              |
| 8    | PD-PF, PH, PZ (data, CR, FC) | Various          | Ports D, E, F, H and Z (0x34-0x3E were formerly misnamed SC0/SC1 registers) |
| 9    | T01MOD, T23MOD               | Various          | Timer modes                                                                 |
| 10   | MSARx, MAMRx                 | Various          | Memory controller                                                           |
| 11   | SER0/SER1                    | Various          | Serial channels                                                             |
| 12   | DRAM_*                       | Various          | DRAM refresh/timing                                                         |
| 13   | BxCSL, BxCSH                 | Various          | Bus chip select                                                             |

### 3. Copy Interrupt Vectors (COPY_VECTORS)

```
Address: 0xFF846D
Source: 0xFF8F6C (ROM)
Destination: 0x0400 (RAM)
Size: 225 bytes (0xE1 bytes)
```

The boot ROM copies interrupt vector trampolines from ROM to RAM. These are placeholder handlers that jump back to boot ROM until the actual payload overwrites them:

```asm
COPY_VECTORS:                  ; 0xFF846D
    LD   XDE, 0x00000400       ; Destination: RAM at 0x0400
    LD   XHL, 0x00FF8F6C       ; Source: ROM stub table
    LD   XBC, 0x000000E1       ; Count: 225 bytes
    LDIR                       ; Block copy
    RET
```

### 4. Enable Interrupts

```asm
ei 0    ; Enable interrupts at level 0
```

### 5. Initialization Routines

| Routine          | Address  | Size  | Purpose                                                                                                                                      |
|------------------|----------|-------|----------------------------------------------------------------------------------------------------------------------------------------------|
| INIT_MEMORY_TEST | 0xFF8956 | ~300B | Returns at once unless bit 0 of 0x30 is clear (strap); then RAM test, ROM checksum, TG probe and an endless loop — not part of a normal boot |
| INIT_DMA_SERIAL  | 0xFF85AE | ~90B  | DMA and serial setup                                                                                                                         |
| INIT_TONE_GEN    | 0xFF84A8 | ~70B  | DSP register block at 0x130000 (the routine's name says tone generator, but it is not)                                                       |

### 6. Main Loop (Wait for Payload)

```
Address: 0xFF840C
```

The sub CPU enters a loop waiting for the payload ready flag:

```asm
MAIN_LOOP:
    res  6, (SUBCPU_STATUS_FLAGS)    ; Clear ready flag
.wait_loop:
    bit  6, (SUBCPU_STATUS_FLAGS)    ; Check if payload ready
    jr   Z, .check_status
    ei   6                            ; Enable interrupt level 6
    call PAYLOAD_ENTRY               ; Call payload at 0x0400
.check_status:
    ; Update serial status
    jr   .wait_loop
```

### 7. Payload Execution

Once `PAYLOAD_LOADED_FLAG` bit 6 is set (by the last 256-byte block, which overwrites 0x400-0x4FF), the sub CPU jumps to the payload entry point at `0x0400`. The payload takes over audio synthesis and tone generation duties.

---

## Inter-CPU Communication Protocol

The main CPU and sub CPU communicate through a pair of 8-bit latches (IC22/IC23), at `0x140000` on the main CPU's bus and `0x120000` on the sub CPU's.

### Command Format

| Command        | Description                               | Data Size      | Buffer          |
|----------------|-------------------------------------------|----------------|-----------------|
| any other byte | Variable-length data (handler = bits 7-5) | Low 5 bits + 1 | CMD_DATA_BUFFER |
| 0xE1           | Two-phase transfer setup                  | 6 bytes        | CMD_E1_BUFFER   |
| 0xE2           | Parameter block                           | 10 bytes       | CMD_E2_BUFFER   |
| 0xE3           | Payload complete                          | 0 bytes        | -               |

### Variable-Length Commands (any other byte)

```
Bits 7-5: Handler index (0-7) from jump table at 0xFF8000
Bits 4-0: Data length - 1 (so 0x00 = 1 byte, 0x1F = 32 bytes)
```

That jump table is `CmdHandler_Table`, and every one of its eight entries is a
`ld hl,0:i3 / ret` stub: before the payload arrives the sub-CPU acknowledges the entire
command set and implements none of it. See
[Sub-CPU Boot ROM (IC30)]({{ site.baseurl }}/subcpu-boot-rom/#the-command-handler-jump-table-at-0xff8000).

### Handshaking Signals (INTERCPU_STATUS at 0x34)

| Bit | Direction | Meaning |
|-----|-----------|---------|
| 0 | Sub → Main | Sub CPU ready flag |
| 1 | Internal | Completion signal from interrupt |
| 2 | Internal | Gate for command processing |
| 4 | Main → Sub | Main CPU ready flag |

### DMA State Machine (DMA_XFER_STATE at 0x0516)

| State | Meaning |
|-------|---------|
| 0 | Idle - no transfer in progress |
| 1 | Single transfer - waiting for completion |
| 2 | Two-phase transfer - phase 1 done, phase 2 pending |

### Transfer Flow

```
Main CPU                          Sub CPU
   │                                 │
   │  1. Write command to latch      │
   │  ─────────────────────────────> │
   │                                 │  2. InterCPU_RX_Handler
   │                                 │     triggered
   │                                 │
   │  3. Wait for sub ready          │  4. Set up DMA
   │  <───────────────────────────── │     destination
   │                                 │
   │  5. Send data bytes             │
   │  ─────────────────────────────> │  6. DMA receives data
   │                                 │
   │  7. Check completion            │  8. DMA_Complete_Handler
   │  <───────────────────────────── │     clears state
   │                                 │
```

---

## Boot ROM Routines Reference

### DMA Transfer Routines (0xFF8604-0xFF881E)

| Routine | Address | Size | Description |
|---------|---------|------|-------------|
| SendData_Chunked | 0xFF8604 | 69B | Break large transfers into 32-byte chunks |
| InterCPU_SendChunk | 0xFF8649 | 99B | Send single block with handshaking |
| SendCmd_E3 | 0xFF86AC | 48B | Signal payload complete |
| SendParams_E2 | 0xFF86DC | 112B | Send E2 parameter block |
| TwoPhase_Transfer | 0xFF874C | 211B | Execute E1 two-phase sequence |

### Interrupt Handlers

| Handler | Address | Description |
|---------|---------|-------------|
| InterCPU_RX_Handler | 0xFF881F | Receives commands from main CPU |
| DMA_Complete_Handler | 0xFF889A | Advances DMA state machine |
| CMD_Dispatch_Handler | 0xFF88B8 | Processes received commands |
| DEFAULT_HANDLER | 0xFF8432 | Default handler (just RETI) |

### Utility Routines

| Routine          | Address  | Description                                                            |
|------------------|----------|------------------------------------------------------------------------|
| COPY_VECTORS     | 0xFF846D | Copy interrupt trampolines to RAM                                      |
| INIT_TONE_GEN    | 0xFF84A8 | Initialize the 0x130000 DSP register block (not the tone generator)    |
| TONE_GEN_WRITE   | 0xFF84F1 | Write the 8 registers of one 0x130000 channel (not the tone generator) |
| CHECKSUM_CALC    | 0xFF859B | Calculate memory checksum                                              |
| MEM_TEST_ROUTINE | 0xFF89FC | RAM test with patterns                                                 |
| ROM_CHECKSUM     | 0xFF8AB4 | Verify boot ROM integrity                                              |

---

## Memory Map During Boot

### Sub CPU RAM Layout

| Address | Size | Symbol               | Description                                                           |
|---------|------|----------------------|-----------------------------------------------------------------------|
| 0x0400  | 225B | PAYLOAD_ENTRY        | Interrupt vector trampolines                                          |
| 0x04FE  | 1B   | PAYLOAD_LOADED_FLAG  | Payload ready flags                                                   |
| 0x0502  | 10B  | DMA_SETUP_PARAMS     | DMA parameter block                                                   |
| 0x050C  | 6B   | E1_XFER_PARAMS       | E1 command parameters                                                 |
| 0x0512  | 4B   | DMA_TARGET_ADDR      | Current DMA destination                                               |
| 0x0516  | 2B   | DMA_XFER_STATE       | DMA state machine                                                     |
| 0x0518  | 2B   | CMD_PROCESSING_STATE | Command processing phase                                              |
| 0x051A  | 1B   | LAST_CMD_BYTE        | Last received command                                                 |
| 0x051E  | 32B  | CMD_DATA_BUFFER      | Variable-length command data                                          |
| 0x053E  | 10B  | E2_XFER_PARAMS       | E2 command parameters                                                 |
| 0x0544  | 6B   | CMD_E1_BUFFER        | E1 command buffer                                                     |
| 0x054A  | 10B  | CMD_E2_BUFFER        | E2 command buffer                                                     |
| 0x0556  | 1B   | MEMTEST_RESULT       | Memory test result                                                    |
| 0x0558  | 8B   | SERIAL_STATUS        | Key-down bitmap (the equate keeps an older name; not a serial buffer) |
| 0x05A2  | -    | STACK_INIT           | Initial stack pointer                                                 |

### Hardware Addresses

| Address  | Description                                                                                               |
|----------|-----------------------------------------------------------------------------------------------------------|
| 0x100000 | Tone generator IC303 register interface (address 0x100000, data 0x100002, status 0x100004)                |
| 0x110000 | Tone generator keybed event data (status at 0x110002, P6.7 selects)                                       |
| 0x120000 | Inter-CPU communication latch                                                                             |
| 0x130000 | DSP register block (address/data; MAME maps it to DSP1 IC311). The boot ROM's `INIT_TONE_GEN` writes here |

### Sub CPU Payload Command Dispatch

After payload loading, the `MICRODMA_CH0_HANDLER` at 0x020F1F processes commands using `CMD_DISPATCH_TABLE`:

| Handler | Command Range | Address  | Purpose                                |
|---------|---------------|----------|----------------------------------------|
| 0       | 0x00-0x1F     | 0x034D5F | MIDI/audio data to ring buffer         |
| 1       | 0x20-0x3F     | 0x01FC7C | No-op (returns immediately)            |
| 2       | 0x40-0x5F     | 0x01FC7F | Skip N bytes (data drain)              |
| 3       | 0x60-0x7F     | 0x035893 | DSP streaming data                     |
| 4       | 0x80-0x9F     | 0x01F890 | Serial port 1 (SC1) TX                 |
| 5       | 0xA0-0xBF     | 0x03CFEE | Keybed touch curve / forwarding enable |
| 6-7     | 0xC0-0xFF     | 0x020C12 | No-op (returns immediately)            |

---

## Timing Considerations

### Boot Time Estimates

| Phase         | Duration   | Notes                                                                                                                         |
|---------------|------------|-------------------------------------------------------------------------------------------------------------------------------|
| Hardware init | ~1ms       | SFR configuration                                                                                                             |
| Memory test   | ~10ms      | RAM pattern test (diagnostic strap only; skipped in a normal boot)                                                            |
| ROM checksum  | ~5ms       | 4KB verification (diagnostic strap only; skipped in a normal boot)                                                            |
| Tone gen init | ~1ms       | 4 channel setup                                                                                                               |
| Payload load  | ~100ms     | 512 KB through the latch: 5 × 64 KB tone database, then the 192 KB executable                                                 |
| **Total**     | **~100ms** | To payload execution in a normal boot. With the strap, `INIT_MEMORY_TEST` ends in an endless loop and never loads the payload |

These durations are unmeasured estimates.

### DMA Transfer Rates

- Latch clock: Tied to timer frequency
- Typical chunk size: 32 bytes
- Timeout: 60,000 iterations (~300ms at 20MHz)

### MAME Emulation Timing

> **Status: Boot fully working** as of 2026-02-17. The SubCPU payload loads (524K HDMA transfers), executes, initializes audio hardware, and communicates bidirectionally with the Main CPU. Required 12 fixes to MAME's TMP94C241 emulation and the KN5000 driver. See [SubCPU Payload Loading]({{ site.baseurl }}/subcpu-payload-loading/) for the full fix history.

Accurate emulation of the inter-CPU protocol requires careful CPU scheduling. See [Inter-CPU Protocol: MAME Emulation Notes]({{ site.baseurl }}/inter-cpu-protocol/#mame-emulation-notes) for details on:
- Latch pending state management (force-clear before each write)
- INT0 level-detect stale `m_level` fix (`clear_int0_level()`)
- CPU timeslice interleaving for latch transfers

---

## Error Handling

### Memory Test Errors (MEMTEST_RESULT)

| Bit | Meaning                                                     |
|-----|-------------------------------------------------------------|
| 0   | Low half-word RAM mismatch                                  |
| 1   | High half-word RAM mismatch                                 |
| 2   | ROM checksum mismatch                                       |
| 3   | Tone-generator probe failed (HARDWARE_CALIBRATION_SEQUENCE) |

### DMA Timeouts

All DMA routines have 60,000 iteration timeouts (~300ms). On timeout:
- Transfer is abandoned
- Ready flag is set
- Control returns to caller

### HALT_LOOP (0xFF8490)

Fatal error handler that drives port E bit 0 low and halts the CPU:

```asm
HALT_LOOP:
    res  0, (PE)        ; PE.0 low (the payload drives PE.0 as its tentative MUTE line; older notes read SFR 0x38 as SC0MOD, "disable serial")
.halt:
    halt                ; Halt CPU
    jr   T, .halt       ; Loop forever
```

---

## HD-AE5000 Initialization (Optional)

Port E bit 0 (low = board present) gates only the PPI init: `Boot_FlashAndExtensions` calls `HDAE5000_Parport_Setup` when PE.0 = 0 and the region code is not 4. The extension ROM itself is found by its "XAPR" signature at 0x280000, with no PE.0 test. `Xapr_DetectOnInit` (init phase 0) sets `XAPR_PRESENT_FLAG` on a match. `Xapr_DetectAndCallBootInit` (the tail of `ScreenGroup_ReInit`) re-checks the signature, sets or clears the flag, and calls `0x280008` when it is set.

### Detection and Entry

```
Boot_FlashAndExtensions: PE.0 = 0 and region != 4 → HDAE5000_Parport_Setup (PPI only)

ScreenGroup_ReInit → Xapr_DetectAndCallBootInit   (no PE.0 test)
    ├─> "XAPR" not at 0x280000: XAPR_PRESENT_FLAG = 0, skip
    └─> "XAPR" at 0x280000:     XAPR_PRESENT_FLAG = 1
            → CALL 0x280008 (Boot_Init, XWA = 0x027ED2)
```

### HDAE5000_Boot_Init (0x28F576)

The firmware passes workspace pointer **`0x027ED2`** in XWA. This is the base of the firmware's object table -- a structure with 14-byte entries spanning to `0x02BC12` (~1,118 entries) in main DRAM.

The XAPR validation routine at `Xapr_DetectAndCallBootInit` handles detection and initialization:

```asm
; Validate XAPR signature at 0x280000
PUSHW 0004h                          ; Compare 4 bytes
PUSHW LoadExtROM_JumpEntry_Data@hi16
PUSHW LoadExtROM_JumpEntry_Data@lo16 ; "XAPR" (0xE1FFC6)
LD    XWA, 00280000h                 ; Extension ROM base
PUSH  XWA
CALL  String_Compare
ADD   XSP, 0000000ah
CP    HL, 0
JR    NZ, .no_extension

LD    (XAPR_PRESENT_FLAG), 001h      ; 0x03DD04 (cleared to 0 when absent)

; Call Boot_Init with workspace pointer
LD    XHL, 00280008h                 ; Boot_Init entry point
LDA   XWA, 027ED2h                  ; Workspace pointer
CALL  T, XHL                        ; Boot_Init(XWA = 0x027ED2)
RET
```

The boot initialization performs these steps:

| Step | Action | Details |
|------|--------|---------|
| 1 | Clear work buffer | Zero 0xF52A bytes at 0x22A000, copy the 0x0C82-byte initialised `.data` image from ROM 0x2F94B2 to 0x23952A |
| 2 | Store workspace | Save workspace pointer (0x027ED2) at 0x23A1A2 |
| 3 | Register 11 object tables and title 0x7F | Via `workspace[0x0E0A][0x00E4]` (`RegisterObjectTable`), then `workspace[0x0E0A][0x0270]` = `RegisterTitle(0x7F, ..., "TT_HDDEXT", module 0x0A)` |
| 4 | Load palette | Load 256-entry VGA palette from ROM at 0x2E5DCE |
| 5 | Blit the boot splash | Copy the 320×240 8bpp splash at ROM 0x2E61CE into VRAM as two 0x9600-byte halves, to 0x1A0000 and 0x1A9600 — this is the "HD-AE5000 / Version 2 / Start-up ! / Please wait . . ." screen |
| 6 | Claim the DISK MENU item | `workspace[0x0E0A][0x02C4]` = `GetViewInstance(0x00600002)`; write class id `0x016A0005` at +0 and the "HD-AE5000" string at +0x2A |
| 7 | Fetch sequencer-variable addresses | `workspace[0x0E88]` offsets 0x0108, 0x0100, 0x0104 = `GetAdr_sqsrtc`, `GetAdr_sqbtof`, `GetAdr_sq_beadt`; results at 0x230ECC / 0x230ED2 / 0x230ED6 |
| 8 | Check HD presence | `HDAE5000_Check_HD_Present`, result stored at 0x230EDA. If the result is **non-zero**, post `ApPostEvent(0xFFFFFFFF, 0x01C00016, 0x01A0007F)`, a request for title 0x7F (see note) |
| 9 | Reset UI state | `HDAE5000_Finalize_Init` (a `ret`), then `HDAE5000_UiState_Reset` at 0x2803C2 |

**Note on step 8.** `HDAE5000_Check_HD_Present`'s header says its result is
`HDAE5000_HD_Init`'s step code: 0 = drive up and formatted, non-zero = the step
that failed (1 unformatted, 3 no drive, …). Read that way, Boot_Init requests
the HD title only when the drive is *not* ready. The comments at the call site
("Skip if no HD", "drive present: go to the HD title") read the result the other
way round. The two readings have not been reconciled. Listed on
[Open Questions]({{ site.baseurl }}/questions/).

**Important:** Steps 1-5 must complete before step 6. The record `GetViewInstance` returns is re-classed as the HD-AE5000's `HDTitleMenu`, which exists only after the class table `0x016A` has been registered in step 3.

### Frame Handler Dispatch

The frame handler dispatcher at `Xapr_CallFrameHandler` runs every main loop iteration:

```asm
CP    (03DD04h), 000h           ; Check XAPR detection flag
RET   Z                         ; Skip if no extension
LD    XHL, 00280010h            ; Frame handler entry point
CALL  T, XHL                   ; Call Frame_Handler()
RET
```

The frame handler is called **unconditionally** -- no registration is needed. The flag at `0x03DD04` is the only gate.
In the source it is `XAPR_PRESENT_FLAG` (each maincpu tree's `shared/ram_variables.s`, 0x03DD04 in v7, v9 and v10).

### Workspace Dispatch System

The workspace pointer at `0x027ED2` provides access to the firmware's callback dispatch system:

```
Workspace (0x027ED2) = the object table, 14-byte entries {class id, proc, count, data}
    |
    +-- +0x0E0A = data of table 0x100: InitializeRoot's Function table (0xEAFA6E)
    |       +0x00DC InheritedProc      +0x00E4 RegisterObjectTable
    |       +0x0100 SendEvent          +0x0104 PostEvent     +0x0124 ApPostEvent
    |       +0x0168 ClassProc          +0x0244/0248/024C Function/ApFunction/MainFunctionProc
    |       +0x0270 RegisterTitle      +0x02C4 GetViewInstance    ... (41 offsets used)
    |
    +-- +0x0E88 = data of table 0x109: InitializeHama's Function table (0xE1F0EC)
            +0x0100 GetAdr_sqbtof      +0x0104 GetAdr_sq_beadt    +0x0108 GetAdr_sqsrtc
            ... (58 offsets used)
```

The names are the firmware's own, read from the name tables the main CPU
registers beside each function table (0x400 and 0x409). The HD-AE5000 source
spells every call as `RootFn_<name>` / `HamaFn_<name>`. The earlier diagram here
called `+0x0124` a "display callback", `+0x02C4` a "callback registration
function" and table B's entries "init functions"; all three were wrong.

HDAE5000 registers **11** object tables with `RegisterObjectTable` and one title
with `RegisterTitle`. Each table is identified by a **class id** and an
object-table index; `0x0160000n` is a class id, not a "port address". The
module number is 0x0A. See
[HDAE5000 Homebrew — Complete Handler Table]({{ site.baseurl }}/hdae5000-homebrew/#complete-handler-table). See [HDAE5000 Homebrew Development]({{ site.baseurl }}/hdae5000-homebrew/) for details on the workspace protocol and writing custom extension ROMs.

### Frame Handler (0x28F662)

After initialization, the main CPU calls the frame handler periodically:

1. While a lyric box is open, read the main CPU's song position through the
   `sqbtof` / `sq_beadt` addresses fetched at boot and post it to the box
   (event `0x01CA0004`, `EV_TICKS`) when it changes
2. When bit 2 of the main CPU's `sqsrtc` byte falls to 0 and
   `HDAE5000_Get_Status_Byte` returns 1, either post the file-load events (if
   the HD title 0x7F is current, `GetTitleNow` = `0x01A0007F`) or request title
   0x7F (`HDAE5000_RequestTitle15`)
3. Jump to the PC-link handler (`HDAE5000_PPORT_ServicePending`)

(Details: `HDAE5000_Frame_Handler`'s header in `hdae5000/hdae5000_ui_display.s`
and [HDAE5000 Filesystem — Lyric Files]({{ site.baseurl }}/hdae5000-filesystem/#lyric-files-tlx).)

---

## Subsystem Initialization Order

After boot completes, subsystems initialize roughly as below; the authoritative order is the `Subsys_HandlerTableList` order in [Subsystem Init Phases](#subsystem-init-phases):

```
Sub CPU Payload Loaded (last 256-byte block)
    │
    v
┌─────────────────────────────────────────────┐
│         Main CPU Subsystem Init             │
├─────────────────────────────────────────────┤
│  1. Display System (VGA controller)         │
│     - Configure MN89304 at 0x170000         │
│     - Set 320×240 resolution                │
│     - Load default palette                  │
│                                             │
│  2. Control Panel (Serial Channel 1)        │
│     - 250kHz clock, 8-bit mode              │
│     - Initialize button/encoder states      │
│     - Start polling loop                    │
│                                             │
│  3. Floppy Disk Controller (0x110000)       │
│     - Detect drive presence                 │
│     - Initialize FDC state machine          │
│                                             │
│  4. HDAE5000 (if present)                   │
│     - Call 0x280008 for initialization      │
│     - No registration: XAPR_PRESENT_FLAG    │
│                                             │
│  5. MIDI I/O                                │
│     - Configure serial channels             │
│     - Initialize message buffers            │
└─────────────────────────────────────────────┘
    │
    v
    Main Event Loop
```

---

## System Runtime

### Main Event Loop

After all initialization completes, the main CPU enters its event loop:

```
┌─────────────────────────────────────────────────────────┐
│                    MAIN EVENT LOOP                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Control   │    │   Display   │    │    MIDI     │  │
│  │   Panel     │───>│   Update    │───>│  Processing │  │
│  │   Poll      │    │             │    │             │  │
│  └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                  │                  │         │
│         v                  v                  v         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │    FDC      │    │  HDAE5000   │    │   Audio     │  │
│  │   Handler   │───>│   Frame     │───>│   Sync      │  │
│  │             │    │   Handler   │    │             │  │
│  └─────────────┘    └─────────────┘    └─────────────┘  │
│                           │                             │
│                           v                             │
│                    Loop continues                       │
└─────────────────────────────────────────────────────────┘
```

### Control Panel Communication

The control panel uses a serial protocol at 250kHz:

| Direction | Data | Purpose |
|-----------|------|---------|
| Main → Panel | Button LED states | Update indicator LEDs |
| Panel → Main | Button presses | User input events |
| Panel → Main | Encoder deltas | Rotary encoder changes |

See [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) for detailed protocol documentation.

### Inter-CPU Communication (Runtime)

During runtime, the main CPU sends commands to the sub CPU for audio operations:

| Command Range | Purpose                                |
|---------------|----------------------------------------|
| 0x00-0x1F     | MIDI/audio data to ring buffer         |
| 0x20-0x3F     | No-op                                  |
| 0x40-0x5F     | Skip N bytes (data drain)              |
| 0x60-0x7F     | DSP streaming data                     |
| 0x80-0x9F     | Serial port 1 (SC1) TX                 |
| 0xA0-0xBF     | Keybed touch curve / forwarding enable |
| 0xC0-0xFF     | No-op                                  |

### HDAE5000 PPORT Polling

If HD-AE5000 is present, its frame handler checks for PC parallel port commands:

1. Check PPORT status register at 0x239000
2. If active, load parameters from 0x23900A-0x239010
3. Call `HDAE5000_PPORT_ServiceDispatch` (0x29511C) and `HDAE5000_PPORT_ReturnToLink` (0x2950CC)
4. Process command from `HDAE5000_PPORT_Cmd_Table` (0x2953E2)

Available PPORT commands include file transfers, HD formatting, and PC communication.

---

## Complete Boot Timeline

```
Time    Event
─────   ─────────────────────────────────────────────────
0ms     Power On
        ├── Main CPU reset vector → hardware init
        └── Sub CPU reset vector → hardware init

1ms     Hardware configured
        ├── Main CPU: Ports, memory controller, timers
        └── Sub CPU: Serial, DMA, tone generator

10ms    (diagnostic strap only) Sub CPU RAM pattern test, ROM checksum

15ms    Sub CPU waiting for payload
        └── Main CPU: Begin payload transfer

115ms   Payload loaded (192KB via DMA)
        └── Last 256-byte block sets bit 6 of 0x4FE

120ms   Sub CPU executing payload
        ├── Audio engine active
        └── Command dispatch ready

150ms   Main CPU subsystem init
        ├── Display initialized
        ├── Control panel connected
        └── FDC ready

200ms   HDAE5000 init (if present)
        ├── 32KB RAM test
        ├── HD detection
        └── XAPR_PRESENT_FLAG set (frame handler called every loop)

250ms   System Ready
        └── Main event loop running
```

---

## See Also

- [Memory Map]({{ site.baseurl }}/memory-map/) - Complete address space documentation
- [Reverse Engineering]({{ site.baseurl }}/reverse-engineering/) - Technical details
- [ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/) - Build status and known issues
- [Flash Programming]({{ site.baseurl }}/flash-programming/) - Flash memory programming routines and update system
- [HDAE5000 Hard Disk Expansion]({{ site.baseurl }}/hdae5000/) - HD-AE5000 firmware details
- [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) - Serial communication with control panel (runtime driver)
- [Boot CP-Serial Link]({{ site.baseurl }}/boot-cpserial-link/) - The bootloader's own, independent CP-serial driver
- [FDC Subsystem]({{ site.baseurl }}/fdc-subsystem/) - Both FDC drivers, including the bootloader's
