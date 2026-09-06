from aethon.evidence import Evidence, detect_conflicts, deduplicate_evidence, source_trust_score


def test_source_trust_score():
    assert source_trust_score('https://example.gov/report') > source_trust_score('https://example.com/report')


def test_evidence_normalization_and_deduplication():
    a = Evidence(title='A', url='https://Example.com/path/')
    b = Evidence(title='B', url='https://example.com/path')
    assert a.normalized_url() == b.normalized_url()
    assert len(deduplicate_evidence([a, b])) == 1


def test_content_hash_is_stable():
    evidence = Evidence(title='A', url='https://example.com').with_content('hello')
    assert len(evidence.content_hash) == 64


def test_conflicts_require_distinct_values():
    assert detect_conflicts([('temperature', '20 C'), ('temperature', '21 C')])
    assert detect_conflicts([('temperature', '20 C'), ('temperature', '20 C')]) == []
