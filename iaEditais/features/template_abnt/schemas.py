# Schemas do envelope de status usados pelos endpoints (routers/template_abnt.py).
# Os relatórios têm formatos diferentes entre si, por isso `report` é um dict livre.

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

ProcessingStatus = Literal['processing', 'completed', 'error']


class TemplatesListResponse(BaseModel):
    templates: list[str]


class ProcessingAccepted(BaseModel):
    doc_id: str
    status: ProcessingStatus = 'processing'


class ProcessingResult(BaseModel):
    doc_id: str
    status: ProcessingStatus
    updated_at: str
    report: dict[str, Any] | None = None
    error: str | None = None
