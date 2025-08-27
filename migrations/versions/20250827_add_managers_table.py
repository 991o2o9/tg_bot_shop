"""add managers table

Revision ID: 20250827_add_managers
Revises: 20250827_add_is_deleted_to_products
Create Date: 2025-08-27
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20250827_add_managers"
down_revision = "20250827_add_is_deleted_to_products"
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.create_table(
		"managers",
		sa.Column("id", sa.Integer(), primary_key=True),
		sa.Column("user_id", sa.BigInteger(), nullable=False),
	)
	op.create_unique_constraint("uq_managers_user_id", "managers", ["user_id"])


def downgrade() -> None:
	op.drop_constraint("uq_managers_user_id", "managers", type_="unique")
	op.drop_table("managers")


