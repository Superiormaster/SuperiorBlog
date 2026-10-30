"""Add registered user campaign recipients

Revision ID: 1dab4ce5ee7d
Revises: 10c28d1d64c5
Create Date: 2026-10-30 13:43:16.654554

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1dab4ce5ee7d'
down_revision = '10c28d1d64c5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('campaign_recipient', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('user_id', sa.Integer(), nullable=True)
        )

        batch_op.create_index(
            'ix_campaign_recipient_user_id',
            ['user_id'],
            unique=False
        )

        batch_op.create_foreign_key(
            'fk_campaign_recipient_user_id',
            'user',
            ['user_id'],
            ['id']
        )


def downgrade():
    with op.batch_alter_table('campaign_recipient', schema=None) as batch_op:
        batch_op.drop_constraint(
            'fk_campaign_recipient_user_id',
            type_='foreignkey'
        )

        batch_op.drop_index('ix_campaign_recipient_user_id')
        batch_op.drop_column('user_id')