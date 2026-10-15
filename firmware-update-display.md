---
layout: page
title: Firmware Update Display
permalink: /firmware-update-display/
---

# Firmware Update Display State Machine

During firmware updates, the KN5000 displays status messages on the LCD using pre-rendered 1-bit bitmap images stored in the Program ROM. This page documents the complete display state machine, correlating each bitmap with its update stage and the code that triggers it.

## Bitmap Messages

All update bitmaps are 224 pixels wide x 22 pixels tall, stored as packed 1bpp data (28 bytes/row x 22 rows = 616 bytes each). They are rendered by `Draw_FlashMemUpdate_message_bitmap` (`0xEF5040`), which unpacks each bit to an 8bpp pixel and blits to VRAM via an offscreen buffer at `0x43C00`.

| Bitmap | ROM Address | Message Text | Display Parameters |
|--------|-------------|-------------|-------------------|
| `Bitmap_1bit_Please_Wait` | `0xE00B2E` | "Please Wait !!" | X=48, Y=80, FG=8, BG=3 |
| `Bitmap_1bit_Flash_Memory_Update` | `0xE0018E` | "Flash Memory Update" | X=48, Y=80, FG=8, BG=2 |
| `Bitmap_1bit_Now_Erasing` | `0xE003F6` | "Now Erasing!!" | X=48, Y=160, FG=8, BG=2 |
| `Bitmap_1bit_FD_to_Flash_Memory` | `0xE0065E` | "FD -> Flash Memory" | X=48, Y=160, FG=8, BG=2 |
| `Bitmap_1bit_Completed` | `0xE008C6` | "Completed!" | X=48, Y=160, FG=8, BG=1 |
| `Bitmap_1bit_Turn_On_AGAIN` | `0xE01266` | "Turn On AGAIN !!" | X=48, Y=200, FG=8, BG=1 |
| `Bitmap_1bit_Change_FD_2_of_2` | `0xE00D96` | "Change FD (2/2)" | X=48, Y=160, FG=8, BG=2 |
| `Bitmap_1bit_Illegal_Disk` | `0xE00FFE` | "Illegal Disk!" | X=48, Y=160, FG=8, BG=2 |

FG/BG values are palette indices pushed onto the stack before calling the draw routine. BG=1 appears to be used for "final" messages (completion), BG=2 for "in-progress" messages, and BG=3 for the initial boot wait screen.

## Rendering: Draw_FlashMemUpdate_message_bitmap

**Address:** `0xEF5040`

**Input:**
- XWA = pointer to 1bpp bitmap data (24-bit ROM address)
- BC = X start coordinate (left edge)
- DE = Y start coordinate (top edge)
- Stack: foreground color (byte), background color (byte)

**Algorithm:**
1. For each byte in the 616-byte bitmap (28 bytes x 22 rows):
2. Divide byte index by 28 to determine the current row
3. For each bit in the byte, use a bit mask lookup table (at DRAM address from `0xE34A`)
4. If bit is set: write foreground color to pixel; otherwise: write background color
5. Pixel address = offscreen buffer (`0x43C00`) + Y*320 + X
6. After rendering all pixels, blit the entire offscreen buffer to VRAM

The Y*320 multiplication uses the shift-add trick: `(Y << 2 + Y) << 6 = Y * 320`, matching the 320-pixel LCD width.

## Progress Bar

During flash erase operations, `Flash_BurnWithProgress` (`0xEF4702`) displays an animated progress bar:

- **Initial X position:** 50 pixels (0x32)
- **Y position:** 180 pixels (0xB4)
- **Bar height:** 5 pixels
- **Step size:** 8 pixels per increment
- **Increment trigger:** each time more than 500 (0x1F4) timer ticks have elapsed

The progress bar grows left-to-right while `Flash_BurnWithProgress` waits for the table-data chip erase (`TableDataFlash_ChipErase`) to finish, polling P7 bit 5 through `HDAE5000_Status_Check`. The counter is `SYSTEM_TIMESTAMP` (RAM `0x409` = 1033), which `INTT1_HANDLER` increments on every timer tick; when it exceeds 500, the bar extends by 8 pixels and the counter is cleared.

The bar is drawn using `VRAM_FillRect` with parameters (X=IZ, Y=0xB4, width implied, height=5).

## State Machine

### Entry Conditions

The firmware update is triggered during boot when **all three conditions** are met:
1. Firmware version byte at `0xFFFFE8` equals `0xFF` (update-mode sentinel)
2. A floppy disc is present (disc change signal on port PD bit 6)
3. Button scan returns value 4 (specific key held during boot)

### Boot-Time Pre-Update Display

```
[Power On]
    |
    v
MainCPU_self_test_routines
    |
    v
Get_Firmware_Version == 0xFF?
    |yes                    |no
    v                       v
"Please Wait !!"       Normal boot
(at Y=80, BG=3)        sequence
    |
    v
[Task scheduler, region code, flash init, HD-AE5000 PPI, sequencer and panel init, button scan]
    |
    v
Floppy present AND button==4?
    |yes                    |no
    v                       v
FLASH_MEM_UPDATE        Normal boot
    |
    v
[infinite loop at 0xEF05E6 after return]
```

### Main Update Flow (FLASH_MEM_UPDATE at 0xEF4F6F)

```
FLASH_MEM_UPDATE
    |
    v
Check floppy present ──no──> Return (no update)
    |yes
    v
FDC_InitRecalibrate
    |
    v
Detect_Disk_Type ──> type stored in register pointer 0xFB
    |
    v
Region 4, or HDAE5000_Detect (0xEF3D0E) fails ──> Skip to HDAE5000 path
    |
    v
Is type == 6 (HDAE5000)? ──yes──> Skip to HDAE5000 path
    |no
    v
╔══════════════════════════════════╗
║  "Flash Memory Update"          ║
║  (at Y=80, BG=2)                ║
╚══════════════════════════════════╝
    |
    v
Erase_and_Burn____when_disk_is_valid(type)
    |
    v
╔══════════════════════════════════╗
║  "Completed!"                   ║
║  (at Y=160, BG=1)               ║
╠══════════════════════════════════╣
║  "Turn On AGAIN !!"             ║
║  (at Y=200, BG=1)               ║
╚══════════════════════════════════╝
    |
    v
[Check for HDAE5000 update too]
    |
    v
Return → infinite loop
```

### HDAE5000-Specific Path

When the detected disc type is 6 (HDAE5000 extension firmware), the firmware:
1. Validates the HDAE5000 flash chip with `Flash_IdentifyAndValidateChip`
2. If flash chip not found → skip (no update)
3. Otherwise: displays "Flash Memory Update", erases and programs, then shows "Completed!" + "Turn On AGAIN!!"

The HDAE5000 path uses `Flash_WaitUntilReady` before programming and writes uncompressed data directly to flash at `0x280000`.

### Erase and Burn State Machine

`Erase_and_Burn____when_disk_is_valid` (`0xEF4745`) handles all non-HDAE5000 update types:

```
Erase_and_Burn
    |
    v
╔══════════════════════════════════╗
║  "Now Erasing!!"                ║
║  (at Y=160, BG=2)               ║
╚══════════════════════════════════╝
    |
    v
Validate type (1-8 range)
    |invalid               |valid
    v                      v
"Illegal Disk!"        Jump to type-specific handler
(infinite halt)        via offset table at 0xE00178
```

### Per-Type Handler Display Sequences

Each update type has a specific handler that shows different sequences of messages:

#### Type 7: Program ROM (Compressed)

```
"Now Erasing!!"
    |
    v
Erase flash sectors at 0x3E0000 and 0x3F0000
    |
    v
Flash_BurnWithProgress (with progress bar)
    |
    v
"FD -> Flash Memory"
    |
    v
LZ_Decompress_Init + LZSS_Decompress_ToFlash
    |
    v
Return → "Completed!" + "Turn On AGAIN!!"
```

#### Type 8: Table Data ROM (Compressed)

```
"Now Erasing!!"
    |
    v
Flash_BurnWithProgress (with progress bar)
    |
    v
"FD -> Flash Memory"
    |
    v
LZ_Decompress_Init
    |
    v
Return → "Completed!" + "Turn On AGAIN!!"
```

#### Types 1/3: Program/Table Data (Uncompressed, Disc 1 of 2)

```
"Now Erasing!!"
    |
    v
Flash_BurnWithProgress (with progress bar)
    |
    v
"FD -> Flash Memory"
    |
    v
FDC_WriteSectors (first half to 0x800000)
    |
    v
"Change FD (2/2)"  ←── wait for disc swap
    |
    v
[User removes disc 1, inserts disc 2]
    |
    v
[Wait for disc removal detected]
    |
    v
[Delay loop: 0x40000 iterations]
    |
    v
[Wait for new disc insertion detected]
    |
    v
[Delay loop: 0x200000 iterations]
    |
    v
Detect_Disk_Type (verify disc 2 matches)
    |mismatch              |match
    v                      v
Loop back to          "FD -> Flash Memory"
"Change FD (2/2)"         |
                           v
                      FDC_WriteSectors (second half to 0x900000)
                           |
                           v
                      Return → "Completed!" + "Turn On AGAIN!!"
```

#### Types 2/4: Program/Table Data (Disc 2 of 2 inserted first)

These are **invalid starting discs**. If the user inserts disc 2 first, the handler immediately jumps to `SHOW_ILLEGAL_DISK_MESSAGE` and halts.

#### Type 5: Custom Data (CMPCUSTOMDATA, written verbatim)

```
"Now Erasing!!"
    |
    v
Flash_WaitUntilReady (target: Custom Data Flash)
    |
    v
"FD -> Flash Memory"
    |
    v
FDC_WriteSectors_Compressed (to 0x300000)
    |
    v
Return → "Completed!" + "Turn On AGAIN!!"
```

#### Type 6: HDAE5000 Extension

```
"Now Erasing!!"
    |
    v
Flash_WaitUntilReady (target: Extension ROM)
    |
    v
"FD -> Flash Memory"
    |
    v
FDC_WriteSectors_Compressed (to 0x280000)
    |
    v
Return → "Completed!" + "Turn On AGAIN!!"
```

## Error States

### Illegal Disk (Fatal)

Displayed when:
- Disc type code is outside range 1-8 (after subtracting 1)
- Types 2 or 4 are used as the starting disc (these are "disc 2 of 2" and cannot start an update)

**Address:** `SHOW_ILLEGAL_DISK_MESSAGE` (`0xEF482A`)

After displaying "Illegal Disk!", the firmware enters an **infinite loop** (`jr IllegalDisk_HaltLoop` at address `0xEF4841`). The only recovery is power cycling the keyboard.

### Disc Swap Mismatch

When a 2-disc update (types 1/3) prompts for disc 2, it re-runs `Detect_Disk_Type` after the swap. If the new disc doesn't match the expected type, the "Change FD (2/2)" message is shown again in a retry loop. This is not a fatal error — the user can try inserting the correct disc.

### Flash Hardware Not Found

If `Flash_IdentifyAndValidateChip` returns `0xFFFF` for the HDAE5000 path, the update is silently skipped (no error message). For the main ROM path, if `0xEF3D0E` returns `0xFFFFFFFF`, the non-HDAE5000 erase/burn is skipped.

## LCD Layout During Update

The update messages are positioned vertically on the 320x240 LCD:

```
Y=0   ┌────────────────────────────────────────┐
      │                                        │
Y=80  │  "Flash Memory Update"  (or "Please    │
      │   Wait !!" during initial boot)        │
      │                                        │
Y=160 │  "Now Erasing!!" → "FD -> Flash"       │
      │  → "Completed!" (messages replace      │
      │  each other at the same Y position)    │
      │                                        │
Y=180 │  ████████████████  (progress bar)      │
      │                                        │
Y=200 │  "Turn On AGAIN !!"                    │
      │                                        │
Y=240 └────────────────────────────────────────┘
```

Messages at Y=160 are displayed sequentially (each new message overwrites the previous one at the same screen position). The title at Y=80 remains visible throughout.

## Code References

| Symbol                                 | Address    | Purpose                          |
|----------------------------------------|------------|----------------------------------|
| `FLASH_MEM_UPDATE`                     | `0xEF4F6F` | Main entry point                 |
| `Draw_FlashMemUpdate_message_bitmap`   | `0xEF5040` | 1bpp bitmap renderer             |
| `SHOW_FD_TO_FLASH_MEMORY_MESSAGE`      | `0xEF468E` | Display "FD -> Flash Memory"     |
| `SHOW_ILLEGAL_DISK_MESSAGE`            | `0xEF482A` | Display "Illegal Disk!" + halt   |
| `SHOW_CHANGE_FLOPPY_2_OF_2_MESSAGE`    | `0xEF46A8` | Display "Change FD (2/2)" + wait |
| `Flash_BurnWithProgress`               | `0xEF4702` | Erase with progress bar          |
| `Erase_and_Burn____when_disk_is_valid` | `0xEF4745` | Type dispatcher                  |
| `Detect_Disk_Type`                     | `0xEF42FE` | Identify floppy disc type        |
| `We_seem_to_be_running_boot_ROM_code`  | `0xEF0536` | Initial "Please Wait" display    |

## References

- [System Update Discs]({{ site.baseurl }}/system-update-discs/) — Disc format, signatures, and file contents
- [Flash Programming]({{ site.baseurl }}/flash-programming/) — Flash erase/program routines and hardware details
- [LZSS Compression]({{ site.baseurl }}/lzss-compression/) — SLIDE4K format used by compressed update types

---

*Last updated: October 2026*
