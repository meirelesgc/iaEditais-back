"""add references column to document_messages

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = '0006'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'document_messages',
        sa.Column('references', JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('document_messages', 'references')
