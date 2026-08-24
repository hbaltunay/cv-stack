import json
from typing import Any

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.telemetry import observe

settings = get_settings()
logger = get_logger("cvs")


class CacheService:
    def __init__(self) -> None:
        """Initializes the CacheService instance."""
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        """Returns the active Redis client.

        Returns:
            redis.Redis: The configured Redis client instance.

        Raises:
            RuntimeError: If the client is accessed before initialization.
        """
        if self._client is None:
            raise RuntimeError(
                "Redis client is not initialized. Call start() first."
            )

        return self._client

    async def start(self) -> None:
        """Initializes the Redis connection pool and verifies connectivity."""
        try:
            pool = ConnectionPool.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
            )
            self._client = redis.Redis(connection_pool=pool)

            await self._client.ping()

            logger.info("Redis connection established")

        except Exception as e:
            logger.error(
                "Redis connection failed", extra={"params": {"error": str(e)}}
            )
            self._client = None

    async def shutdown(self) -> None:
        """Terminates the Redis connection and cleans up resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

            logger.info("Redis connection has been terminated.")

    @observe(name="Cache", method="Get")
    async def get(self, key: str) -> dict[str, Any] | None:
        """Retrieves data from Redis by key.

        Args:
            key (str): The cache key.
            params (dict[str, Any]): Contextual parameters for logging.

        Returns:
            dict[str, Any] | None: The cached data, or None if not found.
        """
        try:
            value = await self.client.get(key)

            if value is None:
                logger.info("Cache miss")
                return None

            logger.info("Cache hit")
            return json.loads(value)

        except Exception as e:
            logger.error("Cache get error", extra={"params": {"error": str(e)}})
            return None

    @observe(name="Cache", method="Set")
    async def set(self, key: str, value: dict[str, Any]) -> None:
        """Stores data in Redis with a TTL.

        Args:
            key (str): The cache key.
            value (dict[str, Any]): The data to store.
        """
        try:
            await self.client.set(key, json.dumps(value), ex=settings.REDIS_TTL)

            logger.info("Cache SET success")

        except Exception as e:
            logger.error(
                "Cache SET error",
                extra={
                    "params": {
                        "error": str(e),
                    }
                },
            )
