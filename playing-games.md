---
layout: page
title: "Playing Games on MAME"
permalink: /playing-games/
---

# Playing Games on the KN5000 in MAME

This guide walks you through running homebrew games on the Technics KN5000 using the MAME emulator. No physical hardware required.

## What You Need

| Item | Source |
|------|--------|
| **MAME** (with KN5000 driver) | Build from source: see [Building MAME](#building-mame) below |
| **Original KN5000 ROM dumps** | Dump from your own KN5000 keyboard (see [Help Wanted]({{ site.baseurl }}/help-wanted/)) |
| **Game source code** | See individual game sections below |

> **Which MAME.** The base KN5000 driver is in upstream `mamedev/mame`, so a plain upstream
> checkout has it. The homebrew walkthroughs below are developed against the driver overlay
> repository (kn7000_mame), which is ahead of upstream. Another World and Mines rely on custom
> ROM images and the HDAE5000 extension slot, which upstream has. If one of them does not work on
> a plain upstream checkout, try the overlay. The App Loader always needs the overlay: it reads
> its disk through the HD-AE5000's hard-disk (ATA) interface, which only the overlay emulates
> (upstream's ATA registers read 0).

## Building MAME

```bash
git clone https://github.com/mamedev/mame.git
cd mame

# Incremental build (KN5000 driver only — much faster than full MAME)
make -j$(nproc) SOURCES=src/mame/matsushita/kn5000.cpp
```

This produces a `mame` binary in the current directory.

## ROM Setup

The KN5000 driver expects ROM files in a `kn5000/` directory within your ROM path. The required files are:

| Filename | Size | Description |
|----------|------|-------------|
| `kn5000_v10_program.rom` | 2 MB | Main CPU firmware |
| `kn5000_subcpu_boot.ic30` | 128 KB | Sub CPU boot ROM |
| `kn5000_subprogram_v142_compressed.rom` | ~93 KB | Sub CPU payload (compressed) |
| `kn5000_rhythm_data_rom.ic14` | 4 MB | Rhythm/waveform data |
| `kn5000_custom_data_rom.ic19` | 1 MB | Custom data |
| `kn5000_table_data_rom_even.ic3` | 1 MB | Table data (even bytes) |
| `kn5000_table_data_rom_odd.ic1` | 1 MB | Table data (odd bytes) |
| `kn5000_waveform_rom.ic307` | 4 MB | Waveform ROM |

Place these in a directory structure like:

```
/path/to/roms/kn5000/
  kn5000_v10_program.rom
  kn5000_subcpu_boot.ic30
  ...
```

### Quick Test — Boot the Firmware

```bash
./mame kn5000 -rompath /path/to/roms -window -skip_gameinfo
```

You should see the KN5000 control panel with the LCD displaying the startup screen.

![KN5000 firmware startup screen in MAME]({{ site.baseurl }}/assets/images/tutorial/firmware-boot.png)
*The KN5000 firmware fully booted in MAME, showing the default Panel Memory screen with instrument assignments and rhythm levels.*

---

## Game 1: Another World

A port of Delphine Software's *Another World* (1991) running natively on the KN5000. The original Amiga bytecode VM is reimplemented in TLCS-900/H2 assembly, executing unmodified game data on the keyboard hardware.

See: [Another World VM technical details]({{ site.baseurl }}/another-world-vm/)

### Prerequisites

- [ASL Macro Assembler](http://john.ccac.rwth-aachen.de:8000/as/) (`asl` and `p2bin`)
- Original *Another World* game data files (DOS version)
- Python 3 (for resource extraction)
- A checkout of [kn5000-roms-disasm](https://github.com/ArqueologiaDigital/technics-roms-disasm). The build includes the ASL sources in its `archive/asl/` tree; pass its location as `DISASM_REPO` (default `../../kn5000-roms-disasm`).

### Build

```bash
git clone https://github.com/felipesanches/technics-anotherworld.git
cd technics-anotherworld

# Place your Another World DOS game files in game_data/MSDOS/
# Required: BANK*, MEMLIST.BIN

make ORIGINAL_ROMS=/path/to/roms/kn5000 ROMSET_BASE=/path/to/custom-roms/anotherworld \
     DISASM_REPO=/path/to/kn5000-roms-disasm ASL_PATH=/path/to/asl
```

This builds a custom main CPU ROM with the game replacing the firmware, and assembles a MAME ROM set. The Makefile copies `kn5000_subprogram_v142.rom`, but MAME's kn5000 loads the compressed sub-CPU payload `kn5000_subprogram_v142_compressed.rom`, so copy that file from your ROM dumps into `ROMSET_BASE/kn5000/` yourself.

### Run

```bash
# Standalone ROM (replaces firmware — game runs directly from boot)
./mame kn5000 -rompath /path/to/custom-roms/anotherworld -window -skip_gameinfo

# Or use the Makefile shortcut (with the same ROM paths as for the build):
cd technics-anotherworld
make test ORIGINAL_ROMS=/path/to/roms/kn5000 ROMSET_BASE=/path/to/custom-roms/anotherworld
```

The game starts immediately — the intro cinematic plays on the KN5000's LCD.

![Another World running on the KN5000 in MAME]({{ site.baseurl }}/assets/images/tutorial/another-world.png)
*Another World's intro cinematic rendered on the KN5000 LCD via the MAME emulator.*

### Extension ROM Mode

An HDAE5000 extension build (`make extension`) also compiles, but it cannot run the game: the game's 974 KB of resources do not fit in the 512 KB extension ROM, so at most the intro could. Its ROM is written as `hd-ae5000.ic4`, which must be renamed to `hd-ae5000_v2_06i.ic4` for MAME to load it, and it is tested with `make test TARGET=extension` (plain `make test` runs the main-CPU build).

---

## Game 2: Minesweeper

A custom Minesweeper game written in C, compiled with the LLVM TLCS-900 backend. Runs as an HDAE5000 extension ROM — the original firmware boots normally, and the game is activated from the DISK MENU.

See: [HDAE5000 Homebrew Development]({{ site.baseurl }}/hdae5000-homebrew/)

### Prerequisites

- [LLVM with TLCS-900 backend](https://github.com/felipesanches/llvm-project/tree/tlcs900_backend) (`clang`, `llc`, `llvm-link`, `ld.lld`, `llvm-objcopy`)
- Python 3 (`tools/generate_tiles.py` makes the tiles and palette; `tools/patch_icon.py` adds the mine icon to the ROM set's table-data ROMs)

### Build

```bash
git clone -b kn5000_port https://github.com/ArqueologiaDigital/Mines.git
cd Mines/platforms/kn5000
make LLVM_BIN=/path/to/llvm-project/build/bin ORIGINAL_ROMS=/path/to/roms/kn5000 ROMSET_BASE=/path/to/mines/romset
```

### Run

```bash
./mame kn5000 \
  -rompath /path/to/mines/romset \
  -extension hdae5000 \
  -window -skip_gameinfo
```

### Activating the Game

After MAME boots the firmware:

1. Press the **`MENU: DISK`** button (top-right area of the control panel — that is the name
   it carries in MAME's input list)
2. Navigate the DISK MENU — look for the **Mines Game** entry with a mine icon
3. Select it to launch the game

The game renders on the KN5000 LCD: a green border, red minefield, and yellow tile markers.

![Minesweeper running on the KN5000 in MAME]({{ site.baseurl }}/assets/images/tutorial/mines-game.png)
*Minesweeper game rendering on the KN5000 LCD. The green border, red minefield grid, and yellow tile markers are drawn by the HDAE5000 extension ROM.*

> **Note:** The game currently requires MAME's `-seconds_to_run` flag or a Lua script to automate activation for headless testing. For interactive play, just navigate the DISK MENU as described above.

---

## Game 3: App Loader

A generic program launcher that loads applications from a FAT16 hard disk image. Multiple games can be installed on a single disk.

See: [App Loader documentation]({{ site.baseurl }}/app-loader/)

### Prerequisites

- [LLVM with TLCS-900 backend](https://github.com/felipesanches/llvm-project/tree/tlcs900_backend) (`clang`, `llc`, `llvm-link`, `ld.lld`, `llvm-objcopy`)
- Python 3 (`tools/create_disk.py` writes the FAT16 image)
- The App Loader source, `custom-kn5000-roms/apploader/`, which has not been published yet
- MAME built from the driver overlay (upstream's HD-AE5000 has no working ATA)

### Build

```bash
cd custom-kn5000-roms/apploader
make
```

### Run

```bash
./mame kn5000 \
  -rompath /path/to/apploader/romset \
  -extension hdae5000 \
  -hard /path/to/disk.hd \
  -window -skip_gameinfo
```

> **Disk format:** Use raw `.hd` disk images, not CHD format. If you have a `.img` file: `cp disk.img disk.hd`

### Using the Menu

After the firmware boots and the DISK MENU loads the App Loader:

- **`RIGHT 2`** (PART SELECT, port `CPR_SEG4`; MAME has a second `RIGHT 2`, the LCD soft key on `CPL_SEG8`) / **`CONDUCTOR: RIGHT 2`**: move the selection up / down
- **`VARIATION 1`**: launch the selected app
- **`EXIT`**: leave the App Loader

---

## Controls Reference

The KN5000 has no joystick or D-pad. The games use panel buttons instead: PART SELECT's `RIGHT 2` and the CONDUCTOR buttons for directions, VARIATION 1 and 4 as action buttons, and `EXIT`; Another World also reads `HELP` and `OTHER PARTS/TR` (see [Another World — Input System]({{ site.baseurl }}/another-world-vm/#input-system) and [HDAE5000 Homebrew — Button Mapping]({{ site.baseurl }}/hdae5000-homebrew/#button-mapping)). The LCD soft keys select menu items, such as the DISK MENU entry that starts Mines. In MAME, these map to keyboard keys.

To see or change key bindings, press **Tab** in MAME and go to **Input (This Machine)**. The
keys are listed there under these exact names, on these ports:

| Name in MAME            | Port · mask        |
|-------------------------|--------------------|
| `LEFT 1`                | `CPL_SEG10` `0x02` |
| `LEFT 2`                | `CPL_SEG10` `0x01` |
| `LEFT 3`                | `CPL_SEG9` `0x04`  |
| `LEFT 4`                | `CPL_SEG9` `0x02`  |
| `LEFT 5`                | `CPL_SEG9` `0x01`  |
| `RIGHT 1`               | `CPL_SEG8` `0x04`  |
| `RIGHT 2`               | `CPL_SEG8` `0x02`  |
| `RIGHT 3`               | `CPL_SEG8` `0x01`  |
| `RIGHT 4`               | `CPL_SEG7` `0x02`  |
| `RIGHT 5`               | `CPL_SEG7` `0x01`  |
| `EXIT`                  | `CPL_SEG7` `0x08`  |
| `MENU: DISK`            | `CPR_SEG10` `0x20` |
| `RIGHT 2` (PART SELECT) | `CPR_SEG4` `0x02`  |
| `CONDUCTOR: LEFT`       | `CPR_SEG4` `0x10`  |
| `CONDUCTOR: RIGHT 2`    | `CPR_SEG4` `0x20`  |
| `CONDUCTOR: RIGHT 1`    | `CPR_SEG4` `0x40`  |
| `VARIATION 1`           | `CPL_SEG4` `0x01`  |
| `VARIATION 4`           | `CPL_SEG4` `0x08`  |
| `HELP`                  | `CPL_SEG10` `0x04` |
| `OTHER PARTS/TR`        | `CPL_SEG10` `0x08` |

None of these has a default key assignment, so assign the ones you need before playing.

---

## Troubleshooting

### "THIS SYSTEM DOESN'T WORK" warning

This is normal — the KN5000 driver is still in development. MAME skips the warning when `-seconds_to_run N` is given with N ≤ 300, or with `-video none`; `-skip_gameinfo` alone does not skip it. For interactive use, just press any key to dismiss it.

### No sound

Upstream MAME's KN5000 makes no sound (`MACHINE_NO_SOUND`): the tone generator, DSP and waveform RAM are stubs. Only the driver overlay (kn7000_mame) has a tone generator, and even there many sounds are incomplete because IC304, IC305 and IC306 are undumped.

### ROM checksum mismatch warnings

If you're using custom ROMs (Another World, Mines), MAME will report checksum mismatches for the modified ROM files. This is expected — the game ROMs intentionally differ from the original firmware.

### Disk image not loading

- Use raw `.hd` format, not CHD (`.chd`)
- Ensure the image is a valid FAT16 filesystem
- Convert from `.img`: `cp disk.img disk.hd`

### Game doesn't appear in DISK MENU

- Make sure you passed `-extension hdae5000` to MAME
- The HDAE5000 extension ROM must be in the ROM set under one of the four names the device
  knows: `hd-ae5000_v1_10i.ic4`, `hd-ae5000_v1_15i.ic4`, `hd-ae5000_v2_01i.ic4` or
  `hd-ae5000_v2_06i.ic4` (the default BIOS selection is v2.06i)
- Press the **`MENU: DISK`** button to enter the DISK MENU

---

## For Developers

Want to write your own game for the KN5000? See:

- [HDAE5000 Homebrew Development]({{ site.baseurl }}/hdae5000-homebrew/) — full SDK and build pipeline
- [App Loader]({{ site.baseurl }}/app-loader/) — disk-based application framework
- [Another World VM]({{ site.baseurl }}/another-world-vm/) — full game port as reference
- [Display Subsystem]({{ site.baseurl }}/display-subsystem/) — framebuffer and palette details
- [Memory Map]({{ site.baseurl }}/memory-map/) — available address space
