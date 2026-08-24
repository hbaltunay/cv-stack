from typing import Any, Protocol


class TritonProvider(Protocol):
    async def start(self) -> None: ...

    async def shutdown(self) -> None: ...

    async def health_check(self) -> bool: ...

    async def infer(
        self,
        model_name: str,
        input_values: bytes,
        request_id: str,
    ) -> dict[str, Any]: ...


class CacheProvider(Protocol):
    async def start(self, **kwargs: Any) -> None: ...

    async def shutdown(self) -> None: ...

    async def get(self, key: str) -> dict[str, Any] | None: ...

    async def set(self, key: str, value: dict[str, Any]) -> None: ...


class QueueProvider(Protocol):
    def start(self) -> None: ...

    def shutdown(self) -> None: ...

    def publish(
        self,
        topic: str,
        image_bytes: bytes,
        model_name: str,
        request_id: str | None = None,
    ) -> str: ...
