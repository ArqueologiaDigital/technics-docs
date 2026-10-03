---
layout: page
title: HDAE5000 Filesystem
permalink: /hdae5000-filesystem/
---

# HD-AE5000 Custom Filesystem

The HD-AE5000 extension board uses a **custom filesystem** of its own. It is not
FAT12/16/32: there is no boot sector, BPB or FAT identifier string. It does keep
a file allocation table of its own, 32-bit entries linking cluster chains, and
that is what the ROM's "Hard disk FAT read error" message refers to. Files are
not found through a directory tree. They are **parts of songs**: a fixed table
of 120 directories × 16 songs, each song record holding the first cluster of
each of its parts. The firmware was written by M. Kitajima (Technics Software
section), dated Juli-Oktober 1996.

Everything on this page is read from the disassembly in `kn5000-roms-disasm`
unless it says otherwise. The routines are in `hdae5000/hdae5000_ui_display.s`,
`hdae5000_filesystem.s` and `hdae5000_hd_driver.s`. The RAM variables are the
`HDAE5000_RAM_` `.equ` block at the top of `hdae5000/hd-ae5000_v2_06i.s`, each
with its evidence. Most names on this page come from the Wave 2 `hdae` lane,
which renamed the filesystem, lyrics and PC-link layers after reading their data
(`notes/lanes/wave2-2026-09-25/lane-reports/hdae.json`; rename maps
`scripts/renaming/rename_hdae5000_*.sed`).

> **Earlier versions of this page were largely wrong.** They described an
> "FSB/FGB/FEB" block hierarchy with 21- and 37-byte directory entries, a VarInt
> "sector allocation table" at `0x22B430`, "file operations" at
> `0x28D6D1-0x28E187`, and "audio settings" at `0x2307A4`. All of that came from
> the lyrics player and the list screens misread as a filesystem. `0x22B430` is
> the lyric-file buffer. The "VarInt" routines read SMF variable-length
> quantities. The "file operations" are the lyric parser, and the "audio
> settings" are the lyric's time signature. See
> [Lyric Files](#lyric-files-tlx) and the
> [rename table](#routines-that-were-misnamed) below.

## Hardware

| Component | Details |
|-----------|---------|
| Storage Medium | 2.5" IDE Hard Disk (1.08GB capacity) |
| PC Interface | NEC uPD71055 (i8255-compatible) PPI for parallel port communication |
| Static RAM | 512KB (2x 256KB) at 0x200000-0x27FFFF |
| ROM | 512KB at 0x280000-0x2FFFFF |
| ATA Registers | 0x130010-0x130020 |
| Addressing Mode | CHS (Cylinder/Head/Sector) -- not LBA |

### ATA Commands Used

| Command | Code | Routine |
|---------|------|---------|
| READ SECTORS | 0x20 | `HDAE5000_ATA_ReadSector` |
| WRITE SECTORS | 0x30 | `HDAE5000_ATA_WriteSector` |
| STANDBY (IMMEDIATE) | 0x94 | `HDAE5000_ATA_Standby` |
| IDENTIFY DEVICE | 0xEC | `HDAE5000_ATA_IdentifyDevice` |

See [HDAE5000 Hard Disk Interface]({{ site.baseurl }}/hdae5000-disk-interface/) for the register sequences.

## Sector Numbers and CHS

The filesystem numbers sectors from **1**. `HDAE5000_ATA_ReadSector` and
`HDAE5000_ATA_WriteSector` split a sector number *s* **head-major**, not cylinder-major as
LBA does:

```
head     = (s - 1) / (cylinders × sectors_per_track)
cylinder = ((s - 1) - head × C × S) / sectors_per_track
sector   = s - head × C × S - cylinder × S          (1-based)
```

The head stride `cylinders × sectors per track` is kept at `0x200200` by
`HDAE5000_HD_ParseIdentify`. So the filesystem's consecutive sectors run along
all cylinders of head 0 before moving to head 1, and filesystem sector 1 is the
disk's first sector (C0/H0/S1).

## Disk Layout

`HDAE5000_HD_ParseIdentify` derives the whole layout from the IDENTIFY DEVICE
block (words 54-58: current cylinders, heads, sectors per track, capacity):

| Filesystem sectors | Contents | RAM variable |
|--------------------|----------|--------------|
| 1 | Settings sector: signature longs `0xAA55AA55`, `0xF4F1F2F3` at +0, six setting bytes at +0x78 | read into `0x200628` |
| 2 - 3907 | **FAT**: 32-bit entries, 128 per sector | `HDAE5000_RAM_FatStartSector` = 2 |
| 3908 - 4230 | the **323 table sectors**: the in-RAM tables below, stored verbatim | `HDAE5000_RAM_TablesStartSector` = 3908 |
| 4231 - end | **data**: clusters, cluster 1 first | `HDAE5000_RAM_DataStartSector` = 4231 |

- **Cluster size** (`HDAE5000_RAM_SectorsPerCluster`) is 0x20 sectors, or 0x40
  on drives of at least 0x14DC93 sectors. `HDAE5000_RAM_ClusterBytes` holds
  it in bytes.
- **FAT entries**: 0 = free, `0xFFFFFFFE` = end of chain. The allocator
  (`HDAE5000_HD_FindFreeCluster`) returns `0xFFFFFFFD` when the disk is full.
  `HDAE5000_RAM_FatEntryCount` counts whole 128-entry FAT sectors, sized to the
  data area. `HDAE5000_HD_CountFreeClusters` counts the zero entries into
  `HDAE5000_RAM_FreeClusters`.
- **Signature.** `HDAE5000_HD_CheckSignature` sets `HDAE5000_RAM_HdSignatureOk`
  when the settings sector starts with the two longs. In memory those are the
  bytes `55 AA 55 AA F3 F2 F1 F4`. A drive without them is reported as
  unformatted (step code 1 of `HDAE5000_HD_Init`).
- **Settings.** The six bytes at +0x78 become the RAM settings `0x229DA9`-`0x229DAE`:
  `HDAE5000_RAM_QuickLoadMode`, `HDAE5000_RAM_LoadByNumberMode`,
  `HDAE5000_RAM_JumpAfterLoad`, `HDAE5000_RAM_LyricJump`,
  `HDAE5000_RAM_LyricForeColor` and `HDAE5000_RAM_LyricBackColor`.

### The Tables (sectors 3908-4230)

`HDAE5000_HD_ReadTables` reads the 323 sectors into RAM `0x201632`, and
`HDAE5000_HD_WriteTables` writes them back, reads each one back and compares it
(7 retries). `HDAE5000_HD_InitTables` builds the blank images a format writes.
`HDAE5000_HD_GetBlockInfo` hands the PC link the three blocks as
`{address, record width, record count[, items]}`:

| Block | RAM | Record | Count | Contents |
|------:|-----|-------:|------:|----------|
| 0 | `0x201632` (`HDAE5000_RAM_DirNames`) | 16 B | 120 | directory names (blank = 16 spaces) |
| 1 | `0x201DB2` (`HDAE5000_RAM_SongRecords`) | 76 B | 1,920 | song records, 16 per directory: `0x201DB2 + dir × 0x4C0 + song × 0x4C` |
| 2 | `0x2257B2` (`HDAE5000_RAM_FlsRecords`) | 144 B | 120 | FLS records, 32 items each |

16 × 120 + 76 × 1,920 + 144 × 120 = 165,120 bytes = 322.5 sectors, hence 323.

**Song record (76 bytes)**:

| Offset | Size | Contents |
|--------|------|----------|
| +0 | 26 | name, space-padded (blank = 26 spaces) |
| +26 | 10 | zeroed by a format |
| +36 | 10 × 4 | first-cluster slots, `0xFFFFFFFF` = empty |

Nine part types have their own `HDAE5000_SaveSong_*`, `HDAE5000_LoadSong_*` and
`HDAE5000_DeleteSongPart_*` routines: LSW, PMT, SQT, CMP, TM, MSP, RCM, MD and
TLX. `HDAE5000_CheckFileSignature` checks each part's signature when songs are
imported from floppy, using the 8-byte records `{string, offset, length}` at ROM
`0x2F8E20`, one per part in the order above: `"HK"` at +4 (LSW), `"HK"` at +0
(PMT, MD), `01 08` at +5 (SQT), `"H\0K"` (CMP, MSP, RCM), `"KN5000 SOUND RAM"`
(TM), `"TLhd"` (TLX); offsets not given are +0. (The routine's header comment in
`hdae5000/hdae5000_ui_display.s` still gives CMP as `"HK\0"`; CMP's record at
`0x2F8E38` points at `0x2F8E8C`, length 3, and the ROM bytes there are `48 00 4B`.)

**FLS record (144 bytes)**: a 16-byte name, then four 32-byte arrays indexed
by item: the directory + 1 (+16), the song + 1 (+48), and two more bytes per
item (+80, +112) whose meaning is not established. An item is set when both
its directory and song bytes are non-zero (`HDAE5000_FlsItem_IsSet`).

**The developers' names for the blocks.** The PC-link services that move these
blocks carry the developers' own names, taken from the banners of a compiled-out
debug trace (`HDAE5000_DebugTrace`, now a lone `ret`):

- block 0: `HDAE5000_PPORT_Svc04_SendInfosAboutDirBlock`,
  `HDAE5000_PPORT_Svc07_ReadDirBlockFromHd`,
  `HDAE5000_PPORT_Svc10_WriteDirBlockToHd`;
- block 1: `HDAE5000_PPORT_Svc05_SendInfosAboutFileSystemBlock`,
  `HDAE5000_PPORT_Svc08_ReadFileBlockFromHd`,
  `HDAE5000_PPORT_Svc11_WriteFileSystemBlockToHd`;
- block 2: `HDAE5000_PPORT_Svc06_SendInfosAboutFlsBlock`,
  `HDAE5000_PPORT_Svc09_ReadFlsBlockFromHd`,
  `HDAE5000_PPORT_Svc12_WriteFlsBlockToHd`.

The same trace formats lines such as `"FGB wid : %d"` for service 4, which ties
"FGB" to block 0 and "FEB" to block 1. The PC-link commands 03-06 ("Read FSB
from HD" … "Writing FSB to HD") use "FSB". The service names suggest "file
system block", i.e. block 1, but nobody has traced which blocks those commands
move.

### Files are cluster chains

`HDAE5000_HD_WriteFile` writes a part as a **new** chain. It frees the old one
if the slot is not `0xFFFFFFFF` (`HDAE5000_HD_FreeChain_Worker`). It then takes
⌈bytes / cluster bytes⌉ clusters one by one (`HDAE5000_HD_FindFreeCluster`),
writes each (`HDAE5000_HD_WriteCluster`) and links it to the previous one
(`HDAE5000_HD_FatSetEntry`). The last gets `0xFFFFFFFE`, and the first goes into
the song record's slot. `HDAE5000_HD_ReadFile` follows a chain
(`HDAE5000_HD_FatNextCluster`) to the end marker or until the byte count runs
out. `HDAE5000_HD_AppendFile` and `HDAE5000_HD_ReadFileNext` continue from where
the previous call stopped. Streamed writes go through a 0x8000-byte buffer at
`0x230F1C` (`HDAE5000_HD_WriteOpen`, `HDAE5000_HD_WriteStream`, `HDAE5000_HD_WriteClose`).

## On-Disk Layout Seen in a Formatted Disk Image

*This section comes from an analysis of a formatted 1 GB disk image made in an
earlier pass. The image is not in the repository. The reconciliation with the
firmware below is arithmetic done on this page.*

The image showed, in LBA sector numbers:

- **Sector 0**: `55 AA 55 AA`, `F3 F2 F1 F4`, then "Technics Software section
  M. Kitajima", "2.33J", "2.21", "TECHNICS KN5000", and at +0x78 the bytes
  `01 01 01 01 01 01 FF FF`.
- **Sectors 1-0xF402**: zeros on a fresh disk.
- **Sectors 0xF403-0xF41F** (29 sectors), then 32-sector runs at 0xF600,
  0xF800, … 0x10600, then 6 sectors at 0x10800: packed 76-byte records of
  26 spaces + 10 zeros + 40 × `0xFF`, and one name, "RONCO", at 0x10600 +
  0x782.

**It is the firmware's layout.** Sector 0 is filesystem sector 1: the signature
bytes agree with `HDAE5000_HD_CheckSignature`'s longs, and the six setting bytes
sit at +0x78. The earlier version of this page gave the first long as
`0x55AA55AA`, a byte-order slip. The 76-byte records are empty song records.
With 32 sectors per track and 16 heads, the head-major mapping above sends
filesystem sector 3908 (the first table sector) to cylinder 122, head 0,
sector 4. That is LBA (122 × 16) × 32 + 3 = **0xF403**. Sectors 4-32 of that
track are 29 sectors, and each further cylinder of head 0 begins
16 × 32 = 0x200 LBA sectors later. The runs therefore add up to
29 + 9 × 32 + 6 = **323**, the table-sector count. The zero LBA sectors
1-0xF402 are the FAT on head 0's tracks (all entries free) and, on the other
heads, data-area sectors that a fresh disk leaves empty. The
32-sector, 16-head geometry is inferred from the 0x200 spacing. The image's
IDENTIFY data was not recorded, so the geometry is not measured.

## Lyric Files (.TLX)

The lyrics player keeps the whole lyric file in RAM at `0x22B430`
(`HDAE5000_RAM_LyricBuffer`, 0x5000 bytes). A lyric file is a **one-track
Standard MIDI File with the chunk ids renamed**:

```
+0   "TLhd"                 (SMF "MThd")
+4   length, big-endian     must be 6
+8   format, big-endian     must be <= 0
+10  tracks, big-endian     must be <= 1
+12  division, big-endian   bit 15 (SMPTE) must be clear
+14  "TLtr"                 (SMF "MTrk")
+18  length, big-endian     end of events = length + 22
+22  events: <VarLen delta> FF <type> <VarLen length> <data> ...
```

Every event must be a meta event: a status other than `FF` is parse error
0xFFFD. `HDAE5000_Lyrics_ParseEvent` and `HDAE5000_Lyrics_PlayToPosition` act on
these types:

| Meta type | Meaning to the player |
|-----------|-----------------------|
| `0x05` (lyric) | a syllable: appended to the current line (at most 39 characters) and highlighted. CR / LF end the line, and after the third line the window scrolls |
| `0x58` (time signature) | numerator and 2^denominator stored at `0x2307A4` / `0x2307A8`, shown as `"%i/%i"` |
| `0x7E` | when the data starts with `'0'`, the rest is a chord name shown as `"Chord : %s"` |
| `0x2F` (end of track) | sets the end flag `0x230434` |

A parse error shows `"Fault : No Lyrics loaded or corrupt Data - Code %i %i %i"`.
The codes are 0xFFFF-0xFFFA in `0x2307B6`.

**The header checks are dead code.** `HDAE5000_Lyrics_CheckFile` would run
`HDAE5000_Lyrics_CheckHeaderChunk` (the five header conditions above, codes
-1 to -5) and `HDAE5000_Lyrics_CheckTrackChunk` ("TLtr", code -10). It has no
caller in this ROM (`scripts/analysis/hdae5000_reachability.py`), and neither
has the debug loader `HDAE5000_Lyrics_LoadTestFile` ("TESTTEST.TLX"). The only
check a lyric file gets is the 4-byte `"TLhd"` signature when songs are
imported from floppy (`HDAE5000_CheckFileSignature`).

**Playback.** Each frame, `HDAE5000_Frame_Handler` reads the main CPU's
sequencer position through the addresses that
`HamaFn_GetAdr_sqbtof`, `HamaFn_GetAdr_sq_beadt` and `HamaFn_GetAdr_sqsrtc` returned at boot. While a lyric
box is open (`HDAE5000_RAM_LyricBoxObj` ≠ `0xFFFFFFFF`) it computes
`sqbtof × 12 + (sq_beadt >> 3) + 2`. When `(sq_beadt >> 3) + 1` changes, it
posts event `0x01CA0004` (`EV_TICKS`) with that position to the lyric box.
`HDAE5000_LyricBoxProc` then runs `HDAE5000_Lyrics_PlayToPosition`, which scales
the position by `division / 12` (`0x230868`, set from the TLhd division by
`HDAE5000_Lyrics_ResetState`). It walks events up to that tick and updates the six
40-byte lines at `0x23A0AA` (`HDAE5000_RAM_LyricLines`), which
`HDAE5000_Lyrics_FillLines` scrolls.

**Floppy companions.** The floppy lyric list (`HDAE5000_FdLyricList_Scan`,
`HDAE5000_FdLyricList_AddTlx`) collects up to 40 `*.TLX` base names, sorted,
at `0x230884`. For each it reads the first 26 bytes of `<name>.TTX` as the
title (`0x2309F6`) and notes whether `<name>.MID` exists (`0x230E4A`).

**Not established:** what the byte stored at `0x230882` (read at "next event +
delta size + 4") is for, what meta type `0x7E` carries beyond its chord case,
and how the tempo and measure lyric objects work.

**The three main-CPU variables** (named in the maincpu source since 2026-10-03, each tree's
`shared/ram_variables.s`; the same addresses in v7, v9 and v10) are the song clock:

| firmware name | address | source name | meaning |
|---|---|---|---|
| `sq_beadt` | 0x041B | `SEQ_BEAT_TICK` | tick within the beat, 0..95 (96 per quarter note); at 96 it wraps to 0 and `sqbtof` counts up |
| `sqbtof` | 0x041C | `SEQ_BEAT_COUNT` | beats since the start (word) |
| `sqsrtc` | 0x0421 | `SEQ_TRANSPORT_STATE` | bit set: bit 0 start pending, bits 1-2 running (bit 2 gates the clock), bit 3 stop requested (the ISR then writes 16), bit 4 stopped; 0 when idle. Written whole as 0, 1, 6, 12 and 16, otherwise bit by bit |

The timer ISR (`INTTR4_CheckAltSeqEnable`, `boot/system_handlers.s`) adds 1 per tick while bit 2 of
`sqsrtc` is set; with an external MIDI clock `ClkTick_Src3ClickCheck` (`midi/midi_serial_routines.s`)
adds 4 per clock (24 clocks per quarter note). So the lyric position `sqbtof × 12 + (sq_beadt >> 3) + 2`
is in twelfths of a beat, and the frame handler's "bit 2 fell" is the song clock stopping.

### Lyric parser state (RAM)

| Address | Contents |
|---------|----------|
| `0x22B430` | the lyric file (0x5000 bytes) |
| `0x230430` | meta type of the current event |
| `0x230434` | end-of-track flag |
| `0x230436` | data length of the current event |
| `0x230438` / `0x23043C` | event position / the previous one (flag bit 0) |
| `0x23043A` | end position of the current event |
| `0x230440` | running tick (sum of deltas) |
| `0x230444` | tick of the next event |
| `0x230450` | next event's delta |
| `0x230458` | event text, NUL-terminated, at most 127 characters |
| `0x230636` | second copy of the text (flag bit 1) |
| `0x2304F2` | end of the events (TLtr length + 22) |
| `0x2307A4` / `0x2307A8` | time signature: numerator / 2^denominator |
| `0x2307B6` | parse error code |
| `0x23085E` / `0x230860` | size of the last VarLen read / its value (the delta) |
| `0x230864` | last target tick |
| `0x230868` | division / 12 |
| `0x23086C` | last position |
| `0x23A0AA` | six 40-byte text lines of the lyric window |
| `0x23A19C` | 1 once a lyric file is loaded |
| `0x23A19E` | object id of the open lyric box, `0xFFFFFFFF` when none |

## Other RAM Variables

| Address | Name | Contents |
|---------|------|----------|
| `0x200222` | `HDAE5000_RAM_AtaError` | drive error byte, tested after every disk operation |
| `0x229C32` / `0x229C34` / `0x200220` | — | cylinders / heads / sectors per track (`HDAE5000_HD_ParseIdentify`) |
| `0x229D92` | `HDAE5000_RAM_HdInitResult` | `HDAE5000_HD_Init`'s step code (0 = ready and formatted) |
| `0x229D99` / `0x229D9A` | `HDAE5000_RAM_WriteProtect` / `HDAE5000_RAM_WriteConfirm` | "WRITE PROTECTION" / "WRITE CONFIRM" settings, 0/1 |
| `0x22AA4C` | `HDAE5000_RAM_SaveOptions` | 12-byte part-selection record of the save options |
| `0x22AA5C` / `0x22AA5E` / `0x22AA60` | `HDAE5000_RAM_LbnDigitPos` / `HDAE5000_RAM_LbnDir` / `HDAE5000_RAM_LbnSong` | load-by-number entry: digit position, directory, song |
| `0x22ABE6` | `HDAE5000_RAM_DeleteOptions` | 12-byte part-selection record of the delete options |
| `0x22B2F4` | `HDAE5000_RAM_SeparateOutputMode` | 0-3 = OFF / DRUMS L/R / BASS+DRUMS MIX / BASS/DRUMS MONO |
| `0x23A08E` / `0x23A090` | `HDAE5000_RAM_DirPageBase` / `HDAE5000_RAM_FlsPageBase` | first directory / FLS of the list page |
| `0x23A092` / `0x23A094` / `0x23A096` | `HDAE5000_RAM_CurDir` / `HDAE5000_RAM_CurSong` / `HDAE5000_RAM_CurFls` | current selections |
| `0x23A1A2` | `HDAE5000_RAM_MainWorkspacePtr` | the main CPU's object table `0x027ED2` |

The old "CHS spinbox" reading of `0x22AA4C`-`0x22AA60` and the "ATA IDENTIFY
cylinders/heads" reading of `0x229D99`/`0x229D9A` were wrong.

### Calls into the main CPU

`HDAE5000_RAM_MainWorkspacePtr` holds `0x027ED2`, the main CPU's object table.
`+0x0E0A` and `+0x0E88` are the data pointers of its function tables 0x100 and
0x109. The firmware's own name tables name every offset used: 99 functions at
953 call sites (`tools/hdae5000_fn_table_check.py` in this site's repository). Examples: `+0x0100` `SendEvent`, `+0x0124` `ApPostEvent` and
`+0x050C` `GetNamingWindowID` in table 0x100, and `+0x0100` `GetAdr_sqbtof` in
table 0x109. Earlier versions of this page called the first three
"SetDisplayCell", "RegisterEventHandler" and "GetCurrentSelection". The full list is on
[HDAE5000 Homebrew — Workspace Pointer]({{ site.baseurl }}/hdae5000-homebrew/#workspace-pointer).

## PC Parallel Port Interface

The PC link (via the NEC uPD71055 PPI) is a command loop,
`HDAE5000_PPORT_CommandLoop`. The command byte *n* (packet `0x239168`, byte 0,
1-20) selects entry *n* - 1 of `HDAE5000_PPORT_CommandTable` (20 entries). Each
handler first shows its own status record, and the handlers are named after
those records: `HDAE5000_PPORT_Cmd01_SendInfosAboutHd` …
`HDAE5000_PPORT_Cmd20_SendXapFileFlash`. The filesystem commands are:

| Command | Routine | Status text |
|---------|---------|-------------|
| 03 | `HDAE5000_PPORT_Cmd03_ReadFsbFromHd` (0x2956F2) | "03>Read FSB from HD" |
| 04 | `HDAE5000_PPORT_Cmd04_SendFsbToPc` (0x29572E) | "04>Sending FSB to PC" |
| 05 | `HDAE5000_PPORT_Cmd05_RcvFsbFromPc` (0x295802) | "05>Rcv FSB from PC" |
| 06 | `HDAE5000_PPORT_Cmd06_WriteFsbToHd` (0x2958D6) | "06>Writing FSB to HD" |

The routines this page used to list for commands 03-06 (0x2959F6, 0x295D3C,
0x29605A, 0x296294) are the handlers of commands **08-11**. The 12-entry
table at `0x2953E2` holds entries 6-17 of the 20, and the old notes numbered it
from 1. The handlers call 30 PC-link services
(`HDAE5000_PPORT_Svc01_GetInfoBlockPointer` … `HDAE5000_PPORT_Svc30_MainHook053C`).
The names of services 1-25 come from the `"---[ <FunctionName> ]---"` banners
of the compiled-out debug trace.

### PPORT transfer packet (older reading, not re-verified)

The hdae lane marked the descriptive lines inside the command handlers as
"predate this name and are not re-verified". The packet layout below comes from
those lines:

```
Offset  Size  Contents
------  ----  --------
0x00    1     flags byte 1 (bitmask for regions 0-5, 7)
0x01    1     flags byte 2 (bitmask for region 8)
0x02-0x2B  42  header/padding
0x2C    36    9 region descriptors (32-bit sector address each)
```

## Routines That Were Misnamed

The old names on this page, and what the code turned out to be:

| Address | Old name | Current name |
|---------|----------|--------------|
| 0x2870D6 | `HDAE5000_FS_Init` | `HDAE5000_Lbn_ShowEntry` (load-by-number entry) |
| 0x287F55 | `HDAE5000_FS_Read_FSB` | `HDAE5000_FlsList_BuildPage` |
| 0x288295 | `HDAE5000_FS_Write_FSB` | `HDAE5000_FlsScreen_Refresh` |
| 0x289665 | `HDAE5000_FS_Buffer_Setup` | `HDAE5000_FdList_Redisplay` |
| 0x289889 | `HDAE5000_FS_Scan_Directory` | `HDAE5000_CopyToHd_Execute` |
| 0x28A2F0 | `HDAE5000_FS_Entry_Lookup` | `HDAE5000_DelOpt_ShowFlags` |
| 0x28D6D1 | `HDAE5000_File_Operation` | `HDAE5000_Lyrics_PlayToPosition` |
| 0x28DA7B | `HDAE5000_File_Save` | `HDAE5000_Lyrics_ResetState` |
| 0x28DBF8 | `HDAE5000_File_Load` | `HDAE5000_Lyrics_ReadSongInfo` |
| 0x28DE2C | `HDAE5000_File_Delete` | `HDAE5000_Lyrics_FillLines` |
| 0x28E06F | `HDAE5000_File_Rename` | `HDAE5000_Lyrics_FindEvent` |
| 0x28E187 | `HDAE5000_File_Format` | `HDAE5000_Lyrics_ParseEvent` |
| 0x28E48B | `HDAE5000_Calc_Disk_Space` | `HDAE5000_Lyrics_ReadVarLen` |
| 0x28F197 | `HDAE5000_Directory_Handler` | `HDAE5000_FdLyricList_AddTlx` |
| 0x29AE24 | `HDAE5000_File_Read` | `HDAE5000_MemCmp` |
| 0x2959F6 | `HDAE5000_Cmd03_ReadFSB` | `HDAE5000_PPORT_Cmd08_SendDataToPc` |
| 0x295D3C | `HDAE5000_Cmd04_SendFSB` | `HDAE5000_PPORT_Cmd09_SendFilesToPc` |
| 0x29605A | `HDAE5000_Cmd05_RcvFSB` | `HDAE5000_PPORT_Cmd10_RcvDataFromPc` |
| 0x296294 | `HDAE5000_Cmd06_WriteFSB` | `HDAE5000_PPORT_Cmd11_SaveMemoryToHd` |

Source: the `scripts/renaming/rename_hdae5000_*.sed` scripts in
`kn5000-roms-disasm`. `HDAE5000_Read_Table_Word`, `HDAE5000_Read_Table_Multi`,
`HDAE5000_VarInt_Encode` and `HDAE5000_VarInt_Decode` kept their names, but
they work on the lyric buffer and SMF variable-length quantities.

## Open Questions

- Which of the ten first-cluster slots of a song record belongs to which part
  (nine part types are known), and what the 10 bytes at +26 hold.
- What the FLS item bytes at +80 and +112 mean.
- Whether "FSB" names the whole table set; see [Open Questions]({{ site.baseurl }}/questions/).
- The lyric-player details listed under [Lyric Files](#lyric-files-tlx).

## Related Pages

- [HDAE5000 Hard Disk Expansion]({{ site.baseurl }}/hdae5000/) -- Original firmware documentation
- [HDAE5000 Hard Disk Interface]({{ site.baseurl }}/hdae5000-disk-interface/) -- IDE/ATA low-level protocol
- [HDAE5000 Homebrew Development]({{ site.baseurl }}/hdae5000-homebrew/) -- Writing custom extension ROMs
- [Storage Subsystem]({{ site.baseurl }}/storage-subsystem/) -- Overview of all KN5000 storage options
- [Memory Map]({{ site.baseurl }}/memory-map/) -- Full system address space
