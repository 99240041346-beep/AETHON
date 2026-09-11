from __future__ import annotations

from uuid import uuid4

import pytest

from app.assistant_repository import AssistantRepository


def test_session_lifecycle_and_search_is_owner_scoped() -> None:
    repo = AssistantRepository(database_url="")
    owner_a = "owner-a"
    owner_b = "owner-b"
    session_id = str(uuid4())

    repo.ensure_session(session_id, owner_a, "en-US", "project-a")
    repo.add_message(session_id, owner_a, "user", "Build AETHON", "en-US")

    assert repo.session(session_id, owner_a)["owner_id"] == owner_a
    assert repo.session(session_id, owner_b) is None
    assert repo.history(session_id, owner_b) == []

    assert repo.rename_session(session_id, owner_a, "AETHON Build") is True
    assert repo.search_sessions(owner_a, "aethon")[0]["title"] == "AETHON Build"
    assert repo.search_sessions(owner_b, "aethon") == []

    assert repo.archive_session(session_id, owner_a) is True
    assert repo.sessions(owner_a) == []
    assert repo.sessions(owner_a, include_archived=True)[0]["archived_at"] is not None

    assert repo.delete_session(session_id, owner_b) is False
    assert repo.delete_session(session_id, owner_a) is True
    assert repo.session(session_id, owner_a) is None


def test_cross_owner_existing_session_cannot_be_mutated() -> None:
    repo = AssistantRepository(database_url="")
    session_id = str(uuid4())
    repo.ensure_session(session_id, "owner-a", "en-US")

    with pytest.raises(PermissionError):
        repo.ensure_session(session_id, "owner-b", "en-US")
    with pytest.raises(PermissionError):
        repo.add_message(session_id, "owner-b", "user", "not mine", "en-US")


def test_search_treats_like_metacharacters_as_literal() -> None:
    repo = AssistantRepository(database_url="")
    session_id = str(uuid4())
    repo.ensure_session(session_id, "owner-a", "en-US")
    repo.rename_session(session_id, "owner-a", "100% complete")

    assert repo.search_sessions("owner-a", "100%")
    assert repo.search_sessions("owner-a", "100_") == []
