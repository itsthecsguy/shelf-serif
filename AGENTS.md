# Working on Shelf Serif

Guidance for anyone changing this repository, people and coding agents alike. The README is for people who use the font. This file is for people who change it.

## What this repository is

Shelf Serif is a typeface whose every outline is drawn by Python. Nothing is edited in a font editor.

- `generator/` draws the glyphs (`glyphs.py`, `glyphs_ext.py`, shapes in `geom.py`, weights in `params.py`, kerning in `spacing.py`) and builds UFO sources (`build_ufo.py`).
- `build.sh` turns those into every file in `fonts/`. The files in `fonts/` are committed and are the product.
- `tests/` checks the fonts in `fonts/`. `tools/` holds the review tools the tests and CI use.

## The rules

1. **Never edit `fonts/` by hand.** Change the generator and run `make build`. CI rebuilds from source and fails if `fonts/` differs from what you committed.
2. **Commit the rebuilt fonts with the code that made them**, in the same commit.
3. **Don't change `requirements.txt` versions** unless the task is to upgrade the toolchain. The build is byte-for-byte reproducible only with these exact versions.
4. **Don't move `SOURCE_DATE_EPOCH` in `build.sh`** except when making a release (see below). Moving it changes the bytes of every font.
5. **Don't loosen a check to make it pass.** If a test in `tests/` or a limit in `generator/check_*.py` fails, fix the glyph. If you are sure the check is wrong, change it in its own commit and say why in the message.

## Setup

```bash
make setup     # creates .venv and installs the pinned tools (Python 3.13 or 3.14)
```

## The loop after every change

```bash
make build     # about 10 s; rewrites fonts/
make test      # about 10 s; 350-odd tests
make diff      # images of every glyph that changed, in build/glyph-diff/
```

`make check` runs build and test together.

**Look at the images.** Open `build/glyph-diff/overview.png` and the per-glyph PNGs. Each per-glyph image has three rows across the five weights. The **before** row is the committed glyph, **after** is your build, and **diff** shows unchanged ink in dark grey, removed ink in red and added ink in blue. The vertical lines are the advance widths. If you are an agent that can read images, read them. Tests catch known failure modes. The images are how you catch a new one, such as a nub poking into a counter or a stroke that thinned in one weight only.

Also check that **only the glyphs you meant to change** appear in `build/glyph-diff/summary.md`. A change to a shared helper in `geom.py` or `params.py` can move dozens of glyphs.

`make diff BASE=origin/main` compares against another ref instead of HEAD.

## When `test_snapshot` fails

`tests/snapshots/glyphs.tsv` records every glyph's advance, side bearings, bounding box, point count, area and outline hash in all five weights. Any glyph change fails `test_fonts_match_the_glyph_snapshot` until you accept it.

```bash
make snapshot  # rewrites tests/snapshots/glyphs.tsv and lists what moved
```

Then read `git diff tests/snapshots/glyphs.tsv`. It should only touch the glyphs you meant to change. Commit it with the fonts.

## What the tests cover

| File | What it checks |
| --- | --- |
| `test_outlines.py` | Path direction, missing extremes, stray points, kinks, off-axis lines, and counters that have filled in, in every OTF and TTF and the variable font. The checks are in `generator/check_outlines.py`. |
| `test_spacing.py` | No ink outside the advance, and no two glyphs collide at default spacing and kerning, in the three drawn masters. The checks are in `generator/check_spacing.py`. |
| `test_generator.py` | Masters are interpolation-compatible and agree on glyphs, Unicode values, components and anchors, and the built fonts carry what the generator drew. |
| `test_shaping.py` | HarfBuzz shaping. Kerning, tabular and proportional figures, `ccmp`, mark positioning, no ligatures, and static weights matching the variable font. |
| `test_glyphs.py` | Rules for particular glyphs that went wrong in a release, such as the Q's advance and the tilde's direction. |
| `test_metadata.py` | Version and date agree across `build_ufo.py`, `build.sh`, the README, the changelog and the font names. Also names, weight classes, vertical metrics, the variable axis, the stylesheet's file paths and the README's glyph counts. |
| `test_snapshot.py` | The fonts match `tests/snapshots/glyphs.tsv`. |
| `test_tools.py` | `glyph_diff` and `glyph_snapshot` notice a changed glyph. |

**When you fix a glyph that shipped broken, add a test to `tests/test_glyphs.py`** that would have caught it. Write a geometric rule that holds in every weight, as the existing tests do.

Run one file or one test with `.venv/bin/python -m pytest tests/test_glyphs.py -k tilde`.

## Units

The generator draws on a 1000-unit grid. `build_ufo.py` multiplies by 2.048 into the fonts' 2048 units per em. The README and code comments quote 1000-unit values. The tests, the snapshot and the diff tool report 2048-unit values from the compiled fonts.

## Other checks

- `make fontbakery` runs Font Bakery's universal profile. CI runs it too. Without network access, the `fontdata_namecheck` check reports ERROR because it can't reach its web service. That error is expected offline.
- `.venv/bin/python generator/check_spacing.py --all` lists every tight pair. Only crossing pairs fail.
- `.venv/bin/python generator/preview.py out.png Q R S --size 300` renders named glyphs large in Light, Regular and Bold.

## Making a release

1. Add a `## X.YYY, YYYY-MM-DD` entry at the top of `CHANGELOG.md`, under any `## Unreleased` notes.
2. Set `VERSION` in `generator/build_ufo.py`.
3. Set `SOURCE_DATE_EPOCH` in `build.sh` to midnight UTC on that date: `date -u -d 2026-11-14 +%s`.
4. Update the version in the README: "Current version is", the release ZIP link and the jsDelivr tag.
5. Run `make build`, `make test` and `make snapshot`, then commit. `test_metadata.py` fails if any of steps 1 to 4 disagree.
6. If shapes changed, run `make images` to re-render the README images.

## CI

`.github/workflows/build.yml` runs on every pull request and on pushes to `main`. It does the following:

- Rebuilds the fonts and fails if they differ from the commit.
- Runs the tests, the spacing audit and Font Bakery.
- On pull requests, a `glyph-diff` job compares the PR's fonts with the base branch. It writes the changed-glyph table to the job summary and uploads the images as the `glyph-diff` artifact.
