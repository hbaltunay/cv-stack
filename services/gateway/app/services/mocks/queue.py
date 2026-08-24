from datetime import UTC, datetime

from app.core.logging import get_logger

logger = get_logger("cvs")


class QueueMock:
    def start(self) -> None:
        logger.info("Kafka producer starting..")

    def shutdown(self) -> None:
        logger.info("Kafka Producer has been shutdown.")

    def publish(
        self,
        topic: str,
        image_bytes: bytes,  # noqa
        model_name: str,
        request_id: str | None = None,
        image_key: str | None = None,
    ) -> str:
        from app.services.mocks.cache import DATA

        logger.info(
            "The request to analyze was sent to Kafka.",
            extra={
                "params": {
                    "request_id": request_id,
                    "model_name": model_name,
                    "topic": topic,
                }
            },
        )

        DATA[f"result:{str(request_id)}"] = {
            "request_id": request_id,
            "model_name": model_name,
            "image_key": image_key,
            "status": "completed",
            "from_cache": False,
            "results": {"pred": [1]},
            "retry_count": "0",
            "produced_at": datetime.now(UTC).isoformat(),
        }

        return request_id
