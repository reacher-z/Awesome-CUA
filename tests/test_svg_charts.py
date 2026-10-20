from pathlib import Path
import random
import re
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build
import charts

ROOT = Path(__file__).resolve().parents[1]
SVG = "{http://www.w3.org/2000/svg}"


def row(rid, kind="paper", status="curated", year=None, environments=("web",)):
    return {"id": rid, "name": rid, "kind": kind, "review_status": status, "url": "https://example.com/" + rid, "environments": list(environments),
        "published_at": f"{year}-05-01" if year else None, "details": {}}


ROWS = [row("arxiv:1", year=2026), row("arxiv:2", status="metadata_verified", year=2026), row("arxiv:3", "survey", year=2026),
    row("arxiv:4", status="metadata_verified", year=2024), row("arxiv:5", year=2010), row("arxiv:6", status="metadata_verified", year=2001), row("arxiv:7"),
    row("github:a/bench", "benchmark", environments=("web", "android", "web")), row("github:a/data", "dataset", environments=("android",)),
    row("github:a/model", "model", environments=("desktop", "windows")), row("github:a/agent", "agent"), row("github:a/brand", "company"),
    row("github:a/draft", "framework", status="metadata_verified", environments=("macos",)), row("arxiv:8", year=2025, environments=("ios",))]


class ChartDataTests(unittest.TestCase):
    def test_years_fold_before_the_window_and_keep_empty_years_and_undated_records(self):
        years, series = build.papers_by_year(ROWS, span=3)
        self.assertEqual(years, ["≤2023", "2024", "2025", "2026", "Undated"])
        self.assertEqual(series, [("Reviewed", [1, 0, 1, 2, 1]), ("Metadata only", [1, 1, 0, 1, 0])])
        self.assertEqual(build.papers_by_year(ROWS)[0], ["≤2016", *map(str, range(2017, 2027)), "Undated"])
        self.assertEqual(build.papers_by_year([row("arxiv:1", year=2025)]), (["2025"], [("Reviewed", [1]), ("Metadata only", [0])]))
        self.assertEqual(build.papers_by_year([]), ([], [("Reviewed", []), ("Metadata only", [])]))

    def test_platforms_count_curated_resources_once_per_facet_by_kind_group(self):
        platforms, series = build.platforms_by_group(ROWS)
        # macOS carries only an uncurated framework, so it has no bar; duplicate facets count once.
        self.assertEqual(platforms, ["Web", "Desktop", "Windows", "Android", "iOS"])
        self.assertEqual(series, [("Benchmarks and datasets", [1, 0, 0, 2, 0]), ("Models", [0, 1, 1, 0, 0]), ("Systems", [2, 0, 0, 0, 0]), ("Papers", [4, 0, 0, 0, 1])])

    def test_alt_text_states_the_figures_in_both_languages(self):
        en, zh = build.chart_lines(ROWS), build.chart_lines(ROWS, "zh")
        self.assertIn('alt="Stacked column chart of 8 paper and survey records by publication year, ≤2016 to 2026.', en[0])
        self.assertIn("2026 has the most records: 3, of which 2 are reviewed.", en[0])
        self.assertIn("Largest: Web 7, Android 2, Desktop 1.", en[2])
        self.assertIn("数量最多的是 Web 7、Android 2、Desktop 1。", zh[2])
        for lines, links in ((en, "[bibliography by year](docs/papers.md)"), (zh, "[按年份的论文目录](docs/papers.md)")):
            self.assertIn('<source media="(prefers-color-scheme: dark)" srcset="docs/assets/papers-by-year-dark.svg"><img src="docs/assets/papers-by-year-light.svg"', lines[0])
            self.assertIn('srcset="docs/assets/platforms-dark.svg"><img src="docs/assets/platforms-light.svg"', lines[2])
            self.assertIn(links, lines[4])
        self.assertIn('srcset="assets/platforms-dark.svg"', build.chart_lines(ROWS, base="")[2])
        self.assertEqual(build.chart_lines([])[0].count("alt="), 1)


class ChartSvgTests(unittest.TestCase):
    def test_output_is_deterministic_and_independent_of_record_order(self):
        files = build.chart_files(ROWS)
        self.assertEqual(sorted(files), [f"docs/assets/{name}-{theme}.svg" for name in ("papers-by-year", "platforms") for theme in ("dark", "light")])
        shuffled = ROWS[:]
        random.Random(7).shuffle(shuffled)
        self.assertEqual(build.chart_files(shuffled), files)
        for content in files.values():
            self.assertNotRegex(content, r"\d{4}-\d{2}-\d{2}|\d{2}:\d{2}")
            self.assertNotRegex(content, r'\b(?:[xy][12]?|width|height|d)="[^"]*\d\.\d\d')
            self.assertTrue(content.endswith("</svg>\n"))

    def test_svgs_are_accessible_and_use_their_theme_surface(self):
        for name, content in build.chart_files(ROWS).items():
            svg = ET.fromstring(content)
            theme = charts.THEMES["dark" if name.endswith("-dark.svg") else "light"]
            self.assertEqual(svg.get("role"), "img")
            self.assertEqual([svg.find(SVG + tag).get("id") for tag in ("title", "desc")], svg.get("aria-labelledby").split())
            self.assertIn(f'fill="{theme["surface"]}"', content)
            # Every column or bar group carries a tooltip with its exact counts.
            self.assertTrue(all(g.find(SVG + "title") is not None for g in svg.iter(SVG + "g")))

    def test_columns_stack_from_the_baseline_with_a_surface_gap_and_rounded_data_end(self):
        content = charts.stacked_columns("c", "light", "T", "S", ["2025"], [("A", [10]), ("B", [10])], ["#111111", "#222222"])
        svg = ET.fromstring(content)
        lower = [r for r in svg.iter(SVG + "rect") if r.get("fill") == "#111111" and r.get("width") == "24"][0]
        upper = [p for p in svg.iter(SVG + "path") if p.get("fill") == "#222222"][0]
        top = float(upper.get("d").split("V")[0].split()[-1])
        self.assertEqual(top, float(lower.get("y")) - charts.GAP)
        self.assertIn("A4 4 0 0 1", upper.get("d"))
        self.assertIn("<title>2025: 20 (A 10, B 10)</title>", content)

    def test_segment_values_are_printed_only_where_they_fit(self):
        content = charts.stacked_bars("b", "light", "T", "S", ["Web"], [("A", [1000]), ("B", [1])], ["#2a78d6", "#eda100"])
        self.assertRegex(content, r">1,000</text>")
        self.assertNotRegex(content, r"fill:#\w+\">1</text>")
        self.assertIn(">1,001</text>", content)
        self.assertEqual(charts.ink("#eda100"), "#000000")
        self.assertEqual(charts.ink("#184f95"), "#ffffff")

    def test_values_inside_every_fill_clear_text_contrast(self):
        def contrast(a, b):
            high, low = sorted((charts.luminance(a), charts.luminance(b)), reverse=True)
            return (high + 0.05) / (low + 0.05)
        for theme in charts.THEMES.values():
            for fill in theme["categorical"] + theme["ordinal"]:
                self.assertGreaterEqual(contrast(charts.ink(fill), fill), 4.5, fill)

    def test_small_nonzero_segments_are_never_swallowed_by_the_gap(self):
        # One HarmonyOS-like bar of 1 + 2 beside a 600-wide bar, and a 3 + 8 column beside a 1,000 column.
        bars = ET.fromstring(charts.stacked_bars("b", "light", "T", "S", ["Big", "Small"], [("A", [600, 0]), ("B", [0, 1]), ("C", [0, 2])], ["#2a78d6", "#eb6834", "#1baf7a"]))
        columns = ET.fromstring(charts.stacked_columns("c", "light", "T", "S", ["2017", "2026"], [("A", [3, 500]), ("B", [8, 500])], ["#256abf", "#86b6ef"]))
        for svg, fills in ((bars, ["#2a78d6", "#eb6834", "#1baf7a"]), (columns, ["#256abf", "#86b6ef", "#256abf", "#86b6ef"])):
            marks = [mark for group in svg.iter(SVG + "g") for mark in group if mark.tag in (SVG + "rect", SVG + "path")]
            self.assertEqual([mark.get("fill") for mark in marks], fills)

    def test_an_empty_chart_draws_no_degenerate_axis(self):
        svg = ET.fromstring(charts.stacked_bars("b", "light", "T", "S", [], [("A", [])], ["#2a78d6"]))
        self.assertEqual(list(svg.iter(SVG + "line")), [])
        self.assertEqual(list(svg.iter(SVG + "g")), [])

    def test_readmes_share_one_generated_chart_block(self):
        block = re.compile(r"<!-- CHARTS:START -->(.*?)<!-- CHARTS:END -->", re.S)
        en, zh = (block.search((ROOT / name).read_text(encoding="utf-8")).group(1) for name in ("README.md", "README.zh-CN.md"))
        sources = lambda text: re.findall(r'(?:src|srcset)="([^"]+)"', text)
        self.assertEqual(sources(en), sources(zh))
        self.assertEqual(len(sources(en)), 4)
        for source in sources(en):
            self.assertTrue((ROOT / source).is_file(), source)


if __name__ == "__main__":
    unittest.main()
