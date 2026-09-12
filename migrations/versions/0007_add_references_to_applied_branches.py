"""add references column to applied_branches

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = '0007'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'applied_branches',
        sa.Column('references', JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('applied_branches', 'references')