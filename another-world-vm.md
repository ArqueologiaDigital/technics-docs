---
layout: page
title: Another World VM
permalink: /another-world-vm/
---

# Another World VM Port

A port of Delphine Software's **Another World** (1991) running natively on the Technics KN5000 keyboard. The game's original bytecode interpreter is reimplemented in TLCS-900/H2 assembly, executing the unmodified game data of the MS-DOS release on the KN5000's hardware.

> **Project Page:** [felipesanches.github.io/kn5000-anotherworld](https://felipesanches.github.io/kn5000-anotherworld/) | **Source:** [GitHub](https://github.com/felipesanches/kn5000-anotherworld)

## Overview

| Property      | Value                                                                                                                                                              |
|---------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Target CPU    | TMP94C241F (TLCS-900/H2) @ 16 MHz                                                                                                                                  |
| Display       | MN89304 VGA controller, 320x240 @ 8bpp                                                                                                                             |
| Input         | Control panel buttons via SC1 synchronous serial                                                                                                                   |
| Build Targets | Standalone maincpu ROM (2 MB). An HDAE5000 extension build (512 KB) compiles, but the game's 974 KB of resources do not fit, so at most the intro can run that way |
| Game Data     | Original MS-DOS release resources (MEMLIST.BIN + BANK01-BANK0D: bytecode, polygons, palettes, bitmaps)                                                             |

## The KN7000 port, on the real instrument

The same VM also runs on the Technics **KN7000**, rewritten for its Panasonic MN10300 CPU. One
build is a program for the project's SD loader: the stock firmware starts it from the SD card
through STYLE CONVERT and one loader floppy. That build **runs on the owner's KN7000**:

- **Speed.** The first run on the unit, on 2026-10-20, managed 1.5 frames per second, because the
  LCD frame is slow to write. A blit that writes only the pixels that changed brought it to 19-21
  frames per second over a whole run, 25-30 at best.
- **Sound.** Sound effects and music play through the KN7000's own tone generator. The game writes
  MIDI into the firmware's MIDI IN 1 receive ring, on channels 4-7, 10 and 11-14, with GM program
  changes, and its music player produces the intro's sync marks (variable `0xF4`). The owner
  confirmed that it plays on the instrument.
- **Memory.** It loads each part's files from the card when the part starts and keeps everything in
  the RAM the firmware leaves to a converter. It never touches the battery-backed panel memories.

The details, with the memory map, the controls and the unit's own speed figures, are on
[Your Own Code on a Stock KN7000]({{ site.baseurl }}/kn7000-cnv-homebrew/#another-world-on-the-instrument).
A second KN7000 build, a ride-along in the SP7001 SD plug-in, is silent and runs in MAME only
([SP7001 homebrew]({{ site.baseurl }}/kn7000-sp7001-homebrew/#a-larger-example-another-world)).

The rest of this page is about the KN5000 port.

## Architecture

The game uses a bytecode virtual machine originally designed for the Amiga (Motorola 68000). The VM interprets **big-endian bytecode on a little-endian CPU**, requiring byte-swap operations (`EX W, A`) on every 16-bit fetch.

### VM Execution Model

- **64 threads** with cooperative multitasking (no preemption)
- Each thread has a program counter stored in `THREADS_DATA`
- Register `XIX` tracks the current bytecode position during execution
- Thread scheduling happens at frame boundaries via `NEXT_THREAD`

### Bytecode Opcodes

All 27 opcodes (0x00-0x1A) are implemented:

| Range     | Category                   | Examples                                                                                |
|-----------|----------------------------|-----------------------------------------------------------------------------------------|
| 0x00-0x05 | Variables and calls        | MOVCONST, MOV, ADD, ADDCONST, CALL, RET                                                 |
| 0x06-0x0A | Flow control               | PAUSETHREAD (break), JMP, SETVEC, DJNZ, CONDJMP                                         |
| 0x0B-0x10 | Palette, threads and pages | SETPALETTE, RESETTHREAD, SELECTVIDEOPAGE, FILLVIDEOPAGE, COPYVIDEOPAGE, BLITFRAMEBUFFER |
| 0x11-0x12 | Threads and text           | KILLTHREAD, DRAWSTRING                                                                  |
| 0x13-0x17 | Arithmetic and logic       | SUB, AND, OR, SHL, SHR                                                                  |
| 0x18-0x1A | Sound and resources        | PLAYSOUND, LOADRESOURCE, PLAYMUSIC                                                      |
| 0x40/0x80 | Video                      | Polygon/sprite rendering                                                                |

### Video Rendering

Four 320x200 game pages (64,000 bytes each, one per 64 KB slot) support double-buffered rendering; the 320x200 image is drawn 20 lines down on the 320x240 LCD:
- **Polygon engine**: Interprets vertex lists from video data resources, drawing filled convex polygons
- **Bitmap loader**: Decompresses full-screen images (ByteKiller algorithm)
- **Palette**: 16 colors, 4-bit per channel (0x0RGB format), mapped to MN89304's 4-bit DAC

### Memory Layout

**Maincpu target** (standalone ROM):

| Address  | Size  | Contents                                                                           |
|----------|-------|------------------------------------------------------------------------------------|
| 0x010000 | 64 KB | VM variables, thread data (the stack grows down from `0x001000`, below this block) |
| 0x020000 | 64 KB | Page buffer 0                                                                      |
| 0x030000 | 64 KB | Page buffer 1                                                                      |
| 0x040000 | 64 KB | Page buffer 2                                                                      |
| 0x050000 | 64 KB | Page buffer 3                                                                      |
| 0x060000 | —     | Offscreen buffer (used by vga_init)                                                |
| 0xE00000 | 2 MB  | Program ROM (code + game resources)                                                |

**Extension target** (HDAE5000 slot):

| Address           | Size      | Contents                         |
|-------------------|-----------|----------------------------------|
| 0x200000          | 64 KB     | VM variables, thread data, stack |
| 0x210000          | —         | Offscreen buffer                 |
| 0x240000-0x27FFFF | 4 x 64 KB | Page buffers 0-3                 |
| 0x280000          | 512 KB    | Extension ROM                    |

## Input System

The KN5000's control panel buttons are read via **SC1 synchronous serial** at 250 kHz. The game polls three button segments each frame (CPL_SEG10's HELP and OTHER PARTS/TR open the help screen and the password part):

| KN5000 Button        | Segment  | Bit | Game Action                |
|----------------------|----------|-----|----------------------------|
| Part Select: RIGHT 2 | CPR_SEG4 | 1   | Jump (UP)                  |
| CONDUCTOR: LEFT      | CPR_SEG4 | 4   | Move LEFT                  |
| CONDUCTOR: RIGHT 2   | CPR_SEG4 | 5   | Crouch (DOWN)              |
| CONDUCTOR: RIGHT 1   | CPR_SEG4 | 6   | Move RIGHT                 |
| VARIATION 4          | CPL_SEG4 | 3   | ACTION (run/kick/draw gun) |

### Serial Protocol

Each button query is a 4-byte exchange:
1. Send command byte (`0xE0` for right panel, `0x20` for left panel)
2. Send segment number (`0x04`)
3. Send dummy byte (`0xFF`) — response header received
4. Send dummy byte (`0xFF`) — button bitmap received

The TX complete flag (`INTES1` bit 7) is polled between bytes. The baud rate generator (BR1CR = 0x14) provides the 250 kHz clock — **not** the TO2 trigger, which would be corrupted by Timer 1 system tick interrupts.

## Frame Timing

A hardware timer provides frame pacing:

- **Timer 0/1 cascade** at 12,500 Hz (80 µs per tick)
- `INTT1` ISR increments `SYSTEM_TICKS` counter
- `PAUSE` opcode reads `var[0xFF]` for frame duration in 20 ms slices (250 ticks each)
- DJNZ fallback counter provides minimum frame time

## Game Parts

The game consists of multiple "parts", each with its own set of resources (bytecode, video data, palettes):

| Part | ID              | Description                                |
|------|-----------------|--------------------------------------------|
| 0    | Protection/Logo | Interplay logo, copy protection (bypassed) |
| 1    | Intro           | Opening cinematic                          |
| 2    | Water           | First gameplay level                       |
| 3    | Prison          | Escape sequence                            |
| 4    | Citadel         | Main exploration                           |
| 5-7  | Arena/Baths     | Later levels                               |
| 8-9  | Password        | Password entry screen                      |

Part switching loads new resources and reinitializes the VM. Copy protection checks (parts 0, 2, 4, 8-9) are bypassed by pre-setting VM variables at startup.

## Build and Test

```bash
cd kn5000-anotherworld/

make            # Build maincpu ROM + create MAME ROM set
make extension  # Build as HDAE5000 extension ROM (resources do not fit: intro only)
make test TARGET=extension  # Run the extension build (plain `make test` runs the maincpu build)
```

Requirements:
- ASL Macro Assembler 1.42 Beta (`asl` and `p2bin`; Makefile variable `ASL_PATH`, default `../../tools/asl`)
- Original KN5000 ROMs (for MAME ROM set). Pass their directory as `ORIGINAL_ROMS` and the ROM-set output directory as `ROMSET_BASE`: the Makefile's defaults are paths on the author's machine
- The MS-DOS game data files (MEMLIST.BIN and BANK01-BANK0D) in `game_data/MSDOS/`; `tools/extract_resources.py` extracts the resources from them
- A checkout of [kn5000-roms-disasm](https://github.com/ArqueologiaDigital/technics-roms-disasm) at `../../kn5000-roms-disasm` (Makefile variable `DISASM_REPO`), whose `archive/asl/` sources the build includes

## Implementation Status

| Feature                     | Status                                                                                                             |
|-----------------------------|--------------------------------------------------------------------------------------------------------------------|
| All VM opcodes (0x00-0x1A)  | Implemented                                                                                                        |
| Polygon rendering           | Working                                                                                                            |
| Bitmap decompression        | Working (ByteKiller)                                                                                               |
| Palette management          | Working (4-bit DAC)                                                                                                |
| Frame timing                | Working (hardware timer, 12,500 Hz cascade)                                                                        |
| Part switching              | Working (all protection checks bypassed)                                                                           |
| Input (directions + action) | Working (SC1 serial to cpanel HLE)                                                                                 |
| MAME control panel          | **Fully working** — both left and right panels                                                                     |
| Copy protection bypass      | Working (var[0xBC], var[0xDC], var[0xF2])                                                                          |
| Sound effects               | Stub (consumes bytecode, no output); the KN7000 port plays them ([above](#the-kn7000-port-on-the-real-instrument)) |
| Music                       | Stub (consumes bytecode, no output); the KN7000 port plays it                                                      |

The MAME KN5000 driver's control panel HLE (High Level Emulation) was developed alongside this VM. All serial communication bugs discovered during VM development were fixed while maintaining compatibility with the original KN5000 firmware. See the [Serial Firmware Compatibility]({{ site.baseurl }}/serial-firmware-compatibility/) report for details.

## Technical Challenges

### Endianness
The original game was designed for the big-endian Motorola 68000. Every 16-bit value fetched from bytecode must be byte-swapped (`EX W, A` after `LD WA, (XIX)`) on the little-endian TLCS-900.

### 4-bit Palette DAC
The MN89304's RAMDAC is 4-bit (0-15), not 6-bit like standard VGA. The game's 4-bit palette values (0x0RGB format) map directly without scaling.

### Copy Protection
The original game includes protection checks that read specific VM variables. These are bypassed by initializing `var[0xBC]`, `var[0xDC]`, and `var[0xF2]` to expected values at startup.

### FREEZE Semantics
The VM's thread freeze mechanism is **persistent**: `CHECK_THREAD_REQUESTS` applies `thread->state = thread->requested_state` every frame without clearing the request. The `REQUESTED_STATE` is initialized to `NOT_FROZEN`. `RESET_THREAD` type 0 = unfreeze, type 1 = freeze. This matches the reference implementation — threads stay frozen until explicitly unfrozen by another thread's opcode.

## Related Pages

- [CPU Subsystem]({{ site.baseurl }}/cpu-subsystem/) — TMP94C241F architecture
- [Display Subsystem]({{ site.baseurl }}/display-subsystem/) — MN89304 VGA controller
- [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) — Button/LED serial protocol
- [Memory Map]({{ site.baseurl }}/memory-map/) — KN5000 address space
- [HDAE5000]({{ site.baseurl }}/hdae5000/) — Extension board (alternative build target)
