---
layout: page
title: MAME Branch Review & Roadmap
permalink: /mame-branch-review/
---

# MAME Branch Review & Roadmap

This page lists the KN5000-related branches in the local MAME clone, what is already upstream
(for the KN5000 and the other Technics models), and what the remaining branches would become as
pull requests. See also
[MAME Pull Requests]({{ site.baseurl }}/mame-pull-requests/) for PRs 1--5 in detail.

## Upstream

| Topic                                                                                                                                 | Upstream PR                                          | Local branch                                             |
|---------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------|----------------------------------------------------------|
| LDC CR mapping for TMP94C241 DMA registers                                                                                            | [#14970](https://github.com/mamedev/mame/pull/14970) | `MERGED_kn5000_pr1_ldc_cr_mapping`                       |
| EI/RETI interrupt acceptance shadow                                                                                                   | [#14995](https://github.com/mamedev/mame/pull/14995) | `MERGED_kn5000_pr2_irq_inhibit`                          |
| TMP94C241 DMA subsystem (HDMA + DMAR) + port reads                                                                                    | [#15003](https://github.com/mamedev/mame/pull/15003) | `MERGED_kn5000_pr3_dma_and_port`                         |
| TMP94C241 serial port sub-device                                                                                                      | [#15015](https://github.com/mamedev/mame/pull/15015) | `MERGED_kn5000_pr4_serial`                               |
| KN5000 driver: control-panel HLE, compressed sub-CPU payload in IC19, sub-CPU stubs (tone generator, keybed port, DSP1, waveform RAM) | [#15143](https://github.com/mamedev/mame/pull/15143) | `MERGED_kn5000_pr5_driver_v2`                            |
| Feature presentation demo: 16-bit timer fix, IC21 backup SRAM as NVRAM, IC14 dump correction, INT0 vs micro-DMA                       | [#15878](https://github.com/mamedev/mame/pull/15878) | `MERGED_kn5000_feature_presentation_demo_PR15878`        |
| TEMPO/PROGRAM data wheel                                                                                                              | [#15919](https://github.com/mamedev/mame/pull/15919) | `MERGED_kn5000_tempo_program_wheel_PR15919`              |
| Floppy software list `kn5000_flop` (14 disks); drive type 35dd -> 35hd                                                                | [#16415](https://github.com/mamedev/mame/pull/16415) | `origin/technics-kn5000-flop-softlist` (no local branch) |

Earlier KN5000 and TLCS-900 contributions merged before this series: #12649 (the original
KN5000 driver, 2024-08-17), #12744, #12758, #12902, #13219, #13220 (the TMP94C241 CPU variant),
#13386, #14055, #14068 (the KN5000 extension bus and HD-AE5000), #14181, #14190 and #14558 (the
KN5000 layout).

### Other Technics models

Pull requests for the KN7000 family, the SX-WSA1R and the CPU code they share with other
drivers:

| PR                                                   | Merged     | Topic                                                                                   |
|------------------------------------------------------|------------|-----------------------------------------------------------------------------------------|
| [#15911](https://github.com/mamedev/mame/pull/15911) | 2026-08-23 | ROM records for the SX-KN7000, KN6000, KN6500, KN2400 and KN2600 (`kn7000.cpp`, no CPU) |
| [#16190](https://github.com/mamedev/mame/pull/16190) | 2026-09-19 | `mn10300` disassembler: instruction length on the F4 page                               |
| [#16192](https://github.com/mamedev/mame/pull/16192) | 2026-09-19 | `intelfsh`: `FUJITSU_29LV160B` (MBM29LV160B), with the KN7000 as its consumer           |
| [#16204](https://github.com/mamedev/mame/pull/16204) | 2026-09-21 | SX-WSA1R driver (`wsa1.cpp`)                                                            |
| [#16255](https://github.com/mamedev/mame/pull/16255) | 2026-09-25 | `tmp95c061`: restore the 8-bit timer prescaler taps                                     |
| [#16250](https://github.com/mamedev/mame/pull/16250) | 2026-10-07 | KN7000-family driver and the MN10300 execution core                                     |
| [#16394](https://github.com/mamedev/mame/pull/16394) | 2026-10-11 | KN7000 firmware builds as BIOS options (incl. SP7001), `kn7000_flop` software list      |
| [#16416](https://github.com/mamedev/mame/pull/16416) | 2026-10-13 | `kn6000_flop` software list (KN6000/KN6500)                                             |
| [#16413](https://github.com/mamedev/mame/pull/16413) | 2026-10-14 | Three more `kn7000_flop` disks                                                          |
| [#16220](https://github.com/mamedev/mame/pull/16220) | open       | KN6000 expansion connector and the HD-SX6 board                                         |
| [#16414](https://github.com/mamedev/mame/pull/16414) | open       | `wsa1_flop` software list (WSA1/WSA1R)                                                  |

## Active Branches

These branches contain unmerged work that is being developed toward future PRs. None has an open PR. Their merge-base with `upstream/master` is 2026-03-30, except `kn5000_pr6_on_kn7000base` (2026-07-14) and `kn5000_minimal_tonegen`, `kn5000_tonegen_pcm` and `kn5000_tonegen_combined` (rebased 2026-09-21).

### `kn5000_pr6` --- 18 commits

The most complete active branch, containing the next major batch of driver improvements. Its features, with those that have since reached mainline through other PRs marked:

| Feature                 | Commits | Description                                                                                                                                                      |
|-------------------------|---------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Major driver rework** | 1       | SubCPU payload loading and control panel HLE (both upstream since #15143); keybed integration (not upstream)                                                     |
| **TMP94C241 timer fix** | 1       | 16-bit timer interrupt generation and flip-flop gating (upstream since #15878)                                                                                   |
| **FDC wiring**          | 3       | FDC address mapping, PORT D bit 6, register layout (PC AT), floppy DD->HD fix (the DD->HD fix is upstream since #16415)                                          |
| **UART mode**           | 1       | 8-bit UART TX/RX for TMP94C241 serial channels (enables MIDI)                                                                                                    |
| **MIDI output**         | 1       | Wire TX0 to `midi_port` device                                                                                                                                   |
| **Tone generator**      | 7       | Full `kn5000_tonegen_device` (IC303): PCM playback, pitch/pan/volume, release envelope, linear interpolation                                                     |
| **DSP1 stub**           | 1       | IC311 uPD6383GF-3BA device stub                                                                                                                                  |
| **Timer 0 output**      | 1       | Wires TO0 to FDC Terminal Count -- wrong line, **do not submit**: TC is Port H bit 0, pulsed by `FDC_Pulse_PH0`; timer 0 never runs (kn7000_mame `240a41f`)      |
| **SNS NMI write tap**   | 1       | Boot-time write tap on DRAM `0xFFD4` -- **do not submit**: it caused the "Sound Name Error" bug (see [SNS NMI Emulation]({{ site.baseurl }}/sns-nmi-emulation/)) |
| **Code style**          | 1       | Minor upstream compliance cleanup                                                                                                                                |

**Future PR candidates from this branch:**

- **Tone generator device** --- The tone generator, FDC wiring, UART, MIDI output, and DSP1 stub could be submitted as one cohesive "bring the rest of the peripherals online" PR.
- **SNS NMI / NVRAM** --- Not from this branch: its write tap caused the "Sound Name Error" bug. The replacement is the overlay's modelled POWER switch, which needs no core change and is not yet on any fork branch.

### `kn5000_research_tonegen` --- 26 commits (superset of PR6)

Research branch extending PR6 with experimental tone generator and Feature Demo investigation work:

| Feature | Commits | Status |
|---------|---------|--------|
| All of PR6 | 18 | Base (rebased) |
| ATA INTRQ wiring | 1 | HDAE5000 extension IRQ routing |
| VGA controller docs | 1 | MN89304 VGA findings |
| Tone gen voice hold timer | 1 | Fix timing for missing waveform ROMs |
| SSF slide transitions | 1 + 1 revert | Experimental, reverted (approach didn't work) |
| DSP1 ready signal | 1 | Port H bit 0 connection |
| Demo workaround removal | 1 | Removed stuck-parts workaround (not needed with voice timing fix) |
| Voice timing fix | 1 | Final fix for missing waveform ROM behavior |

**Status**: Research branch. Contains fixes (voice timing, DSP1 ready) that should be cherry-picked onto PR6 when preparing the upstream submission. Its ATA INTRQ -> INT9 wiring has no effect on the firmware, which switches PE.1's INT9 function off (`PEFC = 0x00`) and leaves the INT9 vector at `Empty_Handler`.

### `kn5000_research_datawheel` --- 2 commits, superseded

Two commits: "Add Program data wheel encoder input" and "Fix data wheel to use segment 0x0B
button packets". The second is **wrong** — the wheel is a `[0xD7, signed detent count]` frame on
sub-address `0x17`, not a segment `0x0B` button packet
([Data Wheel]({{ site.baseurl }}/data-wheel-investigation/)). What shipped upstream as
[#15919](https://github.com/mamedev/mame/pull/15919) is the wire-level implementation, so this
branch has no remaining PR value.

### Other local branches

| Branch                                          | Commits ahead | Content                                                                                                                                                                                                                       |
|-------------------------------------------------|---------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `kn5000_pr6_hdae5000`                           | 1             | HD-AE5000: ATA interface with INTRQ to INT9, PPI parallel-port callbacks, boot-hang fix; one commit on `upstream/master`, not on PR6                                                                                          |
| `kn5000_pr6_on_kn7000base`                      | 26            | PR6 plus the `kn5000_research_tonegen` fixes (not the reverted SSF pair), the first data-wheel commit and the control-panel ioport move, rebased onto the KN7000 overlay's base (`upstream/master` `957e9dec1b4`, 2026-07-14) |
| `kn5000_research_techmanager`                   | 9             | TechManager5000: HDAE5000 parallel-port null cable, PC LPT PS/2 bidirectional mode, KN5000↔PC signal path via PPI taps                                                                                                        |
| `kn5000_minimal_tonegen`                        | 5             | Reduced tone-generator variant                                                                                                                                                                                                |
| `kn5000_tonegen_pcm`, `kn5000_tonegen_combined` | 9 each        | Tone-generator variants; the owner's PR plan elects `kn5000_tonegen_pcm` for a partial-tone-generator PR                                                                                                                      |

### `kn5000_power_off_nmi` --- 2 commits

Power-off sequence emulation (alternative approach to PR6's boot-time write tap):

| Feature | Commits | Status |
|---------|---------|--------|
| MACHINE_NOTIFY_POWER_OFF | 1 | New machine notification phase before NVRAM save |
| NVRAM + NMI checksum | 1 | KN5000-specific power-off NMI handler |

**Status**: Superseded. Neither this core phase nor PR6's write tap is needed. The kn7000_mame overlay models the instrument's POWER switch: a machine control pulses `~NMI`, a 100 ms timer lets the firmware's own `NMI_StorePayloadChecksums` run, and only then does MAME exit. That gives NVRAM persistence without touching MAME's core. PR6's write tap is not an alternative: it caused the "Sound Name Error" bug. See [SNS NMI Emulation]({{ site.baseurl }}/sns-nmi-emulation/).

## Retired Branches

Kept only for reference:

| Branch                                            | Original Purpose             | Reason Archived                                              |
|---------------------------------------------------|------------------------------|--------------------------------------------------------------|
| `MERGED_kn5000_pr1_ldc_cr_mapping`                | PR 1                         | Merged upstream                                              |
| `MERGED_kn5000_pr2_irq_inhibit`                   | PR 2                         | Merged upstream                                              |
| `MERGED_kn5000_pr3_dma_and_port`                  | PR 3                         | Merged upstream                                              |
| `MERGED_kn5000_pr4_serial`                        | PR 4                         | Merged upstream                                              |
| `MERGED_kn5000_pr5_driver`                        | PR 5 (original)              | Not merged as such: superseded by v2, which merged as #15143 |
| `MERGED_kn5000_pr5_driver_v2`                     | PR 5 (final version)         | Merged upstream as #15143                                    |
| `MERGED_kn5000_interactive_control_panel`         | PR 5 (identical to v2)       | Merged upstream                                              |
| `ARCHIVED_kn5000_aided_by_claude`                 | Early research branch        | Superseded by PR branches                                    |
| `ARCHIVED_kn5000_pr4_serial_downcast`             | PR 4 downcast experiment     | Superseded by merged PR 4                                    |
| `ARCHIVED_kn5000_pr5_driver_aided_by_claude`      | PR 5 with research additions | Superseded by research branches                              |
| `ARCHIVED_kn5000_research_encoder`                | Data wheel encoder (v1)      | Superseded by datawheel branch                               |
| `ARCHIVED_kn5000_research_encoder_v2`             | Data wheel encoder (v2, WIP) | Superseded by datawheel branch                               |
| `ARCHIVED_kn5000_research_ssf`                    | SSF presentation research    | Identical to tonegen branch                                  |
| `ARCHIVED_kn5000_pr4_serial_to2_trigger`          | TO2 trigger for serial       | Superseded by merged serial work                             |
| `ARCHIVED_kn5000_minor_fix`                       | Old misc fixes               | Superseded by PR 5                                           |
| `ARCHIVED_kn5000_squash_attempt_2025_08_14`       | Early squash attempt         | Superseded by PR branches                                    |
| `ARCHIVED_kn5000_research_tonegen_pre_rebase`     | Pre-rebase snapshot          | Replaced by rebased branch                                   |
| `ARCHIVED_kn5000_research_datawheel_pre_rebase`   | Pre-rebase snapshot          | Replaced by rebased branch                                   |
| `MERGED_kn5000_feature_presentation_demo_PR15878` | Feature presentation demo    | Merged upstream as #15878                                    |
| `MERGED_kn5000_tempo_program_wheel_PR15919`       | TEMPO/PROGRAM data wheel     | Merged upstream as #15919                                    |

## Roadmap: Future PR Candidates

Based on the branch review, the following PRs are planned:

### KN5000 Peripherals (Tone Gen, FDC, UART, MIDI, DSP1)

**Source**: `kn5000_pr6` + cherry-picks from `kn5000_research_tonegen`

> **Plan changed (2026-09-19).** Parts of this now go as separate PRs. The floppy drive type merged in [#16415](https://github.com/mamedev/mame/pull/16415) without the disc-formats line (`default_pc_floppy_formats`), which is still unsubmitted. The partial tone generator would come from `kn5000_tonegen_pcm` and waits on a policy decision. One `/INT0` per pin assertion is a separate TLCS-900 core PR, blocked on one experiment. The control-panel ioport move should go before any PR that extracts the overlay's `kn5000.lay`. The FDC address mapping, the UART mode, MIDI output, the DSP1 device and the FDC Terminal Count (on Port H bit 0, not the branch's TO0 wiring) are not yet in any planned PR.

**Scope**: Bring the remaining KN5000 peripherals online:
- Tone generator device (IC303 TC183C230002) with PCM waveform playback, pitch/pan/volume control
- Floppy disk controller wiring (PC AT register layout, PORT D dskchg)
- 8-bit UART mode for TMP94C241 serial channels
- MIDI output via TX0
- DSP1 device stub (IC311 uPD6383GF-3BA)
- FDC Terminal Count on Port H bit 0, which the firmware pulses in `FDC_Pulse_PH0` (not the branch's Timer 0 output: the firmware never starts timer 0; kn7000_mame `240a41f`)
- The modelled POWER switch from the kn7000_mame overlay (pulse `~NMI`, let the firmware save its own checksums), not PR6's write tap

**Preparation needed**:
1. Cherry-pick confirmed fixes from `kn5000_research_tonegen` (DSP1 ready, voice timing)
2. Squash/rewrite commits for clean history (one topic per commit)
3. Remove AI attribution from commit messages
4. Build-test on current `upstream/master`

### SHARC core contributions (from the KN7000 work)

The KN7000's effects DSP (an ADSP-21065L) drove a series of fixes to MAME's **shared
2106x SHARC core** — they live on the base `adsp21062_device`, so they benefit every
SHARC system in MAME (arcade boards included), not just the Technics drivers. The
series already exists as clean per-fix commits, staged as patch files in
`kn7000_mame/notes/upstream-patches/` and catalogued in
`kn7000_mame/notes/sharc-upstream-patch-series.md`:

| Candidate                                     | Content                                                                                                                                                                                                                             | State                                                                                                                                                 |
|-----------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| Perf: native fixed MAC                        | the DRC never implemented the fixed-point multiply/accumulate family and fell back to the interpreter (~82M fallbacks per 22 s of reverb)                                                                                           | applies cleanly to upstream; **ready**                                                                                                                |
| Perf: native single-function fixed multiplier | the actual hot path (the multi-op MAC turned out unused by the kernel)                                                                                                                                                              | applies cleanly; **ready**                                                                                                                            |
| Perf: native fixed ALU average (op 0x09)      | last big fallback; overflow-free signed average with exact flags                                                                                                                                                                    | applies cleanly; **ready**                                                                                                                            |
| Correctness: `MODE1.ALUSAT` in the recompiler | the DRC compiled fixed-point add/sub as plain wrapping ops where the interpreter honored saturation — a silent recompiler-vs-interpreter divergence for any SHARC program with ALUSAT set (this is what railed the KN7000's reverb) | needs the documented small rebase (depends on one op-0x09 hunk; drop one KN7000-only clock hunk) + a per-patch reverb-WAV A/B                         |
| New device: `adsp21065l_device`               | a 21065L personality of the 2106x core (reset PC `0x8004`, interrupt vectors from `0x8000`, internal SRAM map, SDRAM window) — MAME has no 21065L today                                                                             | vector base, reset offset and external space confirmed against the Technical Reference appendices; the DM windows `0x9800`/`0xC000` remain RE-derived |

All verified bit-identical against the running KN7000 reverb (interpreter == DRC after
the fixes; >99% of interpreter fallbacks eliminated). Submission is under the project
owner's authorship; the apply-tests should be re-run against the current upstream base
before sending. Since 2026-10-08 the series also sits, rebased, on the fork branch
`technics-kn7000-dsp` together with the KN7000 effects-DSP hookup. It has no PR yet and is queued
behind the KN7000 tone-generator PR (`technics-kn7000-tonegen`). One fix in the catalogue, the
circular-buffer wrap off-by-one in both engines, reached upstream independently as
[mamedev/mame#16016](https://github.com/mamedev/mame/pull/16016) (merged 2026-09-25), so it is
not part of the branch.

Also riding with a future KN5000 PR: the control-panel **button ioports moved into
`kn5000_cpanel_device`** (`device_input_ports()`, layout inputtags qualified
`cpanel:...`) — the same boundary cleanup applied to the KN7000 driver, so the panel
device owns its own inputs.

### Future Research Areas

These are not yet ready for PRs but are active research topics:

- **Waveform ROM decoding**: IC307 format has been decoded (see [Waveform ROM Format]({{ site.baseurl }}/waveform-rom-format/)). Remaining waveform ROMs (IC304--IC306) are undumped.
- **DSP emulation**: Mainline maps DSP1 (IC311, uPD6383GF-3BA) as a `noprw()` stub and has no device for DSP2 (IC310, MN19413). The kn7000_mame overlay has an opt-in uPD6383 core (`KN5000_ENABLE_DSP1`) and, in that build, a default-off HLE path (`DSPHLE`) that applies decoded effects to the tone generator's mix (see [Effects DSP]({{ site.baseurl }}/effects-dsp/)). Full emulation requires decoding the DSP bytecode interpreter and register semantics.
- **Feature Presentation demo**: runs in mainline since [#15878](https://github.com/mamedev/mame/pull/15878), silently, because there is no tone generator. That PR needed four fixes: the 16-bit timer, so that INTTR4 (the sequencer clock) fires; IC21 backup SRAM as NVRAM; the corrected IC14 dump; and no INT0 re-assertion while micro-DMA owns it.

## Branch Management Policy

Active branches are rebased onto `upstream/master` before a PR is prepared from them. When preparing a PR:

1. Create a fresh `kn5000_prN_<topic>` branch from `upstream/master`
2. Cherry-pick or rewrite commits from research branches
3. One topic per PR, clean commit history, no AI attribution
4. Test before and after each commit
5. Archive the source research branch with `ARCHIVED_` prefix after the PR is merged

See the [MAME Branch Management policy](https://github.com/ArqueologiaDigital/KN5000/blob/main/CLAUDE.md) for full details.
