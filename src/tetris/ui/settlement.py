"""Settlement (game-over statistics) display UI."""

from __future__ import annotations

import curses

from ..config import Config
from ..settlement_message import SettlementMessage
from ..utils import draw_win_border


class Settlement:
    """Game-over statistics screen.

    Renders the :class:`SettlementMessage` inside a bordered window and
    lets the player choose to retry or quit.
    """

    def __init__(
        self, stdscr: curses.window, set_msg: SettlementMessage, config: Config
    ) -> None:
        self._stdscr = stdscr
        self._set_msg = set_msg
        self._config = config

        d = config.display
        self._title_window = curses.newwin(6, d.window_cols)
        self._show_window = curses.newwin(d.window_rows - 8, d.window_cols, 6, 0)
        self._notice_window = curses.newwin(2, d.window_cols, d.window_rows - 2, 0)

    def _draw_border(self) -> None:
        """Draw the outer borders for all settlement sub-windows."""
        title_win = self._title_window
        show_win = self._show_window
        notice_win = self._notice_window

        d = self._config.display
        draw_win_border(title_win, d, bs="", bl=d.bd_v, br=d.bd_v)
        draw_win_border(show_win, d, tl=d.bd_vr, tr=d.bd_vl, bl=d.bd_vr, br=d.bd_vl)
        draw_win_border(notice_win, d, ts="", tl=d.bd_v, tr=d.bd_v)

        title_win.refresh()
        show_win.refresh()

    def _draw_title(self) -> None:
        """Render the "GAME OVER" ASCII-art title."""
        window = self._title_window
        _, width = window.getmaxyx()
        width -= 2

        window.addstr(2, 1, "┏━┓┏━┓┏┳┓┏━   ┏━┓╻ ╻┏━┏━┓".center(width))
        window.addstr(3, 1, "┃ ┳┣━┫┃┃┃┣━   ┃ ┃┗┓┃┣━┣┳┛".center(width))
        window.addstr(4, 1, "┗━┛╹ ╹╹╹╹┗━   ┗━┛ ┗┛┗━┛┗╸".center(width))
        window.refresh()

    def _draw_show(self) -> None:
        """Render the settlement statistics."""
        window = self._show_window
        height, width = window.getmaxyx()
        height -= 2
        width -= 2

        messages = self._set_msg.format(width)

        start_row = (height - len(messages)) >> 1

        window.addstr(start_row - 1, 1, self._set_msg.title.center(width))

        for i, line in enumerate(messages):
            window.addstr(i + start_row + 1, 1, line)

        window.refresh()

    def _draw_notice(self) -> None:
        """Render the footer notice (quit / retry)."""
        window = self._notice_window
        _, width = window.getmaxyx()

        notice = "'q' to quit, 'r' to retry."

        window.addstr(0, 1, notice.center(width - 2))
        window.refresh()

    def _draw(self) -> None:
        """Redraw the entire settlement screen."""
        self._draw_border()
        self._draw_title()
        self._draw_show()
        self._draw_notice()

    def _loop(self) -> int:
        """Input loop for the settlement screen.

        Returns:
            ``1`` if the player chose to retry, ``0`` to quit.
        """
        while True:
            self._draw()
            c = self._stdscr.getch()
            if c == ord("r") or c == ord("R"):
                return 1
            elif c == ord("q") or c == ord("Q"):
                return 0

    def main(self) -> int:
        """Run the settlement screen.

        Returns:
            ``1`` if the player chose to retry, ``0`` to quit.
        """
        self._stdscr.timeout(-1)
        return self._loop()
