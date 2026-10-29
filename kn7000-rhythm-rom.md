---
layout: page
title: "KN7000 Rhythm ROM (IC18): the style data"
permalink: /kn7000-rhythm-rom/
---

# The KN7000 rhythm ROM (IC18): "Technics Rhythms"

The KN7000's 4 MB rhythm ROM (IC18, mask ROM `C3CBND000046`; early units fit an IC20 flash at
the same site) starts with the 64 KB [boot ROM]({{ site.baseurl }}/kn7000-boot-rom/). The rest
of the chip is one resource, `"Technics Rhythms"`, at CPU address `0x40010000`: a header, a
style-ID index, **169 styles of 20 variations each** and 8 count-in patterns. All its
multi-byte fields are big-endian, although the CPU is a little-endian MN10300; the firmware
reads them with `LoadU16BE` / `LoadU24BE`.

Since 2026-10-29 the disassembly repository rebuilds the whole chip byte for byte, with every
record and every event typed, one event per line and one file per style, and nothing
`.incbin`'d:

| file                                                                                                                        | what                                                                              |
|-----------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| [`kn7000/src/ic18/ic18.s`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/src/ic18/ic18.s)     | the whole chip: `boot.s` plus `rhythm.s`                                          |
| [`kn7000/src/ic18/rhythm.s`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/src/ic18/rhythm.s) | the header, the index, the tables, the macros and the count-in patterns           |
| [`kn7000/src/ic18/styles/`](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/kn7000/src/ic18/styles)    | one file per style, `styles/<rhythm group>/<style>.s` (169 files in 12 groups)    |
| `kn7000/src/ic18/old_build.s`                                                                                               | the leftovers of an older build past the last style                               |
| `kn7000/tools/gen_ic18_rhythm_s.py`                                                                                         | the generator; it refuses an image whose structure differs from the one described |

    make -C kn7000 verify-ic18-full   # src/ic18/ic18.s -> build/kn7000_ic18.bin, compared with all 4 MB of the chip
    make -C kn7000 ic18-rhythm-src    # regenerate src/ic18/rhythm.s and styles/ (tools/gen_ic18_rhythm_s.py)

`make gate-kn7000` (and so `make gate-all`) runs `verify-ic18-full` beside `verify-ic18`, the
boot ROM's own target. The format notes this page follows are
[`kn7000/notes/ic18-rhythm-rom.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/ic18-rhythm-rom.md);
their figures come from
[`ic18_rhythm_probe.py`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/ic18-rhythm-rom-probes/README.md).
Firmware addresses are program 941's. *[INFERENCE]* marks a reading that no traced code fixes.

## Provenance

The image is pass 4 of the [ROM dumper]({{ site.baseurl }}/kn7000-rom-dumper/) on the owner's
own instrument, read twice and identical both times; it is the same image the boot ROM is cut
from. It is not committed: the Makefile copies it from the private romset to
`baserom/kn7000_ic18.rom` after checking its SHA-1, `2dc71f5082063cd6b21e4ed16acd67e9d326a79f`
(all 4,194,304 bytes). Which chip answers at the IC18/IC20 site of that unit has not been
checked by opening it.

The generator reads three images: IC18 itself, program 941 for the rhythm groups
(`RhythmGenreNameTable`, `0x48735EE4`), which give each style its group, its place in the group
and its style-ID, and table 84 for the names of the 51 styles the index sends to the table ROM.

**In MAME.** The `kn7000_mame` overlay loads this chip as `c3cbnd000046.ic18` at `0x40000000`.
It replaced the synthetic "Technics Rhythms" stand-in described on
[User Data & the Initial Data Disk]({{ site.baseurl }}/kn7000-initial-data/#how-the-rhythm-menu-resolves-a-style-name),
whose 168 placeholder style names only the real chip could supply. Mainline MAME still
declares the part `NO_DUMP`.

## Layout

| file offset         | CPU address  | contents                                            | source label            |
|---------------------|--------------|-----------------------------------------------------|-------------------------|
| `0x000000-0x00FFFF` | `0x40000000` | the [boot ROM]({{ site.baseurl }}/kn7000-boot-rom/) | (`boot.s`)              |
| `0x010000-0x010027` | `0x40010000` | header: signature, checksum, five offsets           | `TechnicsRhythms`       |
| `0x010027-0x010033` | `0x40010027` | count block                                         | `RhythmCountBlock`      |
| `0x010033-0x011033` | `0x40010033` | the style-ID index, 2048 x u16BE                    | `RhythmStyleIndex`      |
| `0x011033-0x01122E` | `0x40011033` | the style table, 169 x u24BE                        | `RhythmStyleTable`      |
| `0x01122E-0x011246` | `0x4001122E` | the count-in table, 8 x u24BE                       | `RhythmCountInTable`    |
| `0x011246-0x0113B2` | `0x40011246` | the 8 count-in patterns                             | `CountIn_1Beats` ...    |
| `0x0113B2-0x3FBAD3` | `0x400113B2` | 169 styles, each a record and its 20 variations     | `Style_8BtStandard` ... |
| `0x3FBAD3-0x3FFC6D` | `0x403FBAD3` | an older build's leftovers                          | `OldBuildStyle_*`       |
| `0x3FFC6D-0x3FFFE8` |              | erased (`0xFF`)                                     |                         |
| `0x3FFFE8-0x3FFFF8` | `0x403FFFE8` | `"jkr_33.ssf"`, NUL-padded                          | `RhythmRomVersion`      |
| `0x3FFFF8-0x3FFFFF` |              | erased                                              |                         |

The count-ins, the styles and their variations tile `0x10000-0x3FBAD3` exactly: 0 bytes
uncovered, 0 covered twice. Each style's 20 variations follow its record with no gap, in the
same slot order in all 169 styles: 12, 13, 16, 17, 0-11, 14, 15, 18, 19.

## The header

`StyleResourceWindowProbe` (`0x4843D6D7`) looks for the signature at five windows; the third is
`0x40010000`. `StyleNameModuleBoot` (`0x4843385E`) then opens the resource with
`StyleBuiltinNameTableInit` (`0x484332F9`). Offsets are from the resource start.

| offset  | type  | value                 | read by, and what for                                                                    |
|---------|-------|-----------------------|------------------------------------------------------------------------------------------|
| `+0x00` | ascii | `"Technics Rhythms"`  | `strncmp` with the firmware's string `0x4872980C`                                        |
| `+0x10` | u16BE | `0xE2DA`              | `StyleResourceVerify` (`0x484338AF`): compared with `SumU16BE` (`0x484403A5`) of a range |
| `+0x12` | u24BE | `0x100000`            | the range's start: file `0x110000`, inside a style's events (not an object boundary)     |
| `+0x15` | u24BE | `0x100000`            | the range's length in halfwords: 2 MB, file `0x110000-0x310000`                          |
| `+0x18` | u24BE | -> `RhythmCountBlock` | the u16BE at +2 of the block is the rhythm count, kept at `0x50034B74`                   |
| `+0x1B` | u24BE | -> the index          | `0x50034B7C`                                                                             |
| `+0x1E` | u24BE | -> the style table    | `0x50034B80`                                                                             |
| `+0x21` | u24BE | -> the count-in table | `0x50034B84`                                                                             |
| `+0x24` | u24BE | -> style 0            | `0x50034B88`, the style `StyleBuiltinNameResolve` falls back to                          |

The checksum recomputes equal; it covers only the middle 2 MB of the chip.

**The count block** is 12 bytes, `00 00 | 00 DC | 00 60 | 0D 08 04 02 02 02`. Only the 220 at
+2 is read: it is the rhythm count, and it bounds the index's style and table-ROM entries. The
rest has no reader. *[INFERENCE]* `0x60` = 96 is the ticks per beat (every position byte in
every stream is 0-95), and the six bytes read as the format's dimensions: a 13-character name,
8 parts, 4 variations, 2 fill-ins each, 2 intros and 2 endings, which makes the 20 slots every
style has.

## The style-ID index

A style-ID (a u32 of the rhythm group lists) is folded to an entry
`((id & 0x0F00) >> 1) | (id & 0x7F)` by `StyleNameSourceSet` (`0x484333FF`); its source bits
`id & 0x00700000` must be 0, the built-in source. 2048 entries cover every folded ID, and
`StyleBuiltinNameResolve` (`0x48433ABF`) reads an entry `e` like this:

| entry        | count | meaning                                                                                       | source spelling    |
|--------------|-------|-----------------------------------------------------------------------------------------------|--------------------|
| `e < 220`    | 169   | style `e` of this resource's style table; each of the 169 appears once                        | `sidx_style SNo_*` |
| `0x8000 + n` | 1828  | read entry `n` instead (one hop)                                                              | `sidx_alias n`     |
| `0x4000 + n` | 51    | style `n` of the table ROM's secondary sub-table (`TableRomStyleSubTablePtr`, `0x48244F78`)   | `sidx_table n`     |

After one alias hop every one of the 2048 entries resolves to a style. So the **220 built-in
rhythms are 169 styles in IC18 and 51 in the table ROM**. Program 941's 14 rhythm groups list
220 IDs, and every IC18 style is in exactly one of them. The chip stores them in group order
(8&16 BEAT, ROCK & POP, ... SOUL & R&B). COUNTRY&WESTERN has one IC18 style (Bluegrass) and 13
from the table ROM; MARCH & WALTZ and LATIN & WORLD come entirely from the table ROM.

**The table ROM's copy.** Table 84 carries a truncated copy of this header and index
(`TechnicsRhythmsTable` in `kn7000/src/table.s`, `0x483E828C`, `0x1248` bytes).
`StyleBuiltinNameTableInit` re-points `0x50034B7C` at that copy's index when it carries the
signature, so with table 84 installed the index the firmware uses is the table ROM's. The copy
differs from IC18's first `0x1248` bytes in 7 bytes: the checksum fields are zeroed, the count is
221, and one index entry differs, which makes room for a 52nd table-ROM style, "70s Orchestra".

## The style table and the count-in patterns

The style table holds 169 u24BE offsets, each spelled `.be24 Style_<name> - TechnicsRhythms`;
entry 0 is the fallback style.

The count-in table holds 8 offsets. Pattern `k` is one bar of `k + 1` beats that sets the drum
part to program `00 00 26` and plays note 37 (side stick in GM numbering) at velocity 64 on every
beat. `StyleRecordSlotSelect` (`0x48433643`) uses one of them for slot 20 through
`StyleVariationNameGet` (`0x484335BF`); the low 3 bits of the bound variation's meter byte pick
which. (The name `StyleVariationNameGet` is a misnomer: it returns a count-in pattern record.)

## A style record (`0xC6` bytes)

Read by `StyleNameCommit` (`0x484334A4`) and `func_484420EF`:

| offset  | size   | field               | evidence                                                                             |
|---------|--------|---------------------|--------------------------------------------------------------------------------------|
| `+0x00` | 13     | name, as displayed  | copied to the name buffer `0x50034B9C` and NUL-terminated there                      |
| `+0x0D` | 4      | two sound-unit keys | `0x50034C20`; `func_484420EF` decodes them                                           |
| `+0x11` | 8 x 15 | eight part set-ups  | `0x50034BAC[i] = record + 0x11 + 15i`; `func_4844187A` copies them to `0x5003A37C`   |
| `+0x89` | 1      | 1 in every style    | no reader found                                                                      |
| `+0x8A` | 20 x 3 | slot offsets        | u24BE, from the record; `0x50034BCC[slot]`                                           |

**Sound-unit keys.** `func_484420C8` decodes each 2-byte pair as a 14-bit value, 7 bits a byte,
low byte first; bit 6 of the second byte adds `0x10000`. `func_484420EF` stores the first pair to
parameter key `0xB044` and the second to `0xB054`, and bit 7 of the first pair's second byte to
key `0xB001`. 88 styles have `44 00 44 00`; the source keeps the four bytes as they are
(`style_units`).

**A part set-up** (15 bytes, `style_part`). Byte `k` is the value of field `k` of the
firmware's part-field table `0x485B77D4`, which holds one (status, controller) pair per field:

| byte | controller | name in the source             | values over 169 x 8 parts                                                                 |
|------|------------|--------------------------------|-------------------------------------------------------------------------------------------|
| 0    | CC97       | `mode`                         | `0x00` on parts 0 and 7 of all 169 styles; `0x08` on the others but 8 parts               |
| 1    | CC7        | `volume`                       | most often 105, 98, 127, 100                                                              |
| 2-4  | program    | `prog`, `bank_lsb`, `bank_msb` | the program change's data bytes; `bank_msb` `0x26` on parts 0 and 7, else `0x20` but 4    |
| 5    | CC94       | `cc94`                         | 64 in every part                                                                          |
| 6    | CC91       | `reverb`                       |                                                                                           |
| 7    | CC93       | `chorus`                       | 0 in 1,221                                                                                |
| 8    | CC10       | `pan`                          | 64 in 929                                                                                 |
| 9    | CC96       | `cc96`                         | 12 in every part                                                                          |
| 10   | CC82       | `cc82`                         |                                                                                           |
| 11   | CC83       | `cc83`                         |                                                                                           |
| 12   | CC80       | `cc80`                         |                                                                                           |
| 13   | CC81       | `cc81`                         |                                                                                           |
| 14   | CC92       | `cc92`                         | 0 in 1,259                                                                                |

Fields 15-23 of the table (CC64, CC1, CC11, channel pressure, pitch bend, CC16, CC17, CC13) are
not in a style's set-up; they start from the default template `0x485B7804`. *[INFERENCE]* The
eight parts are Drum, Bass, Acc1-Acc5 and Perc: parts 0 and 7 have mode 0 and `bank_msb` `0x26`
in every style, and part 1's program is `0x21` (GM finger bass) in 84 styles.

## The 20 slots

| slots | name in the source                               | bars                      | evidence                                                                                                         |
|-------|--------------------------------------------------|---------------------------|------------------------------------------------------------------------------------------------------------------|
| 0-11  | `Var1`, `Var1Fill1`, `Var1Fill2` ... `Var4Fill2` | 4, 1, 1 in all 169 styles | only `slot % 3 == 0` carries a name in a MEMORY style (`MemStyleVarCopy`); `func_4844232B` treats the rest apart |
| 12-15 | `Intro1A/B`, `Intro2A/B`                         | 1-9                       | `func_4844232B` treats `(slot - 12) % 4 < 2` (12, 13, 16, 17) apart from 14, 15, 18, 19                          |
| 16-19 | `Ending1A/B`, `Ending2A/B`                       | 2-10                      | the same; the odd slots are the B halves (the MEMORY pair bit, `0x485B6D74`)                                     |

The two halves of each pair have the same bar count in every style. *[INFERENCE]* The roles
(main pattern, fill-in, intro, ending) follow the panel's VARIATION 1-4, FILL IN 1/2 and
INTRO & ENDING 1/2 buttons and the bar counts. What tells an A half from a B half is not known.

## A variation record

`StyleRecordBindBuiltin` (`0x484336DB`) binds the current one into the pattern player's view:

| offset     | size  | field                         | evidence                                                                         |
|------------|-------|-------------------------------|----------------------------------------------------------------------------------|
| `+0`       | 1     | bars - 1                      | `0x50122DCE`; `StyleBoundRecByteCeInc` + 1 -> `0x5003A452` (`func_48442293`)     |
| `+1`       | 1     | beats a bar - 1               | `0x50122DCF`; `StyleBoundRecByteCfLow3` + 1 -> `0x5003A454`                      |
| `+2`, `+3` | 1, 1  | two part numbers, `0xFF` none | `0x50122DD4`; `func_48442164` stores them as key `0xB048`                        |
| `+4`       | u16BE | set-up length L               | `0x50122DCC`                                                                     |
| `+6`       | L     | set-up events                 | `0x50122DC8`; replayed into the part table by `func_48441DEB`                    |
| `+6+L`     | u24BE | stream length S               |                                                                                  |
| `+9+L`     | S     | the event stream              | start `0x50122DC0`, end `0x50122DC4` = start + S - 1, the `0xF5`                 |

Bytes 2/3 are `FF FF` in 2,710 of the 3,380 variations and `FF 02`-`FF 07` in the rest. The
set-up events are only controllers (22,351) and program changes (4,947). The MEMORY ("TCMP")
variation record holds the same fields in a different layout (bars at `+0x10`, meter at `+0x11`,
the stream offset at `+0x15`, no set-up events); `MemStyleVarBarCount` (`0x4843C445`) gives the
beat-marker count both kinds must hold. The same TCMP layout is used by the
[custom style memory]({{ site.baseurl }}/kn7000-custom-style-memory/#the-tcmp-style-container).

## The event stream

Event lengths are those of `RhyEventLenByStatus` (`0x484403D5`) and `RhySysexLen`
(`0x484403CD`). The low nibble of a status byte is the part.

| first byte  | length | meaning                                                               | count in the 169 styles |
|-------------|--------|-----------------------------------------------------------------------|-------------------------|
| `0x00-0x5F` | 1      | position: the tick in the beat (0-95) of the events after it          | 324,664                 |
| `0x9n`      | 6      | note: key, velocity, then three bytes                                 | 529,662                 |
| `0xBn`      | 3      | controller: CC11 69,771, CC1 24,081, CC64 17,758, CC10 1,593, CC91 20 | 113,223                 |
| `0xDn`      | 2      | channel pressure                                                      | 4                       |
| `0xEn`      | 3      | pitch bend                                                            | 23,491                  |
| `0xF4`      | 1      | beat marker; a stream opens with one                                  | 39,412                  |
| `0xF5`      | 1      | end of stream                                                         | 3,388                   |
| `0xF0`      | 2 + n  | SysEx                                                                 | 0                       |

All 3,388 streams (169 x 20 plus the 8 count-ins) parse to their exact end: each opens with
`0xF4`, ends with `0xF5`, and holds bars x beats beat markers; every data byte is below `0x80`.
The 324,664 position bytes are all 0-95 and never fall within a beat, which is why they read as
positions, not deltas, and why a beat is 96 ticks. An event with no position byte before it is at
tick 0. *[INFERENCE]* A note's last three bytes are its length (two bytes) and a
chord-adaptation class (always 0 on parts 0 and 7); the player that reads them was not traced.

**In the source** each event is one macro line (macros defined in `rhythm.s`):

| macro                                                                 | bytes                          | used for                                                     |
|-----------------------------------------------------------------------|--------------------------------|--------------------------------------------------------------|
| `n part,key,vel,len_lo,len_hi,cls`                                    | `9n key vel len_lo len_hi cls` | a note                                                       |
| `vol`, `pan`, `expr`, `mod`, `sus`, `rev`, `cho`, `mode` `part,value` | `Bn CC value`                  | CC7, 10, 11, 1, 64, 91, 93, 97                               |
| `cc part,ctl,value`                                                   | `Bn ctl value`                 | any other controller (CC80-83, 92, 94 in set-ups)            |
| `pc part,prog,bank_lsb,bank_msb`                                      | `Cn prog bank_lsb bank_msb`    | program change (set-ups only)                                |
| `bend part,lsb,msb`, `pres part,value`                                | `En lsb msb`, `Dn value`       | pitch bend, channel pressure                                 |
| `@<any of the above> tick,...`                                        | `tick` then the event          | the event with the position byte before it                   |
| `beat`, `end`                                                         | `F4`, `F5`                     | beat marker, end of stream                                   |

So `@n 48,0,BD1,64,16,0,0` is a bass drum on part 0 at tick 48 of the beat. On parts 0 and 7 a
key from 27 to 87 is spelled by its GS/GM percussion name (`.equ BD1, 36` ...). *[INFERENCE]*
That the KN7000's kits follow that map rests on table 84's drum-voice records, which list "Bass
Drum 2", "Bass Drum 1", "Side Stick" and "Snare Drum 1" in the GM order of keys 35-38.

## Past the last style

The last style, Bluegrass, ends at `0x3FBAD3`. 16,794 non-erased bytes follow that no table
reaches: the end of an event stream whose start is overwritten, ten whole variation records
(4,1,1, 4,1,1, 4,4, 6,6 bars of 4/4) whose streams occur nowhere else in the chip, and a stream
fragment that starts inside a note event, its last 135 bytes repeated. *[INFERENCE]* In the slot
order every style uses, the ten records are slots 6-11, 14, 15, 18 and 19 of a style that is not
in this build; the source labels them `OldBuildStyle_Var3` ... `OldBuildStyle_Ending2B`. The
chip was mastered over an image of an earlier, longer build, as the boot ROM's first kilobyte
also shows ([The older link]({{ site.baseurl }}/kn7000-boot-rom/#the-older-link)).

## The version string

`"jkr_33.ssf"` at `0x3FFFE8`. `AcRhythmVerBoxProc` (`0x4848895F`) takes the probed window,
subtracts `0x10000`, adds `0x3FFFEC`, reads the decimal digits there and prints them with
`"RHYTHM  : %4d"`: **RHYTHM 33** on the SP7001 DEBUG TOOLS screen. The boot ROM can rewrite this
data on units with an IC20 flash in this site: update kinds 8/9 (`KN7KR1` / `KN7KR2`) and
`KN7KRHY.DAT` on SD ([Boot ROM]({{ site.baseurl }}/kn7000-boot-rom/#floppy-updates)).

## Representation and census

| part                                    | form in the source                                                            | bytes     |
|-----------------------------------------|-------------------------------------------------------------------------------|-----------|
| header, count block, index, tables      | `rhythm.s`: `.ascii`, `.be16` / `.be24` with label differences, `sidx_*`      | 4,678     |
| 169 style records                       | `styles/*/*.s`: `.ascii` name, `style_units`, 8 x `style_part`, `style_slots` | 33,462    |
| 3,380 variation headers + set-up events | `var_head`, set-up events, `var_events`, `var_end`                            | 117,229   |
| 3,380 event streams                     | one event per line                                                            | 3,955,326 |
| 8 count-in patterns                     | `rhythm.s`, typed the same way                                                | 364       |
| the leftovers                           | `old_build.s`: 10 variations and 3 fragments, the same way                    | 16,794    |
| erased flash, the version string        | `.space ..., 0xff`, `.ascii`                                                  | 915       |

They add up to the 4,128,768 bytes from `0x10000`. The text is 171 files, 760,109 lines and
14,378,065 bytes, 3.48 times the binary size, with 0 `.incbin` lines;
`scripts/analysis/data_incbin_census.py` gives the tree `kn7000-ic18` no binary include at all
(0 generic, 0 opaque). Only 2 bytes are `.byte`: the prefix of `OldBuildFragment1`, which starts
inside an event.

The tree needed three additions to the KN7000 assembler `kn7000/tools/kn7asm.py`: `.be16` /
`.be24` / `.be32`; `.macro` / `.endm` with named parameters; and caches that make 760,000 lines
of macro invocations fast (all of IC18 assembles in about 18 s).

## Open questions

- The count block's bytes after the 220 and the style byte at `+0x89` have no reader.
- CC97 (part `mode`), CC94, CC96 and CC80-CC83: the firmware routes them into part fields, but
  what each does to the sound was not traced into the tone generator.
- What the sound-unit key values (`0x0044`, `0x1111`, `0x0B12` ...) select in units
  `0xB040` / `0xB050`.
- The A/B halves of the intros and endings (a major/minor pair would fit, but nothing shows it).
- A note's last three bytes: trace the pattern player that consumes `0x50122DC0`.
- The drum kits' own key names (table 84's drum-voice records), to name keys outside 27-87.
- Which chip answers at the IC18/IC20 site of the owner's unit.

See also: the [Music Stylist Catalog]({{ site.baseurl }}/kn7000-rhythm-catalog/) (a separate
database), and [Custom Style Memory (IC21)]({{ site.baseurl }}/kn7000-custom-style-memory/)
for the user-style copy of the same format.
