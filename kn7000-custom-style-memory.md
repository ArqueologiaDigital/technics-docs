---
layout: page
title: "Custom Style Memory (IC21) & .AST Files"
permalink: /kn7000-custom-style-memory/
---

# Custom style memory: KN7000 IC21, KN6000 / KN6500 IC18, and the `.AST` files

The KN7000 keeps its 20 **CUSTOM** styles in the upper 1,920 KB of IC21, the 2 MB flash at
`0x96800000`: a bank at `0x96820000` of 60 blocks of 32 KB (`0x1E0000` bytes). Each of the 20
slots is a custom style together with everything it needs: its four ONE TOUCH SETTING panel
memories, its six performance pads and any user sounds it uses. The owner's manual (p.120)
describes CUSTOM as 20 styles copied in from COMPOSER MEMORY; the Initial Data Disk resets it to
the factory set (p.137). The **KN6000 and KN6500** have the same bank at the same address on their
IC18, written by the same firmware module.

The flash chip itself, its driver and the Initial Data Disk's other files are on
[User Data & the Initial Data Disk]({{ site.baseurl }}/kn7000-initial-data/). This page is the
bank's format. Its source is the disassembly's
[`kn7000/notes/custom-data-ic21.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/custom-data-ic21.md)
(2026-10-29), with probes in
[`custom-data-ic21-probes/`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/custom-data-ic21-probes/README.md).
Routine addresses are KN7000 program 941's. *[INFERENCE]* marks a reading no traced code fixes.

## The ten factory banks, rebuilt from source

The disassembly repository rebuilds every factory bank that exists byte for byte from typed
sources, every style event on its own line:

| image                           | floppy (MAME softlist)  | file           | SHA-1 of the bank                          |
|---------------------------------|-------------------------|----------------|--------------------------------------------|
| KN7000 `01ctmini.ic21`          | `kn7000_flop` `idd7000` | `01CTMINI.AST` | `67b2a0fe8154c4d15557399a86bf0d0b49813ced` |
| KN7000 `01custm1.ic21`          | `kn7000_flop` `custom1` | `01CUSTM1.AST` | `4cd5fe37871984a4b470b1a12b835c9bc41f37f5` |
| KN7000 `02custm2.ic21`          | `kn7000_flop` `custom1` | `02CUSTM2.AST` | `6c85b616a9acc3a7ecc1b49a70f138c0d9442086` |
| KN7000 `03custm3.ic21`          | `kn7000_flop` `custom1` | `03CUSTM3.AST` | `d5722a1129134383bf643d20b4e0866c3089fc36` |
| KN7000 `04custm4.ic21`          | `kn7000_flop` `custom1` | `04CUSTM4.AST` | `25822a3ad726df49882cdd0066424600fb70ea14` |
| KN7000 `01custm5.ic21`          | `kn7000_flop` `custom2` | `01CUSTM5.AST` | `11d32c3d293a23a511a76297647758046cd8ccc9` |
| KN7000 `02custm6.ic21`          | `kn7000_flop` `custom2` | `02CUSTM6.AST` | `54f2bac0551a8d43dc1a87fe24a13c545169a326` |
| KN7000 `03custm7.ic21`          | `kn7000_flop` `custom2` | `03CUSTM7.AST` | `e1bdfbbbe78353003af5ed01866be87d799523bb` |
| KN7000 `04custm8.ic21`          | `kn7000_flop` `custom2` | `04CUSTM8.AST` | `f4722d93ff3f31c6d8c25f757968d796e4eb57ca` |
| KN6000 / KN6500 `01ctmini.ic18` | `kn6000_flop` `idd6000` | `01CTMINI.AST` | `8c6d62a8afab717a2b59e9242bbf897b01369416` |

The Makefiles make the references from the floppy images, not from a romset: unzip the disk,
extract the `.AST` with `tools/fat12_extract.py`, inflate it with `tools/ast_file.py`, check the
SHA-1. Nothing copyrighted is committed.

    make -C kn7000 verify-customdata       # the 9 KN7000 banks; part of make gate-kn7000
    make -C kn6000 verify-customdata       # the KN6000 bank;   part of make gate-kn6000
    make -C kn7000 verify-customdata-ast   # the 9 .AST files rebuilt from the banks (not in the gate)
    make -C kn6000 verify-customdata-ast
    make -C kn7000 customdata-src          # regenerate src/customdata/ (tools/gen_customdata_s.py)
    make -C kn6000 customdata-src

| path                                                                                                                                                | what                                                                         |
|-----------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| [`kn7000/src/customdata/customdata.inc`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/src/customdata/customdata.inc) | the record macros, one per record kind, every known field named              |
| [`kn7000/src/customdata/<image>.s`](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/kn7000/src/customdata)                     | the bank: the directory, then per block an include, residue or fill          |
| `kn7000/src/customdata/<image>/SlotNN.inc`                                                                                                          | slot NN's record, fully typed, events one per line                           |
| `kn7000/src/customdata/<image>/StaleNN.inc`                                                                                                         | a complete older record in free block NN, typed the same way                 |
| [`kn6000/src/customdata/01ctmini.s`](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/kn6000/src/customdata), `01ctmini/`       | the KN6000 bank, same macros (`--model kn6000`)                              |
| `kn7000/src/include/panel_memory.inc`, `voice_record.inc`                                                                                           | one-touch-setting and voice-record macros, shared with the floppy describers |
| `kn7000/tools/gen_customdata_s.py`                                                                                                                  | the generator; it models every macro's bytes and stops on a mismatch         |
| `kn7000/tools/ast_file.py`                                                                                                                          | `.AST` inflate (references) and deflate (rebuild)                            |
| `kn7000/tools/zlib10_deflate.py`                                                                                                                    | the firmware's zlib 1.0.4 deflate, ported to Python                          |

## The directory (block 0)

At boot `func_48484499` sets the module status `*(0x50001298)`. When `FlashReadAutoselect` fails
it sets -1 (no custom flash: every fetcher returns NULL). When the bank does not start with `"IK"`
it builds an empty directory in the RAM shadow `0x5037A000` (`0x6000` bytes of `0xFF`, the
signature, all slots `{0, 0}`, all blocks free but block 0) and programs it with
`FlashProgram128Words`.

| offset  | size   | field                                  | read / written by                                                            |
|---------|--------|----------------------------------------|------------------------------------------------------------------------------|
| `+0x00` | 2      | `"IK"`                                 | `func_48484499` (check), `func_48483F35` (write)                             |
| `+0x02` | 20 x 2 | slot: first block (0 = empty), count   | `func_48483F53` / `func_48483F82`; setters `func_48483F6D` / `func_48483F9C` |
| `+0x2A` | 60     | block map, 1 = allocated               | `func_48483FB4`, set `func_48483FC6`, clear `func_48483FDA`                  |
| `+0x66` |        | `0xFF` to `0x6000`, erased to `0x8000` |                                                                              |

Block `b` is at `0x96820000 + (b << 15)` (`func_48483FED`); a slot's record is at its first block.
The allocator `func_484843A4` looks for free runs in the map, and the saver `func_484857AF` writes
the slot descriptor and marks the blocks. In all ten images every slot is used, its block count
is `ceil(size / 0x8000)`, and the map is exactly block 0 plus the slots' blocks.

## The slot record

Built in RAM by the MEMORY -> CUSTOM save `func_484854E3` (at `0x5031C000` or `INSTALL_SCRATCH`
`0x502B8000`), then programmed to its blocks. All little-endian.

| offset           | field                                                      | evidence                                                                                  |
|------------------|------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| `+0x00`          | u32 record size = `0x100` + the sections                   | `func_4848403C`; `func_4848512E` sums the sections                                        |
| `+0x04`          | 16-byte style name                                         | `func_48484049`; written by `func_4C021AF8`                                               |
| `+0x14..+0x44`   | four 16-byte ONE TOUCH SETTING names                       | `func_4848407B` ...; written by `func_4C021B53`                                           |
| `+0x54..+0x7C`   | five `{u32 offset, u32 count}`: `0x42`-byte records        | `func_48484153` .. `func_48484257`; counts from item bitmasks                             |
| `+0x7C`          | `{offset, count}` of `0x2C8`-byte SOUND EDIT records       | `CustomSoundEditRecFetch` (`0x484845E1`)                                                  |
| `+0x84`          | `{offset, count}` of the `0x48A7`-byte custom-sound block  | `CustomVoiceRecFetch` (`0x4844A42F`)                                                      |
| `+0x8C`          | `{offset, size}` of the 4 one-touch-setting panel memories | `func_484842D8`; record size from `func_4C02AD02` (`0xA0`)                                |
| `+0x94`          | `{offset, size}` of the "TCMP" style container             | `CustomStyleBlockFetch` (`0x48484578`)                                                    |
| `+0x9C`          | `{offset, size}` of the "TPAD" pad container               | `func_48484332`, `func_4848435C`                                                          |
| `+0xA4`, `+0xA5` | first block, block count (as in the directory)             | equal to the slot descriptor in all 200 live records                                      |
| `+0xA6..+0xFF`   | RAM residue of the build buffer                            | *[INFERENCE]*: debug strings ("TITLE : TT_RVARI"); no accessor reads past `+0xA4`         |

The sections follow the header in that order with no gap. In the factory sets only one record
has a dependency section: `03custm3` slot 7 carries a custom-sound block, a user drum kit
("User Kit"; voice names such as "Electric SD", "Snare Drum 2", "Silent" for unused keys). The
block is a `0x27`-byte header, 128 `{program, bank LSB, bank MSB}` references and 128 voice
records of `0x8E` bytes, the tone generator's voice-resource unit (`VoiceRecFetchBanked`,
`VoiceSubRecFetch`, `TgPartLocalEditElemRecPtr`), typed by `VOICE_HEAD`, `VOICE_SUB` and
`VOICE_ELEM`.

**One touch settings.** Four records of `0xA0` bytes (KN6000: `0x90`), one per ONE TOUCH SETTING,
built by library `func_4C02A0C4` (KN6000 `func_4C04B9F8`) from four consecutive PANEL MEMORY
records of the backup SRAM (KN7000: `0x750`-byte records at `0x84000824 + bank*0x3A90 + 0x10 +
i*0x750`; KN6000: `0x700`-byte records at `0x840007D2 + bank*0x3810 + 0x10 + i*0x700`). Each field is copied as `source & mask`
through a table of `{source offset, destination offset, mask}` triples; the macros `PM_PART`,
`PM_ENTRIES`, `PM_STYLE`, `PM_FX` and `PM_PART_TAIL` name each field by its source offset. Two
observations show what wrote the factory files: all 80 KN6000 settings have part 3 all `0xFF`
(the v7.1 writer copies part 3, so an earlier one wrote them), and 82 of the KN7000 settings do
not hold program 941's part tails at `+0x8F`.

## The "TCMP" style container

The CUSTOM container is the MEMORY style area's layout with one style (`MemStyleExportToCustom`,
`0x4843DEC7`). Big-endian.

| offset    | field                                                                                                |
|-----------|------------------------------------------------------------------------------------------------------|
| `+0x00`   | `"TCMP"`, `00 00`; the checksum descriptor `[0x06,0x10)` zero (the export clears it)                 |
| `+0x10`   | u24BE container length; `+0x13` u24BE allocator top: both equal the size here                        |
| `+0x16`   | u16BE style count 1; `+0x18` the template tail `00 60 0D 08 04 02 02 01 02 0F`; 64 spaces at `+0x30` |
| `+0x70`   | style record, `0x80` bytes: name, four variation-name fields, indices 0..19, two u16BE at `+0x70`    |
| `+0xF0`   | 20 variation records of `0xE0` bytes                                                                 |
| `+0x1270` | the 20 event streams, contiguous, the last ending at the container's end                             |

A variation record holds its kind at `+0x00`, a pair flag at `+0x03` (bit 4), eight per-part
bytes at `+0x04`, bars at `+0x10` and meter at `+0x11` (`MemStyleVarBarCount`), the stream offset
at `+0x15`, then eight part set-ups of `0x18` bytes at `+0x20` (`PART_SETUP`). *[INFERENCE]* The
`0x18`-byte set-up is the 24 fields of the part-field table `0x485B77D4` in order; its first 15
are the built-in styles' 15-byte part set-up described on
[Rhythm ROM (IC18)]({{ site.baseurl }}/kn7000-rhythm-rom/#a-style-record-0xc6-bytes).

**Event streams** are `[index][u24BE count][events]`: the index is the variation number
(`MemStyleAreaStreamsVerify`, `0x4843579E`, rejects any other), the count excludes the 4-byte
header, and the events run from a `0xF4` beat marker to `0xF5`, with the event lengths of
`RhyEventLenByStatus` / `RhySysexLen`. All 5,200 streams of the live records (TCMP and TPAD, ten
images) parse to their exact ends: 806,516 events, 2,979,536 bytes, no data byte `>= 0x80`,
every position byte 0-95. The macros are those of the IC18 tree:

| event           | macro       | count   |
|-----------------|-------------|---------|
| `9n` 5 bytes    | `ev_note`   | 398,918 |
| `00-5F`         | `ev_at`     | 261,177 |
| `F4`            | `ev_beat`   | 57,034  |
| `En` 2 bytes    | `ev_bend`   | 49,467  |
| `Bn` 2 bytes    | `ev_cc`     | 31,240  |
| `F5`            | `ev_end`    | 5,200   |
| `F0 04` 4 bytes | `ev_sysex4` | 3,290   |
| `Cn` 3 bytes    | `ev_pc`     | 188     |
| `Dn` 1 byte     | `ev_press`  | 2       |

## The "TPAD" performance-pad container

The PERFORMANCE PAD user memory's layout (`MemPadAreaLoadFactory`, `0x48432175`) with one bank:

| offset   | field                                                                                                             |
|----------|-------------------------------------------------------------------------------------------------------------------|
| `+0x00`  | `"TPAD"`, `00 00`, descriptor zero, length / top u24BE, count 1, template tail `00 60 10 06 10 02 00 00 00 0F`    |
| `+0x70`  | bank record `0x30`: 16-byte name ("User Bank 1"), six `{bank, pad, 0x20}`                                         |
| `+0xA0`  | six pad records of `0x60`: name, 13 setting bytes, u24BE stream offset at `+0x1D`, two part set-ups at `+0x28`    |
| `+0x2E0` | six event streams, same format, index = pad                                                                       |

## Stale records and residue

A record's blocks are programmed whole, from a RAM buffer that still held what was built there
before. So past many records lie the tails of earlier, longer writes (166 records have such
residue), and the free blocks of the nine KN7000 sets are not erased: they hold **41 complete
older records** that no slot lists (their `+0xA4` gives the block they were written for), such as
"Revival Rock" (in 7 sets) and "Soloist Sounds" (4), and one fragment. The complete ones are typed
like live records (`StaleNN.inc`). The 80 "Blank" slots of the eight custom1/custom2 sets are each
`0x237F` bytes. The KN6000 bank has no stale records and no residue.

The residue is typed too, in this order: copies of typed records at the same or any offset
(2,202,310 bytes, spelled with that record's own macros and a comment naming it), whole event
streams and TCMP/TPAD records that no record holds (200,114 bytes), runs that parse as events
(185,705), and what is left, 4,179 bytes in 679 `.incbin_range` entries of the reference, mostly
1-15-byte splinters between matched pieces (partial events, the bytes of a header cut by the
next write). Of the 2,592,308 residue bytes the first rounds declared opaque, 99.84% are now
typed. `scripts/analysis/data_incbin_census.py` measures the trees:

| tree                | opaque (entries / bytes) | generic (entries) | generic (bytes) |
|---------------------|--------------------------|-------------------|-----------------|
| `kn7000-customdata` | 679 / 4,179              | 0                 | 0               |
| `kn6000-customdata` | 0 / 0                    | 0                 | 0               |

## The `.AST` file

`func_4852D0E5` (the whole-bank save) builds a 16-byte header:

| offset  | size | field                                                                                                                                                               |
|---------|------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `+0x00` | 3    | `"J K"` on the KN7000, `"I K"` on the KN6000 (copied from `0x48664308`)                                                                                             |
| `+0x03` | 1    | 1                                                                                                                                                                   |
| `+0x04` | 4    | u32 LE, the inflated size, `0x1E0000`                                                                                                                               |
| `+0x08` | 8    | never written: whatever the stack held (LE words `48582CD3 5006F220` in custom1/custom2's eight files, `485A9C1D 5006ED88` in idd7000's, `0 50052930` in idd6000's) |
| `+0x10` |      | the bank deflated by zlib 1.0.4 (level 6, windowBits 15, memLevel 8), without the 2-byte zlib header but with the big-endian Adler-32 trailer                       |

On load, `AstHeaderIngest` (`0x4848594D`) takes kind `0x17` as the whole-bank file, at most
`0x1E0000` bytes, programmed from `0x96820000`.

**Rebuilding them.** Python's zlib (1.3.1) does not reproduce the payload: it differs at byte 1.
zlib 1.0.4, the version linked in the firmware (its banner is at program file `0x3B8604`), does:
compiled from its C sources it gives `01CUSTM1.AST`'s payload exactly. The difference is in
`_tr_tally`: 1.0.4 may end a block every 4096 symbols when its estimate says the block compresses
well, which later versions compile only with `TRUNCATE_BLOCK`. `kn7000/tools/zlib10_deflate.py`
ports 1.0.4's deflate to Python, and `ast_file.py deflate` rebuilds **all ten** `.AST` files byte
for byte from the banks, the tag and the 8 stack bytes (`make verify-customdata-ast` in both
trees).

## Open questions

- Most panel-memory fields: the map gives each one's source offset in the PANEL MEMORY record, not
  what that offset holds.
- The `0x42`-byte dependency records (five kinds) and the `0x2C8` SOUND EDIT records: none in the
  factory sets, so only their strides are known.
- The voice record's single fields and the custom-sound block's `0x27`-byte header.
- TCMP variation bytes `+0x01`, `+0x02`, `+0x18`, `+0x19`; the style record's two u16BE at
  `+0x70`; the pad record's setting bytes.
- A reader of the 24-field part set-up, to confirm the field order.
- Where the factory sets were made: the residue matches across sets, so one tool built them in
  sequence, reusing its buffer.
