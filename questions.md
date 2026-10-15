---
layout: page
title: Open Questions
permalink: /questions/
---

# Open Questions

Things we don't know yet and need to investigate.

## Control Panel Protocol

### Command Structure
- [ ] What is the complete list of valid command bytes?
- [ ] Are there command categories we haven't discovered?
- [ ] What determines the response length for each command?
- [ ] Are there error/retry mechanisms in the protocol?

### Button Handling
- [x] How many buttons are there total? **~150 buttons** across 22 segments (11 per panel, 8 bits each)
- [x] How are button banks organized? **11 segments per panel (CPL_SEG0-10, CPR_SEG0-10)**, see [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/)
- [ ] Is there debouncing in the MCU or main CPU?
- [ ] How are simultaneous button presses handled?

### LED Control
- [x] How many LEDs are there total? **~119 LEDs** (69 on CPR, 50 on CPL)
- [x] What is the addressing scheme? **Segment outputs SEG00-SEG15** via HD74LS07P drivers
- [ ] Can LEDs be dimmed or only on/off?
- [x] Is there multiplexing? **Yes**, MCU multiplexes via segment outputs
- [x] What do the 4 LED packet types (bits 4-5) represent? **Dispatched via `CPanel_LED_PacketHandlers` (0xFC4B85)**: types 0-2 share `CPanel_LED_HandlePacket2` (0xFC4B95, 48 bytes) which transfers a fixed 2-byte row-select+pattern pair; type 3 uses `CPanel_LED_HandlePacketN` (0xFC4BC5, 66 bytes) for variable-length data, whose first byte's low nibble is a count: the handler copies that byte plus `nibble + 2` more (`nibble + 3` bytes in all). See [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/).
- [x] LED packet format? **Bits 4-5 select handler, bits 5-0 = row, bits 7-6 = panel select**
- [x] LED row mapping? **CPR: rows 0x00-0x0C, CPL: rows 0xC0-0xC8** - see [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/)

### Rotary Encoders
- [x] How many encoders are there? **6 active encoder IDs** (2, 5, 25, 26, 27, 31)
- [x] Absolute or relative encoding? **Both.** The five analog IDs (2, 5, 25, 26, 27) send absolute 8-bit ADC readings; ID 31, the data wheel, sends a signed detent count that the CPL MCU decodes from ROTA/ROTB quadrature
- [ ] What is the resolution (steps per rotation)?
- [x] How is direction determined? **Quadrature decoding** of ROTA/ROTB phase relationship
- [x] Encoder ID encoding? **5-bit ID from bits 0-2 and 6-7 of packet byte 0**
- [x] Which physical encoders map to which IDs? **ID 2=Modwheel, 5=Volume, 25=Breath, 26=Foot, 27=Expression, 31=TEMPO/PROGRAM data wheel** (`Encoder_PassthroughIdentity` passes its count through)
- [x] Does the TEMPO/PROGRAM data wheel travel through this system? **Yes** — its header `0xD7` is a Type 2 frame with encoder ID 31, whose handler `Encoder_PassthroughIdentity` passes the signed detent count through unchanged; `CtrlPanel_HandleSerialPort` then applies the wheel's acceleration curve (`CtrlPanel_DialStepByDelta`) and posts `EVT_DIAL`. See [Data Wheel]({{ site.baseurl }}/data-wheel-investigation/#the-wheel-is-the-type-2-pass-through-entry)

## Hardware Architecture

### Control Panel MCUs
- [x] What MCU model is used? **Mitsubishi M37471M2196S** (8-bit CMOS, 740 series)
- [x] How many MCUs are on the control panel board? **2** (CPL board and CPR board)
- [x] What is the serial baud rate? **250 kHz for the command bytes** (fc/16/4); 31.25 kHz (fc/64/8) arms each command and 62.5 kHz (fc/64/4) carries the phantom/turnaround bytes. See [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/#baud-rate-transitions)
- [x] Is it UART, SPI, or custom protocol? **Clock-synchronous serial**: the CPU runs SC1 in I/O interface mode (`SC1MOD = 0x00`), 8 bits LSB first over a shared SCLK1; the CPU clocks its commands and each panel clocks its own replies. See [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/)

### Inter-CPU Communication
- [x] How do main CPU and sub CPU coordinate? **Command/response via the IC22/IC23 latch — `0x140000` on the main-CPU bus, `0x120000` on the sub-CPU bus — with DMA for bulk transfers**
- [x] What data passes through the latches? **Header-framed packets, in both directions.** Each packet is a header byte followed by its data: bits 7-5 of the header pick one of eight handlers and bits 4-0 give the length (1-32 bytes). Main → Sub, the Sub CPU dispatches through `CMD_DISPATCH_TABLE` (0x00-0x1F MIDI/audio data, 0x60-0x7F DSP data, 0x80-0x9F serial-port-1 data, 0xA0-0xBF keybed settings; the rest are no-ops or a byte drain). Sub → Main (`InterCPU_DMA_Send`, which carries the keybed's note events among others), the Main CPU dispatches through `SeqRingBuf_WriteDispatch_Table`. Headers `0xE1` (6-byte address/count block) and `0xE2` (10-byte parameter block) bypass both tables and set up block transfers. The status lines are separate (next answer). See [Sub-CPU Command Format]({{ site.baseurl }}/subcpu-command-format/)
- [x] Are there handshaking signals? **Yes: two status lines each way.** The Main CPU drives `MSTAT0`/`MSTAT1` (its port Z bits 0-1) and reads `SSTAT0`/`SSTAT1` (port Z bits 2-3), which the Sub CPU drives from its port D; every E1 transfer waits on `SSTAT1` ([SubCPU Payload Loading]({{ site.baseurl }}/subcpu-payload-loading/#e1-bulk-transfer-protocol)). The byte at `0x04FE` in Sub-CPU RAM (bit 6 = payload ready, bit 7 = transfer active) is the Sub CPU's own state, which the boot ROM and the payload both write; it is not a handshake line. During boot the last E1 block, which covers `0x0400`-`0x04FF`, sets bit 6, and the boot ROM's main loop polls that bit before it calls the payload ([Payload Execution Trigger]({{ site.baseurl }}/subcpu-payload-loading/#payload-execution-trigger))
- [ ] **What did the overlay's former SNS write tap break?** The kn7000_mame write tap on DRAM `0xFFD4` (removed in `b1cf7db`) caused the "Sound Name Error", but not by skipping the payload transfer: `SubCPU_Send_Payload` runs before `SubCPU_Payload_Verify` and does not depend on it, and the verify only sets the error flag at `0x01E53E`. Without the tap a cold start gives 0xFF. With the tap the splash played, so the flag was 0 or 1, and which of the two was never traced. At 0 the boot runs each subsystem's phase-1 init handler instead of phase 2. At 1 it runs phase 2 but skips the paths that act only on 0xFF: the welcome screen's "ALL INITIAL SETTING!", `AccompSeq_InitBankIfNoError`, `SendPartDataBlock_DoGetError` and the 0xFF branch of `Audio_ResetAfterPayloadError`. Which of these left the Sub CPU unable to answer the sound-name query? A warm boot through the modelled POWER switch also shows the splash and keeps the names. ([SNS NMI Emulation]({{ site.baseurl }}/sns-nmi-emulation/#abandoned-approach-boot-time-write-tap))

### HDAE5000 Hard Disk Expansion
- [x] What is the command interface via PPI at `0x160000`? **i8255 PPI for PC parallel port (LPT) communication** — used by HD-TechManager5000 Windows software for backup/restore. See [HDAE5000]({{ site.baseurl }}/hdae5000/) and [HDAE5000 Disk Interface]({{ site.baseurl }}/hdae5000-disk-interface/)
- [x] How does it communicate file data to the keyboard? **IDE/ATA at 0x130010-0x130020** (CHS addressing, PIO mode, 4 ATA commands: Read Sectors, Write Sectors, Identify Device, Standby Immediate (0x94)). See [HDAE5000 Disk Interface]({{ site.baseurl }}/hdae5000-disk-interface/)
- [ ] Which of a song record's ten first-cluster slots holds which part (nine part types are known), and what are the FLS item bytes at +80/+112? ([HDAE5000 Filesystem]({{ site.baseurl }}/hdae5000-filesystem/#open-questions))
- [ ] Is "FSB" (PC-link commands 03-06) the whole table set or only the song-record block?
- [ ] Lyric player: the byte at `0x230882`, meta type `0x7E` beyond its chord case, the tempo and measure lyric objects, and the meaning of the main-CPU variables `sqbtof` / `sq_beadt` / `sqsrtc`.
- [ ] The 13,334 bytes of class-specific body in the HD-AE5000's 769 UI object records: the main-CPU class layouts should decode them (record #0 already reads as a `TtlScreen`).
- [ ] Does the main CPU read the STORE button's palette (`HDAE5000_Palette_Button01`) at the bitmap pointer − 0x400?
- [x] What is the protocol for directory listing and file loading? **A custom filesystem**: a 32-bit FAT of cluster chains, and 323 table sectors holding 120 directory names, 1,920 song records (each with first-cluster slots for its parts) and 120 FLS records. See [HDAE5000 Filesystem]({{ site.baseurl }}/hdae5000-filesystem/). (Earlier text here described an "FSB/FGB/FEB hierarchy"; that reading came from misnamed lyrics-player routines.)

## ROM Reconstruction

### Main CPU Reconstruction
- [x] Does the main-CPU image rebuild byte-for-byte? **Yes** — every gated image is byte-identical under `make gate-all`, encoded natively by the custom LLVM TLCS-900 backend. See [ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/).

### Table Data
- [x] What is the structure of the table data ROM? **2MB ROM at 0x800000-0x9FFFFF** — contains rhythm patterns, sound parameter tables, bitmap images, demo songs, SSF presentation data. See [Storage Subsystem]({{ site.baseurl }}/storage-subsystem/)
- [x] What file formats are embedded (images, samples)? **BMP bitmap data** (FTBMP format for Feature Demo), **SSF XML** (presentation scripts), **rhythm pattern data**, **sound parameter tables**
- [x] How is data indexed/accessed? **Via pointer tables in main program ROM** — e.g., file entry index at 0x8CE01C for bitmap lookup, SSF data at 0x88000E

## NAKA Widget System

The firmware's own class definitions answered most of this section in September 2026; see
[UI Framework — The class system describes itself]({{ site.baseurl }}/ui-framework/#the-class-system-describes-itself).

### handler_table Dispatch
- [x] What is the `handler_table` field in CONTAINER/MENU_ITEM widgets? **Not a dispatch table.** The class definitions name it: `window` in a `TtlScreen` (inherited from `Screen`) and `selected` in an `AcTitleMenu` (inherited from `PsMenuBox`). The earlier answer ("DRAM dispatch table address that `InheritedProc` indexes by event code") is superseded.
- [x] Where do the `0x0003xxxx` values point? **Into main DRAM** (`0x000000-0x0FFFFF`), inside the work-RAM image that `Boot_InitWorkRAM` copies to `0x3D524-0x3F6C1` at boot ([Memory Map]({{ site.baseurl }}/memory-map/#work-ram-initial-image)).
- [x] How does `RegisterObjectTable` populate the 14-byte object records at DRAM 0x27ED2? **It copies the caller's `{class id, proc, count, data}` block to `0x027ED2 + 14 × index`.**
- [x] What determines the screen_id values (e.g., 0x01A0 for CONTROL MENU)? **0x01A0 is object table 0x1A0, the title table**: `0x01A0nnnn` is title *nnnn* ([Event Codes]({{ site.baseurl }}/event-codes/#mode-and-title-requests-0x01c00014-0x01c00016)).
- [ ] How does `InheritedProc` use a menu item's `selected` pointer, and what does the `flag` word (+12) of a widget record control? (The HD-AE5000's DISK MENU item has flag 0 where the ROM items have 8.)

### Compact Dispatch Widgets
- [x] What is the 24-byte dispatch format? **A class definition read 4 bytes late.** Its "header" is the class's `parent`, `field_04`/`field_06` are `allsize`/`selfsize`, `name_ptr` is `name`, `inst_ptr` is `propdata`, `link_ptr` is `propname`, and `proc_addr` is the next class's `proc`.
- [x] What do field_04 and field_06 represent? **`allsize` and `selfsize`**: the record size with inherited fields, and the bytes the class adds.
- [x] What is the relationship between inst_ptr (code string) and proc_addr (handler function)? **None.** `inst_ptr` is the class's type-letter string, and `proc_addr` belongs to the next class.
- [ ] Per-class C structs for every NAKA widget record: 3,197 of 3,234 records in 14 C files are typed; the nakabig lane's three files, 37 straddling records and `naka_master_style.c`'s 27 class definitions are not.

## Event System

- [x] **`0x01C00015` versus `0x01C00016`.** Both are title requests carrying a `0x01A0nnnn` title id and reaching `TitleProc`, but they take different cases (`EventDispatch_SelectMatch` / `EventDispatch_OK`). What is the difference? **The firmware's own names settle it:** `0x01C00015` is `EV_CHANGE_TITLE` (change the current title) and `0x01C00016` is `EV_INTERRUPT_TITLE` (show a title on top of the current one until `EV_RETURN_TITLE` closes it). ([Event Codes]({{ site.baseurl }}/event-codes/#mode-and-title-requests-0x01c00014-0x01c00016))
- [ ] **HD-AE5000 boot title request.** `HDAE5000_Boot_Init` requests title 0x7F when `HDAE5000_Check_HD_Present` returns non-zero. Per its header, that means the drive is *not* ready. Per the call site's comments, it means it *is*. Which reading is right? ([Boot Sequence]({{ site.baseurl }}/boot-sequence/#hdae5000_boot_init-0x28f576))
- [ ] Does anything besides `InheritedProc` read `allsize`/`selfsize` of a class that re-classes an existing record (as `HDTitleMenu` re-classes view object `0x00600002`)? A class with parent `0xFFFFFFFF` has no inherited behaviour; whether the view system tolerates that for a DISK MENU item is untested. ([HDAE5000 Homebrew]({{ site.baseurl }}/hdae5000-homebrew/))

## Data Tables (September 2026 leads)

- [ ] **Work-RAM mirror.** Every "no reader found" verdict on ROM data in `0xEED8C8-0xEF03C0` should be re-run against the RAM copy (`nakarest_refs.py` `ram_mirror()`); see [Memory Map]({{ site.baseurl }}/memory-map/#work-ram-initial-image).
- [ ] **Preset Data Destination.** Confirm in MAME that the `0x800000` fallback of `SubCPU_Send_Payload` ships the bitmap bank (and so the `0xF7` bytes). ([LZSS Compression]({{ site.baseurl }}/lzss-compression/#preset-data-destination-dispute))
- [ ] **Section directory at `0x800000`.** Nothing in any ROM we hold reads it or the bitmap copies it indexes. What uses it?
- [ ] **Wallpaper palette entries 0xE0-0xEF.** What writes the RAM table at `0x3F1E4` that `ChangeWallPalette_Impl` loads them from?
- [ ] **Tone database.** The class nibble of a zone record's recording selector appears to pick a 1 MB page of the wave space (page = class & 3, bank = class >> 2; classes 4, 5 and 7 match IC307's pages 0, 1 and 3 exactly). Which socket holds the other banks? Why does `Voice_Init_Type1` add `(tick & 7)` to the whole selector, and what does `WaveSel_StageB_Store_Reg040`'s doubling of the class (bit 2 of `Voice_GlobalFlags`) select? What are SET descriptor `+0x0E` and flags bit 3, and the third id byte (`+13`) of each catalogue row? ([Tone Database]({{ site.baseurl }}/tone-database/#what-is-still-open))
- [ ] **Music Stylist.** Does parameter id 0x4900 resolve to tag 0x61 +0 (style record `+0x9E`), naming each of the 1000 styles' DSP effect? What reads record byte `+0xBE`, and which panel part is "PART 4"?
- [ ] **Effect-parameter metadata.** Why does the Sub CPU payload carry a byte-identical copy of the main CPU's effect-parameter metadata (`0x0133CF`) that it never reads? ([DSP Effect Data Zone]({{ site.baseurl }}/dsp-effect-data-zone/#the-main-cpu-holds-the-same-metadata-and-reads-it))
- [ ] **`InterCPU_E1_DMA_Transfer` (Sub CPU).** The tonedb lane reports that its header probably has source and destination swapped (`DSP_Reinit_VoiceSlots` passes `XWA = 0x007800`, its own staging image, and `XDE = 0x1E0000`). Unverified.
- [ ] **HD-AE5000 disk image geometry.** The reconciliation on [HDAE5000 Filesystem]({{ site.baseurl }}/hdae5000-filesystem/#on-disk-layout-seen-in-a-formatted-disk-image) infers 32 sectors/track and 16 heads from the image's 0x200-sector spacing. The image's IDENTIFY data would confirm it.

## SX-WSA1R

Open questions left by the 2026-09-25 semantic push over the four SX-WSA1R images. Each
lane's full list of what it could not do is in the disassembly repository,
`notes/lanes/wave2-2026-09-25/lane-reports/proma.json`, `promb.json` and `promcd.json`.

### CPU 1's parameter-number space
See [Parameter Records]({{ site.baseurl }}/wsa1-parameters/).
- [ ] What does number `0xB0` of `Dispatch_By_60F080` do (`List2030_ParamB0_Dispatch`)?
  Three of the four numbers that reach a handler with a body are now named: `0x7A` is the
  tempo (`List2030_Tempo_Dispatch` → `Tempo_ApplyBpm`), `0x98` applies a program
  (`List2030_Param98_Dispatch` → `List2030_Param98_ApplyProgram`), and `0xA8` passes its value
  through unchanged (`List2030_ParamA8_PassThrough`). (Nine further numbers with entries of
  their own — `0x44`–`0x46`, `0x48`, `0x60`, `0x70`, `0x72`, `0x90`, `0x91` — point at
  one-byte `ret` stubs, so they are no-ops here, like the 168 that share
  `Dispatch_By_60F080_Nop64`.)
- [ ] Which controllers are numbers `0xB6` and `0xB7`? Two MIDI-in tables carry them for
  every part, but no controller number reaches their handlers.
- [x] What does bit 5 of RAM `0x7F36`, tested before every controller fan-out, switch off?
  **The LOCAL TOTAL setting** of the MIDI screen (set = OFF): `MidiTotalMode_EditLocalTotal`
  writes it, and `MidiTotalMode_PaintLocalTotal` shows it as ON/OFF.
- [ ] What are the switch assignments `0x88`, `0x89` and `0x90`, and which physical controls
  are panel groups `0x0B`–`0x17`?
- [ ] The part record's layout beyond the known classes; what `Dispatch_By_60F080__Tail` is.
- [ ] Reconcile `prom_b`'s factory-default ids that are "without meaning" (`0x60`,
  `0x78`–`0x7A`, `0x80`, `0x91`–`0x93`, `0x98`, `0x99`) with the SysEx reference's names for
  the combination chunks (`0x78` COMBINATION NAME, `0x60` EFFECT COMMON, `0x79` PART
  COMMON, `0x92` KEY SCALING / SCALE TUNING). `tools/wsa1_param_record_layout_check.py`
  shows those chunks and the parameter records occupy the same RAM, which makes the names a
  strong lead; they are not yet confirmed from `prom_a`'s own readers. (The default payload
  of `0x78` is sixteen spaces, as a blank name would be.) `0x7A` is now identified from
  `prom_a`: it is the tempo (record RAM `0x7EE2`, applied by `List2030_Tempo_Dispatch` →
  `Tempo_ApplyBpm`; factory default 120 BPM).
- [ ] SysEx address-hi `0x11` reads RAM `0x7622 + lo` in the SMF exporter. Does the SysEx
  reference's address map agree, field by field, with the combination layout at those
  offsets?
- [ ] Does `SmfSysEx_WriteAddr11`'s pointer-versus-entry compare really let a write to an
  unused address through to `0xFFFFFF`? Worth a MAME trace.
- [ ] Eight jump tables are indexed by RAM cells rather than button codes — the ones at
  `0xF9A3C7` and `0xF9AB84` by `(0x2720)`, `0xF9D966` by `(0x269A)`, and `0xF9DBE6`,
  `0xF9EC58`, `0xFA08BF`, `0xFA09BD`, `0xFA0B13` by others. What do the cells select?

### `prom_a` and `prom_b` data
- [ ] `DrumKitNames_Block7`–`DrumKitNames_Block12` (7,740 B): no reader; their 24-bit block
  and base addresses occur in none of the four images.
- [ ] Not yet attempted: `RecordTables_FB82A0` (2,566 B), `MixedTables_FC6626`, the hard-disk
  sectors `DiskImage_HardDisk_BootSector` / `DiskImage_HardDisk_MBR` (1,024 B), `Msg0716_ObjectRecords`, the `VersionScreen_*` objects,
  `RamInitTable_F96CA6_Addrs`, `MidiFile_Tables_FBA169`.
- [x] How are the words of `SoundCodeByGroupMember_ModeOffsetGroup` (`0xF06EF4`) and
  `PanelSoundSel_ByProgramAndBank` (`0xF07134`) encoded? **They are inverse maps between a
  part's panel selection and its PROGRAM CHANGE & BANK.** `SoundCode_FromGroupMember_ModeOffset`
  reads the first at (group + bias, member) and gets (program, bank) as (low byte, high byte);
  `SoundSel_FromPresetProgramAndBank` reads the second at (program, bank) and gets (group,
  member), sorting the group byte into R1 / R2 / RD at `prom_a` `0xFC248D`. All 272 panel
  selections round-trip (`wsa1/notes/prom_ab_sound_selection_tables.py` in the disassembly).
- [ ] What do the words of `ProgramChangeOut_ByProgramAndBank` (`0xF08514`; low byte = the
  program change transmitted, high byte = the bank select) say for a given sound? The table is
  not an identity map.
- [ ] What do a SysEx decode-tree leaf's result and pair bytes select (`LinkTable_F4FF61`)?
- [ ] Is there more older-build residue? `relocated_copy_scan.py --boundaries` lists
  unchecked candidates in `prom_b`, and `prom_a`'s ~`0x400` stale twins suggest a systematic
  constant-delta twin scan there too
  ([remnants]({{ site.baseurl }}/wsa1-disassembly/#older-build-remnants-and-why-unreached-code-can-be-correct)).
- [ ] `DLRecordPtrs_F03173`'s readers index entries 19–20, past the end of the table and into
  the next display list — a firmware bug, or a deliberate overlap?
- [ ] `TouchCurve_BoxOrigins3[0]` gives x = `0xA8`, but its list's box starts at `0xE0`.
- [ ] Is either of the firmware's two Japanese messages (the display list at `0xF2E91A`)
  reachable? `0xF2E97A`, where the second begins, is spelled nowhere.

### `prom_c` and `prom_d`
- [ ] 24 P7 streams (5,897 B) have no reader in any image. Orphans of an older build, or
  reached some way no search has tried?
- [ ] The P7 type letters `v` and `s`: only their width (one byte) is decoded; `s` occurs
  only in the two wah records, whose hand-coded paths are untraced.
- [ ] Record 14 (ROTARY SPEAKER), descriptor 14, is a 0/1 switch driven by
  amount ≥ `0x40`. Is it the panel's rotary speed control?
- [ ] The program order of `ToneDB_ToneNumBanks` in `prom_d`.
- [ ] Four maths helpers beside the `Double_*` routines are unnamed (`sub_FC8EE5`,
  `sub_FC9FA3`, `sub_FC9ACB` with no caller, `sub_FC9BBC`).

## Needs Technical Documentation

These areas would benefit from official datasheets or service manuals:

- [ ] **TMP94C241F datasheet** - Full instruction encoding tables
- [x] **HDAE5000 documentation** - ✓ Reverse engineered in depth: ROM, IDE/ATA protocol, filesystem, PC link (the questions still open are under [HDAE5000 Hard Disk Expansion](#hdae5000-hard-disk-expansion) above). See [HDAE5000]({{ site.baseurl }}/hdae5000/)
- [x] **KN5000 Service Manual** - ✓ Have it! (EMID971655 A5, 59 pages)
- [x] **Control panel schematic** - ✓ Analyzed pages II-35 to II-38

## Partially Understood

Things we have some info on but need verification:

### CP_Flags Usage
Some flag bits appear unused in the code we've analyzed:
- `CPANEL_TX_RX_FLAGS.2` - Set by `CPanel_RX_ProcessWithFlag`/`CPanel_RX_Process` but never read?
- `CPANEL_TX_RX_FLAGS.4` - Never set, only tested?
- `CPANEL_PROTOCOL_FLAGS.1`, `.2`, `.3`, `.6` - Purpose unclear

### State Machine
- `CPANEL_PACKET_BYTE_COUNT` can hold values 0-17, tracking expected bytes in multi-byte transfers
- See [Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/) for complete state machine diagram

### Multi-byte Packets (Types 6, 7)
- Complex decoding in `CPanel_RX_MultiBytePacket` (0xFC4A40)
- Byte count = `(byte0 & 0x0F) + 1`
- Bit 4 used for mode selection
- Purpose and expected data format unknown

### Timing
- Various routines use "wait 6 ticks" or "wait 3000 loops" - what are the actual timing requirements?

### Control Panel Code

All control panel routines are disassembled: the encoder handlers at `0xFC6C80` (450 bytes, six
handlers) and the LED packet handlers `CPanel_LED_HandlePacket2` (`0xFC4B95`) and
`CPanel_LED_HandlePacketN` (`0xFC4BC5`) are named and sized — see
[Control Panel Protocol]({{ site.baseurl }}/control-panel-protocol/#led-packet-handlers-fully-disassembled).

---

*Have answers or new questions? Contribute to the project — see
[Help Wanted]({{ site.baseurl }}/help-wanted/).*
