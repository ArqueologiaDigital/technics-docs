# 2026-10-24: follow-ups from syncing the site with the repository audit

Left by the session that added `source-tree-inventory.md` and corrected `rom-reconstruction.md`,
`rom-dumping-roadmap.md`, `wsa1-disassembly.md`, `subcpu-firmware-images.md`, `kn7000-firmware.md`
and `kn7000.md` against `technics-roms-disasm/notes/repo-audit-2026-10-24/` (HEAD `14aec1197`).

## Pages to revisit when the 2026-10-24 wave lands

**Done** for the first three rows by the wave-1 sync session (see
`notes/2026-10-24-wave1-sync-followups.md`); the `rom-dumping-roadmap.md` row is still open.

Every one of these pages says, in one sentence, that a wave of work is in progress on the
disassembly repository and is not merged. When it lands, update:

| page                                                   | what changes                                                                                            |
|--------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| `source-tree-inventory.md`                             | v8, sub-CPU v1.41, KN7000 IC18 boot ROM and table 80, KN2400/KN6000/KN6500/HD-SX3 rows; the warning box |
| `rom-reconstruction.md`                                | the v8 row and the sub-CPU paragraph; the gate count (26 today) if new images join `gate-all`           |
| `kn7000-firmware.md`, `kn7000.md`, `kn7000-roadmap.md` | the converted-function counts (561 + 437 today) and the 3.88% figure, after the bulk conversion         |
| `rom-dumping-roadmap.md`                               | the "not yet in mainline MAME" phrasing once the six KN7000 reads are declared upstream                 |

## Symbol-name lint: what `tools/check_doc_symbols.py` still reports, and why it was left

`python3 tools/check_doc_symbols.py --repo ../technics-roms-disasm *.md` reported 957 names
before this session and about 930 after it. The fixed ones were real staleness: the
HD-AE5000 region tables on `hdae5000.md` and `hdae5000-resources.md` quoted labels without
their `HDAE5000_` prefix (`Get_Init_Flag`, `RECORD_TABLE`, `UiObject_PtrTable`, ...), and
`midi-serial-io.md` (`SeqBuf2` for `SeqBuf2_WriteByte`), `music-stylist-database.md`
(`StyleRec_` prefix), `memory-map.md` (abbreviated `HDAE5000_RAM_Sq*` names) and
`kn7000-work-ram.md` (`func_4853397B`, a generator placeholder that is in no symbol file)
each had one. The audit's four named examples (`HDAE5000_FS_Scan_Directory`,
`HDAE5000_File_Delete`, `Audio_SendCommand`, `Audio_InitDMAChannels`) all turned out to be
deliberate history: the first two sit in `hdae5000-filesystem.md`'s "Routines That Were
Misnamed" table beside their current names, and `Audio_SendCommand` is quoted only as
"formerly" on every page that carries it.

What remains falls into these groups. Spot checks found no stale label among them, but they were
not read one by one, and the reviewer of this session found one such case (`cpu-subsystem.md`
quoted `SndTable_ByteBlock_ReadOps_Helper` as if it were live; now marked "formerly"):

1. **Names quoted as history** ("was `X`", "formerly `X`", "until 2026-09-25 named `X`"):
   `boot-sequence.md`, `dsp-name-tables.md`, `feature-demo.md`, `hdae5000.md` (`GFX_DATA_1`,
   `HDAE5000_Display_Init`, ...), `hdae5000-filesystem.md`'s misnamed-routines table,
   `image-gallery.md`, `inter-cpu-protocol.md`, `keybed-scanning.md`, `sound-categories.md`,
   `sound-parameter-protocol.md`, `subcpu-command-format.md`, `tone-generator.md`,
   `wsa1-disassembly.md` (`sub_F0EA9F_Arm`), `wsa1-modeling-lsi.md`, `llvm-semantic-instructions.md`
   and `tlcs900-instruction-encoding.md` (deleted LLVM pseudo-instructions, documented as such).
2. **Identifiers from other code bases**: MAME C++ (`kn5000_state`, `MACHINE_NO_SOUND`, `ROM_LOAD`,
   `m_level`, ...), the site's own Python tools, the Pico wave-tap firmware, the Mines and Another
   World homebrew, Toshiba's cc900 runtime (`original-toolchain.md`), the ASL macro names in
   `rom-reconstruction.md`'s legacy section.
3. **Firmware name-table strings, not labels**: the KN7000 `MT_*`, `EV_*`, `TT_*`, `_TT_*`,
   `Tt*`, `*Proc` and `DefaultWindow` names on the KN7000 pages are strings the firmware carries
   in its reflection tables (they are in `kn7000/baserom/*.rom`, not in `kn7000/*.sym`); the
   KN6000 names on `kn6000-names.md` and `sound-editor-screens.md` come from a model with no tree
   yet; the `_Volume`-style keys on `panel-parameter-keys.md` are parameter-name strings.
4. **Prefix-only mentions** (`Audio_`, `BitMapOut_`, `HDAE5000_RAM_`, `SeqInit_`, ...), which
   the lint cannot match by design, and pattern placeholders (`SeXxxTitleFunc_OnDraw`,
   `LABEL_XXXXXX`, `FDC_SEND_COMMAND` as naming-convention examples on `help-wanted.md`).

**Possible improvement to the lint**, if the noise is worth removing: skip a name when the
same line contains "was", "formerly", "until", "renamed" or "old name", and accept a
per-page allowlist comment for groups 2 and 3. Not done here.

## Outside this repository

- `technics-roms-disasm/kn7000/README.md` still says 111 functions are converted and that
  there are zero `.byte` escapes; `tools/coverage_score.py` says 999 of 4,201 and 71 escapes.
  `wsa1/README.md`'s status table still says 175 KB of `.incbin` (the real figure is 0), and
  `wsa1/TOOLCHAIN_VERSION` records an older toolchain commit. These are WP10 of the audit.
- `technics-roms-disasm/analysis/binclude-audit-2026-08-07/PLAN.md:29` still calls the
  compressed v1.40 image the only copy of v1.40; the private romset held the decompressed
  payload since 2026-07-20 (WP18's first commit, per the audit).
- The private romset's README still lists the KN7000 wave, rhythm and picture ROMs as undumped
  and says `.exe` to `.SLD` needs DOSBox; both are wrong (audit, inventory-other-models lane).
- Mainline MAME `kn7000.cpp` declares IC18 and IC19 as 8 MB `NO_DUMP`; the reads are the
  CPU-visible 4 MB and 2 MB. How to declare them is the owner's call
  (`kn7000-picture-rom.md` records the plan for IC19).
