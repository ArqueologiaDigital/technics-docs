# Follow-ups from the 2026-10-21 KN7000 documentation pass

The site was brought up to date with the KN7000 work of 2026-10-20/21 (commits `bde2906`..`173981e`).
These items belong outside the site, or need evidence the site cannot supply yet.

## Source repositories

1. **kn7000_mame `OVERLAY-GAPS.md` has stale state lines.** G13 says "in progress (decoded and built,
   not published)", and G22 says "in progress (branch `cpu-timing`, not published)". Yet `main` has
   merged `cpu-timing` (`a9e822a`), the gate was re-baselined (`f01af6b`), and the published binary
   `kn7000-emulator/kn7000` is md5 `3077b137f86844bbb8515d25c2d19008`, the G22 final binary. The
   History table has no line for the merge or the publish. The site (`mame-emulation-gaps.md`)
   calls both published.
2. **kn5000-anotherworld `kn7000/README-CNV.md` does not record the sound on the unit.** "What MAME
   cannot settle" still lists the sound on the instrument as unknown. The request for this pass
   relayed that the owner confirmed it plays on his KN7000. Record that run there (build SHA-1,
   what was heard, hanging notes or not, whether RIGHT 1/2/LEFT kept their voices). The site
   states the confirmation without those details.
3. **README-CNV's LCD wait-state claim.** "Speed" says the LCD frame sits "behind four wait states
   (the firmware leaves MEMCTR3 at `0x0424`)". kn7000_mame `notes/cpu-timing-2026-10-20/README.md`
   says the LCD is CS7 by the 64 MB map and that the MEMCTR fields are not documented. The site
   follows the cpu-timing notes. Reconcile the two.
4. **technics-roms-disasm `kn7000/tools/kn7menu/README.md`, "What is new on the unit"**, lists the
   menu route as MAME-only. If the owner ran the sound build of Another World from `AW\` through
   the menu, the menu has run on the unit. Record it there, then change the status on
   `kn7000-cnv-homebrew.md`.
5. **cnv_romdump README, pass 9.** It has the MAME run but no "on the owner's KN7000" subsection.
   The unit's results are only in kn7000_mame `notes/cpu-timing-2026-10-20/` and in the private
   `pass9-check-2026-10-20.txt`. A public summary beside passes 6-8's would help.
6. **32 MHz elsewhere.** The blog post "Learning to tell time" and the merged MAME driver's
   comments still give 32 MHz for the KN7000 (OVERLAY-GAPS G18 lists the driver side).

## Waiting for the unit

7. **DSPTONE's first run on the instrument.** Once it has run, update `kn7000-effects-dsp.md`
   ("Our own program on the DSP") and `questions.md`. Record the heartbeat rate, whether the tone
   and the sweep were heard, the level against a note, and whether STOP brought the reverb back.
8. **The LCD slowdown** (`questions.md`): pass 9's LCD tests vary up to 2.4x and Another World saw
   3-4x. A probe that times LCD stores with the display blanked, against the same stores with it
   running, would test the "controller holds the CPU off" explanation.

## Owner decisions or research

9. **SY-EW boards: ROM or RAM?** The request for this pass called them "wave-ROM boards". The
   site's `kn7000-expansion-and-wave-dump.md` says the firmware checks an
   "Expansion Board KN7000 SOUND RAM" signature and that the CPU loads samples into the board. The
   owner's manual says only that EW EXPANSION selects the board's preset sounds. The sound page now
   avoids saying either; settle it (service manual §8.12, the firmware's board loader).
10. **Which TG is on which chip select.** `kn7000-sound-subsystem.md`'s port table puts master IC201
    at `0x98040000`. The WAVE ROM test reads the pair it labels IC203/IC204 (the master's, per the
    schematic) through `0x98050000`. The new text flags the conflict and `questions.md` lists it.
    The schematic's decoder outputs would settle the table.
11. **`kn7000-sound-subsystem.md`, "How a note's pitch really works"** still describes the overlay's
    voice-record pitch read in the present tense. Check whether the overlay still uses
    `notePitch16` for the synthetic pack (KN6000/KN6500/KN2400) and rewrite the section to match.
12. **`kn7000-roadmap.md` row "Reset vector / version block"** says there is no boot ROM and the CPU
    starts at `0x48400000`. Pass 4 (2026-10-19) found IC18's boot ROM at `0x40000000`, the reset
    path (OVERLAY-GAPS G9). Not changed in this pass.

## Checks run at the end of this pass

- `tools/check_nav.py`: 152 entries, 0 dead, 0 duplicates, order newest first; 0 pages linked from
  nowhere.
- `tools/check_tables.py --all` on the 18 pages touched: clean after `--fix` (17 older compact
  tables re-padded in `173981e`).
- `tools/check_links.py` on a local build (`~/compartilhado/tmp/docs-build/site`): 0 dead anchors.
  It reported 10 dead page links, all older and none on a page touched here: links written without
  `{{ site.baseurl }}` in `panel-parameter-keys.md`, `sound-editor-screens.md`,
  `sound-parameter-protocol.md` and `ui-framework.md`.
- `tools/check_doc_symbols.py` on the touched pages: no firmware symbol added in this pass is
  missing. The names it lists are MAME identifiers and build variables on lines that were only
  re-padded.
