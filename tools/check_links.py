#!/usr/bin/env python3
"""check_links.py -- do the site's internal links and #anchors resolve in the BUILT site?

QUESTION ANSWERED
  Pages link to each other as `{{ site.baseurl }}/page/#anchor`.  When a page is
  renamed or a heading is reworded, the links into it break silently: GitHub Pages
  serves a 404 for a missing page and simply ignores a missing anchor.  This reads
  every HTML file of a built site and checks every href that stays on the site:

    DEAD PAGE    the target file does not exist in the build;
    DEAD ANCHOR  the target exists but has no element with that id (kramdown
                 gives every heading an id, so a reworded heading breaks links).

  Links to other hosts, mailto: and javascript: are skipped.  Relative links
  (no leading slash) are resolved against the linking page, as a browser would.
  A relative link to `some-page.md` is resolved to that page's permalink, as
  GitHub Pages' jekyll-relative-links plugin does when it builds the site (a
  plain local Jekyll leaves such links as they are).  Exits non-zero if anything
  is dead.

  It checks the HTML that Jekyll produced, not the Markdown, so Liquid and
  kramdown have already done their work and the result is what a reader gets.

RUN
  JEKYLL_NO_BUNDLER_REQUIRE=true jekyll build -s . -d ~/compartilhado/tmp/site
  python3 tools/check_links.py ~/compartilhado/tmp/site
  python3 tools/check_links.py SITE --baseurl /technics-docs   # the default
"""

import argparse
import html.parser
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_nav import pages  # noqa: E402  (URL -> source path of every page)


class Collector(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.hrefs = set(), []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for key in ("id", "name"):
            if a.get(key):
                self.ids.add(a[key])
        if tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("site", help="the built site directory (jekyll -d)")
    ap.add_argument("--baseurl", default="/technics-docs")
    args = ap.parse_args()
    site = os.path.abspath(args.site)
    base = args.baseurl.rstrip("/")

    # basename of every page's source -> its URL, for `.md` links (unique names only)
    by_name = {}
    for url, (rel, _) in pages().items():
        by_name.setdefault(os.path.basename(rel), []).append(url)
    md_url = {name: urls[0] for name, urls in by_name.items() if len(urls) == 1}

    parsed = {}
    for dirpath, _, files in os.walk(site):
        for name in files:
            if name.endswith(".html"):
                path = os.path.join(dirpath, name)
                c = Collector()
                with open(path, encoding="utf-8", errors="replace") as f:
                    c.feed(f.read())
                parsed[path] = c

    def target_file(url_path):
        p = os.path.normpath(os.path.join(site, url_path.lstrip("/")))
        if os.path.isdir(p):
            p = os.path.join(p, "index.html")
        return p

    dead_pages, dead_anchors, checked = [], [], 0
    for path, c in sorted(parsed.items()):
        page_url = "/" + os.path.relpath(path, site).replace(os.sep, "/")
        for href in c.hrefs:
            u = urllib.parse.urlsplit(href)
            if u.scheme or u.netloc or href.startswith(("mailto:", "javascript:")):
                continue
            if not u.path:          # same-page anchor
                target = path
            else:
                if u.path.startswith("/"):
                    if not (u.path == base or u.path.startswith(base + "/")):
                        dead_pages.append((page_url, href, "outside baseurl"))
                        continue
                    rel = u.path[len(base):]
                elif u.path.endswith(".md") and os.path.basename(u.path) in md_url:
                    rel = md_url[os.path.basename(u.path)]
                else:
                    rel = urllib.parse.urljoin(page_url, u.path)
                target = target_file(urllib.parse.unquote(rel))
            checked += 1
            if not os.path.exists(target):
                dead_pages.append((page_url, href, "no such file"))
                continue
            frag = urllib.parse.unquote(u.fragment)
            if frag and target in parsed and frag not in parsed[target].ids:
                dead_anchors.append((page_url, href))

    print(f"html files: {len(parsed)}; internal links checked: {checked}")
    print(f"dead page links: {len(dead_pages)}")
    for src, href, why in dead_pages:
        print(f"  {src}\t{href}\t({why})")
    print(f"dead anchors: {len(dead_anchors)}")
    for src, href in dead_anchors:
        print(f"  {src}\t{href}")
    return 1 if dead_pages or dead_anchors else 0


if __name__ == "__main__":
    sys.exit(main())
