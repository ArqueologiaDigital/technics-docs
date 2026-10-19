---
layout: page
title: Firmware Architecture Flowchart
permalink: /firmware-flowchart/
---

# Firmware Architecture Flowchart

This page is the diagram view of the KN5000 firmware: how execution flows from power-on
through steady-state operation, and how the subsystems sit relative to one another. The
firmware runs on a TMP94C241F (TLCS-900/H2) at 16 MHz — an 8 MHz crystal through the part's
internal doubler — with a cooperative task scheduler.

The prose behind each diagram lives on the page it links to; the numbers behind each diagram
live on [ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/). Symbol addresses below
are v10 and come from `symbols/maincpu_v10_symbols_reference.txt` in the
[disassembly repository](https://github.com/ArqueologiaDigital/technics-roms-disasm).

## Power-On Boot Sequence

The main CPU boots in two stages. At reset the **Table Data ROM** is mapped over
`0xE00000-0xFFFFFF`, so the reset vector at `0xFFFEE0` lands in a first-stage bootloader that
lives in that ROM. The bootloader configures the memory controller, and a single store —
`MSAR2 := 0x80` — moves the table data down to `0x800000` and reveals the program flash
underneath. Control then enters the program flash at `Boot_InitIOPorts` (0xEF050F), through
the slot at 0xFFFEDC, skipping `RESET_HANDLER`'s duplicate init block.

<pre class="mermaid">
flowchart TD
    RESET["Reset vector 0xFFFEE0<br/>(table-data ROM, aliased at 0xE00000)"] --> BOOT1["First-stage bootloader<br/>0xFFB4E8"]
    BOOT1 --> MEMCTL["Memory-controller config<br/>MSAR/MAMR, DRAM refresh"]
    MEMCTL --> REMAP["MSAR2 := 0x80 at 0x9FB6D3<br/>table data moves to 0x800000"]
    REMAP --> RESETH["Boot_InitIOPorts<br/>0xEF050F via 0xFFFEDC (program flash)"]
    RESETH --> HW_INIT["Hardware init<br/>watchdog, clock, ports, timers, stack"]
    HW_INIT --> SELF_TEST["MainCPU_self_test_routines<br/>0xFB729E"]
    SELF_TEST --> FW_VER{"Get_Firmware_Version<br/>0xFFFEE5"}
    FW_VER -->|"0xFF (boot ROM)"| SHOW_WAIT["Display<br/>'Please Wait !!'"]
    FW_VER -->|"Normal"| POST_TEST["Post self test"]
    SHOW_WAIT --> POST_TEST
    POST_TEST --> TASK_INIT["TaskSched_Init<br/>0xEF1977"]
    TASK_INIT --> PERIPH["Init peripherals<br/>GPIO, region code"]
    PERIPH --> FLASH["Flash_InitAllBanks"]
    FLASH --> HDAE{"HD-AE5000<br/>present?"}
    HDAE -->|Yes| PPI_INIT["HD-AE5000 PPI init<br/>i8255 at 0x160000"]
    HDAE -->|No| SEQ_INIT
    PPI_INIT --> SEQ_INIT["Seq_FullInit"]
    SEQ_INIT --> CPANEL["CPanel_ScanButtons<br/>read power-on key combo"]
    CPANEL --> FLASH_UPD{"Key combo =<br/>flash update?"}
    FLASH_UPD -->|Yes| FW_UPDATE["FLASH_MEM_UPDATE<br/>firmware update from floppy"]
    FLASH_UPD -->|No| MAIN_BOOT
    FW_UPDATE --> HALT["Boot_MainSequence_Trampoline<br/>(infinite loop — reboot required)"]

    subgraph MAIN_BOOT ["Main Boot Path"]
        FACTORY{"Combo 1 and DRAM[0xFFCA] != 0x5AA5?"}
        FACTORY -->|Yes| RESET_DRAM["Boot_HandleFactoryReset<br/>clear work DRAM + IC21 SRAM"]
        FACTORY -->|No| SUBCPU_INIT["SubCPU_Init_DMA_Channels"]
        RESET_DRAM -->|"jp Boot_InitIOPorts (reboot)"| RESETH
        SUBCPU_INIT --> PAYLOAD["SubCPU_Send_Payload<br/>192 KB over the 0x140000 latch"]
        PAYLOAD --> VERIFY["SubCPU_Payload_Verify<br/>checksum validation"]
        VERIFY --> SCREEN0["ScreenGroup_Dispatch(0)<br/>init phase 0 of every subsystem"]
        SCREEN0 --> CHECK_ERR{"Payload<br/>transfer OK?"}
        CHECK_ERR -->|Error| ERR_SCREEN["WA = 2 (payload error)"]
        CHECK_ERR -->|OK| OK_SCREEN["WA = 1"]
        ERR_SCREEN --> BOOT_SCREEN
        OK_SCREEN --> BOOT_SCREEN["Boot_DisplayScreen<br/>ScreenGroup_Dispatch(WA), then (3)"]
    end

    BOOT_SCREEN --> MAIN_LOOP
</pre>

Full detail, including the memory map on either side of the remap, is on
[Boot Sequence]({{ site.baseurl }}/boot-sequence/) and
[TMP94C241 Memory Controller]({{ site.baseurl }}/tmp94c241-memory-controller/).

## Subsystem Registration

There is no monolithic "initialise everything" routine. The UI framework is built from
**modules carrying developer code names**, each of which registers its own object tables
through `InitializeObjectTable` (`0xFA40B3`). The call sequence is literal in
`v10/maincpu/ui/ui_widget_defs.s`: eleven named modules, then twenty generic `User` slots,
then the root.

<pre class="mermaid">
flowchart TD
    SETTGT["SetCurrentTarget"] --> NAMED

    subgraph NAMED ["Named modules (in call order)"]
        direction LR
        M1["Murai"]
        M2["Toshi"]
        M3["East"]
        M4["Suna"]
        M5["Cheap"]
        M6["Scoop"]
        M7["Yoko"]
        M8["Kubo"]
        M9["Hama"]
        M10["KSS"]
        M11["Naka"]
    end

    NAMED --> USERS["InitializeUser12 … InitializeUser31<br/>(twenty generic slots)"]
    USERS --> ROOT["InitializeRoot"]
</pre>

The code names are the original developers' own — three of them also name directories in the
disassembly (`ui_widgets/` is NAKA, `extensions/` is TOSHI, `factory_test/` is HAMA). Each
module's init address and the object tables it registers are on
[UI Framework]({{ site.baseurl }}/ui-framework/); the widget descriptors Naka registers are on
[UI Widget Types]({{ site.baseurl }}/ui-widget-types/).

## Main Event Loop

After boot the firmware runs a cooperative multitasking loop: a task scheduler that never
preempts, plus an event dispatch system. A task runs to completion or yields; nothing
interrupts it but the ISRs below.

<pre class="mermaid">
flowchart TD
    BOOT["Boot_DisplayScreen"] --> SCHED

    subgraph MAIN_LOOP ["Main event loop (cooperative multitasking)"]
        SCHED["TaskSched_Dispatch<br/>0xEF1AC0 — run next ready task"]
        SCHED --> EVT_CHECK{"Events<br/>pending?"}
        EVT_CHECK -->|Yes| EVT_DISPATCH["Event dispatch<br/>route to registered handler"]
        EVT_CHECK -->|No| TIMER_CHECK{"Timer<br/>expired?"}
        EVT_DISPATCH --> SCHED
        TIMER_CHECK -->|Yes| TIMER_HANDLER["Timer handler<br/>sequencer tick, UI refresh"]
        TIMER_CHECK -->|No| SCHED
        TIMER_HANDLER --> SCHED
    end
</pre>

## Interrupt Service Routines

Real-time work is interrupt-driven; the ISRs are thin and hand data to the main loop through
ring buffers.

<pre class="mermaid">
flowchart LR
    subgraph ISR ["Main-CPU interrupt handlers"]
        T1["INTT1_HANDLER<br/>0xEF0BF9 — timer 1, SYSTEM_TIMESTAMP"]
        RX0["INTRX0_HANDLER<br/>0xFCF1F0 — MIDI RX (SC0)"]
        TX0["INTTX0_HANDLER<br/>0xFCF15B — MIDI TX (SC0)"]
        RX1["INTRX1_HANDLER<br/>0xFC44D7 — control-panel RX (SC1)"]
        TX1["INTTX1_HANDLER<br/>0xFC44B5 — control-panel TX (SC1)"]
    end

    subgraph SUBISR ["Sub-CPU"]
        DMA["MICRODMA_CH0_HANDLER<br/>0x020F1F — inter-CPU command dispatch"]
    end

    TX0 --> MIDIQ["MidiOut ring buffer<br/>0x01F785 — MIDI TX queue"]
    RX0 --> PARSER["MidiSerial_ProcessInput<br/>0xFCF9AE (main loop)"]
    RX1 --> CPPARSE["Control-panel packet parser"]
</pre>

Besides the main sequencer ring buffer at `0x01F37B` (`SeqMain_*`), the main CPU has ring
buffers at `0x01F785`, `0x01FCA3`, `0x0201C1`, `0x0204DF` and `0x0203D5`. The source names them
by role through their accessors: MidiOut (`SeqBuf_MidiOut_ReadByte`), DspSysEx
(`SeqBuf_DspSysEx_WriteByte`), VoiceMap (`SeqBuf_VoiceMap_ReadByte`), SoundEdit
(`SeqBuf_SoundEdit_ReadByte`) and NoteEvent (`SeqBuf_NoteEvent_WriteByte`); the full accessor
lists are on [Sequencer]({{ site.baseurl }}/sequencer/#additional-buffer-instances).
`INTTX0_HANDLER` dequeues MIDI output bytes from the MidiOut buffer. The others are filled with
packets from the sub-CPU: `INTTC0_HANDLER` routes each received packet, by bits 7-5 of its
header byte, through `SeqRingBuf_WriteDispatch_Table` to `SeqDMA_MultiWrite_NoteEvent` /
`SeqDMA_WriteMidi_NoteOn` (NoteEvent), `SeqDMA_MultiWrite_SoundEdit`,
`SeqDMA_MultiWrite_VoiceMap` or `SeqDMA_MultiWrite_DspSysEx`; entries 5-7 are `SeqDMA_Nop`. See
[MIDI Serial I/O]({{ site.baseurl }}/midi-serial-io/) for the two MIDI handlers in full and
[Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) for the panel pair.

## Subsystem Architecture

<pre class="mermaid">
flowchart TD
    subgraph UI_LAYER ["UI Layer"]
        NAKA["NAKA widget framework<br/>478 registered widget objects, 9 type codes"]
        SCREEN["Screen manager<br/>screen groups, mode dispatch"]
        DRAW["Drawing primitives<br/>lines, boxes, text, bitmaps"]
        VGA["VGA controller IC206<br/>320x240 8bpp LCD"]
    end

    subgraph AUDIO_LAYER ["Audio Layer"]
        TONEGEN["Tone generator IC303<br/>64 voices, PCM wavetable"]
        DSP["Effects DSPs<br/>IC310 (serial) + IC311 (parallel)"]
        VOICE["Voice allocator<br/>note-on/off, velocity, pan"]
        SNDPARAM["Sound parameters<br/>preset lookup, category maps"]
    end

    subgraph SEQ_LAYER ["Sequencer Layer"]
        SEQ["Sequencer engine<br/>16-track, ring buffer playback"]
        ACCOMP["Accompaniment engine<br/>rhythm, bass, chord patterns"]
        SMF["SMF player<br/>Standard MIDI File playback"]
        STYLE["Style system<br/>SSF data, variation select"]
    end

    subgraph IO_LAYER ["I/O Layer"]
        CPANEL["Control panel<br/>serial protocol, buttons, LEDs, data wheel"]
        MIDI["MIDI<br/>31250 baud UART, SysEx, CC routing"]
        FDC["Floppy disk<br/>uPD72068 controller"]
        IDE["IDE/ATA<br/>HD-AE5000 hard disk"]
        FLASH["Flash memory<br/>user settings, custom data"]
    end

    subgraph CPU_LAYER ["Inter-CPU Communication"]
        MAIN["Main CPU<br/>TMP94C241F @ 16 MHz"]
        SUB["Sub CPU<br/>TMP94C241F @ 20 MHz (audio engine)"]
        LATCH["Latch IC22/IC23<br/>0x140000 main side, 0x120000 sub side"]
    end

    UI_LAYER --> AUDIO_LAYER
    UI_LAYER --> SEQ_LAYER
    SEQ_LAYER --> AUDIO_LAYER
    AUDIO_LAYER --> CPU_LAYER
    IO_LAYER --> UI_LAYER
    IO_LAYER --> SEQ_LAYER
    MAIN <-->|"commands, E1/E2 bulk transfers"| LATCH
    LATCH <-->|"DMA bulk transfer"| SUB
    SUB --> TONEGEN
    SUB --> DSP
</pre>

The 478 is literal in the source: `InitializeNaka`
(`v10/maincpu/storage/flash_floppy_handlers.s`) registers `NAKA_UIObjectTable` against handler
`ViewableProc` with an entry count of `0x1DE`. The widget type codes and the descriptor record
layout are on [UI Widget Types]({{ site.baseurl }}/ui-widget-types/).

## NAKA Widget Event Flow

The UI framework dispatches on 32-bit event IDs, not on the widget's type byte. A button press
becomes an event; the event walks the class hierarchy until a handler claims it.

<pre class="mermaid">
flowchart TD
    BUTTON["Physical button press"] --> CPANEL_ISR["INTRX1_HANDLER<br/>serial packet decode"]
    CPANEL_ISR --> EVT_GEN["Generate event ID<br/>(e.g. 0x01C00008 = EVT_SW_ON)"]
    EVT_GEN --> VIEWABLE["ViewableProc<br/>0xFA5995 — dispatch on 32-bit event ID"]
    VIEWABLE --> INHERITED["InheritedProc<br/>0xFA4409 — walk parent chain"]

    subgraph WIDGETS ["Widget handlers"]
        CONTAINER["Container handler<br/>screen root, layout"]
        MENU_ITEM["Menu item handler<br/>selection, navigation"]
        SLIDER["Slider handler<br/>value adjustment"]
        DISPATCH["Dispatch handler<br/>proc function call"]
    end

    INHERITED --> CONTAINER
    INHERITED --> MENU_ITEM
    INHERITED --> SLIDER
    INHERITED --> DISPATCH
    DISPATCH --> PROC["Proc function<br/>(e.g. IvDrawbarProc)"]
    PROC --> ACTION["UI action<br/>sound change, screen transition"]
</pre>

The `0x0003xxxx` values older notes called a `handler_table` are not a dispatch table: the
class definitions name that field `window` (in a `TtlScreen`) or `selected` (in an
`AcTitleMenu`), and the values point into main DRAM, inside the work-RAM image
`Boot_InitWorkRAM` copies to `0x3D524-0x3F6C1`
([Open Questions]({{ site.baseurl }}/questions/#handler_table-dispatch)).

## Memory Map

The address space is documented, with its chip-select blocks and the reset-time alias, on
[Memory Map]({{ site.baseurl }}/memory-map/). Note that the main and sub CPUs have **separate**
buses: `0x100000` is audio hardware on the sub-CPU side and `0x140000` is the inter-CPU latch
on the main-CPU side, so a single flat picture of "the" address space would be misleading.

## Source File Organization

The v10 main-CPU firmware is six top-level `.s` files (`kn5000_v10_program.s`, four
`*_constants.s` and `msp_factory_defaults.s`) and one top-level C file
(`msp_factory_defaults.c`), plus fifteen subsystem directories; the chart leaves out the
top-level files other than `kn5000_v10_program.s`, `shared/` (11 `.s`, only
`boot_hw_init.s` drawn), `includes/` (2 `.s`, 1 `.c`), the 16 C files of `style_ui/` and
`ui/sepaout_config.c`. Counts are
from `find v10/maincpu -name '*.s' | wc -l` (and `'*.c'`) in the disassembly repository —
157 assembly files and 104 C files.

<pre class="mermaid">
flowchart TD
    MAIN["kn5000_v10_program.s<br/>(ROM layout, inline data, entry point)"]

    subgraph BOOT_FILES ["Boot &amp; system — 6 .s"]
        BOOT_HW["shared/boot_hw_init.s"]
        SYS_HAND["boot/system_handlers.s"]
        MAINTITLE["boot/main_title_ctrl_panel.s"]
    end

    subgraph UI_FILES ["UI framework — 17 .s"]
        WIDGET_DEFS["ui/ui_widget_defs.s"]
        DRAW_PRIM["ui/drawing_primitives.s"]
        CPANEL_RT["ui/cpanel_routines.s"]
        CTRLPANEL["ui/ui_control_panel.s"]
    end

    subgraph NAKA_FILES ["UI widgets, codename NAKA — 36 .s + 29 .c"]
        NAKA_C["ui_widgets/*.c<br/>typed packed structs, byte-identical output"]
        NAKA_S["ui_widgets/*.s<br/>descriptor tables and linker scripts"]
    end

    subgraph AUDIO_FILES ["Audio — 31 .s + 53 .c"]
        ACE["audio/audio_control_engine.s"]
        NVM["audio/note_voice_mapping.s"]
        SEMENU["audio/semenu_routines.s"]
        DSP_CFG["audio/dsp_config_sysex.s"]
        SND_DATA["audio/sound_data_*.c"]
    end

    subgraph SEQ_FILES ["Sequencer — 15 .s + 3 .c"]
        ACC_ENG["sequencer/accompaniment_engine.s"]
        SEQ_ENG["sequencer/sequencer_engine.s"]
        SMF_PLAY["sequencer/smf_playback.s"]
    end

    subgraph MIDI_FILES ["MIDI — 9 .s"]
        MIDI_SER["midi/midi_serial_routines.s"]
        MIDI_DISP["midi/midi_dispatch_handlers.s"]
        SYSEX["midi/sysex_routines.s"]
    end

    subgraph OTHER_FILES ["Storage 2 · file I/O 9 · display 3 · demo 4 · factory test 4 · extensions 2"]
        FDC_RT["storage/fdc_routines.s"]
        FLASH_RT["storage/flash_floppy_handlers.s"]
        FILEIO["file_io/*.s"]
        FACTORY["factory_test/*.s"]
    end

    MAIN --> BOOT_FILES
    MAIN --> UI_FILES
    MAIN --> NAKA_FILES
    MAIN --> AUDIO_FILES
    MAIN --> SEQ_FILES
    MAIN --> MIDI_FILES
    MAIN --> OTHER_FILES
</pre>

Per-file descriptions are on [Source Code Map]({{ site.baseurl }}/source-map/), and the
measured state of the disassembly — instruction census, symbol count, byte gate, remaining
debt — is on [ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/).
