---
layout: page
title: Floppy Disk Files and Formats
permalink: /floppy-disk-formats/
---

# Floppy disk files: the formats, and the softlist disks as source

Every diskette in MAME's Technics floppy software lists is now held as typed source in the
disassembly repository and rebuilt from it byte for byte: the 14 KN5000 disks (`kn5000_flop`),
the 21 KN6000 disks (`kn6000_flop`), the 6 KN7000 disks (`kn7000_flop`) and the 9 SX-WSA1R disks
(`wsa1_flop`). The boot sector, both FATs and every directory entry are typed field by field.
Each file is typed by what it holds: panel records field by field, sound records by parameter
name, and every style and sequencer event on a line of its own.

This page describes the file formats those sources spell. How the softlist images themselves
were made, and what the instruments' formatters write, is on
[Floppy Disk Images]({{ site.baseurl }}/floppy-disk-images/).

```
make gate-floppy                                   # all 50 disks, each image's SHA-1 checked (in make gate-all)
make -C floppy gate-kn5000                         # one model: kn5000, kn6000, kn7000 or wsa1
make -C floppy src-kn5000                          # regenerate floppy/kn5000/<disk>/ from the references
```

The sources are in
[`floppy/`](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/floppy)
([README](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/floppy/README.md)).
The findings behind them are in two lane notes of 2026-10-29:
[KN5000](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/notes/floppy-kn5000-2026-10-29/README.md)
and
[WSA1R, KN6000 and KN7000](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/notes/floppy-others-2026-10-29/README.md).

## The disks

| model  | softlist      | disks | files                                                                                      |
|--------|---------------|-------|--------------------------------------------------------------------------------------------|
| KN5000 | `kn5000_flop` | 14    | CMP 75, SQT 72, PMT 64, LSW 63, TM 46, BMP 29, TXT 11, RCM 1                               |
| KN6000 | `kn6000_flop` | 21    | SQT 90, CMP 72, JPG 64, LSW 61, PMT 61, TM 50, HMP 21, TXT 10, CNV 6, and 9 others         |
| KN7000 | `kn7000_flop` | 6     | LSW 19, PMT 11, SQT 11, CMP 10, MSP 10, AST 9, CNV 6, CST 5, and 4 others                  |
| WSA1R  | `wsa1_flop`   | 9     | TM 17, MID 16, CMB 13, CRM 11, DRM 11, LSW 11, SLS 11, SRM 11, SEQ 10, SQF 10              |

The images are those of the 2026-10-18 rebuild of the softlists, which their headers call
"faithful reconstructions built from the archives' own files": no original diskette was dumped.
The KN5000 disks all share one layout: the KN5000 formatter's boot sector, two identical FATs,
files stored contiguously in directory order, zero slack after each file's end, and every free
cluster filled with `E5`. The generator checks each of those properties rather than assuming
it. Bytes per kind over the 14 KN5000 disks: CMP 4,717,568, PMT 4,304,384, BMP 2,304,830,
TM 1,350,626, SQT 665,856, RCM 470,016, LSW 229,824 and TXT 4,432.

## The framework: FAT12 as source

All four models write FAT12 1.44 MB diskettes, so one framework holds them all. Each disk is a
directory `floppy/<model>/<disk>/`, written by `floppy/tools/fat12_to_s.py` and assembled by the
repository's pinned `llvm-mc`, then `llvm-objcopy -O binary`. The images hold data only, so the
triple does not matter; the KN6000, KN7000 and WSA1R disks build the same way. `llvm-mc` was
chosen over `kn7000/tools/kn7asm.py` because it already has keyword macro parameters, `.rept`,
`.if`, `.error` and numeric local labels, and because it takes the `.incbin "f", skip, count`
form that the data-incbin census sizes.

| generated file                  | what it spells                                                                                                |
|---------------------------------|---------------------------------------------------------------------------------------------------------------|
| `<disk>/boot.s`                 | the BPB, one labelled line per field, the boot code and the signature word                                    |
| `<disk>/fat.s`                  | every 12-bit FAT slot, as chains: `fat12_run FIRST, N, LAST` per contiguous run, `fat12_free N`               |
| `<disk>/root.s`, `dir_<path>.s` | one `fat_dirent` per used slot, time and date decoded; `fat_lfn` for VFAT long names                          |
| `<disk>/disk.s`                 | the data area, cluster by cluster: each file's unit asserted at its first cluster, slack and free runs filled |
| `<disk>/files/<unit>.s`         | one unit per file, written by the model's format describer (`<model>/formats.py`)                             |

The committed trees are exactly what `make src-<model>` writes; to change one, change the
generator, a describer or a macro and regenerate. The reference images are copied, git-ignored,
out of the softlist zips into `<model>/baserom/`, with their SHA-1 checked against
`<model>/disks.mk`. `floppy/tools/sha1_gate.py` exits 1 on any mismatch and prints the first
differing offset. A payload with no better form is an `.incbin` of the git-ignored reference, declared to the
census as opaque (stale bytes). Pictures and MIDI files are the exception (since 2026-10-31): the
disks' 131 BMP, JPEG and MIDI files are committed in `<model>/<disk>/media/`, which comes before
`build/<model>/<disk>/` on the include path, so a disk unit reads the committed file
(`tools/fat12_media.py check`, in every `gate-<model>`; [Media Files]({{ site.baseurl }}/media-files/)). Unit names spell every character outside `[A-Za-z0-9_-]` as `xHH`, so
`06(DEMO).TM` becomes `06x28DEMOx29.TM`.

Census rows after the 2026-10-29 passes (`scripts/analysis/data_incbin_census.py`): every floppy
tree is at **generic 0**, meaning no file is left as an undescribed blob. What remains as opaque
is leftover bytes, listed per model below.

## KN5000 disk files

The KN5000 formats a 1.44 MB diskette itself. The first 32 bytes of the boot sector are
`FDC_Format2HD_BootSectorHead` (v10 0xE450DA), which `FDC_Format2HD_WriteBoot` (0xF522F5)
writes: `EB 1C 90`, `"Technics"`, a DOS 3.x BPB, then `EB FE` (x86 `jmp $`) at 0x1E. The rest of
the sector is zero, signature word included, so the disk does not boot a PC; all 14 softlist
disks carry exactly that sector. FAT slot 0 is `0xFF0`, from the media byte `F0` that
`FDC_Format2HD_FatHead` starts with.

The KN5000 numbers its file types by an index into `FileIO_TypeExtensions` (v10 0xEA0340: LSW
PMT SQT CMP `"TM "` MSP RCM `"MD "` SQF SEQ), and `SaveAll_RegionSaveRecs` maps each index to a
save handler. **Every save handler writes a fixed RAM region verbatim, so each file's layout is
the RAM layout of its region.** The handlers' `_VRAM` / `_ExtMem` suffixes are older misnomers.

| ext | type | on-screen name | writer (v10)                                                              | what it holds                                                                     |
|-----|------|----------------|---------------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| LSW | 0    | CURRENT PANEL  | `FileIO_SaveRegion0_VRAM` 0xF87AF6                                        | RAM 0xF980..0xFFC0 (32-byte header, panel blocks 0 and 1) + 0x800 B from 0x1E7800 |
| PMT | 1    | PANEL MEMORY   | `FileIO_SaveRegion1_VRAM` 0xF87B88                                        | RAM 0x1ED350..0x200000: header, 10 bank names, 80 panel blocks of 960 bytes       |
| SQT | 2    | SEQUENCER      | `FileIO_SaveRegion2_ExtMem` 0xF87CAC                                      | 0x800-byte song slots (`SEQ_SONG_SLOTS`, 0xAB000) and the event memory (0xB0000)  |
| CMP | 3    | COMPOSER       | `FileIO_SaveRegion3_ExtMem` 0xF87D2C                                      | `RHYTHM_PATTERN_BUF_A`: one style bank in the IC19 custom-data format             |
| TM  | 4    | SOUND MEMORY   | `FileIO_SaveRegion4_VRAM` 0xF87E41                                        | RAM 0x1E0000, 0x72AA bytes, opening with `"KN5000 SOUND RAM"` (checked at boot)   |
| RCM | 6    | RHYTHM CUSTOM  | `FileIO_SaveRegion6_Simple` 0xF87E00 / `FileIO_LoadRcmToFlash` 0xF186A9   | a header and 8 chunks for Custom Data Flash sections 0..7                         |
| BMP | -    | (wallpaper)    | `CaptureLcd` 0xFAF030; read by `Gfx_LoadSplashBMP` 0xFAE86D               | a Windows BMP: the instrument's own 320 x 240 x 8 screenshot                      |
| TXT | -    | -              | (written on a PC)                                                         | the disk's table of contents, CR LF text                                          |

### How each kind is typed

- **Panel records** (the two LSW blocks, the 80 memories of each PMT, the song's panel copy
  inside each SQT slot). A generator reads the firmware's record lists and rule lists
  (`PanelTlv_Block0_Layout`, `PanelTlv_Block1_Layout` and the `PanelTlv_Rules_*` tables) and
  writes one macro per record kind, each field's rule beside it
  (`floppy/kn5000/include/kn5000_panel.inc`). Part records (tags 0x00..0x19) name `sound` (with
  the tone database's name in a comment), `bank`, `fx_flags`, `level`, signed `pan`,
  `midi_channel` and `status`; tag 0x78 is the style name, 0x44..0x46 the drawbars, 0x48 the
  style number and tempo, and 0x61/0x63..0x66 the five DSP slots' algorithms. The LSW header's
  `"HK"` is the one `FileIO_CheckRegionSignature` tests.

  **Panel records, byte by byte.** Every editable panel setting has a parameter descriptor in the
  firmware that names the record (its tag), the byte and the bits that hold it
  ([Panel Parameter Keys]({{ site.baseurl }}/panel-parameter-keys/)), so the floppy sources name each byte
  after its setting (`floppy/kn5000/panel_fields.py`): a part's sound, bank, volume and mute, sustain bits,
  DIGITAL EFFECT, DSP effect send, reverb send, pan, key shift, tuning, bend range and its MIDI bits; the
  style number, bank, APC mode and variation; the panel-memory filter switches; the metronome; and so on.
  The descriptors correct three older readings: part +3 is VOLUME (bits 6:0) and MUTE (bit 7), +4 bit 6 is
  DIGITAL EFFECT and bit 3 SUSTAIN (not "reverb on" / "chorus on"), and +7 is REVERB SEND. A DSP effect slot
  (tags 0x61, 0x63..0x66) holds the effect number and then that effect's parameters in order (DEPTH, LFO
  SPEED, ...), from the v10 tables `DspFxParamCountTable`, `DSPCfg_LookupAndExtract_PtrTable` and
  `DspParamName_Table`; a parameter whose range passes 255 takes two bytes, big-endian. Over the 23,487 DSP
  slot records on the disks that layout decodes every record of 28 of the 44 effects used; the reverbs 18,
  19 and 21-26, GEQ, ROOM and PEQ+S.DELAY pack two parameters to a word in a way not yet established.
  Of the 818 macro arguments of the 43 record kinds, 175 are named from a descriptor or the curated studies,
  33 by the firmware's key only, 23 are DSP slot parameters, 419 are `reserved_<offset>` (zeroed on load, no
  descriptor, no reference), 43 are bits no descriptor names, and 125 keep `f<offset>` (mostly the companion
  records 0xC0..0xD7, refreshed from each part's sound by `PanelTlv_ResolvePartCompanions`). Counts and
  probes: the disassembly's `notes/kn5000-style-2026-10-31/README.md`.
- **TM sound records.** The 470-byte record is the sub-CPU's 426-byte tone record plus four
  11-byte velocity-split records, named from the sub-CPU reader table. The value ranges come
  from the sound-RAM byte clamp at v10 0xFEEC48, which also settles which fields are signed. The
  kit record is a 295-byte header and 128 user drum instruments of 80 bytes, then the edit index
  and an image checksum, `~sum` of the 0x24B8 words from +0x10 (checked on all 45 KN5000 files).
  406 of the 470 record bytes are named (71 of them by inference), and 10,025 of the 10,538 kit
  bytes.
- **SQT slot headers** are the RAM image of the current-song record (0xF180): the track mask and
  assignment, the edit parameters, per-track tail cells and write offsets, the free list, the
  punch-in fields, `event_used_size16`, and the +0xD0 track table, whose first cells are the
  chain heads of all 132 tracks present on the disks. Absent tracks read 0xFFFF there. +0x1C is
  the song password (`FmmPasswordFunc` writes it into all ten slots); fields that nothing reads are
  `written_only_<off>`, and fields that nothing writes or reads are `stale_<off>`, RAM residue
  (`notes/kn5000-style-2026-10-31/probes/sqt_field_refs.py`). The songs' structure, in RAM, is on
  [Sequencer]({{ site.baseurl }}/sequencer/#song-storage).
- **Style banks** (CMP, RCM sections 0..6) share one bank layout with the custom-data and table
  ROM banks: the header's size words (`used_size16 * 16` is the .CMP size), the
  **30 directory records, which are the 30 STYLE_SECTION records of one style, not 30 styles**,
  and the 64-byte fill-in cell at +0x13C0 that `AccDemo_LoadFillIn` reads. Cell links count
  blocks from block 20 of the bank (bank + 0x1400) in all 82 banks; no other base makes a tenth
  as many links mutual. Every field is named: [The Composer style bank](#the-composer-style-bank).
- **RCM** holds sections 0..6 as style banks and section 7's slot store (owner maps, 40 small
  and 4 large slots, erased on the factory disk). The loader writes it to Custom Data Flash,
  stamping the section number into the style directory on the way
  ([Custom Data Flash]({{ site.baseurl }}/custom-data-flash/)).
- **BMP** headers are typed field by field; palette and pixels are `.incbin`s of the committed
  `.bmp` in the disk's `media/` folder. **TXT** is one `.ascii` line per line.

### The Composer style bank

A Composer style is one 0x16800-byte image: a 0x60-byte header, 30 section records of 0x60 bytes
(variations A/B/C 1-4, then intro, fill-in and ending 1-2 of A, B and C), the five COMPOSER CHORD MAPs
at +0xBA0, a measure-start table at +0xC40, a 64-byte fill-in cell at +0x13C0 and 340 cells of 256 bytes
from +0x1400. The header holds the Composer password (+0x0E) and the NORMAL / EXPAND mode (+0x10).
Each section record holds the first cells of its DRUM, BASS and ACCOMP1-3 parts, the time signature,
the number of measures, the RECORD SETTING (key, major / minor, bass and accompaniment type), a flag
that keeps the meter changeable until something is recorded, the preset style the section uses, and
per part the sound, panpot, digital effect on/off, pitch point and upper note limit. The same layout
is in the IC19 custom-data banks, the .CMP files and each section of an .RCM file.

| offset              | field                                                                                           | read or written by (v10)                                                                       |
|---------------------|-------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| header +0x0E        | `password` (u16)                                                                                | `FmmPasswordFunc` through `SetCurrentSlotIndex`; read by `GetCurrentSlotIndex` (both misnamed) |
| header +0x10        | `composer_mode`: 0 NORMAL, 1 EXPAND                                                             | `AcCmpMdBoxProc`, `CmpSetP1_TtlDispatch`                                                       |
| record +0x00..+0x0A | first cells of DRUM, BASS, ACCOMP1-3 (+0x02 unused)                                             | `MapBitFlagsToChannelOffset`                                                                   |
| record +0x0C        | `time_sig`                                                                                      | `RhythmPatInit_LoadParams`                                                                     |
| record +0x0D        | `last_measure` (the MEASURE row shows it + 1)                                                   | `RhythmPatInit_LoadParams`, `Tempo_DisplayMeasureRange`                                        |
| record +0x0E        | `rec_chord`: bits 0-3 key, 4 minor, 5 accomp 7th, 6 bass 7th                                    | `RhythmPatInit_LoadParams`, `RhythmProc_CheckConfigBits`                                       |
| record +0x0F        | `edit_flags`: bit 7 = MEASURE / TIME SIGNATURE changeable                                       | `DrumVoice_Handler0` / `1` refuse with error 19 when it is clear                               |
| record +0x10, +0x11 | `style_number`, `style_group`: the preset style (a `PANEL_STYLE` pair)                          | `RhythmVariation_Select_Entry_Data`                                                            |
| record +0x18 + 8 i  | part i (DRUM, BASS, ACCOMP1-3): sound, bank, pan, digital effect, byte 4, pitch point, high key | `MainCmpSetFunc`, `AccPatch_ChannelBitToIndex`                                                 |
| record +0x40        | `name`                                                                                          | `Tempo_DisplayMeasureRange`                                                                    |
| +0xBA0              | `chord_map[5]`, 32 bytes each: one value per variation (0..11 or 0xFF)                          | `CmpNcp_StepSlotInGroup2`; selecting map n sets `PANEL_STYLE` = 0xF0 + n                       |
| +0xC40              | `measure_start[12][5][8]`: {cell, offset}                                                       | `AccVoice_GetMeasureStartBlock`, `AccPatch_StoreMeasureCursor`                                 |

The other header words and the record bytes not listed have no reader: they are constant in every bank
or zero, and the code hard-codes the sizes they would give. Part byte 4 is the fifth byte of the part's
program-change record [INFERENCE: its use is not traced]; bit 7 of the high-key byte is also an inference.
Both describers, `floppy/kn5000/formats.py` for the floppies and `scripts/build/style_events.py` for the
custom-data banks, import one module, `scripts/build/style_bank_layout.py`, whose docstring gives the
evidence for every field (disassembly, `notes/kn5000-style-2026-10-31/README.md`).

### Events, one per line

Parseable music is typed, never left opaque. Two grammars are spelled, in
`floppy/kn5000/events.py` with their macros in `floppy/kn5000/include/kn5000_files.inc`:

- **Style banks** use the IC19 grammar of `scripts/build/style_events.py`: `st_beat`, `st_end`,
  `st_note pos, note, vel, dur_ticks, dur_beats`, `st_note2`, `st_ctl1..3 pos, value`. The user
  banks also need **`st_ctl4` / `st_ctl5` (0xD4 / 0xD5) with two data bytes**, which the
  factory IC19 banks never use. That argument count is measured: with two data bytes all 29
  chains that stopped at 0xD4/0xD5 parse to their end; with one or three, more than 20 break.
- **Sequencer event memory** uses the demo-song grammar of `scripts/build/demo_preset_to_midi.py`:
  `sq_beat`, `sq_note status, pos, note, vel, dur_ticks, dur_beats`, `sq_run` for running status,
  and `sq_ev` for 0x82 end-of-track and other statuses. Every byte tokenises. A chain starts at a
  cell whose PREV is 0 and whose byte 0 is non-zero; byte-0 = 0 cells are the free list.

Typed text runs 2.2x (LSW) to 5.8x (SQT) the size of the binary it spells.

| probe row (`notes/floppy-kn5000-2026-10-29/probes/kn5000_floppy_formats.py`, all 14 disks) | count                     |
|--------------------------------------------------------------------------------------------|---------------------------|
| boot sector == firmware head, rest zero                                                    | 14 / 14                   |
| LSW files of 0xE40 bytes with `"HK"` at +4                                                 | 63                        |
| PMT memories with all 46 block-0 records / with only the first 43                          | 4,128 / 344               |
| TM files in the KN5000 0x72AA layout / a KN3000 image                                      | 45 / 1                    |
| style banks whose link base is block 20                                                    | 82                        |
| style cells / chains / events                                                              | 18,400 / 12,324 / 506,970 |
| style next links mutual / not                                                              | 5,958 / 13                |
| SQT cells; next links mutual / not                                                         | 1,377; 1,186 / 7          |

The firmware's panel record lists are identical in v5, v6, v7, v9 and v10, so the 43-record
blocks (13 LSWs, 344 PMT memories) were written by an older firmware than any dumped revision
[INFERENCE: these files date from 1997-98]. They are typed as far as they follow the list, then
as tag/length records up to their `FF FF` mark.

**The last 2 KB of a .LSW file** are the Sound Arranger memory, RAM 0x1E7800 (`AccStyle_InitVRAM`
fills it from `AccStyle_RamImage_1E7800`): a 16-byte header and 200 ten-byte records, one per preset
style, holding the DRUM kit and the BASS and ACCOMP1-3 sounds the player chose for that style (each
with its DIGITAL EFFECT switch), and a flag that tells the accompaniment to use them instead of the
style's own sounds. `AccVoiceState_Snapshot` writes a record and `AccTuning_LoadFromROM` reads it back
when the flag is set. The floppy sources type it with the `sndarg` macro in all 63 files.

**Not typed:** the body of `ca5000r/03FOLKS2.TM`, a "KN3000 SOUND RAM" image in another
model's layout (opaque, 64 entries, 158,704 bytes in all). BMP pixels are media. Fields with
neutral names (`f<offset>`, `b_<offset>` and the like) carry a TODO saying what was tried.

## KN6000 and KN7000 disk files

The KN6000 and KN7000 wrap most files in a small container, `floppy/tools/kd/kd.py` (byte layout
in its docstring and `floppy/tools/kd.inc`). The first byte of the magic names the model: `I` is
the KN6000, `J` the KN7000.

| magic                 | used for                                 | parts                                                                    |
|-----------------------|------------------------------------------|--------------------------------------------------------------------------|
| `I KD` / `IK D`       | KN6000 .CMP .TM .PMT .EFC, .SQT .LSW     | one or two parts, each a deflate stream from **zlib 1.0.4, level 6**     |
| `J KD`                | KN7000 .CMP .PMT .MSP .SQT .LSW          | **LZSS**, not deflate                                                    |
| `I K\1` / `J K\1`     | .AST, .CST                               | a u32 inflated size, then one deflate part                               |
| `IK \0` / `JK \0`     | .HMP .FAV .MD                            | stored                                                                   |

- **Deflate.** The file drops the zlib stream's 2-byte header but keeps its big-endian adler32,
  and the stored size still counts the dropped header. The coder is zlib 1.0.4: the KN7000
  program links it (`deflateInit2_` checks the version string "1.0.4"), and every multi-block
  stream on the disks ends its first block at exactly 4,096 symbols. That is 1.0.4's
  unconditional early block end in `_tr_tally`; later releases compile it only under
  `TRUNCATE_BLOCK`, at 8,192. A modern zlib reproduces only the single-block streams. The
  repository's coder is `kn7000/tools/zlib10_deflate.py`, a Python transcription of 1.0.4's
  deflate.
- **'J KD' LZSS**, derived from the TCMP header each stream must decode to: flag bytes low bit
  first, 1 = literal; a reference is `lo, hi` with ring position `lo | (hi >> 3) << 8` (13 bits)
  and length `(hi & 7) + 3`; an 8 KB ring filled with 0 and starting at 0x1FF6; no end marker.
  Okumura's LZSS.C binary-tree encoder with N = 8192 and F = 10 reproduces every stream
  (`floppy/tools/kd/lzss_j.py`). It is the KN5000's SLIDE8K coder too: re-encoding the table data's
  five live SLIDE8K help streams with `lzss_j.encode` makes every one of the factory's decisions, so
  `scripts/build/compress_slide8k.py` now builds them without a reference stream
  (`notes/misc-2026-10-31/probes/slide8k_vs_lzss_j.py`). SLIDE4K is the same encoder with N = 4096 and
  F = 18 (`slide4k_vs_okumura.py`, all 22 streams; see [LZSS Compression]({{ site.baseurl }}/lzss-compression/)).

`kd.py verify` over every file of the 27 KN6000 and KN7000 disks: 397 KD and 15 K1 containers
re-encode byte-identical, and 122 files are stored.

| model  | kind           | how it is held                                                                                               |
|--------|----------------|--------------------------------------------------------------------------------------------------------------|
| KN6/7  | .CMP           | the TCMP container typed in full, every event one per line                                                   |
| KN6/7  | .SQT           | song records (track directory, the song's panel memory as `PMR_*` records) and event cells, event by event   |
| KN6/7  | .PMT           | bank names and memories, each record a `PMR_*` line (`kn7000/src/include/panel_memory.inc`)                  |
| KN6/7  | .LSW           | part 1: the current panel and a second record block; part 2: per rhythm, eight sound references              |
| KN6000 | .TM            | 40 SOUND EDIT records, the custom-sound kit block and the tail                                               |
| KN7000 | .CST           | one CUSTOM slot record, typed by the custom-data emitter                                                     |
| KN7000 | .MSP           | the TPAD container: header, banks, 18 pads, every event                                                      |
| KN6000 | .EFC           | 55 records of 0x42 bytes (the CUSTOM record's five 0x42-byte kinds), name first                              |
| KN6/7  | .MD .FAV       | header and u32 entries; named groups of {kind, value} items                                                  |
| KN6/7  | .AST           | generated: the deflate of the custom-data image that `kn7000/src/customdata` / `kn6000/src/customdata` build |
| KN6/7  | .CNV           | generated: the build output of `kn7000/src/cnv/*.s`                                                          |
| KN6/7  | .HMP           | the 0x18C-byte home-page record and a 160 x 100 BMP (media)                                                  |
| KN6000 | .JPG           | the extracted file (media)                                                                                   |
| KN6000 | .TXT .ACT .PRE | `.ascii` lines                                                                                               |
| KN6/7  | .VER           | a Cakewalk .WRK, chunk by chunk                                                                              |

### Styles: the TCMP container (.CMP)

A style file is the instrument's "TCMP" style memory, saved whole. Every field below is read by a
KN7000 program 941 routine (names and addresses in `kn7000/kn7000_manual.sym`, quoted in
`floppy/tools/kn_style.inc`).

- **Header**: `"TCMP" 00 00`, a u16BE checksum (`SumU16BE` over 0x1B00 halfwords from 0x70), a
  field at +0x0E that is copied between containers and not validated, the u24 container length,
  the u24 allocator top (`MemStyleAllocOffsetGet`), the style count (3 in every file), a 0x18-byte
  template tail and 0x40 spaces.
- **3 style records of 0x80 bytes** at 0x70 + 0x80·s: the name and four variation names
  (16-byte fields of 13 characters), and at +0x50 the 20 variation indices the style owns.
- **60 variation records of 0xE0 bytes**: kind, the B-half flag, eight per-part bytes, bars − 1,
  the meter and the stream offset, then eight part set-ups of 24 bytes each
  ([INFERENCE] the 24 fields of the part-field table; the first 15 match the built-in styles'
  set-ups of the IC18 rhythm ROM,
  [`kn7000/notes/ic18-rhythm-rom.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/ic18-rhythm-rom.md)).
- **A heap of 60 event streams**, one per variation in allocation order: the owning variation's
  index, a u24BE length and the events (`MemStyleAreaStreamsVerify`). In all 82 files the heap
  tiles 0x3670..top exactly. Event lengths follow the firmware's length-by-status table: note
  0x9n + 5, controller + 2, program + 3, pressure + 1, bend + 2, SysEx; `F4` marks a beat and
  `F5` ends the stream; a byte below 0x80 is a position, the tick within the beat.

### Songs (.SQT)

- **Part 1** is 1 or 10 song records, 0x870 bytes on the KN6000 and 0x8E0 on the KN7000, each
  opening with `"ZZZZ"`, the 10-song flag and the model signature (`01 0A` KN6000, `01 0D`
  KN7000). At +0xD0 is the KN5000's 16-track directory of {flags, u16 first cell}; at +0x140 a
  full PANEL MEMORY record, typed as `PMR_*` lines. The KN7000 keeps these records at
  0x501A5800 + n·0x8E0 (`Rec8E0TablePtr`) and the cells in its song memory of 0x4D8 pages at
  0x501AB9A0 (`SongPageStorePtr`).
- **Part 2** holds the 256-byte cells: flags, prev, next and 251 data bytes.
- **Events** were first typed by a measured grammar: a tick byte before every event; 0x9n + 4,
  0xAn + 6, 0xBn + 3, 0xCn + 3, 0xDn + 1, 0xEn + 2, 0x8n + 2; 0xF1 + 5, 0xF2 + 6, 0xF3 + 7;
  0x85 / 0x86 + 0; 0x81 beat, 0x82 end. Since 2026-10-29 `kn_sqt.py` uses the firmware's own
  per-status length table (KN7000 `0x485B9328`, read by `func_4845BC5B`; the player tick steps
  each track through it). The table agrees with the measured lengths on every status the 27 disks
  hold, adds 0x84 (bar), 0x8A (PIC), 0xA2 / 0xA3 and 0xF4, and makes 0xB1-0xBF non-events. The
  macros' parameters are the event layouts: `sq_cc` {part, cc, value}, `sq_a` {part, flags, id
  big-endian, value}, `sq_note` {key, velocity, u16 duration}. All 422 track chains parse to
  their end. Free cells are opaque: they hold bytes left from earlier songs.
- **The song record's tail is an SRAM image.** The firmware reads a song's parameters at song
  record `+0x120 + (block - 0x84000000)`, so `+0x120` onward mirrors the backup SRAM from
  `0x84000000`: `+0x140` is the panel memory, and after it comes block `0x52` (46 bytes on the
  KN6000, 40 on the KN7000), typed in all 605 song records as `PMR_52_46` / `PMR_52_40`. The
  field names of the `PMR_*` records are on
  [Panel Memory Records]({{ site.baseurl }}/kn7000-panel-memory/).

### Custom-data backups (.AST)

Each .AST inflates to the SHA-1 of one custom-data dump: the nine KN7000 IC21 images and the
KN6000's `01ctmini` (the same as the KN6500's). So the .AST units are not stored at all: the
build compresses the custom-data images that the typed sources in `kn7000/src/customdata` and
`kn6000/src/customdata` produce. The header words at +8 / +0xC are never written by the saver;
they are the old contents of its stack frame (`kn7000/tools/ast_file.py`).

**Stale song bytes.** The bytes after a track's 0x82 and the free cells hold events of an earlier
version of the song, in two orders: the model's own tick-first order and the KN5000's status-first
order. In 76 of 327 tails the KN5000-order notes occur, equal and in order, among the same track's live
events (`notes/floppy-leftovers-2026-10-31/probes/sqt_tails2.py`) [INFERENCE: the factory songs were
converted in place from KN5000 song files]. `kn_sqt.py` types them per event in whichever order parses
further (macros `k5_note`, `k5_run`, `k5_ev` in `floppy/tools/kn_song.inc`).

| model  | stale bytes | tick-first | KN5000 order | cut events | still opaque              |
|--------|-------------|------------|--------------|------------|---------------------------|
| KN6000 | 32,861      | 17,923     | 12,046       | 1,124      | 1,768 (126 declarations)  |
| KN7000 | 11,122      | 5,541      | 222          | 89         | 5,270 (96 declarations)   |

A note's last byte is its duration in **beats, 0..255** (KN7000 941 `func_48459B49` reads it unsigned),
so the four notes with 141 or 216 there are held that long. **The KN6000 .TM's last word** is the sound
records' checksum as RAM held it at save time: `PostTmTransLoad` recomputes it after every load, so no
load reads the file's word. It matches in 12 of 50 files (`notes/floppy-leftovers-2026-10-31/probes/tm_tail.py`; the earlier "13" was a miscount)
[INFERENCE: the other 38 were saved after a sound change that did not recompute it].

## SX-WSA1R disk files

The WSA1R saves RAM windows:

| kind           | what it holds                                                                                                  |
|----------------|----------------------------------------------------------------------------------------------------------------|
| .TM            | 4 banks of sound flash: tag, 8 lines, 64 NORMAL SOUND records, the DRUM SOUND kit and its 128 NOTE DATA blocks |
| .CMB           | the user combination bank: 16 bank names, 128 combinations of 23 records each                                  |
| .SEQ           | the song store's 256-byte blocks, events one per line                                                          |
| .SQF           | the sequencer workspace: ten song records of 0xC00 bytes                                                       |
| .LSW .SLS      | record blocks: the current combination and further {tag, length} blocks                                        |
| .SRM .CRM .DRM | three re-maps: names, group names, {number, source} entries                                                    |
| .MID           | a Standard MIDI File, held as media; the tail of its last 1 KB window is a copy of the window before           |

- **.TM, every byte named.** Technics' Reference Guide publishes the NORMAL SOUND layout
  (713 bytes: GENERAL DATA 217, TONE DATA 4 x 81, MODELING DATA 4 x 43) and the DRUM SOUND layout
  (KIT DATA 0x98, SOUND SELECT 0x100, 128 NOTE DATA of 150). These are the strides
  `SoundRam_ClearFourBanks` writes. Transcribed into
  `wsa1/notes/sysex-probes/sound_layout.json`, they become the 532 named parameters of
  `floppy/wsa1/include/wsa1_sound.inc`, none of them reserved.
- **.CMB** fields are named from the Reference Guide (`cmb_*` macros).
- **.MID.** The SMF writer flushes whole 1,024-byte windows (`SmfOut_WindowsFlushed`), so 13 of
  the 16 files end with stale window bytes after the last track; the three demo1 files are not
  padded.
- **.SEQ** blocks are the prom_b block store's; their events use the KN5000 demo-song grammar
  (bit 7 = status), which parses 443 of 444 chains [INFERENCE].

**Leftovers.** The WSA1R moves files in kilobytes, so they carry bytes past their data, now typed or
proven copies (`notes/floppy-leftovers-2026-10-31/probes/wsa1_leftovers.py`, `seq_layout.py`):

- a combination bank's last kilobyte repeats 0x100 bytes of the chunk before (the first 0x100 bytes of
  combination 112, in all 13 .CMB files): `DiskSave_StreamLinkRamToFile` writes each 0x2C00 chunk 0x400
  at a time, and the last write carries the window before;
- an SMF's last window repeats the window before (the window buffer is reused), held as an `.incbin` of
  the committed .mid;
- a song file is a whole number of KB and ends with free blocks of its block store;
- the 128 bytes at sound bank +0x10..+0x8F are the USER 1 / USER 2 sound-group names, read by
  `UserSoundBank_RemoteGroupNameAddr` and `SoundGroupName_Lookup`;
- the PC boot sector is one small "This is not a bootable disk" stub on all nine disks, now source
  (`floppy/tools/pc_boot_stub.s`, 16-bit x86) [INFERENCE: written by the tool that made the images].

What stays opaque is one 250-byte run of 0xDF 0xF7 pairs in `qsdisk/01WORKS_.SEQ` block 838 (180
entries, 50,503 bytes before this).

## Open questions

- **KN5000:** what 0xD4 / 0xD5 do in the style player (the argument count is measured, the
  meaning is not); which firmware revision wrote the 43-record panel blocks (a v1-v4 dump would
  settle it); the byte packing of 16 DSP effects' slot records and the 125 panel bytes still named
  `f<offset>`. Settled on 2026-10-31 (`notes/kn5000-style-2026-10-31/probes/style_links.py`): the
  13 non-mutual style links and the two chains that stop at 0x10 / 0x87 all lie in stale cell-shaped
  blocks 12..19, below the cell area, of three .CMP files, where no directory record reaches them; the
  7 non-mutual SQT links leave orphan cells, on no track chain and not on the free list.
- **KN6000 / KN7000:** the SOUND EDIT and voice-element fields of the KN6000 .TM; the 1,768 + 5,270
  stale song bytes that no event order explains; which firmware path changes a KN6000 sound without
  recomputing the checksum. (The PANEL MEMORY fields are named, on
  [Panel Memory Records]({{ site.baseurl }}/kn7000-panel-memory/); bit 7 in the last event of five
  tracks is a duration in beats above 127; the .TM tail word is explained above.)
- **WSA1R:** block 838's 0xDF 0xF7 run. (The 8 lines at the start of each sound bank, which
  `SoundRam_ClearFourBanks` does not write, are the USER sound-group names.)
- **Cross-model:** settled: 'J KD' is the KN5000's SLIDE8K coder (above).

## Related pages

- [Floppy Disk Images]({{ site.baseurl }}/floppy-disk-images/): how the softlist images were
  made, and what the formatters write
- [FDC Subsystem]({{ site.baseurl }}/fdc-subsystem/) and
  [Storage Subsystem]({{ site.baseurl }}/storage-subsystem/) (KN5000)
- [KN7000 Storage & File System]({{ site.baseurl }}/kn7000-storage-subsystem/)
- [Custom Data Flash]({{ site.baseurl }}/custom-data-flash/): the style bank and RCM sections
- [Music Stylist Database]({{ site.baseurl }}/music-stylist-database/)
