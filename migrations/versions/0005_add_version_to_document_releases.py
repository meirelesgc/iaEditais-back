"""add version column to document_releases

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'document_releases', sa.Column('version', sa.String(), nullable=True)
    )
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT r.id,
                       ROW_NUMBER() OVER (
                           PARTITION BY h.document_id
                           ORDER BY r.created_at ASC, r.id ASC
                       ) - 1 AS idx
                FROM document_releases r
                JOIN document_histories h ON h.id = r.history_id
            )
            UPDATE document_releases
            SET version = '1.0.' || ranked.idx
            FROM ranked
            WHERE document_releases.id = ranked.id
            """
        )
    )


def downgrade() -> None:
    op.drop_column('document_releases', 'version')
