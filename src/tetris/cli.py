"""program entrance"""

import argparse
import curses
import sys

from tetris.config import Config
from tetris.logger import logger, setup_from_config
from tetris.menu import Menu, Sections
from tetris.settlement import Settlement
from tetris.tetris import Tetris, GameMode
from tetris.utils import get_version


def make_wrapper(disable_config: bool = False):
    def wrapper(stdscr: curses.window) -> int:
        config = Config() if disable_config else Config.load()
        setup_from_config(config.logging)

        curses.update_lines_cols()
        if curses.LINES < config.display.window_rows or curses.COLS < config.display.window_cols:
            raise RuntimeError(
                f"tetris-terminal needs {config.display.window_rows} rows, and {config.display.window_cols} cols terminal size."
            )

        curses.use_default_colors()
        curses.curs_set(False)
        while True:
            section = Menu(stdscr, config).main()
            if Sections(section) == Sections.QUIT:
                return 0

            game_mode = GameMode(section)

            set_msg = Tetris(stdscr, game_mode, config).main()
            if Settlement(stdscr, set_msg, config).main() == 0:
                break
        return 0

    return wrapper


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Tetris Terminal",
        epilog=f"Tetris Terminal v{get_version()}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--version", action="version", version=f"v{get_version()}")
    parser.add_argument(
        "--generate-config",
        action="store_true",
        help=f"generate a default config file at {Config.config_path()} and exit",
    )
    parser.add_argument(
        "--disable-config",
        action="store_true",
        help="ignore config file and run with defaults",
    )

    args = parser.parse_args()

    if args.generate_config:
        try:
            path = Config.generate_config()
        except FileExistsError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        print(f"Config file created at: {path}")
        return 0

    return curses.wrapper(make_wrapper(disable_config=args.disable_config))
