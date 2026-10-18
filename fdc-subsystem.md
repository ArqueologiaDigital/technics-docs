---
layout: page
title: FDC Subsystem
permalink: /fdc-subsystem/
---

# Floppy Disk Controller Subsystem

This page documents the FDC (Floppy Disk Controller) handler routines from the KN5000 firmware. The FDC interfaces with a uPD72068GF-3B9 controller at IC208.

There are **two** FDC drivers in the machine, and they are different code:

| driver                        | where                                                               | status                                                                                           |
|-------------------------------|---------------------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| runtime driver                | Program ROM 0xF96B13-0xF9800B, `v10/maincpu/storage/fdc_routines.s` | fully disassembled (no `.byte` lines); several routines still carry their original guessed names |
| first-stage bootloader driver | Table Data ROM 0x9FD8A5-0x9FEA9C, `table_data/boot_fdc_driver.s`    | **fully labelled**: 84 labels, byte-matching rebuild                                             |

The bootloader driver is a compact port of the runtime one, and each of its routine
headers names its runtime twin. That correspondence is what makes it valuable: it
settles what several of the runtime driver's guessed names actually do — see
[What the boot twin corrects](#what-the-boot-twin-corrects).

---

## SOME_DELAY Routine (0xF97612) - Timing Delay

The `SOME_DELAY` routine provides millisecond-scale timing delays used throughout FDC operations.

### Disassembly

```asm
SOME_DELAY:                 ; F97612
    SRL 1, WA               ; Divide WA by 2 (logical shift right)
    LD DE, (SYSTEM_TIMESTAMP) ; Snapshot current timestamp
    LD HL, 0                ; Initialize timeout counter
    CP HL, 0ffffh           ; Initial check (always passes)
    RET NC                  ; (never triggers on first pass)

SOME_DELAY_Loop:               ; Polling loop
    LD BC, (SYSTEM_TIMESTAMP) ; Read current timestamp
    SUB BC, DE              ; Elapsed = current - start
    CP BC, WA               ; Compare elapsed to target
    RET UGT                 ; Return if elapsed > target (delay complete)
    INC 1, HL               ; Increment timeout counter
    CP HL, 0ffffh           ; Check for timeout (65535 iterations)
    JR C, SOME_DELAY_Loop      ; Continue polling
    RET                     ; Timeout exit (safety)
```

### Operation

1. **Input**: WA register contains the delay duration
2. **Division**: WA is divided by 2 (so actual delay is half the input value in ticks)
3. **Timing**: Polls SYSTEM_TIMESTAMP until elapsed time exceeds target
4. **Safety**: Timeout exits after 65535 loop iterations to prevent hangs

### SYSTEM_TIMESTAMP Source

`SYSTEM_TIMESTAMP` (address 0x0409) is a 32-bit counter incremented by the Timer 1 interrupt handler (`INTT1_HANDLER` at 0xEF0BF9). The timer is configured during system initialization:

```asm
; Timer configuration at EF042D
LD (T01MOD), 01dh   ; Timer 0/1 mode = 0x1D (timer 0 is never started; only timer 1 runs)
LD (TREG0), 00ah    ; Timer 0 reload = 10
LD (TREG1), 010h    ; Timer 1 reload = 16
SET 1, (T8RUN)      ; Start Timer 1
```

Each `SYSTEM_TIMESTAMP` tick is one Timer 1 interrupt. Timer 0 is never started (the only `T8RUN` write at boot, in `shared/boot_hw_init.s`, starts timer 1), so the two 8-bit timers are not cascaded, and the clock is the main CPU's 16 MHz, not the sub CPU's 20 MHz (see [CPU Subsystem]({{ site.baseurl }}/cpu-subsystem/)). The tick period has not been measured on hardware: a MAME trace measured about 582 ticks per second, about 1.7 ms per tick (see [SSF Presentation]({{ site.baseurl }}/ssf-presentation/#timer-is-working--song-data-missing-trace-result)). The millisecond figures below assume a 1 ms tick.

### Delay Formula

```
Actual_delay_ms = WA / 2
```

### Common FDC Delay Values

| WA Value   | Effective Delay | Usage Context                                             |
|------------|-----------------|-----------------------------------------------------------|
| 2          | ~1 ms           | Brief settling (FDC_INIT, FDC_CmdSeek)                    |
| 10 (0x0A)  | ~5 ms           | Hardware reset settle, FDC_CMD_ENABLE loop                |
| 16 (0x10)  | ~8 ms           | Seek/recalibrate settle (FDC_CmdSeek, FDC_CmdRecalibrate) |
| 200 (0xC8) | ~100 ms         | Motor spin-up, long operations                            |

### Usage in FDC Code

- **FDC_INIT (0xF96BBF)**: `WA=2` - 1ms delay after register setup
- **FDC_CONFIG_VERIFY**: `WA=2` - Settling delays between operations
- **FDC_CmdSeek**: `WA=2`, then `WA=0x10` - before and after the SEEK command
- **FDC_CMD_ENABLE loop (0xF97C40)**: `WA=0x0A` - 5ms delay per ready-check iteration
- **FDC Reset (0xF97ECF)**: `WA=0x0A` - Reset pulse timing

---

## FDC Memory Map

| Address     | Size | Name                                    | Description                                                                                                                                                               |
|-------------|------|-----------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 0x8A10      | 2    | —                                       | Media-probe flag: 0xFFFF while a caller probes the disk format; a one-sector read of track 0, head 0 then gets a single try (`FDC_DETECT_CHECK`, `FDC_DRIVE_DETECT`)      |
| 0x8A16      | 1    | FDC_STATUS_FLAG                         | Busy latch: 0xA5 while a request runs, 0x5A when it ends; a request that finds 0xA5 fails with 0xFB                                                                       |
| 0x8A1C      | 2    | FDC_SECTOR_COUNT                        | Transfer byte count, despite the name: sector size × sectors of one same-track burst for a read or write, ID bytes for a format; `FDC_Setup_DMA_Mode` loads it into DMAC3 |
| 0x8A1E      | 2    | FDC_SECTOR_SIZE                         | Sector size (0x200 or 0x400)                                                                                                                                              |
| 0x8A20      | 1    | FDC_INIT_FLAG                           | Initialization flag (0xFF=init done)                                                                                                                                      |
| 0x8A24      | 1    | FDC_ERROR_CODE                          | Current error code                                                                                                                                                        |
| 0x8A26      | 1    | FDC_CACHED_STATUS                       | Cached status value                                                                                                                                                       |
| 0x8A28      | 1    | FDC_COMMAND_REG                         | Command register                                                                                                                                                          |
| 0x8A2B-8A35 | -    | —                                       | uPD765 command parameters: C, H, R, N, EOT, GPL, DTL (0x8A2B-0x8A31), format SC, gap and filler (0x8A32-0x8A34), STP (0x8A35)                                             |
| 0x8A36      | 1    | FDC_TARGET_TRACK                        | Seek target cylinder, copied from the request's track                                                                                                                     |
| 0x8A40      | 2    | FDC_COMMAND_INDEX                       | Request +0x00: command number, the 0..11 dispatch index                                                                                                                   |
| 0x8A42      | 2    | —                                       | Request +0x02: drive                                                                                                                                                      |
| 0x8A44      | 2    | —                                       | Request +0x04: head (0 or 1); command 9 reads it as the new disk-changed flag                                                                                             |
| 0x8A46      | 2    | —                                       | Request +0x06: track (command 0: the media-type code)                                                                                                                     |
| 0x8A48      | 2    | —                                       | Request +0x08: starting sector (1-based)                                                                                                                                  |
| 0x8A4A      | 2    | —                                       | Request +0x0A: sector count                                                                                                                                               |
| 0x8A4C      | 4    | —                                       | Request +0x0C: buffer address, the DMA memory address; advanced by `FDC_SECTOR_COUNT` before each further burst (a format points it at RAM 0x8A70 instead)                |
| 0x8A5C      | 4    | —                                       | Mirror of the request's buffer address (+0x0C)                                                                                                                            |
| 0x8A68      | 1    | —                                       | Retry counter: 8 for a read or write (1 for a probe read); a failed burst decrements it, and at 0 the command fails with error 16 (read) or 32 (write)                    |
| 0x8A6A      | 1    | —                                       | Disk-changed flag: command 9 sets it to 0xFF (request +0x04 = 1) or 0 (= 0); cleared at initialization                                                                    |
| 0x8A6C      | 1    | FDC_DRIVE_MODE                          | Drive mode (0-5)                                                                                                                                                          |
| 0x8B00      | 1    | FDC_RESERVED_00                         | Reserved                                                                                                                                                                  |
| 0x8B04      | 1    | — (the source calls it the track cache) | Cylinder last sought to (0xFF = unknown); compared by `FDC_CmdSeek`                                                                                                       |
| 0x8B0C      | 2    | —                                       | One more than the sectors per track (10, 9 or 19 by media type); bounds the sector number in the read and write loops                                                     |
| 0x8B10      | 2    | —                                       | Starting sector, saved while the read and write loops count a batch of sectors                                                                                            |

Named in the source since 2026-10-03 (each maincpu tree's `shared/ram_variables.s`; v7 0x9C lower), only
where the code agrees with this table: `FDC_SECTOR_COUNT` (0x8A1C, cleared before each transfer burst; it counts
bytes, not sectors), `FDC_ERROR_CODE` (0x8A24, set by `FDC_Set_Status`), `FDC_COMMAND_INDEX` (0x8A40, the 0..11
dispatch index) and `FDC_TARGET_TRACK` (0x8A36, the cylinder `FDC_CmdSeek` seeks to).
`FDC_CommandEntry_CopyParams` copies the caller's 16-byte request block to 0x8A40-0x8A4F and again to
0x8A50-0x8A5F; the layout is the one the bootloader twin's
[`FDC_Request`](#fdc_request--the-single-public-entry-boot-0xffe944) takes.

## Routine Addresses

| Address  | Name                  | Description                                 |
|----------|-----------------------|---------------------------------------------|
| 0xF96BBF | FDC_INIT              | Basic FDC initialization                    |
| 0xF96BD0 | FDC_CONFIG_VERIFY     | Controller and drive (re)initialization     |
| 0xF96D95 | FDC_CMD_DISPATCH_SUB  | Command handler subroutine                  |
| 0xF97696 | FDC_CmdSeek           | Seek to the target cylinder (FDC command 2) |
| 0xF976E4 | FDC_CMD_EXEC          | Command execution handler                   |
| 0xF97835 | FDC_SECTOR_XFER       | Sector/data transfer handler                |
| 0xF97984 | FDC_MODE_CONFIG       | Mode configuration (Handler 5)              |
| 0xF97C21 | FDC_CMD_ENABLE        | Command enable setup                        |
| 0xF97C4B | FDC_CMD_DISABLE       | Command disable                             |
| 0xF97C54 | FDC_STATUS_COPY       | Copy cached status                          |
| 0xF97C5B | FDC_OUTPUT_CTRL       | Output control                              |
| 0xF97C7C | FDC_INTERRUPT_HANDLER | Main interrupt handler                      |

## Helper Routine Addresses

| Address  | Name             | Description                                         | Status         |
|----------|------------------|-----------------------------------------------------|----------------|
| 0xF97612 | SOME_DELAY       | Millisecond delay using SYSTEM_TIMESTAMP            | **Documented** |
| 0xF97544 | FDC_DRIVE_DETECT | FDC drive detection routine                         | Disassembled   |
| 0xF97592 | FDC_DRIVE_STATUS | FDC drive status routine                            | Disassembled   |
| 0xF975AC | FDC_PRE_OP_CHECK | No-op (a bare `ret`)                                | Disassembled   |
| 0xF975DC | FDC_TIMING_DELAY | Marks the result buffer empty (`ld (0x8A60), 0xFF`) | Disassembled   |
| 0xF975E2 | FDC_POST_OP      | FDC post-operation routine                          | Disassembled   |
| 0xF972F9 | FDC_CMD_SEND     | FDC command send routine                            | Disassembled   |
| 0xF974FE | FDC_DETECT_CHECK | FDC detection check routine                         | Disassembled   |

---

## Disassembled Routines

### FDC_INIT (0xF96BBF) - Basic FDC Initialization

Sends auxiliary command 36h (software reset), waits, and marks the cached head cylinder at 0x8B04 unknown (0xFF), which forces the next seek.

```asm
FDC_INIT:                   ; F96BBF
    LD WA, 0036h
    CALR FDC_Send_Command
    LD WA, 2
    CALR SOME_DELAY
    LD (8B04h), 0FFh
    RET
```

### FDC_CONFIG_VERIFY (0xF96BD0) - Configuration/Status Verification

(Re)initialises the controller and drive: software reset, drain pending interrupts, SPECIFY, select format, media-type configuration, motor on and recalibrate.

```asm
FDC_CONFIG_VERIFY:          ; F96BD0
    PUSH XIZ
    CALR FDC_ClearStatus_InitTimer
    CALR FDC_DRIVE_DETECT
    CP HL, 0FFFFh
    JR Z, FDC_CONFIG_L1
    CALR FDC_DRIVE_STATUS
    CP HL, 0FFFFh
    JR Z, FDC_CONFIG_L1
    LD (8B04h), 0FFh
FDC_CONFIG_L1:              ; F96BEB
    CP (8A20h), 0FFh
    JRL Z, FDC_CONFIG_EXIT
    LD (8A20h), 0FFh
    LD WA, 0036h
    CALR FDC_Send_Command
    LD WA, 2
    CALR SOME_DELAY
    CALR FDC_DRIVE_DETECT
    CP HL, 0FFFFh
    JR Z, FDC_CONFIG_L2
    CALR FDC_DRIVE_STATUS
    CP HL, 0FFFFh
    JR Z, FDC_CONFIG_L2
    CALR FDC_ClearStatus_InitTimer
    CALR FDC_CMD_DISPATCH_SUB
    CP (8A24h), 0
    JR Z, FDC_CONFIG_L3
    LD (8A20h), 0
    JRL T, FDC_CONFIG_EXIT
FDC_CONFIG_L3:              ; F96C2A - drain pending interrupts
    CALR FDC_Read_Status
    BIT 7, L                ; wait for RQM
    JR Z, FDC_CONFIG_L3
    ...                     ; if DIO=0: wait, then write 08h (SENSE INTERRUPT STATUS)
    ...                     ; read the result bytes into 8A61h..
    CALR FDC_Exception_Status_Decoder
    CP (8A61h), 80h         ; ST0 = 80h: nothing pending
    JR NZ, FDC_CONFIG_L3
FDC_CONFIG_L2:              ; F96C7B
    LD WA, 3                ; SPECIFY
    CALR FDC_CMD_SEND
    LD WA, 4Fh              ; aux: select format
    CALR FDC_CMD_SEND
    ...                     ; switch on (8A6Eh) & 0Fh via FDC_WaitReady_CaseTable:
                            ; drive mode 0-5 -> (8A6Ch), rate bits
    ...                     ; aux: rate | 0Bh (control internal mode)
    CALR FDC_CMD_ENABLE     ; motor on
    CALR FDC_CmdRecalibrate
    LD (8A20h), 0
FDC_CONFIG_EXIT:            ; F96D93
    POP XIZ
    RET
```

Each `FDC_CMD_SEND` call and the `FDC_CMD_ENABLE` call is followed by `CP (8A24h), 0`; on an
error the routine clears `8A20h` and exits.

### FDC_CMD_DISPATCH_SUB (0xF96D95) - Command Handler Subroutine

Primary handler that initializes FDC and returns status.
Called by: FDC_HANDLER_10 (dispatch table entry).

```asm
FDC_CMD_DISPATCH_SUB:       ; F96D95
    LD WA, 0036h
    CALR FDC_Send_Command
    LD WA, 2
    CALR SOME_DELAY
    CALR FDC_Read_Status
    CP L, 0FFh
    JR NZ, FDC_H10_OK
    LD WA, 00FCh
    CALR FDC_Set_Status
FDC_H10_OK:                 ; F96DAE
    LD HL, 0
    RET
```

### FDC_CmdSeek (0xF97696) - Seek Handler

Seeks the head to the target cylinder (0x8A36) unless the cached cylinder (0x8B04) already matches; on error invalidates the cache (0xFF). Renamed from the misnomer `FDC_STATUS_HANDLER` on 2026-08-21.

```asm
FDC_CmdSeek:                ; F97696
    LD A, (8A36h)
    CP A, (8B04h)
    RET Z
    LD (8B04h), (8A36h)
    LD WA, 2
    CALR SOME_DELAY
    CALR FDC_TIMING_DELAY
    LD WA, 000Fh
    CALR FDC_CMD_SEND
    CALR FDC_POST_OP
    CP (8A24h), 0
    JR Z, FDC_CmdSeek_Skip
    LD (8B04h), 0FFh
FDC_CmdSeek_Skip:           ; F976C3
    LD WA, 0010h
    JRL T, SOME_DELAY

; Submit MT|MF READ DATA (C6h), DMA3 armed
FDC_SubmitReadDataCmd:      ; F976C9
    LD (8A28h), 0C6h
    CALR FDC_Setup_DMA_Mode
    CALR FDC_TIMING_DELAY
    LD WA, 00C6h
    CALR FDC_CMD_SEND
    CP (8A24h), 0
    RET NZ
    JRL T, FDC_POST_OP
```

### FDC_CMD_EXEC (0xF976E4) - Command Execution Handler

Handles FDC command execution with detection and validation.

```asm
FDC_CMD_EXEC:               ; F976E4
    PUSH IZ
    CALR FDC_DETECT_CHECK
    CP HL, 0
    JR Z, FDC_CE_L1
    LD (8A68h), 001h
    JRL T, FDC_CE_DISPATCH  ; 0xF9782A
FDC_CE_L1:                  ; F976F4
    CALR FDC_DRIVE_DETECT
    CP HL, 0
    JR NZ, FDC_CE_L2
    LD (8A68h), 008h
    JRL T, FDC_CE_DISPATCH
FDC_CE_L2:                  ; F97703
    LD (8A68h), 001h
    JRL T, FDC_CE_DISPATCH

FDC_CE_PROCESS:             ; F9770B
    LD (8A24h), 0
    CALR FDC_CmdSeek
    CP (8A24h), 0
    JR Z, FDC_CE_L3
    LD A, (8A24h)
    LD IZL, A
    EXTS IZ
    CALR FDC_CONFIG_VERIFY
    LD A, IZL
    LD (8A24h), A
    JRL T, FDC_CE_EXIT      ; 0xF97833
FDC_CE_L3:                  ; F97730
    LD WA, (8A48h)
    CP WA, (8B0Ch)
    JR ULE, FDC_CE_L4
    LD (8A48h), 0001h
FDC_CE_L4:                  ; F97740
    LDW (8B10h), (8A48h)
    LDW (8A1Ch), 0          ; FDC_SECTOR_COUNT
    ; ... continues with more sector handling
```

### FDC_MODE_CONFIG (0xF97984) - Mode Configuration (Handler 5)

Configures FDC for different operating modes (0-5).

```asm
FDC_MODE_CONFIG:            ; F97984
    CALR FDC_PRE_OP_CHECK
    CP (8A24h), 0
    JRL NZ, FDC_MC_EXIT     ; 0xF97A3C
    CALR FDC_INTERRUPT_HANDLER
    CP (8A24h), 0
    JRL NZ, FDC_MC_EXIT
    CALR FDC_CmdRecalibrate      ; formerly FDC_SeekRecalibrate
    CP (8A24h), 0
    JRL NZ, FDC_MC_EXIT
    LD A, (8A6Ch)           ; Load FDC mode
    CP A, 2
    JR Z, FDC_MC_MODE2
    CP A, 3
    JR Z, FDC_MC_MODE3
    CP A, 5
    JR Z, FDC_MC_MODE045
    CP A, 4
    JR Z, FDC_MC_MODE045
    CP A, 0
    JR NZ, FDC_MC_COMMON
FDC_MC_MODE045:             ; F979BD - Mode 0, 4, 5
    LD (8A2Eh), 002h
    LD (8A33h), 050h
    JR T, FDC_MC_COMMON
FDC_MC_MODE3:               ; F979C9
    LD (8A2Eh), 002h
    LD (8A33h), 06Ch
    JR T, FDC_MC_COMMON
FDC_MC_MODE2:               ; F979D5
    LD (8A2Eh), 003h
    LD (8A33h), 074h
FDC_MC_COMMON:              ; F979DF
    LD (8A36h), 0
    LD (8A2Bh), 0
    LD (8A34h), 0E5h
    LD (8A2Ch), 0
    LD (8A29h), 0
    ; ... continues
```

### FDC_CMD_ENABLE (0xF97C21) - Command Enable Setup

Sets bit 3 at 0x28, waits for FDC ready.

```asm
FDC_CMD_ENABLE:             ; F97C21
    PUSH IZ
    SET 3, (28h)
    LD WA, 00FEh
    CALR FDC_CMD_SEND
    CP (8A24h), 0
    JR Z, FDC_CE_READY
    LD WA, 0031h
    CALR FDC_Set_Status
    JR T, FDC_CE_DONE
FDC_CE_READY:               ; F97C3A
    LD IZ, 1
    CP IZ, 0
    JR Z, FDC_CE_DONE
FDC_CE_LOOP:                ; F97C40
    LD WA, 000Ah
    CALR SOME_DELAY
    DJNZ IZ, FDC_CE_LOOP
FDC_CE_DONE:                ; F97C49
    POP IZ
    RET
```

### FDC_CMD_DISABLE (0xF97C4B) - Command Disable

Clears bit 3 at 0x28.

```asm
FDC_CMD_DISABLE:            ; F97C4B
    RES 3, (28h)
    LD WA, 000Eh
    JRL T, FDC_CMD_SEND
```

### FDC_STATUS_COPY (0xF97C54) - Copy Cached Status

Simple 2-instruction routine.

```asm
FDC_STATUS_COPY:            ; F97C54
    LD (8A24h), (8A26h)
    RET
```

### FDC_OUTPUT_CTRL (0xF97C5B) - Output Control

Controls FDC output based on value in 0x8A44.

```asm
FDC_OUTPUT_CTRL:            ; F97C5B
    LD WA, (8A44h)
    CP WA, 1
    JR Z, FDC_OC_ENABLE
    CP WA, 0
    JR NZ, FDC_OC_OTHER
    JR T, FDC_OC_DISABLE
FDC_OC_OTHER:               ; F97C69
    LD WA, 00FEh
    CALR FDC_Set_Status
    RET
FDC_OC_ENABLE:              ; F97C70
    LD (8A6Ah), 0FFh
    RET
FDC_OC_DISABLE:             ; F97C76
    LD (8A6Ah), 0
    RET
```

### FDC_INTERRUPT_HANDLER (0xF97C7C) - Main Interrupt Handler

Checks status and dispatches to appropriate handlers.

```asm
FDC_INTERRUPT_HANDLER:      ; F97C7C
    PUSH QIZ
    CP (8A24h), 0
    JR NZ, FDC_IH_EXIT
    LD WA, 4
    CALR FDC_CMD_SEND
    CP (8A24h), 0
    JR NZ, FDC_IH_EXIT
    CALR FDC_Wait_Ready_Timeout
    CP (8A24h), 0
    JR NZ, FDC_IH_EXIT
    CALR FDC_ReadDataRegister
    LD QIZH, L
    BIT 7, QIZH
    JR Z, FDC_IH_L1
    LD WA, 0032h
    CALR FDC_Set_Status
FDC_IH_L1:                  ; F97CAE
    BIT 5, QIZH
    JR NZ, FDC_IH_L2
    LD WA, 0031h
    CALR FDC_Set_Status
FDC_IH_L2:                  ; F97CBA
    BIT 6, QIZH
    JR Z, FDC_IH_EXIT
    LD WA, 002Fh
    CALR FDC_Set_Status
FDC_IH_EXIT:                ; F97CC6
    POP QIZ
    RET
```

### FDC_ByteTransfer_PIO (0xF97DEE) - PIO Fallback Transfer and the '+2 Quirk'

Non-DMA fallback used from the INT4 path when DMA channel 3 is not armed:
it moves ONE byte per call between the uPD72068 DMA-acknowledge data port
(`0x120000`) and the caller's buffer, decrementing the remaining-byte count
(`0x8A1C`). Request command 3 reads (port to buffer), command 4 writes
(buffer to port); any other command has no PIO path.

**uPD72068 PIO '+2 quirk'** (found during the bootloader FDC-driver
disassembly, `table_data/boot_fdc_driver.s`, routines `FDC_PIO_ReadTransfer`
/ `FDC_PIO_WriteTransfer`): in both drivers the running buffer pointer is
kept at **+2 into the 32-bit buffer field** of the request block. The
maincpu driver keeps its pointer at `0x8A4E` while the request's buffer
field is the 32-bit word at `0x8A4C`; the bootloader twin keeps its pointer
at `0x0C7C` while its buffer field is the 32-bit word at `0x0C7A`. The same
off-by-two displacement appearing in both independently assembled drivers
looks like a latent defect inherited from a common source. It is harmless
in practice because the DMA path is what ships; the PIO fallback is only
reached when DMA3 is not armed.

---

## Handler Dispatch Table (0xF97D8D)

The runtime driver dispatches through the 12-entry `u16` offset table
`FDC_CommandEntry_CopyParams_CaseTable` (formerly `FDC_HANDLER_OFFSETS`) at **0xEA98CA**, whose entries are relative to
`FDC_HANDLER_DISPATCH_BASE` at 0xF97D8D. The offsets in the ROM are
`0, 5, 13, 21, 29, 37, 45, 50, 55, 60, 65, 70`, which gives the handler entry points
below. These are the offsets read out of `kn5000_v10_program.rom`, and they agree with
`symbols/maincpu_symbols_reference.txt`.

The index is the **command number** of the request — the same numbering the bootloader
driver uses, which is how the "Command" column below is known:

| Cmd | Offset | Address  | Handler                     | Body                                       | Command meaning    |
|-----|--------|----------|-----------------------------|--------------------------------------------|--------------------|
| 0   | 0      | 0xF97D8D | `FDC_HANDLER_DISPATCH_BASE` | `FDC_InitSequence_Full`                    | initialize         |
| 1   | 5      | 0xF97D92 | `FDC_HANDLER_01`            | `FDC_CMD_ENABLE` + `FDC_CmdRecalibrate`    | recalibrate        |
| 2   | 13     | 0xF97D9A | `FDC_HANDLER_02`            | `FDC_CMD_ENABLE` + `FDC_CmdSeek`           | **seek**           |
| 3   | 21     | 0xF97DA2 | `FDC_HANDLER_03`            | `FDC_CMD_ENABLE` + `FDC_CMD_EXEC`          | **read sectors**   |
| 4   | 29     | 0xF97DAA | `FDC_HANDLER_04`            | `FDC_CMD_ENABLE` + `FDC_SECTOR_XFER`       | **write sectors**  |
| 5   | 37     | 0xF97DB2 | `FDC_HANDLER_05`            | `FDC_CMD_ENABLE` + `FDC_MODE_CONFIG`       | **format**         |
| 6   | 45     | 0xF97DBA | `FDC_HANDLER_06`            | `FDC_CMD_ENABLE` only                      | motor on           |
| 7   | 50     | 0xF97DBF | `FDC_HANDLER_07`            | `FDC_CMD_DISABLE`                          | motor off          |
| 8   | 55     | 0xF97DC4 | `FDC_HANDLER_08`            | `FDC_STATUS_COPY`                          | get last error     |
| 9   | 60     | 0xF97DC9 | `FDC_HANDLER_09`            | `FDC_OUTPUT_CTRL`                          | set disk-changed   |
| 10  | 65     | 0xF97DCE | `FDC_HANDLER_10`            | `FDC_CMD_DISPATCH_SUB`                     | controller reset   |
| 11  | 70     | 0xF97DD3 | `FDC_HANDLER_11`            | `FDC_CMD_ENABLE` + `FDC_INTERRUPT_HANDLER` | sense drive status |

All handlers end by jumping to `FDC_Handler_ExitStatus`, which sets the status flag and returns.

### What the boot twin corrects

The runtime driver's routine names were assigned before the command numbering was known,
and several of them describe the wrong thing. The bootloader twin (which *is* organised
by command) settles them:

| Runtime name                                            | Actually                                           | Bootloader twin           |
|---------------------------------------------------------|----------------------------------------------------|---------------------------|
| `FDC_CmdSeek` (0xF97696), formerly `FDC_STATUS_HANDLER` | the **SEEK** handler — the old name was a misnomer | `FDC_CmdSeek`             |
| `FDC_CMD_EXEC` (0xF976E4)                               | read sectors                                       | `FDC_CmdReadSectors`      |
| `FDC_SECTOR_XFER` (0xF97835)                            | write sectors                                      | `FDC_CmdWriteSectors`     |
| `FDC_MODE_CONFIG` (0xF97984)                            | format                                             | `FDC_CmdFormat`           |
| `FDC_CMD_ENABLE` (0xF97C21)                             | motor on                                           | `FDC_CmdMotorOn`          |
| `FDC_CMD_DISABLE` (0xF97C4B)                            | motor off                                          | `FDC_CmdMotorOff`         |
| `FDC_STATUS_COPY` (0xF97C54)                            | get last error                                     | `FDC_CmdGetLastError`     |
| `FDC_OUTPUT_CTRL` (0xF97C5B)                            | set disk-changed                                   | `FDC_CmdSetDiskChanged`   |
| `FDC_CMD_DISPATCH_SUB` (0xF96D95)                       | controller reset                                   | `FDC_CmdControllerReset`  |
| `FDC_INTERRUPT_HANDLER` (0xF97C7C)                      | sense drive status                                 | `FDC_CmdSenseDriveStatus` |

The maincpu source still carries the old names for all of these except the seek handler,
which was renamed `FDC_CmdSeek` on 2026-08-21 (and `FDC_SeekRecalibrate`, now
`FDC_CmdRecalibrate`); renaming the rest repo-wide is an open follow-up.

---

## The Bootloader's FDC Driver (ROM 0x9FD8A5-0x9FEA9C)

4,600 bytes in the Table Data ROM, running at the boot-time alias 0xFFD8A5-0xFFEA9C
(at reset the Table Data ROM is mapped at 0xE00000-0xFFFFFF, so boot address = ROM
address + 0x600000). It is the complete command layer of the bootloader's floppy driver for the uPD72068 at
IC208 — **not** the "Flash Update Type Handlers / Type 1..8 disk types" its old build
name `bootcode_flash_handlers.bin` suggests. Source: `table_data/boot_fdc_driver.s`.

### Hardware interfaces

| Interface | Use |
|-----------|-----|
| 0x110008 | uPD72068 main status register (read) / **auxiliary command** register (write) — 0x36 software reset, 0x33 enable external mode, `rate|0x0B` control internal mode, `drives|0x0E` enable motors, 0x4F select format |
| 0x11000A | data register: uPD765-style commands, parameters, result bytes |
| 0x120000 | DMA-acknowledge data port, used by DMA channel 3 and by the PIO fallback |
| DMA3 | DMAS3/DMAD3/DMAC3/DMAM3 (CR 0x0C/0x2C/0x4C/0x4E); mode 0x00 = I/O→memory, 0x08 = memory→I/O |
| Port A bit 3 (SFR 0x28) | drive motor / enable line |
| Port H bit 0 (SFR 0x44) | FDC TC (terminal count), pulsed by `FDC_PulseTC` |
| INTE45 / INTETC23 / INTCLR | INT4 (FDC IRQ) and INTTC3 (DMA3 end) enables |

Data-rate bits for the aux control-internal-mode command: 0x00 = 250 kbps, 0x40 = 500,
0x80 = 600, 0xC0 = 300.

### `FDC_Request` — the single public entry (boot 0xFFE944)

The caller pushes a pointer to a **16-byte request block**:

| Offset | Size | Field |
|--------|------|-------|
| +0x00 | u16 | command (0-11) |
| +0x02 | u16 | drive |
| +0x04 | u16 | head / flag |
| +0x06 | u16 | track / media-type code |
| +0x08 | u16 | starting sector |
| +0x0A | u16 | sector count |
| +0x0C | u32 | buffer address |

`FDC_Request` copies the block to RAM 0x0C6E.. and mirrors it at 0x0C7E.., rotates the
status history, validates, dispatches, then returns `HL` = the sign-extended sticky
status. A busy latch at RAM 0x0C44 (0xA5 = executing, 0x5A = done) makes the driver
non-re-entrant: a second request while one is running fails with error 0xFB. Command 0
is the exception — it always clears the latch and preempts.

### The three offset tables at 0x9FB496 and the `jp T, XIX+WA` idiom

Three tables of 16-bit offsets are packed together at ROM 0x9FB496-0x9FB4D1 (boot
0xFFB496). They were previously an unlabelled 60-byte `.byte` block; commit `0494f44`
symbolized them, which is what made the driver disassemblable at all — all three are
consumed by a computed jump of the form

```asm
        add   wa, wa                  ; index * 2
        lda   xix, <table address>
        ld    wa, (xix + wa)          ; fetch the 16-bit offset
        lda   xix, <target base>
        jp    T, XIX+WA               ; jump to base + offset
```

so without the tables the branch targets are unknown and the following bytes cannot be
decoded.

| Table | ROM address | Entries | Index | Base the offsets are relative to | Consumed at |
|-------|-------------|---------|-------|----------------------------------|-------------|
| `FDC_DiskTypeStanza_Offsets` | 0x9FB496 | 6 | low nibble of the media-type code (0x0C9C), values 0-5 | `FDC_MediaStanza_Type0` (0x9FD9A2) | boot 0xFFD98F, in `FDC_MediaConfigAndRecalibrate` |
| `FDC_ValidateCmd_Offsets` | 0x9FB4A2 | 12 | command number | `FDC_Validate_FormatParams` (0x9FDAAB) | boot 0xFFDA97, in `FDC_ValidateRequest` |
| `FDC_CommandDispatch_Offsets` | 0x9FB4BA | 12 | command number | `FDC_Dispatch_Initialize` (0x9FEA07) | boot 0xFFE9F4, in `FDC_Request` |

The values, read out of `kn5000_table_data.rom`:

* stanzas: `0, 21, 43, 65, 87, 108`
* validators: `0, 14, 14, 14, 14, 14, 8, 8, 8, 11, 8, 14` — only four distinct validators
  exist (format-params, accept-always, head/drive, drive+track+sector)
* dispatch stubs: `0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55` — twelve uniform 5-byte
  stubs, each `calr <handler>; jr T, FDC_Request__finish`

Media-type codes 6-15 skip the stanza table entirely and run `FDC_MediaStanza_Default`
(whose body is identical to type 0); commands > 11 skip the dispatch table and report
error 0xFF.

### Commands

| Cmd | Handler (boot addr)                  | Runtime twin            |
|-----|--------------------------------------|-------------------------|
| 0   | `FDC_CmdInitialize` (0xFFE2BD)       | `FDC_InitSequence_Full` |
| 1   | `FDC_CmdRecalibrate` (0xFFE2D6)      | `FDC_CmdRecalibrate`    |
| 2   | `FDC_CmdSeek` (0xFFE31A)             | `FDC_CmdSeek`           |
| 3   | `FDC_CmdReadSectors` (0xFFE368)      | `FDC_CMD_EXEC`          |
| 4   | `FDC_CmdWriteSectors` (0xFFE4AA)     | `FDC_SECTOR_XFER`       |
| 5   | `FDC_CmdFormat` (0xFFE5FE)           | `FDC_MODE_CONFIG`       |
| 6   | `FDC_CmdMotorOn` (0xFFE89B)          | `FDC_CMD_ENABLE`        |
| 7   | `FDC_CmdMotorOff` (0xFFE8C5)         | `FDC_CMD_DISABLE`       |
| 8   | `FDC_CmdGetLastError` (0xFFE8CE)     | `FDC_STATUS_COPY`       |
| 9   | `FDC_CmdSetDiskChanged` (0xFFE8D5)   | `FDC_OUTPUT_CTRL`       |
| 10  | `FDC_CmdControllerReset` (0xFFDA6A)  | `FDC_CMD_DISPATCH_SUB`  |
| 11  | `FDC_CmdSenseDriveStatus` (0xFFE8F6) | `FDC_INTERRUPT_HANDLER` |

`FDC_CmdInitialize` does a display refresh and a TC pulse, clears the disk-changed and
media-removed flags, enables INT4/INTTC3, strobes a software reset and then runs
`FDC_MediaConfigAndRecalibrate` (boot 0xFFD8A5) — the full drive/media (re)configuration:
aux reset 0x36, drain the result phase, SPECIFY, select-format, the media stanza, then
control-internal-mode, motor-on and a recalibrate. `FDC_CmdRecalibrate` seeks to track 5
first for head-load settling, then issues RECALIBRATE (0x07).

### Media geometry presets

`FDC_SetGeometryForDiskType` (boot 0xFFDBAD) writes one of three presets from the low
nibble of the media-type code:

| Media type | Geometry | Gaps (r/w, format) |
|------------|----------|--------------------|
| 0, 4, 5 | 9 x 512 B, 80 tracks | 0x1B / 0x54 (720 KB 2DD) |
| 2 | 8 x 1024 B, 77 tracks | 0x53 / 0x74 (2DD-8, 1024-byte sectors) |
| 3 | 18 x 512 B, 80 tracks | 0x1B / 0x6C (1.44 MB 2HD) |

The common tail derives SRT from the code's high nibble and fixes HUT = 0x0F, HLT = 1,
ND = 0, DTL = 0xFF. Unknown types raise error 0xFE.

### Error codes

Sticky per request — the first error wins (`FDC_Error`), and command 8 returns the
*previous* request's code:

| Code | Meaning | Code | Meaning |
|------|---------|------|---------|
| 0x01/0x02/0x03 | ready-wait timeouts | 0x33 | no data (sector not found) |
| 0x08 | unspecified FDC error | 0x34 | overrun |
| 0x09 | result-phase timeout | 0x35 | missing address mark |
| 0x10 | read retries exhausted | 0x36 | data CRC error |
| 0x20 | write retries exhausted | 0x37 | end of cylinder |
| 0x2F | write-protected | 0xFB | driver re-entered |
| 0x31 | drive not ready | 0xFC | controller not present |
| 0x32 | equipment check / fault | 0xFE | bad request parameters |
| | | 0xFF | no such command |

### `FDC_ProbeDiskFormat` — five requests that fingerprint the media

`FDC_ProbeDiskFormat` (ROM 0x9FEB3D, boot 0xFFEB3D) in `table_data/boot_disk_probe.s`
sits on top of `FDC_Request`. It sets `PHFC = 0x1E`, returns immediately if Port D bit 6
says there is no disk, then builds and submits five 16-byte request blocks at RAM 0x0D52:

| # | Command | Track | Sector | Count | Buffer |
|---|---------|-------|--------|-------|--------|
| 1 | 0 (initialize) | field = 0x00E0 | 0 | 0 | NULL |
| 2 | 3 (read sectors) | 0 | 1 | 1 | 0x0D62 |
| 3 | 3 | 78 | 1 | 1 | 0x0D62 |
| 4 | 3 | 10 | 1 | 1 | 0x0D62 |
| 5 | 3 | 40 | 1 | 1 | 0x0D62 |

Four single-sector reads at spread-out tracks: the pass/fail pattern across tracks
0/10/40/78 is what distinguishes the three geometry presets above. Afterwards it waits
200 ticks and increments a probe-pass counter at 0x104C.

Two caveats. The alternative track field 0x00D3 in request 1 is **dead code** — the
register it is selected on is always 0 at that point, so the `NZ` arm never runs. And
`FDC_ProbeDiskFormat` itself has **no caller**: an exhaustive search of the table_data
and maincpu ROMs for both address forms found no reference. It is retained factory or
diagnostic code; the shipped update path drives `FDC_Request` directly. The same is true
of the neighbouring `Boot_PulsePD0` (ROM 0x9FEB2B), whose Port D bit 0 line is not yet
identified. `Boot_CheckDiskPresent` (ROM 0x9FEC63) *is* live — it is the boot-time twin
of `Check_for_Floppy_Disk_Change` and reads the same active-low Port D bit 6.

## Code References

| Symbol                         | Address    | Purpose                                                                                                      |
|--------------------------------|------------|--------------------------------------------------------------------------------------------------------------|
| `SOME_DELAY`                   | `0xF97612` | Millisecond-scale timing delay (polls SYSTEM_TIMESTAMP)                                                      |
| `FDC_INIT`                     | `0xF96BBF` | Software reset (aux 36h); invalidates the track cache (0x8B04 = 0xFF)                                        |
| `FDC_CONFIG_VERIFY`            | `0xF96BD0` | Controller and drive (re)initialization (reset, SPECIFY, media setup, recalibrate)                           |
| `FDC_CMD_DISPATCH_SUB`         | `0xF96D95` | Primary command handler subroutine                                                                           |
| `FDC_CmdSeek`                  | `0xF97696` | Seek to the target cylinder (FDC command 2)                                                                  |
| `FDC_CMD_EXEC`                 | `0xF976E4` | Command execution with detection/validation                                                                  |
| `FDC_SECTOR_XFER`              | `0xF97835` | Sector/data transfer handler                                                                                 |
| `FDC_MODE_CONFIG`              | `0xF97984` | Mode configuration (modes 0-5)                                                                               |
| `FDC_CMD_ENABLE`               | `0xF97C21` | Enable FDC command interface                                                                                 |
| `FDC_CMD_DISABLE`              | `0xF97C4B` | Disable FDC command interface                                                                                |
| `FDC_STATUS_COPY`              | `0xF97C54` | Copy cached status register                                                                                  |
| `FDC_OUTPUT_CTRL`              | `0xF97C5B` | FDC output enable/disable control                                                                            |
| `FDC_INTERRUPT_HANDLER`        | `0xF97C7C` | Main FDC interrupt handler                                                                                   |
| `FDC_ByteTransfer_PIO`         | `0xF97DEE` | PIO fallback byte transfer (see the '+2 quirk' above)                                                        |
| `FDC_ReadSectors`              | `0xEF42CC` | Read sectors from floppy disc (update path, command 3)                                                       |
| `FDC_WriteSectors`             | `0xEF441B` | Write sectors to floppy disc                                                                                 |
| `Check_for_Floppy_Disk_Change` | `0xF98001` | Detect disc insertion/removal (Port D bit 6)                                                                 |
| `FDC_InitRecalibrate`          | `0xEF4241` | Re-initialize the drive (command 0, media code 0xD3, ending in a recalibrate); `FDC_ReadSectors`' retry path |

## MAME Emulation Status

> This table describes the **kn7000_mame overlay** build. In mainline MAME the `UPD72067` is instantiated but not mapped (`//FIXME: map(0x110000, ...)`), Port D bit 6 is unimplemented and no TC is wired, so a floppy cannot be read there yet; mainline offers only the `35hd` drive (mamedev/mame#16415).

| Component             | Status                     | Notes                                                                                                                                                                                                                                                                                                                                                                         |
|-----------------------|----------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| FDC device            | **Working**                | UPD72067 at 0x110008/0x11000A, 32MHz clock                                                                                                                                                                                                                                                                                                                                    |
| DMA data port         | **Working**                | 0x120000 for software DMA channel 3                                                                                                                                                                                                                                                                                                                                           |
| IRQ routing           | **Working**                | INT4 (command complete), INT5 (DRQ)                                                                                                                                                                                                                                                                                                                                           |
| Floppy connector      | **Working (overlay only)** | 3.5" HD drive on **unit 1** (`fdc:1`): the firmware sets US = 1 in every command (`FDC_CMD_SEND` builds the unit/head byte with `set 0, a`). Raw `.img` loads (PC formats registered, 2026-10-18); before that only MFI and other flux containers did                                                                                                                         |
| TC signal             | **Working (overlay only)** | Port H bit 0, strobed by the firmware's `FDC_Pulse_PH0` (from `INTTC3_HANDLER` at each DMA-3 end, at the end of a PIO transfer, and in `FDC_InitSequence_Full`): `m_maincpu->porth_write().set([this] (u8 data) { m_fdc->tc_w(BIT(data, 0)); })` (kn7000_mame 240a41f). Mainline wires no TC                                                                                  |
| Disk images           | **Available**              | v5-v10 firmware update disks from [archive.org](https://archive.org/details/technics-kn5000-system-update-disks). Mainline ships `hash/kn5000_flop.xml` (14 FAT12 reconstructions, mamedev/mame#16415), but mainline cannot load a `.img`, and the images are to be rebuilt on the KN5000's own formatted disk ([Floppy Disk Images]({{ site.baseurl }}/floppy-disk-images/)) |
| Disk present (FD.I/O) | **Working (overlay only)** | Port D bit 6, low while a disk is in the drive (a level; see below)                                                                                                                                                                                                                                                                                                           |
| Motor                 | **Working**                | `FDC_CMD_ENABLE` sets bit 3 of SFR 0x28 and sends auxiliary command `0xFE` (enable motors, all drives), which MAME's uPD72067 applies                                                                                                                                                                                                                                         |
| Ready (RDY)           | **Working (overlay only)** | tied active: the firmware issues its first SEEK about 5 ms after motor-on, far too soon for a drive's ready signal                                                                                                                                                                                                                                                            |
| Data rate             | **Working (overlay only)** | auxiliary command "control internal mode": `0x4B` before a 1.44 MB attempt (500 kbit/s), `0x0B` before 720 KB (250 kbit/s); MAME's uPD72067 acknowledges it without changing rate, so the driver applies it                                                                                                                                                                   |
| FORMAT                | **Working (overlay only)** | DISK TOOLS on a blank disk; FORMAT TRACK `4D 01 02 12 6C E5` (unit 1, 512-byte sectors, 18 per track, gap 0x6C, fill `E5`); the disk is byte-identical to the KN6000's and KN7000's ([Floppy Disk Images]({{ site.baseurl }}/floppy-disk-images/))                                                                                                                            |

**Test command (overlay build):** `kn7000 kn5000 -flop <disk_image.img>`

### Disk Present Signal (Port D Bit 6, FD.I/O)

The firmware reads Port D bit 6 as a **level**, low while a disk is in the drive.
`GetMediaType` reports "no disk" when it reads 1, without touching the drive, and
`Reset_Floppy_Disk_Controller` skips its seek sweep on 1 (`Check_for_Floppy_Disk_Change`, at
0xF98001, only reads the bit). Until 2026-10-18 the overlay fed it from MAME's
`floppy_image_device::dskchg_r()`, inverted. That is a disk-change latch, which only a head step
clears, and the firmware never steps while the line says "no disk". A disk present at power-on
worked, because the latch starts set, but a disk inserted while the instrument ran was never
seen: "ERROR 02! There is no disk in the disk drive." The line now follows whether a disk is in
the drive, which gives the same value at boot.

### Drive Unit, Ready and Data Rate

Three more defects stopped the KN5000 reading or formatting any disk in MAME. They were found
on 2026-10-18 by tapping the controller's registers while the firmware ran (kn7000_mame
`tools/floppy-images/runs-2026-10-18/`).

- **Unit 1.** Every command the firmware sends addresses drive 1 (SEEK `0F 01 05`, RECALIBRATE
  `07 01`, READ DATA `C6 01 ...`), and the driver had the drive on unit 0. Every command came
  back "not ready" (ST0 `0x69`/`0x49`), so every disk looked unformatted.
- **RDY.** With the unit right, the controller still waited for the drive's ready signal. The
  firmware sends motor-on (auxiliary `0xFE`) and seeks about 5 ms later, so on the board the
  controller's RDY input must be tied active (inferred from the firmware; the schematic net for
  that pin has not been traced).
- **Data rate.** The firmware selects 500 kbit/s with auxiliary command `0x4B` before trying a
  1.44 MB disk and 250 kbit/s with `0x0B` before 720 KB. MAME ignored the command, so every
  track was read and written at 250 kbit/s, and a disk the KN5000 formatted was saved as 720 KB.

### Terminal Count (TC)

TC terminates a multi-sector FDC transfer; without it a READ DATA never completes. The line
is Port H bit 0 (IC5 pin 145, PH0/TC0): boot leaves PH.0 as plain GPIO (PHFC = 0x1E), and
the firmware strobes it in `FDC_Pulse_PH0`, called from `INTTC3_HANDLER` when DMA channel 3
finishes, at the end of a PIO transfer and during initialization. An earlier driver bound
`to0_callback()`, the timer-0 match output, but this firmware never starts timer 0, so that
TC never fired. The overlay binds bit 0 of `m_maincpu->porth_write()` to `m_fdc->tc_w()`
(kn7000_mame 240a41f, 2026-09-03).

---

## See Also

- [Boot Sequence]({{ site.baseurl }}/boot-sequence/) - where the bootloader's FDC driver is used, and the rest of the first-stage bootloader
- [Boot CP-Serial Link]({{ site.baseurl }}/boot-cpserial-link/) - the bootloader's other big driver, disassembled in the same wave
- [Storage Subsystem]({{ site.baseurl }}/storage-subsystem/) - disk formats and the file system above the FDC
- [Firmware Update Procedure]({{ site.baseurl }}/firmware-update-procedure/) - the boot path that drives `FDC_Request`

---

*Last updated: October 2026*
