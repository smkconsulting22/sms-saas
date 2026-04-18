from alembic import op

revision = '007_fix_campaign_status'
down_revision = '006_amount_paid_nullable'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Convertir la colonne status de l'enum PostgreSQL vers VARCHAR(20)
    # puis supprimer l'ancien type enum devenu inutile
    op.execute("ALTER TABLE campaigns ALTER COLUMN status TYPE VARCHAR(20)")
    op.execute("DROP TYPE IF EXISTS campaignstatus")


def downgrade() -> None:
    # Recréer l'enum sans "scheduled" (état d'origine)
    op.execute("CREATE TYPE campaignstatus AS ENUM ('draft', 'running', 'completed', 'failed')")
    op.execute(
        "ALTER TABLE campaigns ALTER COLUMN status TYPE campaignstatus"
        " USING status::campaignstatus"
    )
