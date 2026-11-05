"""Declared discovery-source formats: section-scoped lists, DOI opt-in, spreadsheets, Hub indexes and arXiv queries."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
import urllib.parse
from unittest import mock
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build
import catalog
from test_arxiv_metadata import entry, feed

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RELS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE = "http://schemas.openxmlformats.org/package/2006/relationships"
SURVEY = """# Awesome agents
- [Preamble](https://github.com/o/preamble)
## A. Related Surveys
```bash
# install
```
- [Survey](https://arxiv.org/abs/2401.00001)
## B. Robots
- [Robot](https://github.com/o/robot)
## E. Benchmarks
### Robotic Systems
- [Arm](https://github.com/o/arm)
### Multimodal Agents
#### Interaction
- [WebArena](https://github.com/web-arena-x/webarena) [doi](https://doi.org/10.1145/3832165)
"""


def workbook(sheets, shared=(), target="worksheets/sheet{}.xml"):
    """A minimal Office Open XML workbook: sheets are (name, rows_xml, hyperlinks)."""
    body = io.BytesIO()
    with zipfile.ZipFile(body, "w") as book:
        entries = "".join(f'<sheet name="{name}" sheetId="{i}" r:id="rId{i}"/>' for i, (name, _, _) in enumerate(sheets, 1))
        book.writestr("xl/workbook.xml", f'<workbook xmlns="{MAIN}" xmlns:r="{RELS}"><sheets>{entries}</sheets></workbook>')
        book.writestr("xl/_rels/workbook.xml.rels", f'<Relationships xmlns="{PACKAGE}">' + "".join(
            f'<Relationship Id="rId{i}" Type="worksheet" Target="{target.format(i)}"/>' for i in range(1, len(sheets) + 1)) + "</Relationships>")
        if shared:
            book.writestr("xl/sharedStrings.xml", f'<sst xmlns="{MAIN}">' + "".join(f"<si><t>{text}</t></si>" for text in shared) + "</sst>")
        for i, (_, rows, links) in enumerate(sheets, 1):
            refs = "".join(f'<hyperlink ref="{ref}" r:id="L{j}"/>' for j, (ref, _, _) in enumerate(links))
            book.writestr(f"xl/worksheets/sheet{i}.xml", f'<worksheet xmlns="{MAIN}" xmlns:r="{RELS}"><sheetData>{rows}</sheetData>'
                          + (f"<hyperlinks>{refs}</hyperlinks>" if links else "") + "</worksheet>")
            if links:
                book.writestr(f"xl/worksheets/_rels/sheet{i}.xml.rels", f'<Relationships xmlns="{PACKAGE}">' + "".join(
                    f'<Relationship Id="L{j}" Type="hyperlink" Target="{target}"{mode}/>' for j, (_, target, mode) in enumerate(links)) + "</Relationships>")
    return body.getvalue()


def sha(body):
    return hashlib.sha256(body).hexdigest()


class SectionAndDoiTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(mock.patch.object(catalog, "DATA", self.path))
        self.enterContext(mock.patch.object(catalog, "fetch", side_effect=self.fetch))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.source = {"id": "survey", "name": "Survey", "url": "https://raw.githubusercontent.com/o/survey/main/README.md",
                       "homepage": "https://github.com/o/survey", "sections": ["a. related surveys", "Multimodal Agents"]}
        self.requests = []

    def fetch(self, url, refresh=False):
        self.requests.append(url)
        return {"url": url, "ok": True, "status": 200, "sha256": sha(SURVEY.encode()), "retrieved_at": "2026-11-05T00:00:00Z"}, SURVEY.encode()

    def discover(self, source):
        catalog.write_json(self.path / "sources.json", [source])
        catalog.discover(types.SimpleNamespace(refresh=True, limit=0))
        return {row["id"]: row for row in catalog.read_jsonl(self.path / "candidates.jsonl")}

    def test_sections_keep_links_under_matching_headings_and_their_subheadings(self):
        links = catalog.source_links(self.source, SURVEY.encode())
        # Text before the first heading and other sections stay outside the selection; a '# comment' inside a
        # code block is not a heading, so the survey after it is still under "A. Related Surveys".
        self.assertEqual(links, [
            (7, "A. Related Surveys", "https://arxiv.org/abs/2401.00001"),
            (15, "Interaction", "https://github.com/web-arena-x/webarena"),
            (15, "Interaction", "https://doi.org/10.1145/3832165")])
        # Without a declaration every link is read, as before.
        self.assertEqual(len(catalog.source_links({"parser": "links"}, SURVEY.encode())), 6)

    def test_a_doi_that_ends_a_sentence_keeps_the_bare_doi_identity(self):
        bare = catalog.canonical("https://doi.org/10.1145/3832165", allow_doi=True)
        for text in ["https://doi.org/10.1145/3832165.", "https://doi.org/10.1145/3832165,", "https://doi.org/10.1145/3832165);"]:
            with self.subTest(text=text):
                self.assertEqual(catalog.canonical(text, allow_doi=True), bare)
        # Balanced parentheses stay part of a DOI.
        self.assertEqual(catalog.canonical("https://doi.org/10.1002/(SICI)1097-4571", allow_doi=True)[1], "https://doi.org/10.1002/(sici)1097-4571")

    def test_doi_links_are_candidates_only_for_a_source_that_declares_them(self):
        self.assertEqual(sorted(self.discover(self.source)), ["arxiv:2401.00001", "github:web-arena-x/webarena"])
        candidates = self.discover({**self.source, "doi_links": True})
        doi = catalog.canonical("https://doi.org/10.1145/3832165", allow_doi=True)
        self.assertEqual(sorted(candidates), sorted(["arxiv:2401.00001", "github:web-arena-x/webarena", doi[0]]))
        self.assertEqual({key: candidates[doi[0]][key] for key in ("url", "provider")}, {"url": "https://doi.org/10.1145/3832165", "provider": "url"})
        self.assertEqual([(o["source_id"], o["line"]) for o in candidates[doi[0]]["discovered_in"]], [("survey", 15)])
        # A later pass by a source without DOI links keeps the stored DOI candidate as history instead of dropping it.
        catalog.write_json(self.path / "sources.json", [])
        catalog.discover(types.SimpleNamespace(refresh=True, limit=0))
        retained = {row["id"]: row for row in catalog.read_jsonl(self.path / "candidates.jsonl")}
        self.assertEqual(retained[doi[0]]["url"], "https://doi.org/10.1145/3832165")

    def test_registry_reports_unusable_selection_keys(self):
        good = [self.source, {**self.source, "id": "doi", "doi_links": True},
                {"id": "hub", "url": "https://huggingface.co/api/datasets?search=gui&limit=100", "homepage": "https://huggingface.co/datasets",
                 "parser": "huggingface_datasets", "min_likes": 3, "id_pattern": "(?i)gui"}]
        self.assertEqual(build.validate_sources(good), [])
        for key, value, message in [
                ("sections", [], "sections must list 1-20 distinct heading texts of at most 140 characters"),
                ("sections", ["Agents", "Agents"], "sections must list 1-20 distinct heading texts of at most 140 characters"),
                ("doi_links", "yes", "doi_links, when present, must be true"),
                ("sections", [["Agents"]], "sections must list 1-20 distinct heading texts of at most 140 characters"),
                ("min_likes", 3, "min_likes is not an option of the links parser"),
                ("parser", "rss", "unknown discovery-source parser 'rss'"),
                ("parser", ["links"], "unknown discovery-source parser ['links']")]:
            with self.subTest(key=key, value=value):
                self.assertEqual(build.validate_sources([{**self.source, key: value}]), ["survey: " + message])
        for value in ["(", "x" * 201, 7]:
            with self.subTest(id_pattern=value):
                self.assertEqual(build.validate_sources([{**good[2], "id_pattern": value}]),
                                 ["hub: id_pattern must be a regular expression of at most 200 characters"])
        with self.assertRaisesRegex(ValueError, "sections is not an option of the arxiv_query parser"):
            catalog.source_links({**self.source, "parser": "arxiv_query"}, b"")

    def test_an_unusable_declaration_is_reported_without_a_request(self):
        self.discover(self.source)
        before = catalog.read_jsonl(self.path / "candidates.jsonl")
        self.requests.clear()
        catalog.write_json(self.path / "sources.json", [{**self.source, "doi_links": "yes"}])
        catalog.discover(types.SimpleNamespace(refresh=True, limit=0))
        run = catalog.read_json(self.path / "discovery-runs.json")[0]
        self.assertEqual(self.requests, [])
        self.assertEqual({key: run[key] for key in ("ok", "state", "request_attempted", "unique_resources", "error")},
                         {"ok": False, "state": "failed", "request_attempted": False, "unique_resources": 0,
                          "error": "Invalid discovery source: doi_links, when present, must be true"})
        # Earlier occurrences stay, as after any failed pass.
        self.assertEqual(catalog.read_jsonl(self.path / "candidates.jsonl"), before)


class SpreadsheetTests(unittest.TestCase):
    ROWS = ('<row r="1"><c r="A1" t="s"><v>0</v></c></row>'
            '<row r="2"><c r="A2" t="s"><v>1</v></c><c r="B2" t="inlineStr"><is><t>see https://arxiv.org/abs/2404.07972 now</t></is></c></row>'
            '<row r="3"><c r="A3" t="str"><f>HYPERLINK("https://github.com/xlang-ai/OSWorld","OSWorld")</f><v>OSWorld</v></c><c r="B3"><v>42</v></c></row>'
            '<row r="5"><c r="C5" t="s"><v>2</v></c></row>')

    def test_hyperlinks_formulas_and_url_text_are_located_by_sheet_and_row(self):
        body = workbook([("Eval Results", self.ROWS, [("C5", "https://os-world.github.io/agent", ' TargetMode="External"'),
                                                      ("A1:B1", "#Sheet2!A1", "")]),
                         ("工作表1", '<row r="2"><c r="A2" t="s"><v>3</v></c></row>', [])],
                        shared=["Model", "Agent https://example.org/agent", "Agent page", "https://www.modelscope.cn/models/o/m"])
        self.assertEqual(catalog.source_links({"parser": "xlsx_links"}, body), [
            (2, "Eval Results", "https://example.org/agent"), (2, "Eval Results", "https://arxiv.org/abs/2404.07972"),
            (3, "Eval Results", "https://github.com/xlang-ai/OSWorld"), (5, "Eval Results", "https://os-world.github.io/agent"),
            (2, "工作表1", "https://www.modelscope.cn/models/o/m")])

    def test_malformed_or_oversized_workbooks_fail_the_source_pass(self):
        sheet = [("Results", '<row r="1"><c r="A1"><v>1</v></c></row>', [])]
        with self.assertRaisesRegex(ValueError, "not an Office Open XML workbook"):
            catalog.source_links({"parser": "xlsx_links"}, b"<html>Sign in</html>")
        with mock.patch.object(catalog, "XLSX_MAX_BYTES", 100), self.assertRaisesRegex(ValueError, "unpacked part budget"):
            catalog.source_links({"parser": "xlsx_links"}, workbook(sheet))
        broken = io.BytesIO()
        with zipfile.ZipFile(broken, "w") as book:
            book.writestr("xl/workbook.xml", "<workbook")
        with self.assertRaisesRegex(ValueError, "not well-formed XML"):
            catalog.source_links({"parser": "xlsx_links"}, broken.getvalue())
        for target in ["../../evil/sheet{}.xml", "/docProps/app{}.xml", "worksheets/sheet{}.bin"]:
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, "outside the workbook"):
                catalog.source_links({"parser": "xlsx_links"}, workbook(sheet, target=target))
        with self.assertRaisesRegex(ValueError, "part is missing"):
            catalog.source_links({"parser": "xlsx_links"}, workbook(sheet, target="worksheets/absent{}.xml"))


class HubIndexTests(unittest.TestCase):
    def source(self, kind="datasets", query="search=android&sort=likes&direction=-1&limit=100", **options):
        return {"id": "hub", "url": f"https://huggingface.co/api/{kind}?{query}", "homepage": "https://huggingface.co",
                "parser": "huggingface_" + kind, **options}

    def test_search_indexes_apply_declared_like_floor_and_identifier_pattern(self):
        body = json.dumps([{"id": "stepfun-ai/AndroidDaily", "likes": 30}, {"id": "o/android_icons", "likes": 3},
                           {"id": "o/android-novel", "likes": 2}, {"id": "o/guitar-chords", "likes": 50}]).encode()
        links = catalog.source_links(self.source(min_likes=3, id_pattern="(?i)android"), body)
        self.assertEqual(links, [(None, 'Hub dataset search "android"; relevance awaits review', "https://huggingface.co/datasets/stepfun-ai/AndroidDaily"),
                                 (None, 'Hub dataset search "android"; relevance awaits review', "https://huggingface.co/datasets/o/android_icons")])
        models = catalog.source_links(self.source("models", "author=microsoft&search=GUI&limit=10"), json.dumps([{"id": "microsoft/GUI-Actor-2B"}]).encode())
        self.assertEqual(models, [(None, 'Hub model search "GUI" by microsoft; relevance awaits review', "https://huggingface.co/microsoft/GUI-Actor-2B")])
        # A publisher index without a search keeps its established section label.
        publisher = catalog.source_links(self.source("datasets", "author=osunlp&limit=100"), json.dumps([{"id": "osunlp/Mind2Web"}]).encode())
        self.assertEqual(publisher, [(None, "Publisher dataset index; relevance and variant identity await review", "https://huggingface.co/datasets/osunlp/Mind2Web")])

    def test_unbounded_or_ambiguous_indexes_are_rejected(self):
        listing = json.dumps([{"id": "o/model", "likes": 1}]).encode()
        for source, body in [(self.source(query="limit=100"), listing), (self.source(query="search=gui&limit=101"), listing),
                             (self.source(query="search=gui&limit=100&full=true"), listing), (self.source(query="search=gui&search=web&limit=100"), listing),
                             (self.source(query="author=a&author=b&limit=100"), listing), (self.source(query="search=gui%0Aagent&limit=100"), listing),
                             ({**self.source(), "url": "https://huggingface.co/api/models?search=gui&limit=100"}, listing),
                             (self.source(query="author=other&limit=100"), listing), (self.source(min_likes=2), json.dumps([{"id": "o/model"}]).encode()),
                             (self.source(), json.dumps({"id": "o/model"}).encode()), (self.source(query="search=gui&limit=1"), b'[{"id":"a/b"},{"id":"c/d"}]')]:
            with self.subTest(url=source["url"], body=body[:40]), self.assertRaises(ValueError):
                catalog.source_links(source, body)

    def test_collections_map_each_item_type_and_skip_nested_collections(self):
        source = {"id": "collection", "url": "https://huggingface.co/api/collections/maxiw/gui-datasets-66c512aef77e8e56f38a670b",
                  "homepage": "https://huggingface.co/collections/maxiw/gui-datasets-66c512aef77e8e56f38a670b", "parser": "huggingface_collection"}
        body = {"slug": "maxiw/gui-datasets-66c512aef77e8e56f38a670b", "items": [
            {"type": "model", "id": "ByteDance-Seed/UI-TARS-72B-DPO"}, {"type": "dataset", "id": "OpenGVLab/GUI-Odyssey"},
            {"type": "space", "id": "showlab/ShowUI"}, {"type": "paper", "id": "2411.17465"}, {"type": "collection", "id": "a/b-1"}]}
        section = "Hub collection maxiw/gui-datasets-66c512aef77e8e56f38a670b; relevance awaits review"
        self.assertEqual(catalog.source_links(source, json.dumps(body).encode()), [
            (None, section, "https://huggingface.co/ByteDance-Seed/UI-TARS-72B-DPO"), (None, section, "https://huggingface.co/datasets/OpenGVLab/GUI-Odyssey"),
            (None, section, "https://huggingface.co/spaces/showlab/ShowUI"), (None, section, "https://huggingface.co/papers/2411.17465")])
        self.assertEqual(catalog.canonical("https://huggingface.co/papers/2411.17465")[0], "arxiv:2411.17465")
        for changed, response in [(source, {**body, "slug": "other/list-1"}), (source, {**body, "items": [{"type": "user", "id": "a/b"}]}),
                                  (source, {**body, "items": [{"type": "paper", "id": "not-a-paper"}]}), (source, [body]),
                                  ({**source, "url": source["url"] + "?limit=5"}, body), ({**source, "url": "https://huggingface.co/api/collections/maxiw"}, body)]:
            with self.subTest(url=changed["url"], response=str(response)[:60]), self.assertRaises(ValueError):
                catalog.source_links(changed, json.dumps(response).encode())


class ArxivQueryTests(unittest.TestCase):
    QUERY = 'abs:"GUI agent" OR abs:"web agents"'

    def source(self, **params):
        query = {"search_query": self.QUERY, "start": 0, "max_results": 2000, "sortBy": "submittedDate", "sortOrder": "descending", **params}
        return {"id": "arxiv-abstract", "url": "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(query),
                "homepage": "https://arxiv.org", "parser": "arxiv_query"}

    def test_entries_become_version_free_paper_candidates(self):
        old = entry(aid="cs/0208008")
        body = feed([entry(aid="2504.12682", version=2), old, entry(aid="2410.02052")], total=3)
        self.assertEqual(catalog.source_links(self.source(), body), [
            (None, "arXiv API query; relevance awaits review", "https://arxiv.org/abs/2504.12682"),
            (None, "arXiv API query; relevance awaits review", "https://arxiv.org/abs/2410.02052")])

    def test_queries_must_be_bounded_first_pages_of_the_official_api(self):
        body = feed([], total=0)
        self.assertEqual(catalog.source_links(self.source(), body), [])
        for source in [self.source(start=100), self.source(max_results=2001), self.source(id_list="2401.00001"),
                       {**self.source(), "url": self.source()["url"].replace("export.arxiv.org", "arxiv.org")}]:
            with self.subTest(url=source["url"]), self.assertRaises(ValueError):
                catalog.source_links(source, body)
        for body in [b"<feed", feed([entry()], total=None), feed([entry(), entry(aid="2610.00002")], total=1)]:
            with self.subTest(body=body[:60]), self.assertRaises(ValueError):
                catalog.source_links(self.source(), body)

    def test_an_identifier_list_names_exactly_the_papers_it_queries(self):
        listed = {"id": "backfill", "url": "https://export.arxiv.org/api/query?id_list=1812.09195,2106.00133&max_results=2",
                  "homepage": "https://arxiv.org", "parser": "arxiv_query"}
        body = feed([entry(aid="1812.09195"), entry(aid="2106.00133", version=3)], total=2)
        self.assertEqual(catalog.source_links(listed, body), [
            (None, "arXiv API identifier list; relevance awaits review", "https://arxiv.org/abs/1812.09195"),
            (None, "arXiv API identifier list; relevance awaits review", "https://arxiv.org/abs/2106.00133")])
        with self.assertRaisesRegex(ValueError, "not requested"):
            catalog.source_links(listed, feed([entry(aid="1812.09195"), entry(aid="2401.00001")], total=2))
        for query in ["id_list=1812.09195,1812.09195&max_results=2", "id_list=1812.09195,2106.00133&max_results=1",
                      "id_list=cs/0208008&max_results=1", "id_list=1812.09195&search_query=ti:web&max_results=1", "max_results=5"]:
            with self.subTest(query=query), self.assertRaises(ValueError):
                catalog.source_links({**listed, "url": "https://export.arxiv.org/api/query?" + query}, body)


class ReferenceTargetTests(unittest.TestCase):
    def edge(self, url):
        return {"target_id": catalog.canonical(url)[0], "target_url": catalog.canonical(url)[1]}

    def test_repositories_and_hub_models_or_datasets_are_promoted_but_other_pages_are_not(self):
        for url, provider in [("https://arxiv.org/abs/2401.00001", "arxiv"), ("https://github.com/e2b-dev/surf", "github"),
                              ("https://huggingface.co/microsoft/OmniParser", "url"), ("https://huggingface.co/datasets/osunlp/Mind2Web", "url")]:
            with self.subTest(url=url):
                self.assertEqual(catalog.reference_target(self.edge(url))[2], provider)
        for url in ["https://huggingface.co/spaces/showlab/ShowUI", "https://huggingface.co/collections/OS-Copilot/os-atlas-67246e44",
                    "https://huggingface.co/Hcompany", "https://huggingface.co/docs/hub", "https://huggingface.co/blog/open_rail",
                    "https://huggingface.co/datasets/JackBAI/trajectories/tree/main", "https://example.org/tool"]:
            with self.subTest(url=url):
                self.assertIsNone(catalog.reference_target(self.edge(url)))
        # A stored target ID that no longer matches its URL is not trusted.
        self.assertIsNone(catalog.reference_target({"target_id": "github:a/b", "target_url": "https://github.com/c/d"}))


if __name__ == "__main__":
    unittest.main()
