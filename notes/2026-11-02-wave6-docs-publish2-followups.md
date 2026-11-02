# Wave 6 docs publication (lane docs-publish2, 2026-11-02): follow-ups

The drafts of the wave-6 lanes (technics-roms-disasm de0ad164e, figures re-read at fb8aaf94c) are
published by technics-docs 6d023e2..9ab5fa8 (nine commits). This lane did not edit technics-roms-disasm: the tracker
issues stay open there, and the errors below are left in the notes that carry them.

## Tracker issues the owner (or the next disassembly lane) can close

Each issue comment says "issue left open for the docs lane to publish the Website page draft and close".
The drafts are now on the site:

| issue      | pages                                                           | commit  |
|------------|-----------------------------------------------------------------|---------|
| kn5000-1gu | audio-subsystem.md, inter-cpu-protocol.md                       | 6d023e2 |
| kn5000-a1f | sequencer.md, inter-cpu-protocol.md                             | 6d023e2 |
| kn5000-zc1 | sequencer.md ("Song storage")                                   | 6d023e2 |
| kn5000-3qp | accompaniment-engine.md, rhythm-rom.md                          | f82ed3b |
| kn5000-rzg | accompaniment-engine.md                                         | f82ed3b |
| kn5000-j8z | the renamed labels on nine pages                                | 4cc30c2 |
| kn5000-rld | no page quoted a rld record (naming README); nothing to publish | -       |
| kn5000-wxn | wsa1-menu-map.md                                                | ac382a3 |
| kn5000-ax7 | upd6383-decode-status.md (BLOCKED: hardware)                    | 9f208d1 |
| kn5000-i2m | effects-dsp.md section 19 (BLOCKED: hardware)                   | 9f208d1 |
| kn5000-3ei | rom-reconstruction.md (table data 15,634 B)                     | f79bf37 |

## Errors found in the disassembly notes (not fixed here)

- `kn7000/notes/ic18-rhythm-rom.md` and `kn7000/notes/table-semantics-2026-10-29.md` still quote
  `func_<addr>` names that the same lane named in `kn7000_manual.sym` (`func_48436229` = `NoteConvApply`,
  `func_484361D8` / `F3` / `620E` = `NoteConvRuleByte1Get` .. `3Get`, `func_4843D558`, `func_4843CEF3`,
  `func_484420EF`, `func_484420C8`, `func_4844187A`, `func_48441DEB`, `func_48440533`, `func_484437DA`,
  `func_484439EB`, ...). The site uses the current names.
- `kn7000_manual.sym`'s `StyleCountInBoundGet` row says "func_48441DEB applies its program changes"
  (now `StyleTemplateRebuild`); `kn6000_manual.sym`'s `NoteConvRules` row says "the KN7000's
  func_48436229" (now `NoteConvApply`).
- `notes/open6-kn5000-d/accomp/README.md` says its renames are "not applied" and quotes the old names
  throughout; `rename_accomp.sed` says APPLIED in 5a5311c56.
- `notes/open6-kn5000-d/panel/README.md` counts 23,434 typed DSP slot records; the 2026-10-31 figure
  (`notes/kn5000-style-2026-10-31`) was 23,487 DSP slot records. The note does not reconcile the two.

## Left on the site

- `kn7000-wave-rom-format.md` and `media-files.md` still give 2,251 MAIN / 3,682 KN7000 WAV files and the
  `pcm_wav.py verify` round-trip counts of before 6cd18610c (W065 and the old W0AF are one WAV now; the
  wave notes say 2,250). Re-run `scripts/build/pcm_wav.py verify` and the data-incbin census before
  changing those figures.
- `tools/sound_categories_counts.py` still counts the string-scan lists that the cox catalogue replaced
  (notes-errors-2026-10-31 row 17's remark).
