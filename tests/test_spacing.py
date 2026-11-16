"""Spacing audit of the three drawn masters (generator/check_spacing.py):
no ink outside the advance, and no pair of glyphs whose outlines cross at
default spacing and kerning."""
from __future__ import annotations

import pytest

import check_spacing
from params import MASTERS


@pytest.fixture(scope='module', params=MASTERS, ids=lambda P: P.name)
def audit(request):
    return check_spacing.audit(request.param, quiet=True)


def test_ink_stays_inside_the_advance(audit):
    assert audit['outside'] == []


def test_no_pair_of_glyphs_collides(audit):
    msg = '\n'.join(f'{a} {b}: gap {g:.1f}' for g, a, b in audit['crossing'])
    assert audit['crossing'] == [], 'pairs that cross at default spacing (add a kern or fix the sidebearing):\n' + msg
