# Endpoints HTTP da feature "Conformidade com Template e Normas ABNT" — toda
# a lógica de negócio fica em iaEditais/features/template_abnt/ (ver service.py).

from http import HTTPStatus
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from iaEditais.features.template_abnt import service
from iaEditais.features.template_abnt.json_store import JsonResultStore
from iaEditais.features.template_abnt.schemas import (
    ProcessingAccepted,
    ProcessingResult,
    TemplatesListResponse,
)

router = APIRouter(
    prefix='/template-abnt',
    tags=['conformidade com template e normas ABNT'],
)

TEMPLATE_NOT_FOUND_DETAIL = 'Template não encontrado.'
TEMPLATE_RESULT_NOT_FOUND_DETAIL = 'Nenhum processamento de template encontrado para este documento.'
ABNT_RESULT_NOT_FOUND_DETAIL = 'Nenhum processamento ABNT encontrado para este documento.'


def get_result_or_404(store: JsonResultStore, doc_id: str, not_found_detail: str) -> dict:
    result = store.get(doc_id)
    if result is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=not_found_detail)
    return result


@router.get('/templates', response_model=TemplatesListResponse)
async def list_templates():
    return {'templates': service.list_templates()}


@router.post(
    '/{doc_id}/template',
    status_code=HTTPStatus.ACCEPTED,
    response_model=ProcessingAccepted,
)
async def process_template_compliance(
    doc_id: str,
    background_tasks: BackgroundTasks,
    template_name: Annotated[str, Form()] = service.DEFAULT_TEMPLATE_NAME,
    file: UploadFile = File(...),
):
    template_path = service.resolve_template_path(template_name)
    if template_path is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=TEMPLATE_NOT_FOUND_DETAIL)

    content = await file.read()
    service.start_template_analysis(doc_id, file.filename, content, template_path, background_tasks)
    return {'doc_id': doc_id, 'status': 'processing'}


@router.get('/{doc_id}/template', response_model=ProcessingResult)
async def get_template_result(doc_id: str):
    return get_result_or_404(service.get_template_store(), doc_id, TEMPLATE_RESULT_NOT_FOUND_DETAIL)


@router.post(
    '/{doc_id}/abnt',
    status_code=HTTPStatus.ACCEPTED,
    response_model=ProcessingAccepted,
)
async def process_abnt_compliance(
    doc_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    content = await file.read()
    service.start_abnt_analysis(doc_id, file.filename, content, background_tasks)
    return {'doc_id': doc_id, 'status': 'processing'}


@router.get('/{doc_id}/abnt', response_model=ProcessingResult)
async def get_abnt_result(doc_id: str):
    return get_result_or_404(service.get_abnt_store(), doc_id, ABNT_RESULT_NOT_FOUND_DETAIL)
