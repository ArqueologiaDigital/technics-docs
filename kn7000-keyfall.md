---
layout: page
title: "Keyfall on the KN7000"
permalink: /kn7000-keyfall/
---

# Keyfall on the KN7000

A falling-notes piano game for a stock KN7000:
- notes fall down the LCD onto a keyboard drawn at its bottom;
- the player strikes them on the instrument's keybed as they reach it, and each key is judged by its timing;
- the other parts of the song are the accompaniment, which the instrument itself plays.

The songs are Standard MIDI Files on the SD card. It is a program of the
[program menu]({{ site.baseurl }}/kn7000-cnv-homebrew/) (folder `KEYFALL\`), listed in the menu's Games folder as
"Keyfall (piano game)" and started from DISK MENU > STYLE CONVERT. Three public-domain pieces come with it.

Source: `kn5000_homebrew/demos/kn7000_keyfall/` (its `README.md` has the details).

> **Status (2026-11-06): plays in MAME (program 893), every check passing, and has played on the owner's
> KN7000.** The card copied off the unit on 2026-10-31 holds Keyfall's log: build 3d0fe47 started from the program
> menu on program 893, MINUETG played three times (scores 350, 1360 and 4180) and ODEJOY once (8270), its 602
> accompaniment messages sent with the ring never full, the best scores saved (kn5000_homebrew
> `demos/kn7000_keyfall/tests/results/unit-2026-10-31/`). In MAME (the owner's loader floppy, the program menu on a
> copy of the owner's card) it:
> - starts from the menu, plays all three songs (in PLAY, WAIT and DEMO between them), and judges the keys struck on
>   MAME's keybed;
> - sends the accompaniment into the instrument's MIDI IN 1, and the instrument plays it.
>
> **User manual:** [Keyfall on the KN7000 (PDF, 6 pages)]({{ site.baseurl }}/assets/manuals/keyfall-kn7000-manual.pdf).
>
> The final runs, on source commit 703ad97, passed 13 of 13 checks twice, one of them with both hands
> ([How it was checked](#how-it-was-checked)).

## Playing it

![Keyfall playing Ode to Joy on the KN7000's LCD, in MAME]({{ site.baseurl }}/assets/images/kn7000/keyfall-playing.png)

DISK MENU, STYLE CONVERT, `KN7LOAD.CNV`, OK; then the program menu's Games folder, "Keyfall (piano game)", RUN. The
folder's MIDI files are listed. The TEMPO/PROGRAM wheel (or UP/DOWN) chooses one, and the soft keys beside the LCD set
up the game:

| control                  | on the song list                                                               | during a game  | on the results |
|--------------------------|--------------------------------------------------------------------------------|----------------|----------------|
| TEMPO/PROGRAM wheel      | the song                                                                       |                |                |
| LCD left 1: PART         | the part played: each track, and "Both hands" when tracks are named for each   |                | SONGS          |
| LCD left 2: TEMPO        | 100% to 50% of the song's tempo                                                |                |                |
| LCD left 3: ACCOMP       | the accompaniment (the other parts) on or off                                  |                |                |
| LCD left 4: MODE         | PLAY (judged), WAIT (the song waits at each note for its key), DEMO (it plays) |                |                |
| LCD left 5: SPEED        | how fast the notes fall (70 to 180 lines a second)                             |                |                |
| LCD right 1: PLAY        | starts the game                                                                |                | AGAIN          |
| LCD right 2, 3: UP, DOWN | the song                                                                       |                |                |
| LCD right 5: LATENCY     | ms taken off each key's time before it is judged (-40 to 100)                  |                |                |
| EXIT                     |                                                                                | stops the song | SONGS          |
| EXIT held 1.5 s          | leaves Keyfall                                                                 | leaves Keyfall |                |

The rest of the panel works as usual. The keybed plays the sound chosen for it (choose one while the song list is
up); the game only reads its keys.

**Judging.** A note's lower edge reaches the keyboard at its time, and the key it belongs to lights up just before.

| key struck within the note's time | judged    | points (times the multiplier) |
|-----------------------------------|-----------|-------------------------------|
| 50 ms                             | PERFECT   | 100                           |
| 100 ms                            | GOOD      | 70                            |
| 150 ms                            | OK        | 40                            |
| not struck by then                | MISSED    |                               |
| a key that strikes no note        | WRONG KEY |                               |

The multiplier is 1 plus a tenth of the streak, at most 4.

![Keyfall's results screen after Ode to Joy, in MAME, the test script striking each key 30 ms before its time]({{ site.baseurl }}/assets/images/kn7000/keyfall-results.png)

The results give the grade (S from 95%, A 85%, B 70%, C 50%), the counts, the longest streak, and how early or late
the keys came on average. The best score of each song, part and tempo is kept in `SCORES.TXT` in the folder.

**Which keys are read.** The game reads the keys that the keybed sends to MIDI OUT on channels 1-3 (RIGHT 1, RIGHT 2,
LEFT). It also reads what MIDI IN 1 receives on those channels, from a keyboard plugged in there. While AUTO PLAY CHORD
is on, the keys left of the split point are the arranger's chord keys and send nothing. A right-hand part plays as it
is; for a left-hand part, or both hands, turn AUTO PLAY CHORD off first. In MAME every key was read with it off, and
none below C4 with it on.

## The songs

The three songs were written out for this game as text (`songs/*.txt`) and made into MIDI files by
`tools/songs/mksong.py`:

| file          | piece                                                                  | parts                            |
|---------------|------------------------------------------------------------------------|----------------------------------|
| `TWINKLE.MID` | Twinkle, Twinkle, Little Star (the French "Ah ! vous dirai-je, maman") | right hand, left hand (chords)   |
| `ODEJOY.MID`  | Ode to Joy (Beethoven, Symphony No. 9), in G major                     | right hand, bass, strings, drums |
| `MINUETG.MID` | Minuet in G major, BWV Anh. 114 (Petzold), its first part              | right hand, left hand            |

**Adding songs.** Copy any Standard MIDI File (format 0 or 1) into the card's `KEYFALL\` folder, with an 8.3 name
ending in `.MID`. Every track's notes on one channel are a part, named by the track's name. A track named "Right hand"
(or "RH", "Melody") is offered first, and a "Left hand" ("LH") beside it adds "Both hands" to the choices. System
exclusive messages in the file are left out, because a GM reset would change the instrument's settings.
`mksong.py`'s README describes the text format for writing a song by hand.

## How it works

Keyfall has two programs, built the same way as ProTracker's and the PDF viewer's:
- **`KN7APP.BIN`** is the PDF viewer's platform at ABI 15. The loader runs it on each converter call. It starts a task
  for the game and serves its file reads. From the firmware it takes only the switches the game names (the ten soft
  keys and EXIT) and the wheel, and leaves the firmware everything else. It keeps the firmware's drawing off. ABI 15
  adds the keybed's presses and releases, each with the millisecond it was found (`keyEvents`, read from the MIDI rings
  as Another World reads them), and a way to put MIDI messages into MIDI IN 1's ring (`midiIn`). At the end it sends
  Reset All Controllers and All Notes Off on every channel the game used.
- **`KEYFALL.BIN`** is the game: the song reading, the chart and the accompaniment, the judging, the screens and the
  best scores. Its code and data take 45 KB of the 204 KB program area.

**The accompaniment through MIDI IN 1.** The game puts the accompaniment into MIDI IN 1's receive ring as its time comes,
as if it came from the MIDI IN socket, and the instrument plays it. The instrument's MIDI parts PART 4-16 receive
channels 4-16 (the owner's manual, "Part Setting"). So a song's channels 1-3, the keybed's own parts, move to channels
that the song leaves free, and channel 10 stays the drums. Each channel starts with a GM2 bank select (MSB 121, drums
120), its program, volume 100, pan centre and expression 127. In MAME the game never read its own accompaniment as
keys.

**The converter rest and latency.** The firmware's main task passes the keybed to MIDI OUT, and takes what is in MIDI
IN 1, only between converter calls. So the time each converter call rests decides how late the keys reach the game and
how late the accompaniment is played. Measured in MAME:

| converter rest | keys reached the game (after the script struck them) | firmware took the accompaniment (after the game put it in) |
|----------------|------------------------------------------------------|------------------------------------------------------------|
| 100 ms         | 23-146 ms                                            | 1-178 ms                                                   |
| 20 ms          | 24-62 ms                                             | 1-47 ms                                                    |
| 10 ms          | 26-48 ms (median 38)                                 | 0.5-13 ms                                                  |

While a song plays, Keyfall rests 10 ms between converter calls (ABI 15's `restMs`; `PLAY_REST_MS` in its Makefile).
Up to one frame (17 ms) of each key's lateness is the test script's own: it strikes a key on the first MAME frame at
which the game's clock has passed the note's time. The LATENCY soft key takes a set number of ms off each key's time
before it is judged.

**The screen.** The game draws 8 bits a pixel through the LCD controller's look-up table (the PDF viewer's set-up),
with the soft keys' labels in its ink layer. Display memory is slow, so only what changes is drawn. The lanes are cut
into segments at every key's edge. Each frame redraws only the rows that a note's edges crossed in its lane, and a beat
line's old and new row.

## How it was checked

All of this was in MAME, program 893, run through the program menu as on the instrument. A Lua script chose the song
and settings with the soft keys, read the chart from the game's memory, and struck each note on MAME's keybed when the
game's clock reached its time. It then checked the results screen's counts against what it struck. It also checked
that every key reached the game, and that every accompaniment message went into MIDI IN 1's ring and the firmware took
it. The scripts and their results are in `tests/` of the source.

| run                                          | result                                                                                  |
|----------------------------------------------|-----------------------------------------------------------------------------------------|
| Twinkle, every note struck                   | 42 of 42 PERFECT                                                                        |
| Twinkle, 3 notes left out, 2 stray keys      | the 3 counted MISSED, the 2 counted WRONG KEY, the rest PERFECT                         |
| Ode to Joy, each key struck 30 ms early      | 62 of 62 PERFECT, judged -5 to +26 ms                                                   |
| Ode to Joy, no key struck                    | 602 accompaniment messages, all taken by the firmware, none read as a key; 62 MISSED    |
| the same run's sound                         | the accompaniment heard at -36.8 dBFS over the song, digital silence in the 5 s before  |
| Minuet, WAIT                                 | the clock stopped at every note (51.7 s played for 29.7 s of clock), all 64 struck      |
| Ode to Joy, DEMO                             | the player's part sent too (736 messages against 602), nothing judged                   |
| every keybed key, C2 to C7                   | all read with AUTO PLAY CHORD off; only C4 and up with it on                            |
| final, 703ad97: Twinkle, 2 left out, 2 stray | 13 checks, 0 failed; keys judged 25-51 ms late, the accompaniment taken 0.5-12 ms after |
| final, 703ad97: Minuet, both hands           | keys down to D3: 88 PERFECT, 1 GOOD of 89; 13 checks, 0 failed                          |

On a PC, `make check` builds the game's own song reading and judging (32-bit, as on the KN7000) and runs it over every
song. It checks that each song is read as written, that the charts and the accompaniment are in time order and off
channels 1-3, and that four scripted players (perfect, 70 ms late, a wrong key before every fourth note, every third
note missed) are judged as they should be, at 100% and 50% tempo.

## Limits and open items

- How late keys reach the game on the instrument has not been measured: the log of the unit's run counts each
  game's judgements (perfect, good, ok, miss, wrong), not how late each key arrived.
- The keys below the split point reach the game only with AUTO PLAY CHORD off (measured in MAME).
- System exclusive messages in a song are not sent.
- The final MAME runs were of 703ad97, from before commit 33b277a (2026-10-31). Since that commit every link refuses an
  `addc` or `subc` right after a flag update. Built with the old GCC, Keyfall had 4 such places; with the Pinball
  port's patched GCC (a `nop` before each `addc` and `subc`), none.

## Sources

kn5000_homebrew, `demos/kn7000_keyfall/`:
- `README.md`: the game, its controls, the songs, how it works, what was checked;
- `manual/`: the user manual, printed from `keyfall-kn7000-manual.html` by `build.sh`; its pictures cut from the MAME
  snapshots by `mkimg.py`;
- `songs/`, `tools/songs/README.md`: the songs as text and MIDI files, and `mksong.py`'s format;
- `src/game/` (the game), `src/app/` (`KN7APP.BIN`), `src/common/pfhost.h` (the interface between the two);
- `tests/mame/README.md`, `tests/mame/keyfall_test.lua`, `tests/mame/run_keyfall.sh`: the MAME sessions;
- `tests/results/README.md`: every MAME run, its events file and its versions file;
- `tests/results/unit-2026-10-31/`: the log and the best scores of the run on the owner's KN7000;
- `tests/host/README.md`: the PC checks (`make check`);
- the commits 9f431b3 to 3d0fe47 (2026-10-30) and 33b277a (2026-10-31).
