---
layout: page
title: Panel Memory Factory Data
permalink: /panel-memory-factory-data/
---

# Panel Memory Factory Data (Table Data ROM)

The block at **0x99EC00-0x9ABF3F** in the Table Data ROM holds the **factory contents of
the PANEL MEMORY registrations**: ten 16-character bank names followed by 80 preset
records of 674 bytes -- ten banks of eight, one per PANEL MEMORY button. Boot copies all
of it into DRAM, where the user's own registrations later overwrite the working copies.

Two earlier readings of this region are retired by this page:

* **"Demo Category Names"** -- the ten strings at 0x99EC00 are Panel Memory *bank* names
  ("Tour Of The 5000", "Accordion", ...), not demo-song categories. The eleventh name
  older notes listed, `xPiano Atmosphere`, is almost certainly a boundary artefact of
  reading string-shaped runs straight past the end of the name array into the first preset
  record: the record's first byte is its `0x78` name-chunk tag, which is ASCII `x`, and
  `Piano Atmosphere` is preset 0's name.
* **"Tone Generator Configuration Records, 26-byte stride"** -- there is no 26-byte
  record stride here. The 26-byte autocorrelation that produced that guess is the
  **2-byte chunk header plus 24-byte payload** of the sound-part chunks *inside* a
  674-byte record. The stride of an actual record is 674.

The block is now assembled from source in `table_data/panel_memory_presets.s`.

Companion pages: [Custom Data Flash]({{ site.baseurl }}/custom-data-flash/) for the
*user* Panel Memory storage, [Table Data ROM]({{ site.baseurl }}/table-data-rom/) for the
region map, [Music Stylist Preset Database]({{ site.baseurl }}/music-stylist-database/)
for the other factory-registration block in this ROM.

## Layout

| range | symbol | contents |
|:---|:---|:---|
| `0x99EC00-0x99EC9F` | `PanelMemory_BankNames` | 10 x 16-char space-padded bank names |
| `0x99ECA0-0x9ABF3F` | `PanelMemory_Preset_00`..`_79` | 80 x 674-byte preset records |

Record *i* is bank `i / 8`, button `(i % 8) + 1`. 80 x 674 = 53,920 bytes, ending exactly
at 0x9ABF40, from where the ROM is 0xFF fill to 0x9B3FFF (32,960 bytes, verified).

### Factory banks and presets

| bank | name | buttons 1-8 |
|:---|:---|:---|
| 1 | Tour Of The 5000 | Piano Atmosphere, String Orchestra, PianistMode Trio, New Guitars, Fall To The Left, HollywoodRomance, It's An Illusion, Pomp & Ceremony |
| 2 | Accordion | Le Musette, Jazz Accordion, Steirisches, Soft Latin, Tutti Registers, Pure Tango, Romantic Reeds, Fun Park Reeds |
| 3 | Piano Styles | Ragtime Pianist, Jazz Pianist, Easy Jazz Groove, Lullaby Of Jazz, Bossa Pianist, Deep Rhumba Solo, Blueberry Keys, Sequin Virtuoso |
| 4 | Jazz&Rock Organ | The Cat of Jimmy, Smith strikes B3, Tribute to Joey, DeFrancesco's C3, The Lord Organ, Hensley's Livin', Brian's Revival, Auger's Bump |
| 5 | Church & Theatre | Chapel Organ, Sunday Service, Full Pipes, All Stops Out, Funtime Theatre, At The Seaside, Tibia Chorus, Tibias Plus |
| 6 | Light Orchestra | 40's Dance Band, Late Night Jazz, On The Shore?, Mantostringy!, Latin Muzak, Cello Romance, Pizzicato Magic, Radio Orchestra |
| 7 | Split Sounds | Piano,Bass&Drums, Modern Jazz Trio, Ballad Combo, 60's Pop Group, Folk Festival, Power Pop Ballad, Hillbilly Band, Brass Band |
| 8 | Layer Production | Behind The Piano, Guitar Dreams, Studio EP, Bright Piano Pad, Guitar Synth, Open Spaces, Super Sweeper, Of The Ether |
| 9 | Special DSP FX | 50's Echo, Don't Ring Us!, A Bit Of A Mixup, Phased Guitar, Effective Warmth, Bad Boy Wah, Flanged & Funked, Underwater Echo |
| 10 | World | Sunset in Peru, Party in Greece!, Tango Symphonia, Hungarian Party, Caribbean Style, The French Way!, Eastern Promise, Edinburgh Dance |

Bank names are stored centred with spaces (`"   Accordion    "`, `"     World      "`);
only bank 0 fills all 16 columns. Preset names are stored likewise and are shown here
trimmed.

## Record format: a chunk stream

A record is **not** a fixed struct. It is a stream of `(tag, length, payload[length])`
chunks, terminated by a `0xFF` tag; a second `0xFF` byte pads the record out to 674
bytes. All 80 records carry the **same 34-chunk sequence in the same order** (verified
across all 80).

| # | tag | payload | role |
|:---|:---|---:|:---|
| 1 | `0x78` | 18 | 16-char preset name + 2 spare bytes (`00 00` in all 80) |
| 2-5 | `0x00`-`0x03` | 24 each | sound-part blocks, the four realtime parts |
| 6 | `0x0F` | 24 | sound-part block |
| 7-13 | `0x10`-`0x16` | 24 each | sound-part blocks (accompaniment/rhythm side) |
| 14 | `0x19` | 24 | sound-part block |
| 15-17 | `0x44`-`0x46` | 10 each | parameter groups (undecoded) |
| 18 | `0x47` | 8 | parameter group (undecoded) |
| 19 | `0x43` | 4 | parameter group (undecoded) |
| 20 | `0x48` | 10 | parameter group (undecoded) |
| 21 | `0x90` | 6 | parameter group (undecoded) |
| 22 | `0x60` | 4 | parameter group (undecoded) |
| 23-27 | `0x61`, `0x63`-`0x66` | 24 each | part-block-sized groups (undecoded) |
| 28 | `0x68` | 10 | undecoded |
| 29 | `0x70` | 8 | undecoded |
| 30 | `0x72` | 14 | undecoded |
| 31 | `0x92` | 14 | undecoded |
| 32 | `0x71` | 2 | undecoded |
| 33 | `0x99` | 30 | undecoded |
| 34 | `0x80` | 14 | undecoded |
| -- | `0xFF` | -- | terminator, then one `0xFF` pad byte |

That adds up: 20 + 13x26 + 78 + 5x26 + 106 + 2 = 674.

Note the chunk order in the stream is not tag order -- `0x44 0x45 0x46 0x47 0x43 0x48`
is the literal sequence in every record.

### The 24-byte sound-part block

Thirteen chunks per record carry a 24-byte sound-part payload (`0x00`-`0x03`, `0x0F`,
`0x10`-`0x16`, `0x19`). Five further chunks (`0x61`, `0x63`-`0x66`) happen to be 24 bytes
long as well but are not part blocks.

Field observations from cross-record diffs, all **tentative**:

| offset | observation |
|:---|:---|
| +0 / +1 | sound selection (program number plus a bank/group byte) |
| +3 | volume-like level, range 0x3C-0x7F |
| +8 / +9 | a 0x40-centred pair (pan-like) |
| +13 | part/routing byte -- **constant per tag** across all 80 records |

The +13 byte is the strongest structural signal in the block. Its value per tag,
measured over all 80 records:

| tag | +13 | tag | +13 |
|:---|:---|:---|:---|
| `0x00` | `0x00` | `0x13` | `0xC2` |
| `0x01` | `0x01` | `0x14` | `0xCE` |
| `0x02` | `0x02` | `0x15` | `0xC4` |
| `0x03` | `0x03` | `0x16` | `0xC0` |
| `0x0F` | `0x0F` | `0x19` | `0xCF` |
| `0x10` | `0xC4` | | |
| `0x11` | `0xC8` | | |
| `0x12` | `0xC9` | | |

For the five low tags the byte simply repeats the tag; for the eight high tags it is
`0xC0 | m` with an `m` that is *not* the tag's low nibble, so the mapping is a lookup, not
an arithmetic rule. There is exactly one exception in the whole block: preset 15
(bank 2 button 8, "Fun Park Reeds") stores `0xC0` in its `0x19` chunk where the other 79
records store `0xCF`.

## How the firmware loads it

Three main-CPU routines, cited at their v10 addresses; v7 and v9 carry the same code at
shifted addresses. The routines now carry names in the v10 source, but the names do not
describe what they do here: `Display_CopyAndRenderBitmaps` (0xFC81EF),
`VoiceData_ExtendedParamSetup` (0xFC7E82) and `VoiceData_InitAndCopyParams` (0xFC7DD8). The
`tdata` lane recorded this in `table_data/panel_memory_presets.s` and left the rename to the
file's owner.

**`0xFC81EF` -- initialise everything.**

```
MEM_COPY(0x1ED350, 0xEDBA1C, 16)    ; 16-byte spare name slot: "HK \0" + zeros + c0 03 50
MEM_COPY(0x1ED360, 0x0099EC00, 160) ; the ten bank names
for i in 0..0x4F: call 0xFC7DD8     ; the 80 preset records
```

The `"HK "` signature it seeds is the same one the user registration area in the Custom
Data Flash uses (see [Custom Data Flash]({{ site.baseurl }}/custom-data-flash/)).

**`0xFC7E82` -- copy one bank name.** Returns immediately if the index is >= 10, otherwise
`MEM_COPY(0x1ED360 + 16*i, 0x99EC00 + 16*i, 16)`.

**`0xFC7DD8` -- build one RAM record.** Bounds-checks the index against `0x50` (= 80),
zero-fills a 960-byte (`0x3C0`) RAM record at `0x1ED400 + 960*i`, then assembles it from
*two* sources -- the 674-byte ROM record at `0x99ECA0 + 674*i`, and a fixed default block
in the program ROM:

| RAM range | length | source |
|:---|---:|:---|
| `+0x000` | `0x07C` | ROM record `+0x00` -- the name chunk and parts `0x00`-`0x03` |
| `+0x07C` | `0x11E` | program ROM `0xEDB478` -- eleven chunks tagged `0x04`-`0x0E` |
| `+0x19A` | `0x226` | ROM record `+0x7C` -- everything else, including the `FF FF` terminator |

The middle piece is the key structural fact: **parts `0x04`-`0x0E` are not stored per
preset**. The block at main-CPU ROM `0xEDB478` is 286 bytes = eleven chunks in exactly the
same `(tag, 24, payload)` grammar, tagged `0x04` through `0x0E`, and every one of the 80
factory presets gets the identical copy spliced in. The assembled RAM image is therefore a
45-chunk stream of 960 bytes carrying 24 sound parts, with tags `0x17` and `0x18` unused.

## Composer factory memory image (0x9B4000-0x9C3FFF)

The 64 KB immediately after the Panel Memory fill is `Composer_FactoryMemoryImage`: the
factory contents of the **COMPOSER** (user rhythm-style) memory. It is copied wholesale
into DRAM at boot, with no interior addressing at all:

```
ld XIY,0x9B4000 / ld XIX,0x94800 / ld BC,0x8000 / ldirw   ; 0x8000 words = 64 KB
```

That code is at main-CPU **0xF6413A** in v9 and v10 and **0xF63D36** in v7; the v7 source
tree has it at `v7/maincpu/sequencer/accompaniment_engine.s:16703` under the placeholder
label `AccWidget_DispatchTable` (the same label at 0xF6413A in v9 and v10), which does not describe it: it is the Composer image copier (a rename is pending). Because
nothing addresses inside the image, the block stays a single labelled `.incbin` slice.

Structure observed in the image (offsets are image-relative; add 0x9B4000 for ROM):

| image offset | contents |
|:---|:---|
| `+0x0000` | header: memory-configuration words, part lists `01 02 03 04`, a `5A 5A 5A` (`"ZZZ"`) tag |
| `+0x0080` | 30 style-slot records, 0x60 bytes each, 16-char name at slot offset +0x20 |
| `+0x0C00` | zero fill to `+0x12FF` |
| `+0x1300` | style event pool, to the end of the image |

The 30 slot names are three factory user styles at four variations each --
` Pop Samba 1`..` Pop Samba 4`, `GentleSwing 1`..`GentleSwing 4`,
`German 3/4 1`..`German 3/4 4` -- followed by 18 slots named `    Clear       `.

### The "MIDI-like note streams near 0x9C0000"

The old region map described `0x9B4D78-0x9C3FFF` as "tone generator parameter data;
MIDI-event-like note streams (`90 30 24 ...`) from 0x9C0000". Those streams are real, but
they are the Composer image's rhythm data, not tone-generator parameters. They use the
same cell grammar the factory rhythms use: a `80 nn 00 FF FF 87` cell header followed by
six-byte note events beginning `0x90`. In the dumped image there are **52** such headers,
each landing on a 256-byte boundary, the first at image offset `0xAB00` = ROM
**0x9BEB00** -- earlier than both the old map's 0x9C0000 and the "+0xC000" figure quoted
in the module header. The event grammar itself is not decoded on this page; see
[Custom Data Flash]({{ site.baseurl }}/custom-data-flash/) for the rhythm-cell format in
the factory style database.

## Neighbours

* `0x9999CC-0x9999D2` -- `HelpDB_TrailingResidue`, seven stray bytes left after the
  Indonesian help database: `7F D8 7F E2 7F EC 7E`, three `(0x7F, N)` pairs with `N`
  stepping by 10, then a lone `0x7E`. Nothing points at them; they look like the tail of
  a stride-10 table from an earlier factory build.
* `0x9999D3-0x99EBFF` -- 0xFF fill (21,037 bytes, verified).
* `0x9C4000-0x9C404F` -- `DemoSongPreset_PointerTable`: 19 four-byte LE pointers plus a
  null terminator, indexed as `part * 4`. Every non-null target begins with the ASCII
  magic `SLIDE4K`, so these are **compressed demo-song presets**, not PCM waveform
  samples as an older note on the Table Data ROM page had it. Entry 18 is the Feature
  Demo preset at 0x8E0000; the other 18 tile 0x9C4050-0x9F94CA (the last block starts at
  0x9F494E), with 0xFF fill following from 0x9F94CB.

## Build status

`table_data/panel_memory_presets.s` is a prerequisite of
`rebuilt_ROMs/kn5000_table_data.llvm.o` (`Makefile:680`), so the whole Panel Memory block
assembles from source in the LLVM lane, chunk by chunk, and the demo-preset pointer table
is symbolic. The Composer image is still a labelled raw slice of
`table_data/includes/icons_to_strings.bin`, and the parallel ASL mirror still takes the
entire 0x944D78-0x9C404F range as one `binclude`
(`archive/asl/table_data/kn5000_table_data.asm:221`) so that the blob file stays
byte-identical on disk.

Open items on this block:

* every chunk except the name chunk is undecoded at field level; the sound-part field
  guesses above have not been checked against the tone-generator command format;
* the meaning of the tags themselves (why `0x43`-`0x48`, `0x60`-`0x66`, `0x70`-`0x72`,
  `0x80`, `0x90`-`0x99`) is unknown;
* the preset-15 `0x19`/`0xC0` outlier is unexplained;
* the Composer image's header words and its 0x1300-0xAB00 span are undescribed;
* the loader routines carry misleading names (`Display_CopyAndRenderBitmaps`,
  `VoiceData_ExtendedParamSetup`, `VoiceData_InitAndCopyParams`); renaming them is pending.

## Provenance

* Carve + labels: `table_data/panel_memory_presets.s` and the Composer / demo-table
  hunks in `table_data/kn5000_table_data.s` (commit `9510993`).
* Loader routines: disassembled from `original_ROMs/kn5000_v10_program.rom` at
  `0xFC81EF`, `0xFC7E82`, `0xFC7DD8`; the default block at `0xEDB478` and the `"HK "`
  slot at `0xEDBA1C` were read from the same image.
* Composer copy: `v7/maincpu/sequencer/accompaniment_engine.s:16703`; the immediate
  `0x009B4000` occurs exactly once in each of the v7, v9 and v10 program ROMs.
* Chunk-signature, +13 census, bank/preset names, fill extents and the Composer image
  survey: recomputed from `original_ROMs/kn5000_table_data.rom` for this page.
