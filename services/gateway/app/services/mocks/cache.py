import threading
import time
from typing import Any

from app.core.exceptions import CacheServiceException
from app.core.logging import get_logger
from app.core.telemetry import observe

logger = get_logger("cvs")

DATA = {}
TLOCK = threading.Lock()
TEVENT = threading.Event()


class CacheMock:
    def __init__(self, expire: int = 10) -> None:
        self.expire = expire
        self.thread = threading.Thread(target=self.expire_cache, daemon=True)
        self.thread.start()

    @staticmethod
    def expire_cache() -> None:
        while not TEVENT.is_set():
            with TLOCK:
                data_copy = DATA.copy()

            delete_keys = []

            for key, value in data_copy.items():
                if value.get("time") and time.time() - value["time"] >= 10:
                    delete_keys.append(key)

            if delete_keys:
                with TLOCK:
                    for delete_key in delete_keys:
                        if delete_key in DATA:
                            del DATA[delete_key]
                            logger.info(
                                f"This request cache has expired. "
                                f"({delete_key})"
                            )

            TEVENT.wait(timeout=2)

    async def start(self, **kwargs: Any) -> None:  # noqa
        try:
            self.client = DATA
            logger.info("Redis connection established")

        except TypeError as err:
            logger.error(
                "An unexpected keyword argument was received.",
                extra={"params": {"error": str(err)}},
            )
            self.client = None

            raise CacheServiceException(detail=f"Cache Error: {err}") from err

    async def shutdown(self) -> None:
        try:
            self.client = None
            TEVENT.set()
            self.thread.join()

            logger.info("Redis connection has been terminated.")

        except Exception as err:
            logger.error("The Redis connection could not be terminated.")
            raise CacheServiceException(detail=f"Cache Error: {err}") from err

    @observe(name="Cache", method="Get")
    async def get(self, key: str) -> dict[str, Any] | None:
        try:
            value = self.client.get(key)

            if value is None:
                logger.info("Cache miss", extra={"params": {"key": key}})
                return None

            logger.info("Cache hit", extra={"params": {"key": key}})
            return value

        except Exception as err:
            logger.error(
                "Cache get error",
                extra={"params": {"key": key, "error": str(err)}},
            )
            raise CacheServiceException(detail=f"Cache Error: {err}") from err

    async def set(self, key: str, value: dict[str, Any]) -> None:
        try:
            value["time"] = time.time()
            self.client[key] = value

            logger.info(
                "Cache SET success",
                extra={
                    "params": {
                        "key": key,
                        # "ttl": settings.REDIS_TTL,
                    }
                },
            )

        except Exception as err:
            logger.error(
                "Cache SET error",
                extra={"params": {"key": key, "error": str(err)}},
            )
            raise CacheServiceException(detail=f"Cache Error: {err}") from err
