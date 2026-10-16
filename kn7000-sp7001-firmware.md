---
layout: page
title: "SP7001 Firmware: What Changed, and the Plug-in"
permalink: /kn7000-sp7001-firmware/
---

# The SP7001 firmware: what changed, and how the plug-in works

Key Soft Service's [SD PLUG-iN (SP7001)]({{ site.baseurl }}/kn7000-sd-plugin/) shipped its
own KN7000 system update: **program build 942** ("v1.6 PLUG-iN") and **table build 83**, plus a
plug-in program, `BASEEXT.XAP`. All three are now disassembled byte-exactly alongside the
standard firmware (program 941, table 84), and this page records what that showed: how little
of the firmware actually changed, how the plug-in is installed, validated and called, and how
the update disks account for every byte of the dumped table.

The work reused what was already recovered for build 941 instead of starting over, and the
method generalises to any two builds of the same firmware; see
[Cross-version diffs]({{ site.baseurl }}/cross-version-diff-guidebook/#across-a-relocation-map-first-then-diff).

## The update disks

The SP7001 update was distributed as four self-extracting ZIP "disks". The project reads the
archives' members directly and never runs the executables:

| archive                   | members                                                               | payload                            |
|---------------------------|-----------------------------------------------------------------------|------------------------------------|
| `PROGR1_2v1.6PLUG-iN.exe` | `TECHNICS.PR1`, `SMCKPR1.INF`, `DUMMY.2`, `HAMA1.SLD`                 | program, `0x200000` bytes          |
| `PROGR2_2v1.6PLUG-iN.exe` | `TECHNICS.PR2`, `SMCKPR2.INF`, `DUMMY.2`, `HAMA2.SLD`                 | program, `0x1F8BDB` bytes          |
| `table1_2.exe`            | `TECHNICS.TB1`, `SMCKTB1.INF`, `DUMMY.2`, `JKT1.SLD`                  | table, `0x200000` bytes            |
| `table2_2PLUG-iN.exe`     | `TECHNICS.TB2`, `SMCKTB2.INF`, `DUMMY.2`, `JKTBL2.SLD`, `BASEEXT.XAP` | table, `0x200000` bytes, + plug-in |

The payloads use the standard [`.SLD` container]({{ site.baseurl }}/kn7000-system-update-discs/)
(`JKPRG4K`, `JKTB14K`, `JKTB24K`). For the table, the disks account for every byte:

- **Both table payloads are byte-identical to the dumped table 83.** Disk 1 decompresses to
  exactly `0x000000`–`0x1FFFFF` and disk 2 to exactly `0x200000`–`0x3FFFFF`, including the plug-in
  and the erased flash after it.
- **The shipped checksum file describes an earlier table.** `SMCKTB1.INF` and `SMCKTB2.INF` are
  identical. They match, in the total and in all 16 block sums, the 0x3E0660-byte table *without*
  the plug-in and with three version markers (segments 68–70, below) reading `83` instead of
  `80`. As shipped those markers read `80` (block 14 is off by exactly −9, i.e. 3 × ('0' − '3')),
  and the plug-in is appended. That is the precise content of "the SP7001 checksum predates the
  final payload".

The program's two disks are likewise byte-identical to the dumped program 942: `HAMA1.SLD` and
`HAMA2.SLD` decompress to exactly `0x000000`–`0x1FFFFF` and `0x200000`–`0x3F8BDA`. Their
`SMCKPR*.INF` predates the build and matches none of the images held (unlike the table's, there is
no earlier program image on hand for it to match).

## Program 942 is build 941 plus a few edits

A byte comparison of the two program images reports 83% of the bytes different. That number is
misleading: every byte after a small insertion shifts, and every pointer and call displacement
across the shift changes. Aligning the images first (unique 24-byte anchors every 0x100 bytes,
then an exact byte alignment inside each gap) shows the real difference: **42 insertions totalling
7,692 bytes and 30 deletions totalling 306 bytes**, net +7,386 bytes, which is exactly the growth
of the image from `0x3F6F01` to `0x3F8BDB` bytes.

| where (942)                                          | change             | what it is                                                                                                                                         |
|------------------------------------------------------|--------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| `InitializeObjectTable` (`0x4842A5xx`)               | net +2 bytes       | four small instruction rewrites                                                                                                                    |
| the `InitializeBlock30`–`47` stub run                | −3, −16 bytes      | the 3-byte `InitializeBlock46` stub removed; that name now points at new code                                                                      |
| `0x4858598B`–`0x48585E8F`                            | **+1,285 bytes**   | **new code**: `InitializeBlock46`, the plug-in host, 35 forwarders and accessors                                                                   |
| `0x486BD3B8`–`0x486BDEE7`                            | **+2,864 bytes**   | the names of the services exported to plug-ins (`loc_cpu`, `unl_cpu`, …), then the plug-in API's own strings (`PAPI`, `iplugapi`, `XAPR`, `1.0.4`) |
| `0x487B1B9D`–`0x487B231C`, `0x487B234C`–`0x487B2353` | **+1,928 bytes**   | `InitializeBlock46`'s object records and the export table                                                                                          |
| library `0x4C0036EA`                                 | +87 bytes          | `rand` and `srand`                                                                                                                                 |
| library tail (`0x4C03C507`–)                         | +1,289 / −61 bytes | the µITRON kernel grows: `preq_sem`, `del_tsk`, `sta_tsk`, `get_tid`, `clr_flg` are new                                                            |

Everything else is the same code, shifted by +0, +2 or −17 bytes in code region 1 and by up to
+7,386 bytes further up. **All 2,302 functions the firmware names in its own reflection tables are
present in both builds; none was added or removed.** Carried across through the alignment, 2,291
of those names land exactly where build 942's own tables put them. The other 11 are explained: ten
sit in a run of byte-identical 3-byte `InitializeBlockNN` stubs, where deleting one stub is
ambiguous to any alignment, and the eleventh is `InitializeBlock46`, rewritten into the new code.
Of the 1,623 names recovered by hand for build 941, 1,622 carry over.

Addresses outside the image moved too. Work-RAM variables shared by both builds sit 0, +8 or
+16 bytes higher (new globals; the frame buffer moves from `0x500D4080` to `0x500D4090`), and the
library image the boot copies to `0x4C000000` starts at program file offset `0x3BA785` instead of
`0x3B8FD1`.

## The plug-in host

The new code validates a plug-in in table flash and calls into it. It follows the same `XAPR`
extension convention as the KN5000's [HD-AE5000 expansion ROM]({{ site.baseurl }}/hdae5000-homebrew/)
(a 4-byte signature, a present flag, an initialisation entry called with a workspace pointer, and
an entry called on every main-loop pass), the one the KN7000's standard firmware
[no longer has]({{ site.baseurl }}/kn7000-firmware-security/#2-the-expansion-connector--a-capability-that-was-removed)
for its expansion connector. Here it is pointed at table flash, and the slots are assigned
differently:

| routine (942)           | address      | does                                                                                                       |
|-------------------------|--------------|------------------------------------------------------------------------------------------------------------|
| `PlugInProbe`           | `0x48585B95` | compares `XAPR` at `0x483E8000` and at the footer `*(0x483E8004)`; sets `PlugInPresent` (RAM `0x500066D0`) |
| `PlugInProbeCallSlot08` | `0x48585C02` | probes again, then calls header slot `+0x08` with `a0 = 0x5011FABC`                                        |
| `PlugInCallSlot0C`      | `0x48585BE8` | calls slot `+0x0C`; the library main loop calls this once per pass (`0x4C02BE74`)                          |
| `PlugInCallSlot10`      | `0x48585C27` | calls slot `+0x10` with `d0`/`d1`, or returns −1 when there is no plug-in                                  |

| header offset | KN5000 HD-AE5000 ROM           | SP7001 plug-in                             |
|---------------|--------------------------------|--------------------------------------------|
| `+0x00`       | `XAPR`                         | `XAPR`                                     |
| `+0x04`       | version/ID word                | pointer to a second `XAPR` (the footer)    |
| `+0x08`       | boot init (workspace pointer)  | init (`a0 = 0x5011FABC`)                   |
| `+0x0C`       | `RET`                          | called every main-loop pass                |
| `+0x10`       | frame handler, every main loop | call with `d0`/`d1`, returns a value       |
| `+0x14`–      | `RET`                          | ten unused slots, all pointing at a `rets` |

Both firmwares compare the signature with a string compare: on the KN7000 it is the library's
`strncmp` (`LibStrncmp`, `0x4C00203C`).

## The export table

Build 942 also exports services to the plug-in **by name**. A code-pointer array at
`0x487B1BB8`, a NUL word and a name-pointer array at `0x487B1F5C` (the same shape as the MILK
reflection tables) pair 231 names with routines. The pairing is offset by one: `name[k]` names
`code[k+1]`, and `code[0]` (zero) and the last name are unpaired. That was not assumed; it was
checked against what four µITRON interrupt services must do on the MN10300, where PSW bit 11 is the
interrupt enable. Only this pairing makes `loc_cpu` and `dis_int` clear it (`and 0xf7ff, psw`) and
`ena_int` set it (`or 0x0800, psw`), and it also makes every `Set*`/`Reset*`/`Check*` triple store
1, store 0 and read the same variable.

The 231 exports are 64 library routines (the µITRON kernel services, `rand`, `srand`, …), 132
firmware functions (`ResetSdSavePM3Bank`, `PutM3Non`, …) and the 35 new forwarders and accessors,
which the firmware itself calls `cre_tsk_X`, `snd_msg_X`, `malloc_X`, `fopen_api`, `decomp`,
`putstr`, `GetVRAMAddr` and `GetWRAMAddr` (they return the two draw planes the compositor turns into the LCD frame), `GetTimBase` (a 2 ms counter) and so on. **228 of these
names are new**: build 941's tables never named those routines. Because the routines exist in
build 941 too, 186 of the names also apply to it, and they are now used in build 941's disassembly;
the other 42 are exactly the code that only build 942 has.

## Table 83 against table 84

Table 83 has the same 84-segment directory layout as table 84, and **78 of the 84 segments are
byte-identical**. The six that differ:

| segment    | table 84               | table 83               | note                                                                                          |
|------------|------------------------|------------------------|-----------------------------------------------------------------------------------------------|
| 7          | `84\n`                 | `83\n`                 | the table version shown on the [SOFT VERSION screen]({{ site.baseurl }}/kn7000-soft-version/) |
| 59         | data, `0x13980C` bytes | data, `0x131BDC` bytes | 31,789 bytes removed from its end, and two small edits near its start (net −3 bytes)          |
| 68, 69, 70 | `84\n` each            | `80\n` each            | three more 4-byte version markers                                                             |
| 83         | `Tech`, `0x1248` bytes | `DMY`, 4 bytes         | an asset replaced by a stub                                                                   |

After the directory image, which ends at `0x483E0660`, the flash is erased up to `0x483E8000`,
where the plug-in starts.

## The plug-in in table flash

The block at `0x483E8000`–`0x483FB59F` (79,264 bytes) is Key Soft Service's resident application,
"KSS" in its own names:

| range (CPU)               | content                                                                                                 |
|---------------------------|---------------------------------------------------------------------------------------------------------|
| `0x483E8000`–`0x483E803B` | the header above                                                                                        |
| `0x483E803C`–`0x483EF6C4` | code, 30,345 bytes, all disassembled                                                                    |
| `0x483EF6C8`–`0x483FB59B` | data: field-name strings, widget tables, messages, the activation keystream, two MILK reflection tables |
| `0x483FB59C`              | the footer, `XAPR` again                                                                                |

Its reflection tables name 35 routines: the UI screens and widgets `Ap_CE_Main`, `Ap_Ce_StartUp`,
`Ap_Ce_Fd2Sd` (floppy to SD), `Ap_Ce_JukeBox`, `AcKssScreenMenuProc` and others. The
[activation gate]({{ site.baseurl }}/kn7000-sp7001-activation/) lives here too: `KssPasswordCheck`
(`0x483EE8E9`), `KssActivationApply` (`0x483EE921`), `KssKeyCompare` (`0x483EF0AF`),
`KssKeyTransform` (`0x483EF1AD`), `KssHash275` (`0x483EF275`) and the 27 keystream records at
`0x483F8B74`.

The plug-in also loads further plug-ins. `KssPluginLoad` (`0x483EEAA9`) logs `PluginLoad id=%i`,
opens `A:\%s.XAP` (floppy) or the SD-card path, rejects a file over `0x1D000` bytes, reads exactly
`0x1D000` bytes to **work RAM `0x5029B000`**, and calls the first byte with `a0` = the framework
object, `a1 = 0x502992E4`, and `d0`/`d1` pointing at two results. Only after that call does it
check them: the plug-in id it was asked for, and a compile id that must equal the base plug-in's
(`Compile id's dont match: base=%i != baseext=%i`). That matches the vendor's account of using
"hardware ROM and SD card": the resident block in table flash, plus code loaded from the card.

## BASEEXT.XAP

`BASEEXT.XAP`, on table disk 2, is the plug-in the SP7001 setup copies to the SD card (the
resident plug-in reports *"BaseExt.xap wurde auf der SD Card nicht gefunden!"* when it is
missing). It is 118,784 = `0x1D000` bytes, an absolute image linked for the address
`KssPluginLoad` reads it to:

| file range          | content                                                                                                                    |
|---------------------|----------------------------------------------------------------------------------------------------------------------------|
| `0x00000`–`0x1321D` | code, entered at byte 0 (`XapEntry`), all disassembled                                                                     |
| `0x1321E`–`0x16B4B` | data: 391 strings (SD-card prompts, the song and lyrics screens, in German and English), pointer tables, a C `ctype` table |
| `0x16B4C`–`0x1CFFF` | erased (`0xFF`): the space its variables occupy at run time                                                                |

`XapEntry` saves the two pointers it is given, initialises, and returns its plug-in object
(`0x502B1E50`), its compile id, and **plug-in id 3**. It does not call the firmware directly: at no
load address does any of its `call` instructions land on a known firmware routine. Instead it is
handed the firmware's **MILK framework object** — `*(0x50299298)`, which it saves at
`0x502B4044` — and reaches every firmware service through that object's method table. Its `+0x1C`
field points at a **static method vtable in program flash at `0x487280D0`** (a MILK reflection
table), so each call can be named by reading the slot: `+0xEC` is `RegisterObjectTable`, `+0x108`
`SendEvent`, `+0x10C` `PostEvent`, `+0x27C` `RegisterTitle`. **639 of the plug-in's 1,340 indirect
calls resolve through that one table to named firmware methods** — `SendEvent` (285 calls),
`PostEvent` (89), `InheritedProc` (76), `SetVisible` (65), `GetViewInstance` (35), `SetApTimer`,
`ApFuncCall`, `GetClientBox`, the drawing/dial/box helpers, `SleepMainTask`/`WakeUpMainTask`. The
resident plug-in's own init (`func_483E8071`) drives the same table the other way: it calls
`RegisterObjectTable` (`+0xEC`) with the plug-in's 11 class ids and name tables, exactly as the
KN5000's HD-AE5000 `Boot_Init` registers its titles. The remaining 701 calls dispatch through other
MILK objects the plug-in is given or creates (view instances, its own objects). It also
links its own copy of the compiler runtime; seven routines are byte-identical to named firmware
routines: `LibStrncmp`, `LibDiv32`, `abs` and four soft-float helpers (`LibF64Unpack`,
`LibF64UnpackedToI32`, `LibI32ToF64`, `LibF64Abs`).

The load address is the one the loader uses, and the file agrees: 122 of its pointers land on
function prologues if it is placed at `0x5029B000`, and one if it is placed 16 bytes either side.
(A vote on pointers to its strings seemed to favour another address; that came from a single
variable, the saved framework object at `0x502B4044`, read 970 times.)

## Reproducing

Everything above is reproduced by the `kn7000_disassembly` repository (unpublished, like its
source images), whose `notes/sp7001-build-diff.md` gives the full numbers:

| target                         | checks                                                                    |
|--------------------------------|---------------------------------------------------------------------------|
| `make verify-sp7001`           | program 942, table 83 and `BASEEXT.XAP` rebuild byte-for-byte from source |
| `make verify-sp7001-floppy`    | the two table disks against the dumped table, and the checksum files      |
| `make verify-sp7001-progdisks` | the two program disks against the dumped program 942                      |
| `make verify`                  | build 941 / table 84, with the names carried back from build 942          |
| `make symbols-sp7001`          | carry the build-941 names to 942/83 and check them against 942's tables   |

The sources are generated: program 942 from build 941's function split, conversions and notes,
carried through the alignment (544 code-region-1 and 437 library functions as MN10300 assembly,
the 40 new routines among them), table 83 with the plug-in's code as assembly, and `BASEEXT.XAP` as
loaded at `0x5029B000`.

## Answered, and still open

- **What does `BASEEXT.XAP` call?** (above) The firmware only, through the MILK framework object.
  Its `+0x1C` method table is a static vtable at `0x487280D0`, so 639 of the plug-in's 1,340
  indirect calls are named firmware methods (`SendEvent`, `PostEvent`, `SetVisible`,
  `GetViewInstance`, …). The remaining 701 dispatch through other MILK objects it is handed or
  creates; naming those needs their object vtables pinned.
- **Does `KssPluginLoad` run before the plug-in is activated?** Yes. In `Ap_Ce_StartUp` the load
  case reads the latch `0x50299070`, calls `KssPluginLoad(id=3)` to read `BASEEXT.XAP` to
  `0x5029B000` and run it, then sets the latch; the activation status `0x502992C4` is read only
  after the load returns, and the password gate is on user-action paths. So the base extension
  loads and runs on a never-activated unit; activation releases features, it does not gate the
  load. (This is what makes a [dumper plug-in]({{ site.baseurl }}/rom-dumping-roadmap/#method-b--read-it-with-the-instruments-own-cpu-no-desoldering)
  a clean route: an `.XAP` in place of `BASEEXT.XAP` runs at startup.)
- **Program 942 against its two disks.** `make verify-sp7001-progdisks`: `HAMA1.SLD` + `HAMA2.SLD`
  decompress to exactly program 942. Their `SMCKPR*.INF` predates the build (as the table's did),
  and matches none of the images held.
- **Is this release the "Update V2.0" of the product page?** Still open — see
  [SD PLUG-iN]({{ site.baseurl }}/kn7000-sd-plugin/#open-questions).
