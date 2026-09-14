---
layout: page
title: Help Wanted
permalink: /help-wanted/
---

# How You Can Help

This is a community reverse engineering project. Here's how you can contribute:

**Current Progress:** thirteen ROM images — nine KN5000 and four SX-WSA1R — **rebuild byte-identically** from assembly source, gated by `make gate-all` and built with a custom LLVM TLCS-900 backend. Twelve of those images are 12,386,304 distinct bytes (the thirteenth is a compressed re-encoding of one of the others), and about 93.8 % of them can be *explained* — what the data represents, not merely that it reproduces — with a 95 % confidence interval of 86.7 – 96.6 %.

Where to look for work: the open technical unknowns are on [Open Questions]({{ site.baseurl }}/questions/), the programme-level plan is on the [Roadmap]({{ site.baseurl }}/roadmap/), and what the emulator does not model yet is on [MAME Emulation Gaps]({{ site.baseurl }}/mame-emulation-gaps/).

## High Priority

### ROM Dumps Needed

We're missing ROM dumps for several chips:
- **Control Panel MCUs** (Mitsubishi M37471M2196S) - Custom-masked ROMs handling buttons, LEDs, and rotary encoders. These would require decapping to dump.
- **Any other undumped chips** on the KN5000 board

If you have a KN5000 and can dump ROMs, please reach out!

### ROM Disassembly Improvements

All thirteen images byte-match, every symbol carries a semantic name, and the NAKA widget and
sound data files are typed C structs rather than raw byte arrays.

**Byte-match is not the same as understood, and this is the honest backlog.** A 100 % byte
match is preserved by construction and says nothing about how much of the build is real source
rather than `.incbin` passthrough or code spelled as `.byte`. What is genuinely open:

- **Code still written as `.byte`.** The v7 main-CPU tree holds 236,713 B in confirmed regions
  plus 29,032 B in misframed islands; HD-AE5000 holds 13,168 B. Every other image is at zero.
  Method and per-image measurement on
  [Raw Byte Code Elimination]({{ site.baseurl }}/raw-byte-code-elimination/).
- **Two LLVM wrapper mnemonics.** `lda_dpi` (669 sites) and `bit_dri` (189) cannot be renamed
  until their operands are modelled in the backend — see
  [LLVM Semantic Instructions]({{ site.baseurl }}/llvm-semantic-instructions/).
- **Firmware versions with no source tree.** v5, v6 and v8 on the main CPU; v1.40 and v1.41 on
  the sub-CPU payload. v8 differs from v9 by the version byte alone, so it is the cheapest of
  them by a wide margin.
- **A C port beyond data.** The C files in the tree are all `__attribute__((packed))` struct
  initializers; **no firmware routine is written in C yet.** Converting leaf functions while
  holding byte-identity is open work with a working compiler behind it.

### HDAE5000 ROM Disassembly

The HD-AE5000 hard disk expansion ROM has been partially analyzed but needs complete disassembly:

**Known Entry Points:**
- Boot initialization at 0x28F576 (called via JP at 0x280008)
- Frame handler at 0x28F662 (called via JP at 0x280010)

**Analysis Tasks:**
- Disassemble PPORT command handlers (15 commands documented)
- Document FSB (File System Block) structure
- Trace HD controller communication routines
- Analyze Windows DLL callback interfaces
- Document file transfer protocol details

**Skills Needed:** TLCS-900 assembly, parallel port protocols, filesystem analysis

See [HDAE5000 page]({{ site.baseurl }}/hdae5000/) for current findings.

### Assembly Analysis

Help analyze the disassembled code:
- Trace execution paths through undocumented routines
- Document serial protocol command/response patterns
- Map button/LED indices to physical panel locations
- Identify data structures and their purposes

### Testing

If you have a working KN5000:
- Test homebrew code on real hardware
- Capture serial protocol traces with logic analyzer
- Document hardware behavior for edge cases
- Take photos of PCB for chip identification

### ~~Read six pins on the SX-WSA1R's effects board~~ — ✅ **ANSWERED 2026-09-15**

Kept here because the *method* is the reusable part, and because the answer is a negative
worth stating loudly.

**The question was:** where do **IC30 pins 83–88** go? In the CDJ-500 pin table those are
`RQ1`–`RQ3` (host-written, testable by an instruction's condition field) and `GF1`–`GF3`
(set by instructions, host-readable). Neither the condition field nor the flag-setting
instruction has been located in the microcode, and neither MAME driver wires the pins.

**The answer, read at 400 dpi off the WSA1R service manual, sheet II-15/II-16:**

- `RQ1`, `RQ2`, `RQ3` (86, 87, 88) are **tied together and strapped to ground** — the host
  can never vary them.
- `GF1`, `GF2`, `GF3` (83, 84, 85) are **short stubs with no net, no strap and no
  destination** — the host can never read them.

⇒ the flag/condition decode route is **dead on the SX-WSA1R**. The honest report is
*"not available on this machine"* — **never** *"the chip has no `COND` field"*: the pins
exist on the die, and the CDJ-500 may well wire them. See the
[pinout]({{ site.baseurl }}/upd6383-datasheet/#2-pinout).

⚠ It cost one `pdftoppm` command. These service manuals are **image-only scans** —
`pdftotext` and `grep` return nothing from them, and that has produced two false negatives
on this project. **Render the page before concluding anything is undocumented.**

### Still wanted: a Pioneer CDJ-500 firmware dump

The CDJ-500 / CDJ-500G uses the same µPD6383GF as IC302, and its DSP-shaped feature —
**Master Tempo**, key-lock pitch shifting — is microcode neither Technics corpus contains.
It is worth **+214 decoded words** once the corpus-side work is done (and, measurably,
almost nothing before then — see the
[route to 100 %]({{ site.baseurl }}/upd6383-decode-status/#5-the-routes-ranked-cheapest-and-safest-first)).

A cheap second-hand player and a ROM reader is the whole shopping list. **What is needed is
the firmware dump, not the service manual** — we have the manual.

## Medium Priority

### Documentation

- Improve code comments in the disassembly
- Write tutorials for new contributors
- Translate documentation to other languages
- Create diagrams of system architecture

### MAME Development

- Help implement HLE for control panel MCUs
- Test emulation accuracy
- Debug emulation issues
- Improve audio emulation

### Tooling

- Extend LLVM TLCS-900 backend for remaining niche encodings (compact zero-load, compact load-1, dec/inc N xsp)
- Create visualization tools for protocol analysis
- Build comparison/diff tools for ROM analysis

## Contribution Guidelines (STRICT POLICIES)

These policies ensure the disassembly remains useful for understanding the firmware, not just rebuilding it.

### Symbolic Cross-Referencing

**All cross-references must be symbolic (using labels), never numeric addresses.**

```asm
; WRONG - numeric address
CALL 0F97544h
LDA XIX, 0E46312h

; CORRECT - symbolic label
CALL FDC_DRIVE_DETECT
LDA XIX, FONT_METRICS_TABLE
```

**Meaningful names are STRONGLY preferred:**
- Use descriptive names: `FDC_SEND_COMMAND`, `LED_CONTROL_DISPATCH`, `MIDI_EVENT_HANDLER`
- `LABEL_XXXXXX` style names are a **last resort** for completely unknown code/data
- When you discover what a `LABEL_*` does, rename it immediately

**Naming conventions:**
- Routines: VerbNoun (`SendCommand`, `InitHardware`)
- Data tables: NOUN_TABLE (`FONT_METRICS_TABLE`)
- Constants: NOUN (`SYSTEM_TIMESTAMP`)
- Flags: NOUN_FLAG (`PAYLOAD_LOADED_FLAG`)

### Binary Include Splitting

**When code references an address inside a binary include (not the first address), the binary must be split.**

This ensures cross-references are symbolic and binary files become smaller for analysis.

**Example:** If `data.bin` covers 0xE02510-0xE06BAF and code references 0xE04000:
1. Split the binary at 0xE04000
2. Replace one `binclude` with two, each with a proper label
3. Remove old binary, add new binaries to git
4. Verify build still produces identical ROM

### Disassembly Quality

- **Prefer disassembled code over raw bytes** - Raw `db` sequences are last resort
- **Never sacrifice readability** for byte-matching
- **Document everything** - Comments, labels, and clear structure

See `CLAUDE.md` in the repository for complete policy details.

## Getting Started

1. Clone the [ROM disassembly repo](https://github.com/ArqueologiaDigital/kn5000-roms-disasm)
2. Read the `CLAUDE.md` for build instructions and **contribution policies**
3. Check the [Open Questions]({{ site.baseurl }}/questions/) for areas needing investigation
4. Read the [Roadmap]({{ site.baseurl }}/roadmap/) for what the project is trying to reach and in what order
5. Join the [discussion forum](https://forum.fiozera.com.br/t/technics-kn5000-homebrew-development/321)

## Long-Term Goals

### Higher-Level Compiler

A **custom LLVM backend for TLCS-900** is already operational and used as the authoritative build system for all ROM reconstruction. It supports C compilation targeting the TMP94C241F, and has been used to build the Minesweeper homebrew game.

**Remaining compiler work:**
- Optimization passes for code density
- Standard library support for homebrew development
- Niche encoding variants (compact zero-load, dec/inc xsp) for 100% assembler coverage

## Skills We Need

- **Assembly programming** (TLCS-900 or similar)
- **Reverse engineering** experience
- **MAME/emulator development**
- **Hardware hacking** (ROM dumping, logic analysis)
- **C++ programming** (for MAME HLE devices)
- **Technical writing** (documentation)
- **Compiler development** (LLVM, GCC) - for long-term goals

## Contact

Reach out to Felipe Sanches to coordinate contributions.
