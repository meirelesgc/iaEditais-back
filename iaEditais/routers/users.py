from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import Depends, File, UploadFile
from faststream.rabbit.fastapi import RabbitRouter as APIRouter

from iaEditais.core.dependencies import CurrentUser, Session, Storage
from iaEditais.schemas import (
    UserCreate,
    UserFilter,
    UserList,
    UserPasswordChange,
    UserPublic,
    UserUpdate,
)
from iaEditais.schemas.common import Message
from iaEditais.schemas.user import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from iaEditais.services import (  # Importando auth_service
    auth_service,
    user_service,
)

router = APIRouter(
    prefix='/user',
    tags=['operações de sistema, usuário'],
)

# ... [Outros endpoints de Create/Read/Update/Delete de usuário mantidos iguais] ...
# Vou listar apenas os endpoints que delegam para o auth_service para economizar espaço
# mas considere que o resto do arquivo (CRUD) continua chamando user_service


@router.post('', status_code=HTTPStatus.CREATED, response_model=UserPublic)
async def create_user(user: UserCreate, session: Session):
    return await user_service.create_user(session, user, router.broker)


@router.post('/{user_id}/icon', response_model=Message)
async def add_icon(
    user_id: UUID,
    session: Session,
    current_user: CurrentUser,
    storage: Storage,
    file: UploadFile = File(...),
):
    return await user_service.update_user_icon(
        session, user_id, current_user.id, file, storage
    )


@router.get('', response_model=UserList)
async def read_users(
    session: Session, filters: Annotated[UserFilter, Depends()]
):
    users = await user_service.get_users(session, filters)
    return {'users': users}


@router.get('/my', response_model=UserPublic)
async def read_me(current_user: CurrentUser):
    return current_user


@router.get('/{user_id}', response_model=UserPublic)
async def read_user(user_id: UUID, session: Session):
    return await user_service.get_user_by_id(session, user_id)


@router.put('', response_model=UserPublic)
async def update_user(
    user_update: UserUpdate,
    session: Session,
    current_user: CurrentUser,
):
    return await user_service.update_user(session, current_user, user_update)


@router.delete('/{user_id}', status_code=HTTPStatus.NO_CONTENT)
async def delete_user(
    user_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await user_service.delete_user(session, current_user.id, user_id)


@router.delete('/{user_id}/icon', response_model=Message)
async def delete_icon(
    user_id: UUID,
    session: Session,
    current_user: CurrentUser,
    storage: Storage,
):
    return await user_service.delete_user_icon(
        session, current_user.id, user_id, storage
    )


@router.post('/{user_id}/test-whatsapp', response_model=Message)
async def test_whatsapp(
    user_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    return await user_service.test_whatsapp(
        session, current_user, user_id, router.broker
    )


# --- ENDPOINTS LEGADOS (Redirecionando para Auth Service) ---


@router.put('/password', response_model=Message, include_in_schema=False)
async def change_password(
    payload: UserPasswordChange,
    session: Session,
    current_user: CurrentUser,
):
    return await auth_service.change_password(session, current_user, payload)


@router.post(
    '/forgot-password', status_code=HTTPStatus.OK, include_in_schema=False
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    session: Session,
):
    return await auth_service.forgot_password(session, payload, router.broker)


@router.post(
    '/reset-password', status_code=HTTPStatus.OK, include_in_schema=False
)
async def reset_password(
    payload: ResetPasswordRequest,
    session: Session,
):
    # Delega para auth_service
    return await auth_service.reset_password(session, payload)
