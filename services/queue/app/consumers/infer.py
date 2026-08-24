import json
from typing import Any

import numpy as np
from confluent_kafka import Message

from app.consumers.base import BaseConsumer
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.telemetry import observe
from app.services import cache_service, triton_service

settings = get_settings()
logger = get_logger("cvs")


HEADERS = ["model_name", "request_id", "image_key"]


class InferConsumer(BaseConsumer):
    def __init__(self) -> None:
        super().__init__(
            consumer_type="INFER",
            topics=[settings.KAFKA_TOPIC_NAME],
        )

    @observe(name="Consumer", in_context=True)
    async def process_message(self, msg: Message) -> None:
        payload = self._parse_payload(msg)

        if payload["request_id"] is None or payload["model_name"] is None:
            return

        nparr = np.frombuffer(payload["image_bytes"], np.uint8)
        image_data = np.expand_dims(nparr, axis=0)

        try:
            await cache_service.set(
                key=f"Result:{payload['request_id']}",
                value={"status": "processing"},
            )

            result = await triton_service.infer(
                model_name=payload["model_name"],
                input_values=[image_data],
                request_id=payload["request_id"],
            )

            await cache_service.set(
                key=f"Result:{payload['request_id']}", value=result
            )

            if payload["image_key"]:
                await cache_service.set(
                    key=f"INFER:{payload['model_name']}:{payload['image_key']}",
                    value=result,
                )

        except Exception as e:
            logger.error(f"Error: {e}")

    def _parse_payload(self, msg: Message) -> dict[str, Any]:
        try:
            payload = {}
            headers = None

            msg_bytes = msg.value()
            payload["image_bytes"] = msg_bytes

            if msg.headers():
                headers = {
                    (k.decode("utf-8") if isinstance(k, bytes) else k): (
                        v.decode("utf-8") if isinstance(v, bytes) else v
                    )
                    for k, v in (
                        msg.headers.items()
                        if isinstance(msg.headers(), dict)
                        else (msg.headers() or [])
                    )
                }

            for req_header in HEADERS:
                header_value = headers.get(req_header)
                payload[req_header] = header_value

            return payload

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(
                "Payload parsing error",
                extra={
                    "params": {
                        "consumer_type": self.consumer_type,
                        "offset": msg.offset(),
                        "error": str(e),
                    }
                },
            )
            raise
