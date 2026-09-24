#!/usr/bin/env python3
"""Sync the KN5000 DSP signal-flow flowcharts onto the Jekyll docs site.

READS the GENERATED Mermaid charts from the sibling disassembly repo
(kn5000-roms-disasm/dsp/flowcharts/*.md) and EMITS Jekyll pages under
technics-docs/flowcharts/, so future flowchart regenerations flow to the site
with one command (`make flowcharts`).

This is a CONSUMER of that source tree: it never edits the charts, it only
transforms them. For each source chart it:

  * adds Jekyll front matter (layout: page; title from the `# ...` heading;
    a stable permalink /effects-dsp/flowcharts/<name>/, kernel -> .../kernel/),
  * keeps every ```mermaid block verbatim (they render client-side on the site),
  * rewrites the source's repo-relative links so they resolve on the site:
      - chart -> chart links (kernel.md, prog05_phaser.md) -> the site permalink,
      - README.md (the source index) -> the site flowcharts index,
      - links into the disasm repo (../disasm/..., ../instruction-set.md,
        ../README.md, ../tools/..., ../algorithms/...) -> the GitHub blob/tree
        URL of that file, so they open real, viewable files instead of 404ing.

README.md becomes the site index page at /effects-dsp/flowcharts/.

The output is DETERMINISTIC / idempotent: re-running produces byte-identical
files, and stale generated pages (charts dropped upstream) are pruned.
"""

import argparse
import html
import re
import subprocess
import sys
from pathlib import Path

# --- output layout on the site -------------------------------------------------
SITE_SUBDIR = "flowcharts"                      # technics-docs/flowcharts/
PERMALINK_BASE = "/effects-dsp/flowcharts"      # + /<name>/  (index = base + /)
GENERATED_MARKER = "SYNCED from kn5000-roms-disasm"

# Links written into the emitted pages use {{ site.baseurl }} so they resolve
# under the site's baseurl (/technics-docs) exactly like the hand-written pages do.
SITE_INDEX_LINK = "{{ site.baseurl }}" + PERMALINK_BASE + "/"


def chart_permalink(name: str) -> str:
    """Site permalink for a chart file basename (without .md)."""
    return f"{PERMALINK_BASE}/{name}/"


def git_remote_slug(repo: Path) -> str:
    """owner/repo parsed from the disasm repo's origin remote."""
    url = subprocess.check_output(
        ["git", "-C", str(repo), "remote", "get-url", "origin"],
        text=True,
    ).strip()
    # https://github.com/OWNER/REPO.git  or  git@github.com:OWNER/REPO.git
    m = re.search(r"[:/]([^/:]+/[^/:]+?)(?:\.git)?$", url)
    if not m:
        raise SystemExit(f"cannot parse owner/repo from origin url: {url!r}")
    return m.group(1)


def git_default_branch(repo: Path) -> str:
    """Default branch of the disasm repo (origin/HEAD, else current, else main)."""
    try:
        ref = subprocess.check_output(
            ["git", "-C", str(repo), "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
        return ref.split("/", 1)[1] if "/" in ref else ref
    except subprocess.CalledProcessError:
        pass
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), "branch", "--show-current"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip() or "main"
    except subprocess.CalledProcessError:
        return "main"


class LinkRewriter:
    """Rewrites `](target)` link targets found in the source charts."""

    LINK_RE = re.compile(r"\]\(([^)]+)\)")

    def __init__(self, chart_names: set, github_slug: str, branch: str):
        self.chart_names = chart_names            # {"kernel", "prog00_no_operation", ...}
        self.gh = f"https://github.com/{github_slug}"
        self.branch = branch

    def github_url(self, rel: str) -> str:
        # Source links are relative to dsp/flowcharts/ ; `../x` -> dsp/x.
        # (README.md lives in the same dir, so resolution is uniform.)
        is_dir = rel.endswith("/")
        parts = []
        for seg in rel.split("/"):
            if seg in ("", "."):
                continue
            if seg == "..":
                parts.append("..")
            else:
                parts.append(seg)
        # collapse the leading `..` hops from dsp/flowcharts/
        base = ["dsp", "flowcharts"]
        for seg in parts:
            if seg == "..":
                if base:
                    base.pop()
            else:
                base.append(seg)
        path = "/".join(base)
        kind = "tree" if is_dir else "blob"
        return f"{self.gh}/{kind}/{self.branch}/{path}"

    def _rewrite_target(self, target: str) -> str:
        # Leave absolute URLs / anchors / mailto untouched.
        if re.match(r"^[a-z]+://", target) or target.startswith("#") or target.startswith("mailto:"):
            return target
        # chart -> chart (and the source index README.md)
        if target.endswith(".md"):
            stem = target[:-3]
            if stem == "README":
                return SITE_INDEX_LINK
            if stem in self.chart_names:
                return "{{ site.baseurl }}" + chart_permalink(stem)
        # links into the disasm repo
        if target.startswith("../"):
            return self.github_url(target)
        return target

    def apply(self, text: str) -> str:
        return self.LINK_RE.sub(
            lambda m: "](" + self._rewrite_target(m.group(1)) + ")", text
        )


def heading_title(body: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return html.unescape(line[2:].strip())
    return "DSP flowchart"


def yaml_quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def front_matter(title: str, permalink: str, src_name: str) -> str:
    return (
        "---\n"
        "layout: page\n"
        f"title: {yaml_quote(title)}\n"
        f"permalink: {permalink}\n"
        "---\n"
        f"<!-- {GENERATED_MARKER} dsp/flowcharts/{src_name} "
        "by tools/sync_flowcharts.py -- DO NOT EDIT; run `make flowcharts`. -->\n\n"
    )


def index_footer(github_slug: str) -> str:
    return (
        "\n---\n\n"
        "## On this site\n\n"
        "These flowcharts are the diagram companion to the "
        "[Effects DSP (NEC uPD6383GF)]({{ site.baseurl }}/effects-dsp/) reference "
        "page. The narrative &mdash; how each result was found &mdash; is in the MAME "
        "development blog, KN5000 effects-DSP series (Parts 78-84).\n\n"
        f"Synced from the [`kn5000-roms-disasm`](https://github.com/{github_slug}) "
        "disassembly tree by `tools/sync_flowcharts.py`; re-run `make flowcharts` "
        "to refresh after the charts are regenerated upstream.\n"
    )


def build_page(src_path: Path, rewriter: LinkRewriter, is_index: bool, github_slug: str) -> tuple:
    body = src_path.read_text()
    name = src_path.stem  # "kernel", "prog16_room_reverb_1", "README"
    title = heading_title(body)
    if is_index:
        permalink = PERMALINK_BASE + "/"
        out_name = "index.md"
    else:
        permalink = chart_permalink(name)
        out_name = name + ".md"
    rewritten = rewriter.apply(body)
    page = front_matter(title, permalink, src_path.name) + rewritten
    if is_index:
        if not page.endswith("\n"):
            page += "\n"
        page += index_footer(github_slug)
    return out_name, page


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    default_disasm = Path(__file__).resolve().parents[2] / "kn5000-roms-disasm"
    ap.add_argument("--disasm", type=Path, default=default_disasm,
                    help=f"path to the kn5000-roms-disasm repo (default: {default_disasm})")
    ap.add_argument("--site", type=Path, default=Path(__file__).resolve().parents[1],
                    help="path to the technics-docs site root (default: repo of this script)")
    args = ap.parse_args()

    src_dir = args.disasm / "dsp" / "flowcharts"
    if not src_dir.is_dir():
        print(f"error: source flowcharts dir not found: {src_dir}", file=sys.stderr)
        return 2

    out_dir = args.site / SITE_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)

    sources = sorted(src_dir.glob("*.md"))
    chart_names = {p.stem for p in sources if p.name != "README.md"}

    slug = git_remote_slug(args.disasm)
    branch = git_default_branch(args.disasm)
    rewriter = LinkRewriter(chart_names, slug, branch)

    written = {}
    for src in sources:
        is_index = src.name == "README.md"
        out_name, page = build_page(src, rewriter, is_index, slug)
        written[out_name] = page

    # Emit (deterministic content).
    for out_name in sorted(written):
        (out_dir / out_name).write_text(written[out_name])

    # Prune stale generated pages (charts dropped upstream); only touch files we own.
    for existing in out_dir.glob("*.md"):
        if existing.name in written:
            continue
        if GENERATED_MARKER in existing.read_text():
            existing.unlink()

    print(f"synced {len(written)} pages -> {out_dir}  "
          f"(index=1, charts={len(written) - 1}; repo {slug}@{branch})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
