"""Post-build.

* static TTFs: drop sub-unit duplicate points left by the cubic-to-
  quadratic conversion, autohint with ttfautohint (hinting range 8 to 64
  px, Latin, no version-string note), set head.flags bit 3 (integer ppem)
* variable TTF: OVERLAP_SIMPLE flags; gasp for grayscale + symmetric
  smoothing at every size; a prep program with smart dropout control; an
  identity avar; a STAT table whose axis values match the fvar instances
  (unhinted, as Google Fonts ships variable fonts)
* WOFF2 copies of every TTF
* read every file back with fontTools and check glyph count, upm,
  version, copyright, license, features, vertical metrics
"""
from __future__ import annotations

import glob
import os

from fontTools.otlLib.builder import buildStatTable
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import ttProgram
from ttfautohint import ttfautohint

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, 'fonts')
OTF, TTF, VAR, WOFF2 = (os.path.join(FONTS, d) for d in ('otf', 'ttf', 'variable', 'woff2'))


def clean_tiny_segments(path, tol=1.0):
    """Remove an on-curve point that sits within `tol` units of the
    previous on-curve point (cu2qu + integer rounding can leave two such
    points at a contour's start).  Static TTFs only."""
    f = TTFont(path)
    glyf = f['glyf']
    removed = 0
    for name in glyf.keys():
        g = glyf[name]
        if g.isComposite() or g.numberOfContours <= 0:
            continue
        coords, ends, flags = g.getCoordinates(glyf)
        coords = list(coords)
        flags = list(flags)
        keep = [True] * len(coords)

        def close(i, j):
            dx = coords[i][0] - coords[j][0]
            dy = coords[i][1] - coords[j][1]
            return (dx * dx + dy * dy) ** 0.5 < tol

        start = 0
        for end in ends:
            n = end - start + 1
            # v4.1: compare each on-curve point with the last point kept,
            # so a run of three coincident points (pathops leaves one in
            # the Bold y) collapses to one, then close the cycle
            kept = []
            for i in range(start, end + 1):
                if kept and flags[i] & 1 and flags[kept[-1]] & 1 and close(i, kept[-1]) and n > 3:
                    keep[i] = False
                    n -= 1
                    continue
                kept.append(i)
            if n > 3 and len(kept) > 1 and flags[kept[0]] & 1 and flags[kept[-1]] & 1 \
                    and close(kept[0], kept[-1]):
                keep[kept[-1]] = False
            start = end + 1
        if all(keep):
            continue
        from fontTools.pens.ttGlyphPen import TTGlyphPen
        pen = TTGlyphPen(None)
        start = 0
        for end in ends:
            pts = [(coords[i], flags[i] & 1) for i in range(start, end + 1) if keep[i]]
            start = end + 1
            if len(pts) < 3:
                continue
            # rotate so the contour starts on an on-curve point
            k = next((i for i, (_, on) in enumerate(pts) if on), 0)
            pts = pts[k:] + pts[:k]
            pen.moveTo(pts[0][0])
            i = 1
            while i < len(pts):
                p, on = pts[i]
                if on:
                    pen.lineTo(p)
                    i += 1
                else:
                    offs = []
                    while i < len(pts) and not pts[i][1]:
                        offs.append(pts[i][0])
                        i += 1
                    endp = pts[i][0] if i < len(pts) else pts[0][0]
                    if i >= len(pts):
                        pen.qCurveTo(*offs, pts[0][0])
                        break
                    pen.qCurveTo(*offs, endp)
                    i += 1
            pen.closePath()
        new = pen.glyph()
        glyf[name] = new
        removed += keep.count(False)
    if removed:
        f.save(path)
    return removed


def set_integer_ppem_flag(path):
    f = TTFont(path)
    f['head'].flags |= 1 << 3
    f.save(path)


def variable_tables(path):
    f = TTFont(path)
    glyf = f['glyf']
    for name in glyf.keys():
        g = glyf[name]
        if g.isComposite() or g.numberOfContours <= 0:
            continue
        g.flags[0] |= 0x40  # OVERLAP_SIMPLE
    # unhinted: grayscale + symmetric smoothing at every size
    gasp = newTable('gasp')
    gasp.version = 1
    gasp.gaspRange = {0xFFFF: 0x0A}
    f['gasp'] = gasp
    # smart dropout control for rasterisers that still scan-convert
    prep = newTable('prep')
    prep.program = ttProgram.Program()
    prep.program.fromAssembly(['PUSHW[] 511', 'SCANCTRL[]', 'PUSHB[] 4', 'SCANTYPE[]'])
    f['prep'] = prep
    # identity avar
    avar = newTable('avar')
    avar.segments = {'wght': {-1.0: -1.0, 0.0: 0.0, 1.0: 1.0}}
    f['avar'] = avar
    # STAT: one axis value per named instance, Regular elidable and linked to Bold
    axes = [dict(tag='wght', name='Weight', ordering=0, values=[
        dict(value=300, name='Light'),
        dict(value=400, name='Regular', flags=0x2, linkedValue=700),
        dict(value=500, name='Medium'),
        dict(value=600, name='SemiBold'),
        dict(value=700, name='Bold'),
    ])]
    buildStatTable(f, axes)
    # buildStatTable adds Macintosh name records; the rest of the family
    # has none, so drop them again
    f['name'].names = [n for n in f['name'].names if n.platformID != 1]
    f.save(path)


def autohint(path):
    tmp = path + '.hinted'
    ttfautohint(in_file=path, out_file=tmp,
                hinting_range_min=8, hinting_range_max=64,
                hinting_limit=200, default_script='latn',
                fallback_script='latn', no_info=True,
                windows_compatibility=True)
    os.replace(tmp, path)


def woff2(path):
    f = TTFont(path)
    f.flavor = 'woff2'
    out = os.path.join(WOFF2, os.path.splitext(os.path.basename(path))[0] + '.woff2')
    f.save(out)
    return out


def verify(path):
    f = TTFont(path)
    n = f['name']
    fam = n.getDebugName(16) or n.getDebugName(1)
    sub = n.getDebugName(17) or n.getDebugName(2)
    ver = n.getDebugName(5)
    lic = n.getDebugName(13)
    cr = n.getDebugName(0)
    axes = ''
    if 'fvar' in f:
        axes = ' axes=' + ','.join(f'{a.axisTag}[{a.minValue}-{a.maxValue}]' for a in f['fvar'].axes)
    feats = sorted({fr.FeatureTag for fr in f['GPOS'].table.FeatureList.FeatureRecord}
                   | {fr.FeatureTag for fr in f['GSUB'].table.FeatureList.FeatureRecord})
    os2, hhea, head = f['OS/2'], f['hhea'], f['head']
    print(f'  {os.path.basename(path):30s} glyphs={len(f.getGlyphOrder()):3d} upm={head.unitsPerEm} '
          f'{fam} {sub} {ver}{axes} size={os.path.getsize(path) // 1024}k')
    print(f'      features={",".join(feats)}  typo={os2.sTypoAscender}/{os2.sTypoDescender}/{os2.sTypoLineGap} '
          f'hhea={hhea.ascent}/{hhea.descent}/{hhea.lineGap} win={os2.usWinAscent}/{os2.usWinDescent} '
          f'fsSelection={os2.fsSelection:#06x} fsType={os2.fsType} hinted={"fpgm" in f} '
          f'tables={"STAT" in f and "avar" in f and "gasp" in f}')
    assert cr and cr.startswith('Copyright 2026 thecsguy'), cr
    assert lic and 'SIL Open Font License' in lic, lic
    assert ver == 'Version 5.000', ver
    assert abs(head.fontRevision - 5.0) < 1e-3, head.fontRevision
    assert head.unitsPerEm == 2048
    for tag in ('kern', 'mark', 'pnum', 'tnum', 'ccmp'):
        assert tag in feats, (path, tag)
    assert os2.sTypoAscender == hhea.ascent == os2.usWinAscent
    assert os2.sTypoDescender == hhea.descent == -os2.usWinDescent
    assert os2.fsSelection & (1 << 7), 'USE_TYPO_METRICS'
    # nothing may poke out of the win box (no clipping on Windows)
    assert head.yMax <= os2.usWinAscent and -head.yMin <= os2.usWinDescent, (head.yMax, head.yMin)
    if 'fpgm' in f:
        assert head.flags & (1 << 3)
    return len(f.getGlyphOrder())


def main():
    vf = os.path.join(VAR, 'ShelfSerif[wght].ttf')
    if os.path.exists(vf):
        variable_tables(vf)

    for path in sorted(glob.glob(os.path.join(TTF, '*.ttf'))):
        n = clean_tiny_segments(path)
        if n:
            print(f'  {os.path.basename(path)}: removed {n} sub-unit duplicate points')
        autohint(path)
        set_integer_ppem_flag(path)
    os.makedirs(WOFF2, exist_ok=True)
    for path in sorted(glob.glob(os.path.join(TTF, '*.ttf')) + glob.glob(os.path.join(VAR, '*.ttf'))):
        woff2(path)

    print('\nVerification (fontTools):')
    counts = set()
    for d in (OTF, TTF, VAR, WOFF2):
        for path in sorted(glob.glob(os.path.join(d, '*'))):
            counts.add(verify(path))
    assert len(counts) == 1, counts
    print(f'  all files carry {counts.pop()} glyphs')


if __name__ == '__main__':
    main()
