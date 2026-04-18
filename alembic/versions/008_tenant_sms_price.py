from alembic import op
import sqlalchemy as sa

revision = '008_tenant_sms_price'
down_revision = '007_fix_campaign_status'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'tenants',
        sa.Column('sms_price', sa.Numeric(10, 2), nullable=False, server_default='20.0'),
    )


def downgrade() -> None:
    op.drop_column('tenants', 'sms_price')
