---
layout: page
title: "KN7000 Techni-chord: software, not silicon"
permalink: /kn7000-technichord/
---

# Techni-chord: software, not silicon

**Techni-chord** is the KN7000's auto-harmony feature: play a melody with the
right hand while a chord is specified (by the auto-play-chord section or a held
left-hand chord) and the instrument adds harmony notes underneath the melody,
voiced in one of fourteen selectable styles. The user's manual documents it on
page 48; the on-screen `TECHNI-CHORD` editor offers a style grid and an
`ORCHESTRATOR` selector that picks which part sounds the added notes.

A natural assumption about a device with two custom PCM tone-generator LSIs is
that a "harmony" feature might be a capability of that silicon — a note-multiplier
or chord mode inside the tone generator. **It is not.** Reverse engineering the
MN10300 firmware shows Techni-chord is implemented **entirely in software** on the
main CPU. The harmony engine detects the chord, computes MIDI note numbers with
plain semitone arithmetic, and emits them as **ordinary note-ons** through the
same voice path any other note travels. The tone generators never learn that the
notes are "harmony" — they receive ordinary voices.

## How it is turned on

Techni-chord is not a mode bit in the tone generator; it is three entries in the
firmware's **sound-parameter database** (the same key/value store that carries
every other panel setting):

| Parameter | Meaning |
|---|---|
| `0x8080` | Techni-chord **on / off** |
| `0x8081` | harmony **style**, `0..13` (index into the 14 styles below) |
| `0x8082` | **orchestrator** — which part produces the harmony notes |

Pressing the panel `TECHNI-CHORD` button toggles `0x8080`; the `TECHNI-CHORD`
editor's style grid writes `0x8081`; its `ORCHESTRATOR` rocker writes `0x8082`.
These are ordinary CPU-side settings — nothing is written to the sound hardware
to "arm" harmony.

## The harmony-compute path

When a melody note is played with Techni-chord on, the harmony routine at
`0x48472EBA` runs on the MN10300:

1. **Fetch the chord.** It calls `GetCurrentChord` at `0x4844DDF2`, which
   copies the currently specified chord — a 6-byte record `{type, root, …}`
   maintained at RAM `0x50000B18` by the auto-play-chord / left-hand chord
   state — then normalises extended chord types (29–41) to a basic type 1–28
   through a **42-entry jump table at `0x485BC3EC`**.
2. **Dispatch by style.** It indexes a **14-entry jump table at `0x485BC3B4`**
   with the style number (`0x8081`), branching to that style's voicing routine —
   for example `CLOSE` at `0x48473051`, `OCTAVE` at `0x484736D4`,
   `HARD ROCK` at `0x48473703`, `FANFARE` at `0x48473732`. **Note the style
   number is *not* the on-screen grid position** — see the corrected mapping
   below.
3. **Compute the notes.** Each voicing routine computes its harmony notes'
   **MIDI note numbers by plain semitone arithmetic** — there is no pitch DSP
   and no reference to sample-zone pitch here. Three families:
   - *Chord-tone styles* (`CLOSE`, `OPEN 1/2`, `DUET 1`): walk the chord-tone
     list (RAM `0x5003AB04/05`), fold each tone into the octave below the
     melody, keep tones more than 2 semitones below it (max 4), then re-spread
     or clamp per style.
   - *Matrix styles* (`DUET 2`, `COUNTRY`, `THEATRE`, `HYMN`, `BLOCK`,
     `BIG BAND BRASS`, `BIG BAND REEDS`): per-style matrices at
     `0x485BA574`–`0x485BC3A4` — 28 chord-type rows × 12 interval columns ×
     1–4 harmony bytes; each harmony note = melody − matrix byte. A shared
     helper (`0x48473766`) folds the roots of the symmetric chord types
     (augmented / diminished) so enharmonically identical chords share columns.
   - *Fixed-interval styles* (`OCTAVE`, `HARD ROCK`, `FANFARE`): signed pairs
     at `0x485BC3A4` — these three never read the chord at all, which is why
     the user's manual says exactly these three "function even when the
     keyboard is not split".
4. **Emit as ordinary note-ons.** The computed notes are sent as **normal
   note-on events on the orchestrator part** (`0x8082`), so they play through
   that part's own patch, volume, effects and the standard voice-allocation path
   — indistinguishable, to the tone generator, from a note the player pressed.

Because the harmony notes are just note-ons on a normal part, everything that
applies to a part applies to them for free: the orchestrator's sound selection,
its transpose and tuning, its reverb / chorus / DSP sends, and the
[sample-zone-relative pitch pipeline]({{ site.baseurl }}/kn7000-sound-subsystem/)
that turns a MIDI note into the tone generator's internal pitch value.

## The fourteen styles — and the parameter order that hides one of them

*(Corrected 2026-07-19: an earlier version of this page assumed the style
parameter counts in on-screen order, which shifted the example addresses for
`OCTAVE`/`HARD ROCK` by one routine. It does not — see below.)*

The 14 style names live as a string pool at `0x485EC960` in **on-screen grid
order** (the `TECHNI-CHORD` editor screen, user's manual page 48). But the
**style parameter `0x8081` — the value the jump table dispatches on — uses a
different, legacy order**: the GUI translates between the two through a
14-halfword table at `0x485EC940` (`param → grid slot`:
`0,1,2,4,5,6,7,8,9,10,11,12,13,3`). The one style that moves is `DUET 1`:
drawn in grid slot 3, **stored as parameter 13, after `FANFARE`**.

| param | Style (voicing routine) | added notes |
|---|---|---|
| 0 | CLOSE (`0x48473051`) | chord tones below the melody, max 4 |
| 1 | OPEN 1 (`0x484731EB`) | CLOSE, first note dropped an octave |
| 2 | OPEN 2 (`0x4847320C`) | CLOSE, re-spread by octave shifts |
| 3 | DUET 2 (`0x48473288`) | 1 (matrix `0x485BA574`) |
| 4 | COUNTRY (`0x484732F0`) | 1 (matrix `0x485BAEA4`) |
| 5 | THEATRE (`0x48473358`) | 2 (matrix `0x485BA6C4`) |
| 6 | HYMN (`0x484733E3`) | 3 (matrix `0x485BAFF4`) — four-part writing with the melody |
| 7 | BLOCK (`0x48473495`) | 4 (matrix `0x485BA964`) |
| 8 | BIG BAND BRASS (`0x4847355D`) | 3 (matrix `0x485BB3E4`) |
| 9 | BIG BAND REEDS (`0x4847360F`) | 4 (matrix `0x485BBE64`) |
| 10 | OCTAVE (`0x484736D4`) | melody +12 and −12 (fixed) |
| 11 | HARD ROCK (`0x48473703`) | melody −5 and −12 (fixed — fourth + octave below) |
| 12 | FANFARE (`0x48473732`) | melody +10 and +5 (fixed — stacked fourths above) |
| 13 | DUET 1 (`0x484731D0`) | 1 (CLOSE clamped to its first note) |

This corrected mapping is what makes every user-manual statement line up with
the code: *"big band reeds … adds four harmony notes"* (the `0x485BBE64`
matrix carries four bytes per column); the manual's chord-independent trio
(*"when the OCTAVE, HARD ROCK or FANFARE style is selected, the TECHNI-CHORD
functions even when the keyboard is not split"*) is exactly the three
fixed-interval routines; and *"a simple duet which adds one harmony note"* is
`DUET 1`. The most likely reason for the odd storage order: earlier models had
a 13-style list whose parameter 3 was a single `DUET`; `DUET 1` was appended
at the end so stored registration data kept its meaning, while the screen
draws it beside `DUET 2`. The KN6000 firmware embeds the same string pool and
the same mapping table.

The full engine — `TechniChordCompute`, all fourteen voicing routines and
their helpers — is now converted to re-assemblable, byte-exact MN10300 source
in the `technics-roms-disasm` repository (`kn7000/src/program.s`, names
in `kn7000/kn7000_manual.sym`).

## Why this is dispositive — it is not hardware

Two facts settle it beyond the mere presence of a software routine:

- **The harmony engine writes zero tone-generator registers.** The whole path
  above touches no sound-hardware I/O — there is **no access to `0x98040000` /
  `0x98050000`** (the master / sub tone-generator register ports) anywhere in the
  harmony computation. It produces note events and hands them to the ordinary
  voice engine; the register writes that actually reach the tone generators are
  the same ones used for every other note. A hardware harmony feature would have
  to configure the tone generator; this one never does.
- **The harmony is routed to an arbitrary, user-selectable part with that part's
  own patch.** `0x8082` lets the player send the added notes to *any* part —
  played through whatever sound that part is set to. A note-multiplier built into
  the tone-generator silicon could not redirect its extra notes to an arbitrary
  part and re-voice them with a different patch. That flexibility only exists
  because the notes are computed in software and injected as ordinary note-ons.

## Panel control

Techni-chord has one dedicated panel button and one indicator LED, both bound in
the control-panel device:

| | Physical binding | Part |
|---|---|---|
| **TECHNI-CHORD** button | `CPR_SEG1` bit `0x01` | SW0 |
| **TECHNI-CHORD** indicator LED | `cpr_led33` | D1013 (red) |

(See the [Control Panel Protocol]({{ site.baseurl }}/kn7000-control-panel/) for
the scan-matrix tagging convention.)

## Consequence for emulation

Nothing extra is required to emulate Techni-chord. Because it is a pure-software
feature that ends in ordinary note-ons, **a correct MN10300 running the firmware
plus the existing tone-generator note path reproduces it for free** — the
[MAME driver]({{ site.baseurl }}/kn7000-sound-subsystem/) already executes the
harmony routine as part of normal firmware execution. In the project's
sound-enabled build (not yet upstream: upstream MAME's `kn7000` is
`MACHINE_NO_SOUND`), the added notes sound through the same pipeline as any key
press. No harmony model, note-multiplier or special tone-generator mode has to
be written.

---

**Footnote — not to be confused with the microphone harmonizer.** The symbol
`HarmOnOffFunc` at `0x484D6EA6` and the writes to `0x90204000` belong to the
**Vocalist Workstation** microphone-harmony feature (a real-time pitch harmonizer
for the mic input, driven through a MILK class descriptor at `0x4874CFF0`) — a
separate subsystem from Techni-chord. Techni-chord harmonizes *keyboard* notes in
software as described above and does not use that path.
