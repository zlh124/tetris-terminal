"""utils"""

from __future__ import annotations

import curses
import time
from functools import wraps
from importlib.metadata import PackageNotFoundError, version
from typing import Callable

from .logger import logger
from .config import DisplayConfig


def timed(func: Callable) -> Callable:
    """Decorator that logs function execution time in milliseconds."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            logger.debug(
                "%s.%s took %.3f ms", func.__module__, func.__qualname__, elapsed
            )

    return wrapper


def rotate_points(
    points: list[tuple[int, int]],
    center: list[int | tuple[int, int]],
    ccw: bool = False,
) -> list[tuple[int, int]]:
    """rotate the point 90 degree"""
    if isinstance(center[0], (list, tuple)):
        cr = (center[0][0] + center[0][1]) / 2.0
        cc = (center[1][0] + center[1][1]) / 2.0  # type: ignore
    else:
        cr, cc = float(center[0]), float(center[1])  # type: ignore

    rotated_points = []

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
    """get version"""
    try:
        return version("tetris-terminal")
    except PackageNotFoundError:
        return "0.0.0-dev"


def safe_addstr(win: curses.window, y: int, x: int, s: str) -> None:
    """addstr but ignore curses.error"""
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
    """draw window border using display config, with optional per-call overrides"""
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
    """clear window without border"""
    r, c = win.getmaxyx()
    r -= 1
    c -= 2
    for row in range(start_row, r):
        win.addstr(row, 1, " " * c)
