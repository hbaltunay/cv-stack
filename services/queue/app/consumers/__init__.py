from app.consumers.base import BaseConsumer
from app.consumers.infer import InferConsumer

__all__ = ["BaseConsumer", "InferConsumer"]


CONSUMER_TYPES: dict[str, BaseConsumer] = {
    "INFER": InferConsumer,
}
