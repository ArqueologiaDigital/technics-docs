# Follow-ups from the picture ROM page and the first real-instrument dump (2026-10-19)

Left open when `kn7000-picture-rom.md` went in (commit `54f3bdc`).

- ~~**Owner check:** does the instrument's SOFT VERSION screen show `PICTURE : 7`?~~ **Answered**
  2026-10-19: the screen has no PICTURE row, only PROGRAM and TABLE (owner; MAME agrees). PICTURE
  is in the DEBUG TOOLS version box, which prints 7 in MAME with the ROM mapped.
- ~~Second reads~~ **Done** 2026-10-19: both passes were read twice the same day, byte-identical
  (files and manifests). PR #16517 is open; a note saying so is ready to paste in the KN7000 repo,
  `tools/mame-pr-planning/kn7000-v13-pr/comment-second-read.md`.
- **MAME:** declare IC19 as the 2 MB image (CRC-32 `3372cb5c`, SHA-1 `9631dedf...`) and map it with
  `.mirror(0x600000)` at `0x57800000`. **Prepared** 2026-10-19: branch `technics-kn7000-picrom`.
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
commit hashes resolve through `kn7000/notes/migration-commit-map.txt`. The owner renamed the GitHub
repository to `technics-roms-disasm` and pushed the same day; the site's 83 links to the old name
were rewritten to the new one (all 45 distinct URLs answer 200), and the KN7000 pages now link the
repository's `kn7000/` folder.
