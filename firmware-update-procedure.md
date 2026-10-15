---
layout: page
title: Firmware Update Procedure
permalink: /firmware-update-procedure/
---

# KN5000 Firmware Update Procedure

This page describes how to update the firmware on a Technics KN5000 keyboard using an original Technics update disc or a custom-built update disc.

## Requirements

- Technics KN5000 keyboard in working condition
- 3.5" HD floppy disc containing the firmware update
- Stable power supply (do NOT disconnect power during the update)

## Available Update Types

| Update Type | Disc Signature | Target |
|-------------|---------------|--------|
| Program ROM (compressed) | `Technics KN5000 Program  DATA FILE PCK` | Main firmware |
| Table Data ROM (compressed) | `Technics KN5000 Table    DATA FILE PCK` | Tone/instrument data |
| Custom Data | `Technics KN5000 CMPCUSTOMDATA FILE` | Custom instrument patches |
| HDAE5000 Extension | `Technics KN5000 HD-AEPRG DATA FILE` | Hard disk expansion firmware |

Compressed ("PCK") discs are the standard format for v5 and later. Older uncompressed 2-disc sets (types 1-4) are also supported; no archived update uses them.

## Step-by-Step Procedure

### Standard Program ROM Update

1. **Power off** the KN5000.
2. **Insert** the update floppy disc into the disc drive.
3. **Hold all four PANEL MEMORY buttons (1, 2, 3 and 4)** and **power on** the keyboard.
4. The screen will display **"Please Wait !!"** while the system initializes.
5. After initialization:
   - **"Flash Memory Update"** appears at the top of the screen.
   - **"Now Erasing!!"** appears while the old firmware is being erased.
   - A **progress bar** grows across the screen during the erase process.
   - **"FD -> Flash Memory"** appears while data is being copied from the floppy to flash memory.
6. When the update is complete:
   - **"Completed!"** appears.
   - **"Turn On AGAIN !!"** appears below it.
7. **Power off** the keyboard, **remove** the floppy disc, and **power on** again.
8. The keyboard will boot with the new firmware.

### HDAE5000 Extension Update

The procedure is the same as above, with an HD-AE5000 update disc (type 6, `HD-AEPRG DATA FILE`). Only that disc type writes the HD-AE5000 ROM; program, table and custom-data discs never do.

If the HD-AE5000 board is not installed, a type-6 disc writes nothing and shows no message; the keyboard then stops and must be switched off.

### 2-Disc Updates (Legacy)

For older uncompressed updates using two floppy discs:

1. Follow steps 1-5 above with **disc 1**.
2. After disc 1 is written, the screen displays **"Change FD (2/2)"**.
3. **Remove disc 1** and **insert disc 2**.
4. The firmware verifies the disc and continues writing.
5. Steps 6-8 are the same as above.

If the wrong disc is inserted, "Change FD (2/2)" will be displayed again. Insert the correct disc to continue.

## Troubleshooting

### "Illegal Disk!" message

The floppy disc is not recognized as a valid update disc. This can happen if:
- The disc is not a genuine Technics update disc or a correctly formatted custom disc.
- The disc is corrupted or unreadable.
- A "disc 2 of 2" from a 2-disc set was inserted first (always start with disc 1).

**Recovery:** Power off the keyboard and power on again without the disc to boot normally.

### Screen is blank / keyboard doesn't respond

The update button was not held correctly during power-on, or the floppy disc is not detected. The keyboard may have booted normally instead of entering update mode.

**Recovery:** Power off and try again, ensuring the button is held before and during power-on.

### Progress bar stalls

The floppy disc may have a read error, or the flash chip is not responding.

**Recovery:** If the keyboard is unresponsive for more than 5 minutes, power off. The keyboard may still boot normally if the firmware was not partially erased. If the keyboard does not boot, the update must be retried with a known-good disc.

### Keyboard doesn't boot after update

The update may not have completed successfully. This can happen due to:
- Power interruption during the update.
- Defective floppy disc with undetected read errors.

**Recovery:** Attempt the update procedure again with a known-good disc. If the firmware is partially erased, the keyboard should still enter update mode on power-on.

## Safety Warnings

**Do NOT disconnect power during the update.** The firmware update erases the flash memory before writing new data. If power is lost during this process, the firmware will be partially erased and the keyboard will not boot normally. Recovery requires repeating the update with a valid disc.

**Use a stable power source.** Do not perform updates during thunderstorms or when the power supply is unreliable.

**Keep the update disc.** After a successful update, keep the update disc in a safe place. It may be needed for recovery if the firmware becomes corrupted.

## Technical Details

For technical documentation of the update process internals, see:
- [Firmware Update Display]({{ site.baseurl }}/firmware-update-display/) — LCD message state machine
- [Firmware Update Validation]({{ site.baseurl }}/firmware-update-validation/) — Validation checks and error handling
- [System Update Discs]({{ site.baseurl }}/system-update-discs/) — Disc format specification
- [Flash Programming]({{ site.baseurl }}/flash-programming/) — Flash erase/program routines

## Creating Custom Update Discs

Custom firmware update discs can be created with `tools/make_update_disc.py` from the [kn5000-anotherworld](https://github.com/felipesanches/kn5000-anotherworld) repository:

```bash
python tools/make_update_disc.py <rom_file> <output_disc.img> --type 7
```

See [System Update Discs]({{ site.baseurl }}/system-update-discs/#creating-update-discs) for details.

---

*Last updated: October 2026*
