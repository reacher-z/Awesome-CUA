import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANNERS = {'README.md': ('assets/readme-banner.svg', 'assets/readme-banner-dark.svg'),
           'README.zh-CN.md': ('assets/readme-banner.zh-CN.svg', 'assets/readme-banner-dark.zh-CN.svg')}


def luminance(color):
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a, b):
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


class ReadmeBannerTests(unittest.TestCase):
    def test_readmes_offer_the_dark_banner_to_dark_mode_readers(self):
        for readme, (light, dark) in BANNERS.items():
            text = (ROOT / readme).read_text(encoding='utf-8')
            self.assertIn(f'<picture><source media="(prefers-color-scheme: dark)" srcset="{dark}"><img src="{light}"', text, readme)

    def test_dark_banner_keeps_the_light_banner_text_and_reads_on_its_card(self):
        for light, dark in BANNERS.values():
            light_svg, dark_svg = ((ROOT / path).read_text(encoding='utf-8') for path in (light, dark))
            # Same layout, title, description and words; only colors differ.
            self.assertEqual(re.sub(r'#[0-9A-F]{6}', '#', light_svg), re.sub(r'#[0-9A-F]{6}', '#', dark_svg))
            card = re.search(r'<rect x="\.5" y="\.5"[^>]*fill="(#[0-9A-F]{6})"', dark_svg).group(1)
            self.assertLess(luminance(card), 0.05)
            for color in set(re.findall(r'<text[^>]*fill="(#[0-9A-F]{6})"', dark_svg)):
                self.assertGreaterEqual(contrast(color, card), 4.5, color)


if __name__ == '__main__':
    unittest.main()
