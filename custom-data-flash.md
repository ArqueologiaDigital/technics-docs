---
layout: page
title: Custom Data Flash
permalink: /custom-data-flash/
---

# Custom Data Flash Organization

The Custom Data Flash is a 1 MB flash device at IC19, mapped at **0x300000-0x3FFFFF**. It stores user-writable data: custom accompaniment styles, three banks of sound-parameter settings, LCD wallpaper screenshots, and the compressed SubCPU payload.

## Hardware

The firmware identifies the chip via the AMD unlock command sequence and accepts
manufacturer ID `0x0001` (AMD) or `0x0004` (Fujitsu) with any of four device IDs:

| Device ID | Part | Size | Boot block |
|---|---|---|---|
| `0x2223` | AM29F400BT | 4 Mbit | top |
| `0x22AB` | AM29F400BB | 4 Mbit | bottom |
| `0x22D6` | AM29F800BT | 8 Mbit | top |
| `0x2258` | AM29F800BB | 8 Mbit | bottom |

> **Correction (August 2026).** This page and the disassembly source previously named the
> part **AM29LV800B** and listed only the two 4 Mbit IDs. Both are wrong: `0x2223`/`0x22AB`
> are the 4 Mbit **AM29F400B**, the two 8 Mbit IDs were omitted, and the family is the 5 V
> AM29F400/800B rather than the 3.3 V AM29LV. The service-manual parts list gives IC19 as
> 8 Mbit (house number `QV1GFKN5KAX1`), which matches the 1 MB window exactly — the largest
> supported population fills it, so no bank switching is possible or needed.

IC19 is a single ×16 device on the 16-bit bus: the firmware's unlock writes go to
`base + 0xAAAA` and `base + 0x5554`, i.e. 2 × the word address. (Contrast the `0x800000`
ROM pair, whose unlock cycles at `0x815554`/`0x80AAA8` are 4 × the word address —
two ×16 dies interleaved on a 32-bit bus.)

**Region-4 boards populate the slot with two 512 KB devices** at `0x300000` and
`0x380000`. Every flash command routine adds `0x80000` to its *command base* when the
target is ≥ `0x380000`; data reads and program-word writes stay linear across the whole
`0x300000-0x3FFFFF`. This is a per-die command base, **not** a bank window. MAME's `AREA`
dip switch offers no Region 4 setting, so that path has never run under emulation.

The chip is programmed from the "initial data disk" during factory setup.

## ROM Layout

| Address Range       | Size  | Contents                                                                                   |
|:--------------------|:------|:-------------------------------------------------------------------------------------------|
| `0x300000-0x3167FF` | 90KB  | Section 0: Custom Style Data                                                               |
| `0x316800-0x3197FF` | 12KB  | Erased: unused end of section 0's area                                                     |
| `0x319800-0x3467FF` | 180KB | Sections 1-2: Custom Style Data                                                            |
| `0x346800-0x3497FF` | 12KB  | Erased                                                                                     |
| `0x349800-0x3767FF` | 180KB | Sections 3-4: Custom Style Data                                                            |
| `0x376800-0x3797FF` | 12KB  | Erased                                                                                     |
| `0x379800-0x3A67FF` | 180KB | Sections 5-6: Custom Style Data                                                            |
| `0x3A6800-0x3AFFFF` | 38KB  | Unused (erased)                                                                            |
| `0x3B0000-0x3B0FFF` | 4KB   | Section 7: block slot store — header and owner maps ([below](#section-7-block-slot-store)) |
| `0x3B1000-0x3BFFFF` | 60KB  | Section 7's slots (erased in the factory image)                                            |
| `0x3C0000-0x3D2FFF` | 78KB  | LCD Wallpaper/Screenshot Storage                                                           |
| `0x3D3000-0x3D3FFF` | 4KB   | Sound-parameter user banks (`CustomData_SndParamBanks`)                                    |
| `0x3D4000-0x3DFFFF` | 48KB  | Unused (erased)                                                                            |
| `0x3E0000-0x3FFFFF` | 128KB | Compressed SubCPU payload — **blank in our dump**, see below                               |

The erased runs are the unused ends of the style areas: each one stops where the next section begins (`0x319800`, `0x349800`, `0x379800`). They fall inside 64 KiB sectors and have nothing to do with the boot block.

## Section 7: block slot store

Section 7 (`FLASH_SECTION_PTR_7`, RAM `0x0C92` = `0x3B0000`) was long described as "SubCPU performance data".
It is a slot store: the main CPU keeps blocks from its RAM work area at `0x1E0000` there, and the whole 64KB
sector is used.

| Offset | Contents |
|:---|:---|
| `+0x00` | `"H",0,"K",0` header; word `+0x08` = 40 and word `+0x0A` = 4, the slot counts |
| `+0x10` | 40 owner bytes, one per small slot (0 = free) |
| `+0x50` | 4 owner bytes, one per large slot |
| `+0x410` | 40 small slots of 470 bytes |
| `+0x4D80` | 4 large slots of 10,535 bytes (to `+0xF21C`) |

The v10 routines (`storage/flash_floppy_handlers.s`):
- `Flash_CountFreeOrOwnedSlots` counts the free or owned slots of each size.
- `Flash_AssignSlotsToBlocks` builds the assignment list at RAM `0x7A0`.
- `Flash_WriteSlotOwnerMap` writes the owner bytes.
- `Flash_CopyBlocksToSlots` copies the blocks into the sector's RAM image and rewrites the sector.

`FileIO_LoadRcmToFlash` loads the `.RCM` file's last `0xF400`-byte chunk over this sector, which covers every
slot. The evidence is in `analysis/kn5000-naming/proposals-2026-10-06-helpers-g.json` in the disassembly
repository. The factory image holds only the header; the slots are erased.

## Section Pointer Table

The firmware computes 8 section pointers at runtime (`Flash_InitExtMemAddrs` in main CPU ROM) and stores them in internal RAM:

| Section | Address | RAM Ptr | Contents |
|:---|:---|:---|:---|
| 0 | 0x300000 | 0x0C76 | Custom accompaniment styles |
| 1 | 0x319800 | 0x0C7A | Custom accompaniment styles |
| 2 | 0x330000 | 0x0C7E | Custom accompaniment styles |
| 3 | 0x349800 | 0x0C82 | Custom accompaniment styles |
| 4 | 0x360000 | 0x0C86 | Custom accompaniment styles |
| 5 | 0x379800 | 0x0C8A | Custom accompaniment styles |
| 6 | 0x390000 | 0x0C8E | Custom accompaniment styles |
| 7 | 0x3B0000 | 0x0C92 | Block slot store ([below](#section-7-block-slot-store)) |

The RAM pointers are named in the source (each maincpu tree's `shared/ram_variables.s`, the same
addresses in v7): `FLASH_SECTION_PTR_0` .. `FLASH_SECTION_PTR_7`. The same routine also sets
`RHYTHM_PATTERN_BUF_PTR` (`0x0C6E`) to the rhythm pattern buffer A (`0x94800`).

## "HK" Header Format

Sections 0-7 begin with an `H`, `K` magic in 16-bit characters. In the style sections (0-6) it opens a 96-byte header, and the style directory follows at +0x60 (below):

| Offset | Size       | Value  | Description                                                                                                                  |
|:-------|:-----------|:-------|:-----------------------------------------------------------------------------------------------------------------------------|
| +0x00  | word       | 0x0048 | 'H' (16-bit)                                                                                                                 |
| +0x02  | word       | 0x004B | 'K' (16-bit)                                                                                                                 |
| +0x04  | 4 bytes    | varies | Flags/configuration                                                                                                          |
| +0x08  | 0x58 bytes | varies | rest of the header (in section 7, the slot counts at +0x08 / +0x0A and the owner maps, [above](#section-7-block-slot-store)) |

Each style section (0-6) holds **one style**. The 30 records at section base + 0x60 are not 30 styles: they are the 30 sections of that one style, indexed by `STYLE_SECTION` 0..29 (variations a/b/c 1-4 = 0..11, then intros, fill-ins and endings 1-2 = 12..29; `AccPatch_GetCurrentSlotAddr`, `RHYTHM_PATTERN_BUF_A + 0x60 + 0x60 * n`). The default image `Demo_StyleRhythmData` names them "a-variation1" .. " c-ending 2". The names a bank holds, such as "Bolero puro" four times, are the names of the patterns each section was taken from. Earlier revisions of this page, and the floppy-format comments, called the records "styles" and counted 210 styles; the firmware's indexing says 7 styles of 30 sections. Each record is 96 bytes, with a 16-character name at record +0x40 and the section's cell-chain pointers at +0x00 and +0x04..+0x0A. The music follows in 256-byte cells, each with an `80 PREV NEXT 87` header, an event stream and a trailing `87`, the same event language as the factory styles in the [Rhythm ROM (IC14)]({{ site.baseurl }}/rhythm-rom/).

The whole bank, header and directory included, is typed in the listings `custom_data/styles/*.styles` (listing format 2 of [`scripts/build/style_events.py`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/scripts/build/style_events.py), whose docstring section BANK LAYOUT gives the evidence for every field). No `RAW` block is left. `kn5000_custom_data.s` emits each bank as one generated `.incbin` of the listing's output (`CustomData_Section_0` .. `_6`), so the listing is the only source; `style_events.py verify` round-trips all five banks, and `make style-midi` exports each section as a Standard MIDI File. The format is documented in `docs/accompaniment-style-format.md` in the disassembly repository.

| bank offset  | listing line                                                                          | evidence                                                                                                                                                 |
|--------------|---------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| +0x00        | `BANK b`                                                                              | the `"H\0K\0"` magic                                                                                                                                     |
| +0x04        | `hdr_04` (26 B hex)                                                                   | not established; the same in every IC19 bank and in all seven sections of the initial-data disk's `.RCM`                                                 |
| +0x1e        | `capacity16` 0x1680                                                                   | [inference] 0x16800 / 16, the section size                                                                                                               |
| +0x20..+0x2b | `dir_offset`, `record_size`, `record_count`, `cell_size`, `cell_count`, `name_offset` | constants in every bank and in `Demo_StyleRhythmData`; [inference] by value (30 = the `cp a, 0x1e` in `AccDemo_LoadVariation`)                           |
| +0x2e        | `used_size16`                                                                         | written by `AccPatch_InitSlotChain`; read by `cmp_sv_mae` (.CMP size) and `FileIO_SaveRcmFromFlash` (.RCM chunk length = `+0x2e * 16` in all 7 sections) |
| +0x60        | `SECTION k parts=... w02=... name="..."`                                              | the 30 `STYLE_SECTION` records, in the order of `AccDemo_LoadVariation_EntryLoop_Data`                                                                   |
| rec +0x0c    | `rec_0c` (12 B), `part0..part4` (4 x u16 each)                                        | `AccDemo_LoadVariation` copies 0x34 B here; the 12 + 5 x 8 split is [inference] by shape                                                                 |
| rec +0x50    | `tail`                                                                                | `AccDemo_SectionRecordTail`                                                                                                                              |
| +0xba0       | `data_ba0`                                                                            | `AccDemo_LoadVariation_DataBlock` (160 B) and the table after it; zero in every factory bank                                                             |
| +0x13c0      | `FILLIN mark= prev= next=` + events                                                   | `AccDemo_LoadFillIn` copies 0x40 B here: a 64-byte cell, `80 ffff ffff 87`, eight beats, end                                                             |
| +0x1400      | `CELL b mark= prev= next=`, then `CHAIN` events                                       | `AccPatch_InitSlotChain` (base + 0x1400; 150 head entries = 30 sections x 5 parts, continuation cells from +0xaa00)                                      |

The area between the directory and block 20 is therefore not unknown: zero up to +0x13c0, then a 64-byte fill-in cell. A bank in IC19 and a section of the initial-data floppy's `01CTMINI.RCM` have the same format: the header +0x00..+0x2d is byte-identical in all seven, and the directory pointers agree in their low 12 bits (the high nibble is 0 in the file and section + 1 in flash, stamped by the loader); only the music differs. Still unnamed: header +0x04..+0x1d, each record's 0x34-byte parameter block and 16-byte tail, and the meaning of the five parts. Source: `notes/kn5000-existing-includes-2026-10-29/README.md` in the disassembly repository.

## LCD Wallpaper Storage (0x3C0000)

77,824 bytes for capturing the LCD screen contents:
- **76,800 bytes**: 320x240 pixel image at 8bpp (one pixel per byte)
- **1,024 bytes**: its palette, stored after the pixels (see below)

Zero-filled in factory state.

Loaded from disk by `Gfx_LoadSplashBMP` (`0xFAE86D`) and written by `Flash_SaveSplashScreen`
(`0xFAF00B`). Three details differ from a plain BMP copy, established 2026-08-02:

- the **palette is stored after the pixels**, not before — pixels occupy `0x3C0000`–`0x3D2BFF`
  and the palette `0x3D2C00`–`0x3D2FFF`;
- rows are un-flipped to **top-down** on the way in;
- palette entries are reordered **BGR0 → RGB0**.

`CaptureLcd` (`0xFAF030`) writes the reverse, emitting `bfSize = 0x13036` = 77,878 bytes — exactly
the size of the five `.bmp` files on the Initial Data Disk, which are therefore in the instrument's
**own screenshot format** rather than an arbitrary external one.

## Installing an Initial Data Disk (`.RCM`) — the loader rewrites as it writes

The disk-menu path reaches the loader through the extension table at `0xEA0340`–`0xEA0367`
(10 entries, reverse order; `RCM` is index 6, labelled "RHYTHM CUSTOM"):
`FileIO_ReadHeader` `0xF891AB` → `ParseFileExtension` `0xF896F0` → the RCM read
wrapper `FileIO_LoadRegion6_Simple` `0xF87913` → the loader `FileIO_LoadRcmToFlash` at
`0xF186A9`. The export-table entry `rcm_ld_XAPR_j` (`0xF1EB28`) jumps to
`FloppyDisk_LoadNoteEvents` (`0xF18A74`), the same algorithm with I/O callbacks.

Eight chunks are copied straight through, with no permutation. Lengths come from a table at
file `+0x40`, whose entry 0 is the header size and whose entry 8 is never read — **the final block
uses a hard-coded `0xF400`**, and `0x63800 + 0xF400 = 0x72C00`, exactly EOF:

| file offset | length | flash section | base |
|---|---|---|---|
| `0x000400` | `0xE000` | 0 | `0x300000` |
| `0x00E400` | `0xE000` | 1 | `0x319800` |
| `0x01C400` | `0xDC00` | 2 | `0x330000` |
| `0x02A000` | `0xF400` | 3 | `0x349800` |
| `0x039400` | `0xE000` | 4 | `0x360000` |
| `0x047400` | `0xD400` | 5 | `0x379800` |
| `0x054800` | `0xF000` | 6 | `0x390000` |
| `0x063800` | `0xF400` (hard-coded) | 7 | `0x3B0000` |

> **The payload is not written verbatim.** `NoteEventBuffer_Store` (`0xF17189`) calls
> `PartGrid_ColumnDispatch_Default` (`0xF17001`) before any flash access, which walks 30
> records of `0x60` bytes at `base + 0x60 + 0x60n` and rewrites fields 0, 2, 3, 4 and 5
> through `Pack12BitValueWithBank` (`0xF1710C`):
>
> ```
> v = (v == 0xFFFF) ? v : ((k+1) << 12) | (v & 0x0FFF)
> ```
>
> The section index (1-based) is folded into the top nibble. `0xFFFF` is left alone, and the
> `0x60`-byte section header is untouched.

**The control that proves it:** section 7 never takes that path, and file section 7 is
byte-identical to chip `0xB0000`–`0xBEFFF`. One section transformed, one not, both as predicted.

Erase is **per-sector, never chip-wide** — twelve 64 KiB sectors covering `0x300000`–`0x3BFFFF`
only. Wallpaper (`0x3C0000`), the sound-parameter banks (`0x3D3000`) and the SubCPU payload (`0x3E0000`) are not
touched by a disk install.

> **Contrast with the KN6000/KN6500/KN7000**, whose `.AST` payload *is* written verbatim, at flash
> offset `0x20000`. Only the KN5000 stamps. See [ROM Dumping Roadmap]({{ site.baseurl }}/rom-dumping-roadmap/) and
> [KN7000 Initial Data]({{ site.baseurl }}/kn7000-initial-data/).

## Sound-Parameter User Banks (0x3D3000)

> **Corrected (September 2026).** This section used to call the region "Registration Memory",
> holding the user's PANEL MEMORY registrations, with a "Registration Object Table system" that
> serialised every registered parameter to it. Nothing in the code supports that. The hdae lane
> traced the region's readers and writers while typing the custom-data source: it holds **three
> user banks of sound-parameter settings**. Panel Memory lives in battery-backed SRAM (the
> factory loaders build 960-byte records at RAM `0x1ED400`; see
> [Panel Memory Factory Data]({{ site.baseurl }}/panel-memory-factory-data/)).
> `RegObjTable` / `RegObjTabl` register the UI's object tables
> ([UI Framework]({{ site.baseurl }}/ui-framework/#module-numbers-and-the-object-table)), not
> saveable parameters.

| Offset                         | Contents                                                                                                                                                                               |
|:-------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `+0x000`                       | 16-byte header, starting `"HK "`                                                                                                                                                       |
| `+0x010` / `+0x110` / `+0x210` | banks 0 / 1 / 2: 39 six-byte entries `{u32 RAM address, u8 b4, u8 b5}` = 234 (`0xEA`) bytes, padded with `0xFF` to the next 0x100                                                      |
| `+0x400`                       | a 0x50-byte option block, written with the defaults; `SndParamBank_LoadOptionBlock` copies it to RAM `0x340E4`.., and `SndParamBank_RestoreOptionBlock` rebuilds it on a factory reset |

Readers and writers (v10):

- `SndParam_GetBlockPointer` returns ROM records for parameter blocks 0..0x18 and
  `0x3D3010` / `0x3D3110` / `0x3D3210` for blocks 0x1B / 0x1C / 0x1D, the three user banks.
- `SndParam_AllocAndCopyPreset` writes 0xEA bytes to a bank with `FlashWrite`.
- `SndParamBank_CheckFlash` / `SndParamBank_WriteFlashDefaults`: when the first 3 bytes differ from the ROM
  default (`0xED933A`), they write the defaults (header + bank 0 from `0xED933A`, banks 1-2 from
  `0xED9434` / `0xED951E`) and the 0x50-byte block at `+0x400`.
- `SndParam_ApplyBaseBlock` applies a bank's first 23 entries (RAM addresses `0xF9C2`,
  `0xF9DC`, … on a 0x1A stride), and `SndParam_ApplyMaskBlock` the other 16 (addresses
  `0xFD50`-`0xFD5C`); the next bullet gives how each half writes. Both skip entries whose
  address is 0; in this dump entries 36-38 are unused.
- *(Corrected 2026-10-06, from the code.)* The two halves are applied differently.
  `SndParam_ApplyBaseBlock` (entries 0-22) does not mask: it writes `addr[0] = (addr[0] & 0xF8) | b4` and
  `addr[1] = b5` -- the low 3 bits of payload byte 12 and the whole of byte 13 (the part/routing byte; see
  [Panel Memory Factory Data]({{ site.baseurl }}/panel-memory-factory-data/)) of the 23 part records
  `0x00`-`0x0F`, `0x19`, `0x10`-`0x15`. Only `SndParam_ApplyMaskBlock` (entries 23-38) is
  `*addr = (*addr & ~b4) | b5`: tag `0x80` payload bytes 0-12, and in 9 of the 25 ROM presets also tag
  `0x70` bytes 0-1 (`0xFD02`/`0xFD03`, entries 36-37).
- The 25 ROM presets (`SndParam_PresetBanks`, `sound_config_lookup.c`) and the three factory defaults
  (`SndParamBank_Default0`-`2`, `naka_extension_device.c`) are typed in C as `snd_param_base_entry_t[23]`
  + `snd_param_mask_entry_t[16]`, each entry annotated with the record byte it sets
  (`scripts/converters/sndparam_bank_retype.py`). The routines above are now `SndParamBank_CheckFlash` /
  `SndParamBank_WriteFlashDefaults`; the 0x50-byte block at `+0x400` is copied to RAM `0x340E4`.. by
  `SndParamBank_LoadOptionBlock` and rebuilt on a factory reset by `SndParamBank_RestoreOptionBlock`.

In the IC19 dump the header and bank 0 differ from the ROM default in 14 of 0xFA bytes, values
only: the unit's user had edited them. Source: the `CustomData_SndParamBanks` header in
`custom_data/kn5000_custom_data.s`. The main-CPU routines still use the numeric addresses
`0x3D3000`-`0x3D3400`; making them cross-ROM symbolic references is an open lead of the hdae lane.

## Compressed SubCPU Payload (0x3E0000)

The 128 KB region at `0x3E0000-0x3FFFFF` is where a File Type 007 ("Program DATA FILE
PCK") update disc writes the compressed SubCPU executable payload — verbatim, as a raw
SLIDE4K stream, exactly `0x20000` bytes after erasing the two sectors. It is **not** a
transient staging area: `SubCPU_Send_Payload` decompresses it on **every** boot, and the
table-data `0x800000` source is only a fallback taken when the `SLIDE` magic check fails.

> **In the IC19 dump this project holds, this entire region is `0xFF`** — 131,072 blank
> bytes, and the string `SLIDE` appears nowhere in the 1 MB image. Since every dumped
> firmware version reaches this branch (marker byte `0xFFFEED` = `0xFF` in v7, v9 and
> v10), a machine matching our dumps could not start its sub-CPU. Whether the region was
> never programmed on that unit or the dump is simply incomplete is **unresolved** — see
> [Sub-CPU Payload Provenance]({{ site.baseurl }}/subcpu-payload-provenance/) for the
> evidence and for the two free measurements that would settle it.
>
> The MAME driver supplies the missing bytes with a per-BIOS `ROMX_LOAD` overlay of the
> compressed payload: v1.42 for the v10 and v9 BIOSes, v1.41 for v8 and v7, v1.40 for v6
> and v5. Address, form and content all match what a real install writes; only the
> acquisition path is indirect.

## Flash Programming

The main CPU ROM contains dedicated flash management routines:
- `Flash_IdentifyChip` (0xEF3724): Detects flash chip type using AMD command protocol
- `Flash_IdentifyAndValidateChip` (0xEF379A): Validates chip ID against known device IDs
- `Flash_BurnWithProgress` (referenced by floppy update handlers): Programs flash sectors with progress indication

The flash programming uses the standard AMD byte-programming algorithm with polling for completion.
