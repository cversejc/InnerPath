"""Remove booking and course tables from the active schema.

Revision ID: 008
Revises: 007
Create Date: 2026-10-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    for table in ("user_courses", "courses", "bookings"):
        if table in tables:
            op.drop_table(table)


def downgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cover_image", sa.String(length=255), nullable=True),
        sa.Column("price", sa.DECIMAL(10, 2), nullable=False),
        sa.Column("original_price", sa.DECIMAL(10, 2), nullable=True),
        sa.Column("total_lessons", sa.Integer(), nullable=False),
        sa.Column("duration_hours", sa.DECIMAL(5, 1), nullable=True),
        sa.Column("modules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "user_courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("completed_lessons", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_percentage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_lesson_id", sa.Integer(), nullable=True),
        sa.Column("purchase_price", sa.DECIMAL(10, 2), nullable=False),
        sa.Column("payment_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("enrolled_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "course_id", name="uq_user_course"),
    )
    op.create_index("ix_user_courses_user_id", "user_courses", ["user_id"], unique=False)
    op.create_index("ix_user_courses_course_id", "user_courses", ["course_id"], unique=False)
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("service_type", sa.String(length=50), nullable=False),
        sa.Column("service_name", sa.String(length=100), nullable=False),
        sa.Column("service_price", sa.DECIMAL(10, 2), nullable=True),
        sa.Column("preferred_time", sa.String(length=50), nullable=False),
        sa.Column("confirmed_date", sa.Date(), nullable=True),
        sa.Column("confirmed_time", sa.Time(), nullable=True),
        sa.Column("consultant_id", sa.Integer(), nullable=True),
        sa.Column("consultant_name", sa.String(length=50), nullable=True),
        sa.Column("contact_phone", sa.String(length=20), nullable=False),
        sa.Column("topics", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("meeting_url", sa.String(length=255), nullable=True),
        sa.Column("meeting_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["consultant_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bookings_user_id", "bookings", ["user_id"], unique=False)
    op.create_index("ix_bookings_status", "bookings", ["status"], unique=False)
