---
layout: page
title: Sound Categories
permalink: /sound-categories/
---

# Sound Categories

The KN5000 organizes its sounds into 16 categories (plus 2 user memory slots), 40 slots per category. The maps behind them hang off one descriptor at `0xE023A0` in the Main CPU Program ROM.

## Architecture

The sound-selection data in the Main CPU Program ROM is one **descriptor** at `0xE023A0`
(`SoundData_CategoryDesc`) followed by sixteen table pointers at `+0x10..+0x4C`
(`SOUND_DATA_SECTION_PTRS`, `0xE023B0`). The firmware reaches all of it through one RAM
cell: `Param_SignExtendRetu_Block` copies the descriptor pointer to RAM `0xE14E` (v7:
`0xE0B2`), and every reader does `ld xr,(0xe14e)` and reads its own fixed descriptor
offset. No instruction indexes the sixteen pointers by category.

> **Corrected (September 2026, audio lane).** This page used to present the sixteen pointers
> as "one per factory sound category", `SOUND_DATA_PIANO` … `SOUND_DATA_DRUM_KITS`. Those labels
> were given by pairing pointer slot *k* with category name *k*. The readers show that the slots
> are **not** per-category data. They are bank/program ↔ category/slot maps, voice-index maps,
> per-category "last slot" tables and a program-change remap. The labels are kept in the source
> for continuity and are historical. Evidence: the header of `v10/maincpu/audio/sound_data.s`
> (reader addresses for v10/v9/v7), the `CORRECTED` blocks in the fifteen
> `v10/maincpu/audio/sound_data_*.c` files, and `scripts/analysis/sound_data_map_proof.py`.

**The descriptor header:**

| Offset | Value                    | Reader                                                                                                              |
|--------|--------------------------|---------------------------------------------------------------------------------------------------------------------|
| +0x00  | → `SOUND_CATEGORY_NAMES` | `StoreDRAMInit_LoadDRAM` copies category A's 16-char name ("WRONG SW NUMBER!" when A is out of range)               |
| +0x04  | 18                       | the category count (includes MEMORY A/B); a bound in `StoreDRAMInit_LoadDRAM` and `ApplyProgramChangeAs_DoLookupRe` |
| +0x08  | 40                       | **sounds per category**: `FetchOscTableEntry_Prologue` clamps the slot below it and computes `category × 40 + slot` |
| +0x0C  | `0xFFFFFFFF`             | no reader found                                                                                                     |

**The sixteen table slots** (label = the historical category name). A *selection record*
`{+0 category, +1 slot (0..39), +2 voice index (0..127), +3 program, +4 bank, +5 part}` is
passed between the readers. "Mode 1" is when `SndParam_LookupReadOnly(0xC0)` returns 1; in
mode 1 the tables hold 128 sounds in 12 categories, which suggests General MIDI mode, but that
is an inference from the counts.

| Slot          | Label (historical)                                         | What it is                                                                                                                       | Reader (v10)                                               |
|---------------|------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------|
| +0x10 / +0x20 | `SOUND_DATA_PIANO` / `SOUND_DATA_FLUTE`                    | (bank, program) → (category, slot), mode 0 / mode 1                                                                              | `ApplyProgramChangeAs_LoadDRAM2`                           |
| +0x14 / +0x24 | `SOUND_DATA_GUITAR` / `SOUND_DATA_SAX_REED`                | (category, slot) grid → (program, bank), mode 0 / 1 (18 × 40 × 2 = 1,440 B)                                                      | `FetchOscTableEntry_Prologue`                              |
| +0x18 / +0x28 | `SOUND_DATA_STRINGS_VOCAL` / `SOUND_DATA_MALLET_ORCH_PERC` | (bank, program) → voice index, mode 0 / 1                                                                                        | `ApplyProgramChange_LoadDRAM`                              |
| +0x1C / +0x2C | `SOUND_DATA_BRASS_PTRS` / `SOUND_DATA_WORLD_PERC`          | voice index → (program, bank): 128 pointers to `{program, bank, 0xFF}` records; nothing found indexes +0x2C                      | `SndParam_LookupOscEnvelope`                               |
| +0x30         | `SOUND_DATA_ORGAN_ACCORDION`                               | **GS drum-set map**: drum-set program p -> KN5000 kit (0xF0+k, 0): Standard, Room, Power, Electric, Jazz, Brush, Orchestral, SFX | `SndParam_LookupOscEnvelope`, `SndParam_LookupAndDispatch` |
| +0x34         | `SOUND_DATA_ORCHESTRAL_PAD`                                | **SMF-import note shift** per GM voice (0, +12, -12), added to note numbers on channels other than 10                            | `SndParam_LookupByPartAndNote`                             |
| +0x38         | `SOUND_DATA_SYNTH`                                         | **program-change remap**: a received `Cn p` is retransmitted as `Bn 00`, `Bn 20`, `Cn` from entry *p*                            | `SndParam_LookupFromPointerTable`                          |
| +0x3C         | `SOUND_DATA_BASS`                                          | per-category **last slot index**, mode 0, ordinary parts (18 bytes, 0xFF = not offered); the values give 368 sounds              | `CharMap_ActivePreamb_Prologue`                            |
| +0x40         | `SOUND_DATA_DIGITAL_DRAWBAR`                               | the same for part 15 (only category 15, 16 drum kits)                                                                            | same                                                       |
| +0x44         | `SOUND_DATA_ACCORDION_REG`                                 | the same for part 20                                                                                                             | same                                                       |
| +0x48         | `SOUND_DATA_GM_SPECIAL`                                    | the same in mode 1, ordinary parts (12 categories, 128 sounds)                                                                   | same                                                       |
| +0x4C         | `SOUND_DATA_DRUM_KITS`                                     | the same in mode 1 for part 15 (8 kits); only its first 18 bytes are this table                                                  | same                                                       |

**The voice index** of +0x18 / +0x1C / +0x30 / +0x34 is the GM program number (0-based): +0x1C resolves voice v
to the KN5000 tone for GM program v+1 (0 Piano, 8 Celesta, 32 Acoustic Bass; see the GM voice map in the
catalogue below).

**Slots +0x30 and +0x34** (traced 2026-10-31, issue kn5000-8dy; disassembly
`notes/open4-kn5000-b/midi/README.md`, probe `notes/open4-kn5000-b/midi/probes/sound_desc_slots_30_34.py`):

- **+0x30 is a GS drum-set map.** The probe groups its 128 two-byte entries: indices 0-7, 25 and 64-127 -> `F0 00`;
  8-15 -> `F3`; 16-23 -> `F7`; 24 and 26-31 -> `F2`; 32-39 -> `F1`; 40-47 -> `F5`; 48-55 -> `FC`; 56-63 -> `FD`
  (identical in v10, v9 and v7). That is the GS drum-set numbering (Standard 1, Room 9, Power 17, Electronic 25,
  TR-808 26, Jazz 33, Brush 41, Orchestra 49, SFX 57), and the targets resolve to Standard, Room, Power, Electric,
  Jazz, Brush, Orchestral and Sound Effect Kit. `SndParam_LookupAndDispatch` uses it for a program change in bank
  0x78 (the GM2 rhythm bank, 120); `SndParam_LookupOscEnvelope` uses it instead of +0x1C for part 15 and for sounds
  >= 0xF0. The kits are programs 0xF0+k in bank 0, which `SndParam_ApplyMaskClamp` turns into program k in bank 0x40
  (bank 1 -> 0x41).
- **+0x34 is a note shift for SMF import.** Its only reader, `SndParam_LookupByPartAndNote`, is called by
  `MidiNoteOn_NonDrumLookupA` / `B` (`sequencer/smf_tonegen_core.s`, the SMF loader: it scales delta times to 96
  ticks per beat), which add the byte to the note number of each note-on on channels other than 10. +12 goes to the
  basses, Bowed Bass, Bright Trombone, Orchestral Tuba, Bigband Brass, Bassoon, Bass & Lead, Agogo, Breath Noise and
  Rock Harmonics; -12 to Celesta, Glockenspiel, Music Box, Xylophone, Tubular Bells, Full Drawbars, Perc Organ,
  Piccolo, Whistle, Tinkle Bell and Wood Block. [Inference] an octave correction between GM's written pitch and the
  KN5000 tones.

**The pairs are exact inverses.** `sound_data_map_proof.py` checks, on all three dumps:
the +0x14 grid mapped through the +0x10 bank map returns all 368 populated cells to
themselves; +0x24 through +0x20 does so for 136 of 136; the +0x1C list through +0x18 for 128
of 128; and +0x2C through +0x28 for 128 of 128. The +0x3C table sums to 368 sounds and the
+0x48 table to 128, the same totals counted a different way.

**The category names** (18 × 16 characters at `SOUND_CATEGORY_NAMES`, `0xE023F0`) are real:
PIANO, GUITAR, STRINGS & VOCAL, BRASS, FLUTE, SAX & REED, MALLET&ORCH PERC, WORLD PERC,
ORGAN&ACCORDION, ORCHESTRAL PAD, SYNTH, BASS, DIGITAL DRAWBAR, ACCORDION REG., GM SPECIAL,
DRUM KITS, MEMORY A, MEMORY B. A category's sounds are the 40 slots of its row in the
+0x14 grid (+0x24 in mode 1).

The older per-"category" format descriptions (a "sub-category index" header, "2-byte voice
records `{voice_id, variation}`", "organ registration sets") had no reader behind them. The
`CORRECTED` blocks in the C files mark which of their older comment lines are false.

## Sound Selection Flow

When a user selects a sound:

1. **UI event** — Sound button press generates a control panel event
2. **Category/slot → program** — `FetchOscTableEntry_Prologue` reads the descriptor's `+0x14` grid (`+0x24` in mode 1) at `category × 40 + slot` to get the sound's `{program, bank}`
3. **Voice index** — `ApplyProgramChange_LoadDRAM` maps (bank, program) to a voice index through `+0x18` (`+0x28`); the reverse maps (`+0x10`/`+0x20`) take a received program change back to a category and slot
4. **Program change** — `SndPart_SendProgramChange` sends the record `{5, 0xC0, part, program, bank, effect}` to the sub CPU after `SndParam_ApplyMaskClamp` has turned panel program numbers >= 0x80 into the tone database's bank selectors (0x70 drawbars, 0x40/0x41 drum kits, 0x10/0x15/0x50/0x55 RAM memories). See "The C0 sender" below.
5. **Inter-CPU transfer** — Command sent via `sendCOMM` → `InterCPU_Send_Data_Block` → latch at 0x140000 (0x120000 on the sub CPU's bus)
6. **Sub CPU processing** — `Audio_CmdHandler_00_1F` writes to ring buffer → `MIDI_Dispatch` routes to `Voice_ProgChange`
7. **Voice activation** — `Voice_ProgChange` updates the part's 287-byte record (`Part_Record_Base`, `0x041368` + part × 0x11F)

### The C0 sender

Traced 2026-10-31 (issue kn5000-8dy). `SndPart_SendProgramChange` (named `SendChannelPressure_Prologue` before
then): WA = part, BC = program, DE = bank, a pushed word = the part's DIGITAL EFFECT switch. It runs
`SndParam_ApplyMaskClamp` and sends `{5, 0xC0, part, program, bank, effect (0 / 0x7F)}` with
`MIDI_SendCmdPacket`. Its only caller is `Song_SendPartDataBlocks`, which flushes the pending tables `0xCFD0`
(program) / `0xD010` (bank) that `SndPart_SetParam` fills for Lsw 0x000 / 0x020. `SndParam_Init` sends the one
literal C0 record (part 0x19, program 0, bank 0x40).

`SndParam_ApplyMaskClamp` (mode 0, not for bank 0x78):

| program       | bank  | becomes                                                                                                                   |
|---------------|-------|---------------------------------------------------------------------------------------------------------------------------|
| < 0x80        | any   | bank & 7                                                                                                                  |
| >= 0x80       | 7     | program & 0x7F in bank 0x70 (the two drawbar presets)                                                                     |
| 0x80-0xEF     | 0 / 5 | bank 0x10 / 0x15 (RAM user banks; the panel's MEMORY A and B are programs 0x80-0xA7 in bank 0, entries 0-39 of bank 0x10) |
| 0xF0-0xFF     | 0 / 1 | program & 0x0F in bank 0x40 / 0x41 (drum kits)                                                                            |
| 0xF0-0xFF     | 6 / 5 | bank 0x50 / 0x55 (user kits)                                                                                              |
| anything else |       | program 0, bank 0                                                                                                         |

These are exactly the selectors `ToneDB_Find_PatchRecord` admits (<= 7, 0x40, 0x41, 0x70) or diverts to RAM
(0x10, 0x15, 0x50, 0x55).

## Instrument Patch Catalog

The panel's sound list, read from the firmware's own tables: category/slot grid -> program/bank ->
`SndParam_ApplyMaskClamp` -> tone record. Generated by `scripts/generators/gen_sound_patch_catalogue.py`
(disassembly repository; its committed output is `notes/open4-kn5000-b/midi/sound-patch-catalogue.md`, and
`--check FILE` compares); slot numbers are as on the panel. Traced 2026-10-31, issue kn5000-cox.

The generator walks the firmware's own path: the descriptor's category/slot grid (+0x14, +0x24 in mode 1), the
last-slot tables (+0x3C/+0x40/+0x44, +0x48/+0x4C), `SndParam_ApplyMaskClamp`, then the sub CPU's
`ToneDB_Find_PatchRecord` over the table-data tone database (`ToneDB_BankMap_Main` -> `ToneDB_ToneNumBanks_Main`
-> `ToneDB_ToneOffsetTable` -> record name; see [Tone Database]({{ site.baseurl }}/tone-database/)).

| section                     | sounds | from                           |
|-----------------------------|--------|--------------------------------|
| mode 0, ordinary parts      | 368    | +0x14 grid, +0x3C last slots   |
| mode 0, drum part (part 15) | 16     | +0x14 row 15, +0x40            |
| mode 0, part 20             | 16     | +0x14 row 15, +0x44            |
| mode 1, ordinary parts      | 128    | +0x24 grid, +0x48              |
| mode 1, drum part           | 8      | +0x24 row 15, +0x4C, via +0x30 |
| GM voice map                | 128    | +0x1C, +0x34                   |

Every cell resolves to a named ROM tone except MEMORY A/B (programs 0x80-0xA7 of bank 0, which become entries
0-39 of RAM user bank 0x10) and the user drum kit (bank 0x50), as the firmware's own bank selectors say. The 368
total agrees with `sound_data_map_proof.py`. Not covered: the per-sound sample mappings, envelopes and filters are
fields of the tone records (layout on [Tone Database]({{ site.baseurl }}/tone-database/)); a per-tone parameter
dump is not part of this catalogue. The mode-1 drum rows apply the mode-0 rewrite to the +0x30 result, which is an
inference (the mode-1 send of a bank 0x78 pair is not traced).

### Mode 0, ordinary parts

368 sounds.  Grid D+0x14, last-slot table D+0x3C.

#### PIANO (category 0, 20 sounds)

| slot | program    | bank | sent (program / bank) | tone # | tone record | tone name        |
|------|------------|------|-----------------------|--------|-------------|------------------|
| 1    | 0 (0x00)   | 0x00 | 0 / 0x00              | 0      | 0x8324D4    | Piano            |
| 2    | 1 (0x01)   | 0x00 | 1 / 0x00              | 1      | 0x8325DC    | Bright Piano     |
| 3    | 0 (0x00)   | 0x01 | 0 / 0x01              | 3      | 0x8327EC    | Piano 1 Octave   |
| 4    | 3 (0x03)   | 0x02 | 3 / 0x02              | 5      | 0x8329FC    | Rock Piano       |
| 5    | 3 (0x03)   | 0x00 | 3 / 0x00              | 7      | 0x832BBB    | Electric Grand   |
| 6    | 5 (0x05)   | 0x00 | 5 / 0x00              | 9      | 0x832E1C    | E.Piano 1        |
| 7    | 4 (0x04)   | 0x02 | 4 / 0x02              | 11     | 0x832F8A    | Suitcase E.P.    |
| 8    | 6 (0x06)   | 0x00 | 6 / 0x00              | 14     | 0x833251    | Modern E.P.1     |
| 9    | 16 (0x10)  | 0x00 | 16 / 0x00             | 16     | 0x833410    | Harpsichord      |
| 10   | 17 (0x11)  | 0x00 | 17 / 0x00             | 18     | 0x833713    | Clavi            |
| 11   | 2 (0x02)   | 0x00 | 2 / 0x00              | 2      | 0x8326E4    | Mellow Piano     |
| 12   | 2 (0x02)   | 0x01 | 2 / 0x01              | 4      | 0x8328F4    | Piano 2 Octave   |
| 13   | 1 (0x01)   | 0x01 | 1 / 0x01              | 6      | 0x832AB3    | Honky-Tonk Piano |
| 14   | 0 (0x00)   | 0x02 | 0 / 0x02              | 8      | 0x832CC3    | Midi Grand       |
| 15   | 5 (0x05)   | 0x02 | 5 / 0x02              | 10     | 0x832ED3    | E.Piano 2        |
| 16   | 4 (0x04)   | 0x04 | 4 / 0x04              | 12     | 0x833041    | Tremolo E.Piano  |
| 17   | 4 (0x04)   | 0x05 | 4 / 0x05              | 13     | 0x833149    | Wurly E.Piano    |
| 18   | 4 (0x04)   | 0x00 | 4 / 0x00              | 15     | 0x833308    | Modern E.P.2     |
| 19   | 18 (0x12)  | 0x00 | 18 / 0x00             | 17     | 0x833569    | Cembalo          |
| 20   | 115 (0x73) | 0x00 | 115 / 0x00            | 19     | 0x83381B    | Synth Clavi      |

#### GUITAR (category 1, 20 sounds)

| slot | program   | bank | sent (program / bank) | tone # | tone record | tone name        |
|------|-----------|------|-----------------------|--------|-------------|------------------|
| 1    | 20 (0x14) | 0x00 | 20 / 0x00             | 40     | 0x8349F7    | Classical Guitar |
| 2    | 20 (0x14) | 0x01 | 20 / 0x01             | 41     | 0x834AAE    | Spanish Guitar   |
| 3    | 22 (0x16) | 0x00 | 22 / 0x00             | 45     | 0x834DDB    | Folk Guitar      |
| 4    | 25 (0x19) | 0x00 | 25 / 0x00             | 48     | 0x835144    | Jazz Guitar 1    |
| 5    | 31 (0x1F) | 0x01 | 31 / 0x01             | 58     | 0x835A50    | Country Guitar   |
| 6    | 26 (0x1A) | 0x00 | 26 / 0x00             | 50     | 0x8352B2    | Bright Solid Gtr |
| 7    | 26 (0x1A) | 0x01 | 26 / 0x01             | 52     | 0x835471    | Clean Solid Gtr  |
| 8    | 29 (0x1D) | 0x00 | 29 / 0x00             | 54     | 0x835630    | Mute Guitar      |
| 9    | 30 (0x1E) | 0x00 | 30 / 0x00             | 56     | 0x835891    | Distortion Gtr   |
| 10   | 27 (0x1B) | 0x02 | 27 / 0x02             | 57     | 0x835948    | Overdrive Guitar |
| 11   | 21 (0x15) | 0x00 | 21 / 0x00             | 42     | 0x834B65    | Jazz Ac.Guitar   |
| 12   | 20 (0x14) | 0x04 | 20 / 0x04             | 43     | 0x834C1C    | Bossa Guitar     |
| 13   | 27 (0x1B) | 0x04 | 27 / 0x04             | 44     | 0x834CD3    | Guitar Harmonics |
| 14   | 23 (0x17) | 0x00 | 23 / 0x00             | 46     | 0x834EE3    | 12 String Guitar |
| 15   | 25 (0x19) | 0x02 | 25 / 0x02             | 47     | 0x83508D    | ElectroAc.Guitar |
| 16   | 24 (0x18) | 0x00 | 24 / 0x00             | 49     | 0x8351FB    | Jazz Guitar 2    |
| 17   | 28 (0x1C) | 0x00 | 28 / 0x00             | 51     | 0x8353BA    | Mellow Solid Gtr |
| 18   | 28 (0x1C) | 0x02 | 28 / 0x02             | 53     | 0x835579    | Fusion Solid Gtr |
| 19   | 29 (0x1D) | 0x03 | 29 / 0x03             | 55     | 0x835789    | Funk Mute Guitar |
| 20   | 31 (0x1F) | 0x03 | 31 / 0x03             | 59     | 0x835B07    | Nashville Steel  |

#### STRINGS & VOCAL (category 2, 30 sounds)

| slot | program    | bank | sent (program / bank) | tone # | tone record | tone name        |
|------|------------|------|-----------------------|--------|-------------|------------------|
| 1    | 100 (0x64) | 0x03 | 100 / 0x03            | 80     | 0x836DD6    | SymphonicStrings |
| 2    | 102 (0x66) | 0x04 | 102 / 0x04            | 84     | 0x837154    | Violin Ensemble  |
| 3    | 102 (0x66) | 0x05 | 102 / 0x05            | 85     | 0x83720B    | Viola Ensemble   |
| 4    | 102 (0x66) | 0x06 | 102 / 0x06            | 86     | 0x8372C2    | Cello Ensemble   |
| 5    | 102 (0x66) | 0x07 | 102 / 0x07            | 87     | 0x837379    | Bass Ensemble    |
| 6    | 101 (0x65) | 0x04 | 101 / 0x04            | 81     | 0x836EDE    | Concert Strings  |
| 7    | 99 (0x63)  | 0x00 | 99 / 0x00             | 92     | 0x8377FF    | Pizzicato Str.   |
| 8    | 104 (0x68) | 0x03 | 104 / 0x03            | 101    | 0x838003    | Vocal Ah         |
| 9    | 104 (0x68) | 0x04 | 104 / 0x04            | 103    | 0x838171    | Stereo Vocal Ah  |
| 10   | 104 (0x68) | 0x02 | 104 / 0x02            | 104    | 0x838279    | Vocal Ooh        |
| 11   | 100 (0x64) | 0x00 | 100 / 0x00            | 82     | 0x836FE6    | ClassicalStrings |
| 12   | 96 (0x60)  | 0x00 | 96 / 0x00             | 95     | 0x837B68    | Violin           |
| 13   | 97 (0x61)  | 0x02 | 97 / 0x02             | 98     | 0x837DDE    | Viola            |
| 14   | 97 (0x61)  | 0x00 | 97 / 0x00             | 99     | 0x837E95    | Cello            |
| 15   | 98 (0x62)  | 0x00 | 98 / 0x00             | 100    | 0x837F4C    | Bowed Bass       |
| 16   | 100 (0x64) | 0x04 | 100 / 0x04            | 83     | 0x83709D    | Marcato Strings  |
| 17   | 96 (0x60)  | 0x01 | 96 / 0x01             | 96     | 0x837C1F    | Jazz Violin      |
| 18   | 96 (0x60)  | 0x02 | 96 / 0x02             | 97     | 0x837CD6    | Country Fiddle   |
| 19   | 109 (0x6D) | 0x00 | 109 / 0x00            | 108    | 0x838648    | Vocal Doo        |
| 20   | 109 (0x6D) | 0x02 | 109 / 0x02            | 109    | 0x838750    | Vocal Daa        |
| 21   | 101 (0x65) | 0x00 | 101 / 0x00            | 88     | 0x837430    | Slow Strings     |
| 22   | 102 (0x66) | 0x00 | 102 / 0x00            | 89     | 0x8374E7    | Octave Strings   |
| 23   | 98 (0x62)  | 0x01 | 98 / 0x01             | 90     | 0x8375EF    | Bass Strings     |
| 24   | 103 (0x67) | 0x00 | 103 / 0x00            | 93     | 0x837907    | Synth Strings 1  |
| 25   | 103 (0x67) | 0x01 | 103 / 0x01            | 94     | 0x837A60    | Synth Strings 2  |
| 26   | 100 (0x64) | 0x02 | 100 / 0x02            | 91     | 0x8376F7    | Tremolo Strings  |
| 27   | 104 (0x68) | 0x00 | 104 / 0x00            | 102    | 0x8380BA    | Pop Vocal Ah     |
| 28   | 105 (0x69) | 0x00 | 105 / 0x00            | 105    | 0x838330    | Humming          |
| 29   | 107 (0x6B) | 0x00 | 107 / 0x00            | 106    | 0x838438    | Synth Vocal      |
| 30   | 106 (0x6A) | 0x01 | 106 / 0x01            | 107    | 0x838540    | Air Vox          |

#### BRASS (category 3, 20 sounds)

| slot | program   | bank | sent (program / bank) | tone # | tone record | tone name       |
|------|-----------|------|-----------------------|--------|-------------|-----------------|
| 1    | 56 (0x38) | 0x00 | 56 / 0x00             | 150    | 0x83B606    | Bigband Brass   |
| 2    | 57 (0x39) | 0x04 | 57 / 0x04             | 151    | 0x83B6BD    | Marching Brass  |
| 3    | 56 (0x38) | 0x03 | 56 / 0x03             | 152    | 0x83B774    | Brass & Synth   |
| 4    | 60 (0x3C) | 0x00 | 60 / 0x00             | 155    | 0x83BB7F    | Synth Brass 1   |
| 5    | 48 (0x30) | 0x00 | 48 / 0x00             | 157    | 0x83BD8F    | Trumpet         |
| 6    | 50 (0x32) | 0x00 | 50 / 0x00             | 160    | 0x83BFB4    | Harmon Mute Tpt |
| 7    | 51 (0x33) | 0x00 | 51 / 0x00             | 162    | 0x83C122    | Flugel Horn     |
| 8    | 52 (0x34) | 0x00 | 52 / 0x00             | 163    | 0x83C1D9    | Bright Trombone |
| 9    | 54 (0x36) | 0x00 | 54 / 0x00             | 166    | 0x83C3FE    | Closed Fr.Horn  |
| 10   | 54 (0x36) | 0x01 | 54 / 0x01             | 167    | 0x83C4B5    | Open Fr.Horn    |
| 11   | 56 (0x38) | 0x01 | 56 / 0x01             | 153    | 0x83B8CD    | Octave Brass    |
| 12   | 59 (0x3B) | 0x00 | 59 / 0x00             | 154    | 0x83BA26    | Octave Horns    |
| 13   | 58 (0x3A) | 0x04 | 58 / 0x04             | 169    | 0x83C674    | Brass Fall      |
| 14   | 63 (0x3F) | 0x03 | 63 / 0x03             | 156    | 0x83BC87    | Synth Brass 2   |
| 15   | 48 (0x30) | 0x04 | 48 / 0x04             | 158    | 0x83BE46    | Solo Trumpet    |
| 16   | 48 (0x30) | 0x02 | 48 / 0x02             | 159    | 0x83BEFD    | Orchest.Trumpet |
| 17   | 50 (0x32) | 0x01 | 50 / 0x01             | 161    | 0x83C06B    | StraightMuteTpt |
| 18   | 53 (0x35) | 0x00 | 53 / 0x00             | 164    | 0x83C290    | Mellow Trombone |
| 19   | 52 (0x34) | 0x03 | 52 / 0x03             | 165    | 0x83C347    | CupMuteTrombone |
| 20   | 55 (0x37) | 0x01 | 55 / 0x01             | 168    | 0x83C56C    | Marching Tuba   |

#### FLUTE (category 4, 20 sounds)

| slot | program    | bank | sent (program / bank) | tone # | tone record | tone name        |
|------|------------|------|-----------------------|--------|-------------|------------------|
| 1    | 64 (0x40)  | 0x00 | 64 / 0x00             | 190    | 0x83DB29    | Piccolo          |
| 2    | 65 (0x41)  | 0x00 | 65 / 0x00             | 191    | 0x83DBE0    | Jazz Flute       |
| 3    | 65 (0x41)  | 0x01 | 65 / 0x01             | 192    | 0x83DC97    | Classical Flute  |
| 4    | 64 (0x40)  | 0x01 | 64 / 0x01             | 193    | 0x83DD9F    | Alto Flute       |
| 5    | 72 (0x48)  | 0x00 | 72 / 0x00             | 196    | 0x83E0B7    | Pan Flute 1      |
| 6    | 74 (0x4A)  | 0x00 | 74 / 0x00             | 199    | 0x83E3CF    | Recorder         |
| 7    | 74 (0x4A)  | 0x01 | 74 / 0x01             | 200    | 0x83E486    | Ocarina          |
| 8    | 111 (0x6F) | 0x00 | 111 / 0x00            | 202    | 0x83E696    | Whistle          |
| 9    | 75 (0x4B)  | 0x00 | 75 / 0x00             | 203    | 0x83E74D    | Shakuhachi       |
| 10   | 72 (0x48)  | 0x04 | 72 / 0x04             | 207    | 0x83EBBE    | Penny Whistle    |
| 11   | 65 (0x41)  | 0x04 | 65 / 0x04             | 209    | 0x83EE1F    | Chiff Flute      |
| 12   | 75 (0x4B)  | 0x05 | 75 / 0x05             | 195    | 0x83DFAF    | Flutter Flute    |
| 13   | 64 (0x40)  | 0x03 | 64 / 0x03             | 194    | 0x83DEA7    | Alto Ensemble    |
| 14   | 72 (0x48)  | 0x01 | 72 / 0x01             | 197    | 0x83E16E    | Pan Flute 2      |
| 15   | 72 (0x48)  | 0x03 | 72 / 0x03             | 198    | 0x83E276    | Synth Calliope   |
| 16   | 72 (0x48)  | 0x02 | 72 / 0x02             | 201    | 0x83E53D    | Blown Bottle     |
| 17   | 75 (0x4B)  | 0x01 | 75 / 0x01             | 204    | 0x83E804    | Quena            |
| 18   | 73 (0x49)  | 0x02 | 73 / 0x02             | 205    | 0x83E95D    | Ney              |
| 19   | 111 (0x6F) | 0x02 | 111 / 0x02            | 208    | 0x83EC75    | Marching Whistle |
| 20   | 112 (0x70) | 0x02 | 112 / 0x02            | 206    | 0x83EA65    | Chopper Flute    |

#### SAX & REED (category 5, 20 sounds)

| slot | program   | bank | sent (program / bank) | tone # | tone record | tone name        |
|------|-----------|------|-----------------------|--------|-------------|------------------|
| 1    | 76 (0x4C) | 0x00 | 76 / 0x00             | 170    | 0x83C72B    | Soprano Sax      |
| 2    | 77 (0x4D) | 0x00 | 77 / 0x00             | 171    | 0x83C833    | Alto Sax         |
| 3    | 77 (0x4D) | 0x01 | 77 / 0x01             | 172    | 0x83C93B    | Mellow Alto Sax  |
| 4    | 78 (0x4E) | 0x03 | 78 / 0x03             | 173    | 0x83CA43    | Tenor Sax 1      |
| 5    | 78 (0x4E) | 0x01 | 78 / 0x01             | 175    | 0x83CC02    | Breathy Tenor    |
| 6    | 79 (0x4F) | 0x01 | 79 / 0x01             | 177    | 0x83CE63    | Baritone Sax     |
| 7    | 68 (0x44) | 0x00 | 68 / 0x00             | 180    | 0x83D2BF    | Jazz Clarinet 1  |
| 8    | 66 (0x42) | 0x00 | 66 / 0x00             | 185    | 0x83D796    | Oboe             |
| 9    | 83 (0x53) | 0x00 | 83 / 0x00             | 188    | 0x83D9BB    | Harmonica        |
| 10   | 83 (0x53) | 0x01 | 83 / 0x01             | 189    | 0x83DA72    | Blues Harmonica  |
| 11   | 78 (0x4E) | 0x04 | 78 / 0x04             | 174    | 0x83CB4B    | Tenor Sax 2      |
| 12   | 79 (0x4F) | 0x00 | 79 / 0x00             | 176    | 0x83CD5B    | Rock Tenor Sax   |
| 13   | 78 (0x4E) | 0x02 | 78 / 0x02             | 178    | 0x83CFBC    | Distortion Sax   |
| 14   | 79 (0x4F) | 0x02 | 79 / 0x02             | 179    | 0x83D115    | Unison Saxes     |
| 15   | 68 (0x44) | 0x02 | 68 / 0x02             | 181    | 0x83D3C7    | Jazz Clarinet 2  |
| 16   | 68 (0x44) | 0x01 | 68 / 0x01             | 182    | 0x83D520    | Mellow Clarinet  |
| 17   | 69 (0x45) | 0x00 | 69 / 0x00             | 183    | 0x83D628    | Classic Clarinet |
| 18   | 69 (0x45) | 0x01 | 69 / 0x01             | 184    | 0x83D6DF    | Bass Clarinet    |
| 19   | 67 (0x43) | 0x00 | 67 / 0x00             | 186    | 0x83D84D    | English Horn     |
| 20   | 70 (0x46) | 0x00 | 70 / 0x00             | 187    | 0x83D904    | Bassoon          |

#### MALLET&ORCH PERC (category 6, 20 sounds)

| slot | program    | bank | sent (program / bank) | tone # | tone record | tone name        |
|------|------------|------|-----------------------|--------|-------------|------------------|
| 1    | 9 (0x09)   | 0x00 | 9 / 0x00              | 20     | 0x8338D2    | Glockenspiel     |
| 2    | 8 (0x08)   | 0x00 | 8 / 0x00              | 21     | 0x8339DA    | Vibraphone       |
| 3    | 10 (0x0A)  | 0x00 | 10 / 0x00             | 23     | 0x833BEA    | Marimba          |
| 4    | 11 (0x0B)  | 0x00 | 11 / 0x00             | 24     | 0x833CA1    | Xylophone        |
| 5    | 12 (0x0C)  | 0x00 | 12 / 0x00             | 25     | 0x833D58    | Celesta          |
| 6    | 14 (0x0E)  | 0x00 | 14 / 0x00             | 26     | 0x833E0F    | Tubular Bells    |
| 7    | 126 (0x7E) | 0x01 | 126 / 0x01            | 39     | 0x834940    | Gong             |
| 8    | 32 (0x20)  | 0x00 | 32 / 0x00             | 33     | 0x834454    | Harp             |
| 9    | 126 (0x7E) | 0x00 | 126 / 0x00            | 37     | 0x834781    | Timpani          |
| 10   | 127 (0x7F) | 0x01 | 127 / 0x01            | 34     | 0x83455C    | Orchestra Hit    |
| 11   | 8 (0x08)   | 0x04 | 8 / 0x04              | 22     | 0x833AE2    | Vibes&JazzGuitar |
| 12   | 13 (0x0D)  | 0x00 | 13 / 0x00             | 29     | 0x834085    | Bottle Marimba   |
| 13   | 113 (0x71) | 0x00 | 113 / 0x00            | 30     | 0x83413C    | African Mallet   |
| 14   | 11 (0x0B)  | 0x01 | 11 / 0x01             | 31     | 0x834244    | Caribbean Mallet |
| 15   | 7 (0x07)   | 0x00 | 7 / 0x00              | 32     | 0x83439D    | Music Box        |
| 16   | 14 (0x0E)  | 0x04 | 14 / 0x04             | 27     | 0x833EC6    | Carillon         |
| 17   | 14 (0x0E)  | 0x01 | 14 / 0x01             | 28     | 0x833F7D    | Wind Chime       |
| 18   | 125 (0x7D) | 0x00 | 125 / 0x00            | 38     | 0x834838    | Sleigh Bell      |
| 19   | 127 (0x7F) | 0x04 | 127 / 0x04            | 35     | 0x834613    | Dance Hit 1      |
| 20   | 127 (0x7F) | 0x05 | 127 / 0x05            | 36     | 0x8346CA    | Dance Hit 2      |

#### WORLD PERC (category 7, 20 sounds)

| slot | program    | bank | sent (program / bank) | tone # | tone record | tone name        |
|------|------------|------|-----------------------|--------|-------------|------------------|
| 1    | 31 (0x1F)  | 0x00 | 31 / 0x00             | 62     | 0x835D2C    | Hawaiian Guitar1 |
| 2    | 31 (0x1F)  | 0x04 | 31 / 0x04             | 63     | 0x835DE3    | Hawaiian Guitar2 |
| 3    | 33 (0x21)  | 0x00 | 33 / 0x00             | 60     | 0x835BBE    | Banjo            |
| 4    | 35 (0x23)  | 0x04 | 35 / 0x04             | 78     | 0x836B75    | Bouzouki         |
| 5    | 15 (0x0F)  | 0x00 | 15 / 0x00             | 69     | 0x8362CF    | Steel Drum       |
| 6    | 39 (0x27)  | 0x00 | 39 / 0x00             | 66     | 0x836008    | Kalimba          |
| 7    | 13 (0x0D)  | 0x04 | 13 / 0x04             | 70     | 0x8363D7    | Bonang           |
| 8    | 13 (0x0D)  | 0x05 | 13 / 0x05             | 71     | 0x83648E    | Sarrons          |
| 9    | 13 (0x0D)  | 0x06 | 13 / 0x06             | 72     | 0x836545    | Kenong           |
| 10   | 13 (0x0D)  | 0x07 | 13 / 0x07             | 73     | 0x8365FC    | Slentem          |
| 11   | 35 (0x23)  | 0x00 | 35 / 0x00             | 61     | 0x835C75    | Mandolin         |
| 12   | 37 (0x25)  | 0x00 | 37 / 0x00             | 64     | 0x835E9A    | Koto             |
| 13   | 36 (0x24)  | 0x00 | 36 / 0x00             | 65     | 0x835F51    | Shamisen         |
| 14   | 38 (0x26)  | 0x00 | 38 / 0x00             | 68     | 0x836218    | Sitar            |
| 15   | 38 (0x26)  | 0x01 | 38 / 0x01             | 74     | 0x8366B3    | Dulcimer         |
| 16   | 38 (0x26)  | 0x02 | 38 / 0x02             | 75     | 0x8367BB    | Kanun            |
| 17   | 38 (0x26)  | 0x03 | 38 / 0x03             | 76     | 0x836914    | Cumbus           |
| 18   | 34 (0x22)  | 0x00 | 34 / 0x00             | 77     | 0x836A6D    | Ukulele          |
| 19   | 39 (0x27)  | 0x01 | 39 / 0x01             | 67     | 0x836110    | Metal Kalimba    |
| 20   | 123 (0x7B) | 0x04 | 123 / 0x04            | 79     | 0x836CCE    | Talking Drum     |

#### ORGAN&ACCORDION (category 8, 20 sounds)

| slot | program   | bank | sent (program / bank) | tone # | tone record | tone name        |
|------|-----------|------|-----------------------|--------|-------------|------------------|
| 1    | 88 (0x58) | 0x00 | 88 / 0x00             | 130    | 0x839FD1    | Perc Organ       |
| 2    | 89 (0x59) | 0x00 | 89 / 0x00             | 131    | 0x83A088    | Full Drawbars    |
| 3    | 85 (0x55) | 0x00 | 85 / 0x00             | 139    | 0x83A919    | Chapel Organ     |
| 4    | 84 (0x54) | 0x00 | 84 / 0x00             | 140    | 0x83AA72    | Full Organ       |
| 5    | 86 (0x56) | 0x04 | 86 / 0x04             | 141    | 0x83ABCB    | Cathedral Organ  |
| 6    | 93 (0x5D) | 0x00 | 93 / 0x00             | 132    | 0x83A13F    | Jazz Drawbars    |
| 7    | 91 (0x5B) | 0x00 | 91 / 0x00             | 133    | 0x83A1F6    | 16' & 1'         |
| 8    | 80 (0x50) | 0x00 | 80 / 0x00             | 145    | 0x83B12F    | Bright Accordion |
| 9    | 82 (0x52) | 0x00 | 82 / 0x00             | 147    | 0x83B29D    | Musette          |
| 10   | 82 (0x52) | 0x04 | 82 / 0x04             | 149    | 0x83B45C    | Folk Accordion   |
| 11   | 91 (0x5B) | 0x02 | 91 / 0x02             | 134    | 0x83A2AD    | Accomp Drawbars  |
| 12   | 90 (0x5A) | 0x00 | 90 / 0x00             | 135    | 0x83A406    | Pop Organ        |
| 13   | 89 (0x59) | 0x02 | 89 / 0x02             | 136    | 0x83A55F    | Soul Organ       |
| 14   | 92 (0x5C) | 0x02 | 92 / 0x02             | 137    | 0x83A6B8    | Rock Organ       |
| 15   | 94 (0x5E) | 0x01 | 94 / 0x01             | 138    | 0x83A811    | Organ Bass       |
| 16   | 87 (0x57) | 0x02 | 87 / 0x02             | 142    | 0x83AD24    | Theatre Organ    |
| 17   | 87 (0x57) | 0x03 | 87 / 0x03             | 143    | 0x83AE7D    | Theatre Accomp   |
| 18   | 87 (0x57) | 0x05 | 87 / 0x05             | 144    | 0x83AFD6    | Theatre Novelty  |
| 19   | 81 (0x51) | 0x00 | 81 / 0x00             | 146    | 0x83B1E6    | Mellow Accordion |
| 20   | 80 (0x50) | 0x01 | 80 / 0x01             | 148    | 0x83B354    | Bandoneon        |

#### ORCHESTRAL PAD (category 9, 20 sounds)

| slot | program    | bank | sent (program / bank) | tone # | tone record | tone name        |
|------|------------|------|-----------------------|--------|-------------|------------------|
| 1    | 102 (0x66) | 0x03 | 102 / 0x03            | 290    | 0x844249    | Strings & Horns  |
| 2    | 100 (0x64) | 0x06 | 100 / 0x06            | 291    | 0x8443F3    | Strings & Flutes |
| 3    | 0 (0x00)   | 0x05 | 0 / 0x05              | 292    | 0x84454C    | Piano & Strings  |
| 4    | 99 (0x63)  | 0x04 | 99 / 0x04             | 293    | 0x8446A5    | Heavenly Strings |
| 5    | 101 (0x65) | 0x05 | 101 / 0x05            | 307    | 0x845C0B    | Dreamy Strings   |
| 6    | 107 (0x6B) | 0x06 | 107 / 0x06            | 294    | 0x8447FE    | Warm String Pad  |
| 7    | 18 (0x12)  | 0x04 | 18 / 0x04             | 295    | 0x844906    | Chamber Orch     |
| 8    | 100 (0x64) | 0x05 | 100 / 0x05            | 297    | 0x844C5A    | Movie Musical    |
| 9    | 68 (0x44)  | 0x06 | 68 / 0x06             | 309    | 0x845EBD    | Big Band Pad     |
| 10   | 105 (0x69) | 0x04 | 105 / 0x04            | 298    | 0x844E04    | Field of Voices  |
| 11   | 99 (0x63)  | 0x03 | 99 / 0x03             | 303    | 0x845563    | Orchestra Pizz   |
| 12   | 101 (0x65) | 0x06 | 101 / 0x06            | 305    | 0x8458B7    | Unison Strings   |
| 13   | 100 (0x64) | 0x07 | 100 / 0x07            | 306    | 0x845A61    | Springtime Orch  |
| 14   | 103 (0x67) | 0x04 | 103 / 0x04            | 300    | 0x845107    | Dark Movie Scene |
| 15   | 103 (0x67) | 0x07 | 103 / 0x07            | 304    | 0x84570D    | Synth Orchestra  |
| 16   | 62 (0x3E)  | 0x07 | 62 / 0x07             | 301    | 0x845260    | Orchestral Sweep |
| 17   | 108 (0x6C) | 0x04 | 108 / 0x04            | 302    | 0x84540A    | Moonlight Pad    |
| 18   | 86 (0x56)  | 0x05 | 86 / 0x05             | 296    | 0x844AB0    | Cathedral        |
| 19   | 54 (0x36)  | 0x05 | 54 / 0x05             | 299    | 0x844F5D    | Horns & Woods    |
| 20   | 54 (0x36)  | 0x06 | 54 / 0x06             | 308    | 0x845D64    | Many Horns       |

#### SYNTH (category 10, 40 sounds)

| slot | program    | bank | sent (program / bank) | tone # | tone record | tone name        |
|------|------------|------|-----------------------|--------|-------------|------------------|
| 1    | 117 (0x75) | 0x00 | 117 / 0x00            | 250    | 0x841213    | Square Lead      |
| 2    | 118 (0x76) | 0x01 | 118 / 0x01            | 251    | 0x84131B    | Saw Lead         |
| 3    | 94 (0x5E)  | 0x00 | 94 / 0x00             | 252    | 0x841423    | Sine Lead        |
| 4    | 117 (0x75) | 0x02 | 117 / 0x02            | 253    | 0x84152B    | Chiffer Lead     |
| 5    | 60 (0x3C)  | 0x07 | 60 / 0x07             | 262    | 0x8420FB    | Block Synth      |
| 6    | 107 (0x6B) | 0x01 | 107 / 0x01            | 270    | 0x8429DD    | Mellow Ensemble  |
| 7    | 107 (0x6B) | 0x02 | 107 / 0x02            | 272    | 0x842BED    | Spacy Pad        |
| 8    | 116 (0x74) | 0x03 | 116 / 0x03            | 277    | 0x843166    | Fantasia         |
| 9    | 62 (0x3E)  | 0x06 | 62 / 0x06             | 278    | 0x8432BF    | Multi Sweeper    |
| 10   | 116 (0x74) | 0x02 | 116 / 0x02            | 279    | 0x843469    | Bell Pad         |
| 11   | 27 (0x1B)  | 0x03 | 27 / 0x03             | 254    | 0x841684    | Charang          |
| 12   | 115 (0x73) | 0x06 | 115 / 0x06            | 255    | 0x8417DD    | Metallica Solo   |
| 13   | 117 (0x75) | 0x05 | 117 / 0x05            | 256    | 0x841936    | Talking Lead     |
| 14   | 116 (0x74) | 0x06 | 116 / 0x06            | 257    | 0x841A8F    | Digi Stack       |
| 15   | 62 (0x3E)  | 0x04 | 62 / 0x04             | 286    | 0x843D36    | Warm Synth Brass |
| 16   | 62 (0x3E)  | 0x05 | 62 / 0x05             | 271    | 0x842AE5    | Warm Synth Pad   |
| 17   | 120 (0x78) | 0x01 | 120 / 0x01            | 274    | 0x842DFD    | Star Theme       |
| 18   | 120 (0x78) | 0x00 | 120 / 0x00            | 275    | 0x842F56    | Bowed Glass      |
| 19   | 108 (0x6C) | 0x02 | 108 / 0x02            | 280    | 0x8435C2    | Dream            |
| 20   | 108 (0x6C) | 0x03 | 108 / 0x03            | 281    | 0x84371B    | Mist             |
| 21   | 46 (0x2E)  | 0x02 | 46 / 0x02             | 264    | 0x84230B    | Bass & Lead      |
| 22   | 106 (0x6A) | 0x05 | 106 / 0x05            | 259    | 0x841D41    | Steamy Keys      |
| 23   | 60 (0x3C)  | 0x04 | 60 / 0x04             | 260    | 0x841E9A    | Olymp Synth      |
| 24   | 118 (0x76) | 0x02 | 118 / 0x02            | 261    | 0x841FA2    | Voco Synth       |
| 25   | 121 (0x79) | 0x05 | 121 / 0x05            | 258    | 0x841BE8    | 80's Solo        |
| 26   | 62 (0x3E)  | 0x02 | 62 / 0x02             | 282    | 0x843874    | Sweep Pad        |
| 27   | 107 (0x6B) | 0x03 | 107 / 0x03            | 283    | 0x84397C    | Halo Pad         |
| 28   | 21 (0x15)  | 0x03 | 21 / 0x03             | 276    | 0x84305E    | Atmosphere       |
| 29   | 102 (0x66) | 0x02 | 102 / 0x02            | 285    | 0x843BDD    | Poly Synth       |
| 30   | 106 (0x6A) | 0x00 | 106 / 0x00            | 289    | 0x8440F0    | Goblins          |
| 31   | 60 (0x3C)  | 0x05 | 60 / 0x05             | 265    | 0x842413    | Talking Synth    |
| 32   | 32 (0x20)  | 0x04 | 32 / 0x04             | 266    | 0x84251B    | Synth Harp       |
| 33   | 11 (0x0B)  | 0x05 | 11 / 0x05             | 267    | 0x842623    | Afro Dance       |
| 34   | 14 (0x0E)  | 0x06 | 14 / 0x06             | 268    | 0x84272B    | Digi Bells       |
| 35   | 9 (0x09)   | 0x02 | 9 / 0x02              | 269    | 0x842884    | Crystal          |
| 36   | 119 (0x77) | 0x00 | 119 / 0x00            | 263    | 0x842203    | 5th Wave         |
| 37   | 106 (0x6A) | 0x02 | 106 / 0x02            | 273    | 0x842CF5    | Metal Pad        |
| 38   | 106 (0x6A) | 0x03 | 106 / 0x03            | 284    | 0x843AD5    | Echo Drops       |
| 39   | 121 (0x79) | 0x03 | 121 / 0x03            | 287    | 0x843E3E    | Ice Rain         |
| 40   | 119 (0x77) | 0x01 | 119 / 0x01            | 288    | 0x843F97    | Soundtrack       |

#### BASS (category 11, 20 sounds)

| slot | program   | bank | sent (program / bank) | tone # | tone record | tone name        |
|------|-----------|------|-----------------------|--------|-------------|------------------|
| 1    | 43 (0x2B) | 0x00 | 43 / 0x00             | 210    | 0x83EF78    | Acoustic Bass    |
| 2    | 43 (0x2B) | 0x01 | 43 / 0x01             | 211    | 0x83F02F    | Mellow Ac.Bass   |
| 3    | 40 (0x28) | 0x00 | 40 / 0x00             | 212    | 0x83F0E6    | Electric Bass    |
| 4    | 40 (0x28) | 0x01 | 40 / 0x01             | 213    | 0x83F19D    | Bright E.Bass    |
| 5    | 40 (0x28) | 0x03 | 40 / 0x03             | 215    | 0x83F30B    | Funky E.Bass     |
| 6    | 40 (0x28) | 0x02 | 40 / 0x02             | 216    | 0x83F3C2    | Fretless Bass    |
| 7    | 42 (0x2A) | 0x00 | 42 / 0x00             | 217    | 0x83F479    | Picked E.Bass    |
| 8    | 41 (0x29) | 0x00 | 41 / 0x00             | 219    | 0x83F5E7    | Slap Bass 1      |
| 9    | 46 (0x2E) | 0x01 | 46 / 0x01             | 222    | 0x83F8AE    | Analog Bass      |
| 10   | 46 (0x2E) | 0x00 | 46 / 0x00             | 224    | 0x83FA1C    | Wow Bass         |
| 11   | 40 (0x28) | 0x04 | 40 / 0x04             | 214    | 0x83F254    | Fusion E.Bass    |
| 12   | 47 (0x2F) | 0x00 | 47 / 0x00             | 218    | 0x83F530    | Mute Bass        |
| 13   | 41 (0x29) | 0x01 | 41 / 0x01             | 220    | 0x83F6EF    | Slap Bass 2      |
| 14   | 42 (0x2A) | 0x01 | 42 / 0x01             | 223    | 0x83F965    | Soul Bass        |
| 15   | 47 (0x2F) | 0x03 | 47 / 0x03             | 225    | 0x83FAD3    | Dance Bass       |
| 16   | 47 (0x2F) | 0x02 | 47 / 0x02             | 226    | 0x83FBDB    | House Bass       |
| 17   | 46 (0x2E) | 0x05 | 46 / 0x05             | 227    | 0x83FC92    | Plastic Bass     |
| 18   | 45 (0x2D) | 0x04 | 45 / 0x04             | 228    | 0x83FD9A    | Basic Synth Bass |
| 19   | 47 (0x2F) | 0x05 | 47 / 0x05             | 221    | 0x83F7F7    | Killer Bass      |
| 20   | 47 (0x2F) | 0x04 | 47 / 0x04             | 229    | 0x83FEA2    | Techno Bass      |

#### DIGITAL DRAWBAR (category 12, 2 sounds)

| slot | program    | bank | sent (program / bank) | tone # | tone record | tone name       |
|------|------------|------|-----------------------|--------|-------------|-----------------|
| 1    | 128 (0x80) | 0x07 | 0 / 0x70              | 336    | 0x8706BD    | <Jazz Drawbars> |
| 2    | 129 (0x81) | 0x07 | 1 / 0x70              | 337    | 0x870867    | <Rock Drawbars> |

#### ACCORDION REG. (category 13, 20 sounds)

| slot | program   | bank | sent (program / bank) | tone # | tone record | tone name        |
|------|-----------|------|-----------------------|--------|-------------|------------------|
| 1    | 82 (0x52) | 0x01 | 82 / 0x01             | 110    | 0x838858    | German Acdn 1    |
| 2    | 82 (0x52) | 0x02 | 82 / 0x02             | 111    | 0x838960    | German Acdn 2    |
| 3    | 82 (0x52) | 0x03 | 82 / 0x03             | 112    | 0x838AB9    | German Acdn 3    |
| 4    | 82 (0x52) | 0x05 | 82 / 0x05             | 113    | 0x838BC1    | German Acdn 4    |
| 5    | 82 (0x52) | 0x06 | 82 / 0x06             | 114    | 0x838D6B    | German Acdn 5    |
| 6    | 82 (0x52) | 0x07 | 82 / 0x07             | 115    | 0x838EC4    | German Acdn 6    |
| 7    | 83 (0x53) | 0x06 | 83 / 0x06             | 116    | 0x83901D    | German Acdn 7    |
| 8    | 83 (0x53) | 0x07 | 83 / 0x07             | 117    | 0x839125    | German Acdn 8    |
| 9    | 81 (0x51) | 0x06 | 81 / 0x06             | 118    | 0x8391DC    | German Acdn Bs1  |
| 10   | 81 (0x51) | 0x07 | 81 / 0x07             | 119    | 0x839335    | German Acdn Bs2  |
| 11   | 80 (0x50) | 0x02 | 80 / 0x02             | 120    | 0x83948E    | Italian Acdn 1   |
| 12   | 80 (0x50) | 0x03 | 80 / 0x03             | 121    | 0x839545    | Italian Acdn 2   |
| 13   | 80 (0x50) | 0x04 | 80 / 0x04             | 122    | 0x83964D    | Italian Acdn 3   |
| 14   | 80 (0x50) | 0x05 | 80 / 0x05             | 123    | 0x839755    | Italian Acdn 4   |
| 15   | 80 (0x50) | 0x06 | 80 / 0x06             | 124    | 0x8398FF    | Italian Acdn 5   |
| 16   | 80 (0x50) | 0x07 | 80 / 0x07             | 125    | 0x839A58    | Italian Acdn 6   |
| 17   | 83 (0x53) | 0x04 | 83 / 0x04             | 126    | 0x839B60    | Italian Acdn 7   |
| 18   | 83 (0x53) | 0x05 | 83 / 0x05             | 127    | 0x839C68    | Italian Acdn 8   |
| 19   | 81 (0x51) | 0x04 | 81 / 0x04             | 128    | 0x839D1F    | Italian Acdn Bs1 |
| 20   | 81 (0x51) | 0x05 | 81 / 0x05             | 129    | 0x839E78    | Italian Acdn Bs2 |

#### GM SPECIAL (category 14, 20 sounds)

| slot | program    | bank | sent (program / bank) | tone # | tone record | tone name       |
|------|------------|------|-----------------------|--------|-------------|-----------------|
| 1    | 14 (0x0E)  | 0x02 | 14 / 0x02             | 244    | 0x840BE3    | Tinkle Bell     |
| 2    | 27 (0x1B)  | 0x01 | 27 / 0x01             | 245    | 0x840CEB    | Rock Harmonics  |
| 3    | 55 (0x37)  | 0x00 | 55 / 0x00             | 247    | 0x840EFB    | Orchestral Tuba |
| 4    | 73 (0x49)  | 0x00 | 73 / 0x00             | 248    | 0x840FB2    | Bagpipe         |
| 5    | 73 (0x49)  | 0x01 | 73 / 0x01             | 249    | 0x8410BA    | Shanai          |
| 6    | 86 (0x56)  | 0x02 | 86 / 0x02             | 246    | 0x840DF3    | Harmonium       |
| 7    | 122 (0x7A) | 0x00 | 122 / 0x00            | 230    | 0x83FFAA    | Agogo           |
| 8    | 122 (0x7A) | 0x01 | 122 / 0x01            | 231    | 0x840061    | Wood Block      |
| 9    | 123 (0x7B) | 0x03 | 123 / 0x03            | 232    | 0x840118    | Taiko Drum      |
| 10   | 122 (0x7A) | 0x03 | 122 / 0x03            | 235    | 0x84033D    | Reverse Cymbal  |
| 11   | 122 (0x7A) | 0x02 | 122 / 0x02            | 233    | 0x8401CF    | Melodic Tom     |
| 12   | 124 (0x7C) | 0x00 | 124 / 0x00            | 234    | 0x840286    | Synth Drum      |
| 13   | 124 (0x7C) | 0x01 | 124 / 0x01            | 236    | 0x8403F4    | Fret Noise      |
| 14   | 124 (0x7C) | 0x02 | 124 / 0x02            | 237    | 0x8404AB    | Breath Noise    |
| 15   | 124 (0x7C) | 0x03 | 124 / 0x03            | 238    | 0x840562    | Seashore        |
| 16   | 125 (0x7D) | 0x02 | 125 / 0x02            | 239    | 0x84070C    | Bird Tweet      |
| 17   | 123 (0x7B) | 0x00 | 123 / 0x00            | 240    | 0x840814    | Telephone       |
| 18   | 123 (0x7B) | 0x01 | 123 / 0x01            | 241    | 0x8408CB    | Helicopter      |
| 19   | 125 (0x7D) | 0x03 | 125 / 0x03            | 242    | 0x840982    | Applause        |
| 20   | 123 (0x7B) | 0x02 | 123 / 0x02            | 243    | 0x840A8A    | Gun Shot        |

#### DRUM KITS (category 15, 16 sounds)

| slot | program    | bank | sent (program / bank) | tone # | tone record | tone name                |
|------|------------|------|-----------------------|--------|-------------|--------------------------|
| 1    | 241 (0xF1) | 0x00 | 1 / 0x40              | 310    | 0x86363C    | Jazz Kit                 |
| 2    | 245 (0xF5) | 0x00 | 5 / 0x40              | 312    | 0x86388A    | Brush Kit                |
| 3    | 246 (0xF6) | 0x00 | 6 / 0x40              | 314    | 0x863763    | Trad Kit                 |
| 4    | 240 (0xF0) | 0x00 | 0 / 0x40              | 315    | 0x863079    | Standard Kit             |
| 5    | 243 (0xF3) | 0x00 | 3 / 0x40              | 318    | 0x8631A0    | Room Kit                 |
| 6    | 254 (0xFE) | 0x00 | 14 / 0x40             | 320    | 0x8633EE    | Light Rock Kit           |
| 7    | 247 (0xF7) | 0x00 | 7 / 0x40              | 321    | 0x8632C7    | Power Kit                |
| 8    | 248 (0xF8) | 0x00 | 8 / 0x40              | 323    | 0x863515    | Funk Kit                 |
| 9    | 249 (0xF9) | 0x00 | 9 / 0x40              | 326    | 0x863BFF    | Soul Kit                 |
| 10   | 242 (0xF2) | 0x00 | 2 / 0x40              | 327    | 0x863D26    | Electric Kit             |
| 11   | 250 (0xFA) | 0x00 | 10 / 0x40             | 324    | 0x8639B1    | Dance Kit                |
| 12   | 251 (0xFB) | 0x00 | 11 / 0x40             | 325    | 0x863AD8    | House Kit                |
| 13   | 244 (0xF4) | 0x00 | 4 / 0x40              | 329    | 0x864AFA    | Synth Kit                |
| 14   | 252 (0xFC) | 0x00 | 12 / 0x40             | 330    | 0x863E4D    | Orchestral Kit           |
| 15   | 253 (0xFD) | 0x00 | 13 / 0x40             | 332    | 0x864C21    | Sound Effect Kit         |
| 16   | 240 (0xF0) | 0x06 | 0 / 0x50              | -      | -           | (RAM user drum kit 0x50) |

#### MEMORY A (category 16, 20 sounds)

| slot | program    | bank | sent (program / bank) | tone # | tone record | tone name            |
|------|------------|------|-----------------------|--------|-------------|----------------------|
| 1    | 128 (0x80) | 0x00 | 0 / 0x10              | -      | -           | (RAM user bank 0x10) |
| 2    | 129 (0x81) | 0x00 | 1 / 0x10              | -      | -           | (RAM user bank 0x10) |
| 3    | 130 (0x82) | 0x00 | 2 / 0x10              | -      | -           | (RAM user bank 0x10) |
| 4    | 131 (0x83) | 0x00 | 3 / 0x10              | -      | -           | (RAM user bank 0x10) |
| 5    | 132 (0x84) | 0x00 | 4 / 0x10              | -      | -           | (RAM user bank 0x10) |
| 6    | 133 (0x85) | 0x00 | 5 / 0x10              | -      | -           | (RAM user bank 0x10) |
| 7    | 134 (0x86) | 0x00 | 6 / 0x10              | -      | -           | (RAM user bank 0x10) |
| 8    | 135 (0x87) | 0x00 | 7 / 0x10              | -      | -           | (RAM user bank 0x10) |
| 9    | 136 (0x88) | 0x00 | 8 / 0x10              | -      | -           | (RAM user bank 0x10) |
| 10   | 137 (0x89) | 0x00 | 9 / 0x10              | -      | -           | (RAM user bank 0x10) |
| 11   | 138 (0x8A) | 0x00 | 10 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 12   | 139 (0x8B) | 0x00 | 11 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 13   | 140 (0x8C) | 0x00 | 12 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 14   | 141 (0x8D) | 0x00 | 13 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 15   | 142 (0x8E) | 0x00 | 14 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 16   | 143 (0x8F) | 0x00 | 15 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 17   | 144 (0x90) | 0x00 | 16 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 18   | 145 (0x91) | 0x00 | 17 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 19   | 146 (0x92) | 0x00 | 18 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 20   | 147 (0x93) | 0x00 | 19 / 0x10             | -      | -           | (RAM user bank 0x10) |

#### MEMORY B (category 17, 20 sounds)

| slot | program    | bank | sent (program / bank) | tone # | tone record | tone name            |
|------|------------|------|-----------------------|--------|-------------|----------------------|
| 1    | 148 (0x94) | 0x00 | 20 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 2    | 149 (0x95) | 0x00 | 21 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 3    | 150 (0x96) | 0x00 | 22 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 4    | 151 (0x97) | 0x00 | 23 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 5    | 152 (0x98) | 0x00 | 24 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 6    | 153 (0x99) | 0x00 | 25 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 7    | 154 (0x9A) | 0x00 | 26 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 8    | 155 (0x9B) | 0x00 | 27 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 9    | 156 (0x9C) | 0x00 | 28 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 10   | 157 (0x9D) | 0x00 | 29 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 11   | 158 (0x9E) | 0x00 | 30 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 12   | 159 (0x9F) | 0x00 | 31 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 13   | 160 (0xA0) | 0x00 | 32 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 14   | 161 (0xA1) | 0x00 | 33 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 15   | 162 (0xA2) | 0x00 | 34 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 16   | 163 (0xA3) | 0x00 | 35 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 17   | 164 (0xA4) | 0x00 | 36 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 18   | 165 (0xA5) | 0x00 | 37 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 19   | 166 (0xA6) | 0x00 | 38 / 0x10             | -      | -           | (RAM user bank 0x10) |
| 20   | 167 (0xA7) | 0x00 | 39 / 0x10             | -      | -           | (RAM user bank 0x10) |

### Mode 0, the drum part (part 15)

16 sounds.  Grid D+0x14, last-slot table D+0x40.

#### DRUM KITS (category 15, 16 sounds)

| slot | program    | bank | sent (program / bank) | tone # | tone record | tone name                |
|------|------------|------|-----------------------|--------|-------------|--------------------------|
| 1    | 241 (0xF1) | 0x00 | 1 / 0x40              | 310    | 0x86363C    | Jazz Kit                 |
| 2    | 245 (0xF5) | 0x00 | 5 / 0x40              | 312    | 0x86388A    | Brush Kit                |
| 3    | 246 (0xF6) | 0x00 | 6 / 0x40              | 314    | 0x863763    | Trad Kit                 |
| 4    | 240 (0xF0) | 0x00 | 0 / 0x40              | 315    | 0x863079    | Standard Kit             |
| 5    | 243 (0xF3) | 0x00 | 3 / 0x40              | 318    | 0x8631A0    | Room Kit                 |
| 6    | 254 (0xFE) | 0x00 | 14 / 0x40             | 320    | 0x8633EE    | Light Rock Kit           |
| 7    | 247 (0xF7) | 0x00 | 7 / 0x40              | 321    | 0x8632C7    | Power Kit                |
| 8    | 248 (0xF8) | 0x00 | 8 / 0x40              | 323    | 0x863515    | Funk Kit                 |
| 9    | 249 (0xF9) | 0x00 | 9 / 0x40              | 326    | 0x863BFF    | Soul Kit                 |
| 10   | 242 (0xF2) | 0x00 | 2 / 0x40              | 327    | 0x863D26    | Electric Kit             |
| 11   | 250 (0xFA) | 0x00 | 10 / 0x40             | 324    | 0x8639B1    | Dance Kit                |
| 12   | 251 (0xFB) | 0x00 | 11 / 0x40             | 325    | 0x863AD8    | House Kit                |
| 13   | 244 (0xF4) | 0x00 | 4 / 0x40              | 329    | 0x864AFA    | Synth Kit                |
| 14   | 252 (0xFC) | 0x00 | 12 / 0x40             | 330    | 0x863E4D    | Orchestral Kit           |
| 15   | 253 (0xFD) | 0x00 | 13 / 0x40             | 332    | 0x864C21    | Sound Effect Kit         |
| 16   | 240 (0xF0) | 0x06 | 0 / 0x50              | -      | -           | (RAM user drum kit 0x50) |

### Mode 0, part 20

16 sounds.  Grid D+0x14, last-slot table D+0x44.

#### DRUM KITS (category 15, 16 sounds)

| slot | program    | bank | sent (program / bank) | tone # | tone record | tone name                |
|------|------------|------|-----------------------|--------|-------------|--------------------------|
| 1    | 241 (0xF1) | 0x00 | 1 / 0x40              | 310    | 0x86363C    | Jazz Kit                 |
| 2    | 245 (0xF5) | 0x00 | 5 / 0x40              | 312    | 0x86388A    | Brush Kit                |
| 3    | 246 (0xF6) | 0x00 | 6 / 0x40              | 314    | 0x863763    | Trad Kit                 |
| 4    | 240 (0xF0) | 0x00 | 0 / 0x40              | 315    | 0x863079    | Standard Kit             |
| 5    | 243 (0xF3) | 0x00 | 3 / 0x40              | 318    | 0x8631A0    | Room Kit                 |
| 6    | 254 (0xFE) | 0x00 | 14 / 0x40             | 320    | 0x8633EE    | Light Rock Kit           |
| 7    | 247 (0xF7) | 0x00 | 7 / 0x40              | 321    | 0x8632C7    | Power Kit                |
| 8    | 248 (0xF8) | 0x00 | 8 / 0x40              | 323    | 0x863515    | Funk Kit                 |
| 9    | 249 (0xF9) | 0x00 | 9 / 0x40              | 326    | 0x863BFF    | Soul Kit                 |
| 10   | 242 (0xF2) | 0x00 | 2 / 0x40              | 327    | 0x863D26    | Electric Kit             |
| 11   | 250 (0xFA) | 0x00 | 10 / 0x40             | 324    | 0x8639B1    | Dance Kit                |
| 12   | 251 (0xFB) | 0x00 | 11 / 0x40             | 325    | 0x863AD8    | House Kit                |
| 13   | 244 (0xF4) | 0x00 | 4 / 0x40              | 329    | 0x864AFA    | Synth Kit                |
| 14   | 252 (0xFC) | 0x00 | 12 / 0x40             | 330    | 0x863E4D    | Orchestral Kit           |
| 15   | 253 (0xFD) | 0x00 | 13 / 0x40             | 332    | 0x864C21    | Sound Effect Kit         |
| 16   | 240 (0xF0) | 0x06 | 0 / 0x50              | -      | -           | (RAM user drum kit 0x50) |

### GM mode (mode 1)

<details markdown="1">
<summary>Mode-1 category tables, the mode-1 drum kits and the GM voice map</summary>

### Mode 1, ordinary parts

128 sounds.  Grid D+0x24, last-slot table D+0x48.

#### PIANO (category 0, 8 sounds)

| slot | program  | bank | sent (program / bank) | tone # | tone record | tone name      |
|------|----------|------|-----------------------|--------|-------------|----------------|
| 1    | 0 (0x00) | 0x00 | 0 / 0x00              | 0      | 0x8324D4    | Piano          |
| 2    | 1 (0x01) | 0x00 | 1 / 0x00              | 1      | 0x8325DC    | Bright Piano   |
| 3    | 2 (0x02) | 0x00 | 2 / 0x00              | 2      | 0x8326E4    | Mellow Piano   |
| 4    | 3 (0x03) | 0x00 | 3 / 0x00              | 7      | 0x832BBB    | Electric Grand |
| 5    | 4 (0x04) | 0x00 | 4 / 0x00              | 15     | 0x833308    | Modern E.P.2   |
| 6    | 5 (0x05) | 0x00 | 5 / 0x00              | 9      | 0x832E1C    | E.Piano 1      |
| 7    | 6 (0x06) | 0x00 | 6 / 0x00              | 14     | 0x833251    | Modern E.P.1   |
| 8    | 7 (0x07) | 0x00 | 7 / 0x00              | 32     | 0x83439D    | Music Box      |

#### GUITAR (category 1, 8 sounds)

| slot | program   | bank | sent (program / bank) | tone # | tone record | tone name        |
|------|-----------|------|-----------------------|--------|-------------|------------------|
| 1    | 24 (0x18) | 0x00 | 24 / 0x00             | 49     | 0x8351FB    | Jazz Guitar 2    |
| 2    | 25 (0x19) | 0x00 | 25 / 0x00             | 48     | 0x835144    | Jazz Guitar 1    |
| 3    | 26 (0x1A) | 0x00 | 26 / 0x00             | 50     | 0x8352B2    | Bright Solid Gtr |
| 4    | 27 (0x1B) | 0x00 | 27 / 0x00             | 245    | 0x840CEB    | Rock Harmonics   |
| 5    | 28 (0x1C) | 0x00 | 28 / 0x00             | 51     | 0x8353BA    | Mellow Solid Gtr |
| 6    | 29 (0x1D) | 0x00 | 29 / 0x00             | 54     | 0x835630    | Mute Guitar      |
| 7    | 30 (0x1E) | 0x00 | 30 / 0x00             | 56     | 0x835891    | Distortion Gtr   |
| 8    | 31 (0x1F) | 0x00 | 31 / 0x00             | 62     | 0x835D2C    | Hawaiian Guitar1 |

#### STRINGS & VOCAL (category 2, 15 sounds)

| slot | program    | bank | sent (program / bank) | tone # | tone record | tone name        |
|------|------------|------|-----------------------|--------|-------------|------------------|
| 1    | 40 (0x28)  | 0x00 | 40 / 0x00             | 212    | 0x83F0E6    | Electric Bass    |
| 2    | 41 (0x29)  | 0x00 | 41 / 0x00             | 219    | 0x83F5E7    | Slap Bass 1      |
| 3    | 42 (0x2A)  | 0x00 | 42 / 0x00             | 217    | 0x83F479    | Picked E.Bass    |
| 4    | 43 (0x2B)  | 0x00 | 43 / 0x00             | 210    | 0x83EF78    | Acoustic Bass    |
| 5    | 44 (0x2C)  | 0x00 | 44 / 0x00             | 212    | 0x83F0E6    | Electric Bass    |
| 6    | 45 (0x2D)  | 0x00 | 45 / 0x00             | 228    | 0x83FD9A    | Basic Synth Bass |
| 7    | 48 (0x30)  | 0x00 | 48 / 0x00             | 157    | 0x83BD8F    | Trumpet          |
| 8    | 49 (0x31)  | 0x00 | 49 / 0x00             | 157    | 0x83BD8F    | Trumpet          |
| 9    | 50 (0x32)  | 0x00 | 50 / 0x00             | 160    | 0x83BFB4    | Harmon Mute Tpt  |
| 10   | 51 (0x33)  | 0x00 | 51 / 0x00             | 162    | 0x83C122    | Flugel Horn      |
| 11   | 52 (0x34)  | 0x00 | 52 / 0x00             | 163    | 0x83C1D9    | Bright Trombone  |
| 12   | 53 (0x35)  | 0x00 | 53 / 0x00             | 164    | 0x83C290    | Mellow Trombone  |
| 13   | 54 (0x36)  | 0x00 | 54 / 0x00             | 166    | 0x83C3FE    | Closed Fr.Horn   |
| 14   | 85 (0x55)  | 0x00 | 85 / 0x00             | 139    | 0x83A919    | Chapel Organ     |
| 15   | 110 (0x6E) | 0x00 | 110 / 0x00            | 105    | 0x838330    | Humming          |

#### BRASS (category 3, 8 sounds)

| slot | program   | bank | sent (program / bank) | tone # | tone record | tone name      |
|------|-----------|------|-----------------------|--------|-------------|----------------|
| 1    | 56 (0x38) | 0x00 | 56 / 0x00             | 150    | 0x83B606    | Bigband Brass  |
| 2    | 57 (0x39) | 0x00 | 57 / 0x00             | 151    | 0x83B6BD    | Marching Brass |
| 3    | 58 (0x3A) | 0x00 | 58 / 0x00             | 169    | 0x83C674    | Brass Fall     |
| 4    | 59 (0x3B) | 0x00 | 59 / 0x00             | 154    | 0x83BA26    | Octave Horns   |
| 5    | 60 (0x3C) | 0x00 | 60 / 0x00             | 155    | 0x83BB7F    | Synth Brass 1  |
| 6    | 61 (0x3D) | 0x00 | 61 / 0x00             | 155    | 0x83BB7F    | Synth Brass 1  |
| 7    | 62 (0x3E) | 0x00 | 62 / 0x00             | 155    | 0x83BB7F    | Synth Brass 1  |
| 8    | 63 (0x3F) | 0x00 | 63 / 0x00             | 156    | 0x83BC87    | Synth Brass 2  |

#### FLUTE (category 4, 9 sounds)

| slot | program   | bank | sent (program / bank) | tone # | tone record | tone name      |
|------|-----------|------|-----------------------|--------|-------------|----------------|
| 1    | 72 (0x48) | 0x00 | 72 / 0x00             | 196    | 0x83E0B7    | Pan Flute 1    |
| 2    | 73 (0x49) | 0x00 | 73 / 0x00             | 248    | 0x840FB2    | Bagpipe        |
| 3    | 74 (0x4A) | 0x00 | 74 / 0x00             | 199    | 0x83E3CF    | Recorder       |
| 4    | 75 (0x4B) | 0x00 | 75 / 0x00             | 203    | 0x83E74D    | Shakuhachi     |
| 5    | 76 (0x4C) | 0x00 | 76 / 0x00             | 170    | 0x83C72B    | Soprano Sax    |
| 6    | 77 (0x4D) | 0x00 | 77 / 0x00             | 171    | 0x83C833    | Alto Sax       |
| 7    | 78 (0x4E) | 0x00 | 78 / 0x00             | 175    | 0x83CC02    | Breathy Tenor  |
| 8    | 79 (0x4F) | 0x00 | 79 / 0x00             | 176    | 0x83CD5B    | Rock Tenor Sax |
| 9    | 82 (0x52) | 0x00 | 82 / 0x00             | 147    | 0x83B29D    | Musette        |

#### SAX & REED (category 5, 9 sounds)

| slot | program   | bank | sent (program / bank) | tone # | tone record | tone name        |
|------|-----------|------|-----------------------|--------|-------------|------------------|
| 1    | 22 (0x16) | 0x00 | 22 / 0x00             | 45     | 0x834DDB    | Folk Guitar      |
| 2    | 64 (0x40) | 0x00 | 64 / 0x00             | 190    | 0x83DB29    | Piccolo          |
| 3    | 65 (0x41) | 0x00 | 65 / 0x00             | 191    | 0x83DBE0    | Jazz Flute       |
| 4    | 66 (0x42) | 0x00 | 66 / 0x00             | 185    | 0x83D796    | Oboe             |
| 5    | 67 (0x43) | 0x00 | 67 / 0x00             | 186    | 0x83D84D    | English Horn     |
| 6    | 68 (0x44) | 0x00 | 68 / 0x00             | 180    | 0x83D2BF    | Jazz Clarinet 1  |
| 7    | 69 (0x45) | 0x00 | 69 / 0x00             | 183    | 0x83D628    | Classic Clarinet |
| 8    | 70 (0x46) | 0x00 | 70 / 0x00             | 187    | 0x83D904    | Bassoon          |
| 9    | 71 (0x47) | 0x00 | 71 / 0x00             | 180    | 0x83D2BF    | Jazz Clarinet 1  |

#### MALLET&ORCH PERC (category 6, 10 sounds)

| slot | program   | bank | sent (program / bank) | tone # | tone record | tone name       |
|------|-----------|------|-----------------------|--------|-------------|-----------------|
| 1    | 8 (0x08)  | 0x00 | 8 / 0x00              | 21     | 0x8339DA    | Vibraphone      |
| 2    | 9 (0x09)  | 0x00 | 9 / 0x00              | 20     | 0x8338D2    | Glockenspiel    |
| 3    | 10 (0x0A) | 0x00 | 10 / 0x00             | 23     | 0x833BEA    | Marimba         |
| 4    | 11 (0x0B) | 0x00 | 11 / 0x00             | 24     | 0x833CA1    | Xylophone       |
| 5    | 12 (0x0C) | 0x00 | 12 / 0x00             | 25     | 0x833D58    | Celesta         |
| 6    | 13 (0x0D) | 0x00 | 13 / 0x00             | 29     | 0x834085    | Bottle Marimba  |
| 7    | 14 (0x0E) | 0x00 | 14 / 0x00             | 26     | 0x833E0F    | Tubular Bells   |
| 8    | 46 (0x2E) | 0x00 | 46 / 0x00             | 224    | 0x83FA1C    | Wow Bass        |
| 9    | 47 (0x2F) | 0x00 | 47 / 0x00             | 218    | 0x83F530    | Mute Bass       |
| 10   | 55 (0x37) | 0x00 | 55 / 0x00             | 247    | 0x840EFB    | Orchestral Tuba |

#### WORLD PERC (category 7, 7 sounds)

| slot | program    | bank | sent (program / bank) | tone # | tone record | tone name    |
|------|------------|------|-----------------------|--------|-------------|--------------|
| 1    | 15 (0x0F)  | 0x00 | 15 / 0x00             | 69     | 0x8362CF    | Steel Drum   |
| 2    | 104 (0x68) | 0x00 | 104 / 0x00            | 102    | 0x8380BA    | Pop Vocal Ah |
| 3    | 105 (0x69) | 0x00 | 105 / 0x00            | 105    | 0x838330    | Humming      |
| 4    | 106 (0x6A) | 0x00 | 106 / 0x00            | 289    | 0x8440F0    | Goblins      |
| 5    | 107 (0x6B) | 0x00 | 107 / 0x00            | 106    | 0x838438    | Synth Vocal  |
| 6    | 108 (0x6C) | 0x00 | 108 / 0x00            | 280    | 0x8435C2    | Dream        |
| 7    | 114 (0x72) | 0x00 | 114 / 0x00            | 19     | 0x83381B    | Synth Clavi  |

#### ORGAN&ACCORDION (category 8, 7 sounds)

| slot | program   | bank | sent (program / bank) | tone # | tone record | tone name        |
|------|-----------|------|-----------------------|--------|-------------|------------------|
| 1    | 16 (0x10) | 0x00 | 16 / 0x00             | 16     | 0x833410    | Harpsichord      |
| 2    | 17 (0x11) | 0x00 | 17 / 0x00             | 18     | 0x833713    | Clavi            |
| 3    | 18 (0x12) | 0x00 | 18 / 0x00             | 17     | 0x833569    | Cembalo          |
| 4    | 19 (0x13) | 0x00 | 19 / 0x00             | 16     | 0x833410    | Harpsichord      |
| 5    | 20 (0x14) | 0x00 | 20 / 0x00             | 40     | 0x8349F7    | Classical Guitar |
| 6    | 21 (0x15) | 0x00 | 21 / 0x00             | 42     | 0x834B65    | Jazz Ac.Guitar   |
| 7    | 23 (0x17) | 0x00 | 23 / 0x00             | 46     | 0x834EE3    | 12 String Guitar |

#### SYNTH (category 10, 22 sounds)

| slot | program    | bank | sent (program / bank) | tone # | tone record | tone name        |
|------|------------|------|-----------------------|--------|-------------|------------------|
| 1    | 80 (0x50)  | 0x00 | 80 / 0x00             | 145    | 0x83B12F    | Bright Accordion |
| 2    | 81 (0x51)  | 0x00 | 81 / 0x00             | 146    | 0x83B1E6    | Mellow Accordion |
| 3    | 83 (0x53)  | 0x00 | 83 / 0x00             | 188    | 0x83D9BB    | Harmonica        |
| 4    | 84 (0x54)  | 0x00 | 84 / 0x00             | 140    | 0x83AA72    | Full Organ       |
| 5    | 86 (0x56)  | 0x00 | 86 / 0x00             | 246    | 0x840DF3    | Harmonium        |
| 6    | 87 (0x57)  | 0x00 | 87 / 0x00             | 142    | 0x83AD24    | Theatre Organ    |
| 7    | 88 (0x58)  | 0x00 | 88 / 0x00             | 130    | 0x839FD1    | Perc Organ       |
| 8    | 89 (0x59)  | 0x00 | 89 / 0x00             | 131    | 0x83A088    | Full Drawbars    |
| 9    | 90 (0x5A)  | 0x00 | 90 / 0x00             | 135    | 0x83A406    | Pop Organ        |
| 10   | 91 (0x5B)  | 0x00 | 91 / 0x00             | 133    | 0x83A1F6    | 16' & 1'         |
| 11   | 92 (0x5C)  | 0x00 | 92 / 0x00             | 137    | 0x83A6B8    | Rock Organ       |
| 12   | 93 (0x5D)  | 0x00 | 93 / 0x00             | 132    | 0x83A13F    | Jazz Drawbars    |
| 13   | 94 (0x5E)  | 0x00 | 94 / 0x00             | 252    | 0x841423    | Sine Lead        |
| 14   | 95 (0x5F)  | 0x00 | 95 / 0x00             | 252    | 0x841423    | Sine Lead        |
| 15   | 96 (0x60)  | 0x00 | 96 / 0x00             | 95     | 0x837B68    | Violin           |
| 16   | 97 (0x61)  | 0x00 | 97 / 0x00             | 99     | 0x837E95    | Cello            |
| 17   | 98 (0x62)  | 0x00 | 98 / 0x00             | 100    | 0x837F4C    | Bowed Bass       |
| 18   | 99 (0x63)  | 0x00 | 99 / 0x00             | 92     | 0x8377FF    | Pizzicato Str.   |
| 19   | 100 (0x64) | 0x00 | 100 / 0x00            | 82     | 0x836FE6    | ClassicalStrings |
| 20   | 101 (0x65) | 0x00 | 101 / 0x00            | 88     | 0x837430    | Slow Strings     |
| 21   | 102 (0x66) | 0x00 | 102 / 0x00            | 89     | 0x8374E7    | Octave Strings   |
| 22   | 103 (0x67) | 0x00 | 103 / 0x00            | 93     | 0x837907    | Synth Strings 1  |

#### BASS (category 11, 8 sounds)

| slot | program   | bank | sent (program / bank) | tone # | tone record | tone name |
|------|-----------|------|-----------------------|--------|-------------|-----------|
| 1    | 32 (0x20) | 0x00 | 32 / 0x00             | 33     | 0x834454    | Harp      |
| 2    | 33 (0x21) | 0x00 | 33 / 0x00             | 60     | 0x835BBE    | Banjo     |
| 3    | 34 (0x22) | 0x00 | 34 / 0x00             | 77     | 0x836A6D    | Ukulele   |
| 4    | 35 (0x23) | 0x00 | 35 / 0x00             | 61     | 0x835C75    | Mandolin  |
| 5    | 36 (0x24) | 0x00 | 36 / 0x00             | 65     | 0x835F51    | Shamisen  |
| 6    | 37 (0x25) | 0x00 | 37 / 0x00             | 64     | 0x835E9A    | Koto      |
| 7    | 38 (0x26) | 0x00 | 38 / 0x00             | 68     | 0x836218    | Sitar     |
| 8    | 39 (0x27) | 0x00 | 39 / 0x00             | 66     | 0x836008    | Kalimba   |

#### GM SPECIAL (category 14, 17 sounds)

| slot | program    | bank | sent (program / bank) | tone # | tone record | tone name      |
|------|------------|------|-----------------------|--------|-------------|----------------|
| 1    | 109 (0x6D) | 0x00 | 109 / 0x00            | 108    | 0x838648    | Vocal Doo      |
| 2    | 111 (0x6F) | 0x00 | 111 / 0x00            | 202    | 0x83E696    | Whistle        |
| 3    | 112 (0x70) | 0x00 | 112 / 0x00            | 253    | 0x84152B    | Chiffer Lead   |
| 4    | 113 (0x71) | 0x00 | 113 / 0x00            | 30     | 0x83413C    | African Mallet |
| 5    | 115 (0x73) | 0x00 | 115 / 0x00            | 19     | 0x83381B    | Synth Clavi    |
| 6    | 116 (0x74) | 0x00 | 116 / 0x00            | 15     | 0x833308    | Modern E.P.2   |
| 7    | 117 (0x75) | 0x00 | 117 / 0x00            | 250    | 0x841213    | Square Lead    |
| 8    | 118 (0x76) | 0x00 | 118 / 0x00            | 251    | 0x84131B    | Saw Lead       |
| 9    | 119 (0x77) | 0x00 | 119 / 0x00            | 263    | 0x842203    | 5th Wave       |
| 10   | 120 (0x78) | 0x00 | 120 / 0x00            | 275    | 0x842F56    | Bowed Glass    |
| 11   | 121 (0x79) | 0x00 | 121 / 0x00            | 250    | 0x841213    | Square Lead    |
| 12   | 122 (0x7A) | 0x00 | 122 / 0x00            | 230    | 0x83FFAA    | Agogo          |
| 13   | 123 (0x7B) | 0x00 | 123 / 0x00            | 240    | 0x840814    | Telephone      |
| 14   | 124 (0x7C) | 0x00 | 124 / 0x00            | 234    | 0x840286    | Synth Drum     |
| 15   | 125 (0x7D) | 0x00 | 125 / 0x00            | 38     | 0x834838    | Sleigh Bell    |
| 16   | 126 (0x7E) | 0x00 | 126 / 0x00            | 37     | 0x834781    | Timpani        |
| 17   | 127 (0x7F) | 0x00 | 127 / 0x00            | 34     | 0x83455C    | Orchestra Hit  |

Mode 1, the drum part (part 15): descriptor +0x4C lists 8 kits as program/bank pairs in bank 0x78 (the GM2 rhythm bank).  SndParam_LookupAndDispatch maps such a pair through the GS drum-set map at descriptor +0x30 to a KN5000 kit program 0xF0+k, bank 0; the table below applies the mode-0 rewrite to that pair, which is an INFERENCE (the mode-1 send path of a bank-0x78 pair is not traced).

#### DRUM KITS, mode 1 (8 kits)

| slot | program   | bank | +0x30 kit   | sent (program / bank) | tone # | tone record | tone name      |
|------|-----------|------|-------------|-----------------------|--------|-------------|----------------|
| 1    | 0 (0x00)  | 0x78 | 0xF0 / 0x00 | 0 / 0x40              | 315    | 0x863079    | Standard Kit   |
| 2    | 8 (0x08)  | 0x78 | 0xF3 / 0x00 | 3 / 0x40              | 318    | 0x8631A0    | Room Kit       |
| 3    | 16 (0x10) | 0x78 | 0xF7 / 0x00 | 7 / 0x40              | 321    | 0x8632C7    | Power Kit      |
| 4    | 24 (0x18) | 0x78 | 0xF2 / 0x00 | 2 / 0x40              | 327    | 0x863D26    | Electric Kit   |
| 5    | 25 (0x19) | 0x78 | 0xF0 / 0x00 | 0 / 0x40              | 315    | 0x863079    | Standard Kit   |
| 6    | 32 (0x20) | 0x78 | 0xF1 / 0x00 | 1 / 0x40              | 310    | 0x86363C    | Jazz Kit       |
| 7    | 40 (0x28) | 0x78 | 0xF5 / 0x00 | 5 / 0x40              | 312    | 0x86388A    | Brush Kit      |
| 8    | 48 (0x30) | 0x78 | 0xFC / 0x00 | 12 / 0x40             | 330    | 0x863E4D    | Orchestral Kit |

### GM voice map (descriptor +0x1C and +0x34)

Voice index v is GM program v+1: +0x1C gives the KN5000 sound used for it, +0x34 the note shift added to its note-ons when an SMF is imported.

| voice | GM program | program / bank | tone # | tone name        | +0x34 shift |
|-------|------------|----------------|--------|------------------|-------------|
| 0     | 1          | 0 / 0x00       | 0      | Piano            | 0           |
| 1     | 2          | 1 / 0x00       | 1      | Bright Piano     | 0           |
| 2     | 3          | 3 / 0x00       | 7      | Electric Grand   | 0           |
| 3     | 4          | 1 / 0x01       | 6      | Honky-Tonk Piano | 0           |
| 4     | 5          | 5 / 0x00       | 9      | E.Piano 1        | 0           |
| 5     | 6          | 6 / 0x00       | 14     | Modern E.P.1     | 0           |
| 6     | 7          | 16 / 0x00      | 16     | Harpsichord      | 0           |
| 7     | 8          | 17 / 0x00      | 18     | Clavi            | 0           |
| 8     | 9          | 12 / 0x00      | 25     | Celesta          | -12         |
| 9     | 10         | 9 / 0x00       | 20     | Glockenspiel     | -12         |
| 10    | 11         | 7 / 0x00       | 32     | Music Box        | -12         |
| 11    | 12         | 8 / 0x00       | 21     | Vibraphone       | 0           |
| 12    | 13         | 10 / 0x00      | 23     | Marimba          | 0           |
| 13    | 14         | 11 / 0x00      | 24     | Xylophone        | -12         |
| 14    | 15         | 14 / 0x00      | 26     | Tubular Bells    | -12         |
| 15    | 16         | 38 / 0x01      | 74     | Dulcimer         | 0           |
| 16    | 17         | 89 / 0x00      | 131    | Full Drawbars    | -12         |
| 17    | 18         | 88 / 0x00      | 130    | Perc Organ       | -12         |
| 18    | 19         | 92 / 0x02      | 137    | Rock Organ       | 0           |
| 19    | 20         | 84 / 0x00      | 140    | Full Organ       | 0           |
| 20    | 21         | 86 / 0x02      | 246    | Harmonium        | 0           |
| 21    | 22         | 80 / 0x00      | 145    | Bright Accordion | 0           |
| 22    | 23         | 83 / 0x00      | 188    | Harmonica        | 0           |
| 23    | 24         | 80 / 0x01      | 148    | Bandoneon        | 0           |
| 24    | 25         | 21 / 0x00      | 42     | Jazz Ac.Guitar   | 0           |
| 25    | 26         | 22 / 0x00      | 45     | Folk Guitar      | 0           |
| 26    | 27         | 25 / 0x00      | 48     | Jazz Guitar 1    | 0           |
| 27    | 28         | 26 / 0x00      | 50     | Bright Solid Gtr | 0           |
| 28    | 29         | 29 / 0x00      | 54     | Mute Guitar      | 0           |
| 29    | 30         | 27 / 0x02      | 57     | Overdrive Guitar | 0           |
| 30    | 31         | 30 / 0x00      | 56     | Distortion Gtr   | 0           |
| 31    | 32         | 27 / 0x01      | 245    | Rock Harmonics   | +12         |
| 32    | 33         | 43 / 0x00      | 210    | Acoustic Bass    | +12         |
| 33    | 34         | 40 / 0x01      | 213    | Bright E.Bass    | +12         |
| 34    | 35         | 42 / 0x00      | 217    | Picked E.Bass    | +12         |
| 35    | 36         | 40 / 0x02      | 216    | Fretless Bass    | +12         |
| 36    | 37         | 41 / 0x00      | 219    | Slap Bass 1      | +12         |
| 37    | 38         | 41 / 0x01      | 220    | Slap Bass 2      | +12         |
| 38    | 39         | 46 / 0x00      | 224    | Wow Bass         | +12         |
| 39    | 40         | 46 / 0x05      | 227    | Plastic Bass     | +12         |
| 40    | 41         | 96 / 0x00      | 95     | Violin           | 0           |
| 41    | 42         | 97 / 0x02      | 98     | Viola            | 0           |
| 42    | 43         | 97 / 0x00      | 99     | Cello            | 0           |
| 43    | 44         | 98 / 0x00      | 100    | Bowed Bass       | +12         |
| 44    | 45         | 100 / 0x02     | 91     | Tremolo Strings  | 0           |
| 45    | 46         | 99 / 0x00      | 92     | Pizzicato Str.   | 0           |
| 46    | 47         | 32 / 0x00      | 33     | Harp             | 0           |
| 47    | 48         | 126 / 0x00     | 37     | Timpani          | 0           |
| 48    | 49         | 100 / 0x00     | 82     | ClassicalStrings | 0           |
| 49    | 50         | 101 / 0x00     | 88     | Slow Strings     | 0           |
| 50    | 51         | 103 / 0x00     | 93     | Synth Strings 1  | 0           |
| 51    | 52         | 103 / 0x01     | 94     | Synth Strings 2  | 0           |
| 52    | 53         | 104 / 0x03     | 101    | Vocal Ah         | 0           |
| 53    | 54         | 109 / 0x00     | 108    | Vocal Doo        | 0           |
| 54    | 55         | 107 / 0x00     | 106    | Synth Vocal      | 0           |
| 55    | 56         | 127 / 0x01     | 34     | Orchestra Hit    | 0           |
| 56    | 57         | 48 / 0x00      | 157    | Trumpet          | 0           |
| 57    | 58         | 52 / 0x00      | 163    | Bright Trombone  | +12         |
| 58    | 59         | 55 / 0x00      | 247    | Orchestral Tuba  | +12         |
| 59    | 60         | 50 / 0x00      | 160    | Harmon Mute Tpt  | 0           |
| 60    | 61         | 54 / 0x01      | 167    | Open Fr.Horn     | 0           |
| 61    | 62         | 56 / 0x00      | 150    | Bigband Brass    | +12         |
| 62    | 63         | 60 / 0x00      | 155    | Synth Brass 1    | 0           |
| 63    | 64         | 62 / 0x04      | 286    | Warm Synth Brass | 0           |
| 64    | 65         | 76 / 0x00      | 170    | Soprano Sax      | 0           |
| 65    | 66         | 77 / 0x00      | 171    | Alto Sax         | 0           |
| 66    | 67         | 78 / 0x03      | 173    | Tenor Sax 1      | 0           |
| 67    | 68         | 79 / 0x01      | 177    | Baritone Sax     | 0           |
| 68    | 69         | 66 / 0x00      | 185    | Oboe             | 0           |
| 69    | 70         | 67 / 0x00      | 186    | English Horn     | 0           |
| 70    | 71         | 70 / 0x00      | 187    | Bassoon          | +12         |
| 71    | 72         | 68 / 0x00      | 180    | Jazz Clarinet 1  | 0           |
| 72    | 73         | 64 / 0x00      | 190    | Piccolo          | -12         |
| 73    | 74         | 65 / 0x00      | 191    | Jazz Flute       | 0           |
| 74    | 75         | 74 / 0x00      | 199    | Recorder         | 0           |
| 75    | 76         | 72 / 0x00      | 196    | Pan Flute 1      | 0           |
| 76    | 77         | 72 / 0x02      | 201    | Blown Bottle     | 0           |
| 77    | 78         | 75 / 0x00      | 203    | Shakuhachi       | 0           |
| 78    | 79         | 111 / 0x00     | 202    | Whistle          | -12         |
| 79    | 80         | 74 / 0x01      | 200    | Ocarina          | 0           |
| 80    | 81         | 117 / 0x00     | 250    | Square Lead      | 0           |
| 81    | 82         | 118 / 0x01     | 251    | Saw Lead         | 0           |
| 82    | 83         | 72 / 0x03      | 198    | Synth Calliope   | 0           |
| 83    | 84         | 117 / 0x02     | 253    | Chiffer Lead     | 0           |
| 84    | 85         | 27 / 0x03      | 254    | Charang          | 0           |
| 85    | 86         | 106 / 0x01     | 107    | Air Vox          | 0           |
| 86    | 87         | 119 / 0x00     | 263    | 5th Wave         | 0           |
| 87    | 88         | 46 / 0x02      | 264    | Bass & Lead      | +12         |
| 88    | 89         | 116 / 0x03     | 277    | Fantasia         | 0           |
| 89    | 90         | 107 / 0x01     | 270    | Mellow Ensemble  | 0           |
| 90    | 91         | 102 / 0x02     | 285    | Poly Synth       | 0           |
| 91    | 92         | 107 / 0x02     | 272    | Spacy Pad        | 0           |
| 92    | 93         | 120 / 0x00     | 275    | Bowed Glass      | 0           |
| 93    | 94         | 106 / 0x02     | 273    | Metal Pad        | 0           |
| 94    | 95         | 107 / 0x03     | 283    | Halo Pad         | 0           |
| 95    | 96         | 62 / 0x02      | 282    | Sweep Pad        | 0           |
| 96    | 97         | 121 / 0x03     | 287    | Ice Rain         | 0           |
| 97    | 98         | 119 / 0x01     | 288    | Soundtrack       | 0           |
| 98    | 99         | 9 / 0x02       | 269    | Crystal          | 0           |
| 99    | 100        | 21 / 0x03      | 276    | Atmosphere       | 0           |
| 100   | 101        | 108 / 0x03     | 281    | Mist             | 0           |
| 101   | 102        | 106 / 0x00     | 289    | Goblins          | 0           |
| 102   | 103        | 106 / 0x03     | 284    | Echo Drops       | 0           |
| 103   | 104        | 120 / 0x01     | 274    | Star Theme       | 0           |
| 104   | 105        | 38 / 0x00      | 68     | Sitar            | 0           |
| 105   | 106        | 33 / 0x00      | 60     | Banjo            | 0           |
| 106   | 107        | 36 / 0x00      | 65     | Shamisen         | 0           |
| 107   | 108        | 37 / 0x00      | 64     | Koto             | 0           |
| 108   | 109        | 39 / 0x00      | 66     | Kalimba          | 0           |
| 109   | 110        | 73 / 0x00      | 248    | Bagpipe          | 0           |
| 110   | 111        | 96 / 0x02      | 97     | Country Fiddle   | 0           |
| 111   | 112        | 73 / 0x01      | 249    | Shanai           | 0           |
| 112   | 113        | 14 / 0x02      | 244    | Tinkle Bell      | -12         |
| 113   | 114        | 122 / 0x00     | 230    | Agogo            | +12         |
| 114   | 115        | 15 / 0x00      | 69     | Steel Drum       | 0           |
| 115   | 116        | 122 / 0x01     | 231    | Wood Block       | -12         |
| 116   | 117        | 123 / 0x03     | 232    | Taiko Drum       | 0           |
| 117   | 118        | 122 / 0x02     | 233    | Melodic Tom      | 0           |
| 118   | 119        | 124 / 0x00     | 234    | Synth Drum       | 0           |
| 119   | 120        | 122 / 0x03     | 235    | Reverse Cymbal   | 0           |
| 120   | 121        | 124 / 0x01     | 236    | Fret Noise       | 0           |
| 121   | 122        | 124 / 0x02     | 237    | Breath Noise     | +12         |
| 122   | 123        | 124 / 0x03     | 238    | Seashore         | 0           |
| 123   | 124        | 125 / 0x02     | 239    | Bird Tweet       | 0           |
| 124   | 125        | 123 / 0x00     | 240    | Telephone        | 0           |
| 125   | 126        | 123 / 0x01     | 241    | Helicopter       | 0           |
| 126   | 127        | 125 / 0x03     | 242    | Applause         | 0           |
| 127   | 128        | 123 / 0x02     | 243    | Gun Shot         | 0           |

</details>

## Research Needed

- [ ] Trace UI event codes that trigger sound selection
- [ ] Document MEMORY A/B user sound storage format in DRAM
- [x] ~~What the +0x30 bytes 0xF0-0xFD mean, and what uses the +0x34 byte~~ — +0x30 is the GS drum-set map, +0x34 the SMF-import note shift (2026-10-31, kn5000-8dy; see "Slots +0x30 and +0x34" above)
- [x] ~~Map bank/program to a patch name~~ — each record header in `table_data/tone_database_records.s` names the bank selector and program that select it; see [Tone Database]({{ site.baseurl }}/tone-database/#program-change-lookup-bank-map--tone-number--offset-table)
- [x] ~~Relate a sound to its wave-ROM recordings~~ — tone record → partial blocks → SET descriptor → zone record → `+0x040` selector; see [Tone Database]({{ site.baseurl }}/tone-database/#wave-selection-end-to-end)

## Code References

| Symbol                       | Address  | Description                                                                    |
|------------------------------|----------|--------------------------------------------------------------------------------|
| `SOUND_DATA_SECTION_PTRS`    | 0xE023B0 | The 16 table pointers at descriptor +0x10..+0x4C (maps, not per-category data) |
| `SOUND_CATEGORY_NAMES`       | 0xE023F0 | 18 × padded ASCII category name strings                                        |
| `SOUND_DATA_PIANO`           | 0xE02510 | Slot +0x10: (bank, program) → (category, slot), mode 0 (8320 bytes)            |
| `SOUND_DATA_BRASS_PTRS`      | 0xE06BB0 | Slot +0x1C: voice index → {program, bank, 0xFF} (128 pointers)                 |
| `SOUND_DATA_WORLD_PERC`      | 0xE0ADD0 | Slot +0x2C: the mode-1 twin of +0x1C (128 pointers; no reader found)           |
| `SOUND_DATA_ORGAN_ACCORDION` | 0xE0B150 | Slot +0x30: the GS drum-set map, drum-set program → KN5000 kit (128 entries)   |
| `SndPart_SendProgramChange`  | 0xFEBB86 | Builds and sends the `{5, 0xC0, part, program, bank, effect}` record           |
| `SOUND_DATA_ORCHESTRAL_PAD`  | 0xE0B250 | Slot +0x34: the SMF-import note shift per GM voice (128 entries)               |
| `Voice_ProgChange`           | Sub CPU  | Sub CPU program change handler                                                 |

⚠ **Removed 2026-09: `Audio_SendCommand` at `0xFF0B6B`.** Neither the name nor the address
holds up. The routine this page meant is at `0x00FF0A72` and was renamed `Sprintf_Locked` in
March 2026 (`b5d34b75`, along with `Audio_CommandEncoder`→`Sprintf_Core` and 282 internal
`AudioCmd_*` labels→`Sprintf_*`) once it was shown to be a general sprintf()-style formatter
called from 128+ sites across MIDI, sequencer and demo code — not an audio-specific command
interface. Step 4's sender is now traced: `SndPart_SendProgramChange` (2026-10-31, see "The C0
sender" above).

## Related Pages

- [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) - Sound generation overview
- [Tone Generator]({{ site.baseurl }}/tone-generator/) - Voice register map and parameter write sequence
- [Waveform ROM Format]({{ site.baseurl }}/waveform-rom-format/) - PCM waveform data layout in IC304-IC307
- [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/) - Command transfer details
- [SysEx Messages]({{ site.baseurl }}/sysex-messages/) - Sound parameter SysEx
- [Storage Subsystem]({{ site.baseurl }}/storage-subsystem/) - Table Data ROM (tone database storage)
