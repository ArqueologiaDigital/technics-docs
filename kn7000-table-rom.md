---
layout: page
title: KN7000 Table ROM — Resource Archive
permalink: /kn7000-table-rom/
---

# Technics SX-KN7000 — table ROM resource archive

The KN7000's 4 MB **table ROM** (mapped at `0x48000000`: the half of the IC16/IC17 flash pair
where A22 is low, the program being the other half, interleaved in 16-bit words with IC17
holding the even words and IC16 the odd) is not code — it is a **directory-based resource
archive**. It opens with a table of little-endian u32 chunk offsets, and each entry points to a tagged resource.

## Chunk kinds

| Address      | Segment | Tag / content        | Meaning                                                                                                                                                                                                                                               |
|--------------|---------|----------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `0x48000000` |         | u32 offset directory | index of all chunks (first chunk at `0x48000200`)                                                                                                                                                                                                     |
| `0x48034858` | 1       | **`ZZZJ`**           | 220 battery-SRAM default records of eight program selections each ([below](#zzzj-segment-1))                                                                                                                                                          |
| `0x48035d08` | 2       | **`TCMP`**           | the factory rhythm-**style** container (3 built-in styles, " Easy 8 Beat " / "Easy 16 Beat " / " Easy Swing  "), copied by `memcpy_entry` to RAM `0x50180000` (`MEM_STYLE_AREA`) at boot — **data, not code**; nothing ever calls into that RAM range |
| `0x48040674` | 3       | **`TPAD`**           | the factory PERFORMANCE PAD user memory: 5 banks, 18 pads                                                                                                                                                                                             |
| `0x4804238c` | 4       | `Technics Pads`      | the built-in pad bank: 120 pads                                                                                                                                                                                                                       |
| `0x4806ea98` | 6       | **`JK`**             | the internal voice archive (832,592 bytes): tones, voices, zones ([below](#the-jk-internal-voice-archive))                                                                                                                                            |
| `0x48244f78` | 59      | style sub-table      | 52 built-in styles in the "Technics Rhythms" format (1,284,108 bytes)                                                                                                                                                                                 |
| `0x483e828c` | 83      | `Technics Rhythms`   | a copy of the rhythm ROM IC18's header and style-ID index (0x1248 bytes)                                                                                                                                                                              |
| (throughout) |         | **JFIF JPEG**        | 119 embedded UI/graphics images                                                                                                                                                                                                                       |

> **Correction.** An earlier pass here misread the copy of the `TCMP` chunk into RAM
> `0x50180000` as a **code overlay being executed** (the symbol was once named
> `RamCodeOverlayImage`). Both ends of that copy are data: the destination is zeroed by
> `memset_entry(0x50180000, 0, 0x25800)` beforehand, the source is `TableRomSeg02PtrSize`
> resolving directory entries 2–3, and nothing in the firmware branches into
> `0x50180000`. The routine and symbol are now named `MemStyleAreaLoadFactory` /
> `FactoryMemStyleContainer`. See `kn7000_mame/notes/AUTONOMOUS-STATUS.md` (2026-07-20)
> and `kn7000_mame/notes/table-rom-format.md`.

## The UI graphics are standard JPEGs

Scanning for JPEG streams recovers **119 images, 117 of which decode cleanly with an ordinary JFIF
decoder** (`tools/kn7000_table_jpegs.py` in this repository) — 52 are `160×120` icons/thumbnails and twelve are full-screen `640×240` reference/help
screens. In other words the KN7000 stores its on-screen artwork as ordinary JPEGs and decodes them
in firmware. (A long-standing emulation note that "the boot-splash JPEG decodes to garbage" was
therefore an **emulation bug**, not a bad dump or an exotic format: the source stream is valid
JFIF. The CPU core lacked the `udf07` bit-search instruction that the firmware's JPEG decoder
uses. With it implemented, the splash decodes pixel-clean; see
[User Data & Initial Data Disk]({{ site.baseurl }}/kn7000-initial-data/#the-boot-splash-and-the-green-screen).)

Example full-screen reference screens, extracted verbatim from the ROM:

![KN7000 RHYTHM home screen reference]({{ site.baseurl }}/assets/images/table-rom/rhythm-home.jpg)

![KN7000 ORGAN STYLIST style-list reference]({{ site.baseurl }}/assets/images/table-rom/organ-stylist.jpg)

The ORGAN STYLIST screen above groups its styles under subcategory headings. The two shown,
`Tonewheel Jazz` and `Organ A-Go-Go`, are the first two Organ Stylist entries of the
[built-in Music Stylist catalog]({{ site.baseurl }}/kn7000-rhythm-catalog/) recovered from the
program ROM, in the same order. The style names listed under them (`Swing Tonewheels`,
`Classic B3 Jazz`, …) are not in that catalog, which lists only the headings; they are a separate
list of strings in the program ROM.

A smaller `240×160` panel graphic:

![KN7000 panel graphic]({{ site.baseurl }}/assets/images/table-rom/icon-sample.jpg)

## What the data is: the source tree (2026-10-29)

The disassembly now describes almost all of the table image. `kn7000/src/table.s` (table build 84,
the image of the update disks), `kn7000/src/sp7001/table.s` (build 83, the SP7001's) and
`kn7000/src/b80/table.s` (build 80) are rebuilt byte for byte by
`make -C kn7000 verify verify-sp7001 verify-table80`, all three part of `make gate-kn7000`. The
notes are
[`kn7000/notes/table-semantics-2026-10-29.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/table-semantics-2026-10-29.md);
the format of the style data is that of the rhythm ROM,
[`kn7000/notes/ic18-rhythm-rom.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/ic18-rhythm-rom.md).

| segment                      | slot | form in the source                                                                            |
|------------------------------|------|-----------------------------------------------------------------------------------------------|
| GUI bitmaps, frames, icons   | 0    | 366 indexed PNGs, `src/table/gui/`                                                            |
| GUI fonts                    | 0    | 12 PNG glyph sheets, `src/table/gui/font_NN.png`; font 5's kern table typed                   |
| `SramRecordDefaultsZZZJ`     | 1    | typed: signature, 220 records of eight voice entries                                          |
| `FactoryMemStyleContainer`   | 2    | typed 'TCMP': header, 3 style records, 60 variation records, event streams                    |
| `FactoryMemPadContainer`     | 3    | typed 'TPAD': header, 5 bank records, 18 pad records, event streams                           |
| `TechnicsPadsResource`       | 4    | typed: header, pad-ID index, pad table, 120 pads in `src/table/pads/`                         |
| `InternalVoiceArchive`       | 6    | typed: hash tables, directories, tones, voices, zones with their wave recordings named        |
| `UserHpMenuData`             | 57   | 47 2-bpp PNGs, `src/table/user_hp_menu/`                                                      |
| `TcdImages`                  | 58   | 14 1-bpp PNGs, `src/table/tcd/`                                                               |
| `BuiltinStyleSubTable`       | 59   | typed: offsets + 52 styles (51 in table 83), one file each in `src/table/styles/`             |
| `TechnicsRhythmsTable`       | 83   | typed: the copy of IC18's header, style-ID index and offset tables                            |
| the 57 JPEGs, 102 pictures   |      | files in `src/table/` (since 2026-10-24)                                                      |

The data-incbin census (`scripts/analysis/data_incbin_census.py`) reads 0 generic bytes for table
84 and table 80; it was 447 entries, 2,560,580 bytes, before the 2026-10-29 pass. Table 83 kept
three generic gaps then (46,625 bytes), the SP7001 plug-in's GUI data; since 2026-10-30 they are
typed too, widget by widget ([SP7001 Plug-in Screens]({{ site.baseurl }}/kn7000-sp7001-plugin/)).
The census counts table 83 in the same tree as program 942, whose data region reads generic 0 too
since lane generic-zero ([Program Data Region]({{ site.baseurl }}/kn7000-data-region/#what-is-left-the-census)).
From the fourth committed snapshot, `docs/coverage/data-incbin-2026-10-30-04.txt` (whose rows for these trees are `-03`'s; the first, `-01`,
read 179 generic pieces / 3,044 bytes and opaque 4321 / 80,480 for `kn7000-sp7001`; the second,
`-02`, generic 0 and opaque 3482 / 62,187):

| tree          | generated     | from media    | media           | opaque        | generic entries | generic bytes |
|---------------|---------------|---------------|-----------------|---------------|-----------------|---------------|
| kn7000-table  | 439 / 299,512 | 439 / 299,512 | 159 / 1,316,309 | 0 / 0         | 0               | 0             |
| kn7000-sp7001 | 527 / 462,486 | 527 / 462,486 | 169 / 1,375,301 | 3472 / 61,662 | 0               | 0             |
| kn7000-b80    | 2 / 4,064,860 | 0 / 0         | 0 / 0           | 0 / 0         | 0               | 0             |

(Count / bytes. Table 80's two entries are generated from table 83's assembled image.)

### The raw pictures, as PNG files

Every raw picture is an indexed PNG whose pixel indices are the firmware's pixel values, and a
`kn7000-format` text chunk in the PNG says how it is packed. The build packs the PNGs back into the
firmware's format (`tools/table_png.py`) before assembling. The palette in the PNG is for viewing
only: the 8-bpp items use the firmware's CLUT seed (`ClutPaletteSeedTable`, `0x00BBGGRR`), with
0xF7 transparent, 0xF6 the template colour and, in frames, 0xF4 copying the picture plane.

| format       | items                     | packing                                                                                         |
|--------------|---------------------------|-------------------------------------------------------------------------------------------------|
| `p8 W H`     | 53 bitmaps, 73 frames     | `DrawBitmap_Impl`, `DrawFrameSP_Impl`: 1 byte a pixel, rows padded to even                      |
| `p4 24 24`   | 240 icons                 | `DrawIcons_Impl`: 24x24, 4 bpp, high nibble left                                                |
| `font C H N` | 12 fonts, 224 glyphs each | `DrawString_Impl`: 1 bpp column-major, from character 0x20; font 5 proportional                 |
| `b1 240 80`  | 14 TCD pictures           | `AcTcdImageProc`: MSB-first rows; they are the chord-voicing staves of the TCD screen           |
| `p2 W H`     | 47 USER HP pictures       | `AcUserHpMenuProc`: four 2-bit pixels a byte, rows of (W + 3) / 4 bytes                         |

The USER HP pictures' widths were chosen so the panels look right (all 47 checked by eye); the true
box sizes are in view resources not yet traced. Any width gives the same bytes back.

### Styles

**Segment 59** holds the 52 built-in styles (51 in table 83, identical to the first 51 of table 84;
table 84 adds "70s Orchestra"). It opens with one u24BE offset per style; index entry 0x4000 + n of
the rhythm ROM's style-ID index sends a style-ID to style n (`StyleBuiltinNameResolve`,
`TableRomStyleSubTablePtr`). Each style is a 0xC6-byte record, exactly as in the rhythm ROM: a
13-character name, eight part set-ups, 20 variations (four main patterns with two fill-ins each,
two intros and two endings, as A/B pairs) and per variation an event stream: position bytes (96
ticks a beat), notes, controllers, program changes, pitch bends, beat markers.

**Segment 83** (table 84 only; table 83 has `"DMY"`) is a copy of IC18's first 0x1248 bytes minus
the styles: the header with its checksum fields zeroed, the count block (221), the 2048-entry
style-ID index, IC18's 169-entry style table and its 8-entry count-in table.

In the source, music that can be parsed is typed, one event per line (`ev_at`, `ev_beat`,
`ev_note`, `ev_cc`, `ev_pc`, `ev_bend`, `ev_sysex` ...), in one include file per style
(`src/table/styles/`) or pad (`src/table/pads/`). The macros keep the rhythm ROM's names
(`src/table/style_macros.inc`). Every stream in segments 2, 3, 4 and 59 parses: it opens with
0xF4, ends with 0xF5, holds bars x beats beat markers, and every event has the length
`RhyEventLenByStatus` gives. The generator refuses an image where one does not.

### Pads

**Segment 4, "Technics Pads"**, has the same resource shape as the styles.
`TechnicsPadsResourceParse` checks the 16-byte name and reads three u24BE offsets: the count block
(120 pads), the 1024-entry pad-ID index and the pad table. A pad is a 16-byte name, 6 bytes of
head (bars - 1, beats - 1 and four bytes no traced code reads), two 15-byte part set-ups and its
event stream. The 120 pads tile the segment.

### MEMORY styles and pads: 'TCMP' and 'TPAD'

**'TCMP', segment 2**, is the factory MEMORY style area that boot copies to `0x50180000`
(`MemStyleAreaLoadFactory`): a 0x70-byte header (signature, checksum, checksum range, the 0x25800
area length, the allocator top, 3 styles), three 0x80-byte style records (name, four variation
names, the 20 slots' variation indices, two sound-unit keys), 60 variation records of 0xE0 bytes
(a head and eight part blocks) and the heap of event streams. The three styles are Easy 8 Beat,
Easy 16 Beat and Easy Swing.

**'TPAD', segment 3**, is the factory PERFORMANCE PAD memory, read by its likeness to TCMP: the
same header, five bank records of 0x30 bytes (a name and six pad references) and 18 pad records of
0x60 bytes, then the heap.

Both checksums are measured, not inferred: the 16-bit big-endian word sum over the stated range
gives TCMP's stored 0xCC00 and TPAD's stored 0xE13D (`notes/table-semantics-probes/`).

### 'ZZZJ', segment 1

`SramRecordsLoadFactory` compares the first 8 bytes with `'ZZZJ', 0, 'K', 0, 0xDC` and copies
records of 0x18 bytes over the battery-SRAM table at `0x84030FF8`. A record is read as eight
{program, bank LSB, bank MSB} entries; that is an inference from the bank pattern (bank MSB 0x26
in entries 0 and 1 of all 220 records, the drum/melodic pattern of the styles' part programs). 220
is the rhythm count, but no record matches any table style's eight part programs, so what the
records configure is still open.

### The 'JK' internal voice archive

**Segment 6**, 832,592 bytes, is the archive of the built-in voices, generated into
`src/table/voices/internal_archive.s` by `tools/gen_table_voices.py` (table 83:
`src/sp7001/internal_voice_archive.s`). It holds no passthrough. All its pointers are u32 offsets
from the archive's first byte.

| item                     | count                          | reader                                         |
|--------------------------|--------------------------------|------------------------------------------------|
| header, descriptor       | 0x20 + 0x54 bytes              | `VoiceArchiveScanBoot`                         |
| hash tables              | 8 tables, 11,357 chain entries | the tone-key and voice lookups                 |
| tone directory, records  | 1,293 (+ 'Initial')            | `TgPartProgramApply`, `TgNoteOn`               |
| table tones              | 52 x 0x1A7                     | `TgNoteOnTableTone`                            |
| voice directory, records | 1,617 (+ default)              | `VoiceRecFetchBanked`, `VoiceSubRecFetch`      |
| parameter records        | 864 x 0x10                     | `TgVoiceRoutePtrCalc`, `TgPitchZoneFold`       |
| key maps                 | 7 x 128 (one unreferenced)     | `TgVoiceRoutePtrCalc`                          |
| zone lists, zone array   | 3,753 + 1,462 zones            | `TgVoiceRoutePtrCalc`, `TgVoiceRouteFieldSet`  |
| element table            | 87 x 0x23                      | `VoiceElemRecFetch`, `TgVoiceZoneVeloResolve`  |
| 0x2C8-byte named records | 40                             | SOUND EDIT records (`voice_record.inc` macros) |

**How a note reaches a recording**, traced through program 941's library:

1. The part's tone record comes from a hash lookup of the MIDI {program, bank} triple in the
   tone-key hash table (`TgPartProgramApply`).
2. The note-on staging fetches the voice sub-record, the element (whose velocity splits pick a
   layer) and the layer's parameter record (`TgPartVoiceRecFetchIdxSel`,
   `TgPartElemProgramApplyIdxSel`, `VoiceParamRecFetchBanked`).
3. `TgVoiceRoutePtrCalc` finds the zone: the parameter record's key map gives a group for the
   note, the group gives a zone index, and the zone is that index times 6 or 8 bytes into the zone
   list. **Bit 7 of parameter byte +8 is the zone-size selector**: when it is set the zones are 8
   bytes, and `TgPitchNoteResolve` adds the 8-byte zone's signed halfword at +6 to the pitch.
4. `TgVoiceRouteFieldSet` and `TgElemNoteOnStd` put the zone's page (byte +0) and entry (halfword
   +2 & 0xFFF) into the select word the tone generator reads
   ([Wave ROM Format]({{ site.baseurl }}/kn7000-wave-rom-format/#how-the-firmware-selects-a-recording)).
   `TgVoiceSideSelect` takes the TG side from bits 10/11 of halfword +0; which side bit means MAIN
   and which SUB was not traced, so each zone's comment names both candidate recordings
   (zone 0 of the first list: `Main_P01_E019` / `Sub_P01_E019`).

That gives a static cross-check of the wave ROMs: all 5,215 zones name an existing wave directory
entry. The generator lists any that does not, and none does.

**The fields, named from their readers (2026-10-29).** A tone record (a 0x54-byte head and its
0x7A-byte units) and the first 0x23C bytes of a SOUND EDIT record are one layout:
`TgPartAuxRecBuild` copies one onto the other. So the archive no longer has macros of its own: its
tone heads, units, voice sub-records, elements, its 40 0x2C8 records and its 87-row element table
are spelled with the shared `SOUND_HEAD`, `SOUND_MOD`, `VOICE_HEAD_TAIL`, `VOICE_SUB` and
`VOICE_ELEM` of `kn7000/src/include/voice_record.inc`, whose field names come from the `Tg*`
routines that read them: the pitch, amplitude and filter envelopes, key follow, the velocity and
key fades, the effect sends, the element reference and the velocity splits. Tables 84, 83 and 80
rebuild byte-identically. What each field is, and which bytes no traced routine reads, is on
[Panel Memory Records: the sound records]({{ site.baseurl }}/kn7000-panel-memory/#the-sound-records)
(lane kn67-field-names, `notes/data-semantics-2026-10-29/kn67-field-names.md` in the disassembly
repository).

### Still open

- The 'JK' archive's fields that no traced routine reads (the 0x7A unit's `+0x04`..`+0x06` and
  others), and which tone generator each zone's side bit selects.
- 'ZZZJ': what the 220 records select.
- The USER HP pictures' true box sizes.
- A few pad, TPAD and TCMP head bytes that no traced code reads.

## Reproduce
De-interleave MAME's table build 84 pair, `kn7000_table_even_b84.ic17` / `kn7000_table_odd_b84.ic16`
(`out[0::4]=e[0::2]; out[1::4]=e[1::2]; out[2::4]=o[0::2]; out[3::4]=o[1::2]`) → 4 MB image;
walk the u32 directory at offset 0; extract JPEGs by scanning `ff d8 ff e0` → `ff d9`. See also
the [firmware images]({{ site.baseurl }}/kn7000-firmware/) page for the full per-segment breakdown; technical detail in `kn7000_mame/notes/table-rom-format.md`.
