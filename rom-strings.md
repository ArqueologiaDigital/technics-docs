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
actually the start of the instrument-category table below). A separate string,
`Technics KN5000 Program  DATA FILE 1/2`, exists near the very start of the ROM
(`0xE00038`).

| Location | String |
|----------|--------|
| 0xE5957E | `KN5000 ~95 VOCALIST WORKSTATION` |

This product ID string confirms the keyboard model and its "Vocalist Workstation" designation, indicating built-in vocal processing capabilities.

### Key String Tables

| Address  | Description                                | Count |
|----------|--------------------------------------------|-------|
| 0xE023F0 | Instrument categories                      | ~50   |
| 0xE0C3BE | Chord database                             | ~200  |
| 0xECFDFE | Part names (RIGHT1, RIGHT2, LEFT, PART4 …) | ~30   |

### String Categories

**Instrument Names:**
- Piano variations (Grand Piano, Upright, Electric)
- String ensembles (Strings, Violin, Cello, Orchestra)
- Wind instruments (Flute, Clarinet, Oboe, Saxophone)
- Brass section (Trumpet, Trombone, French Horn)
- Guitars (Acoustic, Electric, Nylon, Steel)
- Synthesizer patches (Synth Pad, Synth Lead, Analog)

**Menu Text:**
- Main menu items (Sound, Rhythm, Sequencer, Disk)
- Sub-menu options (Edit, Copy, Delete, Save, Load)
- Dialog prompts (Yes/No, OK/Cancel, Continue?)
- Error messages (Disk Error, Memory Full, File Not Found)

**Effects Names:**
- Reverb types (Hall, Room, Plate, Spring)
- Chorus/Delay effects
- EQ and filter settings
- DSP processing modes

**System Messages:**
- Boot messages
- Memory test strings
- Calibration routines
- Debug output

---

## Sub CPU Payload ROM (kn5000_subprogram_v142.rom)

**Size:** 192KB (196,608 bytes)
**Purpose:** Tone generator and audio synthesis control
**Total Meaningful Strings:** 88

### Key Strings

| Address | String | Purpose |
|---------|--------|---------|
| 0x31E3 | `KN5000 SOUND RAM` | Memory region identifier |
| 0x31F4 | `User Kit` | User-defined drum kit designation |

### DSP Control Messages

The sub CPU firmware contains control messages for the DSP subsystem:

| Category | Strings |
|----------|---------|
| Reset | DSP reset commands |
| Mute | Channel mute control |
| Disconnect | Audio path disconnect |
| Link | Channel linking |
| Edit | Parameter editing |

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
**Total Strings Found:** 164+

### Bass Instruments

| String | Type |
|--------|------|
| Acoustic Bass | Standard |
| Electric Bass | Standard |
| Slap Bass | Extended |
| Fretless Bass | Extended |
| Synth Bass | Electronic |

### Drum Kits

The tone database's kit names include Standard Kit, Room Kit, Power Kit, Brush Kit, Jazz Kit, Light Rock Kit, Funk Kit, Soul Kit, Dance Kit, House Kit, Analog Kit, Synth Kit, Electric Kit, Orchestral Kit, Trad Kit, Special Kit, Sound Effect Kit and MSP Kit. See [Tone Database]({{ site.baseurl }}/tone-database/) for the 26 drum-kit records.

---

## Custom Data Flash (kn5000_custom_data.ic19)

**Size:** 1MB (1,048,576 bytes)
**Load Address:** 0x300000
**Total Strings Found:** 324
**Unique Rhythm/Style Names:** 89

### Purpose

This flash memory stores user-customizable data including:
- custom accompaniment styles (sections 0-6) and section 7's block slot store
- three user banks of sound-parameter settings
- the LCD wallpaper image
- the sub-CPU payload staging area

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

Strings were extracted using systematic scanning with the following criteria:

1. **Minimum Length:** 4 characters
2. **Character Set:** Printable ASCII (0x20-0x7E)
3. **Termination:** Null-terminated (0x00) or fixed-length fields
4. **Filtering:** Manual review to exclude false positives from binary data

### Tools Used

- Binary string extraction (custom scripts)
- Cross-reference with disassembly
- Pattern matching for structured data

---

## References

- [Memory Map]({{ site.baseurl }}/memory-map/) - ROM address locations
- [Hardware Architecture]({{ site.baseurl }}/hardware-architecture/) - ROM chip identification
- [HDAE5000]({{ site.baseurl }}/hdae5000/) - Hard disk expansion details
