"""Game menu — mode selection screen."""

from __future__ import annotations

import curses


from .config import Config
from .enums import Sections, WebClientMsgType
from .logger import logger
from .network import NetworkClient
from .utils import clear_win_without_border, draw_win_border, get_version


class Menu:
    """Terminal mode-selection menu.

    Renders a list of game modes inside bordered windows and dispatches
    to the versus lobby when the player selects multiplayer.
    """

    def __init__(self, stdscr: curses.window, config: Config) -> None:
        self._stdscr = stdscr
        self._config = config

        d = config.display
        self._title_window = curses.newwin(6, d.window_cols)
        self._sections_window = curses.newwin(d.window_rows - 8, d.window_cols, 6, 0)
        self._notice_window = curses.newwin(2, d.window_cols, d.window_rows - 2, 0)

        self._sections = [str(section) for section in Sections]
        self._cur_section = 0
        self._confirm = False

    def _versus_lobby(self) -> NetworkClient | None:
        """Connect to a multiplayer server and wait for an opponent.

        Shows status messages on ``self._sections_window``.
        Blocks until a match is found, the user cancels, or the connection
        fails.

        Returns:
            A connected :class:`NetworkClient` on success, or ``None`` on
            failure / cancellation.
        """
        network = NetworkClient()
        win = self._sections_window
        clear_win_without_border(win)
        host, port = (
            self._config.multi_play.host,
            self._config.multi_play.port,
        )

        x, y = win.getmaxyx()
        x -= 2
        y -= 2

        win.addstr(5, 1, f"Connecting to {host}:{port}...".center(y))
        win.refresh()

        try:
            network.handshake(host, port, get_version())
        except (OSError, RuntimeError) as e:
            logger.error(f"Connection failed: {e!r}")
            win.addstr(7, 1, f"Failed to connect.".center(y))
            win.addstr(9, 1, "Press any key to return...".center(y))
            win.refresh()
            win.getch()
            return None

        # handshake blocks until hello_ok; now wait for an opponent
        dots = 0
        while True:
            msg = network.recv(timeout=0.5)
            if msg is not None:
                msg_type = msg.get("type")
                if msg_type == WebClientMsgType.MATCH_FOUND:
                    network.opponent_id = msg["data"]["opponent_id"]
                    break
                if msg_type == WebClientMsgType.SERVER_FULL:
                    win.addstr(7, 1, "Server is full".center(y))
                    win.addstr(9, 1, "Press any key to return...".center(y))
                    win.refresh()
                    win.getch()
                    network.close()
                    return None
            dots = (dots + 1) % 4
            win.addstr(7, 1, f"Waiting for opponent{'.' * dots}".center(y))
            win.addstr(9, 1, f"Press 'q' to cancel.".center(y))
            if self._stdscr.getch() == ord("q"):
                network.send({"type": WebClientMsgType.LEAVE_QUEUE, "data": {}})
                network.close()
                return None
            win.refresh()

        return network

    def _draw_border(self) -> None:
        """Draw borders around the title, sections, and notice windows."""
        title_win = self._title_window
        sec_win = self._sections_window
        notice_win = self._notice_window

        d = self._config.display
        draw_win_border(title_win, d, bs="", bl=d.bd_v, br=d.bd_v)
        draw_win_border(sec_win, d, tl=d.bd_vr, tr=d.bd_vl, bl=d.bd_vr, br=d.bd_vl)
        draw_win_border(notice_win, d, ts="", tl=d.bd_v, tr=d.bd_v)

        title_win.refresh()
        sec_win.refresh()
        notice_win.refresh()

    def _draw_title(self) -> None:
        """Render the ASCII-art "Tetris Terminal" title."""
        window = self._title_window
        _, width = window.getmaxyx()
        width -= 2

        window.addstr(2, 1, "╺┳━┳━━┳━┳━┳┳┳━╸  ╺┳━┳━┏━┓┏┳┓┳┏┓┏━┓╻ ".center(width))
        window.addstr(3, 1, " ┃ ┣━ ┃ ┣┳┛┃┗━┓   ┃ ┣━┣┳┛┃┃┃┃┃┃┣━┫┃ ".center(width))
        window.addstr(4, 1, " ╹ ┗━ ╹ ╹┗╸┻╺━┛   ╹ ┗━┛┗━┛╹┗┻┛┗┛ ╹┗╸".center(width))
        window.refresh()

    def _draw_sections(self) -> None:
        """Render the mode list, highlighting the currently selected item."""
        window = self._sections_window
        height, width = window.getmaxyx()
        height -= 2
        width -= 2

        spaces = (height - len(self._sections)) // (len(self._sections) - 1)
        start_row = (
            (height - len(self._sections) - spaces * (len(self._sections) - 1)) >> 1
        ) + 1

        for i, section in enumerate(self._sections):
            if i == self._cur_section:
                window.addstr(
                    spaces * i + start_row + i,
                    1,
                    section.center(width),
                    curses.A_REVERSE,
                )
            else:
                window.addstr(spaces * i + start_row + i, 1, section.center(width))

        window.refresh()

    def _draw_notice(self) -> None:
        """Render the controls hint in the footer."""
        window = self._notice_window
        _, width = window.getmaxyx()

        notice = "tab, ↑, ↓ to select, enter to confirm"

        window.addstr(0, 1, notice.center(width - 2))
        window.refresh()

    def _draw(self) -> None:
        """Redraw the entire menu screen."""
        self._draw_border()
        self._draw_title()
        self._draw_sections()
        self._draw_notice()

    def _handle_input(self) -> None:
        """Process a single key-press from the user."""
        c = self._stdscr.getch()
        if c == ord("\n"):
            self._confirm = True
        if c == curses.KEY_UP:
            self._cur_section = (self._cur_section - 1) % len(self._sections)
        if c == curses.KEY_DOWN or c == ord("\t"):
            self._cur_section = (self._cur_section + 1) % len(self._sections)

    def _loop(self) -> None | NetworkClient:
        """Main menu loop — handles input, drawing, and versus-mode flow.

        Returns:
            A connected :class:`NetworkClient` when versus mode was selected
            and a match was found, or ``None`` for single-player modes.
        """
        while not self._confirm:
            self._handle_input()
            self._draw()

        if self._confirm and Sections(self._cur_section) == Sections.VERSUS:

            terminal_height, terminal_width = self._stdscr.getmaxyx()
            if (
                terminal_height < self._config.display.window_rows
                or terminal_width < self._config.display.window_cols_versus_mode
            ):
                raise RuntimeError(
                    f"verses mode needs {self._config.display.window_rows} rows, "
                    f"and {self._config.display.window_cols_versus_mode} cols terminal size."
                )

            network = self._versus_lobby()
            if network is None:
                self._confirm = False
                clear_win_without_border(self._sections_window)
                self._loop()
            return network

    def main(self) -> tuple[int, NetworkClient | None]:
        """Run the menu and return the selected section and optional network client.

        Returns:
            A tuple of ``(section_index, network)`` where *network* is
            ``None`` for single-player modes or a connected
            :class:`NetworkClient` for versus mode.
        """
        self._stdscr.timeout(100)
        network = self._loop()
        return self._cur_section, network
