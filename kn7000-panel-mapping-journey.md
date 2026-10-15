---
layout: page
title: "Determining KN7000 Panel Bindings"
permalink: /kn7000-panel-mapping/
---

# Determining KN7000 Panel Bindings

The SX-KN7000 has over a hundred front-panel buttons. The scan matrix that carries them says
nothing about which position is which button, so every binding in the
[MAME driver]({{ site.baseurl }}/kn7000-roadmap/) has to be established by evidence. This page
describes the methods that produce that evidence and the rules that keep them honest. The
resulting map is on the [Control Panel Protocol]({{ site.baseurl }}/kn7000-control-panel/) page.

## What Has to Be Determined

The panel HLE reports **22 scan segments** (`0x00`–`0x15`) of eight bits each, one per MAME
input port (`CP{board}_SEG{col}` for CPL, CPC and CPR), carrying **154 declared buttons**. (The
kn7000_mame overlay's older device declares 33 normalised segments, `num_segs()` = `0x21`, and
152 buttons.) A binding is one (port, mask) pair tied to one
silk-screened button, and it is only correct if pressing it makes the firmware do what that
button does on the instrument.

## Method 1: The HELP Oracle

The KN7000 names its own buttons. Press **HELP**, then press any other button, and the display
shows an info page titled `HELP : <BUTTON NAME>`.

This is a per-button oracle built into the firmware. Enter HELP mode, press a candidate bit,
and read the title strip. Because a no-op leaves the previous title on screen, consecutive
identical strips are de-duplicated and the distinct ones stacked into one tall image, so a
single run and a single screenshot reveal a whole segment's worth of names.

> ⚠ **One candidate per boot.** HELP is a toggle — pressing it again turns help off — and some
> buttons navigate away instead of showing info. A multi-press sweep in one boot silently
> contaminates itself after the first such press. The reliable form is: boot, enter HELP, press
> exactly one bit, screenshot, check the result.

The oracle is silent for buttons with no info page, which is most of the part-mute matrix.

## Method 2: Snapshot Probing

For any button that opens a distinctive screen, press the bit and capture the LCD. This
identifies sound families, rhythm genres, menu keys and transport keys directly.

> ⚠ **Never decide a screen changed from a hash of the whole frame.** The title bar carries a
> live tempo readout; a tick from ♩=120 to ♩=121 registers as a change and will attribute a
> screen close, or a screen open, to a button that did nothing of the sort. Compare the screen
> *body*, and read the actual image before believing an automated verdict.

## Method 3: Press-Count Encoding (the mute matrix)

The sixteen `MUTE UP` / `MUTE DOWN` buttons have no HELP pages and open no screens; each press
nudges one part's mixer level by one step. That is enough to identify them in bulk: press the
first candidate 5 times, the second 10, the third 15, and so on, then take **one** snapshot of
the PT1–16 mixer. Each affected part sits at a distinct level, and the level decodes which
button drove it — a whole segment per screenshot.

The mute matrix as currently bound: `CPC_SEG5` bits 4–7 are parts 1–2, `CPC_SEG8` parts 3–6,
`CPC_SEG9` parts 7–10, `CPC_SEG10` parts 11–14, and `CPC_SEG11` bits 0–3 parts 15–16.

## Method 4: Owner Reports

Reports from the instrument's owner running the published build — *"the button labelled CUSTOM
opens the ENTERTAINER screen"*, *"MUTE 1 triggers MUTE 7"* — are hard data points and outrank
any inference from the firmware tables.

## The Firmware Dispatch Table Is a Lead, Not Gospel

The firmware records an event code for every switch, which groups the panel usefully: genres
form one event class, part mutes appear as on/off pairs, and a `0x1xxx` class marks the system
keys.

There are **two complete panel interpretations** in the shared MN10300 codebase, and a RAM flag
at `0x5006BE94` selects between them:

| Flag                                                  | Normalise table                     | Dispatch table |
|-------------------------------------------------------|-------------------------------------|----------------|
| **0 — what the KN7000 runs** (tone generator present) | `PanelWireNormTable` (`0x486135A0`) | `0x48614978`   |
| 1 (a variant with no tone generator)                  | `0x48613620`                        | `0x486149FC`   |

`0x486149FC` is a real, fully decoded dispatch table, but it is the **inactive half** on this
model: the firmware selects it only when the strap at `0x98070000` reports no tone generator
(`TgStrapProbe`, `0x484D7713`). Both tables agree on the mute part IDs, so the mute
cross-check holds either way. The ADDR→normSeg formula is in
`notes/panel-board-decode.md`, and which bank the KN7000 runs is settled in
`notes/panel-bank-A-is-the-kn7000.md`.

The table also indexes the firmware's internal segment numbering, which is not the layout's.
A binding read straight out of it can land on a physically different switch: an "AUTO PLAY
CHORD ON/OFF" binding taken from the table sat on a bit that is physically a part-10 mute.
Confirm every table-derived binding with a live test.

## Where the Map Lives

The button map is `notes/panel-button-map.md` in the driver overlay repository. The current
bindings, as declared by `kn7000_cpanel_device`, are listed on the
[Control Panel Protocol]({{ site.baseurl }}/kn7000-control-panel/) page.
