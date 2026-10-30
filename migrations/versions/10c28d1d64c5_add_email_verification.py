"""Add email verification

Revision ID: 10c28d1d64c5
Revises: d3feafe5a94e
Create Date: 2026-10-30 11:50:37.098927

"""

from alembic import op
import sqlalchemy as sa

revision = '10c28d1d64c5'
down_revision = 'd3feafe5a94e'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'email_verified',
                sa.Boolean(),
                server_default=sa.text('TRUE'),
                nullable=False
            )
        )
    
        batch_op.add_column(
            sa.Column(
                'email_verified_at',
                sa.DateTime(),
                nullable=True
            )
        )

def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('email_verified_at')
        batch_op.drop_column('email_verified')