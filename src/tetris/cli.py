import curses
import sys

from tetris import Tetris


def wrapper(stdscr: curses.window) -> int:
    try:
        Tetris(stdscr).main()
    except:
        return 1
    return 0


def main() -> int:
    return curses.wrapper(wrapper)

if __name__ == "__main__":
    sys.exit(main())
