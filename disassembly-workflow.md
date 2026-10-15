---
layout: page
title: Disassembly Workflow
permalink: /disassembly-workflow/
---

# Disassembly Workflow

Conversion work on the disassembly is organised in **waves**: a batch of independent
packages, worked by read-only agents in parallel, integrated serially by a single writer,
each package gated on the ROMs still rebuilding byte-identically. This page describes that
process and the traps that make a green gate untrustworthy if you take a shortcut.

## The invariant

> ```
> make gate            # the nine KN5000 images
> make gate-all        # all thirteen: 9 KN5000 + 4 SX-WSA1R
> ```
> **Byte-identical, or the package does not land.**

`make gate` depends on `all`, so it rebuilds before it compares; it runs
`scripts/analysis/assert_images_assemble.py` (every root source must assemble, asked of the
assembler directly) and then `scripts/analysis/assert_byte_identical.py`, which **compares
bytes and exits non-zero on any difference**. Everything else in the workflow exists to
protect that one line. A package that cannot demonstrate it is reverted, and the reason is
recorded rather than argued away.

### ⚠ Never gate on a percentage

`scripts/build/compare_roms.py` prints `Similarity: 100.00%`, rounded to two decimals. In a
2,097,152-byte ROM that rounding covers **up to 104 differing bytes**. It does append
`(N incorrect bytes)`, but a check written as `grep -c "Similarity: 100.00%"` matches the
failing line too, because it is a prefix. That is why the gate is a byte comparison with an
exit status and not a printed figure — the reasoning is written into
`assert_byte_identical.py`'s own docstring, and both shortcuts (a percentage, and
`--no-build` on a tree that was not just built) have cost this project real retractions.

### The ASL mirror is a second, separate build

The sources are maintained twice: the primary LLVM build and an archived ASL mirror. Three
facts about that combine into a trap:

- `make all` builds only the primary LLVM targets — the rule is literally `all: llvm-all`.
  It never invokes `asl-all`.
- `make clean-all` is `clean` + `clean-asl`, and `clean-asl` deletes the six
  `rebuilt_ROMs/*.rebuilt.rom` files the ASL mirror build produces.
- `compare_roms.py` **skips a section whose built file is missing**, silently: each of its
  fifteen table entries is guarded by `if not os.path.exists(...): continue`. There is no
  warning, and the exit status does not change.

So `make clean-all && make all && python3 scripts/build/compare_roms.py` prints **nine**
sections instead of fifteen, every one reading `100.00%`, having assembled nothing of the
mirror at all.

> **Count the sections, not the percentages.** Fifteen is the number: nine from the primary
> LLVM build, six from the ASL mirror. A run that prints nine has tested nothing about the
> mirror, however green it looks.

Until 2026-09-01 the LLVM incremental build was not sound either: most object files listed
only the top-level `.s` of their ROM as a prerequisite, so an edit to an `.include`d file
rebuilt nothing, and four of eight KN5000 images had in fact stopped assembling while the
gate said PASS. `179709ea5` fixed both. Every LLVM object now depends on every `.s` of its
tree (`V10_SRC = $(wildcard v10/maincpu/*.s v10/maincpu/*/*.s v10/maincpu/*/*/*.s)` and its
siblings), and `make gate` runs `scripts/analysis/assert_images_assemble.py`, which asks the
assembler directly from each root source, before the byte comparison. The ASL mirror's rules
still name only each image's top-level `.asm`, so after editing a mirror file rebuild it from
clean (`make clean-asl asl-all`) — and then count fifteen sections in the report, because
`clean-all` followed by `make all` alone leaves the six mirror sections out.

## Step 0: audit before touching anything

The waves were scoped by a prior audit rather than by intuition about what looked
interesting. Ten agents — seven scanners and three adversarial verifiers — walked every
`.incbin`/`binclude` directive and every compressed region in the repository.

| Quantity | Result |
|----------|--------|
| Directives inventoried | 598 |
| Honest build products (compiled from C/asm, or generated from documented data) | 505 |
| Findings recorded | 55 |
| Adversarial verdicts | 24 (14 CONFIRMED, 10 REFUTED) |

The output was a machine-readable `findings.json` plus a plan that ordered the remaining
work into waves. Crucially, the audit distinguished *build products* from *undocumented
binaries in disguise* — a `generated/` path is not evidence of anything if the "generator"
is a `dd` that slices the original ROM.

### The evidence standard

"This blob is code" was accepted only after an adversarial pass demanding all four of:

1. a clean decode at the claimed base address;
2. every branch target landing on an instruction boundary;
3. at least one call target coinciding with an independently known label; and
4. **a shifted-decode control** — the same bytes must *not* decode cleanly at base+1.

The fourth condition is the one that does the work. Plausible-looking disassembly is cheap;
disassembly that survives a deliberate attempt to produce it from the wrong offset is not.

### The adversarial pass earned its place

It corrected the scanners repeatedly rather than rubber-stamping them:

- The scan reported 23 `v7_block_*` binaries. The verifier checked all of them and found
  the generator's list contains 138 unique block entries (139 files) — a six-fold
  undercount that would have made Wave 4 unschedulable.
- Ten of the twenty-four verdicts came back **REFUTED**, most of them as *gaps*: whole
  categories the scanners had declared clean and had not actually covered (the maincpu
  inline `.byte` regions, orphaned reference slices, the v1.41 payload with no build
  coverage, binaries under `dsp/` that a "clean sweep" claim had missed).

The waves then refuted several claims the plan itself had carried forward: there is no
"exponential pitch table at 0x13318" (it is the middle of a mixer *gain* curve); a banner
claiming two 128-byte tables at 0x00FF00/0x00FF80 was retracted (those addresses are
immediate values written to a hardware address latch, not table pointers); the HD-AE5000
"graphics data" at 0x2A5D2C is two 790-entry pointer arrays and a string pool; and the
sub-CPU boot ROM's 96 KB of `0xFF` is **undumped** apart from 2 KB read blank at each end,
not erased.

## The wave shape

Each wave is one run with the same three-part structure. Five rounds were integrated on
2026-08-07 and 08-08, and the ledger records the count for each. The later 2026-09-25
semantic push and the 2026-09-25 to 10-02 toolchain wave reuse the names "Wave 2" and
"Wave 3a" for different work (see
[ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/#after-wave-2-2026-09-25)); in this
table they mean the August rounds:

| Round                      | Scope                                                                     | Landed      |
|----------------------------|---------------------------------------------------------------------------|------------:|
| Wave 0 (August 2026)       | foundations, SLIDE8K tooling, the tone database                           | 7 / 7       |
| Wave 1 (August 2026)       | bootcode disassembly, help-database round-trip, the v1.42 update image    | 6 / 7       |
| Wave 2 (August 2026)       | table-data conversion (fonts, style records, preset banks, panel memory…) | 8 / 8       |
| Wave 3a (August 2026)      | the sub-CPU DSP data zones A0 / A / B                                     | 3 / 3       |
| Waves 3b + 5 (August 2026) | HD-AE5000, sub-CPU boot data, maincpu name tables, orphan cleanup         | 9 / 10      |
| **Total**                  |                                                                           | **33 / 35** |

A sixth wave ran in between, but it was an investigation rather than a conversion: it
proved the runtime memory remap, re-read the service manual's address-decode logic, and
turned the sub-CPU payload question into a dump-provenance question. It produced findings
and documentation, not packages, so it does not appear in the count.

### 1. Parallel read-only workers

N agents draft in parallel into a scratch directory. **No worker ever touches the
repository or git.** Each receives one package — a bounded region and a deliverable — and
returns replacement `.s` text with semantic labels matching house conventions, a module
header, per-table comments, and the evidence behind every label (an xref address or an
observed behaviour).

The part that makes the whole thing work is the **mandatory self-check**: before returning,
a worker assembles its fragment standalone and byte-compares the result against the
original ROM slice, quoting the commands and their output. A fragment that does not match
returns `blocked` or `partial` *with the diff*. It never returns silently.

This pushes verification to where the knowledge is. By the time a package reaches
integration, someone has already proved it reproduces the ROM.

### 2. One integration manager — the only writer

A single agent owns the branch and applies packages **one at a time**. After each package:
the full similarity run of the time (`make clean-all && make all && make asl-all`, then
`compare_roms.py`; the byte gate `make gate-all` replaced it on 2026-09-01). On fifteen
sections at 100.00% it commits (one commit per package, succinct message,
toolchain-provenance line). On anything less it reverts — by hand, surgically, never with
`git checkout`/`reset`/`stash`, because those would take uncommitted work with them.

Serial integration is the expensive-looking part and the reason the gate held. Parallel
drafting is safe because drafts are text in a scratch directory; parallel *merging* would
make a byte mismatch impossible to attribute.

### 3. Ledger

The manager appends one row per wave to a status file: what launched, what landed, the
commit hashes, what was adapted during integration, and what was deferred. The deferred
list is not a wish list; it is the input to the next wave.

## Workers draft against a tree that is already moving

The subtlest integration hazard is not a bad package — it is a *stale* one. Workers in a
wave all read the tree as it stood when the wave launched, but the manager has been
committing their siblings' work ever since. By the time package six is applied, the file it
edits may no longer be the file it read.

Wave 3b hit this repeatedly, and the discipline that came out of it is:

- **Apply a worker's diffs, not its whole files**, whenever an earlier package in the same
  wave touched the same file. Two HD-AE5000 packages shipped complete replacement files
  that predated a landed sibling; taking them whole would have silently reverted it.
- **Expect overlap to be real work.** In Wave 2 several workers rewrote the same banner
  comments in `kn5000_table_data.s`; the manager hand-merged later hunks over earlier text
  and re-verified rather than letting the last package win.
- **Re-derive machine-generated artifacts instead of trusting the worker's copy.** One
  package's symbol-table hunk shipped uppercase-mangled names for labels that exist in
  MixedCase, and rows for C struct members that are not assembler labels at all; the
  manager rebuilt that hunk from the linked ELF.
- **Take the part of a package that is still true.** When a package's core edit had already
  landed via a sibling, only its remaining pieces — an extracted image asset, a metadata
  entry, a path bug fix, corrected comments — were applied, renamed to the labels that
  actually got committed.

None of this is visible in the final diff, which is exactly why it is worth writing down.

## What grep does not tell you

Two of the waves' larger corrections started as a search that came back empty and was
briefly believed. In this repository a negative grep result is weak evidence — and a
positive one is not much better. There are at least four independent traps.

**1. grep will not read some of the sources at all.** Six `.s` files in the v7 tree contain
raw 8-bit bytes — Latin-1 text such as `¡ATENCIÓN!` at
`v7/maincpu/ui_widgets/disk_menu_file_io_screens.s:1455`, for instance. That makes each file
invalid UTF-8, and the `grep` installed here (ugrep 7.8.4, in a UTF-8 locale) treats four of
them as binary: it prints **nothing** and exits **1**, which is indistinguishable from "no
match". Other greps differ only in the detail — GNU grep announces `Binary file … matches`
instead of listing the lines — so either way the hits vanish from a line-oriented pipeline.
The cost is not marginal: `grep -rn '\.incbin' v7/maincpu` reports 8,773 matching lines,
while `grep -ran` reports 10,057 (disassembly `3417969c0`). The 1,284 invisible lines are
all in three of those files. Pass `-a` or use a parser; with this grep, `LC_ALL=C` does not
help.

**2. The disassembler writes numbers in a different base than the datasheet.** An early
scouting pass searched for writes to the TMP94C241's memory-controller registers, found
none, and concluded the firmware never programs them. All twenty-four registers are in fact
programmed, in one block at `table_data/shared/boot_hw_init.s:85-134` — but they are emitted
as direct SFR addresses in **decimal**, so MSAR0 (`0x143`) appears as `ld (323:16), 30`.
Searching for the *name* is no better: `table_data/shared/sfr_tmp94c241.s:210` defines
`.equ MSAR0, 0x143`, so a grep for `MSAR0` in `table_data/` returns exactly one hit — the
definition — and zero writes. See [TMP94C241 Memory Controller]({{ site.baseurl }}/tmp94c241-memory-controller/)
for what those writes do.

**3. Text is not always stored as text.** The DSP effect-name and parameter-name tables were
believed to be absent from the sources because a string grep never found them. They were
there all along, as raw `uint16_t` array members inside the C-compiled
`naka_widget_descriptors.c` blob. They are now carved into named tables
(`DspParamUnit_Table`, `DspParamName_Table`, `DspEffectName_PtrTable`), identical in v7, v9
and v10.

**4. A hit is not a reference.** The reverse error is just as easy. The orphaned slices under
`original_ROMs/demo_preset_compressed_refs/` share their basenames with *live* build
products under `table_data/includes/demo_presets/`, and the build's `--reference` argument
actually names a third set of files, `original_ROMs/demo_preset_NN_compressed.original.bin`.
A bare-basename grep reports the orphans as "referenced" and is wrong about every one of
them. In the other direction, ASL is invoked as `asl -i table_data …`, so a
`binclude "includes/foo.bin"` in the mirror is a path relative to that include directory —
grepping for the repository-root path finds nothing while the file is very much in use.

The general rule: **a search proves something only when you have shown the search could
have found it.** Construct a positive control — grep for something you know is there, in the
same notation, in the same files — before believing a zero.

## Deleting things safely

Wave 5 retired 32 tracked binaries that participated in no build. Deletion is the one
irreversible operation in the workflow, so it got its own standard, and every condition was
re-verified by the manager independently of the worker:

1. The file is named by no `.s`, no `.asm`, no Makefile rule and no script — checked with
   the false-positive traps above in mind, including ASL's `-i` search paths.
2. The file is a **byte-exact slice of a ROM that remains tracked**, so no information is
   destroyed.
3. The exact `dd` that regenerates it is written down before it goes.

That last point is what makes the deletion reviewable rather than merely asserted:
`analysis/orphans-2026-08-08/README.md` lists every retired file with its size, its source
ROM, its CPU address and a one-line `dd` that reproduces it byte-for-byte from the
repository root.

The same instinct produced a permanent check for the opposite problem — bytes that are
present but unexplained. `make audit-icons-blob` accounts for all 742,024 bytes of
`icons_to_strings.bin`: none read by the LLVM build since 2026-09-02, the first 520,920
bytes (file offsets 0x0–0x7F2D7) `binclude`d by the ASL mirror, and a 221,104-byte dead
tail beyond file offset 0x7F2D8 that is a stale duplicate of the demo-preset region and is
read by nothing. A coverage tool
that can report an unexplained gap is worth more than a comment claiming there is none.

## House constraints that keep the gate honest

Some of these look like bureaucracy until you notice what each one prevents.

- **Blob files that the archived ASL build still `binclude`s stay byte-identical on disk.**
  Conversions slice with `.incbin "file", offset, length` instead of splitting a blob into
  new files. This is why the legacy ASL mirror still builds — and the mirror is six of the
  fifteen verified sections, so it is a real check, not sentiment.
- **Every commit records the exact LLVM toolchain commit** that produced the artifacts
  (`LLVM: <branch>@<hash>`), and LLVM history is immutable once it has produced verified
  ROMs. A byte-match is only meaningful if you can say which assembler produced it.
- **Symbol reference files are address-sorted, with upper-case hex addresses**, so they
  diff cleanly and external tools can bisect them.
- **Documentation commits must build.** A docs change that breaks `jekyll build` is not
  finished.
- **Nothing is pushed** during an autonomous run.

## The failure modes this shape is built against

Two are structural and cost nothing when they happen; the third is the one that matters.

- **A worker stalls and returns nothing.** Workers cannot write to the repository, so the
  cost is exactly one package's delay and the tree is untouched.
- **A run is interrupted mid-wave.** Nothing is integrated until the manager runs, so an
  interrupted wave leaves the repository exactly as it was; finished workers replay from
  cache.
- **A byte-safe change whose *comment* is a false claim.** The sub-CPU boot ROM's 98,304
  lines of `.byte 0xff` were collapsed to a single `.fill` on 2026-09-02 (`cccbe2978`), with
  no byte changing, and the directive's comment calls the region "erased flash". It is not
  erased flash. Apart from 2 KB read at each end, it is **undumped**: 14,336 of the chip's
  131,072 bytes were ever read, and only 4,352 are not `0xFF`. So the bytes pass the gate
  while the comment states something about the physical part that the dump does not
  support, and the comment needs correcting.

**The gate protects the bytes; only the reviewer protects the meaning.** Rejecting a
byte-safe change on the strength of what its comment would claim is the standard here, not
an exception to it.

## Why the byte-match holds

Three properties, in order of importance:

1. **The acceptance criterion cannot be argued with.** Byte-identical, or revert. No
   reviewer judgement is involved, so no reviewer fatigue can erode it — provided the
   command is the gate and not a percentage, which is the whole point of the traps above.
2. **Verification happens twice, in different places** — once by the worker against a ROM
   slice, once by the manager against the whole ROM set. The first catches almost
   everything; the second catches interactions between packages.
3. **Serial integration keeps attribution exact.** When something does mismatch, exactly
   one package changed, so the diff points at the cause instead of at a merge.

## The documentation half has its own gate

Byte-identity says nothing about whether a sentence on this site is true, so the
documentation refresh that followed the waves was put through its own adversarial pass.
Every writer recorded the claims it made and the evidence it cited — 292 claims — and two
independent verifier passes graded them against the repository:

| Pass | Verdicts | Confirmed | Refuted | Unverifiable |
|---|---:|---:|---:|---:|
| Addresses and structure | 24 | 12 | 12 | 0 |
| Behaviour, provenance and overclaiming | 58 | 47 | 9 | 2 |

All 82 verdicts were applied before publishing. The refutations were not cosmetic: one
boundary address had been stated four different ways across four pages, a claim about the
sub-CPU payload's location was retracted in four places, and a section headed "RESOLVED"
was downgraded to "under investigation".

One process lesson came out of it. Both passes carried all ~292 claims into a single large
structured return at the end of a long run; one took two attempts to deliver, and a
completed result was briefly mistaken for a stall. Verification work should be split so each
agent returns a small result — the same reasoning that makes the workers' per-package
self-check reliable.

## Remaining work

The conversion is not finished, and **what is left is not one kind of thing**. Three kinds
of debt exist and they are counted by different instruments — quoting one as the total is
the mistake this tree has shipped twice:

* **verbatim** — bytes entering the build through an `.incbin` of a blob with no generating
  source. Counted by `scripts/analysis/kn5000_source_coverage.py`.
* **code-as-`.byte`** — real instructions spelled as data directives. Invisible to the
  column above, counted by per-image census tools.
* **data-as-code** — data disassembled into plausible instruction mnemonics. Invisible to
  *both*, and invisible to the byte gate as well, because re-assembling a wrong
  interpretation reproduces the same bytes. It needs a per-image detector and a null.

The largest concentration of the first two is the **v7 maincpu tree**, whose
`includes/romslices/` holds live-referenced ROM transplants — `.bin` slices reproduced by no
source at all, itemised by `scripts/analysis/v7_no_source_bytes.py`. v9 and v10 are at zero
verbatim debt.

Per-image figures move within hours while lanes convert; take them from a live run of the
coverage script, and take the debt taxonomy and the per-image detectors from
`notes/DEBT-INVENTORY-2026-09-02.md` in the disassembly repo. Current status per ROM is
summarised on the [ROM Reconstruction]({{ site.baseurl }}/rom-reconstruction/) page.
