---
layout: page
title: SX-WSA1R Parameter Records
permalink: /wsa1-parameters/
---

# SX-WSA1R — one parameter-number space on CPU 1

A parameter change on CPU 1 — a MIDI controller arriving, a panel control moving, a
performance setting being written — travels as one **four-byte record**, and the first byte
of that record is a **parameter number** from one shared space. The number names either a
*record* in work RAM (a part, an effect block, the combination name …) or a *MIDI
controller* that applies to many parts at once.

⚠ Not everything goes this way: the tone editor's fields (RESONATOR TYPE, POSITION, DEPTH …)
live in a separate store at RAM `0x27A6` and are committed by `ToneEdit_CommitField` — see
[System Exclusive Messages]({{ site.baseurl }}/sysex-messages/#tone-edit-parameters-use-a-separate-store).

Everything on this page is read from the [SX-WSA1R disassembly]({{ site.baseurl }}/wsa1-disassembly/)
(`wsa1/prom_a/wsa1_prom_a.s`, `wsa1/prom_b/wsa1_prom_b.s` and
`wsa1/prom_c/data_tables/preset_bank.s` in the disassembly repository). The checks that
re-derive each claim from the ROM bytes are named where the claim is made; most live in
`notes/proma-2026-09-25/` (their index is that directory's `README.md`).

## The record

| byte | name in the sources | what it holds |
|---|---|---|
| `+0` | number | the parameter number, `0x00`–`0xBF` (the list runners skip anything above `0xBF`) |
| `+1` | class | for a number that has a RAM record: the **byte offset** of the field inside that record. For the controller numbers `0xB1`–`0xBD`: the **part**, 0–31 |
| `+2` | value | the new value |
| `+3` | mask | which bits of the field the value owns |

`ParamRecord_WriteFieldAndStage` (prom_a `0xFAA623`) is the plainest statement of it: with
C = number, B = offset, E = value and D = mask it looks up the number's record, writes
`(record + B) = (old & ~D) | (E & D)`, and stages the same four bytes `{C, B, E, D}` at RAM
`0x60F080` for publication. The same four bytes are what `List2030_AppendRegs` stores in
the list at RAM `0x2030`, what the queue at RAM `0x2C00` carries, and what the MIDI-in
handlers build at RAM `0x1950`.

## Where records come from, and where they go

```
MIDI IN   a MidiIn_* handler takes the part, reads that part's entry of its ROM table
          ([number][class][mask]) and adds the value  ->  record at RAM 0x1950
          controllers 0xB1..0xBD: MidiIn_ControlRecord_Dispatch loads the number's
          32-bit PART MASK (RAM 0x60F280+) and queues the record once per set bit
          (Queue2C00_FanOutToPartMask), the part in the class byte

PANEL     group queue RAM 0x2000 -> PanelGroupQueue_ExpandToEvents
          (PanelGroupEventLists_Variant1/2, picked by the model strap) -> list RAM 0x2030

LIST      List2030_TranslateToQueue2C00: per record, List2030_LoadRecord copies it to
0x2030    RAM 0x60F080.., then Dispatch_By_60F080[number] is called -> records appended
          to the queue at RAM 0x2C00 (cursor 0x60F000; drained when it reaches 0x1FC)

QUEUE     Queue2C00_DrainPassAB: UiEventList_RunPassA and _RunPassB over 0x2C00,
0x2C00    then 0xFF at 0x2C00 and the cursor zeroed

MIDI OUT  MidiOut_ParamChanged: MidiOut_ParamNumberTable[number] -> the MIDI message
```

The list at `0x2030` holds at most 15 records: `(0x206C − 0x2030) / 4`, the ceiling both
`List2030_AppendRegs` and `PanelGroupQueue_ExpandToEvents` enforce.

Checks: `gen_param_list_headers.py` (M1–M8: the list-to-queue loop, the eleven controller
entries, the part-mask cells, the fan-out loop, the byte-wise queue append) and
`gen_midiin_param_headers.py` (R1–R4: every MIDI-in table's one reader, its `cp A,0x1F`
part bound and its walk into the `0x1950` record).

## The number space

### `0x00`–`0x3F`: the 32 parts, in two halves

Number *n* in `0x00`–`0x1F` is **part *n***, and the class byte chooses the field. Number
`0x20 + n` is the **second half** of the same part's record: `ParamNumber_RecordPtrs` gives
`entry[0x20 + i] = entry[i] + 0x20` for all 32, which is why `Evt2030_ClassHandlers` and
`Dispatch_By_60F080` route the two ranges to different handlers.

The classes of a part parameter, from `MidiOut_ParamClassTable` (17 entries, indexed by
`MidiOut_DispatchByClass`) and the MIDI-in tables that produce them:

| class | field | MIDI-in source |
|---:|---|---|
| 0 | program | program change |
| 1 | bank select, packed (`MidiOut_BankSelect_Packed`) | |
| 3 | volume | CC7 |
| 5 | effect 3 depth | CC93 (`MidiIn_CC5D_ParamTable`) |
| 6 | effect 4 depth | CC94 (`MidiIn_CC5E_ParamTable`) |
| 7 | effect 1 depth | CC91 (`MidiIn_CC5B_ParamTable`) |
| 8 | pan | CC10 (`MidiIn_CC0A_ParamTable`) |
| 9 / 10 / 11 | RPN 2 coarse tune / RPN 1 fine tune / RPN 0 pitch-bend range | data entry, CC6 / CC38 |
| 15 / 16 | bank select LSB / MSB halves | |

Classes 2, 4 and 12–14 go to `MidiIn_NullHandler` on the way out. General-purpose CC81
(`MidiIn_CC51_ParamTable`) writes number `0x20 + part`, class `0x18`, mask `0x01` — a
one-bit field in a part's second half.

**The class is the field's byte offset.** The combination format the
[SysEx reference](#factory-defaults-and-the-combination-memory) documents puts PROGRAM
CHANGE & BANK at A-block `+0x00`, VOLUME at `+0x03` and PANPOT at `+0x08` — classes 0, 3
and 8 above — and `ParamRecord_WriteFieldAndStage` uses the second byte as that offset.

### `0xB1`–`0xBD`: the MIDI controllers, which apply per part

For these numbers the class byte is the **part**, and each number owns a 32-bit **part
mask** in RAM. `MidiIn_ControlRecord_Dispatch` and the `ParamMsg_*` entries of
`Dispatch_By_60F080` load the same cell for each number — two readers of eleven cells — and
fan the record out once per set bit.

| number | controller | part-mask cell |
|---|---|---|
| `0xB1` | pitch bend | `0x60F280` |
| `0xB2` | CC1 modulation | `0x60F284` |
| `0xB3` | CC11 expression | `0x60F2A8` |
| `0xB4` | channel pressure | `0x60F28C` |
| `0xB5` | CC64 hold | `0x60F294` |
| `0xB8` / `0xB9` | CC16 / CC17 (`MidiOut_CC10_RTCreatX` / `MidiOut_CC11_RTCreatY`) | `0x60F298` / `0x60F29C` |
| `0xBA` / `0xBB` | CC18 / CC19 (`MidiOut_CC12_RTCtrlX` / `MidiOut_CC13_RTCtrlY`) | `0x60F2A0` / `0x60F2A4` |
| `0xBC` | CC2 (`MidiOut_CC02_Modulation2`) | `0x60F288` |
| `0xBD` | CC4 (`MidiOut_CC04_CtrlPedal`) | `0x60F290` |
| `0xAD` / `0xAE` | CC121 reset all controllers / CC120 all sound off | — |

The number-to-controller link is pinned twice: the MIDI-in table named for each controller
holds that number in every one of its 32 records, and `MidiOut_ParamNumberTable[number]` is
the MIDI-out handler of the same controller. Two further tables carry numbers `0xB6` and
`0xB7` for every part; **which controllers those are is not established** — no controller
number reaches their handlers, and both go out through `MidiOut_Param_Ignore`.

⚠ Each `ParamMsg_*` entry first tests bit 5 of RAM `0x7F36`, which the MIDI TOTAL MODE
screen draws and edits as **LOCAL TOTAL** (set = `OFF`; `MidiTotalMode_PaintLocalTotal`,
`MidiTotalMode_EditLocalTotal` at prom_a `0xF9A5E5`). What the fan-out skips when it is set
is not traced.

### The rest of the space

`Dispatch_By_60F080` has 256 entries (its reader multiplies by an 8-bit operand); 168 of
them point at the shared one-instruction handler `Dispatch_By_60F080_Nop64`, a lone `ret`.
Beyond the parts and the controllers, thirteen more numbers have entries of their own, and
nine of those are no-ops as well: `0x44`–`0x46` share `Dispatch_By_60F080_Nop68`, and
`0x48`, `0x60`, `0x70`, `0x72`, `0x90`, `0x91` go to `Dispatch_By_60F080_Nop72`,
`Dispatch_By_60F080_Nop96`, `Dispatch_By_60F080_Nop112`, `Dispatch_By_60F080_Nop114`,
`Dispatch_By_60F080_Nop144` and `Dispatch_By_60F080_Nop145` — each of them a one-byte
`ret` stub. So 177 of the 256 numbers do nothing in this dispatcher. **Only four numbers
reach a handler with a body, and three of them are decoded:**

* `0x7A` is the **tempo** (`List2030_Tempo_Dispatch` → `List2030_Tempo_Apply`: record RAM
  `0x7EE2`, whose low 9 bits `Tempo_ApplyBpm` takes as BPM — a value outside 40–300 is
  reset to 120 — and turns into the timer constant it writes to `TREG5`);
* `0x98` is a **combination program change** (`List2030_Param98_Dispatch` →
  `List2030_Param98_ApplyProgram`, record RAM `0x7F02`), the twin of the part
  program-change handler;
* `0xA8` is a pass-through (`List2030_ParamA8_PassThrough`): it queues the value and mask
  unchanged and writes no record;
* what `0xB0` is (`List2030_ParamB0_Dispatch`) stays open.

(The entries are read from the ROM table at prom_a `0xFAC8EA`; the byte at each stub's
address is `0x0E`, `ret`.)

`ParamNumber_RecordPtrs` (prom_a `0xFACDEA`) gives a RAM record to 77 numbers, in
`0x7622`–`0x7F5A`: the 64 part halves and `0x60`–`0x63`, `0x78`–`0x7A`, `0x80`,
`0x91`–`0x93`, `0x98`, `0x99`. `Evt2030_ClassHandlers` gives a handler to 76 numbers; 65
have both, and the eleven with a handler and no record are exactly `0xB1`–`0xB5` and
`0xB8`–`0xBD`. Two tables derived from different parts of the ROM agreeing on that
eleven-element set is what makes both readable. Record `0x80` is RAM `0x7F32`, the byte
whose bit 2 `MIDI_RT_ExternalOff` names.

On the way out, `MidiOut_ParamChanged` bounds the number at `0xBF` and calls
`MidiOut_ParamNumberTable[number]`: 111 of the 192 slots are `MidiOut_Param_Ignore`, so most
parameter changes are not echoed as MIDI.

## The panel's assignable controls send MIDI controller numbers

The assignable panel controls read a byte from RAM `0x7F12 + slot`
(`PanelGroupToRam7F12Slot`, panel groups `0x0B`–`0x17`) and turn it into a parameter number.
That byte **is a MIDI controller number**. The firmware's own byte-to-number map — spelled
twice, in `PanelCtrl_AssignToParamNumber` and inline in `PanelAction_AssignableController`
— is value for value the MIDI-in map above: `0x01`→`0xB2`, `0x02`→`0xBC`, `0x04`→`0xBD`,
`0x0B`→`0xB3`, `0x10`–`0x13`→`0xB8`–`0xBB`, `0x40`→`0xB5`, and `0x81`, which is not a
controller number, → `0xB4`, channel pressure. A switch assigned `0x40` sends number `0xB5`
with `0x7F` / `0x00`, i.e. Hold on and off (`PanelAction_SwitchSendsHold`, `0xF8B298`, the
`0x40` arm of `PanelAction_AssignableSwitch`) — what reading the byte as a CC number
predicts.

⚠ Which physical controls panel groups `0x0B`–`0x17` are is not established, and neither
are the switch assignments `0x88`, `0x89` and `0x90` that `PanelAction_AssignableSwitch`
also branches on. Check: `notes/proma-2026-09-25/gen_panel_actions.py`, A1–A4.

The panel side of the chain — groups, action lists, held-button sets — is on
[Control Panel]({{ site.baseurl }}/wsa1-panel/#from-a-switch-to-a-parameter-record).

## Factory defaults and the combination memory

**The part records' factory defaults are in `prom_b`.** `0xF3F400`–`0xF3FFFF` is 77
`[id][len][payload]` records, and `ParamNumber_DefaultRecordPtrs` (prom_a `0xFAD28A`, 64
entries) moves in lockstep with the RAM table: `entry[n] = ParamNumber_RecordPtrs[n] +
0xF37DDE` for all 64. Three prom_a routines copy payload byte *H* to byte *H* of the RAM
record with the same number — `PartSettings_ResetToDefault` for `0x00`–`0x3F`,
`SystemSettings_ResetToDefault` for the thirteen others (through `ByteTable_FAD38A` and
`PtrTable_FAD397`), `MidiSettings_ResetToDefault` for bytes `0x0D`–`0x15` of the 32 first
halves; they are what the INITIAL screen's items run. The sources label the records
`Default_Part00_A` …, `Default_DspEffect1`–`3`, `Default_Record78` and so on. What the
defaults say:

* part *k*'s channel byte (`+0x0D`) defaults to *k*; part 9 — MIDI channel 10 — alone
  differs, in both halves;
* the three DSP effect blocks `0x61`–`0x63` default to algorithms **1, 35 and 20**.

Checks: `notes/promb-2026-09-25/factory_default_records.py` and
`notes/proma-2026-09-25/gen_default_records.py` (D1–D3).

**The factory combinations are in `prom_c`, in the same record numbers.** `prom_c`
`0xF80000`–`0xF965BF` is the factory COMBINATION memory — 16 banks × 8 combinations plus a
record named `Clear`, 704 bytes each — and CPU 1 reads it over the inter-processor link:
six prom_a routines build a CPU-2 address from the region's own constants and hand it to
`Link_SendCommandE2`, the link's remote read. `Combination_ReadFromCpu2` (`0xF98927`)
copies one 704-byte record to CPU-1 RAM `0x7620`. Each record is a chain of
`[tag][length][payload]` chunks, and the tags are parameter-record numbers. The
disassembly's SysEx reference
(`wsa1/docs/system-exclusive-reference/sec-blocks.tex`) names them:

| tag | chunk |
|---|---|
| `0x78` | COMBINATION NAME |
| `0x60` | EFFECT COMMON |
| `0x61` / `0x62` | EFFECT block 1 / 2 |
| `0x63` | REVERB block |
| `0x00 + k` / `0x20 + k` | PART *k* + 1, blocks A / B (eight parts) |
| `0x92` | KEY SCALING / SCALE TUNING |
| `0x79` | PART COMMON (real time) |

★ **Loading a combination is one block copy into the parameter records.** With the record
at `0x7620`, every one of the 23 chunks' payloads lands exactly on
`ParamNumber_RecordPtrs[tag]` — `0x78` at `0x7622`, `0x60` at `0x7634`, `0x61` at `0x7642`,
… `0x79` at `0x78B2` — and a RAM base two bytes either way matches none. That also explains
the one irregular step in the part-record table: part 7's first half is at `0x7862` and part
8's at `0x78E2`, `0x80` apart where every other step is `0x40`, because the combination's
`0x92` and `0x79` chunks and its terminator sit in between.
Re-derive it with `tools/wsa1_param_record_layout_check.py` in this repository, which reads
the two images and asserts all 23 matches, one chunk layout across all 129 records, and the
negative control.

⚠ The SysEx names come from the reference and from `sysex_combination_layout.py` in the
disassembly tree, not from prom_a's readers; `prom_b`'s default module still describes ids
`0x60`, `0x78`–`0x7A`, `0x80`, `0x91`–`0x93`, `0x98` and `0x99` as having no established
meaning, and reconciling the two is open (see [Open Questions]({{ site.baseurl }}/questions/#sx-wsa1r)).
The combination memory is read by prom_a routines, per
`notes/lanes/promcd-2026-09-25/preset_bank_readers.py`; its field layout by
`wsa1/notes/sysex-probes/sysex_combination_layout.py --fields`.

## SysEx from a standard MIDI file

The song reader in `prom_b` handles two kinds of SysEx inside an SMF (`SmfEvent_SysEx`):
General MIDI System On / Off (`7E 7F 09 01` / `02`), and the WSA1's own parameter change
`50 2C 04 00 11 00 <hi> <lo> 00 00 01 <nh> <nl>`, whose two data nibbles form one byte. For
address-hi `0x11` the low address byte indexes `SmfSysEx_Addr11_Targets`, a 118-entry table
of RAM byte addresses bounded by `cp A,0x75`. The writer side is
`SmfExport_ParamSysExTemplates` (`prom_b` `0xF74FCF`, 74 templates of 19 bytes), and for
address-hi `0x11` its templates 4–70 read RAM `0x7622 + lo` — the start of the parameter
records above, so `11 20` is `0x7642`, DSP effect block 1
(`notes/promb-2026-09-25/smf_param_sysex_probe.py`). Whether the SysEx reference's address
map matches the combination layout field by field is an
[open question]({{ site.baseurl }}/questions/#sx-wsa1r).

⚠ In `SmfSysEx_WriteAddr11` the unused-entry test `cp XDE,0xffffffff` runs *before*
`ld XDE,(XDE)`, so it compares the entry's address, not the entry: as the instructions
stand, a write to an unused address goes through to `0xFFFFFF`. This is read from the
bytes and has not been run on hardware or traced in MAME.
(`notes/promb-2026-09-25/smf_sysex_param_change.py`.)

The live-MIDI SysEx decoder is on [System Exclusive Messages]({{ site.baseurl }}/sysex-messages/#sx-wsa1r-system-exclusive).

## What is not established

* Which byte of a part record is which field, *from `prom_a`'s own code*: only the classes
  above, `+0x0D` (the MIDI channel byte) and the bytes the AND/OR patch lists touch (`+0x0C`,
  `+0x0D`, `+0x2B`–`+0x36`) are confirmed there. The SysEx reference names more — KEY LAYER
  LOW / HIGH at B-block `+0x07` / `+0x08` and others (`sysex_combination_layout.py --fields`)
  — and the shared layout above makes those names a strong lead, not yet a reading of the
  code. (The `0x40`-byte step between part records, once called "a step, not a proof", is
  two chunks of 2 + 30 bytes.)
* What parameter `0xB0` is (its handler stages a value from RAM `0x24F3`), and what the
  default-module ids listed above other than `0x7A`, the tempo, mean in prom_a's own code.
* Which controllers numbers `0xB6` and `0xB7` stand for; what the LOCAL TOTAL bit (bit 5
  of `0x7F36`) skips; the switch assignments `0x88`, `0x89`, `0x90`.
* `Dispatch_By_60F080__Tail` (64 words after the reachable table) and the stale copies of
  this module 0x400 lower — see
  [older-build remnants]({{ site.baseurl }}/wsa1-disassembly/#older-build-remnants-and-why-unreached-code-can-be-correct).

## Related

| Page | Description |
|------|-------------|
| [SX-WSA1 / SX-WSA1R Overview]({{ site.baseurl }}/wsa1/) | The machine, its memory maps and the inter-processor link |
| [Control Panel]({{ site.baseurl }}/wsa1-panel/) | The switch matrix and the panel's path into these records |
| [System Exclusive Messages]({{ site.baseurl }}/sysex-messages/#sx-wsa1r-system-exclusive) | The live SysEx vocabulary and decoder |
| [Disassembly]({{ site.baseurl }}/wsa1-disassembly/) | The source tree these facts are read from, and how complete it is |
