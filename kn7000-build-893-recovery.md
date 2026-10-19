---
layout: page
title: "Recovering build 893 — a photographic transcription, not a dump"
permalink: /kn7000-build-893-recovery/
---

# Recovering build 893 — a photographic transcription, not a dump

The project owner's SX-KN7000 runs **PROGRAM 893 / TABLE 80**. The images this
work was compared against are **PROGRAM 941 / TABLE 84**; the project has since
also obtained builds 942/83 (SP7001), 935 (v1.5) and the upper half of 929
(v1.4), all later than 893. Neither of his is preserved
anywhere — see [the SOFT VERSION screen]({{ site.baseurl }}/kn7000-soft-version/)
for how that was discovered and why it matters.

This page is about what has been done since: **9,472 bytes of build 893 read off
the instrument's own screen and typed in by hand**, and what those bytes say
about the relationship between the two builds.

> **Update, 2026-10-19: build 893 and table 80 have since been read whole from the instrument's
> own chips**, with the [ROM dumper]({{ site.baseurl }}/kn7000-rom-dumper/), and kept in the
> project's private ROM collection. This page predates that read. The transcription below has
> not yet been checked against it; doing so would grade both the transcription and the method.

> ## ⚠ Read this before anything else on the page
>
> **This is a transcription of photographs. It is not a dump.**
>
> A person photographed the KN7000's built-in
> [MEMORY DUMP viewer]({{ site.baseurl }}/kn7000-memory-dump-screen/) 60 times,
> and readers transcribed the hex digits from those photographs. Thirty-seven of
> the sixty are done. There is no chip read, no bus capture, no checksum, and no
> independent second reading of any screen.
>
> **No reconstructed build-893 image has been produced**, and none should be
> produced without being labelled *derived, not a dump*. Nothing on this page may
> be loaded into an emulator, published as a ROM, or hashed as if it were one.

## 1. How the instrument names its own build

Two of the four numbers on the SOFT VERSION screen are checkable against bytes
we hold, and they are what make a stranger's LCD reading actionable:

| Field | Where the number physically is | Value in our images |
|---|---|---|
| `PROGRAM` | a **compiled-in constant**: `u16` little-endian at program-flash file offset `0x33660C` (CPU `0x4873660C`) | `0x03AD` = **941** |
| `TABLE` | an **ASCII decimal string** in the table image: follow the `u32` at table offset `0x1C` (directory segment 7) → `0x139EE8`, and parse the digits there | the four bytes `"84\n\0"` = **84** |

Both were re-read from `kn7000_program.rom` (0x3F6F01 bytes) and
`kn7000_table.rom` (0x3E94D4 bytes) while writing this page, and both are
identical in the byte-interleaved even/odd pairs MAME actually loads.

The consequence is sharp. `PROGRAM` is an immediate value in flash, so a machine
printing `893` is running **different program-flash bytes** — no setting, no
battery-backed cell, no service procedure can make our image print anything else.
`TABLE` is read out of the table image at run time, so a machine printing `80` is
reading **different table-flash bytes**. His instrument differs from our reference
on *both* devices, in the same direction.

## 2. What was transcribed

`kn7000_disassembly/dumps/build893-photo-transcription/` holds
`screens.json` (one record per photograph, with the source filename, the base
address, and per-screen notes about glare and contested cells) and
`screens.hex` (the same content, address-ordered and human-auditable).

| | |
|---|---|
| Photographs taken | **60** |
| Photographs transcribed | **37** |
| Bytes | **9,472** (37 × 256) |
| Cells marked unknown (`??`) | **17** |
| Independent re-readings | **none** |

Two transcription runs were cut short — one by a usage limit, one interrupted
deliberately — and 37 screens are what completed. The remaining 23 photographs
already exist; they have simply not been read yet.

**Coverage.** Ten screens in the table half and twenty-seven in the program half:

| Half | Base addresses |
|---|---|
| Table (`0x48000000`+) | `48000000`, `48009000`, `48019000`, `48029000`, `48039000`, `48049000`, `48059000`, `48159000`, `48259000`, `48359000` |
| Program (`0x48400000`+) | `48400000`–`48400600` (7 consecutive pages), `48400A00`–`48400D00` (4), `48459000`, `48789000`, `487B9000`, `487C9000`, `487DA000`, `487E9000`–`487ED000` (5), `487F4400`–`487F4900` (6) |

That is 0.11 % of the 8 MB the two halves occupy. The point of these particular
screens is not coverage; it is **calibration** — they are placed where they
constrain the relationship between the two builds.

### Method, and the rules the readers worked under

- **Never guess.** Any cell destroyed by glare or blur is `??`. No inference from
  surrounding context, and explicitly no inference from our build-941 image.
- **All 16 hex columns are present** in these photographs; only the ASCII column
  at the right edge is cut off. So ASCII was **not** available as a cross-check —
  the one free redundancy the screen offers was lost to framing.
- **The colour legend was used.** The viewer highlights cells matching four
  legend bytes (Aqua = `F0`, Yellow = `F7`, Lime = `FF`, Fuchsia = `XX`), which
  encodes those values a second time and settled marginal cells.
- The shots are slightly off-axis, so text rows slope — a row sits 15–20 px
  higher at the right edge than at the left. Measured once and reused.

> **The trap that was hit and survived.** At `0x48400DF0` byte 13, the
> surrounding `EC 01 / 02 / 04 / 10 / 20` progression made `40` look obvious. The
> pixels said `80`. The pixels were right. Any rule that lets a reader "fix" a
> byte toward a pattern — or toward our other ROM — manufactures agreement and
> destroys exactly the build differences being preserved.

## 3. The drift profile — four steps, not one block

Each transcribed screen was correlated against the archived build-941 program
image at every byte shift in ±0x8000. Every screen lands on one clear offset, and
the offsets are **not all the same**.

| Covered address | Drift of 941 relative to 893 | Agreement |
|---|---|---|
| `0x48400000` – `0x48400D00` | **0** | 93.0 – 99.2 % |
| `0x48459000` | **+201** (`0x00C9`) | 96.1 % |
| `0x48789000` | **+6428** (`0x191C`) | **100.0 %** |
| `0x487B9000` – `0x487DA000` | **+6453** (`0x1935`) | 94.1 – 97.7 % |
| `0x487E9000` – `0x487F4900` | **+6451** (`0x1933`) | 91.0 – 100.0 % |

So build 941 is build 893 with **several separate insertions totalling 6,451
bytes** — an ordinary recompilation with code added in more than one place, not
a single patch block.

> **This supersedes an earlier reading.** With only the first 12 screens the
> profile looked like one 6,451-byte insertion. Twelve screens simply did not
> sample the middle of the image. The single-shift model is withdrawn; the
> correlation evidence and the verification argument it rested on still hold.

The final step is **−2 bytes**, which is either a genuine small deletion or a
near-tie in the correlation over a data region. It is the least trustworthy row
in the table and is labelled as such.

**A cross-check from the top of the flash.** On the 893 machine the owner read
`0x487F55CF`–`0x487FFFFF` as one unbroken block of `0xFF`; in our 941 image the
last non-`0xFF` byte is at `0x487F6F00` (value `0x4C`). The gap between those two
end-of-code marks is `0x1931` by subtraction, or `0x1932` bytes counted
inclusively — within a byte or two of the `0x1933` the correlation finds
independently in that region. The point is the order of magnitude and the sign,
not the last digit: an entirely independent observation lands on the same ~6.4 KB.

**The release byte.** The transcribed row `0x48400000` reads
`CC EE 79 CB CB CB CB CB DC BA 75 0D 00 FF FF 13`. Its last byte, CPU `0x4840000F`,
is the release number the firmware carries in hexadecimal digits (`0x15` in v1.5
build 935, `0x16` in v1.6 build 941; see
[the release number]({{ site.baseurl }}/kn7000-soft-version/#the-release-number-one-byte-at-0x4840000f)).
The owner re-read that byte directly on his instrument on 2026-10-18 and got `0x13`
again, so build 893 is **v1.3**. The row's layout also matches build 935's first row
(`CC EE 79 CB CB CB CB CB DC 85 77 0D 00 FF FF 15`, a 3-byte reset jump) rather than
941's (`DC 7E FF 00 00 CB CB CB CB CB DC C5 77 0D 00 16`, a 5-byte one).

### The table half

Shift 0 and 96.1 – 100 % agreement from `0x48000000` up to `0x48159000`, then
**+3** at both `0x48259000` and `0x48359000`. Table build 84 therefore carries a
**three-byte insertion** somewhere in `0x48159100` – `0x48259000`.

> ⚠ **One anomaly, unresolved.** The screen at `0x48029000` correlates best at
> **−1088** with 100 % agreement. A negative drift there contradicts every
> neighbour. The likeliest explanation is a spurious high-correlation match
> inside a repetitive record table, but it has **not** been re-checked against
> the photograph and should not be trusted until it is.

## 4. Why 91–99 % is evidence *for* the model, not against it

An obvious objection: if the two builds are the same code displaced, why isn't
agreement 100 % everywhere?

Because **absolute pointers must change when code moves.** Any 32-bit constant
above an insertion point has to be rewritten by that region's drift amount, so
those bytes *should* differ between the builds. The residuals track pointer
density exactly:

- the low-address program screens `0x48400000`–`0x48400600` — the vector table
  and early boot, where nearly every word is an address — score **93 – 97 %**;
- a pure-code page like `0x48789000` scores **exactly 100.0 %**.

A transcription error, by contrast, would be scattered uniformly and would not
prefer the pages full of pointers. Six-to-thirty screens agreeing at 91–100 %
under a *single* shift each also cannot arise from chance: the earlier apparent
"2 % agreement" of the program screens was an artefact of comparing at the wrong
offset, not a reading problem. **The readers were accurate.**

That said, this is the *only* verification these screens have received. A planned
independent structural verifier never ran, and no screen has been transcribed
twice by different readers.

## 5. What to photograph next

Each of these bisects a bracket in which an insertion is known to lie. Roughly
**twelve well-placed shots** can pin an insertion point that brute force would
need ~16,000 photographs to find.

| # | Dial this address | Bracket it bisects | Why |
|---|---|---|---|
| 1 | **`485F1000`** | `0x48459100` – `0x48789000`, 3.19 MB | holds **+6,227 of the 6,451** drift bytes — 97 % of the total change |
| 2 | **`4842CF00`** | `0x48400E00` – `0x48459000`, 0.34 MB | the +201 step |
| 3 | **`481D9000`** | `0x48159100` – `0x48259000` (table) | the table half's 3-byte insertion |
| 4 | `487A1000` | `0x48789100` – `0x487B9000`, 0.19 MB | the +25 step |
| 5 | `48029000` | — | **re-check**: correlates at −1088 with 100 %, contradicting every neighbour |

Before requesting new photography, the **23 untranscribed photographs already in
hand** should be read — they may collapse some brackets for free.

The correlation has so far been run only against build 941. Builds 935 (v1.5,
complete) and 929 (v1.4, upper half) are closer to 893 in build number and are
now held; correlating the 37 screens against them costs nothing and may shrink
the drift.

## 6. What this does and does not buy

**Does:** it proves build 893 exists in a specific, describable relationship to
build 941; it gives a free cross-version calibration of the work-RAM layout
(the viewer's four default address slots are digit-for-digit identical on his
machine — see
[what real hardware has already confirmed]({{ site.baseurl }}/kn7000-memory-dump-screen/#what-real-hardware-has-already-confirmed));
and it turns "photograph 4 MB" into "photograph a dozen carefully chosen pages".

**Does not:** it does not preserve build 893. Reconstructing 893 from 941 remains
*conceivable* but is much harder than a single shift — every breakpoint must be
located, and each region's absolute pointers relocated by that region's own
drift. Any artifact produced that way would be **derived, not a dump**, and must
carry that label into every file, hash and catalogue entry it ever appears in.

The two routes that would actually preserve it are the
[in-circuit clip read of IC16/IC17]({{ site.baseurl }}/kn7000-program-rom-clip-read/)
and
[reading the ROM back out of the screen with a video grabber]({{ site.baseurl }}/kn7000-rom-from-the-screen/).
The second is why photography was paused: at 256 bytes per screenful a person
cannot photograph 4 MB, but a capture card holding down one button can.

## Provenance of the numbers on this page

| Claim                                          | How it was checked                                                                                                                                                     |
|------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `PROGRAM` = 941 at file `0x33660C`             | re-read from `kn7000_program.rom` while writing this page: `u16` LE = `0x03AD` = 941                                                                                   |
| `TABLE` = 84 via table offset `0x1C`           | re-read: `dir[7]` = `0x139EE8`, bytes there are `"84\n\0"`                                                                                                             |
| `PROGRAM : 893` / `TABLE : 80`                 | **owner testimony, 2026-08-08**, read off the LCD of a real SX-KN7000                                                                                                  |
| 37 screens / 9,472 bytes / 17 unknown cells    | counted from `screens.json` (37 records × 256 cells; 17 cells equal to `??`)                                                                                           |
| The transcribed address list                   | the `base_address` field of all 37 records                                                                                                                             |
| The four-step drift profile                    | `DRIFT-ANALYSIS.md` in the transcription directory — correlation of each screen against build 941 at every shift in ±0x8000                                            |
| `0x487F55CF`–`0x487FFFFF` is all `0xFF` on 893 | owner hardware read, 2026-08-09, via the instrument's own MEMORY DUMP screen                                                                                           |
| `0x4840000F` = `0x13` (v1.3) on 893            | owner hardware read, 2026-10-18, via the MEMORY DUMP screen; the same value as the transcribed row `0x48400000`                                                        |
| Build 935's first row                          | `JK1.SLD` of the kn7-15 update set, decompressed with the disassembly's `tools/sld_decompress.py`                                                                      |
| Our last non-`0xFF` byte is `0x487F6F00`       | `kn7000_program.rom` is `0x3F6F01` bytes, so its final byte sits at CPU `0x487F6F00`; scanned the image and confirmed that byte (`0x4C`) is the highest non-`0xFF` one |
| Nothing here is a dump                         | stated in the transcription directory's own `README.md`; no reconstructed image exists in any repository                                                               |

## Related pages

- [SOFT VERSION screen]({{ site.baseurl }}/kn7000-soft-version/) — how 893/80 was found, and what all four version rows mean
- [MEMORY DUMP screen]({{ site.baseurl }}/kn7000-memory-dump-screen/) — the hidden hex viewer the photographs are of, and the chord that opens it
- [Reading ROM out of the screen]({{ site.baseurl }}/kn7000-rom-from-the-screen/) — the video-grabber route that replaces hand photography
- [Program-ROM clip read (IC16/IC17)]({{ site.baseurl }}/kn7000-program-rom-clip-read/) — the hardware route to a real dump
- [Firmware Robustness & ROM Archival]({{ site.baseurl }}/kn7000-firmware-security/) — why the instrument will not hand over its own bytes
- [Firmware Images]({{ site.baseurl }}/kn7000-firmware/) — the 941/84 images and their layout
- [Cross-Version Diff Guidebook]({{ site.baseurl }}/cross-version-diff-guidebook/) — the KN5000 method this work is trying to make possible for the KN7000
