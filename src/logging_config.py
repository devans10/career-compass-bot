import logging
from typing import Optional


def configure_logging(log_level: str = "INFO", timezone: Optional[str] = None) -> None:
    """Configure application-wide logging settings.

    A simple formatter is provided to make it easier to adjust or extend later.
    """

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )

    if timezone:
        logging.captureWarnings(True)
