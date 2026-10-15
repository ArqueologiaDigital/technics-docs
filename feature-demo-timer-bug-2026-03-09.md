---
layout: page
title: "Timer 4/5 and the Sequencer Clock"
permalink: /feature-demo-timer-bug-2026-03-09/
---

# Timer 4/5 and the Sequencer Clock

The KN5000 firmware paces its sequencer, metronome and demo-song cycling from the TMP94C241's
**Timer 4/5** pair. This page states how the firmware programs it, what the chip does on a
compare match, and which parts of that the MAME core models.

## How the Firmware Programs It

```
Timer 4 (16-bit up counter UC4)
  ├── TREG4 (low compare register)  → INTTR4 on match
  └── TREG5 (high compare register) → INTTR5 on match + counter reset

T4FFCR (flip-flop control register)
  ├── Bit 2: invert the flip-flop on a TREG4 match
  └── Bit 3: invert the flip-flop on a TREG5 match
```

Boot (`v10/maincpu/shared/boot_hw_init.s:76-82`) starts **only timer 4** (T16RUN bit 0) with
`T4MOD = 0x05`, `T4FFCR = 0`, `TREG4 = 1` and `TREG5 = 0x3D09`. `Boot_InitPeripherals`
(`v10/maincpu/kn5000_v10_program.s:1329-1333`) then sets the interrupt priorities:

| Interrupt | Priority     | Handler                       |
|-----------|--------------|-------------------------------|
| INTTR4    | 3 (enabled)  | `INTTR4_HANDLER` (`0xEF0E21`) |
| INTTR5    | 0 (disabled) | `Empty_Handler` (`0xEF086A`)  |

TREG5 sets the interval (`T4MOD` bit 2, `CLE`, clears the counter on a TREG5 match), and the
`TREG4 = 1` match raises INTTR4 once per interval, so **INTTR4 is the sequencer clock**. Its
handler drives the tick counters at DRAM 1047, 1051 and 1052, which pace the accompaniment
engine, the metronome and demo song cycling. If INTTR4 does not fire, demo songs never advance.
(The March 2026 notes, and the description of
[#15878](https://github.com/mamedev/mame/pull/15878), name INTTR5; the vector table and the boot
priorities say INTTR4.)

## What a Compare Match Does

Three things are independent, and the emulation keeps them independent:

| On match | Condition |
|---|---|
| Raise the interrupt flag — `0x80` (INTTR5) for TREG_HIGH, `0x08` (INTTR4) for TREG_LOW | always |
| Reset the up counter (TREG_HIGH only) | always, given `T4MOD` bit 2 (`CLE`) set |
| Invert the timer flip-flop | only if the matching `T4FFCR` bit is set |

The `T4FFCR` bits gate **only** the flip-flop. They must not gate the interrupt or the counter
reset — that is what the 8-bit timers in the same file have always done, and the 16-bit path
matches them. TREG_HIGH must raise the upper flag (`0x80`), not the lower one.

## Two Documented Gaps in the 16-Bit Path

`timer_16bits` in `src/devices/cpu/tlcs900/tmp94c241.cpp` deliberately leaves two datasheet
behaviours unmodelled. The sibling `tmp95c061.cpp` implements both in its `run16()` lambda;
port that if a driver ever needs them.

1. **`CLE` is assumed set.** `T4MOD`/`T5MOD` bit 2 chooses whether a TREG_HIGH match clears the
   up counter; `CLE = 0` means a free-running counter. The code always clears.
2. **The two comparators are chained, not independent.** The `else if` means that when
   TREG_LOW and TREG_HIGH hold the same value the lower interrupt can never be raised.

Neither is observable on any Technics machine: the KN5000 sets `T4MOD` bit 2, so (1) is moot,
and `TREG4 = 1` against `TREG5 = 0x3D09` are different, so (2) is moot. The Toshiba TMP95C061
databook passages are Figure 3.9 (3) p.95 and section 3.9 (5) p.103; the quotes are
re-checkable with `notes/wsa1-probes/tlcs900_datasheet_quotes.py` in the
[MAME_Technics_Research](https://github.com/ArqueologiaDigital/MAME_Technics_Research) repository
(`kn7000_mame`).

## Source Locations

| File                          | Location                 | Role                                                                                          |
|-------------------------------|--------------------------|-----------------------------------------------------------------------------------------------|
| `tmp94c241.cpp`               | `timer_16bits` lambda    | 16-bit timer match handling for T4/T6/T8/TA                                                   |
| `tmp94c241.cpp`               | `INTET45 = 6`            | Interrupt register index mapping                                                              |
| ROM vector `0xFFFF60`         | `0x00EF0E21`             | INTTR4: `INTTR4_HANDLER`, the sequencer clock                                                 |
| ROM vector `0xFFFF64`         | `0x00EF086A`             | INTTR5: `Empty_Handler`                                                                       |
| `system_handlers.s:634`       | `INTTR4_HANDLER`         | Advances the tick counters (priority 3 at boot)                                               |
| `system_handlers.s:392`       | `INTT1_HANDLER`          | Internal clock, for comparison                                                                |
| `sequencer_engine.s:19587`    | `SeqPlay_AdvanceMeasure` | State 3 of 8956 (via `SeqStep_TimerDispatchA`): waits on tick counter 1052 (`SEQ_BEAT_COUNT`) |
| `accompaniment_engine.s:8398` | `AccPlayMode_Dispatch`   | Promotion chain endpoint                                                                      |

## Sequencer DRAM Counters

| Address | Name                  | Purpose                                                            |
|---------|-----------------------|--------------------------------------------------------------------|
| 1047    | Metro sub-tick        | Metronome timing (driven by INTTR4)                                |
| 1050    | Internal clock        | Internal clock counter (driven by INTT1)                           |
| 1051    | `SEQ_BEAT_TICK`       | Tick within the beat, 0–95 (INTTR4; +4 per MIDI clock when synced) |
| 1052    | `SEQ_BEAT_COUNT`      | Beats since the start (word, 1052–1053)                            |
| 1054    | Enable flags          | Bit 2: sequencer enabled                                           |
| 1056    | Alt clock state       | Promotion chain variable                                           |
| 1057    | `SEQ_TRANSPORT_STATE` | Transport state; bit 2 gates the beat clock                        |
| 8956    | AccPlayMode state     | State machine index                                                |

## Timer 4 SFR Addresses

| Address | Register | Purpose |
|---------|----------|---------|
| 0x90-0x91 | TREG4 | Timer 4 compare register (write-only) |
| 0x92-0x93 | TREG5 | Timer 5 compare register (write-only) |
| 0x98 | T4MOD | Timer 4 mode |
| 0x99 | T4FFCR | Timer 4 flip-flop control |
| 0x9E | T16RUN | 16-bit timer run control |
| 0xE6 | INTET45 | Interrupt priority/flags for INTTR4/INTTR5 |

## Related Pages

- [Feature Demo & Presentation System]({{ site.baseurl }}/feature-demo/)
- [Feature Demo Timer Behaviour]({{ site.baseurl }}/feature-demo-investigation-2026-03-09/)
