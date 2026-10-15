---
layout: page
title: Reverse Engineering
permalink: /reverse-engineering/
---

# Reverse Engineering Strategies

Documented approaches for understanding undocumented aspects of the KN5000 system.

## Working Method

How a finding becomes committed source is documented separately, on the
[Disassembly Workflow]({{ site.baseurl }}/disassembly-workflow/) page: the byte-match
invariant, the audit that scopes each round of work, the evidence standard for calling a
blob "code" (including the shifted-decode control), and the parallel-workers /
single-integrator shape that let thirty-three conversion packages land in August 2026
without the byte-match gate ever slipping.

Three rules from that page are worth repeating here, because they apply to any
investigation on this hardware:

- **A claim is not accepted because it looks right.** Every "this region is X" assertion is
  checked against a control that should fail if the claim is wrong — a decode at the wrong
  offset, a null measurement, a consumer census that must tile the region exactly.
- **A search proves something only once you have shown it could have found the thing.** Two
  of the larger corrections in these pages began as an empty grep that was briefly believed:
  all twenty-four memory-controller registers *are* programmed, but the disassembler writes
  their addresses in decimal (`ld (323:16), 30`, never `0x143`); and the DSP effect-name
  strings were never missing from the sources, they were `uint16_t` members inside a
  C-compiled blob. A third trap needs no history to be dangerous: `grep` declines to read
  five of the v7 sources at all, because a high byte inside an `.ascii` string makes them
  invalid UTF-8, and reports no matches with exit status 1. Build a positive control before
  believing a zero.
- **Corrections are published, not quietly dropped.** Several long-standing descriptions in
  these pages were wrong (a "flash update handler" region that is really the bootloader's
  FDC driver; an "exponential pitch table" that is really a mixer gain curve). Where that
  has happened, the page says so.

## HDAE5000 Hard Disk Expansion

The HD-AE5000 is an optional hard disk expansion that provides 1.08GB storage for music files. **See the [dedicated HDAE5000 page]({{ site.baseurl }}/hdae5000/) for complete documentation** including PPORT commands, entry points, and firmware analysis.

### Key Findings Summary

| Property | Value |
|----------|-------|
| ROM File | `hd-ae5000_v2_06i.ic4` (512KB) |
| Base Address | 0x280000 |
| Internal Version | 2.33J (Juli-Oktober 1996, M. Kitajima) |
| PPI Address | 0x160000-0x160006 |

### ROM Entry Points

| Address | Target | Description |
|---------|--------|-------------|
| 0x280008 | JP 0x28F576 | Boot initialization |
| 0x280010 | JP 0x28F662 | Frame handler (PPORT polling) |

### PPI Interface (0x160000)

The main CPU communicates with the HDAE5000 via an 8255 PPI (Programmable Peripheral Interface).

**PPI Port Addresses:**

| Address | Port | Direction | Function |
|---------|------|-----------|----------|
| 0x160000 | Port A | Output | Data output |
| 0x160002 | Port B | Input | Status input |
| 0x160004 | Port C | Output | Control signals |
| 0x160006 | Control | Write | PPI configuration |

**PPI Control Register Value: 0x82**
- Bit 7 = 1: Mode set active
- Port A: Mode 0, Output
- Port B: Mode 0, Input
- Port C: Output (both nibbles)

**Port C Control Signals:**

| Bit | Function | Usage |
|-----|----------|-------|
| 0 | Strobe | SET 0 / RES 0 for pulse |
| 1 | Secondary strobe | Secondary handshake |
| 2 | Data direction/select | CHG 2 toggles |
| 3 | Control signal | CHG 3 toggles |

**Initialization Sequence (HDAE5000_Parport_Setup at 0xEF4BCC):**

```
1. B5CSL = 0x66 (bus timing for HDAE5000)
2. Control Register = 0x82 (configure PPI)
3. Port A = 0x00 (clear output)
4. Port C = 0x00, then 0x0F (pulse control signals)
5. Delay loop (0xDBBA0 iterations)
6. Port C = 0x00 (clear control)
7. Poll Port B bit 0 until clear (wait for ready)
```

**HDAE5000 Detection (at 0xEF05B0):**

```asm
BIT 0, (PE)           ; Check PE port bit 0
JR NZ, BootInit_SeqAndPanel ; If set, HD-AE5000 NOT present
CALR Get_Region_Code
CP L, 4               ; Check region code
CALL NZ, HDAE5000_Parport_Setup ; Init if present
```

PE.0 (active low) gates only `HDAE5000_Parport_Setup`. The XAPR header check at 0x280000 and the call to the extension's Boot_Init (0x280008) run regardless, through `ScreenGroup_ReInit` → `Xapr_DetectAndCallBootInit`.

### PPORT Commands (Documented)

The PC-link command table `HDAE5000_PPORT_Cmd_Table` (0x2953E2) has 20 slots, handled by `HDAE5000_PPORT_Cmd01_SendInfosAboutHd` … `HDAE5000_PPORT_Cmd20_SendXapFileFlash`; slots 12, 15 and 19 are empty:

| Code  | Command              | Description                            |
|-------|----------------------|----------------------------------------|
| 01    | Send Infos About HD  | Report HD info to PC                   |
| 02    | Exit PPORT           | End session                            |
| 03-06 | FSB Operations       | Read/Write File System Block           |
| 07-11 | Data Transfer        | Load/Save between HD, memory, PC       |
| 13-14 | Data / info transfer | Receive data from PC, send infos to PC |
| 16-18 | HD Management        | Delete, Format, Motor off              |
| 20    | Send XapFile flash   | XAP file transfer                      |

### Registered object names

Names such as `LyricBackColorCheck`, `ErrMsgTimerCatch` and `AttenHDFormatSwCatch` are entries in the HD-AE5000 firmware's own 69-entry object registry, not callbacks of the PC software. See [HDAE5000 Resources]({{ site.baseurl }}/hdae5000-resources/#the-69-object-registry). The command handlers, the FSB structure and the disk protocol are documented on [HDAE5000]({{ site.baseurl }}/hdae5000/#pport-command-protocol), [HDAE5000 Filesystem]({{ site.baseurl }}/hdae5000-filesystem/) and [HDAE5000 Disk Interface]({{ site.baseurl }}/hdae5000-disk-interface/).

---

## Sub CPU Payload Loading

The main CPU (TMP94C241F) loads a 192KB executable payload to the sub CPU (IC27) at boot time using MicroDMA.

### MicroDMA Mechanism

The TMP94C241F has a built-in MicroDMA controller with 4 channels (0-3).

**DMA Registers:**

The channel registers `DMASn` (source, 32-bit), `DMADn` (destination, 32-bit),
`DMACn` (count, 16-bit) and `DMAMn` (mode, 8-bit) are CPU control registers with
no memory address: only `LDC` reaches them, through the selector byte listed
below. The memory-mapped DMA registers are the start vectors `DMAV0`–`DMAV3` at
0x100–0x103, which name the interrupt that starts a transfer on each channel,
and the software request register `DMAR` at 0x109 (MAME `tmp94c241.cpp`). 0x110
is the watchdog mode register `WDMOD`, not a DMA register.

**DMA Mode Register Bits (DMAMn):**

| Bits | Function      | Values                                                                                                                                                                                                                                                                            |
|------|---------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 4-2  | Transfer mode | 000 = destination increment, source fixed (I/O to memory); 001 = destination decrement, source fixed; 010 = source increment, destination fixed (memory to I/O); 011 = source decrement, destination fixed; 100 = both fixed; 101 = counter (source increments, nothing is moved) |
| 1-0  | Data size     | 00 = byte, 01 = word, 10 = long                                                                                                                                                                                                                                                   |

**LDC Instruction Encoding for DMA Registers:**

DMA registers are accessed via special `LDC` (Load Control) instructions. The LLVM backend spells them `ldc_cr8` / `ldc_cr16` / `ldc_cr32 <register>, <selector>` (e.g. `ldc_cr32 xwa, 0x28` = `e8 2e 28`); the native `ldc dmad2, xwa` is not parsed:

| Instruction | Encoding | Description |
|-------------|----------|-------------|
| `LDC DMAS0, XWA` | `E8 2E 00` | Load source ch0 from XWA |
| `LDC DMAD0, XWA` | `E8 2E 20` | Load dest ch0 from XWA |
| `LDC DMAC0, WA` | `D8 2E 40` | Load count ch0 from WA |
| `LDC DMAS2, XDE` | `EA 2E 08` | Load source ch2 from XDE |
| `LDC DMAD2, XWA` | `E8 2E 28` | Load dest ch2 from XWA |
| `LDC DMAC2, BC` | `D9 2E 48` | Load count ch2 from BC |

**Third Byte Encoding (DMA register selector):**

| Value | Register | Description               |
|-------|----------|---------------------------|
| 0x00  | DMAS0    | Source, Channel 0         |
| 0x08  | DMAS2    | Source, Channel 2         |
| 0x0C  | DMAS3    | Source, Channel 3         |
| 0x20  | DMAD0    | Destination, Channel 0    |
| 0x28  | DMAD2    | Destination, Channel 2    |
| 0x2C  | DMAD3    | Destination, Channel 3    |
| 0x40  | DMAC0    | Count, Channel 0 (16-bit) |
| 0x42  | DMAM0    | Mode, Channel 0 (8-bit)   |
| 0x48  | DMAC2    | Count, Channel 2 (16-bit) |
| 0x4A  | DMAM2    | Mode, Channel 2 (8-bit)   |
| 0x4C  | DMAC3    | Count, Channel 3 (16-bit) |
| 0x4E  | DMAM3    | Mode, Channel 3 (8-bit)   |

**Sub CPU Boot ROM DMA Usage:**
- **Channel 0**: Latch reads (source=0x120000 fixed, dest=RAM incrementing)
- **Channel 2**: Payload transfers (configurable source/dest)
- **DMAV2** (0x0102, named `DMA_BURST_CTRL` in the boot source) = 0x16: channel 2 starts on INTT2, so the payload transfers are paced by timer 2, which the code starts with `set 2, (T8RUN)`
- **DMAV0** (0x0100) = 0x0A: channel 0 starts on INT0, the inter-CPU latch interrupt (the MAME driver wires the latch's data-pending line to the sub CPU's INT0)

**DMA Transfer Routines (Sub CPU Boot ROM):**

| Routine | Address | Size | Function |
|---------|---------|------|----------|
| SendData_Chunked | 0xFF8604 | 69B | Sends data in 32-byte chunks |
| InterCPU_SendChunk | 0xFF8649 | 99B | Single block with handshaking |
| SendCmd_E3 | 0xFF86AC | 48B | Payload ready signal |
| SendParams_E2 | 0xFF86DC | 112B | Wait then send E2 command |
| TwoPhase_Transfer | 0xFF874C | 211B | Two-phase transfer with E1 |

### Inter-CPU Communication (0x120000)

The main and sub CPUs communicate through a pair of 8-bit latches (IC22/IC23, one per direction), which the sub CPU addresses at `0x120000` and the main CPU at `0x140000`.

**Command Encoding:**

| Byte Range | Format | Description |
|------------|--------|-------------|
| 0x00-0x1F | `HHHLLLLL` | Handler (bits 7-5) + data length-1 (bits 4-0) |
| 0xE1 | Fixed | Multi-stage DMA, 6-byte param block at 0x0544 |
| 0xE2 | Fixed | Payload transfer, 10-byte param block at 0x054A |
| 0xE3 | Fixed | Payload ready signal |

**Handshaking Register (INTERCPU_STATUS at SFR 0x34):**

| Bit | Name | Description |
|-----|------|-------------|
| 0 | SUB_READY | Sub CPU ready to receive |
| 1 | COMPLETION | Transfer complete signal |
| 2 | GATE | Processing gate for InterCPU_RX_Handler |
| 4 | MAIN_READY | Main CPU ready (polled by sub) |

**Transfer Sequence (Sub CPU → Main CPU):**

```
1. Poll MAIN_READY (bit 4) until set
2. Clear SUB_READY (bit 0)
3. Write command byte to 0x120000
4. Poll MAIN_READY for acknowledgment
5. Set SUB_READY, initiate DMA
6. Wait for COMPLETION (bit 1) via interrupt
```

**Status Flags (SUBCPU_STATUS_FLAGS at 0x04FE):**
- Bit 6: Payload data ready
- Bit 7: Transfer complete

**No checksumming** observed in protocol - relies on handshaking for reliability.

### Boot Sequence

**Confirmed flow (from firmware analysis):**

1. Main CPU initializes after reset (see Reset Vector section)
2. Sub CPU boot ROM runs from 0xFF8290 (BOOT_INIT)
3. Sub CPU configures DMA for inter-CPU latch at 0x120000
4. Sub CPU waits for payload via `InterCPU_RX_Handler` (the INT0 inter-CPU latch interrupt)
5. Main CPU sends payload via DMA transfers
6. Sub CPU receives E3 command (payload ready signal)
7. Sub CPU jumps to payload entry point via trampoline at 0x0400
8. Sub CPU signals ready to main CPU via INTERCPU_STATUS

**Sub CPU Boot ROM Key Routines:**

| Address  | Routine              | Function                                                                                                                    |
|----------|----------------------|-----------------------------------------------------------------------------------------------------------------------------|
| 0xFF8290 | BOOT_INIT            | Hardware initialization entry                                                                                               |
| 0xFF846D | COPY_VECTORS         | Copy trampolines to RAM (0x0400)                                                                                            |
| 0xFF85AE | INIT_DMA_SERIAL      | Configure DMA for latch                                                                                                     |
| 0xFF84A8 | INIT_TONE_GEN        | Initialize the 4-channel × 8-register block at 0x130000 (the payload's DSP register base; the routine's name is historical) |
| 0xFF881F | InterCPU_RX_Handler  | INT0 (inter-CPU latch) interrupt                                                                                            |
| 0xFF88B8 | CMD_Dispatch_Handler | INTTC0 (micro-DMA channel 0 completion) interrupt                                                                           |
| 0xFF889A | DMA_Complete_Handler | INTTC2 (micro-DMA channel 2 completion) interrupt                                                                           |

### Payload Structure

The sub CPU payload (`v142/subcpu/kn5000_subprogram_v142.s` and its sibling files) is 192KB.

**Key State Variables:**

| Address | Symbol | Description |
|---------|--------|-------------|
| 0x04FE | `PAYLOAD_LOADED_FLAG` | Shared with boot ROM (bit 6: ready, bit 7: complete) |
| 0x10E8 | `DMA_XFER_STATE` | DMA transfer state: 0=idle, 1=single, 2=two-phase |
| 0x10EA | `CMD_PROCESSING_STATE` | Command processing phase (0-4) |
| 0x10EC | `BYTE_FROM_MAINCPU_LATCH` | Last received command byte |

**MicroDMA Interrupt Handlers:**

| Handler | Address | Description |
|---------|---------|-------------|
| `MICRODMA_CH0_HANDLER` | 0x020F1F | Latch reads, command dispatch |
| `MICRODMA_CH2_HANDLER` | 0x020F01 | Payload transfers, state machine |

**Command Dispatch Table (`CMD_DISPATCH_TABLE`):**

The command byte received from main CPU uses bits 7-5 to select a handler:

| Bits 7-5 | Range     | Handler                     | Address  | Purpose                                |
|----------|-----------|-----------------------------|----------|----------------------------------------|
| 0        | 0x00-0x1F | `Audio_CmdHandler_00_1F`    | 0x034D5F | MIDI/audio data to ring buffer         |
| 1        | 0x20-0x3F | `Audio_CmdHandler_20_3F`    | 0x01FC7C | No-op (returns immediately)            |
| 2        | 0x40-0x5F | `Audio_CmdHandler_40_5F`    | 0x01FC7F | Skip N bytes (data drain)              |
| 3        | 0x60-0x7F | `Audio_CmdHandler_60_7F`    | 0x035893 | DSP streaming data                     |
| 4        | 0x80-0x9F | `Serial1_DataTransmit_Loop` | 0x01F890 | Serial port 1 (SC1) TX                 |
| 5        | 0xA0-0xBF | `Audio_CmdHandler_A0_BF`    | 0x03CFEE | Keybed touch curve / forwarding enable |
| 6-7      | 0xC0-0xFF | `Audio_CmdHandler_C0_FF`    | 0x020C12 | No-op (returns immediately)            |

See [Sub CPU Command Format]({{ site.baseurl }}/subcpu-command-format/#cmd_dispatch_table).

Bits 4-0 encode the data length minus one (1-32 bytes).

**Tone Generator Interface:**

The payload's sound-hardware windows:

| Address             | Register       | Description                                                            |
|---------------------|----------------|------------------------------------------------------------------------|
| 0x100000 / 0x100002 | Tone generator | IC303 register-address latch / data port                               |
| 0x110002            | Keybed status  | Bit 0: a keybed event is ready (read with P6.7 set)                    |
| 0x110000            | Keybed data    | Keybed event: low byte note, high byte velocity (read with P6.7 clear) |
| 0x130000            | DSP block      | 4 channels × 8 registers (`DSP_Init_Channels`, `DSP_Write_Channel`)    |

Port P6 bit 7 controls the A23 address line for tone generator access.

**Tone generator and keybed routines (0x03D0xx):**

| Routine                 | Address  | Description                                                                   |
|-------------------------|----------|-------------------------------------------------------------------------------|
| `ToneGen_Init`          | 0x03D016 | Initialize tone gen (mode = 6)                                                |
| `ToneGen_Process_Notes` | 0x03D01E | Process incoming note events                                                  |
| `Keybed_Read_Event`     | 0x03D0C5 | Read one keybed event (status 0x110002, data 0x110000) with P6.7 control      |
| `Keybed_Decode_Event`   | 0x03D11F | Decode the event: note, black-key velocity trim and clamping                  |
| `ToneGen_Poll_Init`     | 0x03D1FB | Clear 8 voice buffers                                                         |
| `ToneGen_Poll_All`      | 0x03D217 | Poll all 16 channels                                                          |
| `FP_dcmp`               | 0x03D2AC | Floating-point double compare (8-byte operands); not a tone-generator routine |

**Voice State Buffer:**

| Address | Size | Description |
|---------|------|-------------|
| 0x4A42 | 1B | DMA command byte |
| 0x4A43 | 1B | Note number |
| 0x4A44 | 1B | Velocity |
| 0x4A48 | 1B | Tone gen mode (0-6) |
| 0x4A4A | 1B | DMA enabled flag |
| 0x4A4C | 16B | Voice slot table (one per channel) |

**Serial Port Routines:**

| Routine | Address | Description |
|---------|---------|-------------|
| `INTTX1_HANDLER` | 0x01F765 | Serial TX interrupt |
| `READ_BYTE_FROM_RING_BUFFER` | 0x01F7B9 | Ring buffer read |
| `SAVE_BYTE_TO_RING_BUFFER` | 0x01F7DD | Ring buffer write |
| `RING_BUFFER_HAS_OVERRUN` | 0x01F7AB | Check buffer empty |

Ring buffer descriptor format (at XWA):
- +0x00: buffer_start pointer
- +0x04: buffer_end pointer
- +0x08: write_pointer
- +0x0C: read_pointer
- +0x14: available_bytes count

**Debug Output Routines:**

| Routine | Address | Description |
|---------|---------|-------------|
| `Debug_Print_String` | 0x038365 | Print string via serial |
| `Debug_Print_Byte` | 0x03836C | Print byte as hex |
| `Debug_Print_Word` | 0x038375 | Print 16-bit word as hex |

These call boot ROM serial routines at 0xFFFEA1 (string) and 0xFFFE86 (byte).

---

## Sub CPU Boot ROM

The 128KB boot ROM (`kn5000_subcpu_boot.ic30`) initializes the sub CPU hardware and provides a bootstrap environment until the payload is ready.

### Memory Map

| Address Range     | Size  | Description                                                                                   |
|-------------------|-------|-----------------------------------------------------------------------------------------------|
| 0x0000-0x00FF     | 256B  | Special Function Registers (SFR)                                                              |
| 0x0100-0x01FF     | 256B  | Extended SFR / Memory Controller                                                              |
| 0x0400-0x04E0     | 225B  | Interrupt vector trampolines (copied from ROM)                                                |
| 0x04FE            | 1B    | Payload ready flag                                                                            |
| 0x0500-0x05A2     | ~160B | RAM / Stack area                                                                              |
| 0x120000          | -     | Inter-CPU Communication Latch                                                                 |
| 0x130000          | -     | 4-channel × 8-register block (DSP register base; misnamed `TONE_GEN_BASE` in the boot source) |
| 0xFE0000-0xFFFFFF | 128KB | Boot ROM (only 3.3% is real data — see below)                                                 |

### ROM Structure

> **The 0xFF regions are UNDUMPED, not erased.** IC30 is a mask ROM, and the dump we hold
> is deliberately partial: 14,336 bytes (10.9%) were actually read, and the remaining
> 116,736 bytes are `0xFF` **by assumption**, not by measurement. Calling them "erased" is
> doubly wrong — a mask ROM has no erased state, and nobody looked. Only **4,352 bytes of
> the whole chip, 3.3%, are real data**. MAME flags the file `BAD_DUMP`. See
> [ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/#dump-provenance) for the
> provenance record and the owner's own account of how it was dumped.

| Offset | Address | Size | Content |
|--------|---------|------|---------|
| 0x00000-0x007FF | 0xFE0000-0xFE07FF | 2KB | Dumped, blank |
| 0x00800-0x177FF | 0xFE0800-0xFF77FF | 92KB | **Not dumped** — assumed 0xFF |
| 0x17800-0x17FFF | 0xFF7800-0xFF7FFF | 2KB | Dumped, blank |
| 0x18000-0x1828F | 0xFF8000-0xFF828F | 656B | Eight data objects, no code — [carved]({{ site.baseurl }}/subcpu-boot-rom/#4-the-656-byte-data-region-at-0xff8000) |
| 0x18290-0x1904C | 0xFF8290-0xFF904C | ~3.5KB | Boot code and routines |
| 0x1904D-0x197FF | 0xFF904D-0xFF97FF | ~2KB | Dumped, blank |
| 0x19800-0x1EFFF | 0xFF9800-0xFFEFFF | 22KB | **Not dumped** — assumed 0xFF |
| 0x1F000-0x1FE7F | 0xFFF000-0xFFFE7F | ~3.6KB | Dumped, blank |
| 0x1FE80-0x1FEFF | 0xFFFE80-0xFFFEFF | 128B | Debug/diagnostic tail |
| 0x1FEE0 | 0xFFFEE0 | 5B | Reset handler (JP BOOT_INIT) |
| 0x1FF00-0x1FFEF | 0xFFFF00-0xFFFFEF | 240B | Interrupt vector table (45 live entries) |
| 0x1FFF0-0x1FFFF | 0xFFFFF0-0xFFFFFF | 16B | `41 b1 62 1b` × 4 — unexplained |

The non-`0xFF` content occupies three extents: `0xFF8000-0xFF904C` (4,173 B),
`0xFFFE80-0xFFFFB3` (308 B) and `0xFFFFF0-0xFFFFFF` (16 B) — two, if the 60-byte blank gap
at `0xFFFFB4-0xFFFFEF` inside the vector-table page is not counted as a separation. Those
are extents, not runs: they contain 145 interior `0xFF` bytes between them, so they span
4,497 bytes while the actual non-`0xFF` count is 4,352. Note also that roughly 10 KB of
the ranges recorded as "dumped" came back blank, so in the file itself a dumped-and-blank
byte is indistinguishable from an assumed-blank one.

### Boot Sequence (Confirmed)

1. **Reset** (0xFFFEE0): `JP 0xFF8290` jumps to boot initialization
2. **Hardware Init** (0xFF8290): Configures all SFR registers:
   - Port function control (P0FC-PBFC)
   - Serial channels (SC0, SC1)
   - Timers and watchdog
   - DRAM refresh
   - DMA for inter-CPU latch
3. **Stack Setup**: Sets XSP to 0x05A2
4. **Vector Copy** (0xFF846D): Copies 225 bytes of interrupt trampolines from ROM (0xFF8F6C) to RAM (0x0400)
5. **Enable Interrupts**: `EI 0`
6. **Initialization Routines**:
   - Memory test (0xFF8956)
   - DMA/Serial setup (0xFF85AE) - configures inter-CPU latch at 0x120000
   - Register-block init (0xFF84A8, `INIT_TONE_GEN`) - initializes the 4-channel block at 0x130000 (DSP registers, not the tone generator)
7. **Main Loop**: Waits for payload ready flag at 0x04FE, then calls 0x0400

### Interrupt Trampoline System

The boot ROM uses an elegant trampoline system for interrupts:

1. **ROM Vector Table** (0xFFFF00): Contains 4-byte addresses pointing to RAM (0x04xx)
2. **RAM Trampolines** (0x0400): Each is 5 bytes: `JP addr` (4B) + `RET` (1B)
3. **ROM Handlers**: Trampolines initially point back to ROM handlers

This allows the payload to replace interrupt handlers by modifying the trampolines in RAM.

**Trampoline Layout:**

| RAM Address | Handler                                | Initial Target                    |
|-------------|----------------------------------------|-----------------------------------|
| 0x0400      | Handler 0 (Reset)                      | 0xFFFEE0 (ROM)                    |
| 0x0405      | Handler 1                              | 0xFF8432 (Default RETI)           |
| 0x040A      | Handler 2                              | 0xFF8432 (Default RETI)           |
| ...         | ...                                    | ...                               |
| 0x042D      | Handler 9 (INT0, `IntTramp_INT0`)      | 0xFF881F (`InterCPU_RX_Handler`)  |
| ...         | ...                                    | ...                               |
| 0x04B4      | Handler 36 (INTTC0, `IntTramp_INTTC0`) | 0xFF88B8 (`CMD_Dispatch_Handler`) |
| 0x04BE      | Handler 38 (INTTC2, `IntTramp_INTTC2`) | 0xFF889A (`DMA_Complete_Handler`) |

### Key Hardware Addresses Discovered

**Inter-CPU Communication Latch (0x120000)**

The DMA is configured to use 0x120000 for communication between main CPU and sub CPU. This confirms the latch address documented elsewhere.

**The block at 0x130000**

The `INIT_TONE_GEN` routine writes initialization patterns to the 4-channel × 8-register block at 0x130000. Despite the routine's name, this is not the tone generator, which is IC303 at 0x100000/0x100002; the v1.42 payload's identical code calls 0x130000 the DSP register base (`DSP_Init_Channels`, `DSP_Write_Channel`). See [Tone Generator]({{ site.baseurl }}/tone-generator/).

### Disassembly Status

**Completed:**
- BOOT_INIT (0xFF8290) - Full hardware initialization
- COPY_VECTORS (0xFF846D) - Vector trampoline copy
- RESET_ENTRY (0xFF8433) - Alternative reset handler (uses `jrl T` to BOOT_INIT)
- TONE_GEN_CHANNEL_INIT (0xFF8437) - Channel initialization loop for the 0x130000 block
- HALT_LOOP (0xFF8490) - Error handler with stub routines
- TONE_GEN_WRITE (0xFF84F1) - Write the 8 registers of one 0x130000 channel
- WRITE_TONE_REG_MULTI_CHANNEL (0xFF850E) - Multi-register push/call wrapper
- WRITE_TONE_REG_SINGLE_CHANNEL (0xFF853A) - Write register pairs to one channel
- COPY_WORDS (0xFF858B) - Word block copy using `ldirw`
- FILL_WORDS (0xFF8594) - Memory fill with word values
- CHECKSUM_CALC (0xFF859B) - Calculate checksum over memory range
- INIT_DMA_SERIAL (0xFF85AE) - DMA/Serial configuration
- INIT_TONE_GEN (0xFF84A8) - 0x130000 register-block setup
- MAIN_LOOP - Payload wait loop
- DEFAULT_HANDLER (0xFF8432) - Simple RETI
- Vector trampolines (0xFF8F6C) - All 45 handlers
- Interrupt vector table (0xFFFF00)
- InterCPU_RX_Handler (0xFF881F) - INT0 (inter-CPU latch) interrupt
- CMD_Dispatch_Handler (0xFF88B8) - INTTC0 (micro-DMA channel 0 completion) interrupt
- DMA_Complete_Handler (0xFF889A) - INTTC2 (micro-DMA channel 2 completion) interrupt
- DELAY_ROUTINE (0xFF89A9) - Variable delay routine
- MEM_TEST_ROUTINE (0xFF89FC) - RAM test
- ROM_CHECKSUM (0xFF8AB4) - Boot ROM integrity check
- SERIAL_INIT (0xFF8B07) - Serial communication init

**Remaining:** none. The 0xFF8000 data region is carved ([Sub CPU Boot ROM §4]({{ site.baseurl }}/subcpu-boot-rom/#4-the-656-byte-data-region-at-0xff8000)), 0xFF8604-0xFF8955 is the transfer family listed under DMA Transfer Routines plus the three interrupt handlers, and the last helpers are CONTROL_PANEL_BIT_SET_CLEAR (0xFF8B37), INTER_CPU_LATCH_READ_DISPATCH (0xFF8B89) and HARDWARE_CALIBRATION_SEQUENCE (0xFF8C80).

### Inter-CPU Protocol (Boot ROM Side)

The sub CPU boot ROM handles commands from the main CPU via the latch at `0x120000`. The protocol uses a command byte followed by optional data bytes transferred via DMA.

#### Command Format

| Command | Action | DMA Buffer | DMA Size |
|---------|--------|------------|----------|
| `E1` | Set up DMA transfer | `CMD_E1_BUFFER` (0x0544) | 6 bytes |
| `E2` | Set up DMA transfer | `CMD_E2_BUFFER` (0x054A) | 10 bytes |
| `E3` | Signal payload ready | - | - |
| `00-1F` | Variable-length data | `CMD_DATA_BUFFER` (0x051E) | low 5 bits + 1 (1-32 bytes) |

For commands `00-1F`, the command byte encodes both the handler index and data length:
- **Bits 7-5**: Handler index (0-7), selects function from jump table at 0xFF8000
- **Bits 4-0**: Data length - 1 (0-31 = 1-32 bytes)

#### Interrupt Handler Details

**InterCPU_RX_Handler (0xFF881F) - INT0 (inter-CPU latch) interrupt**

Triggered when data arrives from the main CPU via the inter-CPU latch.

```
1. Check if bit 2 of INTERCPU_STATUS (0x34, port D) is set (busy flag)
   - If set: exit immediately (another transfer in progress)
2. Read command byte from latch (0x120000)
3. Store command in LAST_CMD_BYTE (0x051A)
4. Decode command:
   - E1: Set CMD_PROCESSING_STATE=2, DMA 6 bytes to CMD_E1_BUFFER (0x0544)
   - E2: Set CMD_PROCESSING_STATE=3, DMA 10 bytes to CMD_E2_BUFFER (0x054A)
   - E3: Set bit 6 of SUBCPU_STATUS_FLAGS (0x04FE), skip DMA
   - Other: Set CMD_PROCESSING_STATE=1, DMA (cmd & 0x1F)+1 bytes to CMD_DATA_BUFFER (0x051E)
5. Arm DMA channel 0 by writing 0x0A (INT0) to DMAV0 (0x0100)
6. Clear bit 1 of INTERCPU_STATUS
```

**CMD_Dispatch_Handler (0xFF88B8) - INTTC0 (micro-DMA channel 0 completion) interrupt**

Main processing interrupt that handles received data after DMA completes.

```
1. Save all registers (XWA, XBC, XDE, XHL, XIX, XIY, XIZ)
2. Read CMD_PROCESSING_STATE (0x0518):
   - State 1: Process received command data
     - Push parameters to stack
     - Calculate handler index from high 3 bits of LAST_CMD_BYTE
     - Call handler from jump table at 0xFF8000 + (index * 4)
     - Clean up stack, set CMD_PROCESSING_STATE=0
   - State 2: Set up secondary DMA transfer
     - Load parameters from CMD_E1_BUFFER (0x0544)
     - Trigger DMA, set CMD_PROCESSING_STATE=4
   - State 3: Set completion flags
     - Write 0xFF to 0x051C
     - Set bit 7 of 0x0554
     - Set CMD_PROCESSING_STATE=0
   - State 4: Finalize transfer
     - Clear bit 7 of SUBCPU_STATUS_FLAGS (0x04FE)
     - Set CMD_PROCESSING_STATE=0
3. Manage watchdog (toggle bit 2 of WDMOD if set)
4. Restore all registers
```

**DMA_Complete_Handler (0xFF889A) - DMA Complete Interrupt**

Handles DMA transfer completion by advancing the state machine.

```
1. Clear bit 2 of WDMOD (watchdog)
2. Check DMA_STATE (0x0516):
   - If 1: Set to 0 (transfer complete)
   - If 2: Set to 1 (first phase complete)
3. Return from interrupt
```

#### State Machine Diagram

```
                     Command Received
                           │
              ┌────────────┴────────────┐
              │                         │
         E1/E2 cmd               Other cmd (00-1F)
              │                         │
              v                         v
  CMD_PROCESSING_STATE = 2/3    CMD_PROCESSING_STATE = 1
              │                         │
              │    ┌────────────────────┘
              │    │
              v    v
       CMD_Dispatch_Handler processes
              │
    ┌─────────┼─────────┬─────────┐
    │         │         │         │
 State 1   State 2   State 3   State 4
    │         │         │         │
    v         v         v         v
Call handler  DMA    Set flags  Clear ready
from table  transfer           flag
    │         │         │         │
    └─────────┴─────────┴─────────┘
                    │
                    v
       CMD_PROCESSING_STATE = 0 (Idle)
```

#### DMA State Machine - `DMA_XFER_STATE` (0x0516)

Separate from the command state machine, tracks DMA transfer phases:

| Value | State | Description |
|-------|-------|-------------|
| 0 | Idle | No transfer in progress |
| 1 | Single | Single transfer pending, waiting for completion |
| 2 | Two-Phase | E1 mode: phase 1 complete, phase 2 pending |

#### DMA Register Encoding (LDC Instructions)

The TMP94C241F uses `LDC` instructions to configure DMA registers. The sources write them with the backend's `ldc_cr8`/`ldc_cr16`/`ldc_cr32` mnemonics and a numeric selector.

**DMA Register Address Encoding (Third Byte of LDC):**

| Register | Third Byte | Description                   |
|----------|------------|-------------------------------|
| DMAS0    | `00h`      | DMA Source, Channel 0         |
| DMAS2    | `08h`      | DMA Source, Channel 2         |
| DMAS3    | `0Ch`      | DMA Source, Channel 3         |
| DMAD0    | `20h`      | DMA Destination, Channel 0    |
| DMAD2    | `28h`      | DMA Destination, Channel 2    |
| DMAD3    | `2Ch`      | DMA Destination, Channel 3    |
| DMAC0    | `40h`      | DMA Count, Channel 0 (16-bit) |
| DMAM0    | `42h`      | DMA Mode, Channel 0 (8-bit)   |
| DMAC2    | `48h`      | DMA Count, Channel 2 (16-bit) |
| DMAM2    | `4Ah`      | DMA Mode, Channel 2 (8-bit)   |
| DMAC3    | `4Ch`      | DMA Count, Channel 3 (16-bit) |
| DMAM3    | `4Eh`      | DMA Mode, Channel 3 (8-bit)   |

**LDC Instruction Format:**

```
Byte 1: Register operand encoding (e.g., E8=XWA, E9=XBC, D8=WA, C9=A)
Byte 2: 2Eh (LDC opcode)
Byte 3: DMA register selector (see table above)
```

**Example:** `LDC DMAD0, XWA` = `E8 2E 20` (load DMA destination 0 from XWA)

#### MAME MicroDMA Implementation

The TMP94C241 MicroDMA is implemented in MAME's `tmp94c241.cpp` driver. MAME performs one transfer per CPU instruction boundary.

**DMAM Mode Register Format (TMP94C241):**

| Bits | Function      | Values                                                                                                                                                                                                                                                                            |
|------|---------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 4-2  | Transfer mode | 000 = destination increment, source fixed (I/O to memory); 001 = destination decrement, source fixed; 010 = source increment, destination fixed (memory to I/O); 011 = source decrement, destination fixed; 100 = both fixed; 101 = counter (source increments, nothing is moved) |
| 1-0  | Data size     | 00 = byte, 01 = word, 10 = long                                                                                                                                                                                                                                                   |

**DMA Trigger Mechanism:**

1. Software writes a start vector to `DMAVn` register (0x100-0x103)
2. The start vector maps to an interrupt source
3. When that interrupt's flag is set, DMA transfer triggers
4. One transfer occurs per `tlcs900_check_hdma()` call (cycle-steal)
5. After transfer, the triggering interrupt flag is cleared

**Cycle Costs:**

| Transfer Size | Cycles |
|---------------|--------|
| Byte (8-bit) | 8 |
| Word (16-bit) | 8 |
| Long (32-bit) | 12 |

**Completion Interrupts:**

When `DMACn` (transfer count) reaches zero:
- `DMAVn` is cleared (disables channel)
- Completion interrupt flag is set:
  - Channel 0: `INTETC01` bit 0x08
  - Channel 1: `INTETC01` bit 0x80
  - Channel 2: `INTETC23` bit 0x08
  - Channel 3: `INTETC23` bit 0x80

**Key Functions:**

- `tlcs900_check_hdma()`: Called each instruction, processes one DMA if pending
- `tlcs900_process_hdma(channel)`: Executes single transfer for a channel

### Memory Test Routine (0xFF89FC)

At boot, the sub CPU tests RAM integrity using complementary bit patterns. Results are stored in `MEMTEST_RESULT` (0x0556).

**Test Patterns:**
- Pattern 1: `0x5A5A5A5A` (alternating bits: 01011010...)
- Pattern 2: `0xA5A5A5A5` (inverted: 10100101...)

**Algorithm:**
```
1. For each test region (configured in table at 0xFF8020):
   a. Read original value
   b. Write pattern 1 (0x5A5A5A5A)
   c. Read back and verify both 16-bit halves
   d. If mismatch: OR error code from table into MEMTEST_RESULT
   e. Restore original, advance to next location
   f. Write pattern 2 (0xA5A5A5A5)
   g. Read back and verify
   h. If mismatch: OR error code into MEMTEST_RESULT
   i. Restore original, advance
2. Return error flags in L register (also stored in MEMTEST_RESULT)
```

The test configuration table at 0xFF8020 contains:
- Start address (4 bytes)
- Size in dwords (4 bytes)
- Error code for low word failure (1 byte)
- Error code for high word failure (1 byte)

### ROM Checksum Routine (0xFF8AB4)

Verifies boot ROM integrity by checksumming 0x800 words from 0xFE0000.

**Algorithm:**
```
1. Initialize two 16-bit accumulators to 0
2. For each of 0x800 words starting at 0xFE0000:
   a. Add word to accumulator (alternating between two)
3. Compare the two checksums
4. If mismatch: Set bit 2 in error flags
5. Return error flags in L register
```

### Delay Routine (0xFF89A9)

Provides variable timing delays based on a bit pattern.

**Parameters:**
- A register: 3-bit delay selector (bits 0-2 checked)

**Algorithm:**
```
1. For each of 3 bits in A (starting from bit 0):
   a. Clear bit 1 of port C (0x30)
   b. If current bit set: delay count = 0xC000, else 0x4000
   c. Execute nested delay loops (outer: BC count, inner: 32 iterations)
   d. Set bit 1 of port C (0x30)
   e. Execute another nested delay with count 0x4000
   f. Shift A right, increment loop counter
   g. Repeat until 3 bits processed
```

This allows 8 different delay combinations based on which bits are set.

### Source File

`subcpu/boot/kn5000_subcpu_boot.s` in the disassembly repository (3,115 lines)

---

## Embedded Images

The ROMs contain icons, UI elements, and splash screens for the LCD display.

### Image Locations

**Main CPU ROM:**
- 1-bit status bitmaps (Please Wait, Completed, etc.)
- UI elements (drawbar sliders, icons)
- Various graphics referenced by display routines
- Palette data at `0xEB37DE` (256 colors × 4 bytes RGBA)

**Table Data ROM:**
- Feature demo BMP images (FTBMP01-06)
- Additional UI assets

**HDAE5000 ROM:**
- Four full-screen images (320×240, 8-bit indexed): the title logo, the same drive-mechanism
  photograph without the wordmark, the file-selection panel, and the **boot splash** at
  `0x661ce` — the last of these went unidentified until August 2026
- Hard disk icon (27×27 with a 28-byte row stride, 8-bit indexed) and a 42×15 "STORE" button
- **Six** palettes, not two: every bitmap is immediately preceded by its own 1,024-byte RGBX
  palette. `0x65dce` is the boot-splash palette (the one the boot code loads into the DAC),
  `0x6158e` is the Windows halftone palette that pairs with the icon
- Together the pixels and palettes are 314,730 bytes — 60% of this 512KB ROM

### Image Format

The LCD controller is IC206 (MN89304) with 4Mbit Video RAM (IC207).

**Format characteristics to document:**
- Pixel depth (1bpp, 4bpp, 8bpp, or RGB)
- Dimension encoding
- Palette format (if indexed color)
- Compression (if any)
- Header structure

### Extraction Workflow

1. **Scan ROMs** for image signatures (BMP headers: `0x42 0x4D`)
2. **Trace display code** to find image address references
3. **Extract to binary files** in `v10/maincpu/images/`, `table_data/images/`, or `hdae5000/images/`
4. **Name descriptively** based on apparent purpose
5. **Update assembly sources** with `incbin` directives
6. **Verify byte-match** after rebuild

### Palette Discovery Technique

For indexed color images without obvious palette data, trace the boot/initialization code:

1. **Search for VGA DAC writes** - Look for code writing to `0x3C8` (palette index) and `0x3C9` (RGB data)
2. **Find the palette load routine** - Often a loop loading 256 entries
3. **Trace back to find palette address** - The `LDA` instruction before the call reveals the palette location

**Example (HDAE5000):** Boot code at `0x28f585` executes:
```asm
lda XWA, 0x2e5dce    ; Palette address (ROM offset 0x65dce)
calr 0x28f8e0        ; Palette load routine
```

The load routine at `0x28f8e0` shifts each RGB component right by 4 bits before writing it to the VGA DAC (with a round-up when bit 3 of the source byte is set and the byte is below 0xF0).

**Caveat learned the hard way on this ROM:** finding *the* palette this way finds only the palette the boot code installs. The HD-AE5000 has six, one per bitmap, each sitting in the 1,024 bytes immediately before its picture; the other five are copied to an offscreen buffer at display time rather than loaded at boot. Assuming one global palette is what makes the non-splash renders in this site's gallery come out mis-coloured. See [HDAE5000 — Embedded Graphics]({{ site.baseurl }}/hdae5000/#embedded-graphics-rewritten).

### Current Progress

**Already extracted:**
- `v10/maincpu/images/` - 44 `.bin` files with 42 PNG renders (1-bit bitmaps, UI elements, logos)
- `table_data/images/` - the 6 feature-demo BMPs, two wallpapers (`Wallpaper_0/1`, PNG beside `.bin`), and 465 PNGs under `icons/`, `icons_png/`, `ui_bitmaps/` and `fonts/`
- `hdae5000/images/` - 5 images (logo, hands, file panel, splash screen, icon) as `.bin` with PNG renders, plus 2 raw palettes and 5 palette listings

**Tools** (in the disassembly repository):
- `scripts/analysis/extract_include_binaries.py` - Extraction script
- `scripts/build/convert_images.py` - Converts raw `.bin` to PNG with correct palettes

### Conversion for Documentation

For website documentation, images can be converted to PNG format for viewing. This helps identify what each image represents and aids in understanding the UI.

---

## Boot Sequence

Understanding the complete boot sequence is essential for MAME emulation and debugging.

### Reset Vector and Early Init

**Reset Vector:** `0xFFFF00` points to `RESET_HANDLER` at `0xEF03C6`

The main CPU executes the following initialization sequence:

| Step | Address | Action | Register Values |
|------|---------|--------|-----------------|
| 1 | 0xEF03C6 | Disable Watchdog | WDMOD=0x00, WDCR=0xB1 |
| 2 | 0xEF03CC | Clock Config | CLKMOD=0x04 |
| 3 | 0xEF03D0 | Port Setup | See table below |
| 4 | 0xEF0420 | Timer Init | T01MOD=0x1D, T23MOD=0x1D |
| 5 | 0xEF0450 | Memory Controller | MSAR0-5, MAMR0-5 |
| 6 | 0xEF04A1 | DRAM Init | DRAM1REF, DRAM1CRL/H |
| 7 | 0xEF04C0 | Bus Chip Select | B0CSL-B5CSL, B0CSH-B5CSH |
| 8 | 0xEF0510 | Serial & DAC | SC0MOD=0x29, DAREG0/1=0xFF |
| 9 | 0xEF0526 | Stack Pointer | XSP=0x00000C00 |

**Port Configuration (Step 3):**

| Port | Data | Function Control | Control Register |
|------|------|------------------|------------------|
| PF | 0x00 | 0x73 (panel on, MIDI off) | 0x15 |
| P2/P3 | - | 0xFF | - |
| P7 | 0xFF | 0x1F | 0x00 |
| PA | 0xFE | 0x08 | - |
| PB | 0xFF | 0x1F | - |
| PC | 0x03 | 0x00 | 0x02 |
| PD | 0x00 | 0x06 | 0x11 |
| PE | 0x00 | 0x42 | 0x20 |
| PH | 0x00 | 0x1E | 0x09 |
| PZ | 0xFF | - | 0x03 |

**Timer Initialization (Step 4):**

```
8-bit Timers:
  T01MOD = 0x1D, T23MOD = 0x1D
  T02FFCR = 0x00
  TREG0 = 0x0A, TREG1 = 0x10
  T8RUN bit 1 set

16-bit Timer 4:
  T4MOD = 0x05, T4FFCR = 0x00, T16CR = 0x00
  TREG4L = 0x0001, TREG5L = 0x3D09
  T16RUN bits 7 and 0 set
```

**Post-Init Sequence (after 0xEF0526):**
1. `Boot_InitWorkRAM` - Work-RAM initialization
2. `MainCPU_self_test_routines` - RAM test
3. `Get_Firmware_Version` - Read version from ROM
4. If boot ROM (version 0xFF): Display "Please Wait !!" bitmap
5. Initialize system timestamp to 0
6. Call peripheral init routines
7. Set interrupt priorities (INTET01, INTET45)
8. Detect area/region code
9. Check for HD-AE5000 (PE bit 0)
10. Read control panel buttons for update mode
11. Optional: `FLASH_MEM_UPDATE` if holding button combo

### Memory Initialization

**Hardware:**
- DRAM: IC9/IC10 (M5M44260AJ7S, 4Mbit each)
- SRAM: IC21 (1Mbit, battery-backed)

**Memory Segment Configuration (MSAR/MAMR):**

| Segment | MSAR | MAMR | Start Address | Size |
|---------|------|------|---------------|------|
| 0 | 0x1E | 0x0F | 0x1E0000 | 64KB |
| 1 | 0x10 | 0x3F | 0x100000 | 256KB |
| 2 | 0xC0 | 0x7F | 0xC00000 | 512KB |
| 3 | 0x00 | 0x1F | 0x000000 | 128KB |
| 4 | 0x80 | 0xFF | 0x800000 | 1MB (Table Data) |
| 5 | 0x00 | 0xFF | 0x000000 | 1MB |

**DRAM Initialization Sequence (0xEF04A1-0xEF04BC):**

```
1. Short delay loop (BC = 0x400 iterations)
2. DRAM1REF = 0x81 (initial refresh)
3. Longer delay loop (BC = 0x2000 iterations)
4. DRAM1REF = 0x71 (final refresh)
5. DRAM1CRL = 0x8B (DRAM control low)
6. DRAM1CRH = 0x58 (DRAM control high)
7. PMEMCR bit 4 cleared
```

**Bus Chip Select Configuration:**

| Register | Low | High | Description |
|----------|-----|------|-------------|
| B0CS | 0x11 | 0x80 | Bus segment 0 |
| B1CS | 0x33 | 0x81 | Bus segment 1 |
| B2CS | 0x11 | 0xC2 | Bus segment 2 |
| B3CS | 0x22 | 0x8A | Bus segment 3 |
| B4CS | 0x11 | 0x82 | Bus segment 4 |
| B5CS | 0x22 | 0x81 | Bus segment 5 |

**Memory Test:**
- `MainCPU_self_test_routines` performs RAM test
- Uses complementary patterns: 0x5A5A5A5A and 0xA5A5A5A5

### Peripheral Initialization Order

The confirmed initialization order (from RESET_HANDLER analysis):

| Order | Peripheral | Registers | Values |
|-------|------------|-----------|--------|
| 1 | Watchdog | WDMOD, WDCR | 0x00, 0xB1 (disable) |
| 2 | Clock | CLKMOD | 0x04 |
| 3 | GPIO Ports | Px, PxFC, PxCR | See port table above |
| 4 | 8-bit Timers | T01MOD, T23MOD, TREGx | See timer table |
| 5 | 16-bit Timers | T4MOD, T16RUN, TREGxL | See timer table |
| 6 | Memory Controller | MSARx, MAMRx | See memory table |
| 7 | DRAM | DRAM1REF, DRAM1CRL/H | See DRAM sequence |
| 8 | Bus Chip Select | BxCSL, BxCSH | See bus table |
| 9 | Serial Channel 0 | SC0MOD, SC0CR | 0x29, 0x00 |
| 10 | DAC | DAREG0, DAREG1, DADRV | 0xFF, 0xFF, 0x03 |
| 11 | Stack Pointer | XSP | 0x00000C00 |

**Sub CPU Initialization (after main init):**

| Order | Peripheral      | Registers                                            | Values            |
|-------|-----------------|------------------------------------------------------|-------------------|
| 1     | Watchdog        | WDMOD_REAL, WDCR_REAL                                | 0x00, 0xB1        |
| 2     | Interrupt       | INT_CTRL (0x10A)                                     | 0x04              |
| 3     | Port Functions  | P0FC-PBFC                                            | 0xFF (most ports) |
| 4     | Port C          | PC (0x30; the boot source's `INTTC01` is a misnomer) | 0x03              |
| 5     | 8-bit Timers    | T01MOD, T23MOD                                       | 0x1D, 0x0A        |
| 6     | 16-bit Timer 4  | T4MOD, T4FFCR                                        | 0x05, 0x00        |
| 7     | Serial Channels | SER0_MOD, SER1_MOD                                   | 0x01, 0x29        |

### Sub CPU Startup

**Sequence:**
1. Main CPU releases sub CPU from reset
2. MicroDMA transfers 192KB payload
3. Latch communication at `0x120000`
4. Sub CPU signals ready

See [Sub CPU Payload Loading](#sub-cpu-payload-loading) for details.

### Panels, display and audio at boot

The control-panel bring-up is on [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/), the LCD controller set-up on [Display Subsystem]({{ site.baseurl }}/display-subsystem/#vga-initialization-values), and the order and timing of every stage on [Boot Sequence]({{ site.baseurl }}/boot-sequence/#complete-boot-timeline).

---

## Video Hardware

The KN5000 has a 320x240 QVGA LCD display for user interface.

### Hardware Components

| IC | Part Number | Function |
|----|-------------|----------|
| IC206 | MN89304 | LCD Controller |
| IC207 | M5M44265CJ8S | 4Mbit Video RAM |

### LCD Controller (MN89304)

The MN89304 is a Panasonic LCD controller providing **VGA-compatible register interface**.

**I/O Port Addresses (memory-mapped):**

| Port      | Register             | Function                              |
|-----------|----------------------|---------------------------------------|
| 0x3C0     | Attribute Controller | Address/Data                          |
| 0x3C2     | Misc Output          | Timing config (write)                 |
| 0x3C3     | VGA Enable           | Global enable                         |
| 0x3C4/3C5 | Sequencer            | Address/Data                          |
| 0x3C6     | DAC Mask             | Palette mask                          |
| 0x3C8     | DAC Write Addr       | Palette index                         |
| 0x3C9     | DAC Data             | Palette RGB (4 significant bits each) |
| 0x3CE/3CF | Graphics Ctrl        | Address/Data                          |
| 0x3D4/3D5 | CRTC                 | Address/Data                          |
| 0x3DA     | Input Status 1       | Vertical retrace                      |

**Display Configuration:**

| Parameter | Value | Description |
|-----------|-------|-------------|
| Resolution | 320x240 | QVGA |
| Color Depth | 8bpp | 256 indexed colors |
| Dot Clock | 25 MHz | From Misc Output = 0xE3 |
| Refresh | ~60 Hz | Standard VGA timing |

**Initialization Sequence (`VGA_Setup` at 0xEF55A7):**

| Step | Port | Value | Action |
|------|------|-------|--------|
| 1 | 0x3C3 | 0x01 | Global enable |
| 2 | 0x3C2 | 0xE3 | 25MHz clock, 60Hz |
| 3 | Seq 00 | 0x00 | Reset sequencer |
| 4 | Seq 01 | 0x21 | Screen off, 8-dot clock |
| 5 | Seq 00 | 0x03 | Release reset |
| 6 | Seq 02 | 0x0F | All planes writable |
| 7 | Seq 04 | 0x06 | Sequential, extended mem |
| 8 | GC 05 | 0x00 | Write mode 0, read mode 0 |
| 9 | GC 08 | 0xFF | Bit mask all bits |

**CRTC Timing Registers:**

| Register | Value | Description |
|----------|-------|-------------|
| Horiz Total | 0x65 | 101 characters |
| Horiz Display End | 0x27 | 39 chars = 320 pixels |
| Start H Retrace | 0x28 | Horizontal sync start |
| End H Retrace | 0x29 | Horizontal sync end |
| Vert Total | 0xF3 | 243 scanlines total |
| Vert Display End | 0xEF | 239 = 240 visible lines |
| Start V Retrace | 0xF2 | Vertical sync start |
| End V Retrace | 0x03 | Vertical sync end |

**Helper Functions:**
- `Write_VGA_Register` (0xEF5141): Writes BC to port WA
- `Read_VGA_Register` (0xEF5157): Reads from port WA

### Video RAM Organization

See also [Display Subsystem]({{ site.baseurl }}/display-subsystem/#video-ram).

**IC207: Mitsubishi M5M44265CJ8S (4Mbit VRAM)**

| Parameter  | Value                                        |
|------------|----------------------------------------------|
| Capacity   | 512KB chip (4Mbit), of which 256KB is mapped |
| Type       | Dual-ported VRAM                             |
| CPU window | 0x1A0000-0x1DFFFF                            |

**Confirmed Configuration:**

| Setting          | Value                        |
|------------------|------------------------------|
| Color Depth      | 8bpp (256 colors)            |
| Frame Size       | 320 × 240 × 1 = 76,800 bytes |
| Available Frames | 256KB / 75KB ≈ 3.4 frames    |

**Memory Layout:**

| Address Range     | Size    | Content                             |
|-------------------|---------|-------------------------------------|
| 0x1A0000-0x1B2BFF | 76,800B | Frame buffer 0                      |
| 0x1B2C00-0x1C57FF | 76,800B | Frame buffer 1 (if double-buffered) |
| 0x1C5800-0x1DFFFF | ~106KB  | Additional buffers                  |

**Access Patterns:**
- CPU writes to 0x1A0000 base
- VGA controller reads via serializer
- CRTC Start Address (0x0C/0x0D) selects active buffer
- Current config: Start Address = 0x0000 (buffer 0)

**Display Timing:**
- Pixel clock: 25 MHz
- Horizontal: 320 visible + blanking ≈ 400 total
- Vertical: 240 visible + blanking ≈ 262 total
- Frame rate: 25MHz / (400 × 262) ≈ 60 Hz

### Pixel Format and Palette

**Confirmed: 8-bit indexed color**

| Property             | Value                     |
|----------------------|---------------------------|
| Bits per pixel       | 8                         |
| Color count          | 256                       |
| Palette format       | 4-bit R, 4-bit G, 4-bit B |
| Total palette colors | 12-bit (4,096 possible)   |

**Palette Loading:**
1. Write palette index to 0x3C8
2. Write R, G, B values (4 significant bits each) to 0x3C9
3. Index auto-increments

**EGA Compatibility:**
- Attribute Controller (0x3C0) provides 16-color EGA palette at indices 0-15
- Standard EGA palette loaded during initialization

### Drawing, fonts and screen layout

The graphics library, fonts, widget rendering, screen regions and fade effects are documented on [Display Subsystem]({{ site.baseurl }}/display-subsystem/#drawing-primitives) and [UI Widget Types]({{ site.baseurl }}/ui-widget-types/); extracted graphics are in the [Image Gallery]({{ site.baseurl }}/image-gallery/).

---

## Feature Demo Extraction

The Feature Demo is an interactive presentation showcasing keyboard features. Extracting its data structures enables documentation, modification, and source code simplification.

### Components

- **Slides** - Background images with overlaid UI widgets
- **Widgets** - Text, images, shapes, interactive elements
- **MIDI files** - Demo music embedded in ROM
- **Timing data** - Slide duration and transitions

### Known Demo Images

Already extracted to `table_data/images/`:

| File        | Size    | Description                    |
|-------------|---------|--------------------------------|
| FTBMP01.BMP | 320x240 | Demo screen 1                  |
| FTBMP02.BMP | 320x130 | Demo screen 2                  |
| FTBMP03.BMP | 320x120 | Demo screen 3                  |
| FTBMP04.BMP | 320x120 | Demo screen 4 (disk insertion) |
| FTBMP05.BMP | 320x125 | Demo screen 5                  |
| FTBMP06.BMP | 320x240 | Demo screen 6                  |

See [Image Gallery]({{ site.baseurl }}/image-gallery/) for viewable versions.

The slide and widget format is the SSF presentation format, documented on [Feature Demo]({{ site.baseurl }}/feature-demo/#ssf-presentation-format) and [SSF Presentation System]({{ site.baseurl }}/ssf-presentation/).

### ASL Macro Design

⚠ **Superseded.** This macro-based plan was never built; `feature_demo.inc` does
not exist. The demo slide data was disassembled directly into real source
instead — `v10/maincpu/demo/demo_routines.s` and `table_data/kn5000_table_data.s`
— which is what the [Feature Demo]({{ site.baseurl }}/feature-demo/) page
documents. The sketch below is kept for the widget-parameter shapes it records,
not as an open task.

Goal: Replace raw data bytes with human-readable macros.

**Slide macros:**
```asm
SLIDE_BEGIN id, background_image, duration_ms, midi_ptr
    ; widgets defined here
SLIDE_END
```

**Widget macros:**
```asm
TEXT x, y, font, color, "string"
IMAGE x, y, image_id
RECT x, y, w, h, fill_color, border_color
LINE x1, y1, x2, y2, color
```

**Example slide definition:**
```asm
SLIDE_BEGIN 1, FTBMP01, 5000, DemoMidi1
    TEXT 10, 20, FONT_LARGE, COLOR_WHITE, "Welcome to KN5000"
    IMAGE 100, 80, ICON_KEYBOARD
    RECT 50, 150, 200, 30, COLOR_BLUE, COLOR_WHITE
SLIDE_END
```

**Tasks:**
1. Design macro syntax for each structure
2. Implement macros in ASL format
3. Ensure macros emit correct binary
4. Add to `feature_demo.inc`

### Demo songs

The demo songs are SLIDE4K-compressed presets in the table data, rebuilt from committed MIDI files; see [Table Data ROM]({{ site.baseurl }}/table-data-rom/#demo-song-presets-slide4k).

---

## Sound Hardware

The KN5000 has a sophisticated sound generation system with dedicated processors for synthesis and effects.

### Architecture Overview

```
Main CPU (TMP94C241F)
    │
    │ Commands via the IC22/IC23 latches
    v
Sub CPU (IC27)
    │
    │ Register writes at 0x100000/0x100002
    v
Tone generator (IC303) <────── Waveform ROMs (IC304-IC307)
    │      ^
    │      │ effects send/return
    │      v
    │  DSP1 (IC311)
    │
    │ Main mix
    v
DSP2 (IC310): mixing and EQ
    │
    v
DAC (IC313, PCM69AU)
    │
    │ Analog audio
    v
Output Jacks (Line, Headphones, Speakers)
```

### Hardware Components

| IC        | Function       | Description                                                              |
|-----------|----------------|--------------------------------------------------------------------------|
| IC27      | Sub CPU        | TMP94C241F; tone generator control, synthesis engine                     |
| IC303     | Tone generator | TC183C230002; 64 voices, PCM playback from the waveform ROMs             |
| IC304-307 | Waveform ROMs  | Four 4 MB mask ROMs of PCM samples; only IC307 is dumped                 |
| IC311     | DSP1           | uPD6383GF-3BA; digital effects (reverb, chorus, …) on a send/return loop |
| IC310     | DSP2           | MN19413; mixing and EQ on the main mix                                   |
| IC313     | DAC            | PCM69AU; digital-to-analog conversion for audio output                   |

See [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/#architecture) for the full picture.

### Sub CPU (IC27)

The Sub CPU handles all real-time sound generation, receiving commands from the main CPU. See [CPU Subsystem]({{ site.baseurl }}/cpu-subsystem/).

### DSP (IC311)

Digital Signal Processor for audio effects. See [Effects DSP]({{ site.baseurl }}/effects-dsp/).

### DAC (IC313)

Converts digital audio to analog output. See [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/).

### Waveform ROMs (IC304-IC307)

Contain all PCM samples for instrument sounds. See [Waveform ROM Format]({{ site.baseurl }}/waveform-rom-format/).

### Main CPU ↔ Sub CPU Protocol

Communication via latches at `0x120000`. See [Sub CPU Command Format]({{ site.baseurl }}/subcpu-command-format/).

### Synthesis Architecture

**Questions to answer (ANSWERED — see [Tone Generator]({{ site.baseurl }}/tone-generator/)):**
- Polyphony count: **64 voices**, register-indirect at 0x100000/0x100002
- Synthesis method: **PCM sample playback** from 16MB waveform ROM (4 chips)
- Envelope generators: **Hardware-internal ADSR** — firmware sends pitch/volume/pan, chip handles envelopes
- LFO capabilities: the mod wheel selects vibrato, tremolo or auto-pan (`Voice_ModWheel_Apply`); see [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/#lfo-and-modulation)
- Filter: the firmware writes a per-voice TVF (filter cutoff) in several modes through `TVF_Emit_Registers` (0x024444, formerly misnamed Voice_PanReg_WriteDispatch)

### Effects Processing

**Known effects (from panel labels):**
- Reverb (multiple types: Hall, Room, Plate, etc.)
- Chorus/Flanger
- EQ (bass, treble, presence)

See [Effects DSP]({{ site.baseurl }}/effects-dsp/).

### Audio Output Path

From DAC to physical jacks.

**Outputs:**
- Line Out (L/R)
- Headphone jack
- Internal speakers (if present)

See [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/).

### MIDI Implementation

Full MIDI capability for external control and sequencing. See [MIDI Subsystem]({{ site.baseurl }}/midi-subsystem/) and [SysEx Messages]({{ site.baseurl }}/sysex-messages/).

### Rhythm/Accompaniment Engine

Auto-accompaniment system for backing tracks.

**Components:**
- Rhythm patterns (drums, percussion)
- Bass patterns
- Chord patterns
- Style variations (Intro, Main A/B, Fill, Ending)

See [Accompaniment Engine]({{ site.baseurl }}/accompaniment-engine/#chord-detection).

### Sample/Patch Extraction

The tone and drum-kit parameter records are documented on [Tone Database]({{ site.baseurl }}/tone-database/), and the sample layout on [Waveform ROM Format]({{ site.baseurl }}/waveform-rom-format/). Questions that are still open belong on [Open Questions]({{ site.baseurl }}/questions/).

---

## System Update Procedures

The KN5000 supports firmware updates via floppy disk. Understanding this system enables custom firmware development.

### Update File Formats

Official updates distributed as executable files on floppy disk.

**Known files (from [archive.org](https://archive.org/details/technics-kn5000-system-update-disks)):**

| File | Version | Date |
|------|---------|------|
| KN5KPV5.EXE | v5 | 1997-11-12 |
| KN5KPV6.EXE | v6 | 1998-01-16 |
| KN5KPV7.EXE | v7 | 1998-06-26 |
| KN5KPV8.EXE | v8 | 1998-11-13 |
| KN5KPV9.EXE | v9 | 1999-01-26 |
| KN5KPV10.EXE | v10 | 1999-08-02 |

**File Type Identifiers (38-byte header at 0xE00038):**

| ID | Header String | Description |
|----|---------------|-------------|
| 1 | `Technics KN5000 Program  DATA FILE 1/2` | Main CPU ROM disk 1 |
| 2 | `Technics KN5000 Program  DATA FILE 2/2` | Main CPU ROM disk 2 |
| 3 | `Technics KN5000 Table    DATA FILE 1/2` | Table data disk 1 |
| 4 | `Technics KN5000 Table    DATA FILE 2/2` | Table data disk 2 |
| 5 | `Technics KN5000 CMPCUSTOMDATA FILE    ` | Custom data (compressed?) |
| 6 | `Technics KN5000 HD-AEPRG DATA FILE    ` | HDAE5000 ROM |
| 7 | `Technics KN5000 Program  DATA FILE PCK` | Main CPU ROM (packed) |
| 8 | `Technics KN5000 Table    DATA FILE PCK` | Table data (packed) |

**File Structure:**
- 38-byte identification header string
- Null terminator (0x00)
- 0xFF marker byte
- Payload data

**Handler Dispatch:** Table at 0xE00178 routes each file type to its handler.
Types 2 and 4 show "ILLEGAL DISK" if loaded before 1 and 3 respectively.

### Update Mode Entry

**Entry Conditions (all must be true; checked in `BootInit_SeqAndPanel`, around 0xEF05C5):**

| Condition | Check | Description |
|-----------|-------|-------------|
| 1 | Firmware version = 0xFF | Running from boot ROM, not flash |
| 2 | Floppy disk inserted | `Check_for_Floppy_Disk_Change` ≠ 0 |
| 3 | Button code = 0x04 | Specific button held at power-on |

**Detection Code:**

```asm
CALL CPanel_ScanButtons  ; Read buttons at power-on
LD (0402h), L                    ; Store button state
CALL Get_Firmware_Version
CP L, 0ffh                       ; Check if boot ROM
JR NZ, User_didnt_request_flash_mem_update
CALL Check_for_Floppy_Disk_Change
CP HL, 0                         ; Check disk present
JR Z, User_didnt_request_flash_mem_update
CP (0402h), 004h                 ; Button code 0x04?
JR NZ, User_didnt_request_flash_mem_update
CALL FLASH_MEM_UPDATE            ; Enter update mode
```

**Notes:**
- Update mode only accessible from boot ROM (virgin/corrupted flash)
- "Please Wait !!" bitmap displayed at 0xEF0536 when in boot ROM mode
- System halts after update (infinite loop at Boot_MainSequence_Trampoline)

### File Types and Target Components

| File ID | Header        | Target                                                           | Address                                                         | Size        |
|---------|---------------|------------------------------------------------------------------|-----------------------------------------------------------------|-------------|
| 1       | Program 1/2   | Main CPU ROM (first half)                                        | 0xE00000+                                                       | 1MB         |
| 2       | Program 2/2   | Main CPU ROM (second half)                                       | 0xF00000+                                                       | 1MB         |
| 3       | Table 1/2     | Table Data (first half)                                          | 0x800000+                                                       | 1MB         |
| 4       | Table 2/2     | Table Data (second half)                                         | 0x900000+                                                       | 1MB         |
| 5       | CMPCUSTOMDATA | Custom Data Flash                                                | 0x300000                                                        | 1MB         |
| 6       | HD-AEPRG      | HDAE5000 ROM                                                     | 0x280000                                                        | 512KB       |
| 7       | Program PCK   | Main CPU program (packed) **and** the compressed sub-CPU payload | program as for types 1/2; payload to Custom Data Flash 0x3E0000 | 2MB + 128KB |
| 8       | Table PCK     | Table Data (packed)                                              | 0x800000                                                        | 2MB         |

**Component Sizes:**

| Component | Size | Distribution |
|-----------|------|--------------|
| Main CPU ROM | 2MB | 2 disks (1/2, 2/2) or 1 packed |
| Table Data | 2MB | 2 disks (1/2, 2/2) or 1 packed |
| Custom Data | 1MB | 1 disk (compressed?) |
| HDAE5000 ROM | 512KB | 1 disk |

**Note:** the sub-CPU payload is not a separate update file: a type-7 file carries it as a second SLIDE4K stream, which the installer writes verbatim to Custom Data Flash 0x3E0000 (see [System Update Discs]({{ site.baseurl }}/system-update-discs/#update-handlers-by-type)).

### Flash ROM Chips

**Chip Identification:** QV1GFKN5KAX1

| Location | Chip | Capacity | Address |
|----------|------|----------|---------|
| IC4/IC6 | Program Flash | 2MB total | 0xE00000 |
| - | Custom Data Flash | 1MB | 0x300000 |

### Flash Erase Algorithm

Flash memory must be erased before programming.

**Typical sequence:**
1. Write unlock sequence to chip
2. Issue sector erase or chip erase command
3. Poll for completion
4. Verify erasure (all 0xFF)

See [Flash Programming]({{ site.baseurl }}/flash-programming/#amdatmel-flash-protocol).

### Flash Program Algorithm

Writing data to Flash ROM.

**Typical sequence:**
1. Write unlock sequence
2. Issue program command
3. Write data byte/word
4. Poll for completion
5. Verify written data

See [Flash Programming]({{ site.baseurl }}/flash-programming/#amdatmel-flash-protocol).

### FDC Interaction

Floppy Disk Controller at `0x110000` (IC208: D72068GF-3B9).

See [FDC Subsystem]({{ site.baseurl }}/fdc-subsystem/).

### Update Progress Display

LCD messages during update (extracted as 1-bit bitmaps):

| Bitmap | Message | Stage |
|--------|---------|-------|
| `Bitmap_1bit_Flash_Memory_Update.bin` | Flash Memory Update | Start |
| `Bitmap_1bit_Please_Wait.bin` | Please Wait | Processing |
| `Bitmap_1bit_Now_Erasing.bin` | Now Erasing | Erase phase |
| `Bitmap_1bit_FD_to_Flash_Memory.bin` | FD to Flash Memory | Write phase |
| `Bitmap_1bit_Completed.bin` | Completed | Success |
| `Bitmap_1bit_Turn_On_AGAIN.bin` | Turn On AGAIN | Restart needed |
| `Bitmap_1bit_Illegal_Disk.bin` | Illegal Disk | Error |
| `Bitmap_1bit_Change_FD_2_of_2.bin` | Change FD 2 of 2 | Multi-disk |

See [Firmware Update Display]({{ site.baseurl }}/firmware-update-display/#state-machine).

### Validation and Error Handling

See [Firmware Update Validation]({{ site.baseurl }}/firmware-update-validation/).

### HDAE5000 Update

Separate update procedure for HD-AE5000 expansion.

**Versions:**
- v1.10i (1998-07-06)
- v1.15i (1998-10-13)
- v2.01i (1999-01-15) - Added lyrics display (the installer says "v2.0i"; the ROM's signature says v2.01i)
- v2.06i (release date unknown) - the version disassembled here

See [System Update Discs]({{ site.baseurl }}/system-update-discs/#update-handlers-by-type) (type 6, HD-AE5000).

### Homebrew Development

Understanding the update system enables:
- Custom firmware creation
- Feature modifications
- Bug fixes for aging hardware
- Preservation of update capability

See [Firmware Update Procedure]({{ site.baseurl }}/firmware-update-procedure/#creating-custom-update-discs) for creating custom update discs.

---

## Jump Tables

The firmware uses jump tables extensively for event dispatching, state machines, and handler selection. Documenting these tables is essential for understanding program flow.

### Jump Table Patterns

**Direct address tables** (32-bit entries):
```asm
; Table of absolute addresses
JUMP_TABLE:
    dd HANDLER_0
    dd HANDLER_1
    dd HANDLER_2

; Usage: index in register, multiply by 4, load address, jump
    SLL 2, A           ; index * 4
    LDA XHL, JUMP_TABLE
    LD XHL, (XHL + A)  ; load address
    JP T, XHL          ; jump to handler
```

**Offset tables** (16-bit entries):
```asm
; Table of offsets from base address
OFFSET_TABLE:
    dw (HANDLER_0 - BASE_ADDR)
    dw (HANDLER_1 - BASE_ADDR)

; Usage: load offset, add to base, jump
    LDA XIX, OFFSET_TABLE
    LD WA, (XIX + WA)      ; load offset
    LDA XIX, BASE_ADDR
    JP T, XIX + WA         ; jump to base+offset
```

### Indirect Jump Instructions

| Pattern | Description |
|---------|-------------|
| `CALL T, XHL` | Call through XHL register |
| `CALL T, XIX` | Call through XIX register |
| `JP T, XHL` | Jump through XHL register |
| `JP T, XIX + WA` | Indexed jump (base + WA offset) |
| `JP T, XIX + BC` | Indexed jump (base + BC offset) |
| `JP T, XIX + DE` | Indexed jump (base + DE offset) |

### Jump Table Statistics

Every jump table in the KN5000 images is resolved: the disassembly's semantic score counts 2,259 of 2,259 KN5000 jump tables resolved (3,021 of 3,021 with the SX-WSA1R, where 11 tables are accepted as declared stale copies), from the dispatch census `docs/coverage/dispatch-census-2026-10-06-31` (`make dispatch-census`). [Dispatch Tables]({{ site.baseurl }}/dispatch-tables/) lists the main-CPU dispatch sites.

**High-use indirect call tables (analyzed):**
- 0xE9F11C (13 uses) - `PsMixer_ControlProcTable`: 11 code addresses, the mixer's control-type procedures `PsMixer_CtlTypeProc0`..`10`, called by `PsMixer_ControlHelper` with the paint message (September 2026; it was called EVENT_HANDLER_DISPATCH_TABLE)
- 0xEA0A16 (12 uses) - `SingleLoadDst_AreaListProcs` (data transfer subsystem)
- 0xEA0212 (1 use) - `SaveAll_RegionRecs_HandlerCol` (save-all region-record handlers)

### FDC Memory Map

FDC handler routines access these RAM locations:

| Address | Purpose |
|---------|---------|
| 0x8A20 | FDC status/mode flag (0xFF = active) |
| 0x8A24 | Error indicator (0x00 = success) |
| 0x8A26 | Cached FDC status |
| 0x8A2E | FDC timing parameter |
| 0x8A34 | FDC control value |
| 0x8A36 | FDC address register |
| 0x8A40 | FDC command code (0-11) |
| 0x8A44 | FDC output control flag |
| 0x8A48-4A | Sector/track/head |
| 0x8A6A | FDC output enable flag |
| 0x8A6C | FDC drive/mode selector |
| 0x8B04 | FDC control register |

### FDC Handler Routines

The FDC subsystem uses a handler dispatch table at 0xF97D8D with 12 handlers. Full disassembly is documented in `docs/fdc_disassembly.md` in the roms-disasm repository.

| Address  | Name                  | Description                        |
|----------|-----------------------|------------------------------------|
| 0xF96BBF | FDC_INIT              | Basic FDC initialization           |
| 0xF96BD0 | FDC_CONFIG_VERIFY     | Configuration/status verification  |
| 0xF96D95 | FDC_CMD_DISPATCH_SUB  | Command handler subroutine         |
| 0xF97696 | FDC_CmdSeek           | Seek command                       |
| 0xF976E4 | FDC_CMD_EXEC          | Command execution handler          |
| 0xF97835 | FDC_SECTOR_XFER       | Sector/data transfer handler       |
| 0xF97984 | FDC_MODE_CONFIG       | Mode configuration (modes 0-5)     |
| 0xF97C21 | FDC_CMD_ENABLE        | Command enable (sets bit 3 @ 0x28) |
| 0xF97C4B | FDC_CMD_DISABLE       | Command disable                    |
| 0xF97C54 | FDC_STATUS_COPY       | Copy cached status                 |
| 0xF97C5B | FDC_OUTPUT_CTRL       | Output control                     |
| 0xF97C7C | FDC_INTERRUPT_HANDLER | Main interrupt handler             |

**Handler dispatch** works by reading an index from 0x8A40 (0-11) and calling the corresponding routine through the dispatch table.

### FDC Helper Routines (Fully Analyzed)

These helper routines support the main FDC handlers:

| Address  | Name             | Size      | Description                                          |
|----------|------------------|-----------|------------------------------------------------------|
| 0xF97544 | FDC_DRIVE_DETECT | 78 bytes  | 6-check drive detection (returns HL=0xFFFF if found) |
| 0xF97592 | FDC_DRIVE_STATUS | 26 bytes  | Quick 2-check status validation                      |
| 0xF972F9 | FDC_CMD_SEND     | 231 bytes | NEC uPD765 command protocol                          |
| 0xF975DC | FDC_TIMING_DELAY | 6 bytes   | Set wait flag for timeout protection                 |
| 0xF975E2 | FDC_POST_OP      | 48 bytes  | Wait with 500ms timeout (error 0x09)                 |
| 0xF97612 | SOME_DELAY       | 32 bytes  | Millisecond delay (WA/2 ms)                          |

**FDC_DRIVE_DETECT (0xF97544)** validates 6 conditions:
1. (8A46h) == 0 - Status register 3 clear
2. (8A44h) == 0 - Status register 2 clear
3. (8A40h) == 3 - Command = Sense Drive Status
4. (8A4Ah) == 1 - Result count = 1
5. (8A10h) == 0xFFFF - Detection mode active
6. (8A48h) == 2 or 0xFF - Valid drive response

**FDC_CMD_SEND (0xF972F9)** implements the NEC uPD765 protocol:
- Command byte structure: MT(7), MF(6), SK(5), Command(4-0)
- Accesses FDC hardware at 0x110008 (status) and 0x11000A (data)
- Handles: Seek, Recalibrate, Read/Write Data, Format Track, Sense Interrupt

**SOME_DELAY timing**: Uses SYSTEM_TIMESTAMP at 0x0409, incremented by Timer 1 at ~1ms intervals. Delay = WA/2 milliseconds.

### Known Jump Tables

| Table                                   | Address  | Type             | Entries | Purpose                                  |
|-----------------------------------------|----------|------------------|---------|------------------------------------------|
| `HANDLE_UPDATE_OFFSETS`                 | 0xE00178 | 16-bit offsets   | 8       | Update file type dispatch                |
| `UI_STATE_MACHINE_TABLE`                | 0xEF0D64 | 32-bit addresses | 3       | UI state machine (3 states)              |
| `UI_SUBSTATE_TABLE`                     | 0xEF0DA5 | 32-bit addresses | 16      | UI sub-state handler dispatch            |
| `SOUND_DATA_SECTION_PTRS`               | 0xE023B0 | 32-bit addresses | 16      | Sound category data pointers             |
| `FDC_CommandEntry_CopyParams_CaseTable` | 0xEA98CA | 16-bit offsets   | 12      | FDC command handler dispatch             |
| `FDC_HANDLER_DISPATCH_BASE`             | 0xF97D8D | (base address)   | 12      | FDC handler routines                     |
| `SQTR_DISPATCH_TABLE_1`                 | 0xF20D37 | Inline code      | 6       | Sequencer track handler (SqTrAsTtlFunc)  |
| `SQTR_DISPATCH_TABLE_2`                 | 0xF20D8E | Inline code      | 6       | Sequencer track handler (SqTrAsTtlFunc)  |
| `APP_EVENT_HANDLER_TABLE`               | 0xF44169 | Inline code      | 32      | Application event delivery system        |
| `NOTE_EVENT_DISPATCH_1`                 | 0xF17155 | Inline code      | 7       | Note event handler (BC index)            |
| `NOTE_EVENT_DISPATCH_2`                 | 0xF171C4 | Inline code      | 7       | Note event handler (WA index)            |
| `UI_COMPONENT_DISPATCH`                 | 0xF1A7CB | Inline code      | 8       | UI grid/focus component handler          |
| `RESOURCE_INFO_HANDLERS`                | 0xF1EA4C | Inline code      | 10      | Resource info retrieval (GetResouceInfo) |
| `FDC_COMMAND_DISPATCHER`                | 0xF96DB1 | Inline code      | 12      | FDC command dispatcher                   |
| `FDC_CMD_HANDLER_BASE`                  | 0xF96DD6 | (base address)   | 12      | FDC command handler base                 |

### Handler Dispatch Example

The update file handler uses offset-based dispatch:

```asm
Erase_and_Burn____when_disk_is_valid:
    LD A, (0F23Ch)              ; Get file type ID
    EXTZ WA                     ; Zero-extend to 16-bit
    SLL 1, WA                   ; Multiply by 2 (word offset)
    LDA XIX, HANDLE_UPDATE_OFFSETS
    LD WA, (XIX + WA)           ; Load offset from table
    LDA XIX, HANDLE_UPDATE_FILE_TYPE_ID_001h  ; Base address
    JP T, XIX + WA              ; Jump to handler
```

### State Machine Pattern

Multi-level dispatch using nested jump tables:

```asm
; First level: 3 main states
    LDA XHL, 0EF0D64h       ; Main state table
    LD XHL, (XHL + A)
    JP T, XHL

UI_STATE_MACHINE_TABLE:
    dd UI_STATE_0_IDLE         ; State 0
    dd UI_STATE_1_PROCESS         ; State 1
    dd UI_STATE_2_SUBSTATE         ; State 2

; State 2 has 16 sub-states
UI_STATE_2_SUBSTATE:
    LDA XHL, 0EF0DA5h       ; Sub-state table
    LD XHL, (XHL + A)
    JP T, XHL

UI_SUBSTATE_TABLE:
    dd UI_SUBSTATE_CLEAR_FLAGS         ; Sub-state 0
    dd UI_SUBSTATE_PROCESS_A         ; Sub-state 1
    ... (16 total entries)
```

### Undocumented Jump Table Targets

The FDC handler dispatch table (`FDC_CommandEntry_CopyParams_CaseTable` at 0xEA98CA) calls these routines, all now disassembled:

| Routine                 | Address  | Status       | Called By             |
|-------------------------|----------|--------------|-----------------------|
| `FDC_CmdSeek`           | 0xF97696 | Disassembled | FDC_HANDLER_02        |
| `FDC_CMD_EXEC`          | 0xF976E4 | Disassembled | FDC_HANDLER_03        |
| `FDC_SECTOR_XFER`       | 0xF97835 | Disassembled | FDC_HANDLER_04        |
| `FDC_CMD_ENABLE`        | 0xF97C21 | Disassembled | Multiple handlers     |
| `FDC_INTERRUPT_HANDLER` | 0xF97C7C | Disassembled | FDC_HANDLER_11        |
| `FDC_INIT`              | 0xF96BBF | Disassembled | FDC_InitSequence_Full |
| `FDC_CONFIG_VERIFY`     | 0xF96BD0 | Disassembled | FDC_InitSequence_Full |
| `FDC_MODE_CONFIG`       | 0xF97984 | Disassembled | FDC_HANDLER_05        |
| `FDC_CMD_DISABLE`       | 0xF97C4B | Disassembled | FDC_HANDLER_07        |
| `FDC_STATUS_COPY`       | 0xF97C54 | Disassembled | FDC_HANDLER_08        |
| `FDC_OUTPUT_CTRL`       | 0xF97C5B | Disassembled | FDC_HANDLER_09        |
| `FDC_CMD_DISPATCH_SUB`  | 0xF96D95 | Disassembled | FDC_HANDLER_10        |

All of them are code in `v10/maincpu/storage/fdc_routines.s`, which holds no `.byte` lines. See [FDC Subsystem]({{ site.baseurl }}/fdc-subsystem/).

### Finding Jump Tables

To find undocumented jump tables:

1. Run `make dispatch-census` in the disassembly repository; it lists every table found, whether each is used, and any target that is unlabelled, mid-instruction or still data (see `docs/coverage/README.md`).
2. To search by hand, indirect jumps are spelled `jp t, (xix+wa)` / `call (xhl)` in the LLVM sources.

---

## UI and Event System

The firmware implements a sophisticated event-driven UI system with multiple dispatch layers.

### Event Handler Dispatch

The main event loop uses a multi-level dispatch system:

**APP_EVENT_HANDLER_TABLE (0xF44169):**
- 32 inline code handlers for application events
- Used for LED control, button handling, and UI updates

**UI_COMPONENT_DISPATCH (0xF1A7CB):**
- 8 inline code handlers for UI grid/focus components
- Handles keyboard grid navigation and focus management

**NOTE_EVENT_DISPATCH (0xF17155 / 0xF171C4):**
- Two 7-entry tables for note event handling
- Uses BC index (table 1) or WA index (table 2)

### Sequencer System

The sequencer track system uses dedicated dispatch tables:

| Table | Address | Entries | Purpose |
|-------|---------|---------|---------|
| SQTR_DISPATCH_TABLE_1 | 0xF20D37 | 6 | SqTrAsTtlFunc handlers |
| SQTR_DISPATCH_TABLE_2 | 0xF20D8E | 6 | SqTrAsTtlFunc handlers |

### Resource System

**GetResouceInfo (0xF1EA30; handler table `RESOURCE_INFO_HANDLERS` at 0xF1EA4C):**
- 10-entry dispatch table for resource information retrieval
- Handles font metrics, character widths, and string dimensions

Font metrics and character tables are documented on [Display Subsystem]({{ site.baseurl }}/display-subsystem/#font-helper-functions).

### UI State Machine

The main UI uses a two-level state machine:

```
Level 1 (0xEF0D64): 3 main states
  ├── State 0: UI_STATE_0_IDLE
  ├── State 1: UI_STATE_1_PROCESS
  └── State 2: UI_STATE_2_SUBSTATE → Level 2

Level 2 (0xEF0DA5): 16 sub-states for detailed UI handling
```

---

## Formerly Undocumented Data Structures

The roughly 50 KB spanning 0xE0176C-0xE0E974 that once sat as five untyped binary
includes is now named, typed source. `0xE0176C-0xE01F7F` is
`v10/maincpu/sequencer/ssf_gate_states.s`; the rest is the instrument sound-data
family under `v10/maincpu/audio/` (`sound_data_guitar.{s,c}`,
`sound_data_strings_vocal.{s,c}`, `sound_data_flute.{s,c}`,
`sound_data_sax_reed.{s,c}`, `sound_data_mallet_orch_perc.{s,c}`,
`sound_data_orchestral_pad.{s,c}`, `sound_data_piano.{s,c}`, `sound_data_brass.s`,
and the other per-instrument-category files alongside them) — each range was split
into per-instrument slices before conversion, so no single binary file now
corresponds to any one of the five address ranges above.

---

## Semantic Label Naming

A comprehensive analysis identified 200+ labels across 14 assembly files that need semantic names. The full recommendations are in `docs/label_rename_recommendations.md` in the disassembly repository.

### Completed Renames

**150+ labels renamed across 22 files** using sed scripts in `scripts/renaming/`:

| File                     | Renames | Examples                                                                                                                                         |
|--------------------------|---------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| demo_routines.asm        | 23      | `DemoStyle_InputHandler`, `DemoRhythm_DispatchTable`                                                                                             |
| sysex_routines.asm       | 15      | `ExcSendFunc_InvalidParam_Exit`, `ExcDotFunc_HandlerJumpTable`                                                                                   |
| midi_serial_routines.asm | 15      | `MIDI_RX_BYTE_DISPATCHER`, `MIDI_CHANNEL_HANDLER_JUMP_TABLE`                                                                                     |
| cpanel_routines.asm      | 16      | `CPanel_InterruptPoll_MainLoop`, `CPanel_PanelDetection`                                                                                         |
| fdc_routines.asm         | 15      | `FDC_Setup_DMA_Write_Mode`, `FDC_Exception_Status_Decoder`                                                                                       |
| subcpu_boot.asm          | 15      | `TONE_GEN_CHANNEL_INIT`, `DEBUG_OUTPUT_BYTE_HEX`                                                                                                 |
| subcpu_payload.asm       | 20      | `Audio_DMA_RingBuffer_To_Maincpu`, `Voice_Pool_Quota_ModeB`                                                                                      |
| hdae5000.asm             | 22      | `HDAE5000_SongRecord_Address` (then `HDAE5000_Calculate_Row_Address`), `HDAE5000_PPORT_Cmd12_Nothing` (then `HDAE5000_PPORT_Cmd_LoadHDtoMemory`) |
| file_io/*.asm            | 20      | `SelectPasswordMode`, `DisplaySmfFileList`                                                                                                       |

### Naming Conventions

| Category | Pattern | Examples |
|----------|---------|----------|
| Routines | VerbNoun | `FDC_Validate_Drive_Head`, `MIDI_RX_BYTE_DISPATCHER` |
| Dispatch Tables | *_DispatchTable | `DemoStyle_DispatchTable`, `MIDI_CHANNEL_HANDLER_JUMP_TABLE` |
| Exit Points | *_Exit, *_Return | `ExcDotFunc_InvalidIndex_Exit` |
| Error Handlers | *_Error, *_Invalid | `FDC_WaitReady_TimeoutCheck` |
| Data Tables | *_Table | `Voice_PolyphonyLimits_Table` |

### Where naming stands

The rename list above is history. At disassembly `3417969c0` the symbol files have no `LABEL_` placeholders, and v10 has 53,108 semantic names against 638 positional ones (98.8 %). The labels once listed here as pending exist, some under the names the code review settled on: `Boot_HandleFactoryReset` (0xEF07F3), `Sprintf_Core` (0xFF1048) and `Voice_Pool_Quota_ModeB` (0x00F519). The disassembly's `make semantic-score` measures what is left.

---

## References

- [Service Manual PDF]({{ site.baseurl }}/service_manual/technics_sx-kn5000.pdf)
- [System Update Disks Archive](https://archive.org/details/technics-kn5000-system-update-disks)
- [HDAE5000 Technical Info](https://www.keysoftservice.ch/hdae5000-e.htm)
- [Image Gallery]({{ site.baseurl }}/image-gallery/) - Extracted graphics from firmware
