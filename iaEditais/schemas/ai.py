from typing import List, Optional

from pydantic import BaseModel, Field


class Citation(BaseModel):
    chunk_id: str = Field(
        description='Identificador único do chunk utilizado'
    )
    text_snippet: Optional[str] = Field(
        None,
        description='Pequeno trecho exato do texto citado para facilitar o mapeamento visual',
    )


class AnswerWithCitations(BaseModel):
    answer: str = Field(
        description='Sua resposta completa para a pergunta do usuário.'
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description='Lista de identificadores dos chunks que embasam a sua resposta.',
    )
