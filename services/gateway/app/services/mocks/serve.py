from typing import Any

from app.core.logging import get_logger
from app.core.telemetry import observe

logger = get_logger("cvs")


class TritonMock:
    async def start(self) -> None:
        logger.info("Triton Server Inference Starting.")

    async def shutdown(self) -> None:
        logger.info("Triton connection has been terminated.")

    async def health_check(self) -> bool: ...

    @observe(name="Triton", method="Inference")
    async def infer(
        self,
        model_name: str,
        input_values: bytes,
        request_id: str,
    ) -> dict[str, Any]:
        return {
            "model": model_name,
            "results": "Mock",
        }

    @observe(name="Triton", method="Serve")
    async def serve(
        self,
        model_name: str,
        image_bytes: bytes,
        request_id: str,
    ) -> dict[str, Any]:
        return {
            "model": model_name,
            "results": "Mock",
        }
