from http import HTTPStatus
from pathlib import Path

import pytest

# from uuid import uuid4
from iaEditais.schemas.source import Source


@pytest.mark.asyncio
async def test_create_source(client):
    file_path = Path('storage/tests/source.pdf')
    data = {'name': 'name', 'description': 'description'}
    with file_path.open('rb') as f:
        file = {'file': f}

        response = client.post('/source/', files=file, data=data)
        source = response.json()

        assert isinstance(Source(**source), Source)
        assert response.status_code == HTTPStatus.CREATED
