---
layout: page
title: "KN6000 / KN6500 Program Data & GUI"
permalink: /kn6000-program-data/
---

# KN6000 / KN6500 / HD-SX6: the program data and the screens

Like the KN7000, the SX-KN6000 and SX-KN6500 draw every screen from MILK widget records: **7,145**
(KN6000 v7.1) and **7,203** (KN6500 v1.3), instances of 449 / 451 self-describing classes. Besides
the GUI, the program flash carries the built-in Music Stylist (1,000 / 1,080 setups, each pointing
at a one-touch setting), the accompaniment's note-conversion tables, the factory panel memories, a
fallback "Technics Rhythms" style and "Technics Pads" bank, twelve demo songs, thirteen bitmaps,
and on the KN6000 the built-in sound tables. Since 2026-10-29 the disassembly writes all of it as
typed source. This page summarises how; the [disassembly trees]({{ site.baseurl }}/kn6000-disassembly/)
page says how the images are rebuilt.

The images use the KN7000 tree's tools, given a profile, not copied
(`../kn7000/tools/gen_data_s.py --profile kn6000|kn6500|hdsx3`), so the
[KN7000 Menu Map]({{ site.baseurl }}/kn7000-menu-map/) and
[Program Data Region]({{ site.baseurl }}/kn7000-data-region/) pages describe the method. The lane
notes in the disassembly repository are the reference:

- [`kn6000/notes/data-region.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn6000/notes/data-region.md)
  (lane sib-kn6000: the GUI, the registry, the first typed structures);
- [`kn6000/notes/siblings-data-final/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn6000/notes/siblings-data-final/README.md)
  (lane siblings-final: the reader-typed passes, the Music Stylist, the hash tables);
- [`kn2400/notes/data-region/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn2400/notes/data-region/README.md)
  and [`hdsx3/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/hdsx3/README.md)
  (lane sib-kn2400: the HD-SX6 plug-in).

| model  | data region (file)   | CPU            | RAM-init image (ROM -> RAM)          |
|--------|----------------------|----------------|--------------------------------------|
| KN6000 | `0x176037..0x3F47EC` | `0x4C176037..` | `0x4C3ED870 -> 0x50000010`, `0x6F7C` |
| KN6500 | `0x176839..0x37E44C` | `0x4C176839..` | read from its crt0 the same way      |

Each tree's `src/program/data/` holds `data.s` and `data_NN.s` (the region in address order),
`gui_classes.inc`, `gui_ids.inc`, `gui_code_ids.inc`, `functions.sym`, `labels.sym`, `code_refs.txt`,
the rhythm and tone macros, and `media/`. `make data-and-code-src` regenerates the data and the
code alternately until nothing the code reads changes (2 or 3 rounds); `make verify` keeps the image
byte-identical.

## The MILK object system: the KN5000's registry

`RegisterObjectTable` (KN6000 v7.1 `0x4C01D198`) copies the 16-byte `{class, proc, u16 count, u16
pad, table}` record to `0x5024BE58 + 16 * slot`. The tables are grouped by **kind**, as in the
KN5000's NAKA framework, not by block as on the KN7000:

| slots            | kind                                   | registered by      |
|------------------|----------------------------------------|--------------------|
| `0x000 + V`      | Viewable (one per screen group)        | InitializeUserNN   |
| `0x100 + N`      | Function                               | InitializeUserNN   |
| `0x120 + N`      | ApFunction                             |                    |
| `0x140 + N`      | MainFunction                           |                    |
| `0x160 + N`      | Class                                  |                    |
| `0x180 + N`      | ResEvent                               |                    |
| `0x1A0 + N`      | ResMethod                              |                    |
| `0x1C0`          | SupportClass                           | InitSptClassTable  |
| `0x1E0`, `0x1F0` | Mode, Title                            | InitModeTitleTable |
| `0x200 + V`      | ResName, parallel to Viewable V        |                    |
| `0x300 + N` ...  | the names of the three function tables |                    |

An id is `(slot << 16) | index`, as on the KN7000. Eleven modules register tables
(`InitializeUser00` .. 18; the others are empty stubs). The class records are the KN7000's and so
is the aligned field layout, but the type alphabet differs: the older firmware has no `\`, so its
`]` `^` `_` are the KN7000's `\` `]` `^` (flag, colour, border) and its `m`..`w` the KN7000's
`l`..`v`. `kn6000/notes/data-region-probes/sigmap.py` pairs the fields of every same-named class of
KN6000 v7.1 and KN7000 941: 591 pairs, one KN7000 character per KN6000 character. With the
translation, selfsize and allsize hold for all 449 / 451 classes and every link checks.

The records are written as on the KN7000: one macro per class, links as object names, the tree as
indentation, X / Y / W / H, `CL_` / `BD_` / `ES_` / `VF_` names from the firmware's own tables,
`TT_` / `MD_` / `FN_` ids by name. A Viewable table is named `V_<its first root object's ResName>`
(the KN6000 has no OT blocks). `functions.sym` gives the code the firmware's own name of each
procedure a MILK Function table lists: 551 names on the KN6000, where `gen_symbols.py` had found
only 21 of those tables.

## The menu maps

| model  | map                                                                                                                                 | objects | Viewable tables | top-level objects | titles |
|--------|-------------------------------------------------------------------------------------------------------------------------------------|---------|-----------------|-------------------|--------|
| KN6000 | [`kn6000/notes/gui-menu-map.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn6000/notes/gui-menu-map.md) | 7145    | 188             | 673               | 241    |
| KN6500 | [`kn6500/notes/gui-menu-map.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn6500/notes/gui-menu-map.md) | 7203    | 188             | 680               | 241    |
| HD-SX6 | [`hdsx3/notes/gui-menu-map.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/hdsx3/notes/gui-menu-map.md)   | 999     | 1               | 67                | 3      |

(The figures are each map's own header.) `make -C <tree> gui-map` regenerates a map and
`make verify-gui-map` checks it; the gates run it.

## What else the program flash holds

| structure                    | KN6000 / KN6500                               | evidence                                                                                                             |
|------------------------------|-----------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| demo songs (36 zlib streams) | both: 12 songs x record / events / panel bank | the floppy describers type them (song record `0x870` bytes on the KN6000); `.zlib 6` re-compresses byte-exactly      |
| `TechnicsRhythmsResource`    | `0x4C359AC0` / `0x4C2E5304`                   | IC18's format, one style " 8 Beat 1"; `func_4C0557E9` falls back to it when the table ROM's resource does not check  |
| bitmap resources (13 / 13)   | both                                          | procedures answering `MT_GetBitmapData` / `Width` / `Height` / `Palette` / `MT_GetBitCount`; indexed PNG             |
| `ToneRecordDirectory`        | KN6000 `0x4C3E5FD4` (2,475 entries)           | `func_4C07C26A`: record index -> address when no archive is loaded; tone, TABLE-tone and voice records               |
| `FactoryPanelMemory`         | `0x4C32BE24` / `0x4C2B7668`, 13 banks x 8     | `func_4C03D431` / `func_4C03D5A1` copy it (`0x2D8D0` bytes) and the `.PMT` header to the backup RAM                  |
| `TechnicsPadsResource`       | `0x4C35FF84` / `0x4C2EB7C8`                   | `TechnicsPadsResourceInit` keeps it and calls `TechnicsPadsResourceParse` when the table flash's copy does not check |
| JPEG / BMP files             | 3                                             | whole files                                                                                                          |

**The KN6500 does have factory panel memories.** The first notes on these images said the KN6500's
program flash had no panel banks; that was wrong. `func_4C03D5A1` copies `func_4C03D5A1_Table` (the
`.PMT` header) and then `0x2D8D0` bytes from `0x4C2B7668` to the backup RAM `0x840007C2` /
`0x840007D2`, as the KN6000's `func_4C03D431` copies its own. `FactoryPanelMemory`
(`kn6500_manual.sym`) is now typed: 13 banks x 8 memories, 186,576 bytes (the "Soloist Sounds",
"PAd", "PZA" ... runs), as `PMR_*` lines ([Panel Memory Records]({{ site.baseurl }}/kn7000-panel-memory/)).

### The Music Stylist setups and their one-touch settings

`StyleRecordTable` is the KN7000's 24-byte `MusicStylistSetup` record, field for field: 1,000 records
at `0x4C3DF8EC` (KN6000), 1,080 at `0x4C36F724` (KN6500). The KN6000's field readers:

| field            | reader                                                                                          |
|------------------|-------------------------------------------------------------------------------------------------|
| `+0 panel`       | `func_4C16B6B5_entry_L43` loads it and calls `func_4C04C476`, which hands it to `func_4C04C58C` |
| `+4 name`        | `MssNameFunc_L121` (`0x4C1637F8`), strncpy 16                                                   |
| `+8 genre`       | `func_4C1640C8`: `StyleGenreTable` + genre * 8                                                  |
| `+10 style`      | `func_4C1640C8`: the genre's style list + style * 8                                             |
| `+12 setup`      | `func_4C1649B6`, `func_4C164AAC`                                                                |
| `+14 era`        | `func_4C165A19`, `cmp 0xffff, d1`                                                               |
| `+16 era_pos`    | `func_4C16619A`: `LibDiv32` by 9, page and row                                                  |
| `+18 letter`     | `func_4C164F3F`: `StyleAlphabetTable` + letter * 8                                              |
| `+20 letter_pos` | `func_4C164F3F`, `func_4C1655C7`                                                                |

The `panel` record is the one-touch-setting record that the CUSTOM banks also hold, `0x90` bytes
here (`func_4C04C552`, KN6500 `func_4C04C6C2`, answers `0x90`). `func_4C04C58C` merges it into
`0x84000036..` through the same triple tables (`func_4C04B9F8_entry_L4f_Table`) that the CUSTOM
writer `func_4C04B9F8` uses. Each record is typed with the one-touch macros (`PM_PART` x 3,
`PM_ENTRIES`, `PM_PART`, `PM_RHYTHM`, `PM_SET77`, `PM_FX`, `PM_SET88`, `PM_SET8C`) and labelled
`StylePanel_<setup name>_<n>`. `PM_RHYTHM` is the new macro: where a CUSTOM setting has its slot, a
built-in one has the style's 24-bit rhythm id, low byte first. KN6000 999 records (143,856 bytes),
KN6500 1,080.

### The note-conversion rules

`NoteConvRules` (KN6000 `0x4C3850BC`, KN6500 `0x4C3108F8`) is 128 x 8 bytes, `{is_melody, alt_chord,
no_third_adj, no_transpose, table}`. Its reader, `func_4C05805C`, is the KN7000's `func_48436229`
instruction for instruction: it adds `4 + (type - 1) * 12`, or `4 + (type - 1) * 0x90 + (root - 1) *
12`, then note % 12, and reads a signed byte. The tables are the KN7000's `NoteConvTable` {name;
s8 deltas}, 492-byte melody and 4,900-byte chord tables: on the KN6000 21 tables, about 50 KB (the
"chord tables" of the first notes).

### The built-in sound hash tables (KN6000)

The KN6000 v7.1 holds three multiplicative hash tables of the shape of the table flash's 'JK' voice
archive, with absolute pointers: a `{u16 mult, u16 nbuckets}` descriptor, the buckets, then chains
of `{u32 next, key, payload}`. The readers are used when no archive is loaded (when `func_4C07B982`
answers neither 1 nor 2). Each takes `key * mult % nbuckets` (`func_4C09B1EC`), walks the chain
comparing `+4` and answers the payload:

| descriptor         | address      | buckets | entries x size | key                                                         | lookup           |
|--------------------|--------------|---------|----------------|-------------------------------------------------------------|------------------|
| `ToneKeyHashDesc`  | `0x4C3E8680` | 1,139   | 1,896 x 20     | `MSB << 16 \| LSB << 8 \| program` (`ToneKeyFind`)          | `ToneKeyLookup`  |
| `ShortKeyHashDesc` | `0x4C3E9850` | 1,907   | 2,898 x 12     | a panel switch, `group << 8 \| number` (`SoundSwNoBankGet`) | `ShortKeyLookup` |
| `BankKeyHashDesc`  | `0x4C3EC6A0` | 1,139   | 1,375 x 12     | `MSB << 16 \| LSB << 8 \| program` (`SoundBankIndexGet`)    | `BankKeyLookup`  |

`kn6000/notes/siblings-data-final-probes/hash_chains.py` checks every key against its bucket (0
misplaced). These 89,196 bytes were the "past the tone directory" region of the first notes.

**The payloads** (lane mn10300-formats, 2026-10-31, [`kn7000/notes/mn10300-formats/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/mn10300-formats/README.md), section 2). `hash_payloads.py` shows
which payload bytes carry values, and the routines that read them (named in `kn6000_manual.sym`) say
what they are; the bytes nobody reads are 0 in every entry, the macros' trailing `.space`:

| payload macro       | fields, from their readers                                                                                                                                                                                                                                         |
|---------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `TONE_KEY_PAYLOAD`  | +0 u16 `tone` (`SoundToneIndexGet`), +2 `icon` (`SoundIconGet`; `MainGetSoundName` answers it for `MT_GetSoundIcon`), +3 / +4 `swgroup01` / `swgroup23`, +5..+8 `swno0`..`swno3` (`SoundSwNoGet`: the panel switch {group, number} for the reference's state 0..3) |
| `SHORT_KEY_PAYLOAD` | the bank `msb`, `lsb` and `program` the switch selects (`SoundSwNoBankGet` copies +0 / +1 / +2 to its three outputs)                                                                                                                                               |
| `BANK_KEY_PAYLOAD`  | the u16 `index` `SoundBankIndexGet` answers                                                                                                                                                                                                                        |

So `ToneKeyHash` maps a sound to its icon, tone and panel button, and `ShortKeyHash` maps a button back
to its sound. `swgroup01` takes 0..15 and `swno0` / `swno1` 0..39 (the panel's sound groups),
`swgroup23` 0..31 and `swno2` / `swno3` 0..127 (bank-and-program style numbers) *[INFERENCE on what
the two pairs of states are]*. The KN7000's 'Tone' hash has the same 12-byte payload; its readers were
not traced.

### zlib's tables and field names (lane mn10300-formats)

Lane mn10300-formats named zlib 1.0.4's 19 data tables, found by
their contents, in this tree's manual symbol file too (`cplens`, `cplext`, `static_l_desc`,
`inflate_mask`, `z_errmsg` ...), and the record macros' fields are now named after what the code does
with them: 525 of the KN6000's 1,330 fields have a name, against 30 before (KN6500: 523 of 1,331)
(`field_names_census.py`). The method and every tree's figures are on
[KN7000 Program Data Region]({{ site.baseurl }}/kn7000-data-region/#field-names-from-their-use).

## The HD-SX6 plug-in

The expansion board's `XAPR` plug-in ([which board]({{ site.baseurl }}/kn6000-disassembly/#the-xapr-plug-in-hd-sx3-or-hd-sx6))
makes no direct call into the keyboard. Every host call is

```
mov (0x979126B4), aN / mov (0x100C, aN), aN / mov (OFF, aN), aM / calls (aM)
```

`0x979126B4` holds the registry base and `+0x100C` is the table pointer of slot `0x100`, the
KN6000's block-0 Function table at `0x4C32923C` (422 entries), so OFF / 4 is the function index:
`0xEC` `RegisterObjectTable`, `0x278` `RegisterTitle`, `0xA8` DrawBox (77 calls), `0x2D8`
GetClientBox (55), `0x25C` MainFuncCall (34), `0x108` SendEvent (29), 41 offsets in all
(`kn2400/notes/data-region-probes/plugin_registry.py`). With them the plug-in registers its own
tables:

| slot  | kind         | count | table        |
|-------|--------------|-------|--------------|
| 0x168 | Class        | 55    | `0x978B0740` |
| 0x077 | Viewable     | 999   | `0x978B1F44` |
| 0x277 | ResName      | 999   | `0x978B2EE4` |
| 0x108 | Function     | 52    | `0x97912378` |
| 0x128 | ApFunction   | 44    | `0x979118EC` |
| 0x148 | MainFunction | 7     | `0x97912520` |
| 0x188 | ResEvent     | 47    | `0x9791211C` |
| 0x1A8 | ResMethod    | 100   | `0x979121E0` |

and the title `0x77` = `TT_HDDEXT`, whose screen is `HDD_MAIN_MENU`. The tables at `0x9791xxxx` are
in the plug-in's initialised RAM, copied from `0x978B3E84` (`0x26D8` bytes, `func_97800082`). Its 55
classes use the NAKA alphabet and derive from KN6000 classes, so the generator builds the KN6000's
model first. Two link checks fail, both in the plug-in's own data: object 11's `next` is its child
14, and object 137's `next` is the orphan 138. Its three pictures (`BitmapBg001`, `BitmapBg002`,
`BitmapDirsel`) are 640 x 240, 8 bits, with a 256-entry `0x00BBGGRR` palette.

## Blocks a routine is handed

Most reader-row pieces were blocks whose address the code only passes to a routine. Since lane
callee-walk (2026-10-30,
[`kn7000/notes/callee-walk/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/callee-walk/README.md))
the walk follows the address into that routine, through register and stack arguments
([calling convention]({{ site.baseurl }}/kn7000-firmware/#calling-convention)), and the block is
written as a record of what the routine reads, `REC_<routine>_Arg<slot>`, with a header naming the
routine, the argument and the call ([KN7000 Program Data Region]({{ site.baseurl }}/kn7000-data-region/#blocks-a-routine-is-handed)).
The siblings' walk had more to gain: it kept a register at a join only when every path agreed, had no
return-value rule, and entered a jump table's cases knowing nothing, so a switch that selects a
descriptor per case (`mov data_X, a1` / `bra Join`) and returns it reached the call as "unknown". It
now has the KN7000 extended walk's frame slots (narrowed: a slot gives back only a data address, a
parameter, or NULL into an address register), address joins and return sets, and so the switches'
descriptors are records too (`func_4C026B6B_Selected` ...).

Measured against disassembly `2a7b45be5` (`kn7000/notes/callee-walk-probes/callee_walk_stats.py`;
n / bytes; "pointed" counts every record a pointer leads to, the new switch selections included):

| tree     | address-only rows before | after         | all rows before | after         | callee records | pointed before | pointed after |
|----------|--------------------------|---------------|-----------------|---------------|----------------|----------------|---------------|
| `kn6000` | 339 / 17,838             | 151 / 11,022  | 378 / 18,109    | 188 / 11,275  | 31 / 696       | 2571 / 42,931  | 2861 / 50,844 |
| `kn6500` | 345 / 17,958             | 156 / 11,138  | 384 / 18,229    | 193 / 11,391  | 31 / 696       | 2549 / 42,801  | 2839 / 50,714 |
| `hdsx3`  | 30 / 228                 | 25 / 177      | 40 / 266        | 34 / 211      | 131 / 1,048    | 17 / 19,340    | 155 / 20,444  |

With the walk on, the KN6000 types 15,951 more bytes of its data region (2,408,017 -> 2,423,968), the
KN6500 15,953 and the plug-in 89 (`callee_off_on.py --profile P`); 29 bytes per keyboard that a reader
table or a record head held are reader rows now, because a record the new joins find claims a different
extent. On the KN6000 the 151 address-only blocks left are kept as rows because the routine only stores
the pointer (69 / 1,028 bytes), hands it to a library routine (52 / 2,015), the address reaches no call
the walk sees (24 / 7,839), the routine's reads are lost inside it (4 / 112), it hands the pointer on
(1 / 20), or the record would overlap another item (1 / 8); the KN6500's split is the same within a few
pieces. The opaque bytes fell too, KN6000 70,137 -> 65,733, KN6500 74,371 -> 69,967, plug-in 3,133 ->
3,103: bytes declared unread were records' tails.

## Pointers, arrays and loops (lane mn10300-typer)

Lane mn10300-typer (2026-10-31, [`kn7000/notes/mn10300-typer/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/mn10300-typer/README.md)) changed the shared typer for every MN10300 tree: a
32-bit field is a pointer into code only where it lands on the first byte of an instruction (a length
decoder, `kn7000/tools/mn10300_insn_len.py`, walks the code from its known entry points; 0 disagreements
with the assembler in any tree), a pointer loop proven to stop at an address ends the array it walks, a
loop's counter is an index, a block a routine steps through is an array of records, and a chain a loop
walks is typed record by record. The rules and the KN7000's figures are on
[KN7000 Program Data Region]({{ site.baseurl }}/kn7000-data-region/#pointers-arrays-and-loops-lane-mn10300-typer).
Here (`typer_stats.py`, all rules off against all on, the same inputs; n / bytes):

| tree   | typed before | typed after | change  | reader rows before | after       | opaque before   | opaque after    |
|--------|--------------|-------------|---------|--------------------|-------------|-----------------|-----------------|
| kn6000 | 2,424,027    | 2,436,905   | +12,878 | 185 / 11,215       | 142 / 9,370 | 2,833 / 65,733  | 2,347 / 54,782  |
| kn6500 | 1,935,342    | 1,948,203   | +12,861 | 190 / 11,331       | 147 / 9,486 | 2,849 / 69,967  | 2,364 / 59,027  |
| hdsx3  | 481,868      | 482,118     | +250    | 34 / 211           | 34 / 211    | 98 / 3,103      | 98 / 2,981      |
A few bytes that an over-long table held before (32 on the KN6000, 35 on the KN6500, 6 on the HD-SX3)
are now rows or fill: the `0xFFFFFFFF` terminators after some tables, whose loop stops before them. The kernel's routine after `KernelInitHook` is `KernelTickIsrDefault`
([KN6000 Disassembly]({{ site.baseurl }}/kn6000-disassembly/#the-two-program-images)); since it is a
function now, its call names an entry, one more routine without a header in the doc-quality census.
## What is left: the census

The fourth committed snapshot of `scripts/analysis/data_incbin_census.py`,
[`docs/coverage/data-incbin-2026-10-30-04.txt`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/docs/coverage/data-incbin-2026-10-30-04.txt)
(measured at `b84f732aa`, committed in `a25c88274`; its rows for these trees are those of `-03`, measured at `a9b5cf764` after lanes media-files, code-island and callee-walk merged; count / bytes; *from media* is the part of *generated* made from a PNG by a committed converter):

| tree     | generated    | from media   | media      | opaque        | generic n | generic bytes | opaque in `-02` |
|----------|--------------|--------------|------------|---------------|-----------|---------------|-----------------|
| `kn6000` | 80 / 137,020 | 80 / 137,020 | 3 / 28,660 | 2833 / 65,733 | 0         | 0             | 3197 / 70,137   |
| `kn6500` | 83 / 137,404 | 83 / 137,404 | 3 / 28,660 | 2849 / 69,967 | 0         | 0             | 3213 / 74,371   |
| `hdsx3`  | 3 / 309,200  | 3 / 309,200  | 0 / 0      | 98 / 3,103    | 0         | 0             | 101 / 3,133     |

The opaque fall from `-02` is lane callee-walk's ([above](#blocks-a-routine-is-handed)). The current
snapshot, [`docs/coverage/data-incbin-2026-10-31-02.txt`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/docs/coverage/data-incbin-2026-10-31-02.txt) (measured at `6ca33e656`, committed in `c58fe3de7`), reads generic 0 and opaque `kn6000` 2347 / 54,782, `kn6500` 2364 / 59,027
and `hdsx3` 98 / 2,981, the other columns unchanged: lane mn10300-typer's work
([above](#pointers-arrays-and-loops-lane-mn10300-typer)).

Before the work the trees held 2,630,724 (KN6000), 2,140,036 (KN6500) and 533,544 (plug-in) generic
bytes; after lanes sib-kn6000 and sib-kn2400, 797,489 / 901,823 / 6,623; in the first snapshot
(`data-incbin-2026-10-30-01`, after lane siblings-final) 18,810 / 18,930 / 266 bytes in 380 / 386 /
40 pieces, with opaque 3336 / 79,522, 3346 / 83,667 and 101 / 3,133. Lane generic-zero (snapshot `-02`, disassembly `141313939`;
`c04e41079` for the KN6000 / KN6500, `c65a62c5b` for the plug-in;
`kn6000/notes/siblings-data-final/README.md`, section "generic-zero") took all three to 0. Every
generic piece had a reader, so none could stay a binary include or be declared opaque:

- **Records.** `record_start()` stops a record that the walk reads past its first bytes from being
  taken for a short string; the KN6000's `func_4C02CA6A_Records_p0` records (`func_4C02CBDA_Records_p0`
  on the KN6500), before a run of guessed strings, are typed records now. The opaque bytes fell
  with them (79,522 -> 70,137 and 83,667 -> 74,371): bytes declared unread were the records' tails.
- **Reader rows.** Every other piece is written as rows at the width and signedness of the reads
  that land in it (`tab_u8` ... `tab_u32`), address words as `.long Label` / `Label+N`, under a
  header naming the readers (counts below). Most are "address only taken": the code loads the
  piece's address into a register or passes it to a routine. On the KN6000, `data_4C1A04AC` is
  now 2,240 bytes of u8 rows whose address `func_4C055ED9_L43` loads as a base; the table at
  `0x4C176EA8` is the 16-colour table of `VwUserBitmapProc` (u32 `0x00BBGGRR` rows; since lane
  callee-walk `DrawBitmapSPFast16_Impl_entry_Le0_Table`, typed from the routine it is passed to); empty strings handed to
  strcpy are `.asciz ""`. The plug-in's are coordinate words (`0x500014` = x `0x14`, y `0x50`)
  passed to the host's drawing routines through `calls (a2)`, and 10 strings.
- **The kernel's tail.** The two pieces of the code file outside every range (115 + 586 bytes)
  are typed: `FirmwareVersionByte`, the kernel's version string, `KernelServiceHash`,
  `KernelRamLayout`, `KernelParams`, and the kernel's two interrupt dispatchers as code (see
  [KN6000 / KN6500 / HD-SX Disassembly]({{ site.baseurl }}/kn6000-disassembly/)). Lane code-island
  (2026-10-30) named the kernel routines beside them after the KN7000's flash tail (`KernelInit`,
  `KernelWaitRelease` ... `KernelInitHook`) and turned the sibling generator's last `.byte` escapes
  into instructions.

What the reader-row pieces were after lane generic-zero, by tree
(`kn7000/notes/data-final-probes/reader_rows_stats.py`; lane callee-walk's figures since are
[above](#blocks-a-routine-is-handed)):

| tree     | read at a width (n / bytes) | address only taken (n / bytes) | strings (n) | total n | total bytes |
|----------|-----------------------------|--------------------------------|-------------|---------|-------------|
| `kn6000` | 5 / 129                     | 339 / 17,838                   | 34          | 378     | 18,109      |
| `kn6500` | 5 / 129                     | 345 / 17,958                   | 34          | 384     | 18,229      |
| `hdsx3`  | 0 / 0                       | 30 / 228                       | 10          | 40      | 266         |

A reader row kept the **reader's** widths, not the callee's layout, because the walk did not carry
an argument into the routine that reads it; lane callee-walk changed that
([above](#blocks-a-routine-is-handed)), and the rows left say why in their headers.

Opaque means that the reader search found no load, store, base or call argument in the bytes. The
biggest on these images: records `03 00 00 00 00 00 00 00 f0 c0 05 ff ff ff 04 ...` (3,927 bytes at
`0x4C398C2B` / `0x4C3244AF`), the tail of a pointed record kind with small 0..13 values (3,888
bytes), `{0, pointer}` word pairs whose pointers lead into gaps, and on all four MILK siblings a
1,525-byte high-entropy block followed by the JPEG zig-zag order (*[INFERENCE]* the JPEG decoder
library's constant tables).

## Open

- ~~The hash tables' payloads past their first field, and the key of the short-key table~~: read from
  their readers ([above](#the-built-in-sound-hash-tables-kn6000)); what the two pairs of switch states
  mean is still *[INFERENCE]*.
- The one-touch bytes the macros keep as hex.
- The code reaches many tables with computed offsets; their bounds come from the labels the code
  names, so a table can still be split in two.
- The plug-in's entry vectors' roles.
- Blocks the callee walk cannot follow: a pointer a routine stores (a timer, a registry, a queue),
  library copies. (Arrays indexed by a loop counter are followed since lane mn10300-typer.) The siblings' walk has the KN7000 extended walk's
  slots, joins and return sets, not its other rules (pointer-from-a-field returns, loop bodies keeping
  slots, bounds); the whole extended walk, tried on the KN2400, typed less.
- *[INFERENCE]* What the kernel's hash keys, RAM layout words and u16 parameters mean.
