"""Parametric geometry for Shelf Serif.

Every glyph is assembled from a handful of primitives that are drawn from
numbers, never from other fonts:

  rect        a rounded rectangle (stems, bars, shelf serifs, dots)
  ring        a rounded-rectangle ring (bowls: O, o, 0, 8, a-bowl)
  arc         a slice of a ring between two cuts (C, S, n-arch, hooks ...)
  diag        a straight stroke between two points with flat/vertical/
              perpendicular end cuts (A, V, K, x, y, z ...)

Contours are lists of nodes.  A node is ('l', (x, y)) or
('c', (c1x, c1y), (c2x, c2y), (x, y)).  The contour is closed and its start
point is the end point of the last node.  Outer contours run counter-
clockwise (positive signed area, y up), holes run clockwise.

The node count of a primitive does not depend on the weight parameters,
which is what keeps the Regular and Bold masters interpolation-compatible.
"""
from __future__ import annotations

import math
from fontTools.misc.bezierTools import calcCubicParameters, solveCubic

KAPPA = 0.5522847498  # circular-arc cubic handle ratio

# v2: corner tension.  1.0 = circular arc, 0.0 = straight 45-degree chamfer.
# The wordmark's corners read as a tight cut between the two, so bowls use a
# low tension; stems/serifs with tiny radii use the full circle.
CORNER_TENSION = 0.62

# v2: how much of the stroke the inner corner radius gives up.  1.0 would be
# a concentric rounded rectangle (inner radius = outer - stroke).  Smaller
# values keep a visible cut on the inside of a tight corner, which is what
# the wordmark's O and B counters do.  v3: 0.85, measured off the O's
# inner corner (about 0.09 cap against 0.21 outside).
INNER_SHRINK = 0.85

# v4: set to a list to collect level/plumb cuts that landed on a corner
CUT_AUDIT = None

Pt = tuple[float, float]


# ---------------------------------------------------------------- helpers
def _lerp(a: Pt, b: Pt, t: float) -> Pt:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def _split_cubic(p0, p1, p2, p3, t):
    """de Casteljau split, returns (left, right) as 4-point tuples."""
    p01 = _lerp(p0, p1, t)
    p12 = _lerp(p1, p2, t)
    p23 = _lerp(p2, p3, t)
    p012 = _lerp(p01, p12, t)
    p123 = _lerp(p12, p23, t)
    m = _lerp(p012, p123, t)
    return (p0, p01, p012, m), (m, p123, p23, p3)


def _sub_cubic(p0, p1, p2, p3, t0, t1):
    if t0 > 0:
        _, (p0, p1, p2, p3) = _split_cubic(p0, p1, p2, p3, t0)
        t1 = (t1 - t0) / (1 - t0) if t0 < 1 else 1.0
    if t1 < 1:
        (p0, p1, p2, p3), _ = _split_cubic(p0, p1, p2, p3, t1)
    return (p0, p1, p2, p3)


def _seg_sub(seg, t0, t1):
    if seg[0] == 'l':
        _, a, b = seg
        return ('l', _lerp(a, b, t0), _lerp(a, b, t1))
    _, p0, p1, p2, p3 = seg
    return ('c',) + _sub_cubic(p0, p1, p2, p3, t0, t1)


def _seg_rev(seg):
    if seg[0] == 'l':
        return ('l', seg[2], seg[1])
    return ('c', seg[4], seg[3], seg[2], seg[1])


def _seg_end(seg):
    return seg[-1]


def _seg_start(seg):
    return seg[1]


def _is_degenerate(seg):
    """v4: a zero-length line (a sharp corner's placeholder segment)."""
    if seg[0] != 'l':
        return False
    (ax, ay), (bx, by) = seg[1], seg[2]
    return abs(ax - bx) < 1e-6 and abs(ay - by) < 1e-6


def pieces_to_contour(pieces):
    """Turn a closed chain of segments into nodes.  Zero-length lines
    (sharp corners) are dropped so no stray points reach the font."""
    nodes = []
    for s in pieces:
        if _is_degenerate(s):
            continue
        if s[0] == 'l':
            nodes.append(('l', s[2]))
        else:
            nodes.append(('c', s[2], s[3], s[4]))
    return nodes


def contour_points(nodes):
    return [n[-1] for n in nodes]


def signed_area(nodes):
    pts = contour_points(nodes)
    a = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i - 1]
        x1, y1 = pts[i]
        a += x0 * y1 - x1 * y0
    return a / 2


def reverse_contour(nodes):
    """Reverse direction, keeping the node format."""
    pts = contour_points(nodes)
    n = len(nodes)
    out = []
    # new start = old start (pts[-1]); walk backwards
    for i in range(n - 1, -1, -1):
        node = nodes[i]
        prev_pt = pts[i - 1]
        if node[0] == 'l':
            out.append(('l', prev_pt))
        else:
            out.append(('c', node[2], node[1], prev_pt))
    return out


def ccw(nodes):
    return nodes if signed_area(nodes) >= 0 else reverse_contour(nodes)


def cw(nodes):
    return nodes if signed_area(nodes) <= 0 else reverse_contour(nodes)


def transform(contours, fn):
    """Apply a point function.  Reverses contours if the map flips handedness."""
    out = []
    for c in contours:
        nc = []
        for n in c:
            if n[0] == 'l':
                nc.append(('l', fn(n[1])))
            else:
                nc.append(('c', fn(n[1]), fn(n[2]), fn(n[3])))
        if (signed_area(nc) >= 0) != (signed_area(c) >= 0):
            nc = reverse_contour(nc)
        out.append(nc)
    return out


def translate(contours, dx, dy):
    return transform(contours, lambda p: (p[0] + dx, p[1] + dy))


def rotate180(contours, cx, cy):
    return transform(contours, lambda p: (2 * cx - p[0], 2 * cy - p[1]))


def mirror_x(contours, cx):
    return transform(contours, lambda p: (2 * cx - p[0], p[1]))


def mirror_y(contours, cy):
    return transform(contours, lambda p: (p[0], 2 * cy - p[1]))


def bbox(contours):
    xs, ys = [], []
    for c in contours:
        for n in c:
            for p in n[1:]:
                xs.append(p[0])
                ys.append(p[1])
    return min(xs), min(ys), max(xs), max(ys)


# ------------------------------------------------------- rounded rectangle
def _radii(r, w, h):
    """Normalise radius spec to (tr, tl, bl, br), clamped to the box.
    v4: a radius under 1.5 (v3 wrote 1 for "square") is a sharp corner."""
    if isinstance(r, (int, float)):
        rr = [float(r)] * 4
    else:
        rr = [float(v) for v in r]
    lim = max(0.5, min(w, h) / 2 - 0.01)
    return [0.0 if v < 1.5 else min(v, lim) for v in rr]


def rr_segments(x0, y0, x1, y1, r):
    """8 segments, counter-clockwise, starting at (x1, y0 + r_br).

    index: 0 right side (up), 1 top-right corner, 2 top (leftwards),
           3 top-left corner, 4 left side (down), 5 bottom-left corner,
           6 bottom (rightwards), 7 bottom-right corner.
    """
    tr, tl, bl, br = _radii(r, x1 - x0, y1 - y0)
    # small radii (stem corners, dots) stay circular; bowl corners get the
    # tighter tension so they read as a cut rather than a round
    k = KAPPA * (CORNER_TENSION if max(tr, tl, bl, br) > 40 else 1.0)

    def corner(rv, a, c1, c2, b):
        # v4: a sharp corner is a zero-length line that pieces_to_contour drops
        if rv == 0:
            return ('l', a, b)
        return ('c', a, c1, c2, b)

    return [
        ('l', (x1, y0 + br), (x1, y1 - tr)),
        corner(tr, (x1, y1 - tr), (x1, y1 - tr + k * tr), (x1 - tr + k * tr, y1), (x1 - tr, y1)),
        ('l', (x1 - tr, y1), (x0 + tl, y1)),
        corner(tl, (x0 + tl, y1), (x0 + tl - k * tl, y1), (x0, y1 - tl + k * tl), (x0, y1 - tl)),
        ('l', (x0, y1 - tl), (x0, y0 + bl)),
        corner(bl, (x0, y0 + bl), (x0, y0 + bl - k * bl), (x0 + bl - k * bl, y0), (x0 + bl, y0)),
        ('l', (x0 + bl, y0), (x1 - br, y0)),
        corner(br, (x1 - br, y0), (x1 - br + k * br, y0), (x1, y0 + br - k * br), (x1, y0 + br)),
    ]


class RRect:
    """A rounded rectangle you can locate cuts on and walk along."""

    def __init__(self, x0, y0, x1, y1, r):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.r = _radii(r, x1 - x0, y1 - y0)  # tr, tl, bl, br
        self.segs = rr_segments(x0, y0, x1, y1, self.r)

    def contour(self):
        return pieces_to_contour(self.segs)

    # -- locating --------------------------------------------------------
    def _t_on_cubic(self, seg, value, axis):
        if seg[0] == 'l':          # v4: sharp corner, nothing to solve
            return 0.0
        _, p0, p1, p2, p3 = seg
        a, b, c, d = calcCubicParameters(p0, p1, p2, p3)
        roots = solveCubic(a[axis], b[axis], c[axis], d[axis] - value)
        best = None
        for t in roots:
            if -1e-6 <= t <= 1 + 1e-6:
                t = min(max(t, 0.0), 1.0)
                if best is None or abs(t - 0.5) < abs(best - 0.5):
                    best = t
        if best is None:
            # fall back to nearest end
            best = 0.0 if abs(p0[axis] - value) < abs(p3[axis] - value) else 1.0
        return best

    def locate(self, cut):
        """cut -> (segment index, t).

        ('a', deg)            perpendicular cut on a corner, deg from +x ccw
        ('x', v, 'top'|'bottom')  vertical cut at x = v
        ('y', v, 'left'|'right')  horizontal cut at y = v
        Values outside the box clamp to the nearest corner end.
        """
        kind = cut[0]
        tr, tl, bl, br = self.r
        if kind == 'a':
            deg = cut[1] % 360.0
            q = int(deg // 90) % 4
            seg = (1, 3, 5, 7)[q]
            return seg, (deg - 90 * q) / 90.0
        if kind == 'x':
            v, side = cut[1], cut[2]
            if side == 'top':
                if v >= self.x1 - tr:
                    if v >= self.x1:
                        return 1, 0.0
                    return 1, self._t_on_cubic(self.segs[1], v, 0)
                if v <= self.x0 + tl:
                    if v <= self.x0:
                        return 3, 1.0
                    return 3, self._t_on_cubic(self.segs[3], v, 0)
                a, b = self.segs[2][1], self.segs[2][2]
                return 2, (v - a[0]) / (b[0] - a[0])
            else:
                if v <= self.x0 + bl:
                    if v <= self.x0:
                        return 5, 0.0
                    return 5, self._t_on_cubic(self.segs[5], v, 0)
                if v >= self.x1 - br:
                    if v >= self.x1:
                        return 7, 1.0
                    return 7, self._t_on_cubic(self.segs[7], v, 0)
                a, b = self.segs[6][1], self.segs[6][2]
                return 6, (v - a[0]) / (b[0] - a[0])
        if kind == 'y':
            v, side = cut[1], cut[2]
            if side == 'right':
                if v <= self.y0 + br:
                    if v <= self.y0:
                        return 7, 0.0
                    return 7, self._t_on_cubic(self.segs[7], v, 1)
                if v >= self.y1 - tr:
                    if v >= self.y1:
                        return 1, 1.0
                    return 1, self._t_on_cubic(self.segs[1], v, 1)
                a, b = self.segs[0][1], self.segs[0][2]
                return 0, (v - a[1]) / (b[1] - a[1])
            else:
                if v >= self.y1 - tl:
                    if v >= self.y1:
                        return 3, 0.0
                    return 3, self._t_on_cubic(self.segs[3], v, 1)
                if v <= self.y0 + bl:
                    if v <= self.y0:
                        return 5, 1.0
                    return 5, self._t_on_cubic(self.segs[5], v, 1)
                a, b = self.segs[4][1], self.segs[4][2]
                return 4, (v - a[1]) / (b[1] - a[1])
        raise ValueError(cut)

    def walk(self, locA, locB):
        """Segments from A to B going counter-clockwise."""
        iA, tA = locA
        iB, tB = locB
        if iA == iB and tA <= tB:
            return [_seg_sub(self.segs[iA], tA, tB)]
        out = [_seg_sub(self.segs[iA], tA, 1.0)]
        i = (iA + 1) % 8
        while i != iB:
            out.append(self.segs[i])
            i = (i + 1) % 8
        out.append(_seg_sub(self.segs[iB], 0.0, tB))
        return out


# ------------------------------------------------------------ primitives
def rect(x0, y0, x1, y1, r=1.0):
    """Rounded rectangle, CCW."""
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    return RRect(x0, y0, x1, y1, r).contour()


def _inner(x0, y0, x1, y1, r, v, h, rmin):
    """Inner rounded rect of a ring with vertical stroke v, horizontal h.
    v5: h may be (top, bottom), for a bowl whose waist side is thinner; the
    corner radii follow the thicker one."""
    tr, tl, bl, br = _radii(r, x1 - x0, y1 - y0)
    ht, hb = h if isinstance(h, tuple) else (h, h)
    d = (v + max(ht, hb)) / 2 * INNER_SHRINK
    # v4: a sharp outer corner gets a sharp inner corner
    ri = [0.0 if rv == 0 else (max(rv - d, rmin) if rv > 40 else rmin)
          for rv in (tr, tl, bl, br)]
    return RRect(x0 + v, y0 + hb, x1 - v, y1 - ht, ri)


def ring(x0, y0, x1, y1, r, v, h, rmin=4.0):
    """Closed ring: outer CCW + inner CW."""
    outer = RRect(x0, y0, x1, y1, r)
    inner = _inner(x0, y0, x1, y1, r, v, h, rmin)
    return [outer.contour(), reverse_contour(inner.contour())]


def arc(x0, y0, x1, y1, r, v, h, cutA, cutB, rmin=4.0):
    """Slice of a ring from cutA to cutB, counter-clockwise along the outer
    boundary.  Returns one CCW contour."""
    outer = RRect(x0, y0, x1, y1, r)
    inner = _inner(x0, y0, x1, y1, r, v, h, rmin)
    la, lb = outer.locate(cutA), outer.locate(cutB)
    ia, ib = inner.locate(cutA), inner.locate(cutB)
    if CUT_AUDIT is not None:
        # v4: record cuts whose closing line is not level/plumb, i.e. where
        # one of the two contours was cut on a corner instead of a side
        for cut, lo, li in ((cutA, la, ia), (cutB, lb, ib)):
            if cut[0] == 'a':
                continue
            straight = lo[0] % 2 == 0 and li[0] % 2 == 0
            if not straight:
                CUT_AUDIT.append((cut, lo, li))
    op = outer.walk(la, lb)
    ip = inner.walk(ia, ib)
    ip_rev = [_seg_rev(s) for s in reversed(ip)]
    pieces = (
        op
        + [('l', _seg_end(op[-1]), _seg_start(ip_rev[0]))]
        + ip_rev
        + [('l', _seg_end(ip_rev[-1]), _seg_start(op[0]))]
    )
    return pieces_to_contour(pieces)


def _cap_points(p, d, n, w, cap):
    """Two points (left, right) of an end cap at point p.

    d: unit direction of the stroke, n: left unit normal, w: full width.
    cap: 'flat' (horizontal cut), 'vert' (vertical cut), 'perp'.
    """
    hw = w / 2
    L = (p[0] + n[0] * hw, p[1] + n[1] * hw)
    R = (p[0] - n[0] * hw, p[1] - n[1] * hw)
    if cap == 'perp':
        return L, R
    if cap == 'flat':      # slide along d until y == p.y
        if abs(d[1]) < 1e-9:
            return L, R
        sL = -(n[1] * hw) / d[1]
        sR = (n[1] * hw) / d[1]
    elif cap == 'vert':    # slide along d until x == p.x
        if abs(d[0]) < 1e-9:
            return L, R
        sL = -(n[0] * hw) / d[0]
        sR = (n[0] * hw) / d[0]
    else:
        raise ValueError(cap)
    return (L[0] + d[0] * sL, L[1] + d[1] * sL), (R[0] + d[0] * sR, R[1] + d[1] * sR)


def diag(p, q, w, cap0='flat', cap1='flat'):
    """Straight stroke of perpendicular width w from p to q.  CCW quad."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dx, dy)
    d = (dx / L, dy / L)
    n = (-d[1], d[0])
    pL, pR = _cap_points(p, d, n, w, cap0)
    qL, qR = _cap_points(q, d, n, w, cap1)
    nodes = [('l', pR), ('l', qR), ('l', qL), ('l', pL)]
    return ccw(nodes)


def diag_halfwidth(p, q, w, cap='flat'):
    """Half extent of the cut at an end along the cut axis."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dx, dy)
    if cap == 'flat':
        return (w / 2) * L / abs(dy)
    if cap == 'vert':
        return (w / 2) * L / abs(dx)
    return w / 2
