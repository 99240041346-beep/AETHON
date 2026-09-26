from app.attachment_store import MAX_ATTACHMENT_BYTES, attachment_context, create_attachment, get_attachment, retrieve_attachment_context


def test_text_attachment_is_owner_scoped_and_context_is_bounded():
    item = create_attachment(
        owner_id="owner-a",
        filename="notes.txt",
        media_type="text/plain",
        raw=b"hello AETHON",
    )

    assert item.kind == "text"
    assert item.text == "hello AETHON"
    assert get_attachment(item.attachment_id, "owner-a") is not None
    assert get_attachment(item.attachment_id, "owner-b") is None

    context, names = attachment_context([item.attachment_id], "owner-a")
    assert "hello AETHON" in context
    assert names == ["notes.txt"]


def test_attachment_size_and_type_are_rejected():
    try:
        create_attachment(owner_id="owner", filename="x.exe", media_type="application/octet-stream", raw=b"x")
    except ValueError as exc:
        assert "unsupported" in str(exc)
    else:
        raise AssertionError("unsupported type was accepted")

    try:
        create_attachment(owner_id="owner", filename="large.txt", media_type="text/plain", raw=b"x" * (MAX_ATTACHMENT_BYTES + 1))
    except ValueError as exc:
        assert "2 MiB" in str(exc)
    else:
        raise AssertionError("oversized attachment was accepted")


def test_attachment_retrieval_returns_relevant_bounded_chunks():
    item = create_attachment(
        owner_id="rag-owner",
        filename="research.txt",
        media_type="text/plain",
        raw=("python is useful for data analysis. " * 120).encode(),
    )
    result = retrieve_attachment_context([item.attachment_id], "rag-owner", "data analysis", max_chunks=2, chunk_chars=300)
    assert "data analysis" in result
    assert result.count("[research.txt#") <= 2


def test_attachment_retrieval_is_owner_scoped():
    item = create_attachment(
        owner_id="rag-owner-a",
        filename="private.txt",
        media_type="text/plain",
        raw=b"secret project content",
    )
    assert retrieve_attachment_context([item.attachment_id], "rag-owner-b", "secret") == ""
