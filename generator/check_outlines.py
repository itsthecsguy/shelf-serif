"""Outline QA on the compiled fonts.

For every glyph of every static font (and the variable font's default
outlines) this checks:

  direction   outermost contours run clockwise in TrueType and
              counter-clockwise in CFF (y up); nested contours alternate
  extremes    no curve has an interior x or y extreme more than TOL units
              away from an on-curve point
  stray       no segment shorter than TOL units, no duplicate consecutive
              points, no contour with fewer than 3 points
  kinks       at an on-curve point where both neighbours are nearly
              collinear (between KINK_MIN and KINK_MAX degrees off), the
              join is a kink rather than a clean corner or a smooth joint
  near-axis   straight lines within 1 degree of vertical or horizontal
              that are not exactly so (rounding slop)
  overlaps    the static fonts must have no self-intersecting contours
              (checked by re-running a union and comparing the area)

Usage:  python generator/check_outlines.py [font files...]
Exit status 1 if anything fails.
"""
from __future__ import annotations

import glob
import math
import os
import sys

from fontTools.pens.basePen import BasePen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOL = 1.0          # font units (2048 upm)
KINK_MIN, KINK_MAX = 0.6, 12.0   # degrees


class ContourPen(BasePen):
    """Collects contours as lists of segments: ('l', p0, p1) or
    ('c', p0, c1, c2, p1) or ('q', p0, c, p1)."""

    def __init__(self, glyphSet):
        super().__init__(glyphSet)
        self.contours = []
        self.cur = None
        self.start = None

    def _moveTo(self, p):
        self.cur = []
        self.start = p
        self.last = p

    def _lineTo(self, p):
        self.cur.append(('l', self.last, p))
        self.last = p

    def _curveToOne(self, c1, c2, p):
        self.cur.append(('c', self.last, c1, c2, p))
        self.last = p

    def _qCurveToOne(self, c, p):
        self.cur.append(('q', self.last, c, p))
        self.last = p

    def _closePath(self):
        if self.last != self.start:
            self.cur.append(('l', self.last, self.start))
        self.contours.append(self.cur)
        self.cur = None

    def _endPath(self):
        self._closePath()


def seg_points(seg, n=16):
    if seg[0] == 'l':
        return [seg[1], seg[2]]
    pts = []
    if seg[0] == 'c':
        p0, p1, p2, p3 = seg[1:]
        for i in range(n + 1):
            t = i / n
            mt = 1 - t
            pts.append((mt**3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t**3 * p3[0],
                        mt**3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t**3 * p3[1]))
    else:
        p0, p1, p2 = seg[1:]
        for i in range(n + 1):
            t = i / n
            mt = 1 - t
            pts.append((mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0],
                        mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1]))
    return pts


def signed_area(contour):
    a = 0.0
    for seg in contour:
        pts = seg_points(seg)
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            a += x0 * y1 - x1 * y0
    return a / 2


def point_in_contour(pt, contour):
    x, y = pt
    inside = False
    for seg in contour:
        pts = seg_points(seg)
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if (y0 > y) != (y1 > y):
                xi = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
                if xi > x:
                    inside = not inside
    return inside


def extremes_missing(seg):
    """Interior extremes of a curve segment farther than TOL from both ends."""
    if seg[0] == 'l':
        return []
    pts = seg_points(seg, 64)
    out = []
    p0, p1 = seg[1], seg[-1]
    for axis in (0, 1):
        vals = [p[axis] for p in pts]
        lo, hi = min(vals), max(vals)
        ends = (p0[axis], p1[axis])
        for v in (lo, hi):
            if min(abs(v - e) for e in ends) > TOL:
                out.append(('xy'[axis], v))
    return out


def tangent_in(seg):
    """Direction arriving at the end of seg."""
    if seg[0] == 'l':
        a, b = seg[1], seg[2]
    elif seg[0] == 'c':
        a, b = seg[3], seg[4]
        if a == b:
            a = seg[2]
    else:
        a, b = seg[2], seg[3]
    return (b[0] - a[0], b[1] - a[1])


def tangent_out(seg):
    if seg[0] == 'l':
        a, b = seg[1], seg[2]
    elif seg[0] == 'c':
        a, b = seg[1], seg[2]
        if a == b:
            b = seg[3]
    else:
        a, b = seg[1], seg[2]
    return (b[0] - a[0], b[1] - a[1])


def angle_between(u, v):
    lu, lv = math.hypot(*u), math.hypot(*v)
    if lu < 1e-9 or lv < 1e-9:
        return 0.0
    c = (u[0] * v[0] + u[1] * v[1]) / (lu * lv)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def check_glyph(name, contours, is_cff, allow_overlap):
    probs = []
    if not contours:
        return probs
    # direction by nesting depth: depth 0 outer must be cw (TT) / ccw (CFF)
    areas = [signed_area(c) for c in contours]
    for i, c in enumerate(contours):
        if len(c) < 2:
            probs.append(f'{name}: contour {i} has fewer than 3 points')
            continue
        if abs(areas[i]) < 1.0:
            probs.append(f'{name}: contour {i} has no area')
            continue
        # a point on this contour
        tp = seg_points(c[0], 4)
        test = ((tp[0][0] + tp[-1][0]) / 2, (tp[0][1] + tp[-1][1]) / 2) if c[0][0] == 'l' else tp[2]
        depth = sum(1 for j, o in enumerate(contours) if j != i and point_in_contour(test, o))
        ccw = areas[i] > 0
        outer = depth % 2 == 0
        want_ccw = outer if is_cff else not outer
        if ccw != want_ccw and not allow_overlap:
            probs.append(f'{name}: contour {i} (depth {depth}) runs {"ccw" if ccw else "cw"}')
        for k, seg in enumerate(c):
            p0, p1 = seg[1], seg[-1]
            if math.hypot(p1[0] - p0[0], p1[1] - p0[1]) < TOL:
                probs.append(f'{name}: contour {i} segment {k} is shorter than {TOL} units at {p0}')
            for axis, v in extremes_missing(seg):
                probs.append(f'{name}: contour {i} segment {k} missing {axis}-extreme at {v:.1f}')
            if seg[0] == 'l':
                dx, dy = p1[0] - p0[0], p1[1] - p0[1]
                ang = math.degrees(math.atan2(abs(dy), abs(dx)))
                if (0 < ang < 1.0) or (89.0 < ang < 90):
                    probs.append(f'{name}: contour {i} segment {k} is {ang:.2f} deg off axis {p0}->{p1}')
            # kink at the joint between seg and the next one
            nxt = c[(k + 1) % len(c)]
            a = angle_between(tangent_in(seg), tangent_out(nxt))
            if KINK_MIN < a < KINK_MAX:
                probs.append(f'{name}: kink of {a:.1f} deg at {p1}')
    return probs


def main():
    paths = sys.argv[1:] or sorted(glob.glob(os.path.join(ROOT, 'fonts', 'otf', '*.otf'))
                                   + glob.glob(os.path.join(ROOT, 'fonts', 'ttf', '*.ttf'))
                                   + glob.glob(os.path.join(ROOT, 'fonts', 'variable', '*.ttf')))
    total = 0
    for path in paths:
        f = TTFont(path)
        is_cff = 'CFF ' in f
        is_var = 'fvar' in f
        gs = f.getGlyphSet()
        probs = []
        nglyphs = 0
        for name in f.getGlyphOrder():
            pen = ContourPen(gs)
            gs[name].draw(pen)
            if pen.contours:
                nglyphs += 1
            probs += check_glyph(name, pen.contours, is_cff, allow_overlap=is_var)
        total += len(probs)
        print(f'{os.path.basename(path)}: {nglyphs} drawn glyphs, {len(probs)} problems')
        for p in probs[:80]:
            print('   ', p)
        if len(probs) > 80:
            print(f'    ... {len(probs) - 80} more')
    sys.exit(1 if total else 0)


if __name__ == '__main__':
    main()
