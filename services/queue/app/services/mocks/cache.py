import threading
import time
from typing import Any

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

        except TypeError as e:
            logger.error(
                "An unexpected keyword argument was received.",
                extra={"params": {"error": str(e)}},
            )
            self.client = None

    async def shutdown(self) -> None:
        self.client = None
        TEVENT.set()
        self.thread.join()

        logger.info("Redis connection has been terminated.")

    @observe(name="Cache", method="Get")
    async def get(self, key: str) -> dict[str, Any] | None:
        try:
            value = self.client.get(key)

            if value is None:
                logger.info("Cache miss", extra={"params": {"key": key}})
                return None

            m_value = value.copy()
            m_value.pop("time")

            logger.info(
                f"Cache hit. ({key}: {m_value})", extra={"params": {"key": key}}
            )
            return value

        except Exception as e:
            logger.error(
                f"Cache get error (Error: {e})",
                extra={"params": {"key": key, "error": str(e)}},
            )
            return None

    async def set(self, key: str, value: dict[str, Any]) -> None:
        try:
            value["time"] = time.time()
            self.client[key] = value

            m_value = value.copy()
            m_value.pop("time")

            logger.info(
                f"Cache SET success. ({key}: {m_value})",
                extra={
                    "params": {
                        "key": key,
                        # "ttl": settings.REDIS_TTL,
                    }
                },
            )

        except Exception as e:
            logger.error(
                f"Cache SET error (Error: {e})",
                extra={"params": {"key": key, "error": str(e)}},
            )
