---
layout: page
title: Waveform ROM Format
permalink: /waveform-rom-format/
---

# Waveform ROM Format

The KN5000's tone generator (IC303, TC183C230002) reads waveform data from four 32Mbit (4MB) mask ROMs (IC304-IC307). These ROMs contain the PCM sample data used for all wavetable synthesis. This page documents the format of IC307, the only dumped waveform ROM.

## ROM Inventory

| IC | Part Number | Size | MAME Offset | Status |
|----|-------------|------|-------------|--------|
| IC304 | QS6GU3C32375 | 4 MB | 0x000000 | **undumped** — driver fills the bank with a `BAD_DUMP`-flagged copy of IC307 |
| IC305 | QS6GT3C33A01 | 4 MB | 0x400000 | **undumped** — driver fills the bank with a `BAD_DUMP`-flagged copy of IC307 |
| IC306 | QS6GU3C32374 | 4 MB | 0x800000 | **undumped** — driver fills the bank with a `BAD_DUMP`-flagged copy of IC307 |
| IC307 | QS6GX3C32008 | 4 MB | 0xC00000 | **Dumped** (CRC: 20ff4629) — the one hardware-rooted wave ROM dump |

The four ROMs form a contiguous 16 MB waveform address space, declared as `ROM_REGION16_LE` in the MAME driver (16-bit little-endian word access). IC304-306 are not `NO_DUMP` in the current driver: since 2026-07-23 the driver loads a real region there, filled with a copy of the genuine IC307 dump and marked `BAD_DUMP` so MAME's audit/UI flags it as not-genuine. This is a deliberate faithful-mechanism placeholder — voices that select IC304-306 play a real-but-wrong-instrument PCM waveform (routed through the real paged datapath) rather than silence, and it is dropped for the real dumps the moment they exist. See `src/mame/matsushita/kn5000.cpp` (`ROM_REGION16_LE(0x1000000, "waveform", 0)`) in the `kn7000_mame` driver overlay.

## IC307 Binary Layout

IC307 (4,194,304 bytes) has three distinct regions:

```
Offset      Size     Contents
─────────────────────────────────────────
0x000000    6,704    Index table + parameter records
0x001A30    4,187,536  Signed 16-bit PCM waveform data
0x3FFFC0    64       Padding (0xFF)
```

### 1. Main Index Table (0x0000 - 0x0317)

198 entries, 4 bytes each (two 16-bit LE words):

```
struct index_entry {
    uint16_t param_ptr;       // Byte offset to parameter record within ROM
    uint16_t wave_offset;     // Waveform data offset (multiply by 16 for byte address)
};
```

The first entry's `param_ptr` value (0x0318 = 792 = 198 * 4) confirms the table size: it points immediately past itself.

**Addressing scheme:** The `wave_offset` field uses a **x16 byte multiplier**. Multiplying the stored value by 16 yields the byte offset of the waveform PCM data within the ROM. This is equivalent to x8 in 16-bit word addresses, meaning the minimum addressable granularity is **8 samples (16 bytes)**.

Example: Entry 0 has `wave_offset = 0x01A3`. Byte offset = `0x01A3 * 16 = 0x1A30`, which is exactly where the PCM data begins.

### 2. Parameter Records (0x0318 - 0x1A2F)

Variable-length records referenced by the main index. Each record starts with a waveform offset word (same value cached in the main index), followed by zero or more parameter words.

**Record format:**

```
uint16_t wave_start;      // Waveform start offset (same as index wave_offset)
uint16_t params[];        // 0-N parameter words (key zones, tuning, flags)
```

Record sizes range from 2 bytes (waveform offset only, no params) to 850 bytes (424 parameter words). The most common sizes are:

| Record Size | Entries | Interpretation |
|-------------|---------|----------------|
| 2 bytes (0 params) | 1 | Single waveform, no key zones |
| 4 bytes (1 param) | 31 | Single key zone boundary |
| 6 bytes (2 params) | 25 | Two key zone boundaries |
| 8 bytes (3 params) | 44 | Three zones + terminal flag |
| 10 bytes (4 params) | 45 | Four zones (common for split instruments) |
| 12+ bytes | 46 | Multi-zone or per-key tuning data |

**Parameter word encoding:** Each parameter word is structured as `[flags:8][value:8]`:

| High Byte (Flags) | Meaning |
|---|---|
| 0x00 | Normal key zone boundary |
| 0x01 | Per-key pitch/tuning adjustment |
| 0x08 | Per-key pitch/tuning adjustment (alternate range) |
| 0x0A | Transition marker |
| 0x1C | Initial/header parameter |
| 0x40 | Mid-record marker (possible loop point or split) |
| 0x80 | End-of-record marker |
| 0xC0 | Terminal zone boundary (0x80 OR 0x40) |

| Low Byte (Value) | Meaning |
|---|---|
| 0x00 - 0x7F | MIDI key number (for key zone boundaries) |
| 0xF0 - 0xFF | Signed pitch offset (for per-key tuning: 0xFF = -1, 0xFE = -2, etc.) |

**Key zone evidence:** Multiple entries sharing the same waveform offset have systematically transposed key zone parameters:

```
Entry 185 (wave 0xFCA6): params = 0040 0030 0020 0010  (keys 64, 48, 32, 16)
Entry 186 (wave 0xFCA6): params = 0048 0038 0028 0018  (keys 72, 56, 40, 24)
Entry 187 (wave 0xFCA6): params = 0050 0040 0030 0020  (keys 80, 64, 48, 32)
```

Key zone values are listed in **descending order** (highest key first). The values correspond to MIDI note numbers and represent the boundaries where the tone generator changes pitch zones during playback.

### 3. Waveform PCM Data (0x1A30 - 0x3FFFBF)

**Format:** Signed 16-bit PCM, little-endian. Full 16-bit dynamic range (-32767 to +32767).

The byte distribution confirms signed PCM encoding:
- High bytes cluster near 0x00 and 0xFF (values near zero)
- Symmetric distribution around the zero line
- All 256 byte values present (no unused codes)

**186 unique waveforms** are indexed, ranging from 80 to tens of thousands of samples. Most are multi-cycle PCM recordings (not single-cycle wavetable entries), confirming the KN5000 uses **PCM sample-based synthesis** rather than traditional single-cycle wavetable synthesis.

**Notable waveform:** Index 0 (offset 0x01A3 = byte 0x1A30) contains a **256-sample sine wave** with less than 0.5 LSB average error from a mathematically perfect sine. This is likely used as a test tone or fallback waveform.

| Waveform | Offset | Samples | Description |
|----------|--------|---------|-------------|
| 0 | 0x01A3 | 256 | Perfect sine wave (single cycle) |
| 1 | 0x01C3 | 1,408 | Complex multi-cycle sample |
| 2 | 0x0273 | 1,152 | Complex multi-cycle sample |
| ... | ... | ... | Various instrumental timbres |
| 185 | 0xFCA6 | ~16,000+ | Long sample (shared by 6 entries) |
| 186 | 0xFEF6 | ~1,575,000 | Very long sample (shared by 7 entries) |

## Tone Generator Interface

The SubCPU firmware writes waveform addresses to the tone generator via two per-voice registers:

| Register Offset | Struct Offset | Description |
|-----------------|---------------|-------------|
| +0x0040 (group 0, bank 1) | +2 | **Pitch increment** (16-bit semitone table lookup) |
| +0x0080 (group 0, bank 2) | +4 | **Voice mode/velocity** (bit 15 = latch strobe; velocity OR'd in) |
| +0x00C0 (group 0, bank 3) | +6 | Waveform control (cleared on note-off) |

The firmware computes: `velocity_volume = (vel^2 / 4) + 63` (range 63-4095) and OR's it into register +0x0080. The latch strobe protocol (write with bit 15 SET, then rewrite with bit 15 CLEAR) triggers the tone generator hardware to load and process the voice parameters.

> ⚠ **These are not waveform pointers**, despite where they sit in the write sequence.
> `ToneGen_SetupPolyVoice` is what settles it: the pair carries pitch and velocity.

## Sample Rate

The native sample rate of the waveform data is not explicitly stored in the ROM. The pitch increment register (+0x0040) controls the playback rate. The firmware computes: `octave = (MIDI_note + 36) / 12`, `semitone = remainder`, then looks up a 16-bit value from the pitch table at ROM 0x01217D (12 entries, one per semitone). This value is written to the pitch register. The waveform data is recorded at a fixed base sample rate and pitch-shifted by the hardware during playback.

Based on the DAC specification (PCM69AU, 18-bit stereo) and typical Matsushita tone generator designs, the output sample rate is likely **48 kHz** or **44.1 kHz**.

## Relationship to Other ROMs

The waveform ROMs are separate from:
- **Rhythm Data ROM** (IC14, 4 MB) -- Contains drum pattern sequencing data, not PCM audio. Uses a completely different format with 0x83 delimiter bytes.
  The main CPU addresses it at `0x400000` and finds its data through two tables in its own ROM
  (kn5000-roms-disasm, 2026-10-03):
  - `RhythmROM_ValidateHeader` stores 0 in RAM `0x3277` when the ROM starts with the 12-byte
    signature `00 01 04 05 83 00 01 04 05 83 00 01`, else `0xFFFFFFFF` (`RhythmROM_CheckValid`
    tests it).
  - `RhythmROM_BankProgramLocators` (8 banks x 128 programs x {u16 hi, u16 lo}) gives, per
    (bank, program), an offset `(hi & 0xFF) << 16 | lo`; `VoiceAssign_Process_Return` reads
    `0x400000 + (RAM 0x3277) + offset`.  201 locators are non-zero: 201 distinct, 2 KB-aligned
    blocks `0x800`-`0x64800` of the corrected IC14 dump, each beginning with the same 12-byte
    signature.
  - `VoiceParam_BankProgramWords` (8 x 128 u16) first maps any requested (bank, program < 128)
    onto a (bank', program') pair; 1,022 of its 1,024 entries land on one of those 201 blocks
    (bank 0 programs 89 and 90 map to an empty slot).
  - `RhythmDrum_Entries` (1718 x 4 bytes) feeds that path from the drum parts: bytes 0-1 are the
    request, byte 2 selects a `RegPreset_LoadVoiceData` entry, byte 3 goes to RAM `0x3881 + drum`.

  Probes: `notes/rhythm-rom-tables-2026-10-02/locator_targets_probe.py` and
  `bank_program_map_probe.py` in kn5000-roms-disasm.
- **Table Data ROM** (IC1/IC3, 2 MB) -- Contains voice parameter tables, pitch lookup tables, and other firmware data. Accessed by the SubCPU to configure tone generator registers.
- **Waveform/sample RAM stub** (sub-CPU address `0x1E0000-0x1EFFFF`) -- still an unattributed `noprw()` stub in the MAME driver (`kn7000_mame`'s `src/mame/matsushita/kn5000.cpp`), not yet tied to a specific chip. **Correction:** earlier revisions of this page named this region "IC308/IC309, 2 x 4Mbit DRAM" — that attribution is wrong. IC308 and IC309 have since been identified (Felipe, reading the chips directly) as the DSP1/DSP2 *effect delay-line* DRAMs: IC309 (M5M44260AJ-7S, 4-Mbit) is IC311/DSP1's external delay memory, and IC308 (M5M418128AJ-6, a **1**-Mbit, byte-wide DRAM) is DSP2's. Neither is waveform/sample RAM, and IC308 is not 4 Mbit.

## Open Questions

- What is the exact base sample rate of the waveform data?
- How does the tone generator's address bus map to the 4-chip ROM layout? (Direct linear mapping via chip select, or interleaved?)
- What waveforms are in IC304-IC306? (The KN5000 has hundreds of sound presets; IC307 alone has 186 waveforms.)
- Do the parameter records encode loop start/end points for sustain loops? (Firmware analysis shows the SubCPU does NOT write loop registers — the tone generator chip likely handles looping autonomously, reading loop boundaries from ROM parameter records directly. The 0x40 flag in parameter records may indicate loop point markers.)
- What is the relationship between the 198 index entries and the ~700 sound presets in the KN5000?
- Are waveform ROMs shared across Technics keyboard models (KN6000, KN7000)?

## Related Pages

- [Tone Generator]({{ site.baseurl }}/tone-generator/) -- Register map and voice parameter structure
- [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) -- Overall audio architecture
- [Sound Categories]({{ site.baseurl }}/sound-categories/) -- Voice preset organization
