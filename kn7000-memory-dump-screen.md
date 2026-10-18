---
layout: page
title: "MEMORY DUMP Screen (KN7000 built-in hex viewer)"
permalink: /kn7000-memory-dump-screen/
---

# The built-in MEMORY DUMP screen

The stock KN7000 firmware ships a **hex memory viewer** on a hidden factory
screen. Like its [KN5000 counterpart]({{ site.baseurl }}/memory-dump-screen/) it
can be reached on an unmodified instrument with no jumper, no jig, no disk and
no power-on combination — it is a runtime chord on the panel of a normally
booted machine. It reads any address in the CPU's 32-bit space, which makes it
the cheapest way to answer questions about what is really in the flash chips of
a particular unit.

On the KN7000 it is **not** nested inside the Panel Simulator the way it is on
the KN5000. On our image the chord opens the viewer directly, as a first-class
screen (`_TT_MEMDUMP`, title id `0xF2`). Whether *your* instrument behaves that
way depends on a single byte of the program flash, which turns out to be the
firmware's release number — see
[Two doors](#two-doors-the-configuration-byte-at-0x4840000f). Every numbered release
we can check opens the viewer directly: v1.5 and v1.6 from their code, v1.3 from its
byte if its gate code is unchanged; v1.4 is unknown, its byte having been on a lost
update disk. Only a build whose byte is `0xFF` opens the developers' Panel Simulator
and its [DEBUG TOOLS](#debug-tools) instead; of the builds we hold that is the SP7001
PLUG-iN build 942, which was shipped without a release number. Only on such a build
are the [LCD capture](#lcd-capture) chords live.

> ⚠ **Derived from PROGRAM 941 / TABLE 84; many owners run something else.**
> Every address, constant and disassembly listing below was read out of the
> program image this project reconstructed from the public update disks, and
> every behavioural step was driven in MAME against that image. The project
> owner's own instrument runs **PROGRAM 893 / TABLE 80**, which is
> [an unpreserved earlier firmware]({{ site.baseurl }}/kn7000-soft-version/).
> A chord table derived from our bytes is not automatically true of his. Two
> independent checks say the mechanism did carry over — see
> [What real hardware has already confirmed](#what-real-hardware-has-already-confirmed)
> — but treat any *unconfirmed* constant on this page as "expected", not
> "known", on a build other than 941.

## The four questions this page answers

The project owner opened this screen on his own instrument and asked four
things. Short answers, each with its own section below:

1. **Can it get data off the instrument?** No.
   [Only one debug feature in the whole firmware writes a file](#can-it-get-data-off-the-instrument),
   and it saves the *rendered screen*, not the memory you are pointing at.
2. **What is FULLTIME?** ["Keep this memory watch alive after I leave the
   screen"](#fulltime--the-onoff-box). It is the second LCD soft key down the
   left side. It is also the one setting on this screen that can bite you.
3. **What are the four saved addresses?** Not ROM — they are
   [watch-points on your own stored user data](#the-four-saved-addresses--what-they-actually-are):
   the battery-backed backup SRAM, your live panel setup, your 104 stored
   PANEL MEMORY records, and a work-RAM record table.
4. **Which chip is which?** See the
   [ROM inventory](#which-chip-is-which--a-rom-inventory), and what to dial to
   fingerprint each one.

## Procedure

PHYSICAL CONTROLS USED (KN7000 front panel)
- The **part mixer**: the row of tall button pairs directly below the display. The KN7000 has **sixteen** columns, each with an UP cap (*PART n ON*) above a DOWN cap (*PART n OFF*). Number them 1 (leftmost) to 16 (rightmost). These are the same buttons documented in the [Control Panel Protocol]({{ site.baseurl }}/kn7000-control-panel/) as `MUTE UP n` / `MUTE DOWN n`.
- The soft keys down the left and right edges of the LCD (`LCDL1`..`LCDL5`, `LCDR1`..`LCDR5`).
- EXIT.

STEP 0 — CALIBRATION, ZERO RISK. DO THIS FIRST.
Instrument on, at a normal play screen. Press and hold at the same time the UP and the DOWN cap of part-mixer columns **1, 6 and 8** (six caps). The SOFT VERSION screen should appear, showing PROGRAM / TABLE / RHYTHM / PICTURE, and go away again by itself after a few seconds. That is held-switch accumulator `0xA1`. **This step is confirmed working on real KN7000 hardware by the project owner** — it is not an emulator inference. If it works, the chord mechanism is live on your unit, your column numbering matches ours, and you have also just recorded the four numbers that identify your firmware (please report them; the [SOFT VERSION page]({{ site.baseurl }}/kn7000-soft-version/) explains why they matter).
IF NOTHING HAPPENS: do not escalate to the four-column chord. Re-read the column numbering — count from the far left of the mixer row — and try again. Rolling the six caps on one at a time is easier than slamming them down together, and it may take two hands.

STEP 1 — THE CHORD
Same idea, one more column: hold the UP **and** the DOWN cap of part-mixer columns **1, 4, 5 and 8** all at once (eight caps). That is accumulator `0x99`.
Two things about this chord matter and are easy to get wrong:
- It is the manual's own MUTE gesture applied to four parts at once, so nothing about pressing it is unusual for the instrument.
- The firmware tests **exact equality**, not a bit mask. One extra column with both caps held changes the accumulator and the chord silently does nothing (measured: columns 1,2,4,5,8 → `0x9B` → no screen). If you have big hands, brush a neighbouring pair and you will conclude the screen does not exist. It does; you missed.

STEP 2 — WHICH SCREEN CAME UP?
There are exactly two possible outcomes, and which one you get **reads out a configuration byte on your chip** (see [Two doors](#two-doors-the-configuration-byte-at-0x4840000f)).
- **A 16-row hex dump appears immediately.** You are in the viewer. Go to step 3.
- **A Technics wallpaper reading "Panel Simulator 2.1" appears**, with a DEBUG TOOLS caption at the bottom right. Press the bottom-right LCD soft key (`LCDR5`) to open **DEBUG TOOLS**, then the top-left soft key (`LCDL1`) for MEMORY DUMP. This route is *more* valuable, not less — see step 6.

STEP 3 — CHECK WHERE IT LANDED (SAFETY)
Read the address in the caption line (` DUMP ADR0 = xxxx xxxx `) before doing anything else. On a fresh power-up it will be one of four firmware defaults, all of them RAM (see [what they are](#the-four-saved-addresses--what-they-actually-are)). If it is anything in `0x96800000`-ish, `0x98000000`–`0x9807FFFF`, `0x9C000000`, `0x9CC00008`, `0x20000000` or `0x34000000`, move off it at once or press EXIT — those are the flash command window, the tone generator and floppy controller, the DSP port, the SD interface and CPU-internal I/O including the MIDI transmitter. The viewer repaints continuously, so a parked address is re-read over and over.

STEP 4 — DIAL AN ADDRESS
Part-mixer columns **1 to 8 are the eight hex digits of the address, in reading order**: column 1 is the leftmost digit, column 8 the rightmost. UP raises a digit, DOWN lowers it.

| Column | Step           | Column | Step       |
|--------|----------------|--------|------------|
| 1      | ± `0x10000000` | 5      | ± `0x1000` |
| 2      | ± `0x1000000`  | 6      | ± `0x100`  |
| 3      | ± `0x100000`   | 7      | ± `0x10`   |
| 4      | ± `0x10000`    | 8      | ± `0x1`    |

Columns **10, 11, 12 and 13** set the four colour-highlight bytes named in the
legend (`Aqua`, `Yellow`, `Lime`, `Fuchsia`) — any byte in the dump equal to one
of those four values is drawn in that colour, which is a genuinely useful way to
find a value at a glance. Column **15 steps between the four saved address slots
ADR0..ADR3**. **Columns 9, 14 and 16 do nothing at all**, and that is by design
rather than by accident: the screen's resource table gives its rockers the edit
switches `ES_Bottom1`..`ES_Bottom8`, `ES_Bottom10`..`ES_Bottom13` and
`ES_Bottom15`, and `ES_Bottom9` / `ES_Bottom14` / `ES_Bottom16` have no owner.

This whole table is now **proven from the firmware's own screen resources**, not
merely measured. Each rocker is a widget record carrying both its internal
control index and its edit-switch id; the two columns below are read straight
out of those records (`0x485D5FE4`..`0x485D6224`, control index at `+0x1C`,
edit-switch id at `+0x28`), and the step law `± (1 << 4i)` is read out of the
step handler at `0x48487E60`:

| Internal index *i* | Edit switch                  | Panel column      | Effect                                  |
|--------------------|------------------------------|-------------------|-----------------------------------------|
| 0                  | `ES_Bottom8` (7)             | 8                 | address ± `0x1`                         |
| 1..6               | `ES_Bottom7`..`ES_Bottom2`   | 7..2              | address ± `1 << 4i`                     |
| 7                  | `ES_Bottom1` (0)             | 1                 | address ± `0x10000000`                  |
| 8                  | `ES_Left2` (0x91)            | *left soft key 2* | **FULLTIME** (not a rocker)             |
| 9..12              | `ES_Bottom10`..`ES_Bottom13` | 10..13            | highlight bytes 0..3, clamped 0..`0xFF` |
| 13                 | `ES_Bottom15` (0x0E)         | 15                | ADR slot 0..3                           |

The digits therefore run "backwards" internally — index 0 is the *rightmost*
digit — which is exactly why the panel column and the internal index never
looked like they lined up. They do; they simply run in opposite directions.
Everything is printed on the screen anyway, so a single test press re-derives
the mapping on any unit.

WRAP: the value has no wrap at `0xFFFFFFFF`. Instead, any address that reaches `0xC0000000` or above is masked down with `& 0x0FFFFFFF` on the next step, so dialling the top digit up past `B` drops you into `0x0xxxxxxx`. Coming *down* from `0x84000000` to the program flash at `0x48400000` takes four presses of column 1's DOWN cap (to `0x44000000`), then four of column 2's UP cap (to `0x48000000`, the table flash) and four of column 3's UP cap, and is the normal way to get there.

STEP 5 — READ AND RECORD
256 bytes per screenful (16 rows × 16 bytes), shown as an 8-hex-digit address, sixteen hex bytes with a `-` separator after the eighth, and an ASCII column with `.` substituted for bytes below `0x20`. Photograph the screen. The four cheapest and most valuable addresses on an instrument whose firmware is not ours:

| Address                       | What ours reads                                   | What it settles                                                                                                                                                                                                                                                                |
|-------------------------------|---------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `0x48400000`                  | `DC 7E FF 00 00 CB CB CB CB CB DC C5 77 0D 00 16` | The program-flash header. The **16th byte** is the configuration byte that chooses which of the two doors your chord opens, and it is compared against `0x77` elsewhere in the firmware, so it is a configuration/destination code, not a debug flag.                          |
| `0x4873660C`                  | `AD 03 00 00` (= 941)                             | Whether build 893's layout is *aligned* with ours. `7D 03 00 00` (= 893) here would mean the two builds sit at the same offsets, which would make a cross-version diff enormously easier. Anything else means the layout moved.                                                |
| `0x487F6E00` and `0x487F7000` | `4E 0C F6 DF …` and all `FF`                      | Where the image ends. Ours stops at `0x487F6F00`.                                                                                                                                                                                                                              |
| `0x48000000` (table flash)    | `00 02 00 00 58 48 03 00 08 5D 03 00 74 06 04 00` | The table-flash directory: the lower half of the same IC16/IC17 pair (tables 84 and 83 are preserved; the owner's table 80 is not). Its version pointer is the 32-bit word at `0x4800001C` (ours `0x00139EE8`, so the ASCII version string is at `0x48139EE8` and reads `84`). |

STEP 6 — IF YOU LANDED ON THE PANEL SIMULATOR, YOU HAVE A BMP EXPORT
The same configuration byte that sends you to the Panel Simulator also **enables the LCD screen-capture chord**, which the direct-viewer branch disables. It writes the framebuffer to a file named `LCDCAP%02d.BMP` on whatever media is currently selected. On such a unit, memory-dump screens can be *saved as image files* instead of photographed, which is the difference between a legible archive and a pile of phone snaps. If your chord opened the Panel Simulator, say so — it changes what is worth attempting on your instrument.

STEP 7 — LEAVE
EXIT. No power cycle is needed, and nothing you did needs undoing — **unless you
turned FULLTIME on**, in which case read the next section.

## FULLTIME — the ON/OFF box

`FULLTIME` is the ON/OFF box on the MEMORY DUMP screen, and it means **"keep
this memory watch alive after I leave the screen"**. It is not a freeze, not a
snapshot, not a global debug-enable and not a profiling counter.

**It is the second LCD soft key down the LEFT side of the display.** That is
read out of the widget's own resource record, which names edit switch
`ES_Left2` = `0x91`; the firmware enumerates its own edit switches in a
`{name, value}` pair array at `0x485B0C68` (`ES_Bottom1`..`16` = `0x00`..`0x0F`,
`ES_Right1`..`5` = `0x10`..`0x14`, `ES_Exit` = `0x17`, `ES_Left1`..`5` =
`0x90`..`0x94`, `ES_None` = `0xFF`), and pressing that key in the emulator drove
the toggle. The box itself is an `AcIndexToggle` at `0x485D5F6C`; its caption
comes from the label at `0x485D5FA8`, whose string `"FULLTIME"` at `0x485D5F9C`
has exactly **one** reference in the entire 4 MB image.

What it actually switches: the viewer always free-runs while its window is open.
`MT_Draw` paints the frame and sends `MT_SeleDraw`; `MT_SeleDraw` repaints and
re-arms itself with `SetApTimer(0x78, …)`, so the watched address is re-read and
redrawn periodically: measured in the emulator, an idle repaint comes every
~2.95 s and itself takes ~112 ms (see
[Reading ROM out of the screen §4]({{ site.baseurl }}/kn7000-rom-from-the-screen/#4-the-firmwares-repaint-is-not-atomic--and-that-is-not-tearing)).
When the window closes, the `EV_HIDE` handler normally kills those timers —
**but only if the FULLTIME shadow at `0x5006B528` is clear**:

```
48487993: fc a4 28 b5 06 50   mov  (0x5006b528), d0     ; the FULLTIME shadow
48487999: a0 00               cmp  0, d0
4848799b: c9 3e               bne  0x484879d9           ; set -> SKIP the timer flush
```

That single branch is the whole feature. That cell has exactly **four**
references in the image — two reads and two writes, all inside
`DbMemoryDumpProc` — and this is its only behavioural effect.

With FULLTIME ON, leaving the screen leaves the hex grid **painted on top of
whatever you do next, still updating**. This was verified in MAME with a null
control: two identical runs differing only in whether the left-2 soft key was
pressed. In the FULLTIME run the HOME/play screen six seconds after EXIT still
carries the hex grid and its legend drawn over it; in the control run the same
EXIT leaves a clean HOME screen.

> ⚠ **This is the one setting on the screen that can bite you.** With FULLTIME
> ON the polling of the parked address continues *with no viewer left on screen
> to EXIT from*. If you parked the address over an I/O window, you have now made
> that a permanent background activity. To stop it: re-open MEMORY DUMP (the
> `0x99` chord — its `EV_SHOW` handler flushes the timers unconditionally) with
> FULLTIME off, or power-cycle. The shadow is plain uninitialised RAM and is
> zero at every power-on.

One prediction from the code that was **not** tested: because the toggle is a
radio-group member that always drives itself ON, while the viewer's ON→OFF
re-broadcast passes the widget's *tag* (0) rather than its *index* (8), the box
may keep reading `ON` after a second press even though the behaviour has already
reverted. Only one press was exercised in the emulator.

## The four saved addresses — what they actually are

Every KN7000 that has ever opened this screen has opened it on the same four
addresses, and none of them is ROM. They are **watch-points on your own stored
user data** — which is exactly what a factory technician would want, and exactly
not what an archivist would want.

| Slot | Address      | What it is                                                                                                                                                                                              |
|------|--------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ADR0 | `0x84000000` | Base of the **256 KB battery-backed backup SRAM** (IC23), i.e. the start of its checksummed settings header — `0x7A0` bytes, whose one's-complement word sum is stored back at `0x84030174`.            |
| ADR1 | `0x84000770` | The global immediately after the **live panel-settings record**, which occupies `0x84000020`..`0x8400076F`. The library folds that record's size as the difference `0x84000770 − 0x84000020` = `0x750`. |
| ADR2 | `0x84000814` | The `0x10`-byte header of the **PANEL MEMORY store**.                                                                                                                                                   |
| ADR3 | `0x501A5920` | Record 0, field `+0x120`, of an 11-entry table of `0x8E0`-byte records at `0x501A5800` in work RAM. **Identity plausible only**: probably the sequencer song slots.                                     |

`0x44000000`, mirrored at `0x84000000`, is **not** generic work RAM. The service
RAM DEVICE TEST walks it from
`0x44000000` for `0x20000` iterations of two bytes each, i.e. exactly 256 KB,
which fixes the extent of the battery-backed part; and the firmware checksums a
header there and stores the result inside the same device, which is the classic
backup-validity pattern.

The PANEL MEMORY geometry comes out of the library's own addressing arithmetic:

```
addr(i) = 0x84000824 + (i / 8) * 0x3A90 + 0x10 + (i % 8) * 0x750 ,  i < 0x68
```

`0x68` = 104 = **13 banks × 8 memories**, which is verbatim what the owner's
manual specification page claims (`PANEL MEMORY 13 BANKS × 8`), and
`0x3A90 = 0x10 + 8 × 0x750` makes each bank self-consistent. As a check that
falls out for free: the whole store is `13 × 0x3A90` = `0x2F950` bytes, so it
spans `0x84000824`..`0x84030173` and **ends exactly where the checksum cell
`0x84030174` begins**. Two independently-derived addresses abutting is a good
sign that both are right.

ADR3 is the interesting one, because it is not a constant anywhere — it is
computed at run time as `0x501A5800 + 0 × 0x8E0 + 0x120`. See
[the next section](#what-real-hardware-has-already-confirmed) for why that
matters.

**A detail nobody has ever seen.** The *linked* defaults — the values the
compiler put in the `.data` image, which the boot loader copies to RAM on every
power-on — are different, and rather more useful:

```
ROM 0x487B1E54:  00 00 00 84 | 00 00 00 50 | 00 00 00 4C | 00 00 40 48
                 0x84000000    0x50000000    0x4C000000    0x48400000
                 f0 00 f7 00 ff 00 ff ff  <- the four highlight bytes
                 01 00 00 00              <- "slots need defaults" flag
```

One slot per address space, **including the program flash at `0x48400000` and
the library window at `0x4C000000`**. The author of this screen did park a slot
on the ROM. The first `EV_SHOW` then overwrites three of them and computes the
fourth, before the screen is ever painted — so those source-level defaults have
never appeared on anybody's LCD. (The highlight bytes next to them are *not*
overwritten by any code, which is why the legend always starts at
`Aqua = F0  Yellow = F7  Lime = FF  Fuchsia = XX`; `FFFF` is the disabled
sentinel, printed as `XX`.)

> **A note for MAME users.** The driver currently maps `0x44000000` as 16 MB of
> plain RAM with no NVRAM backing, so in emulation your 104 panel memories are
> lost on every restart and the 256 KB wrap is invisible. On real hardware this
> region is battery-backed. See
> [MAME emulation gaps]({{ site.baseurl }}/mame-emulation-gaps/).

## Can it get data off the instrument?

**No.** This was the owner's first question and it deserves a blunt answer.

**MEMORY DUMP itself has no export of any kind.** It is strictly read-only with
respect to the address you point it at. Statically: every store in the whole
window procedure targets the stack frame or five work-RAM cells of its own — the
four address slots at `0x500012EC`, the four highlight bytes at `0x500012FC`,
the init flag at `0x50001304`, the slot selector at `0x5006B524` and the
FULLTIME shadow at `0x5006B528`. A byte scan of the entire 4 MB image finds
**every** reference to those five cells inside this one procedure. The inspected
address is only ever *read*, with `movbu (dN,aN),dM`. Its ten event handlers
call ten routines between them, and not one of them is a file, card, MIDI, port
or flash-command routine. Dynamically: a write tap over the whole `0x96xxxxxx`
flash window counted **zero writes** across a full open → drive-every-control →
EXIT session in MAME.

**Exactly one debug feature in the firmware writes a file, and it is the wrong
one** — and it only works on a build whose release byte is `0xFF`: of the builds we
hold, only the SP7001 PLUG-iN build 942, not v1.5 or v1.6 ([LCD capture](#lcd-capture)). Two chords run `CaptureLcd` at
`0x4841567D`, which does
`sprintf` into `LCDCAP%02d.BMP` (format string at `0x4859E2E4`, counter at
`0x50021FC8`), `fopen`s it `"wb"` and writes a Windows bitmap. Its source is
**hardcoded**:

```
484157c0: fc d0 00 00 e0 9c   add   0x9ce00000, a0     ; the composited LCD framebuffer
484157c9: f0 6c               movhu (a0), d3           ; ... unpacked from RGB565 below
```

`0x9CE00000` is the composited LCD framebuffer, and the area variant reads a
second framebuffer plane at `0x500D4080`. Neither ever touches the memory-dump
address slots. So capturing the hex viewer captures the **rendered screen** —
256 inspected bytes as ASCII text, needing OCR to be useful again — not raw
memory. The file lands on whichever media the current-drive selector at
`0x5007125A` names, because the `fopen` thunk indexes a per-backend table
(floppy prepends `A:\`, SD prepends `C:\`) and `CaptureLcd` passes a bare
filename.

**And no other route exists.** The generic `fwrite(src, len)` primitive is real
and could in principle write any range, but every one of its call sites either
is LCD capture (fixed framebuffer source) or gathers one specific data structure
— a song, a custom style, a setup, a wallpaper. No debug widget ever calls it
with an address you chose. MEMO LOG and the other DEBUG TOOLS entries persist
nothing; the only file operation in DEBUG TOOLS is BITMAP LOAD, which *reads* a
BMP. Nothing routes memory to MIDI OUT, to RS-232, or to the (dormant,
undumped-coprocessor) USB link.

At 256 bytes per screenful, photographing the whole 4 MB program flash would be
**16384 screenfuls**. This screen settles questions; it does not replace a dump.
For what it would actually take to capture PROGRAM 893, see
[Firmware Robustness & ROM Archival]({{ site.baseurl }}/kn7000-firmware-security/)
and the [in-circuit clip read of IC16/IC17]({{ site.baseurl }}/kn7000-program-rom-clip-read/).

**But the screen is still an output.** It cannot *export* bytes, yet it can
*display* them, and the rear composite VIDEO OUT carries whatever it displays. A
capture card plus the auto-repeating page rocker turns 16384 screenfuls from a
photography problem into about fifty minutes of held button — see
[Reading ROM out of the screen]({{ site.baseurl }}/kn7000-rom-from-the-screen/),
which measures 99.87 % byte accuracy on emulator frames and, so far, refuses every
real composite frame it has been given. Thirty-seven screenfuls of build 893 have
already been read the slow way, by hand, from photographs:
[Recovering build 893]({{ site.baseurl }}/kn7000-build-893-recovery/).

## What real hardware has already confirmed

Three independent facts, all from the project owner's instrument running the
undumped PROGRAM 893:

1. **The SOFT VERSION chord (columns 1, 6, 8) works on his machine.** That is
   the `0xA1` case of the very same dispatcher, at the very same panel
   accumulator. The chord mechanism, the both-caps-held accumulation and the
   column-to-bit numbering are therefore not emulator artefacts.

2. **His MEMORY DUMP screen shows four saved addresses — `0x84000000`,
   `0x84000770`, `0x84000814` and `0x501A5920` — and those are exactly the four
   values our firmware computes as its first-open defaults.** The first three
   are immediate constants in the viewer's initialiser. The fourth is not a
   constant anywhere: it is the *return value of a helper call*, computed at
   run time as `0x501A5800 + 0 × 0x8E0 + 0x120`. It could not have been copied
   out of any note or page in this project, because until this page was written
   nothing here recorded it.

```
48487903: fc a4 04 13 00 50   mov   (0x50001304), d0    ; "slots need defaults" flag
48487909: a0 00               cmp   0, d0
4848790b: c8 39               beq   0x48487944          ; zero -> keep whatever is in the slots
4848790d: fc cc 00 00 00 84   mov   0x84000000, d0
48487913: fc 81 ec 12 00 50   mov   d0, (0x500012ec)    ; ADR0 = 0x84000000
48487919: fa c0 70 07         add   0x770, d0
4848791d: fc 81 f0 12 00 50   mov   d0, (0x500012f0)    ; ADR1 = 0x84000770
48487923: fc cc 14 08 00 84   mov   0x84000814, d0
48487929: fc 81 f4 12 00 50   mov   d0, (0x500012f4)    ; ADR2 = 0x84000814
4848792f: 00                  clr   d0
48487930: dd 8b f5 fc ff 00 00 call 0x48456ebb, 0, 0    ; helper(0) -> a0
48487937: fc 80 f8 12 00 50   mov   a0, (0x500012f8)    ; ADR3 = 0x501A5920
4848793d: 00                  clr   d0
4848793e: fc 81 04 13 00 50   mov   d0, (0x50001304)    ; and clear the flag
```

```
48456ebb: 81                  mov   d0, d1
48456ebc: 15                  extbu d1
48456ebd: a5 0b               cmp   0xb, d1
48456ebf: c2 17               bge   0x48456ed6          ; index >= 11 -> the constant below
48456ec1: 14                  extbu d0
48456ec2: 2d e0 08            mov   0x8e0, d1
48456ec7: f2 54               mulu  d1, d0
48456ec9: fc c0 00 58 1a 50   add   0x501a5800, d0
48456ecf: 24 20 01            mov   0x120, a0
48456ed2: f1 60               add   d0, a0              ; index 0 -> 0x501A5920
48456ed4: f0 fc               rets
48456ed6: fc dc 20 59 1a 50   mov   0x501a5920, a0      ; and the fallback is the same address
48456edc: f0 fc               rets
```

Both paths of that helper produce `0x501A5920` for index 0, and a scan of the
whole image finds that value as a literal in exactly one place — this function's
own fallback. So the four addresses on his LCD are our four defaults, digit for
digit.

3. **His configuration byte reads `0x13`.** The owner dialled `0x48400000` and read
   the last byte of the row, `0x4840000F`, as `0x13` (2026-10-18), the same value as
   in the earlier [photo transcription]({{ site.baseurl }}/kn7000-build-893-recovery/).
   It is his firmware's release number, v1.3 (see
   [Two doors](#two-doors-the-configuration-byte-at-0x4840000f)).

What items 1 and 2 **prove**: the hidden viewer exists and opens on PROGRAM 893, and
this initialiser — including a helper in a completely different part of the
image — is present and behaves identically on a build we have never executed.
It also means build 893's work-RAM layout in the `0x501A5xxx` region matches
941's, a free cross-version calibration point.
Item 3 makes it very likely that he came through the direct door: with `0x13`, the
gate code of every complete build we hold (935, 941, 942) opens the viewer directly
and keeps both LCD-capture chords dead. 893's own gate code has not been transcribed,
though its first program row has the same layout as v1.5's.

A practical corollary of the flag at `0x50001304`: the defaults are installed
**once**, and then the flag is cleared, so within a power cycle the slots keep
whatever you dial into them. Four addresses can be parked and revisited with
column 15. (No absolute store anywhere in the image *sets* that flag — only
this routine reads it and clears it — so what makes it nonzero at first open is
the boot loader's `.data` copy, which restores its linked value of `1`.)

## Two doors: the configuration byte at 0x4840000F

The `0x99` chord does not go straight to the viewer. It first calls a
two-instruction accessor that returns a single byte out of the program-flash
header, and branches on it:

```
484d7928: fc a8 0f 00 40 48   movbu (0x4840000f), d0
484d792e: de 00 00            retf  0, 0
```

```
484148dc: dd 4c 30 0c 00 00 00 call 0x484d7928, 0, 0
484148e3: 14                    extbu d0
484148e4: fa c8 ff 00           cmp   0xff, d0
484148e8: c9 0d                 bne   0x484148f5        ; NOT 0xFF -> hex viewer
484148ea: 00                    clr   d0
484148eb: 04                    clr   d1
484148ec: dd 5c 6a 01 00 e0 20  call  0x4842b348, …     ; 0xFF -> ChangeMode(0,0) = Panel Simulator
484148f3: ca 46                 bra   0x48414939
484148f5: 2c f2 00              mov   0xf2, d0          ; _TT_MEMDUMP
484148f8: 04                    clr   d1
484148f9: dd a7 6b 01 00 e0 20  call  0x4842b4a0, …
```

In our PROGRAM 941 image that byte is **`0x16`** — non-`0xFF`, so our chord
opens the hex viewer directly. On a unit where the byte is `0xFF` the same
chord lands on **Panel Simulator 2.1** instead, and the viewer is two soft keys
further in (LCDR5, then LCDL1), through a **DEBUG TOOLS** screen (`_TT_DEBUG`, title
id `0xFF`) that also offers MEMO LOG, ICON LIST, COLOR LIST, BITMAP LOAD, a
`DEBUG MODE : OFF/ON` switch, a mode enumerator reading `015 : _MD_SONG`, and a
`--- SOFTWARE VERSION ---` box with the same four numbers as the SOFT VERSION
screen (all described under [DEBUG TOOLS](#debug-tools)).

The two outcomes are mutually exclusive, which makes the chord **a one-press
probe of that byte on any unit**. It is worth reporting which screen you got
even if you go no further.

The LCD screen-capture chords are gated the *other* way: they require the byte
to **be** `0xFF`, so capture is dead on our image and live on a Panel-Simulator
unit ([LCD capture](#lcd-capture)).

**The byte is the release number.** The firmware itself prints it as a version:
the welcome-screen class `AcMPVer` formats it with `"%s    Ver%1X.%1X"`, so `0x16`
is "Ver1.6" (and 942's `0xFF` would print "VerF.F"). The builds:

| build | release                 | byte at `0x4840000F`                             | chord 1/4/5/8 opens | LCD capture                          |
|-------|-------------------------|--------------------------------------------------|---------------------|--------------------------------------|
| 893   | v1.3 (the owner's unit) | `0x13`                                           | the hex viewer      | dead (same gate assumed)             |
| 929   | v1.4                    | lost with update disk 1 (by the pattern, `0x14`) | —                   | —                                    |
| 935   | v1.5                    | `0x15`                                           | the hex viewer      | dead                                 |
| 941   | v1.6                    | `0x16`                                           | the hex viewer      | dead                                 |
| 942   | v1.6 PLUG-iN (SP7001)   | `0xFF`                                           | Panel Simulator 2.1 | live (read from the code; never run) |

The gate code is the same in 935, 941 and 942 apart from relocated addresses. The
byte lives in the program flash itself, so only a program update changes it.
Going by its code, installing the SP7001 update would open these screens (942 has not
been run in MAME or on hardware), and would
also overwrite its program for good, which for the owner's unarchived 893 must not be
done; MAME with the byte patched is the safe way to see them.

## DEBUG TOOLS

DEBUG TOOLS (`_TT_DEBUG`, title `0xFF`) is the developers' menu behind the Panel
Simulator. It is reached only on a build whose byte at `0x4840000F` is `0xFF`: hold the
`1`/`4`/`5`/`8` chord, which then opens "Technics / Panel Simulator 2.1", and press
**LCDR5** (bottom right). On v1.6 (941) there is no route to it: the chord opens
MEMORY DUMP directly, and EXIT from there returns to the play screen (measured in MAME);
v1.5's gate code is the same.
Every call that could open the Panel Simulator or DEBUG TOOLS was checked; the only other
"DEBUG TOOLS" key sits on an unreferenced "Panel Simulator for IK" test screen. In MAME,
write `0xFF` to byte `0x0F` of the `:maincpu` region after boot and use the chord.

The screen carries MEMORY DUMP and MEMO LOG on the left soft keys, ICON LIST, COLOR LIST
and BITMAP LOAD on the right, the SOFTWARE VERSION box, and two controls worked with the
part-mixer (balance) buttons:

### DEBUG MODE : OFF / ON

A developer switch that adds extras to five ordinary screens. **UP of balance column 2
or 3 sets ON, DOWN sets OFF** (it is not a toggle; columns 1 and 4 do nothing). It lives
in work RAM (`0x5015080C`, `DbModeEditBox`), so it is OFF again after every power-on.
Changing it broadcasts `MT_SetDebugMode` to every mode and title of the UI. It adds no
logging, relaxes no check and has nothing to do with LCD capture. What it changes, each
seen in MAME:

| screen                          | with DEBUG MODE ON                                                                                                     |
|---------------------------------|------------------------------------------------------------------------------------------------------------------------|
| SOUND MENU > PART SETTING       | the PART SELECT list grows from 22 to 32 parts: ACCOMP 1–5, BASS, DRUM 1, DRUM 2, PADS 1 and PADS 2 become selectable  |
| SOUND MENU > APC REVERB SETTING | a second DEPTH column at the right edge, read back from the eight accompaniment parts                                  |
| PROGRAM MENUS > REVERB & EFFECT | the blank LCDL2 key opens a hidden **EFFECT DEBUG** screen (title `0x3E`): an effect grid with mode toggles            |
| APC SELECT                      | a window with four editable APC wait times (OFF / 1st / 2nd / more 3; 0–500, defaults 192 / 40 / 24 / 4), columns 8–11 |
| HELP text pages                 | a page-number box at the bottom right; column 16 steps through the help pages                                          |

The first two react only to the broadcast, so they need the real switch; the last
three read `0x5015080C` directly. The DEMO mode also records the setting, but nothing
reads it there. Build 942 has the same code.

### The mode / title list ("015 : _MD_SONG")

The box next to DEBUG MODE is a separate tool (`DbVariableMenu`): a list of every UI
**mode** and **title** by the developers' own names, which come from tables in the
firmware. The number is hexadecimal — `015` is mode `0x15`, `_MD_SONG`. Balance column
11 steps through the 32 modes (`_MD_PS`, mode 0, is the Panel Simulator) and then the 320
titles (`_TT_PS` ... ); **LCDR5 jumps** to the selected one. It does not interact with
DEBUG MODE. Some modes, `0x15` among them, are never registered, so jumping to them
probably lands on the Panel Simulator (inferred).

### BITMAP LOAD

A preview tool: it shows a `.BMP` file from a floppy on the LCD, through the same
drawing path the instrument uses for its own BMP pictures. It writes nothing.

1. Insert a DOS floppy (1.44 MB or 720 KB) with the pictures in its **root
   directory**, named `*.BMP`. Only the **first ten** matches can be reached.
2. On DEBUG TOOLS press **LCDR3** (BITMAP LOAD). The box "BITMAP FILE :" shows
   `NN:NAME`; step through the files with the UP/DOWN buttons of balance **column 5
   or 6**.
3. Press **LCDR4** (LOAD). The file is read — at most `0x18000` bytes (96 KB) — into
   the work area at `0x502B8000` and drawn at the top-left corner by `Draw2BpFile`.
4. EXIT goes back to the list (rescanned, back to file 00); EXIT again to DEBUG TOOLS.

What a file must be: an uncompressed Windows BMP with the 40-byte header, 1, 4 or 8
bits per pixel, rows bottom-up, and the whole file no larger than 98,304 bytes — so a
full 640 × 240 picture needs 4 bpp or less. 8-bit pictures should use at most **176
colours**: the routine loads the file's colours 0–175 into palette entries `0x20`–`0xCF`
and adds `0x20` to every pixel, so higher indices show other colours. Tested in MAME
with the files written into memory (MAME's floppy reads no sectors yet):

| file                             | result                                                                         |
|----------------------------------|--------------------------------------------------------------------------------|
| 320 × 240, 8 bpp                 | drawn exactly, top-left                                                        |
| 640 × 240, 4 bpp (76,918 bytes)  | fills the screen                                                               |
| 640 × 240, 1 bpp                 | fills the screen                                                               |
| taller than 240 rows             | the top 240 rows are shown                                                     |
| 640 × 240, 8 bpp (154,678 bytes) | only the first 96 KB is read: rows 89–239 are right, the rest is stale memory  |
| 700 pixels wide                  | not clipped: each row runs into the next screen line                           |
| top-down (negative height)       | nothing drawn                                                                  |
| 24 bpp, 2 bpp, RLE, V5 header    | refused: a black view with only the file label, no message                     |

Why a developer would want it: a 640 × 240 4-bpp BMP is exactly what the firmware's
own LCD capture writes on the 2-bit (4-grey) display variant, and three of the DEBUG
TOOLS sub-screens form an artwork check-list: ICON LIST pages through the icons, COLOR
LIST shows all 256 palette entries with their RGB values, and BITMAP LOAD shows a real
file.
The name `Draw2BpFile` most likely refers to that 2-bit display; the routine itself is a
copy of the ordinary BMP blitter (see the
[Display Subsystem]({{ site.baseurl }}/kn7000-display-subsystem/#windows-bmp-files)).

## LCD capture

On a build whose byte at `0x4840000F` is `0xFF` — of the builds we hold, only the SP7001
build 942 — two chords save the screen as a BMP file:

- **The four corners:** hold **LCDL1, LCDL5, LCDR1 and LCDR5** — the top and bottom soft
  keys on both sides of the display — in any order. The capture happens when the fourth
  goes down. The keys keep their normal functions, so choose a screen where they are
  harmless (the play screen and MEMORY DUMP are). While all four are held, almost any
  further press or release of a soft key or part-mixer (balance) button makes another
  capture; pressing both halves of another pair blocks it, and releasing that pair
  captures again.
- **DISPLAY HOLD + pads:** hold DISPLAY HOLD, hold PAD 1, then press PAD 2 (any other
  performance pad also completes it). DISPLAY HOLD also
  toggles hold mode and the pads sound; press DISPLAY HOLD once more afterwards.

The file is `LCDCAP00.BMP`, `LCDCAP01.BMP`, … on the current drive — the floppy, `A:\`,
outside SD-card operations. On the KN7000's colour LCD it is 640 × 240, 24-bit,
uncompressed, 460,854 bytes (a 1.44 MB disk holds three); in the 2-bit LCD mode the
routine writes a 640 × 240 4-bpp file instead. There is no message and no beep; the numbering starts again at 00 at
every power-on and an existing file is replaced.

In MAME, PROGRAM 941 with the byte patched to `0xFF` behaves exactly so: both chords run
`CaptureLcd`. MAME's floppy cannot write yet, so the file was obtained by steering the
firmware's file calls to its SD-card backend (an emulator-only intervention); the image
is the screen shifted up by one row. Whether real hardware shows the same one-row shift
is unknown. The SP7001 image itself does not boot in the current MAME build, so the
capture has not been run on 942.

## What it can read

READ: any address the CPU can address, 256 bytes per screenful. The renderer
re-clamps each row base at `0xBFFFFFF0`, so the last usable row starts at
`0xBFFFFFE0`; everything below that is dialable, **including both flash devices
in full**.

**CANNOT WRITE**, and **cannot export** — see
[Can it get data off the instrument?](#can-it-get-data-off-the-instrument) for
the proof of both.

## Which chip is which — a ROM inventory

You do not have to guess at the chip names: the firmware's own service ROM test
prints them, and those label strings are in the image we hold (at CPU
`0x48609728` onwards).

| Firmware's label                                                                       | Window to dial                                                                                                                                                                      | Preservation status                                                                                                                                                                                                                                                                                                                                                        |
|----------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `PROGRAM ROM: IC16 = , IC17 = `                                                        | `0x48000000`–`0x487FFFFF` (**8 MB**: the table image is the *lower* half, the program image the upper half)                                                                         | **Dumped** from the update disks for builds 941/84, 935, 942/83 (SP7001) and the upper half of 929, except one hole on standard builds: **`0x483E94D4`–`0x483FFFFF` (92,972 bytes)**, the top of the lower half, which no standard update payload ships (the SP7001 table update does fill it) and nobody has read on a stock unit. **Your build is the archival target.** |
| `RHYTHM ROM: IC18 (IC20) = `                                                           | not directly CPU-mapped in our model                                                                                                                                                | **Undumped.** Upstream MAME declares it `NO_DUMP`; the development driver in the kn7000_mame overlay substitutes a clearly-labelled synthetic name resource at `0x54E00000`, a genuine firmware probe window. Anything you see there *in the emulator* is synthetic.                                                                                                       |
| `PICTURE ROM: IC19 = `                                                                 | `0x57800000`–`0x57FFFFFF` (4 firmware references)                                                                                                                                   | **Undumped**, and unmapped in MAME (reads `0x00` there). On real hardware it has content.                                                                                                                                                                                                                                                                                  |
| `CUSTOM FLASH: IC21 = `                                                                | `0x96800000`–`0x969FFFFF`, the one window the firmware uses for it: it reads the data there (e.g. the slot descriptors at `0x96820002`) and ⛔ also issues its flash commands there | A real, writable 16 Mbit flash (house code C3FBMD000050 in the service manual, which is IC20's code and probably copied from it; the firmware accepts a Fujitsu MBM29LV160B, Macronix MX29LV160B or Atmel AT49BV16X4) holding your own custom data. **Do not leave the repainting viewer parked on it**: the same window is the flash command window.                      |
| `MAIN TG BANK 0-15 ROM: IC203= , IC204= ` and `SUB TG BANK 0-15 ROM: IC207= , IC208= ` | **not CPU-mapped at all**                                                                                                                                                           | **Undumped** wave/sample mask ROMs, reachable only through the tone generator's readback registers. They cannot appear in this viewer. See [Expansion Bus & Wave-ROM Dump]({{ site.baseurl }}/kn7000-expansion-and-wave-dump/).                                                                                                                                            |

Two more kinds of window turn up in the firmware. The first is the EXP.CS "SOUND
RAM" expansion windows, among them `0x56000000` (170 references) and
`0x57000000` (89): they read empty unless an SY-EW board is fitted, and MAME maps
them as empty (see [Expansion Bus & Wave-ROM Dump]({{ site.baseurl }}/kn7000-expansion-and-wave-dump/)).
The second is the `0x4C000000` library/kernel window — which is **not a chip at
all**: the boot loader copies it into RAM out of the program flash, so it is
already preserved inside the IC16/IC17 dump.

> **An architectural correction, 2026-08-09.** The firmware's own ROM-test labels
> say `IC18` = RHYTHM and `IC19` = PICTURE, while older extraction notes assigned
> `IC18`/`IC19` to the chips holding the "table" image at `0x48000000`. Those two
> statements cannot both be right, and the current reading is that the older notes
> were wrong: **IC16 + IC17 are one 8 MB pair spanning `0x48000000`–`0x487FFFFF`**,
> with the table image as its lower half and the program image as its upper half.
> The evidence is 21 address lines (A2–A22) on a 32-bit bus, corroborated by the
> firmware's own service ROM test at `0x4849FC54` — `0x200000` iterations of a
> 4-byte stride = 8 MB — printed under the screen row
> `PROGRAM ROM: IC16 = , IC17 = `. Two consequences: there is **no** separate
> unread upper half at `0x48800000`, and the only never-read part of the pair is
> `0x483E94D4`–`0x483FFFFF` on units without the SP7001 PLUG-iN, whose table
> update fills it. Any older note calling the custom-data flash "IC18" is wrong
> either way — the firmware calls it IC21.

## ⛔ DANGER — power-on combinations that erase or reprogram flash

None of this is on the screen described above, and none of it can be reached by
accident from it. It is here because anyone reading this page is standing in
front of an instrument whose firmware may be the only surviving copy, and the
destructive combinations are held **at power-on**, which is exactly when a
curious owner is most likely to be holding buttons.

| Combination                                                                | Effect                                                                                                                                                                                                                                            |
|----------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ⛔ **PANEL MEMORY 1 + 2 + 3 + 4 held during power-on**                     | Enters **Flash Memory Update**. Erases and reprograms IC16/IC17. On an instrument running an unpreserved build this **destroys it irreversibly**.                                                                                                 |
| ⛔ PANEL MEMORY 2 + 3 + 4 held during power-on                             | The same updater in verify-only mode. One button away from the destructive one — which is the reason it is listed here rather than recommended.                                                                                                   |
| ⛔ RHYTHM `[60s & 70s]` + `[MODERN DANCE]` + `[SOUL & R&B]` at power-on    | Post-update re-initialisation. The vendor's own installation notes warn that all stored data except Custom memory is lost.                                                                                                                        |
| ⛔ Factory service/test menu (keyboard notes held during power-on)         | Contains a RAM DEVICE TEST that **writes to every byte of the battery-backed user SRAM** (it restores each byte, but it is still a write pass over your panel memories), and an FD SAVE/LOAD TEST that writes to whatever floppy is in the drive. |
| ✅ SOUND GROUP `[PIANO]` + `[GUITAR]` + `[MALLET & ORCH PERC]` at power-on | Read-only version display, bottom right. Safe.                                                                                                                                                                                                    |

These come from the vendor documentation shipped with the update disks and from
the service manual, **not** from emulation: no power-on combination has been
executed in MAME, and none should be attempted on an instrument holding an
unpreserved image. Do not confuse any of them with the runtime chord on this
page, which touches nothing.

> **Where the flash updater lives is unresolved** — see
> [Where does the flash updater live?]({{ site.baseurl }}/kn7000-firmware-security/#45-where-does-the-flash-updater-live-unresolved).
> Two things it is *not*: a string sweep finding no KN5000-style "Flash Memory
> Update" text proves nothing, because the updater's UI is *bitmaps* — those ASCII
> strings are absent from a genuine KN5000 dump too; and it is not in the top
> `0x90FF` of the program flash: on the owner's build-893 unit everything from
> `0x487F55CF` up reads as one unbroken block of `0xFF`.
>
> Not knowing where it lives does not make the combinations in this table any less
> destructive. The update path demonstrably runs.

## Caveats

- **THE VERSION GAP IS THE MAIN CAVEAT.** Everything here was derived from PROGRAM 941 / TABLE 84 and driven in MAME. Many instruments — including the project owner's — run something else. Three elements are corroborated on real 893 hardware (the chord dispatcher via the `0xA1` SOFT VERSION case, the viewer's four default address slots, and the release byte `0x13` at `0x4840000F`); the rest is expected-by-inheritance, not measured there.
- The compare is an equality, so the chord is brittle by design: `0x99` and only `0x99`. A single extra both-held column kills it. This was measured (`0x9B` → nothing), and it is the most likely reason for a failed attempt.
- **The KN5000 chord does not work here, and that is not a bug.** Columns 1+5+8 give `0x91`, the KN5000's Panel Simulator constant. The KN7000 dispatcher has no case for `0x91`; it falls through and returns. Reproduced in the emulator: the accumulator reached exactly `0x00000091` — the instrument *saw* the input — and the screen never changed. Wrong constant for this firmware; not timing, not panel mapping, not an absent screen.
- The dispatcher is complete and that is provable, not assumed. A byte scan for the absolute address of the both-held accumulator (`0x50021FE0`) finds exactly five references in the whole 4 MB image: the three in the block below, plus two resets at `0x48414C05` and `0x48414CA8`. **There is no second comparison site anywhere**, so `0x99`, `0xA1` and `0x110000` are the only chords this handler implements.
- Not every chord has been swept behaviourally. All 56 three-column combinations over columns 1..8 *were* swept, with exactly one positive (`0xA1`). Four-column chords were not exhaustively swept — only `0x99` positive and `0x9B` negative. The disassembly closes the gap, but as a completeness statement this rests on the ROM scan rather than on measurement.
- **The `0x110000` capture chord is the four corner soft keys.** Bits 16 and 20 of the held-switch accumulator are index switches `0x10` and `0x14`, produced only by LCDL1 and LCDL5 (the DOWN half) and LCDR1 and LCDR5 (the UP half); the names come from the firmware's own edit-switch table at `0x485B0C68`. Settled 2026-10-18 from the code and in MAME; see [LCD capture](#lcd-capture).
- ADR3's target (the 11-entry table of `0x8E0`-byte records at `0x501A5800`) is **plausibly** the sequencer song slots — the bound is 11, the manual says `10 SONG MAX.`, and a sequencer initialiser is one of its callers — but nothing names it, so treat the identification as unproven.
- The viewer keeps repainting while it is open (measured in the emulator: about every 3 s when idle), so a parked address is re-read over and over. That is harmless in ROM and RAM and is **not** harmless over I/O. Keep it in `0x48000000`–`0x487FFFFF` or `0x50000000`+ / `0x84000000`+, and stay off the flash command window, the TG/FDC window, the DSP port, the SD interface and CPU-internal I/O including the MIDI transmitter. FULLTIME makes this worse, not better.
- RHYTHM and PICTURE read 0 in the emulator because those two devices have never been dumped and upstream MAME declares both `NO_DUMP` and maps neither (the kn7000_mame overlay substitutes a synthetic stand-in for the rhythm resource). **Any RHYTHM or PICTURE number seen in emulation is an artefact.** On real hardware those two rows show numbers this project holds from no source at all, which makes them worth photographing.
- The service manual documents no memory-dump screen. Its diagnostics are power-on combinations and jig-based device tests. The chord on this page is firmware-proven and manual-silent.
- No photograph of a KN7000 MEMORY DUMP screen exists in this repository yet — neither from the emulator nor from hardware. The KN5000 page has screenshots; this one does not, and should get them.

## Where it lives in the ROM

All addresses are MN10300 CPU addresses; program-flash file offset = CPU
address − `0x48400000`. A byte-exact, fully annotated disassembly of everything
described here — the dispatcher, the gate, all ten event handlers of the viewer
and its static data — is committed in the
[`kn7000_disassembly` reconstruction project]({{ site.baseurl }}/kn7000-firmware/)
as `disasm/debugger_memdump.asm`, where a checker re-reads every byte column out
of the ROM and re-encodes every mnemonic with the project's own MN10300 encoder.

The balance-button ("index switch") handler at `0x48414735` maintains two
32-bit held-masks and their intersection. Bit *N* of each word is **column
*N*+1**: the index→mask table at `0x4859E1A0` is a plain `1 << N` (entries 0..11
read `1, 2, 4, 8, 10, 20, 40, 80, 100, 200, 400, 800`).

| Cell         | Meaning                                                             |
|--------------|---------------------------------------------------------------------|
| `0x50021FD8` | columns whose **UP** cap is currently held (panel event `0x702001`) |
| `0x50021FDC` | columns whose **DOWN** cap is currently held (event `0x702000`)     |
| `0x50021FE0` | `FD8 & FDC` — columns with **both** caps held                       |

```
48414842: fc a6 e0 1f 02 50   mov  (0x50021fe0), d2
48414848: fc a4 dc 1f 02 50   mov  (0x50021fdc), d0
4841484e: fc a5 d8 1f 02 50   mov  (0x50021fd8), d1
48414856: f2 01               and  d0, d1
48414858: fc 85 e0 1f 02 50   mov  d1, (0x50021fe0)
```

The dispatcher at `0x484148C0` tests exactly three constants and nothing else:

```
484148c0: fc a4 e0 1f 02 50   mov  (0x50021fe0), d0
484148c6: fa c8 99 00         cmp  0x99, d0
484148ca: c8 12               beq  0x484148dc        ; gate -> _TT_MEMDUMP (0xF2)
484148cc: fa c8 a1 00         cmp  0xa1, d0
484148d0: c8 49               beq  0x48414919        ;         _TT_SOFTVER (0xF0)
484148d2: fc c8 00 00 11 00   cmp  0x110000, d0
484148d8: c8 4e               beq  0x48414926        ; gate -> LCD capture
484148da: ca 5f               bra  0x48414939        ; anything else: return
```

| Accumulator  | Held-switch bits                                                           | Result                                                                      |
|--------------|----------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| `0x000000A1` | columns 1, 6, 8                                                            | SOFT VERSION — ungated                                                      |
| `0x00000099` | **columns 1, 4, 5, 8**                                                     | **MEMORY DUMP** — gated on `0x4840000F` ≠ `0xFF`                            |
| `0x00110000` | bits 16 and 20: the four corner LCD soft keys (LCDL1, LCDL5, LCDR1, LCDR5) | LCD capture to `LCDCAP%02d.BMP` — gated inversely, on `0x4840000F` = `0xFF` |

The viewer itself is `DbMemoryDumpProc` at `0x484878AC`. It dispatches through
an open-addressed table of sixteen 8-byte `{key, handler}` slots at
`0x485D6830`, keyed on `event − 0x50000`; ten slots are populated and everything
else falls through to the base class. Using the firmware's own event names —
recovered from a 260-entry name list at `0x485B25FC` with an index-parallel
pointer array at `0x48726BF0` — the ten are `EV_SHOW`, `EV_HIDE`, `MT_Draw`,
`MT_SeleDraw`, `MT_ParaDraw`, `EV_IAMSELECTED`, `EV_INDEXSW_UP`,
`EV_INDEXSW_DOWN`, `EV_MEMDUMP` and `MT_GetColor`.

Its step handler is at `0x48487E60`: it takes a control index *i*, and for
*i* ∈ 0..7 applies `± (1 << (4i))` to the currently selected address slot —

```
48487e60: 5e 9c               mov   (0x9c, sp), a2     ; control index
48487e62: ba 07               cmp   7, a2
48487e64: c5 7a               bhi   0x48487ede         ; > 7 -> colour / slot controls
48487e66: f1 d8               mov   a2, d0
48487e68: 54                  asl2  d0                 ; d0 = 4i
48487e69: 8f 01               mov   1, d3
48487e6b: f2 93               asl   d0, d3             ; d3 = 1 << 4i
```

— then clamps:

```
48487ea6: fc c8 00 00 00 c0   cmp   0xc0000000, d0
48487eac: c4 0f               bcs   0x48487ebb
48487eb3: fc e0 ff ff ff 0f   and   0x0fffffff, d0
```

Its strings, for anyone confirming this in another image: `MEMORY DUMP` at
`0x485D5D34` (and again, inline in the screen's own resource record, at
`0x485D5F28`); the caption ` DUMP ADR%d = %04X%04X  ` at `0x485D6780`; the
colour legend ` %s = %02X  ` at `0x485D6764` with its disabled form ` %s = XX  `
at `0x485D6774` and the four labels `Aqua` / `Yellow` / `Lime` / `Fuchsia` at
`0x485D6738`..`0x485D6749`; `FULLTIME` at `0x485D5F9C`; `DEBUG MODE :` at
`0x485D5CD0`; `SOFTWARE VERSION ---` at `0x485D5DA0`; `DEBUG TOOLS` at
`0x485D5B88`; `Panel Simulator 2.1` at `0x485B52D0`; `LCDCAP%02d.BMP` at
`0x4859E2E4` and `LCDBOX%02d.BMP` at `0x4859E334`. The firmware's own developer
symbol strings `_TT_MEMDUMP`, `_TT_SOFTVER` and `_TT_DEBUG` survive in the image
at `0x485AFA4B`, `0x485AFA36` and `0x485AFAD8`.

## Related

- [SOFT VERSION Screen — and an unpreserved KN7000 firmware]({{ site.baseurl }}/kn7000-soft-version/) — the zero-risk chord, and why PROGRAM 893 matters
- [Recovering build 893]({{ site.baseurl }}/kn7000-build-893-recovery/) — 9,472 bytes read off this screen by hand, and what they say about how 893 and 941 differ
- [Reading ROM out of the screen]({{ site.baseurl }}/kn7000-rom-from-the-screen/) — turning a video capture of this screen back into bytes
- [Firmware Robustness & ROM Archival]({{ site.baseurl }}/kn7000-firmware-security/) — why the instrument cannot hand over its own bytes
- [Program-ROM Clip Read (IC16/IC17)]({{ site.baseurl }}/kn7000-program-rom-clip-read/) — the route that actually captures a build
- [Control Panel Protocol]({{ site.baseurl }}/kn7000-control-panel/) — the part-mixer buttons and their event codes
- [Expansion Bus & Wave-ROM Dump]({{ site.baseurl }}/kn7000-expansion-and-wave-dump/) — the wave ROMs this screen cannot see
- [The KN5000's MEMORY DUMP screen]({{ site.baseurl }}/memory-dump-screen/) — the same idea on the older instrument, with a different chord and a different constant
