# Changelog

## 5.002, 2026-11-14

- Redrew the eszett (ß). The old one closed its top hook with a slanted cut, which left an arrow-shaped counter, and had a sliver of white between the stem and the lower bowl. The new one is a stem that rounds over into an upper bowl, a waist bar that stops short of the stem, and a wider lower bowl.
- Redrew the section sign (§). The old hooks overlapped the middle ring and filled in. The new one has three equal counters, uses the thinner waist stroke on all four horizontals and descends to -150.
- The Q's tail starts inside the bottom stroke. It used to poke a small nub into the counter in Light and Regular and not in Bold.
- The Q's advance ends at the tip of its tail. It used to add a full sidebearing past the tail, which left a hole after every Q. The Q is 44 units narrower in every weight, on the 1000-unit design grid.
- New kerning pairs keep the Q's tail and the section sign off the j hook and the underscore.
- The tilde falls from left to right and has a tick at each end. It used to rise with no ticks, so ñ read as ń. This changes `~`, the spacing and combining tildes, and Ã Ñ Õ ã ñ õ.
- The braces round into their arms. They used to be square brackets with a tick.
- The eth (ð) has a short, thin cross stroke in place of a full-weight diagonal.
- The guillemets are taller and thinner, so the notch stays open in Bold.
- The at sign's inner stem runs to the top of its ring. Its corner used to stick out past a rounded one.
- Bold 4: the stem moves right, the diagonal thins and the bar takes the waist thickness. The counter had closed to 3 units. This also changes the Bold ¼ and ¾. Light and Regular keep their 4.

Every other glyph is unchanged from 5.001.

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
