"""Regressão: pontos iniciais de arquivos ocultos não podem ser descartados."""
import unittest

from tramontosec.correlation import _same_file


class CorrelationPathTest(unittest.TestCase):
    def test_hidden_files_remain_distinct(self):
        self.assertFalse(_same_file('.env', 'env'))
        self.assertFalse(_same_file('.github/a.yml', 'github/a.yml'))

    def test_relative_directory_prefix(self):
        self.assertTrue(_same_file('./src/a.py', 'src/a.py'))
        self.assertTrue(_same_file('././src/a.py', 'src/a.py'))
        self.assertTrue(_same_file(r'.\src\a.py', 'src/a.py'))


if __name__ == '__main__':
    unittest.main()
