"""Real loopback HTTP requests, synthetic projects, no external networking."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from tramontosec.dashboard import LocalServer
from tramontosec.demo import run_demo
from tramontosec.store import create_project, snapshot


class DashboardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.ws = Path(cls.temp.name) / 'ws'
        run_demo(cls.ws, 'demo')
        cls.server = LocalServer(cls.ws, 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=5)
        cls.server.server_close()
        cls.temp.cleanup()

    def request(self, method, path, data=None, headers=None, auth=True):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        h = {'Origin': self.server.origin}
        if auth:
            h.update({'Cookie': f'tramonto_session={self.server.cookie_token}', 'X-CSRF-Token': self.server.csrf_token})
        if data is not None:
            data = json.dumps(data)
            h['Content-Type'] = 'application/json'
        h.update(headers or {})
        try:
            conn.request(method, path, data, h)
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read().decode()
        finally:
            conn.close()

    def test_shell_and_security_headers(self):
        status, headers, body = self.request('GET', '/', auth=False)
        self.assertEqual(status, 200)
        self.assertIn('TramontoSec', body)
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')

    def test_api_requires_session(self):
        self.assertEqual(self.request('GET', '/api/projects', auth=False)[0], 403)
        self.assertEqual(self.request('POST', '/api/session', headers={'X-Local-Token': 'wrong'}, auth=False)[0], 403)
        code, headers, body = self.request('POST', '/api/session', headers={'X-Local-Token': self.server.entry_token}, auth=False)
        self.assertEqual(code, 200)
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        self.assertIn('SameSite=Strict', headers['Set-Cookie'])

    def test_projects_evidence_activities_and_report_from_core(self):
        code, _, body = self.request('GET', '/api/project?project=demo')
        self.assertEqual(code, 200)
        result = json.loads(body)
        self.assertTrue(result['project']['synthetic'])
        self.assertEqual(len(result['tasks']), 3)
        self.assertEqual(len(result['stages']), 5)
        self.assertGreater(len(result['evidence']), 0)
        code, _, content = self.request('GET', '/api/report?project=demo')
        self.assertEqual(code, 200)
        self.assertIn('preliminar', content)

    def test_csrf_dns_rebinding_external_origin_denied(self):
        for headers in ({'X-CSRF-Token': 'bad'}, {'Origin': 'http://external.invalid'}, {'Host': 'external.invalid'}, {'Sec-Fetch-Site': 'cross-site'}):
            self.assertEqual(self.request('POST', '/api/review', {}, headers)[0], 403)

    def test_human_review_requires_ack_then_persists(self):
        key = snapshot(self.ws, 'demo')['hypotheses'][0]['id']
        body = {'project': 'demo', 'id': key, 'decision': 'accepted', 'reviewer': 'Auditor sintético',
                'reason': 'Revisão fictícia independente.', 'ack': False}
        self.assertEqual(self.request('POST', '/api/review', body)[0], 403)
        body['ack'] = True
        self.assertEqual(self.request('POST', '/api/review', body)[0], 200)
        self.assertEqual(snapshot(self.ws, 'demo')['hypotheses'][0]['status'], 'accepted')

    def test_unknown_paths_and_bad_payload(self):
        for path in ('/../../private', '/audit.sqlite3', '/api/shell'):
            self.assertEqual(self.request('GET', path)[0], 404)
        self.assertEqual(self.request('GET', '/api/project?project=../demo')[0], 400)
        self.assertEqual(self.request('POST', '/api/review', {'command': 'shell'})[0], 400)


if __name__ == '__main__':
    unittest.main()
