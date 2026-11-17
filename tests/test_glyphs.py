"""Rules for particular glyphs, each one written after a shape went wrong
in a release.  When a glyph is fixed, add the rule that would have caught
it here."""
from __future__ import annotations

import pytest
from fontTools.pens.boundsPen import BoundsPen

from conftest import STYLES

# 2048 units per em; 4 units is about 2 on the 1000-unit design grid
TOL = 4


def bounds(font, name):
    gs = font.getGlyphSet()
    bp = BoundsPen(gs)
    gs[name].draw(bp)
    return bp.bounds


@pytest.mark.parametrize('style', STYLES)
def test_q_advance_ends_at_the_tip_of_its_tail(otf, style):
    """5.002: the Q used to add a full sidebearing past its tail, which left
    a hole after every Q."""
    font = otf[style]
    xmax = bounds(font, 'Q')[2]
    assert abs(font['hmtx']['Q'][0] - xmax) <= TOL


@pytest.mark.parametrize('style', STYLES)
def test_q_tail_reaches_below_the_baseline(otf, style):
    assert bounds(otf[style], 'Q')[1] < 0


@pytest.mark.parametrize('style', STYLES)
def test_q_is_an_o_with_a_tail(otf, style):
    """The Q's bowl is the O: same left side and height."""
    q, o = bounds(otf[style], 'Q'), bounds(otf[style], 'O')
    assert abs(q[0] - o[0]) <= TOL
    assert abs(q[3] - o[3]) <= TOL


@pytest.mark.parametrize('style', STYLES)
@pytest.mark.parametrize('name', ['asciitilde', 'tilde', 'tildecomb'])
def test_tilde_falls_from_left_to_right(otf, style, name):
    """5.002: the tilde rose left to right, so ñ read as ń.  Its leftmost ink
    must sit higher than its rightmost ink."""
    from glyph_render import glyph_polygons
    pts = [p for poly in glyph_polygons(otf[style], name) for p in poly]
    xmin = min(x for x, _ in pts)
    xmax = max(x for x, _ in pts)
    left_top = max(y for x, y in pts if x <= xmin + 20)
    right_top = max(y for x, y in pts if x >= xmax - 20)
    assert left_top > right_top


@pytest.mark.parametrize('style', STYLES)
@pytest.mark.parametrize('upper, lower', [('O', 'o'), ('H', 'n'), ('E', 'e')])
def test_capitals_are_taller_than_lowercase(otf, style, upper, lower):
    assert bounds(otf[style], upper)[3] > bounds(otf[style], lower)[3]


@pytest.mark.parametrize('style', STYLES)
def test_tabular_figures_share_one_advance(otf, style):
    names = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']
    assert len({otf[style]['hmtx'][n][0] for n in names}) == 1
