---
layout: page
title: System Overview
permalink: /system-overview/
---

# KN5000 System Overview

This page provides a high-level view of the Technics KN5000 keyboard architecture. Use this as your starting point to understand how all the subsystems connect and interact.

## System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         TECHNICS KN5000 SYSTEM OVERVIEW                      │
└──────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐     Serial Bus      ┌──────────────────────────────────────┐
│  CONTROL PANEL  │<───────────────────>│           MAIN CPU                   │
│                 │  SIN/SOUT/CLK       │          TMP94C241F                  │
│  2x M37471M2    │                     │                                      │
│  ├─ 150 Buttons │                     │  Program ROM: 2MB @ 0xE00000         │
│  ├─ 119 LEDs    │                     │  RAM: 512KB @ 0x200000               │
│  └─ 6 Encoders  │                     │                                      │
└─────────────────┘                     │  ┌─────────────────────────────────┐ │
                                        │  │ Subsystem Handlers:             │ │
┌─────────────────┐       Latch         │  │  ├─ UI/Menu System              │ │
│    SUB CPU      │<───────────────────>│  │  ├─ MIDI Processing             │ │
│   TMP94C241F    │  sub 0x120000 /     │  │  ├─ Sequencer                   │ │
│                 │  main 0x140000      │  │  ├─ FDC Controller              │ │
│  Boot: 128KB    │                     │  │  └─ HDAE5000 (if present)       │ │
│  Payload: 192KB │                     │  └─────────────────────────────────┘ │
│                 │                     └──────────────────────────────────────┘
│  Controls:      │                                      │
│  ├─ DSP/DAC     │                                      │
│  └─ Tone Gen    │                     ┌────────────────┴────────────┐
└─────────────────┘                     │                             │
        │                               v                             v
        │                      ┌─────────────────┐           ┌─────────────────┐
        v                      │  FDC            │           │  HDAE5000       │
┌─────────────────┐            │  uPD72068       │           │  Hard Disk Exp. │
│  AUDIO OUTPUT   │            │                 │           │                 │
│                 │            │  @ 0x110000     │           │  ROM: 512KB     │
│  DSP Processing │            │  3.5" Floppy    │           │  RAM: 512KB     │
│  DAC @ 0x100000 │            └─────────────────┘           │  HD: 1.08GB     │
│  L/R Outputs    │                                          │  PPI @ 0x160000 │
└─────────────────┘            ┌─────────────────┐           │  ATA @ 0x130010 │
                               │  LCD DISPLAY    │           └─────────────────┘
                               │                 │                    │
                               │  MN89304        │                    │
                               │  VGA @ 0x170000 │           ┌────────┴────────┐
                               │  320×240        │           │  PC PARALLEL    │
                               └─────────────────┘           │      PORT       │
                                                             │                 │
┌─────────────────┐                                          │  HD-TechManager │
│  TABLE DATA ROM │                                          │  ppkn50.dll     │
│                 │                                          └─────────────────┘
│  2MB @ 0x800000 │
│  Styles, Sounds │
└─────────────────┘
```

## Subsystem Guide

The KN5000 is organized into several interconnected subsystems. Click each link to learn more.

### Processing Units

| Subsystem | Description | Documentation |
|-----------|-------------|---------------|
| **Main CPU** | TMP94C241F (32-bit TLCS-900/H2). Runs the main firmware, handles UI, MIDI, and coordinates all subsystems. | [CPU Subsystem]({{ site.baseurl }}/cpu-subsystem/) |
| **Sub CPU** | TMP94C241F. Dedicated to audio processing - controls the DSP, DAC, and tone generation. | [CPU Subsystem]({{ site.baseurl }}/cpu-subsystem/) |
| **Control Panel MCUs** | 2x Mitsubishi M37471M2 (8-bit). Scan the button matrix, read encoders, drive LEDs. | [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) |

### User Interface

| Subsystem | Description | Documentation |
|-----------|-------------|---------------|
| **LCD Display** | 320x240 color LCD driven by MN89304 VGA controller at 0x170000 | [Display Subsystem]({{ site.baseurl }}/display-subsystem/) |
| **Control Panel** | ~150 buttons, ~119 LEDs, 6 rotary encoders, pitch/mod wheels | [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) |
| **UI Framework** | Menu system, page navigation, parameter editing | [UI Framework]({{ site.baseurl }}/ui-framework/) |

### Audio

| Subsystem | Description | Documentation |
|-----------|-------------|---------------|
| **Audio Output** | DSP processing and DAC at 0x100000, stereo L/R outputs | [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) |
| **Tone Generation** | Sub CPU controls synthesis engine | [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) |
| **MIDI** | Full MIDI In/Out/Thru implementation | [MIDI Subsystem]({{ site.baseurl }}/midi-subsystem/) |

### Storage

| Subsystem | Description | Documentation |
|-----------|-------------|---------------|
| **Floppy Disk** | 3.5" FDD via uPD72068 controller at 0x110000 | [FDC Subsystem]({{ site.baseurl }}/fdc-subsystem/) |
| **HDAE5000** | Optional 1.08GB hard disk expansion | [HDAE5000]({{ site.baseurl }}/hdae5000/) |
| **Table Data ROM** | 2MB of factory styles, sounds, and data at 0x800000 | [Storage Subsystem]({{ site.baseurl }}/storage-subsystem/) |
| **Custom Data** | 1MB flash for user storage at 0x300000 | [Storage Subsystem]({{ site.baseurl }}/storage-subsystem/) |

### Music Features

| Subsystem | Description | Documentation |
|-----------|-------------|---------------|
| **Sequencer** | 16-track MIDI sequencer with recording/playback | [Sequencer]({{ site.baseurl }}/sequencer/) |
| **Style System** | Auto-accompaniment patterns and variations | [Sequencer]({{ site.baseurl }}/sequencer/) |

## Data Flow

### Power-On Sequence

1. **Reset Vector** (0xFFFEE0) - Main CPU starts executing
2. **Hardware Init** - Initialize RAM, peripherals, interrupts
3. **Sub CPU Boot** - Load 192KB payload via `SubCPU_Send_Payload` ([details]({{ site.baseurl }}/boot-sequence/#subcpu_send_payload-details))
4. **Subsystem Init** - Initialize UI, MIDI, FDC, audio
5. **HDAE5000 Detection** - Check for hard disk expansion
6. **Ready State** - Enter main event loop

See [Boot Sequence]({{ site.baseurl }}/boot-sequence/) for detailed analysis, including the [Sub CPU payload transfer mechanism]({{ site.baseurl }}/boot-sequence/#sub-cpu-payload-loading).

### Runtime Event Loop

```
┌──────────────────────────────────────────────────────────┐
│                   MAIN EVENT LOOP                        │
└──────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        v                  v                  v
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ Control Panel │  │     MIDI      │  │   Timers &    │
│   Polling     │  │   Messages    │  │   Callbacks   │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           v
                  ┌───────────────┐
                  │    Event      │
                  │   Dispatch    │
                  └───────┬───────┘
                          │
        ┌─────────────────┼─────────────────┐
        v                 v                 v
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│  UI Updates   │ │ Sound Engine  │ │  Sequencer    │
│  LCD Refresh  │ │  Note Events  │ │  Playback     │
└───────────────┘ └───────────────┘ └───────────────┘
```

### Inter-CPU Communication

The Main CPU and Sub CPU communicate through one pair of memory-mapped latches (IC22/IC23),
which the Main CPU addresses at 0x140000 and the Sub CPU at 0x120000:

| Direction | Mechanism | Purpose |
|-----------|-----------|---------|
| Main → Sub | Write to latch | Send commands, note data |
| Sub → Main | Read from latch | Status, acknowledge |

See [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/) for details.

## Memory Organization

| Address Range | Size | Component |
|---------------|------|-----------|
| 0x000000-0x001FFF | 8KB | Internal RAM (Main CPU) |
| 0x100000-0x10FFFF | 64KB | Audio/DAC Interface |
| 0x110000-0x11FFFF | 64KB | Floppy Disk Controller |
| 0x140000-0x14FFFF | 64KB | Inter-CPU Communication Latch (0x120000 on the Sub CPU's bus) |
| 0x130010-0x130020 | 16B | HDAE5000 ATA Registers |
| 0x160000-0x160007 | 8B | HDAE5000 PPI (Parallel Port) |
| 0x170000-0x17FFFF | 64KB | VGA/LCD Controller |
| 0x200000-0x27FFFF | 512KB | Main RAM |
| 0x280000-0x2FFFFF | 512KB | HDAE5000 ROM |
| 0x300000-0x3FFFFF | 1MB | Custom Data Flash |
| 0x800000-0x9FFFFF | 2MB | Table Data ROM |
| 0xE00000-0xFFFFFF | 2MB | Main Program ROM |

See [Memory Map]({{ site.baseurl }}/memory-map/) for complete details.

## Documentation Status

| Subsystem | Status | Notes |
|-----------|--------|-------|
| Main CPU Firmware | 100% | Byte-perfect match (239,683 native instructions) |
| Sub CPU Boot ROM | 100% | Byte-exact rebuild of a dump that is 97% `0xFF` and 89% never read — see [Sub-CPU Boot ROM (IC30)]({{ site.baseurl }}/subcpu-boot-rom/) |
| Sub CPU Payload | 100% | Complete disassembly |
| Control Panel Protocol | Documented | HLE in progress for MAME |
| HDAE5000 | 100% | ROM complete, protocol documented |
| FDC Subsystem | Partial | Handler identified, needs integration |
| Audio Subsystem | Documented | DSP effects, tone gen, voice management |
| Display Subsystem | Documented | Framebuffer layout, palette, VGA registers |
| MIDI Subsystem | Documented | 26-channel voice routing, CC handlers, SysEx |
| UI Framework | Documented | 550+ widget handlers, event system, drawing API, property types |
| Sequencer | Documented | 16-track engine, ring buffer pipeline, style system, medley playback |

## Learning Paths

Choose your path based on your interest:

### For MAME Emulation Development

1. [Hardware Architecture]({{ site.baseurl }}/hardware-architecture/) - Understand the physical layout
2. [Memory Map]({{ site.baseurl }}/memory-map/) - Address space organization
3. [Boot Sequence]({{ site.baseurl }}/boot-sequence/) - Startup process
4. [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) - Button/LED HLE

### For Homebrew Development

1. [CPU Subsystem]({{ site.baseurl }}/cpu-subsystem/) - TMP94C241F programming
2. [Memory Map]({{ site.baseurl }}/memory-map/) - Available resources
3. [Display Subsystem]({{ site.baseurl }}/display-subsystem/) - Graphics programming
4. [Help Wanted]({{ site.baseurl }}/help-wanted/) - Contribute to tools

### For Reverse Engineering Research

1. [ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/) - Current progress
2. [Reverse Engineering]({{ site.baseurl }}/reverse-engineering/) - Methodology
3. [Open Questions]({{ site.baseurl }}/questions/) - Unsolved mysteries
4. [Help Wanted]({{ site.baseurl }}/help-wanted/) - Where to start contributing

## Related Pages

- [Hardware Architecture]({{ site.baseurl }}/hardware-architecture/) - Detailed component analysis
- [Boot Sequence]({{ site.baseurl }}/boot-sequence/) - Power-on to ready
- [Memory Map]({{ site.baseurl }}/memory-map/) - Complete address space
