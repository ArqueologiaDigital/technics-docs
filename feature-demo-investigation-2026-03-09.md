---
layout: page
title: "Feature Demo Timer Behaviour"
permalink: /feature-demo-investigation-2026-03-09/
---

# Feature Demo Timer Behaviour

The Feature Demo has two independent subsystems:

1. **Demo timer** — a countdown at DRAM `0x0D2F`. It is set to 15 and acts at three
   thresholds: at **10** it loads the next demo song, at **3** it starts playback, at **1** it
   updates the display.
2. **SSF visual presentation** — renders FTBMP bitmaps to the LCD from XML-scripted actions.
   See [Feature Demo & Presentation System]({{ site.baseurl }}/feature-demo/).

This page covers the timer.

## The Song-Load Path

`Demo_SelectEntry_PlaySong` (`file_demo_proc.s:718`, `0xF86E06`) runs when the timer reaches 10:

```
Demo_SelectEntry_PlaySong (0xF86E06)
  → cpdi8 36148, 19            ; require DRAM[0x8D34] == 0x13
  → calr Demo_GetPresetBaseForPartAlt   ; read the song pointer from the table
  → call ToneGen_FileIO_SaveAndSync     ; configure song data
  → call SwbtWr_ReinitBothBanks         ; long-running (see below)
  → call Seq_DispatcherEntry
  → stdi8 36686, 6                      ; DRAM[0x8F4E] = 6 marks the song loaded
  → ret
```

## The Main Loop Stalls for About 16 Seconds

`SwbtWr_ReinitBothBanks` (`system_handlers.s`) calls `SwbtWr_InitBank1` and `SwbtWr_InitBank2`
(both in `dsp_config_sysex.s`). Each enters `SwbtWr_DispatchLoop_Init`, which falls through into
`SwbtWr_DispatchLoop`:

```asm
SwbtWr_DispatchLoop_Init:           ; dsp_config_sysex.s
    stdi16 49275, 0                 ; reset buffer index to 0
                                    ; *** FALLS THROUGH ***
SwbtWr_DispatchLoop:
    ldda32 xiy, 49289               ; buffer base pointer
    addda16 xiy, 49275              ; + current index
    cp (xiy), 0xFF                  ; terminator?
    jr z, SwbtWr_DispatchLoop_PostCallbacks
    ; ... process one event, call the tone generator callback ...
    adddi16 49275, 4                ; advance 4 bytes
    jrl SwbtWr_DispatchLoop         ; tight loop — no yield
```

The loop walks every buffered event until it hits the `0xFF` terminator, calling a tone
generator callback each time. It does not yield, so the whole firmware main loop — including
`Demo_SelectEntry_TimerTick` — stops while it runs, and the timer sits at 10.

The stall is **temporary**, not a deadlock. In MAME it clears after roughly 960 frames
(~16 seconds), across two bank re-initialisations:

| Frame | Event |
|-------|-------|
| 1225 | Timer reaches 10, `PlaySong` called |
| 1237 | Buffer processing begins (`buf_idx` starts climbing) |
| 1600 | `buf_idx` reaches 452, then resets for the second bank |
| 1686–2100 | Second bank cycle (`buf_idx` 0→488) |
| ~2200 | DRAM[0x8F4E] becomes `0x06` — `PlaySong` has returned |
| 2600 | Timer resumes: 10→9→8→… |
| 3000 | Timer at 4, system running normally |

452+ events at roughly one callback per 5 frames (~35 ms each) accounts for the duration.

Observable signature while the stall is in progress:

| Signal | Value | Meaning |
|--------|-------|-------------|
| DRAM[0x8F4E] | stays `0x04` | `stdi8 36686, 6` has not executed |
| `swbt_idx` (DRAM `0xC07B`) | climbs 0→140+ over 130 frames | ~1 event per 5 frames |
| Timer (DRAM `0x0D2F`) | stuck at 10 | main loop blocked |
| chain (DRAM `0xC080`) | constant | no new events generated |

## Open Questions

- **Does ~16 seconds match real hardware?** The tone generator callbacks go to real DSP
  hardware on the instrument and to HLE in MAME, so the durations need not agree. Settling this
  requires a stopwatch on a real KN5000 entering the Feature Demo.
- **SSF event routing.** Event `0x1C00038` requires `UIState_KeyScan_Dispatch` to be called
  with the right UI state. LEFT 2 produces param upper16 = `0xAA0A`, which matches none of the
  five registered filters (`0x1000`–`0x1400`), and `demo_state` at `0x0251D8` stays `0x0000`.
  This is independent of the timer stall.

## Demo Song Pointer Table

The table at `0x9C4000` in the Table Data ROM holds 19 valid entries (indices 0–18); entry 18
is `0x008E0000` and entry 19 is NULL, ending the list. The current index lives at DRAM `0x28A4`
(10404) and is written by `drawbar_panel_ui.s:15232`.

## Source Files

| File | Key Functions | Relevance |
|------|---------------|-----------|
| `file_demo_proc.s` | `Demo_SelectEntry_TimerTick`, `Demo_SelectEntry_PlaySong`, `Demo_SelectEntry_ProcessSongList` | Timer state machine and song loading |
| `dsp_config_sysex.s` | `SwbtWr_DispatchLoop`, `SwbtWr_QueueMainEvent` | The non-yielding dispatch loop |
| `system_handlers.s` | `SwbtWr_ReinitBothBanks`, main loop Phase 4 | The initialisation that triggers the stall |
| `ui_control_panel.s` | `UIState_KeyScan_Dispatch` | Button event routing |
| `ui_widget_defs.s` | `EventDispatch_Direct` (0xFA9945) | Event filter matching |
| `cpanel_constants.s` | Button mapping tables | Physical button → event param |
| `cpanel_routines.s` | `CPanel_RX_ButtonPacket` | Control panel ISR |
| `smf_event_processor.s` | `Seq_DispatcherEntry`, `Seq_DispatcherTick` | Sequencer task scheduling |

## Key DRAM Addresses

| Address | Name | Purpose |
|---------|------|---------|
| `0x0D2F` | Demo timer | Countdown, set to 15; acts at 10 / 3 / 1 |
| `0x8F4E` | Playback state | `PlaySong` sets it to 6; `0x04` means it has not returned |
| `0x8D34` | UI state | Must be `0x13` for `PlaySong` to execute |
| `0x8D38` | UI sub-state | `0xE4` = Feature Presentation mode |
| `0xC07B` | SwbtWr buffer index | Current read position in the dispatch buffer |
| `0xC089` | SwbtWr buffer base | Pointer to the event buffer |
| `0xC080` | Chain byte | Handler chain selector |
| `0xC07D` | Param byte | Handler parameter |
| `0x0251D8` | Demo state | SSF presentation state |
| `0x28A4` | Demo entry index | Current song index |
| `0x28B4` | Guard variable | ~~Song list pointer~~ -- the code disagrees (2026-10-03): it is a word of per-part bits the sequencer sets (`SeqReassign_OrPartBits`) and clears (`SeqCh_ClearActive_ShiftDone`, `PartDeact_*`), named `SEQ_ACTIVE_PARTS` in the source; the demo handlers test it with `cpw (..),0` |

## Related Pages

- [Feature Demo & Presentation System]({{ site.baseurl }}/feature-demo/)
- [Timer 4/5 and the Sequencer Clock]({{ site.baseurl }}/feature-demo-timer-bug-2026-03-09/)
