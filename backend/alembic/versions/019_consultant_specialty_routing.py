"""Add consultant capabilities and request routing direction."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "019_consultant_specialty_routing"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "consultant_specialties",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "service_requests",
        sa.Column("consultation_type", sa.String(length=30), nullable=True),
    )
    op.execute(
        "UPDATE service_requests SET consultation_type = 'integrated' "
        "WHERE service_type = 'report' AND consultation_type IS NULL"
    )


def downgrade() -> None:
    op.drop_column("service_requests", "consultation_type")
    op.drop_column("users", "consultant_specialties")
