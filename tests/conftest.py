"""Shared paths and fixtures.  The tests read the committed fonts in fonts/
(rebuild with ./build.sh first if you changed the generator) and import the
generator and tools modules directly."""
from __future__ import annotations

import os
import sys

import pytest
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'generator'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

STYLES = ('Light', 'Regular', 'Medium', 'SemiBold', 'Bold')
WEIGHT = {'Light': 300, 'Regular': 400, 'Medium': 500, 'SemiBold': 600, 'Bold': 700}
FONTS = os.path.join(ROOT, 'fonts')
VARIABLE = os.path.join(FONTS, 'variable', 'ShelfSerif[wght].ttf')


def static_path(fmt, style):
    folder = {'otf': 'otf', 'ttf': 'ttf', 'woff2': 'woff2'}[fmt]
    return os.path.join(FONTS, folder, f'ShelfSerif-{style}.{fmt}')


def all_font_paths():
    paths = [static_path(fmt, s) for fmt in ('otf', 'ttf', 'woff2') for s in STYLES]
    return paths + [VARIABLE, os.path.join(FONTS, 'woff2', 'ShelfSerif[wght].woff2')]


def font_id(path):
    return os.path.relpath(path, FONTS)


_cache = {}


def load(path):
    if path not in _cache:
        _cache[path] = TTFont(path)
    return _cache[path]


@pytest.fixture(scope='session')
def otf():
    """{style: TTFont} for the static OTFs."""
    return {s: load(static_path('otf', s)) for s in STYLES}


def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as fh:
        return fh.read()
