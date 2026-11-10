"""Open Graph cards (1200×630 PNG) for the home page, collection pages and each resource kind, drawn at build time.

Palette "Indigo on Grid Paper" and the site's own fonts: EB Garamond titles, Inter text, JetBrains Mono labels.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / 'web/assets/fonts'
WIDTH, HEIGHT = 1200, 630
PAPER, GRID, INDIGO, INK, BODY, META = '#FFFFFF', '#E3EAFF', '#4B59F2', '#212632', '#303542', '#5E6472'
CORAL, CORAL_LINE, CURSOR_EDGE, PERIWINKLE = '#FFA69E', '#E8695C', '#9D4E49', '#BFD7FF'
DIRECTORY = 'og'


def font(name, size, weight=None):
    face = ImageFont.truetype(str(FONTS / name), size)
    if weight:face.set_variation_by_axes([weight])
    return face


def wrap(draw, text, face, width, lines):
    """Greedy word wrap into at most `lines` lines; an overflowing last line ends with an ellipsis."""
    words, out = text.split(), []
    while words and len(out) < lines:
        line = words.pop(0)
        while words and draw.textlength(line + ' ' + words[0], font=face) <= width:
            line += ' ' + words.pop(0)
        out.append(line)
    if words:
        last = out[-1]
        while last and draw.textlength(last + '…', font=face) > width:
            last = last.rsplit(' ', 1)[0] if ' ' in last else last[:-1]
        out[-1] = re.sub(r'[\s,;:.]+$', '', last) + '…'
    return out


def dashed_rectangle(draw, box, color, width=3, dash=12, gap=9):
    left, top, right, bottom = box
    for start, end, fixed, horizontal in ((left, right, top, True), (left, right, bottom, True), (top, bottom, left, False), (top, bottom, right, False)):
        position = start
        while position < end:
            stop = min(position + dash, end)
            draw.line([(position, fixed), (stop, fixed)] if horizontal else [(fixed, position), (fixed, stop)], fill=color, width=width)
            position = stop + gap


def cursor(draw, x, y, scale=1.0):
    # The site's coral pointer, from the logo mark.
    points = [(0, 0), (40, 17), (23, 21.5), (18, 39)]
    draw.polygon([(x + px * scale, y + py * scale) for px, py in points], fill=CORAL, outline=CURSOR_EDGE, width=3)


def card(address, eyebrow, title, subtitle, step='click'):
    """One card: a browser window on grid paper, the page title framed by the agent's dashed target box."""
    image = Image.new('RGB', (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    for x in range(0, WIDTH, 30):draw.line([(x, 0), (x, HEIGHT)], fill=GRID, width=1)
    for y in range(0, HEIGHT, 30):draw.line([(0, y), (WIDTH, y)], fill=GRID, width=1)
    left, top, right, bottom = 60, 54, 1140, 576
    draw.rounded_rectangle([left, top, right, bottom], radius=14, fill=PAPER, outline=INDIGO, width=3)
    draw.rounded_rectangle([left, top, right, top + 58], radius=14, fill=INDIGO, corners=(True, True, False, False))
    for index in range(3):draw.ellipse([left + 26 + index * 24, top + 23, left + 38 + index * 24, top + 35], fill=PAPER)
    mono = font('jetbrains-mono.woff2', 22, 500)
    draw.text((left + 112, top + 29), address, font=mono, fill=PAPER, anchor='lm')
    inner = left + 64
    label = font('jetbrains-mono.woff2', 21, 500)
    draw.text((inner, top + 104), eyebrow.upper(), font=label, fill=META, anchor='ls')
    heading = font('eb-garamond.woff2', 84, 500)
    lines = wrap(draw, title, heading, right - inner - 120, 2)
    if len(lines) == 2 or draw.textlength(lines[0], font=heading) > 820:
        heading = font('eb-garamond.woff2', 68, 500)
        lines = wrap(draw, title, heading, right - inner - 120, 2)
    line_height = int(heading.size * 1.08)
    baseline = top + 162 + heading.size
    widest = max(draw.textlength(line, font=heading) for line in lines)
    for number, line in enumerate(lines):
        draw.text((inner, baseline + number * line_height), line, font=heading, fill=INK, anchor='ls')
    box = (inner - 18, baseline - heading.size - 4, inner + widest + 18, baseline + (len(lines) - 1) * line_height + 22)
    dashed_rectangle(draw, box, CORAL_LINE)
    tag_face = font('jetbrains-mono.woff2', 18, 500)
    tag = f'1 · {step}'
    tag_width = draw.textlength(tag, font=tag_face) + 20
    draw.rectangle([box[0], box[1] - 30, box[0] + tag_width, box[1]], fill=CORAL)
    draw.text((box[0] + 10, box[1] - 15), tag, font=tag_face, fill=INK, anchor='lm')
    cursor(draw, box[2] - 26, box[3] - 18, 1.25)
    text = font('inter.woff2', 29, 400)
    for number, line in enumerate(wrap(draw, subtitle, text, right - inner - 70, 2)):
        draw.text((inner, box[3] + 58 + number * 40), line, font=text, fill=BODY, anchor='ls')
    brand = font('inter.woff2', 26, 600)
    draw.rounded_rectangle([inner, bottom - 66, inner + 34, bottom - 40], radius=6, outline=INK, width=3)
    draw.line([(inner, bottom - 58), (inner + 34, bottom - 58)], fill=INK, width=3)
    cursor(draw, inner + 18, bottom - 54, 0.55)
    draw.text((inner + 50, bottom - 52), 'Awesome', font=brand, fill=INK, anchor='lm')
    draw.text((inner + 50 + draw.textlength('Awesome ', font=brand), bottom - 52), 'CUA', font=brand, fill=INDIGO, anchor='lm')
    site = font('jetbrains-mono.woff2', 20, 400)
    draw.text((right - 40, bottom - 52), 'awesomecua.com', font=site, fill=META, anchor='rm')
    draw.rectangle([right - 40 - draw.textlength('awesomecua.com', font=site), bottom - 38, right - 40, bottom - 35], fill=PERIWINKLE)
    out = BytesIO()
    image.save(out, 'PNG', optimize=True)
    return out.getvalue()


def write_cards(destination, cards):
    """Write {slug: (address, eyebrow, title, subtitle, step)} to /og/<slug>.png and return {slug: site path}."""
    folder = Path(destination) / DIRECTORY
    folder.mkdir(parents=True, exist_ok=True)
    paths = {}
    for slug, spec in cards.items():
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug):raise ValueError('Unsafe OG card name: ' + slug)
        (folder / f'{slug}.png').write_bytes(card(*spec))
        paths[slug] = f'/{DIRECTORY}/{slug}.png'
    for stale in folder.glob('*.png'):
        if stale.stem not in cards:stale.unlink()
    return paths
