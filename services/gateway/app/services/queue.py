from confluent_kafka import Message, Producer

from app.core.config import get_settings
from app.core.exceptions import QueueServiceException
from app.core.logging import get_logger
from app.core.telemetry import observe, trace_inject

settings = get_settings()
logger = get_logger("cvs")


class QueueService:
    def __init__(self) -> None:
        self._producer: Producer | None = None

    @property
    def producer(self) -> Producer:
        if self._producer is None:
            raise RuntimeError(
                "The producer hasn't been started. Call start() first."
            )
        return self._producer

    def start(self) -> None:
        try:
            self._producer = Producer(
                {
                    "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                    # "acks": "all",
                    # "retries": 3,
                    # "retry.backoff.ms": 500,
                    # "delivery.timeout.ms": 30_000,
                    # "enable.idempotence": True,
                    "message.max.bytes": 10485760,  # 10MB
                }
            )
            logger.info("Kafka producer starting.")

        except Exception as err:
            logger.error("Kafka producer could not be started.")
            raise QueueServiceException(detail=f"Queue Error: {err}") from err

    def shutdown(self) -> None:
        try:
            if self._producer is not None:
                self._producer.flush()
                logger.info("Kafka Producer has been shutdown.")
        except Exception as err:
            logger.error("Kafka producer could not be shutdown.")
            raise QueueServiceException(detail=f"Queue Error: {err}") from err

    def _delivery_callback(self, err: str, msg: Message) -> None:
        if err:
            logger.error(
                "Kafka message delivery error",
                extra={
                    "params": {
                        "topic": msg.topic(),
                        "error": str(err),
                    }
                },
            )
            raise QueueServiceException(detail=f"Queue Error: {err}")

        logger.info(
            "Kafka message has been delivered.",
            extra={
                "params": {
                    "topic": msg.topic(),
                    "partition": msg.partition(),
                    "offset": msg.offset(),
                }
            },
        )

    def _produce(
        self,
        topic: str,
        value: bytes,
        key: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.producer.produce(
            topic=topic,
            value=value,
            key=key.encode(),
            headers={k: v.encode() for k, v in (headers or {}).items()},
            on_delivery=self._delivery_callback,
        )
        self.producer.poll(0)

    @observe(name="Queue", method="Produce")
    def publish(
        self,
        topic: str,
        image_bytes: bytes,
        model_name: str,
        request_id: str,
        image_key: str | None = None,
    ) -> str:
        try:
            headers = trace_inject(request_id)
            headers["model_name"] = model_name
            headers["image_key"] = image_key

            self._produce(
                topic=topic,
                key=request_id,
                value=image_bytes,
                headers=headers,
            )

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

            return request_id

        except Exception as err:
            logger.error("The message could not be published.")
            raise QueueServiceException(detail=f"Queue Error: {err}") from err
