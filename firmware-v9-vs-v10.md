---
layout: page
title: "Firmware Changes: v9 vs v10"
permalink: /firmware-v9-vs-v10/
---

# Firmware Changes: Version 9 to Version 10

*Technics KN5000 Main CPU Program ROM — comparison of the last two firmware releases.*

**Version 9** was released January 26, 1999. **Version 10** (the final release) was released August 2, 1999.

Both ROMs are exactly 2 MB (2,097,152 bytes). Of those, **13,517 bytes differ** (0.64%). The changes are concentrated in a single subsystem: the **SubCPU data transfer and HDAE5000 extension handler** routines.

## Summary of Key Changes

### 1. Rewritten SubCPU Data Block Transfer (SendPartDataBlock)

The largest change is a complete rewrite of the `SendPartDataBlock` family of functions in `audio/note_voice_mapping.s`. This code handles transferring voice parameter data blocks between the main CPU and the tone generator SubCPU.

- **v9:** 2,906 bytes — uses a compact loop-based approach with shared parameter load routines
- **v10:** 2,920 bytes — restructured with explicit per-field copy sequences and additional validation

The v10 version adds **14 bytes** of net code growth. Because both source trees use symbolic label references for function calls and data pointers, this address shift is invisible in the source diff — the linker resolves all labels automatically.

### 2. Updated HDAE5000 Extension Data Handler

The `HdaeRom_DataHandler` and `HdaeRom_DataDispatch` routines — which manage communication with the optional HD-AE5000 hard disk expansion board — were revised. The dispatch table was restructured and the block transfer protocol adjusted. These changes are directly adjacent to the SendPartDataBlock rewrite.

### 3. Flash Memory Save/Restore Adjustments

The `TmFlash_WriteRoutine` (now `Flash_GetSlotAddressAndSize`) and `PostTmSave`/`PostTmLoad` functions received minor adjustments to their internal branch targets and parameter passing, likely to accommodate the SendPartDataBlock restructuring.

### 4. Debug Utility Code Changes

The `Debug_UartHelpers` and `ROM_PaddingFF` routines at the very end of the ROM (just before the interrupt vector table) contain different code between versions. The debug UART serial output helpers were adjusted — possibly reflecting changes to the debug console protocol or baud rate configuration.

### 5. Version Byte

The firmware version identifier at address `0xFFFFE8` changed from `0x09` (v9) to `0x0A` (v10). This byte is read by `Get_Firmware_Version` and displayed on the splash screen.

### 6. Widget Data Correction

One NAKA widget descriptor field changed: `naka_style_bitmaps.c` field `field_0772` went from `0x0549` to `0x054A` — a single-bit correction in a style bitmap display parameter.

## What Did NOT Change

- **Boot sequence**: Identical initialization, self-test, and hardware setup.
- **UI framework**: All NAKA widget descriptors, screen layouts, and event handlers are identical (except the one bitmap field above).
- **MIDI subsystem**: Core MIDI dispatch, SysEx handling, and serial I/O are unchanged.
- **Sequencer engine**: Song playback, SMF processing, and accompaniment are the same.
- **Display/VGA subsystem**: Graphics primitives, text rendering, and scoop display code are unchanged.
- **Floppy disk controller**: FDC routines are identical.
- **SubCPU boot ROM**: Same across all firmware versions.
- **Table Data ROM**: Same across all firmware versions.

---

## The Engineering Story

The v9-to-v10 firmware update tells a clear story when read at the instruction level. Matsushita's engineers made **one targeted fix** in the SubCPU voice parameter transfer system, and the rest of the ROM differences are mechanical consequences of that fix.

### The Bug: Silent Failures in SubCPU Communication

The root cause is in `SendPartDataBlock_DoGetError` -- the function called when the main CPU needs to verify that a data block transfer to the SubCPU completed successfully.

**v9 (broken):**
```asm
SendPartDataBlock_DoGetError:
    ldw  wa, 0xff        ; load "error" response
    ldw  bc, 0xff
    jp   COMM_BuildAndSendPacket   ; tail-call: send and return
```

**v10 (fixed):**
```asm
SendPartDataBlock_DoGetError:
    call SubCPU_Payload_GetErrorFlag   ; actually check for errors
    cp   hl, 0xffff                    ; was there an error?
    ret  nz                            ; if yes, abort early
    ldw  wa, 0xff
    ldw  bc, 0xff
    call COMM_BuildAndSendPacket       ; changed from jp to call
    ret                                ; explicit return
```

In v9, `DoGetError` was **not checking for errors at all**. It blindly sent a "success" packet regardless of whether the SubCPU payload transfer actually succeeded. The v10 fix adds a call to `SubCPU_Payload_GetErrorFlag`, checks the return value, and aborts early if an error occurred. This grew the function from 10 bytes to 21 bytes (**+11 bytes**).

### The Second Fix: Return Value Corruption

A second change in the same region fixes return value handling:

**v9:**
```asm
    jrl  SendPartDataBlock_SetWord7   ; tail-jump (doesn't return here)
```

**v10:**
```asm
    calr SendPartDataBlock_SetWord7   ; call (returns here)
    lds  hl, 0                        ; clear return value to "success"
    ret                               ; explicit return
```

In v9, this was a tail-jump -- control flow never returned. In v10, it became a proper call followed by clearing `hl` to zero (indicating success) before returning. This suggests the v9 version could leave stale data in `hl` that callers would misinterpret as an error code. This added **+3 bytes**.

**Total intentional code growth: 11 + 3 = 14 bytes.**

### The Cascade: How 14 Bytes Become 13,517

The KN5000's 2MB ROM has no relocatable linking at runtime -- all addresses are hardcoded. When 14 bytes of code were inserted in the middle of `note_voice_mapping.s`, every absolute address pointing to code *after* that insertion point shifted. This cascade explains every other difference in the diff:

| Consequence | Files | Diff Lines | Explanation |
|-------------|-------|------------|-------------|
| `.long` pointers shifted +14 | 2 | 6 | Data tables in `smf_event_processor.s` and `flash_floppy_handlers.s` contain 32-bit pointers to functions that moved |
| `.long` pointers shifted +11 | 1 | 8 | `widget_dispatch.s` NAKA descriptors point to `SendPartDataBlock_Data2/Data3`, which are *inside* the modified region -- they shifted by 11 (only past the first fix, not both) |
| `pushw` callback address shifted | 1 | 4 | `Sprintf_OutputCallback` address split across two `pushw` instructions |
| Fill padding absorbed the growth | 1 | 2 | `Sprintf_FillToVectors` shrank from 12,710 to 12,696 bytes of 0xFF padding |
| Version byte | 1 | 2 | `0x09` -> `0x0A` at address `0xFFFFE8` |

### Unrelated Single-Byte Fixes

Five single-byte differences appear to be opportunistic fixes made during the same release cycle, unrelated to the SubCPU error-handling bug:

1. **Widget bitmap parameter** (`naka_style_bitmaps.c`): `field_0772` changed from `0x0549` to `0x054A` (+1). Likely a cosmetic UI fix -- an off-by-one in a display size or position for a style bitmap widget.

2. **Data table prefix** (`demo/file_demo_proc.s`): byte `0xe5` changed to `0xf3`. In a bytecode/data table region surrounded by `swi` instructions, this changed a table entry from one addressing mode prefix to another.

3. **32-bit constant** (`note_voice_mapping.s`): `0xe91e376f` changed to `0xe61e376f`. The high byte changed from `0xe9` to `0xe6` in a constant loaded during `TmFlashWrite_Block1_Entry` -- a flash memory write configuration value.

4. **Invalid opcode fix** (`note_voice_mapping.s`): `.byte 0xed` (not a valid TLCS-900 opcode) changed to `swi 3` (`0xfb`). Located in a jump table, this was likely a corrupted table entry in v9 that was corrected in v10.

5. **Register correction** (`note_voice_mapping.s`): `cp (xhl+8), sp` changed to `cp (xbc+8), xsp`. The base register changed from XHL to XBC -- a bug fix where v9 was comparing against the wrong register pair.

### Conclusion

**The v9-to-v10 update was a targeted reliability fix.** The SubCPU data transfer system in v9 had a silent failure mode: when the SubCPU reported a payload error, the main CPU ignored it and sent a "success" response anyway. This could cause the tone generator to operate with corrupted voice parameters -- resulting in wrong sounds, missing notes, or audio glitches that would be difficult to reproduce and diagnose.

The fix was surgical: add 14 bytes of error checking code, fix a return value corruption path, and let the existing 0xFF padding absorb the growth. The additional single-byte changes suggest the engineers also addressed a few minor bugs discovered during the same testing cycle.

The 7-month gap between releases (January to August 1999) is consistent with a field-reported issue that required careful investigation and regression testing before deployment.

## Source Diff Statistics

**95 lines** across 9 files (+ 2 entry point renames). Systematically minimized from 5,388 lines through symbolic references, parenthesized operands, and normalized formatting.

| Category | Files | Lines | Description |
|----------|-------|-------|-------------|
| SubCPU error handling fix | 1 | ~15 | The core bug fix (+14 bytes) |
| Address cascade (`.long + N`) | 3 | ~14 | Pointer adjustments from code growth |
| Callback address shift | 1 | 4 | `Sprintf_OutputCallback` pushw values |
| Padding absorption | 1 | 2 | Fill size 12,710 -> 12,696 |
| Version byte | 1 | 2 | `0x09` -> `0x0A` |
| Unrelated single-byte fixes | 2 | ~6 | Constants, opcodes, registers |
| **Total** | **9** | **95** | |

```
Diff reduction history:
  Initial raw comparison:                5,388 lines
  After symbolic call/jp/lda_24:         ~300 lines
  After pointer offset elimination:        231 lines
  After parenthesized direct addr:        106 lines
  After symbolic calr + formatting:         95 lines (current)
```
