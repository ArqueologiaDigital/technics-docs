---
layout: page
title: Media Files (pictures and recordings)
permalink: /media-files/
---

# Pictures and recordings as ordinary files

Every picture in the disassembly is a PNG, JPEG or BMP file, and every wave-ROM recording is a WAV
file, which the build turns back into the ROM's bytes. You can open them in any image viewer or sound
program, edit them, and rebuild. (Three SX-WSA1R ranges stay byte rows until their picture geometry is
established; see [What is not a file](#what-is-not-a-file).)

This page covers all the models in the tree. The reference is lane media-files of 2026-10-30 in the
disassembly repository:
[`notes/media-files-2026-10-30/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/notes/media-files-2026-10-30/README.md),
with its probes in
[`notes/media-files-probes/`](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/notes/media-files-probes).
Every image still rebuilds byte-identical: `make gate`, `make gate-wsa1 gate-floppy` and
`make gate-kn7000 gate-kn6000 gate-kn6500 gate-kn2400 gate-hdsx3` all pass (the gates table of that
README).

## Where the files are

**Pictures** are committed:

| model     | folders                                                                                                                                               |
|-----------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| KN5000    | `v10/maincpu/images/` (and the `images/` of `v9`, `v7`, `v6`, `v5`), `table_data/images/`, `hdae5000/images/`                                         |
| SX-KN7000 | `kn7000/src/table/`, `kn7000/src/picture/`, `kn7000/src/program/data/media/` (and each other build's `program/data/media/`), `kn7000/src/ic18/media/` |
| SX-WSA1R  | `wsa1/prom_*/images/`                                                                                                                                 |

Indexed PNGs store the ROM's palette indices, so a pixel's value is the ROM's byte. One-bit pictures
are one-bit PNGs. The KN5000's 8-bit pictures carry the main palette, `Palette_8bit_RGBA.bin`; the
palettes themselves are not counted as pictures.

**Recordings** are not committed: they are the dumps' own bytes, and the repository is public.
`make waveform-wav` (KN5000 IC307) and `make -C kn7000 wave-wav` (SX-KN7000) write them from your copy
of the ROM images into `waveform/wav/` and `kn7000/wav/main/`, `kn7000/wav/sub/` (both git-ignored),
about 72 MB for 5,095 files (72,121,566 bytes, measured 2026-10-30). `make` extracts any WAV that is
missing and never overwrites one that is there, so an edited WAV survives; the build then reads the
WAVs, not the reference image.

```
make waveform-wav                                   # KN5000: extract the missing WAVs into waveform/wav/
make -C kn7000 wave-wav                             # SX-KN7000: extract into kn7000/wav/{main,sub}/
make rebuilt_ROMs/kn5000_waveform_ic307.llvm.rom    # builds IC307 from the WAVs (extracts them first if absent)
make -C kn7000 verify-wave                          # the same for the four KN7000 wave chips
```

The reverse direction is checked too: with `waveform/wav/` and `kn7000/wav/` deleted, `make gate` and
`make gate-kn7000` regenerate them from the references and the images come out byte-identical again.

## The WAV files

They are plain mono RIFF WAVE files, `pcm_s16le` or `pcm_u8`: `ffplay kn7000/wav/main/Main_P0A_W00F.wav`
plays one, and Audacity opens the folder. `ffprobe` read all 5,095 without an error (2026-10-30).

| set                      | files | 16-bit | 8-bit | header rate (nominal) | `smpl` loops | manifest                       |
|--------------------------|-------|--------|-------|-----------------------|--------------|--------------------------------|
| KN5000 IC307             | 1,413 | 1,213  | 200   | 22,050 Hz             | 0            | `waveform/wav_manifest.tsv`    |
| SX-KN7000 MAIN (IC203/4) | 2,251 | 1,806  | 445   | 44,100 Hz             | 477          | `kn7000/src/wave/main_wav.tsv` |
| SX-KN7000 SUB (IC207/8)  | 1,431 | 917    | 514   | 44,100 Hz             | 360          | `kn7000/src/wave/sub_wav.tsv`  |

(Counted from the three committed manifests, which hold one row per recording and no sample data:
label, offset in the reference, end, bit depth, sample rate, WAV file name, unity note, loops and the
INFO comment.)

- **The mapping is exact both ways.** A 16-bit recording is signed little-endian, so the WAV's `data`
  chunk holds the ROM bytes unchanged. An 8-bit recording is two signed samples per word, low byte
  first; WAV 8-bit PCM is unsigned, so each WAV byte is the ROM byte XOR 0x80.
  `scripts/build/pcm_wav.py verify` checks the round trip (1,413 / 2,251 / 1,431 of 1,413 / 2,251 /
  1,431). `pcm_wav.py build` refuses a WAV that is not mono integer PCM of the recording's bit depth,
  or whose length differs, because the page layout fixes where every recording starts.
- **Names.** A WAV is named after its source label. The KN5000 labels already carry the instrument
  (`P1_W0003_JazzFlute.wav`). A KN7000 recording whose audio IC307 also holds gets the IC307 name too
  (`Main_P00_W000_Sine.wav`; 1,118 of 3,682, from `kn7000/src/wave/ic307_names.tsv`). Each file's
  LIST/INFO chunk carries the label and a comment: tone generator, page, entries, select, format, and
  the IC307 or KN7000 counterpart.
- **Sample rates are nominal.** Neither ROM stores a rate. 44.1 kHz is the rate at which the KN7000's
  tone generator steps one source sample per output sample; IC307's 22.05 kHz is half of it, because
  that chip holds every other sample (below).
- **Loops and root note (KN7000).** The KN7000 files carry a `smpl` chunk that samplers read: the loop
  where the parameter record marks one (837 recordings), written from the record's `LOOP_START` /
  `LOOP_END` segment ends, and a unity note from the pitch law `96 + 12 (log2(44100 / 2093.0045) - (E - 9))`.
  That law was fitted in emulation (kn7000_mame `notes/g13-waves-2026-10-20`, 478 of 556 voices), so
  the root note is *[INFERENCE]* and only near: it leaves out each zone's tuning. 90 loops end past
  their item and are left out of the WAV (its comment says how many); `Main_P00_W0AF` has no unity
  note, because its P word reads as E = 47.
- **8-bit gain.** The KN7000's 8-bit segments carry a 6-bit code that, in emulation, scales the
  segment by 2^(-b/2) (fitted, not derived). The WAV holds the raw samples, so 8-bit recordings play
  with their segments at the stored level.

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
the other half and each entry's format, pitch and loop word, is not dumped, and which socket it is
(IC304, IC305 or IC306) is not known. An IC307 WAV therefore sounds like its recording at half the
sample rate, without anti-alias filtering. 200 of the waves are 8-bit (two samples per word, so an
8-bit IC307 WAV holds the sample pairs 4i, 4i + 1): 169 known from the KN7000 recording with the same
audio, 31 by a byte-correlation rule calibrated on those (*[INFERENCE]*). For the 1,327 waves that match
whole, the KN7000's X chip holds the other half of what is very probably the same recording; the
disassembly does not combine them, because a KN7000 dump is not a KN5000 one.

## The pictures converted in this lane

Most pictures were PNG, JPEG or BMP files already. The inventory found these still spelled as byte rows
or C initializers; each is now a PNG that a build step turns back into the bytes:

| item                                             | format (evidence)                                                                                                                 | converter                            |
|--------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|--------------------------------------|
| `SeBitmap_*` x 13, KN5000 v10 v9 v7 v6 v5        | 1 bpp, column-major, bit 7 leftmost; drawn by static op 03 via `ColorBlit2_LargeCodeBlock`                                        | `scripts/build/se_bitmaps.py`        |
| `HDAE5000_Bitmap_Button01`, both HD-AE5000s      | 42 x 15, 8 bpp, no row pad; `HDAE5000_BitmapButt01` answers `EVT_GET_BITMAP_DATA` / `_WIDTH` / `_HEIGHT` with it                  | `scripts/build/indexed_images.py`    |
| `FontGlyphs8x16`, KN7000 IC18 boot ROM           | 224 glyphs from 0x20, 16 bytes each, MSB leftmost; `FontTable` points at it                                                       | `kn7000/tools/table_png.py`          |
| `SjisMissingGlyph`, KN7000 941 / 942 / 935 / 893 | 16 x 16, 1 bpp, column-major; `DrawString_Impl` (941 `0x48425467`) draws it for an absent Shift-JIS code                          | `kn7000/tools/table_png.py`          |
| NAKA GUI C pictures, 39 x 5 KN5000 trees         | the 8-bpp bitmaps, `UserBitmapCheck_Bitmap24x24` and the welcome screen's 16 x 17 letters (`WelcomeGlyph_C`, `Bitmap_Digit1` ...) | `scripts/build/c_bitmaps.py`         |
| `OldBuild_ValueGlyph_Bitmaps`, SX-WSA1R          | four value glyphs, byte-identical to the live ones; now listed with PNGs                                                          | `wsa1/scripts/build/wsa1_bitmaps.py` |

- `c_bitmaps.py build` writes every NAKA GUI initializer's values from its PNG before clang runs (and
  redraws the letters' ASCII-art comments); an unchanged PNG leaves the C file byte-identical.
  `c_bitmaps.py verify` checks 195 of 195 pictures: PNG = C = the built bytes at the label. For v10
  the PNG is the same file the table data uses; v9, v7, v6 and v5 got their own 39 each.
- `se_bitmaps.py verify` and `indexed_images.py verify` check 65 of 65 round trips.

## The census counts them as generated

`scripts/analysis/data_incbin_census.py` keeps an include made from a standalone media file through a
committed lossless converter in class **generated**, with the converter and the file named in its
marker (`census: generated -- scripts/build/pcm_wav.py, from waveform/wav/P0_W0000_Sine.wav (16-bit)`).
A column **from media** counts those entries per tree. In snapshot
[`docs/coverage/data-incbin-2026-10-30-03.txt`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/docs/coverage/data-incbin-2026-10-30-03.txt)
(measured at disassembly `a9b5cf764`) the class *opaque pcm* is empty in every tree; in `-02` it held
5,095 items, 70,490,064 bytes:

| tree               | generated (n / bytes) | of them from media | opaque -02 (n / bytes) | opaque -03 |
|--------------------|-----------------------|--------------------|------------------------|------------|
| `kn5000-waveform`  | 1413 / 4,170,480      | 1413 / 4,170,480   | 1413 / 4,170,480       | 0 / 0      |
| `kn7000-wave`      | 3682 / 66,319,584     | 3682 / 66,319,584  | 3682 / 66,319,584      | 0 / 0      |
| `kn5000-tabledata` | 344 / 985,431         | 336 / 831,920      | 0 / 0                  | 0 / 0      |
| `kn5000-v10`       | 10114 / 872,070       | 21 / 6,496         | 0 / 0                  | 0 / 0      |
| `kn5000-hdae5000`  | 11 / 313,706          | 6 / 308,586        | 0 / 0                  | 0 / 0      |
| `kn7000-ic18`      | 1 / 3,584             | 1 / 3,584          | 0 / 0                  | 0 / 0      |

The NAKA GUI C's pictures still count as compiled C there, not as "from media", although their C is
now written from the PNGs.

## The inventory

`python3 notes/media-files-probes/media_inventory.py` lists every picture, PCM recording and MIDI
stream of every census tree and the file behind each. At the end of the lane (2026-10-30, every tree
built) it exits 0: **8,122 items backed by a standalone file, 0 not**. *Backed* means the build reads
the item from that file, directly (JPEG, BMP, MID) or through a committed converter (PNG, WAV), or holds
rows that a converter checks against the file in the gate (the SX-WSA1R's `wsa1_bitmaps.py` /
`wsa1_fonts.py check`, and the KN5000 NAKA GUI C).

Not committed, by design: the WAVs, and the floppies' BMP / JPEG / MID files, which the floppy framework
extracts from the git-ignored disk images. Every other backing file is committed.

### What is not a file

- **SX-WSA1R, left as rows by `wsa1_bitmaps.py`'s own choice** (it refuses to guess a geometry): prom_a
  `0xFC48E4`-`0xFC52F7` beyond its eight 90-byte widgets (1,860 B), prom_b `Bitmap_DrawbarA` /
  `Bitmap_DrawbarB` (699 B each: three 233-byte slices, drawn as 123-row windows at an offset the caller
  computes), and no fifth cell at `0xF17AE0`. A PNG needs a rectangle; these have none yet.
- The probe's limit: a picture under a label that names no picture class, held as typed rows, is not
  seen.

## Open questions

- **Sample rates.** Neither ROM stores one; the WAV headers are nominal.
- **The 8-bit gain law**, KN7000 and IC307: fitted in emulation, not derived. A line-out recording of an
  8-bit sound would settle it, and whether the WAVs should apply it.
- **IC307's partner chip**: which socket, and what the other pair holds (selector classes 0-3). Until it
  is dumped, an IC307 WAV is half of each recording.
- **The 71 IC307 waves with no KN7000 counterpart**: their 8-bit or 16-bit format is the byte-correlation
  inference.

## Related pages

- [Waveform ROM Format]({{ site.baseurl }}/waveform-rom-format/): KN5000 IC307
- [KN7000 Wave ROM Format]({{ site.baseurl }}/kn7000-wave-rom-format/): the four SX-KN7000 wave chips
- [Image Gallery]({{ site.baseurl }}/image-gallery/) and [KN7000 Image Gallery]({{ site.baseurl }}/kn7000-image-gallery/)
- [ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/#the-data-include-census): the data-include census
