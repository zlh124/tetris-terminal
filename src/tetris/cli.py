import argparse
import curses
import sys
from typing import Callable

from .config import Config
from .logger import setup_from_config, logger
from .menu import Menu, Sections
from .settlement import Settlement
from .tetris import Tetris, GameMode
from .utils import get_version


def make_wrapper(
    server_host: str | None = None,
    server_port: int | None = None,
    config: Config | None = None,
) -> Callable[..., int]:
    if config is None:
        config = Config.load()

    def wrapper(stdscr: curses.window) -> int:
        if server_host is not None:
            config.multi_play.host = server_host
        if server_port is not None:
            config.multi_play.port = server_port

        terminal_height, terminal_width = stdscr.getmaxyx()
        if (
            terminal_height < config.display.window_rows
            or terminal_width < config.display.window_cols
        ):
            raise RuntimeError(
                f"tetris-terminal needs {config.display.window_rows} rows, and {config.display.window_cols} cols terminal size."
            )

        curses.use_default_colors()
        curses.curs_set(False)
        while True:
            section, network = Menu(stdscr, config).main()
            if section == Sections.QUIT:
                return 0

            # multi game modes
            game_mode = GameMode(section)
            set_msg = Tetris(stdscr, game_mode, config, network=network).main()

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
    parser.add_argument(
        "--server",
        default=None,
        metavar="HOST:PORT",
        help="multiplayer server address (default: localhost:8765)",
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

    disable_config = args.disable_config
    config = Config() if disable_config else Config.load()
    setup_from_config(config.logging)

    logger.info("Tetris Terminal Started!")
    logger.info(f"Config: {config.get_config_data()}")
    logger.info(f"params: {args._get_kwargs()}")

    host: str | None = None
    port: int | None = None
    if args.server is not None:
        host, _, port_str = args.server.partition(":")
        if not host:
            host = None
        if port_str:
            try:
                port = int(port_str)
                if not (0 <= port <= 65535):
                    raise ValueError
            except ValueError:
                print(f"Invalid port: {port_str}", file=sys.stderr)
                return 1

    return curses.wrapper(
        make_wrapper(
            server_host=host,
            server_port=port,
            config=config,
        )
    )
