"""Outline quality of every compiled font: path direction, extremes, stray
points, kinks, near-axis lines and counters that have filled in.  The
checks live in generator/check_outlines.py so they also run from the
command line."""
from __future__ import annotations

import pytest

import check_outlines
from conftest import VARIABLE, font_id, static_path, STYLES

PATHS = [static_path(fmt, s) for fmt in ('otf', 'ttf') for s in STYLES] + [VARIABLE]


@pytest.mark.parametrize('path', PATHS, ids=font_id)
def test_outlines_are_clean(path):
    nglyphs, problems = check_outlines.check_font(path)
    assert nglyphs > 200
    assert problems == [], '\n'.join(problems)


def counter_problems(name, contours):
    return [p for p in check_outlines.check_glyph(name, contours, True, False) if 'counter' in p]


def square(x0, y0, x1, y1, ccw=True):
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if not ccw:
        pts.reverse()
    return [('l', pts[i], pts[(i + 1) % 4]) for i in range(4)]


def test_counter_check_flags_a_closed_counter():
    # a 600-unit square with a 600 x 10 slot cut into it, the shape of a
    # counter that has filled in
    glyph = [square(0, 0, 600, 600), square(100, 300, 500, 310, ccw=False)]
    assert counter_problems('four', glyph)


def test_counter_check_passes_an_open_counter():
    glyph = [square(0, 0, 600, 600), square(150, 150, 450, 450, ccw=False)]
    assert counter_problems('o', glyph) == []
