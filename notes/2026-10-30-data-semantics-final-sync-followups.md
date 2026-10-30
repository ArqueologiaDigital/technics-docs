# Follow-ups from the 2026-10-30 sync of the data-semantics work (final state)

The sync (commits `63ac628`..`a9316c8`) put the KN7000 program data region and GUI, the SP7001
plug-in's screens, the KN6000 / KN7000 panel-memory field names, the KN6000 / KN6500 / HD-SX6 and
KN2400 program data, and the first committed census snapshot
(`docs/coverage/data-incbin-2026-10-30-01`) on the site, from technics-roms-disasm `39fc875ef`.
New pages: `kn7000-menu-map.md`, `kn7000-data-region.md`, `kn7000-sp7001-plugin.md`,
`kn7000-panel-memory.md`, `kn6000-program-data.md`, `kn2400-program-data.md`. Left open:

**Errors in the disassembly repository's notes** (the site uses the current source names; the
notes should be corrected there):

- `kn7000/notes/gui-data-region/README.md`, "Jump and pointer tables into code": the chord-type
  switch of `TechniChordCompute` is called `ptrs_485BC3EC`; the label is now
  `TechniChordCompute_Table_2` (`src/program/data/labels.sym`). Same file, "The built-in demo
  songs": `ptrs_50000C20` / `_50000C50` / `_50000C80` are now `func_48457350_Table`,
  `_Table_2` and `_Table_3`. Same file, "Third pass": `TgElemNoteOnStd_Table` is "128 x u16, 0..8191"; the source's
  header now says 0..16383.
- `kn2400/notes/data-region/README.md`, "Demo songs": `ptrs_50000C18` / `C48` / `C78` are now
  `func_486183E3_entry_L44_Table`, `_Table_2` and `_Table_3`.
- `kn7000/notes/data-rest/README.md`, "Records a pointer leads to": "StyleRecordTable (1,085
  records of 24 bytes)"; the source (`src/program/data/data_03.s`) declares 1,080 records. The site
  quotes 1,080.
- `hdsx3/README.md`, "Open work": "414 small data pieces (6,623 bytes) are still binary" predates
  lane siblings-final (snapshot: 40 generic pieces / 266 bytes, 101 opaque / 3,133); and "The
  plug-in has no direct call ... Where those pointers come from ... has not been traced"
  contradicts the same README's "The data region and the plug-in's GUI", which says they go
  through the KN6000's block-0 Function table (registry slot `0x100`).
- `kn7000/kn7000.sym` comments `ResourceIdTrie` as "used by libROM 0x4C01BB1C"; the walker the
  notes and the code name is `func_4C01BB1A`.

**On the site, not done in this sync:**

- The "Names" tables of `kn6000-disassembly.md` and `kn2400-disassembly.md` (and the matching
  `source-tree-inventory.md` rows) still give the 2026-10-24 counts of the `*.sym`, `*_manual.sym`
  and `*_ported.sym` files; the pages now say so. A recount should come from a committed probe,
  not by hand.
- `kn6000-names.md` and `kn6000-roadmap.md` were not reviewed against the new `functions.sym`
  files (551 KN6000 procedure names from the MILK function tables).
- The KN6500's built-in Music Stylist (1,080 setups) and the KN2400's two lists could get a
  catalogue page like `kn7000-rhythm-catalog.md`, generated from `StyleRecordTable`.
