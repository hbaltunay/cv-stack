import logging
import os
import signal
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("App")

PID_FILE = "/tmp/app.pid"


def trigger() -> None:
    if not os.path.exists(PID_FILE):
        logger.error(f"PID file not found: {PID_FILE}")
        sys.exit(1)

    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())

        os.kill(pid, signal.SIGHUP)
        logger.info(f"Reload signal sent for PID {pid}.")

    except ProcessLookupError:
        logger.error(f"PID {pid} not found. The process may not be running.")
    except Exception as e:
        logger.error(f"An error occurred: {e}")


if __name__ == "__main__":
    trigger()
