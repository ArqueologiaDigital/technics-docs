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

The program declares 23 `PP50*` functions.  Which PC-link command each one that talks to the keyboard sends
(the disassembly's `notes/open4-kn5000-b/hdae/probes/ppkn50_command_map.py`, from the
`push <command>; push <port>; call 0x10002810` before each link transaction; the commands are those of
[HDAE5000 Filesystem: PC-link packets]({{ site.baseurl }}/hdae5000-filesystem/#pc-link-packets)):

| Export                           | Commands | Export                            | Commands |
|----------------------------------|----------|-----------------------------------|----------|
| `PP50TestTheKNPP`                | 1        | `PP50SendFileFromPCToKNMem`       | 10       |
| `PP50EscapeKeyboardToPlay`       | 2        | `PP50SendFileFromPCToKNHD`        | 10       |
| `PP50ReadFsbFromKnHdToKnMem`     | 3        | `PP50SaveFileFromKNMemToKNHd`     | 11       |
| `PP50SendFsbFromKnMemToPC`       | 4        | `PP50SaveFileFromPCDirectToKNHd`  | 13       |
| `PP50SendFsbFromPCToKnMem`       | 5        | `PP50SavePCMemDirectToKNHd`       | 13       |
| `PP50WriteFsbFromKnMemToKnHd`    | 6        | `PP50SendSeveralFileDirectToKNHD` | 13, 6    |
| `PP50LoadFileFromKnHdToKnMem`    | 7        | `PP50TestSongInfoFromKnHd`        | 14       |
| `PP50LoadFileFromKnHdToPC`       | 8        | `PP50DeleteFileOnKnHd`            | 16       |
| `PP50LoadFileFromKnHdDirectToPC` | 9        | `PP50FormatTheKn50HardDisk`       | 17       |
|                                  |          | `PP50TurnOffTheKn50HdMotor`       | 18       |

The remaining declared functions, among them `PP50InitializeTheDll`, `PP50OpenThePortNumber` (LPT 1-3) and
`PP50CloseThePort`, set up the port and send no command.  ppkn50.dll also exports four functions the program does
not declare (`AskTheConvMem`, `OpenThisFile`, `SaveThisFile`, `PP50TestParallelModus`), which send nothing.
Commands 12, 15, 19 ("nothing") and 20 (the v2.x XAP flash) are never sent.  (The disassembly's
`hdae5000/hd-techmanager5000/ppkn50-protocol-analysis.md` used to give 02 as "TestTheKNPP" and to write the decimal
commands 10, 11, 16, 17, 18 as 0x10 ... 0x18; corrected there on 2026-10-31.)

## The software

The archived disks are Wise installers: each file is a raw deflate stream followed by its CRC-32
(`notes/open4-kn5000-b/hdae/probes/wise_scan.py` in the disassembly finds every member by trying an inflate at each
offset: 71 members in the `setup.EXE` + `setup.W02` set, 80 in the `HDTMD120.EXE` + `.W02` set).

- **`setup.EXE` / `setup.W02`** install **HD-TechManager5000 v1.40** (the install notes call it "Version 1.40",
  from keysoftservice.ch): `HD-TechManager5000.exe`, a Visual Basic 5 program (1,353,728 bytes, importing only
  `MSVBVM50.DLL`) over `ppkn50.dll` (byte-identical to the copy in the disassembly's `hdae5000/hd-techmanager5000/`),
  with German and English help (`D_hilfe.hlp`, `E_help.hlp`), `ReadMe.doc`, `Fls.ini` and sample songs (four, as
  .lsw / .pmt / .sqt / .tm / .cmp; the .tm members are 0x72AA bytes beginning "KN5000 SOUND RAM").  This software
  cannot use the v2.x XAP flash command (above).
- **Files on the PC.**  The program's strings name the PC copies of the three table blocks, `Dirblk.dat`,
  `Fileblk.dat` and `Flsblk.dat` (the raw blocks of
  [the filesystem's tables]({{ site.baseurl }}/hdae5000-filesystem/#the-tables-sectors-3908-4230): 16 × 120,
  76 × 1,920 and 144 × 120 bytes), with `Dirdumy.dat` / `Filedumy.dat` / `Flsdumy.dat` and `Filesic.dat` /
  `Flssic.dat` beside them, a `Manager.ini`, a `Backup.log` and the file filter `*.cmp;*.sqt;*.tm;*.lsw;*.msp`.
  [inference, from the names] "dumy" are blank images and "sic" (Sicherung) safety copies.  The install notes say
  the backup stores each song's parts plus a `.TTX` file "with long name" per song, so a disk backup can be
  restored with the 26-character names; and that "COPY TO HD-AE" sends a floppy of Technics files with a text file
  of titles supplied by the software publishers (Tech-Note, Taiyo, Mister Music, Technisoft, Musikstudio Witten).
- **`HDTMD120.EXE` / `.W02`** is a different, 16-bit program for the KN3000's hard disk: it installs `Demo.exe`
  with `Kn30pp16.dll`, `Ppbas16.dll`, `Ppbcre16.dll`, `Psccprog.dll`, `Disk.dll`, `Filedir.dat` / `Fls.dat` /
  `Groupdir.dat` databases, Crystal Reports `.rpt` files and Visual Basic 4 (16-bit) runtimes, and its sample
  database lists folders named "KN 3000 1" ... "KN 3000 17".  It is not for the HD-AE5000.  The names
  "HD-TE96.exe" and "ConvKN.dll" that earlier notes gave are on neither disk set.
- **Not analysed.**  The VB5 program's body (its form logic) was not decompiled: no VB decompiler was at hand.  Its
  strings and its DLL calls are what this section uses.

Source: the disassembly's `notes/open4-kn5000-b/hdae/README.md`, "kn5000-qnf".

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
