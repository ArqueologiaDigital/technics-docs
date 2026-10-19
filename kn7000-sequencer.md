---
layout: page
title: KN7000 Sequencer
permalink: /kn7000-sequencer/
---

# KN7000 Sequencer

The KN7000's on-board **sequencer** records and plays back songs — both the
player's own performance and **Standard MIDI Files** — with a note/step editor,
karaoke-style lyrics, and the ability to turn a recorded sequence into a Composer
style or a Pad phrase. Like the rest of the UI it runs on the MILK toolkit, so it
is decoded here from `kn7000_program.rom` through its **event namespace** and its
**`MT_` engine API**, both recovered from the firmware's reflection tables. It sits
between the [storage]({{ site.baseurl }}/kn7000-storage-subsystem/) layer (which loads/saves the
`.MID` files) and the tone generators that play the notes.

## Engine API

The sequencer engine is reached through a dedicated block of `MT_*` calls (the
MILK `MT_GetProcedure` dispatch — table at program `0x355764`). They split into
**transport/query** and **rendering** groups:

| Call | Purpose |
|------|---------|
| `MT_Seq_PlayRequest` | start playback of the current song |
| `MT_Seq_ChangeColor` | recolour the display during playback |
| `MT_GetCurSongName` | current song title |
| `MT_GetComporserName` | current Composer (style) name |
| `MT_GetLyricsSongName` / `MT_GetLyricsMusic` / `MT_GetLyricsLyrics` | lyrics data for karaoke display |
| `MT_GetDiskFileName` / `MT_GetDiskFileNo` | the file being loaded/saved |
| `MT_GetInternalData` | the in-RAM song buffer |

The **note/step editor** is served by a family of drawing primitives:
`MT_DrawNote` (`_0`/`_1` variants), `MT_DrawHilightNote`, `MT_DrawCursor`,
`MT_DrawMeas_NE` / `MT_DrawMeas_SR` (measure rulers), `MT_DrawSoundName` /
`MT_DrawSoundCursor`, and the step-edit set `MT_StepDataDraw`,
`MT_StepDrawCursor`, `MT_StepDrawStrData`, `MT_StepDrawMMMData` — i.e. both a
piano-roll ("note") view and a numeric step-list view, ending each frame with
`MT_SeqDrawEnd`.

## Event namespace

The sequencer screen has its own `EV_*` event block (name table at program
`0x35570C`), separate from the global [UI events]({{ site.baseurl }}/kn7000-event-system/):

* **transport** — `EV_PlayStartIni`, `EV_PlayRequest`, `EV_GetEvent`
* **display** — `EV_SEQ_DRAW`, `EV_ALLCLEAR`, `EV_ALLDRAW`, `EV_RENEW`,
  `EV_REVERSE`, `EV_UPDATE_SCREEN`, `EV_SCROLLUP`, `EV_ChangeColor`,
  `EV_CURSONGNAME`
* **write / commit** — `EV_SONGWRITE`, `EV_COMPORSERWRITE`,
  `EV_LYRICSMUSICWRITE`, `EV_LYRICSLYRICSWRITE`
* **transpose** — `EV_SEQ_TRAS_RESET`, `EV_SEQ_TRAS_UPDATE`, `EV_SEQ_TRAS_OK_WIN`
* **file** — `EV_DISKFILENAME`, `EV_DISKFILENO`

## What a song can carry

Traced 2026-10-18 from the firmware (technics-roms-disasm
`kn7000/notes/presentation-control-probes/song-records.md`; not yet run in MAME). Besides notes, a song
holds tempo (`0x80`), beat and bar markers (`0x81`, `0x84`), end of track (`0x82`), rhythm
start/stop (`0x85`/`0x86`), PIC slide cues (`0x8A`), MIDI-style controller, program change,
aftertouch and pitch bend events, and **parameter events** (`0xA1`–`0xA3` for a part,
`0xF1`–`0xF3` global) that can name any 24-bit parameter id. Playback and recording both pass
every event through a list of the ids allowed for that track's kind:

| track kind     | what it can play and record besides notes                                                                                 |
|----------------|---------------------------------------------------------------------------------------------------------------------------|
| parts, B.PEDAL | program change, the mixer and sound-controller CCs, RPNs, part parameters, PIC                                            |
| CONTROL        | rhythm, variation, intro, fill, ending, rhythm start/stop, tempo, transpose, panel-memory number, TECHNI-CHORD, fade, PIC |
| RHYTHM, APC    | the rhythm subset (intro, fill, ending, start/stop, style, variation, tempo)                                              |
| CHORD          | no list: everything                                                                                                       |

Every change also reaches the GUI as `EV_MMMDATA`, so the screen that shows a setting redraws as
the song changes it; nothing in a song switches screens. Panel operations made while recording
are captured through the same lists, so an automated performance can be recorded on the
instrument. A song cannot store SysEx: SysEx in a loaded Standard MIDI File is converted into
parameter events or initial settings, and unrecognised SysEx is dropped. The global effect types
are on no list, so they cannot change mid-song. Each song also stores a full settings snapshot,
applied at SEQUENCER RESET.

## Record / play controls

The recorder and transport are driven by the screen handlers (all recovered by
name): track selection `SeqTrackSel`, measure navigation `SeqMeasUpDown`,
**easy record** `SeqEasyRecOk`, **cycle (loop) record** `SeqCycRecTglFunc` /
`SeqPlayCycleTgl` / `SeqCycClrSwFunc`, the **metronome** toggle
`SeqRecMetTglFunc`, and stop `SeqRecStopExec`. Lyrics display is handled by
`SeqLyricsShowHide` / `SeqLyricsSong` and set up by the AP-task helper
`AppSEQ_InitSmfLyrics` — confirming the sequencer engine runs in the **AP task**
(see [Tasks & Scheduler]({{ site.baseurl }}/kn7000-task-scheduler/)) while its screen runs in the
main task.

## Standard MIDI Files and conversions

Songs interchange as **SMF** (`.MID`) through the storage layer:
`SmfLoadAsFunc` / `SmfSaveAsFunc` / `SmfPlayAsFunc`, naming/rename via
`SmfFileNaming` / `SmfFileRename`, and song-slot mapping
`SmfSeqToSongNumFunc` / `SmfSeqFromSongNumFunc`. A recorded sequence can also be
**converted in place** into other engines' data — `SeqToCmpCopyGrid` /
`Seq2CmpCpEditFunc` copy it into a **Composer** style, and `SeqToPadCopyGrid` /
`Seq2PadCpEditFunc` copy it into a **[Pad]({{ site.baseurl }}/kn7000-sound-names/#sound-arranger-pad-presets)**
phrase — which is why the pad presets are themselves stored as MIDI event
streams.

## Song memory

The sequencer's songs live in the never-cleared user-memory block of work RAM (see the
[Work RAM Map]({{ site.baseurl }}/kn7000-work-ram/)):

| range                     | size      | what                                                                           |
|---------------------------|-----------|--------------------------------------------------------------------------------|
| `0x501A5800`–`0x501AB9A0` | `0x61A0`  | 11 song records of `0x8E0` bytes                                               |
| `0x501AB9A0`–`0x501F91A0` | `0x4D800` | the song event store: 1,240 pages of 256 bytes (`SongPageStorePtr`)            |
| `0x5003D36C`–`0x50046B6C` | `0x9800`  | in `.bss`: the pages of the built-in demo song being played, inflated from ROM |

A song saved to disk or SD card is a `.SQT` file (signature `J KD`) with a `.ACT`
slide-show file beside it, and loading a KN7000 song also loads its `.ACT` and pictures
([Slide Shows]({{ site.baseurl }}/kn7000-slideshow/); a KN6000 `I KD` song is loaded
without looking for one, inferred). The reset code never clears the
user block, and its owners check the data before trusting it; the service manual gives about 80 minutes of retention for SEQUENCER data.
The event store's size, 317,440 bytes, is the same number as the picture-import file
limit, but nothing in the code ties the two together.

## The tempo clock (how playback actually advances)

Everything the KN7000 plays in time — the sequencer, the rhythm accompaniment,
the metronome, the built-in demos, MIDI clock out — is paced by **one on-chip
16-bit hardware timer** (mode register `0x34001082`, 16-bit reload `0x34001092`,
counter `0x340010A2`). The firmware programs its reload as **1,250,000 ÷ BPM**
on a 2 MHz timebase (IOCLK 16 MHz ÷ 8), and every underflow raises interrupt
group 7, whose handler (`0x48447084`) is a **96-PPQN tick**: it advances a
mod-96 beat phase (`0x50149664`) and steps five clock-lane structures that make
queued events due. Tempo changes simply rewrite the reload on the fly (clamped
40–300 BPM). A second timer (`0x34001080/90`) provides the separate 1 kHz
system tick that runs the RTOS scheduler and UI — which is why a machine can
have a fully live UI while sequenced playback is stopped.

The **KN6000/KN6500** run the same 96-PPQN tick handler (KN6000 `0x48468A69`, phase at
`0x50276E0C`) and the same 1,250,000 ÷ BPM tempo formula, but on a different timer: the
MN10300's 16-bit **timer 6** (mode `0x34001084`, compare A `0x340010C4`, interrupt group 9,
GxICR `0x34000124`). Their TM5 is the millisecond counter instead. Until that timer was
emulated (2026-10-18) nothing sequenced ever advanced on the emulated KN6000.

The ten **demo songs** are self-contained in the program ROM: per song a
zlib-compressed *setup* blob (track table and initial part programs), a
*sequence* blob (256-byte-per-measure pages of delta-timed, running-status MIDI
events) and a *sounds* blob. Each also has a slide-show script in ROM, whose slides
the song's PIC points select as it plays (see
[Slide Shows]({{ site.baseurl }}/kn7000-slideshow/#the-built-in-demonstrations)).

In MAME this timer was the last missing link for playback: with it modeled, the
demo songs play end-to-end and the rhythm accompaniment starts and runs from
START/STOP, at the displayed tempo. This is audible only in the research overlay,
whose tone generator plays placeholder waveforms; mainline MAME's KN7000 decodes the
tone-generator registers but makes no sound.

## Relationship to the KN5000

The sequencer concept, the `MT_Seq_*`/`EV_*` naming and the SMF interchange are
**shared with the KN5000** ([Shared Codebase Map]({{ site.baseurl }}/technics-shared-codebase/));
the [Sequencer]({{ site.baseurl }}/sequencer/) and [Accompaniment engine]({{ site.baseurl }}/accompaniment-engine/)
KN5000 pages are the conceptual companions. The concrete KN7000 specifics
observed here are the addresses of the engine API and event tables and the
Seq→Composer / Seq→Pad conversion paths.
