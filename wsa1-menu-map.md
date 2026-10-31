---
layout: page
title: "SX-WSA1R Menu Map"
permalink: /wsa1-menu-map/
---

# SX-WSA1R: how the screens are built, and the menu map

The SX-WSA1R has no widget classes and no string table, unlike the KN5000. Everything its
320 x 240, 1-bit, three-layer LCD shows is drawn from **display lists**: short byte-coded programs
run by two interpreters in program ROM B, `DisplayList_Run` (`0xF31A09`) and `DisplayListB_Run`
(`0xF31AF0`). A record names a graphics service and its operands: a box, a line, a string in one of
the [twelve fonts](#the-fonts-twelve-faces-five-of-them-japanese), a bitmap, or a live value.

- The opcode of an interpreter-A record *is* the service number of the CPU's SWI 7 graphics call
  (34 services, `SWI7_ServiceTable` at prom_a `0xF8E9C6`).
- Interpreter B reads a bit-field from a RAM variable, `((var) & mask) >> shift`, and draws it as
  digits, as an entry of a string table, or as a rectangle taken from a table.

A screen is an object of three methods (Enter, Leave, Button) in the 256-entry
`PanelScreen_VtableTable` at prom_a `0xF86EC1` (see
[the control panel]({{ site.baseurl }}/wsa1-panel/#the-screen-objects-how-a-screen-is-dispatched)).
Its Button method dispatches the 5-bit panel key code through a 32-entry key map.

The disassembly spells all of this as macros (`wsa1/include/wsa1_gui.inc`), and a generated menu
map lists every screen, what it draws, which key does what, and which key leads to it. This page
summarises both. The lane notes behind it are
[`wsa1/notes/gui-data-2026-10-29/README.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/wsa1/notes/gui-data-2026-10-29/README.md).

## What the source looks like

```
DL_SoundEditWriteCopy:
	dl_text16x16_packed	x=110, y=5, text="SOUND EDIT"
	dl_text8x14	x=0, y=36, text="\020 WRITE"
	dl_text8x10	x=272, y=36, text="COPY"
	dl_box	x0=12, y0=31, x1=60, y1=50
	dl_value_glyph	glyph=16, x=80, y=1

	dlb_string	var=DisplayListB_Stage, mask=0xff, shift=0, svc=LCDSVC_DrawText8x10, table=PartLabels_FE84F5, width=3, x=8, y=175

ButtonTable_SongClear:
	keymap_begin
	on_key	KEY_SoftKeyCol3,	SoftKeyCol3_SongClear
	...
	on_key	KEY_Exit,		ExitKey_SongClear
	...
	keymap_end
```

Each record kind is one macro of [`wsa1/include/wsa1_gui.inc`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/wsa1/include/wsa1_gui.inc),
whose header gives the field conventions:

- **Geometry is in panel pixels**, x right and y down. A box's corners are the four words the
  handler copies to `LCD_X0`..`LCD_Y1`. A text or bitmap position is stored in the ROM as a
  display-RAM byte offset, y * 40 + x / 8 (the SED1330 is programmed for 40 bytes per line), so the
  macro computes it and checks that x is a multiple of 8. The packed-text services `0x17` and `0x1C`
  take pixel x and y directly.
- **Text is inline**, with the font's own glyph codes written as octal escapes.
- Bitmaps and string tables are referenced **by label**, the live variable by its
  `wsa1/include/wsa1_ram.inc` name, and the drawing service by an `LCDSVC_*` name.
- **Every length byte is computed by the macro**, so a text or field that was misread cannot
  rebuild the ROM: the byte gate (`make gate-wsa1`) checks every record.
- Which layer a list draws into is not in the list: the caller sets `LCD_CurrentLayer` before it
  runs the list.

| macro family                                               | interpreter, opcodes                  | fields                                      |
|------------------------------------------------------------|---------------------------------------|---------------------------------------------|
| `dl_line` ... `dl_box_shadow1` (12)                        | A 00 01 02 05 09 0A 11 12 13 15 1B 22 | x0, y0, x1, y1                              |
| `dl_text8x14` ... `dl_text16x24` (12)                      | A 06 07 08 16 18 19 1A 1D 1E 1F 20 21 | x, y, text                                  |
| `dl_text8x8_packed`, `dl_text16x16_packed`                 | A 17 1C                               | x, y (pixels), text                         |
| `dl_plot`                                                  | A 0B                                  | x, y                                        |
| `dl_clear_area`                                            | A 0E                                  | x, y, w, h                                  |
| `dl_bitmap`, `dl_read_area`                                | A 03 04                               | bitmap / buffer, x, y, w, h                 |
| `dl_value_glyph`                                           | A 23                                  | glyph (24 x 24, `DLGlyph_000_F78028`), x, y |
| `dlb_number`, `dlb_number16`                               | B 00, 06                              | var, mask, shift, svc, x, y, digits         |
| `dlb_number_signed`                                        | B 05                                  | ... digits, signflag                        |
| `dlb_number_xy`, `dlb_number16_xy`, `dlb_number_signed_xy` | B 09 0A 0B                            | ... x, y (pixels), digits [, signflag]      |
| `dlb_string`, `dlb_string_xy`                              | B 02, 07                              | ... table, width, x, y                      |
| `dlb_rect_entry`, `dlb_rect_entry_op08`                    | B 03, 08                              | var, mask, shift, svc, table                |
| `dlb_area_entry`                                           | B 04                                  | var, mask, shift, svc, table                |
| `dlb_centred_span`                                         | B 01                                  | var, mask, shift, x0, x1, y1 (unused)       |
| `keymap_begin` / `on_key` / `keymap_end`                   | 32 handlers per map                   | `KEY_*` code, handler                       |
| `keymap_begin` / `on_key` / `fieldops_end`                 | 17 handlers and a zero word           | `KEY_*` code 0x00-0x10, handler             |

The notes give the code evidence for each field (the handler that reads it and what it does with
it). The macro bodies are data directives only, so the repository's source censuses read them as
data.

### Which interpreter runs a record

The emitters that first framed the lists left a comment naming the interpreter on each record
header, and it was wrong for 118 records: they are interpreter B's.
`wsa1/scripts/tools/gui_display_list_macros.py` decides each record in this order:

1. **audit**: the walk of `wsa1/notes/prom_b_dl_length_audit.py` from every call site, where it
   reaches the record (4,097 records; none is reached by both interpreters);
2. **comment**: otherwise, the old comment;
3. **length**: B, when the A reading is impossible and the record's length is B's own (each B
   opcode has exactly one length);
4. **adjacent**: B, when a neighbour in the same run is B and the record reads as B;
5. **geometry**: B, when the A reading puts a corner off the panel and the B reading does not.

The 118 re-read records split 12 audit, 70 length, 26 adjacent and 10 geometry. A run that holds one
unreadable record is left untouched as a whole, because a list walked from the wrong start reads as
plausible text for a while before it fails.

## The panel key codes

A key map has one slot for each of the 32 codes `PanelButton_Route` passes to a screen's Button
method (`KEY_*` in `wsa1_gui.inc`):

| code      | name                                         | control                                                       |
|-----------|----------------------------------------------|---------------------------------------------------------------|
| 0x00-0x07 | `KEY_SoftKeyCol1` .. `KEY_SoftKeyCol8`       | SOFT KEY columns 1-8 (the lower and upper key share the code) |
| 0x08-0x0C | `KEY_LcdRow1` .. `KEY_LcdRow5`               | the five LCD-row key pairs, top to bottom                     |
| 0x0D      | `KEY_MinusPlus`                              | the -1 / +1 pair                                              |
| 0x0E      | `KEY_Code0E`                                 | TODO: nothing on this panel raises it                         |
| 0x0F      | `KEY_Exit`                                   | EXIT; the one slot all 32 prom_b `ButtonTable_*` maps fill    |
| 0x10      | `KEY_Page`                                   | the PAGE v / PAGE ^ pair                                      |
| 0x11-0x18 | `KEY_SoftKeyCol1Alt` .. `KEY_SoftKeyCol8Alt` | the soft-key column's second event                            |
| 0x19      | `KEY_PageAlt`                                | PAGE's second event                                           |
| 0x1A      | `KEY_Code1A`                                 | TODO: no control known                                        |
| 0x1B      | `KEY_NumberPad`                              | the number pad, the whole field                               |
| 0x1C-0x1D | `KEY_Code1C`, `KEY_Code1D`                   | TODO: no control known                                        |
| 0x1E      | `KEY_Compare`                                | COMPARE; no screen's key map handles it                       |
| 0x1F      | `KEY_Code1F`                                 | TODO: no control known                                        |

Codes 0x11-0x19 were `KEY_Code11`..`KEY_Code19` until 2026-10-29
(`scripts/renaming/rename_wsa1_key_codes.sed`). `PanelEvent_ToFieldIndex` folds 0x11-0x18 onto
operations 0-7, the codes of the soft-key columns, and sets a flag bit; it folds 0x19 onto 0x10,
PAGE's. In the 87 key maps, 182 of the 0x11-0x18 slots repeat the handler of their own column and 41
differ. Which physical action raises these codes is still open: no prom_a panel template emits them.

## The menu map

[`wsa1/docs/gui-menu-map.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/wsa1/docs/gui-menu-map.md) is generated from the sources by
`wsa1/scripts/analysis/gui_menu_map.py`, whose docstring says exactly what it follows:

```
make -C wsa1 gui-menu-map         # regenerate
make -C wsa1 gui-menu-map-check   # exit 1 when stale; also run by the root make gate-wsa1
```

It indexes 183 objects: the panel modes (`PanelScreen_VtableTable` entries 0-47) and the screen ids
(entry 32 + n is screen id n, the number a screen request carries). For each it gives the Enter,
Leave and Button methods; the display lists they name, with their first texts; the key map, with
the handler on each key (do-nothing keys left out); the screen requests those handlers write,
decoded from `UI_Request_Hi` (bit 7 = go to the screen, bit 6 = ask for it, bit 1 = change mode,
bit 4 = repaint); and which key on which screen leads to it.

The sound-edit pages (0x80-0xAF, 0xC0-0xCF) paint through one more step, which the generator
follows: their Enter methods ask CPU 2 for the page's values, `Cpu2Reply_HandleNext` re-runs the
same Enter for each reply (through `ScreenCode80_Handlers` / `ScreenCodeC0_Handlers` when the reply's
tag is `UI_ScreenId`), and each run stores the reply in `ModelingPage_Fields` and calls
`T_Dispatch_Code80_Bracketed`. That runs prom_b's `Dispatch_Code80_PaintTable` entry for the page
between an LCD blank and an LCD show; `Dispatch_Code80_RepaintFieldTable` repaints a single field.

The map is a static reading of the code: a screen request written through a register, or a list
chosen through a pointer table, is missing from it. Nothing in it is more than the code states.

## Every screen, at a glance

The map's index, grouped by screen-id range. "First texts drawn" are the first captions of the
display lists the Enter method names (many captions spell O as the digit 0, exactly as the ROM's
text does, and the labels derived from them keep that spelling); "keys" counts the key-map slots that do something; "reached from"
is the screen or mode whose key handler requests this one. The per-screen detail (every key and
its handler, every list) is in the [full map](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/wsa1/docs/gui-menu-map.md).

### Panel modes (table entries 0x01-0x2F; entry 32 + n is also screen id n)

| id   | Enter method                             | first texts drawn                                            | keys | reached from |
|------|------------------------------------------|--------------------------------------------------------------|------|--------------|
| 0x01 | `ModeEnter_Sound`                        | -                                                            | 0    | -            |
| 0x02 | `ModeEnter_Combination`                  | -                                                            | 0    | -            |
| 0x03 | `ModeEnter_Sequencer`                    | SEQUENCER / REALTIME / EDIT                                  | 0    | -            |
| 0x05 | `ModeEnter_RealtimeRecord_Fwd`           | -                                                            | 0    | -            |
| 0x06 | `ModeEnter_StepRecord`                   | EDIT / SEQ. / N0TE                                           | 0    | -            |
| 0x07 | `ModeEnter_Edit`                         | EDIT / SEQ. / N0TE                                           | 0    | -            |
| 0x08 | `ModeEnter_SeqPlay_Fwd`                  | -                                                            | 0    | -            |
| 0x09 | `ModeEnter_CombiEditPart`                | C0MBINATI0N EDIT / INTERNAL / CONFIGURE                      | 0    | -            |
| 0x0A | `PanelMode_System_Enter`                 | -                                                            | 0    | -            |
| 0x12 | `PanelMode_MidiEnter`                    | -                                                            | 0    | -            |
| 0x14 | `ModeEnter_SoundCopy`                    | -                                                            | 0    | -            |
| 0x15 | `ModeEnter_SoundCopy_Call`               | MIDI FILE LOAD / MIDI FILE SAVE / LOAD                       | 0    | -            |
| 0x16 | `CombiEdit_Begin`                        | -                                                            | 0    | -            |
| 0x17 | `ModeEnter_SoundEdit`                    | SOUND EDIT / · WRITE / COPY                                  | 0    | -            |
| 0x21 | `InstallPainter_SoundMode_Entry`         | SOUND MODE / 1 / 2                                           | 19   | -            |
| 0x22 | `InstallPainter_C0mbinati0nM0de_Entry`   | C0MBINATI0N M0DE / PAGE2/2 / SOUND:                          | 0    | -            |
| 0x24 | `Paint_Sequencer`                        | SEQUENCER / REALTIME / EDIT                                  | 14   | -            |
| 0x26 | `ScreenEnter_RealtimeRecordScreen_Fwd`   | -                                                            | 20   | -            |
| 0x27 | `ScreenEnterBody_CombiEditMixer`         | MIXER / SOUND:                                               | 0    | -            |
| 0x28 | `ScreenEnter_CycleRecordScreen_Fwd`      | -                                                            | 7    | -            |
| 0x2B | `ScreenEnter_AfterT0uchSetting`          | AFTER T0UCH SETTING / Select whether or not After Touch / is | 0    | -            |
| 0x2C | `ScreenEnter_MetronomeBalanceScreen_Fwd` | -                                                            | 3    | -            |
| 0x2D | `ScreenEnter_S0ngSelectName`             | S0NG SELECT & NAME / KB / S0NG                               | 0    | -            |
| 0x2E | `ScreenEnter_StepRecord`                 | -                                                            | 0    | -            |
| 0x2F | `ScreenEnter_StepRecordPartSelect`       | STEP RECORD / : PART SELECT / Press the up/down button under | 17   | -            |

### Sound, combination, sequencer and song edit (screen ids 0x01-0x2E)

| id   | Enter method                             | first texts drawn                                            | keys | reached from                                           |
|------|------------------------------------------|--------------------------------------------------------------|------|--------------------------------------------------------|
| 0x01 | `InstallPainter_SoundMode_Entry`         | SOUND MODE / 1 / 2                                           | 19   | screen 0xA1, screen 0xA6                               |
| 0x02 | `InstallPainter_C0mbinati0nM0de_Entry`   | C0MBINATI0N M0DE / PAGE2/2 / SOUND:                          | 0    | screen 0xA1, screen 0xA5, screen 0xA6                  |
| 0x04 | `Paint_Sequencer`                        | SEQUENCER / REALTIME / EDIT                                  | 14   | mode 0x2F, screen 0x0F, screen 0x10, screen 0x13       |
| 0x06 | `ScreenEnter_RealtimeRecordScreen_Fwd`   | -                                                            | 20   | mode 0x28, screen 0x08, screen 0x1E                    |
| 0x07 | `ScreenEnterBody_CombiEditMixer`         | MIXER / SOUND:                                               | 0    | -                                                      |
| 0x08 | `ScreenEnter_CycleRecordScreen_Fwd`      | -                                                            | 7    | mode 0x26, screen 0x06                                 |
| 0x0B | `ScreenEnter_AfterT0uchSetting`          | AFTER T0UCH SETTING / Select whether or not After Touch / is | 0    | mode 0x24, screen 0x04                                 |
| 0x0C | `ScreenEnter_MetronomeBalanceScreen_Fwd` | -                                                            | 3    | mode 0x26, screen 0x06                                 |
| 0x0D | `ScreenEnter_S0ngSelectName`             | S0NG SELECT & NAME / KB / S0NG                               | 0    | mode 0x24, screen 0x04                                 |
| 0x0E | `ScreenEnter_StepRecord`                 | -                                                            | 0    | mode 0x24, screen 0x04                                 |
| 0x0F | `ScreenEnter_StepRecordPartSelect`       | STEP RECORD / : PART SELECT / Press the up/down button under | 17   | -                                                      |
| 0x10 | `ScreenEnter_TrackAssign`                | SONG / TRACK ASSIGN / TRACK   L0CAL   MIDI                   | 15   | mode 0x24, screen 0x04, screen 0x11                    |
| 0x11 | `ScreenEnter_TrackAssignPresets`         | TRACK / ASSIGN / PRESETS                                     | 16   | screen 0x10                                            |
| 0x12 | `ScreenEnter_SeqPlayScreen_Fwd`          | -                                                            | 20   | screen 0x14                                            |
| 0x13 | `ScreenEnter_SequencerMedley`            | SEQUENCER MEDLEY / START / FIRST S0NG                        | 15   | mode 0x24, screen 0x04                                 |
| 0x14 | `ScreenEnter_CyclePlayScreen_Fwd`        | -                                                            | 6    | screen 0x12                                            |
| 0x15 | `ScreenCode15_Handler`                   | -                                                            | 0    | -                                                      |
| 0x1A | `ScreenEnter_Edit`                       | EDIT / SEQ. / N0TE                                           | 16   | screen 0x1B, screen 0x1C, screen 0x1D, screen 0x1E +11 |
| 0x1B | `ScreenEnter_SongClear`                  | SONG / CLEAR / KB                                            | 7    | screen 0x1A                                            |
| 0x1C | `ScreenEnter_TrackClear`                 | TRACK / CLEAR / Press                                        | 21   | screen 0x1A                                            |
| 0x1D | `ScreenEnter_Vel0cityChange`             | VEL0CITY CHANGE / TRACK           : / FIRST MEASURE   :      | 11   | screen 0x1A                                            |
| 0x1E | `ScreenEnter_Quantize`                   | QUANTIZE / TRACK         : / STRENGTH :                      | 11   | mode 0x26, screen 0x06, screen 0x1A                    |
| 0x1F | `ScreenEnter_TrackMerge`                 | TRACK MERGE / OK / TRACK  :                                  | 8    | screen 0x1A                                            |
| 0x20 | `ScreenEnter_MeasureErase`               | MEASURE ERASE / TRACK           : / FIRST MEASURE   :        | 11   | screen 0x1A                                            |
| 0x21 | `ScreenEnter_MeasureC0py`                | MEASURE C0PY / FROM TRACK / TO TRACK                         | 11   | screen 0x1A                                            |
| 0x22 | `ScreenEnter_MeasureInsert`              | MEASURE INSERT / FROM TRACK / TO TRACK                       | 11   | screen 0x1A                                            |
| 0x23 | `ScreenEnter_MeasureDelete`              | MEASURE DELETE / TRACK           : / FIRST MEASURE   :       | 10   | screen 0x1A                                            |
| 0x24 | `ShowScreen_NoteEditPartSelect`          | NOTE / EDIT / :                                              | 17   | screen 0x1A, screen 0x25, screen 0x28                  |
| 0x25 | `EditScreen_EnterNoteEdit`               | NOTE EDIT / TRACK / SONG                                     | 21   | screen 0x26, screen 0x29                               |
| 0x26 | `ScreenEnter_CyclePlayEditScreen_Fwd`    | -                                                            | 6    | screen 0x25, screen 0x28                               |
| 0x27 | `ShowScreen_DrumEditPartSelect`          | DRUM / EDIT / :                                              | 17   | screen 0x1A, screen 0x25, screen 0x28                  |
| 0x28 | `EditScreen_EnterDrumEdit`               | -                                                            | 20   | screen 0x26, screen 0x29                               |
| 0x29 | `ScreenEnter_CyclePlayEditScreen29_Fwd`  | -                                                            | 6    | screen 0x25, screen 0x28                               |
| 0x2A | `ScreenEnter_S0ngC0py`                   | S0NG C0PY / FROM / TO                                        | 21   | screen 0x1A                                            |
| 0x2B | `ScreenEnter_Transp0se`                  | TRANSP0SE / TRACK           : / FIRST MEASURE   :            | 11   | screen 0x1A                                            |
| 0x2C | `ScreenEnter_AdvanceDelay`               | ADVANCE/DELAY / TRACK           : / FIRST MEASURE   :        | 11   | screen 0x1A                                            |
| 0x2D | `ScreenEnter_N0teChange`                 | N0TE CHANGE / TARGET NOTE / TRACK         :                  | 10   | screen 0x1A                                            |
| 0x2E | `ScreenEnter_PanelWrite`                 | PANEL WRITE / PANEL WRITE replaces the sounds and / settings | 0    | screen 0x1A                                            |

### Combination edit (0x33-0x3C)

| id   | Enter method                            | first texts drawn                       | keys | reached from |
|------|-----------------------------------------|-----------------------------------------|------|--------------|
| 0x33 | `ScreenEnter_CombiEditMenuRedirect`     | -                                       | 0    | -            |
| 0x34 | `ScreenEnter_CombiEditMenu`             | C0MBINATI0N EDIT / INTERNAL / CONFIGURE | 0    | -            |
| 0x35 | `ScreenEnter_CombiEditConfigure_35`     | CONFIGURE / PART / PART                 | 0    | -            |
| 0x36 | `ScreenEnter_CombinationNaming`         | CONFIGURE / COMBI.EDIT / SOLO           | 20   | -            |
| 0x37 | `ScreenEnter_CombiEditInternalSound_37` | C0MBINATI0N EDIT / INTERNAL / CONFIGURE | 0    | -            |
| 0x38 | `ScreenEnter_CombiEditInternalSound_38` | C0MBINATI0N EDIT / INTERNAL / CONFIGURE | 0    | -            |
| 0x39 | `ScreenEnter_CombiEditDspEffect`        | SEND                                    | 0    | -            |
| 0x3A | `ScreenEnter_CombiEditMixer`            | MIXER / SOUND:                          | 0    | -            |
| 0x3B | `T_F41A88_Nop`                          | -                                       | 0    | -            |
| 0x3C | `Screen_CombinationNaming_Enter`        | MEM0RY WRITE / COMBI.EDIT / 0K          | 0    | -            |

### Disk (0x40-0x54)

| id   | Enter method                         | first texts drawn                                            | keys | reached from |
|------|--------------------------------------|--------------------------------------------------------------|------|--------------|
| 0x40 | `Paint_DiskMenu`                     | MIDI FILE LOAD / MIDI FILE SAVE / LOAD                       | 5    | -            |
| 0x45 | `Paint_MidiFileDirectPlay`           | PLAY ·                                                       | 6    | -            |
| 0x47 | `Paint_DiskL0adFile`                 | SAVE / SAVE FILE / SAVE ·                                    | 6    | -            |
| 0x49 | `Paint_MidiFileL0ad`                 | MIDI FILE L0AD / : / L0AD ·                                  | 6    | -            |
| 0x4C | `PageDispatch_DiskSaveFile`          | DISK SAVE : FILE NAMING                                      | 63   | -            |
| 0x4E | `PageDispatch_MidiFileSave`          | SAVE                                                         | 33   | -            |
| 0x50 | `Paint_FloppyDiskFormatSelectType`   | COMPOSER LOAD                                                | 33   | -            |
| 0x51 | `Paint_FloppyDiskFormatAreYouSure`   | ATTENTION! / Using DISK FORMAT will erase / any current data | 33   | -            |
| 0x53 | `PageDispatch_L0adSingleC0mbination` | LOAD SINGLE COMBINATION / DISK / 0K                          | 0    | -            |
| 0x54 | `PageDispatch_L0adSingleS0und`       | LOAD SINGLE SOUND / DISK / 0K                                | 0    | -            |

### System (0x5B-0x6E)

| id   | Enter method                           | first texts drawn                            | keys | reached from |
|------|----------------------------------------|----------------------------------------------|------|--------------|
| 0x5B | `Screen_SoundGroupNaming_Enter`        | SOUND GROUP NAMING / SYSTEM / WRITE          | 0    | -            |
| 0x5C | `Screen_CombinationGroupNaming_Enter`  | COMBINATION GROUP NAMING / SYSTEM / WRITE    | 0    | -            |
| 0x5D | `Screen_SoundMute_Enter`               | -                                            | 0    | -            |
| 0x5E | `Screen_SoundCopy_Enter`               | SOUND COPY / SYSTEM / OK                     | 0    | -            |
| 0x5F | `Screen_CombinationCopy_Enter`         | SOUND COPY / SYSTEM / OK                     | 0    | -            |
| 0x60 | `Screen_System_Enter`                  | -                                            | 0    | -            |
| 0x61 | `Screen_DataLoadFilter_Enter`          | -                                            | 0    | -            |
| 0x62 | `Screen_TuneScale_Enter`               | TUNE & SCALE / SYSTEM / MASTER TUNE        : | 0    | -            |
| 0x64 | `Screen_TouchSensitivityOrTest_Enter`  | -                                            | 0    | -            |
| 0x65 | `Screen_ControllerAssign_Enter`        | CONTROLLER ASSIGN / PAGE /2 / SYSTEM         | 0    | -            |
| 0x66 | `Screen_DspEffect_Enter`               | SEND                                         | 0    | -            |
| 0x67 | `Screen_DrumsMapNaming_Enter`          | DRUMS MAP / SYSTEM / WRITE                   | 0    | -            |
| 0x6A | `Screen_Initial_Enter`                 | -                                            | 0    | -            |
| 0x6B | `Screen_MainOutEqualizer_Enter`        | MAIN OUT EQUALIZER / SYSTEM                  | 0    | -            |
| 0x6C | `Screen_ReMapEdit_Enter`               | -                                            | 0    | -            |
| 0x6D | `Screen_SoundCombinationManager_Enter` | -                                            | 0    | -            |
| 0x6E | `Screen_MemoryProtect_Enter`           | -                                            | 0    | -            |

### MIDI (0x70-0x7F)

| id   | Enter method                  | first texts drawn                              | keys | reached from |
|------|-------------------------------|------------------------------------------------|------|--------------|
| 0x70 | `Paint_MidiMenu`              | ITEM / VALUE                                   | 5    | -            |
| 0x71 | `T_F41660_Nop`                | -                                              | 0    | -            |
| 0x72 | `T_F41680_Nop`                | -                                              | 0    | -            |
| 0x73 | `T_F41670_Nop`                | -                                              | 0    | -            |
| 0x75 | `Paint_MidiRealtimeMessages`  | REALTIME MESSAGES / MIDI / REALTIME COMMANDS : | 4    | -            |
| 0x76 | `T_F416B0_Nop`                | -                                              | 0    | -            |
| 0x78 | `T_F41700_Nop`                | -                                              | 0    | -            |
| 0x79 | `Paint_SysexBulkDump_Entry`   | SYSEX BULK DUMP / MIDI / TOTAL KEYBOARD        | 6    | screen 0x70  |
| 0x7A | `Paint_GeneralMidiMode_Entry` | OK                                             | 4    | screen 0x70  |
| 0x7B | `T_F416A0_Nop`                | -                                              | 0    | -            |
| 0x7C | `T_F416C0_Nop`                | -                                              | 0    | -            |
| 0x7D | `Paint_MidiTotalMode`         | LOCAL TOTAL     :                              | 17   | screen 0x70  |
| 0x7E | `Paint_MidiInputOutputFilter` | INPUT&OUTPUT / FILTER / MIDI                   | 17   | screen 0x70  |
| 0x7F | `Paint_MidiOutProgramChange`  | PROGRAM / CHANGE / MIDI                        | 19   | -            |

### Sound edit pages (0x80-0x9F)

| id   | Enter method                                  | first texts drawn                  | keys | reached from |
|------|-----------------------------------------------|------------------------------------|------|--------------|
| 0x80 | `ScreenEnter_SoundEditMenu`                   | SOUND EDIT / · WRITE / COPY        | 0    | -            |
| 0x82 | `ScreenEnter_SoundEditModelingToneTemplate`   | -                                  | 11   | -            |
| 0x83 | `ScreenEnter_SoundEditToneLayerPanning`       | PANNING / PANNING                  | 9    | -            |
| 0x84 | `ScreenEnter_SoundEditToneLayerKeyLayer`      | KEY LAYER / 0 / 1                  | 10   | -            |
| 0x85 | `ScreenEnter_SoundEditToneLayerVelocityLayer` | VELOCITY LAYER / 0 / 32            | 10   | -            |
| 0x86 | `ScreenEnter_SoundEditModelingDriverWaveform` | DRIVER / DRIVER WAVEFORM / RESO    | 10   | -            |
| 0x87 | `ScreenEnter_SoundEditPitchTune`              | KEY / DE- / TONE                   | 10   | -            |
| 0x88 | `ScreenEnter_SoundEditPitchEnvelope1`         | START PITCH / STOP / PITCH         | 14   | -            |
| 0x89 | `ScreenEnter_SoundEditPitchEnvelope2`         | PAGE2/2 / KEY FOLLOW / 0           | 13   | -            |
| 0x8A | `ScreenEnter_SoundEditPitchLfo`               | -                                  | 13   | -            |
| 0x8B | `ScreenEnter_SoundEditAmpLevel1`              | PAGE1/2 / LEVEL / TOUCH            | 13   | -            |
| 0x8C | `ScreenEnter_SoundEditAmpLevel2`              | PAGE2/2 / KEY FOLLOW / 0           | 11   | -            |
| 0x8D | `ScreenEnter_SoundEditAmpEnvelope1`           | ENVELOPE / KEYOFF / ATK            | 15   | -            |
| 0x8E | `ScreenEnter_SoundEditAmpEnvelope2`           | PAGE2/2 / KEY FOLLOW ( / 0         | 15   | -            |
| 0x8F | `ScreenEnter_SoundEditAmpLfo`                 | -                                  | 13   | -            |
| 0x90 | `ScreenEnter_SoundEditFilterLpf12`            | FILTER: / CUTOFF / EQUALIZER       | 14   | -            |
| 0x91 | `ScreenEnter_SoundEditFilterHpf12`            | FILTER: / CUTOFF / EQUALIZER       | 14   | -            |
| 0x92 | `ScreenEnter_SoundEditFilterLpf24`            | FILTER: / CUTOFF / FILTER          | 11   | -            |
| 0x93 | `ScreenEnter_SoundEditFilterHpf24`            | FILTER: / CUTOFF / FILTER          | 11   | -            |
| 0x94 | `ScreenEnter_SoundEditFilterBpf`              | FILTER: / BAND PASS / · LOW        | 13   | -            |
| 0x95 | `ScreenEnter_SoundEditFilterThrough`          | THROUGH                            | 7    | -            |
| 0x96 | `ScreenEnter_SoundEditFilterKeyFollow`        | PAGE2/2 / KEY FOLLOW / 0           | 11   | -            |
| 0x97 | `ScreenEnter_SoundEditFilterEnvelope1`        | START / POINT / STOP               | 14   | -            |
| 0x98 | `ScreenEnter_SoundEditFilterEnvelope2`        | FILTER / SOUND EDIT                | 13   | -            |
| 0x99 | `ScreenEnter_SoundEditFilterLfo`              | -                                  | 13   | -            |
| 0x9A | `ScreenEnter_SoundEditDigitalEffect`          | DIGITAL EFFECT / SOUND EDIT / TYPE | 11   | -            |
| 0x9B | `ScreenEnter_SoundEditControllerPage2`        | DIGITAL EFFECT / SOUND EDIT / TYPE | 13   | -            |
| 0x9C | `ScreenEnter_SoundEditDigitalEffectFromMenu`  | DIGITAL EFFECT / SOUND EDIT / TYPE | 11   | -            |
| 0x9D | `ScreenEnter_SoundEditCopy`                   | COPY / SOUND EDIT / FROM           | 7    | -            |
| 0x9E | `ScreenEnter_SoundEditMemoryWrite`            | MEM0RY WRITE / SOUND EDIT / 0K     | 5    | -            |
| 0x9F | `ScreenEnter_SoundEditNaming`                 | -                                  | 11   | -            |

### Group menus, messages and errors (0xA0-0xB7)

| id   | Enter method                                 | first texts drawn                                            | keys | reached from                                       |
|------|----------------------------------------------|--------------------------------------------------------------|------|----------------------------------------------------|
| 0xA0 | `InstallPainter_SoundGroupMenu_Entry`        | SOUND / GROUP / MENU                                         | 0    | screen 0xA1                                        |
| 0xA1 | `InstallPainter_GroupSoundDisplayHold_Entry` | GROUP: / SOUND / DISPLAY                                     | 23   | screen 0xA1                                        |
| 0xA2 | `InstallPainter_CombinationGroupMenu_Entry`  | COMBINATION GROUP MENU / 1. / 9.                             | 0    | -                                                  |
| 0xA3 | `ScreenEnter_DrawbarScreen`                  | 2 / ' / 2/3                                                  | 0    | -                                                  |
| 0xA5 | `InstallPainter_CombinationGroupMenu_Entry`  | COMBINATION GROUP MENU / 1. / 9.                             | 12   | screen 0xA6                                        |
| 0xA6 | `InstallPainter_GroupCombiDisplayHold_Entry` | GROUP: / COMBI. / DISPLAY                                    | 19   | screen 0xA5                                        |
| 0xA7 | `UiEvent_MarkRedrawFromPartClass`            | -                                                            | 0    | -                                                  |
| 0xAA | `ScreenEnter_PowerOnSplash`                  | -                                                            | 1    | -                                                  |
| 0xAB | `InstallPainter_MessageScreen`               | -                                                            | 0    | mode 0x26, mode 0x28, screen 0x06, screen 0x08 +15 |
| 0xAD | `ScreenEnter_CreatorSelectController`        | -                                                            | 0    | -                                                  |
| 0xB0 | `ScreenEnter_CombiEditPartMenu`              | C0MBINATI0N EDIT / INTERNAL / CONFIGURE                      | 0    | -                                                  |
| 0xB1 | `ScreenEnter_CombiEditInternalSound`         | C0MBINATI0N EDIT / INTERNAL / CONFIGURE                      | 0    | -                                                  |
| 0xB2 | `ScreenEnter_CombiEditConfigure_B2`          | CONFIGURE / PART / PART                                      | 0    | -                                                  |
| 0xB3 | `ScreenEnter_WriteProtectError`              | ERR0R! / The S0UND or C0MBINATI0N / memories are write prote | 0    | -                                                  |
| 0xB4 | `ScreenEnter_CombiEditInternalSound_B4`      | C0MBINATI0N EDIT / INTERNAL / CONFIGURE                      | 0    | -                                                  |
| 0xB5 | `ScreenEnter_CombiEditInternalSound_B5`      | C0MBINATI0N EDIT / INTERNAL / CONFIGURE                      | 0    | -                                                  |
| 0xB6 | `ScreenEnter_Effect2OutputConflict`          | ERR0R! / The S0UND or C0MBINATI0N / memories are write prote | 0    | mode 0x21, screen 0x01                             |
| 0xB7 | `ScreenEnterBody_CombiEditMixer`             | MIXER / SOUND:                                               | 0    | mode 0x26, screen 0x06, screen 0x12                |

### Tone edit (modelling) pages (0xC0-0xCE)

| id   | Enter method                           | first texts drawn                          | keys | reached from |
|------|----------------------------------------|--------------------------------------------|------|--------------|
| 0xC0 | `ToneEditPage_A0_ModelingTop`          | : / :                                      | 11   | -            |
| 0xC1 | `T_F41F7C_Nop`                         | -                                          | 0    | -            |
| 0xC2 | `T_F41F8C_Nop`                         | -                                          | 0    | -            |
| 0xC3 | `ToneEditPage_A3_PositionParameter`    | PAGE1/2 / P0SITI0N PARAMETER / P0SITI0N  : | 11   | -            |
| 0xC4 | `ToneEditPage_A4_PositionMovement`     | PAGE2/2 / P0SITI0N M0VEMENT / WIDTH :      | 11   | -            |
| 0xC5 | `ToneEditPage_A5_FittingMutingTuning`  | PAGE1/3 / FIT / MUT                        | 13   | -            |
| 0xC6 | `ToneEditPage_A6_TouchDepth`           | PAGE2/3 / TOUCH DEPTH / SUB                | 12   | -            |
| 0xC7 | `ToneEditPage_A7_ResoModeKeyFollow`    | MUTING / KEY FOLLOW / SLOPE                | 13   | -            |
| 0xC8 | `ToneEditPage_A8_SerialParallel`       | SERIAL                                     | 8    | -            |
| 0xCA | `ScreenEnter_SoundEditDspEffect`       | SEND                                       | 0    | -            |
| 0xCB | `ScreenEnter_SoundEditDrumMenu`        | SOUND EDIT / · WRITE / COPY                | 9    | -            |
| 0xCC | `T_F42340_Nop`                         | -                                          | 0    | -            |
| 0xCD | `ScreenEnter_SoundEditControllerPage1` | DIGITAL EFFECT / SOUND EDIT / TYPE         | 11   | -            |
| 0xCE | `T_F433E0_Nop`                         | -                                          | 0    | -            |

### Service and test screens (0xD8-0xDD)

| id   | Enter method               | first texts drawn                                            | keys | reached from |
|------|----------------------------|--------------------------------------------------------------|------|--------------|
| 0xD8 | `Paint_GateArrayCheck`     | PANEL CPU CHECK / Please check the CPU port / LED flash.     | 0    | -            |
| 0xD9 | `Paint_PanelCpuCheck`      | SINE WAVE CHECK / CHECK MODE / (1) SINE WAVE & ROM CHECK     | 0    | -            |
| 0xDA | `Paint_SineWaveCheckMode`  | SINE WAVE CHECK / CHECK MODE / (1) SINE WAVE & ROM CHECK     | 8    | -            |
| 0xDB | `Paint_PanelSwLedCheck`    | PANEL SW&LED CHECK / Please push a any button. / If LED near | 0    | -            |
| 0xDC | `T_F40110_Nop`             | -                                                            | 0    | -            |
| 0xDD | `ScreenEnter_DebugMonitor` | -                                                            | 13   | -            |

## How much of the GUI is still raw numbers

`python3 wsa1/scripts/analysis/gui_readability_census.py` (or `make -C wsa1 gui-census`) counts
it; its docstring defines each column. The lane measured, over all four images, before (`9dbc03088`)
and after the respelling:

| figure                                                 | before | after |
|--------------------------------------------------------|--------|-------|
| display-list records as macros                         | 0      | 8,871 |
| display-list records as raw `.byte op, len` + operands | 8,960  | 89    |
| anonymous operand fields in raw records                | 30,119 | 330   |
| pointer fields spelled as a number                     | 103    | 30    |
| B variable addresses spelled as a number               | 479    | 230   |
| B service numbers spelled as a number                  | 1,010  | 0     |
| key-map / field-operation entries named by key         | 0      | 3,558 |
| key-map / field-operation entries indexed only         | 3,558  | 0     |
| screen-table entries spelled as a number               | 3      | 0     |

A second round named the RAM cells the display lists draw, each from the routine that **writes**
it (`scripts/tools/name_wsa1_ram.py` generates `wsa1/include/wsa1_ram.inc`): for example
`EditScreen_DrawNumber` (`0x26B0`), `UI_CursorBox` (`0x2721`), the STEP RECORD row texts
`StepRecord_PrevRowText` / `StepRecord_CurrentRowText` / `StepRecord_NextRowText`, and the part
record fields `CombiPart_Volume` .. `CombiPart_SoundBank`. `DLB_NoVariable` (`0x0000` with mask 0)
marks the records that draw no variable.

What is still open:

- the 89 raw records: 88 are one run at `DL_F3D1B9`, whose framing needs a walk from its real entry
  points; the 89th is `TrackAssign_PaintTrackGroup_DL`, whose length byte over-declares (advance 11,
  extent 10), which a macro that computes the length cannot spell;
- records 6-101 of the fixed-stride run at `0xF3D3AD` (`StepRecord_MarkGrid_DL`,
  `StepRecord_ChordSymbolGrid_DL`) have no reader in either image; [INFERENCE] an older build's grid;
- a few RAM cells with no writer keep neutral names and a TODO;
- the physical action behind key codes 0x11-0x19.

## The fonts: twelve faces, five of them Japanese

All twelve character generators are in program ROM B, laid end to end from `0xF1B400`
(`wsa1/prom_b/modules/f1b400_f27bff_fonts.s`). Each is typed from a committed contact sheet,
`wsa1/prom_b/images/fonts/Font_Svc*.png`, by `wsa1/scripts/build/wsa1_fonts.py`. The cell counts
are arithmetic: the gap to the next table's base divided by the glyph pitch
(`wsa1/notes/FINDINGS-fonts.md` §1, re-derived by `notes/font_layout_check.py`).

| face               | base       | cell    | cells | script                             |
|--------------------|------------|---------|-------|------------------------------------|
| `Font_Svc06_8x14`  | `0xF1B400` | 8 x 14  | 200   | Latin                              |
| `Font_Svc07_8x16`  | `0xF1BEF0` | 8 x 16  | 200   | Latin                              |
| `Font_Svc08_16x16` | `0xF1CB70` | 16 x 16 | 200   | Latin                              |
| `Font_Svc17_8x8`   | `0xF1E470` | 8 x 8   | 200   | Latin, proportional, 6 px advance  |
| `Font_Svc1C_16x16` | `0xF1EAB0` | 11 x 16 | 200   | Latin, proportional, 11 px advance |
| `Font_Svc1D_16x16` | `0xF203B0` | 16 x 16 | 120   | hiragana                           |
| `Font_Svc16_8x14`  | `0xF212B0` | 8 x 14  | 120   | half-width katakana                |
| `Font_Svc19_16x16` | `0xF21940` | 16 x 16 | 120   | katakana                           |
| `Font_Svc1A_16x16` | `0xF22840` | 16 x 16 | 240   | kanji, set A (224 defined)         |
| `Font_Svc1F_16x16` | `0xF24640` | 16 x 16 | 60    | kanji, set B (43 defined)          |
| `Font_Svc20_8x10`  | `0xF24DC0` | 8 x 10  | 200   | Latin                              |
| `Font_Svc21_16x24` | `0xF25590` | 16 x 24 | 128   | Latin                              |

- **The code page is private.** Codes `0x10`-`0x1F` are music and UI symbols (triangles, the
  note-value ladder), not control codes. Above `0x7E` the Latin faces carry a Western-European
  block. Their accented letters are the plain letter's bytes with the accent in rows 0-1 (17
  codes of `Font_Svc06_8x14`, asserted by `font_layout_check.py`). The kana faces have JIS X
  0201's repertoire but not its code points, and the kanji sets are subsets numbered in a
  private order.
- **Settled 2026-10-31** (`wsa1/notes/open4-f-probes/latin_b0_bc.py`, commit `e87c170fd`):
  `Font_Svc06_8x14`'s `0xB0`-`0xBC` are the Spanish block. Read by byte identity with the face's
  own ASCII cells where a plain letter exists, they are −1, Á, É, Ñ, á, ó, ú, ñ, í, **ò**, **¡**, ¿, −2. `0xB0` and `0xBC` are
  single-cell negatives, so a reverse mapping must map the strings "-1" and "-2" onto them.
  The earlier reading `ì` for `0xB9` was wrong. In the kana faces, half-width `0x15` is the wave
  dash 〜 and full-width katakana `0x66` is ・, the katakana middle dot (read from the renderings).
  Kanji set A `0x38` is read **既** by eye. A machine match of the kanji cells against the X11
  `jiskan16` JIS X 0208 font agrees with the human reading on only about 6 % of cells
  (`kanji_nearest_jis.py`), so it decides nothing.
- **The text services' `HL` argument is a row number** (`notes/open4-f-probes/swi7_text_hl.py`).
  Every character is read as `ld r,(XIY+IZ)` with `IZ = HL x BC`, so `HL` picks row `HL` of a
  table of `BC`-character strings at `XIY`, in all twelve services. The Latin call sites that
  pass `HL` other than 0 use it that way, and so does prom_b's `DLB_Handler_StringTable`.
- **Nothing calls the Japanese services.** A byte-pattern census of `ld a,nn` / `swi 7`
  (`notes/swi7_call_sites.py`, with a measured false-positive floor) finds call sites for 6 of
  the 7 Latin text services and 0 of the 5 Japanese ones. No Japanese text was found in the four
  images. On 2026-10-31 the nine WSA1R floppies of MAME's `wsa1_flop` softlist were searched the
  same way: no disk scores above its permuted-map null, and no image declares a compressed span
  (FINDINGS-fonts.md §6.3). The service manual lists no Japanese market area for the SX-WSA1R.
  [Inference] The Japanese faces ship because the export SX-WSA1R shares its firmware source
  with the domestic SX-WSA1. The text the kanji order was taken from would need a domestic
  SX-WSA1 dump (program ROMs or a disk), and none is in the romset.

## Related

| Page                                                                 | Description                                                    |
|----------------------------------------------------------------------|----------------------------------------------------------------|
| [Control Panel & Switch Matrix]({{ site.baseurl }}/wsa1-panel/)      | the switches, and how a screen request reaches a screen object |
| [Disassembly]({{ site.baseurl }}/wsa1-disassembly/)                  | the byte-exact tree these macros live in                       |
| [HD-AE5000 Menu Map]({{ site.baseurl }}/hdae5000-menu-map/)          | the KN5000 expansion's GUI, a NAKA class tree                  |
| [UI Framework]({{ site.baseurl }}/ui-framework/)                     | the KN5000's class-based GUI, for contrast                     |
