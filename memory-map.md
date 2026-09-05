---
layout: page
title: Memory Map
permalink: /memory-map/
---

# KN5000 Memory Map

## Main CPU Address Space

| Address Range | Size | Description |
|---------------|------|-------------|
| `0x000000 - 0x0003FF` | 1KB | Special Function Registers (on-chip) |
| `0x000400 - 0x000BFF` | 2KB | On-chip RAM (decoded inside the CPU, so it wins over the DRAM below) |
| `0x000000 - 0x0FFFFF` | 1MB | Work DRAM, 2 × 4 Mbit at IC9/IC10 on CS3 — **volatile**, not battery backed |
| `0x110000` | - | Floppy Disk Controller |
| `0x120000` | - | Floppy DMA acknowledge window (**not** the inter-CPU latch — that is at `0x140000` on this bus) |
| `0x140000` | - | Inter-CPU Communication Latches (IC22/IC23) |
| `0x150000 - 0x150003` | - | Audio/mixer register file (IC11 74VHC138 decode) — register-address latch at `0x150000`, data at `0x150002`. `AudioMix_Init` writes ~68 registers every boot; it is the main-bus twin of the sub-bus `0x130000` block. Chip identity open (service-manual p.32) |
| `0x160000 - 0x160006` | 8B | HDAE5000 PPI (8255) |
| `0x1703B0 - 0x1703DF` | - | VGA Registers (LCD Controller IC206 MN89304, memory-mapped at 0x170000 + VGA port) |
| `0x1A0000 - 0x1DFFFF` | 256KB | Video RAM (IC207 M5M44265CJ8S, 512KB chip with 256KB mapped via A18 bank select) |
| `0x1E0000 - 0x1FFFFF` | 128KB | Battery-backed SRAM (1 Mbit, IC21) — the machine's only persistent RAM |
| `0x280000` | 512KB | HDAE5000 ROM |
| `0x300000 - 0x3FFFFF` | 1MB | Custom Data Flash (User Storage) - see [Boot Sequence]({{ site.baseurl }}/boot-sequence/#lzss-preset-data-handling) for 0x3E0000 usage |
| `0x400000` | - | Rhythm Data ROM |
| `0x800000` | 2MB | Table Data ROM — see [internal layout](#table-data-rom-internal-layout) below |
| `0xE00000` | 2MB | Program Flash (Main ROM) |

At reset the Table Data ROM is mapped at `0xE00000-0xFFFFFF` (overlapping the Program
Flash) so that its first-stage bootloader can run; the bootloader later reprograms one
chip-select register and the ROM moves to `0x800000`. Bootloader routines therefore have
two addresses: a ROM address `0x9Fxxxx` and a boot-time alias `0xFFxxxx` (+0x600000).

> The swap is a **single store**, `MSAR2 := 0x80` at table-data `0x9FB6D3`, three
> instructions before the jump into the program flash — not part of the earlier
> memory-controller init block, which sets `MSAR2 = 0xC0`. The table below is the map
> *after* that store. See
> [TMP94C241 Memory Controller]({{ site.baseurl }}/tmp94c241-memory-controller/) for the
> six chip-select blocks, the measured register values, and the caveat that the exact
> MSAR/MAMR decode rule is reconstructed rather than documented.

## Table Data ROM Internal Layout

The 2MB table-data ROM is now source-built region by region. The table below is the
top-level map as recorded in `table_data/kn5000_table_data.s`; see
[Table Data ROM]({{ site.baseurl }}/table-data-rom/) for per-region detail and
[ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/) for conversion status.

| Address Range | Contents | Source module |
|---------------|----------|---------------|
| `0x800000 - 0x82FFFF` | Section directory (34 LE32 entries) + 27 in-half preset data banks | `preset_banks.s` |
| `0x830000 - 0x8324D3` | Tone database directory, bank maps, 629-entry tone-record offset table | `tone_database_directory.s` |
| `0x8324D4 - 0x855A47` | 579 tone/voice records | `tone_database_records.s` |
| `0x855A48 - 0x87FFEF` | Drum kits, percussion and name lists, envelope data | `tone_database_aux.s` |
| `0x87FFF0 - 0x8CFFFF` | Feature Demo data (SSF file, BMP bitmaps, file entries) | `kn5000_table_data.s` |
| `0x8D0000 - 0x8DFFFF` | Unused (0xFF fill) | — |
| `0x8E0000 - 0x8ECFFF` | SLIDE4K compressed preset block (demo preset 18, the Feature Presentation) | `kn5000_table_data.s` |
| `0x8ED000 - 0x912FFF` | Two 320×240 8bpp wallpapers, each followed by a 1KB trailer of 16-entry `{r,g,b,0}` shade ramps | `kn5000_table_data.s` |
| `0x913000 - 0x91CFFF` | UI bitmap descriptor table (34 entries) + 8bpp pixel runs | `ui_bitmaps.s` |
| `0x91D000 - 0x933FFF` | Section banks 6 and 28-32: factory UI images (Technics logo, KN5000 picture, note/drum-edit backgrounds) | `ui_bitmaps.s` |
| `0x934000 - 0x937FFF` | UI frame-piece descriptor table (53 entries) + pixel runs | `ui_bitmaps.s` |
| `0x938000 - 0x938587` | Icon descriptor table (176 entries + terminator) | `kn5000_table_data.s` |
| `0x938588 - 0x944D77` | Icon pixel data (176 × 24×24 4bpp, plus one unreferenced "E.L.S." signature icon) | `kn5000_table_data.s` |
| `0x945C00 - 0x945CAF` | Font descriptor table (10 fonts × 16 bytes + null slot) | `fonts.s` |
| `0x945CB0 - 0x950A5F` | Font glyph bitmaps (1bpp, characters 0x20-0xFF per font) | `fonts.s` |
| `0x951000 - 0x98156F` | Music Stylist preset records (1000 × 198 bytes) | `style_records.s` |
| `0x981570 - 0x983B39` | Unreferenced residue after the record grid, plus a ramp remnant | `style_records.s` |
| `0x983B3A - 0x985FFF` | Stale, truncated SLIDE8K help database (superseded German revision) | `help_databases.s` |
| `0x986000 - 0x986FFF` | Music Stylist pointer table (UI states 0xC2/0xC5) | `style_record_ptr_tables.s` |
| `0x987000 - 0x987FFF` | Music Stylist pointer table (all other UI states) | `style_record_ptr_tables.s` |
| `0x988000 - 0x98868F` | Help language index (two 6-entry pointer tables) + intro strings | `help_databases.s` |
| `0x988690 - 0x9999CB` | Five SLIDE8K help databases (EN, DE, FR, ES, Indonesian) | `help_databases.s` |
| `0x99EC00 - 0x99EC9F` | Panel Memory factory bank names (10 × 16 chars) | `panel_memory_presets.s` |
| `0x99ECA0 - 0x9ABF3F` | Panel Memory factory presets (80 × 674-byte chunk records) | `panel_memory_presets.s` |
| `0x9B4000 - 0x9C3FFF` | Composer factory user-style memory image (copied to RAM 0x94800) | `kn5000_table_data.s` |
| `0x9C4000 - 0x9C404F` | Demo song preset pointer table (19 LE32 entries + null) | `kn5000_table_data.s` |
| `0x9C4050 - 0x9F94CA` | SLIDE4K compressed demo song presets, entries 0-17 (0xFF fill from 0x9F94CB) | `kn5000_table_data.s` |
| `0x9FA000 - 0x9FA14F` | File identifier strings (floppy disk format IDs) | `kn5000_table_data.s` |
| `0x9FA150 - 0x9FB495` | Boot screen bitmaps (1bpp, 224×22) | `kn5000_table_data.s` |
| `0x9FB496 - 0x9FFFFF` | First-stage bootloader: dispatch tables, init, FDC driver, CP-serial driver, C runtime, IVT | see below |

**Key tables the Main CPU reads from this ROM:**

| Address | Table |
|---------|-------|
| `0x800000` | Section directory — 33 entries indexing preset banks for floppy I/O |
| `0x830000` | Tone database directory (see [Sub CPU](#tone-database-in-sub-cpu-ram) — the whole database is shipped to the sub CPU) |
| `0x945C00` | Font descriptors — 10 fonts, 16 bytes each (w, h, descent, ascent, glyph ptr, kern ptr) |
| `0x986000` / `0x987000` | Music Stylist preset pointers, selected by the current UI state ID (RAM `0x8D38`) |
| `0x988000` | Help language index — 6 intro-string pointers + 6 SLIDE8K database pointers; slot 4 of each reuses English |
| `0x9C4000` | Demo song presets — 19 pointers to SLIDE4K blocks; entry 18 is `0x008E0000` |

### First-Stage Bootloader Regions

| Address Range | Contents |
|---------------|----------|
| `0x9FB496 - 0x9FB4D1` | Three FDC dispatch offset tables (for the `jp T,XIX+WA` sites) |
| `0x9FB4D2 - 0x9FB4E7` | `Boot_BitMaskTable` (0x9FB4D2) + `Boot_InitParams` (0x9FB4DC) |
| `0x9FB4E8 - 0x9FB7F1` | `Boot_Init`, halt handler, `Boot_ClearRAM` |
| `0x9FC6F6 - 0x9FC8C1` | HD-AE5000 boot-flash programming tail |
| `0x9FC8C2 - 0x9FCC29` | LZSS (SLIDE4K) decoder suite: `LZSS_ReadByte`, `LZSS_OutputByte`, `LZSS_OutputByte_Alt`, `LZSS_ParseHeader`, `LZSS_Decompress` |
| `0x9FCC2A - 0x9FD8A4` | Flash-update main, bitmap/display helpers, VGA register I/O |
| `0x9FD8A5 - 0x9FEA9C` | FDC command-layer driver (uPD72068 at IC208) — a compact port of the maincpu FDC driver |
| `0x9FEA9D - 0x9FEB2A` | `BootTimer_InterruptHandler` (0x9FEA9D) and `Handler_INT4` (0x9FEAB2) |
| `0x9FEB2B - 0x9FEC6D` | Floppy disk-format probe (`Boot_PulsePD0`, `FDC_ProbeDiskFormat`) |
| `0x9FEC6E - 0x9FF228` | Boot-time CP-serial driver, polling/setup half |
| `0x9FF229 - 0x9FF2F1` | Boot-time CP-serial ISRs (three handlers + two `.long` dispatch tables) |
| `0x9FF2F2 - 0x9FFB2E` | Boot-time CP-serial state handlers and packet codecs |
| `0x9FFB2F - 0x9FFE7F` | Boot C runtime: first-fit heap (list head at RAM `0x0099A0`), `memcmp`, 32-bit divide/modulo |
| `0x9FFE80 - 0x9FFEDF` | Debug character-output group — present but NOP-patched out in shipped firmware |
| `0x9FFEE0 - 0x9FFEFF` | `RESET_HANDLER` |
| `0x9FFF00 - 0x9FFFFF` | TMP94C241F interrupt vector table (entries hold boot-time `0xFFxxxx` addresses) |

The boot-time CP-serial driver is a **separate implementation** from the runtime
`CPanel_*` protocol stack in the program ROM; findings about one do not transfer to the
other. See [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/).

## Special Function Registers (TMP94C241F)

### Serial Channels

| Register | Address | Description |
|----------|---------|-------------|
| `SC0BUF` | - | Serial Channel 0 Buffer |
| `SC0CR` | - | Serial Channel 0 Control |
| `SC0MOD` | - | Serial Channel 0 Mode |
| `SC1BUF` | - | Serial Channel 1 Buffer |
| `SC1CR` | - | Serial Channel 1 Control |
| `SC1MOD` | - | Serial Channel 1 Mode |

### Timers

| Register | Address | Description |
|----------|---------|-------------|
| `T0` - `T7` | - | 8-bit Timers |
| `T8` - `TB` | - | 16-bit Timers |

### DMA Registers

| Register | Address | Size | Description |
|----------|---------|------|-------------|
| `DMAV0` - `DMAV3` | `0x100` - `0x103` | 8-bit | DMA start vector (matches interrupt vector to trigger HDMA) |
| `DMAM0` - `DMAM3` | `0x104` - `0x107` | 8-bit | DMA mode (transfer size, direction, counter mode) |
| `DMAR` | `0x109` | 8-bit | DMA software request (write bit N to trigger DMA ch N) |

DMA source (DMAS), destination (DMAD), count (DMAC), and mode (DMAM) registers are accessed via the `LDC` instruction with control register (CR) numbers. **Note:** TMP94C241 uses different CR numbers than TMP96C141/TMP95C063:

| Register | TMP96C141 CR | TMP94C241 CR | Size |
|----------|-------------|-------------|------|
| DMAS0-3 | 0x00-0x0C | 0x00-0x0C | 32-bit (same) |
| DMAD0-3 | 0x10-0x1C | 0x20-0x2C | 32-bit (different) |
| DMAC0-3 | 0x20-0x2C | 0x40-0x4C | 16-bit (different) |
| DMAM0-3 | 0x22-0x2E | 0x42-0x4E | 8-bit (different) |

**DMAM encoding (bits 4-0):**

| Value | Source | Destination | Size |
|-------|--------|-------------|------|
| 0x00 | Fixed | Increment | Byte |
| 0x01 | Fixed | Increment | Word |
| 0x02 | Fixed | Increment | Long |
| 0x04 | Fixed | Decrement | Byte |
| 0x08 | Increment | Fixed | Byte |
| 0x09 | Increment | Fixed | Word |
| 0x0A | Increment | Fixed | Long |
| 0x10 | Increment (counter only) | — | Byte |
| 0x14 | Increment (counter only) | — | Byte |

### Interrupt Control

| Register | Address | Description |
|----------|---------|-------------|
| `INTE45` | `0xE0` | INT4/INT5 interrupt enable/level |
| `INTE67` | `0xE2` | INT6/INT7 interrupt enable/level |
| `INTE89` | `0xE4` | INT8/INT9 interrupt enable/level |
| `INTEAB` | `0xE6` | INTA/INTB interrupt enable/level |
| `INTET01` | `0xE8` | Timer 0/1 interrupt enable/level |
| `INTET23` | `0xEA` | Timer 2/3 interrupt enable/level |
| `INTET45` | `0xEC` | Timer 4/5 interrupt enable/level |
| `INTET67` | `0xEE` | Timer 6/7 interrupt enable/level |
| `INTE0AD` | `0xF0` | INT0/AD interrupt enable/level |
| `IIMC` | `0xF6` | INT0 mode control (bit 1: 0=level, 1=edge) |
| `INTETC01` | `0xF2` | DMA ch0/ch1 completion interrupt enable/level |
| `INTETC23` | `0xF3` | DMA ch2/ch3 completion interrupt enable/level |
| `INTCLR` | `0xF8` | Interrupt clear register |

### Interrupts

| Vector | Handler | Description |
|--------|---------|-------------|
| `INTA` | `INTA_HANDLER` | Interrupt A (includes serial) |
| `INT0` | `INT0_HANDLER` | External Interrupt 0 |

## Control Panel Memory

### Button State

| Address | Variable | Description |
|---------|----------|-------------|
| `0x8E4A` | `STATE_OF_CPANEL_BUTTONS` | Button state array (Right panel) |
| `0x8E5A` | `STATE_OF_CPANEL_BUTTONS_LEFT` | Button state array (Left panel) |
| `0x8E55` | `STATE_OF_CPANEL_BUTTONS + 11` | Bits 6,7 select value 0x0c/0x0d/0x0e |

### LED State

| Address | Variable | Description |
|---------|----------|-------------|
| `0x8DFD` | `CPANEL_LED_READ_PTR` | LED TX buffer read pointer (word) |
| `0x8DFF` | `CPANEL_LED_WRITE_PTR` | LED TX buffer write pointer (word) |
| `0x8E01` | `CPANEL_LED_TX_BUFFER` | LED state TX buffer (60 bytes) |

### Protocol State

| Address | Variable | Description |
|---------|----------|-------------|
| `0x8D8A` | `CPANEL_STATE_MACHINE_INDEX` | State machine index (byte, values 0-10) |
| `0x8D8B` | `CPANEL_PACKET_BYTE_COUNT` | Packet byte counter (byte, values 0-17) |
| `0x8D9D` | `CPANEL_RX_READ_PTR` | RX buffer read pointer (word) |
| `0x8D9F` | `CPANEL_RX_WRITE_PTR` | RX buffer write pointer (word) |

### Status Flags

| Address | Variable | Description |
|---------|----------|-------------|
| `0x8D8C` | `CPANEL_TX_RX_FLAGS` | TX/RX protocol flags (byte) |
| `0x8D92` | `CPANEL_PROTOCOL_FLAGS` | Protocol state flags (byte) |
| `0x8D93` | `CPANEL_PANEL_DETECT_FLAGS` | Panel detection flags (byte) |

### Encoder Raw Input Storage

| Address | Variable | Description |
|---------|----------|-------------|
| `0x8ECA` | `ENCODER_RAW_MODWHEEL` | Raw modulation wheel input |
| `0x8ECC` | `ENCODER_RAW_VOLUME` | Raw volume slider input |
| `0x8ED4` | `ENCODER_RAW_BREATH` | Raw breath controller input |
| `0x8ED6` | `ENCODER_RAW_FOOT` | Raw foot controller input |
| `0x8ED8` | `ENCODER_RAW_EXPRESSION` | Raw expression pedal input |
| `0x8EDA` | `ENCODER_BREATH_MODE` | Breath controller mode/enable |
| `0x8EDC` | `ENCODER_VOLUME_MODE` | Volume mode configuration |
| `0x8EDE` | `ENCODER_RANGE_LIMIT` | Encoder range limit value |

### MIDI Controller Values

| Address | Variable | Description |
|---------|----------|-------------|
| `0x8EE0` | `MIDI_CC_MODWHEEL_PENDING` | Modulation value with change flag (bit 7) |
| `0x8EE2` | `MIDI_CC_EXPRESSION_PENDING` | Expression value with change flag (bit 7) |
| `0x8EE4` | `MIDI_CC_MODWHEEL_VALUE` | Current modulation wheel value (CC#1) |
| `0x8EE6` | `MIDI_CC_EXPRESSION_VALUE` | Current expression value (CC#0) |
| `0x8EE8` | `MIDI_CC_BREATH_VALUE` | Breath controller value (CC#2) |
| `0x8EEA` | `MIDI_CC_FOOT_VALUE` | Foot controller value (CC#4) |
| `0x8EF4` | `MIDI_CC_VOLUME_VALUE` | Volume controller value (CC#7) |

### Encoder State

| Address | Variable | Description |
|---------|----------|-------------|
| `0x8EFC` | `ENCODER_0_LAST_VALUE` | Previous encoder 0 reading (for delta) |
| `0x8EFE` | `ENCODER_1_LAST_VALUE` | Previous encoder 1 reading (for delta) |
| `0x8F04` | `ENCODER_0_STATUS` | Encoder 0 status flags (bit 3 = changed) |
| `0x8F06` | `ENCODER_1_STATUS` | Encoder 1 status flags (bit 3 = changed) |
| `0x8F10` | `ENCODER_0_OUTPUT` | Encoder 0 output buffer (2 bytes) |
| `0x8F16` | `ENCODER_1_OUTPUT` | Encoder 1 output buffer (2 bytes) |
| `0x8F18` | `ENCODER_STATE_BASE` | Base of encoder state structure |

### Encoder Lookup Tables (ROM)

| Address | Variable | Description |
|---------|----------|-------------|
| `0xEDA13C` | `ENCODER_LUT_MODWHEEL` | Modulation wheel value lookup |
| `0xEDA1BC` | `ENCODER_LUT_VOLUME` | Volume slider value lookup |
| `0xEDA2BC` | `ENCODER_LUT_BREATH_INDEX` | Breath controller index lookup |
| `0xEDA2D2` | `ENCODER_LUT_BREATH_VALUE` | Breath controller value lookup |
| `0xEDA3D2` | `ENCODER_LUT_BREATH_MULT` | Breath controller multiplier table |
| `0xEDA3EA` | `ENCODER_LUT_BREATH_OFFSET` | Breath controller offset table |
| `0xEDA402` | `ENCODER_LUT_FOOT` | Foot controller value lookup |
| `0xEDA482` | `ENCODER_LUT_EXPRESSION` | Expression pedal value lookup |

## Sequencer/Medley Memory

The internal medley system stores user-recorded sequences in battery-backed SRAM.

### Internal Medley Song Storage

| Address | Size | Description |
|---------|------|-------------|
| `0xAB000` | 20KB | Internal medley song slots (10 slots × 0x800 bytes) |
| `0xAB0D0` | - | Song slot 0 data start (0xAB000 + 0xD0 header offset) |
| `0xF180` | 2KB | Current playback buffer (active song copied here) |

Each song slot is 2048 bytes (0x800). The slot address is calculated as: `0xAB000 + (slot_index × 0x800)`.

### Medley State Variables

| Address | Variable | Description |
|---------|----------|-------------|
| `0x84FE` | `MEDLEY_PLAY_FLAG` | Play state: 0=stopped, 1=playing |
| `0x8890` | `MEDLEY_ORDER_ARRAY` | Play order array (10 bytes, 0xFF=unused, 0xFE=marked) |
| `0x889A` | `MEDLEY_SONG_COUNT` | Number of songs in current playlist |
| `0x889C` | `MEDLEY_CURRENT_INDEX` | Currently playing song index |
| `0x889E` | `MEDLEY_REPEAT_FLAG` | Repeat mode: 0=no repeat, 1=repeat all |

### Key Medley Routines (ROM)

| Address | Routine | Description |
|---------|---------|-------------|
| `0xF2065A` | `IntMed_CheckSlotValid` | Check if song slot has valid data |
| `0xF20BCE` | `IntMed_LoadAndPlay` | Load and play song from slot |
| `0xF20BFA` | `IntMed_CopyToBuffer` | LDIR copy from slot to playback buffer |
| `0xF2076D` | `IntMed_GetPlaybackState` | Get current playback state |

See [Sequencer]({{ site.baseurl }}/sequencer/) for complete medley system documentation.

## Sub CPU Address Space

The sub CPU (tone generator controller) has its own memory map, documented from boot ROM disassembly.

| Address Range | Size | Description |
|---------------|------|-------------|
| `0x0000 - 0x00FF` | 256B | Special Function Registers (SFR) |
| `0x0100 - 0x01FF` | 256B | Extended SFR / Memory Controller |
| `0x0400 - 0x04E0` | 225B | Interrupt vector trampolines (copied from boot ROM) |
| `0x04FE` | 1B | `PAYLOAD_LOADED_FLAG` - Payload ready indication (bit 7 set when payload loaded) |
| `0x0500 - 0x05A2` | ~160B | RAM / Stack area (stack init = 0x05A2) |
| `0x0502` | 12B | `DMA_SETUP_PARAMS` - DMA parameter storage (XWA, XDE, BC values) |
| `0x0512` | 4B | `DMA_TARGET_ADDR` - Current DMA destination address |
| `0x0516` | 2B | `DMA_XFER_STATE` - DMA transfer state (0=idle, 1=single xfer, 2=two-phase E1 mode) |
| `0x0518` | 2B | `CMD_PROCESSING_STATE` - Command processing state (0-4) |
| `0x051A` | 1B | `LAST_CMD_BYTE` - Last received command byte from main CPU |
| `0x051E` | 32B | `CMD_DATA_BUFFER` - Variable-length command data buffer |
| `0x0544` | 6B | `CMD_E1_BUFFER` - E1 command data buffer |
| `0x054A` | 10B | `CMD_E2_BUFFER` - E2 command data buffer |
| `0x0556` | 1B | `MEMTEST_RESULT` - Memory test result flags |
| `0x0558` | 8B | `SERIAL_STATUS` - Serial communication status bytes |
| `0x100000` | - | Audio Hardware Registers (DSP/DAC) |
| `0x110000` | - | Keyboard/Control Panel Interface Latches |
| `0x120000` | - | Inter-CPU Communication Latch (the same pair of latches the main CPU reaches at `0x140000`) |
| `0x130000` | - | Tone Generator Registers |
| `0xFE0000 - 0xFFFFFF` | 128KB | Boot ROM |

### Sub CPU SFR Addresses (Confirmed from Boot ROM)

| Address | Register | Description |
|---------|----------|-------------|
| `0x07` | P0FC | Port 0 Function Control |
| `0x0B` | P1FC | Port 1 Function Control |
| `0x0F` | P2FC | Port 2 Function Control |
| `0x1C` | P7 | Port 7 Data |
| `0x1E` | P7CR | Port 7 Control |
| `0x1F` | P7FC | Port 7 Function Control |
| `0x20` | P8 | Port 8 Data |
| `0x22` | P8CR | Port 8 Control |
| `0x23` | P8FC | Port 8 Function Control |
| `0x28` | PA | Port A Data |
| `0x2B` | PAFC | Port A Function Control |
| `0x2C` | PB | Port B Data |
| `0x2F` | PBFC | Port B Function Control |
| `0x30` | INTTC01 | Interrupt Control (Timer 0/1) |
| `0x34` | INTERCPU_STATUS | Inter-CPU handshaking: bit 0=sub ready, bit 1=completion, bit 2=gate, bit 4=main ready |
| `0x36` | SC0CR | Serial Channel 0 Control |
| `0x38` | SC0MOD | Serial Channel 0 Mode |
| `0x3A` | SC1BUF | Serial Channel 1 Buffer |
| `0x3C` | SC1CR | Serial Channel 1 Control |
| `0x3E` | SC1MOD | Serial Channel 1 Mode |
| `0x80` | T01MOD | Timer 0/1 Mode (not watchdog - real WD at 0x110) |
| `0x81` | T01FFCR | Timer 0/1 Flip-Flop Control |
| `0x82` | T8RUN | 8-bit Timer Run Control |
| `0x102` | DMA_BURST_CTRL | DMA burst mode configuration register |

### Payload Image Extents

The 196,608-byte sub-CPU payload is **not one contiguous region**. The main CPU delivers
it as four bulk transfers (`SubCPU_Send_Payload`), and the reconstructed `.rom` image is
the concatenation of the two resulting extents:

| Sub CPU addresses | Size | Note |
|-------------------|------|------|
| `0x000400 - 0x0004FF` | 256B | Vector/trampoline area, sent last |
| `0x00F000 - 0x03EEFF` | 196,352B | The payload proper (three transfers: 0x10000 + 0x10000 + 0xFF00) |

This is why the build post-processes the linked ELF with `dd` before comparison — the
linker lays the code out contiguously from 0x0400 and the two live extents are then
extracted and joined.

### Tone Database in Sub CPU RAM

At boot the main CPU copies table-data ROM `0x830000-0x87FFFF` into sub-CPU work RAM
`0x050000-0x09FFFF` as five 64KB InterCPU E1 bulk transfers (`SubCPU_Send_Payload`).
`DSP_System_Init` then stores the RAM base `0x050000` in `ToneDB_RelBase` (0x045310) and
`ToneDB_RootPtr` (0x045314).

**Address aliasing:** sub-CPU address = table-data ROM address − `0x7E0000`. Every offset
*inside* the database is relative to its own base, so a stored offset is equally valid
read as a sub-CPU address (`0x050000 + offset`). The sub-CPU disassembly never sees the
`0x83xxxx` form.

| Sub CPU | Table Data ROM | Contents |
|---------|----------------|----------|
| `0x050000` | `0x830000` | Directory of 4-byte slots (offset / scalar / unused) |
| `0x050100` | `0x830100` | `ToneDB_BankMap_Main` — 128-entry bank-select byte map |
| `0x050180` | `0x830180` | `ToneDB_ToneNumBanks_Main` — 11 banks × 128 LE16 tone numbers |
| `0x050C80` | `0x830C80` | `ToneDB_BankMap_Coeff` — 128-entry bank-select byte map |
| `0x050D00` | `0x830D00` | `ToneDB_ToneNumBanks_Coeff` — 14 banks × 128 LE16 tone numbers |
| `0x051B00` | `0x831B00` | `ToneDB_ToneOffsetTable` — 629 LE32 offsets to tone records |
| `0x0524D4` | `0x8324D4` | Tone/voice records (`ToneRec_000`…), variable length, 16-char space-padded name first |

**Important:** this region is *data*. The claim that the sub-CPU executable lives at
table-data `0x830000` is wrong; the source path of the runtime code payload is a separate,
still-open question.

### Sub CPU Payload Data Zones

Three large constant-pool regions inside the payload were carved into individually
labelled tables in August 2026. All addresses are sub-CPU addresses.

| Range | Size | Contents |
|-------|------|----------|
| `0x00F7E6 - 0x012114` | ~10.5KB | Voice trim/portamento/key-bend tables, transfer-curve families, jump tables and case maps, DSP algorithm descriptors |
| `0x012115 - 0x012158` | 68B | Tone-generator voice template |
| `0x012195 - 0x014738` | ~9.6KB | EQ and coefficient pools, floating-point constant pools, per-effect parameter metadata for all 100 algorithms |
| `0x0131CF - 0x0133CE` | 512B | `DSP_MixerGain_Curve` — 128 × u32 monotonic **gain** curve (piecewise-exponential, 53.5 dB span, ends at 0x7FFFFF00). Read by `DSP_MixerCoeff_Compute`; it is *not* a pitch table |
| `0x0147B3 - 0x01E17E` | 39,372B | DSP effect bytecode + parameter zone — see [DSP Effect Data Zone]({{ site.baseurl }}/dsp-effect-data-zone/) |
| `0x01ED7C` / `0x01EF0C` / `0x01F09C` / `0x01F22C` | 400B each | The four 100-entry `u32` pointer arrays that index the effect zone (algorithm bytecode, coefficient bytecode, parameter values, parameter descriptors) |

## Inter-CPU Communication

The main CPU and sub CPU communicate through **one pair of 8-bit latches (IC22 and IC23)
that each CPU sees at a different address**: `0x140000` on the main CPU's bus and `0x120000`
on the sub CPU's. Both firmwares name the address they use — `INTER_CPU_COMM_LATCHES` is
`0x140000` in `v10/maincpu/kn5000_v10_program.s` and `0x120000` in
`v142/subcpu/subcpu_vectors.s`. ⚠ On the **main** CPU's bus `0x120000` is the floppy
controller's DMA-acknowledge window and has nothing to do with the latches.

### Latch Addresses

| Bus | Address | Access | Description |
|---|---------|--------|-------------|
| Sub CPU | `0x120000` | R/W | Inter-CPU Communication Latch |
| Main CPU | `0x140000` | R/W | the same latch pair |

The sub CPU boot ROM configures DMA to use this address for bidirectional communication with the main CPU.

### Command Protocol (Boot ROM)

The sub CPU boot ROM implements this command protocol:

| Command Byte | Action | Data Size | Buffer Address |
|--------------|--------|-----------|----------------|
| `0x00 - 0x1F` | Handler dispatch + data | 1-32 bytes | `0x051E` |
| `0xE1` | DMA transfer type 1 | 6 bytes | `0x0544` |
| `0xE2` | DMA transfer type 2 | 10 bytes | `0x054A` |
| `0xE3` | Signal payload ready | 0 bytes | - |

**Command Encoding (0x00-0x1F):**

For general commands, the byte encodes both handler and length:

```
Bits 7-5: Handler index (0-7) → selects from jump table at 0xFF8000
Bits 4-0: Data length minus 1 (0-31 → 1-32 bytes)
```

Example: Command `0x45` = handler 2 (`0x45 >> 5 = 2`), 6 bytes (`(0x45 & 0x1F) + 1 = 6`)

The table at `0xFF8000` is `CmdHandler_Table` in the boot ROM, and **all eight of its
entries are `lds hl,0 / ret` stubs** — the boot loader accepts and acknowledges the whole
command set without implementing any of it. The working handlers arrive with the payload,
as `CMD_DISPATCH_TABLE` at `0x00F46C`
([SubCPU Command Format]({{ site.baseurl }}/subcpu-command-format/),
[Sub-CPU Boot ROM (IC30)]({{ site.baseurl }}/subcpu-boot-rom/#the-command-handler-jump-table-at-0xff8000)).

### Communication Flow

**Main CPU → Sub CPU (Command):**

```
1. Main CPU writes command byte to the latch (`0x140000` on its bus)
2. Sub CPU InterCPU_RX_Handler triggered
3. Sub CPU reads command, initiates DMA for data bytes
4. DMA transfers remaining data to RAM buffer
5. CMD_Dispatch_Handler processes command based on state machine
```

**Sub CPU → Main CPU (Response):**

```
1. Sub CPU writes response to the latch (`0x120000` on its bus)
2. Sub CPU sets appropriate flag bits in VAR_04FE
3. Main CPU polls or receives interrupt
4. Main CPU reads response from latch
```

### Sub CPU State Variables

| Address | Symbol | Description |
|---------|--------|-------------|
| `0x04FE` | `SUBCPU_STATUS_FLAGS` | Bit 6: payload ready, Bit 7: transfer complete |
| `0x0512` | `DMA_TARGET_ADDR` | Current DMA destination address (4 bytes) |
| `0x0516` | `DMA_XFER_STATE` | 0=idle, 1=single xfer, 2=two-phase (E1) |
| `0x0518` | `CMD_PROCESSING_STATE` | 0-4, tracks command processing phase |
| `0x051A` | `LAST_CMD_BYTE` | Most recent command byte received |
| `0x051E` | `CMD_DATA_BUFFER` | Variable-length command data (32 bytes) |
| `0x0544` | `CMD_E1_BUFFER` | E1 command data buffer (6 bytes) |
| `0x054A` | `CMD_E2_BUFFER` | E2 command data buffer (10 bytes) |
| `0x0556` | `MEMTEST_RESULT` | Memory test result flags |
| `0x0558` | `SERIAL_STATUS` | Serial status bytes (8 bytes) |

### DMA Configuration

The boot ROM configures DMA for the inter-CPU latch:

- **Source:** `0x120000` (latch)
- **Mode:** Controlled via undocumented LDC opcodes
- **Trigger:** Write `0x0A` to address `0x0100`

## Sub CPU Boot ROM Routines

Key routines identified in the boot ROM at 0xFF8000+:

| Address | Routine | Description |
|---------|---------|-------------|
| `0xFF8290` | `BOOT_INIT` | Hardware initialization entry point |
| `0xFF8432` | `DEFAULT_HANDLER` | Default interrupt handler (RETI) |
| `0xFF8433` | `RESET_ENTRY` | Alternative reset/NMI handler |
| `0xFF8437` | `SUB_8437` | Tone generator channel init loop |
| `0xFF846D` | `COPY_VECTORS` | Copy interrupt trampolines to RAM |
| `0xFF8490` | `HALT_LOOP` | Error handler (halt and loop) |
| `0xFF84A8` | `INIT_TONE_GEN` | Tone generator initialization |
| `0xFF84F1` | `TONE_GEN_WRITE` | Write data to tone generator |
| `0xFF850E` | `SUB_850E` | Multi-register push/call wrapper |
| `0xFF853A` | `SUB_853A` | Write register pairs to tone generator |
| `0xFF858B` | `COPY_WORDS` | Word block copy (ldirw) |
| `0xFF8594` | `FILL_WORDS` | Memory fill with word values |
| `0xFF859B` | `CHECKSUM_CALC` | Calculate checksum over memory range |
| `0xFF85AE` | `INIT_DMA_SERIAL` | DMA and serial initialization |
| `0xFF8604-0xFF881E` | *DMA routines* | 539 bytes, fully disassembled (5 routines) |
| `0xFF8956` | `INIT_MEMORY_TEST` | Memory test initialization |
| `0xFF881F` | `InterCPU_RX_Handler` | Inter-CPU receive interrupt |
| `0xFF889A` | `DMA_Complete_Handler` | DMA complete interrupt |
| `0xFF88B8` | `CMD_Dispatch_Handler` | Command dispatch interrupt |
| `0xFF89A9` | `DELAY_ROUTINE` | Variable delay loop |
| `0xFF89FC` | `MEM_TEST_ROUTINE` | RAM test routine |
| `0xFF8AB4` | `ROM_CHECKSUM` | Boot ROM integrity check |
| `0xFF8B07` | `SERIAL_INIT` | Serial communication init |
| `0xFF8F6C` | *Trampolines* | 45 interrupt vector trampolines (225 bytes) |
| `0xFFFF00` | *Vector Table* | Hardware interrupt vector table |

## Tone Generator

The tone generator hardware uses two address ranges:

**Data/Status Registers (accessed via P6.7 control):**

| Address | Register | Description |
|---------|----------|-------------|
| `0x110000` | Data | 16-bit voice data (note in low byte, velocity in high byte) |
| `0x110002` | Status | Status register (bit 0: data ready, bit 1: mode flag) |

Port P6 bit 7 controls the A23 address line - SET for status read, RES for data read.

**DSP Control Registers:**

| Address | Description |
|---------|-------------|
| `0x130000` | Dual DSP control base address |

The sub CPU boot ROM initializes tone generator registers with patterns starting at this address. Each voice appears to use a 32-byte register block. The system has 8 voices across 16 MIDI channels.

**Voice State Buffer (Sub CPU RAM):**

| Address | Size | Description |
|---------|------|-------------|
| `0x4A42` | 3B | DMA command buffer (cmd, note, velocity) |
| `0x4A48` | 1B | Tone generator mode (0-6) |
| `0x4A4A` | 1B | DMA enabled flag |
| `0x4A4C` | 16B | Voice slot table |

**DSP State Buffers:**

| Address | Size | Description |
|---------|------|-------------|
| `0x041342` | 38B | DSP state buffer 1 |
| `0x041368` | 7462B | DSP state buffer 2 |

## HDAE5000 Hard Disk Expansion

The HD-AE5000 is a hard disk expansion system providing 1.08GB storage for music files. See the [dedicated HDAE5000 page]({{ site.baseurl }}/hdae5000/) for complete documentation.

### Memory-Mapped Addresses

| Address | Size | Description |
|---------|------|-------------|
| `0x160000` | 2B | PPI Port A (Data output) |
| `0x160002` | 2B | PPI Port B (Status input) |
| `0x160004` | 2B | PPI Port C (Control signals) |
| `0x160006` | 2B | PPI Control Register |
| `0x280000` | 512KB | HDAE5000 ROM |

### ROM Entry Points

| Address | Target | Description |
|---------|--------|-------------|
| `0x280008` | JP 0x28F576 | Boot initialization |
| `0x280010` | JP 0x28F662 | Frame handler (PPORT polling) |

### Analyzed Firmware Version

| Property | Value |
|----------|-------|
| ROM File | `hd-ae5000_v2_06i.ic4` |
| Internal Version | 2.33J |
| Development Period | Juli-Oktober 1996 |
| Author | M. Kitajima |

### PPORT Commands (PC Parallel Port)

| Code | Command | Description |
|------|---------|-------------|
| 01 | Send Infos About HD | Report HD info to PC |
| 02 | Exit PPORT | End parallel port session |
| 03 | Read FSB from HD | Read File System Block |
| 04 | Sending FSB to PC | Transfer FSB to PC |
| 05 | Rcv FSB from PC | Receive FSB from PC |
| 06 | Writing FSB to HD | Write FSB to HD |
| 07 | Load HD to Memory | Load file to KN5000 |
| 08 | Send data to PC | Data transfer to PC |
| 09 | Sending files to PC | File transfer to PC |
| 10 | Rcv data from PC | Receive data from PC |
| 11 | Save memory to HD | Save to hard disk |
| 16 | Delete files | Delete HD files |
| 17 | Formating HD | Format hard disk |
| 18 | Switch HD-motor off | Spin down HD |
| 20 | Send XapFile flash | XAP file transfer |

### Firmware Versions

| Version | Release Date | Notes |
|---------|--------------|-------|
| v1.10i | 1998-07-06 | Initial release |
| v1.15i | 1998-10-13 | Bug fixes |
| v2.0i | 1999-01-15 | Added lyrics display |

All versions archived at [archive.org](https://archive.org/details/technics-kn5000-system-update-disks).

**Reference:** [keysoftservice.ch/hdae5000-e.htm](https://www.keysoftservice.ch/hdae5000-e.htm)
