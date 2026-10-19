from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import catalog


# Hub datasets and checkpoints that had no reviewed relation (#93), with the link their retained sources state.
LINKED = {"url:c5eb975c0d66f8a2954f": ("variant_of", "github:zai-org/cogagent"),
    "url:c79e152e6f7af1a9efed": ("component_of", "github:likaixin2000/screenspot-pro-gui-grounding"),
    "url:79287058342289aa5d45": ("documented_by", "arxiv:2502.01977"),
    "url:07b65dc937756ddff4a1": ("component_of", "github:ariaui/aria-ui"),
    "url:25a4d0ab29b60250863a": ("component_of", "github:murtyshikhar/nnetnav"),
    "url:4f47abde8cd28a1ec1e1": ("component_of", "github:murtyshikhar/nnetnav"),
    "url:631e74223e198ef40202": ("documented_by", "arxiv:2509.15221"),
    "url:b80bfa0a4939a493a11f": ("documented_by", "arxiv:2409.14818"),
    "url:c4898ad1bfc049926a63": ("component_of", "github:osu-nlp-group/uground"),
    "url:d1830de02226155ee16d": ("component_of", "github:microsoft/phi-ground"),
    "url:f976dec3d1c5e0bedbd7": ("component_of", "github:showlab/showui"),
    "url:72f7fe0211c6551b945f": ("documented_by", "arxiv:2505.15277"),
    "url:6aa1aa58a7a888395189": ("documented_by", "arxiv:2605.25624"),
    "url:ab26f9ef56d651cee587": ("documented_by", "arxiv:2603.08533"),
    "url:fe43af1801032be708cc": ("component_of", "github:showlab/showui-pi")}
# Their cards name no catalogued family or paper; the notes say why.
UNLINKED = {"url:13b9442bcb6a8b984c4f", "url:aa28e1329a52e341d285", "url:b854ff53e497da3a5ad8"}
# Checkpoints whose cards link their own code repository.
CHECKPOINTS = {"url:23ad240757185c6f7eac": "github:jcwang0602/seg2click", "url:29588aa5651b5839c045": "github:jcwang0602/seg2click",
    "url:7405463ba56f9a41e79a": "github:jcwang0602/seg2click", "url:826f3753905c5c43bf46": "github:jcwang0602/seg2click",
    "url:fec1c5aa8fd93cb78923": "github:jcwang0602/seg2click", "url:d35224f787e7ec21ce36": "github:openmobile2/openmobile2-code",
    "url:1611de0e6d606165d12d": "github:openmobile2/openmobile2-code", "url:de31b07ff24ab15d9bdf": "github:prentisai/groundgui"}


class HubRelationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = {r["id"]: r for r in catalog.read_jsonl(catalog.DATA / "catalog.jsonl")}

    def cited(self, record, relation):
        return [ev for ev in record["evidence"] if ev["url"] == relation["evidence_url"] and "relations" in ev["supports"]]

    def test_former_orphans_link_to_family_or_paper(self):
        for rid, (kind, target) in LINKED.items():
            with self.subTest(rid):
                record = self.records[rid]
                matches = [rel for rel in record["relations"] if (rel["type"], rel["target_id"]) == (kind, target)]
                self.assertEqual(len(matches), 1)
                self.assertTrue(self.cited(record, matches[0]))
                self.assertEqual(self.records[target]["review_status"], "curated")

    def test_unlinked_records_explain_why(self):
        for rid in UNLINKED:
            with self.subTest(rid):
                record = self.records[rid]
                self.assertEqual(record["relations"], [])
                self.assertRegex(record["notes"], r"\bso no (?:paper (?:or family )?)?relation is recorded\.$")
                self.assertTrue(any("notes" in ev["supports"] for ev in record["evidence"]))

    def test_checkpoint_is_a_variant_of_its_code_repository(self):
        for rid, target in CHECKPOINTS.items():
            with self.subTest(rid):
                relations = {(rel["type"], rel["target_id"]) for rel in self.records[rid]["relations"]}
                self.assertIn(("variant_of", target), relations)
                self.assertNotIn(("uses", target), relations)


if __name__ == "__main__":
    unittest.main()
