"""Synthetic regression tests for SQLite lifecycle; no external systems."""
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from tramontosec.core import make_workspace, open_db, list_findings
from tramontosec.local_ai import local_suggestion


class SQLiteLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ws = Path(self.tmp.name) / "private"
        make_workspace(self.ws)

    def test_closed_after_context_even_if_reference_retained(self):
        with open_db(self.ws) as conn:
            self.assertEqual(conn.execute("SELECT 1").fetchone()[0], 1)
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_commits_and_preserves_row_factory(self):
        with open_db(self.ws) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS lifecycle(v TEXT)")
            conn.execute("INSERT INTO lifecycle(v) VALUES (?)", ("ok",))
            self.assertIs(conn.row_factory, sqlite3.Row)
            self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        with open_db(self.ws) as check:
            self.assertEqual(check.execute("SELECT v FROM lifecycle").fetchone()[0], "ok")

    def test_rollback_on_error_and_close(self):
        with self.assertRaisesRegex(RuntimeError, "revert"):
            with open_db(self.ws) as conn:
                conn.execute("INSERT INTO events(event_at,finding_key,verb,details) VALUES (?,?,?,?)", ("test", "fake", "x", "y"))
                raise RuntimeError("revert")
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")
        with open_db(self.ws) as check:
            self.assertEqual(check.execute("SELECT COUNT(*) FROM events").fetchone()[0], 0)

    def test_keyboard_interrupt_also_closes(self):
        with self.assertRaises(KeyboardInterrupt):
            with open_db(self.ws) as conn:
                raise KeyboardInterrupt
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_fk_error_on_transaction_exit_closes(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with open_db(self.ws) as conn:
                conn.execute("INSERT INTO report_catalog(doc_id,scope,format,ids_json,parsed_at,note) VALUES (?,?,?,?,?,?)", ("missing", "x", "y", "[]", "x", ""))
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_read_function_no_handles_remain(self):
        self.assertEqual(list_findings(self.ws), [])
        (self.ws / "audit.sqlite3").rename(self.ws / "renamed.sqlite3")
        (self.ws / "renamed.sqlite3").rename(self.ws / "audit.sqlite3")

    def test_missing_finding_never_calls_model(self):
        with patch("urllib.request.build_opener", side_effect=AssertionError("network")):
            with self.assertRaises(KeyError):
                local_suggestion(self.ws, "missing", "tiny", True)
        with open_db(self.ws) as conn:
            self.assertEqual(conn.execute("SELECT 1").fetchone()[0], 1)

    def test_cursor_explicit_close(self):
        with open_db(self.ws) as conn:
            with closing(conn.execute("SELECT * FROM documents")) as cursor:
                self.assertIsNone(cursor.fetchone())
        with self.assertRaises(sqlite3.ProgrammingError):
            cursor.fetchone()

    def test_connection_closes_if_pragma_setup_fails(self):
        class FailingConnection(sqlite3.Connection):
            def execute(self, sql, parameters=()):
                if sql.startswith("PRAGMA foreign_keys"):
                    raise ValueError("pragma unavailable")
                return super().execute(sql, parameters)
        original_connect = sqlite3.connect
        with patch("tramontosec.core.sqlite3.connect", side_effect=lambda *a, **kw: original_connect(*a, factory=FailingConnection, **kw)):
            with self.assertRaisesRegex(ValueError, "pragma unavailable"):
                with open_db(self.ws):
                    pass
