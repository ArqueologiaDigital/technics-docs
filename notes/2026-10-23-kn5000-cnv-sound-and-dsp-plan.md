# Follow-ups: the KN5000 style converter, its sound, the DSP research plan (2026-10-23)

Pages added: `kn5000-cnv-homebrew.md`, `kn5000-dsp-sample-playback-research.md`. Updated: `another-world-vm.md`,
`inter-cpu-protocol.md` (records a converter can send, the part map), `mame-emulation-gaps.md`, `roadmap.md`.
Later the same day: the research plan's second pass (a sub-CPU-fed mixer on IC311, playing the game in MAME).

## Owner actions (need the instrument)

- Run `AW.CNV` on a real KN5000 when it is back: start, controls, the keybed, EXIT; whether the voices sound
  as chosen, and retune `technics-anotherworld kn5000cnv/tools/aw_sound_map5.py` (it was picked among the voices
  MAME plays; the instrument plays them all).
- Research plan Q4 (delay-address width) and Q7 (which IC311 return is heard) need the unit.
- The DSP sound (`make DSND=1`): run it on the unit. Whether the mixer is heard at all is the test of the
  MAME core's model (the per-unit CALL, its D-RAM rebase, the output level in D-RAM 0x06); then whether
  leaving the game brings the instrument's effects back.

## Desk work

- Research plan Q1-Q3, Q8 first (no hardware): the modulation offset (`lo12 0x44C`) range and precision,
  whether write words can use it, a DSP-kept frame counter.
- Q6, done: the running sub program accepts E1 writes into its DRAM, and its RAM trampolines can be pointed
  at code of ours (whether `0x2D` uploads a replaced stream was not needed and is not tested).
- The DSP sound: a tick rate above 4000 Hz (how much of the sub CPU the streamer takes is not measured); a
  faster part load (8 s for the intro's sounds, most of it the firmware's floppy reads).
- MAME: an organ's note (Chapel Organ) does not end after its note-off; not looked into.
- MAME, done for programs of ours: the IC311 build mixes DO1/DO2 (Q9). The firmware's own effects are still
  not heard, the presentation words being undecoded (`UPD6383_PRESENT_ASIS` only for programs that make
  their arithmetic not matter).
- The site has 10 dead page links that predate this change (`tools/check_links.py`); not touched here.
