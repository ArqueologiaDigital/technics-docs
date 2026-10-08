---
layout: page
title: "SD PLUG-iN (SP7001) — a code-load interface, in a firmware we don't have"
permalink: /kn7000-sd-plugin/
---

# The SD PLUG-iN (SP7001), and the reserved plug-in region

> ### Update, 2026-10-08 — the PLUG-iN firmware has now been found
>
> The SP7001 program ("v1.6 PLUG-iN") and table updates were located and
> reconstructed from their update `.SLD` payloads. The customized **program**
> image (CRC `7bc3e247`; flash halves ic17 `4c91678f` / ic16 `7a7990ec`) **does**
> contain the `PLUG`/`SP700` strings that build 941 lacks, and the update also
> ships **`BASEEXT.XAP`** — 0x1d000 bytes of MN10300 code (it begins `cf 30` =
> `movm`), the plug-in program the firmware copies from the SD card into the
> reserved region. So the reserved-region / SD-load path is no longer
> hypothetical; it can now be reverse-engineered directly. ⚠ Provenance caveat:
> the SP7001 program's shipped `SMCK` checksum does **not** verify the
> reconstructed image (the shipped `.INF` predates the final `.SLD` rebuild);
> the table verifies except its top two 256 KB blocks (the plug-in customization).
> Hashes and the reproducer: `research-scratch/kn7000-sp7001/`.
>
> It is now a **MAME BIOS option** too: `kn7000 -bios sp7001` runs the SP7001
> program/table, selectable independently of the custom-data set. See the
> firmware PR (`technics-kn7000-firmware-bios`). The reserved region and the
> SD-load protocol can be reverse-engineered from this image and `BASEEXT.XAP`.


A commercial add-on sold for the KN7000 around 2002 — **KEY SOFT SERVICE's
"SD PLUG-iN", product code SP7001** — extended the keyboard's software through the
SD card. That is interesting for two reasons this project cares about:

1. It is direct, third-party evidence that the KN7000 OS has a **reserved region
   for plug-in code that is loaded from the SD card**. A legitimate SD *code-load*
   entry point therefore exists — somewhere.
2. It is **not in the firmware we have.** Our dump ([program build 941]({{ site.baseurl }}/kn7000-soft-version/))
   has no such path, verified by reverse engineering. The SP7001 shipped with a
   Technics **"Update V2.0"**, a later firmware this project has never seen.

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
not a contradiction with the vendor: **SP7001 required Update V2.0**, and V2.0 is
a *later* firmware than 941.

## The version picture — and why it matters for dumping

| Firmware | How we know it | Has the SD PLUG-iN hook? |
|---|---|---|
| **PROGRAM 893** | the project owner's own instrument (read off its [SOFT VERSION screen]({{ site.baseurl }}/kn7000-soft-version/); partly [recovered by hand]({{ site.baseurl }}/kn7000-build-893-recovery/)) | almost certainly **no** — it is *earlier* than 941 |
| **PROGRAM 941** | reconstructed from the public [system-update discs]({{ site.baseurl }}/kn7000-system-update-discs/); the only image we execute | **no** — verified (above) |
| **"Update V2.0"** (SP7001) | KEY SOFT SERVICE product pages only; **never dumped** | **yes** — by the vendor's own description |

The owner's instrument runs **893**, which is *older* than our 941 and older still
than V2.0. That is the whole reason its firmware is worth archiving — and it is
also why **SP7001's SD code-load path is not, by itself, a way to dump 893**:

- The hook lives in V2.0, not in 893. Writing V2.0 onto the instrument to gain the
  hook would **overwrite the 893 firmware we are trying to preserve** — the one
  thing we must not do.
- So for build 893 the realistic non-destructive route is unchanged: the
  [built-in MEMORY DUMP viewer]({{ site.baseurl }}/kn7000-memory-dump-screen/),
  read [out of the screen]({{ site.baseurl }}/kn7000-rom-from-the-screen/), or a
  [hardware clip read of IC16/IC17]({{ site.baseurl }}/kn7000-program-rom-clip-read/).

Where the SP7001 interface *does* help the wider project:

- If a **V2.0 image is ever obtained** (another preservation target — the update
  exists on SP7001 start/boot cards), it would let us **characterise the reserved
  region and the SD-load protocol exactly**: the reserved address range, the
  on-card format of the loaded code, the signature the firmware checks, and the
  routine that copies card bytes into the region and transfers control.
- That documented path could then run a **dumper plug-in on a V2.0 unit** — a
  clean way to read the still-undumped
  [`0x4C000000` library/kernel ROM]({{ site.baseurl }}/kn7000-firmware/) and the
  wave ROMs over the SD interface, without opening the case.

## Open questions

1. **What build number is "Update V2.0"?** The KEY SOFT SERVICE name does not map
   to a Technics `PROGRAM :` number yet. It is later than 941; by how much is
   unknown.
2. **Did Technics reserve the region broadly (dormant in 941/893), or only add the
   loader in V2.0?** The 941 image shows no dormant signature-probe-and-jump, which
   argues for "added in V2.0." A V2.0 dump would settle it.
3. **Where is the reserved region?** Unknown until a V2.0 image exists. The vendor
   says it is small (the leftover of "one-sixth of the original memory").
4. **On-card format of the plug-in code and its signature** — unknown; this is what
   a V2.0 dump would reveal.

## Sources

- KEY SOFT SERVICE, *SD-PLUG-iN7000 / SP7001* product page and Q&A (© 2002).
- This project: [SOFT VERSION screen]({{ site.baseurl }}/kn7000-soft-version/),
  [Firmware Robustness & ROM Archival]({{ site.baseurl }}/kn7000-firmware-security/),
  [Firmware Images]({{ site.baseurl }}/kn7000-firmware/),
  [System Update Discs]({{ site.baseurl }}/kn7000-system-update-discs/).
- Disassembly: `GetTtSoftverID` `0x48488AAC`, disk-file dispatcher `0x4852B6B0`,
  `LibRomImageBase` `0x487B8FD1`, task context switch `0x487F46D8`
  (see the [disassembly repository](https://github.com/)'s `kn7000_disassembly`,
  `notes/sd-plugin-interface.md`).
