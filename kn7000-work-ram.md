---
layout: page
title: KN7000 Work RAM Map
permalink: /kn7000-work-ram/
---

# KN7000 Work RAM Map

The KN7000's main CPU has **4 MB of work RAM at `0x50000000`** (two 16-Mbit DRAMs,
IC12/IC13 in the service manual; the reset code clears up to `0x50400000`). This page
maps it for **PROGRAM 941**, the build this project holds in full, and answers a
practical question that comes up whenever the firmware handles a picture, a song or a
setup file read from disk or SD card: *where in RAM does it go?*

The map was built twice, by two methods that did not see each other's results: once
from the code that sets RAM up (reset, `.data` copy, `.bss` clears, the allocators and
their arenas) and once from a sweep of every work-RAM address the ROM references
(4130 and 4129 distinct addresses; they differ at one). An independent verifier then
re-derived each region from the code. The scripts behind it are in the
[disassembly]({{ site.baseurl }}/kn7000-firmware/) repository, `notes/work-ram-map-probes/`;
routine names are those of `kn7000_manual.sym` (section "FILES, PICTURES, SLIDE SHOW").

> ⚠ **Build 941 only.** Another build can place things elsewhere. One calibration point
> is known: the owner's PROGRAM 893 unit shows the same song-record address
> `0x501A5920` on its [MEMORY DUMP screen]({{ site.baseurl }}/kn7000-memory-dump-screen/#what-real-hardware-has-already-confirmed),
> so the `0x501A5xxx` region at least matches. Every address below can be inspected
> on a real instrument with that screen.

## At a glance

| range                     | size      | what                                                                                 |
|---------------------------|-----------|--------------------------------------------------------------------------------------|
| `0x50000000`–`0x50007F44` | 32 KB     | interrupt stubs and `.data` (initialised globals, copied from ROM `0x487B0B78`)      |
| `0x50007F44`–`0x50180000` | 1.47 MB   | `.bss`, cleared at every reset: all firmware globals, queues, buffers, frame buffers |
| `0x50180000`–`0x50298000` | 1.1 MB    | **user memory, never cleared**: composer styles, songs, pads, slide-show pictures    |
| `0x50298000`–`0x502B8000` | 128 KB    | unused by build 941 (build 942 loads its SD plug-in here)                            |
| `0x502B8000`–`0x50380000` | 800 KB    | `INSTALL_SCRATCH`: a shared work area for file loads, installs and demos             |
| `0x50380000`–`0x503BC000` | 240 KB    | the RTOS: system area, then the memory pool the task stacks come from                |
| `0x503BB800`–`0x503FFDC0` | 280,000 B | the zlib arena (compression, and the homepage loaders' buffer)                       |

## Where an image file lands

| path                                   | reads into                                   | length / limit                                       | then                                                                                   |
|----------------------------------------|----------------------------------------------|------------------------------------------------------|----------------------------------------------------------------------------------------|
| PICTURE LOAD (floppy, SD, 3rd backend) | INSTALL_SCRATCH 0x502B8000                   | whole file; files over 0x4D800 refused (-0x6D)       | optional crop to 240 rows, then memcpy into a slide-show pool block (0x4858154C)       |
| slide-show script images (.ACT tags)   | a pool block directly (SswImageFileLoad)     | whole file, no limit but pool space                  | refused and freed if larger than 640x240                                               |
| FEATURE.PRE demo                       | .SQT at 0x502C0000; images into a demo pool  | whole files                                          | demo pool 0x502C0000+round4(SQT)..0x50380000                                           |
| debug BITMAP LOAD                      | 0x502B8000                                   | fixed 0x18000-byte read, no size check               | drawn by Draw2BpFile at (0,0)                                                          |
| homepage .HMP                          | 0x503BB810 (zlib arena, first block)         | fixed 0x4442-byte read, no size check                | 'JK' record to RAM 0x5006B5F8 and flash 0x96811000; BMP to flash 0x9681118C            |
| homepage PICTURE LOAD (.BMP)           | 0x503BB810 (zlib arena, first block)         | fixed 0x42B6-byte read                               | checked (<= 160x100, <= 8 bpp), ConvertBitmapFile, programmed to flash 0x9681118C      |

**The PICTURE LOAD import (PictureImport 0x485812E8).** 0x4D800 is the size of its
file buffer: the same immediate is the size check (0x48581327), the read length
(0x48581369) and the offset of the second work buffer, 0x502B8000 + 0x4D800 =
0x50305800 (0x485814B5, 0x485814E3). That buffer holds a JPEG decoded to 640 x 240 x 3
bytes (0x70800) when a JPEG taller than 240 rows is trimmed; JpegDecodeCrop keeps the
top, centre or bottom 240 rows and JpegEncode re-encodes them into 0x502B8000. BMPs
are cropped in place (SswBmpCropRows). The highest byte an import writes is
0x50375FFF. The read is already capped, so the size check does not prevent an
overflow; it refuses a file that would be stored cut short. Why exactly 310 KiB is not
in the code. Most likely it is the largest BMP the parser accepts at the manual's
640 x 480 maximum (8 bpp with 256 colours = 308,278 bytes) rounded up; the song event
store is also exactly 0x4D800 bytes, with no code link (`limit_arith.py` prints the
candidates). The PICTURE LOAD screens send All Notes Off when they open (SD
0x4855D148/0x4855D167, floppy 0x4852270F), which is the manual's "no sound is
produced"; that is not tied to the buffer.

**The slide-show pool.** SswPoolAlloc is a bump allocator: a block is
round4(n) + 4 bytes with its length word in front, and the payload starts at
(pool+0x18) + 4. In the main pool (base 0x502031A0, heap from 0x50203F90) the first
payload is 0x50203F94, and payloads lie in 0x50203F94..0x50297FFB (..0x50257FFB when
TgStrapProbe() != 1, which shrinks the pool by 0x40000; MAME returns 1; real hardware
unchecked: the word at 0x502031AC is 0x94E5C or 0x54E5C). USER PICTURE slot k is the
record at 0x502033D0 + k*0x20: name[16], pointer at +0x10 (0x502033E0 + k*0x20), size
at +0x14. SswPoolFree compacts, so a picture's address moves when an earlier block is
freed. Pool header: +8 base, +0xC size, +0x10 heap start, +0x14 heap size, +0x18 bump
pointer, +0x1C free bytes, +0x20/+0x24/+0x28 script and section blocks, +0x30 128
`<ACT NO=n>` pointers, +0x230 30 slot records, +0x5F0 64 named-image records, +0xDF0
heap. Nothing writes picture flash (0x57800000 is read only); pictures leave RAM only
through the slide-show save to disk. The pool is wiped by every song load from disk
(SeqActFileLoad -> SswSongActLoad).

**Script images and the FEATURE demo.** SswImageFileLoad reads straight into a pool
block, no intermediate copy. On the song route the pool holds the script text, then
the `<SLIDESHOW>` and `<ACTION>` sections, then the images in tag order. The FEATURE
demo (FeaturePreLoad, FeatureDemoSqtLoad, FeatureDemoActLoad) reads the .SQT whole to
0x502C0000 and builds its pool after it, up to 0x5037FFFF; the built-in feature demos
(StartFeatureDemo 1..10, pool 0x502B8000..0x502BFFFF) load no files.

**Debug BITMAP LOAD (DbBitmapLoadProc).** 0x18000 (96 KiB) is only a read length;
there is no size check, so a larger file is cut silently and Draw2BpFile still draws
every row the header promises, from stale RAM. It does not derive from 0x4D800. Most
likely it is 3 x 32 KiB chosen to hold a full-screen 4-bpp BMP (76,918 bytes), which is
what CaptureLcd writes in the 2-bit LCD mode (`bmp_sizes.py`).

**Homepage (.HMP and .BMP).** Both buffers come from the zlib arena 0x503BB800..
0x503FFDBF (0x445C0 = 280,000 bytes; ZArenaReset/ZArenaAlloc/ZArenaFree, 16-byte block
headers), and each homepage routine resets the arena just before allocating, so the
data always starts at 0x503BB810: 0x4442 bytes for .HMP (to 0x503BFC51), 0x42B6 for
the BMP (to 0x503BFAC5). MAME confirmed 0x503BB810 on the boot path that reprograms
the default homepage BMP (`arena_verify.lua`). 0x42B6 = 54 + 1024 + 160 x 100, the
largest 160 x 100 BMP the manual allows; 0x4442 = the 0x18C-byte 'JK' settings record
+ that BMP, a byte image of the custom-flash blob at 0x96811000 (the factory
04HPGINI.HMP is 17,474 bytes).

## Above 0x502B8000

| range                     | use                                                                              |
|---------------------------|----------------------------------------------------------------------------------|
| 0x502B8000..0x5037FFFF    | INSTALL_SCRATCH: shared, short-lived users that never run together (below)       |
| 0x50380000..0x50387FFF    | RTOS system area                                                                 |
| 0x50388000..0x503BBFFF    | RTOS memory pool, task stacks (about 0x23860 bytes used after boot in MAME)      |
| 0x503BB800..0x503FFDBF    | zlib arena (overlaps the RTOS pool's configured tail by 0x800 bytes)             |
| 0x503FFDC0..0x503FFFFF    | no reference found                                                               |

Users of INSTALL_SCRATCH: the .AST custom-data install ({0x502B8000, 0xC0000}), the
PICTURE LOAD import (file 0x502B8000..0x503057FF, JPEG crop buffer 0x50305800..
0x50375FFF), the built-in feature-demo pool 0x502B8000..0x502BFFFF and the FEATURE
demo 0x502C0000..0x5037FFFF, the SD-SOUND lists (memset 0x89E00), the style-convert
screens, the file-copy bounce buffer (0x4000-byte chunks), CmpConvLoad (0x25800
bytes), the debug BITMAP LOAD (0x18000 bytes), the song-page gather buffer, and the
custom-flash directory edit buffer 0x5037A000..0x5037FFFF.

## The map: top level

| start      | end (excl.) | size     | reset treatment                 | what                                                          |
|------------|-------------|----------|---------------------------------|---------------------------------------------------------------|
| 0x50000000 | 0x50000010  | 0x10     | stubs written via 0x90000000    | two jump stubs + 4 spare bytes                                |
| 0x50000010 | 0x50007F44  | 0x7F34   | copied from ROM 0x487B0B78      | .data (initialised globals)                                   |
| 0x50007F44 | 0x50180000  | 0x1780BC | zeroed (0x48410027..0x4841003C) | .bss: firmware globals, buffers, frame buffers, boot stack    |
| 0x50180000 | 0x50298000  | 0x118000 | never cleared                   | user memory: composer styles, songs, pads, slideshow pictures |
| 0x50298000 | 0x502B8000  | 0x20000  | zeroed (0x4841003E..0x48410053) | unused in 941 (SD plug-in RAM in 942)                         |

## The map: region by region

| start      | end (excl.) | size    | what                                                                   | evidence (CPU addresses)                                   |
|------------|-------------|---------|------------------------------------------------------------------------|------------------------------------------------------------|
| 0x50000000 | 0x50000006  | 0x6     | Jump stub `nop; jmp 0x4C03DE26` (LibIrqScheduler)                      | written via 0x90000000 at 0x48410070..0x48410096           |
| 0x50000006 | 0x5000000C  | 0x6     | Jump stub `nop; jmp 0x484D77CF` (= ROM jmp at 0x4840000A)              | 0x484100CE..0x484100F4                                     |
| 0x5000000C | 0x50000010  | 0x4     | Unreferenced (4 bytes)                                                 | no code, .data or ROM-table reference                      |
| 0x50000010 | 0x50007F44  | 0x7F34  | .data: initialised globals of every module (see note 2)                | copy loop 0x48410055..0x4841006E (len 0x7F34)              |
| 0x50007F44 | 0x50008698  | 0x754   | DSP-host vars, tone-generator (TG) globals, drum key-off scratch       | .bss start 0x48410031; lib 0x4C00BF2A                      |
| 0x50008698 | 0x50009930  | 0x1298  | TG drawbar tone records, 34 parts x 0x8C                               | lib 0x4C00A1F9..0x4C00A20E                                 |
| 0x50009930 | 0x50009F70  | 0x640   | TG drawbar / key-off / EG-ramp scratch                                 | lib 0x4C00A491, 0x4C01176F                                 |
| 0x50009F70 | 0x5000B208  | 0x1298  | TG element-map scratch, 34 x 0x8C                                      | lib 0x4C0386C0..0x4C0386C8                                 |
| 0x5000B208 | 0x5000B7E4  | 0x5DC   | TG voice-allocator scratch                                             | lib 0x4C03AE49, 0x4C03AA86                                 |
| 0x5000B7E4 | 0x50014808  | 0x9024  | 9 library message queues x 0x1004                                      | lib 0x4C01D1B8..0x4C01D216                                 |
| 0x50014808 | 0x50016030  | 0x1828  | Library message-engine globals                                         | lib 0x4C01D5FB and neighbours                              |
| 0x50016030 | 0x5001EC50  | 0x8C20  | 4 library FIFOs (0x50016030, then 3 x 0x2408)                          | lib 0x4C02458C, 0x4C0245E8                                 |
| 0x5001EC50 | 0x500214F0  | 0x28A0  | 8 MIDI receive byte FIFOs + descriptors                                | lib 0x4C024BED..0x4C024CB2                                 |
| 0x500214F0 | 0x500214F8  | 0x8     | Library vars 0x500214F0/F2/F4/F6                                       | lib 0x4C02B979                                             |
| 0x500214F8 | 0x50021CF8  | 0x800   | Boot (pre-kernel) stack, top = INITIAL_SP                              | SP set 0x4840FFF9; replaced at 0x487B8FA4; bottom inferred |
| 0x50021CF8 | 0x50021F8C  | 0x294   | 10 records x 0x42 (RAM twin of SRAM 0x840301B8 + n*0x42)               | func_48412C25 0x48412C3C..0x48412C55; count from the gap   |
| 0x50021F8C | 0x50022004  | 0x78    | Panel LED / index-switch state                                         | 0x48416515..0x48416587                                     |
| 0x50022004 | 0x5002A004  | 0x8000  | Malloc arena, 32 KB                                                    | .data 0x500006E0/E4; Malloc 0x48416625                     |
| 0x5002A004 | 0x5002A034  | 0x30    | Malloc lock id, graphics globals (draw enable 0x5002A01C)              | 0x484165D0, func_48421807                                  |
| 0x5002A034 | 0x5002C034  | 0x2000  | Draw-record arena, 8 KB, circular                                      | DrawQueue_Alloc, cmp 0x2000 at 0x48421B74                  |
| 0x5002C034 | 0x5002C044  | 0x10    | Draw-arena cursors and flags                                           | 0x48421A4F, 0x48421A55                                     |
| 0x5002C044 | 0x5003148C  | 0x5448  | Message buffers of the 4 GUI-task queues (slot table 0x5000757C)       | .data slot words 0x500075A8..0x50007658                    |
| 0x5003148C | 0x50031490  | 0x4     | Title control u16                                                      | MainTitleControl 0x4842B781                                |
| 0x50031490 | 0x50031890  | 0x400   | CLUT, 256 x u32                                                        | SetPaletteRGB 0x4842DB18, GetPaletteRGB 0x4842DB25         |
| 0x50031890 | 0x50031A64  | 0x1D4   | Resource / text-layout vars                                            | 0x4842DCF5, 0x48431697                                     |
| 0x50031A64 | 0x50031C64  | 0x200   | Mode object table (class 0xE, 0x20 entries)                            | RegisterObjectTable at 0x4843179E                          |
| 0x50031C64 | 0x50033F64  | 0x2300  | Title object table (class 0xF, 0x140 entries)                          | RegisterObjectTable at 0x484317C4                          |
| 0x50033F64 | 0x50034B64  | 0xC00   | Panel-function subscription queue, easy-set records                    | 0x48431894                                                 |
| 0x50034B64 | 0x5003A5BC  | 0x5A58  | Rhythm/style name module, style-ID queues, pattern player              | StyleIdQueueDequeue, StyleBuiltinNameResolve               |
| 0x5003A5BC | 0x5003D308  | 0x2D4C  | Chord detection and accompaniment control                              | GetChordToneList                                           |
| 0x5003D308 | 0x5003D36C  | 0x64    | Sequencer play vars (0x5003D34C = demo page base)                      | 0x4845740A, 0x484563FC                                     |
| 0x5003D36C | 0x50046B6C  | 0x9800  | Built-in demo song event pages (note 3)                                | 0x484573CE..0x484573DE; note 3                             |
| 0x50046B6C | 0x5004A5FC  | 0x3A90  | Save copy of PANEL MEMORY bank 1 (note 4)                              | 0x4845742B..0x48457466; note 4                             |
| 0x5004A5FC | 0x5004A76C  | 0x170   | Unreferenced tail of the 0x3C00 slot                                   | no reference                                               |
| 0x5004A76C | 0x5004FB68  | 0x53FC  | Sequencer engine, disk-job, Techni-Chord and style-converter vars      | 0x4845A..0x4846D code, MainStylCnvFunc                     |
| 0x5004FB68 | 0x5005FB68  | 0x10000 | Custom-flash 64 KB sector read-modify-write buffer                     | func_4847F8AD: 0x4847F91D, 0x4847F939, 0x4847F95A          |
| 0x5005FB68 | 0x500615F4  | 0x1A8C  | Custom-data / flash module state and buffers                           | 0x48481F4E, 0x48482076, 0x484821A1                         |
| 0x500615F4 | 0x50061604  | 0x10    | 16-byte block zeroed before the record scan                            | func_48482617: 0x48482623..0x48482634                      |
| 0x50061604 | 0x5006A984  | 0x9380  | Record table, stride 0x49C (note 5)                                    | func_48482764: base 0x4848278C, add 0x49C at 0x484828D3    |
| 0x5006A984 | 0x5006B4E4  | 0xB60   | Loader flag/handle, custom-data vars, MEMO LOG text                    | func_48482725, DbMemoProc                                  |
| 0x5006B4E4 | 0x5006CEF0  | 0x1A0C  | UI screen vars, panel serial, MIDI settings (note 10)                  | DbBitmapFileProc, 0x484970B2                               |
| 0x5006CEF0 | 0x500712D0  | 0x43E0  | Step/app-event buffers, load/save screens, fmm file layer              | fmmformat, SingleLoadModeFunc                              |
| 0x500712D0 | 0x500812D0  | 0x10000 | 64 KB compressed-file stream buffer (0x78 0x9C + 0xFFFE file bytes)    | 0x485330EB..0x4853310E, 0x4853363A..0x4853365D             |
| 0x500812D0 | 0x50083D72  | 0x2AA2  | Stream state, edit vars, SMF load/save, SD-card state                  | LoadSmf, SaveSmf, AcStepRecBoxProc                         |
| 0x50083D72 | 0x50091392  | 0xD620  | SD directory / favourites block (RAM working copy, 0xD620)             | FavFormat 0x4855EC37..0x4855EC7A; 0xD620 at 0x4855EB9E     |
| 0x50091392 | 0x500934F5  | 0x2163  | SD bank / playlist vars                                                | SdSndListEntryCountGet                                     |
| 0x500934F5 | 0x5009CEBC  | 0x99C7  | SD sound / audio list buffers (0x3E70 + 0x7CE + 0x5388)                | func_4857BE97: 0x4857BE9E..0x4857BEC9                      |
| 0x5009CEBC | 0x5009E724  | 0x1868  | Slideshow screens: image-name list (60 x 0x50), vars                   | AcSswImgListProc                                           |
| 0x5009E724 | 0x500A04C4  | 0x1DA0  | DSP host: DMA interface, parameter blocks, effect select               | DspManagerInit 0x48405E7B..0x48405F2D                      |
| 0x500A04C4 | 0x500AD37C  | 0xCEB8  | 10 DSP unit state structs x 0x14AC                                     | DspManagerInit 0x48405E2E..0x48405E6C                      |
| 0x500AD37C | 0x500AD5A8  | 0x22C   | errno, sound-command stream ring                                       | SndCmdStreamWrite                                          |
| 0x500AD5A8 | 0x500D28AC  | 0x25304 | Tone-generator driver tables (library), note 6                         | lib TG code; see note 6                                    |
| 0x500D28AC | 0x500D2B10  | 0x264   | Library table (loop bound 0x500D2B10)                                  | lib 0x4C01D5FB, 0x4C01F880..0x4C01F8C2                     |
| 0x500D2B10 | 0x500D35B8  | 0xAA8   | RAM copy of custom-flash settings 0x96804000..0x96804AA4               | lib 0x4C024033 (jump table 0x4858D794), 0x4C02404D..       |
| 0x500D35B8 | 0x500D407C  | 0xAC4   | Library/kernel vars (ms counter 0x500D3C58), focus ids, GroupBox table | KernelTickHandler 0x4C02BB0A, func_484141E0, GroupBoxProc  |
| 0x500D407C | 0x500D4080  | 0x4     | Pointer to picture plane 2                                             | 0x4842181A..0x48421820                                     |
| 0x500D4080 | 0x500F9880  | 0x25800 | Frame buffer, 640 x 240 x 8 bpp                                        | 0x4842182B, 0x4842183F; LcdOut 0x48414D71                  |
| 0x500F9880 | 0x5011F080  | 0x25800 | PICTURE_PLANE2, 640 x 240                                              | LcdOut 0x48414D7A                                          |
| 0x5011F080 | 0x5011F880  | 0x800   | Unreferenced (2 KB)                                                    | no reference; no MAME boot write                           |
| 0x5011F880 | 0x5011FAAC  | 0x22C   | Draw-ring, change-rectangle, AP-timer vars                             | 0x48421A28..0x48421A43, DrawRing_Post                      |
| 0x5011FAAC | 0x50122AAC  | 0x3000  | Object/class registry, 0x300 x 0x10                                    | 0x4842949F..0x484294A6                                     |
| 0x50122AAC | 0x50122CAC  | 0x200   | RGB565 palette, 256 x u16 (used by LcdOut)                             | 0x48414DA4                                                 |
| 0x50122CAC | 0x50122E28  | 0x17C   | Colour-mode palette, font table pointer, style view                    | kn7000_manual.sym                                          |
| 0x50122E28 | 0x50148628  | 0x25800 | Backup of MEM_STYLE_AREA, taken before a style conversion              | 0x4847A6E8, 0x48437EC3 (copy), 0x48437EDE (restore)        |
| 0x50148628 | 0x50149628  | 0x1000  | Rhythm pattern-scan tables, 2 x 0x800                                  | memset 0x800 at 0x4843301A, 0x48439439                     |
| 0x50149628 | 0x50149850  | 0x228   | Tempo / clock blocks, MIDI sync, VFS vars                              | .data 0x50007A40 = 0x50149730                              |
| 0x50149850 | 0x5014AD68  | 0x1518  | VFS file control blocks, 10 x 0x21C                                    | func_4846E0DA 0x4846E0EB..0x4846E13C                       |
| 0x5014AD68 | 0x5014DFE0  | 0x3278  | Floppy/VFS find state, directory buffers (0x1C00 at 0x5014AD70, ...)   | _findfirst/_findnext                                       |
| 0x5014DFE0 | 0x50150A34  | 0x2A54  | Style-converter buffer (0x2800) and vars                               | StylCnvModlTtlFunc                                         |
| 0x50150A34 | 0x501523E4  | 0x19B0  | Panel LED shadows, MIDI serial state, 2 ms time base, lyrics vars      | PanelEventPost, MidiSerialInit                             |
| 0x501523E4 | 0x501605F4  | 0xE210  | LZSS encoder trees, N = 0x2000 (window, dad, lson, rson)               | InitTree 0x4853397B..0x485339A3; 0x485339AB                |
| 0x501605F4 | 0x501605F8  | 0x4     | LZSS match position / length                                           | 0x48533A90, 0x485339E2                                     |
| 0x501605F8 | 0x50160608  | 0x10    | Second-allocator sentinel (arena 0x503BB800, note 9)                   | 0x485340BE..0x48534111                                     |
| 0x50160608 | 0x50160E98  | 0x890   | Sequencer edit vars, SD/disk driver state 0x50160644, playlist header  | AcStepRecBoxProc, DiskInit, SdWorkerCmdHandler             |
| 0x50160E98 | 0x50172A50  | 0x11BB8 | SD playlist / audio-list database                                      | SdPlaylistDbClear 0x4854CB1B..0x4854CBB3                   |
| 0x50172A50 | 0x5017317C  | 0x72C   | Slideshow / third-backend vars (pool header ptr 0x50172C90)            | 0x4857F0B5, 0x4857F154                                     |
| 0x5017317C | 0x5017397C  | 0x800   | 2 KB read buffer of the third fmm backend                              | 0x48584185, 0x48584265, 0x4858428F                         |
| 0x5017397C | 0x50174868  | 0xEEC   | JPEG decoder state and Huffman tables                                  | func_4840D402, func_4840D7BA                               |
| 0x50174868 | 0x501749E8  | 0x180   | JPEG 8x8 sample blocks, 6 x 0x40                                       | ROM table 0x487390C0..0x487390EC; 0x48486123               |
| 0x501749E8 | 0x50180000  | 0xB618  | Unreferenced end of .bss                                               | no reference; no MAME boot write                           |
| 0x50180000 | 0x501A5800  | 0x25800 | MEM_STYLE_AREA: COMPOSER (MEMORY) styles, 'TCMP' container             | 0x4843B160..0x4843B16E, 0x484355C8, 0x4843A59D..0x4843A5A5 |
| 0x501A5800 | 0x501AB9A0  | 0x61A0  | 11 song records x 0x8E0                                                | Rec8E0TablePtr 0x48456E49..0x48456E5D                      |
| 0x501AB9A0 | 0x501F91A0  | 0x4D800 | Song event-page store, 0x4D8 pages x 0x100                             | 0x4845641B..0x48456425, 0x48456E94..0x48456EA2             |
| 0x501F91A0 | 0x502031A0  | 0xA000  | PERFORMANCE PAD user memory, 'TPAD' container                          | 0x4843217A..0x484321C2; 0x48437C5C..0x48437C69             |
| 0x502031A0 | 0x50297FFC  | 0x94E5C | Slideshow picture pool (note 7)                                        | 0x4857F0C1..0x4857F147                                     |
| 0x50297FFC | 0x50298000  | 0x4     | Unused (0x50297FFC is only the pool end constant)                      | 0x4857F0E8, 0x4857F104                                     |
| 0x50298000 | 0x502B8000  | 0x20000 | Unreferenced in 941, zeroed at reset (942: plug-in RAM, note 8)        | clear 0x4841003E..0x48410053 only                          |

## Notes on the map

**1. How reset sets RAM up** (read from 0x4840FF7E..0x48410156):
- SP is set to 0x50021CF8 (0x4840FFF9).
- `.bss` 0x50007F44..0x50180000 is zeroed (0x48410027..0x4841003C).
- 0x50298000..0x50400000 is zeroed (0x4841003E..0x48410053). This covers INSTALL_SCRATCH and the RTOS area.
- `.data` is copied (0x48410055..0x4841006E).
- The two stubs are written through 0x90000000 (0x48410070..0x484100F4).
- The block loader 0x484D7A40 copies only the library image to 0x4C000000 and 3 bytes to 0x4C03FFF0. Nothing else is copied into work RAM.
- The kernel then switches SP to 0x50381408 (0x487B8FA4). Task stacks come from the RTOS pool 0x50388000..0x503BBFFF (lib 0x4C03D1DC -> 0x4C03CC89).

**Retention.** 0x50180000..0x50298000 is never cleared. Its owners validate their data and load factory data only when the check fails (pads: 0x48437C70 chooses 0x484321D4 or 0x4843217A). The service manual lists SEQUENCER, COMPOSER (MEMORY contents) and PERFORMANCE PADS as kept "about 80 minutes" (service manual, memory-backup table). That matches song records and pages, 'TCMP' and 'TPAD'; the DRAM mechanism is inferred. RAM is 4 MB: the clear ends at 0x50400000, and the parts list has IC12/IC13 as two 16-Mbit DRAMs (service manual parts list).

**2. `.data` contents** (ROM image 0x487B0B78; values printed by `notes/work-ram-map-probes/rom_facts.py`):
- Malloc control 0x500006E0..0x500006EB: cursor 0x50022004, remaining 0x8000, free list.
- The 4 GUI-task queue slots at 0x5000757C (0x38 bytes each). Their buffer pointers run from 0x5002C044 to 0x50031474.
- The demo-song stream tables 0x50000C20, 0x50000C50 and 0x50000C80.
- Pointer words: 0x500058B8 = 0x502B8000, 0x50007A40 = 0x50149730, 0x50007DC0 = 0x50060DA4.
- The finer split of `.data` into module variables is not in this note; `notes/work-ram-map-probes/scan_ramrefs.py` in the disassembly repository produces the reference census it can be built from.

**3. Built-in demo song** (0x484573A4..0x48457403):
- 0x4853375D is zlib 1.0.4 `uncompress`. It calls inflateInit with version string 0x48664864 and inflate with Z_FINISH, and expects Z_STREAM_END.
- For demo n (clamped to 1..12 at 0x48457393), it inflates three ROM streams:
  - into song record 0 (0x501A5800, 0x8E0 bytes);
  - into 0x5003D36C (0x9800 bytes = 0x98 pages of 0x100);
  - into battery SRAM 0x84000824 (0x3A90 bytes).
- It then stores 0x5003D36C in 0x5003D34C. The page accessor uses that base instead of 0x501AB9A0 when the mode byte is 3 (0x484563F2..0x4845640E).

**4. 0x50046B6C**:
- 0x48457426 does memcpy(0x50046B6C, 0x84000824, 0x3A90), and 0x4845744B copies it back. The pointer and length come from lib 0x4C021A4E and 0x4C021ADE.
- 0x84000824 + 0x3A90 is PANEL MEMORY bank 1 in the battery SRAM (0x10 + 8 x 0x750; kn7000_manual.sym ~2426).
- The sequencer saves it at 0x48545FCE and restores it at 0x48546191 / 0x485462D8. Inferred: this keeps the user's bank 1 while a demo's own bank is loaded there.
- The slot is 0x3C00 bytes; its last 0x170 bytes are unreferenced.

**5. Record table 0x50061604**:
- Records are 0x49C bytes (0x4848278C, 0x484828D3, 0x48482979). They are read by the VFS block read 0x4846DA31 from handle 0x5006A988, which is opened at 0x4848335C (VFS open 0x4846D800, "rb", name/config buffer 0x50060DA4).
- The count is the u16 at 0x50007BA2, taken from big-endian header bytes (0x4847FF9B..0x4847FFBD, 0x48481D80..0x48481D8F). No clamp was found in the code read.
- 32 x 0x49C = 0x9380 fills the span exactly, so 32 is the implied maximum (inferred).
- Which file this is: unknown.

**6. Tone-generator tables** (library), each from 0x500AD5A8:
- 34 x 0x10C glide/repeat-note state;
- 128 x 0xB4 voice records (0x500AF940);
- 34 x 0x54C part records (0x500B5340);
- master globals (0x500C0758) and SOUND EDIT records;
- 128 x 0x8E local-edit shadows (0x500C1183);
- 128 x 0x84 register shadows (0x500CA0B0);
- the TG-enable gate (0x500CE380);
- 34 x 0x130 part tone blocks (0x500CE404);
- voice-allocator lists and masks (0x500D0C64..0x500D28AC).

Each gap between referenced bases equals count x stride. The strides come from the code and from kn7000_manual.sym.

**7. Slideshow pool**:
- Size: TgStrapProbe (0x484D7713) returns 1 only when bits 0x02 and 0x04 of 0x98070000 are both set; it returns 2 when 0x04 is clear and 3 when 0x02 is clear (no TG). With 1, the test at 0x4857F0CD..0x4857F0DF is constant-false and the pool gets the full 0x94E5C bytes (0x4857F0FD). Any other value takes 0x4857F0E1, which subtracts 0x40000: the pool is then 0x54E5C bytes and ends at 0x50257FFC.
- Init 0x4857F116 zeroes the pool and writes a header at the base: +8 base, +0xC size, +0x10/+0x18 heap start = base + 0xDF0, +0x14/+0x1C free bytes.
- It runs through the wrappers 0x4857EDAA, 0x4857EE02 and 0x4857EE8D (callers include 0x484579AE and 0x4851E2A8). Whether it runs at power-on, and so whether pictures survive a power cycle, is unknown. The service manual's retention list does not mention pictures.

**8. 0x50298000..0x502B8000**:
- In 941 its only reference is the reset clear. A raw scan of both 941 ROMs found 106 words with values in this range. Only 0x4841004A is a decoded operand. The other 105 are 21 instruction overlaps, 22 data bytes in the program data area and 62 in the table ROM; none forms a pointer table.
- The 40 s idle MAME boot made no writes there (ramboot log).
- Program 942 clears the same span at reset. Its resident plug-in then copies its `.data` to 0x50298000..0x50299498 and clears `.bss` to 0x50299EE0 (table.s func_483E803E). It loads BASEEXT.XAP, at most 0x1D000 bytes, at 0x5029B000; 0x5029B000 + 0x1D000 = 0x502B8000 exactly.

**9. Second allocator**:
- The sentinel is in `.bss` at 0x501605F8. The arena is 0x503BB800, 0x445C0 bytes, so it lies above the asked range.
- Allocation is first fit and returns block + 0x10.
- uncompress, the .HMP load and the homepage BMP load each re-initialise the arena first. Their buffers therefore start at 0x503BB810: 0x4442 bytes for .HMP, 0x42B6 for the BMP.
- The arena overlaps the RTOS pool tail 0x503BB800..0x503BBFFF.

**10. UI variables used by the other questions**:
- 0x5006B52C: BITMAP LOAD index.
- 0x5006B52E: BITMAP LOAD file name.
- 0x5006B5F8: homepage settings record (0x18C bytes).
- 0x5006B798: .HMP buffer pointer (written at 0x484970B2).

**11. Read versus named.** The verifier re-read the boot code, the allocators, every buffer bound and the TG, DSP, LZSS, zlib, JPEG, pool, MEM_STYLE, TPAD and song code cited above. For the small variable clusters, the owner is named only from the functions that reference them; both lanes agree on those names. The two lanes' censuses match: 4130 vs 4129 addresses, differing only at 0x5004AD64.

## Spans that remain unexplained

| start      | end (excl.) | size    | what is known                                                                           |
|------------|-------------|---------|-----------------------------------------------------------------------------------------|
| 0x5000000C | 0x50000010  | 0x4     | after the two stubs; no reference; no MAME boot write                                   |
| 0x500214F8 | 0x50021CF8  | 0x800   | boot stack by position below INITIAL_SP; bottom inferred; MAME deepest write 0x50021C98 |
| 0x5004A5FC | 0x5004A76C  | 0x170   | tail of the 0x3C00 slot holding the 0x3A90 PANEL MEMORY copy; no reference              |
| 0x5011F080 | 0x5011F880  | 0x800   | after PICTURE_PLANE2; no reference; no MAME boot write                                  |
| 0x501749E8 | 0x50180000  | 0xB618  | end of .bss after the JPEG blocks; no reference; no MAME boot write                     |
| 0x50297FFC | 0x50298000  | 0x4     | past the pool end constant; no MAME boot write                                          |
| 0x50298000 | 0x502B8000  | 0x20000 | only the reset clear touches it in 941; no MAME boot write                              |

"No MAME boot write" covers only a 40 s idle boot. SD, slideshow, demo and install paths were not exercised at runtime.

## Open questions

- Which value TgStrapProbe returns on real hardware (main pool 0x94E5C or 0x54E5C
  bytes); read the u32 at 0x502031AC on a v1.6 unit.
- Whether 0x50180000..0x50297FFF (songs, styles, pads, pictures) survives power-off
  for the "about 80 minutes" the service manual gives for the sequencer data; the RAM
  is DRAM, so the mechanism is not visible in the code.
- What keeps the keyboard silent for the whole time the PICTURE LOAD screen is shown
  (only the open-time All Notes Off was traced).

## Related

- [Display Subsystem]({{ site.baseurl }}/kn7000-display-subsystem/) — the frame buffer and picture plane at `0x500D4080` / `0x500F9880`, and the BMP routines the picture loaders use
- [Storage & File System]({{ site.baseurl }}/kn7000-storage-subsystem/#the-fmm-file-layer) — the `fmm` file calls every loader on this page goes through
- [Sequencer]({{ site.baseurl }}/kn7000-sequencer/) — the song records and the song event store
- [MEMORY DUMP Screen]({{ site.baseurl }}/kn7000-memory-dump-screen/) — how to look at any of these addresses on a real instrument

