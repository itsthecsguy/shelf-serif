"""Render a set of glyphs by name from the built fonts, large, in every
master, for a visual pass.  Uses the glyph names directly (via the cmap
or the glyph order), so unencoded glyphs such as zero.pnum work too.

    python generator/preview.py out.png name1 name2 ... [--size 220] [--fmt otf]
"""
from __future__ import annotations

import os
import sys

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    args = sys.argv[1:]
    size = 220
    fmt = 'otf'
    if '--size' in args:
        i = args.index('--size')
        size = int(args[i + 1])
        del args[i:i + 2]
    if '--fmt' in args:
        i = args.index('--fmt')
        fmt = args[i + 1]
        del args[i:i + 2]
    out, names = args[0], args[1:]
    rows = []
    for style in ('Light', 'Regular', 'Bold'):
        path = os.path.join(ROOT, 'fonts', fmt, f'ShelfSerif-{style}.{fmt}')
        tt = TTFont(path)
        rev = {}
        for u, n in tt.getBestCmap().items():
            rev.setdefault(n, u)
        f = ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
        # unencoded glyphs: use the PUA via a temporary cmap? Simpler: draw
        # by glyph index through the 'basic' layout with a private font copy.
        text = ''
        missing = []
        for n in names:
            if n in rev:
                text += chr(rev[n])
            else:
                missing.append(n)
        rows.append((style, f, text, missing, tt))
    W = int(max(f.getlength(t) + len(m) * size * 0.8 for _, f, t, m, _ in rows)) + 160
    H = int(size * 1.6) * len(rows) + 60
    img = Image.new('RGB', (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    y = int(size * 1.15)
    for style, f, text, missing, tt in rows:
        d.text((40, y), text, font=f, fill=(0, 0, 0), anchor='ls')
        if missing:
            # render unencoded glyphs via a PUA-mapped copy of the font
            tmp = f'/tmp/_preview_{style}.{fmt}'
            cmap = tt['cmap']
            for sub in cmap.tables:
                if sub.isUnicode():
                    for i, n in enumerate(missing):
                        sub.cmap[0xE000 + i] = n
            tt.save(tmp)
            f2 = ImageFont.truetype(tmp, size, layout_engine=ImageFont.Layout.RAQM)
            d.text((40 + f.getlength(text) + 40, y), ''.join(chr(0xE000 + i) for i in range(len(missing))),
                   font=f2, fill=(0, 0, 0), anchor='ls')
        d.text((40, y - size * 1.05), style, font=ImageFont.truetype(
            os.path.join(ROOT, 'fonts', fmt, f'ShelfSerif-Regular.{fmt}'), 18), fill=(130, 130, 130))
        y += int(size * 1.6)
    img.save(out)
    print('wrote', out)


if __name__ == '__main__':
    main()
