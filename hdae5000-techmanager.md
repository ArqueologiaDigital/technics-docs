---
layout: page
title: TechManager5000 Emulation Plan
permalink: /hdae5000-techmanager/
---

# HD-TechManager5000 Emulation Plan

*Last updated: October 15, 2026*

The HD-TechManager5000 is a Windows application that communicates with the HD-AE5000 expansion board via a PC parallel port cable (DB25 to DB15). It enables file management, backup, and formatting of the HDAE5000 hard disk from a PC. This page documents plans for running the original, unmodified TechManager5000 software alongside the KN5000 MAME emulation.

> **Preservation principle**: The TechManager5000 software must run **completely unmodified**. No patching, DLL replacement, or binary modification. The original `ppkn50.dll` performs direct I/O port access (`in`/`out` to LPT base+0/1/2) and must see real (emulated) LPT hardware.

> **See Also**: [HDAE5000 Disk Interface]({{ site.baseurl }}/hdae5000-disk-interface/) for the parallel port protocol details, [HDAE5000 MAME Setup]({{ site.baseurl }}/hdae5000-mame-setup/) for basic setup.

> **Update (2026-09).** Plans A and B below are no longer just proposals — a third
> architecture was actually built on the `kn5000_research_techmanager`
> branch of the [felipesanches/mame fork](https://github.com/felipesanches/mame/tree/kn5000_research_techmanager)
> (9 commits, 2026-03-30/31, no pull request), and it isn't either plan as written. Instead
> of a TCP bridge or a symmetric composite driver, `kn5000_state` was refactored from
> `driver_device` to `device_t` (following MAME's Sega System 32 dual-PCB pattern) so the
> whole KN5000+HDAE5000 machine can be instantiated as a **centronics peripheral device**
> that plugs into any stock PC driver's LPT slot — e.g. `mame at486
> -board4:lpt:centronics kn5000_cable`. This needed a new `kn5000_cable` device wiring the
> HDAE5000's PPI (Port A/B/C at `0x160000`-`0x160004`) to the centronics lines in both
> directions, plus a PS/2 bidirectional-mode fix to MAME's `pc_lpt` device (`data_r()` was
> masking peripheral response bits against the host's own output latch — exactly the mode
> `ppkn50.dll` uses). As of the branch's last commit, the bidirectional signal path (PC → KN5000
> via direct PPI input wiring, KN5000 → PC via write taps on the PPI output ports) is wired
> end-to-end. It has not been run against the real, unmodified TechManager5000 software as
> part of this review, and the project's own PR-planning notes call it "genuinely interesting
> research... not close to PR shape" — so treat it as a working prototype of the signal path,
> not a finished, submitted, or upstream feature. The comparison below is kept for its
> original planning value, but the "Status" section is stale and is corrected further down.

## Background: How ppkn50.dll Works

The `ppkn50.dll` library (disassembled and fully documented) communicates with the HDAE5000 using:

- **PC parallel port registers**: Data (base+0 = 0x378), Status (base+1 = 0x379), Control (base+2 = 0x37A)
- **HDAE5000 PPI registers**: Port A (0x160000), Port B (0x160002), Port C (0x160004)
- **Custom handshake protocol**: Strobe/ACK/BUSY signaling, not standard Centronics
- **Timeouts**: 10,000ms per byte transfer, 512 polling iterations before time check

The DLL exports 23 `PP50*` functions, among them:

| Function                      | Description                   |
|-------------------------------|-------------------------------|
| `PP50InitializeTheDll`        | Initialize DLL                |
| `PP50OpenThePortNumber`       | Select LPT port (1-3)         |
| `PP50CloseThePort`            | Close parallel port           |
| `PP50TestTheKNPP`             | Test connection to KN5000     |
| `PP50ReadFsbFromKnHdToKnMem`  | Read filesystem block from HD |
| `PP50SendFsbFromKnMemToPC`    | Transfer FSB to PC            |
| `PP50SendFsbFromPCToKnMem`    | Transfer FSB to KN            |
| `PP50LoadFileFromKnHdToKnMem` | Download file from HD         |
| `PP50DeleteFileOnKnHd`        | Delete file on HD             |
| `PP50FormatTheKn50HardDisk`   | Format hard disk              |
| `PP50TurnOffTheKn50HdMotor`   | Spin down drive motor         |

## Plan A: Two MAME Instances (TCP Bridge)

Two separate MAME processes communicate over a TCP socket on localhost:

```
┌──────────────────────────────────────────────────────────────┐
│  MAME instance 1 (PC emulation)                              │
│  ┌────────────────────┐    emulated LPT    ┌───────────────┐ │
│  │ Windows 95 + HD-   │ ◄────────────────► │ Emulated      │ │
│  │ TechManager5000    │   I/O port 0x378   │ parallel port │ │
│  │ (unmodified)       │                    │ hardware      │ │
│  └────────────────────┘                    └───────┬───────┘ │
└────────────────────────────────────────────────────┼─────────┘
                                                     │ TCP socket
┌────────────────────────────────────────────────────┼─────────┐
│  MAME instance 2 (KN5000 emulation)                │         │
│  ┌──────────┐    PPI callbacks    ┌────────────────┴──────┐  │
│  │ KN5000 + │ ◄─────────────────► │ PPI socket device     │  │
│  │ HDAE5000 │    Port A/B/C       │ (listens for PC MAME) │  │
│  └──────────┘                     └───────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### How it works

1. **MAME (KN5000)** runs the keyboard emulation with HDAE5000. The PPI device is bridged to a TCP socket listener.
2. **MAME (PC)** runs a Windows 95 PC driver (e.g., `pcipc`) with TechManager5000 installed on its emulated hard disk. The PC's emulated LPT parallel port connects to the KN5000 MAME instance via TCP.
3. `ppkn50.dll` executes `in`/`out` instructions to the PC's LPT port --- which is real (emulated) hardware from its perspective. The emulated LPT hardware relays the signals to the KN5000's PPI over TCP.

### Implementation needed

- **KN5000 side**: Socket-based PPI bridge device (exposes Port A/B/C over TCP)
- **PC side**: Socket-based external connection for MAME's centronics/LPT device
- **PC disk image**: Windows 95 installation + TechManager5000

### Open questions

- Which MAME PC driver has the best LPT parallel port emulation?
- Does MAME's existing parallel port infrastructure support external socket connections?
- Can MAME's `bitbanger` device serve as the socket transport on both sides?

## Plan B: Single MAME Instance (Multi-Driver)

Run both the KN5000 and a PC driver within a single MAME instance, with the parallel ports wired directly:

```
┌─────────────────────────────────────────────────────────────────┐
│  Single MAME instance                                           │
│                                                                 │
│  ┌────────────────────┐    direct wire    ┌───────────────────┐ │
│  │ Windows PC driver  │ ◄──────────────► │ KN5000 + HDAE5000 │ │
│  │ (pcipc / at)       │   centronics ←→   │ PPI @ 0x160000    │ │
│  │ + TechManager5000  │   PPI callbacks   │                   │ │
│  └────────────────────┘                   └───────────────────┘ │
│                                                                 │
│  Both machines share the same scheduler, so handshake timing    │
│  is cycle-accurate with no socket latency.                      │
└─────────────────────────────────────────────────────────────────┘
```

### Advantages over Plan A

- No TCP socket overhead or timing concerns
- Single process, single scheduler --- handshake signals propagate within the same emulation cycle
- Simpler to launch (one command line)
- More faithful to the original hardware setup (two physical devices connected by a cable)

### Implementation needed

- A MAME "null cable" device that cross-wires the PC's LPT data/status/control lines to the HDAE5000's PPI Port A/B/C, with appropriate signal inversion (PC parallel port inverts BUSY on bit 7)
- A composite driver or multi-machine configuration that instantiates both the KN5000 and a PC system
- Shared display (two screens, or a split layout)

### Open questions

- Does MAME support running two independent machine drivers in one instance? (Multi-system configurations exist for linked arcade cabinets --- can this pattern be reused?)
- How to handle two independent CPUs with different clock domains in the same scheduler?
- How to present two screens (KN5000 LCD + PC VGA) to the user?

## Comparison

| Aspect | Plan A (Two instances) | Plan B (Single instance) |
|--------|----------------------|-------------------------|
| Timing accuracy | Good (10s timeout is generous) | Perfect (same scheduler) |
| Complexity | Lower (independent processes) | Higher (multi-machine config) |
| User experience | Two windows, two commands | One window, one command |
| Latency | TCP localhost (~microseconds) | Zero (direct callback) |
| MAME precedent | Common (networked games) | Exists (linked cabinets) |
| Preservation fidelity | Good | Best (models the physical cable) |

## Status

Neither Plan A nor Plan B as written was the path actually taken — see the update note at
the top of this page. Superseding status:
1. The HDAE5000 PPI callbacks are wired on the fork branches `kn5000_research_techmanager`
   (published) and `kn5000_pr6_hdae5000` (local only), both 2026-03-30; upstream MAME and
   the kn7000_mame overlay still leave them unconnected
2. A working ATA interface with disk image support is in the kn7000_mame overlay (patch
   `kn5000-19-hdae5000-ata-intrq`) and on those branches; upstream MAME still stubs the ATA
   registers
3. A third architecture (KN5000+HDAE5000 as a centronics peripheral of a stock PC driver,
   `kn5000_research_techmanager` branch) has the bidirectional PPI↔centronics signal path
   wired end-to-end, but has not been validated against the real TechManager5000 software
   and is explicitly not close to PR/upstream shape.

## Related Pages

- [HDAE5000 MAME Setup]({{ site.baseurl }}/hdae5000-mame-setup/) --- Basic emulator setup
- [HDAE5000 Disk Interface]({{ site.baseurl }}/hdae5000-disk-interface/) --- Parallel port protocol details
- [HDAE5000 Filesystem]({{ site.baseurl }}/hdae5000-filesystem/) --- On-disk data structures
