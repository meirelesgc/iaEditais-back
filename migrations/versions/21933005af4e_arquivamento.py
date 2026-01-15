from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '21933005af4e'
down_revision: Union[str, Sequence[str], None] = '836a80fde2a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('documents', sa.Column('is_archived', sa.Boolean(), nullable=True))
    op.execute("UPDATE documents SET is_archived = FALSE")
    op.alter_column('documents', 'is_archived', nullable=False)

def downgrade() -> None:
    op.drop_column('documents', 'is_archived')
