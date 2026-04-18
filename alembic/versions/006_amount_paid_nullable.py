from alembic import op

revision = '006_amount_paid_nullable'
down_revision = '005_account_requests'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.alter_column('recharge_requests', 'amount_paid', nullable=True)

def downgrade() -> None:
    op.alter_column('recharge_requests', 'amount_paid', nullable=False)