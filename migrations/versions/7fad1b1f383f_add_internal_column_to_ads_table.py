"""Add internal column to Ads table

Revision ID: 7fad1b1f383f
Revises: 8dbc8cc5fbce
Create Date: 2026-02-26 22:18:39.904568
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7fad1b1f383f'
down_revision = '8dbc8cc5fbce'
branch_labels = None
depends_on = None


def upgrade():
    """Add 'internal' column to ads table with default False and create index."""
    with op.batch_alter_table('ads', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'internal',
                sa.Boolean(),
                nullable=False,
                server_default=sa.false()  # ensures existing rows are set to False
            )
        )
        batch_op.create_index(batch_op.f('ix_ads_internal'), ['internal'], unique=False)


def downgrade():
    """Remove 'internal' column and index."""
    with op.batch_alter_table('ads', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ads_internal'))
        batch_op.drop_column('internal')