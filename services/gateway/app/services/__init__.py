from app.core.config import get_settings
from app.services.base import (
    CacheProvider,
    QueueProvider,
    StreamProvider,
    TritonProvider,
)
from app.services.cache import CacheService
from app.services.mocks import CacheMock, QueueMock, TritonMock
from app.services.queue import QueueService
from app.services.serve import TritonService

__all__ = ["CacheService", "TritonService", "QueueService"]

settings = get_settings()


class Services:
    def __init__(self) -> None:
        self._cache: CacheProvider | None = None
        self._queue: QueueProvider | None = None
        self._triton: TritonProvider | None = None
        self._stream: StreamProvider | None = None

    def get_cache(self) -> CacheProvider:
        if self._cache is None:
            self._cache = (
                CacheService()
                if settings.ENVIRONMENT == "production"
                or not settings.CACHE_MOCK
                else CacheMock()
            )

        return self._cache

    def get_queue(self) -> QueueProvider:
        if self._queue is None:
            self._queue = (
                QueueService()
                if settings.ENVIRONMENT == "production"
                or not settings.QUEUE_MOCK
                else QueueMock()
            )
        return self._queue

    def get_triton(self) -> TritonProvider:
        if self._triton is None:
            self._triton = (
                TritonService()
                if settings.ENVIRONMENT == "production"
                or not settings.TRITON_MOCK
                else TritonMock()
            )
        return self._triton


services = Services()
triton_service = services.get_triton()
cache_service = services.get_cache()
queue_service = services.get_queue()
