from iaEditais.repositories import release_repo


async def get_releases_by_document(session, doc_id):
    return await release_repo.get_releases_by_document(session, doc_id)


async def get_release_with_details(session, release_id):
    return await release_repo.get_release_with_details(session, release_id)


def _parse_version(version: str) -> int:
    """Converte uma versão para um inteiro sequencial.

    Aceita o formato antigo 'x.y.z' (usa o primeiro segmento como parte
    inteira) ou um inteiro simples 'n'. Retorna 0 se não for possível.
    """
    text = str(version or '').strip()
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        pass
    major = text.split('.')[0]
    try:
        return int(major)
    except ValueError:
        return 0


async def get_next_version(session, doc_id) -> str:
    releases = await release_repo.get_releases_by_document(session, doc_id)
    latest = releases[0] if releases else None
    if not latest or not latest.version:
        return '1'
    return str(_parse_version(latest.version) + 1)

