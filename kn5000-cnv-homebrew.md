---
layout: page
title: "Your Own Code on a Stock KN5000"
permalink: /kn5000-cnv-homebrew/
---

# Running your own code on a stock KN5000

DISK MENU > STYLE CONVERT loads a `.CNV` program from a floppy and runs it on the KN5000's main CPU,
on the stock firmware, as it does on the [KN7000]({{ site.baseurl }}/kn7000-cnv-homebrew/). Any
TLCS-900 program linked to the converters' load address can use that door, not only a style
converter. The project's first program through it is **Another World**, `AW.CNV`, with the game's
files on the same floppy (technics-anotherworld `kn5000cnv/`).

> **Status (2026-10-23).** `AW.CNV` runs in MAME on firmware v5, v6, v7 and v10 (v8 and v9 share
> v10's addresses): the whole intro, the water part, the controls on the panel and on the keybed,
> the game's sound on the instrument's voices, and, in a test build, the game's own samples through
> a mixer of ours on the effects DSP. It has **not** run on a real KN5000: the project's
> unit is away. Building it found four emulator bugs, fixed in the project's MAME overlay
> ([below](#emulator-bugs-it-found)).

## Running it

1. Build the floppy from your own copy of the MS-DOS release: `make AW_DATA=<dir>` in
   `kn5000cnv/` writes `build/aw5000.img`, a 1.44 MB DOS floppy holding `AW.CNV` and the game's
   resources as `AWnn.BIN`. The game data is not in the repository.
2. On the main screen: **DISK** (MENU group), **STYLE CONVERT** (left button 3), `AW.CNV` is
   already selected, **OK** (right button 4). The intro's files load in about 7 s.
3. Hold **EXIT** for 1.5 s to leave. The firmware then shows "ERROR!" and "Continue Next?", as it
   does after any converter that ends; **NO** returns to the main screen.

The game refuses to start ("AW: SAVE SONGS, SWITCH OFF+ON") while a song is recorded, because it
borrows the sequencer's song memory and gives it back exactly as found.

| control                 | panel                                 | keybed              |
|-------------------------|---------------------------------------|---------------------|
| UP (jump, swim up)      | PART SELECT: RIGHT 2                  | A♭4 or B♭4          |
| DOWN                    | CONDUCTOR: RIGHT 2                    | A4                  |
| LEFT / RIGHT            | CONDUCTOR: LEFT / CONDUCTOR: RIGHT 1  | F4 / C5             |
| ACTION (run, kick, gun) | VARIATION 4                           | any key C3 or lower |
| help screen             | HELP (PAGE UP / DOWN; EXIT closes it) |                     |
| level codes             | OTHER PARTS/TR                        |                     |
| leave the game          | hold EXIT for 1.5 s                   |                     |

Note names are the KN5000's own (middle C is C3, as its SPLIT POINT screen shows). Of two opposite
directions held on the keybed, the one already in use stays until its key is released. The help
screen's first page lists the keybed too.

## What a converter gets

| what                    | how                                                                                                                                                                                                                                                                                                                                      |
|-------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| load and call           | the file, at most 192 KB, at `0x80000` (the firmware zeroes those 192 KB first); the firmware calls its first byte, and keeps calling it                                                                                                                                                                                                 |
| talking back            | a mailbox byte at `0xFFC00`: 1 parks, 5 shows the text the converter points at (the firmware calls again at once, so a message is repeated for as long as it should stay), `0xFE` ends with "ERROR!" and "Continue Next?"                                                                                                                |
| more memory             | the sequencer's song memory, `0xB0000`-`0xFDFFF`, when it holds no song (all zero on v5/v6 after boot; v7-v10 build a chain of `0x4D8` 256-byte blocks there): `AW.CNV` puts its four pages, the shared polygons and a screen buffer there and restores the chain                                                                        |
| VRAM                    | 256 KB at `0x1A0000`; the visible 320x240 ends at `0x1B2BFF`, and the firmware draws nothing past it while a converter runs (the help screen draws at `0x1B3000`)                                                                                                                                                                        |
| files                   | the firmware's own `FileIO_OpenWithMode`, `_ReadBlock`, `_SeekAndReadBlock` and `_CloseHandle`, whose addresses differ between v5, v6, v7 and v8-v10; `AW.CNV` checks each routine's opening bytes before trusting a set                                                                                                                 |
| time                    | the firmware's Timer 1 counter at `0x0409`, 488 Hz (2.048 ms a tick)                                                                                                                                                                                                                                                                     |
| the panel               | the firmware runs the panel link by interrupt but decodes it in its main loop, which does not run meanwhile: the converter masks INTA, INTRX1 and INTTX1, turns SC1's pins on as the firmware's transmit path does (`PFFC`/`PFCR` \| `0x50`) and polls the panels itself, using a reply only when its header names the segment asked for |
| the keybed              | the sub CPU's key events still reach the main CPU's note ring (`0x202CB` in v5-v10, found from the sequencer's dispatch table entry 2 at `0xE0001A`): note and velocity, velocity 0 for a release                                                                                                                                        |
| the instrument's voices | records written to the sub CPU over the inter-CPU latch, with the firmware's own handshake ([Inter-CPU Protocol]({{ site.baseurl }}/inter-cpu-protocol/#records-a-converter-can-send-2026-10-22))                                                                                                                                        |

## Another World on it

The KN5000 VM of the [Another World]({{ site.baseurl }}/another-world-vm/) port, built as a
converter: it runs inside the firmware's first call and returns only when the game ends. Each part's
palette, bytecode and polygons are read from the floppy when the part starts; the screens when the
game names them; the music modules when it starts one.

### Speed

Frames took about 1.5 times what the game's script asks for, in emulated time: the VM showed the
page, then paused, and timed the next frame from the end of its thread loop, so the work after the
pause never counted; and every frame copied the page to VRAM a second time. Pausing first and timing
from the pause, as the reference engine does, and block moves (`LDIRW`, `LDIR`, 32-bit stores) for
the page copies, fills and spans, brought a chase frame asked as 80 ms from 124 ms to 85 ms (the
pause polls a 2 ms tick, so 82 ms is the floor). The pages shown are the same, hashed frame by frame
against the earlier build. MAME itself runs the KN5000 at about 63 % of real time on the project's
machine, which no change to the game can recover.

### Sound

As the KN7000 port's first sound mode: no sample of the game is played; each sound effect and each
row of the music module becomes a note of one of the instrument's voices. The firmware's main loop,
which turns MIDI and the keybed into the sub CPU's records, does not run during the game, so the game
sends those records itself, on the MIDI receive parts 3-10 (idle while no song is loaded), and gives
the parts their power-on settings back when it ends. The music's sync marks reach variable `0xF4` as
in the original.

MAME has only one of the KN5000's four wave ROMs dumped, and plays few of its voices: of 66 voices
tried, about twenty sound, and no drum kit does. The voices were chosen among those, and the drums
are voices at a fixed note; the real instrument plays every voice, so the table is one to retune on
the unit.

**The game's own samples, on the effects DSP (`make DSND=1`, MAME only so far).** A four-channel mixer
of ours runs on IC311, fed by a streamer of ours in the sub CPU's DRAM. That streamer steps the
channels over the game's samples 4000 times a second, and the sound effects and music module both
drive the four channels, as on the Amiga. Each part's sounds load with the part: about 8 s more
for the intro. Leaving the game puts IC311's own effects back as they were. It is heard in MAME's
IC311 build only, and it has not run on a real KN5000:
[DSP Sample Playback — Research Plan]({{ site.baseurl }}/kn5000-dsp-sample-playback-research/#results-second-pass-a-mixer-fed-by-the-sub-cpu).

### A VM bug it found

At the lake, dying or climbing out froze the game. `CHECK_THREAD_REQUESTS` walked the 64 threads with
`LD A, 0` but indexed the thread table with all of `WA`; on the frame a part switch ran, `W` still
held the high byte of the palette pointer, so that frame's 64 thread updates went to
`THREADS_DATA + 0x2800` (the index wraps at 16 bits): the middle of the new part's bytecode, the code
that runs when Lester dies or leaves the lake. The standalone ROM builds had the same bug, with the
writes landing elsewhere. Clearing `W` fixed both.

### Emulator bugs it found

| bug                                                                                                                                                                                                                                           | fix in the MAME overlay                                                               |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| v7 and v9 panel buttons did the wrong thing (DISK nothing, EXIT transposed), v6 showed "ERROR in CPU data transmission": the panel model raised INTA while a command was still being sent, and lost every other packet of a long answer       | `kn5000_cpanel`: answer no sooner than 150 us after a command; 150 us between packets |
| opening STYLE CONVERT held the sub CPU in reset (keybed dead, "Sound Name Error" afterwards): the TMP94C241's ports A and B have no control register, so a read gave the pins, and the firmware's `set 3,(PA)` cleared the sub CPU's `/RESET` | ports A and B read back their output latch                                            |
| every keybed input was named an octave above the instrument's own name for the key                                                                                                                                                            | inputs renamed C1..C6                                                                 |
| with IC311 emulated, the DSP saw the sub CPU's writes only once per sound-stream batch (about 90 times a second for a 4 kHz sample stream)                                                                                                    | the tone generator's stream is brought up to date before each IC311 host byte         |

## Sources

- technics-anotherworld `kn5000cnv/README.md`: the build, the memory, every measurement above with
  the probe that made it.
- kn7000_mame `notes/kn5000-panel-race-2026-10-22/`, `notes/kn5000-subcpu-reset-porta-2026-10-22/`,
  `notes/kn5000-key-names-2026-10-22/`.
