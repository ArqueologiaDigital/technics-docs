---
layout: page
title: Source Code Map
permalink: /source-map/
---

# Source Code Map

The [disassembly repository](https://github.com/ArqueologiaDigital/kn5000-roms-disasm) holds
two products as TLCS-900 assembly that reassembles to the original dumps byte for byte: the
**KN5000** — nine gated images under `v10/`, `v9/`, `v7/`, `v142/`, `subcpu/`, `hdae5000/`,
`table_data/` and `custom_data/` — and the **SX-WSA1R**, four images under `wsa1/`. Every image
is assembled by the project's LLVM TLCS-900 backend (`llvm-mc`), linked by `ld.lld` against its
own linker script, and certified by one thing only: `make gate-all` (see [Build System](#build-system)).
This page is the map of that tree. The measured state of the disassembly — byte gate, symbol
counts, instruction census, remaining debt — is on
[ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/).

**Every count on this page is `find <dir> -name '*.<ext>' | wc -l`**, printed by
`tools/source_map_counts.py` in the documentation repository:

```
python3 tools/source_map_counts.py              # the tables below
python3 tools/source_map_counts.py --selftest   # proves it can go red
```

The figures here are its output against disassembly commit `3417969c0`; re-run it rather than
quoting them. Per-file line counts are deliberately not listed — they move with every
conversion, and `wc -l` answers them in a second.

## Tree overview

| Tree                                                 | Directory      | Root source                    | Image                                     | `.s` | `.c` |
|------------------------------------------------------|----------------|--------------------------------|-------------------------------------------|-----:|-----:|
| [Main CPU v10](#main-cpu-v10maincpu)                 | `v10/maincpu/` | `kn5000_v10_program.s`         | 2 MB @ 0xE00000                           | 157  | 104  |
| Main CPU v9                                          | `v9/maincpu/`  | `kn5000_v9_program.s`          | 2 MB @ 0xE00000                           | 157  | 91   |
| Main CPU v7                                          | `v7/maincpu/`  | `kn5000_v7_program.s`          | 2 MB @ 0xE00000                           | 157  | 91   |
| [Sub-CPU payload v1.42](#sub-cpu-payload-v142subcpu) | `v142/subcpu/` | `kn5000_subprogram_v142.s`     | 192 KB @ 0x0400 (+ its LZSS update image) | 5    | —    |
| [Sub-CPU boot ROM](#sub-cpu-boot-rom-subcpuboot)     | `subcpu/boot/` | `kn5000_subcpu_boot.s`         | 128 KB @ 0xFE0000                         | 1    | —    |
| [HD-AE5000](#hd-ae5000-hdae5000)                     | `hdae5000/`    | `hd-ae5000_v2_06i.s`           | 512 KB @ 0x280000                         | 8    | —    |
| [Table data](#table-data-table_data)                 | `table_data/`  | `kn5000_table_data.s`          | 2 MB @ 0x800000                           | 26   | —    |
| [Custom data](#custom-data-custom_data)              | `custom_data/` | `kn5000_custom_data.s`         | 1 MB @ 0x300000                           | 1    | —    |
| [SX-WSA1R](#sx-wsa1r-wsa1)                           | `wsa1/`        | `prom_{a,b,c,d}/wsa1_prom_*.s` | 4 × 512 KB                                | 37   | —    |

The three main-CPU trees have the same 15-directory shape and the same 157 assembly files;
`v9/` and `v7/` differ from `v10/` in content, in the thirteen C data files v10 alone carries,
and in `v7/maincpu/transplant_manifest.txt`, which records how v7 was derived. `v10/` is the
primary target and the one described file by file below. Each tree's `.ld` (32 per main-CPU
tree, one per other image) is the linker script that places its sections; the 32 in a
main-CPU tree are the image's own plus the link scripts of the C-compiled data blocks (see
[`ui_widgets/`](#ui_widgets--naka-screen-descriptors) and [`style_ui/`](#style_ui--style-ui-screen-data-c)).

---

## Main CPU (`v10/maincpu/`)

The main-CPU ROM is the whole user-facing firmware: UI framework and screen descriptors,
display rendering, sound and DSP parameter control, sequencer and accompaniment, MIDI, file
I/O, floppy controller, control-panel link, factory diagnostics. **157 `.s`, 104 `.c`, 3 `.h`
and 32 `.ld` files** across 15 subject directories plus an `images/` directory of bitmaps.

```
v10/maincpu/                       .s   .c
  kn5000_v10_program.s              ROM layout: includes every module in address order,
  maincpu.ld                        inline data, the boot combo handlers, Get_Firmware_Version
  *_constants.s (4 files)           cpanel / fdc / gui / midi_encoder constants
  msp_factory_defaults.s + .c       factory image of the accompaniment stream-buffer pool
  shared/                           11    -   macros, SFRs, VGA, shared boot code, RAM variables
  boot/                              6    -   vectors, system handlers, main title, ROM end structure
  display/                           3    -   VGA graphics/text, scoop display
  ui/                               17    1   UI framework, widgets, control panel, mode handlers
  audio/                            31   53   sound control, sound editor, DSP/SysEx, sound data
  midi/                              9    -   MIDI serial, dispatch, SysEx, computer interface
  sequencer/                        15    3   sequencer, SMF, accompaniment, rhythm
  storage/                           2    -   flash memory, floppy controller
  demo/                              4    -   feature demo
  file_io/                           9    -   disk file operations
  factory_test/                      4    -   factory diagnostics (codename HAMA)
  extensions/                        2    -   expansion-slot devices (codename TOSHI)
  ui_widgets/                       36   29   NAKA screen descriptors (+ naka_types.h, 27 .ld)
  style_ui/                          -   16   Style UI screen data (+ screendata_types.h)
  includes/                          2    1   GUI format strings; generated/ is build output
  images/                            -    -   86 files: 42 PNG + .bin bitmap pairs, 2 palettes
```

### Top level

| File | Contents |
|------|----------|
| `kn5000_v10_program.s` | The image. `.include`s every module in address order, carries the inline data between them, the boot-time button-combo handlers (`Boot_HandleComboDisplay`, `Boot_HandleFactoryReset`) and `Get_Firmware_Version` |
| `maincpu.ld` | Linker script placing the 2 MB image at 0xE00000 |
| `cpanel_constants.s` | Control-panel button and LED segment constants |
| `fdc_constants.s` | Floppy disk controller register constants |
| `gui_constants.s` | GUI framework constants (widget types, flags) |
| `midi_encoder_constants.s` | MIDI and encoder constants |
| `msp_factory_defaults.s` / `.c` | Factory image of the accompaniment stream-buffer pool; the `.s` `.incbin`s the compiled `.c` |

### `shared/` — macros, SFRs, VGA and shared boot code

| File                        | Contents                                                                                                                                                                                                                                      |
|-----------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `macros.s`                  | Assembler helper macros                                                                                                                                                                                                                       |
| `sfr_tmp94c241.s`           | TMP94C241F special-function-register names (`PC` is `0x30`, and so on)                                                                                                                                                                        |
| `vga_constants.s`           | VGA display register constants                                                                                                                                                                                                                |
| `vga_init.s`                | VGA controller initialisation sequence                                                                                                                                                                                                        |
| `vga_io.s`                  | VGA register read/write primitives                                                                                                                                                                                                            |
| `event_codes.s`             | System event-code constants                                                                                                                                                                                                                   |
| `boot_hw_init.s`            | Hardware register initialisation                                                                                                                                                                                                              |
| `boot_routines.s`           | Region detection and boot helpers                                                                                                                                                                                                             |
| `boot_call_init_handlers.s` | Walks the initialisation-handler table at boot                                                                                                                                                                                                |
| `ram_variables.s`           | Main-CPU RAM variables named on this site (`CURRENT_MODE`, the rhythm and medley state, the SwbtWr queue, …), each line citing the page that establishes it; values are v10's, and `scripts/tools/name_kn5000_ram.py` derives each tree's own |
| `positional_labels.s`       | Empty apart from a comment since 2026-10-03, when the last positional aliases were canonicalised to real labels; kept so the `.include` still resolves                                                                                        |

`table_data/shared/` carries its own copy of the boot and VGA files: the table-data ROM's
boot code is the same code (see [Table data](#table-data-table_data)).

### `boot/` — startup, vectors and core handlers

| File | Contents |
|------|----------|
| `interrupt_vector_trampolines.s` | **Not interrupt vectors** (historical file name): in v9/v10, entries 61-191 of the 192-entry MIDI RX record-type handler table read by `MidiStream_DispatchLoop` (entries 0-60 end `audio/audio_control_engine.s`); in v7 the file holds displaced v10 sound-parameter code. The CPU's vector table is in `rom_end_structure.s` |
| `system_handlers.s` | Interrupt handlers (NMI, timers), UI state machine, task scheduler, flash-memory update, LZSS decompression, the inter-CPU link (`InterCPU_E2_Send`) |
| `main_title_ctrl_panel.s` | System initialisation (graphics, events, timers, LCD) and the main-title event loop |
| `screen_group_dispatch.s` | Boot screen-group dispatcher (startup screens, error dialogs) |
| `boot_data_tables.s` | LED patterns, file-type signatures, firmware-update data |
| `rom_end_structure.s` | Interrupt vector table and `FIRMWARE_VERSION` at the top of ROM |

### `display/` — VGA graphics and text

| File                  | Contents                                                                                                                                                                             |
|-----------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `graphics_text_vga.s` | Palette initialisation, text rendering, string layout, VRAM operations                                                                                                               |
| `scoop_display.s`     | Display dirty-region tracking, performance-mode parameter handlers, scoop editor UI                                                                                                  |
| `scoop_editor_data.s` | **Code** (historical file name): the sound editor's title-function handlers, 3,422 instructions and no data directive, entered at `SeWrtSndTitleFunc_OnDraw` and 15 interior offsets |

### `ui/` — UI framework and widgets

| File | Contents |
|------|----------|
| `ui_widget_defs.s` | Grid box, exit window, title/resource widgets, event dispatch loops, object enumeration; also the hidden hex viewer `DbMemoryDumpProc` |
| `ui_window_procs.s` | Window procedures: ModeEdit, TitleEdit, StringBox, Label, Bitmap, Icon, Line, Frame, EditSw, TextBox, VwBox, ListBox, RadioBox, TempoBox, GridBox |
| `ui_control_panel.s` | Control-panel key dispatch, UI task control, slider/scrollbar handlers, GroupBoxProc, `UI_PostModeChangeEvent` |
| `ui_mode_handlers.s` | UI mode handlers (Pmem, bank editor, filter grid, RVari, effect modes); also the power-on self-test (`MainCPU_self_test_routines`) and the keybed service-mode detection (`SelfTest_FirmwareVersionCheck`) — see [Test Modes]({{ site.baseurl }}/test-modes/) |
| `ui_playback_modes.s` | Voice parameter handlers, sequencer timer/tempo, part validation, play/song/medley mode dispatch |
| `drawbar_panel_ui.s` | Drawbar organ slider UI, DSP effect controls, presentation system, demo menu |
| `cpanel_routines.s` | Control-panel link: serial RX/TX, button polling (`CPanel_ScanButtons`, `CPanel_CheckSpecialCombos`), LED control |
| `led_panel_write.s` | Control-panel LED write sequence |
| `bitmap_out_routines.s` | Bitmap blitting and palette loading |
| `drawing_primitives.s` | Line drawing, rectangle fill, reverse string rendering |
| `psgridbox_routines.s` | PS Grid Box widget |
| `rvari_routines.s` | RVari (rhythm variation) screen renderer and interaction |
| `setwall_routines.s` | Sequencer TRACK ASSIGN page (SqTrAs) and the routines after it; not wallpaper code (historical `SetWall_` prefix) |
| `password_slot_routines.s` | Password slot management stubs |
| `char_encoding_naka_state.s` | Character encoding tables and NAKA state blocks |
| `charmap_dispatch_table.s` | Character-map mode dispatch table |
| `sepaout_config.s` / `.c` / `sepaout_config_link.ld` | SepaOut (separate output) configuration data and resource-info handler offsets, compiled from C |

### `audio/` — sound control, sound editor and sound data

| File | Contents |
|------|----------|
| `audio_control_engine.s` | MIDI stream processing, control-panel LED management, voice/tone control, sound preset dispatch |
| `audioinit_routines.s` | Audio subsystem initialisation, stereo voice configuration |
| `dsp_config_sysex.s` | DSP effect parameter handlers (reverb, chorus, EQ, compressor), SysEx command processing |
| `note_voice_mapping.s` | Note-on processing, voice allocation and stealing, NoteMap, sequence playback, MIDI output, sound parameters |
| `sound_editor_ui.s` | Sound editor UI: patch/bank selection, parameter editing, drum-kit editor; `.incbin`s the `sound_editor_screens/` blocks |
| `sound_editor_routines.s` | Sound editor mode helpers |
| `semenu_routines.s` | Sound editor menu (SeMenu) event handling and navigation |
| `sound_navigation.s` | Sound bank browsing: `MainGetSoundName`, `Sound_Navigate_*`, `MainGetRhythmName`, `MainGetPmemName` |
| `presentation_sound_nav.s` | SSF presentation workspace, sound navigation, voice control, presentation control proc |
| `tonegen_fileio_handlers.s` | Tone-generator config initialisation, DSP config entry setup, FileIO callbacks |
| `sndparam_routines.s` | Sound-parameter probe, match and heap allocation |
| `sprintf_core.s` | `sprintf` — a general string formatter. It keeps the `audio/` path from before the routines were identified as `Sprintf_*` rather than an audio command encoder |
| `voice_bank_defaults.s` | Voice bank default data: header, slot templates, bank name strings |
| `sound_data.s` | The sound-data hub: region identifier, the sound-selection descriptor and its sixteen table slots, the category name table, then the tables — it `.incbin`s the fifteen compiled `sound_data_*.c` blocks and `.include`s `sound_data_brass.s` and `sound_data_world_perc.s`. The per-category file names are historical: the tables are maps, not per-category data ([Sound Categories]({{ site.baseurl }}/sound-categories/#architecture)) |
| `sound_data_brass.s`, `sound_data_world_perc.s` | Brass and world-percussion patch data: a 128-entry pointer table plus `0xFF`-terminated patch entries, kept in assembly |
| `sound_data_{piano, strings_vocal, mallet_orch_perc, flute, flute_extra, guitar, sax_reed, synth, drum_kits, orchestral_pad, accordion_reg, bass, digital_drawbar, organ_accordion, gm_special}.s` | The same fifteen categories in assembly form. **In no v10 build**: nothing `.include`s them; the image takes those bytes from the compiled `.c` twins |
| `sound_data_{…}.c` (15 files) | The descriptor's tables as typed C: bank/program ↔ category/slot maps, voice-index maps, per-category last-slot tables, a program-change remap (each file's `CORRECTED` block names its slot and reader). Compiled to `includes/generated/sound_data_*.bin` and `.incbin`'d by `sound_data.s` |
| `tonegen_param_table.c` | Feature-demo text / sound-engine parameter table |
| `voice_factory_presets.c` | Voice factory preset data |
| `sndparam_records/` | Nine `run_*.c` files, one per contiguous ROM run of 18-byte sound-parameter descriptors (named by start address, `run_edbac0.c` … `run_ee0010.c`), and `sndparam_types.h` defining the descriptor |
| `sound_editor_screens/` | 27 `se_*.c` screen-layout blocks for the Sound Editor plus `se_screens_link.ld`, their shared linker script |

### `midi/` — MIDI processing and computer interface

| File | Contents |
|------|----------|
| `midi_dispatch_handlers.s` | MIDI CC handlers, serial input parsing, file-data validation, sound-mode handlers, arpeggiator queue |
| `midi_serial_routines.s` | MIDI serial communication (SC0): TX/RX handlers, initialisation |
| `midi_encoder_routines.s` | MIDI encoder timing and output dispatch |
| `midipkt_routines.s` | MIDI packet extraction, packing and queue management |
| `sysex_routines.s` | System Exclusive message handling |
| `ac_listener_handlers.s` | AcLswFuncBoxProc event dispatch, parameter processing, mixer controls, TtMd exclusion |
| `param_load_routines.s` | ParaLoadOpt parameter loading, audio flag processing, event posting |
| `computer_interface_config.s` | Computer-interface connection configuration |
| `computer_interface_pcg.s` | Computer-interface program change (PCG) output |

### `sequencer/` — sequencer and accompaniment

| File | Contents |
|------|----------|
| `sequencer_engine.s` | Core sequencer: note editor UI, playback control, voice allocation, application event framework, part/voice data |
| `sequencer_ui.s` | Sequencer editing UI, track display, bitmap drum editor |
| `seq_step_routines.s` | Step recording and editing, note event dispatch |
| `seq_event_playback.s` | Event buffer processing, voice slot scanning, accompaniment playback loop, tempo events, MIDI sustain, ring buffers |
| `seq_audio_mode.s` | Audio-mode stereo flags, accompaniment pedal processing, sequencer timing, part activation |
| `smf_event_processor.s` | SMF event processing, tone-generation dispatch, voice channel management |
| `smf_config_routines.s` | SMF configuration and parameter setup |
| `smf_playback.s` | SMF playback control entry points |
| `smf_tonegen_core.s` | Sequencer-driven tone generation: floppy I/O integration, SMF track parsing, tone-generator block writes |
| `accompaniment_engine.s` | Rhythm dispatch, accompaniment voice selection, timing, patches, drum configuration, style conversion; `.incbin`s the `accomp_screens/` blocks |
| `accompseq_routines.s` | Accompaniment sequencer periodic processing |
| `rhythm_routines.s` | Rhythm pattern comparison, trigger and transposition |
| `ssf_gate_states.s` | SSF gate-state arrays and presentation gate table |
| `bmdredit_routines.s` | Bitmap drum editor: stream positioning, sequence display, voice allocation UI |
| `composer_msp_defaults.s` | Composer / MSP (Music Style Preset) default configuration |
| `accomp_screens/` | Three accompaniment screen-layout `.c` blocks (`accomp_section_widget`, `accomp_part_widget`, `accomp_display_full`) and `accomp_screens_link.ld` |

### `storage/` — flash and floppy

| File | Contents |
|------|----------|
| `flash_floppy_handlers.s` | Flash-memory sector write, floppy note-event loading, FDC format UI |
| `fdc_routines.s` | Floppy disk controller: register access, sector read/write, disk-change detection |

### `demo/` — feature demo

| File | Contents |
|------|----------|
| `demo_routines.s` | Demo mode entry and control |
| `fdemotext_routines.s` | Feature-demo text processing: voice probing, flag processing, output formatting |
| `file_demo_proc.s` | File demo procedures and title handlers |
| `demo_seq_bridge.s` | Demo-to-sequencer bridge and playback initialisation; MiddleFuncCall dispatcher, SqTrSel |

### `file_io/` — disk file operations

| File | Contents |
|------|----------|
| `disk_operations.s` | Disk file copy, rename, format, disk info |
| `filename_password.s` | Filename and password entry UI |
| `composer_filters.s` | Composer load and filter operations |
| `smf_operations.s` | Standard MIDI File load, save, naming |
| `wallpaper.s` | Wallpaper image loading from disk |
| `single_load.s` | Single-file load with source/destination selection |
| `medley.s` | Medley playback: internal, disk, SMF, performance-data modes |
| `misc_ui.s` | Miscellaneous file I/O UI (jump insert, file priority, setup) |
| `title_handlers.s` | Load/save title entry handlers |

### `factory_test/` — factory diagnostics (codename HAMA)

The factory test system, documented on [Test Modes]({{ site.baseurl }}/test-modes/). "HAMA" is
a Matsushita developer codename preserved in the ROM's own symbol strings (`InitializeHama`,
`RegObjTableHama`, …).

| File | Contents |
|------|----------|
| `test_init.s` | `InitializeHama` — title and widget-table registration; `TestTitleFunc` lifecycle handler |
| `test_data.s` | Factory test UI configuration data and the original-symbol string table |
| `fd_test_code.s` | `FDLoadSaveTest` — the FD SAVE/LOAD test; `HamaListProc` file-browser handler |
| `fd_test_data.s` | Floppy test dialog data: NAKA widget descriptors, `TT_HDDEXT` / `TT_EXTAPR` title strings |

### `extensions/` — expansion-slot devices (codename TOSHI)

| File | Contents |
|------|----------|
| `extension_init.s` | Extension-slot driver framework: device registration and initialisation (`InitializeToshi`) |
| `extension_data.s` | Extension device data tables and NAKA widget descriptors |

### `ui_widgets/` — NAKA screen descriptors

The "NAKA" format describes UI screens as hierarchical widget trees; see
[UI Widget Types]({{ site.baseurl }}/ui-widget-types/). Each descriptor block is a **C
file** of typed packed structs with named fields, readable string literals and symbolic pointer
references, compiled and then `.incbin`'d by an assembly file of the same region; a
`*_link.ld` per block resolves external symbols against the main ELF, and `naka_types.h`
defines the structs. The directory holds 36 `.s`, 29 `.c`, 27 `.ld` and the header.

Assembly files (region wrappers and the dispatch/pointer tables that stay in assembly):

| File | Contents |
|------|----------|
| `widget_descriptors.s` | Widget descriptor tables and grid data (ROM 0xE30E60–0xE55BC7); hosts the DSP name tables (see [DSP Name Tables]({{ site.baseurl }}/dsp-name-tables/)) |
| `widget_dispatch.s` | Data tables typed from their readers (uimisc lane): sound-parameter descriptors and the SndParam registry, MIDI/SysEx tables and the incoming-SysEx recognition trie, the DSP effect-parameter pointer tables and parameter-write lists (`DspFxRecs_*`), the three SwbtWr listener banks, audio/note/harmony tables, and the work-RAM initial image (`WorkRamInit_Image`) |
| `naka_screen_dispatch.s` | Screen definition tables: SeqToComposer, SeqCopy, EasyComposer, ModeSelect, ExpandMode |
| `naka_widget_tables_1.s`, `naka_widget_tables_2.s` | Widget pointer tables, parts 1 and 2 |
| `naka_property_descriptors.s` | Widget property descriptor tables |
| `naka_widget_desc_dispatch.s`, `naka_effects_eq_dispatch.s`, `naka_sound_technichord_dispatch.s`, `naka_direct_play_dispatch.s`, `naka_direct_play_property_tables.s` | Dispatch and property data for the descriptor, effects/EQ, sound-menu/TechniChord and direct-play screens |
| `naka_debug_proc_names.s` | NAKA debug proc-name table |
| `control_menu_screens.s` | Control Menu header widgets |
| `performance_style_screens.s` | Performance and style screens |
| `composer_style_convert_screens.s` | Composer and style-convert screens |
| `msp_recording_screens.s` | MSP recording and accompaniment screens |
| `direct_play_medley_screens.s` | Direct Play, Medley, Step Record, Track Assign and Demo screens |
| `effects_sequencer_screens.s` | Effects and sequencer screens |
| `midi_reverb_presets_screens.s` | MIDI, reverb and presets screens |
| `sound_menu_drawbar_screens.s` | Sound menu and drawbar screens |
| `technichord_part_settings.s` | TechniChord part-settings screens |
| `technichord_string_data.s` | TechniChord and UI string tables |
| `disk_menu_file_io_screens.s` | Disk menu and file I/O screens |
| `disk_warning_strings.s` | Multilingual disk-operation warning strings |
| `extension_device_screens.s` | Extension-device diagnostic and configuration screens |
| `master_style_grid_screens.s` | Master Style grid screens |
| `normal_mode_layout.s` | Normal Mode screen layout |
| `sequencer_exit_widgets.s` | Sequencer exit / mode widgets |
| `sequencer_channel_containers.s` | Sequencer channel containers, drawbar/mixer data |
| `debug_naming_panel_sim.s` | Debug / naming panel-simulator screens |
| `style_bitmaps.s` | Style bitmaps, presentation data and UI dispatch |
| `widget_names_charmap.s` | Widget name strings and character-map data |
| `style_ui_params.s` | Style UI parameter blocks and screen data — `.incbin`s the compiled [`style_ui/`](#style_ui--style-ui-screen-data-c) blocks |
| `naka_accomp7_widgets.s` | Accompaniment screen 7 widget descriptors |
| `block_007.s`, `block_012.s` | Widget panel grid descriptors; disk/system UI panel widgets |

C files — one per block above where the block is descriptor data: `control_menu_header.c`,
`naka_ctrl_menu_body.c`, `naka_perf_style.c`, `naka_composer_style.c`, `naka_msp_recording.c`,
`naka_direct_play.c`, `naka_effects_seq.c`, `naka_midi_reverb.c`, `naka_sound_menu_drawbar.c`,
`naka_technichord_part.c`, `naka_technichord_strings.c`, `naka_disk_menu_file_io.c`,
`naka_disk_warning.c`, `naka_extension_device.c`, `naka_master_style.c`, `naka_normal_mode.c`,
`naka_sequencer_exit.c`, `naka_sequencer_channels.c`, `naka_debug_naming.c`,
`naka_style_bitmaps.c`, `naka_widget_names_charmap.c`, `naka_widget_tables_1.c`,
`naka_widget_tables_2.c`, `naka_widget_descriptors.c`, `naka_accomp7_widgets.c`,
`naka_block_007.c`, `naka_block_012.c` — plus two lookup tables, `sound_config_lookup.c`
(`SndParam_InitFuncTable`, the sound-parameter subsystem's four init-phase handlers) and `tonekit_param_blocks.c` (labelled "ToneKit", but
the blocks are the DSP effect-parameter defaults records that the `DSPCfg_*` routines read; see
[DSP Effect Data Zone]({{ site.baseurl }}/dsp-effect-data-zone/#the-main-cpu-holds-the-same-metadata-and-reads-it)).

### `style_ui/` — Style UI screen data (C)

Screen layouts and parameter blocks for the style-editing modes, as typed C
(`screendata_types.h` defines the ScreenData bytecode commands); compiled blocks are
`.incbin`'d from `ui_widgets/style_ui_params.s`. See
[ScreenData C Conversion]({{ site.baseurl }}/screendata-c-conversion/).

| File | Contents |
|------|----------|
| `main.c` | Style UI main screen layout |
| `ctlonly.c` (+ `ctlonly_link.ld`) | CTL-only screen (control parameters) |
| `yesctl.c` | Yes/No confirmation + CTL value screen |
| `meascursor.c` | Measure-cursor screen |
| `paramblock/{common, extended, medium, short, value, bal, meas, alta, altb, altc, altd, alte}.c` | The twelve parameter blocks; `altd` is the "Are You Sure?" confirmation dialog |

### `includes/`

| File | Contents |
|------|----------|
| `gui_format_strings.s` | GUI number/text format strings |
| `gui_display_struct_data.s` / `.c` | GUI display-structure data for the Sound Editor. The `.s` is **in no build** — it emits zero bytes into any ROM, as its header says |
| `generated/` | Build output: every compiled `.bin` that the assembly `.incbin`s. Not tracked; `make all` produces it |

### `images/`

86 tracked files: 42 bitmaps as PNG, each beside the `.bin` that an image script regenerates
from it, and two 8-bit palettes (`Palette_8bit_RGBA.bin`, `Palette_8bit_RGBA_2.bin`). Eight
are the 1-bit flash-update banners (`Bitmap_1bit_Please_Wait`, `Bitmap_1bit_Completed`, …;
`scripts/build/mono_images.py`), which `boot/boot_data_tables.s` and the table-data ROM's
`kn5000_table_data.s` `.incbin`; the other 34 are 8-bit indexed bitmaps
(`scripts/build/indexed_images.py`), of which the table-data ROM's `preset_banks.s` `.incbin`s
27 and `ui_bitmaps.s` 6 (`BitmapWormWearingHat.bin` is read only by the ASL mirror). The PNG
is the source; the objects depend on it.

---

## Sub-CPU payload (`v142/subcpu/`)

The sub-CPU runs the real-time audio engine: it receives commands from the main CPU over the
inter-CPU latch and drives the tone generator and the effects DSP. The v1.42 payload is
verified in both forms it ships in — the 192 KB image the boot ROM runs at 0x0400 and the
LZSS "SLIDE4K" update image on the firmware-update disk (see
[ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/#the-v142-sub-cpu-firmware-update-image)).

| File | Contents |
|------|----------|
| `kn5000_subprogram_v142.s` | The engine: RESET handler, initialisation, main audio loop, voice-slot management, tone-generator command emission, pitch/envelope processing, DSP register writes, the keybed service (`Keybed_Read_Event`, `ToneGen_Process_Notes`) |
| `subcpu_vectors.s` | The 45 entry stubs at 0x0400: slot 0, `PAYLOAD_ENTRY`, is the payload entry point the boot ROM `call`s. The other 44 are the interrupt entries the boot ROM's `VECTOR_TABLE` reaches, each named for its TMP94C241F vector (`IntTramp_SWI1` … `IntTramp_INTTC7`, and `IntTramp_NMI` in the last slot). `IntTramp_INT0` is the inter-CPU latch receive. Also the latch and state-variable definitions |
| `subcpu_data_tables.s` | Firmware configuration, floating-point constants, serial I/O buffers, command dispatch table, voice polyphony limits, pitch/MIDI lookup tables, the DSP data zones and the effects-DSP microprogram table |
| `subcpu_fp_math.s` | IEEE 754 floating-point library: double/single arithmetic, mantissa operations, multiply-add, division, pitch-slide engine, amplitude convergence, NaN/overflow handling |
| `shared/sfr_tmp94c241.s` | TMP94C241 SFR names (the sub-CPU is the same part as the main CPU) |
| `subcpu.ld` | Linker script |
| `tools/` | `convert_code_byte_runs.py`, `convert_arm_blocks.py`, `arm_block_evidence.py`, `spell_search.py` — the conversion and evidence scripts for this image |

The effects-DSP microprograms embedded in this image are extracted, disassembled and documented
in the top-level [`dsp/`](#effects-dsp-microprograms-dsp) tree.

---

## Sub-CPU boot ROM (`subcpu/boot/`)

| File                           | Contents                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
|--------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `kn5000_subcpu_boot.s`         | IC30: hardware init, inter-CPU command dispatch, payload reception, and the data objects at 0xFF8000 (the command-handler jump table, the RAM-test descriptor, the keybed velocity/touch front end). It contains **no decompressor** — the main CPU decompresses the payload and pushes it over the link. The 96 KB at 0xFE0000–0xFF7FFF, never dumped apart from 2 KB read blank at each end, is emitted as a `.fill` of the assumed `0xFF` (the source comment still calls it erased flash), not as source; see [Sub-CPU Boot ROM (IC30)]({{ site.baseurl }}/subcpu-boot-rom/) |
| `subcpu_boot.ld`               | Linker script (128 KB at 0xFE0000)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `subcpu_boot_data_8000.bin`    | The 0xFF8000 data region as a file. The LLVM source no longer reads it — the region is carved into labelled source — but the legacy ASL mirror still `binclude`s it, so it stays on disk                                                                                                                                                                                                                                                                                                                                                                                         |
| `tools/convert_erased_fill.py` | The script that turned the 98,304-byte `0xFF` run into `.fill`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |

---

## HD-AE5000 (`hdae5000/`)

The HD-AE5000 is the optional hard-disk expansion board. Its ROM provides IDE/ATA disk access,
a [custom filesystem]({{ site.baseurl }}/hdae5000-filesystem/) (FSB/FGB/FEB — **not** FAT16,
despite one "FAT read error" string), and a file-manager UI that plugs into the main firmware
through the [`extensions/`](#extensions--expansion-slot-devices-codename-toshi) framework.

| File | Contents |
|------|----------|
| `hd-ae5000_v2_06i.s` | ROM header, entry vectors, handler registration, bitmap resource descriptors, `HDAE5000_UiState_Reset` (0x2803C2, resets the browser selection and the save-option record) and the routines after it, among them the title screens (`HDAE5000_TtlScreenRProc`, `HDAE5000_TtlScreenR2Proc`, `HDAE5000_TtlScreenR3Proc`, which hold the bitmap/palette copy code), the select list, the naming window and the hardware test page |
| `hdae5000_hd_driver.s` | Despite the file name, no ATA code (the driver is in `hdae5000_ui_display.s`). UI screens: the floppy list (`HDAE5000_FdList_Scan`), title info (`HDAE5000_TitleInfo_Build`), the directory and song screens (`HDAE5000_DirList_BuildPage`, `HDAE5000_SEL_DIR_Screen`, `HDAE5000_SongScreen_Refresh`), file load and naming, save and setup options, the format dialog, load-by-number, and the PC data-link page (`HDAE5000_PC_DATA_LINK_PAGE`) |
| `hdae5000_filesystem.s` | FLS list and screens (`HDAE5000_FlsList_BuildPage`, `HDAE5000_FlsScreen_Refresh`), load-by-number, delete options, copy-to-HD. The old routine names (`FS_Init`, FSB read/write…) were misreadings; see [HDAE5000 Filesystem]({{ site.baseurl }}/hdae5000-filesystem/#routines-that-were-misnamed) |
| `hdae5000_ui_display.s` | Title/mode requests, the lyrics player, Boot_Init and the frame handler, the song/FLS record layer, the ATA driver, FAT and cluster-chain I/O, the PC-link coroutine and its services, the C runtime library |
| `hdae5000_utilities.s` | Memory copy/compare, multiply, signed/unsigned divide, string operations, and the registered-object name pool |
| `hdae5000_data_tables.s` | UI configuration, class records, the index-parallel UI object and name tables, localisation strings, the palette/bitmap slices |
| `hdae5000_init_data.s` | The initialised `.data` image (ROM 0x2F94B2–0x2FA133) copied to RAM at boot: nine pointer tables, included from `hdae5000_data_tables.s` |
| `shared/event_codes.s` | Shared event-code constants |
| `hdae5000.ld` | Linker script (512 KB at 0x280000) |

There is **no font data** in this ROM: the range once labelled as a font starts 0x11818
bytes inside a bitmap. See [HDAE5000]({{ site.baseurl }}/hdae5000/#embedded-graphics-rewritten).

---

## Table data (`table_data/`)

The 2 MB table-data ROM is labelled source end to end — no anonymous blob is pulled in whole
(see [Table Data ROM]({{ site.baseurl }}/table-data-rom/) and the region map on
[ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/#region-by-region-source-map)).

| File                                                               | Contents                                                                                                                                                                                                                                                                                                                                                                                                   |
|--------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `kn5000_table_data.s`                                              | The image: structure overview, `.include`s the modules below in address order, and the labelled `.incbin` slices                                                                                                                                                                                                                                                                                           |
| `preset_banks.s`                                                   | Section directory and 27 bitmaps (0x800000–0x82FFFF); no preset data, despite the file name                                                                                                                                                                                                                                                                                                                |
| `tone_database_directory.s`                                        | [Tone database]({{ site.baseurl }}/tone-database/): directory, program maps and tone-record offset table                                                                                                                                                                                                                                                                                                   |
| `tone_database_records.s`                                          | The tone/voice parameter records (`ToneRec_000` … `ToneRec_628`)                                                                                                                                                                                                                                                                                                                                           |
| `tone_database_aux.s`                                              | Tone database auxiliary tables (0x855A48–0x87FFEF)                                                                                                                                                                                                                                                                                                                                                         |
| `ui_bitmaps.s`                                                     | UI bitmaps, frame pieces and factory image banks (0x912C00–0x937FFF)                                                                                                                                                                                                                                                                                                                                       |
| `fonts.s`                                                          | UI text fonts: descriptor table and 1-bpp glyph banks (0x944D78–0x950FFF)                                                                                                                                                                                                                                                                                                                                  |
| `style_records.s`                                                  | [Music Stylist]({{ site.baseurl }}/music-stylist-database/) preset records (`StyleRec_000` … `StyleRec_999`)                                                                                                                                                                                                                                                                                               |
| `style_record_ptr_tables.s`                                        | Music Stylist pointer tables (0x986000 / 0x987000)                                                                                                                                                                                                                                                                                                                                                         |
| `help_databases.s`                                                 | Help system: multilingual intro strings and the SLIDE8K help databases                                                                                                                                                                                                                                                                                                                                     |
| `panel_memory_presets.s`                                           | Panel Memory factory bank names and preset records                                                                                                                                                                                                                                                                                                                                                         |
| `boot_fdc_driver.s`                                                | First-stage bootloader floppy (FDC) command-layer driver                                                                                                                                                                                                                                                                                                                                                   |
| `boot_disk_probe.s`                                                | Boot-time floppy disk-format probe                                                                                                                                                                                                                                                                                                                                                                         |
| `boot_cpserial.s`, `boot_cpserial_isr.s`, `boot_cpserial_states.s` | Boot-time control-panel serial-link driver: polling/setup half, interrupt entry half, state handlers and packet codecs — see [Boot CP-Serial Link]({{ site.baseurl }}/boot-cpserial-link/)                                                                                                                                                                                                                 |
| `boot_clib.s`                                                      | Boot-time C runtime (Toshiba `c900ml.lib`): heap allocator, strncmp, 32-bit divide/modulo                                                                                                                                                                                                                                                                                                                                          |
| `boot_debug.s`                                                     | Boot-time debug output group, disabled in shipped firmware                                                                                                                                                                                                                                                                                                                                                 |
| `shared/`                                                          | `boot_hw_init.s`, `boot_routines.s`, `boot_call_init_handlers.s`, `vga_init.s`, `vga_io.s`, `vga_constants.s`, `sfr_tmp94c241.s`, `macros.s` — this ROM's own copy of the shared boot and VGA code                                                                                                                                                                                                         |
| `table_data.ld`                                                    | Linker script (2 MB at 0x800000)                                                                                                                                                                                                                                                                                                                                                                           |
| `includes/`                                                        | The data files the LLVM image slices from: `demo_presets/` (the 19 demo songs as `.mid` + `.yaml` sidecars and their compressed forms) and `help_databases/` (the decompressed databases and their SLIDE8K streams); `generated/` is build output. The six `bootcode_*.bin` slices, the icon, wallpaper and initial-data blobs and `hkst_55.ssf` stay on disk only because the ASL mirror `binclude`s them |

---

## Custom data (`custom_data/`)

| File | Contents |
|------|----------|
| `kn5000_custom_data.s` | IC19, the 1 MB flash of user-modifiable data with its factory contents — the sub-CPU update image at 0x3E0000 among them. Structure on [Custom Data Flash]({{ site.baseurl }}/custom-data-flash/) |
| `custom_data.ld` | Linker script (1 MB at 0x300000) |

---

## SX-WSA1R (`wsa1/`)

The second product in the tree: four 512 KB EPROM images, two processors, and — as
[SX-WSA1 Disassembly]({{ site.baseurl }}/wsa1-disassembly/) sets out — **one kernel source
that assembles into both processors' images**. `wsa1/` keeps its own `Makefile`, `scripts/`,
`notes/`, `original_ROMs/` and `rebuilt_ROMs/`; the top-level `make wsa1` and `make gate-wsa1`
delegate to it. 37 `.s` files outside `notes/` (which holds a probe's `.image-*.s` that is in no
build).

| Directory | `.s` | Contents |
|-----------|-----:|----------|
| `prom_a/` | 1 | `wsa1_prom_a.s` — CPU 1's program image (IC12), one file, plus `prom_a.ld` and `images/` |
| `prom_b/` | 1 | `wsa1_prom_b.s` — CPU 1's second image (IC13), one file, plus `prom_b.ld` and `images/` |
| `prom_c/` | 27 | CPU 2's image (IC28): `wsa1_prom_c.s` is a master listing that `.include`s 26 subject sources in address order, in `boot/` (reset and vectors, boot and main, the INTT1 scheduler tick), `keyscan/` (keyboard scanner, touch-to-velocity), `link/` (link interrupts, key events, link service), `midi/` (serial port, controllers), `voice/` (note engine, voice parameters, leaf helpers), `tone_db/`, `p7/` (the port-P7 module and its byte-stream pool), `devices/` (register-device drivers and writers), `storage/` (EEPROM, flash), `mathlib/`, `data_tables/` (preset bank, touch/EQ/mixer, voice/DSP tables, tail data zone) and `field_accessors.s` |
| `prom_d/` | 4 | The tone database: `wsa1_prom_d.s`, `tone_database_directory.s`, `tone_database_records.s`, `tone_database_aux.s` — the same three-module shape as the KN5000's |
| `kernel/` | 1 | `kernel.s` — the multitasking kernel, one source for both processors; `kernel_maincpu.inc` / `kernel_subcpu.inc` say what it means on each |
| `dsp/` | 1 | `dsp_channel_regs.s` — the DSP channel-register driver, also one source included by both `prom_a` and `prom_c`, with its two `.inc` views |
| `maincpu/shared/` | 2 | `indexed_table.s`, `lcd_screen_redraw.s` — routines `prom_a` and `prom_b` carry twice, included at both sites |
| `include/` | — | `tmp95c061_sfr.inc` (the TMP95C061's I/O registers) and `tlcs900_mem_ops.inc` (the byte-emitter macros) |

`wsa1/scripts/analysis/assert_byte_identical.py` is the product's gate;
`wsa1/scripts/analysis/source_coverage.py` and `wsa1/notes/reachability.py` produce the
coverage figures quoted on the WSA1 pages.

---

## Effects-DSP microprograms (`dsp/`)

Not TLCS-900. The KN5000's effects DSP (IC311, an NEC uPD6383GF) has no ROM of its own: the
sub-CPU host-boots it with microprograms embedded in the v1.42 payload. `dsp/` extracts and
documents them — `programs.tsv` (the generated manifest), `instruction-set.md` (the ISA as far
as it is decoded, with the withdrawn claims listed first), `algorithms/`, `disasm/*.dsm`,
`flowcharts/` (the Mermaid signal-flow charts this site's flowchart pages are generated from),
`analysis/`, `tools/` and `verify.py`. See [Effects DSP]({{ site.baseurl }}/effects-dsp/).

---

## Supporting directories

| Directory | Contents |
|-----------|----------|
| `scripts/` | `build/` (the Makefile's helpers: `compare_roms.py`, the LZSS/SLIDE8K compressors, image conversion), `analysis/` (censuses, gates, symbol references — `assert_byte_identical.py`, `assert_images_assemble.py`, `l2_symbol_reference.py`, the data-as-code and coverage censuses), `converters/`, `generators/`, `lanes/`, `renaming/`, `repair/`, `tools/`; `scripts/README.md` indexes them |
| `symbols/` | `*_symbols_reference.txt`, one per image — `SYMBOL ADDRESS` lines generated from the built ELF by `scripts/analysis/l2_symbol_reference.py --regen`. The authority for any address quoted on this site |
| `archive/asl/` | The legacy ASL sources, still built by `make asl-all` and compared as six extra sections; they constrain which data files must stay byte-identical on disk |
| `original_ROMs/`, `wsa1/original_ROMs/` | The dumps and their `unidasm` listings. Local only — no dump is committed |
| `rebuilt_ROMs/`, `wsa1/rebuilt_ROMs/` | Build output: `.o`, `.elf` and `.rom` per image. The gate compares these against the dumps |
| `notes/`, `analysis/`, `docs/`, `tests/` | Working notes and findings, lane ledgers, the older in-repo documentation, and the format re-implementations that double as tests |
| `TOOLCHAIN_VERSION` | The pinned LLVM commit; the authority for which backend assembles the tree |

---

## Build System

```
make all          # the nine KN5000 images (LLVM), then compare_roms.py
make wsa1         # the four SX-WSA1R images
make everything   # both
make gate         # KN5000: assert every image assembles, then assert byte identity
make gate-wsa1    # SX-WSA1R byte identity
make gate-all     # all thirteen, plus the check that the assembler is a prerequisite of every image
```

The pipeline per image is `llvm-mc -triple=tlcs900` → `ld.lld -T <image>.ld` →
`llvm-objcopy` → raw binary, with the C data blocks compiled by `clang` and `.incbin`'d.
Only the gate certifies a tree: `scripts/analysis/assert_byte_identical.py` compares bytes and
exits non-zero on any difference. ⚠ **Do not gate on `compare_roms.py`'s percentage**:
`100.00%` is rounded to two decimals and covers up to 104 differing bytes in a 2 MB image, and
the script silently skips a section whose built file is missing, so a short build prints nine
sections that all read `100.00%` having assembled none of the ASL mirror. See
[Disassembly Workflow]({{ site.baseurl }}/disassembly-workflow/).
