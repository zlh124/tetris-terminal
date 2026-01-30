import curses
import sys

from .tetris import Tetris


def wrapper(stdscr: curses.window):
    tetris = Tetris(stdscr)
    tetris.main()


def main() -> int:
    curses.wrapper(wrapper)
    return 0


if __name__ == "__main__":
    sys.exit(main())
