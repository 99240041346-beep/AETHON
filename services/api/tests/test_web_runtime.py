from aethon.schemas import Task
from aethon.verification import BasicVerifier
from aethon.web_runtime import WebAwareVerifier


def test_web_aware_verifier_uses_url_trust_default():
    verifier = WebAwareVerifier(BasicVerifier())
    result = verifier.verify('research', {
        'answer': 'supported',
        'evidence': [{'title': 'Official', 'url': 'https://example.gov/report'}],
        'claims': [('fact', 'one')],
    })
    assert result.ok is True
    assert result.evidence['web_verification']['status'] == 'SUPPORTED'


def test_web_aware_verifier_rejects_conflicting_claims():
    verifier = WebAwareVerifier(BasicVerifier())
    result = verifier.verify('research', {
        'answer': 'uncertain',
        'evidence': [
            {'title': 'A', 'url': 'https://a.example.com/a'},
            {'title': 'B', 'url': 'https://b.example.com/b'},
        ],
        'claims': [('fact', 'one'), ('fact', 'two')],
    })
    assert result.ok is False
    assert result.evidence['web_verification']['status'] == 'CONFLICTED'


def test_web_aware_verifier_preserves_normal_tasks():
    result = WebAwareVerifier(BasicVerifier()).verify('hello', 'ordinary model output')
    assert result.ok is True
