"""Add premium_expires_at to user

Revision ID: 053924c11a27
Revises: c03fc45019b8
Create Date: 2026-02-23 07:54:03.696325
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '053924c11a27'
down_revision = 'c03fc45019b8'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    rows = conn.execute(text("SELECT id FROM post WHERE content_hash IS NULL")).fetchall()
    for row in rows:
        unique_hash = f"placeholder_{row.id}"
        conn.execute(
            text("UPDATE post SET content_hash = :h WHERE id = :i"),
            {"h": unique_hash, "i": row.id}
        )

    inspector = inspect(conn)

    # 1️⃣ Create 'payment' table if it does not exist
    if 'payment' not in inspector.get_table_names():
        op.create_table(
            'payment',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('reference', sa.String(120), nullable=False),
            sa.Column('email', sa.String(120), nullable=False),
            sa.Column('amount', sa.Integer(), nullable=False),
            sa.Column('plan', sa.String(50), nullable=False),
            sa.Column('status', sa.String(50), nullable=True),
            sa.Column('subscription_code', sa.String(120), nullable=True),
            sa.Column('customer_code', sa.String(120), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.UniqueConstraint('reference', name='uq_payment_reference')
        )

    # 3️⃣ Alter 'post' table: make content_hash NOT NULL and unique
    with op.batch_alter_table('post') as batch_op:
        batch_op.alter_column(
            'content_hash',
            existing_type=sa.VARCHAR(length=64),
            nullable=False
        )
        batch_op.create_unique_constraint('uq_content_hash', ['content_hash'])

    # 4️⃣ Add 'premium_expires_at' to 'user' table
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(
            sa.Column('premium_expires_at', sa.DateTime(), nullable=True)
        )


def downgrade():
    # 1️⃣ Remove 'premium_expires_at' from 'user'
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('premium_expires_at')

    # 2️⃣ Remove unique constraint and allow NULLs on 'post.content_hash'
    with op.batch_alter_table('post') as batch_op:
        batch_op.drop_constraint('uq_content_hash', type_='unique')
        batch_op.alter_column(
            'content_hash',
            existing_type=sa.VARCHAR(length=64),
            nullable=True
        )

    # 3️⃣ Drop 'payment' table
    op.drop_table('payment')