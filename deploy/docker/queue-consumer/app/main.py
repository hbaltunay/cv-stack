import asyncio
import logging
import os
import signal
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("App")


class App:
    def __init__(self, pid_path: str = "/tmp/app.pid") -> None:
        self.pid_path = pid_path
        self.is_running = True
        self._write_pid()

    def _write_pid(self) -> None:
        pid = str(os.getpid())

        with open(self.pid_path, "w") as f:
            f.write(pid)

        logger.info(f"PID {pid} was written to file: {self.pid_path}")

    def handle_reload(self) -> None:
        logger.info(f"RELOAD. Refreshing code, PID {os.getpid()} is preserved.")

        os.execv(sys.executable, [sys.executable] + sys.argv)

    def handle_exit(self) -> None:
        logger.info("\nSTOP! The application is being closed.")
        self.is_running = False

    async def run(self) -> None:
        logger.info("The application is running...")
        try:
            while self.is_running:
                await asyncio.sleep(3)
        finally:
            if os.path.exists(self.pid_path):
                os.remove(self.pid_path)


async def main() -> None:
    app = App()
    loop = asyncio.get_running_loop()

    signals = {
        signal.SIGHUP: app.handle_reload,
        signal.SIGTERM: app.handle_exit,
        signal.SIGINT: app.handle_exit,
    }

    for sig, handler in signals.items():
        loop.add_signal_handler(sig, handler)

    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
