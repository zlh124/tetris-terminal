"""Utility helpers used across tetris-terminal."""

from __future__ import annotations

import curses
import time
from functools import wraps
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Callable, TypeVar

from .logger import logger
from .config import DisplayConfig

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


def rotate_points(
    points: list[tuple[int, int]],
    center: list[int | tuple[int, int]],
    ccw: bool = False,
) -> list[tuple[int, int]]:
    """Rotate a list of (row, col) points by 90 degrees around a center.

    Args:
        points: The points to rotate, each as ``(row, col)``.
        center: Either ``[row, col]`` or ``[(row0, row1), (col0, col1)]``
            for an averaged center (used by I-piece double-axis rotation).
        ccw: If ``True``, rotate counter-clockwise; otherwise clockwise.

    Returns:
        New list of rotated ``(row, col)`` tuples.
    """
    if isinstance(center[0], (list, tuple)):
        cr = (center[0][0] + center[0][1]) / 2.0
        cc = (center[1][0] + center[1][1]) / 2.0  # type: ignore[index]
    else:
        cr, cc = float(center[0]), float(center[1])  # type: ignore[index]

    rotated_points: list[tuple[int, int]] = []

    for r, c in points:
        rel_r = r - cr
        rel_c = c - cc
        new_rel_r = -rel_c if ccw else rel_c
        new_rel_c = rel_r if ccw else -rel_r
        new_r = int(new_rel_r + cr)
        new_c = int(new_rel_c + cc)

        rotated_points.append((new_r, new_c))

    return rotated_points


def get_version() -> str:
    """Return the installed package version.

    Returns:
        Version string (e.g. ``"1.2.3"``) or ``"0.0.0-dev"`` if not installed.
    """
    try:
        return version("tetris-terminal")
    except PackageNotFoundError:
        return "0.0.0-dev"


def safe_addstr(win: curses.window, y: int, x: int, s: str) -> None:
    """Call ``win.addstr`` while silently ignoring ``curses.error``.

    Args:
        win: The curses window to draw on.
        y: Row position.
        x: Column position.
        s: String to render.
    """
    try:
        win.addstr(y, x, s)
    except curses.error:
        pass


def draw_win_border(
    win: curses.window,
    display: DisplayConfig,
    ls: str | None = None,
    rs: str | None = None,
    ts: str | None = None,
    bs: str | None = None,
    tl: str | None = None,
    tr: str | None = None,
    bl: str | None = None,
    br: str | None = None,
) -> None:
    """Draw a window border using display config characters, with optional per-call overrides.

    Each border side or corner defaults to the value from *display* but can be
    individually replaced by the corresponding keyword argument.

    Args:
        win: The curses window to draw on.
        display: Border character configuration.
        ls: Left-side vertical border (default: ``display.bd_v``).
        rs: Right-side vertical border (default: ``display.bd_v``).
        ts: Top horizontal border (default: ``display.bd_h``).
        bs: Bottom horizontal border (default: ``display.bd_h``).
        tl: Top-left corner (default: ``display.bd_tl``).
        tr: Top-right corner (default: ``display.bd_tr``).
        bl: Bottom-left corner (default: ``display.bd_bl``).
        br: Bottom-right corner (default: ``display.bd_br``).
    """
    _ls = ls if ls is not None else display.bd_v
    _rs = rs if rs is not None else display.bd_v
    _ts = ts if ts is not None else display.bd_h
    _bs = bs if bs is not None else display.bd_h
    _tl = tl if tl is not None else display.bd_tl
    _tr = tr if tr is not None else display.bd_tr
    _bl = bl if bl is not None else display.bd_bl
    _br = br if br is not None else display.bd_br

    height, width = win.getmaxyx()
    safe_addstr(win, 0, 0, _tl)
    safe_addstr(win, 0, width - 1, _tr)
    safe_addstr(win, height - 1, 0, _bl)
    safe_addstr(win, height - 1, width - 1, _br)

    safe_addstr(win, 0, 1, _ts * (width - 2))
    safe_addstr(win, height - 1, 1, _bs * (width - 2))

    for i in range(1, height - 1):
        safe_addstr(win, i, 0, _ls)
        safe_addstr(win, i, width - 1, _rs)


def clear_win_without_border(win: curses.window, start_row: int = 1) -> None:
    """Clear the interior of a curses window, leaving its border intact.

    Args:
        win: The curses window to clear.
        start_row: First interior row to clear (default ``1``, below top border).
    """
    r, c = win.getmaxyx()
    r -= 1
    c -= 2
    for row in range(start_row, r):
        win.addstr(row, 1, " " * c)
