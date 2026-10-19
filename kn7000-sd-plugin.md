---
layout: page
title: "SD PLUG-iN (SP7001) and the reserved plug-in region"
permalink: /kn7000-sd-plugin/
---

# The SD PLUG-iN (SP7001), and the reserved plug-in region

> ### Update, 2026-10-16 — the plug-in mechanism is traced
>
> Program 942, table 83 and `BASEEXT.XAP` are now disassembled byte-exactly, and the
> mechanism this page asks about is traced end to end; the details are on
> [SP7001 Firmware: What Changed, and the Plug-in]({{ site.baseurl }}/kn7000-sp7001-firmware/).
> In short: program 942 is build 941 plus a small **plug-in host** that checks for an `XAPR`
> block at table address `0x483E8000` and calls entries in its header (the same convention as
> the KN5000's HD-AE5000 expansion ROM), plus a table of **231 services exported to plug-ins by
> name** (the µITRON kernel calls, file and compression routines, buffer accessors). The `XAPR`
> block, written by the second table disk, is Key Soft Service's resident application. It holds
> the activation gate and a loader, `KssPluginLoad`, which reads an `.XAP` file of up to
> `0x1D000` bytes from the floppy or SD card to **work RAM `0x5029B000`** and calls its first
> byte. `BASEEXT.XAP` is such a file, linked for that address. The two table disks are also
> byte-identical to the dumped table, and the "stale" table checksum is now explained exactly.

> ### Update, 2026-10-08 — the PLUG-iN firmware has now been found
>
> The SP7001 program ("v1.6 PLUG-iN") and table updates were located and
> reconstructed from their update `.SLD` payloads. The customized **program**
> image (CRC `7bc3e247`; flash halves ic17 `4c91678f` / ic16 `7a7990ec`) **does**
> contain the `PLUGIN API` and `XAPR` strings that build 941 lacks (the `SP700`
> strings are in the update's table, build 83), and the update also
> ships **`BASEEXT.XAP`** — 0x1d000 bytes of MN10300 code (it begins `cf 30` =
> `movm`), the plug-in program the firmware copies from the SD card into the
> reserved region. So the reserved-region / SD-load path is no longer
> hypothetical; it can now be reverse-engineered directly. ⚠ Provenance caveat:
> the SP7001 program's shipped `SMCK` checksum does **not** verify the
> reconstructed image (the shipped `.INF` predates the final `.SLD` rebuild);
> the table verifies except its top two 256 KB blocks (the plug-in customization).
> Hashes: MAME's `kn7000` ROM definitions (the `sp7001` BIOS). The reproducer
> scripts are in the project's unpublished research notes (`kn7000-sp7001/`).
>
> It is now a **MAME BIOS option** too: `kn7000 -bios sp7001` runs the SP7001
> program/table, merged upstream as
> [mamedev/mame#16394](https://github.com/mamedev/mame/pull/16394) on 2026-10-11.
> The reserved region and the SD-load protocol can be reverse-engineered from
> this image and `BASEEXT.XAP`.
>
> The product's **licence activation** has since been reverse-engineered end to
> end and a genuine password recovered for the emulator's serial — with an
> in-browser key generator. See
> [SP7001 Activation & Key Generator]({{ site.baseurl }}/kn7000-sp7001-activation/).


A commercial add-on sold for the KN7000 from about 2002 (the vendor's pages are
© 2002; the PLUG-iN release preserved here is V1.0 of 23 August 2003) —
**KEY SOFT SERVICE's "SD PLUG-iN", product code SP7001** — extended the keyboard's
software through the SD card. That is interesting for two reasons this project
cares about:

1. It is direct, third-party evidence that the KN7000 OS has a **reserved region
   for plug-in code that is loaded from the SD card**. A legitimate SD *code-load*
   entry point therefore exists — somewhere.
2. It is **not in the stock firmware.** Program build 941
   ([SOFT VERSION]({{ site.baseurl }}/kn7000-soft-version/)) has no such path,
   verified by reverse engineering. The SP7001 shipped its own system update,
   found and reconstructed in October 2026: program build 942 / table 83
   ("v1.6 PLUG-iN", MAME BIOS `sp7001`), which does carry the plug-in code (see
   the update above).

This page records what the vendor documents say, what our own firmware analysis
says, and — importantly, because it bears on
[dumping an unpreserved firmware]({{ site.baseurl }}/kn7000-rom-from-the-screen/) —
why the two do not conflict.

> Everything here is ordinary preservation reverse engineering of firmware on
> hardware the project owns, to document an interface and to find a
> non-destructive way to archive an **unpreserved** firmware revision before the
> hardware is gone. It is not an attack recipe and targets nobody's system but the
> owner's own instrument.

## What the vendor says

Two pages on the KEY SOFT SERVICE site (© 2002) describe the product:

- **SD-PLUG-iN7000 / SP7001** — a *"PLUG-iN Basis Software"*, called *"das Basis
  Modul für weitere Systemerweiterungen"* (the base module for further system
  extensions). Sold at €249 / CHF 375, **bundled with an "Update V2.0 fürs
  KN7000"**.
- The Q&A page gives the mechanism, in the developers' own words:

  > "we have asked Technics to reserve a PLUG-iN RAM/ROM area for the entire
  > program code."

  The reserved area turned out too small — the page says that after the KN7000
  was finished *"only about one-sixth of the original memory remained"* — so the
  team *"used hardware ROM and SD card,"* and therefore **the PLUG-iN code must be
  present on every SD card** that uses the new file structure. The plug-in
  installs onto each card.

So the design is: **Technics reserved a code region; the plug-in's program code is
carried on the SD card and loaded into that region at run time.** That is the
code-load entry point the project is interested in.

The SP7001 also introduces its own on-card file system (16 songs × 240
directories, 26-character names, TLX lyrics format), separate from the stock
20-songs/99-directories layout — see [Storage & File System]({{ site.baseurl }}/kn7000-storage-subsystem/).

## What our firmware says

Our program image is build **941** (the `GetTtSoftverID` routine at `0x48488AAC`
returns the software-version constant `0x00100000`; the
[SOFT VERSION screen]({{ site.baseurl }}/kn7000-soft-version/) reports
`PROGRAM : 941`). In that image:

- **There are no `PLUG`, `SP700`, `V2.0`, `SD-PLUG` or `KEYSOFT` strings.**
- The exhaustive external-data study already behind
  [Firmware Robustness & ROM Archival]({{ site.baseurl }}/kn7000-firmware-security/)
  found **no execute-from-SD, no overlay, and no SD firmware-update path.** Every
  SD file is matched to a **bounded index** and dispatched to a **fixed** ROM
  handler (the disk-file dispatcher at `0x4852B6B0`); the runtime library at
  `0x4C000000` self-loads from **program flash**, never from the card.
- A fresh, narrower check confirms it from another direction: across the whole
  image there is **exactly one** "load a function pointer from a fixed RAM cell
  and jump through it" site — `0x487F46D8` — and it is the **MILK-kernel task
  context switch** (it saves `SP` into the current task block at `*(0x5038002C)`
  and resumes another task's stack from `0x50380CB8`). It is not a plug-in vector;
  the address it jumps to is a saved task PC, never a byte from the card.

So build 941 **does not** contain the SP7001 reserved-region/SD-load hook. This is
not a contradiction with the vendor: the SP7001 came with its own system update,
program build 942 / table 83, which is *later* than 941 and does contain it.
(Whether that release is the "Update V2.0" named on the product page is not
established.)

## The version picture — and why it matters for dumping

| Firmware                                           | How we know it                                                                                                                                                                                                      | Has the SD PLUG-iN hook?                                                                                                                                                                                               |
|----------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **PROGRAM 893**                                    | the project owner's own instrument (read off its [SOFT VERSION screen]({{ site.baseurl }}/kn7000-soft-version/); partly [recovered by hand]({{ site.baseurl }}/kn7000-build-893-recovery/))                         | almost certainly **no** — it is *earlier* than 941                                                                                                                                                                     |
| **PROGRAM 941**                                    | reconstructed from the public [system-update discs]({{ site.baseurl }}/kn7000-system-update-discs/); one of four program builds now preserved (929, upper half only; 935; 941; 942) and MAME's default BIOS (`v16`) | **no** — verified (above)                                                                                                                                                                                              |
| **PROGRAM 942 / TABLE 83** (SP7001 "v1.6 PLUG-iN") | reconstructed in October 2026 from the PLUG-iN update's `.SLD` payloads; MAME BIOS `sp7001` ([mamedev/mame#16394](https://github.com/mamedev/mame/pull/16394))                                                      | **yes** — program 942's `PlugInProbe` validates the `XAPR` block at `0x483E8000` and calls its header entries; that block's `KssPluginLoad` loads `.XAP` files such as `BASEEXT.XAP` to RAM `0x5029B000` and runs them |

The owner's instrument runs **893**, which is *older* than 941 and than the SP7001
build 942. That is the whole reason its firmware is worth archiving — and it is
also why **SP7001's SD code-load path is not, by itself, a way to dump 893**:

- The hook lives in the SP7001 release (build 942), not in 893. Writing that
  update onto the instrument to gain the hook would **overwrite the 893 firmware
  we are trying to preserve** — the one thing we must not do.
- So for build 893 the realistic non-destructive route is unchanged: the
  [built-in MEMORY DUMP viewer]({{ site.baseurl }}/kn7000-memory-dump-screen/),
  read [out of the screen]({{ site.baseurl }}/kn7000-rom-from-the-screen/), or a
  [hardware clip read of IC16/IC17]({{ site.baseurl }}/kn7000-program-rom-clip-read/).

Where the SP7001 interface *does* help the wider project:

- The reserved region and the SD-load protocol are now **characterised exactly**
  ([SP7001 Firmware]({{ site.baseurl }}/kn7000-sp7001-firmware/)). The resident
  plug-in in table flash (`0x483E8000`–`0x483FB59F`) is validated by its `XAPR`
  header and footer. Its loader `KssPluginLoad` (`0x483EEAA9`) reads an `.XAP` of at
  most `0x1D000` bytes, the first `0x1D000` bytes of the file, to work RAM
  `0x5029B000` and calls offset 0. It checks the plug-in id and compile id the code
  returns only *after* that call. The setup copies `BASEEXT.XAP` to `TECHNICS\DATA`
  on the card.
- That path could therefore run a **dumper plug-in on an SP7001 unit**: an `.XAP`
  linked for `0x5029B000`, in place of `BASEEXT.XAP`, is executed when the resident
  plug-in loads it. That would be a clean way to read the still-undumped wave and rhythm
  ROMs over the SD interface, without opening the case. It has not been
  tried, and whether the loader runs before the plug-in is activated has not been
  traced. (The picture ROM has since been read another way, with no SP7001 at all: a
  [style converter on a floppy]({{ site.baseurl }}/kn7000-rom-dumper/).) (The `0x4C000000` library is not a separate ROM: it self-loads from
  program flash, as noted above.)

## Open questions

Answered since the first version of this page
([details]({{ site.baseurl }}/kn7000-sp7001-firmware/)):

- **Did Technics reserve the region broadly, or only add the loader for the SP7001?**
  Aligning program 942 against 941 shows the host is **new code** in 942: `PlugInProbe` and
  three routines that call the plug-in's header entries, 35 forwarders and accessors, and
  the export table. Build 941 has no dormant hook. The stock table's help text about
  third-party plug-ins does not have code behind it in 941.
- **Where is the reserved region?** In two places. The resident plug-in is in table flash at
  `0x483E8000`–`0x483FB59F`, headed and footed by `XAPR`. Code loaded from the card goes to
  work RAM `0x5029B000`–`0x502B7FFF` (`0x1D000` bytes).
- **On-card format and signature of the plug-in code.** An `.XAP` file is a flat image linked
  for `0x5029B000`, read as exactly `0x1D000` bytes and entered at offset 0. It carries no
  magic of its own. It identifies itself by the plug-in id and the compile id its entry
  returns (`BASEEXT.XAP`: id 3).

- **Does the loader run before activation?** Yes. At startup `Ap_Ce_StartUp` reads a
  "base extension loaded" latch (`0x50299070`); when it is clear it calls `KssPluginLoad(id=3)`
  to read `BASEEXT.XAP` to `0x5029B000` and run it, then sets the latch, and only *afterwards*
  reads the activation status (`0x502992C4`). The password gate is on user-action paths. So the
  base extension loads and runs on a never-activated unit — activation releases features, it does
  not gate the load.
- **What does `BASEEXT.XAP` call?** It reaches the firmware only through the framework object's
  method tables (`obj+0x1C`, `obj+0x2E1C`), not through any fixed address; 567 of its 1,340
  indirect calls resolve there directly. What remains is naming the individual method slots.

Still open:

1. **Is the SP7001 release the "Update V2.0" of the product page?** The update
   found is program build 942 / table 83 ("v1.6 PLUG-iN", PLUG-iN V1.0 of
   2003-08-23). Whether the bundled "Update V2.0" is the same release is not
   established.
2. **Naming the MILK method slots** (`obj+0x1C` `+0x108`/`+0x10C`/`+0x2A4`/…, `obj+0x2E1C`
   `+0x78`/`+0x334`/…) would turn `BASEEXT.XAP`'s indirect calls into named firmware calls.

## Sources

- KEY SOFT SERVICE, *SD-PLUG-iN7000 / SP7001* product page and Q&A (© 2002).
- This project: [SOFT VERSION screen]({{ site.baseurl }}/kn7000-soft-version/),
  [Firmware Robustness & ROM Archival]({{ site.baseurl }}/kn7000-firmware-security/),
  [Firmware Images]({{ site.baseurl }}/kn7000-firmware/),
  [System Update Discs]({{ site.baseurl }}/kn7000-system-update-discs/).
- Disassembly: `GetTtSoftverID` `0x48488AAC`, disk-file dispatcher `0x4852B6B0`,
  `LibRomImageBase` `0x487B8FD1`, task switch `TaskYieldSwitch` `0x487F46D8`
  (see `kn7000/notes/sd-plugin-interface.md` in the `technics-roms-disasm`
  repository). For build 942, table 83 and `BASEEXT.XAP`: `PlugInProbe`
  `0x48585B95`, `KssPluginLoad` `0x483EEAA9`, `XapEntry` `0x5029B000`
  (`notes/sp7001-build-diff.md` in the same repository).
