---
layout: page
title: "Dispatch Tables Inventory"
permalink: /dispatch-tables/
---

# Dispatch Tables Inventory

This page catalogs all indirect call/jump dispatch tables found in the KN5000 ROM disassembly. These are sites where firmware computes a target address at runtime using an index into a table of function pointers or offsets.

## Current state: the dispatch-table census

Since 2026-10-05 the disassembly measures this with its dispatch-table census (`scripts/analysis/dispatch_table_census/`, run by `make dispatch-census`; snapshots in `docs/coverage/`). The latest committed snapshot, `dispatch-census-2026-10-06-31` (committed in disassembly commit `d8574de89`), finds no unused table in any KN5000 image. Every entry of every framed jump or call table lands on a labelled instruction and is spelled symbolically:

| Image                 | Framed tables | Used |
|-----------------------|---------------|------|
| Main CPU v10          | 684           | 684  |
| Main CPU v9           | 684           | 684  |
| Main CPU v7           | 681           | 681  |
| Sub-CPU payload v1.42 | 44            | 44   |
| Sub-CPU boot ROM      | 2             | 2    |
| Table data            | 13            | 13   |
| HD-AE5000             | 68            | 68   |

No `jp t, (xR+rr)` site is left whose offset table the census cannot read. A zero means none that the census detects. This is the 'jump tables resolved' component of the disassembly README's semantic score: 2,259 of 2,259 for the KN5000, a figure that also counts 83 unframed pointer runs.

## March 2026 sprint: 1,583 / 1,583 dispatch sites labelled

The rest of this page records the March 9, 2026 labelling sprint. It counted indirect-jump and indirect-call instruction sites, not tables, and found every one across the four KN5000 images below inside a semantically labelled function.

### Coverage by ROM

| ROM        | Total Sites | Coverage |
|------------|-------------|----------|
| Main CPU   | 499         | 100%     |
| Sub CPU    | 24          | 100%     |
| HDAE5000   | 1057        | 100%     |
| Table Data | 3           | 100%     |
| **Total**  | **1583**    | **100%** |

### Dispatch Site Breakdown

| Instruction Type                             | Count     | Description                                      |
|----------------------------------------------|-----------|--------------------------------------------------|
| `jp t, (xR+rr)` (written jp_dri at the time) | 316       | Offset-table indexed jumps (switch/case style)   |
| `call (xreg)`                                | 1,240     | Indirect calls through pointer tables or vtables |
| `jp (xreg)`                                  | 27        | Indirect jumps through pointer tables            |
| **Total**                                    | **1,583** |                                                  |

**Note:** In the March 2026 count the HDAE5000 extension ROM accounted for 67% of all sites (1,057). Most of its `call (xhl)` sites are calls into the main firmware's Function tables (Pattern 3): `+0x00E4` is `RootFn_RegisterObjectTable`, `+0x0100` is `RootFn_SendEvent`, and so on.

---

## Dispatch Patterns

The firmware uses three main patterns for runtime code dispatch:

### Pattern 1: Pointer Table via `call (xreg)` / `jp (xreg)`

```asm
ld c, (xsp+2)                                   ; index
extz bc
sla bc, 2                                       ; multiply by 4 (pointer size)
lda xde, (SeAmpEnv1TitleFunc_SwitchHandlers:24) ; table base
exts xbc
add xbc, xde
ld xhl, (xbc)                                   ; xhl = table[index]
call (xhl)                                      ; dispatch to handler
```

Table contains `.long` entries pointing to handler functions. Entry size is 4 bytes (24-bit addresses stored in 32-bit slots).

### Pattern 2: Offset Table via `jp t, (xR+rr)`

```asm
cp xde, 0xe                                     ; bounds check
jrl ugt, NoteEditSy_ReturnZero
add xde, xde                                    ; multiply by 2 (offset size)
add xde, NoteEditSy_HandleUpScroll_CaseTable    ; offset table (.short Case - Base)
ld de, (xde)                                    ; de = offsets[index]
lda xix, (NoteEditSy_UpScroll_Param0:24)        ; dispatch base
jp t, (xix+de)                                  ; jump to base + offset
```

Table contains 16-bit relative offsets. More compact than pointer tables. Used extensively (316 sites).

### Pattern 3: Calls through the main firmware's Function tables (HDAE5000)

```asm
ld xwa, (HDAE5000_RAM_MainWorkspacePtr:24)
ld XWA, (xwa + WS_RootFnTable)                     ; the firmware's Function table 0x100
ld_sril XHL, (xwa + RootFn_RegisterObjectTable)    ; entry 57 (offset 0xE4)
call (xhl)
```

These are not object vtables. XWA holds one of the main firmware's registered Function tables: object table 0x100, or Hama's 0x109 through `WS_HamaFnTable`. The offset is 4 × the function's index, so every call names one firmware function (`RootFn_<name>` / `HamaFn_<name>`). The HD-AE5000 makes 953 such calls to 99 functions; see [HDAE5000 Homebrew]({{ site.baseurl }}/hdae5000-homebrew/#complete-handler-table).

### Pattern 4: Two-Level Dispatch

```asm
; Level 1: byte lookup
ld a, (xix + <byte_table>)  ; byte_table[index] -> secondary index
extz wa
sll wa, ...
; Level 2: offset table
lda xix, (<offset_table>:24)
ld wa, (xix+wa)                 ; wa = offsets[index]
lda xix, (<dispatch_base>:24)
jp t, (xix+wa)                  ; jump to base + offset
```

6 sites use this cascaded pattern for more complex routing.

---

## Recently Documented (March 9, 2026)

A total of **502 dispatch labels** were created during the dispatch table documentation sprint:
- 105 dispatch site labels (jp t, (xR+rr) / call / jp instruction sites)
- 397 dispatch handler target labels (case handlers within dispatch tables)

### Phase 1: Dispatch Sites (105 labels)

The following dispatch sites were labeled with semantic names:

### Batch 1: Core Dispatch Sites (7 sites)
| Label | File | Type | Description |
|-------|------|------|-------------|
| `SeqRingBuf_WriteDispatch_Table` | kn5000_v10_program.s | call (xhl) | 8-entry sequencer ring buffer write, indexed by DRAM[1508] bits [7:5] |
| `MidiPkt_EventType_Table` | naka_dispatch.s | call (xhl) | 192-entry MIDI packet event type dispatch |
| `UIStateMachine_PrimaryDispatch` | style_data_init.s | jp (xhl) | 3-state UI state machine primary dispatch |
| `Timer_ModeDispatch` | scoop_display.s | call (xhl) | 4-entry timer mode dispatch |
| `E1DMA_TransferSetup` | style_data_init.s | call (xhl) | DMA transfer setup after SeqRingBuf dispatch |
| `VoiceSynth_CommandDispatch` | kn5000_v10_program.s | cascaded | Voice synthesis command dispatcher (DRAM[4012]) |
| `VoiceParam_CommandDispatch` | kn5000_v10_program.s | cascaded | Voice parameter command dispatcher (DRAM[4012]) |

### Batch 2: File I/O & MIDI Stream (7 sites)
| Label | File | Type | Description |
|-------|------|------|-------------|
| `RegBitManip_Dispatch` | file_io_engine.s | call (xhl) | 8-entry register bit manipulation dispatch |
| `MidiStream_ProcessorDispatch` | file_io_engine.s | call (xhl) | 8-entry MIDI stream processor A |
| `MidiStream_ProcessorDispatchB` | file_io_engine.s | call (xhl) | 8-entry MIDI stream processor B |
| `MidiStream_ProcessorDispatchC` | file_io_engine.s | call (xhl) | 16-entry MIDI stream processor C |
| `VoiceMode_ParamDispatch` | file_io_engine.s | call (xhl) | 8-entry voice mode parameter dispatch |
| `VoiceSynth_AlgoTableDispatch` | kn5000_v10_program.s | call (xhl) | 16-entry algorithm table via VoiceSynth_Algorithm_Table |
| `VoiceParam_ReadUpdateDispatch` | kn5000_v10_program.s | call (xhl) | 16-entry read-update table via VoiceParam_ReadUpdate_Table |

### Batch 3: Mode Screens UI (22 sites)
| Label | File | Description |
|-------|------|-------------|
| `TEST2FUNC_DispatchReturn` | mode_screens.s | 6-entry event dispatch (event 0x1C00013) |
| `TEST3FUNC_DispatchReturn` | mode_screens.s | 6-entry event dispatch |
| `TEST4FUNC_DispatchReturn` | mode_screens.s | 6-entry event dispatch |
| `TEST6FUNC_DispatchReturn` | mode_screens.s | 6-entry event dispatch |
| `MasterSetup_EventDispatch` | mode_screens.s | 7-entry UI event dispatch (table 0xED0D24) |
| `MstStyleAlp_EventDispatch` | mode_screens.s | 7-entry (table 0xED0D58) |
| `MstStyle_EventDispatch` | mode_screens.s | 7-entry (table 0xED0D66) |
| `MstStyle1Grid_EventDispatch` | mode_screens.s | 7-entry (table 0xED0D8A) |
| `MstStyle1_EventDispatch` | mode_screens.s | 7-entry (table 0xED0D9E) |
| `MstStyle1Sub_EventDispatch` | mode_screens.s | 7-entry (table 0xED0DC2) |
| `MstStyle1Page_EventDispatch` | mode_screens.s | 7-entry (table 0xED0E04) |
| `MstStyle2_EventDispatch` | mode_screens.s | 7-entry (table 0xED0ED2) |
| `TchSensGrid_EventDispatch` | mode_screens.s | 7-entry (table 0xED0F08) |
| `TchSens_EventDispatch` | mode_screens.s | 7-entry (table 0xED0F16) |
| `FSWAssGrid_EventDispatch` | mode_screens.s | 7-entry (table 0xED1226) |
| `FswAsIni_EventDispatch` | mode_screens.s | 6-entry (table 0xED1234) |
| `PmemPageCtl_EventDispatch` | mode_screens.s | 7-entry (table 0xED1420) |
| `PmExpFilter_EventDispatch` | mode_screens.s | 7-entry (table 0xED149A) |
| `PmExpFilter2_EventDispatch` | mode_screens.s | 7-entry (table 0xED14A8) |
| `DispTimeSet_EventDispatch` | mode_screens.s | 7-entry (table 0xED1582) |
| `MssName_EventDispatch` | mode_screens.s | 10-entry (table 0xED15AC) |
| `PmBkName_EventDispatch` | mode_screens.s | 10-entry (table 0xED15EE) |

### Batch 4: Sequencer UI (21 sites)
| Label | File | Description |
|-------|------|-------------|
| `MuteChSel_Dispatch` | sequencer_ui.s | SmfMuteChSelFunc dispatch |
| `SqTrAsPsSong_Dispatch` | sequencer_ui.s | Song track dispatch |
| `MuteChSet_Dispatch` | sequencer_ui.s | Mute channel set dispatch |
| `DemoMedDsp_Dispatch` | sequencer_ui.s | Demo medium display dispatch |
| `DPPlayDsp_Dispatch` | sequencer_ui.s | Demo play display dispatch |
| `DPPauseDsp_Dispatch` | sequencer_ui.s | Demo pause display dispatch |
| `NoteEditBox_EventDispatch1` | sequencer_ui.s | Note edit box event dispatch 1 |
| `NoteEditBox_EventDispatch2` | sequencer_ui.s | Note edit box event dispatch 2 |
| `NoteEditBox_GridDispatch` | sequencer_ui.s | Note edit box grid dispatch |
| `AcEntertainer_EventDispatch` | sequencer_ui.s | Accompaniment entertainer dispatch |
| `SndParam_Dispatch` | sequencer_ui.s | Sound parameter dispatch |
| `AccIll_Dispatch` | sequencer_ui.s | Accompaniment illustration dispatch |
| `EffectBox_Dispatch` | sequencer_ui.s | Effect box dispatch |
| `SeqAccomp_Dispatch` | sequencer_ui.s | Sequencer accompaniment dispatch |
| `SqedtFunc_OnGetTrkString` | sequencer_ui.s | Sequencer editor param dispatch |
| `SqedtFunc_OnCurToParam_CursorPos0` | sequencer_ui.s | Sequencer editor value dispatch |
| `SqedtFunc_OnChkCur_AtCursorPos0` | sequencer_ui.s | Sequencer format dispatch A |
| `SeqFormat_DispatchB` | sequencer_ui.s | Sequencer format dispatch B |
| `DspItem0_TypeDispatch` | sequencer_ui.s | DSP item 0 type dispatch |
| `Equalizer_DispatchA` | sequencer_ui.s | Equalizer dispatch A |
| `Equalizer_DispatchB` | sequencer_ui.s | Equalizer dispatch B |

### Batch 5: Voice, MIDI & Sound (21 sites)
| Label | File | Description |
|-------|------|-------------|
| `VoiceEvent_Dispatch` | note_voice_mapping.s | 14-entry voice event handler (table 0xEE8F06) |
| `SeqPerformance_EventDispatch` | note_voice_mapping.s | 6-entry sequence performance dispatch |
| `UIParam_CallbackReturn` | note_voice_mapping.s | UI parameter callback return |
| `MidiSysMsg_Dispatch` | note_voice_mapping.s | 15-entry MIDI system message dispatch |
| `SndParam_TypeDispatch` | note_voice_mapping.s | 6-entry sound parameter type dispatch |
| `SndParam_OffsetDispatch` | note_voice_mapping.s | 6-entry sound parameter offset dispatch |
| `HdaeRom_DataDispatch` | note_voice_mapping.s | 6-entry HDAE5000 data dispatch |
| `HdaeRom_AltDispatch` | note_voice_mapping.s | 6-entry HDAE5000 alt dispatch |
| `ToneGen_ParamWriteDispatch` | voice_midi_buf.s | ToneGen param write dispatch table |
| `WallHomeEdit_EventDispatch` | voice_midi_buf.s | Wall home edit event dispatch |
| `WallMenuEdit_EventDispatch` | voice_midi_buf.s | Wall menu edit event dispatch |
| `WallOthEdit_EventDispatch` | voice_midi_buf.s | Wall other edit event dispatch |
| `MainSysCtrl_DispatchTable` | voice_midi_buf.s | Main system control dispatch |
| `CntIniFunc_EventDispatch` | voice_midi_buf.s | CntIniFunc event dispatch |
| `DspConfig_EventDispatch` | dsp_config_sysex.s | DSP config event dispatch |
| `WndEvt_EventCodeDispatch` | voice_synth.s | Window event code dispatch |
| `MidiChan_ParamDispatch` | midi_voice_routing.s | MIDI channel parameter dispatch |
| `SeqData_FieldDispatch` | midi_voice_routing.s | Sequence data field dispatch |
| `SysEx_SendDispatch` | midi_voice_routing.s | SysEx send dispatch |
| `TitleProc_EventDispatch` | ui_widget_defs.s | Title proc event dispatch |
| `SeqEvent_Dispatch` ... (3 more) | sequencer_engine.s | Sequencer engine dispatches |

### Phase 2: Handler Targets (~397 labels)

Dispatch handler targets (individual case labels) were labeled across these files:

| File | Targets Labeled | Key Handler Groups |
|------|----------------|-------------------|
| kn5000_v10_program.s | 152 | System (EditSwParam, WindowField, DirmdEmu, DSPCfg), Title functions (SqTrAs, SqMdlyPly, DkMdlyPly, DpMdly*, DpDoc*, DpPd*, DpSmf*, SqTrSel), Voice (AcVocalGrid, VocalistGrid, ParaLoadOpt) |
| sound_editor_ui.s | 68 | PartGrid columns, NoteEvent buffers, CmpSetP1/EasyCmp/FdcFormat grids, SndArgGrid, PsSCTxtBox |
| drawbar_panel_ui.s | 44 | ComSetGrid, PmemOutL, CtlMsgGrid, MidiSetup, IvSdpart, PsMixer, DemoMenu, AcPresCtrl |
| accompaniment_engine.s | 78 | RhythmParam, CmpMenuTtl/SetTtl/RealTtl, CmpBkslTtl fill-ins, CmpEsyTtl/NcpTtl, MainCmpSet, MspMenu/Name/Rec |
| sequencer_ui.s | 59 | TrAsGrid, MuteChSel, DemoMedDsp, NoteEditBox, Entertainer, SqedtFunc, DspItem0/Equalizer |
| sequencer_engine.s | 30 | SeqData/Event, AppEvent chain, SeqState, NoteEditSy, MainExeCall |

---

## Previously Documented Dispatch Tables

These tables had meaningful semantic labels before the documentation sprint.

Except in rows 21 and 25–27, file names and line numbers in this section and in the batch tables above are from the March 2026 flat `maincpu/` layout. The labels all still exist, but the sources are now split per subsystem, so every line number has moved; find a label with `git grep -n '^Label:'` in kn5000-roms-disasm. The file names that no longer exist map as follows:

| File name in the tables                | Where those labels are now                                                                                                                            |
|----------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| mode_screens.s                         | `v10/maincpu/ui/ui_mode_handlers.s`                                                                                                                   |
| voice_midi_buf.s                       | `v10/maincpu/display/graphics_text_vga.s`                                                                                                             |
| file_io_engine.s                       | `v10/maincpu/audio/audio_control_engine.s`                                                                                                            |
| midi_voice_routing.s                   | `v10/maincpu/midi/midi_dispatch_handlers.s`                                                                                                           |
| style_data_init.s                      | `v10/maincpu/boot/system_handlers.s`                                                                                                                  |
| voice_synth.s                          | `v10/maincpu/ui/ui_window_procs.s`                                                                                                                    |
| naka_dispatch.s                        | `v10/maincpu/ui_widgets/widget_dispatch.s`                                                                                                            |
| tonegen_voice_ctrl.s                   | `v10/maincpu/ui/ui_control_panel.s`                                                                                                                   |
| subprogram_v142.s                      | `v142/subcpu/kn5000_subprogram_v142.s`                                                                                                                |
| subcpu_boot.s                          | `subcpu/boot/kn5000_subcpu_boot.s`                                                                                                                    |
| kn5000_v10_program.s (Batches 1 and 2) | `v10/maincpu/boot/boot_data_tables.s` (`SeqRingBuf_WriteDispatch_Table`), `v10/maincpu/sequencer/smf_tonegen_core.s` (`VoiceSynth_*`, `VoiceParam_*`) |

### Main CPU — Sequencer & Timing

| #   | Label                          | File                   | Line  | Table Base | Index Source   | Entries | Type          |
|-----|--------------------------------|------------------------|-------|------------|----------------|---------|---------------|
| 1   | `SeqStep_TimerDispatchA`       | seq_step_routines.s    | 2516  | 0xE44F00   | DRAM[8956]     | ~23     | jp (xhl)      |
| 2   | `SeqStep_TimerDispatchB`       | seq_step_routines.s    | 2524  | 0xE44F5C   | DRAM[8956]     | ~23     | jp (xhl)      |
| 3   | `SeqStep_TimerDispatchC`       | seq_step_routines.s    | 2532  | 0xE44FB8   | DRAM[8956]     | ~23     | jp (xhl)      |
| 4   | `AccPlayMode_Dispatch_Execute` | accompaniment_engine.s | 8061  | 0xF5ADF9   | flags in reg l | ~32     | call (xhl)    |
| 5   | `AccFlags_Dispatch`            | accompaniment_engine.s | 5356  | 0xF59517   | reg w & 0xF    | ~16     | jp (xhl)      |
| 6   | `DrumSlot_ClampAndLookup`      | accompaniment_engine.s | 22127 | 0xF64D75   | reg hl         | var     | call (xhl)    |
| 7   | `NoteEditSy_HandleUpScroll`    | sequencer_engine.s     | 22430 | 0xE44A6A   | xde (<=0xE)    | 15      | jp t, (xR+rr) |
| 8   | `NoteEditSy_HandleDownScroll`  | sequencer_engine.s     | 22491 | 0xE44A52   | xde (<=0xB)    | 12      | jp t, (xR+rr) |
| 9   | `DspItem0_TypeChangeHandler`   | sequencer_ui.s         | 13583 | 0xE34D92   | xde (<=0x8)    | 9       | jp t, (xR+rr) |

### Main CPU — UI & Control Panel

| #   | Label                       | File                    | Line | Table Base | Index Source     | Entries | Type          |
|-----|-----------------------------|-------------------------|------|------------|------------------|---------|---------------|
| 10  | `UI_STATE_2_SUBSTATE`       | style_data_init.s       | 561  | 0xEF0DA5   | DRAM[1042] & 0xF | ~16     | jp (xhl)      |
| 11  | `CtrlPanel_DispatchByIndex` | tonegen_voice_ctrl.s    | 4113 | 0xEA9A04   | wa (<=0x2A)      | 43      | jp t, (xR+rr) |
| 12  | `CPanel_EncoderDispatch`    | midi_encoder_routines.s | 33   | 0xEDA0BC   | 5-bit idx        | ~32     | jp (xhl)      |
| 13  | `Scoop_EventLoop_12Entry`   | scoop_display.s         | 9770 | (stack)    | reg c            | ~12     | call (xhl)    |

### Main CPU — MIDI & Sound

| # | Label | File | Line | Table Base | Index Source | Entries | Type |
|---|-------|------|------|-----------|-------------|---------|------|
| 14 | `MIDI_CHANNEL_MESSAGE_DISPATCHER` | midi_serial_routines.s | 690 | 0xFCF761 | DRAM[1059] & 0x70 | 8 | jp (xhl) |
| 15 | `PanelEvent_DispatchByIndex` | midi_voice_routing.s | 847 | (computed) | DRAM[0x964D] | var | call (xhl) |
| 16 | `SndParam_*` (5 tables) | sndparam_routines.s | 50-464 | 0xEE10D0-0xEE1148 | reg a/c | 5-7 | call (xhl) |
| 17 | `SeMenu_ValueEditor_*` | sound_editor_ui.s | 3098 | 0xE0E72D | a (0x20-0x3F) | ~32 | call (xhl) |
| 18 | `SeMenu_ListSelector_*` | sound_editor_ui.s | 3248 | 0xE0E72D | a (0x20-0x3F) | ~32 | call (xhl) |

### Main CPU — Interrupt Handlers

| # | Label | File | Line | Table Base | Index Source | Entries | Type |
|---|-------|------|------|-----------|-------------|---------|------|
| 19 | `INTTX1_HANDLER` | cpanel_routines.s | 724 | 0xFC4489 | DRAM[36234] | var | jp (xhl) |
| 20 | `INTRX1_HANDLER` | cpanel_routines.s | 746 | 0xFC4489 | DRAM[36234] | var | jp (xhl) |

### Sub CPU

| #   | Label                                             | File                                 | Line  | Table Base                                                           | Index Source | Entries | Type          |
|-----|---------------------------------------------------|--------------------------------------|-------|----------------------------------------------------------------------|--------------|---------|---------------|
| 21  | `MICRODMA_CH0_HANDLER` (sub-CPU command dispatch) | v142/subcpu/kn5000_subprogram_v142.s | 3250  | 0x00F46C (`CMD_DISPATCH_TABLE`, in v142/subcpu/subcpu_data_tables.s) | latch[7:5]   | 8       | call (xwa)    |
| 22  | `CmdHandler_Table`                                | subcpu_boot.s                        | 99847 | 0xFF8000                                                             | latch[7:5]   | 8       | call (xwa)    |
| 23  | `Voice_SystemMsg_DispatchJump`                    | subprogram_v142.s                    | 25730 | 0x00F74F                                                             | bc (<=0x16)  | 23      | jp t, (xR+rr) |
| 24  | `CmdHandler2C_JumpDispatch`                       | subprogram_v142.s                    | 40501 | 0x0121BD                                                             | wa (<=0xE)   | 15      | jp t, (xR+rr) |

Entry 22 is the boot ROM's own copy of entry 21's dispatch: same 3-bit selector, same
sharing of slots 6 and 7. All eight of its targets are `ld hl, 0:i3 / ret` stubs, so the boot
loader acknowledges every command and implements none until the payload installs the real
table. Since August 2026 it is emitted as symbolic `.long`s rather than hidden inside a
binary include — see
[Sub-CPU Boot ROM (IC30)]({{ site.baseurl }}/subcpu-boot-rom/#the-command-handler-jump-table-at-0xff8000).

### Main CPU — Factory test (HAMA)

| #   | Label                         | File                     | Line | Table Base | Index Source | Entries | Type          |
|-----|-------------------------------|--------------------------|------|------------|--------------|---------|---------------|
| 26  | `TitleFunc_LifecycleDispatch` | factory_test/test_init.s | 178  | 0xE1FDFE   | xwa (<=0x7)  | 8       | jp t, (xR+rr) |
| 27  | `GetResouceInfo`              | kn5000_v10_program.s     | 1697 | 0xE1FFD2   | wa (<=0x9)   | 10      | jp t, (xR+rr) |

### HDAE5000

| #   | Label                                               | File                           | Line  | Table Base                               | Index Source | Entries             | Type       |
|-----|-----------------------------------------------------|--------------------------------|-------|------------------------------------------|--------------|---------------------|------------|
| 25  | `HDAE5000_PPORT_ServiceDispatch` (PC-link services) | hdae5000/hdae5000_ui_display.s | 16230 | 0x295146 (`HDAE5000_PPORT_ServiceTable`) | wa (1..30)   | 31 (entry 0 unused) | call (xhl) |

### Table Data ROM

| # | Label | File | Line | Table Base | Index Source | Entries | Type |
|---|-------|------|------|-----------|-------------|---------|------|
| 28 | Boot transfer | kn5000_table_data.s | 537 | 0xFFFEDC | -- | 1 | jp (xwa) |

---

## Labeling Sprint Summary (March 9, 2026)

During this sprint, **569 dispatch labels** were created or verified:
- 105 dispatch site labels in Phase 1 (jp t, (xR+rr) / call / jp instruction sites)
- 397 handler target labels in Phase 2 (case handlers within dispatch tables)
- 67 additional function labels in Phase 3 (remaining unlabeled dispatch functions)

### Phase 3: Final Labels (67 renames)

| File | Labels Added | Key Functions |
|------|-------------|---------------|
| ui_widget_defs.s | 23 | ObjectProc, EventHandler/EventRoute, DrawTask/DrawFunc pipeline, ApTimer, RootContext, FunctionProc, MainSendEvent/PostEvent |
| drawbar_panel_ui.s | 9 | PsMixer (ControlHelper, EventCallback, GridLoop), AudioCtrl (MixerDispatch, ArrayRead) |
| note_voice_mapping.s | 7 | VoiceEvent_TypeDispatch, SeqEvtBuf_NoteDispatch, MidiSysMsg_Handler, HdaeRom handlers |
| file_io_engine.s | 6 | PanelButton_DispatchChange_Call, BitmaskDispatch, MidiCtrl/VoiceNote/Part dispatches |
| dsp_config_sysex.s | 5 | VoiceInit, AudioModeChange, AudioSubsystem/Voice callbacks |
| sound_editor_ui.s | 3 | FloppyDisk_LoadNoteEvents, ComputeToneParams, CopyNoteBuffers |
| midi_voice_routing.s | 3 | FileData/MidiTable/SeqData dispatch handlers |
| voice_synth.s | 2 | Draw_DispatchByPartType, DrawPartGroup_DispatchByType |
| Other files | 9 | CtrlPanel_FuncDispatch, FileDemo callbacks, Display_ModeHandler, etc. |

---

*This inventory was generated by automated analysis of all `.s` files in the ROM disassembly. Coverage verified at 100% on March 9, 2026.*
