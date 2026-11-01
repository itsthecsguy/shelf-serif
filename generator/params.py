"""Weight parameters for the three masters.  All values in font units (UPM 1000).

The numbers come from measuring the GROK BOT SHELF wordmark by pixel
coverage.  Cap height in the image measured is 28.75 px.  Medians over the flat-sided letters:

    vertical stem       4.50 px = 0.157 cap  -> 110 units on a 700 cap
    horizontal stroke   3.84 px = 0.134 cap  ->  94 units  (H/V = 0.85)
    diagonal (K arms)   ~4.3 px perpendicular -> 0.95 V
    letter ink width    0.69 (L) to 0.84 (O) of cap, per letter in glyphs.py
    O counter           0.49 cap              -> 340 units
    corner              coverage missing in an 8x8 px window at the O's
                        top-left is 29.5 px^2: between a quarter circle of
                        r = 11.7 px and a chamfer of leg 7.7 px; v3 uses
                        r = 0.21 cap with geom.CORNER_TENSION (calibrated to
                        the same missing area)
    bars (H, E, F, B)   centre at 0.485 cap from the baseline
    letter gap          0.645 cap (median), word gap 1.47 cap

Light is the master that matches the logo.  Regular and Bold are scaled up
from it (x1.29 and x1.73 on the stem); outer widths grow by 0.8 of the stem
increase on caps and 1.2 on lowercase (see glyphs.ow / glyphs.cw).

v5: Regular and Bold return to the launch video's stems and widths.  Bold's
outer horizontals drop from 162 to 140, and the middle stroke of a stacked
glyph (`waist`) is 104, so the B counters are 0.24 and 0.21 of the cap height
tall (0.17 and 0.14 in the video).  Every weight draws the same R.
"""
from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass
class Params:
    name: str
    wght: int
    V: float      # vertical stem thickness
    H: float      # horizontal stroke thickness (0.85 V, as measured)
    ser: float    # shelf-serif thickness (hairline)
    serL: float   # shelf-serif overhang beyond the stem, each side
    rs: float     # corner radius of stems / bars / serifs
    rc: float     # outer corner radius of cap bowls (O, C, G, Q, 0)
    rx: float     # outer corner radius of lowercase bowls (o, b, d ...)
    os: float     # overshoot for rounded shapes
    dot: float    # dot size (i, j, punctuation)
    # shared vertical metrics
    cap: float = 700
    xh: float = 520
    asc: float = 730
    desc: float = -200
    # spacing: distances from the ink to the advance edge
    sb_stem: float = 56    # from the stem face (serifs sit inside this)
    sb_bar: float = 42     # ends of bars (E, L, T, Z)
    sb_round: float = 44   # bowls
    sb_diag: float = 22    # diagonal ends (serif edge)
    sb_term: float = 40    # open terminals (C, S, e, c)
    # v4: reduced-size derivatives (superiors, the C in the copyright
    # ring, the TM) scale every length by `scale` but keep the parent's
    # stem (`V_ref`) in the width model, see glyphs._dv()
    scale: float = 1.0
    V_ref: float | None = None
    # v5: how many units of stem the crowded glyphs (a, e, k, 8) give back so
    # their counters stay open.  Zero in Light and Regular, whose shapes
    # are the launch video's; only Bold has it.
    relief: float = 0.0
    # v5: thickness of a waist stroke, the middle horizontal of a stacked
    # glyph (B, E, R, S, 8 ...).  None means the same as H; only Bold thins it.
    waist: float | None = None

    @property
    def Hw(self):
        return self.H if self.waist is None else self.waist

    @property
    def Vd(self):
        """Diagonal stroke thickness (perpendicular)."""
        return self.V * 0.95

    @property
    def ri_min(self):
        return 5.0

    @property
    def serL_lc(self):
        """Lowercase serif overhang: shorter, so hairlines never run into
        the next glyph in text spacing."""
        return self.serL * 0.75


# Light's stem: the reference for the width model in glyphs.py.
V_L = 110

LIGHT = Params(
    name="Light", wght=300,
    V=110, H=94, ser=20, serL=24, rs=7,
    rc=148, rx=104, os=6, dot=126,
)

REGULAR = Params(
    name="Regular", wght=400,
    V=142, H=121, ser=24, serL=26, rs=8,
    rc=152, rx=108, os=7, dot=160,
)

BOLD = Params(
    name="Bold", wght=700,
    V=190, H=140, ser=30, serL=28, rs=9,
    rc=158, rx=114, os=8, dot=212,
    relief=54, waist=104,
)

MASTERS = [LIGHT, REGULAR, BOLD]


def small(P: Params, s: float, k: float, max_ratio: float = 0.26) -> Params:
    """v4: a parameter set for a glyph drawn at `s` of the normal size with
    strokes at `k` of the normal thickness (k > s, so small shapes do not
    go hairline).  The stem is capped at `max_ratio` of the reduced cap
    height so Bold counters stay open.  Used for superiors, fractions,
    ordinals, the C and R inside the copyright and registered rings and
    the TM."""
    V = min(P.V * k, max_ratio * P.cap * s)
    kk = V / P.V
    return replace(
        P,
        cap=P.cap * s, xh=P.xh * s, asc=P.asc * s, desc=P.desc * s,
        V=V, H=P.H * kk, ser=P.ser * kk, serL=P.serL * s,
        waist=None if P.waist is None else P.waist * kk,
        rc=P.rc * s, rx=P.rx * s, os=P.os * s, dot=P.dot * kk,
        sb_stem=P.sb_stem * s, sb_bar=P.sb_bar * s, sb_round=P.sb_round * s,
        sb_diag=P.sb_diag * s, sb_term=P.sb_term * s,
        scale=s * (P.scale if P.scale else 1.0),
        V_ref=P.V_ref if P.V_ref is not None else P.V,
    )
