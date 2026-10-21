"""add tree suggestion tables

Tabelas da feature de geracao da arvore de verificacao a partir de um
documento PDF: sessoes de sugestao e itens sugeridos (fonte, tipificacao,
taxonomias e ramos).

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '0009'
down_revision: Union[str, Sequence[str], None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tree_suggestion_sessions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('mode', sa.String(20), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('original_filename', sa.String(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('target_typification_id', sa.Uuid(), nullable=True),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('generation_model', sa.String(), nullable=True),
        sa.Column('processing_started_at', sa.DateTime(), nullable=True),
        sa.Column('processing_finished_at', sa.DateTime(), nullable=True),
        sa.Column(
            'excluded_rules',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            'created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False
        ),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('deleted_by', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ['target_typification_id'],
            ['typifications.id'],
            name='fk_tree_suggestion_session_typification_id',
        ),
        sa.ForeignKeyConstraint(
            ['created_by'], ['users.id'], name='fk_tree_suggestion_sessions_created_by'
        ),
        sa.ForeignKeyConstraint(
            ['updated_by'], ['users.id'], name='fk_tree_suggestion_sessions_updated_by'
        ),
        sa.ForeignKeyConstraint(
            ['deleted_by'], ['users.id'], name='fk_tree_suggestion_sessions_deleted_by'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_tree_suggestion_sessions_status',
        'tree_suggestion_sessions',
        ['status'],
    )
    op.create_index(
        'ix_tree_suggestion_sessions_created_at',
        'tree_suggestion_sessions',
        ['created_at'],
    )

    op.create_table(
        'tree_suggestion_items',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('session_id', sa.Uuid(), nullable=False),
        sa.Column('kind', sa.String(20), nullable=False),
        sa.Column('operation', sa.String(20), nullable=False),
        sa.Column('proposed_title', sa.String(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('proposed_description', sa.Text(), nullable=True),
        sa.Column('parent_item_id', sa.Uuid(), nullable=True),
        sa.Column('parent_entity_id', sa.Uuid(), nullable=True),
        sa.Column('target_entity_id', sa.Uuid(), nullable=True),
        sa.Column('target_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            'evidence',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('similar_to_id', sa.Uuid(), nullable=True),
        sa.Column('similarity_note', sa.Text(), nullable=True),
        sa.Column('final_title', sa.String(), nullable=True),
        sa.Column('final_description', sa.Text(), nullable=True),
        sa.Column('applied_entity_id', sa.Uuid(), nullable=True),
        sa.Column('reviewed_by', sa.Uuid(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ['session_id'],
            ['tree_suggestion_sessions.id'],
            name='fk_tree_suggestion_item_session_id',
        ),
        sa.ForeignKeyConstraint(
            ['parent_item_id'],
            ['tree_suggestion_items.id'],
            name='fk_tree_suggestion_item_parent_item_id',
        ),
        sa.ForeignKeyConstraint(
            ['reviewed_by'], ['users.id'], name='fk_tree_suggestion_item_reviewed_by'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_tree_suggestion_items_session_status',
        'tree_suggestion_items',
        ['session_id', 'status'],
    )
    op.create_index(
        'ix_tree_suggestion_items_parent_item_id',
        'tree_suggestion_items',
        ['parent_item_id'],
    )


def downgrade() -> None:
    op.drop_index(
        'ix_tree_suggestion_items_parent_item_id', table_name='tree_suggestion_items'
    )
    op.drop_index(
        'ix_tree_suggestion_items_session_status', table_name='tree_suggestion_items'
    )
    op.drop_table('tree_suggestion_items')
    op.drop_index(
        'ix_tree_suggestion_sessions_created_at', table_name='tree_suggestion_sessions'
    )
    op.drop_index(
        'ix_tree_suggestion_sessions_status', table_name='tree_suggestion_sessions'
    )
    op.drop_table('tree_suggestion_sessions')
