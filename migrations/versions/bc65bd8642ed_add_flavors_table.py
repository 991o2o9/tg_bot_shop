"""add_flavors_table

Revision ID: bc65bd8642ed
Revises: add_is_deleted_20250827
Create Date: 2025-08-28 01:43:34.372526

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bc65bd8642ed'
down_revision = 'add_is_deleted_20250827'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add flavor_id to order_items table (flavors table already exists)
    op.add_column('order_items', sa.Column('flavor_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'order_items', 'flavors', ['flavor_id'], ['id'])


def downgrade() -> None:
    # Remove flavor_id from order_items
    op.drop_constraint(None, 'order_items', type_='foreignkey')
    op.drop_column('order_items', 'flavor_id')


