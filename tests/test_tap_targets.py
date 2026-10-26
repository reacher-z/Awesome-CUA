import re
import unittest
from pathlib import Path

STYLES = (Path(__file__).resolve().parents[1] / 'web' / 'styles.css').read_text(encoding='utf-8')


def declarations(selector):
    """Merged declarations of every top-level-or-nested rule whose selector is exactly `selector`."""
    merged = {}
    for match in re.finditer(r'(?:(?<=[{}])|^)\s*([^{}@]+?)\s*\{([^{}]*)\}', STYLES, re.M):
        if match.group(1).strip() == selector:
            merged.update(d.split(':', 1) for d in match.group(2).split(';') if ':' in d)
    return merged


class TapTargetTests(unittest.TestCase):
    # WCAG 2.2 SC 2.5.8: catalog links that sit on top of the card's own link need a 24×24 CSS px hit area.
    def test_card_source_arrow_has_a_24px_hit_area(self):
        rule = declarations('.card-external')
        self.assertGreaterEqual(int(rule['min-width'].rstrip('px')), 24)
        self.assertGreaterEqual(int(rule['min-height'].rstrip('px')), 24)
        # Negative margins keep the larger hit area from moving the glyph or growing the card footer.
        self.assertTrue(rule['margin-block'].startswith('-'))

    def test_list_row_actions_have_a_24px_hit_height(self):
        rule = declarations('.row-actions a')
        self.assertGreaterEqual(int(rule['min-height'].rstrip('px')), 24)
        self.assertEqual(rule['display'], 'inline-flex')


if __name__ == '__main__':
    unittest.main()
