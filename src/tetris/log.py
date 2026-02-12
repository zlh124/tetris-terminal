import os
import logging

import logging.handlers
from pathlib import Path


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """output log to file"""
    logger = logging.getLogger("tetris")
    logger.setLevel(level)
    logger.handlers.clear()
    if os.getenv("TETRIS_DEV_MODE", "0") == "1":
        log_dir = Path(__file__).parent.parent.parent / ".log"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "tetris.log"

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            mode="w",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(file_handler)

        logger.info(f"Logging initialized. File: {log_file}")
    return logger
