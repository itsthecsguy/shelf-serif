"""Every glyph change must be accepted on purpose.  If this fails after a
deliberate change, run `make snapshot` (python tools/glyph_snapshot.py
--update), look at `make diff`, and commit tests/snapshots/glyphs.tsv."""
from __future__ import annotations

import glyph_snapshot


def test_fonts_match_the_glyph_snapshot():
    changed = glyph_snapshot.diff_lines(glyph_snapshot.read_snapshot(), glyph_snapshot.render())
    assert not changed, (
        f'{len(changed)} glyph(s) differ from tests/snapshots/glyphs.tsv.\n'
        'If the change is intended, run `make snapshot` and commit the file; '
        'run `make diff` to see the glyphs.\n' + '\n'.join(changed[:40]))
