---
layout: page
title: ROM Reconstruction
permalink: /rom-reconstruction/
---

# ROM Reconstruction

Goal: rebuild every KN5000 firmware image from disassembled source, byte for byte.

Byte-identity is the project's only acceptance criterion. The gate is

```
make gate-all      # thirteen images: 9 KN5000 + 4 SX-WSA1R
```

which rebuilds, then runs `scripts/analysis/assert_byte_identical.py` over nine KN5000 image
pairs and four SX-WSA1R pairs, and `assert_toolchain_is_a_prerequisite.py` to prove the
assembler is a prerequisite of every image rather than a stale object comparing green
forever. It **compares bytes and exits non-zero on any difference**. A change that fails it is
reverted, not explained away.

> ⚠ **`compare_roms.py` is a similarity report, not the gate.** It prints
> `Similarity: 100.00%`, rounded to two decimals — in a 2,097,152-byte ROM that rounding
> covers up to 104 differing bytes, and `grep -c "Similarity: 100.00%"` prefix-matches the
> failing line `Similarity: 100.00%  (N incorrect bytes)` as well. It is useful for locating
> where a divergence sits, and it is what prints the fifteen verification sections below
> (nine LLVM, six legacy ASL). It is not an acceptance criterion; see
> [Disassembly Workflow]({{ site.baseurl }}/disassembly-workflow/#-never-gate-on-a-percentage).
>
> A full similarity run needs `make clean-all && make all && make asl-all` before it, because
> `make all` builds only the LLVM targets and `compare_roms.py` silently skips a section whose
> built file is missing — the short form prints nine sections, all reading `100.00%`, having
> never assembled the mirror.

## Firmware Version History

Official firmware updates were distributed on floppy disk. All versions are archived at [archive.org](https://archive.org/details/technics-kn5000-system-update-disks).

> **Provenance note.** The release dates below come from the update-disc listing, not from
> anything inside the ROM images, and no corresponding dates exist in the disassembly
> repository. Treat them as unconfirmed.

### Main Board Firmware

| Version | Release Date | Source tree |
|---------|--------------|-------|
| v5 | 1997-11-12 | none — earliest available; no dump in the disassembly repository |
| v6 | 1998-01-16 | none — no dump in the disassembly repository |
| **v7** | 1998-06-26 | `v7/maincpu/`, byte-identical |
| v8 | 1998-11-13 | none — differs from v9 by the version byte alone, so this is the cheapest tree still missing |
| **v9** | 1999-01-26 | `v9/maincpu/`, byte-identical |
| **v10** | 1999-08-02 | `v10/maincpu/` — the primary disassembly target |

Three of the six main-CPU releases are source-built. v5, v6 and v8 are archived on
[archive.org](https://archive.org/details/technics-kn5000-system-update-disks) and selectable
as MAME BIOS options, but no dump of them sits in the disassembly repository and none has a
source tree, so they are outside the byte gate.

The sub-CPU payload has the same shape: `v142/subcpu/` is source-built and gated, while v1.40
and v1.41 are held as verified artifacts with no source tree — see
[Sub-CPU Firmware Images]({{ site.baseurl }}/subcpu-firmware-images/).

### HD-AE5000 Firmware

| Version | Release Date | Notes |
|---------|--------------|-------|
| v1.10i | 1998-07-06 | Initial release |
| v1.15i | 1998-10-13 | |
| v2.0i | 1999-01-15 | Added lyrics display |

## Verification Sections

### Primary build (LLVM)

| Section | Original image | Size | Base | Top-level source |
|---------|----------------|------|------|------------------|
| maincpu v10 | `kn5000_v10_program.rom` | 2MB | 0xE00000 | `v10/maincpu/kn5000_v10_program.s` |
| maincpu v9 | `kn5000_v9_program.rom` | 2MB | 0xE00000 | `v9/maincpu/kn5000_v9_program.s` |
| maincpu v7 | `kn5000_v7_program.rom` | 2MB | 0xE00000 | `v7/maincpu/kn5000_v7_program.s` |
| subcpu payload v142 | `kn5000_subprogram_v142.rom` | 192KB | 0x0400 | `v142/subcpu/kn5000_subprogram_v142.s` |
| **subcpu v142 update image** | `kn5000_subprogram_v142_compressed.rom` | 93,203B | 0x3E0000 | *(compressed from the built payload — see below)* |
| subcpu boot | `kn5000_subcpu_boot.ic30` | 128KB | 0xFE0000 | `subcpu/boot/kn5000_subcpu_boot.s` |
| hdae5000 | `hd-ae5000_v2_06i.ic4` | 512KB | 0x280000 | `hdae5000/hd-ae5000_v2_06i.s` |
| table data | `kn5000_table_data.rom` | 2MB | 0x800000 | `table_data/kn5000_table_data.s` |
| custom data | `kn5000_custom_data.ic19` | 1MB | 0x300000 | `custom_data/kn5000_custom_data.s` |

### Legacy ASL mirror build

The project's original ASL sources are kept in `archive/asl/` and are still built and
compared: maincpu, subcpu boot, subcpu payload, table data, custom data and hdae5000 —
six more sections, all at 100.00%. They are built by `make asl-all`, which is **not** a
dependency of `make all`; that is the whole reason the gate command has to name it
explicitly.

The mirror is not a museum piece; it constrains the work. The ASL sources still
`binclude` several data blobs *whole* (`initial_data.bin`, `icons_to_strings.bin`,
`wallpaper1_to_icons.bin`, …), so those files must stay byte-identical on disk even
after the LLVM sources stop referencing them. Conversions therefore slice with
`.incbin "file", offset, length` rather than splitting a blob into new files.

### The v1.42 sub-CPU firmware-update image

The sub-CPU payload is verified in *both* of the forms it ships in.

`original_ROMs/kn5000_subprogram_v142_compressed.rom` is the v1.42 payload as it appears
on a firmware-update disk ("Program DATA FILE PCK", File Type 007, flashed to Custom Data
`0x3E0000`). It is an 11-byte header — `"SLIDE4K"` + NUL, then a 24-bit **big-endian**
decompressed size (`03 00 00` = 196,608) — followed by the LZSS stream.

Because the payload itself is already source-built, recompressing the build output with
the factory stream's own decisions must reproduce the update image exactly. The Makefile
rule does that and then seals it with `cmp`:

```make
rebuilt_ROMs/kn5000_subprogram_v142_compressed.rom: \
		rebuilt_ROMs/kn5000_subprogram_v142.llvm.rom \
		original_ROMs/kn5000_subprogram_v142_compressed.rom
	python3 scripts/build/compress_lzss.py $< $@ --strict --with-header \
		--reference original_ROMs/kn5000_subprogram_v142_compressed.rom
	cmp $@ original_ROMs/kn5000_subprogram_v142_compressed.rom
```

`--with-header` (added at the same time) emits and validates the SLIDE4K header;
`--strict --reference` replays the factory encoder's match/literal decisions so the
output is byte-identical rather than merely equivalent. The section appears in
`compare_roms.py` as *subcpu v142 update image*.

See [LZSS Compression]({{ site.baseurl }}/lzss-compression/) for the format, and
[Sub-CPU Firmware Images]({{ site.baseurl }}/subcpu-firmware-images/) for what this means
for the v1.40 and v1.41 payloads.

### Generated data with its own verification targets

Two families of compressed data are no longer bincluded as opaque payloads; they are
rebuilt from checked-in sources and compared against factory slices.

| Target | What it rebuilds | Check |
|--------|------------------|-------|
| `make verify-demo-presets` | 19 SLIDE4K demo-song presets, from `.mid` + `.yaml` sidecars | 19/19 byte-identical |
| `make verify-help-databases` | 6 SLIDE8K help databases, recompressed from the checked-in decompressed database binaries | 6/6 byte-identical |

**Demo presets.** All 19 presets (entries 0–17 at 0x9C4050–0x9F94CA plus the Feature
Presentation at 0x8E0000) round-trip from a `.mid` file — the musical content, editable
in any DAW — and a `.yaml` sidecar carrying everything MIDI cannot express: song header,
cell topology, padding, stream order, running-status flags and the durations MIDI cannot
represent. `compress_lzss.py --strict` aborts the build if any payload stops matching the
factory stream, so an edit can never silently ship different music.

**Help databases.** The five live multilingual help databases (English, German, French,
Spanish, Indonesian) plus one stale sixth block are SLIDE8K — a previously undocumented
8 KB-window LZSS variant. The firmware itself supports both widths: the main-CPU routine
`SLIDE_Parse_Header` reads the digit in the magic and branches on it, `0x34` (`'4'`) to
`SLIDE_Decompress_4K_Init` and `0x38` (`'8'`) to `SLIDE_Decompress_8K_Init`. Each database
decompresses to exactly 0x9000 bytes.
`compress_slide8k.py --strict --reference` replays the factory encoder's decisions,
which is necessary because the final flag bytes carry nonzero unused bits that a plain
re-encode would not reproduce.

The sixth block, at ROM 0x983B3A, is a superseded German revision that nothing points at.
It is **truncated, not merely corrupt**: its stream decodes identically to the live German
database for exactly 0x55E0 output bytes, and the element that would produce output 0x55E0
is the first to read past 0x985FFF — because the factory image wrote the two Music Stylist
pointer tables at 0x986000/0x987000 straight over this obsolete block's tail. It is
therefore kept as a byte-exact raw slice of the dump and is *not* rebuilt from source; a
whole-extent reference slice is still round-trip-verified by `make verify-help-databases`
to pin the bytes down.

## What the source says each region is

Every `.incbin` in the repository has been audited: **598 `.incbin`/`binclude` directives**,
of which **505 are honest build products** — compiled from C or assembly, or generated from
documented data. The audit method, and the discipline that keeps a conversion from silently
asserting more than the dump supports, are on the
[Disassembly Workflow]({{ site.baseurl }}/disassembly-workflow/) page.

### Table Data ROM: labelled source, not opaque halves

The LLVM source for the 2 MB table-data ROM pulls **zero bytes out of anonymous blob files**.
`initial_data.bin` is not referenced by the LLVM build at
all; `icons_to_strings.bin` survives only as 13 labelled, explicitly sized slices
(126,674 B: ten font glyph banks, the truncated German help block, the Composer factory
memory image and one residue block); `wallpaper1_to_icons.bin` as 87 named bitmap slices;
`icon_pixel_data.bin` as 177 named icon slices. Every remaining `.incbin` in the table-data
sources carries a label, a length and a comment saying what it is.

`icons_to_strings.bin` is audited end to end: all 742,024 bytes are accounted for — 126,674 B in those 13 slices, 394,246 B that this build emits from
source but the ASL mirror still takes from the blob, and a 221,104-byte dead tail
(ROM `0x9C4050-0x9F9FFF`) that no build reads and that is a stale duplicate of the
now-source-built demo-song presets. It was documented rather than deleted, because the
file is a checked-in dump slice whose hash the audit quotes and because giving those bytes
a second source would be a byte-match trap. `make audit-icons-blob` re-derives the map
from the tree and the factory dump and fails if any of it drifts. Details on the
[Table Data ROM]({{ site.baseurl }}/table-data-rom/) page.

Symbol counts follow, from each file's generated header at `be376096`:
`symbols/table_data_symbols_reference.txt` holds **4,759** symbols, the sub-CPU payload's
**5,560**, the HD-AE5000's **3,932** and the sub-CPU boot ROM's **201**.

### Region-by-region source map

| Region | ROM range | Now |
|--------|-----------|-----|
| Section directory + preset banks | 0x800000–0x82FFFF | `table_data/preset_banks.s` (+ generator) |
| Tone database | 0x830000–0x87FFEF | three modules: directory/offset table, 579 tone records, aux tables |
| UI bitmaps, frames, icon tables | 0x913000–0x944D77 | `table_data/ui_bitmaps.s`, symbolic descriptor tables |
| Font descriptors + glyph banks | 0x945C00–0x950A5F | `table_data/fonts.s` (10 fonts) |
| Music Stylist preset database | 0x951000–0x98156F | `table_data/style_records.s`, 1000 × 198 B records |
| Help index, intro strings, help DBs | 0x988000–0x9999D2 | `table_data/help_databases.s` + source-built SLIDE8K |
| Panel Memory factory presets | 0x99EC00–0x9ABF3F | `table_data/panel_memory_presets.s` |
| Composer factory memory image | 0x9B4000–0x9C3FFF | `Composer_FactoryMemoryImage` — one labelled 64 KB include, layout documented in-source |
| Boot FDC command-layer driver | 0x9FD8A5–0x9FEA9C | `table_data/boot_fdc_driver.s` (2,316 lines) |
| Boot disk-format probe | 0x9FEB2B–0x9FEC6D | `table_data/boot_disk_probe.s` |
| Boot CP-serial driver | 0x9FEC6E–0x9FFB2E | `table_data/boot_cpserial.s` + `table_data/boot_cpserial_isr.s` + `table_data/boot_cpserial_states.s` |
| Boot C runtime (heap, memcmp, divide) | 0x9FFB2F–0x9FFE7F | `table_data/boot_clib.s` |
| Boot debug group (NOP-patched out) | 0x9FFE80–0x9FFEDF | `table_data/boot_debug.s` |
| Sub-CPU DSP data zones A0 / A / B | 0x00F7E6–0x01E17E | carved into labelled tables in `v142/subcpu/subcpu_data_tables.s` |
| Sub-CPU boot data region | 0xFF8000–0xFF828F | eight objects in `subcpu/boot/kn5000_subcpu_boot.s`: an 8-entry command-handler jump table, a RAM-test descriptor and the tone-generator velocity/touch front end |
| DSP effect + parameter name tables (maincpu) | 0xE32418–0xE33579 | `DspParamUnit_Table` (86 × 2), `DspParamName_Table` (86 × 17), `DspEffectName_PtrTable` (128 × u32) and `DspEffectName_Strings` (128 × 18) in `ui_widgets/widget_descriptors.s` ([DSP Name Tables]({{ site.baseurl }}/dsp-name-tables/)) |
| HD-AE5000 UI object + name tables | 0x2A5D2C–0x2A8499 | two index-parallel 790-entry pointer arrays and the name pool they index, in `hdae5000/hdae5000_data_tables.s` |
| HD-AE5000 initialised `.data` image | 0x2F94B2–0x2FA133 | `hdae5000/hdae5000_init_data.s` — nine tables, 96 code pointers and 166 string pointers, all named from the firmware's own registration calls |
| HD-AE5000 graphics bank | 0x2A858E–0x2F8DCD | re-split into eleven regions: five palette + bitmap pairs at the boundaries hard-coded in `HDAE5000_Register_Frame`, plus a string head |

Several of these regions are not what their file names say, and the names were kept while the
descriptions were not:

- `bootcode_flash_handlers.bin` is not flash update handlers — it is the bootloader's
  complete uPD72068 FDC command layer, a compact port of the maincpu FDC driver.
- `bootcode_utils.bin` is not motor control, VGA display or a progress bar — it is the
  floppy disk-format probe plus the bootloader's own CP-serial driver, which is
  **independent of** the runtime `CPanel_*` stack in the program ROM.
- The incbin boundary at 0x9FC6F6 was splitting a five-byte `ld A,(0x160002)` in half. It
  byte-matched, but only by accident; the instruction is now emitted whole.
- There is no "exponential pitch table at 0x13318" in the sub-CPU payload. 0x13318 is the
  middle of `DSP_MixerGain_Curve` (0x0131CF–0x0133CE), a 128-entry piecewise-exponential
  **gain** curve ending at digital full scale 0x7FFFFF00; the only proven consumer,
  `DSP_MixerCoeff_Compute`, treats its entries as amplitude.
- The sub-CPU executable does not live at table-data 0x830000. That region is the tone
  database; where the runtime code payload is sourced from is a separate question.
- `HDAE5000_GFX_DATA_1`, despite the name, is neither graphics nor code: all 3,160
  bytes of it group into valid little-endian pointers — 769 into the UI descriptor pool,
  20 into sub-CPU work RAM, and one NULL terminator. Its `0x315` is an *entry count*, not a
  byte size.
- There is no `HDAE5000_Font_Data` region. The address that label named holds no font, and
  fell 0x11818 bytes *inside* a 320×240 bitmap.
- A 320×240 boot splash sits at 0x2E61CE, immediately after the 0x400-byte VGA palette.
- The sub-CPU boot ROM's 96 KB of `0xFF` is **not erased flash**. It was never dumped: only
  4,352 of the chip's 131,072 bytes have ever been read. Any "the sub-CPU boot ROM is ~99%
  disassembled" figure computed over the whole file is meaningless.

## Where the source still holds raw ROM slices

The HD-AE5000 and sub-CPU boot packages have now landed; what remains is the v7 tree and
the unfinished half of the closing sweep. Measured from the current sources — total bytes
emitted by `.incbin` directives per ROM tree:

| ROM tree | `.incbin` bytes | Character of what remains |
|----------|-----------------|---------------------------|
| `v10/maincpu` | 860,028 | Overwhelmingly `includes/generated/*.bin` — C-compiled screen/widget data, an honest build product |
| `v9/maincpu` | 860,028 | Same shape as v10 |
| `v7/maincpu` | 995,213 | **Raw ROM slices behind a `generated/` path** — see the note below |
| `v142/subcpu` | 0 | No binary includes at all |
| `subcpu/boot` | 0 | The 656-byte blob was carved into source; the ASL mirror still `binclude`s the file, so it stays on disk |
| `hdae5000` | 313,076 | Ten labelled slices of `code_29af2d_2fffff.bin`, and **all ten are pixel or palette data**: five 1,024-byte RGBX palettes, four 320×240 bitmaps and one 756-byte icon. Despite the file's name none of it is code. The slice boundaries sit on the real palette/bitmap edges, and the boot splash at 0x2E61CE is named |
| `table_data` | 1,113,121 | All labelled: BMPs, wallpapers, font glyph banks, icon/bitmap slices, and the source-built compressed payloads |
| `custom_data` | 667,648 | Six factory-style-database sections; blob-level documentation judged adequate (this is one unit's user-data area, not firmware) |

> **What that table does and does not say.** These are bytes that the LLVM build pulls in
> as opaque binary. A slice that is labelled, sized and commented is *not* the same thing as
> disassembled code or a decoded structure — it is a boundary that someone has proved. The
> HD-AE5000 bitmaps, for instance, are fully identified and still 313,076 raw bytes, exactly
> as they should be.

**The v7 tree deserves a warning.** `scripts/build/extract_v7_bins.py` runs at build time
and `dd`-slices the v7 ROM into `v7/maincpu/includes/generated/`. Some of those slices are
explicitly v7-specific (139 `v7_block_*`, 24 `v7_fix_*`, 16 `v7_data_*` and the transplant
set — 136,775 bytes between them). The rest — 858,438 bytes under names shared with the v9
tree (`naka_*`, `sound_data_*`, …) — are C-compile outputs that the script **overwrites**
with raw ROM bytes whenever a >50%-similarity check fires. The v7 ROM therefore rebuilds
byte-perfectly while much of its "source" is the ROM itself, and the similarity heuristic
is a silent-corruption risk: a genuinely different block that happens to match at 51%
would be silently accepted. Fixing this means parameterising the C sources per firmware
version so compilation alone reproduces the v7 bytes, then deleting the overwrite. It is
the single largest item left in the plan.

Additional known-unfinished items:

- **Code hidden in maincpu `.byte` is measured, per tree, and it is uneven.** `v7` holds
  275,822 B of it — 797 confirmed code-shaped regions (247,603 B) plus 2,268 shorter
  misframed islands (28,219 B) — the single largest debt figure anywhere in the tree, more
  than twice v7's own verbatim romslice debt. `v9` and `v10`'s high-confidence
  confirmed-region backlog — the shape `v9_v10_undisassembled_census.py --judge` can find and
  hand-audit — is at **0 B on both images**, re-confirmed independently for each; the
  remaining debt in this shape is shorter misframed islands (real instructions run past a
  flanking `.byte` run, so fixing one means re-framing an instruction already present rather
  than filling a gap), which stood at about 14,727 B per image before this push and has
  since been partly converted on both. Converting a region creates new islands at its
  boundary, so an island count is only valid against the exact commit it was measured at —
  quote a fresh run, not this page. This is a different, larger category than the `.incbin`
  verbatim debt measured below: a long `.byte` run is exactly as undecoded as an `.incbin`,
  but it passes every "no `.incbin`" check, so no tool that only scans for `.incbin` can see
  it. `scripts/analysis/v9_v10_undisassembled_census.py` (v9/v10, and the same rule applied
  to v7) is the census.
- The sub-CPU boot ROM source still spells its blank region as **98,304 individual
  `.byte 0xff` lines**. Collapsing them to one `.fill` was proposed, drafted and then
  **withdrawn**: the change is byte-safe, but the region is undumped rather than known to be
  erased, and a single `.fill` directive would assert a fact about the physical chip that
  the dump does not support.
- The HD-AE5000 UI descriptor pool at 0x29DC12–0x2A5D2B is one 769-entry array currently cut
  into five pieces at non-boundaries — the next honest-data package.
- The v1.41 sub-CPU payload has no source tree; see
  [Sub-CPU Firmware Images]({{ site.baseurl }}/subcpu-firmware-images/).

Three items on this list were closed by the August waves. The HD-AE5000 string table around
0x2A5D2C–0x2A8499 is no longer mis-decoded as instructions; the orphaned
`table_data/includes/bootcode_*.bin` slices are gone, along with 25 other unreferenced
artifacts, each recorded in `analysis/orphans-2026-08-08/README.md` with the `dd` that
regenerates it byte-for-byte (six `bootcode_*.bin` files remain because the ASL mirror still
`binclude`s them); and `icons_to_strings.bin` is now fully accounted for by
`make audit-icons-blob`, which reports 126,674 bytes in thirteen labelled LLVM slices,
615,350 bytes unreferenced by the LLVM build, and a 221,104-byte dead tail beyond file
offset 0x7F2D8 that duplicates the source-built demo-preset region and is read by nothing.

## Three kinds of debt, not one

Disassembly debt in this tree comes in three distinct shapes, counted by three different
instruments, and quoting any one of them as "the" debt figure is the mistake to avoid:

| kind | what it is | counted by |
|---|---|---|
| **verbatim** | bytes handed back through `.incbin` of a blob with no generating source | `scripts/analysis/kn5000_source_coverage.py` |
| **code-as-`.byte`** | real instructions spelled as data directives | per-image census tools, e.g. `scripts/analysis/v9_v10_undisassembled_census.py` |
| **data-as-code** | data disassembled into plausible instruction mnemonics that re-assemble byte-exact | `scripts/analysis/v10_data_as_code_census.py`, `wsa1/notes/data_as_code_audit.py`, `scripts/analysis/kn5000_rest_data_as_code_audit.py` |

A `.byte` run is exactly as undecoded as an `.incbin`, but passes every "no `.incbin`" check
— and the third kind is invisible by construction: a re-assembly of a wrong interpretation
still reproduces the original bytes, so the byte gate cannot object to it either. Two
confirmed instances exist in [HD-AE5000]({{ site.baseurl }}/hdae5000/) — a 309-byte version
string disassembled as garbage instructions, and a 6,356-byte record table with zero call or
jump sites anywhere in the tree, loaded only as an address.

**All thirteen gated images have been censused for data-as-code, and a "clean" verdict has
not held everywhere.** Sub-CPU boot, table data, custom data, `prom_c` and `prom_d` came
back clean and nothing since has contradicted it; for those the "every debt figure is a
lower bound" caveat below is lifted. (`prom_c`'s 84 remaining data-as-code markers are all
five-`nop` device-settle delays in real code, per its Wave 2 lane.) `prom_a` and `prom_b`
were reported clean as well, but the Wave 2 lanes then found and retyped data framed as code
in both — 1,958 B, eleven panel lookup tables and the panel LED wire maps in `prom_a`, nine
tables in `prom_b` — and the lanes' marker counts there still stand at 855 and 112, so the
caveat applies to them again. It survives for `v9`, `v7` and `v142`, whose seed-coverage
gaps run 51–74% — that much of their proven code is reached only through indirect or
computed dispatch that static analysis cannot follow, so a census there cannot rule out
further misdecoded spans.

### A fourth, smaller kind: numeric cross-references

A branch whose operand is a number (`jr z, 17`, `calr 2716`, `call 16569399`) assembles
byte-exact but names nothing, which breaks the symbolic-cross-reference rule. Numeric
`jr`/`jrl`/`calr` operands are raw PC-relative displacements, so each target can be computed
from the address map, and `scripts/converters/symbolize_numeric_branches.py` does that,
inserting a structurally named label (`_Return`, `_Loop`, `_Join`, `_Skip`, `_Helper`, …) at
the target. Because the new label is used as an operand, a label placed even one byte wrong
changes the assembled displacement, so the byte gate does check this edit.

It deliberately leaves a residue numeric. A "branch" made of data decoded as code, or of
the operand bytes of a mis-framed instruction, would plant a meaningless label that the
gate cannot see. So every site must also be decoded identically by a second decoder (MAME's
`unidasm`), and sites in text, pointer tables or absurd instruction neighbourhoods are refused.
An eight-judge review of 360 accepted sites found two phantom branches, both of which that
second-decoder rule now refuses. The review evidence is in `notes/branch-symbolization-2026-09-25/`.

| tree | numeric branch operands | of all branches | before the pass |
|---|---:|---:|---:|
| maincpu v10 | 585 | 74,085 | 13,344 / 74,282 |
| maincpu v9 | 611 | 74,085 | 14,217 / 75,164 |
| maincpu v7 | 2,102 | 73,848 | 19,408 / 57,528 |
| subcpu v142 | 0 | 7,049 | 726 / 6,997 |
| HD-AE5000 | 1 | 7,146 | 877 / 7,146 |
| table data | 0 | 1,331 | 83 / 1,280 |
| SX-WSA1R `prom_a` | 197 | 25,232 | 7,605 / 25,208 |
| SX-WSA1R `prom_b` | 206 | 18,516 | 18,241 / 18,411 |
| SX-WSA1R `prom_c` | 6 | 10,241 | 2,479 / 10,241 |

Counted with the one-liner in `scripts/converters/README-symbolize-branches.md` (the
"all branches" column drops the operand pattern), over the committed sources at `be376096`
for the current columns and at the commit before the symboliser landed (`b0bfd371^`) for the
last; `tools/branch_operand_counts.py <rev>` in this repository runs exactly that over the
committed blobs. Those "before" figures reproduce the ones in the tool's own docstring
exactly. v7's
denominator grew by 16,320 branches during Wave 2 (`3958235e` → `5fc8d5bd`), as v7 regions
were converted to instructions.

What remains is mostly the refused residue, and that residue doubles as a list of places
where a branch or its target is framed wrongly. In `prom_c` all six sit in the dead
`UNREFERENCED_TRAMPOLINES` block and target mid-instruction addresses. `prom_a`'s own lane
instrument (`notes/proma-2026-09-25/measure_proma.py`) counts 203 and splits them: 24 `call`s into `prom_a` and 9 into `prom_b`, 117 `calr`, 33
`jr`, 9 `jrl`, 9 `jp` into `prom_a` and 2 elsewhere — some of them in genuinely stale code
(see [SX-WSA1R older-build remnants]({{ site.baseurl }}/wsa1-disassembly/#older-build-remnants-and-why-unreached-code-can-be-correct)).

## Verbatim debt across all thirteen gated images

`scripts/analysis/kn5000_source_coverage.py` measures **verbatim debt** — bytes that enter
the build through an `.incbin` of a committed blob with no generating source — across all
nine KN5000 images and the four SX-WSA1R images together (13 total, 12,386,304 B). This is
a narrower question than "is this region understood": a `.byte` run that spells real code
(tracked separately per image — see the maincpu figures above), or a wrong disassembly that
happens to re-assemble to the right bytes (see the data-as-code note above), is invisible to
it. Outside the five data-as-code-clean images above, every debt figure on this page is
therefore a lower bound.

**Eleven of the thirteen images are at zero verbatim debt: 100% source.** Nothing in
maincpu v10 or v9, the sub-CPU payload v142, the sub-CPU boot ROM, custom data,
HD-AE5000, or any of the four SX-WSA1R images enters the build as an opaque blob — even
the eight flash-update boot banners round-trip from committed PNGs
(`python3 scripts/build/mono_images.py verify` reports `ROUND TRIP EXACT: all 8 banners x
2 revisions (9,856 B)`, the same 616-byte-each files shared byte-for-byte between the two
firmware revisions). v9's confirmed-region backlog — the high-confidence code-as-`.byte`
shape `v9_v10_undisassembled_census.py --judge` can find — is closed on both images:
re-running it directly against v9 (not mirrored from v10, whose source has since drifted
out of lockstep) finds zero confirmed hits beyond the same hand-audited DATA regions
already on record.

The two remaining rows (reproduce with the command above; these are current measurements,
not the tool's raw total — see the note on table data below):

| Image | Verbatim debt | % source |
|---|---:|---:|
| `v7/maincpu` | 120,666 B | 94.2% |
| `table_data` | 0 B real (318,468 B raw tool total) | see below |

**So the tree's only real remaining verbatim debt is v7's 120,666 B.** The whole-tree
figure the tool prints, 439,134 B over 12,386,304 B (96.5% source), is that plus table
data's BMPs.

*(2026-09-02, from the command above. The v7 row falls as conversion lanes land, sometimes
within hours — re-run rather than quoting this table.)*

**Table data's real remaining debt is zero.** The tool's raw 318,468 B figure is entirely the
six `FTBMP01-06.BMP` feature-demo slide images — genuine, uncompressed 8bpp Windows BMPs
(`BM` magic, correct 40-byte DIB header, viewable in any image tool) that are already the
shipped artefact in its best form. The tool counts them as debt because it classifies by
*mechanism* (does a generator exist?) rather than by *what is understood*; giving them a
round-trip PNG generator would add machinery for no viewability gain and would discard the
genuine artefact Technics's own toolchain shipped. The only other slice ever counted against
table data — a 17,570 B stale remnant duplicating the live English/German help-database
streams 0x8000 lower in the ROM — is now itself derived from those streams by a committed
generator (`gen_stale_help_duplicate.py`) rather than stored as a raw blob, so it no longer
counts as debt either: table data's unclassified, real conversion debt is 0 B.

## How much of the data is actually explained

Byte identity says the source reproduces the ROM. It says nothing about whether anybody
can state what a given range of bytes *represents*. That is a separate measurement, and it
is the one that decides whether "the ROMs are done" is true.

**Of the 12,386,304 bytes across the twelve distinct images, 95.04 % are CODE, evidenced
data or verified filler** -- the census's *strict* figure, 11,771,934 bytes, after the
September 25 semantic push (Wave 2), whose twenty lanes turned named-but-unevidenced data into
data whose header cites its reader; it stood at 64.15 % before (details
[below](#after-wave-2-2026-09-25)). Counting data that rests on a descriptive name alone as
well, the census reports 99.54 %. ⚠ That is the instrument's grade, not an audited figure:
the hand-audited false-positive sample was last drawn for the September 2 run, when about
93.8 % (≈11.61 MB) could be explained, with a 95 % confidence interval of 86.7 % – 96.6 %
(about 82 % under the strictest reading -- that a section header does not explain a 30 KB blob
it happens to sit above). That day's raw census reported 99.78 %, a figure wrong by
construction for the reasons itemised below.

    python3 scripts/analysis/data_range_census.py                     # the census, all 12 images
    python3 scripts/analysis/data_range_census.py --json out.json --targets 60
    python3 scripts/analysis/data_range_census.py --selftest

The run after Wave 2 is committed as
`notes/lanes/wave2-2026-09-25/census-after-wave2.txt` in the disassembly repository (at
`5fc8d5bd`, toolchain `tlcs900_backend@4d7fa4f6b37c`, llvm-mc sha256 `a7ee33d5…`). **That
file is only the first part of the output**: it carries the reconciliation, the per-image
table and the strict / explained lines, and stops at the heading of the purpose-unknown
list. The research-target figures and the flag table further down this page are not in it.
All of them come from the second command above, re-run at `be376096`: its report (less the per-image progress
lines) matches the committed file line for line as far as the file goes, and the rest printed the research-target
totals, their split by reason and the three flags exactly as quoted here. `be376096`'s
sources no longer assemble with the current shared llvm-mc (they still use spellings such
as `mul8rr` that the later toolchain retired), so that re-run was made in a `git archive`
export of the commit, after `make all`, with `PROJECTS_ROOT` pointing at a directory whose
`llvm-project/build/bin/llvm-mc` is the `a7ee33d5…` binary. The lanes' own before/after
figures, and what each could not do, are in `lane-reports/*.json` beside the committed
file.

### The grades

Every byte of every image lands in exactly one bucket:

- **CODE** — instruction statements.
- **KNOWN-A** — data whose header says what it represents **and** cites evidence: a reader,
  a call site, a record layout, a field, a findings file or script.
- **KNOWN-B** — data under a descriptive, non-address-derived name (`Font_Svc07_8x16`,
  `DrumKitNames`), with or without a header, but with no evidence cited. Real understanding,
  resting on somebody's naming judgement and nothing else.
- **UNKNOWN** — an address-derived or absent label with no explanatory header, **or a
  header of fewer than 40 words that admits the purpose is not established**. (A longer
  admitting header can still grade KNOWN-B; either way the admission puts the region on the
  research-target list.)
- **FILLER** — a fill directive whose ROM bytes are **verified uniform**, run ≥ 16 bytes.

*Strict* is CODE + KNOWN-A + FILLER; *explained* adds KNOWN-B.

Separately, the census lists **research targets**: ranges whose purpose is not
established — UNKNOWN bytes, any region whose header self-admits a gap whatever its grade,
and undocumented data sandwiched between two instruction regions ("embedded-in-code").

### After Wave 2 (2026-09-25)

| image | CODE | KNOWN-A | KNOWN-B | UNKNOWN | FILLER | strict |
|---|---:|---:|---:|---:|---:|---:|
| v10 | 995,508 | 917,658 | 108,608 | 16,943 | 58,435 | 94.01 % |
| v9 | 995,358 | 917,199 | 109,203 | 16,943 | 58,449 | 93.98 % |
| v7 | 985,895 | 915,445 | 114,755 | 20,662 | 60,395 | 93.54 % |
| v142 sub-CPU | 128,860 | 65,969 | 1,687 | 44 | 48 | 99.12 % |
| sub-CPU boot | 3,604 | 870 | 35 | 0 | 126,563 | 99.97 % |
| table data | 19,426 | 1,800,585 | 95,143 | 0 | 181,998 | 95.46 % |
| custom data | 0 | 660,657 | 0 | 0 | 387,919 | 100.00 % |
| HD-AE5000 | 112,324 | 373,890 | 7,736 | 0 | 30,338 | 98.52 % |
| `prom_a` | 324,950 | 107,566 | 24,023 | 1,355 | 66,394 | 95.16 % |
| `prom_b` | 204,396 | 163,160 | 85,108 | 620 | 71,004 | 83.65 % |
| `prom_c` | 207,511 | 177,152 | 10,409 | 0 | 129,216 | 98.01 % |
| `prom_d` | 0 | 329,425 | 1,096 | 0 | 193,767 | 99.79 % |
| **total** | **3,977,832** | **6,429,576** | **557,803** | **56,567** | **1,364,526** | **95.04 %** |

| | before Wave 2 (`3958235e`) | after (`5fc8d5bd`) |
|---|---:|---:|
| strict (CODE + KNOWN-A + FILLER) | 64.15 % | **95.04 %** |
| KNOWN-A (evidence header) | 2,778,685 B | 6,429,576 B |
| KNOWN-B (name only) | 4,428,721 B | 557,803 B |
| UNKNOWN | 12,357 B | 56,567 B |
| research targets | 395,986 B in 26,553 ranges | 328,853 B in 5,077 ranges |

The research targets split by reason as 248,744 B self-admitted, 59,562 B with no
explanation and 20,547 B embedded-in-code (apportioned where a range has more than one).
By image: v10 70,509 B, v9 70,816, v7 77,018, v142 105, table data 7,999, HD-AE5000 1,280,
`prom_a` 21,094, `prom_b` 69,348, `prom_c` 9,588, `prom_d` 1,096; sub-CPU boot and custom data
none (`tools/census_research_by_image.py out.json` in this repository splits the census's
JSON this way, with the census's own target rule).

> The thirteenth gated image, `kn5000_subprogram_v142_compressed.rom`, is deliberately
> outside the denominator: it is the v1.42 payload re-compressed, so its bytes are already
> counted under `v142`. Counting it would inflate the total with a duplicate.

### Reading those numbers honestly

**UNKNOWN went up, and that is the push working.** A header that says "purpose not
established — searched X and Y" grades UNKNOWN (when it is under 40 words; a longer one is
still listed as a research target), while a plausible name with no header
grades KNOWN-B. The lanes' rule was to replace names that *hid* a gap with admissions that
*state* it, so UNKNOWN rose from 12,357 B to 56,567 B while KNOWN-B fell by 3.87 MB — most
of that into KNOWN-A, some of it, correctly, into UNKNOWN. Two examples from the lane
reports: `prom_a`'s MIDI-in tables for two unidentified controllers now say so (192 B added
to research on purpose), and 24 streams in `prom_c`'s P7 pool are stated as unreferenced
(5,897 B). The admission is the true statement; the name it replaced was not.

**95.04 % is the instrument's grade, not an audited figure.** KNOWN-A is keyword-graded
(`grade_purpose()` in `scripts/analysis/data_range_census.py`), by either of two routes: a
header of eight or more words carrying two evidence tokens, or a descriptive
(non-address-derived) name with a header of six or more words carrying one — and in both
cases no admission phrase. The evidence list holds specific tokens (`read by`, `call site`,
`+0x`, `.py`, …) but also any `0x` and generic words such as `entry`, `header`, `format` and
`see `, so a header can earn an evidence token without citing any evidence. The only check of whether a grade means a reader
can say what the bytes are is a hand audit: 40 regions drawn from KNOWN-A ∪ KNOWN-B,
size-weighted, seed 90902 (`--load … --sample 40 --seed 90902`). **That audit was run on the
2026-09-02 tree and has not been repeated since Wave 2.** It found 3 of 40 failing outright —
7.5 %, Wilson 95 % interval 2.6 %–19.9 % — and a further 8 of 40 passing only at the
granularity of a whole blob. Its run is in `notes/data-census-2026-09-02/` and
`notes/DATA-CENSUS-2026-09-02.md`. Until the sample is redrawn from the current tree, quote
95.04 % together with that sentence.

**Some of the grading is known to be wrong in both directions** (listed for Wave 3 in
`notes/lanes/wave2-2026-09-25/WAVE3-LEADS.md` — the first two below under "Instruments",
the rest under "Open research"): a `NAME = expr` line is
taken for an instruction owning the next line's bytes; a comment run is kept open across
blank lines, so a file header can leak into the first object and flip it to "admits" (98 B
of false research target at `0xED0008` in v10, v9 and v7); a banner is credited only to
objects within six lines, so about 86 KB of one-line icon and bitmap `.incbin` entries whose
banner names their readers stay KNOWN-B; single-line headers are not credited; labels such
as `F64_2376` are read as address-derived; and `m_ldc_*` macro lines are graded as data.

### The instrument

Each image's source tree is mirrored with a synthetic label inserted in front of every
byte-emitting line, the mirror is assembled and **linked with the real linker script**, and
the marker addresses come out of the ELF symbol table — so byte `[addr(n), addr(n+1))` is
attributed to the source line marker *n* was written in front of. Two properties make it a
measurement rather than a tally:

- **Inertness.** A label emits no bytes, so the marked mirror must still *be* the dump.
  Every image is objcopy'd to a raw binary and compared against `original_ROMs/`: **12 of
  12 byte-identical.** A mirror that is not inert is refused rather than reported.
- **Reconciliation.** Every byte lands in exactly one bucket and the per-image total must
  equal the dump size; **the run aborts on a non-zero delta.**

The CODE/DATA split is corroborated by a completely separate instrument,
`scripts/analysis/l1_territory_map.py`, which flattens the maincpu images through
`llvm-mc -show-encoding` and never sees a marker or a symbol table.

### What the census structurally cannot see

1. **It classifies by the source's own framing.** A byte inside a `.byte` directive is DATA
   here even when it is a TLCS-900 instruction, and a byte inside an instruction is CODE
   here even when it is a string. Both errors exist in this tree — see the three kinds of
   debt above.
2. **A region is only as explained as the one label and header attached to it.** A
   C-compiled struct can enter the ROM as a single large `.incbin` whose labels are offsets
   into it, so a region can be much larger than the object its label names. **103 regions of
   ≥ 8 KiB carry 3,014,878 B — 43.1 % of the explained figure — and 26 regions of ≥ 32 KiB
   carry 1,703,154 B.**
3. **A self-admitted open question is not the same as an unexplained region.** A header
   asking one question about an otherwise understood object — a font whose role, metrics
   and loader are all established but whose encoding is not — trips the flag anyway. The
   largest single research target, 15,120 B of `prom_b` fonts, is of that kind.
4. **The FILLER rule is byte-verified but arbitrary at the edge**: uniform and ≥ 16 B.
   Shorter uniform runs are graded as data.

### Code that may be misclassified as data

Three independent flags, reported as leads and not verdicts. Nothing is converted on the
strength of them.

| flag | regions | bytes | what it means |
|---|---:|---:|---|
| embedded-in-code | 3,687 | 20,547 | an undocumented data region with an *instruction* region on both sides in the same file |
| code-shaped label | 8,812 | 360,387 | the label carries a routine token (`_Loop`, `_Prologue`, `_Dispatch`, `Initialize*`, …) |
| code-suspect | 1,100 | 25,424 | a label at or inside the region is the target of a `call`/`jp`/`jr`/`jrl` somewhere in the tree |

The name-based flag comes with its null, because without one it would be worthless: 55.1 %
of regions the source itself frames as CODE carry such a name, against 4.1 % of the data
regions of the three pure-data images (`table_data`, `custom_data`, `prom_d`), where a hit
can only be a false positive.

### Disassembly status diagram

![ROM Status Diagram]({{ "/assets/images/rom-status-diagram.png" | relative_url }})

**Legend:** green = disassembled code · blue = known data structures · cyan = strings ·
light green = pointer/jump tables · purple = binary includes · red = raw bytes, unknown ·
orange = raw bytes known to be code · gray = padding/unused · yellow = undetermined.
Rectangle width is proportional to ROM size.

> **This image is stale.** It was generated on 2026-02-07, before the source tree was
> reorganised per firmware version, and `scripts/build/generate_rom_status_diagram.py`
> still looks for the pre-split ASL paths (`maincpu/kn5000_v10_program.asm`, …) that no
> longer exist. Treat the picture as historical until the generator is repointed at the
> `.s` sources; the tables above are measured from the current tree.

## Original ROM Files

The original firmware dumps are stored in `original_ROMs/`:

| File | Size | Description |
|------|------|-------------|
| `kn5000_v10_program.rom` | 2MB | Main CPU program ROM (also v9, v7) |
| `kn5000_subprogram_v142.rom` | 192KB | Sub CPU payload (sent by main CPU at boot) |
| `kn5000_subprogram_v142_compressed.rom` | 93,203B | Same payload as shipped on update disks |
| `kn5000_subcpu_boot.ic30` | 128KB | Sub CPU boot ROM |
| `kn5000_table_data_rom_odd.ic1` | 1MB | Table data ROM (odd words) |
| `kn5000_table_data_rom_even.ic3` | 1MB | Table data ROM (even words) |
| `kn5000_custom_data.ic19` | 1MB | Custom data flash (user storage) |
| `hd-ae5000_v2_06i.ic4` | 512KB | HDAE5000 hard disk expansion ROM |

**ROM interleaving:** the table-data ROM uses 16-bit **word-level** interleaving across two
physical chips. `kn5000_table_data.rom` is built by alternating 16-bit words from
`odd.ic1` and `even.ic3`, not individual bytes.

## Dump Provenance

Byte-identity of a rebuild says nothing about whether the *original* file is a complete,
faithful image of the physical part. Two of the files above are known not to be, and this
section records what is measured versus what is assumed. It matters because everything
downstream inherits the assumption.

### `kn5000_subcpu_boot.ic30` — partially dumped, deliberately

**Owner testimony (Felipe, 2026-08-08), which is ground truth about what was physically
done.** IC30 was dumped in small chunks, because the tooling could only copy a limited
amount at a time. He read the regions that appeared to hold the boot code needed to make
the emulator work, analysed that code, and — as far as he could assess at the time — found
no references to addresses in the regions he had not read. He concluded the remainder was
very likely `0xFF`. **He calls this an educated guess, not a fact**, and intends a full
dump when he regains physical access to the instrument (it is currently in storage in
another country).

What is measured in the file today:

| Quantity | Value |
|---|---|
| File size | 131,072 bytes (`sha1 d29429a9…`) |
| Bytes that are not `0xFF` | **4,352 — 3.3% of the chip** |
| Non-`0xFF` content, block 1 | file `0x18000-0x1904C` = CPU `0xFF8000-0xFF904C`, 4,173 B |
| Non-`0xFF` content, block 2 | file `0x1FE80-0x1FFB3` = CPU `0xFFFE80-0xFFFFB3`, 308 B |
| Non-`0xFF` content, block 3 | file `0x1FFF0-0x1FFFF` = CPU `0xFFFFF0-0xFFFFFF`, 16 B |
| Windows actually read | `0xFE0000-0xFE07FF`, `0xFF7800-0xFF97FF`, `0xFFF000-0xFFFFFF` — 14,336 B, 10.9% of the chip |
| Bytes never read | **116,736 — 89.1%**, present in the file as assumed `0xFF` |

The three window sizes are corroborated by the driver's own comment and by the owner's
dump script, whose chunking constant is `0x800`. But note that **the window boundaries are
documentary, not measurable**: a byte that was read and came back blank is
byte-indistinguishable from a byte that was never read. Roughly 10 KB of the ranges the
driver comment says *were* dumped are also `0xFF`.

MAME flags the file `BAD_DUMP` and states the assumption inline. A full re-dump would
convert 116,736 assumed bytes into measured ones and let that flag be removed.

**What the educated guess survives.** A structure-aware reference census over the
disassembled boot ROM — which rebuilds byte-identically, so the census is over ground
truth rather than a linear-decode guess — found **220 ROM-address operand references, all
in dumped windows, none in an undumped range**. The 45 live interrupt-vector entries, the
45 ROM trampolines, and the one indirect `CALL T,XWA` (bounded by an 8-entry table) all
resolve into dumped space, as do the only two callbacks the loaded v1.42 payload makes
into IC30 (`0xFFFEA1`, `0xFFFE86`). There is one honest counter-example, `ROM_CHECKSUM`
(`0xFF8AB4`), which reads 2 KB past the dumped window at `0xFE0000`; it is
content-independent and its only caller returns immediately unless a strap is asserted.

The code island also does not run up against a dump boundary anywhere: 2,048 blank bytes
precede it, 1,971 follow it, and the chip's first 2,048 bytes were read and came back
blank.

**What the guess does not yet survive: a rigorous check.** The adversarial re-verification
graded the educated guess **UNDECIDED**, not corroborated. Its objection
is method: the enumeration it asks for — the targets of real `JP`/`JR`/`CALL`/`CALR`
instructions plus the vector-table entries, taken out of a disassembly — has never been run
and committed as an auditable artifact, and raw byte scans *do* turn up candidates. Two
concrete ones: the little-endian long at `0xFF8C44` is `0x00FF42A3` and the one at
`0xFF8C4A` is `0x00FFCFEB`, both pointing into never-read space. Neither survives contact
with the source — both fall inside the black-key comparison chain of
`NOTE_VELOCITY_LOOKUP_CALCULATE`, and neither constant appears as an operand anywhere in
the assembly — which is exactly the point: at this data volume raw scans manufacture
coincidences, so only a structure-aware enumeration counts. Redoing the check properly is
cheap and is still outstanding. See
[Sub-CPU Boot ROM (IC30)]({{ site.baseurl }}/subcpu-boot-rom/) for the full record.

**What it cannot settle.** A full IC30 dump would *not* answer the sub-CPU payload
question. The payload is 196,608 bytes; the entire chip is 131,072; the undumped part is
116,736; the boot ROM has no decompressor; and IC30 is not in the main CPU's address space
at all. See
[Sub-CPU Payload Provenance]({{ site.baseurl }}/subcpu-payload-provenance/).

### `kn5000_custom_data.ic19` — real content, but missing the payload region

The image is a genuine chip read — the 77,824-byte block of `0x00` at chip `0x0C0000` is
actively programmed content, and flash erases to `0xFF`, so it cannot be padding. Ten
independent structural anchors land exactly where the firmware's own hardcoded pointers
say they should, which rules out any rotated, offset or wrapped read.

But the last non-`0xFF` byte is at chip `0x0D344F`, and chip `0x0E0000-0x0FFFFF`
(CPU `0x3E0000-0x3FFFFF`) — the sub-CPU payload staging area — is entirely blank. Since
every dumped firmware version reaches that source, **a machine matching this image could
not start its sub-CPU**. Whether the region was never programmed on that unit, or an
install was interrupted, or the dump is truncated and `0xFF`-padded, is **unresolved**:
the three are byte-indistinguishable in the file. The full argument, and the two free
measurements that would decide, are on
[Sub-CPU Payload Provenance]({{ site.baseurl }}/subcpu-payload-provenance/).

The MAME driver papers over the gap with a `ROMX_LOAD` overlay of the compressed payload
carved from a genuine update floppy. That composite is a **reconstruction**, and nothing
in the ROM definition marks it as one.

> Note also that `/home/fsanches/compartilhado/kn5000_custom_data_with_preset.ic19` is
> **not** independent chip evidence: it is byte-identical to the canonical dump except for
> a 27,967-byte SLIDE4K blob grafted at chip `0x0E0000` — a different, smaller blob than
> the 93,203-byte v1.42 subprogram.

### `kn5000_v10_program.rom` versus the physical program flash

A reasonable worry, given the KN7000 precedent — where the "program ROM" we hold turned out
to be the *update payload*, which deliberately omits the top `0x90FF` of the part and so
leaves it neither shipped nor dumped — is whether the KN5000 main-program image has the same
blind spot. (On the KN7000 that gap was for a while assumed to hold the resident updater;
[that assumption is refuted]({{ site.baseurl }}/kn7000-firmware-security/#45-where-does-the-flash-updater-live-unresolved)
— real hardware reads the region as erased — but the *payload is not the whole chip* point
stands, which is what makes the worry reasonable.)

**It does not.** The v10 update floppy's `HKMSPRG.SLD` carries a SLIDE4K stream whose
header declares a decompressed size of `0x200000` — the **full 2 MB** — and decoding it
reproduces `kn5000_v10_program.rom` byte for byte (2,097,152/2,097,152, consuming
965,545/965,545 input bytes; independently reproduced twice with separately written
decoders). The type 001h and 007h handlers chip-erase the pair before writing, so an
update rewrites the entire device and no region is left uncovered.

That identity does not by itself prove *how* the file was acquired — a chip read of a
v10-updated machine and a decompression of the disc must agree — but it makes the
distinction moot for preservation purposes.

The same measurement establishes the v10 ↔ v1.42 pairing as fact rather than inference:
both images come off the same floppy. The v141 → v7/v8 and v140 → v5/v6 pairings that
MAME's BIOS options assert are **not** measured — only the v10 disc is available here.

Reference disassembly files (`.unidasm`) are generated with MAME's `unidasm` tool for analysis.

## Assembler

The project uses a **custom LLVM backend** (`llvm-mc -triple=tlcs900`) for assembly. All
instructions are encoded natively — no workaround macros needed.

**Build process:**

1. `llvm-mc` assembles `.s` files to ELF object files
2. `ld.lld` links with a linker script that sets the ROM base address
3. `llvm-objcopy` extracts the raw binary from the ELF
4. generated payloads (demo presets, help databases, the v142 update image) are
   recompressed and `cmp`-checked
5. `compare_roms.py` verifies every section byte-for-byte against the originals

```bash
cd kn5000-roms-disasm

make gate-all                         # the gate: thirteen images, byte-exact or non-zero exit

# the full similarity report: expect FIFTEEN sections, all 100.00%
make clean-all && make all && make asl-all && python3 scripts/build/compare_roms.py

make all                              # LLVM sections only (nine) + compare
python3 scripts/build/compare_roms.py # compare whatever is already built
make verify-demo-presets              # 19/19
make verify-help-databases            # 6/6
make audit-icons-blob                 # coverage report for icons_to_strings.bin
```

**Two toolchains, and the LLVM one is authoritative.** The LLVM TLCS-900 backend encodes
the TLCS-900/H2 instruction set natively. A second set of sources for ASL (Alfred Arnold's
Macro Assembler) is archived in `archive/asl/` and is still built and verified; ASL supports
only the TMP96C141, so those sources carry 110+ workaround macros for the TMP94C241F's own
instructions — which is why they are the archived set and not the primary one.

## Source Organisation

Each firmware version has its own tree (`v7/`, `v9/`, `v10/` for the maincpu; `v142/` for
the sub-CPU payload), with `shared/` modules included by more than one ROM.

**The three maincpu trees are split by subsystem, not monolithic:** each is about 156 `.s`
files across roughly twenty directories, and the three carry the same file layout so a
routine sits at the same path in all of them. The remaining images are far smaller and are
not split that way — `v142/subcpu` is 5 files, `hdae5000` 8, `table_data` 26, and the
sub-CPU boot ROM and custom-data flash are a single file each.

Symbol names live outside the sources, in `symbols/*_symbols_reference.txt`; the three
maincpu trees share `maincpu_symbols_reference.txt` and each also has a per-version file.

File and line counts move with every conversion; measure them rather than quoting one:

```
find v10/maincpu -name '*.s' | wc -l
find v10/maincpu -name '*.s' -exec cat {} + | wc -l
```

The per-file breakdown lives on the [Source Code Map]({{ site.baseurl }}/source-map/) page,
and the diagram view of how the directories relate is on
[Architecture Flowchart]({{ site.baseurl }}/firmware-flowchart/).

### Instruction census

How the source spells its instructions, for the v10 main-CPU tree. Produced by

```
python3 notes/syntax-convergence-probes/mnemonic_census.py --root v10/maincpu
```

which prints to stdout and writes nothing unless given `--out`:

| Bucket | Sites | Distinct names |
|--------|------:|---------------:|
| Instruction statements, total | 336,011 | 359 |
| — a native LLVM mnemonic `unidasm` also has | 294,233 | 68 |
| — a tree-local synthetic name encoding the operand form | 40,071 | 266 |
| — a `.macro` defined inside the tree | 1,705 | 23 |
| — unclassified | 2 | 2 |

Of the synthetic names, 6,020 sites over 79 names are *byte emitters wearing a mnemonic's
name*: their operands are literal mode and displacement bytes rather than modelled operands,
so no rename reaches them until the operand is modelled. What retiring the rest would take is
on [LLVM Semantic Instructions]({{ site.baseurl }}/llvm-semantic-instructions/).

Symbol count is a `wc -l` on the reference file, which carries one symbol per line:

```
grep -c LABEL_ symbols/maincpu_symbols_reference.txt   # 0
```

The file's own header block carries the count, regenerated with it by
`scripts/analysis/l2_symbol_reference.py --regen` (last after Wave 2, at `be376096`):
**47,836 symbols**, of which 43,656 (91.3 %) have semantic names and 4,180 are positional. No opaque `LABEL_XXXXXX` placeholders remain, in
that file or in any of the other seven `symbols/*_symbols_reference.txt`. Note the file is
**v10 only** — it agrees with the v7 ELF at 25.96 % — so each version also has its own.

**Subsystem entry points (main CPU):**

- **FDC** — `storage/fdc_routines.s`: `FDC_COMMAND_DISPATCHER`, per-command handlers,
  `Reset_Floppy_Disk_Controller`, `Check_for_Floppy_Disk_Change`;
  `fdc_constants.s` holds the 0x110000-base I/O addresses, uPD765-compatible command
  codes and status-bit definitions.
- **MIDI / encoders** — `midi/midi_encoder_routines.s`: `CPanel_EncoderDispatch`,
  `Encoder_ProcessModwheel` / `Volume` / `Breath` / `Foot` / `Expression`.
- **Control panel** — `ui/cpanel_routines.s`: serial state machine (`CPanel_SM_*`),
  packet processors (`CPanel_RX_*`), LED control, buffer management.
- **SysEx** — `midi/sysex_routines.s`: `ExcSendFunc`, `ExcPmemFunc`, `ExcSmemFunc`,
  `ExcCompFunc`, `ExcSeqFunc`, `ExcMspFunc`.
- **Feature demo** — `demo/demo_routines.s`, `demo/fdemotext_routines.s`.
- **Computer interface** — `midi/computer_interface_config.s`,
  `midi/computer_interface_pcg.s`.
- **File I/O** — `file_io/`: title handlers, disk operations, filename/password UI,
  composer filters, SMF operations, wallpaper loading, single load, medley, misc UI.
- **GUI constants** — `gui_constants.s`: display dirty flags (0x0205E4), offscreen buffer
  addresses (0x043C00, 0x056800, 0x05FE00, 0x069400), 320×240 @ 8bpp.

## Sub CPU Boot ROM

The 128 KB sub-CPU boot ROM rebuilds at 100.00% — against a file that is 97% `0xFF` and
89% never read, so read that number together with [Dump Provenance](#dump-provenance)
above and with [Sub-CPU Boot ROM (IC30)]({{ site.baseurl }}/subcpu-boot-rom/). Routines
identified include the tone generator init loop (`SUB_8437`), register-pair writers,
`COPY_WORDS`/`FILL_WORDS`, `CHECKSUM_CALC`, the inter-CPU handler set, and the
debug/diagnostic tail at 0xFFFE80.

**DMA transfer routines (0xFF8604–0xFF881E):**

| Routine | Address | Size | Description |
|---------|---------|------|-------------|
| `SendData_Chunked` | 0xFF8604 | 69 bytes | Send data in 32-byte chunks via DMA |
| `InterCPU_SendChunk` | 0xFF8649 | 99 bytes | Send single data block via DMA |
| `SendCmd_E3` | 0xFF86AC | 48 bytes | Send E3 (payload ready) command |
| `SendParams_E2` | 0xFF86DC | 112 bytes | Wait for DMA, then send E2 command |
| `TwoPhase_Transfer` | 0xFF874C | 211 bytes | Two-phase DMA with E1 command, 200-cycle delays |

**The 656-byte data region at 0xFF8000–0xFF828F is now source.** A single `.incbin` was
hiding eight cross-referenced objects: an 8-entry command-handler jump table of `.long`
code pointers, a RAM-test region descriptor, and the tone generator's velocity/touch front
end. The last six of those objects also exist, byte-identical, in the v1.42 payload, so
they carry the payload's own names. The tree now contains no `.incbin` at all — the blob
file stays on disk only because the ASL mirror still `binclude`s it. Full breakdown:
[Sub-CPU Boot ROM (IC30)]({{ site.baseurl }}/subcpu-boot-rom/#4-the-656-byte-data-region-at-0xff8000).

Bear in mind what "rebuilds at 100.00%" means for this particular image: **116,736 of its
131,072 bytes were never read off the chip** and are present in the file as assumed `0xFF`,
and only 4,352 bytes in the whole image are not `0xFF`. Reproducing assumed bytes is not an
achievement. See the dump-provenance section above.

## Table Data ROM

The table-data ROM holds the first-stage bootloader plus almost all factory data. See
[Table Data ROM]({{ site.baseurl }}/table-data-rom/) for the region-by-region reference
and [Memory Map]({{ site.baseurl }}/memory-map/) for the current layout.

**First-stage bootloader (0x9FB496–0x9FFFFF).** All of it is now symbolic assembly. At
reset the table-data ROM is mapped at 0xE00000–0xFFFFFF, so ROM address 0x9Fxxxx executes
at boot-time alias 0xFFxxxx (+0x600000) until `Boot_Init` reprograms the memory
controller. Source labels are at ROM addresses; the 0xFFxxxx aliases appear in comments,
and the handful of `CALL`-absolute sites that must stay numeric are marked as such.

| Component | Address range | Module |
|-----------|---------------|--------|
| FDC dispatch offset tables | 0x9FB496–0x9FB4D1 | `kn5000_table_data.s` (three tables) |
| `Boot_BitMaskTable` + `Boot_InitParams` | 0x9FB4D2–0x9FB4E7 | `kn5000_table_data.s` |
| `Boot_Init`, halt handler, `Boot_ClearRAM` | 0x9FB4E8–0x9FB7F1 | `kn5000_table_data.s`, `shared/` |
| HDAE5000 boot-flash tail | 0x9FC6F6–0x9FC8C1 | `kn5000_table_data.s` (was `bootcode_hdae_to_lzss.bin`) |
| LZSS decoder suite | 0x9FC8C2–0x9FCC29 | `kn5000_table_data.s` (872 bytes, five routines) |
| FDC command-layer driver | 0x9FD8A5–0x9FEA9C | `boot_fdc_driver.s` |
| Disk-format probe | 0x9FEB2B–0x9FEC6D | `boot_disk_probe.s` |
| CP-serial driver (polling half) | 0x9FEC6E–0x9FF228 | `boot_cpserial.s` |
| CP-serial ISRs | 0x9FF229–0x9FF2F1 | `boot_cpserial_isr.s` |
| CP-serial state handlers/codecs | 0x9FF2F2–0x9FFB2E | `boot_cpserial_states.s` |
| Boot C runtime | 0x9FFB2F–0x9FFE7F | `boot_clib.s` |
| Debug group (disabled) | 0x9FFE80–0x9FFEDF | `boot_debug.s` |
| `RESET_HANDLER` + IVT | 0x9FFEE0–0x9FFFFF | `kn5000_table_data.s` |

The LZSS decoder is SLIDE4K (4 KB sliding window, 12-bit offset, 4-bit length) and is
invoked during flash firmware updates:

| Routine | Address | Size | Purpose |
|---------|---------|------|---------|
| `LZSS_ReadByte` | 0x9FC8C2 | 115 bytes | Read from compressed stream with sector buffering |
| `LZSS_OutputByte` | 0x9FC935 | 63 bytes | Write decompressed bytes with 32-bit batching |
| `LZSS_OutputByte_Alt` | 0x9FC974 | 63 bytes | Alternative output for flash update mode |
| `LZSS_ParseHeader` | 0x9FC9B3 | 157 bytes | Parse/validate firmware header, set up source |
| `LZSS_Decompress` | 0x9FCA50 | 474 bytes | Main decompression loop with sliding window |

(The 4 KB/8 KB *variant* dispatch lives in the main-CPU firmware, not here — see the help
database note above.)

**System update bitmaps (shared with the main CPU).** Eight 1-bit monochrome images
(224×22 px, 616 bytes each) at 0x9FA156, byte-identical to the main-CPU copies; both ROMs
`.incbin` the same files.

| Address | Image |
|---------|-------|
| 0x9FA156 | Flash Memory Update |
| 0x9FA3BE | Now Erasing |
| 0x9FA626 | FD to Flash Memory |
| 0x9FA88E | Completed |
| 0x9FAAF6 | Please Wait |
| 0x9FAD5E | Change FD 2 of 2 |
| 0x9FAFC6 | Illegal Disk |
| 0x9FB22E | Turn On AGAIN |

**Key discovery (still valid):** the interrupt vector table holds boot-time addresses
(0xFFxxxx) precisely because of the reset-time mapping described above.

### Shared source with the Main CPU

Several bootloader routines are byte-identical or semantically identical to main-CPU
utilities — both ROMs were built from common source. The disassembly now uses real shared
modules in `shared/`:

| File | Description |
|------|-------------|
| `shared/vga_constants.s` | VGA register addresses and constants |
| `shared/vga_init.s` | VGA initialization data + completion code |
| `shared/vga_io.s` | VGA register I/O routines (byte-identical between ROMs) |
| `shared/boot_call_init_handlers.s` | Init handler dispatch (conditional assembly) |
| `shared/boot_routines.s` | Boot initialization routines + LZSS decoder |
| `shared/macros.s`, `shared/sfr_tmp94c241.s` | Macros and SFR definitions |

**Shared routine mapping:**

| Table Data | Main CPU | Size | Routine |
|------------|----------|------|---------|
| 0x9FCDFC-0x9FCE1D | 0xEF5141-0xEF515F | 30-34 bytes | `Write_VGA_Register`, `Read_VGA_Register` |
| 0x9FB70A-0x9FB73F | 0xEF086F-0xEF08A3 | 53-54 bytes | `Boot_CallInitHandlers` |
| 0x9FCD9A-0x9FD7BD | 0xEF50DF-0xEF5B02 | 2,596 bytes | `VRAM_FillRect` and display routines |
| 0x9FBC3C-0x9FBECF | 0xEF3CE0-0xEF3F73 | 660 bytes | Boot utility routines |
| 0x9FB4F2-0x9FB622 | 0xEF03D0-0xEF0500 | 305 bytes | Boot initialization code |

Where the two ROMs differ in encoding (byte vs word compare, different helper addresses),
conditional assembly handles it — each ROM defines the required parameters before
including the shared file.

## Technical Notes

### TMP94C241F vs TMP96C141

Instructions unique to TMP94C241F that required macro workarounds under ASL:

- Memory-to-memory `LD` (not supported by TLCS-900)
- Certain shift/rotate variants
- Some MUL/DIV variants
- LDI, LDIR, LDD, LDDR block transfer instructions
- DMA control register access (`LDC` with DMAS/DMAD/DMAC/DMAM registers)

The LLVM backend encodes all of these natively; the macro tables below document the
archived ASL mirror, which is still built.

### ASL Macro Workarounds (tmp94c241.inc)

**DMA register macros:**

| Macro | Encoding | Description |
|-------|----------|-------------|
| `LDC_DMAS0_XWA` | `e8 2e 00` | Load DMA source 0 from XWA |
| `LDC_DMAS2_XDE` | `ea 2e 08` | Load DMA source 2 from XDE |
| `LDC_DMAS2_XHL` | `eb 2e 08` | Load DMA source 2 from XHL |
| `LDC_DMAD0_XWA` | `e8 2e 20` | Load DMA destination 0 from XWA |
| `LDC_DMAD0_XBC` | `e9 2e 20` | Load DMA destination 0 from XBC |
| `LDC_DMAD2_XWA` | `e8 2e 28` | Load DMA destination 2 from XWA |
| `LDC_DMAC0_WA` | `d8 2e 40` | Load DMA count 0 from WA |
| `LDC_DMAC0_A` | `c9 2e 42` | Load DMA count 0 from A |
| `LDC_DMAC2_A` | `c9 2e 4a` | Load DMA count 2 from A |
| `LDC_DMAC2_BC` | `d9 2e 48` | Load DMA count 2 from BC |
| `LDC_DMAC2_WA` | `d8 2e 48` | Load DMA count 2 from WA |

**Additional sub CPU boot ROM macros:**

| Macro | Encoding | Description |
|-------|----------|-------------|
| `INC_0_XBC` | `e9 60` | Increment XBC by 1 |
| `PUSH_WORD value` | `0b LL HH` | Push 16-bit immediate |
| `CP_pXWA_WORD value` | `90 3f LL HH` | Compare (XWA) with 16-bit immediate |
| `CP_pXBC_d_WORD d,val` | `99 dd 3f LL HH` | Compare (XBC+d) with 16-bit immediate |
| `LDA_XWA_IMM24 value` | `f2 LL MM HH 30` | Load 24-bit address into XWA |
| `CALR target` | `1e LL HH` | Call relative (3-byte encoding) |
| `CALL_ABS24 target` | `1d LL MM HH` | Call absolute with 24-bit address |
| `JRL_T target` | `78 LL HH` | Jump relative long (always true) |
| `LDIR_94` | `83 11` | Block copy (TMP94C241 encoding) |
| `LD_A value` | `21 nn` | Load immediate to A register |
| `LD_D value` | `24 nn` | Load immediate to D register |
| `LD_E value` | `25 nn` | Load immediate to E register |
| `LD_L value` | `27 nn` | Load immediate to L register |
| `LD_W value` | `20 nn` | Load immediate to W register |
| `LD_pXIX_IMM16 value` | `b4 02 LL HH` | Store 16-bit imm to (XIX) |
| `LD_pXHL_IMM16 value` | `b3 02 LL HH` | Store 16-bit imm to (XHL) |
| `LD_MEM24_IMM16 addr,val` | `f2 LL MM HH 02 VV WW` | Store 16-bit to 24-bit addr |

**Stack frame and register macros (DMA routines):**

| Macro | Encoding | Description |
|-------|----------|-------------|
| `DEC_6_XSP` | `ef 6e` | Decrement XSP by 6 (allocate stack frame) |
| `INC_6_XSP` | `ef 66` | Increment XSP by 6 (deallocate stack frame) |
| `LD_IZ_BC` | `d9 8e` | Load IZ from BC |
| `CP_IZ_imm16 val` | `de cf LL HH` | Compare IZ with 16-bit immediate |
| `SUB_IZ_imm16 val` | `de ca LL HH` | Subtract 16-bit immediate from IZ |
| `LD_C_IZL` | `c7 f8 8b` | Load C from low byte of IZ |
| `EXTZ_WA` | `d8 12` | Zero-extend A to WA |
| `EXTZ_BC` | `d9 12` | Zero-extend C to BC |

**Stack-relative addressing macros:**

| Macro | Encoding | Description |
|-------|----------|-------------|
| `LD_A_pXSP_d disp` | `8f dd 21` | Load A from (XSP+disp) |
| `LD_XDE_pXSP_d disp` | `af dd 22` | Load XDE from (XSP+disp) |
| `LD_XBC_pXSP_d disp` | `af dd 21` | Load XBC from (XSP+disp) |
| `LD_pXSP_d_A disp` | `bf dd 41` | Store A to (XSP+disp) |
| `LD_pXSP_d_XDE disp` | `bf dd 62` | Store XDE to (XSP+disp) |
| `ADD_pXSP_d_XWA disp` | `af dd 88` | Add XWA to (XSP+disp) |

### Encoding Differences

ASL sometimes chooses different (but functionally equivalent) encodings than the original ROM:

| Instruction | Original | ASL Default | Notes |
|-------------|----------|-------------|-------|
| `lda XWA, imm16` | 5-byte (24-bit addr) | 4-byte (16-bit) | Use `LDA_XWA_IMM24` macro |
| `call addr` | 3-byte `calr` | 4-byte `call` | Use `CALR` macro when target is within range |
| `jp addr` | 3-byte `jrl T` | 4-byte `jp` | Use `JRL_T` macro for relative long jump |
| `ldir` | `83 11` | `85 11` | Use `LDIR_94` macro for TMP94C241 encoding |
| `ld A, imm8` | `21 nn` | Different | Use `LD_A` macro |
| `ld D, imm8` | `24 nn` | Different | Use `LD_D` macro |

## How the source represents the ROM

### Code spelled as data

Executable code is written as native TLCS-900 mnemonics wherever it has been identified as
code. It is **not** true that no code remains as `.byte`: the sub-CPU payload, the sub-CPU
boot ROM, table data, custom data, `prom_b` and `prom_c` are at zero, while v7, HD-AE5000
and `prom_a` still hold instructions spelled as data — in `prom_a`, 298 certified `.byte`
instruction sites (1,318 B, 89 forms) at disassembly commit `be376096`; under the current
assembler pin (`8e188b215251`) 282 of them have no spelling found so far that reassembles
byte-identically, and the other 16 are spellable and being respelled. The per-image figures and the method
that measures them are on
[Raw Byte Code Elimination]({{ site.baseurl }}/raw-byte-code-elimination/).

### Data tables held as C

Structured data is source as typed C rather than byte arrays wherever the shape is known:
15 sound-data files in `audio/sound_data/` and 29 NAKA widget descriptor blocks are
`__attribute__((packed))` struct initializers with named fields and `_Static_assert` size
checks, compiled and `.incbin`'d so the ROM stays byte-identical. These are data only —
**no firmware routine is written in C**; see
[ScreenData C conversion]({{ site.baseurl }}/screendata-c-conversion/) and
[UI Widget Types]({{ site.baseurl }}/ui-widget-types/).

The IC307 waveform ROM's format is decoded — 16-bit signed PCM at 32 kHz with a 512-entry
sample table — on [Waveform ROM Format]({{ site.baseurl }}/waveform-rom-format/).

### Binary include splitting policy

Binary includes are split whenever code references an address inside them, so that
cross-references use symbolic labels instead of hardcoded addresses and structure
boundaries are explicit. A slice must also carry a label, a length and a comment saying what
it holds — an unnamed whole-file `.incbin` is treated as an unfinished conversion.
