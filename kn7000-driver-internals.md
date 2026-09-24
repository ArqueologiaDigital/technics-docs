---
layout: page
title: KN7000 MAME Driver Internals
permalink: /kn7000-driver-internals/
---

# KN7000 MAME Driver Internals

The reasoning behind the MAME driver for the SX-KN7000 and its MN10300 siblings
(KN6000, KN6500, KN2400, KN2600).

MAME's house style keeps the *what* in the source and puts the *why* in the pull
request and the project's documentation. This page is that *why*: the design notes
that used to sit as prose in the driver sources, moved here when the driver was
trimmed to MAME's comment volume in September 2026.

Measured at the time of the move: the driver's thirteen files carried 1124 comment
lines over 3670 lines of code (30.6%), against 12.7--28.4% across MAME's own
comparable drivers (`model2.h`, `model2.cpp`, `roland_d50.cpp`, `ctk551.cpp`,
`ymmu100.cpp`, `gticlub.cpp`, `zr107.cpp`, `hornet.cpp`).

A verbatim copy of every block, with its original line numbers, is kept in the
project repository as `notes/kn7000-driver-source-annotations.md`.


## The driver: memory map, interrupts, peripherals

*Source: `src/mame/matsushita/kn7000.cpp`*

>  license:GPL2+
>  copyright-holders:Felipe Sanches
> **************************************************************************
>
> Technics SX-KN7000 and related MN10300-based keyboards
>
> Emulated: the MN10300 CPU and its on-chip peripherals, the LCD, the control
> panel, the floppy and SD interfaces, MIDI, the ADSP-21065L effects DSP, and a
> tone generator that responds to the firmware but has no samples to play - the
> wave ROMs are undumped, so its timbre is a placeholder.
>
> All five machines are built around a Panasonic MN103002A (MN10300 family,
> AM33 core), running Panasonic's "MILK" object framework.
>
> Hardware inventory below is taken from the manufacturer's service manuals:
>
> SX-KN7000  EMID0207013C0 (2002)
> SX-KN6000  EMID9908016C0 (1999)
> SX-KN6500  EMID0101001C0 (2001)
> SX-KN2400, SX-KN2600
>
> Each manual covers only its own model, except that the SX-KN2400 book's
> parts list reproduces the SX-KN2600's list of main-board integrated
> circuits verbatim - it names devices that appear on no SX-KN2400 schematic
> sheet or board silkscreen, and omits the floppy controller that all three
> SX-KN2400 sources show. The SX-KN2400 devices below are therefore taken
> from its schematics, block diagram and board assembly drawings only.
>
> Capacities were read from the schematics and parts lists, and confirmed by
> counting address pins. The manuals write ROM sizes in megabits: the KN6000
> manual prints "(64M BIT MASK ROM)" next to parts numbered QSIGX3C64004 and
> up, which fixes both the unit and the meaning of the digits in the part
> number.
>
> Clocking: the KN6000 and KN6500 manuals print a 32 MHz oscillator at X1,
> feeding a spread-spectrum clock generator at IC6 whose output drives the
> CPU. The KN7000, KN2400 and KN2600 use the same topology, but their
> manuals do not give the frequency of X1, so their core clocks are inferred
> from the KN6000 and KN6500 rather than documented.
>
> The KN7000's program and table ROMs are not chip reads. They are payloads
> from Panasonic's own firmware update disks, and they validate against the
> checksums that Panasonic ships alongside them: the update descriptor files
> carry a 32-bit sum over the whole payload plus 16-bit sums of each 256 KiB
> block, and every block matches.
>
> A note on the KN7000's IC16/IC17: these are one pair of 4 MiB flash devices
> on CPU address lines A2-A22, so together they span 8 MiB. Address line A22
> selects between the two regions declared below - the table data occupies
> the half where A22 is low, and the program the half where it is high.
>
> TODO:
> - dump the wave, rhythm and picture ROMs listed as NO_DUMP below
>
> *************************************************************************


**`constexpr offs_t IRQ_VECTOR_BASE = 0x50000000;`**

>  A maskable interrupt of level L vectors to <base> + IVAR[L]. Every firmware
>  clears IVAR0..IVAR6 once at boot and builds a `nop ; jmp handler` thunk at the
>  base of work RAM, computing the jump displacement for execution there -- so
>  one entry serves all seven levels and the handler address stays the firmware's
>  business. Nothing in the 4 MB image branches to the thunk, so it is reached
>  from the vector; what decodes work RAM to the CPU's 0x40000000 vector base is
>  a board question the available documentation does not answer.


**`uint16_t io_r(offs_t offset, uint16_t mem_mask = ~0);`**

>  Everything else that is mapped but not decoded yet: log and move on. This
>  must NOT share a handler with snd_r/snd_w -- MAME gives a handler an offset
>  measured from its own map entry's base, so one switch cannot serve windows
>  at five different bases without aliasing offset 0 of each onto the first.


**`enum { IRQGRP_TIMER = 0x06, IRQGRP_PANEL = 0x1A, IRQGRP_MIDI1 = 0x12, IRQGRP_MID`**

>  --- On-chip interrupt controller (INTC) at 0x34000100 ------------------
>  The register model lives in the CPU core. The driver keeps only board policy:
>  which group each peripheral asserts, the panel transfer-complete re-delivery
>  filter, and the panel-ATN EXTMD edge decode.


**`uint8_t m_kbd_midi_status = 0;             // MIDI running-status byte`**

>  --- MIDI -> internal KEY BED bridge (velocity-sensitive) ------------------
>  A MIDI controller wired here plays the machine's own key bed rather than the
>  rear MIDI IN jacks, so the firmware treats the notes exactly like physical key
>  presses. MIDI note n maps to key index n-36; the 61-key compass is C2..C7 and
>  notes outside it are dropped. Connect a host controller with -kbdmidi <port>.


**`uint16_t m_tg_addr[2] = { 0, 0 };          // latched register address, [0]=main`**

>  Tone generators (main 0x98040000 / sub 0x98050000): register-indirect,
>  write-only from the firmware. Address latched at base+0, data written at
>  base+2 -> reg[address]. Voice registers are group<<8|bank<<6|channel
>  (< 0x1000); the 0xFC0x system-refresh group is accepted but not stored.


**`emu_timer *m_sd_insert_timer = nullptr;`**

>  --- SD card-detect (GxICR group 0x1B pin, register 0x3400016C) ------------
>  The card/lid switch is an external-interrupt pin whose ICR the firmware polls:
>  bit4 set = no card or lid open, clear = card present. The SD state machine is
>  driven by the detect TRANSITION, so a line that is statically present from
>  power-on never fires it -- model the card as absent at power-on and insert it
>  a few seconds into the boot.


**`uint16_t m_sdmbx_out = 0xFF;               // last MISO byte (mailbox read value`**

>  --- SD mailbox (register 0x9805000C + ICR group 0x1C handshake) ----------
>  The firmware speaks the standard SD-card SPI protocol through this byte
>  mailbox: wake-up clocks, CMD0, then R1 response reads. Each mailbox write
>  clocks the byte through the spi_sdcard device and asserts INTC group 0x1C;
>  reads return the MISO byte, so the register behaves as a full-duplex SPI
>  data latch.


**`map(0x90000000, 0x903fffff).ram().share("workram");`**

>  External memory is visible twice: cachable at 0x40000000-0x7FFFFFFF and
>  uncachable 0x40000000 above that, which is what the 0x50/0x90, 0x4C/0x8C and
>  0x44/0x84 pairs are. The firmware writes code through the uncachable view and
>  executes it from the cachable one -- the interrupt vector thunk here, the
>  library at 0x8C000000/0x4C000000.

>  0x96800000-0x969FFFFF inside the window above is the WRITABLE custom-data FLASH
>  (IC21), not RAM. It is carved back out here -- a later map() entry overrides an
>  earlier one -- and handed to a real flash device so the firmware's erase and program
>  command sequences are decoded instead of being stored as stray bytes. Contents come
>  from the "customflash" region, which holds what the "Initial Data" disk installs.


**`m_dsp_irq_timer->adjust(attotime::from_hz(DSP_FRAME_HZ), 0, attotime::from_hz(DS`**

>  Start the audio frame tick: the kernel's reset handler enables IRQ0 and
>  then IDLEs waiting for the first one, which drives its main loop one audio
>  frame per edge. On real hardware IRQ0 comes from the SPORT/codec frame
>  sync; a periodic pulse stands in for it here.


**`if (!m_dsp_running)`**

>  Audio frame tick: pulse the effects DSP's IRQ0, the kernel's frame interrupt. Only the
>  assert is needed -- the SHARC clears the pending bit when it takes the interrupt, so one
>  edge is delivered per tick. The kernel configures IRQ0 edge-triggered (MODE2 0x18011) and
>  its handler at PM 0x8020 sets R13=1 to hand a frame to the main loop.


**`PORT_START("VOL_MAIN")   PORT_ADJUSTER(80, "Main Volume")`**

>  Front-panel volume sliders (the ESQ1-style slider script in kn7000.lay binds
>  these; PORT_ADJUSTER gives a 0-100 value the layout knob animates). MAIN drives
>  the DSP bridge's master gain and APC/SEQ is sent to the panel as a CP 0xD2
>  frame; MIC and LINE-IN are read but reach no audio path yet.


**`if (m_lib_mirror)`**

>  KN6000/KN6500: unlike the KN7000, which self-loads its library, these
>  firmwares read the library at 0x4C000000/0x8C000000 without ever writing
>  it. What backs that window on the board is not established; filling it from
>  the program ROM here is what makes the boot find what it reads.


**`void kn7000_state::kn6500(machine_config &config)`**

>  The KN6500 is the KN6000 machine with a different firmware BUILD. Same hardware
>  (one D82398GD001 tone generator, same 64 voices, same register numbering), but the
>  build's RAM layout shifted, so the driver-side voice-record binding has to follow it:
>  the per-TG-slot voice record sits one record earlier than the KN6000's.


**`kn7000_base(config);`**

>  PLACEHOLDER: this inherits the KN7000's control panel, whose scan matrix is
>  the wrong one -- the SX-KN2400/KN2600 front panel is a different and smaller
>  one that has not been drawn. It does not inherit the artwork; only kn7000()
>  calls set_default_layout.

> **************************************************************************
>
> SX-KN7000
>
> IC16, IC17   C3FBNG000016   32 Mbit flash, program + table (see note above)
> IC18         C3CBND000046   64 Mbit mask ROM, rhythm  (later production)
> IC20         C3FBMD000050   32 Mbit flash, rhythm      (earlier production,
> same site, and half the capacity; the manual
> states IC20 is not supplied as a spare part)
> IC19         C3CBMD000098   64 Mbit picture ROM
> IC21         C3FBMD000050   16 Mbit custom flash (user data).  The service
> manual captions this "32M FLASH", but that is
> copied from IC20: the firmware's flash device
> table (0x485CF9E0) accepts only 16 Mbit parts,
> so a 32 Mbit device would fail its autoselect
> check.  It also builds a 0x200000 sector map,
> and the board decodes a 2 MB window at
> 0x96800000.  Three independent reasons for
> 16 Mbit.
> IC203        C3CBQD000002  128 Mbit mask ROM, wave, main TG bank Y (AWAY)
> IC204        C3CBQD000001  128 Mbit mask ROM, wave, main TG bank X (AWAX)
> IC207        C3CBQD000004  128 Mbit mask ROM, wave, sub TG bank Y (BWAY)
> IC208        C3CBQD000003  128 Mbit mask ROM, wave, sub TG bank X (BWAX)
>
> The wave devices sit on two independent buses per tone generator, so they
> are declared as one region per bank rather than concatenated. The block
> diagram shows IC207 and IC208 the other way round, but the schematic gives
> BWAY on IC207 and BWAX on IC208 at pin level, the chip-enable groups agree
> with it, and the part numbers pair as Y = 000002/000004 against
> X = 000001/000003.
> IC414        C3FBKD000162    4 Mbit flash, SD card sub-CPU program
>
> *************************************************************************


**`ROM_REGION16_BE(0x200000, "custom_data", ROMREGION_ERASEFF)`**

>  The custom flash holds user data, and is populated from a floppy rather than
>  programmed at the factory: the firmware inflates the CTMINI payload from an
>  "Initial Data Disk" and writes it verbatim to offset 0x20000, which is the top
>  30 of the 64 KiB sectors.  Nothing is written below that, so the boot sectors
>  are left erased here.
>
>  The images below are not dumps of IC21 and are marked BAD_DUMP accordingly.
>  Each is the payload one published data set writes into the part, taken from
>  the manufacturer's own installer, so a part programmed from that floppy reads
>  back as declared -- but nobody has read one off a chip. They are a BIOS choice
>  because a real instrument holds exactly one at a time. Sectors 19..29 are
>  byte-identical in all nine, so a third of the region is an invariant template.
>  16_BE: intelfsh preloads a 16-bit part with m_region->as_u16(), a host-native
>  read, so a byte-wide region would reach the device halfword-swapped.

> **************************************************************************
>
> SX-KN6000
>
> IC11, IC12   M29LV160B8TN   16 Mbit flash, program
> IC13         QSIGX3C16008   16 Mbit mask ROM, table data
> IC14         QSIGX3C16007   16 Mbit mask ROM, table data
> IC15         QSIGX3C32021   32 Mbit mask ROM, rhythm data
> IC18         A49BV161490T   16 Mbit flash, custom rhythm (user data)
> IC205        QSIGX3C64004   64 Mbit mask ROM, wave, bank Y (WAY)
> IC206        QSIGX3C64005   64 Mbit mask ROM, wave, bank X (WAX)
> IC207        QSIGX3C64006   64 Mbit mask ROM, wave, bank Y (WAY)
> IC208        QSIGX3C64007   64 Mbit mask ROM, wave, bank X (WAX)
>
> *************************************************************************

> **************************************************************************
>
> SX-KN6500
>
> IC11, IC12   M29LV160B8TN   16 Mbit flash, program
> IC13         C3FBMD000069   16 Mbit table data, supplied pre-programmed
> IC14         C3FBMD000068   16 Mbit table data, supplied pre-programmed
> (the schematic legend reads "PROGRAMMED MASK
> ROM", copied from the KN6000, but the pinout
> drawn beside it - RESET, RY/BY, VPP, WE - is a
> NOR flash, so no device type is asserted here)
> IC15         QSIGX3C32021   32 Mbit mask ROM, rhythm data
> IC18         M29LV160B8TN   16 Mbit flash, custom rhythm (user data).  The
> schematic labels IC11, IC12 and IC18 with this
> same part but three different descriptors, so
> it is fitted at all three flash sites rather
> than being a repeated parts-list row.  The
> firmware will only program a device whose
> autoselect response is in its table, and that
> table holds MBM29LV160B and AT49BV16X4 - both
> 16 Mbit bottom boot, which is what fixes the
> geometry here.  Which vendor's 29LV160B this
> designation refers to is not established.
> IC205        QSIGX3C64004   64 Mbit mask ROM, wave, bank Y (WAY)
> IC206        QSIGX3C64005   64 Mbit mask ROM, wave, bank X (WAX)
> IC207        QSIGX3C64006   64 Mbit mask ROM, wave, bank Y (WAY)
> IC208        QSIGX3C64007   64 Mbit mask ROM, wave, bank X (WAX)
> IC209        QSIGX3C64020   64 Mbit mask ROM, wave, bank Y (WAY)
> IC210        QSIGX3C64019   64 Mbit mask ROM, wave, bank X (WAX)
>
> *************************************************************************

> **************************************************************************
>
> SX-KN2400 and SX-KN2600
>
> One firmware image serves both models, selecting between them at run time,
> and the two boards carry an identical set of memory devices: the schematic
> sheet holding the tone generator and both wave ROMs is the same drawing in
> both manuals, and the board assembly drawings list the same designators.
> The models differ in storage and I/O only - the SX-KN2400 has a floppy
> drive and controller, the SX-KN2600 an SD card interface. They therefore
> share every ROM listed below except the SD sub-processor's program flash,
> which is fitted only on the SX-KN2600.
>
> IC12, IC13   C3FBNG000007   32 Mbit flash, program (see note below)
> IC14         C3ZBNG000023   64 Mbit flash, rhythm and other data
> IC302        C3ZBP0000003   64 Mbit flash, wave bank Y (AWAY bus)
> IC303        C3ZBP0000004   64 Mbit flash, wave bank X (AWAX bus)
> IC404        C3ZBK0000020    4 Mbit flash, SD sub-CPU program (KN2600 only)
>
> Neither board carries a table or font ROM: the schematics, the board
> assembly drawings and the block diagrams agree that the devices listed
> above are the only memories present, and the LCD controller at IC104 has
> no external memory attached.
>
> The block diagrams describe IC302 and IC303 as 128 Mbit parts addressed by
> WAY0-WAY22, but the schematics show only 22 address inputs, and the tone
> generator's WAY22 and WAY23 pins terminate unconnected. The 64 Mbit figure
> from the schematics is used here.
>
> A note on IC12/IC13: the schematics show 21 address inputs driven from CPU
> address lines A2-A22, making these 32 Mbit devices that together span
> 8 MiB. The dumps below cover 4 MiB of that pair. The remainder has not been
> read, so it is not described here; on the KN7000 the equivalent pair holds
> the table data in the half that these dumps do not cover.
>
> *************************************************************************


**`ROM_REGION32_LE(0x400000, "table_data", ROMREGION_ERASEFF) \`**

>  The firmware reads 0x48000000-0x483fffff. No separate table part appears in \
> any SX-KN2400 source, and the header above explains why: as on the KN7000, \
> that data lives in the half of the IC12/IC13 pair these dumps do not cover. \
> The region stands in for it and is left erased. */ \


## Tone generator: the shared voice engine

*Source: `src/mame/matsushita/kn_tonegen.h`*

>  license:GPL2+
>  copyright-holders:Felipe Sanches
> **************************************************************************
>
> Technics MN10300 keyboards -- tone-generator HLE, shared base
>
> Every MN10300-generation Technics keyboard drives its tone generator(s)
> the same way, and unlike most such claims this one is settled by the
> firmware itself rather than by the part numbers. The KN7000 carries two
> `C1BB00000709` LSIs (IC201 master + IC205 sub); the KN6000/KN6500 carry a
> single `D82398GD001` (IC213). Different part numbers -- but the same
> driver architecture, because the two firmwares are re-targets of one
> source tree.
>
> THE DECISIVE EVIDENCE:
>
>  The KN6000's tone-generator write primitive at 0x4849465B is
> BYTE-IDENTICAL to the KN7000's TG-A leg at 0x4C036F7C -- the same 20
> bytes, 81 f8c510 fc8700000598 fae0ffff fc8302000598. The KN7000's
> writer is that same routine with a chip-select branch (cmp 0x40,d0)
> wrapped around it, so the KN7000's two-chip path is literally a
> parameterised generalisation of the KN6000's one-chip path.
>  Both pack the same 32-bit command word (slot<<20)|(class<<16)|data
> and latch it as an ADDRESS halfword to +0 then a DATA halfword to +2,
> with the identical bitfield split (slot at address bit 4, 4-bit
> register index). Both expose the same dual asl-20 / asl-18 addressing
> modes.
>  Both use sixteen halfword registers per voice as four 4-register
> banks of [rate|level] byte-pair envelope segments, and share the
> literal constants 0xFF80/0xFF00 (boot reset), 0xA280/0xA200 and
> 0x7F80/0x7F00 (damp pairs), 0xC000 (mute) and 0x87FF (gate on).
>  Both build the 18-bit pitch with the same instruction idiom
> (and 0x00018000 / or 0x4000), carrying pitch bit 16 in class bit 0.
>  Plane 0x20 (the per-channel send/output matrix) and plane 0x28 (the
> global register bank) sit at the SAME plane numbers on both chips.
>  Both use a 0xB4-stride library voice record and a 0x130-stride part
> tone block, over a 34-part model.
>
> WHAT DIFFERS is numbering and sizing, not behaviour: the per-voice
> register index assignment (the gate is r3 on the KN7000, r0 on the
> KN6000; the envelope banks sit at 0/4/8 vs 4/8/C), the per-voice
> parameter plane numbers below 0x20, the slot count (128 across two
> windows vs 64 in one), the shadow-image stride (0x84 vs 0xA0), and the
> KN7000-only 0x98040010/0x98050010 init strobe.
>
> So the split is drawn exactly where the evidence draws it:
>
> BASE (here) -- the MECHANISM, proven identical on both chips: the
> [rate|level] envelope decode and its rate->seconds law, the
> four-stage per-voice envelope state machine and all per-voice state,
> the gate-follow key coupling, the effect-send/return gains (planes
> 0x20/0x28, same numbers on both), the optional synthetic wave pack,
> and the audio stream and rendering.
>
> DERIVED (kn7000_tonegen.*) -- the NUMBERING: which plane and which
> register index means what, i.e. the tg_write() decode itself, plus
> the chip/window count.
>
> kn6000_tonegen_device is that second decode. Its plane map is only partly
> pinned, so the KN6000/KN6500 render with the same placeholder waveforms the
> KN7000 does.
>
> *************************************************************************


**`virtual void tg_write(int tg, uint16_t addr, uint16_t data) = 0;`**

>  The model-specific half: turn one tone-generator register write into voice
>  events on the shared state below. Each derived device decodes its own chip's
>  register numbering. The arguments are exactly what the chip is given -- a
>  register number and a word -- so nothing here can depend on CPU state the
>  hardware cannot see.


## Tone generator: shared synthesis

*Source: `src/mame/matsushita/kn_tonegen.cpp`*

>  license:GPL2+
>  copyright-holders:Felipe Sanches
> **************************************************************************
>
> Technics MN10300 keyboards -- tone-generator HLE, shared base
>
> The model-independent half of the tone-generator emulation: the per-voice
> envelope state machine and its rate->seconds law, the voice state, the
> gate-follow key coupling, the synthetic wave pack, and the audio stream.
> Concrete tone generators (kn7000_tonegen.cpp) supply the register decode
> that drives it.
>
> See kn_tonegen.h for the firmware evidence behind this split.
>
> *************************************************************************


**`if (m_wdefault < 0)`**

>  The wave ROMs have no dump, so every voice plays a synthesized single-cycle
>  sine through the ordinary sample-playback path rather than a sin() oscillator:
>  the mechanism is the real one, only the data is fabricated. 441 samples per
>  cycle gives a 44100/441 = 100 Hz root.


**`const wentry &we = m_wentries[m_wsel[v]];`**

>  SINGLE, FAITHFUL DATAPATH: every voice reads PCM from the wave pack, exactly
>  as the real chip reads its wave ROM -- donor zones where a KN5000 sample was
>  mapped, or the fabricated default sine (m_wdefault) everywhere else. There is
>  no sin() oscillator; the hardware has none. Linear interpolation, tail loop
>  (seam crossfaded at build time for donors; single cycle for the sine), stepped
>  by musical pitch / root. Faithful mechanism -- the DATA is placeholder, the
>  PLAYBACK PATH is real.


**`if (!std::isfinite(pos) || pos < 0.0 || pos >= double(we.len))`**

>  SANITISE the read position before indexing the PCM. A model whose
>  note->pitch resolve is not yet reversed (e.g. the KN6000) can hand us a
>  non-finite or out-of-range frequency; an unguarded uint32_t(pos) on inf/NaN
>  or a huge pos would index the sample array out of bounds and crash the
>  emulator. Keep pos finite and within the sample before use.


**`double step = m_freq[v] / we.root_hz;`**

>  Advance by musical pitch / root, then wrap into the tail loop. GUARD both:
>  a model whose note->pitch resolve is not yet reversed (e.g. the KN6000) can
>  hand us a non-finite, negative, or absurdly large frequency. The step is
>  clamped finite/non-negative, and the loop wrap is done with an O(1) modulo
>  (NOT a subtract-loop): a huge finite step through a subtract-loop would
>  iterate billions of times and livelock the single-threaded emulator.


## Tone generator: KN7000 device

*Source: `src/mame/matsushita/kn7000_tonegen.h`*

>  license:GPL2+
>  copyright-holders:Felipe Sanches
> **************************************************************************
>
> KN7000 tone generator
>
> Two LSIs, IC201 (master) and IC205 (sub), C1BB00000709, 64 voice slots
> each. Only the register numbering is here; the voice model, envelopes and
> audio stream are shared with the KN6000 in kn_tonegen.h.
>
> *************************************************************************


## Tone generator: the KN7000 register decode

*Source: `src/mame/matsushita/kn7000_tonegen.cpp`*

>  license:GPL2+
>  copyright-holders:Felipe Sanches
> **************************************************************************
>
> KN7000 tone generator -- the register decode
>
> See kn7000_tonegen.h. This file holds the KN7000's register NUMBERING:
> the tg_write() decode that turns firmware register writes into voice
> events on the shared base (kn_tonegen.cpp).
>
> *************************************************************************


**`const double note = 96.0 + (double(p18) - double(0x1C838)) / 1024.0;`**

>  Note-on. The pitch register carries an ABSOLUTE LOG PITCH at 0x400 units
>  per semitone, anchored where pitch18 0x1C838 = MIDI 96, the keybed top-C
>  reference. The firmware folds it by whole octaves into the sample zone's
>  key range when the zone cannot cover the played key (the KN5000's
>  Pitch_Fold_Octaves_Into_Range does exactly this, in the same 8.8 domain),
>  so with the wave ROMs undumped the zone limits are unknown and a voice
>  whose zone would have folded sounds an octave out. The pitch CLASS is
>  exact either way.


**`m_mode[v] = (m_aux[v] & 0x8000) ? 1 : 0;`**

>  Voice life-cycle class:
>   - GATE_FOLLOW: aux bit15 (brass/sax/organ) -- no firmware key-up write; the
>     TG, which hosts the key-bed FIFO, gates them off itself on key release.
>  The synthesis/release class lives in a firmware record the chip never
>  sees, so only the aux word's gate-follow marker is available here.
>  Everything else is treated as firmware-managed, which is the safe
>  default: a managed voice waits for the firmware's key-up write.


## Tone generator: KN6000 device

*Source: `src/mame/matsushita/kn6000_tonegen.h`*

>  license:GPL2+
>  copyright-holders:Felipe Sanches
> **************************************************************************
>
> KN6000/KN6500 tone generator
>
> One LSI, IC213 D82398GD001, 64 voice slots behind a register window at
> 0x98050000/2. Driven entirely by the firmware's voice engine. Only the
> register numbering is here; the voice model, envelopes and audio stream
> are shared with the KN7000 in kn_tonegen.h.
>
> *************************************************************************


## Tone generator: the KN6000/KN6500 register decode

*Source: `src/mame/matsushita/kn6000_tonegen.cpp`*

>  license:GPL2+
>  copyright-holders:Felipe Sanches
> **************************************************************************
>
> KN6000/KN6500 tone generator -- the register decode
>
> See kn6000_tonegen.h for how this numbering was recovered from the
> firmware's own note-on register blit (0x484948CB) and its damp/mute
> literals. This file holds only the decode; the voice model it drives is
> shared with the KN7000 in kn_tonegen.cpp.
>
> *************************************************************************


## Control panel: the shared CP protocol

*Source: `src/mame/matsushita/kn_cpanel.h`*

>  license:GPL2+
>  copyright-holders:Felipe Sanches
> **************************************************************************
>
> Technics MN10300 keyboards -- control-panel HLE, shared base
>
> Every MN10300-generation Technics keyboard (KN7000, KN6000/KN6500,
> KN2400/KN2600, ...) drives its front panel the same way: one 8-bit
> sub-CPU per panel PCB scans that board's button matrix and drives its
> LEDs, and all of them talk to the main CPU over the SAME synchronous
> serial link (channel 0 of the SIO ASIC), using the SAME wire protocol.
>
> That protocol -- the 7-byte TX frame layout, the handshake commands, the
> ATN/RX interrupt dance, the [ADDR][DATA] switch and latched-control
> frames, and the analog controls (DATA dial, TEMPO/PROGRAM wheel, APC/SEQ
> fader) -- lives HERE, because it is genuinely model-independent. This is
> empirically confirmed: the KN6000 driver, running the KN7000's panel
> device unmodified, accepts button presses and its TEMPO/PROGRAM wheel
> works perfectly. Only the *contents* of the matrix differ.
>
> What each model supplies (pure virtuals below):
> - its scan-matrix ioports (how many, and which normalized segment each
> drives),
> - its segment -> wire-ADDR reverse-normalization table,
> - its LED-register decode.
>
> *************************************************************************


## Control panel: shared scan engine

*Source: `src/mame/matsushita/kn_cpanel.cpp`*

>  license:GPL2+
>  copyright-holders:Felipe Sanches
> **************************************************************************
>
> Technics MN10300 keyboards -- control-panel HLE, shared base
>
> The model-independent half of the front-panel emulation: the CP serial
> protocol, the ATN/RX handshake, the analog controllers, and the periodic
> matrix scan. Concrete panels (kn7000_cpanel.cpp, kn6000_cpanel.cpp)
> supply their own matrix geometry and LED decode.
>
> See kn_cpanel.h for the rationale of the split.
>
> *************************************************************************


**`void kn_cpanel_base_device::tx_byte(uint8_t data)`**

>  One panel TX byte from the main CPU (SIO channel 0). The main CPU transmits
>  7-byte FRAMES with interleaved line syncs:
>    pos 0 sync, 1 sync, 2 PAYLOAD1, 3 sync, 4 PAYLOAD2, 5 sync, 6 sync
>  Parse by position.


**`switch (m_panel_p1)`**

>  Frame complete. Handshake commands (payload1 = 0x1F/0x1D/0x1E init,
>  0x20/0xE0 ping CPL/CPR, 0x29/0xDD -- the boot's observed sequence) are
>  answered with a TYPE-3 sync packet and an ATN pulse. All other frames
>  carry LED-register updates [addr][data].


**`TIMER_CALLBACK_MEMBER(kn_cpanel_base_device::panel_event)`**

>  Deferred panel events (one-shot; scheduled from ISR-context register writes so
>  the interrupt lands after the firmware's current handler returns):
>   param 1: ATN edge on the panel's external-interrupt pin -> main asserts group 0x1A.
>   param 2: the panel places its next reply byte on SIO0 -> main pushes it onto the
>            RX FIFO and asserts group 0x10 (the state-8 handler reads it from +9).


**`{`**

>  Front-panel APC/SEQ VOLUME slider -> the firmware's own accompaniment/sequencer volume,
>  delivered the way the real hardware does it: the panel sub-CPU digitises the pot and sends a
>  CP-protocol TYPE 2 "latched control" frame [ADDR, DATA]. ADDR 0xD2 (bank11/type2/sub2) = APC/SEQ
>  VOLUME. The handler does DATA -> NOT -> latch -> >>1 -> a monotonic 0..127 remap, so a LOUDER
>  setting needs a LOWER DATA byte. Map the 0..100 adjuster accordingly and emit only on change.


**`m_vol_apcseq_prev = data;`**

>  First scan: just record the initial pot position. Do NOT emit a frame during early boot --
>  the firmware isn't servicing the panel handshake yet, so an undelivered frame would sit in
>  the response queue and block all later ATN kicks (buttons included). The slider takes over
>  on the first real move (matching the hardware's soft-takeover behaviour).


**`{`**

>  Front-panel DATA dial (the big value wheel with the central SET button) -> CP-protocol TYPE 2
>  "latched control" frame [0x10, POSITION]. The wheel is a rotary ENCODER: the panel sub-CPU keeps
>  an 8-bit position counter and ships it on the CP link, and the main-CPU handler DIFFS successive
>  positions to derive turn direction/amount. MAME's IPT_DIAL is precisely this kind of relative
>  accumulator (0..255, wraps), so we forward its value verbatim.


**`{`**

>  Front-panel TEMPO/PROGRAM knob -> CP-protocol RELATIVE encoder [0x17, STEP]. The main-CPU handler
>  latches the wire byte, but the tempo routine ADDS it as a SIGNED 8-bit step every frame --
>  tempo += (int8_t)wire -- it does NOT diff an absolute position. So forward a clean SIGNED step,
>  slewing m_tempoknob_prev toward the adjuster one detent per scan. (Sending a growing ABSOLUTE
>  position made the firmware race to the 300-BPM rail regardless of direction.)


**`uint8_t seg_state[MAX_SEGS] = { 0 };`**

>  Inputs are declared one ioport per NORMALIZED SEGMENT, the identity the firmware's
>  button dispatcher uses. For a changed segment we emit its 2-byte [ADDR][DATA] switch
>  frame, computing the wire ADDR by REVERSE-normalizing via the model's table.
>  DATA = segment bitmask (bit=1 pressed); the main CPU XORs vs its shadow for edges.
>  Delivery rides the ATN dance via panel_queue (a bare fifo push never IRQs).


## Control panel: KN7000 device

*Source: `src/mame/matsushita/kn7000_cpanel.h`*

>  license:GPL2+
>  copyright-holders:Felipe Sanches
> **************************************************************************
>
> KN7000 control panel HLE
>
> High-level emulation of the KN7000 front-panel sub-CPUs (one per panel
> PCB) that scan the button matrices and analog controls and drive the panel
> LEDs, talking to the main MN10300 over a synchronous serial link (channel
> 0 of the SIO ASIC).
>
> Only the KN7000-SPECIFIC half lives here: the button scan matrix (40
> normalized segments, 230 descriptor button-bits) and the three-board LED
> register decode. The CP wire protocol, the ATN/RX handshake and the analog
> controllers are shared with the other MN10300 models and live in the base
> class (kn_cpanel.h / kn_cpanel.cpp).
>
> *************************************************************************


## Control panel: the KN7000 matrix and LEDs

*Source: `src/mame/matsushita/kn7000_cpanel.cpp`*

>  license:GPL2+
>  copyright-holders:Felipe Sanches
> **************************************************************************
>
> KN7000 control panel HLE
>
> Like the KN5000, the KN7000 front panel is driven by dedicated panel
> sub-CPUs -- one per panel PCB -- that scan the button matrices and drive
> the LEDs, and talk to the main MN10300 over a synchronous serial link.
> The main CPU delivers whole bytes on SIO channel 0; this device parses the
> 7-byte TX frames, decodes the LED-register writes, and replies with
> handshake / button-event / analog-controller packets that ride back to the
> firmware via the panel ATN pulse and the SIO0 receive interrupt.
>
> *************************************************************************


**`static const uint8_t PORT_SEG[22] = {`**

>  Physical scan matrix == firmware normalized-segment space (see kn7000.cpp INPUT_PORTS header).
>  PORT_SEG[port] is the normSeg (= sub-CPU scan column) that input port n drives; the SW bit is
>  forwarded unchanged. Each scan column maps to exactly one wire ADDR (no per-bit repacking), so
>  this is a pure identity -- no per-button translation table is needed.


**`static INPUT_PORTS_START(kn7000_cpanel)`**

>  The front-panel BUTTON matrix belongs to the panel sub-CPUs this device emulates, so the
>  ports live HERE (device_input_ports()) rather than in the driver's INPUT_PORTS -- the layout
>  references them as "cpanel:CP{board}_SEG{col}". Each CP{board}_SEG{col} port is one scan
>  segment the panel sub-CPU drives, and each bit is one SW sense line it reads. This is exactly
>  the firmware's normalized-segment (normSeg) space: port n -> normSeg PORT_SEG[n] with the bit
>  unchanged, then reverse-normalized to the wire ADDR (one ADDR per column: CPL/CPC bank11 subs
>  0xC0-0xCB -> segs 0x00-0x0B; CPR bank00 subs 0x00-0x09 -> segs 0x0C-0x15). Because each scan
>  column maps to a single wire ADDR (no per-bit repacking), naming the ports by scan column is a
>  pure identity. Button-to-column assignments come from each button's firmware event code + arg.
>  LEDs are driven independently on the same normSeg keys.


**`uint8_t kn7000_cpanel_device::seg_wire_addr(int seg) const`**

>  Reverse-normalization (the inverse of the firmware's normalization table):
>    normSeg 0x00-0x0B -> ADDR 0xC0-0xCB (grp3), 0x0C-0x15 -> 0x00-0x09 (grp0),
>    0x16-0x19 -> 0xD0-0xD3, 0x20 -> 0x17. normSeg 0x1A (wire 0x10 = DATA dial) is a
>    VALUATOR, emitted by the base class's dial block, NOT here; 0x1B-0x1F have NO wire path.


**`const int reg = addr & 0x3f;`**

>  One decoded LED-command frame. ADDR = board (bits 7:6; 0x00 = CPR / right panel, 0xC0/0xE0 =
>  CPL / left panel) | LED register (bits 5:0). Each DATA bit is one LED; its output index is
>  reg*8 + bit within that board's bank (cpr_led#/cpl_led#), and the comment names the panel
>  function/mode that LED indicates (KN5000 style). This map is kept in sync with -- and generated
>  from -- the layout's LED bindings (tools/gen_lay.py LED_PURPOSE), which carry the empirically
>  verified assignments (e.g. FAVORITES = cpr_led2 via PANEL_LED). Bits marked
>  (unmapped) are real firmware LEDs whose panel function is not yet identified; the default arm
>  keeps any register not enumerated here working too.


**`const int creg = addr & 0x1f;`**

>  CPC board (centre panel: OTHER PARTS/TG, the 16-part MUTE grid, ...). One sub-CPU drives both
>  CPL and CPC LEDs and selects the board with ADDR bit 5: 0xC0-0xDF = CPL, 0xE0-0xFF = CPC
>  (empirically CPC LED frames appear only as ADDR 0xE0-0xFF; register = ADDR bits 4:0). Bits not
>  yet tied to a panel function are still driven, so the layout can name cpc_led# once identified.


## Control panel: KN6000 device

*Source: `src/mame/matsushita/kn6000_cpanel.h`*

>  license:GPL2+
>  copyright-holders:Felipe Sanches
> **************************************************************************
>
> KN6000 / KN6500 control panel HLE
>
> The SX-KN6000 and SX-KN6500 share ONE panel device: their firmware button
> matrices are BYTE-IDENTICAL (30 descriptor segments, 164 button-bits, zero
> differing entries), so a single class serves both models.
>
> The panel is scanned by TWO Mitsubishi M37471M2196S 8-bit sub-CPUs (service
> manual pp.45-49): IC1 on the CPL board (10 SEG strobe columns) and IC10 on
> the CPR board (16 SEG columns, 10 of them wired). The CPC, LCDL, LCDC and
> LCDR boards have no CPU of their own -- they are matrix extensions hanging
> off those two. Buttons sit at (SEG column x SW0..SW7 return line); LEDs sit
> at (PNP anode group x SEG column).
>
> The CP wire protocol, the ATN/RX handshake and the analog controllers are
> shared with the KN7000 and live in the base class (kn_cpanel.h).
>
> *************************************************************************


## Control panel: the KN6000/KN6500 matrix and LEDs

*Source: `src/mame/matsushita/kn6000_cpanel.cpp`*

>  license:GPL2+
>  copyright-holders:Felipe Sanches
> **************************************************************************
>
> KN6000 / KN6500 control panel HLE
>
> ONE device serves both models: their firmware button matrices are
> BYTE-IDENTICAL (compared descriptor-for-descriptor across all 30 segments
> and 164 button-bits -- zero differences).
>
> Where this matrix comes from
> ----------------------------
> The seg/bit GEOMETRY is extracted from the firmware itself: the
> PanelButtonDispatch descriptor arrays, reached through the pointer table at
> library 0x4C19BCAC (KN6000) / 0x4C19BDB0 (KN6500), consumed by the dispatcher
> at 0x4844D376 which indexes that table directly with the segment byte. Each
> 12-byte entry is { u16 event, u16 class, u8 mask, u8 bit, u8 group, u8 flag,
> u32 handler }.
>
> The NAMES come from the SX-KN6000 service manual (pp.45-49), and the two
> sources agree cell-for-cell: all 150 populated button-bits in normSeg
> 0x00-0x13 are accounted for, and every switch group the manual inventories
> (16 RHYTHM GROUP in 6/6/4 columns, 16 SOUND GROUP in 6/6/4, 32 MUTE UP/DOWN
> in four 8-tall columns, 6 PERFORMANCE PADS sharing three columns as 1/4, 2/5,
> 3/6, 8 PANEL MEMORY, the CONDUCTOR and PART SELECT quads) lands exactly where
> the descriptors put it. That mutual confirmation is what makes this map
> trustworthy without a live sweep.
>
> Board split (service manual, confirmed by the descriptor content)
> ----------------------------------------------------------------
> Two Mitsubishi M37471M2196S sub-CPUs scan everything:
> IC1 on CPL -- 10 SEG columns -> normSeg 0x00-0x09, covering the CPL board
> itself plus its matrix extensions LCDL and LCDC:
> 0x00-0x03 LCDL (RHYTHM GROUP, SOUND ARRANGER, APC, LCDL keys)
> 0x04-0x08 LCDC (32 MUTE UP/DOWN, PAGE/TR/HELP/HOLD/EXIT)
> 0x09      CPL  (PERFORMANCE PADS ops, MSA, VARIATION, DEMO)
> IC10 on CPR -- 16 SEG columns, 10 wired -> normSeg 0x0A-0x13, covering CPR
> plus its extensions LCDR and CPC:
> 0x0A-0x0D LCDR (SOUND GROUP, SUSTAIN/DIGITAL EFFECT, LCDR keys)
> 0x0E-0x13 CPC + CPR (transport, effects, PANEL MEMORY, ...)
> A button is (SEG column x SW0..SW7 return line); an LED is (PNP anode group
> x SEG column). Note normSeg 0x12 is CPR SEG9, not SEG8: the manual finds CPR
> SEG8 unwired, and the firmware's normalized numbering skips it.
>
> Segments 0x14-0x1D exist in the descriptor table but are NOT panel buttons --
> they are the latched analog controls (the four pots at 0x16-0x19, the DATA
> dial at 0x1A) and pedal/rear switches, which reach the firmware through the
> base class's TYPE 2 control path rather than the switch-frame path.
>
> The CP wire protocol, ATN/RX handshake and analog controllers are shared with
> the KN7000 and live in the base class (kn_cpanel.cpp).
>
> *************************************************************************


**`uint8_t kn6000_cpanel_device::seg_wire_addr(int seg) const`**

>  Reverse-normalization: normSeg -> CP wire ADDR. The KN6000 keeps the same two-bank
>  wire allocation as the KN7000 -- the CPL-side sub-CPU answers on ADDRs 0xC0.., the
>  CPR-side one on 0x00.. -- but with 10 columns each rather than the KN7000's 12 + 10.
>  (That the wire encoding is shared is what makes the KN6000 accept panel traffic at all
>  while running the KN7000's panel device, and is why its TEMPO/PROGRAM wheel already
>  worked: only the matrix CONTENTS differ, not the transport.)


**`void kn6000_cpanel_device::panel_led_frame(uint8_t addr, uint8_t data)`**

>  One decoded LED-command frame. ADDR = board (bit 7:6 clear = CPR, set = CPL) | LED
>  register; each DATA bit is one LED at index reg*8 + bit within that board's bank.
>
>  The service manual inventories every LED by designator, colour and legend (CPL D125-D130,
>  LCDL D101-D134, LCDC D106, LCDR D301-D320, CPC D323-D345, CPR D351-D377). What it does NOT
>  give without further wire tracing is the anode-group x SEG coordinate for most of them,
>  i.e. which register/bit the
>  firmware uses. So this is a faithful GENERIC decode onto cpl_led#/cpr_led# outputs: the
>  firmware's LED writes land on stable, correctly-banked output names. Binding individual
>  D-numbers to legends is deferred until a KN6000 .lay exists to display them (there is none
>  yet), at which point the manual's inventory plus the built-in "Panel SW & LED test"
>  (service manual p.22 section 7.5) gives the ground truth to bind against.
