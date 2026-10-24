---
layout: page
title: Source Tree Inventory
permalink: /source-tree-inventory/
---

# Source Tree Inventory

Which Technics ROMs and programs are in the disassembly repository, which are only held as
dumps, and which are not there at all. One section per model. The facts come from the
read-only repository audit of 2026-10-24, taken at disassembly commit `14aec1197`
(`notes/repo-audit-2026-10-24/` in the disassembly repository: `README.md` plus
`audit-2026-10-24.json`, which records every figure with the command that produced it).

> ⚠ **This page describes the tree as of 2026-10-24.** A wave of work is in progress on the
> disassembly repository (a KN5000 v8 build, a sub-CPU v1.41 tree, the KN7000 IC18 boot ROM
> and table 80, and KN2400/KN6000/KN6500/HD-SX3 skeletons, among other lanes); none of it is
> merged, and this page will be updated when it lands.

**How to read the state column.** *Byte-exact source tree* means a `make` target rebuilds
the image from source and a gate compares it byte for byte with the reference. *Dump only*
means the image is tracked under `original_ROMs/` but nothing builds it. *Not present* means
the repository holds neither a source tree nor the image; the "where it comes from" column
says where a copy exists. *Blocked* means a tree cannot be started until something else
happens, usually a re-dump.

## KN5000 and HD-AE5000

The main CPU and the sub CPU are both Toshiba TMP94C241F (TLCS-900/H2). The HD-AE5000
expansion ROM runs on the main CPU.

| artifact                                                                                                  | kind            | CPU                     | where it comes from                                                                                                         | state in the disassembly repo                                     | notes                                                                                                                                                                     |
|-----------------------------------------------------------------------------------------------------------|-----------------|-------------------------|-----------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Main program v10 (`kn5000_v10_program.rom`, 2 MiB)                                                        | CPU code + data | TMP94C241F              | chip dump; also stream 1 of `HKMSPRG.SLD` inside the official v10 installer `KN5VA.exe` (`kn5-10.zip`)                      | byte-exact source tree, `v10/maincpu/`                            | The primary target. 100.0% source, 0 B raw blob. Version byte at `0xFFFFE8` = `0x0A`                                                                                      |
| Main program v9 (`kn5000_v9_program.rom`)                                                                 | CPU code + data | TMP94C241F              | chip dump                                                                                                                   | byte-exact source tree, `v9/maincpu/`                             | 100.0% source. Differs from v10 in 13,517 bytes                                                                                                                           |
| Main program v8 (`kn5000_v8_program.rom`)                                                                 | CPU code + data | TMP94C241F              | chip dump in the private romset (MAME BIOS 2)                                                                               | not present                                                       | Identical to v9 except the version byte at `0xFFFFE8` (`0x08` for `0x09`). A build from the v9 sources is in progress                                                     |
| Main program v7 (`kn5000_v7_program.rom`)                                                                 | CPU code + data | TMP94C241F              | chip dump                                                                                                                   | byte-exact source tree, `v7/maincpu/`                             | 99.7% source; 6,591 B still enter the build as a raw blob                                                                                                                 |
| Main program v6 (`kn5000_v6_program.rom`)                                                                 | CPU code + data | TMP94C241F              | chip dump in the private romset (MAME BIOS 4)                                                                               | not present                                                       | 1,461,567 bytes differ from v7, so it needs a tree of its own                                                                                                             |
| Main program v5 (`kn5000_v5_program.rom`)                                                                 | CPU code + data | TMP94C241F              | chip dump in the private romset (MAME BIOS 5)                                                                               | not present                                                       | The earliest release held                                                                                                                                                 |
| Main program v3, v4                                                                                       | CPU code + data | TMP94C241F              | no copy anywhere (MAME `NO_DUMP`)                                                                                           | not present                                                       |                                                                                                                                                                           |
| Sub-CPU payload v1.42 (`kn5000_subprogram_v142.rom`, 196,608 B)                                           | CPU code        | TMP94C241F (sub CPU)    | update disk: the decompressed form of the image below                                                                       | byte-exact source tree, `v142/subcpu/`                            | 100.0% source                                                                                                                                                             |
| Sub-CPU v1.42 compressed update image (`kn5000_subprogram_v142_compressed.rom`, 93,203 B)                 | data (SLIDE4K)  |                         | update disk; byte-identical to stream 2 of `HKMSPRG.SLD` in `KN5VA.exe`                                                     | byte-exact: recompressed from the built payload and `cmp`-checked | Proves the v10 / v1.42 pairing                                                                                                                                            |
| Sub-CPU payload v1.41 and its compressed image (196,608 B / 93,181 B)                                     | CPU code / data | TMP94C241F (sub CPU)    | update disk of unrecorded origin                                                                                            | dump only (both tracked under `original_ROMs/`)                   | Differs from v1.42 in 124,033 bytes. A v1.41 source tree is in progress                                                                                                   |
| Sub-CPU payload v1.40 and its compressed image (196,608 B / 93,124 B)                                     | CPU code / data | TMP94C241F (sub CPU)    | update disk of unrecorded origin                                                                                            | dump only (both tracked under `original_ROMs/`)                   | Differs from v1.41 in 56,018 bytes                                                                                                                                        |
| Sub-CPU payload v1.39                                                                                     | CPU code        | TMP94C241F (sub CPU)    | no copy anywhere (MAME `NO_DUMP`)                                                                                           | not present                                                       |                                                                                                                                                                           |
| Sub-CPU boot ROM IC30 (`kn5000_subcpu_boot.ic30`, 131,072 B)                                              | CPU code        | TMP94C241F (sub CPU)    | chip dump, partial: MAME marks it `BAD_DUMP`                                                                                | byte-exact source tree, `subcpu/boot/`                            | 100.0% source over what was read; see [Sub-CPU Boot ROM]({{ site.baseurl }}/subcpu-boot-rom/) for the unread ranges                                                       |
| Table data ROM IC3 (even) + IC1 (odd), interleaved as `kn5000_table_data.rom` (2 MiB)                     | data, with code | TMP94C241F              | chip dumps; both halves are tracked, and the build uses their 16-bit-word interleave                                        | byte-exact source tree, `table_data/`                             | 84.8% source; 318,468 B still enter as a raw blob, the largest KN5000 debt                                                                                                |
| Custom data flash IC19 (`kn5000_custom_data.ic19`, 1 MiB)                                                 | data            |                         | chip dump                                                                                                                   | byte-exact source tree, `custom_data/`                            | 100.0% typed data                                                                                                                                                         |
| HD-AE5000 v2.06i (`hd-ae5000_v2_06i.ic4`, 512 KiB)                                                        | CPU code + data | TMP94C241F (main CPU)   | chip dump (MAME BIOS 3)                                                                                                     | byte-exact source tree, `hdae5000/`                               | 100.0% source                                                                                                                                                             |
| HD-AE5000 v2.01i (`hd-ae5000_v2_01i.ic4`)                                                                 | CPU code + data | TMP94C241F (main CPU)   | chip dump in the private romset (MAME BIOS 2)                                                                               | not present                                                       |                                                                                                                                                                           |
| HD-AE5000 v1.15i (`hd-ae5000_v1_15i.ic4`; the unversioned `hd-ae5000.ic4` is the same file)               | CPU code + data | TMP94C241F (main CPU)   | chip dump in the private romset (MAME BIOS 1); byte-identical to `HKEXTROM.XAP` inside the official installer `AE5-115.exe` | not present                                                       |                                                                                                                                                                           |
| HD-AE5000 v1.10i (`hd-ae5000_v1_10i.ic4`)                                                                 | CPU code + data | TMP94C241F (main CPU)   | chip dump in the private romset (MAME BIOS 0)                                                                               | not present                                                       |                                                                                                                                                                           |
| Rhythm data ROM IC14 (4 MiB)                                                                              | data            |                         | chip dump in the private romset, as the descrambled image (A19/A21 swap undone) and as the raw read                         | not present                                                       | Analysis probes read it from outside the repository. The repository's reference copy of the MAME driver still declares the raw read's CRC                                 |
| Waveform ROM IC307 (4 MiB)                                                                                | data            |                         | chip dump in the private romset                                                                                             | not present                                                       | The only waveform chip dumped; three tracked probes read it from outside                                                                                                  |
| Waveform ROMs IC304 / IC305 / IC306                                                                       | data            |                         | not dumped (MAME `NO_DUMP`)                                                                                                 | not present                                                       | Synthetic placeholders exist under these chips' names; see "Not counted"                                                                                                  |
| Official v10 update installer `kn5-10.zip` / `KN5VA.exe` (`HKMSPRG.SLD`), and the v10 update floppy image | disk program    | TMP94C241F (main + sub) | the CA software mirror; the floppy image is a FAT12 disk holding the same four files                                        | not present                                                       | Its two SLIDE4K streams decode to exactly the v10 program and the v1.42 compressed image, which are in the repository. No update disk for v5 to v9 exists on this machine |
| Official HD-AE5000 v1.15 installer `ae5-115.zip` / `AE5-115.exe` (`HKEXTROM.XAP`)                         | disk program    | TMP94C241F (main CPU)   | the CA software mirror                                                                                                      | not present                                                       | `HKEXTROM.XAP` is the v1.15i image                                                                                                                                        |

## SX-WSA1R

Two Toshiba TMP95C061 (TLCS-900). The four OS v2 EPROM dumps are committed in the public
repository, under `wsa1/original_ROMs/`.

| artifact                                                                        | kind                 | CPU           | where it comes from | state in the disassembly repo          | notes                                                                                                                          |
|---------------------------------------------------------------------------------|----------------------|---------------|---------------------|----------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| OS v2 EPROMs A, B, C (`wsa1_prom_a.ic12`, `_b.ic13`, `_c.ic28`), 512 KiB each   | CPU code + data      | 2 x TMP95C061 | chip dumps          | byte-exact source tree, `wsa1/`        | No `.incbin` left in any image. 78.0% of the four images is substantive source; the rest is verified filler emitted as `.fill` |
| OS v2 EPROM D (`wsa1_prom_d.bin`), 512 KiB                                      | data (tone database) |               | chip dump           | byte-exact source tree, `wsa1/prom_d/` |                                                                                                                                |
| Wave mask ROMs, the AM29F400T flash, the SED1330 character generator, the v1 OS | data / CPU code      |               | not dumped          | not present                            | See [Help Wanted]({{ site.baseurl }}/help-wanted/)                                                                             |

## SX-KN7000, SP7001 and the Style Convert converters

Panasonic MN10300 (MN103002A). The `kn7000/` tree follows a different convention from the
KN5000 and WSA1R trees: its reference images are git-ignored and regenerated from the update
disks, the private romset and the software-list floppies, and the Makefile checks their SHA-1.

| artifact                                                                                                                                      | kind                   | CPU                | where it comes from                                                                                  | state in the disassembly repo                                                    | notes                                                                                                                                                                                    |
|-----------------------------------------------------------------------------------------------------------------------------------------------|------------------------|--------------------|------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Program build 941 (v1.6), 4,157,185 B + Table build 84                                                                                        | CPU code + data / data | MN103002A          | update disks kn7-16 (`JK1.SLD`, `JK2.SLD`) and kn7-14 (`JKT1.SLD`, `JKT2.SLD`)                       | byte-exact source tree, `kn7000/src/program.s` and `table.s`                     | Byte-exact, but 3.88% of the program image is real source (161,369 B); the rest passes through as `.incbin_range`. 999 of the 4,201 named functions are converted. `table.s` is 100% raw |
| Program build 942 / Table build 83 (SP7001 PLUG-iN) + `BASEEXT.XAP`                                                                           | CPU code + data        | MN103002A          | the SP7001 update disks and the private romset                                                       | byte-exact source tree, `kn7000/src/sp7001/`                                     | Generated from build 941's work; the plug-in code in the table is real assembly                                                                                                          |
| Program build 935 (v1.5)                                                                                                                      | CPU code + data        | MN103002A          | private romset (`kn7000_program_{even,odd}_v1.5_b935`)                                               | not present                                                                      |                                                                                                                                                                                          |
| Program build 893 (v1.3) + Table build 80                                                                                                     | CPU code + data / data | MN103002A          | read from the owner's own unit with the [ROM dumper]({{ site.baseurl }}/kn7000-rom-dumper/) (pass 1) | not present; only a 9,472-byte photo transcription is tracked (`kn7000/dumps/`)  | Table 80 equals the first 0x3E0660 bytes of SP7001 table 83 except one byte, the build string at `0x139EE9` (`0` for `3`). A table 80 build is in progress                               |
| Program build 929 (v1.4), upper half only                                                                                                     | CPU code + data        | MN103002A          | update disk 2 of the v1.4 set; disk 1 is lost                                                        | not present                                                                      | Only a partial skeleton is possible                                                                                                                                                      |
| IC18 rhythm ROM `C3CBND000046`: the 4 MB the CPU can see, whose first 64 KB is the instrument's boot ROM                                      | data + CPU code        | MN10300 (boot ROM) | read from the owner's unit (pass 4)                                                                  | not present                                                                      | Nothing in `kn7000/` builds or disassembles it. A boot-ROM disassembly is in progress                                                                                                    |
| IC19 picture ROM `C3CBMD000098`: the 2 MB the CPU can see                                                                                     | data                   |                    | read from the owner's unit (pass 2)                                                                  | byte-exact source tree, `kn7000/src/picture.s` + 100 committed JPEGs             | See [Picture ROM]({{ site.baseurl }}/kn7000-picture-rom/)                                                                                                                                |
| Wave ROMs `C3CBQD000001`-`4` (IC204, IC203, IC208, IC207), 16 MB each                                                                         | data                   |                    | read from the owner's unit (pass 3), twice, byte-identical                                           | not present                                                                      | PCM sample data; no code                                                                                                                                                                 |
| Custom-data images (`01ctmini.ic21` and the eight `custm` sets, 1,966,080 B each)                                                             | data                   |                    | regenerable from the Initial Data and custom disks (`.AST` = raw deflate at +0x10)                   | not present                                                                      |                                                                                                                                                                                          |
| Style Convert Disk converters: scd7000's `GEM_WS2`, `GEM_WX2`, `KORG`, `Roland`, `SOLTON`, `TECHNICS` `.CNV`, and scd6000's `TECHNICS_KN6000` | disk programs          | MN10300            | the `scd7000` / `scd6000` software-list floppies                                                     | byte-exact source tree, `kn7000/src/cnv/` (seven converters, fully disassembled) | See [Style Converter]({{ site.baseurl }}/kn7000-style-converter/). scd6000's other five converters are identical to scd7000's                                                            |

## SX-KN6000 and SX-KN6500

Panasonic MN10300, linked at `0x4C000000`. Neither model has a folder in the repository.
Small pieces exist elsewhere in it: `kn7000/dsp/cross-model/kn6000/` (81 effects-DSP
records taken from the KN6000 image), `kn7000/src/cnv/technics_kn6000.s`, and
`notes/feature-presentation-cues-probes/`.

| artifact                                                   | kind     | CPU     | where it comes from                                                                                               | state in the disassembly repo | notes                                                                                                                |
|------------------------------------------------------------|----------|---------|-------------------------------------------------------------------------------------------------------------------|-------------------------------|----------------------------------------------------------------------------------------------------------------------|
| KN6000 program `IK1.SLD` + `IK2.SLD` (v7.1), 4,160,049 B   | CPU code | MN10300 | update installer (`kn6-71.zip`): `sfx_extract.py`, then `sld_decompress.py`; `smck_check.py` matches 16/16 blocks | not present                   | A skeleton is in progress. The MILK reflection tables name 1,293 functions, 1,007 of them also in the KN7000         |
| KN6500 program `IKV1.SLD` + `IKV2.SLD` (v1.3), 3,675,793 B | CPU code | MN10300 | update installer (`kn65-13.zip`), same chain; 15/15 blocks                                                        | not present                   | A skeleton is in progress. 1,434 names, 1,142 shared with the KN7000. Its DSP pool is byte-identical to the KN6000's |
| Custom data `01ctmini.ic18` (shared by both models)        | data     |         | regenerable from the idd6000 disk                                                                                 | not present                   |                                                                                                                      |
| Table / font ROMs IC13, IC14; wave and rhythm ROMs         | data     |         | not dumped                                                                                                        | not present                   | The `*_table_fontph.rom` files in the private romset are generated placeholders, not dumps                           |

## SX-KN2400 and SX-KN2600

Panasonic MN10300, linked at `0x48400000`, the same base as the KN7000.

| artifact                                            | kind     | CPU     | where it comes from                                                      | state in the disassembly repo | notes                                                                                                                                     |
|-----------------------------------------------------|----------|---------|--------------------------------------------------------------------------|-------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| Program `LKG1.SLD` + `LKG2.SLD` (v1.1), 3,761,619 B | CPU code | MN10300 | update installer (`kn24-11.zip`), same chain as the KN6000; 15/15 blocks | not present                   | A skeleton is in progress. The KN2600 runs the same ROM: the two romset archives are identical. 2,471 names, 2,133 shared with the KN7000 |
| Rhythm flash, wave flash, SD sub-CPU flash (KN2600) | data     |         | not dumped                                                               | not present                   | See [ROM Dumping Roadmap]({{ site.baseurl }}/rom-dumping-roadmap/)                                                                        |

## SX-KN1500

Toshiba TMP95C061 (TLCS-900), the WSA1R's CPU, so the `wsa1/` toolchain would fit it.

| artifact                                                                                                                        | kind            | CPU       | where it comes from                           | state in the disassembly repo | notes                                                                                                                                                                                                                                                                                                                                                         |
|---------------------------------------------------------------------------------------------------------------------------------|-----------------|-----------|-----------------------------------------------|-------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| IC15 mask ROM `QSIGT3C16079`: a 2 MiB program half (mapped at `0xE00000`) and a 2 MiB rhythm-data half (`.rest`, at `0xC00000`) | CPU code + data | TMP95C061 | chip dump in the private romset (a 2021 read) | blocked                       | The dump is defective: in the program half, four of the eight 256 KiB blocks (`0x000000`, `0x040000`, `0x100000`, `0x140000`) have every odd byte `0xFF`, and MAME says the machine never boots from it. A tree would only reproduce a bad dump, so it needs a re-dump first. A uPD6383 microcode corpus has been taken from the readable part (`dsp/tools/`) |

## HD-SX3

The hard-disk expansion for the KN6000 family. Its program runs on the KN6000's MN10300, in
the ISOROM window at `0x97800000`.

| artifact                                                     | kind     | CPU                        | where it comes from                                                                                                       | state in the disassembly repo | notes                                                                                                                                                                        |
|--------------------------------------------------------------|----------|----------------------------|---------------------------------------------------------------------------------------------------------------------------|-------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `hd-sx3_v1_1.bin`, the `XAPR` plug-in flash image, 786,432 B | CPU code | MN10300 (the KN6000's CPU) | `EXTAPR.SLD` inside `sx6v113a.exe` (`sx6-113.zip`), decompressed; the private romset holds the same bytes under this name | not present                   | A skeleton is in progress. 98 function names recoverable. The [ROM Dumping Roadmap]({{ site.baseurl }}/rom-dumping-roadmap/) describes this same image as the HD-SX6 OS v1.1 |

## Not counted

Some things on the machine look like ROMs and are not counted above:

- **Synthetic placeholders.** The three KN5000 waveform files named after IC304, IC305 and
  IC306 are the project's own generated stand-ins (the private romset keeps them under
  `SYNTHETIC_wave_placeholder_bank1/2/3`), and `kn5000_custom_data_with_preset.ic19` is the
  IC19 image with the 27,967-byte compressed preset block pasted in at the firmware-update
  staging offset: 27,699 bytes differ from the real IC19, all between `0xE0000` and `0xE6D3E`.
  The KN6000/KN6500 `*_table_fontph.rom` files are placeholders too.
- **PC-hardware ROM sets** (`at_keybc.zip`, `ct486.zip`, `et4000.zip`, `kb_ms_natural.zip`)
  that sit in a KN5000 folder but have nothing to do with the instrument.
- **Homebrew run sets** (`anotherworld`, `apploader`, `mines`): official images plus a
  modified v10 program, HD-AE5000 or table data.
- **x86 PC programs.** HD-TechManager5000 v1.20 is tracked under `hdae5000/hd-techmanager5000/`
  as binaries with a disassembly listing of its DLL, not as a byte-exact source; the Technics
  SongManager & AudioRecorder installers are not in the repository at all.
- **Data-only floppies.** All 14 KN5000 software-list disks (355 files of style data,
  wallpapers and index text), the nine WSA1R disks (121 files), every KN7000 disk except
  scd7000, every KN6000 disk except scd6000, and the KN7000 style archives: none holds a
  program. The disks are described on
  [Floppy Disk Images]({{ site.baseurl }}/floppy-disk-images/).

## Duplicates and near-duplicates worth knowing

- `hd-ae5000.ic4` is byte-identical to `hd-ae5000_v1_15i.ic4` (one SHA-1 for both), and both
  equal `HKEXTROM.XAP` from the official `AE5-115.exe` installer. MAME declares only the
  versioned name.
- KN5000 program v8 is v9 with one byte changed: `cmp -l` prints a single line, the version
  byte at file offset `0x1FFFE8` (CPU address `0xFFFFE8`), `0x08` against `0x09`. That byte
  reads `05`, `06`, `07`, `08`, `09`, `0a` across the six releases held.
- The decompressed sub-CPU v1.40 payload has existed in the private romset since 2026-07-20;
  the repository's copy was committed on 2026-08-07.
- KN7000 table 80 (the owner's unit) equals SP7001 table 83's first 0x3E0660 bytes except the
  one byte at `0x139EE9`, where the build string reads `80` instead of `83`; table 80 ends there,
  and table 83 continues with the plug-in.
- The KN2400 and KN2600 romset archives are the same file (same MD5); the two models share one
  program ROM.
- The HD-SX3 image `hd-sx3_v1_1.bin` is exactly `EXTAPR.SLD` from `sx6v113a.exe`, decompressed
  to 0xC0000 bytes.
- The KN1500 IC15 dump is defective, as described in its section; it is the only held dump in
  this state.
- The interleaved `kn5000_table_data.rom` the build compares against exists only in the
  repository; the chips' two halves are the files in the private romset.

## How this page is kept honest

Every "byte-exact" cell above is a claim a script checks, and every percentage is a script's
output. Re-run them rather than copying the numbers forward:

| question                                                      | command (in the disassembly repository)                                                                                         |
|---------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| Do all gated images rebuild byte for byte?                    | `make gate-all` (the KN5000 and WSA1R gates plus `make gate-kn7000`)                                                            |
| Each KN7000 image on its own                                  | `make -C kn7000 verify`, `verify-sp7001`, `verify-picture`, `verify-cnv`                                                        |
| How much of each KN5000 image enters the build as a raw blob? | `python3 scripts/analysis/kn5000_source_coverage.py`                                                                            |
| The same for the four WSA1R images                            | `cd wsa1 && python3 scripts/analysis/source_coverage.py`                                                                        |
| How much of the KN7000 program is real source?                | `cd kn7000 && python3 tools/coverage_score.py` (history in `notes/coverage-history.tsv`)                                        |
| Can the MN10300 disk programs be regenerated without DOSBox?  | `kn7000/tools/sfx_extract.py` (pure Python, reads the zip appended to the `.exe`), then `sld_decompress.py` and `smck_check.py` |

The audit itself is `notes/repo-audit-2026-10-24/` in the disassembly repository. The two
facts on this page that the audit's critic did not re-check (the KN1500 block pattern and the
table 80 / table 83 difference) were re-measured for this page with
[`tools/verify_inventory_facts.py`](https://github.com/ArqueologiaDigital/technics-docs/blob/main/tools/verify_inventory_facts.py)
in this site's repository, read-only against the private romset.
