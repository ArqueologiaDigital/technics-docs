---
layout: page
title: KN6000 / KN6500 Hardware Architecture
permalink: /kn6000-hardware/
---

# KN6000 / KN6500 — hardware architecture

Reconstructed from the **Technics SX-KN6000** (89-page) and **SX-KN6500**
(142-page) service manuals, cross-checked against the decoded firmware. The
KN6000 and KN6500 are **architecturally the KN7000's siblings** — the same
Panasonic **MN10300** main CPU and the same [MILK application
framework]({{ site.baseurl }}/technics-shared-codebase/) — not the TLCS-900 KN5000. See the
[KN6000/KN6500 roadmap]({{ site.baseurl }}/kn6000-roadmap/) for the preservation plan and its
[four-way code-reuse strategy]({{ site.baseurl }}/kn6000-roadmap/#the-four-way-code-reuse-strategy-the-force-multiplier).

## Main board (board **A**, MAIN)

| Ref                                       | Device                                                                                                                                                                                     | Role                                                                                                                                                                                                                                                                                           |
|-------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **IC4**                                   | **32-bit micro controller — Panasonic MN10300** (**MN103002A** on both models)                                                                                                             | Main CPU. Address bus **A0–A25** (64 MB space), data bus **D0–D31**. Same family as KN7000.                                                                                                                                                                                                    |
| **IC11 / IC12**                           | **PROGRAM ROM (ODD) / (EVEN)** — 16 Mbit flash each (4 MB total)                                                                                                                           | The MAIN CPU program, byte-interleaved on the 32-bit bus. **= `IK1.SLD` + `IK2.SLD` concatenated** — the program update ships as **two floppy parts** (`IK1` = low 2 MB, `IK2` = high 2 MB), so both must be joined to form the 4 MB image. Field-rewritable from a floppy system-update disc. |
| **IC13 / IC14**                           | **Table data ROMs**, 16 Mbit each — KN6000: **PROGRAMMED MASK ROM** `QSIGX3C16008` / `QSIGX3C16007`; KN6500: `C3FBMD000069` / `C3FBMD000068`, pre-programmed parts with a NOR-flash pinout | Built-in style / sound tables. **Not provided by the firmware update discs** (only the program flash is field-updatable), so a physical chip dump is needed to emulate these.                                                                                                                  |
| **IC15**                                  | **RHYTHM DATA ROM**                                                                                                                                                                        | Built-in rhythm/accompaniment pattern data.                                                                                                                                                                                                                                                    |
| **IC18**                                  | **CUSTOM DATA ROM** — 16 Mbit flash                                                                                                                                                        | RHYTHM & ACCOMP data for the RHYTHM-GROUP / CUSTOM function; user COMPOSER data. **Factory-set, and defaulted from the [Initial Data Disk]({{ site.baseurl }}/kn7000-initial-data/) (`idd6000`); user data is lost if the chip is replaced.**                                                  |
| **IC9 / IC10**                            | **DRAM**                                                                                                                                                                                   | Main work RAM.                                                                                                                                                                                                                                                                                 |
| **IC20**                                  | **SRAM**                                                                                                                                                                                   | Battery-backed panel / user state.                                                                                                                                                                                                                                                             |
| **IC304**                                 | **Digital Signal Processor** — `S21065LKS240` (ADSP-21065L, the same part as the KN7000's) (+ **IC305/IC306 SDRAM**)                                                                       | Reverb / chorus / effects DSP with its own SDRAM.                                                                                                                                                                                                                                              |
| **IC213**                                 | **Tone Generator LSI**                                                                                                                                                                     | PCM synthesis engine (KB/KF/KS key buses, WAX/WAY wave buses).                                                                                                                                                                                                                                 |
| **IC205–IC208** (KN6500: **IC205–IC210**) | **64 Mbit WAVE mask ROMs** — four on the KN6000; the KN6500 adds IC209/IC210 (`QSIGX3C64020` / `QSIGX3C64019`)                                                                             | PCM sample data (KN6000 256 Mbit ≈ 32 MB; KN6500 384 Mbit ≈ 48 MB).                                                                                                                                                                                                                            |
| **IC108**                                 | **Color LCD Controller** (+ **IC110 4 Mbit DRAM**)                                                                                                                                         | LCD framebuffer / video RAM; backlight via the **INV** board (board K).                                                                                                                                                                                                                        |
| **IC101**                                 | **Floppy Disk Controller**                                                                                                                                                                 | 3.5″ 2HD/2DD drive.                                                                                                                                                                                                                                                                            |
| **IC107**                                 | Computer-port driver / receiver                                                                                                                                                            | PC / MAC serial (SW-selected).                                                                                                                                                                                                                                                                 |
| —                                         | HDD connector (**CN105**)                                                                                                                                                                  | Optional hard-disk drive.                                                                                                                                                                                                                                                                      |

**`IC18` is the physical confirmation of the "custom-data flash defaulted from the
Initial Data Disk" mechanism** that the KN7000 rhythm-name investigation traced in
software — the built-in/user rhythm data really does live in a flash IC that the
`idd*` disk initialises.

## Emulation status (MAME driver)

Both machines have been emulated in mainline MAME since mamedev/mame#16250 (merged 2026-10-07; their ROM
records came first, in #15911): `kn6000` and `kn6500` in `src/mame/matsushita/kn7000.cpp`, with their own
`kn6000_state` class and machine config, the KN6000 control-panel device and, since #16416, the `kn6000_flop`
software list. In the development driver of the kn7000_mame overlay both **boot to their main PLAY screen** —
the tone/sound-group icon row, the menu bars, and the status bar render. Reaching
the display took **five stacked boot fixes**:

1. The program ROM had to be **assembled from both floppy parts** — an earlier extraction used only part 1,
   leaving the upper 2 MB empty, and the firmware jumps into it.
2. The firmware reads its **library at `0x4C000000` without writing it first, and expects a copy of the program
   ROM there** (unlike the KN7000, which self-loads its library into RAM). What backs that window on the board
   is not established; the driver copies the program flash into it.
3. The boot's single-threaded RTOS **object creation was being preempted by the system tick**, so the tick
   is delayed past it (the CPU reaches a stable state instead of crashing).
4. The **on-chip millisecond timer** (`0x34001080`) had to tick so that the boot's timer delay loops clear and
   the real timer ISR runs. At first a driver stand-in raised **INTC group 7** at 1 kHz. Since 2026-07-20 the
   MN10300 core models the timer (TM5) and the firmware programs it itself, at the true 2.0005 ms period, so
   the stand-in, which ran at double that rate, is retired.
5. The firmware's interrupt trampoline has a **general handler** (slot 0) and a separate **exception/fault
   handler** (slot 1); the driver now routes all maskable interrupts to the general handler instead of the
   fault vector — the old level-based routing had sent the timer IRQ to the fault handler, causing a
   deliberate halt.

The play-screen graphics render correctly once the display format is handled: the KN6000/KN6500 LCD panel
is **RGB555 and mounted rotated 180°** (unlike the KN7000's upright RGB565), so the overlay's shared
`screen_update` reads the framebuffer reversed and decodes 5-5-5 for these models (mainline MAME uses a
separate `screen_update_rgb555` and flags both machines `ROT180`) — giving gray sound-group tiles with real,
upright instrument icons (grand piano, guitars, trumpet, drums) and the correct title/menu colours. Both
machines remain `MACHINE_NOT_WORKING`: the wave ROMs and the IC13/IC14 table ROMs are undumped, so there is no
real sound and no KN6xxx-authentic text. Mainline MAME flags both `MACHINE_NO_SOUND`. In the kn7000_mame overlay
the KN6000's tone generator plays placeholder PCM (`MACHINE_IMPERFECT_SOUND`) and the KN6500 stays silent (see
the [roadmap]({{ site.baseurl }}/kn6000-roadmap/)).

## Front-panel & keyboard sub-processors

Two panel boards, **CPL** and **CPR**, each carry an **8-bit microcomputer** (Mitsubishi
`M37471M2196S`, IC1 and IC10) that scans switches and drives LEDs, reporting to the main
CPU over a serial link. The other boards have no CPU of their own: CPL's microcomputer also
scans LCDL and LCDC, and CPR's scans CPC, LCDR and ROT. (The KN7000 is laid out the same
way: its two panel microcomputers sit on CPL and CPR, and its CPC board has none.) The boards:

| Board | Sub-CPU / role |
|-------|----------------|
| **E — CPL** | `IC1` 8-bit µC + LED driver/buffer; MAIN VOLUME / APC volume pots |
| **G — CPR** | `IC10` 8-bit µC + `IC11` decoder + LED driver; MIC volume |
| **F — CPC** | switches & LEDs |
| **I — ROT** | rotary **data-wheel** encoder (`SW500`) |
| **L/M/N — LCDL/LCDR/LCDC** | LCD-flanking switches & LEDs, contrast |
| **Q/R/S — MKB1/2/3** | keyboard matrix (decoders + diodes) with an **after-touch** sensor |

## Audio path (board **B** FAJ / **C** ASUB)

Tone-generator + DSP output → D/A → equalizer/integrator → power amps → **66 W**
(18 W × 2 mid/high + 30 W bass); speakers 12 cm × 2, 6.5 cm × 2, 14 cm bass.
Jacks: PHONES, FOOT SW 1/2, FOOT CONTROLLER, EXP PEDAL, LINE OUT (R/R+L,L), AUX
IN, COMPUTER, **MIDI IN/OUT/THRU** (photo-coupled), MIC.

## Service diagnostics (test modes)

The service manual documents a built-in **service diagnostic function**: **ROM
device test, RAM device test, WAVE ROM test, SOUND SYSTEM test, Panel SW & LED
test, LCD module test, Floppy save/load test, MIDI in/out test, In & Out
interface test.** These are directly useful for validating an emulator against the
real hardware's self-tests.

## Specifications (from the owner's-manual excerpt)

200 rhythms × 4 variations · 8-part Composer (~13 000-note capacity) · 16-track
sequencer (~40 000 notes, 1/96 resolution) · 20 preset + 3 user + 2 compile
performance-pad banks · 13 × 8 Panel Memory · 3.5″ floppy + optional HDD ·
MN10300 CPU · ~15.4 kg.
