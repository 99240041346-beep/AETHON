import pytest

from aethon.embeddings import DisabledEmbeddingProvider, EmbeddingError, OpenAICompatibleEmbeddingProvider


def test_disabled_embedding_is_explicit():
    provider = DisabledEmbeddingProvider()
    with pytest.raises(EmbeddingError):
        provider.embed('hello')


def test_openai_embedding_rejects_empty_text():
    provider = OpenAICompatibleEmbeddingProvider('https://example.invalid/v1', 'embed', 'test', dimension=3)
    with pytest.raises(EmbeddingError):
        provider.embed('')
