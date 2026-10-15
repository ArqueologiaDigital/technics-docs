---
layout: page
title: Shared Codebase Map
permalink: /technics-shared-codebase/
---

# Shared Codebase Map (KN5000 ↔ KN7000 ↔ WSA1)

Many Technics keyboards appear to have had their firmware developed by reusing a
common source codebase. This page maps **where the KN5000 and KN7000 firmwares
match** — which is valuable precisely because the two machines use **different
CPU architectures**, so any similarity must originate above the machine-code
level, in shared *source*.

> **The key constraint:** the [KN5000]({{ site.baseurl }}/cpu-subsystem/) runs a Toshiba
> **TLCS-900/H2**; the [KN7000]({{ site.baseurl }}/kn7000/) runs a Panasonic **MN10300/AM33**.
> Compiled machine code therefore **cannot** be shared. Everything that *does*
> match — identifier names, resource tables, message text, numeric constants —
> is evidence of a shared source tree that was **recompiled** for each target.

> **★ And there is now a control for that constraint.** The 1995
> [SX-WSA1 / SX-WSA1R]({{ site.baseurl }}/wsa1/) — a synthesizer, not an arranger —
> runs the **same CPU family as the KN5000**, and there the reuse shows up as
> **literal machine code: 32,795 shared bytes against a measured null of zero**.
> Same house style, one product line earlier, at the one layer the KN5000↔KN7000
> pair could not use. See
> [The WSA1 case](#the-wsa1-case-when-the-cpus-match-the-machine-code-is-shared-too).

## Verdict

The evidence establishes, at high confidence, that the KN5000 and KN7000
firmwares are **two re-targets of one shared application source tree**. The
application layer — an object-oriented UI framework, its localization tables, and
its resource/audio/menu data — was **ported and evolved onto a new CPU and OS**,
while the platform layer (CPU port, RTOS, compression, image pipeline) was
rewritten.

Every match below was located at exact byte offsets in **both** program ROMs
(`kn5000_v10_program.rom` and `kn7000_program.rom`) or table ROMs, and the
headline claims were independently re-verified.

## The smoking gun: a shared misspelling

The single most conclusive proof is an **idiosyncratic spelling error carried
verbatim into both firmwares**: "Comporser" (for "Composer").

| | KN5000 | KN7000 |
|--|--------|--------|
| `ComporserNameBoxProc` | `0x20406` | `0x23D782` |
| `MT_GetComporserName` | `0x20E94` | `0x23D65C` |

A typo cannot arise by coincidence or by convergent naming across two independent
teams targeting two different CPUs. It can only be **inherited from a common
source tree**. (Confirmed present in both program ROMs by direct search.)

## What cannot be shared: machine code

| | KN5000 | KN7000 |
|--|--------|--------|
| Main CPU | Toshiba TLCS-900/H2 (TMP94C241F) | Panasonic MN10300/AM33 |
| Program flash mapping | CPU `0xE00000` | CPU `0x48400000` |
| Instruction encoding | TLCS-900 | MN10300 (byte-aligned CISC) |
| RTOS | custom | named `MILK MN10300 Ver1.0R1` |

Because the instruction sets differ, no byte-run of executable code is common to
the two images. Every match below is therefore source-level reuse, made visible
only because the compiler embeds these strings/tables verbatim regardless of
target CPU.

## The WSA1 case: when the CPUs match, the machine code IS shared too

The section above is an argument from a *constraint* — the KN5000 and the KN7000
cannot share object code, so whatever they do share must live above it. That
constraint is real, but on its own it leaves one thing untested: **is Technics
reuse actually a source-level habit, or is it only ever the assets a compiler
happens to embed?**

The **[Technics SX-WSA1 / SX-WSA1R]({{ site.baseurl }}/wsa1/)** (1995) answers
that, because it is the case where the constraint is lifted. It is not an
arranger at all — it is an "acoustic modelling" synthesizer, keyboard and rack —
and it is built around **two Toshiba TMP95C061 processors, TLCS-900/H**. The
KN5000's sub-CPU is a **TMP94C241, TLCS-900/H2**: same instruction encoding, and
the same LLVM `tlcs900_backend` assembles both disassembly trees. So here there
is **no CPU boundary to stop machine code crossing** — and it crosses.

### 32,795 bytes of literal shared object code, against a null of zero

`kn5000_shared_runs.py` in the WSA1 disassembly tree finds every maximal run of
≥ 16 bytes shared between the four WSA1 images and the KN5000 sub-CPU payload,
and grades each one:

| | |
|--|--:|
| kept (survived the entropy guard) | **32,795 B** |
| rejected as low-entropy fill | 291,802 B |
| **shuffle null** — same byte histogram, sequence destroyed | **0 B** |
| signal-to-null ratio | **32,795×** |
| of the kept mass, held in the WSA1's **prom_c** | **28,916 B** |

*(Figures re-run 2026-08-26.)*

**The entropy guard is the result, not a detail.** Without it the "shared" mass
is nine parts erase-fill and padding: runs are rejected when fewer than 12
distinct byte values appear, when the modal byte is over 60 % of the run, or when
the run is a repeating period of ≤ 4 bytes — and the rejected set is printed
rather than silently dropped, because *"the kinship is entirely in padding"* is
an outcome that script exists to be able to report. The second guard is the
**shuffle null**, which preserves the byte histogram and destroys sequence: any
run length reachable by chance at this histogram would score there. Nothing does.

That **28,916 of the 32,795 bytes sit in prom_c** — the image belonging to the
WSA1's *second* processor — is the structural finding. The KN5000's sub-CPU is
*its* tone-generator controller, so **the WSA1's CPU 2 and the KN5000's sub-CPU
are the same design**, and the data format follows the controller: the WSA1's
tone database shares the KN5000's **81-byte per-element voice-parameter block**,
63 of 81 columns agreeing on their modal byte against byte-shift nulls of 18–29
and rotation nulls of 19–28.

⚠ **Two different numbers exist for this and must not be conflated.** An earlier,
separate script (`technics_roms/tools/wsa1_kinship.py`) reports **31,046 B in 588
runs**, with its own null of 0 B against an unrelated Technics ROM. Different
script, different corpus, no entropy guard. Pick one and name its script; do not
average them.

### The panel driver is shared, and it is a bijection

A second, independent measurement makes the same point at routine granularity.
Both machines carry a **Mitsubishi M37471M2196S** panel microcontroller. Take the
3,150 bytes of the WSA1's serial-channel-1 module and the whole 2 MiB KN5000 v10
main program ROM, and list every common substring of ≥ 16 bytes: there are
**eight, 154 bytes in all, and all eight land inside the KN5000's control-panel
driver** — a 3,535-byte window, **0.169 %** of that ROM.

**The null is what makes it a result.** The same scan over the *whole* 512 KiB of
the WSA1's prom_b gives **4,399 runs / 126,327 bytes**, and **exactly eight** of
them land in the panel driver: the same eight. **A bijection, not a cluster.**
⚠ (The count 8 is window-sensitive — a ninth run begins at the module's last byte
and ends at the panel driver's first.)
The two packet dispatchers are literally *the same instruction with a different
table pointer* — ten bytes, of which three differ — and even the delay constants
match (`SC1_WaitTicks2/6/51` against `DELAY_{2,6,51}_TICKS`).

⚠ **The counter-example that keeps this honest.**
In the same pair of machines, `DSP_WriteChannelRegs_Inner` is **80 of 81 bytes
identical** to the KN5000's — and the one differing byte is the **peripheral
base**. *Always diff the bytes before reusing a name.* Byte identity establishes
that the code is the same; it does not establish that the surrounding machine is.

### Three parts of silicon, not just code

The sharing is not only in the firmware. Three custom parts on the 1995
synthesizer carry **the same part numbers already reverse-engineered for the
KN5000**:

| part           | WSA1                          | KN5000 counterpart                       | certainty                           |
|----------------|-------------------------------|------------------------------------------|-------------------------------------|
| panel MCU      | Mitsubishi M37471M2196S       | the same part                            | solid                               |
| effects DSP    | NEC uPD6383GF-3BA (×3)        | [IC311]({{ site.baseurl }}/effects-dsp/) | solid                               |
| tone generator | Matsushita TC183C230002 (IC4) | IC303                                    | solid (schematic sheet II-13/II-14) |

The parts-list OCR printed the tone generator both as `TC183C230002` and as
`TC1830230002`, but schematic sheet II-13/II-14 prints the label directly under the
IC4 designator and settles it as `TC183C230002`. It is the most consequential of
the three, because it means an acoustic-modelling synth still carries the KN5000's
PCM tone generator.

### ★ And the framework is *absent* — which is the point

> **Provenance, because this section rests on ROM bytes.** The SX-WSA1 images are
> **not dumps this project made**. They are a publicly redistributed set, and the
> claim that they came out of a rack is the uploader's testimony. The byte
> measurements below are reproducible against those images; what is second-hand is
> where the images came from, not the arithmetic. See
> [the WSA1 overview]({{ site.baseurl }}/wsa1/) for the full provenance note.

The WSA1 does **not** run the MILK toolkit. Zero `MT_` or `*Proc` hits
across its full 2 MB, against working positive controls on the machines that do
have it. So the WSA1 **predates the KN line's application framework**: what it
shares is **silicon, kernel and assets**, not the UI framework this page
otherwise tracks.

That absence is exactly what turns a suggestive result into a shape. Read the two
findings together:

| | KN5000 ↔ KN7000 | KN5000 ↔ WSA1 |
|---|---|---|
| CPUs | **differ** (TLCS-900 vs MN10300) | **match** (both TLCS-900) |
| machine code shared | **none possible** | **32,795 B, null 0 B** |
| kernel / RTOS | rewritten | **one kernel, four processors, two products** — see below |
| MILK UI framework | **shared, and the evidence for this page's thesis** | **absent — it had not been written yet** |
| assets | tone-name tables byte-identical incl. padding | the **81-byte voice-parameter block** shared with prom_d |

### ★★ One kernel, four processors, two products

The kernel result is the strongest cross-machine finding in these trees, and it is
stronger than "the same RTOS":

* **The WSA1R's two TMP95C061s build their kernel from ONE SOURCE FILE.**
  `wsa1/kernel/kernel.s` assembles twice — into 2,180 bytes of `prom_a` and 2,180
  bytes of `prom_c`, both byte-identical to the EPROMs. Of 941 instruction slots,
  81 carry a per-CPU value, and those 81 sites are **21 constants**: RAM
  addresses, array sizes and ROM pointers. The two processors run the same kernel
  over different RAM maps with different task, semaphore and queue counts.
* **The same kernel is in both of the KN5000's processors**, in the sub-CPU
  payload and — as a separate build, not a copy — in the main program ROM
  (`wsa1/notes/kernel_structural_match.py`).
* ⚠ **Byte identity cannot answer this question.** A byte search finds zero kernel
  routines in any of the 41 KN5000 images, because two processors in the *same*
  product from the *same* build already differ in 81 of 941 slots. The match is
  structural, over decoded token sequences, and it is graded against a **foil** —
  non-kernel WSA1R routines of the same lengths, run through the identical
  search. Kernel routines score 0.742–1.000 (median 0.909, 20 of 20 above 0.70);
  the 26 foils top out at 0.333, none above 0.70. No overlap, and a gap of 0.41.

The adaptation shows in one detail worth keeping: the WSA1 holds the
interrupt-nesting depth in control register `0x3C` and **reads it back**, while the
KN5000 keeps it in a RAM word and only *mirrors* it into cr `0x7C`. Same RTOS,
two family members, two ways of using the hardware the part provides.

And the asset lineage reaches across all three machines at once:
`technics_roms/tools/wsa1_kinship.py` finds **195 of the WSA1's 252 16-character
tone-name fields (77.4 %) occurring verbatim in the KN7000's table ROM** — a 1995
synthesizer and a 2002 arranger, seven years and a CPU architecture apart.

The reuse was never a *framework* phenomenon. **It was a house style that
operated at every layer the target allowed**: object code where the instruction
set permitted it, silicon where the part was still current, and — once the CPU
changed and object code stopped travelling — the source tree, the resource
tables and the framework that this page documents. The KN5000 sits in the middle
of that story rather than at its start: it shares a kernel and a panel driver
with the earlier WSA1 generation, and hands a UI framework forward to the KN7000
generation.

Full detail is on the [SX-WSA1 pages]({{ site.baseurl }}/wsa1/), and the
measurements are re-runnable from the scripts named above; see
[SX-WSA1 Disassembly]({{ site.baseurl }}/wsa1-disassembly/#-shared-code-with-the-kn5000--measured-with-a-null).

## What is shared: the MILK UI toolkit

Both ROMs embed the runtime symbol tables of the **same object-oriented,
event-dispatch UI framework** — the "MILK Toolkit" (`MT_` API), named by the
KN7000 kernel banner. These are consumed by the framework's own
class-introspection / RTTI at runtime, so the compiler stores them as literal
strings.

| Framework element | KN5000 | KN7000 | Overlap |
|-------------------|--------|--------|---------|
| `*Proc` class/widget handler names (`ViewableProc`, `InheritedProc`, `DefaultClassProc`, `ObjectProc`, `WindowProc`, `Vw*`/`Ac*`/`Ps*`/`Iv*` taxonomy) | 348 unique, table at `0xB1040`–`0xB15FF` | 537 unique, table at `0x1B3B40`+ | **187 exact-identical** names; same class hierarchy `DefaultClassProc→ClassProc→ObjectProc→ViewableProc` |
| `MT_*` toolkit API (`MT_GetLanguagePtr`, `MT_GetProcedure`, `MT_FLASHWRITE`, `MT_SleepApTask`, `MT_WakeUpApTask`, `MT_IWillWakeUp`, `MT_VST_PST_OK`) | 450 unique | 427 unique | **216 exact-identical**, including highly idiosyncratic names and the cooperative-task API |
| Framework core (`RegisterObjectTable`, `InitializeObjectTable`, `DispatchEvent`, `SendEvent`, `RegisterTitle`, `GetTitleNow`, `CheckViewObject`) | `0xB153E`–`0xB15B4` | `0x1B3B65`–`0x1B406A` | identical names, same contiguous symbol table |
| RTTI / resolution API (`MT_GetProcedure`, `MT_GetModeProc`, `MT_GetTitleProc`, `MT_AreYouClassProc`) | present | `0x1B2A4E`–`0x1B3058` | identical |
| `TT_*` title-tag vocabulary (`TT_SEMENU`, `TT_SEEASY`, `TT_SEDIGEFF`; SE/DK/CM families) | 211 tags (`TT_`) at `0xD588`+ | 375 tags (`_TT_`) at `0x1AEF61`+ | **141 identical** bodies (KN7000 adds a `_` prefix) |
| Symbol-table storage format | NUL-terminated + `0xFF` even-alignment pad (`ALIGNED_STRING`) | same contiguous NUL-terminated table | shared data-format design |
| Developer/system objects | `Panel Simulator for HK`, `PanelSimulator`, `ClipBoard` | `Panel Simulator 2.1` / `for IK`, `ClipBoard`, `DefaultWindow` | same tool, matured (`2.1`) |

The `Panel Simulator for <model-code>` template (HK on the KN5000; the KN7000 still
says `for IK`, the KN6000's project code, because its source tree was forked from the
KN6000's, see the [Roadmap]({{ site.baseurl }}/roadmap/)) and the whole class-introspection table survive the CPU change intact —
the shared code is the entire event-dispatch + object-registration core, not just
leaf widgets.

### Framework internals: the dispatch & object model

Decoding the KN7000 tables reveals *how* this shared toolkit works internally —
mechanism that transfers to the KN5000 too:

* **A unified 32-bit message-id space, partitioned by category** (the high 16
  bits). The same encoding recurs everywhere: `0x0002_xxxx` toolkit opcodes,
  `0x0004_xxxx` / `0x0008_xxxx` `MT_` method selectors, `0x0005_xxxx` UI events,
  `0x0006_xxxx` system/task messages. `SleepMainTask`, for instance, sends
  opcode `0x00020009` with message id `0x0006009D`.
* **The `MT_` dispatch table** (KN7000 name array at `0x326CE4`, 241 entries) is
  *heterogeneous*: each method resolves to **either** a direct code pointer
  (≈29, e.g. `MT_GetProcedure` itself), a **selector** id (`0x0004_xxxx`, routed
  through the kernel), or a pointer into the **class-descriptor region** — i.e.
  the toolkit mixes direct calls, late-bound message dispatch and RTTI in one
  table.
* **An object property/class metadata region** (KN7000 ≈`0x1B1000`+): class
  descriptors delimited by `0xFFFFFF00`, carrying property lists whose names
  (`parent`, `top`, `super`, `fontcolor`, `pagemax`, `editsw`, …) are what the
  `MT_GetPropName`/`MT_GetPropData`/`MT_GetClass`/`MT_GetParentClass` RTTI reads.
* **A named-constant table** for the property values — recovered by
  `kn7000_disassembly/tools/gen_constants.py`: `VF_*` view flags, `CL_*` palette
  colours, `BD_*` border styles, and part/track/step enums. These cross-check the
  rest of the reverse engineering exactly — `VF_Invisible=1`, `VF_Change=4`,
  `VF_Const=8` are precisely the object flag bits the KN7000's `SetVisible` /
  `SetChange` / `SetConst` test with `btst`, and `CL_Transparent=0xF7` names the
  transparent palette index used by both machines' sprite blitters.

## What is shared: localization & resource tables

| Element | KN5000 | KN7000 |
|---------|--------|--------|
| Multi-language dialog blocks (`ATTENTION!` / `ACHTUNG !` / `Perhatian !`; `Sind Sie sicher ?`; Indonesian `Apakah yakin akan dihapus ?`) in identical EN/DE/FR/ES/Indonesian order | `0x1E4D0`+ (repeats `0x25884`, `0x3382C`, …) | `0x2276B8`+ (repeats `0x261E6C`, `0x2AE468`) |
| Vendor-custom 8-bit codepage — `¿Está seguro?` = bytes `BF 45 73 74 E1 …` (¿=`0xBF`, á=`0xE1`, û=`0xFB`), **not** Latin-1 | `0x1E55E` | `0x227BFF` (byte-for-byte identical) |
| Private engineering test-menu selector (~90 bytes: `\|-\|SAVE REMINDER\|'COMPLETED' MESSAGE\|ARE YOU SURE?\|…\|EASY SETTING`) | `0xD4D5A` | `0x20E735` (byte-identical) |
| User prompt `Please Insert the Style Convert Disk!` | `0x1EE44` | `0x207124` |

A non-user-facing engineering test-menu string present verbatim in both is a
direct fingerprint of a shared source/asset tree; the identical vendor codepage
implies shared font and string tooling.

## What is shared: audio & menu data tables

| Element | KN5000 (table ROM) | KN7000 (table ROM) |
|---------|--------------------|--------------------|
| Tone-name inventory in 16/17-char centered fields (`SymphonicStrings `, `Concert Strings  `, `CupMuteTrombone  `, ` Bottle Marimba `, ` Country Fiddle  `) — byte-identical incl. padding | `SymphonicStrings` @ `0x36DD6` | @ `0xA2266` |
| Easy-Setting / Music-Stylist genre menu (`     8 Beat     `, `16 Beat`, `Dance Pop`, `Jazz Fusion`, …) — 10 labels, identical centered padding | `0x1DEFC` (prog) | `0x1CCF2C` (prog); only traversal order differs |

## Evolved, but recognizably the same lineage

Some elements were carried forward with modifications — the signature of a shared
codebase that kept developing:

- **Version screen**: both share the `SOFT VERSION` caption and the internal
  `MPVersion` symbol; the KN7000 added `RHYTHM`/`PICTURE` rows and dropped the
  MAIN/SUB split (reflecting its single-CPU design).
- **`<model> SOUND RAM` convention**: the KN7000 extends it to a predecessor list
  at `0x1B8517` — `KN6000 / KN5000 / KN3000 / KN2000 / KN1600 SOUND RAM` — i.e. it
  explicitly reaches back to import the **KN5000's own** sound-RAM data format.
- **Sound-group / style categories**: `DIGITAL DRAWBAR`, `DRUM KITS`,
  `JAZZ COMBO`, `MARCH & WALTZ`, `COUNTRY`, `CUSTOM` carry over exactly; others
  are reorganized or spelled out (`ACCORDION REG.` → `ACCORDION REGISTER`).

## The divergence boundary (what was rewritten)

Shared reuse stops cleanly at the application layer:

| Layer | KN5000 | KN7000 |
|-------|--------|--------|
| RTOS/kernel | no banner — but **not bespoke**: it is the same TLCS-900 kernel the SX-WSA1R's two processors run, present in both KN5000 CPUs ([above](#-one-kernel-four-processors-two-products)) | `MILK MN10300 Ver1.0R1` @ `0x3B8AAC` |
| Compression | [LZSS]({{ site.baseurl }}/lzss-compression/) | LZSS **and** zlib/deflate 1.0.4 @ `0x3B8604` |
| Photo/demo images | headerless 8bpp bitmaps | *adds* JPEG (Adobe Photoshop) + Windows BMP |
| Tone-init helper | `SwbtWr` @ `0x1F410` | absent (sound-init layer reworked) |
| Version widgets | — | KN7000-only `AcProgVerBoxProc`, `IvMpVerWinProc`, `DefaultWindow` (same naming grammar) |

The KN7000-only additions follow the **same framework naming grammar**
(`Ac*BoxProc`, `Iv*WinProc`), exactly what you expect from new features authored
downstream in a shared codebase.

Note that the image *divergence* is only partial: the KN7000 **adds** JPEG for
photos and demo art but still stores its **UI icons as headerless
palette-indexed bitmaps reached through a `{width, height, pointer}` descriptor
hierarchy — the same design as the KN5000** (293 such bitmaps, including a 240
sprite icon set; see the [KN7000 image gallery]({{ site.baseurl }}/kn7000-image-gallery/#raw-ui-bitmaps-table-rom)).
So even the graphics pipeline is shared at the UI layer; only the photo/demo
asset format was modernised.

## The update-disc container is shared too

Independently of the firmware, the update subsystem is the same across models —
same `.SLD` container, same 24-bit big-endian size field, same 4 KB
[LZSS]({{ site.baseurl }}/lzss-compression/), same `.INF` checksum sidecar — only the magic string
differs (`SLIDE4K` → `JKPRG4K`/`JKTB14K`/`JKTB24K`). See
[KN7000 System Update Discs]({{ site.baseurl }}/kn7000-system-update-discs/) and the KN5000's
[System Update Discs]({{ site.baseurl }}/system-update-discs/).

## Why this matters

Mapping the shared portions lets discoveries transfer between models: a data
format decoded on the well-documented KN5000 gives a decoding head-start on the
KN7000, and the shared `MT_`/`*Proc` symbol tables let KN5000 symbol knowledge
seed the KN7000 disassembly directly. Across the whole Technics keyboard line,
this reuse map is a route to understanding the family as a **single evolving
system** rather than a set of unrelated instruments.

The WSA1 extends that route **backwards in time, and past the keyboard line
altogether**: it is not an arranger, and it still shares a kernel, a panel driver
and a voice-parameter format with the KN5000. Anything decoded on the KN5000's
sub-CPU is a head start on the WSA1's CPU 2, and — because the WSA1 names real
effects that the KN5000 ships as
[programs byte-identical to NO OPERATION]({{ site.baseurl }}/dsp-effect-data-zone/)
on the very same uPD6383GF DSP — the traffic may yet run the other way as well.
The shared instruction set is now demonstrated (kn5000-roms-disasm `d28b3bf8e`,
2026-09-06): the WSA1R's `prom_c` program words use the KN5000's container and
field layout and decode under its uPD6383 model at 34.48 %, against 38.53 % on the
KN5000 and nulls of 0.03–0.40 %. ⚠ Whether the WSA1's programs for the named
effects would be *usable* on the KN5000 is still **not demonstrated**.

## Method note

Matches were found by intersecting whole-token string inventories of the two
program ROMs and comparing the table ROMs field-by-field, then verifying exact
byte offsets on both sides. Counts (e.g. "187 identical `*Proc` names") are
whole-string set intersections; "byte-identical" means an exact byte-run match
including padding. The comparison covered UI-framework symbols, container/file
formats, localized string tables, and numeric/audio data tables.
