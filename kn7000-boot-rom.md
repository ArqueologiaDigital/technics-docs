---
layout: page
title: KN7000 Boot ROM (IC18)
permalink: /kn7000-boot-rom/
---

# The KN7000 boot ROM: the first 64 KB of IC18

The KN7000's CPU starts at `0x40000000`, where IC18 answers: the 4 MB the CPU can see of the
mask ROM `C3CBND000046`, which holds the rhythm (style) data. Its first 64 KB are not rhythm
data but MN10300 code, the instrument's **boot ROM**. It sets up the bus, the caches and the
SDRAM, runs the **update system** (floppy and SD flash update, update-disk check, device
info) when the right keys are held at power-on, and otherwise jumps to the firmware in the
program flash at `0x48400000`.

This is where the KN7000 keeps its flash updater. The resident firmware cannot rewrite its
own program flash, and the long search recorded on
[Firmware Robustness & ROM Archival]({{ site.baseurl }}/kn7000-firmware-security/#45-where-does-the-flash-updater-live)
ended in "another device"; the boot ROM is that device.

Since 2026-10-24 the disassembly repository rebuilds it byte for byte:
`kn7000/src/ic18/boot.s` is all 65,536 bytes, fully disassembled, with every routine named and
given a header comment, the data typed and nothing `.incbin`'d (disassembly commit
`60216cfe8` and the naming commits after it, merged as `31add4e7b`). Its notes, which this
page follows, are `kn7000/notes/ic18-boot-rom.md`.

    make -C kn7000 verify-ic18        # src/ic18/boot.s -> build/kn7000_ic18_boot.bin, compared with the chip
    make -C kn7000 ic18-src UNIDASM=… # regenerate src/ic18/boot.s (tools/gen_ic18_s.py)

`make gate-kn7000` (and so `make gate-all`) runs `verify-ic18`, and since 2026-10-29 also
`verify-ic18-full`, which rebuilds the whole chip ([below](#the-rest-of-ic18-rhythm-data)).

## Provenance

The image is the first 4 MB of `R4000000.BIN` from pass 4 of the
[ROM dumper]({{ site.baseurl }}/kn7000-rom-dumper/) on the owner's own instrument (a PROGRAM 893
unit), read twice and identical both times. Which chip answers at the IC18/IC20 site of that
unit has not been checked by opening it. Neither the chip image nor its first 64 KB is
committed: the Makefile cuts the reference from the private romset and checks it.

| what                        | SHA-1                                      |
|-----------------------------|--------------------------------------------|
| the whole chip, 4,194,304 B | `2dc71f5082063cd6b21e4ed16acd67e9d326a79f` |
| its first 64 KB             | `00db930227efcac3b329edbb210db5ec26dfa25e` |

## Layout of the 64 KB

The reset code reads its own layout from the image, and the source generator checks every
constant it relies on (`layout()` in `kn7000/tools/gen_ic18_s.py`):

| file offset     | CPU address        | contents                                                                |
|-----------------|--------------------|-------------------------------------------------------------------------|
| `0x0000-0x0010` | `0x40000000`       | reset vector (`jmp Reset`), NMI vector at +8 (through a work-RAM thunk) |
| `0x0011-0x03FF` | `0x40000011`       | what an older link of this ROM left behind (below)                      |
| `0x0400-0x0593` | `0x50010000` (run) | the initialised-data image, copied there by Reset                       |
| `0x0594-0x0AFF` | `0x40000594`       | Reset and the NMI handler, run in place                                 |
| `0x0B00-0xFA0B` | `0x50000010` (run) | the program image: code to `0xCF1C`, then its constant data             |
| `0xFA0C-0xFA17` | `0x4000FA0C`       | `ImageCopyDescriptor`: count, source, destination of that copy          |
| `0xFA18-0xFFFF` |                    | erased (`0xFF`)                                                         |

63,148 of the 65,536 bytes are not `0xFF`; the last used byte is `0xFA17`
(`kn7000/notes/ic18-boot-rom-probes/ic18_layout.py`).

## What it does

**`Reset`** sets up the memory controller, the caches (`CHCTR` `0x30`, then 3), the port
defaults and the SDRAM (eight refresh cycles through `0x32000040`). It copies the program
image to `0x50000010` through the uncached view, clears `.bss` and copies `.data`, sets `CHCTR`
bit 7, clears `IVAR0`-`IVAR6`, and writes two `nop; jmp` thunks in work RAM, at `0x50000000`
to `IrqDispatch` and at `0x50000006` to the NMI handler. With `IVAR0`-`IVAR6` at 0 and the
thunks in RAM, `CHCTR` bit 7 is what moves the interrupt entry from the ROM to work RAM. The
firmware repeats the same sequence. Port P04 bit 5 is strobed between almost every step; by its
pattern it may be a watchdog kick, which has not been confirmed on the board.

**`BootMain`**, ticking on timer 4 with every flash in read mode:

1. If strap bit 14 (`0x98070000`) is clear, it runs the SD update at once (by the look of
   it, a factory or service set-up).
2. It brings up the panel link and reads which of seven key combinations is held
   (`BootKeyComboMatch`, from the panel's sign-on replies). Combination 4 opens the **UPDATE
   SYSTEM MENU**, 5 **DEVICE INFO** (does the program flash identify as flash or as mask ROM)
   and 7 **UPDATE DISK CHECK**, each only with an update floppy in the drive. On 4 it then
   offers the **SD update** if the card holds update files.
3. Interrupts and caches off, `jmp 0x48400000`.

The firmware has the same key-combination code as `PanelTypeDetect`; here the result picks
the menu.

### Floppy updates

An update floppy is a 1.44 MB disk. `UpdateDiskIdentify` reads LBA 0x21 and compares its first
six bytes with thirteen kinds; the kind is also the target device (`FlashDeviceBase`):

| kind  | name                         | target                                |
|-------|------------------------------|---------------------------------------|
| 0, 1  | `KN7KP1`, `KN7KP2`           | program flash, `0x88400000` and +2 MB |
| 2, 3  | `KN7KT1`, `KN7KT2`           | table flash, `0x88000000` and +2 MB   |
| 4     | `KN7KCT`                     | custom-data flash IC21, `0x96800000`  |
| 5     | `KN7KHD`                     | `0x96000000` (expansion window)       |
| 6, 7  | `KN7KW1`, `KN7KW2`           | `0x97000000`, `0x81000000`            |
| 8, 9  | `KN7KR1`, `KN7KR2`           | CS0 `0x80000000` and +2 MB            |
| 10-12 | `KN7KDM`, `KN7KA1`, `KN7KA2` | picture window `0x97800000`           |

Kinds 8 and 9 write CS0 itself: on early units an IC20 flash sits where IC18 is
(`0x80000000` is the uncached view of `0x40000000`). LBA 0x22 holds the block sums as
`@`-separated hex text; the image follows from LBA 0x24 as an LZSS stream (4 KB window,
12-bit offsets, 4-bit lengths + 3, window pre-filled up to `0xFEE`) whose 8-byte header is
followed by the 24-bit size. `UpdWriteDisk` decompresses it straight into the flash, a word at
a time; `UpdVerifyDisk` only sums it against LBA 0x22 (UPDATE DISK CHECK). Images of 2 MB
(kinds 0, 2, 8) or 1 MB (kind 0xB) continue on a second disk ("Change disk(2/2)"). The
[System Update Discs]({{ site.baseurl }}/kn7000-system-update-discs/) page describes the
disks themselves.

The flash driver has two halves. Kinds 0-3 are two 16-bit chips side by side (32-bit
commands, `0x00AA00AA` at `0x1554`; Fujitsu `0x22F6`/`0x22F9`/`0x225F`/`0x2250`, Macronix
`0xA100`/`0xA200`); the others are one 16-bit chip (`0xAA` at `0xAAAA`; Fujitsu
`0x2227`..`0x22F9`, Atmel `0xC0`/`0xC2`, Macronix `0xF9`/`0xA100`/`0xA200`). The program
flash's version is the byte at `0x4840000F` (`PROGRAM_FLASH_VERSION`), shown as
`NOW(CURRENT) = VerX.Y` beside the disk's.

### SD updates

`SdFlashUpdate` mounts the card's first FAT12 partition with its own small reader (`Fat*`)
and looks for `KN7KPRG.DAT`, `KN7KTBL.DAT`, `KN7KCSTM.DAT`, `KN7KRHY.DAT` and
`KN7KAROM.DAT` (kinds 0, 2, 4, 8 and 0xB). Each file found is written uncompressed: identify,
erase, write, verify, then a summary ("Update Infomation", sic). The SD layer below it
(`Sd*`, `Disk*`) is the firmware's design: the routines follow program 941's in order and many
have the same code, but there is no worker task, so `DiskCmdTransact` calls the handler
directly.

### What else is inside

- The C library under `sprintf` (newlib-style `vsprintf_core`, `strtol`, `localeconv`, the
  double helpers): 33 routines are byte-identical to the firmware's, 20 more the same code
  linked elsewhere.
- The control-panel link driver, a copy of the firmware's (`Panel*`).
- The floppy controller driver (`Fdc*`): a uPD765-family controller at `0x98020000` with DMA
  channel 0, media geometry for 720 KB, 1.2 MB (77 cylinders, 1024-byte sectors) and 1.44 MB
  disks, and disk detection by index pulses.
- A text console on the LCD controller at `0x9CC00000` (frame buffer `0x9CE00000`, 640
  pixels a line) with an 8x16 font for `0x20`-`0xFF`, and four soft-key captions read
  through the panel.

**The LCD controller is an Epson S1D13806**, the S1D13506 with 1280 KB of display memory inside
it (measured on the owner's unit, 2026-10-26). `LcdControllerInit`
writes 106 registers, every offset an S1D13506 register, and it skips exactly that chip's reserved
offsets; its values decode by that chip's rules as 640 x 240 at 16 bits a pixel; the display
memory answers at +`0x200000`, where the chip's M/R# line puts it; and the firmware uses offsets
`0x004`/`0x005` and `0x008`/`0x009` as pin directions and pin data for the SD slot's lines and
lamps, which are that chip's GPIO registers. The S1D13806 has the same register map, so the source
gives the registers the S1D13506's names (`LCDC_LCD_HDISP`, `LCDC_BLT_CTRL0`, `LCDC_LUT_DATA`, ...).
What sets the two apart is the memory. `LcdControllerInit` clears `0x140000` bytes of it, exactly
1280 KB, and probes of the Pinball Fantasies port on the unit read the rest: PFT16 found its own
words at display memory `0x07FFF0` and `0x0FFFF0` and `0xFFDF` at `0x17FFF0` and `0x1FFFF0`, and
PFT17 read `REG[00Ch]` = `0x20`, whose MD[7:6] = 00 would mean 512 KB on an S1D13506. The
S1D13806's technical manual gives 1280 KB of embedded memory, which needs no MD setting
([Display Subsystem]({{ site.baseurl }}/kn7000-display-subsystem/#lcd-hardware)). Two routines nothing calls,
`LcdControllerInitAlt` and `LcdControllerInitOld`, program other register maps; Alt's fit
the earlier S1D13505, Old's is unidentified. See also
[Display Subsystem]({{ site.baseurl }}/kn7000-display-subsystem/).

### The older link

Bytes `0x0011`-`0x03FF` are from an earlier link of the same program that the new one did not
overwrite: the end of its NMI handler, its own Reset (`OldReset`), its cache routines and its
`.data` image. Nothing in this ROM reaches them, and their targets outside these bytes are
that link's addresses (`OldLink_*` in the source). The last routine is cut off at `0x400`,
where the new `.data` image starts.

## How the source is made

`kn7000/tools/gen_ic18_s.py` decodes with MAME's `unidasm` at each byte's run address, by
recursive descent from the vectors, the two thunks and `BootMain`, through the 12 indirect
transfers (four `switch` tables, three hashed `{key, handler}` tables, the interrupt handler
table, a table of 11 routine pointers and a routine-pointer variable), then decodes every gap
in a code range as unreferenced code. It keeps a mnemonic only if `kn7000/tools/mn10300_asm.py`
re-encodes the exact bytes. A routine with a prologue is named at its `movm`, and `call`
enters past it, at `NAME_entry`. Names come from `kn7000/kn7000_ic18.sym`, then from the
firmware: routines whose code is the same as a named routine of program 941 take its name.

Every memory operand that names a device register is an `.equ`. On 2026-10-24
`kn7000/notes/ic18-boot-rom-probes/leftovers.py` found 0 numeric memory operands left (down
from 222) and 193 bytes of `.byte` lines without a comment, under 23 labels, down from 422.
Still open: `LcdOldPaletteA`/`B` (they depend on the unidentified map), `OldDataImage` (the
older link's `.data`), the layout of `LocaleNumericC` / `LocaleMonetaryC`, and what
`FatMountFailImage`'s numbers were meant to be. Four register placeholders keep a TODO each:
`UNKNOWN_32000010`, `UNKNOWN_34004002`, `TGA_04` and `TGA_10`.

## The rest of IC18: rhythm data

From `0x10000` the chip holds the style data the firmware reads: the `"Technics Rhythms"`
resource at `0x40010000`, which the firmware's probe finds at its third candidate address. It
holds a header (signature, a 16-bit sum of the middle 2 MB, five offsets), a 2048-entry style-ID
index, **169 styles of 20 variations each**, 8 count-in patterns, the leftovers of an older build
and the version string `"jkr_33.ssf"` at `0x3FFFE8`, which the SP7001 DEBUG TOOLS screen shows as
RHYTHM 33. Since 2026-10-29 that part is byte-exact too: `kn7000/src/ic18/rhythm.s` and one file
per style under `kn7000/src/ic18/styles/` type every record and every event, and
`kn7000/src/ic18/ic18.s` (`boot.s` plus `rhythm.s`) rebuilds all 4 MB:

    make -C kn7000 verify-ic18-full   # src/ic18/ic18.s -> build/kn7000_ic18.bin, compared with the whole chip

`make gate-kn7000` runs it beside `verify-ic18`. The format is on its own page,
[Rhythm ROM (IC18): the style data]({{ site.baseurl }}/kn7000-rhythm-rom/).
