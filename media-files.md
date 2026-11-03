---
layout: page
title: Media Files (pictures and recordings)
permalink: /media-files/
---

# Pictures and recordings as ordinary files

Every picture in the disassembly is a PNG, JPEG or BMP file, every wave-ROM recording is a WAV file,
and every MIDI stream is a `.mid` file. They are **committed**, and the build turns them back into the
ROM's bytes, so you can open them in any image viewer or sound program, edit them, and rebuild. Nothing
the build derives from them is committed: the bytes it writes go into git-ignored files next to the
sources or under `build/`. The owner's decision of 2026-10-31: *"Images and wav files must be commited
and the conversion must happen as a build step."*

This page covers all the models in the tree. The references are two lanes in the disassembly
repository: media-files of 2026-10-30, which turned the last byte rows into files
([`notes/media-files-2026-10-30/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/notes/media-files-2026-10-30/README.md)),
and media-build of 2026-10-31, which committed the WAVs and the floppy media and made every conversion
a make rule
([`notes/media-build-2026-10-31/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/notes/media-build-2026-10-31/README.md)).
The probes are in
[`notes/media-files-probes/`](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/notes/media-files-probes).
The repository's own rule is the CLAUDE.md section "Media Files Are Committed; Conversion Is a Build Step".

## Where the files are

| kind       | model     | folders                                                                                                                                                  |
|------------|-----------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| pictures   | KN5000    | `v10/maincpu/images/` (and the `images/` of `v9`, `v7`, `v6`, `v5`), `table_data/images/`, `hdae5000*/images/`                                           |
| pictures   | SX-KN7000 | `kn7000/src/table/`, `kn7000/src/picture/`, `kn7000/src/program/data/media/` (and each other build's `program/data/media/`), `kn7000/src/ic18/media/`    |
| pictures   | siblings  | `kn2400/`, `kn6000/`, `kn6500/`, `hdsx3/` `src/program/data/media/`                                                                                      |
| pictures   | SX-WSA1R  | `wsa1/prom_a/images/`, `wsa1/prom_b/images/` (with `fonts/`)                                                                                             |
| recordings | KN5000    | `waveform/wav/` (IC307, 1,413 files)                                                                                                                     |
| recordings | SX-KN7000 | `kn7000/wav/main/`, `kn7000/wav/sub/` (3,580 files; 3,682 until 2026-11-02 and 3,681 until 2026-11-03)                                                   |
| MIDI       | KN5000    | `table_data/includes/demo_presets/midi/` (the demo songs)                                                                                                |
| disk files | all       | `floppy/<model>/<disk>/media/`: the softlist floppies' BMP, JPEG and MIDI files, 131 files, 5,062,376 B (KN5000 29, SX-WSA1R 16, KN6000 85, SX-KN7000 1) |

Indexed PNGs store the ROM's palette indices, so a pixel's value is the ROM's byte. One-bit pictures
are one-bit PNGs. The KN5000's 8-bit pictures carry the main palette, `Palette_8bit_RGBA.bin`; the
palettes are data, not pictures, and stay tracked as they are. The WAVs are about 72 MB
(72,121,566 bytes of PCM, measured 2026-10-30); with the floppy media they are almost all of the
71.6 MB (zlib-compressed) that lane media-build added to the repository (its section "Repository size").

## How the build uses them

Each converter output is a real make target that depends on its media file, so an edited PNG or WAV
rebuilds it. The outputs stay at the paths the sources already `.incbin`, now git-ignored, so no
`.incbin` line changed (the build graph of the media-build README has every row):

| media                                                      | converter                                                            | git-ignored output                                          |
|------------------------------------------------------------|----------------------------------------------------------------------|-------------------------------------------------------------|
| KN5000 `images/*.png`, `Wallpaper_*.png`, the STORE button | `scripts/build/indexed_images.py`, `mono_images.py`, `se_bitmaps.py` | the `.bin` beside each PNG (142, `kn5000_image_outputs.py`) |
| the NAKA GUI C's pictures (39 per revision)                | `scripts/build/c_bitmaps.py build TREE`                              | `v*/maincpu/includes/generated/pictures/*.inc`              |
| Feature Demo `FTBMP0?.png` + `ftbmp_headers.json`          | `scripts/build/ftbmp_images.py build`                                | `table_data/images/FTBMP0?.BMP`                             |
| table data UI bitmaps, icons, fonts                        | `ui_bitmaps_images.py`, `icon_images.py`, `font_images.py`           | `table_data/includes/generated/*.bin` (274)                 |
| HD-AE5000 pictures and palette listings                    | `scripts/build/hdae5000_images.py build`                             | `hdae5000*/includes/generated/HDAE5000_*.bin` (14)          |
| KN5000 demo songs (`.mid` + sidecars)                      | `midi_to_preset.py`, `compress_lzss.py`                              | `table_data/includes/demo_presets/*_compressed.bin`         |
| `waveform/wav/*.wav`                                       | `scripts/build/pcm_wav.py build`                                     | `waveform/build/pcm/*.pcm`                                  |
| `kn7000/wav/{main,sub}/*.wav`                              | `scripts/build/pcm_wav.py build`                                     | `kn7000/build/wav_pcm/{main,sub}/*.pcm`                     |
| SX-KN7000 and sibling PNGs                                 | `kn7000/tools/table_png.py build`                                    | `build/table_png/`, `build/bitmaps/`, `build/ic18_png/`     |
| SX-WSA1R bitmaps and font faces                            | `wsa1_bitmaps.py`, `wsa1_fonts.py build`                             | the `.bin` beside each PNG (222)                            |
| floppy BMP / JPEG / MIDI, KN7000 JPEG / BMP                | none: read directly                                                  | -                                                           |

- **No converter reads a reference image.** `pcm_wav.py build` has no `--ref` option any more: it reads
  the committed manifest and the WAVs, and a missing WAV is an error that says to restore it from git.
  `icon_images.py` and `font_images.py` take their counts and kern widths from the committed blob size and
  `table_data/fonts.s`; `table_png.py build` reads the format from each PNG's tEXt chunk. A reference is
  needed only for the final byte compare and for the maintenance targets that re-extract media from a
  dump: `make waveform-wav`, `make -C kn7000 wave-wav`, `make -C floppy media-<model>`,
  `make -C wsa1 images-export`, and the `*-src` generators.
- **The floppy media come first.** A disk unit's `.incbin` of a `.bmp`, `.jpg` or `.mid` name finds the
  committed copy in `floppy/<model>/<disk>/media/`, which precedes `build/<model>/<disk>/` on the include
  path; `tools/fat12_media.py check` runs in every `gate-<model>`.
- **To add a picture**: put the PNG beside the source, teach the converter its geometry, make the source
  `.incbin` the converter's output with `census: generated -- <tool>, from <file>`, and never `git add`
  the output.

## The clean-checkout proof

`notes/media-build-2026-10-31/clean_checkout_proof.sh` runs the whole chain on a fresh clone. Its run of
2026-10-31 is committed beside it (`clean_checkout_proof-2026-10-31.txt`) and printed
`PASS: clean checkout of open2/media-build`:

| phase | what it does                                                                                                                         | result                                                             |
|-------|--------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| A     | builds every converter output with every romset, dump and mirror path (`PROJECTS_ROOT`, `UNIDASM` ...) pointed at an empty directory | 7,033 outputs built; no reference image present                    |
| B     | `make gate gate-wsa1 gate-floppy gate-kn7000 gate-kn6000 gate-kn6500 gate-kn2400 gate-hdsx3`, `make -C kn7000 symbols-check`         | all exit 0; every rebuilt ROM byte-identical                       |
| C     | `git status --porcelain`                                                                                                             | empty                                                              |
| D     | deletes every converter output, makes every tracked file read-only, runs the same gates                                              | all exit 0; the 7,033 outputs rebuilt SHA-256-identical to phase A |
| E     | deletes the 93 extracted copies of committed floppy media from `floppy/build/` and rebuilds the disks                                | 4 models reproduced byte for byte                                  |

So a clean checkout builds every media conversion from the committed media alone, and no converter writes
a tracked file. The SHA-256 list of the 7,033 outputs is committed as `converter_outputs.sha256.gz` (the
list hashes to `81927db84c5734446474fc68a6b8b0d50411c0bdc83c958e68a9bb12fbc09b89`); 6,616 of them equal
a build of the tree before the change.

## The WAV files

They are plain mono RIFF WAVE files, `pcm_s16le` or `pcm_u8`: `ffplay kn7000/wav/main/Main_P0A_W00F.wav`
plays one, and Audacity opens the folder. `ffprobe` read all 5,095 without an error (2026-10-30), and
opens all 3,580 KN7000 files of the merged set (2026-11-03, `wav_merge_counts.py --ffprobe`).

| set                      | files | 16-bit | 8-bit | header rate | `smpl` loops | manifest                       |
|--------------------------|-------|--------|-------|-------------|--------------|--------------------------------|
| KN5000 IC307             | 1,413 | 1,213  | 200   | see below   | 0            | `waveform/wav_manifest.tsv`    |
| SX-KN7000 MAIN (IC203/4) | 2,178 | 1,801  | 377   | see below   | 496          | `kn7000/src/wave/main_wav.tsv` |
| SX-KN7000 SUB (IC207/8)  | 1,402 | 905    | 497   | see below   | 362          | `kn7000/src/wave/sub_wav.tsv`  |

(Counted from the three committed manifests, which hold one row per recording and no sample data:
label, offset in the reference, end, bit depth, sample rate, WAV file name, unity note, loops and the
INFO comment. The KN7000 manifests have one row per recording since 2026-11-03, plus a `cues` column
for the alternate starts.)

- **The mapping is exact both ways.** A 16-bit recording is signed little-endian, so the WAV's `data`
  chunk holds the ROM bytes unchanged. An 8-bit recording is two signed samples per word, low byte
  first; WAV 8-bit PCM is unsigned, so each WAV byte is the ROM byte XOR 0x80.
  `scripts/build/pcm_wav.py verify` checks the round trip (1,413 of 1,413 for IC307), and refuses a loop
  or a cue that lies outside the recording. For the merged KN7000 files, `wav_merge_counts.py` finds the
  `data` chunk equal to the samples of the pieces it replaced in 2,178 of 2,178 (MAIN) and 1,402 of 1,402
  (SUB) files, and `make -C kn7000 verify-wave` rebuilds the chips byte for byte from them. `pcm_wav.py build` refuses a WAV that is not mono integer PCM of the recording's bit depth,
  or whose length differs, because the page layout fixes where every recording starts.
- **Names.** A WAV is named after its source label. The KN5000 labels already carry the instrument
  (`P1_W0003_JazzFlute.wav`). A KN7000 recording whose audio IC307 also holds gets the IC307 name too
  (`Main_P00_W000_Sine.wav`; 1,114 of 3,580, from `kn7000/src/wave/ic307_names.tsv`; an alternate
  start's IC307 twin is named in its cue note instead). Each file's
  LIST/INFO chunk carries the label and a comment: tone generator, page, entries, select, format, and
  the IC307 or KN7000 counterpart.
- **Sample rates (since 2026-10-31).** Neither ROM stores a rate, but the headers now carry a real
  sample rate and root note:
  - the SX-KN7000: the tone generator's read rate at the recording's root key, from the tone database
    ([KN7000 Wave ROM Format]({{ site.baseurl }}/kn7000-wave-rom-format/#sample-rates)); rates run from
    3,977 Hz to 189,437 Hz;
  - KN5000 IC307: half that rate where the KN7000 holds the same recording (1,339 of 1,413); the other 74
    stay at 22,050 Hz, nominal, because their pitch exponent is on the undumped IC306.

  `scripts/build/pcm_wav.py retag` rewrote the header chunks of 5,094 WAVs; the samples are the ROM's bytes,
  so a WAV still rebuilds the ROM exactly (disassembly `notes/sound-2026-10-31/README.md`, section 1).
- **Loops and root note (KN7000).** The KN7000 files carry a `smpl` chunk that samplers read: the loop
  where the parameter record marks one (858 recordings: 496 MAIN, 362 SUB), written from the record's `LOOP_START` /
  `LOOP_END` segment ends, and a unity note: the root key plus the rounding of the rate. The pitch law
  behind it was fitted in emulation (kn7000_mame `notes/g13-waves-2026-10-20`, 478 of 556 voices), so
  the octave of the root is *[INFERENCE]*; the pitch class is checked against the audio. (The old item
  `Main_P00_W0AF`, which had no unity note, is part of `Main_P00_W065`'s recording since 2026-11-02: its
  entry, the Reverse Cymbal, plays `Main_P00_W0AE` backwards;
  [KN7000 Wave ROM Format]({{ site.baseurl }}/kn7000-wave-rom-format/).)
- **One file per recording (KN7000, since 2026-11-03).** A recording that two or three directory entries
  start into is one WAV, with a cue point (`cue ` + LIST/adtl `labl` / `note`) at each later start. Every
  file ends where its recording ends, so a looped recording ends at its loop end. The run-out after the
  loop is in the source only, and no loop is left out of a file any more (until 2026-11-03, 90 loops ended
  past their item and were left out of the WAV). 101 alternate-start WAVs were merged into 61 recordings,
  and 867 files were trimmed
  ([KN7000 Wave ROM Format]({{ site.baseurl }}/kn7000-wave-rom-format/#one-wav-per-recording-since-2026-11-03)).
- **8-bit gain.** The KN7000's 8-bit segments carry a 6-bit code that, in emulation, scales the
  segment by 2^(-b/2) (fitted, not derived). The WAV holds the raw samples, so 8-bit recordings play
  with their segments at the stored level: the segment gain law is not established, so no gained copy
  was made.

How each encoding was established is on [KN7000 Wave ROM Format]({{ site.baseurl }}/kn7000-wave-rom-format/#encoding-and-the-wav-files)
and [Waveform ROM Format]({{ site.baseurl }}/waveform-rom-format/#ic307-is-half-of-a-pair).

## KN5000 IC307 is half of a pair

IC307 holds every other 16-bit word of each recording, directory entry and parameter record: it is
the "Y" chip of a word-interleaved pair, like the SX-KN7000's wave ROMs. The probes show it:

- 1,342 of its 1,413 waves occur verbatim in the KN7000's Y chips (1,162 in IC203, 180 in IC207, none
  in an X chip); 1,339 of them start at a KN7000 recording's first sample, and 1,327 match over their
  whole length (`ic307_kn7000_match.py`);
- its 256-word test sine is exactly the even samples of the KN7000's 512-sample sine `Main_P00_W000`
  (`pcm_encoding_probe.py`);
- 456 of its parameter records equal the words p1, p3, p5, ... of a KN7000 record that plays the same
  recording, and none matches the other half, p0, p2, ... (`ic307_records_vs_kn7000.py`).

So the KN5000's tone generator must read its wave ROMs in pairs too (*[INFERENCE]* from the chip's
contents; the MAME driver maps IC304-IC307 as one linear 16 MB region). The partner chip, which holds
the other half and each entry's format, pitch and loop word, is **IC306** (from the service manual's
wiring, [Waveform ROM Format]({{ site.baseurl }}/waveform-rom-format/#ic307s-partner-is-ic306)), not
dumped. An IC307 WAV therefore sounds like its recording at half the
sample rate, without anti-alias filtering. 200 of the waves are 8-bit (two samples per word, so an
8-bit IC307 WAV holds the sample pairs 4i, 4i + 1): 169 known from the KN7000 recording with the same
audio, 31 by a byte-correlation rule calibrated on those (*[INFERENCE]*). For the 1,327 waves that match
whole, the KN7000's X chip holds the other half of what is very probably the same recording; the
disassembly does not combine them, because a KN7000 dump is not a KN5000 one.

## The pictures converted on 2026-10-30

Most pictures were PNG, JPEG or BMP files already. The inventory found these still spelled as byte rows
or C initializers; each is now a PNG that a build step turns back into the bytes:

| item                                             | format (evidence)                                                                                                                  | converter                            |
|--------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------|
| `SeBitmap_*` x 13, KN5000 v10 v9 v7 v6 v5        | 1 bpp, column-major, bit 7 leftmost; drawn by static op 03 via `ColorBlit2_LargeCodeBlock`                                         | `scripts/build/se_bitmaps.py`        |
| `HDAE5000_Bitmap_Button01`, both HD-AE5000s      | 42 x 15, 8 bpp, no row pad; `HDAE5000_BitmapButt01` answers `EVT_GET_BITMAP_DATA` / `_WIDTH` / `_HEIGHT` with it                   | `scripts/build/indexed_images.py`    |
| `FontGlyphs8x16`, KN7000 IC18 boot ROM           | 224 glyphs from 0x20, 16 bytes each, MSB leftmost; `FontTable` points at it                                                        | `kn7000/tools/table_png.py`          |
| `SjisMissingGlyph`, KN7000 941 / 942 / 935 / 893 | 16 x 16, 1 bpp, column-major; `DrawString_Impl` (941 `0x48425467`) draws it for an absent Shift-JIS code                           | `kn7000/tools/table_png.py`          |
| NAKA GUI C pictures, 39 x 5 KN5000 trees         | the 8-bpp bitmaps, `UserBitmapCheck_Bitmap24x24` and the welcome screen's 16 x 17 letters (`WelcomeGlyph_C`, `WelcomeGlyph_I` ...) | `scripts/build/c_bitmaps.py`         |
| `OldBuild_ValueGlyph_Bitmaps`, SX-WSA1R          | four value glyphs, byte-identical to the live ones; now listed with PNGs                                                           | `wsa1/scripts/build/wsa1_bitmaps.py` |

- The NAKA GUI C no longer holds the pixels. Since 2026-10-31 each of the 195 initializer bodies in the
  25 `v*/maincpu/ui_widgets/naka_*.c` files is one `#include` of a git-ignored
  `../includes/generated/pictures/<name>.inc`, which `c_bitmaps.py build TREE` writes from the PNG. The C
  keeps its struct declarations and the header comment above each picture; about 82,000 lines of pixel
  rows left it. The 25 compiled objects equal those of a build before the change (`cmp`).
  `c_bitmaps.py verify` checks PNG = `.inc` = the built bytes at each label. For v10 the PNG is the same
  file the table data uses; v9, v7, v6 and v5 got their own 39 each.
- `se_bitmaps.py verify` and `indexed_images.py verify` check 65 of 65 round trips.

## SX-WSA1R: the ranges that had no rectangle

On 2026-10-30 `wsa1_bitmaps.py` refused three SX-WSA1R ranges because their picture geometry was not
established. The code that draws them settled two of them (media-build README, "WSA1R: the refused ranges"):

- **`Bitmap_DrawbarA` (prom_b `0xF54808`) and `Bitmap_DrawbarB` (`0xF54AC3`), 699 B each, are 24 x 233
  pictures.** `Drawbar_DrawColumn` builds a blit record on its stack and issues it three times through
  `Blit_FromStackRecord`, moving one byte (8 pixels) right and 233 bytes down the source each time. That
  is `LCD_Svc_03_BlitColumns`' column-major layout, three columns of 233 rows. The screen shows a 123-row
  window of it, starting at the row offset the drawbar's value selects (`0x7B` + the largest offset
  `0x6E` = `0xE9` = 233). The PNG shows a drawbar shaft numbered 8 down to 1 above its handle, then the
  110 blank rows the window never reaches at offset 0. DrawbarA serves the integer footages, DrawbarB the
  fractional ones.
- **prom_a `0xFC48E4`-`0xFC52F7` beyond the eight widgets is not a picture.** From `0xFC4BA7` on, the
  module `prom_a/modules/fc4000_fc53ff_digital_effect_screen_data.s` already typed it as the SOUND EDIT
  COPY page's display lists, rectangles and names, each named by its prom_b reader (`SoundEditCopy_Paint`
  and friends). The refusal was stale.
- The third entry ("no fifth cell at `0xF17AE0`") is not a picture and stays as the one refused note.

The SX-WSA1R's bitmaps were `.byte` rows that `wsa1_bitmaps.py check` compared with their PNGs. They are
now `.incbin "images/<name>.bin", skip, count` lines: 210 bitmap ranges and 12 font faces became 225
include lines (three are split by an inner label or comment). `wsa1_bitmaps.py verify` reports 210 images,
47,838 B, 0 failures.

## The census counts them as generated

`scripts/analysis/data_incbin_census.py` keeps an include made from a standalone media file through a
committed lossless converter in class **generated**, with the converter and the file named in its
marker (`census: generated -- scripts/build/pcm_wav.py, from waveform/wav/P0_W0000_Sine.wav (16-bit)`).
A column **from media** counts those entries per tree; class **media** counts the files read directly.
Lane media-build's read-only run (`data_incbin_census.py --compare data-incbin-2026-10-30-04.json`,
media-build README, "Read-only censuses") exits 0 with generic 0 in every tree, and the committed
snapshot [`docs/coverage/data-incbin-2026-10-31-02.txt`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/docs/coverage/data-incbin-2026-10-31-02.txt) (measured at `6ca33e656`, committed in `c58fe3de7`) reads the same; what moved:

- `wsa1`: generated 0 -> 225 entries, 95,342 B, all from media (the respell above);
- `kn5000-tabledata`: media 6 -> 0 and from media 336 -> 342 (the six Feature Demo BMPs are now
  generated from their PNGs);
- the new `kn7000-ic21own` tree counts its home-page BMP as media.

The class *opaque pcm* has been empty in every tree since snapshot `data-incbin-2026-10-30-03`; in `-02`
it held 5,095 items, 70,490,064 bytes (`kn5000-waveform` 1,413 / 4,170,480 and `kn7000-wave`
3,682 / 66,319,584, now all generated from media). Since the KN7000 WAV merge of 2026-11-03,
`kn7000-wave` reads 4,548 generated lines, 66,310,688 bytes, all from media (read-only run at disassembly
commit `32b8124e7`; no snapshot committed since `data-incbin-2026-11-02-01`, which reads 4,539 lines, the
same bytes, 3,690 of them from media). The NAKA GUI C's pictures still count as compiled C,
not as "from media", although their pixels are now written from the PNGs.

## The inventory

`python3 notes/media-files-probes/media_inventory.py` lists every picture, PCM recording and MIDI
stream of every census tree and the file behind each. On 2026-10-31, after lane media-build, every tree
built, it exits 0 (media-build README, section "Inventory"):

- **8,136 items backed by a committed media file**: 630 read directly (JPEG, BMP, MID), 7,506 converted at
  build time (PNG, WAV); **0 not backed**;
- **0 untracked media files** that the build reads;
- **0 tracked files** that a converter derives from media.

The probe fails the other way too: with one WAV untracked and one SX-WSA1R `.bin` force-added, it reported
1 untracked media file and 1 tracked derived output and exited 1. (On 2026-10-30, before the change, it counted 8,122 items.)

### What is left

Nothing in this list. On 2026-10-31 (lane media-cleanup):

- the 191 colour renders that used to sit in `table_data/images/icons/` were deleted. They duplicated
  `table_data/images/icons_png/`, the indexed PNGs the build converts, and `scripts/analysis/extract_icons.py`
  now paints those (`make gallery` writes the sprite sheet). The eight raw blobs that were byte-for-byte
  slices of the table-data and HD-AE5000 reference images (table_data/includes/icon_pixel_data.bin,
  icons_to_strings.bin, wallpaper1_to_icons.bin, hdae5000/includes/code_*.bin; deleted, so named without code marks) were deleted too. No
  build read them; the maintenance commands that did read the same bytes from the reference image.
- the C-divergence patcher's stamps are build state, no longer committed. A missing stamp makes the
  patcher recompile that bin first, so it can never patch a bin twice.
- the MN10300 trees' `src/constants.inc` is committed source, rewritten only by `make constants`.
- the one-shot generator that wrote the SX-WSA1R widget pages as pixel rows no longer writes anything.

The probe's limit stays: a picture under a label that names no picture class, held as typed rows, is not
seen. (Disassembly `notes/media-cleanup-2026-10-31/README.md`.)

## Open questions

- ~~**Sample rates.**~~ Derived from the tone database on 2026-10-31 (above); the octave rests on the emulation fit, and 74 IC307 items wait for IC306.
- **The 8-bit gain law**, KN7000 and IC307: fitted in emulation, not derived. A line-out recording of an
  8-bit sound would settle it, and whether the WAVs should apply it.
- **IC307's partner chip** is IC306, and selector classes 0-3 are IC304 + IC305; until they are dumped,
  an IC307 WAV is half of each recording.
- **The 71 IC307 waves with no KN7000 counterpart**: their 8-bit or 16-bit format is the byte-correlation
  inference.

## Related pages

- [Waveform ROM Format]({{ site.baseurl }}/waveform-rom-format/): KN5000 IC307
- [KN7000 Wave ROM Format]({{ site.baseurl }}/kn7000-wave-rom-format/): the four SX-KN7000 wave chips
- [Floppy Disk Files and Formats]({{ site.baseurl }}/floppy-disk-formats/): the disk images and their media
- [Image Gallery]({{ site.baseurl }}/image-gallery/) and [KN7000 Image Gallery]({{ site.baseurl }}/kn7000-image-gallery/)
- [ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/#the-data-include-census): the data-include census
