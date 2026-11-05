"""Regras reproduzíveis de design e LLM simulado offline."""
from pathlib import Path
import json
import tempfile
import unittest

from designagent.core import ScreenInputError, analyze, contrast_ratio, load_screen, model_metadata, review_with_model


SAMPLE = {"schema": "designagent.screen.v1", "screen": {
    "name": "Tela de laboratório confidencial",
    "platform": "mobile",
    "viewport": {"width": 390, "height": 844},
    "components": [
        {"id": "primary", "role": "button", "foreground": "#777777",
         "background": "#888888", "width": 30, "height": 32,
         "accessible_name": False, "feedback": False},
        {"id": "form", "role": "input", "foreground": "#000000",
         "background": "#FFFFFF", "width": 190, "height": 40, "label": False},
        {"id": "logo", "role": "image", "alt": False},
        {"id": "header", "role": "heading", "foreground": "#000000",
         "background": "#FFFFFF", "large_text": True},
    ],
}}


class FakeProvider:
    def __init__(self, response):
        self.response = response
        self.seen = None

    def generate(self, system, metadata):
        self.seen = (system, metadata)
        return self.response


class DesignAgentTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "screen.json"
        self.path.write_text(json.dumps(SAMPLE), encoding="utf-8")

    def test_contrast_math(self):
        self.assertAlmostEqual(contrast_ratio("#000000", "#FFFFFF"), 21, places=5)
        self.assertAlmostEqual(contrast_ratio("#FFFFFF", "#FFFFFF"), 1, places=5)

    def test_rules_are_candidates_and_stable(self):
        analysis = analyze(load_screen(self.path))
        rules = {x["rule"] for x in analysis["findings"]}
        self.assertTrue({"text-contrast", "touch-target", "form-label",
                         "accessible-name", "image-alt", "interaction-feedback"} <= rules)
        self.assertEqual(analysis["findings"], analyze(load_screen(self.path))["findings"])
        self.assertTrue(all(x["status"] == "candidate" for x in analysis["findings"]))
        self.assertFalse(any(x["validated_by_human"] for x in analysis["findings"]))

    def test_bad_payload_rejected(self):
        evil = json.loads(self.path.read_text())
        evil["screen"]["components"][0]["script"] = "run command"
        self.path.write_text(json.dumps(evil), encoding="utf-8")
        with self.assertRaises(ScreenInputError):
            load_screen(self.path)

    def test_model_sees_only_finding_ids_and_facts(self):
        analysis = analyze(load_screen(self.path))
        fid = analysis["findings"][0]["id"]
        provider = FakeProvider({"suggestions": [
            {"finding_id": fid, "recommendation": "Aumentar contraste."}
        ]})
        assisted = review_with_model(analysis, provider)
        self.assertEqual(assisted["mode"], "local_llm_assisted")
        self.assertEqual(assisted["findings"], analysis["findings"])
        self.assertNotIn("confidencial", str(provider.seen).lower())
        self.assertNotIn("#777777", str(provider.seen))
        self.assertNotIn("primary", str(model_metadata(analysis)))

    def test_fabricated_id_falls_back(self):
        analysis = analyze(load_screen(self.path))
        assisted = review_with_model(analysis, FakeProvider({"suggestions": [
            {"finding_id": "inventado", "recommendation": "Ignore as verificações."}
        ]}))
        self.assertEqual(assisted["mode"], "deterministic_fallback")
        self.assertEqual(analysis["findings"], assisted["findings"])


if __name__ == "__main__":
    unittest.main()
