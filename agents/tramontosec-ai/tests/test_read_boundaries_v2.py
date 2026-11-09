"""Leitores de metadados não inspecionam código nem ultrapassam os limites."""
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from tramontosec.core import make_workspace
from tramontosec.inventory import scan_manifests
from tramontosec.reports import _text, catalog_report, recommendation_markdown, reasoning_markdown


class InventoryBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)

    def write(self, name, value):
        (self.repo / name).write_text(value, encoding='utf-8')

    def test_requirements_names_extras_and_ignored_directives(self):
        self.write('requirements.txt', '# comentário\n-r private.txt\n--index-url SECRET\n'
                   './local\nopenai>=1\nsentence_transformers[extra]>=1\npackage @ local\n')
        self.write('.env', 'anthropic=SECRET')
        self.write('source.py', 'import torch')
        (self.repo / 'nested').mkdir()
        self.write('nested/requirements.txt', 'tensorflow')
        report = scan_manifests(self.repo)
        self.assertEqual(report['manifests_checked'], ['requirements.txt'])
        self.assertEqual({i['dependency'] for i in report['indicators']}, {'openai', 'sentence-transformers'})
        self.assertFalse(report['ai_component_confirmed'])
        self.assertNotIn('SECRET', json.dumps(report))

    def test_toml_project_and_poetry_dependencies_are_only_indicators(self):
        self.write('pyproject.toml', '[project]\ndependencies = ["torch>=2", "qdrant-client"]\n'
                   '[tool.poetry.dependencies]\nollama = "*"\npython = "^3.11"\n')
        report = scan_manifests(self.repo)
        self.assertEqual({i['dependency'] for i in report['indicators']}, {'torch', 'qdrant-client', 'ollama'})
        self.assertFalse(report['ai_component_confirmed'])

    def test_malformed_json_toml_and_wrong_field_types_are_tolerated(self):
        for package, toml in (('{bad', '[bad'), ('[]', 'project = 1'),
                              ('{"dependencies": []}', '[project]\ndependencies = 1')):
            self.write('package.json', package)
            self.write('pyproject.toml', toml)
            self.assertEqual(scan_manifests(self.repo)['indicators'], [])

    def test_files_links_and_large_manifests_are_not_scanned(self):
        self.write('not-a-folder', 'x')
        with self.assertRaises(ValueError):
            scan_manifests(self.repo / 'not-a-folder')
        self.write('package.json', '{"dependencies": {"openai":"*"}}')
        with patch('pathlib.Path.is_symlink', return_value=True):
            self.assertEqual(scan_manifests(self.repo)['manifests_checked'], [])
        with (self.repo / 'package.json').open('wb') as file:
            file.truncate(1_000_001)
        self.assertEqual(scan_manifests(self.repo)['manifests_checked'], [])

    def test_package_field_variants_are_checked_without_dependency_values(self):
        self.write('package.json', json.dumps({'devDependencies': {'langchain': 'SECRET'},
                                              'optionalDependencies': {'openai': 'SECRET'}}))
        report = scan_manifests(self.repo)
        self.assertEqual(len(report['indicators']), 2)
        self.assertNotIn('SECRET', json.dumps(report))


class ReportBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.pdf = self.base / 'synthetic.pdf'
        self.pdf.write_bytes(b'fake pdf metadata')

    def reader(self, pages, encrypted=False):
        return SimpleNamespace(PdfReader=lambda *_a, **_k: SimpleNamespace(
            pages=[SimpleNamespace(extract_text=lambda value=value: value) for value in pages],
            is_encrypted=encrypted))

    def test_optional_pdf_dependency_and_unsupported_formats_have_clear_errors(self):
        with patch.dict('sys.modules', {'pypdf': None}), self.assertRaisesRegex(ValueError, 'Optional'):
            _text(self.pdf)
        other = self.base / 'report.html'
        other.write_text('x')
        with self.assertRaisesRegex(ValueError, 'Only'):
            _text(other)

    def test_pdf_encryption_page_and_file_limits_are_rejected(self):
        for reader in (self.reader(['x'], True), self.reader(['x'] * 201)):
            with patch.dict('sys.modules', {'pypdf': reader}), self.assertRaises(ValueError):
                _text(self.pdf)
        for path, limit in ((self.pdf, 20_000_001), (self.base / 'report.md', 2_000_001)):
            with path.open('wb') as file:
                file.truncate(limit)
            with self.assertRaises(ValueError):
                _text(path)

    def test_pdf_empty_pages_and_text_budget_are_bounded(self):
        with patch.dict('sys.modules', {'pypdf': self.reader([None, 'VULN-01', 'x' * 120_001])}):
            text, fmt = _text(self.pdf)
        self.assertEqual(fmt, 'pdf')
        self.assertIn('VULN-01', text)
        self.assertEqual(len(text), 120_009)
        with patch.dict('sys.modules', {'pypdf': self.reader(['x' * 120_001] * 10)}):
            self.assertEqual(len(_text(self.pdf)[0]), 1_000_000)

    def test_catalog_invalid_scope_and_conflicting_metadata_are_rejected(self):
        ws = self.base / 'ws'
        make_workspace(ws)
        path = self.base / 'report.md'
        path.write_text('VULN-01')
        with self.assertRaises(ValueError):
            catalog_report(ws, 'doc', path, 'unsupported')
        catalog_report(ws, 'doc', path, 'external_assessment')
        with self.assertRaises(ValueError):
            catalog_report(ws, 'doc', path, 'whitebox_assessment')

    def test_model_text_in_report_helpers_is_escaped(self):
        lines = recommendation_markdown({'hypothesis_id': '<img>', 'mitigation': '[unsafe]',
            'validation': '<script>', 'incident_response': '<script>', 'origin': 'llm'})
        lines += reasoning_markdown([{'tool': 'read_evidence', 'reason': 'Conferir',
                                     'model_note': '<script>[unsafe]'}])
        output = '\n'.join(lines)
        self.assertNotIn('<script>', output)
        self.assertIn('&lt;script&gt;', output)
        self.assertIn('sugestão de modelo não verificada', output)
        self.assertIn('nota do modelo (não verificada)', output)
