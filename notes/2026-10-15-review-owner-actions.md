# Technics docs review, 2026-10-15: actions outside the site

The full review of this site (three rounds: per-page find, adversarial verify, fix; then
cross-page fixes and a coherence sweep) changed only the pages, the menu and `tools/`. These are
the fixes it found that belong elsewhere: in a source repository, upstream MAME, the LLVM
branch, or a decision only the owner can make. The reviewers' 190 notes were merged into this
list and spot-checked on 2026-10-15 (`still true`: yes / no / not checked). This directory is
kept off the published site (`_config.yml`).

## Decisions raised by the coherence sweep

- **kn7000-roadmap.md keeps a public development log** (the dated UPDATE / CORRECTION entries
  under "Development log", about 60 of them), although CLAUDE.md says the site is not a
  changelog. Keep it under its "history, not current state" banner, move it to kn7000_mame
  notes, or prune it.
- **The full KN5000 service manual is published on the site** (`service_manual/`, linked from
  three pages, tracked since 23ec5d0), while roadmap.md says Panasonic service manuals are
  copyrighted. Decide which statement holds.
- **The SP7001 key generator's evidence lives only in research-scratch**, which has no remote,
  so readers of kn7000-sp7001-activation.md cannot check it. Publish the algorithm's evidence
  somewhere public, or say on the page that it is not published.
- **index.md "About" sentence** was reworded from "All content is verified against actual
  hardware behavior" (not true) to a description of the actual practice (6b68219). It is in
  the owner's voice: approve or rewrite.
- **Tables written before this review are still compact.** Every table the review touched is
  aligned; a one-time `python3 tools/check_tables.py --all --fix *.md` would align the rest.

## owner: push or publish repositories (blocks reproducibility and the pages' links)

- Push llvm-project tlcs900_backend up to the TOOLCHAIN_VERSION pin a3a81863f87d to github.com/felipesanches/llvm-project. Then drop the 'not yet pushed' notes on index.md:197-198, llvm-semantic-instructions.md:284, tlcs900-instruction-encoding.md:491 and wsa1-disassembly.md.
  Evidence: `git ls-remote https://github.com/felipesanches/llvm-project.git refs/heads/tlcs900_backend` -> 86332721969d; `git rev-list --count 86332721969d..a3a81863f87d` -> 32; kn5000-roms-disasm TOOLCHAIN_VERSION:10 pins a3a81863f87d.
- Push kn7000_mame main to ArqueologiaDigital/MAME_Technics_Research, so that the notes the pages cite stop returning 404. These include 183e0ef notes/FINDINGS-test-jig-port.md and notes/kn7000-driver-source-annotations.md, which kn7000-driver-internals.md:22-24 cites.
  Evidence: `git -C kn7000_mame rev-list --count origin/main..main` -> 340; `git ls-remote origin refs/heads/main` -> 0eaa46a (= origin/main); `git branch -r --contains 183e0ef` -> none; curl of github.com/.../blob/main/notes/kn7000-driver-source-annotations.md and FINDINGS-test-jig-port.md -> 404.
- Either publish kn7000_extraction and kn7000_disassembly, or have every page that cites them say 'not yet published', as kn7000-initial-data.md:55 does. The citing pages are kn7000.md:143-150, kn7000-image-gallery.md, kn6000-names.md and kn7000-system-update-discs.md.
  Evidence: `git -C kn7000_extraction remote -v` and `git -C kn7000_disassembly remote -v` are empty. An anonymous `git ls-remote` of github.com/{ArqueologiaDigital,felipesanches}/{kn7000_extraction,kn7000_disassembly} prompts for credentials, so neither is public.
- Publish custom-kn5000-roms, which holds the App Loader source that app-loader.md and playing-games.md describe, or keep those pages' 'not yet published' notes.
  Evidence: An anonymous `git ls-remote https://github.com/ArqueologiaDigital/custom-kn5000-roms.git` prompts for credentials (not public).
- Commit Mines LLVM_TLCS900_BUGS.md, the only detailed record of the backend bugs, and push kn5000_port, if the pages are to link it again.
  Evidence: `git -C Mines status --short` -> '?? LLVM_TLCS900_BUGS.md'; kn5000_port is 3 commits ahead of its upstream.
- Publish the SP7001 reproducers, now only in research-scratch, which has no remote (kn7000-sp7001/ and kn7000-sp7001-activation/: invert.py, keygen.js, keygen_test.js, the trace and inject Lua scripts), for example under kn7000_mame tools/. Strip their absolute paths first, so that both SP7001 pages can link them.
  Evidence: `git -C research-scratch remote -v` is empty; absolute paths remain at kn7000-sp7001-activation/README.md:62-64 and trace_param1_build.lua:22.
- Note that kn5000-docs main is itself unpushed, so none of the round-1 and round-2 page fixes are on the published site yet.
  Evidence: `git -C kn5000-docs rev-list --count @{u}..HEAD` -> 245 (origin = ArqueologiaDigital/technics-docs).

## owner commit: round-2 producers (beside the code or in kn5000-docs tools/, the rest into research-scratch)

- Commit kn5000-tones/scripts/ic307_flag_counts_by_page.py, or fold its 0x80-split count into tools/ic307_wave_directory.py, because waveform-rom-format.md:85 still says '0x80 occurs 52 times in the whole chip' with no committed producer.
  Evidence: waveform-rom-format.md:85; `grep -n '0x80\|split' tools/ic307_wave_directory.py` -> no match; the script is at research-scratch (harvested from the review scratch) round2/kn5000-tones/scripts/.
- Commit kn7000-panel-tables/count_table_jpegs.py (and count_style_lists.py), suggested home kn7000_extraction or kn7000_mame notes/table-rom-probes/, because kn7000-table-rom.md still quotes 119 JPEGs and 117 that decode with no committed producer.
  Evidence: kn7000-table-rom.md:23 and :36 ('119 images, 117 of which decode'); no producer in kn5000-docs tools/. Not checked: whether kn7000_extraction image_extract.py's catalog reproduces 119.
- Commit kn5000-toolchain-methods/probes.sh (pin check, decoder gaps, MUL/DIV and SCC, relocation link test), for example to kn5000-roms-disasm notes/syntax-convergence-probes/, because the tm2-20..26 fixes, such as tlcs900-instruction-encoding.md:98 ('ca 99' invalid encoding), rest on it.
  Evidence: tlcs900-instruction-encoding.md:98; probes.sh exists only in round2/kn5000-toolchain-methods/; not in kn5000-docs tools/ or in research-scratch (git ls-files).
- Commit kn5000-hdae5000/probes/ui_titles_count.py beside the code, and reconcile the on-screen-title count: hdae5000-resources.md:192 says 49, the source says 48 and the probe finds 50.
  Evidence: hdae5000-resources.md:192 '49 of the 178 named descriptors'; kn5000-roms-disasm hdae5000/hdae5000_data_tables.s:9606 'ALL 48 agree'.
- Commit the script that produced upd6383-decode-status.md's §4 unlock cascade, R1 '80.8 % -> 95.2 %' and R2 '+1045' figures, or say which subset R1 means, since the cascade's own end point is 97.5 %.
  Evidence: upd6383-decode-status.md:19, :191, :219 still quote 95.2 % and +1045. `grep -rl '95\.2 %\|1045'` over kn5000-roms-disasm/dsp and kn7000_mame/notes finds only data dumps under dsp/analysis/data/, and dsp/tools/decode_leverage.py prints only the single-axis table.
- Promote compare_hdae5000_renders.py next to scripts/build/convert_images.py in kn5000-roms-disasm while image-gallery.md keeps its mis-coloured-render caveat.
  Evidence: image-gallery.md:179 caveat; the script is only at research-scratch sessions/2026-10-15_kn5000-d/compare_hdae5000_renders.py.
- Harvest the remaining round-2 lane producers from research-scratch (harvested from the review scratch) round2/ into research-scratch, and promote beside the code any whose figure goes on a page. The scripts are slide4k_stream_length.py, payload_chooser_bytes.py, ia_hdae5000_versions.py/.sh, composer_directory_framing.py, ic19_style_names.py, v9_v10_func_compare.py, sld_two_streams.py, ic307_bit7_not_last.py, check_zone_table.py, se_switch_table_slots.py, naka_records_per_class.py, cite_lines.py, sendcomm_census.py, rhythm_mode_census.py, count_ei_pattern.py, count_plugin_strings.py, check_activation_addrs.py, table83_layout.py, test_gold_line.py, kn7000_syms.py and ev_compare.py.
  Evidence: All exist in the lane scratch directories, but `git -C research-scratch ls-files | grep <stem>` finds none of the 28 stems checked. Only name_addr_check.py is in research-scratch (sessions/2026-10-15_kn5000-d/). commit d36ed8c harvested round-1 lanes only.

## kn5000-anotherworld (felipesanches/kn5000-anotherworld; local custom-kn5000-roms/anotherworld)

- Fix tools/make_update_disc.py: its compress_lzss import still points to kn5000-roms-disasm/scripts/compress_lzss.py, which moved to scripts/build/ in a63f092eb, so the published tool that three site pages cite fails with ModuleNotFoundError. Also have it append the compressed sub-CPU payload as a second SLIDE4K stream for type 7, or refuse type 7.
  Evidence: make_update_disc.py:31-38 builds '../../../kn5000-roms-disasm/scripts/compress_lzss.py'; `ls kn5000-roms-disasm/scripts/compress_lzss.py` -> missing, scripts/build/compress_lzss.py exists. The type-7 payload half was not re-checked.
- Make the Makefile copy kn5000_subprogram_v142_compressed.rom, which MAME's kn5000 has loaded since #15143, instead of kn5000_subprogram_v142.rom, and push the local path-neutralising commit 5dc3442.
  Evidence: Makefile:81-83 lists kn5000_subprogram_v142.rom; upstream kn5000.cpp:761 loads kn5000_subprogram_v142_compressed.rom. The public HEAD is 10567af, and local 5dc3442 is 1 ahead (PROJECTS_ROOT ?= $(HOME)/compartilhado at :25).

## kn5000-roms-disasm: broken or misleading tools, scripts and repository docs

- Fix scripts/build/decompress_lzss.py, whose SLIDE4K match length is (high & 0x0F) + 2 where the firmware and compress_lzss.py use + 3, so it under-decodes (1,871,248 B instead of 2,097,152 for the v5 stream). Refresh its stale docstring and the 'length + 2' comment at table_data/kn5000_table_data.s:4395-4397 in the same change.
  Evidence: decompress_lzss.py:82 '(high & 0x0F) + 2'; compress_lzss.py:78 '+ 3'; decompress_lzss.py:13 '~33KB', :24 COMPRESSED_BIN, :26 REBUILT_SUBCPU; kn5000_table_data.s:4395 '; Extract length: (byte & 0x0F) + 2'.
- Update scripts/converters/panel_button_actions_retype.py INPUTS to say 'mamedev/mame#15919' and ENCODER_0_OUTPUT/ENCODER_1_OUTPUT, because otherwise regenerating control-panel-protocol.md's action table undoes the round-1 row-25 fix. Also fix the matching comment in audio_control_engine.s (v10/v9/v7).
  Evidence: panel_button_actions_retype.py:427-431 ('kn7000_mame PR 9', '(ENCODER_0)', '(ENCODER_1)'); v10/maincpu/audio/audio_control_engine.s:2226-2227 'as the kn7000_mame data-wheel patch feeds them'.
- Restore the label DemoSongPreset_PointerTable: before the first `.long DemoSongPreset00` in table_data/kn5000_table_data.s, dropped by 43deafb0f, and regenerate symbols/table_data_symbols_reference.txt, because three pages name it.
  Evidence: `grep -n DemoSongPreset_PointerTable table_data/kn5000_table_data.s` -> only comment lines 347, 951, and :1052 `.long DemoSongPreset00` has no label; the symbols reference has no entry; boot-sequence.md:948, feature-demo.md:170, lzss-compression.md:113 use the name.
- Make convert_images.py give each HD-AE5000 bitmap its own trailing palette (or copy hdae5000/images/HDAE5000_*.png), give Wallpaper_0/1 their trailer palettes, and re-run `make gallery`, so that image-gallery.md's render caveats can go.
  Evidence: scripts/build/convert_images.py:30-37 still maps all HD-AE5000 main images to HDAE5000_Palette_0x65dce.bin; image-gallery.md:179 'Render caveat'.
- Fix or retire scripts/generators/generate_all_screendata.py, whose REPO resolves to scripts/ and which writes to pre-split maincpu/ paths.
  Evidence: generate_all_screendata.py:19 `REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` (file is scripts/generators/).
- Port scripts/analysis/decode_screendata.py and scripts/tools/annotate_screendata_main.py to the typed style_ui/*.c / .bin layout; ui-framework.md documents them as broken.
  Evidence: decode_screendata.py:168 and annotate_screendata_main.py:27 hard-code maincpu/includes/style_ui_screendata_main.s.
- Update the regex in scripts/analysis/naka_class_descriptors.py, which matches only 'RegObjTable 0x1600004,' and so finds no tables now that the sources spell NAKA_CLASS_Class, or retire it in favour of nakarest_objtab_map.py --check-classes.
  Evidence: naka_class_descriptors.py:66 `re.match(r'\s*RegObjTable\s+0x1600004,...`.
- Fix hdae5000/tools/verify_pport_strings_stride.py, which still looks for `lda_24` (respelled in 8ae043393) and so passes vacuously on 0 call sites.
  Evidence: verify_pport_strings_stride.py:29 TABLE_END_LABEL 'HDAE5000_Code_2_PartB:', :30 CALL_SITE_RE `lda_24\s+xbc`.
- Stop wsa1/notes/reachability.py --targets from rewriting the tracked wsa1/notes/reachability-cache.json (untrack it, or write beside the git-ignored .reachability-cache.json), because running the command documented on wsa1-disassembly.md dirties the tree.
  Evidence: reachability.py:712 CACHE = notes/reachability-cache.json (tracked: `git ls-files`), :215 RESULT_CACHE = notes/.reachability-cache.json; tracked copy last changed 8d1951841 (2026-09-02).
- Teach wsa1/notes/sound/wsa1_unspellable_forms.py to try the `<op>a r` shift-by-A spelling and to recognise prom_b's '; ADDR mnemonic [llvm-mc cannot encode this]' convention, so that prom_b stops reading 0.
  Evidence: `grep -n 'slaa\|slla\|srla\|cannot encode' wsa1/notes/sound/wsa1_unspellable_forms.py` -> no match.
- Regenerate diffs/v9_vs_v10_maincpu.diff or label it historical, and make v9/maincpu/shared/positional_labels.s identical to the v10/v7 copies (Rule 6).
  Evidence: The diff is 44 lines from 46f2e935b; `diff -rq v9/maincpu v10/maincpu | wc -l` -> 127; `cmp v9/.../positional_labels.s v10/...` -> differs at EOF (v7 = v10).
- Refresh the docstring of scripts/analysis/nakarest_objtab_map.py, which still quotes 292 classes / 3,340 records / 2,869 of 3,340, while the tool prints 293 / 3,365 at 3417969c0.
  Evidence: nakarest_objtab_map.py:26-27 '2,869 of the 3,340 v10 records'; tool output saved in round2/kn5000-ui/{classes_v10.txt,objtab_v10.txt}.
- Update the CLAUDE.md 'Preset Data Destination' dispute row, which still states the sub-CPU 0xF000+ reading and cites the deleted table_data/preset_data.asm; the block is demo-song preset 18.
  Evidence: kn5000-roms-disasm CLAUDE.md:1200 '... goes to Sub CPU 0xF000+ ... `table_data/preset_data.asm`'.
- Correct docs/subcpu_boot_protocol.md and docs/mame_driver_issues.md, which put `SET 0, (PA)` at 0xEF05F3 where llvm-objdump of the v10 ELF puts it at 0xEF05F8.
  Evidence: docs/subcpu_boot_protocol.md:186, :260 and docs/mame_driver_issues.md:18, :130 say 0xEF05F3 (the 0xEF05F8 address was not re-measured).
- Refresh dsp/instruction-set.md, which technics-docs upd6383-datasheet.md calls its source of truth: its store gate and its 'Still OPEN' counts predate the 2026-09-13/14 decoding. Otherwise reword the datasheet page's 'authoritative' claim.
  Evidence: dsp/instruction-set.md:258 'NOT (bit7 and hi12[3:1]==1)' versus the promoted gate (580a3b94d, kn7000_mame 617ccc3); :332-334 '14 of the 18 ... 17 of the 24'.
- Fix the DSP generators, then regenerate dsp/flowcharts and the site's flowcharts/ pages. gen_dsp_disasm.py still calls the reverb 'all-pass diffuser ladders' (SOLVED), which N-REVERB-NOT-UNDUMPED rejects, and gen_dsp_flowcharts.py attributes the frame restart to the strapped-inactive Fs-RST pin.
  Evidence: dsp/tools/gen_dsp_disasm.py:83; dsp/tools/gen_dsp_flowcharts.py:588 ('`Fs-RST`/`PC-RST` pins restart').
- Correct dsp/hardware/upd6383-pinout.md, which says the KN5000 wires the uPD6383's serial host port, when the firmware drives the parallel port (port Z plus /WR, /RD, /CS, C/D on P7).
  Evidence: upd6383-pinout.md:99-101 'The KN5000 wires the serial side'; v142 kn5000_subprogram_v142.s:50330-50395 per the lane (not re-read).
- Correct analysis/strings/README.md, which claims there are no error messages, no debug strings and English only, although the v10 ROM has 'Media Error', 'Debug Test' and French, German and Indonesian UI strings.
  Evidence: analysis/strings/README.md:29-32.
- Fix the 'Auto-generated by scripts/naka_struct_decode.py' header in naka_widget_descriptors.c (v10, probably v9/v7) to scripts/converters/naka_struct_decode.py.
  Evidence: v10/maincpu/ui_widgets/naka_widget_descriptors.c:6; `ls scripts/naka_struct_decode.py` -> missing, scripts/converters/naka_struct_decode.py exists.
- Close the v7-cdata row in analysis/binclude-audit-2026-08-07/PLAN.md, whose work 1528605e8 did.
  Evidence: PLAN.md:223 row still reads as open; `git log -1 1528605e8` -> 'v7: de-circularised -- the build no longer reads its own ROM'.
- Drop the retired label HDAE5000_Config_Strings from scripts/build/convert_images.py and the 'Not yet extracted to hdae5000/images/' comment above the splash .incbin, since those images now exist.
  Evidence: convert_images.py:75; hdae5000/hdae5000_data_tables.s:16147.

## llvm-project tlcs900_backend

- Make TLCS900ELFObjectWriter refuse non-constant :8 operands and range-check :16 ones, because FK_Data_1 maps to R_TLCS900_NONE and FK_Data_2 to R_TLCS900_LO16, so relocatable symbols link as 0 or silently lose their upper bits.
  Evidence: llvm/lib/Target/TLCS900/MCTargetDesc/TLCS900ELFObjectWriter.cpp:57-60; the lane's link test (probes.sh sections 5 and 7): foo at 0x12345 -> `c0 00 21` / `c1 45 23 21`.
- Make `scc cc, <32-bit reg>` a parse error, because the pinned llvm-mc accepts it and emits zero bytes with no diagnostic.
  Evidence: `printf 'scc z, xwa\n' | llvm-mc.snap -triple=tlcs900 -show-encoding` (sha256 118bb4d6766e) -> 'scc z, xwa ; encoding: []'.
- Close three disassembler gaps. Decode the 0x98+d register-to-register LD and the D7-prefix bank-3 word forms. Stop `e8 03 05 00 00 00` decoding to an `ld xwa, 5` that reassembles to different bytes.
  Evidence: llvm-mc.snap --disassemble: '0xca 0x99' and '0xd7 0x30 0x88' -> 'invalid instruction encoding'; '0xe8 0x03 0x05 0x00 0x00 0x00' -> 'ld xwa, 5'.
- Teach the disassembler shift-by-A, and add instruction definitions for rotate-by-A (rlc/rrc/rl/rr A,r, sub-opcodes 0xF8-0xFB), so that prom_a's `rrc A,H` can be written.
  Evidence: `echo '0xcb 0xff' | llvm-mc.snap -triple=tlcs900 --disassemble` -> warning 'invalid instruction encoding', prints 'swi 7'; `rrc a, h` -> 'error: invalid operand for instruction'.
- Correct the comment 'Previous register bank 16-bit registers (QWA-QSP)' and the PrevGR16 class name: these are the upper 16 bits of the current XWA-XSP.
  Evidence: llvm/lib/Target/TLCS900/TLCS900RegisterInfo.td:116 comment, :129 `def PrevGR16`.

## kn7000_mame (overlay source, notes and tools)

- Revert 142655e. interleave_roms.py weaves single bytes where ROM_LOAD32_WORD alternates 16-bit words, so its control matches only a mis-woven image, and the real KN7000 reset jump goes to 0x4840FF7E (crt0). Restore 0x4840FF7E in kn7000.cpp, mn10300.cpp and the notes, and fix interleave_roms.py's weave.
  Evidence: `git log -1 142655e` -> 'the KN7000 reset vector is jmp 0x48407EFF'; src/mame/matsushita/kn7000.cpp:75, :793 and src/devices/cpu/mn10300/mn10300.cpp:178 say 0x48407EFF; tools/interleave_roms.py:79-80 `b[0::2]=e; b[1::2]=o`. The first instruction of kn7000_extraction/output/kn7000_program.rom (xxd of 5 bytes) decodes to jmp 0x4840FF7E, matching notes/irq-vector-probes/README.md:191. mame-upstream has no 48407EFF.
- Decide from the board whether HD-AE5000 address 0x130020 decodes to ATA Device Control, and remap if so. The overlay maps CS1 register 0 there, so MAME drops the firmware's SRST/nIEN writes and the soft reset never reaches the drive in emulation.
  Evidence: src/devices/bus/technics/kn5000/hdae5000.cpp:114-115 maps 0x130020-0x13002f to cs1 ('device control at offset 6 = 0x13002C'); kn5000-roms-disasm hdae5000/hdae5000_ui_display.s:19826-19827 `ld (0x130020:24), 14` / `10`.
- Record one `mame kn5000 -extension hdae5000` run with no -harddisk to settle the no-disk text on hdae5000-mame-setup.md, or default the ATA slot to empty as kn5000_pr6_hdae5000 (554e89a0542) did.
  Evidence: src/devices/bus/technics/kn5000/hdae5000.cpp:136 `ATA_INTERFACE(config, m_ata).options(ata_devices, "hdd", nullptr, false)`; the run itself was not done.
- Rewrite the stale power-down comment block in src/mame/matsushita/kn5000.cpp ('WE DO NOT MODEL THIS', 'NO workaround', 'skip the payload transfer') and change 0xEF0580 to 0xEF0583. The same theory is in KN7000 side-quests/findings/kn5000_driver_findings.md:592-600.
  Evidence: kn5000.cpp:445 'WE DO NOT MODEL THIS', :452 'NO workaround', :363 '0xEF0580'; contradicted by the modelled POWER switch and 86aae9e ('stop persisting the volatile work DRAM as NVRAM').
- Correct the kn5000.cpp porte_read comment that says that before 7ecb444 the hard disk was 'never probed': HDAE5000_Check_HD_Present runs regardless of PE.0, and only HDAE5000_Parport_Setup is gated.
  Evidence: src/mame/matsushita/kn5000.cpp:1441 'never probed, even with the card selected'.
- Replace the retired names ToneGen_Read_Voice_Data and ToneGen_Calc_Pitch in kn5000.cpp comments with Keybed_Read_Event and Keybed_Decode_Event, and fix kn5000_tonegen.cpp's '48kHz (matching DAC sample rate)' (the instrument's Fs is 44.1 kHz).
  Evidence: src/mame/matsushita/kn5000.cpp:377-378, :395; src/mame/matsushita/kn5000_tonegen.cpp:183.
- Change '32 entries' to 33 for the wheel acceleration curve: notes/kn5000-wheel-probes/curve.py reads range(32), its README says '32 signed longs' and 'The current HLE hardcodes 0x8E94', and kn5000_cpanel.cpp's comment says '32 entries'.
  Evidence: notes/kn5000-wheel-probes/curve.py:7 `range(32)`; README.md:14; src/mame/matsushita/kn5000_cpanel.cpp:1240.
- Refresh upd6383.cpp's 'every frame is discarded' header and comment, which STRATEGIC-REVIEW-2026-07-31.md:69 already called stale.
  Evidence: src/devices/cpu/upd6383/upd6383.cpp:15, :6493.
- Refresh the kn7000.cpp comments that call 0x9805000E a 'sound-interface register' that 'sound init spins on' (it is the SD SPI clock-rate latch) and that say the TG's effect SEND enters at UNIT 0 (predates multi-unit routing).
  Evidence: src/mame/matsushita/kn7000.cpp:455, :1047, :1240.
- Update the overlay's ROM_START(kn2400) comment, which says the family 'DOES have a separate table/font ROM', while the merged upstream note (from the schematics) says there is none.
  Evidence: src/mame/matsushita/kn7000.cpp:2412-2413 'So this family DOES have a separate table/font ROM and it is UNDUMPED'.
- Rewrite wsa1.cpp's LIVE PARAMETER MIRROR comment: the rack refuses family 0x25, the keyboard sends tempo itself, and sub_FB57ED is now SysExRx_ApplyTempo.
  Evidence: src/mame/matsushita/wsa1.cpp:2877 'never emits on edit', :2889 'the real unit accepts', :2898 'sub_FB57ED'.
- Fix the overlay model years: kn6000 2000 -> 1999, kn2400 1998 -> 2003, kn2600 2000 -> 2003.
  Evidence: src/mame/matsushita/kn7000.cpp:2447 SYST(2000, kn6000), :2456 SYST(1998, kn2400), :2457 SYST(2000, kn2600); canon year-kn6000, year-kn2400-kn2600.
- Make tools/gen_lay.py reproduce the committed kn7000.lay (port the perf_pad tiles from 6b066f5), or mark kn7000.lay as hand-maintained, because running the generator would drop the curved pads.
  Evidence: `grep -c perf_pad tools/gen_lay.py` -> 0, src/mame/layout/kn7000.lay -> 12; gen_lay.py has 4 msp_ hits.
- Mark notes/panel-board-decode.md as superseded by notes/panel-bank-A-is-the-kn7000.md (17cee20), and fix that note's :12 'bank B is a sibling without SD', which contradicts its own conclusion.
  Evidence: panel-board-decode.md:8-10 still says flag value 1 = 'the KN7000 mode' and has no 'superseded' banner (grep).
- Update notes/sound-bank-classes.md, which still calls class 1 (0x57000000) the factory data flash and class 2 (0x56000000) the CUSTOM flash, although all four are EXP.CS expansion windows and the custom flash is at 0x96800000.
  Evidence: notes/sound-bank-classes.md:43-44.
- Correct kn_tonegen.h and notes/kn6000-tonegen-spec.md, which put the 20-byte TG-A write leg at 0x4C036F7C and the TgVoiceRegWrite entry at 0x4C036F6B, where kn7000_manual.sym:756 has TgVoiceRegWrite at 0x4C036F98 and the leg at 0x4C036FAB.
  Evidence: src/mame/matsushita/kn_tonegen.h:19; notes/kn6000-tonegen-spec.md:22, :31.
- Update notes/rom-provenance.md: the KN6000, KN6500 and KN2400 updates do ship .INF checksum oracles that match, and the 'never touches it at boot' read-tap claim is superseded by FINDINGS-kn2400-table-rom.md (164,300 reads).
  Evidence: notes/rom-provenance.md:115-118 'ship **no `.INF` checksum oracle**', :143-144 'a read-tap proved the firmware never touches it'.
- Update notes/mame-pr-rom-manifest.md. kn1500 has its own kn1500.cpp. Its BAD_DUMP is confirmed, not 'unvalidated'. IK2.SLD / IKV2.SLD are not table images.
  Evidence: notes/mame-pr-rom-manifest.md:14 'in kn5000.cpp', :15 'unvalidated', :41 'IK2.SLD (table)', :51 'IKV2.SLD (table)'.
- Settle IC311 DO3 in notes/dsp-audiopath-wiring.md §2.3 as DO3 -> HSO pin 62 -> HD-AE5000, as the kn5000-roms-disasm DSP roadmap and the site already do.
  Evidence: notes/dsp-audiopath-wiring.md:209-215 '### 2.3 DO3 — honest open item ... **OPEN.**'.
- Add a pointer in notes/rom-backup-and-update-format.md §2.2 to FINDINGS-updater-location-2026-08-09.md (the region is erased on real hardware).
  Evidence: `grep -c FINDINGS-updater-location notes/rom-backup-and-update-format.md` -> 0; §2.2 at :84-90.
- Correct 0x483E94D4-0x483FFFFF from 93,484 to 92,972 bytes in notes/FINDINGS-updater-location-2026-08-09.md.
  Evidence: FINDINGS-updater-location-2026-08-09.md:90 '(93,484 bytes)'; 0x400000 - 0x3E94D4 = 0x16B2C = 92,972.
- Fix 'same screen, three paths' above a two-row table in tools/dumpgrab/wip-real/r4-capture-side/README.md, either by restoring the third row or by saying 'two paths'.
  Evidence: tools/dumpgrab/wip-real/r4-capture-side/README.md:30.

## KN7000 (PR-planning tools)

- Following the 142655e revert, fix the 0x48407EFF reset address in the KN7000 driver-PR planning scripts.
  Evidence: KN7000 tools/mame-pr-planning/kn7000-driver-pr/drop_firmware_addresses.py:26 'KN7000 reset 0x48407EFF -> sets sp 0x4840FFFF'; degeneralise_mn10300.py:71 'jmp 0x48407EFF'.

## upstream MAME (next PRs)

- Correct the model years in upstream: kn5000 CONS(1998) -> 1997, kn2400 and kn2600 SYST(2000) -> 2003.
  Evidence: mamedev/mame master (fetched 2026-10-15) kn5000.cpp:784 CONS(1998, kn5000), kn7000.cpp:1323-1324 SYST(2000, kn2400) / SYST(2000, kn2600); canon upstream-year-metadata, year-kn2400-kn2600.
- Fix kn5000_cpanel.cpp's '32-entry table' (it has 33). Also correct the 0xD7 comment: the formula gives 0x77, which the ROM table maps to record 0x19, and bits 7:6 are encoder-ID bits.
  Evidence: master src/mame/matsushita/kn5000_cpanel.cpp:922 '32-entry table'; :561 'Header 0xD7 = 0xC0 (left panel) | 0x17 (encoder sub-address)'.
- Resolve kn7000.cpp's internal contradiction: the header says every block matches the shipped checksums, while the ROM_START comment excepts the sp7001 set.
  Evidence: master kn7000.cpp:45 'and every block matches.' versus :1083 'except the SP7001 set' and :1094-1095.
- Fix the hdae5000.cpp header, which says the board has 'a serial port to interface with a computer', when it is the uPD71055 parallel (DB-15) port.
  Evidence: master src/devices/bus/technics/kn5000/hdae5000.cpp:7 (same text in the kn7000_mame overlay :7).
- Re-examine the EI half of merged #14995, which rests on an uncheckable TMP94C241F datasheet section, while the TMP95C061F datasheet §3.3 says EI takes effect immediately on the 900/H core. *(not checked)*
  Evidence: No cheap check; the lane's datasheet extract is in round2/kn5000-mame/ds/tmp95c061.txt.
- If a Pico capture shows mainline's tg_map<0>=0x98040000 -> IC203/IC204 wave-ROM assignment is wrong, fix it upstream. *(not checked)*
  Evidence: Pending hardware capture (placeholder-wave-rom-spec.md:74-79).
- Revisit the KN7000 second MIDI port pair (mdin2/mdout2) if SIO channel 2 turns out to be the USB-MIDI path rather than a second DIN pair. *(not checked)*
  Evidence: master kn7000.cpp:912-915 declare mdout2/mdin2; the rear panel has one MIDI IN/OUT/THRU set (JK702-JK704) per the lane. The wiring was not checked.

## owner: hardware, emulator and archival work

- Dump the KN5000 v3 and v4 program boards that upstream lists as NO_DUMP.
  Evidence: master kn5000.cpp:723-724 'I have a v4 board but haven't dumped it yet' / 'I have a v3 board ...', :745-746 NO_DUMP.
- Consider adding HD-AE5000 v2.06i, the analysed and MAME-default version, to the archive.org item technics-kn5000-system-update-disks.
  Evidence: archive.org/metadata/technics-kn5000-system-update-disks lists v1.10i, v1.15i and v2.0i folders only. hdae5000.md:722 already says 'v2.06i is not in that item'. The unnamed hd_ae5000_disk/ and Misc/HD-AE5000.zip were checked by the lane's ia_hdae5000_versions.py, not re-run here.
- Verify on hardware or in the overlay what drives PE.0 low, because with PE.0 = 0 and region != 4 HDAE5000_Parport_Setup branches into flash reprogramming and never returns, before any page states that PE.0 = 0 means 'HD-AE5000 fitted'. *(not checked)*
  Evidence: hdae5000.md:84 and :823 now say PE.0 gates only the PPI set-up; the 0xEF4C03 path was not re-traced.
- Run MAME to settle whether MENU: DISK alone activates the App Loader, or whether the DISK MENU opens and the item is chosen, then make app-loader.md, playing-games.md and event-codes.md agree.
  Evidence: app-loader.md:436-439 ('Press MENU: DISK ... The App Loader menu should appear') versus playing-games.md:158-160 ('Navigate the DISK MENU').
- From the TMP94C241 datasheet, settle whether SCxMOD's SC1:SC0 = 00 (TO2 trigger) applies in I/O-interface mode, then make control-panel-protocol.md and the two serial pages agree.
  Evidence: control-panel-protocol.md:77 'Internal, derived from fc=16MHz' versus serial-firmware-compatibility.md:23, :124 'TO2 trigger (SC1MOD=0x00)' and serial-debugging-journey.md:44.
- Fetch the public TMP94C241 datasheet that cpu-subsystem.md:432 links into the project, to settle the unchecked datasheet citations on mame-pull-requests.md, the EI/RETI question, the MSAR/MAMR decode rule and the internal-RAM range. *(not checked)*
  Evidence: Not checked whether a copy is already archived locally.
- Check on the current overlay, after 3fd44f3 dropped the INT0 re-assertion, whether panel buttons still work, and if they do, say on subcpu-payload-loading.md that the February 2026 observation no longer holds. *(not checked)*
  Evidence: subcpu-payload-loading.md:569 'Failed first approach ... broke button input' is unchanged; `git -C kn7000_mame log -1 3fd44f3` exists. The emulator run was not done.
- In an emulator, check what the four test-pattern calls write to 0x130000, because DSP_Init_Channels / INIT_TONE_GEN pass the pattern in XWA and the channel in BC, while DSP_Write_Channel / TONE_GEN_WRITE take them in A and XBC; otherwise record it as a questions.md item. *(not checked)*
  Evidence: v142 kn5000_subprogram_v142.s:518-525 'Not checked on an emulator' (per the lane).

## kn5000-docs tools/ (outside the page lanes)

- Add kn7000_disassembly and kn7000_extraction to REPOS in tools/check_doc_paths.py, which today falsely reports 12 of 14 kn7000-roadmap.md paths and the image_extract.py / table_bitmaps.py / extract_idd7000.py citations as dead.
  Evidence: tools/check_doc_paths.py:42-49 REPOS lists only kn5000-docs, kn5000-roms-disasm, kn7000_mame, custom-kn5000-roms and Mines.
- Teach tools/check_doc_symbols.py to read kn7000_disassembly kn7000.sym and kn7000_manual.sym for kn7000-* pages (round2/kn7000-internals/kn7000_syms.py is a working prototype), because today all its hits on those pages are false.
  Evidence: `grep -n 'kn7000\|\.sym' tools/check_doc_symbols.py` -> no match.
- Correct the docstring of tools/check_doc_paths.py, which says 'no dump is committed to either repo', although kn5000-roms-disasm tracks original_ROMs/*.rom and *.ic*.
  Evidence: check_doc_paths.py:23; `git -C kn5000-roms-disasm ls-files original_ROMs | wc -l` -> 44 (including kn5000_subcpu_boot.ic30, hd-ae5000_v2_06i.ic4).

## owner decision: site policy and wording

- Decide on a one-time `tools/check_tables.py --all --fix` pass, because the round rules re-pad only edited tables and most older tables remain compact, including kn7000-control-panel.md's four.
  Evidence: `python3 tools/check_tables.py --all kn7000-control-panel.md` -> misaligned at :115, :144, :322, :388; over all non-generated pages -> 'tables checked: 1260; misaligned: 750' (115 files).
- Keep with a source or soften test-modes.md's statements that the KN5000 was designed and made in Hamamatsu, where Matsushita's instrument division was headquartered.
  Evidence: test-modes.md:449 'at the Hamamatsu factory', :470 'where the KN5000 was designed and manufactured'; no source cited.
- Decide whether the per-page '## Research Needed' checklists stay, given that open questions belong on questions.md and contributor work on help-wanted.md.
  Evidence: `grep -l 'Research Needed' *.md` -> 8 pages: accompaniment-engine, audio-subsystem, inter-cpu-protocol, midi-subsystem, sequencer, sound-categories, tone-generator, ui-framework (the lane counted 14).
- Decide whether pages keep revision notes, such as 'Eight of the entries in the previous revision of this table were stale', given that the site is not a changelog.
  Evidence: subcpu-command-format.md:287; also sysex-messages.md and sound-parameter-protocol.md per the lane.
- Decide whether to rename the dated permalinks of the two feature-demo state pages, which needs redirects and updated inbound links.
  Evidence: feature-demo-investigation-2026-03-09.md:3-4 and feature-demo-timer-bug-2026-03-09.md:3-4 (state titles, dated permalinks).
- Decide whether to fold kn7000-sd-plugin.md's dated 'Update, 2026-10-08' banner into the body, which now repeats its facts.
  Evidence: kn7000-sd-plugin.md:9 '> ### Update, 2026-10-08'.

## kn5000-roms-disasm: respell .byte lines the pinned llvm-mc can spell

- Respell the 27 KN5000 `.byte` lines commented 'the backend cannot spell this form' as slla/srla, and drop that comment from the 25 instruction lines that already assemble.
  Evidence: `git grep -h -i 'cannot spell' -- 'v10/*.s' 'v9/*.s' 'v7/*.s'` -> 25 instruction lines and 27 `.byte` lines (sll a,de/e/hl/l; srl a,bc/c). The pinned llvm-mc.snap (118bb4d6766e) encodes `slla de` = da fe, `srla bc` = d9 ff, `srla c` = cb ff, `slla e` = cd fe, `slla hl` = db fe, `slla l` = cf fe, which matches the .byte values. So #4's claim that the 27 are genuine is wrong.
- Respell the 12 v142 `.byte` lines (10 `minc1 ...,IX`, 2 ldc to DMA control registers) as minc1_16 / ldc_cr32 / ldc_cr16, update subcpu_data_tables.s:3438, and drop the stale 'no llvm-mc spelling' comment from the instruction lines that carry it.
  Evidence: v142/subcpu/kn5000_subprogram_v142.s:2538-2733 (10 minc1), :2977, :2979; `printf 'minc1_16 ix, 0xff\nldc_cr32 xhl, 8' | llvm-mc.snap -show-encoding` -> dc 38 ff 00 and eb 2e 08. The instruction lines are at :30136, :30148, :30204, :40264-40364. subcpu_data_tables.s:3438 '20 single instructions llvm-mc cannot spell'.
- Respell the 34 shift-by-A `.byte` sites (13 forms) in wsa1/prom_a as slaa/slla/srla, then re-quote the prom_a figures on raw-byte-code-elimination, rom-reconstruction, wsa1-disassembly and help-wanted.
  Evidence: `grep -c 'slla\|srla\|slaa' wsa1/prom_a/wsa1_prom_a.s` -> 0; raw-byte-code-elimination.md:62 already says the 34 sites reassemble byte-identically.
- Convert the prom_b `[llvm-mc cannot encode this]` rows that the shared macros or native spellings now cover (for example `rlc h, 2`, `srla w`, `bit 7, (xde+hl)`).
  Evidence: `grep -c 'llvm-mc cannot encode this' wsa1/prom_b/wsa1_prom_b.s` -> 70 (the lane counted 68 rows; notes/promb_macro_rewrite.py --census finds 9 convertible).

## kn5000-roms-disasm: symbol renames (the site follows under Symbol Name Synchronization)

- Rename SubCPU_Payload_Verify, SubCPU_Payload_GetErrorFlag, SubCPU_PayloadErrorStore and NMI_StorePayloadChecksums (for example WorkRam_VerifyPowerDownChecksums), because they checksum main-CPU work DRAM 0xF180/0xF980, not the sub-CPU payload, and the names produced the inverted v9/v10 story.
  Evidence: 18 uses in v10/maincpu/boot/system_handlers.s and kn5000_v10_program.s (`grep -c`); system_handlers.s:80-118.
- Rename SoundCtrl_SendCommand (for example Title_ShowInterrupt), which posts EVT_INTERRUPT_TITLE and sends nothing to a sound controller, and update test-modes.md:142.
  Evidence: v10/maincpu/ui/ui_control_panel.s:2923 header 'Send a command to the sound controller', :2931 label; test-modes.md:142 quotes it.
- Rename UI_PostModeChangeEvent (for example UI_PostTitleChangeEvent), which posts EVT_CHANGE_TITLE with TITLE_PS + A, and update test-modes.md.
  Evidence: v10/maincpu/ui/ui_control_panel.s:2907.
- Rename Boot_ClassifyDeviceID (for example Boot_CheckSpecialCombos) and Boot_ProbeExternalDevice (for example Boot_ScanPanelButtons), and fix their 'device class' comments, because they are the power-on button-combo check.
  Evidence: table_data/boot_cpserial.s:191, :509; kn5000_table_data.s:1549 'HL=device class'.
- Rename the Feature Demo symbols whose names encode the refuted SSF reading (GroupBoxProc_StartSSFPresentation, AcPresentCtrl_CheckSSFStart, DemoMenu_BuildItemWorkspace, Demo_WaitForDisplayBit, Demo_ParseSlideHeader), and name the 1056 transport counter in ram_variables.s.
  Evidence: `git grep -c` finds them in 6 v10 files (drawbar_panel_ui.s 25 uses).
- Rename ToneGen_FileIO_SaveAndSync and ToneGen_DiffScanAndUpdate, which copy song panel data into the live panel and diff-scan main-CPU RAM, and touch no tone generator.
  Evidence: v10/maincpu/audio/tonegen_fileio_handlers.s:880, :758.
- Swap the meanings of TitleFunc_LifecycleDispatch / TitleFunc_LifecycleTable and TitleFunc_ActionDispatch by renaming them, and write the TestTitleFunc pointer as `.long TestTitleFunc`. dispatch-tables.md row 26 follows.
  Evidence: v10/maincpu/factory_test/fd_test_data.s:334 `.byte 0x9a, 0xe3, 0xf1, 0x00`; label semantics per the lane (test_init.s:149, :188).
- Rename the Viewable_* method handlers after the methods they answer (for example Viewable_GetBoundsY -> MT_SetEditSwRect handler), then update ui-widget-types.md:96-107.
  Evidence: v10/maincpu/ui/ui_widget_defs.s:11390 Viewable_GetClass, :11432 Viewable_MatchClass, :11469 Viewable_GetBoundsX, :11504 Viewable_GetBoundsY.
- Replace the tentative NAKA_TYPE_* names in macros.s with the class names (for example NAKA_TYPE_DIAGLIST = PsNumEditBox), and update the superseded naka_types.h members and comments.
  Evidence: v10/maincpu/shared/macros.s:19-22 'NAKA_TYPE_DIAGLIST ... Diagnostic list item', 'NAKA_TYPE_PANEL ... Panel/dialog'.
- Rename the StyleGroup_* labels after the firmware's own group names (for example StyleGroup_ModernDance_Table holds 'Easy Listening'), move group 5's start to the separator, and drop StyleGroup_LatinDance_Table, which is not a group table.
  Evidence: v10/maincpu/ui_widgets/style_bitmaps.s:2846, :3372, :3534 (the group-name mapping was not re-checked).
- Rename FDC_SECTOR_COUNT (for example FDC_BYTE_COUNT), which is a byte count and is not 'incremented per sector', and update fdc-subsystem.md in the same change.
  Evidence: v10/maincpu/shared/ram_variables.s:77 '.equ FDC_SECTOR_COUNT, 0x8a1c ; cleared per command, incremented per sector'.
- Rename the HDAE5000_TableData_Write_* local labels inside HDAE5000_Init_BytecodeBlock, fix the comments that credit HDAE5000_TableData_Write with the flash programming, and correct the HDAE5000_Detect header (it reads table-data flash IDs).
  Evidence: 19 `HDAE5000_TableData_Write_` labels in v10/maincpu/boot/system_handlers.s; :8011-8012, :8134; HDAE5000_Detect header :6718-6721 'Detect presence of HDAE5000 expansion board'.
- Rename the sub-CPU boot TONE_GEN_* labels (or at least fix their headers), whose headers still say 'tone generator' while TONE_GEN_BASE says 0x130000 is not the tone generator.
  Evidence: subcpu/boot/kn5000_subcpu_boot.s:101 '⚠ MISNAMED', :810 TONE_GEN_CHANNEL_INIT 'Initialize tone generator channels', :971-972 WRITE_TONE_REG_MULTI_CHANNEL '... to tone generator'.
- Give 0x4FE one symbol in kn5000_subcpu_boot.s and use it in place of (1278:16), and correct its bit-7 comment: bit 7 is set when the DMA starts, not on 'transfer complete'.
  Evidence: subcpu/boot/kn5000_subcpu_boot.s:89 PAYLOAD_LOADED_FLAG and :319 SUBCPU_STATUS_FLAGS both 0x4FE ('Bit 7: transfer complete'); numeric `(1278:16)` at :775, :777, :1378, :1578, :1706.
- Rename CDlikeSwTtl_JumpToFA9D58 and FCopy_DispatchFA9D58, which embed an address, and fix ui_widget_defs.s's 'BroadcastEvent (FA9D58)' (0xFA9D58 is ApPostEvent).
  Evidence: v10/maincpu/ui/ui_widget_defs.s:18123; labels used in v10/maincpu/file_io/disk_operations.s and ui/ui_playback_modes.s (`git grep -c`).
- Rename CPanel_EncoderCheck and its 'Default encoder check mode' comment, which describe the segment-0x0B settle as an encoder check.
  Evidence: v10/maincpu/ui/cpanel_routines.s:21, :525-527.
- Drop or correct RHYTHM_PATTERN_SEL_A and RHYTHM_PATTERN_TYPE, which no instruction references, and the unsupported '1,024 bytes per pattern' on RHYTHM_PATTERN_BUF_A. Re-check the meanings of RHYTHM_VARIATION_INDEX and RHYTHM_PATTERN_SEL_B, which are referenced, contrary to the lane's claim.
  Evidence: v10/maincpu/shared/ram_variables.s:14-19. `git grep` finds no use of SEL_A/TYPE outside the .equ lines, but RHYTHM_VARIATION_INDEX is used at accompaniment_engine.s:8938 and sequencer_engine.s:4849, and RHYTHM_PATTERN_SEL_B at accompaniment_engine.s:10423.
- Optionally add EVT_ constants for the KN5000 event names that still have none: EV_INIT 0x03, EV_MOVE 0x04, EV_RESIZE 0x05, EV_RESET 0x10, EV_TIMER 0x12.
  Evidence: `grep -ic '1c00003\|1c00004\|1c00005\|1c00010\|1c00012' v10/maincpu/shared/event_codes.s` -> 0. The three AIC ones the lane listed now exist (event_codes.s:166 EVT_INDEXSW_UP_AIC, plus EVT_INDEXSW_DOWN_AIC and EVT_SW_IN_AIC).

## kn5000-roms-disasm: stale source comments (no rename)

- Correct the comments that tie the payload error flag to 'ERROR in CPU data transmission', which only SelfTest_SramAndRom_CheckROM posts after CPanel_ProbePanelMcus fails (v10, v9 and v7).
  Evidence: v10/maincpu/boot/system_handlers.s:89, :126, :2314 (same lines in v9; v7 :89, :126, :2269); v10/maincpu/kn5000_v10_program.s:1392.
- Fix the Boot_HandleFactoryReset header: 0x5AA5 at 0xFFCA is a reset-done marker, not 'payload checksums invalid'.
  Evidence: v10/maincpu/kn5000_v10_program.s:1619-1620 '(payload checksums invalid, e.g. after Flash ROM replacement)'.
- Fix the cpanel_routines.s comments (v10/v9/v7) that say combo 2 shows 'ALL INITIAL SETTING!'; it opens the MPVersion screen.
  Evidence: v10/maincpu/ui/cpanel_routines.s:380, :397 still say 'ALL INITIAL SETTING!'.
- Change 'words' to 'bytes' in the Checksum_ComputeComplement region comments (v10/v9/v7), because the routine counts bytes.
  Evidence: v10/maincpu/boot/system_handlers.s:43-44 '(0xf180, 0x800 words)', '(0xf980, 0x280 words)', :98 '; Size: 0x800 words'.
- Fix the SLIDE4K size comment in table_data, which says little-endian, when LZSS_Decompress reads it big-endian.
  Evidence: table_data/kn5000_table_data.s:4284 '=== Read expected decompressed size (3 bytes, little-endian) ==='.
- Reconcile boot_hw_init.s's 'Block 4 @ 0x800000 (Table Data)' with tmp94c241-memory-controller.md, which disputes it.
  Evidence: v10/maincpu/shared/boot_hw_init.s:89.
- Change 'extension DRAM (0x200000)' in test_init.s (v10/v9/v7) to HD-AE5000 SRAM.
  Evidence: v10/maincpu/factory_test/test_init.s:435, v9 :421, v7 :554; upstream hdae5000.cpp:65 'Static RAM @ IC5, IC6'.
- Fix the test_init.s stale blocks (v10/v9/v7). The TestTitleFunc header swaps EVT_SW_IN (0x1C00007, switch actions via 0xE1FDFE) and EVT_ACTIVATE_STATE (0x1C00013, phases via 0xE1FE0E). The InitializeHama header calls TT_HDDEXT an FDD/APR test.
  Evidence: v10/maincpu/factory_test/test_init.s:91 'Register HAMA (file/disk) subsystem', :123-125 '0x1c00007 (title lifecycle)'; the source itself admits the staleness at :147-148/:155-156.
- Correct 'Total bytes transferred = (byte1 & 0x0f) + 2' in cpanel_routines.s (v10/v9/v7) to nibble + 3, which is the origin of the questions.md error.
  Evidence: v10 and v9 maincpu/ui/cpanel_routines.s:1491, v7 :1380.
- Fix the stale SFR and handler comments in subcpu/boot/kn5000_subcpu_boot.s. INT_CTRL 0x10A is CLKMOD, and the WDMOD/WDCR 'legacy alias' notes are wrong (0x110/0x111 are WDMOD/WDCR). 'Initialize timer registers' covers MAMR/MSAR. T8RUN bit 2 is not a watchdog bit. Handlers 9/36 are INT0/INTTC0. '00-1F: Variable-length data packets' should be 'any other byte'.
  Evidence: kn5000_subcpu_boot.s:220-221, :266, :687, :862 ('Disable serial', unverified), :1539, :2827, :2883.
- Reword the sub-CPU boot ROM's '96KB of 0xFF (erased flash)' as assumed 0xFF, never dumped apart from 2 KB at each end.
  Evidence: subcpu/boot/kn5000_subcpu_boot.s:335; MAME ROM_LOAD comment 'Ranges fe0800-ff7800 and ff9800-fff000 not dumped yet'.
- Update the kn5000_subcpu_boot.s comments that still quote '`lds hl,0 / ret`' and '`lda_24 xbc,(0xff8000)`', which the source no longer spells that way.
  Evidence: subcpu/boot/kn5000_subcpu_boot.s:401, :403, :870.
- Fix the stale table_data and custom_data comments. Rhythm cells start at +0x1400. The banner 'Preset Data Banks' / '0xF7 (erased flash)' is wrong. 'sector gap' entries are section tails. 'SubCPU payload staging area' holds the compressed payload permanently. SndParam_CopyPreset is now SndParam_AllocAndCopyPreset. FLASH_SECTION_PTR_7 is the block slot store. WidgetStyleDataTable_0x2A8 is now EffectMode_PresetFieldMap.
  Evidence: table_data/kn5000_table_data.s:1023, :14-18, :77; custom_data/kn5000_custom_data.s:24-28, :281, :723, :1164, :19, :36, :1753, :1654; v10/maincpu/shared/ram_variables.s:73; table_data/style_records.s:84.
- Fix the table_data flash and FDC comments. The AM29F040/AM29LV800B names should be AM29F400BT/AM29F800BB. 'Wait for P3 bit 5' should be P7. The FDC_ReadSector, LZSS_ReadByte and LZSS_ParseHeader headers and the 0x0C28/0x0C34/0x0C38 labels are also wrong.
  Evidence: table_data/kn5000_table_data.s:86, :1831-1832 (9 AM29F040/AM29LV800B hits), :1788 and :2327 'Wait for P3 bit 5' on `bit 5, (P7:8)`; parts (c)-(f) not re-checked.
- Fix the AcFadeSetGridBoxProc header, which describes a 'dissolve' grid fade that its body never performs.
  Evidence: v10/maincpu/midi/ac_listener_handlers.s:502-503.
- Align the Keybed_Decode_Event header ('Calculate pitch value for voice') and the Keybed_Read_Event 'A23 multiplex' comment with the corrected notes beneath them.
  Evidence: v142/subcpu/kn5000_subprogram_v142.s:58264-58266, :58330.
- Fix the Voice_ModWheel_Apply header: '0x00 -> return' is wrong, because 0x00 falls through to the stereo path.
  Evidence: v142/subcpu/kn5000_subprogram_v142.s:21407.
- Remove the 'prevbank' wording from the v142 comments: QBC/QDE/QIZ are current-bank register codes.
  Evidence: `grep -c prevbank v142/subcpu/kn5000_subprogram_v142.s` -> 8.
- Align the SwbtWr_ReinitBothBanks / SwbtWr_ReinitOutputBank headers ('tone generator output banks') with widget_dispatch.s, where these are event-listener banks.
  Evidence: v10/maincpu/boot/system_handlers.s:1415-1418.
- Fix the first lines of the DSP_AlgoSelect header: the code multiplies the part, not the algorithm index, by 0x11F.
  Evidence: v142/subcpu/kn5000_subprogram_v142.s:34083 'Multiplies algo index by 0x11F'.
- Correct the four `div a,0xC` comments to note % 12 (pitch class), and fix ToneGen_Octave_Pitch_Table's 'indexed by note / 12'.
  Evidence: v142/subcpu/kn5000_subprogram_v142.s:43139-43140, :7993, :43207-43211; v142/subcpu/subcpu_data_tables.s:2680 'u16 indexed by note / 12 (the octave)'.
- Qualify the 'bit 7 never appears on a pair that is not its record's last' comment, which holds only after excluding each page's trailing zero words.
  Evidence: v142/subcpu/kn5000_subprogram_v142.s:8054-8058; probe round2/kn5000-tones/scripts/ic307_bit7_not_last.py.
- Fix the DSP_WriteParamWord header. It sends bits 23:16 then 15:8 of a 24-bit value, high byte first, not 'LOW byte first' of a 16-bit value, and it is called directly from 8 more sites.
  Evidence: v142/subcpu/kn5000_subprogram_v142.s:50423-50425.
- Fix the TOSHI header in extension_init.s, which calls it expansion-device registration; it registers the normal, control and OTP modes and others.
  Evidence: v10/maincpu/extensions/extension_init.s:2-6.
- Update the source comments that still carry the refuted March 2026 Feature Demo narrative ('CANNOT produce 0xb80a', 'ALWAYS fails', 'confirmed root cause', 0x02BC34 as a 'registration table' rather than the event queue).
  Evidence: v10/maincpu/ui/drawbar_panel_ui.s:17724, :17732, :18657; ui/ui_control_panel.s:3403; ui/ui_widget_defs.s:18125, :18171, :18179.
- Fix the v142 keybed comments. `lda xbc, (19020:16)` is the held-key map, not a 'Voice slot table'. '16 iterations (one per MIDI channel)' contradicts 'one per keybed scan group'.
  Evidence: v142/subcpu/kn5000_subprogram_v142.s:58172, :58493, :58496.
- Fix the MICRODMA_CH0_HANDLER header: state 4 is the end of E1 phase 2, not 'Process E3 command'.
  Evidence: v142/subcpu/kn5000_subprogram_v142.s:3248.
- Fix the MIDI_Dispatch header: the 0x80 class is the parameter query/action record that goes to Voice_ParamFinalize, not Note Off.
  Evidence: v142/subcpu/kn5000_subprogram_v142.s:42117 '0x80/0x90 = Note Off/On -> Voice_NoteOn'.
- Fix the ReverbPreset_Load / EQPreset_Load headers: they post SwbtWr events (codes 0x63/0x64) through AssswbWr, not 'via cmd 0x63 to the Sub CPU DSP ring buffer'.
  Evidence: v10/maincpu/audio/audio_control_engine.s:7775, :7805 (the extension_data.s wording was not found by grep).
- Fix the Voice_CC_SetDelayEnable header ('bit 0'), because the code sets bit 8.
  Evidence: v142/subcpu/kn5000_subprogram_v142.s:19039-19040.
- Determine whether VoiceSlot_SendErrorAndReset sends a stale A (it loads W = 0x68 but calls MIDI_SendSysExCmd, which reads A), and record it as a firmware bug or fix the call-target label.
  Evidence: v10/maincpu/demo/demo_seq_bridge.s:1131-1133 `ld w, 0x68:opc` / `call MIDI_SendSysExCmd`.
- Fix the AccompSeq_AdvancePosition header (v10/v9/v7). It advances the read offset 0x7E44 and the block word 0x7E42, not a tick and a beat counter.
  Evidence: v10/maincpu/sequencer/accompseq_routines.s:236-244 'Increments the tick counter (32324) ... beat counter (32322)'.
- Fix the fdc_routines.s header: the chip is a uPD72068, not a 'standard PC-compatible FDC', and the file spans 0xF96B13-0xF9800B.
  Evidence: v10/maincpu/storage/fdc_routines.s:6, :14 'Address range: 0xf96d54 - 0xf98009'.
- Change '14-byte request block' to 16 bytes, as the same file's 0x0C6E-0x0C7D layout shows.
  Evidence: table_data/boot_fdc_driver.s:33, :2151 versus :62; table_data/boot_disk_probe.s:42 'five 14-byte FDC request blocks'.
- Call 0x239CC4-0x239FD1 HD-AE5000 SRAM, not 'sub-CPU work RAM', and drop 'built at run time' for descriptors initialised from HDAE5000_WindowGeometry_Init.
  Evidence: hdae5000/hdae5000_data_tables.s:405, :9601.
- Complete the event_codes.s comments truncated with '...' (event-codes.md copies them verbatim), including EVT_GET_INSTANCE_SIZE_SP's 'as the existing comment says', and fix the MainLoop header address EF1248 to EF1245.
  Evidence: `grep -c '\.\.\.$' v10/maincpu/shared/event_codes.s` -> 1412; event_codes.s:10; system_handlers.s:1076 '(EF1248)' versus symbols/maincpu_v10_symbols_reference.txt:15961 'MainLoop 00EF1245'.
- Drop the stale 'they stay sub_XXXXXX' line from the WSA1 Disk_CommandDispatch header, since 6fa2ba900 named the handlers DiskCmd_*.
  Evidence: wsa1/prom_a/wsa1_prom_a.s:169908 'NOT established: the semantics of the individual command handlers -- they stay'.
- Change prom_b's 'the other 11 ids' to 10 (0x60, 0x78-0x7A, 0x80, 0x91-0x93, 0x98, 0x99), and note that 0x98 and 0x7A are now decoded (94f697933).
  Evidence: wsa1/prom_b/wsa1_prom_b.s:88698 'What the other 11 ids hold is'.

## kn7000_disassembly (unpublished)

- Update notes/sd-plugin-interface.md and kn7000_manual.sym to name the SP7001 release (program 942 / table 83, MAME BIOS sp7001) instead of the unpreserved 'Update V2.0', and stop calling 0x4C000000 an 'undumped library ROM'.
  Evidence: notes/sd-plugin-interface.md:11, :46; kn7000_manual.sym:2468.
- Give 0x4852B6B0 (the tag/extension matcher) a symbol in kn7000_manual.sym, because kn7000-sd-plugin.md calls it 'the disk-file dispatcher' while kn7000.sym names DiskLoadDispatch 0x4852CFE4.
  Evidence: `grep -i '^0x4852B6B0' kn7000_manual.sym kn7000.sym` -> none (it appears only in the comment at kn7000_manual.sym:2471); kn7000-sd-plugin.md:104.
- Add SetLedByIndex (0x484B1BCB) and its OFF entry 0x484B1CA1 to kn7000_manual.sym, because the site already uses the name.
  Evidence: src/program.s:405 `.equ func_484B1BCB`; no symbol in kn7000_manual.sym/kn7000.sym; kn7000-control-panel.md:280 'SetLedByIndex (0x484B1BCB ...)'.
- Correct the StyleGenreTable comment (the sub-table entries carry subcategory headings, not 'REAL style name'), name the 17-byte name list at 0x485D1038, and give StyleRecordTable its 1,080 records instead of '>=400'.
  Evidence: kn7000_manual.sym:303 ('REAL style name'), :261 ('>=400 24-byte built-in style records'); no symbol at 0x485D1038.

## kn7000_extraction (unpublished)

- Update FORMAT.md and extract_idd7000.py: the AST is zlib-coded, not Huffman/LZH (ca2e41b), and the custom flash is read at 0x96800000, not 0x56020000.
  Evidence: FORMAT.md:243-247 'ENTROPY-CODED (Huffman/LZH-', '0x56020000'; extract_idd7000.py:15, :102, :166 '0x56020000'.
- Fix README.md, which says 9 JPEGs where image_extract.py's catalog lists 8, and which names panel sub-CPUs CPL/CPC/CPR/CPSD when only CPL and CPR carry a microcomputer.
  Evidence: README.md:91 'embeds 9 JPEGs', :99 'CPL/CPC/CPR/CPSD'.
- Fix name_extract_nul.py's header: IK2/IKV2 are the upper half of the program flash, not a table ROM, and IC13/IC14 were never dumped.
  Evidence: name_extract_nul.py:4-5 'a KN6000/KN6500 TABLE ROM (the decompressed IK2.SLD / IKV2.SLD image)'.
- Decide whether style_names.py should walk StyleGenreTable/StyleRecordTable instead of heuristically scanning 0x1CF000-0x1D6000. Its 931 names mix headings, 725 of the 1,080 styles and the genre names, and changing it would change a published list. *(not checked)*
  Evidence: The owner's call; the 1,080 figure is produced by kn5000-docs tools/kn7000_style_catalog.py (d886484).

## Mines and the App Loader (custom-kn5000-roms)

- Rename DISP_DISABLE_FLAG (0x0D53 bit 3), or correct its comment, in Mines and the App Loader, because the site has retracted the display-disable reading (bit 3 is set only on the step-record screen).
  Evidence: Mines platforms/kn5000/startup.s:16 '.equ DISP_DISABLE_FLAG, 0x0D53 ; Bit 3: disable firmware display updates'; custom-kn5000-roms apploader/startup.s:16, apploader/src/kn5000.h:95.
- Make the hard-coded LD_LIBRARY_PATH=/tmp/qt5libs/... in the MAME test targets an overridable variable, or drop it.
  Evidence: Mines platforms/kn5000/Makefile:209; custom-kn5000-roms apploader/Makefile:171, :183.

## review harness (round2/canon.json)

- Correct canon entry 'sp7001-firmware-found' before a later round relies on it: program 942 carries PLUGIN API and XAPR, and the SP700 strings are only in table 83.
  Evidence: canon.json sp7001-firmware-found statement still says 'It contains the PLUG/SP700 strings that build 941 lacks'.

## Already resolved during the review

- No action: the producers of the payload pairing, raw-byte counts, style groups, KN7000 1,080-style figures and cross-model figures were already committed to kn5000-docs tools/, and kn2400-kn2600.md no longer quotes the irreproducible 38.9 % / 74.3 %.
- Approve the reworded About sentence, which speaks in the owner's voice; it no longer claims that all content is hardware-verified.
- No action: the swbwr-tone-init.md retitle was applied together with its nav entry and its link text.
