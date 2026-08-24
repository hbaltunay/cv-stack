import asyncio
import os
import signal
import sys

from app.consumers import CONSUMER_TYPES, BaseConsumer
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.telemetry import setup_telemetry
from app.services import cache_service, triton_service

setup_telemetry()

settings = get_settings()

setup_logging(settings.LOG_LEVEL)
logger = get_logger("cvs")


class App:
    def __init__(self, pid_path: str = "/tmp/app.pid") -> None:
        self.pid_path = pid_path
        self.is_running = True
        self._write_pid()
        self.consumers: dict[str, BaseConsumer] = {}

    def _write_pid(self) -> None:
        pid = str(os.getpid())

        with open(self.pid_path, "w") as f:
            f.write(pid)

        logger.info(f"PID {pid} was written to file: {self.pid_path}")

    def handle_reload(self) -> None:
        logger.info(f"RELOAD. Refreshing code, PID {os.getpid()} is preserved.")

        os.execv(sys.executable, [sys.executable] + sys.argv)

    def handle_exit(self) -> None:
        logger.info("STOP! The application is being closed.")
        self.is_running = False

    async def shutdown(self, sig: signal.Signals) -> None:
        logger.info(
            "Shutdown signal received.",
            extra={"params": {"signal": sig.name}},
        )
        for consumer in self.consumers.values():
            await consumer.stop()

        await triton_service.shutdown()
        await cache_service.shutdown()

    async def start(self) -> None:
        logger.info("Services are being started..")

        await triton_service.start()
        await cache_service.start()

        logger.info("Services are ready.")

    async def run(self) -> None:
        logger.info("The application is running...")

        async def run_with_guard(consumer_type: str) -> None:
            try:
                if consumer_type in self.consumers:
                    consumer_instance = self.consumers.get(consumer_type)
                else:
                    consumer_instance = CONSUMER_TYPES.get(consumer_type)

                if consumer_instance is None:
                    raise NotImplementedError

                consumer = consumer_instance()  # ty:ignore[call-non-callable]
                self.consumers[consumer_type] = consumer

                await consumer.start()
                await consumer.run()

            except Exception as e:
                logger.error(
                    f"Consumer unexpectedly stopped working. (Error: {e})",
                    extra={
                        "params": {
                            "consumer_type": consumer_type,
                            "error": str(e),
                        }
                    },
                )

        await asyncio.gather(
            run_with_guard("INFER"),
        )


async def main() -> None:

    app = App()
    loop = asyncio.get_running_loop()

    signals = {
        signal.SIGHUP: app.handle_reload,
        signal.SIGTERM: app.handle_exit,
        signal.SIGINT: app.handle_exit,
    }

    for sig, handler in signals.items():
        loop.add_signal_handler(
            sig,
            lambda s=sig: asyncio.create_task(app.shutdown(s)),
        )
        # It will be removed from the production environment.
        loop.add_signal_handler(sig, handler)

    await app.start()

    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
