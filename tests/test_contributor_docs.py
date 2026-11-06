import os
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
FENCE = re.compile(r"^```bash\n(.*?)^```", re.S | re.M)


def fence_after(text, heading):
    return FENCE.search(text, text.index(heading)).group(1).splitlines()


class ContributorDocsTests(unittest.TestCase):
    def test_readme_verification_block_runs_every_ci_command_in_order(self):
        ci = [re.sub(r"^python ", ".venv/bin/python ", c) for c in re.findall(r"(?m)^ +(?:- )?run: (python .*|node .*)$", (ROOT / ".github/workflows/catalog.yml").read_text())]
        self.assertGreaterEqual(len(ci), 7)
        block = fence_after((ROOT / "README.md").read_text(), "## Maintain and verify")
        self.assertEqual([line for line in block if line in ci], ci)

    def test_node_requirement_matches_package_engines(self):
        node = json.loads((ROOT / "package.json").read_text())["engines"]["node"].removeprefix(">=")
        for name in ("README.md", "README.zh-CN.md"):
            self.assertIn(f"Node.js {node}+", (ROOT / name).read_text(), name)
        maintenance = next(block for block in FENCE.findall((ROOT / "docs/maintenance.md").read_text()) if "catalog.py validate" in block).splitlines()
        self.assertIn("node --test tests/web.test.mjs", maintenance)
        self.assertIn(".venv/bin/python scripts/build_site.py", maintenance)

    def test_contributing_links_verification_file_roles_and_conflict_steps(self):
        text = (ROOT / "CONTRIBUTING.md").read_text()
        self.assertIn("(README.md#maintain-and-verify)", text)
        self.assertIn("(docs/data-dictionary.md#authored-and-generated-files)", text)
        self.assertIn("## Resolving conflicts with the scheduled scan", text)
        self.assertIn("build --check", text.split("## Resolving conflicts", 1)[1])

    def test_every_tracked_data_file_is_classified(self):
        # Tracked files only: a new scan output is classified after its first commit, without blocking that scan.
        # A missing row is a documentation fix for a pull request to make, so it never stops an hourly scan either.
        if os.environ.get("CATALOG_SCAN_QUALITY") == "1":
            self.skipTest("the scan's data check")
        try:
            tracked = subprocess.run(["git", "ls-files", "data"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("not a git checkout")
        table = (ROOT / "docs/data-dictionary.md").read_text().split("## Authored and generated files", 1)[1]
        rows = {cell for line in table.splitlines() if line.startswith("| `") for cell in re.findall(r"`([^`]+)`", line.split(" | ")[0])}
        self.assertGreater(len(tracked), 20)
        self.assertEqual(sorted(Path(p).name for p in tracked if Path(p).name not in rows), [])
        for path in rows:
            if path.startswith("docs/") and "*" not in path:
                self.assertTrue((ROOT / path).exists(), path)


if __name__ == "__main__":
    unittest.main()
