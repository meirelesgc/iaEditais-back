import redis.asyncio as redis

from iaEditais.core.settings import Settings

settings = Settings()


def get_cache():  # pragma: no cover
    client = redis.from_url(settings.CACHE_URL, decode_responses=True)
    yield client
    client.aclose()
