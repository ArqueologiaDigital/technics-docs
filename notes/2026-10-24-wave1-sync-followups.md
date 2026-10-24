# 2026-10-24: follow-ups from syncing the site with the merged wave 1

Left by the session that brought the site to `technics-roms-disasm` at `2319e9b94` (wave 1 of
the audit's work packages, merged as `7dc379217`..`921314742`). What the session changed is in
this repository's history from `ab88942` to the commit of this note; what it left is below.

## Measured for this sync, and how

Every figure the session wrote comes from a script committed in the disassembly repository,
run on its main checkout at `2319e9b94` (read-only, scratch under `~/compartilhado/tmp/`):

| figure                                                | command (in `technics-roms-disasm`)                                      |
|-------------------------------------------------------|--------------------------------------------------------------------------|
| KN5000 + SX-WSA1R verbatim debt, 99.9% source         | `python3 scripts/analysis/kn5000_source_coverage.py`                     |
| SX-WSA1R 78.0% substantive                            | `cd wsa1 && python3 scripts/analysis/source_coverage.py`                 |
| KN7000 44.58%, 3,658 blocks, 0 escapes                | `cd kn7000 && python3 tools/coverage_score.py`                           |
| census strict 96.80%, per image and bucket            | `python3 scripts/analysis/data_range_census.py` (several minutes)        |
| semantic score 91.10 / 97.00 / 92.65 / 65.29          | `docs/badges/semantic-score.json` as committed (`cdc6226f`); not re-run  |
| HD-AE5000: 0 `.L<hex>`, 0 call targets without header | `python3 scripts/analysis/doc_quality_census.py` (table only, no ledger) |
| HD-AE5000 undocumented `.byte` 1,713 B                | `python3 hdae5000/tools/measure_debt.py`                                 |
| 9 WSA1R macro sites left                              | `python3 scripts/converters/respell_wsa1_macros.py --left`               |
| the status diagram and its table                      | `make rom-status DOCS_DIR=/home/fsanches/compartilhado/technics-docs`    |
| gallery renders (Ntedt0k, HD-AE5000 icon)             | `make gallery DOCS_DIR=/home/fsanches/compartilhado/technics-docs`       |
| KN7000 `func_` renames on three pages                 | `cd kn7000 && python3 notes/convert-probes/entry_rename_map.py PAGES`    |
| sibling figures                                       | `kn2400/ kn6000/ kn6500/ hdsx3/ notes/conversion-stats.txt` as committed |

The gate count, 35 images, is counted from the root `Makefile`'s `gate*` targets and
`scripts/analysis/assert_byte_identical.py`'s `PAIRS`, not from a run of `make gate-all` (this
session did not build anything in the disassembly repository).

## For the disassembly repository (not done here: read-only for this session)

| where                                          | what                                                                                                                                                                     |
|------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `scripts/build/generate_rom_status_diagram.py` | its docstring's "DOCS PAGE (follow-up, not yet done)" paragraph is done: the site now publishes the diagram with that legend (`rom-reconstruction.md`, commit `edaef94`) |
| `Makefile` `gallery:`                          | runs `python`, not `python3`; `scripts/build/convert_images.py`'s default output is still `../kn5000-docs/...`                                                           |
| `hdae5000/images/HDAE5000_Icon.bin`            | still 784 bytes; `convert_images.py` warns on every run                                                                                                                  |
| `kn7000/src/sp7001/table.s`                    | the plug-in's init routine is documented as `func_483E8071` (header comment) but only `func_483E8071_entry` is a label; the site quotes the routine name                 |
| `scripts/analysis/semantic_score.py`           | does not rate the SP7001 set, IC19, table 80, the IC18 boot ROM or the four MN10300 siblings; `rom-reconstruction.md` says so                                            |
| `scripts/analysis/kn5000_source_coverage.py`   | measures v1.41 only through v1.42 (the site says so)                                                                                                                     |
| `hdsx3/`                                       | the evidence says HD-SX6; renaming the folder is the owner's call (the site calls the page "HD-SX")                                                                      |

## On the site

- `tools/check_doc_symbols.py` reports 938 names after this session (936 before). The three new
  ones are deliberate: `ROM_SHA1` (a Makefile variable), `SdCardMenu` (a firmware menu table the
  name walker rejects, not a label) and `kn5000_subprogram_v141_compressed` (a row name in
  `assert_byte_identical.py`). The rest is the triage of `2026-10-24-audit-sync-followups.md`.
- `tools/check_doc_retired_labels.py` (new) lists names that were labels at one disassembly
  commit and are not at a later one. `--old ea51f2d51` gives 0 quoted on the site. `--old
  3417969c0` gives 10 and `--old 5fc8d5bd` 22; every one was read and is quoted as history
  ("was", "formerly", "renamed") or is not a label at all (`CP`, `d3`, `field_1c18`).
- `rom-dumping-roadmap.md`'s "not yet in mainline MAME" phrasing is unchanged (that is a MAME
  question, not a wave-1 one).
- `kn7000-image-gallery.md` was not checked against the 159 table files that `table.s` now
  includes from `kn7000/src/table/`.
- A second wave of work started on the disassembly repository the same day; none of it is on
  the site.
