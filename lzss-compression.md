---
layout: page
title: LZSS Compression
permalink: /lzss-compression/
---

# LZSS Compression

The KN5000 firmware uses two closely related LZSS (Lempel-Ziv-Storer-Szymanski)
container formats, told apart by a single character in their magic string:

- **SLIDE4K** — 4 KB sliding window. Used for the 19 demo-song preset blocks in
  the Table Data ROM and for the compressed Sub-CPU firmware-update images.
- **SLIDE8K** — 8 KB sliding window. Used for the six multilingual HELP
  databases in the Table Data ROM. This variant was **undocumented before
  2026-08-07**; its decoder was recovered from the firmware and its round-trip
  tooling landed in commit `f40a93d` of the disassembly repository.

Both are handled by the same firmware entry point, `SLIDE_Parse_Header`, which
dispatches on the `4`/`8` character of the magic. This page documents both
formats, every compressed region found in the dumped ROMs, the decompression
routines, and the build-time round-trip that keeps rebuilt ROMs byte-identical.

## The Two Variants at a Glance

| Property | SLIDE4K | SLIDE8K |
|----------|---------|---------|
| **Magic (8 bytes)** | `"SLIDE4K", 0x00` | `"SLIDE8K", 0x00` |
| **Header size** | 11 bytes | 11 bytes |
| **Size field** | 24-bit **big-endian** at header+8 | 24-bit **big-endian** at header+8 |
| **Ring buffer size** | 0x1000 (4,096) | 0x2000 (8,192) |
| **Ring mask** | 0xFFF | 0x1FFF |
| **Zero pre-fill** | ring[0x0000-0x0FED] | ring[0x0000-0x1FF5] |
| **Initial write position** | 0x0FEE | 0x1FF6 |
| **Match offset** | `((high & 0xF0) << 4) \| low` — 12 bits | `((high & 0xF8) << 5) \| low` — 13 bits |
| **Match count** | `(high & 0x0F) + 3` → 3-18 bytes | `(high & 0x07) + 3` → 3-10 bytes |
| **Flag byte** | 8 elements, LSB first, 1 = literal | identical |
| **Termination** | declared output size only | declared output size only |
| **Firmware decoder** | `SLIDE_Decompress_4K_Init` (0xEF3FAB) | `SLIDE_Decompress_8K_Init` (0xEF40C5) |
| **Blocks known** | 19 in table_data (+ 3 archived update images) | 6 in table_data |

Addresses are Main CPU program ROM (v10). Both routines and the dispatcher live
in `v10/maincpu/boot/system_handlers.s` (lines 6980, 7103 and 7226).

**The dispatcher** (`SLIDE_Parse_Header`, 0xEF41E3,
`v10/maincpu/boot/system_handlers.s:7226`) compares the first **five** bytes of
the block against `SLIDE_STRING` and then reads the sixth character:

```asm
	ld	a, (xwa)
	cp	a, 0x34		; '4'
	jr	nz, SLIDE_Parse_Check8K
	...
	calr	SLIDE_Decompress_4K_Init
SLIDE_Parse_Check8K:
	cp	a, 0x38		; '8'
	jr	nz, SLIDE_Parse_ReturnOK
	...
	calr	SLIDE_Decompress_8K_Init
```

(`system_handlers.s:7245-7263`.) An unrecognised sixth character is silently
ignored — the routine returns success without decompressing anything. Only a
missing `SLIDE` prefix returns the 0xFFFF failure code.

---

## Compressed Data Regions

### Compressed Preset/Parameter Data (SLIDE4K Format)

| Property | Value |
|----------|-------|
| **ROM Component** | table_data |
| **Label** | `Compressed_Preset_Data_LZSS` (a.k.a. `DemoSongPreset18`) |
| **Start Address** | `0x8E0000` (CPU address) / `0xE0000` (offset in `kn5000_table_data.rom`) |
| **End Address** | `0x8E6D3E` (last payload byte; 0xFF padding starts at `0x8E6D3F`) |
| **Header Size** | 11 bytes |
| **Compressed Payload Size** | 27,956 bytes (27,881-byte LZSS stream + 75 verbatim tail bytes) |
| **Total Size** | 27,967 bytes |
| **Decompressed Size** | 38,144 bytes (0x9500, exact — declared by the header size field) |
| **Binary File** | `table_data/includes/demo_presets/demo_preset_18_compressed.bin` |

**Header Structure (11 bytes):**
```
Offset  Size  Content
------  ----  -------
0x00    8     "SLIDE4K", 0x00  (NUL-terminated format signature)
0x08    3     Decompressed size, 24-bit BIG-ENDIAN
              (here: 00 95 00 = 0x009500 = 38,144 bytes)
```

The LZSS stream begins immediately at offset 0x0B. The bytes `7D 5A EE` at
offsets 0x0B-0x0D — previously documented as three extra header metadata bytes
of a supposed 14-byte header — are actually the first flag byte and the first
two payload bytes of the compressed stream.

**Endianness evidence:** the v142 Sub-CPU update image
(`kn5000_subprogram_v142_compressed.rom`) carries size field `03 00 00`;
big-endian that is 0x030000 = 196,608, exactly the decompressed size of the
Sub-CPU program. Read little-endian it would be 3. (The preset block's
`00 95 00` is endian-symmetric and cannot discriminate.) The firmware agrees:
both `SLIDE_Decompress_*_Init` routines build the count as
`(hdr[8] << 16) + ((hdr[9] << 8) | hdr[10])`
(`v10/maincpu/boot/system_handlers.s:7121-7133`).

The decoder stops as soon as the declared output size (38,144 bytes) is
reached, which happens at ROM address `0x8E6CF4` after consuming 27,881 stream
bytes. The remaining 75 bytes up to `0x8E6D3E` are real (non-0xFF) ROM content
that the decoder never reads; they are preserved verbatim so the rebuilt ROM
stays byte-identical.

**Reader.** The block is demo-song preset 18: `DemoSongPreset_PointerTable[18]` (`0x9C4048`)
points at it, and `Demo_ParseSlideHeader` hands it to `SLIDE_Parse_Header` with destination
**main-CPU RAM `0x69800`**, exactly as for demo songs 0-17. The decompressed image begins
"ZZZZ" like theirs, and `Seq_CopyResourcePtrs` pairs demo number 18 with the Feature Demo
script. `SubCPU_Send_Payload` never reads `0x8E0000`. (Established in the source's header on
this block, September 2026, `tdata` lane.)

**Important Clarification:**

> **This compressed region does NOT contain the Sub CPU ROM.** Decompression yields 38,144 bytes (~37KB) of parameter-like data, not the 192KB executable code found in `kn5000_subprogram_v142.rom`.

**Decompressed Data Characteristics:**
- Size: 38,144 bytes (0x9500) (vs 196,608 bytes for Sub CPU ROM)
- Content: Parameter/preset data structure, not executable code
- Most bytes are in MIDI range (0-127)
- Contains repeating structural patterns (e.g., `0x80 XX` flags, `00 03` record markers)
- Does NOT match the Sub CPU ROM byte patterns

### The Other 18 SLIDE4K Blocks (Demo Song Presets)

The 0x8E0000 block is entry 18 of a set of 19. Entries 0-17 run from
**0x9C4050** to **0x9F94CA**, abutting one another except for a single 0xFF pad
byte at **0x9C9017**; 0xFF fill follows from 0x9F94CB. Each has its own 11-byte
`SLIDE4K` header; the last of them starts at 0x9F494E. A scan of
`original_ROMs/kn5000_table_data.rom` for the magic finds exactly these 19
blocks and no others; their declared decompressed sizes range from 0x1700 to
0x9500 bytes. They are built from checked-in MIDI + YAML sources (see
[Source Files](#source-files) below).

<a id="slide8k-help-databases"></a>

### SLIDE8K Help Databases (0x983B3A - 0x9999CB)

Six SLIDE8K blocks exist in the entire dumped ROM set — all of them in the Table
Data ROM, inside the region historically covered by
`table_data/includes/icons_to_strings.bin`. Five are live multilingual HELP
databases; the sixth is an orphan (below).

| # | ROM address | Language | Stream length | Compressed slice | Decompressed |
|---|-------------|----------|---------------|------------------|--------------|
| 0 | `0x983B3A` | German (**stale, orphaned**) | 0x3EEE (16,110) | 16,111 B | 0x9000 |
| 1 | `0x988690` | English (also used for slot 4) | 0x349E (13,470) | 13,471 B | 0x9000 |
| 2 | `0x98BB3A` | German | 0x3594 (13,716) | 13,717 B | 0x9000 |
| 3 | `0x98F0DA` | French | 0x3926 (14,630) | 14,631 B | 0x9000 |
| 4 | `0x992A0C` | Spanish | 0x39E2 (14,818) | 14,819 B | 0x9000 |
| 5 | `0x9963FA` | Indonesian | 0x35C6 (13,766) | 13,767 B | 0x9000 |

"Stream length" is the compressed bitstream proper (header excluded); the
"compressed slice" checked in as
`original_ROMs/help_db_<lang>_compressed.original.bin` is that stream **plus the
one trailing alignment pad byte** (see
[Byte-Exact Recompression](#byte-exact-recompression)). Every block declares —
and produces — exactly 0x9000 (36,864) bytes.

**What the payload is.** Each decompressed database starts with a table of
32-bit little-endian pointers into itself, based at **RAM 0x69800** (the English
database's first entries are 0x69B22, 0x69E5C, 0x6A1B8, …), followed by the
help-string pool. Strings are Latin-1 with `~0d` as the newline escape. The
payload's internal record format has **not** been decoded further: the
decompressed databases are checked in as binaries
(`table_data/includes/help_databases/help_db_<lang>.bin`), not yet as text
sources.

**How the firmware gets there.** The help-language load path in the Main CPU ROM
reads the language number from RAM 0x0340E4, indexes the pointer table at
0x988018, and calls the dispatcher with the destination in XBC:

```
f4779f: ld   A,(0x0340e4)      ; help language number
f477a4: sll  0x02,A            ; × 4
f477ab: add  XWA,0x00988018    ; HelpDB_LanguageTable
f477b1: ld   XWA,(XWA)         ; -> SLIDE8K block address
f477b3: ld   XBC,0x00069800    ; destination RAM
f477d3: call 0xef41e3          ; SLIDE_Parse_Header
```

There are only five distinct languages: slot 4 of the six-entry table reuses the
English block at 0x988690. See
[Table Data ROM]({{ site.baseurl }}/table-data-rom/) for the language index and
intro strings, and `table_data/help_databases.s` for the annotated source.

#### The orphaned block at 0x983B3A

Block 0 is a **superseded revision of the German database**. No 32-bit
little-endian pointer to 0x983B3A exists in any dumped ROM (v7, v9, v10 program
ROMs, table data, custom data, Sub-CPU) — nothing references it.

Its stream is not merely "corrupt": decoding it reproduces the live German
database **byte-for-byte for exactly 0x55E0 output bytes**, and then diverges.
The reason is visible in the ROM layout: the factory image wrote the two Music
Stylist pointer tables (`StyleRec_PtrTable_CategoryOrder` at 0x986000 and
`StyleRec_PtrTable_Default` at 0x987000) straight over this obsolete block's
tail. The last element decoded entirely from surviving bytes ends at ROM
0x985FFE; the very next element reads its two bytes at 0x985FFF/0x986000 —
i.e. straddles into the overwritten region — and everything from output byte
0x55E0 onward is therefore garbage. The decoder still walks the (now foreign)
bytes until the output count reaches 0x9000, consuming its last stream byte at
ROM 0x987A32.

The block is **preserved byte-exactly and deliberately not "fixed"**: the
surviving stream is emitted as a raw slice (`table_data/help_databases.s`),
because its true tail no longer exists anywhere. Its whole walked extent is
still round-trip verified by `make verify-help-databases` so the bytes stay
pinned.

---

<a id="disputed-interpretations"></a>

### ✅ RESOLVED: Address 0x3E0000 is Custom Data Flash (Firmware Update Staging)

> **Resolution:** The `0x3E0000` address mystery has been solved by analyzing the firmware update routines.

---

## Firmware Update System and 0x3E0000

### Discovery: 0x3E0000 is a Firmware Update Destination

The address `0x3E0000` is **Custom Data Flash** (not an alternate ROM mapping). During firmware updates, compressed Sub CPU payload data is written here:

**File Type 007 Handler** (`HANDLE_UPDATE_FILE_TYPE_ID_007h` at 0xEF47FA):
```asm
; "Technics KN5000 Program DATA FILE PCK"
HANDLE_UPDATE_FILE_TYPE_ID_007h:
    LD WA, 1                    ; Select Custom Data Flash
    LD XBC, 003e0000h           ; Write to 0x3E0000
    CALL Flash_EraseSectorWithBankSelect           ; Flash write routine
    LD WA, 1
    LD XBC, 003f0000h           ; Write to 0x3F0000
    CALL Flash_EraseSectorWithBankSelect           ; Flash write routine
```

The flash write routine (`Flash_EraseSectorWithBankSelect`) uses `CUSTOM_DATA_FLASH__BASE_ADDR` (0x300000) as the base when `WA=1`.

### Update File Types

| ID | File Type | Destination | Format |
|----|-----------|-------------|--------|
| **007** | Program DATA FILE **PCK** | Custom Data Flash 0x3E0000 + 0x3F0000 | LZSS compressed |
| 008 | Table DATA FILE **PCK** | Table Data ROM | LZSS compressed |
| 001 | Program DATA FILE 1/2 | Table Data ROM 0x800000 | Uncompressed |
| 003 | Table DATA FILE 1/2 | Table Data ROM 0x800000 | Uncompressed |

The three archived update images
(`original_ROMs/kn5000_subprogram_v14{0,1,2}_compressed.rom`, 93,124 / 93,181 /
93,203 bytes) are whole-file SLIDE4K containers: the 11-byte header followed by
one stream, decompressing to the 196,608-byte Sub-CPU payload. Only **v1.42**
has a full source tree behind it; see [Round-Trip Coverage](#round-trip-coverage).

### Boot Sequence Behavior

**After a firmware update:**
1. Compressed payload exists at Custom Data Flash 0x3E0000
2. `SubCPU_Send_Payload` decompresses from 0x3E0000 → success
3. Updated Sub CPU firmware is loaded

**Factory state (no update):**
1. Custom Data Flash at 0x3E0000 contains user data or is empty
2. `SubCPU_Send_Payload` tries to decompress → fails (returns 0xFFFF)
3. Falls back to `TABLE_DATA_ROM__BASE_ADDR` (0x800000)

### Memory Map Clarification

| Address | Memory Region | Purpose |
|---------|---------------|---------|
| 0x3E0000 | Custom Data Flash (offset 0xE0000) | Firmware update staging area |
| 0x8E0000 | Table Data ROM (offset 0xE0000) | Factory LZSS preset data |
| 0x830000-0x87FFFF | Table Data ROM (offset 0x30000-0x7FFFF) | Tone database -- data shipped to Sub CPU RAM 0x050000 |

The addresses `0x3E0000` and `0x8E0000` are **NOT the same physical data** - they are different chips:
- `0x3E0000` = Custom Data Flash IC19 (user-writable)
- `0x8E0000` = Table Data ROM IC7/IC8 (factory programmed)

---

<a id="preset-data-destination-dispute"></a>

## The "Preset Data Destination" Dispute: a Strong Lead

The disassembly's `CLAUDE.md` lists **Preset Data Destination** under *Known Disputed
Interpretations*. Claude's earlier view was that the LZSS preset data goes to Sub CPU `0xF000+`.
The human concern was that the transfer sizes do not match and that the fallback to `0x800000`
produces invalid data (mostly `0xF7`). Two findings from September 2026 bear on it. Both are
read from the code and the ROM. **Neither has been confirmed in MAME.**

1. **The SLIDE4K preset block at `0x8E0000` is not on this path at all.** Its reader is the
   demo-song pointer table, and it decompresses to main-CPU RAM `0x69800` (see
   [above](#compressed-presetparameter-data-slide4k-format)). `SubCPU_Send_Payload` knows
   exactly two bases. It decompresses the SLIDE4K image at custom-data `0x3E0000` into RAM
   `0x50000` (only when `SubCPU_FlashPayloadEnableFlag` reads `0xFF`). Otherwise, or if that fails, it
   uses `XIZ = 0x800000` raw. It then ships `XIZ + 0x100` onward to Sub CPU `0xF000`,
   `0x1F000` and `0x2F000` (64 KB + 64 KB + 0xFF00 bytes) and `XIZ + 0..0xFF` to Sub CPU
   `0x400` (`v10/maincpu/kn5000_v10_program.s`, `SubCPU_Send_Payload`).
2. **`0x800000` is the section directory and a bank of 8bpp bitmaps**, whose transparent
   palette index is **`0xF7`** (see [Table Data ROM]({{ site.baseurl }}/table-data-rom/#section-directory-and-bitmap-bank-0x800000)).
   So the `0xF7` bytes the fallback sends are those bitmaps' transparent pixels. That
   explains "why does fallback produce 0xF7 bytes": the fallback ships picture data, not a
   payload.

**Status: strong lead, not confirmed.** What would settle it: run the MAME driver with an
erased custom-data flash (no SLIDE image at `0x3E0000`), log the E1 transfers
`SubCPU_Send_Payload` makes, and check what reaches Sub CPU `0x400` and `0xF000+`. The
dispute table in the disassembly's `CLAUDE.md` has not been updated yet. The source of the
lead is `notes/lanes/wave2-2026-09-25/lane-reports/tdata.json` (the `tdata` lane) and the
`table_data/preset_banks.s` header.

## Remaining Questions (Partially Disputed)

While the 0x3E0000 address is now understood, some aspects of the preset data transfer remain unclear:

**Decompressed Data Structure:**

| Section | Offset | Size | Runtime Destination |
|---------|--------|------|---------------------|
| Main CPU Header | 0x0000-0x00AF | 176 bytes | Main CPU only (word at 0x100 → RAM 0x0404) |
| Sub CPU Audio Params | 0x00B0-0x808D | 32,734 bytes | Sub CPU address 0xF000+ (uncertain) |

*Note: this breakdown was derived from a truncated 32,910-byte decompression;
the true output is 38,144 bytes (0x9500), so the section boundaries above need
re-derivation.*

**Outstanding questions:**
- The bulk transfers send 64KB blocks (much larger than the ~37KB of meaningful data)
- The fallback to `TABLE_DATA_ROM__BASE_ADDR` (0x800000) produces mostly 0xF7 bytes — now read as the transparent pixels of the bitmap bank there ([strong lead](#preset-data-destination-dispute), not confirmed in MAME)
- The exact purpose of the preset parameters at Sub CPU 0xF000+ is not fully understood

**Main CPU Header (0x00-0xAF):**
- Mostly zero bytes with sparse configuration values
- Key non-zero positions: 0x18-0x1B, 0x2E, 0x45, 0x57-0x5A, 0x61, 0x94-0x9E, 0xA4-0xA5
- Contains record marker `00 03 01 00` at offset 0x94
- Word at offset 0x100 is copied to Main CPU RAM 0x0404 before bulk transfer

**Sub CPU Audio Parameters (0x100+) - per Claude's interpretation:**
- **Destination**: Sub CPU address 0xF000 (overwrites ROM defaults) - *DISPUTED*
- Variable-length records, often starting with `00 03` marker
- 24 occurrences of `00 03` record markers
- Flag byte `0x80` indicates "value set" (actual value in next byte)
- Pattern `18 XX` appears to indicate parameter type codes
- Common sequence: `64 03 00 7F 20 00 70 80`
- Most values are MIDI-range (0-127), suggesting voice/audio parameters

**Sub CPU 0xF000 Area Usage (IF Claude's interpretation is correct):**

The Sub CPU ROM (`kn5000_subprogram_v142`) contains default values at 0xF000+. These are audio engine configuration tables:

| Address | Purpose |
|---------|---------|
| 0xF000-0xF01F | System configuration, counters |
| 0xF010-0xF100 | Voice parameters (ADSR envelopes) |
| 0xF100-0xF420 | Pitch tables, envelope lookups |
| 0xF420-0xF434 | Runtime buffer initialization |
| 0xF434-0xF460 | Serial buffer structures |
| 0xF48C+ | Voice polyphony/index tables |

If the interpretation is correct, the preset data would overwrite these defaults during boot, configuring factory presets for the audio engine.

**Open Questions - Preset Data Destination (Added due to AI/Human disagreement):**

The following questions remain open regarding where the LZSS preset data actually ends up:

1. **What does 0x3E0000 actually map to?** The memory bank configuration during boot needs investigation.
2. **Are there other ~33KB transfers?** Search for data transfers matching the preset data size.
3. **What happens to the "extra" bytes?** The 64KB transfer vs ~37KB data discrepancy is suspicious.
4. **Why does fallback produce 0xF7 bytes?** This suggests the fallback path may never be intended to work. *Lead (September 2026, not confirmed in MAME): `0x800000` is a bitmap bank whose transparent colour is `0xF7`; see [the dispute section](#preset-data-destination-dispute).*

**Open Questions - Sub CPU Payload Transfer:**

The Sub CPU executable payload (~192KB) is transferred to the Sub CPU via the inter-CPU communication latches during boot. **Where the Main CPU reads it from is unresolved.**

1. **`0x830000-0x87FFFF` is not it.** That region is the **tone database** -- sound-parameter *data*, copied into the Sub CPU's data window at RAM 0x050000, not into its code area at 0x400+. See [Tone Database]({{ site.baseurl }}/tone-database/) and the retraction on [SubCPU Payload Loading]({{ site.baseurl }}/subcpu-payload-loading/).

2. **`SubCPU_Send_Payload`'s two source bases** are the LZSS image at Custom Data Flash `0x3E0000` if it decompresses, and table-data `0x800000` otherwise. In the images this project holds, neither contains the payload: custom-data `0x3E0000` is 131,072 bytes of 0xFF with no `SLIDE` magic anywhere in the 1 MB dump, and no byte of `kn5000_subprogram_v142.rom` appears anywhere in the table-data or custom-data dumps. **Whether that means no File Type 007 update was ever applied to the dumped unit is *not* established** — an interrupted install and a truncated, 0xFF-padded dump are byte-indistinguishable from a never-programmed chip. See [Sub-CPU Payload Provenance]({{ site.baseurl }}/subcpu-payload-provenance/), where the mechanism is now closed end-to-end and only the dump provenance remains open.

3. **The executable is known only** from its own ROM dump (`kn5000_subprogram_v142.rom`) and from the compressed update-disc images. The runtime code-payload source path is flagged as open, not explained.

See [Boot Sequence]({{ site.baseurl }}/boot-sequence/) and [Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/) for related documentation.

---

## SLIDE4K Format Specification

SLIDE4K is a variant of LZSS (Lempel-Ziv-Storer-Szymanski) compression with the following parameters:

| Parameter | Value |
|-----------|-------|
| **Sliding Window Size** | 4,096 bytes (4KB) |
| **Window Offset Bits** | 12 bits (0x000 - 0xFFF) |
| **Match Length Bits** | 4 bits (encoded length + 3) |
| **Minimum Match Length** | 3 bytes |
| **Maximum Match Length** | 18 bytes (15 + 3) |
| **Window Pre-fill** | First 4,078 bytes (0xFEE) filled with 0x00 |

### Encoding Format

The compressed data consists of flag bytes followed by literal bytes or back-references:

1. **Flag Byte:** Each bit (LSB first) indicates the type of the next 8 elements:
   - Bit = 1: Literal byte follows
   - Bit = 0: Back-reference follows

2. **Literal Byte:** Single byte copied directly to output

3. **Back-Reference:** Two bytes encoding position and length:
   ```
   Byte 1: Low 8 bits of window offset
   Byte 2: [High 4 bits of offset][4-bit length]

   offset = (byte2 & 0xF0) << 4 | byte1
   length = (byte2 & 0x0F) + 3
   ```

### Decompression Algorithm

```python
def decompress_slide4k(data):
    window = bytearray(4096)
    window[0:0xFEE] = bytes(0xFEE)  # Pre-fill with zeros
    window_pos = 0xFEE
    output = bytearray()

    i = 0
    while i < len(data):
        flags = data[i]
        i += 1

        for bit in range(8):
            if i >= len(data):
                break

            if flags & (1 << bit):
                # Literal byte
                byte = data[i]
                i += 1
                output.append(byte)
                window[window_pos] = byte
                window_pos = (window_pos + 1) & 0xFFF
            else:
                # Back-reference
                if i + 1 >= len(data):
                    break
                low = data[i]
                high = data[i + 1]
                i += 2

                offset = ((high & 0xF0) << 4) | low
                length = (high & 0x0F) + 3

                for _ in range(length):
                    byte = window[offset]
                    output.append(byte)
                    window[window_pos] = byte
                    window_pos = (window_pos + 1) & 0xFFF
                    offset = (offset + 1) & 0xFFF

    return bytes(output)
```

---

## SLIDE8K Format Specification

SLIDE8K is the same scheme with a doubled ring and one bit moved from the match
count into the match offset. The authority for everything below is
`scripts/build/decompress_slide8k.py` / `compress_slide8k.py` in the
disassembly repository — they round-trip all six factory blocks byte-identically
— cross-checked line by line against `SLIDE_Decompress_8K_Init`
(`v10/maincpu/boot/system_handlers.s:7103-7224`).

### Container

```
Offset  Size  Content
------  ----  -------
0x00    7     "SLIDE8K"
0x07    1     0x00 terminator
0x08    3     Decompressed size, 24-bit BIG-ENDIAN
              (all six factory blocks: 00 90 00 = 0x9000 = 36,864 bytes)
0x0B    ...   compressed stream
```

Identical in shape to SLIDE4K; only the magic differs.

### Ring Buffer

The firmware `malloc`s **0x2000** bytes and zero-fills only up to the initial
write position, leaving the last ten ring bytes as allocator garbage:

```
ef40cc: push 0x2000              ; ring size
ef40cf: call 0xff0e80            ; Malloc
ef40db: lda  XBC,XHL+0x1ff6      ; fill limit
ef40e0: ld   (XWA+),0x00         ; zero-fill ring[0x0000-0x1FF5]
ef40e4: cp   XWA,XBC
ef40e6: jr   C,0xef40e0
ef40e8: ld   BC,0x1ff6           ; initial write position
```

So ring positions **0x0000-0x1FF5 are zero** and the write position starts at
**0x1FF6**, wrapping modulo 0x2000. (SLIDE4K: 0x1000-byte ring, zero-filled to
0x0FED, write position 0x0FEE — `system_handlers.s:6984-6995`.) A valid encoder
must never emit a match reading ring[0x1FF6-0x1FFF] before the corresponding
output bytes have been written; `compress_slide8k.py` enforces exactly that
(`find_longest_match`, lines 195-243).

### Flag Bytes

The firmware keeps the flag in a 16-bit word as `0xFF00 | flags` and shifts it
right once per element; the reload happens when the 0xFF sentinel has been
shifted out of bit 8 (`system_handlers.s:7139-7148`). That is what guarantees
exactly 8 elements per flag byte. Bit 0 after each shift selects the element
type — **LSB first**, 1 = literal, 0 = back-reference (`:7152`).

### Match Encoding

A back-reference is two bytes, low then high:

```
offset = ((high & 0xF8) << 5) | low      ; 13-bit ABSOLUTE ring position
count  = (high & 0x07) + 3               ; 3 .. 10 bytes
```

The offset is an absolute ring position, not a distance, and the ring is written
while the copy runs — so a match may legally read bytes it has just produced
(this is how runs longer than the distance to the write position are encoded).

The firmware forms the offset with `and wa, 0xf8` / `sll wa, 5`
(`system_handlers.s:7182-7183`). The **+3 base** is confirmed twice over: the
count field is masked with `and iz, 0x7` and then incremented by 2
(`:7187-7188`), and the copy loop is **inclusive** — `cp iy, iz` / `jr ule`
(`:7211-7212`) — so it runs `iy = 0 … iz`, i.e. `(high & 0x07) + 3` iterations.
The SLIDE4K routine is structurally identical with `0xF0`/`<<4`, `and iz, 0xf`
(`:7059-7065`, `:7088-7089`), giving `(high & 0x0F) + 3`.

### Termination

Termination is **purely by output count** against the header's declared size.
The count is checked before every compressed-stream byte read and after every
element, but the match copy loop itself is *not* bounds-checked, so a final
back-reference could in principle overrun the declared size. None of the six
factory blocks do — all produce exactly 0x9000 bytes.

There is no end-of-stream marker, and the trailing bits of the last flag byte
are never examined.

### Reference Decoder

```python
WINDOW_SIZE, WINDOW_MASK, START = 0x2000, 0x1FFF, 0x1FF6

def decompress_slide8k(buf, offset=0):
    assert buf[offset:offset + 8] == b"SLIDE8K\x00"
    size = (buf[offset+8] << 16) | (buf[offset+9] << 8) | buf[offset+10]
    i = offset + 11

    window = bytearray(WINDOW_SIZE)   # zero prefill
    wpos = START
    out = bytearray()
    flag = 0                          # 16-bit flag word, 0xFF00 | flags

    while True:
        flag >>= 1
        if not (flag & 0x100):        # sentinel gone: reload
            if len(out) >= size: break
            flag = 0xFF00 | buf[i]; i += 1
        if flag & 1:                              # literal
            if len(out) >= size: break
            b = buf[i]; i += 1
            out.append(b); window[wpos] = b
            wpos = (wpos + 1) & WINDOW_MASK
        else:                                     # back-reference
            if len(out) >= size: break
            low = buf[i]; i += 1
            if len(out) >= size: break
            high = buf[i]; i += 1
            ref = ((high & 0xF8) << 5) | low
            for k in range((high & 0x07) + 3):    # ring is live during the copy
                b = window[(ref + k) & WINDOW_MASK]
                out.append(b); window[wpos] = b
                wpos = (wpos + 1) & WINDOW_MASK
        if len(out) >= size: break

    return bytes(out)
```

---

<a id="byte-exact-recompression"></a>

## Byte-Exact Recompression

Rebuilding a ROM from source means the compressed blocks must come out
**byte-identical**, and for both SLIDE variants that is only achievable by
replaying the original encoder's decisions (`--reference`). Plain re-encoding
produces a *valid* stream, but not the factory bytes: the original Technics
compressor's offset/length choices do not follow a simple greedy or lazy
matching rule.

Two further subtleties, specific to how these streams end, would defeat a naive
re-encode even if the match choices were reproduced:

**1. Partially consumed final flag byte with nonzero unused bits.** Because the
decoder stops on the output count, the last flag byte is usually consumed
mid-group, and its never-read high bits are not guaranteed to be zero. Measured
on the six factory streams:

| Block | Last flag byte | Elements consumed | Unused bits |
|-------|----------------|-------------------|-------------|
| German (stale, 0x983B3A) | `0xA0` | 1 | **nonzero** (0x50 remaining) |
| English | `0x30` | 6 | 0 |
| German | `0x00` | 3 | 0 |
| French | `0x00` | 8 | 0 |
| Spanish | `0x00` | 4 | 0 |
| Indonesian | `0x00` | 5 | 0 |

The replay path therefore re-emits each original flag byte **verbatim**, while
still verifying that its *consumed* bits agree with the replayed decisions
(`compress_slide8k.py`, `encode_decisions`, lines 111-161).

**2. An alignment pad byte after every stream.** Each factory block is followed
by exactly one byte of leftover encoder output that the decoder never reads,
so that the next block starts on an even address. The values are arbitrary:
0x20, 0x7F, 0xCF, 0xCD, 0xCE after the English, German, French, Spanish and
Indonesian streams respectively. Such a byte yields no decision and would be
lost on re-encode, so when the replayed output is an exact prefix of the
reference the remaining original bytes are carried over unchanged
(`compress_slide8k.py`, `compress_with_reference`, lines 295-297).

With `--strict`, anything that cannot be reproduced from the reference decisions
is a hard error, so a rebuilt ROM can never silently diverge from the factory
bytes.

---

<a id="round-trip-coverage"></a>

## Round-Trip Coverage

| Data | Format | Source of truth in the repo | Build gate |
|------|--------|------------------------------|------------|
| 19 demo-song presets | SLIDE4K | `.mid` + `.yaml` per preset | `make verify-demo-presets` |
| 5 live help databases | SLIDE8K | decompressed `.bin` per language | `make verify-help-databases` |
| stale German block | SLIDE8K | raw slice of the dump (tail lost) | round-trip checked, not rebuilt |
| v1.42 update image | SLIDE4K | the source-built v142 payload | `cmp` inside `make all` |
| v1.40 / v1.41 update images | SLIDE4K | archived images only | not source-built |

**Still open:** `kn5000_subprogram_v141.rom` has no source tree (tracked as issue
`kn5000-v41`), and the v1.40 payload exists only because it was decompressed out
of its update image and committed for preservation. The help-database *payloads*
are likewise still opaque binaries — decoding their pointer-table/string-pool
record format is future work.

---

## Decompression Routines

The KN5000 contains **two independent decompressor implementations**.

### Main CPU program ROM (both variants)

These are the routines the running instrument uses, e.g. for the help databases
and the demo presets. Source: `v10/maincpu/boot/system_handlers.s`.

| Label | Address (v10) | Purpose |
|-------|---------------|---------|
| `SLIDE_Parse_Header` | `0xEF41E3` | Validate `"SLIDE"`, dispatch on `'4'`/`'8'` |
| `SLIDE_Decompress_4K_Init` | `0xEF3FAB` | SLIDE4K decoder (0x1000 ring) |
| `SLIDE_Decompress_8K_Init` | `0xEF40C5` | SLIDE8K decoder (0x2000 ring) |

Calling convention: XWA = pointer to the block, XBC = destination address.
Returns HL = 0 on success, 0xFFFF when the `"SLIDE"` prefix is absent.

### Table Data ROM bootloader (SLIDE4K only)

A second, self-contained decompressor lives in the first-stage bootloader at the
end of the **table_data** ROM. It is used during boot and firmware-update
operations, reads its input through a sector buffer, and paints a progress
indicator. Source: `table_data/kn5000_table_data.s`.

#### LZSS_Decompress (Main Decompressor)

| Property | Value |
|----------|-------|
| **Address** | `0xFFCA50` (CPU) / `0x09FCA50` (ROM) |
| **Label** | `LZSS_Decompress` |
| **Purpose** | Main SLIDE4K decompression routine |

**Description:** This is the primary decompression routine that:
- Allocates a 4KB sliding window buffer via `malloc`
- Pre-fills the window with zeros (positions 0x0000 to 0x0FED)
- Reads the compressed size from the header
- Processes flag bytes and handles literal/back-reference encoding
- Displays progress during decompression
- Frees the window buffer when complete

**Stack Frame Layout:**
```
XSP+0x00: (local variable)
XSP+0x04: Flag byte (with sentinel in high byte)
XSP+0x06: Copy counter for back-reference
XSP+0x08: Match length
XSP+0x0A: Window write position
XSP+0x0C: Window base address (copy of +0x10)
XSP+0x10: Window buffer pointer (from malloc)
```

#### LZSS_ReadByte

| Property | Value |
|----------|-------|
| **Address** | `0xFFC8C2` (CPU) / `0x09FC8C2` (ROM) |
| **Label** | `LZSS_ReadByte` |
| **Purpose** | Read next byte from compressed input stream |
| **Returns** | HL = byte read, or 0xFFFF if EOF |

**Description:** Handles sector buffering for reading compressed data. Reads 0x2400 bytes per sector from the table_data ROM and manages sector advancement for large compressed data.

#### LZSS_OutputByte

| Property | Value |
|----------|-------|
| **Address** | `0xFFC935` (CPU) / `0x09FC935` (ROM) |
| **Label** | `LZSS_OutputByte` |
| **Purpose** | Write decompressed byte to output buffer |
| **Input** | A = byte to output |

**Description:** Buffers 4 bytes and writes them as a 32-bit word to the destination for efficient memory access. Uses buffer at RAM address 0x0C0A.

#### LZSS_OutputByte_Alt

| Property | Value |
|----------|-------|
| **Address** | `0xFFC974` (CPU) / `0x09FC974` (ROM) |
| **Label** | `LZSS_OutputByte_Alt` |
| **Purpose** | Alternate output handler for different buffer |

**Description:** Variant of LZSS_OutputByte that uses buffer at RAM address 0x0C0E instead of 0x0C0A. Used in flash update operations.

#### LZSS_ParseHeader

| Property | Value |
|----------|-------|
| **Address** | `0xFFC9B3` (CPU) / `0x09FC9B3` (ROM) |
| **Label** | `LZSS_ParseHeader` |
| **Purpose** | Parse and validate LZSS header for flash updates |

**Description:** Sets up the source address (0x3E0000 = Custom Data Flash),
reads six header bytes and `memcmp`s five of them against the `"SLIDE"` string
at 0xFFA150 (= table_data 0x9FA150), then pre-reads sectors for the initial
buffer fill. Note that this bootloader path compares only the five-character
prefix and always uses its 4K decoder — it has **no** SLIDE8K support. Only the
Main CPU's `SLIDE_Parse_Header` inspects the `4`/`8` character.

---

## RAM Variables

The table_data bootloader's LZSS routines use the following RAM locations:

| Address | Size | Purpose |
|---------|------|---------|
| `0x0C20` | 4 | Expected decompressed output size |
| `0x0C24` | 4 | Current output position |
| `0x0C28` | 4 | Source ROM address pointer |
| `0x0C2C` | 4 | Sector read buffer pointer |
| `0x0C30` | 2 | Display X coordinate (progress) |
| `0x0C32` | 2 | Display Y coordinate (progress) |
| `0x0C34` | 2 | Sector offset for progress display |
| `0x0C36` | 1 | Output byte counter (0-3 for 32-bit writes) |
| `0x0C0A` | 4 | Temporary output buffer (LZSS_OutputByte) |
| `0x0C0E` | 4 | Temporary output buffer (LZSS_OutputByte_Alt) |

The Main CPU's `SLIDE_Decompress_*_Init` routines keep their state on the stack
and in the malloc'd ring instead; the ring pointer is stashed at RAM 0x0622.

---

## SLIDE String Markers

The firmware contains `"SLIDE"` string markers used to validate SLIDE headers
before decompression. There are exactly two in the Main CPU program ROM and one
in the table_data ROM:

| Location | Address | Label |
|----------|---------|-------|
| Main CPU | `0xE00032` | `SLIDE_STRING` |
| Main CPU | `0xE00188` | `SLIDE_STRING_2` |
| Table Data | `0x9FA150` | (within boot data) |

`SLIDE_Parse_Header` compares against `SLIDE_STRING`; the table_data bootloader's
`LZSS_ParseHeader` compares against the copy at 0x9FA150. Only the five-character
prefix is compared in both cases — the variant character is checked separately
(and only by the Main CPU routine).

---

## Usage Context

### Boot Sequence

During the boot sequence, the Main CPU's `SubCPU_Send_Payload` routine:
1. Transfers the **tone database** from 0x830000-0x87FFFF to Sub CPU data RAM 0x050000 (five 64 KB bulk transfers) -- this is data, not the executable
2. Attempts to decompress the SLIDE4K image at 0x3E0000 in Custom Data Flash
3. If decompression fails (returns 0xFFFF), falls back to base 0x800000 (the section directory and bitmap bank; see [the dispute section](#preset-data-destination-dispute))
4. Transfers the code blocks (Sub CPU 0x400 and 0xF000-0x3EEFF) from whichever base survived step 2/3 -- and in the dumped images neither base holds the payload, so the actual factory source is **unresolved**

See [Boot Sequence]({{ site.baseurl }}/boot-sequence/) for details.

### Help System

Pressing HELP and then any panel button looks the button up in the active
language's database. The database is decompressed on demand from one of the five
SLIDE8K blocks into RAM 0x69800 (see
[SLIDE8K Help Databases](#slide8k-help-databases) above).

### Firmware Updates

The LZSS decompressor is also used during firmware updates to handle compressed
update files. The bootloader's flash-update path (`Boot_FlashUpdate_Main`, 0x9FCC2A
onward) processes compressed ROM images in SLIDE4K form; the archived Sub-CPU update
images are all SLIDE4K. The region **0x9FD8A5-0x9FEA9C**, which older notes called
"flash update handlers", is not part of that path -- it is the bootloader's uPD72068
FDC command-layer driver (see [FDC Subsystem]({{ site.baseurl }}/fdc-subsystem/)).

---

## Compression Tools

All tools live in `scripts/build/` in the disassembly repository.

### SLIDE4K

```bash
# Re-derive all 19 demo-preset blocks from the factory ROM
python3 scripts/build/decompress_demo_presets.py \
    --rom original_ROMs/kn5000_table_data.rom \
    --output-dir table_data/includes/demo_presets --emit-references

# Byte-identical recompression (replays the factory encoder's decisions)
python3 scripts/build/compress_lzss.py input.bin output.bin \
    --strict --reference original_ROMs/demo_preset_18_compressed.original.bin

# ... and with the 11-byte "SLIDE4K\0" + 24-bit BE size header prepended
python3 scripts/build/compress_lzss.py input.bin output.rom \
    --strict --with-header --reference original_ROMs/kn5000_subprogram_v142_compressed.rom
```

### SLIDE8K

```bash
# Extract all six known blocks (payload + raw stream) from the dump slice
python3 scripts/build/decompress_slide8k.py --all --outdir /tmp/slide8k

# Decompress one block at a known offset, asserting the expected size
python3 scripts/build/decompress_slide8k.py table_data/includes/icons_to_strings.bin \
    --offset 0x43918 --expected-size 0x9000 --output help_db_english.bin

# Byte-identical recompression
python3 scripts/build/compress_slide8k.py help_db_english.bin out.bin \
    --strict --reference original_ROMs/help_db_english_compressed.original.bin
```

`decompress_slide8k.py --compressed-out` writes the stream **without** the header
and **without** the alignment pad, which is the form `--reference` expects to
compare against.

**Note:** the `--reference` option decodes the compression decisions from the
original file and replays them. Without it, both compressors emit a valid but
different stream — see [Byte-Exact Recompression](#byte-exact-recompression).

---

## Makefile Targets

```bash
# --- SLIDE4K: 19 demo-song presets ---------------------------------------
make decompress-demo-presets   # bootstrap: re-extract from the factory ROM
make demo-midi                 # regenerate the .mid sources
make demo-sidecars             # regenerate the .yaml sidecars
make rebuild-demo-presets      # .mid + .yaml -> .bin -> compressed .bin
make verify-demo-presets       # byte-compare all 19 against the factory streams

# --- SLIDE8K: 6 help databases -------------------------------------------
make decompress-help-databases # bootstrap: re-extract the decompressed sources
make rebuild-help-databases    # recompress the checked-in sources
make verify-help-databases     # byte-compare all 6 against the factory streams
```

`make all` rebuilds every ROM and additionally regenerates
`rebuilt_ROMs/kn5000_subprogram_v142_compressed.rom` from the source-built v142
payload with `compress_lzss.py --strict --with-header --reference`, sealing it
with a `cmp` against the archived update image.

Both `verify-*` targets print one `OK`/`MISMATCH` line per block. As of
2026-08-07 all 25 blocks (19 SLIDE4K + 6 SLIDE8K) report `OK`.

---

<a id="source-files"></a>

## Source Files

### Demo-song presets (SLIDE4K)

The compressed blocks are **build products**. The checked-in sources are MIDI
files plus YAML sidecars carrying everything MIDI cannot express (song header,
cell topology, padding, stream order, running-status flags):

```
table_data/includes/demo_presets/midi/demo_preset_NN.mid     <- musical content
table_data/includes/demo_presets/sidecar/demo_preset_NN.yaml <- everything else
    ↓ (midi_to_preset.py)
table_data/includes/demo_presets/demo_preset_NN.bin          <- uncompressed
    ↓ (compress_lzss.py --strict --reference)
table_data/includes/demo_presets/demo_preset_NN_compressed.bin  <- in ROM
```

Both `.bin` stages are generated and git-ignored. *(This supersedes the earlier
`table_data/preset_data.asm` flow described in older revisions of this page;
that file no longer exists.)*

### Help databases (SLIDE8K)

```
table_data/includes/help_databases/help_db_<lang>.bin        <- checked-in source
    ↓ (compress_slide8k.py --strict --reference)
table_data/includes/help_databases/help_db_<lang>_compressed.bin  <- in ROM
```

`table_data/help_databases.s` is the assembly module that emits the language
pointer tables, the intro strings, the 11-byte SLIDE8K headers and these
payloads — and the stale German block as a raw slice.

### Reference files

| File | Description |
|------|-------------|
| `original_ROMs/demo_preset_NN_compressed.original.bin` | Factory SLIDE4K stream, ×19 |
| `original_ROMs/help_db_<lang>_compressed.original.bin` | Factory SLIDE8K stream + pad byte, ×6 |
| `original_ROMs/kn5000_subprogram_v14{0,1,2}_compressed.rom` | Sub-CPU update images (whole-file SLIDE4K) |

---

## Future Work

- [ ] Decode the help-database payload format (pointer table + string pool at RAM 0x69800) into per-topic sources
- [ ] Reverse engineer the preset parameter record format in detail
- [ ] Determine the exact purpose of each parameter type (`18 XX` codes)
- [ ] Build a source tree for the v1.41 Sub-CPU payload (issue `kn5000-v41`)
- [ ] Re-derive the 0x8E0000 section boundaries from the full 38,144-byte decompression
