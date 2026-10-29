"""Offline security and regression tests; no production services or cloud calls."""
import json
from contextlib import closing
import os
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tramontosec.core import make_workspace, import_findings, verify, export_report
from tramontosec.git_readonly import inspect_repo, compare_commit
from tramontosec.scanners import import_scan, list_alerts, triage_alert, parse_redacted
from tramontosec.inventory import scan_manifests
from tramontosec.reports import catalog_report
from tramontosec.benchmark import run_benchmark
from tramontosec.local_ai import local_suggestion


class V02Test(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.ws = self.root/'private'; make_workspace(self.ws)

    def _repo(self):
        repo = self.root/'repo'; repo.mkdir()
        (repo/'src').mkdir(); (repo/'src'/'service.py').write_text('one\ntwo\n',encoding='utf-8')
        env={**os.environ, 'GIT_CONFIG_NOSYSTEM':'1', 'GIT_CONFIG_GLOBAL':os.devnull}
        def git(*xs):
            return subprocess.check_output(['git','-C',str(repo),*xs], stderr=subprocess.DEVNULL,
                                           env=env, text=True).strip()
        git('init', '-q'); git('add','src/service.py')
        git('-c','user.name=Test','-c','user.email=test@example.invalid', 'commit','-qm','example')
        return repo, git('rev-parse','HEAD')

    def _finding(self, commit):
        x=[{'project':'Lab','identifier':'LAB-1','title':'Test', 'classification':'I',
            'severity':'Indeterminada','summary':'fixture', 'source_doc':'synthetic',
            'evidence':[{'repo':'api', 'path':'src/service.py','start':1,'end':2,'commit':commit}]}]
        p=self.root/'f.json';p.write_text(json.dumps(x));import_findings(self.ws,p)

    def test_clean_git_commit_and_dirty_git(self):
        repo, head=self._repo()
        self._finding(head)
        result=verify(self.ws,{'api':repo})[0]
        self.assertTrue(result['baseline_valid'])
        self.assertTrue(result['commit_verified'])
        self.assertFalse(result['semantics_verified'])
        (repo/'untracked.txt').write_text('local change')
        result=verify(self.ws,{'api':repo})[0]
        self.assertTrue(result['commit_verified'])
        self.assertFalse(result['baseline_valid'])
        self.assertFalse(result['worktree_clean'])

    def test_wrong_commit_even_when_lines_exist(self):
        repo,head=self._repo(); self._finding('0'*40)
        x=verify(self.ws,{'api':repo})[0]
        self.assertEqual(x['status'],'located')
        self.assertFalse(x['commit_verified'])
        self.assertFalse(x['baseline_valid'])

    def test_git_disables_fsmonitor_and_does_not_run_hooks(self):
        repo, head=self._repo()
        hooks=repo/'.git'/'hooks'; hooks.mkdir(exist_ok=True)
        sentinel=self.root/'sentinel.txt'
        (hooks/'post-checkout').write_text('#!/bin/sh\ntouch '+str(sentinel)+'\n')
        (hooks/'post-checkout').chmod(0o755)
        self.assertEqual(inspect_repo(repo)['head'],head)
        self.assertFalse(sentinel.exists())
        self.assertFalse(compare_commit('0'*40,inspect_repo(repo))['commit_verified'])

    def test_scanner_dedup_secret_excluded_and_manual_triage(self):
        raw={'results':[{'check_id':'rule.test','path':'src/service.py','start':{'line':2},
                         'extra':{'severity':'WARNING','lines':'REAL_PASSWORD=EXAMPLE_SECRET'}},
                        {'check_id':'rule.test','path':'src/service.py','start':{'line':2}}]}
        f=self.root/'semgrep.json'; f.write_text(json.dumps(raw))
        with self.assertRaises(ValueError):import_scan(self.ws,'Lab','semgrep',f,False)
        res=import_scan(self.ws,'Lab','semgrep',f,True)
        self.assertEqual((res['raw_count'],res['unique_count'],res['added']), (2,1,1))
        self.assertTrue(import_scan(self.ws,'Lab','semgrep',f,True)['already_imported'])
        a=list_alerts(self.ws)[0]
        self.assertNotIn('REAL_PASSWORD', json.dumps(a))
        triage_alert(self.ws,a['alert_id'],'false_positive','Tester','Sintético e não alcançável')
        self.assertEqual(list_alerts(self.ws)[0]['triage'],'false_positive')
        self.assertIn('false_positive',export_report(self.ws).read_text())

    def test_gitleaks_secret_never_persisted(self):
        p=self.root/'gitleaks.json'
        p.write_text(json.dumps([{'RuleID':'generic','File':'src/x.py','StartLine':7,
                                  'Secret':'FAKE_DONT_STORE_ME','Match':'FAKE_DONT_STORE_ME'}]))
        import_scan(self.ws,'Lab','gitleaks',p,True)
        with closing(sqlite3.connect(self.ws/'audit.sqlite3')) as db:
            data=str(db.execute('SELECT * FROM alerts').fetchall())
        self.assertNotIn('FAKE_DONT_STORE_ME',data)

    def test_trivy_parsing_and_zizmor_parsing(self):
        tr={'Results':[{'Target':'package-lock.json','Vulnerabilities':[
            {'VulnerabilityID':'CVE-2099-1234','PkgName':'library','Severity':'HIGH'}]}]}
        zz={'findings':[{'ident':'unpinned-uses', 'severity':'low',
                         'locations':[{'path':'.github/workflows/ci.yml','line':10}]}]}
        t=self.root/'t.json'; t.write_text(json.dumps(tr))
        z=self.root/'z.json'; z.write_text(json.dumps(zz))
        self.assertEqual(parse_redacted('trivy',t)[1][0]['rule_id'],'CVE-2099-1234')
        self.assertEqual(parse_redacted('zizmor',z)[1][0]['rule_id'],'unpinned-uses')

    def test_catalog_keeps_distinct_assessment_scopes(self):
        f1=self.root/'old.md'; f1.write_text('# VULN-01\n# VULN-01\n# VULN-02')
        f2=self.root/'new.md'; f2.write_text('# A-01\n# A-02\n# CA-01')
        a=catalog_report(self.ws,'old',f1,'external_assessment','09/2026')
        b=catalog_report(self.ws,'new',f2,'whitebox_assessment','10/2026')
        self.assertEqual(a['historical_identifiers'],['VULN-01','VULN-02'])
        self.assertEqual(b['count'],3)
        self.assertIn('external_assessment',export_report(self.ws).read_text())

    def test_inventory_only_indicators_not_proof(self):
        repo=self.root/'manifest'; repo.mkdir()
        (repo/'package.json').write_text(json.dumps({'dependencies':{'@langchain/core':'1.0','react':'19.0'}}))
        report=scan_manifests(repo)
        self.assertEqual(report['indicators'][0]['dependency'],'@langchain/core')
        self.assertFalse(report['ai_component_confirmed'])
        (repo/'package.json').write_text(json.dumps({'dependencies':{'react':'19.0'}}))
        self.assertEqual(scan_manifests(repo)['indicators'],[])

    def test_benchmark_synthetic_only(self):
        x=run_benchmark()
        self.assertEqual(x['cases'],5)
        self.assertEqual(x['fp'],0)
        self.assertIn('NOT',x['warning'])

    def test_local_llm_needs_consent_and_cannot_approve(self):
        self._finding('a'*40)
        with self.assertRaises(ValueError):
            local_suggestion(self.ws,'Lab:LAB-1','tiny',False)
        # Never connect to a real Ollama server in automated tests.
        with patch('urllib.request.build_opener',side_effect=AssertionError('network called')):
            with self.assertRaises(AssertionError):
                local_suggestion(self.ws,'Lab:LAB-1','tiny',True)

    def test_existing_workspace_can_migrate(self):
        # Emulate an old workspace containing v0.1 data without new tables.
        with closing(sqlite3.connect(self.ws/'audit.sqlite3')) as db:
            with db:
                db.execute('DROP TABLE scanner_runs');db.execute('DROP TABLE alerts')
                db.execute('DROP TABLE report_catalog')
        make_workspace(self.ws)
        with closing(sqlite3.connect(self.ws/'audit.sqlite3')) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],2)
            self.assertTrue(db.execute("SELECT name FROM sqlite_master WHERE name='alerts'").fetchone())

if __name__=='__main__': unittest.main()

class CorrelationTest(unittest.TestCase):
    def test_only_file_and_line_candidates(self):
        from tramontosec.correlation import correlate_candidates
        from tramontosec.core import make_workspace, import_findings
        from tramontosec.scanners import import_scan
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); ws=root/'w';make_workspace(ws)
            f=root/'findings.json'
            f.write_text(json.dumps([{'project':'Lab','identifier':'X-1','title':'Fixture',
              'classification':'I','severity':'Baixa','summary':'Synthetic', 'source_doc':'fixture',
              'evidence':[{'repo':'api','path':'src/a.py','start':3,'end':4,'commit':'0'*40}]}]))
            import_findings(ws,f)
            scanner=root/'scanner.json'
            scanner.write_text(json.dumps({'results':[
              {'check_id':'ruleA','path':'src/a.py','start':{'line':3}},
              {'check_id':'ruleB','path':'src/b.py','start':{'line':3}},
              {'check_id':'ruleC','path':'src/a.py','start':{'line':80}}]}))
            import_scan(ws,'Lab','semgrep',scanner,True)
            pairs=correlate_candidates(ws,'Lab')
            self.assertEqual(len(pairs),1)
            self.assertEqual(pairs[0]['rule_id'],'ruleA')
            self.assertIn('human',pairs[0]['interpretation'])

class SyncRootsTest(unittest.TestCase):
    def test_onedrive_org_folder_disallowed(self):
        from tramontosec.core import no_sync_roots
        with self.assertRaises(ValueError):
            no_sync_roots(Path('/tmp/OneDrive - Universidade/confidential'))
