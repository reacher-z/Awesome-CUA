"""Deterministic, dependency-free SVG stacked charts for the README and coverage ledger; one file per color theme."""
from __future__ import annotations
import html
import math

# Validated light/dark steps: categorical slots 1-4 for nominal groups, and a two-step blue ordinal ramp for review depth.
THEMES = {
    "light": {"surface": "#fcfcfb", "border": "rgba(11,11,11,0.10)", "primary": "#0b0b0b", "secondary": "#52514e", "grid": "#e1e0d9", "axis": "#c3c2b7",
        "categorical": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"], "ordinal": ["#86b6ef", "#256abf"]},
    "dark": {"surface": "#1a1a19", "border": "rgba(255,255,255,0.10)", "primary": "#f0efec", "secondary": "#c3c2b7", "grid": "#2c2c2a", "axis": "#383835",
        "categorical": ["#3987e5", "#d95926", "#199e70", "#c98500"], "ordinal": ["#184f95", "#5598e7"]},
}
WIDTH, PAD, GAP, RADIUS, THICKNESS = 720, 24, 2, 4, 24
FONT = "system-ui,-apple-system,'Segoe UI',sans-serif"


def esc(text):
    return html.escape(str(text), quote=True)


def num(value):
    text = f"{value:.1f}"
    return text[:-2] if text.endswith(".0") else text


def text_width(text, size):
    # Upper-bound estimate without font metrics; labels that might not fit are dropped, never clipped.
    return size * sum(1.0 if ord(c) > 0x2e7f else 0.64 if c.isupper() or c.isdigit() else 0.32 if c in " .,·:" else 0.56 for c in text)


def luminance(color):
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ink(fill):
    """Black or white for text set inside a fill, whichever contrasts more. Pure black, not the primary ink, keeps 11px values at 4.5:1 on
    mid-luminance fills such as the light blue slot, where neither the primary ink nor white reaches it."""
    level = luminance(fill)
    return "#000000" if (level + 0.05) / 0.05 >= 1.05 / (level + 0.05) else "#ffffff"


def gap(extent, cumulative):
    """The surface gap before a stacked segment; it never takes more than half of the segment, so a small nonzero count stays drawn."""
    return min(GAP, extent / 2) if cumulative else 0


def rounded(x, y, w, h, end):
    """A mark with a 4px rounded data end ('top' or 'right') and square corners at the baseline."""
    r = min(RADIUS, w / 2, h / 2)
    if end == "top":
        return f'M{num(x)} {num(y + h)}V{num(y + r)}A{num(r)} {num(r)} 0 0 1 {num(x + r)} {num(y)}H{num(x + w - r)}A{num(r)} {num(r)} 0 0 1 {num(x + w)} {num(y + r)}V{num(y + h)}Z'
    return f'M{num(x)} {num(y)}H{num(x + w - r)}A{num(r)} {num(r)} 0 0 1 {num(x + w)} {num(y + r)}V{num(y + h - r)}A{num(r)} {num(r)} 0 0 1 {num(x + w - r)} {num(y + h)}H{num(x)}Z'


def nice_step(maximum, ticks=5):
    raw = max(maximum, 1) / ticks
    power = 10 ** math.floor(math.log10(raw))
    return next(m * power for m in (1, 2, 2.5, 5, 10) if m * power >= raw)


def frame(slug, height, theme, title, subtitle, names, colors, body):
    t = THEMES[theme]
    legend, x = [], PAD
    for name, color in zip(names, colors):
        legend.append(f'<rect x="{num(x)}" y="74" width="10" height="10" rx="2" fill="{color}"/><text x="{num(x + 16)}" y="83.5">{esc(name)}</text>')
        x += 16 + text_width(name, 12) + 20
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img" aria-labelledby="{slug}-title {slug}-desc">',
        f'<title id="{slug}-title">{esc(title)}</title>', f'<desc id="{slug}-desc">{esc(subtitle)}</desc>',
        f'<style>text{{font-family:{FONT};font-size:12px;fill:{t["secondary"]}}}.t{{font-size:16px;font-weight:600;fill:{t["primary"]}}}.n{{font-variant-numeric:tabular-nums}}.v{{font-weight:600;fill:{t["primary"]}}}</style>',
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="8" fill="{t["surface"]}" stroke="{t["border"]}"/>',
        f'<text class="t" x="{PAD}" y="36">{esc(title)}</text>', f'<text x="{PAD}" y="57">{esc(subtitle)}</text>', *legend, *body, "</svg>", ""])


def tooltip(category, names, values):
    return f"{category}: {sum(values):,} (" + ", ".join(f"{name} {value:,}" for name, value in zip(names, values)) + ")"


def stacked_columns(slug, theme, title, subtitle, categories, series, colors):
    """Vertical stacked columns over ordered categories (years); series stack from the baseline up in list order."""
    t, names = THEMES[theme], [name for name, _ in series]
    height, top, left, right = 360, 116, PAD + 44, WIDTH - PAD
    bottom = height - 44
    totals = [sum(values[i] for _, values in series) for i in range(len(categories))]
    step = nice_step(max(totals, default=0))
    ceiling = step * math.ceil(max(max(totals, default=0), 1) / step)
    y = lambda v: bottom - v / ceiling * (bottom - top)
    body = []
    for i in range(int(ceiling / step) + 1):
        tick = i * step
        body.append(f'<line x1="{left}" x2="{right}" y1="{num(y(tick))}" y2="{num(y(tick))}" stroke="{t["axis"] if i == 0 else t["grid"]}" stroke-width="1"/>'
            f'<text class="n" x="{left - 8}" y="{num(y(tick) + 4)}" text-anchor="end">{tick:,.0f}</text>')
    band = (right - left) / max(len(categories), 1)
    width = min(THICKNESS, band * 0.6)
    for i, category in enumerate(categories):
        x, cumulative, marks = left + band * i + (band - width) / 2, 0, []
        values = [values[i] for _, values in series]
        last = max((k for k, v in enumerate(values) if v), default=-1)
        for k, value in enumerate(values):
            if not value:
                continue
            upper, lower = y(cumulative + value), y(cumulative) - gap(y(cumulative) - y(cumulative + value), cumulative)
            cumulative += value
            if lower - upper > 0:
                marks.append(f'<path d="{rounded(x, upper, width, lower - upper, "top")}" fill="{colors[k]}"/>' if k == last else
                    f'<rect x="{num(x)}" y="{num(upper)}" width="{num(width)}" height="{num(lower - upper)}" fill="{colors[k]}"/>')
        if totals[i]:
            marks.append(f'<text class="n v" x="{num(x + width / 2)}" y="{num(y(totals[i]) - 6)}" text-anchor="middle">{totals[i]:,}</text>')
        body.append(f'<g><title>{esc(tooltip(category, names, values))}</title>{"".join(marks)}'
            f'<text x="{num(x + width / 2)}" y="{bottom + 20}" text-anchor="middle">{esc(category)}</text></g>')
    return frame(slug, height, theme, title, subtitle, names, colors, body)


def stacked_bars(slug, theme, title, subtitle, categories, series, colors):
    """Horizontal stacked bars, one row per category; segment values are printed only where they fit inside the segment."""
    t, names = THEMES[theme], [name for name, _ in series]
    top, pitch, thickness, left, right = 104, 32, 20, PAD + 104, WIDTH - PAD - 48
    height = top + pitch * len(categories) + 12
    totals = [sum(values[i] for _, values in series) for i in range(len(categories))]
    scale = (right - left) / max(max(totals, default=0), 1)
    body = [f'<line x1="{left}" x2="{left}" y1="{top}" y2="{top + pitch * len(categories) - (pitch - thickness)}" stroke="{t["axis"]}" stroke-width="1"/>'] if categories else []
    for i, category in enumerate(categories):
        y, cumulative, marks = top + pitch * i, 0, []
        values = [values[i] for _, values in series]
        last = max((k for k, v in enumerate(values) if v), default=-1)
        for k, value in enumerate(values):
            if not value:
                continue
            start, end = left + cumulative * scale + gap(value * scale, cumulative), left + (cumulative + value) * scale
            cumulative += value
            if end - start <= 0:
                continue
            marks.append(f'<path d="{rounded(start, y, end - start, thickness, "right")}" fill="{colors[k]}"/>' if k == last else
                f'<rect x="{num(start)}" y="{y}" width="{num(end - start)}" height="{thickness}" fill="{colors[k]}"/>')
            if text_width(f"{value:,}", 11) + 8 <= end - start:
                marks.append(f'<text class="n" x="{num((start + end) / 2)}" y="{y + 14}" text-anchor="middle" style="font-size:11px;fill:{ink(colors[k])}">{value:,}</text>')
        if totals[i]:
            marks.append(f'<text class="n v" x="{num(left + totals[i] * scale + 6)}" y="{y + 14.5}">{totals[i]:,}</text>')
        body.append(f'<g><title>{esc(tooltip(category, names, values))}</title><text x="{PAD}" y="{y + 14.5}">{esc(category)}</text>{"".join(marks)}</g>')
    return frame(slug, height, theme, title, subtitle, names, colors, body)
