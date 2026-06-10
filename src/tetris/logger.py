"""Logging module for tetris."""

from __future__ import annotations


import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import LoggingConfig

logger = logging.getLogger("tetris")

FMT = "[%(asctime)s] %(levelname)-8s %(message)s"
DATE_FMT = "%H:%M:%S"


def setup_from_config(config: LoggingConfig) -> None:
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
