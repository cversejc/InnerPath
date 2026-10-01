import pytest

from app.services.report_task_service import create_report_task


class TaskDatabase:
    def __init__(self):
        self.added = None
        self.committed = False
        self.refreshed = None

    def add(self, value):
        self.added = value

    async def commit(self):
        self.committed = True

    async def refresh(self, value):
        self.refreshed = value


@pytest.mark.asyncio
async def test_create_report_task_persists_initial_task_state_and_snapshot():
    db = TaskDatabase()
    snapshot = {"schema_version": 2, "context": {"focus_topics": ["career"]}}

    task = await create_report_task(
        db,
        task_id="task-123",
        user_id=7,
        input_snapshot=snapshot,
        retry_count=1,
        retry_of_task_id="task-previous",
    )

    assert db.committed
    assert db.added is task
    assert db.refreshed is task
    assert task.task_id == "task-123"
    assert task.user_id == 7
    assert task.status == "processing"
    assert task.progress == 0
    assert task.input_snapshot == snapshot
    assert task.retry_count == 1
    assert task.retry_of_task_id == "task-previous"
