# Follow-ups from the picture ROM page and the first real-instrument dump (2026-10-19)

Left open when `kn7000-picture-rom.md` went in (commit `54f3bdc`).

- **Owner check:** does the instrument's SOFT VERSION screen show `PICTURE : 7`? The chip's version
  string says it should (`kn7000-picture-rom.md`, "How they are stored").
- **Second reads** of pass 1 (program, table, IC21) and pass 2 (IC19), to show the reads are stable.
  Pass 1's also gates MAME PR #16517.
- **MAME:** declare IC19 as the 2 MB image (CRC-32 `3372cb5c`, SHA-1 `9631dedf...`) and map it with
  `.mirror(0x600000)` at `0x57800000`. Not started; owner decision on timing.
- **Build-893 recovery page:** check the 9,472 transcribed bytes against the real read. That grades
  the transcription method; the page now says it predates the read. The transcription's data is in
  `technics-roms-disasm` `kn7000/dumps/build893-photo-transcription/` (`screens.hex`, `screens.json`).
- **Remaining "unpreserved 893" wording**, not touched in `54f3bdc`, to reword now that 893/80 were
  read: `kn7000-memory-dump-screen.md` (lines ~35, ~335, ~653, ~662), `kn7000-rom-from-the-screen.md`
  (~21), `kn7000-sd-plugin.md` (~71, ~76), `kn7000-firmware-security.md` (~160), and the SOFT VERSION
  page's title.
- ~~`tools/check_doc_symbols.py` only knows the KN5000 disassembly~~ **Done** the same day: the
  KN7000 disassembly moved into `technics-roms-disasm` as `kn7000/`, and the checker now walks it
  (`.sym` files included). `kn7000-soft-version.md` went from 18 unmatched names to 6, all developer
  tags that were never source labels.

## The repositories moved (2026-10-19)

`kn5000-roms-disasm` is now `technics-roms-disasm` (the old path is a symlink), with the KN7000
disassembly inside it as `kn7000/`; `kn7000_disassembly` is decommissioned. The site's live
references were repointed; dated logs (notes/, roadmap entries) keep the old name, and their old
commit hashes resolve through `kn7000/notes/migration-commit-map.txt`. On GitHub the repository is
still `kn5000-roms-disasm` until the owner renames it; the site's existing links to that name will
keep working through GitHub's redirect.
