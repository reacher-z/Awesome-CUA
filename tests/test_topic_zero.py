"""The topic directory shows a known zero as 0 with readable contrast; the site reserves — for facts that are not recorded."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from topic_pages import topic_index_body

MANIFEST = {"resources_with_topics": 3, "topics": [{"id": "grounding", "name": {"en": "GUI grounding", "zh": "GUI 定位"},
            "counts": {"total": 3, "papers": 2, "benchmarks": 0, "datasets": 1, "models": 0, "systems": 0}}]}


def luminance(hex_color):
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    channels = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


class TopicZeroTests(unittest.TestCase):
    def test_zero_counts_render_as_zero_not_as_an_unknown_dash(self):
        for language, note in (("en", "0 means no reviewed entry carries that tag yet."), ("zh", "0 表示该标签下尚无已审阅条目。")):
            body = topic_index_body(MANIFEST, language=language)[0]
            rows = body.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
            self.assertEqual(rows.count('<span class="topic-zero">0</span>'), 3)
            self.assertNotIn("—", rows)
            self.assertIn(note, body)
            self.assertNotIn("Blank cells", body)
            # A generic span cannot carry an accessible name; the digit itself is read out.
            self.assertNotRegex(rows, r'<span class="topic-zero"[^>]*aria-label')

    def test_zero_text_meets_aa_contrast(self):
        pages = (ROOT / "web/pages.css").read_text(encoding="utf-8")
        self.assertIn(".topic-zero{color:var(--faint);", pages)
        faint = re.search(r"--faint:(#[0-9a-fA-F]{6})", (ROOT / "web/styles.css").read_text(encoding="utf-8")).group(1)
        self.assertGreaterEqual(1.05 / (luminance(faint) + 0.05), 4.5)


if __name__ == "__main__":
    unittest.main()
