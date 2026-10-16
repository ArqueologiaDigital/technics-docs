---
layout: page
title: KN7000 Tasks & Scheduler
permalink: /kn7000-task-scheduler/
---

# KN7000 Tasks & Scheduler

The KN7000 firmware's user interface runs as **two cooperative tasks** on top of the MILK kernel:
a **main** task (the foreground UI / panel loop) and an **AP** ("application")
task (background work — song/data processing, longer operations). They take turns
by explicitly sleeping and waking each other through a small message API. This
page documents that mechanism as decoded from `kn7000_program.rom`; it is the
companion to the [Event & Dispatch System]({{ site.baseurl }}/kn7000-event-system/), which is what
each task actually runs while awake. The kernel runs other tasks too, such as the
disk worker (MILK task 8, created by `DiskInit`; see
[Storage & File System]({{ site.baseurl }}/kn7000-storage-subsystem/#sd-subsystem-internals)).

## The two tasks

The main task and the currently-running task are identified by handles kept in
work RAM:

| Global       | Meaning                                                              |
|--------------|----------------------------------------------------------------------|
| `0x50380004` | handle (TCB) of task 1, the **main** task                            |
| `0x5038002C` | handle (TCB) of the **currently running** task                       |

(An earlier version of this page had the two labels the other way round. `cre_tsk`
indexes `0x50380000` by task id to reach a task's TCB, so `0x50380004` is task 1's, and
the dispatcher writes the next task's TCB to `0x5038002C` when it switches; read at boot,
both hold `0x50381470` because the main task is the one running. See
[Kernel tasks and the tick](#kernel-tasks-and-the-tick-build-942).)

Code decides "am I the main or the AP task?" by comparing them — exactly what the
event layer's `GetCurrentObjectId` helper (`func_48414A4F` in the disassembly) does
before it picks the active task's focused-object id (`0x500D3C60` for main,
`0x500D3C5C` for AP; see the
[event page]({{ site.baseurl }}/kn7000-event-system/)). So each task carries its own focused UI
object, and the event dispatcher always acts on the running task's object.

## Kernel tasks and the tick (build 942)

Read from the SP7001 firmware (program 942) and measured in MAME
(`notes/sp7001-probes/rate_probe.lua` in `kn7000_disassembly`):

| what             | value                                                                                                                                                                                                                                                                    |
|------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| task slots       | `cre_tsk` (`0x4C03D46B`; 941 `0x4C03D0C8`) takes a task's TCB from `0x50380000`, one pointer per task id, **ids 0–10**; `0xFFFFFFFF` marks a free slot (the next word, `0x5038002C`, is the running task)                                                                |
| tasks at boot    | ids 0, 1, 2, 3, 4, 7 and 8; ids 5 and 6 are created on demand; 9 and 10 are free (no task-creation call passes them as a constant)                                                                                                                                       |
| task 1 (main)    | entry `0x4C02BC27` (the library main loop), stack `0x6000`                                                                                                                                                                                                               |
| task 8           | `DiskWorkerTask` `0x4854AD7F`, stack `0xC00`                                                                                                                                                                                                                             |
| priority         | every firmware task runs at **3** (attribute 1, `TA_HLNG`); they share one ready queue                                                                                                                                                                                   |
| task descriptors | standard micro-ITRON 3.0 `T_CTSK`: exinf `+0`, attribute `+4`, entry `+8`, priority `+0x0C` (16-bit), stack size `+0x10`; the kernel allocates the stack                                                                                                                 |
| kernel tick      | `KernelTickHandler` (`0x4C02BB5F`; build 941 `0x4C02BB05`) increments `0x500D3C68` (941: `0x500D3C58`) at **1 kHz** (measured 999.5/s); it starts about 0.27 s after power-on, so it is milliseconds since the instrument was switched on                                |
| second time base | every other tick it calls `TimeBase2msTick` (`0x484D7920`; 941 `0x484D7931`), which increments `0x50151C0C` (941: `0x50151BFC`): **2 ms** units, 499.8/s in both builds. Earlier notes called `0x50151BFC` a 1 kHz tick; it is not. `GetTimBase` returns its low 16 bits |
| `dly_tsk(ms)`    | `0x4C03E295`: adds `ms` to `0x500D3C68` and loops on a kernel ready-queue rotation until that time, so it yields only to tasks of the same priority                                                                                                                      |

These services are exported to SP7001 plug-ins by name; the
[KN7000 Custom SD Apps]({{ site.baseurl }}/kn7000-sp7001-homebrew/) page uses them to run a task
of its own.

## Sleep / wake API

Four thin entry points let code hand control back and forth:

| Function         | CPU addr     | Effect                |
|------------------|--------------|-----------------------|
| `SleepMainTask`  | `0x48414B8D` | suspend the main task |
| `WakeUpMainTask` | `0x48414BA7` | resume the main task  |
| `SleepApTask`    | `0x48414BC1` | suspend the AP task   |
| `WakeUpApTask`   | `0x48414BDB` | resume the AP task    |

Each is a one-line wrapper that builds a **task-control message** and dispatches
it — decoded straight from the source (`SleepMainTask`):

```
SleepMainTask:                   # CPU 0x48414B8D
    add     -0x14, sp
    clr     d0
    mov     d0, (0x10, sp)       # message param slot = 0
    mov     0x00020009, d0       # message opcode/class
    mov     0x0006009D, d1       # message id  (see table)
    call    0x48414A77           # task-control message handler
    ret
```

The opcode in `d0` is the constant `0x00020009` for all four; the **message id in
`d1`** is what selects the action, and the ids form a small contiguous block:

| Message id   | Action                                                                                                               |
|--------------|----------------------------------------------------------------------------------------------------------------------|
| `0x0006009D` | sleep main                                                                                                           |
| `0x0006009E` | wake main                                                                                                            |
| `0x0006009F` | sleep AP                                                                                                             |
| `0x000600A0` | wake AP                                                                                                              |
| `0x000600A1` | refresh: posted by `RefreshApTask` after its re-broadcast; `MainTaskControl` re-posts it, `ApTaskControl` ignores it |

The main-task wrappers call `0x48414A77`, 3 bytes into `ApTaskControl`
(`0x48414A74`), just past its stack-frame `add`. The AP-side wrappers call
`0x48414AFD`, the same point in `MainTaskControl` (`0x48414AFA`). The names are
crossed relative to their callers, exactly as on the KN5000. Each is a
`switch` on `d1` that runs the matching sleep/wake code — from its first
instructions:

```
cmp 0x6009F, d1 ; beq …        # sleep AP
cmp 0x600A0, d1 ; beq …        # wake AP
cmp 0x6009D, d1 ; beq …        # sleep main
cmp 0x6009E, d1 ; beq …        # wake main
cmp 0x600A1, d1 ; beq …
```

The underlying context switch / run-queue lives in the **MILK kernel** (the
banner `MILK MN10300 Ver1.0R1` at program-file offset `0x3B8AAC`), part of which
runs from the library at `0x4C000000`. That library is not a separate ROM: at boot
`InitializeBlock27` (`0x484D7BBD`) copies it out of the program flash
(`LibRomImageBase`, `0x487B8FD1`), so it is preserved inside the dumped program
image.

## Task refresh

`RefreshApTask` (`0x48414BF5`) and `RefreshSwEvent` (`0x48414C98`) reset a small
block of task-state globals (`0x50021FD8`, `0x50021FDC`, `0x50021FE0`) and then
re-broadcast events (`mov -1, d0` with event-category ids `0x00050006` /
`0x00050005`) so the UI redraws after a task transition. This is the seam where
the scheduler hands back to the event system.

## Relationship to the KN5000

Cooperative main/AP tasking on the MILK kernel is **shared with the KN5000**
(same source tree — [Shared Codebase Map]({{ site.baseurl }}/technics-shared-codebase/)); the
message opcode/id convention and the sleep/wake naming carry across. What is
observed here for the KN7000 specifically are the concrete addresses — the task
handles (`0x50380004` / `0x5038002C`), the per-task focused-object pointers, the
message-id block (`0x6009D…0x600A1`) and the handler entry points.

## The same kernel is in four processors, across two products

This section concerns the KN5000's TLCS-900 kernel, not the KN7000's: between the KN5000 and the KN7000 the kernel was rewritten (see the [Shared Codebase Map]({{ site.baseurl }}/technics-shared-codebase/)). The KN5000's kernel, though, is shared well beyond the KN5000. The **SX-WSA1R**, a physical-modelling synthesiser built on a different
CPU family (two TMP95C061s against the KN7000's MN10300), runs the **same
multitasking kernel** — and so does each of the KN5000's two processors. One
kernel, four processors, two products.

The proof for the WSA1R pair is a build, not a resemblance: `wsa1/kernel/kernel.s`
is a single source that assembles into **2,180 bytes of `prom_a` and 2,180 bytes of
`prom_c`, both byte-identical to the real EPROMs**. Over the union of the two
blocks there are 941 instruction slots, 939 of them on both sides. 735 of those
needed no reconciliation; of the other 204, 129 differ in house style and 81 name a
per-CPU value (6 slots are both). Those 81 reduce to **21 named constants** (twelve
RAM addresses, six array sizes, three ROM pointers) — with no conditional assembly
anywhere in the file.

For the KN5000 the identification rests on **control-flow shape**, not byte
identity. Byte identity is the wrong measure across products: two processors in
the same product, from the same build, running the same source, still differ in
81 of 941 instruction slots, so a third built years apart cannot be closer. The
score is measured against a **foil control** of non-kernel code cut to the same
instruction counts:

|                              | routines | max   | median | min   | ≥ 0.70 |
|------------------------------|----------|-------|--------|-------|--------|
| kernel routines (≥ 20 instr) | 20       | 1.000 | 0.909  | 0.742 | 20     |
| non-kernel foils             | 26       | 0.333 | 0.212  | 0.143 | 0      |

No overlap, and a gap of 0.41.

⚠ **Do not trust the KN5000's kernel labels.** The measured alignment does not
match them: the site that actually corresponds to `MsgQueue_Send` is labelled
`TaskSched_Wait`, the one matching `Kernel_SemaSignal` is labelled
`TaskEvent_Wait`, and on the main CPU the site matching `Kernel_StartTask` at 0.978
is called `Show_ScreenGroup`. Several KN5000 kernel labels are simply wrong —
a renaming pass waiting to happen, and a reminder that names point an instrument at
a region without being evidence about it.

Not established: who wrote it, and that the sources are identical.
`Kernel_Dispatch` scores only 0.742, because the KN5000 version has no tick-drain
loop and its lock depth has moved out of a control register the TMP94C241 does not
have. The same program; not the same file.
