from http import HTTPStatus
from typing import Annotated, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    Form,
    UploadFile,
)

from iaEditais.core.dependencies import CurrentUser, Session, Storage
from iaEditais.features.tree_suggestion import (
    service as tree_suggestion_service,
)
from iaEditais.schemas import (
    TreeSuggestionFilter,
    TreeSuggestionItemConfirm,
    TreeSuggestionItemPublic,
    TreeSuggestionSessionDetail,
    TreeSuggestionSessionList,
)

router = APIRouter(
    prefix='/tree-suggestion',
    tags=['árvore de verificação, sugestões'],
)


@router.post(
    '',
    status_code=HTTPStatus.ACCEPTED,
    response_model=TreeSuggestionSessionDetail,
)
async def create_suggestion_session(  # noqa: PLR0913, PLR0917
    session: Session,
    current_user: CurrentUser,
    storage: Storage,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    typification_id: Optional[UUID] = Form(None),
    document_group_id: Optional[UUID] = Form(None),
    document_group_item_id: Optional[UUID] = Form(None),
):
    return await tree_suggestion_service.create_session(
        session,
        current_user.id,
        storage,
        file,
        typification_id,
        background_tasks,
        document_group_id,
        document_group_item_id,
    )


@router.get('', response_model=TreeSuggestionSessionList)
async def read_suggestion_sessions(
    session: Session,
    current_user: CurrentUser,
    filters: Annotated[TreeSuggestionFilter, Depends()],
):
    sessions = await tree_suggestion_service.list_sessions(session, filters)
    return {'sessions': sessions}


@router.get('/{session_id}', response_model=TreeSuggestionSessionDetail)
async def read_suggestion_session(
    session_id: UUID, session: Session, current_user: CurrentUser
):
    return await tree_suggestion_service.get_session_detail(
        session, session_id
    )


@router.post(
    '/{session_id}/items/{item_id}/confirm',
    response_model=TreeSuggestionItemPublic,
)
async def confirm_suggestion_item(  # noqa: PLR0913, PLR0917
    session_id: UUID,
    item_id: UUID,
    session: Session,
    current_user: CurrentUser,
    data: Annotated[Optional[TreeSuggestionItemConfirm], Body()] = None,
):
    return await tree_suggestion_service.confirm_item(
        session,
        current_user.id,
        session_id,
        item_id,
        data,
    )


@router.post(
    '/{session_id}/items/{item_id}/discard',
    response_model=TreeSuggestionSessionDetail,
)
async def discard_suggestion_item(
    session_id: UUID,
    item_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    return await tree_suggestion_service.discard_item(
        session, current_user.id, session_id, item_id
    )


@router.post(
    '/{session_id}/discard',
    response_model=TreeSuggestionSessionDetail,
)
async def discard_suggestion_session(
    session_id: UUID, session: Session, current_user: CurrentUser
):
    return await tree_suggestion_service.discard_session(
        session, current_user.id, session_id
    )
