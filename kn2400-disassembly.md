---
layout: page
title: KN2400 / KN2600 Disassembly
permalink: /kn2400-disassembly/
---

# KN2400 / KN2600 — the disassembly tree

Since 2026-10-24 the disassembly repository has a folder, `kn2400/`, that rebuilds the
program flash image of the SX-KN2400 and SX-KN2600 byte for byte from MN10300 assembly
source (disassembly commit `9c99a6988`, merged as `921314742`). The KN2600 runs the same
image; see [KN2400 / KN2600 / PR54]({{ site.baseurl }}/kn2400-kn2600/) for how the firmware
tells the models apart.

The tree is made the way the KN7000's is, with the KN7000 tree's own tools, used by relative
path (`../kn7000/tools`) and not copied: the assembler `kn7asm.py`, the source generator
`gen_image_s.py`, the MILK reflection-table walker `gen_symbols.py` and the update-disk
decoders. The [KN6000, KN6500 and HD-SX trees]({{ site.baseurl }}/kn6000-disassembly/) were
made the same way on the same day.

    make kn2400          # from the repository root: assemble the image
    make gate-kn2400     # its byte-identity gate, plus the KN2600 check below

Since 2026-10-29 the data half of the image is typed source too: the 7,322 MILK widget records
with a generated menu map, the Music Stylist setups, the note-conversion tables, the demo songs
and the built-in style and pads. That is on
[KN2400 / KN2600 Program Data & GUI]({{ site.baseurl }}/kn2400-program-data/).

## The reference image is regenerated, not committed

The image is copyrighted and the repository has a public remote, so `kn2400/baserom/` is
git-ignored. `make baserom` rebuilds it from the manufacturer's v1.1 update in the private
customer-service mirror beside the repository (`CA_MIRROR=`), without running any of its
programs:

| step            | tool                               | result                                                |
|-----------------|------------------------------------|-------------------------------------------------------|
| outer archive   | `sfx_extract.py kn24-11.zip`       | `kn24_11a.exe`, `kn24_11b.exe` (self-extracting ZIPs) |
| floppy contents | `sfx_extract.py kn24_11?.exe`      | `LKG1.SLD`, `LKG2.SLD`, `SMCKPR1.INF`                 |
| decompression   | `sld_decompress.py`                | 0x200000 + 0x1965D3 bytes                             |
| join            | `cat`                              | `kn2400_program.rom`, 3,761,619 bytes                 |
| checksum file   | `smck_check.py ... --expect match` | total 0x16DA58C4, 15/15 block sums match              |
| recorded SHA-1  | Makefile `ROM_SHA1`                | `39163ea892baf8ad11419c29fe58cc536bef9ca7`            |

`sfx_extract.py` reads the ZIP archive appended to each self-extracting `.exe`; no DOS
emulator is involved. `sld_decompress.py` falls back to a pure-Python LZSS decoder when
pylzss is not installed.

**The KN2600 check.** The KN2600's own v1.1 package, `kn26-11.zip`, ships the image
uncompressed as `KN24PRG.DAT`. `make verify-kn2600` (part of `make gate-kn2400`) checks that
this file equals `kn2400_program.rom` byte for byte.

## Layout: the data first, and part of the code linked for RAM

| file offsets          | linked for              | contents                                                                         |
|-----------------------|-------------------------|----------------------------------------------------------------------------------|
| `0x000000`-`0x000010` | `0x48400000`            | boot header: `_reset` (jmp to `crt0_start`), 5 nops, `_vector_0a`, one data byte |
| `0x000010`-`0x1E427C` | `0x48400000`            | data: names, styles, bitmaps, tables, the `MILK MN10300 Ver1.0R1` banner         |
| `0x1E427C`-`0x3285BE` | `0x48400000`            | code linked for flash: the MILK kernel and the application                       |
| `0x3285BE`-`0x3965BB` | `0x50120000` (work RAM) | code linked for work RAM                                                         |
| `0x3965BB`-`0x3965D3` | none                    | 24 bytes after the last instruction                                              |

This is the reverse of the KN7000's program image, which has its code first. The last code
range runs at **`file offset + 0x4FDF7A42`**, in work RAM from `0x50120000`. The evidence,
from `kn2400/notes/layout-probes/ram_linked_range.py` (its README has the command):

- the flash code makes 6,876 calls and jumps into `0x50120000`-`0x5018DFFD`, and all of
  them land on an instruction start of that range when it is decoded at that address;
- the range makes 15,011 calls and jumps of its own. Decoded at its flash address, 629 of
  them go nowhere, outside both the image and the RAM window; decoded at `0x50120000`, 5 do;
- a switch table at `0x48405C48` holds `0x50145241`, `0x50145251` and so on, the case
  bodies at file `0x34D7FF`, `0x34D80F` and following under the same offset;
- crt0 points the vector at `0x90000000` to `0x5018DF0B`, which is file `0x3964C9` under
  the same offset.

Much of that range is what the KN7000 keeps in its library at `0x4C000000`: of the 337 names
carried into it from the KN7000 (below), 250 come from KN7000 library routines, many of them
`Tg*` tone-generator routines. The source assembles it under `.mnbase 0x4FDF7A42`, so its
PC-relative encodings are reproduced exactly.

**Open: who copies it there.** The 24 bytes after the last instruction hold, among others,
`0x487285BE` (the range's flash address), `0x50120000` (its link address) and `0x487965B8`,
which fits a copy descriptor (`RamCodeTrailer`). `func_4870587E` reads it, byte by byte from
`RamCodeTrailer+3`, 12 bytes a record (each word assembled little-endian with `asl 8 / 16 / 24`);
what it does with the three words of each record was not traced, so the routine that copies the
range to RAM is still not identified: crt0 copies only `.data` (`0x6E78` bytes from
`0x485DD334` to `0x50000010`). (Corrected 2026-10-30, lane generic-zero, disassembly
`c65a62c5b`: this paragraph had said no code reads them.)

## Names

| file                | what it holds                                                                                                                                           | names |
|---------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|------:|
| `kn2400.sym`        | function names from the firmware's own MILK reflection tables (`gen_symbols.py`), only from tables whose procedures land in the flash-linked code range | 2,277 |
| `kn2400_manual.sym` | names recovered by hand: `_reset`, `_vector_0a`, `crt0_start`                                                                                           | 3     |
| `kn2400_ported.sym` | names carried over from KN7000 program 941 by `port_names_by_code.py` (`make ported-names`, generated)                                                  | 485   |

`port_names_by_code.py` carries a name only when one of this image's unnamed entries is the
same code as a routine the KN7000's symbol files name: the same instructions from the entry
to the first return, with every number of 0x10000 or more masked out (addresses, and MILK
message codes, which are renumbered between models). At least 8 of those instructions must
have nothing masked, and the match must be unique among all of the KN7000's routine starts
and among this image's entries. Each row records the KN7000 address it came from.

Counting the whole image as code would let `gen_symbols.py` name 194 more addresses, from
seven more tables, and those names would be wrong: event-name string tables and the
`DiskMenu` / `SdCardMenu` menu tables, whose pointers lead into data.
`kn7000/notes/sibling-symbol-probes/whole_image_pairings.py` produces those figures.

**Corrected 2026-10-29: 90 names.** `gen_symbols.py` had paired 90 procedures of the SDFM
MainFunctions table (slot `0x213`) 21 entries late, because a name that is not an identifier cut
the name run short. Pairing reflection tables start-aligned fixed them (disassembly `8037f3750`;
`kn2400/notes/data-region-probes/fn_table_pairing.py`: 2,283 entries agree, 0 disagree). The count
in the table above is unchanged; 90 of its names moved to the right addresses.

Every other label is generated with the source (`src/labels.inc`): `func_<ADDR>` for an
entry no table names, `<name>_entry` for the register-save `call` entry behind a named
prologue (the KN7000 convention: `call` saves the registers itself, so callers enter after
the `movm` / `add -N, sp` prologue), and `<entry>_L<offset>` for a branch target.

## How the source is made, and how much of it is code

`src/program.s` is generated by `make program-src` (`../kn7000/tools/gen_image_s.py`, which
needs MAME's `unidasm`):

1. every named entry, every call target, and the functions that sit back to back after them
   are decoded and walked by control flow;
2. only code a traced path reaches becomes instructions, re-encoded by `mn10300_asm` and
   compared with the image. The code halves of the 69 MILK reflection tables in the data are
   `.long` rows of names. Everything else stays `.incbin_range` from `baserom/`, so data is
   never spelled as instructions;
3. an instruction the encoder spells differently becomes a `.byte` escape with the
   disassembly beside it: the compiler's non-minimal `call` / `or` forms and the `udf*`
   coprocessor operations.

The generator writes `kn2400/notes/conversion-stats.txt`. As committed at disassembly `45884293c`
(2026-10-30, unchanged at `39fc875ef`):

| measure                      | value                                                            |
|------------------------------|------------------------------------------------------------------|
| image                        | 3,761,619 bytes, of which 1,778,507 in the code ranges           |
| entries                      | 15,824 (3,014 named, 852 derived `<name>_entry`, 11,958 `func_`) |
| bytes emitted as code        | 1,759,605: 98.94% of the code ranges, 46.78% of the image        |
| instructions                 | 664,654, plus 93 `.byte` escapes                                 |
| unreached code decoded       | 18,862 bytes (`--decode-gaps`), plus 35 bytes of `0xFF` fill     |
| local branch labels          | 60,820                                                           |
| code-range bytes left binary | 0                                                                |

At `2319e9b94` (2026-10-24) 19,350 code-range bytes in 376 pieces were still binary, mostly short
stretches no traced path enters, such as switch cases reached only through RAM-linked jump tables.
`gen_image_s.py --decode-gaps` now decodes them: of those pieces, 324 end in a return or jump, 42
run into the next function's `add -N, sp`, 7 are fill and 2 stop early
(`kn2400/notes/data-region-probes/code_gap_classes.py`).

## Open work

- 11,958 entries are still `func_<ADDR>`. Routines that differ slightly from their KN7000
  versions need another naming method than exact matching.
- Reflection tables whose procedures are in the RAM-linked range: `gen_symbols.py` assumes
  one link base, so it pairs none of them.
- RAM and I/O addresses are still numbers. Since the data is typed, the code names the data
  addresses it uses by their labels, but not everywhere: the RAM-linked `func_50173F49` still
  loads `NoteConvRules` as `mov 0x4854b24c, d3`.
- The 4 MiB half of the IC12/IC13 flash pair at `0x48000000` has never been read; see
  [Memory layout]({{ site.baseurl }}/kn2400-kn2600/#memory-layout).
- The routine that copies the RAM-linked code to `0x50120000`.

The tree's own `kn2400/README.md` is the reference for all of the above.
