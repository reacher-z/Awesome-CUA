import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import land_prs


def jsonl(rows):
    return "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)


class GeneratedBlockTests(unittest.TestCase):
    def test_every_marker_pair_in_the_readme_is_emptied(self):
        text = ("intro\n<!-- STATS:START -->\n1,000 records\n<!-- STATS:END -->\n"
                "<!-- CHARTS:START -->\n<picture>chart</picture>\n<!-- CHARTS:END -->\noutro\n")
        stripped = land_prs.strip_blocks("README.md", text)
        self.assertNotIn("1,000 records", stripped)
        self.assertNotIn("<picture>", stripped)
        self.assertIn("<!-- CHARTS:START --><!-- CHARTS:END -->", stripped)
        self.assertTrue(stripped.startswith("intro\n") and stripped.endswith("outro\n"))

    def test_data_dictionary_keeps_its_fixed_block_list(self):
        text = "<!-- TOPICS:START -->x<!-- TOPICS:END --><!-- OTHER:START -->y<!-- OTHER:END -->"
        self.assertEqual(land_prs.strip_blocks("docs/data-dictionary.md", text),
                         "<!-- TOPICS:START --><!-- TOPICS:END --><!-- OTHER:START -->y<!-- OTHER:END -->")


class CandidateMergeTests(unittest.TestCase):
    def test_candidate_rows_from_both_sides_are_kept_in_id_order(self):
        base = jsonl([{"id": "arxiv:1"}, {"id": "arxiv:3"}])
        ours = jsonl([{"id": "arxiv:1"}, {"id": "arxiv:2"}, {"id": "arxiv:3"}])
        theirs = jsonl([{"id": "arxiv:1"}, {"id": "arxiv:3"}, {"id": "arxiv:4"}])
        merged = land_prs.merge_keyed("data/candidates.jsonl", base, ours, theirs)
        self.assertEqual([json.loads(l)["id"] for l in merged.splitlines()], ["arxiv:1", "arxiv:2", "arxiv:3", "arxiv:4"])

    def test_metadata_updates_are_keyed_too(self):
        self.assertIn("data/metadata-updates.jsonl", land_prs.KEYED_INPUTS)
        self.assertIn("data/candidates.jsonl", land_prs.SORTED_BY_ID)


if __name__ == "__main__":
    unittest.main()
