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
the 2-bit panel. The KN7000 itself has a 640×240 colour panel; the 2-bit path
matches the 320×240, four-grey panel of the KN2400/KN2600, which run the same
codebase.

## Palette-indexed bitmaps

UI artwork is stored as **headerless palette-indexed bitmaps** (the same design
as the KN5000 — see
[Raw UI bitmaps]({{ site.baseurl }}/kn7000-image-gallery/#raw-ui-bitmaps-table-rom)). Pixels are
raw palette indices, row-major; the bit depth is 2, 4 or 8 bpp. The blit API has
a **dedicated fast path per depth**, which is how the depths are known:

| Function | CPU addr | Depth |
|----------|----------|-------|
| `DrawBitmapSPFast4` | `0x484243CD` | 2 bpp (4 colours) |
| `DrawBitmapSPFast16` | `0x484245BC` | 4 bpp (16 colours) |
| `DrawBitmapSPFast256` | `0x48424784` | 8 bpp (256 colours) |
| `DrawBitmap` / `DrawBitmapFast` | `0x48423B56` / `…3C88` | generic |
| `DrawBitmapSP` / `…SP2` | `0x484240A4` / `…48DE` | sprite (transparent) |
| `DrawBitmapFile` / `…FileEx` | `0x48424A9F` / `…4CC8` | from a bitmap-file struct |
| `DrawIcons` / `DrawJpegFile[R]` | `0x48423DCD` / `…4EBD` | icon sheet / JPEG |

The **`SP` ("sprite") variants honour a transparent index** — index **`0xF7`**,
the KN5000's transparent colour, which the extracted 8-bpp icons use heavily.
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

| Index | Name | | Index | Name |
|-------|------|-|-------|------|
| `0x00` | `CL_Black` | | `0xF8` | `CL_Gray` |
| `0x01` | `CL_Maroon` | | `0xF9` | `CL_Red` |
| `0x02` | `CL_Green` | | `0xFA` | `CL_Lime` |
| `0x03` | `CL_Olive` | | `0xFB` | `CL_Yellow` |
| `0x04` | `CL_Navy` | | `0xFC` | `CL_Blue` |
| `0x05` | `CL_Purple` | | `0xFD` | `CL_Fuchsia` |
| `0x06` | `CL_Teal` | | `0xFE` | `CL_Aqua` |
| `0x07` | `CL_Silver` | | `0xFF` | `CL_White` |

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
