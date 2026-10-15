---
layout: page
title: "HDAE5000 Homebrew Development"
permalink: /hdae5000-homebrew/
---

# Writing Custom HDAE5000 Extension ROMs

The HD-AE5000 extension slot can run custom code on the KN5000's main CPU. By replacing the HDAE5000 ROM with a custom binary, you can create games, demos, or utilities that run on the keyboard hardware. This page documents the extension ROM protocol, known toolchain bugs, and a working build pipeline.

> **Status**: A Minesweeper game is fully playable on the KN5000 LCD via the HDAE5000 extension slot. Boot initialization, handler registration, DISK MENU entry with custom icon, game activation via button press, palette loading, and VRAM rendering are all working in MAME. The firmware's object dispatch system, handler registration protocol, and event dispatch are fully implemented. Control-panel input during gameplay works as well (see [Control Panel Input](#control-panel-input)).

![DISK MENU showing Mines Game entry]({{ site.baseurl }}/assets/images/mines-disk-menu.png)
*The KN5000 DISK MENU in MAME showing the "Mines Game" entry with a custom mine icon at the bottom-right position. Selecting this entry activates the game.*

![Mines game rendering on KN5000 LCD in MAME]({{ site.baseurl }}/assets/images/mines-game-rendering.png)
*Minesweeper game rendering on the KN5000 LCD screen after activation from the DISK MENU. The green border, red minefield, and yellow tile markers are drawn by the extension ROM's game code.*

## Prerequisites

- **[LLVM with TLCS-900 backend](https://github.com/felipesanches/llvm-project/tree/tlcs900_backend)** -- a custom LLVM build with the TLCS-900 target
- **MAME** with KN5000 driver for testing
- Knowledge of the [HDAE5000 firmware protocol]({{ site.baseurl }}/hdae5000/)

## Quick Start

This section walks through building a minimal "hello world" extension ROM that draws a colored rectangle on the KN5000 LCD. For the full protocol details, see the sections below.

### 1. Set Up the Toolchain

```bash
# Build LLVM with TLCS-900 backend
git clone https://github.com/felipesanches/llvm-project.git -b tlcs900_backend
cd llvm-project
mkdir build && cd build
cmake -G Ninja ../llvm -DLLVM_TARGETS_TO_BUILD="X86" -DLLVM_EXPERIMENTAL_TARGETS_TO_BUILD="TLCS900" \
  -DLLVM_ENABLE_PROJECTS="clang;lld" -DCMAKE_BUILD_TYPE=Release
ninja
```

### 2. Create the Project Structure

```
my_extension/
  startup.s       # XAPR header + entry points (assembly)
  main.c          # Your C code
  kn5000.ld       # Linker script
  Makefile
```

### 3. Minimal Startup Assembly (startup.s)

```asm
.equ VIDEO_RAM_BASE, 0x1A0000
.equ WORKSPACE_PTR,  0x200008
.equ GAME_ACTIVE,    0x200000
.equ STACK_TOP,      0x203000
.equ SAVED_SP,       0x200044

.globl GAME_ACTIVE
.globl yield_to_firmware

.section .startup, "ax", @progbits

; XAPR Header (8 bytes)
        .ascii  "XAPR"
        .byte   0x34, 0xA1, 0x2F, 0x00

; Entry Point 1: Boot_Init (offset 0x08)
        jp      Boot_Init
        ret
        .byte   0x00, 0x00, 0x00

; Entry Point 2: Frame_Handler (offset 0x10)
        jp      Frame_Handler
        ret
        .byte   0x00, 0x00, 0x00

; Entry Points 3-4: Unused
        ret
        .byte   0x00, 0x00, 0x00
        ret
        .byte   0x00, 0x00, 0x00

Boot_Init:
        ld      (WORKSPACE_PTR), xwa    ; Save workspace pointer
        ret

Frame_Handler:
        push    xwa
        push    xbc
        push    xde
        push    xhl
        push    xix
        push    xiy
        push    xiz

        ; Check if game is active
        ld      xhl, GAME_ACTIVE
        ld      xwa, (xhl)
        and     xwa, 0xFF
        cp      xwa, 0
        jrl     z, .Lframe_done

        ; First frame: set up stack and call main()
        ld      xwa, xsp
        ld      (SAVED_SP), xwa
        ld      xsp, STACK_TOP
        call    main

        ; main() returned — deactivate
        ld      xhl, GAME_ACTIVE
        ld      xwa, 0
        ld      (xhl), xwa
        ld      xwa, (SAVED_SP)
        ld      xsp, xwa

.Lframe_done:
        pop     xiz
        pop     xiy
        pop     xix
        pop     xhl
        pop     xde
        pop     xbc
        pop     xwa
        ret

; yield_to_firmware: save game context, return to firmware main loop.
; Firmware calls Frame_Handler next frame, which resumes here.
yield_to_firmware:
        ; (See Mines startup.s for full cooperative multitasking implementation)
        ret
```

### 4. Minimal C Code (main.c)

```c
#include <stdint.h>

#define VRAM_BASE  ((volatile uint8_t *)0x1A0000)
#define LCD_WIDTH  320
#define LCD_HEIGHT 240

#define VGA_DAC_WRITE_INDEX ((volatile uint8_t *)0x1703C8)
#define VGA_DAC_DATA        ((volatile uint8_t *)0x1703C9)

void set_palette_entry(uint8_t index, uint8_t r, uint8_t g, uint8_t b) {
    *VGA_DAC_WRITE_INDEX = index;
    *VGA_DAC_DATA = r;  /* 4-bit values (0-15): the MN89304 DAC uses only the low 4 bits */
    *VGA_DAC_DATA = g;
    *VGA_DAC_DATA = b;
}

void main(void) {
    /* Set palette: index 1 = bright green */
    set_palette_entry(1, 0, 15, 0);

    /* Draw a green rectangle */
    for (int y = 80; y < 160; y++) {
        for (int x = 100; x < 220; x++) {
            VRAM_BASE[y * LCD_WIDTH + x] = 1;
        }
    }

    /* Spin (in a real app, use yield_to_firmware() for cooperative multitasking) */
    while (1) {}
}
```

### 5. Linker Script (kn5000.ld)

```
MEMORY {
  ROM (rx)  : ORIGIN = 0x280000, LENGTH = 512K
  RAM (rwx) : ORIGIN = 0x200000, LENGTH = 12K
}
SECTIONS {
  .startup 0x280000 : { startup.o(.startup) } > ROM
  .text             : { *(.text*) } > ROM
  .rodata           : { *(.rodata*) } > ROM
  .data             : { *(.data*) } > RAM AT > ROM
  .bss              : { *(.bss*) } > RAM
}
```

### 6. Makefile

```makefile
LLVM_BIN := /path/to/llvm-project/build/bin
CLANG    := $(LLVM_BIN)/clang
LLC      := $(LLVM_BIN)/llc
LLD      := $(LLVM_BIN)/ld.lld
OBJCOPY  := $(LLVM_BIN)/llvm-objcopy

CFLAGS   := -target tlcs900 -ffreestanding -nostdlib -O2
LLC_FLAGS := -mtriple=tlcs900 -mcpu=tmp94c241 -O2

BUILD    := build

all: $(BUILD)/extension.bin

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/main.ll: main.c | $(BUILD)
	$(CLANG) $(CFLAGS) -S -emit-llvm -o $@ $<

$(BUILD)/main.o: $(BUILD)/main.ll
	$(LLC) $(LLC_FLAGS) -filetype=obj -o $@ $<

$(BUILD)/startup.o: startup.s | $(BUILD)
	$(CLANG) -target tlcs900 -mcpu=tmp94c241 -c -o $@ $<

$(BUILD)/extension.elf: $(BUILD)/startup.o $(BUILD)/main.o kn5000.ld
	$(LLD) -T kn5000.ld -o $@ $(BUILD)/startup.o $(BUILD)/main.o

$(BUILD)/extension.bin: $(BUILD)/extension.elf
	$(OBJCOPY) -O binary $< $@
	@SIZE=$$(stat -c%s "$@"); \
	if [ "$$SIZE" -lt 524288 ]; then \
		dd if=/dev/zero bs=1 count=$$((524288 - $$SIZE)) 2>/dev/null | \
		tr '\0' '\377' >> $@; \
	fi

clean:
	rm -rf $(BUILD)
```

### 7. Build and Test

```bash
make
# Copy to MAME ROM set
cp build/extension.bin /path/to/romset/kn5000/hd-ae5000_v2_06i.ic4
# Run (game activation requires Lua or handler registration — see below)
mame kn5000 -rompath /path/to/romset -extension hdae5000 -window
```

> **Note:** This minimal example skips handler registration and DISK MENU integration. The `GAME_ACTIVE` flag at `0x200000` must be set to 1 for Frame_Handler to call `main()`. For automated testing, use a MAME Lua script: `emu.register_periodic(function() if manager.machine.time:as_double() > 30 then manager.machine.devices[":maincpu"].spaces["program"]:write_u8(0x200000, 1) end end)`. For proper DISK MENU integration with button activation, see [Handler Registration](#handler-registration) and [DISK MENU Activation](#disk-menu-activation-mechanism).

For a complete working example with handler registration, input, display management, and cooperative multitasking, see the [Mines game source code](https://github.com/ArqueologiaDigital/Mines/tree/kn5000_port/platforms/kn5000).

## Extension ROM Protocol

### XAPR Header Format

The KN5000 firmware validates extension ROMs by checking for an "XAPR" magic string at address `0x280000`. The header occupies the first 32 bytes:

```
Offset  Size  Contents              Description
------  ----  --------------------  -----------
0x00    4     "XAPR"                Magic signature
0x04    4     34 A1 2F 00           Version/ID metadata
0x08    4     JP Boot_Init          Entry point 1: boot initialization
0x0C    4     RET + 3x NOP          Padding
0x10    4     JP Frame_Handler      Entry point 2: frame callback
0x14    4     RET + 3x NOP          Padding
0x18    4     RET + 3x NOP          Entry point 3: unused
0x1C    4     RET + 3x NOP          Entry point 4: unused
```

The `JP` instruction (opcode `0x1B`) is followed by a 24-bit little-endian target address.

### Firmware XAPR Validation

The main firmware validates the extension ROM and calls Boot_Init from routine `Xapr_DetectAndCallBootInit`:

```asm
; At Xapr_DetectAndCallBootInit in kn5000_v10_program.rom:
PUSHW 0004h                          ; Compare 4 bytes
PUSHW 00e1h                          ; High word of the pointer to "XAPR" (0x00E1FFC6)
PUSHW 0ffc6h                         ; Low word of that pointer
LD    XWA, 00280000h                 ; Extension ROM base address
PUSH  XWA
CALL  String_Compare                 ; Compare first 4 bytes
ADD   XSP, 0000000ah                 ; Clean stack
CP    HL, 0                          ; Match?
JR    NZ, .no_extension              ; Skip if no match

LD    (03DD04h), 001h                ; Set XAPR detection flag

; ... fall through to call Boot_Init ...

LD    XHL, 00280008h                 ; Address of boot init entry point
LDA   XWA, 027ED2h                  ; Workspace pointer = 0x027ED2
CALL  T, XHL                        ; Call Boot_Init(XWA = workspace_ptr)
RET
```

The frame handler dispatcher (`Xapr_CallFrameHandler`) runs every iteration of the main event loop:

```asm
; Frame handler dispatcher:
CP    (03DD04h), 000h                ; Check XAPR detection flag
RET   Z                              ; Skip if no extension ROM
LD    XHL, 00280010h                 ; Address of frame handler entry point
CALL  T, XHL                        ; Call Frame_Handler()
RET
```

**Key observations:**
- The frame handler is called **unconditionally** every frame -- no registration needed
- The XAPR detection flag at `0x03DD04` is the only gate
  (`XAPR_PRESENT_FLAG` in the maincpu source, the same address in v7, v9 and v10)
- Hardware presence is checked separately via Port E bit 0 (active low)

### Workspace Pointer

The firmware passes `0x027ED2` in XWA to Boot_Init. This is the base address of the firmware's **object table** in main DRAM -- a data structure with 14-byte entries spanning from `0x027ED2` to `0x02BC12` (1,120 entries, ids 0x000-0x45F).

The workspace pointer reaches the firmware's functions through the object table
itself. Each 14-byte entry is `{class id, proc, count, data}` and the data pointer
sits at +10, so:

- `workspace + 0x0E0A` = `0x027ED2 + 14 × 0x100 + 10` is the data pointer of
  **object table 0x100**. That is the **Function table `InitializeRoot`
  registers**: 0x160 entries at ROM `0xEAFA6E`. Its parallel name table is
  table 0x400 (`WidgetName_InitPtrTable`, `0xEAFFF2`).
- `workspace + 0x0E88` = `0x027ED2 + 14 × 0x109 + 10` is the data pointer of
  **object table 0x109**, the **Function table `InitializeHama` registers**
  (`Hama_FunctionTable_109`, `0xE1F0EC`; 0x4B entries). Its names are table 0x409
  (`Hama_ModeParam_Table`, `0xE1F240`).

An offset into either table is 4 × the function's index, and the firmware's name
table gives the function's **own name** at the same index. The HD-AE5000 uses
99 of these functions (41 in table 0x100, 58 in table 0x109) at 953 call sites.
The disassembly spells each call symbolically as `WS_RootFnTable` /
`WS_HamaFnTable` plus a `RootFn_<name>` / `HamaFn_<name>` constant
(`hdae5000/hd-ae5000_v2_06i.s`), and the v10 build's label at each target
agrees with the firmware's name for all 99.

Evidence: `tools/hdae5000_fn_table_check.py` in this site's repository
(`python3 tools/hdae5000_fn_table_check.py --repo ../kn5000-roms-disasm`)
re-reads every constant's function pointer and name from
`original_ROMs/kn5000_v10_program.rom` and counts the call sites. The
disassembly's `scripts/converters/hdae5000_symbolize_fn_tables.py`, which
generated the constants, no longer runs as a check: it refuses because the
registration lines it checks for are no longer spelled as it expects:
`InitializeRoot`'s now reads `RegObjTabl NAKA_CLASS_Function, FunctionProc, 0x160, Root_FunctionTable_100, 0x100`,
and `InitializeHama`'s reads `Hama_FunctionTable_109` instead of `0xe1f0ec`. An earlier count of "100 functions" (the hdae lane
report) is not reproduced: the sources define 99 constants and use all 99.

**Earlier versions of this page guessed several of these wrong.** `+0x0100` is
`SendEvent`, not a "secondary dispatch function". `+0x0124` is `ApPostEvent`,
not a "display callback". `+0x0270` is `RegisterTitle`, not "graphics init
dispatch". `+0x02C4` is `GetViewInstance`, not "DISK MENU slot registration".
In table 0x109, `+0x0100`/`+0x0104`/`+0x0108` are `GetAdr_sqbtof` /
`GetAdr_sq_beadt` / `GetAdr_sqsrtc`, not "init functions". Each returns the
address of one main-CPU sequencer variable (RAM `0x041C`, `0x041B`, `0x0421`),
which the frame handler reads to drive the lyrics.

**Table 0x100 (`workspace + 0x0E0A`), the offsets the HD-AE5000 uses:**

| Offset | Index | Constant (firmware name after the prefix) | Main-CPU address (v10) |
|--------|------:|----------|---------|
| `+0x0084` | 33 | `RootFn_UpdateScreen` | `0xFAA61D` |
| `+0x009C` | 39 | `RootFn_DrawLine` | `0xFAA98A` |
| `+0x00A4` | 41 | `RootFn_DrawBox` | `0xFAB273` |
| `+0x00A8` | 42 | `RootFn_DrawFrame` | `0xFAB3DE` |
| `+0x00B0` | 44 | `RootFn_MovePixels` | `0xFABA53` |
| `+0x00C4` | 49 | `RootFn_DrawString` | `0xFACACA` |
| `+0x00DC` | 55 | `RootFn_InheritedProc` | `0xFA4409` |
| `+0x00E4` | 57 | `RootFn_RegisterObjectTable` | `0xFA42FB` |
| `+0x0100` | 64 | `RootFn_SendEvent` | `0xFA9660` |
| `+0x0104` | 65 | `RootFn_PostEvent` | `0xFA9752` |
| `+0x0124` | 73 | `RootFn_ApPostEvent` | `0xFA9D58` |
| `+0x013C` | 79 | `RootFn_ResEventProc` | `0xFA58FB` |
| `+0x0140` | 80 | `RootFn_ResMethodProc` | `0xFA5948` |
| `+0x0148` | 82 | `RootFn_ResNameProc` | `0xFA62CB` |
| `+0x0150` | 84 | `RootFn_GetCharHeight` | `0xFB260A` |
| `+0x0154` | 85 | `RootFn_GetCharDescent` | `0xFB2617` |
| `+0x0158` | 86 | `RootFn_GetCenteredDelta` | `0xFB2624` |
| `+0x015C` | 87 | `RootFn_ConvertStrings` | `0xFB2640` |
| `+0x0168` | 90 | `RootFn_ClassProc` | `0xFA44E2` |
| `+0x0244` | 145 | `RootFn_FunctionProc` | `0xFA48A9` |
| `+0x0248` | 146 | `RootFn_ApFunctionProc` | `0xFA496C` |
| `+0x024C` | 147 | `RootFn_MainFunctionProc` | `0xFA4A18` |
| `+0x0250` | 148 | `RootFn_ApFuncCall` | `0xFA49B7` |
| `+0x0254` | 149 | `RootFn_MainFuncCall` | `0xFA4A63` |
| `+0x0270` | 156 | `RootFn_RegisterTitle` | `0xFA4D80` |
| `+0x0278` | 158 | `RootFn_GetTitleNow` | `0xFA5867` |
| `+0x0280` | 160 | `RootFn_ViewableProc` | `0xFA5995` |
| `+0x0294` | 165 | `RootFn_SetVisible` | `0xFA5E8C` |
| `+0x02C4` | 177 | `RootFn_GetViewInstance` | `0xFA6266` |
| `+0x02D4` | 181 | `RootFn_GetClientBox` | `0xF995DD` |
| `+0x02DC` | 183 | `RootFn_DrawDesignBox` | `0xFAD559` |
| `+0x03C4` | 241 | `RootFn_SetDialEnable` | `0xF9A53B` |
| `+0x03C8` | 242 | `RootFn_SetDialUp` | `0xF9A579` |
| `+0x03CC` | 243 | `RootFn_SetDialDown` | `0xF9A58A` |
| `+0x0410` | 260 | `RootFn_SetApTimer` | `0xFAA135` |
| `+0x0418` | 262 | `RootFn_KillApTimer` | `0xFAA257` |
| `+0x042C` | 267 | `RootFn_SetAutoInc` | `0xF9A5BD` |
| `+0x050C` | 323 | `RootFn_GetNamingWindowID` | `0xFA1FC7` |
| `+0x0534` | 333 | `RootFn_DeleteEvent` | `0xFA9868` |
| `+0x0538` | 334 | `RootFn_SleepMainTask` | `0xF9883C` |
| `+0x053C` | 335 | `RootFn_WakeUpMainTask` | `0xF9884B` |

**Table 0x109 (`workspace + 0x0E88`), the offsets the HD-AE5000 uses:**

| Offset | Index | Constant (firmware name after the prefix) | Main-CPU address (v10) |
|--------|------:|----------|---------|
| `+0x0004` | 1 | `HamaFn_FDLoadSaveTest` | `0xF1E5DA` |
| `+0x0008` | 2 | `HamaFn_GetMediaType` | `0xF525EC` |
| `+0x000C` | 3 | `HamaFn_PreLswLoad` | `0xFDB434` |
| `+0x0010` | 4 | `HamaFn_PostLswLoad` | `0xFDB43B` |
| `+0x0014` | 5 | `HamaFn_PreLswSave` | `0xFDB48E` |
| `+0x0018` | 6 | `HamaFn_PostLswSave` | `0xFDB48F` |
| `+0x001C` | 7 | `HamaFn_PrePmLoad` | `0xFDB490` |
| `+0x0020` | 8 | `HamaFn_PostPmLoad` | `0xFDB491` |
| `+0x0024` | 9 | `HamaFn_PrePmSave` | `0xFDB49E` |
| `+0x0028` | 10 | `HamaFn_PostPmSave` | `0xFDB49F` |
| `+0x002C` | 11 | `HamaFn_SeqLoadPre` | `0xF47850` |
| `+0x0030` | 12 | `HamaFn_SeqLoadPost` | `0xF47858` |
| `+0x0034` | 13 | `HamaFn_SeqSavePre` | `0xF47923` |
| `+0x0038` | 14 | `HamaFn_SeqSavePost` | `0xF47943` |
| `+0x003C` | 15 | `HamaFn_cmp_ld_mae` | `0xF6BC24` |
| `+0x0040` | 16 | `HamaFn_cmp_ld_ato` | `0xF6BC2F` |
| `+0x0044` | 17 | `HamaFn_cmp_sv_mae` | `0xF6BC48` |
| `+0x0048` | 18 | `HamaFn_cmp_sv_ato` | `0xF6BC5A` |
| `+0x004C` | 19 | `HamaFn_PreTmLoad` | `0xFF049F` |
| `+0x0050` | 20 | `HamaFn_PostTmLoad` | `0xFF04A0` |
| `+0x0054` | 21 | `HamaFn_PreTmSave` | `0xFF04E4` |
| `+0x0058` | 22 | `HamaFn_PostTmSave` | `0xFF04E5` |
| `+0x005C` | 23 | `HamaFn_msp_ld_mae` | `0xF6BC66` |
| `+0x0060` | 24 | `HamaFn_msp_ld_ato` | `0xF6BC71` |
| `+0x0064` | 25 | `HamaFn_msp_sv_mae` | `0xF6BC82` |
| `+0x0068` | 26 | `HamaFn_msp_sv_ato` | `0xF6BC99` |
| `+0x006C` | 27 | `HamaFn_PreMidiLoad` | `0xFDB4A0` |
| `+0x0070` | 28 | `HamaFn_PostMidiLoad` | `0xFDB4A1` |
| `+0x0074` | 29 | `HamaFn_PreMidiSave` | `0xFDB4A2` |
| `+0x0078` | 30 | `HamaFn_PostMidiSave` | `0xFDB4A3` |
| `+0x007C` | 31 | `HamaFn_FlashWrite` | `0xEF3C3C` |
| `+0x0080` | 32 | `HamaFn_GetResouceInfo` | `0xF1EA30` |
| `+0x0084` | 33 | `HamaFn_SetSepaOutMode` | `0xF1EB30` |
| `+0x0090` | 36 | `HamaFn_GetVolumeLabel` | `0xF527CE` |
| `+0x0094` | 37 | `HamaFn__findfirst` | `0xF5298A` |
| `+0x0098` | 38 | `HamaFn__findnext` | `0xF52AE8` |
| `+0x009C` | 39 | `HamaFn__findclose` | `0xF52AAA` |
| `+0x00A0` | 40 | `HamaFn_fopen_ext` | `0xF1ED24` |
| `+0x00A8` | 42 | `HamaFn_fread_ext` | `0xF1ED2C` |
| `+0x00AC` | 43 | `HamaFn_fclose_ext` | `0xF1ED30` |
| `+0x00B0` | 44 | `HamaFn_rcm_ld_XAPR_j` | `0xF1EB28` |
| `+0x00B4` | 45 | `HamaFn_rcm_sv_XAPR_j` | `0xF1EB2C` |
| `+0x00B8` | 46 | `HamaFn_rot_rdq_X` | `0xF1ED38` |
| `+0x00D0` | 52 | `HamaFn_ref_sem_X` | `0xF1ED50` |
| `+0x00E4` | 57 | `HamaFn_pdly_tim_X` | `0xF1ED64` |
| `+0x00E8` | 58 | `HamaFn_PlayHalt` | `0xF1ED68` |
| `+0x00EC` | 59 | `HamaFn_PlayStandBy` | `0xF1EDA8` |
| `+0x00F0` | 60 | `HamaFn_EditSwRefresh` | `0xF1EDBE` |
| `+0x0100` | 64 | `HamaFn_GetAdr_sqbtof` | `0xF1EDE2` |
| `+0x0104` | 65 | `HamaFn_GetAdr_sq_beadt` | `0xF1EDE7` |
| `+0x0108` | 66 | `HamaFn_GetAdr_sqsrtc` | `0xF1EDEC` |
| `+0x0114` | 69 | `HamaFn_sendCOMM` | `0xEF32F4` |
| `+0x0120` | 72 | `HamaFn_SwbtWr` | `0xFDB255` |
| `+0x012C` | 75 | `HamaFn_SetGlobalError` | `0xF1EDF6` |
| `+0x0130` | 76 | `HamaFn_malloc_X` | `0xF1EDFB` |
| `+0x0134` | 77 | `HamaFn_free_X` | `0xF1EE03` |
| `+0x0138` | 78 | `HamaFn_ChangePalette` | `0xFAF2C7` |
| `+0x013C` | 79 | `HamaFn_ChangeWall` | `0xFAF20B` |

Entries 75-79 of table 0x109 lie past the count its registration gives (0x4B =
75), yet the HD-AE5000 calls them (`SetGlobalError`, `malloc_X`, `free_X`,
`ChangePalette`, `ChangeWall`). Table 0x100 (`Root_FunctionTable_100`,
`ui_widgets/widget_names_charmap.s`) is still an `.incbin` slice in the main-CPU
source. Table 0x109 (`Hama_FunctionTable_109`, `factory_test/test_data.s`) has
been typed as `.long` code pointers since 2026-09-25.

### Boot_Init Calling Convention

```
Entry:
  XWA = workspace pointer (0x027ED2)

Expected behavior:
  Store workspace pointer for later use
  Perform initialization
  Return (RET) to firmware

Notes:
  Must preserve stack state (firmware continues initialization after return)
  Extension RAM at 0x200000-0x27FFFF is available for variables
  Extension ROM at 0x280000-0x2FFFFF is available for code and data
```

### Frame_Handler Calling Convention

```
Entry:
  No parameters (called from firmware main loop)

Expected behavior:
  Perform per-frame updates (display, input, etc.)
  Return (RET) to firmware

Notes:
  Called every main loop iteration while XAPR flag (0x03DD04) is set
  Should be fast -- firmware main loop handles other subsystems too
  All registers should be preserved or restored
```

## Handler Registration

### Overview

The original HDAE5000 firmware performs extensive setup during Boot_Init before any DISK MENU registration:

1. **Clear work buffer** -- 62,762 bytes zeroed at `0x22A000`
2. **Copy init data** -- 3,202 bytes from ROM `0x2F94B2` to RAM `0x23952A`
3. **Register 11 object tables and one title** -- via `workspace[0x0E0A][0x00E4]` (`RegisterObjectTable`) and `workspace[0x0E0A][0x0270]` (`RegisterTitle`)
4. **Load VGA palette** -- 256 entries from ROM
5. **Allocate DRAM and copy VRAM** -- 76,800 bytes to display areas
6. *Then* **call `workspace[0x0E0A][0x02C4]`** (`GetViewInstance`) for view object `0x00600002`, the DISK MENU's expansion item
7. **Set that record's fields** -- `+0x00` = class id `0x016A0005`, `+0x2A` = display name string (see [below](#disk-menu-slot-registration-workspace0x0e0a0x02c4))

For basic frame handler operation, handler registration is **not required**. The firmware calls the Frame_Handler entry point every frame regardless.

### RegisterObjectTable Protocol (workspace[0x0E0A][0x00E4])

The Handler_Registration routine at `0x280020` (now fully disassembled) registers handlers by building a 14-byte parameter block on the stack and calling the `RegisterObjectTable` function.

#### Parameter Block Format

```
Parameter block layout (14 bytes):
  +0x00  4 bytes  Class id of the table (e.g. 0x01600004 = class Class)
  +0x04  4 bytes  The class's proc (read from the workspace function table)
  +0x08  2 bytes  Record count (number of sub-objects) ← 16-bit field!
  +0x0A  4 bytes  Data pointer → record table (RAM or ROM address)

Call convention:
  WA  = handler ID (object table index, max 0x045F = 1119)
  XBC = pointer to parameter block (stack or RAM)
  Call workspace[0x0E0A][0x00E4]
```

**Important:** The `+0x08` field is a **record count** (number of 24-byte sub-object records), NOT a byte size. This was confirmed by:
- HDAE5000 handler 0x016A has `+0x08 = 0x000D` (13 records, matching its 13 sub-objects)
- `RegisterObject` (0xFA431A) increments `+0x08` when adding sub-objects
- `UnRegisterObject` (0xFA43B3) decrements `+0x08` when removing them
- Built-in handlers use counts like 55, 32, 256 (matching their sub-object counts)

#### RegisterObjectTable Implementation (0xFA42FB)

The actual implementation is a simple 14-byte block copy:

```asm
RegisterObjectTable:          ; 0xFA42FB
    CP    WA, 045Fh           ; Validate handler ID <= 1119
    RET   UGT                 ; Return if out of range
    EXTZ  XWA                 ; Zero-extend WA to 32-bit
    LD    XDE, XWA
    SLL   3, XDE              ; XDE = id * 8
    SUB   XDE, XWA            ; XDE = id * 7
    ADD   XDE, XDE            ; XDE = id * 14
    LD    XIX, 00027ED2h      ; Object table base address
    ADD   XIX, XDE            ; XIX = base + id * 14
    LD    XIY, XBC            ; XIY = parameter block source
    LD    BC, 7               ; 7 words = 14 bytes
    LDIRW                     ; Block copy from source to object table
    RET
```

This means `RegisterObjectTable` simply copies 14 bytes from the caller's parameter block to `object_table[handler_id * 14]`. The object table base at `0x027ED2` can hold up to 1,120 entries (handler IDs 0x0000-0x045F).

#### RegObjTable Macro (Firmware Convention)

The main CPU firmware uses two macro variants for handler registration:

```asm
; Variant 1: Data size read from ROM address
RegObjTable MACRO ParamA, ParamB, ParamC, ParamD, ParamE
    LDA   XBC, XSP            ; XBC = param block ptr (ON STACK)
    LD    XWA, ParamA          ; Class id (32-bit)
    LD    (XBC), XWA
    LDA   XWA, ParamB          ; Handler function (LEA, not LD)
    LD    (XBC + 004h), XWA
    LD    WA, (ParamC)          ; Data size: 16-bit read from ROM address
    LD    (XBC + 008h), WA      ; 16-BIT store to +0x08
    LDA   XWA, ParamD          ; Data pointer (LEA)
    LD    (XBC + 00Ah), XWA
    LD    WA, ParamE            ; Handler ID (16-bit)
    CALL  RegisterObjectTable
ENDM

; Variant 2: Data size as immediate value
RegObjTabl MACRO ParamA, ParamB, ParamC, ParamD, ParamE
    LDA   XBC, XSP
    LD    XWA, ParamA
    LD    (XBC), XWA
    LDA   XWA, ParamB
    LD    (XBC + 004h), XWA
    LDW   (XBC + 008h:8), ParamC   ; Immediate 16-bit store
    LDA   XWA, ParamD
    LD    (XBC + 00Ah), XWA
    LD    WA, ParamE
    CALL  RegisterObjectTable
ENDM
```

**Key detail:** Both macros use `LDA XBC, XSP` to point XBC at the parameter block which is allocated on the stack. The HDAE5000 also allocates its parameter block on the stack (14 bytes via `LDA XSP, XSP - 0Eh`). The parameter block can be anywhere in RAM -- the `RegisterObjectTable` function just does a block copy from whatever address XBC points to.

#### Firmware Registration Examples

Every module registers its **Class table** with class id `0x01600004` (the root
class `Class`) and proc `ClassProc` (0xFA44E2), at object-table index 0x160 +
its module number:

```
RegObjTable 01600004h, 0FA44E2h, 0E0CDACh, 0E0CD94h, 0166h  ; InitializeScoop (module 6)
RegObjTable 01600004h, 0FA44E2h, 0E0E95Ch, 0E0E944h, 016Bh  ; InitializeNaka  (module 0x0B)
RegObjTable 01600004h, 0FA44E2h, 0E17322h, 0E16C86h, 0164h  ; InitializeSuna  (module 4)
RegObjTable 01600004h, 0FA44E2h, 0E1F0BCh, 0E1F080h, 0169h  ; InitializeHama  (module 9)
RegObjTable 01600004h, 0FA44E2h, 0E20CAEh, 0E208ECh, 0167h  ; InitializeYoko  (module 7)
RegObjTable 01600004h, 0FA44E2h, 0E27596h, 0E27180h, 0168h  ; InitializeKubo  (module 8)
```

This page previously
attributed the 0x16B, 0x167 and 0x168 lines to InitializeKSS, InitializeKubo
and InitializeNaka. The v10 sources put them in `InitializeNaka`,
`InitializeYoko` and `InitializeKubo`.

Indices `0x0160`-`0x016B` are the modules' class tables, not DISK MENU
entries. The HD-AE5000 is module 0x0A, so its class table is `0x016A`. See
[UI Framework — Module numbers]({{ site.baseurl }}/ui-framework/#module-numbers-and-the-object-table).

### Complete Handler Table

`HDAE5000_Handler_Registration` (0x280020) registers eleven object tables and
then one title. The class ids, procs and index scheme are those of the main
CPU's own `InitializeRoot` (module 0) and `InitializeHama` (module 9). The
HD-AE5000 is module **0x0A**, so every per-module index is kind + 0x0A:

| # | Index | Class id | Proc (`workspace[0x0E0A]` offset) | Count | Data | Contents |
|---|-------|----------|------|------|------|----------|
| 1 | 0x016A | 0x01600004 | `ClassProc` (0x0168) | 13 | 0x29C0AA | the module's 13 class definitions |
| 2 | 0x01CA | 0x0160000C | `ResEventProc` (0x013C) | 13 | 0x2397EA | `EV_*` event names (events `0x01CA000n`) |
| 3 | 0x01EA | 0x0160000D | `ResMethodProc` (0x0140) | 18 | 0x239824 | `MT_*` method names |
| 4 | 0x012A | 0x01600002 | `ApFunctionProc` (0x0248) | 69 (0x45) | 0x23952A | ApFunction table: code addresses |
| 5 | 0x042A | 0x01600002 | `ApFunctionProc` (0x0248) | 69 (0x45) | 0x239642 | … their names |
| 6 | 0x010A | 0x01600001 | `FunctionProc` (0x0244) | 13 (0x0D) | 0x239872 | Function table: the UI class procedures |
| 7 | 0x040A | 0x01600001 | `FunctionProc` (0x0244) | 13 (0x0D) | 0x2398AA | … their names |
| 8 | 0x014A | 0x01600003 | `MainFunctionProc` (0x024C) | 14 (0x0E) | 0x239FD2 | MainFunction table: screen procedures |
| 9 | 0x044A | 0x01600003 | `MainFunctionProc` (0x024C) | 14 (0x0E) | 0x23A00E | … their names |
| 10 | 0x007F | 0x01600010 | `ViewableProc` (0x0280) | 789 (0x315) | 0x2A5D2C | the UI objects (widget records) of Viewable table 0x7F |
| 11 | 0x037F | 0x0160000F | `ResNameProc` (0x0148) | 789 (0x315) | 0x2A6984 | … their names |

The counts of tables 2 and 3 are read at run time from the `.data` image
(`HDAE5000_EventName_Count`, RAM `0x239822`, and `HDAE5000_MessageName_Count`,
RAM `0x239870`). Tables 0x7F and 0x37F replace the
empty tables `InitializeHama` registers at the same indices.

The final call is **`RegisterTitle`** (`workspace[0x0E0A][0x0270]`):
title 0x7F, `XBC = 0x014A0000` (entry 0 of the module's MainFunction table),
`XDE = 0x007F01EE` (UI object `IV_HDDMENU`, the title's view), name `"TT_HDDEXT"`
(ROM `0x2A849A`), module 0x0A. `InitializeHama` registers title 0x7F with the
same name as module 9, and the HD-AE5000 overrides it. Title 0x7F is the one
the HD-AE5000 later requests with event `0x01C00016` / `0x01C00015` (see
[Event Codes]({{ site.baseurl }}/event-codes/#mode-and-title-requests-0x01c00014-0x01c00016)).

Earlier versions of this table called the class ids "port addresses" and
described the tables as "UI config strings", "RAM data area A/B", "Init data",
"Serial data", "Parallel data" and "ROM graphics". Those descriptions were
wrong. A class id `0x016000nn` is entry *nn* of the root's class table; the
[UI Framework page]({{ site.baseurl }}/ui-framework/#module-numbers-and-the-object-table)
explains the scheme. Source: `HDAE5000_Handler_Registration`'s header in
`hdae5000/hd-ae5000_v2_06i.s` and the hdae lane report.

### Data Record Table (Handler 0x016A): the Module's Classes

The table registered at `0x016A` (`0x29C0AA`, `HDAE5000_RECORD_TABLE`) holds the
HD-AE5000's **13 class definitions**, 24 bytes each. The layout is the one every
module's classes use. Its field names are the firmware's own, from the root class
`Class` (see [UI Framework — The class system describes itself]({{ site.baseurl }}/ui-framework/#the-class-system-describes-itself)):

```
Class definition (24 bytes):
  +0x00  4 bytes  proc      the class procedure (called for every event)
  +0x04  4 bytes  parent    class id of the parent class
  +0x08  2 bytes  allsize   size of an instance record, inherited fields included
  +0x0A  2 bytes  selfsize  bytes this class adds
  +0x0C  4 bytes  name      -> class name
  +0x10  4 bytes  propdata  -> one type letter per own field
  +0x14  4 bytes  propname  -> the own fields' names (a RAM pointer here: the list
                               lives in the .data image copied to 0x23952A)
```

| Rec | Name | proc | parent (class) | allsize | selfsize | name | propdata | propname |
|-----|------|------|----------------|---------|----------|------|----------|----------|
| 0 | SelectList | 0x2807D9 | 0x01600011 `VwBox` | 0x3C | 0x20 | 0x29D972 | 0x29D966 | 0x23975A |
| 1 | DbMemoCl | 0x28122A | 0x01600046 `DbMemo` | 0x1A | 0x04 | 0x29D95C | 0x29D958 | 0x23978A |
| 2 | TtlScreenR | 0x280489 | 0x01600034 `TtlScreen` | 0x2A | 0x00 | 0x29D94C | 0x29D94A | 0x239796 |
| 3 | AcHddNamingWindow | 0x281411 | 0x01600035 `Window` | 0x24 | 0x00 | 0x29D938 | 0x29D936 | 0x23979A |
| 4 | IvHddNaming | 0x282681 | 0x01600027 `PsInvisibleBox` | 0x1A | 0x04 | 0x29D92A | 0x29D928 | 0x23979E |
| **5** | **HDTitleMenu** | **0x2827A8** | **0x0160001D `AcTitleMenu`** | **0x36** | **0x00** | **0x29D91C** | **0x29D91A** | **0x2397A6** |
| 6 | TtlScreenR2 | 0x280567 | 0x01600034 `TtlScreen` | 0x2A | 0x00 | 0x29D90E | 0x29D90C | 0x2397AA |
| 7 | TtlScreenR3 | 0x280645 | 0x01600034 `TtlScreen` | 0x2A | 0x00 | 0x29D900 | 0x29D8FE | 0x2397AE |
| 8 | AcWindowPage1 | 0x28043C | 0x01600025 `AcWindowPage` | 0x24 | 0x00 | 0x29D8F0 | 0x29D8EE | 0x2397B2 |
| 9 | IvScreenR2 | 0x280723 | 0x0160006A `IvScreen` | 0x22 | 0x00 | 0x29D8E2 | 0x29D8E0 | 0x2397B6 |
| 10 | AcLanguageText1 | 0x28B554 | 0x01600066 `AcLanguageText` | 0x2A | 0x00 | 0x29D8D0 | 0x29D8CE | 0x2397BA |
| 11 | LyricBox | 0x28CD08 | 0x01600011 `VwBox` | 0x2E | 0x12 | 0x29D8C4 | 0x29D8BC | 0x2397BE |
| 12 | FDFileSelect | 0x28E61B | 0x01600027 `PsInvisibleBox` | 0x20 | 0x0A | 0x29D8AE | 0x29D8AA | 0x2397DA |

The parent names are the root classes at those indices (0x11 = 17 `VwBox`,
0x1D = 29 `AcTitleMenu`, 0x34 = 52 `TtlScreen`, and so on), printed by
`python3 scripts/analysis/nakarest_objtab_map.py v10 --classes` in the disassembly
repo. **All 13 HD-AE5000 classes satisfy the firmware's size rule,
`allsize = parent.allsize + selfsize`.** For example, `SelectList` is
`VwBox` 28 + 0x20 = 60 = 0x3C, `LyricBox` is 28 + 0x12 = 46 = 0x2E, and
`FDFileSelect` is `PsInvisibleBox` 22 + 0x0A = 32 = 0x20. The classes that add
nothing (selfsize 0) have exactly their parent's size. The HD-AE5000's
init-data header reports that the signature string's length equals the
parameter count for all 13 records. The letter sizes solved on the main CPU
also give each class's `selfsize` exactly, for all 13. For example,
`LyricBox`'s `"mc^^c^"` is 4+4+2+2+4+2 = 18 = 0x12, `FDFileSelect`'s `"Gnn"` is
2+4+4 = 10 and `SelectList`'s `"c^ksAAnGGmA"` is 32 = 0x20. Check (in
`kn5000-roms-disasm`):

```python
import struct, importlib.util
spec = importlib.util.spec_from_file_location('m', 'scripts/analysis/nakarest_objtab_map.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)   # for SIG_SIZE
d = open('original_ROMs/hd-ae5000_v2_06i.ic4', 'rb').read(); B = 0x280000
for i in range(13):
    _, parent, alls, selfs, name, sig, _ = struct.unpack_from('<IIHHIII', d, 0x29C0AA - B + 24 * i)
    sg = d[sig - B:].split(b'\0')[0].decode('latin-1')
    print(d[name - B:].split(b'\0')[0].decode(), sg, sum(m.SIG_SIZE[c] for c in sg) == selfs)
```

This replaces the older reading on this page, which took +0x04 for a "next
handler ID" chaining to a "Root module handler", +0x08 for a "config size" and
+0x0A for "config flags". `InheritedProc` does follow the +0x04 link, because
it is the **parent class**. That is how an event a class does not handle
reaches the root class's behaviour. `HDTitleMenu` is a subclass of the root's
`AcTitleMenu`, the class of the DISK MENU items that lead to a title (see
below).

### DISK MENU Slot Registration (workspace[0x0E0A][0x02C4])

After registering its tables, Boot_Init calls `workspace[0x0E0A][0x02C4]` with
`0x00600002`. The firmware's name for that function is **`GetViewInstance`**. It
returns XHL = the instance record of view object `0x00600002`, which is entry 2
of Viewable table 0x60. The HD-AE5000 then writes two fields of that record:

| Offset | Size | Value (HDAE5000) | Value (Mines) | Field (class `AcTitleMenu`) |
|--------|------|-------------------|---------------|-------------|
| +0x00 | 4 | `0x016A0005` | `0x016A0000` | `class`: the record's class id |
| +0x2A | 4 | `0x2F8DCE` → "HD-AE5000" | MENU_NAME → "Mines Game" | `str`: the item's text |
| +0x2E | 4 | *(left as is: `0x01A0007F`)* | — | `title`: the title the item opens |
| +0x32 | 4 | *(left as is: `0x83`)* | 176 | `icon` |

**What the record is.** Viewable table 0x60 is registered by `InitializeCheap`
(`RegObjTabl NAKA_CLASS_Viewable, ViewableProc, 0x4a, Cheap_ViewableTable_060, 0x60`, table at 0xEA67B6, in
`v10/maincpu/file_io/medley.s`) and holds the DISK MENU screen. Entry 0 is a
`TtlScreen`. Entries 1, 3 and 4 are ROM records of class `AcTitleMenu`:
"STYLE CONVERT" (title 0x10), "PREFERENCES" (title 0x7E) and "SAVE" (title
0x65). **Entry 2 is not in ROM.** Its table entry is `0x0003EEEE`, a RAM
address inside the [work-RAM image]({{ site.baseurl }}/memory-map/#work-ram-initial-image),
so its initial contents are the ROM bytes at `0xEED8C8 + (0x3EEEE - 0x3D524)` =
`0xEEF292`. Decoded with the class model, they are an `AcTitleMenu` whose
`str` is **"HARD DISK MAIN MENU"**, `title` is **`0x01A0007F`**, `icon` is
0x83 and rectangle is (163, 198)-(311, 223). The firmware ships the expansion's
DISK MENU entry pre-built, in RAM where an expansion can rewrite it, and already
pointing at title 0x7F (`TT_HDDEXT`). The HD-AE5000 re-registers that title
with its own view and re-classes the item as its own `HDTitleMenu`.

The ROM bytes can be checked with this snippet (run in `kn5000-roms-disasm`):

```python
import struct
d = open('original_ROMs/kn5000_v10_program.rom', 'rb').read(); B = 0xE00000
p = struct.unpack_from('<I', d, 0xEA67B6 - B + 4 * 2)[0]            # 0x0003EEEE
r = d[0xEED8C8 + (p - 0x3D524) - B:][:54]                           # image 1
cls, s, title, icon = struct.unpack_from('<I', r, 0)[0], *struct.unpack_from('<III', r, 42)
print(hex(p), hex(cls), d[s - B:s - B + 20].split(b'\0')[0], hex(title), hex(icon))
# 0x3eeee 0x160001d b'HARD DISK MAIN MENU' 0x1a0007f 0x83
```

This reading comes from combining the hdae lane's function names with the
nakarest class model. It explains why writing `+0x00` "links the menu entry to a
handler": the first word of every widget record is its class id. It also
explains why `+0x32` is an icon id: `AcTitleMenu`'s `icon` field sits at +50.
Nobody has yet traced whether the item's `flag` (0 here, 8 in the ROM items)
controls its visibility.

The `slot+0x2A` field was earlier **confirmed** as a display-name pointer:
address `0x2F8DCE` in the HDAE5000 ROM holds the null-terminated string
"HD-AE5000".

## Display Ownership Model

Understanding how the firmware manages the LCD display is critical for any homebrew project that wants to render graphics.

### Firmware Display Architecture

The KN5000 display is **NOT driven by a vertical blank interrupt (VBI)**. Instead, display updates happen in the firmware's main event loop at `MainLoop`:

```
Main Event Loop (MainLoop)
    |
    +-- Control Panel Poll
    +-- Display Update         <-- firmware draws its UI here
    +-- MIDI Processing
    +-- FDC Handler
    +-- Frame_Handler call     <-- extension ROM runs AFTER firmware drawing
    +-- Audio Sync
    |
    (loop)
```

**Key implication:** The Frame_Handler is called **after** the firmware has already drawn its screen content. Any VRAM writes made by the extension ROM will be visible briefly, then overwritten by the firmware on the next loop iteration.

### Step-Record Display Flag (0x0D53, bit 3)

Address `0x0D53` is a firmware flag byte in the TMP94C241F's internal RAM. Bit 3 is set on the path of `SqStep_SetupCursorTrack` (the second half of `SqStep_InitOnEnter`, which runs when the sequencer's step-record screen is entered) and cleared by `SqStep_RestoreOnLeave` when that screen is left. It is not a display-disable switch.

#### Firmware mechanism

The firmware tests this bit at eight places (five in `display/scoop_display.s`, three in `sequencer/accompaniment_engine.s`). The main loop's display update gate is one of them:

```asm
; At 0xEF77DF — main display update gate:
BIT 3, (0D53h)
JRL Z, skip               ; If bit 3 CLEAR, skip display update entirely
CALL Display_ResetDirtyFlags
; ... dispatches to display handler based on state in (0D65h) ...
CALL Display_UpdateDirtyRegions
```

Note the polarity. `JRL Z` jumps when bit 3 is **clear**, so this update runs only while bit 3 is **set**. The same `BIT 3` / `JR Z` pattern holds at the other seven sites, among them `SysEx_ControllerBitCheck` at 0xEFAA40 and the `AccPedal_Sustain_CheckPlay` / `AccPedal_Distribute_CheckRecord` tests at 0xF59C11 / 0xF59D65. All of them belong to the sequencer's step-record and accompaniment code, and `SqStep_RestoreOnLeave` clears the bit when the step-record screen is left.

The dispatch indexes the step-record display mode at `0x0D65`.

#### When is it needed?

In practice, Mines sets bit 3 when the game is activated and writes the saved byte back when it exits (Mines `platforms/kn5000/startup.s`, since commit b865da2). The App Loader does the same. Given the polarity above, doing so is not known to stop the firmware's drawing, and what it changes on screen has not been measured. What both programs rely on is timing. The firmware's display work runs earlier in each main-loop pass, and then `Frame_Handler` runs and the game redraws its screen over it. There is no VBI-driven refresh.

### VGA Controller Details

The KN5000 uses an **MN89304** LCD controller, which is VGA-compatible with some differences:

| Property | Standard VGA | MN89304 (KN5000) |
|----------|-------------|-------------------|
| DAC resolution | 6-bit (0-63) | **4-bit (0-15)** |
| Palette format | 18-bit RGB | **12-bit RGB** |
| Row pitch | configurable | `svga_device::offset() << 3` (8x multiplier) |
| CRTC start | standard | standard |

#### VGA Register Map

| Register | CPU Address | Description |
|----------|-------------|-------------|
| DAC Mask | 0x1703C6 | Palette mask register |
| DAC Write Index | 0x1703C8 | Select palette entry to write |
| DAC Data | 0x1703C9 | Write R, G, B values sequentially |
| CRTC Index | 0x1703D4 | Select CRTC register |
| CRTC Data | 0x1703D5 | Read/write CRTC register value |

#### Palette Format

The MN89304 uses a **4-bit RAMDAC** (`pal4bit()` in MAME). Only the lower 4 bits of each color component are used:

```c
// Writing a palette entry
*VGA_DAC_WRITE_INDEX = palette_index;
*VGA_DAC_DATA = red >> 2;    // Convert 6-bit VGA to 4-bit
*VGA_DAC_DATA = green >> 2;
*VGA_DAC_DATA = blue >> 2;
```

The original HDAE5000 firmware shifts RGB values right by 4 bits (`>> 4`) from 8-bit source data. If your palette data is already in 6-bit VGA format (0-63), shift right by 2 (`>> 2`) to get 4-bit values.

#### CRTC Start Address

The CRTC start address (registers 0x0C high, 0x0D low) determines which VRAM address appears at the top-left of the screen. The firmware initializes this to `0x0000` during VGA setup, meaning VRAM address `0x1A0000` maps to pixel (0,0).

The MN89304 applies an additional 8x multiplier to the row offset calculation (`mn89304::offset()` overrides `svga_device::offset()` and left-shifts by 3). This affects scrolling but not the basic framebuffer start address.

### VRAM Layout

| Property | Value |
|----------|-------|
| Base address | 0x1A0000 |
| Size | 256KB (0x1A0000-0x1DFFFF) |
| Active display | 76,800 bytes (320 x 240) |
| Pixel format | 8-bit indexed color |
| Row stride | 320 bytes |

VRAM is linear and row-major. Pixel at screen position (x, y) is at VRAM address `0x1A0000 + y * 320 + x`.

### Experimental Observations

Testing with MAME confirmed:
- **VRAM writes from extension ROM code work correctly** -- both assembly and C code can write to the 0x1A0000 framebuffer
- **Game rendering is fully working** -- the Mines game draws a complete minesweeper board (palette, tiles, grid) to the KN5000 LCD
- **Critical pitfall:** The LLVM backend's for-loop bug (#11) caused the VRAM clear to only execute one iteration, making it appear that VRAM writes didn't work when in fact only 4 bytes out of 76,800 were being cleared

### Headless MAME Testing

For automated testing without a display (CI environments, SSH sessions):

```bash
QT_QPA_PLATFORM=offscreen mame kn5000 -rompath rompath \
    -extension hdae5000 -video none -sound none \
    -skip_gameinfo -autoboot_script test.lua
```

MAME Lua scripts can read/write VRAM and CPU memory via `cpu.spaces["program"]:read_u8(addr)` / `write_u8(addr, val)`, take screenshots via `manager.machine.video:snapshot()`, and exit via `manager.machine:exit()`.

## Object Dispatch System

The firmware implements an **object-oriented dispatch system** that manages all DISK MENU interactions. Understanding this system is essential for proper DISK MENU integration.

### Firmware Symbol Names

The main CPU firmware symbol table reveals the real names for these functions:

| Address | Symbol Name | Previous Name | Purpose |
|---------|-------------|---------------|---------|
| 0xFA9660 | **SendEvent** | "FA9660" | Main event dispatch entry point |
| 0xFA44E2 | **ClassProc** | "Layer 1 handler" | UI event handler (shared by all DISK MENU modules) |
| 0xFA3D85 | **ObjectProc** | "Layer 2 dispatch" | Object lifecycle event handler |
| 0xFA4409 | **InheritedProc** | "Layer 3 chain dispatch" | Handler chain traversal |
| 0xFA42FB | **RegisterObjectTable** | "workspace[0x0E0A][0x00E4]" | Register handler in object table |
| 0xFA431A | **RegisterObject** | (unnamed) | Register individual object entry |
| 0xFA43B3 | **UnRegisterObject** | (unnamed) | Remove object entry |
| 0xFA9752 | **PostEvent** | (was confused with `ApPostEvent`) | Queue event for asynchronous dispatch (`workspace[0x0E0A][0x0104]`) |
| 0xFA9D58 | **ApPostEvent** | "Display callback" | Queue event into the same ring; yields while the queue is full (`workspace[0x0E0A][0x0124]`) |
| 0xFA9868 | **DeleteEvent** | (unnamed) | Remove queued events matching an object and event (`workspace[0x0E0A][0x0534]`) |

### Architecture Overview

```
Object Table (0x027ED2)                  Data Record Table
 14-byte entries, max 1120               24-byte records per sub-object
┌──────────────────────────────┐       ┌────────────────────────────────┐
│ +0x00: Class id (4)          │       │ +0x00: proc (4)                │
│ +0x04: Proc (4)              │       │ +0x04: parent class id (4)     │
│ +0x08: Count (2)             │       │ +0x08: allsize (2)             │
│ +0x0A: Data pointer (4) ─────┼──────>│ +0x0A: selfsize (2)            │
└──────────────────────────────┘       │ +0x0C: name (4)                │
                                       │ +0x10: propdata (4)            │
Global State (saved/restored           │ +0x14: propname (4)            │
 per dispatch call):                   └────────────────────────────────┘
 (the right-hand box is a class definition, as registered by a ClassProc table)
  0x02BC14: Current object identity (SetCurrentTarget/GetCurrentTarget)
  0x02BC18-20: Root object/event/param (SetRootObject/GetRootObject etc.)
  0x02BC24-2C: Focus object/event/param (GetFocusObject/GetFocusEvent etc.)
  (in the maincpu source: ROOT_OBJECT / ROOT_EVENT / ROOT_PARAM and FOCUS_OBJECT / FOCUS_EVENT / FOCUS_PARAM)
```

### Object Identifiers

Object IDs combine an object table index with a sub-object index:

```
  0x016A0005
  ├── 0x016A  = Object table index (handler ID registered via RegisterObjectTable)
  └── 0x0005  = Sub-object index (record number in data table)
```

The `slot+0x00` field in the DISK MENU slot stores this combined identifier, linking the menu entry to a specific sub-object (record) in the handler's data table.

### SendEvent (0xFA9660) — Main Event Dispatch

`SendEvent` is the firmware's synchronous event dispatch. Every request to an object goes through this function:

```
SendEvent(XWA=object_id, XBC=request_code, XDE=param):
  1. Save current focus state (0x02BC24-2C) to stack
  2. Extract handler_index = (object_id >> 16) & 0xFFF
  3. Look up handler function from object_table[handler_index * 14 + 4]
  4. Call handler(object_id, 0x01E00000, 0) → "identity" query
  5. Set 0x02BC14 = identity result (via handler function)
  6. Extract sub_index from identity result
  7. Look up data record table from object_table[handler_index * 14 + 0x0A]
  8. Read implementation function from record[sub_index * 24 + 0x00]
  9. Call record_function(object_id, request_code, param)
  10. Restore focus state from stack
  11. Return result in XHL
```

The class query (step 4) goes to the table's proc: `ViewableProc` for the DISK MENU view `0x00600002`, which returns the class id the view record holds (`0x016A0005` for the HD-AE5000's item). Only for a class object does `ClassProc` return XWA unchanged.

### PostEvent (0xFA9752) — Asynchronous Event Queue

`PostEvent` (previously called "ApPostEvent") queues events for later dispatch:

```asm
PostEvent:                    ; 0xFA9752
    ; Allocate 8 bytes on stack, save registers
    ; Acquire lock (CALL 0xEF1EA7 with WA=4)
    ; Read queue state:
    ;   BC = read index from (0x02EC34)
    ;   DE = write index from (0x02EC36)
    ; Check for queue full (WA = DE + 1, compare with BC)
    ; If full: release lock, spin forever (deadlock!)
    ;
    ; Write 12-byte event entry to queue:
    ;   Queue base: 0x02BC34
    ;   Entry address: 0x02BC34 + (write_index * 12)
    ;   +0x00: XIZ (target object ID)
    ;   +0x04: XBC (event code)
    ;   +0x08: XDE (parameter)
    ;
    ; Advance write index (wrap at 0x03FF)
    ; Increment event counter at 0x02F840
    ; Release locks
    RET
```

The event queue is a ring buffer with 1,024 entries (indices 0x0000-0x03FF), each 12 bytes. Events are dequeued by the main loop and dispatched via `SendEvent`.

### Request Code Dispatch (Three Layers)

`ClassProc` (shared by all DISK MENU modules) dispatches requests through three layers:

> **Correction.** `SendEvent` asks the target's table proc (`ViewableProc` for a view such as `0x00600002`, `ClassProc` for a class object) only for the class id (`EVT_GET_CLASS_SP`, 0x01E00000). For a view, the answer is the class id that the view record holds, here `0x016A0005`. `SendEvent` then calls that class's `proc` (class record +0x00) with the real request. `ClassProc`, `ObjectProc` and `InheritedProc` see a real request only through delegation. A class proc passes on what it does not handle with `InheritedProc`, which follows the class record's `parent` field (+0x04). `ObjectProc` is the proc of the root class `Object`, and the base procs (`ViewableProc`, `ClassProc`) also call it directly for codes they do not handle. The tree below lists what each proc does with the codes it handles, not the order in which a request reaches them.

```
ClassProc (0xFA44E2): UI event handler
  ├── 0x01E00000-0x01E00007: Jump table via 0xEAA8F8
  │   ├── Case 0 (0x01E00000): Return XWA (identity)
  │   ├── Case 1 (0x01E00001): Return *(XHL)
  │   ├── Case 2 (0x01E00002): Return *(XIZ)
  │   ├── Case 3 (0x01E00003): Return the WORD at +0x08 (allsize)
  │   ├── Case 4-7: MT_CheckClassSp, MT_GetPropStringEx, MT_GetPropCountSp, MT_GetPropNameSp
  │   Via helper functions:
  │     ClassProc_Event_LoadFromWA   (0xFA4598)
  │     ClassProc_Event_LoadFromHL   (0xFA459D)
  │     ClassProc_Event_LoadFromIZ   (0xFA45A2)
  │     ClassProc_OnGetInstanceSizeSp (case 3)
  ├── 0x01E0000D: MT_GetPropDataSp (entry #n of an ID-typed property's domain)
  ├── 0x01E0000E: MT_GetPropDataCountSp (size of that domain)
  ├── 0x01E0000F: MT_GetInstance (pointer to the instance record)
  ├── 0x01E00015: MT_GetName (record+12 for a class, via ClassProc_Event_LoadFromOffset)
  └── Default (including 0x01E0009C): → ObjectProc
                                         │
ObjectProc (0xFA3D85): Lifecycle events
  ├── Allocates 0x90 bytes stack frame
  ├── Extracts handler index, looks up data records
  ├── Calls handler identity query first
  ├── 0x01E00010-0x01E00023: 20 cases via jump table at 0xEAA8A4
  │   (setters, init/teardown, string operations)
  └── Out of range (including 0x01E0009C): → InheritedProc
                                               │
InheritedProc (0xFA4409): Handler chain traversal
  ├── Read current target identity from 0x02BC14
  ├── Extract handler_index and sub_index
  ├── Look up data record table for current handler
  ├── Read "next" handler ID from record[sub_index * 24 + 0x04]
  ├── If next ≠ 0xFFFFFFFF:
  │     Set 0x02BC14 = next handler ID
  │     Look up next handler's record table
  │     Call next handler's implementation function
  │     Restore 0x02BC14 to original value
  │     Return result
  └── If next = 0xFFFFFFFF: return 0
```

### HDAE5000 Handler Behavior (Record 5: "HDTitleMenu")

The HDAE5000's DISK MENU handler function at `0x2827A8` (Record 5) is minimal:

```
HDAE5000_HDTitleMenuProc (0x2827A8)(XWA=object, XBC=request, XDE=param):
  if (request == 0x01C0000F):
    call workspace[0x0E0A][0x00DC]  // InheritedProc: the parent class (AcTitleMenu) first
    SendEvent(0x007F01ED, 0x01C0000D, 0)  // workspace[0x0E0A][0x0100], object HD_MENU_BMP
    return 0
  else:
    jp workspace[0x0E0A][0x00DC]    // InheritedProc: let AcTitleMenu handle it
```

**The "default handler" at `workspace[0x0E0A][0x00DC]` is `InheritedProc`.**
It runs the parent class's behaviour, here `AcTitleMenu`'s, and that manages
the DISK MENU item for most requests. These include the panel-switch event `0x01C00007` (`EVT_SW_IN`), on which `AcTitleMenuProc` sends `EVT_CHANGE_TITLE` (0x01C00015) to the current target (`SendEvent` with object `0xFFFFFFFF`) with the item's `title` field (+0x2E). The
HD-AE5000 only intercepts `0x01C0000F`. It sends `0x01C0000D` synchronously
(`SendEvent`, not a post) to its own UI object `HD_MENU_BMP` (`0x007F01ED`,
entry 0x1ED of Viewable table 0x7F).

## DISK MENU Activation Mechanism

When the user selects a DISK MENU entry, the firmware does not directly call the extension ROM. Instead, it uses the event dispatch system to activate the registered handler.

### Activation Trigger

The main firmware routine `FileIO_DiskRemoved` (0xF8B1DF) is the one place that
posts `0x01E0009C` to the expansion's DISK MENU item, and it does not activate
anything:

```asm
; FileIO_DiskRemoved, after resetting the medley and progress state:
CALL  Xapr_GetPresentFlag           ; Read XAPR detection flag from (0x03DD04)
CP    L, 0
RET   NZ                     ; Extension present: return at once

; No extension -- hide the expansion's DISK MENU item
LD    XWA, 00600002h         ; View object 0x00600002 (the DISK MENU's expansion item)
LD    XBC, 01E0009Ch         ; EVT_SET_VISIBLE (MT_SetVisible)
LD    XDE, 0                 ; Parameter 0: hide
CALL  ApPostEvent            ; Queue event for dispatch
```

`0x01E0009C` is `MT_SetVisible`, not an activation event. With an extension ROM
installed, nothing posts it to the item. The activation itself is `AcTitleMenuProc`'s
answer to the panel-switch event `0x01C00007` (`EVT_SW_IN`): it opens the item's
`title` (+0x2E) by sending `EVT_CHANGE_TITLE` (`SendEvent`, to the current target
`0xFFFFFFFF`; see [HDAE5000 Handler Behavior](#hdae5000-handler-behavior-record-5-hdtitlemenu)).

### What Mines Needs for DISK MENU Activation

Based on the complete dispatch analysis, the Mines project needs:

1. **Register handler `0x016A`** via `RegisterObjectTable` (workspace[0x0E0A][0x00E4]) with:
   - Class id: `0x01600004` (a Class table)
   - Proc: `ClassProc` (via workspace[0x0E0A][0x0168], resolves to 0xFA44E2)
   - Count: number of 24-byte class definitions in the table (e.g., 1)
   - Data pointer: address of the class-definition table

2. **Provide a class-definition table** with at least one 24-byte class:
   - `+0x00` `proc`: our handler function
   - `+0x04` `parent`: the parent class id. The HD-AE5000 uses `0x0160001D` (`AcTitleMenu`), whose behaviour `InheritedProc` runs for everything the proc does not handle
   - `+0x08` `allsize` / `+0x0A` `selfsize`: the parent's size (54 for `AcTitleMenu`) and 0, unless the class adds fields
   - `+0x0C`-`+0x14` `name` / `propdata` / `propname`: name string, type letters (`""` for none), and a name list ending in `""`

3. **Set `slot+0x00`** (the `class` field of view object `0x00600002`) to `0x016A0005` (class 5 of table 0x016A, matching the HD-AE5000) — or `0x016A0000` if the class table has one entry

4. **Implement a handler function** that:
   - Intercepts `0x01C00008` (`EVT_SW_ON`, the panel-switch press that selects the item) to set the `GAME_ACTIVE` flag, and **skips delegation** for it. (Mines and the App Loader also intercept `0x01E0009C`, but that is `MT_SetVisible`, not an activation event.)
   - Delegates all other requests to `workspace[0x0E0A][0x00DC]` (`InheritedProc`, i.e. the parent class)
   - Optionally intercepts `0x01C0000F` (`EVT_PARA_DRAW`, draw the item's text) to draw extra content after the parent class has drawn the item. The original HD-AE5000 uses it to send `EVT_DRAW` (0x01C0000D) to its `HD_MENU_BMP` icon view.

### Object System Initialization

The firmware initializes the object table at startup via `InitializeObjectTable` (0xFA40B3). This function:

1. Clears all 1,120 entries in the object table (14 bytes each)
2. Initializes internal dispatch tables (0x0328FC and 0x032ABC)
3. Registers built-in system handlers (IDs 0x0260, 0x0180, 0x01A0, 0x0000-0x00FF, 0x0300-0x03FF)
4. Calls 31 `Initialize*` functions (one per built-in module): `InitializeMurai`, `InitializeToshi`, `InitializeEast`, `InitializeSuna`, `InitializeCheap`, `InitializeScoop`, `InitializeYoko`, `InitializeKubo`, `InitializeHama`, `InitializeKSS`, `InitializeNaka`, and `InitializeUser12`-`InitializeUser31`
5. Each `Initialize*` function calls `RegisterObjectTable` with that module's handlers

The HDAE5000's `Handler_Registration` runs later (during `Boot_Init`), filling the table entry for handler `0x016A`, which no built-in module registers: module 0x0A's `InitializeKSS` is a bare `ret`, so the entry still holds what `InitializeObjectTable` cleared it to.

### Simplified Activation (Mines Approach)

The Mines project demonstrates that full participation in the object dispatch system is not required. Instead of implementing all 13 sub-objects and chaining to the Root module, the Mines handler:

1. Registers handler `0x016A` with a minimal 1-record data table
2. Sets the record's implementation function to `Mines_Handler`
3. `Mines_Handler` intercepts the activation event to set a `GAME_ACTIVE` flag in extension RAM
4. All other requests are delegated to `workspace[0x0E0A][0x00DC]` (`InheritedProc`)
5. Frame_Handler checks `GAME_ACTIVE` and branches into the C game code when set

**Key discovery:** When the user selects a DISK MENU entry via a physical button press, the firmware dispatches event code **`0x01C00008`** (not `0x01E0009C`) to the handler's record function. `0x01E0009C` is `MT_SetVisible`, not an activation event. Its one sender to this item, `FileIO_DiskRemoved`, hides the item, and only when no extension ROM is present. Intercepting `0x01C00008` is enough.

When activation is intercepted, the handler should **skip delegation** to the default handler — otherwise the default handler shows its own UI (e.g., "FD SAVE/LOAD TEST") which would interfere with the game.

The full sequence of events received by the handler during DISK MENU interaction:

| Phase | Events (in order) | Description |
|-------|------------------|-------------|
| Menu opens | `0x01C00001`, `0x01E00014`, `0x01C0000F` | Menu display and initialization |
| Entry selected | `0x01C00008`, `0x01C00039`, `0x01C00002`, `0x01E00014` | Button press, selection, redraw |

See the [Event Codes Reference]({{ site.baseurl }}/event-codes/) for a complete table of known event codes.

### Open Questions

- Does anything besides `InheritedProc` read `allsize`/`selfsize` of a class that re-classes an existing record (as `HDTitleMenu` re-classes view object `0x00600002`)? A class with parent `0xFFFFFFFF` has no inherited behaviour; whether the view system tolerates that for a DISK MENU item is untested.

## Control Panel Input

The KN5000 control panel communicates with the main CPU via SC1 synchronous serial at 250 kHz. The firmware's interrupt-driven state machine continuously polls the panel and stores button bitmaps in RAM arrays. Extension ROMs read these arrays directly — no SC1 serial access needed, no interference with firmware operation.

### Reading Button State from Firmware RAM

The firmware maintains two button state arrays in internal RAM, one per panel half:

| Array | Address | Description |
|-------|---------|-------------|
| Right panel | `0x8E4A` + segment | Segments 0-10, 1 byte each |
| Left panel | `0x8E5A` + segment | Segments 0-10, 1 byte each |

Each byte is a bitmap of pressed buttons in that segment. Read them with simple memory loads:

```c
/* Read right panel segment 4 (direction buttons) */
uint8_t right_seg4 = *(volatile uint8_t *)0x8E4E;  /* 0x8E4A + 4 */

if (right_seg4 & 0x02)  /* bit 1 */ { /* UP pressed */ }
if (right_seg4 & 0x10)  /* bit 4 */ { /* LEFT pressed */ }
if (right_seg4 & 0x20)  /* bit 5 */ { /* DOWN pressed */ }
if (right_seg4 & 0x40)  /* bit 6 */ { /* RIGHT pressed */ }
```

**Edge detection:** Button state is level-based (1 = currently held). For single-press events, track previous state and detect rising edges:

```c
static uint32_t prev_buttons = 0;
uint32_t buttons = /* ... read current state ... */;
uint32_t pressed = buttons & ~prev_buttons;  /* newly pressed only */
prev_buttons = buttons;
```

**Event queue suppression:** While your extension has display control, suppress the firmware's control panel event queue to prevent it from acting on button presses meant for your code:

```c
/* Equalize read/write pointers to discard queued events */
*(volatile uint16_t *)0x8D9D = *(volatile uint16_t *)0x8D9F;   /* raw serial */
*(volatile uint16_t *)0x02F838 = *(volatile uint16_t *)0x02F83A; /* app events */
```

### Button Mapping

See the [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) page for the full serial protocol. For game-like input, useful buttons include:

| Button Group | Panel | Segment | Bit | Address | Suggested Use |
|-------------|-------|---------|-----|---------|---------------|
| Part Select: Right 2 | Right | 4 | 1 | `0x8E4E` | UP |
| Conductor: Left | Right | 4 | 4 | `0x8E4E` | LEFT |
| Conductor: Right 2 | Right | 4 | 5 | `0x8E4E` | DOWN |
| Conductor: Right 1 | Right | 4 | 6 | `0x8E4E` | RIGHT |
| Variation 4 | Left | 4 | 3 | `0x8E5E` | ACTION (open cell) |
| Variation 1 | Left | 4 | 0 | `0x8E5E` | SECONDARY (flag) |
| Exit | Left | 7 | 3 | `0x8E61` | QUIT |

### Cooperative Multitasking for Input

Button state arrays are updated by the firmware's SC1 interrupt handler during the firmware's main loop. Your extension must periodically yield control back to the firmware so it can process serial data and update the arrays.

The Mines game implements this with a `yield_to_firmware()` function (see the App Loader page's [Startup Assembly]({{ site.baseurl }}/app-loader/#startup-assembly), which reproduces it): the game saves its stack pointer, restores the firmware's stack, and returns from `Frame_Handler`. On the next frame, the firmware calls `Frame_Handler` again, which restores the game's stack and resumes execution. This cooperative multitasking ensures button state stays fresh.

## Audio

The KN5000's audio subsystem is managed entirely by the SubCPU (a second TMP94C241F). The main CPU sends it commands through a pair of memory-mapped latches at `0x140000` (see [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/)). Extension ROMs on the main CPU cannot directly control the tone generator or the DSP effects. MIDI is different: it runs on the main CPU's own serial channel 0 (see [MIDI Serial I/O]({{ site.baseurl }}/midi-serial-io/)).

### What Extensions Can Do

- **Trigger sounds via firmware callbacks:** The firmware's workspace contains callback pointers for triggering MIDI notes and sound effects. The two function tables reachable from the workspace (see [Workspace Pointer](#workspace-pointer)) name some candidates: the HD-AE5000 calls `HamaFn_sendCOMM` and `HamaFn_SwbtWr` in table 0x109. `HamaFn_sendCOMM` is the main CPU's block sender to the SubCPU (`sendCOMM`: A = command/channel id, BC = byte count, XDE = source; it sends 32-byte chunks through `InterCPU_Send_Data_Block`). `HamaFn_SwbtWr` has not been traced. Whether an extension can play notes through either has not been tried. This is unexplored territory — the exact API for triggering notes from extension code is not yet documented.
- **Write to the inter-CPU latch:** the latch at `0x140000` could in principle be used to send commands to the SubCPU, but the protocol is complex and interference with normal firmware operation is likely.

### What Extensions Cannot Do

- Directly program the tone generator (IC303, TC183C230002, at `0x100000` on the SubCPU's bus only; on the main CPU's bus that range holds the floppy controller and the inter-CPU latch)
- Directly program the DSP effect processors (MN19413 / uPD6383GF — connected via SubCPU GPIO, no main CPU access)
- Bypass the SubCPU for audio output

### Practical Guidance

For homebrew projects needing audio: the firmware continues running while your extension is active (via cooperative multitasking). The keyboard's normal sound engine remains operational — keys pressed on the physical keyboard will still produce sound. A future area of research is triggering specific notes or sound effects programmatically through the firmware's callback system.

See the [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) documentation for hardware details.

## LLVM TLCS-900 Backend Bugs

The LLVM TLCS-900 backend had several encoding and code generation bugs during development. **Status: All 11 bugs fixed or resolved (Feb 28, 2026). All C-level workarounds removed.**

### Assembler Encoding Bugs (Fixed)

### Bug 1: Direct Memory Load Prefix (Fixed)

**Instruction:** `ld reg, (addr)` (load from absolute address)

**Bug:** LLVM uses the `F2` prefix (F0/store group) instead of `E2` (E0/load group). In the F0 sub-opcode table, entry `0x26` is `LDA` (load address), not `LD` (load data) as in the E0 table.

**Former workaround:**
```asm
; Instead of: ld xwa, (0x200008)     -- BROKEN
ld   xhl, 0x200008                    ; load address into register
ld   xwa, (xhl)                       ; then dereference
```

### Bug 2: Immediate-to-Memory Store Sub-opcode (Fixed)

**Instruction:** `ld (addr), imm32` (store immediate to absolute address)

**Bug:** LLVM emits sub-opcode `0x08` in the F0 table, which does not exist on the TLCS-900. The hardware only supports `0x00` (byte immediate) and `0x02` (word immediate) -- there is no 32-bit immediate-to-memory store.

**Former workaround:**
```asm
; Instead of: ld (0x200000), 0x100   -- BROKEN
ld   xde, 0x200000                    ; load address
ld   xwa, 0x00000100                  ; load value
ld   (xde), xwa                       ; store via register-indirect
```

### Bug 3: Indirect CALL Sub-opcode (Fixed)

**Instruction:** `call (xreg)` (call function at address in register)

**Bug:** LLVM emits sub-opcode `0x1F` in the b0 table, which is undefined on the TLCS-900. The correct encoding for an unconditional call is `0xE8` (CALL T, where T = True = condition code 8). CALL entries occupy `0xE0-0xEF` in the b0 table, one per condition code.

**Former workaround:**
```asm
; Instead of: call (xix)             -- BROKEN (emits 0x1F)
.byte 0xB4, 0xE8                      ; B4 = XIX prefix, E8 = CALL T

; Register prefix bytes for indirect CALL:
;   B0 = XWA, B1 = XBC, B2 = XDE, B3 = XHL
;   B4 = XIX, B5 = XIY, B6 = XIZ, B7 = XSP
```

### Bug 4: JP Opcode (Fixed in LLVM Backend)

**Instruction:** `jp target` (unconditional jump)

**Bug:** LLVM originally encoded JP as opcode `0x1C`, which is actually `CALL I16` (call with 16-bit address) on the real hardware. This was fixed in the LLVM backend to use the correct opcode `0x1B` (JP I24, jump with 24-bit address).

### Bug 5: Register+Displacement Loads (Fixed)

**Instruction:** `ld xreg, (xreg + disp)` (load from register + displacement)

**Bug (fixed):** LLVM did not support encoding register+displacement loads. This was initially believed to be a hardware limitation, but the original HDAE5000 ROM uses instructions like `ld XWA, (XWA + 0x0E0A)` successfully -- confirming the hardware *does* support this addressing mode. Stores with displacement (`ld (xreg + disp), src`) work correctly in LLVM.

**Former workaround:**
```asm
; Instead of: ld xiz, (xiz + 0x0E0A)  -- NOT SUPPORTED
add  xiz, 0x0E0A                       ; modify register (destructive)
ld   xiz, (xiz)                        ; then dereference
```

### Bug 6: Source Memory Prefix Size Mismatch (Fixed)

**Instruction:** 8/16-bit register-indirect loads (`ld a, (xhl)`, `ld wa, (xhl)`)

**Bug:** LLVM always used the 32-bit prefix (0xA0-0xA7) regardless of operand size. The TLCS-900 requires 0x80-0x87 for byte, 0x90-0x97 for word, and 0xA0-0xA7 for long operations.

**Fix:** Corrected in LLVM backend. ISel now auto-materializes addresses for byte/word global loads (LD32ri + register-indirect). Displacement range restricted from +/-32767 to +/-127 (d8).

### Bug 7: INC/DEC Immediate Field Off-by-One (Fixed)

**Instruction:** `inc 1, xreg` / `dec 1, xreg`

**Bug:** LLVM encoded INC 1 with I3=0, which means increment by 8 (not 1) on the TLCS-900. The I3 convention is: 000=8, 001=1, 010=2, ..., 111=7. LLVM used `(Count - 1) & 7` instead of the correct `Count & 7`.

### Bug 8: 8-bit Register Encoding (Fixed)

**Instruction:** Any instruction using 8-bit registers (A, C, E, L)

**Bug:** `getRegEncoding()` returned the GPR_lo8 class index (A=0, C=1, E=2, L=3) instead of the hardware encoding (A=1, C=3, E=5, L=7). This caused 8-bit operations to use wrong registers. GPR_lo8 operands contain 32-bit parent registers (XWA/XBC/XDE/XHL), and the encoder used the parent's HWEncoding instead of the 8-bit sub-register's.

**C workaround (before fix):** Copy 32-bit values and mask, instead of using 8-bit register operations directly.

### Code Generation Bugs (Resolved)

### Bug 10: Register Allocation X/Y Swap in Inlined Functions — NOT REPRODUCIBLE

**Resolution (Feb 28, 2026):** The original analysis assumed XBC held the first parameter and XDE the second. Investigation of `TLCS900CallingConv.td` confirmed the calling convention has always been XDE-first (`CCAssignToReg<[XDE, XBC, XIX, XIY]>`). With the correct parameter mapping, the generated code was correct all along. The `__attribute__((noinline))` workaround has been removed.

### Bug 11: For-Loop with uint16_t Counter Exits After 1 Iteration — FIXED

**Fix (Feb 28, 2026):** originally commit `eba2fe6622ee`, kept on branch `tlcs900_backend_backup_20260418`. On `tlcs900_backend` it is part of the squashed commit `e90ba8f16b19` (2026-04-18). Root cause: `EXTS32` and `EXTZ32` were declared with `Defs=[SR]` in `TLCS900InstrInfo.td`, telling the compiler they set flags. On TLCS-900/H hardware, EXTS/EXTZ do NOT set any flags (confirmed via MAME's `op_EXTZLR` and `op_EXTSLR` implementations).

For `uint16_t` loops, clang generates a count-down pattern: `DEC` + `EXTZ` + `CP 0` + `JR NZ`. The `RedundantCmpElim` pass saw `EXTZ` (which it thought set Z) followed by `CP 0` + `JPcc NZ`, and removed the `CP` as "redundant." This left the `JR NZ` reading stale flags, causing immediate loop exit.

**Fix:** Moved `EXTS32`/`EXTZ32` out of the `Defs=[SR]` block and removed them from `isFlagSettingDef()` in `RedundantCmpElim`. Standard `for` loops with `uint16_t` counters now work correctly. The `do-while` with `uint32_t` workaround has been removed.

### TLCS-900 Opcode Reference for Workarounds

Understanding the opcode table structure helps when crafting raw `.byte` workarounds:

| Prefix Range | Table | Purpose |
|-------------|-------|---------|
| A0-A7 | a0/e0 | Source register indirect (loads) |
| B0-B7 | b0 | Destination register indirect (stores, CALL, JP) |
| B8-BF | b0 + 8-bit displacement | Register indirect + displacement |
| E0-E5 | e0 | Direct memory addressing (loads) |
| F0-F5 | f0 | Direct memory addressing (stores) |

Key b0 sub-opcodes:

| Range | Operation |
|-------|-----------|
| 0x40-0x47 | LD (M), C8 -- store 8-bit register |
| 0x50-0x57 | LD (M), C16 -- store 16-bit register |
| 0x60-0x67 | LD (M), C32 -- store 32-bit register |
| 0xD0-0xDF | JP cc, (M) -- conditional jump indirect |
| 0xE0-0xEF | CALL cc, (M) -- conditional call indirect |

Register indices (for prefixes and sub-opcodes):

| Index | 32-bit | 16-bit | 8-bit |
|-------|--------|--------|-------|
| 0 | XWA | WA | A |
| 1 | XBC | BC | C |
| 2 | XDE | DE | E |
| 3 | XHL | HL | L |
| 4 | XIX | IX | - |
| 5 | XIY | IY | - |
| 6 | XIZ | IZ | - |
| 7 | XSP | SP | - |

## Build Pipeline

The build uses a pure LLVM toolchain:

```
C sources --> clang (-emit-llvm) --> .ll files
                                        |
                                        v
                            llvm-link (merge) --> merged.ll
                                                     |
                                                     v
                                    llc (-filetype=obj) --> all_c.o
                                                               |
startup.s --> clang -c --> startup.o                           |
                              |                                |
                              v                                v
                     ld.lld (linker script) --> ELF
                                                |
                                                v
                              llvm-objcopy -O binary --> raw ROM
                                                           |
                                                           v
                                               dd pad --> 512KB ROM
```

### Linker Script

The linker script places code and data in the extension ROM address space:

```
MEMORY {
  ROM (rx)  : ORIGIN = 0x280000, LENGTH = 512K
  RAM (rwx) : ORIGIN = 0x200000, LENGTH = 12K
}
SECTIONS {
  .startup 0x280000 : { startup.o(.startup) } > ROM
  .text             : { all_c.o(.text) } > ROM
  .rodata           : { *(.rodata*) } > ROM
  .data             : { *(.data*) } > RAM AT > ROM
  .bss              : { *(.bss*) } > RAM
}
```

### Minimal Startup Assembly

A minimal working extension ROM needs only a header, Boot_Init, and Frame_Handler:

```asm
.section .startup, "ax", @progbits

; XAPR Header
    .ascii  "XAPR"
    .byte   0x34, 0xA1, 0x2F, 0x00

; Entry Point 1: Boot_Init (offset 0x08)
    jp      Boot_Init
    ret
    .byte   0x00, 0x00, 0x00

; Entry Point 2: Frame_Handler (offset 0x10)
    jp      Frame_Handler
    ret
    .byte   0x00, 0x00, 0x00

; Entry Points 3-4: Unused
    ret
    .byte   0x00, 0x00, 0x00
    ret
    .byte   0x00, 0x00, 0x00

; Boot_Init: called once with XWA = workspace pointer (0x027ED2)
Boot_Init:
    push    xde
    ld      xde, 0x200000           ; extension RAM
    ld      (xde), xwa              ; store workspace pointer
    pop     xde
    ret

; Frame_Handler: called every frame by firmware
Frame_Handler:
    ; Your per-frame code here
    ret
```

### Complete Makefile Template

A production Makefile for multi-file C projects with MAME ROM set creation. Adapted from the [Mines game](https://github.com/ArqueologiaDigital/Mines/tree/kn5000_port/platforms/kn5000):

```makefile
# HDAE5000 Extension ROM Build System
# Requires: LLVM with TLCS-900 backend

LLVM_BIN := /path/to/llvm-project/build/bin
CLANG    := $(LLVM_BIN)/clang
LLC      := $(LLVM_BIN)/llc
LLD      := $(LLVM_BIN)/ld.lld
OBJCOPY  := $(LLVM_BIN)/llvm-objcopy
LLVM_LINK := $(LLVM_BIN)/llvm-link

BUILD    := build
CFLAGS   := -target tlcs900 -ffreestanding -nostdlib -O2
LLC_FLAGS := -mtriple=tlcs900 -mcpu=tmp94c241 -O2

# Source files (add your .c files here)
C_SRCS   := main.c

# MAME ROM set
ORIGINAL_ROMS := /path/to/kn5000_original_roms/kn5000
ROMSET_DIR    := romset/kn5000
ROM_NAME      := hd-ae5000_v2_06i.ic4

ORIGINAL_ROM_FILES := \
    kn5000_v10_program.rom \
    kn5000_subcpu_boot.ic30 \
    kn5000_subprogram_v142_compressed.rom \
    kn5000_table_data_rom_even.ic3 \
    kn5000_table_data_rom_odd.ic1 \
    kn5000_rhythm_data_rom.ic14 \
    kn5000_waveform_rom.ic307 \
    kn5000_custom_data_rom.ic19

# Derived file lists
LL_FILES := $(patsubst %.c,$(BUILD)/%.ll,$(C_SRCS))

all: romset

$(BUILD):
	mkdir -p $(BUILD)

# Step 1: C -> LLVM IR
$(BUILD)/%.ll: %.c | $(BUILD)
	$(CLANG) $(CFLAGS) -S -emit-llvm -o $@ $<

# Step 2: Link LLVM IR modules
$(BUILD)/all_c.ll: $(LL_FILES)
	$(LLVM_LINK) -S -o $@ $^

# Step 3: LLVM IR -> object
$(BUILD)/all_c.o: $(BUILD)/all_c.ll
	$(LLC) $(LLC_FLAGS) -filetype=obj -o $@ $<

# Step 4: Assemble startup
$(BUILD)/startup.o: startup.s | $(BUILD)
	$(CLANG) -target tlcs900 -mcpu=tmp94c241 -c -o $@ $<

# Step 5: Link
$(BUILD)/extension.elf: $(BUILD)/startup.o $(BUILD)/all_c.o kn5000.ld
	$(LLD) -T kn5000.ld -o $@ $(BUILD)/startup.o $(BUILD)/all_c.o

# Step 6: Binary + pad to 512KB
$(BUILD)/extension.bin: $(BUILD)/extension.elf
	$(OBJCOPY) -O binary $< $@
	@SIZE=$$(stat -c%s "$@" 2>/dev/null || stat -f%z "$@"); \
	if [ "$$SIZE" -lt 524288 ]; then \
		dd if=/dev/zero bs=1 count=$$((524288 - $$SIZE)) 2>/dev/null | \
		tr '\0' '\377' >> $@; \
	fi
	@echo "ROM: $$(stat -c%s "$@" 2>/dev/null || stat -f%z "$@") bytes"

# Create MAME ROM set
romset: $(BUILD)/extension.bin
	mkdir -p $(ROMSET_DIR)
	@for rom in $(ORIGINAL_ROM_FILES); do \
		cp "$(ORIGINAL_ROMS)/$$rom" "$(ROMSET_DIR)/" 2>/dev/null || \
		echo "WARNING: Missing $$rom"; \
	done
	cp $< $(ROMSET_DIR)/$(ROM_NAME)

# Run in MAME
test: romset
	mame kn5000 -rompath romset -extension hdae5000 -window

clean:
	rm -rf $(BUILD)
```

### Key Build Flags

| Flag | Purpose |
|------|---------|
| `-target tlcs900` | Target the TLCS-900 architecture |
| `-mcpu=tmp94c241` | Specific CPU model (enables all instructions) |
| `-ffreestanding` | No hosted C library assumptions |
| `-nostdlib` | No standard library linking |
| `-O2` | Optimization (recommended — `-O0` generates larger code) |
| `-S -emit-llvm` | Emit LLVM IR text (for linking step) |

## Memory Map for Custom ROMs

| Address Range     | Size  | Region              | Use                                                                                   |
|-------------------|-------|---------------------|---------------------------------------------------------------------------------------|
| 0x200000-0x27FFFF | 512KB | Extension RAM       | Variables, stack, heap                                                                |
| 0x280000-0x2FFFFF | 512KB | Extension ROM       | Code, read-only data                                                                  |
| 0x1A0000-0x1DFFFF | 256KB | Video RAM           | 320x240 8bpp linear framebuffer                                                       |
| 0x1703C6          | 1B    | VGA DAC Mask        | Palette mask register                                                                 |
| 0x1703C8          | 1B    | VGA DAC Index       | Palette write index                                                                   |
| 0x1703C9          | 1B    | VGA DAC Data        | RGB data (write 3 bytes sequentially)                                                 |
| 0x1703D4          | 1B    | VGA CRTC Index      | CRTC register select                                                                  |
| 0x1703D5          | 1B    | VGA CRTC Data       | CRTC register data                                                                    |
| 0x8E4A-0x8E54     | 11B   | Right Panel Buttons | Firmware button state (1 byte per segment)                                            |
| 0x8E5A-0x8E64     | 11B   | Left Panel Buttons  | Firmware button state (1 byte per segment)                                            |
| 0x0D53            | 1B    | Firmware Flags      | Bit 3: set while the sequencer's step-record screen is active (not a display disable) |
| 0x03DD04          | 1B    | XAPR Flag           | Extension ROM detection (1=present)                                                   |

The KN5000's LCD is 320x240 pixels at 8 bits per pixel (256-color indexed palette). VRAM starts at `0x1A0000` with a linear framebuffer layout (row-major, 320 bytes per row). See [Display Ownership Model](#display-ownership-model) for details on taking control of the display.

## Testing with MAME

Install your ROM as the HDAE5000 extension:

```bash
# Copy to MAME ROM set
cp your_rom.bin rompath/kn5000/hd-ae5000_v2_06i.ic4

# Run with extension enabled
mame kn5000 -rompath rompath -extension hdae5000 -window -oslog
```

The `-oslog` flag captures debug output, including any invalid instruction reports from the TLCS-900 CPU emulation.

## Related Pages

- [App Loader Tutorial]({{ site.baseurl }}/app-loader/) -- Load and run multiple apps from a FAT16 hard disk
- [Event Codes Reference]({{ site.baseurl }}/event-codes/) -- Complete table of known firmware event codes
- [HDAE5000 Hard Disk Expansion]({{ site.baseurl }}/hdae5000/) -- Original firmware documentation
- [HDAE5000 Filesystem]({{ site.baseurl }}/hdae5000-filesystem/) -- Custom filesystem (FAT, cluster chains, song records) and the lyric file format
- [Display Subsystem]({{ site.baseurl }}/display-subsystem/) -- VGA controller and display architecture
- [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) -- Serial input protocol
- [Memory Map]({{ site.baseurl }}/memory-map/) -- Full system address space
- [Boot Sequence]({{ site.baseurl }}/boot-sequence/) -- System startup and XAPR validation
- [Another World VM]({{ site.baseurl }}/another-world-vm/) -- Another homebrew project for the KN5000
