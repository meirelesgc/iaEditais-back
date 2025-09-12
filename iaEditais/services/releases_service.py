import os
import shutil
import uuid
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.database import get_session
from iaEditais.models import User
from iaEditais.repository import releases_repository
from iaEditais.security import get_current_user

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]

UPLOAD_DIRECTORY = 'iaEditais/storage/uploads'


def safe_file(file: UploadFile, upload_directory) -> str:
    os.makedirs(upload_directory, exist_ok=True)

    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f'{uuid.uuid4()}{file_extension}'
    file_path = os.path.join(upload_directory, unique_filename)

    try:
        with open(file_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    return file_path


async def create_release(
    doc_id: UUID,
    session: Session,
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    db_doc = await releases_repository.get_db_doc(doc_id, session)

    if not db_doc:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document not found',
        )

    if not db_doc.history:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Document does not have a history to attach the file.',
        )

    latest_history = db_doc.history[0]
    file_path = safe_file(file, UPLOAD_DIRECTORY)
    db_release = await releases_repository.insert_db_release(
        latest_history, file_path, session, current_user
    )
    return db_release
