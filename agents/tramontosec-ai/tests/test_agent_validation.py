"""Validação offline de propostas e referências."""
import unittest
from tramontosec.agent_validation import InvalidProposal, validate_model_proposals
from tramontosec.contracts import Profile, TaskMessage
from tramontosec.policy import allowed_tools


def msg():
    return TaskMessage('t', 'lab', Profile.RED, 'Escopo fictício', 'execucao',
                       ('e1',), allowed_tools(Profile.RED))


EVIDENCE = [{'id': 'e1', 'kind': 'recon', 'payload': {'assets': [
    {'asset': 'lab.example.invalid', 'services': ['http'], 'controls': []}
]}}]


class ValidationTest(unittest.TestCase):
    def suggestion(self):
        return {'asset_alias': 'asset-1', 'service': 'http', 'evidence_ids': ['e1'],
                'severity': 'Média', 'title': 'Revisar alcance HTTP',
                'uncertainty': 'Requer verificação'}

    def test_red_candidate_is_derived_and_unverified(self):
        result = validate_model_proposals(msg(), EVIDENCE, [],
                                          {'hypotheses': [self.suggestion()], 'recommendations': []})
        candidate = result['hypotheses'][0]
        self.assertEqual(candidate['origin'], 'llm')
        self.assertEqual(candidate['evidence'], ['e1'])
        self.assertIn('não verificada', candidate['uncertainty'])

    def test_reject_invented_evidence_and_severity(self):
        for field, value in [('evidence_ids', ['unknown']), ('severity', 'Supercrítica'),
                             ('title', '<script>alert(1)</script>')]:
            proposal = self.suggestion()
            proposal[field] = value
            with self.subTest(field=field), self.assertRaises(InvalidProposal):
                validate_model_proposals(msg(), EVIDENCE, [],
                                         {'hypotheses': [proposal], 'recommendations': []})


if __name__ == '__main__':
    unittest.main()
