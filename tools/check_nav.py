#!/usr/bin/env python3
"""check_nav.py -- does the sidebar menu (_data/navigation.yml) match the site's pages?

QUESTION ANSWERED
  The sidebar is hand-written YAML, so it drifts from the pages it lists.
  This checks four things, and exits non-zero if any of the first three fail:

    1. DEAD ENTRIES.  Every `url:` in the menu is the permalink of a page.
    2. DUPLICATES.    No URL appears in the menu twice.
    3. ORDER.         Model sections (those with a `released:` year) are ordered
                      newest first, as the comment at the top of the YAML says.
    4. UNLISTED PAGES (report only).  Pages that are not in the menu, split into
                      those another page links to and those NOTHING links to.
                      An unlisted page can be deliberate (the per-effect pages
                      under effect-impl/ hang off their index page); a page that
                      nothing links to is reachable only by typing its URL.

  "Linked" means some other page contains `{{ site.baseurl }}/<permalink>`, the
  form every page on this site uses.  Links are not followed transitively.

  A page's URL is its `permalink:` front matter.  A page without one gets
  Jekyll's default, `/<path>/<name>.html` (index.md becomes `/`).

RUN
  python3 tools/check_nav.py            # from the repository root
  python3 tools/check_nav.py --tree     # also print the menu as an indented tree
"""

import argparse
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "_site", "vendor", "technics-docs", "_includes", "_layouts",
             "_data", "tools", "node_modules", ".jekyll-cache", ".sass-cache"}
SKIP_FILES = {"CLAUDE.md", "README.md"}
FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
LINK = re.compile(r"\{\{\s*site\.baseurl\s*\}\}(/[^\s)\"'#?]*)")


def pages():
    """Map URL -> source path for every page that has front matter."""
    found = {}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if not name.endswith((".md", ".html")) or name in SKIP_FILES:
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
            m = FRONT_MATTER.match(text)
            if not m:
                continue  # no front matter: Jekyll copies it as a static file
            meta = yaml.safe_load(m.group(1)) or {}
            rel = os.path.relpath(path, ROOT)
            url = meta.get("permalink")
            if not url:
                stem = os.path.splitext(rel)[0]
                url = "/" if stem == "index" else "/" + stem + ".html"
                if stem.endswith("/index"):
                    url = "/" + stem[: -len("index")]
            found[url] = (rel, text)
    return found


def walk(items, depth, out, trail):
    for item in items or []:
        here = trail + [item.get("title", "?")]
        if "url" in item:
            out.append((item["url"], here, depth))
        if "children" in item:
            out.append((None, here, depth))
            walk(item["children"], depth + 1, out, here)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--tree", action="store_true", help="print the menu as a tree")
    args = ap.parse_args()

    with open(os.path.join(ROOT, "_data", "navigation.yml"), encoding="utf-8") as f:
        nav = yaml.safe_load(f)
    site = pages()

    entries = []
    for section in nav:
        entries.append((None, [section["title"]], 0))
        walk(section.get("pages"), 1, entries, [section["title"]])

    if args.tree:
        for url, trail, depth in entries:
            print("  " * depth + trail[-1] + (f"  {url}" if url else ""))
        print()

    failed = False
    listed = [(url, trail) for url, trail, _ in entries if url]

    dead = [(u, t) for u, t in listed if u not in site]
    print(f"menu entries: {len(listed)}; dead: {len(dead)}")
    for url, trail in dead:
        print(f"  DEAD  {url}  ({' > '.join(trail)})")
    failed |= bool(dead)

    seen, dups = {}, []
    for url, trail in listed:
        if url in seen:
            dups.append((url, seen[url], trail))
        seen.setdefault(url, trail)
    print(f"duplicate menu URLs: {len(dups)}")
    for url, first, again in dups:
        print(f"  DUP   {url}  ({' > '.join(first)}  and  {' > '.join(again)})")
    failed |= bool(dups)

    models = [(s["title"], s["released"]) for s in nav if "released" in s]
    years = [y for _, y in models]
    in_order = years == sorted(years, reverse=True)
    print(f"model sections: {len(models)}; newest first: {'yes' if in_order else 'NO'}")
    for title, year in models:
        print(f"  {year}  {title}")
    failed |= not in_order

    linked = set()
    for url, (_, text) in site.items():
        for target in LINK.findall(text):
            target = target if target.endswith(("/", ".html")) else target + "/"
            if target != url:
                linked.add(target)
    unlisted = sorted(u for u in site if u not in seen)
    orphans = [u for u in unlisted if u not in linked]
    print(f"pages: {len(site)}; not in the menu: {len(unlisted)} "
          f"({len(unlisted) - len(orphans)} linked from another page, "
          f"{len(orphans)} linked from nowhere)")
    # Pages in a subdirectory (flowcharts/, effect-impl/) hang off an index page by
    # design, so the linked ones are counted per directory instead of listed.
    per_dir = {}
    for url in unlisted:
        rel = site[url][0]
        if url in orphans or os.sep not in rel:
            tag = "UNLINKED" if url in orphans else "linked  "
            print(f"  {tag}  {url}  ({rel})")
        else:
            per_dir[rel.split(os.sep)[0]] = per_dir.get(rel.split(os.sep)[0], 0) + 1
    for d, n in sorted(per_dir.items()):
        print(f"  linked    {n} pages under {d}/")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
