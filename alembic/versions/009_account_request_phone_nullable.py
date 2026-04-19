from alembic import op

revision = '009_account_request_phone_nullable'
down_revision = '008_tenant_sms_price'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('account_requests', 'phone', nullable=True)


def downgrade() -> None:
    op.alter_column('account_requests', 'phone', nullable=False)
