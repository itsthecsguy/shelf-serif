"""v4 glyph constructions: accents and their composites, the rest of
Basic Latin and Latin-1, general punctuation, currency, superiors and
fractions, and the proportional figures.

Everything here is built from the same primitives and parameters as
glyphs.py.  Marks are drawn around their attachment point (0, 0): a mark
contour at y = 70 sits 70 units above the base's `top` anchor.
"""
from __future__ import annotations

import math

import glyphs as G
from geom import arc, bbox, diag, mirror_x, mirror_y, rect, ring, rotate180, translate
from glyphs import (B, Glyph, _hx, bar, bar_y, cap_terminals, ccw, cw, diag_serif, dot,
                    half_bowl_radius, inner_radius, lserif, ow, safe_y, serif, stem)
from params import Params, V_L, small

UNICODES = {
    # Basic Latin that v3 lacked
    'less': 0x3C, 'greater': 0x3E, 'backslash': 0x5C, 'asciicircum': 0x5E,
    'grave': 0x60, 'braceleft': 0x7B, 'braceright': 0x7D, 'asciitilde': 0x7E,
    # Latin-1 Supplement
    'uni00A0': 0xA0, 'exclamdown': 0xA1, 'cent': 0xA2, 'sterling': 0xA3,
    'currency': 0xA4, 'yen': 0xA5, 'brokenbar': 0xA6, 'section': 0xA7,
    'dieresis': 0xA8, 'copyright': 0xA9, 'ordfeminine': 0xAA,
    'guillemotleft': 0xAB, 'logicalnot': 0xAC,
    'registered': 0xAE, 'macron': 0xAF, 'degree': 0xB0, 'plusminus': 0xB1,
    'twosuperior': 0xB2, 'threesuperior': 0xB3, 'acute': 0xB4, 'mu': 0xB5,
    'paragraph': 0xB6, 'periodcentered': 0xB7, 'cedilla': 0xB8,
    'onesuperior': 0xB9, 'ordmasculine': 0xBA, 'guillemotright': 0xBB,
    'onequarter': 0xBC, 'onehalf': 0xBD, 'threequarters': 0xBE,
    'questiondown': 0xBF,
    'Agrave': 0xC0, 'Aacute': 0xC1, 'Acircumflex': 0xC2, 'Atilde': 0xC3,
    'Adieresis': 0xC4, 'Aring': 0xC5, 'AE': 0xC6, 'Ccedilla': 0xC7,
    'Egrave': 0xC8, 'Eacute': 0xC9, 'Ecircumflex': 0xCA, 'Edieresis': 0xCB,
    'Igrave': 0xCC, 'Iacute': 0xCD, 'Icircumflex': 0xCE, 'Idieresis': 0xCF,
    'Eth': 0xD0, 'Ntilde': 0xD1, 'Ograve': 0xD2, 'Oacute': 0xD3,
    'Ocircumflex': 0xD4, 'Otilde': 0xD5, 'Odieresis': 0xD6, 'multiply': 0xD7,
    'Oslash': 0xD8, 'Ugrave': 0xD9, 'Uacute': 0xDA, 'Ucircumflex': 0xDB,
    'Udieresis': 0xDC, 'Yacute': 0xDD, 'Thorn': 0xDE, 'germandbls': 0xDF,
    'agrave': 0xE0, 'aacute': 0xE1, 'acircumflex': 0xE2, 'atilde': 0xE3,
    'adieresis': 0xE4, 'aring': 0xE5, 'ae': 0xE6, 'ccedilla': 0xE7,
    'egrave': 0xE8, 'eacute': 0xE9, 'ecircumflex': 0xEA, 'edieresis': 0xEB,
    'igrave': 0xEC, 'iacute': 0xED, 'icircumflex': 0xEE, 'idieresis': 0xEF,
    'eth': 0xF0, 'ntilde': 0xF1, 'ograve': 0xF2, 'oacute': 0xF3,
    'ocircumflex': 0xF4, 'otilde': 0xF5, 'odieresis': 0xF6, 'divide': 0xF7,
    'oslash': 0xF8, 'ugrave': 0xF9, 'uacute': 0xFA, 'ucircumflex': 0xFB,
    'udieresis': 0xFC, 'yacute': 0xFD, 'thorn': 0xFE, 'ydieresis': 0xFF,
    # the rest of Windows-1252 / Mac Roman letters
    'dotlessi': 0x131, 'dotlessj': 0x237, 'OE': 0x152, 'oe': 0x153,
    'Scaron': 0x160, 'scaron': 0x161, 'Ydieresis': 0x178,
    'Zcaron': 0x17D, 'zcaron': 0x17E,
    # spacing accents
    'circumflex': 0x2C6, 'caron': 0x2C7, 'ring': 0x2DA, 'tilde': 0x2DC,
    'dotaccent': 0x2D9,
    # combining marks
    'gravecomb': 0x300, 'acutecomb': 0x301, 'circumflexcomb': 0x302,
    'tildecomb': 0x303, 'macroncomb': 0x304, 'dotaccentcomb': 0x307,
    'dieresiscomb': 0x308, 'ringcomb': 0x30A, 'caroncomb': 0x30C,
    'cedillacomb': 0x327,
    # general punctuation and symbols
    'endash': 0x2013, 'emdash': 0x2014, 'quoteleft': 0x2018,
    'quoteright': 0x2019, 'quotesinglbase': 0x201A, 'quotedblleft': 0x201C,
    'quotedblright': 0x201D, 'quotedblbase': 0x201E, 'dagger': 0x2020,
    'daggerdbl': 0x2021, 'bullet': 0x2022, 'ellipsis': 0x2026,
    'perthousand': 0x2030, 'guilsinglleft': 0x2039, 'guilsinglright': 0x203A,
    'fraction': 0x2044, 'Euro': 0x20AC, 'trademark': 0x2122, 'minus': 0x2212,
}


# B.finish() looks names up in glyphs.UNICODES, so the new codepoints
# have to be visible there too
G.UNICODES.update(UNICODES)


def _glyph(name, width, cs, **kw):
    return Glyph(name, int(round(width)), cs, UNICODES.get(name), **kw)


# =================================================================== marks
# All marks are drawn around the attachment point (0, 0).  Lowercase bases
# put `top` at the x-height, caps 24 units under the cap height (accents
# sit closer on caps and stay under the 940 ascender in Bold).
GAP = 70            # clearance between a base and the accent above it


def acc_h(P):
    """Accent height: 110 in Light, a little more in the heavier masters."""
    return 110 + 0.3 * (P.V - V_L)


def acc_w(P):
    return P.Vd * 0.92


def m_acute(P):
    h = acc_h(P)
    dx = 46 + 0.1 * (P.V - V_L)
    return [diag((-dx, GAP), (dx, GAP + h), acc_w(P))]


def m_grave(P):
    return mirror_x(m_acute(P), 0)


def m_circumflex(P):
    """Two strokes with level cuts meeting in a short flat apex, the same
    construction as the A."""
    h = acc_h(P) * 1.05
    hs = 96 + 0.25 * (P.V - V_L)
    w = acc_w(P)
    return [diag((-hs, GAP), (0, GAP + h), w), diag((hs, GAP), (0, GAP + h), w)]


def m_caron(P):
    cs = m_circumflex(P)
    x0, y0, x1, y1 = bbox(cs)
    return mirror_y(cs, (y0 + y1) / 2)


def m_tilde(P):
    """Squared tilde: a low bar on the left, a rising stroke, a high bar on
    the right, all one hairline-free stroke thick."""
    t = P.H * 0.70
    h = acc_h(P) * 1.32
    half = 122 + 0.3 * (P.V - V_L)
    arm = 40 + 0.1 * (P.V - V_L)
    y_lo = GAP
    y_hi = GAP + h - t
    xa = -half + arm          # end of the left bar / start of the rise
    xb = half - arm
    return [rect(-half, y_lo, xa + 2, y_lo + t, 0),
            diag((xa, y_lo + t / 2), (xb, y_hi + t / 2), t, 'vert', 'vert'),
            rect(xb - 2, y_hi, half, y_hi + t, 0)]


def m_dieresis(P):
    s = P.dot * 0.78
    off = s / 2 + 34 + 0.1 * (P.V - V_L)
    y = GAP + 22
    return [dot(P, -off, y, s), dot(P, off, y, s)]


def m_dotaccent(P):
    """The i's own dot, so an accented dotless i matches a plain i."""
    return [dot(P, 0, 96, P.dot)]


def m_ring(P):
    """Small squared ring.  Strokes at 0.58 of the letter's so the counter
    stays open in Bold; it sits 20 units over the letter (the Aring's
    ring overlaps the apex, see CAP_DROP)."""
    s = 170 + 1.0 * (P.V - V_L)
    y0 = 20
    return ring(-s / 2, y0, s / 2, y0 + s, P.rx * 0.5, P.V * 0.58, P.H * 0.58, 3)


def m_macron(P):
    half = 118 + 0.2 * (P.V - V_L)
    y = GAP + 30
    return [rect(-half, y, half, y + P.H * 0.8, 0)]


def m_cedilla(P):
    """Hangs from the `bottom` anchor on the baseline: a short stub down
    from the letter, then a tray running left."""
    w = P.V * 0.72
    t = P.H * 0.78
    depth = 150 + 0.2 * (P.V - V_L)
    return [rect(-w / 2, -depth * 0.55, w / 2, 4, 0),
            rect(-w / 2 - 78 - 0.2 * (P.V - V_L), -depth, w / 2, -depth + t, P.rs)]


MARKS = {
    'gravecomb': m_grave, 'acutecomb': m_acute, 'circumflexcomb': m_circumflex,
    'tildecomb': m_tilde, 'macroncomb': m_macron, 'dotaccentcomb': m_dotaccent,
    'dieresiscomb': m_dieresis, 'ringcomb': m_ring, 'caroncomb': m_caron,
    'cedillacomb': m_cedilla,
}
SPACING_OF = {
    'grave': 'gravecomb', 'acute': 'acutecomb', 'circumflex': 'circumflexcomb',
    'tilde': 'tildecomb', 'macron': 'macroncomb', 'dotaccent': 'dotaccentcomb',
    'dieresis': 'dieresiscomb', 'ring': 'ringcomb', 'caron': 'caroncomb',
    'cedilla': 'cedillacomb',
}


def mark_glyph(name, P):
    cs = MARKS[name](P)
    anchor = '_bottom' if name == 'cedillacomb' else '_top'
    return Glyph(name, 0, cs, UNICODES[name], anchors={anchor: (0, 0)}, category='mark')


def spacing_mark(name, P):
    """Spacing accent: the mark as it sits over a lowercase letter, with
    40 units each side."""
    cs = MARKS[SPACING_OF[name]](P)
    x0, y0, x1, y1 = bbox(cs)
    dy = 0 if name == 'cedilla' else P.xh
    cs = translate(cs, 40 - x0, dy)
    return _glyph(name, x1 - x0 + 80, cs)


# ============================================================== composites
# name: (base, mark, anchor)
COMPOSITES = {}
for _b, _marks in (
    ('A', 'grave acute circumflex tilde dieresis ring'),
    ('E', 'grave acute circumflex dieresis'),
    ('I', 'grave acute circumflex dieresis'),
    ('N', 'tilde'), ('O', 'grave acute circumflex tilde dieresis'),
    ('U', 'grave acute circumflex dieresis'), ('Y', 'acute dieresis'),
    ('S', 'caron'), ('Z', 'caron'),
    ('a', 'grave acute circumflex tilde dieresis ring'),
    ('e', 'grave acute circumflex dieresis'),
    ('n', 'tilde'), ('o', 'grave acute circumflex tilde dieresis'),
    ('u', 'grave acute circumflex dieresis'), ('y', 'acute dieresis'),
    ('s', 'caron'), ('z', 'caron'),
):
    for _m in _marks.split():
        COMPOSITES[_b + _m] = (_b, _m + 'comb', 'top')
for _m in 'grave acute circumflex dieresis'.split():
    COMPOSITES['i' + _m] = ('dotlessi', _m + 'comb', 'top')
COMPOSITES['Ccedilla'] = ('C', 'cedillacomb', 'bottom')
COMPOSITES['ccedilla'] = ('c', 'cedillacomb', 'bottom')

# bases that carry anchors: name -> which anchors
ANCHORED_CAPS = 'ACEINOSUYZ'
ANCHORED_LC = 'aceinosuyz'


def body_center_x(cs, frac=(0.2, 0.8)):
    """x centre of the ink between frac of the glyph's height, so hairline
    serifs and one-sided overhangs do not pull the accent off the stem."""
    pts = []
    for c in cs:
        prev = c[-1][-1]
        for node in c:
            if node[0] == 'l':
                pts.append(node[1])
            else:
                p0, p1, p2, p3 = prev, node[1], node[2], node[3]
                for i in range(1, 9):
                    t = i / 8
                    mt = 1 - t
                    pts.append((mt**3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t**3 * p3[0],
                                mt**3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t**3 * p3[1]))
            prev = node[-1]
    ys = [p[1] for p in pts]
    y0, y1 = min(ys), max(ys)
    lo, hi = y0 + frac[0] * (y1 - y0), y0 + frac[1] * (y1 - y0)
    xs = [p[0] for p in pts if lo <= p[1] <= hi] or [p[0] for p in pts]
    return (min(xs) + max(xs)) / 2


def add_anchors(glyphs, P):
    """Put `top` (and `bottom` on C and c) anchors on the bases."""
    for n in ANCHORED_CAPS:
        g = glyphs[n]
        g.anchors['top'] = (body_center_x(g.contours), P.cap - 24)
    for n in ANCHORED_LC:
        g = glyphs[n]
        g.anchors['top'] = (body_center_x(g.contours), P.xh)
    for n in ('dotlessi', 'dotlessj'):
        g = glyphs[n]
        g.anchors['top'] = (body_center_x(g.contours, (0.3, 0.9)), P.xh)
    for n in 'Cc':
        g = glyphs[n]
        g.anchors['bottom'] = (body_center_x(g.contours), 0)
    for g in glyphs.values():
        if g.category is None and g.contours and g.name not in ('.notdef',):
            g.category = 'base'


# marks that sit lower on caps than the cap anchor alone would put them
CAP_DROP = {'ringcomb': 36}


def composite(name, glyphs):
    base, mark, anchor = COMPOSITES[name]
    bg, mg = glyphs[base], glyphs[mark]
    ax, ay = bg.anchors[anchor]
    mx, my = mg.anchors['_' + anchor]
    dx, dy = ax - mx, ay - my
    if base[0].isupper():
        dy -= CAP_DROP.get(mark, 0)
    return Glyph(name, bg.width, [], UNICODES[name],
                 components=[(base, 0, 0), (mark, dx, dy)],
                 anchors=dict(bg.anchors), category='base')


def resolve(glyphs):
    """Fill in the contours of composites (for the audits and specimens;
    the UFO keeps them as components)."""
    for g in glyphs.values():
        if g.components and not g.contours:
            cs = []
            for ref, dx, dy in g.components:
                r = glyphs[ref]
                if r.components and not r.contours:
                    resolve({ref: r, **{k: glyphs[k] for k, _, _ in r.components}})
                cs += translate(r.contours, dx, dy)
            g.contours = cs
    return glyphs


# ============================================================ dotless i j
def g_dotlessi(P):
    g = G.g_i(P)
    return Glyph('dotlessi', g.width, g.contours[:-1], UNICODES['dotlessi'])


def g_dotlessj(P):
    g = G.g_j(P)
    return Glyph('dotlessj', g.width, g.contours[:-1], UNICODES['dotlessj'])


# ============================================================ Latin-1 letters
def g_AE(P):
    """A's left leg running up to the top of an E."""
    b = B(P)
    run = (ccw(P, 458) + P.V) / 2            # the A's half span, same slope
    hx = _hx(P, run, P.cap)
    xL = P.sb_diag + P.serL + hx
    xs = xL + run - P.V / 2
    xr = xs + ow(P, 450)
    yb = bar_y(P)
    # the diagonal's right edge passes 56 units left of the stem at the
    # top of the middle bar, so the counter above the bar stays open in
    # Bold (the apex then runs into the stem or the top bar)
    apex_x = xs - 56 - hx + run * (P.cap - (yb + P.H)) / P.cap
    pL, apex = (xL, 0), (apex_x, P.cap)
    run = apex_x - xL
    xbar = xL + run * ((yb + P.H / 2) / P.cap) - hx * 0.5
    b.add(diag(pL, apex, P.Vd), stem(P, xs, 0, P.cap),
          bar(P, xs, xr, P.cap - P.H), bar(P, xbar, xr - 36, yb, P.Hw), bar(P, xs, xr, 0),
          diag_serif(P, pL, apex, P.Vd, pL, 'bottom', 'both'))
    return b.finish('AE', P.sb_bar)


def g_OE(P):
    """The left half of an O (no overshoot, so the join with the E arms
    is flush) and an E whose stem is the ring's right side."""
    b = B(P)
    x0 = P.sb_round
    xm = x0 + ow(P, 400)                       # left edge of the E stem
    xr = xm + ow(P, 470)
    b.add(arc(x0, 0, xm + P.V + 4, P.cap, (0, P.rc, P.rc, 0), P.V, P.H,
              ('x', xm + 2, 'top'), ('x', xm + 2, 'bottom'), P.ri_min),
          stem(P, xm, 0, P.cap),
          bar(P, xm, xr, P.cap - P.H), bar(P, xm, xr - 36, bar_y(P), P.Hw), bar(P, xm, xr, 0))
    return b.finish('OE', P.sb_bar)


def g_ae(P):
    """a and e sharing a stem."""
    b = B(P)
    a = G.g_a(P)
    x0 = P.sb_round
    xs = x0 + P.V + cw(P, 194)                 # the a's stem, as in g_a
    we = cw(P, 196) + 2 * P.V
    x1 = xs + we
    he = min(P.H, P.xh - 2 * P.H - 130)
    yb = (P.xh - he) / 2 + 10
    b.add(a.contours[:-1],                      # drop the a's foot serif
          stem(P, xs, 0, P.xh),
          arc(xs, -P.os, x1, P.xh + P.os, (P.rx, 0, 0, P.rx), P.V, P.H,
              ('y', yb, 'right'), ('a', 318), P.ri_min),
          bar(P, xs + P.V - 4, x1 - P.V + 4, yb, he))
    return b.finish('ae', P.sb_term)


def g_oe(P):
    b = B(P)
    x0 = P.sb_round
    xm = x0 + P.V + cw(P, 160)                 # shared stem's left edge
    we = cw(P, 196) + 2 * P.V
    x1 = xm + we
    he = min(P.H, P.xh - 2 * P.H - 130)
    yb = (P.xh - he) / 2 + 10
    b.add(arc(x0, -P.os, xm + P.V + 4, P.xh + P.os, (0, P.rx, P.rx, 0), P.V, P.H,
              ('x', xm + 2, 'top'), ('x', xm + 2, 'bottom'), P.ri_min),
          stem(P, xm, -P.os + 2, P.xh + P.os - 2),
          arc(xm, -P.os, x1, P.xh + P.os, (P.rx, 0, 0, P.rx), P.V, P.H,
              ('y', yb, 'right'), ('a', 318), P.ri_min),
          bar(P, xm + P.V - 4, x1 - P.V + 4, yb, he))
    return b.finish('oe', P.sb_term)


def g_Eth(P):
    d = G.g_D(P)
    b = B(P)
    x1 = P.sb_stem
    b.add(d.contours, bar(P, x1 - 56, x1 + P.V + ccw(P, 92), bar_y(P), P.Hw))
    return Glyph('Eth', d.width, b.cs, UNICODES['Eth'])


def g_eth(P):
    """Squared eth: an o bowl, a stem on its right rising to 0.92 of the
    ascender, and a rising bar through the stem's top."""
    b = B(P)
    x0 = P.sb_round
    w = cw(P, 202) + 2 * P.V
    x1 = x0 + w
    xs = x1 - P.V
    top = P.asc * 0.93
    b.add(ring(x0, -P.os, x1, P.xh + P.os, P.rx, P.V, P.H, P.ri_min),
          stem(P, xs, P.xh / 2, top),
          diag((xs - 96 - 0.2 * (P.V - V_L), top - 150), (x1 + 50, top - 20), P.Vd * 0.9))
    return b.finish('eth', P.sb_round)


def g_Thorn(P):
    b = B(P)
    x1 = P.sb_stem
    y0, y1 = P.cap * 0.16, P.cap * 0.80
    xr = x1 + ow(P, 532)
    r = half_bowl_radius(P, P.rc * 0.85, y1 - y0)
    b.add(stem(P, x1, 0, P.cap), G.bowl_right(P, x1, xr, y0, y1, r),
          serif(P, x1, P.cap, 'top', 'both'), serif(P, x1, 0, 'bottom', 'both'))
    return b.finish('Thorn', P.sb_round)


def g_thorn(P):
    b = B(P)
    xs = P.sb_stem
    w = cw(P, 214)
    b.add(stem(P, xs, P.desc, P.asc), G.bowl_right(P, xs, xs + 2 * P.V + w, 0, P.xh, P.rx),
          lserif(P, xs, P.asc, 'top', 'left'), lserif(P, xs, P.desc, 'bottom', 'both'))
    return b.finish('thorn', P.sb_round)


def g_germandbls(P):
    """Eszett: a stem with a squared hook over the top, the hook's right
    side dropping to a waist near the x-height, and a lower bowl that
    bulges out and comes back to a plumb terminal just right of the stem."""
    b = B(P)
    xs = P.sb_stem
    wt = max(2 * P.V + cw(P, 80), 2 * P.V + 70)       # top hook width
    wb = wt + 60 + 0.2 * (P.V - V_L)                  # lower bowl width
    yw = P.xh * 0.90                                   # waist
    yh0 = yw - P.H - 10
    rt = half_bowl_radius(P, P.rx * 0.85, P.asc + P.os - yh0)
    rl = half_bowl_radius(P, P.rx * 0.85, yw + P.H + P.os)
    xb0 = xs + 30
    xB = xs + wt - P.V + 4
    xt = xs + P.V + 50
    b.add(stem(P, xs, 0, yh0 + 30),
          arc(xs, yh0, xs + wt, P.asc + P.os, (rt, rt, 0, 0), P.V, P.H,
              ('y', yw, 'right'), ('y', yh0 + 12, 'left'), P.ri_min),
          arc(xb0, -P.os, xs + wb, yw + P.H, (rl, 0, rl, rl), P.V, P.H,
              ('x', xt, 'bottom'), ('x', xB, 'top'), P.ri_min),
          lserif(P, xs, 0, 'bottom', 'both'))
    return b.finish('germandbls', P.sb_round)


def slash_in(P, x0, x1, y0, y1, w):
    """A diagonal from bottom-left to top-right whose level end cuts stay
    within [x0, x1]."""
    hx = _hx(P, x1 - x0, y1 - y0, w)
    for _ in range(3):
        hx = _hx(P, x1 - x0 - 2 * hx, y1 - y0, w)
    return diag((x0 + hx, y0), (x1 - hx, y1), w)


def g_Oslash(P):
    o = G.g_O(P)
    x0, y0, x1, y1 = bbox(o.contours)
    b = B(P)
    b.add(o.contours, slash_in(P, x0, x1, -46, P.cap + 46, P.Vd * 0.9))
    return Glyph('Oslash', o.width, b.cs, UNICODES['Oslash'])


def g_oslash(P):
    o = G.g_o(P)
    x0, y0, x1, y1 = bbox(o.contours)
    b = B(P)
    b.add(o.contours, slash_in(P, x0, x1, -56, P.xh + 56, P.Vd * 0.85))
    return Glyph('oslash', o.width, b.cs, UNICODES['oslash'])


def g_mu(P):
    u = G.g_u(P)
    b = B(P)
    x1 = P.sb_stem
    b.add(u.contours, stem(P, x1, P.desc, P.xh * 0.5),
          lserif(P, x1, P.desc, 'bottom', 'both'))
    return Glyph('mu', u.width, b.cs, UNICODES['mu'])


# ====================================================== small-size derived
SUP = (0.62, 0.72)     # superiors / fractions: size, stroke factor
ORD = (0.62, 0.72)     # ordinals
SYM = (0.50, 0.62)     # letters inside the copyright and registered rings
TM = (0.42, 0.60)


def _small(P, fn, s, k, **kw):
    Ps = small(P, s, k)
    return fn(Ps, **kw) if kw else fn(Ps), Ps


def _superior(P, fn, name):
    g, Ps = _small(P, fn, *SUP, prop=True)
    cs = translate(g.contours, 0, P.cap - Ps.cap)
    return _glyph(name, g.width, cs)


def g_onesuperior(P):
    return _superior(P, G.g_one, 'onesuperior')


def g_twosuperior(P):
    return _superior(P, G.g_two, 'twosuperior')


def g_threesuperior(P):
    return _superior(P, G.g_three, 'threesuperior')


def _fraction(P, name, num_fn, den_fn):
    num, Ps = _small(P, num_fn, *SUP, prop=True)
    den, _ = _small(P, den_fn, *SUP, prop=True)
    b = B(P)
    nx0, ny0, nx1, ny1 = bbox(num.contours)
    dx0, dy0, dx1, dy1 = bbox(den.contours)
    x = 20
    b.add(translate(num.contours, x - nx0, P.cap - Ps.cap))
    # the slash starts under the numerator's right end; the denominator
    # starts where the slash has cleared the denominator's top edge
    sw = 0.42 * P.cap
    w = P.Vd * 0.85
    hx = _hx(P, sw, P.cap + 20, w)
    y_foot = P.cap - Ps.cap + Ps.ser + 10
    sx0 = x + (nx1 - nx0) + 20 + hx - sw * (y_foot + 10) / (P.cap + 20)
    b.add(diag((sx0, -10), (sx0 + sw, P.cap + 10), w))
    bx0 = sx0 + sw * (Ps.cap + 10) / (P.cap + 20) + 0.5 * P.Vd + 36
    b.add(translate(den.contours, bx0 - dx0, 0))
    return b.finish(name, 24)


def g_onequarter(P):
    return _fraction(P, 'onequarter', G.g_one, G.g_four)


def g_onehalf(P):
    return _fraction(P, 'onehalf', G.g_one, G.g_two)


def g_threequarters(P):
    return _fraction(P, 'threequarters', G.g_three, G.g_four)


def g_fraction(P):
    b = B(P)
    sw = 0.42 * P.cap
    w = P.Vd * 0.85
    hx = _hx(P, sw, P.cap + 20, w)
    b.add(diag((hx, -10), (hx + sw, P.cap + 10), w))
    return b.finish('fraction', 0)


def _ordinal(P, fn, name):
    g, Ps = _small(P, fn, *ORD)
    cs = translate(g.contours, 0, P.cap - Ps.xh)
    return _glyph(name, g.width, cs)


def g_ordfeminine(P):
    return _ordinal(P, G.g_a, 'ordfeminine')


def g_ordmasculine(P):
    return _ordinal(P, G.g_o, 'ordmasculine')


def _ringed(P, fn, name):
    """A squared ring the size of the cap with a small letter inside."""
    b = B(P)
    x0 = P.sb_round
    size = P.cap + 2 * P.os
    vs, hs = P.V * 0.78, P.H * 0.78
    b.add(ring(x0, -P.os, x0 + size, P.cap + P.os, P.rc * 1.05, vs, hs, P.ri_min))
    g, Ps = _small(P, fn, *SYM)
    gx0, gy0, gx1, gy1 = bbox(g.contours)
    cx = x0 + size / 2
    cy = P.cap / 2
    b.add(translate(g.contours, cx - (gx0 + gx1) / 2, cy - (gy0 + gy1) / 2))
    return b.finish(name, P.sb_round)


def g_copyright(P):
    return _ringed(P, G.g_C, 'copyright')


def g_registered(P):
    return _ringed(P, G.g_R, 'registered')


def g_trademark(P):
    t, Ps = _small(P, G.g_T, *TM)
    m, _ = _small(P, G.g_M, *TM)
    b = B(P)
    dy = P.cap - Ps.cap
    b.add(translate(t.contours, 20, dy), translate(m.contours, 20 + t.width - 10, dy))
    return b.finish('trademark', 30)


# =========================================================== punctuation
def g_uni00A0(P):
    return Glyph('uni00A0', G.g_space(P).width, [], 0xA0)


def g_exclamdown(P):
    g = G.g_exclam(P)
    x0, y0, x1, y1 = bbox(g.contours)
    cs = rotate180(g.contours, (x0 + x1) / 2, P.cap / 2)
    cs = translate(cs, 0, -(P.cap - P.xh))
    return _glyph('exclamdown', g.width, cs)


def g_questiondown(P):
    g = G.g_question(P)
    x0, y0, x1, y1 = bbox(g.contours)
    cs = rotate180(g.contours, (x0 + x1) / 2, P.cap / 2)
    cs = translate(cs, 0, -(P.cap - P.xh))
    return _glyph('questiondown', g.width, cs)


def g_endash(P):
    b = B(P)
    hy = P.xh * 0.5 + 12
    b.add(rect(40, hy - P.H / 2, 540, hy + P.H / 2, 0))
    return b.finish('endash', 40)


def g_emdash(P):
    b = B(P)
    hy = P.xh * 0.5 + 12
    b.add(rect(20, hy - P.H / 2, 980, hy + P.H / 2, 0))
    return b.finish('emdash', 20)


def math_width(P):
    """Every math sign takes the plus sign's advance."""
    return G.g_plus(P).width


def g_minus(P):
    b = B(P)
    cy = G.math_center(P)
    aw = cw(P, 318) + P.V
    x0 = P.sb_bar
    b.add(rect(x0, cy - P.H / 2, x0 + aw, cy + P.H / 2, P.rs))
    return b.finish_centered('minus', math_width(P))


def g_multiply(P):
    b = B(P)
    cy = G.math_center(P)
    aw = cw(P, 318) + P.V
    x0 = P.sb_bar
    cx = x0 + aw / 2
    a = aw * 0.34
    w = P.Vd * 0.95
    b.add(diag((cx - a, cy - a), (cx + a, cy + a), w, 'perp', 'perp'),
          diag((cx - a, cy + a), (cx + a, cy - a), w, 'perp', 'perp'))
    return b.finish_centered('multiply', math_width(P))


def g_divide(P):
    b = B(P)
    cy = G.math_center(P)
    aw = cw(P, 318) + P.V
    x0 = P.sb_bar
    s = P.dot * 0.8
    gap = 0.9 * P.H + 50
    b.add(rect(x0, cy - P.H / 2, x0 + aw, cy + P.H / 2, P.rs),
          dot(P, x0 + aw / 2, cy + gap, s), dot(P, x0 + aw / 2, cy - gap - s, s))
    return b.finish_centered('divide', math_width(P))


def g_plusminus(P):
    b = B(P)
    cy = G.math_center(P) + 70
    aw = cw(P, 318) + P.V
    x0 = P.sb_bar
    arm = aw * 0.84
    cx = x0 + aw / 2
    b.add(rect(cx - arm / 2, cy - P.H / 2, cx + arm / 2, cy + P.H / 2, P.rs),
          rect(cx - P.H / 2, cy - arm / 2, cx + P.H / 2, cy + arm / 2, P.rs),
          rect(cx - arm / 2, 6, cx + arm / 2, 6 + P.H, P.rs))
    return b.finish_centered('plusminus', math_width(P))


def g_logicalnot(P):
    b = B(P)
    cy = G.math_center(P) + 40
    aw = cw(P, 318) + P.V
    x0 = P.sb_bar
    b.add(rect(x0, cy - P.H / 2, x0 + aw, cy + P.H / 2, P.rs),
          rect(x0 + aw - P.H, cy - P.H / 2 - 0.3 * aw, x0 + aw, cy + P.H / 2, P.rs))
    return b.finish_centered('logicalnot', math_width(P))


def chevron(P, x, cy, hw, hh, w, point_left=True):
    """Two strokes meeting in a plumb cut at x: '<' if point_left, else '>'
    with the point at x + hw."""
    if point_left:
        p, a, c = (x, cy), (x + hw, cy + hh), (x + hw, cy - hh)
    else:
        p, a, c = (x + hw, cy), (x, cy + hh), (x, cy - hh)
    return [diag(a, p, w, 'vert', 'vert'), diag(c, p, w, 'vert', 'vert')]


def g_less(P):
    b = B(P)
    cy = G.math_center(P)
    aw = cw(P, 318) + P.V
    x0 = P.sb_bar
    b.add(chevron(P, x0, cy, aw * 0.66, aw * 0.44, P.Vd * 0.95, True))
    return b.finish_centered('less', math_width(P))


def g_greater(P):
    g = g_less(P)
    return Glyph('greater', g.width, mirror_x(g.contours, g.width / 2), UNICODES['greater'])


def g_guillemotleft(P):
    b = B(P)
    cy = P.xh * 0.5
    hw, hh = 104 + 0.4 * (P.V - V_L), 112
    w = P.Vd * 0.86
    x0 = 36
    cs = chevron(P, x0, cy, hw, hh, w, True)
    cx0, _, cx1, _ = bbox(cs)
    step = (cx1 - cx0) + 30 + 0.2 * (P.V - V_L)
    b.add(cs, translate(cs, step, 0))
    return b.finish('guillemotleft', 36)


def g_guillemotright(P):
    g = g_guillemotleft(P)
    return Glyph('guillemotright', g.width, mirror_x(g.contours, g.width / 2), UNICODES['guillemotright'])


def g_guilsinglleft(P):
    b = B(P)
    cy = P.xh * 0.5
    b.add(chevron(P, 36, cy, 104 + 0.4 * (P.V - V_L), 112, P.Vd * 0.86, True))
    return b.finish('guilsinglleft', 36)


def g_guilsinglright(P):
    g = g_guilsinglleft(P)
    return Glyph('guilsinglright', g.width, mirror_x(g.contours, g.width / 2), UNICODES['guilsinglright'])


def g_backslash(P):
    g = G.g_slash(P)
    return Glyph('backslash', g.width, mirror_x(g.contours, g.width / 2), UNICODES['backslash'])


def g_asciicircum(P):
    b = B(P)
    hs = 140 + 0.3 * (P.V - V_L)
    w = P.Vd * 0.9
    y0 = P.cap - 250
    x0 = P.sb_diag + hs + _hx(P, hs, P.cap - y0, w)
    b.add(diag((x0 - hs, y0), (x0, P.cap), w), diag((x0 + hs, y0), (x0, P.cap), w))
    return b.finish('asciicircum', P.sb_diag)


def g_asciitilde(P):
    b = B(P)
    cy = G.math_center(P)
    t = P.H * 0.8
    half = 190 + 0.4 * (P.V - V_L)
    arm = 80
    rise = 74 + 0.2 * (P.V - V_L)
    y_lo, y_hi = cy - rise / 2 - t / 2, cy + rise / 2 - t / 2
    xa, xb = -half + arm, half - arm
    cs = [rect(-half, y_lo, xa + 2, y_lo + t, 0),
          diag((xa, y_lo + t / 2), (xb, y_hi + t / 2), t, 'vert', 'vert'),
          rect(xb - 2, y_hi, half, y_hi + t, 0)]
    b.add(translate(cs, P.sb_bar + half, 0))
    return b.finish('asciitilde', P.sb_bar)


def g_braceleft(P):
    """Squared brace: a bracket whose stem carries a short tick to the
    left at the middle."""
    b = B(P)
    x0 = P.sb_term + 70
    bw = cw(P, 150) + P.V
    ym = (P.asc + P.desc) / 2
    b.add(stem(P, x0, P.desc - 10, P.asc + 10),
          bar(P, x0, x0 + bw, P.asc + 10 - P.H), bar(P, x0, x0 + bw, P.desc - 10),
          rect(x0 - 70, ym - P.H / 2, x0 + 4, ym + P.H / 2, P.rs))
    return b.finish('braceleft', 30)


def g_braceright(P):
    g = g_braceleft(P)
    return Glyph('braceright', g.width, mirror_x(g.contours, g.width / 2), UNICODES['braceright'])


def g_brokenbar(P):
    b = B(P)
    x0 = 80
    w = P.V * 0.9
    ym = (P.asc + P.desc) / 2
    b.add(rect(x0, P.desc - 30, x0 + w, ym - 60, P.rs),
          rect(x0, ym + 60, x0 + w, P.asc + 30, P.rs))
    return b.finish('brokenbar', 80)


def g_bullet(P):
    b = B(P)
    s = P.dot * 1.25
    cy = G.math_center(P)
    b.add(dot(P, 60 + s / 2, cy - s / 2, s))
    return b.finish('bullet', 60)


def g_periodcentered(P):
    b = B(P)
    cy = G.math_center(P)
    b.add(dot(P, 60 + P.dot / 2, cy - P.dot / 2))
    return b.finish('periodcentered', 60)


def g_ellipsis(P):
    p = G.g_period(P)
    b = B(P)
    for i in range(3):
        b.add(translate(p.contours, i * p.width, 0))
    return Glyph('ellipsis', 3 * p.width, b.cs, UNICODES['ellipsis'])


def g_quoteright(P):
    c = G.g_comma(P)
    x0, y0, x1, y1 = bbox(c.contours)
    cs = translate(c.contours, 0, P.cap + 16 - y1)
    return _glyph('quoteright', c.width, cs)


def g_quoteleft(P):
    q = g_quoteright(P)
    x0, y0, x1, y1 = bbox(q.contours)
    return _glyph('quoteleft', q.width, rotate180(q.contours, (x0 + x1) / 2, (y0 + y1) / 2))


def g_quotesinglbase(P):
    c = G.g_comma(P)
    return _glyph('quotesinglbase', c.width, c.contours)


def _double(P, single, name):
    g = single(P)
    x0, y0, x1, y1 = bbox(g.contours)
    step = (x1 - x0) + P.V * 0.6
    b = B(P)
    b.add(g.contours, translate(g.contours, step, 0))
    return _glyph(name, g.width + step, b.cs)


def g_quotedblleft(P):
    return _double(P, g_quoteleft, 'quotedblleft')


def g_quotedblright(P):
    return _double(P, g_quoteright, 'quotedblright')


def g_quotedblbase(P):
    return _double(P, g_quotesinglbase, 'quotedblbase')


def g_dagger(P):
    b = B(P)
    w = P.V * 0.9
    x0 = P.sb_bar
    aw = cw(P, 250) + w
    cx = x0 + aw / 2
    yb = P.cap - 190
    b.add(rect(cx - w / 2, -40, cx + w / 2, P.cap, P.rs),
          rect(x0, yb - P.H / 2, x0 + aw, yb + P.H / 2, P.rs))
    return b.finish('dagger', P.sb_bar)


def g_daggerdbl(P):
    g = g_dagger(P)
    b = B(P)
    w = P.V * 0.9
    x0 = P.sb_bar
    aw = cw(P, 250) + w
    yb = 130
    b.add(g.contours, rect(x0, yb - P.H / 2, x0 + aw, yb + P.H / 2, P.rs))
    return _glyph('daggerdbl', g.width, b.cs)


def g_perthousand(P):
    p = G.g_percent(P)
    b = B(P)
    vs, hs = P.V * 0.8, P.H * 0.8
    rw = cw(P, 116) + 2 * vs
    rh = P.cap * 0.40
    rr = min(P.rc * 0.6, 0.45 * rh)
    x0, y0, x1, y1 = bbox(p.contours)
    b.add(p.contours, ring(x1 + 40, 0, x1 + 40 + rw, rh, rr, vs, hs, P.ri_min))
    return b.finish('perthousand', P.sb_round)


def g_section(P):
    """Two S-like hooks sharing a middle ring."""
    b = B(P)
    x0 = P.sb_term
    w = ow(P, 470)
    x1 = x0 + w
    cx = (x0 + x1) / 2
    top, bot = P.cap + 10, -70
    H2 = (top + bot) / 2
    hh = (top - bot) * 0.46                      # height of each hook
    r = half_bowl_radius(P, P.rc * 0.8, hh)
    yt = safe_y(P, top - hh, top, r, top - hh * 0.72)
    upper = arc(x0, top - hh, x1, top, r, P.V, P.H,
                ('y', yt, 'right'), ('x', cx + 40, 'bottom'), P.ri_min)
    lower = rotate180([upper], cx, H2)[0]
    rh = max((top - bot) * 0.40, 2 * P.H + 70)
    rr = half_bowl_radius(P, P.rc * 0.8, rh)
    b.add(upper, lower,
          ring(x0 + 22, H2 - rh / 2, x1 - 22, H2 + rh / 2, rr, P.V, P.H, P.ri_min))
    return b.finish('section', P.sb_term)


def g_paragraph(P):
    """Pilcrow: a filled squared bowl on the left and two stems."""
    b = B(P)
    x0 = P.sb_round
    bw = ccw(P, 230) + 2 * P.V
    x2 = x0 + bw + 40                           # right stem
    x1 = x2 - P.V - 70 - 0.3 * (P.V - V_L)      # inner stem
    y0 = P.cap * 0.42
    b.add(rect(x0, y0, x1 + P.V, P.cap, (0, P.rc * 0.9, P.rc * 0.9, 0)),
          stem(P, x1, -120, P.cap), stem(P, x2, -120, P.cap),
          bar(P, x1, x2 + P.V, P.cap - P.H))
    return b.finish('paragraph', P.sb_stem)


def g_degree(P):
    b = B(P)
    s = 0.36 * P.cap + 0.8 * (P.V - V_L)
    x0 = P.sb_round
    b.add(ring(x0, P.cap - s, x0 + s, P.cap + P.os, P.rc * 0.45, P.V * 0.62, P.H * 0.62, 3))
    return b.finish('degree', P.sb_round)


def g_currency(P):
    b = B(P)
    cy = P.cap * 0.5
    s = 0.44 * P.cap + 0.3 * (P.V - V_L)
    x0 = P.sb_round + 100
    cx = x0 + s / 2
    cs = [*ring(x0, cy - s / 2, x0 + s, cy + s / 2, P.rc * 0.45, P.V * 0.8, P.H * 0.8, 3)]
    a = s / 2 - 56
    e = s / 2 + 90
    w = P.Vd * 0.8
    for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        cs.append(diag((cx + sx * a, cy + sy * a), (cx + sx * e, cy + sy * e), w, 'perp', 'perp'))
    b.add(cs)
    return b.finish('currency', P.sb_round + 100)


def g_cent(P):
    c = G.g_c(P)
    x0, y0, x1, y1 = bbox(c.contours)
    cx = (x0 + x1) / 2 - 8
    bw = P.V * 0.62
    b = B(P)
    b.add(c.contours,
          rect(cx - bw / 2, P.xh - P.H - 4, cx + bw / 2, P.xh + 90, P.rs),
          rect(cx - bw / 2, -90, cx + bw / 2, P.H + 4, P.rs))
    return Glyph('cent', c.width, b.cs, UNICODES['cent'])


def g_yen(P):
    y = G.g_Y(P)
    x0, y0, x1, y1 = bbox(y.contours)
    cx = (x0 + x1) / 2
    hw = (x1 - x0) * 0.30
    b = B(P)
    b.add(y.contours,
          rect(cx - hw, P.cap * 0.38 - P.H / 2, cx + hw, P.cap * 0.38 + P.H / 2, P.rs),
          rect(cx - hw, P.cap * 0.20 - P.H / 2, cx + hw, P.cap * 0.20 + P.H / 2, P.rs))
    return Glyph('yen', y.width, b.cs, UNICODES['yen'])


def g_sterling(P):
    """Pound: a stem with an f-style hook at the top, a crossbar, and a
    bottom bar."""
    b = B(P)
    xs = P.sb_bar + 70
    xt = xs + P.V + cw(P, 150) + 0.3 * (P.V - V_L)
    rf = P.rc * 0.8
    ri = inner_radius(P, rf)
    hw = max(xt - xs + P.V + ri + 6, 2 * P.V + 2 * ri + 10, 2 * rf + 2)
    yh = P.cap * 0.45
    xr = xs + ow(P, 430)
    b.add(stem(P, xs, 0, yh + 40),
          arc(xs, yh - P.H - 20, xs + hw, P.cap + P.os, (rf, rf, 0, 0), P.V, P.H,
              ('x', xt, 'top'), ('y', yh + 20, 'left'), P.ri_min),
          bar(P, xs - 70, xs + P.V + cw(P, 120), bar_y(P, 0.43)),
          bar(P, xs - 70, xr, 0))
    return b.finish('sterling', P.sb_bar)


def g_Euro(P):
    c = G.g_C(P)
    x0, y0, x1, y1 = bbox(c.contours)
    b = B(P)
    xe = x0 + (x1 - x0) * 0.62
    b.add(c.contours,
          bar(P, x0 - P.sb_round, xe, bar_y(P, 0.58)),
          bar(P, x0 - P.sb_round, xe, bar_y(P, 0.40)))
    return Glyph('Euro', c.width, b.cs, UNICODES['Euro'])


# ================================================================ registry
def ext_funcs():
    """Drawn (non-composite) glyph functions added in v4."""
    fns = {
        'dotlessi': g_dotlessi, 'dotlessj': g_dotlessj,
        'AE': g_AE, 'OE': g_OE, 'ae': g_ae, 'oe': g_oe, 'Eth': g_Eth, 'eth': g_eth,
        'Thorn': g_Thorn, 'thorn': g_thorn, 'germandbls': g_germandbls,
        'Oslash': g_Oslash, 'oslash': g_oslash, 'mu': g_mu,
        'onesuperior': g_onesuperior, 'twosuperior': g_twosuperior,
        'threesuperior': g_threesuperior, 'onequarter': g_onequarter,
        'onehalf': g_onehalf, 'threequarters': g_threequarters, 'fraction': g_fraction,
        'ordfeminine': g_ordfeminine, 'ordmasculine': g_ordmasculine,
        'copyright': g_copyright, 'registered': g_registered, 'trademark': g_trademark,
        'uni00A0': g_uni00A0,
        'exclamdown': g_exclamdown, 'questiondown': g_questiondown,
        'endash': g_endash, 'emdash': g_emdash, 'minus': g_minus,
        'multiply': g_multiply, 'divide': g_divide, 'plusminus': g_plusminus,
        'logicalnot': g_logicalnot, 'less': g_less, 'greater': g_greater,
        'guillemotleft': g_guillemotleft, 'guillemotright': g_guillemotright,
        'guilsinglleft': g_guilsinglleft, 'guilsinglright': g_guilsinglright,
        'backslash': g_backslash, 'asciicircum': g_asciicircum, 'asciitilde': g_asciitilde,
        'braceleft': g_braceleft, 'braceright': g_braceright, 'brokenbar': g_brokenbar,
        'bullet': g_bullet, 'periodcentered': g_periodcentered, 'ellipsis': g_ellipsis,
        'quoteleft': g_quoteleft, 'quoteright': g_quoteright,
        'quotesinglbase': g_quotesinglbase, 'quotedblleft': g_quotedblleft,
        'quotedblright': g_quotedblright, 'quotedblbase': g_quotedblbase,
        'dagger': g_dagger, 'daggerdbl': g_daggerdbl, 'perthousand': g_perthousand,
        'section': g_section, 'paragraph': g_paragraph, 'degree': g_degree,
        'currency': g_currency, 'cent': g_cent, 'yen': g_yen, 'sterling': g_sterling,
        'Euro': g_Euro,
    }
    for n in SPACING_OF:
        fns[n] = (lambda P, n=n: spacing_mark(n, P))
    for n in MARKS:
        fns[n] = (lambda P, n=n: mark_glyph(n, P))
    return fns


FIG_NAMES = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']


def pnum_funcs():
    return {n + '.pnum': (lambda P, f=getattr(G, 'g_' + n): f(P, prop=True)) for n in FIG_NAMES}
