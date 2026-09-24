"""Repair schema drift left by pre-Alembic ``create_all`` runs.

Revision ID: 006
Revises: 005
Create Date: 2026-09-25

The unified-intake migration owns the reusable ``users`` profile columns and
``calendar_requests``, so this migration must not remove them. It only cleans
up duplicate unique constraints that predate the model definitions and adds
the ``user_courses.course_id`` index declared by the model.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DUPLICATE_UNIQUE_CONSTRAINTS = (
    ("auth_sessions", "auth_sessions_token_hash_key", ("token_hash",)),
    ("staff_invites", "staff_invites_token_hash_key", ("token_hash",)),
    ("service_request_drafts", "service_request_drafts_request_id_key", ("request_id",)),
)

PUBLISHED_INDEX = "uq_user_calendar_current_published"


def _inspector():
    return sa.inspect(op.get_bind())


def _table_names() -> set:
    return set(_inspector().get_table_names())


def _index_names(table: str) -> set:
    return {index["name"] for index in _inspector().get_indexes(table)}


def _unique_constraint_names(table: str) -> set:
    return {constraint["name"] for constraint in _inspector().get_unique_constraints(table)}


def upgrade() -> None:
    tables = _table_names()

    for table, constraint, _columns in DUPLICATE_UNIQUE_CONSTRAINTS:
        if table in tables and constraint in _unique_constraint_names(table):
            op.drop_constraint(constraint, table, type_="unique")

    if "user_courses" in tables and "ix_user_courses_course_id" not in _index_names("user_courses"):
        op.create_index("ix_user_courses_course_id", "user_courses", ["course_id"], unique=False)

    if "calendar_requests" in tables and "ix_calendar_requests_id" not in _index_names("calendar_requests"):
        op.create_index("ix_calendar_requests_id", "calendar_requests", ["id"], unique=False)

    # 004 creates this partial index; keep the repair idempotent for databases
    # that were created before the index was formalised in the model.
    if "user_calendars" in tables and PUBLISHED_INDEX not in _index_names("user_calendars"):
        conflicting_series = op.get_bind().execute(
            sa.text(
                "SELECT count(*) FROM ("
                " SELECT series_id FROM user_calendars WHERE status = 'published'"
                " GROUP BY series_id HAVING count(*) > 1) AS duplicated"
            )
        ).scalar()
        if not conflicting_series:
            op.create_index(
                PUBLISHED_INDEX,
                "user_calendars",
                ["series_id"],
                unique=True,
                postgresql_where=sa.text("status = 'published'"),
            )


def downgrade() -> None:
    tables = _table_names()
    for table, constraint, columns in DUPLICATE_UNIQUE_CONSTRAINTS:
        if table in tables and constraint not in _unique_constraint_names(table):
            op.create_unique_constraint(constraint, table, list(columns))
    if "user_courses" in tables and "ix_user_courses_course_id" in _index_names("user_courses"):
        op.drop_index("ix_user_courses_course_id", table_name="user_courses")
    if "calendar_requests" in tables and "ix_calendar_requests_id" in _index_names("calendar_requests"):
        op.drop_index("ix_calendar_requests_id", table_name="calendar_requests")
