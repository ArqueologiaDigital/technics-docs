---
layout: page
title: DSP Bytecode Interpreter
permalink: /dsp-bytecode-interpreter/
---

# DSP Bytecode Interpreter

The KN5000's dual DSP chips (IC310 MN19413 and IC311 NEC uPD6383GF) are programmed via a two-level bytecode interpreter running on the SubCPU. This page documents the interpreter architecture, opcodes, and register write protocol.

> **Status:** Architecture and opcode tables decoded from SubCPU firmware. The programs
> themselves — every bytecode stream and parameter record for all 100 effect numbers — are
> now carved and labelled in the disassembly (the August 2026 binary-include-elimination
> Wave 3a, 2026-08-07). Register-to-effect
> parameter mapping is still incomplete: eight translator opcodes have measured semantics,
> the rest are named from their code shape only.

> **Note:** This page predates the identification of IC311. It formerly called the chip
> "DS3613GF-3BA, a custom ASIC" — that was a transcription error; the part is the **NEC
> uPD6383GF-3BA**. Everything below about the *SubCPU-side* interpreter remains valid; for
> the DSP chip's own architecture, instruction word, decoded algorithms and the full
> effect/parameter catalogue, see the newer
> [Effects DSP (NEC uPD6383GF)]({{ site.baseurl }}/effects-dsp/) page.

> **The programs this interpreter runs now have their own page.** The bytecode streams and
> parameter record tables live in a 39,372-byte zone at Sub-CPU `0x0147B3`-`0x01E17E`,
> carved block-by-block in 2026-08. Both stream grammars, the four 100-entry pointer
> arrays and a per-effect address table are documented in
> [DSP Effect Data Zone (Sub-CPU ROM)]({{ site.baseurl }}/dsp-effect-data-zone/).
> Addresses on the present page were re-checked against that carve; the corrections are
> marked inline.

## Architecture

The interpreter has two levels:

### Level 1 — Low-level Bytecode Interpreter

- **Entry:** `DSP_BytecodeInterpreter_Init` (`0x03C259`); loop body
  `DSP_BytecodeInterpreter_Loop` (`0x03C2CB`)
- **Called by:** `DSP_WriteGlobalConfig` (`0x03C181`) and `DSP_WriteEFFConfig` (`0x03C161`)
- **Programs:** the effect data zone at `0x0147B3`-`0x01E17E`, part of the Sub CPU payload
  image the Main CPU ships at boot — so they are in Sub CPU RAM at run time, but they are
  ROM content and are fully carved in the disassembly
- **Format:** 2-byte header per instruction — high nibble of `b0` = opcode, and the
  remaining 12 bits `((b0 & 0x0F) << 8) | b1` are the **total instruction length in bytes,
  header included** (a big-endian 12-bit count, not an element count)

### Level 2 — Translator (Parameter Descriptor Engine)

- **Entry:** `DSP_Translator_ReadOpcode` (`0x03CB18`); per-parameter walker
  `DSP_PerParameterTranslator` (`0x03CAAE`)
- **Called by:** `DSP_ParameterWriteEngine` (`0x03C9E6`)
- **Programs:** parameter **value** records and **descriptor** records, both in the same
  Sub CPU effect data zone. `DSP_WriteParam_Generic` (`0x03C20E`) fetches them from the two
  100-entry `u32` arrays at `0x01F22C` (descriptors) and `0x01F09C` (values) — *corrected
  2026-08*: an earlier revision of this page sourced them from the main-CPU table at
  `0xEE75F6`; that table is a separate main-CPU-side table (its first
  entries are `u32` pointers into `0xEE64DA`-`0xEE69E8`, i.e. main-CPU program ROM) and is
  not this engine's program source. It is now labelled `DspFxRecListPtrTable`: 100 pointers,
  by effect number, to the main CPU's parameter-write record lists `DspFxRecs_NN_<Effect>`,
  which pair with this engine's value tables effect for effect — see
  [DSP Effect Data Zone]({{ site.baseurl }}/dsp-effect-data-zone/#the-main-cpu-holds-the-same-metadata-and-reads-it)
- **Format:** records `[len_hi, len_lo, id, payload…]`, big-endian length covering the whole
  record, `0xF0` as the end-of-table sentinel. Inside a value record the `id` byte is
  dispatched as an opcode, then `{ id, field-index, operands }` repeat until `0x7A`

### Dispatch Router

`DSP_DispatchCommand(wa=cmd_byte, bc=chip_id)` (`0x036A2E`) routes to DSP1 (chip=0, IC311,
parallel bus) or DSP2 (chip=1, IC310, SPI serial). `DSP_DispatchData` (`0x036A4F`) similarly
routes data bytes.

The chip id is not passed down from the caller — it is looked up per **effect slot** in the
5-byte table at Sub-CPU `0x01ED6D`, whose contents are `00 00 01 01 01`: slots 0-1 are IC311,
slots 2-4 are IC310. `DSP_WriteEFFConfig`, `EFF_Disconnect` and the parameter-write front
door all do the same `byte(0x01ED6D + slot)` fetch.

## Level 1 Opcodes (Low-level)

| Opcode | Handler                                | Description                                                                             |
|--------|----------------------------------------|-----------------------------------------------------------------------------------------|
| 0x0N   | Handler 0                              | CMD + preamble + groups-of-5 (3-way branch: 0x00=static, 0x0A=raw, else=param-modified) |
| 0x1N   | Handler 1                              | CMD + preamble + groups-of-5 (12-bit address computation)                               |
| 0x2N   | Handler 2                              | CMD + preamble + groups-of-3 (pure raw data writes)                                     |
| 0x3N   | Handler 3                              | CMD + 16-bit address + raw tail                                                         |
| 0x4N   | Handler 4                              | Single command byte only                                                                |
| 0x5N   | Handler 5                              | CMD + preamble + groups-of-5 (variant with IZH mask)                                    |
| 0xDN   | Op0D (`DSP_Bytecode_Op0D_StateChange`) | SPI bus idle + state change notification                                                |
| 0xEN   | Op0E (`DSP_Bytecode_Op0E_SendCommand`) | DispatchCommand + DispatchData loop (register write)                                    |
| 0xFN   | End                                    | Terminate program                                                                       |

Opcodes `0x6`-`0xC` are consumed and ignored. Termination is by **peek**: the stream ends
when the *next* byte's high nibble is `0xF`, so the `0xF0` terminator is not executed.

Handler dispatch table: `DSP_BytecodeInterpreter_CaseOffsets` at `0x014739` — 6 signed `u16` offsets relative to
base `0x03C32E`, decoding to handlers at `0x03C32E`, `0x03C568`, `0x03C661`, `0x03C708`,
`0x03C7A1`, `0x03C7BB`. Handler code: 1,613 bytes of TLCS-900 code at `0x03C32E`-`0x03C97A`,
disassembled as instructions since 2026-09-02 (named as six handlers on 2026-09-25).
The six handlers are `DSP_Bytecode_Op00_Groups5_ParamMix`, `DSP_Bytecode_Op01_Groups5_Addr12`,
`DSP_Bytecode_Op02_Groups3_Raw`, `DSP_Bytecode_Op03_Addr16_RawTail`,
`DSP_Bytecode_Op04_CommandOnly` and `DSP_Bytecode_Op05_Groups5_Masked`. Opcodes `0xD`/`0xE` go
to `DSP_Bytecode_Op0D_StateChange` and `DSP_Bytecode_Op0E_SendCommand`.

## Level 2 Opcodes (Translator)

| Opcode | Handler                       | Output                  | Purpose                                          |
|--------|-------------------------------|-------------------------|--------------------------------------------------|
| 0x21   | ParamInterp_2Point            | WriteOscParam           | 2-point linear interpolation                     |
| 0x24   | ParamInterp_MultiStep         | WriteOscParam           | Multi-step interpolation                         |
| 0x40   | PanScale_Simple               | WriteOscParam           | Pan position scaling                             |
| 0x61   | ParamFetch_Op61Table          | WriteOscParam           | Table lookup in `DSP_OscParamCurve` (`0x0129A3`) |
| 0x62   | ParamFetch_SingleTable        | WriteOscParam           | Single-table lookup (CURVE_D volume law)         |
| 0x63   | ParamFetch_AlgoTypeTable      | WriteFreqParam_AlgoType | Algorithm-dependent table (A/B/C curve select)   |
| 0x64   | PitchParam_Scale              | WriteFreqParam          | Pitch scaling with freq write                    |
| 0x65   | VolumeParam_Scale             | WriteOscParam           | Volume scaling                                   |
| 0x66   | ParamInterp_2Point            | WriteOscParam           | 2-point interpolation (oscillator)               |
| 0x67   | ParamInterp_FPScale           | WriteOscParam_Offset    | FP scale with offset                             |
| 0x68   | ParamInterp_Div0xB4           | WriteFreqParam          | Frequency interp (divide by 0xB4)                |
| 0x69   | VolumeCurve_FP                | WriteOscParam           | Fixed-point volume curve                         |
| 0x6A   | FreqCurve_FP                  | WriteFreqParam          | Fixed-point frequency curve                      |
| 0x6B   | FreqInterp_2Point             | WriteFreqParam          | 2-point frequency interp                         |
| 0x6C   | ParamInterp_3Point_WithOffset | WriteFreqParam          | 3-point interp with offset                       |
| 0x6D   | ReverbCurve_FP                | WriteOscParam           | Reverb-specific curve                            |
| 0x6E   | ParamInterp_FPComplex         | WriteOscParam           | Complex FP interpolation                         |
| 0x6F   | PanCurve_PiecewiseLin         | WriteOscParam           | Piecewise-linear pan curve                       |
| 0x70   | BiquadCoeff_Compute           | (direct)                | Biquad IIR filter coefficient                    |
| 0x71   | DetuneCurve_SignedFP          | WriteOscParam           | Signed FP detune curve                           |
| 0x72   | BiquadWarp_FP                 | (direct)                | Bilinear transform warping                       |
| 0x73   | ParamInterp_Div0xC6           | WriteOscParam           | Interpolation (divide by 0xC6)                   |
| 0x74   | WriteLUTParamSet              | (direct)                | Lookup table parameter set                       |
| 0x75   | ParamEQ_Curve_FP              | WriteOscParam           | Parametric EQ curve                              |
| 0x76   | SOS_Coeff_Compute             | (direct)                | Second-order section coefficient                 |
| 0x77   | ParamInterp_2Point_B          | WriteOscParam           | 2-point interp variant B                         |
| 0x78   | VolScale_B                    | WriteOscParam           | Volume scaling variant B                         |
| 0x79   | AlgoParam_Decode              | WriteOscParam           | Algorithm parameter decode                       |
| 0x7A   | (end)                         | —                       | Terminate bytecode block                         |
| 0xF0   | (separator)                   | —                       | Separator between parameter slots                |

Translator dispatch table: `DSP_Translator_CaseOffsets` at `0x014745` — 25 signed `u16` offsets relative
to base `0x03CB8E`, indexed by `opcode - 0x61` for opcodes `0x61`-`0x79`. Opcodes `0x21`,
`0x24` and `0x40` are special-cased *before* this table; anything else aborts via
`DSP_Op_Unknown_Error`. Note that opcode `0x79` is a real entry (offset `0x88`, target
`0x03CC16`) — the table covers `0x61`-`0x79`, not `0x61`-`0x78`.

The **measured** semantics of the settled subset are on the
[DSP Effect Data Zone]({{ site.baseurl }}/dsp-effect-data-zone/) page (`0x21` universal tail
level, `0x62` CURVE_D volume law at 1.00 dB/step, `0x68` ms→DRAM words at 44.1 kHz, `0x69`
degrees, `0x70` biquad, `0x72` compressor threshold/ratio). Where that page and the
inferred descriptions in the table above disagree, the measured page wins.

## SPI Protocol (DSP2 Register Writes)

Physical layer: GPIO bit-banging on SubCPU ports.

| Signal | Port | Bit |
|--------|------|-----|
| SDA | Port F (0x3C) | bit 0 |
| SCLK | Port F (0x3C) | bit 2 |
| CS2 | Port E (0x38) | bit 6 |

Each SPI transaction produces **9 SCLK rising edges** (confirmed by `DSP2_Send_Command`, `0x03666B`).

### CMD 0x30 Register Write Sequence

A register write sends 5 SPI transactions:

1. **Command** 0x30 (register write command)
2. **Data** 0x00 (constant preamble byte)
3. **Data** `register_address` (8-bit DSP register)
4. **Data** `value_high` (MSB of 16-bit value)
5. **Data** `value_low` (LSB of 16-bit value)

### Boot-time Writes

| Register | Value | Purpose |
|----------|-------|---------|
| 0xD0 | 0x0000 | Initialization |
| 0xD3 | 0x0000 | Initialization |
| 0x3C | 0x4000 | Configuration |

## Parameter Routing and Algorithm Types

### Parametric EQ (opcode 0x70 = BiquadCoeff_Compute)

The PARAMETRIC EQ (effect 39) runs on IC311, so the CMD 0x30 register writes above do not
apply to it. Its `0x70` descriptor (`DSP_Eff39_Param_Descriptors`, `0x0153AB`) sends the
output of the biquad designer (`DSP_BiquadCoeff_Compute`) to ten IC311 C-RAM cells:

- `0x00`, `0x06`, `0x0C`, `0x12`, `0x18` — the five bands' coefficient blocks, six cells apart;
- `0x64`, `0x68`, `0x6C`, `0x70`, `0x74` — the five bands' state-pointer cells, stride 4.

The designer itself is described on the
[Effects DSP]({{ site.baseurl }}/effects-dsp/#parametric-eq--a-bilinear-transform-biquad-proven-by-construction)
page.

### Effect Algorithm Types

The firmware supports 12 algorithm types (indices 0-11). The August 2026 (Wave 3a) carve of
the sub-CPU data zones turned up the whole supporting table family, all of which agree on that count:

| table                                                                                                                     | address                              | shape                                                                                                    |
|---------------------------------------------------------------------------------------------------------------------------|--------------------------------------|----------------------------------------------------------------------------------------------------------|
| `DSP_AlgoType_Dispatch1_CaseOffsets`                                                                                      | `0x00FB66`                           | 12 × `u16` offsets, base `0x033812` (`DSP_AlgoType_Dispatch1_Arms`)                                      |
| `DSP_AlgoType_Dispatch2_CaseOffsets`                                                                                      | `0x00FB7E`                           | 12 × `u16`, base `0x0339DE`                                                                              |
| `DSP_AlgoType_Dispatch3_CaseOffsets`                                                                                      | `0x00FB96`                           | 12 × `u16`, base `0x033E44`                                                                              |
| `Algo_SubTable_DispatchB_CaseOffsets` / `Algo_SubTable_DispatchC_CaseOffsets` / `Algo_SubTable_Bit15Dispatch_CaseOffsets` | `0x00FBAE` / `0x00FBC0` / `0x00FBD2` | 9 × `u16`, bases `0x0340CC` / `0x0341BE` / `0x03429D`                                                    |
| `DSP_EFFPARAM_APPLY_JUMPTABLE`                                                                                            | `0x00F99B`                           | 12 × `u16`, base `0x02F2D9` (`DSP_EffParam_Apply_T0`, the first arm of `DSP_EffParam_Apply_By_AlgoType`) |
| `DSP_AlgoChannel_SelectorRecords`                                                                                         | `0x010FCE`                           | 12 × 6 bytes — three 2-byte channel pairs per type, `0xFF` = no entry                                    |
| `DSP_AlgoDescriptor_Records`                                                                                              | `0x011E16`                           | 14 × 39-byte (`0x27`) records; types 12 and 13 are all zero                                              |

(The six `*_CaseOffsets` tables were `AlgoJumpTable1`-`AlgoJumpTable6` until September 2026;
each is now named after the dispatcher that reads it,
`scripts/renaming/rename_v142_case_offset_tables.sed`.)

**Correction (2026-08).** An earlier revision of this page said `DSP_WriteEFFConfig` "looks
up the algorithm type from a table at `0x1ED6D[wa]`". It does not: `0x01ED6D` is the 5-byte
**chip-id** table described above (`00 00 01 01 01`, indexed by effect *slot*).
`DSP_WriteEFFConfig` fetches that chip id, then calls
`DSP_BytecodeInterpreter_Init(chip, slot, XDE = 0x014777, bytecode stream)`. `0x014777` is a
run of 12-byte interpreter-frame descriptors indexed by slot (`+0`,`+2`,`+4`,`+6` are copied
into the interpreter frame, `+8` is a long); the disassembly still carries the inherited ELF
label **`ToneGen_WorkArea`** there, which is a misnomer — it is DSP program/parameter data,
not a tone-generator work area. `DSP_WriteGlobalConfig` does the same with the sibling
descriptor table at `0x0147B3` and program index 0.

## Key Functions (SubCPU)

Addresses, not source line numbers — the disassembly moved from `.asm` to `.s` modules and
the old line references were stale. These are the current entries in
`symbols/subcpu_symbols_reference.txt`.

| Function                             | Address    | Purpose                                                                 |
|--------------------------------------|------------|-------------------------------------------------------------------------|
| `DSP_BytecodeInterpreter_Init`       | `0x03C259` | Low-level interpreter entry                                             |
| `DSP_BytecodeInterpreter_Loop`       | `0x03C2CB` | Fetch/decode/dispatch loop                                              |
| `DSP_Bytecode_Op00_Groups5_ParamMix` | `0x03C32E` | Handler 0; first of the six opcode handlers (1,613 bytes to `0x03C97A`) |
| `DSP_Bytecode_NotifyStateChange`     | `0x03C253` | Tail-jumps into the scheduler (yields between register groups)          |
| `DSP_ParameterWriteEngine`           | `0x03C9E6` | Translator entry point                                                  |
| `DSP_PerParameterTranslator`         | `0x03CAAE` | Walks one value record to its `0x7A`                                    |
| `DSP_Translator_ReadOpcode`          | `0x03CB18` | Opcode decode + dispatch                                                |
| `DSP_TableWalk_Search`               | `0x03CF53` | Finds the descriptor record with a given id                             |
| `DSP_TableWalk_SearchWithState`      | `0x03CFA5` | Same, stateful variant                                                  |
| `DSP_DispatchCommand`                | `0x036A2E` | Route command to DSP1/DSP2                                              |
| `DSP_DispatchData`                   | `0x036A4F` | Route data to DSP1/DSP2                                                 |
| `DSP2_Send_Command`                  | `0x03666B` | SPI bit-bang: 9 SCLK rising edges                                       |
| `DSP2_SPI_BusIdle`                   | `0x0364C4` | SPI CS deassert + state change                                          |
| `DSP_WriteGlobalConfig`              | `0x03C181` | Global config via bytecode (descriptor table `0x0147B3`)                |
| `DSP_WriteEFFConfig`                 | `0x03C161` | Effect config via bytecode (descriptor table `0x014777`)                |
| `DSP_WriteParameter`                 | `0x03C190` | "Write parameter set N of effect M" front door                          |
| `DSP_WriteParam_Generic`             | `0x03C20E` | Generic arm: descriptors from `0x01F22C`, values from `0x01F09C`        |
| `DSP_MixerCoeff_Compute`             | `0x03C067` | Two-stage mixer gain via `DSP_MixerGain_Curve`                          |
| `DSP_WriteParamCmd30`                | `0x038439` | CMD 0x30 register write (5 SPI transactions)                            |
| `DSP_WriteOscParam`                  | `0x0387E6` | Write oscillator/effect parameter                                       |
| `DSP_WriteFreqParam`                 | `0x038539` | Write frequency parameter                                               |
| `DSP_Read_Status`                    | `0x0383F7` | Poll DSP1 ready via Port PH bit 0                                       |
| `EFF_Change_WithDebug`               | `0x0380EC` | Uploads algorithm then coefficients for one slot                        |

## Related Pages

- [DSP Effect Data Zone (Sub-CPU ROM)]({{ site.baseurl }}/dsp-effect-data-zone/) — the data this interpreter executes: both grammars, the four pointer arrays, and a per-effect address map for all 100 effect-algorithm numbers
- [Effects DSP (NEC uPD6383GF)]({{ site.baseurl }}/effects-dsp/) — the IC311 DSP chip itself: architecture, instruction word, decoded algorithms, effect/parameter catalogue
- [Audio Subsystem]({{ site.baseurl }}/audio-subsystem/) — Overall audio architecture
- [Tone Generator]({{ site.baseurl }}/tone-generator/) — IC303 wavetable synth
