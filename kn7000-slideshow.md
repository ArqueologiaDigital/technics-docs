---
layout: page
title: "KN7000 Slide Shows: .ACT Scripts and FEATURE.PRE"
permalink: /kn7000-slideshow/
---

# KN7000 Slide Shows: `.ACT` scripts and `FEATURE.PRE`

The KN7000 can show pictures that change with the music. The owner's manual calls this the
**Slide Show** (p. 77): PIC points recorded in a sequencer song pick a picture at each
point (pp. 90–91). Behind that feature sit two file types the manual never mentions:

- **`.ACT`**, a small text script with HTML-like tags, saved next to every sequencer song
  (`<song>.SQT` + `<song>.ACT`). It lists the song's pictures and can define numbered
  slides made of pictures, text and screens.
- **`FEATURE.PRE`**, a two-line file on a floppy that adds one "External Demo Song" — a
  song plus its slide show — to the DEMONSTRATION screen.

The same engine, called **SSW** in the firmware (most likely "slide show"; module strings
`TtSswRun`, `TtSswList`, `OTB_SLIDESHOW`), also runs the instrument's built-in feature
demonstrations. It descends from the KN5000's
[presentation system]({{ site.baseurl }}/feature-demo/), whose tags it still understands in
part, but the file formats changed: the KN6000/KN6500 feature-presentation disks published
for the older instruments do not play on a KN7000 as they are.

Everything here was read from PROGRAM 941 (`kn7000_program.rom`) and checked by an
independent re-reading; routine names are those of the
[disassembly]({{ site.baseurl }}/kn7000-firmware/) (`kn7000_manual.sym`, section
"FILES, PICTURES, SLIDE SHOW"). Where a point was also seen running in MAME it says so;
"inferred" marks what was not read directly. The MAME probes are in the kn7000_mame
repository, `tools/slideshow/`.

## Contents

- [Slide shows in a song](#slide-shows-in-a-song)
- [Writing an `.ACT` file](#writing-an-act-file)
- [`FEATURE.PRE`: an external demo song](#featurepre-an-external-demo-song)
- [From a PIC event to the screen](#from-a-pic-event-to-the-screen)
- [The built-in demonstrations](#the-built-in-demonstrations)
- [The KN5000/KN6000 presentations, and why they do not play here](#the-kn5000kn6000-presentations-and-why-they-do-not-play-here)
- [Seen in MAME](#seen-in-mame)
- [Can a presentation operate the instrument?](#can-a-presentation-operate-the-instrument)
- [Limits and error codes](#limits-and-error-codes)
- [Open questions](#open-questions)

## Slide shows in a song

**Pictures.** A song can use two kinds of picture:

- **PRESET** pictures 0–99, stored in the instrument's picture flash at `0x57800000`
  (undumped);
- **USER** pictures 0–29: 30 slots (these are the firmware's internal numbers; whether
  STEP RECORD shows them counting from 1 was not checked), filled with PICTURE LOAD from a floppy or SD card.
  PICTURE LOAD reads `.BMP` or `.JPG` files up to 640 × 480 and `0x4D800` bytes, and cuts
  taller pictures to 640 × 240 (see
  [where the files land]({{ site.baseurl }}/kn7000-work-ram/#where-an-image-file-lands)).
  An imported picture is named `0000BMnn.BMP` or `0000JPnn.JPG` (nn = slot + 1).

**PIC points.** In STEP RECORD, on the control track, a PIC point records PRESET or USER and
a number. In the song data it is the event `0x8A, n & 0x7F, (n >> 7) & 0x3F`, with bit
`0x40` of the third byte set for USER.

**Saving.** A sequencer save also writes `<song>.ACT`, even when the song has no
pictures. A save with no pictures and no loaded script writes exactly these 42 bytes (CR LF line
ends, with an empty line after the header), which the owner's real SD card holds next to
its `01001KN7.SQT`:

```
SSW-ACT-V01

<SLIDESHOW>
</SLIDESHOW>
```

With USER pictures, the instrument writes one `<SSW NO=k IMG="name">` line per filled slot
inside `<SLIDESHOW>`, and saves each picture as a file named after the song: the first two
characters of the song name, the slot number plus one in two digits, then the picture's
name from its fifth character on. For a song `MYSONG` with a JPEG in slot 0 and a BMP in
slot 2: `MY01JP01.JPG` and `MY03BM03.BMP`. If the song was loaded with a script, the instrument
copies everything outside `<SLIDESHOW>` — including an `<ACTION>` section — unchanged, and
writes back the pictures that `<ACTION>` uses under their own names.

**Loading.** Loading `<song>.SQT` from disk or SD card also loads `<song>.ACT`: the script
text, every USER picture it lists, and every picture its slides use. **Every load of a
KN7000 song (`J KD`) first empties the picture pool**, so the 30 USER pictures and all
script pictures are gone whether or not the new song has an `.ACT`. (An old KN6000 `I KD`
song is loaded without looking for an `.ACT`, inferred from the code.) A missing `.ACT` is not an error. A file that
does not start with `SSW-ACT-V01`, or a section without its end tag, makes the whole load
report an error, after the song itself has been read. Missing or oversized pictures inside
a valid script are dropped silently. Loading a song with an `.ACT` and its pictures from
SD, then pressing START/STOP, showed each picture at its PIC point in MAME.

The pictures live in the slide-show pool in work RAM; the
[Work RAM Map]({{ site.baseurl }}/kn7000-work-ram/#where-an-image-file-lands) gives its
addresses.

## Writing an `.ACT` file

### Structure

```
SSW-ACT-V01
<SLIDESHOW>
<SSW NO=0 IMG="MY01JP01.JPG">
</SLIDESHOW>
<ACTION>
<ACT NO=1><CENTER><IMG SRC="TITLE.JPG"></CENTER></ACT>
<ACT NO=2><FONT SIZE=11 COLOR=254>Verse 1</FONT><BR><IMG SRC="PIC02.JPG"></ACT>
</ACTION>
```

- The file must **start** with the 11 bytes `SSW-ACT-V01`: no byte-order mark, no blank
  before it. Anything may follow on the same line.
- `<SLIDESHOW> ... </SLIDESHOW>` is the USER-picture list. The instrument rewrites it on
  every save, and when it loads an `SSW` line it replaces the first four characters of the
  file name with the song-derived prefix described above; leave this section to the
  instrument.
- `<ACTION> ... </ACTION>` holds the **slides**: `<ACT NO=n> ... </ACT>`, n = 0–127.
  The instrument never changes this section.
- Either section may be missing when the file is loaded; a start tag without its end tag
  is an error. But a script without `<SLIDESHOW>` and `</SLIDESHOW>` cannot be **saved**
  with its song: the save fails (`-0xC8`), the `.ACT` is deleted, and in two of the three
  save paths the error also deletes the song file just written (inferred). Always include
  at least an empty `<SLIDESHOW></SLIDESHOW>`.

### Syntax, exactly as the parser reads it

- **Line breaks and TABs are deleted** before the tags are read, so lines join with no
  separator. Put **only spaces** between attributes: `<IMG` + newline + `SRC="A.JPG">`
  becomes `<IMGSRC="A.JPG">`, which draws nothing.
- Tag and attribute names are **case-sensitive** and must follow `<` directly.
- Tags are matched by **prefix**, in table order: `<IMGX>` is read as `IMG`.
- A tag ends at the **first** `>`, so a value cannot contain `>`.
- A value in double quotes loses its first and its last character, so a missing closing
  quote costs the last character. Numbers are read as decimal.
- Unknown tags and attributes are skipped. Every attribute is optional.
- Text between tags is drawn at the text cursor, with word wrap, in the current font.

### Tags

| tag                  | attributes                                                                               | when a slide is shown                                                                                                                                                                                                                                    | when the file is loaded                        |
|----------------------|------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------|
| `ACT` … `/ACT`       | `NO` (0–127), `PAN`                                                                      | starts slide NO: resets text, font and alignment and probably clears the screen (inferred); `/ACT` ends it                                                                                                                                               | registers slide NO                             |
| `PPT` … `/PPT`       | `NO`                                                                                     | an overlay slide: shows what code NO−1 shows (code 1 for NO=0; the last slide number seen if NO is absent), without clearing, then draws its own content over it                                                                                         | registers slide NO                             |
| `IMG`                | `SRC` (also ALT, ALIGN, VSPACE, HSPACE, WIDTH, HEIGHT, LOWSRC, BORDER: accepted, unused) | draws picture SRC at the text cursor; the cursor moves right by its width                                                                                                                                                                                | reads file SRC into the pool (up to 640 × 240) |
| `FONT` … `/FONT`     | `SIZE` 0–12, `COLOR` 0–255                                                               | font and colour, nested up to 8 levels                                                                                                                                                                                                                   | —                                              |
| `CENTER` … `/CENTER` | —                                                                                        | line break and centred text and pictures, nested up to 8 levels                                                                                                                                                                                          | —                                              |
| `BR`                 | —                                                                                        | line break                                                                                                                                                                                                                                               | —                                              |
| `SHOW`               | `OBJ`                                                                                    | paints a GUI object found by name: the lookup (`0x48580EE6`) searches every view slot and sends the object `EV_PAINT` (`0x00050009`); it draws the object but does not make it the active screen (the built-in demos use `fdemo_a1` …; MAME, 2026-10-18) | —                                              |
| `SCORE`              | `SRC`, `BEAT`, `X` (repeated, up to 64), `Y`, `DISP`                                     | draws picture SRC in a 640 × 120 band (even slides top, odd slides bottom) with a ball that moves to X[i] at song position BEAT + i (the position is inferred to count beats); without SRC the band is filled with colour 0xFF                           | reads file SRC                                 |
| `SSW`                | `NO` 0–29, `IMG`                                                                         | draws USER slot NO                                                                                                                                                                                                                                       | loads file IMG into USER slot NO               |
| `HDR`                | `SQT`, `CLASS`, `TITLE`, `POINT`, `TEMPO0`–`TEMPO2`                                      | —                                                                                                                                                                                                                                                        | stored; nothing in the firmware reads it       |
| `DA`                 | `NO` 0–3                                                                                 | sends `MT_SleepMainTask`, sets parameter `0x90600007` to NO with `PutM3Em`, then `MT_WakeUpMainTask`; what the parameter controls is unknown                                                                                                             | —                                              |

FONT `SIZE` 0–12 selects the firmware fonts 5, 7, 8, 9, 3, 0, 1, 4, 2, 6, 1, 10, 11; the
default is font 5 in colour `0xFF`. `PAN` (left over from the KN5000/KN6000, where a
presentation's slides are cued by part 15's pan setting, see
[below](#the-kn5000kn6000-presentations-and-why-they-do-not-play-here)) is written into the same
variable as `NO`, so `PAN` after `NO` in one tag replaces the slide number.
`<PRESENTATION>`, `<SLIDESHOW>` and `<ACTION>` have no handler of their own; there is no
`EXEC`.

Pictures named by `IMG` and `SCORE` are kept as **named images**: up to 64, loaded once
each, looked up by exact name. Use JPEG, or uncompressed BMP with 1, 4 or 8 bits per
pixel, of 1–640 × 1–240 pixels; BMPs are drawn with at most 176 colours (see the
[Display Subsystem]({{ site.baseurl }}/kn7000-display-subsystem/#windows-bmp-files)). A
file the firmware does not recognise as JPEG or BMP — a 24-bit BMP, for example — is still
loaded and uses pool space, but is drawn as a small built-in placeholder 24 pixels wide.
`SCORE` pictures are drawn with the BMP routine, so a BMP is the safe choice there
(inferred).

## `FEATURE.PRE`: an external demo song

`FEATURE.PRE` turns a floppy into a demonstration: inserting it on the DEMONSTRATION screen
loads a song and its slide show and plays it.

**The file** is plain text, two lines:

```
WESERL
WESERBERGLAND
```

- **Line 1** is a base name: its first 8 characters name `WESERL.SQT` (the song) and
  `WESERL.ACT` (the slide show). Everything from the first control character (CR, LF, TAB)
  on is ignored.
- **Line 2** is a title of up to 16 characters, shown on a new button on the
  DEMONSTRATION screen. Without it the button shows the `.SQT` name.
- Nothing else is read: no tags, one song per disk.

**The song** must be a KN7000 sequencer song file, the kind the instrument saves
(signature `J KD`). It plays **song 1** of the file, the first of its ten song records, in
the demo song slot; the user's own songs are not touched. **The `.ACT`** is an ordinary
slide-show script and needs the `SSW-ACT-V01` header; its slides are chosen by the song's
PIC points. Song, script and pictures share an area of `0xC0000` bytes (768 KB) at
`0x502C0000`.

**How to use it:**

1. Put `FEATURE.PRE`, the `.SQT`, the `.ACT` and its pictures in the **root of a floppy**.
   The SD card is not searched.
2. Press **DEMO** and wait on the DEMONSTRATION screen with nothing playing.
3. **Insert the floppy.** The firmware reacts only to the insertion: a disk already in the
   drive, or one inserted on another screen, does nothing.
4. "PLEASE WAIT!" appears, then a button with the title appears at the bottom centre (the
   firmware calls it "External Demo Song"), and the song starts with its pictures. The
   slide-show screen replaces the menu at the first picture.
5. The button plays it again. START/STOP or a held DEMO, which normally play the built-in
   songs in turn, now play only this song.
6. Leaving DEMO forgets the presentation (the code clears it on a DEMO-mode message that is
   inferred to mean entering or leaving DEMO); to play it again, eject and re-insert the
   floppy on the DEMONSTRATION screen.

There are **no error messages.** A missing `.SQT` or `.ACT`, a song that is not `J KD`, or
a script without the header just leaves the button there with nothing playing — and
pressing it then may play whatever an earlier load left in memory. Neither FEATURE.PRE nor
the External Demo Song button is mentioned in the owner's manual.

## From a PIC event to the screen

When the song reaches a PIC point, the firmware turns it into a picture code n (PRESET
codes get `0x8000` added) and, on the screens that allow it, switches to the slide-show
screen (title `0x5F`). There the routine at `0x4858099B` (unnamed in the symbol files)
decides what n shows:

| picture code n                                              | shows                                                                                              |
|-------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| USER 0–29, and that USER slot holds a picture               | the picture, centred (the screen is presumably cleared first, inferred) — this wins over a slide n |
| USER 0–29 with an empty slot, or 30–127, and slide n exists | slide `<ACT NO=n>` (or `<PPT NO=n>`) of the `.ACT`                                                 |
| PRESET 0–99                                                 | preset picture n from the picture flash                                                            |
| anything else                                               | a cleared screen with `NO PICTURE DATA`                                                            |

STEP RECORD caps USER numbers at 29, so slides 30–127 can only be reached by songs whose
data carry larger numbers, or through a `PPT` (which shows code n−1). Picture codes start
at 0 and the KN6000-era scripts number their slides from 1, so with one of those scripts a
PIC point with code 0 shows `NO PICTURE DATA`.

## The built-in demonstrations

The DEMONSTRATION menu's ten items are built-in songs, each with a slide show stored in
ROM (table `0x4867F75C`). Every script is the same template — 32 slides, each a
`<SHOW OBJ="fdemo_x1">` … `<SHOW OBJ="fdemo_x32">` of built-in demo screens — of which only
the screens that exist are used. The demo songs' PIC points pick the slides; in MAME the
OVERTURE song's first two points showed "Welcome to SX-KN7000" and "High Power Speaker
System".

| menu item        | ROM script   | screens                    |
|------------------|--------------|----------------------------|
| OVERTURE         | `0x4867C618` | `fdemo_a1`..: 18 present   |
| SD CARD          | `0x4867CB02` | `fdemo_b1`..: 6            |
| VINTAGE ORGAN    | `0x4867CFEC` | `fdemo_c1`..: 10           |
| SOUND EXCELLENCE | `0x4867D4D6` | `fdemo_d1`..: 16           |
| RHYTHM&STYLE     | `0x4867D9C0` | `fdemo_f1`..: 6            |
| MULTI MEDIA      | `0x4867DEAA` | `fdemo_g1`..: 6            |
| SEQUENCER        | `0x4867E394` | `fdemo_i1`..: 6            |
| NETWORKING       | `0x4867E87E` | `fdemo_h1`..: 8            |
| EASE OF USE      | `0x4867ED68` | `fdemo_j1`..: 7            |
| CUSTOMIZE        | `0x4867F252` | `fdemo_e1`..: 8            |

The picture in the middle of the menu is a six-frame JPEG animation of the instrument
opening (266 × 168, program ROM, table `0x4867C5DC`). The built-in scripts run without the
header check and load no files; the external song is demo song number 13 (`0xD`).

## The KN5000/KN6000 presentations, and why they do not play here

The KN5000 (v10), KN6000 and KN6500 firmware share an older tag set with an `EXEC` tag:
their `FEATURE.PRE` is itself a tagged file,

```
<PRESENTATION>
<EXEC SONG=1 SRC="WESERL" NAME="WESERBERGLAND">
</PRESENTATION>
```

and their `.ACT` starts directly with `<ACTION>`. On the KN6000 the `EXEC` handler stores
a song number, a base name (used for both the `.SQT` and the `.ACT`) and a title, then posts
UI messages (what they trigger was not traced); it executes nothing from the script.

**What cues their slides is part 15's pan.** Track 14 of each CA-6FP song holds nothing but
`B0 0E 0A n`, controller 10 (pan) on part 0x0E, with n stepping through the ACT numbers
(Weserbergland: 1–25, refrains repeated); the KN6000's presentation proc (`0x484CDB31`) matches
that parameter and runs `<ACT NO=n>`. The KN5000's built-in Feature Presentation works the same
way with its own song format ([Feature Demo]({{ site.baseurl }}/feature-demo/#how-the-song-drives-the-presentation)),
and the `<ACT>` parser of both accepts `PAN=Ln`, `PAN=C` or `PAN=Rn` instead of `NO=` so that an
author can key slides to the pan value shown on the panel. The KN7000 moved the cue to its own
PIC event (`0x8A`).

| part                                   | KN5000 / KN6000 / KN6500             | KN7000                            |
|----------------------------------------|--------------------------------------|-----------------------------------|
| `FEATURE.PRE`                          | `<PRESENTATION><EXEC SONG SRC NAME>` | two plain lines: base name, title |
| `.ACT` header                          | none                                 | `SSW-ACT-V01` required            |
| ACT, /ACT, IMG, SHOW, FONT, CENTER, BR | yes                                  | yes (IMG uses only SRC)           |
| EXEC                                   | yes                                  | removed                           |
| SLIDESHOW, SSW, PPT, SCORE, HDR, DA    | no                                   | new                               |
| song file                              | `I KD` (KN6000)                      | `J KD`                            |

The only feature-presentation disks known are four that ca-software.com offered on its
KN6000 download page under "FEATURE PRESENTATIONS (nur KN6000 und KN6500!)": CA-6FP01 *Weserbergland*, CA-6FP02 *Sexy Girls*, CA-6FP03
*Freisprech-Einrichtung (No Handy!)* and CA-6FP04 *Sexy Girls 2 (Let's get back to bed)*
("press DEMO, then insert the disk; loading starts automatically" — the same procedure as
on the KN7000). Each fails on a KN7000 at three points: the tagged `FEATURE.PRE` is read as
base name `<PRESENT` and title `<EXEC SONG=1 SRC` (seen in MAME), the songs are `I KD`
files the demo loader refuses, and the `.ACT` files lack the header.

Converting one is possible in part: rewrite `FEATURE.PRE` as two lines and put
`SSW-ACT-V01` in front of the `.ACT`. The song is the hard part: the KN7000's sequencer can
load an `I KD` song and save it as `J KD` (inferred from the code), but the KN6000 songs
carry no KN7000-style PIC events, and how they selected their slides is not known.

## Seen in MAME

**From the floppy, nothing forced (2026-10-18, afternoon).** Once the driver modelled the
floppy's DMA and its INDEX interrupt ([how a sector moves]({{ site.baseurl }}/kn7000-storage-subsystem/)),
the converted CA-6FP01 disk was simply inserted on the DEMONSTRATION screen: the disk-in event
fired, FEATURE.PRE was found, the song (`0xD7C0` bytes), the script and the 19 pictures loaded
from the drive (about 2 s per picture), the external demo song started at t = 72 s and each
PIC point drew its slide. The run that showed it first, and the procedure the earlier
morning runs needed, are both below.

**The morning runs.** Before that, the KN7000 MAME driver could not read a floppy, so the
disk-change bit was forced to produce the insert event, the two floppy checks were forced,
and the drive byte was set to SD so that the files were read from the SD card. With CA-6FP01
converted as above, and the built-in OVERTURE song repackaged as a `J KD` file to supply
PIC points:

- the DEMONSTRATION screen showed PLEASE WAIT!, then a **WESERBERGLAND** button, and the
  song started;
- all 19 pictures loaded into the demo pool, and each of the song's 18 PIC points showed
  its slide: code 0 `NO PICTURE DATA` (the sample has no slide 0), codes 1–17 the slides
  `<ACT NO=1>` … `<ACT NO=17>`, including the lyric lines the script draws over the
  pictures, centred, in colour 254;
- the KN6000 originals, unconverted, gave the button `<EXEC SONG=1 SRC` and nothing played.

**The KN6000 disks on the KN6000 driver.** The original, unconverted CA-6FP01 now loads on
the emulated KN6000 the way its users loaded it: DEMO, then insert. The DEMONSTRATION screen
gains a **WESERBERGLAND** button (the `NAME` of the `EXEC` tag), the song and the pictures
load from the floppy, and the first slide (`<ACT NO=1>`, "Wo die Weser einen großen Bogen
macht") is drawn. Three conditions: the driver's DMA channel must move exactly one byte per
DRQ up to count + 1 (one byte more corrupted the KN6000's file-system memory), the INDEX
interrupt must be delivered, and the disk image must be laid out like a DOS-formatted floppy.
The `kn6000_flop` software-list image is not: its FAT starts `F0 0F FF` and each FAT has 12
sectors, and the KN6000's media check accepts only `F0 FF FF` / `F9 FF FF` and its file system
expects 9-sector FATs; the same files copied onto a standard image load. (The same holds for
every image in the `kn5000_flop`, `kn6000_flop`, `kn7000_flop` and `wsa1_flop` lists, and the
KN7000's media check rejects them too.) The lists are being rebuilt on blank disks formatted by
each instrument itself; `ca6fp01` built that way loads with no relayout step
([Floppy Disk Images]({{ site.baseurl }}/floppy-disk-images/)).

At first the show then held its first slide: the KN6000's **tempo timer** was not emulated, so
the song never advanced, and a KN6000 slide show follows its song exactly as the KN7000's does.
The KN6000 paces its sequencer with the MN10300's 16-bit timer 6 (compare register `0x340010C4`
= 1,250,000 ÷ BPM, interrupt group 9), not the KN7000's TM5
([tempo clock]({{ site.baseurl }}/kn7000-sequencer/#the-tempo-clock-how-playback-actually-advances)).
With that timer modelled, **all four CA-6FP presentations play, with their songs**:
*Weserbergland* shows the river towns one by one and then the sing-along slides with the
lyrics over the river; *Sexy Girls* and *Let's Get Back to Bed* show their pictures in turn;
*Freisprecheinrichtung* runs its whole story and returns to the DEMONSTRATION menu. So the
`I KD` songs do carry the slide cues, though not as the KN7000's picture events; how they are
encoded was not decoded.

Separately, an ordinary song with an `.ACT` and eight pictures loaded from SD into the main
picture pool and showed them at its PIC points after START/STOP. A 640 × 240 JPEG slide
took 1–2.5 s of emulated time to finish drawing.

## Can a presentation operate the instrument?

Investigated 2026-10-18 (the full answer, with addresses, is in kn7000_disassembly
`notes/presentation-control.md`).

- **What a KN7000 script can put on screen:** pictures, text, and, through `SHOW`, any GUI object
  that exists under that name, painted, not made active. In MAME the built-in demo screens
  (`fdemo_a1` …, view slot 0x29) resolve and draw. Names tried for the debug screens
  (`PPanelSimulator`, `simulator1`, `DbMemoryDump`, `DbVariableMenu`) are class names, not
  objects, and are not found.
- **What its song can change:** besides notes, tempo and PIC points, a song carries parameter
  events filtered by track kind. A CONTROL track can play rhythm, variation, intro, fill, ending,
  start/stop, tempo, transpose, the panel-memory number, TECHNI-CHORD and fade; part tracks voices
  and mixer moves. The open screen redraws to follow (`EV_MMMDATA`), and the recorder captures
  these panel operations, so an automated demo can be recorded on the instrument. A song cannot
  store SysEx, cannot change the global effect types, and nothing in it switches screens.
- **From SD:** `FEATURE.PRE` is read from the floppy only, but a song loaded from the SD card
  brings its `.ACT` and pictures and shows them at its PIC points, `SHOW` slides included.
- **The Panel Simulator, DEBUG TOOLS and LCD capture are out of reach** on PROGRAM 941. The only
  call that enters the Panel Simulator's mode 0, and the only callers of the LCD capture, sit
  behind the panel chord's release-byte gate (`0x4840000F` must be `0xFF`, as in the SP7001 build);
  no slide-show, song, file or MIDI code calls a mode or title change, and the ungated
  `CaptureLcdCheck` has no caller. See [Memory Dump screen]({{ site.baseurl }}/kn7000-memory-dump-screen/).

On the KN5000 the same kind of disk can go further: its presentation shows live screens
(Accordion, Drawbar, Sdmixer) and its song's panel-record writes change their settings while
they are shown ([Feature Demo]({{ site.baseurl }}/feature-demo/#how-the-song-drives-the-presentation)).

## Limits and error codes

| item                     | limit                                                                                             |
|--------------------------|---------------------------------------------------------------------------------------------------|
| slides                   | `NO` 0–127                                                                                        |
| USER pictures            | 30 slots (0–29)                                                                                   |
| named images (IMG/SCORE) | 64; each JPEG, or BMP of 1/4/8 bpp, of 1–640 × 1–240 pixels                                       |
| PRESET pictures          | 0–99                                                                                              |
| song pool                | 606,316 bytes for the script, both sections and all pictures (344,172 with the other board strap) |
| FEATURE area             | 768 KB for the song, the script and its pictures                                                  |
| names                    | 8.3; record names hold 15 characters, longer values overrun fixed buffers                         |
| FONT / CENTER nesting    | 8 levels                                                                                          |

| code    | meaning                                                                                                                                                                                                 |
|---------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-0xC8` | the `.ACT` does not start with `SSW-ACT-V01`, or a section lacks its end tag; on save, a loaded script without `<SLIDESHOW>` / `</SLIDESHOW>`; on PICTURE LOAD, an extension other than `.BMP` / `.JPG` |
| `-0x6B` | out of pool space, or the 64 named images are taken                                                                                                                                                     |
| `-0x6D` | a picture too large                                                                                                                                                                                     |
| `-0x65` | not enough free space on the medium to save the `.ACT` and its pictures                                                                                                                                 |

Inside a script, all picture errors are ignored: the slide simply lacks the picture.

## Open questions

- What `DA`'s parameter controls, what `DISP` does in `SCORE`, and whether `PAN`
  overwriting `NO` is a bug.
- Which screens let a PIC event open the slide show (the firmware lists titles `0x01`,
  `0x03`, `0x81`, `0xAE`, `0xAF`, `0xCF` = DEMONSTRATION, `0x123`, `0x126`–`0x129`); the manual says "the
  normal display or the SEQUENCER PLAY display".
- How a KN6000 `I KD` song encodes its slide cues (the songs do cue them: the presentations
  play in MAME), and what picture-flash entry 0 holds.
- Whether STEP RECORD shows PIC numbers counting from 0 or from 1.
- A browse mode that steps through slides exists in the code, but nothing seems to turn it
  on.

## Related

- [Work RAM Map]({{ site.baseurl }}/kn7000-work-ram/#where-an-image-file-lands) — the picture pool, the FEATURE area and the PICTURE LOAD buffer
- [Sequencer]({{ site.baseurl }}/kn7000-sequencer/) — songs, song memory and the demo songs
- [Display Subsystem]({{ site.baseurl }}/kn7000-display-subsystem/#windows-bmp-files) — how BMP pictures are parsed and drawn
- [Storage & File System]({{ site.baseurl }}/kn7000-storage-subsystem/#the-fmm-file-layer) — the file calls behind every load and save
- [Feature Demo & Presentation System]({{ site.baseurl }}/feature-demo/) — the KN5000 ancestor
