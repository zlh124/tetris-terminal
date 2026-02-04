import curses
import sys

from tetris import GAME_WINDOW_SIZE_HEIGHT, GAME_WINDOW_SIZE_WIDTH, Tetris


def wrapper(stdscr: curses.window) -> int:
    if curses.COLS < GAME_WINDOW_SIZE_WIDTH or curses.LINES < GAME_WINDOW_SIZE_HEIGHT:
        return 1
    Tetris(stdscr).main()
    return 0


def main() -> int:
    if curses.wrapper(wrapper) == 1:
        print(
            f"ensure your terminal has at least {GAME_WINDOW_SIZE_HEIGHT} rows and {GAME_WINDOW_SIZE_WIDTH} columns."
        )
        print("To ensure the game runs smoothly.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
