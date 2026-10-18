---
layout: page
title: KN7000 Display Subsystem
permalink: /kn7000-display-subsystem/
---

# KN7000 Display Subsystem

The KN7000 draws its UI to an LCD through the MILK toolkit's graphics layer:
palette-indexed bitmaps and text, composited by a family of blit routines and
handed to the LCD controller. This page ties the **hardware** (the LCD controller
and the framebuffer it scans; see [LCD hardware](#lcd-hardware)) to the
**firmware** (the drawing functions recovered by name in the
[disassembly]({{ site.baseurl }}/kn7000-firmware/)). Addresses are decoded from
`kn7000_program.rom`; work-RAM globals are in the `0x50000000` region.

## Panel type: colour vs 2-bit grayscale

The MILK graphics layer supports **more than one LCD panel type**, and the firmware
keeps the type in a work-RAM halfword at **`0x50007578`** (accessed by `GetColorMode` /
`SetColorMode`). Two predicate functions read it — decoded straight from their
source:

```
GetColorMode:    movhu (0x50007578), d0 ; ret          # the panel-type value
CheckColorLcd:   return (colormode == 0)               # 0x48421D70
Check2BitLcd:    return (colormode == 2)               # 0x48421D82
```

So the panel-type enum is **`0` = full-colour**, **`2` = 2-bit (4-level)
grayscale** (value `1` is a further mono/other variant). A second halfword at
`0x5000757A` (`GetLcdMode` / `SetLcdMode`) holds a related mode flag. The
firmware branches on these throughout the graphics layer — e.g. it provides a
`ConvPaletteMono4` routine to fold the colour palette down to 4 grey levels for
the 2-bit panel. The KN7000 itself has a 640×240 colour panel. Which instrument
reports the 2-bit model is not established (the model word is 2 when the ID byte at
`0x9CC00000` is `0x04` and `TgStrapProbe` is not 3); in that mode the firmware still
works with 640 × 240 frames.

What selects mode 2 is a model word at `0x50005218`: when it is 2, the start-up code
at `0x48414328` sets both the colour mode and the LCD mode to 2. In that mode
`SetPaletteRGB` also maps each palette entry to one of four grey levels
(`ColorToMono4Level`, `0x4842DB3C`, by squared RGB distance kept in 16 bits, so not
always the nearest) and stores the level 0..3 in a 256-byte table at `0x50122CAC`, which the
screen output and `CaptureLcd` read back through `GetPaletteRGB4`. The screen capture
follows the mode: a 640 × 240 **4-bpp** BMP (76,918 bytes) in mode 2, a **24-bpp** one
(460,854 bytes) on the colour panel.

## Palette-indexed bitmaps

UI artwork is stored as **headerless palette-indexed bitmaps** (the same design
as the KN5000 — see
[Raw UI bitmaps]({{ site.baseurl }}/kn7000-image-gallery/#raw-ui-bitmaps-table-rom)). Pixels are
raw palette indices, row-major, at 1, 2, 4 or 8 bpp. The blit API has one
routine per source format, which is how the depths are known:

| Function              | CPU addr     | Source                                                                       | Skips 0xF7 |
|-----------------------|--------------|------------------------------------------------------------------------------|------------|
| `DrawBitmap`          | `0x48423B56` | bitmap-table entry, 8 bpp                                                    | yes        |
| `DrawBitmapFast`      | `0x48423C88` | bitmap-table entry, 8 bpp, rows copied whole                                 | no         |
| `DrawIcons`           | `0x48423DCD` | icon-table entry, always 24 x 24 at 4 bpp (nibble n -> index n or 0xF0+n)    | no         |
| `DrawFrameSP`         | `0x48423EFB` | frame-table entry, 8 bpp; 0xF6 = the caller's colour                         | yes        |
| `DrawBitmapSP`        | `0x484240A4` | caller's pointer, 8 bpp                                                      | yes        |
| `DrawBitmapSPFast`    | `0x4842429E` | caller's pointer, 8 bpp, rows copied whole                                   | no         |
| `DrawBitmapSPFast4`   | `0x484243CD` | caller's pointer, 2 bpp; loads 4 colours at a caller-chosen palette index    | no         |
| `DrawBitmapSPFast16`  | `0x484245BC` | caller's pointer, 4 bpp, drawn as indices 0x20..0x2F; loads those 16 colours | no         |
| `DrawBitmapSPFast256` | `0x48424784` | caller's pointer, 8 bpp; loads palette entries 0x20..0xCF first              | no         |
| `DrawBitmapSP2`       | `0x484248DE` | caller's pointer, 1 bpp, foreground and background colour                    | no         |
| `DrawBitmapFile`      | `0x48424A9F` | Windows BMP in memory, 1/4/8 bpp, pixels + 0x20; loads palette 0x20..0xCF    | no         |
| `DrawBitmapFileEx`    | `0x48424CC8` | the same BMP, but it only loads the palette and marks the rectangle dirty    | -          |
| `Draw2BpFile`         | `0x4842829F` | the same BMP; a second copy of `DrawBitmapFile` that cuts images at 240 rows | no         |
| `DrawJpegFile`        | `0x48424EBD` | JPEG, decoded straight to direct-colour picture pixels                       | no         |
| `DrawJpegFileR`       | `0x48424F7D` | the same, with rounded corners (8 pixels per corner keep the background)     | no         |

Only `DrawBitmap`, `DrawBitmapSP` and `DrawFrameSP` skip pixels of index
**`0xF7`** (`CL_Transparent`, the KN5000's transparent colour, which the
extracted 8-bpp icons use heavily); the `SP` in the other names does not mean
transparency. None of the blitters clips horizontally: an image wider than
`640 - x` runs on into the next framebuffer row. The table and pointer
blitters stop at the first row at `y >= 240`; the JPEG path has no such stop.
Every routine has a fully labelled and commented listing in the disassembly
(`annotations/gfx_draw.ann` and `annotations/gfx_bmpfile.ann`, rendered into
`src/program.s`). Despite its name, `Draw2BpFile` has nothing 2-bit about it: it takes
1, 4 and 8 bpp and writes the 8-bit plane like `DrawBitmapFile`. Its only caller is the
hidden DEBUG TOOLS > BITMAP LOAD screen; the "2Bp" most likely names the 2-bit panel
mode above.

## Windows BMP files

Pictures loaded from disk or SD card and the slide-show pictures are BMP or JPEG files,
and the homepage picture is a BMP; all are kept whole in memory. Every BMP user in the
firmware parses them
with one routine, **`GetBitmapInfo`** (`0x48421DE1`, 13 call sites). It accepts only
`"BM"` files with the 40-byte `BITMAPINFOHEADER`, one plane, 1, 4 or 8 bits per pixel,
at most 256 colours and no compression (`BI_RGB`); it copies up to 1 KB of colour table
and returns a pointer to the pixels. It never checks the width, the height, `bfSize`, or
that the colour table and pixels lie inside the file.

`DrawBitmapFile` loads the file's colours 0..`0xAF` into palette entries
**`0x20`..`0xCF`** and adds `0x20` to every pixel. The rest of the palette belongs to the
UI, so a picture can use **176 colours**, not 256. **`ConvertBitmapFile`**
(`0x48421E88`) prepares a file for that: it repacks the BMP in place inside a given size
(the colour table straight after the headers, the pixels straight after it) and, for an
8-bpp file whose repacked colour table has more than 176 entries (every 8-bpp homepage
picture), calls **`BmpReduceColors`** (`0x4842215B`). That
routine counts how often each colour index is used, sorts the palette most-used first
(a comb sort), keeps the first 176 and maps every other colour to the kept one at the
least squared RGB distance, rewriting palette and pixels in place. The slide show runs it
before drawing a picture, and the homepage loader before it programs the picture into
the custom flash.

Where the files themselves sit in RAM while this happens is on the
[Work RAM Map]({{ site.baseurl }}/kn7000-work-ram/#where-an-image-file-lands) page.

Primitive drawing is provided too: `DrawLine`/`DrawLineEx`, `DrawBox`,
`DrawFrame`/`DrawFrameEx`/`DrawFrameSP`, `DrawCircle`.

## The palette (CLUT)

Indices are resolved through a **256-entry colour look-up table**, stored in the
program image at file **`0x32573C`**. Each entry is a 32-bit **`0x00BBGGRR`**
(BGR-order) word — proven by the named colour constants below (`CL_Red` = index
`0xF9` = stored `0x000000FF`, i.e. the *low* byte is red). It is the first data
structure the [disassembly project]({{ site.baseurl }}/kn7000-firmware/) lifted from raw bytes into
typed source. At runtime the palette is manipulated through `SetPaletteRGB`
(`0x4842D9F1`), `GetPaletteRGB` (`0x4842DB23`) and `GetPaletteRGB4`
(`0x4842DB30`); `ConvPaletteMono4` (`0x4842DC88`) derives the 2-bit-panel
greyscale ramp from it.

### Named colours

The firmware refers to palette entries by name through a `CL_*` constant table
(recovered by the KN7000 disassembly's `tools/gen_constants.py`). The base is a
**VGA-16 layout** — the eight dark colours at indices `0x00`–`0x07` and the eight
bright ones at `0xF8`–`0xFF`:

| Index  | Name        |     | Index  | Name         |
|--------|-------------|-----|--------|--------------|
| `0x00` | `CL_Black`  |     | `0xF8` | `CL_Gray`    |
| `0x01` | `CL_Maroon` |     | `0xF9` | `CL_Red`     |
| `0x02` | `CL_Green`  |     | `0xFA` | `CL_Lime`    |
| `0x03` | `CL_Olive`  |     | `0xFB` | `CL_Yellow`  |
| `0x04` | `CL_Navy`   |     | `0xFC` | `CL_Blue`    |
| `0x05` | `CL_Purple` |     | `0xFD` | `CL_Fuchsia` |
| `0x06` | `CL_Teal`   |     | `0xFE` | `CL_Aqua`    |
| `0x07` | `CL_Silver` |     | `0xFF` | `CL_White`   |

On top of that sit **semantic UI colours** — `CL_TitleBar`, `CL_IconBack`,
`CL_Text`, `CL_Selected`, `CL_PageBack`, `CL_EditSw` (`0x17`–`0x1C`), the
sound-expansion accents `CL_SoundExp1`–`4`, and crucially **`CL_Transparent =
0xF7`**, which names the transparent index the `SP` sprite blitters skip.

## Fonts and text

Text metrics come from a **font descriptor table** whose base pointer lives at
`0x50122DB8`. Each descriptor is **`0x14` (20) bytes**, indexed by font id — read
directly from `GetCharHeight` / `GetCharDescent`:

```
GetCharHeight:   font = *(0x50122DB8) + id*0x14 ; return *(font + 2)   # 0x4842DF60
GetCharDescent:  font = *(0x50122DB8) + id*0x14 ; return *(font + 4)   # 0x4842DF73
```

so a descriptor holds the glyph height at `+2`, the descent at `+4`, and further metrics beyond.
`GetFontCount` / `GetFontNameTable` enumerate the installed fonts, and
`ConvertStrings` / `ConvertStringsEx` render/transform strings — the KN7000 draws
English/German/French/Spanish/Indonesian text plus a Japanese developer entry
(see [firmware strings]({{ site.baseurl }}/kn7000-firmware/)).

## LCD hardware

The display hardware is one controller and one buffer:

* **LCD controller — IC104** (`C0HBA0000117`, the colour LCD controller; its
  video output is what
  [Reading ROM out of the screen]({{ site.baseurl }}/kn7000-rom-from-the-screen/)
  captures).
* **Framebuffer — `0x9CE00000`.** The firmware composites the whole display
  itself into a 640×240 RGB565 image at `0x9CE00000`, which is the buffer the LCD
  controller scans, and MAME presents that buffer directly (see
  [the boot splash]({{ site.baseurl }}/kn7000-initial-data/#the-boot-splash-and-the-green-screen)).
  Pictures reach it as 12-bit direct colour from two work-RAM planes
  (`0x500D4080`, `0x500F9880`), not as palette indices.

### The compositor

The routine that turns the planes into the frame is at `0x48414D40` in build 942. It
redraws **one rectangle at a time**: for each pixel it reads a byte from the first plane
(`0x500D4090` in build 942, returned by `GetVRAMAddr`); if its top nibble is `0xD`, the pixel
is direct colour (red in that byte's low nibble, green and blue in the second plane,
`0x500F9890`, returned by `GetWRAMAddr`), otherwise the byte is a palette index looked up in
the RGB565 table at `0x50122ABC`. The result goes to `0x9CE00000`. Only rectangles the
firmware redraws are recomposited, so a pixel written straight into the frame stays until the
firmware repaints that spot — which is how the
[uptime clock demo]({{ site.baseurl }}/kn7000-sp7001-homebrew/#demo-an-uptime-clock) draws.

`0x34000000` is not a display bank. It holds the MN103002A's own on-chip
registers: the interrupt controller's `GxICR` at `0x34000108`–`0x3400017F`,
`EXTMD` at `0x34000280`, the serial channels at `0x34000800` and the timers at
`0x34001080`. `0x90000000` and `0x8C000000` are not video windows either: they
are the uncached views of work RAM (`0x50000000`) and of the self-loaded library
(`0x4C000000`).

## Relationship to the KN5000

The bitmap storage design, the transparent index `0xF7`, the CLUT approach and
the `Draw*`/`…Proc` naming are all **shared with the KN5000**
([Shared Codebase Map]({{ site.baseurl }}/technics-shared-codebase/)); the KN5000
[Display subsystem]({{ site.baseurl }}/display-subsystem/) page is the conceptual companion. What
is KN7000-specific: the panel-type switch (colour and 2-bit), standard **JPEG**
artwork alongside the indexed bitmaps, direct-colour pictures, and the RGB565
framebuffer at `0x9CE00000`.
