"""add is_test flag and test_run status fields

Revision ID: 20ac25fed6c6
Revises: a9c06671bd3a
Create Date: 2025-12-25 19:12:10.423117

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20ac25fed6c6'
down_revision: Union[str, Sequence[str], None] = 'a9c06671bd3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Adiciona colunas is_test como NULLABLE primeiro
    op.add_column('document_releases', sa.Column('is_test', sa.Boolean(), nullable=True))
    op.add_column('documents', sa.Column('is_test', sa.Boolean(), nullable=True))
    
    # 2. Preenche registros existentes com valor padrão (False)
    op.execute("UPDATE document_releases SET is_test = FALSE WHERE is_test IS NULL")
    op.execute("UPDATE documents SET is_test = FALSE WHERE is_test IS NULL")
    
    # 3. Altera colunas para NOT NULL
    op.alter_column('document_releases', 'is_test', nullable=False)
    op.alter_column('documents', 'is_test', nullable=False)
    
    # 4. Adiciona colunas de status no test_runs (mesmo processo)
    op.add_column('test_runs', sa.Column('status', sa.String(), nullable=True))
    op.add_column('test_runs', sa.Column('progress', sa.String(), nullable=True))
    op.add_column('test_runs', sa.Column('error_message', sa.String(), nullable=True))
    op.add_column('test_runs', sa.Column('release_id', sa.Uuid(), nullable=True))
    
    # 5. Preenche status dos test_runs existentes
    op.execute("UPDATE test_runs SET status = 'completed' WHERE status IS NULL")
    
    # 6. Altera status para NOT NULL
    op.alter_column('test_runs', 'status', nullable=False)
    
    # 7. Cria foreign key
    op.create_foreign_key('fk_test_runs_release_id', 'test_runs', 'document_releases', ['release_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_test_runs_release_id', 'test_runs', type_='foreignkey')
    op.drop_column('test_runs', 'release_id')
    op.drop_column('test_runs', 'error_message')
    op.drop_column('test_runs', 'progress')
    op.drop_column('test_runs', 'status')
    op.drop_column('documents', 'is_test')
    op.drop_column('document_releases', 'is_test')
