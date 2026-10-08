from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.audit.context import AuditContext
from app.domains.audit.service import record_audit
from app.domains.workflow.service import (
    assign_step,
    complete_step,
    create_workflow_draft,
    publish_workflow_version,
    reopen_step,
    return_to_step,
    start_step,
)


async def _audit_step_action(
    db: AsyncSession,
    actor_id: int,
    case_id: int,
    action: str,
    step_key: str,
    audit_context: Optional[AuditContext],
    details: Optional[dict[str, Any]] = None,
) -> None:
    await record_audit(
        db,
        actor_id,
        f"workflow.step.{action}",
        "report_case",
        str(case_id),
        details={"step_key": step_key, **(details or {})},
        audit_context=audit_context,
    )


async def start_case_step(
    db: AsyncSession,
    actor_id: int,
    case_id: int,
    step_key: str,
    audit_context: Optional[AuditContext] = None,
):
    task = await start_step(db, case_id, step_key)
    await _audit_step_action(db, actor_id, case_id, "start", step_key, audit_context)
    await db.commit()
    return task


async def complete_case_step(
    db: AsyncSession,
    actor_id: int,
    case_id: int,
    step_key: str,
    result_json: Optional[dict[str, Any]],
    audit_context: Optional[AuditContext] = None,
    *,
    final_gate_verified: bool = False,
    commit: bool = True,
):
    task = await complete_step(
        db,
        case_id,
        step_key,
        result_json=result_json,
        final_gate_verified=final_gate_verified,
    )
    await _audit_step_action(db, actor_id, case_id, "complete", step_key, audit_context)
    if commit:
        await db.commit()
    return task


async def return_case_step(
    db: AsyncSession,
    actor_id: int,
    case_id: int,
    step_key: str,
    target_step_key: str,
    reason: str,
    audit_context: Optional[AuditContext] = None,
):
    task = await return_to_step(db, case_id, step_key, target_step_key, reason)
    await _audit_step_action(
        db,
        actor_id,
        case_id,
        "return",
        step_key,
        audit_context,
        {"target_step_key": target_step_key, "reason": reason},
    )
    await db.commit()
    return task


async def reopen_case_step(
    db: AsyncSession,
    actor_id: int,
    case_id: int,
    step_key: str,
    audit_context: Optional[AuditContext] = None,
):
    task = await reopen_step(db, case_id, step_key)
    await _audit_step_action(db, actor_id, case_id, "reopen", step_key, audit_context)
    await db.commit()
    return task


async def assign_case_step(
    db: AsyncSession,
    actor_id: int,
    case_id: int,
    step_key: str,
    assignee_id: Optional[int],
    audit_context: Optional[AuditContext] = None,
    *,
    force: bool = False,
):
    task = await assign_step(db, case_id, step_key, assignee_id, force=force)
    await _audit_step_action(
        db,
        actor_id,
        case_id,
        "assign",
        step_key,
        audit_context,
        {"assignee_id": assignee_id},
    )
    await db.commit()
    return task


async def create_workflow_version(
    db: AsyncSession,
    actor_id: int,
    workflow_key: str,
    name: str,
    definition_json: dict[str, Any],
):
    version = await create_workflow_draft(
        db, workflow_key, name, definition_json, created_by=actor_id
    )
    await db.commit()
    await db.refresh(version)
    return version


async def publish_workflow(db: AsyncSession, actor_id: int, version_id: int):
    version = await publish_workflow_version(db, version_id, published_by=actor_id)
    await db.commit()
    await db.refresh(version)
    return version
