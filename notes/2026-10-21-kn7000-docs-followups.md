# Follow-ups from the 2026-10-21 KN7000 documentation pass

The site was brought up to date with the KN7000 work of 2026-10-20/21 (commits `bde2906`..`173981e`).
These items belong outside the site, or need evidence the site cannot supply yet.

## Source repositories

1. **Closed (second pass).** kn7000_mame `9d4e47b` marks G13 and G22 done and published, with a
   History line. Was: **kn7000_mame `OVERLAY-GAPS.md` has stale state lines.** G13 says "in progress (decoded and built,
   not published)", and G22 says "in progress (branch `cpu-timing`, not published)". Yet `main` has
   merged `cpu-timing` (`a9e822a`), the gate was re-baselined (`f01af6b`), and the published binary
   `kn7000-emulator/kn7000` is md5 `3077b137f86844bbb8515d25c2d19008`, the G22 final binary. The
   History table has no line for the merge or the publish. The site (`mame-emulation-gaps.md`)
   calls both published.
2. **Closed (second pass).** technics-anotherworld `aa6cf1f` records the tone generator build on the
   unit (`97fbd9e6`, "plays properly; no further detail was recorded") and `9b1bc09` the DSP build.
   Was: **kn5000-anotherworld `kn7000/README-CNV.md` does not record the sound on the unit.** "What MAME
   cannot settle" still lists the sound on the instrument as unknown. The request for this pass
   relayed that the owner confirmed it plays on his KN7000. Record that run there (build SHA-1,
   what was heard, hanging notes or not, whether RIGHT 1/2/LEFT kept their voices). The site
   states the confirmation without those details.
3. **README-CNV's LCD wait-state claim.** "Speed" says the LCD frame sits "behind four wait states
   (the firmware leaves MEMCTR3 at `0x0424`)". kn7000_mame `notes/cpu-timing-2026-10-20/README.md`
   says the LCD is CS7 by the 64 MB map and that the MEMCTR fields are not documented. The site
   follows the cpu-timing notes. Reconcile the two.
4. **Half closed (second pass).** The site now says the menu has started `AW\` and DSPTONE on the
   unit (dsptone README: "in the menu, the 'DSP tone' row and RUN"; README-CNV: "from the menu's
   `AW\`"). The kn7menu README's table below still has to be updated. Was:
   **technics-roms-disasm `kn7000/tools/kn7menu/README.md`, "What is new on the unit"**, lists the
   menu route as MAME-only. If the owner ran the sound build of Another World from `AW\` through
   the menu, the menu has run on the unit. Record it there, then change the status on
   `kn7000-cnv-homebrew.md`.
5. **cnv_romdump README, pass 9.** It has the MAME run but no "on the owner's KN7000" subsection.
   The unit's results are only in kn7000_mame `notes/cpu-timing-2026-10-20/` and in the private
   `pass9-check-2026-10-20.txt`. A public summary beside passes 6-8's would help.
6. **32 MHz elsewhere.** The blog post "Learning to tell time" and the merged MAME driver's
   comments still give 32 MHz for the KN7000 (OVERLAY-GAPS G18 lists the driver side).

## Waiting for the unit

7. **Closed (second pass, `49bd8d9`).** DSPTONE ran on 2026-10-21: heartbeat 44,087/s, tone and
   sweep heard, reverb back after STOP; the level against a note was not measured (now a question
   on `questions.md`). Was: **DSPTONE's first run on the instrument.** Once it has run, update `kn7000-effects-dsp.md`
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
12. **Closed (second pass, `e12bc77`).** Was: **`kn7000-roadmap.md` row "Reset vector / version block"** says there is no boot ROM and the CPU
    starts at `0x48400000`. Pass 4 (2026-10-19) found IC18's boot ROM at `0x40000000`, the reset
    path (OVERLAY-GAPS G9). Not changed in this pass.

## Second pass (2026-10-21, after DSPTONE and Another World's DSP sound ran on the unit)

Site commits `49bd8d9`..(this note). Items 3, 5, 6, 8, 9, 10 and 11 above are still open: no new
source settles them (README-CNV "Speed" still has the MEMCTR3 `0x0424` wait-state sentence; the
cnv_romdump README still has no "pass 9 on the owner's KN7000" subsection; nothing new on SY-EW,
the TG chip selects or `notePitch16`). New follow-ups:

13. **Closed (third pass).** technics-anotherworld `fd1cfb7`: README-CNV now says Felipe heard the
    game with REVERB and CHORUS both off, and "Trying it on the instrument" names `a2fbbaa6` as run on
    the unit and round 3 as MAME-only. Was: **README-CNV is behind its own report.** "Trying it on the instrument" still opens "it has run
    only in MAME", and "What MAME cannot settle" / "Limits" still call unit 9's return unheard on
    the unit. Felipe's report (`9b1bc09`) says the game played with REVERB off, which only unit 9's
    return can carry. Record there whether CHORUS was on during that run; the site says the report
    does not say.
14. **Still open (third pass):** the line is unchanged at technics-roms-disasm `9082189`.
    **dsptone README, "Iteration 2", point 4** still says "Unit 9's path has not been heard on the
    unit yet". Same correction.
15. **Half closed (third pass).** The DSP plan (kn7000_mame `notes/PLAN-2026-10-21-dsp-emulation.md`,
    D1 and D9, confirmed on the unit in `c1f0380`) lists both, and OVERLAY-GAPS points G4 at the plan;
    OVERLAY-GAPS itself still has no item or side finding for either. Was: **OVERLAY-GAPS has no line for the DSP runs or the CHORUS return.** The overlay's bridge mixes
    unit 9's return only while CHORUS is on (probes/cnv README "Sound on the effects DSP"); if the
    instrument mixes it whatever CHORUS is, that is an emulator gap. Also not listed there: host
    uploads go straight into DSP memory, not through EPB0 and DMA channel 8 (dsptone README). The
    site lists both under `mame-emulation-gaps.md` (`d0d5ba1`).
16. **Closed (third pass).** `kernel-architecture.md` already has the unit walk with all ten CALL
    addresses (`0x8080` ... `0x80A0`, with the hops); the site's `kn7000-effects-dsp.md` now lists
    them (`ebfb055`). Was: **Each unit's CALL slot address.** The request for this pass called the slots "PM `0x8080` + n".
    The sources give unit 0 at `0x8080` and unit 9 at `0x80A0` (the chain has delay-slot words
    between the CALLs), not one word per unit. The site says "from `0x8080` (unit 0) to `0x80A0`
    (unit 9)". `kernel-architecture.md` section 5 could list the ten slot addresses.
17. **Closed (third pass, `8a9dfca`, `5a53759`).** Round 3 is committed (technics-anotherworld
    `8744a52`..`e4b87fa`) and the site describes it as MAME-only. Was: **Another World's third round** (faster bank loading, panel buttons dropped as controls, B and
    B♭ both up, the sound mode in the HELP screen, the help page URL) was uncommitted in
    technics-anotherworld when this pass looked (`42aaa5f` plus a dirty tree). The site describes
    `a2fbbaa6`: the panel controls, RIGHT 2 as the mode switch, HELP's mode line. Update
    `kn7000-cnv-homebrew.md` ("Another World on the instrument", "Sound") once it is committed.
18. **The bank's load time on the unit** was not timed ("felt slow"; 25.9 s in MAME). A figure
    from the unit would fill the throughput row on `kn7000-effects-dsp.md`. Third pass: round 3's
    coded bank takes 11.6 s in MAME and about 9.5 s is predicted for the unit; its help screen shows
    the time ("SENT IN n S"), so a photograph of it settles this.

## Third pass (2026-10-21, after round 3, the 60 MHz DSP, the noise study and the DSP plan)

Site commits `6eb13aa`..(this note). Sources read: technics-anotherworld `8744a52`..`e4b87fa`,
kn7000_mame `106b20e`..`74a3d26`, KN7000 `f3becdd`..`a9d6021`, technics-roms-disasm `4dae9e3e7`,
`908218944`. Items 3, 5, 6, 8, 9, 10, 11 and 14 are still open (no new source touches them: README-CNV
"Speed" still has the MEMCTR3 `0x0424` sentence; the cnv_romdump README has no pass-9 unit subsection);
item 4 is still half (the kn7menu README's "What is new on the unit" table is unchanged). New:

19. **README-CNV names the wrong current build.** "What goes where" gives `KN7APP.BIN`
    `7f8ed09a...` as this repository's build, but `e4b87fa` (UP on A♭5 or B♭5) built `94910f68...`, which
    the kn7menu README puts in the card's `AW\` and `probes/cnv/keys-results-2026-10-21/` tested. "Trying
    it on the instrument" and "What MAME cannot settle" also say round 3 is `7f8ed09a`. The site gives
    `94910f68` as the round-3 build.
20. **Felipe's verdict on the listening set is not recorded.** The request for this pass relayed that
    he listened to the computed recording of Another World's intro (`aw-intro-dsp-computed.wav`,
    kn7000_mame `notes/listen-2026-10-21/`) and called it perfect, which backs "the noise is speed".
    Neither that README nor OVERLAY-GAPS G19 records it; the site states it, attributed to the owner.
21. *Closed 2026-10-21 (`b294be6`: fixed as G23, kn7000_mame `7ad5627`, binary `06334896`; the sound page's note-off section corrected too).* **The MIDI note-off bug was open when this pass looked.** OVERLAY-GAPS at `74a3d26` lists it as a
    side finding, untraced; an uncommitted `notes/tg-release-2026-10-21/` suggests a fix in progress.
    When a fix is committed and published (new binary md5), update `mame-emulation-gaps.md` ("Notes
    received over MIDI don't stop", and the published binary's md5 and commit at the top of the
    KN7000 section) and OVERLAY-GAPS's own side finding.
22. **`RUNNING-THE-BUILDS.md` is not on GitHub.** The KN7000 repository is 276 commits ahead of
    `origin/main`, which has no `RUNNING-THE-BUILDS.md`, so the site cites it by path, not by link
    (`mame-emulation-gaps.md`, "Running it at full speed"). Link it once it is pushed.
23. **OVERLAY-GAPS G19's title still says "(noisy sound)"**, and its "Suggested order" predates the
    DSP plan. D2 (the dry sound with REVERB on) and D11/S15 (the interpreter's late IRQ0) live only in
    the plan and in G19's and G4's text, not as items of their own.

## Checks run at the end of the third pass

- `tools/check_nav.py`: 152 entries, 0 dead, 0 duplicates, order newest first; 0 pages linked from
  nowhere.
- `tools/check_tables.py --all` on the 7 pages touched: 29 tables, 0 misaligned.
- `tools/check_links.py` on one local build (`~/compartilhado/tmp/docs-build3/site`): 0 dead
  anchors; the same 10 older dead page links (written without `{{ site.baseurl }}`), none on a page
  touched here.
- `tools/check_doc_symbols.py` on the touched pages: 74 names listed, none on a line added in this
  pass (MAME identifiers, build variables and older text; `kn7000-roadmap.md`'s only on re-padded
  lines).

## Checks run at the end of the second pass

- `tools/check_nav.py`: 152 entries, 0 dead, 0 duplicates, order newest first; 0 pages linked from
  nowhere.
- `tools/check_tables.py --all` on the 8 pages touched and this note: 29 tables, 0 misaligned.
- `tools/check_links.py` on one local build (`~/compartilhado/tmp/docs-build2/site`): 0 dead
  anchors; the same 10 older dead page links as the first pass (written without
  `{{ site.baseurl }}`), none on a page touched here.
- `tools/check_doc_symbols.py` on the touched pages: 71 names listed, none on a line added in this
  pass (MAME identifiers and older text).

## Checks run at the end of the first pass

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
