"""Kerning.  Values are drawn for the Light master (the logo weight) in
1000-unit design space and scale with the stem weight for Regular and Bold.

v4: kerning is class based.  Accented letters inherit their base letter's
pairs through the groups below, so the UFO carries public.kern1 /
public.kern2 groups and the pairs reference a group where one exists.
"""
from __future__ import annotations

from params import Params, V_L

# left-side and right-side classes share these memberships
GROUPS = {
    'A': ['A', 'Agrave', 'Aacute', 'Acircumflex', 'Atilde', 'Adieresis', 'Aring'],
    'C': ['C', 'Ccedilla'],
    'E': ['E', 'Egrave', 'Eacute', 'Ecircumflex', 'Edieresis'],
    'O': ['O', 'Ograve', 'Oacute', 'Ocircumflex', 'Otilde', 'Odieresis', 'Oslash'],
    'U': ['U', 'Ugrave', 'Uacute', 'Ucircumflex', 'Udieresis'],
    'Y': ['Y', 'Yacute', 'Ydieresis'],
    'a': ['a', 'agrave', 'aacute', 'acircumflex', 'atilde', 'adieresis', 'aring'],
    'c': ['c', 'ccedilla'],
    'e': ['e', 'egrave', 'eacute', 'ecircumflex', 'edieresis'],
    'o': ['o', 'ograve', 'oacute', 'ocircumflex', 'otilde', 'odieresis', 'oslash'],
    'u': ['u', 'ugrave', 'uacute', 'ucircumflex', 'udieresis'],
    'y': ['y', 'yacute', 'ydieresis'],
    'period': ['period', 'ellipsis'],
    'hyphen': ['hyphen', 'endash', 'emdash'],
    'quotesingle': ['quotesingle', 'quoteleft', 'quoteright'],
    'quotedbl': ['quotedbl', 'quotedblleft', 'quotedblright'],
    'j': ['j', 'dotlessj'],
}

# (left, right): value in Light units (negative = tighter)
PAIRS = {
    ('A', 'V'): -74, ('V', 'A'): -74, ('A', 'W'): -56, ('W', 'A'): -56,
    ('A', 'Y'): -76, ('Y', 'A'): -76, ('A', 'T'): -66, ('T', 'A'): -66,
    ('L', 'T'): -70, ('L', 'V'): -66, ('L', 'Y'): -72, ('L', 'W'): -52,
    ('P', 'A'): -56, ('F', 'A'): -50, ('T', 'J'): -40, ('R', 'V'): -24,
    ('R', 'Y'): -30, ('K', 'O'): -20, ('A', 'O'): -14, ('O', 'A'): -14,
    ('T', 'o'): -62, ('T', 'e'): -62, ('T', 'a'): -60, ('T', 'c'): -62,
    ('T', 's'): -50, ('T', 'r'): -44, ('T', 'y'): -44, ('T', 'u'): -46,
    ('T', 'i'): -14,
    ('Y', 'o'): -60, ('Y', 'e'): -60, ('Y', 'a'): -56, ('Y', 'u'): -44,
    ('Y', 's'): -46,
    ('V', 'o'): -42, ('V', 'e'): -42, ('V', 'a'): -40, ('V', 'u'): -24,
    ('W', 'o'): -30, ('W', 'e'): -30, ('W', 'a'): -28,
    ('P', 'o'): -14, ('P', 'e'): -14, ('P', 'a'): -14,
    ('T', 'period'): -80, ('T', 'comma'): -80, ('T', 'hyphen'): -60,
    ('Y', 'period'): -80, ('Y', 'comma'): -80, ('Y', 'hyphen'): -50,
    ('V', 'period'): -70, ('V', 'comma'): -70,
    ('W', 'period'): -50, ('W', 'comma'): -50,
    ('P', 'period'): -84, ('P', 'comma'): -84,
    ('F', 'period'): -70, ('F', 'comma'): -70,
    ('r', 'period'): -56, ('r', 'comma'): -56, ('r', 'a'): -14,
    ('y', 'period'): -50, ('y', 'comma'): -50,
    ('v', 'period'): -46, ('v', 'comma'): -46,
    ('w', 'period'): -34, ('w', 'comma'): -34,
    ('f', 'period'): -20, ('f', 'comma'): -20,
    ('o', 'v'): -16, ('v', 'o'): -16, ('o', 'y'): -14, ('y', 'o'): -14,
    ('o', 'w'): -10, ('w', 'o'): -10, ('v', 'a'): -12, ('y', 'a'): -12,
    ('e', 'v'): -12, ('e', 'y'): -12, ('k', 'o'): -14, ('k', 'e'): -14,
    ('r', 'o'): -10, ('r', 'e'): -10, ('r', 'c'): -10,
    ('quotesingle', 'A'): -50, ('quotedbl', 'A'): -50,
    ('A', 'quotesingle'): -50, ('A', 'quotedbl'): -50,
    ('L', 'quotesingle'): -90, ('L', 'quotedbl'): -90,
    ('one', 'one'): -30, ('seven', 'period'): -40, ('seven', 'comma'): -40,
    ('parenleft', 'J'): -20,
    # v3: the j hook runs 40 units left of its origin; keep it off
    # descending or bracketing neighbours, and give K's arm tips room
    ('parenleft', 'j'): 34, ('bracketleft', 'j'): 34, ('bracketright', 'j'): 24,
    ('underscore', 'j'): 50, ('q', 'j'): 30, ('g', 'j'): 20, ('y', 'j'): 10,
    ('K', 'A'): 14, ('K', 'X'): 12, ('K', 'x'): 12,
    # v2: keep the ampersand and at-sign clear of their neighbours
    ('ampersand', 'at'): 12, ('at', 'ampersand'): 10,
    ('slash', 'ampersand'): 6, ('ampersand', 'numbersign'): 8,
    # v4: new glyphs
    ('T', 'hyphen'): -60, ('T', 'guillemotleft'): -40, ('T', 'guillemotright'): -40,
    ('V', 'hyphen'): -40, ('Y', 'guillemotleft'): -40,
    ('f', 'quotesingle'): 10, ('f', 'quotedbl'): 10, ('f', 'parenright'): 12,
    ('f', 'bracketright'): 12, ('f', 'braceright'): 12,
    ('r', 'quotesingle'): -10, ('quotesingle', 'T'): -8,
    ('braceleft', 'j'): 34, ('backslash', 'j'): 24, ('one.pnum', 'one.pnum'): -20,
    ('seven.pnum', 'period'): -40, ('seven.pnum', 'comma'): -40,
    ('A', 'C'): -10, ('A', 'U'): -10, ('L', 'O'): -14, ('L', 'C'): -12,
    ('T', 'O'): -14, ('T', 'C'): -14, ('V', 'O'): -14, ('V', 'C'): -14,
    ('Y', 'O'): -16, ('Y', 'C'): -16, ('W', 'O'): -10,
    ('O', 'V'): -14, ('O', 'Y'): -16, ('O', 'T'): -14, ('O', 'W'): -10,
    ('C', 'A'): -6, ('E', 'J'): -8,
    ('T', 'ae'): -60, ('T', 'oe'): -62, ('T', 'oslash'): -62, ('V', 'ae'): -40,
    ('Y', 'ae'): -56, ('Y', 'oe'): -60, ('V', 'oe'): -42,
    ('Thorn', 'A'): -30, ('Thorn', 'period'): -60, ('Thorn', 'comma'): -60,
    ('AE', 'J'): -8, ('Eth', 'J'): -8,
}


def scale_for(P: Params) -> float:
    # heavier masters are also wider, so the pairs grow with the square
    # root of the stem ratio (Regular x1.14, Bold x1.31), not the ratio
    return (P.V / float(V_L)) ** 0.5


def kerning_for(P: Params):
    """(groups, kerning) in 1000-unit design space.  Groups are keyed by
    their UFO names; pairs use the group name where a group exists."""
    k = scale_for(P)
    groups = {}
    for key, members in GROUPS.items():
        groups['public.kern1.' + key] = list(members)
        groups['public.kern2.' + key] = list(members)
    kerning = {}
    for (a, b), v in PAIRS.items():
        ka = 'public.kern1.' + a if a in GROUPS else a
        kb = 'public.kern2.' + b if b in GROUPS else b
        kerning[(ka, kb)] = int(round(v * k))
    return groups, kerning


def flat_kerning(P: Params) -> dict[tuple[str, str], int]:
    """Every glyph pair with a kerning value, for the audits."""
    groups, kerning = kerning_for(P)
    out = {}
    for (ka, kb), v in kerning.items():
        lefts = groups.get(ka, [ka])
        rights = groups.get(kb, [kb])
        for a in lefts:
            for b in rights:
                out[(a, b)] = v
    return out
