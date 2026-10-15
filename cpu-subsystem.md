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
│  │ Program ROM: 2MB          │  │     │  │ Boot ROM: 128KB (IC30)         │  │
│  │ @ 0xE00000-0xFFFFFF       │  │     │  │ @ 0xFE0000-0xFFFFFF            │  │
│  └───────────────────────────┘  │     │  └────────────────────────────────┘  │
│                                 │     │                                      │
│  ┌───────────────────────────┐  │     │  ┌────────────────────────────────┐  │
│  │ DRAM: 1MB                 │  │     │  │ Payload: 192KB                 │  │
│  │ @ 0x000000-0x0FFFFF       │  │     │  │ (loaded at boot from Main)     │  │
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

| Peripheral | Description                                                                   |
|------------|-------------------------------------------------------------------------------|
| RAM        | 2 KB on-chip, at `0x000400-0x000BFF`                                          |
| Timers     | 4 × 8-bit (T0–T3) and 4 × 16-bit (T4, T6, T8, TA; two compare registers each) |
| Serial     | 2 channels (SC0, SC1), UART or I/O-interface mode                             |
| DMA        | 4-channel MicroDMA                                                            |
| Interrupt  | Multi-level interrupt controller                                              |
| I/O Ports  | Multiple 8-bit ports                                                          |
| ADC        | 10-bit ADC (optional)                                                         |

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

| Address Range     | Size  | Description                                                                       |
|-------------------|-------|-----------------------------------------------------------------------------------|
| 0x000000-0x0003FF | 1KB   | Special Function Registers                                                        |
| 0x000400-0x000BFF | 2KB   | On-chip RAM (takes priority over the external DRAM below)                         |
| 0x000000-0x0FFFFF | 1MB   | Work DRAM — 2 × 4 Mbit at IC9/IC10 on CS3, **volatile**                           |
| 0x110000-0x11FFFF | 64KB  | Floppy Disk Controller                                                            |
| 0x120000-0x12FFFF | 64KB  | Floppy DMA acknowledge (**not** the inter-CPU latch)                              |
| 0x140000-0x14FFFF | 64KB  | Inter-CPU Latch (IC22/IC23)                                                       |
| 0x150000-0x150003 | 4B    | Audio/mixer register file (address 0x150000, data 0x150002)                       |
| 0x130010-0x13002F | 32B   | HDAE5000 ATA (the firmware uses 0x130010-0x13001E and device control at 0x130020) |
| 0x160000-0x160007 | 8B    | HDAE5000 PPI                                                                      |
| 0x170000-0x17FFFF | 64KB  | VGA Controller                                                                    |
| 0x1E0000-0x1FFFFF | 128KB | Battery-backed SRAM (1 Mbit, IC21) — the only persistent RAM                      |
| 0x200000-0x27FFFF | 512KB | HDAE5000 SRAM (only with the board fitted)                                        |
| 0x280000-0x2FFFFF | 512KB | HDAE5000 ROM                                                                      |
| 0x300000-0x3FFFFF | 1MB   | Custom Data Flash (IC19)                                                          |
| 0x400000-0x7FFFFF | 4MB   | Rhythm Data ROM (IC14)                                                            |
| 0x800000-0x9FFFFF | 2MB   | Table Data ROM                                                                    |
| 0xE00000-0xFFFFFF | 2MB   | Program ROM                                                                       |

See [Memory Map]({{ site.baseurl }}/memory-map/) for complete details.

> **This map is software-defined and it changes once during boot.** The TMP94C241 decodes
> external addresses through six programmable chip-select blocks; the table above is the
> state *after* the bootloader's `MSAR2 := 0x80` handover store. Before it, the table-data
> ROM occupies the top of memory and the program flash sits at `0x800000`. See
> [TMP94C241 Memory Controller]({{ site.baseurl }}/tmp94c241-memory-controller/).

### Firmware Structure

The 2MB Main CPU ROM is organized as:

| Component          | Description                                                                                                                                                              |
|--------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Reset handler      | `RESET_HANDLER` at 0xEF03C6; the first-stage bootloader hands over at `Boot_InitIOPorts` (0xEF050F). The CPU's own reset entry, 0xFFFEE0, is the table-data bootloader's |
| Interrupt Vectors  | Exception handlers                                                                                                                                                       |
| Boot Code          | Hardware initialization                                                                                                                                                  |
| Subsystem Handlers | UI, MIDI, FDC, etc.                                                                                                                                                      |
| Data Tables        | Fonts, graphics, strings                                                                                                                                                 |

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
addresses are `PD = 0x34`, `PE = 0x38`, `PG = 0x40`, `PZ = 0x68`.

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

**Port G is the pedal port, and its pins are active low.** `PanelInput_ScanPedalPorts`
(`v10/maincpu/audio/audio_control_engine.s:2093`, reached from `PanelInput_Poll`)
reads `PG` three times per periodic tick: bits 3:2 are shifted down and stored as the foot
switch byte at DRAM `0x8EB6`, and bits 7:4 are shifted down and stored as the foot
controller byte at `0x8EBA`. The polarity is not an inference — the firmware's own idle
test is `cp a, 0xf` on the upper nibble, so **all four high means nothing is engaged**, and
a released panel reads `0xFC`. When the test matches, the firmware arms a 500-count
debounce at `0x8EC8` and skips the write. The routine's auto-generated name is misleading;
its body is a foot-switch and foot-controller scan.

**PE.0 gates the HD-AE5000's PPI set-up, not its detection.** On the normal boot path,
`Boot_FlashAndExtensions` (`v10/maincpu/kn5000_v10_program.s:1343`) tests
`bit 0, (PE:8)` (SFR 0x38) and skips `HDAE5000_Parport_Setup` when it reads 1; when it reads
0 — and the region code is not 4 — it calls it, which programs the uPD71055 PPI. The
extension ROM itself is found without PE.0: `ScreenGroup_ReInit` ends in
`Xapr_DetectAndCallBootInit` (`v10/maincpu/factory_test/test_init.s:546`), which compares
`XAPR` at `0x280000` and calls `0x280008` whenever it matches. The boot programs
`PECR = 0x20`, so PE.0 is an input and the strap is genuinely external.

**Port E is programmed twice, and the second write is the operative one.** Early boot
writes `PECR = 0x20`, which on its own would make PE.5 the port's only output. On the
unconditional path that follows, `CPanel_InitHardware`
(`v10/maincpu/ui/cpanel_routines.s:95-98`, reached from `kn5000_v10_program.s:1357` through
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

| Address Range                        | Size  | Description                                                                                                                   |
|--------------------------------------|-------|-------------------------------------------------------------------------------------------------------------------------------|
| 0x000400-0x000BFF                    | 2KB   | On-chip CPU RAM (bypasses the external bus)                                                                                   |
| 0x000000-0x0FFFFF                    | 1MB   | Work DRAM — 2 × 4 Mbit at IC28/IC29                                                                                           |
| 0x002B00-0x002B1F                    | 32B   | Ring buffer control (MIDI message queue from Main CPU)                                                                        |
| 0x000400-0x0004FF, 0x00F000-0x03EEFF | 192KB | Payload RAM (loaded from Main CPU at boot; see [Payload Image Extents]({{ site.baseurl }}/memory-map/#payload-image-extents)) |
| 0x100000-0x10FFFF                    | 64KB  | Tone Generator hardware registers                                                                                             |
| 0x110000-0x110003                    | 4B    | Tone generator keybed data (+0) / status (+2)                                                                                 |
| 0x120000                             | 1B    | Inter-CPU communication latch (`0x140000` on the main CPU's bus)                                                              |
| 0x130000-0x130003                    | 4B    | DSP1-associated register block (4 channels; address at 0x130000, data at 0x130002) — not the uPD6383GF host interface         |
| 0xFE0000-0xFFFFFF                    | 128KB | Boot ROM                                                                                                                      |

### Boot Process

1. Sub CPU starts from reset vector in Boot ROM (0xFFFEE0)
2. Initializes DMA and serial for the latch (`INIT_DMA_SERIAL`, 0xFF85AE, in the boot ROM; the payload later runs its own `InterCPU_Latch_Setup`, 0x020C15)
3. Receives 192KB payload from Main CPU via DMA transfer
4. Meanwhile the Main CPU compares checksums of its own DRAM at 0xF180 and 0xF980 with the values the power-off NMI saved at 0xFFD4/0xFFD2 (`SubCPU_Payload_Verify`; despite the name it reads nothing that was sent to the Sub CPU — see [SNS NMI Emulation]({{ site.baseurl }}/sns-nmi-emulation/))
5. Jumps to payload entry point
6. Enters audio processing main loop

### Firmware Components

| Component       | Size  | Status                                                                                                                                                                                                                                                                                         |
|-----------------|-------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Boot ROM (IC30) | 128KB | 100% byte-match, and zero verbatim debt. ⚠ **Only 14,336 of the chip's 131,072 bytes (10.9%) have ever been read** — the other 116,736 bytes are `0xFF` standing in for undumped content, and only 4,352 bytes of the file are not `0xFF` — so "100% covered" is true over a 10.9% denominator |
| Payload (v1.42) | 192KB | 100% byte-match, zero verbatim debt                                                                                                                                                                                                                                                            |

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

| Sub CPU (v1.42, named from the code)                 | Main CPU (v10 label)                                     | aligned run                                |
|:-----------------------------------------------------|:---------------------------------------------------------|:-------------------------------------------|
| `TaskSched_SpawnTask`                                | `Show_ScreenGroup` (0xEF1B9C)                            | 63 B at +32                                |
| `TaskSched_ExitCurrentTask`                          | `SndTable_ByteBlock_ReadOps_Helper` (0xEF1C16)           | 20 B at +29                                |
| `TaskSched_PreemptiveYield`                          | `TaskSched_YieldToQueue`                                 | 63 B at +21                                |
| `TaskSched_Block_Self` — blocks the **calling** task | `TaskSched_Resume` (0xEF1CEC)                            | 56 B at +15                                |
| `TaskEvent_Signal` / `TaskEvent_Wait_SuspendTask`    | `TaskSched_SignalEvent` / `TaskSched_WaitForEvent_Block` | 38 B / 30 B                                |
| `TaskSem_Release` (semaphore V)                      | `Audio_Lock_Release` (0xEF1F0F)                          | 44 B at +39                                |
| `TaskSem_Release_WakeWaiter`                         | `AudioLock_Release_WakeWaiter`                           | 16 B at +56                                |
| `TaskSem_TryDec` / `TaskSem_GetCount`                | `AudioLock_TryAcquire` / `AudioLock_GetCount`            | 22 B / 26 B                                |
| `TaskMsgQ_Send` / `TaskMsgQ_Receive`                 | `TaskMsg_Send` / `TaskMsg_Receive`                       | 41 B at +37 and 54 B at +102 / 39 B at +23 |

So **`Audio_Lock_Acquire` / `Audio_Lock_Release` are the kernel's generic semaphore P/V
routines**, not an audio-specific lock. Their "lock index" is a semaphore number. The audio
command path happens to use semaphore 7 (see
[Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/#lock-mechanism)).
`Show_ScreenGroup` spawns a task. `TaskSched_Resume` puts the calling task to sleep
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
- A DSP1-associated register block at 0x130000 (address) / 0x130002 (data); the uPD6383GF itself is loaded over port PZ with port-7 strobes
- 4 channels at a 0x20 register stride: 8 data registers at channel × 0x20 + 0x10 (`DSP_Write_Channel`, 0x01FCDE) and one more at channel × 0x20 + 0x1F (`DSP_Init_Channels`, 0x01FC95)
- Bytecode interpreter `DSP_BytecodeInterpreter_Init` (0x03C259); six native opcode handlers (1,613 bytes) from 0x03C32E
- Real-time parameter updates via `DSP_ParameterWriteEngine` (0x03C9E6)
- See [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) for DSP details

**Hardware I/O:**
- Port E bit 0: cleared by the NMI handler `MUTE_AND_HALT` (0x01FBF4) just before it halts; read as an active-low mute, which the source records as an assumption
- Parallel port (P7/PZ): DSP command/data protocol for effect program loading
- DMA Channel 0: Inter-CPU latch data transfer (interrupt-driven)

## Inter-CPU Communication

The CPUs communicate via one pair of hardware latches (IC22/IC23), which the Main CPU addresses at 0x140000 and the Sub CPU at 0x120000. The Main CPU sends MIDI-like command streams to the Sub CPU for audio synthesis control.

### Transfer Mechanism

| Component         | Main CPU              | Sub CPU                           |
|-------------------|-----------------------|-----------------------------------|
| Latch Address     | 0x140000              | 0x120000                          |
| Transfer Function | `sendCOMM` (0xEF32F4) | `MICRODMA_CH0_HANDLER` (0x020F1F) |
| Direction         | Main → Sub (primary)  | Sub → Main (status/ack)           |

### Data Flow

1. Main CPU writes MIDI-like messages to the latch at 0x140000 (0x120000 on the Sub CPU's bus)
2. Sub CPU's MicroDMA Channel 0 fires interrupt on data arrival
3. `MICRODMA_CH0_HANDLER` dispatches received bytes to command parser
4. Bytes accumulate in ring buffer at 0x2B0D
5. `MIDI_Dispatch` processes complete messages from the ring buffer

### Payload Transfer (Boot Only)

At boot, the Main CPU transfers the 192KB Sub CPU payload via the same latch:

| Function                | Address  | CPU  | Purpose                                                                                 |
|-------------------------|----------|------|-----------------------------------------------------------------------------------------|
| `SubCPU_Send_Payload`   | 0xEF068A | Main | Send 192KB payload                                                                      |
| `SubCPU_Payload_Verify` | 0xEF092B | Main | Compare DRAM 0xF180/0xF980 checksums with 0xFFD4/0xFFD2 (misnomer: not a payload check) |

These are not payload checksums: the power-off NMI (`NMI_StorePayloadChecksums`) stores checksums of Main CPU DRAM 0xF180 and 0xF980 at 0xFFD4 and 0xFFD2, and they survive power-off in the battery-backed SRAM copy at 0x1E8000.

See [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/) for full protocol details.

## Programming Considerations

### Build System

The project uses **LLVM** with a custom TLCS-900 backend as the authoritative build system for all thirteen gated images:

```bash
# Build the nine KN5000 images (from roms-disasm/); make everything also builds the four SX-WSA1R images
make all
# Certify all thirteen images byte-identical
make gate-all

# Pipeline: llvm-mc → ld.lld → llvm-objcopy → raw binary
llvm-mc -triple=tlcs900 -filetype=obj source.s -o output.o
ld.lld -T linker.ld output.o -o output.elf
llvm-objcopy -O binary output.elf output.bin
```

All nine KN5000 images (Main CPU v10/v9/v7, Sub CPU boot, Sub CPU payload and its recompressed form, Table Data, HDAE5000, Custom Data) and the four SX-WSA1R EPROMs rebuild **byte-identically** against the original dumps (twelve distinct images, 12,386,304 bytes, plus the recompressed payload), checked by `make gate-all`.

The ASL Macro Assembler (used historically) is archived in `archive/asl/`.

### `.byte` Code Elimination

As of March 2026, the LLVM backend encodings that were missing at the time (R+d16, 16-bit
direct, 8-bit direct, F2 immediate stores, etc.) had all been implemented, and the disassembly
repository's own milestone commits describe "all executable code" as converted for that
effort. The repository's `scripts/analysis/audit_byte_code.py` classifier, re-run at disassembly
commit `3417969c0` (2026-10-06), reports 422 `.byte` blocks (22,846 bytes) that llvm-mc can
decode as instructions. 418 of them (22,818 bytes) are in the table data, almost all in
`table_data/style_records.s` (18,270 bytes) and `table_data/tone_database_aux.s` (4,502
bytes): style records and tone-database tables that merely happen to decode. The rest are 3
blocks (12 bytes) in the HD-AE5000 and 1 block (16 bytes) in the sub-CPU boot ROM. The tool
does not scan the main-CPU (v10/v9/v7), sub-CPU payload (v1.42) or SX-WSA1R trees, so it says
nothing about code still held as `.byte` there; see
[Raw Byte Code Elimination]({{ site.baseurl }}/raw-byte-code-elimination/). (The classifier's
"decodable" label means llvm-mc can round-trip the bytes, not that a block is code. Treat the
counts as leads.)

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

| Symbol                                  | Address                                  | Purpose                                                         |
|-----------------------------------------|------------------------------------------|-----------------------------------------------------------------|
| `RESET_HANDLER` (table-data bootloader) | `0x9FFEE0` (seen at `0xFFFEE0` at reset) | CPU entry point                                                 |
| `MainCPU_self_test_routines`            | `0xFB729E`                               | Boot-time self tests (called from `Boot_RunSelfTest`, 0xEF0529) |
| `Get_Firmware_Version`                  | `0xFFFEE5`                               | Read version byte from 0xFFFFE8                                 |
| `MainLoop`                              | `0xEF1245`                               | Main event loop entry                                           |
| `INTT1_HANDLER`                         | `0xEF0BF9`                               | Timer 1 interrupt (SYSTEM_TIMESTAMP)                            |
| `SC0Init_Entry`                         | `0xFCF897`                               | MIDI serial port initialization                                 |
| `Boot_DisplayScreen`                    | `0xEF0620`                               | Boot screen display                                             |

### Sub CPU

| Symbol                         | Address    | Purpose                                                                                                                   |
|--------------------------------|------------|---------------------------------------------------------------------------------------------------------------------------|
| Reset Vector                   | `0xFFFEE0` | Sub CPU entry point (Boot ROM)                                                                                            |
| `InterCPU_Latch_Setup`         | `0x020C15` | DMA and latch configuration                                                                                               |
| `MICRODMA_CH0_HANDLER`         | `0x020F1F` | Command dispatcher (DMA interrupt)                                                                                        |
| `MIDI_Dispatch`                | `0x034D93` | MIDI message parser/router                                                                                                |
| `Voice_NoteOn`                 | `0x02CF97` | Voice note-on processing                                                                                                  |
| `Voice_CtrlChange`             | `0x02A282` | Voice CC processing and dispatch                                                                                          |
| `Voice_LoadFilterTable_Ch`     | `0x027534` | Per-channel filter frequency/LPF                                                                                          |
| `DSP_BytecodeInterpreter_Init` | `0x03C259` | DSP effect bytecode interpreter; its six opcode handlers (1,613B) start at `DSP_Bytecode_Op00_Groups5_ParamMix`, 0x03C32E |
| `DSP_ParameterWriteEngine`     | `0x03C9E6` | Real-time DSP parameter update engine                                                                                     |
| `MUTE_AND_HALT`                | `0x01FBF4` | NMI handler: clears PE.0 (read as mute), then halts                                                                       |

### Inter-CPU Communication

| Symbol                  | Address    | CPU  | Purpose                                                                          |
|-------------------------|------------|------|----------------------------------------------------------------------------------|
| `sendCOMM`              | `0xEF32F4` | Main | Send MIDI/command data to Sub CPU via latch, in 32-byte chunks                   |
| `SubCPU_Send_Payload`   | `0xEF068A` | Main | Load 192KB payload to Sub CPU                                                    |
| `SubCPU_Payload_Verify` | `0xEF092B` | Main | Check power-down checksums of DRAM 0xF180/0xF980 (misnomer: not a payload check) |

## External References

- [TMP94C241 Datasheet](https://www.alldatasheet.com/datasheet-pdf/pdf/47265/TOSHIBA/TMP94C241.html) - CPU specifications
- TLCS-900 Programming Manual — **link unverified**: `https://archive.org/details/toshiba-tlcs900` 404s as of this review (2026-09); see [TLCS-900 Instruction Encoding Reference]({{ site.baseurl }}/tlcs900-instruction-encoding/#references) for unconfirmed candidate replacements
- [LLVM TLCS-900 Backend](https://github.com/felipesanches/llvm-project/tree/tlcs900_backend) - Custom LLVM backend for TLCS-900 — the commit the disassembly is built with is named in its `TOOLCHAIN_VERSION`. ⚠ As of 2026-10-15 that commit (`a3a81863f87d`) has not been pushed; the public branch stops at `86332721969d` (2026-09-02), 32 commits earlier, and a build of it cannot assemble the current sources.
