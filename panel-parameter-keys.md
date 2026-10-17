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
`analysis/disk-format-probes/README-lsw-param-namespace-map.md` (sections 1-8). The
tables below are printed by `scripts/renaming/gen_sndparam_desc_names_r2.py
--markdown` and `--markdown-parts` from the v10 ROM.

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

| Lsw number | field            | parts | record         | byte | mask | range           |
|------------|------------------|-------|----------------|------|------|-----------------|
| 0x000      | `_Sound`         | 25    | part           | +0   | 0xFF | 0..255          |
| 0x001      | `_Modulation`    | 25    | 0xB2           | +0   | 0x7F | 0..127 (varies) |
| 0x007      | `_Volume`        | 25    | part           | +3   | 0x7F | 0..127          |
| 0x008      | `_Mute`          | 25    | part           | +3   | 0x80 | 0..1            |
| 0x00A      | `_Pan`           | 25    | part           | +8   | 0x7F | 0..127          |
| 0x00B      | `_Expression`    | 25    | 0xB3           | +0   | 0x7F | 0..127 (varies) |
| 0x020      | `_Bank`          | 25    | part           | +1   | 0x7F | 0..255          |
| 0x040      | `_Sustain`       | 25    | part           | +4   | 0x08 | 0..127          |
| 0x05B      | `_ReverbSend`    | 25    | part           | +7   | 0x7F | 0..127          |
| 0x05D      | `_DspEffect`     | 25    | part           | +5   | 0x7F | 0..127          |
| 0x05E      | `_DigitalEffect` | 25    | part           | +4   | 0x40 | 0..127          |
| 0x080      | `_BendRange`     | 25    | part           | +11  | 0x7F | 0..12           |
| 0x081      | `_Tuning`        | 25    | part           | +10  | 0xFF | 0..255          |
| 0x082      | `_KeyShift`      | 25    | part           | +9   | 0x7F | 52..76          |
| 0x280      | `_Drawbar16`     | 3     | 0x44/0x45/0x46 | +3   | 0x0F | 0..8            |
| 0x281      | `_Drawbar8`      | 3     | 0x44/0x45/0x46 | +3   | 0xF0 | 0..8            |
| 0x282      | `_Drawbar5_1_3`  | 3     | 0x44/0x45/0x46 | +4   | 0x0F | 0..8            |
| 0x283      | `_Drawbar4`      | 3     | 0x44/0x45/0x46 | +4   | 0xF0 | 0..8            |
| 0x284      | `_Drawbar2_2_3`  | 3     | 0x44/0x45/0x46 | +5   | 0x0F | 0..8            |
| 0x285      | `_Drawbar2`      | 3     | 0x44/0x45/0x46 | +5   | 0xF0 | 0..8            |
| 0x286      | `_Drawbar1_3_5`  | 3     | 0x44/0x45/0x46 | +6   | 0x0F | 0..8            |
| 0x287      | `_Drawbar1_1_3`  | 3     | 0x44/0x45/0x46 | +6   | 0xF0 | 0..8            |
| 0x288      | `_Drawbar1`      | 3     | 0x44/0x45/0x46 | +7   | 0x0F | 0..8            |
| 0x293      | `_DrawRelease`   | 3     | 0x44/0x45/0x46 | +2   | 0x0F | 0..15           |
| 0x294      | `_DrawAttack`    | 3     | 0x44/0x45/0x46 | +2   | 0xF0 | 0..15           |
| 0x2CB      | `_PercLevel`     | 3     | 0x44/0x45/0x46 | +1   | 0xF0 | 0..15           |
| 0x2CC      | `_PercDecay`     | 3     | 0x44/0x45/0x46 | +1   | 0x0F | 0..15           |
| 0x400      | `_LocalControl`  | 26    | part           | +13  | 0x20 | 0..1            |
| 0x401      | `_MidiChannel`   | 26    | part           | +13  | 0x0F | 0..15           |
| 0x402      | `_MidiChannelOn` | 26    | part           | +13  | 0x40 | 0..1            |
| 0x600      | `_SustainLength` | 26    | part           | +4   | 0x07 | 0..7            |
| 0x601      | `_SustainPedal`  | 26    | part           | +4   | 0x10 | 0..1            |
| 0x602      | `_KeyScaling`    | 26    | part           | +12  | 0x08 | 0..1            |
| 0x603      | `_GlidePedal`    | 26    | part           | +12  | 0x20 | 0..1            |
| 0x604      | `_PartExp`       | 26    | part           | +4   | 0x20 | 0..1            |
| 0x606      | `_AfterTouch`    | 26    | part           | +12  | 0x10 | 0..1            |

`0x080`-`0x082` are BEND RANGE (0-12), TUNING and KEY SHIFT (64 ± 12). `0x402` is the
part's MIDI-channel ON flag: `LswMidiChannel` prints `OFF` instead of `CH n` when it is 0.

## Global keys

Keys outside the part namespace each name one setting. These are the ones the firmware
identifies. The grids' row captions come from their widgets' `fixedrow` strings
(OVERALL TOUCH SENSITIVITY, FOOT CONTROLLERS, VOCALIST WORKSTATION). The "MIDI IN/OUT"
rows come from `InOutGridCheck`, and the effect switches from the cases of
`SndParam_ApplySystemParam`.

| key     | name                                     | record | byte | mask | range   | basis                                                                  |
|---------|------------------------------------------|--------|------|------|---------|------------------------------------------------------------------------|
| 0x00004 | `SndParam_Tempo`                         | 0x48   | +8   | 0xFF | 40..255 | record 0x48 +8 (SeqTimer_PostTempoUpdate)                              |
| 0x00100 | `SndParam_InitialTouch_VelocitySense`    | 0x93   | +0   | 0x0F | 0..9    | OVERALL TOUCH SENSITIVITY grid, row VELOCITY SENSE                     |
| 0x00102 | `SndParam_AfterTouch_Curve`              | 0x93   | +5   | 0xFF | 1..10   | OVERALL TOUCH SENSITIVITY grid, AFTER TOUCH rows                       |
| 0x00103 | `SndParam_AfterTouch_Threshold`          | 0x93   | +6   | 0x7F | 1..127  | OVERALL TOUCH SENSITIVITY grid, AFTER TOUCH rows                       |
| 0x00104 | `SndParam_AfterTouch_OnOff`              | 0x93   | +6   | 0x80 | 0..1    | OVERALL TOUCH SENSITIVITY grid, AFTER TOUCH rows                       |
| 0x00300 | `SndParam_PanelMemory_Number`            | 0x98   | +1   | 0x7F | 0..80   | MainGetPmemName: bank = (n - 1) >> 3                                   |
| 0x02100 | `SndParam_MidiIn_Right1Input`            | 0x80   | +3   | 0x01 | 0..1    | MIDI IN/OUT grid (InOutGridCheck)                                      |
| 0x02101 | `SndParam_MidiIn_AutoPlayChord`          | 0x80   | +3   | 0x04 | 0..1    | MIDI IN/OUT grid (InOutGridCheck)                                      |
| 0x02181 | `SndParam_MidiOut_TechniChord`           | 0x80   | +3   | 0x80 | 0..1    | MIDI IN/OUT grid (InOutGridCheck)                                      |
| 0x02182 | `SndParam_MidiOut_DrumPattern`           | 0x80   | +0   | 0x40 | 0..1    | MIDI IN/OUT grid (InOutGridCheck)                                      |
| 0x02183 | `SndParam_MidiOut_AutoPlayChord`         | 0x80   | +3   | 0x40 | 0..1    | MIDI IN/OUT grid (InOutGridCheck)                                      |
| 0x02184 | `SndParam_MidiOut_Transpose`             | 0x80   | +0   | 0x20 | 0..1    | MIDI IN/OUT grid (InOutGridCheck)                                      |
| 0x02880 | `SndParam_FootCtrl_ExpressionPedal`      | 0x99   | +2   | 0xFF | 0..199  | FOOT CONTROLLERS grid (FSWAssGrid)                                     |
| 0x02886 | `SndParam_FootCtrl_FootSwitch1`          | 0x99   | +4   | 0xFF | 0..199  | FOOT CONTROLLERS grid (FSWAssGrid)                                     |
| 0x02888 | `SndParam_FootCtrl_FootSwitch2`          | 0x99   | +5   | 0xFF | 0..199  | FOOT CONTROLLERS grid (FSWAssGrid)                                     |
| 0x0288A | `SndParam_FootCtrl_FootContSw1`          | 0x99   | +6   | 0xFF | 0..199  | FOOT CONTROLLERS grid (FSWAssGrid)                                     |
| 0x0288C | `SndParam_FootCtrl_FootContSw2`          | 0x99   | +7   | 0xFF | 0..199  | FOOT CONTROLLERS grid (FSWAssGrid)                                     |
| 0x0288E | `SndParam_FootCtrl_FootContSw3`          | 0x99   | +8   | 0xFF | 0..199  | FOOT CONTROLLERS grid (FSWAssGrid)                                     |
| 0x02890 | `SndParam_FootCtrl_FootContSw4`          | 0x99   | +9   | 0xFF | 0..199  | FOOT CONTROLLERS grid (FSWAssGrid)                                     |
| 0x02C00 | `SndParam_ComputerConnectMode`           | 0x98   | +14  | 0x03 | 0..2    | MdCmptCnct's EVT_GET_LSW_ADDRESS; 0/1/2 pick its 3 connection diagrams |
| 0x02D00 | `SndParam_Vocalist_MidiChannel`          | 0x47   | +1   | 0x1F | 0..17   | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D01 | `SndParam_Vocalist_MidiChannelSend`      | 0x47   | +0   | 0x01 | 0..1    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D02 | `SndParam_Vocalist_Program`              | 0x47   | +2   | 0x7F | 0..99   | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D03 | `SndParam_Vocalist_ProgramSend`          | 0x47   | +0   | 0x02 | 0..1    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D04 | `SndParam_Vocalist_Harmony`              | 0x47   | +3   | 0x07 | 0..7    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D05 | `SndParam_Vocalist_HarmonySend`          | 0x47   | +0   | 0x04 | 0..1    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D06 | `SndParam_Vocalist_Key`                  | 0x47   | +3   | 0xF0 | 0..11   | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D07 | `SndParam_Vocalist_KeySend`              | 0x47   | +0   | 0x08 | 0..1    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D08 | `SndParam_Vocalist_ProgChangeOption`     | 0x47   | +4   | 0xC0 | 0..3    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D09 | `SndParam_Vocalist_ProgChangeOptionSend` | 0x47   | +0   | 0x10 | 0..1    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D0A | `SndParam_Vocalist_ControlVolume`        | 0x47   | +5   | 0x7F | 0..121  | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D0B | `SndParam_Vocalist_ControlVolumeSend`    | 0x47   | +0   | 0x20 | 0..1    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D0C | `SndParam_Vocalist_VocoderKeySplit`      | 0x47   | +6   | 0xFF | 0..255  | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D0D | `SndParam_Vocalist_VocoderKeySplitNote`  | 0x47   | +6   | 0x7F | 0..127  | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D0E | `SndParam_Vocalist_VocoderKeySplitSide`  | 0x47   | +6   | 0x80 | 0..1    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D0F | `SndParam_Vocalist_VocoderIgnore`        | 0x47   | +0   | 0x40 | 0..1    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D10 | `SndParam_Vocalist_ChordalKeySplit`      | 0x47   | +7   | 0xFF | 0..255  | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D11 | `SndParam_Vocalist_ChordalKeySplitNote`  | 0x47   | +7   | 0x7F | 0..127  | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D12 | `SndParam_Vocalist_ChordalKeySplitSide`  | 0x47   | +7   | 0x80 | 0..1    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x02D13 | `SndParam_Vocalist_ChordalIgnore`        | 0x47   | +0   | 0x80 | 0..1    | VOCALIST WORKSTATION grid (VocalistGridCheck)                          |
| 0x04002 | `SndParam_ReverbOnOff`                   | 0x60   | +1   | 0x80 | 0..127  | SndParam_ApplySystemParam case                                         |
| 0x04003 | `SndParam_DigitalEffectOnOff`            | 0x70   | +0   | 0x04 | 0..1    | SndParam_ApplySystemParam case                                         |
| 0x04004 | `SndParam_AcousticIllusionOnOff`         | 0x60   | +1   | 0x40 | 0..1    | SndParam_ApplySystemParam case                                         |
| 0x04006 | `SndParam_EqualizerOnOff`                | 0x60   | +1   | 0x20 | 0..1    | SndParam_ApplySystemParam case                                         |
| 0x04141 | `SndParam_Mic_Volume`                    | 0x43   | +1   | 0x7F | 0..127  | mixer channel 27 MIC (AcMixerVol_Channels)                             |
| 0x04142 | `SndParam_Mic_Mute`                      | 0x43   | +1   | 0x80 | 0..1    | mixer channel 27 MIC (AcMixerVol_Channels)                             |
| 0x04201 | `SndParam_Orchestrator`                  | 0x70   | +3   | 0xFF | 0..255  | LswOrchestrator's EVT_GET_LSW_ADDRESS                                  |
| 0x04280 | `SndParam_ScaleTune_OnOff`               | 0x92   | +1   | 0x80 | 0..1    | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x04281 | `SndParam_ScaleTune_Type`                | 0x92   | +0   | 0xFF | 0..128  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x04282 | `SndParam_ScaleTune_Key`                 | 0x92   | +1   | 0x0F | 0..11   | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x04283 | `SndParam_ScaleTune_UserNote0`           | 0x92   | +2   | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x04284 | `SndParam_ScaleTune_UserNote1`           | 0x92   | +3   | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x04285 | `SndParam_ScaleTune_UserNote2`           | 0x92   | +4   | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x04286 | `SndParam_ScaleTune_UserNote3`           | 0x92   | +5   | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x04287 | `SndParam_ScaleTune_UserNote4`           | 0x92   | +6   | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x04288 | `SndParam_ScaleTune_UserNote5`           | 0x92   | +7   | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x04289 | `SndParam_ScaleTune_UserNote6`           | 0x92   | +8   | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x0428A | `SndParam_ScaleTune_UserNote7`           | 0x92   | +9   | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x0428B | `SndParam_ScaleTune_UserNote8`           | 0x92   | +10  | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x0428C | `SndParam_ScaleTune_UserNote9`           | 0x92   | +11  | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x0428D | `SndParam_ScaleTune_UserNote10`          | 0x92   | +12  | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x0428E | `SndParam_ScaleTune_UserNote11`          | 0x92   | +13  | 0xFF | 0..255  | SndParam_ApplySystemParam cases; LswScaling* addresses                 |
| 0x04900 | `SndParam_DspEffect_Algorithm`           | 0x61   | +0   | 0xFF | 0..255  | format-3 importer, slot 0 (record 0x61)                                |
| 0x04B00 | `SndParam_DigitalReverb_Algorithm`       | 0x63   | +0   | 0xFF | 0..255  | format-3 importer, slot 1 (record 0x63)                                |
| 0x05000 | `SndParam_MidiIn_VelocityMode`           | 0x80   | +10  | 0x03 | 0..2    | MIDI IN/OUT grid (InOutGridCheck)                                      |
| 0x05001 | `SndParam_MidiIn_VelocityOffset`         | 0x80   | +11  | 0xFF | 0..255  | MIDI IN/OUT grid (InOutGridCheck)                                      |
| 0x05002 | `SndParam_MidiIn_VelocityFixed`          | 0x80   | +12  | 0xFF | 1..127  | MIDI IN/OUT grid (InOutGridCheck)                                      |
| 0x0E807 | `SndParam_Metronome_Volume`              | 0x98   | +4   | 0x7F | 0..127  | mixer channel 26 METR (AcMixerVol_Channels)                            |
| 0x0E808 | `SndParam_Metronome_Mute`                | 0x98   | +4   | 0x80 | 0..1    | mixer channel 26 METR (AcMixerVol_Channels)                            |
| 0x28082 | `SndParam_LeftHold`                      | 0x90   | +3   | 0x01 | 0..1    | LswLeftHold's EVT_GET_LSW_ADDRESS                                      |
| 0x28801 | `SndParam_Msp_Volume`                    | 0x72   | +3   | 0x7F | 0..127  | LswVolume / LswMute / LswReverb answer for part 0x17                   |
| 0x28802 | `SndParam_Msp_Reverb`                    | 0x72   | +7   | 0x7F | 0..127  | LswVolume / LswMute / LswReverb answer for part 0x17                   |
| 0x2880B | `SndParam_Msp_Mute`                      | 0x72   | +3   | 0x80 | 0..1    | LswVolume / LswMute / LswReverb answer for part 0x17                   |

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

259 descriptors per firmware version keep address-derived names. The firmware does not
yet tie these keys to a function or a screen:

* per part: Lsw numbers `0x403` (record `+13` bit 7), `0x404` and `0x605` (`+22` bit 0);
* drawbar records: `0x221`, `0x2C0`, `0x2C1` (`IvDrawbar` treats `0x2C1` / `0x2C0` as
  its upper / lower switch);
* the virtual per-part arrays `0xAE`, `0xB1`, `0xB4` (numbers `0x78`, `0x1B0`, `0x1B2`);
* most of the sequencer / MIDI-clock record `0x80` (22 bit flags), the digital-effect
  record `0x70`, records `0x90`, `0x91`, `0x98` and `0xB0`, the style record `0x48`, and
  the algorithm bytes of effect slots `0x62`, `0x64`, `0x65`, `0x66`.

## Related pages

* [Sound Parameter Protocol](/sound-parameter-protocol/): how a changed value travels
  to the sub CPU and the DSP
* [MIDI Subsystem](/midi-subsystem/)
* [UI Framework](/ui-framework/)
