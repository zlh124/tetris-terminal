"""program entrance"""

import argparse
import curses


from tetris.constants import WINDOW_COLS, WINDOW_ROWS
from tetris.menu import Menu, Sections
from tetris.settlement import Settlement
from tetris.tetris import Tetris, GameMode
from tetris.utils import get_version


def wrapper(stdscr: curses.window) -> int:
    curses.update_lines_cols()
    if curses.LINES < WINDOW_ROWS or curses.COLS < WINDOW_COLS:
        raise RuntimeError(
            f"tetris-terminal needs {WINDOW_ROWS} rows, and {WINDOW_COLS} cols terminal size."
        )

    curses.use_default_colors()
    curses.curs_set(False)
    while True:
        section = Menu(stdscr).main()
        if Sections(section) == Sections.QUIT:
            return 0

        game_mode = GameMode(section)

        set_msg = Tetris(stdscr, game_mode).main()
        if Settlement(stdscr, set_msg).main() == 0:
            break
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Tetris Terminal",
        epilog=f"Tetris Terminal v{get_version()}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--version", action="version", version=f"v{get_version()}")

    parser.parse_args()

    return curses.wrapper(wrapper)
