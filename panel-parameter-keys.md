---
layout: page
title: Panel Parameter Keys
permalink: /panel-parameter-keys/
---

# Panel Parameter Keys

Every editable panel setting of the KN5000 has a numeric **key**. The UI's Lsw
functions, the MIDI receive tables, the SysEx handlers and the panel-memory code all
read and write settings through these keys: `SndParam_LookupReadOnly(key)`,
`MainLswGet` / `MainLswPut` / `MainLswAdd`, and `SoundParam_NotifyChange(key, ...)`.
This page is the map from key to setting, taken from the firmware's own tables,
screens and functions. The keys and descriptors are identical in v7, v9 and v10.

The working notes, with every citation, are in the disassembly repository:
`analysis/disk-format-probes/README-lsw-param-namespace-map.md` (sections 1-9). The
tables below come from `scripts/renaming/gen_sndparam_desc_names_r2.py --markdown` and
`--markdown-parts` and, for round 3 (2026-10-17), from `gen_sndparam_desc_names_r3.py
--markdown`, whose evidence is in `analysis/disk-format-probes/sndparam-r3/`. Round 3 read
the MIDI menu's grids (CONTROL MESSAGES, COMMON SETTING, REALTIME MESSAGES, PART SETTING),
the panel memory EXPAND MODE FILTER, the panel LEDs each key drives, and the MIDI messages
`SndPart_SetParam` sends.

## The descriptor

A key is registered at boot with an 18-byte **descriptor**. `SndParam_RegisterAllWidgets`
walks 972 pointers (`SndParam_RegisterLoop_Data`, v10 `0xEE01A0`) and hashes each
descriptor's key into an 8-byte-slot table in RAM at `0x34100`. Every later access
re-hashes the key, finds the descriptor and reads the field it names:

| offset | field               | meaning                                                           |
|--------|---------------------|-------------------------------------------------------------------|
| +0x00  | `key`               | u32; byte 3 is always 0                                           |
| +0x04  | `bank_index`        | the panel record (TLV tag) that holds the value                   |
| +0x05  | `bank_offset`       | byte offset inside that record's payload                          |
| +0x06  | `mask`              | the bits of that byte that hold the value                         |
| +0x07  | `clamp_min`         | the value is raised to this                                       |
| +0x08  | `clamp_max`         | the value is lowered to this                                      |
| +0x09  | `shift`             | low nibble = shift count of the field inside the byte             |
| +0x0A  | `xor_value`         | XORed with the value                                              |
| +0x0B  | `aux_index`         | index of a second descriptor used as a map or bias, `0xFF` = none |
| +0x0C  | `read_accessor`     | selector into `SndParam_RO_Dispatch_Data`                         |
| +0x0D  | `register_accessor` | selector into `SndParam_DispatchCallback_Data`                    |
| +0x0E  | `lookup2_accessor`  | selector into `SndParam_Lkp2_Dispatch_Data`                       |
| +0x0F  | `codec`             | encoder `n` / decoder `n+3` in `SndParam_RW_ProcessResult_Data`   |
| +0x10  | `write_accessor`    | selector into `SndParam_DispatchTypeDE5_Data`                     |
| +0x11  | `unknown_0x11`      | no reader found; `0xFF` in almost every descriptor                |

`bank_index` selects the record's RAM address from `SndParam_BlockRamPtrs` (v10
`0xEE1160`, 256 pointers). The records are the panel work area's TLV records
(`0xF9A0`-`0xFFC0`), the same ones a `.LSW` file saves. A few banks (`0xAE`-`0xBC`)
have no RAM pointer; special accessors serve those. Two of them, `0xB2` (CC1
modulation) and `0xB3` (CC11 expression), are per-part live-controller arrays.

## The part namespace

Keys `0x8000`-`0xE3FF` belong to the 26 per-part records. The firmware's own decode,
`SndParam_KeyToLswPartNumber` (v10 `0xFCD7C5`), splits a key into the Lsw (part,
number) pair the UI uses:

```
0x8000  <= key <= 0x17FFF:   part = ((key - 0x8000) >> 10) & 0x3F,   number = key & 0x3FF
0x18000 <= key <= 0x27FFF:   part = ((key - 0x8000) >> 10) & 0x3F,   number = (key & 0x3FF) + 0x400
```

So `key = 0x8000 + 0x400*T + n` for numbers below `0x400`, and
`key = 0x18000 + 0x400*T + (n - 0x400)` for `0x400` and above. The part tags, named by
the mixer's channel table (`AcMixerVol_Channels` with its name table):

| tag `T` | 0x00 | 0x01 | 0x02 | 0x03-0x0F | 0x10-0x12 | 0x13 | 0x14 | 0x15 | 0x16 | 0x17 | 0x19 |
|---------|------|------|------|-----------|-----------|------|------|------|------|------|------|
| mixer   | RT1  | RT2  | LEFT | PT4-PT16  | ACP1-ACP3 | BASS | DRUM | CHRD | RTBS | MSP  | CTRL |

The mixer also carries METR (`0xE807`/`0xE808`, tag `0x1A` of the same law, held in
record `0x98`) and MIC (`0x4141`/`0x4142`). Part `0x17`, the MSP, answers its volume,
mute and reverb with keys of its own: `0x28801`, `0x2880B`, `0x28802`.

### Part fields

Each Lsw part-parameter function (`LswVolume`, `LswPan`, `LswSustainLength`, ... in
`ui/drawbar_panel_ui.s`) answers `EVT_GET_LSW_DATA_NO` with the number it edits. Below
`0x80` the numbers match the MIDI controller numbers of the same meaning: volume `0x07`,
pan `0x0A`, sustain `0x40`, reverb `0x5B` and so on. This reading is inferred (section 5
of the notes), but every one lands on the byte or bit that controller governs. A field's descriptors
are named `SndParam_Part<TT>_<field>`. "record = part" means the part's own 24-byte
record (`bank_index = T`). `0x280`-`0x2CC` live in the drawbar records `0x44`-`0x46`
of parts 0-2 (RIGHT 1, RIGHT 2, LEFT).

| Lsw number | field              | parts | record         | byte | mask | range           |
|------------|--------------------|-------|----------------|------|------|-----------------|
| 0x000      | `_Sound`           | 25    | part           | +0   | 0xFF | 0..255          |
| 0x001      | `_Modulation`      | 25    | 0xB2           | +0   | 0x7F | 0..127 (varies) |
| 0x007      | `_Volume`          | 25    | part           | +3   | 0x7F | 0..127          |
| 0x008      | `_Mute`            | 25    | part           | +3   | 0x80 | 0..1            |
| 0x00A      | `_Pan`             | 25    | part           | +8   | 0x7F | 0..127          |
| 0x00B      | `_Expression`      | 25    | 0xB3           | +0   | 0x7F | 0..127 (varies) |
| 0x020      | `_Bank`            | 25    | part           | +1   | 0x7F | 0..255          |
| 0x040      | `_Sustain`         | 25    | part           | +4   | 0x08 | 0..127          |
| 0x05B      | `_ReverbSend`      | 25    | part           | +7   | 0x7F | 0..127          |
| 0x05D      | `_DspEffect`       | 25    | part           | +5   | 0x7F | 0..127          |
| 0x05E      | `_DigitalEffect`   | 25    | part           | +4   | 0x40 | 0..127          |
| 0x078      | `_AllSoundOff`     | 25    | 0xAE           | +T   | 0x7F | 0..127          |
| 0x080      | `_BendRange`       | 25    | part           | +11  | 0x7F | 0..12           |
| 0x081      | `_Tuning`          | 25    | part           | +10  | 0xFF | 0..255          |
| 0x082      | `_KeyShift`        | 25    | part           | +9   | 0x7F | 52..76          |
| 0x1B0      | `_PitchBend`       | 25    | 0xB1           | +T   | 0x7F | 0..127          |
| 0x1B2      | `_ChannelPressure` | 25    | 0xB4           | +T   | 0x7F | 0..127          |
| 0x280      | `_Drawbar16`       | 3     | 0x44/0x45/0x46 | +3   | 0x0F | 0..8            |
| 0x281      | `_Drawbar8`        | 3     | 0x44/0x45/0x46 | +3   | 0xF0 | 0..8            |
| 0x282      | `_Drawbar5_1_3`    | 3     | 0x44/0x45/0x46 | +4   | 0x0F | 0..8            |
| 0x283      | `_Drawbar4`        | 3     | 0x44/0x45/0x46 | +4   | 0xF0 | 0..8            |
| 0x284      | `_Drawbar2_2_3`    | 3     | 0x44/0x45/0x46 | +5   | 0x0F | 0..8            |
| 0x285      | `_Drawbar2`        | 3     | 0x44/0x45/0x46 | +5   | 0xF0 | 0..8            |
| 0x286      | `_Drawbar1_3_5`    | 3     | 0x44/0x45/0x46 | +6   | 0x0F | 0..8            |
| 0x287      | `_Drawbar1_1_3`    | 3     | 0x44/0x45/0x46 | +6   | 0xF0 | 0..8            |
| 0x288      | `_Drawbar1`        | 3     | 0x44/0x45/0x46 | +7   | 0x0F | 0..8            |
| 0x293      | `_DrawRelease`     | 3     | 0x44/0x45/0x46 | +2   | 0x0F | 0..15           |
| 0x294      | `_DrawAttack`      | 3     | 0x44/0x45/0x46 | +2   | 0xF0 | 0..15           |
| 0x2C0      | `_Perc4`           | 3     | 0x44/0x45/0x46 | +7   | 0x10 | 0..1            |
| 0x2C1      | `_Perc2_2_3`       | 3     | 0x44/0x45/0x46 | +7   | 0x20 | 0..1            |
| 0x2CB      | `_PercLevel`       | 3     | 0x44/0x45/0x46 | +1   | 0xF0 | 0..15           |
| 0x2CC      | `_PercDecay`       | 3     | 0x44/0x45/0x46 | +1   | 0x0F | 0..15           |
| 0x400      | `_LocalControl`    | 26    | part           | +13  | 0x20 | 0..1            |
| 0x401      | `_MidiChannel`     | 26    | part           | +13  | 0x0F | 0..15           |
| 0x402      | `_MidiTransmitOn`  | 26    | part           | +13  | 0x40 | 0..1            |
| 0x403      | `_MidiReceiveOn`   | 26    | part           | +13  | 0x80 | 0..1            |
| 0x404      | `_MidiOctave`      | 26    | part           | +12  | 0x07 | 0..127          |
| 0x600      | `_SustainLength`   | 26    | part           | +4   | 0x07 | 0..7            |
| 0x601      | `_SustainPedal`    | 26    | part           | +4   | 0x10 | 0..1            |
| 0x602      | `_KeyScaling`      | 26    | part           | +12  | 0x08 | 0..1            |
| 0x603      | `_GlidePedal`      | 26    | part           | +12  | 0x20 | 0..1            |
| 0x604      | `_PartExp`         | 26    | part           | +4   | 0x20 | 0..1            |
| 0x606      | `_AfterTouch`      | 26    | part           | +12  | 0x10 | 0..1            |

`0x080`-`0x082` are BEND RANGE (0-12), TUNING and KEY SHIFT (64 ± 12). `0x402` is the
part's MIDI TRANSMIT gate and `0x403` its RECEIVE gate: `LswMidiChannel` prints `OFF` instead of `CH n` when
`0x402` is 0, and the CHANNEL column of the MIDI PART SETTING grid sets or clears both together (`0x402` was
called `_MidiChannelOn` until round 3). `0x078`, `0x1B0` and `0x1B2` live in arrays with one byte per part
(records `0xAE`, `0xB1`, `0xB4`, byte `+T`): writing them sends the part an All Sound Off (controller 120), a pitch
bend or a channel pressure message (`SndPart_SetParam`). `0x404` is the OCTAVE column of that grid, a 3-bit signed
shift (-3..+3); `0x2C0` / `0x2C1` are the DIGITAL DRAWBAR percussion 4' and 2 2/3' switches.

## Global keys

Keys outside the part namespace each name one setting. These are the ones the firmware
identifies. The grids' row captions come from their widgets' `fixedrow` strings
(OVERALL TOUCH SENSITIVITY, FOOT CONTROLLERS, VOCALIST WORKSTATION). The "MIDI IN/OUT"
rows come from `InOutGridCheck`, and the effect switches from the cases of
`SndParam_ApplySystemParam`.

| key     | name                                      | record | byte | mask | range   | basis                                                                  |
|---------|-------------------------------------------|--------|------|------|---------|------------------------------------------------------------------------|
| 0x00003 | `SndParam_Transpose`                      | 0x70   | +2   | 0xFF | 0..11   | TRANSPOSE (AcTranspose)                                                |
| 0x00004 | `SndParam_Tempo`                          | 0x48   | +8   | 0xFF | 40..255 | record 0x48 +8 (SeqTimer_PostTempoUpdate)                              |
| 0x00005 | `SndParam_Tempo_Bit8`                     | 0x48   | +9   | 0x01 | 0..1    | tempo, bit 8                                                           |
| 0x000C0 | `SndParam_GmOnOff`                        | 0x91   | +3   | 0x04 | 0..1    | GmOnOffFunc; GM screen YES                                             |
| 0x00100 | `SndParam_InitialTouch_VelocitySense`     | 0x93   | +0   | 0x0F | 0..9    | OVERALL TOUCH SENSITIVITY grid, row VELOCITY SENSE                     |
| 0x00102 | `SndParam_AfterTouch_Curve`               | 0x93   | +5   | 0xFF | 1..10   | OVERALL TOUCH SENSITIVITY grid, AFTER TOUCH rows                       |
| 0x00103 | `SndParam_AfterTouch_Threshold`           | 0x93   | +6   | 0x7F | 1..127  | OVERALL TOUCH SENSITIVITY grid, AFTER TOUCH rows                       |
| 0x00104 | `SndParam_AfterTouch_OnOff`               | 0x93   | +6   | 0x80 | 0..1    | OVERALL TOUCH SENSITIVITY grid, AFTER TOUCH rows                       |
| 0x00300 | `SndParam_PanelMemory_Number`             | 0x98   | +1   | 0x7F | 0..80   | MainGetPmemName: bank = (n - 1) >> 3                                   |
| 0x00302 | `SndParam_PanelMemory_Mode`               | 0x98   | +0   | 0x40 | 0..1    | PANEL MEMORY MODE box (PmemModeBoxProc)                                |
| 0x00400 | `SndParam_MusicStyleArranger_OnOff`       | 0x98   | +3   | 0x01 | 0..1    | MUSIC STYLE ARRANGER LED                                               |
| 0x00401 | `SndParam_MusicStyleArranger_Mode`        | 0x98   | +3   | 0x70 | 1..3    | MUSIC STYLE ARRANGER mode setting                                      |
| 0x02100 | `SndParam_MidiIn_Right1Input`             | 0x80   | +3   | 0x01 | 0..1    | MIDI IN/OUT grid (InOutGridCheck)                                      |
| 0x02101 | `SndParam_MidiIn_AutoPlayChord`           | 0x80   | +3   | 0x04 | 0..1    | MIDI IN/OUT grid (InOutGridCheck)                                      |
| 0x02181 | `SndParam_MidiOut_TechniChord`            | 0x80   | +3   | 0x80 | 0..1    | MIDI IN/OUT grid (InOutGridCheck)                                      |
| 0x02182 | `SndParam_MidiOut_DrumPattern`            | 0x80   | +0   | 0x40 | 0..1    | MIDI IN/OUT grid (InOutGridCheck)                                      |
| 0x02183 | `SndParam_MidiOut_AutoPlayChord`          | 0x80   | +3   | 0x40 | 0..1    | MIDI IN/OUT grid (InOutGridCheck)                                      |
| 0x02184 | `SndParam_MidiOut_Transpose`              | 0x80   | +0   | 0x20 | 0..1    | MIDI IN/OUT grid (InOutGridCheck)                                      |
| 0x02200 | `SndParam_MidiRealtime_Clock`             | 0x80   | +0   | 0x04 | 0..1    | MIDI REALTIME MESSAGES screen                                          |
| 0x02201 | `SndParam_MidiCommon_ProgramChangeMode`   | 0x80   | +0   | 0x03 | 0..3    | MIDI COMMON SETTING grid (ComSetGridCheck)                             |
| 0x02202 | `SndParam_MidiCommon_PrgChangeToPmem`     | 0x80   | +0   | 0x08 | 0..1    | MIDI COMMON SETTING grid (ComSetGridCheck)                             |
| 0x02203 | `SndParam_MidiCommon_NoteOnly`            | 0x80   | +0   | 0x10 | 0..1    | MIDI COMMON SETTING grid (ComSetGridCheck)                             |
| 0x02205 | `SndParam_MidiCommon_DrumsType`           | 0x80   | +2   | 0x18 | 0..3    | MIDI COMMON SETTING grid (ComSetGridCheck)                             |
| 0x02280 | `SndParam_MidiCommon_SongSelect`          | 0x80   | +1   | 0x08 | 0..1    | MIDI COMMON SETTING grid (ComSetGridCheck)                             |
| 0x02281 | `SndParam_MidiRealtime_Commands`          | 0x80   | +2   | 0x04 | 0..1    | MIDI REALTIME MESSAGES screen                                          |
| 0x02282 | `SndParam_MidiCommon_RealtimeSysex`       | 0x80   | +6   | 0x08 | 0..1    | MIDI COMMON SETTING grid (ComSetGridCheck)                             |
| 0x0228A | `SndParam_MidiCtlMsg_ProgramChange`       | 0x80   | +7   | 0x10 | 0..1    | MIDI CONTROL MESSAGES grid (CtlMsgGridCheck)                           |
| 0x0228B | `SndParam_MidiCtlMsg_AfterTouch`          | 0x80   | +7   | 0x20 | 0..1    | MIDI CONTROL MESSAGES grid (CtlMsgGridCheck)                           |
| 0x0228C | `SndParam_MidiCtlMsg_PitchBend`           | 0x80   | +7   | 0x40 | 0..1    | MIDI CONTROL MESSAGES grid (CtlMsgGridCheck)                           |
| 0x0228D | `SndParam_MidiCtlMsg_BankSelect`          | 0x80   | +8   | 0x80 | 0..1    | MIDI CONTROL MESSAGES grid (CtlMsgGridCheck)                           |
| 0x0228E | `SndParam_MidiCtlMsg_Volume`              | 0x80   | +8   | 0x04 | 0..1    | MIDI CONTROL MESSAGES grid (CtlMsgGridCheck)                           |
| 0x0228F | `SndParam_MidiCtlMsg_Expression`          | 0x80   | +8   | 0x08 | 0..1    | MIDI CONTROL MESSAGES grid (CtlMsgGridCheck)                           |
| 0x02290 | `SndParam_MidiCtlMsg_Pan`                 | 0x80   | +8   | 0x10 | 0..1    | MIDI CONTROL MESSAGES grid (CtlMsgGridCheck)                           |
| 0x02291 | `SndParam_MidiCtlMsg_Sustain`             | 0x80   | +8   | 0x01 | 0..1    | MIDI CONTROL MESSAGES grid (CtlMsgGridCheck)                           |
| 0x02294 | `SndParam_MidiCtlMsg_EffectReverb`        | 0x80   | +8   | 0x20 | 0..1    | MIDI CONTROL MESSAGES grid (CtlMsgGridCheck)                           |
| 0x02295 | `SndParam_MidiCtlMsg_Modulation`          | 0x80   | +8   | 0x02 | 0..1    | MIDI CONTROL MESSAGES grid (CtlMsgGridCheck)                           |
| 0x02296 | `SndParam_MidiCtlMsg_Tuning`              | 0x80   | +7   | 0x02 | 0..1    | MIDI CONTROL MESSAGES grid (CtlMsgGridCheck)                           |
| 0x02298 | `SndParam_MidiCtlMsg_BendRange`           | 0x80   | +7   | 0x01 | 0..1    | MIDI CONTROL MESSAGES grid (CtlMsgGridCheck)                           |
| 0x02299 | `SndParam_MidiCtlMsg_ResetAllControllers` | 0x80   | +9   | 0x01 | 0..1    | MIDI CONTROL MESSAGES grid (CtlMsgGridCheck)                           |
| 0x0229A | `SndParam_MidiCommon_FadeInOut`           | 0x80   | +1   | 0x04 | 0..1    | MIDI COMMON SETTING grid (ComSetGridCheck)                             |
| 0x02880 | `SndParam_FootCtrl_ExpressionPedal`       | 0x99   | +2   | 0xFF | 0..199  | FOOT CONTROLLERS grid (FSWAssGrid)                                     |
| 0x02886 | `SndParam_FootCtrl_FootSwitch1`           | 0x99   | +4   | 0xFF | 0..199  | FOOT CONTROLLERS grid (FSWAssGrid)                                     |
| 0x02888 | `SndParam_FootCtrl_FootSwitch2`           | 0x99   | +5   | 0xFF | 0..199  | FOOT CONTROLLERS grid (FSWAssGrid)                                     |
| 0x0288A | `SndParam_FootCtrl_FootContSw1`           | 0x99   | +6   | 0xFF | 0..199  | FOOT CONTROLLERS grid (FSWAssGrid)                                     |
| 0x0288C | `SndParam_FootCtrl_FootContSw2`           | 0x99   | +7   | 0xFF | 0..199  | FOOT CONTROLLERS grid (FSWAssGrid)                                     |
| 0x0288E | `SndParam_FootCtrl_FootContSw3`           | 0x99   | +8   | 0xFF | 0..199  | FOOT CONTROLLERS grid (FSWAssGrid)                                     |
| 0x02890 | `SndParam_FootCtrl_FootContSw4`           | 0x99   | +9   | 0xFF | 0..199  | FOOT CONTROLLERS grid (FSWAssGrid)                                     |
| 0x02900 | `SndParam_PmemFilter_RhythmSelection`     | 0x98   | +7   | 0x01 | 0..1    | panel memory EXPAND MODE FILTER grid                                   |
| 0x02901 | `SndParam_PmemFilter_Tempo`               | 0x98   | +7   | 0x02 | 0..1    | panel memory EXPAND MODE FILTER grid                                   |
| 0x02902 | `SndParam_PmemFilter_SplitPoint`          | 0x98   | +7   | 0x04 | 0..1    | panel memory EXPAND MODE FILTER grid                                   |
| 0x02903 | `SndParam_PmemFilter_Transpose`           | 0x98   | +7   | 0x08 | 0..1    | panel memory EXPAND MODE FILTER grid                                   |
| 0x02904 | `SndParam_PmemFilter_ApcMemory`           | 0x98   | +7   | 0x10 | 0..1    | panel memory EXPAND MODE FILTER grid                                   |
| 0x02905 | `SndParam_PmemFilter_Midi`                | 0x98   | +7   | 0x20 | 0..1    | panel memory EXPAND MODE FILTER grid                                   |
| 0x02906 | `SndParam_PmemFilter_KeyScale`            | 0x98   | +7   | 0x40 | 0..1    | panel memory EXPAND MODE FILTER grid                                   |
| 0x02907 | `SndParam_PmemFilter_Reverb`              | 0x98   | +7   | 0x80 | 0..1    | panel memory EXPAND MODE FILTER grid                                   |
| 0x02908 | `SndParam_PmemFilter_DspEffect`           | 0x98   | +8   | 0x01 | 0..1    | panel memory EXPAND MODE FILTER grid                                   |
| 0x02909 | `SndParam_PmemFilter_Part4To16`           | 0x98   | +8   | 0x02 | 0..1    | panel memory EXPAND MODE FILTER grid                                   |
| 0x0290A | `SndParam_PmemFilter_FootCtrl`            | 0x98   | +8   | 0x04 | 0..1    | panel memory EXPAND MODE FILTER grid                                   |
| 0x0290B | `SndParam_PmemFilter_MicLevelReverb`      | 0x98   | +8   | 0x08 | 0..1    | panel memory EXPAND MODE FILTER grid                                   |
| 0x0290C | `SndParam_PmemFilter_FadeInOut`           | 0x98   | +8   | 0x10 | 0..1    | panel memory EXPAND MODE FILTER grid                                   |
| 0x0290D | `SndParam_PmemFilter_R1R2Octave`          | 0x98   | +8   | 0x20 | 0..1    | panel memory EXPAND MODE FILTER grid                                   |
| 0x0290E | `SndParam_PmemFilter_Vocalist`            | 0x98   | +8   | 0x40 | 0..1    | panel memory EXPAND MODE FILTER grid                                   |
| 0x0290F | `SndParam_PmemFilter_AcousticIllusion`    | 0x98   | +8   | 0x80 | 0..1    | panel memory EXPAND MODE FILTER grid                                   |
| 0x02910 | `SndParam_PmemFilter_Equalizer`           | 0x98   | +9   | 0x01 | 0..1    | panel memory EXPAND MODE FILTER grid                                   |
| 0x02911 | `SndParam_PmemFilter_MspBank`             | 0x98   | +9   | 0x02 | 0..1    | panel memory EXPAND MODE FILTER grid                                   |
| 0x02A00 | `SndParam_FadeIn_Time`                    | 0x70   | +5   | 0xFF | 1..16   | FADE IN/OUT settings                                                   |
| 0x02A01 | `SndParam_FadeOut_Time`                   | 0x70   | +6   | 0xFF | 1..16   | FADE IN/OUT settings                                                   |
| 0x02A10 | `SndParam_FadeOut_RhythmAutoStop`         | 0x70   | +7   | 0x01 | 0..1    | FADE IN/OUT settings                                                   |
| 0x02A11 | `SndParam_FadeOut_SeqAutoStop`            | 0x70   | +7   | 0x02 | 0..1    | FADE IN/OUT settings                                                   |
| 0x02A12 | `SndParam_FadeOut_AutoReset`              | 0x70   | +7   | 0x04 | 0..1    | FADE IN/OUT settings                                                   |
| 0x02C00 | `SndParam_ComputerConnectMode`            | 0x98   | +14  | 0x03 | 0..2    | MdCmptCnct's EVT_GET_LSW_ADDRESS; 0/1/2 pick its 3 connection diagrams |
| 0x02D00 | `SndParam_Vocalist_MidiChannel`           | 0x47   | +1   | 0x1F | 0..17   | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D01 | `SndParam_Vocalist_MidiChannelSend`       | 0x47   | +0   | 0x01 | 0..1    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D02 | `SndParam_Vocalist_Program`               | 0x47   | +2   | 0x7F | 0..99   | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D03 | `SndParam_Vocalist_ProgramSend`           | 0x47   | +0   | 0x02 | 0..1    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D04 | `SndParam_Vocalist_Harmony`               | 0x47   | +3   | 0x07 | 0..7    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D05 | `SndParam_Vocalist_HarmonySend`           | 0x47   | +0   | 0x04 | 0..1    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D06 | `SndParam_Vocalist_Key`                   | 0x47   | +3   | 0xF0 | 0..11   | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D07 | `SndParam_Vocalist_KeySend`               | 0x47   | +0   | 0x08 | 0..1    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D08 | `SndParam_Vocalist_ProgChangeOption`      | 0x47   | +4   | 0xC0 | 0..3    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D09 | `SndParam_Vocalist_ProgChangeOptionSend`  | 0x47   | +0   | 0x10 | 0..1    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D0A | `SndParam_Vocalist_ControlVolume`         | 0x47   | +5   | 0x7F | 0..121  | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D0B | `SndParam_Vocalist_ControlVolumeSend`     | 0x47   | +0   | 0x20 | 0..1    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D0C | `SndParam_Vocalist_VocoderKeySplit`       | 0x47   | +6   | 0xFF | 0..255  | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D0D | `SndParam_Vocalist_VocoderKeySplitNote`   | 0x47   | +6   | 0x7F | 0..127  | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D0E | `SndParam_Vocalist_VocoderKeySplitSide`   | 0x47   | +6   | 0x80 | 0..1    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D0F | `SndParam_Vocalist_VocoderIgnore`         | 0x47   | +0   | 0x40 | 0..1    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D10 | `SndParam_Vocalist_ChordalKeySplit`       | 0x47   | +7   | 0xFF | 0..255  | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D11 | `SndParam_Vocalist_ChordalKeySplitNote`   | 0x47   | +7   | 0x7F | 0..127  | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D12 | `SndParam_Vocalist_ChordalKeySplitSide`   | 0x47   | +7   | 0x80 | 0..1    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D13 | `SndParam_Vocalist_ChordalIgnore`         | 0x47   | +0   | 0x80 | 0..1    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x04001 | `SndParam_TotalExpression`                | 0xB0   | +1   | 0x7F | 0..127  | TOTAL EXPRESSION (function code 182)                                   |
| 0x04002 | `SndParam_ReverbOnOff`                    | 0x60   | +1   | 0x80 | 0..127  | SndParam_ApplySystemParam case                                         |
| 0x04003 | `SndParam_RotarySpeedSwitch`              | 0x70   | +0   | 0x04 | 0..1    | rotary speed: COMM 0x23 (DSP_Set_RotarySpeed), TREMOLO SLOW/FAST       |
| 0x04004 | `SndParam_AcousticIllusionOnOff`          | 0x60   | +1   | 0x40 | 0..1    | SndParam_ApplySystemParam case                                         |
| 0x04005 | `SndParam_Fade_Level`                     | 0xB0   | +3   | 0x7F | 0..127  | fade engine (output gain)                                              |
| 0x04006 | `SndParam_EqualizerOnOff`                 | 0x60   | +1   | 0x20 | 0..1    | SndParam_ApplySystemParam case                                         |
| 0x040C0 | `SndParam_FadeIn_OnOff`                   | 0x98   | +11  | 0x80 | 0..1    | FADE IN LED                                                            |
| 0x040C1 | `SndParam_FadeOut_OnOff`                  | 0x98   | +11  | 0x40 | 0..1    | FADE OUT LED                                                           |
| 0x040E0 | `SndParam_R1R2Octave`                     | 0x90   | +4   | 0xFF | 40..88  | R1/R2 OCTAVE LED; R12OctaveFunc                                        |
| 0x04100 | `SndParam_Conductor`                      | 0x90   | +0   | 0x1F | 0..5    | CONDUCTOR LED                                                          |
| 0x04140 | `SndParam_Mic_ReverbOnOff`                | 0x43   | +0   | 0x80 | 0..1    | MIC reverb (DSP slot 3)                                                |
| 0x04141 | `SndParam_Mic_Volume`                     | 0x43   | +1   | 0x7F | 0..127  | mixer channel 27 MIC (AcMixerVol_Channels)                             |
| 0x04142 | `SndParam_Mic_Mute`                       | 0x43   | +1   | 0x80 | 0..1    | mixer channel 27 MIC (AcMixerVol_Channels)                             |
| 0x04180 | `SndParam_SplitPoint_Preset`              | 0x70   | +0   | 0x03 | 0..3    | split point (SplitPointFunc, AcFreeSplit)                              |
| 0x04181 | `SndParam_SplitPoint_Note`                | 0x70   | +1   | 0x7F | 21..108 | split point (SplitPointFunc, AcFreeSplit)                              |
| 0x04200 | `SndParam_TechniChord_OnOff`              | 0x48   | +4   | 0x40 | 0..1    | TECHNI CHORD LED                                                       |
| 0x04201 | `SndParam_Orchestrator`                   | 0x70   | +3   | 0xFF | 0..255  | LswOrchestrator's EVT_GET_LSW_ADDRESS                                  |
| 0x04202 | `SndParam_TechniChord_Type`               | 0x70   | +4   | 0x0F | 0..13   | TECHNI-CHORD type buttons (IvSdtecd1Proc)                              |
| 0x04280 | `SndParam_ScaleTune_OnOff`                | 0x92   | +1   | 0x80 | 0..1    | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x04281 | `SndParam_ScaleTune_Type`                 | 0x92   | +0   | 0xFF | 0..128  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x04282 | `SndParam_ScaleTune_Key`                  | 0x92   | +1   | 0x0F | 0..11   | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x04283 | `SndParam_ScaleTune_UserNote0`            | 0x92   | +2   | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x04284 | `SndParam_ScaleTune_UserNote1`            | 0x92   | +3   | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x04285 | `SndParam_ScaleTune_UserNote2`            | 0x92   | +4   | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x04286 | `SndParam_ScaleTune_UserNote3`            | 0x92   | +5   | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x04287 | `SndParam_ScaleTune_UserNote4`            | 0x92   | +6   | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x04288 | `SndParam_ScaleTune_UserNote5`            | 0x92   | +7   | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x04289 | `SndParam_ScaleTune_UserNote6`            | 0x92   | +8   | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x0428A | `SndParam_ScaleTune_UserNote7`            | 0x92   | +9   | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x0428B | `SndParam_ScaleTune_UserNote8`            | 0x92   | +10  | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x0428C | `SndParam_ScaleTune_UserNote9`            | 0x92   | +11  | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x0428D | `SndParam_ScaleTune_UserNote10`           | 0x92   | +12  | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x0428E | `SndParam_ScaleTune_UserNote11`           | 0x92   | +13  | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x04900 | `SndParam_DspEffect_Algorithm`            | 0x61   | +0   | 0xFF | 0..255  | format-3 importer, slot 0 (record 0x61)                                |
| 0x04B00 | `SndParam_DigitalReverb_Algorithm`        | 0x63   | +0   | 0xFF | 0..255  | format-3 importer, slot 1 (record 0x63)                                |
| 0x04C00 | `SndParam_Equalizer_Algorithm`            | 0x64   | +0   | 0xFF | 0..255  | DSP slot 4 algorithm                                                   |
| 0x04D00 | `SndParam_AcousticIllusion_Algorithm`     | 0x65   | +0   | 0xFF | 0..255  | DSP slot 2 algorithm                                                   |
| 0x04E00 | `SndParam_MicReverb_Algorithm`            | 0x66   | +0   | 0xFF | 0..255  | DSP slot 3 algorithm                                                   |
| 0x05000 | `SndParam_MidiIn_VelocityMode`            | 0x80   | +10  | 0x03 | 0..2    | MIDI IN/OUT grid (InOutGridCheck)                                      |
| 0x05001 | `SndParam_MidiIn_VelocityOffset`          | 0x80   | +11  | 0xFF | 0..255  | MIDI IN/OUT grid (InOutGridCheck)                                      |
| 0x05002 | `SndParam_MidiIn_VelocityFixed`           | 0x80   | +12  | 0xFF | 1..127  | MIDI IN/OUT grid (InOutGridCheck)                                      |
| 0x0E807 | `SndParam_Metronome_Volume`               | 0x98   | +4   | 0x7F | 0..127  | mixer channel 26 METR (AcMixerVol_Channels)                            |
| 0x0E808 | `SndParam_Metronome_Mute`                 | 0x98   | +4   | 0x80 | 0..1    | mixer channel 26 METR (AcMixerVol_Channels)                            |
| 0x28000 | `SndParam_Style_Number`                   | 0x48   | +0   | 0xFF | 0..255  | current style (PanelButton_Variation)                                  |
| 0x28001 | `SndParam_Style_Bank`                     | 0x48   | +1   | 0x7F | 0..7    | current style (PanelButton_Variation)                                  |
| 0x28002 | `SndParam_Style_Variation`                | 0x48   | +7   | 0x30 | 0..3    | VARIATION LEDs                                                         |
| 0x28080 | `SndParam_Apc_Mode`                       | 0x48   | +3   | 0x07 | 0..3    | AUTO PLAY CHORD LEDs                                                   |
| 0x28081 | `SndParam_Apc_Memory`                     | 0x48   | +3   | 0x08 | 0..1    | APC settings (ApcOnOffFunc / ApcOnBasFunc)                             |
| 0x28082 | `SndParam_LeftHold`                       | 0x90   | +3   | 0x01 | 0..1    | LswLeftHold's EVT_GET_LSW_ADDRESS                                      |
| 0x28083 | `SndParam_Apc_OnBass`                     | 0x90   | +3   | 0x02 | 0..1    | APC settings (ApcOnOffFunc / ApcOnBasFunc)                             |
| 0x28100 | `SndParam_Style_FillIn`                   | 0x48   | +5   | 0xC0 | 0..2    | panel LED (style record)                                               |
| 0x28102 | `SndParam_Style_Ending`                   | 0x48   | +5   | 0x30 | 0..2    | panel LED (style record)                                               |
| 0x28103 | `SndParam_Style_SynchroBreak`             | 0x48   | +5   | 0x02 | 0..1    | panel LED (style record)                                               |
| 0x28801 | `SndParam_Msp_Volume`                     | 0x72   | +3   | 0x7F | 0..127  | LswVolume / LswMute / LswReverb answer for part 0x17                   |
| 0x28802 | `SndParam_Msp_Reverb`                     | 0x72   | +7   | 0x7F | 0..127  | LswVolume / LswMute / LswReverb answer for part 0x17                   |
| 0x2880B | `SndParam_Msp_Mute`                       | 0x72   | +3   | 0x80 | 0..1    | LswVolume / LswMute / LswReverb answer for part 0x17                   |
| 0x2A000 | `SndParam_MidiCommon_ApcControl`          | 0x80   | +9   | 0x20 | 0..1    | MIDI COMMON SETTING grid (ComSetGridCheck)                             |
| 0x2A001 | `SndParam_MidiCommon_IntroFillInEnding`   | 0x80   | +9   | 0x40 | 0..1    | MIDI COMMON SETTING grid (ComSetGridCheck)                             |

Notes on the table:

* the FOOT CONTROLLERS values are function numbers (0-199). Record `0x99` also holds one
  flag bit per controller and six more function bytes that the KN5000's grid does not
  show (keys `0x2892`-`0x289C`);
* `0x2C00` is the COMPUTER CONNECT setting: 0, 1 ("KN as master") and 2 ("KN as slave")
  pick one of three MIDI connection diagrams;
* `0x4900` and `0x4B00` are the algorithm bytes of effect slots 0 (DSP EFFECT) and 1
  (DIGITAL REVERB). Each slot's namespace is `0x4?00` algorithm, `0x4?04` parameter
  count, `0x4?10+i` parameter `i`.

## Still unidentified

55 of the 972 registered descriptors per firmware version keep address-derived names; the
other 917 have names. What is known about the 55:

* 0x18205 + 0x400*T (Lsw 0x605), parts 0x00-0x19 -- part byte +22 bit 0. No reader of number 0x605 (also searched in decimal, 1541) and no access to byte +22; SndPart_SetParam ignores it. README-lsw-part-record-fields.md calls +22 the only declared bit no code touches.
* 0x08221 / 0x08621 / 0x08A21 (Lsw 0x221) -- drawbar records 0x44-0x46 +8 low nibble, range 0..1. Not in the drawbar screen's 15-entry control table (MainMemDrawControl) and no reader of byte +8; the screen's TREMOLO SLOW/FAST is the global 0x4003.
* 0x00C1 -- record 0x91 +3 bit 0 (inverted). Set to 1 only by SoundParam_InitDefaultBanks mode 2 (note_voice_mapping.s:23449), which clears GM (0xC0) and loads its own channel map. Mode 2 is used by Epilogue_Prologue/_2 (:22111) from a file-kind dispatch (SeqVoice_PopIzReturn_Prologue, :19934 area). Sent as F0 50 99 0/127. A tone-generator mode exclusive with GM, not named.
* 0x00301 -- record 0x98 +1 bit 7 (beside the panel-memory number 0x300). BitMapOut_ByteData_PresetCopy (bitmap_out_routines.s:374) does a full PanelMemory_Recall on a panel-memory number change when 0x301 = 0, else BitMapOut_CopyVoicePreset9 (parts 0-2 bytes +14/+15/+17 only).
* 0x04080, 0x04081 -- record 0x98 +2 bits 7, 6. 0x4080 is sent as F0 50 85 <v> (sub-CPU Voice_SystemMsg 0x85, labelled Voice_SetKeyShiftEnable there, a guessed name) and cleared at demo setup (file_demo_proc.s:933, mislabelled Timer7_DisableInterrupt). FswAsIniFunc clears it. No reader of 0x4081 found.
* record 0x99 flags 0x2882, 0x2887, 0x2889, 0x288B, 0x288D, 0x288F, 0x2891, 0x2893, 0x2895, 0x2897, 0x2899, 0x289B, 0x289D; function bytes 0x2881 (+3), 0x2892/0x2894/0x2896/0x2898/0x289A/0x289C (+10..+15) -- record 0x99. Each odd key is a 1-bit companion of the function byte at key-1. The FOOT CONTROLLERS grid and the PanelAction_FootSwitch*/FootController* handlers read only 0x2880/0x2886..0x2890. No reader of the flag bits or the unshown bytes except the whole-record copy under the FOOT CONT. SETTING filter row.

Two more have probable names that are not applied: `0x4000` is probably the MAIN VOLUME
slider level, and `0x4A00` the algorithm byte of a second namespace sharing the DIGITAL
REVERB slot (`sndparam-r3/inferred.json` says what would confirm each).

## Related pages

* [Sound Parameter Protocol](/sound-parameter-protocol/): how a changed value travels
  to the sub CPU and the DSP
* [MIDI Subsystem](/midi-subsystem/)
* [UI Framework](/ui-framework/)
