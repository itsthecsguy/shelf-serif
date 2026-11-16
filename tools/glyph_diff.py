"""Show which glyphs changed between two builds, as before-and-after images.

Compares the static OTFs of a base (a git ref, by default HEAD, or a folder)
with the fonts in the working tree, glyph by glyph and weight by weight.  A
glyph counts as changed when its outline or its advance differs.  For each
changed glyph it writes one PNG with three rows across the five weights:

    before   the base outline, with its advance marked
    after    the new outline
    diff     ink in both in dark grey, ink only before in red, ink only
             after in blue; red and blue lines are the old and new advance

It also writes overview.png (the diff row of every changed glyph),
summary.md (a table for people and for a CI job summary) and summary.json.

Usage:
    python tools/glyph_diff.py                    # working tree vs HEAD
    python tools/glyph_diff.py --base origin/main
    python tools/glyph_diff.py --base-dir /path/to/old/otf --out build/glyph-diff

Exit status is 0 whether or not anything changed; pass --fail-on-change to
exit 1 when a glyph changed (useful in a script that expects no change).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageChops, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glyph_render import Y_BOTTOM, Y_TOP, glyph_mask, label_font  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLES = ('Light', 'Regular', 'Medium', 'SemiBold', 'Bold')
BOTH = (40, 40, 40)
BEFORE = (214, 48, 49)
AFTER = (9, 111, 214)
GUIDE = (205, 205, 205)
LEFT, TOP, GAP = 64, 30, 6


def font_path(folder, style):
    return os.path.join(folder, f'ShelfSerif-{style}.otf')


def extract_ref(ref, dest):
    """Write the committed OTFs at `ref` into `dest`.  Returns the styles
    that exist at that ref."""
    found = []
    for style in STYLES:
        rel = f'fonts/otf/ShelfSerif-{style}.otf'
        res = subprocess.run(['git', 'show', f'{ref}:{rel}'], cwd=ROOT, capture_output=True)
        if res.returncode == 0:
            with open(font_path(dest, style), 'wb') as fh:
                fh.write(res.stdout)
            found.append(style)
    if not found:
        sys.exit(f'glyph_diff: no fonts/otf files at {ref!r}; is it a valid git ref with fetched history?')
    return found


def has(font, name):
    return font is not None and name in font.getGlyphSet()


def signature(font, name):
    gs = font.getGlyphSet()
    pen = DecomposingRecordingPen(gs)
    gs[name].draw(pen)
    return gs[name].width, tuple(pen.value)


def compare(base_dir, head_dir):
    """Returns (changes, added, removed) where changes maps glyph name to
    {style: (old_advance, new_advance)} for each style the glyph changed in."""
    changes, added, removed = {}, set(), set()
    for style in STYLES:
        bp, hp = font_path(base_dir, style), font_path(head_dir, style)
        if not (os.path.exists(bp) and os.path.exists(hp)):
            continue
        b, h = TTFont(bp), TTFont(hp)
        bnames, hnames = set(b.getGlyphOrder()), set(h.getGlyphOrder())
        added |= hnames - bnames
        removed |= bnames - hnames
        for name in h.getGlyphOrder():
            if name in bnames:
                sb, sh = signature(b, name), signature(h, name)
                if sb != sh:
                    changes.setdefault(name, {})[style] = (sb[0], sh[0])
    return changes, sorted(added), sorted(removed)


def cell(pair, name, scale, width_px, kind):
    """One weight's cell.  kind is 'before', 'after' or 'diff'; pair is
    (base TTFont or None, head TTFont or None)."""
    base, head = pair
    h = int(round((Y_TOP - Y_BOTTOM) * scale))
    x0 = 12
    img = Image.new('RGB', (width_px, h), (255, 255, 255))
    d = ImageDraw.Draw(img)
    base_y = int(Y_TOP * scale)
    d.line([(0, base_y), (width_px, base_y)], fill=GUIDE)
    d.line([(x0, 0), (x0, h)], fill=GUIDE)

    def mask(font):
        if not has(font, name):
            return Image.new('L', (width_px, h), 0)
        return glyph_mask(font, name, scale, width_px, x0)

    def advance_line(font, colour):
        if has(font, name):
            x = x0 + font['hmtx'][name][0] * scale
            d.line([(x, 0), (x, h)], fill=colour)

    if kind == 'before':
        img.paste(BOTH, mask=mask(base))
        advance_line(base, BEFORE)
    elif kind == 'after':
        img.paste(BOTH, mask=mask(head))
        advance_line(head, AFTER)
    else:
        mb, mh = mask(base), mask(head)
        img.paste(BOTH, mask=ImageChops.multiply(mb, mh))
        img.paste(BEFORE, mask=ImageChops.subtract(mb, mh))
        img.paste(AFTER, mask=ImageChops.subtract(mh, mb))
        advance_line(base, BEFORE)
        if not (has(base, name) and has(head, name)) or base['hmtx'][name][0] != head['hmtx'][name][0]:
            advance_line(head, AFTER)
    return img


def cell_width(pairs, name, scale):
    widest = 0
    for pair in pairs:
        for f in pair:
            if has(f, name):
                gs = f.getGlyphSet()
                bp = BoundsPen(gs)
                gs[name].draw(bp)
                widest = max(widest, gs[name].width, bp.bounds[2] if bp.bounds else 0)
    return int(widest * scale) + 36


def glyph_sheet(name, pairs, styles, changed_styles, scale):
    w = cell_width(pairs, name, scale)
    h = int(round((Y_TOP - Y_BOTTOM) * scale))
    sheet = Image.new('RGB', (LEFT + len(styles) * (w + GAP), TOP + 3 * (h + GAP) + 10), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    lf = label_font(13)
    d.text((8, 6), name, font=label_font(16), fill=(0, 0, 0))
    for r, kind in enumerate(('before', 'after', 'diff')):
        d.text((8, TOP + r * (h + GAP) + h // 2), kind, font=lf, fill=(90, 90, 90))
        for c, (style, pair) in enumerate(zip(styles, pairs)):
            x = LEFT + c * (w + GAP)
            sheet.paste(cell(pair, name, scale, w, kind), (x, TOP + r * (h + GAP)))
            if r == 0:
                changed = style in changed_styles
                d.text((x + 4, 8), style + (' *' if changed else ''), font=lf,
                       fill=(0, 0, 0) if changed else (150, 150, 150))
    return sheet


def diff_row(sheet, name, scale):
    h = int(round((Y_TOP - Y_BOTTOM) * scale))
    top = TOP + 2 * (h + GAP)
    row = Image.new('RGB', (sheet.width, h + 4), (255, 255, 255))
    row.paste(sheet.crop((0, top, sheet.width, top + h)), (0, 2))
    ImageDraw.Draw(row).text((8, 4), name, font=label_font(13), fill=(0, 0, 0))
    return row


def stack(rows):
    out = Image.new('RGB', (max(r.width for r in rows), sum(r.height for r in rows)), (255, 255, 255))
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.height
    return out


def safe_name(name):
    return ''.join(ch if ch.isalnum() or ch in '._-' else '_' for ch in name)


def write_summary(out, changes, added, removed, base_label, files):
    lines = [f'## Glyph changes against `{base_label}`', '']
    if not (changes or added or removed):
        lines.append('No glyph outlines or advances changed.')
    else:
        lines.append(f'{len(changes)} glyph(s) changed. In the images, red is ink that was removed, '
                     'blue is ink that was added, and dark grey is unchanged.')
        if changes:
            lines += ['', '| Glyph | Weights changed | Advance, before → after (2048 upm) |', '| --- | --- | --- |']
            for name, per in changes.items():
                advs = sorted({(a, b) for a, b in per.values() if a != b})
                adv_txt = ', '.join(f'{a} → {b}' for a, b in advs) if advs else 'unchanged'
                lines.append(f'| `{name}` | {", ".join(s for s in STYLES if s in per)} | {adv_txt} |')
        if added:
            lines += ['', 'Added: ' + ', '.join(f'`{n}`' for n in added)]
        if removed:
            lines += ['', 'Removed: ' + ', '.join(f'`{n}`' for n in removed)]
        lines += ['', 'Images: `overview.png`, and one PNG per glyph with before, after and diff rows.']
    text = '\n'.join(lines) + '\n'
    with open(os.path.join(out, 'summary.md'), 'w') as fh:
        fh.write(text)
    with open(os.path.join(out, 'summary.json'), 'w') as fh:
        json.dump({'base': base_label,
                   'changed': {n: {s: {'advance_before': a, 'advance_after': b} for s, (a, b) in per.items()}
                               for n, per in changes.items()},
                   'added': added, 'removed': removed, 'images': files}, fh, indent=2)
        fh.write('\n')
    return text


def run(base_dir, head_dir, out, base_label, size=180, limit=200):
    """Compare two folders of OTFs and write the images and summaries into
    `out` (emptied first).  Returns (changes, added, removed, summary text)."""
    changes, added, removed = compare(base_dir, head_dir)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    scale = size / (Y_TOP - Y_BOTTOM)
    styles = [s for s in STYLES if os.path.exists(font_path(head_dir, s)) or os.path.exists(font_path(base_dir, s))]
    pairs = [tuple(TTFont(p) if os.path.exists(p) else None
                   for p in (font_path(base_dir, s), font_path(head_dir, s))) for s in styles]
    order = {n: i for i, n in enumerate(pairs[0][1].getGlyphOrder())} if pairs and pairs[0][1] else {}
    names = sorted(changes, key=lambda n: order.get(n, 1e9)) + added + removed
    files, rows = [], []
    for name in names[:limit]:
        sheet = glyph_sheet(name, pairs, styles, set(changes.get(name, styles)), scale)
        fn = f'{safe_name(name)}.png'
        sheet.save(os.path.join(out, fn))
        files.append(fn)
        rows.append(diff_row(sheet, name, scale))
    if rows:
        stack(rows).save(os.path.join(out, 'overview.png'))
        files.insert(0, 'overview.png')
    text = write_summary(out, changes, added, removed, base_label, files)
    return changes, added, removed, text


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--base', default='HEAD', help='git ref whose committed fonts are the "before" (default HEAD)')
    ap.add_argument('--base-dir', help='folder of ShelfSerif-*.otf to use as the "before" instead of a git ref')
    ap.add_argument('--head-dir', default=os.path.join(ROOT, 'fonts', 'otf'),
                    help='folder of ShelfSerif-*.otf to use as the "after" (default fonts/otf)')
    ap.add_argument('--out', default=os.path.join(ROOT, 'build', 'glyph-diff'))
    ap.add_argument('--size', type=int, default=180, help='cell height in pixels')
    ap.add_argument('--fail-on-change', action='store_true')
    args = ap.parse_args(argv)

    tmp = None
    try:
        if args.base_dir:
            base_dir, label = args.base_dir, args.base_dir
        else:
            tmp = tempfile.mkdtemp(prefix='glyph-diff-')
            extract_ref(args.base, tmp)
            base_dir, label = tmp, args.base
        changes, added, removed, text = run(base_dir, args.head_dir, args.out, label, args.size)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    print(text.rstrip())
    print(f'\nwrote {os.path.relpath(args.out)}/')
    if args.fail_on_change and (changes or added or removed):
        sys.exit(1)


if __name__ == '__main__':
    main()
