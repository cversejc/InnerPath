"""Correct unstarted report steps to the three-step mingli responsibility."""

import json
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(sa.text("""
        SELECT t.id, t.step_key, t.required_capability, t.assignee_id,
               t.config_snapshot, w.report_case_id,
               r.assigned_mingli_consultant_id
        FROM step_tasks t
        JOIN workflow_instances w ON w.id = t.workflow_instance_id
        JOIN workflow_versions v ON v.id = w.workflow_version_id
        JOIN report_cases c ON c.id = w.report_case_id
        JOIN service_requests r ON r.id = c.service_request_id
        WHERE v.workflow_key = 'report.production'
          AND c.status IN ('ACTIVE', 'BLOCKED')
          AND w.status IN ('RUNNING', 'SUSPENDED')
          AND t.step_key IN ('S1', 'S2', 'S3')
          AND t.status IN ('PENDING', 'READY') AND t.started_at IS NULL
          AND t.required_capability = 'psychology'
    """)).mappings().all()
    for row in rows:
        change = {
            "migration": "018", "reason": "first_three_steps_owned_by_mingli",
            "previous_capability": row["required_capability"],
            "previous_assignee_id": row["assignee_id"],
            "required_capability": "mingli",
            "assignee_id": row["assigned_mingli_consultant_id"],
        }
        config = row["config_snapshot"] or {}
        if isinstance(config, str):
            config = json.loads(config)
        config = {**config, "ownership_correction": change}
        connection.execute(sa.text("""
            UPDATE step_tasks SET required_capability = 'mingli',
                assignee_id = :assignee_id, config_snapshot = :config, updated_at = :now
            WHERE id = :id
        """), {"id": row["id"], "assignee_id": row["assigned_mingli_consultant_id"],
               "config": json.dumps(config), "now": datetime.utcnow()})
        connection.execute(sa.text("""
            INSERT INTO audit_logs (action, resource_type, resource_id, details, created_at, updated_at)
            VALUES ('workflow.step.ownership.correct', 'report_case', :case_id, :details, :now, :now)
        """), {"case_id": str(row["report_case_id"]),
               "details": json.dumps({"step_key": row["step_key"], **change}),
               "now": datetime.utcnow()})


def downgrade() -> None:
    # Ownership corrections are audited business decisions; do not undo them
    # after consultants may already have started work under the corrected owner.
    pass
