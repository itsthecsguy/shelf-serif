"""OpenType behaviour, shaped with HarfBuzz the way browsers set text."""
from __future__ import annotations

import pytest
import uharfbuzz as hb

from conftest import STYLES, VARIABLE, static_path

_faces = {}


def shape(path, text, features=None, variations=None):
    if path not in _faces:
        with open(path, 'rb') as fh:
            _faces[path] = hb.Face(fh.read())
    font = hb.Font(_faces[path])
    if variations:
        font.set_variations(variations)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, features or {})
    names = [font.glyph_to_string(i.codepoint) for i in buf.glyph_infos]
    return names, [p.x_advance for p in buf.glyph_positions], [p.x_offset for p in buf.glyph_positions]


PATHS = [static_path('otf', s) for s in STYLES] + [static_path('ttf', s) for s in STYLES] + [VARIABLE]


def ids(p):
    return p.split('fonts/')[-1]


@pytest.mark.parametrize('path', PATHS, ids=ids)
def test_every_mapped_character_shapes_to_a_real_glyph(path):
    from conftest import load
    chars = ''.join(chr(u) for u in sorted(load(path).getBestCmap()))
    names, _, _ = shape(path, chars)
    assert '.notdef' not in names


@pytest.mark.parametrize('path', PATHS, ids=ids)
@pytest.mark.parametrize('pair', ['AV', 'To', 'Ty', 'LT', 'P.', 'Yo'])
def test_kerning_tightens_classic_pairs(path, pair):
    kerned = sum(shape(path, pair)[1])
    plain = sum(shape(path, pair, {'kern': False})[1])
    assert kerned < plain


@pytest.mark.parametrize('path', PATHS, ids=ids)
def test_accented_letters_kern_like_their_base(path):
    assert sum(shape(path, 'ÀV')[1]) - sum(shape(path, 'ÀV', {'kern': False})[1]) == \
        sum(shape(path, 'AV')[1]) - sum(shape(path, 'AV', {'kern': False})[1])


@pytest.mark.parametrize('path', PATHS, ids=ids)
def test_figures_are_tabular_by_default(path):
    _, advances, _ = shape(path, '0123456789')
    assert len(set(advances)) == 1
    _, advances, _ = shape(path, '0123456789', {'tnum': True})
    assert len(set(advances)) == 1


@pytest.mark.parametrize('path', PATHS, ids=ids)
def test_pnum_gives_proportional_figures(path):
    names, advances, _ = shape(path, '0123456789', {'pnum': True})
    assert all(n.endswith('.pnum') for n in names)
    assert len(set(advances)) > 1
    assert shape(path, '1', {'pnum': True})[1][0] < shape(path, '1')[1][0]


@pytest.mark.parametrize('path', PATHS, ids=ids)
@pytest.mark.parametrize('base, dotless', [('i', 'dotlessi'), ('j', 'dotlessj')])
def test_ccmp_drops_the_dot_under_an_accent(path, base, dotless):
    # i and j with a macron have no precomposed glyph here, so HarfBuzz keeps
    # the combining mark and ccmp has to swap in the dotless form
    names, _, _ = shape(path, base + '\N{COMBINING MACRON}')
    assert names[0] == dotless


@pytest.mark.parametrize('path', PATHS, ids=ids)
@pytest.mark.parametrize('text, mark', [('n\N{COMBINING ACUTE ACCENT}', 'acutecomb'),
                                        ('o\N{COMBINING CARON}', 'caroncomb'),
                                        ('A\N{COMBINING MACRON}', 'macroncomb'),
                                        ('u\N{COMBINING RING ABOVE}', 'ringcomb'),
                                        ('Y\N{COMBINING GRAVE ACCENT}', 'gravecomb')])
def test_combining_accents_attach_to_their_base(path, text, mark):
    # combinations with no precomposed glyph in the font, so the mark stays
    # a mark.  Only the letters that have Latin-1 accented forms carry a
    # 'top' anchor; on the others (b, x, Q ...) a combining mark is not
    # positioned, which is a known gap.
    names, advances, offsets = shape(path, text)
    assert names[1] == mark
    assert advances[1] == 0
    # mark positioning moves the accent back over the letter
    assert offsets[1] < 0


@pytest.mark.parametrize('path', PATHS, ids=ids)
def test_no_ligatures(path):
    names, _, _ = shape(path, 'ffi fl ff', {'liga': True, 'dlig': True})
    assert names.count('f') == 5


@pytest.mark.parametrize('wght', [300, 350, 400, 500, 600, 700])
def test_variable_font_widens_with_weight(wght):
    light = sum(shape(VARIABLE, 'Shelf Serif', variations={'wght': 300})[1])
    here = sum(shape(VARIABLE, 'Shelf Serif', variations={'wght': wght})[1])
    assert here >= light


@pytest.mark.parametrize('style, wght', [('Light', 300), ('Regular', 400), ('Medium', 500),
                                         ('SemiBold', 600), ('Bold', 700)])
def test_static_weights_match_the_variable_font(style, wght):
    text = 'Grok Bot Shelf AVQ 0123 ß§@'
    static = shape(static_path('otf', style), text)[1]
    var = shape(VARIABLE, text, variations={'wght': wght})[1]
    assert all(abs(a - b) <= 1 for a, b in zip(static, var)), (static, var)
