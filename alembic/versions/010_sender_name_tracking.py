from alembic import op
import sqlalchemy as sa

revision = '010_sender_name_tracking'
down_revision = '009_phone_nullable'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tenants', sa.Column('sender_name_requested', sa.String(11), nullable=True))
    op.add_column('tenants', sa.Column('sender_name_status', sa.String(20), nullable=False, server_default='none'))
    op.add_column('tenants', sa.Column('sender_name_requested_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tenants', sa.Column('sender_name_approved_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tenants', sa.Column('sender_name_rejection_reason', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('tenants', 'sender_name_rejection_reason')
    op.drop_column('tenants', 'sender_name_approved_at')
    op.drop_column('tenants', 'sender_name_requested_at')
    op.drop_column('tenants', 'sender_name_status')
    op.drop_column('tenants', 'sender_name_requested')
