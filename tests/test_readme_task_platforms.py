"""README "Find by task" links benchmark, dataset and model rows straight to each main platform hub section."""
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build

ROWS = [json.loads(line) for line in (ROOT / "data/catalog.jsonl").read_text(encoding="utf-8").splitlines()]
SECTIONS = {"Choose a benchmark": ("benchmark", "benchmarks"), "Find training data": ("dataset", "datasets"), "Pick a model": ("model", "models")}
ZH_SECTIONS = {"选择评测基准": "benchmarks", "寻找训练数据": "datasets", "挑选模型": "models"}


def task_rows(readme):
    block = readme.split("<!-- TASKS:START -->", 1)[1].split("<!-- TASKS:END -->", 1)[0]
    return {line.split(" | ")[0].lstrip("| "): line for line in block.splitlines() if line.startswith("| ") and not line.startswith("| ---")}


class ReadmeTaskPlatformTests(unittest.TestCase):
    def test_each_row_links_every_main_platform_section_with_its_count(self):
        rows = task_rows((ROOT / "README.md").read_text(encoding="utf-8"))
        for task, (kind, section) in SECTIONS.items():
            links = re.findall(r"\[(Web|Desktop|Android|iOS) ([\d,]+)\]\(docs/environments/([a-z]+)\.md#(\w+)\)", rows[task])
            self.assertEqual([label for label, *_ in links], ["Web", "Desktop", "Android", "iOS"], task)
            for label, count, env, anchor in links:
                self.assertEqual(anchor, section)
                expected = sum(r["kind"] == kind and r["review_status"] == "curated" and env in r["environments"] for r in ROWS)
                self.assertEqual(int(count.replace(",", "")), expected, (task, env))
                hub = (ROOT / f"docs/environments/{env}.md").read_text(encoding="utf-8")
                self.assertIn(f"## {section.title()}\n", hub, (task, env))

    def test_android_benchmarks_are_one_click_from_the_readme(self):
        row = task_rows((ROOT / "README.md").read_text(encoding="utf-8"))["Choose a benchmark"]
        self.assertRegex(row, r"\[Android \d+\]\(docs/environments/android\.md#benchmarks\)")

    def test_chinese_readme_has_the_same_links_with_localized_labels(self):
        rows = task_rows((ROOT / "README.zh-CN.md").read_text(encoding="utf-8"))
        for task, section in ZH_SECTIONS.items():
            self.assertIn("按平台：[网页 ", rows[task])
            self.assertEqual(re.findall(r"\]\(docs/environments/(\w+)\.md#(\w+)\)", rows[task]), [(env, section) for env in build.TASK_PLATFORMS])

    def test_publication_readme_keeps_absolute_repository_links(self):
        text = build.task_navigator(rows=ROWS)
        self.assertIn("](https://github.com/reacher-z/Awesome-CUA/blob/main/docs/environments/android.md#benchmarks)", text)
        self.assertNotIn("](docs/", text)
        self.assertIn("task_navigator(rows=rows)", (ROOT / "scripts/prepare_publication.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
