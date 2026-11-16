"""Keyboard focus on a catalog card or list row outlines the whole card or row, not only its title text."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "web/styles.css").read_text(encoding="utf-8")


def block(source, start):
    """The body of the brace block that opens at the first occurrence of start."""
    i = source.index(start) + len(start)
    depth, j = 1, i
    while depth:
        depth += {"{": 1, "}": -1}.get(source[j], 0)
        j += 1
    return source[i:j - 1]


class CardFocusTests(unittest.TestCase):
    def test_cards_and_rows_outline_when_their_title_link_has_keyboard_focus(self):
        rules = block(CSS, "@supports selector(:has(*)){")
        self.assertRegex(rules, r"\.resource-card:has\(\.card-title a:focus-visible\)\{outline:2px solid var\(--blue\);outline-offset:3px\}")
        self.assertRegex(rules, r"\.resource-row:has\(\.row-main h3 a:focus-visible\)\{outline:2px solid var\(--blue\);outline-offset:-2px")

    def test_title_outline_is_removed_only_where_the_card_outline_is_supported(self):
        rules = block(CSS, "@supports selector(:has(*)){")
        for selector in (".resource-card .card-title a:focus-visible", ".resource-row .row-main h3 a:focus-visible"):
            self.assertIn(selector + "{outline:none}", rules)
            outside = CSS.replace("@supports selector(:has(*)){" + rules + "}", "")
            self.assertNotIn(selector + "{outline:none}", outside)
        # Browsers without :has keep the global link focus ring.
        self.assertIn("a:focus-visible", re.search(r"button:focus-visible,a:focus-visible[^{]*\{outline:2px solid var\(--blue\)\}", CSS).group(0))


if __name__ == "__main__":
    unittest.main()
