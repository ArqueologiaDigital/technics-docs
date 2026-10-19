# Follow-ups from the picture ROM page and the first real-instrument dump (2026-10-19)

Left open when `kn7000-picture-rom.md` went in (commit `54f3bdc`).

- **Owner check:** does the instrument's SOFT VERSION screen show `PICTURE : 7`? The chip's version
  string says it should (`kn7000-picture-rom.md`, "How they are stored").
- **Second reads** of pass 1 (program, table, IC21) and pass 2 (IC19), to show the reads are stable.
  Pass 1's also gates MAME PR #16517.
- **MAME:** declare IC19 as the 2 MB image (CRC-32 `3372cb5c`, SHA-1 `9631dedf...`) and map it with
  `.mirror(0x600000)` at `0x57800000`. Not started; owner decision on timing.
- **Build-893 recovery page:** check the 9,472 transcribed bytes against the real read. That grades
  the transcription method; the page now says it predates the read. The transcription's data file
  was not found while writing this.
- **Remaining "unpreserved 893" wording**, not touched in `54f3bdc`, to reword now that 893/80 were
  read: `kn7000-memory-dump-screen.md` (lines ~35, ~335, ~653, ~662), `kn7000-rom-from-the-screen.md`
  (~21), `kn7000-sd-plugin.md` (~71, ~76), `kn7000-firmware-security.md` (~160), and the SOFT VERSION
  page's title.
- **`tools/check_doc_symbols.py` only knows the KN5000 disassembly**, so every KN7000 name on a
  KN7000 page is reported as missing (18 on `kn7000-soft-version.md`). Teaching it
  `kn7000_disassembly` (`src/symbols.inc`, `*.sym`) would make the check meaningful there.
