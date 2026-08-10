"""add_users_brokers_accounts

Revision ID: 81122f00a568
Revises: xxxxx
Create Date: 2026-08-10 11:39:35.987950

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '81122f00a568'
down_revision: Union[str, Sequence[str], None] = 'xxxxx'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
