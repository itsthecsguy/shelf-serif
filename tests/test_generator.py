"""The Python generator itself: masters agree so they interpolate, every
glyph is well formed, and the built fonts carry what the generator drew."""
from __future__ import annotations

import pytest

import build_ufo
from conftest import STYLES, load, static_path
from glyphs import build_all
from params import MASTERS


@pytest.fixture(scope='module')
def masters():
    return [build_all(P, resolved=False) for P in MASTERS]


def test_masters_have_the_same_glyphs_in_the_same_order(masters):
    orders = [list(m) for m in masters]
    assert orders[1] == orders[0] and orders[2] == orders[0]


def test_masters_are_interpolation_compatible(masters):
    assert build_ufo.check_compat(masters) == []


def test_masters_agree_on_unicodes_components_and_anchors(masters):
    for name in masters[0]:
        gs = [m[name] for m in masters]
        assert len({g.unicode for g in gs}) == 1, name
        assert len({tuple(c[0] for c in g.components) for g in gs}) == 1, name
        assert len({tuple(sorted(g.anchors)) for g in gs}) == 1, name


def test_unicodes_are_unique(masters):
    seen = {}
    for name, g in masters[0].items():
        if g.unicode is not None:
            assert g.unicode not in seen, f'{name} and {seen.get(g.unicode)} share U+{g.unicode:04X}'
            seen[g.unicode] = name


def test_widths_are_positive_except_marks(masters):
    for m in masters:
        for name, g in m.items():
            if g.category == 'mark':
                assert g.width == 0, name
            else:
                assert g.width > 0, name


def test_components_reference_existing_glyphs(masters):
    for name, g in masters[0].items():
        for ref, _, _ in g.components:
            assert ref in masters[0], f'{name} uses missing {ref}'


@pytest.mark.parametrize('style', STYLES)
def test_built_fonts_have_the_generator_glyph_set(masters, style):
    font = load(static_path('otf', style))
    assert font.getGlyphOrder() == list(masters[0])
    cmap = font.getBestCmap()
    expected = {g.unicode: n for n, g in masters[0].items() if g.unicode is not None}
    assert cmap == expected


@pytest.mark.parametrize('i', range(3), ids=[P.name for P in MASTERS])
def test_built_master_advances_match_the_generator(masters, i):
    P = MASTERS[i]
    font = load(static_path('otf', P.name))
    hmtx = font['hmtx']
    for name, g in masters[i].items():
        assert hmtx[name][0] == build_ufo.r(g.width), name
