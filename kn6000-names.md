---
layout: page
title: KN6000 / KN6500 Names & Symbols
permalink: /kn6000-names/
---

# KN6000 / KN6500 — firmware names & symbols

Beyond rhythm and sound data, the KN6000/KN6500 **program images** — the decompressed
`IK2.SLD` / `IKV2.SLD` payloads, which form the upper half of each 4 MB program flash
image (see [hardware]({{ site.baseurl }}/kn6000-hardware/)) — hold extensive
ASCII string tables. (The table ROMs proper, IC13/IC14, have never been dumped.) They
come in two kinds, both extracted here:

| Image               | Total strings       | Internal MILK symbols | User-facing names |
|---------------------|---------------------|-----------------------|-------------------|
| **KN6000** (`IK2`)  | 4,440 in 132 tables | **1,963**             | 2,477             |
| **KN6500** (`IKV2`) | 4,189 in 112 tables | **2,006**             | 2,183             |

The records are **variable-length, NUL-terminated, space-padded** strings packed
back-to-back — *not* the KN7000's fixed 17-byte `style_names.py` records — so they
need a NUL-walk extractor (`name_extract_nul.py` in `kn7000_extraction`).

## Internal MILK symbol names — the symbol-recovery goldmine

The larger share is **internal GUI-resource identifiers** from the
[MILK application framework]({{ site.baseurl }}/technics-shared-codebase/) — the *same class* of
named-resource data whose reflection tables gave the KN7000 its **2,302 function
names**. Examples (KN6000):

- **Screens / menus:** `DiskMenu`, `TT_DKMENU1`…`TT_DKMENU4`, `MspNameScreen`,
  `MspSeqCpScreen`, `TtSeMenu`, `TtSeTone`
- **Functions / handlers:** `LangSetOKFunc`, `LangSetMenuCheck`, `CusMemOKFunc`,
  `HelpMenuCheck`, `DConsoleProc`
- **Widgets / grids:** `SeqToPadCopyGrid`, `SeqToPadFstMeas`, `gridTone1`,
  `Ed1stOnSe`…`Ed4thOnSe`
- **Service / test mode:** `TEST5_Itimatu`, `TEST6_OK`, `TEST6_NO`, `HDD_COMM_TEST`

Because these identifiers recur across the MN10300 models, they are a **Rosetta
stone** for [cross-model symbol recovery]({{ site.baseurl }}/kn6000-roadmap/#the-four-way-code-reuse-strategy-the-force-multiplier): a symbol
named in one ROM names the equivalent object in the others, and aligning them across
KN6000/KN6500/KN7000 propagates names throughout the shared codebase.

## User-facing style names

The **Music-Stylist / accompaniment style** inventories are distinct per model —
the KN6500 ships a visibly newer, larger library:

Offsets (`@0x…`) are into the decompressed `IK2.SLD` / `IKV2.SLD`; add `0x48600000` to
get the CPU address.

**KN6000** (`@0x0a32cc`): Italian Pop · 70's Folk · Folk Rock · Pop Dance · Star
Groove · Cool 16 Beat · Detroit Ballad · Pop Girls · 90's Rock & Roll · 90's Top Ten · Pop Shuffle ·
Beach Party · Mersey Beat · 16Beat Standards · Piano Superstar · Fifties Smooch ·
Rock Balladeer · Rhythm & Blues …

**KN6500** (`@0x0a7d50`): Sci-fi Adventure · Spy Movie · Cartoon Ballad · ProductionNumber · New
Choreography · Tap Dance Legend · Legendary Ballad · Movie Melodrama · Swing
Production · Breakfast Waltz · Ballroom Waltz · Slow Latin Dance · 60's Foxtrot ·
Ribbon Foxtrot · Swinging Bert · Show Overture …

The built-in **rhythm genres** live in a separate 72-byte-record table (`@0x0580f8`
in KN6000: *8 Beat, 16 Beat, Dance Pop, Jazz Fusion, March/Polka, Swing …*, each
followed by 10×u16 params and 9× `0x4C25xxxx` pattern pointers), and reverb/effect
name tables (`Room1/Room2/Plate1/Plate2/Concert1 …`) sit near `@0x065aec`.

## Method

`kn7000_extraction/name_extract_nul.py <image.bin> <out.txt>` — walks NUL-terminated
strings, clusters adjacent ones into tables, filters binary noise, and classifies
each table as `symbols` or user-facing `names`. Run on `IK2.SLD.bin` (KN6000) and
`IKV2.SLD.bin` (KN6500).
