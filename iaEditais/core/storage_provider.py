import os
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

from aiofiles import open as aio_open
from fastapi import UploadFile

from iaEditais.core.settings import Settings

SETTINGS = Settings()
UPLOAD_DIRECTORY = SETTINGS.UPLOAD_DIRECTORY
STORAGE_PROVIDER = SETTINGS.STORAGE_PROVIDER


class StorageProvider(ABC):
    @abstractmethod
    async def save(self, file: UploadFile, filename: str) -> str:
        pass

    @abstractmethod
    async def delete(self, filename: str) -> bool:
        pass

    @abstractmethod
    async def exists(self, filename: str) -> bool:
        pass

    @abstractmethod
    async def get_url(self, filename: str) -> str:
        pass


class LocalStorage(StorageProvider):
    def __init__(
        self, storage_dir: str = UPLOAD_DIRECTORY, base_url: str = '/uploads'
    ):
        self.storage_dir = Path(storage_dir)
        self.base_url = base_url.rstrip('/')
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, file: UploadFile, filename: str) -> str:
        file_path = self.storage_dir / filename
        async with aio_open(file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
        return await self.get_url(filename)

    async def delete(self, filename: str) -> bool:
        file_path = self.storage_dir / filename
        try:
            if file_path.exists():
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False

    async def exists(self, filename: str) -> bool:
        file_path = self.storage_dir / filename
        return file_path.exists()

    async def get_url(self, filename: str) -> str:
        return f'{self.base_url}/{filename}'


class S3Storage(StorageProvider):
    async def save(self, file: UploadFile, filename: str) -> str:
        raise NotImplementedError('S3 Storage not implemented yet')

    async def delete(self, filename: str) -> bool:
        pass

    async def exists(self, filename: str) -> bool:
        pass

    async def get_url(self, filename: str) -> str:
        pass


@lru_cache
def get_storage_provider() -> StorageProvider:
    if STORAGE_PROVIDER == 'LOCAL':
        return LocalStorage()
    elif STORAGE_PROVIDER == 'S3':
        return S3Storage()
    else:
        raise ValueError(f'Unknown storage provider: {STORAGE_PROVIDER}')
