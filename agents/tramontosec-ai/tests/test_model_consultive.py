"""O parecer do modelo não escolhe ferramentas nem altera hipóteses."""
import unittest

from tramontosec.agents import Specialist
from tramontosec.contracts import Profile, TaskMessage


class ConsultiveModelTest(unittest.TestCase):
    def test_model_cannot_reduce_or_modify_rule_findings(self):
        msg = TaskMessage('t1', 'lab', Profile.RED, 'Exame sintético', 'execucao',
                          ('e1',), ('analyze_recon',))
        evidence = [{'id': 'e1', 'kind': 'recon', 'payload': {'assets': [
            {'asset': 'lab.example.invalid', 'services': ['database'], 'controls': []}]}}]
        class FakeProvider:
            name = 'fake'
            def assess(self, message, metadata):
                return {'summary': 'Parecer não verificado.', 'uncertainties': [],
                        'evidence_ids': ['e1'], 'proposed_tools': []}
        baseline = Specialist(Profile.RED).run(msg, evidence, [])
        assisted = Specialist(Profile.RED).run(msg, evidence, [], FakeProvider())
        self.assertEqual(baseline.hypotheses, assisted.hypotheses)
        self.assertEqual(assisted.mode, 'local_llm_assisted')
        self.assertEqual(assisted.model_assessment['summary'], 'Parecer não verificado')


if __name__ == '__main__':
    unittest.main()
