from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import FileResponse

from iaEditais.core.dependencies import Session
from iaEditais.services import report_service, typification_service

router = APIRouter(prefix='/export', tags=['document verification'])


@router.get('/release/pdf')
async def export_document_release_pdf(
    session: Session,
    document_release_id: UUID,
):
    report_path = await report_service.generate_document_release_pdf(
        session=session,
        document_release_id=document_release_id,
    )

    return FileResponse(report_path, filename=report_path.split('/')[-1])


@router.get('/typifications/pdf')
async def export_typifications_pdf(
    session: Session,
    typification_id: UUID | None = None,
):
    return await typification_service.export_pdf(session, typification_id)
