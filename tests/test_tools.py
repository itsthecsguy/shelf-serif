"""The review tools themselves: glyph_diff must notice a changed outline
and a changed advance, and stay quiet when nothing changed."""
from __future__ import annotations

import json
import os
import shutil

import pytest
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen

import glyph_diff
import glyph_snapshot
from conftest import FONTS, STYLES


@pytest.fixture
def head_dir(tmp_path):
    d = tmp_path / 'head'
    d.mkdir()
    for s in STYLES:
        shutil.copy(os.path.join(FONTS, 'otf', f'ShelfSerif-{s}.otf'), d)
    return d


def nudge_glyph(path, name, dx=0, extra_advance=0):
    """Move one glyph's outline right by dx and widen its advance."""
    from fontTools.ttLib import TTFont
    font = TTFont(path)
    gs = font.getGlyphSet()
    rec = RecordingPen()
    gs[name].draw(rec)
    adv, lsb = font['hmtx'][name]
    pen = T2CharStringPen(adv + extra_advance, gs)
    rec.replay(TransformPen(pen, (1, 0, 0, 1, dx, 0)))
    cff = font['CFF '].cff
    top = cff[cff.fontNames[0]]
    cs = pen.getCharString(private=top.Private, globalSubrs=cff.GlobalSubrs)
    top.CharStrings[name] = cs
    font['hmtx'][name] = (adv + extra_advance, lsb + dx)
    font.save(path)


def test_no_changes_against_itself(tmp_path):
    otf = os.path.join(FONTS, 'otf')
    changes, added, removed, text = glyph_diff.run(otf, otf, str(tmp_path / 'out'), 'self')
    assert (changes, added, removed) == ({}, [], [])
    assert 'No glyph outlines or advances changed' in text


def test_reports_a_changed_glyph_with_images(tmp_path, head_dir):
    nudge_glyph(str(head_dir / 'ShelfSerif-Bold.otf'), 'Q', dx=40, extra_advance=40)
    out = tmp_path / 'out'
    changes, _, _, text = glyph_diff.run(os.path.join(FONTS, 'otf'), str(head_dir), str(out), 'base')
    assert list(changes) == ['Q']
    assert list(changes['Q']) == ['Bold']
    old, new = changes['Q']['Bold']
    assert new == old + 40
    assert (out / 'Q.png').exists() and (out / 'overview.png').exists()
    summary = json.loads((out / 'summary.json').read_text())
    assert 'Q' in summary['changed']
    assert '`Q`' in text


def test_snapshot_diff_names_what_moved(tmp_path, head_dir):
    nudge_glyph(str(head_dir / 'ShelfSerif-Light.otf'), 'O', extra_advance=10)
    before = glyph_snapshot.render(os.path.join(FONTS, 'otf'))
    after = glyph_snapshot.render(str(head_dir))
    msgs = glyph_snapshot.diff_lines(before, after)
    assert len(msgs) == 1
    assert msgs[0].startswith('Light O:') and 'advance' in msgs[0]
