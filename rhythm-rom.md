---
layout: page
title: Rhythm ROM (IC14)
permalink: /rhythm-rom/
---

# Rhythm ROM (IC14)

The 4 MB mask ROM at IC14 holds the KN5000's factory accompaniment styles: **202 style records**, and the
**28,400 one-part patterns ("tracks")** they play. The main CPU maps it at `0x400000`-`0x7FFFFF` and reads it in
64 KB banks (`AccVoice_OffsetTable` holds the 64 bank bases `0x400000 + n * 0x10000`, so the firmware does no
scrambling of its own). The dump in circulation has address lines **A19 and A21 exchanged**. Undoing that swap gives
the layout the firmware's pointers address, and all 46,056 of them land on a track.

Since 2026-10-29 IC14 has a source tree in the disassembly,
[`rhythm_data/`](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/rhythm_data), that rebuilds
the descrambled image byte for byte **without a single `.incbin`**: every byte is a typed record, an event macro or
FF fill. Firmware addresses on this page are v10's (the same code is in v9 and v7). The lane notes, with every probe
and the command that runs it, are
[`notes/rhythm-data-ic14-2026-10-29/`](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/notes/rhythm-data-ic14-2026-10-29).

## The two images

| file (private romset)                                | size | CRC32      | SHA-1                                      | what it is                                              |
|------------------------------------------------------|------|------------|--------------------------------------------|---------------------------------------------------------|
| `kn5000_rhythm_data_rom.ic14`                        | 4 MB | `aa4917ce` | `fef7f1927935d8fdada2afbdbfac29aac56e1c3c` | descrambled: the layout the firmware's pointers address |
| `kn5000_rhythm_data_rom.ic14.as-read-a19a21-swapped` | 4 MB | `76d11a5e` | `e4b572d318c9fe7ba00e5b44ea783e89da9c68bd` | the chip as read, address lines A19 and A21 exchanged   |

`make` copies both into `original_ROMs/` (git-ignored) after a SHA-1 check.
`scripts/build/rhythm_rom_address_swap.py` maps one onto the other: `raw[a] = img[swap(a)]`, where `swap` exchanges
address bits 19 and 21. The swap is its own inverse and moves whole 512 KB blocks (`0x080000` <-> `0x200000`,
`0x180000` <-> `0x300000`). `make verify-rhythm-data-raw`, part of `make gate`, applies it to the rebuilt image and
compares the result with the raw read.

**Why the descrambled image is the right one.** All 46,056 track pointers in the style records land on a track
header in it; in the raw read only 17,608 do, partly by chance (`probes/swap_framing_probe.py`). What this does not
settle is whether the dump is wrong or the board routes CPU A19/A21 to other IC14 pins. The answer decides whether
MAME should load the descrambled image or swap lines in its memory map.

**For emulation.** MAME must present the descrambled layout at `0x400000`. Mainline MAME has declared the
descrambled image (`CRC(aa4917ce) SHA1(fef7f192...)`) since mamedev/mame#15878 (merged 2026-08-17), and so does the
`kn7000_mame` overlay. Given the raw read instead, the firmware plays the wrong 64 KB banks for about two thirds of
the styles. The reference copy of the driver kept in the disassembly repository
(`mame_driver/src/mame/matsushita/kn5000.cpp`) is stale on this point: it still declares the raw read's hashes
(`CRC(76d11a5e)`) under the descrambled file name.

## Layout

| image offset      | CPU address       | bytes     | content                                                                   | source                             |
|-------------------|-------------------|-----------|---------------------------------------------------------------------------|------------------------------------|
| 0x000000-0x064FFF | 0x400000-0x464FFF | 413,696   | 202 style records of 2 KB (two 1 KB halves each)                          | `rhythm_data/style_records.s`      |
| 0x065000-0x37FFFF | 0x465000-0x77FFFF | 3,256,320 | 28,400 tracks (3,138,415 B) in 64 KB banks 6..0x37; FF to each bank's end | `rhythm_data/patterns/bank_NN.s`   |
| 0x380000-0x3FFFFF | 0x780000-0x7FFFFF | 524,288   | erased (FF), banks 0x38..0x3F                                             | `rhythm_data/kn5000_rhythm_data.s` |

The FF tails of banks 6..0x37 total 117,905 B. Nothing else is in the chip (`probes/layout_probe.py`). The tracks
are grouped one include file per 64 KB pattern bank, not one per style, because a bank's tracks are shared between
the 2 to 7 styles stored in it.

**The boot signature is just the first record.** `RhythmROM_ValidateHeader` sets `RHYTHM_ROM_BASE` (RAM `0x3277`)
to 0 when the ROM starts with the 12 bytes `00 01 04 05 83 00 01 04 05 83 00 01`, and every address the firmware
forms is `0x400000 + RHYTHM_ROM_BASE + ...`. Those 12 bytes are the start of the section map that opens every record
half. The service test `Test_Rhythm_data_ROM_IC14` checks the first four of them through
`RomTest_RhythmRomSignature`. Its word-sum loop sums the same first 2 MB twice, because `ld xiy, 0x400000` sits
inside the outer loop, so the sum comparison always passes. No checksum is stored in the ROM.

## Selecting a style record

A style is chosen by (bank, program). The panel stores them at `0xFC5B` (bank) and `0xFC5A` (program).

1. `VoiceParam_BankProgramWords` (8 x 128 u16; `SeqTick_ReadControlState` -> `VoiceParam_ClampAndStore`) remaps
   every requested pair.
2. `RhythmROM_BankProgramLocators` (program ROM `0xE45142`, 8 banks x 128 programs x {u16 hi, u16 lo}) gives
   `record = (hi & 0xff) << 16 | lo`. `AccVoice_ComputeChannelIndex` and `AccVoice_LookupWithOffset` read it for
   the playing style, and `Rhythm_LoadCurrentTimeSig` for the panel style.

201 of the 1,024 locators are non-zero, each pointing to a different record. **A zero locator is a valid pointer to
offset 0**, the same trap the IC19 user styles have. The remap sends (0, 89) and (0, 90) to (0, 90), whose locator
is 0, so the record at `0x000000` (`8br86d`, "8Bt Standard") is the style of bank 0, program 90. Every other pair is
remapped to a slot with a non-zero locator. The remap reaches no pair for two records, `8beats` (bank 3, program 24)
and `6beats` (bank 2, program 8): their two halves are identical, and their panel entries are shared with `dxi97p`
and `wzs87e`, so only a reader that skipped the remap could select them. The locator and remap tables are
byte-identical in v5, v6, v7, v8, v9 and v10 (`probes/locator_selection_probe.py`). (Earlier documentation counted
201 records, from the non-zero locators alone.)

**The names the panel shows.** `AccStyle_PanelRhythmTable` (`0xE4935F`, `[program 128][bank 8]` of u16) is
misnamed: it maps each (program, bank) to the panel's (rhythm group, number). `AccStyle_LookupPanelRhythm` reads it,
and `RhythmROM_PatternDisp_Handle90` and `SndParam_ResolveVoiceEntry` pass the result to `AccVoice_DispatchEntry`.
For groups 0..13 that reaches `AccVoice_ComputedCopy`, which copies `AccVoice_RomRecords13[group * 20 + number]`;
`MainGetRhyGrpName` takes the group name from `AccVoice_RomRecords16[group]`. So every record has a panel name:
`8br86d` is STANDARD ROCK 0 "8Bt Standard", `8br27k` is STANDARD ROCK 1 "Simple 8 Beat", and so on for 14 groups.

**Labels.** Record labels name the selection, `Style_B<bank>P<program>_<id>` (for example `Style_B3P090_8br27k`),
where `<id>` is the record's own 8-character id at +0x3DB without its `1n` / `1v` suffix. The display names are in
each record's comment, not in the label, because they repeat across records and contain spaces and quotes. Programs
group related styles: program 90 holds `8br86d`, `8br97g`, `8br17r`, `8br27k`, `8br37p` and `8br75d` in banks 0, 1,
2, 3, 4 and 7.

## Style record (2 KB = two 1 KB halves)

Half 0 carries the id suffix `1n`, half 1 `1v`. Both halves of a record name the same pattern bank (202 of 202).
Half 0 serves section-slot indices 0..19 and half 1 indices 20..39 (`AccStyle_ReadParamOffset`), that is
sections 0-3 and 4-7. The macros are in
[`rhythm_data/rhythm_macros.inc`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/rhythm_data/rhythm_macros.inc),
each with its readers in its comment.

| half offset | size | macro                                | content                                                                                                                                        | readers                                                                                      |
|-------------|------|--------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------|
| +0x000      | 280  | `style_section_map`                  | 7 blocks of 40 B: per block, 4 sections x (4 slot numbers + 0x83), then 4 more picks. Identical in all 404 halves; blocks 5, 6 unread          | `AccStyle_ReadParamOffset`, `AccPart_IncrementIndex` (0x83 = back to the group's first pick) |
| +0x118      | 6x38 | `part_tracks` x 6                    | per part, 19 u16 track slots: offset of the track within the half's pattern bank                                                               | `AccPart_GetParamAddr`, `AccVoice_TableLookup`                                               |
| +0x1fc      | 76   | `style_gap_1fc`                      | FF                                                                                                                                             | constant                                                                                     |
| +0x248      | 8x49 | `part_sound` x 5 + `sound_block_end` | 8 sound blocks of 5 x 7-byte part sound records (DRUM, BASS, ACCOMP1-3: program, bank, forced byte, bank-msb flag, 3 untraced bytes) and 14 FF | `AccVoice_LoadTuningBlock`, `AccTuning_LoadFromROM` (Sound Arranger overrides)               |
| +0x3d0      | 1    | `style_tail` time_sig                | time signature: 7 = 4/4 (374 halves), 6 = 3/4 (26), 11 = 8/4 (2), 9 = 6/4 (2)                                                                  | `AccStyle_ReadVoiceParam`, `Rhythm_LoadCurrentTimeSig`                                       |
| +0x3d1      | 1    | bank                                 | pattern bank 0x06..0x37 of this half's tracks                                                                                                  | `AccStyle_SetupPartAddresses`                                                                |
| +0x3d2      | 8    | v0a..v3b                             | two velocity settings per section; 61,61 / 13,61 / 61,61 / 61,61 in every half                                                                 | `Rhythm_LookupTuningRange`                                                                   |
| +0x3da      | 1    | flag                                 | 1 in every half                                                                                                                                | `AccStyle_ReadVoiceParam` (to a RAM byte nothing reads)                                      |
| +0x3db      | 8    | id                                   | ASCII `<6-char id>1n` / `1v`, for example `8br27k1n`                                                                                           | no reader found                                                                              |
| +0x3e3      | 16   | m0, m1, 0, m3, w0..w3, c0..c3        | small counts, four u16, four small counts                                                                                                      | **no reader found**                                                                          |
| +0x3f3      | 13   | (in `style_tail`)                    | zeros                                                                                                                                          | constant                                                                                     |

### Parts and slots

The six parts are the one-hot `ACC_PART_BIT` values 1, 2, 4, 8, 16, 32, named `Drum`, `Drum2`, `Bass`, `Acc1`,
`Acc2`, `Acc3` in the source (`probes/part_stats_probe.py`):

- parts 0 and 1 have identical slot lists in all 404 halves and play General MIDI drum notes (36, 49 and 38 most
  common); the note check `Rhythm_CheckVelocityThreshold` is skipped for these two parts only;
- part 2 plays notes 23..84, median 36: a bass line;
- parts 3..5 play notes with medians 62..64, mostly `0x91` notes: chord parts.

Linking parts 2..5 to sound records 1..4 (BASS, ACCOMP1-3) is an **inference**: counts and order agree, but no
code path joining them was traced.

Every track in slots 0..15 and 17 is exactly one bar of the half's time signature (2,424 of 2,424 per slot); slots
16 and 18 hold 1 to 8 bars (`probes/slot_bars_probe.py`).

| slots  | selected by                                                                                          | reading                                        |
|--------|------------------------------------------------------------------------------------------------------|------------------------------------------------|
| 0..7   | the section map: pick p -> slot p (`AccPart_LookupBoundVoiceParam`)                                  | the sections' bars                             |
| 8..11  | no reader traced                                                                                     | open                                           |
| 12..15 | `AccVoice_ComputeParamAddr`, by section slot and a pedal-direction bit                               | [inference] fill-ins                           |
| 16..18 | `AccVoice_SelectPartOffset`, `AccSection_StartIntro_SelectMode`, `AccSection_StartEnding_SelectMode` | [inference] 16 / 18 intro / ending, 17 one bar |

Tracks are shared: 46,056 slot references name 28,400 tracks, and every track is referenced
(`probes/track_grammar_probe.py`). Track labels are `Trk_<id>_<N|V>_<part>_S<slot>`, after the first slot that
refers to each.

## Tracks and events

A track is the six-byte header `80 FF FF FF FF 87`, events, then `83 87`. The reader, `AccVoice_ProcessEventLoop`,
starts just after the header. In the header, +1/+2 and +3/+4 are page links (`AccBuf_Advance` follows the word at
+3 when it meets an `0x87`); in the ROM all 28,400 headers are FFFF/FFFF and every `0x87` follows an `0x83`, so no
link is ever taken. The same header frames the 256-byte cells of the user styles in the
[custom-data flash]({{ site.baseurl }}/custom-data-flash/) (IC19) and on disk, where the links are used.

| status    | bytes | source macro                                          | fields                                                   | reader                                                   | count   |
|-----------|-------|-------------------------------------------------------|----------------------------------------------------------|----------------------------------------------------------|---------|
| 0x81      | 1     | `beat [count]`                                        | one beat passes (96 ticks)                               | `AccVoice_HandleBarEndEvent`, `AccTempo_PositionCompare` | 163,146 |
| 0x90      | 6     | `note tick, key, vel, dur_ticks, dur_beats`           | tick in the beat 0..95, note, velocity, duration         | `AccMidi_ParseCommon`                                    | 319,081 |
| 0x91      | 8     | `note2 ... , ext1, ext2`                              | as 0x90, then two bytes whose meaning is not established | `AccMidi_ParseNoteOn`                                    | 95,112  |
| 0xD1-0xD5 | 3     | `cc_mod`, `cc_bend`, `cc_damper`, `cc_pan`, `cc_expr` | tick, value; selector = status & 0x0f                    | `AccMidi_ParseDType`                                     | 24,229  |
| 0x83 0x87 | 2     | `trk_end`                                             | end of the pattern, then the page-end byte               | `AccVoice_HandleMarker83`                                | 28,400  |

The controller counts are `0xD1` 2,540, `0xD2` 10,496, `0xD3` 9,402, `0xD4` 6 and `0xD5` 1,785; unlike the IC19
styles, IC14 uses all five selectors. Their meanings (modulation, pitch bend, damper, pan, expression) come from the
IC19 analysis of the shared performance dispatcher `SeqPerformance_EventDispatch`; that the IC14 path ends in the
same dispatcher is an **inference**.

## Source, size and census

| item       | value                                                                                                                |
|------------|----------------------------------------------------------------------------------------------------------------------|
| build      | `make rebuilt_ROMs/kn5000_rhythm_data_ic14.llvm.rom verify-rhythm-data-raw` (about 9 s to assemble)                  |
| generator  | `scripts/generators/gen_rhythm_data_s.py` wrote the first source; `--check` reports whether it still equals the tree |
| typed text | 14,958,378 B for 3,552,111 B of non-fill data (records + tracks): 4.2x                                               |
| census     | `data_incbin_census.py` row `kn5000-rhythm`: no `.incbin` at all (generic, opaque and generated all 0)               |

The generator refused to write if a single byte was unexplained. The `.s` files are authoritative now.

## Open questions

1. Does the board cross A19/A21, or is the dump wrong? It decides the MAME fix.
2. +0x3E3..+0x3F2 of each half has no reader. A displacement search over the v10 sequencer and UI code, and a
   comparison of the four u16 with per-part sums of track bytes, note counts and beats, found nothing; it may be
   authoring metadata.
3. Slots 8..11: no reader traced.
4. `part_sound` bytes +4..+6 are copied to RAM with the rest; their consumer is not traced.
5. `8beats` and `6beats`: leftovers, or selected by a path that skips `VoiceParam_BankProgramWords`?
6. `AccStyle_PanelRhythmTable` / `AccStyle_LookupPanelRhythm` (and the siblings `AccStyle_PanelRhythmTable_Ext` / `AccStyle_PanelRhythmTable_High`) need names
   that say they map (program, bank) to the panel's (rhythm group, number).

## Related pages

- [Accompaniment Engine]({{ site.baseurl }}/accompaniment-engine/): the player that reads these records
- [Sequencer]({{ site.baseurl }}/sequencer/#pattern-loading-pipeline): the pattern-loading pipeline
- [Custom Data Flash]({{ site.baseurl }}/custom-data-flash/): the user styles in IC19, in the same event language
- [Memory Map]({{ site.baseurl }}/memory-map/): IC14 at `0x400000`
