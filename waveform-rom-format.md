---
layout: page
title: Waveform ROM Format
permalink: /waveform-rom-format/
---

# Waveform ROM Format

The KN5000's tone generator (IC303, TC183C230002) reads waveform data from four 32Mbit (4MB) mask ROMs (IC304-IC307). These ROMs contain the PCM sample data used for all wavetable synthesis. This page documents the format of IC307, the only dumped waveform ROM.

> **IC307 is half of a pair (2026-10-30).** IC307 is not a linear wave ROM: it holds every other 16-bit word of each recording, directory entry and parameter record, as the "Y" chip of a word-interleaved pair like the SX-KN7000's wave ROMs. Its undumped partner holds the other half. Earlier revisions of this page, and of the pages that link here, described the chip's words as complete recordings and records; read the layout below as one chip's half. The evidence is in [IC307 is half of a pair](#ic307-is-half-of-a-pair).

## ROM Inventory

| IC    | Part Number  | Size | MAME Offset | Status                                                                                                       |
|-------|--------------|------|-------------|--------------------------------------------------------------------------------------------------------------|
| IC304 | QS6GU3C32375 | 4 MB | 0x000000    | **undumped** — `NO_DUMP` upstream; the overlay driver fills the bank with a `BAD_DUMP`-flagged copy of IC307 |
| IC305 | QS6GT3C33A01 | 4 MB | 0x400000    | **undumped** — `NO_DUMP` upstream; the overlay driver fills the bank with a `BAD_DUMP`-flagged copy of IC307 |
| IC306 | QS6GU3C32374 | 4 MB | 0x800000    | **undumped** — `NO_DUMP` upstream; the overlay driver fills the bank with a `BAD_DUMP`-flagged copy of IC307 |
| IC307 | QS6GX3C32008 | 4 MB | 0xC00000    | **Dumped** (CRC: 20ff4629) — the one hardware-rooted wave ROM dump                                           |

The MAME driver declares the four ROMs as one contiguous 16 MB waveform address space, `ROM_REGION16_LE` (16-bit little-endian word access). IC307's contents say that is not how the hardware reads them: the four chips are two word-interleaved pairs (*[INFERENCE]* from IC307 alone; [below](#ic307-is-half-of-a-pair)), and which socket is IC307's partner is not known. IC304-306 are `NO_DUMP` in mainline MAME (mamedev/mame `src/mame/matsushita/kn5000.cpp`). In the `kn7000_mame` overlay driver they are not: since 2026-07-23 it loads a real region there, filled with a copy of the genuine IC307 dump and marked `BAD_DUMP` so MAME's audit/UI flags it as not-genuine. The copy keeps the real paged datapath exercised. Since 2026-08-06 the default PCM rendering mutes every voice that selects IC304-306, the 'with sine substitutes' rendering plays those voices as sines, and the wrong-instrument copy is heard only with `KN5000_UNDUMPED=play`. The placeholder is dropped for the real dumps the moment they exist. See `src/mame/matsushita/kn5000.cpp` (`ROM_REGION16_LE(0x1000000, "waveform", 0)`) in the `kn7000_mame` driver overlay.

## IC307 as Source

Since 2026-10-29 IC307 has a source tree in the disassembly, [`waveform/`](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/waveform), that rebuilds the 4 MB image byte for byte and is part of `make gate`. Per page, the directory and the 1,495 parameter records are typed rows. Each of the 1,413 PCM waves is a labelled item, named after the wave source that selects it (`P0_W0184_ElectricBass`, ...) or `_Drawbar` when only drawbar zone records select it. 1,261 waves are named this way (958 of them `_Drawbar`) and 152 carry only their page and index. Two page-first waves are named `P0_W0000_Sine` and `P2_W0000_Sine` from their measured shape.

| file                                                                                                                                                            | content                                                                                     |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| [`waveform/kn5000_waveform_ic307.s`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/waveform/kn5000_waveform_ic307.s)                     | root: the format header, the macro include, the four page includes                          |
| [`waveform/waveform_macros.inc`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/waveform/waveform_macros.inc)                             | `WaveDirEntry`, `WaveRecHead`, `WaveSplit`, `WaveSeq`                                       |
| `waveform/ic307_page0.s` .. `ic307_page3.s`                                                                                                                     | per page: directory, parameter records, 16-byte alignment, the PCM waves, the 0xFF tail     |
| `waveform/waveform.ld`                                                                                                                                          | links at 0: no CPU reads the chip, so a label's value is its file offset                    |
| [`scripts/generators/gen_waveform_ic307_s.py`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/scripts/generators/gen_waveform_ic307_s.py) | the one-shot generator that wrote the tree; the `.s` files are the authoritative source now |

```
make rebuilt_ROMs/kn5000_waveform_ic307.llvm.rom   # copies the reference first, SHA-1 checked
make gate                                          # includes verify-ic307-reference and the byte gate
```

The reference image is not committed. `make` copies `original_ROMs/kn5000_waveform_rom.ic307` (git-ignored) from the private romset (`KN5000_IC307_REF`) and refuses a copy whose SHA-1 is not `4b511bff6625f4655cabd96a263bf548d2ef4bf7`. The other 23,824 B are typed source.

**The waves are WAV files** (since 2026-10-30, lane media-files; committed since 2026-10-31, lane media-build; [Media Files]({{ site.baseurl }}/media-files/)). Each of the 1,413 PCM bodies (4,170,480 B) is a committed `waveform/wav/<label>.wav`, and the build reads the WAVs back with no reference image present (`make waveform-wav` re-extracts missing ones from the reference, a maintenance target the build never runs): `scripts/build/pcm_wav.py build` writes each raw item to `waveform/build/pcm/<label>.pcm`, which the page source `.incbin`s with the marker `census: generated -- scripts/build/pcm_wav.py, from waveform/wav/<label>.wav`. A 16-bit wave's WAV `data` chunk is the ROM bytes unchanged; an 8-bit one's is each byte XOR 0x80 (WAV 8-bit PCM is unsigned). The headers say 22,050 Hz, a nominal rate (below), and carry no loop. `waveform/wav_manifest.tsv` (committed, no sample data) lists each wave's offsets, bit depth, file name and comment; `scripts/generators/gen_ic307_wav_manifest.py` writes it and `scripts/converters/respell_ic307_pcm_as_wav.py` respelled the pages. The data-incbin census row `kn5000-waveform` reads generated 1,413 / 4,170,480 B, all of them from media, opaque 0, generic 0 (snapshot `docs/coverage/data-incbin-2026-10-30-04`, as in `-03`; it read opaque 1,413 / 4,170,480 B in `-02`).

Every figure below is printed by `notes/waveform-ic307-2026-10-29/probes/ic307_layout.py` in the disassembly repository ([probes](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/notes/waveform-ic307-2026-10-29/probes)); the selector walk by `tonedb_selector_users.py` beside it.

## IC307 Binary Layout

IC307 (4,194,304 bytes) is **four independent 1 MB pages** (each the Y half of a 2 MB page of the pair's stream, as on the SX-KN7000), at `0x000000`, `0x100000`, `0x200000` and `0x300000`. Each page has the same three regions (a directory of `{param_ptr, wave_offset}` pairs, variable-length parameter records, then signed 16-bit PCM) and declares its own directory length: entry 0's `param_ptr` is 4 × N. N is 198, 168, 1,072 and 57, so the chip holds 1,495 directory slots and 1,413 distinct wave offsets (`tools/ic307_wave_directory.py` in this repository measures these from the dump). Offsets are relative to the page base, which is why `wave_offset` × 16 reaches exactly 1 MB.

| page | file offset | N     | directory     | records       | empty records | zero alignment | PCM             | distinct waves | 0xFF tail |
|------|-------------|-------|---------------|---------------|---------------|----------------|-----------------|----------------|-----------|
| 0    | 0x000000    | 198   | 0x0000-0x0317 | 0x0318-0x1a2d | 1             | 2 B            | 0x01a30-0xfff7f | 186            | 128 B     |
| 1    | 0x100000    | 168   | 0x0000-0x029f | 0x02a0-0x1831 | 3             | 14 B           | 0x01840-0xfff7f | 151            | 128 B     |
| 2    | 0x200000    | 1,072 | 0x0000-0x10bf | 0x10c0-0x2695 | 961           | 10 B           | 0x026a0-0xfff7f | 1,034          | 128 B     |
| 3    | 0x300000    | 57    | 0x0000-0x00e3 | 0x00e4-0x0233 | 0             | 12 B           | 0x00240-0xfffbf | 42             | 64 B      |

- Record offsets ascend strictly in all four pages. Wave starts ascend too, except in page 1 at entries 79, 82 and 85, which point back at earlier waves (79 at the "ReverseCym.1" wave stored among the snares, 82 at a "ReverseCym.2" wave, 85 at a wave nothing selects).
- The zero bytes after a page's last record reach exactly the next 16-byte boundary (`.balign 16, 0` in the source): a wave start counts 16-byte granules, so the first wave must start on one.
- **Tails.** Pages 0-2 end with 128 bytes of 0xFF and page 3 with 64 bytes. (Earlier revisions of this page said only the chip's last 64 bytes were 0xFF.)

The sections below describe page 0:

```
Page-0 offset  Size        Contents
─────────────────────────────────────────
0x000000       6,704       Index table + parameter records
0x001A30       1,041,872   Signed 16-bit PCM waveform data
```

Page 0's PCM ends at `0xFFF7F`; the last 128 bytes of the page are `0xFF`.

### 1. Main Index Table (0x0000 - 0x0317)

198 entries, 4 bytes each (two 16-bit LE words):

```
struct index_entry {
    uint16_t param_ptr;       // Byte offset to parameter record within the page
    uint16_t wave_offset;     // Waveform data offset (multiply by 16 for byte address)
};
```

The first entry's `param_ptr` value (0x0318 = 792 = 198 * 4) confirms the table size: it points immediately past itself.

**Addressing scheme:** The `wave_offset` field uses a **x16 byte multiplier**. Multiplying the stored value by 16 yields the byte offset of the waveform PCM data within the page. This is equivalent to x8 in 16-bit word addresses, meaning the minimum addressable granularity is **8 samples (16 bytes)**.

Example: Entry 0 has `wave_offset = 0x01A3`. Byte offset = `0x01A3 * 16 = 0x1A30`, which is exactly where the PCM data begins.

### 2. Parameter Records (0x0318 - 0x1A2F)

Variable-length records referenced by the main index. Each record starts with a waveform offset word (same value cached in the main index, in all 1,495 records), followed by zero or more parameter words. A record runs to the next one, and a page's last record to its last non-zero word. The whole chip holds 7,184 parameter words in 530 non-empty records; 965 records are head-only, 961 of them in page 2.

**Record format:**

```
uint16_t wave_start;      // Waveform start offset (same as index wave_offset)
uint16_t params[];        // 0-N parameter words (key zones, tuning, flags)
```

Record sizes range from 2 bytes (waveform offset only, no params) to 850 bytes (424 parameter words). The most common sizes, for page 0's 198 records (`waverec.py`, kn7000_mame `tools/kn5000-rom-structure/`), are:

| Record Size         | Entries | Interpretation                            |
|---------------------|---------|-------------------------------------------|
| 2 bytes (0 params)  | 1       | Single waveform, no key zones             |
| 4 bytes (1 param)   | 31      | Single key zone boundary                  |
| 6 bytes (2 params)  | 25      | Two key zone boundaries                   |
| 8 bytes (3 params)  | 44      | Three zones + terminal flag               |
| 10 bytes (4 params) | 46      | Four zones (common for split instruments) |
| 12+ bytes           | 51      | Multi-zone or per-key tuning data         |

**Parameter word encoding.** Each parameter word is `[flags:8][value:8]`. Two kinds of word are told apart by a byte rule (measured over the whole chip):

| kind      | source macro                       | rule                                                                    | words |
|-----------|------------------------------------|-------------------------------------------------------------------------|-------|
| key split | `WaveSplit value, mark=, end=`     | flag bits 5..0 clear and value a multiple of 8, at most 0x80            | 658   |
| sequence  | `WaveSeq value, a, b, mark=, end=` | everything else; `value` s8, `a` = flag bits 5..3, `b` = flag bits 2..0 | 6,526 |

Both kinds share two flag bits:

- **bit 7, end of record**: set on 286 words, every one of them the last word of its record. Not every record has one.
- **bit 6, marker**: set on 258 words, not decoded.

Record shapes, with K for a key-split word and S for a sequence word:

| shape       | records |
|-------------|---------|
| empty       | 965     |
| S*          | 277     |
| K*          | 212     |
| S* K*       | 29      |
| K* S*       | 9       |
| S* K* S*    | 2       |
| K* S* K* S* | 1       |

**Sequence words: the KN7000's record words.** Since IC307's records are every other word of a KN7000-format record (p1, p3, p5, ...; [below](#ic307-is-half-of-a-pair)), its words have the KN7000 layout `[flags:2][code:6][value:8]`: a value of 0x80 or more is a segment of (256 − value) granules, flag bit 7 is the KN7000's `LOOP_END` / `REC_END` bit and bit 6 its `LOOP_START` bit, and the 6-bit code is the 8-bit segments' gain ([KN7000 Wave ROM Format]({{ site.baseurl }}/kn7000-wave-rom-format/#parameter-record)). The granule size, and half of each record's words, are on the partner chip, so the segments cannot be laid out from IC307 alone. *[INFERENCE]* The key-split words (a value below 0x80, multiples of 8) are the KN7000's "split list". The 2026-10-29 counts that follow are of the IC307 words as stored. The value is negative in 6,494 of 6,526 words, and 5,957 of them are -1 to -8. `a` and `b` never exceed 5, and differ by at most 1 in 6,128 words (a − b = −1: 2,829; 0: 337; +1: 2,962). A record can hold up to 424 of them (page 0 entry 173). In 30 cases a sequence record repeats the tail of an earlier record of the same page, and its wave starts later in the same audio: page 0 entry 158 is entry 157 without its first 4 words and starts 44 granules later, entry 159 is 157 without 23 words and 296 granules later, and page 2 has 26 more (entries 42-46 inside entry 40, among others). **[Inference]** A sequence record describes the audio from the entry's start in time order, one word per segment of variable length, so an entry can play on past its own item into the next ones (157 through 158's and 159's audio).

**Correction.** Earlier revisions read flags `0x01`-`0x2F` as "per-zone fine tune" with values `0xEA`-`0xFF` as small pitch trims. The values do sit there, but a record of hundreds of such words on a single wave has no zones to tune; that reading is retired.

**Key zone evidence:** Multiple entries sharing the same waveform offset have systematically transposed key zone parameters:

```
Entry 185 (wave 0xFCA6): params = 0040 0030 0020 0010
Entry 186 (wave 0xFCA6): params = 0048 0038 0028 0018
Entry 187 (wave 0xFCA6): params = 0050 0040 0030 0020
```

Key-split values are listed in **descending order**. They are **not** MIDI note numbers: against the firmware's own zone table the relation is key = 1.5 × (value − 0x28), so one unit is 1/8 octave and successive entries of a multisample shift by 8 units. The relation was measured by an earlier lane and was not re-derived by the 2026-10-29 source work; the unit reading is an inference. The key-split rule above is a byte rule: in mixed records, a word with bits 5..0 clear and a value that is not a multiple of 8 (for example `0x98`) is spelled `WaveSeq v, 0, 0`.

### 3. Waveform PCM Data (page 0: 0x1A30 - 0xFFFFF)

**Format:** two's complement, little-endian words, every other word of each recording. 1,213 of the 1,413 waves are 16-bit recordings, one sample per word; 200 are 8-bit recordings, two signed samples per word, low byte first, so an IC307 item holds the sample pairs (4i, 4i + 1). The format is known for 1,342 waves from the KN7000 recording with the same audio (1,173 16-bit, 169 8-bit; the flag that says so is in the directory's P word, on the partner chip) and inferred for the other 71 from the correlation of a word's two bytes (31 8-bit, 40 16-bit; the rule is calibrated on the matched waves: > 0.5 in 0 of 1,170 16-bit ones and 152 of 169 8-bit ones). Counts: `waveform/wav_manifest.tsv`, `ic307_kn7000_match.py`.

The byte distribution confirms signed PCM encoding:
- High bytes cluster near 0x00 and 0xFF (values near zero)
- Symmetric distribution around the zero line
- All 256 byte values present (no unused codes)

**Page 0 indexes 186 unique waveforms** (0-185; the whole chip 1,413). A wave's length is taken as the distance to the next distinct wave start, or to the page's 0xFF tail; over the chip that is 32 B to 75,040 B (16 to 37,520 samples). Most are multi-cycle PCM recordings (not single-cycle wavetable entries), confirming the KN5000 uses **PCM sample-based synthesis** rather than traditional single-cycle wavetable synthesis.

**Test sines.** Index 0 (offset 0x01A3 = byte 0x1A30) is a **256-word sine wave**: peak 32,767, mean deviation 0.26 LSB from `32767 sin(2 pi k / 256)`. It is exactly the even samples of the SX-KN7000's 512-sample sine `Main_P00_W000`, so the recording is a 512-sample sine of which IC307 holds half (`pcm_encoding_probe.py`). **Page 2's first wave is the same sine.** No SET or drawbar record selects either one (`P0_W0000_Sine`, `P2_W0000_Sine`); they are probably test tones.

| Waveform | Offset | Samples | Description                                                               |
|----------|--------|---------|---------------------------------------------------------------------------|
| 0        | 0x01A3 | 256     | Perfect sine wave (single cycle)                                          |
| 1        | 0x01C3 | 1,408   | Complex multi-cycle sample                                                |
| 2        | 0x0273 | 1,152   | Complex multi-cycle sample                                                |
| ...      | ...    | ...     | Various instrumental timbres                                              |
| 184      | 0xFCA6 | 4,736   | Multisample shared by entries 185-190                                     |
| 185      | 0xFEF6 | 2,064   | Multisample shared by entries 191-197; ends at the 0xFF tail at 0xFFF80   |

## Tone Generator Interface

The SubCPU firmware names a voice's recording in one register, `+0x040` (group 0, bank 1). On the voice-engine path that word is the **recording selector** `(class << 12) + entry`, copied verbatim from a tone-database zone record ([Tone Database]({{ site.baseurl }}/tone-database/#wave-selection-end-to-end)). `entry` indexes one page's directory and the class picks the page. No CPU reads the wave ROMs, so IC303 resolves the selector itself (an inference by elimination).

`tonedb_selector_users.py` walks the Sub CPU's whole wave-selection chain backwards over the table-data ROM: tone partial blocks (`WaveSel_StageA1_FromPatchBlock`), drum-instrument layers (`WaveSel_StageA1_FromToneSlot`), velocity bands (`Velocity_Select_Split_Zone`), the SET zone records, and the drawbar zone blocks read by `WaveSel_StageB_Build_Reg040_Footage`:

| class | distinct entries used | largest entry | IC307 page with N entries | users                                                               |
|-------|-----------------------|---------------|---------------------------|---------------------------------------------------------------------|
| 0     | 212                   | 213           | (page 0 has 198)          | SETs                                                                |
| 1     | 168                   | 176           | (page 1 has 168)          | SETs                                                                |
| 2     | 184                   | 184           | (page 2 has 1,072)        | SETs                                                                |
| 3     | 415                   | 435           | (page 3 has 57)           | SETs                                                                |
| 4     | 195                   | 197           | page 0, N = 198           | SETs (organs, accordions, effects, basses)                          |
| 5     | 164                   | 167           | page 1, N = 168           | SETs (flutes, drums and cymbals)                                    |
| 6     | 1,007                 | 1,071         | page 2, N = 1,072         | 49 entries (up to 150) from SETs; 960 from the drawbar zone records |
| 7     | 57                    | 56            | page 3, N = 57            | SETs (piano, slap and dance bass)                                   |

- **Proven: the entry counts fit all four pages.** For classes 4, 5, 6 and 7 the largest entry used is exactly N − 1 of IC307's pages 0, 1, 2 and 3. **Class 6 is page 2**: through the SETs alone it reaches only entry 150, but the drawbar organ's 2 × 729 + 4 zone records reach 960 distinct page-2 entries up to 1,071. Page 2 is the drawbar organ's page: 958 of its 1,034 waves are selected only by drawbar records. (Earlier work matched only classes 4, 5 and 7.)
- **Proven: classes 0, 1 and 3 are not pages 0, 1 and 3 of this chip.** Their largest entries (213, 176, 435) exceed those pages' directories.
- **Inferred: page = class & 3, and classes 4-7 are IC307.** Which socket holds classes 0-3 waits on dumps of IC304-IC306.
- **Not walked:** the alternate StageA2 maps (+0x9C / +0xA0 / +0xA4, which alias the standard ones in the factory data), the RAM user-tone banks, `Voice_Init_Type1`'s `(tick & 7)` offset, and the class doubling under mode bit 2 in `WaveSel_StageB_Store_Reg040`.
- **Entries nothing selects:** page 0 entries 0 (the sine), 152 and 159; page 1 entries 77, 80 and 83 (three 32-sample waves just before the ride cymbals) and 85; 65 page-2 entries (0, the sine, 24, and 63 of entries 41-111, many of them entries that start inside another entry's audio); none in page 3. Pitch goes to `+0x400` (absolute log pitch) and level to `+0x080`.

On the auxiliary 8-voice pool, `ToneGen_SetupPolyVoice` instead writes `+0x040` from the 12-word table at `0x01217D` (values `0x0000`, `0x2000`, `0x4000`, `0x6000`, then zeros, indexed by note mod 12). It ORs `velocity_volume = (vel^2 / 4) + 63` (range 63-4095) into `+0x080`. Whether that `+0x040` word is a selector or a rate constant is unresolved. Bit 15 of `+0x080` frames the burst: it is set on the second write and cleared on the last.

## IC307 is half of a pair

Lane media-files (2026-10-30) compared IC307 with the SX-KN7000's four wave ROMs, whose format is known ([KN7000 Wave ROM Format]({{ site.baseurl }}/kn7000-wave-rom-format/)): there the Y and X chips of a tone generator are one stream of 16-bit words, word i of Y then word i of X. The probes, in [`notes/media-files-probes/`](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/notes/media-files-probes) of the disassembly repository (they read the private dumps and print numbers only):

| probe                        | result                                                                                                                                                                                                                                                                                           |
|------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `ic307_kn7000_match.py`      | 1,342 of IC307's 1,413 waves (1,391 of 64 B or more were searched) occur verbatim in a KN7000 Y chip: 1,162 in IC203, 180 in IC207, none in an X chip; 1,339 at a KN7000 recording's first sample, 1,327 over their whole length                                                                 |
| `pcm_encoding_probe.py`      | IC307's 256-word sine is exactly the even samples of the KN7000's 512-sample `Main_P00_W000`; s16le reads IC307's items with the fewest full-scale jumps in 1,165 of 1,391 (ties 169)                                                                                                            |
| `ic307_records_vs_kn7000.py` | of 1,495 directory entries, 1,430 have a wave at a KN7000 recording's first sample; 456 records equal the words p1, p3, p5, ... of a partner KN7000 record, 965 head-only records pair with KN7000 records of at most one parameter word, 9 match none; none matches the control p0, p2, p4, ... |

So IC307 is **the Y chip of a word-interleaved pair**: it holds every other word of each recording, of each directory entry and of each record. The KN7000 notes had inferred it (kn7000_mame g13); these probes show it. What follows from it:

- **The directory.** IC307's `{param_ptr, wave_offset}` pair is the A and B words of the KN7000's four-word entry `{A, P, B, Q}`. The P word (pitch exponent, the 8-bit flag, the loop granule) and the Q word are on the partner chip.
- **The records.** IC307 holds the head and the odd parameter words; the even ones are on the partner (*[INFERENCE]* from the p1, p3, ... match: a record's head is 32-bit aligned, so the words alternate chips from there).
- **The audio.** An IC307 WAV is the Y half of its recording: a 16-bit one sounds like the recording at half the rate without anti-alias filtering, an 8-bit one holds the sample pairs (4i, 4i + 1). For the 1,327 waves that match whole, the KN7000's X chip holds the other half of what is very probably the same recording; the disassembly does not combine them (a KN7000 dump is not a KN5000 one).
- **The hardware.** The MAME driver maps IC304-IC307 as one linear 16 MB region; these contents say the four chips are two word-interleaved pairs instead, so the tone generator reads its wave ROMs in pairs (*[INFERENCE]*). Which socket (IC304, IC305 or IC306) is IC307's partner, and what the other pair holds (by the class analysis above, selector classes 0-3), is not known. *[INFERENCE, not tested]* The service manual's Wave ROM Check names the chips in two pairs, C keys → IC304 & IC305 and C# to B → IC306 & IC307 ([Test Modes]({{ site.baseurl }}/test-modes/)), which fits IC306 being IC307's partner; the lane did not use or check this.

## Sample Rate

The native sample rate of the waveform data is not stored in the ROM, and neither is a root note. Pitch reaches the chip as an absolute log pitch in `+0x400`, and IC303 resamples. The instrument's output rate is **44.1 kHz**, proven from the effects DSP's ROM constants ([Effects DSP]({{ site.baseurl }}/effects-dsp/)). The rate the recordings were made at is still unknown. The IC307 WAV headers say 22,050 Hz, a nominal figure: half the SX-KN7000's nominal 44,100 Hz (the rate at which its tone generator steps one source sample per output sample), because IC307 holds every other sample.

## Relationship to Other ROMs

The waveform ROMs are separate from:
- **Rhythm Data ROM** (IC14, 4 MB) -- the factory accompaniment styles: 202 style records and the 28,400 one-part patterns they play, as MIDI-like event streams, not PCM audio. The main CPU maps it at `0x400000` and selects a record through `VoiceParam_BankProgramWords` and `RhythmROM_BankProgramLocators` in its own ROM; a zero locator is a valid pointer to the first record. The dump in circulation has address lines A19 and A21 exchanged. See [Rhythm ROM (IC14)]({{ site.baseurl }}/rhythm-rom/), which supersedes the summary this page used to carry (it counted 201 records, missing the one at offset 0).
- **Table Data ROM** (IC1/IC3, 2 MB) -- Contains the tone database (voice records; multisample SET descriptors, which carry each SET's root key and base pitch; and the key maps and zone records that pick each zone's recording and pitch trims) and other firmware data. Read by the main CPU, which copies its tone database (`0x830000`-`0x87FFFF`) to Sub CPU RAM `0x050000` at boot; the SubCPU reads it there ([Tone Database]({{ site.baseurl }}/tone-database/)).
- **No waveform/sample RAM** (sub-CPU address `0x1E0000-0x1EFFFF`) -- the sub CPU never accesses `0x1E0000` on its own bus. Every `0x1E0000` literal in the v1.42 payload is a destination argument of `InterCPU_E1_DMA_Transfer`, i.e. the main CPU's IC21 battery SRAM reached over the inter-CPU link. The `noprw()` line at that address in the MAME drivers maps nothing real. **Correction:** earlier revisions of this page named this region "IC308/IC309, 2 x 4Mbit DRAM" — that attribution is wrong. IC308 and IC309 have since been identified (Felipe, reading the chips directly) as the DSP1/DSP2 *effect delay-line* DRAMs: IC309 (M5M44260AJ-7S, 4-Mbit) is IC311/DSP1's external delay memory, and IC308 (M5M418128AJ-6, a **1**-Mbit, byte-wide DRAM) is DSP2's. Neither is waveform/sample RAM, and IC308 is not 4 Mbit.

## Open Questions

- What is the exact base sample rate of the waveform data?
- Which socket is IC307's partner (the X half of its pair), and which pair holds selector classes 0-3? The class nibble picks a 1 MB page; classes 4, 5, 6 and 7 match IC307's pages 0, 1, 2 and 3 exactly, which implies (by inference) that classes 4-7 are IC307 and its partner. Neither can be settled until IC304-IC306 are dumped. Until then an IC307 WAV is half of each recording.
- ~~What do the sequence words encode?~~ They are the KN7000's record words `[flags:2][code:6][value:8]` seen from one chip ([above](#2-parameter-records-0x0318---0x1a2f)); laying the segments out needs the partner's granule size and its half of each record. The 8-bit gain law of the code is fitted in emulation, not derived.
- The 71 waves with no KN7000 counterpart: their 8-bit or 16-bit format is the byte-correlation inference.
- Why do page 0 entries 152 and 159, page 1 entries 77, 80, 83 and 85, and 65 page-2 entries have no selector? Possibly older-build leftovers, or users reached only through the RAM user-tone banks (not walked).
- What waveforms are in IC304-IC306? (The KN5000 has hundreds of sound presets; IC307 alone has 1,413 distinct waves.)
- Where are loop points? As on the KN7000, a loop is a run of segments in the parameter record, marked by flag bits 6 (`LOOP_START`) and 7 (`LOOP_END`) on its segment words and counted in the granule the P word gives; the P word and half of the record are on the partner chip, so IC307 alone does not give the loops (the WAVs carry none). The firmware writes no loop registers, so looping is IC303's own business. (Earlier revisions said the records hold no loops; `loopprobe.py`, kn7000_mame `tools/kn5000-rom-structure/`, had looked for loops in IC307's words as complete records.)
- ~~What is the relationship between the index entries and the sound presets?~~ A tone's partials reach directory entries through the tone database's SET descriptors and zone records, which produce 1,444 (class, entry) selectors ([Tone Database]({{ site.baseurl }}/tone-database/#wave-selection-end-to-end)).
- ~~Are waveform ROMs shared across Technics keyboard models?~~ The recordings are: 1,342 of IC307's 1,413 waves are in the SX-KN7000's wave ROMs (IC203, IC207). Whether the KN6000's are the same is not known (not dumped).

## Related Pages

- [Media Files]({{ site.baseurl }}/media-files/) -- the WAV files and how to make them
- [KN7000 Wave ROM Format]({{ site.baseurl }}/kn7000-wave-rom-format/) -- the format IC307 is half of
- [Tone Generator]({{ site.baseurl }}/tone-generator/) -- Register map and voice parameter structure
- [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) -- Overall audio architecture
- [Sound Categories]({{ site.baseurl }}/sound-categories/) -- Voice preset organization
