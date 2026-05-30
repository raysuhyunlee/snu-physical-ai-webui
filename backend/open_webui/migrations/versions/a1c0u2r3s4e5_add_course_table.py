"""Add course table (and merge divergent heads)

Revision ID: a1c0u2r3s4e5
Revises: c1d2e3f4a5b6, a0b1c2d3e4f5, 018012973d35
Create Date: 2026-05-30 00:00:00.000000

This migration also merges the three divergent alembic heads that resulted
from the dev-branch merge, so that `alembic upgrade head` resolves to a
single head again.
"""

from alembic import op
import sqlalchemy as sa

revision = 'a1c0u2r3s4e5'
down_revision = ('c1d2e3f4a5b6', 'a0b1c2d3e4f5', '018012973d35')
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'course',
        sa.Column('id', sa.Text(), nullable=False, primary_key=True, unique=True),
        sa.Column('user_id', sa.Text(), nullable=True),
        sa.Column('name', sa.Text(), nullable=True),
        sa.Column('knowledge_id', sa.Text(), nullable=True),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=True),
        sa.Column('updated_at', sa.BigInteger(), nullable=True),
    )


def downgrade():
    op.drop_table('course')
