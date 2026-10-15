---
layout: page
title: SubCPU Payload Loading
permalink: /subcpu-payload-loading/
---

# SubCPU Payload Loading Investigation

This page documents the investigation into SubCPU firmware payload loading in MAME emulation. The investigation uncovered multiple bugs in MAME's TMP94C241 emulation that prevented DMA transfers and inter-CPU communication. All have been fixed, and the SubCPU payload now loads, executes, and communicates bidirectionally with the Main CPU.

> **Status: RESOLVED.** As of 2026-02-17, the SubCPU payload transfer and inter-CPU communication are **fully working**. The "Sound Name Error" messages are gone. The display shows voice names (Piano, Bigband Brass, Modern E.P.1), rhythm patterns, mixer levels, and menu navigation works correctly. Button input is also functional. This required 12 fixes to MAME's TMP94C241 emulation spanning DMA, interrupts, port I/O, serial communication, and interrupt timing. See [Boot Sequence]({{ site.baseurl }}/boot-sequence/) for the overall boot flow and [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/) for latch communication details.
>
> **Where the fixes live (2026-10).** Fixes 1-4 and 6-11 are in mainline MAME: Fix 1 as mamedev/mame#14970 and Fix 8 as #14995. The DMA subsystem, DMAR, the INT0 level-detect re-assertion and direction-aware port reads came in #15003, and #15878 refined the re-assertion's HDMA guard. The sub-CPU peripheral stubs (Fix 11) came with #15143. Fix 5 (`perfect_quantum`) and Fix 12 (`clear_int0_level`) are only in the kn7000_mame overlay. The overlay has since dropped Fix 7's re-assertion itself (`3fd44f3`, 2026-08-05); see [Fix 12](#fix-12-int0-stale-m_level-fix-clear_int0_level). A later recurrence of the "Sound Name Error" (2026-07-20) was caused by the overlay's SNS write tap and cured by removing it; see [SNS NMI Emulation]({{ site.baseurl }}/sns-nmi-emulation/).

## Background

After replacing the decompressed SubCPU payload ROMs with the compressed originals (LZSS SLIDE4K format at Custom Data Flash offset 0xE0000 = address 0x3E0000), the MAME driver originally showed "Sound Name Error" messages. This indicated the SubCPU never received its firmware payload, so sound commands failed.

The firmware's `SubCPU_Send_Payload` function (address `0xEF068A`) is responsible for:

1. Sending 5 x 64KB of **tone-database** data from Table Data ROM (`0x830000`-`0x870000`) to SubCPU RAM (see [What the two source regions actually hold](#what-the-two-source-regions-actually-hold) — this is *not* the Sub CPU's executable)
2. Decompressing the compressed payload from `0x3E0000` to Main CPU RAM at `0x050000`
3. Sending the decompressed data (the sub-CPU executable; its first 256 bytes, the entry-point block, go last) to SubCPU via E1 bulk transfers
4. The last 256-byte E1 transfer writes to SubCPU address `0x000400`-`0x04FF`, which includes `SUBCPU_STATUS_FLAGS` at `0x04FE` -- when bit 6 of that byte is set by DMA, the boot ROM's polling loop triggers payload execution

## Boot Flow: Payload Transfer

The complete calling sequence during boot:

```
User_didnt_request_flash_mem_update (0xEF05E8)
  │
  ├── SET 0, (PA)              → Release Sub CPU from reset
  ├── SubCPU_Init_DMA_Channels → Initialize DMA for inter-CPU comm
  ├── EI 000h                  → Enable interrupts
  ├── SubCPU_Send_Payload      → Transfer 192KB firmware payload
  ├── SubCPU_Payload_Verify    → Verify checksums
  ├── ScreenGroup_Dispatch(0)  → Init phase 0 of every subsystem (boot-sequence: Subsystem Init Phases)
  └── ... (continues boot)
```

### SubCPU_Send_Payload Detail (0xEF068A)

Source: `v10/maincpu/kn5000_v10_program.s:1475`

```
Phase 1: Transfer 5 x 64KB from Table Data ROM
  0x830000 → SubCPU 0x050000 (64KB)
  0x840000 → SubCPU 0x060000 (64KB)
  0x850000 → SubCPU 0x070000 (64KB)
  0x860000 → SubCPU 0x080000 (64KB)
  0x870000 → SubCPU 0x090000 (64KB)

Phase 2: LZSS Decompression
  Source: 0x3E0000 (Custom Data Flash)
  Dest:   0x050000 (Main CPU RAM, temporary)
  Calls SLIDE_Parse_Header (LZSS decompressor)
  If decompression fails (HL=0xFFFF): falls back to Table Data ROM base 0x800000
  (the `ld xiz, 0x800000` in `SubCPU_Send_Payload` — *not* 0x830000, as older notes had it)

Phase 3: Transfer decompressed data to SubCPU
  XIZ+0x100, 64KB    → SubCPU 0x00F000
  XIZ+0x10100, 64KB  → SubCPU 0x01F000
  XIZ+0x20100, 0xFF00 → SubCPU 0x02F000
  XIZ, 0x100 (256B)  → SubCPU 0x000400 (entry point!)
```

### Confirmed Transfer Pattern (from MAME log analysis)

The following 9 E1 blocks were confirmed in the MAME log with 524,358 total HDMA transfers:

| Block | Source Address | SubCPU Dest | Size | Purpose |
|-------|--------------|-------------|------|---------|
| 1 | 0x830000 | 0x050000 | 64KB | Tone database, part 1 of 5 |
| 2 | 0x840000 | 0x060000 | 64KB | Tone database, part 2 of 5 |
| 3 | 0x850000 | 0x070000 | 64KB | Tone database, part 3 of 5 |
| 4 | 0x860000 | 0x080000 | 64KB | Tone database, part 4 of 5 |
| 5 | 0x870000 | 0x090000 | 64KB | Tone database, part 5 of 5 |
| 6 | 0x050100 | 0x00F000 | 64KB | Decompressed payload part 1 |
| 7 | 0x060100 | 0x01F000 | 64KB | Decompressed payload part 2 |
| 8 | 0x070100 | 0x02F000 | 65280B | Decompressed payload part 3 |
| 9 | 0x050000 | 0x000400 | 256B | Entry point code + status flags |

### E1 Bulk Transfer Protocol

Source: `v10/maincpu/boot/system_handlers.s:5700`

Each E1 transfer follows this protocol:

1. Wait for `SSTAT1` high (Sub CPU ready)
2. Clear `MSTAT0`, set state to 2 (two-phase)
3. Write `0xE1` to latch at `0x140000` → triggers INT0 on Sub CPU
4. Wait for `SSTAT1` low (Sub CPU acknowledged E1)
5. Set `MSTAT0`, send 6-byte header (dest addr + byte count) via `Audio_DMA_Transfer`
6. Wait for state transition, send actual data payload via `Audio_DMA_Transfer`

The Main CPU sends data byte-by-byte in a tight software loop (`Audio_DMA_Transfer` at `0xEF341B`). Each write to the latch triggers INT0 on the Sub CPU.

### Sub CPU Reception (Boot ROM INT0 Handler)

Source: `subcpu/boot/kn5000_subcpu_boot.s:1547`

The Sub CPU's INT0 handler (`InterCPU_RX_Handler` at `0xFF881F`) processes incoming bytes:

1. **First byte** (command): DMAV0 not armed, so CPU INT0 handler fires
   - Reads command byte from latch (`0x120000`)
   - For E1: Sets up DMA channel 0 destination and count (6 bytes for header)
   - Arms DMAV0 = `0x0A` (DMA triggers on INT0 for subsequent bytes)
2. **Subsequent bytes**: DMAV0 armed, so HDMA processes INT0
   - Each latch write triggers INT0 → HDMA transfers one byte to destination
   - DMA count decrements automatically
3. **DMA completion**: Fires DMA completion interrupt
   - `DMA_Complete_Handler` advances state machine (state 2→1→0)
   - `CMD_Dispatch_Handler` sets up phase 2 DMA (actual data transfer)

### Payload Execution Trigger

**Critical finding:** The Main CPU does NOT send a dedicated E3 command byte to trigger payload execution. Instead, the last 256-byte E1 transfer (block 9) writes to SubCPU addresses `0x000400`-`0x04FF`. This range includes `SUBCPU_STATUS_FLAGS` at address `0x04FE`.

When the HDMA transfer writes a byte with bit 6 set to address `0x04FE`, the Sub CPU's main loop polling detects this and jumps to the payload entry point:

```asm
; subcpu/boot/kn5000_subcpu_boot.s:774
MAIN_LOOP:
    res 6, (SUBCPU_STATUS_FLAGS)    ; Clear ready flag
.wait_loop:
    bit 6, (SUBCPU_STATUS_FLAGS)    ; Check if payload ready
    jr  Z, .check_status
    ei  6                           ; Enable interrupt level 6
    CALL_ABS24 PAYLOAD_ENTRY        ; Call payload at 0x0400
```

**Confirmed in MAME log:** After HDMA writes to dst=0x0004FE, the SubCPU begins executing payload code at PC=0x01F929 (within the expected payload address range 0x00F000-0x03EE75).

### The E3 Command (Separate from Payload Loading)

`0xE3` is **not** a data command for handler 7. The boot ROM's INT0 handler (`InterCPU_RX_Handler`, `subcpu/boot/kn5000_subcpu_boot.s:1575-1579`) and the payload's (`INT0_HANDLER`, `v142/subcpu/kn5000_subprogram_v142.s:3180-3183`) both test for `0xE3` before the 3-bit dispatch, and both only set bit 6 of `0x04FE` (`SUBCPU_STATUS_FLAGS`; `PAYLOAD_LOADED_FLAG` in the payload source), which in the boot ROM would also trigger payload execution. The byte never reaches `CMD_DISPATCH_TABLE` (see [SubCPU Command Format]({{ site.baseurl }}/subcpu-command-format/#special-commands-e1e2e3)):

- The main CPU's only literal E-command writes to the latch are `0xE1` and `0xE2` (`v10/maincpu/boot/system_handlers.s:5722`, `:5597`); no `0xE3` write has been found
- This E3 path is NOT used during normal boot -- the payload loading trigger comes from the DMA write to 0x04FE

## What the transfer actually carries (2026-08 update)

The nine E1 blocks above were established in 2026-02 from MAME logs, and the labels used
then ("config data", "payload") were placeholders. The disassembly work of 2026-08 replaced
both blobs with symbolic source, so the contents can now be stated exactly.

### What the two source regions actually hold

**`0x830000`-`0x87FFEF` (Table Data ROM) is the tone database — data, not code.** It is now
fully symbolic source (`table_data/tone_database_directory.s`, `..._records.s`,
`..._aux.s`): a directory of 4-byte slots at `0x830000`, bank-select maps and per-bank tone
number tables, a **629-entry LE32 tone-record offset table at `0x831B00`**, then the
variable-length tone/voice records from `0x8324D4`, and an auxiliary tail holding drum kits,
percussion records, name lists, envelope data and drawbar presets. Every offset inside the
database is *database-relative*, which is why the same numbers are equally valid as Sub CPU
addresses once the base lands at `0x050000`: `DSP_System_Init` on the Sub CPU stores that
base in `ToneDB_RelBase` (`0x045310`) and `ToneDB_RootPtr` (`0x045314`), and the Sub CPU
disassembly therefore never mentions an `0x83xxxx` address.

> **Retraction.** Project notes used to describe `0x830000` as holding the "Sub CPU firmware
> payload" or the Sub CPU executable. That is **wrong** and is withdrawn: the region is the
> tone database.
>
> Where the Sub CPU's executable comes from at run time is a *separate* question.
> `SubCPU_Send_Payload` sources the code blocks (Sub CPU `0x400` and `0xF000`-`0x3EEFF`) from
> a base in `XIZ`: the LZSS image at Custom Data Flash `0x3E0000` if it decompresses, and
> table-data `0x800000` otherwise. **In the images this project holds, neither is the
> payload.** Custom-data `0x3E0000` is 131,072 bytes of `0xFF` with no `SLIDE` magic anywhere
> in the 1 MB dump, and no byte of `kn5000_subprogram_v142.rom` appears anywhere in the
> table-data or custom-data dumps.
>
> **Update (August 2026): the mechanism is now closed; only the dump provenance is open.**
> A File Type 007 update disc is proven to write the compressed payload to `0x3E0000`
> verbatim, and the compressed file MAME overlays there was carved from a genuine v10 update
> floppy whose two SLIDE4K streams decode byte-exactly to `kn5000_v10_program.rom` and
> `kn5000_subprogram_v142.rom`. What remains unresolved is why *our* IC19 image lacks that
> region — never programmed, interrupted install, or truncated dump are
> byte-indistinguishable. Note that the earlier inference "so no File Type 007 update was
> ever applied to the dumped unit" is **not** supported by the file. See
> [Sub-CPU Payload Provenance]({{ site.baseurl }}/subcpu-payload-provenance/).

### The payload image's own address layout

`kn5000_subprogram_v142.rom` is 196,608 bytes (`0x30000`) and is **not** a flat image of one
address range. Its first 256 bytes are Sub CPU `0x000400`-`0x0004FF` (block 9 above, the
entry point plus `SUBCPU_STATUS_FLAGS`); from file offset 256 onward it is Sub CPU
`0x00F000`-`0x03EEFF` (blocks 6-8). The arithmetic closes exactly:
`256 + 0x2FF00 = 0x30000`. Sub CPU `0x000500`-`0x00EFFF` is never transmitted — at run time
that window is live DRAM holding the payload's variables (serial ring buffers at
`0x000A00`/`0x000E16`, the inter-CPU command buffers at `0x0010F0`/`0x001116`/`0x00111C`,
the voice-pool and channel record arrays at `0x00112D`/`0x001349`, and the DSP command ring
at `0x003B60`).

### Three data zones, now carved

Three contiguous data zones account for 59,551 bytes of the 196,608-byte image — a little
over 30 % of it. Until 2026-08 all three sat in the disassembly as long raw byte runs; the
Wave-3a packages replaced them with individually labelled tables (commits `09a82ec`,
`c5816ae`, `85ecca2` in the disassembly repository), and the rebuilt ROM is still
byte-identical. Note that this is a *carve*, not a full explanation: several tables in
zone A0 are named from their consumer's arithmetic rather than from understood semantics,
and at least one block (`VoiceParamFinalize_HandlerParams`, `0x00FB3E`) has no located
consumer at all.

| zone | Sub CPU range         | size     | contents                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
|------|-----------------------|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A0   | `0x00F7E6`-`0x012114` | 10,543 B | audio-command jump tables and opcode→case maps, TG power-up defaults, per-key bend/pan/level/EG curve families, the 12-row `DSP_ChanFreq_CurvePool` (`0x011016`), the 14 × 39-byte `DSP_AlgoDescriptor_Records` (`0x011E16`), TVF and envelope curves, two DSP1 image-header strings                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| A    | `0x012195`-`0x014738` | 9,636 B  | `DSP_EQ_FreqHz_Table` (`0x012397`, 27 × f32 ISO ⅓-octave centres) and `DSP_EQ_Q_Table` (`0x012403`, 32 × f32), five Q23 coefficient ladders (`DSP_FreqParamCurve_Algo0/1/2` at `0x012483`/`0x012613`/`0x0127A3`, `DSP_OscParamCurve` at `0x0129A3`, `DSP_CoeffCurve_Op62` at `0x012B33`), the DSP floating-point constant pool (`0x012CD3`-`0x0131CE`, 223 constants each labelled `FPConst_<reader>_<value>`), `DSP_MixerGain_Curve` (`0x0131CF`), and the per-effect parameter metadata complex from `0x0133CF` — `EFF_ParamCount_Table` (`0x0143AD`), `EFF_ParamRanges_PtrTable` (`0x014411`), `EFF_ParamDefaults_PtrTable` (`0x0145A1`) — which is a byte- and relocation-identical copy of main-CPU `0xEE4FC6-0xEE636B`, read by the main CPU's `DSPCfg_*` routines and by nothing in this payload ([details]({{ site.baseurl }}/dsp-effect-data-zone/#the-main-cpu-holds-the-same-metadata-and-reads-it)), plus the two interpreter offset tables `DSP_BytecodeInterpreter_CaseOffsets` and `DSP_Translator_CaseOffsets` |
| B    | `0x0147B3`-`0x01E17E` | 39,372 B | the DSP effect program + parameter zone: bytecode streams and parameter record tables for all 100 effect-algorithm numbers — documented on its own page, [DSP Effect Data Zone]({{ site.baseurl }}/dsp-effect-data-zone/)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

Two readings the earlier raw-blob banners carried were **refuted** by the carve and are
withdrawn:

* There is **no "exponential pitch table at `0x13318`"**. `0x13318` falls in the middle of
  `DSP_MixerGain_Curve` at `0x0131CF`, a 128-entry `u32` piecewise-exponential **amplitude**
  curve ending exactly at digital full scale (`0x7FFFFF00`), spanning 53.5 dB in four
  segments. Its only proven consumer, `DSP_MixerCoeff_Compute` (`0x03C067`), uses entries as
  gain, feeding the mixer-gain product written to DSP2 registers `0xD0`/`0xD3`. Read as
  pitch, the middle segment would be 54.82 cents/step, which matches no musical law.
* There are **no "two 128-byte tables at `0x00FF00` / `0x00FF80`"**. The "11 references
  each" that produced that claim are `ldw (ToneGen_RegDataPort:24), 0xff00` / `0xff80`
  instructions (`ToneGen_RegDataPort` = `0x100002`) — immediate values written to the
  tone-generator data port, not table addresses. No table begins at either address.

Zone A0's split points are all consumer-verified: every boundary is an address some
instruction references, and the set tiles the span with no orphan bytes.

## Fixes Applied

### Fix 1: LDC Control Register Mapping (Critical)

**Root cause of HDMA failure:** The TMP94C241 uses different control register (CR) numbers in the `LDC` instruction than the TMP96C141/TMP95C063. MAME's shared TLCS900 instruction decoder only had the old numbering, causing `LDC DMAD0, XWA` and `LDC DMAC0, WA` to silently write to a dummy register. The DMA destination address and transfer count were never set!

**TMP94C241 vs TMP96C141 CR numbers:**

| Register | TMP96C141 CR | TMP94C241 CR | Size |
|----------|-------------|-------------|------|
| DMAS0-3 | 0x00-0x0C | 0x00-0x0C | 32-bit (same) |
| DMAD0-3 | 0x10-0x1C | 0x20-0x2C | 32-bit (different!) |
| DMAC0-3 | 0x20-0x2C | 0x40-0x4C | 16-bit (different!) |
| DMAM0-3 | 0x22-0x2E | 0x42-0x4E | 8-bit (different!) |

**Fix:** Added TMP94C241 CR numbers as additional cases in the shared LDC instruction decoder (`900tbl.hxx`). Since the numbers don't overlap within each register size class, this doesn't affect other TLCS900 variants. Also updated the disassembler (`dasm900.cpp`) to recognize the new CR numbers.

**Files modified:**
- `mame_driver/src/devices/cpu/tlcs900/900tbl.hxx` -- Added CR cases for p_CR8, p_CR16, p_CR32 (both p1 and p2 operands)
- `mame_driver/src/devices/cpu/tlcs900/dasm900.cpp` -- Added CR labels for O_CR8, O_CR16, O_CR32

### Fix 2: DMAM Register Encoding

**Second root cause:** The DMAM (DMA Mode) register encoding in `tlcs900_process_hdma()` was wrong. The implementation used independent source/destination direction bits, but the actual TMP94C241 (like TMP95C061) uses a combined mode encoding:

| DMAM bits 4-0 | Source | Destination | Size |
|---------------|--------|-------------|------|
| 0x00 | Fixed | Increment | Byte |
| 0x01 | Fixed | Increment | Word |
| 0x02 | Fixed | Increment | Long |
| 0x04 | Fixed | Decrement | Byte |
| 0x08 | Increment | Fixed | Byte |
| 0x10 | Fixed | Fixed | Byte |

**Impact:** The Sub CPU boot ROM sets DMAM0 = 0 during `INIT_DMA_SERIAL`, which means "byte transfer, source fixed (latch), destination incrementing (buffer)". With the old decoding, DMAM=0 was interpreted as "both fixed", causing all received bytes to overwrite the same address.

**Fix:** Replaced the generic bit-field decoding with a switch-based implementation matching the proven TMP95C061 code in MAME.

### Fix 3: DMAR Register Implementation (0x109)

The DMAR register at SFR address `0x109` was missing from the MAME `tmp94c241` device. This register provides software-triggered DMA: writing bit N triggers an immediate DMA transfer on channel N.

**Fix:** Added `dmar_w()` handler at address `0x109` in the SFR address map. When a bit is set, it calls `tlcs900_process_hdma()` for the corresponding channel, performing an immediate DMA transfer.

This register is used by the Main CPU's INT0 handler (`LD (DMAR), 001h` at `0xEF352D`) to trigger DMA channel 0 when receiving data from the Sub CPU.

### Fix 4: HDMA Priority Over IRQs (Critical)

**Third root cause of HDMA failure:** In MAME's `execute_run()` loop, `check_irqs()` ran BEFORE `check_hdma()`. When INT0 fired, `check_irqs()` would dispatch to the INT0 interrupt handler and clear the interrupt flag. By the time `check_hdma()` ran, the flag was gone -- HDMA never fired even though DMAV0 was correctly set to 0x0A.

On real TMP94C241 hardware, when a DMA channel's DMAV matches an active interrupt source, the DMA transfer takes priority -- the interrupt is consumed by HDMA instead of being dispatched to the CPU's interrupt handler.

**Fix:** Added HDMA priority check in `check_irqs()`. Before processing each interrupt, it checks if any active HDMA channel targets that interrupt source (via DMAV matching). If so, the interrupt is skipped in `check_irqs()`, allowing `check_hdma()` to process it as a DMA trigger instead.

```cpp
// In check_irqs(), before processing an interrupt:
bool hdma_targeted = false;
for (int ch = 0; ch < 4; ch++)
{
    if (m_dma_vector[ch] == tmp94c241_irq_vector_map[i].dma_start_vector)
    {
        hdma_targeted = true;
        break;
    }
}
if (hdma_targeted)
    continue;  // Let check_hdma() handle this instead
```

### Fix 5: CPU Scheduling (perfect_quantum)

**CPU scheduling issue:** MAME runs CPUs in time slices. The Main CPU would write many bytes to the latch in a single time slice before the Sub CPU had a chance to process any of them, causing "latch written before being read" overflows.

**Fix:** Added `machine().scheduler().perfect_quantum(attotime::from_usec(100))` to `subcpu_latch_w()`. This temporarily forces minimum quantum for tight CPU interleaving, ensuring the Sub CPU's HDMA can process each byte before the next one arrives.

After this fix, "latch written before being read" warnings dropped from 52,815 to just 36.

### Diagnostic Logging

Added comprehensive logging to trace the inter-CPU communication:

- **Latch writes**: Command bytes (E1/E2/E3) logged with PC address; data bytes logged at verbose level
- **Handshake signals**: MSTAT/SSTAT changes logged with old/new values
- **Sub CPU reset**: Port A bit 0 changes logged
- **DMA vectors**: DMAV register writes logged with channel and value
- **DMA transfers**: Each HDMA transfer logged with source, destination, count, and mode
- **DMA completion**: Logged when HDMA transfer count reaches zero

Logging is controlled by `VERBOSE` flags in `kn5000.cpp` and uses MAME's `logmacro.h` system.

## Investigation Log

### Test Run 1: After DMAR fix + diagnostic logging

- E1 handshake works: SubCPU receives E1, arms DMA0V=0x0A, acknowledges
- **Zero HDMA transfers**: No "HDMA ch0 complete" messages in 81,969-line log
- "latch written before being read" warnings: Main CPU bytes overwrite each other
- Root cause identified: LDC instructions for DMA registers silently fail due to wrong CR mapping

### Test Run 2: After LDC CR mapping fix + DMAM encoding fix

- HDMA still showed zero transfers
- Root cause identified: `check_irqs()` consuming INT0 flag before `check_hdma()` could use it

### Test Run 3: After HDMA priority fix + perfect_quantum

- **524,358 HDMA transfers** (up from zero!)
- Only 36 "latch written before being read" warnings (down from 52,815)
- 17 HDMA completions showing correct transfer pattern (9 blocks x ~2 completions each for header + data)
- All 9 E1 blocks transferred successfully
- **SubCPU payload executes!** PC values 0x01F929, 0x034C6F observed after payload load
- SubCPU initializes serial ports, configures interrupts from within payload code
- "Checking device" LED stops blinking (SubCPU left boot ROM polling loop)

### Test Run 4: After DMAR burst DMA fix + INT0 level-detect re-assertion (545K line log)

- **0 INT0 dispatches** -- the level-detect re-assertion was not yet active in this test
- 524,374 HDMA transfers (payload loading phase works)
- SubCPU goes silent after tone generator init -- no INT0 interrupts fire post-boot
- 36 latch overflow warnings
- "Sound Name Error" persists
- **Theory confirmed:** Without level-detect re-assertion, INT0 fires once (consumed by HDMA during boot) but never again after the payload sets DMA0V=0 and expects ISR-based INT0 handling

### Test Run 5: After INT0 level-detect re-assertion fix (3M line log)

- **394,118 INT0 dispatches** (up from 0!) -- level-detect re-assertion IS working
- 524,374 INT0 ASSERT events
- **INT0 storm detected:** 91,391 INT0 dispatches from PC=`0x01FFF0` (the NOP between `EI 0` and `EI 6`)
- Only 5 latch overflow warnings (down from 36)
- Last HDMA ch0 complete at dst=`0x0010F1` (payload's own HDMA setup)
- After that, INT0 storm begins and SubCPU is trapped in infinite ISR dispatch loop
- Blinking patterns of the SubCPU checking device slightly different vs previous test
- "Sound Name Error" still present
- **Root cause identified:** Missing interrupt shadow after RETI allows INT0 to re-dispatch before the return-address instruction executes, preventing the `EI 0; NOP; EI 6` masking pattern from working. See Fix 8.

### Test Run 6: After EI/RETI interrupt shadow fix (14.8M line log)

- **EI/RETI shadow fix WORKED:** 0 INT0 dispatches from PC=`0x01FFF0` (old storm at boot ROM window eliminated)
- **NEW INT0 storm emerged:** 12,203,435 INT0 dispatches (82% of all log lines), mostly from DSP_SEND_DATA loop (PCs `0x036828`-`0x03685E`)
- 524,353 INT0 ASSERT / 524,354 CLEAR events → ~23 dispatches per ASSERT (level-detect amplification)
- 22,719 INT0 dispatches from PC=`0x01FFF1` (EI 6 address) — these are the correctly-working EI windows
- INTTC0 = 18 (payload DMA completions), **INTTC2 = 0** (SubCPU never sends data back)
- 14 latch overflow warnings (in two clusters: post-boot + E2 command attempt)
- Only 38 INTA + 82 INTRX1 + 157 INTTX1 on MainCPU (very little MainCPU activity)
- Payload loading succeeded (all 9 E1 blocks, 524K HDMA transfers)
- SubCPU payload booted (SSTAT 0→3 at PC=`0x01F986`)
- **SubCPU stuck in `DSP_Send_Data` timeout loop** — DSP not emulated, `DSP_Read_Status` returns 0

**Root cause chain identified:**
1. `DSP_Read_Status` reads Port PH bit 0, which returns 0 (DSP "not ready") because `port_r()` ignores the direction register
2. PH.0 is configured as OUTPUT (PHCR=0x07), so reading should return the output latch (1, set by `SET 0, (PH)`)
3. The SubCPU's DSP init has ~40 `DSP_Send_Data` calls, each with an 8000-iteration timeout loop
4. During timeout loops, IFF=0 (EI 0 in the function), so INT0 fires on every instruction
5. The INT0 ISR checks MSTAT0=1 (MainCPU in data phase), exits without reading the latch
6. Level-detect re-assertion causes INT0 to fire 23x per assertion, creating massive overhead
7. The MainCPU's E2 command handshake check passes spuriously (SSTAT1 already 0 from a previous transfer, not from SubCPU acknowledgment)
8. MainCPU sets MSTAT0=1 and starts sending data before SubCPU reads the command byte
9. All data bytes overflow the latch (written before being read)

### Test Run 7: After port_r direction-aware fix (2.7M line partial log — interrupted early)

- Fix 9 applied: `port_r()` now returns `(latch & dir) | (external & ~dir)` — output bits from latch, input bits from external callback
- **INT0 dispatches: 113,017** (down from 12.2M — 99% reduction)
- **Latch overflow: 0** (down from 14)
- **INTTC0 dispatches: 0** (DMA ch0 completion never fired — transfer in progress or not yet started)
- **INTTC2 dispatches: 0** (SubCPU never sent data back — still initializing)
- **MSTAT values changed: 2↔3** (previously 0↔1 — CORRECT, see analysis below)
- **Top INT0 PCs:** 0x034C6F (7460x = DSP_System_Init memory clearing loop), 0xFFFEC0-D1 (~1023x each = boot ROM debug utilities)
- Log was interrupted before GUI loaded because file was growing too fast

**Analysis of MSTAT 2↔3 behavior:**
The port_r fix affects BOTH Port D (PDCR=0x63: bits 0-1=output) AND Port Z (PZCR=0x03: bits 0-1=output). Previously, SET/RES operations on these ports would lose other output bits during read-modify-write because port_r returned all-external-callback. Now output bits correctly preserve from the latch:
- Old: `SET 0, (PZ)` + `SET 1, (PZ)` → MSTAT = 2 (bit 0 lost because SET 1 read PZ with bit 0 = 0)
- New: `SET 0, (PZ)` + `SET 1, (PZ)` → MSTAT = 3 (bit 0 preserved from latch)
- This is correct real hardware behavior — PZCR=0x03 is set during boot init (`LD (PZCR), 003h` in `shared/boot_hw_init.asm`)

**Key finding: SubCPU still initializing.** The 7460 INT0 hits at 0x034C6F exactly match the `DSP_System_Init_Clear2_Loop` iteration count (clearing a 7,462-byte DSP state buffer). The boot ROM debug routine hits (~1023x at `DEBUG_OUTPUT_CHAR_STUB`, 0xFFFEC1) are the payload calling boot ROM utility functions for diagnostic output. Both are normal initialization activity — the SubCPU hasn't reached the main event loop yet.

### Test Run 8: After logging reduction (superseded — Fixes 10-12 resolved the error)

- Reduced INT0 dispatch logging to every 1000th occurrence
- Reduced HDMA per-transfer logging to every 256th transfer
- Expected: log small enough for full boot completion, allowing us to determine if Sound Name Error persists

## Fixes Applied (continued)

### Fix 6: DMAR Software-Triggered Burst DMA

Analysis of the SubCPU payload's main loop revealed that `InterCPU_DMA_SendDataPacket` (at `0x020CB0`) uses the `DMAR` register to trigger DMA channel 2 for sending data back to the Main CPU. After triggering, it waits in `DMA_Chunk_Wait` for `DMA_XFER_STATE` to be cleared by the `MICRODMA_CH2_HANDLER` interrupt (INTTC2 at vector `0x9C`).

**Bug:** The previous `dmar_w()` implementation called `process_hdma()`, which requires a matching interrupt flag to be pending. Software-triggered DMA via DMAR should bypass the interrupt check and perform a burst transfer (all DMAC units at once), then fire INTTC on completion.

**Fix:** Replaced `dmar_w()` to call a new `tlcs900_process_software_dma()` function that transfers the entire block without checking interrupt flags and fires the INTTC completion interrupt when done.

Without this fix, every attempt by the SubCPU to send data back to the Main CPU would silently fail, and the `DMA_Chunk_Wait` loop would hang forever.

### Fix 7: INT0 Level-Detect Re-assertion

**Root cause:** On real TMP94C241 hardware, when IIMC bit 1 = 0 (level-detect mode for INT0), the interrupt flag in INTE0AD is continuously driven by the external input level. MAME's `check_irqs()` clears the flag when dispatching the interrupt, but on real hardware the flag immediately re-asserts if the input pin is still active.

During boot, this doesn't matter because HDMA consumes INT0 (the flag is cleared but HDMA handles the data transfer). After boot, when the SubCPU payload takes over and configures DMA0V=0 (disabling HDMA for INT0), the ISR handles INT0 directly. Without level-detect re-assertion, INT0 fires once but never again -- the SubCPU stops receiving commands from the Main CPU.

**Fix:** Added re-assertion logic in `check_irqs()`: after dispatching an INT0 interrupt and clearing its flag, if INT0 is in level-detect mode and the input is still ASSERT_LINE, immediately re-set the INTE0AD flag and schedule another `check_irqs`. An HDMA guard prevents re-assertion when any DMA channel is configured for INT0's start vector (0x0A), since HDMA manages its own flag lifecycle.

```cpp
// In check_irqs(), after clearing INT0's flag:
if (tmp94c241_irq_vector_map[irq].reg == INTE0AD &&
    tmp94c241_irq_vector_map[irq].iff == 0x08 &&
    !(m_iimc & 0x02) &&
    m_level[TLCS900_INT0] == ASSERT_LINE)
{
    // Skip re-assertion when HDMA is configured for INT0
    bool hdma_steals_int0 = false;
    for (int ch = 0; ch < 4; ch++)
        if (m_dma_vector[ch] == 0x0a)
            hdma_steals_int0 = true;
    if (!hdma_steals_int0)
    {
        m_int_reg[INTE0AD] |= 0x08;
        m_check_irqs = 1;
    }
}
```

**Note:** This re-assertion relies on `m_level[INT0]` being accurate. See Fix 12 for the stale `m_level` problem this creates and the solution.

### Fix 8: EI/RETI Interrupt Shadow

**Root cause of INT0 storm:** Fix 7 exposed a second bug. The SubCPU payload uses a deliberate `EI 0; NOP; EI 6` pattern at address `0x01FFEE`-`0x01FFF1` to create a one-instruction interrupt window:

```asm
EI 0    ; 01FFEE - Enable all interrupts (IFF=0)
NOP     ; 01FFF0 - One-instruction window for pending interrupts
EI 6    ; 01FFF1 - Re-mask low-priority interrupts (IFF=6)
```

On real TLCS-900 hardware, both EI and RETI defer interrupt acceptance until after the next instruction executes (a "1-instruction interrupt shadow"). This means:
1. `EI 0` enables interrupts, but the CPU executes NOP before accepting any
2. INT0 dispatches from `0x01FFF1` (the address of `EI 6`)
3. ISR handles INT0, returns via RETI
4. RETI has its own shadow -- `EI 6` executes before another INT0 can fire
5. IFF is now 6, masking INT0 (priority 1) -- storm prevented

In MAME, `check_irqs()` runs at the START of the execution loop, BEFORE the instruction executes. After RETI restores IFF=0, `check_irqs` fires before the return-address instruction (NOP) gets a chance to execute. The ISR checks MSTAT0=1, exits without reading the latch, RETI returns to 01FFF0, and INT0 re-dispatches immediately -- an infinite storm of 91,391+ INT0 dispatches in the log.

**Fix:** Added `m_irq_inhibit` flag to the TLCS900 base class. Both `op_EI()` and `op_RETI()` set this flag. In `execute_run()`, when `m_irq_inhibit` is set, interrupt checking is deferred by one instruction:

```cpp
// In execute_run():
if ( m_check_irqs )
{
    if ( m_irq_inhibit )
    {
        // Interrupt shadow: defer until after next instruction
        m_irq_inhibit = false;
    }
    else
    {
        tlcs900_check_irqs();
        m_check_irqs = 0;
    }
}
```

**Files modified:**
- `mame_driver/src/devices/cpu/tlcs900/tlcs900.h` -- Added `bool m_irq_inhibit` member
- `mame_driver/src/devices/cpu/tlcs900/tlcs900.cpp` -- Shadow logic in `execute_run()`, init in `device_start()`/`device_reset()`
- `mame_driver/src/devices/cpu/tlcs900/900tbl.hxx` -- Set `m_irq_inhibit = true` in `op_EI()` and `op_RETI()`

### Fix 9: Port Read Direction Awareness

**Root cause of DSP timeout loops:** The `port_r()` function in `tmp94c241.cpp` always returns the external callback value, ignoring the port direction register (PXCR). On real TMP94C241 hardware, reading a port returns:
- Output latch value for bits configured as output (PXCR bit = 1)
- External pin level for bits configured as input (PXCR bit = 0)

The SubCPU firmware configures Port PH bits 0-2 as output (`LD (PHCR), 007h`). The `DSP_Read_Status` function at `0x0383F7` does `SET 0, (PH)` then reads back PH.0 to check DSP ready status. Since PH.0 is output, the read should return 1 (what was just written). But MAME's `port_r()` called the external callback (unconnected for Port PH), returning 0.

This caused all `DSP_Send_Data` and `DSP_Send_Command` calls to enter their timeout loops (0x1F40 = 8000 iterations each), severely delaying SubCPU initialization. During these long timeouts, INT0 level-detect re-assertion created a massive interrupt storm (12M+ dispatches).

**Fix:** Made `port_r()` direction-aware:

```cpp
uint8_t dir = m_port_control[P];
uint8_t external = m_port_read[P](0);
return (m_port_latch[P] & dir) | (external & ~dir);
```

This fix improves ALL port reads:
- **Port PH** (SubCPU): DSP status reads back output latch → DSP init completes instantly
- **Port D** (SubCPU): SSTAT output bits read back from latch; MSTAT input bits from callback
- **Port Z** (MainCPU): MSTAT output bits read back from latch; SSTAT input bits from callback

**Files modified:**
- `mame_driver/src/devices/cpu/tlcs900/tmp94c241.cpp` -- `port_r()` direction-aware implementation

### SubCPU Initialization Analysis

Detailed analysis of the SubCPU payload init sequence revealed that **initialization does NOT hang** -- all init-phase loops are bounded by timeouts or complete harmlessly with unmapped hardware returning 0:

| Loop                    | Location | Reads From           | Bounded?          | Behavior with Unmapped HW                         |
|-------------------------|----------|----------------------|-------------------|---------------------------------------------------|
| `DSP_Send_Command` wait | 0x036331 | Port PH bit 0        | Yes (8,000 iter)  | PH output latch reads back 1 -- exits immediately |
| `DSP_Send_Data` wait    | 0x0367EE | Port PH bit 0        | Yes (8,000 iter)  | Same as above                                     |
| `ToneGen_Poll_Delay`    | 0x03D227 | Nothing (pure delay) | Yes (10,000 iter) | Runs 160,000 iterations total, completes          |
| `ToneGen_Poll_Read`     | 0x03D230 | 0x110002 / 0x110000  | Single read       | Returns 0, processes 16 fake note-off events      |

After init, the SubCPU enters the main event loop (`Audio_Main_Loop`), which runs continuously. The main loop does NOT hang because:
- `ToneGen_Process_Notes` reads 0 from unmapped 0x110002 (no notes available)
- Ring buffers are empty (no serial data, no queued commands)
- No DMA transfers are triggered on the first iterations

### Fix 10: DMAR Single-Unit Transfer (Critical — Final Fix)

**Root cause of corrupted DMA destinations and the "Sound Name Error":** The main CPU's INT0 handler writes `LD (DMAR), 001h` once per INT0 to transfer a single byte from the inter-CPU latch. Our software DMA implementation burst-transferred ALL remaining bytes at once, reading the same latch value repeatedly.

The E1 protocol header is 6 bytes (4-byte destination + 2-byte count). With burst DMA, the first INT0 would read the same latch byte 6 times, filling the header with garbage (e.g., 0x64646464). The INTTC0 handler then used this garbage as the DMA destination for the bulk transfer, writing all subsequent data to unmapped memory.

**Fix:** Changed `tlcs900_process_software_dma()` to transfer ONE unit per DMAR write (matching HDMA behavior), with INTTC fired only when the count reaches zero. Each INT0 delivers one byte, DMAR transfers one byte, and the count decrements by one.

### Fix 11: SubCPU Peripheral Stubs

The SubCPU payload's main loop polls several unmapped hardware devices, generating millions of MAME "unmapped memory" warnings that flooded the log (500MB+) and severely degraded emulation speed.

**Fix:** Added `noprw` stubs in the SubCPU memory map:

| Address           | Device                                  | Chip                 |
|-------------------|-----------------------------------------|----------------------|
| 0x100000-0x100003 | Tone generator register interface       | IC303 (TC183C230002) |
| 0x110000-0x110003 | Tone generator keybed event data/status | IC303                |
| 0x130000-0x130003 | DSP1 registers                          | IC311                |
| 0x1E0000-0x1EFFFF | Waveform/sample RAM                     |                      |

### Fix 12: INT0 Stale m_level Fix (clear_int0_level)

> **Superseded in the overlay (2026-08-05).** kn7000_mame commit `3fd44f3` later removed Fix 7's /INT0 level re-assertion altogether: it had changed the outcome only twice in 59,300 latch bytes, and both times as a duplicate, nested dispatch of the main CPU's non-reentrant receive ISR. `clear_int0_level()` is still called from both latch-read handlers, and with no re-assertion the latch writes, INT0 dispatches and latch reads are 1:1:1. Mainline MAME keeps the re-assertion (guarded against micro-DMA, #15003/#15878) and has no `clear_int0_level()`. This section records the February 2026 state.

**Root cause of boot timeout regression:** Fix 7's re-assertion logic checks `m_level[INT0] == ASSERT_LINE` to decide whether to re-assert the interrupt flag. However, `set_input_line(CLEAR_LINE)` in MAME goes through `synchronize()` (see `diexec.cpp:663-691`), which defers the actual `execute_set_input()` call until **after the current timeslice ends**. When the ISR reads the latch, `generic_latch::read()` calls `set_input_line(INT0, CLEAR)`, but `m_level` stays `ASSERT_LINE` until the deferred callback runs.

The re-assertion code in `check_irqs()` runs within the same timeslice and sees stale `m_level`, causing ~20 spurious INT0 firings per latch read. Each spurious ISR reads garbage from the latch, corrupting the command protocol. During boot, this caused the SubCPU to misinterpret the E2 command header and hang waiting for bytes that never arrive.

**Failed first approach:** Removing the re-assertion code entirely (reverting Fix 7) fixed boot but broke button input — both CPUs need re-assertion for processing responses during normal operation.

**Fix:** Added `clear_int0_level()` public method to `tmp94c241_device` that synchronously clears `m_level[TLCS900_INT0]` and the INTE0AD interrupt flag. The driver's latch-read wrappers call this immediately after `generic_latch::read()`:

```cpp
uint8_t kn5000_state::subcpu_latch_r()
{
    uint8_t val = m_subcpu_latch->read();
    m_subcpu->clear_int0_level();  // Bypass deferred synchronize()
    return val;
}
```

This is safe because: (1) same-CPU context — modifying the CPU's own state during its own memory read; (2) idempotent — the deferred callback becomes a no-op since m_level is already CLEAR; (3) re-assertion preserved — `check_irqs()` now checks the *correct* m_level; (4) new ASSERT works normally through the deferred path.

**Files modified:**
- `src/devices/cpu/tlcs900/tmp94c241.h` — `clear_int0_level()` declaration
- `src/devices/cpu/tlcs900/tmp94c241.cpp` — `clear_int0_level()` implementation
- `src/mame/matsushita/kn5000.cpp` — Call from `subcpu_latch_r()` and `maincpu_latch_r()`

### "Sound Name Error" Root Cause (Resolved)

The "Sound Name Error" was triggered by the Main CPU's `MainGetSoundName()` function (at `0xF98CAE`). It sends a sound name request to the SubCPU via the inter-CPU latch, then waits for a 32-byte response with a timeout of ~60,000 iterations. When the SubCPU never responds, the timeout fires and displays the error.

**All contributing factors have been fixed:**

1. **LDC CR mapping (Fix 1):** DMA config registers weren't being set due to wrong control register numbers
2. **DMAM encoding (Fix 2):** DMA mode bits were decoded incorrectly
3. **DMAR register (Fix 3):** Software DMA trigger wasn't mapped at all
4. **HDMA priority (Fix 4):** DMA wasn't firing — IRQ handler consumed the interrupt first
5. **CPU scheduling (Fix 5):** SubCPU wasn't getting enough cycles
6. **DMAR burst DMA (Fix 6):** SubCPU response DMA silently failed without burst support
7. **INT0 level-detect (Fix 7):** After boot, INT0 fired once and never again
8. **EI/RETI interrupt shadow (Fix 8):** INT0 storm trapped SubCPU in infinite ISR loop
9. **Port read direction (Fix 9):** Output bits read as 0, breaking DSP status and MSTAT/SSTAT handshake
10. **DMAR single-unit (Fix 10):** Main CPU received garbage headers due to burst-reading same latch byte
11. **Peripheral stubs (Fix 11):** Unmapped hardware warnings flooded the log
12. **INT0 stale m_level (Fix 12):** Fix 7's re-assertion checked stale m_level due to deferred synchronize(), causing ~20 spurious ISR firings per latch read

**As of 2026-02-17, the "Sound Name Error" is GONE and boot completes without timeout.** The display shows voice names, rhythm patterns, mixer levels, and menu navigation works correctly. Button input is also functional (both CPUs' INT0 re-assertion paths work correctly).

## Debugging Inner Thoughts

This section captures the detailed reasoning process behind each investigation step, preserving the "how we got there" alongside the results.

### Reasoning: INT0 Level-Detect Re-assertion (Fix 7)

**Starting observation:** After applying DMAR burst DMA fix, log showed 0 INT0 dispatches post-boot. The payload loaded fine (524K HDMA transfers) but then the SubCPU went completely silent.

**Key insight chain:**
1. During boot, INT0 is consumed by HDMA (DMA0V=0x0A). After boot, the payload calls `InterCPU_Latch_Setup` which sets DMA0V=0x0A for receive and DMA2V for transmit -- but later the main loop's INT0 handler at `0x01F929` processes INT0 via ISR, NOT HDMA. When does DMA0V become 0?
2. Searched the payload code: `InterCPU_Latch_Setup` (line 10964) sets `LDC DMA0V, 000Ah` -- armed for HDMA. But the INT0 handler at line 11247 checks MSTAT0 and if conditions are right, reads the latch byte directly. This means DMA0V stays armed for HDMA throughout, and the HDMA path handles most bytes, but the ISR handles command bytes.
3. Wait -- if HDMA handles INT0, `check_hdma` processes it and clears the flag. But `check_irqs` re-assertion only fires when check_irqs dispatches INT0 to the ISR. In HDMA mode, `check_hdma` clears the flag and... does the level-detect re-assertion fire?
4. **Root cause found:** `check_hdma` calls `process_hdma` which clears the INT0 flag at line 1106. But there's no re-assertion logic in `check_hdma` -- only in `check_irqs`. Since the latch is still pending (ASSERT_LINE), the flag should re-assert. But `execute_set_input`'s `update_int_reg` lambda only updates on level CHANGE (`if (level != m_level[input])`). Since the latch read triggers synchronous CLEAR followed by deferred ASSERT via `synchronize()`, the level does toggle -- but the ASSERT arrives as a callback AFTER the current instruction.
5. The real issue is simpler: when `check_irqs` dispatches INT0, it clears the flag. On real hardware, level-detect means the flag stays set as long as the input is asserted. We need to re-assert immediately after clearing.

### Reasoning: EI/RETI Interrupt Shadow (Fix 8)

**Starting observation:** After Fix 7, log exploded to 3M lines with 394K INT0 dispatches. 91K of them were from PC=`0x01FFF0` -- an INT0 storm.

**Key insight chain:**
1. What's at `0x01FFF0`? It's a NOP instruction, sandwiched between `EI 0` (01FFEE) and `EI 6` (01FFF1). This is a deliberate pattern: enable all interrupts for exactly one instruction, then re-mask.
2. Why does INT0 keep dispatching from `0x01FFF0` instead of letting NOP execute and reaching EI 6?
3. Checked `execute_run()` flow: `check_irqs` runs at the START of the loop, BEFORE instruction execution. After RETI restores SR (with IFF=0), the next loop iteration runs `check_irqs` BEFORE executing the instruction at the return address.
4. So the flow is: `RETI` → returns to `0x01FFF0` → loop starts → `check_irqs` fires (IFF=0, INT0 pending) → dispatches INT0 from `0x01FFF0` → NOP never executes!
5. The ISR at this point checks MSTAT0 (PD bit 2). If MSTAT0=1, it exits without reading the latch (because the Main CPU is in the middle of a transfer phase). The latch stays pending, INT0 re-asserts (Fix 7), RETI returns to `0x01FFF0`, and the cycle repeats.
6. **On real TLCS-900 hardware:** After RETI (and after EI), the CPU executes at least one instruction before accepting another interrupt. This is the "interrupt shadow" -- identical to the Z80's behavior after EI. The NOP absorbs one ISR call, then EI 6 at `0x01FFF1` raises IFF to 6, masking INT0 (priority 1).
7. Checked `op_RETI` in `900tbl.hxx`: it sets `m_prefetch_clear = true` and `m_check_irqs = 1` but has NO interrupt shadow mechanism.
8. **Fix:** Add `m_irq_inhibit` flag, set by EI and RETI, that causes `execute_run` to skip one `check_irqs` call.

### Reasoning: Port Read Direction & DSP Timeout (Fix 9)

**Starting observation:** Test Run 6 showed the EI/RETI shadow fix worked (0 dispatches from PC=01FFF0), but a NEW INT0 storm emerged from DSP_SEND_DATA loop PCs. 12.2M INT0 dispatches with only 524K ASSERTs = 23x amplification.

**Key insight chain:**
1. The storm PCs (0x036828-0x03685E) are in `DSP_Send_Data_WaitLoop` and `DSP_Send_Data_Poll` — a bounded timeout loop (8000 iterations) that polls DSP readiness via `DSP_Read_Status`.
2. `DSP_Read_Status` at 0x0383F7 does: `SET 0, (PH)` → `LDCF 0, (PH)` → return carry. It sets PH.0 high, then reads it back.
3. The SubCPU firmware sets `PHCR = 0x07` (line 9318) — Port PH bits 0-2 are OUTPUT.
4. On real hardware, reading an output bit returns the output latch. Since `SET 0, (PH)` just wrote 1, the read should return 1 (DSP "ready").
5. But MAME's `port_r()` calls `m_port_read[P](0)` — the external callback. Port PH has no callback → returns 0.
6. So `DSP_Read_Status` always returns 0 (not ready), causing 8000-iteration timeouts.
7. `DSP_Send_Data` has `EI 0` / `EI 6` windowing — IFF=0 during the timeout loop body.
8. With level-detect re-assertion, every pending latch byte causes INT0 to fire ~23 times per assertion (ISR checks MSTAT0=1, exits without reading, INT0 re-fires).
9. The E2 handshake protocol race: MainCPU checks SSTAT1=0 (already low from a previous handshake), proceeds to set MSTAT0=1 before SubCPU reads the command.

**The fix** is fundamental: make `port_r()` respect the direction register, combining output latch for output bits and external callback for input bits. This is correct for ALL ports, not just PH.

### Reasoning: MSTAT 2↔3 and PZCR Configuration (Test Run 7 Analysis)

**Starting observation:** Test Run 7 showed MSTAT values 2↔3 instead of the previous 0↔1. Is the handshake broken?

**Key insight chain:**
1. Checked `COM_SELECT` ioport default: 0xE0 = bits 0-1 are ZERO. com_select doesn't bleed into MSTAT.
2. Searched MainCPU firmware for MSTAT usage: `SET 0, (PZ)` / `RES 0, (PZ)` for MSTAT0 AND `SET 1, (PZ)` / `RES 1, (PZ)` for MSTAT1. Both MSTAT bits are actively used in the protocol.
3. Critical discovery: `LD (PZCR), 003h` exists in `shared/boot_hw_init.asm` — the MainCPU configures PZ bits 0-1 as OUTPUT during boot. Similarly, `LD (PDCR), 063h` configures PD bits 0-1 as OUTPUT on SubCPU.
4. With port_r fix + PZCR=0x03: `SET 0, (PZ)` reads PZ → bits 0-1 from latch (preserving MSTAT), bits 2-7 from callback. This is CORRECT — on real hardware output bits read back from the latch.
5. Without port_r fix: `SET 1, (PZ)` reads PZ → bit 0 from callback (=0), losing the previously-written MSTAT0. This is WRONG.
6. **Conclusion:** MSTAT 2↔3 means MSTAT1 is set (signaling "transfer complete") and MSTAT0 is toggling. This is correct protocol behavior that was masked before because SET/RES clobbered the other bit.

**Verified DMA ch2 infrastructure:** The SubCPU's `InterCPU_DMA_SendDataPacket` configures DMA ch2 with Timer 2 triggering (DMA2V=0x16, T23MOD=0x1D with T1 clock, TREG2=0x14). Timer 2 fires INTT2 every 2560 cycles (128µs), each triggering one HDMA byte transfer from RAM to maincpu latch. INTTC2 fires on completion, dispatching to `MICRODMA_CH2_HANDLER` at 0x020F01. All infrastructure is correctly implemented — INTTC2=0 simply means the SubCPU hasn't reached `InterCPU_DMA_Send` yet during the interrupted test.

### DMA Macro Name Confusion (Side Investigation)

During the INT0 investigation, discovered that several DMA macros in `tmp94c241.inc` had misleading names:
- `LDC_DMAM0_WA` (bytes D8,2E,40) actually writes to CR 0x40 = DMAC0 (count register, NOT mode)
- `LDC_DMAC0_A` (bytes C9,2E,42) actually writes to CR 0x42 = DMAM0 (mode register, NOT count)

The names had DMAC and DMAM swapped. Fixed in commit b4ed825 -- all macros now correctly named, duplicates removed, and all call sites updated across all assembly files. Build still produces 100% byte-matching ROMs.

## Key Files

| File | Purpose |
|------|---------|
| `mame_driver/src/mame/matsushita/kn5000.cpp` | Main MAME driver (latches, ports, memory map) |
| `mame_driver/src/devices/cpu/tlcs900/tmp94c241.cpp` | CPU emulation (DMA, SFR, interrupts, INT0 re-assertion) |
| `mame_driver/src/devices/cpu/tlcs900/tmp94c241.h` | CPU header (DMA state) |
| `mame_driver/src/devices/cpu/tlcs900/tlcs900.cpp` | TLCS900 base class (execute_run, interrupt shadow) |
| `mame_driver/src/devices/cpu/tlcs900/tlcs900.h` | TLCS900 base header (m_irq_inhibit) |
| `mame_driver/src/devices/cpu/tlcs900/900tbl.hxx` | Shared instruction decoder (LDC CR, EI/RETI shadow) |
| `mame_driver/src/devices/cpu/tlcs900/dasm900.cpp` | Disassembler (CR label fix) |
| `maincpu/kn5000_v10_program.asm:134123` | `SubCPU_Send_Payload` |
| `maincpu/kn5000_v10_program.asm:139166` | `InterCPU_E1_Bulk_Transfer` |
| `maincpu/kn5000_v10_program.asm:139115` | `Audio_DMA_Transfer` |
| `maincpu/kn5000_v10_program.asm:140484` | LZSS decompressor (`SLIDE_Parse_Header`) |
| `subcpu/kn5000_subprogram_v142.asm:10964` | `InterCPU_Latch_Setup` (payload DMA config) |
| `subcpu/kn5000_subprogram_v142.asm:11247` | Payload INT0 handler |
| `subcpu/boot/kn5000_subcpu_boot.asm:1159` | `InterCPU_RX_Handler` (boot ROM INT0 handler) |
| `subcpu/boot/kn5000_subcpu_boot.asm:718` | `INIT_DMA_SERIAL` (DMA setup) |
| `subcpu/boot/kn5000_subcpu_boot.asm:405` | Main loop (payload ready polling) |

> **Path note.** The `.asm` filenames and line numbers above are from the 2026-02
> investigation. The disassembly has since moved to per-module `.s` files and the line
> numbers no longer resolve. Current equivalents: `v10/maincpu/` (main CPU),
> `v142/subcpu/kn5000_subprogram_v142.s` (payload code),
> `v142/subcpu/subcpu_data_tables.s` (the three data zones described above),
> `subcpu/boot/kn5000_subcpu_boot.s` (boot ROM), and `table_data/tone_database_*.s`
> (the `0x830000` region). Symbol addresses are in `symbols/subcpu_symbols_reference.txt`
> (payload) and `symbols/subcpu_boot_symbols_reference.txt` (boot ROM).
