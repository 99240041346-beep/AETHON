from aethon.evidence_synthesis import EvidenceRecord, EvidenceSynthesizer


def test_supported_claim_is_grounded():
    evidence = [EvidenceRecord("s1", "https://example.com", "Python release", "Python 3.14 was released", 0.9)]
    result = EvidenceSynthesizer().synthesize(["Python 3.14 was released"], evidence)
    assert result.claims[0].supported is True
    assert result.claims[0].source_ids == ("s1",)
    assert not result.limitations


def test_unsupported_claim_is_not_presented_as_fact():
    evidence = [EvidenceRecord("s1", "https://example.com", "Python release", "Python 3.14 was released", 0.9)]
    result = EvidenceSynthesizer().synthesize(["Rust 9 was released"], evidence)
    assert result.claims[0].supported is False
    assert result.answer == ""
    assert result.limitations


def test_non_http_source_is_rejected():
    evidence = [EvidenceRecord("bad", "file:///secret", "Secret", "Python 3.14 was released", 1.0)]
    result = EvidenceSynthesizer().synthesize(["Python 3.14 was released"], evidence)
    assert result.claims[0].supported is False
    assert "No valid HTTP(S)" in result.limitations[0]
