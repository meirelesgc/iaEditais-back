import os
import re
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

from aiofiles import open as aio_open
from fastapi import UploadFile

from iaEditais.core.settings import Settings

SETTINGS = Settings()
UPLOAD_DIRECTORY = SETTINGS.UPLOAD_DIRECTORY
STORAGE_PROVIDER = SETTINGS.STORAGE_PROVIDER

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
UNSAFE_FILENAME_CHARS = re.compile(r'[^A-Za-z0-9._-]')

ALLOWED_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif')


def resolve_storage_dir(directory: str | Path) -> Path:
    """Diretórios relativos são resolvidos a partir da raiz do projeto, e não
    do diretório de trabalho, para que a escrita e o StaticFiles do app
    (/uploads) apontem sempre para a mesma pasta."""
    path = Path(directory)
    return path if path.is_absolute() else PROJECT_ROOT / path


def is_valid_image_filename(filename: str | None) -> bool:
    return bool(filename) and filename.lower().endswith(ALLOWED_IMAGE_EXTENSIONS)


class StorageProvider(ABC):
    @abstractmethod
    async def save(self, file: UploadFile, filename: str) -> str:
        """Persiste o binário e devolve a URL de leitura."""

    @abstractmethod
    async def delete(self, reference: str) -> bool:
        """Remove o binário a partir da URL devolvida por `save`."""

    @abstractmethod
    async def exists(self, reference: str) -> bool:
        pass

    @abstractmethod
    async def get_url(self, filename: str) -> str:
        pass


class LocalStorage(StorageProvider):
    def __init__(
        self, storage_dir: str = UPLOAD_DIRECTORY, base_url: str = '/uploads'
    ):
        self.storage_dir = resolve_storage_dir(storage_dir)
        self.base_url = base_url.rstrip('/')
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sanitize(filename: str) -> str:
        name = UNSAFE_FILENAME_CHARS.sub('_', os.path.basename(filename or ''))
        return name if name.strip('.') else 'file'

    def _resolve(self, reference: str) -> Path:
        """Aceita tanto a URL devolvida por `save` ('/uploads/a.png') quanto o
        nome puro do arquivo, para que `delete` aponte para o mesmo lugar
        que `save` escreveu."""
        prefix = f'{self.base_url}/'
        candidate = reference[len(prefix) :] if reference.startswith(prefix) else reference
        return self.storage_dir / self._sanitize(candidate)

    async def save(self, file: UploadFile, filename: str) -> str:
        safe_name = self._sanitize(filename)
        file_path = self.storage_dir / safe_name
        content = await file.read()
        async with aio_open(file_path, 'wb') as out_file:
            await out_file.write(content)
        return await self.get_url(safe_name)

    async def delete(self, reference: str) -> bool:
        file_path = self._resolve(reference)
        try:
            if file_path.exists():
                os.remove(file_path)
                return True
            return False
        except OSError:
            return False

    async def exists(self, reference: str) -> bool:
        return self._resolve(reference).exists()

    async def get_url(self, filename: str) -> str:
        return f'{self.base_url}/{self._sanitize(filename)}'


class S3Storage(StorageProvider):
    async def save(self, file: UploadFile, filename: str) -> str:
        raise NotImplementedError('S3 Storage not implemented yet')

    async def delete(self, reference: str) -> bool:
        pass

    async def exists(self, reference: str) -> bool:
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
