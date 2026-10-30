---
layout: page
title: KN7000 Sound GUI Map
permalink: /kn7000-sound-gui-map/
---

# KN7000 Sound GUI Map

How the KN7000's sound-related screens connect. Each node is a display; each edge
is the panel button, on-screen soft button, or menu item that opens it. This is
the navigation companion to the [Sound Subsystem]({{ site.baseurl }}/kn7000-sound-subsystem/) and
[Effects DSP]({{ site.baseurl }}/kn7000-effects-dsp/) hardware pages — it maps what the player
touches to the hardware those pages describe. Screen names and paths are from the
user's manual (2002). The firmware's own view of the same screens, every widget of every
block as the program's data defines it, is the generated
[KN7000 Menu Map]({{ site.baseurl }}/kn7000-menu-map/) (blocks SOUND, SNDRHY, SOUNDEDIT and EFF).

Two ways in dominate: the **panel buttons** (a SOUND-GROUP or effect button,
often *press &amp; hold* to open its editor) and the **PROGRAM MENUS** hub (which
branches into the SOUND, REVERB &amp; EFFECT, and SOUND EDIT menu trees).

<pre class="mermaid">
flowchart TD
    HOME["HOME PAGE<br/>sounds R1/R2/LEFT + part volumes"]

    %% --- direct panel-button sound screens ---
    HOME -->|SOUND GROUP button| SEL["SOUND select<br/>(per part, 1236 sounds)"]
    HOME -->|SOUND EXPLORER| EXPL["SOUND EXPLORER<br/>category/alphabet browser"]
    HOME -->|DIGITAL DRAWBAR| DRAW["DIGITAL DRAWBAR<br/>9 drawbars + rotary"]
    HOME -->|TAB ORGAN| TABS["TAB ORGAN<br/>USA/European/Theatre"]
    HOME -->|ACCORDION REGISTER| ACC["ACCORDION REGISTER"]
    HOME -->|hold TECHNI-CHORD| TC["TECHNI-CHORD<br/>harmony styles"]

    %% --- part effects ---
    HOME -->|hold SOUND DSP| SDSP["SOUND DSP<br/>Tremolo/AutoPan/Vibrato/<br/>RingMod/Mixup/ParamEQ/<br/>LFOFilter/Enhancer"]
    SDSP -->|EDIT| SDSPE["EFFECT EDIT<br/>per-parameter table"]

    %% --- global effects ---
    HOME -->|hold REVERB| RV["REVERB<br/>Room/Plate/Concert/Dark"]
    HOME -->|hold CHORUS| CH["CHORUS 1-4"]
    HOME -->|hold MULTI| MU["MULTI EFFECT<br/>Overdrive/Fuzz/AmpSim/<br/>Limiter/Compressor/Delay..."]
    HOME -->|hold MIC| MIC["MIC REVERB &amp; EFFECT<br/>+ harmony"]
    RV -->|DETAIL EDIT| EDET["effect DETAIL EDIT<br/>+ EFFECT MEMORY"]
    CH -->|DETAIL EDIT| EDET
    MU -->|DETAIL EDIT| EDET

    %% --- APC / Chord Finder ---
    HOME -->|APC MODE| APC["APC SELECT<br/>BASIC/FINGERED/PIANIST"]
    APC -->|CHORD FINDER| CF["CHORD FINDER<br/>ear button = sound the chord"]

    %% --- PROGRAM MENUS hub ---
    HOME -->|PROGRAM MENUS| PM["PROGRAM MENUS"]
    PM --> SM["SOUND MENU"]
    PM --> RM["REVERB &amp; EFFECT MENU"]
    PM --> EM["SOUND EDIT MENU"]

    SM --> PS["PART SETTING<br/>5 pages: vol/pan/EQ/env/mode"]
    SM --> MX["MIXER<br/>all parts, 5 pages"]
    SM --> MT["MASTER TUNING"]
    SM --> KS["KEY SCALING<br/>+ temperament templates"]
    SM --> TC
    SM --> MON["MONITOR / SEPARATE / APC REVERB"]

    RM --> RV
    RM --> CH
    RM --> MU
    RM --> SDSP
    RM --> MIC
    RM --> EQ["EQUALIZER<br/>5-band final bus"]
    RM --> ALLOC["ALLOCATION<br/>DSP4/5 -> APC or SEQ"]

    EM --> TONE["TONE EDIT (4 tones)"]
    EM --> PITCH["PITCH EDIT"]
    EM --> FILT["FILTER EDIT"]
    EM --> AMP["AMPLITUDE EDIT"]
    EM --> LFO["LFO EDIT (12 LFOs)"]
    EM --> FX["EFFECT EDIT"]
    EM --> CTRL["CONTROLLER EDIT"]
    EM --> WR["WRITE -> 40 sound memories"]
</pre>

## Where each screen meets the hardware

- **SOUND / SOUND EXPLORER / DIGITAL DRAWBAR / TAB ORGAN / ACCORDION** choose a
  patch for a part — they program the [tone generators]({{ site.baseurl }}/kn7000-sound-subsystem/)
  (which voice, pitch, level) and load the patch's default effects.
- **SOUND DSP / REVERB / CHORUS / MULTI / MIC / EQUALIZER** all drive the
  [effects DSP]({{ site.baseurl }}/kn7000-effects-dsp/): selecting a type downloads that effect's
  SHARC microprogram into the corresponding effect unit, and the parameter tables
  adjust its coefficients. The unit map is fixed-function:

  | Unit | Role | | Unit | Role |
  |---|---|---|---|---|
  | u0 | **REVERB** | | u7 | **MIC REVERB** |
  | u1 | **MULTI** | | u8 | **EQUALIZER** |
  | u2–u6 | per-part Sound-DSP / Digital-Effect insert pool | | u9 | **CHORUS** |
- **CHORD FINDER** is reached from the APC screen; which LCD soft-key opens it is
  not yet confirmed. Its ear button sounds the displayed chord without the rhythm
  engine — a clean, repeatable note trigger useful for probing the note path.
- **SOUND EDIT** reaches inside a patch (up to four tones, envelopes, filters,
  LFOs), i.e. the deepest tone-generator parameter surface.

> This map covers the sound cluster. A full whole-instrument screen map
> (sequencer, composer, disk, SD, MIDI, customize) is a larger, separate effort.
