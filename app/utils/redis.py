from typing import Optional

import aioredis


class BaseRedis:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.host = host
        self.port = port
        self.db = db

        self._redis: Optional[aioredis.Redis] = None

    @property
    def closed(self):
        return not self._redis or self._redis.closed

    async def connect(self):
        if self.closed:
            self._redis = await aioredis.from_url(
                f"redis://{self.host}",
                encoding="utf-8",
                port=self.port,
                db=self.db
            )

    async def disconnect(self):
        if self._redis:
            await self._redis.connection.disconnect()

    @property
    def redis(self) -> aioredis.Redis:
        if self._redis:
            return self._redis
        raise RuntimeError("Connection is not opened!")
