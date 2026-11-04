"""Render the launch video from the fonts in this repository. Needs ffmpeg with
libx264. The soundtrack is not part of this repository, so pass your own.

    pip install playwright fonttools && playwright install chromium
    python docs/make_video.py --audio track.m4a
    python docs/make_video.py --stills 3.2,9.2,20.5 --out /tmp/stills
"""
from __future__ import annotations

import argparse
import os
import subprocess

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO = os.path.join(ROOT, 'docs', 'video')
SCENE = os.path.join(VIDEO, 'scene.html')
MP4 = os.path.join(VIDEO, 'shelf-serif-launch.mp4')
FPS = 30
FRAMES = 660
# Light's stem, thin stroke, serif height and serif overhang, in 1000 units per em.
LIGHT_NUMBERS = {'stemV': 110, 'stemH': 94, 'serifH': 20, 'serifL': 24}
SETS = {'Light': 'SHELFRIAOGKQ', 'Bold': '7M3B'}


def read_contours(font, name):
    """Return a glyph's contours as path commands, plus its on- and off-curve points."""
    glyf = font['glyf']
    coords, ends, flags = glyf[name].getCoordinates(glyf)
    k = 1000 / font['head'].unitsPerEm
    contours, on, off = [], [], []
    start = 0
    for end in ends:
        pts = [(x * k, y * k, flags[i] & 1) for i, (x, y) in enumerate(coords[start:end + 1], start)]
        start = end + 1
        contours.append(pts)
        on += [(x, y) for x, y, c in pts if c]
        off += [(x, y) for x, y, c in pts if not c]
        # Two off-curve points in a row imply an on-curve point halfway between them.
        on += [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
               for a, b in zip(pts, pts[1:] + pts[:1]) if not a[2] and not b[2]]
    return contours, on, off


def rotate_to(pts, x, y, next_x):
    """Start a contour at the on-curve point nearest (x, y), heading towards next_x."""
    i = min((n for n, p in enumerate(pts) if p[2]), key=lambda n: (pts[n][0] - x) ** 2 + (pts[n][1] - y) ** 2)
    pts = pts[i:] + pts[:i]
    if abs(pts[1][0] - next_x) > abs(pts[-1][0] - next_x):
        pts = pts[:1] + pts[:0:-1]
    return pts


def to_commands(pts):
    """Turn TrueType points into M, L, Q and Z commands, filling in implied on-curve points."""
    if not pts[0][2]:
        first = next(i for i, p in enumerate(pts) if p[2])
        pts = pts[first:] + pts[:first]
    cmds = [['M', pts[0][0], pts[0][1]]]
    ring = pts[1:] + pts[:1]
    ctrl = None
    for x, y, on_curve in ring:
        if on_curve:
            cmds.append(['Q', ctrl[0], ctrl[1], x, y] if ctrl else ['L', x, y])
            ctrl = None
        else:
            if ctrl:
                cmds.append(['Q', ctrl[0], ctrl[1], (ctrl[0] + x) / 2, (ctrl[1] + y) / 2])
            ctrl = (x, y)
    cmds.append(['Z'])
    return cmds


def glyph_data():
    data = dict(LIGHT_NUMBERS)
    for style, chars in SETS.items():
        font = TTFont(os.path.join(ROOT, 'fonts', 'ttf', f'ShelfSerif-{style}.ttf'))
        k = 1000 / font['head'].unitsPerEm
        cmap, glyphset = font.getBestCmap(), font.getGlyphSet()
        data[style] = {}
        for c in chars:
            name = cmap[ord(c)]
            contours, on, off = read_contours(font, name)
            if style == 'Light' and c == 'S':
                # The opening shot draws the S from the end of its upper terminal.
                contours = [rotate_to(contours[0], 561, 510, 450)]
            pen = BoundsPen(glyphset)
            glyphset[name].draw(pen)
            data[style][c] = {
                'contours': [to_commands(p) for p in contours], 'on': on, 'off': off,
                'adv': round(font['hmtx'][name][0] * k), 'xMax': pen.bounds[2] * k,
                'yMin': pen.bounds[1] * k, 'yMax': pen.bounds[3] * k,
            }
    return data


def open_page(browser):
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    page.goto('file://' + SCENE.replace('[', '%5B').replace(']', '%5D'))
    page.evaluate('data => init(data)', glyph_data())
    return page


def render_video(page, audio):
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(FPS), '-c:v', 'png', '-i', '-',
           '-i', audio, '-map', '0:v', '-map', '1:a', '-c:a', 'copy',
           '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', MP4]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for frame in range(FRAMES):
        page.evaluate('t => render(t)', frame / FPS)
        enc.stdin.write(page.screenshot(type='png'))
        if frame % 60 == 0:
            print(f'frame {frame}/{FRAMES}', flush=True)
    enc.stdin.close()
    if enc.wait():
        raise SystemExit('ffmpeg failed')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stills', help='comma-separated times in seconds; writes PNGs and skips the video')
    ap.add_argument('--out', default='.', help='folder for --stills')
    ap.add_argument('--audio', help='soundtrack for the video, 22 seconds; copied into the MP4 as is')
    args = ap.parse_args()
    if not args.stills and not args.audio:
        ap.error('--audio is required to render the video')
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = open_page(browser)
        if args.stills:
            for t in args.stills.split(','):
                page.evaluate('t => render(t)', float(t))
                page.screenshot(path=os.path.join(args.out, f't{t}.png'))
        else:
            render_video(page, args.audio)
        browser.close()
    if not args.stills:
        print(MP4, f'{os.path.getsize(MP4) / 1e6:.1f} MB')


if __name__ == '__main__':
    main()
