"""utils"""

import curses
from importlib.metadata import PackageNotFoundError, version

from tetris.constants import BD_BL, BD_BR, BD_H, BD_TL, BD_TR, BD_V


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
    """addstr but ignore curses.error

    :param win: curses.window
    :param y: y coordinate
    :param x: x coordinate
    :param s: string to add
    :rtype: None
    """
    try:
        win.addstr(y, x, s)
    except curses.error:
        pass


def draw_win_border(
    win: curses.window,
    ls: str = BD_V,
    rs: str = BD_V,
    ts: str = BD_H,
    bs: str = BD_H,
    tl: str = BD_TL,
    tr: str = BD_TR,
    bl: str = BD_BL,
    br: str = BD_BR,
) -> None:
    """draw window border

    :param win: curses.window
    :param ls: left side character
    :param rs: right side character
    :param ts: top side character
    :param bs: bottom side character
    :param tl: top left character
    :param tr: top right character
    :param bl: bottom left character
    :param br: bottom right character
    """
    height, width = win.getmaxyx()
    safe_addstr(win, 0, 0, tl)
    safe_addstr(win, 0, width - 1, tr)
    safe_addstr(win, height - 1, 0, bl)
    safe_addstr(win, height - 1, width - 1, br)

    safe_addstr(win, 0, 1, ts * (width - 2))
    safe_addstr(win, height - 1, 1, bs * (width - 2))

    for i in range(1, height - 1):
        safe_addstr(win, i, 0, ls)
        safe_addstr(win, i, width - 1, rs)
