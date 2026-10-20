---
layout: home
title: Home
---

![Technics KN5000]({{ "/assets/images/hero-banner.jpg" | relative_url }}){: .hero-banner }
<small style="display: block; text-align: center; margin-top: -1rem; margin-bottom: 1rem; color: #666;">Technics KN5000. Photo: [Sound On Sound](https://www.soundonsound.com/reviews/technics-kn5000) (April 1998)</small>

# Technics Keyboards — Reverse Engineering & Preservation

Welcome to the technical documentation for the reverse engineering and digital
preservation of **Technics musical keyboards**. Our long-term goal is to preserve
the history of these instruments — their internal architecture, firmware, and
protocols — as the physical hardware becomes scarce.

> **A Digital Archaeology Project**
>
> This project preserves technical knowledge of Technics keyboards through
> detailed reverse engineering. As physical hardware becomes scarce, accurate
> documentation ensures these instruments remain accessible for emulation,
> repair, and homebrew development.

## The Instruments

| Instrument                                                           | Year     | Main CPU                         | Documentation                                                                                                                                                                                                                                                                                                                                                     |
|----------------------------------------------------------------------|----------|----------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **[Technics SX-WSA1]({{ site.baseurl }}/wsa1/)**                     | **1995** | Toshiba TLCS-900 (TMP95C061 ×2)  | New — **the 61-key synthesizer**; the images are a redistributed set and running them in *both* variants rests on the uploader's testimony. **No SX-WSA1 service manual is in hand**, so its panel rests on the ROM alone                                                                                                                                         |
| **[Technics SX-WSA1R]({{ site.baseurl }}/wsa1/)**                    | **1995** | Toshiba TLCS-900 (TMP95C061 ×2)  | New — **a synthesizer module, not an arranger**: rack-mount "acoustic modelling". Firmware images are second-hand, not our dumps; all four EPROM images rebuild byte-identically from source with no verbatim blobs; MAME driver upstream (mamedev/mame#16204) reaches a UI; **placeholder sine sound only** (the wave ROMs are undumped)                         |
| **[Technics SX-KN1500]({{ site.baseurl }}/kn1500/)**                 | 1996     | Toshiba TLCS-900 (TMP95C061)     | New — the KN5000's CPU lineage; program ROM a **confirmed bad dump** (four 256 KiB blocks have their odd bytes displaced, so it never boots; IC15 needs a re-dump), but its LCD-panel SVG is preserved as a ROM asset; MAME skeleton in the fork only                                                                                                             |
| **[Technics SX-KN5000](#technics-kn5000)**                           | 1997     | Toshiba TLCS-900/H2 (TMP94C241F) | Extensive — nine ROM images rebuild byte-identically from source, MAME driver, homebrew SDK                                                                                                                                                                                                                                                                       |
| **[Technics SX-KN6000]({{ site.baseurl }}/kn6000-hardware/)**        | 1999     | Panasonic MN10300 (MN103002A)    | New — firmware extracted, hardware mapped from the service manual, MAME driver upstream (mamedev/mame#16250; not working, no sound); about two-thirds of its strings shared with the KN7000 program                                                                                                                                                               |
| **[Technics SX-KN6500]({{ site.baseurl }}/kn6000-hardware/)**        | 2001     | Panasonic MN10300 (MN103002A)    | New — firmware extracted, hardware mapped from the service manual, MAME driver upstream (mamedev/mame#16250; not working, no sound)                                                                                                                                                                                                                               |
| **[Technics SX-KN7000]({{ site.baseurl }}/kn7000/)**                 | 2002     | Panasonic MN10300 (MN103002A)    | MAME driver upstream (mamedev/mame#16250: LCD, panel, floppy, SD and MIDI; no sound there); the project's overlay plays the wave ROMs read from a real unit through the emulated effects DSP; our own programs run on a real unit from the SD card; four program builds selectable as BIOS options (#16394; v1.4 upper half only); firmware disassembly under way |
| **[Technics SX-KN2400 / KN2600]({{ site.baseurl }}/kn2400-kn2600/)** | 2003     | Panasonic MN10300 (MN103002A)    | New — MAME drivers upstream (mamedev/mame#16250; not working, no sound); the KN7000's closest sibling (one firmware serves KN2400/KN2600/PR54)                                                                                                                                                                                                                    |

These instruments span **two CPU architectures** — the earlier TLCS-900 group
(**SX-WSA1/WSA1R**, KN1500, KN5000) and the **MN10300 family (KN2400, KN2600, KN6000,
KN6500, KN7000)** — yet all descend from a **single evolving source codebase**: the same
update-disk container format (`.SLD`/LZSS), the same MILK UI-framework symbol conventions,
resource tables and message text recur across the arrangers (the KN6000 shares about two-thirds of its
strings with the KN7000).

**The SX-WSA1 pair is the odd one out, and the most informative.** It is a
*synthesizer*, not an arranger — its specification page has no rhythm, style or
auto-accompaniment row at all — and it **predates the MILK framework entirely**. What it shares with the KN5000 instead is
its CPU family, its RTOS, its panel driver and **32,795 bytes of literal machine
code** (against a measured null of zero). See the
[Shared Codebase Map]({{ site.baseurl }}/technics-shared-codebase/) and the
[cross-version diff guidebook]({{ site.baseurl }}/cross-version-diff-guidebook/)
for the comparison across the family.

## Project Goals

| Goal                     | Description                                                    |
|--------------------------|----------------------------------------------------------------|
| **ROM Reconstruction**   | Create buildable source code that produces byte-identical ROMs |
| **MAME Emulation**       | Full system emulation in the MAME framework                    |
| **Homebrew Development** | Enable custom software development for the hardware            |
| **Compiler Development** | LLVM backend for TLCS-900/H2, enabling C/C++ development       |

---

## Technics KN7000

The **[Technics SX-KN7000]({{ site.baseurl }}/kn7000/)** (2002) is the successor
to the KN5000. Its update-disk format and firmware images are decoded, four program
builds are preserved (v1.4 upper half only, v1.5, v1.6 and the SP7001 PLUG-iN build),
and its MAME driver is upstream. The driver is not yet working and makes no sound.

| Page                                                                         | Description                                                                                              |
|------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------|
| [KN7000 Overview]({{ site.baseurl }}/kn7000/)                                | Hardware summary, MN10300 CPU, memory map, project status                                                |
| [KN7000 System Update Discs]({{ site.baseurl }}/kn7000-system-update-discs/) | `.SLD` container format, LZSS decompression, `.INF` checksums, extraction tool                           |
| [KN7000 Firmware Images]({{ site.baseurl }}/kn7000-firmware/)                | Program & table flash layout, version numbers, string/hardware inventory, byte-exact disassembly project |
| [KN7000 Image Gallery]({{ site.baseurl }}/kn7000-image-gallery/)             | 169 images extracted from the firmware (demo slideshows, product photos, digital-drawbar UI graphics)    |
| [Techni-chord (auto-harmony)]({{ site.baseurl }}/kn7000-technichord/)        | Proof that the auto-harmony feature is pure firmware, not a tone-generator capability                    |
| [Effects DSP Algorithm Catalog]({{ site.baseurl }}/kn7000-dsp-algorithms/)   | Every ADSP-21065L program identified — kernel, 72 effect algorithms, GUI names as ROM fact               |
| [Panel Design Language]({{ site.baseurl }}/kn7000-design-language/)          | The control panel as a kit of injection-moulded parts — the design system behind the layout artwork      |
| [Shared Codebase Map]({{ site.baseurl }}/technics-shared-codebase/)          | Cross-model code/data reuse between the KN5000, the KN7000 and the SX-WSA1                               |
| [Roadmap (vs KN5000)]({{ site.baseurl }}/kn7000-roadmap/)                    | What was done for the KN5000 and how each piece maps onto the KN7000                                     |

---

## Technics KN5000

The **Technics SX-KN5000** (1997) is the most thoroughly documented instrument on
this site: a 1997-era professional arranger keyboard whose firmware, protocols
and hardware have been reverse engineered in depth.

**New to the KN5000?** Begin with the [System Overview]({{ site.baseurl }}/system-overview/) to understand how all the components work together.

<div style="text-align: center; margin: 2rem 0;">
<a href="{{ site.baseurl }}/system-overview/" style="background: #0366d6; color: white; padding: 0.75rem 1.5rem; text-decoration: none; border-radius: 4px; font-weight: bold;">View System Overview</a>
</div>

## KN5000 Documentation by Topic

### Hardware & Memory

| Page                                                               | Description                              |
|--------------------------------------------------------------------|------------------------------------------|
| [System Overview]({{ site.baseurl }}/system-overview/)             | Architecture diagram and subsystem guide |
| [Hardware Architecture]({{ site.baseurl }}/hardware-architecture/) | Physical components from service manual  |
| [CPU Subsystem]({{ site.baseurl }}/cpu-subsystem/)                 | TMP94C241F dual-CPU design               |
| [Memory Map]({{ site.baseurl }}/memory-map/)                       | Complete address space layout            |

### Subsystems

| Page                                                                          | Status     | Description                                                                                             |
|-------------------------------------------------------------------------------|------------|---------------------------------------------------------------------------------------------------------|
| [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/)          | Documented | Serial protocol for buttons, LEDs, encoders                                                             |
| [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/)                        | Documented | DSP effects, tone generation, voice management                                                          |
| [Effects DSP (NEC uPD6383GF)]({{ site.baseurl }}/effects-dsp/)                | Documented | IC311 effects processor — chip, instruction word, decoded EQ/reverb, 50-effect parameter catalogue      |
| [Effects-DSP Flowcharts]({{ site.baseurl }}/effects-dsp/flowcharts/)          | Documented | Signal-flow Mermaid diagrams — the shared kernel + 38 effect microprograms, synced from the disassembly |
| [µPD6383GF Unofficial Datasheet]({{ site.baseurl }}/upd6383-datasheet/)       | Documented | Pinout, memories, host interface and instruction set of a chip NEC never documented                     |
| [µPD6383GF Decode — State of Play]({{ site.baseurl }}/upd6383-decode-status/) | Documented | 80.8 % decoded: what is left, what has been ruled out, and the cost-ranked route to 100 %               |
| [Keybed Scanning]({{ site.baseurl }}/keybed-scanning/)                        | Documented | Hardware key scanning, note encoding, held-key map                                                      |
| [Display Subsystem]({{ site.baseurl }}/display-subsystem/)                    | Documented | Framebuffer layout, palette, VGA registers                                                              |
| [Storage Subsystem]({{ site.baseurl }}/storage-subsystem/)                    | Documented | Floppy, flash, Table Data ROM, HDAE5000                                                                 |
| [MIDI Subsystem]({{ site.baseurl }}/midi-subsystem/)                          | Documented | 26-channel voice routing, CC handlers, SysEx                                                            |
| [UI Framework]({{ site.baseurl }}/ui-framework/)                              | Documented | 550+ widget handlers, event system, drawing API                                                         |
| [Sequencer]({{ site.baseurl }}/sequencer/)                                    | Documented | 16-track engine, ring buffer, style system                                                              |

### Protocols

| Page                                                                   | Description                       |
|------------------------------------------------------------------------|-----------------------------------|
| [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/)   | MCU serial communication          |
| [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/)           | Main/Sub CPU latch protocol       |
| [HDAE5000 Disk Interface]({{ site.baseurl }}/hdae5000-disk-interface/) | IDE/ATA and PC parallel port      |
| [HDAE5000 Filesystem]({{ site.baseurl }}/hdae5000-filesystem/)         | Custom filesystem and lyric files |

### Firmware Analysis

| Page                                                                                      | Description                                                          |
|-------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| [Boot Sequence]({{ site.baseurl }}/boot-sequence/)                                        | Power-on to ready state                                              |
| [SubCPU Payload Loading]({{ site.baseurl }}/subcpu-payload-loading/)                      | LZSS decompression, E1 bulk transfer, DMA investigation              |
| [Sub CPU Payload Transfer]({{ site.baseurl }}/boot-sequence/#subcpu_send_payload-details) | 192KB firmware loading mechanism                                     |
| [ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/)                              | Disassembly progress                                                 |
| [Source Code Map]({{ site.baseurl }}/source-map/)                                         | Guide to every source file in the disassembly                        |
| [FDC Subsystem]({{ site.baseurl }}/fdc-subsystem/)                                        | Floppy disk handlers                                                 |
| [Feature Demo & Presentation System]({{ site.baseurl }}/feature-demo/)                    | SSF XML scripting, demo assets, planned-but-unshipped floppy loading |
| [Floppy Security Analysis]({{ site.baseurl }}/floppy-security-analysis/)                  | Code injection vectors via crafted update discs                      |
| [HDAE5000]({{ site.baseurl }}/hdae5000/)                                                  | Hard disk expansion firmware                                         |
| [Firmware v9 vs v10]({{ site.baseurl }}/firmware-v9-vs-v10/)                              | Detailed comparison of the last two firmware releases                |

### Homebrew

| Page                                                       | Description                                                         |
|------------------------------------------------------------|---------------------------------------------------------------------|
| [Playing Games on MAME]({{ site.baseurl }}/playing-games/) | Step-by-step guide to running homebrew games in the emulator        |
| [Another World VM]({{ site.baseurl }}/another-world-vm/)   | Full game port: bytecode VM, polygon rendering, input, frame timing |

### Resources

| Page                                                           | Description                                                   |
|----------------------------------------------------------------|---------------------------------------------------------------|
| [Image Gallery]({{ site.baseurl }}/image-gallery/)             | 56 extracted graphics (42 main CPU, 5 HDAE5000, 9 table data) |
| [ROM Strings]({{ site.baseurl }}/rom-strings/)                 | Extracted text resources                                      |
| [Reverse Engineering]({{ site.baseurl }}/reverse-engineering/) | Methodology and strategies                                    |
| [Help Wanted]({{ site.baseurl }}/help-wanted/)                 | Contribution guide                                            |
| [Open Questions]({{ site.baseurl }}/questions/)                | Unsolved mysteries                                            |

## Learning Paths

Choose based on your goal:

### MAME Emulation Development
1. [System Overview]({{ site.baseurl }}/system-overview/) - Understand the architecture
2. [Hardware Architecture]({{ site.baseurl }}/hardware-architecture/) - Physical components
3. [Memory Map]({{ site.baseurl }}/memory-map/) - Address space
4. [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) - HLE for buttons/LEDs

### Homebrew Development
1. [Playing Games on MAME]({{ site.baseurl }}/playing-games/) - Get the emulator running first
2. [CPU Subsystem]({{ site.baseurl }}/cpu-subsystem/) - TMP94C241F programming
3. [Memory Map]({{ site.baseurl }}/memory-map/) - Available resources
4. [Display Subsystem]({{ site.baseurl }}/display-subsystem/) - Graphics output
5. [Another World VM]({{ site.baseurl }}/another-world-vm/) - Full game port example
6. [Help Wanted]({{ site.baseurl }}/help-wanted/) - Tool development needs

### Reverse Engineering Research
1. [ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/) - Current progress
2. [Reverse Engineering]({{ site.baseurl }}/reverse-engineering/) - Techniques
3. [Open Questions]({{ site.baseurl }}/questions/) - Areas needing investigation
4. [Help Wanted]({{ site.baseurl }}/help-wanted/) - Specific tasks you can pick up

## Project Status

### ROM Reconstruction Progress

**Thirteen ROM images rebuild byte-identically from source** — nine KN5000 and four
[SX-WSA1R]({{ site.baseurl }}/wsa1-disassembly/), 12,386,304 bytes, gated together by
`make gate-all` after every commit. Built with a custom
[LLVM TLCS-900 backend](https://github.com/felipesanches/llvm-project/tree/tlcs900_backend)
(the disassembly currently needs `tlcs900_backend` at `a3a81863f87d`, which has not yet been
pushed to that branch).

| Component                  | Size       | Rebuild        | Verbatim debt                                 |
|----------------------------|------------|----------------|-----------------------------------------------|
| Main CPU Program (v10, v9) | 2MB each   | byte-identical | **0**                                         |
| Main CPU Program (v7)      | 2MB        | byte-identical | 6,591 B                                       |
| Sub CPU Payload            | 192KB      | byte-identical | **0**                                         |
| Sub CPU Boot ROM           | 128KB      | byte-identical | **0**                                         |
| Table Data                 | 2MB        | byte-identical | **0** real (six genuine BMPs the tool counts) |
| Custom Data                | 1MB        | byte-identical | **0**                                         |
| HDAE5000 ROM               | 512KB      | byte-identical | **0**                                         |
| SX-WSA1R `prom_a`–`prom_d` | 512KB each | byte-identical | **0**                                         |

*Byte-identical means identical to the dump files we hold. For the sub-CPU boot ROM that
file is a `BAD_DUMP`: 89% of IC30 was never read and is present in the file as assumed
`0xFF`. See [Sub-CPU Boot ROM (IC30)]({{ site.baseurl }}/subcpu-boot-rom/).*

*Rebuilding is not the same as understanding. Of the same bytes, **96.34 %** are code, data
whose header states what it is and cites the evidence, or verified filler — the data
census's strict grade on 2026-10-06 (95.04 % after the September 25 semantic push, up from
64.15 %; part of the later rise comes from a 2026-10-06 change in how one-line table blocks
inherit their header, so the two figures are not strictly comparable). The grade is
keyword-based, and its hand-audited error sample predates the push and has not been
redrawn. That covers the twelve distinct images; the thirteenth gated image is a compressed
re-encoding of the sub-CPU payload. Measured by `scripts/analysis/data_range_census.py`; see
[how much of the data is actually explained]({{ site.baseurl }}/rom-reconstruction/#how-much-of-the-data-is-actually-explained).*

*The disassembly's README also carries a measured **semantic score** (`make semantic-score`):
95.54 % on 2026-10-06 (KN5000 95.93 %, SX-WSA1R 92.62 %), the mean of four components —
bytes understood (96.34 %), semantic names (92.57 %), jump tables resolved (100 %, 3,021 of
3,021) and C fields named (93.25 %, KN5000 only). As the README puts it, byte-match says
nothing about progress.*

### Homebrew Development

A [homebrew SDK]({{ site.baseurl }}/hdae5000-homebrew/) is available for writing custom HDAE5000 extension ROMs. Features a Quick Start guide, C + assembly build pipeline, and a fully playable [Minesweeper game](https://github.com/ArqueologiaDigital/Mines/tree/kn5000_port/platforms/kn5000) as a working example.

### MAME Emulation

| Component     | Status                                                                                                                                                                                                |
|---------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| MAME Driver   | upstream in mamedev/mame; further work staged as a queue of follow-up PRs — see [MAME Branch Review]({{ site.baseurl }}/mame-branch-review/)                                                          |
| Display       | 320x240 LCD working (VGA controller emulated)                                                                                                                                                         |
| Audio         | No sound in mainline (`MACHINE_NO_SOUND`: tone generator, keybed and effects DSP are stubs there); the fork overlay adds a tone-generator HLE (`MACHINE_IMPERFECT_SOUND`)                             |
| Control Panel | Protocol documented, button state arrays emulated                                                                                                                                                     |
| MIDI          | Fork overlay only (mainline wires no MIDI ports)                                                                                                                                                      |
| HDAE5000      | Extension ROMs (HD-AE5000 firmware, homebrew) load and run in mainline; its IDE/ATA disk is a stub there, so disk access needs the fork overlay                                                       |
| Floppy        | Software list `kn5000_flop` (14 reconstructed disks) and a 1.44 MB drive in mainline (mamedev/mame#16415), but the FDC is not yet mapped into the CPU's address space there; the fork overlay maps it |

## Quick Links

- [Service Manual PDF]({{ site.baseurl }}/service_manual/technics_sx-kn5000.pdf) (26MB, EMID971655 A5) - Schematics, board layouts, IC pinouts
- [GitHub: ROM Disassembly](https://github.com/ArqueologiaDigital/technics-roms-disasm) - Source code
- [GitHub: Mines (KN5000 port)](https://github.com/ArqueologiaDigital/Mines/tree/kn5000_port/platforms/kn5000) and [GitHub: Another World](https://github.com/felipesanches/kn5000-anotherworld) - Homebrew games (the earlier [kn5000_homebrew](https://github.com/felipesanches/kn5000_homebrew/) holds firmware-customisation scripts and early assembly demos)
- [MAME Pull Requests]({{ site.baseurl }}/mame-pull-requests/) - the KN5000 pull-request series; current upstreaming state is on [MAME Branch Review]({{ site.baseurl }}/mame-branch-review/)
- [Discussion Forum](https://forum.fiozera.com.br/t/technics-kn5000-homebrew-development/321)
- [Firmware Archive](https://archive.org/details/technics-kn5000-system-update-disks) - All versions (v5-v10, HD-AE5000 updates)
- [Keysoftservice HDAE5000 Page](https://www.keysoftservice.ch/hdae5000-e.htm) - Original HDAE5000 information

## About This Project

**Project Lead**: Felipe Sanches | [Arqueologia Digital](https://github.com/ArqueologiaDigital)

This documentation is developed with AI assistance from [Claude Code](https://claude.ai/code). Content is checked against the firmware, the service manuals and the emulator; where a claim rests on real hardware, or is still unverified, the page says so. Contributions and corrections are welcome via GitHub issues.

We believe preserving technical knowledge of instruments like the Technics KN5000 and KN7000 is essential for cultural heritage. Our long-term goal is to preserve the history of Technics musical keyboards as a whole. If you find errors or have additions, please contribute.
