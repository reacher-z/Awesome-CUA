import copy
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build
import catalog
import lookup
import migrate_www_urls as migration
import url_identity

OLD = "url:978d1dcd70fde8661b9e"
NEW = "url:b3ffe248cc4292a5e7f0"
WWW = "https://www.browserbase.com"
BARE = "https://browserbase.com"


def write(directory, name, value):
    if name.endswith(".jsonl"):
        text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in value)
    else:
        text = json.dumps(value, indent=2) + "\n"
    (directory / name).write_text(text, encoding="utf-8")


def fixture(directory):
    occurrence = {"source_id": "one", "line": 4, "section": "Tools",
                  "receipt_id": "discovery:kept", "evidence": {
                      "url": "https://example.org/source", "sha256": "b" * 64,
                      "retrieved_at": "2026-01-01T00:00:00Z"}}
    second = {**occurrence, "line": 9}
    third = {**occurrence, "line": 12, "source_id": "two"}
    editorial = {"name": "Browserbase", "kind": "product", "url": WWW,
                 "environments": ["web"], "topics": [], "summary": "Browser automation.",
                 "editorial_reviewed": True, "reviewed_sha256": "a" * 64}
    organization = {**editorial, "id": "organization:browserbase", "kind": "company"}
    pending = {**editorial, "name": "Comet", "url": "https://www.perplexity.ai/comet",
               "editorial_reviewed": False}
    del pending["reviewed_sha256"]
    write(directory, "editorial.json", [editorial, organization, pending])
    primary = {"id": OLD, "url": WWW, "final_url": WWW + "/",
               "sha256": "a" * 64, "retrieved_at": "2026-01-01T00:00:00Z",
               "content_matched": True}
    write(directory, "primary-evidence.jsonl", [primary])
    write(directory, "enrichment.jsonl", [{
        "id": OLD, "source_url": WWW, "evidence_sha256": "a" * 64,
        "evidence": [{"url": WWW, "sha256": "a" * 64}],
        "references": [{"target_id": OLD, "url": WWW, "type": "mentions"}]}])
    write(directory, "candidates.jsonl", [
        {"id": OLD, "url": WWW, "provider": "url", "first_discovered_at": "2026-01-01T00:00:00Z",
         "discovered_in": [occurrence, second]},
        {"id": NEW, "url": BARE, "provider": "url", "first_discovered_at": "2026-02-01T00:00:00Z",
         "discovered_in": [copy.deepcopy(occurrence), third]}])
    write(directory, "candidate-reviews.json", [{
        "id": NEW, "url": BARE, "decision": "alias", "target_id": OLD, "reason": "www variant"}])
    write(directory, "exclusions.json", [{"id": "arxiv:2401.00001", "metadata_sha256": "c" * 64}])
    return editorial, primary, [occurrence, second, third]


def snapshot(directory):
    return {path.name: path.read_bytes() for path in directory.iterdir() if path.is_file()}


class CanonicalWWWTests(unittest.TestCase):
    def test_hosts_paths_queries_and_repeated_normalization(self):
        self.assertEqual(catalog.canonical(WWW + "/"), (NEW, BARE, "url"))
        for address in (
            "https://www.Example.org/item/?keep=yes&utm_source=test#section",
            "https://www.www.example.org/item?keep=yes",
        ):
            result = catalog.canonical(address)
            self.assertEqual(result[1], "https://example.org/item?keep=yes")
            self.assertEqual(catalog.canonical(result[1]), result)
        for address in ("https://github.com/example/repo", "https://arxiv.org/abs/2401.00001"):
            self.assertEqual(catalog.canonical(address.replace("://", "://www.")),
                             catalog.canonical(address))
        # Existing non-resource filtering applies equally to both spellings.
        self.assertEqual(catalog.canonical("https://www.x.com"), catalog.canonical("https://x.com"))

    def test_aliases_are_deterministic_policy_and_do_not_invent_evidence(self):
        declaration = url_identity.www_declaration(WWW, catalog.canonical)
        self.assertEqual(declaration["alias_id"], OLD)
        self.assertEqual(declaration["target_id"], NEW)
        record = {"id": NEW, "url": WWW, "aliases": [], "evidence": [{"sha256": "a" * 64}]}
        result = url_identity.attach_url_aliases([record], [declaration], catalog.canonical)[0]
        self.assertEqual(result["aliases"], [OLD, WWW])
        self.assertEqual(result["evidence"], record["evidence"])
        self.assertEqual(record["aliases"], [])
        for change in ({"target_id": "url:" + "0" * 20}, {"alias_id": NEW},
                       {"policy": "http-redirect"}, {"url": WWW + "/"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                url_identity.url_aliases([{**declaration, **change}], catalog.canonical)
        with self.assertRaises(ValueError):
            url_identity.url_aliases([declaration, declaration], catalog.canonical)
        with self.assertRaises(ValueError):
            url_identity.url_aliases([declaration], catalog.canonical,
                                     [{"id": OLD, "url": WWW}])

    def test_duplicate_gate_excludes_explicit_organization_identity(self):
        rows = [{"id": OLD, "url": WWW}, {"id": NEW, "url": BARE}]
        self.assertEqual(len(url_identity.www_duplicate_errors(rows, "Candidates")), 1)
        self.assertEqual(url_identity.www_duplicate_errors(
            [rows[1], {"id": "organization:browserbase", "url": WWW}], "Catalog"), [])

    def test_candidate_gate_detects_stale_clean_ids_and_duplicates(self):
        self.assertEqual(url_identity.candidate_identity_errors([
            {"id": NEW, "url": BARE}], catalog.canonical), [])
        self.assertIn("canonical URL", url_identity.candidate_identity_errors([
            {"id": OLD, "url": BARE}], catalog.canonical)[0])
        self.assertIn("Duplicate candidate", url_identity.candidate_identity_errors([
            {"id": NEW, "url": BARE}, {"id": NEW, "url": BARE}], catalog.canonical)[0])


class MigrationWWWTests(unittest.TestCase):
    def test_dry_run_merge_receipts_pending_state_and_second_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            editorial, receipt, occurrences = fixture(directory)
            before = snapshot(directory)
            dry = migration.migrate(directory)
            self.assertEqual(snapshot(directory), before)
            self.assertEqual((dry["candidate_rows_before"], dry["candidate_rows_after"]), (2, 1))
            result = migration.migrate(directory, write=True)
            self.assertEqual(result, dry)
            candidate = catalog.read_jsonl(directory / "candidates.jsonl")[0]
            self.assertEqual((candidate["id"], candidate["url"]), (NEW, BARE))
            self.assertEqual(candidate["first_discovered_at"], "2026-01-01T00:00:00Z")
            self.assertEqual(candidate["discovered_in"], occurrences)
            self.assertEqual(catalog.read_jsonl(directory / "primary-evidence.jsonl"),
                             [{**receipt, "id": NEW}])
            current = json.loads((directory / "editorial.json").read_text())
            self.assertEqual(current[0], editorial)
            self.assertEqual(current[1]["id"], "organization:browserbase")
            self.assertFalse(current[2]["editorial_reviewed"])
            self.assertNotIn("reviewed_sha256", current[2])
            self.assertEqual((directory / "exclusions.json").read_bytes(), before["exclusions.json"])
            enrichment = catalog.read_jsonl(directory / "enrichment.jsonl")[0]
            self.assertEqual(enrichment["source_url"], WWW)
            self.assertEqual(enrichment["evidence"], [{"url": WWW, "sha256": "a" * 64}])
            self.assertEqual(enrichment["references"][0], {"target_id": NEW, "url": WWW, "type": "mentions"})
            self.assertEqual(json.loads((directory / "candidate-reviews.json").read_text()), [])
            complete = snapshot(directory)
            self.assertEqual(migration.migrate(directory, write=True)["changed_files"], [])
            self.assertEqual(snapshot(directory), complete)

    def test_conflicts_stop_before_any_file_is_written(self):
        for kind in ("primary", "editorial", "candidate"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                editorial, receipt, _ = fixture(directory)
                if kind == "primary":
                    write(directory, "primary-evidence.jsonl",
                          [receipt, {**receipt, "id": NEW, "sha256": "d" * 64}])
                elif kind == "editorial":
                    write(directory, "editorial.json", [editorial, {**editorial, "url": BARE, "name": "Different"}])
                else:
                    rows = catalog.read_jsonl(directory / "candidates.jsonl")
                    rows[1]["unexpected_fact"] = "conflicts"
                    write(directory, "candidates.jsonl", rows)
                before = snapshot(directory)
                with self.assertRaisesRegex(ValueError, "[Cc]onflicting"):
                    migration.migrate(directory, write=True)
                self.assertEqual(snapshot(directory), before)

    def test_equivalent_duplicate_receipts_can_coalesce(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            _, receipt, _ = fixture(directory)
            write(directory, "primary-evidence.jsonl", [receipt, {**receipt, "id": NEW}])
            migration.migrate(directory, write=True)
            self.assertEqual(catalog.read_jsonl(directory / "primary-evidence.jsonl"), [{**receipt, "id": NEW}])

    def test_report_counts_equivalent_prefix_reviews_as_well_as_self_aliases(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            fixture(directory)
            reviews = json.loads((directory / "candidate-reviews.json").read_text())
            reviews.extend({"url_prefix": url, "decision": "not_a_resource", "reason": "Fixture prefix."}
                           for url in (WWW, BARE))
            write(directory, "candidate-reviews.json", reviews)
            report = migration.migrate(directory, write=True)
            self.assertEqual(report["removed_redundant_candidate_reviews"], 2)
            self.assertEqual(json.loads((directory / "candidate-reviews.json").read_text()),
                             [{"url_prefix": BARE, "decision": "not_a_resource", "reason": "Fixture prefix."}])

    def test_interrupted_write_can_resume_without_losing_the_alias_ledger(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            fixture(directory)
            original_write = migration.atomic_write
            written = []

            def interrupt(path, data):
                if written:
                    raise OSError("simulated interruption")
                original_write(path, data)
                written.append(path.name)

            with mock.patch.object(migration, "atomic_write", side_effect=interrupt):
                with self.assertRaises(OSError):
                    migration.migrate(directory, write=True)
            self.assertEqual(written, ["url-aliases.json"])
            migration.migrate(directory, write=True)
            self.assertEqual(catalog.read_jsonl(directory / "candidates.jsonl")[0]["id"], NEW)
            self.assertEqual(migration.migrate(directory)["changed_files"], [])

    def test_changed_input_stops_before_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            fixture(directory)
            original_plan = migration.plan

            def changed(path):
                result = original_plan(path)
                (directory / "editorial.json").write_text("[]\n")
                return result

            with mock.patch.object(migration, "plan", side_effect=changed):
                with self.assertRaisesRegex(ValueError, "Input changed"):
                    migration.migrate(directory, write=True)
            self.assertFalse((directory / "url-aliases.json").exists())

    def test_retained_scope_identity_requires_explicit_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            fixture(directory)
            write(directory, "exclusions.json", [{"id": OLD, "metadata_sha256": "c" * 64}])
            before = snapshot(directory)
            with self.assertRaisesRegex(ValueError, "explicit reviewed migration"):
                migration.migrate(directory, write=True)
            self.assertEqual(snapshot(directory), before)

    def test_source_build_cannot_silently_overwrite_conflicting_editorial_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            editorial, _, _ = fixture(directory)
            write(directory, "editorial.json", [editorial, {**editorial, "url": BARE}])
            with mock.patch.object(build, "DATA", directory):
                with self.assertRaisesRegex(ValueError, "Duplicate editorial identity"):
                    build.source_records()

    def test_source_build_rejects_a_stale_candidate_before_writing_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            write(directory, "candidates.jsonl", [{"id": OLD, "url": BARE}])
            before = snapshot(directory)
            with mock.patch.object(build, "DATA", directory), \
                    mock.patch.object(build, "source_records", return_value=([], [], [])):
                with self.assertRaisesRegex(ValueError, "canonical URL"):
                    build.build(types.SimpleNamespace(check=False))
            self.assertEqual(snapshot(directory), before)


class LookupWWWTests(unittest.TestCase):
    def test_exact_old_id_returns_unchanged_active_record_but_not_an_unindexed_candidate(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            record = {"id": NEW, "url": WWW, "aliases": [OLD, WWW], "summary": "Preserved"}
            declaration = url_identity.www_declaration(WWW, catalog.canonical)
            pending = url_identity.www_declaration("https://www.perplexity.ai/comet", catalog.canonical)
            write(directory, "catalog.jsonl", [record])
            write(directory, "url-aliases.json", [declaration, pending])
            write(directory, "exclusion-status.json", {"schema_version": 1, "decisions": []})
            payload, code = lookup.read_lookup(OLD, data_dir=directory)
            self.assertEqual((payload, code), (record, 0))
            self.assertEqual(lookup.read_lookup(pending["alias_id"], data_dir=directory)[1],
                             lookup.EXIT_NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
