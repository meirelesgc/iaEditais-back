from redis.asyncio import ConnectionPool, Redis

from iaEditais.config import Settings


class Cache:
    def __init__(self, url: str, **kwargs):
        self.pool = ConnectionPool.from_url(url, decode_responses=True, **kwargs)
        self.client = Redis(connection_pool=self.pool)

    async def disconnect(self):
        await self.pool.disconnect()

    def get_client(self):
        return self.client


cache_url = Settings().get_redis_url()

cache = Cache(cache_url, max_connections=10)


async def get_cache():
    yield cache.get_client()
