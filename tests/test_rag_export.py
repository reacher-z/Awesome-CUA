import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from export_rag import documents,encode_documents,build_exports

ROOT=Path(__file__).resolve().parents[1]


class RetrievalExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=[json.loads(line) for line in (ROOT/'data/catalog.jsonl').read_text().splitlines()]
    def test_reviewed_and_complete_exports_preserve_identity_provenance_and_versions(self):
        for all_records in [False,True]:
            output=[json.loads(line) for line in encode_documents(self.rows,all_records).splitlines()]
            expected={r['id']:r for r in self.rows if all_records or r['review_status']=='curated'}
            self.assertEqual(len(output),len(expected));self.assertEqual({r['id'] for r in output},set(expected))
            for doc in output:
                source=expected[doc['id']];meta=doc['metadata'];snapshot=source['details'].get('arxiv_snapshot')
                self.assertEqual(meta['resource_id'],source['id'])
                for field in ['review_status','scope','evidence','licenses','relations','last_verified_at','details','links','authors','identifiers','updated_at']:
                    self.assertEqual(meta[field],source[field])
                self.assertEqual(meta['arxiv_snapshot'],snapshot)
                self.assertIn(source['name'],doc['text'])
                if snapshot and snapshot.get('versioned_url'):self.assertEqual(meta['source_url'],snapshot['versioned_url'])
                if source['review_status']=='metadata_verified':self.assertIn('has no approved editorial annotation',doc['text'])
    def test_changed_annotations_update_fingerprint_without_changing_upsert_id(self):
        row=copy.deepcopy(next(r for r in self.rows if r['review_status']=='curated'))
        original=list(documents([row]))[0]
        row['summary']='Corrected annotation after another primary-source review.'
        changed=list(documents([row]))[0]
        self.assertEqual(original['id'],changed['id'])
        self.assertNotEqual(original['metadata']['record_sha256'],changed['metadata']['record_sha256'])
        self.assertIn(row['summary'],changed['text'])
    def test_duplicate_ids_and_unknown_review_states_cannot_create_partial_exports(self):
        row=copy.deepcopy(self.rows[0])
        with self.assertRaisesRegex(ValueError,'Duplicate'):encode_documents([row,row],True)
        row['review_status']='automatically_approved'
        with self.assertRaisesRegex(ValueError,'Unrecognized'):encode_documents([row],True)
    def test_manifest_matches_actual_bytes_and_rebuild_is_deterministic(self):
        source=(ROOT/'data/catalog.jsonl').read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory);a=build_exports(self.rows,path,source)
            first={item['file']:(path/item['file']).read_bytes() for item in a['exports']}
            b=build_exports(self.rows,path,source)
            self.assertEqual(a,b);self.assertEqual(a['catalog_sha256'],hashlib.sha256(source).hexdigest())
            for item in a['exports']:
                body=(path/item['file']).read_bytes()
                self.assertEqual(body,first[item['file']]);self.assertEqual(item['sha256'],hashlib.sha256(body).hexdigest())
                self.assertEqual(item['records'],len(body.splitlines()))


if __name__=='__main__':unittest.main()
