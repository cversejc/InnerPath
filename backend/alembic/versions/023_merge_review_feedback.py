"""Merge aggregate-review and service-feedback migration branches."""
revision = "023_merge_review_feedback"
down_revision = ("022_node_review", "020_service_feedback")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
