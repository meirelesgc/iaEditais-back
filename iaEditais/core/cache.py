import json
from typing import Optional

import redis.asyncio as redis

from iaEditais.core.settings import Settings

settings = Settings()


async def get_cache():
    yield redis.from_url(settings.CACHE_URL, decode_responses=True)


async def publish_update(
    cache: redis.Redis,
    type_: str,
    message: str,
    details: Optional[dict] = None,
    channel: str = 'public',
):
    payload = {'type': type_, 'message': message, 'details': details or {}}
    await cache.publish(channel, json.dumps(payload))
