---
layout: page
title: KN7000 Wave ROM Format
permalink: /kn7000-wave-rom-format/
---

# KN7000 Wave ROM Format

The SX-KN7000's PCM samples live in four 128-Mbit (16 MiB) mask ROMs, two per tone generator. They
were read on the owner's instrument in October 2026 (see
[Expansion Bus & Wave-ROM Dump]({{ site.baseurl }}/kn7000-expansion-and-wave-dump/) and the
[ROM dumper]({{ site.baseurl }}/kn7000-rom-dumper/)). This page describes what is in them. Since
2026-10-29 the disassembly rebuilds all four chips byte for byte from source,
[`kn7000/src/wave/`](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/kn7000/src/wave),
checked by `make -C kn7000 verify-wave`, which is part of `make gate-kn7000`.

The full notes, with every probe and its result, are
[`kn7000/notes/wave-roms-2026-10-29.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/wave-roms-2026-10-29.md);
the probes are in
[`kn7000/notes/wave-roms-probes/`](https://github.com/ArqueologiaDigital/technics-roms-disasm/tree/main/kn7000/notes/wave-roms-probes),
and the read port and the service test in
[`kn7000/notes/wave-rom-port.md`](https://github.com/ArqueologiaDigital/technics-roms-disasm/blob/main/kn7000/notes/wave-rom-port.md).

## The chips and their streams

| chip  | MAME name            | tone generator     | half | SHA-1                                      |
|-------|----------------------|--------------------|------|--------------------------------------------|
| IC203 | `c3cbqd000002.ic203` | MAIN, `0x98050000` | Y    | `f2d01ffd020c39a3f5b9d6c3275b1855c5a3d1a6` |
| IC204 | `c3cbqd000001.ic204` | MAIN, `0x98050000` | X    | `f6da330c14cd3bdfc7c19092bd20d188e3ef0600` |
| IC207 | `c3cbqd000004.ic207` | SUB, `0x98040000`  | Y    | `729bb2dd6aebd2932de6960363a554b89ffc171a` |
| IC208 | `c3cbqd000003.ic208` | SUB, `0x98040000`  | X    | `fb48cbc5334f5221ea882d63a58a22f9466e78c7` |

- **The names MAIN and SUB are the firmware's.** Its WAVE ROM TEST page paints IC203's result
  beside the label "MAIN TG" and reads it through the port at `0x98050000`. That is the opposite of
  the "master = `0x98040000`" reading on the
  [Sound Subsystem]({{ site.baseurl }}/kn7000-sound-subsystem/#tone-generators-ic201-ic205) page,
  which comes from the symbol `ToneGenWriteMain`. No hardware capture has settled which is right.
- **Y and X.** The Y and X ROMs of a pair are one stream of 16-bit samples, low byte first: word i
  of Y, then word i of X. The chip fetches two neighbouring samples at once, which is how this was
  found (the correlation of neighbouring samples, `wave-analysis/xy.py`).
- **The images are private.** They are pass 3 of the ROM dumper on the owner's unit. The build
  joins the git-ignored chips into one stream per tone generator (`tools/wave_pair.py join`),
  assembles the source, cuts the result back into four chips (`split`) and compares each with its
  SHA-1. From nothing, that takes about 8 s.

## Layout of a stream

A stream is 16 pages of 0x100000 words, 2 MiB each; a page is 1 MiB of each chip. Every page is
self-contained:

```
page word 0        directory: N entries of 4 words (A, P, B, Q)
          4N       parameter records, one per entry, in entry order, each 32-bit aligned (pad 0)
          ...      zero fill to the next 16-word boundary
          16*B0    recordings (PCM), each starting on a 16-word boundary, in B order
          ...      0xFFFF fill to the page end
```

`layout_probe.py` checks eight rules on all 32 pages and all 3,974 directory entries, and every
one holds: entry 0's A is 4 x N; the records follow the directory in entry order; the first
recording starts at the first 16-word boundary after them; the 0xFFFF fill is only at the end of a
page; P bits 15:12 are always 1; each record starts with its entry's B; Q is the record's first
parameter word; and the code field (below) is non-zero only in 8-bit entries.

### Directory entry

| word | name | meaning                                                                                                 |
|------|------|---------------------------------------------------------------------------------------------------------|
| 4j   | A    | the entry's parameter record, in words from the page start                                              |
| 4j+1 | P    | `0x1000 \| E<<4 \| F<<3 \| K`                                                                           |
|      | E    | bits 11:4, the pitch exponent: a period of 2^(E-9) samples sounds at the note (inferred from emulation) |
|      | F    | bit 3 (`PCM8`): two signed 8-bit samples per word, low byte first                                       |
|      | K    | bits 2:0 (`GRAN_16` .. `GRAN_2048`): segments and loops count in granules of L = 2^(K+4) samples        |
|      | -    | bit 12 (`PFMT`): set in every entry; meaning unknown                                                    |
| 4j+2 | B    | the recording's first sample, in units of 16 words (32 bytes) from the page start                       |
| 4j+3 | Q    | a copy of the record's first parameter word                                                             |

The evidence for F: of 937 recordings whose entry has it set, 929 read better as 8-bit samples;
of 2,721 with it clear, 4 do (`format_probe.py`). For K: with L = 2^(K+4), 945 of 954 marked
loops repeat exactly; with L/2 or 2L, 1 of 1,887 (`loop_probe.py`).

E is 13 to 19 in every entry but one, main page 0x00 entry 0x0AF (`Main_P00_E0AF`), whose P is
`0x12fa`. That is its neighbours' value with bit 9 also set, so bit 9 may be a flag of its own.

### Parameter record

The record at A is B again, then parameter words `[flags:2][code:6][value:8]`, up to the first
word with bit 15 set:

| value / flags                                | meaning                                                                        |
|----------------------------------------------|--------------------------------------------------------------------------------|
| value >= 0x80                                | a segment of (256 - value) granules, laid out from the first sample            |
| flag `LOOP_START` (0x4000) on a segment      | the loop starts at the segment's end                                           |
| flag `LOOP_END` (0x8000) on a segment        | the loop ends at the segment's end, and so does the record                     |
| value < 0x80, descending multiples of 8      | the "split list" (values 8..104); meaning unknown                              |
| `REC_END` (0xc000), value 0 or a split value | ends a record that has no `LOOP_END`                                           |
| code, bits 13:8                              | non-zero only in 8-bit entries; in emulation it scales a segment by 2^(-b/2)   |

The code's gain law is a fit to emulation, not derived. Without an explicit loop, the emulation
model loops the single granule after the last segment; that has not been checked on hardware.

## How the firmware selects a recording

The firmware never sends a ROM address, a loop or a length. It writes a 20-bit **select** into the
voice's shadow register word `+0x40`, which reaches the tone generator as register plane `0x1C`:
bits 19:12 are the page, bits 11:0 the directory entry. The tone generator reads the directory,
the record and the samples itself.

- `TgElemNoteOnStd` (library `0x4C030A98`) takes the entry from the tone zone's halfword `+2`
  (`and 0x0fff`).
- `TgVoiceRouteFieldSet` (`0x4C037C16`) takes the page from the zone's halfword `+0` (low byte,
  shifted left 12). Its mode argument can move the page: on hardware subtypes 1 and 2 (the
  owner's unit reads subtype 2) the page is used as it is; subtypes 3 and 5 map it through small
  tables in the program image; modes 1 to 4 add 0x20 or 0x30, the expansion board's pages.

So select 0x0A00F names `Main_P0A_E00F` on the MAIN tone generator and `Sub_P0A_E00F` on the SUB
one. In a kn7000_mame trace all 556 traced voice note-ons named an internal page and an existing
entry. A static check now covers every tone, not only the traced ones: each of the 5,215 zones in
the table ROM's internal voice archive names an existing directory entry (see
[Table ROM: the 'JK' voice archive]({{ site.baseurl }}/kn7000-table-rom/#the-jk-internal-voice-archive)).
No CPU reads these ROMs except the service-mode checksum.

## Per page

MAIN tone generator (IC203 + IC204):

| page | entries | 8-bit | recordings | record words | first recording (word) | end fill (words) |
|------|---------|-------|------------|--------------|------------------------|------------------|
| 0x00 | 181     | 67    | 160        | 3,907        | 0x1220                 | 4,416            |
| 0x01 | 130     | 0     | 90         | 1,106        | 0x660                  | 192              |
| 0x02 | 119     | 75    | 103        | 1,737        | 0x8b0                  | 384              |
| 0x03 | 138     | 28    | 96         | 1,150        | 0x6b0                  | 64               |
| 0x04 | 70      | 12    | 68         | 477          | 0x300                  | 64               |
| 0x05 | 117     | 56    | 108        | 1,772        | 0x8c0                  | 640              |
| 0x06 | 1,132   | 144   | 1,096      | 7,246        | 0x2e00                 | 768              |
| 0x07 | 36      | 9     | 36         | 300          | 0x1c0                  | 0                |
| 0x08 | 92      | 39    | 83         | 4,316        | 0x1250                 | 64               |
| 0x09 | 27      | 1     | 27         | 172          | 0x120                  | 2,368            |
| 0x0A | 42      | 7     | 42         | 931          | 0x450                  | 64               |
| 0x0B | 45      | 24    | 45         | 2,389        | 0xa10                  | 44,480           |
| 0x0C | 44      | 16    | 44         | 1,803        | 0x7c0                  | 9,728            |
| 0x0D | 174     | 0     | 174        | 923          | 0x660                  | 2,304            |
| 0x0E | 57      | 0     | 57         | 345          | 0x240                  | 12,224           |
| 0x0F | 22      | 0     | 22         | 107          | 0xd0                   | 7,552            |
| all  | 2,426   | 478   | 2,251      | 28,681       |                        | 85,312           |

SUB tone generator (IC207 + IC208):

| page | entries | 8-bit | recordings | record words | first recording (word) | end fill (words) |
|------|---------|-------|------------|--------------|------------------------|------------------|
| 0x00 | 208     | 99    | 177        | 5,775        | 0x19d0                 | 384              |
| 0x01 | 198     | 67    | 161        | 2,800        | 0xe10                  | 448              |
| 0x02 | 37      | 9     | 31         | 677          | 0x340                  | 448              |
| 0x03 | 110     | 23    | 70         | 1,488        | 0x790                  | 128              |
| 0x04 | 139     | 27    | 139        | 1,653        | 0x8b0                  | 448              |
| 0x05 | 111     | 43    | 111        | 2,121        | 0xa10                  | 192              |
| 0x06 | 109     | 79    | 109        | 4,262        | 0x1260                 | 0                |
| 0x07 | 29      | 0     | 29         | 128          | 0x100                  | 2,240            |
| 0x08 | 44      | 13    | 44         | 2,519        | 0xa90                  | 6,976            |
| 0x09 | 170     | 100   | 167        | 7,782        | 0x2110                 | 192              |
| 0x0A | 45      | 7     | 45         | 658          | 0x350                  | 1,216            |
| 0x0B | 36      | 22    | 36         | 2,228        | 0x950                  | 149,120          |
| 0x0C | 46      | 16    | 46         | 2,028        | 0x8b0                  | 2,496            |
| 0x0D | 202     | 7     | 202        | 1,229        | 0x800                  | 3,008            |
| 0x0E | 36      | 0     | 36         | 159          | 0x130                  | 45,632           |
| 0x0F | 28      | 9     | 28         | 716          | 0x340                  | 15,360           |
| all  | 1,548   | 521   | 1,431      | 36,223       |                        | 228,288          |

Several entries can play the same recording, so a page has fewer recordings than entries. Main
page 0x06, with 1,132 entries of about 950 words each, is probably the drum and percussion page;
that is an inference, not checked against the firmware's kit tables.

## The source

| file                       | what it is                                                                                                                   |
|----------------------------|------------------------------------------------------------------------------------------------------------------------------|
| `src/wave/wave_format.inc` | the field constants (`PFMT`, `PCM8`, `GRAN_*`, `LOOP_START`, `LOOP_END`, `REC_END`) with evidence                            |
| `src/wave/main.s`          | the MAIN stream: per page `Main_P00`, entries `Main_P00_E000`, records `Main_P00_R000`, recordings `Main_P00_W000` and so on |
| `src/wave/sub.s`           | the SUB stream, the same way (`Sub_P00` ...)                                                                                 |
| `tools/gen_wave_s.py`      | wrote the two sources from the reference streams, re-checking the layout rules (`make wave-src`)                             |
| `tools/wave_pair.py`       | chips to stream (`join`) and back (`split`)                                                                                  |

A directory entry is one line of typed fields with symbolic pointers:

```
Main_P00_E003:	.word	(Main_P00_R003 - Main_P00) / 2, PFMT | 18<<4 | GRAN_512, (Main_P00_W003 - Main_P00) / 32, 256-2
```

A recording is a labelled item named after the lowest entry that plays it; its comment gives the
sample count, the format and every entry that plays it. Since 2026-10-30 (lane media-files) each one
is a WAV file, and the source `.incbin`s the raw item that `pcm_wav.py` makes from it:

```
Main_P00_W000:	.incbin	"build/wav_pcm/main/Main_P00_W000.pcm", 0, 1024	; census: generated -- ../scripts/build/pcm_wav.py, from wav/main/Main_P00_W000_Sine.wav: 512 16-bit samples, entry 000
```

The data-incbin census reads 3,682 generated items (66,319,584 bytes), all of them from media, and
0 opaque and 0 generic for this tree (snapshot `docs/coverage/data-incbin-2026-10-30-04`, as in `-03`; until
`-02` the recordings were `.incbin_range`s of the reference stream, declared `census: opaque -- pcm`).
The other 789,280 bytes of the 64 MiB are directories, records, alignment and fill, all typed. For
this format `kn7asm.py` gained the operators `/`, `<<`, `>>`, `|` and `&`.

## Encoding and the WAV files

`make -C kn7000 wave-wav` writes every recording as a mono WAV file into `kn7000/wav/main/` and
`kn7000/wav/sub/` (git-ignored: they are the dump's bytes), from the git-ignored reference streams,
and never overwrites a WAV that is there; `make -C kn7000 verify-wave` builds the four chips from
them. The committed manifests `src/wave/main_wav.tsv` and `src/wave/sub_wav.tsv` hold one row per
recording (offsets, bit depth, rate, file name, unity note, loops, comment), no sample data. How to
play and edit them, for all models, is on [Media Files]({{ site.baseurl }}/media-files/).

| field       | value                                                        | evidence                                                                                                       |
|-------------|--------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| 16-bit      | two's complement, little-endian (the stream's words)         | `pcm_encoding_probe.py`: s16le has the fewest full-scale jumps in 2,632 of 2,723; the other 91 tie (silence)   |
| 8-bit       | two's complement, low byte first, two per word               | the same probe: s8 wins in 925 of 959, the rest tie; byte correlation > 0.5 in 917 of 959 (16-bit: 0 of 2,720) |
| companding  | none found; samples are written as stored (linear)           | not proven: the 8-bit segments have a gain code that the WAV does not apply                                    |
| sample rate | 44,100 Hz in the header, **nominal**                         | the rate at which the tone generator steps one source sample per output sample (output 44.1 kHz)               |
| unity note  | `96 + 12 (log2(44100 / 2093.0045) - (E - 9))`                | the pitch law fitted in emulation (kn7000_mame `notes/g13-waves-2026-10-20`, 478 of 556 voices): an inference  |
| loops       | `smpl` loop = the record's LOOP_START..LOOP_END segment ends | `wave-roms-probes/loop_probe.py`: 945 of 954 marked loops repeat; end written inclusive (end sample - 1)       |

(The probes are `notes/media-files-probes/pcm_encoding_probe.py` and
`kn7000/notes/wave-roms-probes/loop_probe.py` in the disassembly repository.)

- The WAV `data` chunk of a 16-bit recording is the stream's bytes unchanged; an 8-bit one's is each
  byte XOR 0x80, because WAV 8-bit PCM is unsigned. `scripts/build/pcm_wav.py verify` round-trips
  2,251 of 2,251 (MAIN) and 1,431 of 1,431 (SUB).
- The `smpl` chunk carries the unity note always and the loop where the record marks one: 837
  recordings (477 MAIN, 360 SUB, counted from the manifests). 90 loops end past their item (an entry
  can play into the next recording's bytes); the WAV leaves those out and says so in its comment.
  `Main_P00_W0AF` has no unity note: its entry's P word reads as E = 47 (see `Main_P00_E0AF` above).
- The unity note leaves out each zone's tuning, which the firmware folds into the pitch it writes,
  so it is only near.
- A recording whose audio the KN5000's IC307 also holds gets the IC307 name too
  (`Main_P00_W000_Sine.wav`): 1,118 of 3,682, from `src/wave/ic307_names.tsv`.

## Open questions

- **The page order.** The pages are self-contained, so a permutation of whole pages would still
  parse. Only the firmware's tone tables or a listening test can rule it out. (A permutation of
  32 KB banks inside a page is now unlikely, since the layout rules and the loop test hold
  everywhere.)
- **The split list**, the values below 0x80: it does not change the pitch in emulation. Perhaps the
  interpolator's or a filter's switch points by pitch.
- **P bit 12**, always set, and **bit 9** of `Main_P00_E0AF`.
- **The 8-bit gain law.** `2^(-(code&7)/2)` is a fit; the code's high three bits, and the code on
  `REC_END` words, are unexplained. A line-out recording of an 8-bit sound would settle it.
- **What plays after the loop.** Many recordings carry data past their loop end: a release segment?
- ~~**Shared recordings with the KN5000.**~~ Settled on 2026-10-30 (lane media-files): the KN5000's
  IC307 is the Y half of such a pair. No 1 MiB page of IC307 equals a KN7000 page (whole-page
  comparison, 2026-10-29), but 1,342 of its 1,413 waves occur verbatim in this tone generator pair's
  Y chips, 1,162 in IC203 and 180 in IC207, none in an X chip, and its parameter records are the odd
  words of the KN7000 records that play the same recordings
  ([Waveform ROM Format]({{ site.baseurl }}/waveform-rom-format/#ic307-is-half-of-a-pair)).

## See also

- [Media Files]({{ site.baseurl }}/media-files/): the WAV files, for every model

- [Sound Subsystem]({{ site.baseurl }}/kn7000-sound-subsystem/#wave-roms-ic203-ic204-ic207-ic208): the
  chips in the signal chain
- [Expansion Bus & Wave-ROM Dump]({{ site.baseurl }}/kn7000-expansion-and-wave-dump/): how the
  firmware's readback window made the dump possible
- [Wave-ROM Dump Tutorial (Pi Pico)]({{ site.baseurl }}/kn7000-wave-rom-dump/): a hardware route
- [Table ROM]({{ site.baseurl }}/kn7000-table-rom/): the voice archive whose zones name these entries
