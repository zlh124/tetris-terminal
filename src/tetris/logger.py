"""Logging module for tetris-terminal."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import LoggingConfig

logger = logging.getLogger("tetris")

FMT: str = "[%(asctime)s] %(levelname)-8s %(message)s"
DATE_FMT: str = "%H:%M:%S"


def setup_from_config(config: LoggingConfig) -> None:
    """Configure the ``tetris`` logger from a :class:`LoggingConfig` instance.

    If logging is disabled in *config*, a ``NullHandler`` is added to suppress
    output. Otherwise log files are written to the configured directory with
    millisecond-precision timestamps.

    Args:
        config: Logging configuration (enabled, level, log_dir).
    """
    if not config.enabled:
        logger.addHandler(logging.NullHandler())
        return

    log_dir = Path(config.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    filename = datetime.now().strftime("tetris-%Y%m%d-%H%M%S.log")
    filepath = log_dir / filename

    handler = logging.FileHandler(filepath, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter(
            FMT.replace("%(asctime)s", "%(asctime)s.%(msecs)03d"),
            datefmt="%Y-%m-%d " + DATE_FMT,
        )
    )
    logger.addHandler(handler)
    logger.setLevel(config.level.upper())


logger.addHandler(logging.NullHandler())
