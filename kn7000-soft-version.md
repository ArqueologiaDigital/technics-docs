---
layout: page
title: "SOFT VERSION Screen — and an unpreserved KN7000 firmware"
permalink: /kn7000-soft-version/
---

# The SOFT VERSION screen — and an unpreserved KN7000 firmware

The KN7000 can tell you which firmware it is running. There is a hidden
**SOFT VERSION** screen — no jig, no jumper, no disk, no power-on combination —
that prints four decimal build numbers on the LCD. It costs nothing to open, it
changes nothing, and it is the one preservation measurement that every KN7000
owner in the world can perform today.

It has already paid off. In August 2026 the project owner opened it on his own
instrument and read numbers that **do not match any of the firmware images
this project holds**.

> ### The finding
>
> **On 2026-08-08 the project owner powered up his real SX-KN7000 and the
> SOFT VERSION screen reported `PROGRAM : 893` and `TABLE : 80`.**
>
> The images reconstructed from the public system-update disks report
> **`PROGRAM : 941`** and **`TABLE : 84`**. His instrument therefore runs an
> **earlier program revision *and* an earlier table revision**, and *neither of
> them is preserved anywhere* — not in this project, not on the update disks,
> not in any dump we are aware of. Until October 2026 every emulator run this
> project made executed program 941. Program 893 has never been executed by anything
> except the machines that shipped with it.
>
> Recorded as owner testimony, read off the instrument's own LCD. No photograph
> of the screen is in the repository yet, and the numbers have not been
> independently re-read.
>
> **Since then, 9,472 bytes of build 893 have been read back off that
> instrument** — by photographing its
> [built-in MEMORY DUMP viewer]({{ site.baseurl }}/kn7000-memory-dump-screen/) and
> transcribing the hex by hand. Those bytes place 941 and 893 in a specific
> relationship (several insertions totalling 6,451 bytes) and corroborate the
> version reading from an entirely different direction. It is a **transcription,
> not a dump**: see
> [Recovering build 893]({{ site.baseurl }}/kn7000-build-893-recovery/).

## Reaching the screen

The screen is a **runtime chord** on a normally booted machine — the same class
of hidden factory screen as the KN5000's
[MEMORY DUMP viewer]({{ site.baseurl }}/memory-dump-screen/).

> With the instrument on and at a normal play screen, **press and hold, all at
> the same time, the UP and the DOWN button of part-mixer columns 1, 6 and 8**
> (six caps). The SOFT VERSION screen appears and goes away again by itself
> after a few seconds.

The buttons in question are the tall pairs of the **part mixer** — the row of
column pairs under the display, which on the KN7000 has **sixteen** columns
(`MUTE UP n` / `MUTE DOWN n`, labelled *PART n ON* / *PART n OFF*; see the
[Control Panel Protocol]({{ site.baseurl }}/kn7000-control-panel/)). Count columns
from the left; you want the UP **and** the DOWN cap of columns **1**, **6** and
**8** held together. Rolling the six caps on one at a time is easier than
slamming them down together, and it may take two hands.

**This chord is confirmed on real KN7000 hardware** by the project owner — it is
not an emulator inference. It is a *runtime* chord and is unrelated to the
instrument's documented **power-on** service diagnostics (for example §8.1's ROM
device test, entered by holding C#3 + D#3 + C#4 while switching on); it is not
among the service-mode entries catalogued on this site.

## What the four numbers are

The screen is drawn under the header `--- SOFTWARE VERSION ---` and each row is
produced by its own window procedure formatting a `%4d`:

| Row             | Format string            | Where the number comes from                                                                                                                                                     | Do we hold that device?                                                                                                                                                                                                                                               |
|-----------------|--------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `PROGRAM : %4d` | program flash `0x1D67E0` | a **constant compiled into the program flash**: the `u16` at CPU `0x4873660C` (file offset `0x33660C`)                                                                          | ✅ yes — four builds: **941** (v1.6), **942** (SP7001), **935** (v1.5) and the upper half of **929** (v1.4); the stamp moves between builds                                                                                                                           |
| `TABLE   : %4d` | `0x1D67F0`               | an **ASCII decimal string read out of the table flash** at boot: the firmware follows the u32 at `0x4800001C` (segment 7 of the table directory) and parses the digits it finds | ✅ yes — two builds: `"84\n"` and `"83\n"` (SP7001). Segments 68–70 carry three more 4-byte markers, `"84\n"` in build 84 but `"80\n"` in the SP7001 table; only segment 7 is shown ([details]({{ site.baseurl }}/kn7000-sp7001-firmware/#table-83-against-table-84)) |
| `RHYTHM  : %4d` | `0x1D6800`               | an ASCII decimal parsed out of the **rhythm ROM** (IC18, or the IC20 flash on earlier units), `0x14` bytes below the top of a 4 MB region                                       | ❌ **undumped**                                                                                                                                                                                                                                                       |
| `PICTURE : %4d` | `0x1D6810`               | an ASCII decimal parsed out of the **picture ROM** (IC19) at `0x57800000`, via the u32 pointer stored at its base                                                               | ❌ **undumped**                                                                                                                                                                                                                                                       |

Two consequences follow directly from that table, and they are the reason the
owner's reading matters so much:

* **PROGRAM is baked into the program image.** It is not a setting, not
  battery-backed, not written by a service procedure — it is an immediate value
  in flash. A machine that prints `893` is running *different program-flash
  bytes*. There is no configuration that makes our image print 893.
* **TABLE is read from the table image at runtime.** A machine that prints `80`
  is reading *different table-flash bytes*. In our table image the value lives
  in a four-byte directory segment holding the literal ASCII `"84\n"`; an
  earlier build would hold `"80\n"` in the same slot.

So the owner's instrument differs from our reference images on **both** flash
devices, consistently in the same direction (both numbers lower). That
self-consistency is a mild corroboration that the reading is a genuine earlier
release pair rather than a misread.

The **RHYTHM** and **PICTURE** rows cannot be reproduced in emulation at all:
those two devices have never been dumped. (Upstream MAME's KN7000 driver
declares both devices `NO_DUMP` and maps nothing at `0x57800000`; the development
driver in the kn7000_mame overlay also substitutes a clearly-labelled synthetic
`BAD_DUMP` stand-in for the rhythm resource.) Anything those rows show in the emulator is
an artefact, not a firmware fact.

## The firmware evidence

Both numbers are latched into work RAM once, early in boot, by a single stretch
of code at CPU `0x48414369`. It reads the PROGRAM stamp straight out of flash
and then walks the table directory and converts the ASCII digits by hand:

```
48414369: fc a4 0c 66 73 48   mov     (0x4873660c), d0   ; the PROGRAM build stamp in flash
4841436f: 0c                  clr     d3
48414370: fc 83 c4 7d 00 50   movhu   d0, (0x50007dc4)   ; keep the low 16 bits -> "PROGRAM : %4d"
48414376: fc a6 1c 00 00 48   mov     (0x4800001c), d2   ; table directory entry 7
4841437c: fc c2 00 00 00 48   add     0x48000000, d2     ; -> CPU address of the version string
48414382: f1 e8               mov     d2, a0
                              ...                        ; d3 = d3*10 + (*a0++ - '0'), until '\n' or NUL
484143ab: fc 8f c8 7d 00 50   movhu   d3, (0x50007dc8)   ; -> "TABLE   : %4d"
```

The two cells are then formatted by the version-box window procedures the
disassembly names `AcProgVerBoxProc` (CPU `0x48488897`) and `AcTableVerBoxProc`
(CPU `0x484888FB`), each of which loads its RAM cell and calls the
`printf`-family formatter at `0x4C001A48`:

```
484888d0: fc cc e0 67 5d 48   mov     0x485d67e0, d0     ; "PROGRAM : %4d"
484888da: fc ac c4 7d 00 50   movhu   (0x50007dc4), d0
484888e3: dd 65 91 b7 03 20 20 call   0x4c001a48         ; formatter (library code, copied from program flash at boot)
```

```
48488934: fc cc f0 67 5d 48   mov     0x485d67f0, d0     ; "TABLE   : %4d"
4848893e: fc ac c8 7d 00 50   movhu   (0x50007dc8), d0
48488947: dd 01 91 b7 03 20 20 call   0x4c001a48
```

The pairing of field to source is not an inference from proximity: a full scan
of the 4 MB program image finds **exactly one** 32-bit reference to each of the
two RAM cells as a store and exactly one as a load —
`0x50007DC4` is written only at `0x48414372` and read only inside
`AcProgVerBoxProc`; `0x50007DC8` is written only at `0x484143AD` and read only
inside `AcTableVerBoxProc`. There is no second writer that could substitute a
different value.

The same shape repeats for the other two rows: `AcRhythmVerBoxProc`
(`0x4848895F`) parses ASCII digits from an address computed as
*helper(`0x4843D6DC`) − `0x10000` + `0x3FFFEC`* — i.e. `0x14` bytes below the
top of a 4 MB region — and `AcAromVerBoxProc` (`0x48488A0B`) dereferences the
u32 at `0x57800000`, adds the picture-ROM base back, and parses digits there.
The screen's own title-ID accessor is `GetTtSoftverID` (`0x48488AAC`), a
three-instruction function that returns the constant `0x00100000`; the
firmware's developer symbol tables carry the matching tags `TtSoftver`,
`_TT_SOFTVER` and the window class `IvMpVerWinProc`.

> **Update — the chord decoder has since been traced.** When this page was first
> written, the panel-chord decoder that turns six held caps into a title ID had
> not been located, and the paragraph here said so. It has now been found and
> disassembled: the balance-button handler accumulates a both-held column mask and
> the dispatcher compares it for equality against exactly three constants.
> Columns 1 + 6 + 8 give **`0xA1`** — the SOFT VERSION case, the same constant as
> on the KN5000. The other two cases are `0x99` (columns 1, 4, 5, 8 → the
> [MEMORY DUMP viewer]({{ site.baseurl }}/kn7000-memory-dump-screen/)) and
> `0x110000` (an LCD-capture chord whose physical caps are still unidentified). A
> byte scan for the accumulator's address finds no second comparison site
> anywhere in the 4 MB image, so those three are the only chords this handler
> implements.

## Why program 893 matters

It is a **different firmware from any that an emulator run has ever
executed.** Not a different setting or a different data disk — different code.
Everything this project has concluded about KN7000 behaviour by running or
disassembling `kn7000_program.rom` is a statement about build 941. Build 893
may differ in bug fixes, in sound or style tables, in panel handling, in the
boot sequence; nobody can say, because nobody has the bytes.

Preservation-wise the problem is not a lack of versions to diff. Every program
image this project holds — builds 929 (upper half), 935, 941 and 942 — was
*reconstructed from update floppies*
([system update discs]({{ site.baseurl }}/kn7000-system-update-discs/)). The revision that
was **factory-installed** in at least one surviving instrument is older than
anything the updates carry, and update packages by their nature overwrite it.
Every time a KN7000 owner applies the kn7-16 program update, one more copy of
whatever earlier build that machine carried is destroyed. Build 893 is not
"rare"; on current evidence it is *unarchived*.

The
[cross-version diff work]({{ site.baseurl }}/cross-version-diff-guidebook/) done for
the KN5000 — where holding v7, v9 and v10 made it possible to tell deliberate
change from coincidence — is now possible for the KN7000 between builds 935, 941
and 942 (and the upper half of 929), though it has not been done yet; for build
893 it still needs that build's bytes.

### What it would take

Nothing in the firmware will hand over its own bytes. As the
[ROM archival analysis]({{ site.baseurl }}/kn7000-firmware-security/) establishes, the
KN7000 has no diagnostic that emits program-flash contents to MIDI, serial or
disk, and the update path is write-only. Capturing build 893 therefore means
reading the chips: the
[in-circuit clip read of IC16/IC17]({{ site.baseurl }}/kn7000-program-rom-clip-read/)
is the least invasive route currently mapped, and the table flash would have to
be read the same way to capture table 80. (Both halves live on the *same* 8 MB
flash pair, so one clip session can capture both.)

There is one route that needs no clip at all, because the instrument's hidden hex
viewer paints any address it can reach and the rear composite VIDEO OUT carries
whatever it paints:
[reading the ROM back out of the screen]({{ site.baseurl }}/kn7000-rom-from-the-screen/).
It reaches 99.87 % byte accuracy on emulator frames and currently **refuses every
real composite frame** it has been given, which is the correct failure — it
declines rather than inventing bytes.

## Check your own instrument

If you own a KN7000, this is a five-minute contribution with no risk to the
machine:

1. Power the instrument on normally and let it reach a play screen.
2. Hold the UP **and** DOWN caps of part-mixer columns **1**, **6** and **8**
   together until the SOFT VERSION screen appears.
3. **Photograph it**, all four rows.
4. Report the numbers. Anything other than `PROGRAM : 935`, `941` or `942` is a
   firmware revision the world does not have in full (of build 929 only the upper
   half survives) — and knowing *which* machines carry which builds is itself
   new information, since no serial-number-to-revision mapping exists.

Even a reading that matches 941 is useful: it tells us how widely the public
update was applied.

## Relationship to the KN5000's hidden screens

The KN5000 has the same class of hidden runtime chord, documented at
[The built-in MEMORY DUMP screen]({{ site.baseurl }}/memory-dump-screen/): six held
caps on the part-volume row open a factory *Panel Simulator*, from which a
16-row hex viewer can read any address in the CPU's space. On that machine the
SOFT VERSION screen is the harmless **calibration step** for the same chord
mechanism (columns 1, 6, 8 → SOFT VERSION; columns 1, 5, 8 → Panel Simulator).

The obvious question is whether the KN7000 has the same escalation. When this
page was first written it was open; **it has since been answered — yes.** The
KN7000's hex viewer opens on a normally booted machine by holding the UP *and*
DOWN caps of mixer columns **1, 4, 5 and 8** together (the dispatcher tests the
held-switch accumulator for exactly `0x99`; one extra column kills it), and it is
fully documented at
[MEMORY DUMP Screen]({{ site.baseurl }}/kn7000-memory-dump-screen/). The two
observations that framed the question at the time still stand and are worth
keeping, because they are what made the search worth doing:

* **The debug widgets exist in the KN7000 firmware.** The program image carries
  a `DbMemoryDumpProc` at CPU `0x484878AC`, alongside `DbMemoProc`,
  `DbColorListProc`, `DbBitmapLoadProc` and `DbVariableMenuProc`, plus the
  developer tag strings `TtMemoryDump`, `TtDebug`, `OTB_DEBUG`, `TT_MEMDUMP`
  and `TT_DEBUG` — the same naming conventions as the KN5000's factory screens
  (see the [Shared Codebase Map]({{ site.baseurl }}/technics-shared-codebase/)).
* **The KN5000 chord does not open them.** The owner tried the KN5000's
  columns 1 + 5 + 8 combination on his KN7000 and **no debug screen appeared.**

The negative result was not a dead end but a clue: the mechanism carried over,
the *constant* did not. Columns 1 + 5 + 8 give `0x91`, the KN5000's Panel
Simulator value, and the KN7000 dispatcher has no case for `0x91` — it falls
through and returns. The two instruments are not opcode-compatible in any case
(the KN7000's main CPU is a Panasonic MN1030-series **MN103002A**, not the
KN5000's Toshiba TLCS-900), so only the *UI framework lineage* transfers, never
the encoding.

Finding that chord paid exactly the dividend it was expected to. The viewer reads
any address in the CPU's space, so an owner can spot-check program flash
**without touching the board** — which turned "what is in build 893?" from a
soldering problem into a photographing problem, and then, with a capture card,
into [a video problem]({{ site.baseurl }}/kn7000-rom-from-the-screen/). The first
9,472 bytes are already transcribed:
[Recovering build 893]({{ site.baseurl }}/kn7000-build-893-recovery/).

## Provenance of the numbers on this page

| Claim | How it was checked |
|---|---|
| Format strings at `0x1D67E0` | read directly out of `kn7000_program.rom` (`PROGRAM : %4d`, `TABLE   : %4d`, `RHYTHM  : %4d`, `PICTURE : %4d`, `0x10` apart, `0xFF`-padded) |
| `PROGRAM` = 941 | `u16` LE at file `0x33660C` = `0x03AD` = 941 in `kn7000_program.rom` (sha1 `cc1c364c…`), and identically in the byte-interleaved pair `kn7000_program_{even,odd}.rom` that MAME actually loads |
| `TABLE` = 84 | table directory entry 7 (u32 at table offset `0x1C`) = `0x139EE8`; the four bytes there are `"84\n\0"` in `kn7000_table.rom` (sha1 `fcf5645a…`) and in the interleaved even/odd pair |
| Field ↔ source pairing | exhaustive 32-bit scan of the program image: one writer and one reader for each of `0x50007DC4` / `0x50007DC8` |
| Handler names | `kn7000_disassembly` symbol table, recovered from the firmware's own reflection tables |
| `PROGRAM : 893` / `TABLE : 80` | **owner testimony, 2026-08-08**, read off the LCD of a real SX-KN7000 |
| The 1 + 6 + 8 chord | **owner testimony**, performed successfully on real hardware |
| The 1 + 5 + 8 chord does *not* open a debug screen on KN7000 | **owner testimony**, negative result on real hardware |

## Related pages

- [Recovering build 893]({{ site.baseurl }}/kn7000-build-893-recovery/) — the photographic transcription, the four-step drift profile, and what to photograph next
- [Reading ROM out of the screen]({{ site.baseurl }}/kn7000-rom-from-the-screen/) — the video-grabber route to a full capture
- [MEMORY DUMP Screen]({{ site.baseurl }}/kn7000-memory-dump-screen/) — the hidden hex viewer, found after this page was first written
- [Firmware Images]({{ site.baseurl }}/kn7000-firmware/) — the two flash images, their layout, and the version fields in context
- [Firmware Robustness & ROM Archival]({{ site.baseurl }}/kn7000-firmware-security/) — why the instrument cannot dump itself
- [Program-ROM Clip Read (IC16/IC17)]({{ site.baseurl }}/kn7000-program-rom-clip-read/) — the practical route to capturing build 893
- [System Update Discs]({{ site.baseurl }}/kn7000-system-update-discs/) — where the 941/84 images come from
- [The built-in MEMORY DUMP screen]({{ site.baseurl }}/memory-dump-screen/) — the KN5000's equivalent hidden chord
- [Control Panel Protocol]({{ site.baseurl }}/kn7000-control-panel/) — the part-mixer buttons the chord uses
