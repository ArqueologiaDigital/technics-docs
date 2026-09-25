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
| `+0x0C` / `+0x10` / `+0x14` | `ToneDB_ToneIndexMapA` / `...MapB` / `ToneDB_PercSourceIndexMapA` | `WaveSel_StageA1` index tables for tone families 0x00+0xC0 / 0x80 / 0x40: selector pair → velocity-split record |
| `+0x18` / `+0x1C` / `+0x20` | `ToneDB_MixerDefaultTable` (twice) / `ToneDB_PercMixerDefaultTable` | 11-byte **velocity-split records** (the labels are historical); length taken from stride word `+0xEA` (`+0xF0` for family 0x40) |
| `+0x24` / `+0x28` / `+0x2C` | `ToneDB_ToneIndexMapC` / `...MapD` / `ToneDB_DrumToneIndexMap` | `WaveSel_StageA2` index tables, same three families: selector pair → multisample SET |
| `+0x30` / `+0x34` / `+0x38` | `ToneDB_EnvDescTable` (all three) | 15-byte **multisample SET descriptors** (the label is historical); strides `+0xEC` and `+0xF2` |
| `+0x44` / `+0x48` / `+0x4C` | `ToneDB_SourceIndexMapA` / `...MapB` / `ToneDB_PercSourceIndexMapB` | `DSP_RouteCoeffs_TypeA` row-index tables (selectors 00/11, 10, 01): selector pair → catalogue row, the exact inverse of the catalogue |
| `+0x50` / `+0x54` | `ToneDB_SourceNameList1` / `ToneDB_SourceList1_Footer` | wave catalogue A + its `DSP_AlgoCoeffLookup` bank 0 footer |
| `+0x58` / `+0x5C` / `+0x60` | `ToneDB_SourceIndexMapC` / `...MapD` / `ToneDB_PercSourceIndexMapC` | `DSP_VoiceCoeffRoute2` row-index tables |
| `+0x64` / `+0x68` | `ToneDB_SourceNameList2` / `ToneDB_SourceList2_Footer` | wave catalogue B + bank 1 footer |
| `+0x6C` | `ToneDB_BankMap_Coeff` | coefficient-path bank map — sole consumer `ToneDB_Find_ToneRecord_CoeffPath` |
| `+0x70` | `DrawbarPreset_EnvDescTable` | 4 SET descriptors for the drawbar records (flags 0x92) |
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
| `+0xEA` | 11 | velocity-split record stride, tone families 0x00 / 0x80 / 0xC0 |
| `+0xEC` | 15 | set-descriptor stride, same families |
| `+0xEE` | 58 | drum-instrument (percussion) record stride |
| `+0xF0` | 11 | velocity-split record stride, family 0x40 |
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

579 variable-length records tile `0x8324D4`-`0x855A47` with no gaps or padding. A record is
`21 + 81·N` bytes (102, 183, 264, 345 or 426). No explicit size field exists: the length is
the distance to the next referenced offset.

The layout below is read from the Sub CPU code that uses each field (Wave 2, lane `tonedb`;
v1.42 addresses). Each record's header in `table_data/tone_database_records.s` names the
bank/program that selects it.

| offset | field | reader(s) |
|:---|:---|:---|
| `+0x00` | 16-char name, space-padded on both sides | |
| `+0x10` | **part-mode byte**. `& 0xC0`: 0x00 = the four-partial melodic path (every record in this file), 0x40 = drawbar records, 0x80 = drum kits, 0xC0 = silent. Bit 4 selects a level-pair variant | `Voice_SetVelocity` (0x02C8E4); `Voice_Calc_LevelPair_PatchAtk` |
| `+0x11` | **partial mask**: partial *p* (0..3) is present iff `+0x11 & {0x01, 0x04, 0x10, 0x40}[p]` | `VoiceBuf_TypeSelector_MatchEpilogue`, `EFFSlotScan_AssignPath` |
| `+0x12` | bits 1:0 tested (0 in every record) | `Partial_Build_Present_Word` |
| `+0x13` | bend type (0 ×573, 4 ×6) | `Voice_Pitch_Compute_Inactive` |
| `+0x14` | 0x55 in all 579; only its address is taken | |
| `+0x15` | 81-byte **COMMON block**, cut into ten groups by its readers: octave-shift nibble (+0x29), two nibble indices (+0x2A), four 4-byte entries (+0x2B+4k), level offset (+0x5C), algorithm type (+0x5D), partial-descriptor bytes (+0x5E..+0x61), secondary parameters (+0x64/+0x65) | see the file header |
| `+0x66` | *N*−1 81-byte **PARTIAL blocks**, in rank order; an absent partial is bound to `ToneDB_DefaultLayerParams` (dir `+0xAC`) | `Voice_Build_Register_Set`, `Voice_Release_Type4` |

`popcount(+0x11 & 0x55)` equals *N*−1 in 542 of the 579 records. The other 37 are
staging-stream records. The earlier reading of `+0x10`-`+0x14` as one 5-byte
"layer-configuration field", whose popcount matched the block count in 311 records, measured
bytes that are not the mask. Each partial block is cut into seven field groups by its
readers. Its **`+0x02`/`+0x03` bytes are the wave-select pair**
(`WaveSel_StageA1_FromPatchBlock`) that starts the chain [below](#wave-selection-end-to-end).
The sibling-record observation still holds: partial-block byte `+19` changes by 12 per
octave ("Piano" 66, "Piano 1 Octave" 54, "Piano 2 Octave" 42).

Bytes with no reader found are listed in the file header: common block `+0x15`..`+0x28`
(except the drum-kit pairs), most of `+0x3B`..`+0x5B`, `+0x62`/`+0x63`; partial block
`+0x01`, `+0x04`, `+0x06`, `+0x12`, `+0x1D`..`+0x26`, `+0x38`, `+0x48`. The partial-block map
comes from a heuristic dataflow probe
(`notes/tonedb-2026-09-25/partial_block_reads.py --chains`) plus reading the code by hand, so
it is a lower bound.

## The auxiliary tables (0x855A48-0x87FFEF)

Everything the directory points at that is not a tone record lives in this tail. It is fully
tiled — the structure map below is the module's own, and each entry's directory slot is known:

| address | structure | shape | dir |
|:---|:---|:---|:---|
| `0x855A48` | `ToneDB_DefaultLayerParams` | 81 B, the partial block used when a partial is absent | `+0xAC` |
| `0x855A99` | `ToneDB_ToneIndexMapA` | 1024 × LE16 | `+0x0C` |
| `0x856299` | `ToneDB_ToneIndexMapB` | 1024 × LE16 | `+0x10` |
| `0x856A99` | `ToneDB_MixerDefaultTable` | 337 velocity-split records × 11 B | `+0x18`/`+0x1C` |
| `0x857914` | `ToneDB_EnvDescTable` | 487 SET descriptors × 15 B | `+0x30`/`+0x34`/`+0x38` |
| `0x85959D` | `ToneDB_ToneIndexMapC` | 1024 × LE16 | `+0x24`/`+0x9C` |
| `0x859D9D` | `ToneDB_ToneIndexMapD` | 1024 × LE16 | `+0x28`/`+0xA0` |
| `0x85A59D` | `ToneDB_DrumToneIndexMap` | 1024 × LE16 | `+0x2C`/`+0xA4` |
| `0x85AD9D` | `ToneDB_VelocityCurve_0..5` | 6 × 128 B **key→band tables** (the name is a misnomer) | — |
| `0x85B09D` | `ToneSet_NNN_KeyMap` / `ToneSet_NNN_Zones` | 974 chunks, 32,732 B: each SET's key map and zone records | — |
| `0x863079` | `DrumKit_*` records | 26 × 295 B | — |
| `0x864E6F` | `PercInst_*` records | 610 × 58 B | `+0x78` |
| `0x86D8A3` | `DrumKit_NoteMapA` | 4096 × LE16 | `+0x74` |
| `0x86F8A3` | `ToneDB_PercMixerDefaultTable` | 142 velocity-split records × 11 B | `+0x20` |
| `0x86FEBD` | `ToneDB_PercSourceIndexMapA` | 1024 × LE16 | `+0x14` |
| `0x8706BD` | `DrawbarPreset_Jazz` / `_Rock` | 2 × 426 B | — |
| `0x870A11` | `DrawbarPreset_EnvDescTable` | 4 SET descriptors × 15 B | `+0x70` |
| `0x870A4D` | `DrawbarPreset_EnvData_0..2` | 8,772 B of drawbar zone records (9 × 9 × 9) | — |
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

The 974 chunks were labelled `ToneEnv_RecNNN_A` / `_B` until September 2026 and described as
envelope segment lists. They hold no envelope data. The rename is
`scripts/renaming/rename_tonedb_set_chunks.sed`.

## Wave selection, end to end

How a note on a melodic part becomes a recording selector for the tone generator, all in the
v1.42 Sub CPU:

```
partial block +0x02 (wave) / +0x03 (family/sub-bank)          WaveSel_StageA1_FromPatchBlock
  -> StageA1 index map, dir +0x0C / +0x10 / +0x14              WaveSel_StageA1_IndexLookup (0x032469)
       index = (family & 0x0F) * 128 + (wave & 0x7F); map chosen by family bits 7:6
  -> velocity-split record, dir +0x18 / +0x1C / +0x20 (11 B)
       3 ascending velocity thresholds +0..+2 -> zone 0..3       Velocity_Select_Split_Zone (0x022824)
       zone z's pair: wave +3+2z, family +4+2z                   WaveSel_StageA2_FromVelZone (0x0328B5)
  -> StageA2 index map, dir +0x24 / +0x28 / +0x2C  -> SET number WaveSel_StageA2_FindSetDesc (0x032750)
  -> SET descriptor, dir +0x30 (15 B): key map, zone records, key range, root, base pitch
  -> key map: band = keytable[(pitch >> 8) & 0x7F]; zone = map[+4 + band]
  -> zone record (4 or 6 B): +0 LE16 recording selector (class << 12 | entry)
       copied verbatim to tone-generator register +0x040         WaveSel_StageB_Build_Reg040 (0x023849)
```

`7F 7F 7F` thresholds mean a single velocity zone. Record 10, `59 6D 7F`, has three. Zone
records also carry an output-level field select (+2, into TG register +0x080), a fine pitch trim
(+3, 1/256 semitone) and, for 6-byte records only, a coarse pitch trim (+4, 8.8 semitones).

**SET descriptors** (`ToneDB_EnvDescTable`, 487 × 15 B): `+0` flags, `+1` key-map offset,
`+5` zone-records offset, `+9`/`+0x0A` lowest/highest key, `+0x0B` root key, `+0x0C` LE16 base
pitch (8.8 log semitones, the units of TG register +0x400), `+0x0E` unidentified. Flags bit 7
selects the 6-byte zone stride and bit 0 a reserve level. Bit 1 is the "pitch trap": in 13 SETs
the portamento stage ignores root and base pitch, so anything that computes
`base pitch − pivot` for them invents +49…+65 semitones. Records 0-340 are melodic SETs and
341-486 percussion SETs (reached only from `ToneDB_DrumToneIndexMap`). Censuses:
`analysis/wave7-probes/probe_set_descriptors.py`.

Still unknown: what a selector's class nibble means at the chip; descriptor `+0x0E` and flags
bit 3 (the searches made are listed in the source header); which drawbar levels feed the three
base-9 digits of the drawbar zone records. The same directory layout exists in the SX-WSA1's
tone database (prom_d), and the velocity-split reading is a candidate framing to test there.

### Wave-source name catalogues

Five `{name list → index maps → footer}` groups have the same shape: a list of **16-byte rows**
(13-character source name + three id bytes), one or two 1024-entry LE16 index maps, and a footer
whose first LE16 is the list's record count followed by small per-category subdivision counts.
Catalogue A (`ToneDB_SourceNameList1`, 333 rows) and catalogue B (`ToneDB_SourceNameList2`, 339
rows) are the same list, B adding six entries (Samba Whistle, Wind Chime, Orch.Gong,
MetronomeBell, Metronome Tap, Silent). The names are PCM source names — "Piano L", "Piano R",
and so on.

**The index maps are exact inverses of the catalogues.** A row's bytes `+14`/`+15` are a
selector pair (sel_program, sel_bank_family), the same kind of pair a partial block carries at
`+0x02`/`+0x03`. Looking that pair up in the catalogue's own name map, at index
`(sel_bank_family & 0x0F) × 128 + (sel_program & 0x7F)`, returns the row's own number, for every
row:

| catalogue | rows inverted | through | best other map (control) |
|:---|---:|:---|---:|
| `+0x50` `ToneDB_SourceNameList1` | **333 / 333** | `+0x44` / `+0x48` | 7 |
| `+0x64` `ToneDB_SourceNameList2` | **339 / 339** | `+0x58` / `+0x5C` | 8 |
| `+0x8C` `ToneDB_PercSourceNameList1` | **141 / 141** | `+0x4C` | 16 |
| `+0x94` `ToneDB_PercSourceNameList2` | **144 / 144** | `+0x60` | 16 |

The row one past each catalogue's count does *not* invert, which confirms the counts. So the
name maps answer "which catalogue row names this selector pair", and the catalogue is how the
firmware names a wave. The promcd lane proved the same property on the SX-WSA1's tone database
(prom_d: 307/307, 314/314, 208/208, 161/161) with
`notes/lanes/promcd-2026-09-25/prom_d_index_maps.py`, and reported the KN5000 figures. That
committed script covers prom_d only. The KN5000 figures above were re-derived for this page
with the check below; it should be committed beside the prom_d one.

```python
import struct   # run in kn5000-roms-disasm
T = open('original_ROMs/kn5000_table_data.rom', 'rb').read(); B = 0x30000   # dir at 0x830000
S = lambda slot: B + struct.unpack_from('<I', T, B + slot)[0]
mp = lambda slot: [struct.unpack_from('<H', T, S(slot) + 2*i)[0] for i in range(1024)]
for cat, n, fam in [(0x50, 333, {0x00: 0x44, 0xC0: 0x44, 0x80: 0x48}), (0x64, 339, {0x00: 0x58, 0xC0: 0x58, 0x80: 0x5C}),
                    (0x8C, 141, {0x40: 0x4C}), (0x94, 144, {0x40: 0x60})]:
    rows = [T[S(cat) + 16*i:][:16] for i in range(n)]
    ok = sum(1 for i, r in enumerate(rows) if r[15] & 0xC0 in fam
             and mp(fam[r[15] & 0xC0])[(r[15] & 0x0F) * 128 + (r[14] & 0x7F)] == i)
    print(hex(cat), ok, '/', n)
```

### Drum kits and percussion

* **26 drum-kit records**, 295 bytes each: a kit is a tone record with part mode 0x80. Kits
  0-13 are the first bank ("Standard Kit" … "MSP Kit"), 14-25 the second ("Standard Kit" …
  "Sound Effect Kit").
* **Per-note assignment**: from `+0x27`, 128 `{wave, slot}` byte pairs, one per MIDI note.
  `ToneDB_Find_SubToneRecord` / `ToneDB_Resolve_NamedToneRecord` turn note *n*'s pair into a
  percussion record, `DrumKit_NoteMapA[slot][wave]`. The independent name path
  (`DSP_SetVoiceCoefficients`, through `DrumKit_NoteMapB` into `PercName_Pack`) names the
  same instrument for 3,236 of the 3,328 kit notes. The rest differ only in numbering
  ("Scratch 3" / "Scratch 2"). The source now names the instrument on every note.
* **General MIDI layout, but not everywhere.** Kits 14-17, 19 and 20 (bank selector 0x41) put
  hi-hats on notes 42/46 and a crash on 49, the GM layout. No bank-0x40 kit does. A MAME/HLE
  drum map should use the ROM's per-kit note table, not GM.
* **610 percussion-instrument records**, 58 bytes each: 13-char name, 3 header bytes, then two
  21-byte layer blocks. Layer bytes `+0x03`/`+0x04` are tune (`Voice_Pitch_CopyBase`) and
  `+0x0F`..`+0x14` the drum-voice filter.
* **`PercName_Pack`** (`0x87D322`): 610 names at a fixed **stride of 10 characters with no
  terminators**. Entries 0-423 are abbreviations, in order, of the 424-entry
  `ToneDB_DrumSourceNameList`.
* Kit `+0x11` (values 0..6) and the constant head `+0x12..+0x26` have no reader found.

Evidence: `python3 notes/tonedb-2026-09-25/drum_chain_probe.py`.

### Drawbar presets

Two 426-byte records, `"<Jazz Drawbars> "` and `"<Rock Drawbars> "`, offset-table indices
336 and 337, part mode 0x40. They use the same field layout as the other tone records, with
four partial blocks mapped directly. They are followed by four SET descriptors of their own
(`DrawbarPreset_EnvDescTable`, directory slot `+0x70`, flags 0x92). The three
`DrawbarPreset_EnvData_*` blobs are 9 × 9 × 9 drawbar zone records, not segment lists.

## What is still open

* **Unread tone-record bytes**, listed [above](#tonevoice-record-layout), and the meaning of
  the four 4-byte entries +0x2B.. (only entries 0-3 have a reader).
* **Selector class nibble**: what the top four bits of a zone record's selector mean at the
  tone generator.
* **SET descriptor `+0x0E`** and flags bit 3 have no reader in v1.42.
* **The third id byte** (`+13`) of each 16-byte catalogue row is unidentified. `+14`/`+15`
  are the selector pair, as above.
* **Five directory scalar words and the directory tail `+0xD0..+0xE8`** have no reader in the
  v1.42 Sub CPU image.
* **The Sub CPU code-payload source path** (see the correction at the top of this page).

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
* Wave 2 (September 2026), lane `tonedb`: `notes/tonedb-2026-09-25/README.md` lists the
  probes (`drum_chain_probe.py`, `partial_block_reads.py`, `style_record_field_map.py`) and the
  row-rewriting tools. The lane report is
  `notes/lanes/wave2-2026-09-25/lane-reports/tonedb.json`. Census for the four files:
  KNOWN-B 436,514 → 7,863 bytes.

## Related Pages

- [Table Data ROM]({{ site.baseurl }}/table-data-rom/) — the rest of the 2 MB ROM
- [Tone Generator]({{ site.baseurl }}/tone-generator/) — the IC303 the records ultimately drive
- [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) — overall audio architecture
- [SubCPU Payload Loading]({{ site.baseurl }}/subcpu-payload-loading/) — the boot transfer
- [Sound Categories]({{ site.baseurl }}/sound-categories/) — how the UI groups these tones
