import json
import logging
import logging.config
import sys
from copy import copy
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.core.utils import ANSI, LEVEL_COLORS

settings = get_settings()


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "environment": settings.ENVIRONMENT,
            "app_version": settings.APP_VERSION,
        }

        params = getattr(record, "params", None)

        if isinstance(params, dict):
            log_data.update(params)

        if record.exc_info:
            log_data["stack_trace"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class StreamFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        recopy = copy(record)
        msg = recopy.getMessage()
        params = getattr(recopy, "params", None)
        if isinstance(params, dict) and params.get("duration_ms", None):
            msg += f" (Duration: {params.get('duration_ms')}) "
        recopy.msg = msg
        return super().format(recopy)

    def formatMessage(self, record: logging.LogRecord) -> str:  # noqa
        recopy = copy(record)
        color = LEVEL_COLORS.get(recopy.levelno, ANSI.BLUE)
        recopy.levelname = (
            f"{color}["
            + f"{recopy.levelname.center(10):.10}"
            + f"]{ANSI.RESET} :"
        )

        return super().formatMessage(recopy)


def setup_logging(log_level: str = "INFO") -> None:
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {"()": JSONFormatter},
            "stream": {
                "()": StreamFormatter,
                "fmt": "%(levelname)s %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json"
                if settings.ENVIRONMENT == "production"
                else "stream",
                "stream": sys.stdout,
            },
        },
        "loggers": {
            "cvs": {
                "handlers": ["console"],
                "level": log_level.upper(),
            },
        },
    }

    logging.config.dictConfig(log_config)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
