from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from agent_pages import CLONE_COMMAND
from search_pages import SITE
from site_config import FORMER_SITES


class CitationFileTests(unittest.TestCase):
    def setUp(self):
        # Top-level scalars only; CI has no YAML parser, and nested values are checked by GitHub's CFF validator.
        self.cff = {k: v.strip('"') for k, v in re.findall(r"^([a-z-]+): *(.*)$", (ROOT / "CITATION.cff").read_text(), re.M)}

    def test_declares_required_cff_keys(self):
        for key in ("cff-version", "message", "title", "authors", "type", "license", "repository-code", "url"):
            self.assertIn(key, self.cff)
        self.assertEqual(self.cff["cff-version"], "1.2.0")
        self.assertEqual(self.cff["type"], "dataset")
        self.assertRegex((ROOT / "CITATION.cff").read_text(), r"authors:\n  - given-names: \S+\n    family-names: \S+")

    def test_matches_license_repository_and_website(self):
        self.assertEqual(self.cff["license"], "MIT")
        self.assertTrue((ROOT / "LICENSE").read_text().startswith("MIT License"))
        self.assertEqual(self.cff["repository-code"], CLONE_COMMAND.split()[-1].removesuffix(".git"))
        # The citation URL moves to SITE with the survey rebuild; until then it may name a former origin, which redirects there.
        self.assertIn(self.cff["url"], [origin + "/" for origin in (SITE, *FORMER_SITES)])

    def test_both_readmes_explain_citing_and_pinning(self):
        for name in ("README.md", "README.zh-CN.md"):
            text = (ROOT / name).read_text()
            self.assertIn("[CITATION.cff](CITATION.cff)", text)
            self.assertIn("git rev-parse HEAD", text)


if __name__ == "__main__":
    unittest.main()
