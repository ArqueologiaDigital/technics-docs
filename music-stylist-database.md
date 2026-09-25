---
layout: page
title: Music Stylist Preset Database
permalink: /music-stylist-database/
---

# Music Stylist Preset Database (Table Data ROM)

The 198,000-byte block at **0x951000-0x98156F** in the Table Data ROM is the factory
database behind the KN5000's **MUSIC STYLIST** button: exactly **1000 records of 198
bytes**, laid out as a flat grid with no directory of its own. It is reached through two
1000-entry pointer tables at 0x986000 and 0x987000.

Earlier passes over this ROM described the block loosely as "~970 x 198 B style records"
and called the two pointer pages "model-specific preset tables". Both descriptions are
retired: the record count is exactly 1000, and the table selection is on the current UI
state, not on a model code (see [Which table, and when](#which-table-and-when)).

The block is now assembled from source in
`table_data/style_records.s` and `table_data/style_record_ptr_tables.s`, both generated
once by `scripts/generators/gen_style_records.py` and byte-verified against the ROM.

Companion pages: [Table Data ROM]({{ site.baseurl }}/table-data-rom/) for the region map
this block sits in, [Panel Memory Factory Data]({{ site.baseurl }}/panel-memory-factory-data/)
for the other factory-registration block in the same ROM.

## The firmware's own words

The Music Stylist front page is built by the widget module
`maincpu/ui_widgets/naka_perf_style.c`, and its labels state the size of the database
directly:

| widget | text |
|:---|:---|
| `w160_text` | `Music Stylist` |
| `w161_text` | `> 1000 Styles of World wide Music !` |
| `w162_text` | `> Style explorer by Genre` |
| `w163_text` | `> Alphabetical style select` |
| `w164_text` | `STYLE EXPLORER` |
| `str_898` | `Explore 1000 Musical Styles with the Music Stylist.` |

`str_898` sits at main-CPU ROM **0xE14C86** in all three dumped firmware versions
(v7, v9, v10). The five help databases carry the same claim in prose -- the English one
reads "The Music Stylist is your guide to 1000 musical styles in the KN5000."

### Terminology

The English help database describes the hierarchy the records implement:

> Style Explorer lets you find different styles by musical category, with each category
> showing you descriptive sub categories. Each sub category has four different styles,
> each with a descriptive name.

So in Technics' own vocabulary the three name fields of a record are **category**
(10 of them), **sub category** (250), and **style** (1000, four per sub category). The
assembly source uses the older working names *style name* for the sub category and
*arrangement name* for the style; the symbol prefix is `StyleRec_`.

## Grid geometry

| property | value |
|:---|:---|
| first record | `StyleRec_000` @ `0x951000` |
| grid stride | 198 bytes |
| record count | 1000 (`StyleRec_000`..`StyleRec_999`) |
| declared record length | 197 (the `.long` at +0x00); the 198th byte is uncommitted padding |
| last record | `StyleRec_999` @ `0x9814AA` |
| end of grid | `0x981570` |

The four records of one sub category are consecutive and carry identical category and
sub-category name fields -- verified for all 250 groups.

## Record layout

| offset | size | field |
|:---|:---|:---|
| +0x00 | long | record byte count -- **197** in every record |
| +0x04 | long | offset to the parameter block -- **77** (0x4D) in every record |
| +0x08 | 16 | category name, space-padded ASCII (`Easy Listening  `) |
| +0x18 | 16 | sub-category name, space-padded ASCII (`German Schlager `) |
| +0x28 | short | constant `1` in every record |
| +0x2A | byte | display-string length -- **32** in every record |
| +0x2B | 32 | display string: 29-char style name + 3-char right-aligned decimal number |
| +0x4B | 2 | `0x00 0x00` terminator/pad for the display string |
| +0x4D | 113 | **parameter block** -- the panel setup the Stylist applies ([decoded below](#the-parameter-block)) |
| +0xBE | 1 | no reader found (0x40 ×850, 0xAD ×95, 0x97 ×54, 0x99 ×1) |
| +0xBF | 6 | `FF` ×6, constant in every record |
| +0xC5 | 1 | grid padding, **not** part of the 197-byte record (93 distinct values across the grid) |

Every invariant in that table (the two `.long`s, the printable name ranges, the constant
`1`, the length byte 32, the `[ 0-9]\d\d` tempo pattern, the five `0xFF`) is asserted for
all 1000 records by the generator before it emits a line.

The 3-character number at +0x48 is the style's **tempo** as displayed: the Music Stylist
list-screen widget templates in `naka_perf_style.c` end their column header with `TEMPO`
(e.g. `"Euro Pop Shuffle:              TEMPO"`), and the values span 62..235 with 98
distinct settings. The tempo the firmware *applies* is a separate binary field in the
parameter block (+0x97, below). The two agree in 991 of the 1000 records. Records 99, 379,
538, 710, 711, 734, 865, 978 and 979 differ by 1-5 BPM.

## The parameter block

Earlier versions of this page called the parameter block "115 bytes, undecoded". The
`tonedb` lane read it from its three main-CPU readers in September 2026: it is **113 bytes**
(+0x4D..+0xBD), and every byte has a destination in the live panel. The block is applied to
the panel TLV stream at RAM `0xF9A0` (records `[tag][len][payload]`), through its mirror at
RAM `0x03C2C4`:

* `EffectMode_ClampAndLookupPreset` returns `record + 77`.
  `EffectMode_ProcessPresetChange` stores it at RAM `0x8D60`.
* `EffectMode_UpdateBitFlags` walks `WidgetStyleDataTable_0x2A8` (ROM `0xEB7BDA` in v7,
  v9 and v10): 30 entries `{u32 panel offset from 0xF9A0, u8 sub-offset, u8 count}` ended
  by `u32 0xFF`. It copies parameter bytes 0..112 in order. **That table is the record
  layout.**
* `BitMapOut_ByteData_PatchTable` is the unrolled variant used when RAM `0x8D52` bit 5 is
  set. It copies 98 of the bytes, some under a mask, and leaves the style number and
  tempo alone.
* `EffectMode_CopyVoiceParams` then copies bytes 29..33 into part 03 when tag 70 +3 = 3.
  For bytes 29/30 it disagrees with the walker table (part 03 +0/+1 versus +1/+2); the
  source records the disagreement without resolving it.

| record | bytes | destination | content |
|:---|---:|:---|:---|
| +0x4D | 10 | part 00 (RIGHT 1) +0..+9 | sound, bank, levels, reverb/chorus bits, pan |
| +0x57 | 10 | part 01 (RIGHT 2) +0..+9 | same |
| +0x61 | 9 | part 02 (LEFT) +0..+8 | same |
| +0x6A | 5 | part 03 ("PART 4") | sound, bank, +3, +4, +8 |
| +0x6F | 10 | parts 10..14 +3, +7 | ACC1, ACC2, ACC3, RHYTHM, BASS |
| +0x79 / +0x81 / +0x89 | 8 each | tags 44 / 45 / 46 | RIGHT 1 / RIGHT 2 / LEFT drawbar registrations |
| +0x91 | 2 | tag 48 +0/+1 | **style number** (11-bit) |
| +0x93 | 3 | tag 48 +2, +3, +4 | +2 = 0 and +3 = 0xEA in all 1000 |
| +0x96 | 1 | tag 48 +7 | bits 5:4 = the arrangement's slot in its style (record index mod 4, 998 of 1000) |
| +0x97 | 2 | tag 48 +8/+9 | **tempo in BPM** |
| +0x99 | 4 | tag 90 +0..+3 | |
| +0x9D | 1 | tag 60 +1 | (bits 7:6 only on the PatchTable path) |
| +0x9E | 18 | tag 61 +0..+17 | DSP-effect slot-0 block |
| +0xB0 | 9 | tag 63 +0..+8 | the block `ReverbPreset_Load` sends |
| +0xB9 | 2 | tag 65 +0, +1 | DSP-effect slot-2 block |
| +0xBB | 3 | tag 70 +0, +3, +4 | digital-effect selection |

Tags 00/01/02 are RIGHT 1 / RIGHT 2 / LEFT. Tags 10..14 are the accompaniment parts. Part
03 is "PART 4" in the part-name table at `0xE9F374`; which panel part that is on the
instrument is not established. Tags 0x90, 0x60 and 0x65, and most of tag 0x61's 18 bytes,
are named only by their destination.

Every record now has one source row per panel field (`table_data/style_records.s`,
written by `scripts/tools/style_records_field_rows.py`). The field map and its census
facts are re-derived, over all 1000 records and all three firmware versions, by
`python3 notes/tonedb-2026-09-25/style_record_field_map.py` (needs a built tree).

**A lead, not yet checked:** `EffEdit_ValidateAndReadParams` reads parameter id 0x4900
(& 0x7F) into RAM `0x2976`, and `DspItem0_DisplayEffectName` uses that byte to index
`DspEffectName_PtrTable`. If `DSPCfg_ReadParam_Map0(0x4900)` resolves to tag 0x61 +0 (record
+0x9E), every one of the 1000 styles has a named DSP effect.

## The ten categories

Record ranges are contiguous and in ROM order:

| # | category | records | sub categories |
|:---|:---|:---|---:|
| 1 | Easy Listening | 000-123 | 31 |
| 2 | Rock & Pop | 124-255 | 33 |
| 3 | Dance Pop | 256-323 | 17 |
| 4 | Party Music | 324-399 | 19 |
| 5 | Gospel/Blues/R&B | 400-471 | 18 |
| 6 | Jazz & Swing | 472-591 | 30 |
| 7 | Show/Trad Dance | 592-715 | 31 |
| 8 | Trad & Folk | 716-815 | 25 |
| 9 | Country | 816-883 | 17 |
| 10 | Latin / World | 884-999 | 29 |
| | **total** | **1000** | **250** |

The STYLE EXPLORER screen carries the same ten strings, with one cosmetic difference: the
screen label reads `Trad / Folk` where the records read `Trad & Folk`. The labels are
declared in `naka_perf_style.c` as `w166_text`..`w175_text` in the order Easy Listening,
Rock & Pop, Party Music, Dance Pop, Gospel/Blues/R&B, Jazz & Swing, Show/Trad Dance,
Trad / Folk, Country, Latin / World -- which differs from ROM order at positions 3 and 4.
Whether that declaration order is also the on-screen order has not been confirmed against
a screenshot.

### Sub categories

Names as stored at +0x18, in ROM order.

**Easy Listening** -- German Schlager, Easy Play 8 Beat, Rock After Eight,
Orchestral Beat, Smooth Rock, Greatest Hits, Studio 8 Beat, Ballad Producer, Love Songs,
16 Beat Groove, Easy Play 16Beat, E.P. Moments, Gentle 16 Beat, Atmospheric 16,
Synth Ballad, Grands on Stage, Modern Ballads, Night Club Dance, 50's Love Songs,
Oldie Ballads, Soft Schlager, Oldie Drawbars, Euro Ballads, Romantic Band, Jazz Serenade,
Nat's Ballads, Drawbar Combo, Paris Romance, Easy Play Waltz, Parisian Nights,
Easy Jazz Waltz

**Rock & Pop** -- Fifties Rock, Piano R&Roll, It's Boogie Time, Rockabilly Band,
Boogie Time, Slow Dance, Swinging Sixties, Liverpool Beat, 60's Rock, California Pop,
70's Fox Dance, Glamrock Piano, 70's Hits, 70's Power Rock, Euro Pop Shuffle,
80's Love Songs, In The Eighties, Pop Beat, 8 Beat Groove, 80's Pop Ballads, Rock Gig,
Heavy Metal, Heavy Shuffle, Power Ballad, L.A. Pop, Gentle SwingRock, Cool Fusion,
Jazz Pop, Pop Fusion, Easy Groovin', Chart Fusion, Cool Funk, Straight Funk

**Dance Pop** -- British DancePop, Straight Dance, House Party, Techno World,
Glory Disco, 80's Disco, Dance Floor, 70's Dance Craze, Hip Hop, 80's & 90's, N.Y. Rap,
The Big Hit, Reggae Hit, Rio Goes Disco, Jambo Dance, Samba Party, Western Techno

**Party Music** -- J.Last Hitparade, Last Arrangement, German Schlager, All Night Party,
Pop Organ March, Eurovision Hits, Euro Party Pop, German Oldies, Golden Oldies,
BeerBarrel Polka, Do The Hokie...., Dancing Birdies, Pub Singalong, Line Dance Craze,
Barn Dance, Hillbilly Joe, Bavarian Party, Munich Festival, Merry Christmas!

**Gospel/Blues/R&B** -- King Of Soul, Detroit Pop, Soft Soul, New Soul Ballad,
Soul To Sun, Mellow Soul, Slow Soul Mood, R&B Groove, Down&Dirty Blues, Rock Blues,
Blues Alley, Play The Blues, Sunday Service, Lift Your Soul, Day Of Rest, Power Gospel,
Gospel Blues, Gospel In Threes

**Jazz & Swing** -- Up Tempo Bigband, Steady Swingband, All Aboard!, 40's Dance Band,
Sentimental Band, Moonlight Dance, 40's Love Songs, Mid Swingband, Swing Orchestra,
Night Club Combo, Easy Play Swing, Jazz Club, Up Tempo Combo, Simple Jazz, 40's Boogie,
Jazz Standards, Combo Drawbars, Gentle Jazz, Gypsy Jazzers, Jazz Accordion,
Speakeasy Jazz, Jazz Francais, Van Damme Jazz, Euro Jazz, Smokey Jazz Club,
Jazz At 3:00am, Steady Jazz 3/4, Slow Jazz 3/4, The Groove, L.A. Fusion

**Show/Trad Dance** -- Musical Overture, Tinseltown, Showband, Theatre Stride,
Vaudeville Act, Tap Dancer, Paris Club, Cabaret Band, Viva Las Vegas, Magic Ballroom,
Gentle Foxtrot, Organist's Dance, Up Tempo Foxtrot, Strictly Foxtrot, Radio Foxtrot,
Strictly Quick!, Let's Twist, Jive Dance, Do The Twist!, 1,2,Cha Cha Cha,
Let's Beguine!, Samba Felicidade, Viva Pasodoble!, Strict Tango, Tango D'Amour,
Tango Pianist, Last Dance Waltz, Quick Waltz, Austrian Waltz, Walzer-Time, Party Vienna

**Trad & Folk** -- Stadium Events, Sousa Marches, German Tradition, Musikantenstadl,
Standard Polka, Modern Polka, German Polka, Ceilidh Band, Highland Dance,
3/4 Concert Time, Munich Waltz, East Euro Waltz, German Waltz, Island Romance,
Hawaiian Dance, Old Ragtime, Ragtime Band, New Orleans Jazz, Sounds of Dixie,
Greek Dance, Moscow At Night, Kings of Gypsy, Spanish Folklore, Mariachi band,
70's Folk Music

**Country** -- Bluegrass Time, Modern Hoedown, Kentucky Blue, Trucker Country,
Country Dance, Hillbilly Blues, 70's Country Pop, Country Romance, Western Ballads,
Country Folks, Country 88, Country Love, Modern Country, EZ Country Rock,
Old Country Hits, New Country Rock, Country Hits

**Latin / World** -- Romantic Bossa, Bossa Pianist, Mellow Bossa, Rhumba Espana,
Cocktail Pianist, Romantic Beguine, Romantic Dance, Latin Lounge Bar, Tito's Cha Cha,
Mambo Band, New Mambo Mood, It's Mambo Time!, Cumbia Band, Holiday Mood, Samba Parade,
Latin Festival, Modern Rio, Castanet Dance, Caribbean Nights, Salsa Picante, Samba Amor,
Modern Caribbean, Modern Samba, Samba Fusion, Indonesian Folk, Dangdut, Talempong,
Synth Reggae, Jamaican Swing

## The two pointer tables

| symbol | address | contents |
|:---|:---|:---|
| `StyleRec_PtrTable_C2C5` | `0x986000` | 1000 x 4-byte LE pointer, then 96 bytes of residue (`StyleRec_PtrTable_C2C5_Residue` @ `0x986FA0`) |
| `StyleRec_PtrTable_Default` | `0x987000` | 1000 x 4-byte LE pointer, then 96 bytes of residue (`StyleRec_PtrTable_Default_Residue` @ `0x987FA0`) |

Each occupies one 4 KB page; 1000 x 4 = 4000 bytes, leaving 96 bytes at the end of each
page. Every pointer in both tables lands exactly on a grid record (verified:
`(p - 0x951000) % 198 == 0` and in range for all 2000 entries).

`StyleRec_PtrTable_C2C5` is the **identity** permutation: entry *n* points at record *n*,
so the order is the ten categories in sequence -- browsing by category, i.e. the STYLE
EXPLORER order.

`StyleRec_PtrTable_Default` is a **different, curated order** that interleaves the
categories and starts with 8-beat-flavoured sub categories (German Schlager,
Easy Play 8 Beat, 8 Beat Groove, Rock After Eight, ...), always keeping a sub category's
four styles together. It is *not* sorted alphabetically by category, sub category or
style name -- so despite the front page's `> Alphabetical style select` entry, this page
does not currently claim the table is that screen's list. What rule produced the order is
an open question.

### An anomaly in the Default table

`StyleRec_PtrTable_Default` does **not** cover all 1000 records. It contains only 996
distinct records:

* records **160-163** -- Rock & Pop / *California Pop* (`San Jose Route`,
  `Easy Bacharach!`, `Santa Monica Way`, `Life's A Beach!`) -- appear **nowhere** in the
  table;
* records **368-371** -- Party Music / *Dancing Birdies* -- appear **twice**, at slots
  652-655 and again at slots 984-987.

The identity table at 0x986000 is unaffected, so those four styles remain reachable in
the UI states that use it. Whether this is visible to a player (a duplicated entry near
the end of one list and a missing one) has not been checked on hardware.

### Which table, and when

`EffectMode_ClampAndLookupPreset` (`v10/maincpu/ui/ui_mode_handlers.s:404`, same routine
in v7/v9) performs the lookup:

```
cp   wa, 0x3e8            ; clamp the index to 1000 = the entry count
ldb  c, (0x8d38)          ; current UI state ID
cp   c, 0xc2 / 0xc5       ; -> 0x986000, otherwise -> 0x987000
sll  xwa, 2 / add xwa, xbc / ld xwa, (xwa)
ld   xhl, xwa / add xhl, (xwa + 4)   ; -> parameter block
```

The selector byte at DRAM **0x8D38** is the **current UI state ID**, not a model code:
the same byte is what `UIState_KeyScan_Dispatch` uses to index the keymap table
(`v10/maincpu/ui/ui_control_panel.s:1920-1932`). The "0xC2 = KN3000 / 0xC5 = KN5000"
reading that older notes carried is withdrawn.

`EffectMode_DisplayPresetName` (same file, line 432) applies the same split, with explicit
checks for 0xC0, 0xC2 and 0xC5 -- 0xC0 taking the default table -- and renders the name
with `Strncpy(dst, record + 43, 16)`, i.e. only the first 16 characters of the 32-char
display string fit the narrow name box.

`MssName_EventDispatch` (event `0x1c00013`, same file, line 10599) uses the default table
only and copies the full string: it loads the length byte from `record + 42` and calls
`Strncpy(dst, record + 43, that length)` = 32 characters.

## After the grid: a stale copy of the help databases

`0x981570-0x983B39` is **not** part of the database, and no pointer to any address in it
exists in the v7, v9 or v10 program ROMs. It was once read as two unrelated residues (a
"discarded compressed block" and a "ramp"). It is one object: **`0x98156F-0x985FFF` is a
byte-identical copy of the live help-database region `0x98956F-0x98DFFF`, written exactly
0x8000 bytes lower.** A single byte differs in the whole 18 KB, at `0x983B39`, the pad
between the two streams. So `0x98156F-0x983B38` is the tail of the English help database
and `0x983B3A-0x985FFF` the German one, truncated at `0x986000` by the pointer tables. The
"text shreds" are SLIDE8K output. The "ramp" is ordinary back-references whose ring offsets
climb linearly. Reproduce: `scripts/analysis/verify_stale_band.py
original_ROMs/kn5000_table_data.rom` (see the header of `table_data/style_records.s`).

## Build status

The LLVM lane assembles both modules from source -- `table_data/style_records.s` and
`table_data/style_record_ptr_tables.s` are prerequisites of
`rebuilt_ROMs/kn5000_table_data.llvm.o` (`Makefile:680`) -- and the pointer tables are
fully symbolic (`.long StyleRec_NNN`), so the record grid and its indices stay consistent
by construction.

The parallel ASL mirror still takes the whole region as one raw slice
(`binclude "includes/icons_to_strings.bin", 0, 07F2D8h` in
`archive/asl/table_data/kn5000_table_data.asm:221`), by design: the blob file must stay
byte-identical on disk.

Open items on this block:

* record byte +0xBE has no reader;
* part 03's panel identity, and the two readers' disagreement on bytes 29/30;
* the ordering rule behind `StyleRec_PtrTable_Default` is unknown, and its
  California Pop / Dancing Birdies anomaly is unexplained;
* whether parameter id 0x4900 names each style's DSP effect (the lead above).

## Provenance

* Carve + labels: `table_data/style_records.s`,
  `table_data/style_record_ptr_tables.s` (commit `c9bc67f`).
* Generator and structural assertions: `scripts/generators/gen_style_records.py`.
* Consumers: `v10/maincpu/ui/ui_mode_handlers.s` lines 404 (`EffectMode_ClampAndLookupPreset`),
  432 (`EffectMode_DisplayPresetName`), 10599 (`MssName_EventDispatch`); UI-state byte
  documented at `v10/maincpu/ui/ui_control_panel.s:1920-1932`.
* Screen labels and the "1000 Musical Styles" string:
  `v10/maincpu/ui_widgets/naka_perf_style.c` (`w160_text`..`w175_text`, `str_898`);
  `str_898` is at main-CPU ROM 0xE14C86 in v7, v9 and v10.
* Help-text wording: `table_data/includes/help_databases/help_db_english.bin`.
* Category counts, pointer-table permutations and the 996/1000 anomaly: recomputed from
  `original_ROMs/kn5000_table_data.rom` for this page.
* Parameter-block field map (September 2026, lane `tonedb`): the `PARAMETER BLOCK` header
  in `table_data/style_records.s`; probe `notes/tonedb-2026-09-25/style_record_field_map.py`;
  lane report `notes/lanes/wave2-2026-09-25/lane-reports/tonedb.json`.
