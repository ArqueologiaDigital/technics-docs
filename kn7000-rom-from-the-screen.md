---
layout: page
title: "Reading ROM out of the screen (dumpgrab)"
permalink: /kn7000-rom-from-the-screen/
---

# Reading ROM out of the screen

The KN7000 will not dump itself — no diagnostic emits flash bytes to MIDI, to
disk or to a serial port, and the update path is write-only (see
[Firmware Robustness & ROM Archival]({{ site.baseurl }}/kn7000-firmware-security/)).
But it will *display* any address it can reach, 256 bytes at a time, on the
[hidden MEMORY DUMP screen]({{ site.baseurl }}/kn7000-memory-dump-screen/) — and
it has a composite **VIDEO OUT** jack on the back.

So: point the video output at a capture card, hold down the page button, and the
instrument reads its own flash out loud for about fifty minutes per 4 MB chip.
**`dumpgrab`** is the tool that turns that video back into bytes.

> **Why bother.** The target is
> [PROGRAM 893]({{ site.baseurl }}/kn7000-build-893-recovery/), an unpreserved
> firmware for which **no oracle exists**. Nothing in this pipeline is allowed to
> depend on already knowing the answer: the character atlas can be built from the
> screen itself, and every result is gated on redundancy the screen *carries*
> (the 16-row address ladder, the colour legend), never on a reference ROM.

Where it lives: `kn7000_mame/tools/dumpgrab/` (commits `74a3457`, and `bf5e97f`
for the real-capture work in progress). The side quest that produced it is
deliberately still filed under `pending/` (in the KN7000 repository's
`side-quests/`), because it has not yet recovered a byte from a real instrument:
every real composite frame tried so far (§6) is refused.

## 1. What the screen gives you for free

Two redundancies, both printed on every page, and both exploited:

- **The address ladder.** Each of the 16 rows prints its own full 32-bit address,
  and they must ascend by exactly `0x10`. That makes the page's base address a
  **16-way vote**, and a disagreeing row localises a failure to that row.
- **The colour legend.** The viewer highlights any cell whose value matches one of
  four legend bytes. The legend is **read off the screen**, not assumed, because
  those four bytes can be stepped from the panel at run time.

There is a third and it is not used yet: the viewer prints every byte a **second
time as ASCII**, to the right of the hex. That is a fully independent encoding of
the same byte at a different screen position, and it is the single most valuable
unimplemented feature in the tool (§5).

## 2. Measured accuracy — on emulator frames

Everything in this section was measured on 2026-08-09 against
`kn7000_program.rom`, byte for byte. **These are emulator numbers.** MAME hands
the extractor a pixel-exact framebuffer, so they measure the extractor and the
voter, *not* an analog capture chain.

| Run | Range | Source | Frames | Pages | Bytes known | Wrong | **Byte accuracy** | Perfect pages |
|---|---|---|---|---|---|---|---|---|
| capture 3, `video` | `0x48400000` | `movie.avi` | 828 | 41 | 10,496 (100 % of the sweep) | 14 | **99.866616 %** | 40 / 41 |
| capture 1, `video` | `0x48400000` | `movie.avi` | 555 | 41 | 10,495 | 16 | **99.847546 %** | 40 / 41 |
| capture 1, `frames` | `0x48400000` | 1,108 PNGs | 1,108 | 41 | 10,495 | 16 | **99.847546 %** | 40 / 41 |
| capture 2, `video` | `0x48410000` | `movie.avi` | 822 | 41 | 10,491 | 63 | **99.399485 %** | 38 / 41 |
| one still, `image` | `0x48736300` | 1 PNG | 1 | 1 | 256 | 0 | **100.000000 %** | 1 / 1 |

So: **99.87 % end to end over a 40-page sweep, and 100.00 % on a single still.**

The video and frames modes of capture 1 produced **byte-identical** output through
two completely different input paths (an ffmpeg rawvideo pipe versus Pillow),
which is the cross-check that says the two readers agree with each other.

**A hole is never quietly filled.** Every output carries a mask — one byte per
byte, `0` for never recovered, otherwise the number of frame votes — plus a
coverage report listing the exact holes to re-sweep. A gap can be re-swept in
thirty seconds; an invented byte can never be found again.

### The gate that makes those numbers mean anything

A misplaced grid does not produce obvious garbage — it produces **confident
nonsense**. On a badly framed corpus, **26 % of the bytes scoring above
confidence 0.9 were wrong.** The pipeline therefore refuses any frame whose own
printed addresses do not hang together (at least 12 of the 16 rows must agree on
one page base, counting a two-base split exactly one page apart, which is what a
mid-repaint frame looks like), and zeroes its confidences so a caller that ignores
the refusal still cannot be poisoned.

**Gate on the grid, weight by confidence, abstain per cell.** Three calibration
decisions behind that rule are measured rather than guessed, and each cost a full
re-run:

- **Do not gate on "every cell readable."** That test threw away 192 of 555 frames
  and lost one page entirely, where letting the single unreadable cell abstain
  recovers the other 255 bytes.
- **An unsettled frame votes at half weight.** Measured on the 555-frame sweep:
  214 wrong bytes at full weight, 201 at 0.5, 200 at 0.15 — a small effect,
  because those errors live on pages that *only* unsettled frames ever saw.
- **A claimed tear must be exactly one page wide.** Accepting any multiple of
  `0x100` once let misread address digits file **196 fabricated bytes** at
  `0x48402B00`, three pages past where the sweep ever went — 185 of that run's 201
  wrong bytes were that one invented page.

## 3. Record uncompressed

The most actionable operational finding, and the one that costs nothing to act on.

Cross-frame voting removes *independent* errors geometrically. Measured on an
H.264-medium corpus (500 frames, 42 pages), letting K frames vote per page:

| K frames voting | 1 | 2 | 3 | 5 | 8 | all |
|---|---|---|---|---|---|---|
| wrong bytes | 1,279 | 697 | 494 | 312 | 261 | **246** |
| accuracy | 88.10 % | 93.52 % | 95.41 % | 97.10 % | 97.57 % | **97.71 %** |

Most of the win arrives by K = 5, and the curve then **flattens onto a systematic
residual that no number of extra frames can remove**. The same pipeline on the
uncompressed corpus runs from 318 wrong bytes at K = 1 down to **22 at K = all —
97.11 % → 99.80 %**.

> **Compression destroys glyph detail in a way voting cannot recover.** Capture
> lossless (FFV1 in Matroska, or whatever raw format the grabber natively emits)
> at least for every calibration clip. For long production sweeps, transcode
> afterwards; budget 1–5 GB per 4 MB chip.

A second geometry-level finding from the same study: a **720×480 grab must be
resized to 640×480 before decoding** — measured **72.45 %** as-is versus
**99.17 %** after the resize. Non-square pixels wreck the character pitch, and a
few percent of pitch error is three characters of drift by the right-hand end of a
75-character row.

## 4. The firmware's repaint is not atomic — and that is not tearing

This is a property of the KN7000, measured on pixel-exact emulator frames, and it
would corrupt a naive one-frame-per-page grab no matter how good the capture chain
is.

**The viewer repaints its 16 rows across several video frames.** A frame grabbed
during a page flip therefore contains rows from two different pages, and the mix
is **interleaved by row**, not a top/bottom split. A real example — the row
addresses of one recorded frame:

```
48400100  48400010  48400120  48400030  48400140  48400050 ...
```

A single-split model cannot even express that, which is why the detector was
rebuilt around per-row page voting instead.

**How often.** Roughly a third of the frames of a held-button sweep are flagged as
damaged, and the exact share depends on the run:

| Run | Frames | Flagged damaged | Breakdown |
|---|---|---|---|
| 555-frame sweep | 555 | **162 (29.2 %)** | 66 genuine two-page mixes, 74 with too many half-drawn glyphs, 20 with no usable address ladder |
| 25-second sweep | 1,501 | **510 (34 %)** | 283 (55 %) salvaged by per-row page assignment |

**It is handled rather than discarded**, because every row states its own address:
each row is simply filed under the page *it* names. Measured salvage: 73,328 cells
filed from torn frames, 72,896 byte-exact = **99.41 %**. The tear detectors
themselves measure **0.00 % false positives** on 271 verified-clean frames and
97.5 – 100 % detection across four synthetic tear types.

> ⚠ **Do not confuse this with analog tearing.** MAME emits pixel-exact frames, so
> nothing in this work has ever seen field interlace, chroma smear, scaler
> ringing, ADC phase jitter or a dropped frame. The firmware's repaint is measured;
> the capture chain's behaviour is **unassessed**.

**Repaint timing**, which the capture harness depends on: the *idle* repaint
period is **~2,952 ms** (~0.34 Hz) with the 16-row repaint itself taking ~112 ms.
A parked address is therefore re-read about three times a minute, not many times a
second. The viewer does repaint on its own, but slowly. The practical consequence
is that after dialling an
address the panel is still being painted for up to ~3 s, so a recording that starts
immediately can never catch its start page settled.

**Sweep rate**, holding the orange page rocker (`PART MUTE UP 6`): 40 pages in 464
and 461 frames at 60 Hz = **5.17 – 5.21 pages/s** on the integrated harness, and
~5.4 pages/s on a separate 12-second run. A 4 MB chip is 16,384 pages ≈ **50–53
minutes** of continuous holding. Frames per page: minimum 8, median 11.

## 5. The error class that survives everything

40 of 41 pages come out 256/256; the errors are never spread out. Two causes, and
the second is the one that matters:

1. **A page that was never shown settled** — the auto-repeat interval occasionally
   dips below the repaint time. Two independent passes fix this class.
2. ★ **A page the extractor reads wrong the same way every time.** On one page,
   three *pixel-identical*, fully settled frames (16/16 rows on the ladder, zero
   low-confidence cells) each decode **24 bytes wrong**: `0`→`3`, `F`→`A`, `C`→`D`
   in the right-hand columns, `0`→`C`, `8`→`B` in the bottom rows. This is a
   sub-pixel grid residual biting on exactly the glyph pairs that differ by one
   column of pixels.

Class 2 is **deterministic**, so cross-frame voting cannot touch it, posterior
gating cannot touch it, and — measured, not assumed — **two independent sweeps
mostly cannot either**: merging two passes over the same range dropped only 2
conflicting bytes and left 14 of 16 errors in place, because both passes made the
same mistake on the same page.

```
dumpgrab.py agree --dir pass1 --dir pass2 --out merged
-> agreed bytes 10,493   conflicts dropped 2   accuracy 99.8666 %
```

That is why the honest headline is 99.87 % and not 100 %. Two defences remain
untried: **decoding the ASCII column** as an independent channel, and sweeping in
the **opposite direction** (`DOWN 6`), which is the one variant that might
decorrelate a grid-phase error.

There is **no checksum anywhere in this loop** — the service ROM test reports
PASS/FAIL, not a value. With no oracle, verification has to come from agreement
between independent readings.

## 6. The batch tool refuses every real capture — correctly

The refusal is the correct behaviour, and it is what motivated the live camera
reader in [§7](#7-the-answer-was-a-camera-and-an-operator-kn7000live).

The shipped `dumpgrab.py` **declines every real composite frame tried to date**:
on the best of them it recovers only 4 of the 16 address rows and puts 237 of 256
cells below the confidence floor, so it emits **zero bytes** rather than inventing
any. The atlas is trained on 640×240 emulator output; a real capture is a
different sampling of a different signal.

Phone photographs fail the same way and for the same reason — geometry, not OCR.
An experimental global pitch search lifts one photo from mean confidence 0.078 and
zero usable bytes to 0.509 and **130 of 256 bytes correct** at pitch scale 1.04,
and finds nothing at all on another. A hand-held shot of a curved LCD needs a real
four-corner homography, not a better one-dimensional search.

### Where the loss actually happens

Measured on the same screen through two paths, in units of *native LCD pixels*
so that captures at different resolutions compare directly:

| Path | Sampling (px per native px) | MTF at 3 px | MTF at 2 px | Noise floor |
|---|---|---|---|---|
| emulator framebuffer (ceiling) | 0.99 × 1.01 | **3.255** | above Nyquist | 0.000 |
| real composite capture | 1.61 × 2.06 | **0.245** | **0.008** | 0.015 |

The composite path keeps **7.5 %** of the three-native-pixel contrast, and at the
two-native-pixel period it measures 0.008 — *below its own 0.015 noise floor*. The
intra-glyph stroke information is **absent, not merely attenuated**. A 5×7 font
with one-pixel strokes cannot survive that, which is why the capture end now
matters more than the decoder end.

The hardware explains it. Composite leaves IC104 (`C0HBA0000117`, the colour LCD
controller) from the **GREEN** DAC, through an emitter follower, a 150 Ω resistor,
a ferrite and clamp diodes, straight to the jack — **there is no low-pass filter in
the instrument**, so all band-limiting happens inside IC104 and inside the capture
device. The chip's RED, BLUE and separate-sync outputs are **not connected**: there
is no better video connector to find.

### NTSC beats PAL on this instrument — measured

CUSTOMIZE → VIDEO OUT MODE SETTING is one bit in one register (the firmware stores
`value & 1` at `0x500D35B2` and a library routine copies two bytes of it to the LCD
controller; nothing else in the firmware differs between the two modes). The
question was which produces a bigger, crisper picture for the grabber.

**NTSC**, and not marginally: same page, same VLC snapshot path, same 720×576
frame, the **NTSC panel measures 539 px wide against PAL's 433 px**. The KN7000
centres its picture inside PAL's taller raster instead of using the extra lines, so
PAL spends its resolution on borders.

> Two plausible predictions fail here. PAL does **not** win on line count, and the
> difference is **not** an artefact of grabber resolution — a measurement that
> suggests it is has usually been confounded by a hand-drawn capture rectangle.
> Take **native VLC snapshots, not hand-cropped preview grabs**; the margin is
> large.

### The calibration page

Real-capture work is scored against a page whose contents are already known:
table page **`0x48019000`**, captured in both modes
(`real-NTSC-48019000.png`, `real-PAL-48019000.png` in the tool directory), with
**all 256 bytes verified row-by-row against the archived ROM**.

> ⚠ **That page is 71 % the single byte `0x77`.** A decoder that always guesses
> `77` scores 71 % and is useless. **Always report accuracy twice**: overall, and
> over the 75 non-`0x77` cells. Conveniently, `0x77` is ASCII `'w'`, so the hex and
> ASCII columns are independently checkable there.

## 7. The answer was a camera and an operator (`kn7000live`)

Section 6 says the composite path loses the information and a hand-held photograph
needs a real four-corner homography. Both of those point the same way, and
`kn7000_mame/tools/dumpgrab/kn7000live/` is what they point at: **a camera aimed at
the instrument's own LCD, decoding continuously, with the operator in the loop.**
An optical path is not band-limited the way the composite chain is; the font is
5×7 pixels, so all that matters is how many camera pixels land on a character.

    python3 -m kn7000live live --source v4l2:/dev/video0 --store ~/kn7000-dump \
                               --seed-address 48019000

Committed bytes turn green on top of the video and are never read again; a page is
finished when the block is green; everything lands in a store keyed by absolute CPU
address, with an append-only journal, so a sweep accumulates across sessions.

**Why the batch decoder could not simply be reused.** Its blind grid fit assumes the
panel fills the frame. Measured, it lands off the text on every real capture, and
the emulator-trained atlas decodes 31 % of a page whose answer is known. So the
registration here is four draggable corners plus a homography re-solved every frame
(the camera is hand-held: an affine correction cannot follow a changing perspective),
and the templates are learned live from the address ladder, through the operator's
own blur.

### Four gates, and why each exists

| Gate | What it catches |
|---|---|
| the 16-row address ladder | a grid slipped by a character, a smeared frame, a half-drawn repaint |
| far-right match strength | the ladder is the left eighth of the block and cannot see the far end sliding off |
| a re-read at a **displaced** grid | a fraction-of-a-cell error, which voting cannot see |
| the viewer's **colour legend** | `F0`/`F7`/`FF`, stated a second time in a channel the glyph classifier cannot influence |

The third and fourth are the ones worth remembering, because each was added after a
measured failure rather than designed in.

**Cross-frame voting protects against noise, not against a misplaced grid.** A grid
a fraction of a cell out of place yields the *same* wrong answer in every frame, at
high confidence: the wrongly-committed bytes scored a mean 0.91 against 0.99 for the
correct ones, and raising the confidence threshold from 0.02 to 0.08 removed one
wrong byte at the cost of eleven right ones. A warm-up (commit nothing until the fit
has been complete for several consecutive frames) plus the jitter re-read fixed it.

**Training on committed bytes is a feedback loop with no brake.** Committed bytes are
a far better balanced teacher than the address column — which supplies `B`, `E` and
`F` once per frame against 657 samples of `0` — but a byte committed wrongly becomes
a labelled example of the wrong glyph, and the template drifts towards it. One `F`/`E`
confusion grew until a page of erased flash read as **88 bytes of `EE`**. Erased flash
is the worst case by construction: a run of `FF` is a long run of identical characters
(where a whole-cell shift is invisible even to the jitter check), the least
naturally-trained class, and a pair differing by one stroke of a 5×7 font. A committed
byte may now teach only if the colour channel or the current frame still agrees with
it; 92 wrong bytes on a three-page run became 18, with the well-resolved page at
200/200 and none wrong.

### Measured

Calibration page, 60 frames a page, 12 camera pixels per character, corners placed
1.5 px out:

| Condition | Committed | **Wrong** |
|---|---|---|
| camera still | 215/256 | **0** |
| hand movement | 171/256 | **0** |
| heavier movement, 12° tilt, 9 px/char, 2× blur, or 3× noise | 0 | **0** |

Five of the seven conditions commit nothing, and none commits a wrong byte. That is
the deliberate trade. A decoder that trains on its own output will commit 150–180
bytes in four of those conditions instead; this one refuses, because coverage is
recoverable — the store accumulates — and a wrong byte is not.

On the real composite frame of §6 the tool commits **0 bytes and gets 0 wrong**.

### Operating notes

- **Take your time aiming.** Until a lit, text-covered region is in view the tool does
  nothing but look for one (3 ms a frame) and says so. Getting that check right needed
  a correction: judged at 1/8 scale a six-pixel character is gone and only sensor noise
  is left, so the first version found a photograph of a wall interesting and made
  everything *slower*. It now judges **anisotropy** at half resolution — hex digits are
  mostly vertical strokes, walls and noise are isotropic.
- **Brace the camera** if you can, and frame the 57-character block to span at least
  ~500 px. Those two things separate the first row of the table from the third.
- **Tap the page rocker, do not hold it.** A page needs two to three seconds to fill;
  auto-repeat runs at ~5.4 pages/s, some fifty times too fast.
- **Sweep twice into two stores and diff them** for anything that matters. Every commit
  is journalled with the evidence behind it.

## 8. Standing rule for this work

> **No model reads images.** The image-analysis loop was stopped on 2026-08-10
> because it burned tokens far out of proportion to what it produced. All further
> work on this pipeline happens as **code run locally that prints numbers**; images
> are opened by `cv2`/`PIL` inside the scripts. If a decision genuinely needs an
> eye, the script writes a PNG and a human looks at it.

The salvaged real-capture code is under `tools/dumpgrab/wip-real/`, organised as
four lines of attack: sub-pixel geometry and PSF estimation, decoding in the
*blurred* domain (templates convolved with the measured PSF, whole rows fitted
jointly), the ASCII column as a second channel, and the capture side itself. Only
the last of the four reported before the stop; the rest is unreviewed code of
unknown quality and should be treated as raw material, not as a result.

## 9. What is still unknown

- **The analog chain is unassessed.** The only prediction available is a
  degradation *simulation* whose fidelity is unverified, and two of whose axes are
  documented as misbehaving. Its one honest use is *after* the first real capture:
  decode a page the ROM covers, score it, and see where it lands.
- **The ASCII column is not read.** The one defence against the deterministic error
  class of §5.
- **Photo mode needs a homography**, not a pitch search.
- **Throughput is about 1.4 kB/s** of ROM, and extraction runs at roughly 0.5–2 s
  per frame single-threaded, so an hour-long sweep costs several hours of
  processing. This is an archival method for a handful of chips, not a bulk one.
- **The wave ROMs are out of reach this way.** They are only readable through the
  tone generator's page/offset/data window, not by a plain load, so the viewer
  cannot see them — likewise the SD sub-CPU, the two panel MCUs and the USB co-processor.
  See [Expansion Bus & Wave-ROM Dump]({{ site.baseurl }}/kn7000-expansion-and-wave-dump/).

## Provenance

| Claim                                                                              | How it was checked                                                                                                                              |
|------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| Accuracy table, `agree` result, deterministic 24-byte page                         | measured end to end on this machine on 2026-08-09 against `kn7000_program.rom`; recorded in `tools/dumpgrab/README.md`                          |
| Voting curve, uncompressed vs H.264, 72.45 % / 99.17 % resize                      | measured in the video-pipeline and extractor work packages; the curve is over a 500-frame / 42-page corpus                                      |
| 29.2 % and 34 % damaged-frame shares; salvage 99.41 %; 0.00 % tear false positives | two separate emulator sweeps; recorded in `notes/FINDINGS-kn7000-debug-screens.md` §10 and the side-quest findings                              |
| Repaint period ~2,952 ms; sweep 5.17–5.21 pages/s                                  | `tools/dumpgrab/capture/measure_repaint_idle.lua` and the capture harness's own `SWEEP hold:` log lines                                         |
| MTF / sampling / noise-floor table                                                 | `wip-real/r4-capture-side/score_capture.py`, same screen through two paths                                                                      |
| NTSC 539 px vs PAL 433 px                                                          | same page, same VLC snapshot path, same 720×576 frame                                                                                           |
| Video-out circuit, unconnected RGB/sync pins                                       | SX-KN7000 service-manual schematic                                                                                                              |
| PAL/NTSC is one bit                                                                | firmware: `0x500D35B2`, the two-byte copy to the LCD-controller register, and the 26-word defaults table                                        |
| Refusal on real frames (4/16 rows, 237/256 cells)                                  | the shipped tool run against `real-NTSC-48019000.png`                                                                                           |
| Calibration page contents                                                          | table page `0x48019000` verified row-by-row against `kn7000_table.rom`                                                                          |
| **No byte has yet been recovered from real hardware**                              | the shipped tool declines every real composite frame tried to date, including `real-NTSC-48019000.png` (§6); the side quest stays in `pending/` |

## Related pages

- [MEMORY DUMP screen]({{ site.baseurl }}/kn7000-memory-dump-screen/) — the screen being read, the chord that opens it, and the page rocker
- [Recovering build 893]({{ site.baseurl }}/kn7000-build-893-recovery/) — the firmware this tool exists to capture
- [SOFT VERSION screen]({{ site.baseurl }}/kn7000-soft-version/) — how to find out which build your instrument runs
- [Firmware Robustness & ROM Archival]({{ site.baseurl }}/kn7000-firmware-security/) — why no firmware-mediated dump exists
- [Program-ROM clip read (IC16/IC17)]({{ site.baseurl }}/kn7000-program-rom-clip-read/) — the hardware alternative
- [ROM Dumping Roadmap]({{ site.baseurl }}/rom-dumping-roadmap/)
