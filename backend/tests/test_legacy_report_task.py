import pytest

from app.tasks import report_tasks


def test_legacy_celery_report_task_is_rejected_and_marked_retired(monkeypatch):
    retired_task_ids = []

    async def mark_retired(task_id):
        retired_task_ids.append(task_id)

    monkeypatch.setattr(report_tasks, "_mark_legacy_task_retired", mark_retired)
    report_tasks.generate_report_task.push_request(id="legacy-task-7")
    try:
        with pytest.raises(RuntimeError, match="旧版直接生成报告任务已停用"):
            report_tasks.generate_report_task.run(21815, {"name": "legacy"})
    finally:
        report_tasks.generate_report_task.pop_request()

    assert retired_task_ids == ["legacy-task-7"]
