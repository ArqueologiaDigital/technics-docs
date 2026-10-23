# Follow-ups: the KN5000 style converter, its sound, the DSP research plan (2026-10-23)

Pages added: `kn5000-cnv-homebrew.md`, `kn5000-dsp-sample-playback-research.md`. Updated: `another-world-vm.md`,
`inter-cpu-protocol.md` (records a converter can send, the part map), `mame-emulation-gaps.md`, `roadmap.md`.

## Owner actions (need the instrument)

- Run `AW.CNV` on a real KN5000 when it is back: start, controls, the keybed, EXIT; whether the voices sound
  as chosen, and retune `technics-anotherworld kn5000cnv/tools/aw_sound_map5.py` (it was picked among the voices
  MAME plays; the instrument plays them all).
- Research plan Q4 (delay-address width) and Q7 (which IC311 return is heard) need the unit.

## Desk work

- Research plan Q1-Q3, Q8 first (no hardware): the modulation offset (`lo12 0x44C`) range and precision,
  whether write words can use it, a DSP-kept frame counter.
- Q6: does the running sub-CPU program accept E1 writes into its DRAM, and does `0x2D` upload a replaced stream?
- MAME: an organ's note (Chapel Organ) does not end after its note-off; not looked into.
- MAME: IC311's return into IC303 is not mixed (research plan Q9).
- The site has 10 dead page links that predate this change (`tools/check_links.py`); not touched here.
