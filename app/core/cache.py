import json
from typing import Optional
from datetime import datetime

import redis.asyncio as redis

from app.core.config import settings


class RedisLinkCache:
    """Кэш для ссылок на основе Redis."""

    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._prefix = "link:"

    async def connect(self) -> None:
        """Подключиться к Redis."""
        self._redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASS if settings.REDIS_PASS else None,
            decode_responses=True,
        )

    async def disconnect(self) -> None:
        """Отключиться от Redis."""
        if self._redis:
            await self._redis.close()

    async def get(self, key: str) -> Optional[dict]:
        """Получить ссылку из кэша."""
        if not self._redis:
            return None
        data = await self._redis.get(f"{self._prefix}{key}")
        if data:
            return json.loads(data)
        return None

    async def set(self, key: str, link_data: dict, ttl: int = 3600) -> None:
        """Положить ссылку в кэш с TTL."""
        if not self._redis:
            return
        await self._redis.set(
            f"{self._prefix}{key}",
            json.dumps(link_data, default=str),
            ex=ttl,
        )

    async def delete(self, key: str) -> None:
        """Удалить ссылку из кэша."""
        if not self._redis:
            return
        await self._redis.delete(f"{self._prefix}{key}")

    async def delete_by_pattern(self, pattern: str) -> None:
        """Удалить ссылки по паттерну."""
        if not self._redis:
            return
        async for key in self._redis.scan_iter(f"{self._prefix}{pattern}"):
            await self._redis.delete(key)

    async def clear(self) -> None:
        """Очистить весь кэш ссылок."""
        if not self._redis:
            return
        await self.delete_by_pattern("*")

    async def get_stats(self) -> dict:
        """Статистика кэша."""
        if not self._redis:
            return {"size": 0, "connected": False}
        
        info = await self._redis.info("stats")
        keys_count = await self._redis.dbsize()
        
        return {
            "size": keys_count,
            "connected": True,
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
        }


# Глобальный экземпляр кэша
link_cache = RedisLinkCache()
