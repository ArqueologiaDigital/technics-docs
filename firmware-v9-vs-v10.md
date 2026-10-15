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

### 1. SubCPU Data Block Transfer: Two Small Fixes

The only code changes are two small edits in `audio/note_voice_mapping.s`, both described under The Engineering Story below. `SendPartDataBlock_DoGetError` gains an error check (+11 bytes), and the routine at `HdaeRom_DataDispatch_Block` turns its tail jump to `SendPartDataBlock_SetWord7` into a call followed by `ld hl, 0` and `ret` (+3 bytes). Every other differing byte is an address or branch displacement moved by those 14 bytes, apart from the version byte and the main-program version number.

The v10 version adds **14 bytes** of net code growth. Because both source trees use symbolic label references for function calls and data pointers, this address shift is invisible in the source diff — the linker resolves all labels automatically.

### 2. HDAE5000 Extension Data Handler

`HdaeRom_DataHandler` and `HdaeRom_DataDispatch` sit just after the first edit and move by 11 bytes. Aligned for that shift, their code is unchanged apart from three bytes of moved addresses; the dispatch table and the transfer protocol did not change. The second edit described under The Engineering Story is at the end of `HdaeRom_DataDispatch_Block`: the tail jump `jrl SendPartDataBlock_SetWord7` (v9 `0xFF03EA`) became `calr SendPartDataBlock_SetWord7`, `ld hl, 0`, `ret` (+3 bytes).

### 3. Flash Memory Save/Restore Adjustments

`Flash_GetSlotAddressAndSize` (formerly `TmFlash_WriteRoutine`), `PostTmLoad` and `PostTmSave` sit after the two edits. Aligned for the 14-byte shift, they differ only in moved addresses and branch displacements, like every other differing byte; their code did not change.

### 4. Debug Utility Code: Unchanged

`Debug_UartHelpers` (`0xFFFEB4`) and `ROM_PaddingFF` (`0xFFFEEB`) are byte-identical in v9 and v10. From `0xFFFE00` to the end of the ROM, the only byte that differs is the version byte at `0xFFFFE8`.

### 5. Version Byte

The firmware version identifier at address `0xFFFFE8` changed from `0x09` (v9) to `0x0A` (v10). This byte is read by `Get_Firmware_Version`; the MPVersion screen prints it (`MPver_ShowHide`, "Ver%2X"), and power-on combo 2 shows it on the panel LEDs.

### 6. Main-Program Version Number

One data word changed: `Softver_MainProgramVersion` in `naka_style_bitmaps.c` went from 1353 (`0x0549`) to 1354 (`0x054A`). It is the main-program version number that the SOFT VERSION screen shows, not a display parameter.

## What Did NOT Change

- **Boot sequence**: Identical initialization, self-test, and hardware setup.
- **UI framework**: All NAKA widget descriptors, screen layouts, and event handlers are identical (apart from the main-program version number above).
- **MIDI subsystem**: Core MIDI dispatch, SysEx handling, and serial I/O are unchanged.
- **Sequencer engine**: Song playback, SMF processing, and accompaniment are the same.
- **Display/VGA subsystem**: Graphics primitives, text rendering, and scoop display code are unchanged.
- **Floppy disk controller**: FDC routines are identical.
- **SubCPU boot ROM**: Same across all firmware versions.
- **Table Data ROM**: Same across all firmware versions.

---

## The Engineering Story

The v9-to-v10 firmware update tells a clear story when read at the instruction level. Matsushita's engineers made **one targeted change**, two small edits to the SubCPU data block transfer routines, and the rest of the ROM differences are mechanical consequences of that change.

### The First Edit: `SendPartDataBlock_DoGetError`

The change is in `SendPartDataBlock_DoGetError`, the sound-RAM subsystem's phase-2 handler (entry 2 of `SoundRam_HandlerTable`). The boot code runs it through `ScreenGroup_Dispatch` slot 2 when `SubCPU_Payload_GetErrorFlag` is non-zero; `MainSysControl` runs it during a system initialisation (`EVT_SYS_INI`); and the MIDI transfer-abort recovery (`MidiSysEx_RecoverAbortedXferGroup`) calls it for the sound-RAM data group. It does not verify a transfer.

**v9:**
```asm
SendPartDataBlock_DoGetError:
    ldw  wa, 0xff        ; packet bytes 0xFF, 0xFF
    ldw  bc, 0xff
    jp   COMM_BuildAndSendPacket   ; tail-call: send and return
```

**v10:**
```asm
SendPartDataBlock_DoGetError:
    call SubCPU_Payload_GetErrorFlag   ; HL = byte at 0x1E53E, sign-extended
    cp   hl, 0xffff                    ; is that byte 0xFF?
    ret  nz                            ; no: return without sending
    ldw  wa, 0xff
    ldw  bc, 0xff
    call COMM_BuildAndSendPacket       ; changed from jp to call
    ret                                ; explicit return
```

In v9, `SendPartDataBlock_DoGetError` sent its `0xFF`/`0xFF` message to the sub-CPU (`COMM_BuildAndSendPacket`) every time it was called. v10 first reads the flag byte at `0x1E53E` (`SubCPU_Payload_GetErrorFlag`) and sends the message only when that byte is `0xFF`; for `0x00` or `0x01` it returns without sending. The byte is `0xFF` when `SubCPU_Payload_Verify` finds no valid saved power-down state (the `0xF980` region fails its check) and `0x01` when only the `0xF180` region fails (see [Boot Sequence]({{ site.baseurl }}/boot-sequence/#welcome-screen-and-boot-animation)). Because the boot code runs the routine whenever the byte is non-zero (see [Subsystem Init Phases]({{ site.baseurl }}/boot-sequence/#subsystem-init-phases)), the two versions differ at boot only for `0x01`: v9 sent the message and v10 does not. `MainSysControl` sets the byte to `0xFF` (`SubCPU_PayloadErrorStore`) before it dispatches a system initialisation (`EVT_SYS_INI`), so that path still sends the message, and the MIDI transfer-abort recovery (`MidiSysEx_RecoverAbortedXferGroup`) now sends it only while the byte reads `0xFF`. This grew the function from 10 bytes to 21 bytes (**+11 bytes**).

### The Second Edit: Return Value Handling

A second change in the same region fixes return value handling:

**v9:**
```asm
    jrl  SendPartDataBlock_SetWord7   ; tail-jump (doesn't return here)
```

**v10:**
```asm
    calr SendPartDataBlock_SetWord7   ; call (returns here)
    ld   hl, 0:i3                     ; clear return value to "success"
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

### Single-Byte Differences

None of the five single-byte differences listed here is an independent fix. Item 1 is the main-program version number; items 2–5 are bytes of addresses or branch displacements moved by the 14-byte growth:

1. **Main-program version number** (`naka_style_bitmaps.c`): `Softver_MainProgramVersion` changed from 1353 (`0x0549`) to 1354 (`0x054A`), the number the SOFT VERSION screen shows as MAIN PROGRAM. It is a version bump, not a fix.

2. **Shifted address byte** (`demo/file_demo_proc.s`): `0xe5` → `0xf3` is +14, an address into the moved code.

3. **Shifted branch displacement** (`note_voice_mapping.s`, v9 `0xFF0558`): `0xe9` → `0xe6` is −3. It is the low byte of a `calr` displacement that spans the 3-byte second edit, not a 32-bit constant.

4. **Shifted address byte** (`note_voice_mapping.s`): `0xed` → `0xfb` is +14.

5. **Shifted address byte** (`note_voice_mapping.s`, v9 `0xFF0892`): `0x9b` → `0xa9` is +14, the low byte of the address `0xFF089B` → `0xFF08A9`; the `cp (xhl+8), sp` reading was a misdecode.

### Conclusion

**The v9-to-v10 update was a small, targeted code change.** v10 makes `SendPartDataBlock_DoGetError` send its `0xFF`/`0xFF` message only while the flag byte at `0x1E53E` reads `0xFF`, and makes `HdaeRom_DataDispatch_Block` return `HL = 0`. What that message does on the sub-CPU side, and so which user-visible fault the change addresses, has not been established.

The fix was surgical: add 14 bytes of error checking code, fix a return value corruption path, and let the existing 0xFF padding absorb the growth.

The 7-month gap between releases (January to August 1999) is consistent with a field-reported issue that required careful investigation and regression testing before deployment.

## Source Diff Statistics

On 2026-03-25 the source diff between the two trees was minimized to **95 lines** across 9 files (+ 2 entry point renames), from 5,388, and the table below describes that stage. Later the same day it reached 44 lines in 5 files (`diffs/v9_vs_v10_maincpu.diff` at kn5000-roms-disasm `46f2e935b`, not regenerated since). By then the address-cascade and callback rows had gone, and so had single-byte differences 3 and 4 listed above, which were disassembly misalignments. The trees have since been relabelled and restructured separately, so neither figure describes today's sources.

| Category                      | Files | Lines  | Description                                                                                                    |
|-------------------------------|-------|--------|----------------------------------------------------------------------------------------------------------------|
| SubCPU error handling fix     | 1     | ~15    | The core bug fix (+14 bytes)                                                                                   |
| Address cascade (`.long + N`) | 3     | ~14    | Pointer adjustments from code growth                                                                           |
| Callback address shift        | 1     | 4      | `Sprintf_OutputCallback` pushw values                                                                          |
| Padding absorption            | 1     | 2      | Fill size 12,710 -> 12,696                                                                                     |
| Version byte                  | 1     | 2      | `0x09` -> `0x0A`                                                                                               |
| Single-byte differences       | 2     | ~6     | Moved addresses and a branch displacement, not fixes (see [Single-Byte Differences](#single-byte-differences)) |
| **Total**                     | **9** | **95** |                                                                                                                |

```
Diff reduction history:
  Initial raw comparison:                5,388 lines
  After symbolic call/jp/lda_24:         ~300 lines
  After pointer offset elimination:        231 lines
  After parenthesized direct addr:        106 lines
  After symbolic calr + formatting:         95 lines (2026-03-25)
  After per-version .set aliases:           66 lines
  After raw .long data pointers:            52 lines
  After two disassembly alignment fixes:    44 lines (2026-03-25, kn5000-roms-disasm 46f2e935b)
```
