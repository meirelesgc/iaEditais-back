from iaEditais.repositories import release_repo


async def get_releases_by_document(session, doc_id):
    return await release_repo.get_releases_by_document(session, doc_id)


async def get_release_with_details(session, release_id):
    return await release_repo.get_release_with_details(session, release_id)


def bump_version(version: str, bump: str) -> str:
    parts = version.split('.')
    major, minor, patch = (
        int(parts[0]),
        int(parts[1]) if len(parts) > 1 else 0,
        int(parts[2]) if len(parts) > 2 else 0,
    )
    if bump == 'major':
        major += 1
        minor = 0
        patch = 0
    elif bump == 'minor':
        minor += 1
        patch = 0
    else:
        patch += 1
    return f'{major}.{minor}.{patch}'


async def get_next_version(session, doc_id, bump: str = 'patch') -> str:
    releases = await release_repo.get_releases_by_document(session, doc_id)
    latest = releases[0] if releases else None
    if not latest or not latest.version:
        return '1.0.0'
    return bump_version(latest.version, bump)

