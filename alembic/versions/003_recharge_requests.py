from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003_recharge_requests'
down_revision = '002_add_superadmin'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'recharge_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount_requested', sa.Integer(), nullable=False),
        sa.Column('amount_paid', sa.Numeric(10, 2), nullable=False),
        sa.Column('payment_method', sa.String(20), nullable=False),
        sa.Column('payment_reference', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('note', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_recharge_requests_tenant_id', 'recharge_requests', ['tenant_id'])
    op.create_index('ix_recharge_requests_status', 'recharge_requests', ['status'])


def downgrade() -> None:
    op.drop_index('ix_recharge_requests_status', table_name='recharge_requests')
    op.drop_index('ix_recharge_requests_tenant_id', table_name='recharge_requests')
    op.drop_table('recharge_requests')
