#!/bin/zsh
# Build Shelf Serif from the Python generator.  Uses the venv in .venv
# (see README.md).
#   1. generator writes UFO masters (2048 upm) + designspace into sources/
#   2. fontmake compiles static OTF/TTF (overlaps removed) and the variable TTF
#   3. postprocess.py autohints the static TTFs (ttfautohint), sets overlap
#      flags and gasp on the variable font, writes WOFF2, verifies with fontTools
set -euo pipefail
cd "$(dirname "$0")"
VENV=${VENV:-.venv}
PY=$VENV/bin/python
FM=$VENV/bin/fontmake

$PY generator/build_ufo.py

rm -rf build fonts
mkdir -p fonts/otf fonts/ttf fonts/variable fonts/woff2 build

for style in Light Regular Bold; do
  $FM -u sources/ShelfSerif-$style.ufo -o otf \
      --output-dir fonts/otf --overlaps-backend pathops \
      --no-production-names 2>&1 | grep -viE "^(INFO|WARNING:fontmake.font_project:Removing)" || true
  $FM -u sources/ShelfSerif-$style.ufo -o ttf \
      --output-dir fonts/ttf --overlaps-backend pathops \
      --no-production-names 2>&1 | grep -viE "^(INFO|WARNING:fontmake.font_project:Removing)" || true
done

$FM -m sources/ShelfSerif.designspace -o variable \
    --output-path "fonts/variable/ShelfSerif[wght].ttf" \
    --no-production-names 2>&1 | grep -vi "^INFO" || true

$PY generator/postprocess.py
