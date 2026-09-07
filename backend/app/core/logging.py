"""Structured application logging with request correlation support."""

import logging
from contextvars import ContextVar
from pathlib import Path

from backend.app.core.config import PROJECT_ROOT, Settings

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")


class RequestContextFilter(logging.Filter):
    """Add the current request identifier to each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        return True


def configure_logging(settings: Settings) -> None:
    """Configure console and file handlers once during application startup."""
    log_directory = PROJECT_ROOT / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s"
    )
    context_filter = RequestContextFilter()

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())
    root_logger.handlers.clear()

    for handler in (
        logging.StreamHandler(),
        logging.FileHandler(Path(log_directory, "app.log"), encoding="utf-8"),
    ):
        handler.setFormatter(formatter)
        handler.addFilter(context_filter)
        root_logger.addHandler(handler)
