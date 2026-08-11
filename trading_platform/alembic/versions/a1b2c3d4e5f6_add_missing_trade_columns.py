"""add missing volume/open_time/close_time columns to trades

Revision ID: a1b2c3d4e5f6
Revises: 81122f00a568
Create Date: 2026-08-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '81122f00a568'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('trades', sa.Column('volume', sa.Float(), nullable=True))
    op.add_column('trades', sa.Column('open_time', sa.DateTime(), nullable=True))
    op.add_column('trades', sa.Column('close_time', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('trades', 'close_time')
    op.drop_column('trades', 'open_time')
    op.drop_column('trades', 'volume')