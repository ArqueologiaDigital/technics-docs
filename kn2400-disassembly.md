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

| file offsets          | linked for              | contents                                                                                                                                                                                             |
|-----------------------|-------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `0x000000`-`0x000010` | `0x48400000`            | boot header: `_reset` (jmp to `crt0_start`), 5 nops, `_vector_0a`, one data byte                                                                                                                     |
| `0x000010`-`0x1E427C` | `0x48400000`            | data: names, styles, bitmaps, tables, the `MILK MN10300 Ver1.0R1` banner                                                                                                                             |
| `0x1E427C`-`0x3285BE` | `0x48400000`            | code linked for flash: the application, ending in the MILK kernel's flash tail (`KernelInit` ... `KernelTickIsrDefault`)                                                                             |
| `0x3285BE`-`0x3965BB` | `0x50120000` (work RAM) | code linked for work RAM: much of what the KN7000 keeps in its library, the MILK kernel's services among it (`slp_tsk` `0x5018B821` ... `dly_tsk` `0x5018DE54`, [below](#the-milk-kernels-services)) |
| `0x3965BB`-`0x3965D3` | none                    | 24 bytes after the last instruction                                                                                                                                                                  |

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

**Who copies it there.** The 24 bytes after the last instruction hold, among others,
`0x487285BE` (the range's flash address), `0x50120000` (its link address) and `0x487965B8`: a copy
descriptor (`RamCodeTrailer`). `RamSectionsCopy` (`0x4870587E`), crt0_start's last call before `KernelStart`, walks
the 12-byte records {u16 flags (bit 15 = last), u16 length, u32 source, u32 dest} from `RamCodeTrailer+3`, each
field read byte by byte: {`0x0002`, `0xDFFA`, `0x487285BE`, `0x50120000`} copies the RAM-linked code, `0x6DFFA`
bytes (the next record's source minus this one's), and {`0x8003`, 3, `0x487965B8`, `0x5018FFF0`} copies the
trailer's first 3 bytes (`de 00 00`, `retf [], 0`) to `0x5018FFF0`. So the KN2400/KN2600 copies its RAM-linked
tone-generator library itself (settled 2026-11-02, lane mn10300-names; disassembly
`kn2400/notes/data-region/README.md` and the row of `RamSectionsCopy` in `kn2400/kn2400_manual.sym`). crt0 itself copies only `.data` (`0x6E78` bytes from
`0x485DD334` to `0x50000010`). (Corrected 2026-10-30, lane generic-zero, disassembly
`c65a62c5b`: this paragraph had said no code reads them.)

## The MILK kernel's services

The kernel's services are named after their µITRON 3.0 function codes, as on the KN7000 (lane
uitron-names, 2026-11-07, disassembly merge `49872b9c1`,
[`kn7000/notes/uitron3-function-codes/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/uitron3-function-codes/README.md);
the method, the service list and the specification's licence are on
[KN7000 Firmware Images]({{ site.baseurl }}/kn7000-firmware/#the-milk-kernels-services)). Here the
services sit in the code linked for work RAM, from `slp_tsk` (`0x5018B821`) to `dly_tsk`
(`0x5018DE54`); `wai_sem`, for one, is `0x5018CF54` and its body `wai_sem_Impl` `0x5018CFE0`. Each reports errors to `KernelErrorHook` with d0 = its
function code; the wrapper a task calls is named after the service and the body behind it
`<svc>_Impl`, and `loc_cpu`, `sus_tsk` (`0x5018DB81`) and `ena_dsp` (`0x5018D879`) are called directly.
The 17 routines that report a code all decode to one defined code, and no label disagrees with its code.
Like the KN7000, it has
`sus_tsk` and `rsm_tsk` (`0x5018D8C7`, *[INFERENCE]*: no code and no name of the firmware's own, the
inverse of `sus_tsk`); it lacks `preq_sem` and the services KN7000 program 942 has and 941 lacks
(`ter_tsk`, `ext_tsk`, `del_mbx`, `del_sem`, `del_flg`, `ref_sem`). `LibMsgSend` / `LibMsgReceive`
became `snd_msg` / `rcv_msg` (`0x5018D2FE` / `0x5018D452`). 39 labels changed; `sibling_name_census.py`
counts `func_` labels 11,315 -> 11,254 (routine starts 6,517 -> 6,480; before at `dfd9dfd90`).

## Names

| file                | what it holds                                                                                                                                                                              | names |
|---------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------:|
| `kn2400.sym`        | function names from the firmware's own MILK reflection tables (`gen_symbols.py`), only from tables whose procedures land in the flash-linked code range                                    | 2,277 |
| `kn2400_manual.sym` | names recovered by hand: `_reset`, `_vector_0a`, `crt0_start`, data blocks (`StyleRecordTable`, `TechnicsPadsResource`, ...) and the MILK kernel's tail (`KernelInit`, `KernelStart`, ...) | 20    |
| `kn2400_ported.sym` | names carried over from KN7000 program 941 by `port_names_by_code.py` (`make ported-names`, generated)                                                                                     | 679   |

Counted 2026-10-31 at technics-roms-disasm `f4045a81c` as each file's rows that start with `0x`
(`command grep -c '^0x' kn2400/<file>`).

`port_names_by_code.py` carries a name only when one of this image's unnamed entries is the
same code as a routine the KN7000's symbol files name: the same instructions from the entry
to the first return, with every number of 0x10000 or more masked out (addresses, and MILK
message codes, which are renumbered between models). At least 8 of those instructions must
have nothing masked, and the match must be unique among all of the KN7000's routine starts
and among this image's entries. Each row records the KN7000 address it came from. Since
2026-11-06 a call entry (`func_<ADDR>_entry`, three bytes after an `add -N, sp` prologue) is a
candidate too, so a name the KN7000 gives a routine's call entry is carried. With that and the
lane's new KN7000 names the ported rows went from 746 to 767 (13 of the new rows are those names; KN6000 778 -> 806, KN6500 803 -> 831, HD-SX3 52 unchanged; counted with
`grep -c '^0x'` at disassembly `a385de42f` and after lane kn7000-names,
`kn7000/notes/kn7000-names/README.md`).

**Where the names come from.** The KN6000, KN6500 and KN2400/KN2600 programs carry part of their
own names: the MILK framework's reflection tables name about 1,250 to 2,300 procedures per image
(the tables above), and its function tables some 550 more. Most other names are carried over from the KN7000, whose
program shares much of their code. A routine whose code is the same as a named KN7000 routine
takes its name; since November 2026 a routine too short to be told apart by its code alone (a
getter, a flag setter) takes it too when the routines that call it are the same on both sides and
call it at the same place, or when it uses the same variables. Variables are named the same way:
from the KN7000 when the same instruction of the same routine uses them, from the firmware's own
accessor routines (`GetSeqSongNo` reads `SeqSongNo`), or after the one named routine that uses
them.

The call-site, same-variable and accessor steps are lane sibling-names's (2026-11-06, disassembly
[`kn7000/notes/sibling-names/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/sibling-names/README.md),
merged in `5b72cf364`). `kn7000/tools/port_names_by_alignment.py` (`make aligned-names`, writing
`<model>_aligned.sym`) carries 941's names along the call sites and RAM operands of routines both
images already name; `kn7000/tools/name_ram_by_use.py` (`make ram-names`, `<model>_ram.sym`) names
a RAM address after a named accessor (`GetSeqPlySrtR` / `SetSeqPlySrtR` -> `SeqPlySrtR`) or after
the one named routine that spells it (`R_Ram`, `R_Ram_2`, ...). Every row states its class and its
evidence.

| file                 | rows | by class                                      |
|----------------------|------|-----------------------------------------------|
| `kn2400_aligned.sym` | 236  | call site 182, same body 46, RAM = (941) 8    |
| `kn2400_ram.sym`     | 634  | accessor 21 (125 operands), owner 613 (2,805) |

Counted with `grep -c '^0x'` at `3834c8773`. `kn7000/notes/sibling-names-probes/sibling_name_census.py`
reads the change as `func_` labels 11,645 -> 11,340 (routine starts 6,765 -> 6,538) and numeric
work-RAM operands / addresses 23,931 / 3,565 -> 20,931 / 2,940 (before at `2bde950fa`). The RAM-linked
tone-generator library, the twin of the one 941 links at `0x4C000000`, gained the most: of 941's 544
routine names there, the KN2400 had 332 and has 418. Run where the answer is already known, the
call-site rule is right 650 times and wrong 3 (`TgGlobalRegWriteB` against 941's
`TgGlobalRegWriteBoth`, `FxCategoryGet` / `DspPresetKeyKind`, `AcRcVolumeProc` / `AcMonitorOnProc`,
read as two names for one routine), the same-body rule 190 / 0.

**More ways a KN7000 name reaches a sibling.** Since the second round of November 2026 a
routine also takes a KN7000 name when the routines both models name hand it over the same way:
as a callback (`mov func, d0` at the same place of the same routine), or as an entry of a table
the two routines read at the same place, when the table's other entries that both models name
already agree. Variables are paired the same way and, between two paired variables of one
module, by their spacing, since a relinked module keeps its variables' order. Every rule is
checked where the answer is known, on the routines both models name already; the table rule is
used only with its check, because without it a third of the table entries pair wrongly in the
KN2400.

Lane sibling-names2 (2026-11-06, disassembly
[`kn7000/notes/sibling-names2/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/sibling-names2/README.md),
merged in `0aa9f82f9`) added those rules to `port_names_by_alignment.py`. It also stopped carrying 941's
name for a RAM window's base (`WORK_RAM_BASE`, `0x50000000`): the base is a memory-map constant, not a
variable, and the name had made the data generator cut the KN6000 / KN6500 RAM-test region records
short, so the few operands that composed an address in the window are numbers again.

| file                 | rows | by class                                                  |
|----------------------|------|-----------------------------------------------------------|
| `kn2400_aligned.sym` | 257  | routines 249 (6 of them by pointers alone), RAM = (941) 8 |
| `kn2400_ram.sym`     | 641  | accessor 28, owner 613                                    |

Counted with `grep -c '^0x'` at `8d0865c27`. `sibling_name_census.py` reads the change as `func_` labels
11,340 -> 11,315 (routine starts 6,538 -> 6,517) and numeric work-RAM operands / addresses 20,931 / 2,940
-> 20,908 / 2,933 (before at `e53dc9b3a`). The call-site audit is 674 right / 3 wrong (the same three),
the same-body rule 201 / 0, the table rule 1,684 / 5 left one out, the RAM pairs by spacing 1,900 / 2.
Four of the new names are the KN7000's own since November 2026 (`JpegEncSetup`, `JpegEncImage`,
`JpegEncMcu`, `KeyZoneNoteResolve`). In the RAM-linked tone-generator library the KN2400 has 424 of
941's 544 names (418 before); 30 short routines identical to 941's stay unnamed, because each is told
apart only by one byte variable in a block whose layout the KN2400 changed, so no RAM pair can be right
for them.

**Names from the firmware's own evidence.** Code the SX-KN7000 does not have gets its names by hand
since November 2026, each with the evidence it rests on: the strings it uses, the screens it posts
to, the hardware registers it drives, or a table another image names. Most of it was named in the
SX-KN6000 ([KN6000 / KN6500 / HD-SX]({{ site.baseurl }}/kn6000-disassembly/#names)): its file layer, the
small file-system library beneath it (`FsOpen`, `FsRead`, `FsWrite` ...), the SMF reader, the zlib file
codec. A routine named there passes to the KN2400 when its code, with every address masked, is the
same at the same place in the link order, a rule checked on the routines both models already name
(KN6000 -> KN2400 1,074 alike / 2 unlike, `port_hand_names.py --report`; the two are pairs already
known as two names for one routine). The KN2400's fmm layer sits on the same `Fs` library. Of its own,
the KN2400 got its string helpers (`StrCopy`, `StrAppend`, `StrCopyPad`) and `FileNameWithExt` with its
14-entry `FileTypeExtTable` ("ACT" added to the KN6000's list), 13 load / save bodies named by their file
type (`LoadCmpFile`, `SaveTmFile` ...), two trampoline bodies, `CaptureLcdWriteBmp`, `FsMountVolume`
*[INFERENCE]* and `TestSdImmunityFile`.

Lane sibling-names3 (2026-11-07, disassembly
[`kn7000/notes/sibling-names3/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/sibling-names3/README.md),
merged in `5ee2082dd`) wrote those 66 rows of `kn2400_manual.sym` (48 carried from the KN6000, 15 of them
RAM). `sibling_name_census.py` reads the change as `func_` labels 11,254 -> 11,166 (routine starts 6,480
-> 6,430), named entries 3,478 -> 3,528 and numeric work-RAM operands / addresses 20,908 / 2,933 ->
20,564 / 2,916 (before at `92b5cc4a7`; `kn7000/notes/sibling-names3-probes/census-92b5cc4a7.txt`,
`census-after.txt`); `kn2400_ram.sym` went from 641 to 643 rows.

**941's names of November 2026 reach the KN2400.** In the same wave lane kn7000-subsystems named 2,312
of program 941's unnamed routines by hand
([KN7000 Firmware]({{ site.baseurl }}/kn7000-firmware/#names-from-the-routines-own-code)), and
`make aligned-names` carried them to every KN2400 routine that 941's named routines call at the same
place. The C file layer, the string helpers and the `INSTALL_SCRATCH` cursor, which both lanes had
named, now carry the siblings' names in 941 too. Measured on the merged tree against main `4e1d77a5b`
(disassembly
[`kn7000/notes/kn7000-subsystems/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/kn7000-subsystems/README.md),
merged in `d8aa8ade1`):

| measure                                        | before         | after          |
|------------------------------------------------|----------------|----------------|
| aligned routine names (`kn2400_aligned.sym`)   | 249            | 1,629          |
| call-site audit, right / wrong                 | 674 / 3        | 1,107 / 3      |
| RAM pairs                                      | 3,147          | 3,355          |
| RAM names, `kn2400_ram.sym` (accessor + owner) | 643            | 773 (82 + 691) |
| `func_` labels (`sibling_name_census.py`)      | 11,166         | 8,901          |
| routine starts named `func_`                   | 6,430          | 5,060          |
| named entries                                  | 3,528          | 4,899          |
| numeric work-RAM operands / addresses          | 20,564 / 2,916 | 19,952 / 2,786 |

The census figures are `kn7000/notes/kn7000-subsystems-probes/sibling-census-main-4e1d77a5b.txt` and
`sibling-census-after.txt` (re-run at `486525b6e` with the same result); `kn2400_aligned.sym`'s header
at `486525b6e` reads 1,629 routine names and 9 RAM names.

**Two sibling names that look like one.** The KN2400's `FilePriorityFunc` and the KN7000's
`SdcPanelSwAsFunc` have the same code because both are two-entry choice parameters of one
template; their choice lists (TECHNICS / SMF and SD-AUDIO / SD-SOUND) tell them apart, so each
image's name is right for its own routine (settled 2026-11-06,
`kn7000/notes/kn7000-names-probes/names_choice_func_lists.py`).

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

- Most entries are still `func_<ADDR>` (8,901 `func_` labels after wave 13's lanes sibling-names3 and
  kn7000-subsystems, above; 11,254 after lane uitron-names, 11,315 after lane sibling-names2, as
  `sibling_name_census.py` counts them). The sibling-only code left is largest in the sequencer's core
  (0x4861xxxx-0x4862xxxx), shared with the KN6000 and KN6500, whose names reach the KN2400 from the
  KN6000. The 30 short tone-generator twins stay unnamed: none of their callers in the RAM-linked
  library is named yet. Routines that differ
  slightly from their KN7000 versions need another naming method than exact matching or
  call-site alignment.
- Reflection tables whose procedures are in the RAM-linked range: `gen_symbols.py` assumes
  one link base, so it pairs none of them.
- Most RAM and I/O addresses are still numbers (19,952 numeric work-RAM operands after wave 13; 20,908
  before). Since the data is typed, the code names the data
  addresses it uses by their labels, but not everywhere: the RAM-linked `NoteConvApply` still
  loads `NoteConvRules` as `mov 0x4854b24c, d3`.
- The 4 MiB half of the IC12/IC13 flash pair at `0x48000000` has never been read; see
  [Memory layout]({{ site.baseurl }}/kn2400-kn2600/#memory-layout).
- The routine that copies the RAM-linked code to `0x50120000`.

The tree's own `kn2400/README.md` is the reference for all of the above.
