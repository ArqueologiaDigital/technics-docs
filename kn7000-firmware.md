---
layout: page
title: KN7000 Firmware Images
permalink: /kn7000-firmware/
---

# KN7000 Firmware Images

Flash images are recovered from the [system-update discs]({{ site.baseurl }}/kn7000-system-update-discs/).
This page describes `kn7000_program.rom` (main firmware, build 941) and
`kn7000_table.rom` (resource archive, build 84); the other builds now held are
listed under [Version numbers](#version-numbers).
Offsets below are file offsets in hex; integers are little-endian **except** the
`.SLD` size field.

## Program image (`kn7000_program.rom`, 0x3F6F01 bytes)

Panasonic **MN10300** code (the MN103002A, an MN1030-series CPU), mapped at CPU address `0x48400000`
(file offset + base). See the [KN7000 overview]({{ site.baseurl }}/kn7000/) for the full memory map.

### Boot header (0x0 – 0x80)

Two absolute jumps and a configuration byte, then `0xFF` fill to the start of code:

```
0x00: dc 7e ff 00 00   jmp  0x4840FF7E     ; reset entry
0x05: cb ×5            nop                  ; padding
0x0a: dc c5 77 0d 00   jmp  0x484D77CF
0x0f: 16               configuration byte   ; 0x15 in v1.5; compared with 0xFF and 0x77 (see MEMORY DUMP Screen)
0x10..0x7f: ff         fill
0x80: code begins
```

`jmp` on the MN10300 is `0xDC` + a 32-bit little-endian target; the stored value
plus the `0x48400000` base gives the destination. There is **no in-image
reset-vector table**: the CPU starts executing at the base of the program flash
itself (the board's MMODE/BMODE straps select that boot mode; MAME sets the reset
PC to `0x48400000`). The library/kernel code at `0x4C000000` is copied out of
this image at boot (see below).

### The library at `0x4C000000` is copied out of this image

The firmware makes **7,965 calls to 298 distinct entry points** at `0x4C000000`:
the **C runtime + MILK kernel**, e.g. `0x4C001A48` (1,201 calls — a
`printf`/`sprintf`-family formatter), `0x4C003051` (a `memcpy`/`strcpy`) and
`0x4C0019D5` (a numeric formatter). That code is **not a separate ROM**. Early in
kernel init `InitializeBlock27` (`0x484D7BBD`) copies ~253 KB from program-flash
`0x487B8FD1` (file `0x3B8FD1`–`0x3F6EE8`, inside code region 2 below) into RAM
that is aliased at both `0x4C000000` and `0x8C000000`. Every entry point the
firmware calls (the highest is `0x4C03DE26`) lies inside that block, so MAME maps
the two aliases to one RAM and runs the real library code, with no dump and no
HLE.

That RAM is IC14/IC15, two 1 Mbit x16 fast SRAMs: 256 KB on chip select CS3, repeating every
256 KB through its 64 MB window ([memory map]({{ site.baseurl }}/kn7000/#memory-map-as-used-by-the-firmware)).
The boot's copy table entry is `{source, 0x4C000000, flags, source end, 0x4C03FFF0}`, followed by
3 bytes copied to `0x4C03FFF0`. The library's length differs per build (the Pinball Fantasies
port's `lib_extent.py` reads it from each image):

| build        | copy table   | source       | library length | free above it, to `0x4C03FFF0` |
|--------------|--------------|--------------|----------------|--------------------------------|
| 893 (v1.3)   | `0x487F55BA` | `0x487B76B1` | `0x3DF02`      | 8,430 bytes                    |
| 929 (v1.4)   | `0x487F6938` | `0x487B8A31` | `0x3DF00`      | 8,432 bytes                    |
| 935 (v1.5)   | `0x487F6E89` | `0x487B8F6D` | `0x3DF15`      | 8,411 bytes                    |
| 941 (v1.6)   | `0x487F6EED` | `0x487B8FD1` | `0x3DF15`      | 8,411 bytes                    |
| 942 (SP7001) | `0x487F8BC7` | `0x487BA785` | `0x3E43B`      | 7,093 bytes                    |

Nothing writes the SRAM above the library. On the owner's unit (program 893) the SURVEY2 dump
of the [ROM dumper]({{ site.baseurl }}/kn7000-rom-dumper/) found power-on noise there after a
whole dumper run: 8,312 of its 8,430 bytes are not zero, with pointer-like words at chance rate.
In program 893 only two instructions name `0x4C03FFF0`, and both concern the 3 copied bytes: a RAM
test at `0x4849FF0C` saves, tests and puts back the 8 bytes from `0x4C03FFF0`, and a check at
`0x4857DE18` tests whether the library RAM's top lies in the work RAM. The library's own variables live
in work RAM (`.bss` from `0x50007F40` in 893). A program of one's own can use the tail
([Work RAM Map]({{ site.baseurl }}/kn7000-work-ram/#ram-a-program-of-ones-own-can-use)).

### The kernel's flash tail

A small part of the MILK kernel is not copied: 1,317 bytes right before the library image, run
from the flash at their flash address. They hold the kernel's version string, its service table,
the RAM layout and parameter words it reads, and 1,113 bytes of code. Until 2026-10-30 the
disassembly took that code for data, because it sits between the data region and the copied image;
`kn7000/tools/gen_program_s.py` now finds it by following every call and jump of the converted
code that lands in the data region (`TAIL_CODE`, `find_tail_code()`), writes it as
`src/<build>/program/tail_code.s` and ends the data region where it starts (`tail_code.txt`, read by
`gen_data_s.py`). Program 941 (lane code-island,
[`kn7000/notes/code-island/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/code-island/README.md)):

| CPU (941)    | bytes | name                        | what it is                                                                                                                                                       |
|--------------|-------|-----------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `0x487B8AAC` | 24    | `Str_MILK_MN10300_Ver1_0R1` | the kernel's version string and two 0xFF pad bytes                                                                                                               |
| `0x487B8AC4` | 128   | `KernelServiceHash`         | 16 x {u32 key, case address}: `KernelWaitRelease` probes it by `(key & 0xF) * 8` and jumps through `+4`; typed `REC_KernelServiceHash`                           |
| `0x487B8B44` | 24    | `KernelRamLayout`           | 6 RAM addresses; +0x14 is `KernelStart`'s stack pointer                                                                                                          |
| `0x487B8B5C` | 28    | `KernelParams`              | 14 u16 = 10, 20, 20, 20, 10, 10, 10, 10, 10, 10, 20, 10, 30, 0; read at +0 (`get_tid`), +0x10, +0x12 and +0x16                                                   |
| `0x487B8B78` | 695   | `KernelInit`                | `KernelStart`'s `jmp` target: fills the kernel's RAM tables, creates the task `KernelTimerTask`, calls `KernelInitHook`                                          |
| `0x487B8E2F` | 364   | `KernelWaitRelease`         | a `movm` + `add -0x10, sp` prologue, then `KernelWaitRelease_entry`; the 11 cases `KernelServiceHash` points at are its labels                                   |
| `0x487B8F9B` | 3     | `KernelErrorHook`           | `retf 0, 0`; 26 calls, each before a service returns an error (d0 = its µITRON 3.0 function code, d1 = a µITRON error code; [below](#the-milk-kernels-services)) |
| `0x487B8F9E` | 3     | `KernelErrorHook2`          | `retf 0, 0`; 3 calls, the same arguments                                                                                                                         |
| `0x487B8FA1` | 3     | `KernelWaitAbortHook`       | `retf 0, 0`; `KernelTimerTask` calls it with a0 = the task's control block, d0 = -0x55 (E_TMOUT)                                                                 |
| `0x487B8FA4` | 11    | `KernelStart`               | `mov (KernelRamLayout+20), a3 / mov a3, sp / jmp KernelInit`; jumped to from the reset code and from `func_4C03DD98`                                             |
| `0x487B8FAF` | 3     | `KernelInitHook`            | `ret 0, 0`, called by `KernelInit`                                                                                                                               |
| `0x487B8FB2` | 31    | `KernelTickIsrDefault`      | the kernel's default system-tick interrupt handler, which nothing enters: the application installs its own (below)                                               |

**`KernelTickIsrDefault`** (lane mn10300-typer, 2026-10-31, [`kn7000/notes/mn10300-typer/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/mn10300-typer/README.md), section 4; was
`func_487B8FB2`). It clears bits 4..7 of G6ICR `0x34000118`, acknowledging interrupt group 6, calls
the kernel's wake-up of the task `(0x50380000)` points at (E_OBJ when it is dormant, E_QOVR at 0x7FFF
queued wake-ups) and returns with `rets`: the interrupt-handler shape. `LibIrqScheduler` (lib
`0x4C03DE26`) reads the accepted group from `0x34000200`, finds the request in GxICR, maps it through
the RAM table `0x50380A6C` to an index and calls the handler from the RAM table `0x50380B64` with
`calls (a2)`. KernelInit fills that table with the default `loc_4C03DEE9`, and the def_int service
`KernelDefInt` installs a handler from a packet {attribute, handler, level, ICR address}. The only
def_int of G6ICR is the application start-up's (`KernelTickTaskInit`, which KernelInit calls): interrupt 1,
handler `KernelTickHandler` (lib `0x4C02BB05`, the 1 kHz tick), level 6. No word of the program, table
or IC18 image holds `0x487B8FB2`, no instruction names it and no branch reaches it, so it is the kernel
configuration's default tick handler, which the application replaced *[INFERENCE]*. All four models
have it right after `KernelInitHook` and install their own tick handler the same way
([KN6000 / KN6500 / HD-SX Disassembly]({{ site.baseurl }}/kn6000-disassembly/#the-two-program-images)).

The routine names are *[INFERENCE]* from what the code does; the table names are the KN6000's. The
block sits at the same distance from the library image in every build, so the tail code starts at
`LIB_FILE_BASE - 0x459`:

| build        | library image (file) | tail code (file)       | `KernelInit` | `KernelWaitRelease` | `KernelStart` |
|--------------|----------------------|------------------------|--------------|---------------------|---------------|
| 941 (v1.6)   | `0x3B8FD1`           | `0x3B8B78`..`0x3B8FD1` | `0x487B8B78` | `0x487B8E2F`        | `0x487B8FA4`  |
| 942 (SP7001) | `0x3BA785`           | `0x3BA32C`..`0x3BA785` | `0x487BA32C` | `0x487BA5E3`        | `0x487BA758`  |
| 935 (v1.5)   | `0x3B8F6D`           | `0x3B8B14`..`0x3B8F6D` | `0x487B8B14` | `0x487B8DCB`        | `0x487B8F40`  |
| 893 (v1.3)   | `0x3B76B1`           | `0x3B7258`..`0x3B76B1` | `0x487B7258` | `0x487B750F`        | `0x487B7684`  |

The KN6000, KN6500 and KN2400 keep the same routines, under the same names
([KN6000 / KN6500 / HD-SX Disassembly]({{ site.baseurl }}/kn6000-disassembly/#the-two-program-images)).
`func_487B8E34`, which the data region used to declare as 301 opaque bytes, was the address of
`KernelWaitRelease_entry`; `KernelTaskReadyRemove_Table` (then `func_4C03B799_Table`), "353 x s16", is 3 x s16 ([Program Data Region]({{ site.baseurl }}/kn7000-data-region/#the-kernels-flash-tail)).

### Region map

| Range                    | Contents                                                                                                                                                                                                                                                                                                                                |
|--------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `0x000080` – ~`0x186000` | Main firmware code (region 1)                                                                                                                                                                                                                                                                                                           |
| ~`0x185DC0` – `0x186208` | `float64` decibel-ratio table (137 IEEE-754 doubles, e.g. `1.25892544` = 10^0.1)                                                                                                                                                                                                                                                        |
| ~`0x186208` – `0x3B8B78` | Data / resources: multi-language UI text, FAT boot template, flash-chip ID strings, RGB palettes, fonts, GUI resource tables, 8 JPEGs, two Windows `.BMP` images; typed source since 2026-10-29 ([Program Data Region]({{ site.baseurl }}/kn7000-data-region/)); it ends in the kernel's flash-resident tables, `0x3B8AAC` – `0x3B8B78` |
| `0x3B8B78` – `0x3B8FD1`  | The MILK kernel's flash tail: 1,113 bytes of code run from the flash, `KernelInit` .. `KernelTickIsrDefault` ([below](#the-kernels-flash-tail))                                                                                                                                                                                         |
| `0x3B8FD1` – `0x3F6F01`  | Code region 2: the library image the boot copies to `0x4C000000`, the `MILK MN10300` kernel + zlib 1.0.4 and the C runtime                                                                                                                                                                                                              |

### The MILK kernel's services

**The MILK kernel is a µITRON 3.0 kernel.** Its services report errors to an empty hook,
`KernelErrorHook` (or `KernelErrorHook2`), with d0 = the service's µITRON 3.0 function code and
d1 = a µITRON error code. The function codes are those of the TRON Association's "µITRON 3.0
Specification", Ver 3.02.00 (document I-01-02E), section 6.3; read as a signed number, the 16-bit
code is what the firmware passes (`cre_tsk` is H'ffef = -17). So the codes name the services, in
the KN7000's program builds 893 (v1.3), 935 (v1.5), 941 (v1.6) and 942 (SP7001) and in the
SX-KN6000, KN6500 and KN2400 alike; lane uitron-names (2026-11-07, disassembly merge `49872b9c1`,
[`kn7000/notes/uitron3-function-codes/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/uitron3-function-codes/README.md))
named them in all seven MN10300 trees.

The specification's licence allows it to be reproduced only in its entirety, so neither the
disassembly nor this page reproduces any part of it. The codes below are facts about the firmware,
cited to the document, version and section; the official text is
[mitron3.02.txt.Z](https://www.ertl.jp/ITRON/SPEC/FILE/mitron3.02.txt.Z), and the disassembly's
`fetch_spec.sh` downloads it (checking its sha256) for `function_codes.py`, which parses it each time
it runs and does not commit it.

**Wrapper and body.** A task calls most services through a small *wrapper*: `add -4, sp / mov d1,
(0, sp)`, the register save with `udf15 d3, d3` (unless the call is nested), a switch to the kernel
stack and a call of the *body*, which does the work and reports the errors. The wrappers are almost
the same bytes for every service. The disassembly names the wrapper after the service, as program
942's export table does (its `wai_sem`, `unl_cpu` ... are wrappers), and the body `<svc>_Impl`
(`wai_sem` / `wai_sem_Impl`), the way `DrawBox` / `DrawBox_Impl` were already named. `loc_cpu`,
`sus_tsk` and `ena_dsp` (and 942's `ref_sem` and `ter_tsk`) are called directly and keep the plain
name; `ena_dsp`'s one caller is `unl_cpu_Impl`. The SP7001 build exports 20 kernel services by name
to its plug-in and 10 more through small forwarders (`cre_tsk_X`, `snd_msg_X` ...); wherever a name
and a code meet, they agree (`function_codes.py --selftest`: PASS).

| service                         | how it is named: the function code its body reports (d0), the errors seen (d1), or 942's name | called                        | builds without it     |
|---------------------------------|-----------------------------------------------------------------------------------------------|-------------------------------|-----------------------|
| `rel_blk`                       | -143 (H'ff71); E_PAR, E_OBJ                                                                   | wrapper                       | none                  |
| `get_blk`                       | -141 (H'ff73); E_OBJ, E_TMOUT                                                                 | wrapper                       | none                  |
| `cre_mpl`                       | -137 (H'ff77); E_NOMEM                                                                        | wrapper                       | none                  |
| `rcv_msg`                       | -61 (H'ffc3); E_CTX; 942's `rcv_msg_X` calls it                                               | wrapper (was `LibMsgReceive`) | none                  |
| `prcv_msg`                      | -61, rcv_msg's code: the polling variant; 942's `prcv_msg_X` calls it                         | wrapper                       | none                  |
| `wai_sem`                       | -53 (H'ffcb); E_CTX                                                                           | wrapper                       | none                  |
| `preq_sem`                      | -53, wai_sem's code: the polling variant; 942 export                                          | wrapper                       | KN2400                |
| `wai_flg`                       | -46 (H'ffd2); E_CTX                                                                           | wrapper                       | none                  |
| `wup_tsk`                       | -39 (H'ffd9); E_QOVR                                                                          | wrapper                       | none                  |
| `slp_tsk`                       | -38 (H'ffda); E_CTX                                                                           | wrapper                       | none                  |
| `sus_tsk`                       | -33 (H'ffdf); E_OBJ, E_QOVR                                                                   | directly                      | KN6000, KN6500        |
| `ena_dsp`                       | -29 (H'ffe3); E_CTX                                                                           | directly                      | none                  |
| `rot_rdq`                       | -28 (H'ffe4); E_CTX                                                                           | wrapper                       | none                  |
| `chg_pri`                       | -27 (H'ffe5); E_ID, E_CTX                                                                     | wrapper                       | none                  |
| `ter_tsk`                       | -25 (H'ffe7); E_OBJ                                                                           | directly                      | 941, 935, 893, KN2400 |
| `exd_tsk`                       | -22 (H'ffea); E_OBJ                                                                           | wrapper                       | none                  |
| `ext_tsk`                       | -21 (H'ffeb); E_OBJ                                                                           | wrapper                       | 941, 935, 893, KN2400 |
| `cre_tsk`                       | -17 (H'ffef); its core's result (E_NOMEM = -10)                                               | wrapper                       | none                  |
| `loc_cpu`                       | -8 (H'fff8); E_CTX                                                                            | directly                      | none                  |
| `unl_cpu`                       | -7 (H'fff9); E_CTX                                                                            | wrapper                       | none                  |
| `snd_msg`                       | 942's `snd_msg_X` calls it                                                                    | wrapper (was `LibMsgSend`)    | none                  |
| `cre_mbx`, `cre_sem`, `cre_flg` | 942's `cre_mbx_X`, `cre_sem_X`, `cre_flg_X` call them                                         | wrapper                       | none                  |
| `set_flg`, `sig_sem`, `sta_tsk` | 942 export                                                                                    | wrapper                       | none                  |
| `del_mbx`, `del_sem`, `del_flg` | 942 export                                                                                    | wrapper                       | 941, 935, 893, KN2400 |
| `ref_sem`                       | 942's `ref_sem_X` calls it                                                                    | directly                      | 941, 935, 893, KN2400 |
| `rsm_tsk`                       | *[INFERENCE]*, below                                                                          | wrapper                       | KN6000, KN6500        |

A name from 942 reaches the other builds and models through a body that is the same code with labels
and addresses masked. **Two services report another's code**: `preq_sem`'s body passes wai_sem's -53
and `prcv_msg`'s rcv_msg's -61, each with d1 = the result of the poll core it shares with the waiting
service (E_TMOUT, -85, when the poll fails). The code alone would name them `wai_sem` / `rcv_msg`; 942's
export table names the one wrapper `preq_sem`, and its forwarder `prcv_msg_X` calls the other.

**`rsm_tsk` *[INFERENCE]*.** One wrapper has no function code (its body reports no error) and no name
of the firmware's own (941 `0x4C03D7E2`, 942 `0x4C03DB4A`, 893 `0x4C03D7CF`, KN2400 `0x5018D8C7`). Its
body counts the task's suspend count (TCB +0x12) down by one and, at zero, makes the task ready or
clears its suspend bit: the inverse of `sus_tsk`, and `sus_tsk`'s callers call it in mirror order
(`sus_tsk(7)`, `sus_tsk(3)`, work, `rsm_tsk(3)`, `rsm_tsk(7)`). µITRON's `rsm_tsk` returns E_OBJ for a
task that is not suspended; this body does not check.

**Renamed.** `LibMsgSend` and `LibMsgReceive` (the disk worker's mailbox calls) are `snd_msg` and
`rcv_msg`; every other renamed routine was a `func_<ADDR>` placeholder. Routine starts still named
`func_`, before (disassembly `dfd9dfd90`) and after:

| tree         | labels changed | `func_` routine starts before | after |
|--------------|----------------|-------------------------------|-------|
| 941 (v1.6)   | 39             | 6,327                         | 6,290 |
| 942 (SP7001) | 44             | 6,331                         | 6,289 |
| 935 (v1.5)   | 39             | 6,324                         | 6,287 |
| 893 (v1.3)   | 39             | 6,316                         | 6,279 |
| KN6000       | 41             | 5,671                         | 5,632 |
| KN6500       | 41             | 5,698                         | 5,659 |
| KN2400       | 39             | 6,517                         | 6,480 |

The HD-SX3 plug-in has no kernel of its own: it calls the host's `dly_tsk`, `dis_int` and `ena_int`
through registry slot 0x107. Still `func_`: the kernel's inner routines that no wrapper calls directly
and that report no code (the poll cores, the ready-queue and wait-queue helpers); the function codes say
nothing about them.

**`loc_cpu` was never mislabelled.** Notes of 2026-11-06 read code -8 as `clr_flg` in some trees and
`ena_int` in others. That was the probe's error: it skipped every label starting `loc_` (meant for the
local `loc_<ADDR>` labels), so `loc_cpu`'s code went to the routine before it. In all seven trees the
routine that reports -8 is labelled `loc_cpu`, and its body is µITRON's `loc_cpu`; `clr_flg` and
`ena_int` are right too. The probe is fixed (disassembly `kn7000/notes/sibling-names2-probes/`).

### Version numbers

The package labels come from the download filenames: `kn7-16` is the v1.6
program update, and `kn7-14` is the four-disk v1.4 update, whose table disks
(3–4) the table image comes from. The firmware carries **its own internal build
numbers**, unrelated to those:

| Component | Value   | Where                                                                                                                  |
|-----------|---------|------------------------------------------------------------------------------------------------------------------------|
| PROGRAM   | **941** | `u16` at file `0x33660C` (the loader reads 32 bits but keeps only the low half), shown by `PROGRAM : %4d` (`0x1D67E0`) |
| TABLE     | **84**  | ASCII `"84\n"` at table file `0x139EE8`, reached via the pointer at table offset `0x1C`                                |

Three more program builds have since been recovered from update disks, and all
four have been MAME BIOS options since
[mamedev/mame#16394](https://github.com/mamedev/mame/pull/16394) (2026-10-11):
**942** with table **83** (Key Soft Service's SP7001 PLUG-iN update, stamp at CPU
`0x48737630`; see [SD PLUG-iN]({{ site.baseurl }}/kn7000-sd-plugin/)), **935**
(v1.5, complete, stamp at `0x487365A8`) and the upper half of **929** (v1.4; its
first program floppy is lost).

RHYTHM and PICTURE versions are read from devices not covered by these
updates (the rhythm ROM and the picture ROM IC19 at `0x57800000`; the picture ROM has
since been read from an instrument, see [Picture ROM (IC19)]({{ site.baseurl }}/kn7000-picture-rom/)).

PROGRAM and TABLE are what the instrument's hidden **SOFT VERSION** screen
prints; RHYTHM and PICTURE appear only on the developer DEBUG TOOLS screen. At least one surviving KN7000 reports `PROGRAM : 893` / `TABLE : 80` —
an earlier pair of images, unpreserved until that instrument's own chips were read on
2026-10-19 with the [ROM dumper]({{ site.baseurl }}/kn7000-rom-dumper/); see the
[SOFT VERSION screen]({{ site.baseurl }}/kn7000-soft-version/).

9,472 bytes of that earlier pair have since been transcribed by hand from
photographs of the instrument's own hex viewer. They put build 941 at build 893
**plus several insertions totalling 6,451 bytes** in the program half, and plus a
single 3-byte insertion in the table half. It is a transcription and **not a
dump**, and no reconstructed image exists — see
[Recovering build 893]({{ site.baseurl }}/kn7000-build-893-recovery/), and
[Reading ROM out of the screen]({{ site.baseurl }}/kn7000-rom-from-the-screen/)
for the capture route meant to replace hand photography.

### Notable strings

- Version screen: `SOFT VERSION` (`0x1D5AD8`), `--- SOFTWARE VERSION ---` (`0x1D5D9C`), `PROGRAM : %4d` / `TABLE   : %4d` / `RHYTHM  : %4d` / `PICTURE : %4d` (`0x1D67E0`+)
- Kernel banner `MILK MN10300 Ver1.0R1` (`0x3B8AAC`); zlib deflate/inflate banners (`0x3B8604` / `0x3B863C`)
- FAT boot template `Technics    NO NAME    FAT12   FAT16` (`0x1BA4BB`)
- Flash-chip IDs `MBM29LV160B`, `MX29LV160B`, `AT49BV16X4` (`0x1CF9E0`+): the table at `0x485CF9E0` of parts the firmware accepts for the custom-data flash IC21, checked against the chip's autoselect ID before it programs it
- Model-compatibility list `@Expansion Board KN7000 SOUND RAM`, then `KN6000`/`KN5000`/`KN3000`/`KN2000`/`KN1600 SOUND RAM` (`0x1B8517`+)
- UI languages: English / German / French / Spanish / Indonesian message blocks (Italian has a menu entry but no translated text), plus an EUC-JP developer easter-egg entry at `0x1A0C4D`
- Developer symbol tables: `_TT_*` tag names, `*Proc` window-procedure names (`AcProgVerBoxProc`, `IvMpVerWinProc`, …), `MT_*` API names (`MT_GetLanguagePtr`, `MT_FLASHWRITE`), GUI object names (`PanelSimulator`, `ClipBoard`, `DefaultWindow`) — the same conventions as the KN5000 (see [Shared Codebase Map]({{ site.baseurl }}/technics-shared-codebase/))

### Embedded images

8 JPEGs (at file `0x19E7FC` and `0x336AD0`..`0x35EB2B`; the files of `kn7000/src/program/data/media/`) plus two genuine Windows `.BMP` files — a 26×46 1bpp treble-clef icon at
`0x19E704` and a 160×100 8bpp photo at `0x345718`. Unlike the KN5000's
headerless raw 8bpp bitmaps, the KN7000 uses standard file formats for at least
part of its artwork, and none of the KN5000 bitmap pixel data is reused.

## Table image (`kn7000_table.rom`, 0x3E94D4 bytes)

A resource archive fronted by an offset directory:

| Offset  | Contents                                                                                                                               |
|---------|----------------------------------------------------------------------------------------------------------------------------------------|
| `0x000` | 85 × `uint32` little-endian offsets: `dir[0]=0x200` (first segment) … `dir[84]=0x3E94D4` (= file size, end sentinel) → **84 segments** |
| `0x154` | zero padding to `0x200`                                                                                                                |
| `0x200` | segment data                                                                                                                           |

Segment *i* spans `dir[i]..dir[i+1]`. The 84 segments break down as **57
baseline JPEGs** (built-in demo slideshows, all verified decodable, 160×80 up to
640×240) and 27 tagged data chunks whose first bytes are an ASCII type tag
(`TCMP`, `TPAD`, `JK`, …). Two 4-byte segments hold the ASCII strings `"84\n"`
(the table version) and a `"ZZZ\n"` placeholder.

In the disassembly (since 2026-10-24, commits `c8d16a271`, `b7f9b8a68`, `5db37967b` and
`dafa442b3`, merged as `70b363ca5`), `kn7000/src/table.s` spells the directory as offsets to
84 labelled segments, named by `tools/table_segments.py`. The 57 JPEG segments, and the 102
pictures of the six picture-group segments, are files in `kn7000/src/table/`. The help texts
(four language indexes, page lists and the texts as `.ascii`) and the GUI resource tables (366
bitmap, frame and icon rows and 12 font descriptors) are typed. Since 2026-10-29 the rest is
typed too: the raw pictures are indexed PNG files that the build packs back, the styles and pads
are event streams one event per line, and the 'TCMP', 'TPAD', 'ZZZJ' and 'JK' (voice archive)
containers are typed records. The data-incbin census reads no generic bytes left in table 84; see
[Table ROM: what the data is]({{ site.baseurl }}/kn7000-table-rom/#what-the-data-is-the-source-tree-2026-10-29).

> **Where the image stops is not where the chip stops.** IC16 + IC17 are one
> 8 MB flash pair spanning `0x48000000`–`0x487FFFFF`, with this table image as the
> lower half and the program image as the upper half. The table payload ends at
> `0x483E94D3`, which leaves **`0x483E94D4`–`0x483FFFFF` (92,972 bytes)** that no
> standard update ships. The SP7001 PLUG-iN table update is a full `0x400000`
> bytes and writes its plug-in code and strings there (up to `0x483FB59F`); what a
> stock unit holds in that range has never been read. See
> [Where does the flash updater live?]({{ site.baseurl }}/kn7000-firmware-security/#45-where-does-the-flash-updater-live).

The SP7001's table, build 83, keeps this layout: 78 of its 84 segments are
byte-identical to build 84's. It differs in the version string (`"83\n"`), in three
more 4-byte markers (segments 68–70, `"80\n"` where build 84 has `"84\n"`), in one
shorter data segment, and in a 4-byte stub where build 84 has a `Tech` asset. Its
plug-in starts at `0x483E8000`; see
[SP7001 Firmware]({{ site.baseurl }}/kn7000-sp7001-firmware/#table-83-against-table-84).

## Byte-exact disassembly project

The `kn7000/` folder of the [`technics-roms-disasm`](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/kn7000) repository (until 2026-10-19 the separate
`kn7000_disassembly`) holds a reconstruction project for the
MN10300 firmware. Because no GNU binutils MN10300 target is available in common
distributions, it ships a small self-contained assembler whose only job is
byte-exact reconstruction: the source starts as a skeleton in which every byte is
pulled in verbatim (a raw range), and reverse engineering proceeds by replacing
those ranges with real disassembled instructions and typed data. A `make verify`
step asserts the rebuilt images stay **100% byte-identical** to the originals at
every step. Disassembly listings are generated with MAME's `unidasm`
(`-arch mn10300`).

This mirrors the KN5000 approach, whose
[ROM reconstruction]({{ site.baseurl }}/rom-reconstruction/) rebuilds sixteen TLCS-900 images
byte-identically from source; `make gate-all` there covers those, the KN7000 images
(`make gate-kn7000`: programs 941, 935 and 893, tables 84 and 80, the IC18 boot ROM and the whole
IC18 rhythm ROM, the SP7001 set, the picture ROM, the four wave ROMs, the custom-data banks and
the seven Style Convert converters) and the four MN10300 sibling trees in one run.

### 2,302 functions named by reusing KN5000 knowledge

The disassembly gets a large head start from the
[shared codebase]({{ site.baseurl }}/technics-shared-codebase/): the KN7000 embeds the same "MILK"
UI-toolkit **runtime reflection tables** the KN5000 does — code-pointer arrays
each followed by an index-parallel name-pointer array, used by the firmware's
`MT_GetProcedure`-style lookup. There are **~114 such tables** (one per
widget/handler group), and parsing them all recovers **2,302 named functions** —
`SleepMainTask`, `DispatchEvent`, and the whole `Ac*`/`Vw*`/`Ps*`/`Iv*`/`Tt*`
widget window-procedure set (518 `*Proc` + 353 `*Func` handlers), i.e. the **same
names documented for the KN5000**. These become the named anchors for the
instruction-level disassembly. Build 942 adds a table of its own, the services it
exports to SP7001 plug-ins by name; 186 of those names belong to routines build 941
has too, and they now name them in build 941's disassembly as well
([details]({{ site.baseurl }}/kn7000-sp7001-firmware/#the-export-table)).

### Readable, re-assemblable source

With a purpose-built MN10300 encoder (99.9% round-trip) wired into
the assembler, named functions are converted from raw bytes into real MN10300
source that still rebuilds byte-for-byte. Call targets are resolved to labels —
recovered names where known, else a synthetic `func_<ADDR>` for the internal
helpers — so the reconstruction reads like ordinary source. For example the
object-visibility accessor `SetVisible`:

```
SetVisible:                        # CPU 0x4842D3DF
    movm    [d2], (sp)
    add     -0xc, sp
    mov     d1, d2                 # the requested state
    call    GetViewInstance, 0, 0  # a0 = the view object
    cmp     0, d2
    beq     0x4842d3fa
    add     0xc, a0
    movhu   (a0), d0               # its flag word
    and     0xfffe, d0             # state != 0: clear bit 0 (shown)
    movhu   d0, (a0)
    bra     0x4842d403
    add     0xc, a0
    movhu   (a0), d0
    or      0x01, d0               # state == 0: set bit 0 (hidden)
    movhu   d0, (a0)
    ret     [d2], 0x10
```

Since 2026-10-24 every function of code region 1 and of the library image is converted this
way (disassembly commits `47737623a` and `d87382628`, merged as `069d6000b`).
`tools/coverage_score.py` reports all 3,658 function blocks converted, 670,646 instruction
lines and no `.byte` escape, and counts 44.58% of the image's bytes, 1,853,232 of 4,157,185,
as real source (it was 3.88% before, with 998 functions converted by hand-picked sets). The
data region, file `0x186000`-`0x3B8FD1`, was still `.incbin_range` then, apart from the typed
display palette. Since 2026-10-29 it is typed source too, generated from the code that reads it:
the 8,509 GUI widget records ([Menu Map]({{ site.baseurl }}/kn7000-menu-map/)), the demo songs,
the built-in style, panel memories, struct arrays and the resource-id trie
([Program Data Region]({{ site.baseurl }}/kn7000-data-region/)). The data-incbin census reads
no generic bytes left in build 941 since lane generic-zero (snapshot `data-incbin-2026-10-30-02`;
the 177 pieces of 2,948 bytes in `-01` became records and reader rows), and in the current snapshot,
`data-incbin-2026-10-30-04` (as in `-03`), opaque 3449 / 63,392 B. The functions read by hand before the bulk conversion keep
their notes, among them the task/event and display/object framework clusters, the complete
Techni-Chord harmony engine and the complete control-panel serial protocol (the
`PanelTransaction`/ISR/state-machine chain that drove the MAME panel HLE).

The converted source is symbolic. Every function keeps its symbol-file name as a label; a
function no symbol file names yet is `func_<ADDR>`; every branch target is a label,
`loc_<ADDR>` unless something names it. A function that can also be reached through a pointer
starts with a register-save prologue (`movm [regs], (sp)` and/or `add -N, sp`) and is entered
by `call` right after it, so its label sits on the prologue and `<name>_entry` on the `call`
entry. Naming the `func_` functions and the `loc_` labels is the next step.

### Names from the routines' own code

**Most of the program's routines have names now.** Beyond the 2,302 names the firmware's own
reflection tables give and the hand-named modules, a pass in November 2026 read the remaining unnamed
routines of program v1.6 (build 941) range by range and named 2,312 of them, each from evidence in its
own code: the strings it prints or compares, the named routines it calls and how, the variables and
hardware registers it uses, or the table that lists it. Each name's evidence is recorded beside it in
the symbol file. Among them are both copies of the floppy-controller driver (the same code as the IC18
boot ROM's `Fdc*` routines: the copy entered on strap 3 is `FdcStrap3*`, the program's own `FdcPrg*`),
the FAT file system (`Fat*`) and the SD-card layer, the song memory of the sequencer (song records,
256-byte pages, the read and write cursors), the tempo clocks, the performance-pad and composer
editors, the SD audio player (`SdAud*`), the slide show (`Ssw*`), the PC COMMUNICATION protocol and the
kernel's queues. The names reach program v1.3 (893), v1.5 (935) and the SP7001 build (942) by the same
code, and the KN6000, KN6500 and KN2400 wherever their code calls the same routines in the same places
([KN6000 / KN6500]({{ site.baseurl }}/kn6000-disassembly/#names),
[KN2400]({{ site.baseurl }}/kn2400-disassembly/#names)).

Lane kn7000-subsystems (2026-11-07, disassembly
[`kn7000/notes/kn7000-subsystems/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/kn7000-subsystems/README.md),
merged in `d8aa8ade1`) wrote them as one section of `kn7000/kn7000_manual.sym`, each row
`0xADDR  Name  ; [CLASS] evidence`, and `check_proposals.py` checked every row (well formed, new in every
MN10300 tree, on a 941 `func_` routine start, with a class). The classes, as `name_tally.py` counts them
(a row with two classes counts in both):

| class  | the name comes from                                                                              | rows  |
|--------|--------------------------------------------------------------------------------------------------|-------|
| STR    | a firmware string the routine itself uses                                                        | 218   |
| TABLE  | a firmware table that names it or its slot                                                       | 103   |
| WRAP   | its whole body is one call of a named routine with constant arguments, or a named routine's twin | 90    |
| CALLEE | what it does, read from the named routines it calls and the arguments it passes them             | 922   |
| CALLER | its callers are all in one named subsystem, and its body does what the name says                 | 613   |
| RAM    | the named RAM it reads or writes                                                                 | 759   |
| IO     | the named I/O registers or hardware windows it drives                                            | 168   |
| BODY   | a self-contained helper whose body alone shows what it computes                                  | 1,201 |

Routines still named `func_<ADDR>` (`kn7000/notes/kn7000-subsystems-probes/placeholders.py`, at main
`4e1d77a5b`, the merge base, and after; re-run at `486525b6e` with the same result):

| build      | before | after | named by the lane |
|------------|--------|-------|-------------------|
| 941 (v1.6) | 6,282  | 3,970 | 2,312             |
| 942        | 6,281  | 3,970 | 2,311             |
| 935 (v1.5) | 6,279  | 3,967 | 2,312             |
| 893 (v1.3) | 6,271  | 3,968 | 2,303             |

The names reach 942, 935 and 893 through the offset map (`make -C kn7000 symbols-sp7001 exports-941
symbols-935 symbols-893`); the few that do not reach a build sit in code it lacks or rewrote. The C file
layer, the string helpers and the `INSTALL_SCRATCH` cursor, which lane sibling-names3 named in the
KN6000 and KN2400 at the same time, take the siblings' names in 941 too (`FsOpen`, `FsMountVolume`,
`FileNameWithExt`, `StrCopy`, `ScratchPosReset` ..., in place of the lane's first names), so each routine
has one name across the models.
The readers also reported that `StyleIdArrayHandler` is the style parts' MIDI event output (it maps
`status & 0x0F` through `StylePartToTgPart` and sends the event on), not a builder of style-ID arrays;
the name is kept for now. 3,970 routines are left, and the ones the siblings pair by call sites are the
next names with the widest reach.

### Calling convention

The compiled code of the SX-KN7000 and of the other MILK models (KN6000, KN6500, KN2400, the HD-SX
plug-in) passes arguments the same way. Lane callee-walk (2026-10-30,
[`kn7000/notes/callee-walk/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/callee-walk/README.md))
established it from the code, so that the data typer could follow a block's address into the routine
it is passed to:

| what                   | where                                                                                            | evidence (program 941)                                                                                                                                                                                                                   |
|------------------------|--------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| pointer arguments 1, 2 | `a0`, `a1`                                                                                       | `DrawString_entry` (`0x48425398`): `mov a1, (0x3c, sp)` "&pen", `mov a0, (0x38, sp)` "&clip rect", with a frame of 0x30: their homes at +8, +12                                                                                          |
| number arguments 1, 2  | `d0`, `d1`                                                                                       | `DrawString`: `mov d0, d3` font index, `mov d1, d2` fg colour                                                                                                                                                                            |
| the rest               | the caller's `(N, sp)`, N = 16, 20, 24 ...                                                       | `DrawString` reads its string at `(0x40, sp)` = the caller's `(0x10, sp)`; `SetApTimer` (`0x48429C95`) its fifth argument at `(0x4c, sp)`, frame 0x34 = the caller's `(0x18, sp)`, which `TestDiskFunc` stores with `mov d0, (0x18, sp)` |
| the callee's frame     | `movm [regs], (sp)` (4 bytes a register) + `add -K, sp`, or the call's `call F_entry, [regs], K` | `SetApTimer`: `movm [d2,d3,a2,a3]` + `add -0x24, sp` = 0x34, the K of `call SetApTimer_entry, [d2,d3,a2,a3], 0x34`; `DrawString_Impl`'s `add -0x188, sp` after its `_entry` label                                                        |

So a word the caller stores at `(N, sp)`, N >= 16, and a read of `(N + frame, sp)` in the callee before
it writes there are the same parameter. The words below 16 are the return address and the homes the
callee spills its own `a0` / `a1` to; taking `(8, sp)` for an argument carried a caller's local into
the HD-SX3's `func_97834719` (measured, then excluded). Return values come back in `a0` (a pointer)
or `d0` ([`fread_api`]({{ site.baseurl }}/kn7000-sp7001-homebrew/#reading-files-from-the-sd-card)
returns its count in `d0`, `fopen_api` its FILE in `a0`). How the data typer uses this is on
[Program Data Region]({{ site.baseurl }}/kn7000-data-region/#blocks-a-routine-is-handed).

### A second target: the SP7001 firmware

The same repository rebuilds the SP7001 firmware (program 942, table 83) and its
plug-in program `BASEEXT.XAP` byte-exactly too. It does so by carrying everything
recovered for build 941 across, not by starting again. An exact alignment of the two
builds shows program 942 is build 941 plus a few small edits. It names every byte that
moved, so build 941's function split, names, converted functions and notes all
transfer. Only the code that is new in 942 had to be read afresh. See
[SP7001 Firmware: What Changed, and the Plug-in]({{ site.baseurl }}/kn7000-sp7001-firmware/).
