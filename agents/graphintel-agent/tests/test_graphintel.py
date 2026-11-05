"""Testes offline com grafo fictício, sem subprocessos ou Ollama."""
from pathlib import Path
import json
import tempfile
import unittest

from graphintel.core import GraphInputError, analyze, load_graph, model_metadata, review_with_model


GRAPH = {
    "graph": {"schema_version": "1"},
    "nodes": [
        {"id": "api", "label": "API", "source_file": "src/private-api.py"},
        {"id": "service", "label": "Service", "source_file": "src/service.py"},
        {"id": "db", "label": "Database", "source_file": "src/database.py"},
        {"id": "unused", "label": "Other", "source_file": "src/other.py"},
    ],
    "links": [
        {"source": "api", "target": "service", "relation": "calls", "confidence": "EXTRACTED"},
        {"source": "service", "target": "db", "relation": "depends_on", "confidence": "INFERRED"},
        {"source": "unused", "target": "db", "relation": "notes", "confidence": "EXTRACTED"},
    ],
}


class FakeProvider:
    def __init__(self, response):
        self.response = response
        self.seen = None

    def generate(self, system, metadata):
        self.seen = (system, metadata)
        return self.response


class GraphIntelTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "graph.json"
        self.path.write_text(json.dumps(GRAPH), encoding="utf-8")

    def test_reverse_impact_and_non_dependency(self):
        graph = load_graph(self.path)
        report = analyze(graph, "db", depth=3)
        self.assertEqual([x["id"] for x in report["impact_candidates"]], ["service", "api"])
        self.assertEqual([x["distance"] for x in report["impact_candidates"]], [1, 2])
        self.assertEqual(report["impact_candidates"][0]["confidence"], "INFERRED")
        self.assertEqual(report["status"], "candidate")

    def test_bad_edges_are_rejected(self):
        wrong = dict(GRAPH)
        wrong["links"] = [{"source": "api", "target": "ghost"}]
        self.path.write_text(json.dumps(wrong), encoding="utf-8")
        with self.assertRaises(GraphInputError):
            load_graph(self.path)

    def test_rejects_duplicate_and_large_input(self):
        wrong = dict(GRAPH)
        wrong["nodes"] = [GRAPH["nodes"][0], GRAPH["nodes"][0]]
        self.path.write_text(json.dumps(wrong), encoding="utf-8")
        with self.assertRaises(GraphInputError):
            load_graph(self.path)
        self.path.write_bytes(b"x" * 8_000_001)
        with self.assertRaises(GraphInputError):
            load_graph(self.path)

    def test_model_receives_only_aliases_and_counts(self):
        report = analyze(load_graph(self.path), "db")
        provider = FakeProvider({"observations": ["Revise ligações inferidas."]})
        assisted = review_with_model(report, provider)
        self.assertEqual(assisted["mode"], "local_llm_assisted")
        self.assertEqual(assisted["impact_candidates"], report["impact_candidates"])
        self.assertNotIn("private-api", str(provider.seen))
        self.assertNotIn("service.py", str(provider.seen))
        self.assertNotIn("src/", str(provider.seen))
        self.assertNotIn("db", str(model_metadata(report)))

    def test_untrusted_reply_does_not_change_results(self):
        report = analyze(load_graph(self.path), "db")
        assisted = review_with_model(report, FakeProvider({"observations": ["x" * 400]}))
        self.assertEqual(assisted["mode"], "deterministic_fallback")
        self.assertEqual(report["impact_candidates"], assisted["impact_candidates"])


if __name__ == "__main__":
    unittest.main()
