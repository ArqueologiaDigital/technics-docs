---
layout: page
title: KN7000 User Data & the Initial Data Disk
permalink: /kn7000-initial-data/
---

# KN7000 User Data & the Initial Data Disk

Some of the KN7000's on-screen content — the built-in **style names**, the
**Favorites**, the **Custom** panels — does not live in the firmware update images
(`kn7000_program.rom` / `kn7000_table.rom`). It lives in a separate **custom-data
flash** that ships **blank** and is programmed, once, from an **"Initial Data"
floppy disk** during first setup. This page documents that subsystem, recovered by
reverse-engineering the firmware's disk-load/install path.

This is the same design the [KN5000]({{ site.baseurl }}/system-overview/) uses — its MAME driver
notes that the custom-data flash (IC19) "was dumped from a system that had it
already programmed by the initial data disk" — one more piece of the
[shared codebase]({{ site.baseurl }}/technics-shared-codebase/).

## The custom-data flash

| Property                   | Value                                                                                                                                                                                                       |
|----------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Read view** (CPU)        | `0x96800000`, the same window: the firmware reads the data there too (e.g. the slot descriptors at `0x96820002`). `0x56000000` is not this chip: it is one of the four EXP.CS "SOUND RAM" expansion windows |
| **Command/program window** | `0x96800000` — AMD/Fujitsu x16 command set (unlock writes to `0x9680AAAA` / `0x96805554`)                                                                                                                   |
| **Chip**                   | IC21, 2 MB / 16 Mbit bottom-boot: MBM29LV160B, MX29LV160B or AT49BV16X4 (descriptor table `FlashChipIdTable`, program `0x1CF9E0`)                                                                           |
| **Driver**                 | `FlashWordProgram` `0x4847F721`, `FlashSectorErase` `0x4847F75A`, `FlashReadAutoselect` `0x4847F980`, `FlashReset` `0x4847F6C7`                                                                             |

`0x57000000` is not a factory data flash either. Like `0x56000000`, it is one of the
four EXP.CS "SOUND RAM" expansion windows, which read empty unless an SY-EW board is
fitted (see [Expansion Bus & Wave-ROM Dump]({{ site.baseurl }}/kn7000-expansion-and-wave-dump/)).
MAME preloads IC21 with the factory default, the payload of the Initial Data Disk.

## The Initial Data disk (`idd7000`)

MAME carries this disk as `idd7000` in the `kn7000_flop` software list
([mamedev/mame#16394](https://github.com/mamedev/mame/pull/16394)), a FAT12
reconstruction built from the archived installer, alongside two disks of published
custom data (`custom1`, `custom2`).

The disk carries four files. Each begins with a Technics tag matching the firmware's
disk-file dispatch tables (`DiskFileTagTable` `0x48664090`, `DiskFileExtTable`
`0x48664438`), and installs to one of two destinations:

| File           | Destination      | Contents                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
|----------------|------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `01CTMINI.AST` | custom **flash** | the factory **CUSTOM style memory**: 20 slots, each a custom style with its One Touch Settings, pads and user sounds (format: [Custom Style Memory (IC21) & .AST Files]({{ site.baseurl }}/kn7000-custom-style-memory/)). A 16-byte header — tag `"J K"` (KN6000: `"I K"`), `+0x03` = 1, the u32 LE **inflated** size `0x1E0000` at `+0x04`, 8 bytes of stack residue at `+0x08` — then the bank deflated by **zlib 1.0.4**, without the 2-byte zlib header but with the Adler-32 trailer. It inflates to the custom flash from offset `0x20000` to the 2 MB end (the bank at `0x96820000`). Decoded, it carries the real style names (`Swing And Jive`, `Calypso Dance`, `Jazz Fusion`, …) |
| `02UMDINI.MD`  | custom **flash** | the three USER MIDI SETTINGs: a header, a list of 44 parameter ids and three settings, at `0x96804000` (was read as "44 style-IDs" for battery SRAM)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `03FAVINI.FAV` | custom **flash** | Favorites (name + settings), at `0x96810000`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| `04HPGINI.HMP` | custom **flash** | Home-Page (layout record + an embedded BMP), at `0x96811000`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |

**All four live in the flash** (corrected 2026-10-31; this page said only the `.AST` did, and the
rest went to battery-backed SRAM at `0x50083D72`). A whole IC21 read from a real KN7000 holds the
`.MD` part byte for byte equal to `02UMDINI.MD` at `0x96804000`, the `.FAV` at `0x96810000` and the
`.HMP` at `0x96811000`. The code that programs those areas is traced (`func_4C024000` for the settings
image, `func_4849EE0B` for the favorites, `HpFlashWriteDefaults` for the home page), and each is copied
to work RAM at boot (`0x500D2B14`, `0x5006B888`, `0x5006B5F8`). *[INFERENCE]* The disk's install
writes them there too; its path for these three files was not traced. The chip's layout is on
[Panel Memory Records]({{ site.baseurl }}/kn7000-panel-memory/#ic21-what-a-kn7000-keeps-in-its-custom-data-flash). The extractor (`extract_idd7000.py`
in the kn7000_extraction tools, not yet published) parses all four and now **decodes
the `.AST`** (raw DEFLATE) to a `.flash.bin`. The disassembly repository does the same for the
`.AST` files with `kn7000/tools/ast_file.py`, and since 2026-10-29 rebuilds the decoded bank of
every factory `.AST` (`idd7000`, the eight sets of `custom1` / `custom2`, and the KN6000's
`idd6000`) byte for byte from typed source (`make -C kn7000 verify-customdata`).

**The `.AST` codec is plain zlib.** The firmware links **zlib 1.0.4** — its inflate error
strings (`unknown compression method`, `invalid window size`, `incorrect header check`,
`need dictionary`, `incorrect data check`) sit at `0x485CD20C`, right after the style-type
name table (`8 Beat`, `16 Beat`, `Dance Pop`, … at `0x485CCF2C`). The payload is a *raw*
DEFLATE stream (no 2-byte zlib header) at file offset `0x10`; inflating it with
`zlib.decompressobj(-15)` yields exactly `0x1E0000` bytes = the custom-flash region from
offset `0x20000` to the 2 MB end. Python's own zlib inflates it but does not deflate it back to
the same bytes; a Python port of zlib 1.0.4's deflate (`kn7000/tools/zlib10_deflate.py`) does, for
all ten factory files ([details]({{ site.baseurl }}/kn7000-custom-style-memory/#the-ast-file)). (The earlier "Huffman/LZH, not zlib" and "LZSS-variant"
readings were wrong — pylzss's 1.1 MB partial was a false positive; the near-uniform byte
histogram is just well-compressed DEFLATE output.) The decoded image is genuine user data,
but it is not the source of the "all 8 Beat 1" style-list bug. (An early test that preloaded
it at `0x56020000` and saw no reads there proved nothing either way: `0x56000000` is an
empty expansion window, not this flash.) That bug's real mechanism — a different, undumped
~4.1 MB "Technics Rhythms" resource, with a synthetic-ROM mitigation in the research
overlay only — is described under [How the rhythm menu resolves a style
name](#how-the-rhythm-menu-resolves-a-style-name) below; an earlier "templated at boot by
`0x484420CB`" theory was investigated and superseded by that finding.

### Favorites, decoded

The four factory Favorites and what they recall (each setting is an ID whose
`& 0x00700000` bits select built-in / MEMORY / CUSTOM source):

* **Example** — a mix of built-in rhythms and CUSTOM sounds
* **Cool Sounds !** — nine CUSTOM sound/style IDs (`0x2014xx` / `0x2600xx`)
* **Cool Rhythms !** — nine built-in rhythm IDs
* **Entertainer** — panel-setting IDs

### The Home-Page image

`04HPGINI.HMP` embeds a 160×100 Windows BMP — a holiday-themed graphic (a red bow
with holly over sheet music):

<figure style="margin:1rem 0;text-align:center;"><img src="{{ "/assets/images/kn7000/idd7000-homepage.png" | relative_url }}" alt="Initial Data disk home-page image, 160x100" style="image-rendering:pixelated;width:320px;max-width:100%;border:1px solid #ccc;border-radius:3px;"><figcaption style="font-size:0.8rem;color:#777;">The factory home-page image, carved from <code>04HPGINI.HMP</code> (160×100, 2× shown)</figcaption></figure>

It is **byte-identical** to the image already in the program ROM at `0x48745718`
(shown in the [Image Gallery]({{ site.baseurl }}/kn7000-image-gallery/) as `program_345718`), so the
disk simply re-installs the factory default.

## The boot splash (and the "green screen")

A real KN7000 opens with a **640×240 boot splash** — three chrome music notes
sweeping past the Earth toward a starburst, then the mirrored **"KN7000"** logo. Both
frames are **JPEGs already present in the dumped table ROM**:

| Frame | Table-ROM address |
|-------|-------------------|
| Music notes in space | `0x480566E8`, `0x4805A32E` |
| "KN7000" chrome logo | `0x48066517`, `0x4806B954` |

(Other 640×240 table-ROM images such as "Welcome to SX-KN7000" @`0x48139EF0` belong
to the **demo mode**, not the power-on splash.)

In the emulator, boot first showed a **green screen** where this animation should be.
Fixing it took untangling **two** independent bugs:

1. **The display model.** KN7000 pictures are **not palettized** — a picture pixel is a
   12-bit (4:4:4) direct colour split across two work-RAM planes (`0x500D4080` byte =
   `0xD0 | red4`; companion `0x500F9880` byte = `(green4<<4) | blue4`). The firmware
   composites these into a 640×240 RGB565 image at `0x9CE00000` — the exact buffer the
   LCD controller scans. The driver now presents `0x9CE00000` directly, so the whole
   display (UI *and* pictures) is pixel-exact.

2. **The JPEG decoder.** With the display fixed, the splash showed *noise* instead of
   green — the software JPEG decoder was producing garbage. The cause was a single
   **unimplemented CPU instruction**: the MN103002A's user-defined `udf07` op, which the
   firmware uses as a **bit-search** (the AM33's `BSCH`), in the decoder's Huffman step.
   The CPU core was silently skipping it, desyncing the entire bit stream. Implementing it
   (the position of the highest set bit below a given bit, searching from bit 31 by
   default) made the splash decode **pixel-clean** — verified against a reference decode
   of the same table-ROM JPEGs.

With both fixed, the emulated KN7000 now plays its real power-on splash — the chrome
music notes sweeping over the Earth, then the mirrored "KN7000" logo. (Details in the
driver's `display-dual-plane-direct-color.md` and `mn10300-udf-instructions-unimplemented.md`
notes.)

<figure style="margin:1rem 0;text-align:center;"><img src="{{ "/assets/images/kn7000/splash-working.png" | relative_url }}" alt="The emulated KN7000 boot splash, decoded and rendered correctly" style="max-width:100%;border:1px solid #ccc;border-radius:3px;"><figcaption style="font-size:0.8rem;color:#777;">The boot splash rendering correctly in emulation after both fixes (dual-plane display + the <code>udf07</code> bit-search CPU op).</figcaption></figure>

## How the rhythm menu resolves a style name

Pressing a rhythm-genre button (e.g. BALLAD) resolves style names through a clean
program-ROM chain — all now named in the [disassembly]:

1. `GetCurrentGenreIndex` (`0x48435A1B`) reads the current genre (RAM `0x50034C3C`).
2. `GenreStyleTable` (`0x48735EE4`) — 16 records `{name[16], styleCount@+0x11,
   styleListPtr@+0x14}` — gives that genre's style-ID list (BALLAD = 16 styles).
3. Each style-ID's source bits pick built-in / MEMORY / CUSTOM; `ResolveStyleId`
   (`0x48435B33`) maps it through `StyleNumToBankSlotLUT` (`0x48734EE4`).
4. The **display name** comes from a *different* resource than the custom-data flash
   above: a "Technics Rhythms" name table that `StyleNameModuleBoot` (`0x4843385E`)
   looks for through `StyleResourceWindowProbe` (`0x4843D6D7`). The probe tries five
   windows — `0x48010000` (table ROM + `0x10000`), `0x40610000`, `0x40010000`,
   `0x54E10000` and `0x40810000` — and otherwise returns `0x54E00000` as a last resort.
   None of them holds the resource in the dumped images. When every probe misses, the
   resolver falls back to a program-ROM stub (`0x48729988`, header `count = 1`), so
   every style row rendered as "8 Beat 1" regardless of its real style-ID.

So the "all 8 Beat 1" symptom was never the custom-data flash above (that theory — along
with an earlier "templated at boot" theory — is superseded); it traces to the rhythm-data
device, which holds the ~4.1 MB resource: IC18, a 64 Mbit mask ROM in later production, or IC20,
a 32 Mbit flash in earlier production. (IC21 is the custom flash above.)

**Resolved by a dump (October 2026).** The CPU-visible 4 MB of IC18 were read from the owner's
unit with the [ROM dumper]({{ site.baseurl }}/kn7000-rom-dumper/), and the resource is at
`0x40010000`, the probe's third window: 169 styles in IC18 plus 51 that the index sends to the
table ROM make the 220 built-in rhythms. Its format, and the byte-exact source the disassembly
now rebuilds it from, are on [Rhythm ROM (IC18)]({{ site.baseurl }}/kn7000-rhythm-rom/). The
`kn7000_mame` overlay now loads the real chip (`c3cbnd000046.ic18`) at `0x40000000`. That
retired its earlier mitigation, a **synthetic ROM** (`kn7000_rhythms_synthetic.rom`, built by
`tools/gen_technics_rhythms.py`, flagged `BAD_DUMP`) mapped at the probe's last-resort window
`0x54E00000`, which rebuilt the directory prefix from the truncated copy in the table ROM at
`0x483E828C` plus 52 real style names from an intact secondary catalog, and labelled the other
168 names as placeholders (e.g. "BALLAD 04 ?"). Mainline MAME still declares the rhythm ROM
`NO_DUMP`, so there the probe finds nothing and the firmware falls back to the program-ROM stub.
