---
layout: page
title: "Dumping the KN7000 Wave ROMs with a Raspberry Pi Pico"
permalink: /kn7000-wave-rom-dump/
---

# Dumping the KN7000 Wave ROMs with a Raspberry Pi Pico

A step‑by‑step, non‑invasive way to dump the four undumped KN7000 PCM wave ROMs
(**IC203 / IC204 / IC207 / IC208**, 16 MB each, 64 MB total) — no desoldering, no firmware
changes, and **verifiable byte‑for‑byte** against checksums baked into the instrument's own firmware.

**Status:** untested on hardware. No capture has been made with this method yet; the pin map comes from
the service-manual schematic, and the timing and throughput figures are estimates to be confirmed by
the trial capture described under Notes & troubleshooting.

## Why it works

The service‑mode **§8.9 WAVE ROM test** makes the tone generator read *every word of every wave ROM
sequentially* to compute a checksum. Those reads cross the external wave bus, which is brought out on
plug‑in **80‑pin expansion connectors**. We simply **listen** while the test runs.

The bus (~1–2 MB/s during the test) is faster than the Pico's USB (~1 MB/s), so we capture **1 in 4**
words per run — each tagged with its low address bits — and run the test **4 times** (phases 0‑3) to
cover everything. The Pico's PIO does the timing; a laptop reassembles the passes and checks the
result against the golden checksum.

> **This is passive.** The keyboard's own test drives the bus; you never drive anything, so there is
> no risk of bus contention and no need to tri‑state the tone generator.

## What you need

- A **Raspberry Pi Pico** (RP2040) — any variant. Its 3.3 V logic matches the bus.
- ~20 jumper wires and a way to tap an 80‑pin connector (a mating header, or fine probe wires).
- A laptop with Python 3 (`pip install pyserial`).
- Your KN7000 and the key sequence to enter service mode (hold **C#3 + D#3 + C#4** while switching on),
  then PAGE to the WAVE ROM item (§8.9) and EXECUTE.

> ⚠ **3.3 V only.** Power the Pico from your **laptop's USB**. **Do not** connect the connector's
> `+5D` or `+3.3D` pins to the Pico. **Share ground.** Handle boards static‑safe.

## Step 1 — the connector and pin map

Four connectors carry the wave bus (two per tone-generator side), all with the **same** layout:

| connectors | ROMs | service‑manual page |
|---|---|---|
| CN204 / CN206 (A‑side) | IC203, IC204 | p112 |
| CN208 / CN209 (B‑side) | IC207, IC208 | p114 |

Each connector serves **two ROMs** sharing the 16‑bit data bus, told apart by output‑enable:

| ROM | address bus | strobe | which |
|---|---|---|---|
| **bank X** — IC204 (A) / IC208 (B) | `WAX` | `WOEX` = **pin 79** | A‑side / B‑side connector |
| **bank Y** — IC203 (A) / IC207 (B) | `WAY` | `WOEY` = **pin 5** | same |

**Data bus `WD0..WD15` → connector pins:**
```
WD0 =36  WD1 =37  WD2 =42  WD3 =44  WD4 =34  WD5 =32  WD6 =47  WD7 =49
WD8 =38  WD9 =39  WD10=43  WD11=45  WD12=33  WD13=31  WD14=48  WD15=50
```
**Address LSBs (the tag), 7 bits:**
- bank X: `WAX0..WAX6` = pins **57, 58, 59, 60, 61, 62, 63**
- bank Y: `WAY0..WAY6` = pins **27, 26, 25, 24, 23, 22, 21**

**Ground (`DE`):** any of pins 3, 4, 28, 29, 30, 35, 46, 53, 56, 80.

## Step 2 — wiring

Wire the (physically scrambled) connector pins to **consecutive** Pico GPIO so PIO reads them in one go.
For **bank X** (IC204/IC208); for bank Y use the `WAY` pins and `WOEY` instead.

```
  80-pin wave-bus connector                 Raspberry Pi Pico
  -------------------------                 -----------------
  WD0  (p36) ---------------------------->  GP0    \
  WD1  (p37) ---------------------------->  GP1     |
   ...  (see table)                              |  } 16 data bits
  WD15 (p50) ---------------------------->  GP15   /
  WAX0 (p57) ---------------------------->  GP16   \
   ...                                            |  } 7-bit address tag
  WAX6 (p63) ---------------------------->  GP22   /
  WOEX (p79) ---------------------------->  GP26      (read strobe / trigger)
  DE   (p80) ---------------------------->  GND
                                            (Pico powered from laptop USB)
```

## Step 3 — Pico firmware (PIO capture + USB stream)

`wavecap.pio` — samples 23 bits (16 data + 7 tag) on each strobe and pushes **every 4th** sample. The
phase (which quarter) is seeded by the host into scratch register `X`.

```
.program wavecap
.wrap_target
    wait 1 gpio 26          ; resync: strobe idle (high)
    wait 0 gpio 26          ; strobe asserted (falling edge = ROM read)
    nop            [10]     ; ~88 ns settle -- TUNE from the trial capture (Notes & troubleshooting)
    in   pins, 23           ; latch GP0-22 : {WAX0-6 (7), WD0-15 (16)}
    jmp  x--, skip          ; decimate /4 : if X!=0 -> X--, drop
    push noblock            ; X==0 -> keep this sample
    set  x, 3               ; reload /4
    jmp  cont
skip:
    mov  isr, null          ; discard
cont:
.wrap
```

`main.c` — arm on a `'0'..'3'` byte from the host, then stream 3 bytes per kept sample. Build with the
standard **pico‑sdk** setup (copy a CMakeLists from `pico-examples/usb`); link `pico_stdlib`,
`hardware_pio`, `tinyusb_device`.

```c
#include "pico/stdlib.h"
#include "hardware/pio.h"
#include "tusb.h"
#include "wavecap.pio.h"        // generated from wavecap.pio

#define WOE 26                  // GP26 = WOEX (or WOEY)

int main(void) {
    tusb_init();
    PIO pio = pio0; uint sm = 0;
    uint off = pio_add_program(pio, &wavecap_program);
    for (int i = 0; i < 23; i++) pio_gpio_init(pio, i);   // GP0..GP22 inputs
    pio_gpio_init(pio, WOE);
    pio_sm_set_consecutive_pindirs(pio, sm, 0, 23, false);
    pio_sm_config c = wavecap_program_get_default_config(off);
    sm_config_set_in_pins(&c, 0);                 // in-base = GP0
    sm_config_set_in_shift(&c, false, false, 32); // shift left, no autopush
    pio_sm_init(pio, sm, off, &c);

    uint8_t buf[3000]; int n = 0; int armed = 0;
    while (true) {
        tud_task();
        if (!armed) {                              // wait for a phase command
            if (tud_cdc_available()) {
                int ch = tud_cdc_read_char();
                if (ch >= '0' && ch <= '3') {
                    pio_sm_set_enabled(pio, sm, false);
                    pio_sm_clear_fifos(pio, sm);
                    pio_sm_restart(pio, sm);
                    pio_sm_exec(pio, sm, pio_encode_set(pio_x, ch - '0'));  // seed phase
                    pio_sm_set_enabled(pio, sm, true);
                    armed = 1; n = 0;
                }
            }
            continue;
        }
        while (!pio_sm_is_rx_fifo_empty(pio, sm)) {
            uint32_t v = pio_sm_get(pio, sm) & 0x7FFFFF;   // 23 valid bits
            buf[n++] =  v        & 0xFF;
            buf[n++] = (v >> 8)  & 0xFF;
            buf[n++] = (v >> 16) & 0xFF;
            if (n >= (int)sizeof(buf) - 3) { tud_cdc_write(buf, n); tud_cdc_write_flush(); n = 0; }
        }
        if (n) { tud_cdc_write(buf, n); tud_cdc_write_flush(); n = 0; }
    }
}
```

> The exact bit order inside the 23‑bit word (data in `[0:15]`, tag in `[16:22]`) depends on the ISR
> shift direction — the **trial capture (Notes & troubleshooting) confirms it** (the tag must count
> up). If it comes out reversed, flip the `shift_right` argument (the second parameter of
> `sm_config_set_in_shift`, `false` here).

## Step 4 — the laptop receiver

`kn7000_wavedump.py` — arms each phase, reassembles one ROM by counting + tag‑verification, and checks
the golden checksum. Run once per ROM (`ic203`/`ic204`/`ic207`/`ic208`).

```python
#!/usr/bin/env python3
import sys, serial
PORT = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyACM0'
ROM  = sys.argv[2] if len(sys.argv) > 2 else 'ic204'
GOLD = {'ic203':0x8164C77C, 'ic204':0x815CFC83, 'ic207':0x8331EF0B, 'ic208':0x83254F9D}
WORDS, DECIM, TAG = 8*1024*1024, 4, 0x7F          # 8,388,608 words = 16 MB
rom  = bytearray(WORDS*2)
seen = bytearray(WORDS)
ser  = serial.Serial(PORT, timeout=0.3)

def run_pass(phase):
    ser.reset_input_buffer(); ser.write(bytes([ord('0')+phase]))
    print(f"  phase {phase}: run the WAVE ROM test now...")
    buf, k, drops, got = b'', 0, 0, 0
    while True:
        chunk = ser.read(65536)
        if not chunk:
            if got: return got, drops                # idle => this pass is done
            continue
        buf += chunk
        while len(buf) >= 3:
            b, buf = buf[:3], buf[3:]
            v = b[0] | b[1]<<8 | b[2]<<16
            data, tag = v & 0xFFFF, (v>>16) & TAG
            addr = phase + DECIM*k
            if addr >= WORDS: return got, drops
            if tag != (addr & TAG): drops += 1        # dropped sample -> pass is dirty
            rom[addr*2], rom[addr*2+1] = data & 0xFF, data >> 8
            seen[addr] = 1; k += 1; got += 1

for phase in range(DECIM):
    while True:
        got, drops = run_pass(phase)
        print(f"    {got} samples, {drops} drops")
        if drops == 0: break
        print("    -> drops; re-running this phase")   # cheap: just run §8.9 again

cov = seen.count(1)
print(f"coverage {cov}/{WORDS}")
s = 0
for i in range(WORDS):
    w = rom[i*2] | rom[i*2+1]<<8
    s = (s + (w>>8) + (w&0xFF)) & 0xFFFFFFFF
hit = [k for k, g in GOLD.items() if g == s]   # the chip-to-checksum pairing is not settled (Step 6)
print(f"checksum {s:#010x}  golden {GOLD[ROM]:#010x}  {'OK ✅' if s==GOLD[ROM] else f'matches {hit[0]} ✅' if hit else 'MISMATCH ❌'}")
open(f"{ROM}.bin", "wb").write(rom)
```
*(The pure‑Python checksum over 8 M words takes a few seconds; use `numpy` if you want it instant.)*

## Step 5 — the dump procedure

1. Wire the Pico to the A‑side connector for **bank X** (`WD0‑15`, `WAX0‑6`, `WOEX`, `GND`). Plug the
   Pico into your laptop.
2. `python3 kn7000_wavedump.py /dev/ttyACM0 ic204`
3. When it says *"run the WAVE ROM test now"*, trigger **§8.9** on the keyboard. The script captures
   phase 0, then prompts for phase 1, 2, 3 — **re‑run §8.9 for each** (no power‑cycle needed).
4. It reports coverage and the checksum. `OK ✅` → `ic204.bin` is byte‑perfect.
5. Move the address tag to `WAY0‑6` and the strobe to `WOEY` (pin 5); run with `ic203`. Then repeat on
   the **B‑side** connector for `ic208` (WOEX) and `ic207` (WOEY).

Four ROMs × 4 phases = 16 test runs, ~20–30 minutes total.

## Step 6 — verify

The golden checksums (Σ of `hi+lo` bytes over all words, straight from the firmware):

| ROM | checksum |
|---|---|
| IC203 | `0x8164C77C` |
| IC204 | `0x815CFC83` |
| IC207 | `0x8331EF0B` |
| IC208 | `0x83254F9D` |

Which checksum belongs to which chip is not settled: the four values are stored per firmware test (port
`0x9805` first, then `0x9804`; bit 0 = 0, then 1), and which chip each port and bit reach has not been
confirmed (see the ⚠ note on the
[expansion page]({{ site.baseurl }}/kn7000-expansion-and-wave-dump/#-the-wave-roms-are-cpu-readable-through-the-tone-generator)).
The chip names in this table and in `GOLD` follow that page's assumption. The connector and strobe you
wired identify the chip: if its dump matches a *different* chip's value, the dump is still good, and the
match settles the mapping.

A match proves the *content* is right. It does **not** catch a whole‑ROM byte swap (`hi+lo` is
order‑independent), so wire `WD0→GP0 … WD15→GP15` in order and keep the low byte low.

## Notes & troubleshooting

- **Do a 0.1 s trial capture first.** Arm one phase, run §8.9, look at the first few samples: the tags
  must **increment by 4** (proving the 1‑in‑4 capture, the bit order, and that the sweep is sequential).
  If tags increment by 1 instead of 4, the strobe isn't per‑word — see the next point.
- **`WOE` per word vs. page mode.** If the tone generator holds `WOE` low and just steps the address,
  trigger on the **`WAX0`/`WAY0` LSB** toggling instead of `WOE` (move that wire to GP26). The trial
  capture tells you which.
- **Sampling instant.** Tune the `nop [n]` delay so you sample while data is valid — if you get noise,
  increase it (or sample on the rising edge: replace the delay with a second `wait 1 gpio 26`).
- **Determinism / drops.** The reassembly is self‑checking: a dropped sample shows as a tag mismatch and
  the script just re‑runs that phase. Because §8.9 is a deterministic sequential sweep, coverage reaches
  100 % in 4 clean passes; a glitch only costs one extra run.
- **Throughput.** ÷4 with 3‑byte samples ≈ 0.8 MB/s, under USB full‑speed. If your setup drops a lot,
  go **÷8 / 8 phases** (change `DECIM` and the `set x, 7` / seed).

## See also

- [KN7000 Expansion Bus & Wave‑ROM Dump Routes]({{ site.baseurl }}/kn7000-expansion-and-wave-dump/) — why the wave port
  works and the software alternative
- [ROM Dumping Roadmap]({{ site.baseurl }}/rom-dumping-roadmap/)
