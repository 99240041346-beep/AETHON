from aethon.evidence import Evidence
from aethon.web_verification import VerificationStatus, WebVerificationGate


def test_gate_supports_acceptable_evidence():
    result = WebVerificationGate().verify([Evidence(title='A', url='https://example.com', trust_score=0.65)])
    assert result.status == VerificationStatus.SUPPORTED


def test_gate_blocks_insufficient_evidence():
    result = WebVerificationGate(minimum_trust=0.8).verify([Evidence(title='A', url='https://example.com', trust_score=0.65)])
    assert result.status == VerificationStatus.INSUFFICIENT_EVIDENCE


def test_gate_marks_conflicting_claims():
    evidence = [Evidence(title='A', url='https://a.example', trust_score=0.8), Evidence(title='B', url='https://b.example', trust_score=0.8)]
    result = WebVerificationGate().verify(evidence, [('fact', 'one'), ('fact', 'two')])
    assert result.status == VerificationStatus.CONFLICTED
    assert result.conflicts[0]['subject'] == 'fact'
