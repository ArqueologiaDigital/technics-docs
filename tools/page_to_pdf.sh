#!/usr/bin/env bash
# page_to_pdf.sh -- turn a page of this site into a shareable PDF.
#
# QUESTION IT ANSWERS: "Felipe wants to read and forward this page; how do I make the PDF?"
#
#   tools/page_to_pdf.sh <page.md> <out.pdf>
#
# Markdown -> HTML (tools/md2pdf.py) -> headless Chromium.  See md2pdf.py's header for why this
# is the pipeline and not pandoc: none of pandoc, LaTeX, WeasyPrint or python-markdown is
# installed, Chromium is, and every PDF this project has published was printed by it.
#
# ⚠ CHROMIUM FAILS QUIETLY.  A relative path, a missing file or a crashed render all produce a
# valid PDF of zero pages, or none at all, with exit status 0.  This script therefore checks the
# output with pdfinfo and refuses to report success on an empty one -- which is the same rule the
# rest of the project applies to any instrument: prove it can see a failure before trusting a pass.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="${1:?usage: page_to_pdf.sh <page.md> <out.pdf>}"
DST="${2:?usage: page_to_pdf.sh <page.md> <out.pdf>}"
[ -f "$SRC" ] || { echo "no such page: $SRC" >&2; exit 1; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
python3 "$HERE/md2pdf.py" "$SRC" "$TMP/page.html" >/dev/null

DST_ABS="$(cd "$(dirname "$DST")" && pwd)/$(basename "$DST")"
chromium --headless --no-sandbox --disable-gpu --no-pdf-header-footer \
    --print-to-pdf="$DST_ABS" "file://$TMP/page.html" 2>/dev/null

[ -s "$DST_ABS" ] || { echo "FAILED: chromium produced nothing" >&2; exit 1; }
PAGES="$(pdfinfo "$DST_ABS" 2>/dev/null | awk '/^Pages:/{print $2}')"
[ -n "$PAGES" ] && [ "$PAGES" -ge 1 ] || { echo "FAILED: $DST_ABS has no pages" >&2; exit 1; }
WORDS="$(pdftotext -l 1 "$DST_ABS" - 2>/dev/null | wc -w)"
[ "$WORDS" -ge 20 ] || { echo "FAILED: page 1 of $DST_ABS has only $WORDS words -- blank render" >&2; exit 1; }
echo "✅ $DST_ABS  --  $PAGES pages, $WORDS words on page 1"
