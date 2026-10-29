import json
import tempfile
import unittest
from pathlib import Path
from tramontosec.core import (
    make_workspace, record_document, import_findings, list_findings,
    verify, review, export_report, _inside_repository, no_sync_roots)


class AuditCoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ws = self.root / 'private'
        make_workspace(self.ws)

    def _load(self):
        sample = self.root / 'findings.json'
        sample.write_text(json.dumps([{
            'project':'Example','identifier':'DEMO-1','title':'Controle de teste',
            'classification':'R','severity':'Baixa','summary':'metadado de teste',
            'source_doc':'DEMO',
            'evidence':[{'repo':'api','path':'src/good.py','start':1,'end':2,'commit':'deadbeef'}]
        }]), encoding='utf-8')
        return import_findings(self.ws,sample)

    def test_import_idempotence(self):
        self.assertEqual(self._load(), (1,0))
        self.assertEqual(self._load(), (0,1))
        self.assertEqual(len(list_findings(self.ws)),1)

    def test_document_hash_and_collision(self):
        path = self.root / 'doc.md'
        path.write_text('# a')
        one=record_document(self.ws,'doc-1',path,'technical_note')
        self.assertEqual(len(one['sha256']),64)
        path.write_text('# b')
        with self.assertRaises(ValueError):
            record_document(self.ws,'doc-1',path,'technical_note')

    def test_verify_only_locations(self):
        self._load()
        repo = self.root / 'repo'; (repo/'src').mkdir(parents=True)
        (repo/'src'/'good.py').write_text('line1\nline2\n')
        checks=verify(self.ws,{'api':repo})
        self.assertEqual(checks[0]['status'],'located')
        self.assertFalse(checks[0]['commit_verified'])
        (repo/'src'/'good.py').write_text('line1\n')
        self.assertEqual(verify(self.ws,{'api':repo})[0]['status'],'unverified')

    def test_path_traversal_rejected(self):
        repo=self.root/'repo';repo.mkdir()
        with self.assertRaises(ValueError):
            _inside_repository(repo,'../outside')
        with self.assertRaises(ValueError):
            _inside_repository(repo,'C:\\Windows\\system.ini')
        with self.assertRaises(ValueError):
            _inside_repository(repo,'/etc/passwd')

    def test_sync_path_rejected(self):
        with self.assertRaises(ValueError):
            no_sync_roots(self.root/'OneDrive'/'audit')

    def test_review_requires_human_ack(self):
        self._load()
        with self.assertRaises(ValueError):
            review(self.ws,'Example:DEMO-1','accepted','Auditor','ok',False)
        review(self.ws,'Example:DEMO-1','in_review','Auditor','pending',False)
        review(self.ws,'Example:DEMO-1','accepted','Auditor','manual review done',True)
        self.assertEqual(list_findings(self.ws)[0]['status'],'accepted')
        exported=export_report(self.ws)
        self.assertIn('REVISTO POR HUMANO',exported.read_text())


if __name__ == '__main__':
    unittest.main()
