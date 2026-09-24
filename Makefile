# technics-docs — local rendering of the documentation site.
#
# The site is a Jekyll site published via GitHub Pages. Mermaid flowcharts render
# CLIENT-SIDE (Mermaid.js is loaded in _includes/head.html + _layouts/default.html),
# so any target here that serves the built HTML to a browser renders the diagrams
# EXACTLY as GitHub Pages does — the diagram output is identical because it is the
# same Mermaid script running in your browser, not a server-side step.
#
# FIDELITY NOTE: GitHub Pages pins Jekyll 3.10.x via the `github-pages` gem. This
# machine has system Jekyll 4.3.4 and that gem is NOT installed, so `bundle` fails.
# We therefore invoke jekyll directly with JEKYLL_NO_BUNDLER_REQUIRE=true (skips the
# Gemfile's github-pages dependency). For CONTENT and for the Mermaid flowcharts this
# is faithful; only obscure Liquid/plugin edge cases could differ between Jekyll 4 and
# GH Pages' Jekyll 3.10. To match GH Pages byte-for-byte, run `make serve-ghpages`
# after `bundle install` once the github-pages gem is available.

JEKYLL      ?= jekyll
DEST        ?= _site
PORT        ?= 4000
NO_BUNDLER   = JEKYLL_NO_BUNDLER_REQUIRE=true

# DSP flowcharts are GENERATED into flowcharts/ from the sibling disassembly repo
# (kn5000-roms-disasm/dsp/flowcharts) by tools/sync_flowcharts.py, so upstream
# chart improvements reach the site with one `make flowcharts`. Override with e.g.
# `make flowcharts DISASM=/path/to/kn5000-roms-disasm`.
DISASM      ?= ../kn5000-roms-disasm
MAME        ?= ../kn7000_mame

.PHONY: serve build flowcharts impl clean serve-ghpages help

## flowcharts: regenerate the DSP flowchart pages from the disassembly source
flowcharts:
	python3 tools/sync_flowcharts.py --disasm $(DISASM) --site .

## impl: regenerate the per-effect "HLE + bytecode" pages from the MAME + disasm sources
impl:
	python3 tools/gen_effect_impl_pages.py --mame $(MAME) --disasm $(DISASM)

## serve: build + live-reload local preview at http://localhost:$(PORT) (renders Mermaid)
serve: flowcharts impl
	$(NO_BUNDLER) $(JEKYLL) serve -s . -d $(DEST) --port $(PORT) --livereload

## build: static build into $(DEST)/ (same HTML GitHub Pages serves)
build: flowcharts impl
	$(NO_BUNDLER) $(JEKYLL) build -s . -d $(DEST)

## serve-ghpages: byte-faithful GitHub Pages render (needs `bundle install` w/ github-pages gem)
serve-ghpages:
	bundle exec $(JEKYLL) serve -s . -d $(DEST) --port $(PORT) --livereload

## clean: remove the built site
clean:
	rm -rf $(DEST)

help:
	@grep -E '^## ' Makefile | sed 's/## //'
