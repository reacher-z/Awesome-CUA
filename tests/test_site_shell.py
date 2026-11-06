import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import search_pages  # noqa: E402
import site_shell  # noqa: E402


class StarCountTests(unittest.TestCase):
    def tearDown(self):
        site_shell.configure()

    def test_display_rounds_down_and_never_overstates(self):
        for count, shown in ((1, "1"), (44, "44"), (999, "999"), (1000, "1k"), (1032, "1k"), (1212, "1.2k"), (1999, "1.9k"), (9999, "9.9k"), (12345, "12k")):
            self.assertEqual(site_shell.short_count(count), shown)

    def test_build_reads_counts_from_the_workflow_and_drops_invalid_values(self):
        value = json.dumps({"a/b": 5, "c/d": 0, "e/f": "7", "g/h": True})
        with mock.patch.dict(os.environ, {"AWESOMECUA_REPO_STARS": value}):
            self.assertEqual(search_pages.repository_stars(), {"a/b": 5})
        for bad in ("", "not json", "[1]"):
            with mock.patch.dict(os.environ, {"AWESOMECUA_REPO_STARS": bad}):
                self.assertEqual(search_pages.repository_stars(), {})

    def test_only_landing_pages_carry_a_count_in_their_html(self):
        site_shell.configure(stars={site_shell.WEBSITEBENCH_REPO: 44, site_shell.SITE_REPO: 1212})
        self.assertIn(f'data-star-count="{site_shell.WEBSITEBENCH_REPO}">44<', site_shell.top(live=True))
        self.assertIn(f'data-star-count="{site_shell.SITE_REPO}">1.2k<', site_shell.top(live=True))
        self.assertIn(f'data-star-count="{site_shell.WEBSITEBENCH_REPO}"></span>', site_shell.top())

    def test_a_missing_count_leaves_no_empty_slot(self):
        site_shell.configure(stars={site_shell.SITE_REPO: 7})
        self.assertNotIn(f'data-star-count="{site_shell.WEBSITEBENCH_REPO}"', site_shell.top(live=True))
        self.assertIn(f'data-star-count="{site_shell.SITE_REPO}">7<', site_shell.top(live=True))

    def test_fallback_without_counts_still_shows_labelled_links(self):
        site_shell.configure()
        top = site_shell.top(live=True)
        self.assertIn(">Star<", top)
        self.assertIn(f'href="{site_shell.WEBSITEBENCH_URL}"', top)
        self.assertIn('href="https://github.com/reacher-z/Awesome-CUA"', top)


class PromotionShellTests(unittest.TestCase):
    def test_bar_and_star_button_exist_in_both_languages(self):
        for lang, text in (("en", "New: <b>WebsiteBench.</b>"), ("zh-CN", "新发布：<b>WebsiteBench。</b>")):
            top = site_shell.top(lang=lang)
            self.assertIn(text, top)
            self.assertIn('class="star-btn"', top)
            self.assertIn("data-dismiss-announce", top)

    def test_links_keep_the_referrer_and_the_policy_sends_the_origin(self):
        html = site_shell.top() + site_shell.bottom()
        self.assertNotIn("noreferrer", html)
        self.assertIn('content="strict-origin-when-cross-origin"', site_shell.head_assets())

    def test_footer_lists_all_four_repositories(self):
        footer = site_shell.footer()
        self.assertIn("More from the maintainers", footer)
        for repo, *_ in site_shell.MAINTAINER_REPOS:
            self.assertIn(f'href="https://github.com/{repo}"', footer)

    def test_the_browser_never_calls_github_for_counts(self):
        self.assertNotIn("api.github.com", (ROOT / "web/assets/site.js").read_text(encoding="utf-8"))

    def test_star_note_is_quiet_and_links_to_this_repository(self):
        note = site_shell.star_note()
        self.assertIn("Useful? Star Awesome CUA on GitHub", note)
        self.assertIn('href="https://github.com/reacher-z/Awesome-CUA"', note)

    def test_resource_facts_read_as_prose_and_omit_empty_rows(self):
        record = {"id": "github:a/b", "kind": "benchmark", "name": "B", "summary": "S.", "url": "https://github.com/a/b", "environments": ["macos", "windows", "unspecified"], "identifiers": {}, "aliases": [],
                  "topics": ["web-navigation"], "last_verified_at": "2026-10-16T06:35:57Z", "published_at": None, "review_status": "curated", "details": {}, "relations": [],
                  "evidence": [], "licenses": {"code": None, "data": None, "weights": None, "document": None}, "authors": [], "scope": "core", "notes": ""}
        body = search_pages.resource_body(record, {record["id"]: record})
        self.assertIn("<dd>Benchmark</dd>", body)
        self.assertIn("<dd>macOS, Windows</dd>", body)
        self.assertIn("<dd>2026-10-16</dd>", body)
        self.assertNotIn("Record publication date", body)
        self.assertNotIn("06:35:57", body.split("Primary evidence")[0])

    def test_dismissal_is_guarded_and_applied_before_paint(self):
        script = site_shell.THEME_SCRIPT
        self.assertIn(f"localStorage.getItem('cua-announce')==='{site_shell.ANNOUNCEMENT_ID}'", script)
        self.assertLess(script.index("try{"), script.index("localStorage"))


if __name__ == "__main__":
    unittest.main()
