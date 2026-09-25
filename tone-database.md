---
layout: page
title: Tone Database (Table Data ROM)
permalink: /tone-database/
---

# Tone Database (Table Data ROM 0x830000-0x87FFEF)

The last 320 KB of the Table Data ROM's **first megabyte** — `0x830000`-`0x87FFEF` — hold the
KN5000's **tone database**: every factory
tone/voice parameter record, every drum kit, the percussion instrument bank, the wave-source
name catalogues, the envelope data pool and the drawbar organ presets. It is the largest
single data structure in the machine and the one the Sub CPU's synthesis code reads on every
program change, so it feeds the sound-emulation work directly.

As of Wave 0 of the 2026-08-07 binary-include elimination effort the whole region is
**source-built and byte-identical**: `table_data/tone_database_directory.s`,
`tone_database_records.s` and `tone_database_aux.s` in the disassembly repository replace what
used to be the right half of the raw blob `includes/initial_data.bin` (commit `f95975b`,
2,263 new labels).

> ⚠ **Correction — the Sub CPU executable is NOT at 0x830000.**
> The project long carried the claim that the Sub CPU's ~192 KB executable sits uncompressed at
> Table Data ROM 0x830000. That is **refuted**. The region is tone *data*; the Sub CPU copies it
> into its **data** window at RAM 0x50000, not into its code area at 0x400+. No byte of the Sub
> CPU executable (`kn5000_subprogram_v142.rom`) has been found anywhere in the table-data or
> custom-data images we hold. **How the Sub CPU code payload reaches the Sub CPU at runtime is
> still unresolved** — the executable is known only from its own ROM dump and from the compressed
> firmware-update image, which lands at Custom Data Flash 0x3E0000 only *after* a File Type 007
> update. See [SubCPU Payload Loading]({{ site.baseurl }}/subcpu-payload-loading/).

## Every address has a Sub-CPU alias

At boot the Main CPU routine `SubCPU_Send_Payload` ships the region across the inter-CPU link as
**five 64 KB E1 bulk transfers**:

| Main CPU source | Sub CPU destination | Size |
|:---|:---|:---|
| `0x830000` | `0x050000` | 64 KB |
| `0x840000` | `0x060000` | 64 KB |
| `0x850000` | `0x070000` | 64 KB |
| `0x860000` | `0x080000` | 64 KB |
| `0x870000` | `0x090000` | 64 KB |

`DSP_System_Init` on the Sub CPU then stores the load base `0x00050000` in **two** long
pointers, `0x045310` (the relative base added to every resolved offset) and `0x045314` (the root
pointer used to read directory slots).

The practical consequence when reading the two disassemblies side by side: **subtract 0x7E0000**
to go from a Table Data ROM address to the Sub CPU address. The Sub CPU disassembly never
mentions a `0x83xxxx` address; it sees the tone-record area at `0x0524D4`, the offset table at
`0x051B00`, and so on. Every offset stored *inside* the database is relative to the database
base, so the same 32-bit value is correct on both sides.

## The directory at 0x830000

The first 256 bytes are a directory: 48 four-byte little-endian slots at `+0x00`..`+0xBC`,
followed by a scalar area at `+0xC0`..`+0xFF` read as 16-bit words. Sub-CPU code never
hard-codes a structure address; it reads `(ToneDB_RootPtr)[slot]` and adds `ToneDB_RelBase`.

| slot | target | role (consumer noted where identified) |
|:---|:---|:---|
| `+0x04` | `ToneDB_BankMap_Main` | preset tone-lookup path (bank map + tone-number banks) |
| `+0x08` | `ToneDB_ToneOffsetTable` | the 629-entry tone-record offset table |
| `+0x0C` / `+0x10` / `+0x14` | `ToneDB_ToneIndexMapA` / `...MapB` / `ToneDB_PercSourceIndexMapA` | `WaveSel_StageA1` index tables for tone families 0x00+0xC0 / 0x80 / 0x40 |
| `+0x18` / `+0x1C` / `+0x20` | `ToneDB_MixerDefaultTable` (twice) / `ToneDB_PercMixerDefaultTable` | 11-byte per-tone records; length taken from stride word `+0xEA` (`+0xF0` for family 0x40) |
| `+0x24` / `+0x28` / `+0x2C` | `ToneDB_ToneIndexMapC` / `...MapD` / `ToneDB_DrumToneIndexMap` | `WaveSel_StageA2` index tables, same three families |
| `+0x30` / `+0x34` / `+0x38` | `ToneDB_EnvDescTable` (all three) | 15-byte envelope/modulation descriptors; strides `+0xEC` and `+0xF2` |
| `+0x44` / `+0x48` / `+0x4C` | `ToneDB_SourceIndexMapA` / `...MapB` / `ToneDB_PercSourceIndexMapB` | `DSP_RouteCoeffs_TypeA` row-index tables (selectors 00/11, 10, 01) |
| `+0x50` / `+0x54` | `ToneDB_SourceNameList1` / `ToneDB_SourceList1_Footer` | wave catalogue A + its `DSP_AlgoCoeffLookup` bank 0 footer |
| `+0x58` / `+0x5C` / `+0x60` | `ToneDB_SourceIndexMapC` / `...MapD` / `ToneDB_PercSourceIndexMapC` | `DSP_VoiceCoeffRoute2` row-index tables |
| `+0x64` / `+0x68` | `ToneDB_SourceNameList2` / `ToneDB_SourceList2_Footer` | wave catalogue B + bank 1 footer |
| `+0x6C` | `ToneDB_BankMap_Coeff` | coefficient-path bank map — sole consumer `ToneDB_Find_ToneRecord_CoeffPath` |
| `+0x70` | `DrawbarPreset_EnvDescTable` | 4 alternate 15-byte descriptors |
| `+0x74` / `+0x7C` | `DrumKit_NoteMapA` / `DrumKit_NoteMapB` | drum note→instrument maps |
| `+0x78` | `PercInst_000_Silent` | base of the 610 percussion-instrument records (stride `+0xEE`) |
| `+0x80` / `+0x84` | `ToneDB_DrumSourceNameList` / `ToneDB_DrumList_Footer` | wave catalogue C + bank 2 footer |
| `+0x88` | **scalar 338** | DSP1 stream-index bias — see below |
| `+0x8C` / `+0x90` | `ToneDB_PercSourceNameList1` / `ToneDB_PercList1_Footer` | sub-unit wave catalogue + bank 3 footer |
| `+0x94` / `+0x98` | `ToneDB_PercSourceNameList2` / `ToneDB_PercList2_Footer` | pair-mode wave catalogue + bank 4 footer |
| `+0x9C` / `+0xA0` / `+0xA4` | aliases of `ToneDB_ToneIndexMapC` / `...MapD` / `ToneDB_DrumToneIndexMap` | `WaveSel_StageA2` alt-mode (`ToneGen_GlobalFlags` bit 2) |
| `+0xAC` | `ToneDB_DefaultLayerParams` | 81-byte fallback layer parameter block |
| `+0xB0` | `PercName_Pack` | packed 10-char percussion source names |

Slots `+0x00`, `+0x3C`, `+0x40`, `+0xA8`, `+0xB4`, `+0xB8`, `+0xBC` are `0xFFFFFFFF` (unused).

The scalar tail carries the record strides the Sub CPU uses as **copy lengths**:

| word | value | meaning |
|:---|:---|:---|
| `+0xEA` | 11 | wave-select record stride, tone families 0x00 / 0x80 / 0xC0 |
| `+0xEC` | 15 | set-descriptor stride, same families |
| `+0xEE` | 58 | drum-instrument (percussion) record stride |
| `+0xF0` | 11 | wave-select record stride, family 0x40 |
| `+0xF2` | 15 | set-descriptor stride, family 0x40 |

Words `+0xD0`, `+0xD4`, `+0xD8`, `+0xE0`, `+0xE8` hold values (3, 3, 3, 28, 426) that **no
reader in the v1.42 Sub CPU image touches** — recorded but unexplained.

## Program-change lookup: bank map → tone number → offset table

`ToneDB_Find_PatchRecord` (Sub CPU) is presented with a bank selector byte and a program number:

1. the selector indexes the 128-byte `ToneDB_BankMap_Main` (`0x830100`), yielding a bank byte `b`;
2. `b` selects one of **11 banks of 128 LE16 tone numbers** at `ToneDB_ToneNumBanks_Main`
   (`0x830180`-`0x830C7F`) — tone number = `u16[base + (b*128 + program)*2]`;
3. the tone number indexes `ToneDB_ToneOffsetTable`; the record address is
   `ToneDB_Base + entry`.

Only selectors that the routine explicitly admits reach that path: `≤ 0x07`, `0x40`, `0x41` and
`0x70`. Selectors `0x10`, `0x15`, `0x50` and `0x55` are diverted before the table walk to
RAM-resident user/edit banks instead, and anything else falls back to record 0. The factory bank
map agrees: the only **mapped** selectors are `0x00`-`0x07` → banks 0-7, `0x40`/`0x41` → banks
8/9 and `0x70` → bank 10; the rest of the 128-byte map is zero. (Selector `0x00` maps to bank 0,
so its byte is `0x00` too and the map alone cannot distinguish it from an unmapped selector — the
`cps bc,7` gate in `ToneDB_Find_PatchRecord` is what admits it.)

A parallel path, `ToneDB_Find_ToneRecord_CoeffPath`, performs the identical walk through
`ToneDB_BankMap_Coeff` (`0x830C80`) and its **14 banks** at `0x830D00`-`0x831AFF` (bytes 0..13),
with **no bank-validity filter and no fallback to record 0**. The two halves are cleanly
separated by content: the Main banks only ever name tone numbers 0-337, the Coeff banks only
311-628.

## The 629-entry tone-record offset table (0x831B00)

`ToneDB_ToneOffsetTable` is 629 LE32 values, each an offset from the database base. It is the
structure `DSP1_ResolveStreamPtr` indexes, and it is the spine of the whole database.

`DSP1_ResolveStreamPtr` takes a *stream index* in WA and:

```
XHL  = 0x50000                       ; ToneDB base (Sub CPU view)
XBC  = word[XHL + 0x88]              ; the bias, 338 (0x152)
WA   = WA + BC                       ; biased index
XBC  = word[XHL + 0x08]              ; 0x1B00, the offset-table offset
XDE  = XHL + XBC + 4*WA
XHL  = XHL + long[XDE]               ; resolved record pointer
```

So the **`+0x88` bias word means table index = caller's stream number + 338**. Its only three
call sites are in `DSP_Reinit_VoiceSlots`, which follows each resolution with a `0xD5`-word
(426-byte) block copy into the DSP1 image — 426 being exactly the largest record size, so short
records are deliberately over-read into their successor.

Index bands, as they fall out of the table:

| indices | what they point at |
|:---|:---|
| 0-309 | tone records at `0x8324D4`-`0x845EBD` (reached with *negative* stream numbers, −338..−29) |
| 310-335 | the 26 drum-kit records (`0x86363C`+, in the auxiliary area) |
| 336-337 | the two drawbar organ presets (`0x8706BD`, `0x870867`) |
| 338-377 | stream numbers 0-39 — all forty are maximum-size 426-byte 5-block records |
| 378-399 | stream numbers 40-61 — every entry is offset `0x24D4`, i.e. an alias of record 0, "Piano" |
| 400-628 | stream numbers 62-290 — the GM-style bank, `0x846016`-`0x851701`, ending in "Gun Shot" |

629 entries resolve to only **607 distinct offsets** and **387 distinct names**: aliasing is
normal here (the 22 unused live slots above, plus GM duplicates such as six consecutive
"Telephone" entries).

## Tone/voice record layout

579 variable-length records tile `0x8324D4`-`0x855A47` with no gaps or padding.

| offset | size | field |
|:---|:---|:---|
| `+0x00` | 16 B | display name, ASCII, **space-padded on both sides** (`"     Piano      "`) |
| `+0x10` | 5 B | layer-configuration field; byte 4 is `0x55` in all 579 records |
| `+0x15` | 81 B | COMMON block — begins `0x81 0x40` in all 579 records |
| `+0x66` | 81 B × 0..4 | further LAYER blocks, one per additional layer |

Record length is therefore `21 + 81·N`, and the only sizes that occur are **102, 183, 264, 345
and 426 bytes** (N = 1..5). No explicit size field was found: a record's length is implied by
the distance to the next referenced offset.

Field semantics are only partially decoded. What is settled, from sibling records that differ in
one known property:

* layer block `+19` is a semitone offset — `"Piano"` = 66, `"Piano 1 Octave"` = 54,
  `"Piano 2 Octave"` = 42, i.e. 12 per octave (block offsets `+48`/`+73` track it);
* layer block `+54`, `+55`, `+62`, `+69` differ between `"Piano"` and `"Bright Piano"`, so they
  are timbre/filter-related.

The `+0x10` layer-configuration field is **not** a plain layer count: its four 2-bit sub-fields
are only ever 0 or 1, and their popcount matches the block count for just 311 of the 579 records.
Its real meaning is unresolved.

## The auxiliary tables (0x855A48-0x87FFEF)

Everything the directory points at that is not a tone record lives in this tail. It is fully
tiled — the structure map below is the module's own, and each entry's directory slot is known:

| address | structure | shape | dir |
|:---|:---|:---|:---|
| `0x855A48` | `ToneDB_DefaultLayerParams` | 81 B | `+0xAC` |
| `0x855A99` | `ToneDB_ToneIndexMapA` | 1024 × LE16 | `+0x0C` |
| `0x856299` | `ToneDB_ToneIndexMapB` | 1024 × LE16 | `+0x10` |
| `0x856A99` | `ToneDB_MixerDefaultTable` | 337 × 11 B | `+0x18`/`+0x1C` |
| `0x857914` | `ToneDB_EnvDescTable` | 487 × 15 B | `+0x30`/`+0x34`/`+0x38` |
| `0x85959D` | `ToneDB_ToneIndexMapC` | 1024 × LE16 | `+0x24`/`+0x9C` |
| `0x859D9D` | `ToneDB_ToneIndexMapD` | 1024 × LE16 | `+0x28`/`+0xA0` |
| `0x85A59D` | `ToneDB_DrumToneIndexMap` | 1024 × LE16 | `+0x2C`/`+0xA4` |
| `0x85AD9D` | `ToneDB_VelocityCurve_0..5` | 6 × 128 B | — |
| `0x85B09D` | `ToneEnv_*` data chunks | 974 blobs, 32,732 B | — |
| `0x863079` | `DrumKit_*` records | 26 × 295 B | — |
| `0x864E6F` | `PercInst_*` records | 610 × 58 B | `+0x78` |
| `0x86D8A3` | `DrumKit_NoteMapA` | 4096 × LE16 | `+0x74` |
| `0x86F8A3` | `ToneDB_PercMixerDefaultTable` | 142 × 11 B | `+0x20` |
| `0x86FEBD` | `ToneDB_PercSourceIndexMapA` | 1024 × LE16 | `+0x14` |
| `0x8706BD` | `DrawbarPreset_Jazz` / `_Rock` | 2 × 426 B | — |
| `0x870A11` | `DrawbarPreset_EnvDescTable` | 4 × 15 B | `+0x70` |
| `0x870A4D` | `DrawbarPreset_EnvData_0..2` | 8,772 B | — |
| `0x872C91` | `ToneDB_SourceNameList1` | 333 × 16 B | `+0x50` |
| `0x874161` | `ToneDB_SourceIndexMapA` | 1024 × LE16 | `+0x44` |
| `0x874961` | `ToneDB_SourceIndexMapB` | 1024 × LE16 | `+0x48` |
| `0x875161` | `ToneDB_SourceList1_Footer` | 17 B | `+0x54` |
| `0x875172` | `ToneDB_SourceNameList2` | 339 × 16 B | `+0x64` |
| `0x8766A2` | `ToneDB_SourceIndexMapC` | 1024 × LE16 | `+0x58` |
| `0x876EA2` | `ToneDB_SourceIndexMapD` | 1024 × LE16 | `+0x5C` |
| `0x8776A2` | `ToneDB_SourceList2_Footer` | 17 B | `+0x68` |
| `0x8776B3` | `ToneDB_PercSourceNameList1` | 141 × 16 B | `+0x8C` |
| `0x877F83` | `ToneDB_PercList1_Footer` | 14 B | `+0x90` |
| `0x877F91` | `ToneDB_PercSourceIndexMapB` | 1024 × LE16 | `+0x4C` |
| `0x878791` | `ToneDB_PercSourceNameList2` | 144 × 16 B | `+0x94` |
| `0x879091` | `ToneDB_PercSourceIndexMapC` | 1024 × LE16 | `+0x60` |
| `0x879891` | `ToneDB_PercList2_Footer` | 14 B | `+0x98` |
| `0x87989F` | `ToneDB_DrumSourceNameList` | 424 × 16 B | `+0x80` |
| `0x87B31F` | `ToneDB_DrumList_Footer` | 3 B | `+0x84` |
| `0x87B322` | `DrumKit_NoteMapB` | 4096 × LE16 | `+0x7C` |
| `0x87D322` | `PercName_Pack` | 610 × 10 chars | `+0xB0` |
| `0x87EAF6` | unused fill | 5,370 B of `0xFF` | — |

### Wave-source name catalogues

Five `{name list → index maps → footer}` groups have the same shape: a list of **16-byte rows**
(13-character source name + three id/flag bytes whose meaning is *not yet decoded*), one or two
1024-entry LE16 index maps, and a footer whose first LE16 is the list's record count followed by
small per-category subdivision counts. Catalogue A (`ToneDB_SourceNameList1`, 333 rows) and
catalogue B (`ToneDB_SourceNameList2`, 339 rows) are the same list, B adding six entries (Samba
Whistle, Wind Chime, Orch.Gong, MetronomeBell, Metronome Tap, Silent). The names are PCM source
names — "Piano L", "Piano R", and so on — i.e. this is the closest thing in the ROM to a
**catalogue of the waveform sources**, which makes it the natural place to look for the
still-unresolved wave-selection index (see [Tone Generator]({{ site.baseurl }}/tone-generator/)).

The cross-index bounds all check out, which is how the pairings were established: index maps
A/B top out at 332/331 against a 333-entry list; C/D at 338/337 against 339; the percussion maps
at 141/140 and 143 against lists of 141 and 144.

Two of the three trailing bytes of a row are now read: **bytes +14/+15 are the row's own
selector pair** (program, bank-family), and the name index maps are the **exact inverse** of
their catalogue — look a row's own selector up as `(bank & 0x0F) × 128 + (program & 0x7F)` in
the map its family's bits 7:6 pick, and the map returns that row, for 333/333, 339/339,
141/141 and 144/144 rows. The same holds on the SX-WSA1R's tone database, where prom_c's
readers compute exactly that index
([SX-WSA1 overview]({{ site.baseurl }}/wsa1/#prom_d-is-a-tone-database-and-it-is-the-kn5000s-design)).
Re-derive both with `tools/tone_db_index_map_inverse_check.py` in this repository.

### Drum kits and percussion

* **26 drum-kit records**, 295 bytes each: 16-char name + 279 parameter bytes. Kits 0-13 are the
  first bank ("Standard Kit" … "MSP Kit"), 14-25 the second ("Standard Kit" … "Sound Effect
  Kit"). Only about 19 parameter bytes differ between kits — per-note assignment lives elsewhere.
* **`DrumKit_NoteMapA` / `NoteMapB`**, 32 slots × 128 MIDI notes of LE16 indices into the
  percussion records (0 = Silent). Bank B is nearly identical to bank A with slot 15 cleared.
* **610 percussion-instrument records**, 58 bytes each: 13-char name, 3 header bytes, then two
  21-byte layer blocks that are byte-identical in 609 of the 610 records.
* **`PercName_Pack`** (`0x87D322`): 610 names packed at a fixed **stride of 10 characters with no
  terminators** (short names are space-filled). Entries 0-423 are abbreviations, in order, of the
  424-entry `ToneDB_DrumSourceNameList`; entries 424+ are mostly blank with a band of
  sound-effect names near the end (Applause, Helicopter, Train, Gun Shot, …, Fret Noise).
  610 is exactly the percussion-record count, which is how the two were matched.

### Drawbar presets

Two 426-byte records, `"<Jazz Drawbars> "` and `"<Rock Drawbars> "`, reachable as offset-table
indices 336 and 337. They use the maximum 5-block record size and are followed by four
15-byte envelope descriptors of their own (`DrawbarPreset_EnvDescTable`, directory slot `+0x70`,
flag byte `0x92`, null A-offset) selecting three shared envelope blobs.

### Envelope material

`ToneDB_EnvDescTable` is 487 records of 15 bytes: a flag byte, two database-relative LE32
offsets (A and B), and six parameter bytes. All 974 offsets are distinct and exactly tile the
`ToneEnv_*` region `0x85B09D`-`0x863078` — which is how the 974 variable-length chunks were
delimited in the first place. Larger chunks are built from 6-byte segments of the form
`70 00 xx xx xx NN` with `NN` incrementing, consistent with rate/level envelope segment lists.

Suggestive but **unproven**: 487 descriptors here plus the 142 records of
`ToneDB_PercMixerDefaultTable`'s sibling group equal 629, the offset-table entry count. That
would mean one descriptor per tone, but no consumer has been traced that makes the correspondence
explicit.

## What is still open

* **Field-level semantics of the 81-byte blocks.** Only the semitone offset and a handful of
  timbre bytes are identified. Nothing here is yet good enough to synthesise a tone from the
  record alone.
* **The `+0x10` layer-configuration field** does not decode as a layer count.
* **The three id/flag bytes** in every 16-byte wave-catalogue row are unidentified — the obvious
  candidate for a wave-ROM selector, but that is a hypothesis, not a finding.
* **The `ToneDB_MixerDefaultTable` naming is provisional.** The aux module reads the 11-byte
  records as per-tone mixer/controller power-on defaults (three level bytes then four LE16
  controller values); the directory comment describes the same records from the consumer side as
  "wave-select records", because `VoiceSubSlot_Init` copies `word[dir+0xEA]` = 11 bytes of them
  into a per-sub-slot staging area. Both readings fit the structure; neither is proven.
* **Five directory scalar words have no reader** in the v1.42 Sub CPU image.
* **The Sub CPU code-payload source path** (see the correction at the top of this page).

This region being source-built says nothing about the wider effort: three wave-groups of the
binary-include audit are still pending (the HD-AE5000 data ROM and Sub-CPU boot data, the v7
firmware tree, and a final sweep including the Main-CPU inline `.byte` audit). See
[ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/).

## Provenance

* `table_data/tone_database_directory.s` — directory, bank maps, tone-number banks, the
  629-entry offset table (`0x830000`-`0x8324D3`).
* `table_data/tone_database_records.s` — the 579 tone/voice records (`0x8324D4`-`0x855A47`).
* `table_data/tone_database_aux.s` — everything from `0x855A48` to the `0xFF` fill at
  `0x87FFEF`.
* One-time deterministic generators, kept for provenance: `scripts/generators/gen_tonedb_directory.py`,
  `gen_tonedb_records.py`, `gen_tonedb_aux.py`. The `.s` files are the authoritative source.
* Boot transfer: `v10/maincpu/kn5000_v10_program.s`, `SubCPU_Send_Payload`.
* Sub-CPU consumers: `v142/subcpu/kn5000_subprogram_v142.s` — `DSP_System_Init`,
  `DSP1_ResolveStreamPtr`, `DSP_Reinit_VoiceSlots`, `ToneDB_Find_PatchRecord`,
  `ToneDB_Find_ToneRecord_CoeffPath`, `ToneDB_Resolve_NamedToneRecord`, `VoiceSubSlot_Init`.
* Audit record: `analysis/binclude-audit-2026-08-07/` (`findings.json`, `PLAN.md`,
  `WAVE-STATUS.md`).

## Related Pages

- [Table Data ROM]({{ site.baseurl }}/table-data-rom/) — the rest of the 2 MB ROM
- [Tone Generator]({{ site.baseurl }}/tone-generator/) — the IC303 the records ultimately drive
- [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) — overall audio architecture
- [SubCPU Payload Loading]({{ site.baseurl }}/subcpu-payload-loading/) — the boot transfer
- [Sound Categories]({{ site.baseurl }}/sound-categories/) — how the UI groups these tones
