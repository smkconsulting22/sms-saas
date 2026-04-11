from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '005_account_requests'
down_revision = '004_add_sender_name'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'account_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('full_name', sa.String(100), nullable=False),
        sa.Column('company_name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('message', sa.String(500), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('rejection_reason', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_account_requests_email', 'account_requests', ['email'])
    op.create_index('ix_account_requests_status', 'account_requests', ['status'])


def downgrade() -> None:
    op.drop_index('ix_account_requests_status', table_name='account_requests')
    op.drop_index('ix_account_requests_email', table_name='account_requests')
    op.drop_table('account_requests')
