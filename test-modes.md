---
layout: page
title: Test & Service Modes
permalink: /test-modes/
---

# KN5000 Test & Service Modes

The KN5000 has a comprehensive built-in diagnostic system designed for factory and field service use. There are four categories of test/service modes:

1. **Power-on self-test** — automatic hardware checks at every boot (with checking device)
2. **Control panel button combos** — special modes activated by holding specific panel buttons during power-on
3. **Keybed service modes** — diagnostic tests activated by holding specific piano keys during power-on
4. **HAMA factory diagnostics** — floppy disk and hard disk extension tests (internal Matsushita codename "HAMA")

> **Reference:** Service Manual EMID971655, pages I-17 through I-21.

## MAME Emulation Support

What the driver (`src/mame/matsushita/kn5000.cpp` and its devices) models for each mode, and
what is actually established under emulation. **Not established** means the source shows no
reason the mode cannot work and no record shows it working: it has not been measured.

| Mode | Status under MAME | What is modelled, and where |
|------|-------------------|-----------------------------|
| Power-on self-test, main CPU (CN11) | **Checking device modelled**: switch and LED. Whether every blink reports OK under emulation is not established | `PORT_DIPNAME` "Main CPU Checking Device" on port `CN11`, read through main-CPU Port C (`portc_read().set_ioport("CN11")`); the LED is output `checking_device_led_cn11`, driven from PC.1, drawn by `kn5000.lay` |
| Power-on self-test, sub CPU (CN12) | Same: **switch and LED modelled**; result not established | "Sub CPU Checking Device" on port `CN12`, sub-CPU Port C, output `checking_device_led_cn12` |
| Control-panel button combos | **Not established** | The firmware reads the panel MCUs' segment bytes over the CP serial link (`CPanel_ScanButtons` → `CPanel_CheckSpecialCombos`); `kn5000_cpanel_device` answers those scans from its button ioports (Tab → Input (This Machine)). No record of a combo honoured from power-on under emulation; the flash-update combo is the open item on [MAME Emulation Gaps]({{ site.baseurl }}/mame-emulation-gaps/) |
| Keybed service modes (Tests 3–8) | **Not established** | `SelfTest_FirmwareVersionCheck` asks the sub-CPU for the held-key bitmap (inter-CPU command `0xF002`, 8 bytes at `0x8D64`). Under emulation the sub-CPU runs its real firmware and sees the keybed only through `kn5000_tonegen_device`'s event FIFO (`push_keybed_event`), fed by `keybed_scan` every millisecond from machine start and by the MIDI→keybed UART. Whether its reply reflects keys held from power-on has not been measured; no keybed test mode is on record as entered |
| HAMA factory diagnostics | **Not established** — reached through Test 8 (B3+B4), so the row above applies | `factory_test/` |

---

## Power-On Self-Test

The self-test runs automatically at boot **only when a CHECKING DEVICE is connected** to CN11 or CN12 on the main board. The checking device is a simple circuit: a switch, a 1kΩ resistor, and an LED. Without it, the self-test is skipped entirely (`MainCPU_self_test_routines` at `0xFB729E`, `ui/ui_mode_handlers.s`).

### Detection

The firmware reads Port C bit 0 (`PC.0`; `PC` is SFR `0x30` in `shared/sfr_tmp94c241.s`). If the checking device is not connected, `PC.0` reads high (pull-up) and the self-test returns immediately. With the checking device connected and its switch activated, `PC.0` reads low, and the self-test proceeds. The LED is `PC.1`, driven by `set_dd8 1, 0x30` / `res_dd8 1, 0x30` in `Report_test_result_by_blinking_LED`. The sub-CPU uses the same two bits of its own Port C for CN12.

```
PC.0 = 1 (pull-up)  → No checking device → skip self-test
PC.0 = 0 (grounded) → Checking device present → run self-test
```

### Test Sequence

The self-test reports results by blinking the checking device's LED:
- **Short blink** (0x4000 delay) = component OK
- **Long blink** (0xC000 delay) = component DEFECTIVE

#### Test 1: Sub CPU Peripheral Devices (CN12)

| Blink # | Component | IC |
|---------|-----------|-----|
| 1 | DRAM | IC29 |
| 2 | DRAM | IC28 |
| 3 | Boot ROM | IC30 |
| 4 | (Unassigned) | — |
| 5 | Keyboard Switch Scanning | IC303 |

After the 4th blink, the keyboard switch scanning test engages: pressing any of the 61 keys lights the LED; releasing turns it off. This tests whether key switches and the Tone Generator LSI (IC303) are working.

**Implementation:** the sub-CPU boot ROM's `INIT_MEMORY_TEST` (`0xFF8956`, `subcpu/boot/kn5000_subcpu_boot.s`), gated on the CN12 strap `PC.0`; its keybed pass drains the IC303 event FIFO through `INTER_CPU_LATCH_READ_DISPATCH` and `NOTE_VELOCITY_LOOKUP_CALCULATE` (both misnomers, as their headers say).

#### Test 2: Main CPU Peripheral Devices (CN11)

| Blink # | Component | IC |
|---------|-----------|-----|
| 1 | DRAM | IC10 |
| 2 | DRAM | IC9 |
| 3 | SRAM | IC21 |
| 4 | (Unassigned) | — |
| 5 | Program ROM (ODD) | IC6 |
| 6 | Program ROM (EVEN) | IC4 |
| 7 | Table Data ROM | IC3 |
| 8 | Table Data ROM | IC1 |
| 9 | Rhythm Data ROM | IC14 |
| 10 | Custom Data ROM | IC19 |
| 11 | LCD Controller | IC206 |
| 12 | Video RAM | IC207 |

### Firmware Implementation

The self-test is implemented in `MainCPU_self_test_routines` at `0xFB729E`, in `ui/ui_mode_handlers.s` (addresses from `symbols/maincpu_v10_symbols_reference.txt`):

| Routine | Address | Tests |
|---------|---------|-------|
| `Test_DRAM_IC10_and_IC9` | `0xFB7348` | Writes `0x5A5A5A5A` / `0xA5A5A5A5` patterns, reads back |
| `Test_SRAM_IC21` | `0xFB7400` | Similar write/readback pattern test |
| `Test_PROGRAM_and_TABLE_DATA_ROMs` | `0xFB7456` | ROM checksum verification |
| `Test_Rhythm_data_ROM_IC14` | `0xFB7561` | ROM checksum verification |
| `Test_Custom_data_ROM_IC19` | `0xFB75D4` | ROM checksum verification |
| `Test_LCD_Controller_IC206` | `0xFB763A` | LCD controller register test |
| `Test_Video_RAM_IC207` | `0xFB7687` | VRAM write/readback test |
| `Report_test_result_by_blinking_LED` | `0xFB72EA` | Outputs result via LED blinks |

---

## Control Panel Button Combos

During boot, the firmware scans the control panel buttons via `CPanel_ScanButtons` (`0xFC3EE5`). The routine `CPanel_CheckSpecialCombos` (`0xFC4165`) tests for four specific button combinations and returns a combo code (0–4) in register HL.

### Button Combination Table

| Code | Buttons Held at Power-On | Panel | Bit Pattern | Effect |
|------|--------------------------|-------|-------------|--------|
| 0 | (none) | — | — | Normal boot |
| 1 | MARCH & WALTZ + PARTY TIME + SHOW TIME & TRAD DANCE | Left, SEG6 | `0x38` | Factory Reset (Initial Setting) |
| 2 | GM SPECIAL + ACCORDION REGISTER + DIGITAL DRAWBAR | Right, SEG1 | `0x70` | "ALL INITIAL SETTING!" screen + firmware version on LEDs |
| 3 | AUTO PLAY CHORD + SPLIT POINT + VARIATION 4 + VARIATION 3 | Left, SEG4 | `0x6C` | Software version / internal build numbers |
| 4 | PM 1 + PM 2 + PM 3 + PM 4 (all 4 Panel Memory buttons) | Right, SEG6 | `0x0F` | Flash Memory Update |

### Detailed Descriptions

#### Combo 1: Factory Reset (Initial Setting)

**Buttons:** The three leftmost buttons in the RHYTHM GROUP section.

This is the procedure described in the service manual under "INITIAL SETTING" (p I-3). It resets all programmable settings, functions, and memories to their factory-preset status. **Sequencer**, **Composer**, and **User MIDI** settings are initialized (Rhythm and Custom data are not affected).

**Firmware flow:** The combo code is stored at address `0x402`. At `Boot_HandleFactoryReset` (`0xEF07F3`), the firmware checks if `DRAM[0xFFCA] != 0x5AA5` (payload checksums invalid) **and** combo code == 1. If both conditions are true, it zero-fills all work DRAM (`0x400`–`0x100000`) and SRAM (`0x1E0000`–`0x200000`), then restarts the boot sequence. This is typically used after replacing Flash ROMs.

For normal users, the factory reset is handled through the welcome screen UI widget when combo 2 is detected.

#### Combo 2: ALL INITIAL SETTING / Firmware Version

**Buttons:** Three buttons from the SOUND GROUP section on the right panel.

Displays "ALL INITIAL SETTING!" on the LCD screen and shows the firmware version number on the control panel LEDs. At `Boot_HandleComboDisplay` (`0xEF07A2`), the firmware reads the version byte from `0xFFFFE8` (currently `0x0A` = version 10), looks up the LED pattern from the table at `0xE00000`, and calls `Set_LEDs`.

#### Combo 3: Software Version Screen

**Buttons:** Four buttons spanning the AUTO PLAY CHORD area on the left panel.

Displays the software version screen showing internal build numbers for all firmware components (main program, sub program, etc.). Implemented via `SoundCtrl_SendCommand`.

#### Combo 4: Flash Memory Update

**Buttons:** All four PANEL MEMORY buttons (PM 1–4) on the right panel.

Initiates firmware update from floppy disk. **Requires** both a floppy disk in the drive **and** a first-boot condition (`Get_Firmware_Version` returns `0xFF`). This is the procedure described in the service manual under "How to write program/data into FLASH ROMs" (p I-24). After the update starts, the instrument enters an infinite loop and must be power-cycled.

### Control Panel Memory Layout

The control panel consists of two MCUs (CPL = left, CPR = right) that communicate with the main CPU via serial protocol at 250 kHz. Button states are organized into segments:

| Variable | Address | Panel | Segment |
|----------|---------|-------|---------|
| `CPR_SEG1` | 36427 | Right | Segment 1 (Sound Group buttons) |
| `CPR_SEG6` | 36432 | Right | Segment 6 (Panel Memory buttons) |
| `CPL_SEG4` | 36446 | Left | Segment 4 (Auto Play / Variation buttons) |
| `CPL_SEG6` | 36448 | Left | Segment 6 (Rhythm Group leftmost buttons) |

---

## Keybed Service Modes

These diagnostic tests are activated by holding specific pairs of piano keys while powering on the instrument. They do **not** require the checking device (except Test 4). The keys are always two adjacent notes in the same octave range.

### Service Mode Table

| # | Test | Keys Held | Purpose |
|---|------|-----------|---------|
| 3 | LCD Panel Test | G3 + G4 | Tests LCD display hardware |
| 4 | CPR/CPL MCU Check | D3 + D4 (+ checking device on CN11, switch OFF) | Tests control panel MCU communication |
| 5 | Control Panel Switch & LED Check | F3 + F4 | Tests all panel buttons and LEDs |
| 6 | Wave ROM Check | E3 + E4 | Tests tone generator Wave ROMs (IC304-307) |
| 7 | FDC IC Test | A3 + A4 | Tests Floppy Disk Controller IC (IC208) |
| 8 | Floppy Disk SAVE/LOAD Test | B3 + B4 | Tests actual floppy disk read/write |

### Key Detection (Fully Traced)

After the SubCPU payload is transferred and verified, the firmware calls `SelfTest_FirmwareVersionCheck` (`0xFB76D8` in `ui/ui_mode_handlers.s`). This routine:

1. Sends an inter-CPU command (`0xF002`) to the SubCPU to read the tone generator's keybed scan registers
2. Waits for the SubCPU response (polls bit 7 at address 1568)
3. Reads 8 bytes of key scan data from address 36196 (the keybed state buffer)
4. Counts the total number of pressed keys using a population count (`SelfTest_PopCount`)
5. If exactly **2 keys** are pressed, checks which specific key bits are set
6. Posts `UI_PostModeChangeEvent` with the appropriate mode code

**Mode code dispatch:**

| Key Bits | Mode Code | Event Data | Test Mode |
|----------|-----------|------------|-----------|
| byte[3] bit 2 + byte[4] bit 6 | `0xF5` | `0x1A000F5` | Test 3: LCD Panel |
| byte[3] bit 4 + byte[5] bit 0 | `0xF6` | `0x1A000F6` | Test 4: CPR/CPL MCU |
| byte[3] bit 5 + byte[5] bit 1 | `0xF7` | `0x1A000F7` | Test 5: Panel Switch & LED |
| byte[3] bit 7 + byte[5] bit 3 | `0xF8` | `0x1A000F8` | Test 6: Wave ROM |
| byte[4] bit 1 + byte[5] bit 5 | `0xF9` | `0x1A000F9` | Test 7: FDC IC |
| byte[4] bit 3 + byte[5] bit 7 | `0xFC` | `0x1A000FC` | Test 8: FDD SAVE/LOAD (HAMA) |

`UI_PostModeChangeEvent` sends event `0x1C00015` with the mode code in the low byte, which triggers a screen group transition to the corresponding test mode UI.

> **Under MAME:** the `0xF002` reply comes from the sub-CPU's own firmware, which sees the keybed only through `kn5000_tonegen_device`'s event FIFO (`push_keybed_event`; `keybed_scan` in `kn5000.cpp` pushes into it every millisecond from machine start). Whether that reply reflects keys held from power-on has not been measured — see the status table above.

### Test 3: LCD Panel Test (G3 + G4)

Displays "LCD PANEL TEST" on screen and cycles through display patterns:

**white → black → "H" pattern → red → blue → green** (repeats)

The "H" pattern is a large letter H used to check for LCD crosstalk between adjacent pixels. The color cycling tests the LCD's RGB color planes independently.

**Implementation:** LCD test screen group data containing 5 instances of "LCD PANEL TEST" text widgets at different screen regions (addresses `0xED6E10`–`0xED6F60`). Color cycling is handled by palette manipulation routines.

### Test 4: CPR/CPL MCU Check (D3 + D4 + Checking Device)

**Requires:** Checking device connected to CN11 with switch OFF.

Tests communication between the Main CPU (IC5) and the two Control Panel MCUs:
- CPR (IC1) — right panel
- CPL (IC1) — left panel

Results are reported via LED blinks AND displayed on the LCD:

| Blink # | Component |
|---------|-----------|
| 1 | CPR (IC1) |
| 2–3 | CPL (IC1) |
| 4 | (Unassigned) |

Short blink = OK, long blink = defective.

**Implementation:** `TEST4FUNC` at `0xFB7DAC`, dispatched via control panel event `0x1C00013`.

### Test 5: Control Panel Switch & LED Check (F3 + F4)

All LEDs on the control panel light up simultaneously. Press each button to verify:
- Button press → corresponding LED lights
- Button release → LED turns off
- For buttons without dedicated LEDs, the 4 BEAT display LEDs light up together when the START/STOP button is pressed

**Implementation:** `TEST2FUNC` at `0xFB7D44`, dispatched via control panel event `0x1C00013`.

### Test 6: Wave ROM Check (E3 + E4)

Enters a sine wave diagnostic mode. The Wave ROMs (IC304/305 and IC306/307) output sine waves when keys are pressed. Available check modes (selected via SOUND GROUP buttons):

| Mode | Description |
|------|-------------|
| (1) SINE WAVE & ROM check (w/o TOUCH) | Basic sine wave output, no velocity |
| (2) GENERATOR LSI OUTSEL check | Output select routing test |
| (3) HIGH SOUND check (+2 octave) | Transposed +2 octaves |
| (4) LOW SOUND check (-2 octave) | Transposed -2 octaves |
| (5) NORMAL SOUND check with TOUCH | Sine wave with velocity sensitivity |
| (6) SINE WAVE & ROM check 16dB DOWN | Attenuated output |

Wave ROM mapping to keys:
- **C keys:** IC304 & IC305
- **C# through B keys:** IC306 & IC307

If no sound is produced or the sound is distorted for a particular key, the corresponding Wave ROM chip may be defective.

**Implementation:** `TEST6FUNC` at `0xFB7DE0` and `TEST3FUNC` at `0xFB7D78`, dispatched via control panel event `0x1C00013`. String data at `0xED19D0`–`0xED1A70`.

### Test 7: FDC IC Test (A3 + A4)

Tests communication between the Floppy Disk Controller IC (IC208) and the Main CPU. Results are displayed on the LCD.

**Note:** This test only checks the FDC IC ↔ CPU communication path. It does **not** test the actual floppy disk drive mechanism. For a full drive test, use Test 8 instead.

**Implementation:** `TestTitleFunc` at `0xF1E39A` (shared test title display routine), with FDC-specific test code dispatched via the screen group event system.

### Test 8: Floppy Disk SAVE/LOAD Test (B3 + B4)

**Requires:** A formatted floppy disk inserted in the drive.

Performs repeated save/load cycles on the floppy disk:
1. Press "▶" on the LCD to start the test
2. Data is saved to and loaded from the disk repeatedly
3. The two data sets are compared
4. OK/NG counts are displayed on the LCD
5. Press "■" to stop the test

Even with a properly functioning drive, occasional "NG" results may occur. If frequent, clean the drive heads with a cleaning disk and re-test. Persistent failures indicate a defective drive.

**Implementation:** `FDLoadSaveTest` at `0xF1E5DA`. Display strings include "FD SAVE/LOAD TEST", "START FDD TEST LOOP", "STOP FDD TEST". Test results shown as "TEST2OKNG", "TEST2OKOK", etc.

---

## HAMA Factory Diagnostics (Codename "HAMA")

The HAMA subsystem is an internal Matsushita factory diagnostic system for testing floppy disk I/O and hard disk extension (HDAE5000) hardware. "HAMA" is the developer codename preserved in the ROM's factory test string table alongside other original symbol names (`assswb_op`, `sendCOMM`, etc.).

### Registration

`InitializeHama` (at `0xF1E146`) is called unconditionally during boot from the UI initialization sequence (`ui/ui_widget_defs.s`). It registers:

- **12 NAKA widget object tables** for the test UI system (file browsers, dialog buttons, diagnostic counters)
- **2 diagnostic titles** in the firmware's title system:

| Title | String Address | Widget Table | Description |
|-------|---------------|--------------|-------------|
| `TT_HDDEXT` | `0xE1FD18` | `0x7F` | FDD / Hard Disk Extension test |
| `TT_EXTAPR` | `0xE1FD22` | `0xFC` | Extension APR test |

Both titles use `TestTitleFunc` (`0xF1E39A`) as their lifecycle callback.

### TestTitleFunc Event Handler

When a HAMA title becomes active, `TestTitleFunc` processes two event types:

**Event `0x1C00007` — Title lifecycle** (xde parameter):

| xde | Action |
|-----|--------|
| 0 | Title created — initialize test UI |
| 1 | Title destroyed — send cleanup event + kill timer |
| 2 | Title activated — display test counters + set 0.5s auto-refresh timer |
| 3 | Title inactivated — run directory listing |
| 4–5 | Interrupt / interrupt return — re-register HAMA title entries |
| 6 | TBIOS test — list directory (alternate entry) |

**Event `0x1C00013` — User button actions** (xde parameter):

| xde | Action |
|-----|--------|
| 2 | STOP FDD TEST |
| 3 | START FDD TEST LOOP — calls `FDLoadSaveTest` |
| 4 | DIR — display floppy directory listing |
| 5–6 | Debug test functions |

### FDD SAVE/LOAD Test (FDLoadSaveTest)

The core diagnostic test (`0xF1E5DA`):

1. Allocates a 2 KB buffer
2. Fills it with a counting pattern (`0x000`–`0x3FF`, 2 bytes each)
3. Opens file `A:IMMUNITY.TST` via `FileOpen`
4. Writes the buffer via `FileWrite`
5. Closes and reopens the file
6. Reads back via `FileRead`
7. Compares read-back data against original pattern byte-by-byte
8. Reports OK/NG via `FDTest_PrintDiag` debug output

The test dialog displays three DIAGLIST widgets showing TOTAL, OK, and NG counters.

### Memory Dump Tool (DbMemoryDumpProc)

The HAMA diagnostic system includes a built-in **interactive memory hex viewer** — a complete debugging tool for inspecting arbitrary memory addresses across the KN5000's entire 24-bit address space.

**Implementation:** `DbMemoryDumpProc` in `ui/ui_widget_defs.s:6878` (`0xFA2EE6`–`0xFA317D`, 663 bytes, per `symbols/maincpu_v10_symbols_reference.txt`). Widget descriptor at `FDTest_Label_MemoryDump` in `factory_test/fd_test_data.s:175`.

#### Display Format

The viewer renders a classic hex dump display with **16 rows of 8 bytes each** (128 bytes per page):

```
XXYYYY  XX XX XX XX XX XX XX XX  ........
```

Each row contains three columns:
1. **Address** — formatted as `%02X%04X` (bank byte + 16-bit offset, e.g., `0E F000`)
2. **Hex data** — 8 bytes formatted as `%02X %02X %02X %02X %02X %02X %02X %02X`
3. **ASCII interpretation** — the same 8 bytes shown as printable characters, with any byte below `0x20` (space) replaced by `.` (period, `0x2E`)

The display is rendered inside a double-bordered design box (`DrawDesignBox` with styles `0xC5` outer / `0xC6` inner), with 5-pixel inset margins on all sides.

#### Address Navigation

The viewer supports **per-nibble address navigation** using 6 step sizes corresponding to each hex digit of the 24-bit address:

| Input | Step Size | Navigates |
|-------|-----------|-----------|
| xde=2 | `0x100000` (1 MB) | Top nibble — selects memory bank (ROM, DRAM, I/O, etc.) |
| xde=3 | `0x010000` (64 KB) | Second nibble — coarse offset within bank |
| xde=4 | `0x001000` (4 KB) | Third nibble — page-level navigation |
| xde=5 | `0x000100` (256 B) | Fourth nibble — fine navigation |
| xde=6 | `0x000010` (16 B) | Fifth nibble — two-row steps |
| xde=7 | `0x000001` (1 B) | Least significant nibble — single-byte precision |
| xde=16 | `0x000080` (128 B) | **Page step** — advances exactly one screenful |

Direction is determined by bit 7 of the WA register: if set, the step is **subtracted** (scroll up); if clear, it is **added** (scroll down). After each navigation, the address is **clamped to 24 bits** (`AND 0xFFFFFF`) to prevent wrap-around, then the display is refreshed.

This per-nibble scheme means a Matsushita technician could quickly jump to any memory region: step xde=2 to select the major region (e.g., `0xE00000` for Program ROM, `0x200000` for DRAM), then refine with smaller steps.

#### Rendering Pipeline

When the Confirm event (`0x1C0000F`) fires, the viewer:

1. Retrieves the view instance via `GetViewInstance`
2. Reads the widget's bounding rectangle and insets it by 5 pixels
3. Enters a **16-iteration row loop** (rows 0–15):
   - Computes the row's vertical position (9-pixel row height)
   - Copies 8 bytes from the target memory address into a local buffer via `Mem_Copy`
   - Renders the **address column** using `Sprintf_Locked` (`%02X%04X` format) and `DrawString`
   - Renders the **hex column** (`%02X` × 8) at a 0x30-pixel horizontal offset
   - **Sanitizes** the 8 bytes for ASCII display: loops through each byte, replacing any value < `0x20` with `0x2E` (period), then null-terminates the string
   - Renders the **ASCII column** at a 0x96-pixel horizontal offset (= 0x30 + 0x66)
4. Returns success

The entire rendering is immediate-mode: each Confirm event redraws all 16 rows from scratch.

#### Event Handler

| Event | Handler | Action |
|-------|---------|--------|
| `0x1C00007` | `DbMemDump_OK` | **Navigation dispatch** — receives button presses, looks up the step size from a 6-entry `u32` table at `0xEAA6FA` (`Str_No + 0x3E4`, labelled `DbMemDump_StepTable` in the source; entries 0x100000, 0x10000, 0x1000, 0x100, 0x10, 0x1 -- the hex-digit weights, index 0..5 selected at `v10/maincpu/ui/ui_widget_defs.s:7088-7091`), adjusts the current address, clamps to 24 bits, triggers redraw via Confirm event |
| `0x1C0000F` | `DbMemDump_Confirm` | **Render** — reads 128 bytes from the current address and renders the full hex dump display |
| `0x1C0000E` | `DbMemDump_Select` | **Auto-repeat** — forwards to Confirm, then sets a periodic timer (`SetApTimer` at 120 ticks) for continuous scrolling while a button is held |
| `0x1C0000D` | `DbMemDump_Paint` | **Background paint** — draws the double-bordered box frame, then triggers a Select event to fill the hex content |
| `0x1C00002` | `DbMemDump_Close` | **Cleanup** — delegates to `ViewableProc` for standard widget teardown |

#### Accessible Memory Regions

Because the tool reads directly from the CPU's address bus, it can inspect **any** memory-mapped region:

| Address Range | Contents |
|--------------|----------|
| `0x000000`–`0x000FFF` | Internal CPU RAM (stack, variables, interrupt vectors) |
| `0x001000`–`0x0FFFFF` | SFR registers, I/O ports, timer/serial config |
| `0x100000`–`0x15FFFF` | Tone generator / DSP hardware registers |
| `0x1A0000`–`0x1DFFFF` | Video RAM (LCD framebuffer, 320×240 8bpp) |
| `0x1E0000`–`0x1FFFFF` | SRAM (battery-backed user settings) |
| `0x200000`–`0x27FFFF` | Extension DRAM (work memory, sequencer data) |
| `0x280000`–`0x2FFFFF` | HDAE5000 extension ROM (if installed) |
| `0x800000`–`0x9FFFFF` | Table Data ROM (fonts, presets, demo songs) |
| `0xE00000`–`0xFFFFFF` | Program ROM (main CPU firmware) |

This makes the tool invaluable for inspecting live hardware state, verifying ROM contents, watching variable changes, and debugging I/O register configurations.

#### Activation

The memory dump widget is part of the "DEBUG SCREEN for HD-AE" layout within the HAMA test system. Access path:

1. Hold **B3 + B4** during power-on → enters HAMA test mode (TT_EXTAPR)
2. Select one of the Debug Test buttons (xde=5 or xde=6 in the `TestTitleFunc` action dispatch)
3. The debug screen layout includes the MEMORY DUMP widget alongside CONSOLE output and navigation controls

#### Why Did Matsushita Include This?

The presence of a full interactive memory viewer in shipping firmware (not just a debug build) reveals several things about the KN5000's development and support lifecycle:

**1. Field Service Diagnostics**

The KN5000 was a professional-grade instrument sold to working musicians, music schools, and churches worldwide. When a unit failed in the field, a Matsushita/Technics service technician needed to diagnose the problem without returning the unit to the factory. The memory dump tool allows a technician to:

- **Verify ROM integrity** by reading back Program ROM, Table Data ROM, and Custom Data ROM contents and comparing against known-good checksums
- **Check SRAM battery backup** by inspecting the battery-backed SRAM region (`0x1E0000`+) to determine if user settings have been corrupted by a dying backup battery — a common failure mode in 1990s keyboard instruments
- **Inspect live I/O state** by reading tone generator registers (`0x100000`+), VGA controller registers, FDC status, and UART configurations to identify communication failures between subsystems
- **Diagnose DRAM failures** by reading the extension DRAM region and checking for stuck bits or addressing failures that the power-on self-test (which only tests basic patterns) might miss

**2. Factory Production Line Testing**

During manufacturing at the Hamamatsu factory, each unit would pass through a quality control station where a technician (using the checking device on CN11/CN12) would run the full test suite. The memory dump provides a catch-all diagnostic when the automated tests pass but the unit still exhibits anomalous behavior. A technician could:

- Compare DRAM initialization patterns against a reference unit
- Verify that Flash ROM programming completed correctly by reading back the firmware
- Check that the tone generator's waveform ROM mapping is correct by reading IC303/IC304-307 register states
- Inspect the SubCPU's shared memory region to verify inter-CPU communication

**3. Firmware Development and Debugging**

The tool's per-nibble navigation scheme (with step sizes from 1 byte to 1 MB) is clearly designed by firmware engineers for their own use during development. The Matsushita engineers working on KN5000 firmware updates (v5 through v10, spanning 1997–1999) would have used this tool to:

- **Watch variable changes in real time** by navigating to DRAM work areas and observing how the firmware's state machines respond to user input
- **Debug inter-CPU protocol issues** by inspecting the shared memory mailbox regions used for Main CPU ↔ SubCPU communication
- **Verify NAKA widget descriptor integrity** by reading the widget tables in DRAM and confirming that `RegisterObjectTable` copied them correctly from ROM
- **Test the HDAE5000 extension** (hence "DEBUG SCREEN for HD-AE" in the label) by reading the extension ROM region to verify that the hard disk expansion board's firmware is accessible

**4. Cost-Effective Debug Infrastructure**

Including the tool in the shipping ROM (rather than maintaining a separate debug build) saved Matsushita from needing to manage two firmware images. The tool costs 663 bytes of ROM (`0xFA2EE6`–`0xFA317D`) and is completely hidden from normal users — it requires a specific keybed combination (B3+B4) during power-on that no user would accidentally trigger. This is the same engineering philosophy seen in many Japanese consumer electronics of the era: ship the debug tools, hide them behind obscure key combinations, and let service technicians discover them through the service manual.

**5. The "HAMA" Codename Connection**

The memory dump tool lives inside the "HAMA" diagnostic subsystem. "HAMA" is likely an abbreviation of **Hamamatsu** — the city where Matsushita's musical instrument division was headquartered and where the KN5000 was designed and manufactured. Embedding the factory's name as a codename in the diagnostic system is a common practice in Japanese engineering culture, connecting the diagnostic tools to the physical factory where they would be most frequently used.

### HAMA Function Reference Table

The factory test string table in `test_data.s` lists the original Matsushita debug symbol names for functions tested by the diagnostic system:

| Original Symbol | Semantic Name | Address | Purpose |
|----------------|---------------|---------|---------|
| `sendCOMM` | `sendCOMM` | `0xEF32F4` | Chunked SubCPU data transfer |
| `assswb_op` | `SwbtWr_ReinitBothBanks` | `0xEF14D8` | Reinitialize both tone gen banks |
| `assswb_out` | `SwbtWr_ReinitOutputBank` | `0xEF14F3` | Reinitialize output tone gen bank |
| `SwbtWr` | `SwbtWr` | — | Sound Write Bank Table Writer root |
| `AddswbWr` | `AddswbWr` | — | Add sound write bank entry |
| `AssswbWr` | `AssswbWr` | — | Assign sound write bank entry |
| `ChangePalette` | `ChangePalette` | — | LCD palette change |
| `free_X` | `free_X` | — | Memory free |
| `malloc_X` | `malloc_X` | — | Memory allocate |
| `SetGlobalError` | `SetGlobalError` | — | Set global error flag |

These strings are displayed on the diagnostic LCD during hardware validation, providing factory technicians with the original source code function names for debugging.

### Activation Path (Traced)

The HAMA titles are activated through the **keybed service mode system**:

**Test 8 (B3 + B4) → TT_EXTAPR (mode 0xFC):**
Holding keys B3 and B4 during power-on causes `SelfTest_FirmwareVersionCheck` to post mode code `0xFC` via `UI_PostModeChangeEvent`. This matches the widget table ID `0xFC` used when registering `TT_EXTAPR`, activating the full HAMA diagnostic screen with FDD SAVE/LOAD test, directory listing, and debug functions.

**TT_HDDEXT (widget table 0x7F):**
The `TT_HDDEXT` title (Hard Disk Extension test) is registered with widget table `0x7F`, which does not correspond to any direct keybed mode code. It is likely accessible from **within** the TT_EXTAPR test screen — the `TestTitleFunc` lifecycle handler processes interrupt/resume events (xde=4-5) that call `RegHamaTitle1/2_Entry`, which may switch between the two HAMA titles. This allows a technician to enter the diagnostic system via Test 8 (B3+B4) and then navigate to the HDD extension test using on-screen buttons.

**Complete activation chain:**
```
Power on while holding B3 + B4
  → Boot sequence runs normally
  → SelfTest_FirmwareVersionCheck reads keybed via SubCPU
  → Detects 2 keys: byte[4] bit 3 + byte[5] bit 7
  → Posts UI_PostModeChangeEvent(0xFC)
  → Event 0x1C00015 with data 0x1A000FC
  → Title system activates TT_EXTAPR (widget table 0xFC)
  → TestTitleFunc receives lifecycle event 0x1C00007 (activate)
  → HAMA diagnostic screen displayed
  → User can START/STOP FDD test, browse files, run debug tests
```

### Source Files

| File | Purpose |
|------|---------|
| `factory_test/test_init.s` | `InitializeHama` — title & widget registration, `TestTitleFunc` lifecycle handler |
| `factory_test/test_data.s` | HAMA function reference table, UI configuration data, `HamaList` widget descriptors |
| `factory_test/fd_test_code.s` | `FDLoadSaveTest` — floppy disk test execution, `HamaListProc` event handler |
| `factory_test/fd_test_data.s` | NAKA widget descriptors for test dialog, title strings `TT_HDDEXT` / `TT_EXTAPR` |

---

## Code Locations Summary

Paths are under `v10/maincpu/` unless stated; addresses are from
`symbols/maincpu_v10_symbols_reference.txt` and `symbols/subcpu_boot_symbols_reference.txt`,
generated from the built ELFs, which are byte-identical to the dumps.

| Routine | Address | File | Purpose |
|---------|---------|------|---------|
| `MainCPU_self_test_routines` | `0xFB729E` | `ui/ui_mode_handlers.s` | Power-on self-test dispatcher |
| `Report_test_result_by_blinking_LED` | `0xFB72EA` | `ui/ui_mode_handlers.s` | LED blink result reporter |
| `Test_DRAM_IC10_and_IC9` | `0xFB7348` | `ui/ui_mode_handlers.s` | DRAM test (write patterns) |
| `Test_SRAM_IC21` | `0xFB7400` | `ui/ui_mode_handlers.s` | SRAM test |
| `SelfTest_FirmwareVersionCheck` | `0xFB76D8` | `ui/ui_mode_handlers.s` | Keybed service-mode detection |
| `INIT_MEMORY_TEST` | `0xFF8956` | `subcpu/boot/kn5000_subcpu_boot.s` | Sub-CPU (CN12) self-test |
| `CPanel_ScanButtons` | `0xFC3EE5` | `ui/cpanel_routines.s` | Boot-time button scan |
| `CPanel_CheckSpecialCombos` | `0xFC4165` | `ui/cpanel_routines.s` | Button combo detection |
| `InitializeHama` | `0xF1E146` | `factory_test/test_init.s` | HAMA subsystem registration |
| `TestTitleFunc` | `0xF1E39A` | `factory_test/test_init.s` | Test title lifecycle handler |
| `FDLoadSaveTest` | `0xF1E5DA` | `factory_test/fd_test_code.s` | Floppy disk SAVE/LOAD test |
| `HamaListProc` | `0xF1E870` | `factory_test/fd_test_code.s` | File browser event handler |
| `TEST2FUNC` | `0xFB7D44` | `ui/ui_mode_handlers.s` | Panel switch & LED test handler |
| `TEST3FUNC` | `0xFB7D78` | `ui/ui_mode_handlers.s` | Wave ROM test handler (part) |
| `TEST4FUNC` | `0xFB7DAC` | `ui/ui_mode_handlers.s` | CPR/CPL MCU test handler |
| `TEST6FUNC` | `0xFB7DE0` | `ui/ui_mode_handlers.s` | Wave ROM test handler (part) |
| `DbMemoryDumpProc` | `0xFA2EE6` | `ui/ui_widget_defs.s` | Hidden hex viewer |
| `Boot_HandleComboDisplay` | `0xEF07A2` | `kn5000_v10_program.s` | Boot combo handler (LED version) |
| `Boot_HandleFactoryReset` | `0xEF07F3` | `kn5000_v10_program.s` | Boot combo handler (factory reset) |
| `WidgetParam_TestMode_Entry` | `0xEDBA44` | `ui_widgets/widget_dispatch.s` | Test mode widget entry |
| `Get_Firmware_Version` | `0xFFFEE5` | `kn5000_v10_program.s` | Returns firmware version byte |
| `FIRMWARE_VERSION` | `0xFFFFE8` | `boot/rom_end_structure.s` | Version byte (0x0A = v10) |

---

## See Also

- [Boot Sequence]({{ site.baseurl }}/boot-sequence/) — Complete boot flow including button combo handling
- [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) — Serial communication with panel MCUs
- [Keybed Scanning]({{ site.baseurl }}/keybed-scanning/) — How the keyboard interfaces with IC303
- [Hardware Architecture]({{ site.baseurl }}/hardware-architecture/) — IC numbers and board layout
