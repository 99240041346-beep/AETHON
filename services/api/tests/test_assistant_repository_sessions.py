from __future__ import annotations

import pytest

from app.assistant_repository import AssistantRepository


def fresh_repo() -> AssistantRepository:
    AssistantRepository._memory_sessions.clear()
    AssistantRepository._memory_messages.clear()
    return AssistantRepository(database_url="")


def test_session_lifecycle_and_owner_isolation():
    repo = fresh_repo()
    repo.ensure_session("s1", "owner-a", "en-IN", "project-1")
    repo.add_message("s1", "owner-a", "user", "hello", "en-IN")

    assert repo.session("s1", "owner-a")["project_id"] == "project-1"
    assert repo.history("s1", "owner-a")[0]["content"] == "hello"
    assert repo.session("s1", "owner-b") is None
    assert repo.history("s1", "owner-b") == []

    with pytest.raises(PermissionError):
        repo.ensure_session("s1", "owner-b", "en-IN")
    with pytest.raises(PermissionError):
        repo.add_message("s1", "owner-b", "user", "should fail", "en-IN")


def test_rename_search_and_archive_visibility():
    repo = fresh_repo()
    repo.ensure_session("s1", "owner-a", "en-IN")
    repo.ensure_session("s2", "owner-a", "en-IN")
    repo.ensure_session("s3", "owner-b", "en-IN")
    assert repo.rename_session("s1", "owner-a", "Project Alpha") is True
    assert repo.rename_session("s3", "owner-a", "Nope") is False

    found = repo.search_sessions("owner-a", "alpha")
    assert [item["session_id"] for item in found] == ["s1"]

    assert repo.archive_session("s1", "owner-a") is True
    assert repo.sessions("owner-a") == [] or all(item["session_id"] != "s1" for item in repo.sessions("owner-a"))
    assert [item["session_id"] for item in repo.sessions("owner-a", include_archived=True)] == ["s1", "s2"]


def test_permanent_delete_is_owner_scoped():
    repo = fresh_repo()
    repo.ensure_session("s1", "owner-a", "en-IN")
    repo.add_message("s1", "owner-a", "user", "delete me", "en-IN")

    assert repo.delete_session("s1", "owner-b") is False
    assert repo.session("s1", "owner-a") is not None
    assert repo.delete_session("s1", "owner-a") is True
    assert repo.session("s1", "owner-a") is None
    assert repo.history("s1", "owner-a") == []
