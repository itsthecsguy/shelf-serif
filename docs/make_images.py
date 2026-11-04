"""Render the README's reference images in Chromium through Playwright, from
the fonts and CSS in this repository, so the images show what a browser draws.

    pip install playwright fonttools && playwright install chromium
    python docs/make_images.py
"""
from __future__ import annotations

import html
import os

from fontTools.ttLib import TTFont
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'docs')
OUT = os.path.join(DOCS, 'images')
FACES = (('Light', 300), ('Regular', 400), ('Medium', 500), ('SemiBold', 600), ('Bold', 700))

CSS = '''
* { box-sizing: border-box; margin: 0; }
html { background: #000; }
body { width: 1600px; padding: 64px 72px; background: #000; color: #fff;
       font-family: var(--font-shelf-serif); font-kerning: normal; }
.tag { color: #9a9a9a; font-size: 20px; font-weight: 500; letter-spacing: .08em; }
.bar { display: flex; justify-content: space-between; align-items: baseline; }
hr { border: 0; border-top: 1px solid #3a3a3a; margin: 26px 0; }
.name { font-size: 150px; line-height: 1.05; text-transform: uppercase; }
.row { display: grid; grid-template-columns: 300px 1fr; gap: 24px; align-items: baseline; padding: 20px 0;
       border-top: 1px solid #3a3a3a; }
.row:first-of-type { border-top: 0; }
.row .tag { font-size: 18px; letter-spacing: .04em; line-height: 1.35; }
.cells { display: grid; grid-template-columns: repeat(18, 1fr); }
.cells span { font-size: 54px; line-height: 1; text-align: center; padding: 14px 0; border: 1px solid #262626;
              margin: -1px 0 0 -1px; }
'''


def page(body):
    return ('<!doctype html><html><head><meta charset="utf-8">'
            '<link rel="stylesheet" href="../css/shelf-serif.css">'
            f'<style>{CSS}</style></head><body>{body}</body></html>')


def bar(left, right):
    return f'<div class="bar tag"><span>{left}</span><span>{right}</span></div>'


def hero():
    return (bar('AN ORIGINAL TYPEFACE FOR GROK BOT SHELF', 'SIL OPEN FONT LICENSE') +
            '<div style="font-size:236px;line-height:1.1;margin-top:48px;font-weight:300;white-space:nowrap">'
            'Shelf Serif</div><hr>'
            '<div style="font-size:64px;line-height:1.25;font-weight:700">Squared bowls. Hairline shelves.</div>'
            '<div style="font-size:64px;line-height:1.25;font-weight:300">Five named weights, 300 to 700.</div>')


def social():
    # GitHub's social preview is 1280 by 640. Upload it in the repository's settings.
    return ('<style>body { width: 1280px; height: 640px; padding: 56px 64px; display: flex; flex-direction: column; }'
            '</style>' + bar('AN OPEN SOURCE TYPEFACE FOR GROK BOT SHELF', 'SIL OPEN FONT LICENSE') +
            '<div style="flex:1;display:flex;flex-direction:column;justify-content:center">'
            '<div style="font-size:196px;line-height:1.05;font-weight:300;white-space:nowrap">Shelf Serif</div><hr>'
            '<div style="font-size:52px;line-height:1.25;font-weight:700">Squared bowls. Hairline shelves.</div>'
            '<div style="font-size:52px;line-height:1.25;font-weight:300">Five named weights, 300 to 700.</div></div>' +
            bar('GITHUB.COM/ITSTHECSGUY/SHELF-SERIF', 'GROKBOTSHELF.COM'))


def weights():
    rows = ''.join(
        f'<div class="bar" style="font-weight:{w};font-size:132px;line-height:1.14;">'
        f'<span>{n.upper()}</span><span>{w}</span></div><hr style="margin:6px 0">'
        for n, w in FACES)
    return rows


def face(name, w):
    t = lambda s, size, extra='': f'<div style="font-size:{size}px;line-height:1.28;{extra}">{html.escape(s)}</div>'
    return (f'<div style="font-weight:{w}">' +
            bar('SHELF SERIF', f'FONT-WEIGHT: {w}') +
            f'<div class="name" style="margin-top:30px">{name}</div><hr>' +
            t('Hamburgefonstiv & Quartz', 104) + '<hr>' +
            t('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 66) +
            t('abcdefghijklmnopqrstuvwxyz', 66) +
            t('0123456789 &?!@$%#', 66) + '<hr>' +
            t('The quick brown fox jumps over the lazy dog.', 46) +
            t('Sphinx of black quartz, judge my vow. Pack my box with five dozen liquor jugs.', 28) +
            t('At 16 px: How vexingly quick daft zebras jump. The five boxing wizards jump quickly at dawn.', 16,
              'margin-top:6px') +
            '</div>')


def codepoints():
    cmap = TTFont(os.path.join(ROOT, 'fonts', 'otf', 'ShelfSerif-Regular.otf')).getBestCmap()
    return [c for c in sorted(cmap) if c > 0x20 and c != 0xA0 and not 0x300 <= c <= 0x36F]


def charset(name, w, chars):
    cells = ''.join(f'<span>{html.escape(chr(c))}</span>' for c in chars)
    return (bar(f'SHELF SERIF {name.upper()}: CHARACTER SET', f'{len(chars)} CHARACTERS, FONT-WEIGHT: {w}') +
            f'<div class="cells" style="font-weight:{w};margin-top:30px">{cells}</div>')


def row(label, content):
    return f'<div class="row"><div class="tag">{label}</div><div>{content}</div></div>'


def features():
    num = lambda style: (f'<div style="font-variant-numeric:{style};font-size:54px;line-height:1.2;'
                         'display:inline-block;text-align:right;margin-right:90px">'
                         '1,111.11<br>9,876.54<br>2,026.17</div>')
    return (bar('SHELF SERIF', 'OPENTYPE FEATURES') + '<div style="margin-top:18px"></div>' +
            row('Tabular figures (default, tnum)', num('tabular-nums')) +
            row('Proportional figures (pnum)', num('proportional-nums')) +
            row('Kerning on (kern)', '<div style="font-size:72px">AVATAR Tower LT Yo</div>') +
            row('Kerning off', '<div style="font-size:72px;font-kerning:none">AVATAR Tower LT Yo</div>') +
            row('Accents (precomposed)', '<div style="font-size:64px">Àéîõü Çñ Øæœ ß Þð Šž</div>') +
            row('Combining marks (mark, ccmp)',
                '<div style="font-size:64px">á è ô ñ ü í ĵ</div>'))


def fpairs():
    return (bar('SHELF SERIF', 'F PAIRS: NO LIGATURE GLYPHS, THE LETTERS STAY SEPARATE') +
            ''.join(f'<div style="font-weight:{w};font-size:88px;line-height:1.3;margin-top:{m}px">'
                    'fi fl ff ffi ffl office waffle fjord</div>'
                    for w, m in ((300, 28), (400, 0), (700, 0))))


def symbols():
    groups = (('Punctuation', '‘ ’ “ ” ‚ „ ‹ › « » – — … • · † ‡ § ¶ ¡ ¿'),
              ('Currency', '$ € £ ¥ ¢ ¤'),
              ('Math', '+ − × ÷ ± = ≠ < > ¬ % ‰ ° µ'),
              ('Fractions, superiors', '¼ ½ ¾ ¹ ² ³ ª º'),
              ('Marks', '© ® ™ @ & #'))
    cmap = TTFont(os.path.join(ROOT, 'fonts', 'otf', 'ShelfSerif-Regular.otf')).getBestCmap()
    rows = ''
    for label, chars in groups:
        have = ' '.join(c for c in chars.split() if ord(c) in cmap)
        rows += row(label, f'<div style="font-size:58px;word-spacing:.12em">{html.escape(have)}</div>')
    return bar('SHELF SERIF', 'SYMBOLS AND PUNCTUATION') + '<div style="margin-top:18px"></div>' + rows


def wordmark():
    return (bar('SHELF SERIF', '.shelf-caps') +
            '<div class="shelf-caps" style="font-size:66px;margin-top:44px;white-space:nowrap">Grok Bot Shelf</div>'
            '<div class="shelf-caps regular" style="font-size:66px;margin-top:30px;white-space:nowrap">Grok Bot Shelf</div>'
            '<div class="shelf-caps bold" style="font-size:66px;margin-top:30px;white-space:nowrap">Grok Bot Shelf</div>')


def sizes():
    rows = ''.join(f'<div style="display:flex;align-items:baseline;gap:30px;margin-top:10px">'
                   f'<span class="tag" style="width:80px;font-size:16px">{s} px</span>'
                   f'<span style="font-size:{s}px;white-space:nowrap">Squared bowls and hairline shelves</span></div>'
                   for s in (12, 14, 16, 20, 24, 32, 48, 72))
    return bar('SHELF SERIF REGULAR', 'SIZES') + f'<div style="margin-top:20px">{rows}</div>'


def main():
    chars = codepoints()
    pages = {'hero': hero(), 'social-preview': social(), 'weights': weights(), 'features': features(), 'f-pairs': fpairs(),
             'symbols': symbols(), 'wordmark': wordmark(), 'sizes': sizes()}
    for name, w in FACES:
        pages[f'face-{name.lower()}'] = face(name, w)
        pages[f'charset-{name.lower()}'] = charset(name, w, chars)
    tmp = os.path.join(DOCS, '_render.html')
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 1600, 'height': 900})
        for name, body in pages.items():
            with open(tmp, 'w', encoding='utf-8') as f:
                f.write(page(body))
            pg = ctx.new_page()
            pg.goto('file://' + tmp)
            pg.evaluate('document.fonts.ready')
            loaded = pg.evaluate('''async () => {
                await Promise.all([300,400,500,600,700].map(w => document.fonts.load(w + ' 40px "Shelf Serif"')));
                await document.fonts.ready;
                return [...document.fonts].filter(f => f.family.includes('Shelf Serif') && f.status === 'loaded').length;
            }''')
            if not loaded:
                raise SystemExit(f'{name}: Shelf Serif did not load')
            pg.locator('body').screenshot(path=os.path.join(OUT, f'{name}.png'))
            pg.close()
            print('wrote', name)
        b.close()
    os.remove(tmp)


if __name__ == '__main__':
    main()
