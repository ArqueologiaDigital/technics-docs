# CLAUDE.md — KN5000 Documentation Website

## Overview

Jekyll-based documentation website for the KN5000 reverse engineering project. Build: `bundle exec jekyll serve`.

## Issue Tracker

There is **no automated issue tracker**. Beads was decommissioned on 2026-07-27 at the owner's request; do not run `bd` and do not reinstall it. The 694 archived issues are at `/home/fsanches/compartilhado/beads-decommission-2026-07-27/` (`readable/` for Markdown, `exports/` for JSON) as a historical record; do not republish them on the site.

There is no `issues.md` page and there should not be one. A dump of a tracker is a changelog, and the site is not a changelog. Open work belongs on the page that owns the subject: unanswered technical questions on `questions.md`, contributor-actionable work on `help-wanted.md`, programme planning on `roadmap.md`, emulator shortfalls on `mame-emulation-gaps.md`, upstreaming state on `mame-branch-review.md`.

**After meaningful work, agents MUST:** record follow-ups in this repository's own Markdown notes so the next session can pick them up.

## Sidebar menu

The menu is `_data/navigation.yml`, rendered by `_includes/sidebar.html` and the recursive
`_includes/nav-items.html`. It has one root entry for the project as a whole (Introduction) and
**one root entry per model**, ordered by release year, newest first (the `released:` key). A
model with many pages groups them one level down (`children:`), as the KN5000 entry does; never
add a second root entry for the same model. Pages about several models go under Introduction.
Every new page gets a menu entry unless an index page links to it (`flowcharts/`, `effect-impl/`).
Check with `python3 tools/check_nav.py` (dead entries, duplicates, order, unlisted pages).

## Checks

- `python3 tools/check_tables.py <pages>`: every table touched since HEAD has aligned,
  space-padded columns (`--all` checks every table on the page, `--fix` re-pads).
- `python3 tools/check_links.py <built site>`: dead internal links and `#anchors` in a local
  build (`JEKYLL_NO_BUNDLER_REQUIRE=true jekyll build -s . -d ~/compartilhado/tmp/<dir>`).
- `python3 tools/check_doc_symbols.py <pages>`: symbol names that no longer exist in the
  disassembly.

## Policies

- **Keep in sync** with reverse engineering discoveries across all subprojects (see Documentation Freshness policy in central CLAUDE.md).
- **Symbol names in docs must match assembly source** (see Symbol Name Synchronization policy in roms-disasm CLAUDE.md).
