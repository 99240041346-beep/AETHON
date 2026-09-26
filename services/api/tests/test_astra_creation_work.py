from aethon.creation_service import CreationService
from aethon.work_manager import WorkManager


def test_creation_service_bounds_code_and_documents():
    service = CreationService()
    assert service.markdown_document("Title", "Body").kind == "markdown"
    assert service.code_artifact("python", "print(1)").metadata["language"] == "python"


def test_work_manager_enforces_task_transitions_and_automation_bounds():
    manager = WorkManager()
    task = manager.create_task("build feature", "owner")
    task.transition("running")
    task.transition("completed")
    assert task.status == "completed"
    automation = manager.schedule("run checks", "owner", 3600)
    assert automation.interval_seconds == 3600
