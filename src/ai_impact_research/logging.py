from __future__ import annotations

import logging

DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(level: str | int = "INFO") -> None:
    logging.basicConfig(level=level, format=DEFAULT_LOG_FORMAT, force=True)


def get_logger(name: str = "ai_impact_research") -> logging.Logger:
    return logging.getLogger(name)
