from http import HTTPStatus
from secrets import token_hex
from typing import Annotated
from uuid import UUID

from fastapi import Depends, File, HTTPException, UploadFile
from faststream.rabbit.fastapi import RabbitRouter as APIRouter
from sqlalchemy import or_, select

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.core.security import get_password_hash, verify_password
from iaEditais.models import User, UserImage
from iaEditais.schemas import (
    UserCreate,
    UserFilter,
    UserList,
    UserPasswordChange,
    UserPublic,
    UserUpdate,
)
from iaEditais.schemas.common import Message
from iaEditais.schemas.user import AccessType
from iaEditais.services import (
    audit,
    notification_service,
    storage_service,
)

UPLOAD_DIRECTORY = 'iaEditais/storage/uploads'

router = APIRouter(prefix='/user', tags=['operações de sistema, usuário'])


@router.post('/', status_code=HTTPStatus.CREATED, response_model=UserPublic)
async def create_user(user: UserCreate, session: Session):
    db_user = await session.scalar(
        select(User).where(
            User.deleted_at.is_(None),
            or_(
                User.email == user.email,
                User.phone_number == user.phone_number,
            ),
        )
    )
    if db_user:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Email or phone number already registered',
        )
    password_was_generated = False
    temp_password = user.password

    if not user.password:
        temp_password = token_hex(12)
        password_was_generated = True

    hashed_password = get_password_hash(temp_password)

    db_user = User(
        username=user.username,
        email=user.email,
        phone_number=user.phone_number,
        password=hashed_password,
        access_level=user.access_level,
        unit_id=user.unit_id,
    )

    session.add(db_user)
    # Flush para gerar o ID antes de usar no log/audit
    await session.flush()

    # 1. Preenche created_at e created_by via Mixin (Auto-referência pois é criação)
    db_user.set_creation_audit(db_user.id)

    # 2. Registro de Auditoria (CREATE)
    await audit.register_action(
        session=session,
        user_id=db_user.id,
        action='CREATE',
        table_name=User.__tablename__,
        record_id=db_user.id,
        old_data=None,
    )

    await session.commit()
    await session.refresh(db_user)

    if password_was_generated:
        await notification_service.publish_user_welcome_notification(
            db_user, temp_password, router.broker
        )

    return db_user


@router.post('/{user_id}/icon', response_model=Message)
async def add_icon(
    user_id: UUID,
    session: Session,
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    result = await session.execute(select(User).where(User.id == user_id))

    user_db = result.scalar_one_or_none()

    if not user_db:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='User not found',
        )

    if user_db.id != current_user.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Access denied',
        )

    # Snapshot antes da alteração (O user será modificado ao receber o icon_id)
    old_data = UserPublic.model_validate(user_db).model_dump(mode='json')

    # 2. Validação do Arquivo
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Invalid file format. Use PNG or JPG',
        )

    if user_db.icon_id:
        old_icon = await session.get(UserImage, user_db.icon_id)
        if old_icon:
            await storage_service.delete_file(old_icon.file_path)
            await session.delete(old_icon)

    file_path = await storage_service.save_file(file, UPLOAD_DIRECTORY)

    user_image = UserImage(
        user_id=current_user.id,
        type='ICON',
        file_path=file_path,
    )
    session.add(user_image)
    await session.flush()

    user_db.icon_id = user_image.id

    # 5. Atualiza auditoria do User
    user_db.set_update_audit(current_user.id)

    # 6. Registro de Auditoria (UPDATE - Adição de Icone)
    await audit.register_action(
        session=session,
        user_id=current_user.id,
        action='UPDATE',
        table_name=User.__tablename__,
        record_id=user_db.id,
        old_data=old_data,
    )

    await session.commit()

    return Message(message='Icon updated successfully')


@router.get('/', response_model=UserList)
async def read_users(
    session: Session, filters: Annotated[UserFilter, Depends()]
):
    query = (
        select(User)
        .where(User.deleted_at.is_(None))
        .order_by(User.created_at.desc())
    )

    if filters.unit_id:
        query = query.where(User.unit_id == filters.unit_id)

    query = query.offset(filters.offset).limit(filters.limit)

    result = await session.scalars(query)
    users = result.all()

    return {'users': users}


@router.get('/my', response_model=UserPublic)
async def read_me(current_user: CurrentUser):
    return current_user


@router.get('/{user_id}/', response_model=UserPublic)
async def read_user(user_id: UUID, session: Session):
    db_user = await session.get(User, user_id)
    if not db_user or db_user.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='User not found'
        )
    return db_user


@router.put('/', response_model=UserPublic)
async def update_user(
    user_update: UserUpdate,
    session: Session,
    current_user: CurrentUser,
):
    db_user = await session.get(User, user_update.id)

    if not db_user or db_user.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='User not found'
        )

    is_owner = db_user.id == current_user.id
    is_admin = current_user.access_level == AccessType.ADMIN

    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='You are not authorized to update this user',
        )

    # Snapshot antes da atualização
    old_data = UserPublic.model_validate(db_user).model_dump(mode='json')

    conflict_user = await session.scalar(
        select(User).where(
            User.deleted_at.is_(None),
            User.id != user_update.id,
            or_(
                User.email == user_update.email,
                User.phone_number == user_update.phone_number,
            ),
        )
    )

    if conflict_user:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Email or phone number already registered',
        )

    db_user.username = user_update.username
    db_user.email = user_update.email
    db_user.phone_number = user_update.phone_number

    # Mixin trata updated_at e updated_by
    db_user.set_update_audit(current_user.id)

    if is_admin:
        db_user.access_level = user_update.access_level
        db_user.unit_id = user_update.unit_id
    elif not is_admin and (
        db_user.access_level != user_update.access_level
        or db_user.unit_id != user_update.unit_id
    ):
        pass

    # Registro de Auditoria (UPDATE)
    await audit.register_action(
        session=session,
        user_id=current_user.id,
        action='UPDATE',
        table_name=User.__tablename__,
        record_id=db_user.id,
        old_data=old_data,
    )

    await session.commit()
    await session.refresh(db_user)

    return db_user


@router.put('/password', response_model=Message)
async def change_password(
    payload: UserPasswordChange,
    session: Session,
    current_user: CurrentUser,
):
    db_user = await session.get(User, payload.user_id)

    if not db_user or db_user.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='User not found',
        )

    is_owner = db_user.id == current_user.id
    is_admin = current_user.access_level == AccessType.ADMIN

    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='You are not authorized to change this password',
        )

    old_data = UserPublic.model_validate(db_user).model_dump(mode='json')

    if is_owner:
        if not payload.current_password:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail='Current password is required',
            )

        if not verify_password(payload.current_password, db_user.password):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail='Invalid current password',
            )

    new_password = payload.new_password
    if len(new_password) < 8:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Password must be at least 8 characters long',
        )
    if (
        new_password.lower() == new_password
        or new_password.upper() == new_password
    ):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Password must contain both uppercase and lowercase letters',
        )
    if not any(c.isdigit() for c in new_password):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Password must contain at least one number',
        )

    db_user.password = get_password_hash(new_password)

    # Auditoria update
    db_user.set_update_audit(current_user.id)

    await audit.register_action(
        session=session,
        user_id=current_user.id,
        action='UPDATE',
        table_name=User.__tablename__,
        record_id=db_user.id,
        old_data=old_data,
    )

    await session.commit()

    return Message(message='Password updated successfully')


@router.delete(
    '/{user_id}/',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_user(
    user_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    db_user = await session.get(User, user_id)
    if not db_user or db_user.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='User not found'
        )

    # Snapshot antes de deletar
    old_data = UserPublic.model_validate(db_user).model_dump(mode='json')

    # Soft delete via Mixin
    db_user.set_deletion_audit(current_user.id)

    # Registro de Auditoria (DELETE)
    await audit.register_action(
        session=session,
        user_id=current_user.id,
        action='DELETE',
        table_name=User.__tablename__,
        record_id=db_user.id,
        old_data=old_data,
    )

    await session.commit()


@router.delete('/{user_id}/icon', response_model=Message)
async def delete_icon(
    user_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    user_db = await session.get(User, user_id)
    if not user_db:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='User not found',
        )

    if user_db.id != current_user.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Access denied',
        )

    if not user_db.icon_id:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Icon not found'
        )

    # Snapshot antes da alteração
    old_data = UserPublic.model_validate(user_db).model_dump(mode='json')

    user_image = await session.get(UserImage, user_db.icon_id)

    if user_image:
        await storage_service.delete_file(user_image.file_path)
        await session.delete(user_image)

    user_db.icon_id = None

    # Atualiza auditoria do User
    user_db.set_update_audit(current_user.id)

    # Registro de Auditoria (UPDATE - Remoção de ícone)
    await audit.register_action(
        session=session,
        user_id=current_user.id,
        action='UPDATE',
        table_name=User.__tablename__,
        record_id=user_db.id,
        old_data=old_data,
    )

    await session.commit()

    return Message(message='Icon successfully deleted!')
