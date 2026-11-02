---
layout: page
title: Accompaniment Engine
permalink: /accompaniment-engine/
---

# Accompaniment Engine

## Overview

The KN5000's accompaniment (auto-accompaniment) system automatically generates musical backing tracks based on the player's chord input on the lower keyboard. The engine plays patterns from built-in styles, transposing and voicing them according to the detected chord. This is one of the largest firmware subsystems, spanning chord recognition, pattern sequencing, bass/chord/rhythm generation, section switching (intro, fill-in, ending, variation), and real-time MIDI event dispatch.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                   LOWER KEYBOARD                      │
│        (Left half of keybed, split point)             │
└──────────────────────────────────────────────────────┘
                          │
                          v
┌──────────────────────────────────────────────────────┐
│              CHORD RECOGNITION (Chord_*)              │
│  Scans held keys, matches chord type + root note     │
│  Sets dirty flags when chord changes                 │
└──────────────────────────────────────────────────────┘
                          │
                          v
┌──────────────────────────────────────────────────────┐
│           ACCOMPANIMENT SEQUENCER (AccompSeq)        │
│  Two independent channels (0 and 1)                  │
│  Each has: position, beat counter, pattern pointer   │
│  Events: notes (0x90/0x91), part ctl (0xD1-D5, D7),  │
│  program change (0xC0), position (0x84), beat (0x81) │
└──────────────────────────────────────────────────────┘
              │                    │
              v                    v
┌────────────────────┐  ┌─────────────────────┐
│  BASS GENERATION   │  │  CHORD GENERATION   │
│  (AccBass)         │  │  (AccChord voices)  │
│  Single-note bass  │  │  Multi-note chords  │
│  lines from style  │  │  transposed to root │
└────────────────────┘  └─────────────────────┘
              │                    │
              v                    v
┌──────────────────────────────────────────────────────┐
│              RHYTHM GENERATION (AccRhythm)            │
│  Drum patterns, percussion mapping                   │
│  DrumChannel_MapToIndex for note routing             │
└──────────────────────────────────────────────────────┘
              │
              v
┌──────────────────────────────────────────────────────┐
│          VOICE ASSIGNMENT (AccVoice/AccPart)          │
│  Maps accompaniment parts to tone generator voices   │
│  Handles program changes, tuning, velocity           │
└──────────────────────────────────────────────────────┘
              │
              v
┌──────────────────────────────────────────────────────┐
│          TONE GENERATOR / MIDI OUTPUT                 │
│  SubCPU receives note events for sound generation    │
│  MIDI OUT sends accompaniment to external devices    │
└──────────────────────────────────────────────────────┘
```

## Main Loop Integration

The accompaniment engine is called from three phases of the main firmware loop (the phase numbers of the comment above `MainLoop` in `boot/system_handlers.s`):

| Function                  | Address    | Main-loop phase / purpose                            |
|---------------------------|------------|------------------------------------------------------|
| `AccWrap_FlagSync`        | `0xF59B01` | Phase 1: synchronize accompaniment wrapper flags     |
| `AccDir_PeriodicEntry`    | `0xF5BD7A` | Phase 5: accompaniment direction periodic processing |
| `AccompSeq_PeriodicEntry` | `0xF6DCA9` | Phase 6: main accompaniment sequencer tick           |

`AccompSeq_PeriodicEntry` is the primary entry point, called once per main loop iteration. It:

1. Reads timing state from interrupt-updated counters at RAM 1128-1131
2. Copies to working state at RAM 32284-32291
3. Checks the start/stop bit (bit 2 of state byte at 32287)
4. If running, processes both accompaniment channels sequentially

## Accompaniment Sequencer

### Dual-Channel Architecture

The sequencer runs **two independent channels** (channel 0 and channel 1), each with its own:
- Pattern data pointer (RAM 32332/32333)
- Pattern read position (RAM 32322/32324): in pool mode a block number and an offset into a pool of 256-byte blocks at 0x1E8B00, in the battery-backed SRAM; otherwise a 32-bit address
- Beat counter (RAM 32326), incremented at each 0x81 beat marker
- Pointer at RAM 32328 (set at channel setup to 0x7E40 for the first channel, 0x7E41 for the second)
- Pattern state (RAM 32372)

Channel 0 uses state at offsets 32300-32302, channel 1 at 32304-32306. The `AccompSeq_InitEventDispatch` routine processes events for the current channel.

### Event Types

The sequencer reads a stream of events from pattern data at the read position, which `ResolveVRAMAddressForVoice` turns into an address (in pool mode a block of the pool at 0x1E8B00, which is SRAM, not VRAM). Each event starts with a type byte:

| Type          | Name            | Description                                                                                                              |
|---------------|-----------------|--------------------------------------------------------------------------------------------------------------------------|
| 0x81          | Beat marker     | Advances beat counter, checks pattern end                                                                                |
| 0x83          | Part transition | Handled by `AccompSeq_HandlePartTransition` (immediate)                                                                  |
| 0x84          | Position        | Update sequencer position                                                                                                |
| 0x90          | Note (small)    | Note-on/off event (compact format)                                                                                       |
| 0x91          | Note (large)    | Note-on/off event (extended format)                                                                                      |
| 0xC0          | Program change  | Change instrument patch                                                                                                  |
| 0xD1-D5, 0xD7 | Part control    | Part-specific control (voice, volume, pan, etc.); there is no 0xD6 case, so a 0xD6 byte is skipped like any unknown byte |

### Event Processing Loop

`AccompSeq_EventDispatchLoop` reads events until a timing boundary is reached:

1. Read event type byte from pattern data (via `ResolveVRAMAddressForVoice`)
2. Dispatch by type:
   - 0x84: Call `AccompSeq_UpdatePosition` (immediate, no timing)
   - 0x83: Call `AccompSeq_HandlePartTransition` (immediate)
   - 0x81: Check beat boundary with delta time comparison
   - 0x90/0x91/0xC0/0xD1-D5/0xD7: Check timing via `AccompSeq_CalcDeltaTime`
3. If delta time <= 24 ticks (a sixteenth note at 96 ticks per beat): process event via `AccompSeq_ParseEvents`
4. If delta time > 24 ticks: set wait flag (bit 0 of 32339) and exit loop

### Timing

The accompaniment uses a 96-tick-per-beat timing resolution (PPQN = 96), with each beat divided into 96 sub-ticks. The firmware compares the current tick position against event timestamps using `AccompSeq_CalcDeltaTime`:

- Delta = 0: event is exactly on time
- Delta <= 24: event is within tolerance (play now)
- Delta > 24: event is in the future (wait)

A beat marker (event type 0x81) that falls due increments the beat counter (32326) and calls `AccompSeq_AdvancePosition`, which:
1. Advances the read position by one byte (offset 32324, carrying into 32322)
2. If the byte there is a block link (0x87), reads the next block number from the block header via `AccompSeq_ReadBeatHeader` and continues at offset 6 of that block

### Pattern End and Looping

A 0x87 byte links to the next 256-byte block: `AccompSeq_ReadBeatHeader` reads the next block's number from the current block's header (the word at offset 3), and reading resumes at offset 6 of that block. The loop is the 0x83 event: `AccompSeq_HandlePartTransition` reloads the read position saved for the channel (RAM 32308/32310 for the first channel, 32312/32314 for the second) when bit 3 of RAM 32295 is set, and otherwise stops the part.

## Style Data Format

### Style Variation Groups

Styles are organized into variation groups; the factory patterns are read from the Rhythm ROM at 0x400000 (see [Sequencer]({{ site.baseurl }}/sequencer/#pattern-loading-pipeline)). The ROM's own format (202 style records of two 1 KB halves, six parts of 19 track slots each, and 28,400 one-part tracks in the `80 FF FF FF FF 87` ... `83 87` event language) is on [Rhythm ROM (IC14)]({{ site.baseurl }}/rhythm-rom/). Each style has multiple variations:

| Variation | Description                                     |
|-----------|-------------------------------------------------|
| Vari1-4   | Main pattern variations (increasing complexity) |
| Fill1-2   | Fill-in patterns (short transitional phrases)   |
| Int1-2    | Intro patterns                                  |
| End1-2    | Ending patterns                                 |

Each variation group (A, B, C) has these sections. The `StyleVarGrp_*` labels are not pattern data: they are the one-letter group strings ("A", "B", "C") that the UI shows, in the Program ROM (`ui_widgets/naka_screen_dispatch.s`, listed by `PtrTbl_StyleVarGroupCodes`).

### Style Groups (Built-in Styles)

The Program ROM holds the style browser's ten group tables, one per category; each entry is a style-name pointer and a variation-table pointer (`ui_widgets/style_bitmaps.s`). The browser reaches them through its root at `0xECFCA4` (`MstStyle_GenreTable`), ten {group name, group table} pairs. The categories are the ten of the [Music Stylist database]({{ site.baseurl }}/music-stylist-database/#the-ten-categories). The category words in the `StyleGroup_*` labels are older guesses that do not match them, and the label at `0xECFCA8`, 4 bytes into the root, is not a group table either: it is the root's group-table column, `MstStyle_GenreTable_GroupColumn` (it was called `StyleGroup_LatinDance_Table`).

| Table                             | Address    | Category (the firmware's group name) |
|-----------------------------------|------------|--------------------------------------|
| `StyleGroup_ModernDance_Table`    | `0xECE2F0` | Easy Listening                       |
| `StyleGroup_RockPop_PairTable`    | `0xECE61E` | Rock & Pop                           |
| `StyleGroup_PopBallad_Table`      | `0xECE980` | Dance Pop                            |
| `StyleGroup_PartyMusic_PairTable` | `0xECEB42` | Party Music                          |
| `StyleGroup_Swing_Table`          | `0xECED38` | Gospel/Blues/R&B                     |
| `StyleGroup_FunkFusion_Separator` | `0xECEF14` | Jazz & Swing                         |
| `StyleGroup_JazzCombo_Table`      | `0xECF228` | Show/Trad Dance                      |
| `StyleGroup_TradFolk_PairTable`   | `0xECF556` | Trad & Folk                          |
| `StyleGroup_WorldMusic_Table`     | `0xECF7E8` | Country                              |
| `StyleGroup_LatinWorld_PairTable` | `0xECF9AA` | Latin / World                        |

The category column is read from the browser root by `tools/style_browser_groups.py` in this
repository.

## Chord Recognition

The recognizer is the `Chord_*` group of the main CPU (v10 `audio/note_voice_mapping.s`);
`AccChord_ReadAndStoreKeys` only copies its result (`CHORD_ROOT`, `CHORD_TYPE`, `CHORD_BASS_ROOT`,
`CHORD_FLAGS`) into the accompaniment state, and `AccChord_CompareAndSetDirty` flags a change.

1. **Trigger.** A change of the held chord keys starts recognition (`Chord_RecognizeNowOrDelay`) at once
   (`CHORD_FLAGS` bit 6) or after 5 ticks (`CHORD_RECOGNIZE_DELAY`). When keys are released it waits 6 or 22
   ticks (`CHORD_DECAY_TIMER`), so a chord is not lost while the hand moves.
2. **Collect.** `Chord_CollectHeldNotes` takes up to four held notes of different pitch class, newest first
   (`CHORD_NOTES`, `CHORD_NOTE_COUNT`).
3. **Look up.** `Voice_ComputeNoteBitPosition` turns their intervals above the reference note (the last one
   collected) into a mask whose low 11 bits index `ChordRecog_IntervalMaskTable` (2,048 two-byte entries at
   0xEEAE44): chord type 1..41 and the root as a semitone offset above the reference.
4. **Fall back.** Without a match on all notes, `Voice_LookupNoteAndComputePitch` tries other note subsets
   (3 notes, then more, then fewer from the top); with none, the last chord (`CHORD_LAST_TYPE`,
   `CHORD_LAST_ROOT`) stays. On-bass chords (`CHORD_FLAGS` bit 1) keep a separate bass root.
5. **Voice.** `Chord_ApplyCurrentChord` voices the chord from `Chord_Tables`: the type's note count and four
   intervals (`ChordTables_TypeNoteCount`, `ChordTables_TypeIntervals`) above the root, sounded between G3 and
   F#4 (`ChordTables_PitchMask`), and a bass note between A1 and G#2. It posts the chord to the display.

`notes/open4-kn5000-b/engine/probes/chord_table_check.py` (disassembly repository) checks all 292 non-zero
table entries against the voicings. For types 1-30, 40 and 41 (189 entries) the type's notes, moved to the
root, are the held set exactly (93), a subset of it (34: extra held notes are ignored) or a superset (44: an
incomplete fingering, such as a 9th chord held without its fifth). The 18 entries whose notes contradict the
held set are all among the 51 with bit 7 of the offset byte set: approximations that are accepted at once.

The 41 chord types. The names are the firmware's own (`Tbl_ChordTypeNames`, 0xEFF5B9: 64 names of 5 LCD
characters, read by `SNS_LoadKeyAndChord`; type 1 shows the root alone). "Voicing" is `ChordTables_TypeIntervals`,
the notes `Chord_ApplyCurrentChord` and the sequencer's step entry use; the accompaniment does not use it (see
[Pattern transposition](#pattern-transposition)).

| type | LCD name     | voicing  | type | LCD name | voicing  | type | LCD name | voicing  |
|------|--------------|----------|------|----------|----------|------|----------|----------|
| 1    | (root alone) | 0 4 7    | 15   | "79"     | 4 7 10 2 | 29   | "9#5"    | 0 4 8 10 |
| 2    | "7"          | 0 4 7 10 | 16   | "7 b9"   | 4 7 10 1 | 30   | "b9 13"  | 0 4 9 10 |
| 3    | "Maj7"       | 0 4 7 11 | 17   | "M79"    | 4 7 11 2 | 31   | "#9 13"  | (none)   |
| 4    | "aug"        | 0 4 8    | 18   | "69"     | 4 7 9 2  | 32   | "b13"    | (none)   |
| 5    | "min"        | 0 3 7    | 19   | "m6"     | 0 3 7 9  | 33   | "b9b13"  | (none)   |
| 6    | "min7"       | 0 3 7 10 | 20   | "m b5"   | 0 3 6    | 34   | "#9b13"  | (none)   |
| 7    | "dim"        | 0 3 6 9  | 21   | "m79"    | 3 7 10 2 | 35   | "13"     | (none)   |
| 8    | "m7b5"       | 0 3 6 10 | 22   | "m69"    | 3 9 2 7  | 36   | "b13"    | (none)   |
| 9    | "mM7"        | 0 3 7 11 | 23   | "sus4"   | 0 5 7    | 37   | "7 #11"  | (none)   |
| 10   | "7sus4"      | 0 5 7 10 | 24   | "7 #9"   | 4 7 10 3 | 38   | "m7 11"  | (none)   |
| 11   | "6"          | 0 4 7 9  | 25   | "M7b5"   | 0 4 6 11 | 39   | "+7#11"  | (none)   |
| 12   | "aug7"       | 0 4 8 10 | 26   | "M7#5"   | 0 4 8 11 | 40   | "add9"   | 0 4 7 2  |
| 13   | "b5"         | 0 4 6    | 27   | "mM7b5"  | 0 3 6 11 | 41   | "madd9"  | 0 3 7 2  |
| 14   | "7 b5"       | 0 4 6 10 | 28   | "13"     | 0 4 9 10 |      |          |          |

Types 15-18, 21, 22 and 24 are voiced without the root (four tension notes). The voicings of 29 and 30 are 0 4 8 10
and 0 4 9 10, four-note subsets of 9(#5) and 7(b9,13): they are different chords from 12 and 28, recognized from
other note sets. Types 35 and 36 carry the same LCD names as 28 and 32 but are the major-seventh forms (M7(13),
M7(b13)). Types 31-39 are recognized (103 table entries) but have no voicing row: for the sequencer's step entry
their voicing is four times the root *[INFERENCE: only that consumer was traced]*; the accompaniment converts its
patterns for them like any other type.

The chord mode decides which recognizer runs. In PIANIST mode (`PANEL_STYLE+3` = 3) it is the 2,048-entry table
above. In FINGERED mode (2, and the default) `ComputeNoteBitPositi_StoreDRAM` tries each held note as the root
and looks the intervals up in `NoteMask9_ClassTable` (512 entries at 0xEEBE44): it knows types 1-27 plus add9 /
madd9, so the tension chords 28-39 are recognized in PIANIST mode only. ONE FINGER (1) has its own key rules.
*[INFERENCE]* The mapping of the AUTO PLAY CHORD dialog's three entries to `PANEL_STYLE+3` values 1-3: the dialog's
radio values and `ParamEdit_WordTable`'s order agree; the widget-to-record link was not traced.

## Pattern transposition

The rhythm-ROM patterns are written for C major. Each note of the BASS and ACCOMP 1-3 parts is converted for the
current chord when the lane writes it into its ring buffer (`AccBuf_WriteExtendedEvent` ->
`AccVoice_ConvertNoteForChord`), and again from the stored pattern note (the last byte of the 7- or 9-byte ring
record) when the chord changes (`Rhythm_CompareAndTrigger`, `RhythmEvt_FullProcess`, `Rhythm_ValidateAndSend`).
The drum parts are not converted, nor are notes of 120 (0x78) and above (`Rhythm_CheckFixedNote`). The chord is
the accompaniment's copy at 0x32D7..0x32DA (flags, type, root 1 = C .. 12 = B, bass root), written by
`AccChord_ReadAndStoreKeys`.

1. A 0x91 note carries two rule bytes. For a seventh-family chord the first applies, for a minor-family chord
   the second (`Rhythm_ChordExtSelect`): low nibble = semitones, bit 4 = down, bit 5 = drop. In IC14 the
   first moves the colour note to Bb (G, C, A or B -> Bb) and the second E to Eb (and A to Ab or G).
2. The chord type picks one of 21 rows of semitone moves per pitch class (`Rhythm_ChordRowMap`,
   `Rhythm_ChordRowMap_Acc1`, `Rhythm_ChordRowMap_Bass`; the rows are `Rhythm_ChordNoteDeltaRows`, 0xE461C2): M7
   raises Bb to B, m7 lowers E, dim snaps every note to C Eb Gb A, and so on. ACCOMP 1 has its own map that
   replaces the root with the tension (D for 9, Db for b9, D# for #9).
3. The note moves by the root (`Rhythm_TransposeNote`): up by up to the part's turnover (IC14: 6 semitones for
   the bass, 8 for the chords), otherwise down; notes at or above the part's ceiling drop by octaves.
4. The bass plays the bass root of an on-bass chord, and the root on the first note after each chord change
   (`Rhythm_BassToRoot`), within a floor (RAM 0x332E) that keeps it near the written note. With chord flag bit 0,
   every note plays the root (`Rhythm_RootOnlyNote`).

Per chord type (`python3 notes/open6-kn5000-d/accomp/probes/pattern_transpose.py --tables`): family is
`Chord_TypeFamilyTable` (0 major, 1 minor, 2 seventh, 3 dim7), row is the `Rhythm_ChordNoteDeltaRows` row each
part uses, the rule byte selector is `Rhythm_ChordExtSelect` / `Rhythm_ChordExtSelect_Bass` (0 none, 1 first byte, 2 second byte), and
"recognized from" is the union of the pitch-class sets `ChordRecog_IntervalMaskTable` maps to the type, relative to
the root.

| type | family | row (parts 16 / 32, 8, 4) | rule byte (default, bass) | recognized from |
|------|--------|---------------------------|---------------------------|-----------------|
| 1    | 0      | 0 0 0                     | 0 0                       | 0,4,7           |
| 2    | 2      | 0 0 0                     | 1 1                       | 0,4,7,10        |
| 3    | 2      | 1 1 1                     | 1 1                       | 0,4,7,11        |
| 4    | 0      | 5 5 5                     | 0 1                       | 0,4,8           |
| 5    | 1      | 0 0 0                     | 2 2                       | 0,3,7           |
| 6    | 2      | 3 3 3                     | 1 1                       | 0,3,7,10        |
| 7    | 3      | 9 9 9                     | 1 1                       | 0,3,6,9         |
| 8    | 1      | 10 10 10                  | 2 2                       | 0,3,6,10        |
| 9    | 2      | 7 7 7                     | 1 1                       | 0,3,7,11        |
| 10   | 2      | 4 4 4                     | 1 1                       | 0,5,7,10        |
| 11   | 2      | 2 2 2                     | 1 1                       | 0,4,7,9         |
| 12   | 2      | 5 5 5                     | 1 1                       | 0,4,8,10        |
| 13   | 0      | 6 6 6                     | 0 0                       | 0,4,6           |
| 14   | 2      | 6 6 6                     | 1 1                       | 0,4,6,10        |
| 15   | 2      | 0 11 0                    | 1 1                       | 0,2,4,7,10      |
| 16   | 2      | 0 12 0                    | 1 1                       | 0,1,4,7,10      |
| 17   | 2      | 1 14 1                    | 1 1                       | 0,2,4,7,11      |
| 18   | 2      | 2 15 2                    | 1 1                       | 0,2,4,7,9       |
| 19   | 2      | 8 8 8                     | 1 1                       | 0,3,7,9         |
| 20   | 1      | 10 10 10                  | 2 2                       | 0,3,6           |
| 21   | 2      | 3 16 3                    | 1 1                       | 0,2,3,7,10      |
| 22   | 2      | 8 17 8                    | 1 1                       | 0,2,3,7,9       |
| 23   | 0      | 4 4 4                     | 0 0                       | 0,5,7           |
| 24   | 2      | 0 13 0                    | 1 1                       | 0,3,4,7,10      |
| 25   | 2      | 18 18 18                  | 1 1                       | 0,4,6,11        |
| 26   | 2      | 19 19 19                  | 1 1                       | 0,4,8,11        |
| 27   | 2      | 20 20 20                  | 1 1                       | 0,3,6,11        |
| 28   | 2      | 0 0 0                     | 1 1                       | 0,2,4,7,9,10    |
| 29   | 0      | 5 5 5                     | 0 1                       | 0,2,4,8,10      |
| 30   | 2      | 0 12 0                    | 1 1                       | 0,1,4,7,9,10    |
| 31   | 2      | 0 13 0                    | 1 1                       | 0,3,4,7,9,10    |
| 32   | 2      | 5 5 5                     | 1 1                       | 0,2,4,7,8,10    |
| 33   | 2      | 0 12 0                    | 1 1                       | 0,1,4,7,8,10    |
| 34   | 2      | 0 13 0                    | 1 1                       | 0,3,4,7,8,10    |
| 35   | 2      | 1 1 1                     | 1 1                       | 0,2,4,7,9,11    |
| 36   | 2      | 1 1 1                     | 1 1                       | 0,2,4,7,8,11    |
| 37   | 2      | 6 6 6                     | 1 1                       | 0,4,6,7,10      |
| 38   | 2      | 4 4 4                     | 1 1                       | 0,3,5,7,10      |
| 39   | 2      | 5 5 5                     | 1 1                       | 0,4,6,8,10      |
| 40   | 0      | 0 11 0                    | 0 0                       | 0,2,4,7         |
| 41   | 1      | 0 16 0                    | 2 2                       | 0,2,3,7         |

The 21 rows (semitone moves per pitch class C..B; `.` = 0):

| row | C  | Db | D  | Eb | E  | F  | Gb | G  | Ab | A  | Bb | B  | effect                           |
|-----|----|----|----|----|----|----|----|----|----|----|----|----|----------------------------------|
| 0   | .  | .  | .  | .  | .  | .  | .  | .  | .  | .  | .  | .  | none                             |
| 1   | .  | .  | .  | .  | .  | .  | .  | .  | .  | .  | +1 | .  | Bb -> B (major seventh)          |
| 2   | .  | .  | .  | .  | .  | .  | .  | .  | .  | .  | -1 | .  | Bb -> A (sixth)                  |
| 3   | .  | .  | .  | .  | -1 | .  | .  | .  | .  | .  | .  | .  | E -> Eb (minor third)            |
| 4   | .  | .  | .  | +1 | +1 | .  | .  | .  | .  | .  | .  | .  | Eb, E -> E, F (sus4)             |
| 5   | .  | .  | .  | .  | .  | .  | .  | +1 | .  | .  | .  | .  | G -> G# (#5)                     |
| 6   | .  | .  | .  | .  | .  | .  | .  | -1 | .  | .  | .  | .  | G -> Gb (b5)                     |
| 7   | .  | .  | .  | .  | -1 | .  | .  | .  | .  | .  | +1 | .  | mM7                              |
| 8   | .  | .  | .  | .  | -1 | .  | .  | .  | .  | .  | -1 | .  | m6                               |
| 9   | .  | -1 | -2 | .  | -1 | -2 | .  | -1 | +1 | .  | -1 | +1 | every note to C Eb Gb A (dim7)   |
| 10  | .  | -1 | -2 | .  | -1 | -2 | .  | -1 | -2 | +1 | .  | -1 | every note to C Eb Gb Bb (m7b5)  |
| 11  | +2 | .  | .  | .  | .  | .  | .  | .  | .  | .  | .  | .  | C -> D (9th instead of the root) |
| 12  | +1 | .  | .  | .  | .  | .  | .  | .  | .  | .  | .  | .  | C -> Db (b9)                     |
| 13  | +3 | .  | .  | .  | .  | .  | .  | .  | .  | .  | .  | .  | C -> D# (#9)                     |
| 14  | +2 | .  | .  | .  | .  | .  | .  | .  | .  | .  | +1 | .  | M7(9)                            |
| 15  | +2 | .  | .  | .  | .  | .  | .  | .  | .  | .  | -1 | .  | 6(9)                             |
| 16  | +2 | .  | .  | .  | -1 | .  | .  | .  | .  | .  | .  | .  | m7(9)                            |
| 17  | +2 | .  | .  | .  | -1 | .  | .  | .  | .  | .  | -1 | .  | m6(9)                            |
| 18  | .  | .  | .  | .  | .  | .  | .  | -1 | .  | .  | +1 | .  | M7(b5)                           |
| 19  | .  | .  | .  | .  | .  | .  | .  | +1 | .  | .  | +1 | .  | M7(#5)                           |
| 20  | .  | .  | .  | .  | -1 | .  | .  | -1 | .  | .  | +1 | .  | mM7(b5)                          |

Rows 11-17 are used only by part 8 (ACCOMP 1). Worked examples: E4 of a 0x91 note with rule bytes 00 / 11 plays F4
for Dm7 and B4 for G7; G1 in the bass plays E1 for C/E; C4 in ACCOMP 1 plays B3 for A9.

Evidence: the disassembly's probe `notes/open6-kn5000-d/accomp/probes/pattern_transpose.py` re-implements the
conversion from the firmware's tables and runs it on all 245,470 IC14 pattern notes of parts 4..32 (root C): for
every type that has a conversion, the share of played pitch classes that are tones of the chord rises, never
falls (min 57.5 % -> 77.8 %, m7b5 35.0 % -> 100 %, dim 39.5 % -> 100 %; the unconverted major patterns are
72.9 %, the rest being passing and colour notes). Only v10 was read. Open: what sets `CHORD_FLAGS` / 0x32D7 bit 0
(the only path found is a song override at 0x2306); the caller of the second converter `Rhythm_TransposeWithMod`;
and whether the fast path's table, which differs from the full path's at type 7, is a firmware bug. Source:
disassembly `notes/open6-kn5000-d/accomp/README.md`, section A.

## Section switching: intro, fill-in, ending

The style-control buttons do not switch the pattern themselves. Each one sets a request bit in the style
record (panel record 0x48, `PANEL_STYLE`), which is also the button's LED. The bits are named by the
firmware's own table `DisplayStr_StyleSectionNames`:

| bit of record 0x48 | request       | set by                      |
|--------------------|---------------|-----------------------------|
| field 5 bit 1      | SYNCHRO armed | `AccStyleCtl_SynchroButton` |
| field 5 bit 2      | INTRO 1       | `AccSection_RequestIntro1`  |
| field 5 bit 3      | COUNT IN      | `AccSection_RequestCountIn` |
| field 5 bit 4      | ENDING 1      | `AccSection_RequestEnding1` |
| field 5 bit 5      | ENDING 2      | `AccSection_RequestEnding2` |
| field 5 bit 6      | FILL IN 1     | `AccSection_RequestFillIn1` |
| field 5 bit 7      | FILL IN 2     | `AccSection_RequestFillIn2` |
| field 6 bit 2      | INTRO 2       | `AccSection_RequestIntro2`  |
| field 7 bits 4-5   | VARIATION 1-4 | `PanelButton_Variation`     |

`AccStyleCtl_DispatchSectionButtons` turns a press into a request. INTRO & ENDING 1/2 give an intro while the
accompaniment is stopped and an ending while it runs. FILL IN 1/2 give a fill-in while it runs; while it is
stopped, FILL IN 2 gives a COUNT IN. A second press of a pending request cancels it, and a new request clears
the requests it excludes. START/STOP (`AccStyleCtl_StartStopButton`) acts at once and is not latched.

Each tick `SeqTick_ReadControlState` copies the request bits into the engine (`ACC_REQ_INTRO`,
`ACC_REQ_FILLIN`, `ACC_REQ_ENDING`). A newly set bit becomes a pending section
(`AccSection_LatchIntroRequests`, `AccSection_LatchFillInRequests`, `AccSection_LatchEndingRequests`). It
takes effect as follows:

- **Fill-in or intro**: at once (`AccSection_SwitchNow`), unless the button was pressed on the last beat of the
  bar (`AccSection_DeferToBarIfLastBeat`). Then it waits for the bar line, so a fill always plays from the
  current beat to a bar line.
- **Ending**: at the next bar line, unless the button was pressed on the first beat
  (`AccSection_DeferToBarUnlessFirstBeat`). Then it replaces the bar that has just started.
- **Variation change**: at the bar line.

At the bar line `AccSection_SwitchAtBarLine` picks the handler from `AccSection_BarLineSwitchTable`. An ending
beats a fill-in, and a fill-in beats an intro. A pending variation is loaded first. With the MUSIC STYLE
ARRANGER on, FILL IN 1 steps the variation down and FILL IN 2 steps it up, from VARIATION 1 to VARIATION 4.

A section plays on all six lanes (`ACC_LANES_INTRO1` .. `ACC_LANES_ENDING2`, one bit per lane). When its last
lane reaches the pattern's end marker, `Rhythm_SaveState` clears the request and the LED. After a fill-in or an
intro the accompaniment returns to the variation.

An ending does not loop: each lane stops at the end marker (`AccVoice_HandleMarker83` -> `AccVoice_ParkLaneAtEnd`),
and when all six have stopped (0x3283 bit 2) `AccTick_Main` runs `AccEnding_StopWhenSilent` each tick. When the last
ending note has been released, that routine stops the accompaniment (`AccPlayMode_StopPlayAndAcc`; only the
accompaniment, `AccPlayMode_StopAcc`, if a song plays), sends all notes off, shows the keyboard's chord again and
clears the ENDING LEDs, 0x3283 bit 2 and the section lanes.

### SYNCHRO & BREAK

The button (`PanelButton_SynchroBreak` -> `AccStyleCtl_SynchroButton`) toggles SYNCHRO (record 0x48 field 5 bit 1)
whether the accompaniment runs or not; there is no separate BREAK action. While SYNCHRO is lit, an AUTO PLAY CHORD
mode is on and no song plays or records (`AccSynchro_UpdateArmed`), the chord keys drive the transport
(`AccSynchro_OnChordKeyEvent`, for every key event from `NoteOn_EntryPoint`):

- stopped: the first chord key starts the accompaniment from the top (`AccSynchro_StartOrCancelStop` ->
  `AccPlayMode_StartAccPlayFull`);
- running: releasing every chord key stops it at the next sixteenth (`AccSynchro_StopOnChordRelease` ->
  `AccPlayMode_StopPlayAndAcc`, both transports to state 12), the break; the next chord starts it again, and a
  chord played before the stop takes effect cancels it.

SYNCHRO stays lit after a synchro start; only the button, or a song track starting (`AccSynchro_PeriodicCheck` ->
`AccSynchro_Disarm`), turns it off. Without SYNCHRO, releasing the keys does nothing. *[INFERENCE]* That "break" is
the owner's manual's word for this behaviour: the manual was not checked. `ACC_TRANSPORT_STATE` 128 / 134, which
`INTTR4_SeqAutoStart` completes at a bar end, is the sequencer's own start (0x28B2 bit 1), not the chord synchro
start. Source: disassembly `notes/open6-kn5000-d/accomp/README.md`, section B (flag bytes listed by
`scripts/analysis/kn5000_ram_bit_usage.py --tree v10 0x3283 0x332a 0x346d 0x3498 0x3499 0x346e 0x28b2`).

Sources: v10 `sequencer/accompaniment_engine.s` (`AccStyleCtl_*`, `AccSection_*`), `sequencer/seq_audio_mode.s`
(`AccSection_Latch*`, `AccSection_DeferToBar*`), `sequencer/smf_event_processor.s` (`SeqTick_ReadControlState`)
and `sequencer/rhythm_routines.s` (`Rhythm_SaveState`); the routine names come from the disassembly's
`scripts/renaming/rename_open4_accvar.sed`, whose old `AccPedal_*` names (`AccPedal_SustainOn` and its twins)
were wrong: none of them touches a pedal. The lane's notes are `notes/open4-kn5000-b/accvar/README.md`.

## Voice Assignment

The accompaniment voice-assignment subsystem (labels prefixed AccVoice_, for example `AccVoice_SlotRows` and `AccVoice_RomRecords13`) manages the mapping between accompaniment parts and tone generator voices:

### Part Types

| Part   | Function      | Description               |
|--------|---------------|---------------------------|
| Bass   | `AccBass_*`   | Single-note bass lines    |
| Chord  | `AccChord_*`  | Multi-note chord voicings |
| Rhythm | `AccRhythm_*` | Drum/percussion patterns  |

### Voice Allocation Pipeline

1. `AccVoice_SelectPartOffset` - Select the parameter offset for the current part
2. `AccVoice_ComputeParamAddr` - Calculate the voice parameter memory address
3. `AccPatch_SetVoiceParam` - Set voice parameters (instrument, volume, etc.)
4. `AccVoice_AssignPerPart` - Assign tone generator voices to the part
5. `AccVoice_SendProgChange` - Send MIDI program change for the instrument

### Part Parameters

Each accompaniment part has parameters stored at calculated offsets:

| Parameter          | Function                                                        |
|--------------------|-----------------------------------------------------------------|
| Voice/Instrument   | `AccVoice_SelectAndApplyPatch`                                  |
| Tuning             | `AccTuning_SetAllFromLookup`, `AccTuning_CopyAllPartsFromStyle` |
| Rhythm mapping     | `RhythmPart3_ProcessAccentData/4/5`                             |
| Channel assignment | `AccVoice_CheckChannelSetActive`                                |

The `AccPart_*` functions manage part data access:

| Function                           | Purpose                                     |
|------------------------------------|---------------------------------------------|
| `AccPart_InitPositionsAndBase`     | Initialize part position and base address   |
| `AccPart_GetVoiceParamOffsetTable` | Look up voice parameter offset table        |
| `AccPart_ResolveStyleAddr`         | Resolve style data address for a part       |
| `AccPart_CheckEndOfDataMarker`     | Check for end-of-data in part stream        |
| `AccPart_SelectSource`             | Select data source (keyboard, Acc1-4)       |
| `AccPart_Deactivate`               | Deactivate a part (with pedal/sync options) |

## Per-tick vectors: variation stepping, Sound Arranger, tap tempo

`Seq_DispatcherTick_Process` calls three jump vectors on every sequencer tick, in this order:

1. **`AccDir_TickVector`** (`jp AccDir_Main`) steps the VARIATION field down or up: record `0x48` `+7`
   bits 4-5 (`SndParam_Style_Variation`, RAM `0xFC61`), when the low 6 bits of RAM `0x3312` / `0x3313`
   drop to 0. It acts only while `0xFD99` bit 0 is set and the style number is below 128, and posts the
   change as panel event `0x48`/7, the same field `PanelButton_Variation` writes.
2. **`SndArg_TickVector`** (`jp AccStyle_Process`) is the **Sound Arranger**. While one of its parts is
   selected (`0x338E & 0x1F`, set from the Sound Arranger grid `AcSndArgGridBoxProc` and cleared when
   mode 17, `MD_SND_ARG`, is entered or left), it compares the sounds of the five accompaniment parts
   with their last values and writes any change into the current style's 10-byte arrangement record at
   RAM `0x1E7810 + 10 * index`, setting `0x3393` bit 0:

   | record bytes | part (record, RAM)     | step                       |
   |--------------|------------------------|----------------------------|
   | +0 / +1      | DRUM (20, `0xFBBE`)    | `SndArg_StoreDrumSound`    |
   | +2 / +3      | BASS (19, `0xFBA4`)    | `SndArg_StoreBassSound`    |
   | +4 / +5      | ACCOMP1 (16, `0xFB56`) | `SndArg_StoreAccomp1Sound` |
   | +6 / +7      | ACCOMP2 (17, `0xFB70`) | `SndArg_StoreAccomp2Sound` |
   | +8 / +9      | ACCOMP3 (18, `0xFB8A`) | `SndArg_StoreAccomp3Sound` |

   Each pair is program, then bank (bit 7 of the bank byte is kept; for BASS and the ACCOMP parts it
   comes from bit 6 of part record `+4`).
3. **`AccProcess_TapTempoTick`** ends a TAP TEMPO sequence. The tap handler (the panel code `0xA8`
   listener, `AccProcess_InlinedCode`) stores `SYSTEM_TIMESTAMP` in `TAP_TEMPO_LAST_TAP_TIME` (RAM
   `0x348E`) on each press, clamps the interval to 100..750 and posts 30000 / interval as the tempo through
   `AccProcess_PostAveragedTapTempo`. The tick vector clears the sequence (`0x3490` bit 0 and the three
   stored intervals) once 0x400 timestamp units pass after the last tap.

The names and evidence are in the disassembly repository's
`analysis/kn5000-naming/proposals-2026-10-17-generic-r1.json` and `-corrections-r1.json`.

## Accompaniment Wrapper (AccWrap)

`AccWrap_FlagSync` and `AccWrap_DispatchAndWaitSync` provide a synchronization layer:

- `AccWrap_ClearPositionAndReset` - Clear position counters and reset state
- `AccWrap_DispatchAndWaitSync` - Dispatch accompaniment events with synchronization

These ensure accompaniment state changes (start/stop, variation switch) are synchronized with the sequencer timing.

## Fade Effects

`AccompSeq_FadeOutTick` handles smooth fade-out when accompaniment stops:
- Called each tick while fade-out is active (bit 5 of state 32339 clear)
- Gradually reduces volume over multiple ticks

## Rhythm Note Dispatch

The rhythm section uses a specialized note dispatch system:

| Function                        | Purpose                                             |
|---------------------------------|-----------------------------------------------------|
| `Rhythm_NoteDispatchWrapper`    | Wrapper for rhythm note events                      |
| `Rhythm_NoteOnAfterSetup_A/B/C` | Note-on for three rhythm channels                   |
| `Rhythm_RootOnlyNote`           | with chord flag bit 0, plays every note as the root |
| `Rhythm_NoteOffMax_Dispatch`    | Note-off with part-specific dispatch (D4-D7)        |
| `DrumChannel_MapToIndexA/B`     | Map drum MIDI notes to internal indices             |

## Display Integration

`AccDisplay_RefreshIfDiskActive` refreshes the accompaniment display when disk operations are active (style loading from floppy/flash).

The `AccIll` (Accompaniment Illustration) subsystem handles the visual representation:
- `AccIllProc` - Main illustration processor
- `AccIll_HandleLowerPanelEvent` / `AccIll_HandleUpperPanelEvent` - Panel input
- `AccIll_HandleHorizSlider` / `AccIll_HandleVertSlider` - Slider controls
- `AccIll_HandleUpScroll` / `AccIll_HandleDownScroll` - Scroll navigation

## Style UI

The `StyleUI_*` labels define parameter blocks and screen layouts for the style editing interface:

| Label                           | Purpose                   |
|---------------------------------|---------------------------|
| `StyleUI_ParamBlock_BAL`        | Balance parameter display |
| `StyleUI_ParamBlock_VALUE`      | Value parameter display   |
| `StyleUI_ScreenData_Main`       | Main style screen layout  |
| `StyleUI_ScreenData_MeasCursor` | Measure cursor display    |

## Related Pages

- [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) - Overall audio architecture
- [Tone Generator]({{ site.baseurl }}/tone-generator/) - Voice synthesis hardware
- [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/) - MainCPU-SubCPU communication
- [Display Subsystem]({{ site.baseurl }}/display-subsystem/) - UI rendering

## Research Needed

- [x] ~~Decode chord recognition algorithm (which chord types are supported, how root is determined)~~ — [Chord Recognition](#chord-recognition); open: what sets `CHORD_FLAGS` bit 0
- [x] ~~Transposition of the Rhythm-ROM pattern notes to the recognized chord (root shift, chord-type note rule)~~ — [Pattern transposition](#pattern-transposition); `Note_PitchClassTable` is the note -> pitch-class map it uses
- [ ] Map the complete style data format (header, part assignments, note data encoding). The Composer style bank is now named field by field ([Floppy Disk Formats]({{ site.baseurl }}/floppy-disk-formats/#the-composer-style-bank)); the Rhythm-ROM format is on [Rhythm ROM]({{ site.baseurl }}/rhythm-rom/)
- [x] ~~Document the variation/fill-in switching state machine~~ — [Section switching](#section-switching-intro-fill-in-ending), [SYNCHRO & BREAK](#synchro--break)
- [x] ~~Analyze the bass pattern generation algorithm (how bass notes are derived from chord)~~ — the bass is converted like the other parts, plus the root rule ([Pattern transposition](#pattern-transposition))
- [ ] Document style conversion routines (`StylCnv_*`) for loading custom styles
- [ ] Map the accompaniment pedal interaction (`AccPedal_ScanVoiceSlots`)
