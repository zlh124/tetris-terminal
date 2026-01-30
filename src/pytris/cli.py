import curses
import sys

from .pytris import Pytris


def wrapper(stdscr: curses.window):
    tetris = Pytris(stdscr)
    tetris.main()


def main() -> int:
    curses.wrapper(wrapper)
    return 0


if __name__ == "__main__":
    sys.exit(main())
