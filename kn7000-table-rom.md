---
layout: page
title: KN7000 Table ROM — Resource Archive
permalink: /kn7000-table-rom/
---

# Technics SX-KN7000 — table ROM resource archive

The KN7000's 4 MB **table ROM** (mapped at `0x48000000`: the half of the IC16/IC17 flash pair
where A22 is low, the program being the other half, interleaved in 16-bit words with IC17
holding the even words and IC16 the odd) is not code — it is a **directory-based resource
archive**. It opens with a table of little-endian u32 chunk offsets, and each entry points to a tagged resource.

## Chunk kinds

| Address | Tag / content | Meaning |
|--------|---------------|---------|
| `0x48000000` | u32 offset directory | index of all chunks (first chunk at `0x48000200`) |
| `0x48035d08` | **`TCMP`** | the factory rhythm-**style** container (3 built-in styles, " Easy 8 Beat " / "Easy 16 Beat " / " Easy Swing  "), `LibMemCopy`'d to RAM `0x50180000` (`MEM_STYLE_AREA`) at boot — **data, not code**; nothing ever calls into that RAM range |
| `0x48040674` | **`TPAD`** | performance-**pad** index / parameters |
| `0x4804238c` | `Technics Pads` | accompaniment pad pattern data |
| `0x483e828c` | `Technics Rhythms` | style/rhythm resource index |
| (throughout) | **JFIF JPEG** | 119 embedded UI/graphics images |

> **Correction.** An earlier pass here misread the copy of the `TCMP` chunk into RAM
> `0x50180000` as a **code overlay being executed** (the symbol was once named
> `RamCodeOverlayImage`). Both ends of that copy are data: the destination is zeroed by
> `LibMemSet(0x50180000, 0, 0x25800)` beforehand, the source is `TableRomSeg02PtrSize`
> resolving directory entries 2–3, and nothing in the firmware branches into
> `0x50180000`. The routine and symbol are now named `MemStyleAreaLoadFactory` /
> `FactoryMemStyleContainer`. See `kn7000_mame/notes/AUTONOMOUS-STATUS.md` (2026-07-20)
> and `kn7000_mame/notes/table-rom-format.md`.

## The UI graphics are standard JPEGs

Scanning for JPEG streams recovers **119 images, 117 of which decode cleanly with an ordinary JFIF
decoder** — 52 are `160×120` icons/thumbnails and twelve are full-screen `640×240` reference/help
screens. In other words the KN7000 stores its on-screen artwork as ordinary JPEGs and decodes them
in firmware. (A long-standing emulation note that "the boot-splash JPEG decodes to garbage" was
therefore an **emulation bug**, not a bad dump or an exotic format: the source stream is valid
JFIF. The CPU core lacked the `udf07` bit-search instruction that the firmware's JPEG decoder
uses. With it implemented, the splash decodes pixel-clean; see
[User Data & Initial Data Disk]({{ site.baseurl }}/kn7000-initial-data/#the-boot-splash-and-the-green-screen).)

Example full-screen reference screens, extracted verbatim from the ROM:

![KN7000 RHYTHM home screen reference]({{ site.baseurl }}/assets/images/table-rom/rhythm-home.jpg)

![KN7000 ORGAN STYLIST style-list reference]({{ site.baseurl }}/assets/images/table-rom/organ-stylist.jpg)

The ORGAN STYLIST screen above groups its styles under subcategory headings. The two shown,
`Tonewheel Jazz` and `Organ A-Go-Go`, are the first two Organ Stylist entries of the
[built-in Music Stylist catalog]({{ site.baseurl }}/kn7000-rhythm-catalog/) recovered from the
program ROM, in the same order. The style names listed under them (`Swing Tonewheels`,
`Classic B3 Jazz`, …) are not in that catalog, which lists only the headings; they are a separate
list of strings in the program ROM.

A smaller `240×160` panel graphic:

![KN7000 panel graphic]({{ site.baseurl }}/assets/images/table-rom/icon-sample.jpg)

## Reproduce
De-interleave MAME's table build 84 pair, `kn7000_table_even_b84.ic17` / `kn7000_table_odd_b84.ic16`
(`out[0::4]=e[0::2]; out[1::4]=e[1::2]; out[2::4]=o[0::2]; out[3::4]=o[1::2]`) → 4 MB image;
walk the u32 directory at offset 0; extract JPEGs by scanning `ff d8 ff e0` → `ff d9`. See also
the [firmware images]({{ site.baseurl }}/kn7000-firmware/) page for the full per-segment breakdown; technical detail in `kn7000_mame/notes/table-rom-format.md`.
