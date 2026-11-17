"""A text snapshot of every glyph in every static weight.

The fonts are binary, so a pull request that changes an outline shows no
readable diff.  This writes tests/snapshots/glyphs.tsv, one line per glyph
per weight, with the numbers a reviewer would want to see move: advance,
side bearings, bounding box, contour and point counts, ink area and a short
hash of the outline.  tests/test_snapshot.py fails when the built fonts no
longer match it, so every glyph change has to be accepted on purpose by
running

    python tools/glyph_snapshot.py --update        (or: make snapshot)

and committing the new file, whose git diff then names the glyphs that
changed and by how much.  All values are in 2048-upm font units.
"""
from __future__ import annotations

import hashlib
import os
import sys

from fontTools.pens.areaPen import AreaPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = os.path.join(ROOT, 'tests', 'snapshots', 'glyphs.tsv')
STYLES = ('Light', 'Regular', 'Medium', 'SemiBold', 'Bold')
HEADER = ('weight', 'glyph', 'unicode', 'advance', 'lsb', 'rsb', 'xmin', 'ymin', 'xmax', 'ymax',
          'contours', 'points', 'area', 'outline')


def rows_for_font(path, style):
    f = TTFont(path)
    gs = f.getGlyphSet()
    rev = {}
    for u, n in sorted(f.getBestCmap().items()):
        rev.setdefault(n, u)
    rows = []
    for name in f.getGlyphOrder():
        g = gs[name]
        rec = DecomposingRecordingPen(gs)
        g.draw(rec)
        bp = BoundsPen(gs)
        g.draw(bp)
        ap = AreaPen(gs)
        g.draw(ap)
        contours = sum(1 for op, _ in rec.value if op == 'moveTo')
        points = sum(len(args) for op, args in rec.value if op not in ('closePath', 'endPath'))
        h = hashlib.sha1(repr(rec.value).encode()).hexdigest()[:10] if rec.value else '-'
        if bp.bounds:
            xmin, ymin, xmax, ymax = (int(round(v)) for v in bp.bounds)
            lsb, rsb = xmin, g.width - xmax
        else:
            xmin = ymin = xmax = ymax = lsb = rsb = '-'
        u = f'U+{rev[name]:04X}' if name in rev else '-'
        rows.append((style, name, u, g.width, lsb, rsb, xmin, ymin, xmax, ymax,
                     contours, points, int(round(abs(ap.value))), h))
    return rows


def render(fonts_dir=None):
    fonts_dir = fonts_dir or os.path.join(ROOT, 'fonts', 'otf')
    lines = ['\t'.join(HEADER)]
    for style in STYLES:
        for row in rows_for_font(os.path.join(fonts_dir, f'ShelfSerif-{style}.otf'), style):
            lines.append('\t'.join(str(v) for v in row))
    return '\n'.join(lines) + '\n'


def read_snapshot(path=SNAPSHOT):
    with open(path) as fh:
        return fh.read()


def diff_lines(old, new):
    """Lines that differ, keyed by (weight, glyph): returns a list of
    human-readable strings."""
    def index(text):
        out = {}
        lines = text.splitlines()
        header = lines[0].split('\t')
        for line in lines[1:]:
            cells = line.split('\t')
            out[(cells[0], cells[1])] = dict(zip(header, cells))
        return out
    a, b = index(old), index(new)
    msgs = []
    for key in sorted(set(a) | set(b)):
        if key not in a:
            msgs.append(f'{key[0]} {key[1]}: new glyph')
        elif key not in b:
            msgs.append(f'{key[0]} {key[1]}: glyph removed')
        elif a[key] != b[key]:
            moved = [f'{k} {a[key][k]} -> {b[key][k]}' for k in HEADER[2:] if a[key][k] != b[key][k]]
            msgs.append(f'{key[0]} {key[1]}: ' + ', '.join(moved))
    return msgs


def main():
    new = render()
    if '--update' in sys.argv:
        os.makedirs(os.path.dirname(SNAPSHOT), exist_ok=True)
        old = read_snapshot() if os.path.exists(SNAPSHOT) else None
        with open(SNAPSHOT, 'w') as fh:
            fh.write(new)
        changed = diff_lines(old, new) if old else []
        print(f'wrote {os.path.relpath(SNAPSHOT, ROOT)}' + (f', {len(changed)} line(s) changed' if old else ''))
        for m in changed:
            print('  ' + m)
        return
    if not os.path.exists(SNAPSHOT):
        sys.exit(f'no snapshot at {SNAPSHOT}; run with --update to create it')
    changed = diff_lines(read_snapshot(), new)
    for m in changed:
        print(m)
    print(f'{len(changed)} glyph(s) differ from the snapshot' if changed else 'fonts match the snapshot')
    sys.exit(1 if changed else 0)


if __name__ == '__main__':
    main()
