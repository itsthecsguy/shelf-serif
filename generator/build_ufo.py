"""Write the UFO masters and the designspace for Shelf Serif.

The generator draws in a 1000-unit design space (the numbers quoted in
the README and NOTES are those units).  The UFOs are written at 2048
units per em: every coordinate, advance, anchor and kerning value is
multiplied by 2.048 and rounded to an integer here, so the compiled fonts
have twice the coordinate resolution and integer-exact outlines.

Medium and SemiBold are not drawn.  They are interpolated from the
masters at 500 and 600, the same way the variable font makes them, and
written next to the masters so build.sh compiles all five the same way.

Usage:  python generator/build_ufo.py
"""
from __future__ import annotations

import os
import sys

import ufoLib2
from fontTools.designspaceLib import (AxisDescriptor, DesignSpaceDocument,
                                      InstanceDescriptor, SourceDescriptor)
from ufo2ft.instantiator import Instantiator

sys.path.insert(0, os.path.dirname(__file__))
from glyphs import build_all  # noqa: E402
from params import MASTERS  # noqa: E402
from spacing import kerning_for  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources')
FAMILY = 'Shelf Serif'
VERSION = (5, 1)
UPM = 2048
S = UPM / 1000.0
COPYRIGHT = 'Copyright 2026 thecsguy'
LICENSE = ('This Font Software is licensed under the SIL Open Font License, '
           'Version 1.1. This license is available with a FAQ at: '
           'https://openfontlicense.org')
LICENSE_URL = 'https://openfontlicense.org'
URL = 'https://grokbotshelf.com'

# vertical metrics, 1000-unit design space.  typo == hhea == win, line gap
# 0, USE_TYPO_METRICS set: every platform gets the same 1.2 em line.
ASC, DESC = 940, -260

FEATURES = '''\
languagesystem DFLT dflt;
languagesystem latn dflt;

@FIG_T = [zero one two three four five six seven eight nine];
@FIG_P = [zero.pnum one.pnum two.pnum three.pnum four.pnum five.pnum six.pnum seven.pnum eight.pnum nine.pnum];
@MARKS_ABOVE = [gravecomb acutecomb circumflexcomb tildecomb macroncomb dotaccentcomb dieresiscomb ringcomb caroncomb];

# soft-dotted i and j lose their dot under a combining mark above
feature ccmp {
    sub i' @MARKS_ABOVE by dotlessi;
    sub j' @MARKS_ABOVE by dotlessj;
} ccmp;

# figures are tabular by default; pnum swaps in the fitted widths and
# tnum brings the tabular set back
feature pnum {
    sub @FIG_T by @FIG_P;
} pnum;

feature tnum {
    sub @FIG_P by @FIG_T;
} tnum;
'''


WEIGHTS = (('Light', 300), ('Regular', 400), ('Medium', 500), ('SemiBold', 600), ('Bold', 700))
INTERPOLATED = ('Medium', 'SemiBold')


def r(v):
    return int(round(v * S))


def panose(wght):
    # bWeight: 3 light, 5 book, 6 medium, 7 demi, 8 bold
    return [2, 0, {300: 3, 400: 5, 500: 6, 600: 7, 700: 8}[wght], 4, 0, 0, 0, 0, 0, 0]


def unique_id(name):
    return f'{VERSION[0]}.{VERSION[1]:03d};TCSG;ShelfSerif-{name}'


def draw(glyph, contours):
    pen = glyph.getPen()
    for c in contours:
        start = c[-1][-1]
        pen.moveTo((r(start[0]), r(start[1])))
        for i, node in enumerate(c):
            last = i == len(c) - 1
            if node[0] == 'l':
                if not last:
                    pen.lineTo((r(node[1][0]), r(node[1][1])))
            else:
                pen.curveTo(*[(r(p[0]), r(p[1])) for p in node[1:]])
        pen.closePath()


def make_ufo(P):
    font = ufoLib2.Font()
    info = font.info
    info.familyName = FAMILY
    info.styleName = P.name
    # Light is not a RIBBI style, so legacy apps see it as its own family
    info.styleMapFamilyName = FAMILY if P.name in ('Regular', 'Bold') else f'{FAMILY} {P.name}'
    info.styleMapStyleName = 'bold' if P.name == 'Bold' else 'regular'
    info.versionMajor, info.versionMinor = VERSION
    info.unitsPerEm = UPM
    info.ascender = r(ASC)
    info.descender = r(DESC)
    info.xHeight = r(P.xh)
    info.capHeight = r(P.cap)
    info.copyright = COPYRIGHT
    info.trademark = 'Shelf Serif is a typeface of Grok Bot Shelf.'
    info.openTypeNameDesigner = 'thecsguy'
    info.openTypeNameDesignerURL = URL
    info.openTypeNameManufacturer = 'thecsguy'
    info.openTypeNameManufacturerURL = URL
    info.openTypeNameLicense = LICENSE
    info.openTypeNameLicenseURL = LICENSE_URL
    info.openTypeNameDescription = (
        'Shelf Serif: a near-monoline, squared serif with tight corners and '
        'hairline shelf serifs, drawn parametrically for Grok Bot Shelf. '
        'The Light weight matches the GROK BOT SHELF wordmark.')
    info.openTypeNameVersion = 'Version %d.%03d' % VERSION
    info.openTypeNameUniqueID = unique_id(P.name)
    info.openTypeNameSampleText = 'Grok Bot Shelf'
    info.openTypeNamePreferredFamilyName = FAMILY
    info.openTypeNamePreferredSubfamilyName = P.name
    info.openTypeOS2VendorID = 'TCSG'
    info.openTypeOS2Type = []          # installable embedding
    info.openTypeOS2WeightClass = P.wght
    info.openTypeOS2WidthClass = 5
    info.openTypeOS2TypoAscender = r(ASC)
    info.openTypeOS2TypoDescender = r(DESC)
    info.openTypeOS2TypoLineGap = 0
    info.openTypeOS2WinAscent = r(ASC)
    info.openTypeOS2WinDescent = r(-DESC)
    info.openTypeOS2Selection = [7]   # USE_TYPO_METRICS
    info.openTypeOS2CodePageRanges = [0, 1]   # Latin 1, Latin 2 (partial)
    info.openTypeHheaAscender = r(ASC)
    info.openTypeHheaDescender = r(DESC)
    info.openTypeHheaLineGap = 0
    info.openTypeOS2StrikeoutSize = r(P.H)
    info.openTypeOS2StrikeoutPosition = r(P.xh * 0.5 + 12 + P.H / 2)
    info.openTypeOS2SubscriptXSize = r(620)
    info.openTypeOS2SubscriptYSize = r(620)
    info.openTypeOS2SubscriptYOffset = r(120)
    info.openTypeOS2SuperscriptXSize = r(620)
    info.openTypeOS2SuperscriptYSize = r(620)
    info.openTypeOS2SuperscriptYOffset = r(280)
    info.postscriptUnderlineThickness = r(97)   # one value for the family (Regular's 0.8 H)
    info.postscriptUnderlinePosition = r(-120)
    info.postscriptFontName = f'ShelfSerif-{P.name}'
    info.postscriptFullName = f'{FAMILY} {P.name}'
    info.postscriptBlueValues = [r(-P.os), 0, r(P.xh), r(P.xh + P.os), r(P.cap), r(P.cap + P.os),
                                 r(P.asc), r(P.asc + P.os)]
    info.postscriptOtherBlues = [r(P.desc - P.os), r(P.desc)]
    info.postscriptStemSnapH = [r(P.ser), r(P.H)]
    info.postscriptStemSnapV = [r(P.V)]
    info.openTypeOS2Panose = panose(P.wght)

    glyphs = build_all(P, resolved=False)
    order = list(glyphs.keys())
    categories = {}
    for name in order:
        g = glyphs[name]
        ug = font.newGlyph(name)
        ug.width = r(g.width)
        if g.unicode is not None:
            ug.unicodes = [g.unicode]
        if g.components:
            pen = ug.getPen()
            for ref, dx, dy in g.components:
                pen.addComponent(ref, (1, 0, 0, 1, r(dx), r(dy)))
        else:
            draw(ug, g.contours)
        for aname, (ax, ay) in g.anchors.items():
            ug.appendAnchor({'name': aname, 'x': r(ax), 'y': r(ay)})
        if g.category:
            categories[name] = g.category
    font.glyphOrder = order
    font.lib['public.openTypeCategories'] = categories

    groups, kern = kerning_for(P)
    for gname, members in groups.items():
        font.groups[gname] = [m for m in members if m in glyphs]
    font.kerning.update({pair: r(v) for pair, v in kern.items()
                         if (pair[0] in glyphs or pair[0] in groups)
                         and (pair[1] in glyphs or pair[1] in groups)})
    font.features.text = FEATURES
    return font, glyphs


def check_compat(all_glyphs):
    """Masters must have identical contour/point structure."""
    names = list(all_glyphs[0].keys())
    problems = []
    for n in names:
        sigs = []
        for gs in all_glyphs:
            g = gs[n]
            sigs.append(tuple((len(c), tuple(node[0] for node in c)) for c in g.contours))
        if any(s != sigs[0] for s in sigs[1:]):
            problems.append((n, [[c[0] for c in s] for s in sigs]))
    return problems


def main():
    os.makedirs(SRC, exist_ok=True)
    doc = DesignSpaceDocument()
    axis = AxisDescriptor()
    axis.name, axis.tag = 'Weight', 'wght'
    axis.minimum, axis.default, axis.maximum = 300, 400, 700
    doc.addAxis(axis)

    all_glyphs = []
    for P in MASTERS:
        font, glyphs = make_ufo(P)
        path = os.path.join(SRC, f'ShelfSerif-{P.name}.ufo')
        font.save(path, overwrite=True)
        all_glyphs.append(glyphs)
        s = SourceDescriptor()
        s.path = path
        s.filename = os.path.basename(path)
        s.name = f'ShelfSerif-{P.name}'
        s.familyName = FAMILY
        s.styleName = P.name
        s.location = {'Weight': P.wght}
        doc.addSource(s)
        print(f'wrote {path}: {len(glyphs)} glyphs')

    for name, w in WEIGHTS:
        i = InstanceDescriptor()
        i.familyName = FAMILY
        i.styleName = name
        i.name = f'ShelfSerif-{name}'
        i.filename = f'instances/ShelfSerif-{name}.ufo'
        i.location = {'Weight': w}
        i.postScriptFontName = f'ShelfSerif-{name}'
        i.styleMapFamilyName = FAMILY if name in ('Regular', 'Bold') else f'{FAMILY} {name}'
        i.styleMapStyleName = 'bold' if name == 'Bold' else 'regular'
        # The instantiator copies Regular's info and leaves these blank, so
        # set them here the way make_ufo sets them on the masters.
        i.lib['public.fontInfo'] = {
            'openTypeNamePreferredFamilyName': FAMILY,
            'openTypeNamePreferredSubfamilyName': name,
            'openTypeNameUniqueID': unique_id(name),
            'postscriptFullName': f'{FAMILY} {name}',
            'openTypeOS2Panose': panose(w),
        }
        doc.addInstance(i)

    ds = os.path.join(SRC, 'ShelfSerif.designspace')
    doc.write(ds)
    print('wrote', ds)

    problems = check_compat(all_glyphs)
    if problems:
        print('INCOMPATIBLE MASTERS:')
        for n, sigs in problems:
            print(' ', n, sigs)
        sys.exit(1)
    print('masters are interpolation-compatible')

    inst = Instantiator.from_designspace(doc)
    for i in doc.instances:
        if i.styleName in INTERPOLATED:
            path = os.path.join(SRC, f'ShelfSerif-{i.styleName}.ufo')
            inst.generate_instance(i).save(path, overwrite=True)
            print('wrote', path, '(interpolated)')


if __name__ == '__main__':
    main()
