# Common tasks.  Every target uses the virtualenv in .venv; `make setup`
# creates it.  Run `make help` for the list.

VENV ?= .venv
PY   := $(VENV)/bin/python
BASE ?= HEAD

.PHONY: help setup build test check verify diff snapshot fontbakery images ci clean

help:  ## List the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-11s %s\n", $$1, $$2}'

setup:  ## Create .venv and install the pinned build and check tools
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -q -r requirements-dev.txt

build:  ## Rebuild every file in fonts/ from generator/ (about 10 s)
	./build.sh

test:  ## Run the test suite against the fonts in fonts/ (about 10 s)
	$(PY) -m pytest

check: build test  ## Rebuild, then test: the loop to run after any change

verify: build  ## Rebuild and fail if fonts/ differs from what is committed (what CI checks)
	@git status --short -- fonts
	@test -z "$$(git status --porcelain -- fonts)" || { echo "fonts/ differs from the commit: run make build and commit fonts/"; exit 1; }

diff:  ## Before-and-after images of every changed glyph vs BASE (default HEAD), in build/glyph-diff/
	$(PY) tools/glyph_diff.py --base $(BASE)

snapshot:  ## Accept glyph changes: rewrite tests/snapshots/glyphs.tsv from fonts/
	$(PY) tools/glyph_snapshot.py --update

fontbakery:  ## Font Bakery's universal profile, one folder at a time
	$(VENV)/bin/fontbakery check-universal --succinct -l WARN fonts/otf/*.otf
	$(VENV)/bin/fontbakery check-universal --succinct -l WARN fonts/ttf/*.ttf
	$(VENV)/bin/fontbakery check-universal --succinct -l WARN fonts/variable/*.ttf

images:  ## Re-render the README images (first: .venv/bin/playwright install chromium)
	$(PY) docs/make_images.py

ci: verify test fontbakery  ## Everything CI runs

clean:  ## Remove build output (leaves fonts/ alone)
	rm -rf build sources .pytest_cache
