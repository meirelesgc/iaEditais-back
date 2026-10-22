"""add tree suggestion document group

Guarda o grupo e o tipo de documento informados na criacao da sessao de
sugestao, para que a tipificacao gerada a partir do documento seja criada
com essas referencias.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0010'
down_revision: Union[str, Sequence[str], None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'tree_suggestion_sessions',
        sa.Column('document_group_id', sa.Uuid(), nullable=True),
    )
    op.add_column(
        'tree_suggestion_sessions',
        sa.Column('document_group_item_id', sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        'fk_tree_suggestion_session_document_group_id',
        'tree_suggestion_sessions',
        'document_groups',
        ['document_group_id'],
        ['id'],
    )
    op.create_foreign_key(
        'fk_tree_suggestion_session_document_group_item_id',
        'tree_suggestion_sessions',
        'document_group_items',
        ['document_group_item_id'],
        ['id'],
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_tree_suggestion_session_document_group_item_id',
        'tree_suggestion_sessions',
        type_='foreignkey',
    )
    op.drop_constraint(
        'fk_tree_suggestion_session_document_group_id',
        'tree_suggestion_sessions',
        type_='foreignkey',
    )
    op.drop_column('tree_suggestion_sessions', 'document_group_item_id')
    op.drop_column('tree_suggestion_sessions', 'document_group_id')
