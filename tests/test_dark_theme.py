import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DARK = '@media (prefers-color-scheme:dark)'
COLOR = re.compile(r'#[0-9a-fA-F]{3,8}\b|\bwhite\b|rgba?\(')
# Badge previews deliberately show each badge on the background it was drawn for.
KEPT = {'.badge-preview', '.badge-preview-dark'}


def rules(css):
    """(media, selector, declarations) for every style rule, with one level of @media nesting."""
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    found, stack = [], []
    for match in re.finditer(r'([^{}]+)\{|\}', css):
        if match.group(0) == '}':
            if stack:
                stack.pop()
            continue
        head = match.group(1).strip()
        if head.startswith('@'):
            stack.append(head)
            continue
        body = css[match.end():css.index('}', match.end())]
        media = next((s for s in reversed(stack) if s), '')
        found.append((media, head, dict(d.split(':', 1) for d in body.split(';') if ':' in d)))
        stack.append(None)
    return found


def luminance(color):
    value = color.lstrip('#')
    channels = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a, b):
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


class DarkThemeTests(unittest.TestCase):
    def setUp(self):
        self.sheets = {name: rules((ROOT / 'web' / name).read_text(encoding='utf-8')) for name in ('styles.css', 'pages.css')}

    def test_tokens_switch_with_the_system_color_scheme(self):
        tokens = next(d for media, selector, d in self.sheets['styles.css'] if media == DARK and selector == ':root')
        self.assertEqual(tokens['color-scheme'], 'dark')
        for name in ('--ink', '--muted', '--faint', '--blue', '--line', '--paper', '--bg'):
            self.assertIn(name, tokens)
        for text in ('--ink', '--muted', '--faint', '--blue', '--green'):
            for surface in ('--bg', '--paper', '--soft-blue'):
                self.assertGreaterEqual(contrast(tokens[text], tokens[surface]), 4.5, f'{text} on {surface}')
        for surface in ('--bg', '--paper', '--soft-blue'):
            self.assertGreaterEqual(contrast(tokens['--blue-line'], tokens[surface]), 3, f'--blue-line on {surface}')

    def test_every_light_color_token_has_a_dark_value(self):
        css = (ROOT / 'web' / 'styles.css').read_text(encoding='utf-8')
        tokens = next(d for media, selector, d in self.sheets['styles.css'] if media == DARK and selector == ':root')
        for light in re.findall(r'(?m)^:root\{([^}]*)\}', css):
            for name in re.findall(r'(--[\w-]+):#', light):
                self.assertIn(name, tokens, f'{name} has no dark value')

    def test_every_hard_coded_light_color_has_a_dark_override(self):
        for name, found in self.sheets.items():
            dark = {}
            for media, selector, d in found:
                if media.startswith(DARK):
                    for part in selector.split(','):
                        dark.setdefault((media.replace(DARK + ' and ', '@media').replace(DARK, ''), part.strip()), set()).update(p.strip() for p in d)
            for media, selector, declarations in found:
                if media.startswith(DARK) or selector in KEPT or selector.startswith(':root'):
                    continue
                colored = {p.strip() for p, v in declarations.items() if COLOR.search(v) and p.strip() not in ('white-space', 'mask-image', '-webkit-mask-image')}
                for part in selector.split(',') if colored else ():
                    override = dark.get((media, part.strip()))
                    self.assertIsNotNone(override, f'{name}: {media} {part} has no dark override')
                    self.assertLessEqual(colored, override, f'{name}: {part}')

    def test_white_labels_on_accent_fills_keep_their_contrast(self):
        for name, found in self.sheets.items():
            for media, selector, d in found:
                if media.startswith(DARK) and d.get('color') == '#fff' and 'background' in d:
                    self.assertGreaterEqual(contrast('#ffffff', d['background'][:7]), 4.5, selector)

    def test_dark_text_colors_read_on_dark_surfaces(self):
        for name, found in self.sheets.items():
            for media, selector, d in found:
                if media.startswith(DARK) and re.fullmatch(r'#[0-9a-f]{6}', d.get('color', '')) and d['color'] != '#fff':
                    self.assertGreaterEqual(contrast(d['color'], '#141821'), 4.5, f'{name}: {selector}')


if __name__ == '__main__':
    unittest.main()
