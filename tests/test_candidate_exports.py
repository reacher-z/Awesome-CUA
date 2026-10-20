"""Offline candidate exports preserve an independent, unapproved observation corpus."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import export_candidates as export
import scan_github_candidates as scan
from test_github_candidate_scan import repo, page, response, Timer


def fixture(directory, *, description='A public interface research project.'):
    root = Path(directory).resolve()
    (root / 'data').mkdir()
    for name in scan.INPUTS:
        (root / 'data' / name).write_text('' if name.endswith('.jsonl') else '[]\n')
    timer = Timer()
    api_rows = [repo(7, 'example/old-name'), repo(8, description=description,
                owner={'email': 'private-fixture@example.invalid'}, permissions={'admin': True},
                authorization='fixture-secret-not-for-export')]
    responses = iter([response(page(api_rows)), response(page([repo(7, 'example/new-name')]))])
    state, _ = scan.run_scan(root, root / '.cache/pilot', max_requests=2, max_seconds=180,
                            existing_budget=0, topics=['browser-automation', 'computer-use'],
                            created_after='2024-01-01', created_before='2024-01-04',
                            fetcher=lambda url, timeout: next(responses), clock=timer.clock,
                            sleep=timer.sleep, now=timer.now)
    return state, root / '.cache/pilot/raw'


class CandidateExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.state, self.raw = fixture(self.root)
        self.ledger = export.encoded(self.state)
        self.catalog = b'{"id":"github:example/reviewed","review_status":"curated"}\n'

    def build(self, state=None):
        return export.build_candidate_export(export.encoded(state) if state is not None else self.ledger,
                                             self.raw, self.catalog)

    def test_numeric_dedup_complete_receipts_and_independent_context(self):
        body, manifest = self.build()
        rows = export.validate_candidate_export(body, manifest, catalog_bytes=self.catalog)
        self.assertEqual([r['repository_id'] for r in rows], [7, 8])
        self.assertEqual(manifest['count'], {'value': 2, 'unit': 'repositories'})
        self.assertEqual(rows[0]['known_names'], ['example/new-name', 'example/old-name'])
        self.assertEqual(len(rows[0]['evidence']), 2)
        self.assertEqual(rows[0]['metadata_receipt_id'], rows[0]['evidence'][-1]['receipt_id'])
        self.assertEqual({r['review_status'] for r in rows}, {'candidate'})
        self.assertEqual({r['scope'] for r in rows}, {'relevance_pending'})
        self.assertEqual(manifest['source_ledger_sha256'], hashlib.sha256(self.ledger).hexdigest())
        self.assertEqual(manifest['active_catalog_context']['sha256'], hashlib.sha256(self.catalog).hexdigest())
        self.assertNotEqual(manifest['observation_snapshot_sha256'], manifest['active_catalog_context']['sha256'])
        self.assertNotIn(b'private-fixture@', body)
        self.assertNotIn(b'fixture-secret', body)
        self.assertNotIn(b'permissions', body)
        self.assertTrue(all('owner' not in row for row in rows))
        self.assertEqual((body, manifest), self.build())

    def test_complete_public_schema_contracts(self):
        import jsonschema
        body, manifest = self.build()
        checker = jsonschema.FormatChecker()
        record_schema = json.loads((ROOT / 'schemas' / export.SCHEMAS[0]).read_text())
        manifest_schema = json.loads((ROOT / 'schemas' / export.SCHEMAS[1]).read_text())
        jsonschema.Draft202012Validator.check_schema(record_schema)
        jsonschema.Draft202012Validator.check_schema(manifest_schema)
        for line in body.splitlines(): jsonschema.Draft202012Validator(record_schema, format_checker=checker).validate(json.loads(line))
        jsonschema.Draft202012Validator(manifest_schema, format_checker=checker).validate(manifest)

    def test_true_empty_response_exports_zero_observations_without_inventing_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); (root / 'data').mkdir()
            for name in scan.INPUTS: (root / 'data' / name).write_text('' if name.endswith('.jsonl') else '[]\n')
            timer = Timer()
            state, _ = scan.run_scan(root, root / '.cache/pilot', max_requests=1, existing_budget=0,
                topics=['computer-use'], created_after='2024-01-01', created_before='2024-01-04',
                fetcher=lambda url, timeout: response(page([])), clock=timer.clock, sleep=timer.sleep, now=timer.now)
            body, manifest = export.build_candidate_export(export.encoded(state), root / '.cache/pilot/raw', self.catalog)
            self.assertEqual(body, b'')
            self.assertEqual(manifest['count']['value'], 0)
            self.assertIsNone(manifest['observed_from'])
            self.assertEqual(manifest['supporting_primary_bodies'], 0)

    def test_source_metadata_cannot_be_edited_while_retaining_the_receipt(self):
        for mutate in [lambda s: s['records']['github-repository:7'].update(description='Invented annotation'),
                       lambda s: s['records']['github-repository:7'].update(last_observed_at='2026-10-19T00:00:00Z'),
                       lambda s: s['records']['github-repository:7']['known_names'].append('invented/alias')]:
            state = copy.deepcopy(self.state); mutate(state)
            with self.assertRaises(ValueError): self.build(state)

    def test_primary_body_tampering_and_missing_body_are_rejected(self):
        path = next(self.raw.glob('*.body'))
        original = path.read_bytes(); path.write_bytes(original + b' ')
        with self.assertRaises(ValueError): self.build()
        path.unlink()
        with self.assertRaises(ValueError): self.build()

    def test_occurrences_and_urls_must_match_the_request(self):
        state = copy.deepcopy(self.state)
        state['records']['github-repository:7']['occurrences'][0]['position'] = 2
        with self.assertRaises(ValueError): self.build(state)
        state = copy.deepcopy(self.state)
        state['receipts'][0]['source_url'] = 'https://name:secret@api.github.com/search/repositories'
        with self.assertRaises(ValueError): self.build(state)
        state = copy.deepcopy(self.state)
        state['receipts'][0]['accepted_repository_ids'].remove(8)
        with self.assertRaises(ValueError): self.build(state)

    def test_private_fork_and_changed_identity_are_rejected_after_honest_hash_update(self):
        for change in ({'private': True}, {'fork': True}, {'full_name': 'another/repository'}):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                state, raw = fixture(Path(directory))
                receipt = state['receipts'][0]
                path = raw / (receipt['response_sha256'] + '.body')
                value = json.loads(path.read_bytes()); value['items'][0].update(change)
                body = export.encoded(value); sha = export.digest(body)
                receipt.update(response_sha256=sha, response_bytes=len(body)); (raw / (sha + '.body')).write_bytes(body)
                with self.assertRaises(ValueError): export.build_candidate_export(export.encoded(state), raw, self.catalog)

    def test_sensitive_descriptions_are_omitted_with_id_field_only_report(self):
        cases = [('ghp_' + 'Z' * 36, 'credential_shaped_string'),
                 ('Saved at /Users/example/private/project', 'private_home_path'),
                 ('See https://alice:example-password@example.org', 'url_userinfo'),
                 ('file:///Users/private-fixture/notes.txt', 'private_home_path'),
                 ('file:///%55sers/private-fixture/notes.txt', 'private_home_path'),
                 ('file:///C:/Users/private-fixture/notes.txt', 'private_home_path'),
                 ('file://alice:example-password@localhost/document.txt', 'url_userinfo')]
        for description, reason in cases:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as directory:
                state, raw = fixture(Path(directory), description=description)
                body, manifest = export.build_candidate_export(export.encoded(state), raw, self.catalog)
                rows = [json.loads(line) for line in body.splitlines()]
                self.assertIsNone(rows[1]['source_description'])
                self.assertEqual(manifest['count']['value'], 2)
                self.assertEqual(manifest['privacy']['omitted_fields'], [{'id': 'github-repository:8', 'field': 'source_description', 'reason': reason}])
                self.assertNotIn(description.encode(), body + export.encoded(manifest))
        self.assertEqual(export.privacy_findings('Research by Alice Smith: https://github.com/example/repository'), [])
        self.assertEqual(export.privacy_findings('https://example.org/home/documentation/start'), [])

    def test_honest_export_fingerprints_do_not_approve_or_forge_counts(self):
        body, manifest = self.build()
        for change in ({'review_status': 'curated'}, {'repository_id': True}, {'scope': 'core'}, {'authorization': 'not-public'}):
            rows = [json.loads(line) for line in body.splitlines()]; rows[0].update(change)
            rows[0]['record_sha256'] = export.digest(export.encoded({k: v for k, v in rows[0].items() if k != 'record_sha256'}))
            new_body = b''.join(export.encoded(row) for row in rows); m = copy.deepcopy(manifest)
            m['observation_snapshot_sha256'] = export.digest(new_body); m['export'].update(sha256=export.digest(new_body), bytes=len(new_body))
            with self.assertRaises(ValueError): export.validate_candidate_export(new_body, m)
        for mutate in [lambda m: m['count'].update(value=999), lambda m: m.update(schema_version=True),
                       lambda m: m['scan']['runs'][0].update(accepted_metadata_rows=999),
                       lambda m: m['input_fingerprints'][0]['files'].update({'private/local': {'bytes': 0, 'sha256': 'a' * 64}}),
                       lambda m: m['scan'].update(global_completeness_established=True),
                       lambda m: m['privacy'].update(headers={'Authorization': 'not-public'})]:
            m = copy.deepcopy(manifest); mutate(m)
            with self.assertRaises(ValueError): export.validate_candidate_export(body, m)

    def test_output_pair_rolls_back_after_second_replace_failure(self):
        body, manifest = self.build()
        destination = self.root / 'output'
        for previous in (False, True):
            with self.subTest(previous=previous):
                destination.mkdir(exist_ok=True)
                for name in export.FILES: (destination / name).unlink(missing_ok=True)
                if previous: export.write_pair(destination, b'previous-records', {'previous': True})
                old = {name: (destination / name).read_bytes() for name in export.FILES} if previous else {}
                replace = export.os.replace; calls = 0
                def fail_second(source, target):
                    nonlocal calls
                    calls += 1
                    if calls == 2: raise OSError('injected publication failure')
                    return replace(source, target)
                with mock.patch.object(export.os, 'replace', side_effect=fail_second), self.assertRaises(OSError):
                    export.write_pair(destination, body, manifest)
                self.assertEqual({path.name: path.read_bytes() for path in destination.iterdir()}, old)

    def test_no_symlinks_or_parent_escape(self):
        body, manifest = self.build()
        linked = self.root / 'linked'; linked.symlink_to(self.raw, target_is_directory=True)
        with self.assertRaises(ValueError): export.build_candidate_export(self.ledger, linked, self.catalog)
        with self.assertRaises(ValueError): export.write_pair(self.root / '..' / 'escape', body, manifest)
        output = self.root / 'output'; output.mkdir(); (output / export.RECORD_FILE).symlink_to(self.root / 'elsewhere')
        with self.assertRaises(ValueError): export.write_pair(output, body, manifest)

    def test_optional_publication_rebinds_only_catalog_context_and_cleans_its_files(self):
        body, manifest = self.build(); source = self.root / 'source'; destination = self.root / 'site'
        export.write_pair(source, body, manifest)
        other = b'{"id":"github:another/resource"}\n'
        copied = export.copy_public_candidates(source, destination / 'downloads', other)
        self.assertEqual((destination / 'downloads' / export.RECORD_FILE).read_bytes(), body)
        self.assertEqual(copied['source_ledger_sha256'], manifest['source_ledger_sha256'])
        self.assertEqual(copied['input_fingerprints'], manifest['input_fingerprints'])
        self.assertNotEqual(copied['active_catalog_context'], manifest['active_catalog_context'])
        self.assertEqual(json.loads((source / export.MANIFEST_FILE).read_bytes()), manifest)
        (destination / 'downloads/keep.json').write_text('{}')
        (destination / 'schemas').mkdir()
        for name in export.SCHEMAS: (destination / 'schemas' / name).write_text('{}')
        absent = self.root / 'absent-build'; (absent / 'downloads').mkdir(parents=True)
        (absent / 'downloads/manifest.json').write_text(json.dumps({'schema_version': 1, 'artifacts': []}))
        export.apply_candidate_publication(export.candidate_publication_plan(absent, destination))
        self.assertEqual(list((destination / 'downloads').iterdir()), [destination / 'downloads/keep.json'])
        self.assertEqual(list((destination / 'schemas').iterdir()), [])

    def test_unlisted_build_orphans_cannot_resurrect_an_old_public_pair(self):
        body, manifest = self.build(); site = self.root / 'old-site'; build = self.root / 'new-build'
        export.write_pair(site / 'downloads', body, manifest)
        (site / 'schemas').mkdir()
        for name in export.SCHEMAS: (site / 'schemas' / name).write_bytes(b'old-schema')
        (build / 'downloads').mkdir(parents=True); (build / 'schemas').mkdir()
        (build / 'downloads/manifest.json').write_text(json.dumps({'schema_version': 1, 'artifacts': []}))
        (build / 'downloads' / export.RECORD_FILE).write_bytes(b'orphan-not-authorized-by-manifest')
        (build / 'schemas' / export.SCHEMAS[0]).write_bytes(b'orphan-schema')
        plan = export.candidate_publication_plan(build, site)
        shutil.copytree(build, site, dirs_exist_ok=True,
                        ignore=lambda folder, names: export.candidate_copy_ignores(build, folder, names))
        export.apply_candidate_publication(plan)
        self.assertTrue(all(not (site / relative).exists() for relative in export.PUBLIC_PATHS))
        partial = {'schema_version': 1, 'artifacts': [{'path': '/downloads/' + export.RECORD_FILE}]}
        (build / 'downloads/manifest.json').write_text(json.dumps(partial))
        with self.assertRaises(ValueError): export.candidate_publication_plan(build, site)

    def test_data_hub_separates_candidate_observations_from_active_and_rag(self):
        import test_data_hub
        from data_hub import build_download_manifest, data_hub_body
        helper = test_data_hub.DataHubTests('test_manifest_uses_actual_bytes_fingerprints_units_and_distinct_scopes')
        helper.setUp(); self.addCleanup(helper.doCleanups)
        helper.destination = helper.destination.resolve()
        body, manifest = self.build(); manifest['active_catalog_context'] = export.catalog_context(helper.catalog_bytes)
        export.write_pair(helper.destination / 'downloads', body, manifest)
        for schema in export.SCHEMAS: shutil.copy2(ROOT / 'schemas' / schema, helper.destination / 'schemas' / schema)
        download = build_download_manifest(helper.destination, helper.rows, helper.catalog_bytes)
        by_id = {item['id']: item for item in download['artifacts']}
        self.assertEqual(by_id['github-candidates']['count'], {'value': 2, 'unit': 'repositories'})
        self.assertEqual(by_id['github-candidates']['group'], 'provenance')
        self.assertEqual(by_id['github-candidates']['scope'], 'candidate-observations')
        self.assertEqual(by_id['catalog-jsonl']['count']['value'], 3)
        self.assertEqual(by_id['rag-reviewed']['count']['value'], 2)
        self.assertNotIn(b'github-repository:', (helper.destination / 'downloads/rag-all-records.jsonl').read_bytes())
        self.assertIn('Unreviewed candidates', data_hub_body(download))
        target = self.root / 'publication'
        plan = export.candidate_publication_plan(helper.destination, target)
        export.apply_candidate_publication(plan)
        for relative in export.PUBLIC_PATHS:
            self.assertEqual((target / relative).read_bytes(), (helper.destination / relative).read_bytes())
        (helper.destination / 'downloads' / export.RECORD_FILE).write_bytes(body + b'{}\n')
        with self.assertRaises(ValueError): build_download_manifest(helper.destination, helper.rows, helper.catalog_bytes)

    def test_optional_candidate_bundle_is_complete_without_changing_active_populations(self):
        import test_data_release_package
        from data_hub import build_download_manifest
        from package_data_release import package_release, ZIP_NAME
        root = self.root / 'release-fixture'; site, rows = test_data_release_package.make_release_fixture(root)
        body, manifest = self.build(); catalog_bytes = (site / 'downloads/catalog.jsonl').read_bytes()
        manifest['active_catalog_context'] = export.catalog_context(catalog_bytes)
        export.write_pair(site / 'downloads', body, manifest)
        for name in export.SCHEMAS:
            shutil.copy2(ROOT / 'schemas' / name, site / 'schemas' / name)
            shutil.copy2(ROOT / 'schemas' / name, root / 'schemas' / name)
        build_download_manifest(site, rows, catalog_bytes)
        result = package_release(site, root / 'release', source_commit='a' * 40,
                                 source_ref='refs/heads/candidate-preview', repo_root=root)
        self.assertEqual(result['population_counts']['active']['value'], 3)
        self.assertEqual(next(f for f in result['files'] if f['path'] == 'downloads/' + export.RECORD_FILE)['count'],
                         {'value': 2, 'unit': 'repositories'})
        self.assertIn('separate, unreviewed population', result['validation_boundary'])
        self.assertNotIn('candidate populations are not included', result['validation_boundary'])
        with zipfile.ZipFile(root / 'release' / ZIP_NAME) as archive:
            for relative in export.PUBLIC_PATHS:
                self.assertEqual(archive.namelist().count(relative), 1)
                self.assertEqual(archive.read(relative), (site / relative).read_bytes())
            self.assertIn('candidate/relevance_pending', archive.read('AGENTS.md').decode())
            self.assertIn('their own snapshot', archive.read('README.md').decode())


if __name__ == '__main__':
    unittest.main()
