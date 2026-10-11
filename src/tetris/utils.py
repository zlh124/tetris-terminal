"""Utility helpers used across tetris-terminal."""

from __future__ import annotations

import time
from collections.abc import Callable
from functools import wraps
from importlib.metadata import PackageNotFoundError, version
from typing import Any, TypeVar

from .logger import logger

F = TypeVar("F", bound=Callable[..., Any])


def timed(func: F) -> F:
    """Decorator that logs function execution time in milliseconds.

    Args:
        func: The function to wrap.

    Returns:
        The wrapped function with timing instrumentation.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            logger.debug(
                "%s.%s took %.3f ms", func.__module__, func.__qualname__, elapsed
            )

    return wrapper  # type: ignore[return-value]


def get_version() -> str:
    """Return the installed package version.

    Returns:
        Version string (e.g. ``"1.2.3"``) or ``"0.0.0-dev"`` if not installed.
    """
    try:
        return version("tetris-terminal")
    except PackageNotFoundError:
        return "0.0.0-dev"
