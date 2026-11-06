---
layout: page
title: Display Subsystem
permalink: /display-subsystem/
---

# Display Subsystem

## Overview

The KN5000 uses a 320x240 color LCD driven by an MN89304 VGA-compatible controller. The display shows menus, parameters, song information, and graphical elements. Display updates are driven by the firmware's main event loop (not by a vertical blank interrupt).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        MAIN CPU                              │
│                                                              │
│  Graphics routines in Main ROM                              │
│  UI framework manages pages and widgets                     │
│  Display updates in main event loop (not VBI)               │
└─────────────────────────────────────────────────────────────┘
                              │
                              v
┌─────────────────────────────────────────────────────────────┐
│                    MN89304 VGA CONTROLLER                    │
│                                                              │
│  Memory-mapped I/O: 0x1703B0-0x1703DF                       │
│  Resolution: 320 x 240 pixels                                │
│  Color depth: 8-bit indexed (256 colors)                    │
│  RAMDAC: 4-bit per channel (12-bit RGB)                     │
│  Row offset: svga_device::offset() << 3 (8x multiplier)    │
└─────────────────────────────────────────────────────────────┘
                              │
                              v
┌─────────────────────────────────────────────────────────────┐
│                 VIDEO RAM (0x1A0000-0x1DFFFF)               │
│                                                              │
│  256KB linear framebuffer                                    │
│  Active area: 76,800 bytes (320 x 240 x 1 byte/pixel)      │
│  Row stride: 320 bytes                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              v
┌─────────────────────────────────────────────────────────────┐
│                      LCD PANEL                               │
│                                                              │
│  320 x 240 color TFT LCD                                    │
│  Backlit display                                             │
└─────────────────────────────────────────────────────────────┘
```

## MN89304 VGA Controller

The MN89304 is a VGA-compatible LCD controller with some important differences from standard VGA:

### Key Differences from Standard VGA

| Property | Standard VGA | MN89304 (KN5000) |
|----------|-------------|-------------------|
| DAC resolution | 6-bit per channel (0-63) | **4-bit per channel (0-15)** |
| Palette color depth | 18-bit RGB | **12-bit RGB** |
| Row pitch calculation | `offset` register value | `offset << 3` (8x multiplier) |
| I/O base | CPU port space | Memory-mapped at 0x170000 |

### VGA Register Map

VGA I/O ports are memory-mapped to CPU address `0x170000 + port_number`:

| VGA Port | CPU Address | Register | Access | Description |
|----------|-------------|----------|--------|-------------|
| 0x3C0 | 0x1703C0 | Attribute Controller | W | Address/Data (alternating writes) |
| 0x3C2 | 0x1703C2 | Misc Output | W | Clock select, sync polarity |
| 0x3C3 | 0x1703C3 | VGA Enable | W | Global enable (write 0x01 to enable) |
| 0x3C4 | 0x1703C4 | Sequencer Index | W | Select sequencer register |
| 0x3C5 | 0x1703C5 | Sequencer Data | R/W | Sequencer register data |
| 0x3C6 | 0x1703C6 | DAC Mask | R/W | Palette mask (typically 0xFF) |
| 0x3C7 | 0x1703C7 | DAC Read Index | W | Select palette entry for reading |
| 0x3C8 | 0x1703C8 | DAC Write Index | W | Select palette entry for writing |
| 0x3C9 | 0x1703C9 | DAC Data | R/W | RGB data (3 sequential bytes per entry) |
| 0x3CE | 0x1703CE | Graphics Controller Index | W | Select GC register |
| 0x3CF | 0x1703CF | Graphics Controller Data | R/W | GC register data |
| 0x3D4 | 0x1703D4 | CRTC Index | W | Select CRTC register |
| 0x3D5 | 0x1703D5 | CRTC Data | R/W | CRTC register data |
| 0x3DA | 0x1703DA | Input Status 1 | R | Vertical retrace status |

### VGA Initialization Values

The `VGA_Setup` routine (0xEF55A7) configures the full register set at boot. Key values:

**Sequencer Registers (via ports 0x3C4/0x3C5):**

| Index     | Value         | Description                                                                              |
|-----------|---------------|------------------------------------------------------------------------------------------|
| 0x00      | 0x03          | Reset (synchronous)                                                                      |
| 0x01      | 0x21          | Clocking Mode (screen off during init; 0x01 = screen on)                                 |
| 0x02      | 0x0F          | Map Mask (all 4 planes enabled)                                                          |
| 0x03      | 0x00          | Character Map Select                                                                     |
| 0x04      | 0x06          | Memory Mode (chain-4, no odd/even)                                                       |
| 0x06      | 0x01 ... 0x00 | MN89304 extension lock: written 0x01 before and 0x00 after every extended-register write |
| 0x07-0x13 | see below     | MN89304 extended registers ([MN89304 Extended Registers](#mn89304-extended-registers))   |

**CRTC Timing Registers (via ports 0x3D4/0x3D5):**

| Index | Value     | Description                                 |
|-------|-----------|---------------------------------------------|
| 0x00  | 0x65      | Horizontal Total (101 chars)                |
| 0x01  | 0x27      | Horizontal Display End (39 chars = 320px/8) |
| 0x04  | 0x28      | Start Horizontal Retrace                    |
| 0x05  | 0x29      | End Horizontal Retrace                      |
| 0x06  | 0xF3      | Vertical Total (243 lines)                  |
| 0x07  | 0x00      | Overflow                                    |
| 0x10  | 0xF2      | Vertical Retrace Start (242)                |
| 0x11  | 0x03→0x80 | Vertical Retrace End (unlock→lock CRTC 0-7) |
| 0x12  | 0xEF      | Vertical Display End (239 = 240 lines)      |
| 0x13  | 0x14      | Offset (20 × 8 = 160 words = 320 bytes/row) |
| 0x15  | 0xEF      | Start Vertical Blanking                     |
| 0x16  | 0xF3      | End Vertical Blanking                       |
| 0x17  | 0xE3      | Mode Control                                |
| 0x18  | 0xFF      | Line Compare                                |
| 0x19  | 0x00      | MN89304 extension (meaning unknown)         |
| 0x1A  | 0x10      | MN89304 extension (meaning unknown)         |

**Graphics Controller (via ports 0x3CE/0x3CF):**

| Index | Value | Description |
|-------|-------|-------------|
| 0x01 | 0x00 | Enable Set/Reset |
| 0x03 | 0x00 | Data Rotate |
| 0x04 | 0x00 | Read Map Select |
| 0x05 | 0x00 | Graphics Mode |
| 0x06 | 0x01 | Miscellaneous (chain odd/even) |
| 0x08 | 0xFF | Bit Mask |

**Misc Output:** 0xE3 (clock select 0, which is 25.175 MHz on a PC VGA card; the KN5000's dot clock and refresh rate have not been measured, and MAME assumes that clock divided by 3; bits 6-7 select negative H/V sync)

**Boot DAC Palette (9 basic colors):**

| Index | R | G | B | Color |
|-------|---|---|---|-------|
| 0 | 0 | 0 | 0 | Black |
| 1 | F | F | F | White |
| 2 | F | 0 | 0 | Red |
| 3 | 0 | F | 0 | Green |
| 4 | 0 | 0 | F | Blue |
| 5 | 0 | F | F | Cyan |
| 6 | F | F | 0 | Yellow |
| 7 | F | 0 | F | Magenta |
| 8 | 0 | 0 | 4 | Dark Blue |

### MN89304 Extended Registers

Everything beyond the standard VGA set is written only while sequencer register 0x06 holds 0x01 (an unlock);
the routines write 0x00 there when they finish. No datasheet exists for the MN89304, so the values are listed,
not explained. Three routines program the controller: `VGA_Setup` (0xEF55A7, boot) with `VGA_Extended_Init`
(0xEF5163), and at run time `VGA_Initialize` (0xFB2B06, entry 0 of `VGA_InitFuncTable`, the display subsystem's
init phase 0) with `VGA_ConfigExtSequencer` (0xFB36A9). All register access goes through `_Write_VGA_Register`
(WA = port offset, C = value; it busy-waits 128 loops, then writes byte 0x170000 + WA) and `_Read_VGA_Register`
(no delay). Source: `notes/open4-kn5000-b/display/probes/vga_register_writes.py` in the disassembly repository,
which lists every write of each routine in order.

| Register   | Boot (`VGA_Setup`) | Run time (`VGA_Initialize`)                                                              |
|------------|--------------------|------------------------------------------------------------------------------------------|
| seq 0x07   | 0x20               | 0x20                                                                                     |
| seq 0x08   | 0x01               | 0x01                                                                                     |
| seq 0x0D   | 0x03               | 0x03                                                                                     |
| seq 0x0F   | 0x00               | 0x44; 0x00 when the region code (`Get_Region_Code`) is 4                                 |
| seq 0x13   | not written        | 0x01                                                                                     |
| CRTC 0x19  | 0x00               | 0x00                                                                                     |
| CRTC 0x1A  | 0x10               | 0x10                                                                                     |
| port 0x3C3 | 0x01               | 0x01 (the factory test `Test_LCD_Controller_IC206` writes 0 / 1 / 0 and reads each back) |

**Indexed table.** Sequencer 0x09 is an index and 0x0A / 0x0B / 0x0C are three data registers: the firmware
writes 0x09 = N, then one byte to each of 0x0A-0x0C. Even indices 0x00-0x10 take all three; odd indices
0x01-0x11 take only 0x0C (0x0D, 0x0F and 0x11 also take 0x0A). [INFERENCE] A register file of LCD timing or
panel-drive parameters (18 entries); there is no datasheet to confirm it. `VGA_Extended_Init` (boot) and
`VGA_ConfigExtSequencer` (run time) load the same 18 entries:

| 0x09 | 0x0A | 0x0B | 0x0C |
|------|------|------|------|
| 0x00 | 0x1C | 0x11 | 0x03 |
| 0x01 | -    | -    | 0x74 |
| 0x02 | 0x05 | 0x11 | 0x03 |
| 0x03 | -    | -    | 0x09 |
| 0x04 | 0x10 | 0x13 | 0x05 |
| 0x05 | -    | -    | 0x2B |
| 0x06 | 0x15 | 0x64 | 0x07 |
| 0x07 | -    | -    | 0x68 |
| 0x08 | 0x92 | 0x13 | 0x08 |
| 0x09 | -    | -    | 0x05 |
| 0x0A | 0x01 | 0x14 | 0x06 |
| 0x0B | -    | -    | 0x01 |
| 0x0C | 0x00 | 0x72 | 0x09 |
| 0x0D | 0x01 | -    | 0x0C |
| 0x0E | 0x00 | 0x13 | 0x08 |
| 0x0F | 0x11 | -    | 0x3A |
| 0x10 | 0xFE | 0x73 | 0x0F |
| 0x11 | 0xFF | -    | 0x0D |

Two more versions of this table sit in the main-CPU ROM with no caller, `VGA_ConfigExtSequencer_AltA`
(0xFB3264, 19 values differ) and `VGA_ConfigExtSequencer_AltB` (0xFB3AED, 18 differ). [INFERENCE] Most probably
settings for another LCD panel or an earlier panel revision, left in the image; nothing selects them. Just before
AltA, `VGA_WritePalette256_Unterminated` (formerly VGA_CRTCTiming_ByteData) is a palette loader whose closing
`jr` never exits its loop; nothing calls it.

**Run time differs from boot.** `VGA_Initialize` runs after `VGA_Setup`, so its values are the ones in force. It
leaves the horizontal total (CRTC 0x00) at **0x50**, not 0x65, and loads all 256 palette entries from the
work-RAM table at 0x00E3E8 (4 bytes per entry), rounding each 8-bit component to the 4-bit DAC (`v >> 4`, plus one
when bit 3 is set and the value is below 0xF0), where the boot code loads the 9 fixed colours below.

MAME's MN89304 VGA device ignores all of these registers; the image is correct without them.

### Palette Programming

The MN89304 uses a **4-bit RAMDAC** (implemented as `pal4bit()` in MAME). Only the lower 4 bits of each color component value are significant:

```c
// Writing a 256-color palette
for (int i = 0; i < 256; i++) {
    *(volatile uint8_t*)0x1703C8 = i;            // Select entry
    *(volatile uint8_t*)0x1703C9 = red[i] >> 4;  // 4-bit R (from 8-bit)
    *(volatile uint8_t*)0x1703C9 = green[i] >> 4; // 4-bit G
    *(volatile uint8_t*)0x1703C9 = blue[i] >> 4;  // 4-bit B
}
```

**Palette data format notes:**
- The HDAE5000 firmware stores palette data as 8-bit RGB and shifts right by 4 during loading
- If palette data is stored in 6-bit VGA format (0-63), shift right by 2 instead
- Effective color resolution: 4096 colors (16 levels per channel)

### CRTC Start Address

The CRTC start address determines which VRAM byte appears at the top-left pixel:

| CRTC Register | Index | Description |
|---------------|-------|-------------|
| Start Address High | 0x0C | High byte of VRAM start offset |
| Start Address Low | 0x0D | Low byte of VRAM start offset |

The firmware initializes the CRTC start address to `0x0000`, meaning VRAM address `0x1A0000` corresponds to screen pixel (0,0).

```c
// Reading current CRTC start address
*(volatile uint8_t*)0x1703D4 = 0x0C;
uint8_t start_high = *(volatile uint8_t*)0x1703D5;
*(volatile uint8_t*)0x1703D4 = 0x0D;
uint8_t start_low = *(volatile uint8_t*)0x1703D5;
uint16_t crtc_start = (start_high << 8) | start_low;
```

### Row Offset Override

The MN89304 overrides the standard VGA row offset calculation with an 8x multiplier:

```cpp
// In MAME: mn89304::offset()
uint32_t mn89304::offset() {
    return svga_device::offset() << 3;
}
```

This means the CRTC offset register value is multiplied by 8 to get the actual byte offset per row. The default configuration results in a 320-byte row stride (matching the 320-pixel width).

## Video RAM

| Property | Value |
|----------|-------|
| Base address | 0x1A0000 |
| Size | 256KB (0x1A0000-0x1DFFFF) |
| Active display area | 76,800 bytes (320 x 240) |
| Pixel format | 8-bit indexed color (1 byte per pixel) |
| Row stride | 320 bytes |
| Pixel addressing | `VRAM_BASE + y * 320 + x` |

The framebuffer is linear and row-major, and the active display occupies the first 76,800 bytes. The rest of the window is not idle. `Vga_SetupMultiPlaneDisplay` (0xEF09EA) copies work-DRAM blocks (from `0xF180` and `SEQ_SONG_SLOTS`) to `0x1B4000`-`0x1BFFFF`. It then selects write planes 1-3 with `Vga_SelectWritePlane` (0xEF09A8), which writes `(plane << 4) | 1` to MN89304 sequencer index 8 between writes of 1 and 0 to index 6, and copies further blocks into each plane at `0x1A0000`. `Vga_RestoreMultiPlaneDisplay` (0xEF0A73) copies them all back.

## Display Update Mechanism

### Draw Task, Not VBI

The firmware's display updates are **not driven by a vertical blank interrupt**. UI code draws into `OFFSCREEN_BUFFER_1`, and `UpdateScreen` (0xFAA61D) copies the changed rectangle to VRAM. The copy runs in the draw task: called from any other task, `UpdateScreen` posts it to the draw ring (see [Rendering Pipeline](#rendering-pipeline)). Its callers include the UI task's loop `MainTitle_EventLoop`. `MainLoop` does not call it directly, so `MainLoop`'s order does not decide when VRAM is written. `MainLoop` runs, in order:

```
Main Event Loop (MainLoop)
    |
    +-- MIDI output; timer-gated: CPanel_RX_ProcessOrInit (panel packets -> button arrays)
    +-- Sequencer and MIDI ticks (several, some timer-gated)
    +-- PanelButton_ProcessChanges
    +-- MainTitle_PrepareAndDispatch  (MainDispatchEvent, then MainTitleControl with EVT_MAIN_LOOP_COUNT)
    +-- timer-gated: MIDI, CPanel_Poll, effect and demo timers
    +-- Sequencer ticks, SeqStep_MainTimerTick
    +-- Display_DirtyRegionDispatch   (step-record screen only, while 0x0D53 bit 3 is set)
    +-- AccompSeq_PeriodicEntry
    +-- Xapr_CallFrameHandler         <-- extension ROM's Frame_Handler (0x280010), last
    |
    (loop)
```

This means:
- The firmware does not repaint on a fixed refresh: `UpdateScreen` copies a changed rectangle when UI code asks for one
- The HDAE5000 Frame_Handler is the last call of each `MainLoop` pass
- The UI reaches VRAM through `UpdateScreen`, which copies only the dirty area of `OFFSCREEN_BUFFER_1` (see [Rendering Pipeline](#rendering-pipeline-1)), so a pixel an extension ROM writes straight to VRAM survives until the firmware next redraws that area. No flag that stops the firmware's drawing has been identified (`0x0D53` bit 3, below, is not one)

### Step-record display flag (`0x0D53` bit 3)

`0x0D53` is a work-DRAM flag byte of the sequencer's step-record screen (TT_SQSTEP). Bit 3 is 0 at power-on (the byte lies in the block `Boot_InitWorkRAM` zero-fills). `SqStep_InitOnEnter` (0xEFA133) sets it when that screen is entered, and `SqStep_RestoreOnLeave` (0xEFA8CE) clears it when the screen is left. The main loop's `Display_DirtyRegionDispatch` (0xEF77DF) runs the step-record screen's dirty-region update only while the bit is set:

```asm
; At 0xEF77DF (Display_DirtyRegionDispatch):
BIT 3, (0D53h)           ; Step-record screen active?
JRL Z, skip              ; If bit 3 CLEAR, skip the step-record update
CALL Display_ResetDirtyFlags
; ... dispatches via state byte (0D65h) ...
CALL Display_UpdateDirtyRegions
```

v10 tests this bit at eight places: five in `display/scoop_display.s` (among them `Display_DirtyRegionDispatch`) and three in `sequencer/accompaniment_engine.s`. It is **not** a display-disable flag. It is clear in normal operation and the firmware's UI draws regardless, so neither setting nor clearing it hands the framebuffer to an extension ROM.

### Workspace function-table entries

An extension ROM reaches main-CPU routines through function table 0x100 at `workspace + 0x0E0A`; see [HDAE5000 Homebrew — Workspace Pointer]({{ site.baseurl }}/hdae5000-homebrew/#workspace-pointer). Earlier versions of this page listed three of its offsets as display callbacks. The firmware's own name table says they are not:

| Offset    | Function      | v10 address | What it does                                         |
|-----------|---------------|-------------|------------------------------------------------------|
| `+0x0124` | `ApPostEvent` | `0xFA9D58`  | queue an event; yields while the queue is full       |
| `+0x0278` | `GetTitleNow` | `0xFA5867`  | return the current title id (`TITLE_NOW`)            |
| `+0x0534` | `DeleteEvent` | `0xFA9868`  | remove queued events matching an object and an event |

The entries that really are drawing routines are `+0x0084` `UpdateScreen`, `+0x009C` `DrawLine`, `+0x00A4` `DrawBox`, `+0x00A8` `DrawFrame`, `+0x00B0` `MovePixels`, `+0x00C4` `DrawString` and `+0x02DC` `DrawDesignBox` (see [Drawing Primitives](#drawing-primitives)).

## Drawing Primitives

The firmware implements a complete graphics library for rendering to offscreen buffers. All drawing targets `OFFSCREEN_BUFFER_1` (0x43C00) by default, which is then blitted to VRAM (0x1A0000) during the display update cycle.

### Rendering Pipeline

All drawing functions follow a **deferred command queue** pattern:

```
Caller invokes DrawLine/DrawBox/DrawString/etc.
     │
     ├── IS_XSP_INSIDE_4K_REGION_AT_1C032 (0xFAA532)
     │   checks if caller is running in the draw task context
     │   (stack pointer in range 0x1C032 - 0x1D032)
     │
     ├── YES (draw task context):
     │   Execute DrawXxx_Impl directly
     │   Write pixels to OFFSCREEN_BUFFER_1 (0x43C00)
     │   Call SetChangeRect() to expand dirty bounding box
     │
     └── NO (other task context):
         Serialize parameters into DrawQueue (circular buffer)
         Call DrawRing_Post: post the record to the draw ring at 0x03247C
         (event 3 guards the ring), retrying while the ring is full
         → the draw task later takes it (DrawRing_TryTake) and runs it
```

This ensures all VRAM/buffer writes happen in a single task context, avoiding concurrency issues.

### Draw Command Queue

The draw queue is a **circular buffer** managed by `DrawQueue_Alloc` (0xFAA444):

| Property        | Value                                                                                                                                                                                      |
|-----------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Base address    | 0x030466                                                                                                                                                                                   |
| Size            | 8KB (0x2000 bytes)                                                                                                                                                                         |
| Write pointer   | 0x03246A                                                                                                                                                                                   |
| Read pointer    | 0x032474                                                                                                                                                                                   |
| Entry count     | 0x03247A (modular counter, wraps at 0x7C entries)                                                                                                                                          |
| Synchronization | Event 3 (wait/signal) + semaphore 4 (taken with the kernel's generic `Kernel_SemaWait`/`Kernel_SemaSignal`, `Audio_Lock_Acquire`/`Audio_Lock_Release` until 2026-11-06; not an audio lock) |

Each queued command starts with a 4-byte function pointer (the `DrawXxx_Impl` address), followed by serialized parameters (8-28 bytes depending on the primitive). When the draw task processes a command, it calls the function pointer with the parameter block.

### Graphics Initialization

`InitializeGraphics` (0xFAA547) performs the following at boot:

1. Initialize draw task (`InitDrawTask`)
2. Show screen group 5 and enable palette
3. Initialize palette RGB tables (`InitPaletteRGB`)
4. Set wallpaper (index 0) and palette (index 2)
5. Clear `OFFSCREEN_BUFFER_1` (76,800 bytes at 0x43C00) with two `Memset(0)` calls of 0x9600 bytes each (the count is a 16-bit word)

### Address Calculation

All drawing functions convert (x, y) pixel coordinates to buffer offsets using:

```
offset = y * 320 + x
```

The multiplication `y * 320` is computed via shifts: `(y << 2 + y) << 6 = y * 5 * 64`. This is implemented in the shared helper `Set_XWA_to_320_times_XDE` at `0xEF5088`.

### Drawing Modes

Several primitives support multiple drawing modes specified by a mode code:

| Mode | Code | Operation | Description |
|------|------|-----------|-------------|
| Write | 0x201 | `pixel = color` | Direct pixel write |
| Clear | 0x202 | `pixel = 0x00` | Clear pixel to zero |
| OR | 0x203 | `pixel |= color` | Bitwise OR with color |
| AND | 0x204 | `pixel &= color` | Bitwise AND with mask |
| XOR | 0x205 | `pixel ^= color` | Bitwise XOR (used for cursors, selection) |

### Special Colors

| Color | Meaning |
|-------|---------|
| 0xF7 | Transparent (pixel skipped, no write) |
| 0xF5 | Read-back: reads pixel from secondary buffer (pattern fill) |

### Memory Operations

| Function | Address | Description |
|----------|---------|-------------|
| `Copy_DE_words_from_XBC_to_XWA` | 0xEF18D7 | Block copy using LDIRW. Blits offscreen → VRAM |
| `Fill_memory_at_XWA_with_DE_words_of_BC_value` | 0xEF18E0 | Fill memory with 16-bit pattern (buffer clear) |

### Pixel Operations

| Function        | Address  | Description                                      |
|-----------------|----------|--------------------------------------------------|
| `ReadPixel`     | 0xFAA7B2 | Read 8-bit color from offscreen buffer at (x, y) |
| `ModifyPixel`   | 0xFAA7E4 | Write single pixel to offscreen buffer           |
| `ModifyPixelEx` | 0xFAA844 | Extended pixel op: write/clear/OR/AND/XOR modes  |

### Rectangle Operations

| Function        | Address  | Description                                                                                                                                                                                                                    |
|-----------------|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `VRAM_FillRect` | 0xEF50DF | Fill 6×12 pixel rect directly in VRAM with solid color                                                                                                                                                                         |
| `DrawWall`      | 0xFABB73 | Fill entire screen from source buffer (wallpaper/splash)                                                                                                                                                                       |
| `DrawRect`      | 0xFB0D14 | Rectangle outline: drawn at once when XSP is inside 0x1C032-0x1D032 (`IS_XSP_INSIDE_4K_REGION_AT_1C032`), otherwise queued as a `DrawRect_CallbackBlock` record (the same pattern as `ColorBlit` and `DrawText_QueueOrDirect`) |
| `DrawRect_Impl` | 0xFB0D8C | The outline itself: clips the box to (0,0)-(319,239), then four `DrawLineWithMode_Impl` sides (one line when y0 = y1) and `SetChangeRect`                                                                                      |

### Line Drawing

| Function     | Address  | Description                                      |
|--------------|----------|--------------------------------------------------|
| `DrawLine`   | 0xFAA98A | Bresenham line from point A to point B           |
| `DrawLineEx` | 0xFAAF12 | Extended line with drawing mode (write/XOR/etc.) |

Both use Bresenham's algorithm with optimized fast paths for horizontal lines (`dy = 0`), vertical lines (`dx = 0`), and general diagonal lines. The color 0xF5 triggers pattern-fill mode where each pixel's color is read from a secondary buffer instead of using a fixed color.

### Bitmap/Sprite Drawing

The firmware uses a **bitmap descriptor table** in ROM at `0x913000`. Each entry is 8 bytes:

```
+0x00: word  width (pixels)
+0x02: word  height (rows)
+0x04: long  pixel_data_ptr (24-bit address of pixel data in ROM)
```

Bitmap pixel data is stored as packed 16-bit words (2 pixels per word). Color `0xF7` in bitmap data is treated as transparent (pixel skipped).

| Function                             | Address  | Description                                                 |
|--------------------------------------|----------|-------------------------------------------------------------|
| `DrawBitmap`                         | 0xFABC3C | Draw bitmap with transparency (0xF7 = transparent)          |
| `DrawBitmapFast`                     | 0xFABE13 | Draw bitmap without transparency check (opaque only)        |
| `MovePixels`                         | 0xFABA53 | Copy rectangular pixel block within offscreen buffer        |
| `Draw_FlashMemUpdate_message_bitmap` | 0xEF5040 | Draw 224×22 monochrome (1bpp) bitmap for firmware update UI |

### Text Rendering

Text is rendered using a **font glyph table** in ROM at `0x945C00`. Each font entry is 16 bytes:

```
+0x00: word  char_width (pixels per character)
+0x02: word  char_height (pixels)
+0x04: word  descent (below baseline)
+0x06: word  ascent (above baseline)
+0x08: long  glyph_bitmap_ptr (1bpp bitmap data, 8 pixels per byte, MSB first)
+0x0C: long  kerning_table_ptr (0 = fixed-width font; see below)
```

For **variable-width fonts** (kerning_table_ptr ≠ 0), the kerning table has 4-byte entries per character: `{word char_width, word glyph_data_offset}`. Each glyph uses `ceil(char_width/8) × height` bytes at `glyph_bitmap_ptr + glyph_data_offset`.

Character codes are offset by 0x20 (space) before table lookup. Glyphs are rendered as 1bpp bitmaps decomposed into 8-pixel-wide vertical strips, drawn left-to-right, top-to-bottom. All text rendering clips against a specified rectangle.

| Function                 | Address  | Description                                            |
|--------------------------|----------|--------------------------------------------------------|
| `DrawString`             | 0xFACACA | Core text renderer: draws null-terminated string       |
| `DrawStringCentered`     | 0xFACEAC | Center text horizontally and vertically in rect        |
| `DrawStringLeftJustify`  | 0xFACF4A | Left-align text (x = rect.left + 4), center vertically |
| `DrawStringRightJustify` | 0xFACFB1 | Right-align text (x = rect.right - 4 - width)          |
| `DrawStringAlignment`    | 0xFAD049 | Dispatch by mode: 0=center, 1=left, 2=right            |
| `DrawStringReverse`      | 0xFAD084 | Draw with swapped fg/bg colors (selection highlight)   |

### Font Helper Functions

| Function          | Address  | Description                                                        |
|-------------------|----------|--------------------------------------------------------------------|
| `GetCharHeight`   | 0xFB260A | Return character height from font table (+0x02)                    |
| `GetCharDescent`  | 0xFB2617 | Return character descent from font table (+0x04)                   |
| `CalcTotalWidth`  | 0xFB26D1 | Calculate total pixel width of rendered string                     |
| `ConvertStrings`  | 0xFB2640 | Convert control codes to displayable format (0x7E prefix = escape) |
| `WordwrapStrings` | 0xFB275A | Word-wrap text for multi-line layout                               |

### Character Encoding

Characters use ASCII encoding with an offset of `0x20` (space). Before lookup in the font or kerning table, each character code has `0x20` subtracted. Control characters below `0x20` are mapped to space.

**Escape sequences:** The `0x7E` prefix byte introduces a two-digit hex-encoded character code:
```
0x7E 0x33 0x41  →  character 0x3A (colon)
0x7E 0x46 0x37  →  character 0xF7 (special symbol)
```

Hex digits support `0-9`, `a-f`, and `A-F`.

**Character → glyph map:** text that goes through `FontGlyph_ByteData` is first translated by
`Text_CharGlyphMap` (256 bytes in the program ROM, 0xEAB1B4 in v10). Printable ASCII maps to itself except `\`,
which becomes 0xA5 (¥). Codes 0x10-0x1F map to UI-symbol glyphs, and 0x80-0xAB to the Latin-1 letters of the
fonts' accent page (Ä Ö Ü ä ö ü ß ...). The routine after it searches the same table to convert a glyph back.

Codes 0x01-0x0F map to 0x20, so every control character draws as a blank cell, and 0x00 stays 0 and ends
the string. The step-record screen's own copy of the map (`Scoop_CharGlyphMap`, 0xE0CB1A in v10,
byte-identical) is applied by `Scoop_CurveUpdate_SegmentEnd` to its pop-up line (RAM 0x0ECA, 30 characters,
style 6 = font 0, at x 8, y 180). That is why the two pairs of TAB bytes (0x09) in `Tbl_AccompPartNames`
draw as spaces.

**A firmware bug in the ACCOMP PART pop-up.** `ParamPopup_AccompPart` copies 16 bytes from
`Tbl_AccompPartNames + 16 × (flags >> 5)` and overwrites "ON " at +13 with "OFF", but the table's three
strings start at offsets 2, 18 and 36 (0x09 0x09 "ACCOMP PART1 ON ACCOMP PART2 ON " 0x09 0x09 "ACCOMP PART3 ON ").
No flag value the caller allows (1-7) lands on a string: the line reads `N ACCOMP PART2 O`,
`N ACCOMP PARTOFF`, `N   ACCOMP PART3` and so on, or bytes of program code past the table. The same in
v5-v10. *[INFERENCE]* from the code and the ROM bytes (probe `notes/open6-kn5000-d/misc/probes/accomp_part_popup_glyph.py`
in technics-roms-disasm); not yet seen on an instrument.

**Text style → font:** display records and widgets carry a *style* byte rather than a font number.
`TextStyle_FontTable` (64 × u32, 0xEAB004 in v10) maps `style & 0x3F` to the font passed to
`DrawText_QueueOrDirect`: style 7 → font 1, style 8 → font 2, style 32 → font 6, every other style → font 0.
Source: `scripts/converters/text_tables_retype.py` in the disassembly repository.

### Font Catalog

The firmware contains **10 fonts** (IDs 0-9) in the Table Data ROM. Each font has 224 characters (ASCII 0x20-0xFF). All font data resides at `0x945C00`-`0x950A5F` (descriptors to `0x945CAF`, glyphs from `0x945CB0`).

| ID | Size   | Type     | Kerning | Description                                             |
|----|--------|----------|---------|---------------------------------------------------------|
| 0  | 8×16   | Fixed    | No      | UI font, UI-symbol upper page                           |
| 1  | 8×16   | Fixed    | No      | Font 0 with glyphs 2 px higher in the cell              |
| 2  | 16×16  | Fixed    | No      | Double-width headline font                              |
| 3  | 6×8    | Fixed    | No      | Small font                                              |
| 4  | 11×16  | Fixed    | No      | Large font                                              |
| 5  | var×16 | Variable | Yes     | Proportional font (widths 3-10 px), Latin-1 accent page |
| 6  | 8×10   | Fixed    | No      | Compact font                                            |
| 7  | 8×16   | Fixed    | No      | Font 0 letterforms, Latin-1 accent page                 |
| 8  | 8×16   | Fixed    | No      | Font 1 letterforms, Latin-1 accent page                 |
| 9  | 11×16  | Fixed    | No      | Font 4 letterforms, Latin-1 accent page                 |

**Variable-width font (ID 5):** Uses a kerning table at `0x94C620` with 4-byte entries per character: `{word char_width, word glyph_offset}`. Each glyph uses `ceil(width/8) × height` bytes. Character widths range from 3 to 10 pixels.

**Font samples** (extracted from ROM):

{% for i in (0..9) %}
**Font {{ i }}:**
![Font {{ i }}]({{ site.baseurl }}/assets/images/gallery/font_0{{ i }}.png)
{% endfor %}

BDF (Bitmap Distribution Format) exports are available in the [roms-disasm repository](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/extracted_fonts) for use in emulators and tools.

## Screen Layout and Regions

### Common title layout

Every title is a full-screen `TtlScreen` view (0, 0, 320 x 240): all 195 `TtlScreen` records in the v10 C sources
have that rectangle. They are laid out on one grid, which the widget records themselves show: each record carries
the panel switch that operates it (`editsw`: `ES_Left1..5` = 0x88-0x8C, `ES_Right1..5` = 0x08-0x0C,
`ES_Bottom1..8` = 0x00-0x07, `ES_Exit` = 0x0F) and its rectangle. Counted over the 916 v10 records that name a
switch (973 have the field, 57 say `ES_None`; `notes/open4-kn5000-b/display/probes/screen_layout.py` in the
disassembly repository):

| Zone             | Rectangle (x, y, w, h)                                                  | Switches                              |
|------------------|-------------------------------------------------------------------------|---------------------------------------|
| Title strip      | 4, 0, 312, 28 (drawn by `DrawTitleBar`, not a record)                   | -                                     |
| Left rows 1-5    | 8, 30 + 42 (n - 1), 149, 26                                             | LEFT 1-5 (0x88-0x8C)                  |
| Right rows 1-5   | 163, 30 + 42 (n - 1), 149, 26; value boxes 281, 34 + 42 (n - 1), 31, 18 | RIGHT 1-5 (0x08-0x0C)                 |
| Bottom slots 1-8 | 4 + 40 (k - 1), 216, 32, 23; a 72-wide box spans two slots              | buttons 1-8 below the LCD (0x00-0x07) |
| EXIT             | the eighth bottom slot (284, 216)                                       | EXIT (0x0F)                           |

These are the most common rectangles per switch, not the only ones: the share of the most common one ranges from
21% (RIGHT 1) to 72% (bottom 7). A wide parameter box in a side row is 165 px; a 112-px bottom box spans three
slots, still operated by the switch of the first. Records with no switch (`ES_None`) are free-placed, for example
list and edit boxes in the middle (44, 111, 233 x 72).

The title strip: `TtlScreenProc` (0xF9AA6D) answers `EVT_DRAW` with `ScreenProc` (wallpaper and children) and
then `DrawTitleBar`, which draws the title's icon at the left (the text box starts 24 px in when the title has an
icon) and its string centred (left or right alignment by a parameter) in font 4, re-measured in font 1 if it does
not fit, inside x 4-315, y 0-27. When the screen has a page box (`PsPageBox`, found with `EVT_SEARCH_CLASS`), the
right 64 px are left to it: the `AcWindowPage` page indicator at (245, 6) or, on the performance screens, the
`AcTempoBox` at (248, 4). There is no fixed status bar. The fifth side row (y 198-223) and the bottom row
(y 216-238) overlap, so a screen uses one or the other there. The 11 regions below belong to the sequencer's
step-record screen only.

### Step-record screen regions

The sequencer's step-record screen (title id 0x8A, `TITLE_SQSTEP`) is divided into 11 independently-tracked dirty regions. This is that screen's layout, not the whole UI's. `Display_UpdateDirtyRegions` is called from two of that screen's title methods (`Display_InitScreenLayout`, run from its draw method, and `Display_PollAudioAndUpdate`). It is also called from `Display_DirtyRegionDispatch` and one SWBT listener, both of which run it only while `0x0D53` bit 3 is set, and from a second SWBT listener that marks regions dirty only when `ACTIVE_TITLE` is 0x8A. Seven of the eleven redraw routines also return at once unless `ACTIVE_TITLE` is 0x8A. The region names below come from the routine labels. Each region has its own redraw function and dirty bit. The regions are not defined by hardcoded pixel coordinates — instead, each redraw function loads **ROM descriptor tables** that define the region geometry, content, and rendering parameters. These descriptors are passed to UI rendering helper functions.

### Region Update Order

`Display_UpdateDirtyRegions` (0xEF5B36) updates regions in a specific order optimized for visual priority:

```
1. Region 0  - Status Bar         (mode indicators, tempo)
2. Region 5  - Menu Area          (menu/list content)
3. Region 7  - Parameter Display  (parameter names)
4. Region 8  - Value Display      (parameter values)
5. Region 9  - Indicator Area     (status indicators)
6. Region 1  - Title Bar          (song/patch name, up to 3 title fields)
7. Region 10 - Footer Area        (status/help text)
8. Region 6  - Button Labels      (soft button labels, 3 rows of 8)
9. Region 3  - Main Content       (primary display area)
10. Region 4 - Side Panel         (side parameters)
11. Region 2 - Selection          (highlight/cursor, drawn last for overlay)
```

### Redraw Functions

Each region has a dedicated redraw function that references ROM descriptor tables:

| Region | Redraw Function | Address | ROM Descriptors (examples) |
|--------|-----------------|---------|---------------------------|
| 0 | `Display_RedrawStatusBar` | 0xF00999 | 0xE0B905, 0xE0B92E, 0xE0B99D |
| 1 | `Display_RedrawTitleBar` | 0xF00C89 | 0xE0BD52-0xE0BD7A (3 title fields) |
| 2 | `Display_RedrawSelection` | 0xF00DA5 | Variable (cursor overlay) |
| 3 | `Display_RedrawMainContent` | 0xF00C33 | 0xE0BD89 |
| 4 | `Display_RedrawSidePanel` | 0xF00E35 | Multiple descriptor sets |
| 5 | `Display_RedrawMenu` | 0xEFF110 | Complex menu rendering |
| 6 | `Display_RedrawButtonLabels` | 0xF00FDC | 0xE0C764, 0xE0C8CC, 0xE0BF6E |
| 7 | `Display_RedrawParameters` | 0xEF6F1A | State-dependent |
| 8 | `Display_RedrawValues` | 0xEF6FA3 | State-dependent |
| 9 | `Display_RedrawIndicators` | 0xEF704B | State-dependent |
| 10 | `Display_RedrawFooter` | 0xF00C4A | 0xE0BDAC, 0xE0BDE8, 0xE0BE06 |

### Display State

The byte at address `0x0D65` (decimal 3429 in the disassembly; a work-DRAM byte, not an SFR) is the step-record screen's display mode, 0-3. `SqStep_SetDisplayModeFromTrack` sets it from the cursor track's TRACK ASSIGN entry, and `Timer_ModeDispatch` uses its low two bits to index a 4-entry table:

| Value | Mode              |
|-------|-------------------|
| 0     | chord / APC track |
| 1     | note track        |
| 2     | CONTROL track     |
| 3     | RHYTHM track      |

On the step-record screen the redraw routines read this byte to choose their descriptor tables (`Display_RedrawStatusBar` and `Display_RedrawSelection` branch on it), so the same regions show different content for each track type.

### UI Rendering Helpers

The redraw functions delegate to specialized rendering helpers:

| Helper | Address | Purpose |
|--------|---------|---------|
| `Scoop_EventLoop_12Entry` | 0xF0212C | General UI element renderer |
| `GraphicsRender_Start` | 0xFB15F6 | Two-descriptor pair renderer |
| `GraphicsRender_ProcessEntries` | 0xFB1594 | Simple descriptor renderer |
| `Scoop_CurveUpdate_SegmentEnd` | 0xF01930 | Content area renderer |
| `Scoop_GlideParam_Setup` | 0xF01DAB | Number/value display renderer |
| `Scoop_EventLoop_36Entry` | 0xF023CF | Dynamic value renderer |
| `DrawFunc_Init` | 0xFB2044 | Parameter display renderer |
| `ColorBlit_WithPaletteSave` | 0xFB24CB | Status indicator renderer |

### Display-List Records (ScreenData)

The sound editor and other screens draw from display lists in ROM: runs of records `{u8 op, u8 len, payload}`,
where `len` is the whole record's size. `GraphicsRender_ProcessEntries` walks a list of **static** records and
calls `GraphicsRender_ProcessEntries_PtrTable[op]` with each one. In the disassembly the records are written
with the `sd_*` macros of `audio/sound_editor_ui.s`. Points are u16 pixel pairs at record +2/+4 (x0, y0) and
+6/+8 (x1, y1). A cell is u16 `y*40 + x/8`.

| Op | Handler | Draws |
|----|---------|-------|
| 00, 01, 02 | `SeGfx_StaticOp00_Line` ... | `DrawLineWithMode` from (x0,y0) to (x1,y1) (three identical compiled bodies) |
| 11, 12, 15 | `SeGfx_StaticOp11_DottedLine` ... | the same with `DrawDottedLineWithMode` |
| 13 | `SeGfx_StaticOp13_DottedBox` | the dotted outline of the box (four dotted lines) |
| 09 | `SeGfx_StaticOp09_Box` | `DrawRect` of the box |
| 22 | `SeGfx_StaticOp22_ShadowBox1` | `DrawRect`, then lines offset +1 along the right and bottom sides (1-pixel drop shadow) |
| 0A | `SeGfx_StaticOp0A_ShadowBox2` | the same with lines at +1 and +2 (2-pixel drop shadow) |
| 05 | `SeGfx_StaticOp05_FillBoxMode1` | `ColorBlit` of the box with `COLORBLIT_MODE` forced to 1 (each pixel's bit 5 set or cleared by its bit 7: a highlight) |
| 03 | `SeGfx_StaticOp03_Bitmap` | 1-bpp bitmap (u32 +2) at a cell (u16 +6), bytes per row +8, rows +10 |
| 06, 07, 08, 20 | `SeGfx_StaticOp06_CellTextFont0` ... | text at the cell in u16 +2, in font 0, 1, 2, 6 |
| 17, 1C | `SeGfx_StaticOp17_PixelTextFont3`, `SeGfx_StaticOp1C_PixelTextFont4` | text at pixel x = u16 +2, y = u16 +4, in font 3, 4 |
| 23 | `SeGfx_StaticOp23_DesignBox` | `DrawDesignBox` + `DrawIcons` (u8 style +2, cell u16 +3) |
| 0E, 1B | `ColorBlit_ComputeRectAndBlit`, `ColorBlit_ByteData` | `ColorBlit2` blits |
| others | `GraphicsRender_RetStub` | nothing |

The text handlers are one compiled body each. They differ only in the font index they pass to
`DrawText_QueueOrDirect` (see [Font Catalog](#font-catalog)), and they clip to the full screen (0,0)-(319,239).

`GraphicsRender_Start` walks **bound** records through `GraphicsRender_Start_PtrTable` (12 ops). Most of them
first read `value = (RAM byte[u16 +2] & u8 +4) >> (u8 +5 & 15)` and then draw a number, a string from a table,
or a box from a table, chosen by that value (the `sdb_*` macros). Ops 06 and 0A instead print a 16-bit RAM word.
The record layouts of ops 08-0B are not derived yet.
Source: `scripts/tools/label_segfx_ops.py` (the handler-by-handler reading) and the `SeGfx_*` header in
`audio/sound_editor_ui.s`.

### Button Label Organization

Region 6 (button labels) manages three rows of 8 soft-button labels, organized at RAM addresses:
- Row 1: 0x0E55 (8 entries, 4 bytes apart)
- Row 2: 0x0E75 (8 entries, 4 bytes apart)
- Row 3: 0x0E95 (8 entries, 4 bytes apart)

### Dirty Region Tracking

The step-record screen's update system tracks 11 independent regions. Each region has a dirty bit in the bitmap at `DISPLAY_DIRTY_FLAGS` (0x205E4):

| Function | Address | Description |
|----------|---------|-------------|
| `Display_ResetDirtyFlags` | 0xEF5B27 | Clear all dirty flags and enable flag |
| `Display_UpdateDirtyRegions` | 0xEF5B36 | Check all 11 regions, call redraw for dirty ones |
| `Display_UpdateRegion0` | 0xEF5B8B | Status bar |
| `Display_UpdateRegion1` | 0xEF5BE9 | Title bar |
| `Display_UpdateRegion2` | 0xEF5C20 | Selection highlight |
| `Display_UpdateRegion3` | 0xEF5C07 | Main content area |
| `Display_UpdateRegion4` | 0xEF5C39 | Side panel |
| `Display_UpdateRegion5` | 0xEF5C52 | Menu area |
| `Display_UpdateRegion6` | 0xEF5C6B | Button labels |
| `Display_UpdateRegion7` | 0xEF5C84 | Parameter display |
| `Display_UpdateRegion8` | 0xEF5C9D | Value display |
| `Display_UpdateRegion9` | 0xEF5CB6 | Indicator area |
| `Display_UpdateRegion10` | 0xEF5CCF | Footer area |

### Change Tracking

| Function        | Address  | Description                                       |
|-----------------|----------|---------------------------------------------------|
| `SetChangeRect` | 0xFAA762 | Expand dirty bounding box to include drawn region |

The bounding box is maintained at:

| Address | Purpose |
|---------|---------|
| 0x030456 | Min X (left edge) |
| 0x030458 | Min Y (top edge) |
| 0x03045A | Max X (right edge) |
| 0x03045C | Max Y (bottom edge) |
| 0x03045E | Update flag (non-zero = needs refresh) |

In the source (each maincpu tree's `shared/ram_variables.s`): `DIRTY_BBOX` (0x030456, the four words) and
`DISPLAY_UPDATE_FLAG` (0x03045E).

### Offscreen Buffers

| Buffer             | Address  | Size                                     | Purpose                                       |
|--------------------|----------|------------------------------------------|-----------------------------------------------|
| OFFSCREEN_BUFFER_1 | 0x043C00 | 76,800 bytes                             | Primary render target (all drawing goes here) |
| OFFSCREEN_BUFFER_2 | 0x056800 | 38,400 bytes (0x9600 to the next buffer) | Secondary buffer (scrolling/animation)        |
| OFFSCREEN_BUFFER_3 | 0x05FE00 | 38,400 bytes (0x9600 to the next buffer) | Tertiary buffer (compositing)                 |
| OFFSCREEN_BUFFER_4 | 0x069400 | 76,800 bytes                             | Quaternary buffer (sprites/overlays)          |

## UI Widget Rendering

### Rectangle & Shape Primitives

In addition to the pixel-level drawing primitives, the firmware provides higher-level shape drawing functions:

| Function          | Address  | Description                                              |
|-------------------|----------|----------------------------------------------------------|
| `DrawBox`         | 0xFAB273 | Fill a rectangle with solid color (clip to 0-319, 0-239) |
| `DrawFrame`       | 0xFAB3DE | Draw rectangle outline (4 border lines, no fill)         |
| `DrawFrameEx`     | 0xFAB809 | Styled frame with XOR support and screen clipping        |
| `DrawDesignFrame` | 0xF9C86F | Decorative frame with special border patterns            |
| `DrawDesignBox`   | 0xFAD559 | Styled box with type-specific rendering                  |

### Icon Rendering

The firmware maintains a separate **icon descriptor table** at `0x938000` (in Table Data ROM), using the same 8-byte format as the bitmap table:

| Function           | Address  | Description                            |
|--------------------|----------|----------------------------------------|
| `DrawIcons`        | 0xFABF3F | Draw icon from table at 0x938000       |
| `DrawBitmapSP`     | 0xFAC1EC | Draw bitmap with special color mapping |
| `DrawBitmapSPFast` | 0xFAC3DB | Fast special bitmap rendering          |
| `DrawBitmapSP2`    | 0xFAC509 | Alternative special bitmap variant     |
| `DrawBitmapFile`   | 0xFAC697 | Draw bitmap from file/external data    |

### Arrow Widget

These two routines were once read as progress bars (DrawProgressRectH / V). Their only caller is `ArrowProc`'s
`EVT_PAINT` (0xF96569): they paint the arrow of an Arrow view into its client box, a head that is DE percent of
the box and is drawn as a fan of `DrawLineHelper` lines widening towards the base, and a shaft on the box's
centre line; a pushed word picks the pointing direction (1, 2, 3).

| Function               | Address  | Description                                    |
|------------------------|----------|------------------------------------------------|
| `Arrow_DrawHorizontal` | 0xF96180 | `ArrowProc`'s arrow, horizontal (view +24 = 0) |
| `Arrow_DrawVertical`   | 0xF9635E | `ArrowProc`'s arrow, vertical                  |

### Widget Event Handlers

The firmware implements widget-specific event handlers following a `*Proc` naming convention (`GroupBoxProc`,
`LabelProc`, `EditSwProc`, ...). `EditSwProc` is a Label that handles only `EVT_SW_IN` itself; it is not a toggle
control. How each class paints itself (the `EVT_PAINT` / `EVT_REPAINT` / `EVT_DRAW` protocol and the primitives
each class's `EVT_DRAW` calls) is on the UI Framework page, [How Widgets Paint
Themselves]({{ site.baseurl }}/ui-framework/#how-widgets-paint-themselves).

Many domain-specific widget types exist for the keyboard's various modes (arrangement, composition, bank selection, etc.).

### LCD Control

| Function            | Address  | Description                              |
|---------------------|----------|------------------------------------------|
| `LcdOn`             | 0xFAA5B6 | Enable LCD output (set flag at 0x030464) |
| `LcdOff`            | 0xFAA5DB | Disable LCD output                       |
| `ChangePalette`     | 0xFAF2C7 | Switch color palette                     |
| `ChangeWall`        | 0xFAF20B | Load background wallpaper                |
| `ChangeWallPalette` | 0xFAF25B | Change palette for wallpaper             |

## Embedded Images

Images extracted from firmware ROMs:

| Source       | Count | Description                                                                                                                                                                                                        |
|--------------|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Main CPU ROM | 61    | UI elements (split-point keys, drawbar sliders, sound-editor envelope curves and radio buttons, Fade In/Out labels), the Technics and KN5000 logos, the eight 1 bpp flash-update banners, MIDI connection diagrams |
| HDAE5000 ROM | 6     | Boot splash, product logo, drive mechanism, file panel, hard-disk icon, STORE button                                                                                                                               |

The counts are the committed PNGs in the disassembly, `v10/maincpu/images/*.png` and `hdae5000/images/*.png`
(2026-10-31, disassembly `130735749`; the build turns each into the ROM bytes).

See [Image Gallery]({{ site.baseurl }}/image-gallery/) for all extracted images.

## Display Modes

The KN5000 uses a single display mode:

| Property | Value |
|----------|-------|
| Width | 320 pixels |
| Height | 240 pixels |
| Color Depth | 8-bit (256 color palette) |
| RAMDAC | 4-bit per channel (12-bit effective RGB) |
| Refresh | Main-loop driven (not fixed rate) |

## Related Pages

- [HDAE5000 Homebrew Development]({{ site.baseurl }}/hdae5000-homebrew/) - Display ownership for custom ROMs
- [Image Gallery]({{ site.baseurl }}/image-gallery/) - Extracted firmware graphics
- [UI Framework]({{ site.baseurl }}/ui-framework/) - Menu and widget system
- [Hardware Architecture]({{ site.baseurl }}/hardware-architecture/) - Physical components
- [System Overview]({{ site.baseurl }}/system-overview/) - Overall architecture

## Animation and Transition Effects

The KN5000 implements several animation and fade mechanisms, all software-based (no hardware scroll registers are used). It does not animate a change of title (see [Title changes are immediate](#title-changes-are-immediate)).

### Rendering Pipeline

All drawing operations target `OFFSCREEN_BUFFER_1` (0x43C00), never VRAM directly. The `UpdateScreen` function (0xFAA61D) copies changed regions to VRAM:

```
Drawing Operation (DrawString, DrawBox, etc.)
        ↓
Write to OFFSCREEN_BUFFER_1 (0x43C00)
        ↓
Call SetChangeRect() → expand dirty bounding box at 0x030456
        ↓
UpdateScreen (0xFAA61D), called by UI code such as MainTitle_EventLoop
(not directly by MainLoop); the copy runs in the draw task
        ↓
Check dirty bounding box:
  Full screen? → full-screen blit (0xFB30A9)
  Partial?     → row-by-row blit (0xFB30D3)
        ↓
Copy from 0x43C00 → VRAM at 0x1A0000
        ↓
Reset dirty box and flags
```

During large updates, `VGA_ScreenBlank` (0xFB319A) blanks the display by setting VGA Sequencer register 01h bit 5, preventing visible tearing. `VGA_ScreenUnblank` (0xFB318A) re-enables display after the update.

### Palette-Based Fade Effects

The firmware implements fade effects through VGA DAC palette manipulation:

| Function            | Address  | Description                                                                                     |
|---------------------|----------|-------------------------------------------------------------------------------------------------|
| `ChangePalette`     | 0xFAF2C7 | Switch to a new 256-color palette from table at 0xEAAE66 (body: `ChangePalette_Impl`, 0xFAF2F3) |
| `PaletteBankRotate` | 0xFAF346 | Rotate pixel values through palette banks for fade effect                                       |

**Palette table** at `0xEAAE66`: entries are 10 bytes each, containing pointers to RGB palette data. The firmware supports 16 palette banks of 16 colors each (0x00-0x0F through 0xE0-0xEF).

**Palette bank rotation** (0xFAF346) creates fade effects by modifying pixel color indices:
- Pixels with value >= 0xE0: subtract 0x90 (wrap to lower bank)
- Pixels with value < 0xE0: add 0x10 (shift to next bank)

This rotates all pixels one palette bank forward. Combined with palettes arranged as intensity gradients, this produces smooth brightness fade transitions.

**Key palette state addresses:**

| Address | Purpose |
|---------|---------|
| 0x03EF94 | Current palette data pointer |
| 0x03EF9E | Current palette index |
| 0x03EFA0 | Previous palette index (for partial updates) |
| 0x030460 | Palette update pending flag |

In the source: `PALETTE_DATA_PTR_CACHED` (0x03EF94), `PALETTE_INDEX_CACHED` (0x03EF9E),
`PALETTE_INDEX_PREVIOUS` (0x03EFA0) and `PALETTE_UPDATE_FLAG` (0x030460).

### Fade-setting grid box

| Function             | Address  | Description                                                        |
|----------------------|----------|--------------------------------------------------------------------|
| AcFadeSetGridBoxProc | 0xF75229 | Grid-box widget procedure (cell redraw, header row/column strings) |
| FadeSetGridCheck     | 0xF754BE | Grid parameter validation and dispatch                             |
| TtFadeInOut          | 0xF751EB | Fade-in/out state machine (Entertainer mode)                       |

`AcFadeSetGridBoxProc` answers `EVT_REQUEST_GRID_DRAW` (redraw one cell), `EVT_GET_FIXED_ROW_STR` and `EVT_GET_FIXED_COL_STR` (header labels) and `EVT_SHOW` directly, and dispatches seven index-switch events (from `EVT_INDEXSW_UP`) through `AcFadeSetGridBoxProc_CaseTable` (0xE7F964). Nothing in it fades the screen.

### Fade In / Fade Out bitmaps

Four 8 bpp bitmaps, drawn by `VwUserBitmapProc` through `DrawBitmapSPFast`, label the Fade In / Fade Out controls:

| Label                 | Address  | Size | Purpose                                  |
|-----------------------|----------|------|------------------------------------------|
| Bitmap_FadeInPicture  | 0xEB8072 | 2800 | 112×25 crescendo wedge                   |
| Bitmap_FadeInText     | 0xEB8B62 | 1440 | 80×18 "FADE IN" lettering                |
| Bitmap_FadeOutPicture | 0xEB9102 | 2850 | 113×25 (row stride 114) diminuendo wedge |
| Bitmap_FadeOutText    | 0xEB9C24 | 2160 | 108×20 "FADE OUT" lettering              |

### Timer-Driven Animation

Animation timing is handled by the `IvOneShotTimerProc` (0xF96025) event handler, which provides single-shot timer callbacks for UI animation frame ticks.

### Title changes are immediate

The firmware does not animate a change of screen. `MainTitleCtrl_ChangeTitle` (0xF9936D), MainTitleControl's
`EVT_CHANGE_TITLE` case, only records the title ids (`PREVIOUS_TITLE` := `CURRENT_TITLE`, `ACTIVE_TITLE_PREVIOUS` :=
`ACTIVE_TITLE`, then `CURRENT_TITLE` = `ACTIVE_TITLE` := the new id), requests a panel indicator update (0x61),
clears the held-switch masks and resets the audio voice state (`AudioMode_ResetVoiceState`); the new title's view
is painted on the next screen update. The RAM words 0x02749A / 0x02749E / 0x0274A2, once described here as a
transition counter, timer and type, are the panel's held-switch masks (`PANEL_SW_HELD_UP`, `PANEL_SW_HELD_DOWN`,
`PANEL_SW_HELD_BOTH`): every reader and writer of them is in the panel-switch code (`SwbtB3_OnPanelEvent`,
`CtrlPanel_DispatchCombinedState`). 0x0274A6-0x0274AE hold MainTitleControl's delayed requests:
`MainTitleCtrl_OnSetTitleFlag` (event `MT_SetTitleFlag`) stores the title-flags word in `TITLE_FLAGS_PENDING` with
a count of 10 in `TITLE_FLAGS_DELAY`, `MainTitleCtrl_OnOtherPartLed` its LED request in `OTHER_PART_LED_PENDING` /
`OTHER_PART_LED_DELAY`, and `MainTitleCtrl_OnMainLoopCount` (once per main-loop pass) counts both down, latching the
flags into `TITLE_FLAGS_LATCHED` (read by `CtrlPanel_GetSelectionState`) and applying the LED.

Nothing else animates a change of title either: palette changes (`ChangePalette`, `PaletteBankRotate`), the
FADE IN / FADE OUT setting bitmaps, blanking during large updates (`VGA_ScreenBlank`), UI timers
(`IvOneShotTimerProc`) and software scrolling (`MovePixels`) all exist, but none of them runs on a title change.

### Scrolling

All scrolling is software-based — no VGA hardware scroll registers are used. Scrolling is implemented via `MovePixels` (0xFABA53), which copies rectangular pixel blocks within the offscreen buffer. The `AcRotStrBoxProc` (0xF967E8) handler provides smooth scrollbar animation with timer-based auto-repeat.

The names "SlideMove" and "SlideBase" at 0xEAB8D8 are not an animation feature. They are entries of `BitmapID_Names`, the name table of the NAKA bitmap-ID property (`BitmapIDProc` reads `BitmapIDProc_PtrTable[id]`): `idSlideBase` = 2 and `idSlideMove` = 3, beside `idMixerControl` / `idMixerPoint` = 4 / 5. The development-time table `BitmapID_FileNamePtrTable`, which nothing in the ROM reads, gives their resource files as `slide.bmp` and `slmove.bmp`. [INFERENCE] From the names and the pairing with MixerControl / MixerPoint, they are the track and the moving knob of a slider control.

## MAME Emulation Status

| Component              | Status      | Notes                                                                             |
|------------------------|-------------|-----------------------------------------------------------------------------------|
| MN89304 VGA Controller | **Working** | Register map emulated, 320×240 8bpp LCD output                                    |
| VRAM                   | **Working** | 256KB at 0x1A0000-0x1DFFFF, linear framebuffer                                    |
| Palette                | **Working** | 256-color palette with 4-bit RAMDAC (VGA DAC at 0x170000)                         |
| Display output         | **Working** | Full screen rendering visible, UI widgets draw correctly                          |
| Font rendering         | **Working** | All firmware text drawing functions operate correctly                             |
| Palette changes        | **Working** | `ChangePalette` / `PaletteBankRotate` (there are no title transitions to emulate) |

The display is one of the most complete subsystems in MAME emulation. The MN89304 VGA controller is emulated as a custom device with the KN5000-specific RAMDAC and offset override behaviors.

## Code References

> Addresses are v10, checked against `symbols/maincpu_v10_symbols_reference.txt` at disassembly
> commit `3417969c0` (2026-10-06). v9 shares most of them; v7 does not.

### Core Display

| Symbol                             | Address    | Purpose                                                                                                                    |
|------------------------------------|------------|----------------------------------------------------------------------------------------------------------------------------|
| `Display_ResetDirtyFlags`          | `0xEF5B27` | Clear all dirty flags                                                                                                      |
| `Display_UpdateDirtyRegions`       | `0xEF5B36` | Check and redraw dirty regions                                                                                             |
| `UpdateScreen`                     | `0xFAA61D` | Copy changed regions to VRAM                                                                                               |
| `Set_XWA_to_320_times_XDE`         | `0xEF5088` | Y×320 coordinate calculation                                                                                               |
| `VGA_ScreenBlank`                  | `0xFB319A` | Blank display during updates                                                                                               |
| `VGA_ScreenUnblank`                | `0xFB318A` | Restore display after updates                                                                                              |
| `VGA_Initialize`                   | `0xFB2B06` | Run-time VGA setup (display init phase 0): registers, 256-entry palette                                                    |
| `VGA_ConfigExtSequencer`           | `0xFB36A9` | Load the MN89304 seq 0x09-indexed table (same values as boot `VGA_Extended_Init`)                                          |
| `VGA_ConfigExtSequencer_AltA`      | `0xFB3264` | Unreferenced second version of that table                                                                                  |
| `VGA_ConfigExtSequencer_AltB`      | `0xFB3AED` | Unreferenced third version of that table                                                                                   |
| `_Write_VGA_Register`              | `0xFB3087` | Write C to port 0x170000 + WA after a 128-loop delay                                                                       |
| `_Read_VGA_Register`               | `0xFB309D` | Read port 0x170000 + WA (no delay)                                                                                         |
| `LcdOn`                            | `0xFAA5B6` | Enable LCD output                                                                                                          |
| `LcdOff`                           | `0xFAA5DB` | Disable LCD output                                                                                                         |
| `DrawQueue_Alloc`                  | `0xFAA444` | Allocate space in deferred draw queue                                                                                      |
| `DrawRing_Post`                    | `0xFAA36C` | Post a draw command to the draw task's ring (RAM 0x03247C), retrying while it is full (was `DisplayCmd_DequeueAndExecute`) |
| `IS_XSP_INSIDE_4K_REGION_AT_1C032` | `0xFAA532` | Check if caller runs in draw task context                                                                                  |
| `InitializeGraphics`               | `0xFAA547` | Boot-time graphics initialization                                                                                          |
| `DrawFunc`                         | `0xFAA48C` | Generic draw function dispatch with deferred support                                                                       |

### Drawing Primitives

| Symbol                          | Address    | Purpose                          |
|---------------------------------|------------|----------------------------------|
| `ReadPixel`                     | `0xFAA7B2` | Read pixel from offscreen buffer |
| `ModifyPixel`                   | `0xFAA7E4` | Write single pixel               |
| `ModifyPixelEx`                 | `0xFAA844` | Write/clear/OR/AND/XOR pixel     |
| `DrawLine`                      | `0xFAA98A` | Bresenham line drawing           |
| `DrawLineEx`                    | `0xFAAF12` | Line with drawing mode           |
| `DrawBox`                       | `0xFAB273` | Filled rectangle                 |
| `DrawFrame`                     | `0xFAB3DE` | Rectangle outline                |
| `DrawFrameEx`                   | `0xFAB809` | Styled frame with XOR            |
| `VRAM_FillRect`                 | `0xEF50DF` | Direct VRAM rectangle fill       |
| `SetChangeRect`                 | `0xFAA762` | Expand dirty bounding box        |
| `Copy_DE_words_from_XBC_to_XWA` | `0xEF18D7` | Block memory copy (blit)         |

### Bitmap & Sprite

| Symbol                               | Address    | Purpose                         |
|--------------------------------------|------------|---------------------------------|
| `DrawBitmap`                         | `0xFABC3C` | Bitmap with transparency (0xF7) |
| `DrawBitmapFast`                     | `0xFABE13` | Opaque bitmap (no transparency) |
| `DrawIcons`                          | `0xFABF3F` | Icon from table at 0x938000     |
| `MovePixels`                         | `0xFABA53` | Copy rectangular pixel block    |
| `DrawWall`                           | `0xFABB73` | Full-screen wallpaper fill      |
| `Draw_FlashMemUpdate_message_bitmap` | `0xEF5040` | 1bpp update UI bitmap renderer  |

### Text

| Symbol                   | Address    | Purpose                      |
|--------------------------|------------|------------------------------|
| `DrawString`             | `0xFACACA` | Core text renderer           |
| `DrawStringCentered`     | `0xFACEAC` | Center-aligned text          |
| `DrawStringLeftJustify`  | `0xFACF4A` | Left-aligned text            |
| `DrawStringRightJustify` | `0xFACFB1` | Right-aligned text           |
| `DrawStringReverse`      | `0xFAD084` | Reversed fg/bg colors        |
| `CalcTotalWidth`         | `0xFB26D1` | Calculate string pixel width |

### Display Regions

| Symbol | Address | Purpose |
|--------|---------|---------|
| `Display_RedrawStatusBar` | `0xF00999` | Region 0: Status bar |
| `Display_RedrawTitleBar` | `0xF00C89` | Region 1: Title bar |
| `Display_RedrawSelection` | `0xF00DA5` | Region 2: Selection highlight |
| `Display_RedrawMainContent` | `0xF00C33` | Region 3: Main content |
| `Display_RedrawSidePanel` | `0xF00E35` | Region 4: Side panel |
| `Display_RedrawMenu` | `0xEFF110` | Region 5: Menu area |
| `Display_RedrawButtonLabels` | `0xF00FDC` | Region 6: Button labels |
| `Display_RedrawParameters` | `0xEF6F1A` | Region 7: Parameter display |
| `Display_RedrawValues` | `0xEF6FA3` | Region 8: Value display |
| `Display_RedrawIndicators` | `0xEF704B` | Region 9: Indicators |
| `Display_RedrawFooter` | `0xF00C4A` | Region 10: Footer |

### Palette & Effects

| Symbol                      | Address    | Purpose                              |
|-----------------------------|------------|--------------------------------------|
| `ChangePalette`             | `0xFAF2C7` | Switch color palette                 |
| `ChangeWall`                | `0xFAF20B` | Load wallpaper                       |
| `PaletteBankRotate`         | `0xFAF346` | Fade via palette bank rotation       |
| `AcFadeSetGridBoxProc`      | `0xF75229` | Fade-setting grid-box procedure      |
| `MainTitleCtrl_ChangeTitle` | `0xF9936D` | Record a title change (no animation) |
| `Arrow_DrawHorizontal`      | `0xF96180` | `ArrowProc`'s horizontal arrow       |
| `Arrow_DrawVertical`        | `0xF9635E` | `ArrowProc`'s vertical arrow         |

## How to Contribute

See [Help Wanted]({{ site.baseurl }}/help-wanted/) for contribution guidelines.

The HDAE5000 ROM has documented VGA palette setup at `0x28F8E0` which can serve as a reference for understanding the display interface.
