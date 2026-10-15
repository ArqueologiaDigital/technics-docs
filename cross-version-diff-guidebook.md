---
layout: page
title: "Cross-Version Diff Guidebook"
permalink: /cross-version-diff-guidebook/
---

# Cross-Version Source Diff Guidebook

Best practices for producing the cleanest possible source-level diffs between KN5000 firmware versions. Derived from the v9-to-v10 diff minimization journey (5,388 lines reduced to 44 on 2026-03-25: `diffs/v9_vs_v10_maincpu.diff` in the disassembly repository, `46f2e935b`) and applied to all version pairs.

## Principles

### 1. The diff should tell the engineering story

A good cross-version diff shows ONLY what the firmware engineers actually changed. Every diff line should answer "what did Matsushita change and why?" If a diff line exists because of how WE chose to represent the data rather than because of a genuine firmware difference, it's noise.

### 2. Symbolic references absorb address shifts

When code grows or shrinks between versions, every absolute address after the change point shifts. If the source uses symbolic label references (`.long FunctionName` instead of `.long 0x00ef1234`), the linker resolves per-version and the diff shows nothing. **Every pointer that CAN be symbolic MUST be symbolic.**

### 3. Identical source for identical behavior

If two versions execute the same code or contain the same data structure (just at different addresses), the source text should be IDENTICAL. The versions should share the same `.s` files wherever the functionality is unchanged, with version differences isolated to the minimum number of files.

### 4. Data blobs are a last resort

Replacing source-level representations (`.byte`, `.long`, `.ascii`, instructions) with opaque `.incbin` binary blobs defeats the purpose of disassembly. A blob hides the structure and makes the diff useless. Binary blobs are acceptable ONLY when:
- The data has no known structure (raw bitmap pixels, opaque firmware tables)
- The data is genuinely different between versions AND the structure is unknown
- Temporarily, as a stepping stone toward full source representation

### 5. Code must never be a blob

Executable code must ALWAYS be disassembled instructions, never `.incbin` of raw bytes. If code shifted between versions, the correct fix is symbolic references (labels, `.set`, `.equ`), not binary blobs. The entire point of the disassembly project is to have readable source.

## Rules

### Rule 1: Use symbolic `.long` for ALL pointer tables

**Bad (version-specific, creates diff noise):**
```asm
.long 0x00ef1234    ; hardcoded address
```

**Good (version-independent, linker resolves):**
```asm
.long FunctionName  ; symbolic, same in all versions
```

If the pointer target doesn't have a label, ADD one. Every function, data table, and entry point should have a meaningful label.

### Rule 2: Use symbolic `call`/`jp`/`calr`/`jrl` for ALL branches

Never leave numeric displacements in branch instructions when the target has a label.

**Bad:** `calr 64899`
**Good:** `calr HdaeRom_DataDispatch_Block`

### Rule 3: Use `addr24` with labels, not `_addr24_*` constants

The `addr24` macro uses `.reloc R_TLCS900_24` to emit linker-resolved 24-bit addresses. Use it directly with labels.

**Bad:** `.set _addr24_Free, 0xff0af2` then `addr24 _addr24_Free`
**Good:** `addr24 Free`

(Since 2026-10-02 the KN5000 trees have no `addr24` uses left: those sites were re-framed as instructions whose operands are labels, and a far pointer pushed as two words is spelled `Label@hi16` / `Label@lo16`.)

### Rule 4: Parenthesized direct addressing for consistency

All direct-address operands use parenthesized syntax with an explicit address width: `ld a, (SomeLabel:24)`. This is enforced by the LLVM `directaddr` operand class and ensures formatting consistency across versions.

### Rule 5: Use `.set FW_VERSION_BYTE` for version-specific constants

Version-specific scalar values should be defined as named constants in one place, not scattered as magic numbers.

### Rule 6: Shared source files must be IDENTICAL

Any `.s` file that appears in multiple version trees must be byte-identical across versions. If a file differs, either:
- The difference is genuine (document it)
- Or the representation should be unified (fix it)

Files like `positional_labels.s`, `macros.s`, `sfr_tmp94c241.s` MUST be identical.

### Rule 7: Data tables with embedded pointers need `.long label` not `.byte` raw bytes

When a data table contains 32-bit pointer fields mixed with non-pointer data, the pointer fields should be `.long SymbolName` and the non-pointer fields should be `.byte`. Never encode a pointer as raw `.byte 0xNN, 0xNN, 0xNN, 0xNN`.

### Rule 8: No `.incbin` for data that has known structure

If the binary data is a table of pointers, a struct with named fields, or a dispatch table, it should be expressed as source-level directives (`.long`, `.byte`, `.ascii`), not `.incbin` of an extracted blob.

### Rule 9: Minimize the number of version-specific files

Most `.s` files should be SHARED (identical) across versions. Version differences should be concentrated in:
- The entry point file (`kn5000_vN_program.s`)
- A small number of data files with genuine content differences
- `.set`/`.equ` constants for version-specific scalar values

### Rule 10: Never use code blobs between versions

If code shifted by N bytes, the correct representation is:
- Same `.include` structure in both versions
- Symbolic labels that the linker resolves per-version
- Different `.fill` padding to absorb size differences

NOT: `.incbin "v7_postshift_blob.bin"` replacing 43 `.include` directives.

## Scoring a Cross-Version Diff

| Criterion | Score | Description |
|-----------|-------|-------------|
| No binary blobs for code | 0-10 | All code is disassembled instructions? |
| No binary blobs for structured data | 0-10 | All data tables use `.long`/`.byte`/`.ascii`? |
| Symbolic pointers | 0-10 | All `.long` pointer values use labels? |
| Symbolic branches | 0-10 | All `call`/`jp`/`calr` use labels? |
| Shared source files identical | 0-10 | Same `.s` files are byte-identical? |
| Diff tells the story | 0-10 | Every diff line reflects a genuine change? |
| Minimal diff size | 0-10 | Diff is as small as possible? |
| Version constants centralized | 0-10 | Version-specific values in one place? |
| No post-build hacks | 0-10 | No binary patching, overlay, or fixup scripts? |
| Consistent formatting | 0-10 | Tab indentation, hex case, parenthesization? |

**Total: /100**

## See Also

- [Firmware Changes: v9 vs v10]({{ site.baseurl }}/firmware-v9-vs-v10/) -- the diff at its 95-line stage of 2026-03-25 (it reached 44 lines the same day: `diffs/v9_vs_v10_maincpu.diff`, `46f2e935b`, not regenerated since); at disassembly `3417969c0` the trees differ in 121 files, 34 of them PNGs only v10 carries (+15,289 / −2,565 lines: `git diff --shortstat 3417969c0:v9/maincpu 3417969c0:v10/maincpu`), so the minimisation needs redoing
- [LLVM Semantic Instructions]({{ site.baseurl }}/llvm-semantic-instructions/) -- Parenthesized operand syntax
