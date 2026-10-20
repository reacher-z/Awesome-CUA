from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\]\(([^)\s]+)\)")
GENERATED = re.compile(r"<!-- (\w+):START -->.*?<!-- \1:END -->", re.S)
FENCE = re.compile(r"^```(?:bash|sh)\n(.*?)^```", re.S | re.M)


def targets(text):
    return {t for t in LINK.findall(text) if not t.startswith("#")} - {"README.md", "README.zh-CN.md"}


def commands(text):
    return {line for block in FENCE.findall(text) for line in block.splitlines() if line.strip() and not line.startswith("#")}


class ReadmeParityTests(unittest.TestCase):
    def setUp(self):
        self.en = (ROOT / "README.md").read_text()
        self.zh = (ROOT / "README.zh-CN.md").read_text()

    def test_chinese_readme_links_every_english_target(self):
        # Generated blocks link many upstream projects; their relative category links still count.
        expected = {t for t in targets(self.en) if "://" not in t} | targets(GENERATED.sub("", self.en))
        self.assertEqual(sorted(expected - targets(self.zh)), [])

    def test_chinese_readme_runs_the_same_commands(self):
        self.assertEqual(sorted(commands(self.en) - commands(self.zh)), [])
        maintain = FENCE.search(self.en, self.en.index("## Maintain and verify")).group(0)
        self.assertIn(maintain, self.zh)

    def test_language_toggles_and_generated_status_are_shared(self):
        self.assertIn("[简体中文](README.zh-CN.md)", self.en)
        self.assertIn("[English](README.md)", self.zh)
        block = re.compile(r"<!-- BADGES:START -->.*?<!-- BADGES:END -->", re.S)
        self.assertEqual(block.search(self.zh).group(0), block.search(self.en).group(0))
        # The other generated blocks are localized, but both pages carry every one of them.
        for name in ["STATS", "EXPLORE", "CHARTS", "HIGHLIGHTS", "RECENT"]:
            for text in (self.en, self.zh):
                self.assertIn(f"<!-- {name}:START -->", text)


if __name__ == "__main__":
    unittest.main()
