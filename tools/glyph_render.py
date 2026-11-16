"""Draw glyph outlines from a compiled font straight into Pillow images.

This reads the outlines through fontTools instead of asking a text engine
to set characters, so unencoded glyphs (zero.pnum, dotlessj) draw as easily
as encoded ones, and two versions of a glyph can be laid over each other
pixel for pixel.  Fill is even-odd: each contour is XORed into the mask,
which is right for the overlap-free static fonts this is used on.
"""
from __future__ import annotations

import os

from fontTools.pens.basePen import BasePen
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Vertical window drawn for every glyph, in 2048-upm font units.  It runs
# from below the descender (-200 on the 1000 grid) to above the accented
# capitals.
Y_TOP = 2000
Y_BOTTOM = -560


class PolygonPen(BasePen):
    """Flattens a glyph into a list of closed polygons."""

    def __init__(self, glyphSet, steps=16):
        super().__init__(glyphSet)
        self.steps = steps
        self.polys = []
        self.cur = None

    def _moveTo(self, p):
        self.cur = [p]

    def _lineTo(self, p):
        self.cur.append(p)

    def _curveToOne(self, c1, c2, p):
        p0 = self._getCurrentPoint()
        for i in range(1, self.steps + 1):
            t = i / self.steps
            mt = 1 - t
            self.cur.append((
                mt**3 * p0[0] + 3 * mt * mt * t * c1[0] + 3 * mt * t * t * c2[0] + t**3 * p[0],
                mt**3 * p0[1] + 3 * mt * mt * t * c1[1] + 3 * mt * t * t * c2[1] + t**3 * p[1]))

    def _qCurveToOne(self, c, p):
        p0 = self._getCurrentPoint()
        for i in range(1, self.steps + 1):
            t = i / self.steps
            mt = 1 - t
            self.cur.append((mt * mt * p0[0] + 2 * mt * t * c[0] + t * t * p[0],
                             mt * mt * p0[1] + 2 * mt * t * c[1] + t * t * p[1]))

    def _closePath(self):
        if self.cur and len(self.cur) > 2:
            self.polys.append(self.cur)
        self.cur = None

    _endPath = _closePath


def glyph_polygons(font, name):
    gs = font.getGlyphSet()
    pen = PolygonPen(gs)
    gs[name].draw(pen)
    return pen.polys


def glyph_mask(font, name, scale, width_px, x0_px=0):
    """A mode-'1'-like 'L' mask (0 or 255) of one glyph, `scale` pixels per
    font unit, origin at x0_px, the Y_TOP..Y_BOTTOM window filling the
    height."""
    h = int(round((Y_TOP - Y_BOTTOM) * scale))
    mask = Image.new('L', (width_px, h), 0)
    for poly in glyph_polygons(font, name):
        layer = Image.new('L', (width_px, h), 0)
        pts = [(x0_px + x * scale, (Y_TOP - y) * scale) for x, y in poly]
        ImageDraw.Draw(layer).polygon(pts, fill=255)
        mask = ImageChops.logical_xor(mask.convert('1'), layer.convert('1')).convert('L')
    return mask


def label_font(size=14):
    path = os.path.join(ROOT, 'fonts', 'otf', 'ShelfSerif-Regular.otf')
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()
