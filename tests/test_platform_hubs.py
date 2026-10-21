from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build


def row(rid, name, kind, environments, status="curated", published_at=None):
    return {"id": rid, "name": name, "kind": kind, "review_status": status, "url": "https://example.com/" + rid, "environments": environments,
        "topics": [], "summary": name + ".", "published_at": published_at, "relations": [], "details": {},
        "licenses": {"code": None, "data": None, "weights": None, "document": None},
        "evidence": [{"method": "editorial_primary_review", "url": "https://example.com/" + rid, "retrieved_at": "2026-10-16T00:00:00Z"}]}


class PlatformHubTests(unittest.TestCase):
    def test_hubs_list_curated_resources_under_every_platform_they_carry(self):
        rows = [row("github:a/bench", "Bench", "benchmark", ["android", "ios"]), row("github:a/model", "Model", "model", ["android"]),
            row("arxiv:2401.00001", "Old", "paper", ["android"], published_at="2024-01-01"), row("arxiv:2501.00001", "New", "paper", ["android"], published_at="2025-01-01"),
            row("github:a/pending", "Pending", "framework", ["android"], status="metadata_verified"), row("github:a/none", "None", "tool", ["unspecified"])]
        files = build.environment_pages(rows)
        self.assertEqual(sorted(files), ["docs/environments.md", "docs/environments/android.md", "docs/environments/ios.md"])
        android = files["docs/environments/android.md"]
        self.assertEqual(android.count("[Bench]("), 1)
        self.assertNotIn("Pending", android)
        self.assertLess(android.index("[New]("), android.index("[Old]("))
        self.assertIn("[Benchmarks (1)](#benchmarks) · [Models (1)](#models) · [Papers (2)](#papers)", android)
        self.assertIn("[Bench](", files["docs/environments/ios.md"])
        self.assertIn("| [Android](environments/android.md) | 4 | 1 | · | 1 | · | · | 2 |", files["docs/environments.md"])

    def test_readme_platform_line_in_both_languages(self):
        rows = [row("github:a/bench", "Bench", "benchmark", ["android", "web"]), row("github:a/b2", "B2", "benchmark", ["web"])]
        report = {"bibliographic_records": 0}
        self.assertIn("**By platform:** [Web](docs/environments/web.md) **2** · [Android](docs/environments/android.md) **1**", build.explore(rows, report))
        self.assertIn("**按平台：** [Web](docs/environments/web.md) **2**", build.explore(rows, report, "zh"))


if __name__ == "__main__":
    unittest.main()
