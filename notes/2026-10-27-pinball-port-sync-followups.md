# Follow-ups from the 2026-10-27 sync of the Pinball Fantasies port's findings

The sync (commits `6c21fd2`..`4a7b35f`) put the RAM chips and chip selects, the library SRAM, the
usable RAM (ARENA1-7), the cache sequence, the S1D13806 LCD controller, the panel LED shadow and
knob ring, and the MAME changes of 2026-10-26/27 on their owner pages. Left open:

- **`mame-emulation-gaps.md`, first paragraph of "KN7000: the overlay emulator"**: it still names the
  published binary as md5 `06334896…` from kn7000_mame `7ad5627` (2026-10-21). The binary in
  `kn7000-emulator/` was republished on 2026-10-27 (md5 `105fa7f3…`), while kn7000_mame had
  uncommitted changes to `kn7000.cpp`; which commit it was built from is not recorded.
- **`kn7000-memory-dump-screen.md`, the ROM-row table**: the `PICTURE ROM: IC19` row says
  "Undumped, and unmapped in MAME", but `kn7000.md` and `kn7000-picture-rom.md` say IC19 was read
  on 2026-10-19.
- **The Pinball repository's `kn7000/notes/ram-inventory-2026-10-27/README.md`** says 941 clears
  only `0x20000` bytes at `0x50298000`. The 941 disassembly (`src/program/region1_00.s`,
  `0x4841003E`) clears `0x168000`, to `0x50400000`, as 893 and 942 do; the site keeps the
  disassembly's figure. The note should be corrected in that repository.
- **Not on the site yet**: the MN10300 far `(d32,An)` load that raises a system-error NMI and
  restarts the KN7000 (kn7000_mame `de0191c`, `a582ec5`, 2026-10-26).
- **Unit confirmation**: the knob's LED blinking, best-score letters by the knob and the side
  panels in the ink layer are documented from MAME runs. When the owner reports them on the unit,
  update the status box of `kn7000-cnv-homebrew.md`.
