---
layout: page
title: Table Data ROM
permalink: /table-data-rom/
---

# Table Data ROM Structure

The Table Data ROM is a 2 MB flash pair mapped at **0x800000-0x9FFFFF** after boot-time
memory reconfiguration. At power-on the CPU sees it at 0xE00000-0xFFFFFF (overlapping the
Program ROM), and the first-stage bootloader at the end of this ROM performs the hardware
setup before the remap. It holds the factory preset banks, the tone database, the on-screen
fonts and artwork, the Music Stylist and HELP databases, the demo songs, and the
first-stage bootloader itself.

**Conversion status.** As of the 2026-08-07 conversion waves this ROM is *fully accounted
for*: every byte is either symbolic assembly source or an explicitly labelled, named
binary slice, and the reconstruction is byte-exact against the dump (the disassembly
repo's build gate requires a 100 % byte-match after every merge). "Accounted for" is not
the same as "fully understood" — several regions below are correctly located and named but
their internal field semantics are still undecoded. Those are called out per section and
summarised under [What is still open](#what-is-still-open).

## Source modules

The top-level module is `table_data/kn5000_table_data.s` in the
[disassembly repo](https://github.com/ArqueologiaDigital/kn5000-roms-disasm); its banner is the
canonical table of contents. Large regions live in their own modules:

| Module | ROM range | Contents |
|:---|:---|:---|
| `preset_banks.s` | `0x800000-0x82FFFF` | Section directory + 26 bitmaps (the module name is historical: it holds no preset data) |
| `tone_database_directory.s` | `0x830000-0x8324D3` | Tone-DB directory, bank/program maps, 629-entry offset table |
| `tone_database_records.s` | `0x8324D4-0x855A47` | 579 tone/voice parameter records |
| `tone_database_aux.s` | `0x855A48-0x87FFEF` | Velocity-split records, multisample SET descriptors, key maps and zone records, drum kits, percussion, name lists |
| `kn5000_table_data.s` | `0x87FFF0-0x912BFF`, `0x938000-0x944D77`, `0x9999CC-0x9999D2`, `0x9B4000-0x9FFFFF` | Feature-demo assets, demo presets, wallpapers, icons, Composer image, bootloader (which it splits into the `boot_*` modules below) |
| `ui_bitmaps.s` | `0x912C00-0x937FFF` | Wallpaper trailer, UI bitmap/frame tables, factory image banks |
| `fonts.s` | `0x944D78-0x950FFF` | Font descriptor table + ten 1bpp glyph banks |
| `style_records.s` | `0x951000-0x983B39` | 1000 Music Stylist records + trailing residue |
| `help_databases.s` | `0x983B3A-0x9999CB` | Stale SLIDE8K remnant, HELP index/strings, five SLIDE8K databases |
| `style_record_ptr_tables.s` | `0x986000-0x987FFF` | The two 1000-entry Music Stylist pointer tables |
| `panel_memory_presets.s` | `0x99EC00-0x9ABF3F` | Panel Memory factory bank names + 80 preset records |
| `boot_fdc_driver.s` | `0x9FD8A5-0x9FEA9C` | Bootloader FDC command-layer driver |
| `boot_disk_probe.s` | `0x9FEB2B-0x9FEC6D` | Boot-time floppy disk-format probe |
| `boot_cpserial.s` | `0x9FEC6E-0x9FF228` | Boot-time control-panel serial driver (polling/setup half) |
| `boot_cpserial_isr.s` | `0x9FF229-0x9FF2F1` | INTA / INTTX1 / INTRX1 ISRs + state dispatch table |
| `boot_cpserial_states.s` | `0x9FF2F2-0x9FFB2E` | CP-serial state handlers, packet codecs, shared library tail |
| `boot_clib.s` | `0x9FFB2F-0x9FFE7F` | Boot heap allocator, memcmp, 32-bit divide/modulo runtime |
| `boot_debug.s` | `0x9FFE80-0x9FFEDF` | Debug character output — NOP-patched, disabled in shipped firmware |

## ROM layout

| Address range | Size | Contents |
|:---|:---|:---|
| `0x800000-0x800087` | 136 B | `SectionDirectory_Table` — 33 pointers + null terminator |
| `0x800088-0x82FFFF` | ~192 KB | 26 8bpp bitmaps of the section directory (entries 0-5, 8-27), the KN-5000 wordmark (entry 7) and 17 accessor routines at `0x82F000` |
| `0x830000-0x8324D3` | 9.2 KB | Tone-DB directory, bank maps, 629-entry offset table |
| `0x8324D4-0x855A47` | 141 KB | 579 tone/voice records |
| `0x855A48-0x87FFEF` | 169 KB | Tone-DB auxiliary tables + 0xFF fill |
| `0x87FFF0-0x880417` | 1 KB | `hkst_55.ssf` metadata + the SSF slideshow script |
| `0x880418-0x8CE01B` | 311 KB | Six feature-demo BMP images (`FTBMP01..06`) |
| `0x8CE01C-0x8CE0C9` | 174 B | Six `FeatureDemo_FileEntry` records + 30 zero bytes |
| `0x8CE0CA-0x8DFFFF` | 72 KB | 0xFF fill |
| `0x8E0000-0x8E6D3E` | 27,967 B | `DemoSongPreset18` — SLIDE4K Feature Demo preset |
| `0x8E6D3F-0x8ECFFF` | 25,281 B | 0xFF fill |
| `0x8ED000-0x8FFBFF` | 76,800 B | `Wallpaper_0` (320x240, 8bpp) |
| `0x8FFC00-0x8FFFFF` | 1 KB | Wallpaper_0 trailer + `Wallpaper0_ShadeRamp` at `0x8FFF80` |
| `0x900000-0x912BFF` | 76,800 B | `Wallpaper_1` (320x240, 8bpp) |
| `0x912C00-0x912FFF` | 1 KB | Wallpaper_1 trailer: five 16-entry shade-ramp tables |
| `0x913000-0x913117` | 280 B | `BitmapDescriptorTable` — 34 entries + terminator |
| `0x913118-0x91CE19` | 39 KB | UI bitmap pixel runs |
| `0x91CE1A-0x91CFFF` | 486 B | 0xFF fill |
| `0x91D000-0x933FFF` | 92 KB | Section banks 6, 28-32 — factory UI images |
| `0x934000-0x9341AF` | 432 B | `FrameDescriptorTable` — 53 entries + terminator |
| `0x9341B0-0x9373F3` | 12.6 KB | UI frame-piece pixel runs |
| `0x9373F4-0x937FFF` | 3,084 B | 0xFF fill |
| `0x938000-0x938587` | 1,416 B | `IconTable` — 176 entries + terminator |
| `0x938588-0x944D77` | 50 KB | Icon pixel data (176 icons + 1 unreferenced + pad) |
| `0x944D78-0x945BFF` | 3,720 B | 0xFF fill |
| `0x945C00-0x945CAF` | 176 B | `FontDescriptor_Table` — 10 fonts + one unused slot |
| `0x945CB0-0x950A5F` | 43 KB | Font glyph banks + `Font5_KernTable` |
| `0x950A60-0x950FFF` | 1,440 B | 0xFF fill |
| `0x951000-0x98156F` | 193 KB | Music Stylist records — 1000 x 198 B |
| `0x981570-0x983B39` | 9.4 KB | Unreferenced residue of an older flash generation |
| `0x983B3A-0x985FFF` | 9.2 KB | Stale, truncated SLIDE8K German HELP database |
| `0x986000-0x986FFF` | 4 KB | `StyleRec_PtrTable_C2C5` + residue |
| `0x987000-0x987FFF` | 4 KB | `StyleRec_PtrTable_Default` + residue |
| `0x988000-0x98868F` | 1.6 KB | HELP language index (2 x 6 pointers) + five intro strings |
| `0x988690-0x9999CB` | 69 KB | Five live SLIDE8K HELP databases |
| `0x9999CC-0x9999D2` | 7 B | `HelpDB_TrailingResidue` — stray bytes, referenced by nothing |
| `0x9999D3-0x99EBFF` | 21,037 B | 0xFF fill |
| `0x99EC00-0x99EC9F` | 160 B | `PanelMemory_BankNames` — 10 x 16 chars |
| `0x99ECA0-0x9ABF3F` | 53,920 B | 80 Panel Memory factory presets (674 B each) |
| `0x9ABF40-0x9B3FFF` | 32,960 B | 0xFF fill |
| `0x9B4000-0x9C3FFF` | 64 KB | `Composer_FactoryMemoryImage` |
| `0x9C4000-0x9C404F` | 80 B | `DemoSongPreset_PointerTable` — 19 entries + null |
| `0x9C4050-0x9F94CA` | 213 KB | SLIDE4K demo-song presets 0-17 |
| `0x9F94CB-0x9F9FFF` | 2,869 B | 0xFF fill |
| `0x9FA000-0x9FA14F` | 336 B | File identifier strings (floppy format IDs) |
| `0x9FA150-0x9FB495` | 4.9 KB | `"SLIDE"` marker + eight 1bpp boot-screen bitmaps |
| `0x9FB496-0x9FB4D1` | 60 B | Three FDC bootloader dispatch offset tables |
| `0x9FB4D2-0x9FB4E7` | 22 B | `Boot_BitMaskTable` + `Boot_InitParams` |
| `0x9FB4E8-0x9FFEDF` | 18 KB | First-stage bootloader code |
| `0x9FFEE0-0x9FFEFF` | 32 B | `RESET_HANDLER` + reserved bytes |
| `0x9FFF00-0x9FFFFF` | 256 B | TMP94C241F interrupt vector table |

## Section directory and bitmap bank (0x800000)

The ROM opens with a 34-entry table of 4-byte little-endian pointers, `SectionDirectory_Table`:
33 targets plus a null terminator. The targets are not in address order. Entry 7 points
backwards into this half (`0x82CDA2`), and entries 6 and 28-32 point *forward* into the
UI-bitmap half of the ROM at `0x91D000` and above.

**Every one of the 33 targets is an 8bpp indexed bitmap** (the `tdata` lane, September 2026).
Each is byte-identical to an image the program ROM carries for itself and that the
disassembly already extracts under `v10/maincpu/images/`, so the source now emits each from
that file (`.incbin`, one line per image):

| entries | images |
|:---|:---|
| 0, 1 | accordion pictures, 120×95 ("accger16", "accita16") |
| 2 | a strip of small arrows, 294×6 |
| 3-5 | drawbar scale 8..1 with a red / white / black knob, 22×222 |
| 7 | the **KN-5000 wordmark**, 199×36 (previously "section 7, bitmap-like") |
| 8-11 | FADE IN / FADE OUT symbols and lettering |
| 12-24 | the split-point pictures, 58×52: none, then C … B |
| 25-27 | MIDI-connection diagrams, 296×108 |
| 6, 28-32 | Technics logo, KN5000 picture, note-edit and drum-edit backgrounds (in `ui_bitmaps.s`) |

Two independent checks fix the geometry. The 17 accessor routines at `0x82F000`
(`SectionInfo_SecNN`, previously 745 bytes of `.byte`) return (base, width, height) for
entries 0-11 and 28-32. And the entries tile `0x800088-0x82E9C1` with no gap, each target
being the previous one plus its image size.

**Readers: none found** for the directory or for these copies. Every target address was
searched as a 24-bit and a 32-bit little-endian constant in the v7/v9/v10 program ROMs, the
v1.42 Sub CPU program, custom data (IC19) and the HD-AE5000 ROM. The only hits are byte
coincidences; the program draws its **own** copies. The firmware does write this half: a
"`Technics KN5000 Table    DATA FILE 1/2`" update floppy rewrites the whole `0x800000` half
through `HANDLE_UPDATE_FILE_TYPE_ID_003h` → `Flash_BurnWithProgress` + `FDC_WriteSectors`.

> **Corrected.** This section used to call the region "the rewritable user-data area" holding
> "factory defaults for the user's sound/registration/Composer memories", with a fill-pattern
> legend (`0xF7`/`0xF8` "erased flash", `0x07`/`0x06` "default parameter values") and record
> grids found by autocorrelation (95 × 120 B, 222 × 22 B, 52 × 58 B, 108 × 296 B, …). The grids
> were real, because they are the images' row lengths and heights. The reading was wrong. The
> byte values are palette indices, and **`0xF7` is the transparent colour**. The per-slot
> "re-marking" of entries 12-24 (`0xFF` → `0xFE`, `0x00` → `0xFC`) is the split-point pictures
> recolouring the keys on one side of the split. The labels `PresetBank_SecNN` became
> `SectionBankNN_<image>` (`scripts/renaming/rename_tdata_section_banks.sed`). Evidence:
> `python3 scripts/analysis/tdata_evidence_probes.py` (checks `sections`, `sec07`,
> `accessors`), and the header of `table_data/preset_banks.s`.

This matters for the Sub CPU boot: `SubCPU_Send_Payload`'s fallback ships table data from
`0x800000` on, i.e. this bitmap bank. See the dispute note on
[LZSS Compression]({{ site.baseurl }}/lzss-compression/#preset-data-destination-dispute).

## Tone database (0x830000-0x87FFEF)

The upper 320 KB of the first megabyte is the **tone database** — the sound-parameter data
the Main CPU ships wholesale to the Sub CPU at boot. `SubCPU_Send_Payload` issues five
64 KB InterCPU E1 bulk transfers copying ROM `0x830000-0x87FFFF` to Sub-CPU work RAM
`0x050000-0x09FFFF`, so every offset inside the database is equally readable as a Sub-CPU
address. It contains the 629-entry tone-record offset table at `0x831B00`, 579
variable-length tone/voice records, drum kits, percussion instruments, drawbar presets,
name lists and envelope data.

See **[Tone Database]({{ site.baseurl }}/tone-database/)** for the full structure. It is
*not* duplicated here.

> **Superseded:** earlier revisions of this page described an "Instrument Patch Data"
> region at 0x832000-0x850000 with ~303 patches, derived from a string scan. The real
> structure is the tone database above; the record grid and record count come from the
> offset table, not from string spacing.

## Feature-demo assets (0x87FFF0-0x8CE0C9)

`FeatureDemo_FileMetadata` at `0x87FFF0` is a small file record for `hkst_55.ssf`, pointing
at the SSF slideshow script that follows. The filename does double duty as a **version
stamp**: `Boot_ParseSubCPUTimestamp` points `ParseInt16` at `0x87FFF5` — the "55" inside
`hkst_55.ssf` — so the digits in this filename are the table-data revision number the boot
code parses.

The script itself (`Feature_Demo_XML`) is one unbroken ASCII run in the SSF `ACTION`
format: 27 sequential `<ACT>` steps, each showing one display object. Most steps name a
slide image (`ftdemo01`, `ftdemo04`, ...); steps 16/17, 19/20 and 25 bring up the live
`Accordion`, `Drawbar` and `Sdmixer` UI widget pages between slides. See
[SSF Presentation System]({{ site.baseurl }}/ssf-presentation/) and
[Feature Demo]({{ site.baseurl }}/feature-demo/).

The six slide images are ordinary Windows 3.x BMP files (8bpp indexed, 256-colour palette,
320 px wide) stored verbatim, each echoed by a 24-byte `FeatureDemo_FileEntry` record at
`0x8CE01C` giving name, address and size:

| Label | Address | File | Size |
|:---|:---|:---|---:|
| `Feature_Bitmap_1` | `0x880418` | `FTBMP01.BMP` | 77,878 B |
| `Feature_Bitmap_2` | `0x89344E` | `FTBMP02.BMP` | 42,678 B |
| `Feature_Bitmap_3` | `0x89DB04` | `FTBMP03.BMP` | 39,478 B |
| `Feature_Bitmap_4` | `0x8A753A` | `FTBMP04.BMP` | 39,478 B |
| `Feature_Bitmap_5` | `0x8B0F70` | `FTBMP05.BMP` | 41,078 B |
| `Feature_Bitmap_6` | `0x8BAFE6` | `FTBMP06.BMP` | 77,878 B |

## Demo-song presets (SLIDE4K)

Nineteen compressed preset blocks hold the panel setups for the demo songs. Eighteen of
them (entries 0-17) sit at `0x9C4050-0x9F94CA`, abutting one another except for a single
`0xFF` pad byte at `0x9C9017`, with `0xFF` fill from `0x9F94CB` to the end of the region;
**entry 18, the Feature Demo preset, is stored apart at `0x8E0000`** and decompresses to
38,144 bytes. Its reader is the same as the others': `DemoSongPreset_PointerTable[18]`
(`0x9C4048`), which `Demo_ParseSlideHeader` passes to `SLIDE_Parse_Header` with destination
RAM `0x69800`. `SubCPU_Send_Payload` does not read it: that routine decompresses from
`0x3E0000` and falls back to `0x800000`. `Seq_CopyResourcePtrs` pairs demo number 18 with
the Feature Demo script (`hkst_55.ssf`). (Corrected in the source in September 2026, `tdata`
lane.)

`DemoSongPreset_PointerTable` at `0x9C4000` is the index: 19 four-byte LE pointers plus a
null terminator, read by the `Demo_GetPresetBaseForPart` family as
`sla wa, 2; add xwa, 0x9C4000; ld xwa, (xwa)`. A non-null entry means the SLIDE4K block it
points at is decompressed to RAM `0x69800`; a null entry for index 0-18 falls back to the
live preset area at `0x0AB000`.

Each block is an 11-byte header — 8-byte `"SLIDE4K\0"` magic plus a **24-bit big-endian**
decompressed size — followed by the LZSS stream. All 19 blocks are build products, and the
checked-in sources are **not** binaries: each preset ships as a MIDI file plus a YAML
sidecar (`table_data/includes/demo_presets/midi/demo_preset_NN.mid` +
`sidecar/demo_preset_NN.yaml`). `midi_to_preset.py` regenerates the decompressed preset and
`compress_lzss.py --strict --reference` recompresses it byte-identically; both `.bin` stages
are generated and git-ignored. Two errata worth recording from that verification:

* the size field is 24-bit **big**-endian, not little-endian as older notes stated;
* preset 17's LZSS stream ends at `0x9F5676`; the remaining ~15.9 KB of its slice is
  non-stream tail carried verbatim.

See [LZSS Compression]({{ site.baseurl }}/lzss-compression/) for the codec.

Entries 0-17 also survive verbatim, header and payload, in the dead tail of
`table_data/includes/icons_to_strings.bin` — a pre-conversion duplicate that no build
reads. See *The backing blob* below before treating it as a second copy of anything.

> **Superseded:** earlier revisions of this page called `0x9C4000` a "Waveform Sample
> Table" pointing at PCM samples. It is the demo-song preset pointer table; the KN5000's
> PCM waveforms live in the dedicated wave ROMs, not here.

## Wallpapers (0x8ED000, 0x900000)

Two 320x240 8bpp LCD background images, 76,800 bytes each. The Main CPU's wallpaper table at
`0xEAAE62` holds five 10-byte records `{+0 pixel pointer, +4 palette pointer, +8 zero word}`.
Records 0 and 1 are these two images and their trailers; records 2-4 point into custom-data
flash `0x3C0000` and RAM.

* **Wallpaper 0** (`0x8ED000`) — blue textured pattern
* **Wallpaper 1** (`0x900000`) — Technics-branded texture

`SetWallPaper` (0xF9A9EF) jumps to `ChangeWall`. `ChangeWall_Impl` (0xFAF237) stores
record+0, and `DrawWall` (0xFABB73) copies the image to the offscreen buffer at `0x43C00`.
**Each 1 KB trailer is a 256-entry palette of `{red, green, blue, 0}`.**
`ChangePalette_Impl` (0xFAF2F3) reads record+4 and copies entries 0x20-0xDF into the RAM
palette at `0x324FC` via `SetPaletteRGB`. `VGA_WritePaletteEntry` sends bytes +0, +1, +2 to
the DAC data port in that order. Every pixel of both images is in 0xE0-0xEF, the 16-shade
ramp at trailer `+0x380` (`Wallpaper0_ShadeRamp`, the `WallpaperRamp_*` set in
`ui_bitmaps.s`). The loader of entries 0xE0-0xEF (`ChangeWallPalette_Impl`, via the RAM
table at `0x3F1E4`) has not been traced back to that slot. The older note that "no code
reference to these ramps has been found" is superseded. The wallpaper table itself still
sits under the positional labels `ChangeWall_Impl_Data` / `ChangePalette_Impl_Data` in the main-CPU source.

## UI bitmaps, frames and icons (0x912C00-0x944D77)

This region was formerly one opaque blob whose filename claimed it was a gap. It is three
distinct drawing resources plus six factory images.

**`BitmapDescriptorTable` (`0x913000`)** — 34 entries of `{u16 width, u16 height, u32 ptr}`
plus a null terminator, indexed by the bitmap number passed to `DrawBitmap` /
`DrawBitmapFast` (`index * 8` added to `0x913000`). The set is the UI's photographic-style
artwork: transport controls, the vertical fader, the 307x45 outlined "Technics" wordmark,
a "GENERAL MIDI SPECIAL" logo, LED buttons, and sixteen 32x32 sound-category icons (violin,
trumpet, drum kit, flutes, electric guitar, grand piano, drawbars, accordion, ...). Entry 0
is a 24x24 green worm wearing a straw hat — an easter egg, byte-identical to the Main CPU
ROM's own copy at `0xEA9F20`.

**`FrameDescriptorTable` (`0x934000`)** — 53 entries in the same format, indexed by
`DrawFrameSP`. This is a UI frame construction kit: rounded-rectangle corner pieces in
sizes 1/2/5/9/14 (TL, TR, BR, BL order), chevron arrowheads in five sizes each direction,
"ON/OFF" soft-button bodies with a pointed tab aimed at the physical buttons beside the
LCD, red arrows, 5x5 bevel-corner overlays in raised/outlined/sunken styles, and a wide
tab-bar body.

Pixel format for both tables: **8bpp indexed, two pixels per 16-bit word**, rows padded to
16-bit alignment (odd-width images carry one pad byte per row). Colour `0xF7` is
transparent. In frame pieces colour `0xF6` is a *template* colour replaced at draw time by
the caller's colour argument — which is how one master shape serves every button state.

**Factory image banks (`0x91D000-0x933FFF`)** — the six blocks that section-directory
entries 6 and 28-32 point at. They are floppy save/load banks whose factory content is a
set of full UI images, each byte-identical to a copy already in the Main CPU ROM:

| Bank | Image | Size | Main CPU copy |
|:---|:---|:---|:---|
| 6 | Technics wordmark (black, transparent bg) | 312x45 | `0xE8FFA6` |
| 28 | The KN5000 itself on teal ("bmphk") | 100x120 | `0xE7BE12` |
| 29 | Vertical piano ruler, note-edit screen ("ntedt0k") | 16x127 | `0xE34E78` |
| 30 | Dotted note-edit grid ("ntedt0d") | 240x127 | `0xE35668` |
| 31 | Ruled instrument rows, drum-edit screen ("dredt0k") | 88x119 | `0xE3CD78` |
| 32 | Drum-edit grid ("dredt0d") | 168x119 | `0xE3F660` |

The original Matsushita asset names (`bmphk`, `ntedt0k`, `ntedt0d`, `dredt0k`, `dredt0d`)
survive in Main-CPU routine and widget names.

**Icons (`0x938000`)** — `IconTable` holds 176 entries of `{u16 bbox width, u16 bbox
height, u32 pixel pointer}` plus a terminator, indexed by the icon number passed to
`DrawIcons` (`0xFABF9B`). Every icon's pixel data is 24x24 at 4bpp (2 pixels per byte,
288 bytes, 12 bytes/row x 24 rows — `DrawIcons` hardcodes the geometry). The bounding-box
fields are UI hit-test dimensions only: icons 173-175 declare 27x27 or 28x28 but still
carry 24x24 pixels. A **177th icon** sits after the last referenced one — yellow "E.L.S."
lettering with small glyphs below, apparently a developer signature. No table entry points
at it, so it is unreachable art.

Icons use a 16-colour CGA/EGA-style palette; the lookup table at `0xEAABF2` in the Main CPU
ROM expands 4-bit nibbles to 8-bit palette indices into the main palette at `0xEB37DE`:

| Nibble | Palette index | Colour | Nibble | Palette index | Colour |
|:---|:---|:---|:---|:---|:---|
| 0 | `0x00` | Black | 8 | `0xF8` | Dark Gray |
| 1 | `0x01` | Dark Red | 9 | `0xF9` | Bright Red |
| 2 | `0x02` | Dark Green | 10 | `0xFA` | Bright Green |
| 3 | `0x03` | Olive | 11 | `0xFB` | Yellow |
| 4 | `0x04` | Dark Blue | 12 | `0xFC` | Bright Blue |
| 5 | `0x05` | Dark Magenta | 13 | `0xFD` | Magenta |
| 6 | `0x06` | Dark Cyan | 14 | `0xFE` | Cyan |
| 7 | `0x07` | Light Gray (background) | 15 | `0xFF` | White |

Extracted renders of the icons and bitmaps are in the
[Image Gallery]({{ site.baseurl }}/image-gallery/).

## Fonts (0x944D78-0x950FFF)

`FontDescriptor_Table` at `0x945C00` holds ten 16-byte entries plus one all-zero unused
slot:

| Offset | Size | Field |
|:---|:---|:---|
| `+0x00` | word | Width in pixels (0 = proportional) |
| `+0x02` | word | Height in pixels |
| `+0x04` | word | Descender (pixels below baseline) |
| `+0x06` | word | Ascender (pixels above cap height) |
| `+0x08` | long | Pointer to the 1bpp glyph bank |
| `+0x0C` | long | Pointer to the kern table (0 = fixed width) |

Both consumers — `TextRender_LoadFontData` and `DrawString_Impl_ClipCursorYMin` in the Main
CPU ROM — compute `0x945C00 + 16 * font_id`. When the kern pointer is null they use `+0x00`
and `+0x06` for a fixed advance; otherwise the kern table drives per-character widths.

| Font | Geometry | Upper code page | Notes |
|:---|:---|:---|:---|
| 0 | 8x16 fixed | UI symbols | Same letterforms as font 7 over 0x20-0x7E |
| 1 | 8x16 fixed | UI symbols | Glyphs sit 2 px higher in the cell than font 0 |
| 2 | 16x16 fixed | UI symbols | Double-width headline font |
| 3 | 6x8 fixed | UI symbols | Small font |
| 4 | 11x16 fixed | UI symbols | Same letterforms as font 9 over 0x20-0x7E |
| 5 | proportional, 16 px tall | Latin-1 accents | Only proportional font; widths 3-10 px |
| 6 | 8x10 fixed | UI symbols | Compact font |
| 7 | 8x16 fixed | Latin-1 accents | Font 0 letterforms |
| 8 | 8x16 fixed | Latin-1 accents | Font 1 letterforms |
| 9 | 11x16 fixed | Latin-1 accents | Font 4 letterforms |

Every bank covers characters 0x20-0xFF (224 glyphs — the renderer does `sub c, 0x20`).
A glyph is stored **column-major**: `ceil(width/8)` columns of `height` bytes each,
top-to-bottom, MSB = leftmost pixel of the 8-pixel column slice. The nine fixed banks tile
their address ranges exactly with no gaps. Font 5's kern table holds 224
`{u16 char_width, u16 glyph_offset}` pairs whose entries tile `0x94B7B0-0x94C61F` exactly.

The two upper-code-page flavours matter for the multilingual UI: fonts 0/1/2/3/4/6 use the
0x7F-0xFF range for arrows and markers with empty-box placeholders in the Latin-1 letter
slots, while fonts 5/7/8/9 carry real Latin-1 accented characters.

Font 9's bank runs past the `0x950000` boundary — characters 0xAD-0xFF live at
`0x950000-0x950A5F`. That area was previously misfiled as standalone "sparse bitmap-like
data"; it is simply the tail of font 9.

## Music Stylist database (0x951000-0x987FFF)

One thousand 198-byte records at `0x951000` hold the MUSIC STYLIST presets — 250 styles x 4
arrangement variations across ten categories — reached exclusively through two 1000-entry
pointer tables at `0x986000` and `0x987000`.

See **[Music Stylist Database]({{ site.baseurl }}/music-stylist-database/)** for the record layout,
category boundaries and the two table orderings.

> **Superseded:** earlier revisions of this page called `0x986000`/`0x987000`
> "model-specific preset tables" selected by a keyboard model code (0xC2 = KN3000,
> 0xC5 = KN5000). The selector byte at RAM `0x8D38` is the **current UI state ID**, not a
> model code: `EffectMode_ClampAndLookupPreset` picks the `0x986000` table for UI states
> 0xC2 and 0xC5 and the `0x987000` table for every other state.

## Help system (0x983B3A-0x9999D2)

Press HELP and then any panel button, and the firmware looks that button up in the active
language's database and renders the explanation.

The index at `0x988000` is **not** a demo-song table: it is the HELP language index, twelve
4-byte LE pointers forming two parallel 6-slot tables, both indexed by the help-language
number in RAM `0x0340E4`:

| Address | Table | Slot 0 | 1 | 2 | 3 | 4 | 5 |
|:---|:---|:---|:---|:---|:---|:---|:---|
| `0x988000` | `HelpIntro_LanguageTable` (intro strings) | EN `0x988030` | DE `0x988160` | FR `0x988296` | ES `0x988404` | EN again | ID `0x98855E` |
| `0x988018` | `HelpDB_LanguageTable` (SLIDE8K databases) | EN `0x988690` | DE `0x98BB3A` | FR `0x98F0DA` | ES `0x992A0C` | EN again | ID `0x9963FA` |

There are only five distinct languages (English, German, French, Spanish, Indonesian);
slot 4 of both tables reuses English. The intro strings at `0x988030-0x98868F` are the
null-terminated Latin-1 paragraphs shown on the HELP start screen (`~0d` is the newline
escape).

Each database is a **SLIDE8K** container — a previously undocumented 8 KB-window LZSS
variant that the firmware itself supports (`SLIDE_Parse_Header` dispatches on the `8` of
the magic to `SLIDE_Decompress_8K_Init`). The header is 11 bytes: `"SLIDE8K\0"` magic plus
a 24-bit big-endian decompressed size. The stream uses a 0x2000-byte ring pre-filled with
zeros and a write position starting at 0x1FF6, 13-bit absolute ring offsets and 3-10 byte
match lengths. Every block decompresses to exactly **0x9000 (36,864) bytes**: a
self-referential pointer table plus a help-string pool based at RAM `0x69800`.

Termination is purely by output count, so the final flag byte may be only partly consumed
and its unused bits are nonzero in these blocks; each stream is also odd-length and
followed by one alignment pad byte the decoder never reads. Only decision-replay against
the factory stream reproduces them byte-exactly, which is what the build does: the five
live payloads are **build products** recompressed from the decompressed sources in
`table_data/includes/help_databases/` by `compress_slide8k.py --strict --reference`, and
`make verify-help-databases` byte-compares all of them against the original slices.

A sixth, *stale* SLIDE8K block sits at `0x983B3A`: a superseded revision of the German
database, referenced by nothing in any program ROM (v7, v9 or v10). It is **truncated, not
merely corrupt** — the factory image wrote the two Music Stylist pointer tables at
`0x986000`/`0x987000` straight over its tail. Decoding it tracks the live German database
byte-for-byte for exactly 0x55E0 output bytes, and the element producing output 0x55E0 is
the first one to read past `0x985FFF`. Because its tail no longer exists it is preserved as
a raw, byte-exact slice of the dump rather than rebuilt from source.

Seven stray bytes follow the Indonesian database at `0x9999CC`: three `(0x7F, N)` pairs with
N stepping by 10 (`0xD8`, `0xE2`, `0xEC`) plus a lone `0x7E` — the tail of some stride-10
table from an earlier factory build. No pointer to that address exists in any ROM.

> **Superseded:** earlier revisions of this page claimed demo-song sequence data began at
> `0x9999CC` and that demo category names lived at `0x99EC00`. Neither is true:
> `0x9999CC` is the seven residue bytes above, `0x9999D3-0x99EBFF` is 0xFF fill, and
> `0x99EC00` is the Panel Memory bank-name table (below). The demo songs' *presets* are the
> SLIDE4K blocks indexed from `0x9C4000`.

## Panel Memory and Composer factory data (0x99EC00-0x9C3FFF)

`PanelMemory_BankNames` at `0x99EC00` is ten 16-character space-padded bank names — "Tour
Of The 5000", "Accordion", "Piano Styles", "Jazz&Rock Organ", "Church & Theatre", "Light
Orchestra", "Split Sounds", "Layer Production", "Special DSP FX", "World" — followed at
`0x99ECA0` by 80 factory preset records of 674 bytes each (10 banks x 8 PANEL MEMORY
buttons).

`Composer_FactoryMemoryImage` at `0x9B4000` is a 64 KB image of the COMPOSER (user rhythm
style) memory, copied wholesale to RAM `0x94800` at boot. It carries three factory user
styles in four variations each (" Pop Samba 1".."4", "GentleSwing 1".."4", "German 3/4
1".."4") plus 18 empty "Clear" slots, and from image offset `+0xAB00` (ROM `0x9BEB00`) the
rhythm cell streams in the same cell grammar the factory rhythms use — 52 `80 nn 00 FF FF 87`
cell headers, each on a 256-byte boundary. (The module header's "+0xC000" is too late by
0x1500 bytes.)

See **[Panel Memory & Composer Factory Data]({{ site.baseurl }}/panel-memory-factory-data/)** for the
record format and the loader routines.

## File identifier strings (0x9FA000)

Format identification strings used to detect floppy disk file types:

* `Technics KN5000 Program  DATA FILE 1/2`
* `Technics KN5000 Program  DATA FILE 2/2`
* `Technics KN5000 Program  DATA FILE PCK`
* `Technics KN5000 Table    DATA FILE 1/2`
* `Technics KN5000 Table    DATA FILE 2/2`
* `Technics KN5000 Table    DATA FILE PCK`
* `Technics KN5000 CMPCUSTOMDATA FILE`
* `Technics KN5000 HD-AEPRG DATA FILE`

## Boot screen bitmaps (0x9FA150)

A `"SLIDE"` marker string, then eight headerless 1bpp bitmaps (224x22, 616 bytes each)
shown during a firmware update: "Flash Memory Update", "Now Erasing", "FD to Flash Memory",
"Completed", "Please Wait", "Change FD 2 of 2", "Illegal Disk", "Turn On AGAIN". They are
byte-identical duplicates of the eight bitmaps in the Main CPU ROM at `0xE0018E-0xE0148D`
and are emitted from the same image files, so the duplication stays single-sourced. See
[Firmware Update Display]({{ site.baseurl }}/firmware-update-display/).

## FDC dispatch offset tables (0x9FB496)

Three `.short` offset tables driving the `JP T, XIX+WA` dispatches in the bootloader's FDC
driver. Because the bootloader runs with this ROM mapped at 0xE00000-0xFFFFFF, the
consuming code references them as `0xFFB4xx`.

| Table | Consumed at | Indexed by |
|:---|:---|:---|
| `FDC_DiskTypeStanza_Offsets` | `0xFFD98F` (`FDC_MediaConfigAndRecalibrate`) | Low nibble of the media-type code at `0x0C9C`, values 0-5 |
| `FDC_ValidateCmd_Offsets` | `0xFFDA97` (`FDC_ValidateRequest`) | Command word at `0x0C6E`, 0-11 |
| `FDC_CommandDispatch_Offsets` | `0xFFE9F4` (`FDC_Request`) | Command word, 0-11 |

The first two are byte-identical to copies the Main CPU's own FDC driver carries at
`0xEA98A6` and `0xEA98B2`. All targets are labelled in `boot_fdc_driver.s`, so the entries
are now symbolic label differences rather than raw constants. See
[FDC Subsystem]({{ site.baseurl }}/fdc-subsystem/).

## First-stage bootloader (0x9FB4E8-0x9FFFFF)

`Boot_Init` at `0x9FB4E8` (boot-time `0xFFB4E8`) runs at power-on while the CPU still sees
this ROM at 0xFFxxxx. It initializes the CPU and memory controller from code shared with
the Main CPU ROM, sets the stack pointer from `0x00987E`, clears RAM, copies
`Boot_BitMaskTable` and `Boot_InitParams` to RAM `0x1044`/`0x9998`, detects the region code
and boot mode, checks for a firmware-update floppy, validates flash integrity, reconfigures
CS2 to move this ROM to 0x800000, and hands control to the main Program ROM.

The bootloader is a complete little system of its own, disassembled in Wave 1 and Wave 2 of
the conversion effort. Beyond `Boot_Init` it contains a shared VGA register-init block
(`0x9FCDFC-0x9FD7E7`), an FDC command-layer driver with twelve commands
(`0x9FD8A5-0x9FEA9C`, previously mislabelled "flash update handlers"), a floppy
disk-format probe, a **boot-time control-panel serial driver that is entirely independent
of the runtime CP-serial stack**, three serial ISRs with a state-machine dispatch table, a
first-fit heap allocator with coalescing free plus a 32-bit divide/modulo runtime, and a
NOP-patched debug-output group that emits nothing in shipped firmware. `RESET_HANDLER` sits
at `0x9FFEE0` and the TMP94C241F interrupt vector table occupies the last 256 bytes.

See [Boot Sequence]({{ site.baseurl }}/boot-sequence/) for the system-level view and
[Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) for the *runtime*
serial stack this boot driver must not be confused with.

## The backing blob (icons_to_strings.bin)

One artefact predates the whole conversion and still sits in the tree:
`table_data/includes/icons_to_strings.bin`, **742,024 bytes**, sha256
`0df126455434ccc35a9f40609ec26dc68edc2a170910de602a6fbe814f31379d`. It is a **verbatim
slice of the factory dump** — file offset 0 is ROM `0x944D78` and its last byte is ROM
`0x9F9FFF` — and as of commit `6ab2b5d` every one of those bytes is accounted for.

| Part | File offsets | ROM | Size | Status |
|:---|:---|:---|---:|:---|
| Read by the LLVM build | 13 sized `.incbin` slices | — | 126,674 B | live (17.1 % of the file) |
| Source-built here, still `binclude`d whole by the ASL mirror | remainder below `0x7F2D8` | `0x944D78-0x9C404F` | 394,246 B | live for the mirror only |
| Dead tail | `0x7F2D8-0xB5287` | `0x9C4050-0x9F9FFF` | 221,104 B | read by nothing |

The 13 live slices are the ten font glyph banks (`fonts.s`), the Music Stylist residue
block (`style_records.s`), the truncated stale German help block (`help_databases.s`) and
the 64 KB Composer factory memory image (`kn5000_table_data.s`). Every one lies inside the
extent the archived ASL mirror bincludes as a single block
(`binclude "includes/icons_to_strings.bin", 0, 07F2D8h`), which is why the file may not be
rewritten, re-sliced or truncated on disk even though the LLVM build now emits most of the
region from real source. The 80 bytes at file `0x7F288-0x7F2D7` (ROM `0x9C4000-0x9C404F`)
are the last thing the mirror still takes from the blob that this build emits from source:
`DemoSongPreset_PointerTable`'s 19 pointers plus its null terminator.

**The dead tail is a stale duplicate of the demo-song presets.** The 221,104 bytes past the
ASL extent are eighteen SLIDE4K blocks laid end to end — presets 0-17, one `0xFF`
alignment byte after preset 00 (ROM `0x9C9017`) and 2,869 bytes of `0xFF` fill after
preset 17's block ends at `0x9F94CA` — byte-identical to the reference payloads in
`original_ROMs/demo_preset_NN_compressed.original.bin`. Nothing reads them: not the LLVM
build, not the ASL mirror, not the bootstrap extraction (`make decompress-demo-presets`
reads `original_ROMs/kn5000_table_data.rom`, not this file). The ROM's live copy of those
bytes is rebuilt from `includes/demo_presets/midi/*.mid` plus its YAML sidecars.

The tail was **documented rather than removed**. Deleting it would save 221 KB and break
neither build, but it would rewrite a checked-in dump artefact whose hash is quoted in
`analysis/binclude-audit-2026-08-07/`; and re-slicing the region would give the
demo-preset bytes a *second* source, which is a byte-match trap. One practical
consequence: sweeping this file for the `SLIDE4K` magic finds eighteen headers past
`0x7F2D8` that are residue, not a newly discovered compressed region.

`make audit-icons-blob` (`scripts/analysis/audit_icons_blob_coverage.py`) re-derives the
whole map from the tree and the factory dump on every run and fails if any of it drifts.
It checks four invariants: that the blob is still byte-identical to
`original_ROMs/kn5000_table_data.rom` over its extent; that the ASL mirror still
bincludes exactly `0, 0x7F2D8`; that no LLVM slice reaches past that extent; and that the
dead tail is still exactly the eighteen preset blocks plus `0xFF` fill. It is not part of
`make all`.

## What is still open

The ROM is byte-complete in source form, but understanding lags behind location in several
places:

* **The section directory's reader.** All 33 targets are identified bitmaps, but nothing in
  any ROM we hold reads the directory (`SectionDirectory_Table`, 136 B) or these copies.
* **Wallpaper palette entries 0xE0-0xEF.** Entries 0x20-0xDF come from the trailer through
  `ChangePalette_Impl`. The 0xE0-0xEF shade ramp is loaded by `ChangeWallPalette_Impl` via
  RAM `0x3F1E4`, and what writes that RAM table is not found.
* **Panel Memory parameter payloads.** The chunk framing is settled. Each of the 80 records
  now carries its ROM/RAM addresses, but most payloads are still undecoded. The Music Stylist
  parameter block is decoded ([Music Stylist]({{ site.baseurl }}/music-stylist-database/#the-parameter-block)).
* **Icon names.** The 176 icons have no semantic names yet. `DrawIcons` callers take the
  icon id from widget fields (+50, +46, +22); icon 32 is the GENERAL MIDI logo, used by the
  GM on/off widget.
* **Boot disk types 1 and 3** both write `0x800000`/`0x900000`; how the chip is selected is
  not worked out.
* **Tone-record fields.** The record framing is exact; several fixed-value fields have no
  established meaning yet (see the tone-database page).
* **Housekeeping — settled.** Both items previously listed here are closed. The seven
  orphaned `bootcode_*.bin` files were deleted along with 25 other unreferenced
  extraction artefacts (commit `7280bce`; six `bootcode_*` remain because the archived
  ASL mirror still bincludes them). The dead tail of `includes/icons_to_strings.bin` was
  measured, explained and left in place on purpose — see *The backing blob* above.

Work on the wider disassembly is also unfinished: the v7 firmware tree has not been
converted, and the Main-CPU inline `.byte` audit is still pending. Neither affects the
table-data ROM's own coverage.
