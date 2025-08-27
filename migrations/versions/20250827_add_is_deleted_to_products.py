from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_is_deleted_20250827'
down_revision = 'add_in_stock_20250826'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('products', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column('products', 'is_deleted', server_default=None)


def downgrade() -> None:
    op.drop_column('products', 'is_deleted')


