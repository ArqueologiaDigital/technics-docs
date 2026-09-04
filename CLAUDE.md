# CLAUDE.md — KN5000 Documentation Website

## Overview

Jekyll-based documentation website for the KN5000 reverse engineering project. Build: `bundle exec jekyll serve`.

## Issue Tracker

There is **no automated issue tracker**. Beads was decommissioned on 2026-07-27 at the owner's request; do not run `bd` and do not reinstall it. The 694 archived issues are at `/home/fsanches/compartilhado/beads-decommission-2026-07-27/` (`readable/` for Markdown, `exports/` for JSON) as a historical record; do not republish them on the site.

There is no `issues.md` page and there should not be one. A dump of a tracker is a changelog, and the site is not a changelog. Open work belongs on the page that owns the subject: unanswered technical questions on `questions.md`, contributor-actionable work on `help-wanted.md`, programme planning on `roadmap.md`, emulator shortfalls on `mame-emulation-gaps.md`, upstreaming state on `mame-branch-review.md`.

**After meaningful work, agents MUST:** record follow-ups in this repository's own Markdown notes so the next session can pick them up.

## Policies

- **Keep in sync** with reverse engineering discoveries across all subprojects (see Documentation Freshness policy in central CLAUDE.md).
- **Symbol names in docs must match assembly source** (see Symbol Name Synchronization policy in roms-disasm CLAUDE.md).
