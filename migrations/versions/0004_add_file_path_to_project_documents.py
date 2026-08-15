"""add file_path column to project_documents

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'project_documents', sa.Column('file_path', sa.String(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('project_documents', 'file_path')
