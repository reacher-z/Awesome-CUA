from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
BIBTEX = re.compile(r"^```bibtex\n(@misc\{awesomecua,\n.*?\n\})\n```$", re.S | re.M)
READMES = {"README.md": "Cite", "README.zh-CN.md": "引用"}


def github_anchor(heading):
    # GitHub lowercases a heading, drops punctuation except '-' and '_', and turns spaces into '-'.
    return "#" + re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def bibtex_fields(entry):
    return dict(re.findall(r"^  (\w+)\s*= \{(.*)\},?$", entry, re.M))


class ReadmeCiteTests(unittest.TestCase):
    def setUp(self):
        text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        # Top-level scalars only, as in test_citation_file: CI has no YAML parser.
        self.cff = {k: v.strip('"') for k, v in re.findall(r"^([a-z-]+): *(.*)$", text, re.M)}
        self.given = re.search(r"given-names: (.+)", text)[1].strip()
        self.family = re.search(r"family-names: (.+)", text)[1].strip()

    def test_hero_links_to_a_cite_section(self):
        for name, heading in READMES.items():
            text = (ROOT / name).read_text(encoding="utf-8")
            hero = text[:text.index("```sh")]
            self.assertIn(f"]({github_anchor(heading)})", hero, name)
            self.assertIn(f"\n## {heading}\n", text, name)

    def test_both_readmes_carry_the_same_bibtex(self):
        entries = [BIBTEX.findall((ROOT / name).read_text(encoding="utf-8")) for name in READMES]
        for found in entries:
            self.assertEqual(len(found), 1)
        self.assertEqual(entries[0], entries[1])

    def test_bibtex_matches_citation_cff(self):
        fields = bibtex_fields(BIBTEX.search((ROOT / "README.md").read_text(encoding="utf-8"))[1])
        self.assertEqual(fields["title"], self.cff["title"])
        self.assertEqual(fields["author"], f"{self.family}, {self.given}")
        self.assertEqual(fields["url"], self.cff["url"])
        self.assertEqual(fields["howpublished"], "\\url{%s}" % self.cff["repository-code"])
        self.assertRegex(fields["year"], r"^20\d\d$")

    def test_cite_section_keeps_pinning_guidance(self):
        for name, heading in READMES.items():
            text = (ROOT / name).read_text(encoding="utf-8")
            section = text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]
            self.assertIn("[CITATION.cff](CITATION.cff)", section)
            self.assertIn("git rev-parse HEAD", section)
            self.assertIn("https://github.com/reacher-z/Awesome-CUA/releases", section)


if __name__ == "__main__":
    unittest.main()
