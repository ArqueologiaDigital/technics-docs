---
layout: page
title: "PDF Viewer on the KN7000"
permalink: /kn7000-pdf-viewer/
---

# A PDF viewer on the KN7000

Sheet music in PDF on a stock KN7000's LCD, while the instrument goes on playing:
- the page drawn as wide as the LCD, 16 grays;
- the TEMPO/PROGRAM wheel scrolling it, and on past its end to the next page;
- the keybed and the rest of the panel left to the instrument.

It is a port of **MuPDF 1.1** (Artifex, GPL-3.0), the "lightweight PDF viewer", with FreeType, zlib, libjpeg and
jbig2dec. It is a program of the [program menu]({{ site.baseurl }}/kn7000-cnv-homebrew/) (folder `PDF\`, listed under
Tools as "PDF viewer (MuPDF)"), started from DISK MENU > STYLE CONVERT with the loader `KN7LOAD.CNV`. Its test documents
are a LilyPond score (`Bachianinha_No1_duas_vozes.pdf`, `BACHIANI.PDF` on the card) and the manual of the
[ProTracker port]({{ site.baseurl }}/kn7000-protracker/) (`PROTRACK.PDF`, 15 pages).

Source: `kn5000_homebrew/demos/kn7000_pdf/` (its `README.md` has the details, `notes/UNIT-RUNS.md` every run on the
instrument).

> **Status (2026-11-01): draws pages on the owner's KN7000; the page cache works there.** On the owner's instrument
> (program 893), build 87f01d5:
> - all 5 pages of the score and all 15 of the manual were drawn and saved on the card;
> - opened again, the score showed its first page from the card in 818 ms, the manual in 621 ms.
>
> The builds after 87f01d5 (Type 3 glyph procedures kept, a read cache for the PDF, runs of fills merged, the log saved
> in parts) were checked in MAME on 2026-11-01; `notes/UNIT-RUNS.md` records no run of them on the instrument.
> The road there is in [How it was checked](#how-it-was-checked): the first unit runs hung in FreeType, and the cause
> was the CPU reading a carry flag one instruction late.

## Using it

DISK MENU, STYLE CONVERT, `KN7LOAD.CNV`, OK; then the program menu's "PDF viewer (MuPDF)" row, RUN. The folder's PDFs
are listed; the wheel or UP/DOWN chooses one, OPEN opens it, and its first page is drawn (about 15 s for a page of
music in MAME). The page fills the LCD's width; the LCD shows 240 of its lines at a time.

While the page is read, the next pages are drawn behind it: the next, the one after, the one before. Turning the wheel
past the page's end shows the next page at once when it is drawn already. A page asked for that is not drawn yet is
drawn first, and the page shown can be read and scrolled meanwhile (the status line says "drawing page N..."). Each
page drawn is saved on the card once the controls have been left alone a moment, and the next time the document is
opened its pages come from there in about a second.

| control                    | in the list | on a page                                                                 |
|----------------------------|-------------|---------------------------------------------------------------------------|
| TEMPO/PROGRAM wheel        | the file    | scrolls the page; past its end the next page, past its top the one before |
| PAGE UP, PAGE DOWN         |             | the page before, the page after                                           |
| LCD left 1 (FILES)         |             | back to the list                                                          |
| LCD left 2, 3 (PREV, NEXT) |             | the page before, the page after                                           |
| LCD left 4 (FIRST)         |             | the first page                                                            |
| LCD left 5 (LOG)           | the log     | the log (MuPDF's warnings and errors, the pages' times)                   |
| LCD right 1                | OPEN        | TOP: the page's top                                                       |
| LCD right 2, 3             | UP, DOWN    |                                                                           |
| LCD right 5                |             | END: the page's bottom                                                    |
| EXIT                       |             | back to the list                                                          |
| EXIT held 1.5 s            | the end     | the end                                                                   |

Everything else on the panel does what it always does, and the keybed plays, also while a page is drawn. The tempo
does not change while the wheel scrolls. The status line at the bottom names the file and the page; when memory ran
short while a page was drawn it says so ("it may lack something").

### The card's `PDF\` folder

| file           | what                                                                                                                    |
|----------------|-------------------------------------------------------------------------------------------------------------------------|
| `KN7APP.BIN`   | the platform: firmware search, task, files, the panel shared with the firmware, the frame buffers lent                  |
| `PDF.BIN`      | the viewer: MuPDF 1.1, FreeType, zlib, libjpeg, jbig2dec, and the viewer's own code                                     |
| `MANIFEST.TXT` | the name the program menu shows and its folder (Tools)                                                                  |
| `*.CFF`        | the 14 standard PDF fonts (URW's Nimbus, from MuPDF 1.1), read only by a PDF that does not embed them                   |
| `*.PDF`        | the documents: any PDF copied in, under an 8.3 name                                                                     |
| `K*.PGC`       | the pages drawn, one a file (`Kxxxxnnn.PGC`: xxxx from the document's name and size, nnn the page); they may be deleted |
| `PDFLOG*.TXT`  | the log (below)                                                                                                         |

`tools/card/pgc2png.py -o DIR CARD/PDF` makes a PNG of each `.PGC` on a computer, with Python 3 alone. KN7000's
`update_sdcard.sh` (`tools/sdcard/` in the KN7000 repo) brings the `.PGC` files back from the card and converts them
into `from-card/<date-time>/PDF/png/`.

## How it works

Two programs, as in the Doom and ProTracker ports (`src/common/pfhost.h` is the interface between them):

- **`KN7APP.BIN`** (`src/app/`) is the platform, taken from the Doom port. The loader runs it on each converter call.
  It starts a task for the viewer and serves its file reads. It takes from the firmware only the switches the viewer
  names (the ten soft keys, PAGE UP/DOWN, EXIT) and the wheel, before the firmware decodes them, and leaves the firmware
  everything else. It keeps every switch that went down until the viewer takes it, so a press made while the viewer
  is busy is not lost. It keeps the firmware's drawing off, and it loads `PDF.BIN` in pieces.
- **`PDF.BIN`** (`src/kn7/`, `src/mupdf/`, `src/third/`) is MuPDF 1.1, with its changes behind `#ifdef KN7PDF`, and the
  viewer.

### Memory

`PDF.BIN`'s code and data are 724 KB, more than any one free region of the KN7000's RAM holds. The linker script
`src/kn7/pdf.ld` spreads them over ARENA2, the program area and ARENA4 (`ld --enable-non-contiguous-regions`);
`tools/build/mkpdf.py` writes the main image and the segments, and `KN7APP.BIN` reads each where it goes.

The rest of the free regions and the firmware's frame buffers (292 KB, lent while the firmware's drawing is off and
kept in display memory meanwhile: `src/app/borrow.c`) make one TLSF heap of **844 KB** on program 893.

MuPDF 1.1 was chosen by measurement (`tools/measure/`, 2026-10-30): built for the KN7000 the same way, current MuPDF
linked to a minimal viewer is 1,361,633 bytes of code and constants; MuPDF 1.1 is 853,101.

On the PC, with the same drawing code built 32-bit (`tests/host/`), the smallest heap with which every page still comes
out right is 526 KB for the score and 862 KB for the manual (its pages are many small paths, and 30 Type 3 fonts).
Before the `KN7PDF` changes the manual peaked at 17 MB and the score at 2 MB. The main changes:

- an image is decoded a band of rows at a time, reduced and made gray as it decodes; images outside a band are not
  decoded;
- a Type 3 glyph's procedure is loaded when it is run, and shared between the codes that name it;
- a page's parsed objects are dropped once it is loaded and once it is drawn;
- ToUnicode CMaps and link annotations are left out; identity CMaps are shared;
- FreeType allocates through MuPDF's allocator, so its allocations make MuPDF free its cache; FreeType is trimmed;
- smaller tables: 8 colour components, a glyph cache of 64 KB and 400 glyphs;
- the draw device no longer frees the parent's picture after a push that ran out of memory;
- consecutive fills with the same state that share no pixel become one path. A contents page's dotted leaders are
  thousands of fills: page 2 of the manual needed 1208 KB with them separate and 798 KB merged, drawn byte-identical.

The floating point is GCC 14.2's soft-fp (`src/third/softfp/`) instead of the MN10300 libgcc's fp-bit.c, which took 45 %
of the CPU while a page was drawn. That brought the score's first page in MAME from 34.0 s to 24.6 s. Four-bit
anti-aliasing (the LCD shows 16 grays), coarser glyph positions in the glyph cache's key and curves flattened to 0.6
pixel, among other changes, brought it to 14.8 s.

### Drawing a page

The page is run once into MuPDF's display list (`src/kn7/view.c`), then drawn from it 32 lines at a time into a gray
band. Each band is made 4 bits a pixel and coded, PackBits a row at a time, into the page cache. When memory runs short
while the list is made, the page is drawn a region at a time without a whole list (the log says "no list"); a band that
runs short is drawn again half as tall.

### The page cache

The page is shown at 4 bits a pixel, half of the 643 KB an 8-bit page took. The display memory the page shown does not
take is a second heap, the display heap (`src/kn7/pagecache.c`). It holds:
- the coded pages: 29-69 KB each for the two test PDFs, 9-23 % of the 290 KB a 640 x 906 page takes at 4 bits a pixel
  (`tests/host/packbits_size.py`);
- up to 128 KB of MuPDF's font files and the Type 3 glyph procedures it has loaded. A Type 3 font's glyphs are content
  streams in the PDF; kept until the document is closed, each is read from the card once instead of each time it is
  drawn.

When the display heap is full, the page used longest ago goes, one the card has first. The card's copy of a page is the
coded page with a header naming the document, the page, the width and the anti-aliasing; a copy that does not match is
not used.

### Reading the PDF

The card is slow: a read costs about 5 ms, and 3.9 ms more for each 512-byte sector (from the unit's log). So MuPDF
reads at most 1 KB at a time, and 32 KB of display memory keep the file's 1 KB blocks read last (`src/kn7/readcache.c`);
a miss reads only the blocks missing, and 4 more when the reads run on. On the manual's 15 pages, the read cache and the
glyph procedures kept take the card's time from 427 s to 35 s, and the reads from 10,632 to 1,526; on the score's 5
pages from 8.0 s to 6.0 s. These figures come from the PC build's count of reads and a cost model made from the unit's
log (`tests/host/kn7pdf.c`).

### Drawing ahead, and showing it

The viewer's loop (`src/kn7/viewer.c`) serves the page asked for first, then saves a page drawn once the controls have
been left alone 1.5 s, then draws ahead. While MuPDF draws, its yield (every 20 ms) serves the wheel and the switches:
the page shown scrolls, a page drawn already is shown at once, and a page whose drawing is no longer wanted is stopped
(MuPDF's cookie). A page that does not fit in the cache is drawn straight onto the LCD.

The page is decoded from the cache whole into display memory, up to 1,004 lines at 640 wide (A4 is 906, Letter 828).
The [LCD controller]({{ site.baseurl }}/kn7000-display-subsystem/) shows 240 lines of it from its start address, so the
wheel scrolls the page by moving that address, without a pixel moving. The labels and the status line are in the
controller's ink layer (2 bits a dot over the picture), which stays still.

### The instrument meanwhile

The viewer's task runs at the firmware's priority, 3 (see the [task scheduler]({{ site.baseurl }}/kn7000-task-scheduler/)),
and MuPDF gives the CPU to the firmware every 20 ms of its work (`fz_kn7_yield`). So the keybed sounds, the panel's
buttons act and MIDI flows while a page is drawn. The firmware's tasks give the CPU only to each other: a first build's
task at priority 4, below them, ran once and never again.

A wheel step the firmware decoded first gets a step the other way put into the panel's ring after it, so the tempo
stays where it was.

### The log and the watchdog

`KN7APP.BIN` keeps a log (`src/app/diag.c`): the build, the firmware found, the load, every file and page, and a
heartbeat every 5 s while a page is drawn. It goes onto the card as it grows: each 3 KB as the next part,
`PDF\PDFLOG01.TXT`, `PDFLOG02.TXT` and on (up to 50), and what came after the last part as `PDF\PDFLOG.TXT`.
`update_sdcard.sh` brings them all back and then deletes the parts from the card.

When the viewer's task has not yielded for 4 s, a watchdog on the firmware's 1 kHz tick (`src/app/crash.c`) samples
where it is 16 times, then makes the task leave what it was doing. The log gets the 16 PCs, the registers, the stack
words that may be return addresses, and the viewer's own account: the page and stage, the glyph FreeType was drawing,
the line its rasterizer was on, the outline's points. The screen shows the PCs and the stack; the program stops there
and the instrument goes on.

## How it was checked

### On the PC

- **Arithmetic.** `tests/softfp/test_softfp.c` runs every floating-point operation `PDF.BIN` calls on 3,000,000 random
  pairs (NaNs, infinities and subnormals among them) against the PC's IEEE 754 arithmetic: 0 mismatches (2026-10-30).
- **Memory and pages.** `tests/host/kn7pdf.c` draws each page as the viewer does, with the heap limited as on the
  instrument; `heap_min.sh` finds the smallest heap with which every page comes out as with no limit (the figures in
  [Memory](#memory)). An AddressSanitizer build of the same ran clean down to a 150 KB heap.

### In MAME

Program 893, the owner's loader floppy, the program menu on a copy of the owner's card (`tests/mame/run_pdf.sh`).

- **The whole use.** `tests/mame/pdf_test.lua`: the list, a file opened and its first page drawn with C4 held on the
  keybed (and found held in `KN7APP.BIN`'s note state), the wheel scrolling the page, the viewer's switches kept from the firmware and the
  firmware's own still reaching it, the next page drawn ahead, PAGE UP, EXIT, EXIT held. With the page cache (build
  ce189eb, 2026-10-31) 20 checks of 20 pass on the score: first page in 16.8 s, the pages turned from the cache shown
  at once, the document opened again showing its first page from the card in 0.8 s. With build b2d4b5e (2026-11-01)
  20 of 20 pass on both PDFs: the manual's first page in 23.9 s, the score's in 16.5 s.
- **The pages.** The four pages of the manual written on the card in MAME (build b2d4b5e) match the PC's drawing with no heap limit, no pixel
  more than 32 of 255 apart.
- **The watchdog.** `tests/mame/hang.lua` makes the viewer stop yielding: the watchdog's screen came up 5.6 s later and
  its report was on the card 0.1 s after that (2026-10-31).

### On the owner's KN7000

Each build was staged on the owner's card (KN7000 `tools/sdcard/stage.sh`); the log came back with `update_sdcard.sh`.
From `notes/UNIT-RUNS.md`:

| date       | build   | result                                                                                                 |
|------------|---------|--------------------------------------------------------------------------------------------------------|
| 2026-10-30 | first   | an error after "Loading..."                                                                            |
| 2026-10-30 | 0a1b033 | `PDF.BIN` loaded in 6 s, checksums right, the list shown; the log ends at "drawing page 1"             |
| 2026-10-30 | 57292fe | freezes; one heartbeat at 5 s, then nothing: the viewer has stopped yielding                           |
| 2026-10-31 | 3d0fe47 | the watchdog's screen: 15 of its 16 PCs in FreeType's rasterizer (`gray_render_line`)                  |
| 2026-10-31 | 64d125c | the watchdog's report: FreeType's negative coordinates 65536 too high                                  |
| 2026-10-31 | 33b277a | toolchain fixed: past the old hang; then a system-error NMI while the heap was walked                  |
| 2026-10-31 | d2f9a89 | the score's pages 1-3 drawn in 16.1, 9.9 and 14.0 s; then the borrowed frame buffers found overwritten |
| 2026-10-31 | 8468662 | no crash screen; the manual's page 2 took 124 s (memory short, "no list"); it seemed to freeze later   |
| 2026-11-01 | 87f01d5 | the page cache works: every page drawn and saved; documents reopened start from the card               |

**The hang was the CPU.** The 64d125c report showed glyph 18 of a bold font with every negative y coordinate 65536 too
high: the high word of a 64-bit result one too high whenever it should be all ones. The MN1030/MN103S instruction manual (chapter 3, "Dangerous Code
Sequences") says a flag update reaches the PSW one cycle late, so an ADDC right after the ADD that sets its carry adds
the carry from before. GCC makes exactly that pair, in FreeType's `FT_MulFix_64` among others. The firmware, built with
Panasonic's compiler, has no ADDC, SUBC, ROR or ROL at all. `tools/build/check_flags.py` found 520 such reads in
`PDF.BIN` and none in `KN7APP.BIN`. The toolchain now puts a nop before every ADDC and SUBC (the Pinball port's
`gcc-kn7000-flags.patch`), `check_flags.py` checks every link, and MAME's MN10300 core models the delay
(kn7000_mame 0a37d84). With the delay modelled, MAME runs the 64d125c build into the same hang, on the same glyph.

**The page cache on the unit** (87f01d5, the log of 2026-11-01): the card has all 5 of the score's pages and all 15 of
the manual's as `.PGC` files, 29-70 KB each. The manual's pages 14 and 15 drew in 49.6 and 35.0 s and were saved in
1027 and 895 ms. Pages still in the display heap came back in 192-349 ms, pages read back from the card in 586-985 ms.
Reopened, the score found "5 of 5 pages on the card" and showed page 1 in 818 ms; the manual, 15 of 15, in 621 ms. The
score's pages 1, 2, 3 and 5 on the unit are 56261, 46047, 56372 and 64007 bytes, the sizes MAME's run wrote. No
watchdog report and no heap damage appear in what the log kept.

## Limits and open items

- **Unit runs of the latest builds.** The Type 3 procedures kept, the read cache, the merged fills and the log in parts
  (6ba23f7 to b2d4b5e, 2026-11-01) have been run in MAME only, as far as `notes/UNIT-RUNS.md` records.
- **The manual's page 2.** In MAME it still runs short of memory (the heap holds 316 KB after page 1) and is drawn in
  regions, in 50.0 s with b2d4b5e; its 543 MuPDF messages were not logged.
- **The borrowed frame buffers.** On the 2026-10-31 unit run of d2f9a89, part of the frame buffers lent to the heap was
  found filled with E0 bytes, and CONTRAST DOWN then ended in an NMI. In MAME (`tests/mame/probes/contrast.lua`) the
  firmware writes nothing there. Since 8468662 every pool is checked every 200 ms and damage is logged with its extent;
  the two unit runs since logged none, in what their logs kept. What wrote the E0 bytes is not known.
- **The firmware's gap.** What the firmware keeps in display memory between its frame's end (0x4B500) and the page
  (`LCD_FRAME`) is not known, so the display heap leaves that gap alone, at a cost of 16 KB of cache.
- **MuPDF 1.1 as trimmed.** Pages are 16 grays, at most 1,004 lines tall at 640 wide; images are reduced to gray;
  ToUnicode CMaps and link annotations are left out. File names on the card are 8.3.
- **Speed.** A page of music takes about 15 s in MAME and 9.9-16.1 s on the unit; a page of the manual 15.6-60.9 s in
  MAME. The card reads more slowly on the unit than in MAME (the viewer's 385 KB image in 3054 ms there, 1834 ms in
  MAME), so the read cache should save more on the unit than MAME shows.

The whole is AGPL-3.0 (MuPDF 1.1 is GPL-3.0 and jbig2dec AGPL-3.0); FreeType is used under its FTL, zlib, libjpeg and
TLSF under theirs (`src/UPSTREAM`).

## Sources

All in kn5000_homebrew `demos/kn7000_pdf/` unless named otherwise.

| path                                            | what                                                                          |
|-------------------------------------------------|-------------------------------------------------------------------------------|
| `README.md`                                     | use, the card, how it works, memory, building, licences                       |
| `notes/UNIT-RUNS.md`                            | every run on the owner's KN7000: build, what the owner saw, what the log said |
| `src/kn7/`                                      | the viewer: `viewer.c`, `view.c`, `pagecache.c`, `readcache.c`, `pdf.ld`      |
| `src/mupdf/`, `src/third/`, `src/UPSTREAM`      | MuPDF 1.1 with its `KN7PDF` changes; FreeType, zlib, libjpeg, jbig2dec, TLSF  |
| `src/app/`, `src/common/pfhost.h`               | `KN7APP.BIN`: task, files, panel, `borrow.c`, `diag.c`, `crash.c`             |
| `tools/measure/README.md`                       | why MuPDF 1.1: the code sizes of current MuPDF and 1.1                        |
| `tools/build/check_flags.py`                    | the link check for ADDC/SUBC after a flag update                              |
| `tools/card/pgc2png.py`, `tools/card/fatget.py` | the page files as PNGs; a file read off a card image                          |
| `tests/host/README.md`                          | the drawing on the PC: heap per page, smallest heap, cost model, page sizes   |
| `tests/mame/README.md`                          | the MAME sessions (`pdf_test.lua`, `hang.lua`, probes) and their results      |
| `tests/softfp/README.md`                        | soft-fp against IEEE 754 arithmetic                                           |
| KN7000 `tools/sdcard/README.md`                 | staging the card; `update_sdcard.sh` bringing back the logs and page files    |
| kn5000_homebrew `git log -- demos/kn7000_pdf`   | the dates and measurements of each step                                       |
