"""Glyph constructions for Shelf Serif.

Each glyph function takes a Params object and returns a Glyph with its
advance width and a list of contours.  Nothing here is traced or copied:
every coordinate is derived from the weight parameters and from the
numbers in params.py, which were measured off the wordmark by pixel
coverage.

Design vocabulary (v3)
  * caps carry the wordmark's per-letter ink widths at Light (on a 700
    cap): G 571, R 546, O 583, K 546, B 557, T 542, S 546, H 552, E 494,
    L 480, F 500.  The others follow the same proportion.
  * stems and bars are rounded rectangles with a tiny corner radius
  * bowls are rounded-rectangle rings with a tight, low-tension corner
    (outer radius 0.18 cap on caps, 0.14 cap on lowercase)
  * curved strokes (C, S, arches, hooks) are slices of such rings
  * terminals are horizontal or vertical cuts
  * bars (H, E, F, B, G) centre on 0.485 of the cap height, as measured
  * serifs are hairline "shelves" that sit inside the sidebearing
  * near-monoline: horizontals are 0.85 of verticals, diagonals 0.95

Width model
  Light is the master that matches the logo.  `ow()` gives the outer ink
  width of a cap for any weight (grows by 0.8 of the stem increase);
  `ccw()` is the matching cap counter.  Lowercase outer widths grow by 1.2
  of the stem increase (`owl()`, `cw()`), so Bold lowercase counters stay
  readable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from geom import (arc, bbox, diag, diag_halfwidth, mirror_x, rect, ring,
                  rotate180, translate)
from params import Params, V_L


@dataclass
class Glyph:
    name: str
    width: int
    contours: list = field(default_factory=list)
    unicode: int | None = None
    # v4: composites reference other glyphs: [(glyph name, dx, dy)]
    components: list = field(default_factory=list)
    # v4: attachment points, e.g. {'top': (x, y)} or {'_top': (0, 0)}
    anchors: dict = field(default_factory=dict)
    # v4: 'base' | 'mark' | None, written to public.openTypeCategories
    category: str | None = None


UNICODES = {
    'space': 0x20, 'exclam': 0x21, 'quotedbl': 0x22, 'numbersign': 0x23,
    'dollar': 0x24, 'percent': 0x25, 'ampersand': 0x26, 'quotesingle': 0x27,
    'parenleft': 0x28, 'parenright': 0x29, 'asterisk': 0x2A, 'plus': 0x2B,
    'comma': 0x2C, 'hyphen': 0x2D, 'period': 0x2E, 'slash': 0x2F,
    'colon': 0x3A, 'semicolon': 0x3B, 'equal': 0x3D, 'question': 0x3F,
    'at': 0x40, 'bracketleft': 0x5B, 'bracketright': 0x5D,
    'underscore': 0x5F, 'bar': 0x7C,
    'zero': 0x30, 'one': 0x31, 'two': 0x32, 'three': 0x33, 'four': 0x34,
    'five': 0x35, 'six': 0x36, 'seven': 0x37, 'eight': 0x38, 'nine': 0x39,
}
for _c in range(26):
    UNICODES[chr(65 + _c)] = 65 + _c
    UNICODES[chr(97 + _c)] = 97 + _c


# ------------------------------------------------------------------ builder
class B:
    """Small accumulator: add contours, then finish with a right sidebearing."""

    def __init__(self, P: Params):
        self.P = P
        self.cs = []

    def add(self, *items):
        for it in items:
            if not it:
                continue
            if isinstance(it[0], tuple) and isinstance(it[0][0], str):
                self.cs.append(it)          # a single contour
            else:
                self.cs.extend(it)          # a list of contours
        return self

    def finish(self, name, rsb, edge=None):
        """Advance = right ink edge + rsb.  `edge` overrides the bbox so a
        hairline serif can sit inside the sidebearing instead of adding
        to it."""
        x0, y0, x1, y1 = bbox(self.cs)
        right = x1 if edge is None else max(edge, x1 - self.P.serL)
        return Glyph(name, int(round(right + rsb)), self.cs, UNICODES.get(name))

    def finish_centered(self, name, width):
        x0, y0, x1, y1 = bbox(self.cs)
        dx = (width - (x1 - x0)) / 2 - x0
        return Glyph(name, int(round(width)), translate(self.cs, dx, 0),
                     UNICODES.get(name))


# ------------------------------------------------------------ width model
def _dv(P: Params) -> float:
    """Stem increase over Light that drives the width model.  v4: a
    reduced-size parameter set (see params.small) keeps its parent's
    weight here, so a small C inside the copyright ring has the same
    proportions as the big one."""
    return (P.V_ref if P.V_ref is not None else P.V) - V_L


def ow(P: Params, W: float) -> float:
    """Outer ink width of a cap whose Light width is W."""
    return P.scale * (W + 0.8 * _dv(P))


def ccw(P: Params, base: float) -> float:
    """Cap counter whose Light value is base (outer grows 0.8 of the stem)."""
    return P.scale * (base - 1.2 * _dv(P))


def owl(P: Params, W: float) -> float:
    """Outer ink width of a lowercase shape whose Light width is W."""
    return P.scale * (W + 1.2 * _dv(P))


def cw(P: Params, base: float) -> float:
    """Lowercase counter whose Light value is base (outer grows 1.2 of the
    stem, so Bold counters stay open)."""
    return P.scale * (base - 0.8 * _dv(P))


BAR_C = 0.485   # cap-height fraction where the H/E/F/B bars centre


def bar_y(P, frac=BAR_C):
    """Bottom edge of a waist bar whose centre sits at frac of the cap."""
    return P.cap * frac - P.Hw / 2


def stem(P, x, y0, y1, w=None):
    return rect(x, y0, x + (w or P.V), y1, P.rs)


def bar(P, x0, x1, y, h=None):
    return rect(x0, y, x1, y + (h or P.H), P.rs)


def serif(P, xs, y, pos, kind, w=None, ov=None):
    """Hairline shelf serif at a stem whose left edge is xs and width w.
    pos: 'top' | 'bottom'; kind: 'both' | 'left' | 'right'."""
    w = w if w is not None else P.V
    ov = ov if ov is not None else P.serL
    x0 = xs - (ov if kind in ('both', 'left') else 0)
    x1 = xs + w + (ov if kind in ('both', 'right') else 0)
    if pos == 'bottom':
        return rect(x0, y, x1, y + P.ser, P.rs * 0.5)
    return rect(x0, y - P.ser, x1, y, P.rs * 0.5)


def lserif(P, xs, y, pos, kind, w=None):
    """Lowercase serif: the same shelf with the shorter overhang."""
    return serif(P, xs, y, pos, kind, w=w, ov=P.serL_lc)


def diag_serif(P, p, q, w, end, pos, kind, ov=None):
    """Serif under/over the flat end of a diagonal from p to q."""
    hx = diag_halfwidth(p, q, w, 'flat')
    x, y = end
    return serif(P, x - hx, y, pos, kind, w=2 * hx, ov=ov)


def dot(P, cx, y0, size=None):
    s = size or P.dot
    return rect(cx - s / 2, y0, cx + s / 2, y0 + s, s * 0.16)


def bowl_right(P, xs, xr, y0, y1, r, h=None):
    """Bowl attached to the right of a stem whose left edge is xs.
    h: horizontal stroke, or (top, bottom) for a bowl with a waist side."""
    return arc(xs, y0, xr, y1, (r, P.rs, P.rs, r), P.V, P.H if h is None else h,
               ('x', xs + P.V - 6, 'bottom'), ('x', xs + P.V - 6, 'top'), P.ri_min)


def bowl_left(P, xl, xs, y0, y1, r):
    """Bowl attached to the left of a stem whose left edge is xs."""
    return arc(xl, y0, xs + P.V, y1, (P.rs, r, r, P.rs), P.V, P.H,
               ('x', xs + 6, 'top'), ('x', xs + 6, 'bottom'), P.ri_min)


def half_bowl_radius(P, rmax, height):
    return min(rmax, 0.47 * height)


def inner_radius(P, r):
    """Inner corner radius geom.ring/arc will use for outer radius r."""
    from geom import INNER_SHRINK
    return max(r - INNER_SHRINK * (P.V + P.H) / 2, P.ri_min)


def hook_cut(P, y0, r):
    """Height of a level cut that sits on the straight part of both the
    outer and inner contour of a bottom hook whose box starts at y0 with
    corner radius r.  Keeps the three masters point-compatible."""
    return max(y0 + r, y0 + P.H + inner_radius(P, r)) + 8


def safe_y(P, y0, y1, r, want, h=None):
    """Clamp a level ('y') cut on the side of a ring box [y0, y1] with
    corner radius r so it lands on the straight part of both the outer
    and the inner contour at every weight."""
    h = P.H if h is None else h
    ri = inner_radius(P, r)
    top = min(y1 - r, y1 - h - ri) - 6
    bot = max(y0 + r, y0 + h + ri) + 6
    return min(max(want, bot), top)


def cap_terminals(P):
    """Level terminal heights for C and G: 0.727 cap at the top and
    0.273 at the bottom, as measured, pulled in where a heavy stroke
    would otherwise put the cut on the inner corner."""
    ri = inner_radius(P, P.rc)
    yt = min(P.cap * 0.727, P.cap + P.os - P.H - ri - 8)
    yb = max(P.cap * 0.273, -P.os + P.H + ri + 8)
    return yt, yb


# =============================================================== capitals
def g_I(P):
    b = B(P)
    x = P.sb_stem
    b.add(stem(P, x, 0, P.cap), serif(P, x, 0, 'bottom', 'both'),
          serif(P, x, P.cap, 'top', 'both'))
    return b.finish('I', P.sb_stem, edge=x + P.V)


def g_H(P):
    b = B(P)
    x1 = P.sb_stem
    x2 = x1 + ow(P, 552) - P.V
    b.add(stem(P, x1, 0, P.cap), stem(P, x2, 0, P.cap),
          serif(P, x1, 0, 'bottom', 'both'), serif(P, x1, P.cap, 'top', 'both'),
          serif(P, x2, 0, 'bottom', 'both'), serif(P, x2, P.cap, 'top', 'both'),
          bar(P, x1, x2 + P.V, bar_y(P), P.Hw))
    return b.finish('H', P.sb_stem, edge=x2 + P.V)


def g_E(P):
    """Top and bottom arms the same length, middle arm 36 shorter, all
    bars 0.85 of the stem; the middle bar centres on 0.485 cap."""
    b = B(P)
    x1 = P.sb_stem
    xr = x1 + ow(P, 494)
    b.add(stem(P, x1, 0, P.cap),
          bar(P, x1, xr, P.cap - P.H),
          bar(P, x1, xr - 36, bar_y(P), P.Hw),
          bar(P, x1, xr, 0),
          serif(P, x1, P.cap, 'top', 'left'), serif(P, x1, 0, 'bottom', 'left'))
    return b.finish('E', P.sb_bar)


def g_F(P):
    b = B(P)
    x1 = P.sb_stem
    xr = x1 + ow(P, 500)
    b.add(stem(P, x1, 0, P.cap),
          bar(P, x1, xr, P.cap - P.H),
          bar(P, x1, xr - 52, bar_y(P), P.Hw),
          serif(P, x1, P.cap, 'top', 'left'), serif(P, x1, 0, 'bottom', 'both'))
    return b.finish('F', P.sb_bar, edge=xr)


def g_L(P):
    b = B(P)
    x1 = P.sb_stem
    xr = x1 + ow(P, 480)
    b.add(stem(P, x1, 0, P.cap), bar(P, x1, xr, 0),
          serif(P, x1, P.cap, 'top', 'both'), serif(P, x1, 0, 'bottom', 'left'))
    return b.finish('L', P.sb_bar)


def g_T(P):
    b = B(P)
    tw = ow(P, 542)
    x0 = P.sb_bar
    xs = x0 + tw / 2 - P.V / 2
    b.add(bar(P, x0, x0 + tw, P.cap - P.H), stem(P, xs, 0, P.cap),
          serif(P, xs, 0, 'bottom', 'both'))
    return b.finish('T', P.sb_bar)


def g_B(P):
    """Lower bowl 16 wider than the upper one; the middle bar centres on
    0.485 cap and both bowls share it."""
    b = B(P)
    x1 = P.sb_stem
    ym = P.cap * BAR_C
    xr1 = x1 + ow(P, 541)
    xr2 = x1 + ow(P, 557)
    r1 = half_bowl_radius(P, P.rc * 0.85, P.cap - ym + P.Hw / 2)
    r2 = half_bowl_radius(P, P.rc * 0.85, ym + P.Hw / 2)
    b.add(stem(P, x1, 0, P.cap),
          bowl_right(P, x1, xr1, ym - P.Hw / 2, P.cap, r1, (P.H, P.Hw)),
          bowl_right(P, x1, xr2, 0, ym + P.Hw / 2, r2, (P.Hw, P.H)),
          serif(P, x1, P.cap, 'top', 'left'), serif(P, x1, 0, 'bottom', 'left'))
    return b.finish('B', P.sb_round)


def g_D(P):
    b = B(P)
    x1 = P.sb_stem
    xr = x1 + ow(P, 586)
    r = half_bowl_radius(P, P.rc, P.cap)
    b.add(stem(P, x1, 0, P.cap), bowl_right(P, x1, xr, 0, P.cap, r),
          serif(P, x1, P.cap, 'top', 'left'), serif(P, x1, 0, 'bottom', 'left'))
    return b.finish('D', P.sb_round)


def g_P(P):
    b = B(P)
    x1 = P.sb_stem
    yP = P.cap * 0.41
    xr = x1 + ow(P, 532)
    r = half_bowl_radius(P, P.rc * 0.85, P.cap - yP)
    b.add(stem(P, x1, 0, P.cap), bowl_right(P, x1, xr, yP, P.cap, r, (P.H, P.Hw)),
          serif(P, x1, P.cap, 'top', 'left'), serif(P, x1, 0, 'bottom', 'both'))
    return b.finish('P', P.sb_round)


def g_R(P):
    """R as in the wordmark, in every weight: a bowl whose bottom edge sits
    at 0.405 cap and a vertical leg flush with the bowl's right side.  The
    bowl's rounded bottom-right corner leaves a small notch above the leg.
    The leg's top drops as the stem grows, so the notch grows with the stroke
    and keeps its Light proportion; a fixed notch fills in and the R reads
    as an A."""
    b = B(P)
    x1 = P.sb_stem
    yP = P.cap * 0.405
    xr = x1 + ow(P, 546)
    r = half_bowl_radius(P, P.rc * 0.85, P.cap - yP)
    ytop = yP + P.H * 0.8 - 0.95 * _dv(P) * P.scale
    b.add(stem(P, x1, 0, P.cap), bowl_right(P, x1, xr, yP, P.cap, r, (P.H, P.Hw)),
          stem(P, xr - P.V, 0, ytop),
          serif(P, xr - P.V, 0, 'bottom', 'both'),
          serif(P, x1, P.cap, 'top', 'left'), serif(P, x1, 0, 'bottom', 'both'))
    return b.finish('R', P.sb_stem, edge=xr)


def g_C(P):
    b = B(P)
    x0 = P.sb_round
    w = ow(P, 583)
    yt, yb = cap_terminals(P)
    b.add(arc(x0, -P.os, x0 + w, P.cap + P.os, P.rc, P.V, P.H,
              ('y', yt, 'right'), ('y', yb, 'right'), P.ri_min))
    return b.finish('C', P.sb_term)


def g_G(P):
    """G: the top arm ends in a level cut at 0.727 cap; the bar sits at
    0.48 cap and runs in from the right side by 0.43 of the letter."""
    b = B(P)
    x0 = P.sb_round
    w = ow(P, 571)
    x1 = x0 + w
    yG = bar_y(P, 0.48)
    yt, _ = cap_terminals(P)
    b.add(arc(x0, -P.os, x1, P.cap + P.os, P.rc, P.V, P.H,
              ('y', yt, 'right'), ('y', yG, 'right'), P.ri_min),
          bar(P, x1 - P.V - ccw(P, 192), x1, yG, P.Hw))
    return b.finish('G', P.sb_round)


def g_O(P):
    b = B(P)
    x0 = P.sb_round
    w = ow(P, 583)
    b.add(ring(x0, -P.os, x0 + w, P.cap + P.os, P.rc, P.V, P.H, P.ri_min))
    return b.finish('O', P.sb_round)


def g_Q(P):
    b = B(P)
    x0 = P.sb_round
    w = ow(P, 583)
    x1 = x0 + w
    b.add(ring(x0, -P.os, x1, P.cap + P.os, P.rc, P.V, P.H, P.ri_min),
          diag((x1 - P.rc * 1.1, 130), (x1 + 20, -130), P.Vd))
    return b.finish('Q', P.sb_round)


def g_S(P):
    """S: two squared hooks sharing a flat spine centred on 0.514 cap.
    The upper half is inset 24 on the right, as in the wordmark; the top
    terminal ends at 0.727 cap, the bottom one starts at 0.266 cap."""
    b = B(P)
    x0 = P.sb_term
    w = ow(P, 546)
    x1 = x0 + w
    cx = (x0 + x1) / 2
    ym = P.cap * 0.514
    hu = P.cap + P.os - (ym - P.Hw / 2)
    hl = ym + P.Hw / 2 + P.os
    ru = half_bowl_radius(P, P.rc * 0.85, hu)
    rl = half_bowl_radius(P, P.rc * 0.85, hl)
    yt = safe_y(P, ym - P.Hw / 2, P.cap + P.os, ru, P.cap * 0.727)
    yb = safe_y(P, -P.os, ym + P.Hw / 2, rl, P.cap * 0.266)
    b.add(arc(x0, ym - P.Hw / 2, x1 - 24, P.cap + P.os, ru, P.V, (P.H, P.Hw),
              ('y', yt, 'right'), ('x', cx + 50, 'bottom'), P.ri_min),
          arc(x0, -P.os, x1, ym + P.Hw / 2, rl, P.V, (P.Hw, P.H),
              ('y', yb, 'left'), ('x', cx - 50, 'top'), P.ri_min))
    return b.finish('S', P.sb_term)


def g_U(P):
    b = B(P)
    x1 = P.sb_stem
    x2 = x1 + ow(P, 552) - P.V
    r = min(P.rc, (x2 + P.V - x1) / 2 - 1)
    b.add(arc(x1, -P.os, x2 + P.V, P.cap + P.H + 40, (1, 1, r, r), P.V, P.H,
              ('y', P.cap, 'left'), ('y', P.cap, 'right'), P.ri_min),
          serif(P, x1, P.cap, 'top', 'both'), serif(P, x2, P.cap, 'top', 'both'))
    return b.finish('U', P.sb_stem, edge=x2 + P.V)


def g_J(P):
    b = B(P)
    x0 = P.sb_term
    w = ow(P, 390)
    x1 = x0 + w
    r = min(P.rc, w / 2 - 1)
    b.add(arc(x0, -P.os, x1, P.cap + P.H + 40, (1, 1, r, r), P.V, P.H,
              ('y', safe_y(P, -P.os, P.cap, r, P.cap * 0.273), 'left'), ('y', P.cap, 'right'), P.ri_min),
          serif(P, x1 - P.V, P.cap, 'top', 'both'))
    return b.finish('J', P.sb_stem, edge=x1)


def _hx(P, dx, dy, w=None):
    w = w or P.Vd
    return (w / 2) * math.hypot(dx, dy) / abs(dy)


def g_A(P):
    b = B(P)
    span = ccw(P, 458) + P.V
    hx = _hx(P, span / 2, P.cap)
    xL = P.sb_diag + P.serL + hx
    xR = xL + span
    cx = xL + span / 2
    pL, pR, apex = (xL, 0), (xR, 0), (cx, P.cap)
    yb = 190
    xl = xL + (cx - xL) * (yb / P.cap)
    xr = xR - (xR - cx) * (yb / P.cap)
    b.add(diag(pL, apex, P.Vd), diag(pR, apex, P.Vd), bar(P, xl, xr, yb, P.Hw),
          diag_serif(P, pL, apex, P.Vd, pL, 'bottom', 'both'),
          diag_serif(P, pR, apex, P.Vd, pR, 'bottom', 'both'))
    return b.finish('A', P.sb_diag)


def g_V(P):
    b = B(P)
    span = ccw(P, 458) + P.V
    hx = _hx(P, span / 2, P.cap)
    xL = P.sb_diag + P.serL + hx
    xR = xL + span
    bot = (xL + span / 2, 0)
    pL, pR = (xL, P.cap), (xR, P.cap)
    b.add(diag(pL, bot, P.Vd), diag(pR, bot, P.Vd),
          diag_serif(P, pL, bot, P.Vd, pL, 'top', 'both'),
          diag_serif(P, pR, bot, P.Vd, pR, 'top', 'both'))
    return b.finish('V', P.sb_diag)


def g_W(P):
    b = B(P)
    u = (ccw(P, 304) + P.V) * 0.5
    hx = _hx(P, u, P.cap)
    x = P.sb_diag + P.serL + hx
    t0, b0, t1, b1, t2 = (x, P.cap), (x + u, 0), (x + 2 * u, P.cap), (x + 3 * u, 0), (x + 4 * u, P.cap)
    b.add(diag(t0, b0, P.Vd), diag(b0, t1, P.Vd), diag(t1, b1, P.Vd), diag(b1, t2, P.Vd),
          diag_serif(P, t0, b0, P.Vd, t0, 'top', 'both'),
          diag_serif(P, b1, t2, P.Vd, t2, 'top', 'both'))
    return b.finish('W', P.sb_diag)


def g_X(P):
    b = B(P)
    span = ccw(P, 418) + P.V
    hx = _hx(P, span, P.cap)
    xL = P.sb_diag + P.serL + hx
    xR = xL + span
    b.add(diag((xL, 0), (xR, P.cap), P.Vd), diag((xL, P.cap), (xR, 0), P.Vd))
    for p, pos in (((xL, 0), 'bottom'), ((xR, 0), 'bottom'), ((xL, P.cap), 'top'), ((xR, P.cap), 'top')):
        b.add(serif(P, p[0] - hx, p[1], pos, 'both', w=2 * hx))
    return b.finish('X', P.sb_diag)


def g_Y(P):
    b = B(P)
    span = ccw(P, 438) + P.V
    yj = P.cap * 0.46
    hx = _hx(P, span / 2, P.cap - yj)
    xL = P.sb_diag + P.serL + hx
    xR = xL + span
    cx = xL + span / 2
    pL, pR = (xL, P.cap), (xR, P.cap)
    jL, jR = (cx - P.V / 2 + hx, yj), (cx + P.V / 2 - hx, yj)
    b.add(diag(pL, jL, P.Vd), diag(pR, jR, P.Vd), stem(P, cx - P.V / 2, 0, yj + 2),
          diag_serif(P, pL, jL, P.Vd, pL, 'top', 'both'),
          diag_serif(P, pR, jR, P.Vd, pR, 'top', 'both'),
          serif(P, cx - P.V / 2, 0, 'bottom', 'both'))
    return b.finish('Y', P.sb_diag)


def _zed(P, name, x0, w, top):
    b = B(P)
    hx = _hx(P, w - 2 * P.Vd, top)   # first guess
    for _ in range(3):
        hx = _hx(P, w - 2 * hx, top)
    b.add(bar(P, x0, x0 + w, top - P.H), bar(P, x0, x0 + w + 6, 0),
          diag((x0 + hx, 0), (x0 + w - hx, top), P.Vd))
    return b.finish(name, P.sb_bar)


def g_Z(P):
    return _zed(P, 'Z', P.sb_bar, ccw(P, 428) + P.V, P.cap)


def g_K(P):
    """K as in the wordmark: the two arms' centre lines cross 159 units to
    the right of the stem at 0.517 cap, so between the stem and the arms
    there is a short horizontal neck one bar thick.  The lower arm reaches
    the letter's right edge at the baseline; the upper arm stops a little
    short of it at the top."""
    b = B(P)
    x1 = P.sb_stem
    xr = x1 + ow(P, 546)
    j = (x1 + P.V + ccw(P, 159), P.cap * 0.517)
    top = (xr - 69, P.cap)
    bot = (xr - 46, 0)
    wk = P.V * 1.02                      # the wordmark's arms are a full stem thick
    b.add(stem(P, x1, 0, P.cap), diag(j, top, wk), diag(j, bot, wk),
          bar(P, x1, j[0] + 10, j[1] - P.H / 2),
          serif(P, x1, 0, 'bottom', 'both'), serif(P, x1, P.cap, 'top', 'both'),
          diag_serif(P, j, top, wk, top, 'top', 'both'),
          diag_serif(P, j, bot, wk, bot, 'bottom', 'both'))
    return b.finish('K', P.sb_diag + 16, edge=xr)


def g_M(P):
    b = B(P)
    x1 = P.sb_stem
    x2 = x1 + P.V + ccw(P, 458)
    cx = (x1 + x2 + P.V) / 2
    yv = 90
    b.add(stem(P, x1, 0, P.cap), stem(P, x2, 0, P.cap),
          diag((x1 + P.V / 2, P.cap), (cx, yv), P.Vd),
          diag((x2 + P.V / 2, P.cap), (cx, yv), P.Vd),
          serif(P, x1, P.cap, 'top', 'left'), serif(P, x2, P.cap, 'top', 'right'),
          serif(P, x1, 0, 'bottom', 'both'), serif(P, x2, 0, 'bottom', 'both'))
    return b.finish('M', P.sb_stem, edge=x2 + P.V)


def g_N(P):
    b = B(P)
    x1 = P.sb_stem
    x2 = x1 + P.V + ccw(P, 328)
    b.add(stem(P, x1, 0, P.cap), stem(P, x2, 0, P.cap),
          diag((x1 + P.V / 2, P.cap), (x2 + P.V / 2, 0), P.Vd),
          serif(P, x1, P.cap, 'top', 'both'), serif(P, x1, 0, 'bottom', 'both'),
          serif(P, x2, P.cap, 'top', 'both'), serif(P, x2, 0, 'bottom', 'both'))
    return b.finish('N', P.sb_stem, edge=x2 + P.V)


# ============================================================== lowercase
def arch(P, xs, xr, y_top, y_join):
    """n-style arch: from the baseline on the right, over the top, into the
    stem on the left at y_join.

    v4: the ring box runs on below the baseline, so the baseline cut lands
    on the straight part of the inner contour as well as the outer one and
    the leg ends in a level foot.  v3's box stopped 2 units under the
    baseline, which put the inner cut on the ring's bottom corner and left
    a wedge under the serif of n, m and h."""
    return arc(xs, -(P.H + 40), xr, y_top + P.os, (P.rx, P.rx, 0, 0), P.V, P.H,
               ('y', 0, 'right'), ('y', y_join, 'left'), P.ri_min)


def g_n(P):
    b = B(P)
    x1 = P.sb_stem
    x2 = x1 + P.V + cw(P, 220)
    b.add(stem(P, x1, 0, P.xh), arch(P, x1, x2 + P.V, P.xh, P.xh * 0.45),
          lserif(P, x1, P.xh, 'top', 'left'), lserif(P, x1, 0, 'bottom', 'both'),
          lserif(P, x2, 0, 'bottom', 'both'))
    return b.finish('n', P.sb_stem, edge=x2 + P.V)


def g_h(P):
    b = B(P)
    x1 = P.sb_stem
    x2 = x1 + P.V + cw(P, 220)
    b.add(stem(P, x1, 0, P.asc), arch(P, x1, x2 + P.V, P.xh, P.xh * 0.45),
          lserif(P, x1, P.asc, 'top', 'left'), lserif(P, x1, 0, 'bottom', 'both'),
          lserif(P, x2, 0, 'bottom', 'both'))
    return b.finish('h', P.sb_stem, edge=x2 + P.V)


def g_m(P):
    """m: outer stems carry full shelves, the middle stem only a short
    one, so the baseline is not a row of six ticks."""
    b = B(P)
    x1 = P.sb_stem
    g = cw(P, 199)
    x2 = x1 + P.V + g
    x3 = x2 + P.V + g
    b.add(stem(P, x1, 0, P.xh), arch(P, x1, x2 + P.V, P.xh, P.xh * 0.45),
          arch(P, x2, x3 + P.V, P.xh, P.xh * 0.45),
          lserif(P, x1, P.xh, 'top', 'left'), lserif(P, x1, 0, 'bottom', 'both'),
          serif(P, x2, 0, 'bottom', 'both', ov=P.serL_lc * 0.6),
          lserif(P, x3, 0, 'bottom', 'both'))
    return b.finish('m', P.sb_stem, edge=x3 + P.V)


def g_u(P):
    b = B(P)
    x1 = P.sb_stem
    x2 = x1 + P.V + cw(P, 220)
    b.add(arc(x1, -P.os, x2 + P.V, P.xh + P.H + 40, (1, 1, P.rx, P.rx), P.V, P.H,
              ('y', P.xh, 'left'), ('y', P.xh, 'right'), P.ri_min),
          stem(P, x2, 0, P.xh),
          lserif(P, x1, P.xh, 'top', 'left'), lserif(P, x2, P.xh, 'top', 'left'),
          lserif(P, x2, 0, 'bottom', 'both'))
    return b.finish('u', P.sb_stem, edge=x2 + P.V)


def g_o(P):
    b = B(P)
    x0 = P.sb_round
    w = cw(P, 202) + 2 * P.V
    b.add(ring(x0, -P.os, x0 + w, P.xh + P.os, P.rx, P.V, P.H, P.ri_min))
    return b.finish('o', P.sb_round)


def g_b(P):
    b = B(P)
    xs = P.sb_stem
    w = cw(P, 214)
    b.add(stem(P, xs, 0, P.asc), bowl_right(P, xs, xs + 2 * P.V + w, 0, P.xh, P.rx),
          lserif(P, xs, P.asc, 'top', 'left'))
    return b.finish('b', P.sb_round)


def g_p(P):
    b = B(P)
    xs = P.sb_stem
    w = cw(P, 214)
    b.add(stem(P, xs, P.desc, P.xh), bowl_right(P, xs, xs + 2 * P.V + w, 0, P.xh, P.rx),
          lserif(P, xs, P.xh, 'top', 'left'), lserif(P, xs, P.desc, 'bottom', 'both'))
    return b.finish('p', P.sb_round)


def g_d(P):
    b = B(P)
    x0 = P.sb_round
    xs = x0 + P.V + cw(P, 214)
    b.add(bowl_left(P, x0, xs, 0, P.xh, P.rx), stem(P, xs, 0, P.asc),
          lserif(P, xs, P.asc, 'top', 'left'), lserif(P, xs, 0, 'bottom', 'both'))
    return b.finish('d', P.sb_stem, edge=xs + P.V)


def g_q(P):
    b = B(P)
    x0 = P.sb_round
    xs = x0 + P.V + cw(P, 214)
    b.add(bowl_left(P, x0, xs, 0, P.xh, P.rx), stem(P, xs, P.desc, P.xh),
          lserif(P, xs, P.desc, 'bottom', 'both'))
    return b.finish('q', P.sb_stem, edge=xs + P.V)


def g_a(P):
    """a: double-storey, squared bowl, shelf foot.  In Bold the bowl grows
    and its horizontals thin so the counter stays at least 112 tall; the
    hook's terminal rises with the bowl to keep the aperture.  Every relief
    term is zero in Light and Regular."""
    b = B(P)
    dv = P.relief * P.scale    # zero at Light and Regular
    x0 = P.sb_round
    xs = x0 + P.V + cw(P, 194) + 0.65 * dv
    ya = P.xh * 0.60 + 0.3 * dv
    ra = min(P.rx * 0.8, 0.47 * ya)
    rh = P.rx * 0.9
    # bowl horizontals thin out in Bold so the small counter stays open:
    # at least 70 tall at Light (unchanged), 112 at Bold
    hb = min(P.H, (ya - 70 - 0.78 * dv) / 2)
    yb = ya - 60 - P.H
    b.add(arc(x0, 0, xs + P.V, ya, (P.rs, ra, ra, P.rs), P.V, hb,
              ('x', xs + 6, 'top'), ('x', xs + 6, 'bottom'), P.ri_min),
          stem(P, xs, 0, P.xh * 0.8),
          arc(x0 + 10, yb, xs + P.V, P.xh + P.os, (rh, rh, 1, 1), P.V, P.H,
              ('y', yb + P.H * 0.5, 'right'),
              ('y', safe_y(P, yb, P.xh + P.os, rh, P.xh * 0.68 + 0.3 * dv), 'left'), P.ri_min),
          serif(P, xs, 0, 'bottom', 'right', ov=P.serL_lc * 0.6))
    return b.finish('a', P.sb_stem, edge=xs + P.V)


def g_g(P):
    b = B(P)
    x0 = P.sb_round
    xs = x0 + P.V + cw(P, 210)
    rg = min(P.rx * 0.75, 0.48 * (0 - (P.desc - P.os)))
    yg0 = P.desc - P.os
    b.add(bowl_left(P, x0, xs, 0, P.xh, P.rx),
          stem(P, xs, -56, P.xh),
          arc(x0 + 10, yg0, xs + P.V, P.H + 70, (1, 1, rg, rg), P.V, P.H,
              ('y', hook_cut(P, yg0, rg), 'left'), ('y', -28, 'right'), P.ri_min),
          serif(P, xs, P.xh, 'top', 'right', ov=P.serL_lc * 0.8))
    return b.finish('g', P.sb_stem, edge=xs + P.V)


def g_c(P):
    b = B(P)
    x0 = P.sb_round
    w = cw(P, 196) + 2 * P.V
    yt = safe_y(P, -P.os, P.xh + P.os, P.rx, P.xh + P.os - P.rx - 16)
    yb = safe_y(P, -P.os, P.xh + P.os, P.rx, -P.os + P.rx + 16)
    b.add(arc(x0, -P.os, x0 + w, P.xh + P.os, P.rx, P.V, P.H,
              ('y', yt, 'right'), ('y', yb, 'right'), P.ri_min))
    return b.finish('c', P.sb_term)


def g_e(P):
    b = B(P)
    x0 = P.sb_round
    w = cw(P, 202) + 2 * P.V + 0.65 * P.relief * P.scale
    x1 = x0 + w
    he = min(P.Hw, P.xh - 2 * P.H - 130)   # Bold: thinner bar, open counters
    yb = (P.xh - he) / 2 + 10
    b.add(arc(x0, -P.os, x1, P.xh + P.os, P.rx, P.V, P.H,
              ('y', yb, 'right'), ('a', 318), P.ri_min),
          bar(P, x0 + P.V - 4, x1 - P.V + 4, yb, he))
    return b.finish('e', P.sb_term)


def g_s(P):
    b = B(P)
    x0 = P.sb_term
    w = cw(P, 188) + 2 * P.V
    x1 = x0 + w
    cx = (x0 + x1) / 2
    ym = P.xh * 0.5
    hu = P.xh + P.os - (ym - P.Hw / 2)
    hl = ym + P.Hw / 2 + P.os
    ru = half_bowl_radius(P, P.rx * 0.85, hu)
    rl = half_bowl_radius(P, P.rx * 0.85, hl)
    yt = safe_y(P, ym - P.Hw / 2, P.xh + P.os, ru, P.xh + P.os - ru - 14)
    yb = safe_y(P, -P.os, ym + P.Hw / 2, rl, -P.os + rl + 14)
    b.add(arc(x0 + 10, ym - P.Hw / 2, x1 - 14, P.xh + P.os, ru, P.V, (P.H, P.Hw),
              ('y', yt, 'right'), ('x', cx + 34, 'bottom'), P.ri_min),
          arc(x0, -P.os, x1, ym + P.Hw / 2, rl, P.V, (P.Hw, P.H),
              ('y', yb, 'left'), ('x', cx - 34, 'top'), P.ri_min))
    return b.finish('s', P.sb_term)


def g_f(P):
    b = B(P)
    xs = P.sb_stem + 30          # the crossbar reaches 50 left of the stem
    # v4: the hook's terminal is a plumb cut at xt.  The ring box is wide
    # enough that xt sits on the straight top of both contours (v3 cut the
    # inner contour on its corner, which slanted the terminal).
    xt = xs + P.V + cw(P, 110) + 0.3 * (P.V - V_L)   # same reach as v3
    # only the part left of xt is drawn, so the box may be wider than the
    # hook; it must stay wider than two stems or the inner contour inverts
    rf = P.rx * 0.85
    ri = inner_radius(P, rf)
    hw = max(xt - xs + P.V + ri + 6, 2 * P.V + 2 * ri + 10, 2 * rf + 2)
    b.add(stem(P, xs, 0, P.xh + 60),
          arc(xs, P.xh - 150, xs + hw, P.asc + P.os, (rf, rf, 0, 0), P.V, P.H,
              ('x', xt, 'top'), ('y', P.xh + 30, 'left'), P.ri_min),
          bar(P, xs - 50, xs + P.V + cw(P, 136), P.xh - P.H),
          lserif(P, xs, 0, 'bottom', 'both'))
    return b.finish('f', P.sb_term)


def g_t(P):
    b = B(P)
    xs = P.sb_bar + 54
    yt = P.xh * 0.45
    xterm = xs + P.V + cw(P, 130)
    rt = min(P.rx * 0.7, 0.48 * (yt + P.os))
    # the box top is never drawn (the arc stops at yt on the left); it only
    # has to leave the inner contour a straight left side at yt in Bold
    ytop = P.xh * 0.75 + 0.6 * (P.V - V_L)
    # v4: the box runs past the terminal by a stem plus the inner corner so
    # the plumb cut at xterm sits on the straight bottom of both contours
    b.add(stem(P, xs, yt - 10, P.xh + 120),
          arc(xs, -P.os, xterm + P.V + P.ri_min + 4, ytop, (0, 0, rt, 0), P.V, P.H,
              ('y', yt - 1, 'left'), ('x', xterm, 'bottom'), P.ri_min),
          bar(P, xs - 54, xs + P.V + cw(P, 116), P.xh - P.H))
    return b.finish('t', P.sb_term)


def g_r(P):
    b = B(P)
    xs = P.sb_stem
    hw = 2 * P.V + max(cw(P, 98), 40)       # the hook keeps a counter in Bold
    rr_ = min(P.rx * 0.85, hw / 2 - 1)
    yj = P.xh * 0.35 - 0.4 * (P.V - V_L)     # Bold: deeper hook, open counter
    # the terminal cut must sit on the straight part of the inner contour
    # too, which the Bold stroke pushes down
    ri = inner_radius(P, rr_)
    yc = min(max(P.xh + P.os - rr_ - 60, yj + P.H + ri + 8), P.xh + P.os - P.H - ri - 8)
    b.add(stem(P, xs, 0, P.xh),
          arc(xs, yj, xs + hw, P.xh + P.os, (rr_, rr_, 1, 1), P.V, P.H,
              ('y', yc, 'right'), ('y', yj + P.H * 0.5, 'left'), P.ri_min),
          lserif(P, xs, P.xh, 'top', 'left'), lserif(P, xs, 0, 'bottom', 'both'))
    return b.finish('r', 24)


def g_i(P):
    b = B(P)
    xs = P.sb_stem
    b.add(stem(P, xs, 0, P.xh), lserif(P, xs, P.xh, 'top', 'left'),
          lserif(P, xs, 0, 'bottom', 'both'), dot(P, xs + P.V / 2, P.xh + 96))
    return b.finish('i', P.sb_stem, edge=xs + P.V)


def g_l(P):
    b = B(P)
    xs = P.sb_stem
    b.add(stem(P, xs, 0, P.asc), lserif(P, xs, P.asc, 'top', 'left'),
          lserif(P, xs, 0, 'bottom', 'both'))
    return b.finish('l', P.sb_stem, edge=xs + P.V)


def g_j(P):
    """j: the stem sits 16 right of where i's does, and a
    squared L-hook runs left under the baseline to x = -40, so the i-j
    gap matches i-i instead of carrying the whole hook as a sidebearing."""
    b = B(P)
    xs = P.sb_stem + 16
    xcut = -40                      # the hook's plumb terminal
    # v4: the ring box runs a stem past the terminal so the cut sits on
    # the straight bottom of both contours (v3 cut the inner on its corner
    # and the hook ended in a slant)
    x0 = xcut - P.V - 6
    rj = min(P.rx * 0.8, 0.48 * (xs + P.V - xcut) / 2)
    yj0 = P.desc - P.os
    b.add(stem(P, xs, -56, P.xh),
          arc(x0, yj0, xs + P.V, P.H + 70, (0, 0, 0, rj), P.V, P.H,
              ('x', xcut, 'bottom'), ('y', -20, 'right'), P.ri_min),
          lserif(P, xs, P.xh, 'top', 'left'), dot(P, xs + P.V / 2, P.xh + 96))
    return b.finish('j', P.sb_stem, edge=xs + P.V)


def g_k(P):
    b = B(P)
    xs = P.sb_stem
    yk = P.xh * 0.47
    j = (xs + P.V / 2, yk)
    j2 = (xs + P.V / 2 + 14, yk)
    # Bold: the arms reach further so the lower one clears the stem
    top = (xs + P.V + cw(P, 190) + 0.9 * P.relief * P.scale, P.xh)
    bot = (top[0] + 22 + 0.5 * P.relief * P.scale, 0)
    wa = P.Vd - 0.3 * P.relief * P.scale
    # the arms start in plumb cuts inside the stem; a level cut stuck out
    # to the left of it as a spike
    b.add(stem(P, xs, 0, P.asc), diag(j, top, wa, 'vert'), diag(j2, bot, wa, 'vert'),
          lserif(P, xs, P.asc, 'top', 'left'), lserif(P, xs, 0, 'bottom', 'both'),
          diag_serif(P, j2, bot, wa, bot, 'bottom', 'both', ov=P.serL_lc))
    return b.finish('k', P.sb_diag)


def g_v(P):
    b = B(P)
    span = cw(P, 274) + P.V
    hx = _hx(P, span / 2, P.xh)
    xL = P.sb_diag + P.serL_lc + hx
    xR = xL + span
    bot = (xL + span / 2, 0)
    pL, pR = (xL, P.xh), (xR, P.xh)
    b.add(diag(pL, bot, P.Vd), diag(pR, bot, P.Vd),
          diag_serif(P, pL, bot, P.Vd, pL, 'top', 'both', ov=P.serL_lc),
          diag_serif(P, pR, bot, P.Vd, pR, 'top', 'both', ov=P.serL_lc))
    return b.finish('v', P.sb_diag)


def g_w(P):
    b = B(P)
    u = (cw(P, 232) + P.V) * 0.5
    hx = _hx(P, u, P.xh)
    x = P.sb_diag + P.serL_lc + hx
    t0, b0, t1, b1, t2 = (x, P.xh), (x + u, 0), (x + 2 * u, P.xh), (x + 3 * u, 0), (x + 4 * u, P.xh)
    b.add(diag(t0, b0, P.Vd), diag(b0, t1, P.Vd), diag(t1, b1, P.Vd), diag(b1, t2, P.Vd),
          diag_serif(P, t0, b0, P.Vd, t0, 'top', 'both', ov=P.serL_lc),
          diag_serif(P, b1, t2, P.Vd, t2, 'top', 'both', ov=P.serL_lc))
    return b.finish('w', P.sb_diag)


def g_x(P):
    b = B(P)
    span = cw(P, 260) + P.V
    hx = _hx(P, span, P.xh)
    xL = P.sb_diag + P.serL_lc + hx
    xR = xL + span
    b.add(diag((xL, 0), (xR, P.xh), P.Vd), diag((xL, P.xh), (xR, 0), P.Vd))
    for p, pos in (((xL, 0), 'bottom'), ((xR, 0), 'bottom'), ((xL, P.xh), 'top'), ((xR, P.xh), 'top')):
        b.add(serif(P, p[0] - hx, p[1], pos, 'both', w=2 * hx, ov=P.serL_lc))
    return b.finish('x', P.sb_diag)


def g_y(P):
    b = B(P)
    span = cw(P, 274) + P.V
    hx = _hx(P, span / 2, P.xh)
    xL = P.sb_diag + P.serL_lc + hx
    xR = xL + span
    cx = xL + span / 2
    pR = (xR, P.xh)
    # right stroke passes through (cx, 60) and continues to the descender
    k = (P.xh - P.desc) / (P.xh - 60)
    tail = (xR + (cx - xR) * k, P.desc)
    pL = (xL, P.xh)
    jL = (cx, 60)   # same slope as the right stroke, so the cuts coincide
    b.add(diag(pR, tail, P.Vd), diag(pL, jL, P.Vd),
          diag_serif(P, pL, jL, P.Vd, pL, 'top', 'both', ov=P.serL_lc),
          diag_serif(P, pR, tail, P.Vd, pR, 'top', 'both', ov=P.serL_lc),
          diag_serif(P, pR, tail, P.Vd, tail, 'bottom', 'left', ov=P.serL_lc * 1.1))
    return b.finish('y', P.sb_diag)


def g_z(P):
    return _zed(P, 'z', P.sb_bar, cw(P, 258) + P.V, P.xh)


# ================================================================ figures
def fig_width(P):
    return 440 * P.scale + P.V


def fig_w(P):
    return ccw(P, 250) + 2 * P.V


def fig_finish(b, name, P, prop, lsb, rsb):
    """v4: tabular figures are centred in the common figure width; the
    proportional variants (name.pnum) take ink sidebearings instead."""
    if not prop:
        return b.finish_centered(name, fig_width(P))
    x0, y0, x1, y1 = bbox(b.cs)
    cs = translate(b.cs, lsb - x0, 0)
    return Glyph(name + '.pnum', int(round(x1 - x0 + lsb + rsb)), cs, None)


def g_zero(P, prop=False):
    b = B(P)
    w = fig_w(P)
    b.add(ring(0, -P.os, w, P.cap + P.os, P.rc * 0.9, P.V, P.H, P.ri_min))
    return fig_finish(b, 'zero', P, prop, P.sb_round, P.sb_round)


def g_one(P, prop=False):
    b = B(P)
    xs = 200 * P.scale
    p, q = (xs + 10, P.cap), (xs - 0.157 * P.cap, P.cap - 0.186 * P.cap)
    b.add(stem(P, xs, 0, P.cap), diag(p, q, P.Vd * 0.92),
          serif(P, xs, 0, 'bottom', 'both'))
    return fig_finish(b, 'one', P, prop, 30, P.sb_stem)


def g_two(P, prop=False):
    b = B(P)
    w = fig_w(P)
    x0, x1 = 0, w
    y0 = P.cap * 0.42
    r = half_bowl_radius(P, P.rc * 0.85, P.cap + P.os - y0)
    yr = y0 + r + 2
    top = (x1 - P.V / 2 - 12, yr + 46)
    hx = _hx(P, top[0] - x0, top[1])
    for _ in range(3):
        hx = _hx(P, top[0] - (x0 + hx), top[1])
    b.add(arc(x0, y0, x1, P.cap + P.os, r, P.V, P.H, ('y', safe_y(P, y0, P.cap + P.os, r, yr), 'right'),
              ('y', safe_y(P, y0, P.cap + P.os, r, P.cap + P.os - r - 16), 'left'), P.ri_min),
          diag((x0 + hx, 0), top, P.Vd), bar(P, x0, x1, 0))
    return fig_finish(b, 'two', P, prop, P.sb_round, P.sb_bar)


def g_three(P, prop=False):
    b = B(P)
    w = fig_w(P)
    x0, x1 = 0, w
    ym = P.cap * 0.52
    hu = P.cap + P.os - (ym - P.Hw / 2)
    hl = ym + P.Hw / 2 + P.os
    ru = half_bowl_radius(P, P.rc * 0.85, hu)
    rl = half_bowl_radius(P, P.rc * 0.85, hl)
    xm = max(x0 + 0.42 * w, x0 + 12 + P.V + inner_radius(P, ru) + 6)
    yt = min(P.cap + P.os - ru - 14, P.cap + P.os - P.H - inner_radius(P, ru) - 8)
    b.add(arc(x0 + 12, ym - P.Hw / 2, x1 - 8, P.cap + P.os, ru, P.V, (P.H, P.Hw),
              ('x', xm, 'bottom'), ('y', yt, 'left'), P.ri_min),
          arc(x0, -P.os, x1, ym + P.Hw / 2, rl, P.V, (P.Hw, P.H),
              ('y', safe_y(P, -P.os, ym + P.Hw / 2, rl, -P.os + rl + 14), 'left'), ('x', xm, 'top'), P.ri_min))
    return fig_finish(b, 'three', P, prop, P.sb_term, P.sb_round)


def g_four(P, prop=False):
    b = B(P)
    w = ccw(P, 260) + 2 * P.V
    x0, x1 = 0, w
    xs = x1 - P.V - 52
    yb = P.cap * 0.27
    top = (xs + P.V / 2, P.cap)
    hx = _hx(P, top[0] - x0, P.cap - yb)
    for _ in range(3):
        hx = _hx(P, top[0] - (x0 + hx), P.cap - yb)
    b.add(stem(P, xs, 0, P.cap), bar(P, x0, x1, yb), diag((x0 + hx, yb), top, P.Vd),
          serif(P, xs, 0, 'bottom', 'both'))
    return fig_finish(b, 'four', P, prop, 26, P.sb_bar)


def g_five(P, prop=False):
    b = B(P)
    w = fig_w(P)
    x0, x1 = 0, w
    yb1 = P.cap * 0.60
    r = half_bowl_radius(P, P.rc * 0.85, yb1 + P.os)
    b.add(bar(P, x0, x1 - 20, P.cap - P.H), stem(P, x0, yb1 - P.H - 10, P.cap),
          arc(x0, -P.os, x1, yb1, r, P.V, (P.Hw, P.H), ('y', safe_y(P, -P.os, yb1, r, -P.os + r + 14), 'left'),
              ('x', x0 + P.V / 2, 'top'), P.ri_min))
    return fig_finish(b, 'five', P, prop, P.sb_bar, P.sb_round)


def _six(P):
    w = fig_w(P)
    x0, x1 = 0, w
    r6 = P.rc * 0.9
    yb = P.cap * 0.60
    rb = half_bowl_radius(P, r6, yb + P.os)
    return [
        arc(x0, -P.os, x1, P.cap + P.os, r6, P.V, P.H,
            ('y', safe_y(P, -P.os, P.cap + P.os, r6, P.cap + P.os - r6 - 20), 'right'),
            ('y', P.cap * 0.33, 'left'), P.ri_min),
        *ring(x0, -P.os, x1, yb, rb, P.V, (P.Hw, P.H), P.ri_min),
    ]


def g_six(P, prop=False):
    b = B(P)
    b.add(_six(P))
    return fig_finish(b, 'six', P, prop, P.sb_round, P.sb_round)


def g_nine(P, prop=False):
    b = B(P)
    cs = _six(P)
    x0, y0, x1, y1 = bbox(cs)
    b.add(rotate180(cs, (x0 + x1) / 2, P.cap / 2))
    return fig_finish(b, 'nine', P, prop, P.sb_round, P.sb_round)


def g_seven(P, prop=False):
    b = B(P)
    w = fig_w(P)
    x0, x1 = 0, w
    bot = (x0 + 0.34 * w, 0)
    hx = _hx(P, x1 - bot[0], P.cap)
    for _ in range(3):
        hx = _hx(P, x1 - hx - bot[0], P.cap)
    b.add(bar(P, x0, x1, P.cap - P.H), diag((x1 - hx, P.cap), bot, P.Vd))
    return fig_finish(b, 'seven', P, prop, P.sb_bar, 30)


def g_eight(P, prop=False):
    """8: two rings sharing the waist stroke.  In Bold the figure widens
    and its stems give up a little, so both counters stay open (the tabular
    8 still fits its advance)."""
    b = B(P)
    dv = P.relief * P.scale
    w = fig_w(P) + 0.5 * dv
    v8 = P.V - 0.12 * dv
    x0, x1 = 0, w
    ym = P.cap * 0.52
    hu = P.cap + P.os - (ym - P.Hw / 2)
    hl = ym + P.Hw / 2 + P.os
    ru = half_bowl_radius(P, P.rc * 0.85, hu)
    rl = half_bowl_radius(P, P.rc * 0.85, hl)
    b.add(ring(x0 + 14, ym - P.Hw / 2, x1 - 14, P.cap + P.os, ru, v8, (P.H, P.Hw), P.ri_min),
          ring(x0, -P.os, x1, ym + P.Hw / 2, rl, v8, (P.Hw, P.H), P.ri_min))
    return fig_finish(b, 'eight', P, prop, P.sb_round, P.sb_round)


# ============================================================ punctuation
def g_space(P):
    return Glyph('space', 260, [], 0x20)


def g_period(P):
    b = B(P)
    b.add(dot(P, 60 + P.dot / 2, 0))
    return b.finish('period', 60)


def comma_tail(P, cx):
    return diag((cx + P.dot * 0.08, P.dot * 0.35), (cx - P.dot * 0.28, -P.dot * 1.05),
                P.dot * 0.42)


def g_comma(P):
    b = B(P)
    cx = 60 + P.dot / 2
    b.add(dot(P, cx, 0), comma_tail(P, cx))
    return b.finish('comma', 60)


def g_colon(P):
    b = B(P)
    cx = 60 + P.dot / 2
    b.add(dot(P, cx, 0), dot(P, cx, P.xh - P.dot))
    return b.finish('colon', 60)


def g_semicolon(P):
    b = B(P)
    cx = 60 + P.dot / 2
    b.add(dot(P, cx, 0), comma_tail(P, cx), dot(P, cx, P.xh - P.dot))
    return b.finish('semicolon', 60)


def g_exclam(P):
    b = B(P)
    cx = 60 + P.dot / 2
    b.add(dot(P, cx, 0), stem(P, cx - P.V / 2, P.dot + 70, P.cap))
    return b.finish('exclam', 60)


def g_question(P):
    b = B(P)
    x0 = P.sb_round
    w = ccw(P, 218) + 2 * P.V
    x1 = x0 + w
    ym = P.cap * 0.45
    r = half_bowl_radius(P, P.rc * 0.85, P.cap + P.os - ym)
    xq = (x0 + x1) / 2 - P.V / 2
    b.add(arc(x0, ym, x1, P.cap + P.os, r, P.V, P.H, ('x', xq + P.V * 0.55, 'bottom'),
              ('y', safe_y(P, ym, P.cap + P.os, r, 505), 'left'), P.ri_min),
          stem(P, xq, P.dot + 70, ym + P.H), dot(P, xq + P.V / 2, 0))
    return b.finish('question', P.sb_round)


def g_quotesingle(P):
    b = B(P)
    b.add(rect(60, P.cap - 220, 60 + P.V * 0.95, P.cap + 16, P.rs))
    return b.finish('quotesingle', 60)


def g_quotedbl(P):
    b = B(P)
    w = P.V * 0.95
    gap = P.V * 0.95
    b.add(rect(60, P.cap - 220, 60 + w, P.cap + 16, P.rs),
          rect(60 + w + gap, P.cap - 220, 60 + 2 * w + gap, P.cap + 16, P.rs))
    return b.finish('quotedbl', 60)


def g_hyphen(P):
    b = B(P)
    hy = P.xh * 0.5 + 12
    b.add(rect(40, hy - P.H / 2, 40 + cw(P, 230) + P.V * 0.6, hy + P.H / 2, P.rs))
    return b.finish('hyphen', 40)


def g_parenleft(P):
    b = B(P)
    x0 = P.sb_term
    pw = 2 * P.V + cw(P, 98)            # keeps an inner contour in Bold
    x1 = x0 + pw
    r = min(P.rc * 0.9, pw / 2 - 1)
    # the terminals are perpendicular cuts on the corners, which keeps the
    # cut on the same segment of both contours at every weight
    b.add(arc(x0, P.desc - 10, x1, P.asc + 10, r, P.V, P.H,
              ('a', 64), ('a', 296), P.ri_min))
    return b.finish('parenleft', 30)


def g_parenright(P):
    g = g_parenleft(P)
    cs = mirror_x(g.contours, g.width / 2)
    return Glyph('parenright', g.width, cs, UNICODES['parenright'])


def g_bracketleft(P):
    b = B(P)
    x0 = P.sb_term
    bw = cw(P, 168) + P.V
    b.add(stem(P, x0, P.desc - 10, P.asc + 10),
          bar(P, x0, x0 + bw, P.asc + 10 - P.H), bar(P, x0, x0 + bw, P.desc - 10))
    return b.finish('bracketleft', 30)


def g_bracketright(P):
    g = g_bracketleft(P)
    cs = mirror_x(g.contours, g.width / 2)
    return Glyph('bracketright', g.width, cs, UNICODES['bracketright'])


def g_slash(P):
    b = B(P)
    w = cw(P, 248) + P.V
    hx = _hx(P, w, P.cap - P.desc)
    for _ in range(3):
        hx = _hx(P, w - 2 * hx, P.cap + 10 - (P.desc + 30))
    b.add(diag((P.sb_diag + hx, P.desc + 30), (P.sb_diag + w - hx, P.cap + 10), P.Vd))
    return b.finish('slash', P.sb_diag)


def g_bar(P):
    """Vertical bar, full ascender-to-descender."""
    b = B(P)
    x0 = 80
    b.add(rect(x0, P.desc - 30, x0 + P.V * 0.9, P.asc + 30, P.rs))
    return b.finish('bar', 80)


def g_underscore(P):
    b = B(P)
    b.add(rect(10, -P.H * 1.6, 10 + cw(P, 388) + 2 * P.V, -P.H * 0.6, P.rs))
    return b.finish('underscore', 10)


def g_numbersign(P):
    b = B(P)
    vn = P.V * 0.82
    hn = P.H * 0.95
    w = cw(P, 328) + 2 * vn
    x0 = P.sb_bar
    xa = x0 + w * 0.30 - vn / 2
    xb = x0 + w * 0.70 - vn / 2
    y1 = P.cap * 0.30
    y2 = P.cap * 0.64
    b.add(rect(xa, 0, xa + vn, P.cap, P.rs), rect(xb, 0, xb + vn, P.cap, P.rs),
          rect(x0, y1, x0 + w, y1 + hn, P.rs), rect(x0, y2, x0 + w, y2 + hn, P.rs))
    return b.finish('numbersign', P.sb_bar)


def math_center(P):
    return P.xh * 0.5 + 12


def g_plus(P):
    b = B(P)
    cy = math_center(P)
    aw = cw(P, 318) + P.V
    x0 = P.sb_bar
    b.add(rect(x0, cy - P.H / 2, x0 + aw, cy + P.H / 2, P.rs),
          rect(x0 + aw / 2 - P.H / 2, cy - aw / 2, x0 + aw / 2 + P.H / 2, cy + aw / 2, P.rs))
    return b.finish('plus', P.sb_bar)


def g_equal(P):
    b = B(P)
    cy = math_center(P)
    aw = cw(P, 318) + P.V
    x0 = P.sb_bar
    gap = P.H * 1.3
    b.add(rect(x0, cy + gap / 2, x0 + aw, cy + gap / 2 + P.H, P.rs),
          rect(x0, cy - gap / 2 - P.H, x0 + aw, cy - gap / 2, P.rs))
    return b.finish('equal', P.sb_bar)


def g_asterisk(P):
    """Six-armed asterisk: a vertical bar and two diagonals, all with
    perpendicular ends, centred near the cap top."""
    b = B(P)
    cy = P.cap - 165
    cx = P.sb_bar + 170 + P.V * 0.3
    arm = 140 + P.V * 0.3
    w = P.Vd * 0.78
    b.add(rect(cx - w / 2, cy - arm, cx + w / 2, cy + arm, P.rs))
    for ang in (30, 150):
        a = math.radians(ang)
        dx, dy = math.cos(a) * arm, math.sin(a) * arm
        b.add(diag((cx - dx, cy - dy), (cx + dx, cy + dy), w, 'perp', 'perp'))
    return b.finish('asterisk', P.sb_bar)


def g_dollar(P):
    """S with short vertical stubs above and below (the bar does not run
    through the spine, which keeps the Bold counters open)."""
    s = g_S(P)
    b = B(P)
    b.add(s.contours)
    x0, y0, x1, y1 = bbox(s.contours)
    cx = (x0 + x1) / 2
    bw = P.V * 0.62
    b.add(rect(cx - bw / 2, P.cap - P.H - 4, cx + bw / 2, P.cap + 88, P.rs),
          rect(cx - bw / 2, -88, cx + bw / 2, P.H + 4, P.rs))
    return Glyph('dollar', s.width, b.cs, UNICODES['dollar'])


def g_percent(P):
    """Two small squared rings on a diagonal."""
    b = B(P)
    vs, hs = P.V * 0.8, P.H * 0.8
    rw = cw(P, 116) + 2 * vs
    rh = P.cap * 0.40
    rr = min(P.rc * 0.6, 0.45 * rh)
    x0 = P.sb_round
    W = 2 * rw + 54
    b.add(ring(x0, P.cap - rh, x0 + rw, P.cap, rr, vs, hs, P.ri_min),
          ring(x0 + W - rw, 0, x0 + W, rh, rr, vs, hs, P.ri_min),
          diag((x0 + rw * 0.52, -8), (x0 + W - rw * 0.52, P.cap + 8), P.Vd * 0.85))
    return b.finish('percent', P.sb_round)


def g_ampersand(P):
    """Squared ampersand, one skeleton in every weight: a small loop over a
    wider lower bowl, sharing the waist stroke as the 8 does.  The diagonal
    runs from the loop's lower left to a shelf foot beyond the bowl.  The
    bowl's right side rises past the diagonal as an arm with a level cut, so
    the wedge above the diagonal stays open to the right."""
    b = B(P)
    dv = P.V - V_L
    x0 = P.sb_round
    lw = 2 * P.V + 288 - 0.25 * dv
    uw = 2 * P.V + 128 - 0.2 * dv
    xl1 = x0 + lw
    xu0 = x0 + 0.42 * (lw - uw)
    yu0 = P.cap * 0.54 - 0.35 * dv
    yl1 = yu0 + P.Hw
    rl = half_bowl_radius(P, P.rc * 0.85, yl1 + P.os)
    ru = half_bowl_radius(P, P.rc * 0.7, P.cap + P.os - yu0)
    wd = P.Vd * (0.95 - 0.15 * dv / 80)
    p = (xu0 + P.V * 0.5, yu0 + P.Hw * 0.5)
    q = (xl1 + 62 - 0.3 * dv, 0)
    yarm = safe_y(P, -P.os, yl1, rl, yu0 - 56 + 0.2 * dv)
    b.add(arc(x0, -P.os, xl1, yl1, rl, P.V, (P.Hw, P.H),
              ('x', xu0 + uw * 0.5, 'top'), ('y', yarm, 'right'), P.ri_min),
          ring(xu0, yu0, xu0 + uw, P.cap + P.os, ru, P.V, (P.H, P.Hw), P.ri_min),
          diag(p, q, wd, 'vert'), diag_serif(P, p, q, wd, q, 'bottom', 'right', ov=P.serL * 0.8))
    return b.finish('ampersand', P.sb_diag + 10)


def g_at(P):
    """@: a squared outer loop open at the right, a small squared a-ring
    inside with its own stem, and a bottom stroke that stops under the stem.
    Gaps between the inner ring and the outer wall are fixed numbers so no
    weight closes them."""
    b = B(P)
    x0 = P.sb_round
    vi, hi = P.V * 0.8, P.H * 0.8
    gap = 46 + 0.15 * P.V
    inner_w = cw(P, 176) + 2 * vi
    inner_h = cw(P, 248) + 2 * hi
    aw = 2 * P.V + 2 * gap + inner_w + 0.35 * P.V
    x1 = x0 + aw
    y0, y1 = -110, P.cap + P.os
    r = min(P.rc, half_bowl_radius(P, P.rc, y1 - y0))
    ya = y0 + r + 20
    xa0 = x0 + P.V + gap
    xa1 = xa0 + inner_w
    ya0 = (y0 + P.H + y1 - P.H) / 2 - inner_h / 2
    ya1 = ya0 + inner_h
    b.add(arc(x0, y0, x1, y1, r, P.V, P.H, ('y', safe_y(P, y0, y1, r, ya), 'right'), ('x', xa1 + 2, 'bottom'), P.ri_min),
          ring(xa0, ya0, xa1, ya1, P.rx * 0.9, vi, hi, P.ri_min),
          rect(xa1 - vi, y0 + P.H - 4, xa1, ya1 - 10, P.rs))
    return b.finish('at', P.sb_round)


def g_notdef(P):
    b = B(P)
    b.add(ring(50, 0, 450, P.cap, 4, P.V * 0.6, P.V * 0.6, 2))
    return Glyph('.notdef', 500, b.cs, None)


GLYPH_FUNCS = {
    '.notdef': g_notdef, 'space': g_space,
    'A': g_A, 'B': g_B, 'C': g_C, 'D': g_D, 'E': g_E, 'F': g_F, 'G': g_G,
    'H': g_H, 'I': g_I, 'J': g_J, 'K': g_K, 'L': g_L, 'M': g_M, 'N': g_N,
    'O': g_O, 'P': g_P, 'Q': g_Q, 'R': g_R, 'S': g_S, 'T': g_T, 'U': g_U,
    'V': g_V, 'W': g_W, 'X': g_X, 'Y': g_Y, 'Z': g_Z,
    'a': g_a, 'b': g_b, 'c': g_c, 'd': g_d, 'e': g_e, 'f': g_f, 'g': g_g,
    'h': g_h, 'i': g_i, 'j': g_j, 'k': g_k, 'l': g_l, 'm': g_m, 'n': g_n,
    'o': g_o, 'p': g_p, 'q': g_q, 'r': g_r, 's': g_s, 't': g_t, 'u': g_u,
    'v': g_v, 'w': g_w, 'x': g_x, 'y': g_y, 'z': g_z,
    'zero': g_zero, 'one': g_one, 'two': g_two, 'three': g_three, 'four': g_four,
    'five': g_five, 'six': g_six, 'seven': g_seven, 'eight': g_eight, 'nine': g_nine,
    'period': g_period, 'comma': g_comma, 'colon': g_colon, 'semicolon': g_semicolon,
    'exclam': g_exclam, 'question': g_question, 'quotesingle': g_quotesingle,
    'quotedbl': g_quotedbl, 'hyphen': g_hyphen, 'parenleft': g_parenleft,
    'parenright': g_parenright, 'bracketleft': g_bracketleft,
    'bracketright': g_bracketright, 'slash': g_slash, 'bar': g_bar,
    'underscore': g_underscore, 'ampersand': g_ampersand, 'at': g_at,
    'numbersign': g_numbersign, 'dollar': g_dollar, 'percent': g_percent,
    'plus': g_plus, 'equal': g_equal, 'asterisk': g_asterisk,
}


def build_all(P: Params, resolved: bool = True) -> dict[str, Glyph]:
    """All glyphs of one master.  v4 adds the glyphs in glyphs_ext.py and
    the accented composites; with `resolved` the composites also carry
    their flattened contours (for audits), the UFO writer keeps them as
    components either way."""
    import glyphs_ext as X
    out = {name: fn(P) for name, fn in GLYPH_FUNCS.items()}
    for name, fn in X.ext_funcs().items():
        out[name] = fn(P)
    for name, fn in X.pnum_funcs().items():
        out[name] = fn(P)
    X.add_anchors(out, P)
    for name in X.COMPOSITES:
        out[name] = X.composite(name, out)
    if resolved:
        X.resolve(out)
    return out
