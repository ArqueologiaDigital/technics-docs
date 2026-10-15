---
layout: page
title: KN6000 / KN6500 Roadmap
permalink: /kn6000-roadmap/
---

# KN6000 / KN6500 — preservation plan

> Project-wide planning now lives in the **[Project Roadmap]({{ site.baseurl }}/roadmap/)**.
> This page remains the KN6000/KN6500 status record.

Goal: reproduce, for the Technics **SX-KN6000** and **SX-KN6500**, everything the
project achieved for the [KN5000]({{ site.baseurl }}/system-overview/) and
[KN7000]({{ site.baseurl }}/kn7000-roadmap/) — extraction, ROM reconstruction, a byte-exact
disassembly, symbol recovery, table-ROM asset decoding, and a MAME driver with an
MN10300 CPU core.

The IC-level **[hardware architecture]({{ site.baseurl }}/kn6000-hardware/)** has been recovered from
the *Technics SX-KN6000* (89-page) and *SX-KN6500* (142-page) service manuals —
main CPU **MN10300** (`MN103002A`), program flash `IC11/IC12`, custom-data flash
`IC18` (defaulted from the Initial Data Disk), tone-generator LSI, DSP, four (KN6500:
six) 64 Mbit wave ROMs, and two 8-bit panel sub-CPUs (on CPL and CPR).

## The key discovery: four re-targets of one source tree

Reconnaissance of the KN6000/KN6500 update files (downloaded from the
same ca-software.com source as the KN7000 files) establishes the decisive facts:

| Property              | KN5000               | KN6000                                     | KN6500                           | KN7000                  |
|-----------------------|----------------------|--------------------------------------------|----------------------------------|-------------------------|
| CPU                   | Toshiba **TLCS-900** | **MN10300** ✅                             | **MN10300** ✅                   | **MN10300**             |
| Application framework | **MILK toolkit**     | **MILK toolkit** ✅                        | **MILK toolkit** ✅              | **MILK toolkit**        |
| Firmware container    | LZSS `SLIDE4K`       | **LZSS `.SLD` (`IKPRG4K`)** ✅             | **LZSS `.SLD` (`IKPRG4K`)** ✅   | LZSS `.SLD` (`JKPRG4K`) |
| Initial-data disk     | —                    | **`idd6000` = same files as `idd7000`** ✅ | **`idd6000`** (the same disk) ✅ | `idd7000`               |

Verified this tick:

- **CPU = MN10300**, same as KN7000. The KN6000 program ROM disassembles as clean,
  coherent MN10300 code (`movm` prologues, `ret [regs],size`, `cd/dd` calls — the
  same idioms as KN7000). So the KN6000/KN6500 are the **MN10300 siblings of the
  KN7000, not of the TLCS-900 KN5000.**
- **Same MILK toolkit**: `DefaultClassProc`, `MT_GetModeProc`, `MT_AreYouClassProc`,
  `ObjectProc`, `InheritedProc`, `ResourceProc`, `ResBitmapProc`, … are all present
  — the same reflection-table framework whose `*Proc`/`*Func` tables gave us all
  2,302 KN7000 function names.
- **~85 % source-level reuse with KN7000**: 4,479 of the KN6000's 5,234 distinct
  ≥8-char strings also appear verbatim in the KN7000 ROM (internal symbol names,
  resource names, `MT_*`, `_TT_SDMIXER`, `ConvertStringsEx`, …). But **almost no
  compiled code is byte-identical at the same offsets**. Under a relocation-tolerant
  match the MN10300 siblings do share byte-identical code, moved to different addresses
  (see [KN2400 / KN2600 / PR54]({{ site.baseurl }}/kn2400-kn2600/#cross-model-code-reuse)), so
  understanding transfers, and some machine code does too.

**Consequence:** almost the entire KN7000 toolchain applies to KN6000/KN6500
directly, and a **four-way comparison** becomes a force-multiplier (below).

## What we have (the files)

The ca-software.com download set (self-extracting archives, same layout
as the KN7000 download):

| File                                    | Contents                                                      | Role                                                                                               |
|-----------------------------------------|---------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| `kn6-71.zip`                            | → `kn6-v7-1a.exe` / `-1b.exe` → **`IK1.SLD` / `IK2.SLD`**     | **KN6000 firmware v7.1** — program flash, low half (0x200000) + high half (0x1F7A31), concatenated |
| `kn65-13.zip`                           | → `kn65_v1-3a/b.exe` → **`IKV1.SLD` / `IKV2.SLD`**            | **KN6500 firmware v1.3** — program, low half (0x200000) + high half (0x181691), concatenated       |
| `idd6000.exe`                           | `01ctmini.ast`, `03favini.fav`, `02umdini.md`, `04hpgini.hmp` | Initial-Data disk — **identical file set to `idd7000`**                                            |
| `ca6001-ca6010`, `ca6000p/s`, `scd6000` | style / sound / CA-software modules                           | user-content packs (decode later)                                                                  |
| `ca6tm01/02`                            | test-mode                                                     | service data                                                                                       |
| `ca6fp01-04`, `ca6dim`                  | JPEG slideshows                                               | marketing (not firmware)                                                                           |

Extraction is **already proven**: `kn7000_extraction`'s `lzss` + `kn7000_extract.py`
decoded all four `IK*.SLD` images with the magic `IKPRG4K` unmodified.

## The four-way code-reuse strategy (the force-multiplier)

Because KN5000/6000/6500/7000 are re-targets of **one evolving source tree**, treat
them as a parallel corpus and cross-reference constantly:

1. **Symbol "Rosetta stone".** A function named in KN7000 (from its MILK reflection
   tables) has a counterpart in KN6000/6500 — found not by byte-matching (compiled
   code differs) but by **string/structure matching**: the `*Proc`/`*Func` reflection
   tables exist in every model, so re-run the KN7000 symbol-recovery generically on
   each ROM, then align by name. Names recovered in *any* model propagate to all.
2. **Shared data formats, decode once.** `.SLD`/LZSS, the Initial-Data disk, the
   table-ROM directory, UI bitmaps (palette + `table_bitmaps.py`), the sound/style
   name tables, PAD phrase presets — all are MILK formats. The KN7000 decoders
   (`table_extract.py`, `table_names.py`, `style_names.py`, `pad_names.py`,
   `table_bitmaps.py`) should run on the KN6000/6500 table ROMs with, at most, offset
   tweaks, once IC13/IC14 have been dumped.
3. **Bug/behaviour triangulation.** Open questions on one model (e.g. the KN7000
   rhythm-name resolution, the panel board-decode) can be
   cross-checked against the other three: where three agree and one differs, the
   difference localises the model-specific code.
4. **MN10300 trio first.** For 6000/6500 use **KN7000 as the primary reference**
   (same CPU, same era, closest strings); fall back to KN5000 only for
   framework-level concepts that predate the MN10300 port.

## Transfer table — KN7000 accomplishment → KN6000/6500 plan

| KN7000 accomplishment                                                                  | Reuse for KN6000/6500                                                                                                                                                                                                                                | Work remaining                                                                                                                                                                                                  |
|----------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `.SLD`/LZSS decode → flash images                                                      | ✅ **works unmodified** (magic `IKPRG4K`)                                                                                                                                                                                                            | ✅ checksum-verified 2026-08-02 — KN6000 `SMCKPR1.INF` 16/16 blocks, KN6500 `SMCKPV1.INF` 15/15 (the oracles sit inside the self-extracting `.exe`)                                                             |
| Split table ROM → 84-segment directory + 293 bitmaps + sound/style names + PAD presets | 🔒 blocked — the KN6000/KN6500 table ROMs (IC13/IC14) are undumped and no update disk carries them                                                                                                                                                   | dump IC13/IC14; then re-point offsets and regenerate galleries                                                                                                                                                  |
| MN10300 disassembler (`unidasm -arch mn10300`)                                         | ✅ **works** (verified on KN6000 code)                                                                                                                                                                                                               | —                                                                                                                                                                                                               |
| MN10300 **execution core** (`mn10300.cpp`, incl. `udf00`/`udf07`, interrupts)          | ✅ **reuse the KN7000 core verbatim**                                                                                                                                                                                                                | none for the ISA; only device wiring                                                                                                                                                                            |
| MAME driver (`kn7000.cpp`)                                                             | ✅ **done, without forking, and emulated in mainline MAME since mamedev/mame#16250** — `kn6000`/`kn6500` are `SYST()` entries in the shared `kn7000.cpp`, with their own `kn6000_state` upstream (the kn7000_mame overlay still uses `kn7000_state`) | upstream has no panel artwork, and its tone-generator device decodes the registers but outputs silence; the overlay's `kn6000.lay` and placeholder-PCM synthesis are not upstream; see the status updates below |
| Library at `0x4C000000`                                                                | ❌ **not the KN7000's mechanism**: the KN6000/KN6500 read it without writing it first, and find a copy of the program flash there (what backs the window on the board is not established)                                                            | —                                                                                                                                                                                                               |
| Byte-exact buildable disassembly + `mn10300_asm.py`                                    | 🟢 transfers                                                                                                                                                                                                                                         | regenerate per ROM                                                                                                                                                                                              |
| 2,302 functions named from MILK reflection tables                                      | 🟢 **rerun generically per ROM**, then four-way align                                                                                                                                                                                                | —                                                                                                                                                                                                               |
| Subsystem docs (memory map, boot, panel, test modes)                                   | 🟢 port + diff                                                                                                                                                                                                                                       | model-specific deltas                                                                                                                                                                                           |

## Phased plan

**Phase 0 — repos & scaffolding.** No KN6000/6500-specific repos were forked. The
KN7000 tooling is reused in place instead: `kn7000_extraction`'s decoders (including
the new `name_extract_nul.py`) run directly against the KN6000/KN6500 images, and
`kn6000`/`kn6500` are `SYST()` variants registered inside the existing
`src/mame/matsushita/kn7000.cpp`, reusing `kn7000_state` and the MN10300 core
verbatim — see the transfer table above and the status update below. `make verify`
stays byte-exact and Jekyll keeps building, as for KN7000.

**Phase 1 — extraction & ROM reconstruction.** Decode `IK*.SLD`/`IKV*.SLD`
(done → 4 flash images); verify the `SMCK*.INF` block checksums (done 2026-08-02);
run the table-ROM splitter + `table_names.py`/`style_names.py`/`table_bitmaps.py`/`pad_names.py`
(blocked until IC13/IC14 are dumped); decode `idd6000` (`01ctmini.ast` is raw DEFLATE,
same as `idd7000`). Publish the sound/style-name lists and image gallery.

**Phase 2 — boots in MAME.** ✅ Done in the kn7000_mame overlay (see the status sections
below); the drivers have been emulated in mainline MAME since mamedev/mame#16250. Find each
model's **reset vector / base address** (KN7000 = `0x48400000`) and I/O map by disassembly;
add the models to the KN7000 driver, drop in the MN10300 core, and iterate to first boot
(hardware init → BSS → MILK kernel → library window at `0x4C000000`), reusing the KN7000
interrupt/timer findings.

**Phase 3 — symbol recovery & disassembly.** Run the generic MILK
reflection-table walker to name functions; build the byte-exact disassembly;
recover `CL_*`/`VF_*`/`BD_*` constants. Then **four-way align** names across models.

**Phase 4 — the four-way diff.** Build a cross-model symbol/behaviour map; use it to
resolve each model's open questions and to back-fill KN5000/KN7000 gaps (e.g. the
rhythm-name resolution, panel board-decode). Document the shared framework once, with
per-model deltas.

## Status update (2026-10)

- **Upstream.** `kn6000` and `kn6500` have been emulated in mainline MAME since
  mamedev/mame#16250 (merged 2026-10-07; their ROM records came first, in #15911 on
  2026-08-23), in `src/mame/matsushita/kn7000.cpp`, with their own `kn6000_state` and
  machine config, the `MN103002A` CPU core and the KN6000 control-panel device.
  mamedev/mame#16416 (merged 2026-10-13) added the `kn6000_flop` software list. Both are
  `MACHINE_NOT_WORKING | MACHINE_NO_SOUND`, declare IC13/IC14 `NO_DUMP` and have no panel
  artwork yet. The panel layout, the KN7000 table-ROM placeholder and the placeholder-PCM
  tone generator described below exist only in the kn7000_mame overlay.
- **Open:** mamedev/mame#16220 adds the KN6000 expansion connector and the optional
  HD-SX6 board.

## Status & next steps (updated 2026-07-08)

**Done:** firmware extracted (all four `IK*/IKV*.SLD` images); [hardware mapped from
the service manuals]({{ site.baseurl }}/kn6000-hardware/); **draft MAME drivers built** — `kn6000` and
`kn6500` are registered in the shared `kn7000_mame` tree (reusing `kn7000_state` and
the KN7000 machine config, same verified `0x48400000` program base), build into the
one binary alongside `kn7000`, pass `-verifyroms`, and run their MN10300 firmware at
~140 % speed and — after a five-fix boot investigation (firmware assembly,
library=program-ROM mirror, tick-delay past object creation, on-chip ms-timer as INTC
group 7, and routing IRQs to the firmware's general handler rather than its fault
vector) — **both now BOOT TO THEIR MAIN PLAY SCREEN** (kn7000_mame commit `805cb46`): the
tone/sound-group icon row, menu bars, and status bar render. **[Firmware name inventories extracted]({{ site.baseurl }}/kn6000-names/)**:
KN6000 4,440 strings (1,963 internal MILK GUI symbol names + user-facing style/sound
names), KN6500 4,189 (2,006 symbols) — via the new NUL-walk `name_extract_nul.py`.

**Next:** exploit the recovered **MILK symbol names** for cross-model symbol recovery
(align KN6000/KN6500/KN7000 GUI-resource identifiers → propagate function names); the
boot now reaches the main play screen, so the priority shifts to **dumping the built-in
mask ROMs (IC13/IC14)** — currently undumped; the font descriptors live there, so no
KN6000/KN6500-authentic text can render (the instrument icons come from the dumped program
flash and are real) — plus further peripheral wiring; decode the remaining
table-ROM assets (bitmaps, PAD presets).

## Status update (2026-07-20 ticks)

Substantial work has landed since the section above was last written:

- **`kn5000` now rides in the same binary too** — the earlier MAME genie/`SOURCES` link
  blocker is resolved (naming `kn5000.cpp` and its device `.cpp` files explicitly in
  `SOURCES` was the fix). `-validate` passes for all seven systems
  (kn1500/kn2400/kn2600/kn5000/kn6000/kn6500/kn7000) from one shared tree.
- **KN6000 has its own panel layout in the kn7000_mame overlay** (mainline MAME has no
  KN6000/KN6500 artwork yet), `kn6000.lay`, generated from the SX-KN6000 service
  manual (pp. 5-6) instead of inheriting the KN7000's — the earlier default silently drew
  a KN6000 as a KN7000, mapping every clickable element to the wrong function. Click-through
  verification (POP, PIANO, DISK, PROGRAM MENU, DEMO, …) confirms the KN6000 now opens the
  right screen per button; LED bindings remain unbound (the `[register][bit]` decode isn't
  confirmed yet) and stay dark rather than guess.
- **KN6000/KN6500 share a single tone-generator chip**, unlike the KN7000's two — confirmed
  from the firmware's own TG write primitive (`0x4849465B`). The KN6000's tone-generator
  device is live-verified against captured audio: measured pitch is within 0.01 semitone of
  the true frequency at three test notes (C4/G4/C5). Timbre is still a placeholder sine
  (wave ROMs undumped).
- **KN6500 is a separate story: it emits zero tone-generator writes on a key press.** Its
  voice engine never starts (a boot/enable-gate difference from KN6000, not a decode
  problem), so it stays `MACHINE_NO_SOUND` while KN6000 is `MACHINE_IMPERFECT_SOUND`.
- **The KN6000/KN6500 "table" ROM loads were confirmed to be non-dumps** — their low 1 MB
  is just the program ROM's upper 1 MB reproduced, contributing nothing. They were replaced
  with the KN7000's table ROM (flagged `BAD_DUMP`, with the substitution stated in the driver
  comment) in the kn7000_mame overlay, so the KN6000 play screen renders with real text (part
  names, voice names; the KN6500 screen is unchanged by it) instead of
  blanking; this makes the screen legible but **nothing table-derived on a KN6xxx screen is
  KN6xxx-authentic** — the real fix is still a hardware dump of KN6000's IC13/IC14
  (`QSIGX3C16008`/`QSIGX3C16007`) and KN6500's equivalents (`C3FBMD000069`/`68`).
  Mainline MAME carries no such placeholder: it declares IC13/IC14 `NO_DUMP` for both models.

## More Technics models incoming

The user is supplying more devices for the same consolidated treatment
(a second download set): **KN2400** (`kn24-11.zip`), **KN2600**
(`kn26-11.zip` + `KN2600_CD-Rom.zip`), a **PR804** CD-ROM, and additional KN7000
material (`kn7-14`/`kn7-16` firmware, `KN7000_CD-Rom.zip`, `scd7000`, `idd7000`,
`ca7001`, `custom1/2`). **KN2400/KN2600 are now emulated** — see
[KN2400 / KN2600 / PR54]({{ site.baseurl }}/kn2400-kn2600/) (MN10300/MILK, the KN7000's closest siblings;
one firmware serves KN2400/KN2600/PR54). The PR804 CD-ROM turned out to hold no firmware
(PC drivers, an MSI and score PDFs), and the KN7000 update disks are covered on
[System Update Discs]({{ site.baseurl }}/kn7000-system-update-discs/). Still pending: a `pr54`
clone, once its exact model designation is confirmed.
