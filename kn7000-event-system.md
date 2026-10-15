---
layout: page
title: KN7000 Event & Dispatch System
permalink: /kn7000-event-system/
---

# KN7000 Event & Dispatch System

The KN7000's user interface is **event-driven**, built on the same object-oriented
"MILK" toolkit as the [KN5000]({{ site.baseurl }}/ui-framework/). Screens are trees of *objects*
(windows, boxes, switches, list boxes…); the firmware delivers **events** to an
object's *window procedure* (`…Proc`), which updates state and redraws. This page
documents the KN7000 implementation as recovered from the firmware itself — the
event-code table and the dispatch functions are both decoded directly from
`kn7000_program.rom`, and the named functions below are converted to readable,
re-assemblable source in the [disassembly project]({{ site.baseurl }}/kn7000-firmware/).

## Event codes

The firmware embeds a 60-entry name table (program file `0x326BF0`) enumerating
every event type. The **event code is the table index**, so `EV_NONE = 0`,
`EV_SHOW = 1`, and so on. They are close kin of the KN5000's
[event codes]({{ site.baseurl }}/event-codes/), the shared framework, but only the names
carry across, not the numbers. 51 of the 60 names occur in both firmwares, yet only 4
indices hold the same name: `EV_NEW_TITLE` is `0x31` here and `0x39` on the KN5000,
and `0x0F` is `EV_INDEXSW_UP` here but `EV_PARADRAW` there. The nine KN7000-only
names are `EV_MMMDATA`, `EV_MEMDUMP`, `EV_TRANSDRAW`, `EV_INDEXSW_ON`,
`EV_INDEXSW_OFF`, `EV_SOUNDDSPNAME`, `EV_LARGECHANGE`, `EV_WALLPREVIEW` and
`EV_WAITDRAW`; none of them is an SD-card event.

| Code | Name | Code | Name |
|------|------|------|------|
| 0x00 | `EV_NONE` | 0x1E | `EV_AUTOINC` |
| 0x01 | `EV_SHOW` | 0x1F | `EV_SWIN_AIC` |
| 0x02 | `EV_HIDE` | 0x20 | `EV_RETURN_TITLE` |
| 0x03 | `EV_MOVE` | 0x21 | `EV_IAMSELECTED` |
| 0x04 | `EV_ACTION` | 0x22 | `EV_YOUARESELECTED` |
| 0x05 | `EV_SWIN` | 0x23 | `EV_SENDSWIN` |
| 0x06 | `EV_SWON` | 0x24 | `EV_CHANGEDIALFOCUS` |
| 0x07 | `EV_SWOFF` | 0x25 | `EV_TRSWPART` |
| 0x08 | `EV_ALLPAINT` | 0x26 | `EV_TRSWCOMMAND` |
| 0x09 | `EV_PAINT` | 0x27 | `EV_PARTSELECT` |
| 0x0A | `EV_RESET` | 0x28 | `EV_SWBOTH` |
| 0x0B | `EV_ACTIVATE` | 0x29 | `EV_INDEXSW_BOTH` |
| 0x0C | `EV_CHANGE_MODE` | 0x2A | `EV_SENDSWON` |
| 0x0D | `EV_CHANGE_TITLE` | 0x2B | `EV_SENDSWOFF` |
| 0x0E | `EV_INTERRUPT_TITLE` | 0x2C | `EV_SENDSWBOTH` |
| 0x0F | `EV_INDEXSW_UP` | 0x2D | `EV_PAGEINIT` |
| 0x10 | `EV_INDEXSW_DOWN` | 0x2E | `EV_UPDATESCREEN` |
| 0x11 | `EV_INDEXSW_UP_AIC` | 0x2F | `EV_DELIVERYEVENT` |
| 0x12 | `EV_INDEXSW_DOWN_AIC` | 0x30 | `EV_ASSSWB` |
| 0x13 | `EV_INDEXSELECT` | 0x31 | `EV_NEW_TITLE` |
| 0x14 | `EV_MMMDATA` | 0x32 | `EV_OLD_TITLE` |
| 0x15 | `EV_RAMDATA` | 0x33 | `EV_MEMDUMP` |
| 0x16 | `EV_PAGECHANGE` | 0x34 | `EV_TRANSDRAW` |
| 0x17 | `EV_DIAL` | 0x35 | `EV_INDEXSW_ON` |
| 0x18 | `EV_SOUNDNAME` | 0x36 | `EV_INDEXSW_OFF` |
| 0x19 | `EV_RHYTHMNAME` | 0x37 | `EV_SOUNDDSPNAME` |
| 0x1A | `EV_PMEMNAME` | 0x38 | `EV_LARGECHANGE` |
| 0x1B | `EV_SOUNDSWNO` | 0x39 | `EV_WALLPREVIEW` |
| 0x1C | `EV_BITDATA` | 0x3A | `EV_WAITDRAW` |
| 0x1D | `EV_MEMODRAW` | 0x3B | `EV_SWIN_MODE` |

The families are recognisable: lifecycle (`EV_SHOW`/`EV_HIDE`/`EV_RESET`), drawing
(`EV_PAINT`/`EV_ALLPAINT`/`EV_UPDATESCREEN`), panel input (`EV_INDEXSW_*`,
`EV_DIAL`, `EV_SWON`/`EV_SWOFF`), focus/selection (`EV_IAMSELECTED`,
`EV_CHANGEDIALFOCUS`, `EV_PARTSELECT`), and data-changed notifications
(`EV_SOUNDNAME`, `EV_RHYTHMNAME`, `EV_MMMDATA`, …).

## The object table

Live UI objects are kept in a fixed table in work RAM at **`0x5000757C`**, with
**`0x38` (56)-byte slots** indexed by object id. Three functions compute a slot
address the same way (`base + id*0x38`), which is how the geometry is known;
`GetCurrentTarget` is the clearest:

```
GetCurrentTarget:                 # CPU 0x4842943B
    add     -0x10, sp
    mov     sp, a0
    add     0xc, a0               # a0 -> a halfword on the stack
    call    func_48414A4F, [a2], 4  # GetCurrentObjectId (below): id -> (a0)
    movhu   (0xc, sp), d0         # d0 <- the active object's id
    mov     0x38, d1
    exth    d0
    mul     d1, d0                # id * 0x38
    add     0x5000757c, d0        # + table base  => &slot[id]
    mov     d0, a0
    mov     (0x10, a0), d0        # slot + 0x10 = the object's current target
    ret     0, 0x10
```

So **offset `+0x10`** within a slot holds the object's current target reference.
`InitializeEventQueue` (`0x484284B4`) walks the same table to reset a slot. Other
framework accessors (e.g. `SetVisible`, `SetChange`) instead reach their object
through a linked-view pointer via the hot helper `GetLinkView` and test flag bits
in it.

## Two tasks: main and AP

The KN7000 runs two cooperative UI tasks — a **main** task and an **AP**
(application) task — matching the `SleepMainTask`/`SleepApTask` /
`WakeUpMainTask`/`WakeUpApTask` pair. The helper that every event call uses to
find "the current object" selects between the two:

```
GetCurrentObjectId:               # CPU 0x48414A4F  (func_48414A4F)
    mov     (0x50380004), a2      # current-task handle
    mov     (0x5038002c), a1      # main-task handle
    cmp     a1, a2
    bne     .ap                   # not the main task -> AP path
    movhu   (0x500d3c60), d0      # main task's focused-object id
    movhu   d0, (a0)
    bra     .done
.ap:
    movhu   (0x500d3c5c), d0      # AP task's focused-object id
    movhu   d0, (a0)
.done:
    clr     d0
    retf    [a2], 4
```

i.e. the *focused object id* is kept per task (`0x500D3C60` for main,
`0x500D3C5C` for AP), and is chosen by comparing the running task handle
(`0x50380004`) against the main-task handle (`0x5038002C`).

## Dispatch API

The public entry points, all recovered by name and converted to source:

| Function | CPU addr | Role |
|----------|----------|------|
| `InitializeEventQueue` | `0x484284B4` | reset an object's slot in the table |
| `DispatchEvent` | `0x4842936F` | deliver the **current** object's pending event now (no args) |
| `SendEvent` | `0x48429388` | deliver an event synchronously, with a param word |
| `PostEvent` | `0x484293AD` | enqueue an event for later delivery |
| `GetEvent` | `0x484293D2` | fetch an event `(obj, a0, a1)` for processing |
| `GetCurrentTarget` | `0x4842943B` | the active object's current target (slot `+0x10`) |

Most begin by resolving the current object via `GetCurrentObjectId`, then hand
off to a lower-level queue/dispatch helper (`func_48428…`) that walks the object
tree and invokes the target's window procedure. (`DispatchEvent` is argument-less
precisely because it acts on the *current* object rather than a passed-in one —
the detail that finally disambiguated the reflection-table alignment, see below.) The window procedure itself is
looked up through the toolkit's `MT_GetProcedure` mechanism — the same
reflection tables that let us recover **518 `*Proc` handlers** by name (see the
[firmware page]({{ site.baseurl }}/kn7000-firmware/)). A handler is therefore a function that
switches on the event code and acts:

```c
// shape of a MILK window procedure (Ac*/Vw*/Iv*/Ps*/Tt*Proc)
long SomeWidgetProc(object *self, int event, long param) {
    switch (event) {
        case EV_SHOW:   ... ; break;
        case EV_PAINT:  ... ; break;
        case EV_ACTION: ... ; break;   // the switch was pressed / activated
        ...
    }
}
```

## A note on the recovered names

The names above are recovered by pairing each reflection table's code-pointer
array with its parallel name-pointer array. Getting the **alignment** right
matters: a one-slot shift silently labels every function with a neighbour's name.
The alignment was pinned down behaviourally — under the correct pairing every
`Get*` accessor reads its variable and every `Set*` writes it, with no
exceptions, whereas the shifted pairing produces impossible "getters" that write
memory. That check is what confirms, for instance, that the argument-less
`0x4842936F` is `DispatchEvent` (acting on the current object) rather than a
similarly argument-less `InitializeEventQueue`.

## Relationship to the KN5000

The event **names and dispatch shape are shared** with the KN5000 (the code numbers
are not; see above) — both firmwares are re-targets of one MILK-based source tree
(see the [Shared Codebase Map]({{ site.baseurl }}/technics-shared-codebase/)). What
differs is machine-specific: the KN7000 adds wallpaper, DSP-sound and drawing events
(none for the SD card), runs on the MN10300 rather than the TLCS-900, and keeps its
object table at a different RAM address. The KN5000 [Event
Codes]({{ site.baseurl }}/event-codes/) and [UI
Framework]({{ site.baseurl }}/ui-framework/) pages remain the best conceptual
companions to this one.
