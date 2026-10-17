---
layout: page
title: ROM String Analysis
permalink: /rom-strings/
---

# ROM String Analysis

This page documents meaningful strings found in each KN5000 ROM through systematic extraction and analysis. String analysis provides valuable insights into firmware functionality, menu systems, instrument databases, and communication protocols.

## Main CPU ROM (kn5000_v10_program.rom)

**Size:** 2MB (2,097,152 bytes)
**Load Address:** 0xE00000
**Total Strings Found:** 9,446

### Product Identification

⚠ **Corrected 2026-09 — the address and exact text below were wrong.** The string is
`KN5000 ~95 VOCALIST WORKSTATION` (no `Technics` prefix in this particular string) at
file offset `0x5957E`, CPU address **`0xE5957E`**, not `0xE023F0` (that address is
actually the start of the sound-category table below). A separate string,
`Technics KN5000 Program  DATA FILE 1/2`, exists near the very start of the ROM
(`0xE00038`).

| Location | String |
|----------|--------|
| 0xE5957E | `KN5000 ~95 VOCALIST WORKSTATION` |

This product ID string confirms the keyboard model and its "Vocalist Workstation" designation, indicating built-in vocal processing capabilities.

### Key String Tables

| Address  | Description                                                                                   | Count |
|----------|-----------------------------------------------------------------------------------------------|-------|
| 0xE023F0 | Sound categories (`SOUND_CATEGORY_NAMES`, 16 characters each)                                 | 18    |
| 0xEFF5B9 | Chord-type names (`Tbl_ChordTypeNames`, 5 characters each)                                    | 64    |
| 0xECFDFE | Part names (`VariScreen_PartNames`), 7 characters each (RIGHT1, RIGHT2, LEFT, PART4 … PART32) | 32    |

### String Categories

**Sound Names:**
- Only the 18 sound-category names (PIANO, GUITAR, STRINGS & VOCAL, BRASS, … DRUM KITS, MEMORY A, MEMORY B) are in this ROM. The names of the sounds themselves are in the Table Data ROM's tone database (see [Tone Database]({{ site.baseurl }}/tone-database/)).
- Instrument words such as "Flute" or "Clarinet" occur here only inside Music Stylist preset names ("Soulful Flute", "German Clarinet").

**Menu Text:**
- Main menu items (Sound, Rhythm, Sequencer, Disk)
- Sub-menu options (Edit, Copy, Delete, Save, Load)
- Dialog prompts ("Are You Sure?" with YES / NO buttons)
- Error messages, numbered up to `ERROR 64`, with their text in English, German, French, Spanish and Indonesian ("There is no disk in the disk drive", "An error has occurred while the disk was loading. Please try again!")

**Effects Names:**
- Reverb presets (Huge Room, Box Room, Small Plate, Sports Hall, Bright Hall, Dark Confines)
- Chorus/Delay effects
- EQ and filter settings
- DSP processing modes

**System Messages:**
- System error dialogs ("CAUTION!!", "\*\* ERROR in back-up SRAM \*\*", "\*\* ERROR in CPU data transmission \*\*")
- Factory test screens and their diagnostics ("LCD PANEL TEST", "FD SAVE/LOAD TEST", "Debug Test", "DEBUG SCREEN for HD-AE", "Media Error", "Not Enough memory!"); see [Test & Service Modes]({{ site.baseurl }}/test-modes/)

---

## Sub CPU Payload ROM (kn5000_subprogram_v142.rom)

**Size:** 192KB (196,608 bytes)
**Purpose:** Tone generator and audio synthesis control
**Total Strings Found:** 88

### Key Strings

| Address | String | Purpose |
|---------|--------|---------|
| 0x31E3 | `KN5000 SOUND RAM` | Memory region identifier |
| 0x31F4 | `User Kit` | User-defined drum kit designation |

### DSP Debug-Trace Messages

The sub CPU payload carries debug-trace message fragments for its DSP and effect routines (`v142/subcpu/subcpu_data_tables.s:2803-2881` in kn5000-roms-disasm): `DSP <n> reset.`, `anti reset.`, `mute.`, `antimute.`, `EFF <n> disconnect.`, `link.`, `headder` (sic), `change`, `data change`, `para<m> edit`, `vol`, plus `argo change` (sic). The routines that use them (`DSP_Reset_WithDebug`, `EFF_Disconnect`, `EFF_Link`, `DSP_AlgorithmChange` and others) print them through `Debug_Print_String`, which calls a boot-ROM routine. In the dumped boot ROM, that routine's character sink outputs nothing, so the messages never appear.

### String Distribution

Most strings in this ROM relate to:
- Audio buffer management
- DSP parameter control
- Waveform table identifiers
- Voice allocation messages
- MIDI processing states

---

## Sub CPU Boot ROM (kn5000_subcpu_boot.ic30)

**Size:** 128KB (131,072 bytes)
**Load Address:** 0xFE0000
**Total Strings:** 11

> ⚠ **The dump is incomplete.** MAME marks this ROM `BAD_DUMP`: the ranges `0xFE0800-0xFF7800` and `0xFF9800-0xFFF000`, about 89 % of it, were never read and are `0xFF` in the image. The string count and the observations below cover only the dumped part.

### Analysis

This boot ROM contains minimal strings, which is typical for embedded firmware:

- **ASCII Lookup Tables:** Character conversion tables for serial debugging
- **No Boot Messages:** The firmware does not output status messages during boot
- **No Version Strings:** Unlike application firmware, boot ROMs often lack version identification

The sparse string content indicates this ROM focuses on:
- Hardware initialization
- Memory testing
- Loading the main payload from the Main CPU
- Interrupt vector setup

---

## Table Data ROM (Interleaved Odd/Even)

**Total Size:** 2MB (1MB odd + 1MB even)
**Organization:** two ×16 chips on a 32-bit bus, word-interleaved: `kn5000_table_data_rom_even.ic3` holds bytes 0-1 of each 32-bit word, `kn5000_table_data_rom_odd.ic1` bytes 2-3

### Bass Instruments

The tone database names each sound individually and has no finer bass types. Tone records 210-229 (`ToneRec_210`..`ToneRec_229` in `table_data/tone_database_directory.s`) are one run of bass sounds: Acoustic Bass, Mellow Ac.Bass, Electric Bass, Bright E.Bass, Fusion E.Bass, Funky E.Bass, Fretless Bass, Picked E.Bass, Mute Bass, Slap Bass 1, Slap Bass 2, Killer Bass, Analog Bass, Soul Bass, Wow Bass, Dance Bass, House Bass, Plastic Bass, Basic Synth Bass and Techno Bass. The directory names more outside that run, for example `ToneRec_355`..`ToneRec_357` (Straight Bass, Wet Bass, Analog Bass 2). See [Tone Database]({{ site.baseurl }}/tone-database/).

### Drum Kits

The tone database's kit names include Standard Kit, Room Kit, Power Kit, Brush Kit, Jazz Kit, Light Rock Kit, Funk Kit, Soul Kit, Dance Kit, House Kit, Analog Kit, Synth Kit, Electric Kit, Orchestral Kit, Trad Kit, Special Kit, Sound Effect Kit and MSP Kit. See [Tone Database]({{ site.baseurl }}/tone-database/) for the 26 drum-kit records.

---

## Custom Data Flash (kn5000_custom_data.ic19)

**Size:** 1MB (1,048,576 bytes)
**Load Address:** 0x300000
**Total Strings Found:** 324
**Style directory records:** 210 (7 sections × 30; `docs/accompaniment-style-format.md` in kn5000-roms-disasm)

### Purpose

This flash memory stores user-customizable data including:
- custom accompaniment styles (sections 0-6) and section 7's block slot store
- three user banks of sound-parameter settings
- the LCD wallpaper image
- the compressed sub-CPU payload (`0x3E0000`)

Panel Memory is not stored here; see [Custom Data Flash]({{ site.baseurl }}/custom-data-flash/).

### Style names

The style names are the 16-character name fields of each section's style directory. Examples: "Bolero puro", "GentleSwing 1", "GospelRevival", "Roaring 20's", "AccordionJazz", "8BtPopBallad D".

### Special Entries

| Entry | Meaning |
|-------|---------|
| `Clear` | Empty user slot (available for user data) |
| `Init` | Factory default initialization state |

These markers indicate the state of user-configurable memory slots.

---

## HDAE5000 ROM (hd-ae5000_v2_06i.ic4)

**Size:** 512KB (524,288 bytes)
**Load Address:** 0x280000

### Version Information

| Property | Value |
|----------|-------|
| Internal Version | `Technics Software section M. Kitajima 2.33J` |
| Author | M. Kitajima |
| Development Period | Juli-Oktober 1996 |

### PPORT Menu Commands

Commands for PC parallel port communication:

| Command             | Description                   |
|---------------------|-------------------------------|
| Send Infos About HD | Report HD information to PC   |
| Exit PPORT          | End parallel port session     |
| Read FSB from HD    | Read File System Block        |
| Sending FSB to PC   | Transfer FSB to PC            |
| Rcv FSB from PC     | Receive FSB from PC           |
| Writing FSB to HD   | Write FSB to HD               |
| Load HD to Memory   | Load file to KN5000 memory    |
| Send data to PC     | Data transfer to PC           |
| Sending files to PC | File transfer to PC           |
| Rcv data from PC    | Receive data from PC          |
| Save memory to HD   | Save to hard disk             |
| Sending infos to PC | Send status information to PC |
| Delete files        | Delete HD files               |
| Formating HD        | Format hard disk              |
| Switch HD-motor off | Spin down HD                  |
| Send XapFile flash  | XAP file transfer             |

The menu is numbered 01-20 (`HDAE5000_PPORT_Cmd01_SendInfosAboutHd` .. `HDAE5000_PPORT_Cmd20_SendXapFileFlash`). Entries 12, 15 and 19 read "nothing", and 13 repeats "Rcv data from PC".

### Registered Object Names

Handler names such as LyricBackColorCheck and FlsOverWrSwCatch belong to the firmware's own 69-entry object registry, not to PC-side DLL callbacks. See [HDAE5000 Resources & Object Registry]({{ site.baseurl }}/hdae5000-resources/#the-69-object-registry).

---

## String Extraction Methodology

The counts on this page are raw `strings(1)` line counts, with no filtering. The main CPU figure is `strings -n 8` (9,446, as recorded in `analysis/strings/README.md` in kn5000-roms-disasm). The other figures reproduce with `strings -n 6` (sub-CPU payload, 88; IC19 flash, 324) and `strings -n 4` (sub-CPU boot ROM, 11), run on the images in that repository's `original_ROMs/`. They count printable-ASCII runs, so they include runs that are really pixel or table data. The string tables named above were then identified against the disassembly.

---

## References

- [Memory Map]({{ site.baseurl }}/memory-map/) - ROM address locations
- [Hardware Architecture]({{ site.baseurl }}/hardware-architecture/) - ROM chip identification
- [HDAE5000]({{ site.baseurl }}/hdae5000/) - Hard disk expansion details
