import asyncio
from abc import ABC, abstractmethod
from asyncio import AbstractEventLoop
from functools import partial

from confluent_kafka import (
    Consumer,
    Message,
    Producer,
)

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger("cvs")


class BaseConsumer(ABC):
    def __init__(self, consumer_type: str, topics: list[str]) -> None:
        self.consumer_type = consumer_type
        self.topics = topics
        self._consumer: Consumer | None = None
        self._producer: Producer | None = None
        self._running = False
        self._queue = asyncio.Queue(maxsize=100)

    def _build_consumer(self) -> Consumer:
        return Consumer(
            {
                "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                "group.id": settings.KAFKA_CONSUMER_GROUP_ID,
                "auto.offset.reset": settings.KAFKA_AUTO_OFFSET_RESET,
                "enable.auto.commit": False,
                "max.poll.interval.ms": settings.KAFKA_MAX_POLL_INTERVAL_MS,
                "session.timeout.ms": settings.KAFKA_SESSION_TIMEOUT_MS,
                "heartbeat.interval.ms": settings.KAFKA_HEARTBEAT_INTERVAL_MS,
            }
        )

    def _build_producer(self) -> Producer:
        return Producer({"bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS})

    async def start(self) -> None:
        self._consumer = self._build_consumer()
        self._producer = self._build_producer()
        self._consumer.subscribe(self.topics)
        self._running = True

        logger.info(
            "Consumer has been launched.",
            extra={
                "params": {
                    "consumer_type": self.consumer_type,
                    "topics": self.topics,
                }
            },
        )

    async def stop(self) -> None:
        self._running = False

        if self._consumer is not None:
            self._consumer.commit(asynchronous=False)
            self._consumer.close()

        if self._producer is not None:
            self._producer.flush()

        logger.info(
            "Consumer has been discontinued.",
            extra={"params": {"consumer_type": self.consumer_type}},
        )

    async def run(self) -> None:
        if self._consumer is None:
            raise RuntimeError(
                "The consumer has not been initialized. Call start() first."
            )

        loop = asyncio.get_running_loop()

        poll_task = asyncio.create_task(self._poll(loop))

        process_task = asyncio.create_task(self._process(loop))

        await asyncio.gather(poll_task, process_task)

    async def _poll(self, loop: AbstractEventLoop) -> None:

        while self._running:
            msg: Message | None = await loop.run_in_executor(
                None,
                self._consumer.poll,
                1.0,
            )

            if msg is None:
                continue

            if msg.error():
                await self._handle_kafka_error(msg)
                continue

            await self._queue.put(msg)

    async def _process(self, loop: AbstractEventLoop) -> None:

        while self._running:
            msg = await self._queue.get()

            await self._handle_message(msg)

            commit_func = partial(self._consumer.commit, asynchronous=False)

            await loop.run_in_executor(None, commit_func)

    async def _handle_message(self, msg: Message) -> None:
        topic = msg.topic()
        partition = msg.partition()
        offset = msg.offset()

        logger.info(
            "Message received.",
            extra={
                "params": {
                    "consumer_type": self.consumer_type,
                    "topic": topic,
                    "partition": partition,
                    "offset": offset,
                }
            },
        )

        try:
            await self.process_message(msg)

            logger.info(
                "Message processed, offset committed.",
                extra={
                    "params": {
                        "consumer_type": self.consumer_type,
                        "topic": topic,
                        "partition": partition,
                        "offset": offset,
                    }
                },
            )

        except Exception as e:
            logger.error(
                "Message processing error",
                extra={
                    "params": {
                        "consumer_type": self.consumer_type,
                        "topic": topic,
                        "partition": partition,
                        "offset": offset,
                        "error": str(e),
                    }
                },
            )

    @abstractmethod
    async def process_message(self, msg: Message) -> None: ...
