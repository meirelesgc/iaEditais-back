"""imagens de item de grupo passam a ser arquivos, nao base64

O icon_path dos itens do configurador era preenchido pelo front com uma data URL
(base64) via JSON. Alem de inflar a tabela em ~33%, a imagem era devolvida em
toda listagem e copiada para audit_logs a cada alteracao do grupo.

A imagem agora e enviada por upload (POST /document-group/item/{id}/icon) e o
icon_path guarda a URL /uploads/<uuid>_<nome>, igual ao icone de perfil do
usuario. Esta migration limpa os base64 existentes.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = '0008'
down_revision: Union[str, Sequence[str], None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT = 'ck_document_group_items_icon_path_not_data_url'


def upgrade() -> None:
    op.execute(
        "UPDATE document_group_items SET icon_path = NULL "
        "WHERE icon_path IS NOT NULL"
    )
    op.create_check_constraint(
        CONSTRAINT,
        'document_group_items',
        "icon_path IS NULL OR icon_path NOT LIKE 'data:%'",
    )


def downgrade() -> None:
    op.drop_constraint(
        CONSTRAINT, 'document_group_items', type_='check'
    )
    op.execute(
        "UPDATE document_group_items SET icon_path = NULL "
        "WHERE icon_path LIKE 'data:%'"
    )
