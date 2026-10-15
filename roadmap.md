---
layout: page
title: Project Roadmap
permalink: /roadmap/
---

# Roadmap — cataloguing and emulating every Technics keyboard

*Assessment date: 2026-08-14. This page supersedes the forward-looking half of the
[KN7000 Roadmap]({{ site.baseurl }}/kn7000-roadmap/) and the
[KN6000 Roadmap]({{ site.baseurl }}/kn6000-roadmap/), which remain as per-model status pages.*

The goal is a museum catalogue: every Technics keyboard documented at IC level, its ROMs preserved
with honest provenance, and — where the silicon allows — a MAME driver that a stranger can run.
Units arrive one at a time, by purchase, so the plan is built around **what can be done at a desk**
with what is already on disk, and a separate lane that waits for hardware.

**Planning constraint:** no hardware bench time is available in the near term. The KN7000 is owned
but not reachable; KN5000 access is uncertain and may not return for a long time. Everything ranked
below Phase 5 assumes zero physical access.

---

## 1. What "done" means

The project has never defined this, which is why "working" has meant different things on different
pages. Four grades, applied per **model × subsystem**:

| grade | criterion |
|---|---|
| **G0 — structural** | Every register and bit the firmware writes is decoded, or explicitly listed as undecoded. A committed script asserts it, with its expected output recorded. |
| **G1 — behavioural** | The firmware cannot tell. It passes **its own factory service diagnostics inside the emulator**, showing the same values a real unit shows. |
| **G2 — signal** | A committed golden capture with a criterion that *can fail*: a positive control that must differ, a null that must not, and a stated tolerance (pitch ±5 cents, envelope times ±10 %). |
| **G3 — provenance** | No `BAD_DUMP`, synthetic, or donor content anywhere in the path being claimed. |

A model is **done** when every subsystem is G2 and G3.

Two consequences worth stating plainly, because they are unwelcome:

- **G2/G3 for every model is not reachable on any horizon we can plan.** The five MN10300
  machines alone have 30 undumped ROM entries over 22 distinct devices (see the
  [ROM Dumping Roadmap]({{ site.baseurl }}/rom-dumping-roadmap/)). On top of those come the
  KN5000's own waveform trio (IC304/305/306), the SX-WSA1R's six wave mask ROMs and its flash,
  and the unread ranges of the KN5000 sub-CPU boot ROM. The *reachable* programme goal is **every model at G1, with an honest provenance register** saying
  exactly what is missing.
- **"Perfect KN5000 audio" is structurally blocked.** IC304/305/306 hold about 75 % of what the
  instrument's sounds select; they are not dumps at all but placeholder copies of IC307, and unlike
  the KN7000 there is no CPU-side wave readback port. Ranking KN5000 audio work by "how good will
  it sound" ranks against a ceiling that cannot be reached. The 155 instruments that use **only**
  the genuine IC307 are therefore the declared test corpus.

G1 is the grade this project should chase hardest, and it is nearly free: **every one of these
instruments ships a factory diagnostic suite** — ROM checksum, RAM, DSP, device, disk, panel/LED,
crosstalk, sample play, video out, wave ROM. Roughly seventeen self-tests per machine, with the
manufacturer's own pass criteria, and they run *inside* the emulator against the emulated devices.
Today two of them are ever used. A driver that passes its own factory diagnostics is a far stronger
claim than any bespoke rig.

---

## 2. The catalogue

Effort is **per generation**, not per model: once one member of a silicon generation runs, its
siblings are mostly ROM work.

| gen         | years     | CPU                                | members                                                             | status                                                                                                |
|-------------|-----------|------------------------------------|---------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| **G0**      | 1963–83   | none / analogue                    | SX-601, Technitone organs, SX-U series                              | out of scope (document only)                                                                          |
| **G1**      | 1982–84   | unknown                            | SX-K100/K200/K150/K250                                              | research; analogue solo path makes it poor value                                                      |
| **G2**      | 1985–86   | **unknown — the one blocker**      | SX-K300/K350/K450                                                   | ★ best *new-silicon* target: OKI MSM5232 TG is **already in MAME**; needs one new MSM6202 drum device |
| **G3**      | 1987–88   | unknown                            | SX-K500/K700                                                        | first full-PCM Technics; one manual covers both                                                       |
| **G4**      | c.1989–95 | **NEC V25 (µPD70325)**             | **KN1200 confirmed**; KN2000, KN800/600, KN1000/750, KN901, KN3000? | ★★ **an unexplored third of the line.** V25 core is upstream in MAME already                          |
| **G5**      | 1995–97   | **Toshiba TLCS-900**               | KN1500, **KN5000**, **SX-WSA1**                                     | in progress; deepest work                                                                             |
| **G6**      | 1999–2003 | **Matsushita MN10300/AM33** + MILK | KN2400/2600/PR54, KN6000/6500, KN7000/PR804/PR604                   | in progress; 5 machines upstream (mamedev/mame#16250); SX-PR54/PR604/PR804 have no driver             |
| **G-ORG**   | 1988–95   | unknown                            | GX/GN/FN3/EN/GA/EA console organs                                   | ★ proven kinship, zero silicon data                                                                   |
| **G-PIANO** | —         | CPU+ROM                            | SX-PX, SX-PC series                                                 | out of scope for drivers; ROM archival only                                                           |

Seven MAME drivers existed as of this assessment — `kn1500`, `kn5000`, `kn6000`, `kn6500`, `kn2400`,
`kn2600`, `kn7000` — all in the fork, with only `kn5000` upstream. **Since then** an eighth,
`wsa1`/`wsa1r` (`src/mame/matsushita/wsa1.cpp`), was added (2026-08-25), and upstreaming caught
up: the five MN10300 machines were registered as ROM records by mamedev/mame#15911 (2026-08-23)
and became a running driver, with an MN10300 execution core, in #16250 (2026-10-07); `wsa1r`
merged as #16204 (2026-09-21). Only `kn1500` and the `wsa1` keyboard remain fork-only. Every
upstream Technics machine is still `MACHINE_NOT_WORKING`. (SX-PR54 is documented but still has
no driver.)

**Models that do not exist and must not appear in any plan:** KN450 (a confusion with SX-K450),
KN900 (the real number is KN901), KN2100, KN2200, KN4000, KN5500, and **KN8000** — zero hits across
every firmware image, service manual and project note. The SX-KN7000 was the last SX-KN.

---

## 3. The one structural insight: the computer is shared, the audio is not

This reorders everything, and it is now measured rather than assumed.

**The front-panel sub-CPU is the same part across the CPU-architecture change.** Mitsubishi
**M37471M2196S** sits on the TLCS-900 KN5000 *and* on the MN10300 KN2400/KN6500/KN7000, with the
same HD74LS07P buffers beside it, the same two-byte `[ADDR][DATA]` frame, the same "bank bits 7:6
must be 00 or 11" rule, and the *same normalisation formula* `idx = ((ADDR&0xC0)>>1)|(ADDR&0x1F)`
into a 128-entry table — implemented in TLCS-900 machine code on the KN5000 (table `0xEDA03C`) and
in MN10300 machine code on the KN7000 (table `0x486135A0`). Only the table contents differ.

Within G6 the sharing is total: identical `MILK MN10300 Ver1.0R1` banner, identical on-chip I/O map,
and **identical literal-reference counts** across four independently built firmwares (panel RX
`0x34000809` twice in all four; MIDI-2 TX `0x34000828` seven times in all four). That is one
peripheral-driver source recompiled per model.

**And it reaches outside the arranger line entirely.** The SX-WSA1 — an acoustic-modelling synth
with a completely different audio architecture — runs **dual TMP95C061** and shares custom parts
with the KN5000: the **M37471M2196S panel MCU** and the **uPD6383GF-3BA effects DSP**, both read
straight from its parts list. Its panel is scanned the same way, over the same SIN/SOUT link.

A third shared part is the **TC183C230002 tone generator** (IC4 on the WSA1R, IC303 on the
KN5000). The parts-list OCR also printed it as `TC1830230002`, but schematic sheet II-13/II-14
prints the label directly under the IC4 designator and settles it. A physical-modelling synth
therefore carries the KN5000's PCM tone generator, with the modelling LSI feeding it (see
[WSA1 Modelling LSI]({{ site.baseurl }}/wsa1-modeling-lsi/)).

Measured asset sharing (`technics_roms/tools/wsa1_kinship.py`):

| measurement | result | null |
|---|---|---|
| WSA1 16-char tone-name fields also in the KN7000 table ROM | **195 / 252 (77.4 %)** | — |
| KN5000 sub-CPU payload bytes verbatim in the WSA1 | **31,046 B in 588 runs (15.8 %)** | **0 B** on an unrelated ROM |

Where it **breaks down**, and this matters as much: the WSA1 has **no MILK toolkit**, a different
vendor codepage (`¿` = `0xBB` not `0xBF`), a different text engine, an Epson SED1330 mono LCD
instead of the MN89304 VGA controller, and a proprietary disk format. The model is *shared silicon
and shared assets, separate application framework*. The KN1500 sits similarly outside MILK while
still sharing a 1,658-byte Composer data block with the KN5000 — so the **accompaniment data layer
predates the toolkit**.

**The source-tree lineage is legible in the binaries.** Both the KN7000 and the KN2400 carry the
string `Panel Simulator for IK` — the **KN6000's** project code — and no `for JK` exists anywhere.
So the two last-generation models are forks of the KN6000 tree rather than independent branches,
which predicts where their code will agree when the cross-model aligner runs.

**A third-party extension ABI was ported across the CPU change.** Key Soft Service shipped hard-disk
expansions for three generations: HD-MEC 2000 (KN2000), HD-AE5000 (KN5000, TLCS-900 code at
`0x280000`) and HD-SX6 (KN6000/KN6500, **MN10300** code at `0x97800000`). The HD-SX6 image we hold
disassembles as clean MN10300 and its pointer census shows 4,930 references into the KN6000 program
flash — so it **runs on the host CPU**, not a board-local one. The host-side hooks `_TT_HDDEXT` and
`_TT_EXTAPR` are present in the KN7000 and KN2400 too, but their UI is absent. This is a whole
cross-model subsystem the project had not recognised as one.

**Practical consequence:** panel, inter-CPU, storage and asset work should be built as
**cross-model devices and tools from the start**. A parameterised `technics_cpanel_device` would
serve every instrument from 1995 to 2003, including the WSA1.

---

## 4. The programme

### Phase 0 — Custody and truth · *days · do this first*

Nothing else is safe until this is done, because these are the only **unrecoverable** items.

1. **Rescue evidence living outside version control.** `kn7000-emulator/` is not a git repository
   and holds `money.lua` — the reverb/keybed oracle quoted as the regression gate in at least six
   notes — plus the EG sweeps and the DSP unit-role captures. Other load-bearing scripts exist only
   under `KN7000/tmp-dir/`. **✅ Done 2026-08-14**: 95 rigs rescued to
   `kn7000_mame/tools/rigs/`, the KN1500 IC15 dump and the WSA1 OS into `technics_roms`. The
   oracle was re-run — see the re-baselining note below. `KN7000/tmp-dir/` triaged: of 3,252
   scratch files the three named evidence scripts were rescued to `kn5000-roms-disasm/dsp/tools/`;
   two still reproduce and **`h0_verify_effectchipmap.py` is rotted**, so the gate-H0 table and the
   "12 of 12 effects are stubs" figure are currently unreproducible.
2. **Decide the fate of the untracked manuals.** `KN7000/service_manual/` (31 MB, 227 files) holds
   the only copies of the KN7000 service manual **and** the complete KN2400/KN2600 manuals with
   schematics. The KN7000 repo has a *public* remote and these are copyrighted Panasonic documents,
   so they need a local, remote-less home — not a push.
3. **Fix provenance lies.** **✅ Mostly done 2026-08-14.** The three fabricated files
   (`kn5000_waveform_rom.ic304/305/306` — 83.4 % `0xFF` against IC307's 1.3 %) are renamed out of
   chip-name space, `technics_roms/README.md` no longer calls them genuine dumps,
   `extract_kn5000_waves.py` refuses unverified donors by CRC instead of merely labelling them,
   and `publish-binary.sh` now quarantines any `*_rom.ic*` whose **basename and md5** are not both
   in the manifest. **Decided upstream:** mainline `kn6000`/`kn6500` have declared their
   table/font ROMs IC13/IC14 `NO_DUMP` since mamedev/mame#15911 (2026-08-23). Only the fork
   overlay still loads the **KN7000's** table files there as a `BAD_DUMP` placeholder, so that
   text renders.
4. **Correct false completeness claims** on the three pages a newcomer reads first. ✅ **Done.**
   `help-wanted.md` once said all `.byte` code was eliminated (507 `.byte` lines still carried
   instruction comments then; 131 at disassembly `3417969c0`) and all `LABEL_*` symbols replaced
   (35,924 of 39,451 rows were still `LABEL_*`; none are now), and later that every symbol carried
   a semantic name (v10 still has 638 positional names, the SX-WSA1R 568 unnamed `sub_`
   routines); it now states what is open. The tracker dump `issues.md` was retired on 2026-09-04.
5. **Fix the two standing autonomous authorisations. ✅ Done 2026-08-14.** `kn7000_disassembly/tools/coverage_score.py` now
   evaluates expression operands and asserts both that every directive parsed and that source bytes
   per instruction line fall in the 1–7 band MN10300 allows — the first assertion caught a bug in
   the fix itself. History rows annotated, not rewritten. `AUTONOMOUS-STATUS.md` gained a
   current-state header above the July ticks.

**Exit:** no quoted number in the project has an untracked producer; no file misrepresents what it is.

> **Re-baselining the audio oracle (2026-08-14).** `money.lua` was rescued and re-run. It is
> bit-deterministic — two identical runs, identical hash — but **both recorded baselines are stale
> and disagree with each other** (`44b09b9d…` in one note, `c3b67ea7…` in three others); neither
> reproduces. The driver moved under them unnoticed, which is what an unrun gate does. New baseline
> `780de131e33a4a0c99d092b57a074247`, with the invocation and binary identity pinned beside it in
> `tools/rigs/README.md`. It was also checked against the project's own rule that a gate must be
> able to fail: rms **0.0** with no stimulus, **165.7** on the held note, plus a decaying reverb
> tail. It remains a *regression* hash — it says nothing changed, never that anything is correct.

### Phase 1 — Instrumentation · *2–3 weeks*

Build the things that make every later phase checkable. The project's leading cause of retraction is
rig error, and every hard-won rule currently lives as prose in a different file, enforced by nothing.

- **`tools/gate.sh`** — ✅ **built 2026-08-14.** Per model: `-validate`, `-listxml`, `-verifyroms`,
  a liveness probe asserting the machine actually drew a UI, and the `money.lua` oracle against its
  pinned md5. `--static` runs the no-emulator half in seconds. Fault-injected: removing one ROM
  turns that model red and exits 1. Liveness floors were measured per model — and the measurement
  itself is a finding: **kn2400 and kn2600 sit at 4 distinct pixel values against kn5000's 20**,
  and produce an *identical* screen hash, matching their known "renders no text" defect. kn1500 has
  no MAME screen device (SVG/HD44780) so it reports SKIP rather than a misleading FAIL.
  ✅ **Second audio arm added 2026-08-15**: a KN5000 demo-audio oracle, because the gate passed
  16/16 on a KN5000 tone-generator change it structurally could not see — `money.lua` is the wrong
  machine and the KN5000 liveness probe sits at the home screen with no notes playing. It carries
  two fault-injected preconditions (the demo needs `DEMO → LEFT 4 → LEFT 2`, and channel 0 is
  always silent so level is measured on ch1/ch2), each corresponding to a mistake that had already
  been made here. Full run 2026-08-15: **17 passed, 0 failed, 1 skipped.**
  Still to add: wiring it to a cron tick and publishing the result as a committed status file.
- **`tools/rig.sh`** — ✅ **built 2026-08-15.** One entry point for all rigs (117 at the time this
  was written; `tools/gen_rig_index.py` counted 136 later, and 150 on 2026-10-15, as later phases
  added more), encoding the hazards once: absolute rig path, throwaway cfg/NVRAM with a loud
  banner (and `--user-cfg` to reproduce the *user's* environment, per RULE 20), timeout wrapper, visible video, correct skip
  flag, machine inferred from a `rig-machine:` header. It prints the exact command it ran, so a
  number a rig produces can be quoted beside its recipe. Fault-injected: a broken rig exits 1 with
  a named diagnosis (`tools/tests/test_rig_sh.sh`).
  It exists because fourteen rig headers documented a `-autoboot_script tools/rigs/…` path that
  cannot work — `run.sh` cd's to the emulator directory. Alongside it, `tools/gen_rig_index.py`
  indexes every rig from its own header and *counts* header defects rather than estimating them;
  as of 2026-08-15 descriptions missing are **0** (was 20), copy-pasted headers naming another
  script **0** (was 5 — the README had claimed two while listing four).
  Still to add: `rig_lib.lua` for the shared in-Lua helpers, and a run manifest recording binary
  mtime, git HEAD and ROM hashes.
- **A modelled POWER switch** — ✅ **shipped 2026-08-15 (KN5000).** MAME's `schedule_exit()`
  calls `eat_all_cycles()`, so no CPU cycles run after shutdown is scheduled and any firmware
  power-down routine is unreachable — an EXIT notifier also fires after NVRAM is written. The fix
  is to stop using the emulator's exit as the power switch: a machine control pulses the CPU's
  NMI, a timer gives the firmware its power-down window, and only then does `schedule_exit()`
  run. No core change.
  On the KN5000 this **restored the boot splash** with no write tap and no faked checksum: the
  firmware's own handler saves `DRAM[0xF980..0xFFEE]` (which carries the payload checksums) into
  the battery-backed IC21 SRAM, and its own boot code restores it. Verified against a cold-boot
  control — warm shows the colour splash, cold shows "ALL INITIAL SETTING!" — with sound names
  still resolving, so the kn5000-29 fix is not regressed. Gate 17/0/1.
  **Worth reusing:** any model whose firmware has a power-fail routine is in the same position.
  See `kn7000_mame/notes/FINDINGS-kn5000-splash-restored.md`.
- **The service-diagnostic suite** — one Lua driver per model that walks all ~17 factory tests and
  records the firmware's own verdict. Expect and document honest failures: WAVE ROM will report NG
  on the KN7000 (synthetic waves) and the KN5000. That is the point — it converts "which parts are
  honestly emulated" into a per-subsystem verdict the manufacturer defined.
- **A reference-audio oracle** — the single largest untapped hardware-free ground truth. The KN5000
  Feature Presentation demo and the KN7000 factory styles are extensively recorded in public, and
  the emulator renders the *same named songs*. An onset-aligned comparison can settle pan polarity,
  gain reference and EG decay law — all currently parked as "needs hardware". It cannot settle
  waveform identity; say so up front.
- **Save states** — ⚠ **the premise of this item was wrong, corrected 2026-08-15.**
  `kn7000_tonegen.cpp` does have zero `save_item` calls, but it is a thin subclass with no state
  of its own; the shared `kn_tonegen` base where the state actually lives already saved 27
  members. Auditing properly found 14 unregistered of 41, of which most are legitimately exempt
  (the MAME-managed stream, construction-time config, immutable ROM-derived wave tables) —
  **and nine that were a real bug**: the effect-send gains, omitted because they are
  `std::atomic<float>` and `save_item()` cannot register an atomic. They are genuine runtime
  state (the firmware writes all nine from `tg_write`), so a state saved with reverb engaged
  restored with the boot-default mix, silently. ✅ Fixed via `device_pre_save`/`device_post_load`
  shadowing; save/load round-trip verified with `kn7000_regress.lua`, gate still 17/0/1 with both
  audio oracles bit-identical.
  ✅ **All six devices audited 2026-08-15** with `tools/audit_savestate.py`, which compares
  declared members against registrations and annotates devices whose state is shadowed (without
  that it reports the just-fixed gains as still broken). `kn_cpanel`, `kn6000_cpanel` and
  `kn7000_cpanel` are clean. **`kn5000_tonegen` — the KN5000's tone-generator device, which
  exists only in the fork (mainline `kn5000` stubs the tone generator out) — was missing its
  keybed FIFO and its pending-note deque**, the latter being how absolute pitch is recovered at
  all; both now shadowed, gate still 17/0/1 with both audio oracles bit-identical. The remaining
  unregistered members there stay unregistered on purpose: instrumentation counters, and four
  flags set once from environment variables (run configuration, which a save state must not
  carry). `kn5000_cpanel`'s `m_tx_queue` is real but belongs to the CP-serial work that is
  **paused at Felipe's request** — not to be touched unasked.
  Still open: the "25 seconds of boot removed from every experiment" payoff needs a documented
  boot-state snapshot per model before it is real.

**Exit:** a red gate is a bug, not a mystery; a measurement can be repeated by a command.

### Phase 2 — KN5000 audio, root-cause first · *3–5 weeks*

`detect_period()` is the root node and is now fully unblocked. It gates the hand-off decode (which
silences 738 of 1,762 organ note-ons), `compute_loop()`, the IC307 chunk
catalogue, and the shared wave helper the KN7000/KN6000 will reuse. Strict order:

1. Build a period oracle from the firmware's own multisample zone table — **not** YIN, which breaks
   the circularity that stopped the last attempt. Use it as acceptance only, never as a fitting target.
2. Rewrite `detect_period()`, dropping the `peak >= 0.5` gate that rejects a real period at 0.436.
3. Fix the aperiodic fallback and `compute_loop()` (a one-shot currently repeats ~90 times).
4. ~~Flip the hand-off default~~ — **do not**: the `F000` hand-off's low byte is an output level
   of zero, and without the mute the voice the boot leaves gated drones (`kn7000_mame` `af0148a`,
   2026-08-19).
5. **Only then** re-open P9 (the stall at 58 % of the song). P10 (the octave error) is a
   measurement artefact on the keybed path: it compared spectral centroid with a sine reference,
   and a played C4 measures 260.87 Hz, −5 cents (`kn7000_mame` `491148a`). The sequencer path is
   untested.

Deprioritise anything whose acceptance test needs the missing wave banks, and say why in the docs so
an outside reader is not misled.

### Phase 3 — KN7000 desk work · *3–4 weeks, parallel to Phase 2*

- **Felipe's own SD card is banked hardware ground truth needing no hardware.** It holds effect,
  sound, panel-memory, composer and sequencer data written by the real instrument. Load it, read
  back the live parameter blocks, diff against the file bytes — the closest thing to a G1 test the
  KN7000 sound domain can build now. *(Contains personal data — never share the image.)*
- **Decode the user-data formats** (`.SEQ .SQF .CMP .TM .LSW .MSP .PMT .EFC .ACT .SQT`) by reading
  the firmware's own serialisers, not by guessing at bytes. Seven real 1999–2000 user disks sit in
  `floppy-archive/` as loose files. Then close the loop: play a real 1999 song and diff the note-on
  stream against the file's event list — a full-stack test of FDC, filesystem, sequencer and TG.
- **Simulate composite video.** The ROM screen-scraper reads 99.87 % on emulator frames and commits
  **zero bytes** on real captures — because it has never seen an NTSC-encoded signal, only a clean
  progressive LCD. Encode, degrade, decode, and find the operating point *before* the instrument is
  reachable. Two calibration pages with fully known answers are already on disk.
- **Build the feature matrix** from the user manual's table of contents: one row per user-facing
  feature (Composer, sequencer record, Music Stylist, One Touch Play, Technichord, Registration,
  pedals, SysEx, GM, metronome), graded per model with the evidence named. Nothing on the site
  currently answers "how much of this instrument works".

### Phase 4 — Upstreaming, continuous · *runs from week 1*

Small, independently-correct PRs beat one large one. Order:

1. ✅ **Done. PR #15878 merged upstream 2026-08-17** (`8789d0f0d48`, "KN5000: Make `Feature
   Presentation` demo run"). The IC14 filename collision resolved toward the PR's flat hash: the
   merge landed `CRC(aa4917ce)` for `kn5000_rhythm_data_rom.ic14` and the fork now carries the same
   hash (with the raw as-dumped bytes kept alongside as `kn5000_rhythm_data_rom.ic14.as-read-a19a21-swapped`,
   regenerable via `tools/kn5000_descramble_ic14.py` — the source comment in `kn5000.cpp` cites
   the path `tools/rom-record-review/ic14_descramble_check.py`, a script in the KN7000 repository
   rather than in kn7000_mame, where the comment sits).
   **Also since merged
   2026-08-31: PR #15919** (`13fd3ea396a`, "kn5000: emulate the TEMPO/PROGRAM data wheel").
2. ✅ **Done.** The one-character `mn10300` disassembler fix merged as #16190 (2026-09-19,
   `6efbfe9427f`).
3. ✅ **Done upstream, not by us.** Curt Coder fixed the `spi_sdcard` CRC16 init in `cb329abc566`
   (2026-09-06); #16394 then added the CSD (CMD9) CRC16.
4. **Promote `mn89304_vga_device`** out of `kn5000.cpp`, where it hides as a driver-local class with
   a live `emu_fatalerror`. It is documented, self-contained and upstream has nothing like it.
   (Still open: it is still a driver-local class in `kn5000.cpp`.)
5. ✅ **Mostly done.** Software lists `kn7000_flop` (#16394, extended by #16413), `kn5000_flop`
   (#16415) and `kn6000_flop` (#16416) are merged; `wsa1_flop` is open as #16414. Every image is
   labelled a FAT12 reconstruction, never a dump.
6. ✅ **Moot.** The ROM-record PR merged as #15911 (2026-08-23), and mainline `kn7000.cpp` now
   declares update-disk payloads as program and table ROMs.

Gate PR 8a/8b (tone generator) on a written verdict for each of the 27 `getenv` switches. One of
them deletes held notes; per the project's own RULE 20 a diagnostic of exactly that kind cost a day
of contradicting the owner about organ sustain.

### Phase 5 — Siblings and the nearly-free models · *2–3 weeks*

Build the **cross-model code aligner** first — relocation-tolerant byte-pattern matching across N
program images, emitting an address-correspondence table. Four separate lanes describe this same
technique as their method, and it is the highest-leverage cross-model artefact available.

Then: **SX-PR54** (a clone of kn2400; its firmware *is* the KN2400 image, selector documented), and
**SX-PR604/PR804** once the KN7000's selector RAM address is located. Caveat: the cabinets genuinely
differ — 88 weighted keys, different panel, video out on the PR804 — so a clone entry that silently
reuses the KN keybed would be a cosmetic lie even though the ROM sharing is real.

### Phase 6 — Opening the NEC generation · *months*

The V25 era is a third of the product line and nobody has touched it. The CPU core is **already
upstream in MAME**; the uPD72068 FDC is a uPD765 relative. The whole cost is the **uPD93083 tone
generator**, which has no datasheet and must be reverse-engineered from firmware register writes —
exactly as was done for the MN10300 line. The KN1200's service manual is free and complete, and its
self-diagnostic makes the wave ROM emit a **sine wave**: a built-in audio oracle.

Two service-manual purchases resolve the entire generation boundary: **KN3000** (which is the
KN5000's direct firmware ancestor — untranslated `KN3000` strings survive in the KN5000's Spanish,
German and French catalogues where the English reads KN5000) and **KN2000**.

### Phase 7 — WSA1, and the organs · *months, gated on research*

**⚠ Update: this phase started 2026-08-25**, after the 2026-08-14 assessment date above — a
`wsa1`/`wsa1r` driver (`src/mame/matsushita/wsa1.cpp`) with LCD, inter-CPU link and CPU2
register-file work boots to the real `SOUND MODE` screen. The rack, `wsa1r`, has been upstream
since mamedev/mame#16204 (2026-09-21), with placeholder sine sound; the keyboard, `wsa1`, stays in
the fork; see
[wsa1-emulation]({{ site.baseurl }}/wsa1-emulation/) for the milestone-by-milestone state. The
framing below (written when this was still unstarted) is kept for its still-valid reasoning about
*why* WSA1 was a good target.

The WSA1 was the best-prepared unstarted target in the project: its **full 2 MB v2.0 OS is in
hand** and verified, its service manual is free, its CPU is one we already emulate, and three of its
custom chips are parts we have already reverse-engineered. Budget it as a new *application*, not a
new architecture. MAME already has a SED1330 device for its display.

★ **The WSA1 has already widened the KN5000's DSP decode.** It drives three of the same uPD6383
chips, its effect microcode disassembles under the same instruction-set model (48 distinct program
bodies in `wsa1/dsp/disasm/` since 2026-09-07; see [Effects DSP]({{ site.baseurl }}/effects-dsp/),
§8), and the [decode state of play]({{ site.baseurl }}/upd6383-decode-status/) is measured over
the pooled KN5000 + WSA1R corpus. Its ROM holds real bodies for SLOW ATTACKER, PITCH SHIFTER,
PEDAL WAH and PEDAL WAH+DELAY, four of the twelve named effects that the KN5000 points at its one
shared NO OPERATION program. (ROTARY SPEAKER is not among them: on the KN5000 it shares one
program with ROCK ROTARY.) The shared container and instruction set are now demonstrated
(kn5000-roms-disasm `d28b3bf8e`, 2026-09-06): the WSA1R's `prom_c` program words (5,777) use the
KN5000's container and field layout and decode under its uPD6383 model at 34.48 %, against
38.53 % on the KN5000 itself and nulls of 0.03–0.40 %. Whether the WSA1's programs for those
named effects would be usable on the KN5000 is still not demonstrated.

The console organs (GN7/GN9/FN3) cannot be emulated — no CPU, no dumps, 100 kg instruments — but a
**format-analysis pass is possible today with zero new material**, because the KN keyboards
hard-code the organs' sequencer capacity limits in a string both the KN5000 and KN7000 carry.

---

## 5. The parked-hardware lane

About twenty items need physical access, currently scattered across nine documents in inconsistent
formats — at least one with a defect that would void the take. **Write
`notes/HARDWARE-VISIT-PROTOCOL.md` now, not when access returns**, one file per instrument, ordered
by what each item unblocks, each with: exact setup, exact takes *including the mandatory negative
control*, the pre-registered prediction with the artefact that computed it, and the acceptance
criterion that would make the take void.

★ **Corrected:** the KN2400/KN2600/PR54 family has **no separate table/font ROM**; its
schematics, board assembly drawings and block diagrams show none. The firmware reads
`0x48000000` 164,300 times from t=0.84 s, all between t=0 and t=6, then never again, and those
reads go to the other, never-read 4 MiB half of the IC12/IC13 program-flash pair
(`C3FBNG000007`), which on the KN7000 holds the table data. That half belongs in the undumped
inventory. (The experiments below were run on the same region and stand as written.)

⚠ **The causal half of that entry was wrong, and is corrected here (2026-08-15).** It said the
empty region is why "text renders as solid blocks while icons draw correctly". Four measurements
say otherwise — see `kn7000_mame/notes/FINDINGS-kn2400-table-rom.md`:

* the region *is* copied into RAM at boot (loop at `0x4860C274`, 40 records × 712 B, destination
  99.86 % `0xFF`), but holding those buffers overwritten across the compositing paint leaves the
  frame **bit-identical** to a control — while poking the framebuffer itself changes it, so the
  test can succeed;
* the routine that paints the panel (`0x485EC9D6`) reads work RAM 550,901 times and this region
  **zero** times, and its input is **0.0 % `0xFF`**;
* substituting the whole region with `0x00` changes read traffic by 68 % — so the firmware really
  does parse it — yet leaves the screen bit-identical;
* dumping and rendering the 320×240 UI plane shows **solid rectangles already drawn where text
  belongs**, and the routine drawing them is a fill primitive that takes its colour as a parameter
  and reads no bitmap at all.

So the sharper statement is: **the KN2400 draws its text boxes and never draws a single glyph
pixel into them.** The plane holds 5 distinct byte values against the KN7000's 45 for the same
architecture. The ROM is undumped and functionally live, and dumping it remains a real win — but
it is not established that it is what withholds the text, and no constant substitution restores
it. What that experiment *cannot* show is what a genuine dump would do: `0x00` is no more a valid
ROM image than `0xFF`.

Highest-value parked items: re-dump **IC14** (should hash to `aa4917ce`); dump **IC304/305/306**
(~75 % of KN5000 sounds, the largest single audible defect); re-read **KN1500 IC15** (lane census
shows 8.5 % vs 54.3 % `0xFF` — against 0.8 %/1.9 % on the known-good IC307); the KN7000 build-893
camera sweep; and the KN5000 sub-CPU boot ROM's two undumped ranges.

**Cheapest acquisitions, ranked by information per euro:** the KN3000 service manual; the KN2000
service manual; the combined SX-K300/K350/K450 manual (the one missing part number for the best
new-silicon target); a **SY-EW65NX** board — the retail KN6000→KN6500 upgrade kit, which likely
carries the KN6500-only wave pair on a bench-readable PCB instead of requiring a donor instrument;
and any gen-03 PR update disk, which would settle a whole generation by checking for the MILK banner.

---

## 6. What we ask of other owners

Every terminal blocker is somebody else's chip, and no one has written the ask. Four contributions
cost a stranger minutes and are worth months here:

1. **A photograph of the service-mode ROM DEVICE TEST screen** — a free per-device checksum oracle
   for any model, including ones nobody here owns.
2. **Raw images of original Panasonic disks** (a PC task, not bench time).
3. **Any unrecognised `.SLD`/`.AST` payload** from a dealer CD. Every model carries a two- or
   three-letter **project code** that keys its update-file names, its container magic from the
   KN6000 on (the KN5000's is still `SLIDE4K`) and its user-data file signature, and, up to the
   KN6000, its internal `Panel Simulator for <code>` string (the KN7000 and KN2400 still say
   `for IK`, see §3) — `HK` = KN5000, `IK` = KN6000/KN6500, `JK` = KN7000, `LKG` =
   KN2400/KN2600/PR54, `LKE` = KN1500 — so magics read `IKPRG4K`, `JKPRG4K`, `LKGP14K`. **An unfamiliar project code is a fingerprint of a model nobody has catalogued.**
4. **A TMP94C241F hardware manual**, and any datasheet for the uPD6383 or uPD93083.

Panasonic's own `TECHNICS.HDD` enumerates twelve KN6000 update payload classes, and **six are types
we have never located** — Table, Rhythm and Wave-Expansion among them. Panasonic itself says those
were field-distributable: a zero-risk software route to several currently "undumped" mask ROMs.

---

## 7. Dead ends — do not retry

- **The uPD6383 decode campaign must not be on the critical path.** It was parked on 2026-08-01
  at 38.53 % ALU decode. The pooled KN5000 + SX-WSA1R corpus reopened it in September: by a
  different measure, distinct microcode words decoded, 80.8 % were decoded on 2026-09-15, with a
  costed, hardware-free route to 95.2 %
  ([µPD6383GF Decode — State of Play]({{ site.baseurl }}/upd6383-decode-status/)). In the
  emulator, though, the device is *compiled out by default* and runtime-gated off; `run_frame()` discards every frame unless decode is total; 44 filed dead
  ends; the output stage is a proven null — "not starved, not connected". Even a perfect IC311 is
  capped, because **IC310 (MN19413), which the entire main mix passes through, is not emulated at
  all**. Keep the cheap hygiene items and the never-run acceptance test T5; drop the kernel-A
  forward-gain hunt and the base-0x90 falsifier. (The SRC 0x00 adjudication was done in any case:
  `SRC 0x00` reads `mem[ptr]`, anchored on 2026-09-13; see
  [Effects DSP]({{ site.baseurl }}/effects-dsp/), §3.) Redirect that budget to IC310, where a few
  days of desk work buys a first-order gain on the whole mix.
- **The "~93.3 % decode ceiling"** is a misread of a stale diagnostic line. It is not a real number.
- **The PR804 CD-ROM** contains no firmware — PC drivers, an MSI and 100 score PDFs. Closed.
- **The `EA5` string** in our firmware is an interleaving artefact; zero hits in any merged image.
  Likewise the apparent `WSA` hits in KN ROMs are coincidence — the real WSA1 kinship was found by
  other means.
- **Never scan split even/odd ROM halves with `strings`.** It shreds every string and returns a
  confident-looking negative. This produced the false claim that the KN6000/KN6500 lack the MILK
  banner — it is present at `0x487F77E8` / `0x48781448`.

---

## 8. Maintaining this page

Every numeric claim here should carry the command that produced it. Where this page and a
measurement disagree, the measurement wins and this page gets corrected in the same commit —
including in the direction that makes the project look less finished. The three most valuable
things published in the last month were retractions.
