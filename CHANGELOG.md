# Changelog

## 5.001, 2026-11-04

- Static OTF, TTF and WOFF2 files for Medium (500) and SemiBold (600). They are interpolated from the masters the same way the variable font makes them, so a static weight and the variable font at the same weight draw the same outlines. Each one is its own legacy family (`Shelf Serif Medium`, `Shelf Serif SemiBold`) and groups with the others under `Shelf Serif` in apps that read the typographic family names.
- `css/shelf-serif.css` declares the new weights under `"Shelf Serif Static"`.
- Builds are reproducible. `build.sh` fixes the font timestamps with `SOURCE_DATE_EPOCH`, and `requirements.txt` pins every package the build imports, including uharfbuzz, which decides how fontTools packs the layout tables. The same source gives byte-identical fonts on an arm64 Mac and on x86-64 Linux.
- The static TTFs drop on-curve points that sit in the middle of a straight line. skia-pathops left one in the eth on some CPUs and not others. The shapes are the same, and the TTFs have a few points fewer.
- `build.sh` runs in bash instead of zsh.
- A GitHub Actions workflow rebuilds the fonts on every push, checks them against the committed files, and runs the outline checks and Font Bakery.
- `requirements-dev.txt` pins Font Bakery and Playwright.
- The README plays a silent launch video, and `docs/make_video.py` renders silent video unless you pass `--audio`.
- Removed the unused `docs/images/hero.png`.

The shapes, spacing and kerning of Light, Regular, Bold and the variable font are unchanged from 5.000.

## 5.000, 2026-11-01

First public release. One variable font with five named weights from 300 to 700, static Light, Regular and Bold, 244 glyphs covering Basic Latin, Latin-1 and Windows-1252 punctuation, under the SIL Open Font License 1.1.
