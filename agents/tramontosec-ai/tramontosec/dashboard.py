"""Optional loopback-only HTTP view. All audit logic stays in the core services."""
from __future__ import annotations

from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, HTTPServer
import hmac
import json
from pathlib import Path
import secrets
import sqlite3
from urllib.parse import parse_qs, urlsplit

from .contracts import identifier
from .orchestrator import report_markdown, review_hypothesis
from .store import list_projects, snapshot

WEB = Path(__file__).parent / 'web'
CSP = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"


class LocalServer(HTTPServer):
    allow_reuse_address = True

    def __init__(self, workspace: Path, port: int):
        self.workspace = workspace
        self.entry_token = secrets.token_urlsafe(32)
        self.cookie_token = secrets.token_urlsafe(32)
        self.csrf_token = secrets.token_urlsafe(32)
        super().__init__(('127.0.0.1', port), Handler)

    @property
    def origin(self):
        return f'http://127.0.0.1:{self.server_port}'


class Handler(BaseHTTPRequestHandler):
    server_version = 'TramontoSecLocal/0.3'
    sys_version = ''

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, format, *args):
        pass  # Never log tokens, evidence URLs, project names or local paths.

    def send(self, status: int, content: bytes, mime='application/json; charset=utf-8', cookie=False):
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', CSP)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        if cookie:
            self.send_header('Set-Cookie', f'tramonto_session={self.server.cookie_token}; HttpOnly; SameSite=Strict; Path=/')
        self.end_headers()
        self.wfile.write(content)

    def json(self, status, obj, cookie=False):
        self.send(status, json.dumps(obj, ensure_ascii=False).encode('utf-8'), cookie=cookie)

    def boundary(self):
        if self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}':
            raise PermissionError('Host inválido. Use o endereço local exibido pela CLI.')
        origin = self.headers.get('Origin')
        if origin and origin != self.server.origin:
            raise PermissionError('Origem externa bloqueada.')
        if self.headers.get('Sec-Fetch-Site') in ('cross-site', 'same-site'):
            raise PermissionError('Acesso fora da origem local bloqueado.')

    def authenticated(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
            value = cookie['tramonto_session'].value if 'tramonto_session' in cookie else ''
        except CookieError:
            value = ''
        if not hmac.compare_digest(value, self.server.cookie_token):
            raise PermissionError('Abra o link de sessão exibido na CLI para acessar os dados.')

    def do_GET(self):
        try:
            self.boundary()
            url = urlsplit(self.path)
            static = {'/': ('index.html', 'text/html; charset=utf-8'),
                      '/app.css': ('app.css', 'text/css; charset=utf-8'),
                      '/app.js': ('app.js', 'text/javascript; charset=utf-8')}
            if url.path in static:
                filename, mime = static[url.path]
                self.send(200, (WEB / filename).read_bytes(), mime)
                return
            self.authenticated()
            if url.path == '/api/projects':
                self.json(200, {'projects': list_projects(self.server.workspace), 'csrf': self.server.csrf_token})
            elif url.path in ('/api/project', '/api/report'):
                project = identifier(parse_qs(url.query).get('project', [''])[0])
                if url.path == '/api/project':
                    self.json(200, snapshot(self.server.workspace, project))
                else:
                    self.send(200, report_markdown(self.server.workspace, project).encode(), 'text/markdown; charset=utf-8')
            else:
                self.json(404, {'error': 'Recurso não encontrado.'})
        except PermissionError as exc:
            self.json(403, {'error': str(exc)})
        except (ValueError, KeyError, OSError, sqlite3.Error):
            self.json(400, {'error': 'Não foi possível consultar este recurso local.'})

    def do_POST(self):
        try:
            self.boundary()
            if self.headers.get('Origin') != self.server.origin:
                raise PermissionError('Decisões exigem a origem exata do dashboard.')
            if self.path == '/api/session':
                if not hmac.compare_digest(self.headers.get('X-Local-Token', ''), self.server.entry_token):
                    raise PermissionError('Link de sessão inválido.')
                self.json(200, {'ready': True, 'csrf': self.server.csrf_token}, cookie=True)
                return
            self.authenticated()
            if not hmac.compare_digest(self.headers.get('X-CSRF-Token', ''), self.server.csrf_token):
                raise PermissionError('Confirmação de origem ausente. Reabra o dashboard.')
            if self.path != '/api/review':
                self.json(404, {'error': 'Ação não disponível.'})
                return
            if self.headers.get('Content-Type') != 'application/json':
                raise ValueError('JSON obrigatório.')
            length = int(self.headers.get('Content-Length', '0'))
            if not 1 <= length <= 16_000 or self.headers.get('Transfer-Encoding'):
                raise ValueError('Entrada ausente ou acima do limite.')
            body = self.rfile.read(length)
            data = json.loads(body)
            if not isinstance(data, dict) or set(data) != {'project', 'id', 'decision', 'reviewer', 'reason', 'ack'}:
                raise ValueError('Contrato de revisão inválido.')
            if type(data['ack']) is not bool:
                raise ValueError('Confirmação deve ser booleana.')
            review_hypothesis(self.server.workspace, identifier(data['project']),
                              data['id'], data['decision'], data['reviewer'], data['reason'], data['ack'])
            self.json(200, {'saved': True})
        except PermissionError as exc:
            self.json(403, {'error': str(exc)})
        except (ValueError, KeyError, TypeError, OSError, sqlite3.Error, RecursionError):
            self.json(400, {'error': 'Revisão inválida. Confira projeto, hipótese, decisão e justificativa.'})


def serve(workspace: Path, port: int = 8765):
    from .core import no_sync_roots
    no_sync_roots(workspace)
    if not 1 <= port <= 65535:
        raise ValueError('Porta deve estar entre 1 e 65535.')
    with LocalServer(workspace, port) as server:
        print('Dashboard local. Abra este link privado nesta máquina:')
        print(f'{server.origin}/#session={server.entry_token}', flush=True)
        print('Ctrl+C para encerrar. A CLI funciona sem navegador.', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
