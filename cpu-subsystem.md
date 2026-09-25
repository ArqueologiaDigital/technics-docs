---
layout: page
title: CPU Subsystem
permalink: /cpu-subsystem/
---

# CPU Subsystem

The KN5000 uses a dual-CPU architecture with two identical TMP94C241F processors performing different roles.

## Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           DUAL CPU ARCHITECTURE                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────┐     ┌──────────────────────────────────────┐
│          MAIN CPU               │     │           SUB CPU                    │
│          TMP94C241F             │     │           TMP94C241F                 │
│                                 │     │                                      │
│  Role: System Controller        │     │  Role: Audio Processor               │
│                                 │     │                                      │
│  ┌───────────────────────────┐  │     │  ┌────────────────────────────────┐  │
│  │ Program ROM: 2MB          │  │     │  │ Boot ROM: 128KB (internal)     │  │
│  │ @ 0xE00000-0xFFFFFF       │  │     │  │ @ 0xFE0000-0xFFFFFF            │  │
│  └───────────────────────────┘  │     │  └────────────────────────────────┘  │
│                                 │     │                                      │
│  ┌───────────────────────────┐  │     │  ┌────────────────────────────────┐  │
│  │ RAM: 512KB                │  │     │  │ Payload: 192KB                 │  │
│  │ @ 0x200000-0x27FFFF       │  │     │  │ (loaded at boot from Main)     │  │
│  └───────────────────────────┘  │     │  └────────────────────────────────┘  │
│                                 │     │                                      │
│  Responsibilities:              │     │  Responsibilities:                   │
│  ├─ User interface              │     │  ├─ DSP control                      │
│  ├─ Menu system                 │     │  ├─ DAC output                       │
│  ├─ Control panel handling      │     │  ├─ Tone generation                  │
│  ├─ MIDI processing             │     │  ├─ Voice management                 │
│  ├─ Sequencer                   │     │  └─ Effects processing               │
│  ├─ Floppy disk I/O             │     │                                      │
│  ├─ HDAE5000 management         │     │                                      │
│  └─ Sub CPU coordination        │     │                                      │
└─────────────────────────────────┘     └──────────────────────────────────────┘
                    │                                     ^
                    │         Communication Latch         │
                    │      main 0x140000 / sub 0x120000    │
                    └─────────────────────────────────────┘
```

## TMP94C241F Specifications

The TMP94C241F is a Toshiba 32-bit microcontroller from the TLCS-900/H2 family.

### Architecture

| Feature | Specification |
|---------|---------------|
| CPU Core | TLCS-900/H2 (32-bit) |
| Clock | main CPU 8 MHz crystal, sub CPU 10 MHz, each with the part's internal clock doubler — 16 MHz and 20 MHz respectively (`TMP94C241(config, m_maincpu, 2 * 8_MHz_XTAL)` / `2 * 10_MHz_XTAL` in `kn5000.cpp`) |
| Address Bus | 24-bit (16MB address space) |
| Data Bus | 16-bit external |
| Registers | 8 general purpose (32-bit each) |
| Instruction Set | CISC, variable length (1-7 bytes) — see [Instruction Encoding Reference]({{ site.baseurl }}/tlcs900-instruction-encoding/) |

### On-Chip Peripherals

| Peripheral | Description |
|------------|-------------|
| RAM | 2 KB on-chip, at `0x000400-0x000BFF` |
| Timers | 8x 16-bit timers |
| Serial | 2x UART, 1x SIO |
| DMA | 4-channel MicroDMA |
| Interrupt | Multi-level interrupt controller |
| I/O Ports | Multiple 8-bit ports |
| ADC | 10-bit ADC (optional) |

### Register File

```
┌─────────────────────────────────────────────────────────────┐
│                    REGISTER FILE                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  XWA  ─┬─ WA' ─┬─ W' ─┬─ A'    (32/16/8/8 bit)              │
│  XBC  ─┼─ BC' ─┼─ B' ─┼─ C'                                 │
│  XDE  ─┼─ DE' ─┼─ D' ─┼─ E'                                 │
│  XHL  ─┼─ HL' ─┼─ H' ─┼─ L'                                 │
│  XIX  ─┼─ IX                                                │
│  XIY  ─┼─ IY                                                │
│  XIZ  ─┼─ IZ                                                │
│  XSP  ─┴─ SP            (Stack Pointer)                     │
│                                                             │
│  PC   ── Program Counter (24-bit)                           │
│  SR   ── Status Register (flags, interrupt level)           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Main CPU

### Memory Map

| Address Range | Size | Description |
|---------------|------|-------------|
| 0x000000-0x0003FF | 1KB | Special Function Registers |
| 0x000400-0x000BFF | 2KB | On-chip RAM (takes priority over the external DRAM below) |
| 0x000000-0x0FFFFF | 1MB | Work DRAM — 2 × 4 Mbit at IC9/IC10 on CS3, **volatile** |
| 0x100000-0x10FFFF | 64KB | Audio/DAC Interface |
| 0x110000-0x11FFFF | 64KB | Floppy Disk Controller |
| 0x120000-0x12FFFF | 64KB | Floppy DMA acknowledge (**not** the inter-CPU latch) |
| 0x140000-0x14FFFF | 64KB | Inter-CPU Latch (IC22/IC23) |
| 0x130010-0x130020 | 16B | HDAE5000 ATA |
| 0x160000-0x160007 | 8B | HDAE5000 PPI |
| 0x170000-0x17FFFF | 64KB | VGA Controller |
| 0x1E0000-0x1FFFFF | 128KB | Battery-backed SRAM (1 Mbit, IC21) — the only persistent RAM |
| 0x280000-0x2FFFFF | 512KB | HDAE5000 ROM |
| 0x300000-0x3FFFFF | 1MB | Custom Data Flash (IC19) |
| 0x400000-0x7FFFFF | 4MB | Rhythm Data ROM (IC14) |
| 0x800000-0x9FFFFF | 2MB | Table Data ROM |
| 0xE00000-0xFFFFFF | 2MB | Program ROM |

See [Memory Map]({{ site.baseurl }}/memory-map/) for complete details.

> **This map is software-defined and it changes once during boot.** The TMP94C241 decodes
> external addresses through six programmable chip-select blocks; the table above is the
> state *after* the bootloader's `MSAR2 := 0x80` handover store. Before it, the table-data
> ROM occupies the top of memory and the program flash sits at `0x800000`. See
> [TMP94C241 Memory Controller]({{ site.baseurl }}/tmp94c241-memory-controller/).

### Firmware Structure

The 2MB Main CPU ROM is organized as:

| Component | Description |
|-----------|-------------|
| Reset Vector | Entry point at 0xFFFEE0 |
| Interrupt Vectors | Exception handlers |
| Boot Code | Hardware initialization |
| Subsystem Handlers | UI, MIDI, FDC, etc. |
| Data Tables | Fonts, graphics, strings |

### Reconstruction Status

The 2 MB image (2,097,152 bytes) rebuilds **byte-identically** from assembly source under
the LLVM TLCS-900 backend (`llvm-mc` + `ld.lld` + `llvm-objcopy`), checked by `make gate`
in the disassembly repo. Instruction and reference counts move with every conversion; see
[ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/) for how the remaining debt is
measured and by which script.

### I/O ports

The parallel ports are the main CPU's connection to the front panel's pedals, the
extension slot and the flash devices. What each bit does is established from the
firmware's own reads and from the direction registers the boot code programs; the SFR
addresses are `PD = 0x30`, `PE = 0x38`, `PG = 0x40`, `PZ = 0x68`.

| Port bit | Direction | Function |
|---|---|---|
| PD.6 | input | floppy disk-change (`Check_for_Floppy_Disk_Change`) — ⚠ also read into the pedal parameter block, see below |
| PE.0 | input | extension board present. **0 = an HD-AE5000 is fitted**, 1 = the slot is empty |
| PE.4 | input | MICSNS — latched every main loop; a change sends an 8-byte packet on the computer-interface port |
| PE.5 | input | control-panel INTA. The panel routines proceed only while it reads low |
| PG.2 | input | foot switch FS1 |
| PG.3 | input | foot switch FS2 |
| PG.4–PG.7 | input | foot controllers FC1–FC4 |
| PZ.7–PZ.4 | input | COM SELECT rotary switch — MIDI / MAC / PC1 / PC2 |
| P7.5 | input | flash ready/busy, polled before every flash command |

**Port G is the pedal port, and its pins are active low.** `MIDI_ProcessVoiceAssignment`
(`v10/maincpu/audio/audio_control_engine.s:1848`, reached from `Audio_PeriodicUpdate`)
reads `PG` three times per periodic tick: bits 3:2 are shifted down and stored as the foot
switch byte at DRAM `0x8EB6`, and bits 7:4 are shifted down and stored as the foot
controller byte at `0x8EBA`. The polarity is not an inference — the firmware's own idle
test is `cp a, 0xf` on the upper nibble, so **all four high means nothing is engaged**, and
a released panel reads `0xFC`. When the test matches, the firmware arms a 500-count
debounce at `0x8EC8` and skips the write. The routine's auto-generated name is misleading;
its body is a foot-switch and foot-controller scan.

**PE.0 gates the whole HD-AE5000 initialisation.** On the normal boot path,
`Boot_FlashAndExtensions` (`v10/maincpu/kn5000_v10_program.s:571`) tests
`bit_dd8 0, 0x38` and skips the extension entirely when it reads 1; when it reads 0 — and
the region code is not 4 — it calls `HDAE5000_Parport_Setup`, which programs the uPD71055
PPI and makes the hard disk reachable. The boot programs `PECR = 0x20`, so PE.0 is an
input and the strap is genuinely external.

**Port E is programmed twice, and the second write is the operative one.** Early boot
writes `PECR = 0x20`, which on its own would make PE.5 the port's only output. On the
unconditional path that follows, `CPanel_InitHardware`
(`v10/maincpu/ui/cpanel_routines.s:95-98`, reached from `kn5000_v10_program.s:584` through
`CPanel_InitDispatchTable[0]`) writes `PEFC = 0x00` and then **`PECR = 0x46`** — outputs on
PE.1, PE.2 and PE.6 only. PE.0 and PE.5 are therefore **inputs** in the running machine, and
the same bytes appear in v7 and v9.

⚠ Reading only the boot write gives the opposite answer for both bits. A port's direction is
whatever the *last* write to its control register says, so a port census has to follow the
whole initialisation path, not stop at the first `PECR`.

⚠ **PD.6 has a contradiction that the ROM cannot settle.** It is read by two floppy routines
and, three instructions after the two Port G reads above, into the pedal parameter block at
`0x8EBE`. The schematic settles the *pin* — net FD.I/O, IC5 pin 17, with a 4.7 kΩ pull-up —
but not its meaning: "disk change" is a routine name supplied by an earlier analysis pass,
not ground truth. Either PD.6 is dual-purpose or one of the two readings is wrong.

## Sub CPU

### Memory Map

| Address Range | Size | Description |
|---------------|------|-------------|
| 0x000400-0x000BFF | 2KB | On-chip CPU RAM (bypasses the external bus) |
| 0x000000-0x0FFFFF | 1MB | Work DRAM — 2 × 4 Mbit at IC28/IC29 |
| 0x002B00-0x002B1F | 32B | Ring buffer control (MIDI message queue from Main CPU) |
| 0x002000-0x031FFF | 192KB | Payload RAM (loaded from Main CPU at boot) |
| 0x100000-0x10FFFF | 64KB | Tone Generator hardware registers |
| 0x120000 | 1B | Inter-CPU communication latch (`0x140000` on the main CPU's bus) |
| 0x130000-0x130002 | 4B | DSP registers (uPD6383GF-3BA: address + data) |
| 0xFE0000-0xFFFFFF | 128KB | Boot ROM |

### Boot Process

1. Sub CPU starts from reset vector in Boot ROM (0xFFFEE0)
2. Initializes DMA and latch configuration (`InterCPU_Latch_Setup` at 0x020B3B)
3. Receives 192KB payload from Main CPU via DMA transfer
4. Main CPU verifies payload checksums (`SubCPU_Payload_Verify`)
5. Jumps to payload entry point
6. Enters audio processing main loop

### Firmware Components

| Component | Size | Status |
|-----------|------|--------|
| Boot ROM (IC30) | 128KB | 100% byte-match, and zero verbatim debt. ⚠ **Only 4,352 of the chip's 131,072 bytes have ever been read** — the rest of the file is `0xFF` standing in for undumped content, so "100% covered" is true over a 3.3% denominator |
| Payload (v1.42) | 192KB | 100% byte-match, zero verbatim debt |

### The RTOS is not bespoke

Both KN5000 processors run the same multitasking kernel as the **SX-WSA1R's** two
TMP95C061s — one kernel source, four processors, two products. The KN5000 builds are
separate builds rather than copies, so the match is structural (decoded token sequences,
graded against a foil) and not a byte match. See
[Shared Codebase Map]({{ site.baseurl }}/technics-shared-codebase/#-one-kernel-four-processors-two-products).

### The two KN5000 CPUs share kernel code byte for byte

Between the KN5000's own two processors the match is closer. 273 runs of at least 16 bytes
(11,946 bytes in all) of the v1.42 Sub CPU payload occur verbatim in the v10 main-CPU ROM
(`python3 scripts/analysis/v142_maincpu_shared_code_scan.py --min 16`, which needs both ELFs
built). A run that starts at the same offset in both enclosing routines (ALIGNED) is the
script's strongest sign that the two names label the same routine. That is how the subcpu lane (September 2026) found several
main-CPU kernel names to be wrong. The main-CPU source still carries these names:

| Sub CPU (v1.42, named from the code) | Main CPU (v10 label) | aligned run |
|:---|:---|:---|
| `TaskSched_SpawnTask` | `Show_ScreenGroup_Entry` (0xEF1B9C) | 63 B at +32 |
| `TaskSched_ExitCurrentTask` | `Show_ScreenGroup_Entry_0x7A` | 20 B at +29 |
| `TaskSched_PreemptiveYield` | `TaskSched_YieldToQueue` | 63 B at +21 |
| `TaskSched_Block_Self` — blocks the **calling** task | `TaskSched_Resume` (0xEF1CEC) | 56 B at +15 |
| `TaskEvent_Signal` / `TaskEvent_Wait_Block` | `TaskSched_SignalEvent` / `TaskSched_WaitForEvent_Block` | 38 B / 30 B |
| `TaskSem_Release` (semaphore V) | `Audio_Lock_Release` (0xEF1F0F) | 44 B at +39 |
| `TaskSem_Release_WakeWaiter` | `AudioLock_Release_WakeWaiter` | 16 B at +56 |
| `TaskSem_TryDec` / `TaskSem_GetCount` | `AudioLock_TryAcquire` / `AudioLock_GetCount` | 22 B / 26 B |
| `TaskMsgQ_Send` / `TaskMsgQ_Receive` | `TaskMsg_Send` / `TaskMsg_Receive` | 41 B at +37 and 54 B at +102 / 39 B at +23 |

So **`Audio_Lock_Acquire` / `Audio_Lock_Release` are the kernel's generic semaphore P/V
routines**, not an audio-specific lock. Their "lock index" is a semaphore number. The audio
command path happens to use semaphore 7 (see
[Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/#lock-mechanism)).
`Show_ScreenGroup_Entry` spawns a task. `TaskSched_Resume` puts the calling task to sleep
rather than resuming another. The run table also pairs the scheduler's init and dispatch
(`TaskSched_Init_TaskDescriptors` / `TaskSched_InitTCBFields`,
`TaskSched_Dispatch_ScanQueues` / `TaskSched_ScanPriorityQueues`) and the timer tick
(`TaskSched_SoftTimer_Service` / `TaskSched_TimerTick`). The same scan shows that main-CPU
`Free_ClearByte` (0xFF0BC3) is byte-identical to the sub CPU's `Int_SignedDiv` over 170 bytes.
Source: `notes/lanes/wave2-2026-09-25/lane-reports/subcpu.json`, and the sub-CPU headers
(`TaskSem_Release`'s says it was `TaskSched_PreemptiveYield_INT` until September 2026).

### Audio Processing Architecture

The Sub CPU's primary role is real-time audio synthesis and effects processing. It manages:

**Voice Management (26 channels):**
- Receives MIDI-like messages from Main CPU via ring buffer at 0x2B0D
- `MIDI_Dispatch` (0x034D93) parses status bytes and routes to voice handlers
- Supports Note On/Off, Control Change, Program Change, Pitch Bend, Channel Pressure
- 26 internal voice channels (0x00-0x19) with per-voice parameter tables
- See [MIDI Subsystem]({{ site.baseurl }}/midi-subsystem/) for full protocol details

**Tone Generator Control:**
- Direct register writes to hardware at 0x100000-0x10FFFF
- Per-channel filter frequency (0x04520A), filter Q (0x04520E), output (0x0451CC)
- Filter frequency clamped to max 0x1C

**DSP Effects Processing (uPD6383GF-3BA):**
- Memory-mapped DSP at 0x130000 (address) / 0x130002 (data)
- 4 effect channels × 32 registers each
- Bytecode interpreter at 0x03C32E (1,613 bytes, 6 native handlers)
- Real-time parameter updates via `DSP_ParameterWriteEngine` (0x03C673)
- See [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) for DSP details

**Hardware I/O:**
- Port E bit 0: Audio mute control (confirmed by `MUTE_AND_HALT` routine at 0x9360)
- Parallel port (P7/PZ): DSP command/data protocol for effect program loading
- DMA Channel 0: Inter-CPU latch data transfer (interrupt-driven)

## Inter-CPU Communication

The CPUs communicate via a hardware latch at 0x120000. The Main CPU sends MIDI-like command streams to the Sub CPU for audio synthesis control.

### Transfer Mechanism

| Component | Main CPU | Sub CPU |
|-----------|----------|---------|
| Latch Address | 0x120000 (write) | 0x120000 (read) |
| Transfer Function | `Audio_DMA_Transfer` (0xEF32F4) | `MICRODMA_CH0_HANDLER` (0x020F1F) |
| Direction | Main → Sub (primary) | Sub → Main (status/ack) |

### Data Flow

1. Main CPU writes MIDI-like messages to latch at 0x120000
2. Sub CPU's MicroDMA Channel 0 fires interrupt on data arrival
3. `MICRODMA_CH0_HANDLER` dispatches received bytes to command parser
4. Bytes accumulate in ring buffer at 0x2B0D
5. `MIDI_Dispatch` processes complete messages from the ring buffer

### Payload Transfer (Boot Only)

At boot, the Main CPU transfers the 192KB Sub CPU payload via the same latch:

| Function | Address | CPU | Purpose |
|----------|---------|-----|---------|
| `SubCPU_Payload_Transfer` | 0xEF0620 | Main | Send 192KB payload |
| `SubCPU_Payload_Verify` | 0xEF06A0 | Main | Verify checksums (DRAM 0xFFD2/0xFFD4) |

The payload checksums are stored in Main CPU DRAM at 0xFFD2 and 0xFFD4, preserved across power cycles via NVRAM save (triggered by SNS NMI).

See [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/) for full protocol details.

## Programming Considerations

### Build System

The project uses **LLVM** with a custom TLCS-900 backend as the authoritative build system for all thirteen gated images:

```bash
# Build all ROMs (from roms-disasm/)
make all

# Pipeline: llvm-mc → ld.lld → llvm-objcopy → raw binary
llvm-mc -triple=tlcs900 -filetype=obj source.s -o output.o
ld.lld -T linker.ld output.o -o output.elf
llvm-objcopy -O binary output.elf output.bin
```

All nine KN5000 images (Main CPU v10/v9/v7, Sub CPU boot, Sub CPU payload and its recompressed form, Table Data, HDAE5000, Custom Data) and the four SX-WSA1R EPROMs rebuild **byte-identically** against the original dumps — 12,386,304 bytes, checked by `make gate-all`.

The ASL Macro Assembler (used historically) is archived in `archive/asl/`.

### `.byte` Code Elimination

As of March 2026, the LLVM backend encodings that were missing at the time (R+d16, 16-bit
direct, 8-bit direct, F2 immediate stores, etc.) had all been implemented, and the disassembly
repository's own milestone commits describe "all executable code" as converted for that
effort. **This is not the current state.** Re-running the repository's own
`scripts/analysis/audit_byte_code.py` classifier (2026-09) still finds several hundred `.byte`
blocks across the sub-CPU boot ROM, HDAE5000 and table-data sources that the tool classifies
as already decodable as native instructions by the current LLVM backend — 397 blocks (20,851
bytes), concentrated in `table_data/preset_banks.s` (18,763 bytes) and
`hdae5000/hdae5000_data_tables.s` (722 bytes) — plus 3 small blocks (19 bytes) that still need
further backend work. Converting `.byte` fallbacks to native mnemonics is therefore an ongoing
effort, not a completed one; see [Raw Byte Code Elimination]({{ site.baseurl }}/raw-byte-code-elimination/)
for the current tracking page. (Note: the classifier's "decodable" label means llvm-mc can
round-trip the bytes as valid instructions, not that a block is proven to be code rather than
data that happens to disassemble cleanly — treat the counts as leads, per the tool's own
caveat.)

## Related Pages

- [System Overview]({{ site.baseurl }}/system-overview/) - Overall architecture
- [Memory Map]({{ site.baseurl }}/memory-map/) - Address space details
- [TMP94C241 Memory Controller]({{ site.baseurl }}/tmp94c241-memory-controller/) - Chip selects and the boot-time remap
- [Boot Sequence]({{ site.baseurl }}/boot-sequence/) - Startup process
- [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/) - Communication details
- [Hardware Architecture]({{ site.baseurl }}/hardware-architecture/) - Physical components
- [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) - DSP effects and tone generation
- [MIDI Subsystem]({{ site.baseurl }}/midi-subsystem/) - MIDI processing and voice management
- [TLCS-900 Instruction Encoding]({{ site.baseurl }}/tlcs900-instruction-encoding/) - Instruction set reference

## Code References

### Main CPU Boot & Init

| Symbol | Address | Purpose |
|--------|---------|---------|
| Reset Vector | `0xFFFEE0` | CPU entry point |
| `MainCPU_self_test_routines` | `0xEF0400` | Boot-time self tests |
| `Get_Firmware_Version` | `0xEF0534` | Read version byte from 0xFFFFE8 |
| `MainLoop` | `0xEF1245` | Main event loop entry |
| `INTT1_HANDLER` | `0xEF0BF9` | Timer 1 interrupt (SYSTEM_TIMESTAMP) |
| `SC0Init_Entry` | `0xFCF890` | MIDI serial port initialization |
| `Boot_DisplayScreen` | `0xEF05D0` | Boot screen display |

### Sub CPU

| Symbol | Address | Purpose |
|--------|---------|---------|
| Reset Vector | `0xFFFEE0` | Sub CPU entry point (Boot ROM) |
| `InterCPU_Latch_Setup` | `0x020B3B` | DMA and latch configuration |
| `MICRODMA_CH0_HANDLER` | `0x020F1F` | Command dispatcher (DMA interrupt) |
| `MIDI_Dispatch` | `0x034D93` | MIDI message parser/router |
| `Voice_NoteOn` | `0x02CF97` | Voice note-on processing |
| `Voice_CtrlChange` | `0x02A282` | Voice CC processing and dispatch |
| `Voice_LoadFilterTable_Ch` | `0x022071` | Per-channel filter frequency/LPF |
| `DSP_Bytecode_Programs` | `0x03C32E` | DSP effect bytecode interpreter (1,613B) |
| `DSP_ParameterWriteEngine` | `0x03C673` | Real-time DSP parameter update engine |
| `MUTE_AND_HALT` | `0x009360` | Audio mute via PE.0 and halt |

### Inter-CPU Communication

| Symbol | Address | CPU | Purpose |
|--------|---------|-----|---------|
| `Audio_DMA_Transfer` | `0xEF32F4` | Main | Send MIDI to Sub CPU via latch |
| `SubCPU_Payload_Transfer` | `0xEF0620` | Main | Load 192KB payload to Sub CPU |
| `SubCPU_Payload_Verify` | `0xEF06A0` | Main | Verify payload checksums |

## External References

- [TMP94C241 Datasheet](https://www.alldatasheet.com/datasheet-pdf/pdf/47265/TOSHIBA/TMP94C241.html) - CPU specifications
- TLCS-900 Programming Manual — **link unverified**: `https://archive.org/details/toshiba-tlcs900` 404s as of this review (2026-09); see [TLCS-900 Instruction Encoding Reference]({{ site.baseurl }}/tlcs900-instruction-encoding/#references) for unconfirmed candidate replacements
- [LLVM TLCS-900 Backend](https://github.com/ArqueologiaDigital/llvm-project) - Custom LLVM backend for TLCS-900 (corrected from `niclasr/llvm-project`: this was the only page on the site using that name, against ~50 pages naming `ArqueologiaDigital/llvm-project` for the same backend; neither URL is confirmed publicly reachable, so this is an internal-consistency fix, not a verified-live link)
