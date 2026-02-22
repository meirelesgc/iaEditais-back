"""acompanhamento do processamento do documento

Revision ID: 0452b4611255
Revises: 39015d7b52aa
Create Date: 2026-02-12 16:15:05.003954

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0452b4611255'
down_revision: Union[str, Sequence[str], None] = '39015d7b52aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'documents',
        sa.Column('processing_status', sa.String(), nullable=True)
    )

    op.execute(
        "UPDATE documents SET processing_status = 'IDLE'"
    )

    op.alter_column(
        'documents',
        'processing_status',
        existing_type=sa.String(),
        nullable=False
    )


def downgrade() -> None:
    op.drop_column('documents', 'processing_status')
