from alembic import op
import sqlalchemy as sa

revision = '004_add_sender_name'
down_revision = '003_recharge_requests'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'tenants',
        sa.Column('sender_name', sa.String(11), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('tenants', 'sender_name')
