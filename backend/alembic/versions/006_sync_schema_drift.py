"""Sync database schema with the SQLAlchemy models.

Revision ID: 006
Revises: 005
Create Date: 2026-09-25

The database carried a few leftovers that made ``alembic check`` fail:

* duplicated unique constraints sitting next to the unique indexes the models declare
* the pre-Alembic ``calendar_requests`` table and its ``user_calendars.calendar_request_id`` link
* ``users`` profile columns that no longer exist on the ``User`` model
* ``user_courses.course_id``, which the model indexes but no migration ever created

Primary keys no longer declare ``index=True`` because PostgreSQL already indexes
``*_pkey``, so no extra ``ix_<table>_id`` index is created here.

The legacy columns and table are dropped without data migration: their values are
kept in the ``backend/logs`` dumps taken before this revision, and ``downgrade``
does not restore them.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


#: ``(table, constraint name, columns)`` duplicated next to the model's unique index.
DUPLICATE_UNIQUE_CONSTRAINTS = (
    ("auth_sessions", "auth_sessions_token_hash_key", ("token_hash",)),
    ("staff_invites", "staff_invites_token_hash_key", ("token_hash",)),
    ("service_request_drafts", "service_request_drafts_request_id_key", ("request_id",)),
)

#: Columns that came from pre-Alembic ``create_all`` runs and disappeared from the models.
LEGACY_USER_COLUMNS = (
    "calendar_type",
    "birth_time_precision",
    "current_residence",
    "marital_status",
    "occupation_status",
    "highest_education",
    "mbti",
    "personality_keywords",
    "strengths",
    "limitations",
    "mingli_experience",
    "mingli_attitude",
    "preferred_content_depth",
    "default_usage_scenarios",
    "profile_version",
    "profile_last_confirmed_at",
)

PUBLISHED_INDEX = "uq_user_calendar_current_published"


def _inspector():
    return sa.inspect(op.get_bind())


def _table_names() -> set:
    return set(_inspector().get_table_names())


def _column_names(table: str) -> set:
    return {column["name"] for column in _inspector().get_columns(table)}


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

    if "user_calendars" in tables:
        # The old request link is superseded by user_calendars.request_id (005).
        if "calendar_request_id" in _column_names("user_calendars"):
            for foreign_key in _inspector().get_foreign_keys("user_calendars"):
                if foreign_key.get("constrained_columns") == ["calendar_request_id"] and foreign_key.get("name"):
                    op.drop_constraint(foreign_key["name"], "user_calendars", type_="foreignkey")
            for index in _inspector().get_indexes("user_calendars"):
                if index.get("column_names") == ["calendar_request_id"] and index.get("name"):
                    op.drop_index(index["name"], table_name="user_calendars")
            op.drop_column("user_calendars", "calendar_request_id")

        # 004 created this partial index; the model now declares it so drift checks keep it.
        if PUBLISHED_INDEX not in _index_names("user_calendars"):
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

    if "users" in tables:
        for column in LEGACY_USER_COLUMNS:
            if column in _column_names("users"):
                op.drop_column("users", column)

    if "calendar_requests" in tables:
        op.drop_table("calendar_requests")


def downgrade() -> None:
    """Restore the duplicated unique constraints only.

    The legacy table and columns are deliberately not restored: they predate
    Alembic, and a pre-006 dump is the rollback path for their data.
    """
    tables = _table_names()
    for table, constraint, columns in DUPLICATE_UNIQUE_CONSTRAINTS:
        if table in tables and constraint not in _unique_constraint_names(table):
            op.create_unique_constraint(constraint, table, list(columns))
    if "user_courses" in tables and "ix_user_courses_course_id" in _index_names("user_courses"):
        op.drop_index("ix_user_courses_course_id", table_name="user_courses")
