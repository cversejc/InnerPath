"""Professional ownership for collaborative report production."""
from alembic import op
import sqlalchemy as sa

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("consultant_type", sa.String(20), nullable=True))
    op.add_column("staff_invites", sa.Column("consultant_type", sa.String(20), nullable=True))
    for field in ("assigned_mingli_consultant_id", "assigned_psychology_consultant_id"):
        op.add_column("service_requests", sa.Column(field, sa.Integer(), nullable=True))
        op.create_foreign_key(f"fk_service_requests_{field}", "service_requests", "users", [field], ["id"], ondelete="SET NULL")
        op.create_index(f"ix_service_requests_{field}", "service_requests", [field])


def downgrade():
    for field in ("assigned_psychology_consultant_id", "assigned_mingli_consultant_id"):
        op.drop_index(f"ix_service_requests_{field}", table_name="service_requests")
        op.drop_constraint(f"fk_service_requests_{field}", "service_requests", type_="foreignkey")
        op.drop_column("service_requests", field)
    op.drop_column("staff_invites", "consultant_type")
    op.drop_column("users", "consultant_type")
