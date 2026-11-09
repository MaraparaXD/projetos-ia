"""Metadados e páginas públicas devem concordar sobre a versão em desenvolvimento."""
from pathlib import Path
import tomllib
import unittest
from tramontosec import __version__


class ReleaseDocsTest(unittest.TestCase):
    def test_version_consistency_and_development_status(self):
        metadata = tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))['project']
        self.assertEqual(metadata['version'], __version__)
        self.assertEqual(__version__, '0.5.0')
        self.assertIn('Development Status :: 3 - Alpha', metadata['classifiers'])
        self.assertEqual(metadata['dependencies'], [])
        for name in ('README.md', 'CHANGELOG.md', 'ARCHITECTURE.md', 'SECURITY.md', 'docs/VALIDATION.md'):
            content = Path(name).read_text(encoding='utf-8')
            self.assertIn(__version__, content, name)
            self.assertIn('desenvolvimento', content.lower(), name)
        self.assertIn('EM DESENVOLVIMENTO', Path('../../README.md').read_text(encoding='utf-8'))
