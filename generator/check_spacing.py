"""Programmatic spacing audit for the three masters.

For every glyph: does any ink fall outside [0, advance]?  (Serifs must
stay inside the advance; only the j hook is allowed out on the left.)

For every pair of glyphs at default spacing (advance + kerning): the
smallest horizontal gap between the left glyph's ink and the right
glyph's ink, measured per 4-unit band of y.  Negative means the outlines
cross.  Pairs tighter than MIN_GAP are listed.

Usage:  python generator/check_spacing.py [--all]   (--all prints every pair under MIN_GAP)
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from glyphs import build_all  # noqa: E402
from params import MASTERS  # noqa: E402
from spacing import flat_kerning  # noqa: E402

BAND = 4
Y0, Y1 = -280, 800
NB = (Y1 - Y0) // BAND
MIN_GAP = 40          # units; pairs tighter than this are reported
ALLOW_LEFT_OUT = {'j', 'dotlessj', 'fraction'}  # hooks and the fraction slash may cross the left edge


def flatten(contour, steps=24):
    pts = []
    start = contour[-1][-1]
    prev = start
    for node in contour:
        if node[0] == 'l':
            pts.append(prev)
            prev = node[1]
        else:
            p0, p1, p2, p3 = prev, node[1], node[2], node[3]
            for i in range(steps):
                t = i / steps
                mt = 1 - t
                x = mt**3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t**3 * p3[0]
                y = mt**3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t**3 * p3[1]
                pts.append((x, y))
            prev = p3
    pts.append(prev)
    return pts


def profile(glyph):
    """Per-band (minx, maxx) of the outline; nan where no ink."""
    lo = np.full(NB, np.inf)
    hi = np.full(NB, -np.inf)
    for c in glyph.contours:
        pts = flatten(c)
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            if ya == yb:
                b = int((ya - Y0) // BAND)
                if 0 <= b < NB:
                    lo[b] = min(lo[b], xa, xb)
                    hi[b] = max(hi[b], xa, xb)
                continue
            if ya > yb:
                xa, ya, xb, yb = xb, yb, xa, ya
            b0 = max(0, int((ya - Y0) // BAND))
            b1 = min(NB - 1, int((yb - Y0) // BAND))
            for b in range(b0, b1 + 1):
                ylo = max(ya, Y0 + b * BAND)
                yhi = min(yb, Y0 + (b + 1) * BAND)
                xlo = xa + (xb - xa) * (ylo - ya) / (yb - ya)
                xhi = xa + (xb - xa) * (yhi - ya) / (yb - ya)
                lo[b] = min(lo[b], xlo, xhi)
                hi[b] = max(hi[b], xlo, xhi)
    lo[np.isinf(lo)] = np.nan
    hi[np.isinf(hi)] = np.nan
    return lo, hi


def audit(P, show_all=False):
    glyphs = build_all(P)
    kern = flat_kerning(P)
    # combining marks are zero-width by design and the accented narrow
    # letters (i, I) carry their accent beyond the advance like any font;
    # both are left out of the audit
    names = [n for n in glyphs if n not in ('.notdef', 'space', 'uni00A0') and glyphs[n].contours
             and glyphs[n].category != 'mark' and not glyphs[n].components]
    prof = {n: profile(glyphs[n]) for n in names}
    print(f'== {P.name}')
    bad = 0
    for n in names:
        lo, hi = prof[n]
        xmin, xmax = np.nanmin(lo), np.nanmax(hi)
        adv = glyphs[n].width
        if xmin < -0.5 and n not in ALLOW_LEFT_OUT:
            print(f'  {n}: ink at x={xmin:.0f} left of the origin')
            bad += 1
        if xmax > adv + 0.5:
            print(f'  {n}: ink at x={xmax:.0f} beyond advance {adv}')
            bad += 1
    print(f'  ink inside advance: {len(names) - bad}/{len(names)} glyphs ok')

    tight = []
    for a in names:
        adv = glyphs[a].width
        loa, hia = prof[a]
        for b in names:
            lob, hib = prof[b]
            gap = adv + kern.get((a, b), 0) + lob - hia
            g = np.nanmin(gap) if not np.all(np.isnan(gap)) else np.inf
            if g < MIN_GAP:
                tight.append((g, a, b))
    tight.sort()
    cross = [t for t in tight if t[0] < 0]
    print(f'  pairs under {MIN_GAP}: {len(tight)}, crossing: {len(cross)}')
    for g, a, b in (tight if show_all else tight[:30]):
        print(f'    {a:>12} {b:<12} gap {g:6.0f}')

    # the gaps the brief asked about, stem face to stem face
    def stem_gap(a, b):
        return glyphs[a].width + kern.get((a, b), 0) + np.nanmin(prof[b][0][(0 - Y0) // BAND:(P.xh - Y0) // BAND]) \
            - np.nanmax(prof[a][1][(0 - Y0) // BAND:(P.xh - Y0) // BAND])
    print('  x-height band gaps: ' + '  '.join(
        f'{a}{b}={stem_gap(a, b):.0f}' for a, b in (('i', 'i'), ('i', 'j'), ('i', 'l'), ('l', 'i'), ('n', 'n'), ('m', 'i'), ('k', 'l'), ('o', 'o'))))
    return tight


def main():
    show_all = '--all' in sys.argv
    for P in MASTERS:
        audit(P, show_all)


if __name__ == '__main__':
    main()
