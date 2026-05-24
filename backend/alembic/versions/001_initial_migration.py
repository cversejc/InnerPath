"""Initial migration

Revision ID: 001
Revises:
Create Date: 2026-05-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('wechat_openid', sa.String(length=100), nullable=True),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('gender', sa.String(length=10), nullable=True),
        sa.Column('birth_year', sa.Integer(), nullable=True),
        sa.Column('birth_month', sa.Integer(), nullable=True),
        sa.Column('birth_day', sa.Integer(), nullable=True),
        sa.Column('birth_hour', sa.Integer(), nullable=True),
        sa.Column('birth_minute', sa.Integer(), nullable=True),
        sa.Column('birth_place', sa.String(length=100), nullable=True),
        sa.Column('avatar_url', sa.String(length=255), nullable=True),
        sa.Column('user_type', sa.String(length=20), nullable=False, server_default='explorer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_phone', 'users', ['phone'], unique=True)
    op.create_index('ix_users_wechat_openid', 'users', ['wechat_openid'], unique=True)

    # Create reports table
    op.create_table(
        'reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False, server_default='个人能量地图报告'),
        sa.Column('birth_date', sa.Date(), nullable=False),
        sa.Column('birth_time', sa.Time(), nullable=True),
        sa.Column('energy_profile', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('career_guidance', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('relationship_pattern', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('personal_growth', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('ai_raw_content', sa.Text(), nullable=True),
        sa.Column('ai_model', sa.String(length=50), nullable=False, server_default='deepseek-chat'),
        sa.Column('generation_time_ms', sa.Integer(), nullable=True),
        sa.Column('selected_topics', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('additional_info', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='completed'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_reports_user_id', 'reports', ['user_id'])

    # Create bookings table
    op.create_table(
        'bookings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('service_type', sa.String(length=50), nullable=False),
        sa.Column('service_name', sa.String(length=100), nullable=False),
        sa.Column('service_price', sa.DECIMAL(10, 2), nullable=True),
        sa.Column('preferred_time', sa.String(length=50), nullable=False),
        sa.Column('confirmed_date', sa.Date(), nullable=True),
        sa.Column('confirmed_time', sa.Time(), nullable=True),
        sa.Column('consultant_id', sa.Integer(), nullable=True),
        sa.Column('consultant_name', sa.String(length=50), nullable=True),
        sa.Column('contact_phone', sa.String(length=20), nullable=False),
        sa.Column('topics', postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('meeting_url', sa.String(length=255), nullable=True),
        sa.Column('meeting_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['consultant_id'], ['users.id'])
    )
    op.create_index('ix_bookings_user_id', 'bookings', ['user_id'])
    op.create_index('ix_bookings_status', 'bookings', ['status'])

    # Create courses table
    op.create_table(
        'courses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('cover_image', sa.String(length=255), nullable=True),
        sa.Column('price', sa.DECIMAL(10, 2), nullable=False),
        sa.Column('original_price', sa.DECIMAL(10, 2), nullable=True),
        sa.Column('total_lessons', sa.Integer(), nullable=False),
        sa.Column('duration_hours', sa.DECIMAL(5, 1), nullable=True),
        sa.Column('modules', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create user_courses table
    op.create_table(
        'user_courses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('completed_lessons', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('progress_percentage', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_lesson_id', sa.Integer(), nullable=True),
        sa.Column('purchase_price', sa.DECIMAL(10, 2), nullable=False),
        sa.Column('payment_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('enrolled_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'course_id', name='uq_user_course')
    )
    op.create_index('ix_user_courses_user_id', 'user_courses', ['user_id'])


def downgrade():
    op.drop_table('user_courses')
    op.drop_table('courses')
    op.drop_table('bookings')
    op.drop_table('reports')
    op.drop_table('users')
