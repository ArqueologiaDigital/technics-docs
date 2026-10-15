---
layout: page
title: "Feature Demo Timer Behaviour"
permalink: /feature-demo-investigation-2026-03-09/
---

# Feature Demo Timer Behaviour

The Feature Demo has two independent subsystems:

1. **Demo timer** — a countdown at DRAM `0x0D2F`. It is set to 15 and acts at three
   thresholds: at **10** it loads the next demo song, at **3** it starts playback, at **1** it
   writes 0x85 to DRAM `0x2966`, which arms the sequencer transport.
2. **SSF visual presentation** — renders FTBMP bitmaps to the LCD from XML-scripted actions.
   See [Feature Demo & Presentation System]({{ site.baseurl }}/feature-demo/).

This page covers the timer.

## The Song-Load Path

`Demo_SelectEntry_PlaySong` (`demo/file_demo_proc.s:866`, `0xF86CF7`) runs when the timer reaches 10:

```
Demo_SelectEntry_PlaySong (0xF86CF7)
  → cp (CURRENT_MODE:16), 19            ; require DRAM[0x8D34] == 0x13 (MD_DEMO)
  → calr Demo_GetPresetBaseForPartAlt   ; read the song pointer from the table
  → call ToneGen_FileIO_SaveAndSync     ; configure song data
  → call SwbtWr_ReinitBothBanks         ; long-running (see below)
  → call Seq_DispatcherEntry
  → call SeqTimer_UpdateTempoReg
  → ld (0x8f4e:16), 6                   ; DRAM[0x8F4E] = 6 marks the song loaded
  → call Seq_DispatchEventType5         ; posts EVT_START_SONG
  → ret
```

## The Main Loop Stall (March 2026 Build)

> On the August 2026 kn7000_mame build the stall does not reproduce. The countdown goes from 10
> to 9 in 0.51 s (t = 24.19 → 24.70 s; the other steps take about 0.1 s;
> `notes/p9-countdown-2026-08-15.log` in kn7000_mame), so `Demo_SelectEntry_PlaySong` returns in
> about half a second. The measurements below were made in March 2026 on an older build.

`SwbtWr_ReinitBothBanks` (`system_handlers.s`) calls `SwbtWr_InitBank1` and `SwbtWr_InitBank2`
(both in `dsp_config_sysex.s`). Each enters `SwbtWr_DispatchLoop_Init`, which falls through into
`SwbtWr_DispatchLoop`:

```asm
SwbtWr_DispatchLoop_Init:           ; audio/dsp_config_sysex.s:927
    ldw (0xc07b:16), 0              ; reset buffer index to 0
                                    ; *** FALLS THROUGH ***
SwbtWr_DispatchLoop:
    ld xiy, (0xc089:16)             ; buffer base pointer
    add iy, (0xc07b:16)             ; + current index
    cp (xiy), 0xff                  ; terminator?
    jr z, SwbtWr_DispatchLoop_PostCallbacks
    ld l, (xiy)                     ; event type byte
    ld (SWBTWR_EVENT_TYPE:16), l    ; event type -> 0xC080
    ; ... call every listener for this event ...
    addw (0xc07b:16), 4             ; advance 4 bytes
    jrl SwbtWr_DispatchLoop         ; tight loop — no yield
```

The loop walks every buffered event until it hits the `0xFF` terminator, calling a tone
generator callback each time. It does not yield, so the whole firmware main loop — including
`Demo_SelectEntry_TimerTick` — stops while it runs, and the timer sits at 10.

The stall is **temporary**, not a deadlock. In the March 2026 MAME build it cleared after
roughly 960 frames (~16 seconds), across two bank re-initialisations:

| Frame | Event |
|-------|-------|
| 1225 | Timer reaches 10, `PlaySong` called |
| 1237 | Buffer processing begins (`buf_idx` starts climbing) |
| 1600 | `buf_idx` reaches 452, then resets for the second bank |
| 1686–2100 | Second bank cycle (`buf_idx` 0→488) |
| ~2200 | DRAM[0x8F4E] becomes `0x06` — `PlaySong` has returned |
| 2600 | Timer resumes: 10→9→8→… |
| 3000 | Timer at 4, system running normally |

The index at `0xC07B` is a byte offset that advances by 4 per event (`addw (0xc07b:16), 4`,
`audio/dsp_config_sysex.s:983`), so the two passes dispatched about 113 and 122 events, roughly
three frames per event (frames 1237–1600 for the first pass).

Observable signature while the stall is in progress:

| Signal                     | Value                         | Meaning                              |
|----------------------------|-------------------------------|--------------------------------------|
| DRAM[0x8F4E]               | stays `0x04`                  | `ld (0x8f4e:16), 6` has not executed |
| `swbt_idx` (DRAM `0xC07B`) | climbs 0→140+ over 130 frames | about 35 events, one per ~4 frames   |
| Timer (DRAM `0x0D2F`)      | stuck at 10                   | main loop blocked                    |
| event type (DRAM `0xC080`) | constant                      | the same event type throughout       |

## Open Questions

- **How long does the song load take on real hardware?** The March 2026 MAME build took about
  16 seconds and the August 2026 overlay build about half a second. The tone generator
  callbacks go to real hardware on the instrument and to HLE in MAME, so neither figure need
  match. Settling it requires a stopwatch on a real KN5000 entering the Feature Demo.
- **Does anything follow the first song?** Since
  [#15878](https://github.com/mamedev/mame/pull/15878) (merged 2026-08-17) the presentation
  runs in mainline MAME (DEMO, LEFT 4, LEFT 2), so the `0x1C00038` filter mismatch recorded in
  March (LEFT 2 gave param upper16 = `0xAA0A`, which matches none of the five registered
  filters `0x1000`–`0x1400`) was not what kept it from starting. In the kn7000_mame overlay
  build (2026-08-15) one song plays to a correct STOP at about 139 s, and the countdown at
  `0x0D2F` is armed once and not re-armed (kn7000_mame `notes/FINDINGS-p9-demo-stops.md`).
  Whether anything should follow is open: the owner describes the presentation as one
  continuous piece.

## Demo Song Pointer Table

The table at `0x9C4000` in the Table Data ROM holds 19 valid entries (indices 0–18); entry 18
is `0x008E0000` and entry 19 is NULL, ending the list. The current index lives at DRAM `0x28A4`
(10404, `DEMO_ACTIVE_ENTRY`). It is written by `Demo_SelectEntry_LoadPattern`
(`demo/file_demo_proc.s:850`), by the `EVT_DEMO_SONG_SEL` handler `MiddleFuncCall_DispatchData`
(`demo/demo_seq_bridge.s:27`), by `PresBox_OK` (`ui/drawbar_panel_ui.s:18423`), and by
`MainPreControl_OnStartPresentation` (`demo/file_demo_proc.s:196`), which sets 19, the NULL
entry, when a presentation loaded from disk starts.

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

| Address    | Name                     | Purpose                                                                                                                                                                                                                                                                              |
|------------|--------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `0x0D2F`   | Demo timer               | Countdown, set to 15; acts at 10 / 3 / 1                                                                                                                                                                                                                                             |
| `0x8F4E`   | Playback state           | `PlaySong` sets it to 6; `0x04` means it has not returned                                                                                                                                                                                                                            |
| `0x8D34`   | UI state                 | Must be `0x13` for `PlaySong` to execute                                                                                                                                                                                                                                             |
| `0x8D38`   | UI sub-state             | `0xE4` = Feature Presentation mode                                                                                                                                                                                                                                                   |
| `0xC07B`   | SwbtWr buffer index      | Current read position in the dispatch buffer                                                                                                                                                                                                                                         |
| `0xC089`   | SwbtWr buffer base       | Pointer to the event buffer                                                                                                                                                                                                                                                          |
| `0xC080`   | Event type               | Type of the event being dispatched, written per event (`SWBTWR_EVENT_TYPE` in the source)                                                                                                                                                                                            |
| `0xC07D`   | Event payload byte 1     | Payload byte 1 of the event being dispatched (`SWBTWR_PAYLOAD_1` in the source)                                                                                                                                                                                                      |
| `0x0251D8` | Presentation-loaded flag | Set to 1 only by `Seq_InitializeAndStart` (a presentation started from disk); stays 0 while the ROM presentation runs                                                                                                                                                                |
| `0x28A4`   | Demo entry index         | Current song index                                                                                                                                                                                                                                                                   |
| `0x28B4`   | Guard variable           | ~~Song list pointer~~ -- the code disagrees (2026-10-03): it is a word of per-part bits the sequencer sets (`SeqReassign_OrPartBits`) and clears (`SeqCh_ClearActive_ShiftDone`, `PartDeact_*`), named `SEQ_ACTIVE_PARTS` in the source; the demo handlers test it with `cpw (..),0` |

## Related Pages

- [Feature Demo & Presentation System]({{ site.baseurl }}/feature-demo/)
- [Timer 4/5 and the Sequencer Clock]({{ site.baseurl }}/feature-demo-timer-bug-2026-03-09/)
