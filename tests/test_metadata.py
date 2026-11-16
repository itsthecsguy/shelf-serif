"""Names, versions, metrics and files: the things that drift when someone
bumps a version in one place and forgets another."""
from __future__ import annotations

import datetime
import os
import re

import pytest

import build_ufo
from conftest import (FONTS, ROOT, STYLES, VARIABLE, WEIGHT, all_font_paths, font_id, load, read,
                      static_path)

VERSION = '%d.%03d' % build_ufo.VERSION


def name(font, nid):
    rec = font['name'].getName(nid, 3, 1, 0x409)
    return rec.toUnicode() if rec else None


def changelog_releases():
    return re.findall(r'^## (\d+\.\d{3}), (\d{4}-\d{2}-\d{2})$', read('CHANGELOG.md'), re.M)


def test_changelog_top_entry_is_the_current_version():
    releases = changelog_releases()
    assert releases, 'CHANGELOG.md has no "## X.YYY, YYYY-MM-DD" headings'
    assert releases[0][0] == VERSION


def test_build_date_is_the_release_date():
    """build.sh's SOURCE_DATE_EPOCH must be midnight UTC on the date of the
    top changelog entry, so the font timestamps match the release."""
    m = re.search(r'SOURCE_DATE_EPOCH:-(\d+)', read('build.sh'))
    assert m
    stamp = datetime.datetime.fromtimestamp(int(m.group(1)), datetime.UTC)
    assert stamp.strftime('%Y-%m-%d') == changelog_releases()[0][1]
    assert (stamp.hour, stamp.minute, stamp.second) == (0, 0, 0)


def test_readme_names_the_current_version():
    readme = read('README.md')
    assert f'Current version is {VERSION}.' in readme
    for link in re.findall(r'releases/download/v([\d.]+)/ShelfSerif-([\d.]+)\.zip', readme):
        assert link == (VERSION, VERSION)
    for tag in re.findall(r'shelf-serif@v([\d.]+)/', readme):
        assert tag == VERSION


@pytest.mark.parametrize('path', all_font_paths(), ids=font_id)
def test_font_version_and_names(path):
    font = load(path)
    assert font['head'].fontRevision == pytest.approx(float(VERSION), abs=1e-4)
    assert name(font, 5).startswith(f'Version {VERSION}')
    assert name(font, 16) in (None, 'Shelf Serif') and name(font, 1).startswith('Shelf Serif')
    assert 'Open Font License' in name(font, 13)
    assert name(font, 14) == build_ufo.LICENSE_URL
    assert font['OS/2'].fsType == 0
    assert font['head'].unitsPerEm == 2048


@pytest.mark.parametrize('style', STYLES)
@pytest.mark.parametrize('fmt', ['otf', 'ttf', 'woff2'])
def test_static_style_names_and_weight_class(fmt, style):
    font = load(static_path(fmt, style))
    assert font['OS/2'].usWeightClass == WEIGHT[style]
    assert name(font, 6) == f'ShelfSerif-{style}'
    typo_sub = name(font, 17) or name(font, 2)
    assert typo_sub == style
    bold = style == 'Bold'
    assert bool(font['OS/2'].fsSelection & 0x20) == bold
    assert bool(font['head'].macStyle & 1) == bold


@pytest.mark.parametrize('path', all_font_paths(), ids=font_id)
def test_vertical_metrics_give_the_same_line_on_every_platform(path):
    os2, hhea = load(path)['OS/2'], load(path)['hhea']
    asc, desc = build_ufo.r(build_ufo.ASC), build_ufo.r(build_ufo.DESC)
    assert (os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap) == (asc, desc, 0)
    assert (hhea.ascent, hhea.descent, hhea.lineGap) == (asc, desc, 0)
    assert (os2.usWinAscent, os2.usWinDescent) == (asc, -desc)
    assert os2.fsSelection & (1 << 7), 'USE_TYPO_METRICS'
    # the README promises a 1.2 em line
    assert (asc - desc) / 2048 == pytest.approx(1.2, abs=0.001)


def test_variable_font_axis_and_instances():
    font = load(VARIABLE)
    (axis,) = font['fvar'].axes
    assert (axis.axisTag, axis.minValue, axis.defaultValue, axis.maxValue) == ('wght', 300, 400, 700)
    coords = sorted(i.coordinates['wght'] for i in font['fvar'].instances)
    assert coords == [300, 400, 500, 600, 700]
    assert 'STAT' in font


def test_every_font_has_the_same_glyph_set():
    orders = {font_id(p): load(p).getGlyphOrder() for p in all_font_paths()}
    first = next(iter(orders.values()))
    for fid, order in orders.items():
        assert order == first, fid


def test_readme_glyph_counts_are_true():
    readme = read('README.md')
    font = load(static_path('otf', 'Regular'))
    nglyphs = len(font.getGlyphOrder())
    cmap = font.getBestCmap()
    assert f'{nglyphs} glyphs' in readme
    assert f'{nglyphs} glyphs and {len(cmap)} Unicode codepoints' in readme
    gs = font.getGlyphSet()
    visible = [u for u, n in cmap.items()
               if u not in (0x20, 0xA0) and not (0x300 <= u < 0x370)]
    assert f"each face's {len(visible)} visible characters" in readme
    assert len(visible) == sum(1 for u in visible if cmap[u] in gs)


def test_stylesheet_points_at_files_that_exist():
    css = read('css/shelf-serif.css')
    urls = re.findall(r'url\("([^"]+)"\)', css)
    assert urls
    for url in urls:
        path = os.path.normpath(os.path.join(ROOT, 'css', url))
        assert os.path.exists(path), url
    for style in STYLES:
        assert f'ShelfSerif-{style}.woff2' in css


def test_no_stray_files_in_fonts():
    expected = {os.path.relpath(p, FONTS) for p in all_font_paths()}
    found = set()
    for dirpath, _, files in os.walk(FONTS):
        for f in files:
            found.add(os.path.relpath(os.path.join(dirpath, f), FONTS))
    assert found == expected
