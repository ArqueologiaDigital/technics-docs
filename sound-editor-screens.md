---
layout: page
title: Sound Editor Screens
permalink: /sound-editor-screens/
---

# Sound Editor Screens (KN5000)

SOUND EDIT mode (`NAKA_MODE_MD_SOUNDEDIT`) edits a sound's tones, pitch, amplitude, filter,
LFO and digital effect. A sound has up to four tones (the `1ST 2ND 3RD 4TH` selectors). Each
page of the editor is a NAKA **title**. `InitializeScoop` (`display/scoop_display.s`)
registers 32 of them with `RegTitle 0x6, <TT_ name>, <id>, NAKA_MAINFUNC_<X>TitleFunc`, ids
`0x20`-`0x3F`.

## Two per-title method tables

Besides its main function, which handles the title's events, every title has two methods,
held in two 48-entry tables in `audio/sound_editor_ui.s`. Both are indexed by `title id - 0x20`:

| table                       | dispatcher                 | what an entry does                                                                                                          |
|-----------------------------|----------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| `SeTitle_StaticScreenTable` | `SeTitle_DrawStaticScreen` | draws the page's fixed captions, frames and bitmaps; the dispatcher wraps it in `SeTitle_DrawWall` / `SeTitle_UpdateScreen` |
| `SeTitle_FieldDrawTable`    | `SeTitle_DrawField`        | redraws one parameter field, A = the field index; called after a value changes (`pushw <field>; pushw <title id>`)          |

Entries 32-47 of both tables, and the field entries of TT_SEFILBCF1 and TT_SECOPY, are
`SeTitle_UnusedSlot`, a bare `ret`. A field routine shared by several titles carries all their
names: `SePitAmpFilLfo1_DrawField` serves the three LFO1 pages.

## The 32 titles

The captions column is what each static-screen routine draws, read from its record lists by
`scripts/analysis/se_title_inventory.py --markdown` (kn5000-roms-disasm). They show that each
routine draws its own title's page. Title 0x32 TT_SEFILL241 draws LOW PASS -24dB, 0x3A
TT_SEDIGEFF draws DIGITAL EFFECT, and 0x3E TT_SEWRTMEM draws MEMORY WRITE. A title whose
captions are reached only through bound records shows none.

| id   | title        | static-screen routine          | field routine                   | captions drawn                                                               |
|------|--------------|--------------------------------|---------------------------------|------------------------------------------------------------------------------|
| 0x20 | TT_SEMENU    | `SeMenuTitle_DrawStaticScreen` | `SeMenuTitle_DrawField`         | YES / NO / ORIGINAL / EDITED                                                 |
| 0x21 | TT_SEEASY    | `SeEasy_DrawStaticScreen`      | `SeEasy_DrawField`              |                                                                              |
| 0x22 | TT_SETONTON1 | `SeTonTon1_DrawStaticScreen`   | `SeTonTon1_DrawField`           | TONE SELECT / SOUND EDIT / PAGE1/3 / TONE / SELECT / LEVEL                   |
| 0x23 | TT_SETONTON2 | `SeTonTon2_DrawStaticScreen`   | `SeTonTon2_DrawField`           | TONE SELECT / SOUND EDIT / SOLO                                              |
| 0x24 | TT_SETONRAN1 | `SeTonRan1_DrawStaticScreen`   | `SeTonRan1_DrawField`           | TONE LAYER / SOUND EDIT / KEY / LAYER / VEL / FADE LOW HIGH H                |
| 0x25 | TT_SETONRAN2 | `SeTonRan2_DrawStaticScreen`   | `SeTonRan2_DrawField`           | TONE LAYER / SOUND EDIT / KEY / LAYER / VEL / FADE LOW HIGH H                |
| 0x26 | TT_SETONHYB1 | `SeTonHyb1_DrawStaticScreen`   | `SeTonHyb1_DrawField`           | TONE SELECT / SOUND EDIT / PAGE2/3 / TONE DYNAMICS / TONE / TONE WAVEFORM    |
| 0x27 | TT_SEPITPIT1 | `SePitPit1_DrawStaticScreen`   | `SePitPit1_DrawField`           | SOLO                                                                         |
| 0x28 | TT_SEPITENV1 | `SePitEnv1_DrawStaticScreen`   | `SePitFilEnv1_DrawField`        | START PITCH / STOP / PITCH / TOTAL / DEPTH / PAGE1/2                         |
| 0x29 | TT_SEPITENV2 | `SePitEnv2_DrawStaticScreen`   | `SePitFilEnv2_DrawField`        | PAGE2/2 / KEY / FOLLOW / ENVELOPE / TOUCH / ATTACK                           |
| 0x2A | TT_SEPITLFO1 | `SePitLfo1_DrawStaticScreen`   | `SePitAmpFilLfo1_DrawField`     |                                                                              |
| 0x2B | TT_SEAMPAMP1 | `SeAmpAmp1_DrawStaticScreen`   | `SeAmpAmp1_DrawField`           | AMPLITUDE / SOUND EDIT / ENV / AMP / LFO                                     |
| 0x2C | TT_SEAMPAMP2 | `SeAmpAmp2_DrawStaticScreen`   | `SeAmpAmp2_SeFilFil2_DrawField` | SOLO / AMPLITUDE / SOUND EDIT / ENV / AMP / LFO                              |
| 0x2D | TT_SEAMPENV1 | `SeAmpEnv1_DrawStaticScreen`   | `SeAmpEnv1_DrawField`           | AMPLITUDE / SOUND EDIT / ENV / AMP / LFO / ENVELOPE                          |
| 0x2E | TT_SEAMPENV2 | `SeAmpEnv2_DrawStaticScreen`   | `SeAmpEnv2_DrawField`           | AMPLITUDE / SOUND EDIT / ENV / AMP / LFO / PAGE2/2                           |
| 0x2F | TT_SEAMPLFO1 | `SeAmpLfo1_DrawStaticScreen`   | `SePitAmpFilLfo1_DrawField`     | AMPLITUDE / SOUND EDIT / ENV / AMP / LFO / LFO1                              |
| 0x30 | TT_SEFILLPQ1 | `SeFilLpq1_DrawStaticScreen`   | `SeFilLpq1_DrawField`           | SOLO                                                                         |
| 0x31 | TT_SEFILHPQ1 | `SeFilHpq1_DrawStaticScreen`   | `SeFilHpq1_DrawField`           | HIGH PASS -12dB / SOLO                                                       |
| 0x32 | TT_SEFILL241 | `SeFilL241_DrawStaticScreen`   | `SeFilL241_DrawField`           | LOW PASS -24dB / SOLO                                                        |
| 0x33 | TT_SEFILH241 | `SeFilH241_DrawStaticScreen`   | `SeFilH241_DrawField`           | HIGH PASS -24dB / SOLO                                                       |
| 0x34 | TT_SEFILBPF1 | `SeFilBpf1_DrawStaticScreen`   | `SeFilBpf1_DrawField`           | FILTER: / BAND PASS / LOW / HIGH ~ / CUTOFF / HIGH                           |
| 0x35 | TT_SEFILBCF1 | `SeFilBcf1_DrawStaticScreen`   | `SeTitle_UnusedSlot`            | THROUGH / SOLO                                                               |
| 0x36 | TT_SEFILFIL2 | `SeFilFil2_DrawStaticScreen`   | `SeAmpAmp2_SeFilFil2_DrawField` | LEVEL / LEVEL KEY FOLLOW / CUTOFF / FILTER KEY FOLLOW                        |
| 0x37 | TT_SEFILENV1 | `SeFilEnv1_DrawStaticScreen`   | `SePitFilEnv1_DrawField`        | START / POINT / STOP / CUTOFF / ADJUST                                       |
| 0x38 | TT_SEFILENV2 | `SeFilEnv2_DrawStaticScreen`   | `SePitFilEnv2_DrawField`        |                                                                              |
| 0x39 | TT_SEFILLFO1 | `SeFilLfo1_DrawStaticScreen`   | `SePitAmpFilLfo1_DrawField`     | LFO1 / LFO2 / LFO3 / LFO4 / LFO / WAVE                                       |
| 0x3A | TT_SEDIGEFF  | `SeDigEff_DrawStaticScreen`    | `SeDigEff_DrawField`            | DIGITAL EFFECT / SOUND EDIT / TYPE / REVERB DEPTH  : / REVERB / INTENSITY    |
| 0x3B | TT_SECTR2    | `SeCtr2_DrawStaticScreen`      | `SeCtr2_DrawField`              | 1ST 2ND 3RD 4TH / 1ST 2ND                                                    |
| 0x3C | TT_SECTR3    | `SeCtr3_DrawStaticScreen`      | `SeCtr3_DrawField`              |                                                                              |
| 0x3D | TT_SECOPY    | `SeCopy_DrawStaticScreen`      | `SeTitle_UnusedSlot`            |                                                                              |
| 0x3E | TT_SEWRTMEM  | `SeWrtMem_DrawStaticScreen`    | `SeWrtMem_DrawField`            | MEMORY WRITE / SOUND EDIT / OK / NAME: / MEMORY BANK:  - / SOUND NAMING      |
| 0x3F | TT_SEWRTSND  | `SeWrtSnd_DrawStaticScreen`    | `SeWrtSnd_DrawField`            | WRITE / SOUND EDIT / SOUND NAMING / A B C D E F G H I J K L M N O / CLR / .. |

The ROM's own strings spell several captions with a zero for the letter O (`T0NE SELECT`,
`LF0`). The table shows them corrected.

## How a page is drawn

A static-screen routine hands record lists to `SeGfx_DrawStaticList`: XIY is the first record
and XIX the exclusive end. Records are `{op, length, ...}`:

- `sd_quad`: rectangles and lines;
- `sd_ctext` / `sd_ptext`: text at a character cell or a pixel position;
- `sd_blit`: bitmaps.

Field routines use bound records (`sdb_num`, `sdb_str`, `sdb_box` ...). These tie a RAM
parameter (address, mask, shift) to a display style and a cell. `SeGfx_DrawIndexedBoundRecord`
draws entry A of such a list. The record formats are in [ScreenData C conversion](/screendata-c-conversion/).

## Across models

The KN6000's name tables (from its update file IK2.SLD; `kn7000_extraction/output/kn6000_table_names.txt`)
register its sound editor under the same mode name, `MD_SOUNDEDIT`. It has 22 `TT_SE*` titles,
grouped by section rather than by page: `TT_SETONE`, `TT_SEAMP`, `TT_SEPITCH`, `TT_SEFILTER`,
`TT_SELFO`, `TT_SEDIGEFF`, `TT_SECONTROL`, `TT_SEWRITE`, `TT_SENAME`, `TT_SECOPY`, `TT_SELFOVIEW`.
A separate drum-sound editor family follows: `TT_SEDMENU`, `TT_SEDAMP`, `TT_SEDFILTER`,
`TT_SEDTONE` ... `TT_SEDNAME`. Where the KN5000 has one title per page (`TT_SEPITENV1`/`2`, one
title per filter type), the KN6000 has one title per section. `TT_SEMENU`, `TT_SEEASY`,
`TT_SEDIGEFF` and `TT_SECOPY` keep their names across both models.

## Related pages

- [UI Framework](/ui-framework/): titles, main functions and the NAKA object model
- [Panel Parameter Keys](/panel-parameter-keys/)
- [KN7000 Sound GUI Map](/kn7000-sound-gui-map/)
