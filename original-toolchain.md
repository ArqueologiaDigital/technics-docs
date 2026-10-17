---
layout: page
title: Original Toolchain
permalink: /original-toolchain/
---

# Original Toolchain: Toshiba's TLCS-900 C Compiler

The KN5000 firmware is mostly compiled C. It was built with **Toshiba's own TLCS-900 C compiler
package**. The package is the `cc900` driver with its `thc1` and `thc2` passes, the `asm900`
assembler, the `tulink` linker and the `tuconv` converter, and it ships Toshiba's standard library
`c900ml.lib`. No ROM image contains a compiler banner or a version string, so the identification
rests on the code. The firmware links Toshiba's runtime library, which matches Toshiba's
published sources instruction for instruction. Its compiled code also follows Toshiba's
documented calling conventions.

The same toolchain built the KN5000 sub-CPU payload, its bootloader, the HD-AE5000 expansion
ROM and the KN1500. The SX-WSA1R is different: only part of it is Toshiba-compiled.

Everything below can be re-checked with one command in the disassembly repository,
`scripts/analysis/compiler_id/verify_toshiba_runtime.sh`; its README lists what each script answers.

## The firmware links Toshiba's runtime library

Toshiba shipped the library sources with the compiler. Its V4.23 release notes (1998-07-01) list
"Source files of standard Library", the run-time routine sources for the long and floating types,
and the startup samples `stc9*ml.c`. A later edition of the package (Ver1.10, 2009) is public and
still holds those 1994-1997 sources. The KN5000's copies are the same instruction sequences:

| Toshiba routine (source file in the package)                                    | KN5000 copy                                                                        | match                              |
|---------------------------------------------------------------------------------|------------------------------------------------------------------------------------|------------------------------------|
| `C9H_mulls` / `C9H_mullu` (LMULL.ASM, 1994)                                     | main CPU 0xFF0A5C (`Math_Multiply32`); also sub CPU and HD-AE5000                  | 10 of 10 instructions              |
| `SDivMod`, `C9H_remls`, `C9H_divls`, `C9H_remlu`, `C9H_divlu` (LDIVL.ASM, 1994) | main CPU 0xFF0BC3-0xFF0C91; bootloader (table data) 0x9FFC0E                       | 96 of 96 instructions, both copies |
| `memcpy`, TLCS-900 inline assembly (_MEMCPY.C, 1995)                            | main CPU 0xFF0D99 (`Mem_Copy`)                                                     | 17 of 17 instructions              |
| `_ctype[256]` (_CTYPE.C, 1994)                                                  | main CPU 0xEED778 (`CType_ClassTable`); HD-AE5000 0x2F9362                         | 256 of 256 bytes                   |
| `._fcmp_d`, `._fcmp_f` (CMP_D.MAC, CMP_F.MAC, 1996)                             | sub CPU 0x3D2AC (`FP_dcmp`), 0x3D306 (`FP_fcmp`)                                   | 34 of 34, 26 of 26 instructions    |
| `_startup` section initialisation (STC94ML.C)                                   | main CPU 0xEF0B46 (f_area clear) and 0xEF0BB0 (f_data copy), in `Boot_InitWorkRAM` | 19 of 19, 11 of 11 instructions    |

The `_ctype` match is a strong fingerprint. Toshiba's bit layout (`__BLK` = 0x40,
`__HEX` = 0x80) is not the BSD one, and every one of the 256 bytes agrees. The rest of the
sub-CPU floating-point library also matches instruction for instruction, including the
`._fadd`, `._fsub`, `._fmul` and `._fdiv` routines in both precisions and the
`TAB_EQ` / `TAB_LT` / `TAB_GT` compare tables.

The library's C modules match by algorithm and data layout:

- `Sprintf_Core` is Toshiba's `_doprnt`. It has the same flag bits, and the statics `padchar`
  and `out_cnt` sit at RAM 0x3C220 and 0x3C222. It uses 15 significant digits for `double` and
  18 for `long double`.
- `Heap_Alloc` is `sbrk`.
- The bootloader's compare routine (`Boot_memcmp`, 0x9FFBDC) is Toshiba's `strncmp`. The main
  CPU has the same 50 bytes at 0xFF0CC1 (`String_Compare`).
- The first initialised words that `Boot_InitWorkRAM` copies to RAM 0x3D524 are 0x10030,
  0x7800 and 0. They are `SBRK_break`, `SBRK_size` and `_allocb`, the three variables
  Toshiba's startup sample defines first.

Matsushita edited some modules. Its `malloc` and `free` take the kernel lock around Toshiba's
code, and the audio code has a lock-protected copy of `sprintf`.

### The copies date the library

The unsigned divide `udiv32` exists in three releases among these ROMs:

| image                                  | normalisation step in `udiv32` | library release                                           |
|----------------------------------------|--------------------------------|-----------------------------------------------------------|
| SX-WSA1R (1995)                        | `j eq,skip` and `sra 1,XBC`    | oldest; the 2009 source keeps these two lines as comments |
| HD-AE5000 v2.06i (1996), sub CPU v1.42 | `stcf 0,BC` and `rrc 1,XBC`    | intermediate                                              |
| KN5000 main CPU and its bootloader     | `rr 1,XBC`                     | as in the 2009 source                                     |

So the HD-AE5000's divide is not a re-encoding of the main CPU's: it is an older release of
the same library routine.

## The compiled code follows Toshiba's calling conventions

Toshiba's compiler has two calling conventions:

- `__cdecl`, the default, passes every argument on the stack. The caller removes them, and the
  result comes back in XHL.
- `__adecl`, which the `-Xr` option also selects, passes the first three arguments in WA/XWA,
  BC/XBC and DE/XDE and the rest on the stack. The callee removes the stack arguments with
  `retd`.

The KN5000's own functions use `__adecl`. The library functions that Toshiba's headers declare
`__CDECL` (`malloc`, `free`, `memcpy`, `strncmp`, `sprintf`, `_doprnt`) take their arguments
from the stack. `sbrk`, declared `__adecl`, takes its size in XWA (`Heap_Alloc`).

The code generator's other habits match too. The counts are over the v10 main-CPU source:

| property                      | measured in the KN5000 v10 source                                              | Toshiba cc900                                                |
|-------------------------------|--------------------------------------------------------------------------------|--------------------------------------------------------------|
| result register               | zero-test right after a call: 1,455 on L / HL / XHL, 26 on A / WA / XWA        | "The return value is stored to register XHL"                 |
| registers saved by a function | first save at a frame entry: XIZ 970, IZ 201, QIZ 163, none 553; never XIX/XIY | library: `push XIZ ; for C compiler`                         |
| frame                         | 956 `lda xsp,(xsp-N)`; `link` / `unlk` only in 33 hand-written stubs           | locals addressed through XSP, no frame pointer               |
| far pointer argument          | two word pushes, high half first (`pushw Sym@hi16`, `pushw Sym@lo16`)          | V4.23 sample: `pushw S1 >> 16`, `pushw S1 & 0xffff`          |
| `switch`                      | 71 + 69 jump tables of 16-bit `Case - Base` words read by `jp T,(XIX+WA)`      | "six or more case statements ... a jump table"; `dw L%u-L%u` |
| data model                    | `int` and `size_t` 16 bits, `long double` 10 bytes                             | LIMITS.H `INT_MAX` = `SHRT_MAX`; FLOAT.H `LDBL_MANT_DIG` 64  |

IAR's ICCT900, the only other TLCS-900 C compiler found for the period, does not fit. Its 1996
datasheet says it passes one parameter of up to four bytes in a register, and that the called
function saves the registers it uses. The KN5000 code passes three and saves only XIZ.

## Other firmware built with the same tools

| image                          | Toshiba runtime / startup            | `switch` jump sequences     | code generator       |
|--------------------------------|--------------------------------------|-----------------------------|----------------------|
| KN5000 main CPU v10 (1998)     | library and `_startup`, as above     | 71 + 69                     | Toshiba cc900        |
| KN5000 sub-CPU payload v1.42   | multiply, divide, float library      | 18                          | Toshiba cc900        |
| KN5000 bootloader (table data) | divide, heap, `strncmp`, startup     | 4                           | Toshiba cc900        |
| HD-AE5000 v2.06i (1996)        | multiply, divide, `memcpy`, `_ctype` | 4 + 49                      | Toshiba cc900        |
| SX-KN1500 IC15 (1996)          | startup blocks                       | 50                          | Toshiba cc900        |
| SNK Neo Geo Pocket BIOS (1998) | startup at 0xFF8991                  | 3                           | Toshiba cc900        |
| SX-WSA1R prom_a (1995)         | divide (`udiv32`, oldest release)    | 9, all in 0xFE0000-0xFEFFFF | mixed                |
| SX-WSA1R prom_b / prom_c       | none                                 | 0                           | a different compiler |

The Neo Geo Pocket BIOS makes the same `__adecl` calls ending in `retd`. SNK's System Program
Reference Manual names its development language as the "Toshiba Micro-controller development
language (C compiler ... Assembler)". So these were the standard tools for TLCS-900 products of
the time.

## What is not known

- **The exact release.** The sub CPU links the 1996 rewrite of the floating-point library,
  which keeps its work area on the stack. Toshiba's notes list that change after V4.1x, so the
  toolchain is V4.20 (in use by May 1996) or later; V4.23 is dated 1998-07-01. Nothing pins the
  release or the compiler options (`-Xr`, or `__adecl` written on each prototype).
- **The SX-WSA1R's user-interface compiler.** That code uses `link` / `unlk` frames, returns
  results in A or WA, pushes byte arguments as single bytes, and has its own floating-point
  runtime. That is not Toshiba's documented convention, and the compiler has not been
  identified. Only the modules at prom_a 0xFE0000-0xFEFFFF are Toshiba-compiled.

## What it means for the project

- **Homebrew calling firmware routines** must use Toshiba's `__adecl` convention for the
  firmware's own functions: three arguments in XWA, XBC and XDE, the rest on the stack, a
  `retd` in the callee, and the result in XHL. Library routines take `__cdecl`: every argument
  on the stack, popped by the caller. The project's LLVM backend has a convention of its own
  (`CCAssignToReg<[XDE, XBC, XIX, XIY]>`, see the [HD-AE5000 homebrew]({{ site.baseurl }}/hdae5000-homebrew/)
  page). A call into the firmware therefore needs a wrapper or an attribute that follows
  Toshiba's order.
- **Toshiba's library names** apply to these routines: `SDivMod`, `C9H_remls`, `C9H_divls`,
  `C9H_remlu`, `C9H_divlu`, `sbrk`, `_doprnt`, `._fadd_d` and the rest. The disassembly keeps
  descriptive labels and records the Toshiba names in comments.

## Sources

- Toshiba TLCS-900 C compiler, Ver1.10 package: https://ahchay.com/NGPC/Downloads/T900.zip
  (sha256 `70687d4b166f73d230fe3b20c8827a50807bdef891fcbda2c6491667f813f4c0`). The files used
  are `README/HIS96CE0.TXT` (release history), `LIB/SRC/*` (library sources),
  `CUSTOMIZ/C900_H2/STC94ML.C` (startup sample) and the C Compiler Reference (tde121-01,
  function qualifiers).
- IAR ICCT900 datasheet (1996):
  https://web.archive.org/web/19970726122154/http://www.iar.se:80/Datasheets/tlcs900.pdf
- SNK Neo Geo Pocket Support CD (1999.4):
  https://web.archive.org/web/20210413082004/http://devrs.com/ngp/files/DoNotLink/MSWord/ManUpdate01/
- Reproduction: `scripts/analysis/compiler_id/` in the
  [kn5000-roms-disasm](https://github.com/ArqueologiaDigital/kn5000-roms-disasm) repository.
