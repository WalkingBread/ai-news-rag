"""Merge heads

Revision ID: e0b9ed405fac
Revises: 033a4779f3b4, 15a9850fcfdf
Create Date: 2026-04-30 14:12:25.684705

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e0b9ed405fac'
down_revision: Union[str, Sequence[str], None] = ('033a4779f3b4', '15a9850fcfdf')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
