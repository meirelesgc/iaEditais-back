import os
import shutil
import uuid

from fastapi import UploadFile

UPLOAD_DIRECTORY = 'iaEditais/storage/uploads'


async def save_file(file: UploadFile, upload_directory) -> str:
    os.makedirs(upload_directory, exist_ok=True)

    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f'{uuid.uuid4()}{file_extension}'
    file_path = os.path.join(upload_directory, unique_filename)

    try:
        with open(file_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()
    return f'/uploads/{unique_filename}'


async def delete_file(file_path: str) -> bool:
    filename = os.path.basename(file_path)

    absolute_path = os.path.join(UPLOAD_DIRECTORY, filename)

    if os.path.exists(absolute_path):
        try:
            os.remove(absolute_path)
            return True
        except Exception:
            return False
    return False
