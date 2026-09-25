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

| Offset | Value | Reader |
|--------|-------|--------|
| +0x00 | → `SOUND_CATEGORY_NAMES` | `StoreDRAMInit_LoadDRAM` copies category A's 16-char name ("WRONG SW NUMBER!" when A is out of range) |
| +0x04 | 18 | the category count (includes MEMORY A/B); a bound in `StoreDRAMInit_LoadDRAM` and `ApplyProgramChangeAs_DoLookupRe` |
| +0x08 | 40 | **sounds per category**: `FetchOscTableEntry_Prologue` clamps the slot below it and computes `category × 40 + slot` |
| +0x0C | `0xFFFFFFFF` | no reader found |

**The sixteen table slots** (label = the historical category name). A *selection record*
`{+0 category, +1 slot (0..39), +2 voice index (0..127), +3 program, +4 bank, +5 part}` is
passed between the readers. "Mode 1" is when `SndParam_LookupReadOnly(0xC0)` returns 1; in
mode 1 the tables hold 128 sounds in 12 categories, which suggests General MIDI mode, but that
is an inference from the counts.

| Slot | Label (historical) | What it is | Reader (v10) |
|------|--------------------|------------|--------------|
| +0x10 / +0x20 | `SOUND_DATA_PIANO` / `SOUND_DATA_FLUTE` | (bank, program) → (category, slot), mode 0 / mode 1 | `ApplyProgramChangeAs_LoadDRAM2` |
| +0x14 / +0x24 | `SOUND_DATA_GUITAR` / `SOUND_DATA_SAX_REED` | (category, slot) grid → (program, bank), mode 0 / 1 (18 × 40 × 2 = 1,440 B) | `FetchOscTableEntry_Prologue` |
| +0x18 / +0x28 | `SOUND_DATA_STRINGS_VOCAL` / `SOUND_DATA_MALLET_ORCH_PERC` | (bank, program) → voice index, mode 0 / 1 | `ApplyProgramChange_LoadDRAM` |
| +0x1C / +0x2C | `SOUND_DATA_BRASS_PTRS` / `SOUND_DATA_WORLD_PERC` | voice index → (program, bank): 128 pointers to `{program, bank, 0xFF}` records; nothing found indexes +0x2C | `SndParam_LookupOscEnvelope` |
| +0x30 | `SOUND_DATA_ORGAN_ACCORDION` | voice index → 2 bytes (0xF0-0xFD, 0), for part 15 or drawbar-type sounds | `SndParam_LookupOscEnvelope`, `SndParam_LookupAndDispatch` |
| +0x34 | `SOUND_DATA_ORCHESTRAL_PAD` | voice index → a signed byte (0, +12, -12: octave-shift-shaped; its use is not traced) | `SndParam_LookupByPartAndNote` |
| +0x38 | `SOUND_DATA_SYNTH` | **program-change remap**: a received `Cn p` is retransmitted as `Bn 00`, `Bn 20`, `Cn` from entry *p* | `SndParam_LookupFromPointerTable` |
| +0x3C | `SOUND_DATA_BASS` | per-category **last slot index**, mode 0, ordinary parts (18 bytes, 0xFF = not offered); the values give 368 sounds | `CharMap_ActivePreamb_Prologue` |
| +0x40 | `SOUND_DATA_DIGITAL_DRAWBAR` | the same for part 15 (only category 15, 16 drum kits) | same |
| +0x44 | `SOUND_DATA_ACCORDION_REG` | the same for part 20 | same |
| +0x48 | `SOUND_DATA_GM_SPECIAL` | the same in mode 1, ordinary parts (12 categories, 128 sounds) | same |
| +0x4C | `SOUND_DATA_DRUM_KITS` | the same in mode 1 for part 15 (8 kits); only its first 18 bytes are this table | same |

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
4. **Command encoding** — a formatting routine builds a MIDI Program Change (or extended command) with the voice/bank parameters. ⚠ This step used to be attributed to `Audio_SendCommand`; that symbol was renamed in March 2026 to `Sprintf_Locked` once it was found to be a general sprintf()-style formatter (parses `%d`/`%x`/`%f`/`%s` format strings), not an audio-specific command sender — see the correction below.
5. **Inter-CPU transfer** — Command sent via `sendCOMM` → `InterCPU_Send_Data_Block` → latch at 0x120000
6. **Sub CPU processing** — `Audio_CmdHandler_00_1F` writes to ring buffer → `MIDI_Dispatch` routes to `Voice_ProgChange`
7. **Voice activation** — Sub CPU updates the voice parameter block (287 bytes at `0x041300 + channel × 0x11F`)

## Instrument Patch Catalog

The Table Data ROM contains the display names for all instrument patches, embedded within variable-length sound parameter records.

> **Superseded framing.** The address range and record shape this section originally quoted ("0x832000-0x850000", "a padded ASCII name string up to 20 characters") came from a string scan and are wrong. The records are the **tone database**: 579 variable-length records tiling `0x8324D4`-`0x855A47`, each opening with a 16-character space-padded name field, reached through the 629-entry offset table at `0x831B00` — not by their string spacing. See [Tone Database]({{ site.baseurl }}/tone-database/). The catalog below is still a useful name listing; its address groupings are approximate.

The following catalog was extracted by scanning the Table Data ROM for ASCII name strings. Names are organized by approximate address region, which corresponds loosely to the 16 factory categories above. GM-compatible patches largely duplicate KN5000-specific patches with different parameter settings.

**Total: ~303 unique instrument patches** (291 KN5000-specific + 12 GM-only)

### Piano (14)

Piano, Bright Piano, Mellow Piano, Piano 1 Octave, Piano 2 Octave, Rock Piano, Honky-Tonk Piano, Electric Grand, Midi Grand, E.Piano 1, E.Piano 2, Suitcase E.P., Tremolo E.Piano, Wurly E.Piano

### Electric Piano & Keyboard (6)

Modern E.P.1, Modern E.P.2, Harpsichord, Cembalo, Synth Clavi, Music Box

### Mallet & Tuned Percussion (10)

Glockenspiel, Vibraphone, Vibes & Jazz Guitar, Marimba, Xylophone, Celesta, Tubular Bells, Carillon, Wind Chime, Bottle Marimba, African Mallet, Caribbean Mallet

### Guitar — Acoustic (8)

Classical Guitar, Spanish Guitar, Jazz Ac.Guitar, Bossa Guitar, Folk Guitar, 12 String Guitar, ElectroAc.Guitar, Guitar Harmonics

### Guitar — Electric (12)

Jazz Guitar 1, Jazz Guitar 2, Bright Solid Gtr, Mellow Solid Gtr, Clean Solid Gtr, Fusion Solid Gtr, Mute Guitar, Funk Mute Guitar, Distortion Gtr, Overdrive Guitar, Country Guitar, Nashville Steel

### Guitar — World / Plucked (9)

Banjo, Mandolin, Hawaiian Guitar 1, Hawaiian Guitar 2, Shamisen, Bouzouki, Dulcimer, Cumbus, Ukulele

### Strings — Ensemble (11)

Symphonic Strings, Concert Strings, Classical Strings, Marcato Strings, Violin Ensemble, Viola Ensemble, Cello Ensemble, Bass Ensemble, Slow Strings, Octave Strings, Bass Strings

### Strings — Special (6)

Tremolo Strings, Pizzicato Str., Synth Strings 1, Synth Strings 2, Bowed Bass, Country Fiddle

### Strings — Solo (3)

Violin, Jazz Violin, Viola, Cello

### Vocal (9)

Vocal Ah, Pop Vocal Ah, Stereo Vocal Ah, Vocal Ooh, Humming, Synth Vocal, Air Vox, Vocal Doo, Vocal Daa

### Accordion — German (10)

German Acdn 1-8, German Acdn Bs1, German Acdn Bs2

### Accordion — Italian (10)

Italian Acdn 1-8, Italian Acdn Bs1, Italian Acdn Bs2

### Accordion — General (5)

Bright Accordion, Mellow Accordion, Musette, Bandoneon, Folk Accordion

### Organ (13)

Perc Organ, Full Drawbars, Jazz Drawbars, Accomp Drawbars, Pop Organ, Soul Organ, Rock Organ, Organ Bass, Chapel Organ, Full Organ, Cathedral Organ, Theatre Organ, Theatre Accomp, Theatre Novelty

### Brass — Ensemble (6)

Bigband Brass, Marching Brass, Brass & Synth, Octave Brass, Octave Horns, Brass Fall

### Brass — Solo (10)

Trumpet, Solo Trumpet, Orchest. Trumpet, Harmon Mute Tpt, Straight Mute Tpt, Flugel Horn, Bright Trombone, Mellow Trombone, Cup Mute Trombone, Closed Fr.Horn, Open Fr.Horn, Marching Tuba, Orchestral Tuba

### Brass — Synth (2)

Synth Brass 1, Synth Brass 2

### Saxophone (10)

Soprano Sax, Alto Sax, Mellow Alto Sax, Tenor Sax 1, Tenor Sax 2, Breathy Tenor, Rock Tenor Sax, Baritone Sax, Distortion Sax, Unison Saxes

### Clarinet & Reed (7)

Jazz Clarinet 1, Jazz Clarinet 2, Mellow Clarinet, Classic Clarinet, Bass Clarinet, Harmonica, Blues Harmonica

### Woodwind — Double Reed (3)

English Horn, Bassoon, Bagpipe

### Flute (12)

Piccolo, Jazz Flute, Classical Flute, Alto Flute, Alto Ensemble, Flutter Flute, Pan Flute 1, Pan Flute 2, Recorder, Ocarina, Blown Bottle, Whistle

### Flute — World & Special (6)

Shakuhachi, Quena, Chopper Flute, Penny Whistle, Marching Whistle, Chiff Flute, Synth Calliope, Shanai

### Bass — Acoustic (2)

Acoustic Bass, Mellow Ac.Bass

### Bass — Electric (9)

Electric Bass, Bright E.Bass, Fusion E.Bass, Funky E.Bass, Fretless Bass, Picked E.Bass, Mute Bass, Slap Bass 1, Slap Bass 2

### Bass — Synth (7)

Killer Bass, Analog Bass, Soul Bass, Wow Bass, Dance Bass, House Bass, Plastic Bass, Basic Synth Bass, Techno Bass

### World Percussion (8)

Kalimba, Metal Kalimba, Steel Drum, Bonang, Sarrons, Kenong, Slentem, Talking Drum

### Percussion & SFX (10)

Wood Block, Taiko Drum, Melodic Tom, Synth Drum, Sleigh Bell, Tinkle Bell, Agogo, Reverse Cymbal, Orchestra Hit, Dance Hit 1, Dance Hit 2

### Sound Effects (7)

Fret Noise, Breath Noise, Seashore, Bird Tweet, Telephone, Helicopter, Applause, Gun Shot

### Synth — Lead (12)

Square Lead, Saw Lead, Sine Lead, Chiffer Lead, Charang, Metallica Solo, Talking Lead, Digi Stack, 80's Solo, Steamy Keys, Olymp Synth, Voco Synth

### Synth — Pad & Texture (20)

Block Synth, 5th Wave, Bass & Lead, Talking Synth, Synth Harp, Afro Dance, Digi Bells, Crystal, Mellow Ensemble, Warm Synth Pad, Spacy Pad, Metal Pad, Star Theme, Bowed Glass, Atmosphere, Fantasia, Bell Pad, Dream, Sweep Pad, Halo Pad, Echo Drops, Poly Synth, Warm Synth Brass, Ice Rain, Soundtrack

### Synth — Multi Sweeper (1)

Multi Sweeper

### Orchestra Combo (14)

Goblins, Strings & Horns, Strings & Flutes, Piano & Strings, Heavenly Strings, Warm String Pad, Chamber Orch, Cathedral, Movie Musical, Field of Voices, Horns & Woods, Dark Movie Scene, Orchestral Sweep, Moonlight Pad, Orchestra Pizz, Synth Orchestra

### Orchestra Combo — Specialty (5)

Unison Strings, Springtime Orch, Dreamy Strings, Many Horns, Big Band Pad

### Harmonium & Misc (2)

Harmonium, Rock Harmonics

### GM-Only Patches (12)

Pipe Organ, Accordion, Jazz Guitar, Solid Guitar, Modern E.P., E.Piano (variant), Bright Bass, Synth String 1, Synth String 2, Jazz Clarinet (variant), Brightness, Warm Pad

## Research Needed

- [ ] Decode the exact binary format of large categories (PIANO, STRINGS & VOCAL, MALLET & ORCH PERC)
- [ ] Determine meaning of sub-category indices in headers (bytes 0-7 or 0-9)
- [x] ~~Map voice_id/bank pairs to actual sound names~~ — 303 patch names extracted from Table Data ROM
- [ ] Trace UI event codes that trigger sound selection
- [ ] Document MEMORY A/B user sound storage format in DRAM
- [ ] Understand voice IDs ≥ 0xF0 (organ drawbar mode hypothesis)
- [ ] Analyze relationship between these voice_id values and Table Data ROM waveform indices
- [ ] Map exact voice_id/bank → Table Data ROM patch name correspondence

## Code References

| Symbol | Address | Description |
|--------|---------|-------------|
| `SOUND_DATA_SECTION_PTRS` | 0xE023B0 | 16-entry pointer table to category data |
| `SOUND_CATEGORY_NAMES` | 0xE023F0 | 18 × padded ASCII category name strings |
| `SOUND_DATA_PIANO` | 0xE02510 | Piano voice data (8320 bytes) |
| `SOUND_DATA_BRASS_PTRS` | 0xE06BB0 | Brass pointer table (128 entries) |
| `SOUND_DATA_WORLD_PERC` | 0xE0ADCD | World Perc pointer table (128 entries) |
| `SOUND_DATA_ORGAN_ACCORDION` | 0xE0B190 | Organ inline 2-byte pairs (128 entries) |
| `Voice_ProgChange` | Sub CPU | Sub CPU program change handler |

⚠ **Removed 2026-09: `Audio_SendCommand` at `0xFF0B6B`.** Neither the name nor the address
holds up. The routine this page meant is at `0x00FF0A72` and was renamed `Sprintf_Locked` in
March 2026 (`b5d34b75`, along with `Audio_CommandEncoder`→`Sprintf_Core` and 282 internal
`AudioCmd_*` labels→`Sprintf_*`) once it was shown to be a general sprintf()-style formatter
called from 128+ sites across MIDI, sequencer and demo code — not an audio-specific command
interface. The step-4 description above ("command encoding") likely still happens somewhere
in the sound-selection path, but this page does not have a verified, current symbol for it.

## Related Pages

- [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) - Sound generation overview
- [Tone Generator]({{ site.baseurl }}/tone-generator/) - Voice register map and parameter write sequence
- [Waveform ROM Format]({{ site.baseurl }}/waveform-rom-format/) - PCM waveform data layout in IC304-IC307
- [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/) - Command transfer details
- [SysEx Messages]({{ site.baseurl }}/sysex-messages/) - Sound parameter SysEx
- [Storage Subsystem]({{ site.baseurl }}/storage-subsystem/) - Table Data ROM (waveform storage)
