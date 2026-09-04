---
layout: page
title: Sub-CPU Boot ROM (IC30)
permalink: /subcpu-boot-rom/
---

# The Sub-CPU Boot ROM (IC30)

The sub-CPU's only non-volatile memory is **IC30**, which the MAME driver's memory map
describes as a 1 Mbit (128 KB) mask ROM. It holds
everything the sub-CPU can do on its own: bring up the SFRs, copy a block of interrupt
trampolines into RAM, acknowledge the main CPU's commands, run the power-on diagnostics,
and turn a keybed touch reading into a velocity. Then it waits to be replaced. The real
audio firmware is the 192 KB payload the main CPU pushes across the inter-CPU link at
every power-on; when it has arrived, `MAIN_LOOP` executes `CALL 0x000400` and control
never returns to the boot loader.

For the transfer itself see [SubCPU Payload Loading]({{ site.baseurl }}/subcpu-payload-loading/)
and [Sub-CPU Payload Provenance]({{ site.baseurl }}/subcpu-payload-provenance/); for the
three surviving payload revisions see
[Sub-CPU Firmware Images]({{ site.baseurl }}/subcpu-firmware-images/).

> **Correction (August 2026).** Two claims that used to appear on this site and in the
> assembly source are wrong and are retracted here.
>
> 1. The 96 KB of `0xFF` at the bottom of the image is **not erased flash and not
>    padding — it was never read.** IC30 is a mask ROM, which has no erased state.
>    `kn5000.cpp` flags the file `BAD_DUMP` and names the ranges `0xFE0800-0xFF7800` and
>    `0xFF9800-0xFFF000` as "not dumped yet. Assumed here as being filled with 0xFF."
> 2. A figure such as "the sub-CPU boot ROM is ~99% disassembled" is meaningless.
>    **97% of the chip is `0xFF`, and 89% of it was never read.** What is 100%
>    byte-identical is the *rebuild of the dump file* — which contains those assumed
>    bytes — not a reconstruction of the physical part.
>
> The disassembly repository records the same correction in commit `153dc45`.

## 1. What the dump actually contains

Measured directly from `original_ROMs/kn5000_subcpu_boot.ic30`
(131,072 bytes, sha1 `d29429a9…`, crc32 `a45ceb77`):

| Region | Range (sub-CPU) | Size | Status | Non-`0xFF` bytes |
|---|---|---:|---|---:|
| Window 1 | `0xFE0000-0xFE07FF` | 2,048 | read | 0 |
| — | `0xFE0800-0xFF77FF` | 94,208 | **never read** | assumed `0xFF` |
| Window 2 | `0xFF7800-0xFF97FF` | 8,192 | read | 4,053 |
| — | `0xFF9800-0xFFEFFF` | 22,528 | **never read** | assumed `0xFF` |
| Window 3 | `0xFFF000-0xFFFFFF` | 4,096 | read | 299 |
| **Whole chip** | `0xFE0000-0xFFFFFF` | **131,072** | 14,336 read (10.9%) | **4,352 (3.3%)** |

So the chip breaks down as 4,352 bytes of real content, 9,984 bytes that were read and
came back blank, and 116,736 bytes (89.1%) that nobody has ever looked at. Both of the
last two categories are `0xFF` in the file and are byte-indistinguishable from each other:
**the window boundaries are documentary, not measurable.**

All the content sits in **two blocks**, both in the top 32 KB:

| Block | Extent | Extent size | Non-`0xFF` | Contents |
|---|---|---:|---:|---|
| 1 | `0xFF8000-0xFF904C` | 4,173 | 4,053 | the 656-byte data region, then all the code |
| 2 | `0xFFFE80-0xFFFFFF` | 384 | 299 | diagnostic tail, reset trampoline, vector table, 16 reserved bytes |

Two details worth stating precisely, because earlier versions of this site got them
slightly wrong. The blocks are *extents*, not runs: block 1 contains 120 interior `0xFF`
bytes and block 2 contains 85, so the extents sum to 4,557 while the actual non-`0xFF`
count is 4,352. And block 2 splits into three runs if any `0xFF` gap counts as a
separation — there is a 60-byte blank gap at `0xFFFFB4-0xFFFFEF` between the end of the
interrupt vector table and the four reserved words `41 b1 62 1b` at `0xFFFFF0`, which is
why some pages describe "three blocks" and others "two".

Block 1 ends exactly where it should: `COPY_VECTORS` copies 225 bytes (45 handlers ×
5 bytes) from `0xFF8F6C`, and `0xFF8F6C + 0xE1 = 0xFF904D` — one past the last non-`0xFF`
byte in the chip's code half. The dump does not cut the code off mid-structure anywhere.

### Where the image is mapped

The disassembly (`subcpu/boot/subcpu_boot.ld`, and every `.org` in the source) and MAME
both base the 128 KB image at sub-CPU `0xFE0000`, spanning `0xFE0000-0xFFFFFF`.

⚠ **The mapping is contested.** An adversarial re-verification argued from the chip-select
registers that the decoded window may really be **64 KB at `0xFF0000-0xFFFFFF`**, which would put the lower
half of the image outside the sub-CPU's address space altogether and would restate the
headline as "at most ~52 KB is both addressable and undumped". That rests on a
memory-decode rule reconstructed from the firmware's own register writes rather than from
a datasheet, and every address-range table derived that way is interpretation rather than
measurement. Treat it as an open question. What is not in
dispute: all 4,352 measured bytes lie in `0xFF8000-0xFFFFFF`, and the 2 KB read at
`0xFE0000` came back entirely blank.

## 2. How the dump was taken

**Owner testimony (Felipe, 2026-08-08), recorded as testimony.** The partial dump was
**deliberate**. His tooling could copy only small chunks at a time, so he read the regions
that appeared to hold the boot code needed to get the emulator running, analysed that
code, found no references from it into the regions he had not read, and inferred that the
rest was `0xFF`. **He calls this an educated guess, not a measurement**, and intends a
full dump when the instrument is physically accessible again — it is currently in storage
in another country.

That is the whole provenance of the 116,736 assumed bytes. It is also why the `BAD_DUMP`
flag must stay until the chip is read in full.

### Is the guess safe? Tested, not settled

**For it.** A structure-aware reference census over the byte-identical disassembly found
220 ROM-address operand references, all in dumped windows and none in an undumped range;
the 45 live vector entries and the single indirect `CALL T,XWA` (bounded by an 8-entry
table, all of whose targets are dumped) resolve into dumped space; and the loaded v1.42
payload calls back into IC30 at only two addresses, `0xFFFEA1` and `0xFFFE86`, both
dumped. An independent re-check for this page agrees: of the 149 distinct
`0xFExxxx`/`0xFFxxxx` address constants that appear anywhere in the source, **none** falls
in an undumped range, and all 45 live vector-table entries point either at `0xFFFEE0`
(dumped) or into sub-CPU RAM at `0x405-0x4DC`.

**Against it.** The wave-6 adjudicator graded the guess **UNDECIDED**, because the test
that would settle it — enumerating the targets of real `JP`/`JR`/`CALL`/`CALR`
instructions and the vector entries out of a disassembly, rather than scanning bytes — has
never been run as an auditable artifact, and because raw byte scans *do* turn up
candidates. Two concrete ones, re-measured here: the little-endian long at `0xFF8C44` is
`0x00FF42A3` and the one at `0xFF8C4A` is `0x00FFCFEB`, both pointing into never-read
space.

Neither survives contact with the disassembly — both fall inside the black-key comparison
chain of `NOTE_VELOCITY_LOOKUP_CALCULATE` (`cp c,0xA` / `jr z` / `cp c,0x8` …), and
neither constant appears as an operand anywhere in the source. That is precisely the
adjudicator's point: at this data volume a raw scan manufactures coincidences, so only a
structure-aware enumeration counts, and the strength of the census above depends on a
disassembly whose own completeness is bounded by the same dump.

**What a full dump would not fix.** It would not answer the sub-CPU payload-source
question. The payload is 196,608 bytes, the entire chip is 131,072, the boot ROM has no
decompressor of its own (the main CPU expands the SLIDE4K image into its own DRAM and
sends the result), and IC30 is not in the main CPU's address space at all — the two CPUs
share only 8-bit latches. See
[Sub-CPU Payload Provenance]({{ site.baseurl }}/subcpu-payload-provenance/).

## 3. What the boot ROM does

The flow, from `subcpu/boot/kn5000_subcpu_boot.s`:

1. **Reset.** Vector slot 0 at `0xFFFF00` holds `0x00FFFEE0`, and the five bytes there are
   `1b 90 82 ff 0e` — `JP 0xFF8290; RET` — so control lands in `BOOT_INIT`.
2. **`BOOT_INIT`** programs the SFR block (ports, serial channels, timers, DRAM refresh,
   micro-DMA), sets `XSP = 0x05A2`, then calls `COPY_VECTORS`.
3. **`COPY_VECTORS`** (`0xFF846D`) copies 225 bytes from ROM `0xFF8F6C` to RAM `0x400` —
   45 five-byte handler trampolines, one per live vector slot.
4. **`INIT_MEMORY_TEST`** (`0xFF8956`), **`INIT_DMA_SERIAL`** (`0xFF85AE`) and
   **`INIT_TONE_GEN`** (`0xFF84A8`) run in that order. `INIT_MEMORY_TEST` returns
   immediately unless bit 0 of `0x30` is clear; on the diagnostic path it instead runs
   `MEM_TEST_ROUTINE`, `ROM_CHECKSUM` and `HARDWARE_CALIBRATION_SEQUENCE`, accumulates
   their error bits in `MEMTEST_RESULT` (`0x556`) and then loops forever calling
   `SERIAL_INIT` — it never comes back.
5. **`MAIN_LOOP`** (`0xFF840C`) clears bit 6 of `SUBCPU_STATUS_FLAGS` (`0x4FE`) and spins
   until the payload-ready flag is set, then `CALL 0x000400`. The payload's first 225
   bytes are 45 five-byte `JP <24-bit>; RET` trampolines — all 45 checked — and the
   256-byte transfer that carries them overwrites exactly the block `COPY_VECTORS` just
   wrote, so from that moment the same 45 interrupt vectors dispatch into payload code.

Interrupt handling, the inter-CPU command state machine and the DMA routines are covered
in [Boot Sequence]({{ site.baseurl }}/boot-sequence/#sub-cpu-boot-sequence),
[Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/) and
[ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/#sub-cpu-boot-rom).

## 4. The 656-byte data region at 0xFF8000

Until August 2026 the 656 bytes ahead of the boot entry point were a single `.incbin` of
`subcpu_boot_data_8000.bin`, commented "possibly for audio/DSP". That one directive was
hiding **eight addresses that code loads by name**, none of which any tool reading the
source could see. Commit `9f48883` replaced it with eight independent objects that tile
the region exactly:

| Object | Address | Size | Referenced from |
|---|---|---:|---|
| `CmdHandler_Table` | `0xFF8000` | 32 | `CMD_Dispatch_Handler` (`0xFF88B8`) |
| `MemTest_RegionTable` | `0xFF8020` | 10 | `MEM_TEST_ROUTINE` (`0xFF89FC`) |
| `ToneGen_VelCurve_Pivot` | `0xFF802A` | 2 | `NOTE_VELOCITY_LOOKUP_CALCULATE` (`0xFF8BD2`) |
| `ToneGen_VelCurve_Divisor` | `0xFF802C` | 2 | `NOTE_VELOCITY_LOOKUP_CALCULATE` |
| `ToneGen_VelCurve_ModeParams` | `0xFF802E` | 30 | `NOTE_VELOCITY_LOOKUP_CALCULATE`, at `0xFF8040` |
| `ToneGen_Velocity_Input_Curve` | `0xFF804C` | 256 | `NOTE_VELOCITY_LOOKUP_CALCULATE` |
| `ToneGen_Velocity_Output_Curve` | `0xFF814C` | 256 | `NOTE_VELOCITY_LOOKUP_CALCULATE` |
| `ToneGen_ProbeVoice_ParamBlock` | `0xFF824C` | 68 | `HARDWARE_CALIBRATION_SEQUENCE` (`0xFF8C80`) |

32 + 10 + 2 + 2 + 30 + 256 + 256 + 68 = **656**, and `0xFF8290 − 0xFF8000 = 656`: the
carve accounts for every byte, with nothing left over and nothing overlapping.

The eight *referenced* addresses are `0xFF8000`, `0xFF8020`, `0xFF802A`, `0xFF802C`,
`0xFF8040`, `0xFF804C`, `0xFF814C` and `0xFF824C` — note that `0xFF8040` is a reference
*into the middle* of the mode-parameter table, not to its start, which is why the eight
objects and the eight cross-references are not the same list.

Nothing in the region is code. After the carve there is **no `.incbin` directive left in
`subcpu/boot/kn5000_subcpu_boot.s`** at all.

### The command-handler jump table at 0xFF8000

Eight little-endian 32-bit code pointers. `CMD_Dispatch_Handler` state 1 reads the command
byte at RAM `0x51A`, splits it into a 5-bit payload length (low bits, plus 1) and a 3-bit
handler index (high bits), scales the index by 4 (`sla wa,2`), adds it to the base
(`lda_24 xbc,(0xff8000)`) and `call`s the entry with a three-word payload descriptor on
the stack.

The table reads `{0xFF8496, 0xFF849F, 0xFF84A2, 0xFF849C, 0xFF8499, 0xFF84A5, 0xFF85AB,
0xFF85AB}`. **Every one of those targets is the same three bytes, `db a8 0e` —
`lds hl,0 / ret`.** The boot loader accepts and acknowledges the main CPU's entire command
surface and implements none of it; the working handlers arrive with the payload.

It is real dispatch data all the same, not padding: there are seven distinct stub
addresses, slots 6 and 7 share one, and reading the six consecutive stubs in address order
gives dispatch indices 0, 4, 3, 1, 2, 5 — a shuffle no filler would produce. The stub
labels carry the index they serve (`CmdHandler_Stub_Cmd0` … `CmdHandler_Stub_Cmd5`,
`CmdHandler_Stub_Cmd6And7`), replacing the old `STUB_8499`-style names.

The shape is the same one the payload uses once it takes over — an 8-entry table indexed
by the top three bits, with entries 6 and 7 sharing a handler. Compare `CMD_DISPATCH_TABLE`
at `0x00F46C` on [SubCPU Command Format]({{ site.baseurl }}/subcpu-command-format/).

### The RAM-test region descriptor at 0xFF8020

Ten bytes, and exactly one row: `MEM_TEST_ROUTINE` indexes with `muls wa,0xA` and stops
after the first entry (`cp (xsp+4),0x1`). The fields are

| Offset | Type | Value | Meaning |
|---|---|---|---|
| +0 | u32 | `0x00050000` | first address tested |
| +4 | u32 | `0x00050000` | byte count (the loop shifts it right by 3 and covers 8 bytes a pass) |
| +8 | u8 | `0x01` | error bit for a low half-word mismatch |
| +9 | u8 | `0x02` | error bit for a high half-word mismatch |

The row therefore covers sub-CPU DRAM `0x050000-0x09FFFF` — 320 KB of the 1 MB at
IC28/IC29. That is not an arbitrary window: it is **exactly** the buffer the main CPU
fills immediately afterwards, since `SubCPU_Send_Payload`'s five unconditional transfers
copy table-data `0x830000-0x87FFFF` into sub-CPU `0x050000-0x09FFFF` (the tone database)
before it even decides where the executable payload will come from. Each pass writes
`0x5A5A5A5A` and `0xA5A5A5A5`, checks each half-word separately, and restores the original
contents.

The two error bits are OR-ed into the value `MEM_TEST_ROUTINE` returns in `L`, which
`INIT_MEMORY_TEST` stores in `MEMTEST_RESULT` (`0x556`) alongside `ROM_CHECKSUM`'s bit 2
and `HARDWARE_CALIBRATION_SEQUENCE`'s bit 3.

### The velocity and touch front end at 0xFF802A-0xFF824B

Five objects, consumed together by `NOTE_VELOCITY_LOOKUP_CALCULATE`, which
`INTER_CPU_LATCH_READ_DISPATCH` (`0xFF8B89`) calls after reading a 16-bit word from the
hardware latch at `0x110000`: low byte = note index, high byte = raw touch reading.

The computation, read off the code:

```
v  = Velocity_Input_Curve[touch]          ; 256-byte LUT at 0xFF804C
v  = (v - 77) * gain / 128                ; pivot 0xFF802A, divisor 0xFF802C, gain from the mode record
v += pivot_out                            ; mode record +1
v -= black_key_trim  if note%12 in {1,3,6,8,10}   ; mode record +2
clamp v to 0..255
velocity = Velocity_Output_Curve[v]       ; 256-byte LUT at 0xFF814C, stored to (XWA+1)
```

`ToneGen_VelCurve_ModeParams` is ten 3-byte records, one per touch-sensitivity mode. The
row count and the 3-byte stride are not guesswork: the v1.42 payload indexes the identical
table as `byte[0x01F420 + 3*mode]`, and the table self-describes — its first byte steps
`0x00, 0x10, 0x20 … 0x90` across the ten rows.

| Mode | Gain | Output at pivot | Black-key trim |
|---:|---:|---:|---:|
| 0 | 0/128 | 208 | 0 |
| 1 | 16/128 | 199 | 3 |
| 2 | 32/128 | 189 | 6 |
| 3 | 48/128 | 180 | 8 |
| 4 | 64/128 | 171 | 11 |
| 5 | 80/128 | 161 | 14 |
| **6** | **96/128** | **152** | **16** |
| 7 | 112/128 | 143 | 19 |
| 8 | 128/128 | 134 | 22 |
| 9 | 144/128 | 130 | 24 |

Mode 0 has zero gain — touch off, every note leaves at level 208. As the gain rises the
output at the pivot falls and the black-key trim grows with it (roughly 0.17 × gain), so
the ten curves fan out about a common point. **The boot ROM hard-codes mode 6**
(`lda_24 xde,(0xff8040)`); only the payload selects among the ten.

The two 256-byte curves are worth reading as a pair. The input curve is monotonically
*decreasing* — `0xFF` for inputs 0-8, then `0xFB 0xF6 0xF1 …` down to `0x01` by input 224
and `0x00` at 254-255. The output curve is monotonically increasing, `0x01` then a long
run of `0x02`, reaching `0x7F` at index 255; from index 144 upward it is exactly
`index − 128`, a straight 2:1 divide, and below that it flattens hard, squeezing the whole
soft half of the range into velocities 1-16. The decreasing sense of the input curve is
consistent with the raw reading being a key-travel *time* (a fast, loud strike giving a
small number), which is an inference from the curve's shape and the tone generator's
treatment of the velocity field as an attenuation — not something the ROM states.

### The tone-generator probe voice at 0xFF824C

A complete 34-word tone-generator voice-parameter record, used by the power-on TG liveness
probe. `HARDWARE_CALIBRATION_SEQUENCE` opens with two raw register writes
(`0x100000 ← 0x0840`, `0x100002 ← 0xFF00`; then `0x0800`/`0xFF80`), passes this block to
`HARDWARE_PARAM_BLOCK_WRITE` (`ld xbc,0xFF824C`), then re-reads word 0 and writes it to TG
register 0 through `HARDWARE_VERIFY_WRITE`; the probe succeeds when the TG status word at
`0x100004` reads back 0.

`HARDWARE_PARAM_BLOCK_WRITE` transmits words 1-21 to TG register offsets `0x040`, `0x080`,
`0x0C0`, `0x100`, `0x140`, `0x180`, `0x400`, `0x440` … `0xA40` (address to `0x100000`,
data to `0x100002`), forcing bit 15 of word 2 on the way out and clearing it again in a
final write. Words 22-33 complete the record's shape but this routine does not transmit
them.

This path is on the same strap-gated diagnostic branch as the RAM test, so it does not run
during a normal boot.

### The same bytes are in the payload

The last six of the eight objects also exist, byte for byte, inside the v1.42 sub-CPU
payload, where they were already carved and named in `v142/subcpu/subcpu_data_tables.s`.
Verified by direct comparison of the two ROM images:

| Boot ROM | v1.42 payload | Bytes | Name |
|---|---|---:|---|
| `0xFF802A` | `0x01F418` | 2 | `ToneGen_VelCurve_Pivot` |
| `0xFF802C` | `0x01F41A` | 2 | `ToneGen_VelCurve_Divisor` |
| `0xFF802E` | `0x01F420` | 30 | `ToneGen_VelCurve_ModeParams` |
| `0xFF804C` | `0x01F43E` | 256 | `ToneGen_Velocity_Input_Curve` |
| `0xFF814C` | `0x01F53E` | 256 | `ToneGen_Velocity_Output_Curve` |
| `0xFF824C` | `0x00F919` | 68 | `ToneGen_ProbeVoice_ParamBlock` |

The only layout difference is that the payload has a four-byte pointer
(`ToneGen_Voice_Bitmap_Ptr`, value `0x0000F002`) between the divisor and the mode
parameters; the boot ROM omits it and runs the two blocks together. The boot ROM's labels
were deliberately kept identical to the payload's so the two copies grep together — and
the probe-voice record, which the v1.42 notes describe as unreachable *there*, turns out
to be live *here*.

## 5. Still open

- **The chip needs a full dump.** 116,736 bytes have never been read. The owner's existing
  tooling can reach the part of that which is addressable under either mapping in two more
  passes — `0xFF0000-0xFF77FF` (30 KB) and `0xFF9800-0xFFEFFF` (22 KB) — and a control read
  at `0xFD0000-0xFD07FF` would additionally tell us whether `0xFF` is simply the value an
  unmapped read returns, which would drain the blank 2 KB at `0xFE0000` of any meaning.
  This is the prerequisite for removing `BAD_DUMP`.
- **The reference check should be redone properly**, as an enumeration of real
  control-flow targets and vector entries rather than a byte scan, and committed as an
  artifact.
- **"Erased flash" is still in the source.** Both `subcpu/boot/kn5000_subcpu_boot.s:231`
  and the ASL mirror `archive/asl/subcpu/boot/kn5000_subcpu_boot.asm:232` still say
  "ROM starts with 96KB of 0xFF (erased flash)". The correction is recorded in the plan
  but has not been applied to the comments.
- **The ASL mirror still hides the data region.** The carve landed in the LLVM source
  only; `archive/asl/subcpu/boot/kn5000_subcpu_boot.asm` still `binclude`s
  `subcpu_boot_data_8000.bin`, which is therefore still a live build input (see the
  Makefile rule for `kn5000_subcpu_boot.rebuilt.p`). Both builds reproduce the dump file
  byte for byte.
- **A proposed source shrink was rejected**, and deliberately so. Collapsing the 98,304
  lines of `.byte 0xff` into one `.fill` is byte-safe, but it would assert as a fact
  something the dump does not support; commit `153dc45` records the reasoning.
- **The sub-CS2 window question** (64 KB at `0xFF0000` versus 128 KB at `0xFE0000`) is
  undecided, and it changes the headline number for how much undumped space is even
  addressable.

## Verification

Both builds of this ROM are byte-identical to the dump file, checked with `cmp` against
`original_ROMs/kn5000_subcpu_boot.ic30`:

```
rebuilt_ROMs/kn5000_subcpu_boot.llvm.rom       identical   (LLVM TLCS-900 backend)
rebuilt_ROMs/kn5000_subcpu_boot.rebuilt.rom    identical   (legacy ASL mirror)
```

`scripts/build/compare_roms.py` reports the boot ROM in two of its fifteen sections — one
primary, one ASL — both at 100.00%. That is a statement about the rebuild, and only about
the rebuild: see the correction at the top of this page.

## Related pages

- [SubCPU Payload Loading]({{ site.baseurl }}/subcpu-payload-loading/) — the transfer protocol
- [Sub-CPU Payload Provenance]({{ site.baseurl }}/subcpu-payload-provenance/) — where the payload is supposed to come from
- [Sub-CPU Firmware Images]({{ site.baseurl }}/subcpu-firmware-images/) — v1.40 / v1.41 / v1.42
- [SubCPU Command Format]({{ site.baseurl }}/subcpu-command-format/) — the dispatch table the payload installs
- [ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/#dump-provenance) — the dump-provenance record for every gated image
- [Boot Sequence]({{ site.baseurl }}/boot-sequence/#sub-cpu-boot-sequence) — the sub-CPU side of power-on
- [MAME Emulation Gaps]({{ site.baseurl }}/mame-emulation-gaps/) — what the driver does and does not model
