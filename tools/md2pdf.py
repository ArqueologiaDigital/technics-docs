#!/usr/bin/env python3
"""md2pdf.py -- Markdown -> printable HTML, with no dependencies at all.

QUESTION IT ANSWERS: "how do I get a shareable PDF of a page on this site?"

    python3 tools/md2pdf.py page.md /tmp/page.html
    chromium --headless --no-sandbox --disable-gpu --no-pdf-header-footer \
        --print-to-pdf=/abs/page.pdf file:///tmp/page.html

or just use the wrapper, which does both and checks the result:

    tools/page_to_pdf.sh upd6383-datasheet.md ~/upd6383-datasheet.pdf

WHY NOT THE OBVIOUS TOOLS.  This machine has no pandoc, no LaTeX, no WeasyPrint
and no Python `markdown`.  It does have Chromium, and every PDF this project has
ever published was printed by it -- `pdfinfo` on all three reports in KN7000/
reads `Producer: Skia/PDF m150`.  So the house pipeline is Markdown -> HTML ->
headless Chromium, and this is the converter half of it.

WHY NOT PRINT THE JEKYLL PAGE.  `assets/main.scss` has no `@media print` rules,
so printing a built site page drags in the 260px sidebar and the site chrome.

⚠ Chromium fails QUIETLY -- a missing file or a relative path yields a valid but
empty PDF.  Always check the output; `page_to_pdf.sh` does.

PROVENANCE: vendored from `gflib-build/docs/md2pdf.py`, which produced
KN7000-SD-media-security-report-2026-08-03.pdf.  Copied rather than referenced so
this repo does not depend on an uncommitted sibling.  Local change: Jekyll front
matter is stripped, and the `{{ site.baseurl }}` Liquid links the site uses are
rewritten to the public site so they still work in a PDF someone was handed.

Handles the GitHub-flavored subset used here: ATX headers, fenced code blocks,
pipe tables, ordered/unordered lists with wrapped continuation lines, horizontal
rules, blockquotes, and inline code / links / **bold** / *italic* /
~~strikethrough~~.  Code-span contents are protected from later inline passes.
"""
import html
import re
import sys

CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm; }
* { box-sizing: border-box; }
body {
  font-family: "DejaVu Serif", Georgia, "Times New Roman", serif;
  font-size: 10.5pt; line-height: 1.45; color: #1a1a1a; max-width: 100%;
}
h1, h2, h3, h4 { font-family: "DejaVu Sans", Helvetica, Arial, sans-serif; line-height: 1.2; color: #111; }
h1 { font-size: 20pt; border-bottom: 2px solid #444; padding-bottom: 6px; margin: 0 0 10px; }
h2 { font-size: 14.5pt; margin: 20px 0 7px; border-bottom: 1px solid #ccc; padding-bottom: 3px; page-break-after: avoid; }
h3 { font-size: 12pt; margin: 15px 0 5px; page-break-after: avoid; }
h4 { font-size: 10.8pt; margin: 12px 0 4px; page-break-after: avoid; }
p { margin: 6px 0; }
a { color: #08507a; text-decoration: none; }
strong { color: #111; }
del { color: #999; }
code {
  font-family: "DejaVu Sans Mono", "Courier New", monospace; font-size: 9pt;
  background: #f3f3f3; padding: 1px 4px; border-radius: 3px; border: 1px solid #e2e2e2;
}
pre {
  background: #f6f8fa; border: 1px solid #ddd; border-radius: 5px; padding: 10px 12px;
  overflow-x: auto; page-break-inside: avoid;
}
pre code { background: none; border: none; padding: 0; font-size: 8.6pt; line-height: 1.4; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 9.3pt; page-break-inside: avoid; }
th, td { border: 1px solid #ccc; padding: 5px 8px; text-align: left; vertical-align: top; }
th { background: #ededed; font-family: "DejaVu Sans", Helvetica, Arial, sans-serif; }
tr:nth-child(even) td { background: #fafafa; }
ul, ol { margin: 6px 0 6px 0; padding-left: 22px; }
li { margin: 3px 0; }
hr { border: none; border-top: 1px solid #bbb; margin: 18px 0; }
blockquote { border-left: 4px solid #ccc; margin: 8px 0; padding: 2px 12px; color: #555; }
"""

_codes = []


def _protect_code(m):
    _codes.append("<code>" + m.group(1) + "</code>")
    return "\x00C%d\x00" % (len(_codes) - 1)


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", _protect_code, text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)([^*]+?)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"\x00C(\d+)\x00", lambda m: _codes[int(m.group(1))], text)
    return text


def is_table_sep(line):
    return bool(re.match(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$", line))


def split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def convert(md):
    lines = md.split("\n")
    out = []
    para = []
    i = 0
    n = len(lines)

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    while i < n:
        line = lines[i]
        s = line.strip()

        if s == "":
            flush()
            i += 1
            continue

        # fenced code
        if s.startswith("```"):
            flush()
            lang = s[3:].strip()
            buf = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1  # closing fence
            cls = (' class="lang-%s"' % lang) if lang else ""
            out.append("<pre><code%s>%s</code></pre>" % (cls, html.escape("\n".join(buf), quote=False)))
            continue

        # header
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            flush()
            lvl = len(m.group(1))
            out.append("<h%d>%s</h%d>" % (lvl, inline(m.group(2).strip()), lvl))
            i += 1
            continue

        # horizontal rule
        if s == "---" or s == "***" or s == "___":
            flush()
            out.append("<hr>")
            i += 1
            continue

        # table: this line + a separator line next
        if "|" in line and i + 1 < n and is_table_sep(lines[i + 1]):
            flush()
            header = split_row(line)
            i += 2
            rows = []
            while i < n and "|" in lines[i] and lines[i].strip() != "":
                rows.append(split_row(lines[i]))
                i += 1
            t = ["<table>", "<thead><tr>"]
            t += ["<th>%s</th>" % inline(c) for c in header]
            t.append("</tr></thead><tbody>")
            for r in rows:
                t.append("<tr>" + "".join("<td>%s</td>" % inline(c) for c in r) + "</tr>")
            t.append("</tbody></table>")
            out.append("".join(t))
            continue

        # blockquote
        if s.startswith(">"):
            flush()
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip())
                i += 1
            out.append("<blockquote>%s</blockquote>" % inline(" ".join(buf)))
            continue

        # lists (ordered / unordered), with wrapped continuation lines
        lm = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", line)
        if lm:
            flush()
            ordered = bool(re.match(r"\d+\.", lm.group(2)))
            raw_items = []  # collect RAW text per item; format once after joining wraps
            while i < n and lines[i].strip() != "":
                m2 = re.match(r"^(\s*)([-*+]|\d+\.)\s+(.*)$", lines[i])
                if m2:
                    raw_items.append(m2.group(3).strip())
                    i += 1
                else:
                    # continuation (wrapped) line for the current item — keep raw so
                    # inline spans (**bold**, `code`, [links]) that cross the wrap survive
                    if raw_items:
                        raw_items[-1] += " " + lines[i].strip()
                    i += 1
            tag = "ol" if ordered else "ul"
            out.append("<%s>%s</%s>" % (tag, "".join("<li>%s</li>" % inline(it) for it in raw_items), tag))
            continue

        para.append(s)
        i += 1

    flush()
    body = "\n".join(out)
    title = "Report"
    mt = re.search(r"<h1>(.*?)</h1>", body)
    if mt:
        title = re.sub(r"<[^>]+>", "", mt.group(1))
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<title>%s</title><style>%s</style></head><body>%s</body></html>"
        % (html.escape(title), CSS, body)
    )


SITE = "https://arqueologiadigital.github.io/KN5000-docs"


def strip_front_matter(md):
    """Remove Jekyll YAML front matter, returning (body, title).

    The title comes from the front matter when there is one, so the PDF's
    document title matches the page's -- Chromium puts it in the PDF metadata.
    """
    title = None
    if md.startswith("---\n"):
        end = md.find("\n---", 4)
        if end != -1:
            for line in md[4:end].splitlines():
                if line.startswith("title:"):
                    title = line[6:].strip().strip('"\'')
            md = md[end + 4:].lstrip("\n")
    return md, title


def rewrite_liquid_links(md):
    """`{{ site.baseurl }}/x/` only resolves inside Jekyll; a PDF is read outside it."""
    return re.sub(r"\{\{\s*site\.baseurl\s*\}\}", SITE, md)


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f:
        md = f.read()
    md, title = strip_front_matter(md)
    md = rewrite_liquid_links(md)
    out = convert(md)
    if title:
        out = re.sub(r"<title>.*?</title>", "<title>%s</title>" % html.escape(title),
                     out, count=1, flags=re.S)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(out)
    print("wrote", dst)
