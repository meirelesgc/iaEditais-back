from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Heading:
    """Cabeçalho identificado no documento."""

    line_number: int
    level: int
    title: str
    raw: str
    page: Optional[int] = None
    char_start: Optional[int] = None


@dataclass
class Section:
    """Seção delimitada por cabeçalho e conteúdo associado."""

    heading: Heading
    breadcrumb: List[str] = field(default_factory=list)
    content: str = ''
    parent_title: Optional[str] = None
    children: List['Section'] = field(default_factory=list)
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    heading_char_start: Optional[int] = None

    @property
    def title(self) -> str:
        return self.heading.title

    @property
    def level(self) -> int:
        return self.heading.level
