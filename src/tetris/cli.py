import curses
import sys
import argparse

from importlib.metadata import PackageNotFoundError, version

from tetris import Tetris


def get_version() -> str:
    try:
        return version("tetris-terminal")
    except PackageNotFoundError:
        return "0.0.0-dev"


def wrapper(stdscr: curses.window) -> int:
    Tetris(stdscr).main()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Tetris Terminal",
        epilog=f"Tetris Terminal v{get_version()}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"v{get_version()}"
    )

    args = parser.parse_args()

    return curses.wrapper(wrapper)


if __name__ == "__main__":
    sys.exit(main())
