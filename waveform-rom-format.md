---
layout: page
title: Waveform ROM Format
permalink: /waveform-rom-format/
---

# Waveform ROM Format

The KN5000's tone generator (IC303, TC183C230002) reads waveform data from four 32Mbit (4MB) mask ROMs (IC304-IC307). These ROMs contain the PCM sample data used for all wavetable synthesis. This page documents the format of IC307, the only dumped waveform ROM.

## ROM Inventory

| IC    | Part Number  | Size | MAME Offset | Status                                                                                                       |
|-------|--------------|------|-------------|--------------------------------------------------------------------------------------------------------------|
| IC304 | QS6GU3C32375 | 4 MB | 0x000000    | **undumped** — `NO_DUMP` upstream; the overlay driver fills the bank with a `BAD_DUMP`-flagged copy of IC307 |
| IC305 | QS6GT3C33A01 | 4 MB | 0x400000    | **undumped** — `NO_DUMP` upstream; the overlay driver fills the bank with a `BAD_DUMP`-flagged copy of IC307 |
| IC306 | QS6GU3C32374 | 4 MB | 0x800000    | **undumped** — `NO_DUMP` upstream; the overlay driver fills the bank with a `BAD_DUMP`-flagged copy of IC307 |
| IC307 | QS6GX3C32008 | 4 MB | 0xC00000    | **Dumped** (CRC: 20ff4629) — the one hardware-rooted wave ROM dump                                           |

The four ROMs form a contiguous 16 MB waveform address space, declared as `ROM_REGION16_LE` in the MAME driver (16-bit little-endian word access). IC304-306 are `NO_DUMP` in mainline MAME (mamedev/mame `src/mame/matsushita/kn5000.cpp`). In the `kn7000_mame` overlay driver they are not: since 2026-07-23 it loads a real region there, filled with a copy of the genuine IC307 dump and marked `BAD_DUMP` so MAME's audit/UI flags it as not-genuine. The copy keeps the real paged datapath exercised. Since 2026-08-06 the default PCM rendering mutes every voice that selects IC304-306, the 'with sine substitutes' rendering plays those voices as sines, and the wrong-instrument copy is heard only with `KN5000_UNDUMPED=play`. The placeholder is dropped for the real dumps the moment they exist. See `src/mame/matsushita/kn5000.cpp` (`ROM_REGION16_LE(0x1000000, "waveform", 0)`) in the `kn7000_mame` driver overlay.

## IC307 Binary Layout

IC307 (4,194,304 bytes) is **four independent 1 MB pages**, at `0x000000`, `0x100000`, `0x200000` and `0x300000`. Each page has the same three regions (a directory of `{param_ptr, wave_offset}` pairs, variable-length parameter records, then signed 16-bit PCM) and declares its own directory length: entry 0's `param_ptr` is 4 × N. N is 198, 168, 1,072 and 57, so the chip holds 1,495 directory slots and 1,413 distinct wave offsets (`tools/ic307_wave_directory.py` in this repository measures these from the dump). Offsets are relative to the page base, which is why `wave_offset` × 16 reaches exactly 1 MB. The sections below describe page 0:

```
Page-0 offset  Size        Contents
─────────────────────────────────────────
0x000000       6,704       Index table + parameter records
0x001A30       1,041,872   Signed 16-bit PCM waveform data
```

The last 64 bytes of the chip (`0x3FFFC0`-`0x3FFFFF`) are `0xFF`.

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

Variable-length records referenced by the main index. Each record starts with a waveform offset word (same value cached in the main index), followed by zero or more parameter words.

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

**Parameter word encoding:** Each parameter word is structured as `[flags:8][value:8]`:

| High Byte (Flag) | Meaning                                                                                                                                                                     |
|------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 0x00             | Key-split boundary (unit 1/8 octave, not a MIDI note; see below)                                                                                                            |
| 0x01 - 0x2F      | Per-zone fine tune; values cluster in 0xEA-0xFF (small negative trims)                                                                                                      |
| bit 7 set        | End of record: only ever on a record's last pair, not counting the zero words that pad each page's last record (286 of 286 in the whole chip), and not every record has one |
| bit 6 set        | A marker (258 occurrences in the whole chip), not decoded                                                                                                                   |

| Low Byte (Value) | Meaning                                                                                                                                         |
|------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| flag 0x00        | Key-split boundary value (1/8-octave units; not limited to 0x00-0x7F, 0x80 occurs 52 times in the whole chip, per `tools/ic307_flag_counts.py`) |
| 0xEA - 0xFF      | Signed pitch offset (for per-key tuning: 0xFF = -1, 0xFE = -2, etc.)                                                                            |

**Key zone evidence:** Multiple entries sharing the same waveform offset have systematically transposed key zone parameters:

```
Entry 185 (wave 0xFCA6): params = 0040 0030 0020 0010
Entry 186 (wave 0xFCA6): params = 0048 0038 0028 0018
Entry 187 (wave 0xFCA6): params = 0050 0040 0030 0020
```

Key-split values are listed in **descending order**. They are **not** MIDI note numbers: against the firmware's own zone table the relation is key = 1.5 × (value − 0x28), so one unit is 1/8 octave and successive entries of a multisample shift by 8 units. The relation is measured; the unit reading is an inference.

### 3. Waveform PCM Data (page 0: 0x1A30 - 0xFFFFF)

**Format:** Signed 16-bit PCM, little-endian. Full 16-bit dynamic range (-32767 to +32767).

The byte distribution confirms signed PCM encoding:
- High bytes cluster near 0x00 and 0xFF (values near zero)
- Symmetric distribution around the zero line
- All 256 byte values present (no unused codes)

**Page 0 indexes 186 unique waveforms** (0-185; the whole chip 1,413), ranging from 80 to tens of thousands of samples. Most are multi-cycle PCM recordings (not single-cycle wavetable entries), confirming the KN5000 uses **PCM sample-based synthesis** rather than traditional single-cycle wavetable synthesis.

**Notable waveform:** Index 0 (offset 0x01A3 = byte 0x1A30) contains a **256-sample sine wave** with less than 0.5 LSB average error from a mathematically perfect sine. This is likely used as a test tone or fallback waveform.

| Waveform | Offset | Samples | Description                                                               |
|----------|--------|---------|---------------------------------------------------------------------------|
| 0        | 0x01A3 | 256     | Perfect sine wave (single cycle)                                          |
| 1        | 0x01C3 | 1,408   | Complex multi-cycle sample                                                |
| 2        | 0x0273 | 1,152   | Complex multi-cycle sample                                                |
| ...      | ...    | ...     | Various instrumental timbres                                              |
| 184      | 0xFCA6 | 4,736   | Multisample shared by entries 185-190                                     |
| 185      | 0xFEF6 | 2,128   | Multisample shared by entries 191-197; ends at the page boundary 0x100000 |

## Tone Generator Interface

The SubCPU firmware names a voice's recording in one register, `+0x040` (group 0, bank 1). On the voice-engine path that word is the **recording selector** `(class << 12) + entry`, copied verbatim from a tone-database zone record ([Tone Database]({{ site.baseurl }}/tone-database/#wave-selection-end-to-end)). `entry` indexes one page's directory and the class picks the page. Classes 4, 5 and 7 need exactly 198, 168 and 57 entries, which are IC307's pages 0, 1 and 3. No CPU reads the wave ROMs, so IC303 resolves the selector itself (an inference by elimination). Pitch goes to `+0x400` (absolute log pitch) and level to `+0x080`.

On the auxiliary 8-voice pool, `ToneGen_SetupPolyVoice` instead writes `+0x040` from the 12-word table at `0x01217D` (values `0x0000`, `0x2000`, `0x4000`, `0x6000`, then zeros, indexed by note mod 12). It ORs `velocity_volume = (vel^2 / 4) + 63` (range 63-4095) into `+0x080`. Whether that `+0x040` word is a selector or a rate constant is unresolved. Bit 15 of `+0x080` frames the burst: it is set on the second write and cleared on the last.

## Sample Rate

The native sample rate of the waveform data is not stored in the ROM, and neither is a root note. Pitch reaches the chip as an absolute log pitch in `+0x400`, and IC303 resamples. The instrument's output rate is **44.1 kHz**, proven from the effects DSP's ROM constants ([Effects DSP]({{ site.baseurl }}/effects-dsp/)). The rate the recordings were made at is still unknown.

## Relationship to Other ROMs

The waveform ROMs are separate from:
- **Rhythm Data ROM** (IC14, 4 MB) -- Contains drum pattern sequencing data, not PCM audio. Uses a completely different format with 0x83 delimiter bytes.
  The main CPU addresses it at `0x400000` and finds its data through two tables in its own ROM
  (kn5000-roms-disasm, 2026-10-03):
  - `RhythmROM_ValidateHeader` stores 0 in `RHYTHM_ROM_BASE` (RAM `0x3277` in v10/v9, `0x31DB` in v7) when the ROM starts with the 12-byte
    signature `00 01 04 05 83 00 01 04 05 83 00 01`, else `0xFFFFFFFF` (`RhythmROM_CheckValid`
    tests it).
  - `RhythmROM_BankProgramLocators` (8 banks x 128 programs x {u16 hi, u16 lo}) gives, per
    (bank, program), an offset `(hi & 0xFF) << 16 | lo`; `VoiceAssign_Process_Return` reads
    `0x400000 + RHYTHM_ROM_BASE + offset`.  201 locators are non-zero: 201 distinct, 2 KB-aligned
    blocks `0x800`-`0x64800` of the corrected IC14 dump, each beginning with the same 12-byte
    signature.
  - `VoiceParam_BankProgramWords` (8 x 128 u16) first maps any requested (bank, program < 128)
    onto a (bank', program') pair; 1,022 of its 1,024 entries land on one of those 201 blocks
    (bank 0 programs 89 and 90 map to an empty slot).
  - `RhythmDrum_Entries` (1718 x 4 bytes) feeds that path from the drum parts: bytes 0-1 are the
    request, byte 2 selects a `VoiceAssign_PresetSelToCase` entry, byte 3 goes to RAM `0x3881 + drum`.

  Probes: `notes/rhythm-rom-tables-2026-10-02/locator_targets_probe.py` and
  `bank_program_map_probe.py` in kn5000-roms-disasm.
- **Table Data ROM** (IC1/IC3, 2 MB) -- Contains the tone database (voice records; multisample SET descriptors, which carry each SET's root key and base pitch; and the key maps and zone records that pick each zone's recording and pitch trims) and other firmware data. Read by the main CPU, which copies its tone database (`0x830000`-`0x87FFFF`) to Sub CPU RAM `0x050000` at boot; the SubCPU reads it there ([Tone Database]({{ site.baseurl }}/tone-database/)).
- **No waveform/sample RAM** (sub-CPU address `0x1E0000-0x1EFFFF`) -- the sub CPU never accesses `0x1E0000` on its own bus. Every `0x1E0000` literal in the v1.42 payload is a destination argument of `InterCPU_E1_DMA_Transfer`, i.e. the main CPU's IC21 battery SRAM reached over the inter-CPU link. The `noprw()` line at that address in the MAME drivers maps nothing real. **Correction:** earlier revisions of this page named this region "IC308/IC309, 2 x 4Mbit DRAM" — that attribution is wrong. IC308 and IC309 have since been identified (Felipe, reading the chips directly) as the DSP1/DSP2 *effect delay-line* DRAMs: IC309 (M5M44260AJ-7S, 4-Mbit) is IC311/DSP1's external delay memory, and IC308 (M5M418128AJ-6, a **1**-Mbit, byte-wide DRAM) is DSP2's. Neither is waveform/sample RAM, and IC308 is not 4 Mbit.

## Open Questions

- What is the exact base sample rate of the waveform data?
- Which physical socket holds each selector bank? The class nibble picks a 1 MB page; classes 4, 5 and 7 match IC307's pages 0, 1 and 3 exactly, which implies (by inference) that classes 4-7 are IC307. Which socket is bank 0 cannot be settled until IC304-IC306 are dumped.
- What waveforms are in IC304-IC306? (The KN5000 has hundreds of sound presets; IC307 alone has 1,413 distinct waves.)
- Where are loop points? Not in the parameter records, probably: every field there is a single byte, too small to address into a wave of tens of thousands of samples, and `loopprobe.py` (kn7000_mame `tools/kn5000-rom-structure/`) found none. The firmware writes no loop registers either, so looping is IC303's own business. Bit 6 of the flag byte is still undecoded.
- ~~What is the relationship between the index entries and the sound presets?~~ A tone's partials reach directory entries through the tone database's SET descriptors and zone records, which produce 1,444 (class, entry) selectors ([Tone Database]({{ site.baseurl }}/tone-database/#wave-selection-end-to-end)).
- Are waveform ROMs shared across Technics keyboard models (KN6000, KN7000)?

## Related Pages

- [Tone Generator]({{ site.baseurl }}/tone-generator/) -- Register map and voice parameter structure
- [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) -- Overall audio architecture
- [Sound Categories]({{ site.baseurl }}/sound-categories/) -- Voice preset organization
