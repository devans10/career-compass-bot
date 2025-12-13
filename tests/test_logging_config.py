import logging
from logging import LogRecord

from src import logging_config


def _first_formatter() -> logging.Formatter:
    root = logging.getLogger()
    for handler in root.handlers:
        if handler.formatter:
            return handler.formatter
    raise AssertionError("No formatter configured on root logger")


def test_configure_logging_sets_root_handler():
    logging_config.configure_logging(log_level="DEBUG", timezone="UTC")

    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert any(isinstance(handler, logging.StreamHandler) for handler in root.handlers)


def test_configure_logging_with_timezone_formatting():
    logging_config.configure_logging(log_level="INFO", timezone="UTC")

    formatter = _first_formatter()
    record = LogRecord("tester", logging.INFO, __file__, 10, "message", args=(), exc_info=None, func="func")
    formatted = formatter.formatTime(record, logging_config.DEFAULT_DATE_FORMAT)

    assert formatted.endswith("+0000")
