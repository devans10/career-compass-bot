"""Central logging configuration used by the bot, scheduler, and storage modules."""

from __future__ import annotations

import logging
from datetime import datetime, timezone as dt_timezone
from logging.config import dictConfig
from typing import Optional
from zoneinfo import ZoneInfo


DEFAULT_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


class _TimezoneFormatter(logging.Formatter):
    """Formatter that applies an optional IANA timezone to timestamps."""

    def __init__(self, fmt: str, datefmt: Optional[str] = None, timezone: Optional[str] = None):
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.tzinfo = ZoneInfo(timezone) if timezone else None

    def formatTime(self, record, datefmt=None):  # noqa: N802 - override signature
        dt = self._to_datetime(record.created, self.tzinfo)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat()

    @staticmethod
    def _to_datetime(timestamp, tzinfo):
        base_dt = datetime.fromtimestamp(timestamp, tz=dt_timezone.utc)
        return base_dt.astimezone(tzinfo) if tzinfo else base_dt


def configure_logging(log_level: str = "INFO", timezone: Optional[str] = None) -> None:
    """Configure consistent console logging for all runtime contexts.

    This function is safe to call multiple times. It resets existing handlers to
    avoid duplicate output, configures a single stream handler with a
    timezone-aware formatter, and captures warnings so they appear in the same
    output stream. The configuration works for CLI executions and containerized
    deployments alike because it writes to standard output.
    """

    normalized_level = getattr(logging, log_level.upper(), logging.INFO)
    formatter_factory = {
        "()": _TimezoneFormatter,
        "fmt": DEFAULT_FORMAT,
        "datefmt": DEFAULT_DATE_FORMAT,
    }
    if timezone:
        formatter_factory["timezone"] = timezone

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"standard": formatter_factory},
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "level": normalized_level,
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {
                "handlers": ["console"],
                "level": normalized_level,
            },
        }
    )

    logging.captureWarnings(True)
